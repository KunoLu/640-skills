"""R1.3 history read paths: event listing, task history, cursor pagination.

Scenario text lives in spec/r1.3-stats-api-scenarios.md. Reads go through
EventStore.replay(); append and dedup semantics are unchanged.
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

from event_store import EventStore
from history_read import (
    CursorError,
    list_events,
    paginate,
    task_history,
)

GOLDEN = ROOT / "golden"


def _dataset() -> dict:
    return json.loads((GOLDEN / "dataset.json").read_text(encoding="utf-8"))


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


class ListEventsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.events = _dataset()["events"]

    def test_filter_by_task_uid(self) -> None:
        rows = list_events(self.events, task_uid="task_leaf")
        self.assertTrue(rows)
        for event in rows:
            self.assertEqual(event["scope"].get("task_uid"), "task_leaf")

    def test_window_is_half_open(self) -> None:
        at_to = list_events(
            self.events,
            from_at="2026-10-15T15:00:00Z",
            to_at="2026-10-15T15:30:00Z",
        )
        ids = {event["event_id"] for event in at_to}
        self.assertNotIn("evt_run_leaf_1_start", ids)  # occurred exactly at to
        past_to = list_events(
            self.events,
            from_at="2026-10-15T15:00:00Z",
            to_at="2026-10-15T15:30:01Z",
        )
        self.assertIn("evt_run_leaf_1_start", {e["event_id"] for e in past_to})

    def test_event_type_filter(self) -> None:
        rows = list_events(self.events, event_types=["run.started"])
        self.assertEqual(len(rows), 6)
        for event in rows:
            self.assertEqual(event["event_type"], "run.started")

    def test_order_is_stable_by_ingest_seq(self) -> None:
        rows = list_events(self.events)
        seqs = [event["ingest_seq"] for event in rows]
        self.assertEqual(seqs, sorted(seqs))

    def test_unknown_time_events_are_listed_not_dropped(self) -> None:
        rows = list_events(self.events)
        self.assertIn("evt_created_untimed", {e["event_id"] for e in rows})
        windowed = list_events(
            self.events, from_at="2026-10-15T15:00:00Z", to_at="2026-10-16T15:00:00Z"
        )
        self.assertNotIn("evt_created_untimed", {e["event_id"] for e in windowed})


class PaginateTests(unittest.TestCase):
    def test_pages_cover_all_items_without_duplicates(self) -> None:
        items = [{"n": n} for n in range(25)]
        seen = []
        cursor = None
        while True:
            page = paginate(items, cursor=cursor, limit=10)
            seen.extend(item["n"] for item in page["items"])
            cursor = page["next_cursor"]
            if cursor is None:
                break
        self.assertEqual(seen, list(range(25)))
        self.assertEqual(page["total"], 25)

    def test_limit_is_clamped(self) -> None:
        items = [{"n": n} for n in range(5)]
        page = paginate(items, limit=10000)
        self.assertEqual(len(page["items"]), 5)
        self.assertIsNone(page["next_cursor"])

    def test_bad_cursor_is_rejected(self) -> None:
        with self.assertRaises(CursorError):
            paginate([{"n": 1}], cursor="%%%")
        with self.assertRaises(CursorError):
            paginate(
                [{"n": 1}], cursor=paginate([{"n": 1}] * 3, limit=1)["next_cursor"]
            )


class TaskHistoryTests(unittest.TestCase):
    def test_history_from_replayed_store_matches_in_memory(self) -> None:
        dataset = _dataset()
        temporary = tempfile.TemporaryDirectory(prefix="sbtd-r13-")
        self.addCleanup(temporary.cleanup)
        home = Path(temporary.name) / "runtime-home"
        _enable(home)
        store = EventStore.open(home, confirmed=True)
        self.addCleanup(store.close)
        store.append(dataset["events"])
        replayed = store.replay()

        from_store = task_history(replayed, "task_leaf")
        from_memory = task_history(dataset["events"], "task_leaf")
        self.assertEqual(
            [e["event_id"] for e in from_store["events"]],
            [e["event_id"] for e in from_memory["events"]],
        )

    def test_history_includes_state_and_mode_events(self) -> None:
        history = task_history(_dataset()["events"], "task_leaf")
        types = {event["event_type"] for event in history["events"]}
        self.assertIn("task.created", types)
        self.assertIn("task.state_changed", types)
        self.assertIn("task.reopened", types)
        self.assertIn("mode.kept", types)
        self.assertEqual(history["latest_status"], "done")

    def test_history_excludes_other_tasks(self) -> None:
        history = task_history(_dataset()["events"], "task_leaf")
        for event in history["events"]:
            self.assertEqual(event["scope"].get("task_uid"), "task_leaf")


if __name__ == "__main__":
    unittest.main()
