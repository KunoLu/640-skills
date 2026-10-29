"""Offline HTML and full CSV export for one frozen snapshot.

Metrics are read from the frozen query before any output redaction. Dataset
rows come from SnapshotStore.dataset_page. Presentation changes HTML only.
"""

from __future__ import annotations

import html
import json
import math
import re
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any

from csv_export import CSV_SCHEMA_VERSION, serialize_csv
from report_snapshot import DEFAULT_PAGE_SIZE, REDACTION_POLICY_VERSION
from stats_query import query

RENDERER_VERSION = "r2.1a.1"
_MANIFEST_PATH = Path(__file__).resolve().parent / "contracts" / "panel-manifest.json"
_FONT_FAMILY = (
    '-apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, '
    '"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", '
    '"Noto Sans CJK SC", "Noto Sans CJK JP", sans-serif'
)
# Rendered copy is bilingual. The zh values reproduce the pre-i18n output byte
# for byte; en values carry the English render. Locale arrives in
# presentation_state and only selects copy, never data.
_L10N = {
    "zh": {
        "lang": "zh-CN",
        "title": "SBTD 报告",
        "family": {
            "task": "任务",
            "run": "运行",
            "step": "步骤",
            "gate": "Gate",
            "component": "组件",
            "invocation": "调用",
            "validation_run": "验证运行",
            "validation_case": "验证用例",
            "usage": "用量",
            "artifact": "工件",
            "event": "事件",
            "data_quality": "数据质量",
        },
        "headers": {
            "record": "记录",
            "status": "状态",
            "time": "时间",
            "role": "角色",
            "task": "任务",
            "step": "步骤",
            "attempt": "尝试",
            "start": "开始",
            "duration_ms": "耗时 ms",
            "data_family": "数据族",
            "rows": "行数",
        },
        "count_label": "{title}：展示 {shown} 条／范围内总 {total} 条",
        "no_range_records": "范围内无记录。",
        "no_rows": "无展示行。",
        "no_task_records": "范围内无任务记录。",
        "no_task_steps": "范围内无该任务的步骤记录。",
        "no_task_events": "范围内无该任务的事件。",
        "task_summary": "任务摘要",
        "step_timeline": "步骤时间线（展示 {shown} 条／该任务范围内 {total} 条）",
        "event_preview": (
            "事件预览（最新优先；展示 {shown} 条／该任务范围内 {total} 条）"
        ),
        "coverage_heading": "覆盖（dataset manifest，实测行数）",
        "gaps_heading": "缺口与未关联",
        "unknown_events": "未知发生时间事件：{count} 条{ids}",
        "summary_item": "quality_summary：{text}",
        "warnings_item": "快照告警：{text}",
        "watermarks_item": "来源水位：{text}",
        "watermark_seq_item": "水位序号 watermark_seq：{seq}",
        "unknown_not_carried": "unknown（快照未携带）",
        "none": "无",
        "no_watermark": "无声明（单一本地来源）",
        "ids_wrapper": "（{text}）",
        "list_sep": "、",
        "summary_sep": "、",
        "semicolon": "；",
        "ellipsis": "…",
        "legend_hidden": (
            "隐藏系列：{metric}（仅影响图表显示，不改变 CSV 数据范围）"
        ),
        "chart_summary": "图表摘要：{text}",
        "range_line": "范围：{start} → {end}（{tz}）",
        "watermark_line": (
            "数据水位：{as_of}（快照 {snapshot}，watermark_seq {seq}）"
        ),
        "quality_line": "数据质量：{coverage}；脱敏版本 {redaction}；导出 schema {schema}",
        "preview_note": "HTML 预览受呈现状态限制；CSV 导出同一快照的全部授权数据族。",
        "unsupported": "不支持",
        "reason_wrapper": "（{reason}）",
        "status_wrapper": "（{status}）",
    },
    "en": {
        "lang": "en",
        "title": "SBTD report",
        "family": {
            "task": "Task",
            "run": "Run",
            "step": "Step",
            "gate": "Gate",
            "component": "Component",
            "invocation": "Invocation",
            "validation_run": "Validation run",
            "validation_case": "Validation case",
            "usage": "Usage",
            "artifact": "Artifact",
            "event": "Event",
            "data_quality": "Data quality",
        },
        "headers": {
            "record": "Record",
            "status": "Status",
            "time": "Time",
            "role": "Role",
            "task": "Task",
            "step": "Step",
            "attempt": "Attempt",
            "start": "Start",
            "duration_ms": "Duration ms",
            "data_family": "Data family",
            "rows": "Rows",
        },
        "count_label": "{title}: showing {shown} of {total} in range",
        "no_range_records": "No records in range.",
        "no_rows": "No rows to show.",
        "no_task_records": "No task records in range.",
        "no_task_steps": "No step records for this task in range.",
        "no_task_events": "No events for this task in range.",
        "task_summary": "Task summary",
        "step_timeline": (
            "Step timeline (showing {shown} of {total} in this task's range)"
        ),
        "event_preview": (
            "Event preview (newest first; showing {shown} of {total} in this "
            "task's range)"
        ),
        "coverage_heading": "Coverage (dataset manifest, observed rows)",
        "gaps_heading": "Gaps and unlinked",
        "unknown_events": "Unknown-time events: {count}{ids}",
        "summary_item": "quality_summary: {text}",
        "warnings_item": "Snapshot warnings: {text}",
        "watermarks_item": "Source watermarks: {text}",
        "watermark_seq_item": "Watermark sequence watermark_seq: {seq}",
        "unknown_not_carried": "unknown (not carried by the snapshot)",
        "none": "none",
        "no_watermark": "No declarations (single local source)",
        "ids_wrapper": " ({text})",
        "list_sep": ", ",
        "summary_sep": ", ",
        "semicolon": "; ",
        "ellipsis": "...",
        "legend_hidden": (
            "Hidden series: {metric} (affects chart display only; does not "
            "change the CSV data range)"
        ),
        "chart_summary": "Chart summary: {text}",
        "range_line": "Range: {start} → {end} ({tz})",
        "watermark_line": (
            "Data watermark: {as_of} (snapshot {snapshot}, watermark_seq {seq})"
        ),
        "quality_line": (
            "Data quality: {coverage}; redaction version {redaction}; "
            "export schema {schema}"
        ),
        "preview_note": (
            "HTML preview is limited by presentation state; CSV exports every "
            "authorized data family of the same snapshot."
        ),
        "unsupported": "unsupported",
        "reason_wrapper": " ({reason})",
        "status_wrapper": " ({status})",
    },
}
# Per-panel insufficient-data copy lives in the manifest (`insufficient_data_zh`
# and `insufficient_data_en`); the renderer only selects the field, so no
# second English copy can drift.


