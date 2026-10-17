"""R1.3 report snapshot: one immutable frozen view per response family.

A snapshot pins one normalized QueryScope at one ingest watermark. Query,
timeseries, dataset cursor pages, and CSV export all reference the same
snapshot_id; cursors are bound to their snapshot and never mix pages across
snapshots. Reuse happens only while both the query hash and the watermark
are unchanged; a late event mints a new snapshot_id and never rewrites an
old snapshot. Window membership reuses contract_eval._time_class: the range
is half-open [from, to) everywhere.
"""

from __future__ import annotations

import copy
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from contract_eval import (
    _before_end,
    _component_kind,
    _in_population,
    _invocation_identity,
    _latest_state,
    _time_class,
    _usage_records,
    accept_events,
    metric_catalog,
    parse_instant,
)
from history_read import CursorError, decode_cursor, encode_cursor
from stats_query import normalize_scope

DEFAULT_TTL_SECONDS = 3600
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000
REDACTION_POLICY_VERSION = "1"
EXPORT_SCHEMA_VERSION = "1.0"
DATASET_FAMILIES = (
    "task",
    "run",
    "step",
    "gate",
    "component",
    "invocation",
    "validation_run",
    "validation_case",
    "usage",
    "artifact",
    "event",
    "data_quality",
)
_FAMILY_ORDER = {name: index for index, name in enumerate(DATASET_FAMILIES)}


class SnapshotNotFound(KeyError):
    """No snapshot with this id exists or is visible."""


class SnapshotGone(RuntimeError):
    """The snapshot expired. A new snapshot never reuses the old id."""


def _canonical(payload: Any) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _base_fields(event: dict[str, Any]) -> dict[str, Any]:
    scope = event.get("scope") or {}
    provenance = event.get("provenance") or {}
    host = event.get("host") or {}
    workflow = event.get("workflow") or {}
    state = event.get("state") or {}
    measurement = event.get("measurement") or {}
    component = event.get("component") or {}
    correlation = event.get("correlation") or {}
    extensions = event.get("extensions") or {}
    return {
        "project_id": scope.get("project_id"),
        "repository_id": scope.get("repository_id"),
        "worktree_id": scope.get("worktree_id"),
        "actor_id": (event.get("actor") or {}).get("actor_id"),
        "actor_alias": extensions.get("actor_alias"),
        "host_kind": host.get("host_kind"),
        "host_version": host.get("host_version"),
        "task_uid": scope.get("task_uid"),
        "logical_task_id": scope.get("logical_task_id"),
        "task_run_id": scope.get("task_run_id"),
        "session_id": scope.get("session_id"),
        "step_run_id": scope.get("step_run_id"),
        "component_id": component.get("component_id"),
        "component_kind": component.get("kind"),
        "component_version": component.get("version"),
        "invocation_id": correlation.get("invocation_id"),
        "attempt_id": correlation.get("attempt_id"),
        "attempt_no": measurement.get("attempt_no"),
        "event_id": event["event_id"],
        "event_type": event["event_type"],
        "source_id": provenance.get("source_id"),
        "source_event_id": provenance.get("source_event_id"),
        "occurred_at": event.get("occurred_at"),
        "recorded_at": event.get("recorded_at"),
        "duration_ms": measurement.get("duration_ms"),
        "duration_basis": measurement.get("duration_basis"),
        "workflow_mode": workflow.get("mode_at_event"),
        "mode_source": workflow.get("mode_source"),
        "previous_status": state.get("previous"),
        "status": state.get("current"),
        "evidence_status": provenance.get("evidence_status"),
        "observation_level": provenance.get("observation_level"),
        "source_kind": provenance.get("source_kind"),
    }


def _row(record_type: str, record_id: str, relation_role: str, fields: dict) -> dict:
    return {
        "record_type": record_type,
        "record_id": record_id,
        "relation_role": relation_role,
        "fields": fields,
    }


def _task_rows(
    tasks: dict[str, dict], events: list[dict], end: datetime, active: set
) -> list[dict]:
    rows = []
    for task_uid in sorted(tasks):
        history = [
            event
            for event in events
            if (event.get("scope") or {}).get("task_uid") == task_uid
            and event["event_type"]
            in {"task.created", "task.state_changed", "task.reopened"}
            and _before_end(event.get("occurred_at"), end)
        ]
        status = _latest_state(history) or "unknown"
        role = "activity" if task_uid in active else "context"
        rows.append(
            _row(
                "task",
                task_uid,
                role,
                {
                    "task_uid": task_uid,
                    "worktree_id": tasks[task_uid].get("worktree_id"),
                    "status": status,
                },
            )
        )
    return rows


