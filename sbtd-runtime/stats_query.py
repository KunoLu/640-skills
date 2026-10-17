"""R1.3 statistics query: QueryScope normalize, catalog, query, timeseries.

Metric values always come from contract_eval.evaluate; this module only
validates the QueryScope, narrows the event population with the declared
filters, and slices time into half-open buckets. It never recomputes a
denominator and never invents a number: a rate with zero decidable samples
stays null with sample_status no-decidable-sample, and missing token or cost
fields stay null.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from contract_eval import evaluate, metric_catalog, parse_instant

SCHEMA_VERSION = "1.0"
FILTER_KEYS = frozenset(
    {
        "project_ids",
        "actor_ids",
        "host_kinds",
        "workflow_modes",
        "component_ids",
        "evidence_levels",
    }
)
TASK_GRANULARITIES = frozenset({"executable-leaf", "all"})


class QueryScopeError(ValueError):
    """Invalid time, dimension, or metric. Never silently defaulted."""


def _fail(field: str, reason: str) -> None:
    raise QueryScopeError(f"{field}: {reason}")


def serve_catalog() -> dict[str, Any]:
    catalog = metric_catalog()
    return {
        "schema_version": catalog["schema_version"],
        "metrics_version": catalog["metrics_version"],
        "release": catalog["release"],
        "metrics": catalog["metrics"],
    }


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        _fail(field, "must be a list of strings")
    return value


def normalize_scope(raw: dict[str, Any], catalog: dict | None = None) -> dict[str, Any]:
    catalog = catalog or metric_catalog()
    if not isinstance(raw, dict):
        _fail("scope", "must be an object")
    if raw.get("schema_version") != SCHEMA_VERSION:
        _fail("schema_version", f"must be {SCHEMA_VERSION!r}")
    window = raw.get("range")
    if not isinstance(window, dict):
        _fail("range", "is required")
    try:
        start = parse_instant(window["from"])
        end = parse_instant(window["to"])
    except (KeyError, TypeError, ValueError) as exc:
        _fail("range", f"from/to must be ISO 8601 with a timezone ({exc})")
    if not start < end:
        _fail("range", "from must be before to; no default window is substituted")
    timezone = window.get("timezone")
    if not isinstance(timezone, str) or not timezone:
        _fail("range.timezone", "must be an IANA timezone name")
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        _fail("range.timezone", f"unknown timezone {timezone!r}")

    filters = raw.get("filters") or {}
    if not isinstance(filters, dict):
        _fail("filters", "must be an object")
    unknown_filters = set(filters) - FILTER_KEYS
    if unknown_filters:
        _fail("filters", f"unsupported dimensions: {sorted(unknown_filters)}")
    clean_filters = {
        key: _string_list(filters[key], f"filters.{key}") for key in filters
    }

    known_ids = {item["metric_id"] for item in catalog["metrics"]}
    metrics = raw.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        _fail("metrics", "must be a non-empty list")
    for metric_id in metrics:
        if not isinstance(metric_id, str) or metric_id not in known_ids:
            _fail("metrics", f"unknown metric id {metric_id!r}")

    granularity = raw.get("task_granularity", "executable-leaf")
    if granularity not in TASK_GRANULARITIES:
        _fail("task_granularity", f"must be one of {sorted(TASK_GRANULARITIES)}")
    group_by = raw.get("group_by") or []
    _string_list(group_by, "group_by")
    if group_by:
        # Grouped aggregation is outside R1.3; an ungrouped answer under a
        # grouped scope would silently mislead (PRD §9.1, §9.6).
        _fail("group_by", "grouped aggregation is not implemented in v2.1.0-rc.1")
    for flag in ("include_unlinked", "include_unknown_time"):
        if flag in raw and not isinstance(raw[flag], bool):
            _fail(flag, "must be a boolean")

    return {
        "schema_version": SCHEMA_VERSION,
        "from": window["from"],
        "to": window["to"],
        "timezone": timezone,
        "filters": clean_filters,
        "task_granularity": granularity,
        "include_unlinked": bool(raw.get("include_unlinked", False)),
        "include_unknown_time": bool(raw.get("include_unknown_time", False)),
        "metrics": list(metrics),
    }


def _matches_filters(event: dict[str, Any], filters: dict[str, list[str]]) -> bool:
    scope = event.get("scope") or {}
    checks = (
        ("project_ids", scope.get("project_id")),
        ("actor_ids", (event.get("actor") or {}).get("actor_id")),
        ("host_kinds", (event.get("host") or {}).get("host_kind")),
        ("workflow_modes", (event.get("workflow") or {}).get("mode_at_event")),
        ("component_ids", (event.get("component") or {}).get("component_id")),
        ("evidence_levels", (event.get("provenance") or {}).get("evidence_status")),
    )
    for key, value in checks:
        wanted = filters.get(key)
        if wanted and value not in wanted:
            return False
    return True


def filter_events(events: list[dict], scope: dict[str, Any]) -> list[dict]:
    filters = scope.get("filters") or {}
    if not filters:
        return list(events)
    return [event for event in events if _matches_filters(event, filters)]


def _eval_scope(scope: dict[str, Any]) -> dict[str, Any]:
    return {
        "from": scope["from"],
        "to": scope["to"],
        "task_granularity": scope["task_granularity"],
        "task_uids": scope.get("task_uids") or [],
    }


def _evaluate(
    dataset: dict, scope: dict[str, Any], catalog: dict | None
) -> dict[str, Any]:
    narrowed = {
        "tasks": dataset["tasks"],
        "events": filter_events(dataset["events"], scope),
    }
    return evaluate(narrowed, _eval_scope(scope), catalog=catalog)


def _meta(scope: dict[str, Any], evaluation: dict[str, Any]) -> dict[str, Any]:
    unknown = evaluation.get("unknown_time_event_ids") or []
    return {
        "as_of": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "effective_from": scope["from"],
        "effective_to": scope["to"],
        "timezone": scope["timezone"],
        "metrics_version": evaluation["metrics_version"],
        "complete": not unknown,
        "coverage_state": "complete" if not unknown else "partial",
        "warnings": ["UNKNOWN_OCCURRED_AT"] if unknown else [],
        "next_cursor": None,
    }


def _attach_snapshot(
    result: dict[str, Any], dataset: dict, raw_scope: dict, store: Any
) -> dict[str, Any]:
    if store is None:
        return result
    snapshot = store.create_or_reuse(dataset, raw_scope)
    result["snapshot_id"] = snapshot.snapshot_id
    result["meta"]["watermark_seq"] = snapshot.watermark_seq
    result["meta"]["query_hash"] = snapshot.query_hash
    return result


def query(
    dataset: dict,
    raw_scope: dict,
    *,
    catalog: dict | None = None,
    store: Any = None,
) -> dict[str, Any]:
    scope = normalize_scope(raw_scope, catalog=catalog)
    evaluation = _evaluate(dataset, scope, catalog)
    metrics = {
        metric_id: evaluation["metrics"][metric_id] for metric_id in scope["metrics"]
    }
    result = {
        "scope": scope,
        "metrics": metrics,
        "dedup": evaluation["dedup"],
        "unknown_time_event_ids": evaluation["unknown_time_event_ids"],
        "meta": _meta(scope, evaluation),
    }
    return _attach_snapshot(result, dataset, raw_scope, store)


def _default_bucket_seconds(span_seconds: float) -> int:
    hour = 3600
    if span_seconds <= hour:
        return 300
    if span_seconds <= 24 * hour:
        return hour
    if span_seconds <= 7 * 24 * hour:
        return 6 * hour
    if span_seconds <= 90 * 24 * hour:
        return 24 * hour
    return int(span_seconds // 300) + 1


def _iso(instant: datetime) -> str:
    return instant.astimezone(UTC).isoformat().replace("+00:00", "Z")


def timeseries(
    dataset: dict,
    raw_scope: dict,
    *,
    bucket_seconds: int | None = None,
    catalog: dict | None = None,
    store: Any = None,
) -> dict[str, Any]:
    scope = normalize_scope(raw_scope, catalog=catalog)
    start = parse_instant(scope["from"])
    end = parse_instant(scope["to"])
    span = (end - start).total_seconds()
    step = (
        bucket_seconds if bucket_seconds is not None else _default_bucket_seconds(span)
    )
    if not isinstance(step, int) or step <= 0:
        _fail("bucket_seconds", "must be a positive number of seconds")
    buckets = []
    cursor = start
    while cursor < end:
        bucket_end = min(cursor + timedelta(seconds=step), end)
        evaluation = _evaluate(
            dataset,
            {**scope, "from": _iso(cursor), "to": _iso(bucket_end)},
            catalog,
        )
        buckets.append(
            {
                "bucket_start": _iso(cursor),
                "bucket_end": _iso(bucket_end),
                "metrics": {
                    metric_id: evaluation["metrics"][metric_id]
                    for metric_id in scope["metrics"]
                },
            }
        )
        cursor = bucket_end
    full_window = _evaluate(dataset, scope, catalog)
    result = {
        "scope": scope,
        "bucket_seconds": step,
        "buckets": buckets,
        "meta": _meta(scope, full_window),
    }
    return _attach_snapshot(result, dataset, raw_scope, store)
