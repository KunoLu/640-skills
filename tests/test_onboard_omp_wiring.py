from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

PACKAGE = (Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard").resolve()
sys.path.insert(0, str(PACKAGE / "scripts"))

from onboard_contracts import ContractError
from sbtd_graft_deployment import execute_normal_wiring, plan_normal_wiring

from tests.test_sbtd_migration_apply import file_contents, legacy_project



class OmpNormalWiringTests(unittest.TestCase):
    def test_unavailable_runtime_is_readonly_and_never_creates_omp_state(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = legacy_project(base, "project")
            home = base / "home"
            home.mkdir()
            args = Namespace(
                projects_root=str(root),
                platform="omp",
                graft_hooks=False,
                global_skills_dir=str(home / ".agent/skills"),
            )
            before = file_contents(base)
            with (
                mock.patch.dict(
                    os.environ,
                    {
                        "HOME": str(home),
                        "USERPROFILE": str(home),
                        "CODEX_HOME": str(home / ".codex"),
                    },
                ),
                mock.patch(
                    "sbtd_graft_deployment.verified_runtime",
                    side_effect=ContractError("runtime-unavailable", "missing"),
                ),
            ):
                plan = plan_normal_wiring("init", args)
            self.assertEqual(plan["status"], "not-available")
            self.assertEqual(file_contents(base), before)

    def test_normal_plan_uses_template_only_when_project_agents_will_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = legacy_project(base, "project")
            home = base / "home"
            home.mkdir()
            (root / "AGENTS.md").write_bytes(b"\xff<!-- graft:start -->broken")
            runtime = {
                "node": "/fixture/node",
                "cli": "/fixture/cli.js",
                "python": "/fixture/python",
            }
            environment = {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "CODEX_HOME": str(home / ".codex"),
                "AGENT_SKILLS_DIR": str(home / ".agent/skills"),
            }

            def plan(skip_project_agents, mode="init"):
                args = Namespace(
                    projects_root=str(root),
                    platform="omp",
                    graft_hooks=False,
                    global_skills_dir=str(home / ".agent/skills"),
                    skip_project_agents=skip_project_agents,
                )
                with (
                    mock.patch.dict(os.environ, environment),
                    mock.patch(
                        "sbtd_graft_deployment.verified_runtime", return_value=runtime
                    ),
                ):
                    return plan_normal_wiring(mode, args)

            self.assertEqual(plan(False)["status"], "planned")
            self.assertEqual(plan(True)["status"], "blocked")
            self.assertEqual(plan(False, "check")["status"], "planned")
            self.assertEqual(plan(True, "check")["status"], "blocked")
            self.assertEqual((root / "AGENTS.md").read_bytes(), b"\xff<!-- graft:start -->broken")


    def test_planned_omp_wiring_writes_active_config_without_hooks(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = legacy_project(base, "project")
            home = base / "home"
            installed = home / ".agent/skills/sbtd-workflow-onboard"
            home.mkdir()
            shutil.copytree(PACKAGE, installed)
            args = Namespace(
                projects_root=str(root),
                platform="omp",
                graft_hooks=False,
                global_skills_dir=str(home / ".agent/skills"),
            )
            runtime = {
                "node": "/fixture/node",
                "cli": "/fixture/cli.js",
                "python": "/fixture/python",
            }
            environment = {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "CODEX_HOME": str(home / ".codex"),
                "AGENT_SKILLS_DIR": str(home / ".agent/skills"),
            }
            with (
                mock.patch.dict(os.environ, environment),
                mock.patch(
                    "sbtd_graft_deployment.verified_runtime", return_value=runtime
                ),
            ):
                plan = plan_normal_wiring("init", args)
            self.assertEqual(plan["status"], "planned", plan)
            self.assertIsNone(plan["codexHome"])
            self.assertEqual(plan["ompHome"], str(home / ".omp/agent"))
            self.assertFalse((home / ".omp").exists())

            def graph(project, _runtime):
                (project / "graft").mkdir()
                (project / "graft/fixture").write_bytes(b"synthetic native output")

            with (
                mock.patch.dict(os.environ, environment),
                mock.patch(
                    "sbtd_graft_deployment.build_project_graph", side_effect=graph
                ),
            ):
                result, code = execute_normal_wiring(plan, template_written=False)
            self.assertEqual(code, 0, result)
            self.assertEqual(result["status"], "success")
            target = home / ".omp/agent/mcp.json"
            servers = json.loads(target.read_text(encoding="utf-8"))["mcpServers"]
            self.assertEqual(len(servers), 1)
            server = next(iter(servers.values()))
            self.assertEqual(server["command"], runtime["python"])
            self.assertEqual(server["cwd"], str(root))
            self.assertFalse((home / ".codex/hooks.json").exists())
            self.assertEqual(result["hooks"], "not-installed")


if __name__ == "__main__":
    unittest.main()
