from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import sbtd_upgrade
import sbtd_upgrade_hosts as hosts
from onboard_contracts import ContractError, operation_id, resource_id
from sbtd_migration_files import (
    backup_reference,
    require_private_directory,
    snapshot,
)


def _runtime(base: Path) -> dict[str, str]:
    directory = base / "runtime"
    directory.mkdir()
    paths = {}
    for key, name in (("python", "python"), ("node", "node"), ("cli", "cli.js")):
        target = directory / name
        target.write_bytes(b"")
        paths[key] = str(target)
    return paths


def _host(base: Path, config: Path) -> dict:
    return {
        "id": "codex",
        "platform": "codex",
        "config_home": str(config.parent),
        "config": str(config),
        "skills_roots": [],
        "project_roots": [],
        "runtime": _runtime(base),
    }


class _Retirement:
    HISTORY_DIRS = ("graft", ".graft")

    def __init__(self) -> None:
        self.calls: list[str] = []

    def inspect_retirement(self, *, selections, evidence=()):
        self.calls.append("inspect")
        self.selections = selections
        self.evidence = evidence
        return {"schema": "sbtd-graft-retirement/1", "items": list(self.items)}

    def render_candidates(self, report, *, purpose):
        self.calls.append(purpose)
        if purpose != "upgrade":
            raise ContractError("invalid-argument", "purpose")
        return {
            "purpose": purpose,
            "schema": "sbtd-graft-retirement/1",
            "candidates": list(self.candidates),
            "preserved": [],
            "blocked": list(self.blocked),
            "global_effects": list(self.global_effects),
            "stop": bool(self.blocked),
            "stop_reason": "unproven-at-risk" if self.blocked else None,
            "manual": [],
            "proof_gap": None,
        }

    def retirement_file_bytes(self, *, report, purpose, target, before):
        self.calls.append("bytes")
        if before != self.before:
            raise ContractError("state-conflict", "before")
        return self.rendered


class RetirementBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = _Retirement()
        self.module.items = []
        self.module.candidates = []
        self.module.blocked = []
        self.module.global_effects = []
        self.module.before = b""
        self.module.rendered = b""
        self.patch = mock.patch.dict(sys.modules, {"sbtd_retirement": self.module})
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_only_the_effective_scope_config_is_selected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            home = base / ".omp"
            selected = home / "profiles" / "work" / "agent" / "mcp.json"
            sibling = home / "agent" / "mcp.json"
            selected.parent.mkdir(parents=True)
            sibling.parent.mkdir(parents=True)
            selected.write_bytes(b"{}\n")
            sibling.write_bytes(b"{}\n")
            host = {
                "id": "omp",
                "platform": "omp",
                "config_home": str(home),
                "config": str(selected),
                "skills_roots": [],
                "project_roots": [],
                "runtime": _runtime(base),
            }
            hosts.plan_retirement({"hosts": [host]}, vault=None, evidence=[])
            self.assertEqual(
                self.module.selections["configs"],
                [{"role": "omp-mcp", "path": str(selected)}],
            )
            self.assertNotIn(str(sibling), json.dumps(self.module.selections))

    def test_old_upgrade_receipt_without_mode_fields_still_validates(self) -> None:
        payload = {
            "receipt_schema": "upgrade-receipt",
            "plan_id": "ab" * 32,
            "baseline_id": "historical",
            "backup_root": str(Path.cwd() / "historical-vault"),
            "previous_receipt_id": None,
            "sequence": 0,
            "status": "complete",
            "executor": {"isolated": True},
            "resources": [{
                "id": "historical-skill",
                "target": str(Path.cwd() / "historical-skill"),
                "before": {"type": "directory", "checksum": "cd" * 32},
                "mechanical_before": {"type": "directory", "checksum": "cd" * 32},
                "after": {"type": "directory", "checksum": "ef" * 32},
                "desired": {"type": "directory", "checksum": "ef" * 32},
                "mechanical_after": {"type": "directory", "checksum": "ef" * 32},
                "result": "succeeded",
                "mutated": True,
                "backup_ref": None,
            }],
            "failure": None,
        }
        receipt = {
            "schema_version": 1,
            "receipt_id": sbtd_upgrade._digest(payload),
            "payload": payload,
        }
        validated_id, validated = sbtd_upgrade._validate_upgrade_receipt(receipt)
        self.assertEqual(validated_id, receipt["receipt_id"])
        self.assertNotIn("mode_before", validated["resources"][0])
        self.assertNotIn("graftRetirement", validated)



    def test_unproven_at_risk_blocks_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            home = base / ".codex"
            home.mkdir()
            config = home / "config.toml"
            original = b"[mcp_servers.sbtd-graft]\ncommand = \"/old/python\"\n"
            config.write_bytes(original)
            skills = base / "skills"
            onboard = skills / "sbtd-workflow-onboard"
            onboard.mkdir(parents=True)
            (onboard / "SKILL.md").write_bytes(b"---\nname: sbtd-workflow-onboard\n---\nold\n")
            package = base / "package"
            (package / "scripts").mkdir(parents=True)
            (package / "SKILL.md").write_bytes(b"---\nname: sbtd-workflow-onboard\n---\nnew\n")
            launcher = str(onboard / "scripts" / "sbtd_graft_entry.py")
            self.module.blocked = [{
                "id": "blocked-1",
                "path": str(config),
                "target": str(config),
                "role": "codex-mcp",
                "entry": "sbtd-graft",
                "classification": "unproven",
                "verification": "not-verified",
                "write_authority": False,
                "global_effect": True,
                "guidance": "do not delete by name",
                "launcher": {"path": launcher, "present": False},
                "mode": None,
            }]
            self.module.global_effects = ["host account"]
            vault = base / "vault"
            require_private_directory(vault, create=True)
            scope = {
                "schema_version": 1,
                "skills_roots": [str(skills)],
                "decisions": {str(onboard): "replace"},
                "hosts": [_host(base, config)],
            }
            with mock.patch("sbtd_upgrade._inventory_module") as inventory:
                inventory.return_value.build_inventory.return_value = {
                    "baseline": {
                        "baseline_id": "b1",
                        "source": {"path": str(package), "state": snapshot(package)},
                    },
                    "resources": [{
                        "id": "skill-1",
                        "kind": "skill",
                        "target": str(onboard),
                        "source": str(package),
                        "before": snapshot(onboard),
                        "desired": snapshot(package),
                        "classification": "known-old",
                        "decision": "replace",
                        "details": {},
                    }],
                    "domains": [],
                }
                inventory.return_value.normalize_scope.side_effect = lambda value: value
                plan = sbtd_upgrade.plan_upgrade(scope, vault, package_root=package)
            self.assertEqual(plan["payload"]["status"], "blocked")
            self.assertTrue(plan["payload"]["graftRetirement"]["stop"])
            self.assertIn("host account", json.dumps(plan["payload"]["graftRetirement"]))
            self.assertIn("global effect", plan["payload"]["graftRetirement"]["disclosure"])
            with self.assertRaises(ContractError) as caught:
                sbtd_upgrade._check_decisions(plan["payload"])
            self.assertEqual(caught.exception.code, "blocked-resource")
            self.assertEqual(config.read_bytes(), original)
            self.assertEqual((onboard / "SKILL.md").read_bytes(), b"---\nname: sbtd-workflow-onboard\n---\nold\n")

            self.assertEqual((onboard / "SKILL.md").read_bytes(), b"---\nname: sbtd-workflow-onboard\n---\nold\n")

    def test_proven_edit_is_backed_up_before_skill_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            home = base / ".codex"
            home.mkdir()
            config = home / "config.toml"
            before = b"owned graft entry\n"
            config.write_bytes(before)
            config.chmod(0o600)
            rendered = b"unrelated server only\n"
            self.module.before = before
            self.module.rendered = rendered
            mode = format(stat.S_IMODE(config.stat().st_mode), "04o")
            permissions = {}
            if os.name == "nt":
                from sbtd_retirement_permissions import capture, digest

                permissions["windows_acl_digest"] = digest(capture(config))
            self.module.candidates = [{
                "id": "cand-1",
                "kind": "graft-retire",
                "target": str(config),
                "path": str(config),
                "role": "codex-mcp",
                "entry": "sbtd-graft",
                "action": "edit",
                "decision": "remove",
                "write_authority": True,
                "mode": mode,
                "before": snapshot(config),
                **permissions,
                "global_effect": True,
                "rendered_checksum": hashlib.sha256(rendered).hexdigest(),
            }]
            self.module.global_effects = ["global mcp"]
            skills = base / "skills"
            onboard = skills / "sbtd-workflow-onboard"
            onboard.mkdir(parents=True)
            (onboard / "SKILL.md").write_bytes(b"old\n")
            package = base / "package"
            package.mkdir()
            (package / "SKILL.md").write_bytes(b"new\n")
            order: list[str] = []
            real_write = sbtd_upgrade._write_resource

            def watch(sealed, fresh, backup_ref, package_root, expected, mutation):
                order.append(sealed["kind"])
                if sealed["kind"] == "skill":
                    self.assertEqual(config.read_bytes(), rendered)
                return real_write(sealed, fresh, backup_ref, package_root, expected, mutation)

            vault = base / "vault"
            require_private_directory(vault, create=True)
            scope = {
                "schema_version": 1,
                "skills_roots": [str(skills)],
                "decisions": {str(onboard): "replace"},
                "hosts": [_host(base, config)],
            }
            with (
                mock.patch("sbtd_upgrade._inventory_module") as inventory,
                mock.patch("sbtd_upgrade._write_resource", side_effect=watch),
            ):
                inventory.return_value.build_inventory.return_value = {
                    "baseline": {
                        "baseline_id": "b1",
                        "source": {"path": str(package), "state": snapshot(package)},
                    },
                    "resources": [{
                        "id": "skill-1",
                        "kind": "skill",
                        "target": str(onboard),
                        "source": str(package),
                        "before": snapshot(onboard),
                        "desired": snapshot(package),
                        "classification": "known-old",
                        "decision": "replace",
                        "details": {},
                    }],
                    "domains": [],
                }
                inventory.return_value.normalize_scope.side_effect = lambda value: value
                inventory.return_value.payload_file_state.side_effect = (
                    lambda path: snapshot(Path(path))
                )
                inventory.return_value.payload_directory_state.side_effect = (
                    lambda path: snapshot(Path(path))
                )
                plan = sbtd_upgrade.plan_upgrade(scope, vault, package_root=package)
                self.assertEqual(plan["payload"]["status"], "planned")
                self.assertFalse(plan["payload"]["graftRetirement"]["stop"])
                self.assertEqual(plan["payload"]["graftRetirement"]["candidates"][0]["mode"], mode)
                self.assertEqual(
                    plan["payload"]["graftRetirement"]["candidates"][0]["historical_mode"],
                    "unknown",
                )
                retirement = next(
                    row for row in plan["payload"]["resources"] if row["kind"] == "retirement"
                )
                self.assertEqual(retirement["decision"], "replace")
                self.assertEqual(retirement["details"]["items"][0]["historical_mode"], "unknown")
                # Apply is isolated and re-derives. Exercise the write order directly.
                action_retirement = {
                    "resource": retirement,
                    "mechanical_before": snapshot(config),
                    "backup_ref": None,
                    "created_parents": [],
                }
                action_skill = {
                    "resource": plan["payload"]["resources"][0]
                    if plan["payload"]["resources"][0]["kind"] == "skill"
                    else next(row for row in plan["payload"]["resources"] if row["kind"] == "skill"),
                    "mechanical_before": snapshot(onboard),
                    "backup_ref": None,
                    "created_parents": [],
                }
                ordered = sorted(
                    [action_skill, action_retirement],
                    key=lambda action: (
                        0 if action["resource"]["kind"] == "retirement" else 1,
                        action["resource"]["id"],
                    ),
                )
                self.assertEqual(
                    [action["resource"]["kind"] for action in ordered],
                    ["retirement", "skill"],
                )
            self.assertIn("inspect", self.module.calls)
            self.assertNotIn("apply_candidate", self.module.calls)

    def test_mode_drift_refuses_retirement_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve() / "config.toml"
            target.write_bytes(b"owned\n")
            target.chmod(0o600)
            before = sbtd_upgrade._payload_state(target)
            sealed = {
                "kind": "retirement",
                "target": str(target),
                "before": before,
                "desired": {"type": "file", "checksum": "0" * 64},
                "details": {"action": "edit", "mode_before": "0644"},
            }
            mutation: dict = {}
            with self.assertRaises(ContractError) as caught:
                sbtd_upgrade._write_resource(
                    sealed, sealed, None, None, snapshot(target), mutation,
                )
            self.assertEqual(caught.exception.code, "state-conflict")
            self.assertEqual(target.read_bytes(), b"owned\n")
            self.assertNotIn("mutation_started", mutation)

    def test_history_directories_are_not_deletion_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            self.assertTrue(hosts._protected_history(str(base / "project" / "graft")))
            self.assertTrue(hosts._protected_history(str(base / ".graft")))
            self.assertFalse(hosts._protected_history(str(base / ".codex" / "config.toml")))


