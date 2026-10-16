"""Evaluate R1.0 nouns, denominators, and dedup against a dataset.

This is a pure contract function. It does not store events, open a socket,
or implement R1.1+.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import jsonschema

ROOT = Path(__file__).resolve().parent
CONTRACTS = ROOT / "contracts"
METRICS_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"

CORE_METRICS = frozenset(
    {
        "tasks.touched",
        "tasks.created",
        "tasks.completed_unique",
        "tasks.completion_events",
        "tasks.reopened",
        "tasks.status_at_end",
        "runs.started",
        "runs.interrupted",
        "steps.attempts",
        "steps.success_rate_observed",
        "steps.retry_count",
        "components.invocations",
        "components.failure_rate",
        "gates.required",
        "gates.evidence_coverage",
        "gates.rework",
        "validations.runs",
        "validations.run_pass_rate",
        "tests.first_attempt_pass_rate",
        "tests.final_result_distribution",
        "evidence.stale_count",
        "audit.unlinked_count",
        "audit.gap_intervals",
    }
)
CONDITIONAL_METRICS = frozenset(
    {
        "usage.tokens",
        "usage.cost_reported",
        "usage.cost_estimated",
    }
)
CALL_KINDS = frozenset({"skill", "tool"})
RECEIVER_FIELDS = frozenset({"event_id", "recorded_at", "ingest_seq"})
TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "reasoning_tokens",
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def event_schema() -> dict:
    return load_json(CONTRACTS / "event.schema.json")


def metric_catalog() -> dict:
    return load_json(CONTRACTS / "metrics-catalog.json")


def capability_matrix() -> dict:
    return load_json(CONTRACTS / "capability-matrix.json")


def canonical_content(event: dict) -> str:
    body = {key: value for key, value in event.items() if key not in RECEIVER_FIELDS}
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def dedup_key(event: dict) -> tuple:
    provenance = event["provenance"]
    source_id = provenance["source_id"]
    source_event_id = provenance.get("source_event_id")
    if source_event_id:
        return ("source", source_id, source_event_id)
    return (
        "segment",
        source_id,
        provenance.get("segment_id"),
        provenance.get("offset"),
        canonical_content(event),
    )


def parse_instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp lacks a timezone: {value}")
    return parsed


def civil_window_seconds(timezone: str, start_civil: str, end_civil: str) -> float:
    zone = ZoneInfo(timezone)
    start = datetime.fromisoformat(start_civil).replace(tzinfo=zone)
    end = datetime.fromisoformat(end_civil).replace(tzinfo=zone)
    # Same tzinfo subtraction ignores a DST offset change. Compare absolute instants.
    return end.timestamp() - start.timestamp()


def host_capability(matrix: dict, host_kind: str, host_version: str) -> str:
    for pin in matrix["acceptance_pins"]:
        if pin["host_kind"] == host_kind and pin["host_version"] == host_version:
            return "pinned"
    return "unsupported"


def validate_events(events: list[dict], schema: dict | None = None) -> None:
    definition = schema or event_schema()
    jsonschema.Draft202012Validator.check_schema(definition)
    validator = jsonschema.Draft202012Validator(definition)
    for event in events:
        validator.validate(event)


def _time_class(occurred_at: str | None, start: datetime, end: datetime) -> str:
    if occurred_at is None:
        return "unknown"
    instant = parse_instant(occurred_at)
    if start <= instant < end:
        return "in"
    return "out"


def _before_end(occurred_at: str | None, end: datetime) -> bool:
    if occurred_at is None:
        return False
    return parse_instant(occurred_at) < end


def _task_uid(event: dict) -> str | None:
    return event.get("scope", {}).get("task_uid")


def _run_id(event: dict) -> str | None:
    return event.get("scope", {}).get("task_run_id")


def _selected_tasks(scope: dict) -> set[str] | None:
    selected = scope.get("task_uids") or []
    return set(selected) if selected else None


def _in_population(event: dict, scope: dict, tasks: dict[str, dict]) -> bool:
    task_uid = _task_uid(event)
    selected = _selected_tasks(scope)
    if selected is not None and task_uid not in selected:
        return False
    if scope.get("task_granularity", "executable-leaf") == "executable-leaf" and task_uid:
        if tasks.get(task_uid, {}).get("role") == "summary":
            return False
    return True


def _rate(numerator: int, denominator: int, excluded: dict) -> dict:
    if denominator == 0:
        return {
            "support": "supported",
            "numerator": 0,
            "denominator": 0,
            "value": None,
            "sample_status": "no-decidable-sample",
            "excluded": excluded,
        }
    return {
        "support": "supported",
        "numerator": numerator,
        "denominator": denominator,
        "value": f"{numerator}/{denominator}",
        "sample_status": "decidable",
        "excluded": excluded,
    }


def _unsupported(metric_id: str) -> dict:
    return {
        "metric_id": metric_id,
        "support": "unsupported",
        "value": None,
        "reason": "outside-v2.1.0-rc.1-core-subset",
    }


def _count(value: int, **extra: object) -> dict:
    return {"support": "supported", "value": value, **extra}


def accept_events(events: list[dict]) -> dict:
    ordered = sorted(
        events,
        key=lambda event: (
            event.get("ingest_seq", 0),
            event.get("recorded_at") or "",
            event["event_id"],
        ),
    )
    kept: dict[tuple, dict] = {}
    accepted: list[dict] = []
    confirmed: list[str] = []
    conflicts: list[dict] = []
    for event in ordered:
        key = dedup_key(event)
        content = canonical_content(event)
        previous = kept.get(key)
        if previous is None:
            kept[key] = event
            accepted.append(event)
            continue
        if canonical_content(previous) == content:
            confirmed.append(event["event_id"])
            continue
        conflicts.append(
            {
                "event_id": event["event_id"],
                "kept_event_id": previous["event_id"],
                "key": list(key[:3]),
            }
        )
    return {
        "accepted": accepted,
        "confirmed_event_ids": confirmed,
        "conflicts": conflicts,
    }


def _invocation_identity(event: dict) -> tuple[str, str] | None:
    correlation = event.get("correlation") or {}
    invocation_id = correlation.get("invocation_id")
    if not invocation_id:
        return None
    return invocation_id, str(correlation.get("attempt_id") or "1")


def _component_kind(event: dict) -> str | None:
    component = event.get("component") or {}
    return component.get("kind")


def _latest_state(events: list[dict]) -> str | None:
    current = None
    for event in events:
        state = (event.get("state") or {}).get("current")
        if state:
            current = state
    return current


def _usage_records(events: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for event in events:
        if event["event_type"] != "usage.recorded":
            continue
        usage = event.get("usage") or {}
        request_id = usage.get("request_id") or event["event_id"]
        grouped.setdefault(request_id, []).append(event)
    kept: list[dict] = []
    for request_id, group in grouped.items():
        details = [event for event in group if not (event.get("usage") or {}).get("rollup")]
        chosen = details or group
        # One request is one billable fact. Extra detail copies still collapse.
        kept.append(chosen[0])
    return kept


def _token_sum(records: list[dict]) -> dict:
    observed: list[str] = []
    missing: list[str] = []
    totals = {field: 0 for field in TOKEN_FIELDS}
    seen = {field: False for field in TOKEN_FIELDS}
    includes_cache = False
    for event in records:
        usage = event.get("usage") or {}
        request_id = usage.get("request_id") or event["event_id"]
        present = [field for field in TOKEN_FIELDS if usage.get(field) is not None]
        if not present:
            missing.append(request_id)
            continue
        observed.append(request_id)
        includes_cache = includes_cache or bool(usage.get("input_includes_cache"))
        for field in present:
            totals[field] += usage[field]
            seen[field] = True
    value = {
        field: totals[field] if seen[field] else None for field in TOKEN_FIELDS
    }
    return {
        "support": "conditional",
        "value": value,
        "missing": bool(missing) or not observed,
        "missing_request_ids": sorted(missing),
        "observed_request_ids": sorted(observed),
        "input_includes_cache": includes_cache,
    }


def _cost_reported(records: list[dict]) -> dict:
    by_currency: dict[str, float] = {}
    statuses: set[str] = set()
    for event in records:
        usage = event.get("usage") or {}
        status = usage.get("cost_status") or "missing"
        statuses.add(status)
        amount = usage.get("cost_amount")
        if status == "reported" and amount is not None:
            currency = usage.get("currency") or "unknown"
            by_currency[currency] = by_currency.get(currency, 0) + amount
    return {
        "support": "conditional",
        "value": None if not by_currency else by_currency,
        "missing": not by_currency,
        "by_currency": by_currency,
        "statuses": sorted(statuses),
    }


def _cost_estimated(records: list[dict]) -> dict:
    estimated = []
    for event in records:
        usage = event.get("usage") or {}
        if usage.get("cost_status") == "estimated" and usage.get("cost_amount") is not None:
            estimated.append(event["event_id"])
    return {
        "support": "conditional",
        "value": None if not estimated else {"event_ids": estimated},
        "missing": not estimated,
        "missing_reason": None if estimated else "source-not-provided",
    }


def evaluate(dataset: dict, scope: dict, catalog: dict | None = None, matrix: dict | None = None) -> dict:
    before = json.dumps(dataset, ensure_ascii=False, sort_keys=True)
    catalog = catalog or metric_catalog()
    matrix = matrix or capability_matrix()
    tasks = {task["task_uid"]: task for task in dataset["tasks"]}
    start = parse_instant(scope["from"])
    end = parse_instant(scope["to"])
    acceptance = accept_events(dataset["events"])
    accepted = acceptance["accepted"]

    def timed(event: dict) -> str:
        return _time_class(event.get("occurred_at"), start, end)

    in_window = [
        event
        for event in accepted
        if timed(event) == "in" and _in_population(event, scope, tasks)
    ]
    unknown_time = [
        event["event_id"]
        for event in accepted
        if timed(event) == "unknown" and _in_population(event, scope, tasks)
    ]
    leaf_ids = {
        task_uid
        for task_uid, task in tasks.items()
        if task.get("role") != "summary"
        and (
            _selected_tasks(scope) is None or task_uid in _selected_tasks(scope)
        )
    }

    def leaf_events(events: list[dict]) -> list[dict]:
        return [event for event in events if _task_uid(event) in leaf_ids]

    window_leaf = leaf_events(in_window)
    touched = {
        _task_uid(event)
        for event in window_leaf
        if _task_uid(event)
    }
    created = {
        _task_uid(event)
        for event in window_leaf
        if event["event_type"] == "task.created" and _task_uid(event)
    }
    done_events = [
        event
        for event in window_leaf
        if event["event_type"] == "task.state_changed"
        and (event.get("state") or {}).get("current") == "done"
    ]
    reopened = [
        event for event in window_leaf if event["event_type"] == "task.reopened"
    ]
    status: dict[str, int] = {}
    for task_uid in sorted(leaf_ids):
        history = [
            event
            for event in accepted
            if _task_uid(event) == task_uid
            and event["event_type"] in {"task.created", "task.state_changed", "task.reopened"}
            and _before_end(event.get("occurred_at"), end)
        ]
        current = _latest_state(history) or "unknown"
        status[current] = status.get(current, 0) + 1

    started_runs = {
        _run_id(event)
        for event in window_leaf
        if event["event_type"] == "run.started" and _run_id(event)
    }
    interrupted = {
        _run_id(event)
        for event in window_leaf
        if event["event_type"] == "run.interrupted" and _run_id(event)
    }
    run_history: dict[str, list[dict]] = {}
    for event in accepted:
        run_id = _run_id(event)
        if run_id and _task_uid(event) in leaf_ids and event["event_type"].startswith("run."):
            if _before_end(event.get("occurred_at"), end):
                run_history.setdefault(run_id, []).append(event)
    unknown_runs = []
    for run_id, history in run_history.items():
        types = {event["event_type"] for event in history}
        if "run.started" in types and "run.finished" not in types and "run.interrupted" not in types:
            unknown_runs.append(run_id)

    step_starts = [event for event in window_leaf if event["event_type"] == "step.started"]
    step_finishes = [event for event in window_leaf if event["event_type"] == "step.finished"]
    succeeded = [
        event
        for event in step_finishes
        if (event.get("state") or {}).get("current") == "succeeded"
    ]
    failed = [
        event
        for event in step_finishes
        if (event.get("state") or {}).get("current") == "failed"
    ]
    blocked = [
        event
        for event in step_finishes
        if (event.get("state") or {}).get("current") == "blocked"
    ]
    finished_ids = {
        (
            _run_id(event),
            event.get("scope", {}).get("step_run_id"),
            (event.get("measurement") or {}).get("attempt_no"),
        )
        for event in step_finishes
    }
    unknown_steps = [
        event
        for event in step_starts
        if (
            _run_id(event),
            event.get("scope", {}).get("step_run_id"),
            (event.get("measurement") or {}).get("attempt_no"),
        )
        not in finished_ids
    ]
    retries = [
        event
        for event in step_starts
        if ((event.get("measurement") or {}).get("attempt_no") or 1) > 1
    ]

    invocations: dict[tuple[str, str], dict] = {}
    for event in in_window:
        identity = _invocation_identity(event)
        if identity is None or event["event_type"] not in {"invocation.started", "invocation.finished"}:
            continue
        if _component_kind(event) not in CALL_KINDS:
            continue
        slot = invocations.setdefault(
            identity,
            {"source_ids": [], "result": None, "started": False, "host": None},
        )
        source_id = event["provenance"]["source_id"]
        if source_id not in slot["source_ids"]:
            slot["source_ids"].append(source_id)
        host = event.get("host") or {}
        if host.get("host_kind") and host.get("host_version"):
            slot["host"] = f"{host['host_kind']}@{host['host_version']}"
        if event["event_type"] == "invocation.started":
            slot["started"] = True
        else:
            slot["result"] = (event.get("state") or {}).get("current")
    started_invocations = {
        identity: slot for identity, slot in invocations.items() if slot["started"]
    }
    invocation_failed = [
        identity
        for identity, slot in started_invocations.items()
        if slot["result"] == "failed"
    ]
    invocation_succeeded = [
        identity
        for identity, slot in started_invocations.items()
        if slot["result"] == "succeeded"
    ]
    invocation_unknown = [
        identity
        for identity, slot in started_invocations.items()
        if slot["result"] not in {"succeeded", "failed"}
    ]

    gate_events = [event for event in window_leaf if event["event_type"].startswith("gate.")]
    gates: dict[tuple[str, str], dict] = {}
    for event in gate_events:
        gate = event.get("gate") or {}
        key = (gate.get("gate_id"), gate.get("scope_revision"))
        slot = gates.setdefault(
            key,
            {"applicability": None, "result": None, "evidence_status": None, "corrections": 0},
        )
        if gate.get("applicability"):
            slot["applicability"] = gate["applicability"]
        if event["event_type"] == "gate.result_recorded":
            slot["result"] = gate.get("normalized_result")
            slot["evidence_status"] = gate.get("evidence_status")
            if gate.get("correction"):
                slot["corrections"] += 1
    required = [slot for slot in gates.values() if slot["applicability"] == "required"]
    covered = [
        slot
        for slot in required
        if slot["result"] == "passed" and slot["evidence_status"] == "validated"
    ]
    gate_excluded = {
        "not_required": sum(slot["applicability"] == "not-required" for slot in gates.values()),
        "undecided": sum(slot["applicability"] == "undecided" for slot in gates.values()),
        "declared_only": sum(
            slot["evidence_status"] == "declared" for slot in required
        ),
        "stale": sum(slot["evidence_status"] == "stale" for slot in required),
    }

    validation_starts = [
        event for event in window_leaf if event["event_type"] == "validation.started"
    ]
    validation_finishes = [
        event for event in window_leaf if event["event_type"] == "validation.finished"
    ]
    strata: dict[str, dict] = {}
    for event in validation_finishes:
        validation = event.get("validation") or {}
        stratum = validation.get("e2e_scope") or "unknown"
        bucket = strata.setdefault(stratum, {"passed": 0, "failed": 0})
        result = validation.get("result")
        if result in bucket:
            bucket[result] += 1
    pass_rates = {
        stratum: _rate(bucket["passed"], bucket["passed"] + bucket["failed"], {})
        for stratum, bucket in strata.items()
    }
    for stratum in ("narrow", "full-stack"):
        pass_rates.setdefault(stratum, _rate(0, 0, {}))

    cases: dict[str, list[dict]] = {}
    for event in validation_finishes:
        for case in (event.get("validation") or {}).get("cases") or []:
            cases.setdefault(case["case_id"], []).append(case)
    first_passed = 0
    first_decidable = 0
    final_distribution: dict[str, int] = {}
    for case_id, attempts in cases.items():
        ordered_cases = sorted(attempts, key=lambda case: case["attempt_no"])
        first = ordered_cases[0]
        if first["result"] in {"passed", "failed"}:
            first_decidable += 1
            if first["result"] == "passed":
                first_passed += 1
        final_distribution[ordered_cases[-1]["result"]] = (
            final_distribution.get(ordered_cases[-1]["result"], 0) + 1
        )

    stale = [
        event["event_id"]
        for event in window_leaf
        if event.get("provenance", {}).get("evidence_status") == "stale"
        or (event.get("gate") or {}).get("evidence_status") == "stale"
    ]
    unlinked = [
        event["event_id"]
        for event in in_window
        if not _task_uid(event)
    ]
    gaps = []
    for event in in_window:
        if event["event_type"] != "collection.gap_detected":
            continue
        collection = event.get("collection") or {}
        if not collection.get("closed"):
            gaps.append(collection.get("gap_id") or event["event_id"])

    usage_events = [
        event
        for event in accepted
        if event["event_type"] == "usage.recorded" and timed(event) == "in"
    ]
    usage_kept = [
        event
        for event in _usage_records(usage_events)
        if _in_population(event, scope, tasks)
    ]
    hosts: dict[str, str] = {}
    for event in accepted:
        host = event.get("host") or {}
        if host.get("host_kind") and host.get("host_version"):
            label = f"{host['host_kind']}@{host['host_version']}"
            hosts[label] = host_capability(matrix, host["host_kind"], host["host_version"])

    computed = {
        "tasks.touched": _count(len(touched), task_uids=sorted(touched)),
        "tasks.created": _count(len(created), task_uids=sorted(created)),
        "tasks.completed_unique": _count(
            len({_task_uid(event) for event in done_events}),
            task_uids=sorted({_task_uid(event) for event in done_events}),
        ),
        "tasks.completion_events": _count(len(done_events)),
        "tasks.reopened": _count(len(reopened)),
        "tasks.status_at_end": {
            "support": "supported",
            "value": status,
            "unknown_count": status.get("unknown", 0),
        },
        "runs.started": _count(len(started_runs), run_ids=sorted(started_runs)),
        "runs.interrupted": _count(
            len(interrupted),
            run_ids=sorted(interrupted),
            unknown_count=len(unknown_runs),
            unknown_run_ids=sorted(unknown_runs),
        ),
        "steps.attempts": _count(len(step_starts)),
        "steps.success_rate_observed": _rate(
            len(succeeded),
            len(succeeded) + len(failed),
            {
                "blocked": len(blocked),
                "unknown": len(unknown_steps),
                "cancelled": sum(
                    (event.get("state") or {}).get("current") == "cancelled"
                    for event in step_finishes
                ),
            },
        ),
        "steps.retry_count": _count(len(retries)),
        "components.invocations": _count(
            len(started_invocations),
            invocation_ids=sorted(identity[0] for identity in started_invocations),
        ),
        "components.failure_rate": _rate(
            len(invocation_failed),
            len(invocation_failed) + len(invocation_succeeded),
            {"unknown": len(invocation_unknown)},
        ),
        "gates.required": _count(len(required)),
        "gates.evidence_coverage": _rate(len(covered), len(required), gate_excluded),
        "gates.rework": _count(sum(slot["corrections"] for slot in gates.values())),
        "validations.runs": _count(
            len(validation_starts),
            unfinished=sum(
                event["event_type"] == "validation.started"
                and event.get("validation", {}).get("validation_id")
                not in {
                    finish.get("validation", {}).get("validation_id")
                    for finish in validation_finishes
                }
                for event in validation_starts
            ),
        ),
        "validations.run_pass_rate": {
            "support": "supported",
            "value": None,
            "strata": pass_rates,
        },
        "tests.first_attempt_pass_rate": _rate(first_passed, first_decidable, {}),
        "tests.final_result_distribution": {
            "support": "supported",
            "value": final_distribution,
        },
        "evidence.stale_count": _count(len(set(stale)), event_ids=sorted(set(stale))),
        "audit.unlinked_count": _count(len(unlinked), event_ids=sorted(unlinked)),
        "audit.gap_intervals": _count(len(gaps), gap_ids=sorted(gaps)),
        "usage.tokens": _token_sum(usage_kept),
        "usage.cost_reported": _cost_reported(usage_kept),
        "usage.cost_estimated": _cost_estimated(usage_kept),
    }
    metrics = {}
    for item in catalog["metrics"]:
        metric_id = item["metric_id"]
        if item["support"] == "unsupported":
            metrics[metric_id] = _unsupported(metric_id)
            continue
        if metric_id not in computed:
            raise KeyError(f"catalog support has no evaluator: {metric_id}")
        metrics[metric_id] = computed[metric_id]
        metrics[metric_id]["metric_id"] = metric_id
    if json.dumps(dataset, ensure_ascii=False, sort_keys=True) != before:
        raise RuntimeError("evaluate mutated the dataset")
    return {
        "metrics_version": METRICS_VERSION,
        "schema_version": SCHEMA_VERSION,
        "dedup": {
            "accepted_event_ids": [event["event_id"] for event in accepted],
            "confirmed_event_ids": acceptance["confirmed_event_ids"],
            "conflicts": acceptance["conflicts"],
        },
        "invocations": {
            identity[0]: {
                "attempt_id": identity[1],
                "source_ids": slot["source_ids"],
                "result": slot["result"],
                "host": slot["host"],
            }
            for identity, slot in started_invocations.items()
        },
        "metrics": metrics,
        "capability": hosts,
        "unknown_time_event_ids": unknown_time,
    }
