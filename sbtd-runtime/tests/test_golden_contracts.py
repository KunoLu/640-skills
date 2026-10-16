"""Executable R1.0 checks for nouns, denominators, and dedup.

Scenario text lives in spec/r1.0-contract-scenarios.md. This repository does
not create .feature files.
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

import jsonschema

from contract_eval import (
    CONDITIONAL_METRICS,
    CORE_METRICS,
    civil_window_seconds,
    evaluate,
    host_capability,
    load_json,
    parse_instant,
    validate_events,
)

CATALOG = load_json(ROOT / "contracts" / "metrics-catalog.json")
DATASET = load_json(ROOT / "golden" / "dataset.json")
SCHEMA = load_json(ROOT / "contracts" / "event.schema.json")
MATRIX = load_json(ROOT / "contracts" / "capability-matrix.json")
OPENAPI = ROOT / "contracts" / "openapi.yaml"

CORE_LITERALS = {
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
CONDITIONAL_LITERALS = {
    "usage.tokens",
    "usage.cost_reported",
    "usage.cost_estimated",
}
PRD_METRIC_IDS = CORE_LITERALS | CONDITIONAL_LITERALS | {
    "duration.execution_ms",
    "duration.blocked_ms",
    "duration.step_p50/p95",
    "components.available",
    "components.loaded",
    "modes.distribution",
    "modes.recommendation_response",
    "usage.requests",
}
REQUIRED_CATALOG_FIELDS = {
    "metric_id",
    "name_zh",
    "unit",
    "grain",
    "dimensions",
    "denominator",
    "dedup",
    "time",
    "unknown_data",
    "version",
    "support",
}


class GoldenContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scope = DATASET["query_scope"]
        cls.result = evaluate(DATASET, cls.scope)
        cls.metrics = cls.result["metrics"]

    def metric(self, metric_id: str) -> dict:
        return self.metrics[metric_id]

    def test_golden_events_match_the_event_schema(self) -> None:
        validate_events(DATASET["events"], SCHEMA)

    def test_replay_does_not_increase_step_attempts(self) -> None:
        self.assertIn("evt_step_a1_replay", self.result["dedup"]["confirmed_event_ids"])
        self.assertNotIn("evt_step_a1_replay", self.result["dedup"]["accepted_event_ids"])
        self.assertEqual(self.metric("steps.attempts")["value"], 4)
        self.assertEqual(self.metric("steps.retry_count")["value"], 1)

    def test_same_source_id_with_different_content_conflicts(self) -> None:
        conflicts = self.result["dedup"]["conflicts"]
        self.assertEqual(conflicts[0]["event_id"], "evt_inv1_conflict")
        self.assertEqual(conflicts[0]["kept_event_id"], "evt_inv1_start")
        self.assertNotIn("evt_inv1_conflict", self.result["dedup"]["accepted_event_ids"])
        self.assertEqual(self.result["invocations"]["inv_1"]["result"], "succeeded")

    def test_timestamp_alone_is_not_a_dedup_key(self) -> None:
        self.assertIn("evt_off_1_replay", self.result["dedup"]["confirmed_event_ids"])
        self.assertIn("evt_off_2", self.result["dedup"]["accepted_event_ids"])
        self.assertNotIn("evt_off_2", self.result["dedup"]["confirmed_event_ids"])

    def test_facade_and_host_observations_merge_to_one_invocation(self) -> None:
        invocation = self.result["invocations"]["inv_1"]
        self.assertEqual(invocation["source_ids"], ["source_runtime", "source_codex"])
        self.assertEqual(self.metric("components.invocations")["value"], 3)
        self.assertEqual(
            self.metric("components.invocations")["invocation_ids"],
            ["inv_1", "inv_2", "inv_3"],
        )
        self.assertNotIn("skill:demo", self.metric("components.invocations")["invocation_ids"])

    def test_loaded_skill_is_not_an_invocation(self) -> None:
        self.assertEqual(self.metric("components.loaded")["support"], "unsupported")
        self.assertIsNone(self.metric("components.loaded")["value"])
        self.assertEqual(self.metric("components.invocations")["support"], "supported")

    def test_leaf_task_nouns_do_not_double_count_parent_or_reopen(self) -> None:
        self.assertEqual(self.metric("tasks.touched")["value"], 2)
        self.assertEqual(
            self.metric("tasks.touched")["task_uids"],
            ["task_leaf", "task_wt_b"],
        )
        self.assertEqual(self.metric("tasks.created")["value"], 2)
        self.assertNotIn("task_other", self.metric("tasks.created")["task_uids"])
        self.assertNotIn("task_parent", self.metric("tasks.created")["task_uids"])
        self.assertEqual(self.metric("tasks.completed_unique")["value"], 1)
        self.assertEqual(self.metric("tasks.completion_events")["value"], 2)
        self.assertEqual(self.metric("tasks.reopened")["value"], 1)
        self.assertEqual(
            self.metric("tasks.status_at_end")["value"],
            {"done": 1, "in-progress": 1, "unknown": 2},
        )

    def test_cross_boundary_run_is_not_a_new_start(self) -> None:
        self.assertEqual(
            self.metric("runs.started")["run_ids"],
            ["run_leaf_1", "run_leaf_2", "run_open"],
        )
        self.assertNotIn("run_cross", self.metric("runs.started")["run_ids"])
        self.assertNotIn("run_parent", self.metric("runs.started")["run_ids"])

    def test_unclosed_span_is_unknown_not_interrupted(self) -> None:
        interrupted = self.metric("runs.interrupted")
        self.assertEqual(interrupted["value"], 1)
        self.assertEqual(interrupted["run_ids"], ["run_leaf_2"])
        self.assertEqual(interrupted["unknown_run_ids"], ["run_open"])
        self.assertIsNone(self.metric("duration.execution_ms")["value"])

    def test_step_success_denominator_excludes_blocked_and_unknown(self) -> None:
        rate = self.metric("steps.success_rate_observed")
        self.assertEqual(rate["numerator"], 1)
        self.assertEqual(rate["denominator"], 2)
        self.assertEqual(rate["value"], "1/2")
        self.assertEqual(rate["excluded"]["blocked"], 1)
        self.assertEqual(rate["excluded"]["unknown"], 1)

    def test_zero_decidable_samples_are_not_zero_or_one_hundred_percent(self) -> None:
        scoped = evaluate(DATASET, {**self.scope, "task_uids": ["task_wt_b"]})
        rate = scoped["metrics"]["steps.success_rate_observed"]
        self.assertEqual(rate["sample_status"], "no-decidable-sample")
        self.assertIsNone(rate["value"])
        self.assertNotEqual(rate["value"], 0)
        self.assertNotEqual(rate["value"], 1)
        full_stack = self.metric("validations.run_pass_rate")["strata"]["full-stack"]
        self.assertEqual(full_stack["sample_status"], "no-decidable-sample")
        self.assertIsNone(full_stack["value"])

    def test_gate_denominator_does_not_grow_with_rework(self) -> None:
        self.assertEqual(self.metric("gates.required")["value"], 3)
        self.assertEqual(self.metric("gates.rework")["value"], 1)
        coverage = self.metric("gates.evidence_coverage")
        self.assertEqual(coverage["numerator"], 1)
        self.assertEqual(coverage["denominator"], 3)
        self.assertEqual(coverage["excluded"]["declared_only"], 1)
        self.assertEqual(coverage["excluded"]["stale"], 1)
        self.assertEqual(coverage["excluded"]["undecided"], 1)

    def test_first_failure_is_not_erased_by_a_later_pass(self) -> None:
        first = self.metric("tests.first_attempt_pass_rate")
        self.assertEqual(first["numerator"], 1)
        self.assertEqual(first["denominator"], 2)
        self.assertEqual(self.metric("tests.final_result_distribution")["value"], {"passed": 2})
        narrow = self.metric("validations.run_pass_rate")["strata"]["narrow"]
        self.assertEqual(narrow["numerator"], 1)
        self.assertEqual(narrow["denominator"], 2)
        self.assertEqual(self.metric("validations.runs")["value"], 2)

    def test_missing_token_and_cost_are_visible_and_not_zero(self) -> None:
        tokens = self.metric("usage.tokens")
        self.assertEqual(tokens["value"]["input_tokens"], 10)
        self.assertEqual(tokens["value"]["output_tokens"], 5)
        self.assertIsNone(tokens["value"]["cache_read_tokens"])
        self.assertEqual(tokens["missing_request_ids"], ["req_2", "req_3"])
        self.assertTrue(tokens["missing"])
        self.assertNotEqual(tokens["value"]["input_tokens"], 0)
        cost = self.metric("usage.cost_reported")
        self.assertIsNone(cost["value"])
        self.assertEqual(cost["by_currency"], {})
        self.assertIn("subscription", cost["statuses"])
        self.assertNotIn("free", cost["statuses"])
        self.assertTrue(cost["missing"])
        estimated = self.metric("usage.cost_estimated")
        self.assertIsNone(estimated["value"])
        self.assertEqual(estimated["missing_reason"], "source-not-provided")

    def test_parent_rollup_and_child_detail_are_not_both_summed(self) -> None:
        inclusive = evaluate(DATASET, {**self.scope, "task_granularity": "all"})
        tokens = inclusive["metrics"]["usage.tokens"]
        self.assertEqual(tokens["value"]["input_tokens"], 10)
        self.assertEqual(tokens["value"]["output_tokens"], 5)
        self.assertNotEqual(tokens["value"]["input_tokens"], 20)

    def test_unlinked_actor_and_gap_stay_visible(self) -> None:
        self.assertEqual(self.metric("audit.unlinked_count")["event_ids"], ["evt_unlinked"])
        self.assertEqual(self.metric("audit.gap_intervals")["gap_ids"], ["gap_omp"])
        self.assertEqual(self.result["unknown_time_event_ids"], ["evt_created_untimed"])
        unlinked = next(event for event in DATASET["events"] if event["event_id"] == "evt_unlinked")
        self.assertIsNone(unlinked["actor"]["actor_id"])
        self.assertEqual(unlinked["actor"]["identity_assurance"], "unbound")
        self.assertEqual(unlinked["external_refs"][0]["system"], "dify")

    def test_unsupported_host_does_not_unsupport_the_metric(self) -> None:
        self.assertEqual(self.result["capability"]["codex@0.164.0"], "unsupported")
        self.assertEqual(self.result["capability"]["codex@0.163.0"], "pinned")
        self.assertEqual(self.result["capability"]["omp@18.11.1"], "pinned")
        self.assertEqual(self.metric("components.invocations")["support"], "supported")
        self.assertEqual(host_capability(MATRIX, "codex", "0.999.0"), "unsupported")
        self.assertEqual(host_capability(MATRIX, "omp", "18.11.1"), "pinned")

    def test_reserved_metrics_are_unsupported_and_not_zero(self) -> None:
        for item in CATALOG["metrics"]:
            metric_id = item["metric_id"]
            result = self.metric(metric_id)
            if item["support"] == "unsupported":
                self.assertEqual(result["support"], "unsupported")
                self.assertIsNone(result["value"])
                self.assertNotEqual(result["value"], 0)

    def test_catalog_covers_prd_ids_and_support_boundary(self) -> None:
        ids = {item["metric_id"] for item in CATALOG["metrics"]}
        self.assertEqual(ids, PRD_METRIC_IDS)
        self.assertEqual(CORE_METRICS, CORE_LITERALS)
        self.assertEqual(CONDITIONAL_METRICS, CONDITIONAL_LITERALS)
        for item in CATALOG["metrics"]:
            self.assertTrue(REQUIRED_CATALOG_FIELDS <= set(item))
            self.assertEqual(item["time"]["window"], "[from, to)")
            self.assertIn("version", item)
            if item["metric_id"] in CORE_LITERALS:
                self.assertEqual(item["support"], "supported")
            elif item["metric_id"] in CONDITIONAL_LITERALS:
                self.assertEqual(item["support"], "conditional")
            else:
                self.assertEqual(item["support"], "unsupported")

    def test_missing_cost_cannot_be_filled_with_zero(self) -> None:
        event = copy.deepcopy(DATASET["events"][0])
        event["event_type"] = "usage.recorded"
        event["usage"] = {
            "request_id": "req_bad",
            "rollup": False,
            "cost_status": "missing",
            "cost_amount": 0,
        }
        with self.assertRaises(jsonschema.ValidationError):
            validate_events([event], SCHEMA)

    def test_secret_fields_are_not_part_of_the_envelope(self) -> None:
        event = copy.deepcopy(DATASET["events"][0])
        event["api_key"] = "secret"
        with self.assertRaises(jsonschema.ValidationError):
            validate_events([event], SCHEMA)

    def test_evaluate_does_not_mutate_the_dataset(self) -> None:
        before = json.dumps(DATASET, sort_keys=True)
        evaluate(DATASET, self.scope)
        self.assertEqual(json.dumps(DATASET, sort_keys=True), before)

    def test_tokyo_window_includes_from_and_excludes_to(self) -> None:
        start = parse_instant(self.scope["from"])
        end = parse_instant(self.scope["to"])
        self.assertEqual(start.isoformat(), "2026-10-15T15:00:00+00:00")
        self.assertEqual(end.isoformat(), "2026-10-16T15:00:00+00:00")
        self.assertIn("task_leaf", self.metric("tasks.created")["task_uids"])
        self.assertNotIn("task_other", self.metric("tasks.created")["task_uids"])

    def test_dst_civil_day_is_twenty_five_hours(self) -> None:
        fixture = DATASET["dst_fixture"]
        self.assertEqual(
            civil_window_seconds(
                fixture["timezone"],
                fixture["from_civil"],
                fixture["to_civil"],
            ),
            90_000,
        )
        edt = parse_instant("2026-11-01T01:30:00-04:00")
        est = parse_instant("2026-11-01T01:30:00-05:00")
        self.assertNotEqual(edt, est)
        self.assertLess(edt, est)

    def test_runtime_package_does_not_import_a_server(self) -> None:
        source = (ROOT / "contract_eval.py").read_text(encoding="utf-8")
        self.assertNotIn("starlette", source)
        self.assertNotIn("uvicorn", source)


class OpenApiDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import yaml

        cls.doc = yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))

    def parameter_names(self, operation: dict) -> set[str]:
        names = set()
        for parameter in operation.get("parameters") or []:
            if "$ref" in parameter:
                name = parameter["$ref"].rsplit("/", 1)[-1]
                parameter = self.doc["components"]["parameters"][name]
            names.add(parameter["name"])
        return names

    def test_loopback_pairing_and_csrf_match_the_auth_decision(self) -> None:
        servers = [server["url"] for server in self.doc["servers"]]
        self.assertEqual(servers, ["http://127.0.0.1:6400", "http://[::1]:6400"])
        self.assertNotIn("0.0.0.0", json.dumps(self.doc))
        schemes = self.doc["components"]["securitySchemes"]
        self.assertIn("localSession", schemes)
        self.assertIn("pairingCode", schemes)
        self.assertEqual(schemes["localSession"]["scheme"], "bearer")
        self.assertEqual(schemes["pairingCode"]["in"], "header")
        self.assertNotEqual(schemes["pairingCode"].get("in"), "query")
        pair = self.doc["paths"]["/api/v1/session/pair"]["post"]
        refresh = self.doc["paths"]["/api/v1/collection/refresh"]["post"]
        self.assertIn("X-Pairing-Code", self.parameter_names(pair))
        self.assertIn("X-CSRF-Token", self.parameter_names(refresh))
        self.assertIn("Idempotency-Key", self.parameter_names(refresh))

    def test_draft_lists_prd_routes_and_no_remote_command(self) -> None:
        paths = set(self.doc["paths"])
        required = {
            "/api/v1/health",
            "/api/v1/capabilities",
            "/api/v1/openapi.json",
            "/api/v1/projects",
            "/api/v1/actors",
            "/api/v1/components",
            "/api/v1/tasks",
            "/api/v1/tasks/{task_uid}",
            "/api/v1/tasks/{task_uid}/history",
            "/api/v1/runs",
            "/api/v1/runs/{run_id}/steps",
            "/api/v1/gates",
            "/api/v1/validations",
            "/api/v1/events",
            "/api/v1/collection-health",
            "/api/v1/metrics/catalog",
            "/api/v1/statistics/query",
            "/api/v1/statistics/timeseries",
            "/api/v1/collection/refresh",
            "/api/v1/ingest/events",
            "/api/v1/report-snapshots",
            "/api/v1/report-snapshots/{snapshot_id}",
            "/api/v1/report-snapshots/{snapshot_id}/dataset",
            "/api/v1/exports",
            "/api/v1/exports/{export_id}",
            "/api/v1/exports/{export_id}/file",
            "/api/v1/session/pair",
        }
        self.assertTrue(required <= paths)
        joined = json.dumps(self.doc["paths"])
        self.assertNotIn("remote-command", joined)
        self.assertNotIn("validation:run", joined)
        self.assertEqual(self.doc["info"]["x-sbtd-implementation"], "contract-only")
        unsafe = []
        for path, methods in self.doc["paths"].items():
            for method, operation in methods.items():
                if method not in {"post", "delete"} or path == "/api/v1/session/pair":
                    continue
                names = self.parameter_names(operation)
                self.assertIn("X-CSRF-Token", names, path)
                unsafe.append(f"{method.upper()} {path}")
        self.assertIn("POST /api/v1/collection/refresh", unsafe)
        self.assertIn("DELETE /api/v1/exports/{export_id}", unsafe)
