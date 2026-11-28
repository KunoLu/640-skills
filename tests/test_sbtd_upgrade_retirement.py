from __future__ import annotations

import ctypes
import hashlib
import json
import os
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
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


def _codex_retirement_fixture(
    base: Path, *, remove_file: bool = False, vault: Path | None = None, host_id: str = "codex",
    onboard: Path | None = None,
):
    home = base / ".codex"
    home.mkdir(parents=True)
    config = home / "config.toml"
    if vault is None:
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
            historical / f"{host_id}-config.toml",
            private_root=vault,
        )
    launcher = (onboard or base / "old-onboard") / "scripts" / "sbtd_graft_entry.py"
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
    evidence = vault / f"{host_id}-operation-results.json"
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
        "hosts": [{**_host(base, config), "id": host_id}],
        "retirement_evidence": [{"kind": "operation-results", "path": str(evidence)}],
    }
    return scope, vault, config, launcher, installed


def _project_fence_fixture(scope: dict, vault: Path, base: Path) -> tuple[Path, bytes, bytes]:
    project = base / "project"
    project.mkdir()
    scope["hosts"][0]["project_roots"] = [str(project)]
    agents = project / "AGENTS.md"
    original = b"# Retained project rules\n"
    agents.write_bytes(original)
    originals = require_private_directory(vault / "historical", create=True)
    backup = backup_reference(
        {"path": str(agents), "state": snapshot(agents)}, originals / "project-AGENTS.md",
        private_root=vault,
    )
    installed = original + b"\n<!-- graft:start -->\nretired fence\n<!-- graft:end -->\n"
    agents.write_bytes(installed)
    identity = resource_id("markdown", str(agents))
    path = Path(scope["retirement_evidence"][0]["path"])
    evidence = json.loads(path.read_text(encoding="utf-8"))
    evidence["operationResults"].append({
        "phase": "deploy", "resource_id": identity,
        "operation_ids": [operation_id("deploy", identity, "graft-agents")],
        "dependent_projects": [], "status": "succeeded", "backup_ref": backup,
        "before": backup["state"], "after": snapshot(agents), "error": None,
    })
    path.write_text(json.dumps(evidence), encoding="utf-8")
    return agents, original, installed


def _set_windows_fixture_acl(path: Path, *, allow_execute: bool = False) -> None:
    # Replace the whole DACL, not a rule in an inherited DACL.
    script = r"""
$ErrorActionPreference = 'Stop'
$path = $env:SBTD_FIXTURE_PATH
$acl = Get-Acl -LiteralPath $path
$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$rights = $env:SBTD_FIXTURE_WORLD_RIGHTS
$acl.SetSecurityDescriptorSddlForm("D:P(A;;FA;;;$sid)(A;;$rights;;;WD)", 'Access')
Set-Acl -LiteralPath $path -AclObject $acl
"""
    powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    subprocess.run(
        [str(powershell), "-NoProfile", "-NonInteractive", "-Command", script],
        env={
            **os.environ, "SBTD_FIXTURE_PATH": str(path),
            "SBTD_FIXTURE_WORLD_RIGHTS": "FRFX" if allow_execute else "FR",
        },
        capture_output=True, timeout=15, check=True,
    )


def _windows_acl_fingerprint(path: Path) -> str:
    """Read native control, SIDs and ordered ACEs without .NET ACL normalization."""
    from ctypes import wintypes

    read_acl = ctypes.WinDLL("advapi32", use_last_error=True).GetFileSecurityW
    read_acl.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    read_acl.restype = wintypes.BOOL
    sections = 0x7  # Owner, group and DACL.
    length = wintypes.DWORD()
    read_acl(str(path), sections, None, 0, ctypes.byref(length))
    if ctypes.get_last_error() != 122 or not length.value:  # ERROR_INSUFFICIENT_BUFFER
        raise AssertionError("native ACL size could not be read")
    raw = ctypes.create_string_buffer(length.value)
    if not read_acl(str(path), sections, raw, length.value, ctypes.byref(length)):
        raise AssertionError("native ACL could not be read")
    revision, reserved, control, owner, group, _, dacl = struct.unpack_from("<BBHIIII", raw)
    acl_revision, _, _, ace_count, _ = struct.unpack_from("<BBHHH", raw, dacl)
    ace_start = end = dacl + 8
    for _ in range(ace_count):
        end += struct.unpack_from("<H", raw, end + 2)[0]
    # Do not compare offsets or unused ACL storage.
    fingerprint = hashlib.sha256(struct.pack("<BBHBH", revision, reserved, control, acl_revision, ace_count))
    for offset in (owner, group):
        fingerprint.update(raw[offset:offset + 8 + 4 * raw[offset + 1][0]])
    fingerprint.update(raw[ace_start:end])
    return fingerprint.hexdigest()