def _l10n(locale: str) -> dict:
    return _L10N.get(locale, _L10N["zh"])


def _family_label(locale: str, family: str) -> str:
    return _l10n(locale)["family"].get(family, family)


def _panel_title(panel: dict, locale: str) -> str:
    title = panel.get("title_en") if locale == "en" else None
    return str(title or panel.get("title_zh") or panel["panel_id"])


def _insufficient(panel: dict, locale: str) -> str:
    if locale == "en":
        return str(
            panel.get("insufficient_data_en")
            or panel.get("insufficient_data_zh")
            or ""
        )
    return str(panel.get("insufficient_data_zh") or "")


# View metadata only. Panel identity stays in the manifest.
_PANEL_FAMILIES = {
    "task-lifecycle": ("task",),
    "activity-trend": ("event",),
    "mode-decisions": ("event",),
    "step-performance": ("step",),
    "blockers": ("run",),
    "gate-matrix": ("gate",),
    "component-usage": ("component", "invocation"),
    "validation-evidence": ("validation_run", "validation_case"),
    "host-model-usage": ("usage",),
    "project-actor-summary": ("task",),
}
_TASK_LIMIT = 20
_DETAIL_LIMIT = 50
_NUMERIC = re.compile(r"^-?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?$")
_FRACTION = re.compile(r"^-?\d+/-?\d+$")
# Absolute paths only. A slash inside parent/demo or duration.step_p50/p95
# is preceded by a word character and must survive.
_ABS_PATH = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    r"~(?:/[A-Za-z0-9._~\-]+)+"
    r"|/(?![/\s])[A-Za-z0-9._~\-]+(?:/[A-Za-z0-9._~\-]+)*"
    r"|[A-Za-z]:\\[^\s\"'<>]+"
    r"|\\\\[^\s\"'<>]+"
    r"|file://[^\s\"'<>]+"
    r")"
)
_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_URL = re.compile(r"(?i)\b(?:https?|ftp)://[^\s\"'<>]+")
_PROTO_REL = re.compile(r"(?<![:/\w])//[A-Za-z0-9.\-]+")
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-+/=]{6,}")
_ASSIGNED = re.compile(
    r"(?i)\b(?:api[_-]?key|secret|password|passwd|token|authorization|credential)"
    r"\b\s*[:=]\s*\S+"
)
_SK = re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}\b")
_AWS = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_PEM = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")
_CSS = """
:root, [data-theme="dark"] {
  color-scheme: dark;
  --bg: #14171c; --panel: #1b1f26; --text: #e7edf5;
  --muted: #9aa8b8; --line: #2c333d; --unknown: #8eabcb;
}
[data-theme="light"] {
  color-scheme: light;
  --bg: #f4f7fb; --panel: #ffffff; --text: #1c2430;
  --muted: #5c6b7c; --line: #d5dee8; --unknown: #3d5f86;
}
* { box-sizing: border-box; }
html, body { margin: 0; background: var(--bg); color: var(--text); }
body {
  font-family: FONT_FAMILY;
  font-size: 14px;
  line-height: 1.55;
}
.report { margin: 0 auto; padding: 24px; }
.grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 16px;
}
.panel {
  border: 1px solid var(--line);
  background: var(--panel);
  padding: 16px;
  overflow-wrap: anywhere;
}
.panel h2 { margin: 0 0 8px; font-size: 16px; }
.panel-id, .metric dt {
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  color: var(--muted);
  font-size: 12px;
}
.metric { margin: 0 0 10px; }
.metric dd { margin: 0; font-size: 28px; }
.unknown, .marker, .insufficient, .legend-hidden { color: var(--unknown); }
table { border-collapse: collapse; width: 100%; }
th, td {
  border-bottom: 1px solid var(--line);
  text-align: left;
  padding: 4px 8px;
  vertical-align: top;
}
svg { max-width: 100%; height: auto; }
svg text { fill: currentColor; }
""".replace("FONT_FAMILY", _FONT_FAMILY)


