"""Approved project AGENTS deployment fidelity.

A signature-approved project routing candidate holds the exact native pause
block, one formatting blank line, then the user's unique rule body. Apply
copies that candidate verbatim. Deploy writes the pause-stripped body after
preflight. The selector is ``approved-agents:<sha256>`` of that body. The
sealed source is the signed candidate, not a vault copy.
"""

from __future__ import annotations

import base64
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
from onboard import GLOBAL_AGENTS_TEMPLATE
from onboard_contracts import ContractError, canonical_json_bytes
from sbtd_deployment import execute_migration_deployment, load_deployment_context
from sbtd_migration import apply_migration, runtime_versions
from sbtd_migration_files import read_file, save_document, snapshot
from sbtd_migration_plan import plan_migration
from sbtd_migration_verify import verify_migration
from sbtd_recovery import apply_recovery, plan_recovery

from tests.test_sbtd_migration_apply import legacy_project

_PAUSE_ASSET = SCRIPTS.parents[0] / "assets" / "migration-paused-agents.txt"
_PROJECT_TEMPLATE = SCRIPTS.parents[0] / "templates" / "agents" / "AGENTS.project.md"

# Unique user rule bytes: no template, pause asset, or fence body carries
# this text, so its byte-exact survival is observable end to end.
_UNIQUE_BODY = (
    "# 项目自定义规则\n"
    "\n"
    "unique-user-rule-bytes-5f3c9a71：此段为用户独有规则，部署后必须逐字节保留。\n"
    "- 规则一：先运行项目自带检查，再回答代码问题。\n"
    "- 规则二：禁止覆盖 docs/owned/ 下的手写文档。\n"
).encode()

# Distinct approved body for the codex-global routing target.
_GLOBAL_BODY = b"# Approved global routing\n\nunique-global-rule-bytes-8e2b4c\n"

_TEST_APPROVAL_KEY = None
_TEST_KEY_PATCH = None


def setUpModule():
    global _TEST_APPROVAL_KEY, _TEST_KEY_PATCH
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    _TEST_APPROVAL_KEY = Ed25519PrivateKey.generate()
    _TEST_KEY_PATCH = mock.patch(
        "sbtd_migration_plan._routing_approval_public_key",
        return_value=_TEST_APPROVAL_KEY.public_key(),
    )
    _TEST_KEY_PATCH.start()


def tearDownModule():
    if _TEST_KEY_PATCH is not None:
        _TEST_KEY_PATCH.stop()


def _sign_existing_approval(path):
    document = json.loads(path.read_bytes())
    payload = contracts.canonical_json_bytes(
        {"schema_version": document["schema_version"], "items": document["items"]}
    )
    document["signature"] = base64.b64encode(
        _TEST_APPROVAL_KEY.sign(payload)
    ).decode("ascii")
    path.write_bytes(json.dumps(document).encode("utf-8"))
    return path


def _file_state(raw):
    return {"type": "file", "checksum": hashlib.sha256(raw).hexdigest()}


