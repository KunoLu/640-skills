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
and a lexical path that is not the physical path all fail closed. Place an
rc2 upgrade receipt at the vault path its wrapper ``receipt_path`` names;
that field must be the file actually read, and ``status`` must equal the
payload status. Historical plans are not required to carry ``graftRetirement``.
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
from sbtd_retirement_paths import HISTORY_DIRS

REPORT_SCHEMA = "sbtd-retirement/1"
RECEIPT_SCHEMA = "sbtd-retirement-receipt/1"
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
        except OSError:
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


def _valid_windows_digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _require_windows_digest(value: Any) -> None:
    if not _valid_windows_digest(value):
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
    if _walk(path) != "file" or _alias(path):
        _fail("unsafe-path", "retirement evidence must be a canonical regular file")
    if path == vault or not path.is_relative_to(vault) or _alias(vault):
        _fail("scope-conflict", "retirement evidence must be a regular file inside the vault")


def _private_permissions_path(path: Path, private_root: Path) -> Path:
    files = _files()
    private_root = files["require_private_directory"](private_root)
    path = _as_path(path, "Windows ACL backup")
    if path == private_root or not path.is_relative_to(private_root):
        _fail("scope-conflict", "the Windows ACL backup is outside the private vault")
    if path.parent != private_root:
        files["require_private_directory"](path.parent)
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
    if document.get("schema_version") != 1 or not isinstance(document.get("payload"), dict):
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
        if isinstance(document.get("operationResults"), list):
            found.extend(document["operationResults"])
        wiring = document.get("graftWiring")
        if isinstance(wiring, dict) and isinstance(wiring.get("operationResults"), list):
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
        mechanical_before = _state(row.get("mechanical_before"))
        if mechanical_before == after:
            continue
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
    for path in paths:
        _contained(path, vault)
    return tuple(str(path) for path in paths)


def _proofs_from_binding(item: Mapping[str, Any], selections: Mapping[str, Any], vault: Path) -> list[dict[str, Any]]:
    paths = _binding_paths(item, vault)
    kind = item["kind"]
    if kind == "operation-results":
        return _bind_results(_operation_results(_strict_json(_read_bytes(Path(paths[0])))), selections, kind, paths, vault)
    if kind == "manifest-deployment":
        manifest = _sealed(_strict_json(_read_bytes(Path(paths[0]))), "manifest_id")
        deployment = _sealed(_strict_json(_read_bytes(Path(paths[1]))), "deployment_id")
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
    receipt_document = _strict_json(_read_bytes(receipt_path))
    plan = _sealed(_strict_json(_read_bytes(Path(paths[0]))), "plan_id")
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
        _contained(path, vault)
        payload = _sealed(_strict_json(_read_bytes(path)), "descriptor_id")
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
    args = entry.get("args")
    command = entry.get("command")
    if not _abs(command) or not isinstance(args, list) or any(not isinstance(token, str) for token in args):
        return None
    if dict(entry.get("env") or {}) != _ENV:
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
    key = "mcpServers" if omp or "mcpServers" in document else "mcp_servers"
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


def _table_key(document: Mapping[str, Any], *, omp: bool) -> str:
    return "mcpServers" if omp or "mcpServers" in document else "mcp_servers"


def _foreign_same(before: Mapping[str, Any], after: Mapping[str, Any], table: str) -> bool:
    before_keys = set(before) - {table}
    after_keys = set(after) - {table}
    if before_keys != after_keys:
        return False
    return all(_plain(before.get(key)) == _plain(after.get(key)) for key in before_keys)


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
        plain = _plain(entry) if isinstance(entry, Mapping) else None
        launcher = _mcp_launcher(key, plain, omp=omp) if isinstance(plain, Mapping) else None
        previous = before_servers.get(key)
        if launcher is None:
            if _plain(previous) != plain:
                return None
            continue
        if _plain(previous) == plain:
            continue
        attributable.append((key, launcher))
    for key, entry in before_servers.items():
        if key not in after_servers and _mcp_launcher(key, _plain(entry) if isinstance(entry, Mapping) else {}, omp=omp) is None:
            return None
    if table not in before_document and table in after_document and not attributable:
        return None
    return attributable, False


