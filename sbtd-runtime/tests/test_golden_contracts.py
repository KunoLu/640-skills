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
PRD_METRIC_IDS = (
    CORE_LITERALS
    | CONDITIONAL_LITERALS
    | {
        "duration.execution_ms",
        "duration.blocked_ms",
        "duration.step_p50/p95",
        "components.available",
        "components.loaded",
        "modes.distribution",
        "modes.recommendation_response",
        "usage.requests",
    }
)
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


class CapabilityMatrixTests(unittest.TestCase):
    def test_completion_gate_encodes_the_adr_fallback_gate(self) -> None:
        # Scenario: 两门禁宿主都拿不到结构化事件时 R1 不放行
        gate = MATRIX["completion_gate"]
        pins = [
            f"{pin['host_kind']}@{pin['host_version']}"
            for pin in MATRIX["acceptance_pins"]
        ]
        self.assertEqual(gate["hosts"], ["codex@0.163.0", "omp@18.11.1"])
        self.assertEqual(gate["hosts"], pins)
        self.assertEqual(gate["evidence"], "real-smoke")
        self.assertIs(gate["parser_fixture_counts"], False)
        self.assertEqual(gate["event"], "skill-or-tool-call")
        self.assertEqual(gate["minimum_passing_hosts"], 1)
        self.assertLess(gate["minimum_passing_hosts"], len(gate["hosts"]))
        self.assertEqual(gate["both_unsupported"], "r1-fail-return-to-user")
        self.assertIs(gate["release_when_both_unsupported"], False)


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
        self.assertNotIn(
            "evt_step_a1_replay", self.result["dedup"]["accepted_event_ids"]
        )
        self.assertEqual(self.metric("steps.attempts")["value"], 4)
        self.assertEqual(self.metric("steps.retry_count")["value"], 1)

    def test_same_source_id_with_different_content_conflicts(self) -> None:
        conflicts = self.result["dedup"]["conflicts"]
        self.assertEqual(conflicts[0]["event_id"], "evt_inv1_conflict")
        self.assertEqual(conflicts[0]["kept_event_id"], "evt_inv1_start")
        self.assertNotIn(
            "evt_inv1_conflict", self.result["dedup"]["accepted_event_ids"]
        )
        kept = next(
            item
            for item in self.result["invocations"]
            if item["invocation_id"] == "inv_1"
        )
        self.assertEqual(kept["result"], "succeeded")

    def test_timestamp_alone_is_not_a_dedup_key(self) -> None:
        self.assertIn("evt_off_1_replay", self.result["dedup"]["confirmed_event_ids"])
        self.assertIn("evt_off_2", self.result["dedup"]["accepted_event_ids"])
        self.assertNotIn("evt_off_2", self.result["dedup"]["confirmed_event_ids"])

    def test_facade_and_host_observations_merge_to_one_invocation(self) -> None:
        invocation = next(
            item
            for item in self.result["invocations"]
            if item["invocation_id"] == "inv_1"
        )
        self.assertEqual(invocation["source_ids"], ["source_runtime", "source_codex"])
        self.assertEqual(self.metric("components.invocations")["value"], 3)
        self.assertEqual(
            self.metric("components.invocations")["invocation_ids"],
            ["inv_1", "inv_2", "inv_3"],
        )
        self.assertNotIn(
            "skill:demo", self.metric("components.invocations")["invocation_ids"]
        )

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
            ["run_child_b", "run_leaf_1", "run_leaf_2", "run_open"],
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
        self.assertEqual(
            self.metric("tests.final_result_distribution")["value"],
            {"failed": 1, "passed": 2},
        )
        narrow = self.metric("validations.run_pass_rate")["strata"]["narrow"]
        self.assertEqual(narrow["numerator"], 1)
        self.assertEqual(narrow["denominator"], 2)
        self.assertEqual(self.metric("validations.runs")["value"], 2)

    def test_missing_token_and_cost_are_visible_and_not_zero(self) -> None:
        tokens = self.metric("usage.tokens")
        self.assertEqual(tokens["value"]["input_tokens"], 10)
        self.assertEqual(tokens["value"]["output_tokens"], 5)
        self.assertIsNone(tokens["value"]["cache_read_tokens"])
        self.assertEqual(tokens["missing_request_ids"], ["req_2", "req_3", "req_est"])
        self.assertTrue(tokens["missing"])
        self.assertNotEqual(tokens["value"]["input_tokens"], 0)
        cost = self.metric("usage.cost_reported")
        self.assertIsNone(cost["value"])
        self.assertEqual(cost["by_currency"], {})
        self.assertIn("subscription", cost["statuses"])
        self.assertNotIn("free", cost["statuses"])
        self.assertTrue(cost["missing"])
        estimated = self.metric("usage.cost_estimated")
        self.assertEqual(estimated["value"], {"USD": 1.5})
        self.assertFalse(estimated["missing"])
        self.assertIsNone(self.metric("usage.cost_reported")["value"])

    def test_parent_rollup_and_child_detail_are_not_both_summed(self) -> None:
        inclusive = evaluate(DATASET, {**self.scope, "task_granularity": "all"})
        tokens = inclusive["metrics"]["usage.tokens"]
        self.assertEqual(tokens["value"]["input_tokens"], 10)
        self.assertEqual(tokens["value"]["output_tokens"], 5)
        self.assertNotEqual(tokens["value"]["input_tokens"], 20)

    def test_unlinked_actor_and_gap_stay_visible(self) -> None:
        self.assertEqual(
            self.metric("audit.unlinked_count")["event_ids"], ["evt_unlinked"]
        )
        self.assertEqual(self.metric("audit.gap_intervals")["gap_ids"], ["gap_omp"])
        self.assertEqual(self.result["unknown_time_event_ids"], ["evt_created_untimed"])
        unlinked = next(
            event for event in DATASET["events"] if event["event_id"] == "evt_unlinked"
        )
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

    def test_declared_step_success_is_not_machine_observed(self) -> None:
        sample = copy.deepcopy(DATASET)
        declared = copy.deepcopy(
            next(
                event
                for event in sample["events"]
                if event["event_id"] == "evt_step_a1_finish"
            )
        )
        declared["event_id"] = "evt_declared_finish"
        declared["ingest_seq"] = 30000
        declared["provenance"]["source_event_id"] = "evt_declared_finish"
        declared["provenance"]["source_kind"] = "user-declared"
        declared["provenance"]["observation_level"] = "declared"
        declared["scope"]["step_run_id"] = "step_declared"
        sample["events"].append(declared)
        rate = evaluate(sample, self.scope)["metrics"]["steps.success_rate_observed"]
        self.assertEqual(rate["numerator"], 1)
        self.assertEqual(rate["excluded"]["declared"], 1)

    def test_gate_invalidation_removes_coverage(self) -> None:
        sample = copy.deepcopy(DATASET)
        invalidated = copy.deepcopy(
            next(
                event
                for event in sample["events"]
                if event["event_id"] == "evt_gate_ddd_pass"
            )
        )
        invalidated["event_id"] = "evt_gate_ddd_invalidated"
        invalidated["event_type"] = "gate.evidence_invalidated"
        invalidated["occurred_at"] = "2026-10-15T18:40:00Z"
        invalidated["recorded_at"] = invalidated["occurred_at"]
        invalidated["ingest_seq"] = 30001
        invalidated["provenance"]["source_event_id"] = invalidated["event_id"]
        invalidated["gate"]["evidence_status"] = "invalid"
        invalidated["gate"]["correction"] = False
        sample["events"].append(invalidated)
        coverage = evaluate(sample, self.scope)["metrics"]["gates.evidence_coverage"]
        self.assertEqual(coverage["numerator"], 0)
        self.assertEqual(coverage["denominator"], 3)

    def test_late_receipt_does_not_override_later_occurrence(self) -> None:
        sample = copy.deepcopy(DATASET)
        late = copy.deepcopy(
            next(
                event
                for event in sample["events"]
                if event["event_id"] == "evt_leaf_progress"
            )
        )
        late["event_id"] = "evt_leaf_late_progress"
        late["occurred_at"] = "2026-10-15T19:30:00Z"
        late["recorded_at"] = "2026-10-15T21:30:00Z"
        late["ingest_seq"] = 30002
        late["provenance"]["source_event_id"] = late["event_id"]
        late["state"] = {"previous": "done", "current": "in-progress"}
        sample["events"].append(late)
        # The later done at 20:00 still wins over the earlier 19:30 progress, even if ingested last.
        status = evaluate(sample, self.scope)["metrics"]["tasks.status_at_end"]["value"]
        self.assertEqual(status["done"], 1)

    def test_spanning_run_counts_as_touched_but_not_started(self) -> None:
        scoped = evaluate(
            DATASET,
            {
                **self.scope,
                "from": "2026-10-15T16:21:00Z",
                "to": "2026-10-15T16:24:00Z",
            },
        )
        self.assertIn("task_leaf", scoped["metrics"]["tasks.touched"]["task_uids"])
        self.assertEqual(scoped["metrics"]["runs.started"]["value"], 0)

    def test_terminal_invocation_rate_includes_a_finish_whose_start_is_outside(
        self,
    ) -> None:
        scoped = evaluate(
            DATASET,
            {
                **self.scope,
                "from": "2026-10-15T15:47:30Z",
                "to": "2026-10-15T15:49:00Z",
            },
        )
        rate = scoped["metrics"]["components.failure_rate"]
        self.assertEqual(rate["numerator"], 0)
        self.assertEqual(rate["denominator"], 1)
        self.assertEqual(scoped["metrics"]["components.invocations"]["value"], 0)

    def test_retry_attempt_is_not_relabeled_as_first(self) -> None:
        scoped = evaluate(
            DATASET,
            {
                **self.scope,
                "from": "2026-10-15T17:30:00Z",
                "to": "2026-10-15T18:00:00Z",
            },
        )
        first = scoped["metrics"]["tests.first_attempt_pass_rate"]
        self.assertEqual(first["numerator"], 1)
        self.assertEqual(first["denominator"], 2)

    def test_recovered_gap_is_not_an_open_interval(self) -> None:
        sample = copy.deepcopy(DATASET)
        recovered = copy.deepcopy(
            next(event for event in sample["events"] if event["event_id"] == "evt_gap")
        )
        recovered["event_id"] = "evt_gap_recovered"
        recovered["event_type"] = "collection.recovered"
        recovered["occurred_at"] = "2026-10-15T18:45:00Z"
        recovered["recorded_at"] = recovered["occurred_at"]
        recovered["ingest_seq"] = 30003
        recovered["provenance"]["source_event_id"] = recovered["event_id"]
        recovered["collection"]["closed"] = True
        sample["events"].append(recovered)
        gaps = evaluate(sample, self.scope)["metrics"]["audit.gap_intervals"]
        self.assertEqual(gaps["value"], 0)

    def test_parallel_child_runs_stay_distinct(self) -> None:
        self.assertIn("run_child_b", self.metric("runs.started")["run_ids"])
        self.assertIn("run_leaf_1", self.metric("runs.started")["run_ids"])

    def test_revision_fields_can_be_retained(self) -> None:
        event = copy.deepcopy(DATASET["events"][0])
        event["workflow"] = {
            "workflow_source_revision": "workflow-sha",
            "source_commit_sha": "commit-sha",
            "worktree_revision": "worktree-sha",
            "task_document_revision": "task-sha",
        }
        validate_events([event], SCHEMA)

    def test_mixed_token_semantics_are_not_summed_together(self) -> None:
        sample = copy.deepcopy(DATASET)
        other = copy.deepcopy(
            next(
                event
                for event in sample["events"]
                if event["event_id"] == "evt_usage_detail"
            )
        )
        other["event_id"] = "evt_usage_cache"
        other["occurred_at"] = "2026-10-15T18:12:00Z"
        other["recorded_at"] = other["occurred_at"]
        other["ingest_seq"] = 30004
        other["provenance"]["source_event_id"] = other["event_id"]
        other["usage"] = {
            **other["usage"],
            "request_id": "req_cache",
            "input_includes_cache": True,
            "input_tokens": 7,
        }
        sample["events"].append(other)
        tokens = evaluate(sample, self.scope)["metrics"]["usage.tokens"]
        self.assertIsNone(tokens["value"])
        self.assertEqual(len(tokens["groups"]), 2)

    def test_golden_oracle_matches_every_metric(self) -> None:
        expected = json.loads(
            (ROOT / "golden" / "expected.json").read_text(encoding="utf-8")
        )
        present = {event["event_id"] for event in DATASET["events"]}
        self.assertEqual(
            set(expected["metrics"]), {item["metric_id"] for item in CATALOG["metrics"]}
        )
        for metric_id, oracle in expected["metrics"].items():
            actual = self.metric(metric_id)
            self.assertEqual(actual["support"], oracle["support"], metric_id)
            self.assertEqual(actual["value"], oracle["value"], metric_id)
            if "numerator" in oracle:
                self.assertEqual(actual["numerator"], oracle["numerator"], metric_id)
                self.assertEqual(
                    actual["denominator"], oracle["denominator"], metric_id
                )
            self.assertTrue(set(oracle["source_event_ids"]) <= present, metric_id)

    def test_library_modules_do_not_import_the_server_layer(self) -> None:
        """R2 起允许服务层存在（serve.py）；钉法改为契约层约束：R1 库面模块
        不得 import 服务栈（starlette／uvicorn），服务依赖只许出现在 serve.py。"""
        library_modules = [
            "codex_adapter.py",
            "contract_eval.py",
            "csv_export.py",
            "event_store.py",
            "extensions.py",
            "facade.py",
            "history_import.py",
            "history_read.py",
            "omp_adapter.py",
            "report_snapshot.py",
            "stats_query.py",
        ]
        for name in library_modules:
            source = (ROOT / name).read_text(encoding="utf-8")
            with self.subTest(module=name):
                self.assertNotIn("starlette", source)
                self.assertNotIn("uvicorn", source)


class OpenApiDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import yaml

        cls.doc = yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))
        manifest = load_json(ROOT / "contracts" / "panel-manifest.json")
        cls.panel_order = [
            panel["panel_id"]
            for panel in sorted(manifest["panels"], key=lambda panel: panel["order"])
        ]

    def parameter_names(self, operation: dict) -> set[str]:
        names = set()
        for parameter in operation.get("parameters") or []:
            if "$ref" in parameter:
                name = parameter["$ref"].rsplit("/", 1)[-1]
                parameter = self.doc["components"]["parameters"][name]
            names.add(parameter["name"])
        return names

    def create_export_validator(self) -> jsonschema.Draft202012Validator:
        body = self.doc["paths"]["/api/v1/exports"]["post"]["requestBody"]
        schema = body["content"]["application/json"]["schema"]
        return jsonschema.Draft202012Validator(self.doc).evolve(schema=schema)

    def test_authenticated_operations_declare_bearer_401(self) -> None:
        exempt_paths = {"/api/v1/health", "/api/v1/session/pair"}
        methods = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
        for path, path_item in self.doc["paths"].items():
            if not path.startswith("/api/v1/") or path in exempt_paths:
                continue
            for method, operation in path_item.items():
                if method not in methods:
                    continue
                with self.subTest(path=path, method=method):
                    self.assertEqual(
                        operation["responses"].get("401"),
                        {"$ref": "#/components/responses/Unauthorized"},
                    )

    def test_auth_exempt_operations_preserve_their_401_contracts(self) -> None:
        health = self.doc["paths"]["/api/v1/health"]["get"]
        pair = self.doc["paths"]["/api/v1/session/pair"]["post"]
        self.assertNotIn("401", health["responses"])
        self.assertEqual(
            pair["responses"].get("401"),
            {"$ref": "#/components/responses/Unauthorized"},
        )

    def test_snapshot_get_responses_match_runtime_handlers(self) -> None:
        for suffix, errors in (
            ("", {"404": "NotFound", "410": "Gone"}),
            ("/dataset", {"400": "BadRequest", "404": "NotFound", "410": "Gone"}),
        ):
            with self.subTest(path=suffix or "/"):
                operation = self.doc["paths"][
                    f"/api/v1/report-snapshots/{{snapshot_id}}{suffix}"
                ]["get"]
                expected = {
                    "200": "Json",
                    "401": "Unauthorized",
                    "403": "Forbidden",
                    **errors,
                }
                self.assertEqual(
                    operation["responses"],
                    {
                        status: {"$ref": f"#/components/responses/{component}"}
                        for status, component in expected.items()
                    },
                )

    def test_export_responses_match_runtime_handlers(self) -> None:
        # export_resource 映射：三个操作带 query params 均 400；DELETE 缺
        # Idempotency-Key 亦 400；ExportNotFound→404、ExportGone→410；
        # ExportNotReady→409 仅 download 抛出，get 返回 200 状态视图、
        # delete 不抛 ExportNotReady，因此两者不声明 409。
        for method, path, success, errors in (
            (
                "get",
                "/api/v1/exports/{export_id}",
                {"200": "ExportStatus"},
                {"400": "BadRequest", "404": "NotFound", "410": "Gone"},
            ),
            (
                "get",
                "/api/v1/exports/{export_id}/file",
                {"200": None},  # inline description 与 x-sbtd-csv-columns
                {
                    "400": "BadRequest",
                    "404": "NotFound",
                    "409": "Conflict",
                    "410": "Gone",
                },
            ),
            (
                "delete",
                "/api/v1/exports/{export_id}",
                {"204": None},  # inline description
                {"400": "BadRequest", "404": "NotFound", "410": "Gone"},
            ),
        ):
            with self.subTest(method=method, path=path):
                responses = dict(self.doc["paths"][path][method]["responses"])
                expected = {"401": "Unauthorized", "403": "Forbidden", **errors}
                for status, component in success.items():
                    if component is None:
                        responses.pop(status)
                    else:
                        expected[status] = component
                self.assertEqual(
                    responses,
                    {
                        status: {"$ref": f"#/components/responses/{component}"}
                        for status, component in expected.items()
                    },
                )

    def test_create_export_accepts_supported_formats_without_presentation(self) -> None:
        # Scenario: 固定快照并选择当前支持的导出格式
        operation = self.doc["paths"]["/api/v1/exports"]["post"]
        body = operation["requestBody"]
        self.assertIs(body["required"], True)
        validator = self.create_export_validator()
        for export_format in ("html", "csv", "jpeg", "pdf"):
            with self.subTest(format=export_format):
                errors = list(
                    validator.iter_errors(
                        {"snapshot_id": "snap_" + "a" * 32, "format": export_format}
                    )
                )
                self.assertEqual(errors, [])
        self.assertEqual(
            self.doc["components"]["schemas"]["CreateExportRequest"]["properties"][
                "format"
            ]["enum"],
            ["html", "csv", "jpeg", "pdf"],
        )

    def test_create_export_accepts_complete_presentation(self) -> None:
        # Scenario: 呈现状态不成为数据筛选
        state = {
            "theme": "light",
            "report_width_px": 1440,
            "expanded_detail_ids": ["task_report"],
            "table_sort": {"tasks": "duration:desc"},
            "preview_row_sets": {"tasks": 20},
            "panel_order": self.panel_order,
            "legend_state": {"tokens": False},
        }
        validator = self.create_export_validator()
        for export_format in ("html", "csv", "jpeg", "pdf"):
            with self.subTest(format=export_format):
                request = {
                    "snapshot_id": "snap_" + "a" * 32,
                    "format": export_format,
                    "presentation_state": state,
                }
                self.assertEqual(list(validator.iter_errors(request)), [])
        for value in (0, 0.5):
            with self.subTest(nonnegative_number=value):
                request = {
                    "snapshot_id": "snap_" + "a" * 32,
                    "format": "html",
                    "presentation_state": {
                        **state,
                        "report_width_px": value,
                        "preview_row_sets": {"tasks": value},
                    },
                }
                self.assertEqual(list(validator.iter_errors(request)), [])

    def test_create_export_rejects_invalid_requests(self) -> None:
        # Scenario: 拒绝不完整或不支持的导出请求
        valid = {"snapshot_id": "snap_" + "a" * 32, "format": "html"}
        cases = [
            ("null body", None, "type"),
            ("array body", [], "type"),
            ("missing snapshot", {"format": "html"}, "required"),
            ("missing format", {"snapshot_id": valid["snapshot_id"]}, "required"),
            ("numeric snapshot", {**valid, "snapshot_id": 42}, "type"),
            ("null snapshot", {**valid, "snapshot_id": None}, "type"),
            ("unknown field", {**valid, "filters": {}}, "additionalProperties"),
            ("null presentation", {**valid, "presentation_state": None}, "type"),
            ("array presentation", {**valid, "presentation_state": []}, "type"),
        ]
        for export_format in (
            "jpg",
            "JPEG",
            "PDF",
            "png",
            "json",
            "HTML",
            "",
            None,
            42,
        ):
            cases.append(
                (
                    f"unsupported format {export_format!r}",
                    {**valid, "format": export_format},
                    "enum",
                )
            )
        validator = self.create_export_validator()
        for name, request, expected_error in cases:
            with self.subTest(case=name):
                errors = list(validator.iter_errors(request))
                self.assertIn(expected_error, [error.validator for error in errors])

    def test_create_export_rejects_malformed_snapshot_id(self) -> None:
        # Scenario: 请求体中格式错误的快照标识属于非法请求
        validator = self.create_export_validator()
        for snapshot_id in (
            "",
            "snap_report",
            "snap_" + "a" * 31,
            "snap_" + "a" * 33,
            "snap_" + "A" * 32,
            "snap_" + "g" * 32,
            "prefix_snap_" + "a" * 32,
            "snap_" + "a" * 32 + "_suffix",
        ):
            for export_format in ("html", "csv", "jpeg", "pdf"):
                with self.subTest(snapshot_id=snapshot_id, format=export_format):
                    request = {"snapshot_id": snapshot_id, "format": export_format}
                    errors = list(validator.iter_errors(request))
                    self.assertEqual(
                        [(list(error.path), error.validator) for error in errors],
                        [(["snapshot_id"], "pattern")],
                    )

    def test_create_export_rejects_incomplete_or_invalid_presentation(self) -> None:
        # Scenarios: 拒绝不完整或不支持的导出请求；拒绝空或重复的 Panel 顺序
        state = {
            "theme": "dark",
            "report_width_px": 1440,
            "expanded_detail_ids": [],
            "table_sort": {},
            "preview_row_sets": {},
            "panel_order": self.panel_order,
            "legend_state": {},
        }
        validator = self.create_export_validator()
        for field in state:
            incomplete = {key: value for key, value in state.items() if key != field}
            with self.subTest(missing=field):
                request = {
                    "snapshot_id": "snap_" + "a" * 32,
                    "format": "html",
                    "presentation_state": incomplete,
                }
                errors = list(validator.iter_errors(request))
                self.assertIn("required", [error.validator for error in errors])
        invalid_fields = [
            ("theme", "sepia", "enum"),
            ("report_width_px", "1440", "type"),
            ("report_width_px", -1, "minimum"),
            ("report_width_px", -0.5, "minimum"),
            ("expanded_detail_ids", [42], "type"),
            ("table_sort", {"tasks": 42}, "type"),
            ("preview_row_sets", {"tasks": "20"}, "type"),
            ("preview_row_sets", {"tasks": -1}, "minimum"),
            ("preview_row_sets", {"tasks": -0.5}, "minimum"),
            ("panel_order", [42], "type"),
            ("panel_order", [], "minItems"),
            ("panel_order", [*self.panel_order, self.panel_order[0]], "uniqueItems"),
            ("legend_state", {"tokens": "hidden"}, "type"),
            ("filters", {}, "additionalProperties"),
        ]
        for field, value, expected_error in invalid_fields:
            with self.subTest(invalid=field, value=value):
                request = {
                    "snapshot_id": "snap_" + "a" * 32,
                    "format": "csv",
                    "presentation_state": {**state, field: value},
                }
                errors = list(validator.iter_errors(request))
                self.assertIn(expected_error, [error.validator for error in errors])

    def test_create_export_declares_validation_snapshot_and_preflight_errors(
        self,
    ) -> None:
        # Scenarios: 缺失与过期快照不被静默替换；JPEG 超限预检返回明确限制
        responses = self.doc["paths"]["/api/v1/exports"]["post"]["responses"]
        expected = {
            "202": "ExportAccepted",
            "400": "BadRequest",
            "401": "Unauthorized",
            "403": "Forbidden",
            "404": "NotFound",
            "410": "Gone",
            "422": "ExportImageSizeLimit",
            "503": "ExportRendererUnavailable",
            "507": "DiskQuotaExceeded",
        }
        with self.subTest(operation="createExport"):
            self.assertEqual(
                responses,
                {
                    status: {"$ref": f"#/components/responses/{component}"}
                    for status, component in expected.items()
                },
            )

    def test_create_export_replay_precedes_admission_checks(self) -> None:
        # Scenarios: renderer／快照／配额变化后的重放；非重放仍执行准入检查
        operation = self.doc["paths"]["/api/v1/exports"]["post"]
        replay = operation.get("x-sbtd-idempotent-replay")
        self.assertEqual(
            replay,
            {
                "response": "202",
                "evaluated_after": ["400", "401", "403"],
                "precedes": ["404", "410", "422", "503", "507"],
            },
        )
        responses = set(operation["responses"])
        self.assertLessEqual(set(replay["precedes"]), responses)
        self.assertEqual(
            set(replay["precedes"]) | set(replay["evaluated_after"]) | {"202"},
            responses,
        )

    def test_create_export_replay_accepts_original_id_and_warnings(self) -> None:
        # Scenario: JPEG 降级重放保留原告警且不重复预检（这里只验证响应 schema）
        operation = self.doc["paths"]["/api/v1/exports"]["post"]
        response = operation["responses"][
            operation["x-sbtd-idempotent-replay"]["response"]
        ]
        self.assertEqual(response, {"$ref": "#/components/responses/ExportAccepted"})
        schema = self.doc["components"]["responses"]["ExportAccepted"]["content"][
            "application/json"
        ]["schema"]
        validator = jsonschema.Draft202012Validator(self.doc).evolve(schema=schema)
        replayed = {
            "api_version": "1",
            "request_id": "req_export_replay",
            "data": {"export_id": "exp_0123456789abcdef0123456789abcdef"},
            "meta": {
                "metrics_version": "1.0",
                "projection_version": "1.0",
                "complete": True,
                "warnings": ["EXPORT_SCALE_DOWNGRADED:1x"],
            },
        }
        self.assertEqual(list(validator.iter_errors(replayed)), [])

    def test_create_report_snapshot_declares_disk_quota_refusal(self) -> None:
        # Scenario: 清扫后共享占用超限时拒绝新建
        responses = self.doc["paths"]["/api/v1/report-snapshots"]["post"]["responses"]
        expected = {
            "201": "Json",
            "401": "Unauthorized",
            "403": "Forbidden",
            "507": "DiskQuotaExceeded",
        }
        self.assertEqual(
            responses,
            {
                status: {"$ref": f"#/components/responses/{component}"}
                for status, component in expected.items()
            },
        )

    def test_query_statistics_declares_shared_disk_quota_refusal(self) -> None:
        # Scenario: 统计查询所需快照被共享配额拒绝的响应契约
        responses = self.doc["paths"]["/api/v1/statistics/query"]["post"]["responses"]
        expected = {
            "200": "Json",
            "400": "BadRequest",
            "401": "Unauthorized",
            "403": "Forbidden",
            "507": "DiskQuotaExceeded",
        }
        self.assertEqual(
            responses,
            {
                status: {"$ref": f"#/components/responses/{component}"}
                for status, component in expected.items()
            },
        )
        for path in ("/api/v1/exports", "/api/v1/report-snapshots"):
            with self.subTest(path=path):
                self.assertEqual(
                    responses["507"],
                    self.doc["paths"][path]["post"]["responses"]["507"],
                )

    def test_disk_quota_exceeded_requires_detail_and_byte_counts(self) -> None:
        # Scenarios: 清扫后共享占用超限时拒绝新建；返回解析后的有效配额而不是固定默认值或原始配置
        response = self.doc["components"]["responses"]["DiskQuotaExceeded"]
        schema = response["content"]["application/json"]["schema"]
        jsonschema.Draft202012Validator.check_schema(schema)
        self.assertEqual(schema["properties"]["detail"]["const"], "DISK_QUOTA_EXCEEDED")
        self.assertEqual(
            set(schema["required"]), {"detail", "used_bytes", "quota_bytes"}
        )
        self.assertIs(schema["additionalProperties"], False)
        self.assertTrue(
            {"const", "enum", "maximum"}.isdisjoint(schema["properties"]["quota_bytes"])
        )
        validator = jsonschema.Draft202012Validator(schema)
        body = {
            "detail": "DISK_QUOTA_EXCEEDED",
            "used_bytes": 2000000001,
            "quota_bytes": 2000000000,
        }
        self.assertEqual(list(validator.iter_errors(body)), [])
        self.assertEqual(
            list(
                validator.iter_errors(
                    {**body, "used_bytes": 4000000001, "quota_bytes": 4000000000}
                )
            ),
            [],
        )
        # schema 只校验各字段边界；U > L 跨字段关系由 R2.2 准入实现保证。
        self.assertEqual(
            list(validator.iter_errors({**body, "used_bytes": 0, "quota_bytes": 1})),
            [],
        )
        for field in body:
            with self.subTest(missing=field):
                incomplete = {key: value for key, value in body.items() if key != field}
                errors = list(validator.iter_errors(incomplete))
                self.assertIn("required", [error.validator for error in errors])
        for field, value, expected_error in (
            ("detail", "EXPORT_IMAGE_SIZE_LIMIT", "const"),
            ("detail", None, "type"),
            ("detail", 507, "type"),
            ("used_bytes", "2000000001", "type"),
            ("used_bytes", 1.5, "type"),
            ("used_bytes", True, "type"),
            ("used_bytes", None, "type"),
            ("used_bytes", -1, "minimum"),
            ("quota_bytes", "2000000000", "type"),
            ("quota_bytes", 1.5, "type"),
            ("quota_bytes", True, "type"),
            ("quota_bytes", None, "type"),
            ("quota_bytes", 0, "minimum"),
            ("quota_bytes", -1, "minimum"),
            ("SBTD_RUNTIME_DISK_QUOTA_BYTES", "2GB", "additionalProperties"),
        ):
            with self.subTest(invalid=field, value=value):
                errors = list(validator.iter_errors({**body, field: value}))
                self.assertIn(expected_error, [error.validator for error in errors])
        for invalid in ([], None, "DISK_QUOTA_EXCEEDED"):
            with self.subTest(body=invalid):
                errors = list(validator.iter_errors(invalid))
                self.assertIn("type", [error.validator for error in errors])

    def test_export_renderer_unavailable_requires_closed_detail_body(self) -> None:
        # Scenario: 图像与 PDF renderer 不可用时在接受前拒绝
        response = self.doc["components"]["responses"]["ExportRendererUnavailable"]
        schema = response["content"]["application/json"]["schema"]
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema)
        body = {"detail": "EXPORT_RENDERER_UNAVAILABLE"}
        self.assertEqual(list(validator.iter_errors(body)), [])
        for invalid, expected_error in (
            ({}, "required"),
            ({"detail": "EXPORT_IMAGE_SIZE_LIMIT"}, "const"),
            ({"detail": None}, "type"),
            ({"detail": 503}, "type"),
            ({**body, "export_id": "export_report"}, "additionalProperties"),
            ([], "type"),
        ):
            with self.subTest(body=invalid):
                errors = list(validator.iter_errors(invalid))
                self.assertIn(expected_error, [error.validator for error in errors])

    def test_get_export_status_requires_state_specific_error(self) -> None:
        # Scenarios: 失败作业使用稳定错误码；非失败状态没有错误码
        response = self.doc["paths"]["/api/v1/exports/{export_id}"]["get"]["responses"][
            "200"
        ]
        response = self.doc["components"]["responses"][
            response["$ref"].rsplit("/", 1)[1]
        ]
        schema = response["content"]["application/json"]["schema"]
        jsonschema.Draft202012Validator.check_schema(schema)
        job_schema = self.doc["components"]["schemas"]["ExportJob"]
        jsonschema.Draft202012Validator.check_schema(job_schema)
        self.assertEqual(
            job_schema["properties"]["status"]["enum"],
            ["queued", "generating", "ready", "failed", "cancelled"],
        )
        validator = jsonschema.Draft202012Validator(self.doc).evolve(schema=schema)
        envelope = {
            "api_version": "1",
            "request_id": "req_export",
            "data": {"status": "queued", "error": None},
            "meta": {
                "metrics_version": "1.0",
                "projection_version": "1.0",
                "complete": True,
                "warnings": ["EXPORT_SCALE_DOWNGRADED:1x"],
            },
        }
        codes = ("EXPORT_RENDER_TIMEOUT", "EXPORT_RENDER_FAILED")
        for status in ("queued", "generating", "ready", "failed", "cancelled"):
            for error in (None, *codes, "export failed", "EXPORT_FUTURE_ERROR", 42):
                with self.subTest(status=status, error=error):
                    data = {"status": status, "error": error}
                    valid = error in codes if status == "failed" else error is None
                    self.assertEqual(
                        validator.is_valid({**envelope, "data": data}), valid
                    )
        for data in (
            {},
            {"status": "ready"},
            {"error": None},
            {"status": "unknown", "error": None},
            {"status": None, "error": None},
            None,
            [],
        ):
            with self.subTest(invalid_data=data):
                self.assertFalse(validator.is_valid({**envelope, "data": data}))
        for field in envelope:
            with self.subTest(missing_envelope_field=field):
                self.assertFalse(
                    validator.is_valid(
                        {key: value for key, value in envelope.items() if key != field}
                    )
                )
        for field, value in (
            ("api_version", "2"),
            ("request_id", 42),
            ("meta", {}),
            ("meta", {**envelope["meta"], "complete": "yes"}),
        ):
            with self.subTest(invalid_envelope_field=field):
                self.assertFalse(validator.is_valid({**envelope, field: value}))
        data = {
            **envelope["data"],
            "export_id": "export_report",
            "ready_at": None,
            "byte_count": None,
            "future_metadata": {"version": 2},
            "warnings": ["EXPORT_SCALE_DOWNGRADED:1x", "Other warning"],
        }
        self.assertEqual(list(validator.iter_errors({**envelope, "data": data})), [])
        for field in ("data", "meta"):
            with self.subTest(structured_warning=field):
                invalid = {**envelope, field: {**envelope[field], "warnings": [{}]}}
                self.assertFalse(validator.is_valid(invalid))

    def test_export_image_size_limit_requires_detail_and_limits(self) -> None:
        # Scenario: JPEG 超限预检返回明确限制
        response = self.doc["components"]["responses"]["ExportImageSizeLimit"]
        schema = response["content"]["application/json"]["schema"]
        jsonschema.Draft202012Validator.check_schema(schema)
        self.assertEqual(
            schema["properties"]["detail"]["const"], "EXPORT_IMAGE_SIZE_LIMIT"
        )
        self.assertEqual(
            set(schema["required"]), {"detail", "max_edge_px", "max_total_pixels"}
        )
        for field in ("max_edge_px", "max_total_pixels"):
            with self.subTest(unfrozen_limit=field):
                self.assertTrue(
                    {"const", "enum", "maximum"}.isdisjoint(schema["properties"][field])
                )
        validator = jsonschema.Draft202012Validator(schema)
        body = {
            "detail": "EXPORT_IMAGE_SIZE_LIMIT",
            "max_edge_px": 32000,
            "max_total_pixels": 80000000,
        }
        self.assertEqual(list(validator.iter_errors(body)), [])
        # PRD 建议值不是冻结值；响应必须能报告平台实测后采用的限制。
        self.assertEqual(
            list(
                validator.iter_errors(
                    {**body, "max_edge_px": 16000, "max_total_pixels": 40000000}
                )
            ),
            [],
        )
        for field in body:
            with self.subTest(missing=field):
                incomplete = {key: value for key, value in body.items() if key != field}
                errors = list(validator.iter_errors(incomplete))
                self.assertIn("required", [error.validator for error in errors])
        for field, value, expected_error in (
            ("detail", "EXPORT_DISK_SIZE_LIMIT", "const"),
            ("max_edge_px", "32000", "type"),
            ("max_edge_px", 1.5, "type"),
            ("max_edge_px", 0, "minimum"),
            ("max_total_pixels", "80000000", "type"),
            ("max_total_pixels", 1.5, "type"),
            ("max_total_pixels", 0, "minimum"),
            ("unknown", True, "additionalProperties"),
        ):
            with self.subTest(invalid=field, value=value):
                errors = list(validator.iter_errors({**body, field: value}))
                self.assertIn(expected_error, [error.validator for error in errors])

    def test_create_export_202_carries_scale_downgrade_warning(self) -> None:
        # Scenario: JPEG 降采样通过接受响应告知用户
        response = self.doc["components"]["responses"]["ExportAccepted"]
        schemas = self.doc["components"]["schemas"]
        warnings = schemas["Meta"]["properties"]["warnings"]
        warning = "EXPORT_SCALE_DOWNGRADED:1x"
        for name, described in (
            ("ExportAccepted", response),
            ("Meta.warnings", warnings),
        ):
            with self.subTest(description=name):
                self.assertIn(warning, described.get("description", ""))
        self.assertEqual(warnings["items"], {"type": "string"})
        self.assertEqual(
            set(schemas["CreateExportAccepted"]["properties"]), {"export_id"}
        )
        schema = response["content"]["application/json"]["schema"]
        validator = jsonschema.Draft202012Validator(self.doc).evolve(schema=schema)
        accepted = {
            "api_version": "1",
            "request_id": "req_export",
            "data": {"export_id": "export_report"},
            "meta": {
                "metrics_version": "1.0",
                "projection_version": "1.0",
                "complete": True,
                "warnings": [warning],
            },
        }
        self.assertEqual(list(validator.iter_errors(accepted)), [])

    def test_create_export_202_requires_export_id_and_preserves_envelope(self) -> None:
        # Scenario: 导出接受响应提供后续查询与下载所需标识
        response = self.doc["paths"]["/api/v1/exports"]["post"]["responses"]["202"]
        response = self.doc["components"]["responses"][
            response["$ref"].rsplit("/", 1)[1]
        ]
        schema = response["content"]["application/json"]["schema"]
        validator = jsonschema.Draft202012Validator(self.doc).evolve(schema=schema)
        accepted = {
            "api_version": "1",
            "request_id": "req_export",
            "data": {"export_id": "export_report"},
            "meta": {
                "metrics_version": "1.0",
                "projection_version": "1.0",
                "complete": True,
            },
        }
        self.assertEqual(list(validator.iter_errors(accepted)), [])
        for data, expected_error in (
            ({}, "required"),
            ({"export_id": 42}, "type"),
            ({"export_id": None}, "type"),
            ({"export_id": "export_report", "status": "ready"}, "additionalProperties"),
            (None, "type"),
            ([], "type"),
        ):
            with self.subTest(data=data):
                errors = list(validator.iter_errors({**accepted, "data": data}))
                self.assertIn(expected_error, [error.validator for error in errors])
        for field in accepted:
            with self.subTest(missing=field):
                incomplete = {
                    key: value for key, value in accepted.items() if key != field
                }
                errors = list(validator.iter_errors(incomplete))
                self.assertIn("required", [error.validator for error in errors])
        for field, value, expected_error in (
            ("api_version", "2", "const"),
            ("request_id", 42, "type"),
            ("meta", {}, "required"),
            ("meta", {**accepted["meta"], "complete": "yes"}, "type"),
        ):
            with self.subTest(invalid=field, value=value):
                errors = list(validator.iter_errors({**accepted, field: value}))
                self.assertIn(expected_error, [error.validator for error in errors])

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

    def test_exports_are_rc2_and_not_rc1_blocking(self) -> None:
        # Scenario: 导出接口不属于 rc.1 阻塞交付
        exports = {
            path: item
            for path, item in self.doc["paths"].items()
            if path == "/api/v1/exports" or path.startswith("/api/v1/exports/")
        }
        self.assertEqual(
            set(exports),
            {
                "/api/v1/exports",
                "/api/v1/exports/{export_id}",
                "/api/v1/exports/{export_id}/file",
            },
        )
        for path, item in exports.items():
            for method, operation in item.items():
                with self.subTest(path=path, method=method):
                    self.assertEqual(operation["x-sbtd-release"], "v2.1.0-rc.2")
                    self.assertIs(operation["x-sbtd-rc1-blocking"], False)
        self.assertEqual(self.doc["info"]["x-sbtd-release"], "v2.1.0-rc.1")
        refresh = self.doc["paths"]["/api/v1/collection/refresh"]["post"]
        self.assertNotEqual(refresh.get("x-sbtd-release"), "v2.1.0-rc.2")

    def test_download_export_csv_columns_match_serializer(self) -> None:
        import csv_export

        operation = self.doc["paths"]["/api/v1/exports/{export_id}/file"]["get"]
        columns = operation["responses"]["200"]["x-sbtd-csv-columns"]
        self.assertEqual(columns, csv_export.COLUMNS)
        self.assertEqual(columns[-1], "reasoning_tokens")
        notes = operation["responses"]["200"]["x-sbtd-csv-column-notes"]
        self.assertIn("reasoning_tokens", notes)
        schema_version = operation["responses"]["200"]["x-sbtd-csv-schema-version"]
        self.assertEqual(schema_version, "1.1")
        self.assertEqual(schema_version, csv_export.CSV_SCHEMA_VERSION)

    def test_forbidden_response_is_shared_for_host_origin_and_csrf(self) -> None:
        # Scenario: Host／Origin 与 CSRF 拒绝共用 403 契约
        forbidden = self.doc["components"]["responses"]["Forbidden"]
        description = forbidden["description"].lower()
        self.assertIn("host", description)
        self.assertIn("origin", description)
        self.assertIn("csrf", description)
        for path, item in self.doc["paths"].items():
            for method, operation in item.items():
                with self.subTest(path=path, method=method):
                    self.assertEqual(
                        operation["responses"]["403"]["$ref"],
                        "#/components/responses/Forbidden",
                    )
