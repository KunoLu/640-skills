r"""Upgrade host-domain resources: Codex/OMP MCP config and shell PATH profiles.

This module owns the host side of the Onboard upgrade alignment (design.md
§公共接口与模块责任):

- ``build_host_resources(scope, *, package_root=None)`` returns one resource
  per selected host config (``kind="mcp"``) and per selected shell profile
  (``kind="shell"``), in the inventory resource shape plus ``host`` /
  ``profile`` descriptors. Planning is strictly read-only: it never starts a
  host, never performs shell command resolution, and never reads ambient
  configuration. It binds the explicit profile, selected executable identity,
  and effective OMP source states; no config content or secrets enter output.
- ``render_resource(resource, *, package_root=None)`` revalidates the live
  before-state and regenerates the candidate bytes through the existing
  structured renderers. It needs only the sealed resource dict.
- ``verify_hosts(scope, *, package_root=None, probe=False)`` reports every
  domain by disk / runtime / host / legacy dimensions. Without ``probe`` it
  is read-only and never claims host evidence. With ``probe`` it performs
  real checks: runtime identity proofs, a direct MCP initialize/tools/list
  handshake against the managed argv, and real host reload/load through the
  Codex app-server JSON-RPC protocol (v2, codex-cli 0.159.x) or the OMP RPC
  protocol (omp 18.x) — always inside private fixtures containing only the
  selected managed configuration and copied selected skill roots, never the
  live HOME, never credentials, never a model request.
  Shell probes parse and source only the explicitly selected profile with
  isolated HOME and resolve ``graft`` without executing it. Standard npm
  command symlinks are supported; unselected bin siblings are never scanned.

Managed-content semantics are the existing candidates': unrelated servers,
comments and profile bytes are preserved; unknown ownership of the managed
``sbtd-graft`` key, retired hash-keyed generations, malformed configs and
ambiguous shell markers all refuse (resource ``identity-conflict`` /
``blocked``). A differing existing global entry is replaced only after it is
proven to be exactly the owned global shape (Codex additionally requires the
old launcher inside the selected installed Onboard root). Source package paths
never become final launcher bindings. One selected Skills root derives the
installation; multiple roots require explicit ``host.onboard_root`` selection,
and host-only domains require an existing source-matching trusted installation.

Applicability: only ``codex`` and ``omp`` hosts carry managed MCP wiring.
Other platforms (e.g. claude/kimi) are reported ``unsupported`` and no
resource or wiring is invented for them. Legacy retired entries are reported
in the legacy dimension; retiring them belongs to the cleanup engine, never
to this module. On native Windows a bash/zsh managed block renders the bin
in Git Bash POSIX form (``/c/Users/...``): a drive-letter colon is the POSIX
PATH delimiter, so both ``C:\`` and ``C:/`` entries split and could never
resolve. Probes run through the real available shell (Git Bash for bash) and
compare the reported ``/c/...`` resolution with the native ``C:\...``
selection via path aliases — a pass is real, never fabricated. PowerShell
profiles keep their native form and probe. Every probe fixture directory is
created through the migration ``require_private_directory`` primitive, so
Windows privacy is proven by its ACL helper at creation, never by a chmod.

Probe evidence policy: recorded evidence is limited to fixed status tokens,
digests, sorted pinned tool names, skill names, and exit/timeout flags. Raw
subprocess stdout/stderr and configuration bytes are never recorded or
printed. Host-load runs against an isolated HOME carrying only the selected
managed projection and is labelled ``isolated-host/selected-projection``; it
never claims the original GUI, live profile, or existing sessions loaded the
new state. The original-domain live reload is reported separately as
``live_reload`` and stays ``unverified`` (never ``unsupported``) until an
explicit future authorization checks the actual chosen domain. Host-load
reports ``unavailable`` when the host CLI or a proven project root is
missing, ``unsupported`` when the actual binary lacks the protocol surface,
and ``failed`` on real errors or evidence mismatch — a pass is never
fabricated.
"""

from __future__ import annotations

import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, NoReturn

import onboard_contracts as contracts
from graft_runtime import GRAFT_PINNED_VERSION
from onboard_contracts import ContractError
from sbtd_cleanup_targets import strict_json_object
from sbtd_graft_deployment import launch_bindings
from sbtd_graft_entry import validate_project, validate_runtime
from sbtd_migration_files import (
    _canonical,
    backup_reference,
    read_file,
    require_private_directory,
    snapshot,
)

__all__ = ["build_host_resources", "render_resource", "verify_hosts"]

_SUPPORTED_MCP_PLATFORMS = frozenset({"codex", "omp"})
_SHELLS = frozenset({"bash", "zsh", "powershell"})
_OWNER_KIND = "upgrade-host"
_GLOBAL_SERVER = "sbtd-graft"
_SERVER_PREFIX = "sbtd-graft-"
_STARTUP_FLAGS = ("-E", "-s")
_TELEMETRY_ENV = (("DO_NOT_TRACK", "1"), ("DNT", "1"))
# Pinned tool catalog of the managed MCP server, bound to GRAFT_PINNED_VERSION
# (PRD AC-01 evidence for the pinned release): initialize + tools/list must
# return exactly this set.
_PINNED_GRAFT_TOOLS = (
    "graft_check_freshness",
    "graft_file_api",
    "graft_find_all",
    "graft_find_code",
    "graft_repo_map",
    "graft_trace_calls",
)

_MARKER_START = b"# sbtd-workflow-onboard:path:start"
_MARKER_END = b"# sbtd-workflow-onboard:path:end"
_NVM_HINTS = (b"NVM_DIR", b"nvm.sh")

_PROPAGATE_CODES = frozenset({"unsafe-path"})

# Bounded, isolated probe budgets (seconds). Probes never retry.
_HANDSHAKE_TIMEOUT = 90.0
_HOST_TIMEOUT = 150.0
_HOST_SHUTDOWN = 10.0
# Host-load evidence runs against an isolated HOME carrying only the selected
# managed projection; it never claims the original GUI, live profile, or
# existing sessions loaded the new state. The original-domain live reload is
# a separate dimension kept ``unverified`` (never ``unsupported``) so an
# explicit future authorization can check the actual chosen domain.
_HOST_LOAD_EVIDENCE_SCOPE = "isolated-host/selected-projection"
_LIVE_RELOAD = {"status": "unverified", "reason": "original-domain-not-authorized"}


def _fail(code: str, message: str) -> NoReturn:
    raise ContractError(code, message)


# ---------------------------------------------------------------------------
# Scope extraction (defensive re-validation of the engine-validated scope)
# ---------------------------------------------------------------------------


def _is_abs(value: Any) -> bool:
    return isinstance(value, str) and os.path.isabs(value)


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not _is_abs(item) for item in value):
        _fail("scope-conflict", f"scope {label} must be absolute path strings")
    return list(value)


