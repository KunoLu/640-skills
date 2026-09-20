from __future__ import annotations

import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard" / "scripts"
TESTS = Path(__file__).resolve().parent
for import_path in (str(SCRIPTS), str(TESTS)):
    if import_path not in sys.path:
        sys.path.insert(0, import_path)

from onboard_contracts import ContractError, seal_document
from sbtd_migration_files import save_document
from sbtd_recovery import apply_recovery, plan_recovery, run_recovery
from test_sbtd_migration_cleanup import VerifiedMigration
from test_sbtd_migration_verify import _tree_bytes


class RestoredMigration:
    def __init__(self, base: Path) -> None:
        self.base = base
        self.fixture = VerifiedMigration(base)
        self.fixture.build()
        self.cleaned, self.cleanup_code = self.fixture.cleanup(
            confirm_cleanup=self.fixture.verification["verification_id"]
        )
        if self.cleanup_code != 0:
            raise AssertionError(f"cleanup failed: {self.cleaned}")
        self.cleanup_receipt = self.cleaned["migration"]["cleanup_receipt"]
        self.cleanup_path = self.fixture.evidence / (
            f"cleanup-{self.cleanup_receipt['cleanup_id']}.json"
        )
        self.plan_path = self.fixture.evidence / "recovery-plan.json"

    @property
    def root(self) -> Path:
        return self.fixture.root

    @property
    def evidence(self) -> Path:
        return self.fixture.evidence

    def plan(self, *, include_cleanup: bool = True):
        envelope, code = plan_recovery(
            self.fixture.manifest_path,
            apply_receipt_path=self.fixture.apply_path,
            deployment_evidence_path=self.fixture.deployment_path,
            cleanup_receipt_path=self.cleanup_path if include_cleanup else None,
        )
        if code not in (0, 2):
            raise AssertionError(f"recovery plan failed: {envelope}")
        return envelope["recovery"]["plan"]

    def save_plan(self, plan: dict[str, Any]) -> Path:
        save_document(self.plan_path, plan, private_root=self.evidence)
        return self.plan_path


