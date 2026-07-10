from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ONBOARD = ROOT / "kuno-workflow-onboard-skills" / "scripts" / "onboard.py"


class MultiProjectOnboardCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="kuno-multi-project-test-")
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.codex_home = self.home / ".codex"
        self.project_one = self.root / "project-one"
        self.project_two = self.root / "project-two"
        self.project_one.mkdir()
        self.project_two.mkdir()
        self.projects_csv = f"{self.project_one},{self.project_two}"
        self.env = os.environ.copy()
        self.env["HOME"] = str(self.home)
        self.env["CODEX_HOME"] = str(self.codex_home)

    def write_executable(self, name: str, body: str) -> Path:
        bin_dir = self.root / "bin"
        bin_dir.mkdir(exist_ok=True)
        target = bin_dir / name
        target.write_text(body, encoding="utf-8")
        target.chmod(target.stat().st_mode | stat.S_IXUSR)
        self.env["PATH"] = os.pathsep.join(
            (str(bin_dir), self.env.get("PATH", "/usr/bin:/bin"))
        )
        return target

    def run_onboard(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            (sys.executable, str(ONBOARD), *args),
            check=False,
            capture_output=True,
            text=True,
            env=self.env,
            timeout=30,
        )

    def test_check_projects_reports_each_root_without_global_install_checks(
        self,
    ) -> None:
        (self.project_one / "package.json").write_text(
            json.dumps({"dependencies": {"react": "latest"}}),
            encoding="utf-8",
        )
        (self.project_one / "components.json").write_text("{}\n", encoding="utf-8")
        (self.project_two / "tests" / "e2e").mkdir(parents=True)

        completed = self.run_onboard(
            "check-projects",
            "--projects-root",
            self.projects_csv,
            "--json",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["mode"], "check-projects")
        self.assertEqual(
            [item["projectRoot"] for item in payload["projects"]],
            [str(self.project_one.resolve()), str(self.project_two.resolve())],
        )
        self.assertTrue(payload["projects"][0]["reactBits"]["applicable"])
        self.assertTrue(payload["projects"][1]["playwright"]["applicable"])
        self.assertNotIn("runtime", payload)
        self.assertNotIn("tools", payload)
        self.assertNotIn("skills", payload)

    def test_projects_root_rejects_relative_paths(self) -> None:
        completed = self.run_onboard(
            "check-projects",
            "--projects-root",
            "relative-project",
            "--json",
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("absolute", completed.stderr)

    def test_plan_installs_global_bundle_once_and_project_files_for_every_root(
        self,
    ) -> None:
        completed = self.run_onboard(
            "plan",
            "--projects-root",
            self.projects_csv,
            "--json",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        targets = [item["target"] for item in payload["operations"]]
        self.assertIn(str(self.project_one.resolve() / "AGENTS.md"), targets)
        self.assertIn(str(self.project_two.resolve() / "AGENTS.md"), targets)
        self.assertIn(str(self.project_one.resolve() / ".gitignore"), targets)
        self.assertIn(str(self.project_two.resolve() / ".gitignore"), targets)
        self.assertIn(
            str(self.codex_home.resolve() / "skills" / "trellis-workflow"),
            targets,
        )
        self.assertNotIn(
            str(self.project_one.resolve() / ".agent" / "skills" / "trellis-workflow"),
            targets,
        )
        self.assertNotIn(
            str(self.project_two.resolve() / ".agent" / "skills" / "trellis-workflow"),
            targets,
        )

    def test_init_projects_writes_only_project_files(self) -> None:
        completed = self.run_onboard(
            "init-projects",
            "--projects-root",
            self.projects_csv,
            "--skip-trellis-init",
            "--yes",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertTrue((self.project_one / "AGENTS.md").is_file())
        self.assertTrue((self.project_two / "AGENTS.md").is_file())
        self.assertTrue((self.project_one / ".gitignore").is_file())
        self.assertTrue((self.project_two / ".gitignore").is_file())
        self.assertFalse((self.codex_home / "AGENTS.md").exists())
        self.assertFalse((self.codex_home / "skills").exists())

    def test_external_skill_project_scope_is_rejected(self) -> None:
        completed = self.run_onboard(
            "install-external-skills",
            "--all",
            "--scope",
            "project",
            "--yes",
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("invalid choice", completed.stderr)

    def test_onboard_public_flags_remove_project_skill_scope(self) -> None:
        completed = self.run_onboard("plan", "--help")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--projects-root", completed.stdout)
        self.assertNotIn("--project-root", completed.stdout)
        self.assertNotIn("--skills-scope", completed.stdout)
        self.assertNotIn("--project-skills-dir", completed.stdout)

    def test_normal_init_keeps_all_skill_targets_global(self) -> None:
        global_skills = self.root / "global-skills"
        external_names = (
            "diagnosing-bugs",
            "tdd",
            "grill-me",
            "grill-with-docs",
            "grilling",
            "domain-modeling",
            "codebase-design",
            "handoff",
            "writing-great-skills",
            "to-spec",
            "to-tickets",
            "impeccable",
            "ui-ux-pro-max",
            "web-ui-autotest-generator",
            "shadcn",
        )
        for name in external_names:
            target = global_skills / name
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text(
                f"---\nname: {name}\n---\n",
                encoding="utf-8",
            )

        completed = self.run_onboard(
            "init",
            "--projects-root",
            self.projects_csv,
            "--global-skills-dir",
            str(global_skills),
            "--global-agents-path",
            str(self.root / "global-AGENTS.md"),
            "--skip-trellis-init",
            "--yes",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertTrue((global_skills / "trellis-workflow" / "SKILL.md").is_file())
        self.assertFalse((self.project_one / ".agent" / "skills").exists())
        self.assertFalse((self.project_two / ".agent" / "skills").exists())

    def test_init_projects_checks_trellis_and_bootstrap_for_every_root(self) -> None:
        bootstrap = self.project_two / ".trellis" / "tasks" / "00-bootstrap-guidelines"
        bootstrap.mkdir(parents=True)
        self.write_executable(
            "trellis",
            """#!/bin/sh
if [ "$1" = "--version" ]; then
  echo "trellis 9.9.9"
  exit 0
fi
if [ "$1" = "init" ]; then
  mkdir -p .trellis
  exit 0
fi
exit 1
""",
        )

        completed = self.run_onboard(
            "init-projects",
            "--projects-root",
            self.projects_csv,
            "--trellis-user",
            "developer",
            "--yes",
        )

        self.assertEqual(completed.returncode, 6, completed.stderr or completed.stdout)
        self.assertTrue((self.project_one / ".trellis").is_dir())
        self.assertIn(str(bootstrap.resolve()), completed.stdout)


if __name__ == "__main__":
    unittest.main()