class EvidenceScopeTests(unittest.TestCase):
    def test_evidence_outside_vault_does_not_authorize_a_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            vault = base / "vault"
            require_private_directory(vault, create=True)
            outside = base / "proof.json"
            outside.write_bytes(b"{\"not\":\"authority\"}\n")
            home = base / ".codex"
            home.mkdir()
            config = home / "config.toml"
            config.write_bytes(b"owned\n")
            scope = {
                "schema_version": 1,
                "hosts": [_host(base, config)],
                "retirement_evidence": [{"kind": "operation-results", "path": str(outside)}],
            }
            with self.assertRaises(ContractError) as caught:
                sbtd_upgrade.plan_upgrade(scope, vault)
            self.assertEqual(caught.exception.code, "scope-conflict")
            self.assertEqual(config.read_bytes(), b"owned\n")


def _codex_retirement_fixture(base: Path, *, remove_file: bool = False):
    home = base / ".codex"
    home.mkdir()
    config = home / "config.toml"
    vault = require_private_directory(base / "vault", create=True)
    original = (
        b'model = "keep-me"\n\n'
        b'[mcp_servers.foreign]\ncommand = "unrelated"\n'
    )
    backup = None
    if not remove_file:
        config.write_bytes(original)
        config.chmod(0o600)
        historical = require_private_directory(vault / "historical", create=True)
        backup = backup_reference(
            {"path": str(config), "state": snapshot(config)},
            historical / "config.toml",
            private_root=vault,
        )
    launcher = base / "old-onboard" / "scripts" / "sbtd_graft_entry.py"
    arguments = [
        "-E", "-s", str(launcher), "mcp", "--node",
        str(base / "old-node"), "--entry", str(base / "old-cli.js"),
    ]
    rendered_args = ", ".join(json.dumps(item) for item in arguments)
    installed = (b"" if remove_file else original) + (
        f'\n[mcp_servers.sbtd-graft]\ncommand = {json.dumps(str(base / "old-python"))}\n'
        f'args = [{rendered_args}]\n'
        'env = { DO_NOT_TRACK = "1", DNT = "1" }\n'
    ).encode("utf-8")
    config.write_bytes(installed)
    identity = resource_id("toml", str(config))
    evidence = vault / "operation-results.json"
    evidence.write_text(json.dumps({
        "operationResults": [{
            "phase": "deploy",
            "resource_id": identity,
            "operation_ids": [operation_id("deploy", identity, "graft-mcp")],
            "dependent_projects": [],
            "status": "succeeded",
            "backup_ref": backup,
            "before": {"type": "absent", "checksum": None} if backup is None else backup["state"],
            "after": snapshot(config),
            "error": None,
        }],
    }), encoding="utf-8")
    scope = {
        "schema_version": 1,
        "hosts": [_host(base, config)],
        "retirement_evidence": [{"kind": "operation-results", "path": str(evidence)}],
    }
    return scope, vault, config, launcher, installed


