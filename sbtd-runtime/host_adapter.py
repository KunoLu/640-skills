"""Shared core for R1.2b host source adapters.

Adapters translate host-recorded facts (omp session JSONL, codex exec JSONL)
into R1.0 observation events and append them to the R1.2a EventStore. They
never invent executions the host did not record, never write task.md, and
never bypass the observation switch or the store's confirmation requirement.

installation_id / device_id are explicit caller inputs: no runtime component
issues them yet (PRD §5.2), so adapters refuse to fabricate one.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from event_store import Checkpoint, EventStore
from extensions import Drop


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def base_event(
    *,
    event_type: str,
    occurred_at: str | None,
    recorded_at: str,
    installation_id: str,
    device_id: str,
    source_id: str,
    source_event_id: str | None,
    parser_version: str,
    segment_id: str | None = None,
    offset: int | None = None,
    observation_level: str = "execution-observed",
    source_kind: str = "host-observed",
    evidence_status: str = "present",
    actor_kind: str = "agent",
    session_id: str | None = None,
    logical_task_id: str | None = None,
    project_id: str | None = None,
    repository_id: str | None = None,
    worktree_id: str | None = None,
    component: dict[str, Any] | None = None,
    host: dict[str, Any] | None = None,
    state: dict[str, Any] | None = None,
    measurement: dict[str, Any] | None = None,
    correlation: dict[str, Any] | None = None,
    workflow: dict[str, Any] | None = None,
    validation: dict[str, Any] | None = None,
    external_refs: list[dict[str, Any]] | None = None,
    extensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one schema-shaped event. Required identity stays explicit."""
    if not installation_id or not device_id:
        raise ValueError("installation_id and device_id are required")
    event: dict[str, Any] = {
        "schema_version": "1.0",
        "event_id": f"evt_{uuid.uuid4().hex}",
        "event_type": event_type,
        "occurred_at": occurred_at,
        "recorded_at": recorded_at,
        "ingest_seq": 0,
        "installation_id": installation_id,
        "device_id": device_id,
        "actor": {
            "actor_id": None,
            "kind": actor_kind,
            "identity_assurance": "unbound",
        },
        "scope": {
            "tenant_id": None,
            "workspace_id": None,
            "project_id": project_id,
            "repository_id": repository_id,
            "worktree_id": worktree_id,
            "task_uid": None,
            "logical_task_id": logical_task_id,
            "task_run_id": None,
            "session_id": session_id,
        },
        "provenance": {
            "source_kind": source_kind,
            "source_id": source_id,
            "source_event_id": source_event_id,
            "segment_id": segment_id,
            "offset": offset,
            "producer_version": "0.1.0",
            "observation_level": observation_level,
            "evidence_status": evidence_status,
            "parser_version": parser_version,
        },
        "privacy": {
            "classification": "local-metadata",
            "redaction_policy_version": "1",
            "exportable": True,
        },
        "external_refs": [],
        "extensions": extensions or {},
    }
    if component is not None:
        event["component"] = component
    if host is not None:
        event["host"] = host
    if state is not None:
        event["state"] = state
    if measurement is not None:
        event["measurement"] = measurement
    if correlation is not None:
        event["correlation"] = correlation
    if workflow is not None:
        event["workflow"] = workflow
    if validation is not None:
        event["validation"] = validation
    if external_refs is not None:
        event["external_refs"] = external_refs
    return event


@dataclass(frozen=True)
class ParseOutcome:
    events: tuple[dict[str, Any], ...]
    records_read: int
    records_skipped: int
    dropped: tuple[Drop, ...] = ()
    host_version: str = "unknown"


@dataclass(frozen=True)
class IngestReceipt:
    """Structured receipt of one adapter ingest. Not a capability proof."""

    source_id: str
    host_kind: str
    host_version: str
    parser_version: str
    records_read: int
    records_skipped: int
    events_emitted: int
    accepted: int
    duplicate: int
    conflict: int
    rejected: int
    dropped: tuple[Drop, ...] = field(default_factory=tuple)
    checkpoints: tuple[Checkpoint, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "host_kind": self.host_kind,
            "host_version": self.host_version,
            "parser_version": self.parser_version,
            "records_read": self.records_read,
            "records_skipped": self.records_skipped,
            "events_emitted": self.events_emitted,
            "accepted": self.accepted,
            "duplicate": self.duplicate,
            "conflict": self.conflict,
            "rejected": self.rejected,
            "dropped": [
                {"key": drop.key, "reason": drop.reason} for drop in self.dropped
            ],
            "checkpoints": [
                {
                    "source_id": checkpoint.source_id,
                    "segment_id": checkpoint.segment_id,
                    "offset": checkpoint.offset,
                    "parser_version": checkpoint.parser_version,
                }
                for checkpoint in self.checkpoints
            ],
        }


def ingest_events(
    store: EventStore,
    outcome: ParseOutcome,
    *,
    source_id: str,
    host_kind: str,
    parser_version: str,
) -> IngestReceipt:
    """Append parsed events and build the structured receipt."""
    result = store.append(list(outcome.events))
    counts = {"accepted": 0, "duplicate": 0, "conflict": 0, "rejected": 0}
    for item in result.outcomes:
        if item.status in counts:
            counts[item.status] += 1
        else:
            counts["rejected"] += 1
    return IngestReceipt(
        source_id=source_id,
        host_kind=host_kind,
        host_version=outcome.host_version,
        parser_version=parser_version,
        records_read=outcome.records_read,
        records_skipped=outcome.records_skipped,
        events_emitted=len(outcome.events),
        accepted=counts["accepted"],
        duplicate=counts["duplicate"],
        conflict=counts["conflict"],
        rejected=counts["rejected"],
        dropped=outcome.dropped,
        checkpoints=store.checkpoints(),
    )
