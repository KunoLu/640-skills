"""R1.2c history and verification-artifact import.

Scenario text lives in spec/r1.2c-history-import-scenarios.md. The consumer
seam is history_import.build_scan_plan / approve_scan_plan / import_plan.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from event_store import EventStore, StoreError
from history_import import (
    HistoryImportError,
    ImportSource,
    approve_scan_plan,
    build_scan_plan,
    import_plan,
    ingest_approved,
    main,
)

INSTALLATION = "inst_r12c_test"
DEVICE = "device_r12c_test"
FIXTURE = (
    REPO
    / "tests"
    / "fixtures"
    / "validation-evidence"
    / "validation-evidence-v2"
    / "positive-unchanged-playwright"
)

TASK_TEXT = """---
schema_version: 1
id: demo-history
workflow_mode: strict
mode_source: user
mode_note: fixture
status: planned
branch: demo
created_at: '1999-05-05T05:05:05Z'
updated_at: '2020-01-02T03:04:05Z'
completed_at: null
---
正文不参与导入。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2020-01-02T03:04:05Z | planned | in-progress | secret-reason-token | secret-evidence-token |
| unknown | in-progress | checking | review | note |
| 2020-01-03T00:00:00Z | checking | done | finished | note |
| 2020-01-04T00:00:00Z | done | planned | reopen | note |
"""


def _enable(home: Path) -> None:
    home.mkdir(mode=0o700, exist_ok=True)
    os.chmod(home, 0o700)
    (home / "config.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "observation": {
                    "enabled": True,
                    "level": "metadata",
                    "failure_policy": "best-effort",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _keys(value: object):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _keys(item)


class ScanPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "project"
        self.root.mkdir()
        self.task = self.root / "ai" / "tasks" / "demo" / "task.md"
        self.task.parent.mkdir(parents=True)
        self.task.write_text(TASK_TEXT, encoding="utf-8")
        bait = self.root / "bait"
        bait.mkdir()
        (bait / "task.md").write_text("not named\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_unapproved_plan_lists_only_named_sources_and_does_not_import(self) -> None:
        home = Path(self.tmp.name) / "home"
        _enable(home)
        with (
            patch("os.listdir", side_effect=AssertionError("listdir")),
            patch("os.walk", side_effect=AssertionError("walk")),
            patch.object(Path, "read_text", side_effect=AssertionError("read")),
            patch.object(Path, "read_bytes", side_effect=AssertionError("read")),
        ):
            plan = build_scan_plan(
                self.root, [ImportSource("task-history", "ai/tasks/demo/task.md")]
            )
        self.assertFalse(plan.approved)
        self.assertEqual(
            [(item.kind, item.path) for item in plan.sources],
            [("task-history", "ai/tasks/demo/task.md")],
        )
        self.assertNotIn("bait", [item.path for item in plan.sources])
        with EventStore.open(home, confirmed=True) as store:
            with self.assertRaises(HistoryImportError):
                import_plan(
                    store,
                    plan,
                    installation_id=INSTALLATION,
                    device_id=DEVICE,
                )
            self.assertEqual(store.replay(), [])

    def test_approval_is_a_separate_value(self) -> None:
        plan = build_scan_plan(
            self.root, [ImportSource("task-history", "ai/tasks/demo/task.md")]
        )
        approved = approve_scan_plan(plan)
        self.assertFalse(plan.approved)
        self.assertTrue(approved.approved)
        self.assertEqual(plan.sources, approved.sources)

    def test_escape_paths_and_symlinks_are_refused(self) -> None:
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        secret = outside / "task.md"
        secret.write_text("SECRET-OUTSIDE\n", encoding="utf-8")
        (self.root / "linked.md").symlink_to(secret)
        with self.assertRaises(HistoryImportError):
            build_scan_plan(
                self.root, [ImportSource("task-history", "../outside/task.md")]
            )
        with self.assertRaises(HistoryImportError):
            build_scan_plan(
                self.root, [ImportSource("task-history", secret.as_posix())]
            )
        with self.assertRaises(HistoryImportError):
            build_scan_plan(self.root, [ImportSource("task-history", "linked.md")])
        self.assertEqual(secret.read_text(encoding="utf-8"), "SECRET-OUTSIDE\n")

    def test_cli_without_approval_does_not_create_a_store(self) -> None:
        home = Path(self.tmp.name) / "home-cli"
        code = main(
            [
                "--runtime-home",
                str(home),
                "--installation-id",
                INSTALLATION,
                "--device-id",
                DEVICE,
                "--project-root",
                str(self.root),
                "--source",
                "task-history=ai/tasks/demo/task.md",
            ]
        )
        self.assertEqual(code, 0)
        self.assertFalse((home / "audit.db").exists())
        self.assertFalse((home / "spool").exists())


class TaskHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "project"
        self.root.mkdir()
        self.task = self.root / "ai" / "tasks" / "demo" / "task.md"
        self.task.parent.mkdir(parents=True)
        self.task.write_text(TASK_TEXT, encoding="utf-8")
        self.before = self.task.read_bytes()
        self.home = Path(self.tmp.name) / "home"
        _enable(self.home)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _import(self, **kwargs):
        plan = approve_scan_plan(
            build_scan_plan(
                self.root, [ImportSource("task-history", "ai/tasks/demo/task.md")]
            )
        )
        with EventStore.open(self.home, confirmed=True) as store:
            receipt = import_plan(
                store,
                plan,
                installation_id=INSTALLATION,
                device_id=DEVICE,
                **kwargs,
            )
            return receipt, store.replay()

    def test_times_status_and_identity_come_only_from_the_table(self) -> None:
        _receipt, events = self._import()
        self.assertEqual(self.task.read_bytes(), self.before)
        by_type = {}
        for event in events:
            self.assertEqual(event["provenance"]["source_kind"], "artifact-imported")
            self.assertEqual(event["provenance"]["observation_level"], "declared")
            self.assertEqual(event["provenance"]["evidence_status"], "present")
            self.assertIsNone(event["scope"]["task_uid"])
            self.assertEqual(event["scope"]["logical_task_id"], "demo-history")
            self.assertIsNone(event["scope"]["project_id"])
            self.assertEqual(event["workflow"]["mode_at_event"], "unknown")
            self.assertNotEqual(event["occurred_at"], "1999-05-05T05:05:05Z")
            self.assertNotIn("secret-reason-token", json.dumps(event))
            self.assertNotIn("secret-evidence-token", json.dumps(event))
            by_type.setdefault(event["event_type"], []).append(event)
        self.assertNotIn("task.created", by_type)
        started = by_type["task.state_changed"][0]
        self.assertEqual(started["occurred_at"], "2020-01-02T03:04:05Z")
        self.assertEqual(
            started["state"], {"previous": "planned", "current": "in-progress"}
        )
        unknown = by_type["task.state_changed"][1]
        self.assertIsNone(unknown["occurred_at"])
        self.assertNotEqual(unknown["recorded_at"], "2020-01-02T03:04:05Z")
        self.assertEqual(unknown["state"]["current"], "checking")
        self.assertEqual(
            by_type["task.reopened"][0]["state"],
            {"previous": "done", "current": "planned"},
        )
        self.assertTrue(all(event["recorded_at"] for event in events))

    def test_repeat_import_only_confirms(self) -> None:
        plan = approve_scan_plan(
            build_scan_plan(
                self.root, [ImportSource("task-history", "ai/tasks/demo/task.md")]
            )
        )
        with EventStore.open(self.home, confirmed=True) as store:
            first = import_plan(
                store, plan, installation_id=INSTALLATION, device_id=DEVICE
            )
            second = import_plan(
                store, plan, installation_id=INSTALLATION, device_id=DEVICE
            )
            self.assertGreater(first.accepted, 0)
            self.assertEqual(second.accepted, 0)
            self.assertEqual(second.duplicate, first.accepted)
            self.assertEqual(len(store.replay()), first.accepted)

    def test_explicit_project_id_is_stored_and_not_looked_up(self) -> None:
        _receipt, events = self._import(project_id="prj_explicit")
        self.assertTrue(events)
        self.assertTrue(
            all(event["scope"]["project_id"] == "prj_explicit" for event in events)
        )


class VerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        _enable(self.home)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _import(self, root: Path, relative: str):
        plan = approve_scan_plan(
            build_scan_plan(root, [ImportSource("verification-envelope", relative)])
        )
        with EventStore.open(self.home, confirmed=True) as store:
            import_plan(store, plan, installation_id=INSTALLATION, device_id=DEVICE)
            return store.replay()

    def test_validated_playwright_envelope_records_a_pass_without_artifact_object(
        self,
    ) -> None:
        events = self._import(FIXTURE, "envelope.json")
        finished = [
            event for event in events if event["event_type"] == "validation.finished"
        ]
        self.assertEqual(len(finished), 1)
        event = finished[0]
        self.assertEqual(event["validation"]["result"], "passed")
        self.assertEqual(event["validation"]["e2e_scope"], "full-stack")
        self.assertEqual(event["provenance"]["source_kind"], "artifact-imported")
        self.assertEqual(event["provenance"]["observation_level"], "artifact-verified")
        self.assertEqual(event["provenance"]["evidence_status"], "validated")
        self.assertEqual(event["occurred_at"], "2026-08-17T00:00:00Z")
        self.assertIsNone(event["scope"]["task_uid"])
        digest = "216c5ce8934894ce0409481c10d5ee0a4e8a1879ac47f060e63af856f18c9a57"
        self.assertIn(
            digest,
            [ref["external_id"] for ref in event["external_refs"]],
        )
        self.assertEqual(event["correlation"]["operation_id"], "run-1")
        self.assertNotIn("artifact", set(_keys(event)))
        self.assertTrue(
            any(case["result"] == "passed" for case in event["validation"]["cases"])
        )
        self.assertTrue(
            all(
                case["result"] != "passed" or case["attempt_no"] >= 1
                for case in event["validation"]["cases"]
            )
        )

    def test_html_title_does_not_become_a_pass(self) -> None:
        root = Path(self.tmp.name) / "html-project"
        root.mkdir()
        (root / "report.html").write_text(
            "<html><title>passed</title><body>15 passed</body></html>\n",
            encoding="utf-8",
        )
        events = self._import(root, "report.html")
        self.assertEqual(events, [])

    def test_status_word_without_a_validator_pass_is_not_a_pass(self) -> None:
        root = Path(self.tmp.name) / "claim"
        root.mkdir()
        (root / "envelope.json").write_text(
            json.dumps({"schemaVersion": 2, "status": "passed", "title": "passed"})
            + "\n",
            encoding="utf-8",
        )
        events = self._import(root, "envelope.json")
        self.assertTrue(events)
        for event in events:
            self.assertNotEqual((event.get("validation") or {}).get("result"), "passed")
            self.assertNotEqual(
                event["provenance"]["observation_level"], "artifact-verified"
            )
            self.assertEqual(event["provenance"]["evidence_status"], "invalid")
            self.assertIsNone(event["occurred_at"])

    def test_unmapped_e2e_mode_is_not_rewritten_as_passed(self) -> None:
        root = Path(self.tmp.name) / "mock-backed"
        shutil.copytree(FIXTURE, root)
        envelope_path = root / "envelope.json"
        payload = json.loads(envelope_path.read_text(encoding="utf-8"))
        payload["e2eMode"] = "mock-backed"
        envelope_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        events = self._import(root, "envelope.json")
        self.assertTrue(events)
        for event in events:
            self.assertNotEqual((event.get("validation") or {}).get("result"), "passed")
        self.assertTrue(
            any(
                event["provenance"]["evidence_status"] == "validated"
                for event in events
            )
        )


class SwitchTests(unittest.TestCase):
    def test_observation_off_creates_no_database(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "project"
        root.mkdir()
        task = root / "task.md"
        task.write_text(TASK_TEXT, encoding="utf-8")
        home = Path(tmp.name) / "home"
        plan = approve_scan_plan(
            build_scan_plan(root, [ImportSource("task-history", "task.md")])
        )
        with self.assertRaises(StoreError):
            ingest_approved(
                home,
                plan,
                confirmed=True,
                installation_id=INSTALLATION,
                device_id=DEVICE,
            )
        self.assertFalse((home / "audit.db").exists())
        self.assertFalse((home / "spool").exists())
        self.assertEqual(
            hashlib.sha256(task.read_bytes()).hexdigest(),
            hashlib.sha256(TASK_TEXT.encode("utf-8")).hexdigest(),
        )
