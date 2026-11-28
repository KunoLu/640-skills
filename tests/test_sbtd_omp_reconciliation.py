"""OMP current-state reconciliation without Graft launchers.

A genuine OMP init batch copies canonical installation files. Reconciliation
observes that current state after the historical receipt is lost. Drift,
invented originals, and a sealed Graft operation fail closed before a new
evidence write.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import onboard_contracts as contracts
from sbtd_deployment import execute_migration_deployment, load_deployment_context
from sbtd_migration import apply_migration, runtime_versions
from sbtd_migration_files import snapshot
from sbtd_migration_plan import plan_migration
from sbtd_migration_verify import verify_migration
from sbtd_reconciliation import reconcile_deployment

from tests.onboard_contract_fixtures import legacy_graft_operation
from tests.test_sbtd_migration_apply import legacy_project
from tests.test_sbtd_migration_verify import _tree_bytes
from tests.test_sbtd_reconciliation import _apply_only_operation, _drift_target, _stage_results

_ABSENT = {"type": "absent", "checksum": None}


class _OmpBatch:
    def __init__(self, case, *, manifest_in_agent_dir=False, no_touch=False):
        directory = tempfile.TemporaryDirectory()
        case.addCleanup(directory.cleanup)
        base = Path(directory.name).resolve()
        self.base = base
        self.root = legacy_project(base, "project")
        if no_touch:
            from onboard import PROJECT_AGENTS_TEMPLATE

            (self.root / "AGENTS.md").write_bytes(PROJECT_AGENTS_TEMPLATE.read_bytes())
            hashes_path = self.root / ".trellis/.template-hashes.json"
            hashes = json.loads(hashes_path.read_bytes())
            hashes["hashes"]["AGENTS.md"] = hashlib.sha256(b"old owned rules").hexdigest()
            hashes_path.write_text(json.dumps(hashes), encoding="utf-8")
        self.home = base / "home"
        self.agent = self.home / ".omp/agent"
        self.codex = self.home / ".codex"
        self.vault = base / "vault"
        self.evidence = base / "evidence"
        for path in (self.agent, self.codex, self.vault, self.evidence):
            path.mkdir(parents=True, mode=0o700)
        (self.agent / "config.yml").write_text("enabledProviders: []\n", encoding="utf-8")
        self.environment = {
            "HOME": str(self.home),
            "USERPROFILE": str(self.home),
            "CODEX_HOME": str(self.codex),
            "AGENT_SKILLS_DIR": str(self.home / ".agent/skills"),
            "PI_CODING_AGENT_DIR": str(self.agent),
            "PI_CONFIG_DIR": ".omp",
            "OMP_PROFILE": "default",
            "PI_PROFILE": "default",
            "PI_CONFIG_FILES": "",
            "CLAUDE_CONFIG_DIR": str(self.home / ".claude"),
            "XDG_DATA_HOME": str(self.home / ".local/share"),
        }
        manifest_dir = self.agent if manifest_in_agent_dir else self.evidence
        with mock.patch.dict(os.environ, self.environment):
            self.manifest = plan_migration(
                [self.root],
                self.vault,
                "fixture",
                None,
                tool_versions=runtime_versions(),
                deployment_mode="init",
                deployment_platform="omp",
            )
            self.operation = self._install_operation()
            self.target = Path(self.operation["target"])
            self.manifest_path = manifest_dir / "manifest.json"
            self.manifest_path.write_bytes(contracts.canonical_json_bytes(self.manifest))
            applied, code = apply_migration(
                self.manifest_path, confirmed=True, no_routing_approvals=True
            )
            if code != 0:
                raise AssertionError(f"fixture apply failed: {applied}")
            receipt = applied["migration"]["apply_receipt"]
            self.apply_path = manifest_dir / ("apply-" + receipt["apply_id"] + ".json")
            self.missing_path = manifest_dir / "interrupted-deployment.json"
            context = load_deployment_context(
                self.manifest_path,
                self.apply_path,
                self.missing_path,
                previous_path=None,
                mode="init",
                roots=[self.root],
                hooks_authorized=False,
            )
            deployed, code = execute_migration_deployment(context)
            if code != 0:
                raise AssertionError(f"fixture deployment failed: {deployed}")
            self.missing_path.unlink()

    def _install_operation(self):
        return next(
            operation
            for operation in self.manifest["payload"]["shared_operations"]
            if operation["phase"] == "deploy"
            and operation["target"] == str(self.agent / "AGENTS.md")
        )


def _reconcile(batch, output_path):
    with mock.patch.dict(os.environ, batch.environment):
        return reconcile_deployment(
            batch.manifest_path,
            batch.apply_path,
            batch.missing_path,
            output_path,
            confirmed=True,
        )


def _observed(batch, evidence):
    return next(
        result
        for result in evidence["payload"]["shared_results"]
        if result["resource_id"] == batch.operation["resource_id"]
    )


class OmpCurrentStateReconciliationLifecycleTests(unittest.TestCase):
    def test_installed_copy_reconciles_and_verifies(self):
        batch = _OmpBatch(self)
        self.assertTrue(batch.target.is_file())
        deployed_bytes = batch.target.read_bytes()
        self.assertNotIn(b"sbtd-graft", deployed_bytes)
        project_before = _tree_bytes(batch.root)
        home_before = _tree_bytes(batch.home)
        originals_before = _tree_bytes(batch.vault)
        output_path = batch.evidence / "current-state-evidence.json"

        result = _reconcile(batch, output_path)
        evidence = result["evidence"]
        self.assertEqual(evidence["payload"]["reconciliation"]["kind"], "current-state")
        observed = _observed(batch, evidence)
        self.assertEqual(observed["status"], "succeeded")
        self.assertEqual(observed["after"], snapshot(batch.target))

        with mock.patch.dict(os.environ, batch.environment):
            verified, verify_code = verify_migration(
                batch.manifest_path, batch.apply_path, output_path
            )
        self.assertEqual(verify_code, 0, verified)
        self.assertEqual(
            verified["migration"]["verification"]["payload"]["acceptance_basis"],
            "current-state",
        )
        self.assertEqual(batch.target.read_bytes(), deployed_bytes)
        self.assertFalse(batch.missing_path.exists())
        self.assertEqual(_tree_bytes(batch.root), project_before)
        self.assertEqual(_tree_bytes(batch.home), home_before)
        self.assertEqual(_tree_bytes(batch.vault), originals_before)

    def test_no_touch_agents_bytes_survive_reconciliation(self):
        batch = _OmpBatch(self, no_touch=True)
        agents = batch.root / "AGENTS.md"
        before = agents.read_bytes()
        output_path = batch.evidence / "current-state-evidence.json"
        _reconcile(batch, output_path)
        self.assertEqual(agents.read_bytes(), before)
        self.assertNotIn(b"<!-- graft:start -->", before)


class OmpCurrentStateReconciliationRefusalTests(unittest.TestCase):
    def test_no_touch_drift_after_final_provenance_blocks_reconciliation(self):
        from sbtd_migration import _require_reconciliation_provenance

        batch = _OmpBatch(self, no_touch=True)
        agents = batch.root / "AGENTS.md"
        drifted = agents.read_bytes() + b"\nOperator edit after provenance check.\n"
        output = batch.evidence / "current-state-evidence.json"
        calls = 0

        def drift_after_final_provenance(*args, **kwargs):
            nonlocal calls
            refs = _require_reconciliation_provenance(*args, **kwargs)
            calls += 1
            if calls == 2:
                agents.write_bytes(drifted)
            return refs

        with (
            mock.patch(
                "sbtd_migration._require_reconciliation_provenance",
                side_effect=drift_after_final_provenance,
            ),
            self.assertRaises(contracts.ContractError) as failure,
        ):
            _reconcile(batch, output)
        self.assertEqual(calls, 2)
        self.assertEqual(failure.exception.code, "state-conflict")
        self.assertEqual(agents.read_bytes(), drifted)
        self.assertFalse(output.exists())
        self.assertFalse(batch.missing_path.exists())

    def test_no_touch_drift_after_retry_provenance_blocks_publication(self):
        from sbtd_migration import _require_reconciliation_provenance

        batch = _OmpBatch(self, no_touch=True)
        agents = batch.root / "AGENTS.md"
        drifted = agents.read_bytes() + b"\nOperator edit during retry.\n"
        previous = batch.evidence / "current-state-evidence.json"
        _reconcile(batch, previous)
        previous_bytes = previous.read_bytes()
        retry = batch.evidence / "retry.json"
        host_before = snapshot(batch.home)
        vault_before = snapshot(batch.vault)

        def drift_after_provenance(*args, **kwargs):
            refs = _require_reconciliation_provenance(*args, **kwargs)
            agents.write_bytes(drifted)
            return refs

        with mock.patch.dict(os.environ, batch.environment):
            context = load_deployment_context(
                batch.manifest_path, batch.apply_path, retry, previous_path=previous,
                mode="init", roots=[batch.root], hooks_authorized=False,
            )
            with mock.patch(
                "sbtd_migration._require_reconciliation_provenance",
                side_effect=drift_after_provenance,
            ) as provenance:
                result, code = execute_migration_deployment(context)
        provenance.assert_called_once()
        self.assertEqual(code, 5, result)
        self.assertIsNone(result["deploymentEvidence"])
        self.assertFalse(retry.exists())
        self.assertFalse(batch.missing_path.exists())
        self.assertEqual(agents.read_bytes(), drifted)
        self.assertEqual(previous.read_bytes(), previous_bytes)
        self.assertEqual(snapshot(batch.home), host_before)
        self.assertEqual(snapshot(batch.vault), vault_before)
        evidence_before = snapshot(batch.evidence)
        with (
            mock.patch.dict(os.environ, batch.environment),
            self.assertRaises(contracts.ContractError) as failure,
        ):
            load_deployment_context(
                batch.manifest_path, batch.apply_path, retry, previous_path=previous,
                mode="init", roots=[batch.root], hooks_authorized=False,
            )
        self.assertEqual(failure.exception.code, "state-conflict")
        self.assertEqual(snapshot(batch.evidence), evidence_before)

    def test_reconciliation_reserves_both_outputs_from_the_smoke_directory(self):
        batch = _OmpBatch(self)
        digest = hashlib.sha256(str(batch.root).encode("utf-8")).hexdigest()
        smoke_path = batch.evidence / "deployment-smoke" / digest / "receipt.json"
        plain_path = batch.evidence / "current-state-evidence.json"
        before = snapshot(batch.base)
        with mock.patch.dict(os.environ, batch.environment):
            for missing, output in ((smoke_path, plain_path), (batch.missing_path, smoke_path)):
                with self.subTest(missing=missing, output=output):
                    with self.assertRaises(contracts.ContractError) as failure:
                        reconcile_deployment(
                            batch.manifest_path, batch.apply_path, missing, output, confirmed=True
                        )
                    self.assertEqual(failure.exception.code, "private-scope")
                    self.assertEqual(snapshot(batch.base), before)

    def test_tampered_install_target_fails_closed_without_repairs(self):
        batch = _OmpBatch(self)
        tampered = batch.target.read_bytes() + b"\ntampered\n"
        batch.target.write_bytes(tampered)
        evidence_before = _tree_bytes(batch.evidence)
        output_path = batch.evidence / "current-state-evidence.json"

        with self.assertRaises(contracts.ContractError) as failure:
            _reconcile(batch, output_path)
        self.assertEqual(failure.exception.code, "state-conflict")
        self.assertFalse(output_path.exists())
        self.assertFalse(batch.missing_path.exists())
        self.assertEqual(batch.target.read_bytes(), tampered)
        self.assertEqual(_tree_bytes(batch.evidence), evidence_before)

    def test_sealed_graft_operation_is_rejected_before_write(self):
        batch = _OmpBatch(self)
        payload = json.loads(contracts.canonical_json_bytes(batch.manifest))["payload"]
        payload["projects"][0]["private_operations"].append(
            legacy_graft_operation(
                target=str(batch.root / "graft"),
                owner_kind="directory",
                selector="whole-resource",
                kind="build-graft",
                dependents=[str(batch.root)],
            )
        )
        tampered = contracts.seal_document("manifest", payload)
        batch.manifest_path.write_bytes(contracts.canonical_json_bytes(tampered))
        before = _tree_bytes(batch.root)
        output_path = batch.evidence / "rejected.json"
        with self.assertRaises(contracts.ContractError) as failure:
            _reconcile(batch, output_path)
        self.assertEqual(failure.exception.code, "unsupported-in-rc.3")
        self.assertFalse(output_path.exists())
        self.assertEqual(_tree_bytes(batch.root), before)

    def test_evidence_paths_reserved_from_sealed_omp_inputs(self):
        batch = _OmpBatch(self, manifest_in_agent_dir=True)
        inputs = {
            reference["path"]: reference["state"]
            for reference in contracts._manifest_input_references(batch.manifest["payload"])
        }
        present = next(
            Path(path) for path, state in inputs.items() if state["type"] == "file"
        )
        output_path = batch.agent / "current-state-evidence.json"
        agent_before = _tree_bytes(batch.agent)
        with (
            self.assertRaises(contracts.ContractError) as failure,
            mock.patch.dict(os.environ, batch.environment),
        ):
            reconcile_deployment(
                batch.manifest_path,
                batch.apply_path,
                batch.missing_path,
                present,
                confirmed=True,
            )
        self.assertEqual(failure.exception.code, "private-scope")
        self.assertEqual(_tree_bytes(batch.agent), agent_before)
        self.assertFalse(output_path.exists())

    def test_apply_only_target_drift_fails_closed(self):
        batch = _OmpBatch(self)
        operation = _apply_only_operation(batch.manifest)
        target = Path(operation["target"])
        after = _stage_results(batch.apply_path)[operation["resource_id"]]["after"]
        _drift_target(target, after)
        drifted = snapshot(target)
        output_path = batch.evidence / "current-state-evidence.json"
        with self.assertRaises(contracts.ContractError) as failure:
            _reconcile(batch, output_path)
        self.assertEqual(failure.exception.code, "state-conflict")
        self.assertFalse(output_path.exists())
        self.assertEqual(snapshot(target), drifted)


if __name__ == "__main__":
    unittest.main()
