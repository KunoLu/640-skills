from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard" / "scripts"
TESTS = Path(__file__).resolve().parent
for import_path in (str(SCRIPTS), str(TESTS)):
    if import_path not in sys.path:
        sys.path.insert(0, import_path)


from onboard_contracts import ContractError, canonical_json_bytes, seal_document
from sbtd_migration import apply_migration, run_migration, runtime_versions
from sbtd_migration_files import save_document
from sbtd_migration_plan import plan_migration
from sbtd_migration_verify import verify_migration
from test_sbtd_migration_verify import _file_ref, _legacy_project, _tree_bytes


class VerifiedMigration:
    def __init__(self, base: Path, names: tuple[str, ...] = ("project",)) -> None:
        self.base = base
        self.roots = [_legacy_project(base, name) for name in names]
        self.root = self.roots[0]
        self.home = base / "home"
        self.vault = base / "vault"
        self.evidence = base / "evidence"
        for path in (self.home, self.vault, self.evidence):
            path.mkdir(mode=0o700)
        self.environment = {
            "HOME": str(self.home),
            "USERPROFILE": str(self.home),
            "CODEX_HOME": str(self.home / ".codex"),
            "AGENT_SKILLS_DIR": str(self.home / ".agent/skills"),
        }
        self.manifest: dict[str, Any] = {}
        self.manifest_path = self.evidence / "manifest.json"
        self.apply_path = self.evidence / "apply.json"
        self.deployment_path = self.evidence / "deployment.json"
        self.verification_path = self.evidence / "verification.json"
        self.verification: dict[str, Any] = {}

    def build(self) -> None:
        with mock.patch.dict(os.environ, self.environment):
            self.manifest = plan_migration(
                list(self.roots),
                self.vault,
                "fixture-custodian",
                None,
                tool_versions=runtime_versions(),
            )
            self.manifest_path.write_bytes(canonical_json_bytes(self.manifest))
            applied, apply_code = apply_migration(self.manifest_path, confirmed=True)
            if apply_code != 0:
                raise AssertionError(f"apply failed: {applied}")
            apply_receipt = applied["migration"]["apply_receipt"]
            self.apply_path = next(
                path
                for path in self.evidence.glob("*.json")
                if json.loads(path.read_text()).get("apply_id")
                == apply_receipt["apply_id"]
            )

            moment = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            report_refs = {}
            for index, root in enumerate(self.roots):
                report_path = self.evidence / f"smoke-{index}.json"
                summary = self.evidence / f"smoke-{index}.md"
                summary.write_text("合成 cleanup 夹具；不证明真实 host 部署。\n")
                raw = {
                    "repositoryKey": "fixture/project",
                    "projectRoot": str(root),
                    "sourceRef": "non-git",
                    "sourceCommit": None,
                    "worktreeState": "unknown",
                    "sourceRevision": "unknown",
                    "evidenceSource": "developer-local",
                    "trigger": "manual",
                    "environmentAlignment": "verified",
                    "evidencePublication": "local-only",
                    "e2eMode": "smoke-only",
                    "mockStrategy": "none",
                    "startedAt": moment,
                    "finishedAt": moment,
                    "command": ["fixture"],
                    "stdout": "synthetic contract data",
                    "stderr": "",
                    "exitCode": 0,
                    "timedOut": False,
                }
                report_path.write_text(json.dumps(raw))
                report = {
                    "testType": "api",
                    "path": str(report_path),
                    "summaryMd": str(summary),
                    "sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
                    "status": "passed",
                    "mode": "smoke-only",
                }
                envelope = {
                    "schemaVersion": 1,
                    "runId": f"fixture-smoke-{index}",
                    "createdAt": moment,
                    "evidenceSource": "developer-local",
                    "trigger": "manual",
                    "repository": {
                        "repositoryKey": "fixture/project",
                        "sourceRef": "non-git",
                        "sourceCommit": None,
                        "worktreeState": "unknown",
                    },
                    "sourceRevision": "unknown",
                    "environmentAlignment": "verified",
                    "e2eMode": "smoke-only",
                    "mockStrategy": "none",
                    "featureSources": [],
                    "reports": [report],
                    "evidencePublication": "local-only",
                    "secretsRedacted": True,
                }
                evidence_path = self.evidence / f"smoke-{index}.evidence.json"
                evidence_path.write_text(json.dumps(envelope))
                report_refs[root] = [
                    _file_ref(evidence_path),
                    _file_ref(report_path),
                    _file_ref(summary),
                ]
            deployment = seal_document(
                "deployment_evidence",
                {
                    "manifest_id": self.manifest["manifest_id"],
                    "apply_id": apply_receipt["apply_id"],
                    "previous_deployment_id": None,
                    "status": "succeeded",
                    "projects": [
                        {
                            "root": str(root),
                            "source_ref": None,
                            "head": None,
                            "status": "succeeded",
                            "reason": "",
                            "nextStep": "",
                            "private_results": [],
                            "shared_operation_ids": [],
                            "report_refs": report_refs[root],
                        }
                        for root in self.roots
                    ],
                    "shared_results": [],
                    "started_at": moment,
                    "finished_at": moment,
                },
            )
            save_document(
                self.deployment_path,
                deployment,
                private_root=self.evidence,
            )
            verified, verify_code = verify_migration(
                self.manifest_path,
                self.apply_path,
                self.deployment_path,
            )
            if verify_code != 0:
                raise AssertionError(f"verify failed: {verified}")
            self.verification = verified["migration"]["verification"]
            save_document(
                self.verification_path,
                self.verification,
                private_root=self.evidence,
            )

    def cleanup(self, **kwargs: Any) -> tuple[dict[str, Any], int]:
        from sbtd_migration import cleanup_migration

        return cleanup_migration(
            self.manifest_path,
            self.apply_path,
            self.deployment_path,
            self.verification_path,
            **kwargs,
        )


