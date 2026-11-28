r"""Upgrade host domains without Graft installation or Graft process launch.

Planning is read-only. Codex uses only ``config_home/config.toml`` and the
explicit sibling ``hooks.json``. OMP uses only the already-resolved config
path in the scope. No HOME, profile, or account scan. Shell profiles are
validated and are not rewritten. The launcher file is not a required asset.

``verify_hosts(..., probe=True)`` spawns the selected Codex or OMP CLI in an
isolated fixture and checks that host's own protocol and Skills. It never
starts Graft, never puts ``graft`` on PATH, and never loads a retained
config that still registers the old server. That case is a refusal.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import queue
import shutil
import stat
import subprocess
import tempfile
import threading
import time
import warnings
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import onboard_contracts as contracts
from onboard_contracts import ContractError
from sbtd_migration_files import (
    _canonical,
    _is_reparse,
    _lstat,
    backup_reference,
    read_file,
    require_private_directory,
    snapshot,
)

__all__ = [
    "build_host_resources",
    "plan_retirement",
    "render_resource",
    "verify_hosts",
]

_SUPPORTED = frozenset({"codex", "omp"})
_SHELLS = frozenset({"bash", "zsh", "powershell"})
_OWNER_KIND = "upgrade-retirement"
_HISTORY_DIRS = frozenset({"graft", ".graft"})
_DISCLOSURE = (
    "Removing a host configuration entry affects every project that uses "
    "this host account. The displayed plan is the confirmation for that "
    "global effect. Entries without write authority are not deleted by name."
)
_HOST_TIMEOUT = 150.0
_HOST_SHUTDOWN = 10.0
_HOST_LOAD_EVIDENCE_SCOPE = "isolated-host/selected-projection"
_LIVE_RELOAD = {"status": "unverified", "reason": "original-domain-not-authorized"}
_REMOVED_SERVER = "sbtd-graft"
_REMOVED_LAUNCHER = "sbtd_graft_entry.py"


def validate_project(root: Path) -> dict[str, Any]:
    """Prove a selected project root is a real directory. Does not build a graph."""
    if _directory_or_absent(str(root)) != "directory":
        _fail("unsafe-path", "a selected project root does not exist")
    return {"root": str(root)}


def validate_runtime(node: Path, cli: Path) -> dict[str, Any]:
    """Probe-double seam. Does not launch a runtime or accept a Graft pin."""
    for item in (node, cli):
        if not isinstance(item, (str, Path)) or not os.path.isabs(str(item)):
            _fail("invalid-argument", "a runtime path must be absolute")
    return {"node": str(node), "cli": str(cli)}


class _ProbeError(Exception):
    def __init__(self, kind: str, reason: str) -> None:
        super().__init__(reason)
        self.kind = kind
        self.reason = reason


def _spawn(argv: list[str], *, env: Mapping[str, str], cwd: str) -> subprocess.Popen[bytes]:
    if _argv_invokes_removed_runtime(argv):
        raise _ProbeError("failed", "unsafe-registered-server")
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


def _argv_invokes_removed_runtime(argv: Sequence[str]) -> bool:
    for item in argv:
        name = Path(item).name.lower()
        if name in {"graft", "graft.exe", "graft.cmd", "graft.ps1"}:
            return True
        folded = item.lower()
        if _REMOVED_LAUNCHER in folded or _REMOVED_SERVER in folded:
            return True
    return False


class _JsonLines:
    """Newline-delimited JSON-RPC client over one spawned process."""

    def __init__(self, proc: subprocess.Popen[bytes], timeout: float, *, require_jsonrpc: bool = False) -> None:
        self._proc = proc
        self._timeout = timeout
        self._require_jsonrpc = require_jsonrpc
        self._next = 0
        self._lines: queue.Queue[bytes | None] = queue.Queue()
        self._outbox: queue.Queue[tuple[bytes, threading.Event, list[BaseException]] | None] = queue.Queue()
        self._writer_done = threading.Event()
        assert proc.stdout is not None
        self._reader = threading.Thread(target=self._pump, args=(proc.stdout,), daemon=True)
        self._reader.start()
        self._writer = threading.Thread(target=self._drain, daemon=True)
        self._writer.start()

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

    def _drain(self) -> None:
        while True:
            item = self._outbox.get()
            if item is None:
                self._writer_done.set()
                return
            data, done, errors = item
            try:
                assert self._proc.stdin is not None
                self._proc.stdin.write(data)
                self._proc.stdin.flush()
            except (BrokenPipeError, OSError, ValueError) as exc:
                errors.append(exc)
            finally:
                done.set()

    def _write(self, payload: Mapping[str, Any], deadline: float) -> None:
        data = json.dumps(payload, allow_nan=False).encode("utf-8") + b"\n"
        done = threading.Event()
        errors: list[BaseException] = []
        self._outbox.put((data, done, errors))
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not done.wait(remaining):
            raise _ProbeError("failed", "host-response-timeout")
        if errors:
            raise _ProbeError("failed", "host-closed-unexpectedly") from None

    def call(self, method: str, params: Mapping[str, Any], *, key: str = "method") -> Any:
        self._next += 1
        request_id: Any = self._next if key == "method" else f"probe-{self._next}"
        payload = (
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
            if key == "method"
            else {"id": request_id, "type": method, **params}
        )
        deadline = time.monotonic() + self._timeout
        self._write(payload, deadline)
        while True:
            line = self._read_line(deadline).strip()
            if not line:
                continue
            try:
                message = json.loads(line, parse_float=Decimal)
            except (ValueError, InvalidOperation):
                continue
            # JSON Number echoes may use a different spelling, but bool is
            # not a Number and rounding must not turn a fractional ID into ours.
            id_types = (int, Decimal) if type(request_id) is int else (str,)
            if (
                not isinstance(message, dict)
                or type(message.get("id")) not in id_types
                or message["id"] != request_id
            ):
                continue
            if self._require_jsonrpc and message.get("jsonrpc") != "2.0":
                raise _ProbeError("failed", "host-invalid-envelope")
            if key != "method":
                if message.get("type") != "response" or message.get("command") != method:
                    continue
                if message.get("success") is not True:
                    raise _ProbeError("failed", "host-request-refused")
                return message.get("data")
            if "error" in message:
                error = message["error"]
                if "result" in message or not isinstance(error, Mapping):
                    raise _ProbeError("failed", "protocol-evidence-invalid")
                if type(error.get("code")) is int and error["code"] == -32601:
                    raise _ProbeError("unsupported", "host-method-unsupported")
                raise _ProbeError("failed", "host-request-refused")
            if message.get("success") is False:
                raise _ProbeError("failed", "host-request-refused")
            if "result" not in message:
                raise _ProbeError("failed", "protocol-evidence-invalid")
            return message["result"]

    def notify(self, method: str, params: Mapping[str, Any]) -> None:
        self._write(
            {"jsonrpc": "2.0", "method": method, "params": params},
            time.monotonic() + self._timeout,
        )

    @staticmethod
    def _close_pipe(stream: Any) -> None:
        if stream is not None and not getattr(stream, "closed", False):
            try:
                stream.close()
            except (OSError, ValueError):
                pass

    def close(self) -> int:
        proc = self._proc
        self._outbox.put(None)
        graceful = self._writer_done.wait(0.5)
        if graceful:
            self._close_pipe(proc.stdin)
        else:
            try:
                proc.terminate()
            except OSError:
                pass
        try:
            code = proc.wait(timeout=_HOST_SHUTDOWN)
        except subprocess.TimeoutExpired:
            graceful = False
            try:
                proc.kill()
            except OSError:
                pass
            try:
                code = proc.wait(timeout=_HOST_SHUTDOWN)
            except subprocess.TimeoutExpired:
                code = proc.returncode if proc.returncode is not None else -1
        # Do not close a buffered stream while its thread holds the I/O lock.
        incomplete = False
        for worker, stream in ((self._writer, proc.stdin), (self._reader, proc.stdout)):
            worker.join(timeout=_HOST_SHUTDOWN)
            if worker.is_alive():
                incomplete = True
            else:
                self._close_pipe(stream)
        if incomplete:
            warnings.warn(
                "host probe cleanup incomplete; I/O workers have not stopped",
                RuntimeWarning,
                stacklevel=2,
            )
            return code or -1
        return code if graceful else (code or -1)


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
        env["SystemRoot"] = os.environ.get("SystemRoot", r"C:\Windows")
        env["COMSPEC"] = os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe")
    env.update(extra)
    return env


def _probe_fixture(prefix: str) -> tuple[Path, Path]:
    holder = Path(tempfile.mkdtemp(prefix=prefix)).resolve()
    try:
        return holder, require_private_directory(holder / "fixture", create=True)
    except BaseException:
        shutil.rmtree(holder, ignore_errors=True)
        raise


def _root_entries(source: Path) -> list[tuple[str, str]]:
    try:
        with os.scandir(source) as listing:
            children = list(listing)
    except OSError:
        _fail("read-failed", "directory entry cannot be inspected")
    entries: list[tuple[str, str]] = []
    for child in children:
        try:
            info = child.stat(follow_symlinks=False)
        except OSError:
            _fail("read-failed", "directory entry cannot be inspected")
        if stat.S_ISLNK(info.st_mode):
            kind = "link"
        elif _is_reparse(info):
            kind = "other"
        elif stat.S_ISDIR(info.st_mode):
            kind = "directory"
        elif stat.S_ISREG(info.st_mode):
            kind = "file"
        else:
            kind = "other"
        entries.append((child.name, kind))
    entries.sort(key=lambda entry: entry[0])
    return entries


def _link_outcome(entry: Mapping[str, Any], status: str) -> dict[str, Any]:
    payload = entry["payload"]
    return {
        "authorization_id": entry["authorization_id"],
        "host_id": payload["host_id"],
        "skill_name": payload["skill_name"],
        "skill_path": payload["skill_path"],
        "target": dict(payload["target"]),
        "state_checksum": payload["state"]["checksum"],
        "status": status,
    }


def _copy_mixed_root(
    source: Path,
    target: Path,
    pre: Sequence[tuple[str, str]],
    authorized: Mapping[str, Mapping[str, Any]],
    destinations: Path,
    outcomes: list[dict[str, Any]] | None,
) -> None:
    from sbtd_probe_links import _validate_live, materialize_authorized_skill

    if any(kind == "other" for _name, kind in pre):
        _fail("unsafe-path", "directory contains a link or special entry")
    plain: dict[str, dict[str, Any]] = {}
    payloads: dict[str, Mapping[str, Any]] = {}
    for name, kind in pre:
        child = source / name
        if kind == "link":
            payload = authorized[os.path.normpath(str(child))]["payload"]
            _validate_live(payload)
            payloads[name] = payload
        else:
            plain[name] = snapshot(child)
    try:
        os.mkdir(target, 0o700)
    except OSError:
        _fail("write-failed", "directory copy target cannot be created")
    for name, kind in pre:
        child = source / name
        if kind == "link":
            materialize_authorized_skill(
                payloads[name], destination=target / name, private_root=destinations
            )
            if outcomes is not None:
                outcomes.append(
                    _link_outcome(authorized[os.path.normpath(str(child))], "materialized")
                )
        else:
            backup_reference(
                {"path": str(child), "state": plain[name]},
                target / name,
                private_root=destinations,
            )
    if _root_entries(source) != pre:
        _fail("state-conflict", "a selected Skills root changed during the probe copy")
    for name, state in plain.items():
        if snapshot(source / name) != state:
            _fail("state-conflict", "a selected Skill changed during the probe copy")
    for payload in payloads.values():
        _validate_live(payload)


def _copy_skill_roots(
    roots: Sequence[str],
    destinations: Path,
    *,
    link_authorizations: Sequence[Mapping[str, Any]] | None = None,
    outcomes: list[dict[str, Any]] | None = None,
) -> list[str]:
    destinations = require_private_directory(destinations, create=True)
    authorized: dict[str, Mapping[str, Any]] = {}
    for entry in link_authorizations or []:
        key = os.path.normpath(str(entry["payload"]["skill_path"]))
        if key in authorized:
            _fail("authorization-conflict", "duplicate link authorizations for one Skill path")
        authorized[key] = entry
    from sbtd_probe_links import _validate_live

    copies: list[str] = []
    for index, root in enumerate(roots):
        source = _canonical(Path(root))
        for entry in authorized.values():
            if Path(entry["payload"]["skill_path"]).parent == source:
                _validate_live(entry["payload"])
        info = _lstat(source)
        if info is None:
            _fail("skills-root-missing", "a selected Skills root is absent")
        if _is_reparse(info) or not stat.S_ISDIR(info.st_mode):
            _fail("unsafe-path", "a selected Skills root is not a safe directory")
        target = destinations / str(index)
        entries = _root_entries(source)
        linked = [name for name, kind in entries if kind == "link"]
        if not linked:
            state = snapshot(source)
            if state["type"] == "absent":
                _fail("state-conflict", "a selected Skills root disappeared during the probe copy")
            if state["type"] != "directory":
                _fail("unsafe-path", "a selected Skills root is not a safe directory")
            backup_reference(
                {"path": str(source), "state": state}, target, private_root=destinations
            )
        else:
            if any(os.path.normpath(str(source / name)) not in authorized for name in linked):
                _fail("unsafe-path", "a selected Skills root contains an unauthorized link")
            _copy_mixed_root(source, target, entries, authorized, destinations, outcomes)
        copies.append(str(target))
    return copies


def _expected_skill_names(roots: Sequence[str], *, required: Sequence[str] = ()) -> list[str]:
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
    if not set(required).issubset(names):
        _fail("skill-identity-unproven", "an authorized Skill is missing from the probe projection")
    return sorted(names)



def _fail(code: str, message: str) -> Any:
    raise ContractError(code, message)


def _is_abs(value: Any) -> bool:
    return isinstance(value, str) and os.path.isabs(value) and "\0" not in value


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not _is_abs(item) for item in value):
        _fail("scope-conflict", f"scope {label} must be absolute path strings")
    return list(value)


def _posix_shell_path(value: str) -> str:
    """Git Bash form of a native path. A drive-letter colon splits POSIX PATH."""
    if value.startswith(("\\\\", "//")):
        return value.replace("\\", "/")
    if len(value) >= 2 and value[0].isalpha() and value[1] == ":":
        tail = value[2:].replace("\\", "/").lstrip("/").rstrip("/")
        drive = value[0].lower()
        return f"/{drive}/{tail}" if tail else f"/{drive}"
    return value


def _validate_bin(value: Any, shell: str = "") -> None:
    if (
        not isinstance(value, str)
        or not os.path.isabs(value)
        or any(char in value for char in ("\0", "\n", "\r"))
    ):
        _fail("invalid-argument", "a managed PATH entry needs a clean absolute bin")
    if os.name == "nt":
        if shell == "powershell" and ";" in value:
            _fail("unsafe-path", "the managed PATH entry cannot be represented in a PowerShell PATH")
        if shell in {"bash", "zsh"} and ":" in _posix_shell_path(value):
            _fail("unsafe-path", "the managed PATH entry cannot be represented in a POSIX shell PATH")
    elif ":" in value:
        _fail("unsafe-path", "the managed PATH entry cannot be represented in a POSIX PATH")


def _same_file_entry(left: Path, right: Path) -> bool:
    """Only existing case aliases of a single directory entry compare equal."""
    if str(left) == str(right):
        return True
    if str(left).casefold() != str(right).casefold():
        return False
    first, second = (_lstat(_canonical(path)) for path in (left, right))
    return (
        first is not None and second is not None
        and stat.S_ISREG(first.st_mode) and stat.S_ISREG(second.st_mode)
        and first.st_ino != 0 and first.st_nlink == second.st_nlink == 1
        and os.path.samestat(first, second)
    )


def _canonical_host_scope(scope: dict[str, Any]) -> dict[str, Any]:
    """Seal the effective config spelling while its alias can still be proven."""
    raw = scope["hosts"]
    hosts = _scope_hosts(scope)
    aliases = {
        declared["config"]: host["config"]
        for declared, host in zip(raw, hosts, strict=True)
        if declared["config"] != host["config"]
    }
    if not aliases:
        return scope
    decisions: dict[str, str] = {}
    for target, decision in _scope_decisions(scope).items():
        target = aliases.get(target, target)
        if decisions.setdefault(target, decision) != decision:
            _fail("decision-conflict", "different decisions name one selected host config")
    return {
        **scope,
        "hosts": [{**declared, "config": host["config"]} for declared, host in zip(raw, hosts, strict=True)],
        "decisions": decisions,
    }


def _scope_hosts(scope: Mapping[str, Any]) -> list[dict[str, Any]]:
    from sbtd_upgrade_inventory import normalize_host_platform

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
        platform = normalize_host_platform(platform)
        ids.add(host_id)
        home_path = Path(config_home)
        config_path = Path(config)
        if platform == "codex":
            canonical_config = home_path / "config.toml"
            if not _same_file_entry(config_path, canonical_config):
                _fail("scope-conflict", "Codex config must be config_home/config.toml")
            config = str(canonical_config)
        elif config_path == home_path or not config_path.is_relative_to(home_path):
            _fail("scope-conflict", "a scope host config must live inside its config_home")
        skills_roots = _string_list(entry.get("skills_roots") or [], "host skills_roots")
        if any(os.path.normpath(item) not in top_roots for item in skills_roots):
            _fail("scope-conflict", "a scope host skills root is not a selected top-level root")
        runtime = entry.get("runtime")
        if not isinstance(runtime, Mapping) or set(runtime) != {"python", "node", "cli"}:
            _fail("scope-conflict", "a scope host runtime must name python/node/cli")
        executable = entry.get("executable")
        if executable is not None and not _is_abs(executable):
            _fail("scope-conflict", "a scope host executable must be absolute")
        onboard_root = entry.get("onboard_root")
        if onboard_root is not None and not _is_abs(onboard_root):
            _fail("scope-conflict", "a scope host onboard_root must be absolute")
        hosts.append(
            {
                "id": host_id,
                "platform": platform,
                "config_home": config_home,
                "config": config,
                "skills_roots": skills_roots,
                "runtime": {key: runtime.get(key) for key in ("python", "node", "cli")},
                "project_roots": _string_list(entry.get("project_roots") or [], "host project_roots"),
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
            _fail("scope-conflict", "scope shell profiles are limited to bash/zsh/powershell")
        _validate_bin(bin_dir, shell)
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


def _retirement():
    try:
        return importlib.import_module("sbtd_retirement")
    except ImportError as error:
        raise ContractError(
            "retirement-unavailable", "the retirement module is not importable"
        ) from error


def _history_names() -> frozenset[str]:
    module = _retirement()
    names = getattr(module, "HISTORY_DIRS", _HISTORY_DIRS)
    if isinstance(names, (str, bytes)) or not isinstance(names, (tuple, list, frozenset, set)):
        return _HISTORY_DIRS
    return frozenset(str(name) for name in names)


def _protected_history(path: str) -> bool:
    return any(part in _history_names() for part in Path(path).parts)


def _regular_or_absent(path: str) -> str:
    """Inspect only the path chain, not siblings or file contents."""
    info = _lstat(_canonical(Path(path)))
    if info is None:
        return "absent"
    if not stat.S_ISREG(info.st_mode):
        _fail("unsafe-path", "a selected path is not a regular file")
    return "file"


def _directory_or_absent(path: str) -> str:
    info = _lstat(_canonical(Path(path)))
    if info is None:
        return "absent"
    if not stat.S_ISDIR(info.st_mode):
        _fail("unsafe-path", "a selected project root is not a directory")
    return "directory"


def _selections(
    scope: Mapping[str, Any],
    vault: str | None,
    retiring_launchers: Sequence[str],
    *,
    include_absent_configs: bool,
) -> list[dict[str, Any]]:
    launchers = [str(path) for path in retiring_launchers]
    if any(not _is_abs(path) or _protected_history(path) for path in launchers):
        _fail("unsafe-path", "a retiring launcher path is not an explicit absolute file path")
    selected: list[dict[str, Any]] = []
    for host in _scope_hosts(scope):
        platform = host["platform"]
        if platform not in _SUPPORTED:
            continue
        configs: list[dict[str, str]] = []
        if platform == "codex":
            if _regular_or_absent(host["config"]) == "file" or include_absent_configs:
                configs.append({"role": "codex-mcp", "path": host["config"]})
            hooks = str(Path(host["config_home"]) / "hooks.json")
            if _regular_or_absent(hooks) == "file" or include_absent_configs:
                configs.append({"role": "codex-hooks", "path": hooks})
        else:
            if _regular_or_absent(host["config"]) == "file" or include_absent_configs:
                configs.append({"role": "omp-mcp", "path": host["config"]})
        projects = [
            root for root in host["project_roots"] if _directory_or_absent(root) == "directory"
        ]
        if not configs and not projects:
            continue
        selected.append(
            {
                "host": platform,
                "configs": configs,
                "projects": projects,
                "vault": vault,
                "retiring_launchers": launchers,
            }
        )
    return selected


def _empty_disclosure() -> dict[str, Any]:
    return {
        "schema": "sbtd-retirement/1",
        "purpose": "upgrade",
        "stop": False,
        "stop_reason": None,
        "global_effects": [],
        "proof_gap": None,
        "disclosure": _DISCLOSURE,
        "candidates": [],
        "blocked": [],
        "preserved": [],
        "manual": [],
    }


def _merge_rendered(parts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    disclosure = _empty_disclosure()
    if not parts:
        return disclosure
    disclosure["schema"] = parts[0].get("schema", disclosure["schema"])
    gaps = [part.get("proof_gap") for part in parts if part.get("proof_gap")]
    disclosure["proof_gap"] = gaps[0] if gaps else None
    for key in ("candidates", "blocked", "preserved", "manual", "global_effects"):
        rows: list[Any] = []
        for part in parts:
            value = part.get(key) or []
            if not isinstance(value, list):
                _fail("invalid-inventory", f"retirement {key} must be a list")
            rows.extend(value)
        disclosure[key] = rows
    disclosure["stop"] = any(bool(part.get("stop")) for part in parts)
    reasons = [part.get("stop_reason") for part in parts if part.get("stop_reason")]
    disclosure["stop_reason"] = reasons[0] if reasons else None
    if disclosure["stop"] and not disclosure["blocked"]:
        _fail("blocked-resource", "retirement stop has no blocked items")
    return disclosure


def _item_summary(item: Mapping[str, Any]) -> dict[str, Any]:
    path = item.get("path", item.get("target"))
    return {
        "id": item.get("id"),
        "role": item.get("role"),
        "entry": item.get("entry"),
        "path": path,
        "classification": item.get("classification"),
        "verification": item.get("verification"),
        "write_authority": item.get("write_authority"),
        "global_effect": item.get("global_effect"),
        "guidance": item.get("guidance"),
        "launcher": item.get("launcher"),
        "mode": item.get("mode"),
        "historical_mode": "unknown",
        "reason": item.get("reason"),
    }


def _public_rows(rows: Sequence[Any], *, candidates: bool = False) -> list[dict[str, Any]]:
    public: list[dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, Mapping):
            _fail("invalid-inventory", "a retirement row is not an object")
        summary = _item_summary(item)
        # Leave reports that selected no retirement writes compatible with older plans.
        if candidates and "windows_acl_digest" in item:
            summary["windows_acl_digest"] = item["windows_acl_digest"]
        public.append(summary)
    return public


def plan_retirement(
    scope: Mapping[str, Any],
    vault: str | Path | None = None,
    *,
    evidence: Sequence[Mapping[str, Any]] | None = None,
    retiring_launchers: Sequence[str] = (),
    required_targets: Sequence[str] = (),
) -> dict[str, Any]:
    """Read-only retirement disclosure and resources for one upgrade scope."""
    if not isinstance(scope, Mapping):
        _fail("scope-conflict", "the upgrade scope must be a JSON object")
    preserved = [Path(path) for path, decision in _scope_decisions(scope).items() if decision == "preserve"]
    _scope_shell_profiles(scope)
    bindings = list(evidence or [])
    # Keep evidence scoped to the selected domain after an authorized file removal.
    selections = _selections(scope, vault, retiring_launchers, include_absent_configs=bool(bindings))
    if required_targets:
        if not bindings:
            _fail("plan-stale", "a completed retirement lacks its selected ownership evidence")
        selected = {config["path"] for selection in selections for config in selection["configs"]}
        selected.update(str(Path(root) / "AGENTS.md") for selection in selections for root in selection["projects"])
        if not selected.issuperset(required_targets):
            _fail("plan-stale", "a completed retirement is outside the selected host or project paths")
    if bindings and not selections:
        _fail("scope-conflict", "retirement evidence requires a selected host config domain")
    if not selections:
        return {"disclosure": _empty_disclosure(), "resources": []}
    if bindings and vault is None:
        _fail("scope-conflict", "retirement evidence requires the private backup root")
    module = _retirement()
    rendered_parts: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    for selection in selections:
        report = module.inspect_retirement(selections=selection, evidence=bindings)
        if not isinstance(report, dict):
            _fail("invalid-inventory", "retirement inspection must return an object")
        rendered = module.render_candidates(report, purpose="upgrade")
        if not isinstance(rendered, dict):
            _fail("invalid-inventory", "retirement rendering must return an object")
        if any(
            _same_file_entry(Path(item["target"]), path)
            for item in rendered["candidates"] if isinstance(item, Mapping) and _is_abs(item.get("target"))
            for path in preserved
        ):
            _fail("decision-conflict", "a retirement candidate conflicts with an explicit preserve decision")
        reports.append(report)
        rendered_parts.append(rendered)
    disclosure = _merge_rendered(rendered_parts)
    disclosure["candidates"] = _public_rows(disclosure["candidates"], candidates=True)
    disclosure["blocked"] = _public_rows(disclosure["blocked"])
    disclosure["preserved"] = _public_rows(disclosure["preserved"])
    resources = _resources(rendered_parts, reports)
    return {"disclosure": disclosure, "resources": resources}


def _candidate_fields(item: Mapping[str, Any]) -> dict[str, Any]:
    for key in ("id", "target", "path", "action", "write_authority"):
        if key not in item:
            _fail("invalid-inventory", "a retirement candidate is missing a required field")
    if item["path"] != item["target"] or not _is_abs(item["target"]):
        _fail("invalid-inventory", "a retirement candidate path is not its absolute target")
    if item["write_authority"] is not True:
        _fail("invalid-inventory", "a displayed candidate lacks write authority")
    if item["action"] not in {"edit", "remove-file"}:
        _fail("invalid-inventory", "a retirement candidate action is not recognized")
    if _protected_history(str(item["target"])):
        _fail("scope-conflict", "historical graft data is not an upgrade deletion target")
    return {
        "id": item["id"],
        "target": item["target"],
        "path": item["path"],
        "action": item["action"],
        "role": item.get("role"),
        "entry": item.get("entry"),
        "mode": item.get("mode"),
        "before": item.get("before"),
        **({"windows_acl_digest": item["windows_acl_digest"]} if "windows_acl_digest" in item else {}),
        "historical_mode": "unknown",
        "global_effect": bool(item.get("global_effect")),
        "write_authority": True,
    }


def _render_target_bytes(report: Mapping[str, Any], target: str, before: bytes) -> bytes:
    # Validate this file again without reopening siblings that may already be retired.
    current = {**report, "items": [
        item for item in report["items"] if isinstance(item, Mapping) and item.get("path") == target
    ]}
    rendered = _retirement().retirement_file_bytes(
        report=current, purpose="upgrade", target=target, before=before,
    )
    if not isinstance(rendered, (bytes, bytearray)):
        _fail("invalid-inventory", "retirement rendering must return bytes")
    return bytes(rendered)


def _resources(
    rendered_parts: Sequence[Mapping[str, Any]], reports: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    report_for: dict[str, dict[str, Any]] = {}
    for rendered, report in zip(rendered_parts, reports, strict=True):
        for raw in rendered.get("candidates") or []:
            if not isinstance(raw, Mapping):
                _fail("invalid-inventory", "a retirement candidate is not an object")
            item = _candidate_fields(raw)
            grouped.setdefault(item["target"], []).append(item)
            report_for[item["target"]] = report
    resources: list[dict[str, Any]] = []
    for target, items in grouped.items():
        actions = {item["action"] for item in items}
        if len(actions) != 1:
            _fail("invalid-inventory", "one retirement target mixes edit and removal")
        action = next(iter(actions))
        before = snapshot(Path(target))
        if before["type"] != "file" or any(item["before"] != before for item in items):
            _fail("state-conflict", "retirement candidates no longer match the live file bytes")
        source = {"path": target, "state": before}
        base = {
            "id": contracts.resource_id(_OWNER_KIND, target),
            "kind": "retirement",
            "target": target,
            "source": source,
            "before": before,
            "host": {"platform": "retirement", "config": target},
        }
        details = {
            "action": action,
            "items": items,
            "report": report_for[target],
            "historical_mode": "unknown",
            "mode_before": _require_live_mode(Path(target), items),
        }
        if os.name == "nt":
            from sbtd_retirement_permissions import capture, digest

            sealed_acl = items[0].get("windows_acl_digest")
            if sealed_acl is None or any(item.get("windows_acl_digest") != sealed_acl for item in items):
                _fail("state-conflict", "retirement candidates do not bind one Windows ACL")
            if digest(capture(Path(target))) != sealed_acl:
                _fail("state-conflict", "retirement candidate Windows ACL is not the live ACL")
            details["windows_acl_digest"] = sealed_acl
        if action == "remove-file":
            resources.append(
                {
                    **base,
                    "desired": {"type": "absent", "checksum": None},
                    "classification": "known-old",
                    "decision": "replace",
                    "details": details,
                }
            )
            continue
        rendered = _render_target_bytes(report_for[target], target, read_file(Path(target), before))
        desired = {"type": "file", "checksum": hashlib.sha256(rendered).hexdigest()}
        resources.append(
            {
                **base,
                "desired": desired,
                "classification": "known-old",
                "decision": "replace",
                "details": details,
            }
        )
    if any(part.get("stop") for part in rendered_parts):
        seen: set[str] = set()
        for rendered in rendered_parts:
            for raw in rendered.get("blocked") or []:
                if not isinstance(raw, Mapping):
                    _fail("invalid-inventory", "a blocked retirement row is not an object")
                path = raw.get("path") or raw.get("target")
                if not _is_abs(path) or path in seen:
                    continue
                seen.add(str(path))
                if _protected_history(str(path)):
                    _fail("scope-conflict", "historical graft data is not an upgrade deletion target")
                before = snapshot(Path(path))
                resources.append(
                    {
                        "id": contracts.resource_id(_OWNER_KIND, str(path)),
                        "kind": "retirement",
                        "target": str(path),
                        "source": {"path": str(path), "state": before},
                        "before": before,
                        "desired": None,
                        "classification": "identity-conflict",
                        "decision": "blocked",
                        "details": {
                            "action": "block",
                            "items": [_item_summary(raw)],
                            "error_code": "retirement-unproven",
                            "guidance": raw.get("guidance"),
                            "historical_mode": "unknown",
                        },
                        "host": {"platform": "retirement", "config": str(path)},
                    }
                )
        if not any(resource["decision"] == "blocked" for resource in resources):
            _fail("blocked-resource", "retirement stop produced no blocked resource")
    return resources


def build_host_resources(
    scope: Mapping[str, Any], *, package_root: Path | str | None = None
) -> list[dict[str, Any]]:
    """Validate host scope. Does not install or wire Graft."""
    if not isinstance(scope, Mapping):
        _fail("scope-conflict", "the upgrade scope must be a JSON object")
    _package_root(package_root)
    _scope_decisions(scope)
    _scope_hosts(scope)
    _scope_shell_profiles(scope)
    return []


def render_resource(
    resource: Mapping[str, Any], *, package_root: Path | str | None = None
) -> bytes:
    """Regenerate retirement edit bytes. ``remove-file`` is not a byte write."""
    del package_root
    if not isinstance(resource, Mapping) or resource.get("kind") != "retirement":
        _fail("unsupported-in-rc.3", "a sealed plan still contains Graft operations; regenerate the plan")
    details = resource.get("details")
    if not isinstance(details, Mapping) or details.get("action") != "edit":
        _fail("unsupported-operation", "remove-file retirement is not rendered as empty bytes")
    target = Path(str(resource.get("target")))
    return _render_target_bytes(details["report"], str(target), read_file(target, resource["before"]))


def _live_mode(path: Path) -> str | None:
    try:
        info = path.lstat()
    except OSError:
        return None
    if not stat.S_ISREG(info.st_mode):
        return None
    return format(stat.S_IMODE(info.st_mode), "04o")


def _require_live_mode(path: Path, items: Sequence[Mapping[str, Any]]) -> str:
    """Bind the live mode; on Windows this is only the read-only attribute."""
    mode = _live_mode(path)
    if mode is None or any(item.get("mode") != mode for item in items):
        _fail("state-conflict", "retirement candidate mode does not match the live file")
    return mode


def _file_registers_removed_server(path: Path, role: str) -> bool:
    try:
        if _regular_or_absent(str(path)) == "absent":
            return False
        raw = read_file(path)
        retirement = _retirement()
        if role == "codex-hooks":
            commands = retirement._hook_commands(retirement._json_document(raw))
            return commands is None or any(
                _REMOVED_SERVER in command.lower() or _REMOVED_LAUNCHER in command.lower()
                or _argv_invokes_removed_runtime(retirement._hook_argv(command) or ())
                for values in commands.values() for command in values
            )
        omp = role == "omp-mcp"
        document = retirement._json_document(raw) if omp else retirement._toml_document(raw)
        for name, entry in retirement._servers(document, omp=omp).items():
            if name == _REMOVED_SERVER or name.startswith(f"{_REMOVED_SERVER}-"):
                return True
            if not isinstance(entry, Mapping):
                return True
            command, args = entry.get("command", ""), entry.get("args", [])
            if not isinstance(command, str) or not isinstance(args, list) or any(not isinstance(arg, str) for arg in args):
                return True
            if _argv_invokes_removed_runtime((command, *args)):
                return True
    except (ContractError, OSError):
        return True
    return False


def _retained_server_would_launch(host: Mapping[str, Any], project: Path) -> bool:
    """Check only effective registration files in the selected host and project."""
    if host["platform"] == "codex":
        paths = (
            (Path(host["config"]), "codex-mcp"),
            (Path(host["config_home"]) / "hooks.json", "codex-hooks"),
            (project / ".codex" / "config.toml", "codex-mcp"),
            (project / ".codex" / "hooks.json", "codex-hooks"),
            (project / "hooks.json", "codex-hooks"),
        )
    else:
        paths = (
            (Path(host["config"]), "omp-mcp"),
            (project / ".codex" / "config.toml", "codex-mcp"),
            (project / ".omp" / "mcp.json", "omp-mcp"),
            (project / ".omp" / ".mcp.json", "omp-mcp"),
        )
    return any(_file_registers_removed_server(path, role) for path, role in paths)


def _proven_project_root(host: Mapping[str, Any]) -> Path | None:
    for root in host["project_roots"]:
        try:
            validate_project(Path(root))
        except ContractError:
            continue
        return Path(root)
    return None


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
        name for name in expected if f"skill:{name}" in identities or f"skill://{name}" in identities
    )


_CODEX_FIXTURE_CONFIG = """\
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
tools:
  xdev: false
