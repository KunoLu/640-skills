"""Public CLI scenarios U01/U03/U06: read-only planning and guarded upgrade."""
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
CLI = ROOT / "sbtd-workflow-onboard/scripts/onboard.py"
sys.path.insert(0, str(CLI.parent))

from sbtd_migration_files import require_private_directory


class UpgradeCliTests(unittest.TestCase):
    def test_canonical_license_checkout_keeps_lf_bytes(self):
        """U14: autocrlf cannot change the canonical license versus its payload."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            environment = {
                key: value for key, value in os.environ.items()
                if not key.startswith("GIT_")
            }
            environment.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
            subprocess.run(
                ["git", "init", "-q", str(root)], env=environment,
                check=True, capture_output=True,
            )
            (root / ".gitattributes").write_bytes((ROOT / ".gitattributes").read_bytes())
            expected = (CLI.parents[1] / "LICENSE").read_bytes()
            root_license = root / "LICENSE"
            root_license.write_bytes((ROOT / "LICENSE").read_bytes())
            bundled_license = root / "sbtd-workflow-onboard/LICENSE"
            bundled_license.parent.mkdir()
            bundled_license.write_bytes(expected)
            subprocess.run(
                ["git", "-C", str(root), "-c", "core.autocrlf=true", "add", "."],
                env=environment, check=True, capture_output=True,
            )
            root_license.unlink()
            bundled_license.unlink()
            subprocess.run(
                ["git", "-C", str(root), "-c", "core.autocrlf=true", "checkout-index", "-a", "-f"],
                env=environment, check=True, capture_output=True,
            )
            self.assertEqual(root_license.read_bytes(), expected)
            self.assertEqual(bundled_license.read_bytes(), expected)

    def test_plan_describes_missing_payload_without_writing_targets(self):
        """U01: a real plan inventories payload, but never initializes the target."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            vault = root / "vault"
            require_private_directory(vault, create=True)
            target = root / "skills"
            scope = root / "scope.json"
            scope.write_text(json.dumps({"schema_version": 1, "skills_roots": [str(target)]}), encoding="utf-8")
            environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            result = subprocess.run(
                [sys.executable, "-B", str(CLI), "upgrade", "--phase", "plan",
                 "--scope", str(scope), "--backup-root", str(vault), "--json"],
                capture_output=True, text=True, env=environment, timeout=120, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            document = json.loads(result.stdout)
            plan = document.get("plan", document)
            payload = plan.get("payload", plan)
            resources = {Path(row["target"]).name: row for row in payload["resources"]}
            self.assertEqual(resources["sbtd-task"]["classification"], "missing")
            self.assertEqual(resources["diagnosing-bugs"]["decision"], "install")
            self.assertFalse(target.exists())
            self.assertEqual(list(vault.iterdir()), [])

    def test_upgrade_rejects_cross_phase_or_legacy_recovery_arguments(self):
        """U06: consent for one phase cannot widen another phase's scope."""
        commands = [
            ["upgrade", "--phase", "plan", "--scope", "/scope", "--backup-root", "/vault", "--yes"],
            ["upgrade", "--phase", "apply", "--plan", "/plan", "--scope", "/scope"],
            ["upgrade", "--phase", "verify", "--plan", "/plan", "--yes"],
            ["recovery", "--phase", "plan", "--upgrade-plan", "/plan",
             "--upgrade-receipt", "/receipt", "--manifest", "/legacy"],
            ["recovery", "--phase", "apply", "--upgrade-recovery-plan", "/plan",
             "--upgrade-plan", "/another-plan"],
        ]
        for command in commands:
            with self.subTest(command=command):
                result = subprocess.run(
                    [sys.executable, "-B", str(CLI), *command],
                    capture_output=True, text=True, timeout=30, check=False,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("invalid arguments", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_missing_probe_consent_does_not_read_plan_or_launch_host(self):
        """U11: probe permission is independent from the readonly verify phase."""
        result = subprocess.run(
            [sys.executable, "-B", str(CLI), "upgrade", "--phase", "verify",
             "--plan", "/nonexistent-upgrade-plan.json", "--probe", "--json"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["reason"], "probe-confirmation-required")

    def test_empty_upgrade_recovery_paths_return_redacted_json_not_legacy_traceback(self):
        """U06/U15: an empty upgrade path cannot route into legacy recovery."""
        result = subprocess.run(
            [sys.executable, "-B", str(CLI), "recovery", "--phase", "plan",
             "--upgrade-plan", "", "--upgrade-receipt", "", "--json"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "blocked")
        self.assertNotIn("Traceback", result.stderr)

    def test_blank_vault_or_supplied_receipt_never_defaults_to_cwd_or_absence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            vault = root / "vault"
            require_private_directory(vault, create=True)
            scope = root / "scope.json"
            scope.write_text(json.dumps({
                "schema_version": 1, "agents_targets": [str(root / "AGENTS.md")],
            }), encoding="utf-8")
            command = [sys.executable, "-B", str(CLI)]
            blank_vault = subprocess.run(
                [*command, "upgrade", "--phase", "plan", "--scope", str(scope),
                 "--backup-root", "", "--json"], cwd=vault,
                capture_output=True, text=True, timeout=60, check=False,
            )
            self.assertEqual(blank_vault.returncode, 2)
            self.assertEqual(json.loads(blank_vault.stdout)["reason"], "invalid-input")
            self.assertEqual(list(vault.iterdir()), [])
            plan_file = vault / "plan.json"
            plan = subprocess.run(
                [*command, "upgrade", "--phase", "plan", "--scope", str(scope),
                 "--backup-root", str(vault), "--output", str(plan_file), "--json"],
                capture_output=True, text=True, timeout=60, check=False,
            )
            self.assertEqual(plan.returncode, 0, plan.stderr + plan.stdout)
            verify = subprocess.run(
                [*command, "upgrade", "--phase", "verify", "--plan", str(plan_file),
                 "--receipt", "", "--json"], capture_output=True, text=True, timeout=60, check=False,
            )
            self.assertEqual(verify.returncode, 2)
            self.assertEqual(json.loads(verify.stdout)["reason"], "invalid-input")
            self.assertFalse((root / "AGENTS.md").exists())

    def test_installed_copy_retries_and_recovers_without_original_source(self):
        """U03/U07/U09: a real installed package owns the public lifecycle."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / "bootstrap"
            shutil.copytree(CLI.parents[1], source, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            skills = root / "skills"
            old = skills / "sbtd-workflow-onboard"
            old.mkdir(parents=True)
            original = b"---\nname: sbtd-workflow-onboard\n---\nold installed payload\n"
            (old / "SKILL.md").write_bytes(original)
            vault = root / "vault"
            require_private_directory(vault, create=True)
            config_home = root / "codex"
            config = config_home / "config.toml"
            profile = root / ".bashrc"
            cli_entry = root / "cli.js"
            cli_entry.write_text("// Not executed: configuration-only runtime fixture.\n", encoding="utf-8")
            runtime = {"python": sys.executable, "node": sys.executable, "cli": str(cli_entry)}
            scope = root / "scope.json"
            scope.write_text(json.dumps({
                "schema_version": 1, "skills_roots": [str(skills)],
                "decisions": {str(old): "replace"},
                "hosts": [{
                    "id": "selected-codex", "platform": "codex",
                    "config_home": str(config_home), "config": str(config),
                    "skills_roots": [str(skills)], "runtime": runtime, "project_roots": [],
                }],
                "shell_profiles": [{"path": str(profile), "shell": "bash", "bin": str(root / "bin")}],
            }), encoding="utf-8")
            plan_path = vault / "plan.json"

            def invoke(package, *arguments):
                result = subprocess.run(
                    [sys.executable, "-B", str(package / "scripts/onboard.py"), *arguments, "--json"],
                    capture_output=True, text=True, timeout=180, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                return json.loads(result.stdout)

            plan = invoke(source, "upgrade", "--phase", "plan", "--scope", str(scope),
                          "--backup-root", str(vault), "--output", str(plan_path))["plan"]
            installed = invoke(source, "upgrade", "--phase", "apply", "--plan", str(plan_path),
                               "--confirm-plan", plan["plan_id"], "--yes")
            self.assertEqual(installed["status"], "complete")
            configured = config.read_text(encoding="utf-8")
            self.assertIn(str(old / "scripts/sbtd_graft_entry.py").replace("\\", "\\\\"), configured)
            self.assertNotIn(str(source), configured)
            shutil.rmtree(source)  # Only the test-owned bootstrap, never user source.
            retry = invoke(old, "upgrade", "--phase", "apply", "--plan", str(plan_path),
                           "--confirm-plan", plan["plan_id"], "--yes",
                           "--receipt", installed["receipt_path"])
            self.assertEqual(retry["status"], "complete")
            recovery_path = vault / "recovery.json"
            recovery = invoke(old, "recovery", "--phase", "plan", "--upgrade-plan", str(plan_path),
                              "--upgrade-receipt", retry["receipt_path"],
                              "--output", str(recovery_path))["plan"]
            restored = invoke(old, "recovery", "--phase", "apply",
                              "--upgrade-recovery-plan", str(recovery_path),
                              "--confirm-recovery", recovery["recovery_id"])
            self.assertEqual(restored["status"], "complete")
            self.assertEqual((old / "SKILL.md").read_bytes(), original)
            self.assertFalse((skills / "sbtd-task").exists())
            self.assertFalse((old / "scripts").exists())
            self.assertFalse(config.exists())
            self.assertFalse(profile.exists())
            self.assertTrue(Path(installed["receipt_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
