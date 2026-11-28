"""Shared host deployment resources without Graft generation.

The public installer owns confirmation and dispatch. This module owns Codex
or OMP installation-template deployment, approved project AGENTS preservation,
and the authenticated migration-init context. Sealed Graft operations are
refused before any write.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

import onboard_contracts as contracts
from sbtd_migration import _LEGACY_TREE, _prepare_target_parents
from sbtd_migration_files import (
    _canonical,
    _lstat,
    backup_reference,
    install_reference,
    read_file,
    require_private_directory,
    save_document,
    snapshot,
    write_file,
)

_PACKAGE = Path(__file__).resolve().parents[1]
_ABSENT = {"type": "absent", "checksum": None}
_LEGACY_KINDS = frozenset({"build-graft", "configure-graft"})
_LEGACY_SELECTORS = frozenset(
    {"graft-agents", "graft-mcp", "graft-hooks", "graft-omp-mcp"}
)
_UNSUPPORTED = (
    "unsupported-in-rc.3",
    "a sealed plan still contains Graft operations; regenerate the plan",
)
APPROVED_AGENTS = "approved-agents"


def _fail(code: str, message: str, exit_code: int = 2) -> NoReturn:
    raise contracts.ContractError(code, message, exit_code=exit_code)


def graft_operation(operation: Mapping[str, Any]) -> bool:
    """True for a sealed Graft kind or selector. Does not read or write."""
    change = operation.get("change")
    kind = change.get("kind") if isinstance(change, Mapping) else None
    return kind in _LEGACY_KINDS or operation.get("selector") in _LEGACY_SELECTORS


def legacy_graft_operations(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    found: list[Mapping[str, Any]] = []
    for project in payload.get("projects", ()):
        for operation in project.get("private_operations", ()):
            if graft_operation(operation):
                found.append(operation)
    for operation in payload.get("shared_operations", ()):
        if graft_operation(operation):
            found.append(operation)
    return found


def validate_archived_graft_declarations(payload: Mapping[str, Any]) -> None:
    """Read-only structural check. Does not write and does not grant execution.

    The private deploy set is exactly ``root/graft`` ``build-graft``
    ``whole-resource``, plus ``root/AGENTS.md`` ``configure-graft``
    ``graft-agents`` unless ``agents_no_touch``. Every Graft operation
    ``source_ref`` must equal ``contracts.archived_graft_policy()`` by
    identity. Does not read ``assets/graft-build-policy.json``.
    """
    policy = contracts.archived_graft_policy()
    operations = legacy_graft_operations(payload)
    if not operations:
        _fail(
            "semantic-violation",
            "archived Graft validation requires the sealed Graft deploy set",
        )
    for operation in operations:
        if operation.get("phase") != "deploy":
            _fail(
                "semantic-violation",
                "Graft generation is restricted to deployment",
            )
        if operation.get("change", {}).get("source_ref") != policy:
            _fail(
                "ownership-conflict",
                "a generated deployment policy was altered",
            )
    for project in payload.get("projects", ()):
        expected = {
            (str(Path(project["root"]) / "graft"), "build-graft", "whole-resource"),
        }
        if project.get("agents_no_touch") is None:
            expected.add(
                (
                    str(Path(project["root"]) / "AGENTS.md"),
                    "configure-graft",
                    "graft-agents",
                )
            )
        actual = {
            (
                operation.get("target"),
                (operation.get("change") or {}).get("kind"),
                operation.get("selector"),
            )
            for operation in project.get("private_operations", ())
            if operation.get("phase") == "deploy"
        }
        if actual != expected:
            _fail(
                "semantic-violation",
                "the complete private deployment set is missing or altered",
            )


def reject_legacy_execution(payload: Mapping[str, Any]) -> None:
    """Refuse Graft deployment before any write. Does not grant write authority."""
    if legacy_graft_operations(payload):
        _fail(*_UNSUPPORTED)


def approved_agents_selector(body: bytes) -> str:
    """Selector seals the pause-stripped body digest. Not a vault path."""
    return APPROVED_AGENTS + ":" + hashlib.sha256(body).hexdigest()


def _is_approved_agents(operation: Mapping[str, Any]) -> bool:
    selector = operation.get("selector")
    return isinstance(selector, str) and selector.startswith(APPROVED_AGENTS + ":")


def _declare_approved_agents(
    payload: Mapping[str, Any],
    private: dict[str, list[dict[str, Any]]],
    *,
    check_live: bool,
) -> None:
    """Seal the signed candidate and the projected body digest. No write."""
    if payload.get("followup") is not None:
        return
    from sbtd_migration_plan import (
        _routing_rows,
        approved_agents_provenance,
        project_approved_body,
    )

    origin, bodies = approved_agents_provenance({"payload": payload})
    if not bodies:
        return
    projects = {project["root"]: project for project in payload["projects"]}
    for _place, root, operation in _routing_rows(origin["payload"]):
        if operation["ownership"].get("role") != "demo-project":
            continue
        target = operation["target"]
        body = bodies.get(target)
        if body is None:
            continue
        project = projects.get(str(root))
        if project is None:
            _fail(
                "scope-conflict",
                "an approved project AGENTS root is outside the batch",
            )
        if project.get("agents_no_touch") is not None:
            _fail(
                "scope-conflict",
                "an untouched AGENTS file cannot take an approved deployment",
            )
        candidate = operation["change"]["source_ref"]
        if project_approved_body(candidate) != body:
            _fail(
                "candidate-conflict",
                "the approved projection does not match its signed candidate",
            )
        selector = approved_agents_selector(body)
        resource = contracts.resource_id("markdown", target)
        apply_here = [
            item
            for item in project["private_operations"]
            if item["phase"] == "apply"
            and item["target"] == target
            and item["selector"] == "approved-routing-replacement"
        ]
        if apply_here:
            if len(apply_here) != 1:
                _fail(
                    "semantic-violation",
                    "approved project AGENTS has conflicting apply operations",
                )
            requirement = {
                "kind": "phase-after",
                "phase": "apply",
                "resource_id": resource,
            }
        else:
            requirement = {"kind": "state", "state": dict(candidate["state"])}
            if check_live and snapshot(Path(target)) != candidate["state"]:
                _fail(
                    "state-conflict",
                    "approved project AGENTS is not the paused candidate",
                )
        private[str(root)].append(
            {
                "phase": "deploy",
                "resource_id": resource,
                "operation_id": contracts.operation_id("deploy", resource, selector),
                "owner_kind": "markdown",
                "target": target,
                "selector": selector,
                "change": {"kind": "ensure-file-block", "source_ref": dict(candidate)},
                "ownership": {
                    "kind": "approved-candidate",
                    "reference": dict(candidate),
                    "approval_ref": copy.deepcopy(
                        operation["ownership"]["approval_ref"]
                    ),
                    "role": "demo-project",
                },
                "before_requirement": requirement,
                "dependent_projects": [str(root)],
            }
        )


def execute_resource(
    operation: Mapping[str, Any],
    *,
    expected: Mapping[str, Any],
    root: Path,
    private_root: Path,
    backup_path: Path,
) -> dict[str, Any]:
    """One observed resource result; caller persists cumulative stage evidence."""
    if graft_operation(operation):
        _fail(*_UNSUPPORTED)
    result: dict[str, Any] = {
        "phase": "deploy",
        "resource_id": operation["resource_id"],
        "operation_ids": [operation["operation_id"]],
        "dependent_projects": list(operation["dependent_projects"]),
        "status": "blocked",
        "backup_ref": None,
        "before": None,
        "after": None,
        "error": "resource execution has not begun",
    }
    target = Path(operation["target"])
    started = False
    try:
        before = snapshot(target)
        result.update(before=before, after=before)
        if before != expected:
            _fail("state-conflict", "the deployment resource changed before execution")
        kind = operation["change"]["kind"]
        root_info = _lstat(_canonical(root))
        if root_info is None:
            root.mkdir(parents=True, mode=0o700)
        elif not stat.S_ISDIR(root_info.st_mode):
            _fail("unsafe-path", "the deployment write scope is not a real directory")
        if private_root.is_relative_to(root):
            _prepare_target_parents(private_root, root)
            require_private_directory(private_root, create=True)
        if before["type"] != "absent":
            require_private_directory(private_root)
            _prepare_target_parents(backup_path, private_root)
            result["backup_ref"] = backup_reference(
                {"path": str(target), "state": before},
                backup_path,
                private_root=private_root,
            )
        if snapshot(target) != before:
            _fail(
                "state-conflict",
                "the deployment resource changed while retaining its original",
            )
        started = True
        if _is_approved_agents(operation):
            from sbtd_migration_plan import project_approved_body

            source = operation["change"]["source_ref"]
            body = project_approved_body(source)
            if operation["selector"] != approved_agents_selector(body):
                _fail(
                    "candidate-conflict",
                    "the sealed projection digest does not match the signed candidate",
                )
            live = b"" if before["type"] == "absent" else read_file(target, before)
            if live != body:
                _prepare_target_parents(target, root)
                write_file(target, body, before, scope=root)
        elif kind in {"copy-file", "copy-directory"}:
            _prepare_target_parents(target, root)
            install_reference(
                operation["change"]["source_ref"],
                target,
                before,
                scope=root,
                backup_ref=result.get("backup_ref"),
            )
        else:
            _fail("unsupported-operation", "the deployment operation is not supported")
        result.update(status="succeeded", after=snapshot(target), error=None)
    except (contracts.ContractError, OSError, RuntimeError):
        result["status"] = "failed" if started else "blocked"
        result["error"] = (
            "deployment resource execution failed"
            if started
            else "deployment resource precondition failed"
        )
        try:
            result["after"] = snapshot(target)
        except (contracts.ContractError, OSError, RuntimeError):
            result["after"] = None
    return result





def _omp_agents_template_target(platform: str) -> Path | None:
    """An explicit OMP migration includes global rules even for a new root."""
    if platform != "omp":
        return None
    from onboard import omp_agents_target

    target, _explicit = omp_agents_target()
    return target.resolve()


def _installation_templates(
    roots: Sequence[str], *, omp_agents_target: Path | None = None
) -> list[Any]:
    """Reuse the installer's canonical source/target selection, not a second catalog."""
    from argparse import Namespace

    from onboard import build_operations

    arguments = Namespace(
        projects_root=",".join(roots),
        skip_project_agents=False,
        global_agents_path=None,
        global_skills_dir=None,
    )
    project_targets = {
        str(Path(root) / name) for root in roots for name in ("AGENTS.md", ".gitignore")
    }
    selected = [
        operation
        for operation in build_operations("init", arguments)
        if str(operation.target) not in project_targets and not operation.same_location
    ]
    if omp_agents_target is not None and all(
        operation.target != omp_agents_target for operation in selected
    ):
        from onboard import GLOBAL_AGENTS_TEMPLATE, Operation

        selected.append(
            Operation(
                "omp global AGENTS.md", GLOBAL_AGENTS_TEMPLATE, omp_agents_target, "file"
            )
        )
    return selected