class ExportCancelled(Exception):
    """Worker cancellation observed before the artifact is returned."""


def load_panel_manifest() -> dict:
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def _ordered_panels(manifest: dict) -> list[dict]:
    return sorted(manifest["panels"], key=lambda panel: panel["order"])


def default_presentation(manifest: dict | None = None) -> dict:
    manifest = manifest or load_panel_manifest()
    return {
        "theme": "dark",
        "report_width_px": 1440,
        "expanded_detail_ids": [],
        "table_sort": {},
        "preview_row_sets": {},
        "panel_order": [panel["panel_id"] for panel in _ordered_panels(manifest)],
        "legend_state": {},
        "locale": "zh",
    }


def _check(cancelled) -> None:
    if cancelled():
        raise ExportCancelled("export cancelled")


def _controls(text: str) -> str:
    return "".join(ch for ch in text if ch in "\t\n\r" or ord(ch) >= 32)


def _is_literal(text: str) -> bool:
    return bool(_NUMERIC.fullmatch(text) or _FRACTION.fullmatch(text))


def _has_raw_audit(node: Any) -> bool:
    if isinstance(node, dict):
        keys = {str(key).casefold() for key in node}
        if keys & {
            "messages",
            "conversation",
            "privacy",
            "prompt",
            "reasoning",
            "password",
            "passwd",
            "secret",
            "token",
            "api_key",
            "apikey",
            "authorization",
            "cookie",
            "credential",
        }:
            return True
        if "event_type" in keys and keys & {"schema_version", "extensions"}:
            return True
        return any(
            _raw_audit(str(key)) or _has_raw_audit(value) for key, value in node.items()
        )
    if isinstance(node, list):
        return any(_has_raw_audit(item) for item in node)
    return False


def _raw_audit(text: str) -> bool:
    body = text.removeprefix("'").strip()
    decoder = json.JSONDecoder()
    for index, char in enumerate(body):
        if char not in "{[":
            continue
        try:
            parsed, _end = decoder.raw_decode(body[index:])
        except json.JSONDecodeError:
            continue
        if _has_raw_audit(parsed):
            return True
    return False


def redact_text(text: str) -> str:
    """Output-only redaction. Numeric literals and relative ids stay intact."""
    if text in {"", "unknown", "true", "false"} or _is_literal(text):
        return text
    if _raw_audit(text) or _PEM.search(text):
        return "[redacted]"
    text = _URL.sub("[redacted-url]", text)
    text = _PROTO_REL.sub("[redacted-url]", text)
    text = re.sub(r"(?i)@import\b", "[redacted-import]", text)
    text = re.sub(r"(?i)url\s*\(", "[redacted-url](", text)
    text = _BEARER.sub("[redacted]", text)
    text = _ASSIGNED.sub("[redacted]", text)
    text = _SK.sub("[redacted]", text)
    text = _AWS.sub("[redacted]", text)
    text = _EMAIL.sub("[redacted-email]", text)
    text = _ABS_PATH.sub("[redacted-path]", text)
    return text


