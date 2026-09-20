from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from onboard_contracts import ContractError, canonical_json_bytes, seal_document
from sbtd_migration import apply_migration, runtime_versions
from sbtd_migration_files import snapshot
from sbtd_migration_plan import plan_migration
from sbtd_migration_verify import validate_deployment_reports, verify_migration


class DeploymentReportTests(unittest.TestCase):
    def test_a_passing_envelope_cannot_hide_a_failed_raw_run(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = base / "project"
            root.mkdir()
            private = base / "private"
            private.mkdir(mode=0o700)
            report_path = private / "smoke.json"
            summary = private / "smoke.md"
            summary.write_text("合成契约夹具；不证明真实host部署。\n")
            head = "1" * 40
            raw = {
                "repositoryKey": "fixture/project",
                "projectRoot": str(root),
                "sourceRef": "main",
                "sourceCommit": head,
                "worktreeState": "clean",
                "sourceRevision": "exact",
                "evidenceSource": "developer-local",
                "trigger": "manual",
                "environmentAlignment": "verified",
                "evidencePublication": "local-only",
                "e2eMode": "smoke-only",
                "mockStrategy": "none",
                "startedAt": "2026-09-19T00:01:00Z",
                "finishedAt": "2026-09-19T00:02:00Z",
                "command": ["fixture"],
                "stdout": "synthetic contract data",
                "stderr": "",
                "exitCode": 0,
                "timedOut": False,
            }
            envelope: dict[str, Any] = {
                "schemaVersion": 1,
                "runId": "fixture-smoke",
                "createdAt": "2026-09-19T00:02:00Z",
                "evidenceSource": "developer-local",
                "trigger": "manual",
                "repository": {
                    "repositoryKey": "fixture/project",
                    "sourceRef": "main",
                    "sourceCommit": head,
                    "worktreeState": "clean",
                },
                "sourceRevision": "exact",
                "environmentAlignment": "verified",
                "e2eMode": "smoke-only",
                "mockStrategy": "none",
                "featureSources": [],
                "reports": [
                    {
                        "testType": "api",
                        "path": str(report_path),
                        "summaryMd": str(summary),
                        "sha256": "",
                        "status": "passed",
                        "mode": "smoke-only",
                    }
                ],
                "evidencePublication": "local-only",
                "secretsRedacted": True,
            }
            evidence_path = private / "smoke.evidence.json"
            project = {
                "root": str(root),
                "source_ref": "main",
                "head": head,
                "report_refs": [],
            }
            deployment = {
                "started_at": "2026-09-19T00:00:00Z",
                "finished_at": "2026-09-19T00:03:00Z",
            }

            def save():
                report_path.write_text(json.dumps(raw))
                envelope["reports"][0]["sha256"] = hashlib.sha256(
                    report_path.read_bytes()
                ).hexdigest()
                evidence_path.write_text(json.dumps(envelope))
                project["report_refs"] = [
                    {
                        "path": str(path),
                        "state": {
                            "type": "file",
                            "checksum": hashlib.sha256(path.read_bytes()).hexdigest(),
                        },
                    }
                    for path in (evidence_path, report_path, summary)
                ]

            save()
            validate_deployment_reports(deployment, project)
            raw["exitCode"] = 1
            save()
            with self.assertRaises(ContractError):
                validate_deployment_reports(deployment, project)
            self.assertEqual(json.loads(report_path.read_text())["exitCode"], 1)


class ReportFixture:
    """合成契约夹具：只证明消费者边界，不证明真实 host 或部署发生。"""

    def __init__(self, base: Path) -> None:
        self.root = base / "project"
        self.root.mkdir()
        self.private = base / "private"
        self.private.mkdir(mode=0o700)
        self.report_path = self.private / "smoke.json"
        self.summary = self.private / "smoke.md"
        self.summary.write_text("合成契约夹具；不证明真实host部署。\n")
        self.head = "1" * 40
        self.raw: dict[str, Any] = {
            "repositoryKey": "fixture/project",
            "projectRoot": str(self.root),
            "sourceRef": "main",
            "sourceCommit": self.head,
            "worktreeState": "clean",
            "sourceRevision": "exact",
            "evidenceSource": "developer-local",
            "trigger": "manual",
            "environmentAlignment": "verified",
            "evidencePublication": "local-only",
            "e2eMode": "smoke-only",
            "mockStrategy": "none",
            "startedAt": "2026-09-19T00:01:00Z",
            "finishedAt": "2026-09-19T00:02:00Z",
            "command": ["fixture"],
            "stdout": "synthetic contract data",
            "stderr": "",
            "exitCode": 0,
            "timedOut": False,
        }
        self.envelope: dict[str, Any] = {
            "schemaVersion": 1,
            "runId": "fixture-smoke",
            "createdAt": "2026-09-19T00:02:00Z",
            "evidenceSource": "developer-local",
            "trigger": "manual",
            "repository": {
                "repositoryKey": "fixture/project",
                "sourceRef": "main",
                "sourceCommit": self.head,
                "worktreeState": "clean",
            },
            "sourceRevision": "exact",
            "environmentAlignment": "verified",
            "e2eMode": "smoke-only",
            "mockStrategy": "none",
            "featureSources": [],
            "reports": [
                {
                    "testType": "api",
                    "path": str(self.report_path),
                    "summaryMd": str(self.summary),
                    "sha256": "",
                    "status": "passed",
                    "mode": "smoke-only",
                }
            ],
            "evidencePublication": "local-only",
            "secretsRedacted": True,
        }
        self.evidence_path = self.private / "smoke.evidence.json"
        self.project: dict[str, Any] = {
            "root": str(self.root),
            "source_ref": "main",
            "head": self.head,
            "report_refs": [],
        }
        self.deployment = {
            "started_at": "2026-09-19T00:00:00Z",
            "finished_at": "2026-09-19T00:03:00Z",
        }

    def save(self) -> None:
        self.report_path.write_text(json.dumps(self.raw))
        self.envelope["reports"][0]["sha256"] = hashlib.sha256(
            self.report_path.read_bytes()
        ).hexdigest()
        self.evidence_path.write_text(json.dumps(self.envelope))
        self.refresh_refs()

    def refresh_refs(self) -> None:
        self.project["report_refs"] = [
            {
                "path": str(path),
                "state": {
                    "type": "file",
                    "checksum": hashlib.sha256(path.read_bytes()).hexdigest(),
                },
            }
            for path in (self.evidence_path, self.report_path, self.summary)
        ]


def _tree_bytes(base: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(base)): path.read_bytes()
        for path in base.rglob("*")
        if path.is_file()
    }


