"""Manifest-scoped migration planning, application and evidence consumption."""

from __future__ import annotations

import hashlib
import json
import re
import stat
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

import onboard_contracts as contracts
from graft_runtime import GRAFT_PINNED_VERSION
from onboard import missing_file_lines
from sbtd_identity import DeveloperStore
from sbtd_migration_files import (
    RetainedObjectError,
    backup_reference,
    install_reference,
    read_file,
    remove_reference,
    require_private_directory,
    save_document,
    snapshot,
    write_file,
)
from sbtd_migration_legacy import (
    read_legacy_identity,
)
from sbtd_project import TaskDataError

_PACKAGE = Path(__file__).resolve().parents[1]
_ABSENT = {"type": "absent", "checksum": None}
_RETENTION = {
    "normal_observation_days": 14,
    "normal_disposal_gates": [
        "observation-complete",
        "final-acceptance",
        "stable-release",
        "recovery-window-closed",
    ],
    "termination_disposal_gates": [
        "explicit-termination",
        "recovery-or-no-recovery-confirmed",
        "custodian-review",
    ],
    "disposal_authorization": "separate-manual-confirmation",
}


def _fail(code: str, message: str, exit_code: int = 2) -> NoReturn:
    raise contracts.ContractError(code, message, exit_code=exit_code)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="microseconds")


def runtime_versions() -> dict[str, str]:
    """Bind plans to the installed implementation, not a guessed release tag."""
    import importlib.metadata
    import sys

    names = [
        "onboard-contracts.schema.json",
        "requirements.txt",
        "catalog.json",
        "catalog.schema.json",
        "assets/migration-local-ignore.txt",
        "assets/migration-legacy-ownership.json",
        "assets/migration-paused-agents.txt",
        "assets/routing-approval.pub",
        "assets/graft-build-policy.json",
        "assets/graft-instructions.txt",
        "assets/graft-hook-entry.mjs",
        "scripts/graft_runtime.py",
        "scripts/onboard.py",
        "scripts/onboard_arguments.py",
        "scripts/onboard_contracts.py",
        "scripts/sbtd_graft_deployment.py",
        "scripts/sbtd_codex_wiring.py",
        "scripts/sbtd_omp_wiring.py",
        "scripts/sbtd_omp_sources.py",
        "scripts/sbtd_graft_entry.py",
        "scripts/sbtd_handoff.py",
        "scripts/sbtd_identity.py",
        "scripts/sbtd_migration.py",
        "scripts/sbtd_migration_files.py",
        "scripts/sbtd_migration_legacy.py",
        "scripts/sbtd_migration_plan.py",
        "scripts/sbtd_migration_verify.py",
        "scripts/sbtd_recovery.py",
        "scripts/sbtd_project.py",
        "scripts/sbtd_task_document.py",
        "scripts/sbtd_task_state.py",
        "templates/agents/AGENTS.global.md",
        "templates/agents/AGENTS.project.md",
        "templates/skills/sbtd-task/references/task-data.schema.json",
        "templates/skills/project-validation/scripts/validate_validation_evidence.py",
        "templates/skills/project-validation/references/validation-evidence.schema.json",
        "templates/skills/project-validation/references/validation-evidence.v2.schema.json",
    ]
    from onboard import PROJECT_AGENTS_TEMPLATE

    selected_template = PROJECT_AGENTS_TEMPLATE.relative_to(_PACKAGE).as_posix()
    if selected_template not in names:
        names.append(selected_template)
    hashes: list[list[Any]] = [[name, snapshot(_PACKAGE / name)] for name in names]
    if any(state["type"] != "file" for _, state in hashes):
        _fail("runtime-unavailable", "the installed migration runtime is incomplete")
    try:
        dependencies = {
            name: importlib.metadata.version(name)
            for name in ("jsonschema", "PyYAML", "markdown-it-py", "tomlkit", "cryptography")
        }
    except importlib.metadata.PackageNotFoundError:
        _fail(
            "validator-unavailable",
            "prepare the installed Skill's declared requirements before migration",
        )
    identity = {
        "files": hashes,
        "dependencies": dependencies,
        "python": list(sys.version_info[:3]),
    }
    digest = hashlib.sha256(contracts.canonical_json_bytes(identity)).hexdigest()
    return {"onboard": f"runtime-sha256:{digest}", "graft": GRAFT_PINNED_VERSION}


def _read_reference(reference: Mapping[str, Any]) -> bytes:
    return read_file(Path(reference["path"]), reference["state"])


def _check_reference(reference: Mapping[str, Any], exit_code: int = 2) -> None:
    if snapshot(Path(reference["path"])) != reference["state"]:
        _fail(
            "state-conflict",
            "a bound input no longer matches its recorded state",
            exit_code,
        )


def _private_document(path: Path, kind: str) -> tuple[dict[str, Any], bytes]:
    require_private_directory(path.parent)
    raw = read_file(path)
    return contracts.load_document(raw, kind), raw


def _project_revision(root: Path) -> tuple[str | None, str | None]:
    try:
        identity = DeveloperStore(root, read_only=True)
        topology, _ = identity._topology()
        if topology == "non-git":
            return None, None
        head_result = identity.tasks._git("rev-parse", "--verify", "HEAD")
        head = head_result.stdout.removesuffix("\n")
        if (
            head_result.returncode
            or re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", head) is None
        ):
            _fail(
                "unknown-revision",
                "the selected project's committed revision is unknown",
            )
        branch = identity.tasks._git("symbolic-ref", "--quiet", "--short", "HEAD")
        return (
            branch.stdout.removesuffix("\n") if branch.returncode == 0 else None
        ), head
    except (TaskDataError, OSError, RuntimeError):
        _fail(
            "unknown-revision",
            "the selected project's Git ownership cannot be verified",
        )


