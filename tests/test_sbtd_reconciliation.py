"""Current-state reconciliation lifecycle; native graph/report boundaries are fixtures."""
from __future__ import annotations

# ruff: noqa: I001 -- approved fixture imports bootstrap the local script path.

import contextlib
import dataclasses
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests import test_sbtd_approved_agents_deployment as approved
from tests.test_sbtd_followup_batch import _failed_copy, _synthetic_smoke
from tests.test_sbtd_migration_verify import _tree_bytes

import onboard_contracts as contracts
from sbtd_graft_deployment import load_deployment_context, save_deployment_evidence
from sbtd_migration_files import snapshot
from sbtd_reconciliation import reconcile_deployment
from sbtd_recovery import plan_recovery
from sbtd_migration_verify import verify_migration


def setUpModule():
    approved.setUpModule()


def tearDownModule():
    approved.tearDownModule()


class CurrentStateReconciliationTests(unittest.TestCase):
    def test_missing_receipt_current_state_is_verified_without_redeployment(self):
        with tempfile.TemporaryDirectory() as directory:
            batch = approved._SignedBatch(Path(directory).resolve())
            manifest = batch.plan(deployment_mode="init")
            manifest_path = batch.write_manifest(manifest, "manifest.json")
            _applied, apply_path = batch.apply(
                manifest_path, routing_approvals=batch.approval
            )
            missing_path = batch.evidence / "interrupted-deployment.json"
            deployed, code = batch.execute(manifest_path, apply_path, missing_path)
            self.assertEqual(code, 0, deployed)
            missing_path.unlink()
            project_before = _tree_bytes(batch.root)
            home_before = _tree_bytes(batch.home)
            originals_before = _tree_bytes(batch.vault)
            manifest_before = manifest_path.read_bytes()
            apply_before = apply_path.read_bytes()
            output_path = batch.evidence / "current-state-evidence.json"

            with mock.patch.dict(os.environ, batch.environment):
                with self.assertRaises(contracts.ContractError):
                    verify_migration(manifest_path, apply_path, missing_path)

                from sbtd_reconciliation import reconcile_deployment

                with (
                    mock.patch(
                        "sbtd_graft_deployment.verified_runtime",
                        return_value=dict(approved._RUNTIME),
                    ),
                    mock.patch(
                        "sbtd_graft_deployment.run_project_smoke",
                        side_effect=_synthetic_smoke(manifest),
                    ),
                    mock.patch(
                        "sbtd_graft_deployment.build_project_graph",
                        side_effect=AssertionError("reconciliation must not rebuild"),
                    ),
                    mock.patch(
                        "sbtd_graft_deployment.execute_resource",
                        side_effect=AssertionError("reconciliation must not deploy"),
                    ),
                ):
                    result = reconcile_deployment(
                        manifest_path,
                        apply_path,
                        missing_path,
                        output_path,
                        confirmed=True,
                    )

                self.assertEqual(result["path"], str(output_path))
                evidence = json.loads(output_path.read_bytes())
                self.assertEqual(
                    evidence["payload"]["reconciliation"]["historical_execution"],
                    "unknown",
                )
                self.assertEqual(
                    evidence["payload"]["reconciliation"]["kind"], "current-state"
                )
                verified, verify_code = verify_migration(
                    manifest_path, apply_path, output_path
                )

            self.assertEqual(verify_code, 0, verified)
            self.assertEqual(verified["status"], "verified")
            self.assertEqual(
                verified["migration"]["verification"]["payload"]["acceptance_basis"],
                "current-state",
            )
            self.assertFalse(missing_path.exists())
            self.assertEqual(_tree_bytes(batch.root), project_before)
            self.assertEqual(_tree_bytes(batch.home), home_before)
            self.assertEqual(_tree_bytes(batch.vault), originals_before)
            self.assertEqual(manifest_path.read_bytes(), manifest_before)
            self.assertEqual(apply_path.read_bytes(), apply_before)


def _native_doubles(manifest, *, smoke=None):
    """Contract-backed doubles for the native external boundaries only.

    Deployment writers stay hard-blocked: reconciliation must never rebuild a
    graph or execute a resource while observing current state.
    """
    return (
        mock.patch(
            "sbtd_graft_deployment.verified_runtime",
            return_value=dict(approved._RUNTIME),
        ),
        mock.patch(
            "sbtd_graft_deployment.run_project_smoke",
            side_effect=(
                _synthetic_smoke(manifest) if smoke is None else smoke
            ),
        ),
        mock.patch(
            "sbtd_graft_deployment.build_project_graph",
            side_effect=AssertionError("reconciliation must not rebuild"),
        ),
        mock.patch(
            "sbtd_graft_deployment.execute_resource",
            side_effect=AssertionError("reconciliation must not deploy"),
        ),
    )


def _interrupted_deployment(case):
    """One genuinely deployed batch whose historical receipt is then lost."""
    directory = tempfile.TemporaryDirectory()
    case.addCleanup(directory.cleanup)
    batch = approved._SignedBatch(Path(directory.name).resolve())
    manifest = batch.plan(deployment_mode="init")
    manifest_path = batch.write_manifest(manifest, "manifest.json")
    _receipt, apply_path = batch.apply(
        manifest_path, routing_approvals=batch.approval
    )
    missing_path = batch.evidence / "interrupted-deployment.json"
    deployed, code = batch.execute(manifest_path, apply_path, missing_path)
    case.assertEqual(code, 0, deployed)
    missing_path.unlink()
    return batch, manifest, manifest_path, apply_path, missing_path


