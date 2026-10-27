"""D13 persistence behavior; spec/r2.0c-snapshot-persistence-scenarios.md."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

from report_snapshot import SnapshotGone, SnapshotNotFound, SnapshotStore
from stats_query import query, timeseries
from test_report_snapshot import _all_pages, _dataset, _scope


class SnapshotPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="sbtd-snapshots-")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name) / "runtime"
        self.dataset = _dataset()
        self.scope = _scope(self.dataset)

    def test_restart_preserves_snapshot_rows_cursor_and_expiry(self) -> None:
        store = SnapshotStore(self.home)
        before = datetime.now(UTC)
        snapshot = store.create_or_reuse(self.dataset, self.scope, now=before)
        page = store.dataset_page(snapshot.snapshot_id, limit=3)
        rows = _all_pages(store, snapshot.snapshot_id, 7)
        restarted = SnapshotStore(self.home)
        restored = restarted.get(snapshot.snapshot_id)
        self.assertEqual(restored.public_view(), snapshot.public_view())
        self.assertEqual(restored.expires_instant, before + timedelta(hours=24))
        self.assertEqual(_all_pages(restarted, snapshot.snapshot_id, 11), rows)
        self.assertEqual(
            restarted.dataset_page(snapshot.snapshot_id, page["next_cursor"], 3)[
                "rows"
            ],
            rows[3:6],
        )
        reused = restarted.create_or_reuse(self.dataset, self.scope)
        self.assertEqual(reused.snapshot_id, snapshot.snapshot_id)
        self.assertEqual(reused.expires_at, snapshot.expires_at)

    def test_creation_responses_report_original_expiry(self) -> None:
        store = SnapshotStore(self.home)
        answer = query(self.dataset, self.scope, store=store)
        snapshot = store.get(answer["snapshot_id"])
        self.assertEqual(answer["expires_at"], snapshot.expires_at)
        series = timeseries(self.dataset, self.scope, bucket_seconds=43200, store=store)
        self.assertEqual(series["expires_at"], answer["expires_at"])
        self.assertEqual(series["snapshot_id"], answer["snapshot_id"])

    def test_corrupt_files_are_never_snapshots(self) -> None:
        store = SnapshotStore(self.home)
        snapshot = store.create_or_reuse(self.dataset, self.scope)
        path = self.home / "snapshots" / f"{snapshot.snapshot_id}.json"
        original = path.read_bytes()
        envelope = json.loads(original)
        without_checksum = {k: v for k, v in envelope.items() if k != "checksum"}
        wrong_version = {**envelope, "format_version": 2}
        bool_version = {**envelope, "format_version": True}
        tampered = json.loads(original)
        tampered["snapshot"]["rows"] = []
        bad_payload = json.loads(original)
        bad_payload["snapshot"]["expires_at"] = 42
        canonical = json.dumps(
            bad_payload["snapshot"],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
        bad_payload["checksum"] = "sha256:" + hashlib.sha256(canonical).hexdigest()
        cases = {
            "truncated": original[: len(original) // 2],
            "missing-checksum": json.dumps(without_checksum).encode(),
            "wrong-version": json.dumps(wrong_version).encode(),
            "boolean-version": json.dumps(bool_version).encode(),
            "checksum-mismatch": json.dumps(tampered).encode(),
            "deeply-nested": b"[" * (sys.getrecursionlimit() + 100)
            + b"0"
            + b"]" * (sys.getrecursionlimit() + 100),
            "invalid-payload": json.dumps(bad_payload).encode(),
            "duplicate-header": b'{"format_version":1,' + original[1:],
        }
        for name, blob in cases.items():
            with self.subTest(corruption=name):
                path.write_bytes(blob)
                with self.assertRaises(SnapshotNotFound):
                    store.get(snapshot.snapshot_id)
                restarted = SnapshotStore(self.home)
                with self.assertRaises(SnapshotNotFound):
                    restarted.get(snapshot.snapshot_id)
                self.assertEqual(path.read_bytes(), blob)

    def test_unchanged_file_is_validated_once_and_returns_isolated_data(self) -> None:
        store = SnapshotStore(self.home)
        snapshot = store.create_or_reuse(self.dataset, self.scope)
        with mock.patch("report_snapshot.json.load", wraps=json.load) as load:
            first = store.get(snapshot.snapshot_id)
            expected = store.dataset_page(snapshot.snapshot_id, limit=3)
            changed = store.dataset_page(snapshot.snapshot_id, limit=3)
            first.rows[0]["fields"]["changed"] = True
            first.dataset["events"].clear()
            changed["rows"][0]["fields"]["changed"] = True
            self.assertEqual(store.dataset_page(snapshot.snapshot_id, limit=3), expected)
            self.assertEqual(store.get(snapshot.snapshot_id).dataset, snapshot.dataset)
            self.assertEqual(load.call_count, 1)

    def test_different_path_and_fd_ctime_preserves_cache_and_rejects_rewrite(self) -> None:
        store = SnapshotStore(self.home)
        snapshot = store.create_or_reuse(self.dataset, self.scope)
        path = self.home / "snapshots" / f"{snapshot.snapshot_id}.json"
        original_stat = path.lstat()
        # Model fd ChangeTime differing from the path's ctime.
        change_time = original_stat.st_ctime_ns + 1_000_000_000
        real_fstat = os.fstat

        def fd_stat(fd):
            info = real_fstat(fd)
            return os.stat_result(
                info,
                {
                    "st_atime_ns": info.st_atime_ns,
                    "st_mtime_ns": info.st_mtime_ns,
                    "st_ctime_ns": change_time,
                },
            )

        with (
            mock.patch("report_snapshot.os.fstat", side_effect=fd_stat),
            mock.patch("report_snapshot.json.load", wraps=json.load) as load,
        ):
            self.assertEqual(store.get(snapshot.snapshot_id).rows, snapshot.rows)
            self.assertEqual(store.get(snapshot.snapshot_id).dataset, snapshot.dataset)
            self.assertEqual(load.call_count, 1)
            original = path.read_bytes()
            tampered = original.replace(b'"checksum":"sha256:', b'"checksum":"sha257:', 1)
            self.assertNotEqual(tampered, original)
            path.write_bytes(tampered)
            os.utime(path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
            change_time += 1
            self.assertEqual(path.stat().st_size, original_stat.st_size)
            self.assertEqual(path.stat().st_mtime_ns, original_stat.st_mtime_ns)
            with self.assertRaises(SnapshotNotFound):
                store.get(snapshot.snapshot_id)
            self.assertEqual(load.call_count, 2)

    def test_cached_file_rewrite_with_preserved_size_and_mtime_is_rejected(self) -> None:
        store = SnapshotStore(self.home)
        snapshot = store.create_or_reuse(self.dataset, self.scope)
        path = self.home / "snapshots" / f"{snapshot.snapshot_id}.json"
        store.get(snapshot.snapshot_id)
        before = path.stat()
        original = path.read_bytes()
        tampered = original.replace(b'"checksum":"sha256:', b'"checksum":"sha257:', 1)
        self.assertNotEqual(tampered, original)
        path.write_bytes(tampered)
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(path.stat().st_size, before.st_size)
        self.assertEqual(path.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertNotEqual(path.stat().st_ctime_ns, before.st_ctime_ns)
        with mock.patch("report_snapshot.json.load", wraps=json.load) as load:
            with self.assertRaises(SnapshotNotFound):
                store.get(snapshot.snapshot_id)
            self.assertEqual(load.call_count, 1)
        path.write_bytes(original)
        self.assertEqual(store.get(snapshot.snapshot_id).rows, snapshot.rows)

    def test_cached_file_replacement_is_revalidated(self) -> None:
        store = SnapshotStore(self.home)
        snapshot = store.create_or_reuse(self.dataset, self.scope)
        path = self.home / "snapshots" / f"{snapshot.snapshot_id}.json"
        store.get(snapshot.snapshot_id)
        before = path.stat()
        replacement = path.with_suffix(".replacement")
        replacement.write_bytes(path.read_bytes())
        os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
        os.replace(replacement, path)
        self.assertNotEqual(path.stat().st_ino, before.st_ino)
        with mock.patch("report_snapshot.json.load", wraps=json.load) as load:
            self.assertEqual(store.get(snapshot.snapshot_id).rows, snapshot.rows)
            self.assertEqual(store.get(snapshot.snapshot_id).rows, snapshot.rows)
            self.assertEqual(load.call_count, 1)

    def test_sweep_reads_only_expired_candidates(self) -> None:
        store = SnapshotStore(self.home, ttl_seconds=10)
        now = datetime.now(UTC)
        expired = store.create_or_reuse(self.dataset, self.scope, now=now)
        live = store.create_or_reuse(
            self.dataset,
            _scope(self.dataset, metrics=["tasks.created"]),
            now=now + timedelta(seconds=1),
        )
        store.get(expired.snapshot_id, now=now)
        with (
            mock.patch.object(store, "_read", wraps=store._read) as read,
            mock.patch("report_snapshot.json.load", wraps=json.load) as load,
        ):
            removed = store.sweep(now=now + timedelta(seconds=10))
        self.assertEqual(removed, [expired.snapshot_id])
        self.assertEqual(
            [call.args[0] for call in read.call_args_list], [expired.snapshot_id]
        )
        self.assertEqual(load.call_count, 1)
        self.assertNotIn(expired.snapshot_id, store._validated)
        self.assertFalse(
            (self.home / "snapshots" / f"{expired.snapshot_id}.json").exists()
        )
        self.assertTrue(
            (self.home / "snapshots" / f"{live.snapshot_id}.json").exists()
        )

    def test_expired_cache_is_dropped_without_evicting_snapshot(self) -> None:
        store = SnapshotStore(self.home, ttl_seconds=10)
        now = datetime.now(UTC)
        snapshot = store.create_or_reuse(self.dataset, self.scope, now=now)
        store.get(snapshot.snapshot_id, now=now)
        self.assertIn(snapshot.snapshot_id, store._validated)
        with self.assertRaises(SnapshotGone):
            store.get(snapshot.snapshot_id, now=now + timedelta(seconds=10))
        self.assertNotIn(snapshot.snapshot_id, store._validated)
        self.assertIn(snapshot.snapshot_id, store._snapshots)

    def test_startup_sweep_touches_only_owned_expired_snapshots(self) -> None:
        store = SnapshotStore(self.home)
        old = datetime.now(UTC) - timedelta(days=2)
        live = store.create_or_reuse(self.dataset, self.scope)
        expired = store.create_or_reuse(
            self.dataset, _scope(self.dataset, metrics=["tasks.created"]), now=old
        )
        snapshots = self.home / "snapshots"
        expired_path = snapshots / f"{expired.snapshot_id}.json"
        live_path = snapshots / f"{live.snapshot_id}.json"
        sentinels = [
            self.home / "exports" / expired_path.name,
            self.home / "audit.db",
            self.home / "config.json",
            self.home / "registry.json",
            self.home / "spool" / "audit.ready",
            self.home / "backups" / "audit.db",
            self.home.parent / "source" / "task.md",
            self.home.parent / "source" / "report.json",
            self.home.parent / "source" / "handoff.md",
            snapshots / "unknown.txt",
            snapshots / "nested" / expired_path.name,
            snapshots / ("snap_" + "a" * 32 + ".json"),
        ]
        for path in sentinels:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"preserve exactly")
        sentinels.append(live_path)
        expected = {path: path.read_bytes() for path in sentinels}
        leftover = snapshots / ".snapshot-interrupted.tmp"
        leftover.write_bytes(b"half-written snapshot")
        restarted = SnapshotStore(self.home)
        self.assertFalse(expired_path.exists())
        self.assertFalse(leftover.exists())
        self.assertEqual(
            restarted.get(live.snapshot_id).public_view(), live.public_view()
        )
        with self.assertRaises(SnapshotGone):
            restarted.get(expired.snapshot_id)
        for path, content in expected.items():
            self.assertEqual(path.read_bytes(), content, str(path))
        with self.assertRaises(SnapshotNotFound):
            SnapshotStore(self.home).get(expired.snapshot_id)

    def test_pins_hold_expired_snapshot_until_last_release(self) -> None:
        store = SnapshotStore(self.home, ttl_seconds=10)
        now = datetime.now(UTC)
        snapshot = store.create_or_reuse(self.dataset, self.scope, now=now)
        store.pin(snapshot.snapshot_id, now=now)
        store.pin(snapshot.snapshot_id, now=now)
        expired = now + timedelta(seconds=10)
        path = self.home / "snapshots" / f"{snapshot.snapshot_id}.json"
        self.assertEqual(store.sweep(now=expired), [])
        self.assertEqual(
            store.get(snapshot.snapshot_id, now=expired).rows, snapshot.rows
        )
        self.assertEqual(
            store.dataset_page(snapshot.snapshot_id, now=expired)["total"],
            len(snapshot.rows),
        )
        store.release(snapshot.snapshot_id)
        self.assertEqual(store.sweep(now=expired), [])
        self.assertTrue(path.exists())
        replacement = store.create_or_reuse(self.dataset, self.scope, now=expired)
        self.assertNotEqual(replacement.snapshot_id, snapshot.snapshot_id)
        store.release(snapshot.snapshot_id)
        self.assertEqual(store.sweep(now=expired), [snapshot.snapshot_id])
        self.assertFalse(path.exists())
        with self.assertRaises(SnapshotGone):
            store.get(snapshot.snapshot_id, now=expired)
        with self.assertRaises(SnapshotGone):
            store.pin(snapshot.snapshot_id, now=expired)

    def test_restored_references_precede_startup_sweep(self) -> None:
        store = SnapshotStore(self.home)
        old = datetime.now(UTC) - timedelta(days=2)
        snapshot = store.create_or_reuse(self.dataset, self.scope, now=old)
        restored = SnapshotStore(self.home, pinned_snapshot_ids=[snapshot.snapshot_id])
        self.assertEqual(restored.get(snapshot.snapshot_id).rows, snapshot.rows)
        self.assertEqual(restored.sweep(), [])
        restored.release(snapshot.snapshot_id)
        self.assertEqual(restored.sweep(), [snapshot.snapshot_id])

    def test_write_failures_preserve_prior_snapshot(self) -> None:
        store = SnapshotStore(self.home)
        original = store.create_or_reuse(self.dataset, self.scope)
        scope = _scope(self.dataset, metrics=["tasks.created"])
        for operation in ("fsync", "replace"):
            with self.subTest(operation=operation):
                with (
                    mock.patch(
                        "report_snapshot.os." + operation, side_effect=OSError("disk")
                    ),
                    self.assertRaises(OSError),
                ):
                    store.create_or_reuse(self.dataset, scope)
                restarted = SnapshotStore(self.home)
                self.assertEqual(
                    restarted.get(original.snapshot_id).rows, original.rows
                )
                self.assertEqual(
                    {path.name for path in (self.home / "snapshots").iterdir()},
                    {original.snapshot_id + ".json"},
                )

    def test_crash_before_rename_leaves_only_unreadable_temp(self) -> None:
        code = """
