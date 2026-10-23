"""Shared admission and ownership; spec/r2.1b-renderer-scenarios.md."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

from export_store import ExportStore
from report_snapshot import SnapshotStore
from test_report_snapshot import _dataset, _scope


class DiskQuotaTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="sbtd-quota-")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.dataset = _dataset()
        self.scope = _scope(self.dataset)

    def snapshots(self, quota: int, **kwargs) -> SnapshotStore:
        return SnapshotStore(self.home, quota_bytes=quota, **kwargs)

    def exports(self, snapshots: SnapshotStore, renderer=None) -> ExportStore:
        store = ExportStore(
            self.home, snapshots, renderer or (lambda *args: (b"artifact", {}))
        )
        self.addCleanup(store.close)
        return store

    def test_environment_parser(self) -> None:
        from disk_quota import parse_disk_quota

        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(parse_disk_quota(), 2000000000)
        for value, expected in (("0001", 1), ("42", 42), ("2000000000", 2000000000)):
            with (
                self.subTest(value=value),
                mock.patch.dict(os.environ, {"SBTD_RUNTIME_DISK_QUOTA_BYTES": value}),
            ):
                self.assertEqual(parse_disk_quota(), expected)
        for value in (
            "",
            "0",
            "00",
            "-1",
            "+1",
            " 1",
            "1\n",
            "1.0",
            "1e3",
            "2GB",
            "١",
            "１",
            "9" * 5000,
        ):
            with (
                self.subTest(value=value[:12]),
                mock.patch.dict(os.environ, {"SBTD_RUNTIME_DISK_QUOTA_BYTES": value}),
            ):
                with self.assertRaisesRegex(
                    ValueError, "SBTD_RUNTIME_DISK_QUOTA_BYTES"
                ) as caught:
                    parse_disk_quota()
                self.assertEqual(
                    str(caught.exception),
                    "SBTD_RUNTIME_DISK_QUOTA_BYTES must be a positive ASCII decimal integer ([0-9]+)",
                )

    def test_invalid_configuration_refuses_startup_before_sweep(self) -> None:
        directory = self.home / "snapshots"
        directory.mkdir()
        leftover = directory / ".snapshot-owned.tmp"
        leftover.write_bytes(b"half")
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "serve",
                "--home",
                str(self.home),
                "--no-open",
            ],
            env={
                **os.environ,
                "SBTD_RUNTIME_DISK_QUOTA_BYTES": "invalid-private-value",
            },
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("SBTD_RUNTIME_DISK_QUOTA_BYTES", result.stderr)
        self.assertNotIn("invalid-private-value", result.stdout + result.stderr)
        self.assertEqual(leftover.read_bytes(), b"half")
        self.assertFalse((self.home / "serve.lock").exists())

    def test_exact_cap_allows_snapshot_then_refuses_with_shared_counts(self) -> None:
        from disk_quota import DiskQuotaExceeded

        store = self.snapshots(10)
        exports = self.home / "exports"
        exports.mkdir(exist_ok=True)
        corrupt = exports / "orphan.bin"
        corrupt.write_bytes(b"1234567890")
        snapshot = store.create_or_reuse(self.dataset, self.scope)
        path = self.home / "snapshots" / (snapshot.snapshot_id + ".json")
        expected = 10 + path.stat().st_size
        before = set((self.home / "snapshots").iterdir())
        with self.assertRaises(DiskQuotaExceeded) as caught:
            store.create_or_reuse(
                self.dataset, _scope(self.dataset, metrics=["tasks.created"])
            )
        self.assertEqual(caught.exception.used_bytes, expected)
        self.assertEqual(caught.exception.quota_bytes, 10)
        self.assertEqual(set((self.home / "snapshots").iterdir()), before)
        self.assertEqual(corrupt.read_bytes(), b"1234567890")
        self.assertEqual(
            store.create_or_reuse(self.dataset, self.scope).snapshot_id,
            snapshot.snapshot_id,
        )

    def test_warning_boundary_is_log_only_and_environment_is_not_reloaded(self) -> None:
        with mock.patch.dict(os.environ, {"SBTD_RUNTIME_DISK_QUOTA_BYTES": "10"}):
            store = SnapshotStore(self.home)
        unknown = self.home / "snapshots" / "unknown"
        unknown.write_bytes(b"1234567")
        with self.assertNoLogs("disk_quota", level="WARNING"):
            store.quota.admit()
        unknown.write_bytes(b"12345678")
        with (
            mock.patch.dict(os.environ, {"SBTD_RUNTIME_DISK_QUOTA_BYTES": "1"}),
            self.assertLogs("disk_quota", level="WARNING") as logs,
        ):
            snapshot = store.create_or_reuse(self.dataset, self.scope)
        self.assertIn("used_bytes=8 quota_bytes=10", logs.output[0])
        self.assertFalse(any("QUOTA" in warning for warning in snapshot.warnings))

    def test_creation_sweeps_expired_pair_then_snapshot_before_measurement(
        self,
    ) -> None:
        store = self.snapshots(1000000, ttl_seconds=10)
        exports = self.exports(store)
        start = datetime.now(UTC)
        old = store.create_or_reuse(self.dataset, self.scope, now=start)
        export_id = exports.create(old.snapshot_id, "csv", {})
        self.assertTrue(exports._jobs[export_id].done.wait(5))
        future = start + timedelta(days=2)
        store.quota.quota_bytes = 1
        # The create supplies one clock to both owners; all old bytes can be freed.
        replacement = store.create_or_reuse(self.dataset, self.scope, now=future)
        self.assertNotEqual(replacement.snapshot_id, old.snapshot_id)
        self.assertFalse(
            (self.home / "snapshots" / (old.snapshot_id + ".json")).exists()
        )
        self.assertEqual(list((self.home / "exports").iterdir()), [])

    def test_snapshot_only_restart_sweeps_expired_exports(self) -> None:
        store = self.snapshots(1000000)
        exports = self.exports(store)
        start = datetime.now(UTC)
        snapshot = store.create_or_reuse(self.dataset, self.scope, now=start)
        export_id = exports.create(snapshot.snapshot_id, "csv", {})
        self.assertTrue(exports._jobs[export_id].done.wait(5))
        exports.close()
        restarted = self.snapshots(1)
        replacement = restarted.create_or_reuse(
            self.dataset, self.scope, now=start + timedelta(days=2)
        )
        self.assertNotEqual(replacement.snapshot_id, snapshot.snapshot_id)
        self.assertEqual(list((self.home / "exports").iterdir()), [])

    def test_export_creation_sweeps_before_measurement(self) -> None:
        store = self.snapshots(1000000)
        exports = self.exports(store)
        snapshot = store.create_or_reuse(self.dataset, self.scope)
        export_id = exports.create(snapshot.snapshot_id, "csv", {})
        self.assertTrue(exports._jobs[export_id].done.wait(5))
        size = (
            (self.home / "snapshots" / (snapshot.snapshot_id + ".json")).stat().st_size
        )
        store.quota.quota_bytes = size
        with mock.patch(
            "export_store._now", return_value=datetime.now(UTC) + timedelta(days=2)
        ):
            accepted = exports.create(snapshot.snapshot_id, "csv", {})
        self.assertNotEqual(accepted, export_id)
        self.assertTrue(exports._jobs[accepted].done.wait(5))
        self.assertFalse((self.home / "exports" / (export_id + ".bin")).exists())

    def test_pinned_and_corrupt_files_are_retained_and_counted(self) -> None:
        from disk_quota import DiskQuotaExceeded

        store = self.snapshots(1000000, ttl_seconds=10)
        now = datetime.now(UTC)
        snapshot = store.create_or_reuse(self.dataset, self.scope, now=now)
        store.pin(snapshot.snapshot_id, now=now)
        corrupt = self.home / "snapshots" / ("snap_" + "f" * 32 + ".json")
        corrupt.write_bytes(b"broken")
        size = sum(p.stat().st_size for p in (self.home / "snapshots").iterdir())
        store.quota.quota_bytes = 1
        with self.assertRaises(DiskQuotaExceeded) as caught:
            store.create_or_reuse(
                self.dataset, self.scope, now=now + timedelta(seconds=11)
            )
        self.assertEqual(caught.exception.used_bytes, size)
        self.assertEqual(corrupt.read_bytes(), b"broken")
        self.assertEqual(
            store.get(snapshot.snapshot_id, now=now + timedelta(seconds=11)).rows,
            snapshot.rows,
        )

    def test_only_confirmed_startup_temps_are_cleaned(self) -> None:
        for name, prefix in (("snapshots", "snapshot"), ("exports", "export")):
            directory = self.home / name
            directory.mkdir()
            (directory / f".{prefix}-old.tmp").write_bytes(b"half")
        store = self.snapshots(1000000)
        exports = self.exports(store)
        self.assertEqual(list((self.home / "exports").iterdir()), [])
        self.assertEqual(list((self.home / "snapshots").iterdir()), [])
        unknown = self.home / "exports" / ".export-foreign.tmp"
        unknown.write_bytes(b"unknown writer")
        snapshot = store.create_or_reuse(self.dataset, self.scope)
        export_id = exports.create(snapshot.snapshot_id, "csv", {})
        self.assertTrue(exports._jobs[export_id].done.wait(5))
        self.assertEqual(unknown.read_bytes(), b"unknown writer")

    def test_measurement_failure_never_admits_as_zero(self) -> None:
        store = self.snapshots(1000000)
        original = Path.iterdir

        def denied(path):
            if path == self.home / "snapshots":
                raise PermissionError("test denied")
            return original(path)

        with (
            mock.patch.object(Path, "iterdir", denied),
            self.assertRaises(PermissionError),
        ):
            store.create_or_reuse(self.dataset, self.scope)
        self.assertEqual(list((self.home / "snapshots").iterdir()), [])

    @unittest.skipUnless(os.name == "posix", "POSIX links and FIFO")
    def test_flat_measurement_does_not_follow_links_or_delete_hardlinks(self) -> None:
        from disk_quota import DiskQuotaExceeded

        directory = self.home / "snapshots"
        directory.mkdir()
        outside = self.home / "outside"
        outside.write_bytes(b"12345")
        (directory / "link").symlink_to(outside)
        nested = directory / "nested"
        nested.mkdir()
        (nested / "keep").write_bytes(b"nested")
        os.mkfifo(directory / "pipe")
        os.link(outside, directory / ".snapshot-hard.tmp")
        os.link(outside, directory / "hard2")
        store = self.snapshots(1)
        with self.assertRaises(DiskQuotaExceeded) as caught:
            store.create_or_reuse(self.dataset, self.scope)
        self.assertEqual(caught.exception.used_bytes, 10)
        self.assertEqual(outside.read_bytes(), b"12345")
        self.assertTrue((directory / ".snapshot-hard.tmp").exists())
        self.assertTrue((directory / "link").is_symlink())
        self.assertEqual((nested / "keep").read_bytes(), b"nested")

    def test_failed_expiry_deletion_remains_in_usage(self) -> None:
        from disk_quota import DiskQuotaExceeded

        store = self.snapshots(1000000, ttl_seconds=1)
        now = datetime.now(UTC)
        snapshot = store.create_or_reuse(self.dataset, self.scope, now=now)
        path = self.home / "snapshots" / (snapshot.snapshot_id + ".json")
        size = path.stat().st_size
        store.quota.quota_bytes = 1
        with (
            mock.patch.object(
                Path, "unlink", side_effect=PermissionError("test denied")
            ),
            self.assertRaises(DiskQuotaExceeded) as caught,
        ):
            store.create_or_reuse(
                self.dataset, self.scope, now=now + timedelta(seconds=2)
            )
        self.assertEqual(caught.exception.used_bytes, size)
        self.assertTrue(path.exists())

    def test_preparing_export_rechecks_quota_before_acceptance(self) -> None:
        from disk_quota import DiskQuotaExceeded

        store = self.snapshots(1000000)
        exports = self.exports(store)
        snapshot = store.create_or_reuse(self.dataset, self.scope)

        def prepare(*args, **kwargs):
            (self.home / "exports" / "unknown").write_bytes(b"x" * 1000001)
            return lambda *args: (b"artifact", {}), []

        with self.assertRaises(DiskQuotaExceeded):
            exports.create(snapshot.snapshot_id, "jpeg", {}, prepare=prepare)
        self.assertEqual(exports._jobs, {})
        self.assertEqual(dict(store._pins), {})

    def test_publication_and_snapshot_admission_serialize(self) -> None:
        from disk_quota import DiskQuotaExceeded

        store = self.snapshots(1000000)
        entered = threading.Event()
        release = threading.Event()
        self.addCleanup(release.set)
        exports = self.exports(store)
        snapshot = store.create_or_reuse(self.dataset, self.scope)
        original = exports._write_temp

        def paused(blob):
            path = original(blob)
            entered.set()
            if not release.wait(5):
                raise AssertionError("publication not released")
            return path

        with mock.patch.object(exports, "_write_temp", side_effect=paused):
            export_id = exports.create(snapshot.snapshot_id, "csv", {})
            self.assertTrue(entered.wait(5))
            store.quota.quota_bytes = 1
            errors = []
            finished = threading.Event()

            def create():
                try:
                    store.create_or_reuse(
                        self.dataset, _scope(self.dataset, metrics=["tasks.created"])
                    )
                except DiskQuotaExceeded as error:
                    errors.append(error)
                finally:
                    finished.set()

            thread = threading.Thread(target=create)
            thread.start()
            try:
                self.assertFalse(finished.wait(0.05))
            finally:
                release.set()
                thread.join(5)
            self.assertTrue(exports._jobs[export_id].done.wait(5))
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], DiskQuotaExceeded)
        self.assertEqual(exports.get(export_id)["status"], "ready")
        self.assertEqual(list((self.home / "exports").glob("*.tmp")), [])
