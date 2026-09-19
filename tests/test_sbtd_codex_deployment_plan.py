from __future__ import annotations

import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.test_sbtd_migration_apply import file_contents, legacy_project
from tests.test_sbtd_migration_plan import _reader
from onboard_contracts import ContractError, operation_id, resource_id, seal_document
from sbtd_migration_plan import plan_migration, validate_legacy_inputs


class CodexDeploymentPlanTests(unittest.TestCase):
    def test_project_only_deploy_resources_are_frozen_before_apply(self):
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
                    tool_versions={"onboard": "fixture", "graft": "0.18.0"},
                    deployment_mode="init-projects",
                )
                validate_legacy_inputs(manifest, _reader)
                self.assertEqual(file_contents(base), before)
                payload = manifest["payload"]
                operations = payload["projects"][0]["private_operations"]
                self.assertEqual(
                    {
                        operation["target"]
                        for operation in operations
                        if operation["phase"] == "deploy"
                    },
                    {str(root / "AGENTS.md"), str(root / "graft")},
                )
                self.assertEqual(payload["shared_operations"], [])
                broken = copy.deepcopy(payload)
                broken["projects"][0]["private_operations"] = [
                    operation
                    for operation in broken["projects"][0]["private_operations"]
                    if operation["change"]["kind"] != "build-graft"
                ]
                with self.assertRaises(ContractError):
                    validate_legacy_inputs(seal_document("manifest", broken), _reader)
                self.assertEqual(file_contents(base), before)

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
                    tool_versions={"onboard": "fixture", "graft": "0.18.0"},
                    deployment_mode="init",
                )
                validate_legacy_inputs(manifest, _reader)
                payload = copy.deepcopy(manifest["payload"])
                forged = base / "unselected-host"
                for shared_root in payload["shared_roots"]:
                    if shared_root["kind"] == "codex-home":
                        shared_root["path"] = str(forged)
                for operation in payload["shared_operations"]:
                    if operation["selector"] == "graft-mcp":
                        operation["target"] = str(forged / "config.toml")
                        operation["resource_id"] = resource_id(
                            "toml", operation["target"]
                        )
                        operation["operation_id"] = operation_id(
                            "deploy", operation["resource_id"], "graft-mcp"
                        )
                payload["projects"][0]["shared_operation_ids"] = sorted(
                    operation["operation_id"]
                    for operation in payload["shared_operations"]
                )
                before = file_contents(base)
                with self.assertRaises(ContractError):
                    validate_legacy_inputs(seal_document("manifest", payload), _reader)
                self.assertEqual(file_contents(base), before)


if __name__ == "__main__":
    unittest.main()