class _SignedBatch:
    """One signed batch whose live routing target holds foreign bytes.

    The approved candidate is the exact native pause block, one formatting
    blank line, then the unique body; the live pre-approval file keeps
    unrelated foreign bytes so every phase transition is observable. With
    the default demo-project role the signed target is the project root
    AGENTS.md; with codex-global it is the Codex HOME AGENTS.md, matching
    the existing global-signed successor fixtures.
    """

    def __init__(self, base, *, body=_UNIQUE_BODY, role="demo-project"):
        self.base = base
        self.root = legacy_project(base, "project")
        self.foreign = (self.root / "AGENTS.md").read_bytes()
        self.home = base / "home"
        self.vault = base / "vault"
        self.evidence = base / "evidence"
        for path in (self.home, self.vault, self.evidence):
            path.mkdir(mode=0o700)
        self.environment = {
            "HOME": str(self.home),
            "USERPROFILE": str(self.home),
            "CODEX_HOME": str(self.home / ".codex"),
            "AGENT_SKILLS_DIR": str(self.home / ".agent/skills"),
        }
        self.agents = self.root / "AGENTS.md"
        self.role = role
        if role == "codex-global":
            self.approved = self.home / ".codex" / "AGENTS.md"
            self.approved.parent.mkdir(parents=True)
            self.approved.write_bytes(b"custom trellis global routing\n")
        else:
            self.approved = self.agents
        self.body = body
        self.paused = _PAUSE_ASSET.read_bytes() + b"\n" + body
        self.candidate = self.vault / "routing-candidate.md"
        self.candidate.write_bytes(self.paused)
        self.approval = self.vault / "routing-approvals.json"
        self.approval.write_bytes(
            json.dumps(
                {
                    "schema_version": 1,
                    "items": [
                        {
                            "role": role,
                            "target_path": str(self.approved),
                            "before": snapshot(self.approved),
                            "candidate_ref": {
                                "path": str(self.candidate),
                                "state": snapshot(self.candidate),
                            },
                            "basis": "fixture custodian approval",
                        }
                    ],
                }
            ).encode("utf-8")
        )
        _sign_existing_approval(self.approval)
        self.projection = body

    def plan(self, **kwargs):
        with mock.patch.dict(os.environ, self.environment):
            return plan_migration(
                [self.root],
                self.vault,
                "fixture",
                None,
                tool_versions=runtime_versions(),
                routing_approvals=self.approval,
                **kwargs,
            )

    def apply(self, manifest_path, **kwargs):
        with mock.patch.dict(os.environ, self.environment):
            applied, code = apply_migration(manifest_path, confirmed=True, **kwargs)
        if code != 0:
            raise AssertionError(f"fixture apply failed: {applied}")
        receipt = applied["migration"]["apply_receipt"]
        return receipt, self.evidence / ("apply-" + receipt["apply_id"] + ".json")

    def execute(
        self,
        manifest_path,
        apply_path,
        output_path,
        *,
        previous_path=None,
        block_shared_home=False,
    ):
        """Real load_deployment_context + execute_migration_deployment."""
        patches = []
        if block_shared_home:
            original_mkdir = Path.mkdir
            shared_home = self.home / ".codex"

            def deny_shared_home(path, *args, **kwargs):
                if path == shared_home:
                    raise PermissionError("synthetic shared scope failure")
                return original_mkdir(path, *args, **kwargs)

            patches.append(mock.patch.object(Path, "mkdir", deny_shared_home))
        with mock.patch.dict(os.environ, self.environment):
            context = load_deployment_context(
                manifest_path,
                apply_path,
                output_path,
                previous_path=previous_path,
                mode="init",
                roots=[self.root],
                hooks_authorized=False,
            )
            for patch in patches:
                patch.start()
            try:
                return execute_migration_deployment(context)
            finally:
                for patch in reversed(patches):
                    patch.stop()

    def write_manifest(self, manifest, name):
        path = self.evidence / name
        path.write_bytes(canonical_json_bytes(manifest))
        return path


def _assert_projected_agents(case, agents, projection, body):
    """Deployed bytes are the pause-stripped approved body. No fence."""
    raw = agents.read_bytes()
    case.assertEqual(raw, projection)
    case.assertEqual(raw, body)
    case.assertNotIn(_PAUSE_ASSET.read_bytes(), raw)
    case.assertNotIn(b"<!-- graft:start -->", raw)
    case.assertEqual(snapshot(agents), _file_state(projection))


def _assert_real_smoke(case, result):
    """Success needs real sealed reports. An empty receipt is not acceptance."""
    payload = result["deploymentEvidence"]["evidence"]["payload"]
    case.assertEqual(payload["status"], "succeeded")
    case.assertTrue(payload["projects"])
    for project in payload["projects"]:
        refs = project["report_refs"]
        case.assertTrue(refs, project["root"])
        for ref in refs:
            path = Path(ref["path"])
            case.assertTrue(path.is_file(), path)
            case.assertGreater(path.stat().st_size, 0, path)


def _assert_verified(case, manifest_path, apply_path, deployment_path):
    verified, code = verify_migration(manifest_path, apply_path, deployment_path)
    case.assertEqual((code, verified["status"]), (0, "verified"), verified)


