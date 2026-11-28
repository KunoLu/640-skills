from __future__ import annotations

import copy
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from contextlib import nullcontext, redirect_stdout
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
from sbtd_migration_files import save_document, snapshot
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
            retained = fixture.root / ".gitignore"
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


    def test_shared_skill_recovery_requires_full_dependent_closure(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = VerifiedMigration(base, names=("one", "two"))
            skill = fixture.home / ".agent/skills/trellis-workflow"
            (skill / "SKILL.md").parent.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: trellis-workflow\n---\n# another 1.0.x release\n"
            )
            fixture.build()
            cleaned, code = fixture.cleanup(
                confirm_cleanup=fixture.verification["verification_id"]
            )
            self.assertEqual(code, 0, cleaned)
            cleanup = fixture.evidence / (
                f"cleanup-{cleaned['migration']['cleanup_receipt']['cleanup_id']}.json"
            )
            before = _tree_bytes(base)
            blocked, blocked_code = plan_recovery(
                fixture.manifest_path,
                apply_receipt_path=fixture.apply_path,
                deployment_evidence_path=fixture.deployment_path,
                cleanup_receipt_path=cleanup,
                projects_root=str(fixture.roots[0]),
            )
            self.assertEqual(blocked_code, 2, blocked)
            self.assertEqual(blocked["recovery"]["plan"]["payload"]["steps"], [])
            self.assertEqual(_tree_bytes(base), before)
            planned, planned_code = plan_recovery(
                fixture.manifest_path,
                apply_receipt_path=fixture.apply_path,
                deployment_evidence_path=fixture.deployment_path,
                cleanup_receipt_path=cleanup,
            )
            resources = planned["recovery"]["plan"]["payload"]["resources"]
            shared = next(resource for resource in resources if resource["target"] == str(skill))
            self.assertEqual(shared["dependent_projects"], sorted(map(str, fixture.roots)))
            self.assertEqual(
                len(
                    [
                        step
                        for step in planned["recovery"]["plan"]["payload"]["steps"]
                        if step["resource_id"] == shared["resource_id"]
                    ]
                ),
                1,
            )

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


    def test_same_resource_keeps_only_the_latest_succeeded_inverse_step(self):
        from sbtd_recovery import _latest_succeeded_step_ids

        steps = [
            {"step_id": "cleanup-step", "resource_id": "same"},
            {"step_id": "deploy-step", "resource_id": "same"},
            {"step_id": "apply-step", "resource_id": "same"},
            {"step_id": "other-step", "resource_id": "other"},
        ]
        previous = {
            "cleanup-step": {"status": "succeeded", "after": {"type": "file"}},
            "deploy-step": {"status": "succeeded", "after": {"type": "absent"}},
            "apply-step": {"status": "failed", "after": {"type": "absent"}},
            "other-step": {"status": "succeeded", "after": {"type": "file"}},
        }
        self.assertEqual(
            _latest_succeeded_step_ids(steps, previous),
            {"deploy-step", "other-step"},
        )

    def test_multi_phase_retry_checks_only_the_latest_restored_state(self):
        from onboard_contracts import (
            operation_id,
            recovery_step_id,
            resource_id,
            seal_document,
        )
        from sbtd_migration_files import snapshot

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            evidence = base / "evidence"
            evidence.mkdir(mode=0o700)
            project = base / "project"
            project.mkdir()
            target = base / "live.txt"
            target.write_bytes(b"pre-apply\n")
            applied_backup = evidence / "backup-applied.txt"
            applied_backup.write_bytes(b"post-apply\n")
            original_backup = evidence / "backup-original.txt"
            original_backup.write_bytes(b"pre-apply\n")
            manifest_path = evidence / "manifest.json"
            apply_path = evidence / "apply.json"
            cleanup_path = evidence / "cleanup.json"
            for path in (manifest_path, apply_path, cleanup_path):
                path.write_bytes(b"{}\n")
            rid = resource_id("file", str(target))
            manifest_id = "ab" * 32
            cleanup_step = recovery_step_id(manifest_id, "cleanup", rid)
            apply_step = recovery_step_id(manifest_id, "apply", rid)
            cleanup_op = operation_id("cleanup", rid, "whole-resource")
            apply_op = operation_id("apply", rid, "name")
            applied = snapshot(applied_backup)
            original = snapshot(target)
            evidence_ref = {
                "manifest": {
                    "path": str(manifest_path),
                    "state": snapshot(manifest_path),
                },
                "apply_receipt": {
                    "path": str(apply_path),
                    "state": snapshot(apply_path),
                },
                "deployment_evidence": None,
                "cleanup_receipt": {
                    "path": str(cleanup_path),
                    "state": snapshot(cleanup_path),
                },
            }
            plan = seal_document(
                "recovery_plan",
                {
                    "manifest_id": manifest_id,
                    "status": "planned",
                    "projects": [
                        {"root": str(project), "source_ref": None, "head": None}
                    ],
                    "shared_operation_ids": [],
                    "input_evidence": evidence_ref,
                    "resources": [
                        {
                            "resource_id": rid,
                            "owner_kind": "file",
                            "target": str(target),
                            "operation_ids": sorted([cleanup_op, apply_op]),
                            "dependent_projects": [str(project)],
                            "state": {"type": "absent", "checksum": None},
                        }
                    ],
                    "steps": [
                        {
                            "step_id": cleanup_step,
                            "phase": "cleanup",
                            "resource_id": rid,
                            "operation_ids": [cleanup_op],
                            "dependent_projects": [str(project)],
                            "depends_on": [],
                            "backup_ref": {
                                "path": str(applied_backup),
                                "state": applied,
                            },
                            "expected_current": {"type": "absent", "checksum": None},
                            "restore_to": applied,
                        },
                        {
                            "step_id": apply_step,
                            "phase": "apply",
                            "resource_id": rid,
                            "operation_ids": [apply_op],
                            "dependent_projects": [str(project)],
                            "depends_on": [cleanup_step],
                            "backup_ref": {
                                "path": str(original_backup),
                                "state": original,
                            },
                            "expected_current": applied,
                            "restore_to": original,
                        },
                    ],
                    "conflicts": [],
                    "risks": [],
                    "target": "pre-apply",
                    "created_at": "2026-09-27T07:00:00+00:00",
                },
            )
            receipt = seal_document(
                "recovery_receipt",
                {
                    "plan_id": plan["plan_id"],
                    "manifest_id": manifest_id,
                    "previous_receipt_id": None,
                    "input_evidence": evidence_ref,
                    "status": "restored",
                    "projects": [
                        {
                            "root": str(project),
                            "source_ref": None,
                            "head": None,
                            "status": "restored",
                            "reason": "",
                            "nextStep": "",
                        }
                    ],
                    "results": [
                        {
                            "step_id": cleanup_step,
                            "resource_id": rid,
                            "phase": "cleanup",
                            "operation_ids": [cleanup_op],
                            "dependent_projects": [str(project)],
                            "status": "succeeded",
                            "protection_ref": None,
                            "before": {"type": "absent", "checksum": None},
                            "after": applied,
                            "error": None,
                        },
                        {
                            "step_id": apply_step,
                            "resource_id": rid,
                            "phase": "apply",
                            "operation_ids": [apply_op],
                            "dependent_projects": [str(project)],
                            "status": "succeeded",
                            "protection_ref": {
                                "path": str(applied_backup),
                                "state": applied,
                            },
                            "before": applied,
                            "after": original,
                            "error": None,
                        },
                    ],
                    "shared_results": [],
                    "completed_step_ids": sorted([cleanup_step, apply_step]),
                    "pending_step_ids": [],
                    "reason": "",
                    "started_at": "2026-09-27T07:01:00+00:00",
                    "finished_at": "2026-09-27T07:02:00+00:00",
                    "runtime_readiness": "not-verified",
                    "report_refs": [],
                },
            )
            plan_path = evidence / "recovery-plan.json"
            receipt_path = evidence / f"recovery-{receipt['receipt_id']}.json"
            save_document(plan_path, plan, private_root=evidence)
            save_document(receipt_path, receipt, private_root=evidence)
            loaded_manifest = {
                "manifest_id": manifest_id,
                "payload": {
                    "backup_root": str(evidence),
                    "projects": [
                        {
                            "sources": [],
                            "private_operations": [
                                {"resource_id": rid, "target": str(target)}
                            ],
                        }
                    ],
                    "shared_operations": [],
                },
            }

            def load_reference(reference, kind):
                if kind == "manifest":
                    return loaded_manifest, b"{}\n"
                return {
                    "payload": {"projects": [], "shared_results": []}
                }, b"{}\n"

            before = target.read_bytes()
            with (
                mock.patch(
                    "sbtd_recovery._document_from_reference",
                    side_effect=load_reference,
                ),
                mock.patch("sbtd_recovery.contracts.validate_declared_bindings"),
                mock.patch("sbtd_recovery._validate_context"),
                mock.patch("sbtd_recovery.contracts.validate_cumulative"),
            ):
                continued, code = apply_recovery(
                    plan_path,
                    previous_receipt_path=receipt_path,
                    confirm_recovery=plan["plan_id"],
                )
            self.assertEqual(code, 0, continued)
            self.assertEqual(continued["status"], "already-complete")
            self.assertEqual(target.read_bytes(), before)
            self.assertNotEqual(snapshot(target), applied)

    def test_bound_multi_phase_continuation_uses_real_recovery_gates(self):
        self._assert_bound_multi_phase_continuation(predecessor=False)

    def test_predecessor_deployment_recovery_uses_latest_bound_stage(self):
        self._assert_bound_multi_phase_continuation(predecessor=True)

    def test_predecessor_failed_deployment_recovers_known_writes_not_retries(self):
        self._assert_bound_multi_phase_continuation(
            predecessor=True, failed_deploy=True
        )

    def test_sealed_graft_deploy_is_rejected_before_recovery_write(self):
        from tests.test_sbtd_migration_rc3_graft import build_completed_historical

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            old = build_completed_historical(base)
            before = snapshot(base)
            with self.assertRaises(ContractError) as raised:
                plan_recovery(
                    old["manifest_path"], apply_receipt_path=old["apply_path"],
                    deployment_evidence_path=old["deployment_path"],
                )
            self.assertEqual(raised.exception.code, "unsupported-in-rc.3")
            self.assertEqual(snapshot(base), before)

    def _install_lineage_fixture(self, base, predecessor, successor):
        import base64

        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        key = Ed25519PrivateKey.generate()
        public = base / "lineage.pub"
        public.write_bytes(
            key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        )
        pair = {
            "schema_version": 1,
            "purpose": "runtime-lineage",
            "predecessor": predecessor,
            "successor": successor,
        }
        signed = json.dumps(pair, sort_keys=True, separators=(",", ":")).encode()
        pair["signature"] = base64.b64encode(key.sign(signed)).decode()
        document = base / "lineage.json"
        document.write_text(json.dumps(pair))
        for name, path in (
            ("_LINEAGE_PUBLIC_KEY", public),
            ("_LINEAGE_DOCUMENT", document),
        ):
            patch = mock.patch(f"sbtd_migration.{name}", path)
            patch.start()
            self.addCleanup(patch.stop)

    def _assert_bound_multi_phase_continuation(
        self, *, predecessor: bool, failed_deploy: bool = False
    ):
        import test_sbtd_migration_plan as routing_tests
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from onboard_contracts import canonical_json_bytes
        from sbtd_deployment import execute_migration_deployment, load_deployment_context
        from sbtd_migration import apply_migration, runtime_versions
        from sbtd_migration_files import snapshot, write_file
        from sbtd_migration_plan import plan_migration
        from test_sbtd_migration_apply import legacy_project
        from test_sbtd_migration_plan import _routing_approval

        producer = runtime_versions()
        key = Ed25519PrivateKey.generate()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = legacy_project(base, "project")
            home, vault, evidence = (base / name for name in ("home", "vault", "evidence"))
            for path in (home, vault, evidence):
                path.mkdir(mode=0o700)
            environment = {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "CODEX_HOME": str(home / ".codex"),
                "AGENT_SKILLS_DIR": str(home / ".agent/skills"),
                "PI_CONFIG_DIR": ".omp",
                "PI_CODING_AGENT_DIR": "",
                "OMP_PROFILE": "default",
                "PI_PROFILE": "default",
            }
            live = project / "AGENTS.md"
            if os.name == "posix":
                live.chmod(0o640)
            original_state = snapshot(live)
            original = live.read_bytes()
            original_mode = stat.S_IMODE(live.stat().st_mode)
            pause = (SCRIPTS.parent / "assets/migration-paused-agents.txt").read_bytes()
            body = b"approved replacement\n"
            paused = pause + b"\n" + body
            candidate = vault / "routing-candidate.md"
            candidate.write_bytes(paused)
            if os.name == "posix":
                candidate.chmod(0o600)
            paused_state = snapshot(candidate)
            paused_mode = stat.S_IMODE(candidate.stat().st_mode)
            approval = vault / "routing-approvals.json"
            with (
                mock.patch.dict(os.environ, environment),
                mock.patch(
                    "sbtd_migration_plan._routing_approval_public_key",
                    return_value=key.public_key(),
                ),
            ):
                with mock.patch.object(routing_tests, "_TEST_APPROVAL_KEY", key):
                    _routing_approval(approval, "demo-project", live, candidate)
                manifest = plan_migration(
                    [project],
                    vault,
                    "fixture",
                    None,
                    tool_versions=producer,
                    deployment_mode="init-projects",
                    routing_approvals=approval,
                )
                routing = {
                    operation["phase"]: operation
                    for operation in manifest["payload"]["projects"][0]["private_operations"]
                    if operation["target"] == str(live)
                }
                self.assertEqual(set(routing), {"apply", "deploy"})
                resource = routing["apply"]["resource_id"]
                self.assertEqual(routing["deploy"]["resource_id"], resource)
                self.assertEqual(
                    routing["deploy"]["before_requirement"],
                    {"kind": "phase-after", "phase": "apply", "resource_id": resource},
                )
                self.assertEqual(manifest["payload"]["shared_operations"], [])
                manifest_path = evidence / "manifest.json"
                manifest_path.write_bytes(canonical_json_bytes(manifest))
                applied, apply_code = apply_migration(
                    manifest_path, confirmed=True, routing_approvals=approval
                )
                self.assertEqual(apply_code, 0, applied)
                self.assertEqual(live.read_bytes(), paused)
                self.assertEqual(stat.S_IMODE(live.stat().st_mode), paused_mode)
                receipt = applied["migration"]["apply_receipt"]
                apply_row = next(
                    result for result in receipt["payload"]["projects"][0]["private_results"]
                    if result["resource_id"] == resource
                )
                apply_backup = Path(apply_row["backup_ref"]["path"])
                self.assertEqual(apply_backup.read_bytes(), original)
                self.assertEqual(stat.S_IMODE(apply_backup.stat().st_mode), original_mode)
                apply_path = evidence / f"apply-{receipt['apply_id']}.json"
                deployment_path = evidence / "deployment.json"
                context_arguments = {
                    "mode": "init-projects", "roots": [project], "hooks_authorized": False,
                }
                context = load_deployment_context(
                    manifest_path, apply_path, deployment_path,
                    previous_path=None, **context_arguments,
                )

                def fail_after_route_write(target, *args, **kwargs):
                    write_file(target, *args, **kwargs)
                    if target == live:
                        raise OSError("injected failure after the route was written")

                fault = (
                    mock.patch("sbtd_deployment.write_file", side_effect=fail_after_route_write)
                    if failed_deploy
                    else nullcontext()
                )
                with fault:
                    deployed, deploy_code = execute_migration_deployment(context)
                expected = (5, "failed") if failed_deploy else (0, "succeeded")
                self.assertEqual((deploy_code, deployed["status"]), expected, deployed)
                self.assertEqual(bool(deployed["projects"][0]["report_refs"]), not failed_deploy)
                self.assertTrue(deployment_path.is_file())
                self.assertEqual(live.read_bytes(), body)
                self.assertEqual(stat.S_IMODE(live.stat().st_mode), paused_mode)
                self.assertEqual(list(home.iterdir()), [])
                deployed_state = snapshot(live)
                stage = deployed["deploymentEvidence"]["evidence"]
                row = stage["payload"]["projects"][0]["private_results"][0]
                self.assertEqual(row["resource_id"], resource)
                self.assertEqual(row["before"], paused_state)
                self.assertEqual(row["after"], deployed_state)
                backup = Path(row["backup_ref"]["path"])
                self.assertEqual(backup.read_bytes(), paused)
                self.assertEqual(stat.S_IMODE(backup.stat().st_mode), paused_mode)

                # Real deployment and smoke run under the producer. Change
                # only the recovery consumer's identity for the lineage hop.
                consumer = nullcontext()
                if predecessor:
                    successor = {**producer, "onboard": "runtime-sha256:" + "a" * 64}
                    self._install_lineage_fixture(base, producer["onboard"], successor["onboard"])
                    consumer = mock.patch("sbtd_migration.runtime_versions", return_value=successor)
                recovery_arguments = {
                    "apply_receipt_path": apply_path, "deployment_evidence_path": deployment_path,
                }
                with consumer:
                    if predecessor:
                        with self.assertRaises(ContractError) as missing_stage:
                            plan_recovery(manifest_path, apply_receipt_path=apply_path)
                        self.assertEqual(missing_stage.exception.code, "lineage-conflict")
                        drifted = b"operator changed this route\n"
                        live.write_bytes(drifted)
                        with self.assertRaises(ContractError) as drift:
                            plan_recovery(manifest_path, **recovery_arguments)
                        self.assertEqual(drift.exception.code, "lineage-conflict")
                        self.assertEqual(live.read_bytes(), drifted)
                        live.write_bytes(body)
                        retry_arguments = {
                            **context_arguments, "previous_path": deployment_path,
                        }
                        retry_path = evidence / "deployment-retry.json"
                        if failed_deploy:
                            self.assertEqual(row["status"], "failed")
                            with self.assertRaises(ContractError) as partial_retry:
                                load_deployment_context(
                                    manifest_path, apply_path, retry_path, **retry_arguments
                                )
                            self.assertEqual(partial_retry.exception.code, "state-conflict")
                            backup.write_bytes(b"damaged retained original\n")
                            with self.assertRaises(ContractError) as damaged:
                                plan_recovery(manifest_path, **recovery_arguments)
                            self.assertEqual(damaged.exception.code, "original-unavailable")
                            self.assertEqual(live.read_bytes(), body)
                            backup.write_bytes(paused)
                            for defect in ("missing-backup", "unknown-after", "wrong-apply"):
                                with self.subTest(defect=defect):
                                    invalid = copy.deepcopy(stage["payload"])
                                    invalid_row = invalid["projects"][0]["private_results"][0]
                                    if defect == "missing-backup":
                                        invalid_row["backup_ref"] = None
                                    elif defect == "unknown-after":
                                        invalid_row["after"] = None
                                    else:
                                        invalid["apply_id"] = "0" * 64
                                    invalid_path = evidence / f"{defect}.json"
                                    save_document(
                                        invalid_path,
                                        seal_document("deployment_evidence", invalid),
                                        private_root=evidence,
                                    )
                                    arguments = {
                                        **recovery_arguments,
                                        "deployment_evidence_path": invalid_path,
                                    }
                                    if defect == "missing-backup":
                                        blocked, code = plan_recovery(manifest_path, **arguments)
                                        self.assertEqual((code, blocked["status"]), (2, "blocked"))
                                    else:
                                        with self.assertRaises(ContractError):
                                            plan_recovery(manifest_path, **arguments)
                                    self.assertEqual(live.read_bytes(), body)
                        else:
                            retry = load_deployment_context(
                                manifest_path, apply_path, retry_path, **retry_arguments
                            )
                            self.assertEqual(retry.expected_before[resource], deployed_state)
                        self.assertFalse(retry_path.exists())

                    planned, plan_code = plan_recovery(manifest_path, **recovery_arguments)
                    self.assertEqual(plan_code, 0, planned)
                    plan = planned["recovery"]["plan"]
                    paired = [
                        step for step in plan["payload"]["steps"]
                        if step["resource_id"] == resource
                    ]
                    self.assertEqual([step["phase"] for step in paired], ["deploy", "apply"])
                    self.assertEqual(paired[0]["restore_to"], paused_state)
                    self.assertEqual(paired[1]["restore_to"], original_state)
                    self.assertEqual(paired[1]["depends_on"], [paired[0]["step_id"]])
                    plan_path = evidence / "recovery-plan.json"
                    save_document(plan_path, plan, private_root=evidence)
                    restored, recovery_code = apply_recovery(
                        plan_path, confirm_recovery=plan["plan_id"]
                    )
                    self.assertEqual(recovery_code, 0, restored)
                    first = restored["recovery"]["receipt"]
                    first_path = evidence / f"recovery-{first['receipt_id']}.json"
                    succeeded = [
                        result for result in first["payload"]["results"]
                        if result["resource_id"] == resource
                    ]
                    self.assertEqual(
                        [(row["phase"], row["status"], row["after"]) for row in succeeded],
                        [("deploy", "succeeded", paused_state), ("apply", "succeeded", original_state)],
                    )
                    self.assertEqual(live.read_bytes(), original)
                    self.assertEqual(stat.S_IMODE(live.stat().st_mode), original_mode)
                    continued, continued_code = apply_recovery(
                        plan_path,
                        previous_receipt_path=first_path,
                        confirm_recovery=plan["plan_id"],
                    )
                    self.assertEqual(continued_code, 0, continued)
                    self.assertEqual(continued["status"], "already-complete")
                    self.assertEqual(live.read_bytes(), original)
                    self.assertEqual(stat.S_IMODE(live.stat().st_mode), original_mode)


    def test_predecessor_recovery_can_continue_from_a_partial_receipt(self):
        from onboard_contracts import canonical_json_bytes
        from sbtd_migration import apply_migration, runtime_versions
        from sbtd_migration_files import snapshot
        from sbtd_migration_plan import plan_migration
        from test_sbtd_migration_apply import legacy_project

        predecessor = "runtime-sha256:" + "a" * 64
        current = runtime_versions()
        sealed = {"onboard": predecessor}
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            self._install_lineage_fixture(base, predecessor, current["onboard"])
            project = legacy_project(base, "project")
            home, vault, evidence = (base / name for name in ("home", "vault", "evidence"))
            for path in (home, vault, evidence):
                path.mkdir(mode=0o700)
            environment = {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "CODEX_HOME": str(home / ".codex"),
                "AGENT_SKILLS_DIR": str(home / ".agent/skills"),
            }
            with mock.patch.dict(os.environ, environment):
                manifest = plan_migration(
                    [project],
                    vault,
                    "fixture",
                    None,
                    tool_versions=sealed,
                )
            manifest_path = evidence / "manifest.json"
            manifest_path.write_bytes(canonical_json_bytes(manifest))
            with mock.patch.dict(os.environ, environment), mock.patch(
                "sbtd_migration.runtime_versions", return_value=sealed
            ):
                applied, apply_code = apply_migration(
                    manifest_path, confirmed=True, no_routing_approvals=True
                )
            self.assertEqual(apply_code, 0, applied)
            receipt = applied["migration"]["apply_receipt"]
            apply_path = evidence / f"apply-{receipt['apply_id']}.json"
            self.assertTrue(apply_path.is_file())
            planned, plan_code = plan_recovery(
                manifest_path, apply_receipt_path=apply_path
            )
            self.assertEqual(plan_code, 0, planned)
            plan = planned["recovery"]["plan"]
            steps = plan["payload"]["steps"]
            self.assertGreaterEqual(len(steps), 2)
            plan_path = evidence / "recovery-plan.json"
            save_document(plan_path, plan, private_root=evidence)
            import sbtd_recovery

            real_execute = sbtd_recovery._execute_step

            def stop_after_first(manifest_doc, operation, path, step):
                if stop_after_first.calls:
                    current = snapshot(Path(operation["target"]))
                    return {
                        "step_id": step["step_id"],
                        "resource_id": step["resource_id"],
                        "phase": step["phase"],
                        "operation_ids": list(step["operation_ids"]),
                        "dependent_projects": list(step["dependent_projects"]),
                        "status": "failed",
                        "protection_ref": None,
                        "before": current,
                        "after": current,
                        "error": "state-conflict",
                    }
                stop_after_first.calls += 1
                return real_execute(manifest_doc, operation, path, step)

            stop_after_first.calls = 0
            with mock.patch.object(
                sbtd_recovery, "_execute_step", side_effect=stop_after_first
            ):
                first, first_code = apply_recovery(
                    plan_path, confirm_recovery=plan["plan_id"]
                )
            self.assertEqual(first_code, 5, first)
            first_receipt = first["recovery"]["receipt"]
            succeeded = [
                result
                for result in first_receipt["payload"]["results"]
                if result["status"] == "succeeded"
            ]
            self.assertEqual(len(succeeded), 1)
            operations = [
                operation
                for project in manifest["payload"]["projects"]
                for operation in project["private_operations"]
            ] + list(manifest["payload"]["shared_operations"])
            restored_target = Path(
                next(
                    operation["target"]
                    for operation in operations
                    if operation["resource_id"] == succeeded[0]["resource_id"]
                )
            )
            self.assertEqual(snapshot(restored_target), succeeded[0]["after"])
            self.assertNotEqual(snapshot(restored_target), succeeded[0]["before"])
            first_path = evidence / f"recovery-{first_receipt['receipt_id']}.json"
            before_continue = _tree_bytes(base)
            unlisted = {"onboard": "runtime-sha256:unlisted-successor"}
            with (
                mock.patch("sbtd_migration.runtime_versions", return_value=unlisted),
                self.assertRaises(ContractError) as rejected,
            ):
                apply_recovery(
                    plan_path,
                    previous_receipt_path=first_path,
                    confirm_recovery=plan["plan_id"],
                )
            self.assertEqual(rejected.exception.code, "version-conflict")
            self.assertEqual(_tree_bytes(base), before_continue)
            official = (base / "lineage.json").read_bytes()
            outside = Path(tempfile.mkdtemp(dir=str(base.parent)))
            tampered = outside / "bad-lineage.json"
            payload = json.loads(official)
            payload["signature"] = "A" * len(payload["signature"])
            tampered.write_text(json.dumps(payload), encoding="utf-8")
            with (
                mock.patch("sbtd_migration._LINEAGE_DOCUMENT", tampered),
                self.assertRaises(ContractError) as bad_signature,
            ):
                apply_recovery(
                    plan_path,
                    previous_receipt_path=first_path,
                    confirm_recovery=plan["plan_id"],
                )
            self.assertEqual(bad_signature.exception.code, "version-conflict")
            self.assertEqual(_tree_bytes(base), before_continue)
            continued, continued_code = apply_recovery(
                plan_path,
                previous_receipt_path=first_path,
                confirm_recovery=plan["plan_id"],
            )
            self.assertEqual(continued_code, 0, continued)
            self.assertEqual(continued["status"], "restored")
            self.assertEqual(
                continued["recovery"]["receipt"]["payload"]["pending_step_ids"],
                [],
            )
            self.assertEqual(snapshot(restored_target), succeeded[0]["after"])




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
