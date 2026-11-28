"""Real Onboard CLI checks at the shared-launcher overwrite boundary."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard" / "scripts"


sys.path.insert(0, str(SCRIPTS))
from onboard_contracts import canonical_json_bytes, operation_id, resource_id


class GlobalRetirementTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.home = self.root / "home"
        self.codex = self.home / ".codex"
        self.codex.mkdir(parents=True)
        self.skills = self.home / "skills"
        self.launcher = self.skills / "sbtd-workflow-onboard/scripts/sbtd_graft_entry.py"
        self.launcher.parent.mkdir(parents=True)
        self.launcher.write_bytes(b"synthetic old launcher; must not execute\n")
        self.config = self.codex / "config.toml"
        self.env = {k: os.environ[k] for k in ("SystemRoot", "WINDIR", "COMSPEC", "TEMP", "TMP") if k in os.environ}
        self.env.update(HOME=str(self.home), USERPROFILE=str(self.home), CODEX_HOME=str(self.codex),
                        PATH=str(self.root / "empty-bin"), PYTHONDONTWRITEBYTECODE="1", DO_NOT_TRACK="1")

    def cli(self, mode, *args):
        run = subprocess.run([sys.executable, "-B", str(SCRIPTS / "onboard.py"), mode,
                              "--global-skills-dir", str(self.skills), "--json", *args],
                             env=self.env, cwd=self.root, capture_output=True, text=True, timeout=30)
        return run.returncode, json.loads(run.stdout)

    def set_server(self, owned_shape=True):
        args = ["-E", "-s", str(self.launcher), "mcp", "--node", str(self.root / "node"),
                "--entry", str(self.root / "cli.js")] if owned_shape else []
        raw = ("[mcp_servers.sbtd-graft]\n" + "command = " + json.dumps(sys.executable) + "\nargs = "
               + json.dumps(args) + '\nenv = { DO_NOT_TRACK = "1", DNT = "1" }\n').encode()
        self.config.write_bytes(raw)
        return raw

    def test_present_launcher_and_unproven_binding_stop_reset_before_installation(self):
        raw = self.set_server()
        before = self.launcher.read_bytes()
        for mode, extra in (("plan", ["--action", "reset"]), ("reset", ["--yes"])):
            with self.subTest(mode=mode):
                code, document = self.cli(mode, "--platform", "codex", *extra)
                self.assertEqual(code, 2)
                self.assertTrue(document["graftRetirement"]["blocked"])
                self.assertEqual(self.config.read_bytes(), raw)
                self.assertEqual(self.launcher.read_bytes(), before)
                self.assertFalse((self.codex / "AGENTS.md").exists())

    def test_proven_reset_requires_displayed_confirmation_and_supports_rollback(self):
        raw = self.set_server()
        vault = self.root / "vault"
        vault.mkdir(mode=0o700)
        identity = resource_id("toml", str(self.config))
        history = vault / "rc2-output.json"
        history.write_bytes(canonical_json_bytes({"graftWiring": {"operationResults": [{
            "phase": "deploy", "resource_id": identity,
            "operation_ids": [operation_id("deploy", identity, "graft-mcp")],
            "dependent_projects": [], "status": "succeeded", "error": None,
            "before": {"type": "absent", "checksum": None}, "backup_ref": None,
            "after": {"type": "file", "checksum": hashlib.sha256(raw).hexdigest()},
        }]}}))
        binding = {"schema": "sbtd-retirement-evidence/1",
                   "items": [{"kind": "operation-results", "path": str(history)}]}
        descriptor = vault / "descriptor.json"
        descriptor.write_bytes(canonical_json_bytes({
            "schema_version": 1, "payload": binding,
            "descriptor_id": hashlib.sha256(canonical_json_bytes(binding)).hexdigest(),
        }))
        args = ("--platform", "codex", "--retirement-backup-root", str(vault),
                "--retirement-evidence", str(descriptor))
        code, plan = self.cli("plan", "--action", "reset", *args)
        self.assertEqual(code, 0, plan["graftRetirement"])
        view = plan["graftRetirement"]
        self.assertEqual(view["targetsToRetire"], [str(self.config)])
        self.assertIn(str(self.config), view["globalEffects"])
        self.assertRegex(view["confirmationId"], r"^[a-f0-9]{64}$")
        code, refused = self.cli("reset", "--yes", *args)
        self.assertEqual((code, refused["retirementResult"]["status"]), (2, "blocked"))
        self.assertEqual(self.config.read_bytes(), raw)
        self.assertTrue(self.launcher.exists())
        self.assertEqual(set(vault.iterdir()), {history, descriptor})

        mode = self.config.stat().st_mode & 0o777
        code, applied = self.cli("reset", "--yes", "--confirm-retirement", view["confirmationId"], *args)
        self.assertEqual(code, 0, applied)
        receipt = applied["retirementResult"]
        self.assertEqual(receipt["status"], "cleaned")
        self.assertFalse(self.config.exists())
        self.assertFalse(self.launcher.exists())
        rollback = subprocess.run([
            sys.executable, "-B", str(SCRIPTS / "onboard.py"), "cleanup-legacy",
            "--phase", "rollback", "--plan", receipt["plan_path"],
            "--cleanup-receipt", receipt["receipt_path"],
            "--confirm-cleanup", receipt["retirement_plan_id"], "--json",
        ], cwd=self.root, env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(rollback.returncode, 0, rollback.stdout)
        self.assertEqual(json.loads(rollback.stdout)["status"], "rolled-back")
        self.assertEqual(self.config.read_bytes(), raw)
        self.assertEqual(self.config.stat().st_mode & 0o777, mode)
        self.assertFalse(self.launcher.exists())  # Restores configuration, not deleted software.

    def test_overwritten_onboard_is_reported_without_recreating_launcher(self):
        raw = self.set_server()
        self.launcher.unlink()  # npx-style replacement of the fixture Onboard payload
        code, document = self.cli("check", "--platform", "codex")
        self.assertEqual(code, 0)
        items = document["graftRetirement"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["path"], str(self.config))
        self.assertTrue(items[0]["launcher"] is not None and not items[0]["launcher"]["present"])
        self.assertFalse(items[0]["write_authority"])
        self.assertEqual(self.config.read_bytes(), raw)
        self.assertFalse(self.launcher.exists())

    def test_unrelated_third_party_entry_does_not_authorize_retirement(self):
        raw = self.set_server(owned_shape=False)
        code, document = self.cli("plan", "--action", "reset", "--platform", "codex")
        self.assertEqual(code, 0)
        report = document["graftRetirement"]
        self.assertFalse(report["blocked"])
        self.assertEqual(report["targetsToRetire"], [])
        self.assertEqual(self.config.read_bytes(), raw)

    def test_omp_check_inspects_only_the_effective_profile_or_override(self):
        default = self.home / ".omp" / "agent" / "mcp.json"
        named = self.home / ".omp" / "profiles" / "work" / "agent" / "mcp.json"
        override = self.home / "private-agent" / "mcp.json"
        self.launcher.unlink()
        server = {
            "type": "stdio", "command": sys.executable,
            "args": ["-E", "-s", str(self.launcher), "mcp", "--node",
                     str(self.root / "node"), "--entry", str(self.root / "cli.js")],
            "env": {"DO_NOT_TRACK": "1", "DNT": "1"},
        }
        original = json.dumps({"mcpServers": {"sbtd-graft": server}}).encode()
        for config in (default, named, override):
            config.parent.mkdir(parents=True)
            config.write_bytes(original)
        self.env["PI_CODING_AGENT_DIR"] = str(override.parent)
        for profile, expected in (("", override), ("work", named)):
            with self.subTest(profile=profile):
                self.env["OMP_PROFILE"] = profile
                code, report = self.cli("check", "--platform", "omp")
                self.assertEqual(code, 0)
                rows = report["graftRetirement"]["items"]
                self.assertEqual([row["path"] for row in rows], [str(expected)])
                self.assertFalse(rows[0]["launcher"]["present"])
                self.assertFalse(rows[0]["write_authority"])
                for path in (default, named, override):
                    self.assertEqual(path.read_bytes(), original)

    def test_unproven_project_fence_is_not_replaced_by_reset_template(self):
        project = self.root / "project"
        project.mkdir()
        rules = project / "AGENTS.md"
        original = b"project-owned\n<!-- graft:start -->\ncustom\n<!-- graft:end -->\n"
        rules.write_bytes(original)
        for mode, extra in (("plan", ["--action", "reset"]), ("reset", ["--yes"])):
            with self.subTest(mode=mode):
                code, result = self.cli(mode, "--platform", "codex",
                                        "--projects-root", str(project), *extra)
                self.assertEqual(code, 2)
                self.assertTrue(result["graftRetirement"]["blocked"])
                self.assertEqual(rules.read_bytes(), original)
                self.assertFalse((project / ".gitignore").exists())

    def test_rootless_reset_does_not_guess_which_domain_to_retire(self):
        code, document = self.cli("plan", "--action", "reset")
        self.assertEqual(code, 2)
        self.assertTrue(document["graftRetirement"]["blocked"])
        self.assertTrue(self.launcher.exists())


if __name__ == "__main__":
    unittest.main()
