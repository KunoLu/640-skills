"""Export job lifecycle; spec/r2.1a-export-scenarios.md.

Traces: in-flight snapshot pin, exports-only retention, immutable download
after restart, path and foreign-home refusal, and unpublished or corrupt
artifacts never becoming ready.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import tempfile
import threading
import time
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

from contract_eval import parse_instant
from export_store import (
    ExportGone,
    ExportNotFound,
    ExportNotReady,
    ExportStore,
)
from report_snapshot import SnapshotGone, SnapshotNotFound, SnapshotStore
from test_report_snapshot import _dataset, _scope

PUBLIC_FIELDS = {
    "export_id",
    "status",
    "format",
    "snapshot_id",
    "created_at",
    "ready_at",
    "expires_at",
    "mime_type",
    "byte_count",
    "byte_size",
    "sha256",
    "redaction_policy_version",
    "export_schema_version",
    "panel_manifest_version",
    "panel_ids",
    "dataset_manifest",
    "range_from",
    "range_to",
    "timezone",
    "warnings",
    "renderer_version",
    "error",
}


class ExportCancelled(Exception):
    """Same class name the renderer raises when cancelled() becomes true."""


def _presentation() -> dict:
    return {
        "theme": "dark",
        "report_width_px": 1440,
        "expanded_detail_ids": [],
        "table_sort": {},
        "preview_row_sets": {},
        "panel_order": ["data-quality", "task-lifecycle"],
        "legend_state": {"hidden": False},
    }


def _metadata(snapshot, **overrides) -> dict:
    meta = {
        "mime_type": "text/csv; charset=utf-8",
        "redaction_policy_version": "1",
        "export_schema_version": "1.1",
        "panel_manifest_version": "1.0.0",
        "panel_ids": ["data-quality", "task-lifecycle"],
        "dataset_manifest": [{"record_type": "task", "rows": 1}],
        "snapshot_id": "renderer-must-not-win",
        "range_from": snapshot.effective_from,
        "range_to": snapshot.effective_to,
        "timezone": snapshot.timezone,
        "warnings": ["覆盖不足"],
        "renderer_version": "test-renderer-1",
        "artifact_path": "/tmp/should-not-leak",
        "byte_size": 1,
    }
    meta.update(overrides)
    return meta


def _until(store: ExportStore, export_id: str, *, status: str = "ready") -> dict:
    deadline = time.monotonic() + 5
    last = None
    while time.monotonic() < deadline:
        last = store.get(export_id)
        if last["status"] == status:
            return last
        if status == "ready" and last["status"] in ("failed", "cancelled"):
            raise AssertionError(last)
        time.sleep(0.01)
    raise AssertionError(last)


class ExportStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="sbtd-export-")
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "runtime"
        self.dataset = _dataset()
        self.scope = _scope(self.dataset)
        self.snapshots = SnapshotStore(self.home)
        self.snapshot = self.snapshots.create_or_reuse(self.dataset, self.scope)
        self.calls: list[tuple] = []
        self.stores: list[ExportStore] = []
        self.addCleanup(self._close_stores)

    def _close_stores(self) -> None:
        for store in self.stores:
            store.close()

    def _renderer(self, payload: bytes = b"export-bytes", mime: str | None = None):
        def render(snapshot, format_name, presentation, cancelled):
            self.calls.append((format_name, copy.deepcopy(presentation), cancelled()))
            if cancelled():
                raise ExportCancelled("cancelled")
            meta = _metadata(snapshot)
            if mime is not None:
                meta["mime_type"] = mime
            elif format_name == "html":
                meta["mime_type"] = "text/html; charset=utf-8"
            return payload, meta

        return render

    def _open(
        self,
        renderer=None,
        home: Path | None = None,
        snapshots: SnapshotStore | None = None,
    ) -> ExportStore:
        store = ExportStore(
            home or self.home,
            snapshots or self.snapshots,
            renderer or self._renderer(),
        )
        self.stores.append(store)
        return store

    def _create(self, store: ExportStore, format_name: str = "csv", **kwargs) -> str:
        return store.create(
            self.snapshot.snapshot_id,
            format_name,
            kwargs.pop("presentation", _presentation()),
            **kwargs,
        )

    def test_ready_manifest_is_stable_across_download_and_restart(self) -> None:
        payload = "固定,bytes".encode()
        store = self._open(self._renderer(payload))
        export_id = self._create(store, idempotency_key="keep")
        info = _until(store, export_id)
        first, downloaded = store.download(export_id)
        again, _repeated = store.download(export_id)
        self.assertEqual(set(info), PUBLIC_FIELDS)
        self.assertEqual(first, payload)
        self.assertEqual(again, payload)
        self.assertEqual(downloaded["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(len(downloaded["sha256"]), 64)
        self.assertEqual(downloaded["byte_count"], len(payload))
        self.assertEqual(downloaded["byte_size"], len(payload))
        self.assertEqual(downloaded["snapshot_id"], self.snapshot.snapshot_id)
        self.assertEqual(downloaded["format"], "csv")
        self.assertEqual(downloaded["mime_type"], "text/csv; charset=utf-8")
        self.assertEqual(downloaded["warnings"], ["覆盖不足"])
        self.assertEqual(downloaded["redaction_policy_version"], "1")
        self.assertEqual(downloaded["export_schema_version"], "1.1")
        self.assertNotIn(str(self.home), json.dumps(downloaded))
        self.assertNotIn("should-not-leak", json.dumps(downloaded))
        self.assertNotIn("keep", json.dumps(downloaded))
        ready = parse_instant(info["ready_at"])
        expires = parse_instant(info["expires_at"])
        self.assertEqual(expires - ready, timedelta(seconds=86400))
        self.assertEqual(store.get(export_id)["expires_at"], info["expires_at"])
        names = sorted(path.name for path in (self.home / "exports").iterdir())
        self.assertEqual(names, [f"{export_id}.bin", f"{export_id}.json"])
        manifest = (self.home / "exports" / f"{export_id}.json").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(str(self.home), manifest)
        store.close()
        calls_before = len(self.calls)
        restored = self._open(self._renderer(b"regenerated"))
        second, info2 = restored.download(export_id)
        self.assertEqual(second, payload)
        self.assertEqual(info2["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(info2["expires_at"], info["expires_at"])
        self.assertEqual(info2["ready_at"], info["ready_at"])
        self.assertEqual(info2["byte_count"], len(payload))
        self.assertEqual(len(self.calls), calls_before)
        self.assertEqual(
            restored.create(
                self.snapshot.snapshot_id,
                "csv",
                _presentation(),
                idempotency_key="keep",
            ),
            export_id,
        )
        self.assertEqual(len(self.calls), calls_before)

    def test_pin_precedes_render_and_releases_on_each_terminal_state(self) -> None:
        home = Path(self.temporary.name) / "pin-home"
        now = datetime.now(UTC)
        snapshots = SnapshotStore(home, ttl_seconds=86400)
        snapshot = snapshots.create_or_reuse(self.dataset, self.scope, now=now)
        expired = now + timedelta(days=1)
        order: list[str] = []

        class Recording:
            def pin(self, snapshot_id: str, **kwargs):
                order.append("pin")
                return snapshots.pin(snapshot_id, **kwargs)

            def release(self, snapshot_id: str) -> None:
                order.append("release")
                snapshots.release(snapshot_id)

        entered = threading.Event()

        def renderer(snapshot_obj, format_name, presentation, cancelled):
            order.append("render")
            entered.set()
            while not cancelled():
                time.sleep(0.005)
            raise ExportCancelled("cancelled")

        store = self._open(renderer, home, Recording())
        export_id = store.create(snapshot.snapshot_id, "csv", _presentation())
        self.assertTrue(entered.wait(5))
        self.assertLess(order.index("pin"), order.index("render"))
        self.assertEqual(snapshots.sweep(now=expired), [])
        self.assertEqual(
            snapshots.get(snapshot.snapshot_id, now=expired).snapshot_id,
            snapshot.snapshot_id,
        )
        queued = store.get(export_id)
        self.assertEqual(queued["export_id"], export_id)
        self.assertIn(queued["status"], ("queued", "generating"))
        self.assertIsNone(queued["expires_at"])
        self.assertIsNone(queued["sha256"])
        self.assertIn("expires_at", queued)
        store.delete(export_id)
        info = store.get(export_id)
        self.assertEqual(info["status"], "cancelled")
        self.assertNotEqual(info["status"], "ready")
        with self.assertRaises(ExportNotReady):
            store.download(export_id)
        self.assertEqual(snapshots.sweep(now=expired), [snapshot.snapshot_id])
        self.assertIn("release", order)

        failed_home = Path(self.temporary.name) / "fail-home"
        failed_snapshots = SnapshotStore(failed_home, ttl_seconds=86400)
        failed_snapshot = failed_snapshots.create_or_reuse(
            self.dataset, self.scope, now=now
        )

        def explode(snapshot_obj, format_name, presentation, cancelled):
            raise OSError(f"disk full at {failed_home}/exports/secret")

        failed = self._open(explode, failed_home, failed_snapshots)
        failed_id = failed.create(failed_snapshot.snapshot_id, "html", _presentation())
        info = _until(failed, failed_id, status="failed")
        self.assertEqual(info["error"], "export failed")
        self.assertNotIn(str(failed_home), json.dumps(info))
        with self.assertRaises(ExportNotReady):
            failed.download(failed_id)
        self.assertFalse((failed_home / "exports" / f"{failed_id}.json").exists())
        failed.close()
        self.assertEqual(
            failed_snapshots.sweep(now=expired), [failed_snapshot.snapshot_id]
        )

    def test_two_jobs_hold_the_snapshot_until_each_releases(self) -> None:
        home = Path(self.temporary.name) / "two-pin"
        now = datetime.now(UTC)
        snapshots = SnapshotStore(home, ttl_seconds=86400)
        snapshot = snapshots.create_or_reuse(self.dataset, self.scope, now=now)
        expired = now + timedelta(days=1)
        entered = threading.Event()
        release = threading.Event()

        def renderer(snapshot_obj, format_name, presentation, cancelled):
            if not entered.is_set():
                entered.set()
                while not release.is_set() and not cancelled():
                    time.sleep(0.005)
            if cancelled():
                raise ExportCancelled("cancelled")
            return b"one", _metadata(snapshot_obj)

        store = self._open(renderer, home, snapshots)
        first = store.create(snapshot.snapshot_id, "csv", _presentation())
        self.assertTrue(entered.wait(5))
        second = store.create(snapshot.snapshot_id, "html", _presentation())
        self.assertEqual(snapshots.sweep(now=expired), [])
        release.set()
        _until(store, first)
        _until(store, second)
        store.close()
        self.assertEqual(snapshots.sweep(now=expired), [snapshot.snapshot_id])

    def test_sweep_and_startup_touch_only_verified_expired_exports(self) -> None:
        payload = b"live-export"
        store = self._open(self._renderer(payload))
        live_id = self._create(store)
        live = _until(store, live_id)
        past = datetime(2020, 1, 1, tzinfo=UTC)
        with mock.patch("export_store._now", return_value=past):
            expired_store = self._open(self._renderer(b"expired-export"))
            expired_id = self._create(expired_store)
            _until(expired_store, expired_id)
            expired_store.close()
        exports = self.home / "exports"
        expired_snapshot = self.snapshots.create_or_reuse(
            self.dataset,
            _scope(self.dataset, metrics=["tasks.created"]),
            now=datetime.now(UTC) - timedelta(days=3),
        )
        outside = self.home.parent / "source"
        sentinels = [
            self.home / "snapshots" / f"{self.snapshot.snapshot_id}.json",
            self.home / "snapshots" / f"{expired_snapshot.snapshot_id}.json",
            self.home / "audit.db",
            self.home / "config.json",
            self.home / "registry.json",
            self.home / "spool" / "audit.ready",
            self.home / "backups" / "audit.db",
            outside / "task.md",
            outside / "report.json",
            outside / "handoff.md",
            exports / "unknown.txt",
            exports / ".export-interrupted.tmp",
            exports / "nested" / f"{expired_id}.bin",
            exports / ("exp_" + "a" * 32 + ".json"),
            exports / f"{live_id}.bin",
            exports / f"{live_id}.json",
        ]
        for path in sentinels:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_bytes(b"preserve exactly")
        expected = {path: path.read_bytes() for path in sentinels}
        link_target = outside / "linked-target"
        link = None
        if os.name == "posix":
            link_target.write_bytes(b"linked-bytes")
            link = exports / "linked-out"
            link.symlink_to(link_target)
        removed = store.sweep(now=parse_instant(live["expires_at"]))
        self.assertEqual(removed, [live_id])
        self.assertFalse((exports / f"{live_id}.bin").exists())
        self.assertFalse((exports / f"{live_id}.json").exists())
        for path, content in expected.items():
            if path.name.startswith(live_id):
                continue
            self.assertEqual(path.read_bytes(), content, str(path))
        if link is not None:
            self.assertTrue(link.is_symlink())
            self.assertEqual(link_target.read_bytes(), b"linked-bytes")
        with self.assertRaises(ExportGone):
            store.get(live_id)
        store.close()
        restarted = self._open(self._renderer(b"must-not-render"))
        with self.assertRaises(ExportNotFound):
            restarted.get(live_id)
        self.assertFalse((exports / f"{expired_id}.json").exists())
        self.assertFalse((exports / f"{expired_id}.bin").exists())
        with self.assertRaises(ExportGone):
            restarted.get(expired_id)
        for path, content in expected.items():
            if path.name.startswith(live_id):
                continue
            self.assertEqual(path.read_bytes(), content, str(path))
        self.assertEqual(
            (exports / ".export-interrupted.tmp").read_bytes(), b"preserve exactly"
        )

    def test_download_does_not_extend_retention(self) -> None:
        store = self._open(self._renderer(b"same-bytes"))
        export_id = self._create(store)
        info = _until(store, export_id)
        expires = parse_instant(info["expires_at"])
        blob, _info = store.download(export_id)
        self.assertEqual(store.sweep(now=expires - timedelta(seconds=1)), [])
        self.assertEqual(store.download(export_id)[0], blob)
        self.assertEqual(store.get(export_id)["expires_at"], info["expires_at"])
        self.assertEqual(store.sweep(now=expires), [export_id])
        with self.assertRaises(ExportGone):
            store.download(export_id)

    def test_partial_and_corrupt_files_are_never_ready(self) -> None:
        payload = b"published-bytes"
        store = self._open(self._renderer(payload))
        export_id = self._create(store)
        _until(store, export_id)
        exports = self.home / "exports"
        artifact = exports / f"{export_id}.bin"
        manifest = exports / f"{export_id}.json"
        original_manifest = manifest.read_bytes()
        artifact.write_bytes(payload[:-1] or b"x")
        tampered = artifact.read_bytes()
        with self.assertRaises(ExportNotFound):
            store.get(export_id)
        with self.assertRaises(ExportNotFound):
            store.download(export_id)
        self.assertEqual(artifact.read_bytes(), tampered)
        self.assertEqual(manifest.read_bytes(), original_manifest)
        store.close()
        restarted = self._open(self._renderer(b"promoted"))
        with self.assertRaises(ExportNotFound):
            restarted.download(export_id)
        self.assertEqual(artifact.read_bytes(), tampered)
        self.assertEqual(restarted.sweep(now=datetime.now(UTC) + timedelta(days=3)), [])
        self.assertEqual(artifact.read_bytes(), tampered)

        planted_id = "exp_" + "ab" * 16
        planted = exports / f"{planted_id}.bin"
        planted.write_bytes(b"partial-only")
        truncated = exports / f"{'exp_' + 'cd' * 16}.json"
        truncated.write_bytes(b'{"format_version":1')
        self.assertEqual(truncated.read_bytes(), b'{"format_version":1')
        third = self._open(self._renderer(b"nope"))
        with self.assertRaises(ExportNotFound):
            third.download(planted_id)
        self.assertEqual(planted.read_bytes(), b"partial-only")
        self.assertEqual(truncated.read_bytes(), b'{"format_version":1')

        real = os.replace

        def fail_manifest(source, destination):
            if str(destination).endswith(".json"):
                raise OSError("interrupted before manifest")
            return real(source, destination)

        unknown = exports / ".export-interrupted.tmp"
        unknown.write_bytes(b"preserve exactly")
        interrupted = self._open(self._renderer(b"half-file"))
        with mock.patch("export_store.os.replace", side_effect=fail_manifest):
            interrupted_id = self._create(interrupted)
            info = _until(interrupted, interrupted_id, status="failed")
        self.assertNotEqual(info["status"], "ready")
        with self.assertRaises(ExportNotReady):
            interrupted.download(interrupted_id)
        self.assertFalse((exports / f"{interrupted_id}.json").exists())
        self.assertEqual(unknown.read_bytes(), b"preserve exactly")
        corrupted = original_manifest.replace(b"ready_at", b"ready_XX")
        manifest.write_bytes(corrupted)
        preserved = self._open(self._renderer(b"must-not-heal"))
        with self.assertRaises(ExportNotFound):
            preserved.get(export_id)
        self.assertEqual(manifest.read_bytes(), corrupted)

    def test_cancel_cleans_only_this_job(self) -> None:
        store = self._open(self._renderer(b"kept"))
        kept_id = self._create(store, "html")
        _until(store, kept_id)
        entered = threading.Event()

        def blocking(snapshot, format_name, presentation, cancelled):
            entered.set()
            while not cancelled():
                time.sleep(0.005)
            return b"should-not-publish", _metadata(snapshot)

        other = self._open(blocking)
        cancelled_id = self._create(other)
        self.assertTrue(entered.wait(5))
        unknown = self.home / "exports" / "unknown.txt"
        unknown.write_bytes(b"preserve exactly")
        snapshot_path = self.home / "snapshots" / f"{self.snapshot.snapshot_id}.json"
        snapshot_bytes = snapshot_path.read_bytes()
        kept_bytes = (self.home / "exports" / f"{kept_id}.bin").read_bytes()
        other.delete(cancelled_id)
        info = other.get(cancelled_id)
        self.assertEqual(info["status"], "cancelled")
        with self.assertRaises(ExportNotReady):
            other.download(cancelled_id)
        self.assertFalse((self.home / "exports" / f"{cancelled_id}.json").exists())
        self.assertFalse((self.home / "exports" / f"{cancelled_id}.bin").exists())
        self.assertEqual(unknown.read_bytes(), b"preserve exactly")
        self.assertEqual(snapshot_path.read_bytes(), snapshot_bytes)
        self.assertEqual(
            (self.home / "exports" / f"{kept_id}.bin").read_bytes(), kept_bytes
        )
        self.assertEqual(store.download(kept_id)[0], b"kept")
        with self.assertRaises(ExportNotFound):
            other.delete("exp_" + "e" * 32)
        with self.assertRaises(ExportNotFound):
            other.delete("../exports/" + kept_id)

    def test_idempotency_replays_same_payload_and_rejects_changes(self) -> None:
        store = self._open()
        state = _presentation()
        original = copy.deepcopy(state)
        first = self._create(store, presentation=state, idempotency_key="same")
        state["theme"] = "light"
        _until(store, first)
        self.assertEqual(self.calls[0][1]["theme"], "dark")
        self.assertEqual(
            store.create(
                self.snapshot.snapshot_id, "csv", original, idempotency_key="same"
            ),
            first,
        )
        with self.assertRaises(ValueError):
            store.create(
                self.snapshot.snapshot_id, "csv", state, idempotency_key="same"
            )
        reversed_state = {key: original[key] for key in reversed(list(original))}
        self.assertEqual(
            store.create(
                self.snapshot.snapshot_id,
                "csv",
                reversed_state,
                idempotency_key="same",
            ),
            first,
        )
        self.assertEqual(len(self.calls), 1)
        empty_a = self._create(store, idempotency_key="")
        empty_b = self._create(store, idempotency_key="")
        self.assertEqual(empty_a, empty_b)
        self.assertNotEqual(self._create(store), self._create(store))
        with self.assertRaises(ValueError):
            store.create(
                self.snapshot.snapshot_id,
                "html",
                original,
                idempotency_key="same",
            )
        with self.assertRaises(ValueError):
            store.create(self.snapshot.snapshot_id, "pdf", original)
        with self.assertRaises(ValueError):
            store.create(self.snapshot.snapshot_id, "csv", original, idempotency_key=1)
        store.close()
        restored = self._open(self._renderer(b"other"))
        before = len(self.calls)
        self.assertEqual(
            restored.create(
                self.snapshot.snapshot_id, "csv", original, idempotency_key="same"
            ),
            first,
        )
        self.assertEqual(len(self.calls), before)

    def test_missing_snapshot_does_not_create_an_export(self) -> None:
        store = self._open()
        with self.assertRaises(SnapshotNotFound):
            store.create("snap_missing", "csv", _presentation())
        with self.assertRaises(SnapshotNotFound):
            store.create("snap_" + "a" * 32, "csv", _presentation())
        old = self.snapshots.create_or_reuse(
            self.dataset,
            _scope(self.dataset, metrics=["steps.attempts"]),
            now=datetime.now(UTC) - timedelta(days=3),
        )
        with self.assertRaises(SnapshotGone):
            store.create(old.snapshot_id, "csv", _presentation())
        self.assertEqual(list((self.home / "exports").glob("exp_*")), [])

    def test_foreign_home_and_traversal_cannot_read_bytes(self) -> None:
        other_home = Path(self.temporary.name) / "other-runtime"
        foreign = self._open(self._renderer(b"foreign-bytes"), other_home)
        foreign_id = foreign.create(
            self.snapshot.snapshot_id,
            "csv",
            _presentation(),
            idempotency_key="foreign",
        )
        _until(foreign, foreign_id)
        foreign_blob, _info = foreign.download(foreign_id)
        self.assertEqual(foreign_blob, b"foreign-bytes")
        local = self._open(self._renderer(b"local-bytes"))
        with self.assertRaises(ExportNotFound):
            local.get(foreign_id)
        with self.assertRaises(ExportNotFound):
            local.download(foreign_id)
        self.assertFalse((self.home / "exports" / f"{foreign_id}.bin").exists())
        secret = self.home.parent / "secret.bin"
        secret.write_bytes(b"secret")
        for invalid in (
            "../secret.bin",
            secret.name,
            "exp_" + "g" * 32,
            "exp_" + "A" * 32,
            "exp_" + "a" * 31,
            "",
            "..%2fconfig.json",
            "exp_" + "f" * 32,
        ):
            with self.assertRaises(ExportNotFound):
                local.get(invalid)
            with self.assertRaises(ExportNotFound):
                local.download(invalid)
        self.assertEqual(secret.read_bytes(), b"secret")
        self.assertEqual(foreign.download(foreign_id)[0], b"foreign-bytes")
        if os.name == "posix":
            foreign_bin = other_home / "exports" / f"{foreign_id}.bin"
            foreign_manifest = (
                other_home / "exports" / f"{foreign_id}.json"
            ).read_bytes()
            stolen_bin = self.home / "exports" / f"{foreign_id}.bin"
            stolen_manifest = self.home / "exports" / f"{foreign_id}.json"
            stolen_manifest.write_bytes(foreign_manifest)
            stolen_bin.symlink_to(foreign_bin)
            relinked = self._open()
            with self.assertRaises(ExportNotFound):
                relinked.download(foreign_id)
            self.assertTrue(stolen_bin.is_symlink())
            self.assertEqual(foreign_bin.read_bytes(), b"foreign-bytes")
            self.assertEqual(stolen_manifest.read_bytes(), foreign_manifest)

    def test_close_cancels_without_starting_a_worker_at_construct(self) -> None:
        entered = threading.Event()

        def renderer(snapshot, format_name, presentation, cancelled):
            entered.set()
            while not cancelled():
                time.sleep(0.005)
            raise ExportCancelled("cancelled")

        before = {thread.name for thread in threading.enumerate()}
        store = self._open(renderer)
        self.assertFalse(self.calls)
        self.assertFalse(any(name.startswith("sbtd-export") for name in before))
        self.assertFalse(
            any(
                thread.name.startswith("sbtd-export")
                for thread in threading.enumerate()
            )
        )
        export_id = self._create(store)
        self.assertTrue(entered.wait(5))
        self.assertTrue(
            any(
                thread.name.startswith("sbtd-export")
                for thread in threading.enumerate()
            )
        )
        store.close()
        self.assertEqual(store.get(export_id)["status"], "cancelled")
        with self.assertRaises(ValueError):
            self._create(store)
        store.close()

    def test_concurrent_same_key_creates_one_job(self) -> None:
        started = threading.Barrier(8)
        store = self._open(self._renderer(b"shared"))
        found: list[str] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def work() -> None:
            try:
                started.wait(5)
                export_id = self._create(store, idempotency_key="race")
                with lock:
                    found.append(export_id)
            except Exception as exc:  # noqa: BLE001 — surface thread failures to unittest.
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=work) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(set(found)), 1)
        _until(store, found[0])
        self.assertEqual(len(self.calls), 1)

    @unittest.skipUnless(os.name == "posix", "POSIX mode and symlink evidence")
    def test_private_modes_links_and_replaced_directory(self) -> None:
        modes: list[int] = []
        real = os.replace

        def capture(source, destination):
            modes.append(Path(source).stat().st_mode & 0o777)
            return real(source, destination)

        store = self._open(self._renderer(b"mode-bytes"))
        with mock.patch("export_store.os.replace", side_effect=capture):
            export_id = self._create(store)
            _until(store, export_id)
        self.assertEqual(modes, [0o600, 0o600])
        exports = self.home / "exports"
        self.assertEqual(exports.stat().st_mode & 0o777, 0o700)
        self.assertEqual((exports / f"{export_id}.bin").stat().st_mode & 0o777, 0o600)
        self.assertEqual((exports / f"{export_id}.json").stat().st_mode & 0o777, 0o600)
        store.close()

        outside = self.home.parent / "outside-artifact"
        artifact = exports / f"{export_id}.bin"
        original = artifact.read_bytes()
        artifact.rename(outside)
        artifact.symlink_to(outside)
        linked = self._open()
        with self.assertRaises(ExportNotFound):
            linked.get(export_id)
        self.assertTrue(artifact.is_symlink())
        self.assertEqual(outside.read_bytes(), original)
        self.assertEqual(linked.sweep(now=datetime.now(UTC) + timedelta(days=3)), [])
        artifact.unlink()
        os.link(outside, artifact)
        untouched = ExportStore(self.home, self.snapshots, self._renderer())
        self.addCleanup(untouched.close)
        self.assertEqual(untouched.sweep(), [])
        self.assertEqual(outside.read_bytes(), original)
        self.assertTrue(artifact.exists())

        replaced = self._open()
        exports.rename(self.home / "exports-old")
        exports.mkdir()
        sentinel = exports / "keep.txt"
        sentinel.write_bytes(b"keep")
        with self.assertRaises(ValueError):
            replaced.sweep()
        self.assertEqual(sentinel.read_bytes(), b"keep")

        link_home = Path(self.temporary.name) / "linked-home"
        link_home.mkdir()
        target = Path(self.temporary.name) / "link-target"
        target.mkdir()
        (target / "keep").write_bytes(b"untouched")
        (link_home / "exports").symlink_to(target, target_is_directory=True)
        with self.assertRaises(ValueError):
            ExportStore(link_home, self.snapshots, self._renderer())
        self.assertEqual((target / "keep").read_bytes(), b"untouched")
        self.assertEqual(set(target.iterdir()), {target / "keep"})

    @unittest.skipUnless(os.name == "posix", "POSIX directory replacement evidence")
    def test_failure_cleanup_refuses_replaced_export_directory(self) -> None:
        entered = threading.Event()
        release = threading.Event()

        def render(snapshot, format_name, presentation, cancelled):
            entered.set()
            release.wait(5)
            return b"artifact", _metadata(snapshot)

        store = self._open(render)
        export_id = self._create(store)
        self.assertTrue(entered.wait(5))
        exports = self.home / "exports"
        exports.rename(self.home / "exports-old")
        outside = Path(self.temporary.name) / "outside-cleanup"
        outside.mkdir()
        sentinel = outside / f"{export_id}.bin"
        sentinel.write_bytes(b"user-owned")
        exports.symlink_to(outside, target_is_directory=True)
        release.set()
        store.close()
        self.assertTrue(sentinel.exists(), "cleanup escaped through replaced parent")
        self.assertEqual(sentinel.read_bytes(), b"user-owned")
        self.assertEqual(
            self.snapshots.sweep(now=datetime.now(UTC) + timedelta(days=2)),
            [self.snapshot.snapshot_id],
        )

    def test_sweep_between_publish_and_finally_still_releases_pin(self) -> None:
        store = self._open()
        published = threading.Event()
        release = threading.Event()
        original = store._publish

        def paused_publish(job, blob, metadata):
            original(job, blob, metadata)
            published.set()
            release.wait(5)

        with mock.patch.object(store, "_publish", side_effect=paused_publish):
            export_id = self._create(store)
            try:
                self.assertTrue(published.wait(5))
                expires = parse_instant(store.get(export_id)["expires_at"])
                self.assertEqual(store.sweep(now=expires), [export_id])
            finally:
                release.set()
                store.close()
        self.assertEqual(
            self.snapshots.sweep(now=datetime.now(UTC) + timedelta(days=2)),
            [self.snapshot.snapshot_id],
        )

    def test_queued_cancellation_does_not_wait_for_another_job(self) -> None:
        entered = threading.Event()
        release = threading.Event()
        deleted = threading.Event()

        def render(snapshot, format_name, presentation, cancelled):
            entered.set()
            release.wait(5)
            return b"first", _metadata(snapshot)

        store = self._open(render)
        first = self._create(store)
        self.assertTrue(entered.wait(5))
        second = self._create(store)

        def cancel():
            store.delete(second)
            deleted.set()

        thread = threading.Thread(target=cancel)
        thread.start()
        try:
            self.assertTrue(deleted.wait(1), "queued cancel waited for another job")
            self.assertEqual(store.get(second)["status"], "cancelled")
            self.assertEqual(store.get(first)["status"], "generating")
        finally:
            release.set()
            thread.join(5)

    def test_worker_start_failure_releases_snapshot_pin(self) -> None:
        store = self._open()
        with (
            mock.patch(
                "export_store.ThreadPoolExecutor",
                side_effect=RuntimeError("unavailable"),
            ),
            self.assertRaises(RuntimeError),
        ):
            self._create(store)
        self.assertEqual(
            self.snapshots.sweep(now=datetime.now(UTC) + timedelta(days=2)),
            [self.snapshot.snapshot_id],
        )

    def test_manifest_does_not_persist_request_text_or_idempotency_secret(self) -> None:
        store = self._open()
        presentation = {
            **_presentation(),
            "expanded_detail_ids": ["password=SYNTH_REQUEST_SECRET"],
        }
        export_id = self._create(
            store, presentation=presentation, idempotency_key="SYNTH_HEADER_SECRET"
        )
        _until(store, export_id)
        manifest = (self.home / "exports" / f"{export_id}.json").read_text()
        self.assertNotIn("SYNTH_REQUEST_SECRET", manifest)
        self.assertNotIn("SYNTH_HEADER_SECRET", manifest)

    @unittest.skipUnless(os.name == "nt", "Windows junction evidence only")
    def test_export_junction_is_refused_without_cleaning_target(self) -> None:
        outside = self.home.parent / "outside"
        outside.mkdir()
        target = outside / "exports"
        target.mkdir()
        sentinel = target / "keep.txt"
        sentinel.write_bytes(b"untouched")
        process = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(self.home / "exports"), str(target)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        with self.assertRaises(ValueError):
            ExportStore(self.home, self.snapshots, self._renderer())
        self.assertEqual(sentinel.read_bytes(), b"untouched")


if __name__ == "__main__":
    unittest.main()