class DeploymentReportAcceptanceTests(unittest.TestCase):
    def build(self, base: Path) -> ReportFixture:
        fixture = ReportFixture(base)
        fixture.save()
        return fixture

    def test_a_genuine_current_api_smoke_is_accepted_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            before = _tree_bytes(base)
            self.assertIsNone(
                validate_deployment_reports(fixture.deployment, fixture.project)
            )
            self.assertEqual(_tree_bytes(base), before)

    def test_a_stale_raw_run_is_safely_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.raw["startedAt"] = "2026-09-18T23:59:00Z"
            fixture.save()
            before = _tree_bytes(base)
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)
            self.assertEqual(_tree_bytes(base), before)

    def test_a_raw_run_finished_after_the_attempt_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.raw["finishedAt"] = "2026-09-19T00:04:00Z"
            fixture.save()
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_a_timed_out_raw_run_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.raw["timedOut"] = True
            fixture.save()
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_a_raw_run_bound_to_another_root_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.raw["projectRoot"] = str(fixture.private)
            fixture.save()
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_a_raw_run_bound_to_another_revision_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.raw["sourceCommit"] = "2" * 40
            fixture.save()
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_a_mocked_report_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.envelope["mockStrategy"] = "user-approved"
            fixture.save()
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_an_unverified_environment_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.envelope["environmentAlignment"] = "unverified"
            fixture.save()
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_a_failed_report_entry_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.envelope["reports"][0]["status"] = "failed"
            fixture.save()
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_a_project_without_an_api_smoke_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.envelope["reports"][0]["testType"] = "unit"
            fixture.save()
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_a_missing_summary_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.summary.unlink()
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_an_auxiliary_report_with_a_non_smoke_mode_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            unit_report = fixture.private / "unit-report.json"
            unit_summary = fixture.private / "unit-report.md"
            unit_report.write_text(json.dumps({"synthetic": "unit evidence"}))
            unit_summary.write_text("合成辅助报告；不证明 smoke。\n")
            fixture.envelope["reports"].append(
                {
                    "testType": "unit",
                    "path": str(unit_report),
                    "summaryMd": str(unit_summary),
                    "sha256": hashlib.sha256(unit_report.read_bytes()).hexdigest(),
                    "status": "passed",
                    "mode": "not-needed",
                }
            )
            fixture.evidence_path.write_text(json.dumps(fixture.envelope))
            fixture.refresh_refs()
            fixture.project["report_refs"].extend(
                {
                    "path": str(path),
                    "state": {
                        "type": "file",
                        "checksum": hashlib.sha256(path.read_bytes()).hexdigest(),
                    },
                }
                for path in (unit_report, unit_summary)
            )

            self.assertIsNone(
                validate_deployment_reports(fixture.deployment, fixture.project)
            )

    def test_a_summary_must_be_a_declared_bound_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.project["report_refs"] = [
                reference
                for reference in fixture.project["report_refs"]
                if reference["path"] != str(fixture.summary)
            ]
            fixture.summary.write_text("changed without a bound reference\n")
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_a_naive_report_timestamp_is_refused_as_contract_error(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.raw["startedAt"] = "2026-09-19T00:01:00"
            fixture.save()
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_raw_run_provenance_must_match_the_envelope(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.raw["sourceRevision"] = "dirty"
            fixture.save()
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_a_missing_raw_report_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.report_path.unlink()
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_a_changed_report_breaks_its_bound_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.report_path.write_text(
                json.dumps({**fixture.raw, "stdout": "changed"})
            )
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_a_report_outside_the_declared_refs_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            foreign = fixture.private / "foreign.json"
            foreign.write_bytes(fixture.report_path.read_bytes())
            fixture.envelope["reports"][0]["path"] = str(foreign)
            fixture.evidence_path.write_text(json.dumps(fixture.envelope))
            fixture.refresh_refs()
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_an_envelope_created_before_the_attempt_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.envelope["createdAt"] = "2026-09-18T23:00:00Z"
            fixture.save()
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_an_inverted_attempt_window_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.deployment["started_at"] = "2026-09-19T00:04:00Z"
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_a_null_ref_non_git_identity_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.project["source_ref"] = None
            fixture.project["head"] = None
            fixture.envelope["repository"]["sourceRef"] = "non-git"
            fixture.envelope["repository"]["sourceCommit"] = None
            fixture.envelope["repository"]["worktreeState"] = "unknown"
            fixture.envelope["sourceRevision"] = "unknown"
            fixture.raw["sourceRef"] = "non-git"
            fixture.raw["sourceCommit"] = None
            fixture.raw["worktreeState"] = "unknown"
            fixture.raw["sourceRevision"] = "unknown"
            fixture.save()
            before = _tree_bytes(base)
            self.assertIsNone(
                validate_deployment_reports(fixture.deployment, fixture.project)
            )
            self.assertEqual(_tree_bytes(base), before)

    def test_a_null_ref_detached_identity_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.project["source_ref"] = None
            fixture.project["head"] = "2" * 40
            fixture.envelope["repository"]["sourceRef"] = "HEAD"
            fixture.envelope["repository"]["sourceCommit"] = "2" * 40
            fixture.raw["sourceRef"] = "HEAD"
            fixture.raw["sourceCommit"] = "2" * 40
            fixture.save()
            self.assertIsNone(
                validate_deployment_reports(fixture.deployment, fixture.project)
            )

    def test_a_retained_report_inside_the_apply_epoch_is_accepted_on_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.deployment["previous_deployment_id"] = "f" * 64
            fixture.deployment["started_at"] = "2026-09-19T00:05:00Z"
            fixture.deployment["finished_at"] = "2026-09-19T00:06:00Z"
            epoch_started = "2026-09-19T00:00:30Z"
            self.assertIsNone(
                validate_deployment_reports(
                    fixture.deployment, fixture.project, epoch_started=epoch_started
                )
            )

    def test_a_retained_report_before_the_apply_epoch_is_refused_on_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.deployment["previous_deployment_id"] = "f" * 64
            fixture.deployment["started_at"] = "2026-09-19T00:05:00Z"
            fixture.deployment["finished_at"] = "2026-09-19T00:06:00Z"
            fixture.raw["startedAt"] = "2026-09-19T00:00:10Z"
            fixture.save()
            epoch_started = "2026-09-19T00:00:30Z"
            with self.assertRaises(ContractError):
                validate_deployment_reports(
                    fixture.deployment, fixture.project, epoch_started=epoch_started
                )

    def test_a_naive_apply_epoch_is_refused_as_contract_error(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.deployment["previous_deployment_id"] = "f" * 64
            fixture.deployment["started_at"] = "2026-09-19T00:05:00Z"
            fixture.deployment["finished_at"] = "2026-09-19T00:06:00Z"
            with self.assertRaises(ContractError):
                validate_deployment_reports(
                    fixture.deployment,
                    fixture.project,
                    epoch_started="2026-09-19T00:00:30",
                )

    def test_a_raw_run_without_a_command_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            del fixture.raw["command"]
            fixture.save()
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_a_raw_run_with_an_empty_command_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.raw["command"] = []
            fixture.save()
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_a_raw_run_without_captured_output_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            del fixture.raw["stdout"]
            fixture.save()
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_a_raw_run_with_a_contradictory_process_exit_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            fixture = self.build(base)
            fixture.raw["processExitCode"] = 1
            fixture.save()
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)

    def test_an_explicit_unknown_process_exit_is_not_a_missing_legacy_field(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.build(Path(directory).resolve())
            fixture.raw["processExitCode"] = None
            fixture.save()
            with self.assertRaises(ContractError):
                validate_deployment_reports(fixture.deployment, fixture.project)


def _legacy_project(base: Path, name: str) -> Path:
    root = base / name
    (root / ".trellis/workspace/dev01").mkdir(parents=True)
    (root / ".codex/agents").mkdir(parents=True)
    (root / ".trellis/.developer").write_bytes(
        b"name=dev01\ninitialized_at=2026-09-01T12:00:00\n"
    )
    (root / ".trellis/.version").write_text("0.6.17\n")
    (root / ".trellis/workspace/dev01/journal-1.md").write_text(
        "Synthetic private legacy journal.\n"
    )
    (root / ".trellis/workspace/dev01/untracked.bin").write_bytes(
        b"\x00retained-private-fixture\xff"
    )
    (root / ".gitignore").write_text(".trellis/\n.gitnexus/\n")
    owned = {
        ".codex/agents/trellis-implement.toml": b'name = "trellis-implement"\n',
        "AGENTS.md": b"Foreign project rule.\n<!-- TRELLIS:START -->\nLegacy route.\n<!-- TRELLIS:END -->\n",
    }
    for filename, content in owned.items():
        (root / filename).write_bytes(content)
    (root / ".trellis/.template-hashes.json").write_text(
        json.dumps(
            {
                "__version": 2,
                "hashes": {
                    filename: hashlib.sha256(content).hexdigest()
                    for filename, content in owned.items()
                },
            }
        )
    )
    return root


def _file_ref(path: Path) -> dict:
    return {
        "path": str(path),
        "state": {
            "type": "file",
            "checksum": hashlib.sha256(path.read_bytes()).hexdigest(),
        },
    }


class MigrationVerifyPathTests(unittest.TestCase):
    """冻结合法证据 + 真实 plan/apply 批次；只证明只读 verify 消费者边界。"""

    def test_a_complete_migration_verifies_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = _legacy_project(base, "project")
            home, vault, evidence = (
                base / name for name in ("home", "vault", "evidence")
            )
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
                    [root],
                    vault,
                    "fixture-custodian",
                    None,
                    tool_versions=runtime_versions(),
                )
                manifest_path = evidence / "manifest.json"
                manifest_path.write_bytes(canonical_json_bytes(manifest))
                applied, apply_code = apply_migration(manifest_path, confirmed=True)
                self.assertEqual(apply_code, 0, applied)
                receipt = applied["migration"]["apply_receipt"]
                apply_path = next(
                    path
                    for path in evidence.glob("*.json")
                    if json.loads(path.read_text()).get("apply_id")
                    == receipt["apply_id"]
                )

                moment = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                report_path = evidence / "smoke.json"
                summary = evidence / "smoke.md"
                summary.write_text("合成契约夹具；不证明真实host部署。\n")
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
                envelope = {
                    "schemaVersion": 1,
                    "runId": "fixture-smoke",
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
                    "reports": [
                        {
                            "testType": "api",
                            "path": str(report_path),
                            "summaryMd": str(summary),
                            "sha256": hashlib.sha256(
                                report_path.read_bytes()
                            ).hexdigest(),
                            "status": "passed",
                            "mode": "smoke-only",
                        }
                    ],
                    "evidencePublication": "local-only",
                    "secretsRedacted": True,
                }
                evidence_path = evidence / "smoke.evidence.json"
                evidence_path.write_text(json.dumps(envelope))
                deployment = seal_document(
                    "deployment_evidence",
                    {
                        "manifest_id": manifest["manifest_id"],
                        "apply_id": receipt["apply_id"],
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
                                "report_refs": [
                                    _file_ref(evidence_path),
                                    _file_ref(report_path),
                                    _file_ref(summary),
                                ],
                            }
                        ],
                        "shared_results": [],
                        "started_at": moment,
                        "finished_at": moment,
                    },
                )
                deployment_path = evidence / "deployment.json"
                deployment_path.write_bytes(canonical_json_bytes(deployment))

                before = snapshot(base)
                verified, exit_code = verify_migration(
                    manifest_path, apply_path, deployment_path
                )
                self.assertEqual(exit_code, 0, verified)
                self.assertEqual(verified["status"], "verified")
                self.assertEqual(
                    {
                        project["root"]: project["status"]
                        for project in verified["projects"]
                    },
                    {str(root): "verified"},
                )
                self.assertEqual(snapshot(base), before)
                retired = root / ".codex/agents/trellis-implement.toml"
                self.assertFalse(retired.exists())
                payload_project = verified["migration"]["verification"]["payload"][
                    "projects"
                ][0]
                self.assertNotIn(
                    str(retired),
                    [asset["path"] for asset in payload_project["retained_assets"]],
                )
                self.assertEqual(
                    [
                        candidate["target"]
                        for candidate in payload_project["cleanup_candidates"]
                    ],
                    [str(root / ".trellis")],
                )


if __name__ == "__main__":
    unittest.main()
