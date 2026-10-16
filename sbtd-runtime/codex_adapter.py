"""Codex host adapter (R1.2b): `codex exec --json` JSONL -> observation events.

Source: the JSONL event stream `codex exec --json` writes to stdout, either
piped live on stdin or replayed from a saved capture file. The stream carries
no timestamps, so occurred_at stays null (PRD section 8.4 rule 8: records with
unknown occurred_at enter the unlocatable set); recorded_at is the ingest
time. The host version is not in the stream either: callers pass the output of
`codex --version`.

Mapped item types: command_execution, mcp_tool_call, web_search,
collab_tool_call, file_change. item.started -> invocation.started;
item.completed -> invocation.finished. item.updated, turn.*, error lines and
unknown item types are skipped and counted. Commands, outputs and arguments
are never copied into events (observation.level=metadata); only the scalar
exit_code is kept as an extension.

This repository never installs or runs codex. The real smoke against
codex@0.163.0 follows sbtd-runtime/docs/host-adapters.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extensions import normalize_extensions
from host_adapter import (
    IngestReceipt,
    ParseOutcome,
    base_event,
    ingest_events,
    utc_now,
)

PARSER_VERSION = "codex-exec-jsonl-1"
SOURCE_ID = "codex-exec"
_HOST_KIND = "codex"

_ITEM_COMPONENTS = {
    "command_execution": ("tool", "tool:command_execution"),
    "web_search": ("tool", "tool:web_search"),
    "collab_tool_call": ("tool", "tool:collab_tool_call"),
    "file_change": ("tool", "tool:file_change"),
}

_STATUS_RESULTS = {
    "completed": "succeeded",
    "failed": "failed",
    "declined": "declined",
}


def _component(item: dict[str, Any]) -> dict[str, Any] | None:
    item_type = item.get("type")
    if item_type == "mcp_tool_call":
        server = item.get("server")
        tool = item.get("tool")
        if not isinstance(server, str) or not isinstance(tool, str):
            return None
        component_id = f"mcp:{server}.{tool}"
        if len(component_id) > 128:
            return None
        return {"component_id": component_id, "kind": "mcp", "name": tool}
    mapped = _ITEM_COMPONENTS.get(str(item_type))
    if mapped is None:
        return None
    kind, component_id = mapped
    return {"component_id": component_id, "kind": kind, "name": str(item_type)}


def parse_exec_lines(
    lines: Iterable[str],
    *,
    installation_id: str,
    device_id: str,
    segment_id: str,
    host_version: str = "unknown",
) -> ParseOutcome:
    """Translate exec JSONL lines into observation events."""
    events: list[dict[str, Any]] = []
    drops = []
    records_read = 0
    records_skipped = 0
    thread_id: str | None = None
    started_ids: set[str] = set()
    recorded_at = utc_now()
    host = {"host_kind": _HOST_KIND, "host_version": host_version}
    for line in lines:
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
        if record_type == "thread.started":
            if isinstance(record.get("thread_id"), str):
                thread_id = record["thread_id"]
            continue
        if record_type not in ("item.started", "item.completed"):
            records_skipped += 1
            continue
        item = record.get("item")
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            records_skipped += 1
            continue
        component = _component(item)
        if component is None:
            records_skipped += 1
            continue
        item_id = item["id"]
        phase = "started" if record_type == "item.started" else "completed"
        common: dict[str, Any] = {
            "occurred_at": None,
            "recorded_at": recorded_at,
            "installation_id": installation_id,
            "device_id": device_id,
            "source_id": SOURCE_ID,
            "source_event_id": f"{item_id}:{phase}",
            "parser_version": PARSER_VERSION,
            "segment_id": segment_id,
            "session_id": thread_id,
            "component": component,
            "host": host,
            "correlation": {"invocation_id": item_id, "attempt_id": "1"},
        }
        if phase == "started":
            started_ids.add(item_id)
            events.append(
                base_event(
                    event_type="invocation.started",
                    state={"previous": None, "current": "running"},
                    **common,
                )
            )
            continue
        result = _STATUS_RESULTS.get(str(item.get("status")))
        if result is None:
            records_skipped += 1
            continue
        raw_extensions: dict[str, Any] = {}
        if isinstance(item.get("exit_code"), int) and not isinstance(
            item.get("exit_code"), bool
        ):
            raw_extensions["exit_code"] = item["exit_code"]
        extensions, dropped = normalize_extensions(
            raw_extensions, priority=("exit_code",)
        )
        drops.extend(dropped)
        events.append(
            base_event(
                event_type="invocation.finished",
                # previous=running only when the stream showed the start.
                state={
                    "previous": "running" if item_id in started_ids else None,
                    "current": result,
                },
                extensions=extensions,
                **common,
            )
        )
    return ParseOutcome(
        events=tuple(events),
        records_read=records_read,
        records_skipped=records_skipped,
        dropped=tuple(drops),
        host_version=host_version,
    )


def ingest_exec_stream(
    store: Any,
    lines: Iterable[str],
    *,
    installation_id: str,
    device_id: str,
    segment_id: str,
    host_version: str = "unknown",
) -> IngestReceipt:
    outcome = parse_exec_lines(
        lines,
        installation_id=installation_id,
        device_id=device_id,
        segment_id=segment_id,
        host_version=host_version,
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
        description=(
            "Ingest `codex exec --json` output (stdin or --file) into the "
            "R1.2a event store."
        )
    )
    parser.add_argument("--runtime-home", required=True, help="SBTD_RUNTIME_HOME")
    parser.add_argument("--installation-id", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument(
        "--host-version",
        default="unknown",
        help="output of `codex --version`, e.g. codex-cli 0.163.0",
    )
    parser.add_argument(
        "--file",
        default=None,
        help="saved capture file; omit to read the live stream from stdin",
    )
    parser.add_argument(
        "--segment-id",
        default=None,
        help="capture segment name; defaults to the file name or 'stdin'",
    )
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

    if args.file is not None:
        try:
            lines = Path(args.file).read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            print(json.dumps({"error": f"capture file unreadable: {exc}"}))
            return 2
        segment_id = args.segment_id or Path(args.file).name
    else:
        lines = sys.stdin.read().splitlines()
        segment_id = args.segment_id or "stdin"
    try:
        with EventStore.open(
            Path(args.runtime_home), confirmed=args.confirmed
        ) as store:
            receipt = ingest_exec_stream(
                store,
                lines,
                installation_id=args.installation_id,
                device_id=args.device_id,
                segment_id=segment_id,
                host_version=args.host_version,
            )
    except StoreError as exc:
        print(json.dumps({"error": exc.reason}, ensure_ascii=False))
        return 2
    print(json.dumps(receipt.as_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
