from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL_SH = ROOT / "install.sh"
INSTALL_PS1 = ROOT / "install.ps1"
SOURCE_ROOT = ROOT / "kuno-workflow-onboard-skills"


class BashInstallerAgentCliFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="kuno-install-sh-test-")
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.state_dir = self.root / "state"
        self.state_dir.mkdir()
        self.project_root = self.root / "project"
        self.project_root.mkdir()
        self.project_root_two = self.root / "project-two"
        self.project_root_two.mkdir()
        self.log_path = self.root / "onboard-modes.log"
        self.args_log_path = self.root / "onboard-args.log"
        self.env = os.environ.copy()
        self.env["PATH"] = os.pathsep.join((str(self.bin_dir), "/usr/bin", "/bin"))
        self.env["REAL_PYTHON"] = sys.executable
        self.env["FAKE_STATE_DIR"] = str(self.state_dir)
        self.env["FAKE_ONBOARD_LOG"] = str(self.log_path)
        self.env["FAKE_ONBOARD_ARGS_LOG"] = str(self.args_log_path)
        self.write_fake_python()

    def write_executable(self, path: Path, body: str) -> None:
        path.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def write_fake_python(self) -> None:
        self.write_executable(
            self.bin_dir / "python3",
            """
            #!/bin/sh
            if [ "$1" = "-" ]; then
              exec "$REAL_PYTHON" "$@"
            fi

            mode="$2"
            printf '%s\n' "$mode" >> "$FAKE_ONBOARD_LOG"
            printf '%s\n' "$*" >> "$FAKE_ONBOARD_ARGS_LOG"
            npm_installed=false
            agent_installed=false
            [ -f "$FAKE_STATE_DIR/npm" ] && npm_installed=true
            [ -f "$FAKE_STATE_DIR/agent" ] && agent_installed=true

            case "$mode" in
              check-agent-cli)
                printf '{"mode":"check-agent-cli","platform":"codex","label":"Codex","command":"codex","installed":%s,"npmPackage":"@openai/codex","installCommand":"npm install -g @openai/codex@latest","runtime":{"npm":{"installed":%s}}}\n' "$agent_installed" "$npm_installed"
                ;;
              ensure-npm)
                : > "$FAKE_STATE_DIR/npm"
                printf '{"status":"installed"}\n'
                ;;
              install-agent-cli)
                if [ ! -f "$FAKE_STATE_DIR/npm" ]; then
                  printf '{"status":"npm-required"}\n'
                  exit 2
                fi
                : > "$FAKE_STATE_DIR/agent"
                printf '{"status":"installed"}\n'
                ;;
              check)
                json=false
                for arg in "$@"; do
                  [ "$arg" = "--json" ] && json=true
                done
                if [ "$json" = true ]; then
                  printf '{"runtime":{"npm":{"installed":%s}},"tools":[{"name":"rtk","installed":true},{"name":"trellis","installed":true},{"name":"gitnexus","installed":true},{"name":"java","installed":true},{"name":"maestro","installed":true}],"skills":[{"name":"caveman","installed":true}],"manualChecks":[]}\n' "$npm_installed"
                else
                  printf 'preflight check\n'
                fi
                ;;
              check-projects)
                printf '{"mode":"check-projects","projects":[]}\n'
                ;;
              plan)
                printf 'plan\n'
                ;;
              init|reset|init-projects)
                printf '%s complete\n' "$mode"
                ;;
              *)
                printf 'unexpected fake mode: %s\n' "$mode" >&2
                exit 1
                ;;
            esac
            """,
        )

    def run_installer(
        self,
        user_input: str = "",
        action: str = "init",
        projects_only: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        project_args = (
            ("--init-projects", str(self.project_root))
            if projects_only
            else (
                "--projects-root",
                str(self.project_root),
                "--action",
                action,
            )
        )
        return subprocess.run(
            (
                "/bin/bash",
                str(INSTALL_SH),
                "--platform",
                "codex",
                "--source-root",
                str(SOURCE_ROOT),
                *project_args,
                "--skip-project-agents",
                "--skip-trellis-init",
                "--no-mcp",
                "--yes",
                "--no-color",
            ),
            input=user_input,
            check=False,
            capture_output=True,
            text=True,
            env=self.env,
            timeout=30,
        )

    def modes(self) -> list[str]:
        return self.log_path.read_text(encoding="utf-8").splitlines()

    def invocation_args(self) -> list[str]:
        return self.args_log_path.read_text(encoding="utf-8").splitlines()

    def test_existing_target_cli_is_checked_before_general_preflight(self) -> None:
        (self.state_dir / "npm").touch()
        (self.state_dir / "agent").touch()

        completed = self.run_installer()

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        modes = self.modes()
        self.assertEqual(modes[0], "check-agent-cli")
        self.assertLess(modes.index("check-agent-cli"), modes.index("check"))
        self.assertNotIn("ensure-npm", modes)
        self.assertNotIn("install-agent-cli", modes)

    def test_reset_uses_the_same_early_target_agent_gate(self) -> None:
        (self.state_dir / "npm").touch()
        (self.state_dir / "agent").touch()

        completed = self.run_installer(action="reset")

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        modes = self.modes()
        self.assertEqual(modes[0], "check-agent-cli")
        self.assertLess(modes.index("check-agent-cli"), modes.index("check"))
        self.assertIn("reset", modes)

    def test_init_projects_skips_all_global_checks_and_installers(self) -> None:
        completed = self.run_installer(projects_only=True)

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        modes = self.modes()
        self.assertIn("check-projects", modes)
        self.assertIn("init-projects", modes)
        self.assertNotIn("check-agent-cli", modes)
        self.assertNotIn("check", modes)
        self.assertNotIn("ensure-npm", modes)
        self.assertNotIn("install-agent-cli", modes)
        self.assertNotIn("install-external-skills", modes)

    def test_omitted_projects_root_prompts_for_and_forwards_multiple_absolute_paths(
        self,
    ) -> None:
        (self.state_dir / "npm").touch()
        (self.state_dir / "agent").touch()
        projects_csv = f"{self.project_root},{self.project_root_two}"
        canonical_projects_csv = (
            f"{self.project_root.resolve()},{self.project_root_two.resolve()}"
        )

        completed = subprocess.run(
            (
                "/bin/bash",
                str(INSTALL_SH),
                "--platform",
                "codex",
                "--source-root",
                str(SOURCE_ROOT),
                "--action",
                "init",
                "--skip-project-agents",
                "--skip-trellis-init",
                "--no-mcp",
                "--yes",
                "--no-color",
            ),
            input=f"n\n{projects_csv}\n",
            check=False,
            capture_output=True,
            text=True,
            env=self.env,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        init_invocation = next(
            line for line in self.invocation_args() if line.split()[1:2] == ["init"]
        )
        self.assertIn(f"--projects-root {canonical_projects_csv}", init_invocation)

    def test_bash_public_flags_use_plural_projects_contract(self) -> None:
        completed = subprocess.run(
            ("/bin/bash", str(INSTALL_SH), "--help"),
            check=False,
            capture_output=True,
            text=True,
            env=self.env,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--projects-root", completed.stdout)
        self.assertIn("--init-projects", completed.stdout)
        self.assertNotIn("--project-root", completed.stdout)
        self.assertNotIn("--skills-scope", completed.stdout)
        self.assertNotIn("--project-skills-dir", completed.stdout)

    def test_bash_enforces_global_tools_skills_and_mcp_scope_policy(self) -> None:
        source = INSTALL_SH.read_text(encoding="utf-8")
        global_stage = source.split("install_missing_runtime_and_skills() {", 1)[
            1
        ].split("prompt_env_pairs() {", 1)[0]
        self.assertIn("npm install -g @mindfoldhq/trellis@latest", global_stage)
        self.assertIn("npm install -g gitnexus@latest", global_stage)
        self.assertIn("--scope global --yes", global_stage)
        self.assertNotIn("External skills install decision", global_stage)
        self.assertNotIn("Install @mindfoldhq/trellis globally?", global_stage)
        self.assertNotIn("Install gitnexus globally?", global_stage)
        self.assertIn("claude mcp add --transport stdio --scope user", source)
        self.assertIn('local target="$HOME/.omp/agent/mcp.json"', source)
        self.assertNotIn("$PROJECT_ROOT/.omp/mcp.json", source)

    def test_missing_target_cli_bootstraps_npm_then_installs_agent_before_preflight(
        self,
    ) -> None:
        completed = self.run_installer("y\ny\n")

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        modes = self.modes()
        first_check = modes.index("check")
        self.assertEqual(
            modes[:first_check],
            [
                "check-agent-cli",
                "ensure-npm",
                "check-agent-cli",
                "install-agent-cli",
                "check-agent-cli",
            ],
        )

    def test_existing_target_cli_bootstraps_required_npm_once_without_legacy_stage(
        self,
    ) -> None:
        (self.state_dir / "agent").touch()

        completed = self.run_installer()

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        modes = self.modes()
        self.assertEqual(modes[0], "check-agent-cli")
        self.assertEqual(modes.count("ensure-npm"), 1)
        source = INSTALL_SH.read_text(encoding="utf-8")
        legacy_stage = source.split("install_missing_runtime_and_skills() {", 1)[
            1
        ].split("prompt_env_pairs() {", 1)[0]
        self.assertNotIn("run_onboard ensure-npm", legacy_stage)


class PowerShellInstallerAgentCliFlowTests(unittest.TestCase):
    def test_powershell_checks_target_agent_before_action_and_removes_legacy_npm_stage(
        self,
    ) -> None:
        source = INSTALL_PS1.read_text(encoding="utf-8")
        self.assertIn("function Ensure-TargetAgentCli", source)
        interactive = source.split("function Resolve-InteractiveInputs", 1)[1].split(
            "function Install-MissingRuntimeAndSkills", 1
        )[0]
        self.assertLess(
            interactive.index("Ensure-TargetAgentCli"),
            interactive.index("if (-not $Action)"),
        )
        legacy_stage = source.split("function Install-MissingRuntimeAndSkills", 1)[
            1
        ].split("function Split-TrellisPlatforms", 1)[0]
        self.assertNotIn('Invoke-Onboard "ensure-npm"', legacy_stage)

    def test_powershell_uses_plural_projects_and_fixed_mcp_scopes(self) -> None:
        source = INSTALL_PS1.read_text(encoding="utf-8")
        parameter_block = source.split(")\n\n$ErrorActionPreference", 1)[0]
        self.assertIn("$ProjectsRoot", parameter_block)
        self.assertIn("$InitProjects", parameter_block)
        self.assertNotIn("$ProjectRoot", parameter_block)
        self.assertNotIn("$SkillsScope", parameter_block)
        self.assertIn('"--scope", "user"', source)
        self.assertIn('Join-Path $HOME ".omp/agent/mcp.json"', source)
        self.assertNotIn('Join-Path $ProjectRoot ".omp/mcp.json"', source)


if __name__ == "__main__":
    unittest.main()
