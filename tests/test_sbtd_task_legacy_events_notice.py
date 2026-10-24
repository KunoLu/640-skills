from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sbtd-workflow-onboard/scripts"))

from sbtd_project import TaskDataError
from sbtd_task_document import TaskDocument
from sbtd_task_state import TaskStateError, TaskStore


HEADER = "| at | from | to | reason | evidence |\n|---|---|---|---|---|\n"
CURRENT_ROW = "| 2026-10-24T12:00:00+08:00 | planned | in-progress | 开始 | 记录 |\n"
LEGACY_ROWS = (
    "| 2026-10-24T12:00:00+08:00 | verifying | done | 历史完成 | 记录 |\n",
    "| 2026-10-24T12:00:00+08:00 | planned | in_progress | 历史开始 | 记录 |\n",
    "| 2026-10-24T12:00:00.123456+08:00 | planned | in_progress | 历史时间 | 记录 |\n",
    "| 2026-10-24T12:00:00+08:00 | in-progress | done | 历史完成 | 记录 |\n",
    "| 2026-10-24T12:00:00+08:00 | done | blocked | 历史转换 | 记录 |\n",
)


def task_text(rows: str, task_id: str = "legacy") -> str:
    metadata = {
        "schema_version": 1,
        "id": task_id,
        "workflow_mode": "strict",
        "mode_source": "user",
        "mode_note": "明确选择",
        "status": "in-progress",
        "branch": None,
        "created_at": "2026-10-24T12:00:00+08:00",
        "updated_at": "2026-10-24T12:00:00+08:00",
        "completed_at": None,
    }
    return "---\n" + json.dumps(metadata) + "\n---\n\n## 状态事件\n\n" + HEADER + rows


class LegacyEventsNoticeTests(unittest.TestCase):
    """PRD 旧格式事件规则 :59–65：完整旧行不阻塞，结构错误不放宽。"""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="sbtd-legacy-notice-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def write_task(self, task_id: str, rows: str) -> Path:
        path = self.root / "ai/tasks" / task_id / "task.md"
        path.parent.mkdir(parents=True)
        path.write_text(task_text(rows, task_id), encoding="utf-8")
        return path

    def test_complete_legacy_rows_use_frontmatter_and_notice_once_without_writes(self):
        path = self.write_task("legacy", CURRENT_ROW)
        for row in (*LEGACY_ROWS, CURRENT_ROW + "".join(LEGACY_ROWS)):
            with self.subTest(row=row):
                path.write_text(task_text(row), encoding="utf-8")
                before = path.read_bytes()
                output = io.StringIO()
                with contextlib.redirect_stderr(output):
                    document = TaskDocument.parse(path.read_text(encoding="utf-8"))
                self.assertTrue(document.legacy_events)
                self.assertEqual(document.events, ())
                self.assertEqual(document.frontmatter["status"], "in-progress")
                self.assertEqual(document.text.encode("utf-8"), before)
                self.assertEqual(output.getvalue().splitlines(), ["旧格式事件，不追溯"])
                self.assertEqual(path.read_bytes(), before)

    def test_malformed_rows_are_not_hidden_by_complete_legacy_rows(self):
        values = ["2026-10-24T12:00:00+08:00", "planned", "in-progress", "开始", "记录"]
        malformed = [values[:-1], values + ["多列"]]
        for index in range(5):
            malformed.append(values[:index] + [" \t "] + values[index + 1:])
        path = self.write_task("legacy", CURRENT_ROW)
        for cells in malformed:
            bad_row = "| " + " | ".join(cells) + " |\n"
            for rows in (bad_row, LEGACY_ROWS[0] + bad_row, bad_row + LEGACY_ROWS[0]):
                with self.subTest(rows=rows):
                    text = task_text(rows)
                    path.write_text(text, encoding="utf-8")
                    before = path.read_bytes()
                    with self.assertRaises(TaskDataError):
                        TaskDocument.parse(text)
                    with self.assertRaises(TaskStateError):
                        TaskStore(self.root, read_only=True)._catalog()
                    self.assertEqual(path.read_bytes(), before)

    def test_current_format_parse_and_catalog_are_silent(self):
        path = self.write_task("current", CURRENT_ROW)
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            document = TaskDocument.parse(path.read_text(encoding="utf-8"))
            records = TaskStore(self.root, read_only=True)._catalog()
        self.assertFalse(document.legacy_events)
        self.assertEqual(document.events, ({
            "at": "2026-10-24T12:00:00+08:00", "from": "planned", "to": "in-progress",
            "reason": "开始", "evidence": "记录",
        },))
        self.assertEqual(records["current"].document.events, document.events)
        self.assertEqual(output.getvalue(), "")

    def test_legacy_rows_do_not_relax_frontmatter_or_table_structure(self):
        text = task_text(LEGACY_ROWS[0])
        invalid = (
            text.replace('"status": "in-progress"', '"status": "verifying"'),
            text.replace('"schema_version": 1', '"schema_version": 99'),
            text.replace('"created_at": "2026-10-24T12:00:00+08:00"', '"created_at": "2026-02-30T12:00:00+08:00"'),
            text.replace("| at | from |", "| when | from |"),
            text.replace("|---|---|---|---|---|", "|---|---|bad|---|---|"),
            text + "\n" + HEADER + CURRENT_ROW,
        )
        for candidate in invalid:
            with self.subTest(candidate=candidate), self.assertRaises(TaskDataError):
                TaskDocument.parse(candidate)

    def test_baseline_preserves_unvalidated_prefix_but_suffix_remains_strict(self):
        prefix = "| old | incomplete |\n"
        evidence = json.dumps({"rows": 1, "sha256": hashlib.sha256(prefix.encode()).hexdigest()})
        baseline = (
            "| 2026-10-24T12:00:00+08:00 | in-progress | in-progress | 旧事件基线：历史 | "
            + evidence + " |\n"
        )
        text = task_text(prefix + baseline)
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            document = TaskDocument.parse(text)
        self.assertTrue(document.has_baseline)
        self.assertFalse(document.baseline_changed)
        self.assertFalse(document.legacy_events)
        self.assertEqual(document.event_lines[0], prefix)
        self.assertEqual(document.events[0]["evidence"], evidence)
        self.assertEqual(output.getvalue(), "")
        for row in LEGACY_ROWS:
            with self.subTest(row=row), self.assertRaises(TaskDataError):
                TaskDocument.parse(text + row)


if __name__ == "__main__":
    unittest.main()