def redact_cell(column: str, text: str) -> str:
    if column == "metric_id" or _is_literal(text):
        return text
    parsed = None
    if text[:1] in "{[":
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
    if isinstance(parsed, (dict, list)):
        return json.dumps(
            _redact_node(parsed),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    return redact_text(text)


def _redact_node(value: Any) -> Any:
    if isinstance(value, (dict, list)) and _has_raw_audit(value):
        return "[redacted]"
    if isinstance(value, dict):
        return {
            _redact_node(str(key)): _redact_node(item) for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_node(item) for item in value]
    if isinstance(value, str):
        return "[redacted]" if _raw_audit(value) else redact_text(value)
    return value


def _non_exportable_ids(snapshot) -> set[str]:
    blocked: set[str] = set()
    dataset = getattr(snapshot, "dataset", None)
    events = dataset.get("events") if isinstance(dataset, dict) else None
    if not isinstance(events, list):
        return blocked
    for event in events:
        if not isinstance(event, dict):
            continue
        privacy = event.get("privacy")
        if not isinstance(privacy, dict):
            continue
        exportable = privacy.get("exportable", True)
        classification = privacy.get("classification", "local-metadata")
        if exportable is False or classification != "local-metadata":
            event_id = event.get("event_id")
            if isinstance(event_id, str):
                blocked.add(event_id)
    return blocked


def _row_event_id(row: dict) -> str | None:
    if row.get("record_type") == "event":
        record_id = row.get("record_id")
        return record_id if isinstance(record_id, str) else None
    fields = row.get("fields")
    if isinstance(fields, dict) and isinstance(fields.get("event_id"), str):
        return fields["event_id"]
    return None


def _withheld(row: dict, blocked: set[str]) -> bool:
    if row.get("record_type") == "task":
        return False
    event_id = _row_event_id(row)
    return event_id in blocked


def _walk_rows(
    snapshot, snapshots, cancelled, blocked: set[str]
) -> tuple[list[dict], int]:
    if snapshots is None:
        raise ValueError("dataset cursor walk requires a snapshot store")
    kept: list[dict] = []
    withheld = 0
    cursor = None
    while True:
        _check(cancelled)
        page = snapshots.dataset_page(snapshot.snapshot_id, cursor, DEFAULT_PAGE_SIZE)
        for row in page["rows"]:
            _check(cancelled)
            if _withheld(row, blocked):
                withheld += 1
                continue
            kept.append(row)
        cursor = page["next_cursor"]
        if cursor is None:
            break
    _check(cancelled)
    return kept, withheld


def _presentation(state, manifest: dict) -> dict:
    base = default_presentation(manifest)
    if not isinstance(state, dict):
        return base
    merged = dict(base)
    for key in base:
        if key in state:
            merged[key] = state[key]
    ids = base["panel_order"]
    order = merged["panel_order"]
    if not isinstance(order, list) or len(order) != len(ids) or set(order) != set(ids):
        merged["panel_order"] = list(ids)
    else:
        merged["panel_order"] = list(order)
    if not isinstance(merged["locale"], str) or merged["locale"] not in _L10N:
        merged["locale"] = "zh"
    return merged


def _css_px(value: Any) -> str:
    if type(value) is bool or not isinstance(value, (int, float)):
        value = 1440
    if not math.isfinite(value) or value < 0:
        value = 1440
    text = format(value, "f").rstrip("0").rstrip(".")
    if not re.fullmatch(r"\d+(?:\.\d+)?", text):
        return "1440"
    return text


def _mapping(state: dict, name: str) -> dict:
    value = state.get(name)
    return value if isinstance(value, dict) else {}


def _limit(state: dict, keys: tuple[str, ...], default: int) -> int:
    sets = _mapping(state, "preview_row_sets")
    for key in keys:
        if key not in sets:
            continue
        value = sets[key]
        if type(value) is bool or not isinstance(value, (int, float)):
            return default
        if not math.isfinite(value) or value < 0:
            return default
        return math.floor(value)
    return default


def _sort_spec(state: dict, keys: tuple[str, ...]) -> str | None:
    sorts = _mapping(state, "table_sort")
    for key in keys:
        value = sorts.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _field(row: dict, name: str) -> Any:
    if name in {"record_id", "record_type", "relation_role"}:
        return row.get(name)
    fields = row.get("fields")
    if isinstance(fields, dict) and name in fields:
        return fields[name]
    return None


def _apply_sort(rows: list[dict], spec: str | None) -> list[dict]:
    if not spec:
        return list(rows)
    descending = spec.startswith("-")
    body = spec[1:] if descending else spec
    field, sep, direction = body.partition(":")
    if sep and direction == "desc":
        descending = True
    elif sep and direction == "asc":
        descending = False

    def key(row: dict) -> tuple:
        value = _field(row, field)
        missing = value is None or value == ""
        return (missing, "" if missing else str(value))

    return sorted(rows, key=key, reverse=descending)


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _show(value: Any) -> str:
    if value is None or value == "":
        return "unknown"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and math.isfinite(value):
        return str(value)
    return _esc(redact_text(_controls(str(value))))


def _render_value(value: Any, sep: str = "、") -> str:
    if value is None:
        return "unknown"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value) if math.isfinite(value) else "unknown"
    if isinstance(value, list):
        return sep.join(_render_value(item, sep) for item in value)
    if isinstance(value, dict):
        if not value:
            return "unknown"
        return sep.join(
            f"{_render_value(str(key), sep)} {_render_value(item, sep)}"
            for key, item in value.items()
        )
    if isinstance(value, str):
        return "[redacted]" if _raw_audit(value) else redact_text(value)
    return _render_value(str(value), sep)


def _metric_body(entry: Any, insufficient: str, locale: str) -> str:
    copy = _l10n(locale)
    if not isinstance(entry, dict):
        return f"unknown — {insufficient}"
    if entry.get("support") == "unsupported":
        reason = entry.get("reason")
        return copy["unsupported"] + (f" — {reason}" if reason else "")
    reason = entry.get("reason") or entry.get("missing_reason")
    strata = entry.get("strata") if isinstance(entry.get("strata"), dict) else None
    chunks: list[str] = []
    if entry.get("value") is None:
        text = "unknown" + (
            copy["reason_wrapper"].format(reason=reason) if reason else ""
        )
        if not strata:
            text += f" — {insufficient}"
        chunks.append(text)
    else:
        chunks.append(_render_value(entry.get("value"), copy["list_sep"]))
    if strata:
        for name, item in strata.items():
            item_value = item.get("value") if isinstance(item, dict) else None
            status = item.get("sample_status") if isinstance(item, dict) else None
            extra = (
                copy["status_wrapper"].format(status=status)
                if isinstance(status, str) and status != "decidable"
                else ""
            )
            chunks.append(
                f"{_render_value(str(name), copy['list_sep'])} "
                f"{_render_value(item_value, copy['list_sep'])}{extra}"
            )
    marks = []
    if entry.get("support") == "conditional":
        marks.append("conditional")
    if entry.get("missing") is True:
        marks.append("partial")
    status = entry.get("sample_status")
    if isinstance(status, str) and status != "decidable":
        marks.append(status)
    if marks:
        chunks.append(" ".join(marks))
    return " ".join(chunks)


