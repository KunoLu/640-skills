"""Evidence-only retirement report and authenticated candidate rendering.

A file checksum is not ownership of every matching shape inside it. An entry
is removable only when a bound receipt shows that exact entry changed between
the retained original and the live post-write bytes. Preexisting identical
shapes, no-op writes, mixed unknown edits, and unreadably linked paths are
not claimed. The captured POSIX mode or Windows owner, group and DACL describe
the live file, not the permissions at the time of the historical write.

Evidence and retained originals must already be regular files lexically
inside the caller-supplied vault. A declared ``backup_ref`` outside that
vault is not evidence. Paths are walked without following links: ``.``,
``..``, symlinks, Windows junctions and other reparse points, hardlinks,
and a lexical path that is not the physical path all fail closed. Documents
that establish authority also require private Windows ACLs; retained user
bytes supply content, not authority. Place an rc2 upgrade receipt at the
vault path its wrapper ``receipt_path`` names; that field must be the file
actually read, and ``status`` must equal the payload status. Historical plans
are not required to carry ``graftRetirement``.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import stat
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from onboard_contracts import (
    ContractError,
    canonical_json_bytes,
    operation_id,
    resource_id,
)
import sbtd_retirement_permissions as windows_permissions
from sbtd_retirement_paths import HISTORY_DIRS, LEGACY_LAUNCHER_RELATIVE

REPORT_SCHEMA = "sbtd-retirement/1"
RECEIPT_SCHEMA = "sbtd-retirement-receipt/1"
_INTENT_SCHEMA = "sbtd-retirement-intent/1"
DESCRIPTOR_SCHEMA = "sbtd-retirement-evidence/1"
_PURPOSES = frozenset({"check", "plan", "reset", "upgrade", "cleanup"})
_EXECUTABLE = frozenset({"reset", "upgrade", "cleanup"})
_ROLES = frozenset({"codex-mcp", "codex-hooks", "omp-mcp"})
_HOST_ROLES = {"codex": frozenset({"codex-mcp", "codex-hooks"}), "omp": frozenset({"omp-mcp"})}
_SELECTORS = {
    "codex-mcp": ("toml", "graft-mcp"),
    "codex-hooks": ("json", "graft-hooks"),
    "omp-mcp": ("json", "graft-omp-mcp"),
    "agents-fence": ("markdown", "graft-agents"),
}
_RESULT_KEYS = frozenset({
    "phase", "resource_id", "operation_ids", "dependent_projects",
    "status", "backup_ref", "before", "after", "error",
})
_UPGRADE_WRAPPER = frozenset({"receipt_path", "status"})
_UPGRADE_ROW_KEYS = frozenset({
    "id", "kind", "target", "decision", "result", "before", "desired", "after",
    "mechanical_after", "mechanical_before", "backup_ref", "created_parents",
    "reason", "mutated",
})
_UPGRADE_BIND = ("kind", "target", "before", "desired", "decision")
_ROW_OPTIONAL = frozenset({
    "mode_before", "mode_after", "windows_acl_digest", "windows_acl_digest_after",
})
_FENCE_BODY_SHA = "7a697bc2a19853aa0c63ea89198b656adb055e7d0a4cad6989f4cb70a241f3e9"
_FENCE_START = "<!-- graft:start -->"
_FENCE_END = "<!-- graft:end -->"
_GLOBAL_KEY = "sbtd-graft"
_LAUNCHER_NAME = Path(LEGACY_LAUNCHER_RELATIVE).name
_ENV = {"DO_NOT_TRACK": "1", "DNT": "1"}
_FLAGS = ("-E", "-s")
_HOOK_EVENTS = {
    "session-start": "SessionStart",
    "prompt": "UserPromptSubmit",
    "post-edit": "PostToolUse",
    "stop": "Stop",
}

__all__ = [
    "REPORT_SCHEMA",
    "inspect_retirement",
    "render_candidates",
    "render_candidate_bytes",
    "retirement_file_bytes",
    "backup_candidate",
    "capture_windows_permissions",
    "read_windows_permissions",
    "retain_windows_permissions",
    "retained_windows_permissions",
    "apply_candidate",
    "reconcile_candidate",
    "restore_candidate",
    "merge_reports",
]


def _fail(code: str, message: str) -> None:
    raise ContractError(code, message, exit_code=2)


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _files():
    try:
        from sbtd_migration_files import (
            assert_private_file,
            backup_reference,
            install_reference,
            read_file,
            remove_reference,
            require_private_directory,
            save_document,
            snapshot,
            write_file,
        )
    except ImportError as error:
        _fail("runtime-unavailable", "retirement file primitives are unavailable")
        raise error
    return {
        "assert_private_file": assert_private_file,
        "backup_reference": backup_reference,
        "install_reference": install_reference,
        "read_file": read_file,
        "remove_reference": remove_reference,
        "require_private_directory": require_private_directory,
        "save_document": save_document,
        "snapshot": snapshot,
        "write_file": write_file,
    }


def _as_path(value: Any, label: str) -> Path:
    if isinstance(value, Path):
        path = value
    elif isinstance(value, str) and value:
        path = Path(value)
    else:
        _fail("invalid-argument", f"{label} must be a path")
        raise AssertionError
    if not path.is_absolute():
        _fail("invalid-path", f"{label} must be absolute")
    return path


def _is_reparse(info: os.stat_result) -> bool:
    return bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _walk(path: Path) -> str:
    """Classify without following links. Unreadable and links are not absent."""
    if not path.is_absolute() or any(part in {".", ".."} for part in path.parts):
        return "invalid"
    current = Path(path.anchor)
    parts = path.parts[1:]
    if not parts:
        return "other"
    for index, part in enumerate(parts):
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            return "absent"
        except (OSError, ValueError):
            return "unreadable"
        if stat.S_ISLNK(info.st_mode) or _is_reparse(info):
            return "unsafe"
        last = index == len(parts) - 1
        if last:
            if not stat.S_ISREG(info.st_mode):
                return "other"
            return "hardlink" if info.st_nlink > 1 else "file"
        if not stat.S_ISDIR(info.st_mode):
            return "other"
    return "absent"


def _alias(path: Path) -> bool:
    """True when the lexical spelling is not the physical path."""
    try:
        return os.path.realpath(path) != os.path.normpath(os.fspath(path))
    except OSError:
        return True


def _mode(path: Path) -> str | None:
    kind = _walk(path)
    if kind not in {"file", "other"}:
        return None
    try:
        return f"{stat.S_IMODE(path.lstat().st_mode):04o}"
    except OSError:
        return None


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _require_windows_digest(value: Any) -> None:
    if not _is_sha256(value):
        _fail("windows-permissions-unproven", "retirement requires a recorded Windows ACL digest")


def capture_windows_permissions(path: Path, expected_digest: str) -> bytes:
    """Read current native access only if it matches the sealed authority."""
    _require_windows_digest(expected_digest)
    raw = windows_permissions.capture(path)
    if windows_permissions.digest(raw) != expected_digest:
        _fail("state-conflict", "the Windows ACL differs from the recorded state")
    return raw


def _state(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict) or set(value) != {"type", "checksum"}:
        return None
    kind = value.get("type")
    checksum = value.get("checksum")
    if kind == "absent" and checksum is None:
        return {"type": "absent", "checksum": None}
    if (
        kind == "file"
        and isinstance(checksum, str)
        and len(checksum) == 64
        and all(char in "0123456789abcdef" for char in checksum.lower())
    ):
        return {"type": "file", "checksum": checksum.lower()}
    return None


def _presence(path: str) -> str:
    kind = _walk(Path(path))
    if kind == "file":
        return "present"
    if kind == "absent":
        return "absent"
    return "unknown"


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError("duplicate key")
        document[key] = value
    return document


def _constant(_value: str) -> None:
    raise ValueError("non-finite")


def _finite(value: Any) -> bool:
    if isinstance(value, float):
        return value == value and value not in (float("inf"), float("-inf"))
    if isinstance(value, list):
        return all(_finite(item) for item in value)
    if isinstance(value, dict):
        return all(_finite(item) for item in value.values())
    return True


def _strict_json(raw: bytes) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        _fail("invalid-config", "a selected file is not strict UTF-8")
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, RecursionError):
        _fail("invalid-config", "a selected file is not strict JSON")
        raise AssertionError
    if not _finite(value):
        _fail("invalid-config", "a selected file contains a non-finite number")
    return value


def _read_bytes(path: Path) -> bytes:
    if _walk(path) != "file":
        _fail("unsafe-path", "retirement can read only a regular file")
    return _files()["read_file"](path)


def _snapshot(path: Path) -> dict[str, Any]:
    return _files()["snapshot"](path)


def _selections(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _fail("invalid-argument", "selections must be a mapping")
    unknown = set(value) - {"host", "configs", "projects", "vault", "retiring_launchers"}
    if unknown:
        _fail("invalid-argument", "selections contain an unknown field")
    host = value.get("host")
    if host not in {None, "codex", "omp"}:
        _fail("invalid-argument", "retirement host must be codex, omp, or absent")
    configs = value.get("configs", [])
    projects = value.get("projects", [])
    launchers = value.get("retiring_launchers", [])
    if any(isinstance(item, (str, bytes)) or not isinstance(item, Sequence) for item in (configs, projects, launchers)):
        _fail("invalid-argument", "retirement selections are not the closed domain")
    parsed_configs = []
    seen: list[Path] = []
    for item in configs:
        if not isinstance(item, Mapping) or set(item) != {"role", "path"}:
            _fail("invalid-argument", "a selected config must name only role and path")
        role = item.get("role")
        if role not in _ROLES or (host is not None and role not in _HOST_ROLES[host]):
            _fail("invalid-argument", "a selected config role is not valid for the host")
        path = _as_path(item.get("path"), "config path")
        parsed_configs.append({"role": role, "path": path})
        seen.append(path)
    parsed_projects = []
    for item in projects:
        path = _as_path(item, "project root")
        for other in [*seen, *parsed_projects]:
            if path == other or path.is_relative_to(other) or other.is_relative_to(path):
                _fail("scope-conflict", "selected retirement paths must be distinct and non-nested")
        parsed_projects.append(path)
    vault = value.get("vault")
    return {
        "host": host,
        "configs": parsed_configs,
        "projects": parsed_projects,
        "vault": None if vault is None else _as_path(vault, "vault"),
        "retiring_launchers": [str(_as_path(item, "retiring launcher")) for item in launchers],
    }


def _blank(status: str = "absent") -> dict[str, Any]:
    return {
        "schema": REPORT_SCHEMA,
        "status": status,
        "items": [],
        "errors": [],
        "manual": [],
        "proof_gap": None,
        "evidence_descriptor": None,
        "retiring_launchers": [],
        "mode_scope": "lstat-imode",
    }


def _overlap(vault: Path, selections: Mapping[str, Any]) -> None:
    targets = [item["path"] for item in selections["configs"]] + list(selections["projects"])
    for path in targets:
        if path == vault or path.is_relative_to(vault) or vault.is_relative_to(path):
            _fail("scope-conflict", "the retirement vault overlaps a selected path")


def _contained(path: Path, vault: Path) -> None:
    if path == vault or not path.is_relative_to(vault):
        _fail("scope-conflict", "retirement evidence must be a regular file inside the vault")
    if _walk(path) != "file" or _alias(path) or _alias(vault):
        _fail("unsafe-path", "retirement evidence must be a canonical regular file")


def _private_parents(path: Path, vault: Path) -> None:
    require = _files()["require_private_directory"]
    parent = vault
    for part in path.relative_to(vault).parts[:-1]:
        parent /= part
        require(parent)


def _evidence_document(path: Path, vault: Path) -> Any:
    _contained(path, vault)
    if os.name == "nt":
        _private_parents(path, vault)
        _files()["assert_private_file"](path)
    return _strict_json(_read_bytes(path))


def _private_permissions_path(path: Path, private_root: Path) -> Path:
    files = _files()
    private_root = files["require_private_directory"](private_root)
    path = _as_path(path, "Windows ACL backup")
    if path == private_root or not path.is_relative_to(private_root):
        _fail("scope-conflict", "the Windows ACL backup is outside the private vault")
    _private_parents(path, private_root)
    return path


def read_windows_permissions(path: Path, expected_digest: str, *, private_root: Path) -> bytes:
    """Read a private native descriptor whose semantics still match the seal."""
    _require_windows_digest(expected_digest)
    path = _private_permissions_path(path, private_root)
    _contained(path, private_root)
    _files()["assert_private_file"](path)
    raw = _read_bytes(path)
    if windows_permissions.digest(raw) != expected_digest:
        _fail("backup-conflict", "the Windows ACL backup differs from its recorded state")
    return raw


def retain_windows_permissions(path: Path, raw: bytes, expected_digest: str, *, private_root: Path) -> None:
    """Retain descriptor bytes, not the source file's security on the sidecar."""
    _require_windows_digest(expected_digest)
    if windows_permissions.digest(raw) != expected_digest:
        _fail("state-conflict", "the captured Windows ACL differs from the recorded state")
    path = _private_permissions_path(path, private_root)
    if _walk(path) == "absent":
        _files()["write_file"](path, raw, {"type": "absent", "checksum": None}, scope=private_root)
    read_windows_permissions(path, expected_digest, private_root=private_root)