"""


def _host_links(
    host_id: str, authorizations: Sequence[Mapping[str, Any]]
) -> list[Mapping[str, Any]]:
    selected = []
    for item in authorizations:
        payload = item.get("payload") if isinstance(item, Mapping) else None
        if isinstance(payload, Mapping) and payload.get("host_id") == host_id:
            selected.append(item)
    return selected


def _probe_selected_host(
    host: Mapping[str, Any], authorizations: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Spawn the selected host in a clean fixture. Never load a retained server."""
    proven = _proven_project_root(host)
    if proven is None:
        raise _ProbeError("unavailable", "no-proven-project-root")
    if _retained_server_would_launch(host, proven):
        raise _ProbeError("failed", "unsafe-registered-server")
    platform = host["platform"]
    binary = "codex" if platform == "codex" else "omp"
    executable = host.get("executable") or _which(binary)
    if not isinstance(executable, str) or not executable:
        raise _ProbeError("unavailable", "host-cli-not-found")
    if _argv_invokes_removed_runtime((executable,)):
        raise _ProbeError("failed", "unsafe-registered-server")
    holder, fixture = _probe_fixture("sbtd-upgrade-host-")
    try:
        require_private_directory(fixture / "home", create=True)
        outcomes: list[dict[str, Any]] = []
        selected_links = _host_links(host["id"], authorizations)
        copies = _copy_skill_roots(
            host["skills_roots"],
            fixture / "skills-roots",
            link_authorizations=selected_links,
            outcomes=outcomes,
        )
        if sorted(row["authorization_id"] for row in outcomes if row["status"] == "materialized") != sorted(
            item["authorization_id"] for item in selected_links
        ):
            _fail("skill-identity-unproven", "an authorized link was not materialized in the probe projection")
        expected = _expected_skill_names(
            copies,
            required=[item["payload"]["skill_name"] for item in selected_links],
        )
        if platform == "codex":
            codex_home = fixture / "codex-home"
            require_private_directory(codex_home, create=True)
            quoted = json.dumps(str(proven))
            config = (
                _CODEX_FIXTURE_CONFIG
                + f'\n[projects.{quoted}]\ntrust_level = "untrusted"\n'
            ).encode("utf-8")
            (codex_home / "config.toml").write_bytes(config)
            env = _probe_env(
                fixture,
                {"CODEX_HOME": str(codex_home), "CODEX_PROBE_DUMMY_API_KEY": "dummy"},
            )
            argv = [executable, "app-server", "--listen", "stdio://"]
        else:
            agent = fixture / "agent"
            require_private_directory(agent, create=True)
            (agent / "models.yml").write_text(_OMP_FIXTURE_MODELS, encoding="utf-8")
            (agent / "config.yml").write_text(_OMP_FIXTURE_CONFIG, encoding="utf-8")
            active_skills = require_private_directory(agent / "skills", create=True)
            for copy in copies:
                for name, kind in _root_entries(Path(copy)):
                    source = Path(copy) / name
                    if kind != "directory" or snapshot(source / "SKILL.md")["type"] != "file":
                        continue
                    target = active_skills / name
                    if _lstat(target) is not None:
                        _fail("skill-identity-unproven", "duplicate Skills cannot share the OMP fixture name")
                    backup_reference(
                        {"path": str(source), "state": snapshot(source)},
                        target,
                        private_root=fixture,
                    )
            env = _probe_env(fixture, {"HOME": str(fixture / "home"), "PI_CODING_AGENT_DIR": str(agent)})
            argv = [executable, "--mode", "rpc", "--no-ui", "--no-extensions", "--no-rules"]
        if _argv_invokes_removed_runtime(argv):
            raise _ProbeError("failed", "unsafe-registered-server")
        try:
            proc = _spawn(argv, env=env, cwd=str(fixture if platform == "codex" else proven))
        except OSError:
            raise _ProbeError("unavailable", "host-cli-unavailable") from None
        rpc = _JsonLines(proc, _HOST_TIMEOUT)
        try:
            if platform == "codex":
                rpc.call(
                    "initialize",
                    {
                        "clientInfo": {"name": "sbtd-upgrade-verify", "version": "1.0.0"},
                        "capabilities": {"experimentalApi": True},
                    },
                )
                rpc.notify("initialized", {})
                thread = rpc.call("thread/start", {"ephemeral": True, "cwd": str(proven)})
                thread_id = None
                if isinstance(thread, Mapping):
                    node = thread.get("thread")
                    if isinstance(node, Mapping):
                        thread_id = node.get("id")
                    thread_id = thread_id or thread.get("threadId")
                if not isinstance(thread_id, str):
                    raise _ProbeError("failed", "host-thread-unavailable")
                if copies:
                    rpc.call("skills/extraRoots/set", {"extraRoots": copies})
                listed = rpc.call(
                    "skills/list", {"cwds": [str(proven)], "forceReload": True}
                )
                found, errors = _parse_skills(listed, copies)
            else:
                rpc.call("negotiate_protocol", {"protocolVersion": 2}, key="type")
                commands = rpc.call("get_available_commands", {}, key="type")
                found = _omp_skill_names(commands, expected)
                errors = 0
        finally:
            exit_code = rpc.close()
        return {
            "expected": expected,
            "found": found,
            "errors": errors,
            "exit": exit_code,
            "link_authorizations": outcomes,
        }
    finally:
        shutil.rmtree(holder, ignore_errors=True)