def _metric_html(metric_id: str, entry: Any, insufficient: str, locale: str) -> str:
    body = _esc(redact_text(_metric_body(entry, insufficient, locale)))
    return f'<div class="metric"><dt>{_esc(metric_id)}</dt><dd>{body}</dd></div>'


def _chart(series: list[tuple[str, float]]) -> str:
    if not series:
        return ""
    peak = max(abs(value) for _, value in series) or 1.0
    height = 16 * len(series) + 4
    parts = [f'<svg class="chart" width="460" height="{height}" role="img">']
    for index, (metric_id, value) in enumerate(series):
        width = 1 if value == 0 else max(1, round(abs(value) / peak * 240))
        y = 4 + index * 16
        parts.append(
            f'<rect data-series="{_esc(metric_id)}" x="0" y="{y}" '
            f'width="{width}" height="12" fill="currentColor"></rect>'
        )
        parts.append(
            f'<text x="248" y="{y + 11}" font-size="12">'
            f"{_esc(metric_id)} {_esc(value)}</text>"
        )
    parts.append("</svg>")
    return "".join(parts)


def _count_label(title: str, shown: int, total: int, locale: str) -> str:
    return _l10n(locale)["count_label"].format(
        title=title, shown=shown, total=total
    )


def _rows_of(rows: list[dict], family: str) -> list[dict]:
    return [row for row in rows if row.get("record_type") == family]