def retained_windows_permissions(backup: Mapping[str, Any], expected_digest: str, *, vault: Path) -> bytes:
    path = _as_path(backup.get("path"), "backup")
    _contained(path, vault)
    _files()["assert_private_file"](path)
    return read_windows_permissions(path.with_name(path.name + ".windows-acl"), expected_digest, private_root=vault)


def _sealed(document: Any, id_key: str, *, extra: frozenset[str] = frozenset()) -> dict[str, Any]:
    required = {"schema_version", "payload", id_key}
    if (
        not isinstance(document, dict)
        or not required <= set(document)
        or set(document) - required - extra
    ):
        _fail("binding-violation", "retirement evidence is not a sealed document")
    if type(document.get("schema_version")) is not int or document["schema_version"] != 1 or not isinstance(document.get("payload"), dict):
        _fail("binding-violation", "retirement evidence is not a sealed document")
    if document.get(id_key) != _digest(document["payload"]):
        _fail("binding-violation", "retirement evidence digest does not match its payload")
    return document["payload"]


def _result(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict) or set(value) != _RESULT_KEYS or value.get("phase") != "deploy":
        return None
    if value.get("status") != "succeeded" or value.get("error") is not None:
        return None
    before = _state(value.get("before"))
    after = _state(value.get("after"))
    operations = value.get("operation_ids")
    resource = value.get("resource_id")
    if (
        before is None
        or after is None
        or not isinstance(operations, list)
        or not operations
        or any(not isinstance(item, str) or len(item) != 64 for item in operations)
        or not isinstance(resource, str)
        or len(resource) != 64
    ):
        return None
    backup = value.get("backup_ref")
    parsed_backup = None
    if backup is not None:
        if not isinstance(backup, dict) or set(backup) != {"path", "state"}:
            return None
        state = _state(backup.get("state"))
        if state is None or state != before:
            return None
        parsed_backup = {"path": backup["path"], "state": state}
    elif before["type"] != "absent":
        return None
    return {
        "resource_id": resource.lower(),
        "operation_ids": [item.lower() for item in operations],
        "before": before,
        "after": after,
        "backup_ref": parsed_backup,
    }


def _operation_results(document: Any) -> list[dict[str, Any]]:
    found: list[Any] = []
    if isinstance(document, dict):
        if "reconciliation" in document:
            return []
        if isinstance(document.get("operationResults"), list):
            found.extend(document["operationResults"])
        wiring = document.get("graftWiring")
        if isinstance(wiring, dict) and "reconciliation" not in wiring and isinstance(wiring.get("operationResults"), list):
            found.extend(wiring["operationResults"])
    results = [item for item in (_result(value) for value in found) if item is not None]
    if not results:
        _fail("binding-violation", "operation evidence does not contain a bound write result")
    return results


