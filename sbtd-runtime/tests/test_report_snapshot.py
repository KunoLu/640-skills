"""R1.3 report snapshot: create/reuse, watermarks, dataset cursor pages.

Scenario text lives in spec/r1.3-stats-api-scenarios.md. One response family
(query, timeseries, dataset pages, CSV) shares one snapshot_id; pages never
mix snapshots.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from history_read import CursorError
from report_snapshot import (
    DATASET_FAMILIES,
    SnapshotGone,
    SnapshotNotFound,
    SnapshotStore,
)
from stats_query import query, timeseries

GOLDEN = ROOT / "golden"


def _dataset() -> dict:
    return json.loads((GOLDEN / "dataset.json").read_text(encoding="utf-8"))


def _scope(dataset: dict, **changes: object) -> dict:
    base = dataset["query_scope"]
    scope = {
        "schema_version": "1.0",
        "range": {
            "from": base["from"],
            "to": base["to"],
            "timezone": base["timezone"],
        },
        "filters": {},
        "task_granularity": base["task_granularity"],
        "include_unlinked": base["include_unlinked"],
        "include_unknown_time": base["include_unknown_time"],
        "metrics": ["tasks.touched", "tasks.created"],
    }
    for key, value in changes.items():
        scope[key] = value
    return scope


def _all_pages(store: SnapshotStore, snapshot_id: str, limit: int) -> list[dict]:
    rows = []
    cursor = None
    while True:
        page = store.dataset_page(snapshot_id, cursor=cursor, limit=limit)
        rows.extend(page["rows"])
        cursor = page["next_cursor"]
        if cursor is None:
            return rows


class SnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset = _dataset()
        self.scope = _scope(self.dataset)

    def test_same_scope_and_watermark_reuse_one_snapshot(self) -> None:
        store = SnapshotStore()
        first = store.create_or_reuse(self.dataset, self.scope)
        second = store.create_or_reuse(self.dataset, self.scope)
        self.assertEqual(first.snapshot_id, second.snapshot_id)

    def test_new_watermark_mints_a_new_snapshot_id(self) -> None:
        store = SnapshotStore()
        first = store.create_or_reuse(self.dataset, self.scope)
        changed = json.loads(json.dumps(self.dataset))
        extra = json.loads(json.dumps(changed["events"][0]))
        extra["event_id"] = "evt_late"
        extra["ingest_seq"] = 99999
        extra["occurred_at"] = "2026-10-16T00:00:00Z"
        extra["recorded_at"] = "2026-10-16T00:00:00Z"
        extra["provenance"]["source_event_id"] = "evt_late"
        changed["events"].append(extra)
        second = store.create_or_reuse(changed, self.scope)
        self.assertNotEqual(first.snapshot_id, second.snapshot_id)

    def test_store_appended_event_with_zero_payload_seq_mints_a_new_id(self) -> None:
        # Real producers build events with payload ingest_seq=0; the store
        # assigns the true sequence only in SQL, so replay() payloads keep 0.
        import os
        import tempfile

        from event_store import EventStore
        from host_adapter import base_event

        temporary = tempfile.TemporaryDirectory(prefix="sbtd-r13-wm-")
        self.addCleanup(temporary.cleanup)
        home = Path(temporary.name) / "runtime-home"
        home.mkdir(mode=0o700)
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

        def make_event(sid: str, at: str) -> dict:
            return base_event(
                event_type="task.state_changed",
                occurred_at=at,
                recorded_at=at,
                installation_id="inst_r13",
                device_id="device_r13",
                source_id="source_runtime",
                source_event_id=sid,
                parser_version="1",
                project_id="project_a",
                logical_task_id="demo/leaf",
                state={"previous": "planned", "current": "in-progress"},
            )

        store = EventStore.open(home, confirmed=True)
        self.addCleanup(store.close)
        store.append([make_event("e1", "2026-10-15T16:00:00Z")])
        snapshots = SnapshotStore()
        dataset = {"tasks": [], "events": store.replay()}
        scope = _scope(self.dataset)
        first = snapshots.create_or_reuse(dataset, scope)
        store.append([make_event("e2", "2026-10-15T17:00:00Z")])
        second = snapshots.create_or_reuse(
            {"tasks": [], "events": store.replay()}, scope
        )
        self.assertNotEqual(first.snapshot_id, second.snapshot_id)

    def test_filters_narrow_dataset_rows_not_only_metrics(self) -> None:
        store = SnapshotStore()
        scope = _scope(self.dataset)
        scope["filters"] = {"project_ids": ["project_b"]}
        snapshot = store.create_or_reuse(self.dataset, scope)
        event_rows = [row for row in snapshot.rows if row["record_type"] == "event"]
        self.assertEqual(event_rows, [])
        for row in snapshot.rows:
            project = row["fields"].get("project_id")
            self.assertIn(project, (None, "project_b"))

    def test_query_timeseries_dataset_share_one_snapshot_id(self) -> None:
        store = SnapshotStore()
        answer = query(self.dataset, self.scope, store=store)
        series = timeseries(self.dataset, self.scope, bucket_seconds=43200, store=store)
        self.assertEqual(answer["snapshot_id"], series["snapshot_id"])
        page = store.dataset_page(answer["snapshot_id"], limit=5)
        self.assertEqual(page["snapshot_id"], answer["snapshot_id"])

    def test_expired_snapshot_is_gone_and_never_recycled(self) -> None:
        store = SnapshotStore(ttl_seconds=0)
        first = store.create_or_reuse(self.dataset, self.scope)
        with self.assertRaises(SnapshotGone):
            store.get(first.snapshot_id)
        second = store.create_or_reuse(self.dataset, self.scope)
        self.assertNotEqual(first.snapshot_id, second.snapshot_id)

    def test_unknown_snapshot_is_not_found(self) -> None:
        store = SnapshotStore()
        with self.assertRaises(SnapshotNotFound):
            store.get("snapshot_missing")

    def test_cursor_from_another_snapshot_is_rejected(self) -> None:
        store = SnapshotStore()
        first = store.create_or_reuse(self.dataset, self.scope)
        other_scope = _scope(self.dataset, metrics=["tasks.created"])
        second = store.create_or_reuse(self.dataset, other_scope)
        page = store.dataset_page(first.snapshot_id, limit=1)
        with self.assertRaises(CursorError):
            store.dataset_page(second.snapshot_id, cursor=page["next_cursor"])

    def test_full_pagination_matches_the_manifest_without_gaps(self) -> None:
        store = SnapshotStore()
        snapshot = store.create_or_reuse(self.dataset, self.scope)
        rows = _all_pages(store, snapshot.snapshot_id, limit=7)
        keys = [(row["record_type"], row["record_id"]) for row in rows]
        self.assertEqual(len(keys), len(set(keys)))
        manifest = {
            item["record_type"]: item["rows"] for item in snapshot.dataset_manifest
        }
        self.assertEqual(len(rows), sum(manifest.values()))
        by_type: dict[str, int] = {}
        for row in rows:
            by_type[row["record_type"]] = by_type.get(row["record_type"], 0) + 1
        self.assertEqual(by_type, {k: v for k, v in manifest.items() if v})

    def test_manifest_lists_every_family_and_unknown_time_set(self) -> None:
        store = SnapshotStore()
        snapshot = store.create_or_reuse(self.dataset, self.scope)
        families = {item["record_type"] for item in snapshot.dataset_manifest}
        self.assertEqual(families, set(DATASET_FAMILIES))
        # evt_created_untimed has occurred_at null.
        self.assertIn("evt_created_untimed", snapshot.unknown_time_event_ids)
        self.assertGreater(snapshot.watermark_seq, 0)

    def test_bad_cursor_is_rejected(self) -> None:
        store = SnapshotStore()
        snapshot = store.create_or_reuse(self.dataset, self.scope)
        with self.assertRaises(CursorError):
            store.dataset_page(snapshot.snapshot_id, cursor="not-a-cursor")

    def test_snapshot_is_immutable_against_dataset_mutation(self) -> None:
        store = SnapshotStore()
        snapshot = store.create_or_reuse(self.dataset, self.scope)
        before = snapshot.snapshot_digest
        self.dataset["events"].clear()
        self.assertEqual(snapshot.snapshot_digest, before)


if __name__ == "__main__":
    unittest.main()