def _family_table(
    panel_id: str,
    family: str,
    rows: list[dict],
    state: dict,
    totals: dict[str, int],
    locale: str,
    *,
    detail: bool,
) -> str:
    chosen = _apply_sort(
        _rows_of(rows, family),
        _sort_spec(state, (f"{panel_id}:{family}", panel_id, family)),
    )
    limit = _limit(state, (f"{panel_id}:{family}", panel_id, family), _DETAIL_LIMIT)
    shown = chosen[:limit]
    total = totals.get(family, len(chosen))
    label = _family_label(locale, family)
    headers = _l10n(locale)["headers"]
    css = "panel-detail" if detail else "panel-table"
    body = []
    for row in shown:
        body.append(
            "<tr>"
            f"<td>{_show(row.get('record_id'))}</td>"
            f"<td>{_show(_field(row, 'status'))}</td>"
            f"<td>{_show(_field(row, 'occurred_at'))}</td>"
            f"<td>{_show(row.get('relation_role'))}</td>"
            "</tr>"
        )
    if not body:
        copy = _l10n(locale)
        note = copy["no_range_records"] if total == 0 else copy["no_rows"]
        body.append(f'<tr><td colspan="4">{note}</td></tr>')
    return (
        f'<div class="{css}">'
        f"<p>{_esc(_count_label(label, len(shown), total, locale))}</p>"
        "<table><thead><tr>"
        f"<th>{headers['record']}</th><th>{headers['status']}</th>"
        f"<th>{headers['time']}</th><th>{headers['role']}</th>"
        "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


def _task_detail(
    task_uid: str, rows: list[dict], state: dict, locale: str
) -> str:
    steps = [
        row
        for row in rows
        if row.get("record_type") == "step" and _field(row, "task_uid") == task_uid
    ]
    events = [
        row
        for row in rows
        if row.get("record_type") == "event" and _field(row, "task_uid") == task_uid
    ]
    step_spec = _sort_spec(state, ("task-audit-detail:step", "step"))
    if step_spec:
        steps = _apply_sort(steps, step_spec)
    else:
        steps = sorted(steps, key=lambda row: str(_field(row, "started_at") or ""))
    event_spec = _sort_spec(state, ("task-audit-detail:event", "event"))
    if event_spec:
        events = _apply_sort(events, event_spec)
    else:
        events = sorted(
            events,
            key=lambda row: str(_field(row, "occurred_at") or ""),
            reverse=True,
        )
    step_limit = _limit(state, ("task-audit-detail:step", "step"), _DETAIL_LIMIT)
    event_limit = _limit(state, ("task-audit-detail:event", "event"), _DETAIL_LIMIT)
    shown_steps = steps[:step_limit]
    shown_events = events[:event_limit]
    step_rows = []
    for row in shown_steps:
        step_rows.append(
            "<tr>"
            f"<td>{_show(_field(row, 'step_run_id'))}</td>"
            f"<td>{_show(_field(row, 'attempt_no'))}</td>"
            f"<td>{_show(_field(row, 'started_at'))}</td>"
            f"<td>{_show(_field(row, 'duration_ms'))}</td>"
            f"<td>{_show(_field(row, 'status'))}</td>"
            "</tr>"
        )
    event_items = []
    for row in shown_events:
        status = _field(row, "status")
        suffix = "" if status is None else f" — {_show(status)}"
        event_items.append(
            "<li>"
            f"{_show(_field(row, 'occurred_at'))} {_show(_field(row, 'event_type'))}"
            f"{suffix}</li>"
        )
    copy = _l10n(locale)
    headers = copy["headers"]
    step_body = (
        "".join(step_rows)
        if step_rows
        else f'<tr><td colspan="5">{copy["no_task_steps"]}</td></tr>'
    )
    event_body = (
        "".join(event_items)
        if event_items
        else f'<li>{copy["no_task_events"]}</li>'
    )
    step_heading = copy["step_timeline"].format(
        shown=len(shown_steps), total=len(steps)
    )
    event_heading = copy["event_preview"].format(
        shown=len(shown_events), total=len(events)
    )
    return (
        '<div class="panel-detail">'
        f"<h3>{step_heading}</h3>"
        "<table><thead><tr>"
        f"<th>{headers['step']}</th><th>{headers['attempt']}</th>"
        f"<th>{headers['start']}</th>"
        f"<th>{headers['duration_ms']}</th><th>{headers['status']}</th>"
        f"</tr></thead><tbody>{step_body}</tbody></table>"
        f"<h3>{event_heading}</h3>"
        f"<ul>{event_body}</ul></div>"
    )


def _task_audit(
    rows: list[dict],
    state: dict,
    totals: dict[str, int],
    expanded: set[str],
    locale: str,
) -> str:
    tasks = _apply_sort(
        _rows_of(rows, "task"),
        _sort_spec(state, ("task-audit-detail", "task")),
    )
    limit = _limit(state, ("task-audit-detail", "task"), _TASK_LIMIT)
    shown = tasks[:limit]
    total = totals.get("task", len(tasks))
    body = []
    for row in shown:
        task_uid = str(row.get("record_id"))
        body.append(
            "<tr>"
            f"<td>{_show(row.get('record_id'))}</td>"
            f"<td>{_show(_field(row, 'status'))}</td>"
            f"<td>{_show(_field(row, 'worktree_id'))}</td>"
            f"<td>{_show(row.get('relation_role'))}</td>"
            "</tr>"
        )
        if task_uid in expanded:
            body.append(
                f'<tr><td colspan="4">'
                f"{_task_detail(task_uid, rows, state, locale)}</td></tr>"
            )
    copy = _l10n(locale)
    headers = copy["headers"]
    if not body:
        note = copy["no_task_records"] if total == 0 else copy["no_rows"]
        body.append(f'<tr><td colspan="4">{note}</td></tr>')
    return (
        f"<p>{_esc(_count_label(copy['task_summary'], len(shown), total, locale))}</p>"
        "<table><thead><tr>"
        f"<th>{headers['task']}</th><th>{headers['status']}</th><th>worktree</th>"
        f"<th>{headers['role']}</th>"
        f"</tr></thead><tbody>{''.join(body)}</tbody></table>"
    )


def _quality_html(
    snapshot, blocked: set[str], warnings: list[str], locale: str
) -> str:
    copy = _l10n(locale)
    headers = copy["headers"]
    totals = []
    for item in snapshot.dataset_manifest:
        family = item.get("record_type")
        count = item.get("rows")
        label = _family_label(locale, family) if isinstance(family, str) else "unknown"
        shown = (
            count
            if isinstance(count, int) and not isinstance(count, bool)
            else "unknown"
        )
        totals.append(f"<tr><td>{_esc(label)}</td><td>{_esc(shown)}</td></tr>")
    unknown_ids = [
        item for item in snapshot.unknown_time_event_ids if item not in blocked
    ]
    unknown_count = len(snapshot.unknown_time_event_ids)
    id_text = ""
    if unknown_ids:
        preview = copy["list_sep"].join(
            _redact_node(item) for item in unknown_ids[:5]
        )
        if len(unknown_ids) > 5:
            preview += copy["ellipsis"]
        id_text = copy["ids_wrapper"].format(text=_esc(preview))
    summary = snapshot.quality_summary
    if isinstance(summary, dict) and summary:
        summary_text = _esc(
            redact_text(
                copy["semicolon"].join(
                    f"{key}={value}" for key, value in summary.items()
                )
            )
        )
    else:
        summary_text = copy["unknown_not_carried"]
    warning_text = (
        copy["none"] if not warnings else _esc(copy["list_sep"].join(warnings))
    )
    watermarks = snapshot.source_watermarks
    if watermarks:
        watermark_text = _esc(
            redact_text(
                copy["semicolon"].join(
                    json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
                    for item in watermarks
                )
            )
        )
    else:
        watermark_text = copy["no_watermark"]
    seq_item = copy["watermark_seq_item"].format(
        seq=_esc(snapshot.watermark_seq)
    )
    return (
        f"<h3>{copy['coverage_heading']}</h3>"
        "<table><thead><tr>"
        f"<th>{headers['data_family']}</th><th>{headers['rows']}</th>"
        "</tr></thead>"
        f"<tbody>{''.join(totals)}</tbody></table>"
        f"<h3>{copy['gaps_heading']}</h3><ul>"
        f"<li>{copy['unknown_events'].format(count=unknown_count, ids=id_text)}</li>"
        f"<li>{copy['summary_item'].format(text=summary_text)}</li>"
        f"<li>{copy['warnings_item'].format(text=warning_text)}</li>"
        f"<li>{copy['watermarks_item'].format(text=watermark_text)}</li>"
        f"<li>{seq_item}</li>"
        "</ul>"
    )


def _panel_html(
    panel: dict,
    metrics: dict,
    rows: list[dict],
    state: dict,
    snapshot,
    totals: dict[str, int],
    expanded: set[str],
    blocked: set[str],
    warnings: list[str],
    locale: str,
) -> str:
    panel_id = panel["panel_id"]
    copy = _l10n(locale)
    legend = _mapping(state, "legend_state")
    insufficient = _insufficient(panel, locale)
    parts = [
        (
            f'<section id="{_esc(panel_id)}" class="panel" '
            f'style="grid-column: span {int(panel["desktop_span"])}">'
        ),
        (
            f"<h2>{_esc(_panel_title(panel, locale))} "
            f'<span class="panel-id">{_esc(panel_id)}</span></h2>'
        ),
        f'<p class="insufficient">{_esc(insufficient)}</p>',
    ]
    visible: list[tuple[str, float]] = []
    hidden: list[str] = []
    for metric_id in panel.get("metric_ids") or []:
        entry = metrics.get(metric_id)
        parts.append(_metric_html(metric_id, entry, insufficient, locale))
        if legend.get(metric_id) is False:
            hidden.append(metric_id)
            continue
        value = entry.get("value") if isinstance(entry, dict) else None
        if (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        ):
            visible.append((metric_id, float(value)))
    for metric_id in hidden:
        parts.append(
            f'<p class="legend-hidden">'
            f"{copy['legend_hidden'].format(metric=_esc(metric_id))}</p>"
        )
    if panel.get("kind") == "chart":
        parts.append(_chart(visible))
        rendered = []
        for metric_id, _value in visible:
            value = metrics.get(metric_id, {}).get("value")
            rendered.append(
                f"{metric_id} {_render_value(value, copy['list_sep'])}"
            )
        summary = copy["summary_sep"].join(rendered)
        if summary:
            parts.append(
                "<p>"
                f"{copy['chart_summary'].format(text=_esc(redact_text(summary)))}"
                "</p>"
            )
    if panel_id == "data-quality":
        parts.append(_quality_html(snapshot, blocked, warnings, locale))
    elif panel_id == "task-audit-detail":
        parts.append(_task_audit(rows, state, totals, expanded, locale))
    else:
        families = _PANEL_FAMILIES.get(panel_id, ())
        show_table = panel.get("kind") == "table" or panel_id in expanded
        for family in families if show_table else ():
            parts.append(
                _family_table(
                    panel_id,
                    family,
                    rows,
                    state,
                    totals,
                    locale,
                    detail=panel_id in expanded and panel.get("kind") != "table",
                )
            )
    parts.append("</section>")
    return "".join(parts)


def _html(
    snapshot,
    presentation: dict,
    manifest: dict,
    rows: list[dict],
    metrics: dict,
    warnings: list[str],
    blocked: set[str],
) -> bytes:
    theme = presentation.get("theme")
    if theme not in ("dark", "light"):
        theme = "dark"
    locale = presentation.get("locale")
    copy = _l10n(locale)
    width = _css_px(presentation.get("report_width_px"))
    panels = {panel["panel_id"]: panel for panel in manifest["panels"]}
    totals = {}
    for item in snapshot.dataset_manifest:
        family = item.get("record_type")
        count = item.get("rows")
        if (
            isinstance(family, str)
            and isinstance(count, int)
            and not isinstance(count, bool)
        ):
            totals[family] = count
    expanded_raw = presentation.get("expanded_detail_ids")
    expanded = set(expanded_raw) if isinstance(expanded_raw, list) else set()
    coverage = "partial" if snapshot.unknown_time_event_ids else "complete"
    parts = [
        "<!DOCTYPE html>",
        f'<html lang="{copy["lang"]}" data-theme="{theme}">',
        f'<head><meta charset="utf-8"><title>{copy["title"]}</title>',
        '<link rel="icon" href="data:,">',
        f"<style>{_CSS}</style></head><body>",
        f'<article class="report" style="width: {width}px">',
        f'<header><h1>{copy["title"]}</h1>',
        (
            "<p>"
            + copy["range_line"].format(
                start=_show(snapshot.effective_from),
                end=_show(snapshot.effective_to),
                tz=_show(snapshot.timezone),
            )
            + "</p>"
        ),
        (
            "<p>"
            + copy["watermark_line"].format(
                as_of=_show(snapshot.as_of),
                snapshot=_show(snapshot.snapshot_id),
                seq=_esc(snapshot.watermark_seq),
            )
            + "</p>"
        ),
        (
            "<p>"
            + copy["quality_line"].format(
                coverage=coverage,
                redaction=_esc(REDACTION_POLICY_VERSION),
                schema=_esc(CSV_SCHEMA_VERSION),
            )
            + "</p>"
        ),
        f"<p>{copy['preview_note']}</p>",
        '</header><main class="grid">',
    ]
    for panel_id in presentation["panel_order"]:
        panel = panels.get(panel_id)
        if panel is None:
            continue
        parts.append(
            _panel_html(
                panel,
                metrics,
                rows,
                presentation,
                snapshot,
                totals,
                expanded,
                blocked,
                warnings,
                locale,
            )
        )
    parts.append("</main></article></body></html>")
    return "".join(parts).encode("utf-8")


def _metadata(
    snapshot,
    presentation: dict,
    manifest: dict,
    payload: bytes,
    mime: str,
    warnings: list[str],
    export_format: str,
) -> dict:
    return {
        "mime_type": mime,
        "format": export_format,
        "byte_size": len(payload),
        "redaction_policy_version": REDACTION_POLICY_VERSION,
        "export_schema_version": CSV_SCHEMA_VERSION,
        "panel_manifest_version": manifest.get("manifest_version"),
        "panel_ids": list(presentation["panel_order"]),
        "dataset_manifest": [dict(item) for item in snapshot.dataset_manifest],
        "snapshot_id": snapshot.snapshot_id,
        "range_from": snapshot.effective_from,
        "range_to": snapshot.effective_to,
        "timezone": snapshot.timezone,
        "warnings": list(warnings),
        "renderer_version": RENDERER_VERSION,
    }


def render_export(snapshot, format, presentation_state, cancelled, *, snapshots=None):
    if format not in ("html", "csv"):
        raise ValueError("format must be html or csv")
    _check(cancelled)
    manifest = load_panel_manifest()
    presentation = _presentation(presentation_state, manifest)
    blocked = _non_exportable_ids(snapshot)
    rows, withheld = _walk_rows(snapshot, snapshots, cancelled, blocked)
    _check(cancelled)
    warnings = list(snapshot.warnings)
    if withheld:
        warnings.append(f"WITHHELD_NON_EXPORTABLE:{withheld}")
        counts = Counter(row["record_type"] for row in rows)
        snapshot = replace(
            snapshot,
            dataset_manifest=[
                {**item, "rows": counts[item["record_type"]]}
                for item in snapshot.dataset_manifest
            ],
        )
    if format == "csv":
        payload = serialize_csv(snapshot, rows=rows, value_transform=redact_cell)
        mime = "text/csv; charset=utf-8"
    else:
        answer = query(snapshot.dataset, snapshot.raw_scope)
        _check(cancelled)
        payload = _html(
            snapshot,
            presentation,
            manifest,
            rows,
            answer["metrics"],
            warnings,
            blocked,
        )
        mime = "text/html; charset=utf-8"
    _check(cancelled)
    metadata = _metadata(
        snapshot, presentation, manifest, payload, mime, warnings, format
    )
    _check(cancelled)
    return payload, metadata


class ExportRenderer:
    def __init__(self, snapshots, *, home: Path | None = None) -> None:
        self.snapshots = snapshots
        self.home = home

    def __call__(self, snapshot, format, presentation_state, cancelled):
        if format in ("jpeg", "pdf"):
            from browser_renderer import BrowserRenderer, RendererError

            if self.home is None:
                raise RendererError("RENDERER_UNAVAILABLE")
            return BrowserRenderer(self.home, self.snapshots)(
                snapshot, format, presentation_state, cancelled
            )
        return render_export(
            snapshot,
            format,
            presentation_state,
            cancelled,
            snapshots=self.snapshots,
        )

    def prepare(self, snapshot, format, presentation, cancelled=None):
        """Freeze one JPEG report and return ``(renderer, warnings)``.

        HTML generation and preflight share one renderer budget. The returned
        callable renders that same HTML at the chosen scale and caps; it does
        not rebuild the report or select another scale.
        """
        if format != "jpeg":
            raise ValueError("format must be jpeg")
        import time

        from browser_renderer import (
            MAX_PIXELS,
            MAX_SIDE_PX,
            BrowserRenderer,
            RendererError,
            _require_timeout,
            _static_html,
        )

        if self.home is None:
            raise RendererError("RENDERER_UNAVAILABLE")
        max_side_px = MAX_SIDE_PX
        max_pixels = MAX_PIXELS
        if (
            type(max_side_px) is not int
            or max_side_px <= 0
            or type(max_pixels) is not int
            or max_pixels <= 0
        ):
            raise RendererError("RENDERER_FAILED")
        browser = BrowserRenderer(self.home, self.snapshots)
        deadline = time.monotonic() + _require_timeout(browser.timeout_seconds)
        try:
            html_bytes, meta = _static_html(
                self.home,
                self.snapshots,
                snapshot,
                presentation,
                cancelled,
                deadline,
            )
            html_text = html_bytes.decode("utf-8")
            measured = browser.preflight(
                snapshot,
                "jpeg",
                presentation,
                cancelled=cancelled,
                timeout_seconds=deadline - time.monotonic(),
                prepared_html=html_text,
                meta=meta,
                max_side_px=max_side_px,
                max_pixels=max_pixels,
            )
        except RendererError:
            raise
        except Exception:  # noqa: BLE001 — library boundary strips local paths.
            raise RendererError("RENDERER_FAILED") from None
        scale = measured.get("scale") if isinstance(measured, dict) else None
        raw_warnings = measured.get("warnings") if isinstance(measured, dict) else None
        if type(scale) is not int or scale not in (1, 2):
            raise RendererError("RENDERER_FAILED")
        if not isinstance(raw_warnings, list) or any(
            type(item) is not str for item in raw_warnings
        ):
            raise RendererError("RENDERER_FAILED")
        warnings = list(raw_warnings)
        frozen_meta = dict(meta)
        frozen_meta["warnings"] = list(warnings)

        def render_job(job_snapshot, job_format, _presentation, cancelled):
            if job_format != "jpeg":
                raise ValueError("format must be jpeg")
            return browser(
                job_snapshot,
                "jpeg",
                presentation,
                cancelled,
                prepared_html=html_text,
                meta=frozen_meta,
                locked_scale=scale,
                max_side_px=max_side_px,
                max_pixels=max_pixels,
            )

        return render_job, warnings