def _declared_operations(payload: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    found: list[Any] = []
    shared = payload.get("shared_operations")
    if isinstance(shared, list):
        found.extend(shared)
    projects = payload.get("projects")
    if isinstance(projects, list):
        for project in projects:
            private = project.get("private_operations") if isinstance(project, dict) else None
            if isinstance(private, list):
                found.extend(private)
    declared = {}
    for operation in found:
        if not isinstance(operation, dict):
            continue
        change = operation.get("change")
        if not isinstance(change, dict) or change.get("kind") != "configure-graft":
            continue
        resource = operation.get("resource_id")
        operation_id_value = operation.get("operation_id")
        target = operation.get("target")
        selector = operation.get("selector")
        if not all(isinstance(item, str) for item in (resource, operation_id_value, target, selector)):
            continue
        declared[resource.lower()] = {
            "operation_id": operation_id_value.lower(),
            "target": target,
            "selector": selector,
        }
    return declared


def _deployment_results(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    if "reconciliation" in payload:
        # A successful current-state observation does not establish who wrote it.
        return []
    found: list[Any] = []
    shared = payload.get("shared_results")
    if isinstance(shared, list):
        found.extend(shared)
    projects = payload.get("projects")
    if isinstance(projects, list):
        for project in projects:
            private = project.get("private_results") if isinstance(project, dict) else None
            if isinstance(private, list):
                found.extend(private)
    results = [item for item in (_result(value) for value in found) if item is not None]
    if not results:
        _fail("binding-violation", "deployment evidence does not contain a bound write result")
    return results


def _check_backup(backup: Mapping[str, Any], before: Mapping[str, Any], vault: Path, target: Path | None) -> dict[str, Any]:
    if backup["state"] != before:
        _fail("binding-violation", "retained original state does not match the recorded before state")
    path = _as_path(backup["path"], "backup")
    _contained(path, vault)
    if target is not None and _walk(target) == "file" and os.path.samestat(path.lstat(), target.lstat()):
        _fail("unsafe-path", "a retained original is a link to the live target")
    if _snapshot(path) != before:
        _fail("binding-violation", "a retained original does not match its recorded state")
    return {"path": str(path), "state": dict(before)}


def _bind_results(
    results: Sequence[Mapping[str, Any]],
    selections: Mapping[str, Any],
    kind: str,
    paths: tuple[str, ...],
    vault: Path,
    declared: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    proofs = []
    targets = [(item["role"], str(item["path"])) for item in selections["configs"]]
    targets += [("agents-fence", str(root / "AGENTS.md")) for root in selections["projects"]]
    for result in results:
        if declared is not None:
            operation = declared.get(result["resource_id"])
            if operation is None or operation["operation_id"] not in result["operation_ids"]:
                continue
        for role, target in targets:
            owner, selector = _SELECTORS[role]
            identity = resource_id(owner, target)
            if identity != result["resource_id"]:
                continue
            if declared is not None and (
                declared[result["resource_id"]]["target"] != target
                or declared[result["resource_id"]]["selector"] != selector
            ):
                _fail("binding-violation", "deployment evidence does not match its manifest operation")
            if operation_id("deploy", identity, selector) not in result["operation_ids"]:
                continue
            if result["before"]["checksum"] == result["after"]["checksum"] and result["before"]["type"] == "file":
                continue
            backup = result["backup_ref"]
            checked = None
            if backup is not None:
                checked = _check_backup(backup, result["before"], vault, Path(target))
            proofs.append({
                "kind": kind,
                "paths": paths,
                "target": target,
                "role": role,
                "before": result["before"],
                "after": result["after"],
                "operation": "install" if result["before"]["type"] == "absent" else "replace",
                "backup_ref": checked,
            })
    return proofs


def _upgrade_wrapper(document: Mapping[str, Any], path: Path, payload: Mapping[str, Any]) -> None:
    if "status" in document and document["status"] != payload.get("status"):
        _fail("binding-violation", "upgrade receipt wrapper status does not match its payload")
    if "receipt_path" not in document:
        return
    declared = _as_path(document["receipt_path"], "receipt_path")
    if declared != path or _walk(declared) != "file" or _alias(declared):
        _fail("binding-violation", "upgrade receipt_path is not the file that was read")


def _upgrade_proofs(
    plan: Mapping[str, Any],
    receipt: Mapping[str, Any],
    selections: Mapping[str, Any],
    paths: tuple[str, ...],
    vault: Path,
) -> list[dict[str, Any]]:
    if plan.get("plan_schema") != "upgrade-plan" or receipt.get("receipt_schema") != "upgrade-receipt":
        _fail("binding-violation", "upgrade evidence is not a plan and apply receipt")
    if receipt.get("plan_id") != _digest(plan):
        _fail("binding-violation", "upgrade receipt is not bound to its plan")
    resources = plan.get("resources")
    rows = receipt.get("resources")
    if not isinstance(resources, list) or not isinstance(rows, list):
        _fail("binding-violation", "upgrade evidence is not a plan and apply receipt")
    by_id: dict[str, Mapping[str, Any]] = {}
    for resource in resources:
        if not isinstance(resource, dict) or not isinstance(resource.get("id"), str) or resource["id"] in by_id:
            _fail("binding-violation", "upgrade plan resources are not the producer shape")
        by_id[resource["id"]] = resource
    selected = {str(item["path"]): item["role"] for item in selections["configs"]}
    selected.update({str(root / "AGENTS.md"): "agents-fence" for root in selections["projects"]})
    proofs = []
    for row in rows:
        if (
            not isinstance(row, dict)
            or _UPGRADE_ROW_KEYS - set(row)
            or set(row) - _UPGRADE_ROW_KEYS - _ROW_OPTIONAL
            or not isinstance(row.get("created_parents"), list)
        ):
            _fail("binding-violation", "upgrade receipt row is not the producer shape")
        resource = by_id.get(row["id"])
        if resource is None or any(row.get(key) != resource.get(key) for key in _UPGRADE_BIND):
            _fail("binding-violation", "upgrade receipt row is not bound to its plan resource")
        if row.get("result") != "succeeded" or row.get("mutated") is not True:
            continue
        if row.get("decision") not in {"install", "replace"}:
            continue
        target = row.get("target")
        role = selected.get(target)
        if not isinstance(target, str) or role is None:
            continue
        if (role == "agents-fence" and row.get("kind") != "agents") or (
            role != "agents-fence" and row.get("kind") != "mcp"
        ):
            continue
        after = _state(row.get("after"))
        before = _state(row.get("before"))
        desired = _state(row.get("desired")) if row.get("desired") is not None else None
        if after is None or before is None or desired != after or after["type"] != "file" or before == after:
            continue
        if _state(row.get("mechanical_before")) != before or _state(row.get("mechanical_after")) != after:
            continue
        if row["decision"] != ("install" if before["type"] == "absent" else "replace"):
            _fail("binding-violation", "upgrade mutation contradicts its recorded before state")
        if ".." in Path(target).parts:
            _fail("unsafe-path", "upgrade evidence target is not canonical")
        backup = row.get("backup_ref")
        checked = None
        if before["type"] != "absent":
            if not isinstance(backup, dict) or set(backup) != {"path", "state"} or _state(backup.get("state")) != before:
                _fail("binding-violation", "upgrade receipt backup is not the recorded original")
            checked = _check_backup({"path": backup.get("path"), "state": before}, before, vault, Path(target))
        elif backup is not None:
            continue
        details = resource.get("details") if isinstance(resource.get("details"), dict) else {}
        launcher = details.get("launcher") if isinstance(details.get("launcher"), dict) else {}
        launcher_path = launcher.get("path")
        if isinstance(launcher_path, str) and (not _abs(launcher_path) or ".." in Path(launcher_path).parts):
            launcher_path = None
        proofs.append({
            "kind": "upgrade-plan-apply",
            "paths": paths,
            "target": target,
            "role": role,
            "before": before,
            "after": after,
            "operation": row["decision"],
            "backup_ref": checked,
            "launcher": launcher_path if isinstance(launcher_path, str) else None,
        })
    return proofs


def _binding_paths(item: Mapping[str, Any], vault: Path) -> tuple[str, ...]:
    kind = item.get("kind")
    keys = {
        "operation-results": ("path",),
        "manifest-deployment": ("manifest", "deployment"),
        "upgrade-plan-apply": ("plan", "receipt"),
    }.get(kind)
    if keys is None or set(item) != {"kind", *keys}:
        _fail("binding-violation", "retirement evidence binding is not a recognized shape")
    paths = tuple(_as_path(item.get(key), key) for key in keys)
    if any(path == vault or not path.is_relative_to(vault) for path in paths):
        _fail("scope-conflict", "retirement evidence must be inside the vault")
    return tuple(str(path) for path in paths)


def _proofs_from_binding(item: Mapping[str, Any], selections: Mapping[str, Any], vault: Path) -> list[dict[str, Any]]:
    paths = _binding_paths(item, vault)
    kind = item["kind"]
    if kind == "operation-results":
        return _bind_results(_operation_results(_evidence_document(Path(paths[0]), vault)), selections, kind, paths, vault)
    if kind == "manifest-deployment":
        manifest = _sealed(_evidence_document(Path(paths[0]), vault), "manifest_id")
        deployment = _sealed(_evidence_document(Path(paths[1]), vault), "deployment_id")
        if deployment.get("manifest_id") != _digest(manifest):
            _fail("binding-violation", "deployment evidence is not bound to its manifest")
        return _bind_results(
            _deployment_results(deployment),
            selections,
            kind,
            paths,
            vault,
            _declared_operations(manifest),
        )
    receipt_path = Path(paths[1])
    receipt_document = _evidence_document(receipt_path, vault)
    plan = _sealed(_evidence_document(Path(paths[0]), vault), "plan_id")
    receipt = _sealed(receipt_document, "receipt_id", extra=_UPGRADE_WRAPPER)
    _upgrade_wrapper(receipt_document, receipt_path, receipt)
    return _upgrade_proofs(plan, receipt, selections, paths, vault)


def _load_evidence(
    evidence: Sequence[Any], selections: Mapping[str, Any], vault: Path | None
) -> tuple[list[dict[str, Any]], dict[str, str] | None]:
    if not evidence:
        return [], None
    if vault is None:
        _fail("invalid-argument", "retirement evidence requires a private vault")
    if len(evidence) == 1 and isinstance(evidence[0], Mapping) and evidence[0].get("kind") == "descriptor":
        if set(evidence[0]) != {"kind", "path"}:
            _fail("binding-violation", "retirement evidence descriptor is malformed")
        path = _as_path(evidence[0].get("path"), "descriptor")
        payload = _sealed(_evidence_document(path, vault), "descriptor_id")
        if payload.get("schema") != DESCRIPTOR_SCHEMA or not isinstance(payload.get("items"), list):
            _fail("binding-violation", "retirement evidence descriptor is malformed")
        proofs: list[dict[str, Any]] = []
        for item in payload["items"]:
            if not isinstance(item, Mapping):
                _fail("binding-violation", "retirement evidence binding is not a recognized shape")
            proofs.extend(_proofs_from_binding(item, selections, vault))
        return proofs, {"path": str(path), "descriptor_id": _digest(payload)}
    proofs = []
    for item in evidence:
        if not isinstance(item, Mapping):
            _fail("binding-violation", "retirement evidence binding is not a recognized shape")
        proofs.extend(_proofs_from_binding(item, selections, vault))
    return proofs, None


def _fixed_key(root: str) -> str:
    return f"{_GLOBAL_KEY}-{hashlib.sha256(root.encode('utf-8')).hexdigest()[:16]}"


def _abs(value: object) -> bool:
    return isinstance(value, str) and os.path.isabs(value)


def _mcp_launcher(key: str, entry: Mapping[str, Any], *, omp: bool) -> str | None:
    """Return the launcher only for the producer argv, never a name-only key."""
    if key != _GLOBAL_KEY and not key.startswith(f"{_GLOBAL_KEY}-"):
        return None
    args = entry.get("args")
    command = entry.get("command")
    if not _abs(command) or not isinstance(args, list) or any(not isinstance(token, str) for token in args):
        return None
    if entry.get("env") != _ENV:
        return None
    base = {"type", "command", "args", "env"} if omp else {"command", "args", "env"}
    if omp and entry.get("type") != "stdio":
        return None
    if set(entry) == base and list(args) == [
        *_FLAGS, args[2] if len(args) > 2 else "", "mcp", "--node", args[5] if len(args) > 5 else "", "--entry", args[7] if len(args) > 7 else "",
    ] and len(args) == 8 and args[3] == "mcp" and all(_abs(args[index]) for index in (2, 5, 7)):
        if key == _GLOBAL_KEY:
            return args[2]
        return None
    if set(entry) != base | {"cwd"} or len(args) != 10 or args[:2] != list(_FLAGS) or args[3] != "mcp":
        return None
    if args[4::2] != ["--root", "--node", "--entry"]:
        return None
    root, launcher, node, cli = args[5], args[2], args[7], args[9]
    if key == _fixed_key(root) and entry.get("cwd") == root and all(_abs(item) for item in (root, launcher, node, cli)):
        return launcher
    return None


def _cmd_split(command: str) -> list[str]:
    argv: list[str] = []
    index = 0
    while index < len(command):
        while index < len(command) and command[index] in " \t":
            index += 1
        if index >= len(command):
            break
        token: list[str] = []
        quoted = False
        while index < len(command):
            char = command[index]
            if char == '"':
                quoted = not quoted
                index += 1
                continue
            if not quoted and char in " \t":
                break
            token.append(char)
            index += 1
        argv.append("".join(token))
    return argv


def _hook_argv(command: str) -> list[str] | None:
    if os.name == "nt":
        return _cmd_split(command)
    try:
        return shlex.split(command)
    except ValueError:
        return None


def _hook_identity(command: str) -> tuple[str, str] | None:
    argv = _hook_argv(command)
    if argv is None:
        return None
    if len(argv) == 13 and argv[1:3] == list(_FLAGS) and argv[4] == "hook":
        flags = argv[5:]
        launcher = argv[3]
    elif len(argv) == 11 and argv[2] == "hook":
        flags = argv[3:]
        launcher = argv[1]
    else:
        return None
    if flags[0::2] != ["--root", "--node", "--entry", "--event"]:
        return None
    event = flags[7]
    if event not in _HOOK_EVENTS or not all(_abs(item) for item in (launcher, flags[1], flags[3], flags[5])):
        return None
    return _HOOK_EVENTS[event], launcher


def _hook_entry(event: str, command: str) -> str:
    # The full command identifies a hook without disclosing its arguments.
    return f"{event}:{_digest(command)}"


def _toml_document(raw: bytes) -> dict[str, Any]:
    if not raw.strip():
        return {}
    try:
        import tomlkit
    except ImportError:
        _fail("runtime-unavailable", "the TOML parser is unavailable")
        raise AssertionError
    try:
        document = tomlkit.parse(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        _fail("invalid-config", "a selected file is not strict TOML")
        raise AssertionError
    return document.unwrap() if hasattr(document, "unwrap") else dict(document)


def _json_document(raw: bytes) -> dict[str, Any]:
    if not raw.strip():
        return {}
    document = _strict_json(raw)
    if not isinstance(document, dict):
        _fail("invalid-config", "a selected MCP document is not an object")
    return document


def _servers(document: Mapping[str, Any], *, omp: bool) -> dict[str, Any]:
    key = _table_key(document, omp=omp)
    servers = document.get(key, {})
    if not isinstance(servers, dict):
        _fail("invalid-config", "a selected MCP table is not a table")
    return servers


def _plain(value: Any) -> Any:
    if hasattr(value, "unwrap"):
        value = value.unwrap()
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def _same_value(before: Any, after: Any) -> bool:
    if type(before) is not type(after):
        return False
    if isinstance(before, dict):
        return before.keys() == after.keys() and all(
            _same_value(value, after[key]) for key, value in before.items()
        )
    if isinstance(before, list):
        return len(before) == len(after) and all(
            _same_value(left, right) for left, right in zip(before, after)
        )
    return before == after


def _table_key(document: Mapping[str, Any], *, omp: bool) -> str:
    if not omp and "mcp_servers" in document and "mcpServers" in document:
        _fail("invalid-config", "a selected Codex file has ambiguous MCP server tables")
    return "mcpServers" if omp or "mcpServers" in document else "mcp_servers"


def _foreign_same(before: Mapping[str, Any], after: Mapping[str, Any], table: str) -> bool:
    before_keys = set(before) - {table}
    after_keys = set(after) - {table}
    if before_keys != after_keys:
        return False
    return all(_same_value(_plain(before[key]), _plain(after[key])) for key in before_keys)


def _attribute_mcp(before: bytes | None, after: bytes, *, omp: bool, toml: bool) -> tuple[list[tuple[str, str]], bool] | None:
    after_document = _toml_document(after) if toml else _json_document(after)
    table = _table_key(after_document, omp=omp)
    after_servers = _servers(after_document, omp=omp)
    if before is None:
        if set(after_document) - {table}:
            return None
        managed = []
        for key, entry in after_servers.items():
            if not isinstance(entry, Mapping):
                return None
            launcher = _mcp_launcher(key, _plain(entry), omp=omp)
            if launcher is None:
                return None
            managed.append((key, launcher))
        return (managed, True) if managed else None
    before_document = _toml_document(before) if toml else _json_document(before)
    if not _foreign_same(before_document, after_document, table):
        return None
    if table in before_document and table not in after_document and after_document.get(table) not in (None, {}):
        return None
    before_servers = _servers(before_document, omp=omp) if table in before_document or omp else {}
    if table not in before_document and not omp and "mcp_servers" not in before_document and "mcpServers" not in before_document:
        before_servers = {}
    attributable = []
    for key, entry in after_servers.items():
        plain = _plain(entry)
        launcher = _mcp_launcher(key, plain, omp=omp) if isinstance(plain, Mapping) else None
        previous = before_servers.get(key)
        if launcher is None:
            if key not in before_servers or not _same_value(_plain(previous), plain):
                return None
            continue
        if _same_value(_plain(previous), plain):
            continue
        attributable.append((key, launcher))
    for key, entry in before_servers.items():
        if key not in after_servers and _mcp_launcher(key, _plain(entry) if isinstance(entry, Mapping) else {}, omp=omp) is None:
            return None
    if table not in before_document and table in after_document and not attributable:
        return None
    return attributable, False


def _group_hooks(group: Any) -> list[dict[str, Any]] | None:
    if (
        not isinstance(group, dict) or set(group) - {"matcher", "hooks"}
        or (group.get("matcher") is not None and not isinstance(group["matcher"], str))
    ):
        return None
    hooks = group.get("hooks", [])
    if not isinstance(hooks, list) or any(
        not isinstance(hook, dict) or not isinstance(hook.get("command"), str) for hook in hooks
    ):
        return None
    return hooks


def _hook_commands(document: Mapping[str, Any]) -> dict[str, list[str]]:
    hooks = document.get("hooks", {})
    if not isinstance(hooks, dict):
        _fail("invalid-config", "a selected Codex hooks table is malformed")
    found: dict[str, list[str]] = {}
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            _fail("invalid-config", "a selected Codex hook event is malformed")
        commands = []
        for group in groups:
            entries = _group_hooks(group)
            if entries is None:
                _fail("invalid-config", "a selected Codex hook group is malformed")
            commands.extend(item["command"] for item in entries)
        found[event] = commands
    return found


def _strict_groups(groups: Any) -> list[str] | None:
    if not isinstance(groups, list):
        return None
    commands = []
    for group in groups:
        hooks = _group_hooks(group)
        if hooks is None:
            return None
        commands.extend(hook["command"] for hook in hooks)
    if len(commands) != len(set(commands)):
        return None
    return commands


def _retained_hook_groups(groups: list, commands: set[str]) -> list[dict[str, Any]]:
    retained = []
    for group in groups:
        original = group.get("hooks", [])
        hooks = [hook for hook in original if hook["command"] in commands]
        if not original:
            retained.append(group)
        elif hooks:
            retained.append({**group, "hooks": hooks})
    return retained


def _attribute_hooks(before: bytes | None, after: bytes) -> tuple[list[tuple[str, str]], bool] | None:
    after_document = _json_document(after)
    if before is None:
        if set(after_document) - {"hooks"}:
            return None
        hooks = after_document.get("hooks")
        if not isinstance(hooks, dict) or not hooks:
            return None
        owned = []
        for event, groups in hooks.items():
            commands = _strict_groups(groups)
            if not commands or any(not group.get("hooks") for group in groups):
                return None
            for command in commands:
                identity = _hook_identity(command)
                if identity is None or identity[0] != event:
                    return None
                owned.append((_hook_entry(event, command), identity[1]))
        return (owned, True) if owned else None
    before_document = _json_document(before)
    if not _foreign_same(before_document, after_document, "hooks"):
        return None
    before_hooks = before_document.get("hooks", {})
    after_hooks = after_document.get("hooks", {})
    if not isinstance(before_hooks, dict) or not isinstance(after_hooks, dict):
        return None
    attributable = []
    for event in set(before_hooks) | set(after_hooks):
        previous = before_hooks.get(event, [])
        current = after_hooks.get(event, [])
        if _same_value(previous, current):
            if (event in before_hooks) != (event in after_hooks):
                return None
            continue
        previous_commands = _strict_groups(previous)
        current_commands = _strict_groups(current)
        if previous_commands is None or current_commands is None or previous_commands == current_commands:
            return None
        shared = set(previous_commands).intersection(current_commands)
        if not _same_value(_retained_hook_groups(previous, shared), _retained_hook_groups(current, shared)):
            return None
        for command in current_commands:
            if command in shared:
                continue
            identity = _hook_identity(command)
            if identity is None or identity[0] != event:
                return None
            attributable.append((_hook_entry(event, command), identity[1]))
        for command in previous_commands:
            if command not in shared:
                identity = _hook_identity(command)
                if identity is None or identity[0] != event:
                    return None
    if "hooks" not in before_document and attributable == []:
        return None
    return attributable, False


def _fence_span(text: str) -> tuple[int, int] | None:
    if text.count(_FENCE_START) != 1 or text.count(_FENCE_END) != 1:
        return None
    start = text.index(_FENCE_START)
    end = text.index(_FENCE_END)
    if end < start:
        return None
    end += len(_FENCE_END)
    if text[end:end + 1] == "\n":
        end += 1
    return start, end


def _producer_prefix(text: str) -> str:
    prefix = text
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    if prefix and not prefix.endswith("\n\n"):
        prefix += "\n"
    return prefix


def _created_fence(text: str) -> bool:
    span = _fence_span(text)
    if span != (0, len(text)) or not text.endswith("\n"):
        return False
    inner_start = len(_FENCE_START) + 1
    inner_end = text.index(_FENCE_END) - 1
    if inner_end < inner_start or text[len(_FENCE_START):inner_start] != "\n" or text[inner_end:inner_end + 1] != "\n":
        return False
    inner = text[inner_start:inner_end]
    return _sha(inner.encode()) == _FENCE_BODY_SHA and text == f"{_FENCE_START}\n{inner}\n{_FENCE_END}\n"


def _attribute_fence(before: bytes | None, after: bytes) -> tuple[list[tuple[str, str]], bool] | None:
    try:
        text = after.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if before is None:
        return ([("graft-fence", "")], True) if _created_fence(text) else None
    try:
        original = before.decode("utf-8")
    except UnicodeDecodeError:
        return None
    span = _fence_span(text)
    if span is None:
        return None
    start, end = span
    before_span = _fence_span(original)
    if before_span is not None:
        left, right = before_span
        if left == start and original[:left] == text[:start] and original[right:] == text[end:]:
            return [("graft-fence", "")], False
        return None
    prefix = _producer_prefix(original)
    if start != len(prefix) or end != len(text) or not text.startswith(prefix):
        return None
    return [("graft-fence", "")], False


def _item(
    *,
    role: str,
    path: str,
    entry: str,
    status: str,
    reason: str,
    write: bool,
    mode: str | None,
    windows_acl_digest: str | None,
    action: str | None,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    desired: dict[str, Any] | None,
    launcher: str | None,
    evidence: Mapping[str, Any] | None,
    recognized: bool,
    body: str,
    points: bool,
    backup_ref: dict[str, Any] | None,
) -> dict[str, Any]:
    ownership = status
    presence = _presence(launcher) if launcher else None
    if mode is None or (os.name == "nt" and windows_acl_digest is None):
        write = False
    if presence == "absent":
        status = "dangling"
    writable = write and ownership == "proven" and isinstance(mode, str)
    at_risk = bool(launcher) and not writable and (points or presence == "absent")
    return {
        "id": _digest([role, path, entry]),
        "role": role,
        "path": path,
        "entry": entry,
        "status": status,
        "classification": status,
        "verification": ownership,
        "write_authority": writable,
        "reason": reason,
        "global_effect": role != "agents-fence",
        "guidance": "Do not delete this entry by name." if not writable else None,
        "launcher": None if launcher is None else {"path": launcher, "present": presence == "present", "presence": presence},
        "historical_mode": "unknown",
        "mode": mode,
        **({"windows_acl_digest": windows_acl_digest} if os.name == "nt" else {}),
        "action": action if writable else None,
        "before": before,
        "recorded_after": after,
        "desired": desired if writable else None,
        "backup_ref": backup_ref if writable else None,
        "evidence_kind": None if evidence is None else evidence["kind"],
        "evidence_paths": [] if evidence is None else list(evidence["paths"]),
        "body_policy": body,
        "recognized": recognized,
        "at_risk": at_risk,
    }


def _proof_for(proofs: Sequence[Mapping[str, Any]], target: str) -> Mapping[str, Any] | None:
    matched = [item for item in proofs if item["target"] == target]
    if not matched:
        return None
    first = matched[0]
    if any(any(proof[key] != first[key] for key in ("role", "before", "after", "operation")) for proof in matched[1:]):
        return {"conflict": True}
    if len({proof["launcher"] for proof in matched if proof.get("launcher")}) > 1:
        return {"conflict": True}
    # Use the stricter binding when equivalent evidence omits a launcher.
    return min(matched, key=lambda proof: (not proof.get("launcher"), proof["kind"], proof["paths"]))


def _launcher_paths(launcher: str) -> set[Path]:
    """Alternate spellings for dependency reporting only; never a file authority."""
    if not _abs(launcher) or "\x00" in launcher:
        return set()
    paths = {Path(os.path.normpath(launcher))}
    try:
        paths.add(Path(os.path.realpath(launcher)))
    except (OSError, ValueError, RuntimeError):
        pass
    return paths


def _retiring_paths(launchers: Sequence[str]) -> set[Path]:
    return {path for launcher in launchers for path in _launcher_paths(launcher)}


def _launcher_token(values: Sequence[Any], retiring: set[Path], *, cwd: Any = None) -> str | None:
    for value in values:
        if not isinstance(value, str) or not value or "\x00" in value:
            continue
        if not _abs(value):
            if not _abs(cwd):
                continue
            value = os.path.join(cwd, value)
        if _points_at_retiring(value, retiring):
            return value
        path = Path(os.path.normpath(value))
        if Path(path.name) == Path(_LAUNCHER_NAME) and _presence(str(path)) == "absent":
            return str(path)
    return None


def _points_at_retiring(launcher: str, retiring: set[Path]) -> bool:
    return bool(retiring and _launcher_paths(launcher) & retiring)


def _watch(raw: bytes, role: str, retiring: set[Path]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Split producer-shaped launchers from token hits. A name is not ownership."""
    recognized: list[tuple[str, str]] = []
    pointed: list[tuple[str, str]] = []
    if role == "agents-fence":
        return recognized, pointed
    if role == "codex-hooks":
        commands = _hook_commands(_json_document(raw))
        for event, values in commands.items():
            for command in values:
                identity = _hook_identity(command)
                if identity and identity[0] == event:
                    recognized.append((_hook_entry(event, command), identity[1]))
                else:
                    launcher = _launcher_token(_hook_argv(command) or [], retiring)
                    if launcher:
                        pointed.append((_hook_entry(event, command), launcher))
        return recognized, pointed
    omp = role == "omp-mcp"
    document = _toml_document(raw) if role == "codex-mcp" else _json_document(raw)
    for key, entry in _servers(document, omp=omp).items():
        if not isinstance(entry, Mapping):
            continue
        plain = _plain(entry)
        launcher = _mcp_launcher(key, plain, omp=omp)
        if launcher:
            recognized.append((key, launcher))
            continue
        values = [plain.get("command")]
        args = plain.get("args")
        if isinstance(args, list):
            values.extend(args)
        launcher = _launcher_token(values, retiring, cwd=plain.get("cwd"))
        if launcher:
            pointed.append((key, launcher))
    return recognized, pointed


def _host_role(candidate: Mapping[str, Any]) -> str:
    role = candidate.get("role")
    if role == "agents-fence" or candidate.get("format") == "agents":
        return "agents-fence"
    if role == "codex-hooks":
        return "codex-hooks"
    if role == "codex-mcp" or candidate.get("format") == "toml":
        return "codex-mcp"
    return "omp-mcp"


def _json_drop(raw: bytes, table: str, keys: Sequence[str]) -> bytes | None:
    document = _json_document(raw)
    if not isinstance(document.get(table), dict):
        return None
    edited = {key: value for key, value in document.items() if key != table}
    servers = {key: value for key, value in document[table].items() if key not in set(keys)}
    if servers:
        edited[table] = servers
    if canonical_json_bytes(document) == raw:
        return canonical_json_bytes(edited)
    text = json.dumps(document, indent=2, ensure_ascii=False)
    if raw.endswith(b"\n"):
        text += "\n"
    if text.encode() != raw:
        return None
    rendered = json.dumps(edited, indent=2, ensure_ascii=False)
    if raw.endswith(b"\n"):
        rendered += "\n"
    return rendered.encode()


def _toml_drop(raw: bytes, table: str, keys: Sequence[str]) -> bytes | None:
    try:
        import tomlkit
    except ImportError:
        return None
    try:
        document = tomlkit.parse(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        return None
    servers = document.get(table)
    if servers is None:
        return None
    for key in keys:
        if key in servers:
            del servers[key]
    try:
        rendered = tomlkit.dumps(document).encode()
    except (ValueError, RecursionError, UnicodeError):
        return None
    before = _toml_document(raw)
    after = _toml_document(rendered)
    remaining = {key: value for key, value in before[table].items() if key not in keys}
    if not _foreign_same(before, after, table) or not _same_value(remaining, after.get(table, {})):
        return None
    return rendered


def _selective_remove(live: bytes, role: str, keys: Sequence[str]) -> bytes | None:
    if role == "omp-mcp":
        return _json_drop(live, "mcpServers", keys)
    if role == "codex-mcp":
        return _toml_drop(live, _table_key(_toml_document(live), omp=False), keys)
    return None


def _safe_retired(
    original: bytes, live: bytes, role: str, keys: Sequence[str], retiring: set[Path],
) -> bytes | None:
    if role == "agents-fence":
        return original
    recognized_live, _ = _watch(live, role, retiring)
    live_entries = set(recognized_live)

    def safe(rendered: bytes) -> bool:
        recognized, pointed = _watch(rendered, role, retiring)
        return not (pointed or set(recognized) - live_entries or any(
            entry in keys or _points_at_retiring(launcher, retiring) or _presence(launcher) == "absent"
            for entry, launcher in recognized
        ))

    if safe(original):
        return original
    if role not in {"omp-mcp", "codex-mcp"}:
        return None
    document = _json_document(original) if role == "omp-mcp" else _toml_document(original)
    if any(key in _servers(document, omp=role == "omp-mcp") for key in keys):
        # Removing a replacement would discard a prior entry, not just the owned addition.
        return None
    rendered = _selective_remove(live, role, keys)
    return rendered if rendered is not None and rendered != live and safe(rendered) else None


def _retired_from_candidate(original: bytes, live: bytes, candidate: Mapping[str, Any]) -> bytes:
    role = _host_role(candidate)
    if role == "codex-hooks":
        attributed = _attribute_hooks(original, live)
    elif role == "agents-fence":
        attributed = _attribute_fence(original, live)
    else:
        attributed = _attribute_mcp(original, live, omp=role == "omp-mcp", toml=role == "codex-mcp")
    if not attributed or attributed[1]:
        _fail("ownership-conflict", "live bytes are not an attributable edit of the retained original")
    keys = [item.get("entry") for item in candidate.get("entries") or [] if isinstance(item, Mapping)]
    if set(keys) != {entry for entry, _launcher in attributed[0]}:
        _fail("binding-violation", "retirement candidate entries differ from the proved changes")
    retiring = _retiring_paths(candidate.get("retiring_launchers", []))
    rendered = _safe_retired(original, live, role, keys, retiring)
    if rendered is None:
        _fail("unsupported-operation", "retirement would leave or restore an older launcher dependency")
    return rendered


def _classify_file(
    path: Path,
    role: str,
    raw: bytes,
    proof: Mapping[str, Any] | None,
    retiring: set[Path],
    errors: list[dict[str, str]],
) -> list[dict[str, Any]]:
    mode = _mode(path)
    live = {"type": "file", "checksum": _sha(raw)}
    toml = role == "codex-mcp"
    omp = role == "omp-mcp"
    original = None
    if proof and proof.get("backup_ref"):
        original = _read_bytes(Path(proof["backup_ref"]["path"]))
        if _sha(original) != proof["before"]["checksum"] or proof["backup_ref"]["state"] != proof["before"]:
            proof = {"conflict": True}
    if role == "codex-hooks":
        attributed = _attribute_hooks(original, raw)
    elif role == "agents-fence":
        attributed = _attribute_fence(original, raw)
    else:
        attributed = _attribute_mcp(original, raw, omp=omp, toml=toml)
    entries = attributed[0] if attributed else []
    created_only = bool(attributed and attributed[1])
    proven = bool(
        proof
        and not proof.get("conflict")
        and proof["after"] == live
        and entries
        and (proof["before"]["type"] == "absent" or original is not None)
    )
    if proof and not proof.get("conflict") and proof.get("before", {}).get("type") == "absent" and not created_only:
        proven = False
    file_safe = None
    replay_blocked = False
    if proven and original is not None and not created_only:
        file_safe = _safe_retired(original, raw, role, [entry for entry, _launcher in entries], retiring)
        if file_safe is None:
            replay_blocked = True
            proven = False
    recognized_live, pointed = _watch(raw, role, retiring)
    shown = {entry: launcher for entry, launcher in recognized_live}
    shown.update({entry: launcher for entry, launcher in pointed})
    recognized_names = {entry for entry, _launcher in entries}
    recognized_names.update(entry for entry, _launcher in recognized_live)
    for entry, launcher in entries:
        shown[entry] = launcher
    if role == "agents-fence" and (_FENCE_START.encode() in raw or _FENCE_END.encode() in raw):
        shown.setdefault("graft-fence", "")
    if not shown:
        return []
    upgrade_launcher = None if not proof or proof.get("conflict") else proof.get("launcher")
    writable = {
        entry for entry, launcher in entries
        if proven and (not upgrade_launcher or not launcher or upgrade_launcher == launcher)
    }
    # A file is only retired as a unit. No entry can be retired if a sibling
    # prevents the file edit, even when this entry's ownership was proven.
    whole_file_writable = writable == shown.keys()
    acl_digest = None
    if os.name == "nt" and writable and whole_file_writable:
        try:
            acl_digest = windows_permissions.digest(windows_permissions.capture(path))
        except (ContractError, OSError):
            errors.append({
                "path": str(path),
                "code": "windows-permissions-unproven",
                "reason": "Windows owner, group and DACL could not be verified; preserve this file.",
            })
    items = []
    for entry, launcher in sorted(shown.items()):
        this_write = entry in writable
        if proof and not proof.get("conflict") and proof["after"] != live:
            status, reason, this_write = "drifted", "live bytes differ from the recorded post-write state", False
        elif this_write:
            status, reason = "proven", "the retained original shows this entry changed"
        elif proof and proof.get("conflict"):
            status, reason = "not-verified", "retirement evidence disagrees or does not match the retained original"
        elif replay_blocked:
            status, reason = "unproven", "retirement would leave or restore an older launcher dependency"
        else:
            status, reason = "unproven", "no attributable managed change was proven"
        if this_write and not whole_file_writable:
            reason = "another entry in this file is not attributable"
        if this_write and whole_file_writable and os.name == "nt" and acl_digest is None:
            reason = "the Windows permissions could not be verified"
        action = "remove-file" if this_write and created_only else "edit" if this_write else None
        desired = {"type": "absent", "checksum": None} if action == "remove-file" else (
            {"type": "file", "checksum": _sha(file_safe)} if action == "edit" and file_safe is not None else None
        )
        items.append(_item(
            role="fixed-root-mcp" if entry in recognized_names and entry.startswith(f"{_GLOBAL_KEY}-") else role,
            path=str(path), entry=entry, status=status, reason=reason, write=this_write and whole_file_writable,
            mode=mode, windows_acl_digest=acl_digest, action=action, before=live,
            after=None if not proof or proof.get("conflict") else proof["after"],
            desired=desired, launcher=launcher or None,
            evidence=None if not this_write or not proof or proof.get("conflict") else proof,
            recognized=entry in recognized_names,
            body="remove" if action == "remove-file" else "preserve",
            points=_points_at_retiring(launcher, retiring),
            backup_ref=None if not this_write or not proof or proof.get("conflict") else proof.get("backup_ref"),
        ))
    return items


def _inspect_path(path: Path, errors: list[dict[str, str]]) -> bytes | None:
    kind = _walk(path)
    if kind == "absent":
        return None
    if kind != "file":
        errors.append({
            "path": str(path),
            "code": "unsafe-path",
            "reason": "selected path is not a readable regular file",
        })
        return None
    try:
        return _read_bytes(path)
    except ContractError as error:
        errors.append({"path": str(path), "code": error.code, "reason": error.message})
        return None


def _manual(projects: Sequence[Path]) -> list[dict[str, Any]]:
    """Display manual commands; never probe npm or the user's telemetry file."""
    found = []
    powershell = os.name == "nt"
    for root in projects:
        if _walk(root) != "other":
            continue
        for name in HISTORY_DIRS:
            child = root / name
            if _walk(child) == "other" and child.is_dir():
                found.append({
                    "kind": "graph" if name == "graft" else "graph-state",
                    "path": str(child),
                    "cwd": str(root),
                    "command": (f"Remove-Item -LiteralPath '.\\{name}' -Recurse -Confirm"
                                if powershell else f"rm -ri -- ./{name}"),
                })
    found.append({"kind": "npm", "path": "<npm root -g>/@nanonets/graft",
                  "command": "npm uninstall -g @nanonets/graft"})
    found.append({
        "kind": "telemetry",
        "path": "~/.graft/telemetry.json",
        "command": ('Remove-Item -LiteralPath "$HOME/.graft/telemetry.json" -Confirm'
                    if powershell else 'rm -i -- "$HOME/.graft/telemetry.json"'),
    })
    return found


def inspect_retirement(
    *,
    selections: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Read-only report. A missing file is absent; a link is not."""
    parsed = _selections(selections)
    if not parsed["configs"] and not parsed["projects"] and not evidence and not parsed["retiring_launchers"]:
        return _blank()
    vault = parsed["vault"]
    if vault is not None or evidence:
        if vault is None:
            _fail("invalid-argument", "retirement evidence requires a private vault")
        vault = _files()["require_private_directory"](vault)
        _overlap(vault, parsed)
    proofs, descriptor = _load_evidence(evidence, parsed, vault)
    retiring = _retiring_paths(parsed["retiring_launchers"])
    items: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for config in parsed["configs"]:
        raw = _inspect_path(config["path"], errors)
        if raw is None:
            continue
        try:
            items.extend(_classify_file(
                config["path"], config["role"], raw, _proof_for(proofs, str(config["path"])),
                retiring, errors,
            ))
        except ContractError as error:
            if error.code != "invalid-config":
                raise
            errors.append({"path": str(config["path"]), "code": error.code, "reason": error.message})
    for root in parsed["projects"]:
        agents = root / "AGENTS.md"
        raw = _inspect_path(agents, errors)
        if raw is None:
            continue
        items.extend(_classify_file(
            agents, "agents-fence", raw, _proof_for(proofs, str(agents)), retiring, errors,
        ))
    items.sort(key=lambda item: (item["path"], item["role"], item["entry"]))
    report = _blank("blocked" if errors else "reported")
    report.update(
        items=items,
        errors=errors,
        manual=_manual(parsed["projects"]),
        evidence_descriptor=descriptor,
        retiring_launchers=list(parsed["retiring_launchers"]),
    )
    return report


def _candidate(group: Sequence[Mapping[str, Any]], launchers: Sequence[str]) -> dict[str, Any] | None:
    first = group[0]
    if any(any(item.get(key) != first.get(key) for key in (
        "action", "before", "desired", "mode", "backup_ref",
    )) for item in group[1:]):
        return None
    path = Path(str(first["path"]))
    if not isinstance(first.get("mode"), str) or _mode(path) != first.get("mode"):
        _fail("state-conflict", "captured mode does not match the live file")
    if _walk(path) != "file" or _snapshot(path) != first.get("before"):
        return None
    acl_digest = first.get("windows_acl_digest")
    if os.name == "nt":
        if not _is_sha256(acl_digest) or any(item.get("windows_acl_digest") != acl_digest for item in group):
            return None
        try:
            capture_windows_permissions(path, acl_digest)
        except (ContractError, OSError):
            return None
    entries = [{"role": item["role"], "entry": item["entry"]} for item in group]
    return {
        "id": _digest([first["path"], entries]),
        "kind": "graft-retire",
        "path": first["path"],
        "target": first["path"],
        "role": first["role"],
        "entry": first["entry"] if len(entries) == 1 else "multiple",
        "entries": entries,
        "format": "agents" if first["role"] == "agents-fence" else "toml" if path.suffix == ".toml" else "json",
        "action": first.get("action"),
        "decision": "remove",
        "classification": "dangling" if any(item["status"] == "dangling" for item in group) else "proven",
        "verification": first.get("verification"),
        "status": "dangling" if any(item["status"] == "dangling" for item in group) else "proven",
        "write_authority": True,
        "global_effect": any(item.get("global_effect") for item in group),
        "guidance": first.get("guidance"),
        "launcher": first.get("launcher"),
        "historical_mode": "unknown",
        "mode": first.get("mode"),
        **({"windows_acl_digest": acl_digest} if os.name == "nt" else {}),
        **({"retiring_launchers": list(launchers)} if launchers else {}),
        "before": first.get("before"),
        "desired": first.get("desired"),
        "recorded_after": first.get("recorded_after"),
        "backup_ref": first.get("backup_ref"),
        "evidence_kind": first.get("evidence_kind"),
        "evidence_paths": list(first.get("evidence_paths") or []),
        "reason": first.get("reason"),
        "body_policy": first.get("body_policy"),
        "at_risk": False,
    }


def render_candidates(report: Mapping[str, Any], *, purpose: str) -> dict[str, Any]:
    """Group an inspection. A drifted reread does not become a new authority."""
    if purpose not in _PURPOSES:
        _fail("invalid-argument", "retirement purpose is not recognized")
    if not isinstance(report, Mapping) or report.get("schema") != REPORT_SCHEMA or not isinstance(report.get("items"), list):
        _fail("invalid-argument", "retirement report is not recognized")
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for item in report["items"]:
        if isinstance(item, Mapping) and isinstance(item.get("path"), str):
            grouped.setdefault(item["path"], []).append(item)
    candidates = []
    preserved = []
    drifted = False
    drifted_items: list[Mapping[str, Any]] = []
    for group in grouped.values():
        if not all(item.get("write_authority") is True for item in group):
            preserved.extend(group)
            continue
        candidate = _candidate(group, report.get("retiring_launchers") or [])
        if candidate is None:
            drifted = True
            preserved.extend(group)
            drifted_items.extend(group)
            continue
        candidates.append(candidate)
    errors = list(report.get("errors") or [])
    blocked = [item for item in report["items"] if isinstance(item, Mapping) and item.get("at_risk")]
    blocked.extend(drifted_items)
    for error in errors:
        if isinstance(error, Mapping):
            blocked.append({
                "path": error.get("path"),
                "target": error.get("path"),
                "status": "blocked",
                "classification": "blocked",
                "verification": "unproven",
                "at_risk": True,
                "write_authority": False,
                "reason": error.get("reason"),
                "guidance": "Do not delete this entry by name.",
                "global_effect": False,
            })
    unsafe = drifted or bool(errors) or report.get("status") == "blocked"
    at_risk = any(isinstance(item, Mapping) and item.get("at_risk") for item in report.get("items", []))
    stop = (purpose in {"reset", "upgrade"} and at_risk) or (purpose in _EXECUTABLE and unsafe)
    if stop and not blocked:
        blocked.append({
            "path": None,
            "status": "blocked",
            "verification": "unproven",
            "at_risk": True,
            "write_authority": False,
            "reason": "A selected path could not be inspected safely.",
            "guidance": "Do not delete this entry by name.",
        })
    if purpose in {"reset", "upgrade"} and at_risk and stop:
        reason = "An unproven entry points at a retiring or missing launcher."
    elif drifted and stop:
        reason = "The inspected file changed before a candidate was sealed."
    elif stop:
        reason = "A selected path could not be inspected safely."
    else:
        reason = None
    return {
        "purpose": purpose,
        "schema": REPORT_SCHEMA,
        "candidates": candidates,
        "preserved": preserved,
        "blocked": blocked,
        "global_effects": sorted({item["path"] for item in report["items"] if isinstance(item, Mapping) and item.get("global_effect")}),
        "stop": stop,
        "stop_reason": reason,
        "manual": list(report.get("manual") or []),
        "proof_gap": report.get("proof_gap"),
        "errors": errors,
    }


def _splice(raw: bytes, candidate: Mapping[str, Any]) -> bytes:
    if candidate.get("role") == "agents-fence" or candidate.get("format") == "agents":
        text = raw.decode("utf-8")
        start = text.index(_FENCE_START)
        end = text.index(_FENCE_END) + len(_FENCE_END)
        if text[end:end + 1] == "\n":
            end += 1
        return (text[:start] + text[end:]).encode()
    _fail("unsupported-operation", "this entry cannot be removed without rewriting unrelated bytes")
    raise AssertionError


def render_candidate_bytes(
    raw: bytes, candidate: Mapping[str, Any], *, vault: Path | None = None,
) -> bytes:
    """Render a selective edit from live bytes and its verified retained original."""
    if not isinstance(raw, (bytes, bytearray)) or not candidate.get("write_authority"):
        _fail("ownership-conflict", "retirement rendering requires write authority")
    if candidate.get("action") == "remove-file":
        _fail("unsupported-operation", "a created file is removed, not rewritten empty")
    if (candidate.get("before") or {}).get("checksum") != _sha(bytes(raw)):
        _fail("state-conflict", "live bytes differ from the captured candidate")
    if vault is None:
        rendered = _splice(bytes(raw), candidate)
    else:
        original = candidate.get("backup_ref")
        recorded = original.get("state") if isinstance(original, dict) else None
        _assert_backup(original, recorded, None, vault, Path(candidate["path"]))
        rendered = _retired_from_candidate(_read_bytes(Path(original["path"])), bytes(raw), candidate)
    if (candidate.get("desired") or {}).get("checksum") != _sha(rendered):
        _fail("unsupported-operation", "removal would not preserve the retained original bytes")
    return rendered


def retirement_file_bytes(*, report: Mapping[str, Any], purpose: str, target: str, before: bytes) -> bytes:
    """Return verified original bytes for an attributable edit.

    ``before`` is the live file, not a caller-supplied backup. The backup path
    is the one already verified in the fresh report. A declared path is reread
    only when it is a canonical regular file whose checksum matches that report.
    """
    if purpose not in _EXECUTABLE:
        _fail("invalid-argument", "retirement rendering is not executable for this purpose")
    if not isinstance(before, (bytes, bytearray)):
        _fail("invalid-argument", "retirement rendering requires live bytes")
    view = render_candidates(report, purpose=purpose)
    candidate = next((item for item in view["candidates"] if item.get("path") == target), None)
    items = [item for item in report.get("items", []) if isinstance(item, Mapping) and item.get("path") == target]
    if candidate is None or not items or any(not item.get("write_authority") for item in items):
        _fail("ownership-conflict", "a target has an entry without write authority")
    if candidate.get("action") == "remove-file":
        _fail("unsupported-operation", "a created file is removed, not rewritten empty")
    if (candidate.get("before") or {}).get("checksum") != _sha(bytes(before)):
        _fail("state-conflict", "live bytes differ from the captured candidate")
    backup = candidate.get("backup_ref")
    if not isinstance(backup, dict):
        _fail("binding-violation", "an edit has no verified retained original")
    path = _as_path(backup.get("path"), "backup")
    if _walk(path) != "file" or _alias(path) or _same_file(path, Path(target)):
        _fail("unsafe-path", "the retained original is not a canonical regular file")
    original = _read_bytes(path)
    if _sha(original) != (backup.get("state") or {}).get("checksum"):
        _fail("binding-violation", "the retained original does not match the fresh report")
    rendered = _retired_from_candidate(original, bytes(before), candidate)
    if (candidate.get("desired") or {}).get("checksum") != _sha(rendered):
        _fail("unsupported-operation", "retirement would not preserve the retained original bytes")
    return rendered


def _expected_file(expected: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    state = _state({"type": expected.get("type"), "checksum": expected.get("checksum")})
    mode = expected.get("mode")
    if (
        state is None or state["type"] != "file"
        or not isinstance(mode, str) or len(mode) != 4 or any(char not in "01234567" for char in mode)
    ):
        _fail("invalid-argument", "expected retirement state must include type, checksum, and mode")
    return state, mode


def _same_file(left: Path, right: Path) -> bool:
    try:
        return os.path.samestat(left.lstat(), right.lstat())
    except OSError:
        return False


def backup_candidate(
    candidate: Mapping[str, Any], *, destination: Path, vault: Path,
) -> dict[str, Any]:
    """Keep original bytes separate from the original's private ACL proof."""
    files = _files()
    target = _as_path(candidate.get("path"), "target")
    state = candidate["before"]
    mode = candidate["mode"]
    if _walk(target) != "file" or _snapshot(target) != state or _mode(target) != mode:
        _fail("state-conflict", "captured bytes or mode changed since planning")
    raw = None
    if os.name == "nt":
        destination = _private_permissions_path(destination, vault)
        raw = capture_windows_permissions(target, candidate.get("windows_acl_digest"))
    backup = files["backup_reference"]({"path": str(target), "state": state}, destination, private_root=vault)
    _assert_backup(backup, state, mode, vault, target)
    if raw is not None:
        files["assert_private_file"](destination)
        retain_windows_permissions(
            destination.with_name(destination.name + ".windows-acl"),
            raw, candidate["windows_acl_digest"], private_root=vault,
        )
    return backup


def _target_scope(target: Path, scope: Path, vault: Path) -> None:
    if (
        target == scope or not target.is_relative_to(scope)
        or _walk(scope) != "other" or not scope.is_dir() or _alias(scope)
        or any(part in {".", ".."} for part in target.parts)
    ):
        _fail("scope-violation", "retirement target is outside its canonical scope")
    if target.is_relative_to(vault) or vault.is_relative_to(target):
        _fail("scope-conflict", "the retirement target overlaps the private vault")


def _candidate_binding(
    candidate: Mapping[str, Any], target: Path, scope: Path, vault: Path,
    expected: Mapping[str, Any], receipt: Path, backup_path: Path | None, plan_id: str,
) -> dict[str, Any]:
    if candidate.get("write_authority") is not True or candidate.get("target") not in {None, candidate.get("path")}:
        _fail("ownership-conflict", "retirement apply requires write authority")
    _target_scope(target, scope, vault)
    state, mode = _expected_file(expected)
    if candidate.get("before") != state or candidate.get("mode") != mode:
        _fail("state-conflict", "expected state does not match the captured candidate")
    acl_digest = expected.get("windows_acl_digest")
    if os.name == "nt":
        _require_windows_digest(acl_digest)
        if candidate.get("windows_acl_digest") != acl_digest:
            _fail("state-conflict", "expected Windows ACL does not match the captured candidate")
    action = candidate.get("action")
    if action not in {"remove-file", "edit"}:
        _fail("unsupported-operation", "retirement candidate action is not recognized")
    desired = _state(candidate.get("desired"))
    if desired is None or desired == state or desired["type"] != ("absent" if action == "remove-file" else "file"):
        _fail("binding-violation", "retirement desired state does not match its action")
    if not _is_sha256(plan_id):
        _fail("binding-violation", "retirement requires a sealed plan identifier")
    if backup_path is None:
        suffix = _digest([plan_id, str(target), state, mode, acl_digest])[:32]
        backup_path = vault / f"retirement-backup-{suffix}"
    backup_path = _as_path(backup_path, "backup")
    if backup_path == vault or not backup_path.is_relative_to(vault):
        _fail("scope-conflict", "retirement backup is outside the private vault")
    return {
        "plan_id": plan_id,
        "candidate_id": candidate["id"],
        "candidate_digest": _digest(dict(candidate)),
        "scope": str(scope),
        "target": str(target),
        "receipt_path": str(receipt),
        "before": state,
        "mode_before": mode,
        "after": desired,
        "mode_after": None if action == "remove-file" else mode,
        "historical_mode": "unknown",
        "mode_scope": "lstat-imode",
        **({
            "windows_acl_digest": acl_digest,
            "windows_acl_digest_after": None if action == "remove-file" else acl_digest,
        } if os.name == "nt" else {}),
        "backup_ref": {"path": str(backup_path), "state": state},
        "action": action,
    }


def _intent_path(receipt: Path) -> Path:
    return receipt.with_name(receipt.name + ".intent")


def _optional_document(path: Path, vault: Path) -> dict[str, Any] | None:
    if path == vault or not path.is_relative_to(vault):
        _fail("scope-conflict", "retirement journal is outside the private vault")
    kind = _walk(path)
    if kind not in {"file", "absent"} or _alias(path):
        _fail("scope-conflict", "retirement journal is not a canonical file inside the vault")
    if kind == "absent":
        return None
    if os.name == "posix":
        _private_parents(path, vault)
        info = path.lstat()
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o022:
            _fail("privacy-unproven", "retirement journal cannot be written by other users")
    document = _evidence_document(path, vault)
    if not isinstance(document, dict):
        _fail("binding-violation", "retirement journal is not a sealed document")
    return document


def _file_identity(path: Path) -> list[int] | None:
    if _walk(path) != "file" or _alias(path):
        return None
    try:
        info = path.lstat()
    except OSError:
        return None
    if not stat.S_ISREG(info.st_mode) or _is_reparse(info) or info.st_nlink != 1 or not info.st_ino:
        return None
    return [info.st_dev, info.st_ino, info.st_mtime_ns, info.st_ctime_ns]


def _record(document: Mapping[str, Any], key: str) -> dict[str, Any]:
    return {"schema_version": 1, "payload": document, key: _digest(document)}


def _completion_body(intent: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": RECEIPT_SCHEMA,
        **intent["transition"],
        "intent_id": _digest(intent),
        "writes": 1,
    }


def _journal(
    receipt: Path, vault: Path, embedded: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, bool]:
    intended = _optional_document(_intent_path(receipt), vault)
    intent = None
    if intended is not None:
        intent = _sealed(intended, "intent_id")
        if (
            set(intent) != {"schema", "transition", "identity_before"}
            or intent["schema"] != _INTENT_SCHEMA
            or not isinstance(intent["transition"], dict)
            or intent["transition"].get("receipt_path") != str(receipt)
            or not isinstance(intent["identity_before"], list)
            or len(intent["identity_before"]) != 4
            or any(type(value) is not int for value in intent["identity_before"])
        ):
            _fail("binding-violation", "retirement intent is not bound to this receipt")
    saved = _optional_document(receipt, vault)
    if saved is not None and embedded is not None and not _same_value(saved, embedded):
        _fail("binding-violation", "saved retirement receipt differs from its recorded completion")
    document = saved if saved is not None else embedded
    if document is None:
        return intent, None, False
    completed = _sealed(document, "receipt_id")
    if (
        completed.get("schema") != RECEIPT_SCHEMA
        or type(completed.get("writes")) is not int or completed["writes"] != 1
        or (intent is not None and not _same_value(completed, _completion_body(intent)))
        or (intent is None and (embedded is not None or "plan_id" in completed or "intent_id" in completed))
    ):
        _fail("binding-violation", "retirement receipt does not bind an executed transition")
    return intent, completed, saved is not None


def _original_matches(target: Path, binding: Mapping[str, Any], identity: list[int] | None) -> bool:
    try:
        if identity is None or _file_identity(target) != identity:
            return False
        if _snapshot(target) != binding["before"] or _mode(target) != binding["mode_before"]:
            return False
        if os.name == "nt":
            capture_windows_permissions(target, binding["windows_acl_digest"])
        return _file_identity(target) == identity
    except (ContractError, OSError):
        return False


def _interrupted(receipt: Path) -> None:
    raise ContractError(
        "retirement-interrupted",
        "retirement intent has no proven completion and the original cannot be verified; preserve the target and backup",
        exit_code=3, details={"writes": None, "retirement_intent": str(_intent_path(receipt))},
    )


def _outcome(
    target: Path, receipt: Path, vault: Path, binding: Mapping[str, Any],
    intent: Mapping[str, Any] | None, completed: Mapping[str, Any] | None, saved: bool,
) -> dict[str, Any] | None:
    if intent is not None and not _same_value(intent["transition"], binding):
        _fail("binding-violation", "retirement intent does not match the sealed plan resource")
    if completed is not None and intent is None:
        _fail("binding-violation", "retirement receipt has no intent bound to the sealed plan")
    if completed is not None:
        if not _matches_after(target, completed):
            _fail("state-conflict", "an existing retirement receipt does not match the live target")
        _verified_backup(completed, vault, target)
        return _apply_row(
            completed, receipt if saved else None, writes=0, result="skipped-complete",
            completion=None if saved else _record(completed, "receipt_id"),
        )
    if intent is None:
        return None
    if not _original_matches(target, binding, intent["identity_before"]):
        _interrupted(receipt)
    _verified_backup(binding, vault, target)
    return {"result": "retryable-before", "writes": 0}


def reconcile_candidate(
    candidate: Mapping[str, Any],
    *,
    scope: Path,
    vault: Path,
    expected: Mapping[str, Any],
    receipt_path: Path,
    backup_path: Path | None,
    plan_id: str,
    retirement_completion: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Observe a confirmed plan's journal without adopting a matching user edit.

    An embedded completion must come from an authenticated cumulative receipt.
    """
    vault = _files()["require_private_directory"](vault)
    target = _as_path(candidate.get("path"), "target")
    receipt = _as_path(receipt_path, "receipt")
    binding = _candidate_binding(candidate, target, _as_path(scope, "scope"), vault, expected, receipt, backup_path, plan_id)
    return _outcome(target, receipt, vault, binding, *_journal(receipt, vault, retirement_completion))



def apply_candidate(
    candidate: Mapping[str, Any],
    *,
    scope: Path,
    vault: Path,
    expected: Mapping[str, Any],
    receipt_path: Path,
    backup_path: Path | None = None,
    plan_id: str,
) -> dict[str, Any]:
    """Retire one resource from a caller-validated plan behind an immutable intent."""
    files = _files()
    scope = _as_path(scope, "scope")
    vault = files["require_private_directory"](vault)
    target = _as_path(candidate.get("path"), "target")
    receipt = _as_path(receipt_path, "receipt")
    binding = _candidate_binding(candidate, target, scope, vault, expected, receipt, backup_path, plan_id)
    intent, completed, saved = _journal(receipt, vault)
    outcome = _outcome(target, receipt, vault, binding, intent, completed, saved)
    if outcome is not None and outcome["result"] == "skipped-complete":
        return outcome

    identity = intent["identity_before"] if intent is not None else _file_identity(target)
    if not _original_matches(target, binding, identity):
        _fail("state-conflict", "captured bytes or mode changed since planning")
    if intent is None and backup_path is None:
        backup_candidate(candidate, destination=Path(binding["backup_ref"]["path"]), vault=vault)
    retained = _verified_backup(binding, vault, target)
    action, state, mode = (binding[key] for key in ("action", "before", "mode_before"))
    rendered = None if action == "remove-file" else render_candidate_bytes(files["read_file"](target, state), candidate, vault=vault)
    if intent is None:
        _private_parents(receipt, vault)
        intent = {"schema": _INTENT_SCHEMA, "transition": binding, "identity_before": identity}
        intent_path = _intent_path(receipt)
        intent_document = _record(intent, "intent_id")
        files["save_document"](intent_path, intent_document, private_root=vault)
        if not _same_value(_evidence_document(intent_path, vault), intent_document):
            _fail("binding-violation", "saved retirement intent differs from the sealed transition")

    native_options: dict[str, Any] = {}
    if os.name == "nt":
        native_options["expected_windows_digest"] = binding["windows_acl_digest"]
        if action == "remove-file":
            native_options["expected_windows_mode"] = int(mode, 8)
        else:
            native_options.update(windows_permissions=retained, windows_mode=int(mode, 8))
    committed = False
    try:
        if not _original_matches(target, binding, identity):
            _interrupted(receipt)
        if action == "remove-file":
            files["remove_reference"](target, state, scope=scope, **native_options)
        else:
            files["write_file"](target, rendered, state, scope=scope, **native_options)
        committed = True
        body = _completion_body(intent)
        if not _matches_after(target, body):
            _fail("state-conflict", "retirement did not preserve its intended bytes and permissions")
    except (ContractError, OSError) as error:
        writes = 1 if committed else 0 if _original_matches(target, binding, identity) else None
        details = {**(getattr(error, "details", None) or {}), "writes": writes, "retirement_intent": str(_intent_path(receipt))}
        if isinstance(error, ContractError):
            error.details = details
            raise
        raise ContractError("operation-failed", "retirement could not prove its outcome", exit_code=3, details=details) from error

    document = _record(body, "receipt_id")
    try:
        files["save_document"](receipt, document, private_root=vault)
    except (ContractError, OSError):
        # The caller can retain the measured completion in its private cumulative receipt.
        # After a lost process, an intent and matching desired bytes alone are NOT enough.
        pass
    try:
        if _same_value(_optional_document(receipt, vault), document):
            return _apply_row(body, receipt, writes=1, result="retired")
    except (ContractError, OSError):
        pass
    return _apply_row(body, None, writes=1, result="retired", completion=document)


def _assert_backup(backup: Any, state: Any, mode: str | None, vault: Path, target: Path) -> None:
    if (
        _state(state) is None or state["type"] != "file"
        or not isinstance(backup, dict) or set(backup) != {"path", "state"}
        or backup["state"] != state
    ):
        _fail("binding-violation", "retained original state does not match the recorded before state")
    path = _as_path(backup.get("path"), "backup")
    _contained(path, vault)
    if _same_file(path, target):
        _fail("unsafe-path", "a retained original is a link to the live target")
    if _snapshot(path) != state:
        _fail("backup-conflict", "retained original bytes differ from the recorded state")
    if mode is not None and _mode(path) != mode:
        _fail("state-conflict", "retained original mode differs from the recorded mode")


def _verified_backup(payload: Mapping[str, Any], vault: Path, target: Path) -> bytes | None:
    backup = payload.get("backup_ref")
    _assert_backup(backup, payload.get("before"), payload.get("mode_before"), vault, target)
    if os.name == "nt":
        return retained_windows_permissions(backup, payload.get("windows_acl_digest"), vault=vault)
    return None


def _matches_after(target: Path, payload: Mapping[str, Any]) -> bool:
    after = _state(payload.get("after"))
    if after is None:
        return False
    acl_digest = payload.get("windows_acl_digest")
    if os.name == "nt" and (
        not _is_sha256(acl_digest)
        or "windows_acl_digest_after" not in payload
        or payload["windows_acl_digest_after"] != (None if after["type"] == "absent" else acl_digest)
        or payload.get("mode_after") != (None if after["type"] == "absent" else payload.get("mode_before"))
    ):
        return False
    if after["type"] == "absent":
        return _walk(target) == "absent" and not _alias(target) and payload.get("mode_after") is None
    identity = _file_identity(target)
    if identity is None or _snapshot(target) != after or _mode(target) != payload.get("mode_after"):
        return False
    if os.name == "nt":
        capture_windows_permissions(target, acl_digest)
    return identity == _file_identity(target)


def _apply_row(
    payload: Mapping[str, Any], receipt: Path | None, *, writes: int, result: str,
    completion: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "result": result,
        "writes": writes,
        "receipt_path": None if receipt is None else str(receipt),
        **({"retirement_completion": completion} if completion is not None else {}),
        "target": payload["target"],
        "before": payload.get("before"),
        "after": payload.get("after"),
        "mode_before": payload.get("mode_before"),
        "mode_after": payload.get("mode_after"),
        **({key: payload[key] for key in ("windows_acl_digest", "windows_acl_digest_after")} if os.name == "nt" else {}),
        "backup_ref": payload.get("backup_ref"),
        "historical_mode": "unknown",
        "mode_scope": "lstat-imode",
    }


def restore_candidate(
    receipt_path: Path,
    *,
    scope: Path,
    vault: Path,
    expected: Mapping[str, Any],
    target: Path,
    plan_id: str | None = None,
    backup_path: Path | None = None,
    retirement_completion: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Restore only after the backup matches the receipt, and only that target."""
    files = _files()
    vault = files["require_private_directory"](vault)
    scope = _as_path(scope, "scope")
    receipt = _as_path(receipt_path, "receipt")
    allowed = _as_path(target, "target")
    _target_scope(allowed, scope, vault)
    if retirement_completion is not None and plan_id is None:
        _fail("binding-violation", "embedded retirement completion requires a sealed plan")
    intent, payload, _saved = _journal(receipt, vault, retirement_completion)
    if payload is None:
        if intent is not None:
            _interrupted(receipt)
        _fail("scope-conflict", "retirement receipt must be a regular file inside the vault")
    backup = payload.get("backup_ref")
    if (
        payload.get("target") != str(allowed)
        or (intent is not None and payload.get("scope") != str(scope))
        or (plan_id is not None and payload.get("plan_id") != plan_id)
        or (backup_path is not None and (not isinstance(backup, dict) or backup.get("path") != str(backup_path)))
    ):
        _fail("binding-violation", "retirement receipt is not bound to the allowed resource")
    if not isinstance(payload.get("mode_before"), str):
        _fail("state-conflict", "retirement recovery has no recorded mode")
    after = payload.get("after")
    if (
        not isinstance(after, dict)
        or set(after) - {"type", "checksum"}
        or expected.get("type") != after.get("type")
        or expected.get("checksum") != after.get("checksum")
        or expected.get("mode") != payload.get("mode_after")
        or (os.name == "nt" and expected.get("windows_acl_digest") != payload.get("windows_acl_digest_after"))
    ):
        _fail("state-conflict", "restore expected state does not match the receipt")
    if not _matches_after(allowed, payload):
        _fail("state-conflict", "the current target differs from the recorded post-retirement state")
    retained = _verified_backup(payload, vault, allowed)
    if os.name == "nt":
        files["write_file"](
            allowed, files["read_file"](Path(payload["backup_ref"]["path"]), payload["before"]), after,
            scope=scope, windows_permissions=retained,
            expected_windows_digest=payload["windows_acl_digest_after"], windows_mode=int(payload["mode_before"], 8),
        )
        capture_windows_permissions(allowed, payload["windows_acl_digest"])
    else:
        files["install_reference"](payload["backup_ref"], allowed, after, scope=scope)
    restored = _snapshot(allowed)
    restored_mode = _mode(allowed)
    if restored != payload["before"] or restored_mode != payload["mode_before"]:
        _fail("state-conflict", "restored bytes or mode differ from the retained original")
    return {
        "result": "restored",
        "target": str(allowed),
        "before": payload.get("before"),
        "after": restored,
        "mode_before": payload["mode_before"],
        "mode_after": restored_mode,
        **({"windows_acl_digest": payload["windows_acl_digest_after"],
            "windows_acl_digest_after": payload["windows_acl_digest"]} if os.name == "nt" else {}),
        "historical_mode": "unknown",
        "mode_scope": "lstat-imode",
    }


def merge_reports(reports: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Collapse identical item ids. Disagreement fails closed."""
    if not reports:
        return _blank()
    merged = _blank("reported")
    seen: dict[str, Mapping[str, Any]] = {}
    manual: dict[bytes, Mapping[str, Any]] = {}
    descriptors = []
    for report in reports:
        if not isinstance(report, Mapping) or report.get("schema") != REPORT_SCHEMA:
            _fail("invalid-argument", "retirement report is not recognized")
        if report.get("status") == "blocked":
            merged["status"] = "blocked"
        for item in report.get("items", []):
            if not isinstance(item, Mapping) or not isinstance(item.get("id"), str):
                _fail("invalid-argument", "retirement report is not recognized")
            prior = seen.get(item["id"])
            if prior is not None and any(not _same_value(prior.get(key), item.get(key)) for key in (
                "status", "write_authority", "path", "entry", "windows_acl_digest",
                "mode", "before", "recorded_after", "desired", "action",
            )):
                _fail("state-conflict", "retirement reports disagree on one entry")
            if prior is not None and (prior.get("backup_ref") or {}).get("state") != (item.get("backup_ref") or {}).get("state"):
                _fail("state-conflict", "retirement reports disagree on the retained original")
            if prior is None:
                seen[item["id"]] = item
            elif item.get("at_risk") and not prior.get("at_risk"):
                seen[item["id"]] = {**prior, "at_risk": True}
        merged["errors"].extend(report.get("errors") or [])
        merged["retiring_launchers"].extend(report.get("retiring_launchers") or [])
        for entry in report.get("manual") or []:
            manual.setdefault(canonical_json_bytes(entry), entry)
        if report.get("evidence_descriptor"):
            descriptors.append(report["evidence_descriptor"])
    merged["items"] = sorted(seen.values(), key=lambda item: (item["path"], item["role"], item["entry"]))
    merged["manual"] = [manual[key] for key in sorted(manual)]
    merged["retiring_launchers"] = sorted(set(merged["retiring_launchers"]))
    merged["evidence_descriptor"] = descriptors[0] if len(descriptors) == 1 else None
    if len(descriptors) > 1:
        merged["evidence_descriptors"] = descriptors
    if not merged["items"] and merged["status"] != "blocked" and all(report.get("status") == "absent" for report in reports):
        merged["status"] = "absent"
    return merged
