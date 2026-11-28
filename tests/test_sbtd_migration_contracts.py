from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from tests import onboard_contract_fixtures as fixtures
from tests.onboard_contract_fixtures import build_manifest_payload, contracts


class MigrationIdentityContractTests(unittest.TestCase):
    def test_legacy_name_extraction_is_an_explicit_private_apply_operation(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = base / "project"
            source = {
                "path": str(root / ".trellis/.developer"),
                "state": {
                    "type": "file",
                    "checksum": hashlib.sha256(
                        b"name=dev01\ninitialized_at=2026-09-01T12:00:00\n"
                    ).hexdigest(),
                },
            }
            target = str(root / ".sbtd/developer")
            resource = contracts.resource_id("file", target)
            operation = {
                "operation_id": contracts.operation_id("apply", resource, "name"),
                "phase": "apply",
                "resource_id": resource,
                "owner_kind": "file",
                "target": target,
                "selector": "name",
                "change": {
                    "kind": "migrate-developer",
                    "source_ref": source,
                    "name": "dev01",
                },
                "ownership": {
                    "kind": "config-entry",
                    "reference": source,
                    "key_path": ["name"],
                },
                "before_requirement": {
                    "kind": "state",
                    "state": {"type": "absent", "checksum": None},
                },
                "dependent_projects": [str(root)],
            }
            payload = {
                "projects": [
                    {
                        "root": str(root),
                        "source_ref": None,
                        "head": None,
                        "platforms": ["codex"],
                        "sources": [source],
                        "private_operations": [operation],
                        "shared_operation_ids": [],
                    }
                ],
                "shared_roots": [],
                "shared_operations": [],
                "publication_decisions": {"schema_version": 1, "items": []},
                "routing_approvals": None,
                "custodian": "fixture",
                "backup_root": str(base / "vault"),
                "created_at": "2026-09-19T00:00:00Z",
                "retention": copy.deepcopy(build_manifest_payload()["retention"]),
                "tool_versions": {"onboard": "fixture"},
                "deployment": None,
            }
            sealed = contracts.seal_document("manifest", payload)
            self.assertEqual(
                contracts.load_document(
                    contracts.canonical_json_bytes(sealed), "manifest"
                ),
                sealed,
            )


class MigrationRetainedContractTests(unittest.TestCase):
    def test_only_proven_absent_unpublished_resources_may_omit_retention(self):
        family = fixtures.build_fixture_family()
        target = fixtures.ALPHA + "/.codex/agents/trellis-implement.toml"
        resource = contracts.resource_id("file", target)
        operation_id = contracts.operation_id("apply", resource, "whole-resource")
        state = fixtures.file_state(42)
        operation = {
            "operation_id": operation_id,
            "phase": "apply",
            "resource_id": resource,
            "owner_kind": "file",
            "target": target,
            "selector": "whole-resource",
            "change": {"kind": "remove"},
            "ownership": {
                "kind": "template-source",
                "reference": {"path": target, "state": state},
            },
            "before_requirement": {"kind": "state", "state": state},
            "dependent_projects": [fixtures.ALPHA],
        }
        payload = copy.deepcopy(family["manifest"]["payload"])
        payload["projects"][0]["private_operations"].append(operation)
        manifest = contracts.seal_document("manifest", payload)

        def evidence(after):
            payload = copy.deepcopy(family["apply_receipt"]["payload"])
            payload["manifest_id"] = manifest["manifest_id"]
            payload["projects"][0]["private_results"].append(
                {
                    "phase": "apply",
                    "resource_id": resource,
                    "operation_ids": [operation_id],
                    "dependent_projects": [fixtures.ALPHA],
                    "status": "succeeded",
                    "backup_ref": {
                        "path": fixtures.BACKUP_ROOT + "/retired-route",
                        "state": state,
                    },
                    "before": state,
                    "after": after,
                    "error": None,
                }
            )
            applied = contracts.seal_document("apply_receipt", payload)
            payload = copy.deepcopy(family["deployment_evidence"]["payload"])
            payload.update(
                manifest_id=manifest["manifest_id"], apply_id=applied["apply_id"]
            )
            deployed = contracts.seal_document("deployment_evidence", payload)
            payload = copy.deepcopy(family["verification"]["payload"])
            payload.update(
                manifest_id=manifest["manifest_id"],
                apply_id=applied["apply_id"],
                deployment_evidence_hash=hashlib.sha256(
                    contracts.canonical_json_bytes(deployed)
                ).hexdigest(),
            )
            return {
                "apply_receipt": applied,
                "deployment_evidence": deployed,
                "verification": contracts.seal_document("verification", payload),
            }

        contracts.validate_declared_bindings(manifest, evidence(fixtures.ABSENT))
        with self.assertRaises(contracts.ContractError):
            contracts.validate_declared_bindings(manifest, evidence(state))


class HistoricalVerificationContractTests(unittest.TestCase):
    def setUp(self):
        family = fixtures.build_fixture_family()
        target = fixtures.ALPHA + "/graft"
        operation = fixtures.legacy_graft_operation(
            target=target, owner_kind="directory", selector="whole-resource",
            kind="build-graft", dependents=[fixtures.ALPHA],
        )
        rid = operation["resource_id"]
        manifest = copy.deepcopy(family["manifest"]["payload"])
        manifest["tool_versions"] = fixtures.legacy_graft_versions()
        manifest["projects"][0]["private_operations"].append(operation)
        self.manifest = contracts.seal_document("manifest", manifest)
        apply = copy.deepcopy(family["apply_receipt"]["payload"])
        apply["manifest_id"] = self.manifest["manifest_id"]
        self.apply = contracts.seal_document("apply_receipt", apply)
        state = fixtures.directory_state(100)
        deployment = copy.deepcopy(family["deployment_evidence"]["payload"])
        deployment.update(
            manifest_id=self.manifest["manifest_id"], apply_id=self.apply["apply_id"]
        )
        deployment["projects"][0]["private_results"].append({
            "phase": "deploy",
            "resource_id": rid,
            "operation_ids": [operation["operation_id"]],
            "dependent_projects": [fixtures.ALPHA],
            "status": "succeeded",
            "backup_ref": None,
            "before": fixtures.ABSENT,
            "after": state,
            "error": None,
        })
        self.deployment = contracts.seal_document("deployment_evidence", deployment)
        self.payload = fixtures.build_verification_payload(
            self.manifest, self.apply, self.deployment,
        )
        self.payload["status"] = "not-verified"
        for project in self.payload["projects"]:
            project.update(status="not-verified", reason="Historical evidence", nextStep="Do not write.")
        self.payload["projects"][0]["retained_assets"].append({"path": target, "state": state})
        self.payload["legacy_resources"] = [{
            "resource_id": rid, "target": target, "bytes": "match", "mode": "absent",
            "mode_source": None, "status": "not-verified", "reason": "No mode evidence",
        }]
        self.mode_source = {"kind": "signed-attestation", "purpose": "post-write-mode"}

    def bind(self, payload):
        verification = contracts.seal_document("verification", payload)
        return contracts.validate_declared_bindings(
            self.manifest,
            {"apply_receipt": self.apply, "deployment_evidence": self.deployment,
             "verification": verification},
        )

    def test_legacy_verdict_must_match_bytes_mode_and_source(self):
        cases = (
            ("differ", "absent", None, "not-verified"),
            ("match", "match", self.mode_source, "drifted"),
            ("match", "differ", None, "drifted"),
            ("unreadable", "differ", self.mode_source, "drifted"),
            ("match", "absent", self.mode_source, "not-verified"),
        )
        for byte_state, mode, source, verdict in cases:
            with self.subTest(bytes=byte_state, mode=mode, mode_source=source, status=verdict):
                payload = copy.deepcopy(self.payload)
                payload["status"] = payload["projects"][0]["status"] = "failed"
                payload["legacy_resources"][0].update(
                    bytes=byte_state, mode=mode, mode_source=source, status=verdict
                )
                with self.assertRaises(contracts.ContractError) as error:
                    contracts.seal_document("verification", payload)
                self.assertEqual(error.exception.code, "semantic-violation")

    def test_drift_requires_failed_owning_project_and_aggregate(self):
        self.payload["legacy_resources"][0].update(
            mode="differ", mode_source=self.mode_source, status="drifted"
        )
        with self.assertRaisesRegex(contracts.ContractError, "failed verification"):
            contracts.seal_document("verification", self.payload)
        self.payload["status"] = self.payload["projects"][1]["status"] = "failed"
        with self.assertRaisesRegex(contracts.ContractError, "project status masks historical"):
            self.bind(self.payload)
        self.payload["projects"][0]["status"] = "failed"
        self.bind(self.payload)

    def test_legacy_rows_bind_exact_targets_and_sealed_observations(self):
        self.bind(self.payload)
        missing = copy.deepcopy(self.payload)
        missing["legacy_resources"].clear()
        with self.assertRaisesRegex(contracts.ContractError, "rows differ from the manifest"):
            self.bind(missing)
        wrong_target = copy.deepcopy(self.payload)
        wrong_target["legacy_resources"][0]["target"] += "-other"
        with self.assertRaisesRegex(contracts.ContractError, "target differs from its manifest"):
            self.bind(wrong_target)
        self.payload["projects"][0]["retained_assets"][-1]["state"] = fixtures.directory_state(101)
        with self.assertRaisesRegex(contracts.ContractError, "byte verdict differs"):
            self.bind(self.payload)


if __name__ == "__main__":
    unittest.main()
