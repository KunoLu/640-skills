"""R1.4 acceptance closeout: security, audit-boundary, and version-compat pins.

Scenario text lives in spec/r1.4-acceptance-scenarios.md. This repository
does not create .feature files. This suite locks the already-merged R1
surface — it adds no product API. ACs with existing coverage are mapped in
the scenarios doc and the acceptance report instead of being duplicated
here.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import csv_export
import stats_query
from event_store import EventStore, StoreError

CONTRACTS = ROOT / "contracts"
OPENAPI = CONTRACTS / "openapi.yaml"
EVENT_SCHEMA = CONTRACTS / "event.schema.json"


def _openapi() -> dict:
    import yaml

    return yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))


def _event(event_id: str, source_event_id: str, **changes: object) -> dict:
    event = {
        "schema_version": "1.0",
        "event_id": event_id,
        "event_type": "task.created",
        "occurred_at": "2026-10-16T00:00:00Z",
        "recorded_at": "2026-10-16T00:00:00Z",
        "ingest_seq": 0,
        "installation_id": "inst_r14",
        "device_id": "device_r14",
        "actor": {
            "actor_id": None,
            "kind": "agent",
            "identity_assurance": "unbound",
        },
        "scope": {
            "tenant_id": None,
            "workspace_id": None,
            "project_id": "project_a",
            "repository_id": "repo_a",
            "worktree_id": "wt_a",
            "task_uid": "task_leaf",
            "logical_task_id": "demo/leaf",
            "task_run_id": None,
        },
        "provenance": {
            "source_kind": "runtime-instrumented",
            "source_id": "source_runtime",
            "source_event_id": source_event_id,
            "producer_version": "0.1.0",
            "observation_level": "execution-observed",
            "evidence_status": "present",
            "parser_version": "parser-1",
        },
        "privacy": {
            "classification": "local-metadata",
            "redaction_policy_version": "1",
            "exportable": True,
        },
        "external_refs": [],
        "extensions": {},
    }
    event.update(changes)
    return event


def _enable_observation(home: Path) -> None:
    home.mkdir(mode=0o700, exist_ok=True)
    os.chmod(home, 0o700)
    (home / "config.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "observation": {
                    "enabled": True,
                    "level": "metadata",
                    "failure_policy": "best-effort",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _valid_scope(**changes: object) -> dict:
    catalog = stats_query.serve_catalog()
    scope: dict = {
        "schema_version": "1.0",
        "range": {
            "from": "2026-10-01T00:00:00Z",
            "to": "2026-10-02T00:00:00Z",
            "timezone": "UTC",
        },
        "metrics": [catalog["metrics"][0]["metric_id"]],
    }
    scope.update(changes)
    return scope


class VersionPinTests(unittest.TestCase):
    """The three version pins evolve independently and must not regress."""

    def test_event_schema_is_pinned_at_1_0(self) -> None:
        schema = json.loads(EVENT_SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(schema["$id"], "urn:sbtd:runtime:event:1.0")
        self.assertEqual(schema["properties"]["schema_version"], {"const": "1.0"})
        self.assertIn("schema_version", schema["required"])

    def test_query_scope_library_version_is_1_0(self) -> None:
        self.assertEqual(stats_query.SCHEMA_VERSION, "1.0")


class CsvContractPinTests(unittest.TestCase):
    """#137 contract: export_schema_version 1.1, reasoning_tokens last."""

    def test_csv_schema_version_is_1_1(self) -> None:
        self.assertEqual(csv_export.CSV_SCHEMA_VERSION, "1.1")

    def test_reasoning_tokens_is_the_last_fixed_column(self) -> None:
        self.assertEqual(csv_export.COLUMNS[-1], "reasoning_tokens")
        self.assertEqual(csv_export.COLUMNS[0], "export_schema_version")

    def test_openapi_csv_contract_matches_the_library(self) -> None:
        doc = _openapi()
        download = doc["paths"]["/api/v1/exports/{export_id}/file"]["get"]
        response = download["responses"]["200"]
        self.assertEqual(response["x-sbtd-csv-schema-version"], "1.1")
        self.assertEqual(response["x-sbtd-csv-columns"], csv_export.COLUMNS)
        note = response["x-sbtd-csv-column-notes"]["reasoning_tokens"]
        self.assertIn("output_tokens", note)
        self.assertIn("never 0", note)