def _run_rows(events: list[dict], in_window_ids: set[str]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for event in events:
        run_id = (event.get("scope") or {}).get("task_run_id")
        if run_id and event["event_type"].startswith("run."):
            grouped.setdefault(run_id, []).append(event)
    rows = []
    for run_id in sorted(grouped):
        members = grouped[run_id]
        started = next((e for e in members if e["event_type"] == "run.started"), None)
        ended = next(
            (
                e
                for e in members
                if e["event_type"] in {"run.finished", "run.interrupted"}
            ),
            None,
        )
        status = "running"
        if ended is not None:
            status = (ended.get("state") or {}).get("current") or ended[
                "event_type"
            ].split(".", 1)[1]
        role = (
            "activity"
            if any(event["event_id"] in in_window_ids for event in members)
            else "context"
        )
        fields = dict(_base_fields(started or members[0]))
        fields.update(
            {
                "task_run_id": run_id,
                "started_at": (started or {}).get("occurred_at"),
                "ended_at": (ended or {}).get("occurred_at"),
                "status": status,
            }
        )
        rows.append(_row("run", run_id, role, fields))
    return rows


def _step_rows(in_window: list[dict]) -> list[dict]:
    finishes = {}
    for event in in_window:
        if event["event_type"] != "step.finished":
            continue
        key = (
            (event.get("scope") or {}).get("task_run_id"),
            (event.get("scope") or {}).get("step_run_id"),
            (event.get("measurement") or {}).get("attempt_no"),
        )
        finishes[key] = (event.get("state") or {}).get("current")
    rows = []
    for event in in_window:
        if event["event_type"] != "step.started":
            continue
        scope = event.get("scope") or {}
        attempt = (event.get("measurement") or {}).get("attempt_no") or 1
        key = (scope.get("task_run_id"), scope.get("step_run_id"), attempt)
        fields = dict(_base_fields(event))
        fields.update(
            {
                "attempt_no": attempt,
                "started_at": event.get("occurred_at"),
                "status": finishes.get(key),
            }
        )
        record_id = f"{scope.get('step_run_id')}#{attempt}"
        rows.append(_row("step", record_id, "activity", fields))
    return rows


def _gate_rows(events: list[dict]) -> list[dict]:
    ordered = sorted(
        (e for e in events if e["event_type"].startswith("gate.")),
        key=lambda e: (e.get("occurred_at") or "", e.get("ingest_seq", 0)),
    )
    slots: dict[tuple, dict] = {}
    for event in ordered:
        gate = event.get("gate") or {}
        key = (gate.get("gate_id"), gate.get("scope_revision"))
        slot = slots.setdefault(
            key,
            {
                "event": event,
                "applicability": None,
                "result": None,
                "evidence_status": None,
            },
        )
        if gate.get("applicability"):
            slot["applicability"] = gate["applicability"]
        if event["event_type"] == "gate.result_recorded":
            slot["result"] = gate.get("normalized_result")
            slot["evidence_status"] = gate.get("evidence_status")
        elif event["event_type"] == "gate.evidence_invalidated":
            slot["evidence_status"] = gate.get("evidence_status") or "invalid"
    rows = []
    for (gate_id, scope_revision), slot in sorted(
        slots.items(), key=lambda item: (str(item[0][0]), str(item[0][1]))
    ):
        fields = dict(_base_fields(slot["event"]))
        fields.update(
            {
                "gate_id": gate_id,
                "gate_scope_revision": scope_revision,
                "applicability": slot["applicability"],
                "normalized_result": slot["result"],
                "evidence_status": slot["evidence_status"],
            }
        )
        rows.append(_row("gate", f"{gate_id}:{scope_revision}", "activity", fields))
    return rows


def _component_rows(events: list[dict]) -> list[dict]:
    latest: dict[str, dict] = {}
    for event in sorted(
        events, key=lambda e: (e.get("occurred_at") or "", e.get("ingest_seq", 0))
    ):
        if event["event_type"] != "component.available":
            continue
        component = event.get("component") or {}
        component_id = component.get("component_id")
        if component_id:
            latest[component_id] = event
    rows = []
    for component_id in sorted(latest):
        rows.append(
            _row(
                "component", component_id, "context", _base_fields(latest[component_id])
            )
        )
    return rows


def _invocation_rows(events: list[dict], start: datetime, end: datetime) -> list[dict]:
    slots: dict[tuple, dict] = {}
    for event in sorted(
        events, key=lambda e: (e.get("occurred_at") or "", e.get("ingest_seq", 0))
    ):
        identity = _invocation_identity(event)
        if (
            not identity
            or event["event_type"] not in {"invocation.started", "invocation.finished"}
            or _component_kind(event) not in {"skill", "tool"}
        ):
            continue
        slot = slots.setdefault(identity, {"started": None, "finished": None})
        if event["event_type"] == "invocation.started" and slot["started"] is None:
            slot["started"] = event
        elif event["event_type"] == "invocation.finished":
            slot["finished"] = event
    rows = []
    for (invocation_id, attempt_id), slot in sorted(slots.items()):
        started = slot["started"]
        if not started or _time_class(started.get("occurred_at"), start, end) != "in":
            continue
        finished = slot["finished"]
        fields = dict(_base_fields(started))
        fields.update(
            {
                "invocation_id": invocation_id,
                "attempt_id": attempt_id,
                "started_at": started.get("occurred_at"),
                "ended_at": (finished or {}).get("occurred_at"),
                "status": ((finished or {}).get("state") or {}).get("current"),
            }
        )
        rows.append(
            _row("invocation", f"{invocation_id}:{attempt_id}", "activity", fields)
        )
    return rows


def _validation_rows(in_window: list[dict]) -> tuple[list[dict], list[dict]]:
    runs: dict[str, dict] = {}
    case_rows = []
    for event in in_window:
        if not event["event_type"].startswith("validation."):
            continue
        validation = event.get("validation") or {}
        validation_id = validation.get("validation_id")
        if not validation_id:
            continue
        slot = runs.setdefault(validation_id, {"started": None, "finished": None})
        if event["event_type"] == "validation.started":
            slot["started"] = event
        else:
            slot["finished"] = event
            for case in validation.get("cases") or []:
                fields = dict(_base_fields(event))
                fields.update(
                    {
                        "validation_run_id": validation_id,
                        "case_id": case.get("case_id"),
                        "attempt_no": case.get("attempt_no"),
                        "normalized_result": case.get("result"),
                    }
                )
                case_rows.append(
                    _row(
                        "validation_case",
                        f"{validation_id}:{case.get('case_id')}:{case.get('attempt_no')}",
                        "activity",
                        fields,
                    )
                )
    run_rows = []
    for validation_id in sorted(runs):
        slot = runs[validation_id]
        finished = slot["finished"]
        validation = ((finished or slot["started"] or {}).get("validation")) or {}
        cases = validation.get("cases") or []
        counts = {"passed": 0, "failed": 0, "skipped": 0}
        for case in cases:
            if case.get("result") in counts:
                counts[case["result"]] += 1
        fields = dict(_base_fields(finished or slot["started"]))
        fields.update(
            {
                "validation_run_id": validation_id,
                "validation_scope": validation.get("e2e_scope"),
                "normalized_result": validation.get("result"),
                "started_at": (slot["started"] or {}).get("occurred_at"),
                "ended_at": (finished or {}).get("occurred_at"),
                "tests_total": len(cases),
                "tests_passed": counts["passed"],
                "tests_failed": counts["failed"],
                "tests_skipped": counts["skipped"],
                "tests_unknown": len(cases) - sum(counts.values()),
            }
        )
        run_rows.append(_row("validation_run", validation_id, "activity", fields))
    return run_rows, case_rows


def _usage_rows(in_window: list[dict]) -> list[dict]:
    usage_events = [
        event
        for event in in_window
        if event["event_type"] in {"usage.recorded", "usage.corrected"}
    ]
    rows = []
    for event in _usage_records(usage_events):
        usage = event.get("usage") or {}
        cost_status = usage.get("cost_status")
        fields = dict(_base_fields(event))
        fields.update(
            {
                "provider": usage.get("provider"),
                "model": usage.get("model"),
                "billing_basis": usage.get("billing_basis"),
                "currency": usage.get("currency"),
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "cache_read_tokens": usage.get("cache_read_tokens"),
                "reasoning_tokens": usage.get("reasoning_tokens"),
                "cost_reported": usage.get("cost_amount")
                if cost_status == "reported"
                else None,
                "cost_estimated": usage.get("cost_amount")
                if cost_status == "estimated"
                else None,
            }
        )
        request_id = usage.get("request_id") or event["event_id"]
        rows.append(_row("usage", request_id, "activity", fields))
    return rows


def _quality_rows(unknown: list[dict], events: list[dict]) -> list[dict]:
    rows = []
    for event in unknown:
        fields = dict(_base_fields(event))
        fields["warning_code"] = "unknown-occurred-at"
        rows.append(
            _row(
                "data_quality",
                f"unknown-occurred-at:{event['event_id']}",
                "quality",
                fields,
            )
        )
    gaps: dict[str, dict] = {}
    gap_events = [
        event
        for event in events
        if event["event_type"] in {"collection.gap_detected", "collection.recovered"}
    ]
    for event in sorted(
        gap_events, key=lambda e: (e.get("occurred_at") or "", e.get("ingest_seq", 0))
    ):
        collection = event.get("collection") or {}
        gap_id = collection.get("gap_id") or event["event_id"]
        if event["event_type"] == "collection.recovered" or collection.get("closed"):
            gaps.pop(gap_id, None)
        else:
            gaps[gap_id] = event
    for gap_id in sorted(gaps):
        fields = dict(_base_fields(gaps[gap_id]))
        fields["warning_code"] = "collection-gap-open"
        rows.append(
            _row("data_quality", f"collection-gap-open:{gap_id}", "quality", fields)
        )
    return rows


def dataset_rows(dataset: dict, scope: dict[str, Any]) -> tuple[list[dict], list[str]]:
    tasks = {task["task_uid"]: task for task in dataset["tasks"]}
    start = parse_instant(scope["from"])
    end = parse_instant(scope["to"])
    accepted = accept_events(dataset["events"])["accepted"]
    population = [event for event in accepted if _in_population(event, scope, tasks)]
    in_window = [
        event
        for event in population
        if _time_class(event.get("occurred_at"), start, end) == "in"
    ]
    before_end = [
        event for event in population if _before_end(event.get("occurred_at"), end)
    ]
    unknown = [event for event in population if event.get("occurred_at") is None]
    unknown_ids = sorted(event["event_id"] for event in unknown)
    in_window_ids = {event["event_id"] for event in in_window}
    active_tasks = {
        (event.get("scope") or {}).get("task_uid")
        for event in in_window
        if (event.get("scope") or {}).get("task_uid")
    }
    selected = scope.get("task_uids") or []
    scoped_tasks = (
        {uid: task for uid, task in tasks.items() if uid in selected}
        if selected
        else tasks
    )
    run_rows, case_rows = _validation_rows(in_window)
    rows = []
    rows += _task_rows(scoped_tasks, accepted, end, active_tasks)
    rows += _run_rows(before_end, in_window_ids)
    rows += _step_rows(in_window)
    rows += _gate_rows(before_end)
    rows += _component_rows(before_end)
    rows += _invocation_rows(before_end, start, end)
    rows += run_rows
    rows += case_rows
    rows += _usage_rows(in_window)
    # artifact: the event schema carries no artifact object, so this family
    # stays empty rather than inventing references.
    for event in sorted(
        in_window, key=lambda e: (e.get("ingest_seq", 0), e["event_id"])
    ):
        rows.append(_row("event", event["event_id"], "activity", _base_fields(event)))
    rows += _quality_rows(unknown, before_end)
    rows.sort(key=lambda row: (_FAMILY_ORDER[row["record_type"]], row["record_id"]))
    return rows, unknown_ids


@dataclass
class Snapshot:
    snapshot_id: str
    created_at: str
    expires_at: str
    query_scope: dict[str, Any]
    query_hash: str
    as_of: str
    effective_from: str
    effective_to: str
    timezone: str
    watermark_seq: int
    source_watermarks: list[dict[str, Any]]
    metrics_version: str
    dataset_manifest: list[dict[str, Any]]
    unknown_time_event_ids: list[str]
    quality_summary: dict[str, Any]
    warnings: list[str]
    redaction_policy_version: str
    export_schema_version: str
    snapshot_digest: str
    raw_scope: dict[str, Any] = field(repr=False)
    dataset: dict[str, Any] = field(repr=False)
    rows: list[dict] = field(repr=False)
    expires_instant: datetime = field(repr=False)

    def public_view(self) -> dict[str, Any]:
        return {
            key: getattr(self, key)
            for key in (
                "snapshot_id",
                "created_at",
                "expires_at",
                "query_scope",
                "query_hash",
                "as_of",
                "effective_from",
                "effective_to",
                "timezone",
                "watermark_seq",
                "source_watermarks",
                "metrics_version",
                "dataset_manifest",
                "unknown_time_event_ids",
                "quality_summary",
                "warnings",
                "redaction_policy_version",
                "export_schema_version",
                "snapshot_digest",
            )
        }


def _iso(instant: datetime) -> str:
    return instant.astimezone(UTC).isoformat().replace("+00:00", "Z")


class SnapshotStore:
    """In-process immutable snapshot registry. No persistence, no writes."""

    def __init__(self, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._snapshots: dict[str, Snapshot] = {}

    def create_or_reuse(
        self,
        dataset: dict,
        raw_scope: dict,
        *,
        now: datetime | None = None,
        source_watermarks: tuple | list = (),
        catalog: dict | None = None,
    ) -> Snapshot:
        now = now or datetime.now(UTC)
        catalog = catalog or metric_catalog()
        scope = normalize_scope(raw_scope, catalog=catalog)
        query_hash = _digest(scope)
        frozen = copy.deepcopy(dataset)
        watermark = max(
            (event.get("ingest_seq", 0) for event in frozen["events"]), default=0
        )
        for snapshot in self._snapshots.values():
            if now >= snapshot.expires_instant:
                continue
            if (
                snapshot.query_hash == query_hash
                and snapshot.watermark_seq == watermark
            ):
                return snapshot
        rows, unknown_ids = dataset_rows(frozen, scope)
        manifest = [{"record_type": family, "rows": 0} for family in DATASET_FAMILIES]
        counts = {item["record_type"]: 0 for item in manifest}
        for row in rows:
            counts[row["record_type"]] += 1
        for item in manifest:
            item["rows"] = counts[item["record_type"]]
        digest = _digest(
            {
                "query_hash": query_hash,
                "watermark_seq": watermark,
                "rows": rows,
            }
        )
        created = now
        expires = now + timedelta(seconds=self._ttl)
        snapshot = Snapshot(
            snapshot_id=f"snap_{uuid.uuid4().hex}",
            created_at=_iso(created),
            expires_at=_iso(expires),
            query_scope=scope,
            query_hash=query_hash,
            as_of=_iso(now),
            effective_from=scope["from"],
            effective_to=scope["to"],
            timezone=scope["timezone"],
            watermark_seq=watermark,
            source_watermarks=[dict(item) for item in source_watermarks],
            metrics_version=catalog["metrics_version"],
            dataset_manifest=manifest,
            unknown_time_event_ids=unknown_ids,
            quality_summary={"unknown_time_events": len(unknown_ids)},
            warnings=["UNKNOWN_OCCURRED_AT"] if unknown_ids else [],
            redaction_policy_version=REDACTION_POLICY_VERSION,
            export_schema_version=EXPORT_SCHEMA_VERSION,
            snapshot_digest=digest,
            raw_scope=copy.deepcopy(raw_scope),
            dataset=frozen,
            rows=rows,
            expires_instant=expires,
        )
        self._snapshots[snapshot.snapshot_id] = snapshot
        return snapshot

    def get(self, snapshot_id: str, *, now: datetime | None = None) -> Snapshot:
        now = now or datetime.now(UTC)
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            raise SnapshotNotFound(snapshot_id)
        if now >= snapshot.expires_instant:
            raise SnapshotGone(snapshot_id)
        return snapshot

    def dataset_page(
        self,
        snapshot_id: str,
        cursor: str | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        snapshot = self.get(snapshot_id, now=now)
        offset = 0
        if cursor is not None:
            payload = decode_cursor(cursor)
            if payload.get("s") != snapshot_id:
                raise CursorError("cursor belongs to a different snapshot")
            offset = payload["o"]
            if offset >= len(snapshot.rows):
                raise CursorError("cursor offset is beyond the result set")
        limit = max(1, min(limit, MAX_PAGE_SIZE))
        page = snapshot.rows[offset : offset + limit]
        end = offset + len(page)
        next_cursor = (
            encode_cursor(end, snapshot_id) if end < len(snapshot.rows) else None
        )
        return {
            "snapshot_id": snapshot_id,
            "rows": page,
            "next_cursor": next_cursor,
            "total": len(snapshot.rows),
        }
