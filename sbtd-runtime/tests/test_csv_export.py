"""R1.3 CSV export: fixed columns, BOM, record families, escaping, no truncation.

Scenario text lives in spec/r1.3-stats-api-scenarios.md. The serializer walks
the full snapshot dataset; page limits never truncate the file.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from csv_export import (
    COLUMNS,
    CSV_ESCAPE_VERSION,
    CSV_SCHEMA_VERSION,
    RECORD_TYPES,
    serialize_csv,
)
from report_snapshot import SnapshotStore
from stats_query import query

GOLDEN = ROOT / "golden"
BOM = b"\xef\xbb\xbf"


def _dataset() -> dict:
    return json.loads((GOLDEN / "dataset.json").read_text(encoding="utf-8"))


def _scope(dataset: dict, metrics: list[str]) -> dict:
    base = dataset["query_scope"]
    return {
        "schema_version": "1.0",
        "range": {"from": base["from"], "to": base["to"], "timezone": base["timezone"]},
        "filters": {},
        "task_granularity": base["task_granularity"],
        "include_unlinked": base["include_unlinked"],
        "include_unknown_time": base["include_unknown_time"],
        "metrics": metrics,
    }


def _rows(payload: bytes) -> list[dict]:
    text = payload.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


class CsvExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset = _dataset()
        self.store = SnapshotStore()
        self.scope = _scope(
            self.dataset, ["tasks.touched", "steps.success_rate_observed"]
        )
        self.snapshot = self.store.create_or_reuse(self.dataset, self.scope)

    def test_bom_and_fixed_header(self) -> None:
        payload = serialize_csv(self.snapshot)
        self.assertTrue(payload.startswith(BOM))
        header = payload.decode("utf-8-sig").splitlines()[0]
        self.assertEqual(header.split(","), COLUMNS)

    def test_record_types_stay_in_the_prd_families(self) -> None:
        rows = _rows(serialize_csv(self.snapshot))
        self.assertTrue(rows)
        for row in rows:
            self.assertIn(row["record_type"], RECORD_TYPES)

    def test_csv_covers_the_full_dataset_regardless_of_page_size(self) -> None:
        payload = serialize_csv(self.snapshot)
        rows = _rows(payload)
        detail = [
            row for row in rows if row["record_type"] not in {"metadata", "metric"}
        ]
        manifest = {
            item["record_type"]: item["rows"] for item in self.snapshot.dataset_manifest
        }
        by_type: dict[str, int] = {}
        for row in detail:
            by_type[row["record_type"]] = by_type.get(row["record_type"], 0) + 1
        self.assertEqual(by_type, {k: v for k, v in manifest.items() if v})
        keys = [(row["record_type"], row["record_id"]) for row in detail]
        self.assertEqual(len(keys), len(set(keys)))

    def test_metadata_records_family_counts_and_scope(self) -> None:
        rows = _rows(serialize_csv(self.snapshot))
        metadata = [row for row in rows if row["record_type"] == "metadata"]
        pairs = {row["metadata_key"]: row["metadata_value"] for row in metadata}
        manifest = {
            item["record_type"]: item["rows"] for item in self.snapshot.dataset_manifest
        }
        for family, count in manifest.items():
            self.assertEqual(int(pairs[f"rows:{family}"]), count)
        self.assertEqual(pairs["query_hash"], self.snapshot.query_hash)
        self.assertEqual(pairs["escape_version"], CSV_ESCAPE_VERSION)
        head = metadata[0]
        self.assertEqual(head["export_schema_version"], CSV_SCHEMA_VERSION)
        self.assertEqual(head["snapshot_id"], self.snapshot.snapshot_id)
        self.assertEqual(head["range_from"], self.scope["range"]["from"])
        self.assertEqual(head["range_to"], self.scope["range"]["to"])
        self.assertEqual(head["timezone"], "Asia/Tokyo")

    def test_metric_rows_carry_values_and_rates(self) -> None:
        rows = _rows(serialize_csv(self.snapshot))
        metrics = {
            row["metric_id"]: row for row in rows if row["record_type"] == "metric"
        }
        self.assertEqual(metrics["tasks.touched"]["metric_value"], "2")
        rate = metrics["steps.success_rate_observed"]
        self.assertEqual(rate["numerator"], "1")
        self.assertEqual(rate["denominator"], "2")
        self.assertEqual(rate["metric_value"], "1/2")

    def test_null_stays_empty_never_zero(self) -> None:
        rows = _rows(serialize_csv(self.snapshot))
        usage = [row for row in rows if row["record_type"] == "usage"]
        detail = next(row for row in usage if row["record_id"] == "req_1")
        self.assertEqual(detail["input_tokens"], "10")
        self.assertEqual(detail["cache_read_tokens"], "")
        self.assertEqual(detail["cost_reported"], "")

    def test_formula_injection_is_escaped_but_numbers_are_not(self) -> None:
        dataset = json.loads(json.dumps(self.dataset))
        for event in dataset["events"]:
            if event["event_id"] == "evt_created_leaf":
                event["extensions"] = {"actor_alias": "=HYPERLINK(1)"}
        snapshot = self.store.create_or_reuse(
            dataset, _scope(dataset, ["tasks.touched"])
        )
        rows = _rows(serialize_csv(snapshot))
        aliased = [row for row in rows if row["actor_alias"]]
        self.assertTrue(aliased)
        for row in aliased:
            self.assertTrue(row["actor_alias"].startswith("'"))

    def test_csv_matches_query_metrics_of_the_same_snapshot(self) -> None:
        answer = query(self.dataset, self.scope, store=self.store)
        self.assertEqual(answer["snapshot_id"], self.snapshot.snapshot_id)
        rows = _rows(serialize_csv(self.snapshot))
        metrics = {
            row["metric_id"]: row for row in rows if row["record_type"] == "metric"
        }
        self.assertEqual(
            metrics["tasks.touched"]["metric_value"],
            str(answer["metrics"]["tasks.touched"]["value"]),
        )

    def test_structured_metric_value_is_compact_json(self) -> None:
        scope = _scope(self.dataset, ["tests.final_result_distribution"])
        snapshot = self.store.create_or_reuse(self.dataset, scope)
        rows = _rows(serialize_csv(snapshot))
        metric = next(row for row in rows if row["record_type"] == "metric")
        self.assertEqual(json.loads(metric["metric_value"]), {"failed": 1, "passed": 2})


if __name__ == "__main__":
    unittest.main()
