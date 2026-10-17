"""R1.3 history read paths over the event store.

Reads go through EventStore.replay(); this module never rescans files,
never writes, and never changes append or dedup semantics. Window filters
are half-open [from, to): an event with occurred_at == to is out. Events
without occurred_at stay visible in unfiltered reads and are excluded from
windowed reads, never backfilled.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Iterable
from typing import Any

from contract_eval import parse_instant

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000
TASK_HISTORY_PREFIXES = ("task.", "mode.")


class CursorError(ValueError):
    """An opaque cursor could not be decoded or is out of range."""


def _order(event: dict[str, Any]) -> tuple:
    return (
        event.get("ingest_seq", 0),
        event.get("recorded_at") or "",
        event["event_id"],
    )


def encode_cursor(offset: int, snapshot_id: str | None = None) -> str:
    payload = {"o": offset}
    if snapshot_id is not None:
        payload["s"] = snapshot_id
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(cursor: str) -> dict[str, Any]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        payload = json.loads(raw)
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise CursorError(f"cursor cannot be decoded: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("o"), int):
        raise CursorError("cursor payload is malformed")
    if payload["o"] < 0:
        raise CursorError("cursor offset is negative")
    return payload


def paginate(
    items: list[Any], cursor: str | None = None, limit: int = DEFAULT_PAGE_SIZE
) -> dict[str, Any]:
    offset = 0
    if cursor is not None:
        offset = decode_cursor(cursor)["o"]
        if offset >= len(items):
            raise CursorError("cursor offset is beyond the result set")
    limit = max(1, min(limit, MAX_PAGE_SIZE))
    page = items[offset : offset + limit]
    end = offset + len(page)
    next_cursor = encode_cursor(end) if end < len(items) else None
    return {"items": page, "next_cursor": next_cursor, "total": len(items)}


def list_events(
    events: Iterable[dict[str, Any]],
    *,
    task_uid: str | None = None,
    event_types: Iterable[str] | None = None,
    from_at: str | None = None,
    to_at: str | None = None,
) -> list[dict[str, Any]]:
    types = set(event_types) if event_types is not None else None
    start = parse_instant(from_at) if from_at else None
    end = parse_instant(to_at) if to_at else None
    rows = []
    for event in events:
        if task_uid is not None and event.get("scope", {}).get("task_uid") != task_uid:
            continue
        if types is not None and event["event_type"] not in types:
            continue
        if start is not None or end is not None:
            occurred = event.get("occurred_at")
            if occurred is None:
                continue
            instant = parse_instant(occurred)
            if start is not None and instant < start:
                continue
            if end is not None and instant >= end:
                continue
        rows.append(event)
    return sorted(rows, key=_order)


def task_history(events: Iterable[dict[str, Any]], task_uid: str) -> dict[str, Any]:
    rows = [
        event
        for event in list_events(events, task_uid=task_uid)
        if event["event_type"].startswith(TASK_HISTORY_PREFIXES)
    ]
    latest = None
    for event in rows:
        if event["event_type"] in {
            "task.created",
            "task.state_changed",
            "task.reopened",
        }:
            state = (event.get("state") or {}).get("current")
            if state:
                latest = state
    return {"task_uid": task_uid, "events": rows, "latest_status": latest}
