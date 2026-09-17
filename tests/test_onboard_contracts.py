from __future__ import annotations

import copy
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import ClassVar

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

import onboard_contract_fixtures as fixtures

contracts = fixtures.contracts
ContractError = contracts.ContractError

ZERO_DIGEST = "0" * 64


def reseal(kind: str, document: dict, mutate) -> dict:
    payload = copy.deepcopy(document["payload"])
    mutate(payload)
    return contracts.seal_document(kind, payload)


def expect_error(
    testcase: unittest.TestCase, code: str, fn, *args, **kwargs
) -> ContractError:
    with testcase.assertRaises(ContractError) as raised:
        fn(*args, **kwargs)
    testcase.assertEqual(raised.exception.code, code)
    return raised.exception


class StrictDecodeTests(unittest.TestCase):
    def load(self, text, kind="publication_decisions"):
        return contracts.load_document(text, kind)

    def test_duplicate_keys_are_rejected(self) -> None:
        error = expect_error(
            self,
            "duplicate-key",
            self.load,
            '{"schema_version": 1, "schema_version": 1, "items": []}',
        )
        self.assertEqual(error.exit_code, 2)

    def test_nonfinite_numbers_are_rejected(self) -> None:
        for literal in ("NaN", "Infinity", "-Infinity", "1e999"):
            with self.subTest(literal=literal):
                expect_error(
                    self,
                    "non-finite-number",
                    self.load,
                    f'{{"schema_version": {literal}, "items": []}}',
                )

    def test_float_literals_are_wrong_type(self) -> None:
        expect_error(
            self,
            "unexpected-type",
            self.load,
            '{"schema_version": 1.0, "items": []}',
        )

    def test_boolean_is_not_an_integer(self) -> None:
        expect_error(
            self,
            "schema-violation",
            self.load,
            '{"schema_version": true, "items": []}',
        )

    def test_invalid_utf8_is_rejected(self) -> None:
        expect_error(
            self,
            "invalid-utf8",
            contracts.load_document,
            b'{"schema_version": 1, "items": [], "x": "\xff"}',
            "publication_decisions",
        )

    def test_unpaired_surrogate_escape_is_rejected(self) -> None:
        expect_error(
            self,
            "malformed-unicode",
            self.load,
            '{"schema_version": 1, "items": [], "x": "\\ud800"}',
        )

    def test_malformed_json_is_rejected(self) -> None:
        expect_error(self, "invalid-json", self.load, '{"schema_version": 1,]')

    def test_unknown_kind_is_rejected(self) -> None:
        expect_error(self, "unknown-kind", self.load, "{}", kind="Manifest")
        expect_error(
            self, "unknown-kind", contracts.validate_document, {}, "deployment_result"
        )

    def test_future_schema_version_is_rejected(self) -> None:
        expect_error(
            self, "schema-violation", self.load, '{"schema_version": 2, "items": []}'
        )


class CanonicalJsonTests(unittest.TestCase):
    def test_canonical_bytes_sort_keys_and_skip_ascii_escaping(self) -> None:
        value = {"b": "用户", "a": [1, True, None]}
        self.assertEqual(
            contracts.canonical_json_bytes(value),
            '{"a":[1,true,null],"b":"用户"}'.encode(),
        )

    def test_key_insertion_order_does_not_change_digest(self) -> None:
        first = {"x": 1, "y": {"z": 2, "w": 3}}
        second = {"y": {"w": 3, "z": 2}, "x": 1}
        self.assertEqual(
            contracts.canonical_json_bytes(first),
            contracts.canonical_json_bytes(second),
        )

    def test_nonfinite_values_cannot_be_serialized(self) -> None:
        expect_error(
            self, "non-json-value", contracts.canonical_json_bytes, float("inf")
        )
        expect_error(
            self, "non-json-value", contracts.canonical_json_bytes, {"x": float("nan")}
        )

    def test_resource_id_matches_independent_vector(self) -> None:
        expected = hashlib.sha256(b'["json","/a/b"]').hexdigest()
        self.assertEqual(contracts.resource_id("json", "/a/b"), expected)

    def test_operation_id_matches_independent_vector(self) -> None:
        rid = contracts.resource_id("toml", "/cfg/file.toml")
        expected = hashlib.sha256(
            f'["apply","{rid}","whole-resource"]'.encode()
        ).hexdigest()
        self.assertEqual(
            contracts.operation_id("apply", rid, "whole-resource"), expected
        )

    def test_recovery_step_id_matches_independent_vector(self) -> None:
        manifest_id = "a" * 64
        rid = contracts.resource_id("json", "/x")
        expected = hashlib.sha256(
            f'["recovery","{manifest_id}","cleanup","{rid}"]'.encode()
        ).hexdigest()
        self.assertEqual(
            contracts.recovery_step_id(manifest_id, "cleanup", rid), expected
        )

    def test_ids_are_stable_across_calls(self) -> None:
        self.assertEqual(
            contracts.resource_id("json", "/a/b"), contracts.resource_id("json", "/a/b")
        )
        self.assertNotEqual(
            contracts.resource_id("json", "/a/b"), contracts.resource_id("toml", "/a/b")
        )


class FormatBoundaryTests(unittest.TestCase):
    def manifest_with(self, mutate):
        payload = fixtures.build_manifest_payload()
        mutate(payload)
        return contracts.seal_document("manifest", payload)

    def test_timestamp_requires_timezone(self) -> None:
        def mutate(payload):
            payload["created_at"] = "2026-09-18T01:00:00"

        expect_error(self, "schema-violation", self.manifest_with, mutate)

    def test_timestamp_requires_a_real_calendar_date(self) -> None:
        def mutate(payload):
            payload["created_at"] = "2026-02-31T01:00:00Z"

        expect_error(self, "schema-violation", self.manifest_with, mutate)

    def test_timestamp_with_explicit_offset_is_accepted(self) -> None:
        def mutate(payload):
            payload["created_at"] = "2026-09-18T09:00:00+08:00"

        self.manifest_with(mutate)

    def test_paths_must_be_normalized_and_absolute(self) -> None:
        for bad in (
            "relative/path",
            "/private//backup",
            "/private/../x",
            "/private/backup/",
        ):
            with self.subTest(path=bad):

                def mutate(payload, bad=bad):
                    payload["backup_root"] = bad

                expect_error(self, "schema-violation", self.manifest_with, mutate)

    def test_uppercase_digest_is_rejected(self) -> None:
        def mutate(payload):
            payload["custodian"] = "custodian"
            payload["projects"][0]["shared_operation_ids"] = ["A" * 64]

        expect_error(self, "schema-violation", self.manifest_with, mutate)

    def test_unknown_keys_are_rejected(self) -> None:
        document = fixtures.build_manifest()
        document["payload"]["unexpected"] = True
        expect_error(
            self, "schema-violation", contracts.validate_document, document, "manifest"
        )

    def test_unknown_enum_is_rejected(self) -> None:
        def mutate(payload):
            payload["projects"][0]["platforms"] = ["trellis"]

        expect_error(self, "schema-violation", self.manifest_with, mutate)


class PublicationDecisionTests(unittest.TestCase):
    def decisions_with(self, mutate):
        items = fixtures.build_publication_items()
        mutate(items)
        return contracts.validate_document(
            {"schema_version": 1, "items": items}, "publication_decisions"
        )

    def test_valid_decisions_pass(self) -> None:
        self.decisions_with(lambda items: None)
        contracts.validate_document(
            {"schema_version": 1, "items": []}, "publication_decisions"
        )

    def test_approval_scope_drift_is_rejected(self) -> None:
        def mutate(items):
            items[0]["approval"]["scope"]["target_path"] = (
                "/private/home/shared/other.md"
            )

        expect_error(self, "semantic-violation", self.decisions_with, mutate)

    def test_approval_scope_must_keep_exact_structure(self) -> None:
        def mutate(items):
            items[0]["approval"]["scope"] = {"decision": "share"}

        expect_error(self, "schema-violation", self.decisions_with, mutate)

    def test_duplicate_item_id_is_rejected(self) -> None:
        def mutate(items):
            clone = copy.deepcopy(items[0])
            clone["target_path"] = "/private/home/shared/second.md"
            clone["approval"]["scope"]["target_path"] = "/private/home/shared/second.md"
            items.append(clone)

        expect_error(self, "semantic-violation", self.decisions_with, mutate)

    def test_duplicate_sources_within_one_item_are_rejected(self) -> None:
        def mutate(items):
            extra = copy.deepcopy(items[0]["sources"][0])
            items[0]["sources"].append(extra)
            items[0]["approval"]["scope"]["sources"].append(copy.deepcopy(extra))

        expect_error(self, "semantic-violation", self.decisions_with, mutate)

    def test_duplicate_targets_across_items_are_rejected(self) -> None:
        def mutate(items):
            clone = copy.deepcopy(items[0])
            clone["item_id"] = "second"
            items.append(clone)

        expect_error(self, "semantic-violation", self.decisions_with, mutate)

    def test_parent_child_target_overlap_is_rejected(self) -> None:
        def mutate(items):
            clone = copy.deepcopy(items[0])
            clone["item_id"] = "second"
            clone["target_path"] = str(Path(items[0]["target_path"]).parent)
            clone["approval"]["scope"]["target_path"] = clone["target_path"]
            items.append(clone)

        expect_error(self, "semantic-violation", self.decisions_with, mutate)

    def test_private_only_must_keep_null_target_and_candidate(self) -> None:
        def mutate(items):
            items[1]["candidate_ref"] = fixtures._file_ref("/private/candidates/x", 90)
            items[1]["approval"]["scope"]["candidate_ref"] = fixtures._file_ref(
                "/private/candidates/x", 90
            )

        expect_error(self, "schema-violation", self.decisions_with, mutate)


class ManifestSemanticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = fixtures.build_manifest()

    def test_valid_manifest_passes(self) -> None:
        contracts.validate_document(self.manifest, "manifest")

    def test_forged_manifest_id_is_rejected_with_exit_three(self) -> None:
        document = copy.deepcopy(self.manifest)
        document["manifest_id"] = ZERO_DIGEST
        error = expect_error(
            self, "id-mismatch", contracts.validate_document, document, "manifest"
        )
        self.assertEqual(error.exit_code, 3)

    def test_forged_operation_id_is_rejected(self) -> None:
        def mutate(payload):
            payload["projects"][0]["private_operations"][0]["operation_id"] = (
                ZERO_DIGEST
            )

        error = expect_error(
            self, "id-mismatch", reseal, "manifest", self.manifest, mutate
        )
        self.assertEqual(error.exit_code, 3)

    def test_forged_resource_id_is_rejected(self) -> None:
        def mutate(payload):
            payload["projects"][0]["private_operations"][0]["resource_id"] = ZERO_DIGEST

        expect_error(self, "id-mismatch", reseal, "manifest", self.manifest, mutate)

    def test_resource_cannot_have_two_private_owners(self) -> None:
        def mutate(payload):
            operation = fixtures.build_operation("r1", "apply")
            operation["selector"] = "second-owner"
            operation["operation_id"] = contracts.operation_id(
                "apply", operation["resource_id"], "second-owner"
            )
            operation["dependent_projects"] = [fixtures.BETA]
            payload["projects"][1]["private_operations"].append(operation)

        expect_error(
            self, "semantic-violation", reseal, "manifest", self.manifest, mutate
        )

    def test_resource_cannot_be_both_private_and_shared(self) -> None:
        def mutate(payload):
            operation = copy.deepcopy(payload["shared_operations"][0])
            operation["dependent_projects"] = [fixtures.ALPHA]
            payload["projects"][0]["private_operations"].append(operation)

        expect_error(
            self, "semantic-violation", reseal, "manifest", self.manifest, mutate
        )

    def test_duplicate_operation_id_is_rejected(self) -> None:
        def mutate(payload):
            operation = copy.deepcopy(payload["projects"][1]["private_operations"][0])
            operation["dependent_projects"] = [fixtures.BETA]
            payload["projects"][1]["private_operations"].append(operation)

        expect_error(
            self, "semantic-violation", reseal, "manifest", self.manifest, mutate
        )

    def test_phase_after_must_reference_an_earlier_phase(self) -> None:
        def mutate(payload):
            operation = payload["projects"][0]["private_operations"][1]
            operation["before_requirement"] = {
                "kind": "phase-after",
                "phase": "deploy",
                "resource_id": operation["resource_id"],
            }

        expect_error(
            self, "semantic-violation", reseal, "manifest", self.manifest, mutate
        )

    def test_phase_after_must_reference_the_same_resource(self) -> None:
        def mutate(payload):
            operation = payload["projects"][0]["private_operations"][1]
            operation["before_requirement"] = {
                "kind": "phase-after",
                "phase": "apply",
                "resource_id": fixtures.resource_id_of("r2"),
            }

        expect_error(
            self, "semantic-violation", reseal, "manifest", self.manifest, mutate
        )

    def test_shared_reverse_dependency_set_must_match(self) -> None:
        def mutate(payload):
            s1_apply = fixtures.operations_of("s1")["apply"]["operation_id"]
            payload["projects"][1]["shared_operation_ids"] = [
                op_id
                for op_id in payload["projects"][1]["shared_operation_ids"]
                if op_id != s1_apply
            ]

        expect_error(
            self, "semantic-violation", reseal, "manifest", self.manifest, mutate
        )

    def test_unknown_shared_operation_reference_is_rejected(self) -> None:
        def mutate(payload):
            payload["projects"][0]["shared_operation_ids"].append(ZERO_DIGEST)

        expect_error(
            self, "semantic-violation", reseal, "manifest", self.manifest, mutate
        )

    def test_dependent_projects_must_be_sorted(self) -> None:
        def mutate(payload):
            payload["shared_operations"][0]["dependent_projects"] = [
                fixtures.BETA,
                fixtures.ALPHA,
            ]

        expect_error(
            self, "semantic-violation", reseal, "manifest", self.manifest, mutate
        )


class StageReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = fixtures.build_manifest()
        cls.apply_receipt = fixtures.build_apply_receipt(cls.manifest)
        cls.deployment = fixtures.build_deployment_evidence(
            cls.manifest, cls.apply_receipt
        )

    def test_valid_receipts_pass(self) -> None:
        contracts.validate_document(self.apply_receipt, "apply_receipt")
        contracts.validate_document(self.deployment, "deployment_evidence")

    def test_duplicate_phase_resource_result_is_rejected(self) -> None:
        def mutate(payload):
            payload["projects"][0]["private_results"].append(
                copy.deepcopy(payload["projects"][0]["private_results"][0])
            )

        expect_error(
            self,
            "semantic-violation",
            reseal,
            "apply_receipt",
            self.apply_receipt,
            mutate,
        )

    def test_absent_before_state_cannot_carry_a_backup(self) -> None:
        def mutate(payload):
            payload["projects"][0]["private_results"][0]["before"] = dict(
                fixtures.ABSENT
            )

        expect_error(
            self,
            "semantic-violation",
            reseal,
            "apply_receipt",
            self.apply_receipt,
            mutate,
        )

    def test_failed_result_requires_an_error(self) -> None:
        def mutate(payload):
            result = payload["projects"][0]["private_results"][0]
            result["status"] = "failed"
            result["error"] = None

        expect_error(
            self,
            "schema-violation",
            reseal,
            "apply_receipt",
            self.apply_receipt,
            mutate,
        )

    def test_temporal_order_is_enforced(self) -> None:
        def mutate(payload):
            payload["started_at"] = fixtures.T2
            payload["finished_at"] = fixtures.T1

        expect_error(
            self,
            "semantic-violation",
            reseal,
            "apply_receipt",
            self.apply_receipt,
            mutate,
        )

    def test_status_must_match_project_aggregation(self) -> None:
        def mutate(payload):
            payload["status"] = "already-complete"

        expect_error(
            self,
            "semantic-violation",
            reseal,
            "apply_receipt",
            self.apply_receipt,
            mutate,
        )

    def test_result_phase_must_match_the_receipt_stage(self) -> None:
        def mutate(payload):
            payload["projects"][0]["private_results"][0]["phase"] = "deploy"

        expect_error(
            self,
            "semantic-violation",
            reseal,
            "apply_receipt",
            self.apply_receipt,
            mutate,
        )

    def test_deployment_evidence_rejects_apply_phase_results(self) -> None:
        def mutate(payload):
            payload["projects"][0]["private_results"] = [
                fixtures.build_resource_result("r1", "apply")
            ]

        expect_error(
            self,
            "semantic-violation",
            reseal,
            "deployment_evidence",
            self.deployment,
            mutate,
        )


class RecoveryPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = fixtures.build_manifest()
        cls.apply_receipt = fixtures.build_apply_receipt(cls.manifest)
        cls.deployment = fixtures.build_deployment_evidence(
            cls.manifest, cls.apply_receipt
        )
        cls.verification = fixtures.build_verification(
            cls.manifest, cls.apply_receipt, cls.deployment
        )
        cls.cleanup = fixtures.build_cleanup_receipt(
            cls.manifest, cls.apply_receipt, cls.deployment, cls.verification
        )
        cls.plan = fixtures.build_recovery_plan(
            cls.manifest, cls.apply_receipt, cls.deployment, cls.cleanup
        )

    def test_valid_plan_passes(self) -> None:
        contracts.validate_document(self.plan, "recovery_plan")

    def test_blocked_plan_records_conflicts(self) -> None:
        def blocked(payload):
            payload["status"] = "blocked"
            payload["conflicts"] = ["shared closure is incomplete"]

        contracts.validate_document(
            reseal("recovery_plan", self.plan, blocked), "recovery_plan"
        )

        def no_conflicts(payload):
            payload["status"] = "blocked"

        expect_error(
            self, "semantic-violation", reseal, "recovery_plan", self.plan, no_conflicts
        )

    def test_steps_must_follow_inverse_phase_order(self) -> None:
        def mutate(payload):
            steps = payload["steps"]
            cleanup_index = next(
                i for i, s in enumerate(steps) if s["phase"] == "cleanup"
            )
            deploy_index = next(
                i for i, s in enumerate(steps) if s["phase"] == "deploy"
            )
            steps[cleanup_index], steps[deploy_index] = (
                steps[deploy_index],
                steps[cleanup_index],
            )

        expect_error(
            self, "semantic-violation", reseal, "recovery_plan", self.plan, mutate
        )

    def test_state_chain_must_hold_per_resource(self) -> None:
        def mutate(payload):
            for step in payload["steps"]:
                if step["phase"] == "deploy" and step[
                    "resource_id"
                ] == fixtures.resource_id_of("r1"):
                    step["expected_current"] = fixtures.file_state(99)

        expect_error(
            self, "semantic-violation", reseal, "recovery_plan", self.plan, mutate
        )

    def test_unknown_or_forward_dependencies_are_rejected(self) -> None:
        def unknown(payload):
            payload["steps"][0]["depends_on"] = [ZERO_DIGEST]

        expect_error(
            self, "semantic-violation", reseal, "recovery_plan", self.plan, unknown
        )

        def forward(payload):
            cleanup_step = payload["steps"][0]
            deploy_step = next(
                step
                for step in payload["steps"]
                if step["phase"] == "deploy"
                and step["resource_id"] == cleanup_step["resource_id"]
            )
            cleanup_step["depends_on"] = [deploy_step["step_id"]]

        expect_error(
            self, "semantic-violation", reseal, "recovery_plan", self.plan, forward
        )

    def test_shared_step_operations_must_be_listed(self) -> None:
        def mutate(payload):
            s1_apply = fixtures.operations_of("s1")["apply"]["operation_id"]
            payload["shared_operation_ids"] = [
                op_id for op_id in payload["shared_operation_ids"] if op_id != s1_apply
            ]

        expect_error(
            self, "semantic-violation", reseal, "recovery_plan", self.plan, mutate
        )

    def test_step_id_must_match_canonical_digest(self) -> None:
        def mutate(payload):
            payload["steps"][0]["step_id"] = ZERO_DIGEST

        error = expect_error(
            self, "id-mismatch", reseal, "recovery_plan", self.plan, mutate
        )
        self.assertEqual(error.exit_code, 3)


class RecoveryReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = fixtures.build_manifest()
        cls.apply_receipt = fixtures.build_apply_receipt(cls.manifest)
        cls.deployment = fixtures.build_deployment_evidence(
            cls.manifest, cls.apply_receipt
        )
        cls.verification = fixtures.build_verification(
            cls.manifest, cls.apply_receipt, cls.deployment
        )
        cls.cleanup = fixtures.build_cleanup_receipt(
            cls.manifest, cls.apply_receipt, cls.deployment, cls.verification
        )
        cls.plan = fixtures.build_recovery_plan(
            cls.manifest, cls.apply_receipt, cls.deployment, cls.cleanup
        )
        cls.receipt = fixtures.build_recovery_receipt(
            cls.manifest, cls.apply_receipt, cls.deployment, cls.cleanup, cls.plan
        )

    def test_valid_receipt_passes(self) -> None:
        contracts.validate_document(self.receipt, "recovery_receipt")

    def test_step_cannot_be_completed_and_pending(self) -> None:
        def mutate(payload):
            payload["pending_step_ids"] = [payload["completed_step_ids"][0]]

        expect_error(
            self, "semantic-violation", reseal, "recovery_receipt", self.receipt, mutate
        )

    def test_shared_results_must_group_multi_project_steps(self) -> None:
        def mutate(payload):
            payload["shared_results"] = []

        expect_error(
            self, "semantic-violation", reseal, "recovery_receipt", self.receipt, mutate
        )

    def test_completed_steps_need_succeeded_results(self) -> None:
        def mutate(payload):
            result = payload["results"][0]
            result["status"] = "failed"
            result["error"] = "write failed"

        expect_error(
            self, "semantic-violation", reseal, "recovery_receipt", self.receipt, mutate
        )

    def test_absent_before_state_cannot_carry_protection(self) -> None:
        def mutate(payload):
            result = payload["results"][0]
            result["protection_ref"] = {
                "path": "/private/migration/protection/x",
                "state": fixtures.file_state(77),
            }

        expect_error(
            self, "semantic-violation", reseal, "recovery_receipt", self.receipt, mutate
        )


class DeclaredBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.family = fixtures.build_fixture_family()

    def documents(self):
        return {
            kind: copy.deepcopy(self.family[kind])
            for kind in (
                "apply_receipt",
                "deployment_evidence",
                "verification",
                "cleanup_receipt",
                "recovery_plan",
                "recovery_receipt",
            )
        }

    def test_full_family_binds_with_raw_bytes(self) -> None:
        supplied = contracts.validate_declared_bindings(
            self.family["manifest"],
            self.documents(),
            fixtures.fixture_raw_documents(self.family),
        )
        self.assertEqual(set(supplied), set(self.documents()))

    def test_bindings_hold_without_raw_bytes(self) -> None:
        contracts.validate_declared_bindings(self.family["manifest"], self.documents())

    def test_absent_stage_documents_are_not_inferred(self) -> None:
        contracts.validate_declared_bindings(
            self.family["manifest"], {"apply_receipt": self.family["apply_receipt"]}
        )

    def test_tampered_raw_bytes_fail_closed(self) -> None:
        raw = fixtures.fixture_raw_documents(self.family)
        raw["deployment_evidence"] = b"{}"
        error = expect_error(
            self,
            "binding-violation",
            contracts.validate_declared_bindings,
            self.family["manifest"],
            self.documents(),
            raw,
        )
        self.assertEqual(error.exit_code, 3)

    def test_successful_stage_requires_complete_private_coverage(self) -> None:
        receipt = reseal(
            "apply_receipt",
            self.family["apply_receipt"],
            lambda payload: payload["projects"][0]["private_results"].pop(0),
        )
        expect_error(
            self,
            "binding-violation",
            contracts.validate_declared_bindings,
            self.family["manifest"],
            {"apply_receipt": receipt},
        )

    def test_partial_receipt_may_omit_unfinished_resources(self) -> None:
        def mutate(payload):
            payload["status"] = "failed"
            alpha = payload["projects"][0]
            alpha["status"] = "failed"
            alpha["reason"] = "shared dependency failed"
            alpha["nextStep"] = "resolve the shared failure and retry"
            alpha["private_results"] = [
                fixtures.build_resource_result("r1", "apply", "failed", "write failed")
            ]
            payload["projects"][1]["status"] = "failed"
            payload["projects"][1]["reason"] = "blocked by batch"
            payload["projects"][1]["nextStep"] = "retry after unblock"
            payload["projects"][1]["private_results"] = []
            payload["shared_results"] = [
                fixtures.build_resource_result("s1", "apply", "failed", "write failed")
            ]

        partial = reseal("apply_receipt", self.family["apply_receipt"], mutate)
        contracts.validate_declared_bindings(
            self.family["manifest"], {"apply_receipt": partial}
        )

    def test_result_operation_ids_must_match_the_declared_set(self) -> None:
        def add_second_apply_entry(payload):
            operation = fixtures.build_operation("r1", "apply")
            operation["selector"] = "second-entry"
            operation["operation_id"] = contracts.operation_id(
                "apply", operation["resource_id"], "second-entry"
            )
            payload["projects"][0]["private_operations"].append(operation)

        manifest = reseal("manifest", self.family["manifest"], add_second_apply_entry)
        receipt_payload = fixtures.build_apply_receipt_payload(manifest)
        receipt = contracts.seal_document("apply_receipt", receipt_payload)
        expect_error(
            self,
            "binding-violation",
            contracts.validate_declared_bindings,
            manifest,
            {"apply_receipt": receipt},
        )

    def test_cleanup_must_bind_the_current_verification(self) -> None:
        cleanup = reseal(
            "cleanup_receipt",
            self.family["cleanup_receipt"],
            lambda payload: payload.update({"verification_id": ZERO_DIGEST}),
        )
        expect_error(
            self,
            "binding-violation",
            contracts.validate_declared_bindings,
            self.family["manifest"],
            {
                "verification": self.family["verification"],
                "cleanup_receipt": cleanup,
            },
        )

    def test_recovery_receipt_must_match_the_plan(self) -> None:
        receipt = reseal(
            "recovery_receipt",
            self.family["recovery_receipt"],
            lambda payload: payload["results"][0].update(
                {"operation_ids": [ZERO_DIGEST]}
            ),
        )
        expect_error(
            self,
            "binding-violation",
            contracts.validate_declared_bindings,
            self.family["manifest"],
            {
                "recovery_plan": self.family["recovery_plan"],
                "recovery_receipt": receipt,
            },
        )

    def test_unknown_binding_kind_is_rejected(self) -> None:
        expect_error(
            self,
            "unknown-kind",
            contracts.validate_declared_bindings,
            self.family["manifest"],
            {"manifest": self.family["manifest"]},
        )


class CumulativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = fixtures.build_manifest()
        cls.full_receipt = fixtures.build_apply_receipt(cls.manifest)

    def partial_receipt(self):
        def mutate(payload):
            payload["status"] = "failed"
            alpha = payload["projects"][0]
            alpha["status"] = "failed"
            alpha["reason"] = "r2 write failed"
            alpha["nextStep"] = "retry the failed resources"
            alpha["private_results"] = [
                fixtures.build_resource_result("r1", "apply"),
                fixtures.build_resource_result("r2", "apply", "failed", "write failed"),
            ]
            retryable = alpha["private_results"][1]
            retryable["before"] = fixtures.resource_state("r2", "orig")
            retryable["after"] = fixtures.resource_state("r2", "orig")
            retryable["backup_ref"] = fixtures.backup_ref_of("r2", "orig")

        return reseal("apply_receipt", self.full_receipt, mutate)

    def retry_receipt(self, previous):
        payload = fixtures.build_apply_receipt_payload(self.manifest)
        payload["previous_receipt_id"] = previous["apply_id"]
        return contracts.seal_document("apply_receipt", payload)

    def test_retry_preserving_previous_successes_passes(self) -> None:
        previous = self.partial_receipt()
        current = self.retry_receipt(previous)
        contracts.validate_cumulative(previous, current, "apply_receipt")

    def test_dropping_a_previous_success_is_rejected(self) -> None:
        previous = self.partial_receipt()
        current = reseal(
            "apply_receipt",
            self.retry_receipt(previous),
            lambda payload: payload["projects"][0]["private_results"].pop(0),
        )
        error = expect_error(
            self,
            "cumulative-violation",
            contracts.validate_cumulative,
            previous,
            current,
            "apply_receipt",
        )
        self.assertEqual(error.exit_code, 3)

    def test_original_backup_reference_must_survive(self) -> None:
        previous = self.partial_receipt()

        def mutate(payload):
            payload["projects"][0]["private_results"][0]["backup_ref"] = {
                "path": "/private/backup/replaced",
                "state": fixtures.file_state(11),
            }

        current = reseal("apply_receipt", self.retry_receipt(previous), mutate)
        expect_error(
            self,
            "cumulative-violation",
            contracts.validate_cumulative,
            previous,
            current,
            "apply_receipt",
        )

    def test_retry_must_reference_the_supplied_previous_receipt(self) -> None:
        previous = self.partial_receipt()
        current = self.retry_receipt(self.full_receipt)
        expect_error(
            self,
            "cumulative-violation",
            contracts.validate_cumulative,
            previous,
            current,
            "apply_receipt",
        )

    def test_first_run_must_declare_a_null_previous_reference(self) -> None:
        contracts.validate_cumulative(None, self.full_receipt, "apply_receipt")
        expect_error(
            self,
            "cumulative-violation",
            contracts.validate_cumulative,
            None,
            self.retry_receipt(self.full_receipt),
            "apply_receipt",
        )

    def test_recovery_receipt_retry_keeps_completed_steps(self) -> None:
        family = fixtures.build_fixture_family()
        receipt = family["recovery_receipt"]
        payload = copy.deepcopy(receipt["payload"])
        keep = sorted(
            step["step_id"] for step in family["recovery_plan"]["payload"]["steps"][:6]
        )
        payload["completed_step_ids"] = keep
        payload["pending_step_ids"] = [
            step_id
            for step_id in receipt["payload"]["completed_step_ids"]
            if step_id not in keep
        ]
        payload["results"] = [r for r in payload["results"] if r["step_id"] in keep]
        payload["shared_results"] = [
            {
                **shared,
                "step_ids": [s for s in shared["step_ids"] if s in keep],
            }
            for shared in payload["shared_results"]
        ]
        payload["shared_results"] = [
            s for s in payload["shared_results"] if s["step_ids"]
        ]
        payload["status"] = "failed"
        payload["reason"] = "later step failed"
        payload["runtime_readiness"] = "not-verified"
        payload["report_refs"] = []
        payload["projects"][0]["status"] = "failed"
        payload["projects"][0]["reason"] = "later step failed"
        payload["projects"][0]["nextStep"] = "retry the plan"
        payload["projects"][1]["status"] = "failed"
        payload["projects"][1]["reason"] = "later step failed"
        payload["projects"][1]["nextStep"] = "retry the plan"
        partial = contracts.seal_document("recovery_receipt", payload)

        retry_payload = copy.deepcopy(receipt["payload"])
        retry_payload["previous_receipt_id"] = partial["receipt_id"]
        retry = contracts.seal_document("recovery_receipt", retry_payload)
        contracts.validate_cumulative(partial, retry, "recovery_receipt")

        retry_payload = copy.deepcopy(partial["payload"])
        retry_payload["previous_receipt_id"] = partial["receipt_id"]
        lost_step = keep[0]
        retry_payload["completed_step_ids"].remove(lost_step)
        retry_payload["pending_step_ids"].append(lost_step)
        retry_payload["results"] = [
            result
            for result in retry_payload["results"]
            if result["step_id"] != lost_step
        ]
        retry_payload["shared_results"] = [
            {
                **shared,
                "step_ids": [
                    step_id for step_id in shared["step_ids"] if step_id != lost_step
                ],
            }
            for shared in retry_payload["shared_results"]
        ]
        retry_payload["shared_results"] = [
            shared for shared in retry_payload["shared_results"] if shared["step_ids"]
        ]
        broken = contracts.seal_document("recovery_receipt", retry_payload)
        expect_error(
            self,
            "cumulative-violation",
            contracts.validate_cumulative,
            partial,
            broken,
            "recovery_receipt",
        )


class EnvelopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.family = fixtures.build_fixture_family()

    def test_every_phase_envelope_in_the_family_is_valid(self) -> None:
        for name in (
            "migration_envelope_plan",
            "migration_envelope_apply",
            "migration_envelope_verify",
            "migration_envelope_cleanup",
        ):
            with self.subTest(name=name):
                contracts.validate_document(self.family[name], "migration_envelope")
        for name in ("recovery_envelope_plan", "recovery_envelope_apply"):
            with self.subTest(name=name):
                contracts.validate_document(self.family[name], "recovery_envelope")

    def test_blocked_envelope_has_honest_null_ids_and_empty_artifact(self) -> None:
        envelope = contracts.make_envelope(
            "migration",
            "plan",
            "blocked",
            [],
            "publication decisions failed validation",
            "fix the decisions file and rerun plan",
        )
        self.assertEqual(envelope["migration"], {})
        self.assertIsNone(envelope["manifest_id"])
        contracts.validate_document(envelope, "migration_envelope")

    def test_blocked_envelope_requires_an_explanation(self) -> None:
        expect_error(
            self,
            "semantic-violation",
            contracts.make_envelope,
            "migration",
            "plan",
            "blocked",
            [],
            "",
            "",
        )

    def test_envelope_ids_must_match_the_artifact(self) -> None:
        expect_error(
            self,
            "semantic-violation",
            contracts.make_envelope,
            "migration",
            "plan",
            "planned",
            fixtures.envelope_projects("planned"),
            "",
            "",
            artifact=self.family["manifest"],
            identifiers={"manifest_id": ZERO_DIGEST},
        )

    def test_envelope_scope_must_match_the_artifact(self) -> None:
        expect_error(
            self,
            "semantic-violation",
            contracts.make_envelope,
            "migration",
            "apply",
            "applied",
            [fixtures.envelope_projects("applied")[0]],
            "",
            "",
            artifact=self.family["apply_receipt"],
            identifiers={"manifest_id": self.family["manifest"]["manifest_id"]},
        )

    def test_project_status_must_fit_the_phase(self) -> None:
        expect_error(
            self,
            "semantic-violation",
            contracts.make_envelope,
            "migration",
            "plan",
            "planned",
            fixtures.envelope_projects("restored"),
            "",
            "",
            artifact=self.family["manifest"],
            identifiers={"manifest_id": self.family["manifest"]["manifest_id"]},
        )

    def test_unexpected_identifier_keys_are_rejected(self) -> None:
        expect_error(
            self,
            "unknown-kind",
            contracts.make_envelope,
            "migration",
            "plan",
            "blocked",
            [],
            "reason",
            "next",
            identifiers={"plan_id": ZERO_DIGEST},
        )


class DeploymentResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.family = fixtures.build_fixture_family()

    def test_null_result_is_accepted(self) -> None:
        self.assertIsNone(contracts.validate_deployment_result(None))

    def test_complete_result_is_accepted(self) -> None:
        result = {
            "path": "/private/migration/deployment_evidence.json",
            "evidence": self.family["deployment_evidence"],
        }
        self.assertIs(contracts.validate_deployment_result(result), result)

    def test_result_requires_path_and_valid_evidence(self) -> None:
        expect_error(
            self,
            "schema-violation",
            contracts.validate_deployment_result,
            {"evidence": self.family["deployment_evidence"]},
        )
        broken = copy.deepcopy(self.family["deployment_evidence"])
        broken["deployment_id"] = ZERO_DIGEST
        expect_error(
            self,
            "id-mismatch",
            contracts.validate_deployment_result,
            {"path": "/private/migration/e.json", "evidence": broken},
        )


class JsonWriterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.family = fixtures.build_fixture_family()

    def write(self, value) -> str:
        stream = io.StringIO()
        contracts.write_json_response(value, stream)
        return stream.getvalue()

    def test_writer_emits_exactly_one_json_root(self) -> None:
        envelope = self.family["migration_envelope_plan"]
        output = self.write(envelope)
        self.assertTrue(output.endswith("\n"))
        self.assertEqual(output.count("\n"), 1)
        self.assertEqual(json.loads(output), json.loads(json.dumps(envelope)))

    def test_writer_validates_fixed_envelopes(self) -> None:
        broken = copy.deepcopy(self.family["migration_envelope_plan"])
        broken["manifest_id"] = ZERO_DIGEST
        expect_error(self, "semantic-violation", self.write, broken)

    def test_retired_trellis_fields_are_refused_not_aliased(self) -> None:
        for field in ("trellis", "trellisInit", "trellisProjectSetup"):
            with self.subTest(field=field):
                expect_error(
                    self, "retired-field", self.write, {field: {"status": "success"}}
                )

    def test_pass_through_payloads_keep_their_fields_and_numbers(self) -> None:
        payload = {"sbtdInit": {"status": "success", "projects": 2, "ratio": 0.5}}
        output = self.write(payload)
        decoded = json.loads(output)
        self.assertEqual(set(decoded), {"sbtdInit"})
        self.assertEqual(decoded["sbtdInit"]["ratio"], 0.5)

    def test_writer_rejects_non_object_roots(self) -> None:
        expect_error(self, "unexpected-type", self.write, ["not", "an", "object"])


class ErrorSanitizationTests(unittest.TestCase):
    def test_schema_errors_do_not_echo_rejected_values(self) -> None:
        secret = "/private/secret-token-9f8e7d"
        items = fixtures.build_publication_items()
        items[0]["approval"]["basis"] = secret
        items[0]["approval"]["scope"]["decision"] = "invalid-decision"
        error = expect_error(
            self,
            "schema-violation",
            contracts.validate_document,
            {"schema_version": 1, "items": items},
            "publication_decisions",
        )
        self.assertNotIn(secret, str(error))
        self.assertNotIn("is not of type", str(error))
        self.assertNotIn("invalid-decision", str(error))

    def test_id_mismatch_does_not_leak_digests(self) -> None:
        document = fixtures.build_manifest()
        declared = document["manifest_id"]
        forged = copy.deepcopy(document)
        forged["manifest_id"] = ZERO_DIGEST
        error = expect_error(
            self, "id-mismatch", contracts.validate_document, forged, "manifest"
        )
        self.assertNotIn(declared, str(error))
        self.assertNotIn(ZERO_DIGEST, str(error))

    def test_binding_errors_do_not_leak_digests(self) -> None:
        family = fixtures.build_fixture_family()
        raw = fixtures.fixture_raw_documents(family)
        raw["deployment_evidence"] = b"{}"
        error = expect_error(
            self,
            "binding-violation",
            contracts.validate_declared_bindings,
            family["manifest"],
            {"verification": family["verification"]},
            raw,
        )
        self.assertNotIn(
            family["verification"]["payload"]["deployment_evidence_hash"], str(error)
        )


class ValidatorAvailabilityTests(unittest.TestCase):
    def test_missing_jsonschema_fails_closed_without_breaking_pure_functions(
        self,
    ) -> None:
        module_path = (
            ROOT / "sbtd-workflow-onboard" / "scripts" / "onboard_contracts.py"
        )
        script = (
            "import importlib.util, json\n"
            "assert importlib.util.find_spec('jsonschema') is None\n"
            f"spec = importlib.util.spec_from_file_location('isolated_contracts', {str(module_path)!r})\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            "try:\n"
            "    module.validate_document({'schema_version': 1, 'items': []}, 'publication_decisions')\n"
            "except module.ContractError as error:\n"
            "    assert error.code == 'validator-unavailable' and error.exit_code == 2\n"
            "    print(json.dumps({'validator': error.code, 'canonical': module.canonical_json_bytes({'b': 2, 'a': 1}).decode()}))\n"
            "else:\n"
            "    raise AssertionError('missing dependency was accepted')\n"
        )
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-B", "-c", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {"validator": "validator-unavailable", "canonical": '{"a":1,"b":2}'},
        )


class FixtureRoundTripTests(unittest.TestCase):
    KIND_BY_FILE: ClassVar[dict[str, str]] = {
        "publication_decisions": "publication_decisions",
        "manifest": "manifest",
        "apply_receipt": "apply_receipt",
        "deployment_evidence": "deployment_evidence",
        "verification": "verification",
        "cleanup_receipt": "cleanup_receipt",
        "recovery_plan": "recovery_plan",
        "recovery_receipt": "recovery_receipt",
        "migration_envelope_plan": "migration_envelope",
        "migration_envelope_apply": "migration_envelope",
        "migration_envelope_verify": "migration_envelope",
        "migration_envelope_cleanup": "migration_envelope",
        "recovery_envelope_plan": "recovery_envelope",
        "recovery_envelope_apply": "recovery_envelope",
    }

    def test_serialized_family_round_trips_through_load_document(self) -> None:
        with tempfile.TemporaryDirectory(prefix="onboard-contract-fixtures-") as tmp:
            written = fixtures.write_fixture_family(Path(tmp))
            self.assertEqual(set(written), set(self.KIND_BY_FILE))
            loaded = {
                name: contracts.load_document(
                    path.read_bytes(), self.KIND_BY_FILE[name]
                )
                for name, path in written.items()
            }
            raw = {
                kind: written[kind].read_bytes()
                for kind in (
                    "manifest",
                    "apply_receipt",
                    "deployment_evidence",
                    "cleanup_receipt",
                )
            }
            contracts.validate_declared_bindings(
                loaded["manifest"],
                {
                    kind: loaded[kind]
                    for kind in (
                        "apply_receipt",
                        "deployment_evidence",
                        "verification",
                        "cleanup_receipt",
                        "recovery_plan",
                        "recovery_receipt",
                    )
                },
                raw,
            )
            # File bytes are exactly the canonical bytes used for raw bindings.
            evidence_hash = hashlib.sha256(
                written["deployment_evidence"].read_bytes()
            ).hexdigest()
            self.assertEqual(
                loaded["verification"]["payload"]["deployment_evidence_hash"],
                evidence_hash,
            )


class ExplicitInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.family = fixtures.build_fixture_family()

    def test_required_projection_cannot_be_private_only(self) -> None:
        document = fixtures.build_publication_decisions()
        document["items"][1]["required"] = True
        with self.assertRaises(ContractError):
            contracts.validate_document(document, "publication_decisions")

    def test_non_adjacent_ancestor_targets_are_rejected(self) -> None:
        seed = fixtures.build_publication_items()[0]
        items = []
        for index, target in enumerate(
            ("/shared/a", "/shared/a-other", "/shared/a/child")
        ):
            item = copy.deepcopy(seed)
            item["item_id"] = f"projection-{index}"
            item["target_path"] = target
            item["approval"]["scope"]["target_path"] = target
            items.append(item)
        with self.assertRaises(ContractError):
            contracts.validate_document(
                {"schema_version": 1, "items": items}, "publication_decisions"
            )

    def test_successful_result_requires_its_original_before_backup(self) -> None:
        for backup in (None, fixtures._file_ref("/private/backup/wrong", 999)):
            with self.subTest(backup_missing=backup is None):
                payload = copy.deepcopy(self.family["apply_receipt"]["payload"])
                payload["projects"][0]["private_results"][0]["backup_ref"] = backup
                with self.assertRaises(ContractError):
                    contracts.seal_document("apply_receipt", payload)

    def test_recovery_restore_requires_a_matching_backup(self) -> None:
        for backup in (None, fixtures._file_ref("/private/backup/wrong", 999)):
            with self.subTest(backup_missing=backup is None):
                payload = copy.deepcopy(self.family["recovery_plan"]["payload"])
                payload["steps"][0]["backup_ref"] = backup
                with self.assertRaises(ContractError):
                    contracts.seal_document("recovery_plan", payload)

    def test_phase_after_requires_a_declared_predecessor(self) -> None:
        payload = copy.deepcopy(self.family["manifest"]["payload"])
        resource = fixtures.resource_id_of("r1")
        payload["projects"][0]["private_operations"] = [
            operation
            for operation in payload["projects"][0]["private_operations"]
            if not (
                operation["resource_id"] == resource and operation["phase"] == "apply"
            )
        ]
        with self.assertRaises(ContractError):
            contracts.seal_document("manifest", payload)

    def test_same_target_cannot_claim_conflicting_owner_formats(self) -> None:
        payload = copy.deepcopy(self.family["manifest"]["payload"])
        operation = copy.deepcopy(payload["projects"][0]["private_operations"][0])
        operation["owner_kind"] = "toml"
        operation["resource_id"] = contracts.resource_id("toml", operation["target"])
        operation["operation_id"] = contracts.operation_id(
            operation["phase"], operation["resource_id"], operation["selector"]
        )
        payload["projects"][0]["private_operations"].append(operation)
        with self.assertRaises(ContractError):
            contracts.seal_document("manifest", payload)

    def test_private_operation_cannot_target_another_project(self) -> None:
        payload = copy.deepcopy(self.family["manifest"]["payload"])
        operation = copy.deepcopy(payload["projects"][0]["private_operations"][0])
        operation["target"] = fixtures.BETA + "/foreign.json"
        operation["resource_id"] = contracts.resource_id(
            operation["owner_kind"], operation["target"]
        )
        operation["operation_id"] = contracts.operation_id(
            operation["phase"], operation["resource_id"], operation["selector"]
        )
        payload["projects"][0]["private_operations"] = [operation]
        with self.assertRaises(ContractError):
            contracts.seal_document("manifest", payload)

    def test_backup_root_cannot_be_inside_a_selected_project(self) -> None:
        payload = copy.deepcopy(self.family["manifest"]["payload"])
        payload["backup_root"] = fixtures.ALPHA + "/.sbtd/backups"
        with self.assertRaises(ContractError):
            contracts.seal_document("manifest", payload)

    def test_recovery_snapshot_must_match_the_first_inverse_step(self) -> None:
        payload = copy.deepcopy(self.family["recovery_plan"]["payload"])
        payload["resources"][0]["state"] = fixtures.file_state(999)
        with self.assertRaises(ContractError):
            contracts.seal_document("recovery_plan", payload)

    def test_raw_bytes_cannot_describe_a_different_supplied_record(self) -> None:
        payload = copy.deepcopy(self.family["apply_receipt"]["payload"])
        payload["finished_at"] = fixtures.T9
        other = contracts.seal_document("apply_receipt", payload)
        self.assertNotEqual(other["apply_id"], self.family["apply_receipt"]["apply_id"])
        with self.assertRaises(ContractError):
            contracts.validate_declared_bindings(
                self.family["manifest"],
                {"apply_receipt": self.family["apply_receipt"]},
                {"apply_receipt": contracts.canonical_json_bytes(other)},
            )

    def test_project_success_cannot_hide_a_failed_private_result(self) -> None:
        payload = copy.deepcopy(self.family["apply_receipt"]["payload"])
        result = payload["projects"][0]["private_results"][0]
        result["status"] = "failed"
        result["error"] = "write failed"
        with self.assertRaises(ContractError):
            contracts.seal_document("apply_receipt", payload)

    def test_unverified_deployment_still_requires_complete_operations(self) -> None:
        payload = copy.deepcopy(self.family["deployment_evidence"]["payload"])
        payload["status"] = "not-verified"
        for project in payload["projects"]:
            project["status"] = "not-verified"
            project["report_refs"] = []
        payload["projects"][0]["private_results"] = []
        document = contracts.seal_document("deployment_evidence", payload)
        with self.assertRaises(ContractError):
            contracts.validate_declared_bindings(
                self.family["manifest"], {"deployment_evidence": document}
            )

    def test_failed_attempt_cannot_replace_known_original_backup(self) -> None:
        payload = copy.deepcopy(self.family["apply_receipt"]["payload"])
        project = payload["projects"][0]
        result = project["private_results"][0]
        result["status"] = "failed"
        result["after"] = copy.deepcopy(result["before"])
        result["error"] = "write failed before target changed"
        project["status"] = "failed"
        project["reason"] = "private write failed"
        project["nextStep"] = "inspect and retry"
        payload["status"] = "failed"
        previous = contracts.seal_document("apply_receipt", payload)
        current_payload = copy.deepcopy(payload)
        current_payload["previous_receipt_id"] = previous["apply_id"]
        changed = current_payload["projects"][0]["private_results"][0]
        changed["before"] = fixtures.file_state(999)
        changed["after"] = fixtures.file_state(999)
        changed["backup_ref"] = fixtures._file_ref("/private/backup/replaced", 999)
        current = contracts.seal_document("apply_receipt", current_payload)
        with self.assertRaises(ContractError):
            contracts.validate_cumulative(previous, current, "apply_receipt")

    def test_successful_deployment_cannot_omit_report_references(self) -> None:
        payload = copy.deepcopy(self.family["deployment_evidence"]["payload"])
        payload["projects"][0]["report_refs"] = []
        with self.assertRaises(ContractError):
            contracts.seal_document("deployment_evidence", payload)

    def test_single_dependent_shared_recovery_keeps_shared_ownership(self) -> None:
        manifest_payload = copy.deepcopy(self.family["manifest"]["payload"])
        for operation in manifest_payload["shared_operations"]:
            operation["dependent_projects"] = [fixtures.ALPHA]
        manifest_payload["projects"][1]["shared_operation_ids"] = []
        for shared_root in manifest_payload["shared_roots"]:
            shared_root["dependent_projects"] = [fixtures.ALPHA]
        manifest = contracts.seal_document("manifest", manifest_payload)
        shared_resource = fixtures.resource_id_of("s1")

        plan_payload = copy.deepcopy(self.family["recovery_plan"]["payload"])
        plan_payload["manifest_id"] = manifest["manifest_id"]
        plan_payload["input_evidence"]["manifest"]["state"]["checksum"] = (
            hashlib.sha256(contracts.canonical_json_bytes(manifest)).hexdigest()
        )
        renamed_steps = {
            step["step_id"]: contracts.recovery_step_id(
                manifest["manifest_id"], step["phase"], step["resource_id"]
            )
            for step in plan_payload["steps"]
        }
        for resource in plan_payload["resources"]:
            if resource["resource_id"] == shared_resource:
                resource["dependent_projects"] = [fixtures.ALPHA]
        for step in plan_payload["steps"]:
            step["step_id"] = renamed_steps[step["step_id"]]
            step["depends_on"] = [renamed_steps[key] for key in step["depends_on"]]
            if step["resource_id"] == shared_resource:
                step["dependent_projects"] = [fixtures.ALPHA]
        plan = contracts.seal_document("recovery_plan", plan_payload)

        missing_ownership = copy.deepcopy(plan_payload)
        missing_ownership["shared_operation_ids"] = []
        bad_plan = contracts.seal_document("recovery_plan", missing_ownership)
        with self.assertRaises(ContractError):
            contracts.validate_declared_bindings(manifest, {"recovery_plan": bad_plan})

        receipt_payload = copy.deepcopy(self.family["recovery_receipt"]["payload"])
        receipt_payload["manifest_id"] = manifest["manifest_id"]
        receipt_payload["plan_id"] = plan["plan_id"]
        receipt_payload["input_evidence"] = copy.deepcopy(
            plan_payload["input_evidence"]
        )
        for result in receipt_payload["results"]:
            result["step_id"] = renamed_steps[result["step_id"]]
            if result["resource_id"] == shared_resource:
                result["dependent_projects"] = [fixtures.ALPHA]
        receipt_payload["completed_step_ids"] = [
            renamed_steps[key] for key in receipt_payload["completed_step_ids"]
        ]
        receipt_payload["shared_results"] = []
        bad_receipt = contracts.seal_document("recovery_receipt", receipt_payload)
        with self.assertRaises(ContractError):
            contracts.validate_declared_bindings(
                manifest, {"recovery_plan": plan, "recovery_receipt": bad_receipt}
            )

    def test_recovery_success_requires_preservation_completion_and_reports(
        self,
    ) -> None:
        missing_protection = copy.deepcopy(self.family["recovery_receipt"]["payload"])
        protected = next(
            result
            for result in missing_protection["results"]
            if result["before"]["type"] != "absent"
        )
        protected["protection_ref"] = None

        incomplete = copy.deepcopy(self.family["recovery_receipt"]["payload"])
        unexecuted = next(
            result
            for result in incomplete["results"]
            if result["dependent_projects"] == [fixtures.ALPHA]
        )
        incomplete["results"].remove(unexecuted)
        incomplete["completed_step_ids"].remove(unexecuted["step_id"])
        incomplete["pending_step_ids"].append(unexecuted["step_id"])

        no_reports = copy.deepcopy(self.family["recovery_receipt"]["payload"])
        no_reports["runtime_readiness"] = "verified"
        no_reports["report_refs"] = []
        for boundary, payload in (
            ("original protection", missing_protection),
            ("pending step", incomplete),
            ("runtime evidence", no_reports),
        ):
            with self.subTest(boundary=boundary), self.assertRaises(ContractError):
                contracts.seal_document("recovery_receipt", payload)

    def test_envelope_cannot_mask_failed_artifact_or_project_status(self) -> None:
        payload = copy.deepcopy(self.family["apply_receipt"]["payload"])
        payload["status"] = "failed"
        payload["projects"][0].update(
            status="failed",
            reason="verification failed",
            nextStep="inspect the project",
        )
        failed = contracts.seal_document("apply_receipt", payload)
        successful_summaries = [
            {"root": project["root"], "status": "applied", "reason": "", "nextStep": ""}
            for project in payload["projects"]
        ]
        with self.assertRaises(ContractError):
            contracts.make_envelope(
                "migration",
                "apply",
                "applied",
                successful_summaries,
                "",
                "",
                artifact=failed,
                identifiers={"manifest_id": self.family["manifest"]["manifest_id"]},
            )

        failed_summary = [
            {
                "root": fixtures.ALPHA,
                "status": "failed",
                "reason": "source inspection failed",
                "nextStep": "repair the source",
            }
        ]
        with self.assertRaises(ContractError):
            contracts.make_envelope(
                "migration",
                "plan",
                "blocked",
                failed_summary,
                "waiting for source",
                "repair the source",
            )

    def test_manifest_preserves_embedded_publication_approval_and_scope(self) -> None:
        for boundary in ("approval drift", "foreign target", "in-project candidate"):
            payload = copy.deepcopy(self.family["manifest"]["payload"])
            item = payload["publication_decisions"]["items"][0]
            if boundary == "approval drift":
                item["approval"]["scope"]["decision"] = "redact"
            elif boundary == "foreign target":
                item["target_path"] = "/private/outside/published.md"
                item["approval"]["scope"]["target_path"] = item["target_path"]
            else:
                item["candidate_ref"]["path"] = fixtures.ALPHA + "/.sbtd/candidate.md"
                item["approval"]["scope"]["candidate_ref"] = copy.deepcopy(
                    item["candidate_ref"]
                )
            with self.subTest(boundary=boundary), self.assertRaises(ContractError):
                contracts.seal_document("manifest", payload)

    def test_partial_stage_references_observed_results_and_preserves_project_truth(
        self,
    ) -> None:
        payload = copy.deepcopy(self.family["deployment_evidence"]["payload"])
        payload["status"] = "blocked"
        payload["shared_results"] = []
        for project in payload["projects"]:
            project.update(
                status="blocked",
                reason="required tool unavailable",
                nextStep="prepare the tool",
                private_results=[],
                shared_operation_ids=[],
                report_refs=[],
            )
        blocked = contracts.seal_document("deployment_evidence", payload)
        contracts.validate_declared_bindings(
            self.family["manifest"], {"deployment_evidence": blocked}
        )
        payload["projects"][0]["shared_operation_ids"] = [
            self.family["deployment_evidence"]["payload"]["projects"][0][
                "shared_operation_ids"
            ][0]
        ]
        dangling = contracts.seal_document("deployment_evidence", payload)
        with self.assertRaises(ContractError):
            contracts.validate_declared_bindings(
                self.family["manifest"], {"deployment_evidence": dangling}
            )

        mixed = copy.deepcopy(self.family["apply_receipt"]["payload"])
        mixed["status"] = "failed"
        mixed["projects"][1].update(
            status="failed",
            reason="private operation failed",
            nextStep="inspect the failure",
        )
        mixed["projects"][0]["private_results"] = []
        incomplete_success = contracts.seal_document("apply_receipt", mixed)
        with self.assertRaises(ContractError):
            contracts.validate_declared_bindings(
                self.family["manifest"], {"apply_receipt": incomplete_success}
            )

    def test_retry_cannot_switch_its_bound_stage_or_recovery_plan(self) -> None:
        for kind, id_key, previous_key, binding in (
            (
                "deployment_evidence",
                "deployment_id",
                "previous_deployment_id",
                "apply_id",
            ),
            ("cleanup_receipt", "cleanup_id", "previous_receipt_id", "verification_id"),
            ("recovery_receipt", "receipt_id", "previous_receipt_id", "plan_id"),
        ):
            previous = self.family[kind]
            payload = copy.deepcopy(previous["payload"])
            payload[previous_key] = previous[id_key]
            payload[binding] = fixtures.digest_number(999)
            self.assertNotEqual(payload[binding], previous["payload"][binding])
            current = contracts.seal_document(kind, payload)
            with self.subTest(kind=kind), self.assertRaises(ContractError):
                contracts.validate_cumulative(previous, current, kind)

    def test_successful_recovery_result_must_match_the_planned_state(self) -> None:
        payload = copy.deepcopy(self.family["recovery_receipt"]["payload"])
        payload["results"][0]["after"] = fixtures.file_state(999)
        changed = contracts.seal_document("recovery_receipt", payload)
        with self.assertRaises(ContractError):
            contracts.validate_declared_bindings(
                self.family["manifest"],
                {
                    "recovery_plan": self.family["recovery_plan"],
                    "recovery_receipt": changed,
                },
            )

    def test_recovery_result_step_reference_retains_its_stable_identity(self) -> None:
        payload = copy.deepcopy(self.family["recovery_receipt"]["payload"])
        result = next(
            result
            for result in payload["results"]
            if result["dependent_projects"] == [fixtures.ALPHA]
        )
        original = result["step_id"]
        result["step_id"] = fixtures.digest_number(999)
        payload["completed_step_ids"] = [
            result["step_id"] if key == original else key
            for key in payload["completed_step_ids"]
        ]
        with self.assertRaises(ContractError):
            contracts.seal_document("recovery_receipt", payload)


class IndependentReviewRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.family = fixtures.build_fixture_family()
        cls.manifest = cls.family["manifest"]
        cls.apply_receipt = cls.family["apply_receipt"]
        cls.deployment = cls.family["deployment_evidence"]
        cls.verification = cls.family["verification"]
        cls.cleanup = cls.family["cleanup_receipt"]
        cls.plan = cls.family["recovery_plan"]
        cls.receipt = cls.family["recovery_receipt"]

    def test_result_states_and_backups_must_match_declared_requirements(self) -> None:
        for kind in ("apply_receipt", "deployment_evidence", "cleanup_receipt"):
            payload = copy.deepcopy(self.family[kind]["payload"])
            result = payload["projects"][0]["private_results"][0]
            result["before"] = fixtures.file_state(999)
            result["backup_ref"] = copy.deepcopy(result["backup_ref"])
            result["backup_ref"]["state"] = copy.deepcopy(result["before"])
            document = contracts.seal_document(kind, payload)
            documents = {kind: document}
            if kind != "apply_receipt":
                documents["apply_receipt"] = self.apply_receipt
            if kind == "cleanup_receipt":
                documents["deployment_evidence"] = self.deployment
            with self.subTest(kind=kind), self.assertRaises(ContractError):
                contracts.validate_declared_bindings(self.manifest, documents)

    def test_partial_results_preserve_known_backup_and_protection_states(self) -> None:
        for unknown_before in (False, True):
            payload = copy.deepcopy(self.apply_receipt["payload"])
            project = payload["projects"][0]
            project.update(status="failed", reason="write failed", nextStep="inspect")
            payload["status"] = "failed"
            result = project["private_results"][0]
            result.update(status="failed", error="write failed")
            if unknown_before:
                result["before"] = None
            else:
                result["backup_ref"]["state"] = fixtures.file_state(999)
            with (
                self.subTest(unknown_before=unknown_before),
                self.assertRaises(ContractError),
            ):
                contracts.seal_document("apply_receipt", payload)

        payload = copy.deepcopy(self.receipt["payload"])
        result = next(
            result
            for result in payload["results"]
            if result["protection_ref"] is not None
        )
        result.update(status="failed", error="restore failed")
        result["protection_ref"]["state"] = fixtures.file_state(999)
        payload["completed_step_ids"].remove(result["step_id"])
        payload["pending_step_ids"].append(result["step_id"])
        payload["status"] = "failed"
        for project in payload["projects"]:
            project.update(status="failed", reason="restore failed", nextStep="inspect")
        with self.assertRaises(ContractError):
            contracts.seal_document("recovery_receipt", payload)

    def test_downstream_artifacts_require_successful_supplied_predecessors(
        self,
    ) -> None:
        for predecessor in (
            "apply_receipt",
            "deployment_evidence",
            "verification",
            "recovery_plan",
        ):
            payload = copy.deepcopy(self.family[predecessor]["payload"])
            payload["status"] = "blocked"
            if predecessor == "recovery_plan":
                payload["conflicts"] = ["resource state changed"]
            else:
                payload["projects"][0].update(
                    status="blocked", reason="waiting", nextStep="prepare"
                )
            failed = contracts.seal_document(predecessor, payload)
            if predecessor == "apply_receipt":
                downstream = fixtures.build_deployment_evidence(self.manifest, failed)
                documents = {predecessor: failed, "deployment_evidence": downstream}
            elif predecessor == "deployment_evidence":
                downstream = fixtures.build_verification(
                    self.manifest, self.apply_receipt, failed
                )
                documents = {predecessor: failed, "verification": downstream}
            elif predecessor == "verification":
                downstream = fixtures.build_cleanup_receipt(
                    self.manifest, self.apply_receipt, self.deployment, failed
                )
                documents = {predecessor: failed, "cleanup_receipt": downstream}
            else:
                receipt_payload = copy.deepcopy(self.receipt["payload"])
                receipt_payload["plan_id"] = failed["plan_id"]
                downstream = contracts.seal_document(
                    "recovery_receipt", receipt_payload
                )
                documents = {predecessor: failed, "recovery_receipt": downstream}
            with (
                self.subTest(predecessor=predecessor),
                self.assertRaises(ContractError),
            ):
                contracts.validate_declared_bindings(self.manifest, documents)

    def test_recovery_steps_must_derive_from_supplied_stage_results(self) -> None:
        payload = copy.deepcopy(self.plan["payload"])
        payload["steps"][0]["expected_current"] = fixtures.file_state(999)
        payload["resources"][0]["state"] = copy.deepcopy(
            payload["steps"][0]["expected_current"]
        )
        plan = contracts.seal_document("recovery_plan", payload)
        with self.assertRaises(ContractError):
            contracts.validate_declared_bindings(
                self.manifest,
                {
                    "apply_receipt": self.apply_receipt,
                    "deployment_evidence": self.deployment,
                    "cleanup_receipt": self.cleanup,
                    "recovery_plan": plan,
                },
            )

    def test_failed_resource_cannot_be_downgraded_to_blocked_project(self) -> None:
        payload = copy.deepcopy(self.apply_receipt["payload"])
        result = payload["projects"][0]["private_results"][0]
        result["status"] = "failed"
        result["error"] = "private write failed"
        payload["projects"][0].update(
            status="blocked", reason="private write failed", nextStep="inspect"
        )
        payload["status"] = "blocked"
        with self.assertRaises(ContractError):
            contracts.seal_document("apply_receipt", payload)

    def test_shared_operations_require_an_unambiguous_shared_root(self) -> None:
        for boundary in (
            "absent root",
            "target outside",
            "ambiguous roots",
            "wrong closure",
        ):
            payload = copy.deepcopy(self.manifest["payload"])
            # Change only the root declaration; operation identities remain valid.
            if boundary == "absent root":
                payload["shared_roots"] = []
            elif boundary == "target outside":
                payload["shared_roots"][0]["path"] = "/private/other"
            elif boundary == "ambiguous roots":
                payload["shared_roots"].append(
                    {
                        "kind": "home",
                        "path": "/private/home",
                        "dependent_projects": list(fixtures.BOTH),
                    }
                )
            else:
                payload["shared_roots"][0]["dependent_projects"] = [fixtures.ALPHA]
            with self.subTest(boundary=boundary), self.assertRaises(ContractError):
                contracts.seal_document("manifest", payload)

    def test_receipt_scope_and_project_outcomes_must_match_its_plan(self) -> None:
        for boundary in ("scope", "evidence", "project result"):
            payload = copy.deepcopy(self.receipt["payload"])
            if boundary == "scope":
                payload["projects"] = [payload["projects"][0]]
            elif boundary == "evidence":
                payload["input_evidence"]["manifest"]["path"] = (
                    "/private/other/manifest.json"
                )
            else:
                dependent = next(
                    result
                    for result in payload["results"]
                    if result["dependent_projects"] == [fixtures.ALPHA]
                )
                dependent["status"] = "failed"
                dependent["error"] = "restore failed"
                payload["completed_step_ids"].remove(dependent["step_id"])
                payload["pending_step_ids"].append(dependent["step_id"])
                payload["status"] = "failed"
                payload["reason"] = "restore failed"
                payload["projects"][1].update(
                    status="failed", reason="restore failed", nextStep="inspect"
                )
            with self.subTest(boundary=boundary), self.assertRaises(ContractError):
                receipt = contracts.seal_document("recovery_receipt", payload)
                contracts.validate_declared_bindings(
                    self.manifest,
                    {"recovery_plan": self.plan, "recovery_receipt": receipt},
                )

    def test_failed_project_records_require_explanatory_diagnostics(self) -> None:
        payload = copy.deepcopy(self.apply_receipt["payload"])
        project = payload["projects"][0]
        project.update(status="failed", reason="", nextStep="")
        result = project["private_results"][0]
        result["status"] = "failed"
        result["error"] = "write failed"
        payload["status"] = "failed"
        with self.assertRaises(ContractError):
            contracts.seal_document("apply_receipt", payload)

    def test_known_partial_write_remains_recoverable_but_noop_does_not(self) -> None:
        for outcome in ("failed", "blocked"):
            cleanup_payload = copy.deepcopy(self.cleanup["payload"])
            result = cleanup_payload["projects"][0]["private_results"][0]
            result.update(status=outcome, error="write did not finish")
            cleanup_payload["projects"][0].update(
                status=outcome, reason="write did not finish", nextStep="recover"
            )
            cleanup_payload["status"] = outcome
            cleanup = contracts.seal_document("cleanup_receipt", cleanup_payload)
            plan = fixtures.build_recovery_plan(
                self.manifest, self.apply_receipt, self.deployment, cleanup
            )
            documents = {
                "apply_receipt": self.apply_receipt,
                "deployment_evidence": self.deployment,
                "cleanup_receipt": cleanup,
                "recovery_plan": plan,
            }
            with self.subTest(outcome=outcome):
                self.assertEqual(
                    contracts.validate_declared_bindings(self.manifest, documents)[
                        "recovery_plan"
                    ],
                    plan,
                )

            result["after"] = copy.deepcopy(result["before"])
            cleanup = contracts.seal_document("cleanup_receipt", cleanup_payload)
            plan_payload = fixtures.build_recovery_plan_payload(
                self.manifest, self.apply_receipt, self.deployment, cleanup
            )
            plan_payload["steps"][0]["expected_current"] = copy.deepcopy(
                result["after"]
            )
            plan_payload["resources"][0]["state"] = copy.deepcopy(result["after"])
            plan = contracts.seal_document("recovery_plan", plan_payload)
            documents.update(cleanup_receipt=cleanup, recovery_plan=plan)
            with self.subTest(noop=outcome), self.assertRaises(ContractError):
                contracts.validate_declared_bindings(self.manifest, documents)

    def test_recovery_can_bind_only_the_proven_apply_stage(self) -> None:
        payload = copy.deepcopy(self.plan["payload"])
        payload["input_evidence"]["deployment_evidence"] = None
        payload["input_evidence"]["cleanup_receipt"] = None
        payload["steps"] = [
            step for step in payload["steps"] if step["phase"] == "apply"
        ]
        by_resource = {step["resource_id"]: step for step in payload["steps"]}
        for step in payload["steps"]:
            step["depends_on"] = []
        for resource in payload["resources"]:
            step = by_resource[resource["resource_id"]]
            resource["operation_ids"] = list(step["operation_ids"])
            resource["state"] = copy.deepcopy(step["expected_current"])
        payload["shared_operation_ids"] = list(
            by_resource[fixtures.resource_id_of("s1")]["operation_ids"]
        )
        plan = contracts.seal_document("recovery_plan", payload)
        self.assertEqual(
            contracts.validate_declared_bindings(
                self.manifest,
                {"apply_receipt": self.apply_receipt, "recovery_plan": plan},
            )["recovery_plan"],
            plan,
        )


if __name__ == "__main__":
    unittest.main()