def _reconcile(batch, manifest, manifest_path, apply_path, missing_path, output_path, *, smoke=None):
    patches = _native_doubles(manifest, smoke=smoke)
    with (
        mock.patch.dict(os.environ, batch.environment),
        patches[0],
        patches[1],
        patches[2],
        patches[3],
    ):
        return reconcile_deployment(
            manifest_path,
            apply_path,
            missing_path,
            output_path,
            confirmed=True,
        )


def _failed_run_smoke(manifest):
    """Smoke double whose native check genuinely fails (exit 1), truthfully reported."""
    passing = _synthetic_smoke(manifest)

    def smoke(project, runtime, evidence_dir):
        refs = passing(project, runtime, evidence_dir)
        raw_path, envelope_path, summary_path = (
            Path(reference["path"]) for reference in refs
        )
        raw = json.loads(raw_path.read_bytes())
        raw["exitCode"] = 1
        raw["processExitCode"] = 1
        raw_path.write_text(json.dumps(raw), encoding="utf-8")
        envelope = json.loads(envelope_path.read_bytes())
        envelope["reports"][0]["status"] = "failed"
        envelope["reports"][0]["sha256"] = hashlib.sha256(
            raw_path.read_bytes()
        ).hexdigest()
        envelope_path.write_text(json.dumps(envelope), encoding="utf-8")
        return [
            {"path": str(path), "state": snapshot(path)}
            for path in (raw_path, envelope_path, summary_path)
        ]

    return smoke


def _stage_results(document_path):
    """Resource results of one stage document, indexed by resource_id."""
    document = json.loads(document_path.read_bytes())
    results = [
        result
        for project in document["payload"]["projects"]
        for result in project["private_results"]
    ] + list(document["payload"]["shared_results"])
    return {result["resource_id"]: result for result in results}


def _apply_only_operation(manifest):
    """One declared apply resource with no deploy observation of its own."""
    payload = manifest["payload"]
    operations = [
        operation
        for project in payload["projects"]
        for operation in project["private_operations"]
    ] + list(payload["shared_operations"])
    deployed = {
        operation["resource_id"] for operation in operations if operation["phase"] == "deploy"
    }
    apply_only = sorted(
        (
            operation
            for operation in operations
            if operation["phase"] == "apply" and operation["resource_id"] not in deployed
        ),
        key=lambda operation: operation["target"],
    )
    if not apply_only:
        raise AssertionError("fixture must declare an apply-only resource")
    return apply_only[0]


def _drift_target(target, after):
    """Mutate one receipt-proven target away from its recorded after-state."""
    if after["type"] == "absent":
        target.write_bytes(b"resurrected receipt-proven absence\n")
    elif after["type"] == "file":
        with open(target, "ab") as handle:
            handle.write(b"\nreceipt outcome drift\n")
    else:
        (target / "receipt-outcome-drift.marker").write_bytes(b"drift\n")


def _reseal_deployment_evidence(document_path, mutate):
    """Mutate one deployment evidence payload in place, then honestly reseal it.

    The seal is recomputed from the mutated payload, so the result is a
    schema-valid, self-consistent document whose provenance claims are false.
    """
    document = json.loads(document_path.read_bytes())
    mutate(document["payload"])
    resealed = contracts.seal_document("deployment_evidence", document["payload"])
    document_path.write_bytes(contracts.canonical_json_bytes(resealed))
    return resealed


