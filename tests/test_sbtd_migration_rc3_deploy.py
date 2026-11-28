"""rc.3 deploy cutover: refuse sealed Graft writes; write the approved body.

No smoke is invented. A sealed Graft operation fails before any backup or
target write. An approved-agents ensure-file-block writes the pause-stripped
body, not a template and not the pause prefix.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from onboard import main as onboard_main
from onboard_contracts import ContractError, load_document, validate_declared_bindings
from sbtd_deployment import (
    approved_agents_selector,
    execute_migration_deployment,
    execute_resource,
    load_deployment_context,
    reject_legacy_execution,
)
from sbtd_migration import _result_index, apply_migration, cleanup_migration, runtime_versions
from sbtd_migration_files import save_document, snapshot
from sbtd_migration_plan import _check_followup_predecessor_outcomes, plan_migration
from sbtd_migration_verify import verify_migration

from tests.test_sbtd_codex_deployment import _isolated_home
from tests.test_sbtd_migration_apply import legacy_project
from tests.test_sbtd_migration_cleanup import _fake_vendor_adapter
from tests.test_sbtd_migration_rc3_graft import build_completed_historical

_GONE = (
    "verified_runtime",
    "build_project_graph",
    "launch_bindings",
    "run_native",
    "run_project_smoke",
    "render_configuration",
    "plan_normal_wiring",
    "execute_normal_wiring",
    "deployment_operations",
    "policy_reference",
    "archived_policy_reference",
)


class _Batch:
    def __init__(self, base, *, evidence_in_codex=False):
        self.root = legacy_project(base, "project")
        self.agents = self.root / "AGENTS.md"
        self.foreign = b"Foreign project rules; no approved replacement.\n"
        self.agents.write_bytes(self.foreign)
        self.home = base / "home"
        self.codex = self.home / ".codex"
        self.vault = base / "vault"
        self.evidence = self.codex if evidence_in_codex else base / "evidence"
        for path in (self.home, self.vault, self.evidence):
            path.mkdir(mode=0o700)
        self.environment = _isolated_home(
            self.home, self.codex, self.home / ".agent/skills"
        )

    def plan(self, **kwargs):
        return plan_migration(
            [self.root],
            self.vault,
            "fixture",
            None,
            tool_versions=runtime_versions(),
            **kwargs,
        )

    def apply(self, manifest, name):
        manifest_path = self.evidence / f"{name}.json"
        save_document(manifest_path, manifest, private_root=self.evidence)
        applied, code = apply_migration(
            manifest_path, confirmed=True, no_routing_approvals=True
        )
        if code != 0:
            raise AssertionError(applied)
        apply_id = applied["migration"]["apply_receipt"]["apply_id"]
        return manifest_path, self.evidence / f"apply-{apply_id}.json"

    def load(self, manifest_path, apply_path, output, mode="init"):
        return load_deployment_context(
            manifest_path,
            apply_path,
            output,
            previous_path=None,
            mode=mode,
            roots=[self.root],
            hooks_authorized=False,
        )


class Rc3DeployCutoverTests(unittest.TestCase):
    def test_deleted_graft_launchers_are_absent(self):
        import sbtd_deployment

        for name in _GONE:
            self.assertFalse(hasattr(sbtd_deployment, name), name)

    def test_public_init_refuses_a_bound_historical_deployment_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            built = build_completed_historical(base, drift=False)
            manifest = load_document(built["manifest_path"].read_bytes(), "manifest")
            applied = load_document(built["apply_path"].read_bytes(), "apply_receipt")
            validate_declared_bindings(manifest, {"apply_receipt": applied})
            output = built["evidence"] / "new-deployment.json"
            before = snapshot(base)
            argv = [
                str(SCRIPTS / "onboard.py"), "init-projects", "--yes", "--json",
                "--projects-root", ",".join(map(str, built["roots"])),
                "--migration-manifest", str(built["manifest_path"]),
                "--migration-apply-receipt", str(built["apply_path"]),
                "--deployment-evidence-out", str(output),
            ]
            with (
                mock.patch.dict(os.environ, built["environment"]),
                mock.patch.object(sys, "argv", argv),
                contextlib.redirect_stdout(io.StringIO()) as stdout,
            ):
                self.assertEqual(onboard_main(), 2)
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["reason"], "a sealed plan still contains Graft operations; regenerate the plan")
            self.assertIsNone(result["deploymentEvidence"])
            self.assertEqual(snapshot(base), before)

    def test_reject_legacy_execution_does_not_touch_the_target(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "config.toml"
            target.write_bytes(b"before\n")
            before = target.read_bytes()
            with self.assertRaises(ContractError) as raised:
                reject_legacy_execution(
                    {
                        "projects": [
                            {
                                "private_operations": [
                                    {
                                        "selector": "graft-mcp",
                                        "change": {"kind": "copy-file"},
                                    }
                                ]
                            }
                        ],
                        "shared_operations": [],
                    }
                )
            self.assertEqual(raised.exception.code, "unsupported-in-rc.3")
            self.assertEqual(target.read_bytes(), before)

    def test_approved_agents_write_strips_pause_after_preflight(self):
        pause = (
            Path(__file__).resolve().parents[1]
            / "sbtd-workflow-onboard"
            / "assets"
            / "migration-paused-agents.txt"
        ).read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = base / "project"
            vault = base / "vault"
            root.mkdir(mode=0o700)
            vault.mkdir(mode=0o700)
            body = b"unique-approved-body-8e2b4c\n"
            candidate = vault / "candidate.md"
            candidate.write_bytes(pause + b"\n" + body)
            target = root / "AGENTS.md"
            target.write_bytes(pause + b"\n" + body)
            before = target.read_bytes()
            result = execute_resource(
                {
                    "phase": "deploy",
                    "resource_id": "rid",
                    "operation_id": "oid",
                    "dependent_projects": [str(root)],
                    "target": str(target),
                    "selector": approved_agents_selector(body),
                    "change": {
                        "kind": "ensure-file-block",
                        "source_ref": {
                            "path": str(candidate),
                            "state": snapshot(candidate),
                        },
                    },
                },
                expected=snapshot(target),
                root=root,
                private_root=vault,
                backup_path=vault / "backup",
            )
            self.assertEqual(result["status"], "succeeded")
            self.assertEqual(target.read_bytes(), body)
            self.assertNotEqual(target.read_bytes(), before)
            self.assertFalse((vault / "approved-agents").exists())
            self.assertNotIn(b"AGENTS.project.md", target.read_bytes())

    def test_bad_approved_candidate_or_selector_never_creates_scope_or_backup(self):
        for change in ("candidate", "selector"):
            for present in (False, True):
                with (
                    self.subTest(change=change, present=present),
                    tempfile.TemporaryDirectory() as directory,
                ):
                    base = Path(directory).resolve()
                    root, vault = base / "project", base / "vault"
                    target, backup = root / "AGENTS.md", vault / "deploy" / "original"
                    vault.mkdir(mode=0o700)
                    if present:
                        root.mkdir(mode=0o700)
                        target.write_bytes(b"Keep project rules.\n")
                    pause = (
                        SCRIPTS.parent / "assets/migration-paused-agents.txt"
                    ).read_bytes()
                    body = b"Approved project rules.\n"
                    candidate = vault / "candidate.md"
                    candidate.write_bytes(pause + b"\n" + body)
                    source = {"path": str(candidate), "state": snapshot(candidate)}
                    if change == "candidate":
                        candidate.write_bytes(pause + b"\nChanged candidate.\n")
                    selector = approved_agents_selector(body if change == "candidate" else b"other")
                    before = snapshot(base)
                    result = execute_resource(
                        {
                            "resource_id": "rid",
                            "operation_id": "oid",
                            "dependent_projects": [str(root)],
                            "target": str(target),
                            "selector": selector,
                            "change": {"kind": "ensure-file-block", "source_ref": source},
                        },
                        expected=snapshot(target), root=root, private_root=vault, backup_path=backup,
                    )
                    self.assertEqual(result["status"], "blocked")
                    self.assertIsNone(result["backup_ref"])
                    self.assertFalse(backup.parent.exists())
                    self.assertEqual(root.exists(), present)
                    self.assertEqual(snapshot(base), before)

    def test_reserved_output_cannot_create_smoke_directories_or_change_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            batch = _Batch(base, evidence_in_codex=True)
            with mock.patch.dict(os.environ, batch.environment):
                manifest_path, apply_path = batch.apply(batch.plan(deployment_mode="init"), "plan")
                smoke = batch.evidence / "deployment-smoke"
                digest = hashlib.sha256(str(batch.root).encode("utf-8")).hexdigest()
                for output in (
                    smoke, smoke / "another-scope.json",
                    smoke / digest / "receipt.json", batch.codex / "AGENTS.md",
                ):
                    with self.subTest(output=output):
                        before = snapshot(base)
                        with self.assertRaises(ContractError) as failure:
                            execute_migration_deployment(batch.load(manifest_path, apply_path, output))
                        self.assertEqual(failure.exception.code, "private-scope")
                        self.assertEqual(snapshot(base), before)
                        self.assertFalse(smoke.exists())
                (smoke / digest).mkdir(mode=0o700, parents=True)
                before = snapshot(base)
                with self.assertRaises(ContractError) as failure:
                    batch.load(manifest_path, apply_path, smoke / digest / "receipt.json")
                self.assertEqual(failure.exception.code, "private-scope")
                self.assertEqual(snapshot(base), before)

    def test_pretty_bound_inputs_are_refused_before_deployment_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            batch = _Batch(base)
            with mock.patch.dict(os.environ, batch.environment):
                manifest_path, apply_path = batch.apply(batch.plan(deployment_mode="init"), "plan")
                output = batch.evidence / "deployment.json"
                for path in (manifest_path, apply_path):
                    with self.subTest(path=path.name):
                        original = path.read_bytes()
                        path.write_text(json.dumps(json.loads(original), indent=2), encoding="utf-8")
                        before = snapshot(base)
                        with self.assertRaises(ContractError) as failure:
                            execute_migration_deployment(batch.load(manifest_path, apply_path, output))
                        self.assertEqual(failure.exception.code, "invalid-document")
                        self.assertEqual(snapshot(base), before)
                        self.assertFalse((batch.evidence / "deployment-smoke").exists())
                        path.write_bytes(original)

    def test_unsigned_zero_write_successor_smokes_verifies_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as directory:
            batch = _Batch(Path(directory).resolve())
            with mock.patch.dict(os.environ, batch.environment):
                original_path, original_apply = batch.apply(batch.plan(), "original")
                successor = batch.plan(
                    deployment_mode="init-projects", successor_manifest=original_path,
                    successor_apply_receipt=original_apply,
                )
                project = successor["payload"]["projects"][0]
                self.assertIsNone(project.get("agents_no_touch"))
                self.assertEqual([op["phase"] for op in project["private_operations"]], ["cleanup"])
                self.assertEqual(successor["payload"]["deployment"], {
                    "mode": "init-projects", "platform": "codex", "inputs": [],
                })
                manifest_path, apply_path = batch.apply(successor, "successor")
                source = project["sources"][0]
                before = snapshot(batch.root)
                home_before = snapshot(batch.home)
                vault_before = snapshot(batch.vault)
                output = batch.evidence / "deployment.json"

                deployed, code = execute_migration_deployment(
                    batch.load(manifest_path, apply_path, output, mode="init-projects")
                )
                self.assertEqual(code, 0, deployed)
                self.assertEqual(deployed["operationResults"], [])
                report_ref, _summary = deployed["projects"][0]["report_refs"]
                report = json.loads(Path(report_ref["path"]).read_bytes())
                self.assertEqual(report["manifestId"], successor["manifest_id"])
                self.assertEqual(report["applyId"], json.loads(apply_path.read_bytes())["apply_id"])
                self.assertEqual(report["exitCode"], 0)
                self.assertEqual(report["mockStrategy"], "none")
                self.assertEqual(snapshot(batch.root), before)
                self.assertEqual(snapshot(batch.home), home_before)
                self.assertEqual(snapshot(batch.vault), vault_before)
                self.assertEqual(snapshot(Path(source["path"])), source["state"])

                verified, code = verify_migration(manifest_path, apply_path, output)
                self.assertEqual(code, 0, verified)
                verification = verified["migration"]["verification"]
                verification_path = batch.evidence / "verified.json"
                save_document(verification_path, verification, private_root=batch.evidence)
                with _fake_vendor_adapter():
                    cleaned, code = cleanup_migration(
                        manifest_path, apply_path, output, verification_path,
                        confirm_cleanup=verification["verification_id"],
                    )
                self.assertEqual(code, 0, cleaned)
                self.assertEqual(cleaned["status"], "cleaned")
                self.assertFalse(Path(source["path"]).exists())
                self.assertEqual(batch.agents.read_bytes(), batch.foreign)
                self.assertEqual(snapshot(batch.home), home_before)

    def test_historical_followup_still_requires_completed_predecessor_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            built = build_completed_historical(base, drift=False)
            manifest = load_document(built["manifest_path"].read_bytes(), "manifest")
            applied = load_document(built["apply_path"].read_bytes(), "apply_receipt")
            deployment = load_document(built["deployment_path"].read_bytes(), "deployment_evidence")
            validate_declared_bindings(
                manifest, {"apply_receipt": applied, "deployment_evidence": deployment},
            )
            chain = [(manifest, {"apply": _result_index(applied), "deploy": _result_index(deployment)})]
            unchanged = snapshot(base)
            with self.assertRaises(ContractError) as raised:
                _check_followup_predecessor_outcomes(chain, overwritten=())
            self.assertEqual(raised.exception.code, "unsupported-in-rc.3")
            with (
                mock.patch("sbtd_migration._LINEAGE_PUBLIC_KEY", built["public"]),
                mock.patch("sbtd_migration._LINEAGE_DOCUMENT", built["pair"]),
                self.assertRaises(ContractError) as incomplete,
            ):
                _check_followup_predecessor_outcomes(chain, overwritten=(), bind_historical=True)
            self.assertEqual(incomplete.exception.code, "followup-conflict")
            self.assertEqual(snapshot(base), unchanged)

    def test_real_smoke_refs_are_on_disk_and_do_not_rewrite_the_seal(self):
        from sbtd_deployment_smoke import run_project_smoke

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "project"
            evidence = base / "evidence"
            root.mkdir(mode=0o700)
            evidence.mkdir(mode=0o700)
            sealed = root / "AGENTS.md"
            sealed.write_bytes(b"sealed-approved-body\n")
            before = sealed.read_bytes()
            refs = run_project_smoke(root, evidence)
            self.assertEqual(len(refs), 2)
            report, summary = (Path(ref["path"]) for ref in refs)
            self.assertEqual(report.suffix, ".json")
            self.assertEqual(report.stem, summary.stem)
            self.assertNotEqual(summary.suffix, ".json")
            for ref in refs:
                path = Path(ref["path"])
                self.assertTrue(path.is_file())
                self.assertTrue(path.is_relative_to(evidence))
                self.assertEqual(snapshot(path), ref["state"])
            self.assertEqual(sealed.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
