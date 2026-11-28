"""Current-state reconciliation for an interrupted migration deployment.

A confirmed migration batch can reach a state where the deployment writes and
native smoke checks genuinely completed but the cumulative deployment evidence
was never saved (interrupted process, lost buffer, crashed writer). The
historical deploy execution can no longer be proven: no receipt exists and its
exit code is unknowable. This module records exactly what CAN be proven — a
fresh, fully revalidated observation of the current state — as new, explicitly
typed deployment evidence at a new path.

Truthfulness contract (no historical fabrication):

* ``payload.reconciliation.kind`` is ``"current-state"`` and
  ``historical_execution`` is ``"unknown"``. With this metadata present, a
  ``succeeded`` status means the current postconditions were observed and
  accepted NOW; it never claims the original deployment process was observed
  to exit 0, and no new target writes occurred while reconciling.
* Every resource result is derived, never caller-supplied: ``before`` is the
  sealed phase requirement, proven by the exact retained original at the
  deterministic deploy backup path (or by planned absence, which must not
  have invented a backup); ``after`` is the freshly measured current state,
  proven equal to the declared copy source. rc.3 does not re-render Graft
  configuration and does not build a native graph.
* The evidence window (``started_at``/``finished_at``) covers only this
  observation. No smoke report is invented. A project without a genuine
  validation report stays ``not-verified`` and is not recorded as acceptance.
* Writes are limited to the single new evidence document, and only after
  acceptance. The missing historical path is never written. Any failed
  check fails closed before that write.

This producer never calls deployment writers (execute_resource,
execute_migration_deployment, apply_migration, recovery or cleanup paths)
and never reseals the manifest or changes versions/pins.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

import onboard_contracts as contracts
import sbtd_deployment as deployment
from sbtd_migration_files import (
    read_file,
    require_private_directory,
    save_document,
    snapshot,
)

_ABSENT = {"type": "absent", "checksum": None}


def _fail(code: str, message: str, exit_code: int = 2) -> NoReturn:
    raise contracts.ContractError(code, message, exit_code=exit_code)


def _check_candidate_path(
    label: str,
    candidate: Path,
    *,
    private: Path,
    reserved: set[Path],
    protected: Sequence[tuple[Path, bool]],
) -> None:
    """One evidence path: new, private, physical, disjoint from all managed state."""
    if (
        not candidate.is_absolute()
        or candidate.resolve() != candidate
        or candidate == private
        or not candidate.is_relative_to(private)
    ):
        _fail(
            "private-scope",
            f"the {label} evidence path must be a new physical path inside the manifest directory",
        )
    for path in reserved:
        if contracts._publication_paths_overlap(str(candidate), str(path)):
            _fail(
                "private-scope",
                f"the {label} evidence path overlaps a declared or protected object",
            )
    for protected_path, _ in protected:
        if contracts._publication_paths_overlap(str(candidate), str(protected_path)):
            _fail(
                "private-scope",
                f"the {label} evidence path overlaps a protected predecessor object",
            )


def _require_original_state(backup_path: Path, expected: Mapping[str, Any]) -> None:
    if snapshot(backup_path) != expected:
        _fail(
            "state-conflict" if expected["type"] == "absent" else "original-unavailable",
            "a retained deployment original or an absent original slot changed",
            2 if expected["type"] == "absent" else 3,
        )


def _observe_resource(
    operation: Mapping[str, Any],
    *,
    expected: Mapping[str, Any],
    backup_path: Path,
    approved_body: bytes | None,
) -> dict[str, Any]:
    """Derive one truthful result from the retained original and live state.

    Nothing is written. A non-absent sealed before-state must still exist as
    the exact deterministic original below the private vault; an absent
    before-state must not have invented one. The current target bytes must
    equal the deterministic declared outcome of the sealed operation.
    """
    target = Path(operation["target"])
    _require_original_state(backup_path, expected)
    backup_ref = (
        None if expected["type"] == "absent"
        else {"path": str(backup_path), "state": dict(expected)}
    )
    kind = operation["change"]["kind"]
    if deployment.graft_operation(operation):
        _fail(
            "unsupported-in-rc.3",
            "a sealed plan still contains Graft operations; regenerate the plan",
        )
    if deployment._is_approved_agents(operation):
        if approved_body is None:
            _fail(
                "state-conflict",
                "the approved project AGENTS projection is not the signed body",
            )
        current = snapshot(target)
        live = b"" if current["type"] == "absent" else read_file(target, current)
        if (
            live != approved_body
            or operation.get("selector")
            != deployment.approved_agents_selector(approved_body)
        ):
            _fail(
                "state-conflict",
                "the current resource state is not the declared deployment outcome",
            )
        after = current
    elif kind in {"copy-file", "copy-directory"}:
        source = operation["change"]["source_ref"]
        if snapshot(Path(source["path"])) != source["state"]:
            _fail(
                "state-conflict",
                "a canonical installation source changed after planning",
            )
        current = snapshot(target)
        if current != source["state"]:
            _fail(
                "state-conflict",
                "the current resource state is not the declared deployment outcome",
            )
        after = current
    else:
        _fail("unsupported-operation", "the deployment operation is not supported")
    return {
        "phase": "deploy",
        "resource_id": operation["resource_id"],
        "operation_ids": [operation["operation_id"]],
        "dependent_projects": list(operation["dependent_projects"]),
        "status": "succeeded",
        "backup_ref": backup_ref,
        "before": dict(expected),
        "after": after,
        "error": None,
    }


def _require_apply_outcomes(
    operations: Sequence[Mapping[str, Any]],
    applied_results: Mapping[str, Any],
    observed: Mapping[str, Mapping[str, Any]],
) -> None:
    """Apply-only drift gate: receipt outcomes must still hold live.

    Every successful apply target not superseded by a fresh deploy
    observation is compared with its receipt after-state, regardless of
    runtime version equality; deploy-observed resources are proven by their
    own current-state observation instead. Runs before smoke and again
    before publication so a mutating native check fails closed.
    """
    for operation in operations:
        if operation.get("phase") != "apply":
            continue
        resource_id = operation["resource_id"]
        if resource_id in observed:
            continue
        result = applied_results.get(resource_id)
        if (
            result is None
            or result.get("status") != "succeeded"
            or result.get("after") is None
        ):
            _fail(
                "state-conflict",
                "a declared apply resource lacks a complete successful receipt outcome",
            )
        if snapshot(Path(operation["target"])) != result["after"]:
            _fail(
                "state-conflict",
                "an applied resource no longer matches its receipt outcome",
            )


def reconcile_deployment(
    manifest_path: Path,
    apply_path: Path,
    missing_path: Path,
    output_path: Path,
    *,
    confirmed: bool = False,
) -> dict[str, Any]:
    """Record a fresh current-state observation as new typed deploy evidence.

    Requires explicit confirmation, the genuine original manifest bytes, a
    complete successful apply receipt, a truly absent historical deployment
    receipt, and a new non-overwriting output path inside the original
    manifest private directory. Returns the ordinary deployment result
    ``{"path": str, "evidence": document}``; the evidence carries
    ``payload.reconciliation`` current-state provenance. Every refusal raises
    a sanitized ContractError before any accepted evidence exists.
    """
    from sbtd_migration import (
        _check_reference,
        _check_source_backups,
        _check_stage_backups,
        _operations,
        _private_document,
        _protected_followup_ancestry,
        _require_reconciliation_provenance,
        _result_index,
        _validate_context,
        _verified_runtime_lineage,
        runtime_versions,
    )
    from sbtd_deployment_smoke import _require_canonical_input

    if not confirmed:
        _fail(
            "confirmation-required",
            "current-state reconciliation requires its own explicit confirmation",
        )
    manifest_path = Path(manifest_path)
    apply_path = Path(apply_path)
    missing_path = Path(missing_path)
    output_path = Path(output_path)
    if contracts._publication_paths_overlap(str(missing_path), str(output_path)):
        _fail(
            "private-scope",
            "the new evidence path must be distinct from the missing historical path",
        )
    manifest, manifest_raw = _private_document(manifest_path, "manifest")
    deployment.reject_legacy_execution(manifest["payload"])
    applied, apply_raw = _private_document(apply_path, "apply_receipt")
    contracts.validate_declared_bindings(
        manifest,
        {"apply_receipt": applied},
        {"manifest": manifest_raw, "apply_receipt": apply_raw},
    )
    contracts._bind_success_gate(applied, {"applied", "already-complete"})
    _require_canonical_input("manifest", manifest, manifest_raw)
    _require_canonical_input("apply_receipt", applied, apply_raw)
    started_at = datetime.now(timezone.utc).isoformat()
    if contracts._parse_timestamp(
        applied["payload"]["finished_at"]
    ) > contracts._parse_timestamp(started_at):
        _fail(
            "state-conflict",
            "the reconciliation clock predates its completed input evidence",
        )
    private = require_private_directory(manifest_path.parent)
    payload = manifest["payload"]
    declaration = payload["deployment"]
    operations = [
        operation
        for project in payload["projects"]
        for operation in project["private_operations"]
        if operation["phase"] == "deploy"
    ] + [
        operation
        for operation in payload["shared_operations"]
        if operation["phase"] == "deploy"
    ]
    zero_write = contracts._is_zero_write_project_successor(payload)
    if declaration is None or (not operations and not zero_write):
        _fail(
            "missing-deployment-plan",
            "this manifest contains no declared deployment operations",
        )
    vault = Path(payload["backup_root"])
    applied_results = _result_index(applied)
    reserved = deployment._deployment_protected_paths(manifest, applied) | {
        manifest_path, apply_path,
    }
    protected = _protected_followup_ancestry(manifest)
    for label, candidate in (("missing historical", missing_path), ("output", output_path)):
        _check_candidate_path(
            label, candidate, private=private, reserved=reserved, protected=protected
        )

    roots = [Path(project["root"]) for project in payload["projects"]]
    smoke_dirs = deployment._preflight_smoke_evidence_paths(
        private,
        (str(root) for root in roots),
        reserved=reserved | {missing_path, output_path} | {path for path, _ in protected},
    )
    for candidate in (missing_path, output_path):
        require_private_directory(candidate.parent)
    if snapshot(missing_path) != _ABSENT:
        _fail(
            "state-conflict",
            "the historical deployment receipt is not absent; reconciliation would duplicate it",
        )
    if snapshot(output_path) != _ABSENT:
        _fail("state-conflict", "the reconciliation evidence target already exists")
    if zero_write:
        # A zero-write observation still has to prove its complete inherited
        # deployment set before creating any report evidence.
        _validate_context(manifest_path, manifest, previous=applied)

    from sbtd_migration_plan import approved_agents_provenance

    _origin, approved_bodies = approved_agents_provenance(manifest)
    resolution = contracts.resolution_stage_results(
        payload, {"apply": applied_results}
    )
    _check_source_backups(manifest)
    results: dict[str, Mapping[str, Any]] = {}
    expected_before: dict[str, Mapping[str, Any]] = {}
    for operation in operations:
        expected = contracts._expected_before(
            operation["before_requirement"], resolution
        )
        if expected is None:
            _fail(
                "state-conflict",
                "a declared deployment resource has no proven before requirement",
            )
        expected_before[operation["resource_id"]] = expected
        results[operation["resource_id"]] = _observe_resource(
            operation,
            expected=expected,
            backup_path=vault
            / manifest["manifest_id"]
            / "deploy"
            / operation["resource_id"],
            approved_body=approved_bodies.get(operation["target"]),
        )

    if declaration["mode"] == "init" and declaration["platform"] == "omp":
        from onboard import user_home
        from sbtd_omp_sources import discover_omp_sources

        discovered = discover_omp_sources(roots, home=user_home(), environ=os.environ)
        if declaration["inputs"] != discovered["inputs"]:
            deployment._require_proven_input_changes(
                payload,
                declaration["inputs"],
                discovered["inputs"],
                {"apply": applied_results, "deploy": results},
            )

    _require_apply_outcomes(_operations(manifest), applied_results, results)
    reports, failed_smokes = deployment.run_completed_smokes(
        payload["projects"],
        operations,
        results,
        evidence_dirs=smoke_dirs,
        context_paths=(manifest_path, apply_path),
    )
    for operation in operations:
        result = results[operation["resource_id"]]
        if snapshot(Path(operation["target"])) != result["after"]:
            _fail(
                "state-conflict",
                "the native check mutated an observed deployment resource",
            )
        _require_original_state(
            vault / manifest["manifest_id"] / "deploy" / operation["resource_id"],
            expected_before[operation["resource_id"]],
        )
    _check_source_backups(manifest)

    reconciliation = {
        "kind": "current-state",
        "historical_execution": "unknown",
        "manifest_ref": {"path": str(manifest_path), "state": snapshot(manifest_path)},
        "apply_receipt_ref": {"path": str(apply_path), "state": snapshot(apply_path)},
        "missing_deployment_evidence": {
            "path": str(missing_path),
            "state": snapshot(missing_path),
        },
        "runtime_versions": runtime_versions(),
    }
    if reconciliation["runtime_versions"]["onboard"] != payload["tool_versions"]["onboard"]:
        reconciliation["observer_lineage"] = _verified_runtime_lineage()
    context = deployment.DeploymentContext(
        manifest_path=manifest_path,
        output_path=output_path,
        manifest=manifest,
        applied=applied,
        previous=None,
        started_at=started_at,
        expected_before=expected_before,
        manifest_raw=manifest_raw,
        apply_raw=apply_raw,
        context_paths=(manifest_path, apply_path),
        smoke_dirs=smoke_dirs,
    )
    evidence = deployment._assemble_deployment_evidence(
        context, results, reports, failed_smokes=failed_smokes, reconciliation=reconciliation
    )
    if evidence["payload"]["status"] != "succeeded":
        _fail(
            "report-acceptance",
            "the current state did not pass deployment acceptance; no evidence was recorded",
            3,
        )

    # Revalidate the complete context against the assembled, provenance-marked
    # evidence: runtime lineage, revisions, physical aliases, input references
    # and retained backups, all through the ordinary validators.
    _validate_context(manifest_path, manifest, previous=applied, deployment=evidence)

    # Validate the proposed result before the single write: a reconciled
    # record never claims its own cited missing historical path, and no
    # invalid deployment result is ever persisted.
    deployment._require_output_clear_of_missing(output_path, evidence["payload"])
    result = contracts.validate_deployment_result(
        {"path": str(output_path), "evidence": evidence}
    )
    provenance = _require_reconciliation_provenance(manifest, evidence)
    for project in payload["projects"]:
        no_touch = project.get("agents_no_touch")
        if no_touch is not None:
            provenance += (no_touch["target"], no_touch["template"])
    # Final snapshot-only pass: no lineage parsing after observed artifacts.
    _check_source_backups(manifest)
    _check_stage_backups({"apply": applied_results, "deploy": _result_index(evidence)})
    # Apply-only drift gate before publication: the native check window must
    # not have mutated any receipt-proven apply target either.
    _require_apply_outcomes(_operations(manifest), applied_results, results)
    for operation in operations:
        if snapshot(Path(operation["target"])) != results[operation["resource_id"]]["after"]:
            _fail(
                "state-conflict",
                "a deployment resource changed before evidence publication",
            )
        _require_original_state(
            vault / manifest["manifest_id"] / "deploy" / operation["resource_id"],
            expected_before[operation["resource_id"]],
        )
    for project in evidence["payload"]["projects"]:
        for reference in project["report_refs"]:
            if snapshot(Path(reference["path"])) != reference["state"]:
                _fail(
                    "state-conflict",
                    "a fresh report changed before evidence publication",
                )
    for reference in provenance:
        _check_reference(reference)
    if snapshot(output_path) != _ABSENT:
        _fail(
            "state-conflict",
            "the reconciliation evidence target appeared before publication",
        )
    save_document(output_path, evidence, private_root=manifest_path.parent)
    return result