class CurrentStateReconciliationLifecycleTests(unittest.TestCase):
    def test_reconcile_then_cumulative_retry_preserves_current_state_provenance(self):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        result = _reconcile(
            batch, manifest, manifest_path, apply_path, missing_path, output_path
        )
        evidence = result["evidence"]

        # An ordinary cumulative deployment retry after reconciliation must
        # carry the reconciliation provenance forward unchanged: provenance is
        # immutable and can never be laundered back to an executed origin.
        retry_path = batch.evidence / "deployment-retry.json"
        retried, retry_code = batch.execute(
            manifest_path,
            apply_path,
            retry_path,
            previous_path=output_path,
            rebuild_graph=False,
        )
        self.assertEqual(retry_code, 0, retried)
        retry_evidence = json.loads(retry_path.read_bytes())
        self.assertEqual(
            retry_evidence["payload"]["reconciliation"],
            evidence["payload"]["reconciliation"],
        )
        self.assertEqual(
            retry_evidence["payload"]["previous_deployment_id"],
            evidence["deployment_id"],
        )
        with mock.patch.dict(os.environ, batch.environment):
            verified, verify_code = verify_migration(
                manifest_path, apply_path, retry_path
            )
        self.assertEqual(verify_code, 0, verified)
        self.assertEqual(
            verified["migration"]["verification"]["payload"]["acceptance_basis"],
            "current-state",
        )
        self.assertFalse(missing_path.exists())

    def test_historical_receipt_reappearance_fails_verification(self):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        _reconcile(batch, manifest, manifest_path, apply_path, missing_path, output_path)
        evidence_before = output_path.read_bytes()
        appeared = b'{"late_historical_evidence": true}\n'
        missing_path.write_bytes(appeared)
        try:
            with (
                mock.patch.dict(os.environ, batch.environment),
                self.assertRaises(contracts.ContractError) as rejected,
            ):
                verify_migration(manifest_path, apply_path, output_path)
            self.assertEqual(rejected.exception.code, "state-conflict")
            self.assertEqual(missing_path.read_bytes(), appeared)
            self.assertEqual(output_path.read_bytes(), evidence_before)
        finally:
            missing_path.unlink()

    def test_reconciled_evidence_supports_recovery_and_cleanup_planning(self):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        _reconcile(batch, manifest, manifest_path, apply_path, missing_path, output_path)

        with mock.patch.dict(os.environ, batch.environment):
            # Recovery planning consumes the genuine reconciled record: every
            # inverse step chains from the derived results and their retained
            # originals, not from a mock echo.
            planned, plan_code = plan_recovery(
                manifest_path,
                apply_receipt_path=apply_path,
                deployment_evidence_path=output_path,
            )
            self.assertEqual(plan_code, 0, planned)
            plan = planned["recovery"]["plan"]
            self.assertTrue(plan["plan_id"])

            verified, verify_code = verify_migration(
                manifest_path, apply_path, output_path
            )
        self.assertEqual(verify_code, 0, verified)
        verification = verified["migration"]["verification"]["payload"]
        self.assertEqual(verification["acceptance_basis"], "current-state")
        # Cleanup planning consumption: candidates are derived from the
        # reconciled evidence after-states and the live tree.
        self.assertIn("shared_cleanup_candidates", verification)
        for project in verification["projects"]:
            self.assertIn("cleanup_candidates", project)

    def test_cli_reconcile_roundtrip_emits_envelope_and_verifies(self):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        project_before = _tree_bytes(batch.root)
        originals_before = _tree_bytes(batch.vault)

        import onboard

        argv = [
            "onboard",
            "migration",
            "--phase",
            "reconcile",
            "--manifest",
            str(manifest_path),
            "--apply-receipt",
            str(apply_path),
            "--missing-deployment-evidence",
            str(missing_path),
            "--deployment-evidence-out",
            str(output_path),
            "--yes",
            "--json",
        ]
        patches = _native_doubles(manifest)
        with (
            mock.patch.dict(os.environ, batch.environment),
            mock.patch.object(sys, "argv", argv),
            patches[0],
            patches[1],
            patches[2],
            patches[3],
        ):
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = onboard.main()
        self.assertEqual(code, 0, buffer.getvalue())
        envelope = json.loads(buffer.getvalue())
        self.assertEqual(envelope["mode"], "migration")
        self.assertEqual(envelope["phase"], "reconcile")
        self.assertEqual(envelope["status"], "reconciled")
        self.assertEqual(envelope["manifest_id"], manifest["manifest_id"])
        self.assertIsNone(envelope["verification_id"])
        self.assertTrue(envelope["projects"])
        self.assertEqual(
            {project["status"] for project in envelope["projects"]}, {"reconciled"}
        )
        self.assertEqual(
            envelope["migration"]["deployment_evidence_path"], str(output_path)
        )
        evidence = envelope["migration"]["deployment_evidence"]
        self.assertEqual(
            evidence["payload"]["reconciliation"],
            {
                "kind": "current-state",
                "historical_execution": "unknown",
                "manifest_ref": {
                    "path": str(manifest_path),
                    "state": snapshot(manifest_path),
                },
                "apply_receipt_ref": {
                    "path": str(apply_path),
                    "state": snapshot(apply_path),
                },
                "missing_deployment_evidence": {
                    "path": str(missing_path),
                    "state": {"type": "absent", "checksum": None},
                },
                "runtime_versions": evidence["payload"]["reconciliation"][
                    "runtime_versions"
                ],
            },
        )
        self.assertEqual(
            evidence["payload"]["reconciliation"]["runtime_versions"]["graft"],
            manifest["payload"]["tool_versions"]["graft"],
        )
        self.assertEqual(evidence, json.loads(output_path.read_bytes()))

        with mock.patch.dict(os.environ, batch.environment):
            verified, verify_code = verify_migration(
                manifest_path, apply_path, output_path
            )
        self.assertEqual(verify_code, 0, verified)
        self.assertEqual(
            verified["migration"]["verification"]["payload"]["acceptance_basis"],
            "current-state",
        )
        self.assertFalse(missing_path.exists())
        self.assertEqual(_tree_bytes(batch.root), project_before)
        self.assertEqual(_tree_bytes(batch.vault), originals_before)

    def test_repeated_reconciliation_to_a_new_path_is_idempotent(self):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        first_path = batch.evidence / "current-state-evidence.json"
        first = _reconcile(
            batch, manifest, manifest_path, apply_path, missing_path, first_path
        )
        # The same output is never overwritten; a fresh path observes the same
        # unchanged current state into an equivalent new record.
        with self.assertRaises(contracts.ContractError) as collision:
            _reconcile(
                batch, manifest, manifest_path, apply_path, missing_path, first_path
            )
        self.assertEqual(collision.exception.code, "state-conflict")

        second_path = batch.evidence / "current-state-evidence-2.json"
        second = _reconcile(
            batch, manifest, manifest_path, apply_path, missing_path, second_path
        )
        self.assertEqual(
            second["evidence"]["payload"]["reconciliation"],
            first["evidence"]["payload"]["reconciliation"],
        )
        with mock.patch.dict(os.environ, batch.environment):
            verified, verify_code = verify_migration(
                manifest_path, apply_path, second_path
            )
        self.assertEqual(verify_code, 0, verified)
        self.assertFalse(missing_path.exists())


