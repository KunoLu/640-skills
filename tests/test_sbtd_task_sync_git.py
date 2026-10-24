from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sbtd-workflow-onboard/scripts"))

from sbtd_task_state import TaskStateError, TaskStore
from sbtd_task_sync import TaskSync

from tests import test_sbtd_task_status_sync as fixtures


class SyncGitTests(unittest.TestCase):
    setUp = fixtures.ProgressTests.setUp
    git = fixtures.ProgressTests.git

    def test_file_inventory_add_delete_evidence_and_same_mtime(self):
        sync = TaskSync(self.store)
        (self.root / "src").mkdir()
        (self.root / "proof").mkdir()
        source = self.root / "src/a"
        source.write_text("one")
        evidence = self.root / "proof/result"
        evidence.write_text("passed")
        self.store.create("sync", body="范围", confirmed=True)
        sync.record("sync", step="验证", writer="甲", scope=("src",), confirmed=True)
        sync.record(
            "sync",
            step="验证",
            writer="甲",
            completed=True,
            validation="通过",
            evidence_files=("proof/result",),
            confirmed=True,
        )
        stamp = source.stat()
        source.write_text("two")
        os.utime(source, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        evidence.unlink()
        (self.root / "src/new").write_text("new")
        differences = sync.check().differences
        self.assertIn("文件内容变化：src/a", differences)
        self.assertIn("删除文件：proof/result", differences)
        self.assertIn("新增文件：src/new", differences)

    def test_git_init_rebind_keeps_hashes_and_routes_tracking_separately(self):
        sync = TaskSync(self.store)
        (self.root / "src").mkdir()
        (self.root / "src/a").write_text("one")
        for task_id, mode in (("local", "default"), ("shared", "lite")):
            self.store.create(task_id, body="范围", mode=mode, confirmed=True)
            sync.record(
                task_id, step="实现", writer="甲", scope=("src",), confirmed=True
            )
        old = self.store.inspect("shared").document.event_lines
        self.git("init", "-b", "main")
        for task_id in ("local", "shared"):
            self.store.rebind(
                task_id,
                expected_branch=None,
                reason="甲：中途 git init",
                evidence="本地仓库",
                confirmed=True,
            )
        self.assertEqual(
            self.store.inspect("shared").document.event_lines[: len(old)], old
        )
        self.assertEqual(sync.check("shared").method, "C")
        self.git("add", ".")
        self.git("commit", "-m", "绑定")
        self.assertEqual(sync.check("shared").method, "B")
        self.assertEqual(sync.check("shared").differences, ())
        self.assertFalse(sync.check("shared").discarded)
        self.assertEqual(sync.check("local").method, "C")

    def test_git_content_comparison_preserves_crlf_bytes(self):
        self.git("init", "-b", "main")
        created = self.store.create("sync", body="任务", mode="lite", confirmed=True)
        path = self.root / created.task_path
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        self.git("add", ".")
        self.git("commit", "-m", "CRLF 任务")
        self.assertEqual(TaskSync(self.store).check("sync").differences, ())

    def test_remote_missing_task_is_unknown_not_a_failed_check(self):
        self.git("init", "-b", "main")
        self.git("add", ".")
        self.git("commit", "-m", "项目")
        remote = Path(self.tmp.name) / "remote.git"
        self.git("clone", "--bare", str(self.root), str(remote))
        self.git("remote", "add", "origin", str(remote))
        self.git("switch", "-c", "new-task")
        self.store.create("sync", body="新任务", mode="lite", confirmed=True)
        self.git("add", ".")
        self.git("commit", "-m", "新任务")
        result = TaskSync(self.store).check("sync")
        self.assertEqual(result.method, "A")
        self.assertFalse(result.discarded)
        self.assertIn("默认分支未包含 task；不可考，不推断丢弃", result.notes)
        before = self.git("rev-parse", "refs/remotes/origin/main")
        with self.assertRaises(TaskStateError):
            TaskSync(TaskStore(self.root, read_only=True)).check("sync")
        self.assertEqual(self.git("rev-parse", "refs/remotes/origin/main"), before)

    def test_remote_check_content_and_missing_recorded_branch(self):
        sync = TaskSync(self.store)
        self.git("init", "-b", "main")
        created = self.store.create("sync", body="任务", mode="strict", confirmed=True)
        self.git("add", ".")
        self.git("commit", "-m", "任务")
        remote = Path(self.tmp.name) / "remote.git"
        self.git("clone", "--bare", str(self.root), str(remote))
        self.git("remote", "add", "origin", str(remote))
        result = sync.check("sync")
        self.assertEqual(result.method, "A")
        self.assertEqual(result.differences, ())
        self.assertFalse(result.discarded)
        self.git("switch", "-c", "work")
        self.store.rebind(
            "sync",
            expected_branch="main",
            reason="甲：切换",
            evidence="实际分支",
            confirmed=True,
        )
        self.git("add", created.task_path)
        self.git("commit", "-m", "重绑定")
        result = sync.check("sync")
        self.assertTrue(result.discarded)
        self.assertIn("默认分支 task 内容与工作区不同", result.differences)
        self.git("switch", "--detach")
        self.assertTrue(sync.check("sync").discarded)

    def test_local_head_difference_is_not_discarded(self):
        sync = TaskSync(self.store)
        self.git("init", "-b", "main")
        self.store.create("sync", body="任务", mode="lite", confirmed=True)
        self.git("add", ".")
        self.git("commit", "-m", "任务")
        sync.record("sync", step="实现", writer="甲", confirmed=True)
        result = sync.check("sync")
        self.assertEqual(result.method, "B")
        self.assertFalse(result.discarded)
        self.assertIn("本地 HEAD task 内容与工作区不同", result.differences)

    def test_baseline_drift_is_recorded_without_reopening(self):
        sync = TaskSync(self.store)
        task = self.root / "ai/tasks/sync/task.md"
        task.parent.mkdir(parents=True)
        task.write_text(fixtures.legacy_text())
        result = sync.check("sync")
        self.assertEqual(result.differences, ())
        self.assertIn("旧格式事件，不追溯", result.notes)
        self.assertEqual(task.read_text(), fixtures.legacy_text())
        sync.record("sync", step="核对", writer="甲", confirmed=True)
        task.write_text(task.read_text().replace("历史验收", "不可考"))
        saved = sync.record_check(sync.check("sync"), writer="乙", confirmed=True)
        self.assertEqual(saved.document.frontmatter["status"], "done")
        self.assertIn("旧事件基线", saved.document.events[-1]["evidence"])

    def test_new_done_requires_checking_and_old_done_can_explicitly_reopen(self):
        created = self.store.create("new", body="任务", confirmed=True)
        self.store.transition(
            "new", "in-progress", reason="甲：开始", evidence="范围", confirmed=True
        )
        before = (self.root / created.task_path).read_bytes()
        with self.assertRaises(TaskStateError):
            self.store.transition(
                "new", "done", reason="甲：完成", evidence="验证", confirmed=True
            )
        self.assertEqual((self.root / created.task_path).read_bytes(), before)
        task = self.root / "ai/tasks/sync/task.md"
        task.parent.mkdir(parents=True)
        task.write_text(fixtures.legacy_text())
        reopened = self.store.reopen(
            "sync", reason="甲：明确重开", evidence="新的工作", confirmed=True
        )
        self.assertEqual(reopened.document.frontmatter["status"], "planned")
        self.assertTrue(reopened.document.has_baseline)
        self.assertEqual(reopened.document.events[-1]["from"], "done")

    def test_concurrent_processes_do_not_lose_successful_events(self):
        self.store.create("sync", body="任务", confirmed=True)
        script = """
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from sbtd_task_state import TaskStore, TaskStateError
from sbtd_task_sync import TaskSync
root, writer = Path(sys.argv[2]), sys.argv[3]
(root / ('ready-' + writer)).touch()
while len(list(root.glob('ready-*'))) < 2:
    time.sleep(.01)
try:
    TaskSync(TaskStore(root)).record('sync', step='并发', writer=writer, confirmed=True)
except TaskStateError:
    sys.exit(3)
"""
        processes = [
            subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    "-c",
                    script,
                    str(fixtures.ROOT / "sbtd-workflow-onboard/scripts"),
                    str(self.root),
                    writer,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            for writer in ("甲", "乙")
        ]
        results = []
        for writer, process in zip(("甲", "乙"), processes):
            stdout, stderr = process.communicate(timeout=30)
            self.assertIn(process.returncode, (0, 3), (stdout, stderr))
            results.append((writer, process.returncode))
        successful = []
        for writer, returncode in results:
            if returncode == 0:
                successful.append(writer)
            else:
                TaskSync(self.store).record(
                    "sync", step="并发", writer=writer, confirmed=True
                )
        self.assertTrue(successful)
        events = self.store.inspect("sync").document.events
        self.assertEqual(
            sorted(event["reason"] for event in events),
            ["乙：开始 并发", "甲：开始 并发"],
        )

    def test_readonly_and_stale_check_do_not_write(self):
        created = self.store.create("sync", body="任务", confirmed=True)
        result = TaskSync(self.store).check("sync")
        TaskSync(self.store).record("sync", step="实现", writer="甲", confirmed=True)
        before = (self.root / created.task_path).read_bytes()
        with self.assertRaises(TaskStateError):
            TaskSync(self.store).record_check(result, writer="乙", confirmed=True)
        with self.assertRaises(TaskStateError):
            TaskSync(TaskStore(self.root, read_only=True)).record(
                "sync", step="实现", writer="乙", confirmed=True
            )
        self.assertEqual((self.root / created.task_path).read_bytes(), before)

    def test_legacy_tolerance_is_identical_for_a_b_c(self):
        path = self.root / "ai/tasks/sync/task.md"
        path.parent.mkdir(parents=True)
        path.write_text(fixtures.legacy_text())
        sync = TaskSync(self.store)
        self.assertEqual(sync.check("sync").method, "C")
        self.git("init", "-b", "main")
        self.store.rebind(
            "sync",
            expected_branch=None,
            reason="甲：git init",
            evidence="实际仓库",
            confirmed=True,
        )
        # 构造尚未写基线的合法旧文档；用于验证三种只读核对相同。
        path.write_text(
            fixtures.legacy_text().replace('"branch": null', '"branch": "main"')
        )
        self.git("add", ".")
        self.git("commit", "-m", "旧任务")
        before = path.read_bytes()
        result = sync.check("sync")
        self.assertEqual(result.method, "B")
        self.assertEqual(result.differences, ())
        remote = Path(self.tmp.name) / "remote.git"
        self.git("clone", "--bare", str(self.root), str(remote))
        self.git("remote", "add", "origin", str(remote))
        self.git("commit", "--amend", "-m", "同内容不同历史")
        result = sync.check("sync")
        self.assertEqual(result.method, "A")
        self.assertEqual(result.differences, ())
        self.assertIn("旧格式事件，不追溯", result.notes)
        self.assertEqual(path.read_bytes(), before)

    def test_unicode_task_finish_commit_uses_exact_path(self):
        self.git("init", "-b", "main")
        created = self.store.create(
            "中文任务", body="任务", mode="lite", confirmed=True
        )
        for status in ("in-progress", "checking"):
            self.store.transition(
                "中文任务", status, reason="甲：进展", evidence="验证", confirmed=True
            )
        self.git("add", ".")
        self.git("commit", "-m", "核验")
        clean = self.git("rev-parse", "HEAD")
        self.store.transition(
            "中文任务",
            "done",
            reason="甲：完成",
            evidence=json.dumps({"clean_sha": clean, "ci_run": "local-fixture"}),
            confirmed=True,
        )
        self.git("add", created.task_path)
        self.git("commit", "-m", "收尾")
        TaskSync(self.store).check_finish_commit(created.task_path)

    def test_external_lock_removal_does_not_mask_success_or_remove_new_lock(self):
        from unittest import mock

        for replacement in (False, True):
            task_id = "replaced" if replacement else "removed"
            created = self.store.create(task_id, body="任务", confirmed=True)
            path = self.root / created.task_path
            lock = path.with_name("task.md.sbtd-lock")
            replace = os.replace

            def interfere(
                source, target, replace=replace, lock=lock, replacement=replacement
            ):
                replace(source, target)
                lock.unlink()
                if replacement:
                    lock.write_text("另一写入者")

            with mock.patch("sbtd_task_state.os.replace", side_effect=interfere):
                saved = TaskSync(self.store).record(
                    task_id, step="核对", writer="甲", confirmed=True
                )
            self.assertEqual(
                self.store.inspect(task_id).document.text, saved.document.text
            )
            self.assertEqual(lock.exists(), replacement)
            if replacement:
                self.assertEqual(lock.read_text(), "另一写入者")

    def test_finish_commit_only_accepts_exact_task_closure(self):
        self.git("init", "-b", "main")
        created = self.store.create("sync", body="原正文", mode="lite", confirmed=True)
        for status in ("in-progress", "checking"):
            self.store.transition(
                "sync", status, reason="甲：进展", evidence="验证", confirmed=True
            )
        self.git("add", ".")
        self.git("commit", "-m", "核验")
        clean = self.git("rev-parse", "HEAD")
        self.store.transition(
            "sync",
            "done",
            reason="甲：done",
            evidence=json.dumps({"clean_sha": clean, "ci_run": "local-fixture"}),
            confirmed=True,
        )
        self.git("add", created.task_path)
        self.git("commit", "-m", "收尾")
        TaskSync(self.store).check_finish_commit(created.task_path)
        path = self.root / created.task_path
        valid = path.read_bytes()
        for changed in (
            valid.replace("原正文".encode(), "篡改正文".encode()),
            valid.replace(b"local-fixture", b""),
            valid.replace(clean.encode(), b"0" * len(clean)),
        ):
            path.write_bytes(changed)
            self.git("add", created.task_path)
            self.git("commit", "--amend", "--no-edit")
            with self.assertRaises(TaskStateError):
                TaskSync(self.store).check_finish_commit(created.task_path)
        path.write_bytes(valid)
        self.git("add", created.task_path)
        self.git("commit", "--amend", "--no-edit")
        (self.root / "other").write_text("越界")
        self.git("add", "other")
        self.git("commit", "--amend", "--no-edit")
        with self.assertRaises(TaskStateError):
            TaskSync(self.store).check_finish_commit(created.task_path)


if __name__ == "__main__":
    unittest.main()