def _host_entry(
    host: Mapping[str, Any],
    *,
    probe: bool,
    authorizations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    supported = host["platform"] in _SUPPORTED
    entry: dict[str, Any] = {
        "id": host["id"],
        "platform": host["platform"],
        "applicability": "supported" if supported else "unsupported",
        "disk": {"status": "not-applicable"},
        "runtime": {"status": "not-applicable"},
        "legacy": {"status": "not-applicable"},
    }
    if not supported:
        entry["status"] = "unsupported"
        entry["host"] = {"status": "not-applicable"}
        return entry
    if not probe:
        entry["status"] = "unverified"
        entry["host"] = {"status": "unverified"}
        return entry
    selected = bool(host["project_roots"] or host["skills_roots"])
    if not selected:
        entry["status"] = "unverified"
        entry["host"] = {
            "status": "not-applicable",
            "checks": {
                "binding": {"status": "not-applicable"},
                "protocol": {"status": "not-applicable"},
                "host_load": {"status": "not-applicable"},
                "skills": {"status": "not-applicable"},
            },
            "live_reload": dict(_LIVE_RELOAD),
        }
        return entry
    try:
        evidence = _probe_selected_host(host, authorizations)
    except _ProbeError as error:
        load = {
            "status": error.kind,
            "reason": error.reason,
            "evidence_scope": _HOST_LOAD_EVIDENCE_SCOPE,
        }
        skills = {
            "status": error.kind,
            "reason": error.reason,
            "skills": [],
        }
        entry["status"] = "unavailable" if error.kind == "unavailable" else "fail"
        entry["host"] = {
            "status": "failed" if error.kind == "failed" else error.kind,
            "checks": {
                "binding": {"status": "not-applicable"},
                "protocol": {"status": error.kind, "reason": error.reason},
                "host_load": load,
                "skills": skills,
            },
            "live_reload": dict(_LIVE_RELOAD),
        }
        return entry
    except ContractError as error:
        entry["status"] = "fail"
        entry["host"] = {
            "status": "failed",
            "checks": {
                "binding": {"status": "not-applicable"},
                "protocol": {"status": "not-applicable"},
                "host_load": {
                    "status": "failed",
                    "reason": error.code,
                    "evidence_scope": _HOST_LOAD_EVIDENCE_SCOPE,
                },
                "skills": {"status": "failed", "reason": error.code, "skills": []},
            },
            "live_reload": dict(_LIVE_RELOAD),
        }
        return entry
    skills_ok = evidence["errors"] == 0 and evidence["found"] == evidence["expected"]
    protocol_ok = evidence["exit"] == 0
    skill_status: dict[str, Any] = {
        "status": "verified" if skills_ok else "failed",
        "skills": list(evidence["found"] if skills_ok else evidence["expected"]),
    }
    if not skills_ok:
        skill_status["expected"] = list(evidence["expected"])
        skill_status["reason"] = "skills-evidence-mismatch"
    if evidence["link_authorizations"]:
        skill_status["link_authorizations"] = evidence["link_authorizations"]
    load_status = {
        "status": "verified" if protocol_ok and skills_ok else "failed",
        "evidence_scope": _HOST_LOAD_EVIDENCE_SCOPE,
        "exit": evidence["exit"],
    }
    if not protocol_ok:
        load_status["reason"] = "host-exit-nonzero"
    elif not skills_ok:
        load_status["reason"] = "skills-evidence-mismatch"
    failed = not protocol_ok or not skills_ok
    entry["status"] = "fail" if failed else "pass"
    entry["host"] = {
        "status": "failed" if failed else "verified",
        "checks": {
            "binding": {"status": "not-applicable"},
            "protocol": {"status": "verified" if protocol_ok else "failed"},
            "host_load": load_status,
            "skills": skill_status,
        },
        "live_reload": dict(_LIVE_RELOAD),
    }
    return entry


def verify_hosts(
    scope: Mapping[str, Any],
    *,
    package_root: Path | str | None = None,
    probe: bool = False,
    link_authorizations: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Selected-host protocol and Skills evidence. Never starts a removed server."""
    del package_root
    if link_authorizations and not probe:
        _fail("invalid-argument", "link authorizations are only meaningful for an explicit probe")
    authorizations = list(link_authorizations or [])
    result: dict[str, Any] = {"probe": bool(probe), "hosts": [], "shell_profiles": []}
    for host in _scope_hosts(scope):
        result["hosts"].append(
            _host_entry(host, probe=bool(probe), authorizations=authorizations)
        )
    for profile in _scope_shell_profiles(scope):
        try:
            absent = _regular_or_absent(profile["path"]) == "absent"
        except ContractError:
            absent = False
        result["shell_profiles"].append(
            {
                "path": profile["path"],
                "shell": profile["shell"],
                "applicability": "supported",
                "status": "unverified",
                "disk": {"status": "not-applicable"},
                "runtime": {"status": "not-applicable"},
                "host": {"status": "not-applicable"},
                "legacy": {"status": "absent" if absent else "unverified", "lines": []},
            }
        )
    return result
