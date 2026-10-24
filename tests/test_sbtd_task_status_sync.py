from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sbtd-workflow-onboard/scripts"))

from sbtd_project import TaskDataError
from sbtd_task_document import TaskDocument


def legacy_text() -> str:
    metadata = {
        "schema_version": 1,
        "id": "sync",
        "workflow_mode": "lite",
        "mode_source": "user",
        "mode_note": "明确选择",
        "status": "done",
        "branch": None,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
        "completed_at": "2026-01-02T00:00:00Z",
    }
    return (
        "---\n" + json.dumps(metadata) + "\n---\n正文保留。\n\n## 状态事件\n\n"
        "| at | from | to | reason | evidence |\n|---|---|---|---|---|\n"
        "| 2026-01-02T00:00:00Z | in-progress | done | 旧完成 | 历史验收 |\n"
    )


class LegacyEventTests(unittest.TestCase):
    def test_legacy_read_is_frontmatter_only_and_lazy(self):
        text = legacy_text()
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            document = TaskDocument.parse(text)
        self.assertEqual(document.frontmatter["status"], "done")
        self.assertEqual(document.text, text)
        self.assertIn("旧格式事件，不追溯", output.getvalue())
        self.assertTrue(document.legacy_events)
        self.assertEqual(
            document.updated({"mode_note": "新说明"}).event_lines, document.event_lines
        )

    def test_legacy_does_not_hide_bad_rows_or_frontmatter(self):
        for text in (
            legacy_text().replace("历史验收", ""),
            legacy_text().replace("in-progress | done", "garbage | done"),
            legacy_text().replace("2026-01-02T00:00:00Z |", "2026-02-30T00:00:00Z |"),
            legacy_text().replace('"schema_version": 1', '"schema_version": 99'),
        ):
            with self.subTest(text=text), self.assertRaises(TaskDataError):
                TaskDocument.parse(text)

    def test_baseline_is_lazy_immutable_and_suffix_is_strict(self):
        document = TaskDocument.parse(legacy_text())
        event = {
            "at": "2026-01-03T00:00:00Z",
            "from": "done",
            "to": "done",
            "reason": "写入者甲：开始核对",
            "evidence": "本地事实",
        }
        changed = document.updated({"updated_at": event["at"]}, event=event)
        self.assertEqual(changed.event_lines[:1], document.event_lines)
        self.assertEqual(json.loads(changed.events[0]["evidence"])["rows"], 1)
        self.assertFalse(changed.baseline_changed)
        self.assertTrue(
            TaskDocument.parse(
                changed.text.replace("历史验收", "已被改写")
            ).baseline_changed
        )
        # 基线内行只读不校验；即使旧行损坏也报告哈希差异。
        self.assertTrue(
            TaskDocument.parse(
                changed.text.replace("in-progress | done", "bad | bad")
            ).baseline_changed
        )
        for source in ("in-progress", "unknown"):
            with self.subTest(source=source), self.assertRaises(TaskDataError):
                changed.updated({}, event={**event, "from": source})
        with self.assertRaises(TaskDataError):
            TaskDocument.parse(
                changed.text + "| invalid | bad | done | 坏事件 | 证据 |\n"
            )

    def test_baseline_append_at_eof_does_not_report_its_own_separator(self):
        for ending in ("\n", "\r\n"):
            text = legacy_text().replace("\n", ending).rstrip("\r\n")
            document = TaskDocument.parse(text)
            changed = document.updated(
                {},
                event={
                    "at": "2026-01-03T00:00:00Z",
                    "from": "done",
                    "to": "done",
                    "reason": "甲：核对",
                    "evidence": "本地事实",
                },
            )
            self.assertTrue(changed.text.startswith(text + ending))
            self.assertFalse(changed.baseline_changed)

    def test_mixed_legacy_and_invalid_current_row_is_rejected(self):
        with self.assertRaises(TaskDataError):
            TaskDocument.parse(
                legacy_text()
                + "| 2026-01-03T00:00:00Z | done | blocked | 非法转换 | 证据 |\n"
            )


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sbtd-sync-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "project"
        self.root.mkdir()
        (self.root / ".gitignore").write_text("/.sbtd/\n", encoding="utf-8")
        from sbtd_task_state import TaskStore

        self.store = TaskStore(self.root)

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-C", str(self.root), *args],
            env={
                **os.environ,
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_AUTHOR_NAME": "Test",
                "GIT_AUTHOR_EMAIL": "test@example.invalid",
                "GIT_COMMITTER_NAME": "Test",
                "GIT_COMMITTER_EMAIL": "test@example.invalid",
            },
            stderr=subprocess.PIPE,
            text=True,
        ).strip()

    def test_file_check_records_hashes_and_never_reopens_done(self):
        from sbtd_task_sync import TaskSync

        sync = TaskSync(self.store)
        (self.root / "src").mkdir()
        source = self.root / "src/code.txt"
        source.write_text("first")
        self.store.create("sync", body="范围", confirmed=True)
        sync.record("sync", step="实现", writer="甲", scope=("src",), confirmed=True)
        sync.record(
            "sync",
            step="实现",
            writer="甲",
            completed=True,
            files=("src/code.txt",),
            validation="人工核对通过",
            confirmed=True,
        )
        self.assertEqual(sync.check().method, "C")
        self.assertEqual(sync.check().differences, ())
        source.touch()
        self.assertEqual(sync.check().differences, ())
        for status in ("checking", "done"):
            self.store.transition(
                "sync", status, reason="甲：验收", evidence="结果通过", confirmed=True
            )
        source.write_text("other")
        result = sync.check()
        self.assertIn("文件内容变化：src/code.txt", result.differences)
        saved = sync.record_check(result, writer="乙", confirmed=True)
        self.assertEqual(saved.document.frontmatter["status"], "done")
        self.assertIn("发现未记录的改动", saved.document.events[-1]["reason"])


