"""R1.2b codex host adapter: `codex exec --json` JSONL to observation events.

Scenario text lives in spec/r1.2b-host-adapter-scenarios.md. Fixture shapes
follow the documented exec JSONL format (thread.started, item.started,
item.completed with command_execution / mcp_tool_call / ...). Codex is not
installed or run here; the real smoke against codex@0.163.0 is executed by a
separate operator using sbtd-runtime/docs/host-adapters.md. The consumer seam
is codex_adapter.parse_exec_lines / ingest_exec_stream.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from codex_adapter import (
    PARSER_VERSION,
    ingest_exec_stream,
    parse_exec_lines,
)
from contract_eval import validate_events
from event_store import EventStore

INSTALLATION = "inst_r12b_test"
DEVICE = "device_r12b_test"

THREAD_ID = "0199a213-81c0-7800-8aa1-bbab2a035a53"


def _fixture_lines() -> list[str]:
    rows = [
        {"type": "thread.started", "thread_id": THREAD_ID},
        {"type": "turn.started"},
        {
            "type": "item.started",
            "item": {
                "id": "item_1",
                "type": "command_execution",
                "command": "bash -lc echo sbtd-r12b",
                "aggregated_output": "",
                "exit_code": None,
                "status": "in_progress",
            },
        },
        {
            "type": "item.completed",
            "item": {
                "id": "item_1",
                "type": "command_execution",
                "command": "bash -lc echo sbtd-r12b",
                "aggregated_output": "sbtd-r12b\n",
                "exit_code": 0,
                "status": "completed",
            },
        },
        {
            "type": "item.started",
            "item": {
                "id": "item_2",
                "type": "mcp_tool_call",
                "server": "docs",
                "tool": "search",
                "arguments": {"q": "exec --json"},
                "result": None,
                "error": None,
                "status": "in_progress",
            },
        },
        {
            "type": "item.completed",
            "item": {
                "id": "item_2",
                "type": "mcp_tool_call",
                "server": "docs",
                "tool": "search",
                "arguments": {"q": "exec --json"},
                "result": {"content": [{"type": "text", "text": "Found 3 matches."}]},
                "error": None,
                "status": "completed",
            },
        },
        {
            "type": "item.completed",
            "item": {
                "id": "item_3",
                "type": "file_change",
                "changes": [{"path": "a.md", "kind": "add"}],
                "status": "failed",
            },
        },
        {
            "type": "item.updated",
            "item": {"id": "item_4", "type": "todo_list", "items": []},
        },
        {
            "type": "item.completed",
            "item": {"id": "item_5", "type": "brand_new_widget", "status": "completed"},
        },
        {
            "type": "turn.completed",
            "usage": {
                "input_tokens": 100,
                "cached_input_tokens": 10,
                "output_tokens": 5,
                "reasoning_output_tokens": 2,
            },
        },
        '{"type": "item.completed", "item": {"id": "item_6"',
    ]
    return [json.dumps(row, ensure_ascii=False) for row in rows[:-1]] + [rows[-1]]


class ParseExecLinesTests(unittest.TestCase):
    def parse(self):
        return parse_exec_lines(
            _fixture_lines(),
            installation_id=INSTALLATION,
            device_id=DEVICE,
            segment_id="capture-1",
        )

    def test_command_execution_maps_to_invocation_pair(self) -> None:
        outcome = self.parse()
        started = [e for e in outcome.events if e["event_type"] == "invocation.started"]
        finished = [
            e for e in outcome.events if e["event_type"] == "invocation.finished"
        ]
        self.assertEqual(len(started), 2)
        self.assertEqual(len(finished), 3)
        command = [e for e in started if e["correlation"]["invocation_id"] == "item_1"]
        self.assertEqual(
            command[0]["component"],
            {
                "component_id": "tool:command_execution",
                "kind": "tool",
                "name": "command_execution",
            },
        )
        self.assertEqual(command[0]["scope"]["session_id"], THREAD_ID)
        self.assertEqual(command[0]["host"]["host_kind"], "codex")
        done = [e for e in finished if e["correlation"]["invocation_id"] == "item_1"]
        self.assertEqual(done[0]["state"]["current"], "succeeded")
        self.assertEqual(done[0]["extensions"], {"exit_code": 0})

    def test_mcp_tool_call_maps_to_mcp_component(self) -> None:
        outcome = self.parse()
        mcp = [
            e
            for e in outcome.events
            if e["event_type"] == "invocation.started"
            and e["correlation"]["invocation_id"] == "item_2"
        ]
        self.assertEqual(mcp[0]["component"]["kind"], "mcp")
        self.assertEqual(mcp[0]["component"]["component_id"], "mcp:docs.search")
        self.assertEqual(mcp[0]["component"]["name"], "search")

    def test_status_mapping(self) -> None:
        outcome = self.parse()
        finished = {
            e["correlation"]["invocation_id"]: e
            for e in outcome.events
            if e["event_type"] == "invocation.finished"
        }
        self.assertEqual(finished["item_1"]["state"]["current"], "succeeded")
        self.assertEqual(finished["item_2"]["state"]["current"], "succeeded")
        self.assertEqual(finished["item_3"]["state"]["current"], "failed")

    def test_no_timestamps_are_fabricated(self) -> None:
        outcome = self.parse()
        for event in outcome.events:
            self.assertIsNone(event["occurred_at"])
            self.assertTrue(event["recorded_at"])

    def test_non_item_and_unknown_lines_are_skipped_and_counted(self) -> None:
        outcome = self.parse()
        self.assertEqual(outcome.records_read, 11)
        # turn.started, item.updated, unknown item type, turn.completed, bad tail
        self.assertEqual(outcome.records_skipped, 5)
        self.assertEqual(len(outcome.events), 5)

    def test_all_events_pass_the_r1_schema(self) -> None:
        outcome = self.parse()
        self.assertTrue(outcome.events)
        validate_events(outcome.events)

    def test_source_event_ids_pair_phases(self) -> None:
        outcome = self.parse()
        ids = {e["provenance"]["source_event_id"] for e in outcome.events}
        self.assertIn("item_1:started", ids)
        self.assertIn("item_1:completed", ids)

    def test_unobserved_start_means_no_fabricated_previous_state(self) -> None:
        outcome = self.parse()
        orphan = [
            e
            for e in outcome.events
            if e["event_type"] == "invocation.finished"
            and e["correlation"]["invocation_id"] == "item_3"
        ]
        self.assertIsNone(orphan[0]["state"]["previous"])

    def test_cli_rejects_empty_identity_without_traceback(self) -> None:
        from io import StringIO
        from unittest.mock import patch

        from codex_adapter import main

        stdout = StringIO()
        with patch("sys.stdout", stdout):
            code = main(
                [
                    "--runtime-home",
                    "/tmp/unused-r12b",
                    "--installation-id",
                    "",
                    "--device-id",
                    "dev1",
                    "--file",
                    "/tmp/nonexistent-r12b.jsonl",
                ]
            )
        self.assertEqual(code, 2)
        self.assertIn("error", stdout.getvalue())

    def test_events_do_not_carry_commands_or_outputs(self) -> None:
        outcome = self.parse()
        for event in outcome.events:
            blob = json.dumps(event)
            self.assertNotIn("bash -lc", blob)
            self.assertNotIn("aggregated_output", blob)


class IngestExecStreamTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name) / "runtime"
        self.home.mkdir(mode=0o700)
        (self.home / "config.json").write_text(
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

    def test_ingest_accepts_and_second_run_confirms(self) -> None:
        with EventStore.open(self.home, confirmed=True) as store:
            receipt = ingest_exec_stream(
                store,
                _fixture_lines(),
                installation_id=INSTALLATION,
                device_id=DEVICE,
                segment_id="capture-1",
            )
            self.assertEqual(receipt.host_kind, "codex")
            self.assertEqual(receipt.parser_version, PARSER_VERSION)
            self.assertEqual(receipt.events_emitted, 5)
            self.assertEqual(receipt.accepted, 5)
            again = ingest_exec_stream(
                store,
                _fixture_lines(),
                installation_id=INSTALLATION,
                device_id=DEVICE,
                segment_id="capture-1",
            )
            self.assertEqual(again.accepted, 0)
            self.assertEqual(again.duplicate, 5)
            self.assertEqual(len(store.replay()), 5)

    def test_missing_host_version_is_reported(self) -> None:
        with EventStore.open(self.home, confirmed=True) as store:
            receipt = ingest_exec_stream(
                store,
                _fixture_lines(),
                installation_id=INSTALLATION,
                device_id=DEVICE,
                segment_id="capture-1",
            )
            # exec JSONL carries no host version; the caller passes it.
            self.assertEqual(receipt.host_version, "unknown")


if __name__ == "__main__":
    unittest.main()