def _hook_commands(document: Mapping[str, Any]) -> dict[str, list[str]] | None:
    hooks = document.get("hooks", {})
    if not isinstance(hooks, dict):
        return None
    found: dict[str, list[str]] = {}
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            return None
        commands = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                return None
            for hook in group["hooks"]:
                command = hook.get("command") if isinstance(hook, dict) else None
                if isinstance(command, str):
                    commands.append(command)
        found[str(event)] = commands
    return found


def _strict_groups(groups: Any) -> list[str] | None:
    if not isinstance(groups, list):
        return None
    commands = []
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("hooks"), list) or not group["hooks"]:
            return None
        if set(group) - {"matcher", "hooks"}:
            return None
        for hook in group["hooks"]:
            if not isinstance(hook, dict) or not isinstance(hook.get("command"), str):
                return None
            commands.append(hook["command"])
    if len(commands) != len(set(commands)):
        return None
    return commands


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
            if not commands:
                return None
            for command in commands:
                identity = _hook_identity(command)
                if identity is None or identity[0] != event:
                    return None
                owned.append(identity)
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
        if _plain(previous) == _plain(current):
            continue
        previous_commands = _strict_groups(previous) if previous else []
        current_commands = _strict_groups(current) if current else []
        if previous_commands is None or current_commands is None or previous_commands == current_commands:
            return None
        for command in current_commands:
            if command in previous_commands:
                continue
            identity = _hook_identity(command)
            if identity is None or identity[0] != event:
                return None
            attributable.append(identity)
        for command in previous_commands:
            if command not in current_commands and _hook_identity(command) is None:
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
    if recognized and presence == "absent":
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
    if len({item["after"]["checksum"] for item in matched}) != 1:
        return {"conflict": True}
    return matched[-1]