class LockCleanupTests(unittest.TestCase):
    def setUp(self):
        from sbtd_task_state import TaskStore

        self.tmp = tempfile.TemporaryDirectory(prefix="sbtd-lock-cleanup-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = TaskStore(self.root)
        self.target = self.root / "target.txt"
        self.lock = self.root / "target.txt.sbtd-lock"

    def test_windows_unlink_requires_closed_lock_descriptor(self):
        real_open, real_unlink = os.open, Path.unlink
        lock_fd = None

        def capture_open(path, *args, **kwargs):
            nonlocal lock_fd
            descriptor = real_open(path, *args, **kwargs)
            if Path(path) == self.lock:
                lock_fd = descriptor
            return descriptor

        def windows_unlink(path, *args, **kwargs):
            if path == self.lock:
                self.assertIsNotNone(lock_fd)
                try:
                    os.fstat(lock_fd)
                except OSError:
                    pass
                else:
                    raise PermissionError("Windows refuses unlink of an open lock")
            return real_unlink(path, *args, **kwargs)

        with (
            mock.patch("sbtd_task_state.os.open", side_effect=capture_open),
            mock.patch.object(Path, "unlink", windows_unlink),
        ):
            self.store._write("target.txt", b"persisted", None)

        self.assertEqual(self.target.read_bytes(), b"persisted")
        self.assertFalse(self.lock.exists())

    def test_transient_permission_error_does_not_fail_completed_write(self):
        real_unlink = Path.unlink
        attempts = 0

        def transient_unlink(path, *args, **kwargs):
            nonlocal attempts
            if path == self.lock:
                attempts += 1
                if attempts <= 2:
                    raise PermissionError("temporarily busy")
            return real_unlink(path, *args, **kwargs)

        with mock.patch.object(Path, "unlink", transient_unlink):
            self.store._write("target.txt", b"persisted", None)

        self.assertEqual(self.target.read_bytes(), b"persisted")
        self.assertFalse(self.lock.exists())

    def test_persistent_permission_error_reports_completed_write_and_stale_lock(self):
        from sbtd_task_state import TaskStateError

        with (
            mock.patch.object(Path, "unlink", side_effect=PermissionError("busy")) as unlink,
            self.assertRaises(TaskStateError) as raised,
        ):
            self.store._write("target.txt", b"persisted", None)

        self.assertIn("写入已完成", str(raised.exception))
        self.assertIn(str(self.lock), str(raised.exception))
        self.assertIn("确认无其他 writer 后手动删除", raised.exception.next_step)
        self.assertLessEqual(unlink.call_count, 5)
        self.assertEqual(self.target.read_bytes(), b"persisted")
        self.assertTrue(self.lock.exists())
        self.assertEqual(list(self.root.glob(".sbtd-write-*")), [])

    def test_cleanup_error_does_not_mask_original_write_error(self):
        from sbtd_task_state import TaskStateError

        self.target.write_bytes(b"original")
        with (
            mock.patch.object(Path, "unlink", side_effect=PermissionError("busy")),
            mock.patch("sbtd_task_state.os.replace", side_effect=OSError("write failed")),
            self.assertRaisesRegex(TaskStateError, "task state write failed"),
        ):
            self.store._write("target.txt", b"replacement", b"original")

        self.assertEqual(self.target.read_bytes(), b"original")
        self.assertTrue(self.lock.exists())
        self.assertEqual(list(self.root.glob(".sbtd-write-*")), [])


if __name__ == "__main__":
    unittest.main()
