"""R1.3 CSV export: serialize a full snapshot dataset to one CSV file.

Fixed column set per PRD §13.8 with record_type families. UTF-8 BOM, standard
CSV quoting, ISO 8601 times, numbers without thousand separators, null stays
empty and is never replaced with 0. User-controlled text that could trigger
spreadsheet formulas (leading = + - @ or control characters) is prefixed
with a single quote under escape policy csv-text-escape-v1; legitimate
negative numeric columns are numbers, not text, and are not escaped.
reasoning_tokens is appended last in the fixed columns; it is a subset of
output_tokens and is never added to output, and a missing value stays an
empty cell. CSV_SCHEMA_VERSION 1.1 is the schema that includes the trailing
reasoning_tokens column (1.0 predates it). The serializer walks the
snapshot's full dataset rows — page limits and Top-N never truncate the
file.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from contract_eval import metric_catalog
from report_snapshot import DATASET_FAMILIES, Snapshot
from stats_query import query

CSV_SCHEMA_VERSION = "1.1"
CSV_ESCAPE_VERSION = "csv-text-escape-v1"
RECORD_TYPES = ("metadata", "metric") + DATASET_FAMILIES
COLUMNS = [
    "export_schema_version",
    "snapshot_id",
    "record_type",
    "record_id",
    "row_grain",
    "range_from",
    "range_to",
    "timezone",
    "as_of",
    "metrics_version",
    "project_id",
    "repository_id",
    "worktree_id",
    "actor_id",
    "actor_alias",
    "host_kind",
    "host_version",
    "branch_alias",
    "task_uid",
    "logical_task_id",
    "task_run_id",
    "session_id",
    "step_run_id",
    "parent_step_run_id",
    "component_id",
    "component_kind",
    "component_version",
    "invocation_id",
    "attempt_id",
    "attempt_no",
    "gate_id",
    "gate_eval_id",
    "gate_scope_revision",
    "validation_run_id",
    "case_id",
    "artifact_id",
    "event_id",
    "event_type",
    "source_id",
    "source_event_id",
    "occurred_at",
    "recorded_at",
    "started_at",
    "ended_at",
    "duration_ms",
    "duration_basis",
    "workflow_mode",
    "mode_source",
    "previous_status",
    "status",
    "raw_result",
    "normalized_result",
    "reason_code",
    "operation_status",
    "state_persisted",
    "audit_status",
    "applicability",
    "evidence_status",
    "observation_level",
    "source_kind",
    "validation_scope",
    "tests_total",
    "tests_passed",
    "tests_failed",
    "tests_skipped",
    "tests_unknown",
    "provider",
    "model",
    "billing_basis",
    "currency",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "cost_reported",
    "cost_estimated",
    "metric_id",
    "metric_value",
    "unit",
    "numerator",
    "denominator",
    "bucket_start",
    "bucket_end",
    "group_dimensions",
    "workflow_source_revision",
    "source_commit_sha",
    "worktree_revision",
    "task_document_revision",
    "scope_revision",
    "revision_state",
    "relation_role",
    "coverage_state",
    "warning_code",
    "metadata_key",
    "metadata_value",
    "reasoning_tokens",
]
BOM = b"\xef\xbb\xbf"
_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (dict, list)):
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    text = str(value)
    if text and (text[0] in _FORMULA_PREFIXES or ord(text[0]) < 0x20):
        return "'" + text
    return text


def _metadata_rows(snapshot: Snapshot) -> list[dict[str, Any]]:
    coverage = "partial" if snapshot.unknown_time_event_ids else "complete"
    head = {
        "export_schema_version": CSV_SCHEMA_VERSION,
        "snapshot_id": snapshot.snapshot_id,
        "record_type": "metadata",
        "record_id": "snapshot",
        "row_grain": "snapshot",
        "range_from": snapshot.effective_from,
        "range_to": snapshot.effective_to,
        "timezone": snapshot.timezone,
        "as_of": snapshot.as_of,
        "metrics_version": snapshot.metrics_version,
        "coverage_state": coverage,
    }
    rows = [head]
    pairs = [
        ("query_hash", snapshot.query_hash),
        ("watermark_seq", snapshot.watermark_seq),
        ("escape_version", CSV_ESCAPE_VERSION),
        ("snapshot_digest", snapshot.snapshot_digest),
    ]
    pairs += [
        (f"rows:{item['record_type']}", item["rows"])
        for item in snapshot.dataset_manifest
    ]
    for key, value in pairs:
        rows.append(
            {
                "record_type": "metadata",
                "record_id": f"metadata:{key}",
                "row_grain": "metadata",
                "snapshot_id": snapshot.snapshot_id,
                "metadata_key": key,
                "metadata_value": value,
            }
        )
    return rows


def _metric_rows(snapshot: Snapshot, catalog: dict | None) -> list[dict[str, Any]]:
    catalog = catalog or metric_catalog()
    units = {item["metric_id"]: item.get("unit") for item in catalog["metrics"]}
    grains = {item["metric_id"]: item.get("grain") for item in catalog["metrics"]}
    answer = query(snapshot.dataset, snapshot.raw_scope, catalog=catalog)
    rows = []
    for metric_id in snapshot.query_scope["metrics"]:
        metric = answer["metrics"][metric_id]
        value = metric.get("value")
        rows.append(
            {
                "record_type": "metric",
                "record_id": metric_id,
                "row_grain": grains.get(metric_id),
                "snapshot_id": snapshot.snapshot_id,
                "metric_id": metric_id,
                "metric_value": value,
                "unit": units.get(metric_id),
                "numerator": metric.get("numerator"),
                "denominator": metric.get("denominator"),
                "range_from": snapshot.effective_from,
                "range_to": snapshot.effective_to,
                "timezone": snapshot.timezone,
            }
        )
    return rows


def serialize_csv(snapshot: Snapshot, catalog: dict | None = None) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(COLUMNS)
    rows = _metadata_rows(snapshot)
    rows += _metric_rows(snapshot, catalog)
    for row in snapshot.rows:
        rows.append(
            {
                "record_type": row["record_type"],
                "record_id": row["record_id"],
                "relation_role": row["relation_role"],
                "snapshot_id": snapshot.snapshot_id,
                "range_from": snapshot.effective_from,
                "range_to": snapshot.effective_to,
                "timezone": snapshot.timezone,
                **row["fields"],
            }
        )
    for row in rows:
        writer.writerow([_cell(row.get(column)) for column in COLUMNS])
    return BOM + buffer.getvalue().encode("utf-8")