import os, sys
from pathlib import Path
from unittest import mock
from report_snapshot import SnapshotStore
from test_report_snapshot import _dataset, _scope
dataset = _dataset()
store = SnapshotStore(Path(sys.argv[1]))
with mock.patch('report_snapshot.os.replace', side_effect=lambda *args: os._exit(73)):
    store.create_or_reuse(dataset, _scope(dataset))
"""
        process = subprocess.run(
            [sys.executable, "-B", "-c", code, str(self.home)],
            env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)},
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(process.returncode, 73, process.stderr)
        (temporary,) = (self.home / "snapshots").iterdir()
        envelope = json.loads(temporary.read_bytes())
        snapshot_id = envelope["snapshot"]["snapshot_id"]
        restarted = SnapshotStore(self.home)
        with self.assertRaises(SnapshotNotFound):
            restarted.get(snapshot_id)
        self.assertFalse(temporary.exists())

    @unittest.skipUnless(os.name == "posix", "POSIX mode evidence only")
    def test_private_permissions_include_temporary_file(self) -> None:
        store = SnapshotStore(self.home)
        replace = os.replace
        modes = []

        def publish(source, destination):
            modes.append(Path(source).stat().st_mode & 0o777)
            replace(source, destination)

        with mock.patch("report_snapshot.os.replace", side_effect=publish):
            snapshot = store.create_or_reuse(self.dataset, self.scope)
        self.assertEqual(modes, [0o600])
        self.assertEqual(self.home.stat().st_mode & 0o777, 0o700)
        directory = self.home / "snapshots"
        self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
        self.assertEqual(
            (directory / f"{snapshot.snapshot_id}.json").stat().st_mode & 0o777, 0o600
        )

    @unittest.skipUnless(os.name == "posix", "symlink/hardlink support")
    def test_links_and_path_traversal_never_escape_snapshot_directory(self) -> None:
        store = SnapshotStore(self.home)
        old = datetime.now(UTC) - timedelta(days=2)
        snapshot = store.create_or_reuse(self.dataset, self.scope, now=old)
        path = self.home / "snapshots" / f"{snapshot.snapshot_id}.json"
        outside = self.home / "exports" / path.name
        outside.parent.mkdir()
        path.rename(outside)
        original = outside.read_bytes()
        path.symlink_to(outside)
        restarted = SnapshotStore(self.home)
        with self.assertRaises(SnapshotNotFound):
            restarted.get(snapshot.snapshot_id)
        self.assertTrue(path.is_symlink())
        self.assertEqual(outside.read_bytes(), original)
        path.unlink()
        os.link(outside, path)
        self.assertEqual(SnapshotStore(self.home).sweep(), [])
        self.assertEqual(outside.read_bytes(), original)
        for invalid in (
            "../exports/" + snapshot.snapshot_id,
            "/tmp/snap_x",
            "snap_missing",
        ):
            with self.assertRaises(SnapshotNotFound):
                restarted.get(invalid)

    @unittest.skipUnless(os.name == "posix", "symlink support")
    def test_snapshot_directory_symlink_is_refused(self) -> None:
        self.home.mkdir()
        outside = self.home.parent / "outside"
        outside.mkdir()
        sentinel = outside / "keep"
        sentinel.write_bytes(b"untouched")
        (self.home / "snapshots").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            SnapshotStore(self.home)
        self.assertEqual(sentinel.read_bytes(), b"untouched")

    @unittest.skipUnless(os.name == "posix", "POSIX symlink and mode evidence")
    def test_serve_rejects_home_link_before_mutating_target(self) -> None:
        outside = self.home.parent / "outside"
        outside.mkdir(mode=0o755)
        lock = outside / "serve.lock"
        lock.write_bytes(b"not a runtime lock")
        before_mode = outside.stat().st_mode
        self.home.symlink_to(outside, target_is_directory=True)
        process = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "serve",
                "--home",
                str(self.home),
                "--no-open",
            ],
            env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)},
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(lock.read_bytes(), b"not a runtime lock")
        self.assertEqual(outside.stat().st_mode, before_mode)
        self.assertEqual({path.name for path in outside.iterdir()}, {"serve.lock"})

    def test_parser_recursion_failure_rejects_file_without_aborting_startup(
        self,
    ) -> None:
        store = SnapshotStore(self.home)
        snapshot = store.create_or_reuse(self.dataset, self.scope)
        path = self.home / "snapshots" / f"{snapshot.snapshot_id}.json"
        original = path.read_bytes()
        # Python decoder recursion limits vary; inject that documented failure
        # at the I/O boundary, as with the fsync/rename failure cases above.
        with mock.patch("report_snapshot.json.load", side_effect=RecursionError):
            restarted = SnapshotStore(self.home)
            with self.assertRaises(SnapshotNotFound):
                restarted.get(snapshot.snapshot_id)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(
            SnapshotStore(self.home).get(snapshot.snapshot_id).rows, snapshot.rows
        )

    @unittest.skipUnless(os.name == "nt", "Windows junction evidence only")
    def test_snapshot_junction_is_refused_without_cleaning_target(self) -> None:
        outside = self.home.parent / "outside"
        owner = SnapshotStore(outside)
        snapshot = owner.create_or_reuse(
            self.dataset, self.scope, now=datetime.now(UTC) - timedelta(days=2)
        )
        target = outside / "snapshots"
        original = (target / f"{snapshot.snapshot_id}.json").read_bytes()
        self.home.mkdir()
        process = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(self.home / "snapshots"), str(target)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        with self.assertRaises(ValueError):
            SnapshotStore(self.home)
        self.assertEqual(
            (target / f"{snapshot.snapshot_id}.json").read_bytes(), original
        )


if __name__ == "__main__":
    unittest.main()
