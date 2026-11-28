"""Retirement proof must be an attributable change, not a matching shape."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from onboard_contracts import ContractError, canonical_json_bytes, operation_id, resource_id
from sbtd_migration_files import require_private_directory, save_document, snapshot
from sbtd_retirement import (
    apply_candidate,
    backup_candidate,
    inspect_retirement,
    merge_reports,
    reconcile_candidate,
    render_candidate_bytes,
    render_candidates,
    restore_candidate,
    retirement_file_bytes,
)
from sbtd_retirement_paths import HISTORY_DIRS, LEGACY_LAUNCHER_RELATIVE


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _mode(path: Path) -> str:
    return f"{stat.S_IMODE(path.lstat().st_mode):04o}"


def _seal(payload, key):
    return {
        "schema_version": 1,
        "payload": payload,
        key: _sha(canonical_json_bytes(payload)),
    }


def native_file_acl(path: Path, *, world_rights: str = "") -> str:
    """Independent PowerShell Win32 oracle; never print the fixture descriptor."""
    script = """
$ErrorActionPreference = 'Stop'
$path = $env:SBTD_ACL_PATH
$acl = Get-Acl -LiteralPath $path
if ($env:SBTD_ACL_WORLD_RIGHTS) {
    $me = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
    $world = [System.Security.Principal.SecurityIdentifier]::new('S-1-1-0')
    $guests = [System.Security.Principal.SecurityIdentifier]::new('S-1-5-32-546')
    $rule = [System.Security.AccessControl.FileSystemAccessRule]
    $rights = [Enum]::Parse([System.Security.AccessControl.FileSystemRights], $env:SBTD_ACL_WORLD_RIGHTS)
    $acl.SetAccessRuleProtection($true, $false)
    $acl.SetAccessRule($rule::new($me, 'FullControl', 'Allow'))
    $acl.SetAccessRule($rule::new($world, $rights, 'Allow'))
    $acl.SetAccessRule($rule::new($guests, 'WriteAttributes', 'Deny'))
    Set-Acl -LiteralPath $path -AclObject $acl
    $acl = Get-Acl -LiteralPath $path
}
$sections = [System.Security.AccessControl.AccessControlSections]'Owner, Group, Access'
[Console]::Out.Write($acl.GetSecurityDescriptorSddlForm($sections))
"""
    command = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    result = subprocess.run(
        [str(command), "-NoProfile", "-NonInteractive", "-Command", script],
        env={**os.environ, "SBTD_ACL_PATH": str(path), "SBTD_ACL_WORLD_RIGHTS": world_rights},
        capture_output=True, text=True, timeout=12,
    )
    if result.returncode or not result.stdout.startswith("O:") or "G:" not in result.stdout or "D:" not in result.stdout:
        raise AssertionError("Windows ACL witness setup or readback failed")
    return result.stdout


def _result(target: str, owner: str, selector: str, before: dict, after: dict, backup=None):
    identity = resource_id(owner, target)
    return {
        "phase": "deploy",
        "resource_id": identity,
        "operation_ids": [operation_id("deploy", identity, selector)],
        "dependent_projects": [str(Path(target).parent)],
        "status": "succeeded",
        "backup_ref": backup,
        "before": before,
        "after": after,
        "error": None,
    }


class RetirementProofTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.vault = require_private_directory(self.root / "vault", create=True)
        self.home = self.root / "home"
        self.home.mkdir()
        self.launcher = self.home / "skills" / "sbtd-workflow-onboard" / LEGACY_LAUNCHER_RELATIVE
        self.launcher.parent.mkdir(parents=True)
        self.launcher.write_bytes(b"launcher")
        self.node = self.home / "node"
        self.cli = self.home / "cli.js"
        self.node.write_bytes(b"node")
        self.cli.write_bytes(b"cli")

    def tearDown(self):
        self.tmp.cleanup()

    def _global(self):
        return ["-E", "-s", str(self.launcher), "mcp", "--node", str(self.node), "--entry", str(self.cli)]

    def _fixed(self, root: Path):
        return [
            "-E", "-s", str(self.launcher), "mcp", "--root", str(root),
            "--node", str(self.node), "--entry", str(self.cli),
        ]

    def _server(self, args, *, cwd=None):
        entry = {"type": "stdio", "command": str(self.home / "python"), "args": args, "env": {"DO_NOT_TRACK": "1", "DNT": "1"}}
        if cwd is not None:
            entry["cwd"] = cwd
        return entry

    def _write(self, path: Path, document: dict, mode=0o640):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((json.dumps(document, indent=2) + "\n").encode())
        path.chmod(mode)
        return path.read_bytes()

    def _evidence(self, result, name="operation-results.json"):
        path = self.vault / name
        path.write_bytes(json.dumps({"operationResults": [result]}).encode())
        return [{"kind": "operation-results", "path": str(path)}]

    def _select(self, config: Path, *, host="omp"):
        return {
            "host": host,
            "configs": [{"role": "omp-mcp", "path": str(config)}],
            "projects": [],
            "vault": str(self.vault),
            "retiring_launchers": [str(self.launcher)],
        }

    def _execution(self, candidate, name):
        return {
            "scope": Path(candidate["path"]).parent,
            "vault": self.vault,
            "expected": {**candidate["before"], "mode": candidate["mode"],
                         "windows_acl_digest": candidate.get("windows_acl_digest")},
            "receipt_path": self.vault / f"{name}.json",
            "plan_id": _sha(name.encode()),
            "backup_path": self.vault / f"{name}.backup",
        }

    def _bound_row(self, resource, *, result="succeeded", mutated=True, backup=None):
        after = resource["desired"]
        return {
            "id": resource["id"],
            "kind": resource["kind"],
            "target": resource["target"],
            "decision": resource["decision"],
            "result": result,
            "before": resource["before"],
            "desired": resource["desired"],
            "after": after,
            "mechanical_after": after,
            "mechanical_before": resource["before"],
            "backup_ref": backup,
            "created_parents": [],
            "reason": None,
            "mutated": mutated,
        }

    def _upgrade(self, resource, row, *, status="complete"):
        plan_payload = {"plan_schema": "upgrade-plan", "resources": [resource]}
        plan_id = hashlib.sha256(canonical_json_bytes(plan_payload)).hexdigest()
        receipt_payload = {
            "receipt_schema": "upgrade-receipt",
            "plan_id": plan_id,
            "status": status,
            "resources": [row],
        }
        receipt_id = hashlib.sha256(canonical_json_bytes(receipt_payload)).hexdigest()
        plan_path = self.vault / "upgrade-plan.json"
        receipt_path = self.vault / f"upgrade-receipt-{receipt_id}.json"
        plan_path.write_bytes(json.dumps({
            "schema_version": 1, "payload": plan_payload, "plan_id": plan_id,
        }).encode())
        receipt_path.write_bytes(json.dumps({
            "schema_version": 1,
            "receipt_path": str(receipt_path),
            "status": status,
            "payload": receipt_payload,
            "receipt_id": receipt_id,
        }).encode())
        return [{"kind": "upgrade-plan-apply", "plan": str(plan_path), "receipt": str(receipt_path)}]


    def test_length_8_created_file_is_removed_and_restore_checks_backup_first(self):
        args = self._global()
        self.assertEqual(len(args), 8)
        self.assertEqual(args[7], str(self.cli))
        config = self.home / ".omp" / "agent" / "mcp.json"
        raw = self._write(config, {"mcpServers": {"sbtd-graft": self._server(args)}})
        evidence = self._evidence(_result(
            str(config), "json", "graft-omp-mcp",
            {"type": "absent", "checksum": None},
            {"type": "file", "checksum": _sha(raw)},
        ))
        report = inspect_retirement(selections=self._select(config), evidence=evidence)
        self.assertNotIn(b"DO_NOT_TRACK", json.dumps(report).encode())
        item = report["items"][0]
        self.assertEqual(item["status"], "proven")
        self.assertEqual(item["historical_mode"], "unknown")
        self.assertTrue(item["write_authority"])
        view = render_candidates(report, purpose="reset")
        candidate = view["candidates"][0]
        self.assertEqual(candidate["action"], "remove-file")
        self.assertEqual(candidate["before"]["checksum"], _sha(raw))
        apply_candidate(
            candidate, scope=config.parent, vault=self.vault,
            expected={**candidate["before"], "mode": candidate["mode"],
                      "windows_acl_digest": candidate.get("windows_acl_digest")},
            receipt_path=self.vault / "receipt.json",
            plan_id=_sha(b"receipt plan"),
        )
        self.assertFalse(config.exists())
        again = apply_candidate(
            candidate, scope=config.parent, vault=self.vault,
            expected={**candidate["before"], "mode": candidate["mode"],
                      "windows_acl_digest": candidate.get("windows_acl_digest")},
            receipt_path=self.vault / "receipt.json",
            plan_id=_sha(b"receipt plan"),
        )
        self.assertEqual(again["writes"], 0)
        backup = Path(again["backup_ref"]["path"])
        if os.name == "nt":
            backup.write_bytes(backup.read_bytes() + b"x")
        else:
            os.chmod(backup, 0o600)
        with self.assertRaises(Exception):
            restore_candidate(
                self.vault / "receipt.json", scope=config.parent, vault=self.vault,
                expected={"type": "absent", "checksum": None, "mode": None}, target=config,
            )
        self.assertFalse(config.exists())

    def test_later_plan_with_same_candidate_id_keeps_separate_backups(self):
        config = self.home / "mcp.json"
        retained = []
        ids = set()
        for index in (1, 2):
            args = self._global()
            args[-1] = str(self.home / f"cli-{index}.js")
            raw = self._write(config, {"mcpServers": {"sbtd-graft": self._server(args)}})
            evidence = self._evidence(_result(
                str(config), "json", "graft-omp-mcp", {"type": "absent", "checksum": None}, snapshot(config),
            ), name=f"history-{index}.json")
            report = inspect_retirement(selections=self._select(config), evidence=evidence)
            (candidate,) = render_candidates(report, purpose="reset")["candidates"]
            ids.add(candidate["id"])
            execution = self._execution(candidate, f"plan-{index}")
            del execution["backup_path"]
            outcome = apply_candidate(candidate, **execution)
            self.assertEqual(outcome["writes"], 1)
            self.assertFalse(config.exists())
            retained.append((Path(outcome["backup_ref"]["path"]), raw))
        self.assertEqual(len(ids), 1)
        self.assertNotEqual(retained[0][0], retained[1][0])
        for path, raw in retained:
            self.assertEqual(path.read_bytes(), raw)

    def test_receipt_save_failure_retains_a_measured_completion_for_rollback(self):
        config = self.home / "mcp.json"
        raw = self._write(config, {"mcpServers": {"sbtd-graft": self._server(self._global())}})
        evidence = self._evidence(_result(
            str(config), "json", "graft-omp-mcp", {"type": "absent", "checksum": None}, snapshot(config),
        ))
        report = inspect_retirement(selections=self._select(config), evidence=evidence)
        (candidate,) = render_candidates(report, purpose="reset")["candidates"]
        execution = self._execution(candidate, "retirement")
        backup = backup_candidate(candidate, destination=execution["backup_path"], vault=self.vault)
        receipt = execution["receipt_path"]
        intent = receipt.with_name(receipt.name + ".intent")

        def persist(path, document, **kwargs):
            if path == receipt:
                self.assertFalse(config.exists())
                raise OSError("injected receipt write failure")
            if path == intent:
                self.assertEqual(config.read_bytes(), raw)
            return save_document(path, document, **kwargs)

        with patch("sbtd_migration_files.save_document", side_effect=persist):
            outcome = apply_candidate(candidate, **execution)
        self.assertEqual((outcome["writes"], outcome["receipt_path"]), (1, None))
        self.assertEqual(outcome["backup_ref"], backup)
        self.assertFalse(config.exists())
        intended = json.loads(intent.read_bytes())["payload"]["transition"]
        self.assertEqual(intended["plan_id"], execution["plan_id"])
        self.assertEqual(intended["backup_ref"], backup)
        self.assertEqual(intended["mode_before"], candidate["mode"])
        self.assertEqual(intended["after"], {"type": "absent", "checksum": None})
        if os.name == "nt":
            self.assertEqual(intended["windows_acl_digest"], candidate["windows_acl_digest"])
            self.assertIsNone(intended["windows_acl_digest_after"])
        self.assertFalse(receipt.exists())

        with self.assertRaises(ContractError) as interrupted:
            reconcile_candidate(candidate, **execution)
        self.assertEqual(interrupted.exception.code, "retirement-interrupted")
        completion = outcome["retirement_completion"]
        skipped = reconcile_candidate(candidate, **execution, retirement_completion=completion)
        self.assertEqual((skipped["result"], skipped["writes"]), ("skipped-complete", 0))
        restore = {
            "scope": config.parent, "vault": self.vault, "target": config, "backup_path": execution["backup_path"],
            "expected": {"type": "absent", "checksum": None, "mode": None},
            "retirement_completion": completion,
        }
        with self.assertRaises(ContractError) as wrong_plan:
            restore_candidate(receipt, **restore, plan_id=_sha(b"different plan"))
        self.assertEqual(wrong_plan.exception.code, "binding-violation")
        self.assertFalse(config.exists())
        restore_candidate(receipt, **restore, plan_id=execution["plan_id"])
        self.assertEqual(config.read_bytes(), raw)
        self.assertEqual(_mode(config), candidate["mode"])

    def test_intent_does_not_claim_a_users_matching_edit(self):
        config = self.home / "mcp.json"
        previous = {"theme": "dark"}
        historic = self.vault / "historic.json"
        old = self._write(historic, previous)
        raw = self._write(config, {**previous, "mcpServers": {"sbtd-graft": self._server(self._global())}})
        before = snapshot(historic)
        evidence = self._evidence(_result(
            str(config), "json", "graft-omp-mcp", before, snapshot(config),
            {"path": str(historic), "state": before},
        ))
        report = inspect_retirement(selections=self._select(config), evidence=evidence)
        (candidate,) = render_candidates(report, purpose="reset")["candidates"]
        execution = self._execution(candidate, "interrupted")
        backup_candidate(candidate, destination=execution["backup_path"], vault=self.vault)
        with patch("sbtd_migration_files.write_file", side_effect=OSError("injected interruption")):
            with self.assertRaises(ContractError) as error:
                apply_candidate(candidate, **execution)
        self.assertEqual(error.exception.details["writes"], 0)
        self.assertEqual(config.read_bytes(), raw)
        self.assertEqual(reconcile_candidate(candidate, **execution)["result"], "retryable-before")

        config.write_bytes(old)
        with self.assertRaises(ContractError) as conflict:
            reconcile_candidate(candidate, **execution)
        self.assertEqual(conflict.exception.code, "retirement-interrupted")
        self.assertIsNone(conflict.exception.details["writes"])
        self.assertFalse(execution["receipt_path"].exists())
        with self.assertRaises(ContractError) as restore:
            restore_candidate(
                execution["receipt_path"], target=config, scope=config.parent, vault=self.vault,
                plan_id=execution["plan_id"], backup_path=execution["backup_path"],
                expected={**candidate["desired"], "mode": candidate["mode"],
                          "windows_acl_digest": candidate.get("windows_acl_digest")},
            )
        self.assertEqual(restore.exception.code, "retirement-interrupted")
        self.assertEqual(config.read_bytes(), old)
        self.assertEqual(execution["backup_path"].read_bytes(), raw)

    @unittest.skipUnless(os.name == "nt", "Windows ACL semantics")
    def test_windows_remove_and_restore_preserves_native_descriptor(self):
        config = self.home / "mcp.json"
        raw = self._write(config, {"mcpServers": {"sbtd-graft": self._server(self._global())}})
        original_mode = _mode(config)
        original_acl = native_file_acl(config, world_rights="ReadAttributes")
        self.assertTrue("D:P" in original_acl and "(D;" in original_acl and ";;;WD)" in original_acl)
        evidence = self._evidence(_result(
            str(config), "json", "graft-omp-mcp", {"type": "absent", "checksum": None}, snapshot(config),
        ))
        report = inspect_retirement(selections=self._select(config), evidence=evidence)
        candidate = render_candidates(report, purpose="reset")["candidates"][0]
        self.assertEqual(candidate["windows_acl_digest"], report["items"][0]["windows_acl_digest"])
        old_report = {**report, "items": [
            {key: value for key, value in item.items() if key != "windows_acl_digest"} for item in report["items"]
        ]}
        self.assertFalse(render_candidates(old_report, purpose="check")["stop"])
        self.assertTrue(render_candidates(old_report, purpose="reset")["stop"])
        expected = {**candidate["before"], "mode": original_mode, "windows_acl_digest": candidate["windows_acl_digest"]}
        receipt = self.vault / "retirement.json"
        plan_id = _sha(b"native retirement plan")
        with self.assertRaises(ContractError):
            apply_candidate(
                candidate, scope=config.parent, vault=self.vault,
                expected={**candidate["before"], "mode": original_mode}, receipt_path=receipt,
                plan_id=plan_id,
            )
        changed_acl = native_file_acl(config, world_rights="ReadData")
        self.assertTrue(changed_acl != original_acl)
        self.assertEqual(_mode(config), original_mode)
        self.assertEqual(config.read_bytes(), raw)
        self.assertTrue(render_candidates(report, purpose="reset")["stop"])
        with self.assertRaises(ContractError):
            apply_candidate(
                candidate, scope=config.parent, vault=self.vault, expected=expected,
                receipt_path=receipt, plan_id=plan_id,
            )
        self.assertTrue(config.is_file())
        self.assertTrue(native_file_acl(config, world_rights="ReadAttributes") == original_acl)
        retired = apply_candidate(
            candidate, scope=config.parent, vault=self.vault, expected=expected,
            receipt_path=receipt, plan_id=plan_id,
        )
        self.assertFalse(config.exists())
        backup = Path(retired["backup_ref"]["path"])
        sidecar = backup.with_name(backup.name + ".windows-acl")
        self.assertTrue(sidecar.is_file())
        self.assertFalse(";;;WD)" in native_file_acl(backup))
        self.assertFalse(";;;WD)" in native_file_acl(sidecar))
        previous = apply_candidate(
            candidate, scope=config.parent, vault=self.vault, expected=expected,
            receipt_path=receipt, plan_id=plan_id,
        )
        self.assertEqual(previous["result"], "skipped-complete")
        after = {"type": "absent", "checksum": None, "mode": None}
        old_receipt = self.vault / "mode-only-retirement.json"
        old_payload = json.loads(receipt.read_bytes())["payload"]
        for key in ("plan_id", "candidate_digest", "scope", "receipt_path", "intent_id"):
            del old_payload[key]
        del old_payload["windows_acl_digest"], old_payload["windows_acl_digest_after"]
        old_receipt.write_bytes(canonical_json_bytes({
            "schema_version": 1,
            "payload": old_payload,
            "receipt_id": _sha(canonical_json_bytes(old_payload)),
        }))
        with self.assertRaises(ContractError) as error:
            restore_candidate(old_receipt, scope=config.parent, vault=self.vault, expected=after, target=config)
        self.assertEqual(error.exception.code, "state-conflict")
        self.assertFalse(config.exists())
        descriptor = sidecar.read_bytes()
        sidecar.write_bytes(b"not a security descriptor")
        with self.assertRaises(ContractError):
            restore_candidate(receipt, scope=config.parent, vault=self.vault, expected=after, target=config)
        self.assertFalse(config.exists())
        sidecar.write_bytes(descriptor)
        restore_candidate(receipt, scope=config.parent, vault=self.vault, expected=after, target=config)
        self.assertEqual(config.read_bytes(), raw)
        self.assertEqual(_mode(config), original_mode)
        self.assertTrue(native_file_acl(config) == original_acl, "Windows owner, group and DACL changed")

    @unittest.skipUnless(os.name == "nt", "Windows ACL semantics")
    def test_windows_authority_documents_require_private_files_and_every_vault_parent(self):
        first = require_private_directory(self.vault / "first", create=True)
        second = require_private_directory(first / "second", create=True)
        config = self.home / "mcp.json"
        before = self.vault / "user-backup.json"
        self._write(before, {"theme": "dark"})
        native_file_acl(before, world_rights="ReadAttributes")
        original = snapshot(before)
        raw = self._write(config, {"theme": "dark", "mcpServers": {"sbtd-graft": self._server(self._global())}})
        native_file_acl(config, world_rights="ReadAttributes")
        result = _result(str(config), "json", "graft-omp-mcp", original, snapshot(config),
                         {"path": str(before), "state": original})
        nested = self._evidence(result, name="first/second/results.json")
        separate = self._evidence(result, name="other-results.json")
        self.assertEqual(Path(nested[0]["path"]).parent, second)
        report = inspect_retirement(selections=self._select(config), evidence=nested)
        self.assertTrue(report["items"][0]["write_authority"])

        native_file_acl(first, world_rights="ReadAttributes")
        native_file_acl(Path(separate[0]["path"]), world_rights="ReadAttributes")
        for evidence in (nested, separate):
            with self.subTest(evidence=evidence), self.assertRaises(ContractError) as error:
                inspect_retirement(selections=self._select(config), evidence=evidence)
            self.assertEqual(error.exception.code, "privacy-unproven")
        self.assertEqual(config.read_bytes(), raw)

    def test_preexisting_same_shape_and_noop_are_not_claimed(self):
        config = self.home / "mcp.json"
        root = self.home / "project"
        root.mkdir()
        key = "sbtd-graft-" + hashlib.sha256(str(root).encode()).hexdigest()[:16]
        document = {"mcpServers": {key: self._server(self._fixed(root), cwd=str(root)), "other": {"type": "stdio", "command": "keep"}}}
        raw = self._write(config, document)
        backup = self.vault / "original.json"
        backup.write_bytes(raw)
        evidence = self._evidence(_result(
            str(config), "json", "graft-omp-mcp",
            snapshot(config), snapshot(config),
            {"path": str(backup), "state": snapshot(config)},
        ))
        report = inspect_retirement(selections=self._select(config), evidence=evidence)
        self.assertFalse(any(item.get("write_authority") for item in report["items"]))
        self.assertEqual(config.read_bytes(), raw)

    def test_same_post_state_with_conflicting_originals_is_not_verified_in_either_order(self):
        config = self.home / "mcp.json"
        raw = self._write(config, {"mcpServers": {"sbtd-graft": self._server(self._global())}})
        before = self.vault / "prior.json"
        self._write(before, {})
        original = snapshot(before)
        after = snapshot(config)
        creation = self._evidence(_result(
            str(config), "json", "graft-omp-mcp", {"type": "absent", "checksum": None}, after,
        ), name="created.json")
        replacement = self._evidence(_result(
            str(config), "json", "graft-omp-mcp", original, after, {"path": str(before), "state": original},
        ), name="changed.json")
        self.assertEqual(render_candidates(
            inspect_retirement(selections=self._select(config), evidence=creation), purpose="reset",
        )["candidates"][0]["action"], "remove-file")
        self.assertEqual(render_candidates(
            inspect_retirement(selections=self._select(config), evidence=replacement), purpose="reset",
        )["candidates"][0]["action"], "edit")
        for evidence in (creation + replacement, replacement + creation):
            report = inspect_retirement(selections=self._select(config), evidence=evidence)
            (item,) = report["items"]
            self.assertEqual(item["verification"], "not-verified")
            self.assertFalse(item["write_authority"])
            view = render_candidates(report, purpose="reset")
            self.assertTrue(view["stop"])
            self.assertEqual(view["candidates"], [])
        self.assertEqual(config.read_bytes(), raw)

    def test_current_state_deployment_observation_does_not_prove_a_write(self):
        config = self.home / "mcp.json"
        raw = self._write(config, {"mcpServers": {"sbtd-graft": self._server(self._global())}})
        result = _result(str(config), "json", "graft-omp-mcp",
                         {"type": "absent", "checksum": None}, snapshot(config))
        manifest = _seal({"shared_operations": [{
            "resource_id": result["resource_id"], "operation_id": result["operation_ids"][0],
            "target": str(config), "selector": "graft-omp-mcp", "change": {"kind": "configure-graft"},
        }], "projects": []}, "manifest_id")
        manifest_file = self.vault / "manifest.json"
        manifest_file.write_bytes(canonical_json_bytes(manifest))
        historical = {"manifest_id": manifest["manifest_id"], "shared_results": [result], "projects": []}
        observed = {**historical, "reconciliation": {"kind": "current-state", "historical_execution": "unknown"}}
        for phase, payload in (("executed", historical), ("observed", observed)):
            file = self.vault / f"{phase}.json"
            file.write_bytes(canonical_json_bytes(_seal(payload, "deployment_id")))
            evidence = [{"kind": "manifest-deployment", "manifest": str(manifest_file), "deployment": str(file)}]
            report = inspect_retirement(selections=self._select(config), evidence=evidence)
            (item,) = report["items"]
            self.assertEqual(item["write_authority"], phase == "executed")
        self.assertEqual(config.read_bytes(), raw)

    def test_rollback_refuses_an_outside_backup_after_matching_the_post_state(self):
        config = self.home / "mcp.json"
        raw = self._write(config, {"mcpServers": {"sbtd-graft": self._server(self._global())}})
        evidence = self._evidence(_result(
            str(config), "json", "graft-omp-mcp", {"type": "absent", "checksum": None}, snapshot(config),
        ))
        report = inspect_retirement(selections=self._select(config), evidence=evidence)
        (candidate,) = render_candidates(report, purpose="reset")["candidates"]
        execution = self._execution(candidate, "real-retirement")
        backup = backup_candidate(candidate, destination=execution["backup_path"], vault=self.vault)
        outcome = apply_candidate(candidate, **execution)
        self.assertFalse(config.exists())
        outside = self.home / "original-outside-vault"
        outside.write_bytes(raw)
        outside.chmod(int(candidate["mode"], 8))
        self.assertEqual(snapshot(outside), backup["state"])
        legacy_payload = json.loads(Path(outcome["receipt_path"]).read_bytes())["payload"]
        for key in ("plan_id", "candidate_digest", "scope", "receipt_path", "intent_id"):
            del legacy_payload[key]
        legacy_payload["backup_ref"]["path"] = str(outside)
        moved_receipt = self.vault / "legacy-restore.json"
        moved_receipt.write_bytes(canonical_json_bytes(_seal(legacy_payload, "receipt_id")))
        after = {"type": "absent", "checksum": None, "mode": None}
        with self.assertRaises(ContractError) as error:
            restore_candidate(moved_receipt, scope=config.parent, vault=self.vault, expected=after, target=config)
        self.assertEqual(error.exception.code, "scope-conflict")
        self.assertFalse(config.exists())
        self.assertEqual(outside.read_bytes(), raw)
        restore_candidate(
            execution["receipt_path"], scope=config.parent, vault=self.vault, expected=after, target=config,
            plan_id=execution["plan_id"], backup_path=execution["backup_path"],
        )
        self.assertEqual(config.read_bytes(), raw)

    def test_vault_overlap_is_refused(self):
        config = self.home / "mcp.json"
        evidence = self._evidence(_result(
            str(config), "json", "graft-omp-mcp", {"type": "absent", "checksum": None},
            {"type": "file", "checksum": _sha(b"not installed")},
        ))
        with self.assertRaises(ContractError) as error:
            inspect_retirement(selections={
                "host": "omp",
                "configs": [{"role": "omp-mcp", "path": str(config)}],
                "projects": [str(self.root)],
                "vault": str(self.vault),
                "retiring_launchers": [],
            }, evidence=evidence)
        self.assertEqual(error.exception.code, "scope-conflict")

    def test_launcher_alias_is_reported_without_authorizing_a_config(self):
        config = self.home / "mcp.json"
        alias = self.home / "launcher-alias"
        try:
            alias.symlink_to(self.launcher)
        except OSError as error:
            if os.name == "nt" and error.winerror == 1314:
                self.skipTest("the Windows test user cannot create symbolic links")
            raise
        raw = self._write(config, {"mcpServers": {"custom": {"command": str(alias)}}})
        report = inspect_retirement(selections=self._select(config))
        view = render_candidates(report, purpose="reset")
        (item,) = view["blocked"]
        self.assertEqual((item["entry"], item["launcher"]["path"]), ("custom", str(alias)))
        self.assertFalse(item["recognized"])
        self.assertFalse(item["write_authority"])
        self.assertTrue(view["stop"])
        self.assertEqual(view["candidates"], [])
        self.assertEqual(config.read_bytes(), raw)

    def test_replacement_cannot_restore_an_older_launcher_under_the_same_entry(self):
        config = self.home / "mcp.json"
        original_args = self._global()
        original_args[-1] = str(self.home / "older-cli.js")
        original = self.vault / "previous.json"
        old = self._write(original, {"mcpServers": {"sbtd-graft": self._server(original_args)}})
        raw = self._write(config, {"mcpServers": {"sbtd-graft": self._server(self._global())}})
        before = snapshot(original)
        evidence = self._evidence(_result(
            str(config), "json", "graft-omp-mcp", before, snapshot(config),
            {"path": str(original), "state": before},
        ))
        report = inspect_retirement(selections=self._select(config), evidence=evidence)
        view = render_candidates(report, purpose="reset")
        self.assertTrue(view["stop"])
        self.assertEqual(view["candidates"], [])
        self.assertIn("older launcher dependency", view["blocked"][0]["reason"])
        self.assertEqual(config.read_bytes(), raw)
        self.assertEqual(original.read_bytes(), old)

    def test_matcher_only_group_preserves_detection_of_a_sibling_hook(self):
        config = self.home / "hooks.json"
        join = subprocess.list2cmdline if os.name == "nt" else shlex.join
        command = join([sys.executable, "-E", "-s", str(self.launcher), "hook", "--root", str(self.home),
                        "--node", str(self.node), "--entry", str(self.cli), "--event", "session-start"])
        matcher = {"matcher": "startup"}
        handler = {"hooks": [{"type": "command", "command": command}]}
        raw = self._write(config, {"hooks": {"SessionStart": [matcher, handler]}})
        selections = self._select(config, host="codex")
        selections["configs"] = [{"role": "codex-hooks", "path": str(config)}]
        view = render_candidates(inspect_retirement(selections=selections), purpose="reset")
        (blocked,) = view["blocked"]
        self.assertTrue(view["stop"])
        self.assertEqual(blocked["launcher"]["path"], str(self.launcher))

        original = self.vault / "hooks-backup.json"
        old = self._write(original, {"hooks": {"SessionStart": [matcher]}})
        before = snapshot(original)
        evidence = self._evidence(_result(
            str(config), "json", "graft-hooks", before, snapshot(config),
            {"path": str(original), "state": before},
        ))
        report = inspect_retirement(selections=selections, evidence=evidence)
        self.assertEqual(retirement_file_bytes(report=report, purpose="reset", target=str(config), before=raw), old)
        for malformed in ({"hooks": None}, {"hooks": ["invalid"]}, {"matcher": 3}, {"hook": [handler]}):
            unsafe = self._write(config, {"hooks": {"SessionStart": [malformed, handler]}})
            with self.subTest(malformed=malformed):
                report = inspect_retirement(selections=selections)
                self.assertEqual(report["status"], "blocked")
                self.assertEqual([(e["path"], e["code"]) for e in report["errors"]], [(str(config), "invalid-config")])
                self.assertTrue(render_candidates(report, purpose="reset")["stop"])
                self.assertEqual(config.read_bytes(), unsafe)

    def test_changed_fixed_root_restores_original_and_keeps_third_party(self):
        config = self.home / "mcp.json"
        root = self.home / "project"
        root.mkdir()
        key = "sbtd-graft-" + hashlib.sha256(str(root).encode()).hexdigest()[:16]
        before = {"mcpServers": {"other": {"type": "stdio", "command": "keep"}}}
        after = {"mcpServers": {"other": before["mcpServers"]["other"], key: self._server(self._fixed(root), cwd=str(root))}}
        before_raw = (json.dumps(before, indent=2) + "\n").encode()
        backup = self.vault / "original.json"
        backup.write_bytes(before_raw)
        raw = self._write(config, after)
        evidence = self._evidence(_result(
            str(config), "json", "graft-omp-mcp",
            {"type": "file", "checksum": _sha(before_raw)},
            {"type": "file", "checksum": _sha(raw)},
            {"path": str(backup), "state": {"type": "file", "checksum": _sha(before_raw)}},
        ))
        report = inspect_retirement(selections=self._select(config), evidence=evidence)
        item = next(row for row in report["items"] if row["entry"] == key)
        self.assertTrue(item["write_authority"])
        (candidate,) = render_candidates(report, purpose="cleanup")["candidates"]
        apply_candidate(
            candidate, scope=config.parent, vault=self.vault,
            expected={**candidate["before"], "mode": candidate["mode"],
                      "windows_acl_digest": candidate.get("windows_acl_digest")},
            receipt_path=self.vault / "fixed-receipt.json",
            plan_id=_sha(b"fixed retirement plan"),
        )
        restored = json.loads(config.read_text())
        self.assertEqual(restored["mcpServers"], {"other": {"type": "stdio", "command": "keep"}})
        self.assertEqual(_mode(config), candidate["mode"])

    def test_other_table_blocks_created_file_removal(self):
        config = self.home / "config.toml"
        text = (
            "[mcp_servers.sbtd-graft]\ncommand = \"/bin/python\"\nargs = "
            + json.dumps(self._global())
            + "\n[mcp_servers.sbtd-graft.env]\nDO_NOT_TRACK = \"1\"\nDNT = \"1\"\n\n[other]\nkeep = true\n"
        )
        config.write_bytes(text.encode())
        evidence = self._evidence(_result(
            str(config), "toml", "graft-mcp",
            {"type": "absent", "checksum": None}, snapshot(config),
        ))
        selections = self._select(config, host="codex")
        selections["configs"] = [{"role": "codex-mcp", "path": str(config)}]
        report = inspect_retirement(selections=selections, evidence=evidence)
        self.assertFalse(any(item.get("action") == "remove-file" for item in report["items"]))
        self.assertEqual(config.read_bytes(), text.encode())

    def test_symlink_is_not_reported_absent_and_missing_parent_is_not_blocked(self):
        target = self.home / "real.json"
        target.write_bytes(b'{"mcpServers":{"sbtd-graft":{"command":"x"}}}\n')
        link = self.home / "link.json"
        link.symlink_to(target)
        missing = self.home / "missing-parent" / "mcp.json"
        report = inspect_retirement(selections={
            "host": "omp",
            "configs": [{"role": "omp-mcp", "path": str(link)}, {"role": "omp-mcp", "path": str(missing)}],
            "projects": [],
            "vault": None,
            "retiring_launchers": [],
        })
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["errors"][0]["path"], str(link))
        self.assertFalse(any(item.get("path") == str(target) for item in report["items"]))
        self.assertNotIn("absent", {item.get("status") for item in report["items"]})
        fresh = inspect_retirement(selections={
            "host": "codex",
            "configs": [{"role": "codex-mcp", "path": str(missing)}, {"role": "codex-hooks", "path": str(missing)}],
            "projects": [],
            "vault": None,
            "retiring_launchers": [],
        })
        self.assertEqual(fresh["status"], "reported")
        self.assertEqual(fresh["items"], [])
        self.assertEqual(fresh["errors"], [])

    def test_present_retiring_launcher_blocks_unproven_entry(self):
        config = self.home / "mcp.json"
        self._write(config, {"mcpServers": {"sbtd-graft": self._server(self._global()), "other": {"command": "keep"}}})
        report = inspect_retirement(selections=self._select(config))
        self.assertTrue(report["items"][0]["at_risk"])
        self.assertFalse(report["items"][0]["write_authority"])
        view = render_candidates(report, purpose="reset")
        self.assertTrue(view["stop"])
        self.assertEqual(view["candidates"], [])
        self.assertEqual(config.read_bytes(), self.home.joinpath("mcp.json").read_bytes())

    def test_drift_after_inspect_does_not_become_authority(self):
        config = self.home / "mcp.json"
        raw = self._write(config, {"mcpServers": {"sbtd-graft": self._server(self._global())}})
        evidence = self._evidence(_result(
            str(config), "json", "graft-omp-mcp",
            {"type": "absent", "checksum": None}, {"type": "file", "checksum": _sha(raw)},
        ))
        report = inspect_retirement(selections=self._select(config), evidence=evidence)
        config.write_bytes(raw + b"\n")
        view = render_candidates(report, purpose="reset")
        self.assertEqual(view["candidates"], [])
        self.assertTrue(view["stop"])

    def test_manifest_mismatch_and_upgrade_reconcile_do_not_authorize(self):
        config = self.home / "mcp.json"
        raw = self._write(config, {"mcpServers": {"sbtd-graft": self._server(self._global())}})
        manifest = {"schema_version": 1, "payload": {"shared_operations": []}, "manifest_id": "0" * 64}
        deployment = {
            "schema_version": 1,
            "payload": {"manifest_id": "1" * 64, "shared_results": [], "projects": []},
            "deployment_id": "2" * 64,
        }
        manifest_path = self.vault / "manifest.json"
        deployment_path = self.vault / "deployment.json"
        manifest_path.write_bytes(json.dumps(manifest).encode())
        deployment_path.write_bytes(json.dumps(deployment).encode())
        with self.assertRaises(Exception):
            inspect_retirement(selections=self._select(config), evidence=[{
                "kind": "manifest-deployment", "manifest": str(manifest_path), "deployment": str(deployment_path),
            }])
        plan_payload = {
            "plan_schema": "upgrade-plan",
            "resources": [{
                "id": "resource",
                "kind": "mcp",
                "target": str(config),
                "before": {"type": "absent", "checksum": None},
                "desired": {"type": "file", "checksum": _sha(raw)},
                "details": {"launcher": {"path": str(self.launcher)}},
            }],
        }
        from onboard_contracts import canonical_json_bytes
        plan = {"schema_version": 1, "payload": plan_payload, "plan_id": hashlib.sha256(canonical_json_bytes(plan_payload)).hexdigest()}
        receipt_payload = {
            "receipt_schema": "upgrade-receipt",
            "plan_id": plan["plan_id"],
            "resources": [{
                "id": "resource",
                "result": "reconciled",
                "mutated": False,
                "after": {"type": "file", "checksum": _sha(raw)},
                "backup_ref": None,
            }],
        }
        receipt = {
            "schema_version": 1,
            "payload": receipt_payload,
            "receipt_id": hashlib.sha256(canonical_json_bytes(receipt_payload)).hexdigest(),
        }
        plan_path = self.vault / "plan.json"
        receipt_path = self.vault / "upgrade-receipt.json"
        plan_path.write_bytes(json.dumps(plan).encode())
        receipt_path.write_bytes(json.dumps(receipt).encode())
        with self.assertRaises(ContractError) as caught:
            inspect_retirement(selections=self._select(config), evidence=[{
                "kind": "upgrade-plan-apply", "plan": str(plan_path), "receipt": str(receipt_path),
            }])
        self.assertEqual(caught.exception.code, "binding-violation")
        resource = {
            "id": "resource",
            "kind": "mcp",
            "target": str(config),
            "before": {"type": "absent", "checksum": None},
            "desired": {"type": "file", "checksum": _sha(raw)},
            "decision": "install",
            "details": {"launcher": {"path": str(self.launcher)}},
        }
        report = inspect_retirement(selections=self._select(config), evidence=self._upgrade(
            resource, self._bound_row(resource, result="reconciled", mutated=False),
        ))
        self.assertFalse(any(item.get("write_authority") for item in report["items"]))

    def test_fence_splice_preserves_project_body(self):
        project = self.home / "project"
        project.mkdir()
        agents = project / "AGENTS.md"
        body = b"user rules\n"
        produced = body + b"\n<!-- graft:start -->\nmanaged\n<!-- graft:end -->\n"
        agents.write_bytes(produced)
        before = self.vault / "agents-before"
        before.write_bytes(body)
        evidence = self._evidence(_result(
            str(agents), "markdown", "graft-agents",
            {"type": "file", "checksum": _sha(body)},
            snapshot(agents),
            {"path": str(before), "state": {"type": "file", "checksum": _sha(body)}},
        ))
        report = inspect_retirement(selections={
            "host": None,
            "configs": [],
            "projects": [str(project)],
            "vault": str(self.vault),
            "retiring_launchers": [],
        }, evidence=evidence)
        self.assertEqual(report["items"][0]["path"], str(agents))
        self.assertEqual(report["items"][0]["body_policy"], "preserve")
        self.assertTrue(report["items"][0]["write_authority"])
        rendered = retirement_file_bytes(
            report=report, purpose="cleanup", target=str(agents), before=produced,
        )
        self.assertEqual(rendered, body)
        self.assertIn(HISTORY_DIRS[0], ("graft", ".graft"))
    def test_rc2_upgrade_receipt_admits_bound_mutation_and_restores_original(self):
        config = self.home / "mcp.json"
        before_doc = {"theme": "dark"}
        before_raw = (json.dumps(before_doc, indent=2) + "\n").encode()
        backup = self.vault / "original.json"
        backup.write_bytes(before_raw)
        raw = self._write(config, {"theme": "dark", "mcpServers": {"sbtd-graft": self._server(self._global())}})
        before_state = {"type": "file", "checksum": _sha(before_raw)}
        after_state = {"type": "file", "checksum": _sha(raw)}
        resource = {
            "id": "mcp",
            "kind": "mcp",
            "target": str(config),
            "before": before_state,
            "desired": after_state,
            "decision": "replace",
            "details": {"launcher": {"path": str(self.launcher)}},
        }
        row = self._bound_row(resource, backup={"path": str(backup), "state": before_state})
        report = inspect_retirement(selections=self._select(config), evidence=self._upgrade(resource, row))
        item = report["items"][0]
        self.assertEqual(item["verification"], "proven")
        self.assertTrue(item["write_authority"])
        rendered = retirement_file_bytes(report=report, purpose="upgrade", target=str(config), before=raw)
        self.assertEqual(rendered, before_raw)

    def test_upgrade_kind_mismatch_and_outside_backup_fail(self):
        config = self.home / "mcp.json"
        raw = self._write(config, {"mcpServers": {"sbtd-graft": self._server(self._global())}})
        before_state = {"type": "absent", "checksum": None}
        after_state = {"type": "file", "checksum": _sha(raw)}
        resource = {
            "id": "mcp", "kind": "mcp", "target": str(config),
            "before": before_state, "desired": after_state, "decision": "install",
        }
        row = self._bound_row(resource)
        row["kind"] = "shell"
        with self.assertRaises(ContractError) as caught:
            inspect_retirement(selections=self._select(config), evidence=self._upgrade(resource, row))
        self.assertEqual(caught.exception.code, "binding-violation")
        outside = self.home / "outside.json"
        outside.write_bytes(b"{}\n")
        outside_state = {"type": "file", "checksum": _sha(b"{}\n")}
        replaced = {
            "id": "mcp", "kind": "mcp", "target": str(config),
            "before": outside_state, "desired": after_state, "decision": "replace",
        }
        with self.assertRaises(ContractError) as caught:
            inspect_retirement(selections=self._select(config), evidence=self._upgrade(
                replaced, self._bound_row(replaced, backup={"path": str(outside), "state": outside_state}),
            ))
        self.assertEqual(caught.exception.code, "scope-conflict")

    def test_missing_launcher_does_not_change_unproven_ownership(self):
        config = self.home / "mcp.json"
        self._write(config, {"mcpServers": {"sbtd-graft": self._server(self._global()), "other": {"command": "keep"}}})
        self.launcher.unlink()
        report = inspect_retirement(selections=self._select(config))
        item = report["items"][0]
        self.assertEqual(item["status"], "dangling")
        self.assertEqual(item["launcher"]["presence"], "absent")
        self.assertEqual(item["verification"], "unproven")
        self.assertFalse(item["write_authority"])
        view = render_candidates(report, purpose="reset")
        self.assertTrue(view["stop"])
        self.assertEqual(view["candidates"], [])
        self.assertEqual(render_candidates(report, purpose="check")["stop"], False)

    def test_third_party_name_is_not_authorized(self):
        config = self.home / "mcp.json"
        self._write(config, {"mcpServers": {"sbtd-graft": {"type": "stdio", "command": "keep", "args": [], "env": {}}}})
        self.launcher.unlink()
        report = inspect_retirement(selections=self._select(config))
        self.assertFalse(any(item.get("write_authority") for item in report["items"]))
        self.assertFalse(any(item.get("status") == "dangling" for item in report["items"]))
        self.assertFalse(any(item.get("recognized") for item in report["items"]))

    def test_first_server_on_existing_object_restores_exact_original(self):
        config = self.home / "mcp.json"
        before_raw = (json.dumps({"theme": "dark"}, indent=2) + "\n").encode()
        backup = self.vault / "theme.json"
        backup.write_bytes(before_raw)
        raw = self._write(config, {"theme": "dark", "mcpServers": {"sbtd-graft": self._server(self._global())}})
        evidence = self._evidence(_result(
            str(config), "json", "graft-omp-mcp",
            {"type": "file", "checksum": _sha(before_raw)},
            {"type": "file", "checksum": _sha(raw)},
            {"path": str(backup), "state": {"type": "file", "checksum": _sha(before_raw)}},
        ))
        report = inspect_retirement(selections=self._select(config), evidence=evidence)
        self.assertTrue(report["items"][0]["write_authority"])
        self.assertEqual(
            retirement_file_bytes(report=report, purpose="upgrade", target=str(config), before=raw),
            before_raw,
        )

    def test_fixed_root_rewrite_does_not_resurrect_old_key(self):
        config = self.home / "mcp.json"
        root = self.home / "project"
        root.mkdir()
        key = "sbtd-graft-" + hashlib.sha256(str(root).encode()).hexdigest()[:16]
        before = {"mcpServers": {"other": {"command": "keep"}, key: self._server(self._fixed(root), cwd=str(root))}}
        after = {"mcpServers": {"other": {"command": "keep"}, "sbtd-graft": self._server(self._global())}}
        before_raw = (json.dumps(before, indent=2) + "\n").encode()
        backup = self.vault / "fixed.json"
        backup.write_bytes(before_raw)
        raw = self._write(config, after)
        evidence = self._evidence(_result(
            str(config), "json", "graft-omp-mcp",
            {"type": "file", "checksum": _sha(before_raw)},
            {"type": "file", "checksum": _sha(raw)},
            {"path": str(backup), "state": {"type": "file", "checksum": _sha(before_raw)}},
        ))
        report = inspect_retirement(selections=self._select(config), evidence=evidence)
        rendered = retirement_file_bytes(report=report, purpose="cleanup", target=str(config), before=raw)
        restored = json.loads(rendered)
        self.assertNotIn(key, restored["mcpServers"])
        self.assertNotIn("sbtd-graft", restored["mcpServers"])
        self.assertEqual(restored["mcpServers"]["other"], {"command": "keep"})

    def test_codex_fixed_root_retirement_serializes_toml_and_preserves_neighbors(self):
        config = self.home / "config.toml"
        root = self.home / "project"
        root.mkdir()
        fixed_key = "sbtd-graft-" + _sha(str(root).encode())[:16]
        neighbors = (
            '# Retain this user comment.\nmodel = "selected"  # retain inline trivia\n\n'
            '[mcp_servers.context7]\ncommand = "keep"\nargs = ["one", "two"]\n'
        )

        def table(key, argv, cwd=None):
            return (
                f"\n[mcp_servers.{key}]\ncommand = {json.dumps(str(self.home / 'python'))}\n"
                f"args = {json.dumps(argv)}\nenv = {{ DO_NOT_TRACK = '1', DNT = '1' }}\n"
                + (f"cwd = {json.dumps(str(cwd))}\n" if cwd is not None else "")
            )

        backup = self.vault / "fixed.toml"
        backup.write_bytes((neighbors + table(fixed_key, self._fixed(root), root)).encode())
        raw = (neighbors + table("sbtd-graft", self._global())).encode()
        config.write_bytes(raw)
        before = snapshot(backup)
        evidence = self._evidence(_result(
            str(config), "toml", "graft-mcp", before, snapshot(config),
            {"path": str(backup), "state": before},
        ))
        selections = self._select(config, host="codex")
        selections["configs"] = [{"role": "codex-mcp", "path": str(config)}]
        report = inspect_retirement(selections=selections, evidence=evidence)
        (candidate,) = render_candidates(report, purpose="cleanup")["candidates"]
        self.assertEqual(candidate["action"], "edit")
        apply_candidate(
            candidate, scope=config.parent, vault=self.vault,
            expected={**candidate["before"], "mode": candidate["mode"],
                      "windows_acl_digest": candidate.get("windows_acl_digest")},
            receipt_path=self.vault / "toml-retirement.json",
            plan_id=_sha(b"toml retirement plan"),
        )
        retired = config.read_text()
        self.assertIn(neighbors, retired)
        self.assertNotIn("sbtd-graft", retired)

    def test_renamed_mcp_key_is_watched_but_never_owned(self):
        config = self.home / "mcp.json"
        raw = self._write(config, {"mcpServers": {
            "renamed": self._server(self._global()),
            "unrelated": {"command": "elsewhere", "env": 7},
        }})
        evidence = self._evidence(_result(
            str(config), "json", "graft-omp-mcp", {"type": "absent", "checksum": None}, snapshot(config),
        ))
        selections = self._select(config)
        report = inspect_retirement(selections=selections, evidence=evidence)
        (item,) = render_candidates(report, purpose="reset")["blocked"]
        self.assertEqual((item["entry"], item["verification"]), ("renamed", "unproven"))
        self.assertFalse(item["write_authority"])
        self.launcher.unlink()
        selections["retiring_launchers"] = []
        report = inspect_retirement(selections=selections, evidence=evidence)
        (item,) = report["items"]
        self.assertEqual((item["entry"], item["status"], item["verification"]), ("renamed", "dangling", "unproven"))
        self.assertTrue(render_candidates(report, purpose="reset")["stop"])
        self.assertEqual(config.read_bytes(), raw)

    def test_custom_mcp_entry_with_relative_launcher_and_explicit_cwd_is_watched(self):
        config = self.home / "mcp.json"
        path = self.launcher
        raw = self._write(config, {"mcpServers": {
            "custom": {"command": str(self.home / "python"), "cwd": str(path.parent), "args": [path.name]},
        }})
        report = inspect_retirement(selections=self._select(config))
        (item,) = render_candidates(report, purpose="reset")["blocked"]
        self.assertEqual((item["entry"], item["launcher"]["path"]), ("custom", str(path)))
        self.assertFalse(item["write_authority"])
        self.assertEqual(config.read_bytes(), raw)

    def test_ambiguous_codex_mcp_tables_refuse_retirement(self):
        config = self.home / "config.toml"
        raw = (
            "[mcpServers.unrelated]\ncommand = 'keep'\n"
            "[mcp_servers.custom]\ncommand = " + json.dumps(str(self.launcher)) + "\n"
        ).encode()
        config.write_bytes(raw)
        selections = self._select(config, host="codex")
        selections["configs"] = [{"role": "codex-mcp", "path": str(config)}]
        report = inspect_retirement(selections=selections)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual([(e["path"], e["code"]) for e in report["errors"]], [(str(config), "invalid-config")])
        view = render_candidates(report, purpose="reset")
        self.assertTrue(view["stop"])
        self.assertEqual(view["candidates"], [])
        self.assertEqual(config.read_bytes(), raw)

    def test_nested_unowned_json_type_changes_block_attribution(self):
        config = self.home / "mcp.json"
        backup = self.vault / "original.json"
        for location in ("top-level", "neighbor"):
            with self.subTest(location=location):
                before = {"mcpServers": {}}
                after = {"mcpServers": {"sbtd-graft": self._server(self._global())}}
                left = before if location == "top-level" else before["mcpServers"]
                right = after if location == "top-level" else after["mcpServers"]
                left["foreign"] = {"nested": [True, {"fallback": False}]}
                right["foreign"] = {"nested": [1, {"fallback": 0}]}
                self._write(backup, before)
                raw = self._write(config, after)
                original = snapshot(backup)
                evidence = self._evidence(_result(
                    str(config), "json", "graft-omp-mcp", original, snapshot(config),
                    {"path": str(backup), "state": original},
                ))
                report = inspect_retirement(selections=self._select(config), evidence=evidence)
                self.assertEqual(render_candidates(report, purpose="reset")["candidates"], [])
                self.assertTrue(render_candidates(report, purpose="reset")["stop"])
                self.assertEqual(config.read_bytes(), raw)

    def test_merge_preserves_deduplicated_manual_disclosures(self):
        first, second = self.home / "first", self.home / "second"
        (first / "graft").mkdir(parents=True)
        (first / ".graft").mkdir()
        (second / "graft").mkdir(parents=True)
        left = inspect_retirement(selections={"projects": [str(first)]})
        right = inspect_retirement(selections={"projects": [str(first), str(second)]})
        expected = {
            ("graph", str(first / "graft")), ("graph-state", str(first / ".graft")),
            ("graph", str(second / "graft")), ("npm", "<npm root -g>/@nanonets/graft"),
            ("telemetry", "~/.graft/telemetry.json"),
        }
        manual = render_candidates(merge_reports([left, right]), purpose="cleanup")["manual"]
        self.assertEqual({(row["kind"], row["path"]) for row in manual}, expected)
        self.assertEqual(len(manual), len(expected))
        self.assertEqual(merge_reports([right, left])["manual"], manual)

    def test_path_escape_and_arbitrary_created_fence_fail(self):
        config = self.home / "mcp.json"
        self._write(config, {"mcpServers": {}})
        with self.assertRaises(ContractError):
            inspect_retirement(selections=self._select(config), evidence=[{
                "kind": "operation-results", "path": str(self.vault / ".." / "outside.json"),
            }])
        project = self.home / "fenced"
        project.mkdir()
        agents = project / "AGENTS.md"
        agents.write_bytes(b"<!-- graft:start -->\nsecrets\n<!-- graft:end -->\n")
        evidence = self._evidence(_result(
            str(agents), "markdown", "graft-agents",
            {"type": "absent", "checksum": None}, snapshot(agents),
        ), name="fence-results.json")
        report = inspect_retirement(selections={
            "host": None, "configs": [], "projects": [str(project)],
            "vault": str(self.vault), "retiring_launchers": [],
        }, evidence=evidence)
        self.assertFalse(any(item.get("write_authority") for item in report["items"]))
        self.assertFalse(any(item.get("action") == "remove-file" for item in report["items"]))

    def test_empty_hook_group_does_not_authorize(self):
        config = self.home / "hooks.json"
        before_raw = (json.dumps({"other": True}, indent=2) + "\n").encode()
        backup = self.vault / "hooks-before.json"
        backup.write_bytes(before_raw)
        raw = self._write(config, {"other": True, "hooks": {"SessionStart": [{"hooks": []}]}})
        evidence = self._evidence(_result(
            str(config), "json", "graft-hooks",
            {"type": "file", "checksum": _sha(before_raw)},
            {"type": "file", "checksum": _sha(raw)},
            {"path": str(backup), "state": {"type": "file", "checksum": _sha(before_raw)}},
        ), name="hook-results.json")
        selections = self._select(config, host="codex")
        selections["configs"] = [{"role": "codex-hooks", "path": str(config)}]
        report = inspect_retirement(selections=selections, evidence=evidence)
        self.assertFalse(any(item.get("write_authority") for item in report["items"]))
        self.assertEqual(config.read_bytes(), raw)

    def test_same_event_hook_commands_have_distinct_identities_and_risks(self):
        config = self.home / "hooks.json"
        safe = self.home / "present-launcher.py"
        safe.write_bytes(b"keep")
        join = subprocess.list2cmdline if os.name == "nt" else shlex.join
        commands = [
            join([sys.executable, "-E", "-s", str(launcher), "hook", "--root", str(root),
                  "--node", str(self.node), "--entry", str(self.cli), "--event", "session-start"])
            for launcher, root in (
                (self.launcher, self.home / "a"), (safe, self.home / "a"), (safe, self.home / "b")
            )
        ]
        raw = self._write(config, {"hooks": {"SessionStart": [
            {"hooks": [{"type": "command", "command": command}]} for command in commands
        ]}})
        selections = self._select(config, host="codex")
        selections["configs"] = [{"role": "codex-hooks", "path": str(config)}]
        report = inspect_retirement(selections=selections)
        self.assertEqual(len({item["id"] for item in report["items"]}), 3)
        view = render_candidates(report, purpose="reset")
        self.assertTrue(view["stop"])
        self.assertEqual([item["launcher"]["path"] for item in view["blocked"]], [str(self.launcher)])

        evidence = self._evidence(_result(
            str(config), "json", "graft-hooks", {"type": "absent", "checksum": None}, snapshot(config),
        ))
        report = inspect_retirement(selections=selections, evidence=evidence)
        (candidate,) = render_candidates(report, purpose="reset")["candidates"]
        self.assertEqual(candidate["action"], "remove-file")
        self.assertEqual(len({item["entry"] for item in candidate["entries"]}), 3)
        self.assertEqual(config.read_bytes(), raw)

        backup = self.vault / "old-hooks.json"
        self._write(backup, {"hooks": {"SessionStart": [
            {"hooks": [{"type": "command", "command": command}]} for command in commands[1:]
        ]}})
        original = snapshot(backup)
        evidence = self._evidence(_result(
            str(config), "json", "graft-hooks", original, snapshot(config),
            {"path": str(backup), "state": original},
        ))
        report = inspect_retirement(selections=selections, evidence=evidence)
        view = render_candidates(report, purpose="reset")
        self.assertTrue(view["stop"])
        self.assertEqual(view["candidates"], [])
        (item,) = view["blocked"]
        self.assertEqual((item["verification"], item["write_authority"]), ("proven", False))

    def test_same_command_hook_metadata_cannot_change_with_managed_addition(self):
        config = self.home / "hooks.json"
        backup = self.vault / "hooks-before.json"
        join = subprocess.list2cmdline if os.name == "nt" else shlex.join
        command = join([sys.executable, "-E", "-s", str(self.launcher), "hook", "--root", str(self.home),
                        "--node", str(self.node), "--entry", str(self.cli), "--event", "session-start"])
        other = {"type": "command", "command": "foreign-hook", "timeout": True}
        self._write(backup, {"hooks": {"SessionStart": [{"hooks": [other]}]}})
        raw = self._write(config, {"hooks": {"SessionStart": [
            {"hooks": [dict(other, timeout=1)]}, {"hooks": [{"type": "command", "command": command}]},
        ]}})
        original = snapshot(backup)
        evidence = self._evidence(_result(
            str(config), "json", "graft-hooks", original, snapshot(config),
            {"path": str(backup), "state": original},
        ))
        selections = self._select(config, host="codex")
        selections["configs"] = [{"role": "codex-hooks", "path": str(config)}]
        view = render_candidates(inspect_retirement(selections=selections, evidence=evidence), purpose="reset")
        self.assertTrue(view["stop"])
        self.assertEqual(view["candidates"], [])
        self.assertEqual(config.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