def _empty_no_touch_successor(payload: Mapping[str, Any]) -> bool:
    declaration = payload.get("deployment")
    return (
        declaration is not None
        and payload.get("successor") is not None
        and declaration["mode"] == "init-projects"
        and all(
            project.get("agents_no_touch") is not None
            for project in payload["projects"]
        )
        and not any(
            operation["phase"] == "deploy"
            for project in payload["projects"]
            for operation in project["private_operations"]
        )
        and not any(
            operation["phase"] == "deploy"
            for operation in payload["shared_operations"]
        )
    )


def attach_deployment(
    payload: dict[str, Any],
    *,
    project_only: bool,
    hooks_authorized: bool,
    platform: str = "codex",
    successor_pauses: Mapping[str, str] | None = None,
    followup_deployed: Mapping[str, Any] | None = None,
) -> None:
    """Declare every write before the migration manifest is sealed."""
    from onboard import (
        default_codex_home,
        detect_omp_root,
        resolve_global_skills_dir,
        user_home,
    )
    from onboard import omp_agents_target as resolve_omp_agents_target
    from sbtd_migration_plan import _ignore_operation

    if platform not in {"codex", "omp"}:
        _fail(
            "invalid-argument", "the deployment platform must be explicitly supported"
        )
    if hooks_authorized:
        _fail(*_UNSUPPORTED)
    roots = sorted(project["root"] for project in payload["projects"])
    if project_only and payload["shared_operations"]:
        _fail(
            "scope-conflict",
            "project-only deployment cannot consume a shared-HOME batch",
        )
    codex_home = None if project_only else default_codex_home()
    discovery = None
    if platform == "omp" and not project_only:
        from sbtd_omp_sources import discover_omp_sources

        discovery = discover_omp_sources(
            [Path(root) for root in roots], home=user_home(), environ=os.environ
        )
    omp_agents_target = None if project_only else _omp_agents_template_target(platform)
    reject_legacy_execution(payload)
    private: dict[str, list[dict[str, Any]]] = {
        project["root"]: [] for project in payload["projects"]
    }
    shared: list[dict[str, Any]] = []
    _declare_approved_agents(payload, private, check_live=True)
    payload["deployment"] = {
        "mode": "init-projects" if project_only else "init",
        "platform": platform,
        "inputs": list(discovery["inputs"]) if discovery is not None else [],
    }
    for project in payload["projects"]:
        if not any(
            operation["owner_kind"] == "gitignore"
            for operation in project["private_operations"]
        ):
            protection = _ignore_operation(Path(project["root"]))
            if protection is not None:
                project["private_operations"].insert(0, protection)
        project["private_operations"].extend(private[project["root"]])
    if codex_home is not None:
        if not any(
            record["path"] == str(codex_home) for record in payload["shared_roots"]
        ):
            payload["shared_roots"].append(
                {
                    "kind": "codex-home",
                    "path": str(codex_home),
                    "dependent_projects": roots,
                }
            )
        omp_root = detect_omp_root()
        omp_target, omp_explicit = resolve_omp_agents_target()
        if omp_explicit:
            effective_omp_root = omp_target.parent.parent
        elif omp_root is not None:
            effective_omp_root = omp_root
        elif omp_agents_target is not None:
            effective_omp_root = omp_agents_target.parent.parent
        else:
            effective_omp_root = None
        if effective_omp_root is not None and not any(
            record["path"] == str(effective_omp_root)
            for record in payload["shared_roots"]
        ):
            payload["shared_roots"].append(
                {
                    "kind": "omp-home",
                    "path": str(effective_omp_root),
                    "dependent_projects": roots,
                }
            )
        obsolete_skills_roots = [
            record
            for record in payload["shared_roots"]
            if record["kind"] == "skills"
            and any(
                Path(record["path"]).is_relative_to(Path(scope["path"]))
                and scope["dependent_projects"] == record["dependent_projects"]
                for scope in payload["shared_roots"]
                if scope["kind"] in {"codex-home", "omp-home"}
            )
        ]
        if any(
            record["dependent_projects"] != roots for record in obsolete_skills_roots
        ):
            _fail(
                "scope-conflict",
                "an existing skills root has different project dependencies",
            )
        if obsolete_skills_roots:
            for record in obsolete_skills_roots:
                strict_covering = [
                    scope
                    for scope in payload["shared_roots"]
                    if scope["kind"] in {"codex-home", "omp-home"}
                    and scope["dependent_projects"] == record["dependent_projects"]
                    and scope["path"] != record["path"]
                    and Path(record["path"]).is_relative_to(Path(scope["path"]))
                ]
                if len(strict_covering) == 1:
                    # The absorbed Skills root survives as sealed logical
                    # metadata on its covering home root; an already-sealed
                    # location keeps authority over a re-resolution.
                    strict_covering[0].setdefault("skills_root", record["path"])
            payload["shared_roots"] = [
                record
                for record in payload["shared_roots"]
                if record not in obsolete_skills_roots
            ]
        skills_root, _source = resolve_global_skills_dir()
        covering_skills = [
            record
            for record in payload["shared_roots"]
            if Path(skills_root).is_relative_to(Path(record["path"]))
            and record["dependent_projects"] == roots
        ]
        if not covering_skills:
            payload["shared_roots"].append(
                {
                    "kind": "skills",
                    "path": str(skills_root),
                    "dependent_projects": roots,
                }
            )
        earlier_by_target = {
            operation["target"]: operation
            for operation in payload["shared_operations"]
            if operation["phase"] == "apply"
            and operation["selector"] == "pause-legacy-routing"
        }
        for selected in _installation_templates(
            roots, omp_agents_target=omp_agents_target
        ):
            target = selected.target
            source = {"path": str(selected.source), "state": snapshot(selected.source)}
            before = snapshot(target)
            earlier = earlier_by_target.get(str(target))
            paused_predecessor = (
                None if successor_pauses is None else successor_pauses.get(str(target))
            )
            directory = selected.kind == "dir"
            owner_kind = "directory" if directory else "markdown"
            selector = "whole-resource" if directory else "global-rules"
            resource = contracts.resource_id(owner_kind, str(target))
            followup_after = (
                None if followup_deployed is None else followup_deployed.get(resource)
            )
            if earlier is None and paused_predecessor is None:
                if followup_after is not None:
                    # A followup batch replaces only what its proven
                    # predecessor deployment owns, from that exact outcome.
                    if before != followup_after:
                        _fail(
                            "state-conflict",
                            "a completed batch outcome no longer matches the "
                            "current state",
                        )
                elif before not in (_ABSENT, source["state"]):
                    _fail(
                        "ownership-conflict",
                        "an installation target has unrecognized customized content",
                    )
            if earlier is not None:
                requirement = {
                    "kind": "phase-after",
                    "phase": "apply",
                    "resource_id": resource,
                }
            elif paused_predecessor is not None:
                if paused_predecessor != resource:
                    _fail(
                        "ownership-conflict",
                        "a paused predecessor does not own the installation target",
                    )
                requirement = {
                    "kind": "phase-after",
                    "phase": "apply",
                    "resource_id": resource,
                }
            else:
                requirement = {"kind": "state", "state": before}
            shared.append(
                {
                    "phase": "deploy",
                    "resource_id": resource,
                    "operation_id": contracts.operation_id(
                        "deploy", resource, selector
                    ),
                    "owner_kind": owner_kind,
                    "target": str(target),
                    "selector": selector,
                    "change": {
                        "kind": "copy-directory" if directory else "copy-file",
                        "source_ref": source,
                    },
                    "ownership": {"kind": "template-source", "reference": source},
                    "before_requirement": requirement,
                    "dependent_projects": roots,
                }
            )
    payload["shared_operations"].extend(shared)
    payload["shared_roots"].sort(key=lambda record: record["path"])
    for project in payload["projects"]:
        project["shared_operation_ids"] = sorted(
            operation["operation_id"]
            for operation in payload["shared_operations"]
            if project["root"] in operation["dependent_projects"]
        )
    has_deploy = any(
        operation["phase"] == "deploy"
        for project in payload["projects"]
        for operation in project["private_operations"]
    ) or any(
        operation["phase"] == "deploy" for operation in payload["shared_operations"]
    )
    if not has_deploy and not _empty_no_touch_successor(payload):
        payload["deployment"] = None