def _scope_hosts(scope: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = scope.get("hosts") or []
    if not isinstance(raw, list):
        _fail("scope-conflict", "scope hosts must be a list")
    top_roots = {os.path.normpath(item) for item in scope.get("skills_roots") or []}
    hosts: list[dict[str, Any]] = []
    ids: set[str] = set()
    for entry in raw:
        if not isinstance(entry, Mapping):
            _fail("scope-conflict", "a scope host entry is malformed")
        host_id = entry.get("id")
        platform = entry.get("platform")
        config_home = entry.get("config_home")
        config = entry.get("config")
        if (
            not isinstance(host_id, str)
            or not host_id
            or host_id in ids
            or not isinstance(platform, str)
            or not platform
            or not _is_abs(config_home)
            or not _is_abs(config)
        ):
            _fail("scope-conflict", "a scope host identity or config path is invalid")
        ids.add(host_id)
        home_path = Path(config_home)
        config_path = Path(config)
        if config_path == home_path or not config_path.is_relative_to(home_path):
            _fail(
                "scope-conflict",
                "a scope host config must live inside its config_home",
            )
        skills_roots = _string_list(entry.get("skills_roots") or [], "host skills_roots")
        if any(os.path.normpath(item) not in top_roots for item in skills_roots):
            _fail(
                "scope-conflict",
                "a scope host skills root is not a selected top-level root",
            )
        runtime = entry.get("runtime")
        if not isinstance(runtime, Mapping) or set(runtime) != {"python", "node", "cli"}:
            _fail("scope-conflict", "a scope host runtime must name python/node/cli")
        executable = entry.get("executable")
        if executable is not None and not _is_abs(executable):
            _fail("scope-conflict", "a scope host executable must be absolute")
        onboard_root = entry.get("onboard_root")
        if platform in _SUPPORTED_MCP_PLATFORMS:
            candidates = [str(Path(root) / "sbtd-workflow-onboard") for root in skills_roots]
            if onboard_root is None and len(candidates) == 1:
                onboard_root = candidates[0]
            if not _is_abs(onboard_root):
                _fail("scope-conflict", "a supported host needs one canonical installed Onboard root")
            onboard_root = str(_canonical(Path(onboard_root)))
            if candidates and onboard_root not in candidates:
                _fail("unsafe-path", "the Onboard installation is outside selected host Skills roots")
        hosts.append(
            {
                "id": host_id,
                "platform": platform,
                "config_home": config_home,
                "config": config,
                "skills_roots": skills_roots,
                "runtime": dict(runtime),
                "project_roots": _string_list(
                    entry.get("project_roots") or [], "host project_roots"
                ),
                "executable": executable,
                "onboard_root": onboard_root,
            }
        )
    return hosts


def _scope_shell_profiles(scope: Mapping[str, Any]) -> list[dict[str, str]]:
    raw = scope.get("shell_profiles") or []
    if not isinstance(raw, list):
        _fail("scope-conflict", "scope shell_profiles must be a list")
    profiles: list[dict[str, str]] = []
    seen: set[str] = set()
    for entry in raw:
        if not isinstance(entry, Mapping):
            _fail("scope-conflict", "a scope shell profile entry is malformed")
        path, shell, bin_dir = entry.get("path"), entry.get("shell"), entry.get("bin")
        if not _is_abs(path) or path in seen:
            _fail("scope-conflict", "scope shell profile paths must be unique absolutes")
        if shell not in _SHELLS:
            _fail(
                "scope-conflict",
                "scope shell profiles are limited to bash/zsh/powershell",
            )
        _validate_bin(bin_dir)
        seen.add(path)
        profiles.append({"path": path, "shell": shell, "bin": bin_dir})
    return profiles


def _scope_decisions(scope: Mapping[str, Any]) -> dict[str, str]:
    raw = scope.get("decisions") or {}
    if not isinstance(raw, Mapping):
        _fail("scope-conflict", "scope decisions must be a mapping")
    decisions: dict[str, str] = {}
    for target, decision in raw.items():
        if not _is_abs(target) or decision not in {"replace", "preserve"}:
            _fail("scope-conflict", "a scope decision entry is malformed")
        decisions[target] = decision
    return decisions


def _package_root(package_root: Path | str | None) -> Path:
    root = Path(package_root) if package_root is not None else Path(__file__).resolve().parents[1]
    if not root.is_absolute():
        _fail("invalid-argument", "the package root must be absolute")
    return root


def _host_runtime(host: Mapping[str, Any]) -> dict[str, str] | None:
    runtime = host["runtime"]
    values = {key: runtime.get(key) for key in ("python", "node", "cli")}
    if any(not _is_abs(value) for value in values.values()):
        return None
    return {key: str(value) for key, value in values.items()}


# ---------------------------------------------------------------------------
# OMP resolver binding (explicit config_home/config, never os.environ)
# ---------------------------------------------------------------------------


def _omp_resolution(host: Mapping[str, Any]) -> tuple[Path, dict[str, str], Path]:
    """Bind the existing resolver to the explicit domain; never guess a profile."""
    from sbtd_omp_sources import active_omp_paths

    config_home = Path(host["config_home"])
    config = Path(host["config"])
    relative = config.relative_to(config_home)
    parts = relative.parts
    environ: dict[str, str] = {"PI_CONFIG_DIR": config_home.name}
    if parts == ("agent", "mcp.json"):
        pass
    elif len(parts) == 4 and parts[0] == "profiles" and parts[2:] == ("agent", "mcp.json"):
        environ["OMP_PROFILE"] = parts[1]
    else:
        _fail(
            "scope-conflict",
            "an OMP host config must be the agent mcp.json of its config_home",
        )
    home = config_home.parent
    resolved = active_omp_paths(home=home, environ=environ)
    if resolved["target"] != config:
        _fail(
            "scope-conflict",
            "the OMP resolver does not reproduce the explicit host config",
        )
    return home, environ, config


# ---------------------------------------------------------------------------
# Managed record extraction and digests (metadata only, never content output)
# ---------------------------------------------------------------------------


def _digest_json(value: Any) -> str:
    return hashlib.sha256(contracts.canonical_json_bytes(value)).hexdigest()


def _toml():
    import tomlkit

    return tomlkit


def _codex_managed(raw: bytes) -> tuple[dict[str, Any] | None, list[str]]:
    """(managed record, legacy key names); record None when absent/unreadable."""
    tomlkit = _toml()
    try:
        document = tomlkit.parse(raw.decode("utf-8"))
        servers = document.unwrap().get("mcp_servers")
    except (ValueError, RecursionError, UnicodeDecodeError):
        return None, []
    if not isinstance(servers, dict):
        return None, []
    record = servers.get(_GLOBAL_SERVER)
    legacy = sorted(key for key in servers if key.startswith(_SERVER_PREFIX))
    return (dict(record) if isinstance(record, dict) else None), legacy


def _omp_managed(raw: bytes) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        document = strict_json_object(raw)
    except (ValueError, TypeError, RecursionError):
        return None, []
    servers = document.get("mcpServers")
    if not isinstance(servers, dict):
        return None, []
    record = servers.get(_GLOBAL_SERVER)
    legacy = sorted(key for key in servers if key.startswith(_SERVER_PREFIX))
    return (dict(record) if isinstance(record, dict) else None), legacy


def _desired_mcp_record(platform: str, bindings: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Desired managed record derived through the existing renderers."""
    if platform == "codex":
        from sbtd_codex_wiring import codex_mcp_candidate

        candidate = codex_mcp_candidate(b"", bindings)
        record, _legacy = _codex_managed(candidate)
        assert record is not None
        return record
    from sbtd_omp_wiring import desired_omp_server

    return dict(desired_omp_server(bindings[0]))


def _managed_digest(platform: str, raw: bytes) -> str | None:
    record, _legacy = (
        _codex_managed(raw) if platform == "codex" else _omp_managed(raw)
    )
    return _digest_json(record) if record is not None else None


# ---------------------------------------------------------------------------
# Ownership-proven upgrade claims (replace path for the owned global entry)
# ---------------------------------------------------------------------------


def _codex_claim(
    before: bytes, bindings: Sequence[Mapping[str, Any]], package_root: Path
) -> bytes:
    """Replace a differing global entry proven to be exactly the owned shape."""
    from sbtd_codex_wiring import _owned_global_server_shape

    def reject() -> NoReturn:
        _fail(
            "ownership-conflict",
            "an existing sbtd-graft MCP entry differs and cannot be claimed",
        )

    tomlkit = _toml()
    try:
        document = tomlkit.parse(before.decode("utf-8"))
        servers = document.get("mcp_servers")
        plain = servers.unwrap() if servers is not None else None
        if not isinstance(plain, dict) or _GLOBAL_SERVER not in plain:
            reject()
        if any(key != _GLOBAL_SERVER and key.startswith(_SERVER_PREFIX) for key in plain):
            reject()
        _owned_global_server_shape(plain[_GLOBAL_SERVER], {str(package_root)})
    except ContractError as error:
        if error.code == "state-conflict":
            reject()
        raise
    except (ValueError, RecursionError, UnicodeDecodeError):
        reject()
    desired = _desired_mcp_record("codex", bindings)
    entry = tomlkit.table()
    entry["command"] = desired["command"]
    entry["args"] = desired["args"]
    env = tomlkit.table()
    for name, value in desired["env"].items():
        env[name] = value
    entry["env"] = env
    servers[_GLOBAL_SERVER] = entry
    try:
        return tomlkit.dumps(document).encode("utf-8")
    except (ValueError, RecursionError):
        _fail("invalid-config", "the rendered TOML candidate cannot be serialized")


def _omp_claim(
    before: bytes,
    bindings: Sequence[Mapping[str, Any]],
    sources: Sequence[Mapping[str, Any]],
    disabled_extensions: Sequence[str],
) -> bytes:
    """Replace a differing active entry proven owned; inherited gates mirrored."""
    from sbtd_omp_wiring import (
        _entry_enabled,
        _equivalent,
        _normalized_inherited,
        _verify_global_omp_entry,
        desired_omp_server,
    )

    def reject() -> NoReturn:
        _fail(
            "ownership-conflict",
            "an active sbtd-graft OMP entry differs and cannot be claimed",
        )

    try:
        document = strict_json_object(before)
        servers = document.get("mcpServers")
        if not isinstance(servers, dict) or _GLOBAL_SERVER not in servers:
            reject()
        if any(name != _GLOBAL_SERVER and name.startswith(_SERVER_PREFIX) for name in servers):
            reject()
        disabled = document.get("disabledServers") or []
        forced = document.get("enabledServers") or []
        if not isinstance(disabled, list) or not isinstance(forced, list):
            reject()
        _verify_global_omp_entry(servers[_GLOBAL_SERVER], set(disabled), set(forced))
        desired = dict(desired_omp_server(bindings[0]))
        blocked_extensions = set(disabled_extensions)
        for source in _normalized_inherited(sources):
            for name, server in source["servers"].items():
                managed = name == _GLOBAL_SERVER or name.startswith(_SERVER_PREFIX)
                if not managed:
                    continue
                if name in set(disabled) or f"mcp:{name}" in blocked_extensions:
                    reject()
                enabled = source["enabled"] and (
                    _entry_enabled(server) or name in set(forced)
                )
                if not enabled or not _equivalent(server, desired):
                    reject()
    except ContractError as error:
        if error.code == "state-conflict":
            reject()
        raise
    except (ValueError, TypeError, RecursionError):
        reject()
    servers[_GLOBAL_SERVER] = desired
    try:
        return contracts.canonical_json_bytes(document)
    except (TypeError, ValueError, RecursionError):
        _fail("invalid-config", "the rendered OMP MCP candidate cannot be serialized")

def _project_paths(roots: Sequence[str]) -> list[Path]:
    paths = [_canonical(Path(root)) for root in roots]
    if any(not path.is_dir() for path in paths):
        _fail("project-root-unavailable", "a selected project configuration root is unavailable")
    return paths



# ---------------------------------------------------------------------------
# MCP render pipeline (shared by build and render_resource)
# ---------------------------------------------------------------------------


def _render_mcp(
    platform: str,
    config: Path,
    before: bytes,
    bindings: Sequence[Mapping[str, Any]],
    *,
    resolution: tuple[Path, dict[str, str], Path] | None,
    package_root: Path,
    project_roots: Sequence[str] = (),
    effective_inputs: list[dict[str, Any]] | None = None,
) -> bytes:
    if platform == "codex":
        from sbtd_codex_wiring import codex_mcp_candidate

        try:
            return codex_mcp_candidate(before, bindings, retire_legacy=False)
        except ContractError as error:
            if error.code != "ownership-conflict":
                raise
            return _codex_claim(before, bindings, package_root)
    from sbtd_omp_sources import discover_omp_sources
    from sbtd_omp_wiring import analyze_omp_configuration, omp_mcp_candidate

    assert resolution is not None
    home, environ, expected = resolution
    if expected != config:
        _fail("scope-conflict", "the OMP resolution does not match the host config")
    discovered = discover_omp_sources(
        _project_paths(project_roots), home=home, environ=environ
    )
    if effective_inputs is not None:
        effective_inputs.extend(discovered["inputs"])
    if discovered["target"] != str(config):
        _fail("scope-conflict", "the OMP resource leaves the active profile")
    target = Path(discovered["target"])
    try:
        analysis = analyze_omp_configuration(
            target,
            bindings,
            discovered["sources"],
            disabled_extensions=discovered["disabled_extensions"],
            retire_legacy=False,
        )
    except ContractError as error:
        if error.code != "ownership-conflict":
            raise
        return _omp_claim(
            before,
            bindings,
            discovered["sources"],
            discovered["disabled_extensions"],
        )
    return omp_mcp_candidate(before, analysis)


# ---------------------------------------------------------------------------
# Shell profile PATH candidate (bytes in, bytes out; arbitrary bytes preserved)
# ---------------------------------------------------------------------------


def _validate_bin(value: Any) -> None:
    if (
        not isinstance(value, str)
        or not os.path.isabs(value)
        or any(char in value for char in ("\0", "\n", "\r"))
    ):
        _fail("invalid-argument", "a managed PATH entry needs a clean absolute bin")


def _quote_posix(value: str) -> str:
    return "'" + _posix_shell_path(value).replace("'", "'\\''") + "'"


def _posix_shell_path(value: str) -> str:
    r"""Git Bash POSIX form of a native absolute path; identity elsewhere.

    A drive-letter colon is the POSIX PATH delimiter, so ``C:\`` and ``C:/``
    entries both split and could never resolve inside a sourced bash/zsh
    profile. The ``/c/...`` alias Git Bash itself assigns to the drive is the
    only form that genuinely resolves there.
    """
    if os.name != "nt":
        return value
    if value.startswith(("\\\\", "//")):
        return value.replace("\\", "/")
    match = re.fullmatch(r"([a-zA-Z]):[\\/](.*)", value)
    if match is None:
        return value
    tail = match.group(2).replace("\\", "/").rstrip("/")
    drive = match.group(1).lower()
    return f"/{drive}/{tail}" if tail else f"/{drive}"


def _resolution_key(value: str) -> str:
    r"""Canonical comparison key for one shell-reported resolution path.

    Git Bash reports ``/c/...`` for what the native selection holds as
    ``C:\...``; both spellings are aliases of the same file, so the key
    folds the POSIX drive alias back to the native form before the usual
    case/separator normalization.
    """
    text = value
    if os.name == "nt":
        match = re.fullmatch(r"/([a-zA-Z])(?:/(.*))?", text)
        if match is not None:
            tail = (match.group(2) or "").replace("/", "\\")
            text = match.group(1).upper() + ":\\" + tail
    return os.path.normcase(os.path.normpath(text))


def _quote_powershell(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _shell_block(shell: str, bin_dir: str, terminator: bytes) -> list[bytes]:
    if shell in {"bash", "zsh"}:
        body = f"export PATH={_quote_posix(bin_dir)}:$PATH"
    else:
        body = (
            f"$env:Path = {_quote_powershell(bin_dir)}"
            " + [IO.Path]::PathSeparator + $env:Path"
        )
    encoded = body.encode("utf-8")
    return [
        _MARKER_START + terminator,
        encoded + terminator,
        _MARKER_END + terminator,
    ]


def _marker_spans(lines: list[bytes]) -> list[tuple[int, int]]:
    events: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        stripped = line.rstrip(b"\r")
        if stripped == _MARKER_START:
            events.append((index, "start"))
        elif stripped == _MARKER_END:
            events.append((index, "end"))
    spans: list[tuple[int, int]] = []
    opened: int | None = None
    for index, kind in events:
        if kind == "start":
            if opened is not None:
                _fail("ownership-conflict", "the managed PATH markers are ambiguous")
            opened = index
            continue
        if opened is None:
            _fail("ownership-conflict", "the managed PATH markers are ambiguous")
        spans.append((opened, index))
        opened = None
    if opened is not None or len(spans) > 1:
        _fail("ownership-conflict", "the managed PATH markers are ambiguous")
    return spans


def _shell_profile_candidate(before: bytes, *, shell: str, bin_dir: str) -> bytes:
    """Idempotent managed PATH block; placed after NVM init lines on insert."""
    if shell not in _SHELLS:
        _fail("invalid-argument", "only bash/zsh/powershell profiles are supported")
    _validate_bin(bin_dir)
    if not isinstance(before, (bytes, bytearray)):
        _fail("invalid-argument", "input document must be bytes")
    raw = bytes(before)
    lines = raw.split(b"\n")
    spans = _marker_spans(lines)
    crlf = any(line.endswith(b"\r") for line in lines)
    terminator = b"\r" if crlf else b""
    block = _shell_block(shell, bin_dir, terminator)
    if spans:
        start, end = spans[0]
        nvm_after = any(
            hint in line for line in lines[end + 1 :] for hint in _NVM_HINTS
        )
        if lines[start + 1 : end] == [block[1]] and not nvm_after:
            return raw
        remaining = lines[:start] + lines[end + 1 :]
    else:
        remaining = lines
    insert_at = len(remaining)
    if insert_at and remaining[-1] == b"":
        insert_at -= 1
    for index, line in enumerate(remaining):
        if any(hint in line for hint in _NVM_HINTS):
            insert_at = max(insert_at, index + 1)
    rendered = b"\n".join(remaining[:insert_at] + block + remaining[insert_at:])
    if not rendered.endswith(b"\n"):
        rendered += b"\n"
    return rendered


def _shell_legacy_lines(raw: bytes, bin_dir: str) -> list[int]:
    needle = bin_dir.encode("utf-8")
    lines = raw.split(b"\n")
    try:
        spans = _marker_spans(lines)
    except ContractError:
        return []
    inside: set[int] = set()
    for start, end in spans:
        inside.update(range(start, end + 1))
    return sorted(
        index + 1
        for index, line in enumerate(lines)
        if index not in inside and needle in line
    )


# ---------------------------------------------------------------------------
# Resource construction
# ---------------------------------------------------------------------------


def _payload_digest(root: Path) -> str:
    from sbtd_upgrade_inventory import _payload_scan

    root = _canonical(root)
    if not root.is_dir():
        _fail("runtime-unavailable", "the trusted Onboard payload root is unavailable")
    return _payload_scan(root)[0]


def _launcher_ref(onboard_root: Path, source_root: Path) -> dict[str, Any]:
    launcher = onboard_root / "scripts" / "sbtd_graft_entry.py"
    desired = snapshot(source_root / "scripts" / "sbtd_graft_entry.py")
    return {"path": str(launcher), "state": snapshot(launcher), "desired": desired}


def _blocked_resource(
    base: dict[str, Any], before: dict[str, Any], details: dict[str, Any], code: str
) -> dict[str, Any]:
    return {
        **base,
        "before": before,
        "desired": None,
        "classification": "identity-conflict",
        "decision": "blocked",
        "details": {**details, "error_code": code},
    }


def _classify(
    before: dict[str, Any],
    before_bytes: bytes,
    rendered: bytes,
    target: str,
    decisions: Mapping[str, str],
) -> tuple[str, str, dict[str, Any] | None]:
    desired = {"type": "file", "checksum": hashlib.sha256(rendered).hexdigest()}
    if rendered == before_bytes:
        return "current", "keep", desired
    if before["type"] == "absent":
        return "missing", "install", desired
    decision = decisions.get(target)
    if decision == "replace":
        return "unknown-drift", "replace", desired
    if decision == "preserve":
        return "unknown-drift", "preserve", None
    return "unknown-drift", "blocked", None


def _build_mcp_resource(
    host: Mapping[str, Any],
    decisions: Mapping[str, str],
    package_root: Path,
) -> dict[str, Any]:
    platform = host["platform"]
    target = host["config"]
    installed_root = Path(host["onboard_root"])
    launcher = _launcher_ref(installed_root, package_root)
    base = {
        "id": contracts.resource_id(_OWNER_KIND, target),
        "kind": "mcp",
        "target": target,
        "source": launcher["path"],
        "host": {
            "id": host["id"],
            "platform": platform,
            "config_home": host["config_home"],
            "config": target,
            "project_roots": list(host["project_roots"]),
            "onboard_root": str(installed_root),
        },
    }
    before = snapshot(Path(target))
    details: dict[str, Any] = {
        "package_root": str(package_root),
        "launcher": launcher,
        "launcher_source": {
            "path": str(package_root / "scripts" / "sbtd_graft_entry.py"),
            "state": launcher["desired"],
        },
        "runtime": host["runtime"],
        "onboard_payload_digest": _payload_digest(package_root),
        "managed_digest": None,
        "before_managed_digest": None,
        "legacy": [],
        "effective_inputs": [],
    }
    runtime = _host_runtime(host)
    if launcher["desired"]["type"] != "file":
        return _blocked_resource(base, before, details, "launcher-source-unavailable")
    if not host["skills_roots"] and (
        launcher["state"] != launcher["desired"]
        or _payload_digest(installed_root) != details["onboard_payload_digest"]
    ):
        return _blocked_resource(base, before, details, "untrusted-onboard-installation")
    if runtime is None:
        return _blocked_resource(base, before, details, "runtime-incomplete")
    if before["type"] not in {"absent", "file"}:
        return _blocked_resource(base, before, details, "invalid-config")
    try:
        before_bytes = b"" if before["type"] == "absent" else read_file(Path(target), before)
        bindings = launch_bindings([], runtime, package_root=installed_root)
        resolution = _omp_resolution(host) if platform == "omp" else None
        desired_record = _desired_mcp_record(platform, bindings)
        details["managed_digest"] = _digest_json(desired_record)
        record, legacy = (
            _codex_managed(before_bytes) if platform == "codex" else _omp_managed(before_bytes)
        )
        details["legacy"] = legacy
        if record is not None:
            details["before_managed_digest"] = _digest_json(record)
        rendered = _render_mcp(
            platform,
            Path(target),
            before_bytes,
            bindings,
            resolution=resolution,
            package_root=installed_root,
            project_roots=host["project_roots"],
            effective_inputs=details["effective_inputs"],
        )
    except ContractError as error:
        if error.code in _PROPAGATE_CODES:
            raise
        return _blocked_resource(base, before, details, error.code)
    classification, decision, desired = _classify(
        before, before_bytes, rendered, target, decisions
    )
    return {
        **base,
        "before": before,
        "desired": desired,
        "classification": classification,
        "decision": decision,
        "details": details,
    }


def _command_identity(bin_dir: Path, shell: str = "powershell") -> dict[str, Any]:
    """Bind only the selected executable; npm executable symlinks are read-only."""
    _canonical(bin_dir)
    names = ("graft",)
    if os.name == "nt":
        names = (
            ("graft", "graft.exe") if shell in {"bash", "zsh"}
            else ("graft.ps1", "graft.exe", "graft.cmd", "graft")
        )
    selected = next(
        (bin_dir / name for name in names if os.path.lexists(bin_dir / name)),
        bin_dir / names[0],
    )
    if not os.path.lexists(selected):
        return {"path": str(selected), "resolved": None, "link": None,
                "state": {"type": "absent", "checksum": None}}
    try:
        link = os.readlink(selected) if selected.is_symlink() else None
        resolved = selected.resolve(strict=True)
    except (OSError, RuntimeError):
        _fail("unsafe-path", "the selected command link cannot be safely resolved")
    state = snapshot(resolved)
    if state["type"] != "file":
        _fail("unsafe-path", "the selected command does not resolve to a regular file")
    return {"path": str(selected), "resolved": str(resolved), "link": link, "state": state}


def _build_shell_resource(
    profile: Mapping[str, str],
    decisions: Mapping[str, str],
    package_root: Path,
) -> dict[str, Any]:
    target = profile["path"]
    shell = profile["shell"]
    bin_dir = profile["bin"]
    base = {
        "id": contracts.resource_id(_OWNER_KIND, target),
        "kind": "shell",
        "target": target,
        "source": bin_dir,
        "profile": {"path": target, "shell": shell, "bin": bin_dir},
    }
    before = snapshot(Path(target))
    block = _shell_block(shell, bin_dir, b"")
    details: dict[str, Any] = {
        "package_root": str(package_root),
        "shell": shell,
        "bin": bin_dir,
        "managed_digest": hashlib.sha256(b"\n".join(block)).hexdigest(),
        "before_managed_digest": None,
        "legacy_lines": [],
        "command_identity": _command_identity(Path(bin_dir), shell),
    }
    if before["type"] not in {"absent", "file"}:
        return _blocked_resource(base, before, details, "invalid-config")
    try:
        before_bytes = b"" if before["type"] == "absent" else read_file(Path(target), before)
        lines = before_bytes.split(b"\n")
        spans = _marker_spans(lines)
        if spans:
            start, end = spans[0]
            details["before_managed_digest"] = hashlib.sha256(
                b"\n".join(lines[start + 1 : end])
            ).hexdigest()
        details["legacy_lines"] = _shell_legacy_lines(before_bytes, bin_dir)
        rendered = _shell_profile_candidate(before_bytes, shell=shell, bin_dir=bin_dir)
    except ContractError as error:
        if error.code in _PROPAGATE_CODES:
            raise
        return _blocked_resource(base, before, details, error.code)
    classification, decision, desired = _classify(
        before, before_bytes, rendered, target, decisions
    )
    return {
        **base,
        "before": before,
        "desired": desired,
        "classification": classification,
        "decision": decision,
        "details": details,
    }


def build_host_resources(
    scope: Mapping[str, Any], *, package_root: Path | str | None = None
) -> list[dict[str, Any]]:
    """Read-only host resource plan; one resource per selected mcp/shell target."""
    if not isinstance(scope, Mapping):
        _fail("scope-conflict", "the upgrade scope must be a JSON object")
    root = _package_root(package_root)
    decisions = _scope_decisions(scope)
    resources: list[dict[str, Any]] = []
    seen_targets: set[str] = set()

    def admit(resource: dict[str, Any]) -> None:
        if resource["target"] in seen_targets:
            _fail("scope-conflict", "host resource targets must be unique")
        seen_targets.add(resource["target"])
        resources.append(resource)

    selected_hosts = _scope_hosts(scope)
    for host in selected_hosts:
        if host["platform"] not in _SUPPORTED_MCP_PLATFORMS:
            continue
        admit(_build_mcp_resource(host, decisions, root))
    for profile in _scope_shell_profiles(scope):
        resource = _build_shell_resource(profile, decisions, root)
        resource["details"]["runtime_cli_targets"] = [
            {"host_id": host["id"], "path": host["runtime"]["cli"]}
            for host in selected_hosts
            if host["platform"] in _SUPPORTED_MCP_PLATFORMS and _is_abs(host["runtime"]["cli"])
        ]
        admit(resource)
    return resources


def render_resource(
    resource: Mapping[str, Any], *, package_root: Path | str | None = None
) -> bytes:
    """Regenerate candidate bytes after revalidating the live before-state."""
    if not isinstance(resource, Mapping):
        _fail("invalid-argument", "a host resource must be a mapping")
    kind = resource.get("kind")
    details = resource.get("details")
    if not isinstance(details, Mapping):
        _fail("invalid-argument", "a host resource is missing its details")
    sealed_root = details.get("package_root")
    if package_root is not None and str(_package_root(package_root)) != sealed_root:
        _fail("invalid-argument", "the package root does not match the sealed resource")
    root = Path(str(sealed_root))
    target = Path(str(resource.get("target")))
    live = snapshot(target)
    if live != resource.get("before"):
        _fail("state-conflict", "the host resource changed before execution")
    before_bytes = b"" if live["type"] == "absent" else read_file(target, live)
    if kind == "shell":
        if _command_identity(Path(str(details["bin"])), str(details["shell"])) != details.get("command_identity"):
            _fail("state-conflict", "the selected shell executable changed")
        return _shell_profile_candidate(
            before_bytes, shell=str(details["shell"]), bin_dir=str(details["bin"])
        )
    if kind != "mcp":
        _fail("invalid-argument", "a host resource kind is not supported")
    launcher = details.get("launcher")
    launcher_source = details.get("launcher_source")
    if (
        not isinstance(launcher_source, Mapping)
        or snapshot(Path(str(launcher_source["path"]))) != launcher_source["state"]
        or not isinstance(launcher, Mapping)
        or snapshot(Path(str(launcher["path"]))) != launcher["desired"]
    ):
        _fail(
            "runtime-unavailable",
            "the canonical installed launcher is missing or has drifted",
        )
    runtime = details.get("runtime")
    if not isinstance(runtime, Mapping) or any(
        not _is_abs(runtime.get(key)) for key in ("python", "node", "cli")
    ):
        _fail("invalid-argument", "a host resource runtime is malformed")
    pins = {key: str(runtime[key]) for key in ("python", "node", "cli")}
    installed_root = Path(str(resource.get("host", {}).get("onboard_root")))
    if (
        _payload_digest(root) != details.get("onboard_payload_digest")
        or _payload_digest(installed_root) != details.get("onboard_payload_digest")
    ):
        _fail("runtime-unavailable", "the trusted installed Onboard payload has drifted")
    bindings = launch_bindings([], pins, package_root=installed_root)
    host = resource.get("host")
    if not isinstance(host, Mapping) or host.get("platform") not in _SUPPORTED_MCP_PLATFORMS:
        _fail("invalid-argument", "a host resource descriptor is malformed")
    platform = str(host["platform"])
    resolution = _omp_resolution(host) if platform == "omp" else None
    observed_inputs: list[dict[str, Any]] = []
    for dependency in details.get("effective_inputs", []):
        if snapshot(Path(dependency["path"])) != dependency["state"]:
            _fail("state-conflict", "an effective host configuration source changed")
    candidate = _render_mcp(
        platform,
        target,
        before_bytes,
        bindings,
        resolution=resolution,
        package_root=installed_root,
        project_roots=host.get("project_roots", []),
        effective_inputs=observed_inputs,
    )
    if platform == "omp" and observed_inputs != details.get("effective_inputs", []):
        _fail("state-conflict", "the effective host source selection changed")
    return candidate


# ---------------------------------------------------------------------------
# Probe transport (isolated spawns; evidence never carries raw output)
# ---------------------------------------------------------------------------


class _ProbeError(Exception):
    def __init__(self, kind: str, reason: str) -> None:
        super().__init__(reason)
        self.kind = kind  # "unavailable" | "failed"
        self.reason = reason


def _spawn(argv: list[str], *, env: Mapping[str, str], cwd: str) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=dict(env),
        cwd=cwd,
        start_new_session=os.name == "posix",
    )


def _which(name: str) -> str | None:
    return shutil.which(name)


class _JsonLines:
    """Newline-delimited JSON-RPC client over one spawned process."""

    def __init__(self, proc: subprocess.Popen[bytes], timeout: float) -> None:
        self._proc = proc
        self._timeout = timeout
        self._next = 0
        self._lines: queue.Queue[bytes | None] = queue.Queue()
        assert proc.stdout is not None
        self._reader = threading.Thread(
            target=self._pump, args=(proc.stdout,), daemon=True
        )
        self._reader.start()

    def _pump(self, stream: Any) -> None:
        try:
            for line in iter(stream.readline, b""):
                self._lines.put(line)
        except (OSError, ValueError):
            pass
        finally:
            self._lines.put(None)

    def _read_line(self, deadline: float) -> bytes:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise _ProbeError("failed", "host-response-timeout")
        try:
            line = self._lines.get(timeout=remaining)
        except queue.Empty:
            raise _ProbeError("failed", "host-response-timeout") from None
        if line is None:
            raise _ProbeError("failed", "host-closed-unexpectedly")
        return line

    def _write(self, payload: Mapping[str, Any]) -> None:
        assert self._proc.stdin is not None
        try:
            self._proc.stdin.write(
                json.dumps(payload, allow_nan=False).encode("utf-8") + b"\n"
            )
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError, ValueError):
            raise _ProbeError("failed", "host-closed-unexpectedly") from None

    def call(self, method: str, params: Mapping[str, Any], *, key: str = "method") -> Any:
        self._next += 1
        request_id: Any = self._next if key == "method" else f"probe-{self._next}"
        payload = (
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
            if key == "method"
            else {"id": request_id, "type": method, **params}
        )
        self._write(payload)
        deadline = time.monotonic() + self._timeout
        while True:
            line = self._read_line(deadline).strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if not isinstance(message, dict) or message.get("id") != request_id:
                continue
            if message.get("error") is not None:
                raise _ProbeError("failed", "host-request-refused")
            if message.get("success") is False:
                raise _ProbeError("failed", "host-request-refused")
            return message.get("result", message.get("data"))

    def notify(self, method: str, params: Mapping[str, Any]) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def close(self) -> int:
        proc = self._proc
        try:
            if proc.stdin is not None:
                proc.stdin.close()
        except OSError:
            pass
        try:
            return proc.wait(timeout=_HOST_SHUTDOWN)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                return proc.wait(timeout=_HOST_SHUTDOWN)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=_HOST_SHUTDOWN)
                return proc.returncode if proc.returncode is not None else -1


def _probe_env(base: Path, extra: Mapping[str, str]) -> dict[str, str]:
    home = base / "home"
    env = {
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": str(home),
        "USERPROFILE": str(home),
        "TMPDIR": str(base),
        "TEMP": str(base),
        "TMP": str(base),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_STATE_HOME": str(home / ".local" / "state"),
        "LANG": "en_US.UTF-8",
        "TERM": "dumb",
        "NO_COLOR": "1",
        "DO_NOT_TRACK": "1",
        "DNT": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "NODE_DISABLE_COMPILE_CACHE": "1",
    }
    if os.name == "nt":
        # Native Windows spawns still need the system roots for process
        # creation and batch-shim resolution; the stripped probe env carries
        # exactly these two, never anything else ambient.
        env["SystemRoot"] = os.environ.get("SystemRoot", r"C:\Windows")
        env["COMSPEC"] = os.environ.get(
            "COMSPEC", r"C:\Windows\System32\cmd.exe"
        )
    env.update(extra)
    return env


def _mcp_handshake(argv: list[str], *, cwd: Path, fixture: Path) -> dict[str, Any]:
    """Real MCP initialize + tools/list against the managed launch argv."""
    try:
        proc = _spawn(argv, env=_probe_env(fixture, {}), cwd=str(cwd))
    except OSError:
        raise _ProbeError("unavailable", "managed-command-unavailable") from None
    rpc = _JsonLines(proc, _HANDSHAKE_TIMEOUT)
    try:
        result = rpc.call(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "sbtd-upgrade-verify", "version": "1"},
            },
        )
        if not isinstance(result, Mapping):
            raise _ProbeError("failed", "protocol-evidence-invalid")
        server_info = result.get("serverInfo")
        version = server_info.get("version") if isinstance(server_info, Mapping) else None
        rpc.notify("notifications/initialized", {})
        listing = rpc.call("tools/list", {})
        tools = listing.get("tools") if isinstance(listing, Mapping) else None
        if not isinstance(tools, list):
            raise _ProbeError("failed", "protocol-evidence-invalid")
        if any(
            not isinstance(tool, Mapping) or not isinstance(tool.get("name"), str)
            for tool in tools
        ):
            raise _ProbeError("failed", "protocol-evidence-invalid")
        names = sorted(tool["name"] for tool in tools)
        return {"tools": names, "server_version": version}
    finally:
        rpc.close()


# ---------------------------------------------------------------------------
# Codex app-server host-load adapter (protocol v2, codex-cli 0.159.x)
# ---------------------------------------------------------------------------

_CODEX_FIXTURE_CONFIG = """\
# Isolated upgrade-probe fixture: no credentials, unreachable loopback model.
check_for_update_on_startup = false
model = "probe-model"
model_provider = "probe-local"
approval_policy = "never"
sandbox_mode = "read-only"

[features]
plugins = false
daemon_auto_start = false

[model_providers.probe-local]
name = "probe-local-unreachable"
base_url = "http://127.0.0.1:9/v1"
env_key = "CODEX_PROBE_DUMMY_API_KEY"
wire_api = "responses"
"""


def _probe_fixture(prefix: str) -> tuple[Path, Path]:
    """(holder, private fixture root) for one isolated probe.

    The holder only reserves a unique name; the fixture root itself is always
    created through ``require_private_directory(create=True)`` — the same
    migration primitive that proves the upgrade vault — so Windows privacy is
    established by its ACL helper at creation, never by a chmod. Descendant
    directories inherit the proven ACL and stay plain single-level creations.
    """
    holder = Path(tempfile.mkdtemp(prefix=prefix)).resolve()
    try:
        return holder, require_private_directory(holder / "fixture", create=True)
    except BaseException:
        shutil.rmtree(holder, ignore_errors=True)
        raise


def _copy_skill_roots(roots: Sequence[str], destinations: Path) -> list[str]:
    """Copy verified no-link trees using the existing nofollow copy primitive.

    ``destinations`` goes through ``require_private_directory(create=True)``:
    a fresh directory is privatized by the ACL helper at creation, while a
    pre-existing path is only ever verified and fails closed when its privacy
    cannot be proven — it is never repaired.
    """
    destinations = require_private_directory(destinations, create=True)
    copies: list[str] = []
    for index, root in enumerate(roots):
        source = Path(root)
        state = snapshot(source)
        if state["type"] == "absent":
            continue
        if state["type"] != "directory":
            _fail("unsafe-path", "a selected Skills root is not a safe directory")
        target = destinations / str(index)
        backup_reference(
            {"path": str(source), "state": state}, target, private_root=destinations
        )
        copies.append(str(target))
    return copies


def _expected_skill_names(roots: Sequence[str]) -> list[str]:
    names: set[str] = set()
    for root in roots:
        path = Path(root)
        if not path.is_dir():
            continue
        try:
            children = sorted(path.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_dir() and (child / "SKILL.md").is_file():
                names.add(child.name)
    return sorted(names)


def _probe_codex(
    executable: str,
    host: Mapping[str, Any],
    bindings: Sequence[Mapping[str, Any]],
    proven_root: Path | None,
) -> dict[str, Any]:
    from sbtd_codex_wiring import codex_mcp_candidate

    if proven_root is None:
        raise _ProbeError("unavailable", "no-proven-project-root")
    holder, fixture = _probe_fixture("sbtd-upgrade-codex-")
    try:
        require_private_directory(fixture / "home", create=True)
        codex_home = fixture / "codex-home"
        codex_home.mkdir(mode=0o700)
        config = codex_mcp_candidate(_CODEX_FIXTURE_CONFIG.encode("utf-8"), bindings)
        quoted = json.dumps(str(proven_root))
        config += f'\n[projects.{quoted}]\ntrust_level = "trusted"\n'.encode()
        (codex_home / "config.toml").write_bytes(config)
        copies = _copy_skill_roots(host["skills_roots"], fixture / "skills-roots")
        expected = _expected_skill_names(copies)
        env = _probe_env(fixture, {"CODEX_HOME": str(codex_home), "CODEX_PROBE_DUMMY_API_KEY": "dummy"})
        try:
            proc = _spawn(
                [executable, "app-server", "--listen", "stdio://"],
                env=env,
                cwd=str(fixture),
            )
        except OSError:
            raise _ProbeError("unavailable", "host-cli-unavailable") from None
        rpc = _JsonLines(proc, _HOST_TIMEOUT)
        try:
            rpc.call(
                "initialize",
                {
                    "clientInfo": {"name": "sbtd-upgrade-verify", "version": "1.0.0"},
                    "capabilities": {"experimentalApi": True},
                },
            )
            rpc.notify("initialized", {})
            thread = rpc.call(
                "thread/start", {"ephemeral": True, "cwd": str(proven_root)}
            )
            thread_id = None
            if isinstance(thread, Mapping):
                node = thread.get("thread")
                if isinstance(node, Mapping):
                    thread_id = node.get("id")
                thread_id = thread_id or thread.get("threadId")
            if not isinstance(thread_id, str):
                raise _ProbeError("failed", "host-thread-unavailable")
            rpc.call("config/mcpServer/reload", {})
            status = rpc.call(
                "mcpServerStatus/list",
                {"threadId": thread_id, "serverName": _GLOBAL_SERVER, "detail": "full"},
            )
            server = _find_server_status(status)
            if copies:
                rpc.call("skills/extraRoots/set", {"extraRoots": copies})
            skills = rpc.call(
                "skills/list", {"cwds": [str(proven_root)], "forceReload": True}
            )
            found_skills, skill_errors = _parse_skills(skills, copies)
            return {
                "reload": "ok",
                "server": server,
                "skills": {"expected": expected, "found": found_skills, "errors": skill_errors},
                "exit": rpc.close(),
            }
        except _ProbeError:
            rpc.close()
            raise
    finally:
        shutil.rmtree(holder, ignore_errors=True)


def _find_server_status(payload: Any) -> dict[str, Any]:
    entries = payload.get("data") if isinstance(payload, Mapping) else None
    if not isinstance(entries, list):
        raise _ProbeError("failed", "protocol-evidence-invalid")
    for entry in entries:
        if isinstance(entry, Mapping) and entry.get("name") == _GLOBAL_SERVER:
            tools = entry.get("tools")
            names = sorted(tools) if isinstance(tools, Mapping) else []
            info = entry.get("serverInfo")
            return {
                "status": entry.get("runtimeStatus"),
                "tools": names,
                "server_version": info.get("version") if isinstance(info, Mapping) else None,
                "tools_error": entry.get("toolsError") is not None,
            }
    raise _ProbeError("failed", "managed-server-not-loaded")


def _parse_skills(payload: Any, copies: Sequence[str]) -> tuple[list[str], int]:
    entries = payload.get("data") if isinstance(payload, Mapping) else None
    if not isinstance(entries, list):
        raise _ProbeError("failed", "protocol-evidence-invalid")
    found: set[str] = set()
    errors = 0
    prefixes = [os.path.normpath(copy) + os.sep for copy in copies]

    def under(path: Any) -> bool:
        return isinstance(path, str) and any(
            os.path.normpath(path).startswith(prefix) for prefix in prefixes
        )

    def walk(value: Any) -> None:
        nonlocal errors
        if isinstance(value, Mapping):
            name = value.get("name")
            if isinstance(name, str) and under(value.get("path")):
                if value.get("enabled") is True:
                    found.add(name)
                else:
                    errors += 1
            if isinstance(value.get("message"), str) and under(value.get("path")):
                errors += 1
            for item in value.values():
                if isinstance(item, (Mapping, list)):
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(entries)
    return sorted(found), errors


def _omp_skill_names(payload: Any, expected: Sequence[str]) -> list[str]:
    """Only exact callable command identities count, never response prose."""
    entries = payload.get("commands") if isinstance(payload, Mapping) else payload
    if not isinstance(entries, list):
        raise _ProbeError("failed", "protocol-evidence-invalid")
    identities: set[str] = set()
    for entry in entries:
        if not isinstance(entry, Mapping) or entry.get("enabled") is False:
            continue
        for key in ("name", "uri"):
            identity = entry.get(key)
            if isinstance(identity, str):
                identities.add(identity)
    return sorted(
        name for name in expected
        if f"skill:{name}" in identities or f"skill://{name}" in identities
    )


# ---------------------------------------------------------------------------
# OMP RPC host-load adapter (omp 18.x headless rpc mode)
# ---------------------------------------------------------------------------

_OMP_FIXTURE_MODELS = """\
providers:
  loopback:
    baseUrl: "http://127.0.0.1:9/v1"
    auth: "none"
    api: "openai-completions"
    models:
      - id: "probe-model"
        contextWindow: 128000
        maxTokens: 8192
"""

_OMP_FIXTURE_CONFIG = """\
modelRoles:
  default: "loopback/probe-model"
startup:
  quiet: true
mcp:
  enableProjectConfig: false
"""

def _omp_projection(
    host: Mapping[str, Any], bindings: Sequence[Mapping[str, Any]],
    home: Path, agent: Path,
) -> str:
    """Preserve the selected effective route, projecting only its managed entry."""
    from sbtd_codex_wiring import codex_mcp_candidate
    from sbtd_omp_sources import discover_omp_sources
    from sbtd_omp_wiring import analyze_omp_configuration, desired_omp_server

    selected_home, environ, target = _omp_resolution(host)
    observed = discover_omp_sources(
        _project_paths(host["project_roots"]),
        home=selected_home, environ=environ,
    )
    analysis = analyze_omp_configuration(
        target, bindings, observed["sources"],
        disabled_extensions=observed["disabled_extensions"],
    )
    matches = analysis["inherited_matches"]
    if analysis["writes"] or analysis["removals"] or not matches:
        raise _ProbeError("failed", "effective-binding-not-aligned")
    route = matches[0]
    name, source = route["name"], route["source"]
    config = _OMP_FIXTURE_CONFIG
    if source == "codex-user":
        destination = home / ".codex" / "config.toml"
        document = _toml().parse(codex_mcp_candidate(b"", bindings).decode("utf-8"))
        if name != _GLOBAL_SERVER:
            entry = document["mcp_servers"].pop(_GLOBAL_SERVER)
            document["mcp_servers"][name] = entry
        content = _toml().dumps(document).encode("utf-8")
        config += 'enabledProviders: ["codex"]\n'
    else:
        destinations = {
            "active": agent / "mcp.json",
            "native-user-alternate": agent / ".mcp.json",
            "claude-user-json": home / ".claude.json",
            "claude-user": home / ".claude" / "mcp.json",
        }
        destination = destinations.get(source)
        if destination is None:
            raise _ProbeError("failed", "effective-route-not-user-wide")
        content = contracts.canonical_json_bytes(
            {"mcpServers": {name: dict(desired_omp_server(bindings[0]))}}
        )
        if source.startswith("claude-"):
            config += 'enabledProviders: ["claude"]\n'
    destination.parent.mkdir(mode=0o700, exist_ok=True)
    destination.write_bytes(content)
    (agent / "config.yml").write_text(config, encoding="utf-8")
    return re.sub(r"[^a-z0-9_]", "_", name.lower())


_OMP_DEVICE = re.compile(r"xd://mcp__[A-Za-z0-9_]+")


def _probe_omp(
    executable: str,
    host: Mapping[str, Any],
    bindings: Sequence[Mapping[str, Any]],
    proven_root: Path | None,
) -> dict[str, Any]:

    if proven_root is None:
        raise _ProbeError("unavailable", "no-proven-project-root")
    holder, fixture = _probe_fixture("sbtd-upgrade-omp-")
    try:
        home = fixture / "home"
        agent = fixture / "agent"
        agent.mkdir(mode=0o700)
        require_private_directory(home, create=True)
        server_identity = _omp_projection(host, bindings, home, agent)
        (agent / "models.yml").write_text(_OMP_FIXTURE_MODELS, encoding="utf-8")
        # _omp_projection wrote the exact provider route's fixture settings.
        copies = _copy_skill_roots(host["skills_roots"], fixture / "skills-roots")
        selected = require_private_directory(agent / "skills", create=True)
        for copy in copies:
            for child in sorted(Path(copy).iterdir()):
                state = snapshot(child)
                destination = selected / child.name
                backup_reference(
                    {"path": str(child), "state": state},
                    destination,
                    private_root=selected,
                )
        expected = _expected_skill_names(copies)
        env = _probe_env(fixture, {"HOME": str(home), "PI_CODING_AGENT_DIR": str(agent)})
        try:
            proc = _spawn(
                [executable, "--mode", "rpc", "--no-ui", "--no-extensions", "--no-rules"],
                env=env,
                cwd=str(proven_root),
            )
        except OSError:
            raise _ProbeError("unavailable", "host-cli-unavailable") from None
        rpc = _JsonLines(proc, _HOST_TIMEOUT)
        try:
            rpc.call("negotiate_protocol", {"protocolVersion": 2}, key="type")
            devices: list[str] = []
            deadline = time.monotonic() + _HOST_TIMEOUT
            while time.monotonic() < deadline:
                state = rpc.call("get_state", {}, key="type")
                blob = json.dumps(state, ensure_ascii=False) if state is not None else ""
                devices = sorted(set(_OMP_DEVICE.findall(blob)))
                if any(
                    device == f"xd://mcp__{server_identity}_{tool}"
                    for device in devices
                    for tool in _PINNED_GRAFT_TOOLS
                ):
                    break
                time.sleep(1.0)
            matched = sorted(
                tool
                for tool in _PINNED_GRAFT_TOOLS
                if f"xd://mcp__{server_identity}_{tool}" in devices
            )
            commands = rpc.call("get_available_commands", {}, key="type")
            found = _omp_skill_names(commands, expected)
            return {
                "reload": "session-connect",
                "server": {"tools": matched, "devices": devices},
                "skills": {"expected": expected, "found": found, "errors": 0},
                "exit": rpc.close(),
            }
        except _ProbeError:
            rpc.close()
            raise
    finally:
        shutil.rmtree(holder, ignore_errors=True)


# ---------------------------------------------------------------------------
# verify_hosts
# ---------------------------------------------------------------------------


def _proven_project_root(host: Mapping[str, Any]) -> Path | None:
    for root in host["project_roots"]:
        candidate = Path(root)
        try:
            validate_project(candidate)
        except ContractError:
            continue
        return candidate
    return None


def _runtime_check(resource: Mapping[str, Any]) -> dict[str, Any]:
    details = resource["details"]
    runtime = details["runtime"]
    if any(not _is_abs(runtime.get(key)) for key in ("python", "node", "cli")):
        return {"status": "unavailable", "reason": "runtime-incomplete"}
    try:
        validate_runtime(Path(str(runtime["node"])), Path(str(runtime["cli"])))
    except ContractError as error:
        status = "unavailable" if error.code == "runtime-missing" else "failed"
        return {"status": status, "reason": error.code}
    interpreter = snapshot(Path(str(runtime["python"])))
    if interpreter["type"] == "absent":
        return {"status": "unavailable", "reason": "runtime-missing"}
    if interpreter["type"] != "file":
        return {"status": "failed", "reason": "invalid-config"}
    return {"status": "verified"}

def _probe_pins(resource: Mapping[str, Any]) -> dict[str, str] | None:
    """Runtime pins for probe spawns; None when the resource is not probeable."""
    details = resource["details"]
    runtime = details["runtime"]
    if resource["decision"] == "blocked" or any(
        not _is_abs(runtime.get(key)) for key in ("python", "node", "cli")
    ):
        return None
    launcher = details.get("launcher")
    if not isinstance(launcher, Mapping) or snapshot(Path(launcher["path"])) != launcher["desired"]:
        return None
    if _payload_digest(Path(resource["host"]["onboard_root"])) != details["onboard_payload_digest"]:
        return None
    return {key: str(runtime[key]) for key in ("python", "node", "cli")}


def _binding_check(host: Mapping[str, Any], resource: Mapping[str, Any]) -> dict[str, Any]:
    details = resource["details"]
    if resource["decision"] == "blocked":
        return {"status": "failed", "reason": details.get("error_code", "blocked")}
    launcher = details["launcher"]
    if snapshot(Path(launcher["path"])) != launcher["desired"]:
        return {"status": "failed", "reason": "installed-launcher-not-aligned"}
    if _payload_digest(Path(host["onboard_root"])) != details["onboard_payload_digest"]:
        return {"status": "failed", "reason": "installed-payload-not-aligned"}
    runtime = {key: str(details["runtime"][key]) for key in ("python", "node", "cli")}
    bindings = launch_bindings([], runtime, package_root=Path(host["onboard_root"]))
    platform = host["platform"]
    desired = _desired_mcp_record(platform, bindings)
    if platform == "omp":
        from sbtd_omp_sources import discover_omp_sources
        from sbtd_omp_wiring import analyze_omp_configuration

        home, environ, target = _omp_resolution(host)
        try:
            observed = discover_omp_sources(
                _project_paths(host["project_roots"]),
                home=home, environ=environ,
            )
            if observed["inputs"] != details.get("effective_inputs", []):
                return {"status": "failed", "reason": "effective-inputs-changed"}
            analysis = analyze_omp_configuration(
                target, bindings, observed["sources"],
                disabled_extensions=observed["disabled_extensions"],
                retire_legacy=False,
            )
        except ContractError as error:
            return {"status": "failed", "reason": error.code}
        if analysis["writes"] or analysis["removals"] or not analysis["inherited_matches"]:
            return {"status": "failed", "reason": "managed-entry-differs"}
        return {
            "status": "verified", "managed_digest": _digest_json(desired),
            "routes": [
                {"source": match["source"], "name": match["name"]}
                for match in analysis["inherited_matches"]
            ],
        }
    target = Path(host["config"])
    live = snapshot(target)
    raw = b"" if live["type"] == "absent" else read_file(target, live)
    record, _legacy = _codex_managed(raw)
    if record is None:
        return {"status": "failed", "reason": "managed-entry-absent"}
    if record != desired:
        return {"status": "failed", "reason": "managed-entry-differs"}
    return {"status": "verified", "managed_digest": _digest_json(record)}


def _protocol_check(host: Mapping[str, Any], resource: Mapping[str, Any]) -> dict[str, Any]:
    pins = _probe_pins(resource)
    if pins is None:
        return {"status": "failed", "reason": "resource-blocked"}
    proven = _proven_project_root(host)
    if proven is None:
        return {"status": "unavailable", "reason": "no-proven-project-root"}
    details = resource["details"]
    argv = [
        pins["python"],
        *_STARTUP_FLAGS,
        str(details["launcher"]["path"]),
        "mcp",
        "--node",
        pins["node"],
        "--entry",
        pins["cli"],
    ]
    try:
        holder, fixture = _probe_fixture("sbtd-upgrade-mcp-")
    except ContractError as error:
        return {"status": "failed", "reason": error.code}
    try:
        require_private_directory(fixture / "home", create=True)
        evidence = _mcp_handshake(argv, cwd=proven, fixture=fixture)
    except _ProbeError as error:
        return {"status": error.kind, "reason": error.reason}
    finally:
        shutil.rmtree(holder, ignore_errors=True)
    tools = evidence.get("tools") or []
    version = evidence.get("server_version")
    if sorted(_PINNED_GRAFT_TOOLS) != tools or version != GRAFT_PINNED_VERSION:
        return {"status": "failed", "reason": "protocol-evidence-mismatch"}
    return {"status": "verified", "tools": tools, "server_version": version}


def _host_load_check(host: Mapping[str, Any], resource: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Real host reload/load plus skills evidence; never fabricated.

    Evidence comes from an isolated HOME carrying only the selected managed
    projection; it is labelled ``isolated-host/selected-projection`` and never
    claims the original GUI, live profile, or existing sessions were loaded.
    """
    platform = host["platform"]
    binary = "codex" if platform == "codex" else "omp"

    def load_result(status: str, reason: str, **extra: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        load = {
            "status": status,
            "reason": reason,
            "evidence_scope": _HOST_LOAD_EVIDENCE_SCOPE,
            **extra,
        }
        return load, {"status": status, "reason": reason}

    executable = host.get("executable") or _which(binary)
    if executable is None:
        return load_result("unavailable", "host-cli-not-found")
    pins = _probe_pins(resource)
    if pins is None:
        return load_result("failed", "resource-blocked")
    bindings = launch_bindings([], pins, package_root=Path(host["onboard_root"]))
    proven = _proven_project_root(host)
    adapter = _probe_codex if platform == "codex" else _probe_omp
    try:
        evidence = adapter(executable, host, bindings, proven)
    except _ProbeError as error:
        return load_result(error.kind, error.reason)
    except ContractError as error:
        return load_result("failed", error.code)
    server = evidence["server"]
    tools = server.get("tools") or []
    mcp_ok = sorted(_PINNED_GRAFT_TOOLS) == sorted(tools) and (
        platform != "codex"
        or (
            server.get("status") == "connected"
            and server.get("server_version") == GRAFT_PINNED_VERSION
            and not server.get("tools_error")
        )
    )
    skills = evidence["skills"]
    skills_ok = skills["errors"] == 0 and sorted(skills["expected"]) == sorted(skills["found"])
    load = {
        "status": "verified" if mcp_ok and evidence.get("exit") == 0 else "failed",
        "reload": evidence.get("reload"),
        "evidence_scope": _HOST_LOAD_EVIDENCE_SCOPE,
        "tools": sorted(name for name in tools if name in _PINNED_GRAFT_TOOLS),
        "exit": evidence.get("exit"),
    }
    if not mcp_ok:
        load["reason"] = "host-load-evidence-mismatch"
    elif evidence.get("exit") != 0:
        load["reason"] = "host-exit-nonzero"
    skill_status = {
        "status": "verified" if skills_ok else "failed",
        "skills": sorted(name for name in skills["found"] if name in skills["expected"]),
    }
    if not skills_ok:
        skill_status["expected"] = sorted(skills["expected"])
        skill_status["reason"] = "skills-evidence-mismatch"
    return load, skill_status


def _worst(checks: Iterable[Mapping[str, Any]]) -> str:
    statuses = [check["status"] for check in checks]
    for token in ("failed", "unavailable"):
        if token in statuses:
            return token
    if all(status == "verified" for status in statuses):
        return "verified"
    return "unverified"


def _disk_status(resource: Mapping[str, Any]) -> dict[str, Any]:
    details = resource["details"]
    mapping = {
        "current": "aligned",
        "missing": "missing",
        "unknown-drift": "drifted",
        "identity-conflict": "blocked",
    }
    return {
        "status": mapping[resource["classification"]],
        "target": resource["target"],
        "decision": resource["decision"],
        "managed_digest": details.get("managed_digest"),
        "before_managed_digest": details.get("before_managed_digest"),
        **(
            {"reason": details["error_code"]}
            if details.get("error_code")
            else {}
        ),
    }


def _legacy_mcp(host: Mapping[str, Any]) -> dict[str, Any]:
    target = Path(host["config"])
    live = snapshot(target)
    if live["type"] != "file":
        return {"status": "none", "entries": []}
    try:
        raw = read_file(target, live)
        _record, legacy = (
            _codex_managed(raw) if host["platform"] == "codex" else _omp_managed(raw)
        )
    except ContractError as error:
        return {"status": "unknown", "reason": error.code}
    if _record is None and not legacy and raw.strip():
        return {"status": "unknown", "reason": "invalid-config"}
    return {
        "status": "present" if legacy else "none",
        "entries": legacy,
    }


def _verify_mcp_host(
    host: Mapping[str, Any], resource: Mapping[str, Any], probe: bool
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id": host["id"],
        "platform": host["platform"],
        "applicability": "supported",
        "disk": _disk_status(resource),
        "legacy": _legacy_mcp(host),
    }
    if not probe:
        entry["runtime"] = {"status": "unverified"}
        entry["host"] = {"status": "unverified"}
        entry["status"] = (
            "fail" if entry["disk"]["status"] in {"drifted", "missing", "blocked"} else "unverified"
        )
        return entry
    runtime = _runtime_check(resource)
    binding = _binding_check(host, resource)
    protocol = _protocol_check(host, resource)
    load, skills = _host_load_check(host, resource)
    host_status = _worst((binding, protocol, load, skills))
    entry["runtime"] = runtime
    entry["host"] = {
        "status": host_status,
        "live_reload": dict(_LIVE_RELOAD),
        "checks": {
            "binding": binding,
            "protocol": protocol,
            "host_load": load,
            "skills": skills,
        },
    }
    if (
        entry["disk"]["status"] in {"drifted", "missing", "blocked"}
        or runtime["status"] == "failed"
        or host_status == "failed"
    ):
        entry["status"] = "fail"
    elif runtime["status"] == "unavailable" or host_status == "unavailable":
        entry["status"] = "unavailable"
    elif runtime["status"] == "verified" and host_status == "verified":
        entry["status"] = "pass"
    else:
        entry["status"] = "unverified"
    return entry


def _shell_resolution(
    profile: Mapping[str, str], details: Mapping[str, Any],
) -> dict[str, Any]:
    """Parse and load the selected profile in an isolated shell; resolve graft."""
    shell = profile["shell"]
    bin_dir = _canonical(Path(profile["bin"]))
    if not bin_dir.exists():
        return {"status": "unavailable", "reason": "bin-missing"}
    if not bin_dir.is_dir():
        return {"status": "failed", "reason": "bin-not-a-directory"}
    identity = _command_identity(bin_dir, shell)
    if identity != details.get("command_identity"):
        return {"status": "failed", "reason": "selected-executable-changed"}
    executable = _which(shell if shell != "powershell" else "pwsh")
    if executable is None and shell == "powershell":
        executable = _which("powershell")
    if executable is None:
        return {"status": "unavailable", "reason": "shell-cli-not-found"}
    target = Path(profile["path"])
    before = snapshot(target)
    if before["type"] != "file":
        return {"status": "failed", "reason": "profile-missing"}
    with tempfile.TemporaryDirectory(prefix="sbtd-upgrade-shell-") as directory:
        holder = Path(directory).resolve()
        try:
            fixture = require_private_directory(holder / "fixture", create=True)
        except ContractError as error:
            return {"status": "failed", "reason": error.code}
        require_private_directory(fixture / "home", create=True)
        selected = fixture / ("profile.ps1" if shell == "powershell" else "profile")
        selected.write_bytes(read_file(target, before))
        env = _probe_env(fixture, {"PATH": os.defpath, "SBTD_PROBE_PROFILE": str(selected)})
        if shell in {"bash", "zsh"}:
            env["HOME"] = _posix_shell_path(env["HOME"])
            env["SBTD_PROBE_PROFILE"] = _posix_shell_path(str(selected))
            if os.name == "nt":
                env["PATH"] = "/usr/bin:/bin"
        marker = "SBTD_RESOLVED_GRAFT="
        if shell == "powershell":
            script = (
                "$e=$null;$t=$null;"
                "[void][System.Management.Automation.Language.Parser]::ParseFile("
                "$env:SBTD_PROBE_PROFILE,[ref]$t,[ref]$e);"
                "if($e.Count){exit 41};"
                "try { . $env:SBTD_PROBE_PROFILE; "
                "$p=(Get-Command graft -CommandType Application,ExternalScript -ErrorAction Stop).Source;"
                f"[Console]::Out.WriteLine('{marker}'+$p)"
                " } catch {exit 42}"
            )
            argv = [executable, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script]
        else:
            syntax = [executable, "-n", _posix_shell_path(str(selected))]
            try:
                parsed = subprocess.run(
                    syntax, cwd=fixture, env=env, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, timeout=15, check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                return {"status": "unavailable", "reason": "shell-parse-unavailable"}
            if parsed.returncode != 0:
                return {"status": "failed", "reason": "profile-syntax-invalid"}
            script = (
                '. "$SBTD_PROBE_PROFILE" >/dev/null 2>&1 || exit 41; '
                'p=$(command -v graft) || exit 42; '
                f"printf '{marker}%s\\n' \"$p\""
            )
            flags = ["--noprofile", "--norc"] if shell == "bash" else ["-f"]
            argv = [executable, *flags, "-c", script]
        try:
            result = subprocess.run(
                argv, cwd=fixture, env=env, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, timeout=15, check=False,
            )
        except OSError:
            return {"status": "unavailable", "reason": "shell-launch-unavailable"}
        except subprocess.TimeoutExpired:
            return {"status": "failed", "reason": "shell-probe-timeout"}
        if result.returncode != 0:
            reason = "profile-load-failed" if result.returncode == 41 else "graft-not-resolved"
            return {"status": "failed", "reason": reason}
        resolutions = [
            line[len(marker):] for line in result.stdout.decode("utf-8", errors="replace").splitlines()
            if line.startswith(marker)
        ]
        expected = {_resolution_key(str(bin_dir / name)) for name in
                    ("graft", "graft.exe", "graft.cmd", "graft.ps1")}
        if len(resolutions) != 1 or _resolution_key(resolutions[0]) not in expected:
            return {"status": "failed", "reason": "graft-resolution-mismatch"}
        identity = _command_identity(bin_dir, shell)
        if identity["resolved"] is None or identity["state"]["type"] != "file":
            return {"status": "failed", "reason": "graft-not-an-ordinary-file"}
        reported = _resolution_key(resolutions[0])
        selected_key = _resolution_key(identity["path"])
        if reported != selected_key:
            stem, suffix = os.path.splitext(selected_key)
            unique_suffix_alias = (
                os.name == "nt"
                and suffix in {".exe", ".cmd", ".ps1"}
                and reported == stem
                and not os.path.lexists(stem)
                and sum(os.path.lexists(stem + ext) for ext in (".exe", ".cmd", ".ps1")) == 1
            )
            if not unique_suffix_alias:
                return {"status": "failed", "reason": "graft-resolution-mismatch"}
        pinned = details.get("runtime_cli_targets", [])
        if pinned and not any(
            str(Path(item["path"]).resolve()) == identity["resolved"] for item in pinned
        ):
            return {"status": "failed", "reason": "graft-runtime-binding-mismatch"}
        return {
            "status": "verified", "command": "graft",
            "runtime_binding": "matched" if pinned else "not-selected",
            "evidence_scope": "isolated-shell/selected-profile",
        }


def _verify_shell_profile(
    profile: Mapping[str, str], resource: Mapping[str, Any], probe: bool
) -> dict[str, Any]:
    details = resource["details"]
    disk = _disk_status(resource)
    legacy_lines = details.get("legacy_lines") or []
    entry: dict[str, Any] = {
        "path": profile["path"],
        "shell": profile["shell"],
        "applicability": "supported",
        "disk": disk,
        "runtime": {"status": "not-applicable"},
        "legacy": {
            "status": "present" if legacy_lines else "none",
            "lines": legacy_lines,
        },
    }
    if not probe:
        entry["host"] = {"status": "unverified"}
        entry["status"] = (
            "fail" if disk["status"] in {"drifted", "missing", "blocked"} else "unverified"
        )
        return entry
    resolution = _shell_resolution(profile, details)
    entry["host"] = {
        "status": resolution["status"],
        "checks": {"command_resolution": resolution},
        "live_reload": {
            "status": "unverified",
            "reason": "existing-sessions-not-reloaded",
        },
    }
    if disk["status"] in {"drifted", "missing", "blocked"} or resolution["status"] == "failed":
        entry["status"] = "fail"
    elif resolution["status"] == "unavailable":
        entry["status"] = "unavailable"
    else:
        entry["status"] = "pass"
    return entry


def verify_hosts(
    scope: Mapping[str, Any], *, package_root: Path | str | None = None, probe: bool = False
) -> dict[str, Any]:
    """Per-domain disk/runtime/host/legacy status; probe adds real evidence."""
    root = _package_root(package_root)
    resources = {
        resource["target"]: resource
        for resource in build_host_resources(scope, package_root=root)
    }
    result: dict[str, Any] = {"probe": bool(probe), "hosts": [], "shell_profiles": []}
    for host in _scope_hosts(scope):
        if host["platform"] not in _SUPPORTED_MCP_PLATFORMS:
            result["hosts"].append(
                {
                    "id": host["id"],
                    "platform": host["platform"],
                    "applicability": "unsupported",
                    "status": "unsupported",
                    "disk": {"status": "not-applicable"},
                    "runtime": {"status": "not-applicable"},
                    "host": {"status": "not-applicable"},
                    "legacy": {"status": "not-applicable"},
                }
            )
            continue
        result["hosts"].append(_verify_mcp_host(host, resources[host["config"]], probe))
    for profile in _scope_shell_profiles(scope):
        result["shell_profiles"].append(
            _verify_shell_profile(profile, resources[profile["path"]], probe)
        )
    return result
