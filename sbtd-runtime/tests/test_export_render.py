"""R2.1a export renderer: offline HTML, full CSV, shared redaction."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from csv_export import CSV_SCHEMA_VERSION, serialize_csv
from export_render import (
    REDACTION_POLICY_VERSION,
    RENDERER_VERSION,
    ExportCancelled,
    ExportRenderer,
    default_presentation,
    load_panel_manifest,
)
from report_snapshot import SnapshotStore
from stats_query import query
from test_csv_export import _dataset, _rows, _scope

FORBIDDEN = (
    "<script",
    '<link href="http',
    "@import",
    "url(http",
    "http://",
    "https://",
    "file://",
    "/usr/share/fonts",
    ".woff",
    ".ttf",
)
CJK_FONTS = (
    "PingFang SC",
    "Hiragino Sans GB",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
    "Noto Sans CJK JP",
)
MALICIOUS = (
    "中文日本語 /home/ada/secret-key.txt ada@example.com "
    "Bearer sk-live-abcdefghij "
    '<script src="https://evil.example/x">@import url(http://evil.example/a)'
)
RAW_JSON = '{"messages":[{"content":"SECRET_CONV"}],"privacy":{"exportable":true}}'


def _panel_metrics(manifest: dict) -> list[str]:
    ids = []
    for panel in manifest["panels"]:
        for metric_id in panel["metric_ids"]:
            if metric_id not in ids:
                ids.append(metric_id)
    return ids


def _section(html: str, panel_id: str) -> str:
    marker = f'id="{panel_id}"'
    start = html.index(marker)
    next_panel = html.find("<section ", start + len(marker))
    return html[start:] if next_panel < 0 else html[start:next_panel]


class _Paging:
    def __init__(self, store, limit=2, cancel_after=None, flag=None):
        self.store = store
        self.limit = limit
        self.cancel_after = cancel_after
        self.flag = flag
        self.calls = 0

    def dataset_page(self, snapshot_id, cursor=None, limit=100, **kwargs):
        self.calls += 1
        page = self.store.dataset_page(snapshot_id, cursor, self.limit)
        if self.cancel_after is not None and self.calls >= self.cancel_after:
            self.flag[0] = True
        return page


class ExportRenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = load_panel_manifest()
        self.dataset = _dataset()
        self.metrics = _panel_metrics(self.manifest)
        temporary = tempfile.TemporaryDirectory(prefix="sbtd-export-render-")
        self.addCleanup(temporary.cleanup)
        self.store = SnapshotStore(Path(temporary.name) / "runtime")
        self.scope = _scope(self.dataset, self.metrics)
        self.snapshot = self.store.create_or_reuse(self.dataset, self.scope)
        self.renderer = ExportRenderer(self.store)

    def test_csv_cursor_walk_matches_schema_without_truncation(self) -> None:
        paging = _Paging(self.store, limit=2)
        renderer = ExportRenderer(paging)
        before = json.dumps(self.snapshot.rows, sort_keys=True, default=str)
        digest = self.snapshot.snapshot_digest
        payload, meta = renderer(
            self.snapshot, "csv", default_presentation(self.manifest), lambda: False
        )
        self.assertGreater(paging.calls, 1)
        self.assertEqual(payload, serialize_csv(self.snapshot))
        self.assertTrue(payload.startswith(b"\xef\xbb\xbf"))
        rows = _rows(payload)
        detail = [
            row for row in rows if row["record_type"] not in {"metadata", "metric"}
        ]
        direct = [
            row
            for row in _rows(serialize_csv(self.snapshot))
            if row["record_type"] not in {"metadata", "metric"}
        ]
        self.assertEqual(
            [(row["record_type"], row["record_id"]) for row in detail],
            [(row["record_type"], row["record_id"]) for row in direct],
        )
        self.assertEqual(rows[0]["export_schema_version"], "1.1")
        self.assertEqual(CSV_SCHEMA_VERSION, "1.1")
        metrics = {
            row["metric_id"]: row for row in rows if row["record_type"] == "metric"
        }
        self.assertEqual(metrics["tasks.touched"]["metric_value"], "2")
        self.assertEqual(metrics["steps.success_rate_observed"]["metric_value"], "1/2")
        self.assertEqual(
            metrics["duration.step_p50/p95"]["metric_id"], "duration.step_p50/p95"
        )
        self.assertIn("parent/demo/leaf", {row["logical_task_id"] for row in detail})
        usage = next(row for row in rows if row["record_id"] == "req_1")
        self.assertEqual(usage["cache_read_tokens"], "")
        self.assertEqual(usage["reasoning_tokens"], "2")
        self.assertEqual(meta["export_schema_version"], "1.1")
        self.assertEqual(meta["redaction_policy_version"], "1")
        self.assertEqual(meta["byte_size"], len(payload))
        self.assertEqual(meta["snapshot_id"], self.snapshot.snapshot_id)
        self.assertEqual(self.snapshot.snapshot_digest, digest)
        self.assertEqual(
            json.dumps(self.snapshot.rows, sort_keys=True, default=str), before
        )

    def test_html_contains_every_panel_and_shared_metric_values(self) -> None:
        payload, meta = self.renderer(self.snapshot, "html", None, lambda: False)
        html = payload.decode("utf-8")
        answer = query(self.dataset, self.scope)
        positions = []
        for panel_id in meta["panel_ids"]:
            self.assertIn(f'id="{panel_id}"', html)
            positions.append(html.index(f'id="{panel_id}"'))
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(
            meta["panel_ids"],
            [panel["panel_id"] for panel in self.manifest["panels"]],
        )
        self.assertIn("duration.step_p50/p95", html)
        self.assertIn(">2<", html)
        self.assertIn("1/2", html)
        self.assertEqual(
            str(answer["metrics"]["tasks.touched"]["value"]),
            "2",
        )
        self.assertIn(self.snapshot.effective_from, html)
        self.assertIn(self.snapshot.timezone, html)
        self.assertIn("数据水位", html)
        self.assertIn("watermark_seq", html)
        self.assertIn("覆盖", html)
        self.assertIn("数据质量", _section(html, "data-quality"))
        self.assertNotIn('"exportable"', html)
        self.assertNotIn("<script", html.lower())
        for token in FORBIDDEN:
            self.assertNotIn(token, html)
        for font in CJK_FONTS:
            self.assertIn(font, html)
        self.assertEqual(meta["mime_type"], "text/html; charset=utf-8")
        self.assertEqual(meta["renderer_version"], RENDERER_VERSION)
        self.assertEqual(meta["redaction_policy_version"], REDACTION_POLICY_VERSION)
        self.assertEqual(meta["byte_size"], len(payload))
        self.assertNotIn("password", json.dumps(meta))
        self.assertNotIn("/home", json.dumps(meta))

    def test_presentation_order_width_legend_sort_and_preview(self) -> None:
        order = list(reversed(default_presentation(self.manifest)["panel_order"]))
        state = default_presentation(self.manifest)
        state["theme"] = "light"
        state["report_width_px"] = 0.5
        state["panel_order"] = order
        state["legend_state"] = {"tasks.touched": False}
        state["table_sort"] = {"task-audit-detail": "worktree_id:desc"}
        state["expanded_detail_ids"] = ["step-performance", "task_leaf"]
        payload, meta = self.renderer(self.snapshot, "html", state, lambda: False)
        html = payload.decode("utf-8")
        positions = [html.index(f'id="{panel_id}"') for panel_id in order]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(meta["panel_ids"], order)
        self.assertIn('data-theme="light"', html)
        self.assertIn("width: 0.5px", html)
        trend = _section(html, "activity-trend")
        self.assertIn("隐藏系列：tasks.touched", trend)
        self.assertNotIn('data-series="tasks.touched"', trend)
        self.assertIn(">2<", _section(html, "overview"))
        audit = _section(html, "task-audit-detail")
        self.assertLess(audit.index("task_other"), audit.index("task_leaf"))
        self.assertIn("步骤时间线", audit)
        self.assertIn("panel-detail", _section(html, "step-performance"))
        self.assertNotIn("panel-detail", _section(html, "activity-trend"))
        preview = default_presentation(self.manifest)
        preview["table_sort"] = {"task-audit-detail": "worktree_id:desc"}
        preview["preview_row_sets"] = {"task-audit-detail": 1}
        preview_html = self.renderer(self.snapshot, "html", preview, lambda: False)[
            0
        ].decode("utf-8")
        preview_audit = _section(preview_html, "task-audit-detail")
        self.assertIn("展示 1 条／范围内总", preview_audit)
        self.assertIn("task_other", preview_audit)
        self.assertNotIn("task_leaf", preview_audit)

        zero = default_presentation(self.manifest)
        zero["report_width_px"] = 0
        zero["preview_row_sets"] = {"task-audit-detail": 0.5}
        quiet, _ = self.renderer(self.snapshot, "html", zero, lambda: False)
        quiet_html = quiet.decode("utf-8")
        self.assertIn("width: 0px", quiet_html)
        self.assertIn("展示 0 条／范围内总", _section(quiet_html, "task-audit-detail"))

    def test_redaction_is_shared_and_does_not_change_metrics(self) -> None:
        dataset = json.loads(json.dumps(self.dataset))
        for task in dataset["tasks"]:
            task["worktree_id"] = MALICIOUS
        for event in dataset["events"]:
            if event["event_id"] == "evt_created_leaf":
                event["privacy"]["exportable"] = False
                event["extensions"] = {
                    "actor_alias": "PRIVATE_ALIAS_SHOULD_VANISH",
                    "conversation": "SECRET_EXTENSION_MARKER",
                }
            elif event["event_id"] == "evt_leaf_done_1":
                event["extensions"] = {"actor_alias": "=HYPERLINK(1)"}
            elif event["event_id"] == "evt_leaf_done_2":
                event["extensions"] = {"actor_alias": RAW_JSON}
            else:
                event["extensions"] = {
                    "actor_alias": MALICIOUS,
                    "conversation": "SECRET_EXTENSION_MARKER",
                }
        scope = _scope(
            dataset,
            ["tasks.touched", "steps.success_rate_observed", "duration.step_p50/p95"],
        )
        snapshot = self.store.create_or_reuse(dataset, scope)
        answer = query(dataset, scope)
        csv_payload, csv_meta = self.renderer(
            snapshot, "csv", default_presentation(self.manifest), lambda: False
        )
        html_payload, html_meta = self.renderer(
            snapshot, "html", default_presentation(self.manifest), lambda: False
        )
        html = html_payload.decode("utf-8")
        rows = _rows(csv_payload)
        metrics = {
            row["metric_id"]: row for row in rows if row["record_type"] == "metric"
        }
        self.assertEqual(metrics["tasks.touched"]["metric_value"], "2")
        self.assertEqual(metrics["steps.success_rate_observed"]["metric_value"], "1/2")
        self.assertEqual(
            metrics["tasks.touched"]["metric_value"],
            str(answer["metrics"]["tasks.touched"]["value"]),
        )
        self.assertEqual(
            metrics["duration.step_p50/p95"]["metric_id"], "duration.step_p50/p95"
        )
        self.assertNotIn("evt_created_leaf", {row["record_id"] for row in rows})
        csv_text = csv_payload.decode("utf-8")
        joined = csv_text + html
        for secret in (
            "PRIVATE_ALIAS_SHOULD_VANISH",
            "SECRET_EXTENSION_MARKER",
            "SECRET_CONV",
            "/home/ada",
            "ada@example.com",
            "sk-live-abcdefghij",
            "https://evil.example",
            "http://evil.example",
            "@import",
            "url(http",
        ):
            self.assertNotIn(secret, joined)
        self.assertNotIn("<script", html.lower())
        self.assertIn("中文日本語", html)
        self.assertIn("中文日本語", csv_text)
        self.assertIn("[redacted", html)
        self.assertIn("[redacted", csv_text)
        self.assertIn("parent/demo/leaf", joined)
        self.assertIn("duration.step_p50/p95", html)
        formula = [
            row["actor_alias"] for row in rows if row["actor_alias"].startswith("'")
        ]
        self.assertTrue(formula)
        self.assertEqual(
            csv_meta["redaction_policy_version"],
            html_meta["redaction_policy_version"],
        )
        self.assertEqual(csv_meta["redaction_policy_version"], "1")
        self.assertNotIn('"exportable"', html)
        self.assertNotIn("evt_created_leaf", html)
        self.assertNotIn("evt_created_leaf", csv_text)
        counts = {
            family["record_type"]: sum(
                row["record_type"] == family["record_type"] for row in rows
            )
            for family in csv_meta["dataset_manifest"]
        }
        self.assertEqual(
            {
                item["record_type"]: item["rows"]
                for item in csv_meta["dataset_manifest"]
            },
            counts,
        )
        recorded = {
            row["metadata_key"]: row["metadata_value"]
            for row in rows
            if row["record_type"] == "metadata"
        }
        for family, count in counts.items():
            self.assertEqual(recorded[f"rows:{family}"], str(count))

    def test_structured_secret_text_is_redacted_in_both_formats(self) -> None:
        dataset = _dataset()
        secret = '{"password":"SYNTHETIC_SECRET_987","label":"safe"}'
        for task in dataset["tasks"]:
            task["worktree_id"] = secret
        snapshot = self.store.create_or_reuse(dataset, self.scope)
        for format_name in ("html", "csv"):
            with self.subTest(format=format_name):
                payload, _ = self.renderer(snapshot, format_name, None, lambda: False)
                self.assertNotIn(b"SYNTHETIC_SECRET_987", payload)

    def test_structured_metric_keys_and_leaves_are_redacted(self) -> None:
        dataset = json.loads(json.dumps(self.dataset))
        hostile_key = '{"password":"CUR_SECRET_99","x":"y"}'
        hostile_leaf = '{"password":"STATE_SECRET_77","x":"y"}'
        for event in dataset["events"]:
            usage = event.get("usage")
            if isinstance(usage, dict):
                usage.update(
                    currency=hostile_key, cost_amount=3.5, cost_status="reported"
                )
            state = event.get("state")
            if event.get("event_type") == "task.state_changed" and isinstance(
                state, dict
            ):
                state["current"] = hostile_leaf
        snapshot = self.store.create_or_reuse(dataset, self.scope)
        for format_name in ("html", "csv"):
            with self.subTest(format=format_name):
                payload, _ = self.renderer(snapshot, format_name, None, lambda: False)
                self.assertNotIn(b"CUR_SECRET_99", payload)
                self.assertNotIn(b"STATE_SECRET_77", payload)
                self.assertNotIn(b'"password"', payload)

    def test_embedded_identifier_secrets_are_redacted(self) -> None:
        dataset = json.loads(json.dumps(self.dataset))
        secret = '{"password":"DQ_LEAK_5"}'
        for event in dataset["events"]:
            if event["event_id"] == "evt_created_untimed":
                event["event_id"] = secret
                event["occurred_at"] = None
                event["provenance"]["source_event_id"] = secret
        snapshot = self.store.create_or_reuse(dataset, self.scope)
        for format_name in ("html", "csv"):
            with self.subTest(format=format_name):
                payload, _ = self.renderer(snapshot, format_name, None, lambda: False)
                self.assertNotIn(b"DQ_LEAK_5", payload)

    def test_cancellation_stops_before_publish_and_preserves_snapshot(self) -> None:
        digest = self.snapshot.snapshot_digest
        flag = [True]
        paging = _Paging(self.store)
        renderer = ExportRenderer(paging)
        with self.assertRaises(ExportCancelled):
            renderer(self.snapshot, "csv", None, lambda: flag[0])
        self.assertEqual(paging.calls, 0)
        flag[0] = False
        paging = _Paging(self.store, limit=2, cancel_after=1, flag=flag)
        renderer = ExportRenderer(paging)
        with self.assertRaises(ExportCancelled):
            renderer(self.snapshot, "html", default_presentation(), lambda: flag[0])
        self.assertGreaterEqual(paging.calls, 1)
        self.assertEqual(self.snapshot.snapshot_digest, digest)
        self.assertEqual(
            self.store.get(self.snapshot.snapshot_id).snapshot_id,
            self.snapshot.snapshot_id,
        )


if __name__ == "__main__":
    unittest.main()
