from __future__ import annotations

import copy
import hashlib
import unittest
from pathlib import Path

from tests import onboard_contract_fixtures as fixtures

contracts = fixtures.contracts


class CodexDeploymentContractTests(unittest.TestCase):
    def test_generated_graph_is_a_bound_deploy_operation_not_a_copy(self):
        payload = fixtures.build_manifest_payload()
        target = fixtures.ALPHA + "/graft"
        resource = contracts.resource_id("directory", target)
        policy_path = (
            Path(__file__).resolve().parents[1]
            / "sbtd-workflow-onboard/assets/graft-build-policy.json"
        )
        policy = {
            "path": str(policy_path),
            "state": {
                "type": "file",
                "checksum": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
            },
        }
        operation = {
            "phase": "deploy",
            "resource_id": resource,
            "operation_id": contracts.operation_id(
                "deploy", resource, "whole-resource"
            ),
            "owner_kind": "directory",
            "target": target,
            "selector": "whole-resource",
            "change": {"kind": "build-graft", "source_ref": policy},
            "ownership": {"kind": "template-source", "reference": policy},
            "before_requirement": {"kind": "state", "state": fixtures.ABSENT},
            "dependent_projects": [fixtures.ALPHA],
        }
        payload["projects"][0]["private_operations"].append(operation)
        manifest = contracts.seal_document("manifest", payload)
        self.assertEqual(
            contracts.load_document(
                contracts.canonical_json_bytes(manifest), "manifest"
            ),
            manifest,
        )
        for boundary in (
            "wrong-phase",
            "wrong-target",
            "wrong-owner",
            "changed-policy",
            "arbitrary-policy-path",
        ):
            broken = copy.deepcopy(payload)
            candidate = broken["projects"][0]["private_operations"][-1]
            if boundary == "wrong-phase":
                candidate["phase"] = "apply"
            elif boundary == "wrong-target":
                candidate["target"] = fixtures.ALPHA + "/business-data"
            elif boundary == "wrong-owner":
                candidate["owner_kind"] = "file"
            elif boundary == "changed-policy":
                candidate["ownership"]["reference"] = {
                    "path": policy["path"],
                    "state": fixtures.file_state(346),
                }
            else:
                forged = {
                    "path": "/private/operator/arbitrary-policy.json",
                    "state": policy["state"],
                }
                candidate["change"]["source_ref"] = forged
                candidate["ownership"]["reference"] = forged
            candidate["resource_id"] = contracts.resource_id(
                candidate["owner_kind"], candidate["target"]
            )
            candidate["operation_id"] = contracts.operation_id(
                candidate["phase"], candidate["resource_id"], candidate["selector"]
            )
            with (
                self.subTest(boundary=boundary),
                self.assertRaises(contracts.ContractError),
            ):
                contracts.seal_document("manifest", broken)

    def test_managed_configuration_cannot_target_arbitrary_project_files(self):
        payload = fixtures.build_manifest_payload()
        target = fixtures.ALPHA + "/AGENTS.md"
        resource = contracts.resource_id("markdown", target)
        policy_path = (
            Path(__file__).resolve().parents[1]
            / "sbtd-workflow-onboard/assets/graft-build-policy.json"
        )
        policy = {
            "path": str(policy_path),
            "state": {
                "type": "file",
                "checksum": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
            },
        }
        operation = {
            "phase": "deploy",
            "resource_id": resource,
            "operation_id": contracts.operation_id("deploy", resource, "graft-agents"),
            "owner_kind": "markdown",
            "target": target,
            "selector": "graft-agents",
            "change": {"kind": "configure-graft", "source_ref": policy},
            "ownership": {"kind": "template-source", "reference": policy},
            "before_requirement": {"kind": "state", "state": fixtures.ABSENT},
            "dependent_projects": [fixtures.ALPHA],
        }
        payload["projects"][0]["private_operations"].append(operation)
        contracts.seal_document("manifest", payload)
        for target in (
            fixtures.ALPHA + "/business.md",
            fixtures.ALPHA + "/.codex/config.toml",
        ):
            broken = copy.deepcopy(payload)
            candidate = broken["projects"][0]["private_operations"][-1]
            candidate["target"] = target
            candidate["resource_id"] = contracts.resource_id(
                candidate["owner_kind"], target
            )
            candidate["operation_id"] = contracts.operation_id(
                "deploy", candidate["resource_id"], candidate["selector"]
            )
            with (
                self.subTest(target=target),
                self.assertRaises(contracts.ContractError),
            ):
                contracts.seal_document("manifest", broken)
    def test_omp_mcp_configuration_binds_the_declared_omp_home(self):
        payload = fixtures.build_manifest_payload()
        target = "/private/home/.omp/mcp.json"
        resource = contracts.resource_id("json", target)
        policy_path = (
            Path(__file__).resolve().parents[1]
            / "sbtd-workflow-onboard/assets/graft-build-policy.json"
        )
        policy = {
            "path": str(policy_path),
            "state": {
                "type": "file",
                "checksum": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
            },
        }
        payload["shared_roots"].append(
            {
                "kind": "omp-home",
                "path": "/private/home/.omp",
                "dependent_projects": list(fixtures.BOTH),
            }
        )
        payload["deployment"] = {
            "mode": "init",
            "platform": "omp",
            "inputs": [],
        }
        operation = {
            "phase": "deploy",
            "resource_id": resource,
            "operation_id": contracts.operation_id(
                "deploy", resource, "graft-omp-mcp"
            ),
            "owner_kind": "json",
            "target": target,
            "selector": "graft-omp-mcp",
            "change": {"kind": "configure-graft", "source_ref": policy},
            "ownership": {"kind": "template-source", "reference": policy},
            "before_requirement": {"kind": "state", "state": fixtures.ABSENT},
            "dependent_projects": list(fixtures.BOTH),
        }
        payload["shared_operations"].append(operation)
        for project in payload["projects"]:
            project["shared_operation_ids"].append(operation["operation_id"])
        contracts.seal_document("manifest", payload)
        broken = copy.deepcopy(payload)
        candidate = broken["shared_operations"][-1]
        candidate["target"] = "/private/home/.codex/mcp.json"
        candidate["resource_id"] = contracts.resource_id("json", candidate["target"])
        candidate["operation_id"] = contracts.operation_id(
            "deploy", candidate["resource_id"], candidate["selector"]
        )
        with self.assertRaises(contracts.ContractError):
            contracts.seal_document("manifest", broken)



if __name__ == "__main__":
    unittest.main()