class QueryScopeVersionTests(unittest.TestCase):
    """Unknown schema versions are rejected honestly, never downgraded."""

    def test_future_schema_version_is_rejected_honestly(self) -> None:
        scope = _valid_scope(schema_version="2.0")
        with self.assertRaises(stats_query.QueryScopeError) as caught:
            stats_query.normalize_scope(scope)
        self.assertIn("schema_version", str(caught.exception))

    def test_older_schema_version_is_rejected(self) -> None:
        scope = _valid_scope(schema_version="0.9")
        with self.assertRaises(stats_query.QueryScopeError):
            stats_query.normalize_scope(scope)

    def test_current_schema_version_is_accepted(self) -> None:
        normalized = stats_query.normalize_scope(_valid_scope())
        self.assertEqual(normalized["schema_version"], "1.0")


class OpenApiPinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.doc = _openapi()

    def test_query_scope_const_matches_library(self) -> None:
        schema = self.doc["components"]["schemas"]["QueryScope"]
        self.assertEqual(schema["properties"]["schema_version"]["const"], "1.0")
        self.assertEqual(schema["additionalProperties"], False)

    def test_exports_stay_rc2_and_not_rc1_blocking(self) -> None:
        operations = [
            self.doc["paths"]["/api/v1/exports"]["post"],
            self.doc["paths"]["/api/v1/exports/{export_id}"]["get"],
            self.doc["paths"]["/api/v1/exports/{export_id}"]["delete"],
            self.doc["paths"]["/api/v1/exports/{export_id}/file"]["get"],
        ]
        for operation in operations:
            self.assertEqual(operation["x-sbtd-release"], "v2.1.0-rc.2")
            self.assertEqual(operation["x-sbtd-rc1-blocking"], False)

    def test_no_remote_business_control_operations(self) -> None:
        reserved = {
            "tasks:write",
            "validation:run",
            "migration:apply",
            "remote-command:execute",
        }
        for path, methods in self.doc["paths"].items():
            for method, operation in methods.items():
                scopes = set(operation.get("x-sbtd-scopes") or [])
                self.assertFalse(
                    scopes & reserved, f"{method.upper()} {path} holds a reserved scope"
                )
        self.assertEqual(self.doc["info"]["x-sbtd-implementation"], "contract-only")

    def test_info_summary_states_r1_4_acceptance(self) -> None:
        self.assertIn("R1.4", self.doc["info"]["summary"])


class AuditBoundaryTests(unittest.TestCase):
    """Thin acceptance smoke over the existing EventStore surface."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="sbtd-r14-")
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "runtime-home"

    def test_observation_off_creates_no_audit_files(self) -> None:
        # Scenario: 观察开关关闭不产生审计库
        self.home.mkdir(mode=0o700)
        (self.home / "config.json").write_text(
            json.dumps({"schema_version": 1, "observation": {"enabled": False}}) + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(StoreError):
            EventStore.open(self.home, confirmed=True)
        self.assertFalse((self.home / "audit.db").exists())
        self.assertFalse((self.home / "spool").exists())

    def test_read_only_open_never_creates_a_store(self) -> None:
        # Scenario: 完全只读调用不落任何文件
        _enable_observation(self.home)
        with self.assertRaises(StoreError):
            EventStore.open(self.home, read_only=True)
        self.assertFalse((self.home / "audit.db").exists())
        self.assertFalse((self.home / "spool").exists())


class DedupConflictTests(unittest.TestCase):
    """AC-06/AC-07 acceptance over the existing dedup contract."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="sbtd-r14-")
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "runtime-home"
        _enable_observation(self.home)
        self.store = EventStore.open(self.home, confirmed=True)
        self.addCleanup(self.store.close)

    def test_same_key_same_content_only_confirms(self) -> None:
        # Scenario: 同来源键同内容只确认
        event = _event("evt_a", "src-1")
        first = self.store.append([event])
        second = self.store.append([dict(event)])
        self.assertEqual([outcome.status for outcome in first.outcomes], ["accepted"])
        self.assertEqual([outcome.status for outcome in second.outcomes], ["duplicate"])
        self.assertEqual(len(self.store.replay()), 1)

    def test_conflicting_content_keeps_the_first_event(self) -> None:
        # Scenario: 同来源键内容冲突保留先接受者
        original = _event("evt_a", "src-1", occurred_at="2026-10-16T00:00:00Z")
        changed = _event("evt_b", "src-1", occurred_at="2026-10-16T01:00:00Z")
        self.store.append([original])
        conflict = self.store.append([changed])
        self.assertEqual(
            [outcome.status for outcome in conflict.outcomes], ["conflict"]
        )
        replayed = self.store.replay()
        self.assertEqual(len(replayed), 1)
        self.assertEqual(replayed[0]["event_id"], "evt_a")
        self.assertEqual(replayed[0]["occurred_at"], "2026-10-16T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