def _watch(raw: bytes, role: str, retiring: Sequence[str]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Split producer-shaped launchers from token hits. A name is not ownership."""
    recognized: list[tuple[str, str]] = []
    pointed: list[tuple[str, str]] = []
    if role == "agents-fence":
        return recognized, pointed
    if role == "codex-hooks":
        commands = _hook_commands(_json_document(raw)) or {}
        for event, values in commands.items():
            for command in values:
                identity = _hook_identity(command)
                if identity and identity[0] == event:
                    recognized.append(identity)
                    continue
                for token in _hook_argv(command) or []:
                    if token in retiring:
                        pointed.append((event, token))
                        break
        return recognized, pointed
    omp = role == "omp-mcp"
    document = _toml_document(raw) if role == "codex-mcp" else _json_document(raw)
    for key, entry in _servers(document, omp=omp).items():
        if not isinstance(key, str) or not key.startswith(_GLOBAL_KEY) or not isinstance(entry, Mapping):
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
        for value in values:
            if isinstance(value, str) and value in retiring:
                pointed.append((key, value))
                break
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


def _fixed_names(raw: bytes, role: str) -> set[str]:
    if role not in {"omp-mcp", "codex-mcp"}:
        return set()
    omp = role == "omp-mcp"
    document = _toml_document(raw) if role == "codex-mcp" else _json_document(raw)
    found = set()
    for key, entry in _servers(document, omp=omp).items():
        if isinstance(key, str) and key.startswith(f"{_GLOBAL_KEY}-") and isinstance(entry, Mapping):
            if _mcp_launcher(key, _plain(entry), omp=omp):
                found.add(key)
    return found


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
    for key in set(before) - {table}:
        if _plain(before.get(key)) != _plain(after.get(key)):
            return None
    return rendered


def _selective_remove(live: bytes, role: str, keys: Sequence[str]) -> bytes | None:
    if role == "omp-mcp":
        return _json_drop(live, "mcpServers", keys)
    if role == "codex-mcp":
        return _toml_drop(live, "mcp_servers", keys)
    if role == "codex-hooks":
        return _json_drop(live, "hooks", keys)
    return None


def _safe_retired(original: bytes, live: bytes, role: str, keys: Sequence[str]) -> bytes | None:
    if role == "agents-fence" or not (_fixed_names(original, role) - _fixed_names(live, role)):
        return original
    rendered = _selective_remove(live, role, keys)
    if rendered is None or _fixed_names(rendered, role) - _fixed_names(live, role):
        return None
    return rendered


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
    rendered = _safe_retired(original, live, role, [key for key in keys if isinstance(key, str)])
    if rendered is None:
        _fail("unsupported-operation", "retirement would resurrect a fixed-root entry")
    return rendered


def _classify_file(
    path: Path,
    role: str,
    raw: bytes,
    proof: Mapping[str, Any] | None,
    retiring: Sequence[str],
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
    if proven and original is not None and not created_only:
        file_safe = _safe_retired(original, raw, role, [entry for entry, _launcher in entries])
        if file_safe is None:
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
    acl_digest = None
    if os.name == "nt" and writable:
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
            status, reason = "not-verified", "the retained original does not match the recorded before state"
        else:
            status, reason = "unproven", "no attributable managed change was proven"
        if this_write and os.name == "nt" and acl_digest is None:
            reason = "the Windows permissions could not be verified"
        action = "remove-file" if this_write and created_only else "edit" if this_write else None
        if action == "edit" and file_safe is None:
            this_write = False
            action = None
            status, reason = "unproven", "retirement would not preserve unrelated bytes"
        desired = {"type": "absent", "checksum": None} if action == "remove-file" else (
            {"type": "file", "checksum": _sha(file_safe)} if action == "edit" and file_safe is not None else None
        )
        items.append(_item(
            role="fixed-root-mcp" if entry.startswith(f"{_GLOBAL_KEY}-") else role,
            path=str(path), entry=entry, status=status, reason=reason, write=this_write,
            mode=mode, windows_acl_digest=acl_digest, action=action, before=live,
            after=None if not proof or proof.get("conflict") else proof["after"],
            desired=desired, launcher=launcher or None,
            evidence=None if not this_write or not proof or proof.get("conflict") else proof,
            recognized=entry in recognized_names,
            body="remove" if action == "remove-file" else "preserve",
            points=bool(launcher) and launcher in retiring,
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
    items: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for config in parsed["configs"]:
        raw = _inspect_path(config["path"], errors)
        if raw is None:
            continue
        items.extend(_classify_file(
            config["path"], config["role"], raw, _proof_for(proofs, str(config["path"])),
            parsed["retiring_launchers"], errors,
        ))
    for root in parsed["projects"]:
        agents = root / "AGENTS.md"
        raw = _inspect_path(agents, errors)
        if raw is None:
            continue
        items.extend(_classify_file(
            agents, "agents-fence", raw, _proof_for(proofs, str(agents)), parsed["retiring_launchers"], errors,
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


def _candidate(group: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    first = group[0]
    path = Path(str(first["path"]))
    if not isinstance(first.get("mode"), str) or _mode(path) != first.get("mode"):
        _fail("state-conflict", "captured mode does not match the live file")
    if _walk(path) != "file" or _snapshot(path) != first.get("before"):
        return None
    acl_digest = first.get("windows_acl_digest")
    if os.name == "nt":
        if not _valid_windows_digest(acl_digest) or any(item.get("windows_acl_digest") != acl_digest for item in group):
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
        if not all(item.get("write_authority") for item in group):
            preserved.extend(group)
            continue
        candidate = _candidate(group)
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


def apply_candidate(
    candidate: Mapping[str, Any],
    *,
    scope: Path,
    vault: Path,
    expected: Mapping[str, Any],
    receipt_path: Path,
    backup_path: Path | None = None,
) -> dict[str, Any]:
    """Backup, then restore the retained original or remove a created file."""
    if candidate.get("write_authority") is not True or candidate.get("target") not in {None, candidate.get("path")}:
        _fail("ownership-conflict", "retirement apply requires write authority")
    files = _files()
    scope = _as_path(scope, "scope")
    vault = files["require_private_directory"](vault)
    target = _as_path(candidate.get("path"), "target")
    receipt = _as_path(receipt_path, "receipt")
    if _walk(scope) != "other" or not target.is_relative_to(scope) or receipt == vault or not receipt.is_relative_to(vault):
        _fail("scope-violation", "retirement target is outside its scope")
    if target.is_relative_to(vault) or vault.is_relative_to(target):
        _fail("scope-conflict", "the retirement target overlaps the private vault")
    receipt_kind = _walk(receipt)
    if receipt_kind not in {"absent", "file"} or _alias(receipt):
        _fail("scope-conflict", "retirement receipt must be a canonical file inside the vault")
    if os.name == "nt":
        files["require_private_directory"](receipt.parent)
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
    if desired is None or desired["type"] != ("absent" if action == "remove-file" else "file"):
        _fail("binding-violation", "retirement desired state does not match its action")
    if receipt_kind == "file":
        previous = _sealed(_strict_json(_read_bytes(receipt)), "receipt_id")
        if (
            previous.get("schema") != RECEIPT_SCHEMA
            or previous.get("candidate_id") != candidate.get("id")
            or previous.get("target") != str(target)
            or previous.get("before") != state
            or previous.get("mode_before") != mode
            or previous.get("after") != desired
            or previous.get("action") != action
            or (os.name == "nt" and previous.get("windows_acl_digest") != acl_digest)
            or not _matches_after(target, previous)
        ):
            _fail("state-conflict", "an existing retirement receipt does not match the live target")
        _assert_backup(previous.get("backup_ref"), previous.get("before"), previous.get("mode_before"), vault, target)
        if os.name == "nt":
            retained_windows_permissions(previous["backup_ref"], acl_digest, vault=vault)
        return _apply_row(candidate, previous, receipt, writes=0, result="skipped-complete")
    if _walk(target) != "file" or _snapshot(target) != state or _mode(target) != mode:
        _fail("state-conflict", "captured bytes or mode changed since planning")
    if backup_path is None:
        backup = backup_candidate(
            candidate, destination=vault / f"retirement-backup-{candidate['id'][:32]}", vault=vault,
        )
    else:
        backup = {"path": str(backup_path), "state": state}
        _assert_backup(backup, state, mode, vault, target)
    native_options: dict[str, Any] = {}
    if os.name == "nt":
        retained = retained_windows_permissions(backup, acl_digest, vault=vault)
        native_options["expected_windows_digest"] = acl_digest
        if action == "remove-file":
            native_options["expected_windows_mode"] = int(mode, 8)
        else:
            native_options.update(windows_permissions=retained, windows_mode=int(mode, 8))
        if _mode(target) != mode:
            _fail("state-conflict", "captured mode changed before retirement")
    if action == "remove-file":
        files["remove_reference"](target, state, scope=scope, **native_options)
        after = {"type": "absent", "checksum": None}
        mode_after = None
    else:
        rendered = render_candidate_bytes(_read_bytes(target), candidate, vault=vault)
        files["write_file"](target, rendered, state, scope=scope, **native_options)
        after = _snapshot(target)
        mode_after = _mode(target)
        if after != desired or mode_after != mode:
            _fail("state-conflict", "retirement did not preserve its intended bytes and captured mode")
        if os.name == "nt":
            capture_windows_permissions(target, acl_digest)
    body = {
        "schema": RECEIPT_SCHEMA,
        "candidate_id": candidate["id"],
        "target": str(target),
        "before": state,
        "mode_before": mode,
        "historical_mode": "unknown",
        "mode_scope": "lstat-imode",
        "after": after,
        "mode_after": mode_after,
        **({
            "windows_acl_digest": acl_digest,
            "windows_acl_digest_after": None if action == "remove-file" else acl_digest,
        } if os.name == "nt" else {}),
        "backup_ref": backup,
        "action": action,
        "writes": 1,
    }
    files["save_document"](
        receipt,
        {"schema_version": 1, "payload": body, "receipt_id": _digest(body)},
        private_root=vault,
    )
    return _apply_row(candidate, body, receipt, writes=1, result="retired")


def _assert_backup(backup: Any, state: Any, mode: str | None, vault: Path, target: Path) -> None:
    if _state(state) is None or not isinstance(backup, dict) or _state(backup.get("state")) != _state(state):
        _fail("binding-violation", "retained original state does not match the recorded before state")
    path = _as_path(backup.get("path"), "backup")
    _contained(path, vault)
    if _same_file(path, target) or _snapshot(path) != backup["state"]:
        _fail("unsafe-path", "a retained original is a link to the live target")
    if mode is not None and _mode(path) != mode:
        _fail("state-conflict", "retained original mode differs from the recorded mode")


def _matches_after(target: Path, payload: Mapping[str, Any]) -> bool:
    after = _state(payload.get("after"))
    if after is None:
        return False
    acl_digest = payload.get("windows_acl_digest")
    if os.name == "nt" and (
        not _valid_windows_digest(acl_digest)
        or "windows_acl_digest_after" not in payload
        or payload["windows_acl_digest_after"] != (None if after["type"] == "absent" else acl_digest)
        or payload.get("mode_after") != (None if after["type"] == "absent" else payload.get("mode_before"))
    ):
        return False
    if after["type"] == "absent":
        return _walk(target) == "absent" and payload.get("mode_after") is None
    if _walk(target) != "file" or _snapshot(target) != after or _mode(target) != payload.get("mode_after"):
        return False
    if os.name == "nt":
        capture_windows_permissions(target, acl_digest)
    return True


def _apply_row(candidate: Mapping[str, Any], payload: Mapping[str, Any], receipt: Path, *, writes: int, result: str) -> dict[str, Any]:
    return {
        "result": result,
        "writes": writes,
        "receipt_path": str(receipt),
        "target": str(candidate.get("path")),
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
) -> dict[str, Any]:
    """Restore only after the backup matches the receipt, and only that target."""
    files = _files()
    vault = files["require_private_directory"](vault)
    scope = _as_path(scope, "scope")
    receipt = _as_path(receipt_path, "receipt")
    allowed = _as_path(target, "target")
    if not receipt.is_relative_to(vault) or _walk(receipt) != "file":
        _fail("scope-conflict", "retirement receipt must be a regular file inside the vault")
    payload = _sealed(_strict_json(_read_bytes(receipt)), "receipt_id")
    if payload.get("schema") != RECEIPT_SCHEMA or payload.get("target") != str(allowed):
        _fail("binding-violation", "retirement receipt target is not the allowed target")
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
    if _walk(scope) != "other" or not allowed.is_relative_to(scope) or not _matches_after(allowed, payload):
        _fail("state-conflict", "the current target differs from the recorded post-retirement state")
    _assert_backup(payload.get("backup_ref"), payload.get("before"), payload["mode_before"], vault, allowed)
    if os.name == "nt":
        retained = retained_windows_permissions(payload["backup_ref"], payload.get("windows_acl_digest"), vault=vault)
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
            if prior is not None and any(prior.get(key) != item.get(key) for key in (
                "status", "write_authority", "path", "entry", "windows_acl_digest",
            )):
                _fail("state-conflict", "retirement reports disagree on one entry")
            seen.setdefault(item["id"], item)
        merged["errors"].extend(report.get("errors") or [])
        if report.get("evidence_descriptor"):
            descriptors.append(report["evidence_descriptor"])
    merged["items"] = sorted(seen.values(), key=lambda item: (item["path"], item["role"], item["entry"]))
    merged["evidence_descriptor"] = descriptors[0] if len(descriptors) == 1 else None
    if len(descriptors) > 1:
        merged["evidence_descriptors"] = descriptors
    if not merged["items"] and merged["status"] != "blocked" and all(report.get("status") == "absent" for report in reports):
        merged["status"] = "absent"
    return merged