def _operations(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    payload = manifest["payload"]
    return [
        operation
        for project in payload["projects"]
        for operation in project["private_operations"]
    ] + list(payload["shared_operations"])


def _groups(manifest: Mapping[str, Any], phase: str) -> list[list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for operation in _operations(manifest):
        if operation["phase"] == phase:
            grouped.setdefault(operation["resource_id"], []).append(operation)
    # Protection precedes local data; a resource is still written only once.
    return sorted(
        grouped.values(),
        key=lambda operations: (
            operations[0]["owner_kind"] != "gitignore",
            operations[0]["target"],
        ),
    )


def _resource_scope(manifest: Mapping[str, Any], operation: Mapping[str, Any]) -> Path:
    payload = manifest["payload"]
    target = Path(operation["target"])
    roots = [Path(project["root"]) for project in payload["projects"]]
    roots.extend(Path(root["path"]) for root in payload["shared_roots"])
    matches = [root for root in roots if target != root and target.is_relative_to(root)]
    if not matches:
        _fail("scope-conflict", "a resource has no declared physical scope")
    return max(matches, key=lambda root: len(root.parts))


def _marker_bounds(text: str, marker: str) -> tuple[int, int]:
    start = f"<!-- {marker}:START -->"
    end = f"<!-- {marker}:END -->"
    if text.count(start) != 1 or text.count(end) != 1:
        _fail("ownership-conflict", "a managed marker is absent or ambiguous")
    left = text.index(start)
    right = text.index(end, left + len(start)) + len(end)
    return left, right


def _remove_markers(raw: bytes, operations: Sequence[Mapping[str, Any]]) -> bytes:
    try:
        text = raw.decode("utf-8")
        spans = []
        for operation in operations:
            ownership = operation["ownership"]
            if ownership["kind"] != "managed-marker":
                _fail(
                    "ownership-conflict", "text removal requires exact marker ownership"
                )
            marker = ownership["marker"]
            left, right = _marker_bounds(text, marker)
            reference = _read_reference(ownership["reference"]).decode("utf-8")
            original_left, original_right = _marker_bounds(reference, marker)
            if text[left:right] != reference[original_left:original_right]:
                _fail("ownership-conflict", "the managed text block has changed")
            spans.append((left, right))
        for left, right in sorted(spans, reverse=True):
            text = text[:left] + text[right:]
        return text.encode("utf-8")
    except (UnicodeError, ValueError):
        _fail(
            "invalid-config",
            "managed text cannot be parsed without changing unrelated content",
        )


def _append_blocks(raw: bytes, operations: Sequence[Mapping[str, Any]]) -> bytes:
    try:
        text = raw.decode("utf-8")
        for operation in operations:
            block = _read_reference(operation["change"]["source_ref"]).decode("utf-8")
            missing = missing_file_lines(block, text)
            if missing:
                prefix = "" if not text or text.endswith("\n") else "\n"
                separator = "\n" if text.strip() else ""
                text += prefix + separator + "\n".join(missing) + "\n"
        return text.encode("utf-8")
    except UnicodeError:
        _fail("invalid-config", "a managed block is not UTF-8 text")


def _render_resource(
    operations: Sequence[Mapping[str, Any]], before: Mapping[str, Any]
) -> tuple[str, Any]:
    first = operations[0]
    change = first["change"]
    kind = change["kind"]
    if kind in {"copy-file", "copy-directory"}:
        _check_reference(change["source_ref"])
        return "reference", change["source_ref"]
    if kind == "migrate-developer":
        if (
            read_legacy_identity(_read_reference(change["source_ref"]))
            != change["name"]
        ):
            _fail(
                "identity-conflict",
                "the legacy name no longer matches the approved operation",
            )
        return "identity", change["name"]
    if kind == "remove" and first["selector"] == "whole-resource":
        return "remove", None
    raw = (
        b"" if before["type"] == "absent" else read_file(Path(first["target"]), before)
    )
    if kind == "ensure-file-block":
        return "bytes", _append_blocks(raw, operations)
    if kind == "remove" and first["owner_kind"] in {"file", "markdown"}:
        return "bytes", _remove_markers(raw, operations)
    _fail(
        "unsupported-operation",
        "this declared resource operation cannot be safely rendered",
    )


def _source_backup_paths(manifest: Mapping[str, Any]) -> dict[str, Path]:
    base = (
        Path(manifest["payload"]["backup_root"]) / manifest["manifest_id"] / "originals"
    )
    return {
        reference["path"]: base
        / hashlib.sha256(reference["path"].encode("utf-8")).hexdigest()
        for project in manifest["payload"]["projects"]
        for reference in project["sources"]
    }


def _result_index(document: Mapping[str, Any] | None) -> dict[str, Mapping[str, Any]]:
    if document is None:
        return {}
    payload = document["payload"]
    results = [
        result
        for project in payload["projects"]
        for result in project["private_results"]
    ] + list(payload["shared_results"])
    return {result["resource_id"]: result for result in results}


def _original_reference(
    reference: Mapping[str, Any],
    manifest: Mapping[str, Any],
    previous: Mapping[str, Any] | None = None,
    deployment: Mapping[str, Any] | None = None,
    cleanup: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    if snapshot(Path(reference["path"])) == reference["state"]:
        return reference
    stages = [
        _result_index(document)
        for document in (previous, deployment, cleanup)
        if document is not None
    ]
    latest: dict[str, Mapping[str, Any]] = {}
    for results in stages:
        latest.update(results)
    targets = {
        operation["resource_id"]: Path(operation["target"])
        for operation in _operations(manifest)
    }
    source = Path(reference["path"])
    for resource_id, target in targets.items():
        if not source.is_relative_to(target):
            continue
        last = latest.get(resource_id)
        if (
            last is None
            or last["status"] != "succeeded"
            or last["after"] != snapshot(target)
        ):
            continue
        for results in stages:
            original = results.get(resource_id)
            if original is None or original["backup_ref"] is None:
                continue
            backup = original["backup_ref"]
            _check_reference(backup, 3)
            restored_source = Path(backup["path"]) / source.relative_to(target)
            if snapshot(restored_source) == reference["state"]:
                return {"path": str(restored_source), "state": reference["state"]}
    _fail("state-conflict", "a source changed without a matching completed operation")


def _all_input_references(manifest: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    references = [
        reference
        for project in manifest["payload"]["projects"]
        for reference in project["sources"]
    ]
    for item in manifest["payload"]["publication_decisions"]["items"]:
        references.extend(item["sources"])
        if item["candidate_ref"] is not None:
            references.append(item["candidate_ref"])
    for operation in _operations(manifest):
        references.append(operation["ownership"]["reference"])
        approval = operation["ownership"].get("approval_ref")
        if approval is not None:
            references.append(approval)
        if "source_ref" in operation["change"]:
            references.append(operation["change"]["source_ref"])
    return references


def _path_inside(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)


def _check_evidence_apply_boundary(
    manifest_path: Path, manifest: Mapping[str, Any]
) -> None:
    """Keep approval, candidates, and project roots out of evidence/apply writers.

    Apply writes receipts beside the manifest and backups under
    ``backup_root/<manifest-id>/apply``. When the manifest directory is inside
    that vault, the vault itself becomes the writer root. A vault that stays
    outside the manifest directory is not authenticated here.
    """
    payload = manifest["payload"]
    evidence = manifest_path.parent
    vault = Path(payload["backup_root"])
    writers = [evidence, vault / manifest["manifest_id"] / "apply"]
    if _path_inside(evidence, vault):
        writers.append(vault)
    subjects = [Path(project["root"]) for project in payload["projects"]]
    approval = payload.get("routing_approvals")
    if isinstance(approval, Mapping) and isinstance(approval.get("path"), str):
        approval_path = Path(approval["path"])
        subjects.append(approval_path)
        state = approval.get("state")
        recorded = state.get("checksum") if isinstance(state, Mapping) else None
        actual = snapshot(approval_path)
        if actual.get("type") != "file" or actual.get("checksum") != recorded:
            _fail(
                "state-conflict",
                "the routing approval record does not match its sealed SHA",
            )
    for operation in _operations(manifest):
        if operation.get("selector") != "approved-routing-replacement":
            continue
        source = operation["change"].get("source_ref")
        if isinstance(source, Mapping) and isinstance(source.get("path"), str):
            subjects.append(Path(source["path"]))
    for subject in subjects:
        for writer in writers:
            if _path_inside(subject, writer):
                _fail(
                    "private-scope",
                    "approval, candidate, or project root overlaps evidence/apply",
                )



def _agents_pause_or_marker_delete(operation: Mapping[str, Any]) -> bool:
    target = operation.get("target")
    if not isinstance(target, str) or Path(target).name != "AGENTS.md":
        return False
    change = operation.get("change")
    kind = change.get("kind") if isinstance(change, Mapping) else None
    selector = operation.get("selector")
    return (
        selector == "pause-legacy-routing" and kind == "ensure-file-block"
    ) or (selector == "trellis-block" and kind == "remove")


def _bind_apply_routing_anchor(
    manifest_path: Path,
    manifest: Mapping[str, Any],
    routing_approvals: Path | None,
    no_routing_approvals: bool,
    *,
    bind_live: bool = True,
) -> None:
    """Bind apply to the caller approval file, not a resealed manifest path.

    A receipt-backed retry must not compare live bytes to the pre-apply
    snapshot. That comparison runs before the successful-result skip and
    rejects an already applied replacement. The receipt's after snapshot
    remains the retry check.
    """
    if routing_approvals is not None and no_routing_approvals:
        _fail(
            "invalid-argument",
            "apply accepts a routing approval file or --no-routing-approvals, not both",
        )
    if routing_approvals is None and not no_routing_approvals:
        _fail(
            "approval-conflict",
            "apply requires the caller routing approval file or --no-routing-approvals",
        )
    payload = manifest["payload"]
    sealed = payload.get("routing_approvals")
    if no_routing_approvals:
        if sealed is not None:
            _fail("state-conflict", "the sealed plan has a routing approval record")
        for operation in _operations(manifest):
            if _agents_pause_or_marker_delete(operation):
                _fail(
                    "approval-conflict",
                    "AGENTS.md pause or marker removal requires the caller routing approval file",
                )
        return
    evidence = manifest_path.parent
    vault = Path(payload["backup_root"])
    writers = [evidence, vault / manifest["manifest_id"] / "apply"]
    if _path_inside(evidence, vault):
        writers.append(vault)
    for writer in writers:
        if _path_inside(routing_approvals, writer):
            _fail(
                "private-scope",
                "the caller routing approval file overlaps evidence/apply",
            )
    if not isinstance(sealed, Mapping):
        _fail("state-conflict", "the sealed plan has no routing approval record")
    state = sealed.get("state")
    recorded = state.get("checksum") if isinstance(state, Mapping) else None
    actual = snapshot(routing_approvals)
    if actual.get("type") != "file" or actual.get("checksum") != recorded:
        _fail(
            "state-conflict",
            "the caller routing approval file does not match the sealed SHA",
        )
    from sbtd_migration_plan import (
        _approved_routing_operations,
        _load_routing_approvals,
        _routing_key,
        _routing_rows,
    )

    roots = [Path(project["root"]) for project in payload["projects"]]
    items = _load_routing_approvals(routing_approvals, vault)
    shared, private = _approved_routing_operations(
        items, roots, vault, routing_approvals, bind_live=bind_live
    )
    declared = _routing_rows(payload)
    expected: list[tuple[str, Path | None, Mapping[str, Any]]] = [
        ("shared", None, operation) for operation in shared
    ]
    for root in roots:
        expected.extend(
            ("private", root, operation) for operation in private.get(root, [])
        )
    if [_routing_key(row) for row in declared] != [
        _routing_key(row) for row in expected
    ]:
        _fail(
            "approval-conflict",
            "an approved routing replacement does not match the caller approval file",
        )

def _validate_context(
    manifest_path: Path,
    manifest: Mapping[str, Any],
    previous: Mapping[str, Any] | None = None,
    deployment: Mapping[str, Any] | None = None,
    cleanup: Mapping[str, Any] | None = None,
) -> None:
    if manifest["payload"]["tool_versions"] != runtime_versions():
        _fail(
            "version-conflict",
            "the migration plan belongs to a different installed implementation",
        )
    _check_evidence_apply_boundary(manifest_path, manifest)
    require_private_directory(Path(manifest["payload"]["backup_root"]))
    resource_inodes: dict[tuple[int, int], str] = {}
    for project in manifest["payload"]["projects"]:
        root = Path(project["root"])
        if not root.is_dir() or root.resolve(strict=True) != root:
            _fail(
                "scope-conflict", "a selected project is not its recorded physical root"
            )
        if manifest_path.is_relative_to(root):
            _fail(
                "private-scope",
                "migration evidence must remain outside selected projects",
            )
        source_ref, head = _project_revision(root)
        if (source_ref, head) != (project["source_ref"], project["head"]):
            _fail("revision-conflict", "a project revision changed after planning")
    for operation in _operations(manifest):
        target = Path(operation["target"])
        state = snapshot(target)
        if state["type"] != "absent":
            metadata = target.lstat()
            identity = metadata.st_dev, metadata.st_ino
            if (
                state["type"] == "file" and metadata.st_nlink > 1
            ) or resource_inodes.setdefault(identity, str(target)) != str(target):
                _fail(
                    "physical-alias",
                    "managed resources have ambiguous physical ownership",
                )
    for reference in _all_input_references(manifest):
        _original_reference(reference, manifest, previous, deployment, cleanup)
    from sbtd_migration_plan import validate_legacy_inputs

    validate_legacy_inputs(
        manifest,
        lambda reference: _read_reference(
            _original_reference(reference, manifest, previous, deployment, cleanup)
        ),
    )


def _prepare_backup_parent(destination: Path, vault: Path) -> None:
    if destination == vault or not destination.is_relative_to(vault):
        _fail("private-scope", "an original backup must remain below its private vault")
    current = vault
    for part in destination.parent.relative_to(vault).parts:
        current = current / part
        require_private_directory(current, create=True)


def _backup_sources(manifest: Mapping[str, Any]) -> None:
    locations = _source_backup_paths(manifest)
    for project in manifest["payload"]["projects"]:
        for reference in project["sources"]:
            destination = locations[reference["path"]]
            _prepare_backup_parent(
                destination, Path(manifest["payload"]["backup_root"])
            )
            backup_reference(
                reference,
                destination,
                private_root=Path(manifest["payload"]["backup_root"]),
            )


def _check_source_backups(manifest: Mapping[str, Any]) -> None:
    locations = _source_backup_paths(manifest)
    for project in manifest["payload"]["projects"]:
        for reference in project["sources"]:
            if snapshot(locations[reference["path"]]) != reference["state"]:
                _fail(
                    "original-unavailable",
                    "a retained original is incomplete or unavailable",
                    3,
                )


def _check_stage_backups(stage_results: Mapping[str, Any]) -> None:
    for results in stage_results.values():
        for result in results.values():
            backup = result["backup_ref"]
            if backup is not None and snapshot(Path(backup["path"])) != backup["state"]:
                _fail(
                    "original-unavailable",
                    "a retained original is incomplete or unavailable",
                    3,
                )


def _summary_projects(artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "root": project["root"],
            "status": project["status"],
            "reason": project["reason"],
            "nextStep": project["nextStep"],
        }
        for project in artifact["payload"]["projects"]
    ]


def _apply_projects(
    manifest: Mapping[str, Any],
    results: Mapping[str, Mapping[str, Any]],
    previous: Mapping[str, Any] | None,
    global_error: str | None,
    originals_ready: bool,
) -> list[dict[str, Any]]:
    previous_projects = (
        {project["root"]: project for project in previous["payload"]["projects"]}
        if previous is not None
        else {}
    )
    shared = manifest["payload"]["shared_operations"]
    projects = []
    original_locations = _source_backup_paths(manifest) if not originals_ready else {}
    for project in manifest["payload"]["projects"]:
        private = [
            operation
            for operation in project["private_operations"]
            if operation["phase"] == "apply"
        ]
        dependencies = private + [
            operation
            for operation in shared
            if operation["phase"] == "apply"
            and project["root"] in operation["dependent_projects"]
        ]
        resource_ids = {operation["resource_id"] for operation in dependencies}
        statuses = {results[rid]["status"] for rid in resource_ids if rid in results}
        complete = resource_ids <= results.keys() and statuses <= {"succeeded"}
        source_ready = originals_ready
        if not source_ready:
            try:
                require_private_directory(Path(manifest["payload"]["backup_root"]))
                source_ready = all(
                    snapshot(original_locations[reference["path"]])
                    == reference["state"]
                    for reference in project["sources"]
                )
            except (contracts.ContractError, OSError, RuntimeError):
                source_ready = False
        if "failed" in statuses or not source_ready:
            status = "failed"
        elif not complete or "blocked" in statuses:
            status = "blocked"
        else:
            old = previous_projects.get(project["root"])
            status = (
                "already-complete"
                if old and old["status"] in {"applied", "already-complete"}
                else "applied"
            )
        private_ids = {operation["resource_id"] for operation in private}
        projects.append(
            {
                "root": project["root"],
                "source_ref": project["source_ref"],
                "head": project["head"],
                "status": status,
                "reason": (
                    global_error or "not every declared resource and original completed"
                )
                if status in {"failed", "blocked"}
                else "",
                "nextStep": "Inspect the retained private receipt and resolve the failure before retrying."
                if status in {"failed", "blocked"}
                else "",
                "private_results": [
                    dict(results[rid]) for rid in sorted(private_ids) if rid in results
                ],
                # Receipts may reference only shared operations whose results
                # were actually observed; declared-but-unattempted operations
                # stay declared so a completed project still requires them.
                "shared_operation_ids": sorted(
                    operation["operation_id"]
                    for operation in shared
                    if operation["phase"] == "apply"
                    and operation["resource_id"] in results
                    and project["root"] in operation["dependent_projects"]
                ),
            }
        )
    return projects


def _prepare_target_parents(target: Path, scope: Path) -> None:
    if target == scope or not target.is_relative_to(scope):
        _fail("scope-conflict", "target parents escape the declared write scope")
    current = scope
    for part in target.parent.relative_to(scope).parts:
        current = current / part
        try:
            information = current.lstat()
        except FileNotFoundError:
            current.mkdir(mode=0o700)
            information = current.lstat()
        if (
            not stat.S_ISDIR(information.st_mode)
            or stat.S_ISLNK(information.st_mode)
            or getattr(information, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            _fail("scope-conflict", "a target parent is not a safe directory")


def _apply_resource(
    manifest: Mapping[str, Any],
    operations: Sequence[Mapping[str, Any]],
    previous: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], int]:
    first = operations[0]
    target = Path(first["target"])
    before = snapshot(target)
    expected = first["before_requirement"]["state"]
    if before != expected:
        _fail("state-conflict", "a resource changed before its operation")
    scope = _resource_scope(manifest, first)
    result = {
        "phase": "apply",
        "resource_id": first["resource_id"],
        "operation_ids": sorted(operation["operation_id"] for operation in operations),
        "dependent_projects": sorted(
            {
                root
                for operation in operations
                for root in operation["dependent_projects"]
            }
        ),
        "status": "failed",
        "backup_ref": previous["backup_ref"] if previous is not None else None,
        "before": before,
        "after": before,
        "error": None,
    }
    exit_code = 0
    try:
        if before["type"] != "absent" and result["backup_ref"] is None:
            backup_path = (
                Path(manifest["payload"]["backup_root"])
                / manifest["manifest_id"]
                / "apply"
                / first["resource_id"]
            )
            _prepare_backup_parent(
                backup_path, Path(manifest["payload"]["backup_root"])
            )
            result["backup_ref"] = backup_reference(
                {"path": str(target), "state": before},
                backup_path,
                private_root=Path(manifest["payload"]["backup_root"]),
            )
        action, value = _render_resource(operations, before)
        if action != "remove":
            _prepare_target_parents(target, scope)
        if action == "reference":
            install_reference(
                value, target, before, scope=scope, backup_ref=result["backup_ref"]
            )
        elif action == "bytes":
            write_file(target, value, before, scope=scope)
        elif action == "remove":
            remove_reference(target, before, scope=scope)
        elif action == "identity":
            identity = DeveloperStore(scope).ensure(
                value, confirmed=True, protect=False
            )
            if identity.status != "created":
                _fail(
                    "identity-conflict",
                    "the identity operation did not create its authorized missing target",
                )
        result["after"] = snapshot(target)
        if action == "reference":
            wanted_after = value["state"]
        elif action in {"bytes", "identity"}:
            content = value if action == "bytes" else f"name={value}\n".encode()
            wanted_after = {
                "type": "file",
                "checksum": hashlib.sha256(content).hexdigest(),
            }
        else:
            wanted_after = _ABSENT
        if result["after"] != wanted_after:
            _fail(
                "post-state-conflict",
                "the resource's current outcome is not its authorized post-state",
            )
        result["status"] = "succeeded"
    except (contracts.ContractError, TaskDataError, OSError, RuntimeError) as error:
        exit_code = (
            3
            if isinstance(error, contracts.ContractError) and error.exit_code == 3
            else 5
        )
        try:
            result["after"] = snapshot(target)
        except (contracts.ContractError, TaskDataError, OSError, RuntimeError):
            result["after"] = None
        result["error"] = (
            error.code
            if isinstance(error, contracts.ContractError)
            else "operation-io-failed"
        )
        if isinstance(error, RetainedObjectError):
            result["error"] += "; retained=" + contracts.canonical_json_bytes(
                error.retained_refs
            ).decode("utf-8")
    return result, exit_code

def _retry_block(old: Mapping[str, Any] | None, target: Path) -> str | None:
    """Return skip, an error code, or None when this attempt may write."""
    if old is None:
        return None
    if old["after"] is None or snapshot(target) != old["after"]:
        return "retry-conflict"
    if old["status"] == "succeeded":
        return "skip"
    if (old["error"] or "").startswith(
        ("foreign-content-conflict", "post-state-conflict")
    ):
        return "unsafe-retry"
    if old["before"] is None or old["before"] != old["after"]:
        return "unsafe-retry"
    return None



def apply_migration(
    manifest_path: Path,
    *,
    previous_receipt_path: Path | None = None,
    confirmed: bool = False,
    routing_approvals: Path | None = None,
    no_routing_approvals: bool = False,
) -> tuple[dict[str, Any], int]:
    if not confirmed:
        _fail(
            "confirmation-required",
            "migration apply requires this plan's explicit confirmation",
        )
    manifest, manifest_raw = _private_document(manifest_path, "manifest")
    previous = None
    if previous_receipt_path is not None:
        previous, previous_raw = _private_document(
            previous_receipt_path, "apply_receipt"
        )
        contracts.validate_declared_bindings(
            manifest,
            {"apply_receipt": previous},
            {"manifest": manifest_raw, "apply_receipt": previous_raw},
        )
        if contracts._parse_timestamp(
            previous["payload"]["finished_at"]
        ) > contracts._parse_timestamp(_now()):
            _fail(
                "future-evidence",
                "a previous receipt is later than the current operation",
            )
    _validate_context(manifest_path, manifest, previous)
    _bind_apply_routing_anchor(
        manifest_path,
        manifest,
        routing_approvals,
        no_routing_approvals,
        bind_live=previous is None,
    )

    groups = _groups(manifest, "apply")
    results = dict(_result_index(previous))
    for group in groups:
        first = group[0]
        old = results.get(first["resource_id"])
        if old is not None:
            if old["backup_ref"] is not None:
                _check_reference(old["backup_ref"], 3)
            decision = _retry_block(old, Path(first["target"]))
            if decision == "retry-conflict":
                _fail(
                    "retry-conflict",
                    "a previously recorded resource no longer matches its outcome",
                )
            if decision == "unsafe-retry":
                _fail(
                    "unsafe-retry",
                    "a partial or unknown write requires explicit recovery or manual reconciliation",
                )
            if decision == "skip":
                continue
        if snapshot(Path(first["target"])) != first["before_requirement"]["state"]:
            _fail(
                "state-conflict",
                "an unfinished resource no longer matches its initial state",
            )
        _render_resource(group, first["before_requirement"]["state"])
    started = _now()
    global_error = None
    originals_ready = False
    failure_exit = 5
    try:
        require_private_directory(Path(manifest["payload"]["backup_root"]))
        if previous is None or (
            previous["payload"]["status"] in {"failed", "blocked"} and not results
        ):
            _backup_sources(manifest)
        else:
            _check_source_backups(manifest)
        originals_ready = True
        for group in groups:
            rid = group[0]["resource_id"]
            old = results.get(rid)
            if old is not None and old["status"] == "succeeded":
                continue
            results[rid], failure_exit = _apply_resource(manifest, group, old)
            if results[rid]["status"] != "succeeded":
                global_error = "a resource failed; later resources were not attempted"
                break
    except (contracts.ContractError, TaskDataError, OSError, RuntimeError) as error:
        failure_exit = (
            3
            if isinstance(error, contracts.ContractError) and error.exit_code == 3
            else 5
        )
        global_error = "private original preparation or resource execution failed"
    projects = _apply_projects(
        manifest, results, previous, global_error, originals_ready
    )
    statuses = [project["status"] for project in projects]
    status = contracts._aggregate(
        statuses, ("failed", "blocked"), "applied", "already-complete"
    )
    shared_ids = {
        operation["resource_id"]
        for operation in manifest["payload"]["shared_operations"]
        if operation["phase"] == "apply"
    }
    payload = {
        "manifest_id": manifest["manifest_id"],
        "previous_receipt_id": previous["apply_id"] if previous is not None else None,
        "status": status,
        "projects": projects,
        "shared_results": [
            dict(results[rid]) for rid in sorted(shared_ids) if rid in results
        ],
        "started_at": started,
        "finished_at": _now(),
    }
    receipt = contracts.seal_document("apply_receipt", payload)
    contracts.validate_cumulative(previous, receipt, "apply_receipt")
    contracts.validate_declared_bindings(manifest, {"apply_receipt": receipt})
    destination = manifest_path.parent / f"apply-{receipt['apply_id']}.json"
    try:
        save_document(destination, receipt, private_root=manifest_path.parent)
    except (contracts.ContractError, TaskDataError, OSError, RuntimeError):
        summaries = []
        for project in projects:
            diagnostics = [
                result["error"]
                for result in results.values()
                if project["root"] in result["dependent_projects"] and result["error"]
            ]
            summaries.append(
                {
                    "root": project["root"],
                    "status": "failed",
                    "reason": "cumulative receipt could not be saved; "
                    + "; ".join(diagnostics),
                    "nextStep": "Preserve originals and all reported retained objects; do not deploy or claim automatic recovery.",
                }
            )
        return contracts.make_envelope(
            "migration",
            "apply",
            "failed",
            summaries,
            "cumulative evidence persistence failed",
            "Inspect the declared private backup root and reconcile before proceeding.",
            identifiers={"manifest_id": manifest["manifest_id"]},
        ), 5
    envelope = contracts.make_envelope(
        "migration",
        "apply",
        status,
        _summary_projects(receipt),
        global_error or "",
        f"Cumulative receipt saved privately at {destination}.",
        receipt,
        {"manifest_id": manifest["manifest_id"]},
    )
    return (
        envelope,
        failure_exit if status == "failed" else 2 if status == "blocked" else 0,
    )


def _cleanup_candidates(
    verification: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    candidates = {
        candidate["resource_id"]: candidate
        for candidate in verification["payload"]["shared_cleanup_candidates"]
    }
    for project in verification["payload"]["projects"]:
        candidates.update(
            (candidate["resource_id"], candidate)
            for candidate in project["cleanup_candidates"]
        )
    return candidates


def _latest_backup_ref(
    resource_id: str, *documents: Mapping[str, Any] | None
) -> Mapping[str, Any] | None:
    for document in documents:
        result = _result_index(document).get(resource_id)
        if result is not None and result["backup_ref"] is not None:
            return result["backup_ref"]
    return None


def _cleanup_resource(
    manifest: Mapping[str, Any],
    operations: Sequence[Mapping[str, Any]],
    candidate: Mapping[str, Any],
    backup_ref: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], int]:
    first = operations[0]
    target = Path(first["target"])
    before = snapshot(target)
    result = {
        "phase": "cleanup",
        "resource_id": first["resource_id"],
        "operation_ids": sorted(operation["operation_id"] for operation in operations),
        "dependent_projects": sorted(
            {
                root
                for operation in operations
                for root in operation["dependent_projects"]
            }
        ),
        "status": "failed",
        "backup_ref": backup_ref,
        "before": before,
        "after": before,
        "error": None,
    }
    exit_code = 0
    try:
        if before != candidate["state"]:
            _fail("state-conflict", "a cleanup candidate changed after verification")
        scope = _resource_scope(manifest, first)
        wanted_after = _ABSENT
        if before["type"] != "absent":
            if backup_ref is None:
                if any(
                    operation["resource_id"] == first["resource_id"]
                    and operation["phase"] != "cleanup"
                    for operation in _operations(manifest)
                ):
                    _fail(
                        "original-unavailable",
                        "a cleanup target lacks its retained original backup",
                        3,
                    )
                # A cleanup-only resource has not been changed by an earlier
                # phase. Preserve its verified original before its first write.
                vault = Path(manifest["payload"]["backup_root"])
                backup_path = (
                    vault / manifest["manifest_id"] / "cleanup" / first["resource_id"]
                )
                _prepare_backup_parent(backup_path, vault)
                backup_ref = backup_reference(
                    {"path": str(target), "state": before},
                    backup_path,
                    private_root=vault,
                )
                result["backup_ref"] = backup_ref
            _check_reference(backup_ref, 3)
            action, value = _render_resource(operations, before)
            if action == "reference" or action == "identity":
                _fail(
                    "unsupported-operation",
                    "this declared cleanup operation cannot be safely rendered",
                )
            if action != "remove":
                _prepare_target_parents(target, scope)
            if action == "remove":
                remove_reference(target, before, scope=scope)
            else:
                if not isinstance(value, bytes):
                    _fail("unsupported-operation", "cleanup did not render file bytes")
                wanted_after = {
                    "type": "file",
                    "checksum": hashlib.sha256(value).hexdigest(),
                }
                write_file(target, value, before, scope=scope)
        result["after"] = snapshot(target)
        if result["after"] != wanted_after:
            _fail(
                "post-state-conflict",
                "the resource's current outcome is not its authorized post-state",
            )
        result["status"] = "succeeded"
    except (contracts.ContractError, TaskDataError, OSError, RuntimeError) as error:
        exit_code = (
            3
            if isinstance(error, contracts.ContractError) and error.exit_code == 3
            else 5
        )
        try:
            result["after"] = snapshot(target)
        except (contracts.ContractError, TaskDataError, OSError, RuntimeError):
            result["after"] = None
        result["error"] = (
            error.code
            if isinstance(error, contracts.ContractError)
            else "operation-io-failed"
        )
        if isinstance(error, RetainedObjectError):
            result["error"] += "; retained=" + contracts.canonical_json_bytes(
                error.retained_refs
            ).decode("utf-8")
    return result, exit_code


def _cleanup_projects(
    manifest: Mapping[str, Any],
    verification: Mapping[str, Any],
    results: Mapping[str, Mapping[str, Any]],
    previous: Mapping[str, Any] | None,
    global_error: str | None,
) -> list[dict[str, Any]]:
    previous_projects = (
        {project["root"]: project for project in previous["payload"]["projects"]}
        if previous is not None
        else {}
    )
    verification_projects = {
        project["root"]: project for project in verification["payload"]["projects"]
    }
    shared = manifest["payload"]["shared_operations"]
    projects = []
    for project in manifest["payload"]["projects"]:
        root = project["root"]
        private = [
            operation
            for operation in project["private_operations"]
            if operation["phase"] == "cleanup"
        ]
        dependencies = private + [
            operation
            for operation in shared
            if operation["phase"] == "cleanup"
            and root in operation["dependent_projects"]
        ]
        resource_ids = {operation["resource_id"] for operation in dependencies}
        statuses = {results[rid]["status"] for rid in resource_ids if rid in results}
        complete = resource_ids <= results.keys() and statuses <= {"succeeded"}
        if "failed" in statuses:
            status = "failed"
        elif not complete or "blocked" in statuses:
            status = "blocked"
        else:
            old = previous_projects.get(root)
            status = (
                "already-complete"
                if old and old["status"] in {"cleaned", "already-complete"}
                else "cleaned"
            )
        private_ids = {operation["resource_id"] for operation in private}
        projects.append(
            {
                "root": root,
                "source_ref": project["source_ref"],
                "head": project["head"],
                "status": status,
                "reason": (
                    "a declared cleanup resource failed"
                    if status == "failed"
                    else global_error or "not every declared cleanup resource completed"
                )
                if status in {"failed", "blocked"}
                else "",
                "nextStep": "Inspect the retained private receipt and resolve the failure before retrying."
                if status in {"failed", "blocked"}
                else "",
                "private_results": [
                    dict(results[rid]) for rid in sorted(private_ids) if rid in results
                ],
                "shared_operation_ids": sorted(
                    operation["operation_id"]
                    for operation in shared
                    if operation["phase"] == "cleanup"
                    and operation["resource_id"] in results
                    and root in operation["dependent_projects"]
                ),
                "retained_assets": [
                    dict(asset)
                    for asset in verification_projects[root]["retained_assets"]
                ],
            }
        )
    return projects


def cleanup_migration(
    manifest_path: Path,
    apply_receipt_path: Path,
    deployment_evidence_path: Path,
    verification_path: Path,
    *,
    previous_receipt_path: Path | None = None,
    confirm_cleanup: str | None = None,
) -> tuple[dict[str, Any], int]:
    manifest_path = Path(manifest_path)
    manifest, manifest_raw = _private_document(manifest_path, "manifest")
    apply_document, apply_raw = _private_document(
        Path(apply_receipt_path), "apply_receipt"
    )
    deployment, deployment_raw = _private_document(
        Path(deployment_evidence_path), "deployment_evidence"
    )
    verification, verification_raw = _private_document(
        Path(verification_path), "verification"
    )
    previous = None
    previous_raw = None
    if previous_receipt_path is not None:
        previous, previous_raw = _private_document(
            Path(previous_receipt_path), "cleanup_receipt"
        )
        if contracts._parse_timestamp(
            previous["payload"]["finished_at"]
        ) > contracts._parse_timestamp(_now()):
            _fail(
                "future-evidence",
                "a previous receipt is later than the current operation",
            )
    documents = {
        "apply_receipt": apply_document,
        "deployment_evidence": deployment,
        "verification": verification,
    }
    raw_documents = {
        "manifest": manifest_raw,
        "apply_receipt": apply_raw,
        "deployment_evidence": deployment_raw,
        "verification": verification_raw,
    }
    if previous is not None:
        assert previous_raw is not None
        documents["cleanup_receipt"] = previous
        raw_documents["cleanup_receipt"] = previous_raw
    contracts.validate_declared_bindings(manifest, documents, raw_documents)
    if confirm_cleanup != verification["verification_id"]:
        _fail(
            "confirmation-required",
            "migration cleanup requires this verification's explicit confirmation",
        )
    _validate_context(
        manifest_path,
        manifest,
        previous=apply_document,
        deployment=deployment,
        cleanup=previous,
    )
    _check_source_backups(manifest)
    source_backups = _source_backup_paths(manifest)
    stage_results = {
        "apply": _result_index(apply_document),
        "deploy": _result_index(deployment),
    }
    _check_stage_backups(stage_results)
    if previous is not None:
        _check_stage_backups({"cleanup": _result_index(previous)})
    candidates = _cleanup_candidates(verification)
    requirements = {
        (operation["phase"], operation["resource_id"]): operation["before_requirement"]
        for operation in _operations(manifest)
    }
    for project in verification["payload"]["projects"]:
        for asset in project["retained_assets"]:
            if snapshot(Path(asset["path"])) != asset["state"]:
                _fail(
                    "state-conflict",
                    "a retained asset changed after verification",
                )
    groups = _groups(manifest, "cleanup")
    results = dict(_result_index(previous))
    for group in groups:
        first = group[0]
        rid = first["resource_id"]
        candidate = candidates.get(rid)
        if candidate is None:
            _fail("missing-input", "a declared cleanup candidate is unavailable")
        old = results.get(rid)
        current = snapshot(Path(first["target"]))
        if old is not None and old["status"] == "succeeded":
            if old["after"] is None or current != old["after"]:
                _fail(
                    "retry-conflict",
                    "a previously cleaned resource no longer matches its outcome",
                )
            continue
        expected = contracts._expected_before(
            requirements[("cleanup", rid)], stage_results
        )
        if expected is not None and current != expected:
            _fail("state-conflict", "a cleanup target changed after its prior stage")
        if current != candidate["state"]:
            _fail("state-conflict", "a cleanup candidate changed after verification")
        if old is not None:
            if (old["error"] or "").startswith(
                ("foreign-content-conflict", "post-state-conflict")
            ):
                _fail(
                    "unsafe-retry",
                    "unapproved changed objects require explicit manual reconciliation",
                )
            if old["before"] is None or old["before"] != old["after"]:
                _fail(
                    "unsafe-retry",
                    "a partial or unknown cleanup requires explicit recovery or manual reconciliation",
                )
    started = _now()
    global_error = None
    failure_exit = 5
    try:
        for group in groups:
            first = group[0]
            rid = first["resource_id"]
            old = results.get(rid)
            if old is not None and old["status"] == "succeeded":
                continue
            backup_ref = _latest_backup_ref(rid, previous, deployment, apply_document)
            if backup_ref is None:
                backup_path = source_backups.get(str(Path(first["target"])))
                if backup_path is not None:
                    backup_ref = {
                        "path": str(backup_path),
                        "state": snapshot(backup_path),
                    }
            results[rid], failure_exit = _cleanup_resource(
                manifest, group, candidates[rid], backup_ref
            )
            if results[rid]["status"] != "succeeded":
                global_error = (
                    "a cleanup resource failed; later resources were not attempted"
                )
                break
    except (contracts.ContractError, TaskDataError, OSError, RuntimeError) as error:
        failure_exit = (
            3
            if isinstance(error, contracts.ContractError) and error.exit_code == 3
            else 5
        )
        global_error = "cleanup resource execution failed"
    projects = _cleanup_projects(
        manifest, verification, results, previous, global_error
    )
    statuses = [project["status"] for project in projects]
    status = contracts._aggregate(
        statuses, ("failed", "blocked"), "cleaned", "already-complete"
    )
    retained: dict[str, Mapping[str, Any]] = {}
    for project in verification["payload"]["projects"]:
        for asset in project["retained_assets"]:
            retained[asset["path"]] = asset
    shared_ids = {
        operation["resource_id"]
        for operation in manifest["payload"]["shared_operations"]
        if operation["phase"] == "cleanup"
    }
    payload = {
        "manifest_id": manifest["manifest_id"],
        "verification_id": verification["verification_id"],
        "apply_id": apply_document["apply_id"],
        "deployment_evidence_hash": hashlib.sha256(bytes(deployment_raw)).hexdigest(),
        "previous_receipt_id": previous["cleanup_id"] if previous is not None else None,
        "status": status,
        "projects": projects,
        "shared_results": [
            dict(results[rid]) for rid in sorted(shared_ids) if rid in results
        ],
        "retained_assets": [dict(retained[path]) for path in sorted(retained)],
        "started_at": started,
        "finished_at": _now(),
    }
    receipt = contracts.seal_document("cleanup_receipt", payload)
    contracts.validate_cumulative(previous, receipt, "cleanup_receipt")
    contracts.validate_declared_bindings(
        manifest,
        {**documents, "cleanup_receipt": receipt},
    )
    destination = manifest_path.parent / f"cleanup-{receipt['cleanup_id']}.json"
    try:
        save_document(destination, receipt, private_root=manifest_path.parent)
    except (contracts.ContractError, TaskDataError, OSError, RuntimeError):
        summaries = []
        for project in projects:
            diagnostics = [
                result["error"]
                for result in results.values()
                if project["root"] in result["dependent_projects"] and result["error"]
            ]
            summaries.append(
                {
                    "root": project["root"],
                    "status": "failed",
                    "reason": "cumulative receipt could not be saved; "
                    + "; ".join(diagnostics),
                    "nextStep": "Preserve originals and all reported retained objects; do not claim automatic recovery.",
                }
            )
        return contracts.make_envelope(
            "migration",
            "cleanup",
            "failed",
            summaries,
            "cumulative evidence persistence failed",
            "Inspect the declared private evidence directory and reconcile before proceeding.",
            identifiers={
                "manifest_id": manifest["manifest_id"],
                "verification_id": verification["verification_id"],
            },
        ), 5
    envelope = contracts.make_envelope(
        "migration",
        "cleanup",
        status,
        _summary_projects(receipt),
        global_error or "",
        f"Cumulative receipt saved privately at {destination}.",
        receipt,
        {
            "manifest_id": manifest["manifest_id"],
            "verification_id": verification["verification_id"],
        },
    )
    return (
        envelope,
        failure_exit if status == "failed" else 2 if status == "blocked" else 0,
    )


def _argument_path(value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute() or not candidate.name:
        _fail("invalid-path", "migration file and directory arguments must be absolute")
    try:
        return candidate.parent.resolve(strict=True) / candidate.name
    except (OSError, RuntimeError):
        _fail("invalid-path", "a migration argument's parent cannot be resolved")


def run_migration(args: Any) -> int:
    """The live CLI projects private envelopes, never private error data as logs."""
    envelope: dict[str, Any]
    rejection: str | None = None
    try:
        if args.phase == "plan":
            from sbtd_migration_plan import plan_migration

            roots = []
            for value in args.projects_root.split(","):
                if not value.strip():
                    _fail(
                        "invalid-path",
                        "the selected project list contains an empty path",
                    )
                root = _argument_path(value.strip())
                if root not in roots:
                    roots.append(root)
            manifest = plan_migration(
                roots,
                _argument_path(args.backup_root),
                args.custodian,
                _argument_path(args.publication_decisions)
                if args.publication_decisions
                else None,
                tool_versions=runtime_versions(),
                deployment_mode=getattr(args, "deployment_mode", None),
                deployment_platform=getattr(args, "deployment_platform", None)
                or "codex",
                hooks_authorized=bool(getattr(args, "graft_hooks", False)),
                routing_approvals=(
                    _argument_path(args.routing_approvals)
                    if getattr(args, "routing_approvals", None)
                    else None
                ),
                routing_approval_key=(
                    _argument_path(args.routing_approval_key)
                    if getattr(args, "routing_approval_key", None)
                    else None
                ),
            )
            projects = [
                {
                    "root": project["root"],
                    "status": "planned",
                    "reason": "",
                    "nextStep": "Confirm this exact private plan before applying it.",
                }
                for project in manifest["payload"]["projects"]
            ]
            envelope = contracts.make_envelope(
                "migration",
                "plan",
                "planned",
                projects,
                "",
                "Save only the manifest object in an authorized private directory; plan made no writes.",
                manifest,
                {"manifest_id": manifest["manifest_id"]},
            )
            code = 0
        elif args.phase == "apply":
            envelope, code = apply_migration(
                _argument_path(args.manifest),
                previous_receipt_path=_argument_path(args.apply_receipt)
                if args.apply_receipt
                else None,
                confirmed=args.yes,
                routing_approvals=_argument_path(args.routing_approvals)
                if getattr(args, "routing_approvals", None)
                else None,
                no_routing_approvals=bool(
                    getattr(args, "no_routing_approvals", False)
                ),
            )
        elif args.phase == "verify":
            from sbtd_migration_verify import verify_migration

            envelope, code = verify_migration(
                _argument_path(args.manifest),
                _argument_path(args.apply_receipt),
                _argument_path(args.deployment_evidence),
            )
        elif args.phase == "cleanup":
            envelope, code = cleanup_migration(
                _argument_path(args.manifest),
                _argument_path(args.apply_receipt),
                _argument_path(args.deployment_evidence),
                _argument_path(args.verification),
                previous_receipt_path=_argument_path(args.cleanup_receipt)
                if args.cleanup_receipt
                else None,
                confirm_cleanup=args.confirm_cleanup,
            )
        else:
            _fail(
                "unsupported-phase",
                "this migration phase is not implemented by this entry point",
            )
    except contracts.ContractError as error:
        code = error.exit_code
        rejection = str(error)
        confirmation = error.details
    except ImportError:
        code = 2
        rejection = "the installed migration runtime or its declared dependencies are unavailable"
        confirmation = None
    except (TaskDataError, OSError, RuntimeError, ValueError):
        code = 5
        rejection = "migration could not safely finish its filesystem operation"
        confirmation = None
    if rejection is not None:
        # A fixed rejection carries no accepted input/artifact. It must remain
        # printable when the validator itself is unavailable, without weakening
        # any operation's input validation or allowing a successful fallback.
        envelope = {
            "mode": "migration",
            "phase": args.phase,
            "status": "failed" if code in {3, 5} else "blocked",
            "manifest_id": None,
            "verification_id": None,
            "projects": [],
            "reason": rejection,
            "nextStep": "Preserve originals and private evidence; resolve the failure before retrying.",
            "migration": {},
        }
        if confirmation:
            envelope["confirmation"] = confirmation
    if args.json:
        if rejection is None:
            contracts.write_json_response(envelope)
        else:
            print(json.dumps(envelope, ensure_ascii=False, allow_nan=False))
    else:
        print(f"Migration {args.phase}: {envelope['status']}")
        for number, project in enumerate(envelope["projects"], 1):
            print(f"Project {number}: {project['status']}")
        print(
            "Detailed references are private; use --json only with authorized private storage."
        )
    return code
