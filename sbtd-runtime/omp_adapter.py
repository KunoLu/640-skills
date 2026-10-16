"""OMP host adapter (R1.2b): session JSONL -> R1.0 observation events.

Reads an omp session JSONL file the caller explicitly passes (omp stores them
under ~/.omp/agent/sessions/<cwd-slug>/). The adapter never writes the session
file and never scans HOME. Observed record shapes come from real omp 18.11.1
sessions on this host:

- {"type": "session", "id": ..., "timestamp": ...}         -> context
- assistant message content item {"type": "toolCall", "id", "name",
  "arguments"}                                             -> invocation.started
  (name == "read" with arguments.path "skill://<name>"     -> skill.loaded)
- toolResult message {"toolCallId", "toolName", "isError"} -> invocation.finished

Other record types and malformed tail lines are skipped and counted.
Arguments, outputs and message text are never copied into events
(observation.level=metadata). parser_version pins this mapping.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from host_adapter import (
    IngestReceipt,
    ParseOutcome,
    base_event,
    ingest_events,
    utc_now,
)

PARSER_VERSION = "omp-session-jsonl-1"
SOURCE_ID = "omp-session"
_HOST_KIND = "omp"
_SKILL_PREFIX = "skill://"
# contracts/event.schema.json: occurred_at must be RFC 3339 with timezone.
_OCCURRED_AT = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
# contracts/event.schema.json: component_id maxLength.
_MAX_COMPONENT_ID = 128


def _valid_instant(value: Any) -> str | None:
    """Keep only schema-valid instants; anything else becomes null."""
    if isinstance(value, str) and _OCCURRED_AT.match(value):
        return value
    return None


def _parse_instant_ms(value: str) -> int:
    parsed = datetime.fromisoformat(value)
    return int(parsed.timestamp() * 1000)


def _skill_name(path: str) -> str:
    return path[len(_SKILL_PREFIX) :].split("/", 1)[0]


def _host_version(record: dict[str, Any], fallback: str) -> str:
    runtime = record.get("runtime")
    if isinstance(runtime, dict) and isinstance(runtime.get("version"), str):
        return str(runtime["version"])
    return fallback


def parse_session_records(
    lines: Iterable[tuple[int, str]],
    *,
    installation_id: str,
    device_id: str,
    segment_id: str,
) -> ParseOutcome:
    """Translate (byte-offset, line) pairs into observation events."""
    events: list[dict[str, Any]] = []
    records_read = 0
    records_skipped = 0
    session_id: str | None = None
    host_version = "unknown"
    started: dict[str, tuple[str, str]] = {}  # toolCallId -> (timestamp, name)
    recorded_at = utc_now()
    for offset, line in lines:
        text = line.strip()
        if not text:
            continue
        records_read += 1
        try:
            record = json.loads(text)
        except json.JSONDecodeError:
            records_skipped += 1
            continue
        if not isinstance(record, dict):
            records_skipped += 1
            continue
        record_type = record.get("type")
        if record_type == "session":
            if isinstance(record.get("id"), str):
                session_id = record["id"]
            continue
        host_version = _host_version(record, host_version)
        if record_type != "message" or not isinstance(record.get("message"), dict):
            records_skipped += 1
            continue
        message = record["message"]
        occurred_at = _valid_instant(record.get("timestamp"))
        host = {"host_kind": _HOST_KIND, "host_version": host_version}
        role = message.get("role")
        if role == "assistant":
            content = message.get("content")
            if not isinstance(content, list):
                records_skipped += 1
                continue
            for item in content:
                if not isinstance(item, dict) or item.get("type") != "toolCall":
                    continue
                call_id = item.get("id")
                name = item.get("name")
                if not isinstance(call_id, str) or not isinstance(name, str):
                    records_skipped += 1
                    continue
                component_id = f"tool:{name}"
                if len(component_id) > _MAX_COMPONENT_ID:
                    records_skipped += 1
                    continue
                arguments = item.get("arguments")
                skill_path = (
                    arguments.get("path") if isinstance(arguments, dict) else None
                )
                if (
                    name == "read"
                    and isinstance(skill_path, str)
                    and skill_path.startswith(_SKILL_PREFIX)
                    and _skill_name(skill_path)
                ):
                    skill_component_id = f"skill:{_skill_name(skill_path)}"
                    # A skill read is both a real `read` invocation (tracked
                    # below) and a skill load fact. skill.loaded only states
                    # the host read the skill resource, not that it passed.
                    if len(skill_component_id) <= _MAX_COMPONENT_ID:
                        events.append(
                            base_event(
                                event_type="skill.loaded",
                                occurred_at=occurred_at,
                                recorded_at=recorded_at,
                                installation_id=installation_id,
                                device_id=device_id,
                                source_id=SOURCE_ID,
                                source_event_id=f"{call_id}:skill-loaded",
                                parser_version=PARSER_VERSION,
                                segment_id=segment_id,
                                offset=offset,
                                observation_level="loaded",
                                session_id=session_id,
                                component={
                                    "component_id": skill_component_id,
                                    "kind": "skill",
                                },
                                host=host,
                            )
                        )
                started[call_id] = (occurred_at or "", name)
                events.append(
                    base_event(
                        event_type="invocation.started",
                        occurred_at=occurred_at,
                        recorded_at=recorded_at,
                        installation_id=installation_id,
                        device_id=device_id,
                        source_id=SOURCE_ID,
                        source_event_id=call_id,
                        parser_version=PARSER_VERSION,
                        segment_id=segment_id,
                        offset=offset,
                        session_id=session_id,
                        component={
                            "component_id": component_id,
                            "kind": "tool",
                            "name": name,
                        },
                        host=host,
                        state={"previous": None, "current": "running"},
                        correlation={"invocation_id": call_id, "attempt_id": "1"},
                    )
                )
            continue
        if role == "toolResult":
            call_id = message.get("toolCallId")
            result_id = record.get("id")
            if not isinstance(call_id, str) or not isinstance(result_id, str):
                records_skipped += 1
                continue
            failed = message.get("isError") is True
            measurement = None
            start = started.get(call_id)
            if start is not None and start[0] and occurred_at:
                try:
                    duration = _parse_instant_ms(occurred_at) - (
                        _parse_instant_ms(start[0])
                    )
                except ValueError:
                    duration = None
                if duration is not None and duration >= 0:
                    measurement = {
                        "duration_ms": duration,
                        "duration_basis": "wall",
                    }
            events.append(
                base_event(
                    event_type="invocation.finished",
                    occurred_at=occurred_at,
                    recorded_at=recorded_at,
                    installation_id=installation_id,
                    device_id=device_id,
                    source_id=SOURCE_ID,
                    source_event_id=result_id,
                    parser_version=PARSER_VERSION,
                    segment_id=segment_id,
                    offset=offset,
                    session_id=session_id,
                    component={
                        "component_id": f"tool:{message.get('toolName') or call_id}",
                        "kind": "tool",
                        "name": str(message.get("toolName") or call_id),
                    },
                    host=host,
                    state={
                        # previous=running only when this session observed the
                        # start; an orphan result must not invent it.
                        "previous": "running" if start is not None else None,
                        "current": "failed" if failed else "succeeded",
                    },
                    measurement=measurement,
                    correlation={"invocation_id": call_id, "attempt_id": "1"},
                )
            )
            continue
        records_skipped += 1
    return ParseOutcome(
        events=tuple(events),
        records_read=records_read,
        records_skipped=records_skipped,
        host_version=host_version,
    )


def parse_session_file(
    path: Path | str,
    *,
    installation_id: str,
    device_id: str,
) -> ParseOutcome:
    source = Path(path)
    raw = source.read_bytes()
    lines: list[tuple[int, str]] = []
    offset = 0
    for chunk in raw.split(b"\n"):
        offset += len(chunk) + 1
        try:
            text = chunk.decode("utf-8")
        except UnicodeDecodeError:
            lines.append((offset, ""))
            continue
        lines.append((offset, text))
    return parse_session_records(
        lines,
        installation_id=installation_id,
        device_id=device_id,
        segment_id=source.name,
    )


def ingest_session(
    store: Any,
    path: Path | str,
    *,
    installation_id: str,
    device_id: str,
) -> IngestReceipt:
    outcome = parse_session_file(
        path, installation_id=installation_id, device_id=device_id
    )
    return ingest_events(
        store,
        outcome,
        source_id=SOURCE_ID,
        host_kind=_HOST_KIND,
        parser_version=PARSER_VERSION,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ingest one omp session JSONL into the R1.2a event store."
    )
    parser.add_argument("session_file", help="path to the omp session JSONL")
    parser.add_argument("--runtime-home", required=True, help="SBTD_RUNTIME_HOME")
    parser.add_argument("--installation-id", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument(
        "--confirmed",
        action="store_true",
        help="confirm opening the store for writing (creates audit.db)",
    )
    args = parser.parse_args(argv)
    if not args.installation_id or not args.device_id:
        print(json.dumps({"error": "installation_id and device_id are required"}))
        return 2
    from event_store import EventStore, StoreError

    try:
        with EventStore.open(
            Path(args.runtime_home), confirmed=args.confirmed
        ) as store:
            receipt = ingest_session(
                store,
                args.session_file,
                installation_id=args.installation_id,
                device_id=args.device_id,
            )
    except StoreError as exc:
        print(json.dumps({"error": exc.reason}, ensure_ascii=False))
        return 2
    except OSError as exc:
        print(json.dumps({"error": f"session file unreadable: {exc}"}))
        return 2
    print(json.dumps(receipt.as_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
