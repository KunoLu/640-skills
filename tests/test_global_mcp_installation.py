from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

PACKAGE = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard"
sys.path.insert(0, str(PACKAGE / "scripts"))

import onboard
import sbtd_graft_deployment as deployment
from sbtd_migration_files import snapshot

from tests.test_sbtd_graft_isolation import _git_repo


class GlobalMcpInstallationTests(unittest.TestCase):
    """GM-01/07/08: approval gates cover the complete installer, not just wiring."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.home = self.base / "home"
        self.home.mkdir()
        self.project = _git_repo(self.base / "project", "main", self.home)
        self.skills = self.home / ".agent/skills"
        self.installed = self.skills / "sbtd-workflow-onboard"
        shutil.copytree(PACKAGE, self.installed)
        self.environment = {
            "HOME": str(self.home), "USERPROFILE": str(self.home),
            "CODEX_HOME": str(self.home / ".codex"),
            "AGENT_SKILLS_DIR": str(self.skills),
        }
        self.runtime = {
            "node": str(self.base / "runtime/node"),
            "cli": str(self.base / "runtime/cli.js"),
            "python": str(self.base / "runtime/python"),
        }

    def approval(self, directory):
        directory.mkdir(parents=True, mode=0o700)
        path = directory / "old-bindings.json"
        path.write_text(json.dumps({
            "schema_version": 1,
            "bindings": [{
                "root": str(self.project), **self.runtime,
                "launcher": str(self.installed / "scripts/sbtd_graft_entry.py"),
            }],
        }))
        return path

    def arguments(self, approval=None, *, mode="reset", extra=()):
        argv = [mode, "--platform", "codex", "--global-skills-dir", str(self.skills),
                "--projects-root", str(self.project), "--skip-project-agents", "--json", "--yes"]
        if approval is not None:
            argv += ["--graft-retire-legacy", "--graft-legacy-bindings", str(approval)]
        return onboard.build_parser().parse_args([*argv, *extra])

    def test_reset_refuses_approval_inside_installed_skill_before_any_write(self):
        for skill in ("sbtd-workflow-onboard", "sbtd-task"):
            with self.subTest(skill=skill):
                approval = self.approval(self.skills / skill / "private")
                before = snapshot(self.base)
                output = io.StringIO()
                with (
                    mock.patch.dict(os.environ, self.environment),
                    mock.patch.object(deployment, "verified_runtime", return_value=self.runtime),
                    contextlib.redirect_stdout(output),
                    contextlib.redirect_stderr(io.StringIO()),
                ):
                    code = onboard.run("reset", self.arguments(approval))
                self.assertEqual(code, 2)
                result = json.loads(output.getvalue())
                self.assertEqual(result["graftWiring"]["status"], "blocked")
                self.assertIn("installation write target", result["graftWiring"]["reason"])
                self.assertEqual(snapshot(self.base), before)
                self.assertTrue(approval.is_file())

    def test_approval_drift_after_plan_prevents_the_first_installer_write(self):
        approval = self.approval(self.base / "private")
        planned = False
        real_plan = deployment.plan_normal_wiring
        before = snapshot(self.home)

        def plan(*args, **kwargs):
            nonlocal planned
            result = real_plan(*args, **kwargs)
            planned = result["status"] == "planned"
            return result

        def provider(_skills):
            if planned:
                approval.write_text(approval.read_text() + "\n")
            return {"provider": "skill"}

        output = io.StringIO()
        with (
            mock.patch.dict(os.environ, self.environment),
            mock.patch.object(deployment, "verified_runtime", return_value=self.runtime),
            mock.patch.object(deployment, "plan_normal_wiring", side_effect=plan),
            mock.patch.object(onboard, "detect_ponytail_provider", side_effect=provider),
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            code = onboard.run("reset", self.arguments(approval))
        self.assertTrue(planned)
        self.assertEqual(code, 2)
        result = json.loads(output.getvalue())
        self.assertIn("before installation", result["graftWiring"]["reason"])
        self.assertEqual(snapshot(self.home), before)
        self.assertIsNone(result["requiredExternalInstall"])

    def test_init_with_explicit_hooks_still_writes_global_mcp_and_hooks(self):
        args = self.arguments(mode="init", extra=("--graft-hooks",))
        target = self.home / ".codex/config.toml"
        target.parent.mkdir()
        target.write_bytes(
            b'model = "keep-user-model"\ncustom = { keep = true }\n\n'
            b'[mcp_servers.foreign]\ncommand = "/foreign/server"\nargs = ["keep"]\n'
        )
        hooks_target = self.home / ".codex/hooks.json"
        hooks_target.write_bytes(b'{"custom": {"keep": true}}\n')

        def graph(project, _runtime):
            (project / "graft").mkdir()

        with (
            mock.patch.dict(os.environ, self.environment),
            mock.patch.object(deployment, "verified_runtime", return_value=self.runtime),
            mock.patch.object(deployment, "build_project_graph", side_effect=graph),
        ):
            plan = deployment.plan_normal_wiring("init", args)
            self.assertEqual(plan["status"], "planned", plan)
            result, code = deployment.execute_normal_wiring(
                plan, template_written=False
            )
        self.assertEqual(code, 0, result)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["hooks"], "configured-needs-host-trust")
        config = tomllib.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(config["model"], "keep-user-model")
        self.assertEqual(config["custom"], {"keep": True})
        self.assertEqual(set(config["mcp_servers"]), {"foreign", "sbtd-graft"})
        self.assertEqual(config["mcp_servers"]["foreign"]["args"], ["keep"])
        hooks = json.loads(hooks_target.read_bytes())
        self.assertEqual(hooks["custom"], {"keep": True})
        self.assertTrue(hooks["hooks"])
        self.assertTrue((self.project / "graft").is_dir())

    def test_explicit_wiring_flags_keep_their_scope_validation(self):
        approval = self.approval(self.base / "private")
        hooks_without_root = self.arguments(mode="init", extra=("--graft-hooks",))
        hooks_without_root.projects_root = None
        omp_hooks = self.arguments(mode="init", extra=("--graft-hooks",))
        omp_hooks.platform = "omp"
        project_only_hooks = self.arguments(
            mode="init-projects", extra=("--graft-hooks",)
        )
        retirement_without_root = self.arguments(approval, mode="init")
        retirement_without_root.projects_root = None
        bindings_without_retirement = self.arguments(
            mode="init", extra=("--graft-legacy-bindings", str(approval))
        )
        cases = [
            ("hook authorization requires", hooks_without_root, "init"),
            ("OMP wiring does not include Codex hooks", omp_hooks, "init"),
            (
                "project-only setup cannot change global hooks",
                project_only_hooks,
                "init-projects",
            ),
            ("legacy retirement requires", retirement_without_root, "init"),
            ("legacy bindings require explicit", bindings_without_retirement, "init"),
        ]
        before = snapshot(self.base)
        with (
            mock.patch.dict(os.environ, self.environment),
            mock.patch.object(
                deployment,
                "verified_runtime",
                side_effect=AssertionError(
                    "scope validation must precede runtime probing"
                ),
            ),
        ):
            for reason, args, mode in cases:
                with self.subTest(reason=reason):
                    plan = deployment.plan_normal_wiring(mode, args)
                    self.assertEqual(plan["status"], "blocked")
                    self.assertIn(reason, plan["reason"])
        self.assertEqual(snapshot(self.base), before)

    def test_global_only_no_mcp_does_not_probe_or_register_a_runtime(self):
        args = self.arguments(extra=("--no-mcp",))
        args.projects_root = None
        before = snapshot(self.base)
        with (
            mock.patch.dict(os.environ, self.environment),
            mock.patch.object(deployment, "verified_runtime", side_effect=AssertionError("no runtime needed")),
        ):
            plan = deployment.plan_normal_wiring("init", args)
            result, code = deployment.execute_normal_wiring(plan, template_written=False)
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(snapshot(self.base), before)

    def test_no_mcp_cannot_authorize_hooks_or_legacy_retirement(self):
        approval = self.approval(self.base / "private")
        cases = [
            self.arguments(extra=("--no-mcp", "--graft-hooks")),
            self.arguments(approval, extra=("--no-mcp",)),
        ]
        before = snapshot(self.base)
        with mock.patch.dict(os.environ, self.environment):
            for args in cases:
                with self.subTest(hooks=args.graft_hooks):
                    plan = deployment.plan_normal_wiring("reset", args)
                    self.assertEqual(plan["status"], "blocked")
                    self.assertIn("--no-mcp", plan["reason"])
        self.assertEqual(snapshot(self.base), before)

    def test_approval_drift_during_graph_build_preserves_host_configuration(self):
        approval = self.approval(self.base / "private")
        args = self.arguments(approval)
        target = self.home / ".codex/config.toml"
        target.parent.mkdir()
        target.write_text('model = "keep-user-model"\n')
        original = target.read_bytes()

        def graph(project, _runtime):
            (project / "graft").mkdir()
            approval.unlink()

        with (
            mock.patch.dict(os.environ, self.environment),
            mock.patch.object(deployment, "verified_runtime", return_value=self.runtime),
        ):
            plan = deployment.plan_normal_wiring("reset", args)
            self.assertEqual(plan["status"], "planned", plan)
            with mock.patch.object(deployment, "build_project_graph", side_effect=graph):
                result, code = deployment.execute_normal_wiring(plan, template_written=False)
        self.assertEqual(code, 2, result)
        self.assertIn("before resource execution", result["reason"])
        self.assertEqual(target.read_bytes(), original)
        self.assertTrue(all(item["status"] == "succeeded" for item in result["operationResults"]))
        self.assertEqual(len(result["operationResults"]), 2)


if __name__ == "__main__":
    unittest.main()
