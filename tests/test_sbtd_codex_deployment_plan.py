from __future__ import annotations
# ruff: noqa: I001 -- local scripts require the explicit test path before import.

import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sys

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard/scripts"
sys.path.insert(0, str(SCRIPTS))

from onboard_contracts import ContractError, operation_id, resource_id, seal_document
from sbtd_deployment import validate_archived_graft_declarations
from sbtd_migration import apply_migration, runtime_versions
from sbtd_migration_files import save_document, snapshot
from sbtd_migration_plan import plan_migration, validate_legacy_inputs

from tests.onboard_contract_fixtures import legacy_graft_operation, legacy_graft_versions
from tests.test_sbtd_migration_apply import file_contents, legacy_project
from tests.test_sbtd_migration_plan import _reader


class CodexDeploymentPlanTests(unittest.TestCase):
    def test_project_only_plan_cannot_authorize_new_graph_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = legacy_project(base, "project")
            home, vault = base / "home", base / "vault"
            home.mkdir(mode=0o700)
            vault.mkdir(mode=0o700)
            environment = {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "CODEX_HOME": str(home / ".codex"),
                "AGENT_SKILLS_DIR": str(home / ".agent/skills"),
            }
            before = file_contents(base)
            with mock.patch.dict(os.environ, environment):
                manifest = plan_migration(
                    [root],
                    vault,
                    "fixture",
                    None,
                    tool_versions=runtime_versions(),
                    deployment_mode="init-projects",
                )
                validate_legacy_inputs(manifest, _reader)
                self.assertEqual(file_contents(base), before)
                payload = manifest["payload"]
                self.assertIsNone(payload["deployment"])
                self.assertFalse(any(
                    op["phase"] == "deploy" for op in payload["projects"][0]["private_operations"]
                ))
                self.assertEqual(payload["shared_operations"], [])
                from tests.test_sbtd_migration_rc3_graft import RC2_ONBOARD

                archived = copy.deepcopy(payload)
                archived["deployment"] = {"mode": "init-projects", "platform": "codex", "inputs": []}
                archived["tool_versions"] = legacy_graft_versions(RC2_ONBOARD)
                archived["projects"][0]["private_operations"].extend((
                    legacy_graft_operation(
                        target=str(root / "graft"), owner_kind="directory", selector="whole-resource",
                        kind="build-graft", dependents=[str(root)],
                    ),
                    legacy_graft_operation(
                        target=str(root / "AGENTS.md"), owner_kind="markdown", selector="graft-agents",
                        kind="configure-graft", dependents=[str(root)], before=snapshot(root / "AGENTS.md"),
                    ),
                ))
                historical = seal_document("manifest", archived)
                validate_archived_graft_declarations(historical["payload"])
                evidence = base / "evidence"
                evidence.mkdir(mode=0o700)
                manifest_path = evidence / "rc2-manifest.json"
                save_document(manifest_path, historical, private_root=evidence)
                unchanged = snapshot(base)
                with self.assertRaises(ContractError) as failure:
                    apply_migration(manifest_path, confirmed=True, no_routing_approvals=True)
                self.assertEqual(failure.exception.code, "unsupported-in-rc.3")
                self.assertEqual(snapshot(base), unchanged)

    def test_resealed_shared_host_root_cannot_replace_the_active_codex_home(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = legacy_project(base, "project")
            home, vault = base / "home", base / "vault"
            home.mkdir(mode=0o700)
            vault.mkdir(mode=0o700)
            active = home / "active-codex"
            environment = {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "CODEX_HOME": str(active),
                "AGENT_SKILLS_DIR": str(home / ".agent/skills"),
            }
            with mock.patch.dict(os.environ, environment):
                manifest = plan_migration(
                    [root],
                    vault,
                    "fixture",
                    None,
                    tool_versions=runtime_versions(),
                    deployment_mode="init",
                )
                validate_legacy_inputs(manifest, _reader)
                payload = copy.deepcopy(manifest["payload"])
                forged = base / "unselected-host"
                for shared_root in payload["shared_roots"]:
                    if shared_root["kind"] == "codex-home":
                        shared_root["path"] = str(forged)
                rules = next(op for op in payload["shared_operations"] if op["target"] == str(active / "AGENTS.md"))
                rules["target"] = str(forged / "AGENTS.md")
                rules["resource_id"] = resource_id(rules["owner_kind"], rules["target"])
                rules["operation_id"] = operation_id("deploy", rules["resource_id"], rules["selector"])
                payload["projects"][0]["shared_operation_ids"] = sorted(
                    operation["operation_id"]
                    for operation in payload["shared_operations"]
                )
                before = file_contents(base)
                with self.assertRaises(ContractError):
                    validate_legacy_inputs(seal_document("manifest", payload), _reader)
                mismatched = copy.deepcopy(manifest["payload"])
                mismatched["deployment"]["platform"] = "omp"
                with self.assertRaises(ContractError):
                    validate_legacy_inputs(
                        seal_document("manifest", mismatched), _reader
                    )
                self.assertEqual(file_contents(base), before)

    def test_codex_manifest_rejects_an_omp_deploy_operation(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = legacy_project(base, "project")
            home, vault = base / "home", base / "vault"
            home.mkdir(mode=0o700)
            vault.mkdir(mode=0o700)
            active = home / "active-codex"
            environment = {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "CODEX_HOME": str(active),
                "AGENT_SKILLS_DIR": str(home / ".agent/skills"),
            }
            with mock.patch.dict(os.environ, environment):
                manifest = plan_migration(
                    [root],
                    vault,
                    "fixture",
                    None,
                    tool_versions=runtime_versions(),
                    deployment_mode="init",
                )
                payload = copy.deepcopy(manifest["payload"])
                operation = legacy_graft_operation(
                    target=str(home / ".omp/agent/mcp.json"), owner_kind="json",
                    selector="graft-omp-mcp", kind="configure-graft", dependents=[str(root)],
                )
                payload["shared_roots"].append(
                    {
                        "kind": "omp-home",
                        "path": str(home / ".omp"),
                        "dependent_projects": [str(root)],
                    }
                )
                payload["shared_operations"].append(operation)
                payload["projects"][0]["shared_operation_ids"].append(
                    operation["operation_id"]
                )
                before = file_contents(base)
                with self.assertRaises(ContractError):
                    validate_legacy_inputs(seal_document("manifest", payload), _reader)
                self.assertEqual(file_contents(base), before)


if __name__ == "__main__":
    unittest.main()