class CurrentStateReconciliationRefusalTests(unittest.TestCase):
    def test_missing_consent_blocks_before_any_write_or_smoke(self):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        evidence_before = _tree_bytes(batch.evidence)
        patches = _native_doubles(manifest)
        with (
            mock.patch.dict(os.environ, batch.environment),
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            self.assertRaises(contracts.ContractError) as failure,
        ):
            reconcile_deployment(manifest_path, apply_path, missing_path, output_path)
        self.assertEqual(failure.exception.code, "confirmation-required")
        self.assertFalse(output_path.exists())
        self.assertFalse(missing_path.exists())
        self.assertEqual(_tree_bytes(batch.evidence), evidence_before)

    def test_existing_historical_receipt_stays_authoritative(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        batch = approved._SignedBatch(Path(directory.name).resolve())
        manifest = batch.plan(deployment_mode="init")
        manifest_path = batch.write_manifest(manifest, "manifest.json")
        _receipt, apply_path = batch.apply(
            manifest_path, routing_approvals=batch.approval
        )
        historical_path = batch.evidence / "interrupted-deployment.json"
        deployed, code = batch.execute(manifest_path, apply_path, historical_path)
        self.assertEqual(code, 0, deployed)
        historical_before = historical_path.read_bytes()
        output_path = batch.evidence / "current-state-evidence.json"
        evidence_before = _tree_bytes(batch.evidence)

        with self.assertRaises(contracts.ContractError) as failure:
            _reconcile(
                batch,
                manifest,
                manifest_path,
                apply_path,
                historical_path,
                output_path,
            )
        self.assertEqual(failure.exception.code, "state-conflict")
        self.assertEqual(historical_path.read_bytes(), historical_before)
        self.assertFalse(output_path.exists())
        self.assertEqual(_tree_bytes(batch.evidence), evidence_before)

    def test_unsafe_and_colliding_paths_reject_before_writes(self):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"

        # Output must be absolute, physical, new, private and disjoint from
        # every declared/protected object; all rejections precede any write.
        cases = {
            "output equals missing": (missing_path, missing_path),
            "output aliases absent missing by case": (
                missing_path, missing_path.with_name(missing_path.name.upper()),
            ),
            "output aliases absent missing by Unicode": (
                batch.evidence / "caf\u00e9.json",
                batch.evidence / "cafe\u0301.json",
            ),
            "output equals manifest": (missing_path, manifest_path),
            "output outside private dir": (
                missing_path,
                batch.base / "outside.json",
            ),
            "relative output": (missing_path, Path("relative-current-state.json")),
            "relative missing": (Path("relative-missing.json"), output_path),
            "missing equals apply receipt": (apply_path, output_path),
        }
        for name, (missing, output) in cases.items():
            with self.subTest(case=name):
                evidence_before = _tree_bytes(batch.evidence)
                manifest_before = manifest_path.read_bytes()
                with self.assertRaises(contracts.ContractError) as failure:
                    _reconcile(
                        batch, manifest, manifest_path, apply_path, missing, output
                    )
                self.assertEqual(failure.exception.code, "private-scope")
                # No write or smoke happened; every input is byte-identical.
                self.assertEqual(_tree_bytes(batch.evidence), evidence_before)
                self.assertEqual(manifest_path.read_bytes(), manifest_before)
                self.assertFalse(missing_path.exists())
                self.assertFalse(output_path.exists())

        # An already-existing output is preserved, never overwritten.
        output_path.write_bytes(b"pre-existing private content\n")
        evidence_before = _tree_bytes(batch.evidence)
        with self.assertRaises(contracts.ContractError) as failure:
            _reconcile(
                batch,
                manifest,
                manifest_path,
                apply_path,
                missing_path,
                output_path,
            )
        self.assertEqual(failure.exception.code, "state-conflict")
        self.assertEqual(output_path.read_bytes(), b"pre-existing private content\n")
        self.assertEqual(_tree_bytes(batch.evidence), evidence_before)

    def test_tampered_deployed_target_fails_closed_without_repairs(self):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        tampered = batch.agents.read_bytes() + b"\ntampered after deployment\n"
        batch.agents.write_bytes(tampered)

        with self.assertRaises(contracts.ContractError) as failure:
            _reconcile(
                batch,
                manifest,
                manifest_path,
                apply_path,
                missing_path,
                output_path,
            )
        self.assertEqual(failure.exception.code, "state-conflict")
        # No evidence, no repair, no historical fabrication.
        self.assertFalse(output_path.exists())
        self.assertFalse(missing_path.exists())
        self.assertEqual(batch.agents.read_bytes(), tampered)

    def test_missing_retained_original_fails_closed(self):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        resource = contracts.resource_id("markdown", str(batch.agents))
        backup = (
            batch.vault / manifest["manifest_id"] / "deploy" / resource
        )
        self.assertTrue(backup.exists())
        backup_bytes = backup.read_bytes()
        backup.unlink()
        vault_after_unlink = _tree_bytes(batch.vault)

        with self.assertRaises(contracts.ContractError) as failure:
            _reconcile(
                batch,
                manifest,
                manifest_path,
                apply_path,
                missing_path,
                output_path,
            )
        self.assertEqual(failure.exception.code, "original-unavailable")
        self.assertFalse(output_path.exists())
        self.assertFalse(missing_path.exists())
        self.assertEqual(_tree_bytes(batch.vault), vault_after_unlink)
        self.assertNotEqual(batch.agents.read_bytes(), backup_bytes)

    def test_altered_manifest_bytes_fail_binding(self):
        batch, _manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        forged = json.loads(manifest_path.read_bytes())
        forged["payload"]["custodian"] = "forged-custodian"
        forged_path = batch.evidence / "manifest-forged.json"
        forged_path.write_bytes(
            contracts.canonical_json_bytes(
                contracts.seal_document("manifest", forged["payload"])
            )
        )

        with self.assertRaises(contracts.ContractError) as failure:
            _reconcile(
                batch,
                forged,
                forged_path,
                apply_path,
                missing_path,
                output_path,
            )
        self.assertEqual(failure.exception.code, "binding-violation")
        self.assertFalse(output_path.exists())
        self.assertFalse(missing_path.exists())

    def test_incomplete_apply_receipt_is_rejected(self):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        failed_apply = batch.evidence / "apply-failed.json"
        _failed_copy(apply_path, "apply_receipt", failed_apply)

        with self.assertRaises(contracts.ContractError) as failure:
            _reconcile(
                batch,
                manifest,
                manifest_path,
                failed_apply,
                missing_path,
                output_path,
            )
        self.assertEqual(failure.exception.code, "binding-violation")
        self.assertFalse(output_path.exists())
        self.assertFalse(missing_path.exists())

    def test_tampered_approved_candidate_is_rejected(self):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        projected = batch.agents.read_bytes()
        batch.candidate.write_bytes(
            approved._PAUSE_ASSET.read_bytes() + b"\ntampered after approval\n"
        )

        with self.assertRaises(contracts.ContractError):
            _reconcile(
                batch,
                manifest,
                manifest_path,
                apply_path,
                missing_path,
                output_path,
            )
        self.assertFalse(output_path.exists())
        self.assertFalse(missing_path.exists())
        self.assertEqual(batch.agents.read_bytes(), projected)

    def test_failed_fresh_smoke_leaves_artifacts_but_no_evidence(self):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        evidence_before = set(os.listdir(batch.evidence))

        with self.assertRaises(contracts.ContractError) as failure:
            _reconcile(
                batch,
                manifest,
                manifest_path,
                apply_path,
                missing_path,
                output_path,
                smoke=_failed_run_smoke(manifest),
            )
        self.assertEqual(failure.exception.code, "report-acceptance")
        self.assertFalse(output_path.exists())
        self.assertFalse(missing_path.exists())
        # Truthful fresh smoke artifacts may remain; accepted evidence may not.
        created = set(os.listdir(batch.evidence)) - evidence_before
        self.assertTrue(
            any(name.startswith("api-report-graft-smoke-") for name in created)
        )

    def test_uncompleted_fresh_smoke_records_no_evidence(self):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        evidence_before = _tree_bytes(batch.evidence)

        def raising_smoke(project, runtime, evidence_dir):
            raise RuntimeError("synthetic native check crash")

        with self.assertRaises(contracts.ContractError) as failure:
            _reconcile(
                batch,
                manifest,
                manifest_path,
                apply_path,
                missing_path,
                output_path,
                smoke=raising_smoke,
            )
        self.assertEqual(failure.exception.code, "report-unavailable")
        self.assertFalse(output_path.exists())
        self.assertFalse(missing_path.exists())
        self.assertEqual(_tree_bytes(batch.evidence), evidence_before)

    def test_smoke_that_mutates_a_target_fails_closed(self):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        passing = _synthetic_smoke(manifest)
        projected = batch.agents.read_bytes()

        def mutating_smoke(project, runtime, evidence_dir):
            refs = passing(project, runtime, evidence_dir)
            with open(batch.agents, "ab") as handle:
                handle.write(b"\nsmoke mutation\n")
            return refs

        with self.assertRaises(contracts.ContractError) as failure:
            _reconcile(
                batch,
                manifest,
                manifest_path,
                apply_path,
                missing_path,
                output_path,
                smoke=mutating_smoke,
            )
        self.assertEqual(failure.exception.code, "state-conflict")
        self.assertFalse(output_path.exists())
        self.assertFalse(missing_path.exists())
        # The mutation is preserved as evidence of the unsafe check; nothing
        # is silently repaired.
        self.assertEqual(
            batch.agents.read_bytes(), projected + b"\nsmoke mutation\n"
        )

    def test_output_race_is_rejected_without_overwriting(self):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        passing = _synthetic_smoke(manifest)
        raced = b"raced private content\n"

        def racing_smoke(project, runtime, evidence_dir):
            refs = passing(project, runtime, evidence_dir)
            output_path.write_bytes(raced)
            return refs

        with self.assertRaises(contracts.ContractError) as failure:
            _reconcile(
                batch,
                manifest,
                manifest_path,
                apply_path,
                missing_path,
                output_path,
                smoke=racing_smoke,
            )
        self.assertEqual(failure.exception.code, "state-conflict")
        self.assertEqual(output_path.read_bytes(), raced)
        self.assertFalse(missing_path.exists())

    def test_tampered_reconciled_evidence_fails_verification(self):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        _reconcile(batch, manifest, manifest_path, apply_path, missing_path, output_path)

        document = json.loads(output_path.read_bytes())
        document["payload"]["reconciliation"]["kind"] = "executed"
        output_path.write_bytes(json.dumps(document).encode("utf-8"))
        with (
            mock.patch.dict(os.environ, batch.environment),
            self.assertRaises(contracts.ContractError),
        ):
            verify_migration(manifest_path, apply_path, output_path)

    def test_apply_only_target_drift_fails_before_any_smoke(self):
        # Every successful apply target without a fresh deploy observation is
        # compared with its receipt after-state before smoke runs, regardless
        # of runtime version equality.
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        operation = _apply_only_operation(manifest)
        target = Path(operation["target"])
        after = _stage_results(apply_path)[operation["resource_id"]]["after"]
        self.assertEqual(snapshot(target), after)
        _drift_target(target, after)
        drifted = snapshot(target)
        evidence_before = _tree_bytes(batch.evidence)

        with self.assertRaises(contracts.ContractError) as failure:
            _reconcile(
                batch,
                manifest,
                manifest_path,
                apply_path,
                missing_path,
                output_path,
            )
        self.assertEqual(failure.exception.code, "state-conflict")
        self.assertFalse(output_path.exists())
        self.assertFalse(missing_path.exists())
        # The refusal precedes any fresh smoke: no report artifacts appear and
        # the drifted target is preserved, never repaired.
        self.assertEqual(_tree_bytes(batch.evidence), evidence_before)
        self.assertEqual(snapshot(target), drifted)

    def test_smoke_mutating_apply_only_target_fails_closed(self):
        # The same receipt-outcome gate runs again after the native check
        # window, so a smoke that mutates an apply-only target invalidates the
        # observation instead of being published.
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        operation = _apply_only_operation(manifest)
        target = Path(operation["target"])
        after = _stage_results(apply_path)[operation["resource_id"]]["after"]
        passing = _synthetic_smoke(manifest)

        def mutating_smoke(project, runtime, evidence_dir):
            refs = passing(project, runtime, evidence_dir)
            _drift_target(target, after)
            return refs

        with self.assertRaises(contracts.ContractError) as failure:
            _reconcile(
                batch,
                manifest,
                manifest_path,
                apply_path,
                missing_path,
                output_path,
                smoke=mutating_smoke,
            )
        self.assertEqual(failure.exception.code, "state-conflict")
        self.assertFalse(output_path.exists())
        self.assertFalse(missing_path.exists())
        # The mutation is preserved as evidence of the unsafe check.
        self.assertNotEqual(snapshot(target), after)

    def test_retry_output_cannot_claim_reconciled_missing_path(self):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        _reconcile(batch, manifest, manifest_path, apply_path, missing_path, output_path)

        # A cumulative retry whose proposed output IS the cited missing
        # historical receipt path is refused at preflight, before any write
        # or smoke.
        with (
            mock.patch.dict(os.environ, batch.environment),
            self.assertRaises(contracts.ContractError) as failure,
        ):
            load_deployment_context(
                manifest_path,
                apply_path,
                missing_path,
                previous_path=output_path,
                mode="init",
                roots=[batch.root],
                hooks_authorized=False,
            )
        self.assertEqual(failure.exception.code, "private-scope")
        self.assertFalse(missing_path.exists())

        # The save path refuses the same collision even when the output is
        # swapped onto the missing path after a clean preflight.
        retry_path = batch.evidence / "deployment-retry.json"
        with mock.patch.dict(os.environ, batch.environment):
            context = load_deployment_context(
                manifest_path,
                apply_path,
                retry_path,
                previous_path=output_path,
                mode="init",
                roots=[batch.root],
                hooks_authorized=False,
            )
        swapped = dataclasses.replace(context, output_path=missing_path)
        carried = _stage_results(output_path)
        with self.assertRaises(contracts.ContractError) as failure:
            save_deployment_evidence(swapped, carried, {}, failed_smokes=set())
        self.assertEqual(failure.exception.code, "private-scope")
        self.assertFalse(missing_path.exists())
        self.assertFalse(retry_path.exists())

    def test_smoke_cannot_create_an_absent_original_slot(self):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        graph = next(
            op for project in manifest["payload"]["projects"]
            for op in project["private_operations"]
            if op["change"]["kind"] == "build-graft"
        )
        backup = (
            Path(manifest["payload"]["backup_root"]) / manifest["manifest_id"]
            / "deploy" / graph["resource_id"]
        )
        self.assertFalse(backup.exists())
        passing = _synthetic_smoke(manifest)

        def mutating_smoke(project, runtime, evidence_dir):
            refs = passing(project, runtime, evidence_dir)
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_bytes(b"unexpected original")
            return refs

        with self.assertRaises(contracts.ContractError) as failure:
            _reconcile(
                batch, manifest, manifest_path, apply_path, missing_path,
                output_path, smoke=mutating_smoke,
            )
        self.assertEqual(failure.exception.code, "state-conflict")
        self.assertEqual(backup.read_bytes(), b"unexpected original")
        self.assertFalse(output_path.exists())
        self.assertFalse(missing_path.exists())

    def test_retry_smoke_cannot_recreate_the_missing_historical_receipt(self):
        from sbtd_graft_deployment import execute_migration_deployment

        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        _reconcile(batch, manifest, manifest_path, apply_path, missing_path, output_path)
        retry_path = batch.evidence / "deployment-retry.json"
        passing = _synthetic_smoke(manifest)

        def late_receipt(project, runtime, evidence_dir):
            refs = passing(project, runtime, evidence_dir)
            missing_path.write_bytes(b"late historical receipt")
            return refs

        with mock.patch.dict(os.environ, batch.environment):
            context = load_deployment_context(
                manifest_path, apply_path, retry_path, previous_path=output_path,
                mode="init", roots=[batch.root], hooks_authorized=False,
            )
            with (
                mock.patch("sbtd_graft_deployment.verified_runtime",
                           return_value=dict(approved._RUNTIME)),
                mock.patch("sbtd_graft_deployment.run_project_smoke",
                           side_effect=late_receipt),
            ):
                result, code = execute_migration_deployment(context)
        self.assertNotEqual(code, 0, result)
        self.assertFalse(retry_path.exists())
        self.assertEqual(missing_path.read_bytes(), b"late historical receipt")

    def test_deployment_drift_after_context_validation_prevents_publication(self):
        import sbtd_migration

        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        before = batch.agents.read_bytes()
        late_content = before + b"\nConcurrent operator change after validation.\n"
        validate_context = sbtd_migration._validate_context

        def change_after_real_validation(*args, **kwargs):
            result = validate_context(*args, **kwargs)
            batch.agents.write_bytes(late_content)
            return result

        with (
            mock.patch(
                "sbtd_migration._validate_context",
                side_effect=change_after_real_validation,
            ),
            self.assertRaises(contracts.ContractError) as failure,
        ):
            _reconcile(
                batch, manifest, manifest_path, apply_path, missing_path, output_path
            )
        self.assertEqual(failure.exception.code, "state-conflict")
        self.assertEqual(batch.agents.read_bytes(), late_content)
        self.assertFalse(output_path.exists())
        self.assertFalse(missing_path.exists())

    def test_report_drift_after_context_validation_prevents_publication(self):
        import sbtd_migration

        damaged_bytes = b"Concurrent report replacement.\n"

        for change in ("modify", "delete"):
            with self.subTest(change=change):
                batch, manifest, manifest_path, apply_path, missing_path = (
                    _interrupted_deployment(self)
                )
                output_path = batch.evidence / "current-state-evidence.json"
                validate_context = sbtd_migration._validate_context
                changed_report = []

                def change_after_real_validation(
                    *args, change=change, validate=validate_context,
                    changed=changed_report, **kwargs
                ):
                    result = validate(*args, **kwargs)
                    reference = kwargs["deployment"]["payload"]["projects"][0]["report_refs"][0]
                    report = Path(reference["path"])
                    if change == "modify":
                        report.write_bytes(damaged_bytes)
                    else:
                        report.unlink()
                    changed.append(report)
                    return result

                with (
                    mock.patch(
                        "sbtd_migration._validate_context",
                        side_effect=change_after_real_validation,
                    ),
                    self.assertRaises(contracts.ContractError) as failure,
                ):
                    _reconcile(
                        batch, manifest, manifest_path, apply_path, missing_path, output_path
                    )
                self.assertEqual(failure.exception.code, "state-conflict")
                if change == "modify":
                    self.assertEqual(changed_report[0].read_bytes(), damaged_bytes)
                else:
                    self.assertFalse(changed_report[0].exists())
                self.assertFalse(output_path.exists())
                self.assertFalse(missing_path.exists())


class CurrentStateProvenanceBindingTests(unittest.TestCase):
    """Public verify must reject resealed evidence carrying false provenance.

    Regression coverage for the deferred RC1 findings RC1-P2-PROVENANCE-PATH
    and RC1-P2-OBSERVER-RUNTIME: a resealed record whose cited input path no
    longer resolves to the recorded bytes, or whose observer Onboard runtime
    fingerprint was swapped for another format-valid value, must not verify.
    """

    def test_equivalent_existing_source_references_still_verify(self):
        # Provenance binds safe objects and exact bytes, not the caller's argv
        # spelling: intact copies remain valid cited sources.
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        _reconcile(batch, manifest, manifest_path, apply_path, missing_path, output_path)
        copies = {}
        for ref_key, source in (
            ("manifest_ref", manifest_path), ("apply_receipt_ref", apply_path)
        ):
            copied = batch.evidence / f"preserved-{ref_key}.json"
            copied.write_bytes(source.read_bytes())
            copies[ref_key] = copied

        def cite_copies(payload):
            for ref_key, copied in copies.items():
                payload["reconciliation"][ref_key]["path"] = str(copied)

        _reseal_deployment_evidence(output_path, cite_copies)

        with mock.patch.dict(os.environ, batch.environment):
            verified, verify_code = verify_migration(
                manifest_path, apply_path, output_path
            )
        self.assertEqual(verify_code, 0, verified)
        self.assertEqual(verified["status"], "verified")
        self.assertEqual(
            verified["migration"]["verification"]["payload"]["acceptance_basis"],
            "current-state",
        )
        self.assertFalse(missing_path.exists())

    def test_signed_successor_can_reconcile_and_verify_predecessor(self):
        import sbtd_migration as migration
        from tests.test_sbtd_reconciliation_followup import _signed_lineage

        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        sealed = manifest["payload"]["tool_versions"]
        observer = {**sealed, "onboard": "runtime-sha256:" + "a" * 64}
        self.assertNotEqual(observer, sealed)
        public_path, pair_path = _signed_lineage(
            batch.evidence, sealed["onboard"], observer["onboard"]
        )
        output_path = batch.evidence / "successor-observation.json"
        with (
            mock.patch.object(migration, "_LINEAGE_PUBLIC_KEY", public_path),
            mock.patch.object(migration, "_LINEAGE_DOCUMENT", pair_path),
            mock.patch.object(migration, "runtime_versions", return_value=observer),
            mock.patch.dict(os.environ, batch.environment),
        ):
            _reconcile(batch, manifest, manifest_path, apply_path, missing_path, output_path)
            verified, code = verify_migration(manifest_path, apply_path, output_path)
        self.assertEqual(code, 0, verified)
        self.assertEqual(verified["status"], "verified")
        evidence = json.loads(output_path.read_bytes())
        self.assertEqual(evidence["payload"]["reconciliation"]["runtime_versions"], observer)
        self.assertEqual(
            verified["migration"]["verification"]["payload"]["acceptance_basis"],
            "current-state",
        )

    def test_forged_manifest_ref_path_fails_verification(self):
        self._assert_forged_ref_path_rejected("manifest_ref")

    def test_forged_apply_receipt_ref_path_fails_verification(self):
        self._assert_forged_ref_path_rejected("apply_receipt_ref")

    def _assert_forged_ref_path_rejected(self, ref_key):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        _reconcile(batch, manifest, manifest_path, apply_path, missing_path, output_path)
        genuine = manifest_path if ref_key == "manifest_ref" else apply_path
        wrong_bytes = batch.evidence / f"decoy-{ref_key}.json"
        wrong_bytes.write_bytes(b'{"decoy": true}\n')
        linked = batch.evidence / f"linked-{ref_key}.json"
        linked.symlink_to(genuine)
        manifest_before = manifest_path.read_bytes()
        apply_before = apply_path.read_bytes()

        for name, forged_path in (
            ("nonexistent path", batch.evidence / f"absent-{ref_key}.json"),
            ("existing bytes of another object", wrong_bytes),
            ("existing directory", batch.evidence),
            ("symlink to the genuine input", linked),
        ):
            with self.subTest(ref=ref_key, case=name):
                # Only the cited path changes; the recorded state still
                # describes the genuine input bytes, exactly the reseal
                # forgery the finding demonstrates.
                _reseal_deployment_evidence(
                    output_path,
                    lambda payload, key=ref_key, path=forged_path: payload[
                        "reconciliation"
                    ][key].update({"path": str(path)}),
                )
                forged = output_path.read_bytes()
                evidence_before = _tree_bytes(batch.evidence)
                with (
                    mock.patch.dict(os.environ, batch.environment),
                    self.assertRaises(contracts.ContractError),
                ):
                    verify_migration(manifest_path, apply_path, output_path)
                # Rejection is read-only: forged evidence stays as submitted,
                # inputs are untouched, and nothing is written anywhere.
                self.assertEqual(output_path.read_bytes(), forged)
                self.assertEqual(_tree_bytes(batch.evidence), evidence_before)
                self.assertEqual(manifest_path.read_bytes(), manifest_before)
                self.assertEqual(apply_path.read_bytes(), apply_before)
                self.assertFalse(missing_path.exists())

    def test_foreign_observer_runtime_fails_verification(self):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        _reconcile(batch, manifest, manifest_path, apply_path, missing_path, output_path)

        # Same-runtime baseline: the genuine record verifies before forgery.
        with mock.patch.dict(os.environ, batch.environment):
            verified, verify_code = verify_migration(
                manifest_path, apply_path, output_path
            )
        self.assertEqual(verify_code, 0, verified)
        self.assertEqual(verified["status"], "verified")

        runtime = json.loads(output_path.read_bytes())["payload"]["reconciliation"][
            "runtime_versions"
        ]
        foreign = "runtime-sha256:" + hashlib.sha256(
            b"foreign observer runtime\n"
        ).hexdigest()
        self.assertNotEqual(foreign, runtime["onboard"])

        # Swap only the observer Onboard fingerprint for another format-valid
        # value; the pinned Graft version and every input stay genuine.
        _reseal_deployment_evidence(
            output_path,
            lambda payload: payload["reconciliation"]["runtime_versions"].update(
                {"onboard": foreign}
            ),
        )
        forged = output_path.read_bytes()
        manifest_before = manifest_path.read_bytes()
        apply_before = apply_path.read_bytes()
        with (
            mock.patch.dict(os.environ, batch.environment),
            self.assertRaises(contracts.ContractError),
        ):
            verify_migration(manifest_path, apply_path, output_path)
        self.assertEqual(output_path.read_bytes(), forged)
        self.assertEqual(manifest_path.read_bytes(), manifest_before)
        self.assertEqual(apply_path.read_bytes(), apply_before)
        self.assertFalse(missing_path.exists())


if __name__ == "__main__":
    unittest.main()
