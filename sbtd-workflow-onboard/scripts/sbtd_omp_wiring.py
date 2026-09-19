"""Pure OMP MCP configuration analysis for P1-05.

The module reads only bytes and already-normalized inherited-source records. It
never executes configured commands, probes a host, or writes a file. Deployment
callers own snapshots, filesystem authorization, and persistence.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NoReturn

import onboard_contracts as contracts
from sbtd_project import _check_finite, _reject_json_constant, _reject_json_duplicates

__all__ = ["analyze_omp_configuration", "desired_omp_server", "omp_mcp_candidate"]

_SERVER_PREFIX = "sbtd-graft"
_BINDING_KEYS = ("root", "node", "cli", "python", "launcher")
_STARTUP_FLAGS = ("-E", "-s")
_TELEMETRY_ENV = {"DO_NOT_TRACK": "1", "DNT": "1"}


def _fail(code: str, message: str) -> NoReturn:
    raise contracts.ContractError(code, message)


def _server_name(root: str) -> str:
    return f"{_SERVER_PREFIX}-{hashlib.sha256(root.encode('utf-8')).hexdigest()[:16]}"


def _bindings(bindings: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
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


def desired_omp_server(binding: Mapping[str, Any]) -> dict[str, Any]:
    """Return the native OMP stdio server record for one verified binding."""
    paths = _bindings([binding])[0]
    return {
        "type": "stdio",
        "command": paths["python"],
        "args": [
            *_STARTUP_FLAGS,
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
        "env": dict(_TELEMETRY_ENV),
    }


def _strict_json(raw: bytes, label: str) -> Any:
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        _fail("invalid-utf8", f"the {label} is not strict UTF-8")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_json_duplicates,
            parse_constant=_reject_json_constant,
        )
    except (ValueError, RecursionError):
        _fail("invalid-json", f"the {label} is not strict JSON")
    if not _check_finite(value):
        _fail("invalid-json", f"the {label} contains a non-finite number")
    return value


def _reject_dynamic(value: Any) -> None:
    if isinstance(value, str):
        if re.search(r"\$\{[^}:]+(?::-[^}]*)?\}", value):
            _fail("invalid-config", "OMP configuration contains unsupported dynamic values")
        return
    if isinstance(value, list):
        for item in value:
            _reject_dynamic(item)
        return
    if isinstance(value, dict):
        for item in value.values():
            _reject_dynamic(item)


def _servers(document: Any, label: str) -> dict[str, Mapping[str, Any]]:
    if not isinstance(document, dict):
        _fail("invalid-config", f"the {label} must be a JSON object")
    servers = document.get("mcpServers", {})
    if not isinstance(servers, dict) or any(
        not isinstance(name, str) or not isinstance(server, Mapping)
        for name, server in servers.items()
    ):
        _fail("invalid-config", f"the {label} MCP server section is malformed")
    _reject_dynamic(servers)
    return servers


def _literal_env_keys(server: Mapping[str, Any]) -> list[str] | None:
    env = server.get("env", {})
    if not isinstance(env, Mapping):
        return None
    policy = server.get("envPolicy")
    if policy == "literal":
        return sorted(key for key in env if isinstance(key, str))
    if policy is not None:
        return None
    literal = server.get("envLiteralKeys", [])
    if not isinstance(literal, list) or any(
        not isinstance(key, str) for key in literal
    ):
        return None
    return sorted(literal)


def _equivalent(actual: Mapping[str, Any], desired: Mapping[str, Any]) -> bool:
    env = actual.get("env", {})
    actual_type = actual.get("type", "stdio")
    actual_literals = _literal_env_keys(actual)
    desired_literals = _literal_env_keys(desired)
    return (
        actual.get("auth") == desired.get("auth")
        and actual.get("oauth") == desired.get("oauth")
        and actual.get("requestIdFormat", "number")
        == desired.get("requestIdFormat", "number")
        and actual_type == desired["type"]
        and actual.get("command") == desired["command"]
        and actual.get("args") == desired["args"]
        and actual.get("cwd") == desired["cwd"]
        and isinstance(env, Mapping)
        and dict(env) == desired["env"]
        and actual_literals is not None
        and actual_literals == desired_literals
    )
def _source_order(source: Mapping[str, Any]) -> int:
    provider = source["source"].split("-", 1)[0]
    try:
        return {"native": 0, "claude": 1, "codex": 2}[provider]
    except KeyError:
        _fail("invalid-argument", "inherited source providers are unsupported")


def _string_set(value: Any, label: str) -> set[str]:
    if value is None:
        return set()
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        _fail("invalid-config", f"the active OMP {label} list is malformed")
    return set(value)


def _entry_enabled(server: Mapping[str, Any]) -> bool:
    enabled = server.get("enabled")
    if isinstance(enabled, str):
        lowered = enabled.lower()
        if lowered in {"false", "0"}:
            return False
        if lowered in {"true", "1"}:
            return True
    if enabled is None:
        return True
    if isinstance(enabled, bool):
        return enabled
    _fail("invalid-config", "an active OMP MCP enabled flag is malformed")


def analyze_omp_configuration(
    target: Path,
    bindings: Sequence[Mapping[str, Any]],
    inherited: Sequence[Mapping[str, Any]],
    *,
    disabled_extensions: Sequence[str] = (),
) -> dict[str, Any]:
    """Analyze the active OMP target and explicit inherited records.

    ``inherited`` is the caller's observed source set, already honoring profile
    and provider gates. This function does not rediscover or execute it.
    """
    if not isinstance(target, Path) or not target.is_absolute():
        _fail("invalid-argument", "the OMP MCP target must be an absolute path")
    if isinstance(disabled_extensions, (str, bytes)) or any(
        not isinstance(item, str) for item in disabled_extensions
    ):
        _fail("invalid-argument", "disabled OMP extension identities are malformed")
    paths = _bindings(bindings)
    desired = {_server_name(item["root"]): desired_omp_server(item) for item in paths}
    sources = sorted(_normalized_inherited(inherited), key=_source_order)
    raw = b""
    document: dict[str, Any] = {"mcpServers": {}}
    existing: dict[str, Mapping[str, Any]] = {}
    if target.exists():
        raw = target.read_bytes()
        document = _strict_json(raw, "active OMP MCP configuration")
        existing = _servers(document, "active OMP MCP configuration")
    disabled_servers = _string_set(document.get("disabledServers"), "disabledServers")
    forced_enabled = _string_set(document.get("enabledServers"), "enabledServers")
    blocked_extensions = set(disabled_extensions)
    def blocked_name(name: str) -> bool:
        return name in disabled_servers or f"mcp:{name}" in blocked_extensions

    blocked_names = {name for name in desired if blocked_name(name)}
    if blocked_names:
        _fail(
            "ownership-conflict",
            "the active OMP configuration disables a generated Graft identity",
        )
    for active_name, active in existing.items():
        enabled = _entry_enabled(active) or active_name in forced_enabled
        managed_shape = active_name == _SERVER_PREFIX or active_name.startswith(
            _SERVER_PREFIX + "-"
        )
        if blocked_name(active_name):
            if managed_shape:
                _fail(
                    "ownership-conflict",
                    "an active sbtd-graft OMP entry is explicitly disabled",
                )
            continue
        if not managed_shape:
            continue
        equivalent_names = {
            desired_name
            for desired_name, desired_server in desired.items()
            if _equivalent(active, desired_server)
        }
        if not enabled or not equivalent_names:
            _fail(
                "ownership-conflict",
                "an active sbtd-graft OMP entry differs or is disabled",
            )
    matches: list[dict[str, str]] = []
    writes: list[dict[str, Any]] = []
    for source in sources:
        for name, server in source["servers"].items():
            server_enabled = source["enabled"] and server.get("enabled", True) is not False
            managed_shape = name == _SERVER_PREFIX or name.startswith(_SERVER_PREFIX + "-")
            if blocked_name(name):
                if managed_shape:
                    _fail(
                        "ownership-conflict",
                        "an inherited sbtd-graft connection is explicitly disabled",
                    )
                continue
            equivalent_names = {
                desired_name
                for desired_name, desired_server in desired.items()
                if _equivalent(server, desired_server)
            }
            if managed_shape and (not server_enabled or not equivalent_names):
                _fail(
                    "ownership-conflict",
                    "an inherited sbtd-graft connection differs or is disabled",
                )
            if not server_enabled:
                continue
            for desired_name in equivalent_names:
                matches.append(
                    {
                        "source": source["source"],
                        "name": name,
                        "server": desired_name,
                    }
                )
    active_candidates = {
        name: server
        for name, server in existing.items()
        if not blocked_name(name)
        and (_entry_enabled(server) or name in forced_enabled)
    }
    for name, server in desired.items():
        if any(match["server"] == name for match in matches):
            continue
        current = active_candidates.get(name)
        if current is not None:
            if _equivalent(current, server):
                matches.append({"source": "active", "name": name, "server": name})
                continue
            _fail(
                "ownership-conflict",
                "an existing sbtd-graft OMP entry differs and cannot be claimed",
            )
        equivalent_active = [
            active_name
            for active_name, active in active_candidates.items()
            if _equivalent(active, server)
        ]
        if equivalent_active:
            matches.append(
                {"source": "active", "name": equivalent_active[0], "server": name}
            )
            continue
        writes.append({"name": name, "server": server})
    return {
        "target": str(target),
        "servers": existing,
        "writes": writes,
        "inherited_matches": matches,
    }




def _normalized_inherited(
    inherited: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(inherited, (str, bytes, bytearray)) or not isinstance(
        inherited, Sequence
    ):
        _fail("invalid-argument", "inherited sources must be a sequence of mappings")
    normalized: list[dict[str, Any]] = []
    for record in inherited:
        if (
            not isinstance(record, Mapping)
            or not isinstance(record.get("source"), str)
            or not isinstance(record.get("enabled"), bool)
            or not isinstance(record.get("servers"), Mapping)
        ):
            _fail("invalid-argument", "inherited source records are malformed")
        servers = record["servers"]
        if any(not isinstance(name, str) or not isinstance(server, Mapping) for name, server in servers.items()):
            _fail("invalid-argument", "inherited MCP server records are malformed")
        _reject_dynamic(servers)
        normalized.append(
            {
                "source": record["source"],
                "enabled": record["enabled"],
                "servers": dict(servers),
            }
        )
    return normalized




def omp_mcp_candidate(before: bytes, analysis: Mapping[str, Any]) -> bytes:
    """Render the active OMP config candidate, or ``before`` when complete."""
    if not isinstance(before, (bytes, bytearray)):
        _fail("invalid-argument", "input document must be bytes")
    raw = bytes(before)
    document = _strict_json(raw, "active OMP MCP configuration") if raw else {
        "mcpServers": {}
    }
    existing = _servers(document, "active OMP MCP configuration")
    if not isinstance(analysis, Mapping) or not isinstance(analysis.get("writes"), list):
        _fail("invalid-argument", "the OMP configuration analysis is malformed")
    writes = analysis["writes"]
    if any(not isinstance(item, Mapping) for item in writes):
        _fail("invalid-argument", "the OMP configuration analysis is malformed")
    servers = dict(existing)
    for item in writes:
        name = item.get("name")
        server = item.get("server")
        if not isinstance(name, str) or not isinstance(server, Mapping):
            _fail("invalid-argument", "the OMP configuration analysis is malformed")
        if name in servers:
            _fail(
                "ownership-conflict",
                "an existing sbtd-graft OMP entry differs and cannot be claimed",
            )
        servers[name] = dict(server)
    if not writes:
        return raw
    document["mcpServers"] = servers
    try:
        return contracts.canonical_json_bytes(document)
    except (TypeError, ValueError, RecursionError):
        _fail("invalid-config", "the rendered OMP MCP candidate cannot be serialized")
