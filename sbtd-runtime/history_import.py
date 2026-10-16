"""R1.2c task-history and verification-artifact import.

Imports already-recorded facts into the R1.2a event store:

- task.md status tables, parsed by the existing TaskDocument parser;
- validation-evidence v2 envelopes, checked by the existing
  validate_validation_evidence validator and its junit/playwright parsers.

Import runs only from a caller-approved scan plan. build_scan_plan is
read-only: it records the explicitly named project root and relative source
paths, refuses escapes and symlinks, and never lists directories, reads file
contents, or opens the event store. approve_scan_plan is the separate
approval act. An unapproved plan cannot append events.

The importer never rewrites task.md, never scans HOME or sibling projects,
and never fabricates history:

- a row whose `at` is unknown or not schema-provable keeps occurred_at null;
  recorded_at only states when this import observed the file;
- frontmatter created_at alone produces no task.created event;
- an HTML report title is never a pass; validation.result is passed only
  when validate_v2 accepts the envelope, the e2eMode maps directly to the
  event-schema scope enum, and the parsed native cases hold at least one
  passed and no failed;
- task_uid stays null unless the caller passes a mapping; the current
  frontmatter mode is not written back onto historical rows.

Events use source_kind artifact-imported. Reports are related through the
existing validation / external_refs / correlation blocks; the event schema
has no artifact object, so none is invented. Extension values stay scalar.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
_SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from event_store import EventStore, StoreError
from host_adapter import (
    IngestReceipt,
    ParseOutcome,
    base_event,
    ingest_events,
    utc_now,
)
from sbtd_project import TaskDataError
from sbtd_task_document import TaskDocument

PARSER_VERSION = "history-import-1"
SOURCE_ID = "history-import"
_KINDS = ("task-history", "verification-envelope")
_OCCURRED_AT = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
_E2E_SCOPES = ("narrow", "full-stack", "contract-backed")
_VALIDATOR_PATH = (
    _SCRIPTS.parent
    / "templates"
    / "skills"
    / "project-validation"
    / "scripts"
    / "validate_validation_evidence.py"
)
_VALIDATOR = None


class HistoryImportError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class ImportSource:
    kind: str
    path: str


@dataclass(frozen=True)
class ScanPlan:
    project_root: str
    sources: tuple[ImportSource, ...]
    approved: bool = False


def _checked_root(project_root: Path | str) -> Path:
    root = Path(project_root).resolve()
    if not root.is_dir():
        raise HistoryImportError("project root is not a directory")
    if Path(project_root).is_symlink():
        raise HistoryImportError("project root symlink is refused")
    return root


def _checked_source(root: Path, source: ImportSource) -> Path:
    if source.kind not in _KINDS:
        raise HistoryImportError(f"unknown source kind {source.kind!r}")
    relative = source.path
    if not relative or relative.startswith("/") or "\\" in relative:
        raise HistoryImportError(f"source path is not project-relative: {relative!r}")
    parts = relative.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise HistoryImportError(f"source path escapes the project root: {relative!r}")
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise HistoryImportError(f"source path symlink is refused: {relative!r}")
    resolved = current.resolve()
    if root not in resolved.parents and resolved != root:
        raise HistoryImportError(f"source path escapes the project root: {relative!r}")
    return resolved


def build_scan_plan(project_root: Path | str, sources: list[ImportSource]) -> ScanPlan:
    """Record the caller-named scope. Read-only; never approved by itself."""
    root = _checked_root(project_root)
    checked = tuple(
        ImportSource(source.kind, source.path)
        for source in sources
        if _checked_source(root, source) is not None
    )
    return ScanPlan(str(root), checked)


def approve_scan_plan(plan: ScanPlan) -> ScanPlan:
    """The separate, explicit approval act. Still touches nothing on disk."""
    return replace(plan, approved=True)


def _fit(value: Any, limit: int = 128) -> str | None:
    if isinstance(value, str) and 1 <= len(value) <= limit:
        return value
    return None


def _source_ref(relative: str, row: int) -> tuple[str | None, str, int]:
    readable = f"{relative}#{row}"
    if len(readable) <= 128:
        return readable, relative, row
    digest = hashlib.sha256(relative.encode("utf-8")).hexdigest()[:32]
    return digest + f"#{row}", digest, row


def _row_occurred(value: Any) -> str | None:
    if isinstance(value, str) and value != "unknown" and _OCCURRED_AT.match(value):
        return value
    return None


def _parse_task(
    target: Path,
    relative: str,
    *,
    installation_id: str,
    device_id: str,
    project_id: str | None,
    recorded_at: str,
) -> list[dict[str, Any]]:
    try:
        raw = target.read_bytes()
    except OSError:
        return []
    try:
        document = TaskDocument.parse(raw.decode("utf-8"))
    except (TaskDataError, UnicodeDecodeError, ValueError):
        return []
    logical_id = _fit(document.frontmatter.get("id"))
    events: list[dict[str, Any]] = []
    for index, row in enumerate(document.events):
        source_event_id, segment_id, offset = _source_ref(relative, index)
        events.append(
            base_event(
                event_type=(
                    "task.reopened"
                    if row["from"] == "done" and row["to"] == "planned"
                    else "task.state_changed"
                ),
                occurred_at=_row_occurred(row.get("at")),
                recorded_at=recorded_at,
                installation_id=installation_id,
                device_id=device_id,
                source_id=SOURCE_ID,
                source_event_id=source_event_id,
                parser_version=PARSER_VERSION,
                segment_id=segment_id,
                offset=offset,
                observation_level="declared",
                source_kind="artifact-imported",
                evidence_status="present",
                actor_kind="unknown",
                logical_task_id=logical_id,
                project_id=project_id,
                state={"previous": row["from"], "current": row["to"]},
                workflow={"mode_at_event": "unknown", "mode_source": None},
                external_refs=[
                    {
                        "system": "task-md",
                        "object_type": "state-event",
                        "external_id": f"{relative}#{index}"[:128],
                        "mapping_version": 1,
                    }
                ],
            )
        )
    return events


def _validator():
    global _VALIDATOR
    if _VALIDATOR is None:
        spec = importlib.util.spec_from_file_location(
            "sbtd_validate_validation_evidence", _VALIDATOR_PATH
        )
        if spec is None or spec.loader is None:
            raise HistoryImportError("validation evidence validator is unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _VALIDATOR = module
    return _VALIDATOR


def _outcome(value: Any) -> str:
    if value == "passed":
        return "passed"
    if value in ("failed", "timedOut", "interrupted", "error"):
        return "failed"
    return "unknown"


def _case_id(text: str) -> str | None:
    if 1 <= len(text) <= 128:
        return text
    if len(text) > 128:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    return None


def _report_cases(validator: Any, root: Path, report: dict[str, Any]) -> list[str]:
    path = report.get("path")
    report_format = report.get("reportFormat")
    if report_format not in ("junit-xml-v1", "playwright-json-v1"):
        return []
    if not isinstance(path, str):
        return []
    try:
        target = _checked_source(root, ImportSource("verification-envelope", path))
        data = target.read_bytes()
        parsed = (
            validator.parse_junit(data)
            if report_format == "junit-xml-v1"
            else validator.parse_playwright(data)
        )
    except Exception:
        return []
    cases: list[str] = []
    for index, case in enumerate(parsed):
        if report_format == "junit-xml-v1":
            text = "/".join(
                [
                    *case.get("suites", []),
                    case.get("classname", ""),
                    case.get("name", ""),
                ]
            )
        else:
            text = "/".join(
                [
                    case.get("project", ""),
                    case.get("file", ""),
                    *case.get("titlePath", []),
                ]
            )
        case_id = _case_id(text or f"case-{index}")
        if case_id is None:
            continue
        cases.append((case_id, _outcome(case.get("outcome"))))
    return cases


def _parse_verification(
    target: Path,
    relative: str,
    *,
    installation_id: str,
    device_id: str,
    project_id: str | None,
    recorded_at: str,
    root: Path,
) -> list[dict[str, Any]]:
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        # HTML or unreadable content is not an envelope; the title is not a result.
        return []
    if not isinstance(payload, dict):
        return []
    validator = _validator()
    try:
        validator.validate_v2(payload, root)
        accepted = True
    except Exception:
        accepted = False
    occurred_at = _row_occurred(payload.get("createdAt"))
    run_id = _fit(payload.get("runId"))
    scope = payload.get("e2eMode")
    mapped_scope = scope if scope in _E2E_SCOPES else None
    reports = [item for item in payload.get("reports") or [] if isinstance(item, dict)]
    cases: list[tuple[str, str]] = []
    refs: list[dict[str, Any]] = []
    formats: set[str] = set()
    if accepted:
        for report in reports:
            report_format = report.get("reportFormat")
            if isinstance(report_format, str):
                formats.add(report_format)
            cases.extend(_report_cases(validator, root, report))
            sha = report.get("sha256")
            if isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{64}", sha.lower()):
                refs.append(
                    {
                        "system": "validation-evidence",
                        "object_type": "report",
                        "external_id": sha.lower(),
                        "mapping_version": 1,
                    }
                )
    extensions: dict[str, Any] = {"case_count": len(cases)}
    if isinstance(scope, str) and scope:
        extensions["e2e_mode"] = scope[:256]
    correlation = {"operation_id": run_id} if run_id is not None else None
    common: dict[str, Any] = {
        "occurred_at": occurred_at,
        "recorded_at": recorded_at,
        "installation_id": installation_id,
        "device_id": device_id,
        "source_id": SOURCE_ID,
        "source_event_id": _fit(f"envelope:{run_id or relative}"),
        "parser_version": PARSER_VERSION,
        "segment_id": relative[:128],
        "offset": 0,
        "source_kind": "artifact-imported",
        "actor_kind": "unknown",
        "project_id": project_id,
        "external_refs": refs,
        "extensions": extensions,
    }
    if correlation is not None:
        common["correlation"] = correlation
    if mapped_scope is None:
        # The required e2e_scope cannot be proven; do not invent one and do
        # not carry a result. The validator verdict stays visible.
        return [
            base_event(
                event_type="artifact.registered",
                observation_level="artifact-verified" if accepted else "declared",
                evidence_status="validated" if accepted else "invalid",
                state={"previous": None, "current": "unknown"},
                **common,
            )
        ]
    if not accepted:
        return [
            base_event(
                event_type="validation.finished",
                observation_level="declared",
                evidence_status="invalid",
                validation={
                    "validation_id": run_id or "unidentified",
                    "e2e_scope": mapped_scope,
                    "result": "unknown",
                },
                **common,
            )
        ]
    results = {result for _case_id_text, result in cases}
    if "failed" in results:
        result = "failed"
    elif "passed" in results:
        result = "passed"
    else:
        result = "unknown"
    runner = next(iter(formats), "validation-evidence")
    if len(formats) > 1:
        runner = "mixed"
    return [
        base_event(
            event_type="validation.finished",
            observation_level="artifact-verified",
            evidence_status="validated",
            component={
                "component_id": f"runner:{runner}"[:128],
                "kind": "test-runner",
                "name": runner[:128],
            },
            validation={
                "validation_id": run_id or "unidentified",
                "e2e_scope": mapped_scope,
                "result": result,
                "cases": [
                    {"case_id": case_id, "attempt_no": 1, "result": outcome}
                    for case_id, outcome in cases
                ],
            },
            **common,
        )
    ]


def import_plan(
    store: EventStore,
    plan: ScanPlan,
    *,
    installation_id: str,
    device_id: str,
    project_id: str | None = None,
) -> IngestReceipt:
    """Import one approved plan. Unapproved plans never reach the store."""
    if not plan.approved:
        raise HistoryImportError("scan plan is not approved")
    root = _checked_root(plan.project_root)
    caller_project = _fit(project_id)
    recorded_at = utc_now()
    events: list[dict[str, Any]] = []
    read = 0
    skipped = 0
    for source in plan.sources:
        target = _checked_source(root, source)
        read += 1
        relative = source.path
        if not target.is_file():
            skipped += 1
            continue
        produced = (
            _parse_task(
                target,
                relative,
                installation_id=installation_id,
                device_id=device_id,
                project_id=caller_project,
                recorded_at=recorded_at,
            )
            if source.kind == "task-history"
            else _parse_verification(
                target,
                relative,
                installation_id=installation_id,
                device_id=device_id,
                project_id=caller_project,
                recorded_at=recorded_at,
                root=root,
            )
        )
        if produced:
            events.extend(produced)
        else:
            skipped += 1
    return ingest_events(
        store,
        ParseOutcome(events=tuple(events), records_read=read, records_skipped=skipped),
        source_id=SOURCE_ID,
        host_kind="import",
        parser_version=PARSER_VERSION,
    )


def ingest_approved(
    runtime_home: Path | str,
    plan: ScanPlan,
    *,
    confirmed: bool = False,
    installation_id: str,
    device_id: str,
    project_id: str | None = None,
) -> IngestReceipt:
    """Open the store (honoring the observation switch) and import."""
    with EventStore.open(Path(runtime_home), confirmed=confirmed) as store:
        return import_plan(
            store,
            plan,
            installation_id=installation_id,
            device_id=device_id,
            project_id=project_id,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import task history and verification artifacts "
        "from an explicitly approved scope into the R1.2a event store."
    )
    parser.add_argument("--runtime-home", required=True, help="SBTD_RUNTIME_HOME")
    parser.add_argument("--installation-id", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--project-id", default=None)
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        metavar="KIND=PATH",
        help="named source; kind is task-history or verification-envelope, "
        "path is project-relative",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="approve the printed scope; without it nothing is written",
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
    sources: list[ImportSource] = []
    for item in args.source:
        kind, separator, path = item.partition("=")
        if not separator:
            print(json.dumps({"error": f"source must be KIND=PATH: {item}"}))
            return 2
        sources.append(ImportSource(kind, path))
    try:
        plan = build_scan_plan(args.project_root, sources)
    except HistoryImportError as exc:
        print(json.dumps({"error": exc.reason}, ensure_ascii=False))
        return 2
    if not args.approve:
        print(
            json.dumps(
                {
                    "project_root": plan.project_root,
                    "approved": plan.approved,
                    "sources": [
                        {"kind": source.kind, "path": source.path}
                        for source in plan.sources
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    try:
        receipt = ingest_approved(
            args.runtime_home,
            approve_scan_plan(plan),
            confirmed=args.confirmed,
            installation_id=args.installation_id,
            device_id=args.device_id,
            project_id=args.project_id,
        )
    except (HistoryImportError, StoreError) as exc:
        print(json.dumps({"error": exc.reason}, ensure_ascii=False))
        return 2
    print(json.dumps(receipt.as_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
