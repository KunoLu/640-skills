"""R1.2b omp host adapter: session JSONL to observation events.

Scenario text lives in spec/r1.2b-host-adapter-scenarios.md. Fixture shapes
mirror real omp 18.11.1 session records observed on this host. The consumer
seam is omp_adapter.parse_session_file / ingest_session.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contract_eval import validate_events
from event_store import EventStore, StoreError
from omp_adapter import PARSER_VERSION, SOURCE_ID, ingest_session, parse_session_file

INSTALLATION = "inst_r12b_test"
DEVICE = "device_r12b_test"

SESSION_ID = "01a14293-7c92-73af-813b-7dfb6ad1fadd"


def _record(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _fixture_lines() -> list[str]:
    return [
        _record(
            {
                "type": "session",
                "version": 3,
                "id": SESSION_ID,
                "timestamp": "2026-10-17T01:00:00.000Z",
                "cwd": "/workspace/640-skills",
            }
        ),
        _record(
            {
                "type": "model_change",
                "id": "6c845299",
                "timestamp": "2026-10-17T01:00:00.100Z",
                "runtime": {"version": "18.11.1"},
                "model": "xai-oauth/grok-4.7",
            }
        ),
        _record(
            {
                "type": "message",
                "id": "msg_assist_1",
                "parentId": "6c845299",
                "timestamp": "2026-10-17T01:00:01.000Z",
                "runtime": {"version": "18.11.1"},
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "先读取。"},
                        {
                            "type": "toolCall",
                            "id": "call-aaa|fc_1",
                            "name": "read",
                            "arguments": {"path": "skill://sbtd-task"},
                        },
                        {
                            "type": "toolCall",
                            "id": "call-bbb|fc_2",
                            "name": "bash",
                            "arguments": {"command": "echo hi", "i": "x"},
                        },
                    ],
                },
            }
        ),
        _record(
            {
                "type": "message",
                "id": "msg_result_1",
                "parentId": "msg_assist_1",
                "timestamp": "2026-10-17T01:00:01.400Z",
                "runtime": {"version": "18.11.1"},
                "message": {
                    "role": "toolResult",
                    "toolCallId": "call-aaa|fc_1",
                    "toolName": "read",
                    "isError": False,
                    "content": [{"type": "text", "text": "[Skill file]"}],
                },
            }
        ),
        _record(
            {
                "type": "message",
                "id": "msg_result_2",
                "parentId": "msg_assist_1",
                "timestamp": "2026-10-17T01:00:02.600Z",
                "runtime": {"version": "18.11.1"},
                "message": {
                    "role": "toolResult",
                    "toolCallId": "call-bbb|fc_2",
                    "toolName": "bash",
                    "isError": True,
                    "content": [{"type": "text", "text": "boom"}],
                },
            }
        ),
        _record({"type": "custom", "customType": "kpi.sbtd.session.v1", "data": {}}),
        '{"type": "message", "id": "broken"',
    ]


def _write_fixture(directory: Path) -> Path:
    path = directory / f"2026-10-17T01-00-00-000Z_{SESSION_ID}.jsonl"
    path.write_text("\n".join(_fixture_lines()) + "\n", encoding="utf-8")
    return path


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


class ParseSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.path = _write_fixture(self.dir)

    def parse(self):
        return parse_session_file(
            self.path, installation_id=INSTALLATION, device_id=DEVICE
        )

    def test_tool_call_maps_to_invocation_started(self) -> None:
        outcome = self.parse()
        started = [
            event
            for event in outcome.events
            if event["event_type"] == "invocation.started"
        ]
        self.assertEqual(len(started), 2)
        event = next(
            item
            for item in started
            if item["correlation"]["invocation_id"] == "call-bbb|fc_2"
        )
        self.assertEqual(
            event["component"],
            {"component_id": "tool:bash", "kind": "tool", "name": "bash"},
        )
        self.assertEqual(event["occurred_at"], "2026-10-17T01:00:01.000Z")
        self.assertEqual(event["correlation"]["invocation_id"], "call-bbb|fc_2")
        self.assertEqual(event["correlation"]["attempt_id"], "1")
        self.assertEqual(event["state"]["current"], "running")
        self.assertEqual(event["host"], {"host_kind": "omp", "host_version": "18.11.1"})
        self.assertEqual(event["scope"]["session_id"], SESSION_ID)
        self.assertIsNone(event["scope"]["task_uid"])
        provenance = event["provenance"]
        self.assertEqual(provenance["source_kind"], "host-observed")
        self.assertEqual(provenance["source_id"], SOURCE_ID)
        self.assertEqual(provenance["source_event_id"], "call-bbb|fc_2")
        self.assertEqual(provenance["observation_level"], "execution-observed")
        self.assertEqual(provenance["parser_version"], PARSER_VERSION)
        self.assertEqual(provenance["segment_id"], self.path.name)

    def test_skill_uri_read_maps_to_skill_loaded(self) -> None:
        outcome = self.parse()
        loaded = [
            event for event in outcome.events if event["event_type"] == "skill.loaded"
        ]
        self.assertEqual(len(loaded), 1)
        event = loaded[0]
        self.assertEqual(
            event["component"],
            {"component_id": "skill:sbtd-task", "kind": "skill"},
        )
        self.assertEqual(event["provenance"]["observation_level"], "loaded")

    def test_tool_result_maps_to_invocation_finished_with_duration(self) -> None:
        outcome = self.parse()
        finished = {
            event["correlation"]["invocation_id"]: event
            for event in outcome.events
            if event["event_type"] == "invocation.finished"
        }
        ok = finished["call-aaa|fc_1"]
        self.assertEqual(ok["state"], {"previous": "running", "current": "succeeded"})
        self.assertEqual(ok["measurement"]["duration_ms"], 400)
        self.assertEqual(ok["measurement"]["duration_basis"], "wall")
        self.assertEqual(ok["provenance"]["source_event_id"], "msg_result_1")

    def test_error_result_maps_to_failed(self) -> None:
        outcome = self.parse()
        failed = [
            event
            for event in outcome.events
            if event["event_type"] == "invocation.finished"
            and event["correlation"]["invocation_id"] == "call-bbb|fc_2"
        ]
        self.assertEqual(failed[0]["state"]["current"], "failed")
        self.assertEqual(failed[0]["measurement"]["duration_ms"], 1600)

    def test_unknown_records_and_bad_tail_are_skipped_and_counted(self) -> None:
        outcome = self.parse()
        self.assertEqual(outcome.records_read, 7)
        self.assertEqual(outcome.records_skipped, 3)
        self.assertEqual(len(outcome.events), 5)

    def test_all_events_pass_the_r1_schema(self) -> None:
        outcome = self.parse()
        self.assertTrue(outcome.events)
        validate_events(outcome.events)

    def test_events_do_not_carry_arguments_or_content(self) -> None:
        outcome = self.parse()
        for event in outcome.events:
            self.assertEqual(event["extensions"], {})
            self.assertNotIn("arguments", json.dumps(event))
            self.assertNotIn("echo hi", json.dumps(event))

    def test_malformed_timestamp_becomes_null_not_schema_rejection(self) -> None:
        path = self.dir / "bad-ts.jsonl"
        record = json.loads(_fixture_lines()[2])
        record["timestamp"] = "2026-10-17 01:00:01"  # no timezone, no T
        path.write_text(json.dumps(record) + "\n", encoding="utf-8")
        outcome = parse_session_file(
            path, installation_id=INSTALLATION, device_id=DEVICE
        )
        self.assertTrue(outcome.events)
        for event in outcome.events:
            self.assertIsNone(event["occurred_at"])
        validate_events(outcome.events)

    def test_orphan_tool_result_has_no_fabricated_previous_state(self) -> None:
        path = self.dir / "orphan.jsonl"
        path.write_text(_fixture_lines()[3] + "\n", encoding="utf-8")
        outcome = parse_session_file(
            path, installation_id=INSTALLATION, device_id=DEVICE
        )
        finished = [
            event
            for event in outcome.events
            if event["event_type"] == "invocation.finished"
        ]
        self.assertEqual(len(finished), 1)
        self.assertIsNone(finished[0]["state"]["previous"])
        # no start observed -> no duration; the block is omitted (schema has
        # no null measurement), so .get() must yield None
        self.assertIsNone(finished[0].get("measurement"))

    def test_overlong_component_id_is_skipped_and_counted(self) -> None:
        path = self.dir / "long.jsonl"
        record = json.loads(_fixture_lines()[2])
        tool_call = record["message"]["content"][1]
        tool_call["name"] = "x" * 200
        record["message"]["content"] = [tool_call]
        path.write_text(json.dumps(record) + "\n", encoding="utf-8")
        outcome = parse_session_file(
            path, installation_id=INSTALLATION, device_id=DEVICE
        )
        self.assertEqual(outcome.events, ())
        self.assertEqual(outcome.records_skipped, 1)


class IngestSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.home = self.dir / "runtime"
        _enable(self.home)
        self.session_dir = self.dir / "sessions"
        self.session_dir.mkdir()
        self.path = _write_fixture(self.session_dir)

    def _open(self, **kwargs) -> EventStore:
        return EventStore.open(self.home, confirmed=True, **kwargs)

    def test_ingest_appends_and_reports_receipt(self) -> None:
        with self._open() as store:
            receipt = ingest_session(
                store, self.path, installation_id=INSTALLATION, device_id=DEVICE
            )
            self.assertEqual(receipt.events_emitted, 5)
            self.assertEqual(receipt.accepted, 5)
            self.assertEqual(receipt.duplicate, 0)
            self.assertEqual(receipt.rejected, 0)
            self.assertEqual(receipt.host_kind, "omp")
            self.assertEqual(receipt.host_version, "18.11.1")
            self.assertEqual(receipt.parser_version, PARSER_VERSION)
            self.assertEqual(len(replay := store.replay()), 5)
            self.assertEqual(
                {event["event_type"] for event in replay},
                {"invocation.started", "invocation.finished", "skill.loaded"},
            )

    def test_second_ingest_only_confirms(self) -> None:
        with self._open() as store:
            first = ingest_session(
                store, self.path, installation_id=INSTALLATION, device_id=DEVICE
            )
            second = ingest_session(
                store, self.path, installation_id=INSTALLATION, device_id=DEVICE
            )
            self.assertEqual(second.accepted, 0)
            self.assertEqual(second.duplicate, first.events_emitted)
            self.assertEqual(len(store.replay()), first.events_emitted)
            checkpoints = store.checkpoints()
            self.assertTrue(checkpoints)
            self.assertTrue(
                all(checkpoint.source_id == SOURCE_ID for checkpoint in checkpoints)
            )
            self.assertTrue(
                all(
                    checkpoint.parser_version == PARSER_VERSION
                    for checkpoint in checkpoints
                )
            )

    def test_quality_counts_accepted_events(self) -> None:
        with self._open() as store:
            ingest_session(
                store, self.path, installation_id=INSTALLATION, device_id=DEVICE
            )
            quality = store.quality()
            self.assertEqual(quality.accepted, 5)
            self.assertEqual(quality.unlinked, 5)

    def test_observation_off_refuses_and_writes_nothing(self) -> None:
        (self.home / "config.json").write_text(
            json.dumps({"schema_version": 1, "observation": {"enabled": False}}),
            encoding="utf-8",
        )
        with self.assertRaises(StoreError):
            EventStore.open(self.home, confirmed=True)
        self.assertFalse((self.home / "audit.db").exists())
        self.assertFalse((self.home / "spool").exists())

    def test_cli_rejects_empty_identity_without_traceback(self) -> None:
        from io import StringIO
        from unittest.mock import patch

        from omp_adapter import main

        stdout = StringIO()
        with patch("sys.stdout", stdout):
            code = main(
                [
                    str(self.path),
                    "--runtime-home",
                    str(self.home),
                    "--installation-id",
                    "inst1",
                    "--device-id",
                    "",
                    "--confirmed",
                ]
            )
        self.assertEqual(code, 2)
        self.assertIn("error", stdout.getvalue())
        self.assertFalse((self.home / "audit.db").exists())


if __name__ == "__main__":
    unittest.main()