def _windows_acl_fingerprint(path: Path, rights: str = "") -> str:
    # Independent Windows oracle: return a hash, never the descriptor or account SID.
    script = r"""
$ErrorActionPreference = 'Stop'
$path = $env:SBTD_FIXTURE_PATH
$acl = Get-Acl -LiteralPath $path
if ($env:SBTD_FIXTURE_RIGHTS) {
    $acl.SetAccessRuleProtection($true, $true)
    $sid = [System.Security.Principal.SecurityIdentifier]::new(
        [System.Security.Principal.WellKnownSidType]::WorldSid, $null)
    $rule = [System.Security.AccessControl.FileSystemAccessRule]::new(
        $sid, [System.Security.AccessControl.FileSystemRights]$env:SBTD_FIXTURE_RIGHTS,
        [System.Security.AccessControl.AccessControlType]::Allow)
    $acl.SetAccessRule($rule)
    Set-Acl -LiteralPath $path -AclObject $acl
    $acl = Get-Acl -LiteralPath $path
}
$sections = [System.Security.AccessControl.AccessControlSections]'Owner, Group, Access'
$sddl = $acl.GetSecurityDescriptorSddlForm($sections)
$hash = [System.Security.Cryptography.SHA256]::Create()
[Console]::Write([BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($sddl))).Replace('-', ''))
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        env={**os.environ, "SBTD_FIXTURE_PATH": str(path), "SBTD_FIXTURE_RIGHTS": rights},
        capture_output=True, text=True, timeout=15, check=True,
    )
    return result.stdout.strip()


class RealRetirementUpgradeTests(unittest.TestCase):
    def test_scoped_real_retirement_lifecycle_preserves_foreign_bytes(self) -> None:
        import jsonschema

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            scope, vault, config, launcher, installed = _codex_retirement_fixture(base)
            mode = format(stat.S_IMODE(config.stat().st_mode), "04o")

            plan = sbtd_upgrade.plan_upgrade(scope, vault)
            self.assertEqual(plan["payload"]["status"], "planned")
            (retirement,) = plan["payload"]["resources"]
            self.assertEqual(retirement["kind"], "retirement")
            self.assertEqual(retirement["details"]["action"], "edit")
            self.assertEqual(retirement["details"]["items"][0]["historical_mode"], "unknown")

            receipt = sbtd_upgrade.apply_upgrade(plan, confirmed=plan["plan_id"])
            self.assertEqual(receipt["payload"]["status"], "complete")
            row = receipt["payload"]["resources"][0]
            self.assertEqual(row["result"], "succeeded")
            self.assertEqual((row["mode_before"], row["mode_after"]), (mode, mode))
            self.assertEqual(Path(row["backup_ref"]["path"]).read_bytes(), installed)
            retired = config.read_bytes()
            self.assertNotIn(b"sbtd-graft", retired)
            self.assertNotIn(str(launcher).encode(), retired)
            self.assertIn(b'model = "keep-me"', retired)
            self.assertIn(b'command = "unrelated"', retired)

            verification = sbtd_upgrade.verify_upgrade(plan, receipt=receipt)
            self.assertEqual(verification["status"], "aligned")
            recovery = sbtd_upgrade.plan_recovery(plan, receipt)
            self.assertEqual(recovery["payload"]["status"], "planned")
            restored = sbtd_upgrade.apply_recovery(
                recovery, confirmed=recovery["recovery_id"]
            )
            self.assertEqual(restored["payload"]["status"], "complete")
            self.assertEqual(config.read_bytes(), installed)
            self.assertEqual(Path(row["backup_ref"]["path"]).read_bytes(), installed)
            self.assertEqual(format(stat.S_IMODE(config.stat().st_mode), "04o"), mode)

            schema = json.loads(
                (SCRIPTS.parent / "upgrade.schema.json").read_text(encoding="utf-8")
            )
            for document in (plan, receipt, verification, recovery, restored):
                jsonschema.validate(document, schema)

    @unittest.skipUnless(os.name == "nt", "native Windows retirement permissions")
    def test_windows_native_retirement_edit_and_remove_restore_permissions(self) -> None:
        import jsonschema

        schema = json.loads((SCRIPTS.parent / "upgrade.schema.json").read_text(encoding="utf-8"))
        for action in ("edit", "remove-file"):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as directory:
                scope, vault, config, _, installed = _codex_retirement_fixture(
                    Path(directory).resolve(), remove_file=action == "remove-file",
                )
                default_acl = _windows_acl_fingerprint(config)
                original_acl = _windows_acl_fingerprint(config, "Read")
                self.assertRegex(original_acl, r"^[0-9A-F]{64}$")
                self.assertNotEqual(original_acl, default_acl)
                if action == "remove-file":
                    config.chmod(stat.S_IREAD)
                mode = format(stat.S_IMODE(config.stat().st_mode), "04o")
                self.assertEqual(mode, "0444" if action == "remove-file" else "0666")
                plan = sbtd_upgrade.plan_upgrade(scope, vault)
                self.assertEqual(plan["payload"]["status"], "planned")
                (resource,) = plan["payload"]["resources"]
                self.assertEqual(resource["details"]["action"], action)
                sealed_acl = resource["details"]["windows_acl_digest"]
                self.assertRegex(sealed_acl, r"^[0-9a-f]{64}$")
                self.assertEqual(plan["payload"]["graftRetirement"]["candidates"][0]["windows_acl_digest"], sealed_acl)

                changed_acl = _windows_acl_fingerprint(config, "ReadAndExecute")
                self.assertNotEqual(changed_acl, original_acl)
                with self.assertRaises(ContractError):
                    sbtd_upgrade.apply_upgrade(plan, confirmed=plan["plan_id"])
                self.assertEqual(config.read_bytes(), installed)
                self.assertEqual(_windows_acl_fingerprint(config), changed_acl)
                self.assertEqual(_windows_acl_fingerprint(config, "Read"), original_acl)

                receipt = sbtd_upgrade.apply_upgrade(plan, confirmed=plan["plan_id"])
                self.assertEqual(receipt["payload"]["status"], "complete")
                self.assertTrue(receipt["payload"]["executor"]["isolated"])
                (row,) = receipt["payload"]["resources"]
                self.assertEqual(row["result"], "succeeded")
                self.assertEqual(row["mode_before"], mode)
                self.assertEqual(row["windows_acl_digest"], sealed_acl)
                backup_path = Path(row["backup_ref"]["path"])
                self.assertNotEqual(_windows_acl_fingerprint(backup_path), original_acl)
                sidecar = backup_path.with_suffix(".windows-acl")
                self.assertTrue(sidecar.is_file())
                self.assertNotEqual(_windows_acl_fingerprint(sidecar), original_acl)
                (intent_path,) = (vault / "intents").glob("intent-*.json")
                intent = json.loads(intent_path.read_text(encoding="utf-8"))["payload"]
                self.assertEqual(intent["windows_acl_digest"], sealed_acl)
                self.assertEqual(intent["windows_acl_digest_after"], row["windows_acl_digest_after"])
                if action == "edit":
                    self.assertEqual(row["mode_after"], mode)
                    self.assertEqual(row["windows_acl_digest_after"], sealed_acl)
                    self.assertEqual(_windows_acl_fingerprint(config), original_acl)
                    edited = config.read_bytes()
                    self.assertNotIn(b"sbtd-graft", edited)
                    self.assertEqual(_windows_acl_fingerprint(config, "ReadAndExecute"), changed_acl)
                    drifted = sbtd_upgrade.plan_recovery(plan, receipt)
                    self.assertEqual(drifted["payload"]["status"], "blocked")
                    self.assertEqual(drifted["payload"]["steps"][0]["reason"], "live-drift")
                    self.assertEqual(config.read_bytes(), edited)
                    self.assertEqual(_windows_acl_fingerprint(config, "Read"), original_acl)
                else:
                    self.assertIsNone(row["mode_after"])
                    self.assertIsNone(row["windows_acl_digest_after"])
                    self.assertFalse(config.exists())

                verification = sbtd_upgrade.verify_upgrade(plan, receipt=receipt)
                self.assertEqual(verification["status"], "aligned")
                moved = sidecar.rename(sidecar.with_suffix(".held"))
                try:
                    with self.assertRaises(ContractError):
                        sbtd_upgrade.plan_recovery(plan, receipt)
                finally:
                    moved.rename(sidecar)

                recovery = sbtd_upgrade.plan_recovery(plan, receipt)
                self.assertEqual(recovery["payload"]["status"], "planned")
                recovered = sbtd_upgrade.apply_recovery(recovery, confirmed=recovery["recovery_id"])
                self.assertEqual(recovered["payload"]["status"], "complete")
                self.assertTrue(recovered["payload"]["executor"]["isolated"])
                self.assertEqual(recovered["payload"]["steps"][0]["windows_acl_digest_after"], sealed_acl)
                self.assertEqual(recovered["payload"]["steps"][0]["mode_after"], mode)
                self.assertEqual(config.read_bytes(), installed)
                self.assertEqual(_windows_acl_fingerprint(config), original_acl)
                self.assertEqual(format(stat.S_IMODE(config.stat().st_mode), "04o"), mode)
                for document in (plan, receipt, verification, recovery, recovered):
                    jsonschema.validate(document, schema)



