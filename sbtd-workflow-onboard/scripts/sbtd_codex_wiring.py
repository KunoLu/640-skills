"""Pure byte-candidate renderers for P1-04 Codex Graft wiring.

This module owns no filesystem state: each function takes the current host
configuration as bytes and returns the exact candidate bytes the caller may
persist. Writing, backups, ownership journals, authorization recording and
every real-host proof stay with the deployment caller; nothing here creates,
deletes or probes anything, and no check/plan path invokes these renderers
implicitly.

Exports (the complete public surface):

- ``codex_mcp_candidate(before, bindings)`` — merge the whole binding batch
  into Codex ``config.toml`` bytes, preserving foreign tables and comments
  through tomlkit. Every bound repository root gets exactly one deterministic
  server key ``sbtd-graft-<sha256(canonical root UTF-8)[:16]>`` whose
  ``command`` is the absolute Python and whose ``args`` start with ``-E -s``
  (ignore the caller's PYTHON* startup environment, disable the user-site
  directory — no caller-controlled ``json.py``/``sitecustomize`` shadow or
  PYTHONHOME redirect runs before the launcher's own guard imports, while
  the launcher's script directory stays importable, unlike ``-I``) followed
  by the absolute managed launcher and ``mcp --root <root> --node <node>
  --entry <cli>``, and whose ``cwd`` is the bound root. The entry is never a
  plain ``npx``/``graft``
  command. ``env`` declares DO_NOT_TRACK/DNT explicitly; the managed launcher
  still scrubs the rest of the inherited environment itself. The key hash
  covers the root string verbatim, so callers must pass the canonical
  absolute root. An existing entry under the same key is left untouched when
  it is exactly the desired content; any difference blocks the whole batch
  with ``ownership-conflict``, because a same-key entry that is not exactly
  ours cannot be claimed. Foreign ``mcp_servers`` entries — including other
  graft-looking ones — are never scanned, renamed or replaced.
- ``codex_hooks_candidate(before, bindings, *, authorized)`` — merge managed
  Codex hook groups into ``hooks.json`` bytes. ``authorized=False`` returns
  the original bytes exactly and installs/removes nothing. When authorized,
  each bound root gets four entries pointing at the absolute Python with the
  same ``-E -s`` startup hardening plus the managed launcher ``hook``
  invocation with explicit
  ``--root/--node/--entry/--event`` flags: SessionStart (matcher
  ``startup|resume|clear|compact``, 10s), UserPromptSubmit (15s), PostToolUse
  (matcher ``apply_patch|Write|Edit|MultiEdit``, 10s) and Stop (130s — the
  managed bridge synchronously completes the pinned package's structural
  sync, whose native subprocess cap is 120s, before the Stop handler, so the
  budget must exceed that cap with launcher and teardown headroom). Every
  foreign handler is preserved, including handlers sharing a group with an
  owned entry; owned entries are identified only by parsing ``command`` in
  the host shell dialect and matching the exact launcher argv with the known
  flag vocabulary, never by substring (e.g. ``graft-hooks.cjs``). Commands
  are rendered in that same dialect: POSIX ``sh -lc`` quoting via
  ``shlex.join`` on Unix, and on Windows — where Codex 0.154 runs
  ``cmd.exe /C "<command>"`` — stdlib ``subprocess.list2cmdline`` quoting
  after refusing any managed path containing a live ``cmd.exe`` operator,
  since quoting alone cannot neutralize those. Stale owned entries for a
  bound root/event are replaced by the canonical entry; identical ones are
  left untouched. No hook trust state or feature flags are set here —
  rendered output stays inactive until the host/user approves it.
- ``project_agents_candidate(before)`` — replace or append the single managed
  ``<!-- graft:start -->``/``<!-- graft:end -->`` fence in project AGENTS
  bytes with the bundled ``assets/graft-instructions.txt`` body. Every byte
  outside the fence is preserved; zero marker pairs append, exactly one
  ordered pair is replaced idempotently, anything else is a conflict.

All failures are sanitized ``ContractError`` failures (exit code 2) with fixed
rule text — never rejected values or foreign content. Strict UTF-8, duplicate JSON
keys, non-finite JSON numbers, malformed JSON/TOML, wrong section shapes and
ownership conflicts all fail closed. ``bindings`` items are mappings with
``root``, ``node``, ``cli``, ``python`` and ``launcher`` absolute path strings
(caller-verified, re-checked here); extra keys are ignored. An empty batch
returns the input bytes unchanged.

Known limits, deliberately fail-closed: a foreign inline-table
``mcp_servers`` section is rejected instead of rewritten; owned hook argv
with unknown or repeated flags, or owned entries filed under a different
event than their ``--event`` flag, are treated as foreign and preserved, not
managed. On Windows a managed binding path that cannot be represented safely
for ``cmd.exe`` (command operators, quotes, control characters) is refused
with ``invalid-argument`` rather than rendered into a shell-misparseable
command; foreign commands are only ever parsed, never rewritten.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NoReturn

from onboard_contracts import ContractError
from sbtd_project import _check_finite, _reject_json_constant, _reject_json_duplicates

__all__ = [
    "codex_hooks_candidate",
    "codex_mcp_candidate",
    "project_agents_candidate",
]

_KEY_PREFIX = "sbtd-graft-"
_BINDING_KEYS = ("root", "node", "cli", "python", "launcher")
_MCP_ENV = (("DO_NOT_TRACK", "1"), ("DNT", "1"))
# Interpreter flags rendered between the pinned Python and the managed
# launcher in every owned command: ``-E`` ignores the caller's PYTHON*
# startup environment (PYTHONPATH/PYTHONHOME/…), ``-s`` disables the
# user-site directory. Together they keep hostile ``json.py``/
# ``sitecustomize.py``/``usercustomize.py`` shadows and an invalid
# PYTHONHOME from running or breaking the interpreter before the launcher's
# own guard imports execute. Unlike ``-I`` (isolated), the launcher's script
# directory stays on ``sys.path``, so its trusted sibling modules still
# import. The ownership parser accepts exactly this argv shape.
_PYTHON_STARTUP_FLAGS = ("-E", "-s")


# Codex 0.154 executes hook commands through the host shell: ``$SHELL -lc``
# (fallback ``/bin/sh -lc``) on Unix, ``cmd.exe /C "<command>"`` on Windows
# (pinned evidence: codex-rs hooks command_runner.rs at rust-v0.154.0). The
# command dialect below is therefore selected by the host, and the exact same
# dialect parses owned commands back for the ownership check.
_WINDOWS = os.name == "nt"
# ``cmd.exe`` operators that stay live even inside a double-quoted argument:
# environment expansion (``%``, ``!``), chaining and redirection
# (``& | < >``), grouping (``( )``), the escape character (``^``) and the
# quote character itself. Quoting cannot neutralize them, so a managed path
# containing any is refused instead of rendered into a command that expands,
# splits or misparse. ``subprocess.list2cmdline`` alone does NOT quote these.
_CMD_FORBIDDEN = frozenset('&|<>^%!()"')

# (Codex event name, group matcher or None, timeout seconds, launcher event flag)
# Stop must outlast the managed bridge's synchronous structural sync: the
# pinned package caps that native subprocess at 120 seconds
# (dist/claude/sync-run.js ``execFileSync(..., timeout: 120000)``), so the
# Stop budget adds launcher, Node startup and teardown headroom on top of the
# cap. Every other event keeps its budget.
_HOOK_SPECS = (
    ("SessionStart", "startup|resume|clear|compact", 10, "session-start"),
    ("UserPromptSubmit", None, 15, "prompt"),
    ("PostToolUse", "apply_patch|Write|Edit|MultiEdit", 10, "post-edit"),
    ("Stop", None, 130, "stop"),
)
_HOOK_FLAGS = ("--root", "--node", "--entry", "--event")
_EVENT_FLAGS = frozenset(spec[3] for spec in _HOOK_SPECS)

_FENCE_START = "<!-- graft:start -->"
_FENCE_END = "<!-- graft:end -->"
_INSTRUCTIONS = (
    Path(__file__).resolve().parents[1] / "assets" / "graft-instructions.txt"
)


def _fail(code: str, message: str) -> NoReturn:
    raise ContractError(code, message)


# ---------------------------------------------------------------------------
# Shared argument and decoding gates
# ---------------------------------------------------------------------------


def _raw_bytes(before: bytes) -> bytes:
    if not isinstance(before, (bytes, bytearray)):
        _fail("invalid-argument", "input document must be bytes")
    return bytes(before)


def _utf8(raw: bytes, code: str, message: str) -> str:
    try:
        return raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        _fail(code, message)


def _resolved_bindings(bindings: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if isinstance(bindings, (str, bytes, bytearray)) or not isinstance(
        bindings, Sequence
    ):
        _fail("invalid-argument", "bindings must be a sequence of mappings")
    resolved: list[dict[str, str]] = []
    for binding in bindings:
        if not isinstance(binding, Mapping):
            _fail("invalid-argument", "each binding must be a mapping")
        paths: dict[str, str] = {}
        for key in _BINDING_KEYS:
            value = binding.get(key)
            if isinstance(value, os.PathLike):
                value = os.fspath(value)
            if not isinstance(value, str) or not value or not os.path.isabs(value):
                _fail(
                    "invalid-argument",
                    "binding paths must be non-empty absolute path strings",
                )
            paths[key] = value
        resolved.append(paths)
    return resolved


def _encode(text: str) -> bytes:
    try:
        return text.encode("utf-8")
    except UnicodeEncodeError:
        _fail("malformed-unicode", "document contains unpaired Unicode surrogates")


# ---------------------------------------------------------------------------
# Codex config.toml MCP candidate
# ---------------------------------------------------------------------------


def _toml_support() -> tuple[Any, Any, Any, Any]:
    try:
        import tomlkit
        from tomlkit.exceptions import TOMLKitError
        from tomlkit.items import InlineTable, Table
    except ImportError:
        _fail(
            "validator-unavailable",
            "install the declared TOML editing dependency before this operation",
        )
    return tomlkit, TOMLKitError, InlineTable, Table


def _server_key(root: str) -> str:
    digest = hashlib.sha256(root.encode("utf-8")).hexdigest()
    return f"{_KEY_PREFIX}{digest[:16]}"


def _desired_server(paths: dict[str, str]) -> dict[str, Any]:
    return {
        "command": paths["python"],
        "args": [
            *_PYTHON_STARTUP_FLAGS,
            paths["launcher"],
            "mcp",
            "--root",
            paths["root"],
            "--node",
            paths["node"],
            "--entry",
            paths["cli"],
        ],
        "cwd": paths["root"],
        "env": dict(_MCP_ENV),
    }


def codex_mcp_candidate(before: bytes, bindings: Sequence[Mapping[str, Any]]) -> bytes:
    """Full-config ``config.toml`` candidate covering the whole binding batch."""
    raw = _raw_bytes(before)
    resolved = _resolved_bindings(bindings)
    if not resolved:
        return raw
    tomlkit, toml_error, inline_table, table_type = _toml_support()
    text = _utf8(raw, "invalid-utf8", "document is not strict UTF-8")
    try:
        document = tomlkit.parse(text)
    except (ValueError, RecursionError, toml_error):
        _fail("invalid-toml", "document is not well-formed TOML")
    servers = document.get("mcp_servers")
    if servers is None:
        servers = tomlkit.table(is_super_table=True)
        document["mcp_servers"] = servers
    elif isinstance(servers, inline_table) or not isinstance(servers, table_type):
        _fail(
            "invalid-config",
            "the existing mcp_servers section is not a plain table",
        )
    for paths in resolved:
        key = _server_key(paths["root"])
        desired = _desired_server(paths)
        existing = servers.get(key)
        if existing is None:
            entry = tomlkit.table()
            entry["command"] = desired["command"]
            entry["args"] = desired["args"]
            entry["cwd"] = desired["cwd"]
            env = tomlkit.table()
            for name, value in _MCP_ENV:
                env[name] = value
            entry["env"] = env
            servers[key] = entry
            continue
        if not isinstance(existing, (table_type, inline_table)):
            _fail(
                "ownership-conflict",
                "an existing sbtd-graft MCP entry differs and cannot be claimed",
            )
        if existing.unwrap() != desired:
            _fail(
                "ownership-conflict",
                "an existing sbtd-graft MCP entry differs and cannot be claimed",
            )
    try:
        rendered = tomlkit.dumps(document)
    except (ValueError, RecursionError):
        _fail("invalid-config", "the rendered TOML candidate cannot be serialized")
    return _encode(rendered)


# ---------------------------------------------------------------------------
# Codex hooks.json candidate
# ---------------------------------------------------------------------------


def _cmd_split(command: str) -> list[str]:
    """CommandLineToArgvW semantics: the exact argv the launcher's C runtime
    builds from a ``cmd.exe`` command line.

    Backslash runs collapse only before a quote (an odd run ends in a literal
    quote), ``""`` inside a quoted section is a literal quote, and an
    unterminated quote is tolerated — the Microsoft argument-parsing contract
    ``python.exe`` applies after ``cmd.exe`` processing. Anything that does
    not parse to the managed argv shape is foreign by construction, never an
    error.
    """
    argv: list[str] = []
    length = len(command)
    index = 0
    while True:
        while index < length and command[index] in " \t":
            index += 1
        if index >= length:
            return argv
        token: list[str] = []
        quoted = False
        while index < length:
            backslashes = 0
            while index < length and command[index] == "\\":
                backslashes += 1
                index += 1
            if index >= length:
                token.append("\\" * backslashes)
                break
            char = command[index]
            if char == '"':
                token.append("\\" * (backslashes // 2))
                if backslashes % 2:
                    token.append('"')
                    index += 1
                    continue
                if quoted and index + 1 < length and command[index + 1] == '"':
                    token.append('"')
                    index += 2
                    continue
                quoted = not quoted
                index += 1
                continue
            token.append("\\" * backslashes)
            if not quoted and char in " \t":
                break
            token.append(char)
            index += 1
        argv.append("".join(token))


def _split_hook_command(command: str) -> list[str] | None:
    """Host shell-dialect argv parse; ``None`` when POSIX words are unbalanced."""
    if _WINDOWS:
        return _cmd_split(command)
    try:
        return shlex.split(command)
    except ValueError:
        return None


def _hook_command(paths: dict[str, str], event_flag: str) -> str:
    argv = [
        paths["python"],
        *_PYTHON_STARTUP_FLAGS,
        paths["launcher"],
        "hook",
        "--root",
        paths["root"],
        "--node",
        paths["node"],
        "--entry",
        paths["cli"],
        "--event",
        event_flag,
    ]
    if not _WINDOWS:
        return shlex.join(argv)
    for argument in argv:
        if any(
            char in _CMD_FORBIDDEN or (ord(char) < 0x20 and char != "\t")
            for char in argument
        ):
            _fail(
                "invalid-argument",
                "a managed hook command path cannot be represented safely for "
                "the Windows command shell",
            )
    return subprocess.list2cmdline(argv)


def _owned_hook_flags(command: str, launcher: str) -> dict[str, str] | None:
    """Exact owned-flag parse: our launcher argv with the known flag vocabulary.

    The current isolated argv is executable only after its full identity
    matches. The exact former unisolated shape is recognized solely so
    authorized reconciliation can reject it, never to leave it active as a
    foreign handler beside a new command.
    """
    argv = _split_hook_command(command)
    if argv is None:
        return None
    if (
        len(argv) >= 5
        and argv[1:3] == list(_PYTHON_STARTUP_FLAGS)
        and argv[3:5] == [launcher, "hook"]
    ):
        tokens = argv[5:]
        startup = "isolated"
    elif len(argv) >= 3 and argv[1:3] == [launcher, "hook"]:
        tokens = argv[3:]
        startup = "unisolated"
    else:
        return None
    if not tokens or len(tokens) % 2:
        return None
    flags: dict[str, str] = {}
    for offset in range(0, len(tokens), 2):
        flag, value = tokens[offset], tokens[offset + 1]
        if flag not in _HOOK_FLAGS or flag in flags:
            return None
        flags[flag] = value
    if set(flags) != set(_HOOK_FLAGS) or flags["--event"] not in _EVENT_FLAGS:
        return None
    flags["interpreter"] = argv[0]
    flags["startup"] = startup
    return flags


def _merge_hook_event(
    groups: list[Any],
    paths: dict[str, str],
    matcher: str | None,
    timeout: int,
    event_flag: str,
) -> None:
    desired: dict[str, Any] = {
        "type": "command",
        "command": _hook_command(paths, event_flag),
        "timeout": timeout,
    }
    hits: list[tuple[int, int]] = []
    for group_index, group in enumerate(groups):
        if not isinstance(group, dict):
            continue
        entries = group.get("hooks")
        if not isinstance(entries, list):
            continue
        for entry_index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            command = entry.get("command")
            if not isinstance(command, str):
                continue
            flags = _owned_hook_flags(command, paths["launcher"])
            if flags is None:
                continue
            if flags["--root"] != paths["root"] or flags["--event"] != event_flag:
                continue
            if flags["startup"] != "isolated":
                _fail(
                    "ownership-conflict",
                    "a prior unisolated managed hook requires explicit reconciliation",
                )
            if (
                flags["interpreter"] != paths["python"]
                or flags["--node"] != paths["node"]
                or flags["--entry"] != paths["cli"]
                or entry.get("type") != "command"
            ):
                _fail(
                    "ownership-conflict",
                    "a managed hook command was changed and requires reconciliation",
                )
            hits.append((group_index, entry_index))
    if hits:
        if len(hits) != 1:
            _fail(
                "ownership-conflict",
                "duplicate managed hooks require explicit reconciliation",
            )
        group_index, entry_index = hits[0]
        group = groups[group_index]
        entries = group["hooks"]
        if len(entries) != 1 or set(group) - {"matcher", "hooks"}:
            _fail(
                "ownership-conflict",
                "a mixed managed hook group requires explicit reconciliation",
            )
        entries[entry_index] = desired
        if matcher is None:
            group.pop("matcher", None)
        else:
            group["matcher"] = matcher
        return
    owned_group: dict[str, Any] = {}
    if matcher is not None:
        owned_group["matcher"] = matcher
    owned_group["hooks"] = [desired]
    groups.append(owned_group)


def codex_hooks_candidate(
    before: bytes, bindings: Sequence[Mapping[str, Any]], *, authorized: bool
) -> bytes:
    """Codex ``hooks.json`` candidate; exact original bytes unless authorized."""
    raw = _raw_bytes(before)
    if not authorized:
        return raw
    resolved = _resolved_bindings(bindings)
    if not resolved:
        return raw
    text = _utf8(raw, "invalid-utf8", "document is not strict UTF-8")
    if text.strip():
        try:
            document = json.loads(
                text,
                object_pairs_hook=_reject_json_duplicates,
                parse_constant=_reject_json_constant,
            )
        except (ValueError, RecursionError):
            _fail("invalid-json", "document is not well-formed unambiguous JSON")
        if not isinstance(document, dict):
            _fail("invalid-config", "the hooks document root must be a JSON object")
        if not _check_finite(document):
            _fail("non-finite-number", "document contains a non-finite number")
    else:
        document = {}
    hooks = document.get("hooks")
    if hooks is None:
        hooks = {}
        document["hooks"] = hooks
    elif not isinstance(hooks, dict):
        _fail("invalid-config", "the hooks section must be a JSON object")
    for event, matcher, timeout, event_flag in _HOOK_SPECS:
        groups = hooks.get(event)
        if groups is None:
            groups = []
            hooks[event] = groups
        elif not isinstance(groups, list):
            _fail("invalid-config", "a hook event section must be a JSON array")
        if any(
            not isinstance(group, dict)
            or (
                "hooks" in group
                and (
                    not isinstance(group["hooks"], list)
                    or any(not isinstance(entry, dict) for entry in group["hooks"])
                )
            )
            for group in groups
        ):
            _fail(
                "invalid-config",
                "a hook event contains an unsupported foreign container",
            )
        for paths in resolved:
            _merge_hook_event(groups, paths, matcher, timeout, event_flag)
    try:
        rendered = json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False)
    except (ValueError, RecursionError):
        _fail("invalid-config", "the rendered hooks candidate cannot be serialized")
    return _encode(rendered + "\n")


# ---------------------------------------------------------------------------
# Project AGENTS.md managed fence candidate
# ---------------------------------------------------------------------------


def _instructions_body() -> str:
    try:
        raw = _INSTRUCTIONS.read_bytes()
    except OSError:
        _fail(
            "runtime-unavailable",
            "the bundled graft instructions asset is unavailable",
        )
    body = _utf8(
        raw,
        "runtime-unavailable",
        "the bundled graft instructions asset is not strict UTF-8",
    ).strip()
    if not body or _FENCE_START in body or _FENCE_END in body:
        _fail("runtime-unavailable", "the bundled graft instructions asset is invalid")
    return body


def project_agents_candidate(before: bytes) -> bytes:
    """AGENTS candidate with exactly one current managed graft fence."""
    text = _utf8(_raw_bytes(before), "invalid-utf8", "document is not strict UTF-8")
    block = f"{_FENCE_START}\n{_instructions_body()}\n{_FENCE_END}"
    starts = text.count(_FENCE_START)
    ends = text.count(_FENCE_END)
    if starts == 0 and ends == 0:
        prefix = text
        if prefix and not prefix.endswith("\n"):
            prefix += "\n"
        if prefix and not prefix.endswith("\n\n"):
            prefix += "\n"
        return _encode(f"{prefix}{block}\n")
    if starts != 1 or ends != 1:
        _fail(
            "ownership-conflict",
            "the managed graft fence is incomplete or ambiguous",
        )
    left = text.index(_FENCE_START)
    end = text.index(_FENCE_END)
    if end < left:
        _fail("ownership-conflict", "the managed graft fence is misordered")
    right = end + len(_FENCE_END)
    return _encode(text[:left] + block + text[right:])