class CleanupMigrationTests(unittest.TestCase):
    def build(self, base: Path) -> VerifiedMigration:
        fixture = VerifiedMigration(base)
        fixture.build()
        return fixture

    def test_cleanup_requires_the_current_verification_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            before = _tree_bytes(fixture.base)
            with self.assertRaises(ContractError) as raised:
                fixture.cleanup()
            self.assertEqual(raised.exception.exit_code, 2)
            self.assertEqual(_tree_bytes(fixture.base), before)
            self.assertTrue((fixture.root / ".trellis").is_dir())

    def test_cleanup_rejects_a_stale_verification_id_without_deleting(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            with self.assertRaises(ContractError):
                fixture.cleanup(confirm_cleanup="0" * 64)
            self.assertTrue((fixture.root / ".trellis").is_dir())
            self.assertEqual(list(fixture.evidence.glob("cleanup-*.json")), [])

    def test_cleanup_removes_the_verified_legacy_tree_and_saves_a_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            envelope, code = fixture.cleanup(
                confirm_cleanup=fixture.verification["verification_id"]
            )
            self.assertEqual(code, 0, envelope)
            self.assertEqual(envelope["status"], "cleaned")
            self.assertFalse((fixture.root / ".trellis").exists())
            receipt = envelope["migration"]["cleanup_receipt"]
            self.assertEqual(receipt["payload"]["status"], "cleaned")
            self.assertEqual(
                receipt["payload"]["verification_id"],
                fixture.verification["verification_id"],
            )
            self.assertIsNone(receipt["payload"]["previous_receipt_id"])
            project = receipt["payload"]["projects"][0]
            self.assertEqual(project["status"], "cleaned")
            self.assertEqual(len(project["private_results"]), 1)
            result = project["private_results"][0]
            self.assertEqual(result["phase"], "cleanup")
            self.assertEqual(result["after"], {"type": "absent", "checksum": None})
            backup = result["backup_ref"]
            self.assertIsNotNone(backup)
            self.assertTrue(Path(backup["path"]).exists())
            receipt_path = fixture.evidence / f"cleanup-{receipt['cleanup_id']}.json"
            self.assertTrue(receipt_path.is_file())

    def test_a_candidate_changed_after_verification_is_blocked_without_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            changed = fixture.root / ".trellis/workspace/dev01/new-user-file.txt"
            changed.write_text("user data after verification\n")
            before = _tree_bytes(fixture.base)
            with self.assertRaises(ContractError):
                fixture.cleanup(confirm_cleanup=fixture.verification["verification_id"])
            self.assertEqual(_tree_bytes(fixture.base), before)
            self.assertEqual(list(fixture.evidence.glob("cleanup-*.json")), [])

    def test_a_retained_asset_changed_after_verification_blocks_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            retained = fixture.root / "AGENTS.md"
            retained.write_text(retained.read_text() + "\nuser edit after verification\n")
            before = _tree_bytes(fixture.base)
            with self.assertRaises(ContractError):
                fixture.cleanup(confirm_cleanup=fixture.verification["verification_id"])
            self.assertEqual(_tree_bytes(fixture.base), before)
            self.assertTrue((fixture.root / ".trellis").is_dir())
            self.assertEqual(list(fixture.evidence.glob("cleanup-*.json")), [])

    def test_a_successful_cleanup_retry_is_already_complete_and_cumulative(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            first, first_code = fixture.cleanup(
                confirm_cleanup=fixture.verification["verification_id"]
            )
            self.assertEqual(first_code, 0, first)
            first_receipt = first["migration"]["cleanup_receipt"]
            first_path = (
                fixture.evidence / f"cleanup-{first_receipt['cleanup_id']}.json"
            )

            second, second_code = fixture.cleanup(
                previous_receipt_path=first_path,
                confirm_cleanup=fixture.verification["verification_id"],
            )
            self.assertEqual(second_code, 0, second)
            self.assertEqual(second["status"], "already-complete")
            second_receipt = second["migration"]["cleanup_receipt"]
            self.assertEqual(
                second_receipt["payload"]["previous_receipt_id"],
                first_receipt["cleanup_id"],
            )
            self.assertTrue(
                (
                    fixture.evidence / f"cleanup-{second_receipt['cleanup_id']}.json"
                ).is_file()
            )

    def test_a_failed_cleanup_can_resume_from_its_cumulative_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            refusal = ContractError(
                "state-conflict", "injected cleanup refusal", exit_code=2
            )
            with mock.patch("sbtd_migration.remove_reference", side_effect=refusal):
                first, first_code = fixture.cleanup(
                    confirm_cleanup=fixture.verification["verification_id"]
                )
            self.assertEqual(first_code, 5, first)
            first_receipt = first["migration"]["cleanup_receipt"]
            self.assertEqual(first_receipt["payload"]["status"], "failed")
            first_result = first_receipt["payload"]["projects"][0]["private_results"][0]
            self.assertEqual(first_result["status"], "failed")
            self.assertEqual(first_result["before"], first_result["after"])
            self.assertTrue((fixture.root / ".trellis").is_dir())
            first_path = (
                fixture.evidence / f"cleanup-{first_receipt['cleanup_id']}.json"
            )
            self.assertTrue(first_path.is_file())
            second, second_code = fixture.cleanup(
                previous_receipt_path=first_path,
                confirm_cleanup=fixture.verification["verification_id"],
            )
            self.assertEqual(second_code, 0, second)
            self.assertEqual(second["status"], "cleaned")
            self.assertFalse((fixture.root / ".trellis").exists())
            self.assertEqual(
                second["migration"]["cleanup_receipt"]["payload"][
                    "previous_receipt_id"
                ],
                first_receipt["cleanup_id"],
            )


    def test_a_failed_cleanup_project_does_not_fail_an_unaffected_project(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = VerifiedMigration(
                Path(directory).resolve(), names=("one", "two")
            )
            fixture.build()
            from sbtd_migration_files import remove_reference as real_remove

            def refuse_second_project(path, expected, *, scope):
                if Path(path) == fixture.roots[1] / ".trellis":
                    raise ContractError(
                        "state-conflict",
                        "injected second-project refusal",
                        exit_code=2,
                    )
                return real_remove(path, expected, scope=scope)

            with mock.patch(
                "sbtd_migration.remove_reference",
                side_effect=refuse_second_project,
            ):
                envelope, code = fixture.cleanup(
                    confirm_cleanup=fixture.verification["verification_id"]
                )
            self.assertEqual(code, 5, envelope)
            receipt = envelope["migration"]["cleanup_receipt"]
            projects = {
                project["root"]: project for project in receipt["payload"]["projects"]
            }
            self.assertEqual(
                projects[str(fixture.roots[1])]["reason"],
                "a declared cleanup resource failed",
            )
            self.assertEqual(receipt["payload"]["status"], "failed")
            statuses = {
                project["root"]: project["status"]
                for project in receipt["payload"]["projects"]
            }
            self.assertEqual(statuses[str(fixture.roots[0])], "cleaned")
            self.assertEqual(statuses[str(fixture.roots[1])], "failed")
            self.assertFalse((fixture.roots[0] / ".trellis").exists())
            self.assertTrue((fixture.roots[1] / ".trellis").is_dir())

    def test_a_receipt_save_failure_is_failed_and_does_not_claim_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            with mock.patch(
                "sbtd_migration.save_document",
                side_effect=ContractError(
                    "write-failed", "cannot save receipt", exit_code=5
                ),
            ):
                envelope, code = fixture.cleanup(
                    confirm_cleanup=fixture.verification["verification_id"]
                )
            self.assertEqual(code, 5, envelope)
            self.assertEqual(envelope["status"], "failed")
            self.assertEqual(
                envelope["reason"], "cumulative evidence persistence failed"
            )
            self.assertEqual(list(fixture.evidence.glob("cleanup-*.json")), [])

    def test_cleanup_cli_emits_one_blocked_json_envelope_without_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            args = SimpleNamespace(
                phase="cleanup",
                manifest=str(fixture.manifest_path),
                apply_receipt=str(fixture.apply_path),
                deployment_evidence=str(fixture.deployment_path),
                verification=str(fixture.verification_path),
                cleanup_receipt=None,
                confirm_cleanup=None,
                json=True,
            )
            output = io.StringIO()
            with redirect_stdout(output):
                code = run_migration(args)
            self.assertEqual(code, 2)
            response = json.loads(output.getvalue())
            self.assertEqual(response["phase"], "cleanup")
            self.assertEqual(response["status"], "blocked")
            self.assertEqual(response["migration"], {})
            self.assertTrue((fixture.root / ".trellis").is_dir())

    def test_run_migration_dispatches_the_cleanup_phase(self):
        envelope = {
            "mode": "migration",
            "phase": "cleanup",
            "status": "blocked",
            "manifest_id": "0" * 64,
            "verification_id": "1" * 64,
            "projects": [],
            "reason": "confirmation required",
            "nextStep": "Confirm the current verification_id.",
            "migration": {},
        }
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            args = SimpleNamespace(
                phase="cleanup",
                manifest=str(base / "manifest.json"),
                apply_receipt=str(base / "apply.json"),
                deployment_evidence=str(base / "deployment.json"),
                verification=str(base / "verification.json"),
                cleanup_receipt=None,
                confirm_cleanup="1" * 64,
                json=False,
            )
            with mock.patch(
                "sbtd_migration.cleanup_migration", return_value=(envelope, 2)
            ) as cleanup:
                code = run_migration(args)
        self.assertEqual(code, 2)
        cleanup.assert_called_once_with(
            base / "manifest.json",
            base / "apply.json",
            base / "deployment.json",
            base / "verification.json",
            previous_receipt_path=None,
            confirm_cleanup="1" * 64,
        )


if __name__ == "__main__":
    unittest.main()