class ApprovedAgentsDeploymentTests(unittest.TestCase):
    def test_signed_original_deploy_preserves_approved_body_through_verify(self):
        with tempfile.TemporaryDirectory() as directory:
            batch = _SignedBatch(Path(directory).resolve())
            manifest = batch.plan(deployment_mode="init")
            routing = [
                operation
                for operation in manifest["payload"]["projects"][0][
                    "private_operations"
                ]
                if operation["selector"] == "approved-routing-replacement"
            ]
            self.assertEqual(len(routing), 1)
            from sbtd_deployment import approved_agents_selector

            deployed = [
                operation
                for operation in manifest["payload"]["projects"][0]["private_operations"]
                if isinstance(operation.get("selector"), str)
                and operation["selector"].startswith("approved-agents:")
            ]
            self.assertEqual(len(deployed), 1)
            self.assertEqual(
                deployed[0]["selector"], approved_agents_selector(batch.body)
            )
            self.assertEqual(deployed[0]["change"]["kind"], "ensure-file-block")
            self.assertEqual(
                deployed[0]["change"]["source_ref"]["path"], str(batch.candidate)
            )
            self.assertEqual(
                deployed[0]["ownership"]["reference"],
                deployed[0]["change"]["source_ref"],
            )
            self.assertFalse((batch.vault / "approved-agents").exists())
            manifest_path = batch.write_manifest(manifest, "manifest.json")
            _receipt, apply_path = batch.apply(
                manifest_path, routing_approvals=batch.approval
            )
            self.assertEqual(batch.agents.read_bytes(), batch.paused)

            deployment_path = batch.evidence / "deployment.json"
            result, code = batch.execute(manifest_path, apply_path, deployment_path)
            self.assertEqual(code, 0, result)
            _assert_real_smoke(self, result)
            _assert_projected_agents(self, batch.agents, batch.projection, batch.body)
            resource = contracts.resource_id("markdown", str(batch.agents))
            outcomes = {
                item["resource_id"]: item for item in result["operationResults"]
            }
            self.assertEqual(outcomes[resource]["status"], "succeeded")
            self.assertEqual(outcomes[resource]["before"], _file_state(batch.paused))
            self.assertEqual(outcomes[resource]["after"], _file_state(batch.projection))

            with mock.patch.dict(os.environ, batch.environment):
                _assert_verified(self, manifest_path, apply_path, deployment_path)

    def test_signed_original_deploy_retry_preserves_body_and_recovers_raw(self):
        with tempfile.TemporaryDirectory() as directory:
            batch = _SignedBatch(Path(directory).resolve())
            manifest = batch.plan(deployment_mode="init")
            manifest_path = batch.write_manifest(manifest, "manifest.json")
            _receipt, apply_path = batch.apply(
                manifest_path, routing_approvals=batch.approval
            )

            blocked_path = batch.evidence / "deployment-blocked.json"
            blocked, blocked_code = batch.execute(
                manifest_path,
                apply_path,
                blocked_path,
                block_shared_home=True,
            )
            self.assertEqual(blocked_code, 2, blocked)
            self.assertEqual(
                blocked["deploymentEvidence"]["evidence"]["payload"]["status"],
                "blocked",
            )
            # The project AGENTS write completed before the shared scope
            # failure; its rendered outcome is already the exact projection.
            _assert_projected_agents(self, batch.agents, batch.projection, batch.body)

            # Recovery inverts each proven phase from its raw retained
            # original: deploy restores the paused candidate, apply restores
            # the foreign pre-approval bytes. No semantic stripping replays.
            with mock.patch.dict(os.environ, batch.environment):
                planned, plan_code = plan_recovery(
                    manifest_path,
                    apply_receipt_path=apply_path,
                    deployment_evidence_path=blocked_path,
                )
            self.assertEqual(plan_code, 0, planned)
            plan = planned["recovery"]["plan"]
            plan_path = batch.evidence / "recovery-plan.json"
            save_document(plan_path, plan, private_root=batch.evidence)
            with mock.patch.dict(os.environ, batch.environment):
                restored, recovery_code = apply_recovery(
                    plan_path, confirm_recovery=plan["plan_id"]
                )
            self.assertEqual(recovery_code, 0, restored)
            self.assertEqual(batch.agents.read_bytes(), batch.foreign)

            # A redeploy straight after recovery must refuse drift: the
            # complete apply receipt proves a paused candidate that the
            # recovery just restored to pre-apply bytes, so the deployment
            # precondition fails closed without writing anything.
            with (
                mock.patch.dict(os.environ, batch.environment),
                self.assertRaises(ContractError) as drifted,
            ):
                load_deployment_context(
                    manifest_path,
                    apply_path,
                    batch.evidence / "deployment.json",
                    previous_path=None,
                    mode="init",
                    roots=[batch.root],
                    hooks_authorized=False,
                )
            self.assertEqual(drifted.exception.code, "state-conflict")
            self.assertEqual(batch.agents.read_bytes(), batch.foreign)
            self.assertFalse((batch.evidence / "deployment.json").exists())

    def test_signed_original_deploy_retry_after_blocked_stays_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            batch = _SignedBatch(Path(directory).resolve())
            manifest = batch.plan(deployment_mode="init")
            manifest_path = batch.write_manifest(manifest, "manifest.json")
            _receipt, apply_path = batch.apply(
                manifest_path, routing_approvals=batch.approval
            )
            blocked_path = batch.evidence / "deployment-blocked.json"
            blocked, blocked_code = batch.execute(
                manifest_path,
                apply_path,
                blocked_path,
                block_shared_home=True,
            )
            self.assertEqual(blocked_code, 2, blocked)

            # Retry from the blocked evidence: preflight re-renders the
            # already-succeeded AGENTS operation from its approved base (the
            # live bytes no longer carry the pause block), completed graph
            # build is not replayed, and the write set stays byte-identical.
            retry_path = batch.evidence / "deployment.json"
            result, code = batch.execute(
                manifest_path,
                apply_path,
                retry_path,
                previous_path=blocked_path,

            )
            self.assertEqual(code, 0, result)
            _assert_real_smoke(self, result)
            _assert_projected_agents(self, batch.agents, batch.projection, batch.body)
            with mock.patch.dict(os.environ, batch.environment):
                _assert_verified(self, manifest_path, apply_path, retry_path)

    def test_signed_successor_deploy_preserves_approved_body_through_verify(self):
        with tempfile.TemporaryDirectory() as directory:
            batch = _SignedBatch(Path(directory).resolve())
            original = batch.plan()
            self.assertIsNone(original["payload"]["deployment"])
            original_path = batch.write_manifest(original, "original-manifest.json")
            _receipt, apply_path = batch.apply(
                original_path, routing_approvals=batch.approval
            )
            self.assertEqual(batch.agents.read_bytes(), batch.paused)

            with mock.patch.dict(os.environ, batch.environment):
                successor = plan_migration(
                    [batch.root],
                    batch.vault,
                    "fixture",
                    None,
                    tool_versions=runtime_versions(),
                    deployment_mode="init",
                    successor_manifest=original_path,
                    successor_apply_receipt=apply_path,
                )
            self.assertIsNone(successor["payload"]["routing_approvals"])
            self.assertFalse(
                any(
                    operation["selector"] == "approved-routing-replacement"
                    for project in successor["payload"]["projects"]
                    for operation in project["private_operations"]
                )
            )
            successor_path = batch.write_manifest(successor, "successor-manifest.json")
            _successor_receipt, successor_apply_path = batch.apply(
                successor_path, no_routing_approvals=True
            )

            deployment_path = batch.evidence / "successor-deployment.json"
            result, code = batch.execute(
                successor_path, successor_apply_path, deployment_path
            )
            self.assertEqual(code, 0, result)
            _assert_real_smoke(self, result)
            _assert_projected_agents(self, batch.agents, batch.projection, batch.body)
            with mock.patch.dict(os.environ, batch.environment):
                _assert_verified(
                    self, successor_path, successor_apply_path, deployment_path
                )

    def test_successor_global_replacement_deploys_template_and_verifies(self):
        with tempfile.TemporaryDirectory() as directory:
            batch = _SignedBatch(
                Path(directory).resolve(), body=_GLOBAL_BODY, role="codex-global"
            )
            original = batch.plan()
            self.assertIsNone(original["payload"]["deployment"])
            shared_replacements = [
                operation
                for operation in original["payload"]["shared_operations"]
                if operation["selector"] == "approved-routing-replacement"
            ]
            self.assertEqual(len(shared_replacements), 1)
            original_path = batch.write_manifest(original, "original-manifest.json")
            _receipt, apply_path = batch.apply(
                original_path, routing_approvals=batch.approval
            )
            self.assertEqual(batch.approved.read_bytes(), batch.paused)

            with mock.patch.dict(os.environ, batch.environment):
                successor = plan_migration(
                    [batch.root],
                    batch.vault,
                    "fixture",
                    None,
                    tool_versions=runtime_versions(),
                    deployment_mode="init",
                    successor_manifest=original_path,
                    successor_apply_receipt=apply_path,
                )
            successor_path = batch.write_manifest(successor, "successor-manifest.json")
            _successor_receipt, successor_apply_path = batch.apply(
                successor_path, no_routing_approvals=True
            )
            project_after_apply = batch.agents.read_bytes()

            deployment_path = batch.evidence / "successor-deployment.json"
            result, code = batch.execute(
                successor_path, successor_apply_path, deployment_path
            )
            self.assertEqual(code, 0, result)
            _assert_real_smoke(self, result)
            global_template = read_file(GLOBAL_AGENTS_TEMPLATE)
            self.assertEqual(batch.approved.read_bytes(), global_template)
            self.assertNotEqual(batch.approved.read_bytes(), batch.paused)
            self.assertEqual(batch.agents.read_bytes(), project_after_apply)
            self.assertNotIn(b"<!-- graft:start -->", batch.agents.read_bytes())
            with mock.patch.dict(os.environ, batch.environment):
                _assert_verified(
                    self, successor_path, successor_apply_path, deployment_path
                )

    def test_drifted_approved_candidate_refuses_deploy_without_touching_agents(self):
        with tempfile.TemporaryDirectory() as directory:
            batch = _SignedBatch(Path(directory).resolve())
            manifest = batch.plan(deployment_mode="init")
            manifest_path = batch.write_manifest(manifest, "manifest.json")
            _receipt, apply_path = batch.apply(
                manifest_path, routing_approvals=batch.approval
            )
            paused = batch.agents.read_bytes()
            batch.candidate.write_bytes(
                _PAUSE_ASSET.read_bytes() + b"\ntampered after approval\n"
            )
            with (
                mock.patch.dict(os.environ, batch.environment),
                self.assertRaises(ContractError) as failure,
            ):
                load_deployment_context(
                    manifest_path,
                    apply_path,
                    batch.evidence / "deployment.json",
                    previous_path=None,
                    mode="init",
                    roots=[batch.root],
                    hooks_authorized=False,
                )
            self.assertEqual(failure.exception.code, "state-conflict")
            self.assertEqual(batch.agents.read_bytes(), paused)
            self.assertFalse((batch.evidence / "deployment.json").exists())

    def test_candidate_drift_after_context_refuses_all_deployment_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            batch = _SignedBatch(Path(directory).resolve())
            manifest_path = batch.write_manifest(batch.plan(deployment_mode="init"), "manifest.json")
            _receipt, apply_path = batch.apply(manifest_path, routing_approvals=batch.approval)
            output = batch.evidence / "deployment.json"
            with mock.patch.dict(os.environ, batch.environment):
                context = load_deployment_context(
                    manifest_path, apply_path, output, previous_path=None,
                    mode="init", roots=[batch.root], hooks_authorized=False,
                )
                batch.candidate.write_bytes(batch.paused + b"\nChanged after loading.\n")
                before = snapshot(batch.base)
                with self.assertRaises(ContractError) as failure:
                    execute_migration_deployment(context)
            self.assertEqual(failure.exception.code, "state-conflict")
            self.assertEqual(snapshot(batch.base), before)
            self.assertFalse(output.exists())

    def test_resealed_zero_write_successor_cannot_drop_signed_project_deployment(self):
        with tempfile.TemporaryDirectory() as directory:
            batch = _SignedBatch(Path(directory).resolve())
            original_path = batch.write_manifest(batch.plan(), "original-manifest.json")
            _receipt, apply_path = batch.apply(original_path, routing_approvals=batch.approval)
            with mock.patch.dict(os.environ, batch.environment):
                successor = plan_migration(
                    [batch.root], batch.vault, "fixture", None, tool_versions=runtime_versions(),
                    deployment_mode="init-projects", successor_manifest=original_path,
                    successor_apply_receipt=apply_path,
                )
                payload = json.loads(canonical_json_bytes(successor))["payload"]
                project = payload["projects"][0]
                self.assertEqual(sum(op["phase"] == "deploy" for op in project["private_operations"]), 1)
                project["private_operations"] = [
                    op for op in project["private_operations"] if op["phase"] != "deploy"
                ]
                tampered = contracts.seal_document("manifest", payload)
                path = batch.write_manifest(tampered, "dropped-project-deploy.json")
                before = snapshot(batch.base)
                with self.assertRaises(ContractError) as failure:
                    apply_migration(path, confirmed=True, no_routing_approvals=True)
            self.assertEqual(failure.exception.code, "semantic-violation")
            self.assertEqual(snapshot(batch.base), before)
            self.assertEqual(batch.agents.read_bytes(), batch.paused)

    def test_successor_deploy_refuses_drifted_predecessor_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            batch = _SignedBatch(Path(directory).resolve())
            original = batch.plan()
            original_path = batch.write_manifest(original, "original-manifest.json")
            _receipt, apply_path = batch.apply(
                original_path, routing_approvals=batch.approval
            )
            with mock.patch.dict(os.environ, batch.environment):
                successor = plan_migration(
                    [batch.root],
                    batch.vault,
                    "fixture",
                    None,
                    tool_versions=runtime_versions(),
                    deployment_mode="init",
                    successor_manifest=original_path,
                    successor_apply_receipt=apply_path,
                )
            successor_path = batch.write_manifest(successor, "successor-manifest.json")
            _successor_receipt, successor_apply_path = batch.apply(
                successor_path, no_routing_approvals=True
            )
            paused = batch.agents.read_bytes()
            # The successor manifest names no candidate itself; only the
            # re-proved predecessor signed set can refuse this drift.
            batch.candidate.write_bytes(
                _PAUSE_ASSET.read_bytes() + b"\ntampered after approval\n"
            )
            with (
                mock.patch.dict(os.environ, batch.environment),
                self.assertRaises(ContractError) as failure,
            ):
                context = load_deployment_context(
                    successor_path,
                    successor_apply_path,
                    batch.evidence / "successor-deployment.json",
                    previous_path=None,
                    mode="init",
                    roots=[batch.root],
                    hooks_authorized=False,
                )
                execute_migration_deployment(context)
            self.assertEqual(failure.exception.code, "state-conflict")
            self.assertEqual(batch.agents.read_bytes(), paused)
            self.assertFalse(
                (batch.evidence / "successor-deployment.json").exists()
            )

    def test_ordinary_init_deploy_preserves_foreign_project_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            batch = _SignedBatch(Path(directory).resolve())
            with mock.patch.dict(os.environ, batch.environment):
                manifest = plan_migration(
                    [batch.root],
                    batch.vault,
                    "fixture",
                    None,
                    tool_versions=runtime_versions(),
                    deployment_mode="init",
                )
            self.assertFalse(
                any(
                    operation["selector"] == "approved-routing-replacement"
                    for project in manifest["payload"]["projects"]
                    for operation in project["private_operations"]
                )
            )
            manifest_path = batch.write_manifest(manifest, "manifest.json")
            _receipt, apply_path = batch.apply(
                manifest_path, no_routing_approvals=True
            )
            self.assertEqual(batch.agents.read_bytes(), batch.foreign)

            deployment_path = batch.evidence / "deployment.json"
            result, code = batch.execute(manifest_path, apply_path, deployment_path)
            self.assertEqual(code, 0, result)
            _assert_real_smoke(self, result)
            raw = batch.agents.read_bytes()
            self.assertEqual(raw, batch.foreign)
            self.assertNotEqual(raw, read_file(_PROJECT_TEMPLATE))
            self.assertNotIn(b"<!-- graft:start -->", raw)
            self.assertNotIn(_UNIQUE_BODY, raw)


if __name__ == "__main__":
    unittest.main()