class RealRetirementUpgradeTests(unittest.TestCase):
    def test_preserve_conflict_refuses_before_plan_or_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            scope, vault, config, _, installed = _codex_retirement_fixture(
                Path(directory).resolve(), remove_file=True,
            )
            saved = sorted(vault.iterdir())
            scope["decisions"] = {str(config): "preserve"}
            with self.assertRaises(ContractError) as caught:
                sbtd_upgrade.plan_upgrade(scope, vault)
            self.assertEqual(caught.exception.code, "decision-conflict")
            self.assertEqual(config.read_bytes(), installed)
            self.assertEqual(sorted(vault.iterdir()), saved)

    def test_file_removal_does_not_block_sibling_edit_or_scoped_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            scope, vault, config, _, original_config = _codex_retirement_fixture(base, remove_file=True)
            agents, retained_rules, original_agents = _project_fence_fixture(scope, vault, base)
            global_rules = base / "global" / "AGENTS.md"
            global_rules.parent.mkdir()
            scope["agents_targets"] = [str(global_rules)]
            plan = sbtd_upgrade.plan_upgrade(scope, vault)
            actual_order = []
            write = sbtd_upgrade._write_resource

            def observe(resource, fresh, backup, package, expected, mutation):
                target = Path(resource["target"])
                actual_order.append(target)
                if target == agents:
                    self.assertFalse(config.exists())
                    self.assertEqual(Path(backup["path"]).read_bytes(), original_agents)
                if target == global_rules:
                    self.assertEqual(agents.read_bytes(), retained_rules)
                return write(resource, fresh, backup, package, expected, mutation)

            with mock.patch.object(sbtd_upgrade, "_write_resource", side_effect=observe):
                receipt = sbtd_upgrade._apply_upgrade_local(
                    plan, confirmed=plan["plan_id"], receipt=None, package_root=SCRIPTS.parent,
                )
            self.assertEqual(receipt["status"], "complete")
            self.assertEqual(actual_order, [config, agents, global_rules])
            self.assertFalse(config.exists())
            self.assertEqual(agents.read_bytes(), retained_rules)
            self.assertEqual(sbtd_upgrade.verify_upgrade(plan, receipt=receipt)["status"], "aligned")
            recovery = sbtd_upgrade.plan_recovery(plan, receipt)
            restored = sbtd_upgrade.apply_recovery(recovery, confirmed=recovery["recovery_id"])
            self.assertEqual(restored["status"], "complete")
            self.assertEqual(config.read_bytes(), original_config)
            self.assertEqual(agents.read_bytes(), original_agents)
            self.assertFalse(global_rules.exists())

    def test_recovery_restores_skill_before_reactivating_host_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            onboard = base / "skills" / "sbtd-workflow-onboard"
            scope, vault, config, launcher, installed = _codex_retirement_fixture(
                base, remove_file=True, onboard=onboard,
            )
            launcher.parent.mkdir(parents=True)
            original_launcher = b"# Original fixture launcher\n"
            launcher.write_bytes(original_launcher)
            (onboard / "SKILL.md").write_bytes(b"---\nname: sbtd-workflow-onboard\n---\nold\n")
            scope["skills_roots"] = [str(onboard.parent)]
            scope["decisions"] = {str(onboard): "replace"}

            plan = sbtd_upgrade.plan_upgrade(scope, vault)
            receipt = sbtd_upgrade.apply_upgrade(plan, confirmed=plan["plan_id"])
            self.assertEqual(receipt["status"], "complete")
            self.assertEqual(receipt["payload"]["resources"][0]["target"], str(config))
            self.assertFalse(config.exists())
            self.assertFalse(launcher.exists())

            recovery = sbtd_upgrade.plan_recovery(plan, receipt)
            with mock.patch.object(
                sbtd_upgrade, "restore_directory_reference",
                side_effect=ContractError("write-failed", "fixture stopped at Skill restore"),
            ):
                failed = sbtd_upgrade._apply_recovery_local(
                    recovery, confirmed=recovery["recovery_id"], receipt=None, package_root=None,
                )
            outcomes = {row["target"]: row for row in failed["payload"]["steps"]}
            self.assertEqual(outcomes[str(onboard)]["result"], "failed")
            self.assertEqual(outcomes[str(config)]["result"], "pending")
            self.assertFalse(config.exists())
            self.assertFalse(launcher.exists())

            restored = sbtd_upgrade.apply_recovery(
                recovery, confirmed=recovery["recovery_id"], receipt=failed,
            )
            self.assertEqual(restored["status"], "complete")
            order = [row["target"] for row in restored["payload"]["steps"]]
            self.assertLess(order.index(str(onboard)), order.index(str(config)))
            self.assertEqual(launcher.read_bytes(), original_launcher)
            self.assertEqual(config.read_bytes(), installed)

    def test_partial_apply_retries_only_with_bound_removed_file_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            scope, vault, config, _, installed = _codex_retirement_fixture(base, remove_file=True)
            agents, retained_rules, original_agents = _project_fence_fixture(scope, vault, base)
            plan = sbtd_upgrade.plan_upgrade(scope, vault)
            self.assertEqual(plan["payload"]["status"], "planned")
            write = sbtd_upgrade._write_resource

            def halt_before_sibling(resource, *args):
                if resource["target"] == str(agents):
                    raise ContractError("write-failed", "fixture stopped before the second retirement")
                return write(resource, *args)

            with mock.patch.object(sbtd_upgrade, "_write_resource", side_effect=halt_before_sibling):
                partial = sbtd_upgrade._apply_upgrade_local(
                    plan, confirmed=plan["plan_id"], receipt=None, package_root=SCRIPTS.parent,
                )
            self.assertEqual(partial["status"], "partial")
            self.assertFalse(config.exists())
            self.assertEqual(agents.read_bytes(), original_agents)
            rows = {row["target"]: row for row in partial["payload"]["resources"]}
            removed = rows[str(config)]
            self.assertEqual(removed["result"], "succeeded")
            self.assertEqual(Path(removed["backup_ref"]["path"]).read_bytes(), installed)
            checkpoints = (
                json.loads(path.read_text(encoding="utf-8"))
                for path in vault.glob("upgrade-receipt-*.json")
            )
            pending = next(
                document for document in checkpoints
                if all(row["result"] == "pending" for row in document["payload"]["resources"])
            )
            verify = sbtd_upgrade.verify_upgrade(plan, receipt=pending)
            self.assertEqual(verify["payload"]["receipt_id"], partial["receipt_id"])
            self.assertEqual(verify["status"], "drift")
            self.assertEqual(
                {row["target"]: row["result"] for row in verify["payload"]["resources"]},
                {str(config): "aligned", str(agents): "drift"},
            )
            recovery = sbtd_upgrade.plan_recovery(plan, pending)
            self.assertEqual(recovery["payload"]["status"], "planned")
            (step,) = recovery["payload"]["steps"]
            self.assertEqual((step["target"], step["status"]), (str(config), "actionable"))

            intent = next(
                path for path in (vault / "intents").glob("intent-*.json")
                if json.loads(path.read_text(encoding="utf-8"))["payload"]["resource_id"] == removed["id"]
            )
            held = intent.rename(intent.with_suffix(".held"))
            try:
                for phase in ("apply", "verify"):
                    with self.subTest(phase=phase), self.assertRaises(ContractError) as missing:
                        if phase == "apply":
                            sbtd_upgrade.apply_upgrade(plan, confirmed=plan["plan_id"], receipt=partial)
                        else:
                            sbtd_upgrade.verify_upgrade(plan, receipt=pending)
                    self.assertEqual(missing.exception.code, "intent-missing")
                    self.assertFalse(config.exists())
                    self.assertEqual(agents.read_bytes(), original_agents)
            finally:
                held.rename(intent)
            retry = sbtd_upgrade.apply_upgrade(plan, confirmed=plan["plan_id"], receipt=partial)
            self.assertEqual(retry["status"], "complete")
            self.assertEqual([row["result"] for row in retry["payload"]["resources"]], ["skipped-complete", "succeeded"])
            self.assertFalse(config.exists())
            self.assertEqual(agents.read_bytes(), retained_rules)
            verification = sbtd_upgrade.verify_upgrade(plan)
            self.assertEqual(verification["status"], "aligned")
            self.assertEqual(verification["payload"]["receipt_id"], retry["receipt_id"])

    @unittest.skipUnless(os.name == "posix", "POSIX file permissions")
    def test_interrupted_posix_retirement_without_completion_stays_unproven(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            scope, vault, config, _, installed = _codex_retirement_fixture(Path(directory).resolve())
            plan = sbtd_upgrade.plan_upgrade(scope, vault)
            save = sbtd_upgrade._save_once

            def interrupt_after_write(path, document, root):
                if path.name.startswith("upgrade-receipt-") and document["status"] == "complete":
                    raise ContractError("write-failed", "fixture receipt publication stopped")
                return save(path, document, root)

            with (
                mock.patch.object(sbtd_upgrade, "_save_once", side_effect=interrupt_after_write),
                self.assertRaises(ContractError) as interrupted,
            ):
                sbtd_upgrade._apply_upgrade_local(
                    plan, confirmed=plan["plan_id"], receipt=None, package_root=SCRIPTS.parent,
                )
            self.assertEqual(interrupted.exception.code, "write-failed")
            (checkpoint,) = vault.glob("upgrade-receipt-*.json")
            pending = json.loads(checkpoint.read_text(encoding="utf-8"))
            self.assertEqual(pending["payload"]["resources"][0]["result"], "pending")
            (intent_path,) = (vault / "intents").glob("intent-*.json")
            intent = json.loads(intent_path.read_text(encoding="utf-8"))["payload"]
            self.assertEqual((intent["mode_before"], intent["mode_after"]), ("0600", "0600"))
            retired = config.read_bytes()
            self.assertNotEqual(retired, installed)

            config.chmod(0o644)
            with self.assertRaises(ContractError) as drifted:
                sbtd_upgrade.apply_upgrade(plan, confirmed=plan["plan_id"], receipt=pending)
            self.assertEqual(drifted.exception.code, "state-conflict")
            self.assertEqual(config.read_bytes(), retired)
            with self.assertRaises(ContractError) as recovery_drift:
                sbtd_upgrade.plan_recovery(plan, pending)
            self.assertEqual(recovery_drift.exception.code, "plan-stale")
            self.assertEqual(config.stat().st_mode & 0o777, 0o644)

            config.chmod(0o600)
            with self.assertRaises(ContractError) as retry:
                sbtd_upgrade.apply_upgrade(plan, confirmed=plan["plan_id"], receipt=pending)
            self.assertEqual(retry.exception.code, "state-conflict")
            with self.assertRaises(ContractError) as verify:
                sbtd_upgrade.verify_upgrade(plan, receipt=pending)
            self.assertEqual(verify.exception.code, "plan-stale")
            with self.assertRaises(ContractError) as recovery:
                sbtd_upgrade.plan_recovery(plan, pending)
            self.assertEqual(recovery.exception.code, "plan-stale")
            self.assertEqual(config.read_bytes(), retired)
            self.assertEqual(config.stat().st_mode & 0o777, 0o600)

    def test_verify_rejects_a_plan_omitting_a_disclosed_retirement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            scope, vault, config, _, installed = _codex_retirement_fixture(base)
            global_rules = base / "AGENTS.md"
            scope["agents_targets"] = [str(global_rules)]
            incomplete = sbtd_upgrade.plan_upgrade(scope, vault)
            payload = incomplete["payload"]
            self.assertTrue(payload["graftRetirement"]["candidates"])
            payload["resources"] = [row for row in payload["resources"] if row["kind"] == "agents"]
            incomplete["plan_id"] = sbtd_upgrade._digest(payload)
            for saved in (False, True):
                with self.subTest(saved=saved):
                    if saved:
                        sbtd_upgrade.save_plan(incomplete, vault / f"upgrade-plan-{incomplete['plan_id']}.json")
                    with (
                        mock.patch.object(hosts, "_spawn") as spawn,
                        self.assertRaises(ContractError) as stale,
                    ):
                        sbtd_upgrade.verify_upgrade(incomplete, probe=True)
                    self.assertEqual(stale.exception.code, "plan-stale")
                    spawn.assert_not_called()
                    self.assertFalse(global_rules.exists())
                    self.assertEqual(config.read_bytes(), installed)


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
            if os.name == "posix":
                config.chmod(0o644)
                drifted = sbtd_upgrade.verify_upgrade(plan, receipt=receipt)
                self.assertEqual(drifted["status"], "drift")
                self.assertEqual(drifted["payload"]["resources"][0]["reason"], "mode-drift")
                self.assertEqual(config.read_bytes(), retired)
                config.chmod(int(mode, 8))
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

    def test_scoped_remove_recovery_refuses_foreign_recreation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            scope, vault, config, _, installed = _codex_retirement_fixture(
                Path(directory).resolve(), remove_file=True,
            )
            plan = sbtd_upgrade.plan_upgrade(scope, vault)
            (resource,) = plan["payload"]["resources"]
            self.assertEqual(resource["details"]["action"], "remove-file")
            receipt = sbtd_upgrade.apply_upgrade(plan, confirmed=plan["plan_id"])
            self.assertEqual(receipt["payload"]["status"], "complete")
            self.assertFalse(config.exists())
            recovery = sbtd_upgrade.plan_recovery(plan, receipt)
            self.assertEqual(recovery["payload"]["status"], "planned")
            (step,) = recovery["payload"]["steps"]
            self.assertEqual(step["expected_current"], {"type": "absent", "checksum": None})

            foreign = b'model = "foreign"\n'
            config.write_bytes(foreign)
            blocked = sbtd_upgrade.plan_recovery(plan, receipt)
            self.assertEqual(blocked["payload"]["status"], "blocked")
            self.assertEqual(blocked["payload"]["steps"][0]["reason"], "live-drift")
            with self.assertRaises(ContractError) as caught:
                sbtd_upgrade.apply_recovery(recovery, confirmed=recovery["recovery_id"])
            self.assertEqual(caught.exception.code, "plan-stale")
            self.assertEqual(config.read_bytes(), foreign)

            config.unlink()
            restored = sbtd_upgrade.apply_recovery(recovery, confirmed=recovery["recovery_id"])
            self.assertEqual(restored["payload"]["status"], "complete")
            self.assertEqual(config.read_bytes(), installed)
            self.assertEqual(Path(step["backup_ref"]["path"]).read_bytes(), installed)
            retry = sbtd_upgrade.apply_recovery(
                recovery, confirmed=recovery["recovery_id"], receipt=restored,
            )
            self.assertEqual(retry["payload"]["steps"][0]["result"], "skipped-complete")
            self.assertEqual(config.read_bytes(), installed)
            if os.name == "posix":
                config.chmod(stat.S_IMODE(config.stat().st_mode) ^ stat.S_IXUSR)
                with self.assertRaises(ContractError) as drifted:
                    sbtd_upgrade.apply_recovery(recovery, confirmed=recovery["recovery_id"], receipt=retry)
                self.assertEqual(drifted.exception.code, "plan-stale")
                self.assertEqual(config.read_bytes(), installed)

    def _partial_retirement(self, base: Path):
        scope, vault, completed, _, original = _codex_retirement_fixture(base / "completed")
        unfinished_scope, _, unfinished, launcher, untouched = _codex_retirement_fixture(
            base / "unfinished", remove_file=True, vault=vault, host_id="unfinished",
        )
        new_scope, _, new_target, _, new_bytes = _codex_retirement_fixture(
            base / "new", remove_file=True, vault=vault, host_id="new",
        )
        new_target.unlink()
        for other in (unfinished_scope, new_scope):
            scope["hosts"].extend(other["hosts"])
            scope["retirement_evidence"].extend(other["retirement_evidence"])
        plan = sbtd_upgrade.plan_upgrade(scope, vault)
        self.assertEqual(plan["payload"]["status"], "planned")
        self.assertEqual(
            [row["path"] for row in plan["payload"]["graftRetirement"]["candidates"]],
            [str(completed), str(unfinished)],
        )
        real_write = sbtd_upgrade._write_resource

        def fail_unfinished(sealed, *args):
            if sealed["target"] == str(unfinished):
                raise ContractError("write-failed", "fixture stopped before the second retirement")
            return real_write(sealed, *args)

        with mock.patch.object(sbtd_upgrade, "_write_resource", side_effect=fail_unfinished):
            receipt = sbtd_upgrade._apply_upgrade_local(
                plan, confirmed=plan["plan_id"], receipt=None, package_root=SCRIPTS.parent,
            )
        self.assertEqual(receipt["status"], "partial")
        self.assertEqual([row["result"] for row in receipt["payload"]["resources"]], ["succeeded", "failed"])
        self.assertEqual(unfinished.read_bytes(), untouched)
        return plan, receipt, (completed, original), (unfinished, launcher, untouched), (new_target, new_bytes)

    def test_partial_recovery_restores_only_completed_retirement_and_rechecks_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plan, receipt, (completed, original), (unfinished, _, untouched), _ = self._partial_retirement(
                Path(directory).resolve(),
            )
            retired = completed.read_bytes()
            self.assertNotIn(b"sbtd-graft", retired)
            recovery = sbtd_upgrade.plan_recovery(plan, receipt)
            self.assertEqual(recovery["payload"]["status"], "planned")
            (step,) = recovery["payload"]["steps"]
            self.assertEqual((step["target"], step["status"]), (str(completed), "actionable"))

            foreign = b'model = "foreign"\n'
            completed.write_bytes(foreign)
            blocked = sbtd_upgrade.plan_recovery(plan, receipt)
            self.assertEqual(blocked["payload"]["status"], "blocked")
            self.assertEqual(blocked["payload"]["steps"][0]["reason"], "live-drift")
            with self.assertRaises(ContractError) as caught:
                sbtd_upgrade.apply_recovery(recovery, confirmed=recovery["recovery_id"])
            self.assertEqual(caught.exception.code, "plan-stale")
            self.assertEqual(completed.read_bytes(), foreign)
            self.assertEqual(unfinished.read_bytes(), untouched)

            completed.write_bytes(retired)
            restored = sbtd_upgrade.apply_recovery(recovery, confirmed=recovery["recovery_id"])
            self.assertEqual(restored["status"], "complete")
            self.assertEqual(completed.read_bytes(), original)
            self.assertEqual(unfinished.read_bytes(), untouched)

    def test_partial_recovery_rejects_changed_and_new_retirement_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plan, receipt, (completed, _), (unfinished, launcher, untouched), (new_target, new_bytes) = (
                self._partial_retirement(Path(directory).resolve())
            )
            payload = plan["payload"]
            scope, vault = payload["scope"], payload["backup_root"]
            evidence = Path(scope["retirement_evidence"][1]["path"])
            original_evidence = evidence.read_bytes()
            alternate = launcher.parents[1].with_name("different-onboard") / "scripts" / launcher.name
            changed = untouched.replace(json.dumps(str(launcher)).encode(), json.dumps(str(alternate)).encode())
            self.assertNotEqual(changed, untouched)
            unfinished.write_bytes(changed)
            proof = json.loads(original_evidence)
            proof["operationResults"][0]["after"] = snapshot(unfinished)
            evidence.write_text(json.dumps(proof), encoding="utf-8")
            fresh = hosts.plan_retirement(scope, vault, evidence=scope["retirement_evidence"])
            (candidate,) = fresh["disclosure"]["candidates"]
            self.assertEqual(candidate["id"], payload["graftRetirement"]["candidates"][1]["id"])
            self.assertEqual(candidate["launcher"]["path"], str(alternate))
            with self.assertRaises(ContractError) as drifted:
                sbtd_upgrade.plan_recovery(plan, receipt)
            self.assertEqual(drifted.exception.code, "plan-stale")
            self.assertEqual(unfinished.read_bytes(), changed)

            unfinished.write_bytes(untouched)
            evidence.write_bytes(original_evidence)
            new_target.write_bytes(new_bytes)
            with self.assertRaises(ContractError) as added:
                sbtd_upgrade.plan_recovery(plan, receipt)
            self.assertEqual(added.exception.code, "plan-stale")
            self.assertEqual(new_target.read_bytes(), new_bytes)
            self.assertNotIn(b"sbtd-graft", completed.read_bytes())

            new_target.unlink()
            unfinished.unlink()
            with self.assertRaises(ContractError) as missing:
                sbtd_upgrade.plan_recovery(plan, receipt)
            self.assertEqual(missing.exception.code, "plan-stale")
            self.assertFalse(unfinished.exists())

    def test_missing_disclosure_does_not_authorize_retirement(self) -> None:
        import jsonschema

        with tempfile.TemporaryDirectory() as directory:
            scope, vault, config, _, original = _codex_retirement_fixture(Path(directory).resolve())
            plan = sbtd_upgrade.plan_upgrade(scope, vault)
            self.assertTrue(plan["payload"].pop("graftRetirement")["candidates"])
            plan["plan_id"] = sbtd_upgrade._digest(plan["payload"])
            schema = json.loads((SCRIPTS.parent / "upgrade.schema.json").read_text(encoding="utf-8"))
            with self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate(plan, schema)
            with self.assertRaises(ContractError) as caught:
                sbtd_upgrade.apply_upgrade(plan, confirmed=plan["plan_id"])
            self.assertEqual(caught.exception.code, "invalid-document")
            self.assertEqual(config.read_bytes(), original)
            self.assertFalse(list(vault.glob("upgrade-*.json")))

    @unittest.skipUnless(os.name == "nt", "native Windows retirement permissions")
    def test_windows_native_retirement_edit_and_remove_restore_permissions(self) -> None:
        import jsonschema
        from sbtd_retirement_permissions import capture, digest

        schema = json.loads((SCRIPTS.parent / "upgrade.schema.json").read_text(encoding="utf-8"))
        for action in ("edit", "remove-file"):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as directory:
                scope, vault, config, _, installed = _codex_retirement_fixture(
                    Path(directory).resolve(), remove_file=action == "remove-file",
                )
                default_acl = _windows_acl_fingerprint(config)
                _set_windows_fixture_acl(config)
                original_acl = _windows_acl_fingerprint(config)
                self.assertRegex(original_acl, r"^[0-9a-f]{64}$")
                self.assertNotEqual(original_acl, default_acl)
                if action == "remove-file":
                    config.chmod(stat.S_IREAD)
                mode = format(stat.S_IMODE(config.lstat().st_mode), "04o")
                self.assertEqual(mode, "0444" if action == "remove-file" else "0666")
                plan = sbtd_upgrade.plan_upgrade(scope, vault)
                self.assertEqual(plan["payload"]["status"], "planned")
                (resource,) = plan["payload"]["resources"]
                self.assertEqual(resource["details"]["action"], action)
                sealed_acl = resource["details"]["windows_acl_digest"]
                self.assertRegex(sealed_acl, r"^[0-9a-f]{64}$")
                self.assertEqual(plan["payload"]["graftRetirement"]["candidates"][0]["windows_acl_digest"], sealed_acl)
                self.assertEqual(plan["payload"]["graftRetirement"]["candidates"][0]["mode"], mode)
                original_descriptor = capture(config)
                self.assertEqual(digest(original_descriptor), sealed_acl)

                _set_windows_fixture_acl(config, allow_execute=True)
                changed_acl = _windows_acl_fingerprint(config)
                changed_descriptor = capture(config)
                self.assertNotEqual(changed_acl, original_acl)
                self.assertNotEqual(digest(changed_descriptor), sealed_acl)
                self.assertEqual(format(stat.S_IMODE(config.lstat().st_mode), "04o"), mode)
                with self.assertRaises(ContractError) as drifted:
                    sbtd_upgrade.apply_upgrade(plan, confirmed=plan["plan_id"])
                self.assertEqual(drifted.exception.code, "plan-stale")
                self.assertEqual(config.read_bytes(), installed)
                self.assertEqual(_windows_acl_fingerprint(config), changed_acl)
                _set_windows_fixture_acl(config)
                self.assertEqual(_windows_acl_fingerprint(config), original_acl)
                self.assertEqual(digest(capture(config)), sealed_acl)
                self.assertEqual(format(stat.S_IMODE(config.lstat().st_mode), "04o"), mode)

                receipt = sbtd_upgrade.apply_upgrade(plan, confirmed=plan["plan_id"])
                self.assertEqual(receipt["payload"]["status"], "complete")
                self.assertTrue(receipt["payload"]["executor"]["isolated"])
                (row,) = receipt["payload"]["resources"]
                self.assertEqual(row["result"], "succeeded")
                self.assertEqual(row["mode_before"], mode)
                self.assertEqual(row["windows_acl_digest"], sealed_acl)
                backup_path = Path(row["backup_ref"]["path"])
                self.assertEqual(backup_path.read_bytes(), installed)
                self.assertEqual(format(stat.S_IMODE(backup_path.lstat().st_mode), "04o"), mode)
                self.assertNotEqual(_windows_acl_fingerprint(backup_path), original_acl)
                sidecar = backup_path.with_suffix(".windows-acl")
                self.assertTrue(
                    sidecar.read_bytes() == original_descriptor,
                    "private ACL sidecar differs from the original native descriptor",
                )
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
                    _set_windows_fixture_acl(config, allow_execute=True)
                    self.assertEqual(_windows_acl_fingerprint(config), changed_acl)
                    self.assertEqual(format(stat.S_IMODE(config.lstat().st_mode), "04o"), mode)
                    verify_drift = sbtd_upgrade.verify_upgrade(plan, receipt=receipt)
                    self.assertEqual(verify_drift["status"], "drift")
                    self.assertEqual(verify_drift["payload"]["resources"][0]["reason"], "windows-permissions-drift")
                    drifted = sbtd_upgrade.plan_recovery(plan, receipt)
                    self.assertEqual(drifted["payload"]["status"], "blocked")
                    self.assertEqual(drifted["payload"]["steps"][0]["reason"], "live-drift")
                    self.assertEqual(config.read_bytes(), edited)
                    _set_windows_fixture_acl(config)
                    self.assertEqual(_windows_acl_fingerprint(config), original_acl)
                    self.assertEqual(digest(capture(config)), sealed_acl)
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
                try:
                    sidecar.write_bytes(changed_descriptor)
                    with self.assertRaises(ContractError) as changed:
                        sbtd_upgrade.plan_recovery(plan, receipt)
                    self.assertEqual(changed.exception.code, "backup-conflict")
                finally:
                    sidecar.write_bytes(original_descriptor)

                recovery = sbtd_upgrade.plan_recovery(plan, receipt)
                self.assertEqual(recovery["payload"]["status"], "planned")
                recovered = sbtd_upgrade.apply_recovery(recovery, confirmed=recovery["recovery_id"])
                self.assertEqual(recovered["payload"]["status"], "complete")
                self.assertTrue(recovered["payload"]["executor"]["isolated"])
                self.assertEqual(recovered["payload"]["steps"][0]["windows_acl_digest_after"], sealed_acl)
                self.assertEqual(recovered["payload"]["steps"][0]["mode_after"], mode)
                self.assertEqual(config.read_bytes(), installed)
                self.assertEqual(_windows_acl_fingerprint(config), original_acl)
                self.assertEqual(format(stat.S_IMODE(config.lstat().st_mode), "04o"), mode)
                for document in (plan, receipt, verification, recovery, recovered):
                    jsonschema.validate(document, schema)
