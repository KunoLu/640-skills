"""R1.2a local event store, dedup, spool, checkpoint, and quality records.

Scenario text lives in spec/r1.2a-event-store-scenarios.md. This repository
does not create .feature files. The consumer seam is EventStore.
"""

from __future__ import annotations

import inspect
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from event_store import EventStore, StoreError


def _event(
    event_id: str,
    source_event_id: str | None,
    occurred_at: str,
    **changes: object,
) -> dict:
    event = {
        "schema_version": "1.0",
        "event_id": event_id,
        "event_type": "task.created",
        "occurred_at": occurred_at,
        "recorded_at": "2026-10-16T00:00:00Z",
        "ingest_seq": 0,
        "installation_id": "inst_r12a",
        "device_id": "device_r12a",
        "actor": {
            "actor_id": None,
            "kind": "agent",
            "identity_assurance": "unbound",
        },
        "scope": {
            "tenant_id": None,
            "workspace_id": None,
            "project_id": "project_a",
            "repository_id": "repo_a",
            "worktree_id": "wt_a",
            "task_uid": "task_leaf",
            "logical_task_id": "demo/leaf",
            "task_run_id": None,
        },
        "provenance": {
            "source_kind": "runtime-instrumented",
            "source_id": "source_runtime",
            "source_event_id": source_event_id,
            "producer_version": "0.1.0",
            "observation_level": "execution-observed",
            "evidence_status": "present",
            "parser_version": "parser-1",
        },
        "privacy": {
            "classification": "local-metadata",
            "redaction_policy_version": "1",
            "exportable": True,
        },
        "external_refs": [],
        "extensions": {},
    }
    event.update(changes)
    return event


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


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _truncate_tail():
    real = EventStore._write_ready

    def truncate(self, segment_id, events):
        path, _ = real(self, segment_id, events)
        size = path.stat().st_size
        with path.open("r+b") as handle:
            handle.truncate(max(0, size - 8))
            handle.flush()
            os.fsync(handle.fileno())
        raise StoreError("spool tail truncated before commit")

    return patch.object(EventStore, "_write_ready", truncate)


def _stop_after_first():
    real = EventStore._commit_event
    seen = {"count": 0}

    def stop(self, event, segment_id, offset):
        seen["count"] += 1
        if seen["count"] > 1:
            raise StoreError("commit interrupted before the batch finished")
        return real(self, event, segment_id, offset)

    return patch.object(EventStore, "_commit_event", stop)


class EventStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="sbtd-r12a-")
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "runtime-home"

    def _open(self) -> EventStore:
        _enable(self.home)
        store = EventStore.open(self.home, confirmed=True)
        self.addCleanup(store.close)
        return store

    def test_switch_off_creates_no_store_or_spool(self) -> None:
        missing = self.home
        with self.assertRaises(StoreError):
            EventStore.open(missing, confirmed=True)
        self.assertFalse(missing.exists())
        self.home.mkdir(mode=0o700)
        (self.home / "config.json").write_text(
            json.dumps({"schema_version": 1, "observation": {"enabled": False}}) + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(StoreError):
            EventStore.open(self.home, confirmed=True)
        self.assertFalse((self.home / "audit.db").exists())
        self.assertFalse((self.home / "spool").exists())

        (self.home / "config.json").write_text("{", encoding="utf-8")
        with self.assertRaises(StoreError):
            EventStore.open(self.home, confirmed=True)
        self.assertFalse((self.home / "audit.db").exists())
        self.assertFalse((self.home / "spool").exists())

    def test_unconfirmed_and_symlink_home_create_nothing(self) -> None:
        _enable(self.home)
        with self.assertRaises(StoreError):
            EventStore.open(self.home, confirmed=False)
        self.assertFalse((self.home / "audit.db").exists())
        self.assertFalse((self.home / "spool").exists())

        real = self.home.parent / "real-home"
        real.mkdir()
        (real / "notes.txt").write_text("keep", encoding="utf-8")
        link = self.home.parent / "home-link"
        link.symlink_to(real, target_is_directory=True)
        with self.assertRaises(StoreError):
            EventStore.open(link, confirmed=True)
        self.assertEqual((real / "notes.txt").read_text(encoding="utf-8"), "keep")
        self.assertFalse((real / "audit.db").exists())
        self.assertFalse((real / "spool").exists())

    def test_append_signature_has_no_fault(self) -> None:
        self.assertNotIn("fault", inspect.signature(EventStore.append).parameters)

    def test_replay_confirms_same_content_without_counting_twice(self) -> None:
        store = self._open()
        original = _event("evt_1", "native_1", "2026-10-16T01:00:00Z")
        first = store.append([original])
        second = store.append([original])
        third = store.append([dict(original, event_id="evt_1b", ingest_seq=9)])
        self.assertEqual([item.status for item in first.outcomes], ["accepted"])
        self.assertEqual([item.status for item in second.outcomes], ["duplicate"])
        self.assertEqual([item.status for item in third.outcomes], ["duplicate"])
        replayed = store.replay()
        self.assertEqual([item["event_id"] for item in replayed], ["evt_1"])
        self.assertEqual(store.quality().accepted, 1)
        self.assertEqual(store.quality().duplicate, 2)
        self.assertGreater(store.checkpoints()[0].offset, 0)
        self.assertEqual(store.checkpoints()[0].parser_version, "parser-1")
        self.assertNotIn("/", store.checkpoints()[0].source_instance)

    def test_same_source_key_with_different_content_conflicts(self) -> None:
        store = self._open()
        original = _event("evt_1", "native_1", "2026-10-16T01:00:00Z")
        store.append([original])
        conflict = _event(
            "evt_2",
            "native_1",
            "2026-10-16T01:00:00Z",
            extensions={"note": "different"},
        )
        result = store.append([conflict])
        self.assertEqual([item.status for item in result.outcomes], ["conflict"])
        replayed = store.replay()
        self.assertEqual([item["event_id"] for item in replayed], ["evt_1"])
        self.assertEqual(replayed[0]["extensions"], {})
        self.assertEqual(store.quality().conflict, 1)

    def test_out_of_order_events_stay_in_ingest_order(self) -> None:
        store = self._open()
        later = _event("evt_later", "native_later", "2026-10-16T03:00:00Z")
        earlier = _event("evt_earlier", "native_earlier", "2026-10-16T01:00:00Z")
        store.append([later])
        store.append([earlier])
        replayed = store.replay()
        self.assertEqual(
            [item["event_id"] for item in replayed], ["evt_later", "evt_earlier"]
        )
        self.assertEqual(
            [item["occurred_at"] for item in replayed],
            ["2026-10-16T03:00:00Z", "2026-10-16T01:00:00Z"],
        )
        self.assertEqual(store.quality().accepted, 2)

    def test_truncated_spool_tail_is_not_invented(self) -> None:
        store = self._open()
        first = _event("evt_keep", "native_keep", "2026-10-16T01:00:00Z")
        second = _event("evt_cut", "native_cut", "2026-10-16T01:05:00Z")
        with _truncate_tail(), self.assertRaises(StoreError):
            store.append([first, second])
        recovered = EventStore.open(self.home, confirmed=True)
        replayed = recovered.replay()
        self.assertEqual([item["event_id"] for item in replayed], ["evt_keep"])
        self.assertNotIn("evt_cut", [item["event_id"] for item in replayed])
        self.assertGreaterEqual(recovered.quality().truncated, 1)

    def test_damaged_database_is_not_replaced(self) -> None:
        store = self._open()
        store.append([_event("evt_1", "native_1", "2026-10-16T01:00:00Z")])
        store.close()
        database = self.home / "audit.db"
        database.write_bytes(database.read_bytes()[:8])
        damaged = database.read_bytes()
        with self.assertRaises(StoreError):
            EventStore.open(self.home, confirmed=True)
        self.assertEqual(database.read_bytes(), damaged)
        with self.assertRaises(StoreError):
            EventStore.open(self.home, confirmed=True)
        self.assertEqual(database.read_bytes(), damaged)

    def test_crash_before_commit_recovers_once(self) -> None:
        _enable(self.home)
        event = _event("evt_crash", "native_crash", "2026-10-16T01:00:00Z")
        payload = self.home / "pending-event.json"
        payload.write_text(json.dumps(event), encoding="utf-8")
        child = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                (
                    "import json, os, sys\n"
                    "from pathlib import Path\n"
                    "from unittest.mock import patch\n"
                    "sys.path.insert(0, sys.argv[1])\n"
                    "from event_store import EventStore\n"
                    "home = Path(sys.argv[2])\n"
                    "event = json.loads(Path(sys.argv[3]).read_text(encoding='utf-8'))\n"
                    "store = EventStore.open(home, confirmed=True)\n"
                    "def crash(self, event, segment_id, offset):\n"
                    "    os._exit(91)\n"
                    "with patch.object(EventStore, '_commit_event', crash):\n"
                    "    store.append([event])\n"
                ),
                str(ROOT),
                str(self.home),
                str(payload),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(child.returncode, 91, child.stderr)
        recovered = EventStore.open(self.home, confirmed=True)
        self.assertEqual(
            [item["event_id"] for item in recovered.replay()], ["evt_crash"]
        )
        again = EventStore.open(self.home, confirmed=True)
        self.assertEqual([item["event_id"] for item in again.replay()], ["evt_crash"])
        self.assertEqual(again.quality().accepted, 1)

    def test_partial_commit_does_not_report_the_rest_accepted(self) -> None:
        store = self._open()
        first = _event("evt_done", "native_done", "2026-10-16T01:00:00Z")
        second = _event("evt_left", "native_left", "2026-10-16T01:05:00Z")
        with _stop_after_first(), self.assertRaises(StoreError) as caught:
            store.append([first, second])
        self.assertNotIn("accepted=2", str(caught.exception))
        ready = list((self.home / "spool").glob("*.ready"))
        self.assertEqual(len(ready), 1)
        self.assertLess(store.checkpoints()[0].offset, ready[0].stat().st_size)
        self.assertEqual(store.quality().pending, 1)
        self.assertEqual([item["event_id"] for item in store.replay()], ["evt_done"])
        recovered = EventStore.open(self.home, confirmed=True)
        self.assertEqual(
            [item["event_id"] for item in recovered.replay()],
            ["evt_done", "evt_left"],
        )
        self.assertEqual(recovered.quality().accepted, 2)
        self.assertEqual(recovered.quality().duplicate, 0)

    def test_invalid_event_is_rejected_and_unlinked_stays_unlinked(self) -> None:
        store = self._open()
        secret = _event("evt_secret", "native_secret", "2026-10-16T01:00:00Z")
        secret["api_key"] = "do-not-store"
        rejected = store.append([secret])
        self.assertEqual([item.status for item in rejected.outcomes], ["rejected"])
        self.assertEqual(store.replay(), [])
        unlinked = _event("evt_free", "native_free", "2026-10-16T01:10:00Z")
        unlinked["scope"] = dict(unlinked["scope"], task_uid=None, logical_task_id=None)
        store.append([unlinked])
        replayed = store.replay()
        self.assertIsNone(replayed[0]["scope"]["task_uid"])
        self.assertEqual(store.quality().unlinked, 1)
        self.assertEqual(store.quality().rejected, 1)
        self.assertEqual(_mode(self.home / "audit.db"), 0o600)
        self.assertEqual(_mode(self.home / "spool"), 0o700)

    def test_segment_digest_key_does_not_invent_a_second_conflict_rule(self) -> None:
        store = self._open()
        first = _event("evt_seg", None, "2026-10-16T01:00:00Z")
        first["provenance"] = dict(
            first["provenance"],
            source_event_id=None,
            segment_id="seg-a",
            offset=4,
        )
        changed = _event("evt_seg_b", None, "2026-10-16T01:00:00Z")
        changed["provenance"] = dict(first["provenance"])
        changed["extensions"] = {"note": "other-digest"}
        store.append([first])
        result = store.append([changed])
        self.assertEqual([item.status for item in result.outcomes], ["accepted"])
        self.assertEqual(len(store.replay()), 2)

    def test_checkpoint_ignores_mtime(self) -> None:
        store = self._open()
        store.append([_event("evt_1", "native_1", "2026-10-16T01:00:00Z")])
        offset = store.checkpoints()[0].offset
        os.utime(self.home / "audit.db", (0, 0))
        reopened = EventStore.open(self.home, confirmed=True)
        self.assertEqual(reopened.checkpoints()[0].offset, offset)
        self.assertGreater(offset, 0)

    def test_foreign_spool_file_is_not_ingested(self) -> None:
        store = self._open()
        store.close()
        spool = self.home / "spool"
        spool.mkdir(mode=0o700, exist_ok=True)
        foreign = spool / "foreign.jsonl"
        foreign.write_text(
            json.dumps(_event("evt_foreign", "native_foreign", "2026-10-16T01:00:00Z"))
            + "\n",
            encoding="utf-8",
        )
        reopened = EventStore.open(self.home, confirmed=True)
        self.assertEqual(reopened.replay(), [])
        self.assertTrue(foreign.is_file())

    def test_read_only_open_does_not_create_or_append(self) -> None:
        _enable(self.home)
        with self.assertRaises(StoreError):
            EventStore.open(self.home, confirmed=True, read_only=True)
        self.assertFalse((self.home / "audit.db").exists())
        store = EventStore.open(self.home, confirmed=True)
        store.append([_event("evt_1", "native_1", "2026-10-16T01:00:00Z")])
        store.close()
        reader = EventStore.open(self.home, confirmed=True, read_only=True)
        self.assertEqual([item["event_id"] for item in reader.replay()], ["evt_1"])
        with self.assertRaises(StoreError):
            reader.append([_event("evt_2", "native_2", "2026-10-16T01:05:00Z")])
        self.assertEqual([item["event_id"] for item in reader.replay()], ["evt_1"])

    def test_extension_secret_is_not_persisted(self) -> None:
        store = self._open()
        for name, key in (("evt_secret", "api_key"), ("evt_camel", "clientSecret")):
            secret = _event(name, f"native_{name}", "2026-10-16T01:00:00Z")
            secret["extensions"] = {key: "do-not-store"}
            result = store.append([secret])
            self.assertEqual([item.status for item in result.outcomes], ["rejected"])
        self.assertEqual(store.replay(), [])
        leaked = [
            path
            for path in self.home.rglob("*")
            if path.is_file() and b"do-not-store" in path.read_bytes()
        ]
        self.assertEqual(leaked, [])

    def test_foreign_ready_spool_is_not_recovered(self) -> None:
        store = self._open()
        first = _event("evt_keep", "native_keep", "2026-10-16T01:00:00Z")
        second = _event("evt_left", "native_left", "2026-10-16T01:05:00Z")
        with _stop_after_first(), self.assertRaises(StoreError):
            store.append([first, second])
        ready = next((self.home / "spool").glob("*.ready"))
        other = self.home.parent / "other-home"
        _enable(other)
        other_store = EventStore.open(other, confirmed=True)
        self.addCleanup(other_store.close)
        other_spool = other / "spool"
        other_spool.mkdir(mode=0o700, exist_ok=True)
        copied = other_spool / ready.name
        copied.write_bytes(ready.read_bytes())
        other_store.close()
        recovered = EventStore.open(other, confirmed=True)
        self.assertEqual(recovered.replay(), [])
        self.assertEqual(recovered.quality().pending, 0)
        self.assertTrue(copied.is_file())

    def test_question_mark_in_home_can_reopen(self) -> None:
        home = self.home.parent / "home?q"
        _enable(home)
        store = EventStore.open(home, confirmed=True)
        self.addCleanup(store.close)
        store.append([_event("evt_q", "native_q", "2026-10-16T01:00:00Z")])
        store.close()
        reopened = EventStore.open(home, confirmed=True)
        self.assertEqual([item["event_id"] for item in reopened.replay()], ["evt_q"])


if __name__ == "__main__":
    unittest.main()