def _declared_operations(
    payload: Mapping[str, Any],
) -> dict[tuple[str, str], Mapping[str, Any]]:
    return {
        (operation["phase"], operation["resource_id"]): operation
        for operation in (
            *(
                operation
                for project in payload["projects"]
                for operation in project["private_operations"]
            ),
            *payload["shared_operations"],
        )
    }


def _proven_input_outcome(
    operations: Mapping[tuple[str, str], Mapping[str, Any]],
    stage_results: Mapping[str, Mapping[str, Any]] | None,
    path: str,
    sealed_state: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    """Chain one sealed input through its bound successful stage outcomes.

    Returns the receipt-proven outcome once at least one bound stage result
    claims the input path, or None when no bound stage touches it. A claimed
    input with a broken chain (duplicate, failed, partial or untracked
    outcome, mutated retained original) keeps the exact drift rejection.
    """
    proven = sealed_state
    bound = False
    for phase in ("apply", "deploy", "cleanup"):
        matched = []
        for resource_id, result in ((stage_results or {}).get(phase) or {}).items():
            operation = operations.get((phase, resource_id))
            if operation is not None and operation["target"] == path:
                matched.append(result)
        if not matched:
            continue
        bound = True
        result = matched[0]
        backup = result["backup_ref"]
        if (
            len(matched) != 1
            or result["status"] != "succeeded"
            or result["before"] != proven
            or result["after"] is None
            or (
                proven["type"] != "absent"
                and (
                    backup is None
                    or snapshot(Path(backup["path"])) != backup["state"]
                )
            )
        ):
            _fail(
                "state-conflict",
                "the sealed OMP configuration sources have drifted",
            )
        proven = result["after"]
    return proven if bound else None


def _require_proven_input_changes(
    payload: Mapping[str, Any],
    sealed: Sequence[Mapping[str, Any]],
    discovered: Sequence[Mapping[str, Any]],
    stage_results: Mapping[str, Mapping[str, Any]] | None,
) -> None:
    """Recognize only input changes proven by bound successful stage results.

    Between planning and deployment a bound stage may legitimately change a
    sealed configuration input; an approved apply removal is the known case.
    Every differing input must chain from its sealed state through succeeded
    receipt outcomes to the live state, with the retained original still
    intact. The input path set itself is closed: new or vanished paths,
    unbound or partial outcomes and mutated originals keep the drift
    rejection.
    """
    sealed_states = {entry["path"]: entry["state"] for entry in sealed}
    live_states = {entry["path"]: entry["state"] for entry in discovered}
    if not stage_results or sealed_states.keys() != live_states.keys():
        _fail("state-conflict", "the sealed OMP configuration sources have drifted")
    operations = _declared_operations(payload)
    for path, sealed_state in sealed_states.items():
        if sealed_state == live_states[path]:
            continue
        if _proven_input_outcome(operations, stage_results, path, sealed_state) != (
            live_states[path]
        ):
            _fail(
                "state-conflict",
                "the sealed OMP configuration sources have drifted",
            )


def _cleanup_safe_input_drift(
    payload: Mapping[str, Any],
    sealed: Sequence[Mapping[str, Any]],
    discovered: Sequence[Mapping[str, Any]],
    stage_results: Mapping[str, Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Recognize only drift provably irrelevant to the cleanup phase.

    Cleanup never redeploys, so a sealed deployment-discovery input whose
    bytes changed since planning need not block legacy retirement — but only
    when the input is deterministically proven to take no part in this
    cleanup. This is never a lexical-disjointness waiver; an input is
    ignored only after every cleanup dependency is shown independent of it:

    - Tool and host choice: cleanup executes only the characterized
      retirement kinds below. A project legacy tree is retired exclusively
      by ``sbtd_trellis_uninstall``: its planner/executor never imports or
      consults OMP runtime configuration, binds an absolute
      ``@mindfoldhq/trellis`` CLI of a supported version plus the verified
      Node executable on a scrubbed child environment, never runs a command
      taken from the plan, and confines every vendor effect to the selected
      project root through the validated relative-path adapter
      (``_join_root`` rejects anything escaping the root) and the sealed
      footprint gate. Global skill retirement writes exactly its validated
      operation target via ``remove_reference`` after preserving the
      verified original. No OMP input byte selects or steers either path.
    - Scope and ownership: every declared operation target (including every
      retained asset), the exact selected project roots, the private backup
      vault and every ownership/source reference are sealed in the payload
      and re-validated by the caller; a drifted input must not
      overlap any of them in either direction, so it cannot be a cleanup
      target, a retained asset, a backup or recovery input, or an
      ownership anchor. The input path set stays closed: new or vanished
      paths change the discovery scope and keep the rejection.
    - Vendor footprint: for each pending characterized ``.trellis``
      retirement the *actual current* vendor footprint is derived with the
      same read-only ``prepare_trellis_uninstall`` planner the executor
      uses, and every resource path it carries is protected exactly — a
      drifted input the vendor would delete, scrub or prune out from under
      is influencing and keeps the rejection, while unrelated project-level
      settings outside the real footprint stay accepted. A retirement
      already proven cleaned by a bound succeeded result whose target is
      still absent runs no vendor plan, so it contributes no footprint; an
      unavailable vendor produces no effects and is reported blocked by the
      executor instead. Project roots themselves stay protected only by
      exact identity: the vendor footprint, not coarse root descent,
      decides which project-local paths participate.
    - Plan, backup and recovery: the cleanup plan derives from the sealed
      operations and the bound verification candidates, backups and stage
      receipts — never from deployment-discovery inputs; receipt-proven
      input changes keep their historical chained acceptance here.
    - Live binding checks stay live: discovery is re-derived from the current
      environment, and the canonical installation targets must still match
      the sealed writes. Only byte equality of irrelevant inputs is waived.

    Acceptance is limited to inputs whose sealed and live states are both
    ordinary files or genuine absence; a forged non-file sealed state or
    any unknown type keeps the exact historical drift rejection, and live
    links, specials and directories already fail inside source discovery,
    so no state transition becomes a generic waiver. Anything unproven
    keeps that rejection. Returns the ignored deployment-only input
    entries, sorted by path.
    """
    sealed_states = {entry["path"]: entry["state"] for entry in sealed}
    live_states = {entry["path"]: entry["state"] for entry in discovered}
    if sealed_states.keys() != live_states.keys():
        _fail("state-conflict", "the sealed OMP configuration sources have drifted")
    declared = [
        operation
        for project in payload["projects"]
        for operation in project["private_operations"]
    ] + list(payload["shared_operations"])
    operations = _declared_operations(payload)
    roots = [Path(project["root"]) for project in payload["projects"]]
    protected = [Path(operation["target"]) for operation in declared]
    protected.append(Path(payload["backup_root"]))
    for operation in declared:
        for field in (
            operation["ownership"].get("reference"),
            operation["change"].get("source_ref"),
        ):
            if isinstance(field, Mapping) and isinstance(field.get("path"), str):
                protected.append(Path(field["path"]))
    retirements: list[tuple[Mapping[str, Any], Path]] = []
    for operation in declared:
        if operation["phase"] != "cleanup":
            continue
        if (
            operation["change"] != {"kind": "remove"}
            or operation["owner_kind"] != "directory"
            or operation["selector"] != "whole-resource"
        ):
            _fail(
                "scope-conflict",
                "the cleanup dependency scope carries an unknown target kind",
            )
        target = Path(operation["target"])
        if target.name == _LEGACY_TREE and target.parent in roots:
            retirements.append((operation, target))
    if retirements:
        from sbtd_trellis_uninstall import prepare_trellis_uninstall

        cleanup_results = (stage_results or {}).get("cleanup") or {}
        for operation, target in retirements:
            prior = cleanup_results.get(operation["resource_id"])
            if (
                prior is not None
                and prior["status"] == "succeeded"
                and prior["after"] == _ABSENT
                and snapshot(target) == _ABSENT
            ):
                # Proven already cleaned: the retry runs no vendor plan for
                # this tree, so it contributes no footprint to protect.
                continue
            prepared = prepare_trellis_uninstall(target.parent)
            plan = prepared["payload"]
            if plan["status"] != "ready":
                # An unavailable vendor mutates nothing; the executor
                # reports the blocked retirement instead of validating it.
                continue
            protected.extend(Path(resource["path"]) for resource in plan["resources"])
    ignored: list[dict[str, Any]] = []
    for path in sorted(sealed_states):
        sealed_state = sealed_states[path]
        live_state = live_states[path]
        if sealed_state == live_state:
            continue
        proven = _proven_input_outcome(operations, stage_results, path, sealed_state)
        if proven is not None:
            if proven != live_state:
                _fail(
                    "state-conflict",
                    "the sealed OMP configuration sources have drifted",
                )
            continue
        if (
            sealed_state["type"] not in {"file", "absent"}
            or live_state["type"] not in {"file", "absent"}
        ):
            _fail(
                "state-conflict",
                "the sealed OMP configuration sources have drifted",
            )
        candidate = Path(path)
        if any(candidate == root for root in roots) or any(
            candidate.is_relative_to(scope) or scope.is_relative_to(candidate)
            for scope in protected
        ):
            _fail(
                "state-conflict",
                "the sealed OMP configuration sources have drifted",
            )
        ignored.append(
            {"path": path, "sealed_state": sealed_state, "live_state": live_state}
        )
    return ignored


def validate_deployment_declarations(
    payload: Mapping[str, Any],
    *,
    followup_deployed: Mapping[str, Any] | None = None,
    stage_results: Mapping[str, Mapping[str, Any]] | None = None,
    cleanup_only: bool = False,
    readonly_legacy: bool = False,
) -> list[dict[str, Any]] | None:
    """Re-derive the closed deploy write set without trusting a resealed list.

    With ``cleanup_only`` the caller is the migration cleanup phase, which
    never redeploys: every structural, ownership and live host-binding check
    below still runs, but sealed OMP discovery inputs that drifted may be
    accepted by ``_cleanup_safe_input_drift`` only when provably irrelevant
    to the cleanup scope. The ignored deployment-only input entries are
    then returned, sorted by path; every other caller keeps the historical
    proven-change rule and a None return.
    """


    ignored: list[dict[str, Any]] = []
    roots = sorted(project["root"] for project in payload["projects"])
    successor = payload.get("successor")
    successor_embedded = (
        {}
        if successor is None
        else {result["resource_id"]: result for result in successor["apply_results"]}
    )
    followup_owned = (
        {}
        if payload.get("followup") is None or followup_deployed is None
        else followup_deployed
    )
    all_deploy = [
        operation
        for project in payload["projects"]
        for operation in project["private_operations"]
        if operation["phase"] == "deploy"
    ] + [
        operation
        for operation in payload["shared_operations"]
        if operation["phase"] == "deploy"
    ]
    shared_deploy = [
        operation
        for operation in payload["shared_operations"]
        if operation["phase"] == "deploy"
    ]
    declaration = payload["deployment"]
    if not all_deploy:
        if declaration is not None:
            if not _empty_no_touch_successor(payload):
                _fail(
                    "semantic-violation",
                    "a deployment declaration requires declared deployment operations",
                )
            from sbtd_migration_plan import _check_agents_no_touch_untouched

            for project in payload["projects"]:
                _check_agents_no_touch_untouched(project)
        return ignored if cleanup_only else None
    if declaration is None:
        _fail(
            "semantic-violation",
            "deployment operations require an explicit deployment declaration",
        )
    expected_mode = "init" if shared_deploy else "init-projects"
    if declaration["mode"] != expected_mode:
        _fail("scope-conflict", "the deployment mode does not match its operation set")
    platform = declaration["platform"]
    if platform not in {"codex", "omp"}:
        _fail(
            "invalid-argument", "the deployment platform must be explicitly supported"
        )
    if platform == "codex" and declaration["inputs"]:
        _fail(
            "scope-conflict",
            "the sealed deployment does not match the Codex producer",
        )
    if legacy_graft_operations(payload):
        if not readonly_legacy:
            reject_legacy_execution(payload)
        validate_archived_graft_declarations(payload)
        return ignored if cleanup_only else None
    expected_private: dict[str, list[dict[str, Any]]] = {
        project["root"]: [] for project in payload["projects"]
    }
    _declare_approved_agents(payload, expected_private, check_live=False)
    for project in payload["projects"]:
        actual = [
            operation
            for operation in project["private_operations"]
            if operation["phase"] == "deploy"
        ]
        if actual != expected_private[project["root"]]:
            _fail(
                "semantic-violation",
                "the approved project AGENTS deployment set was changed",
            )
    shared = [
        operation
        for operation in payload["shared_operations"]
        if operation["phase"] == "deploy"
    ]
    if not shared:
        if payload["shared_operations"]:
            _fail(
                "scope-conflict",
                "shared legacy operations require their declared deployment",
            )
        return ignored if cleanup_only else None
    if any(operation["dependent_projects"] != roots for operation in shared):
        _fail(
            "scope-conflict", "shared deployment requires the complete selected batch"
        )
    discovered = None
    if platform == "omp":
        from onboard import user_home
        from sbtd_omp_sources import discover_omp_sources

        discovered = discover_omp_sources(
            [Path(root) for root in roots], home=user_home(), environ=os.environ
        )
        if declaration["inputs"] != discovered["inputs"]:
            if cleanup_only:
                ignored = _cleanup_safe_input_drift(
                    payload,
                    declaration["inputs"],
                    discovered["inputs"],
                    stage_results,
                )
            else:
                _require_proven_input_changes(
                    payload,
                    declaration["inputs"],
                    discovered["inputs"],
                    stage_results,
                )
    omp_agents_target = _omp_agents_template_target(platform)
    templates = {
        str(operation.target): operation
        for operation in _installation_templates(
            roots, omp_agents_target=omp_agents_target
        )
    }
    copied = {operation["target"]: operation for operation in shared}
    if set(copied) != set(templates):
        _fail(
            "semantic-violation",
            "the complete canonical installation deployment set was changed",
        )
    for target, operation in copied.items():
        selected = templates[target]
        directory = selected.kind == "dir"
        source = {"path": str(selected.source), "state": snapshot(selected.source)}
        if (
            operation["change"]
            != {
                "kind": "copy-directory" if directory else "copy-file",
                "source_ref": source,
            }
            or operation["selector"]
            != ("whole-resource" if directory else "global-rules")
            or operation["ownership"]
            != {"kind": "template-source", "reference": source}
        ):
            _fail(
                "ownership-conflict",
                "an installation deployment source is not canonical",
            )
        paused = [
            earlier
            for earlier in payload["shared_operations"]
            if earlier["phase"] == "apply"
            and earlier["target"] == target
            and earlier["selector"] == "pause-legacy-routing"
        ]
        requirement = operation["before_requirement"]
        expected = {
            "kind": "phase-after",
            "phase": "apply",
            "resource_id": operation["resource_id"],
        }
        if paused:
            if len(paused) != 1 or requirement != expected:
                _fail(
                    "ownership-conflict",
                    "global routing must follow its exact paused predecessor",
                )
        elif successor_embedded.get(operation["resource_id"]) is not None:
            if requirement != expected:
                _fail(
                    "ownership-conflict",
                    "global routing must follow its exact paused predecessor",
                )
        elif followup_owned.get(operation["resource_id"]) is not None:
            # A followup batch replaces a predecessor-owned target only from
            # that exact proven deployment outcome, sealed as concrete state.
            if requirement != {
                "kind": "state",
                "state": followup_owned[operation["resource_id"]],
            }:
                _fail(
                    "ownership-conflict",
                    "a followup replacement must start from the exact "
                    "predecessor deployment outcome",
                )
        elif requirement["kind"] != "state" or requirement["state"] not in (
            _ABSENT,
            source["state"],
        ):
            _fail(
                "ownership-conflict",
                "an installation target has unrecognized customized content",
            )
    return ignored if cleanup_only else None


@dataclass(frozen=True)
class DeploymentContext:
    manifest_path: Path
    output_path: Path
    manifest: dict[str, Any]
    applied: dict[str, Any]
    previous: dict[str, Any] | None
    started_at: str
    expected_before: dict[str, Mapping[str, Any]]
    manifest_raw: bytes
    apply_raw: bytes
    context_paths: tuple[Path, Path]


def _require_output_clear_of_missing(
    output_path: Path, payload: Mapping[str, Any]
) -> None:
    """Keep new evidence off a reconciled record's missing historical path.

    Reconciled deployment evidence cites the historical receipt it observed
    absent; that path stays reserved for the truthful record, so no later
    evidence output may equal it or overlap it in either direction.
    """
    reconciliation = payload.get("reconciliation")
    if reconciliation is None:
        return
    missing = Path(reconciliation["missing_deployment_evidence"]["path"])
    if contracts._publication_paths_overlap(str(output_path), str(missing)):
        _fail(
            "private-scope",
            "deployment evidence must not overlap the cited missing historical receipt",
        )


def load_deployment_context(
    manifest_path: Path,
    apply_path: Path,
    output_path: Path,
    *,
    previous_path: Path | None,
    mode: str,
    roots: Sequence[Path],
    hooks_authorized: bool,
) -> DeploymentContext:
    """All context and actual-state checks precede every deployment write."""
    from sbtd_migration import (
        _check_source_backups,
        _private_document,
        _protected_followup_ancestry,
        _result_index,
        _validate_context,
    )

    if mode not in {"init", "init-projects"}:
        _fail(
            "scope-conflict",
            "migration deployment is supported only by init and init-projects",
        )
    manifest, manifest_raw = _private_document(manifest_path, "manifest")
    applied, apply_raw = _private_document(apply_path, "apply_receipt")
    previous = None
    documents = {"apply_receipt": applied}
    raw_documents = {"manifest": manifest_raw, "apply_receipt": apply_raw}
    if previous_path is not None:
        previous, previous_raw = _private_document(previous_path, "deployment_evidence")
        documents["deployment_evidence"] = previous
        raw_documents["deployment_evidence"] = previous_raw
    contracts.validate_declared_bindings(manifest, documents, raw_documents)
    contracts._bind_success_gate(applied, {"applied", "already-complete"})
    started_at = datetime.now(timezone.utc).isoformat()
    if any(
        contracts._parse_timestamp(document["payload"]["finished_at"])
        > contracts._parse_timestamp(started_at)
        for document in documents.values()
    ):
        _fail(
            "state-conflict",
            "the deployment clock predates its completed input evidence",
        )
    private = require_private_directory(manifest_path.parent)
    if (
        not output_path.is_absolute()
        or output_path.resolve() != output_path
        or output_path == private
        or not output_path.is_relative_to(private)
        or output_path in {manifest_path, apply_path, previous_path}
    ):
        _fail(
            "private-scope",
            "deployment evidence requires a new path inside the manifest directory",
        )
    require_private_directory(output_path.parent)
    if snapshot(output_path) != _ABSENT:
        _fail("state-conflict", "the deployment evidence target already exists")
    for protected_path, is_directory in _protected_followup_ancestry(manifest):
        if contracts._publication_paths_overlap(str(output_path), str(protected_path)):
            _fail(
                "private-scope",
                "deployment evidence must not overlap a protected predecessor object",
            )
    if previous is not None:
        _require_output_clear_of_missing(output_path, previous["payload"])
    declared_roots = {project["root"] for project in manifest["payload"]["projects"]}
    if {str(root) for root in roots} != declared_roots or len(roots) != len(
        declared_roots
    ):
        _fail(
            "scope-conflict",
            "deployment roots must exactly match the confirmed migration batch",
        )
    operations = [
        operation
        for project in manifest["payload"]["projects"]
        for operation in project["private_operations"]
        if operation["phase"] == "deploy"
    ] + [
        operation
        for operation in manifest["payload"]["shared_operations"]
        if operation["phase"] == "deploy"
    ]
    if not operations and not _empty_no_touch_successor(manifest["payload"]):
        _fail(
            "missing-deployment-plan",
            "this manifest contains no declared deployment operations",
        )
    if mode == "init-projects" and manifest["payload"]["shared_operations"]:
        _fail(
            "scope-conflict",
            "project-only deployment cannot execute shared-HOME operations",
        )
    declaration = manifest["payload"]["deployment"]
    if declaration is None or declaration["mode"] != mode:
        _fail("scope-conflict", "the init entry must match the sealed deployment scope")
    reject_legacy_execution(manifest["payload"])
    if hooks_authorized or any(
        operation["selector"] == "graft-hooks" for operation in operations
    ):
        _fail(*_UNSUPPORTED)
    try:
        _validate_context(manifest_path, manifest, previous=applied, deployment=previous)
        _check_source_backups(manifest)
    except contracts.ContractError as error:
        if error.code != "approved-routing-drift":
            raise
        _fail("state-conflict", error.message)
    applied_results, prior_results = _result_index(applied), _result_index(previous)
    resolution = contracts.resolution_stage_results(
        manifest["payload"], {"apply": applied_results}
    )
    expected_before: dict[str, Mapping[str, Any]] = {}
    for operation in operations:
        result = prior_results.get(operation["resource_id"])
        if result is not None and result["status"] == "succeeded":
            expected = result["after"]
        else:
            expected = contracts._expected_before(
                operation["before_requirement"], resolution
            )
            if result is not None and (
                result["before"] is None
                or result["after"] != result["before"]
                or result["before"] != expected
            ):
                _fail(
                    "state-conflict",
                    "a partially written resource needs explicit recovery",
                )
        if expected is None or snapshot(Path(operation["target"])) != expected:
            _fail("state-conflict", "a declared deployment resource has drifted")
        expected_before[operation["resource_id"]] = expected
        if result is not None and result["backup_ref"] is not None:
            reference = result["backup_ref"]
            if snapshot(Path(reference["path"])) != reference["state"]:
                _fail(
                    "original-unavailable",
                    "a prior deployment original is unavailable",
                    3,
                )
    return DeploymentContext(
        manifest_path,
        output_path,
        manifest,
        applied,
        previous,
        started_at,
        expected_before,
        manifest_raw,
        apply_raw,
        (manifest_path, apply_path),
    )


def _assemble_deployment_evidence(
    context: DeploymentContext,
    results: Mapping[str, Mapping[str, Any]],
    reports: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    failed_smokes: set[str],
    reconciliation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble and fully validate one cumulative evidence document, unsaved.

    This is the pure assembly/validation portion of save_deployment_evidence:
    same project statuses, same payload, same seals and binding checks, but no
    filesystem write. Reconciliation provenance is immutable through a retry
    chain: a fresh current-state record supplies its metadata exactly once, a
    retry of an already reconciled record carries the identical metadata
    forward, and the two can never disagree or silently appear/disappear.
    When reconciliation provenance is present, the raw manifest/apply bytes
    are bound explicitly so the metadata can never point at other inputs.
    """
    from sbtd_migration_verify import validate_deployment_reports

    prior_reconciliation = (
        None
        if context.previous is None
        else context.previous["payload"].get("reconciliation")
    )
    if (
        reconciliation is not None
        and prior_reconciliation is not None
        and reconciliation != prior_reconciliation
    ):
        _fail(
            "provenance-conflict",
            "reconciliation provenance cannot change across a deployment retry",
        )
    effective_reconciliation = (
        reconciliation if reconciliation is not None else prior_reconciliation
    )
    prior_reports = (
        {
            project["root"]: project["report_refs"]
            for project in context.previous["payload"]["projects"]
        }
        if prior_reconciliation is not None
        else {}
    )
    manifest = context.manifest
    projects: list[dict[str, Any]] = []
    shared_operations = [
        operation
        for operation in manifest["payload"]["shared_operations"]
        if operation["phase"] == "deploy"
    ]
    finished = datetime.now(timezone.utc).isoformat()
    window: dict[str, Any] = {
        "manifest_id": manifest["manifest_id"],
        "apply_id": context.applied["apply_id"],
        "started_at": context.started_at,
        "finished_at": finished,
        "previous_deployment_id": context.previous["deployment_id"]
        if context.previous
        else None,
    }
    if effective_reconciliation is not None:
        window["reconciliation"] = copy.deepcopy(dict(effective_reconciliation))
    for declared in manifest["payload"]["projects"]:
        root = declared["root"]
        private_operations = [
            operation
            for operation in declared["private_operations"]
            if operation["phase"] == "deploy"
        ]
        required = private_operations + [
            operation
            for operation in shared_operations
            if root in operation["dependent_projects"]
        ]
        resource_ids = {operation["resource_id"] for operation in required}
        statuses = {
            results[resource]["status"]
            for resource in resource_ids
            if resource in results
        }
        complete = resource_ids <= results.keys() and statuses <= {"succeeded"}
        status = (
            "failed"
            if "failed" in statuses or root in failed_smokes
            else ("blocked" if not complete else "not-verified")
        )
        private_ids = {operation["resource_id"] for operation in private_operations}
        project = {
            "root": root,
            "source_ref": declared["source_ref"],
            "head": declared["head"],
            "status": status,
            "reason": (
                "deployment resource execution failed"
                if "failed" in statuses
                else "project smoke failed"
                if root in failed_smokes
                else "deployment is incomplete"
                if not complete
                else "no project validation report is bound to this deployment"
            ),
            "nextStep": (
                "Preserve private evidence and resolve the recorded failure before retrying."
                if not complete or "failed" in statuses or root in failed_smokes
                else "Bind a genuine validation report before treating this deployment as accepted."
            ),
            "private_results": [
                dict(results[rid]) for rid in sorted(private_ids) if rid in results
            ],
            "shared_operation_ids": sorted(
                operation["operation_id"]
                for operation in shared_operations
                if root in operation["dependent_projects"]
                and operation["resource_id"] in results
            ),
            "report_refs": list(reports.get(root, ())),
        }
        if complete and project["report_refs"] and root not in failed_smokes:
            try:
                validate_deployment_reports(
                    window,
                    project,
                    epoch_started=context.applied["payload"]["finished_at"]
                    if context.previous
                    else None,
                    context_paths=context.context_paths,
                    verified_manifest=(
                        manifest
                        if project["report_refs"] == prior_reports.get(root)
                        else None
                    ),
                )
            except contracts.ContractError:
                project.update(
                    status="failed",
                    reason="the actual deployment reports did not pass acceptance",
                )
            else:
                project.update(status="succeeded", reason="", nextStep="")
        projects.append(project)
    shared_ids = {operation["resource_id"] for operation in shared_operations}
    payload = {
        **window,
        "projects": projects,
        "shared_results": [
            dict(results[rid]) for rid in sorted(shared_ids) if rid in results
        ],
        "status": contracts._aggregate(
            [project["status"] for project in projects],
            ("failed", "blocked", "not-verified"),
            "succeeded",
            None,
        ),
    }
    evidence = contracts.seal_document("deployment_evidence", payload)
    contracts.validate_cumulative(context.previous, evidence, "deployment_evidence")
    if effective_reconciliation is not None:
        contracts.validate_declared_bindings(
            manifest,
            {"apply_receipt": context.applied, "deployment_evidence": evidence},
            {"manifest": context.manifest_raw, "apply_receipt": context.apply_raw},
        )
    else:
        contracts.validate_declared_bindings(
            manifest,
            {"apply_receipt": context.applied, "deployment_evidence": evidence},
        )
    return evidence


def save_deployment_evidence(
    context: DeploymentContext,
    results: Mapping[str, Mapping[str, Any]],
    reports: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    failed_smokes: set[str],
) -> dict[str, Any]:
    """Seal one observed cumulative deployment, preserving all prior successes.

    The proposed result is fully validated before the single write: a retry
    of reconciled evidence can never claim its cited missing historical
    path, and no invalid result is ever persisted.
    """
    evidence = _assemble_deployment_evidence(
        context, results, reports, failed_smokes=failed_smokes
    )
    _require_output_clear_of_missing(context.output_path, evidence["payload"])
    result = contracts.validate_deployment_result(
        {"path": str(context.output_path), "evidence": evidence}
    )
    from sbtd_migration import (
        _check_reference,
        _check_source_backups,
        _check_stage_backups,
        _operations,
        _require_reconciliation_provenance,
        _result_index,
    )

    provenance = _require_reconciliation_provenance(context.manifest, evidence)
    if provenance:
        for project in context.manifest["payload"]["projects"]:
            no_touch = project.get("agents_no_touch")
            if no_touch is not None:
                provenance += (no_touch["target"], no_touch["template"])
        _check_source_backups(context.manifest)
        _check_stage_backups({"apply": _result_index(context.applied), "deploy": results})
        for operation in _operations(context.manifest):
            if operation["phase"] != "deploy":
                continue
            observed = results.get(operation["resource_id"])
            if observed is None or observed["status"] != "succeeded":
                continue
            _check_reference({"path": operation["target"], "state": observed["after"]})
        for project in evidence["payload"]["projects"]:
            for reference in project["report_refs"]:
                _check_reference(reference)
        for reference in provenance:
            _check_reference(reference)
    save_document(
        context.output_path, evidence, private_root=context.manifest_path.parent
    )
    return result




def smoke_evidence_dir(private_root: Path, root: str) -> Path:
    """Private per-root report directory under the manifest vault. No project write."""
    digest = hashlib.sha256(root.encode("utf-8")).hexdigest()
    path = private_root / "deployment-smoke" / digest
    require_private_directory(private_root)
    _prepare_target_parents(path / ".keep", private_root)
    return require_private_directory(path, create=True)


def collect_project_smoke(
    root: Path,
    evidence_dir: Path,
    *,
    context_paths: tuple[Path, Path],
) -> list[dict[str, Any]]:
    """Fresh local check. Empty refs are failure, not success."""
    from sbtd_deployment_smoke import run_project_smoke

    refs = run_project_smoke(root, evidence_dir, context_paths=context_paths)
    if not isinstance(refs, list) or len(refs) != 2:
        _fail(
            "report-acceptance",
            "project smoke did not return its JSON report and summary",
            3,
        )
    checked: list[dict[str, Any]] = []
    for ref in refs:
        if not isinstance(ref, Mapping) or "path" not in ref or "state" not in ref:
            _fail("report-acceptance", "a smoke report reference is incomplete", 3)
        path = Path(ref["path"])
        if path == evidence_dir or not path.is_relative_to(evidence_dir):
            _fail("private-scope", "a smoke report left its evidence directory")
        if snapshot(path) != ref["state"]:
            _fail("state-conflict", "a smoke report does not match its reference")
        checked.append({"path": str(path), "state": dict(ref["state"])})
    report, summary = (Path(item["path"]) for item in checked)
    if report.suffix != ".json" or report.stem != summary.stem or summary.suffix == ".json":
        _fail(
            "report-acceptance",
            "project smoke did not return its JSON report and same-stem summary",
            3,
        )
    return checked


def _completed_roots(
    projects: Sequence[Mapping[str, Any]],
    operations: Sequence[Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
    *,
    include_unwritten: bool = False,
) -> list[str]:
    completed: list[str] = []
    for project in projects:
        root = project["root"]
        required = [
            operation["resource_id"]
            for operation in operations
            if operation["phase"] == "deploy"
            and (
                root in operation["dependent_projects"]
                or any(
                    item["resource_id"] == operation["resource_id"]
                    for item in project.get("private_operations", ())
                    if item.get("phase") == "deploy"
                )
            )
        ]
        if (required or include_unwritten) and all(
            results.get(resource_id, {}).get("status") == "succeeded"
            for resource_id in required
        ):
            completed.append(root)
    return completed


def _drifted_roots(
    operations: Sequence[Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
) -> set[str]:
    failed: set[str] = set()
    for operation in operations:
        if operation.get("phase") != "deploy":
            continue
        result = results.get(operation["resource_id"])
        if result is None or result.get("status") != "succeeded":
            continue
        try:
            unchanged = snapshot(Path(operation["target"])) == result["after"]
        except (contracts.ContractError, OSError, RuntimeError, ValueError):
            unchanged = False
        if not unchanged:
            failed.update(operation["dependent_projects"])
    return failed


def run_completed_smokes(
    projects: Sequence[Mapping[str, Any]],
    operations: Sequence[Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
    *,
    private_root: Path,
    context_paths: tuple[Path, Path],
    previous_reports: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    reserved: Sequence[Path] = (),
    include_unwritten: bool = False,
) -> tuple[dict[str, list[dict[str, Any]]], set[str]]:
    """Fresh smoke for completed roots only. Successful fresh refs replace prior refs.

    Previous artifacts remain immutable and reserved by cumulative evidence validation.
    """
    reports: dict[str, list[dict[str, Any]]] = {
        root: [dict(ref) for ref in refs]
        for root, refs in (previous_reports or {}).items()
    }
    failed: set[str] = set()
    for root in _completed_roots(
        projects, operations, results, include_unwritten=include_unwritten
    ):
        evidence_dir = smoke_evidence_dir(private_root, root)
        if any(
            contracts._publication_paths_overlap(str(evidence_dir), str(path))
            for path in reserved
        ):
            failed.add(root)
            continue
        try:
            fresh = collect_project_smoke(
                Path(root), evidence_dir, context_paths=context_paths
            )
        except (contracts.ContractError, OSError, RuntimeError, ValueError, ImportError):
            failed.add(root)
            continue
        reports[root] = fresh
    failed.update(_drifted_roots(operations, results))
    return reports, failed

def execute_migration_deployment(
    context: DeploymentContext,
) -> tuple[dict[str, Any], int]:
    """Execute only the sealed deploy closure and save truthful cumulative results."""
    from sbtd_migration import _result_index, runtime_versions

    manifest = context.manifest
    reject_legacy_execution(manifest["payload"])
    projects = manifest["payload"]["projects"]
    operations = [
        operation
        for project in projects
        for operation in project["private_operations"]
        if operation["phase"] == "deploy"
    ] + [
        operation
        for operation in manifest["payload"]["shared_operations"]
        if operation["phase"] == "deploy"
    ]
    if any(graft_operation(operation) for operation in operations):
        _fail(*_UNSUPPORTED)
    prior = _result_index(context.previous)
    previous_payload = context.previous["payload"] if context.previous else {}
    reconciliation = previous_payload.get("reconciliation")
    carry_observer_reports = (
        reconciliation is not None
        and reconciliation["runtime_versions"]["onboard"] != runtime_versions()["onboard"]
    )
    if carry_observer_reports and any(
        prior.get(operation["resource_id"], {}).get("status") != "succeeded"
        for operation in operations
    ):
        _fail(
            "provenance-conflict",
            "a different observer cannot retry unfinished reconciled deployment writes",
        )
    results = {resource: dict(value) for resource, value in prior.items()}
    scopes = {
        operation["resource_id"]: Path(project["root"])
        for project in projects
        for operation in project["private_operations"]
        if operation["phase"] == "deploy"
    }
    for operation in manifest["payload"]["shared_operations"]:
        if operation["phase"] != "deploy":
            continue
        candidates = [
            Path(record["path"])
            for record in manifest["payload"]["shared_roots"]
            if Path(operation["target"]).is_relative_to(Path(record["path"]))
        ]
        if len(candidates) != 1:
            _fail(
                "scope-conflict",
                "a shared deployment target has no unique approved root",
            )
        scopes[operation["resource_id"]] = candidates[0]
    vault = Path(manifest["payload"]["backup_root"])
    stopped = False
    for operation in operations:
        resource = operation["resource_id"]
        old = prior.get(resource)
        if old is not None and old["status"] == "succeeded":
            continue
        if stopped:
            break
        scope = scopes[resource]
        backup_path = vault / manifest["manifest_id"] / "deploy" / resource
        expected = context.expected_before[resource]
        result = execute_resource(
            operation,
            expected=expected,
            root=scope,
            private_root=vault,
            backup_path=backup_path,
        )
        if old is not None and old["backup_ref"] is not None:
            result["backup_ref"] = old["backup_ref"]
        results[resource] = result
        stopped = result["status"] != "succeeded"
    previous_reports = {
        project["root"]: list(project["report_refs"])
        for project in previous_payload.get("projects", ())
    }
    if carry_observer_reports:
        # The immutable reconciliation already records its observer. Recheck
        # current outcomes without replacing its reports with another producer.
        reports = previous_reports
        failed_smokes = _drifted_roots(operations, results)
    else:
        reports, failed_smokes = run_completed_smokes(
            projects,
            operations,
            results,
            private_root=context.manifest_path.parent,
            previous_reports=previous_reports,
            reserved=[context.output_path, context.manifest_path],
            include_unwritten=_empty_no_touch_successor(manifest["payload"]),
            context_paths=context.context_paths,
        )
    try:
        production = save_deployment_evidence(
            context, results, reports, failed_smokes=failed_smokes
        )
    except (contracts.ContractError, OSError, RuntimeError, ValueError):
        return {
            "status": "failed",
            "deploymentEvidence": None,
            "reason": "deployment evidence could not be safely saved; observed writes are retained",
            "operationResults": list(results.values()),
            "nextStep": "Preserve originals and inspect observed results; do not infer a usable receipt.",
        }, 5
    status = production["evidence"]["payload"]["status"]
    return {
        "status": status,
        "deploymentEvidence": production,
        "projects": production["evidence"]["payload"]["projects"],
        "operationResults": list(results.values()),
    }, {"succeeded": 0, "not-verified": 3, "blocked": 2, "failed": 5}[status]


def run_migration_init(mode: str, args: Any) -> int:
    """Dedicated existing-init context, before unrelated installer side effects."""
    from onboard import (
        default_codex_home,
        expand_path,
        resolve_global_skills_dir,
        resolve_project_roots,
    )
    from sbtd_migration import _argument_path

    payload: dict[str, Any] = {"mode": mode, "deploymentEvidence": None}
    try:
        if (
            getattr(args, "graft_retire_legacy", False)
            or getattr(args, "graft_legacy_bindings", None)
        ):
            _fail(
                "scope-conflict",
                "legacy MCP retirement requires a new explicit installation plan, not a sealed historical deployment",
            )
        if mode != "init-projects" and getattr(args, "no_mcp", False):
            _fail(
                "scope-conflict",
                "sealed deployment cannot omit its declared host wiring",
            )
        if not args.yes:
            _fail(
                "confirmation-required",
                "migration deployment requires its own explicit confirmation",
            )
        selected_platform = getattr(args, "platform", None)
        if selected_platform == "oh-my-pi":
            selected_platform = "omp"
        if selected_platform not in {None, "codex", "omp"}:
            _fail(
                "scope-conflict",
                "this deployment context supports only its declared host",
            )
        if getattr(args, "developer", None) is not None:
            _fail(
                "scope-conflict",
                "deployment cannot create an undeclared developer identity",
            )
        if getattr(args, "skip_project_agents", False):
            _fail(
                "scope-conflict",
                "deployment cannot omit a declared project instruction resource",
            )
        canonical_scopes = {
            "global_agents_path": default_codex_home() / "AGENTS.md",
            "global_skills_dir": resolve_global_skills_dir()[0],
        }
        for name, expected in canonical_scopes.items():
            provided = getattr(args, name, None)
            if provided is not None and (
                mode == "init-projects" or expand_path(provided) != expected
            ):
                _fail(
                    "scope-conflict",
                    "installation scope options must match the sealed deployment batch",
                )
        context = load_deployment_context(
            _argument_path(args.migration_manifest),
            _argument_path(args.migration_apply_receipt),
            _argument_path(args.deployment_evidence_out),
            previous_path=_argument_path(args.previous_deployment_evidence)
            if args.previous_deployment_evidence
            else None,
            mode=mode,
            roots=resolve_project_roots(args),
            hooks_authorized=bool(getattr(args, "graft_hooks", False)),
        )
        if (
            selected_platform is not None
            and selected_platform
            != context.manifest["payload"]["deployment"]["platform"]
        ):
            _fail(
                "scope-conflict",
                "the selected host must match the sealed deployment manifest",
            )
        production, code = execute_migration_deployment(context)
        payload.update(production)
    except contracts.ContractError as error:
        code = error.exit_code
        payload.update(
            status="blocked" if code == 2 else "failed",
            reason=str(error),
            nextStep="Resolve the migration precondition without modifying preserved originals.",
        )
    except (OSError, RuntimeError, ValueError, ImportError):
        code = 5
        payload.update(
            status="failed",
            reason="the installed deployment runtime could not safely complete",
            nextStep="Preserve originals and inspect the private execution evidence.",
        )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, allow_nan=False))
    else:
        print("Host deployment: " + str(payload["status"]))
        print(
            "Detailed artifacts remain private; use --json only with authorized private storage."
        )
    return code