class RecoveryPlanTests(unittest.TestCase):
    def build(self, base: Path) -> RestoredMigration:
        return RestoredMigration(base)

    def test_recovery_plan_restores_the_cleaned_legacy_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            plan = fixture.plan()
            self.assertEqual(plan["payload"]["status"], "planned")
            self.assertEqual(plan["payload"]["target"], "pre-apply")
            targets = {
                resource["resource_id"]: resource["target"]
                for resource in plan["payload"]["resources"]
            }
            cleanup_steps = [
                step
                for step in plan["payload"]["steps"]
                if step["phase"] == "cleanup"
                and targets[step["resource_id"]].endswith("/.trellis")
            ]
            self.assertEqual(len(cleanup_steps), 1)
            step = cleanup_steps[0]
            self.assertEqual(step["expected_current"]["type"], "absent")
            self.assertEqual(step["restore_to"]["type"], "directory")
            self.assertIsNotNone(step["backup_ref"])

            apply_steps = [
                step for step in plan["payload"]["steps"] if step["phase"] == "apply"
            ]
            self.assertTrue(apply_steps)
            self.assertEqual(
                Path(targets[apply_steps[0]["resource_id"]]).name,
                ".gitignore",
            )

    def test_recovery_plan_is_blocked_when_current_state_drifts(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            retained = fixture.root / "AGENTS.md"
            retained.write_text(retained.read_text() + "\nuser edit after cleanup\n")
            plan = fixture.plan()
            self.assertEqual(plan["payload"]["status"], "blocked")
            self.assertTrue(plan["payload"]["conflicts"])
            self.assertEqual(plan["payload"]["steps"], [])

    def test_recovery_plan_is_blocked_by_an_unknown_stage_write(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            payload = copy.deepcopy(fixture.cleanup_receipt["payload"])
            payload["status"] = "failed"
            payload["projects"][0]["status"] = "failed"
            payload["projects"][0]["private_results"][0]["status"] = "failed"
            payload["projects"][0]["reason"] = "unknown write"
            payload["projects"][0]["nextStep"] = "Inspect the retained evidence."
            payload["projects"][0]["private_results"][0]["after"] = None
            payload["projects"][0]["private_results"][0]["error"] = "unknown write"
            unknown = contracts_path = fixture.evidence / "cleanup-unknown.json"
            save_document(
                contracts_path,
                seal_document("cleanup_receipt", payload),
                private_root=fixture.evidence,
            )
            envelope, code = plan_recovery(
                fixture.fixture.manifest_path,
                apply_receipt_path=fixture.fixture.apply_path,
                deployment_evidence_path=fixture.fixture.deployment_path,
                cleanup_receipt_path=unknown,
            )
            self.assertEqual(code, 2, envelope)
            plan = envelope["recovery"]["plan"]
            self.assertEqual(plan["payload"]["status"], "blocked")
            self.assertTrue(plan["payload"]["conflicts"])

    def test_recovery_plan_rejects_projects_outside_the_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            with self.assertRaises(ContractError) as raised:
                plan_recovery(
                    fixture.fixture.manifest_path,
                    apply_receipt_path=fixture.fixture.apply_path,
                    deployment_evidence_path=fixture.fixture.deployment_path,
                    cleanup_receipt_path=fixture.cleanup_path,
                    projects_root=str(fixture.base / "outside"),
                )
            self.assertEqual(raised.exception.exit_code, 2)

    def test_recovery_plan_is_blocked_when_cleanup_evidence_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            plan = fixture.plan(include_cleanup=False)
            self.assertEqual(plan["payload"]["status"], "blocked")
            self.assertTrue(plan["payload"]["conflicts"])
            self.assertEqual(plan["payload"]["steps"], [])


class RecoveryApplyTests(unittest.TestCase):
    def build(self, base: Path) -> RestoredMigration:
        fixture = RestoredMigration(base)
        fixture.save_plan(fixture.plan())
        return fixture

    def test_recovery_requires_the_current_plan_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            before = _tree_bytes(fixture.base)
            with self.assertRaises(ContractError) as raised:
                apply_recovery(fixture.plan_path)
            self.assertEqual(raised.exception.exit_code, 2)
            self.assertEqual(_tree_bytes(fixture.base), before)
            self.assertFalse((fixture.root / ".trellis").exists())

    def test_recovery_restores_the_cleaned_tree_and_saves_a_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            plan = json.loads(fixture.plan_path.read_text())
            envelope, code = apply_recovery(
                fixture.plan_path,
                confirm_recovery=plan["plan_id"],
            )
            self.assertEqual(code, 0, envelope)
            self.assertEqual(envelope["status"], "restored")
            self.assertTrue((fixture.root / ".trellis/.developer").is_file())
            receipt = envelope["recovery"]["receipt"]
            self.assertEqual(receipt["payload"]["status"], "restored")
            self.assertEqual(
                receipt["payload"]["completed_step_ids"],
                sorted(step["step_id"] for step in plan["payload"]["steps"]),
            )
            self.assertEqual(receipt["payload"]["pending_step_ids"], [])
            self.assertEqual(receipt["payload"]["runtime_readiness"], "not-verified")
            receipt_path = fixture.evidence / f"recovery-{receipt['receipt_id']}.json"
            self.assertTrue(receipt_path.is_file())
            protection = receipt["payload"]["results"][0]["protection_ref"]
            self.assertIsNone(protection)

    def test_recovery_refuses_current_drift_without_restoring(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            plan = json.loads(fixture.plan_path.read_text())
            foreign = fixture.root / ".trellis" / "foreign.txt"
            foreign.parent.mkdir()
            foreign.write_text("user-created after cleanup\n")
            before = _tree_bytes(fixture.base)
            with self.assertRaises(ContractError) as raised:
                apply_recovery(
                    fixture.plan_path,
                    confirm_recovery=plan["plan_id"],
                )
            self.assertEqual(raised.exception.exit_code, 2)
            self.assertEqual(_tree_bytes(fixture.base), before)
            self.assertEqual(
                [
                    path
                    for path in fixture.evidence.glob("recovery-*.json")
                    if path.name != "recovery-plan.json"
                ],
                [],
            )

    def test_recovery_retry_resumes_a_failed_step_and_then_already_completes(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            plan = json.loads(fixture.plan_path.read_text())
            refusal = ContractError(
                "state-conflict", "injected restore refusal", exit_code=2
            )
            with mock.patch("sbtd_recovery.install_reference", side_effect=refusal):
                first, first_code = apply_recovery(
                    fixture.plan_path,
                    confirm_recovery=plan["plan_id"],
                )
            self.assertEqual(first_code, 5, first)
            first_receipt = first["recovery"]["receipt"]
            first_path = (
                fixture.evidence / f"recovery-{first_receipt['receipt_id']}.json"
            )
            self.assertTrue(first_path.is_file())
            self.assertFalse((fixture.root / ".trellis").exists())

            second, second_code = apply_recovery(
                fixture.plan_path,
                previous_receipt_path=first_path,
                confirm_recovery=plan["plan_id"],
            )
            self.assertEqual(second_code, 0, second)
            self.assertEqual(second["status"], "restored")
            self.assertTrue((fixture.root / ".trellis").is_dir())
            self.assertEqual(
                second["recovery"]["receipt"]["payload"]["previous_receipt_id"],
                first_receipt["receipt_id"],
            )

            third, third_code = apply_recovery(
                fixture.plan_path,
                previous_receipt_path=(
                    fixture.evidence
                    / f"recovery-{second['recovery']['receipt']['receipt_id']}.json"
                ),
                confirm_recovery=plan["plan_id"],
            )
            self.assertEqual(third_code, 0, third)
            self.assertEqual(third["status"], "already-complete")

    def test_recovery_retry_requires_the_prior_protection_object(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            plan = json.loads(fixture.plan_path.read_text())
            import sbtd_recovery
            from sbtd_migration_files import install_reference as real_install

            def refuse_gitignore_restore(
                source, target, expected, *, scope, backup_ref=None
            ):
                if Path(target).name == ".gitignore":
                    raise ContractError(
                        "write-failed", "injected restore failure", exit_code=5
                    )
                return real_install(
                    source, target, expected, scope=scope, backup_ref=backup_ref
                )

            with mock.patch.object(
                sbtd_recovery, "install_reference", side_effect=refuse_gitignore_restore
            ):
                first, first_code = apply_recovery(
                    fixture.plan_path,
                    confirm_recovery=plan["plan_id"],
                )
            self.assertEqual(first_code, 5, first)
            first_receipt = first["recovery"]["receipt"]
            protection = next(
                result["protection_ref"]
                for result in first_receipt["payload"]["results"]
                if result["protection_ref"] is not None
            )
            Path(protection["path"]).unlink()
            first_path = (
                fixture.evidence / f"recovery-{first_receipt['receipt_id']}.json"
            )
            with self.assertRaises(ContractError) as raised:
                apply_recovery(
                    fixture.plan_path,
                    previous_receipt_path=first_path,
                    confirm_recovery=plan["plan_id"],
                )
            self.assertEqual(raised.exception.exit_code, 3)

    def test_recovery_receipt_save_failure_is_failed_and_honest(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            plan = json.loads(fixture.plan_path.read_text())
            with mock.patch(
                "sbtd_recovery.save_document",
                side_effect=ContractError(
                    "write-failed", "cannot save recovery receipt", exit_code=5
                ),
            ):
                envelope, code = apply_recovery(
                    fixture.plan_path,
                    confirm_recovery=plan["plan_id"],
                )
            self.assertEqual(code, 5, envelope)
            self.assertEqual(envelope["status"], "failed")
            self.assertEqual(
                envelope["reason"], "cumulative evidence persistence failed"
            )
            self.assertEqual(
                [
                    path
                    for path in fixture.evidence.glob("recovery-*.json")
                    if path.name != "recovery-plan.json"
                ],
                [],
            )

    def test_recovery_requires_the_plan_beside_the_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            plan = json.loads(fixture.plan_path.read_text())
            other = fixture.base / "other"
            other.mkdir(mode=0o700)
            other_plan = other / "recovery-plan.json"
            save_document(other_plan, plan, private_root=other)
            before = _tree_bytes(fixture.base)
            with self.assertRaises(ContractError) as raised:
                apply_recovery(other_plan, confirm_recovery=plan["plan_id"])
            self.assertEqual(raised.exception.exit_code, 2)
            self.assertEqual(_tree_bytes(fixture.base), before)


class RecoveryCliTests(unittest.TestCase):
    def test_run_recovery_dispatches_the_apply_phase(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            envelope = {
                "mode": "recovery",
                "phase": "apply",
                "status": "blocked",
                "manifest_id": "0" * 64,
                "plan_id": "1" * 64,
                "receipt_id": None,
                "projects": [],
                "reason": "confirmation required",
                "nextStep": "Confirm the current plan_id.",
                "recovery": {},
            }
            args = SimpleNamespace(
                phase="apply",
                plan=str(base / "plan.json"),
                recovery_receipt=None,
                confirm_recovery="1" * 64,
                json=False,
            )
            with mock.patch(
                "sbtd_recovery.apply_recovery", return_value=(envelope, 2)
            ) as apply:
                code = run_recovery(args)
            self.assertEqual(code, 2)
            apply.assert_called_once_with(
                base / "plan.json",
                previous_receipt_path=None,
                confirm_recovery="1" * 64,
            )

    def test_run_recovery_validates_the_rejection_json_envelope(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            args = SimpleNamespace(
                phase="plan",
                manifest=str(base / "manifest.json"),
                apply_receipt=None,
                deployment_evidence=None,
                cleanup_receipt=None,
                projects_root=None,
                json=True,
            )
            output = io.StringIO()
            with (
                mock.patch(
                    "sbtd_recovery.plan_recovery",
                    side_effect=ContractError(
                        "original-unavailable", "bound evidence missing", exit_code=3
                    ),
                ),
                redirect_stdout(output),
            ):
                code = run_recovery(args)
            self.assertEqual(code, 3)
            response = json.loads(output.getvalue())
            self.assertEqual(response["phase"], "plan")
            self.assertEqual(response["status"], "failed")
            self.assertEqual(response["recovery"], {})
            self.assertEqual(list(base.iterdir()), [])

    def test_run_recovery_dispatches_the_plan_phase(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            envelope = {
                "mode": "recovery",
                "phase": "plan",
                "status": "blocked",
                "manifest_id": "0" * 64,
                "plan_id": None,
                "receipt_id": None,
                "projects": [],
                "reason": "closure missing",
                "nextStep": "Select the full shared dependency closure.",
                "recovery": {},
            }
            args = SimpleNamespace(
                phase="plan",
                manifest=str(base / "manifest.json"),
                apply_receipt=None,
                deployment_evidence=None,
                cleanup_receipt=None,
                projects_root=None,
                json=True,
            )
            output = io.StringIO()
            with (
                mock.patch(
                    "sbtd_recovery.plan_recovery", return_value=(envelope, 2)
                ) as plan,
                redirect_stdout(output),
            ):
                code = run_recovery(args)
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(output.getvalue())["phase"], "plan")
            plan.assert_called_once_with(
                base / "manifest.json",
                apply_receipt_path=None,
                deployment_evidence_path=None,
                cleanup_receipt_path=None,
                projects_root=None,
            )


if __name__ == "__main__":
    unittest.main()
