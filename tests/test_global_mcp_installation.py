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
from onboard_contracts import ContractError
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
            "PI_CONFIG_DIR": ".omp", "PI_CODING_AGENT_DIR": "",
            "OMP_PROFILE": "", "PI_PROFILE": "",
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

    def arguments(
        self, approval=None, *, mode="reset", platform="codex", with_project=True,
        extra=(),
    ):
        argv = [mode, "--platform", platform, "--global-skills-dir", str(self.skills)]
        if with_project:
            argv += ["--projects-root", str(self.project)]
        argv += ["--skip-project-agents", "--json", "--yes"]
        if approval is not None:
            argv += ["--graft-retire-legacy", "--graft-legacy-bindings", str(approval)]
        return onboard.build_parser().parse_args([*argv, *extra])

    def run_cli(self, mode, args, *, runtime_error=None):
        output = io.StringIO()
        with (
            mock.patch.dict(os.environ, self.environment),
            mock.patch.object(
                deployment,
                "verified_runtime",
                return_value=self.runtime,
                side_effect=runtime_error,
            ) as runtime,
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            code = onboard.run(mode, args)
        return code, json.loads(output.getvalue()), runtime

    def host_target(self, platform):
        return (
            self.home / ".codex/config.toml"
            if platform == "codex"
            else self.home / ".omp/agent/mcp.json"
        )

    def isolate_host_home(self, platform):
        self.home = self.base / f"home-{platform}"
        self.home.mkdir()
        self.skills = self.home / ".agent/skills"
        self.installed = self.skills / "sbtd-workflow-onboard"
        shutil.copytree(PACKAGE, self.installed)
        self.environment.update({
            "HOME": str(self.home),
            "USERPROFILE": str(self.home),
            "CODEX_HOME": str(self.home / ".codex"),
            "AGENT_SKILLS_DIR": str(self.skills),
        })

    def test_reset_action_previews_exact_host_write_without_writing(self):
        for platform in ("codex", "omp"):
            with self.subTest(platform=platform):
                self.isolate_host_home(platform)
                target = self.host_target(platform)
                args = self.arguments(
                    mode="plan",
                    platform=platform,
                    with_project=False,
                    extra=("--action", "reset"),
                )
                before = snapshot(self.base)
                code, preview, runtime = self.run_cli("plan", args)

                self.assertEqual(code, 0, preview)
                self.assertEqual(preview["plannedAction"], "reset")
                wiring = preview["graftWiring"]
                self.assertEqual(wiring["status"], "planned", wiring)
                self.assertEqual(wiring["roots"], [])
                preview_targets = [
                    operation["target"]
                    for operation in wiring["sharedOperations"]
                ]
                preview_resources = [
                    operation["resource_id"]
                    for operation in wiring["sharedOperations"]
                ]
                self.assertEqual(preview_targets, [str(target)])
                runtime.assert_called_once_with()
                self.assertEqual(snapshot(self.base), before)
                self.assertFalse(target.exists())

                reset_args = self.arguments(
                    mode="reset", platform=platform, with_project=False
                )
                code, applied, _ = self.run_cli("reset", reset_args)
                self.assertEqual(code, 0, applied)
                actual_resources = [
                    operation["resource_id"]
                    for operation in applied["graftWiring"]["operationResults"]
                ]
                self.assertEqual(actual_resources, preview_resources)
                self.assertTrue(target.is_file())
                servers_key = "mcp_servers" if platform == "codex" else "mcpServers"
                document = (
                    tomllib.loads(target.read_text(encoding="utf-8"))
                    if platform == "codex"
                    else json.loads(target.read_bytes())
                )
                self.assertEqual(set(document[servers_key]), {"sbtd-graft"})

    def test_default_plan_and_init_do_not_wire_global_host_without_project(self):
        for platform in ("codex", "omp"):
            self.isolate_host_home(platform)
            target = self.host_target(platform)
            target.parent.mkdir(parents=True, exist_ok=True)
            original = (
                b'model = "keep-user-model"\n'
                if platform == "codex"
                else b'{"mcpServers": {"foreign": {"command": "/foreign/server"}}}\n'
            )
            target.write_bytes(original)
            for mode in ("plan", "init"):
                with self.subTest(platform=platform, mode=mode):
                    args = self.arguments(
                        mode=mode, platform=platform, with_project=False
                    )
                    before = snapshot(self.base)
                    code, result, runtime = self.run_cli(mode, args)

                    self.assertEqual(code, 0, result)
                    self.assertNotIn("graftWiring", result)
                    runtime.assert_not_called()
                    self.assertEqual(target.read_bytes(), original)
                    if mode == "plan":
                        self.assertEqual(result["plannedAction"], "init")
                        self.assertEqual(snapshot(self.base), before)

    def test_reset_action_failures_and_no_mcp_never_claim_host_targets(self):
        cases = [
            ("no-mcp", ("--no-mcp",), AssertionError("runtime must not be probed"), 0, None),
            (
                "unavailable",
                (),
                ContractError("runtime-unavailable", "runtime unavailable"),
                0,
                "not-available",
            ),
            ("error", (), OSError("runtime probe failed"), 2, "blocked"),
        ]
        for platform in ("codex", "omp"):
            self.isolate_host_home(platform)
            for name, extra, error, expected_code, status in cases:
                with self.subTest(platform=platform, case=name):
                    target = self.host_target(platform)
                    args = self.arguments(
                        mode="plan",
                        platform=platform,
                        with_project=False,
                        extra=("--action", "reset", *extra),
                    )
                    before = snapshot(self.base)
                    code, result, runtime = self.run_cli(
                        "plan", args, runtime_error=error
                    )

                    self.assertEqual(code, expected_code, result)
                    self.assertEqual(result["plannedAction"], "reset")
                    wiring = result.get("graftWiring")
                    if status is None:
                        self.assertIsNone(wiring)
                        runtime.assert_not_called()
                    else:
                        self.assertEqual(wiring["status"], status, wiring)
                        runtime.assert_called_once_with()
                    self.assertNotIn("sharedOperations", wiring or {})
                    self.assertIsNone((wiring or {}).get("codexHome"))
                    self.assertIsNone((wiring or {}).get("ompHome"))
                    self.assertEqual(snapshot(self.base), before)
                    self.assertFalse(target.exists())

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

    def test_global_only_init_reports_file_and_skill_results_without_wiring(self):
        valid_skill = self.skills / "sbtd-task"
        shutil.copytree(PACKAGE / "templates/skills/sbtd-task", valid_skill)
        args = self.arguments(mode="init", with_project=False)

        code, result, runtime = self.run_cli("init", args)

        self.assertEqual(code, 0, result)
        self.assertNotIn("graftWiring", result)
        self.assertNotIn("developerPlan", result)
        runtime.assert_not_called()
        operations = {
            item["label"]: item for item in result["operationResults"]
        }
        agents = operations["codex global AGENTS.md"]
        self.assertEqual(agents["target"], str(self.home / ".codex/AGENTS.md"))
        self.assertEqual(agents["action"], "copied")
        self.assertEqual(agents["status"], "success")
        skipped = operations["global skill sbtd-task"]
        self.assertEqual(skipped["target"], str(valid_skill))
        self.assertEqual(skipped["action"], "skipped-already-valid")
        self.assertEqual(skipped["status"], "skipped")
        self.assertTrue(Path(agents["target"]).is_file())
        self.assertFalse(self.host_target("codex").exists())

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
