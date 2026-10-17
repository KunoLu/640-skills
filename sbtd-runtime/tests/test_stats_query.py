"""R1.3 statistics query: QueryScope normalize, catalog, query, timeseries.

Scenario text lives in spec/r1.3-stats-api-scenarios.md. This repository
does not create .feature files. Metric semantics come from
contract_eval.evaluate; this package never recomputes denominators.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contract_eval import civil_window_seconds, metric_catalog
from stats_query import (
    QueryScopeError,
    normalize_scope,
    query,
    serve_catalog,
    timeseries,
)

GOLDEN = ROOT / "golden"


def _dataset() -> dict:
    return json.loads((GOLDEN / "dataset.json").read_text(encoding="utf-8"))


def _expected() -> dict:
    return json.loads((GOLDEN / "expected.json").read_text(encoding="utf-8"))


def _scope(dataset: dict, **changes: object) -> dict:
    base = dataset["query_scope"]
    scope = {
        "schema_version": "1.0",
        "range": {
            "from": base["from"],
            "to": base["to"],
            "timezone": base["timezone"],
        },
        "filters": {},
        "task_granularity": base["task_granularity"],
        "include_unlinked": base["include_unlinked"],
        "include_unknown_time": base["include_unknown_time"],
        "metrics": [item["metric_id"] for item in metric_catalog()["metrics"]],
    }
    for key, value in changes.items():
        scope[key] = value
    return scope


class CatalogTests(unittest.TestCase):
    def test_catalog_serves_every_metric_with_support_boundary(self) -> None:
        payload = serve_catalog()
        ids = {item["metric_id"] for item in payload["metrics"]}
        expected_ids = {item["metric_id"] for item in metric_catalog()["metrics"]}
        self.assertEqual(ids, expected_ids)
        self.assertEqual(
            payload["metrics_version"], metric_catalog()["metrics_version"]
        )
        unsupported = [
            item for item in payload["metrics"] if item["support"] == "unsupported"
        ]
        self.assertTrue(unsupported)


class NormalizeScopeTests(unittest.TestCase):
    def test_unknown_metric_is_rejected_with_the_field_named(self) -> None:
        scope = _scope(_dataset(), metrics=["tasks.touched", "bogus.metric"])
        with self.assertRaises(QueryScopeError) as caught:
            normalize_scope(scope)
        self.assertIn("metrics", str(caught.exception))
        self.assertIn("bogus.metric", str(caught.exception))

    def test_empty_range_is_rejected_without_a_default(self) -> None:
        dataset = _dataset()
        scope = _scope(dataset)
        scope["range"]["to"] = scope["range"]["from"]
        with self.assertRaises(QueryScopeError):
            normalize_scope(scope)

    def test_bad_timezone_is_rejected(self) -> None:
        scope = _scope(_dataset())
        scope["range"]["timezone"] = "Not/AZone"
        with self.assertRaises(QueryScopeError) as caught:
            normalize_scope(scope)
        self.assertIn("timezone", str(caught.exception))

    def test_missing_schema_version_is_rejected(self) -> None:
        scope = _scope(_dataset())
        del scope["schema_version"]
        with self.assertRaises(QueryScopeError):
            normalize_scope(scope)

    def test_naive_timestamp_is_rejected(self) -> None:
        scope = _scope(_dataset())
        scope["range"]["from"] = "2026-10-15T15:00:00"
        with self.assertRaises(QueryScopeError):
            normalize_scope(scope)


class QueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset = _dataset()
        self.expected = _expected()

    def test_golden_metric_values_match_expected(self) -> None:
        result = query(self.dataset, _scope(self.dataset))
        for metric_id, want in self.expected["metrics"].items():
            got = result["metrics"][metric_id]
            self.assertEqual(got["support"], want["support"], metric_id)
            self.assertEqual(got["value"], want["value"], metric_id)
            if "numerator" in want:
                self.assertEqual(got["numerator"], want["numerator"], metric_id)
                self.assertEqual(got["denominator"], want["denominator"], metric_id)

    def test_requested_metric_subset_is_returned(self) -> None:
        scope = _scope(self.dataset, metrics=["tasks.touched", "tasks.created"])
        result = query(self.dataset, scope)
        self.assertEqual(sorted(result["metrics"]), ["tasks.created", "tasks.touched"])

    def test_tokyo_and_utc_spellings_of_one_window_agree(self) -> None:
        utc_scope = _scope(self.dataset)
        tokyo_scope = _scope(self.dataset)
        tokyo_scope["range"] = {
            "from": "2026-10-16T00:00:00+09:00",
            "to": "2026-10-17T00:00:00+09:00",
            "timezone": "Asia/Tokyo",
        }
        utc = query(self.dataset, utc_scope)["metrics"]
        tokyo = query(self.dataset, tokyo_scope)["metrics"]
        self.assertEqual(
            json.dumps(utc, sort_keys=True), json.dumps(tokyo, sort_keys=True)
        )

    def test_event_at_to_is_out_of_the_window(self) -> None:
        # evt_run_leaf_1_start occurs at 2026-10-15T15:30:00Z.
        scope = _scope(self.dataset, metrics=["runs.started"])
        scope["range"]["to"] = "2026-10-15T15:30:00Z"
        result = query(self.dataset, scope)
        self.assertEqual(result["metrics"]["runs.started"]["value"], 0)
        scope["range"]["to"] = "2026-10-15T15:30:01Z"
        result = query(self.dataset, scope)
        self.assertEqual(result["metrics"]["runs.started"]["value"], 1)

    def test_event_at_from_is_in_the_window(self) -> None:
        # evt_created_leaf occurs at 2026-10-15T15:00:00Z.
        scope = _scope(self.dataset, metrics=["tasks.created"])
        scope["range"]["from"] = "2026-10-15T15:00:00Z"
        scope["range"]["to"] = "2026-10-15T15:00:01Z"
        result = query(self.dataset, scope)
        self.assertEqual(result["metrics"]["tasks.created"]["value"], 1)
        scope["range"]["from"] = "2026-10-15T15:00:01Z"
        scope["range"]["to"] = "2026-10-15T15:00:02Z"
        result = query(self.dataset, scope)
        self.assertEqual(result["metrics"]["tasks.created"]["value"], 0)

    def test_zero_decidable_samples_are_not_one_hundred_percent(self) -> None:
        scope = _scope(self.dataset, metrics=["steps.success_rate_observed"])
        scope["range"]["to"] = "2026-10-15T15:00:01Z"
        result = query(self.dataset, scope)
        metric = result["metrics"]["steps.success_rate_observed"]
        self.assertIsNone(metric["value"])
        self.assertEqual(metric["sample_status"], "no-decidable-sample")
        self.assertEqual(metric["numerator"], 0)
        self.assertEqual(metric["denominator"], 0)

    def test_missing_tokens_stay_null_not_zero(self) -> None:
        scope = _scope(self.dataset, metrics=["usage.tokens"])
        result = query(self.dataset, scope)
        value = result["metrics"]["usage.tokens"]["value"]
        self.assertEqual(value["input_tokens"], 10)
        self.assertIsNone(value["cache_read_tokens"])
        self.assertIsNone(value["reasoning_tokens"])

    def test_project_filter_narrows_the_population(self) -> None:
        scope = _scope(self.dataset, metrics=["tasks.touched"])
        scope["filters"] = {"project_ids": ["project_b"]}
        result = query(self.dataset, scope)
        self.assertEqual(result["metrics"]["tasks.touched"]["value"], 0)
        scope["filters"] = {"project_ids": ["project_a"]}
        result = query(self.dataset, scope)
        self.assertEqual(result["metrics"]["tasks.touched"]["value"], 2)

    def test_host_filter_narrows_invocations(self) -> None:
        scope = _scope(self.dataset, metrics=["components.invocations"])
        scope["filters"] = {"host_kinds": ["omp"]}
        result = query(self.dataset, scope)
        got = result["metrics"]["components.invocations"]
        self.assertEqual(got["value"], 1)
        self.assertEqual(got["invocation_ids"], ["inv_2"])

    def test_unknown_filter_key_is_rejected(self) -> None:
        scope = _scope(self.dataset)
        scope["filters"] = {"sql": ["drop table"]}
        with self.assertRaises(QueryScopeError):
            query(self.dataset, scope)

    def test_unsupported_metrics_stay_unsupported_not_zero(self) -> None:
        scope = _scope(self.dataset, metrics=["duration.execution_ms"])
        result = query(self.dataset, scope)
        metric = result["metrics"]["duration.execution_ms"]
        self.assertEqual(metric["support"], "unsupported")
        self.assertIsNone(metric["value"])


class TimeseriesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset = _dataset()

    def test_buckets_cover_the_window_without_overlap(self) -> None:
        scope = _scope(self.dataset, metrics=["tasks.created"])
        result = timeseries(self.dataset, scope, bucket_seconds=43200)
        buckets = result["buckets"]
        self.assertEqual(len(buckets), 2)
        self.assertEqual(buckets[0]["bucket_start"], "2026-10-15T15:00:00Z")
        self.assertEqual(buckets[0]["bucket_end"], "2026-10-16T03:00:00Z")
        self.assertEqual(buckets[1]["bucket_start"], buckets[0]["bucket_end"])
        self.assertEqual(buckets[1]["bucket_end"], "2026-10-16T15:00:00Z")
        total = sum(bucket["metrics"]["tasks.created"]["value"] for bucket in buckets)
        self.assertEqual(total, 2)

    def test_event_at_to_lands_in_no_bucket(self) -> None:
        dataset = copy.deepcopy(self.dataset)
        event = copy.deepcopy(dataset["events"][0])
        event["event_id"] = "evt_at_to"
        event["occurred_at"] = dataset["query_scope"]["to"]
        event["provenance"]["source_event_id"] = "evt_at_to"
        dataset["events"].append(event)
        scope = _scope(dataset, metrics=["tasks.created"])
        result = timeseries(dataset, scope, bucket_seconds=43200)
        total = sum(
            bucket["metrics"]["tasks.created"]["value"] for bucket in result["buckets"]
        )
        self.assertEqual(total, 2)

    def test_dst_civil_day_is_twenty_five_hours(self) -> None:
        fixture = self.dataset["dst_fixture"]
        seconds = civil_window_seconds(
            fixture["timezone"], fixture["from_civil"], fixture["to_civil"]
        )
        self.assertEqual(seconds, 25 * 3600)
        scope = _scope(self.dataset, metrics=["tasks.touched"])
        scope["range"] = {
            "from": "2026-11-01T00:00:00-04:00",
            "to": "2026-11-02T00:00:00-05:00",
            "timezone": fixture["timezone"],
        }
        result = timeseries(self.dataset, scope, bucket_seconds=3600)
        self.assertEqual(len(result["buckets"]), 25)

    def test_empty_bucket_rate_is_no_decidable_sample(self) -> None:
        scope = _scope(self.dataset, metrics=["steps.success_rate_observed"])
        result = timeseries(self.dataset, scope, bucket_seconds=3600)
        empty = [
            bucket
            for bucket in result["buckets"]
            if bucket["metrics"]["steps.success_rate_observed"]["denominator"] == 0
        ]
        self.assertTrue(empty)
        for bucket in empty:
            metric = bucket["metrics"]["steps.success_rate_observed"]
            self.assertIsNone(metric["value"])
            self.assertEqual(metric["sample_status"], "no-decidable-sample")

    def test_zero_bucket_seconds_is_rejected_not_defaulted(self) -> None:
        scope = _scope(self.dataset, metrics=["tasks.created"])
        with self.assertRaises(QueryScopeError) as caught:
            timeseries(self.dataset, scope, bucket_seconds=0)
        self.assertIn("bucket_seconds", str(caught.exception))

    def test_group_by_is_rejected_not_silently_ignored(self) -> None:
        scope = _scope(self.dataset, metrics=["tasks.touched"])
        scope["group_by"] = ["component_id"]
        with self.assertRaises(QueryScopeError) as caught:
            query(self.dataset, scope)
        self.assertIn("group_by", str(caught.exception))

    def test_timeseries_meta_matches_query_coverage(self) -> None:
        scope = _scope(self.dataset, metrics=["tasks.created"])
        series = timeseries(self.dataset, scope, bucket_seconds=43200)
        # The golden set holds evt_created_untimed with occurred_at null.
        self.assertIs(series["meta"]["complete"], False)
        self.assertEqual(series["meta"]["coverage_state"], "partial")
        self.assertIn("UNKNOWN_OCCURRED_AT", series["meta"]["warnings"])


if __name__ == "__main__":
    unittest.main()
