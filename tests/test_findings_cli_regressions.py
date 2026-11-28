from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "sbtd-workflow-onboard" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import onboard


class FindingsCliRegressionTests(unittest.TestCase):
    def test_missing_migration_module_returns_sanitized_blocked_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = root / "skill"
            shutil.copytree(
                SCRIPTS.parent, skill, ignore=shutil.ignore_patterns("__pycache__")
            )
            scripts = skill / "scripts"
            (scripts / "sbtd_migration_files.py").unlink()
            home = root / "home"
            home.mkdir()
            environment = os.environ.copy()
            environment.pop("PYTHONPATH", None)  # Exercise the incomplete copy, not the checkout.
            environment.update(
                HOME=str(home), USERPROFILE=str(home), CODEX_HOME=str(home / ".codex")
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(scripts / "onboard.py"),
                    "migration",
                    "--phase",
                    "apply",
                    "--manifest",
                    str(root / "manifest.json"),
                    "--json",
                ],
                capture_output=True,
                text=True,
                env=environment,
                timeout=30,
                check=False,
            )
            self.assertEqual(completed.returncode, 2, completed.stderr)
            response = json.loads(completed.stdout)
            self.assertEqual(response["status"], "blocked")
            self.assertEqual(response["migration"], {})
            self.assertIn("runtime", response["reason"])
            self.assertNotIn("Traceback", completed.stderr)
            self.assertEqual(list(home.iterdir()), [])

    def test_installers_reject_missing_state_module_before_invoking_python(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "incomplete"
            for relative in (
                "SKILL.md",
                "REFERENCE.md",
                "catalog.json",
                "catalog.schema.json",
                "templates/agents/AGENTS.global.md",
                "templates/agents/AGENTS.project.md",
                "assets/external-skills/stable/MANIFEST.json",
                "scripts/onboard.py",
            ):
                target = source / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(
                    'print("UNEXPECTED_CLI_EXECUTION")\n'
                    if relative.endswith("onboard.py")
                    else "fixture\n"
                )
            (source / "templates/skills").mkdir()
            runners = []
            bash = shutil.which("bash")
            if bash:
                runners.append(
                    [
                        bash,
                        str(ROOT / "install.sh"),
                        "migration",
                        "--source-root",
                        str(source),
                    ]
                )
            pwsh = shutil.which("pwsh")
            if pwsh:
                runners.append(
                    [
                        pwsh,
                        "-NoProfile",
                        "-File",
                        str(ROOT / "install.ps1"),
                        "-WorkflowMode",
                        "migration",
                        "-SourceRoot",
                        str(source),
                    ]
                )
            if not runners:
                self.skipTest("no supported installer interpreter")
            for command in runners:
                with self.subTest(interpreter=command[0]):
                    completed = subprocess.run(
                        command, capture_output=True, text=True, timeout=30, check=False
                    )
                    self.assertNotEqual(completed.returncode, 0)
                    combined = completed.stdout + completed.stderr
                    self.assertIn("scripts/sbtd_project.py", combined)
                    self.assertNotIn("UNEXPECTED_CLI_EXECUTION", combined)

    def test_missing_optional_runtime_is_not_an_installation_failure(self):
        runtime = {
            name: {
                "installed": False,
                "path": None,
                "version": None,
                "advice": "prepare only when needed",
            }
            for name in ("npm", "node", "nvm")
        }
        runtime["advice"] = "prepare only when needed"
        report = onboard.build_installation_report(
            {
                "runtime": runtime,
                "tools": [],
                "skills": [],
                "manualChecks": [],
            }
        )
        self.assertEqual(report["failedOrMissing"]["runtime"], [])
        self.assertEqual(report["summary"]["failedOrMissing"], 0)
        self.assertEqual(
            {entry["name"] for entry in report["conditionalRuntime"]},
            {"npm", "node", "nvm"},
        )
        self.assertTrue(
            all(
                entry["status"] == "conditional"
                for entry in report["conditionalRuntime"]
            )
        )


if __name__ == "__main__":
    unittest.main()
