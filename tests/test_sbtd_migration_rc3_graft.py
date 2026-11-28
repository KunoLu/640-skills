"""rc.3 migration: exact lineage hop, D7 rows, no write authority.

The measured rc.2 onboard hash is not the installed signed predecessor or
successor. These tests do not sign or replace the release lineage pair.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import stat
import sys
import tempfile
import unittest
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from onboard_contracts import (
    ARCHIVED_GRAFT_PIN,
    ContractError,
    archived_graft_policy,
    canonical_json_bytes,
    operation_id,
    resource_id,
    seal_document,
)
from sbtd_deployment import legacy_graft_operations, reject_legacy_execution
from sbtd_migration import (
    _CURRENT_RUNTIME_FILES,
    _HISTORICAL_RUNTIME_FILES,
    _lineage_signed_bytes,
    historical_lineage_grants_verify,
    runtime_versions,
)
from sbtd_migration_files import snapshot
from sbtd_migration_verify import validate_deployment_reports, verify_migration

# Measured from the rc.2 tag with declared dependencies. Not an allowlist.
RC2_ONBOARD = (
    "runtime-sha256:5ce6943c6726af61b1bbcb2d784cac15a2c630dd768f0b8b22e6abff4a7cbe1c"
)


def _sign_pair(predecessor: str, successor: str) -> tuple[dict, bytes]:
    """Isolated fixture signature. Not the release key and not installed."""
    private = Ed25519PrivateKey.generate()
    document = {
        "schema_version": 1,
        "purpose": "runtime-lineage",
        "predecessor": predecessor,
        "successor": successor,
    }
    signature = private.sign(_lineage_signed_bytes(predecessor, successor))
    document["signature"] = base64.b64encode(signature).decode("ascii")
    public = private.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    return document, public


class LineageHopTests(unittest.TestCase):
    def test_exact_predecessor_to_current_successor_is_allowed(self):
        current = "runtime-sha256:" + "ab" * 32
        sealed = "runtime-sha256:" + "cd" * 32
        pair, _public = _sign_pair(sealed, current)
        self.assertTrue(historical_lineage_grants_verify(sealed, current, pair))

    def test_wrong_successor_and_set_membership_are_rejected(self):
        current = "runtime-sha256:" + "11" * 32
        sealed = "runtime-sha256:" + "22" * 32
        other = "runtime-sha256:" + "33" * 32
        wrong, _public = _sign_pair(sealed, other)
        self.assertFalse(historical_lineage_grants_verify(sealed, current, wrong))
        unrelated, _public = _sign_pair(other, current)
        self.assertFalse(historical_lineage_grants_verify(sealed, current, unrelated))
        self.assertFalse(historical_lineage_grants_verify(current, current, wrong))

    def test_unsigned_pair_does_not_grant_verify(self):
        current = "runtime-sha256:" + "11" * 32
        sealed = "runtime-sha256:" + "22" * 32
        unsigned = {
            "schema_version": 1,
            "purpose": "runtime-lineage",
            "predecessor": sealed,
            "successor": current,
        }
        self.assertFalse(historical_lineage_grants_verify(sealed, current, unsigned))
        unsigned["signature"] = ""
        self.assertFalse(historical_lineage_grants_verify(sealed, current, unsigned))

    def test_measured_rc2_hash_is_not_the_installed_hop(self):
        installed = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "sbtd-workflow-onboard"
                / "assets"
                / "runtime-lineage.json"
            ).read_text()
        )
        self.assertNotEqual(RC2_ONBOARD, installed["predecessor"])
        self.assertNotEqual(RC2_ONBOARD, installed["successor"])
        self.assertFalse(
            historical_lineage_grants_verify(
                RC2_ONBOARD, runtime_versions()["onboard"], installed
            )
        )
        self.assertNotIn("assets/graft-build-policy.json", _CURRENT_RUNTIME_FILES)
        self.assertIn("scripts/sbtd_graft_deployment.py", _HISTORICAL_RUNTIME_FILES)


class NewPlanTests(unittest.TestCase):
    def test_new_plan_declares_no_graft_operations(self):
        from sbtd_migration_plan import plan_migration
        from tests.test_sbtd_migration_apply import legacy_project

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = legacy_project(base, "fresh")
            home, vault = base / "home", base / "vault"
            home.mkdir(mode=0o700)
            vault.mkdir(mode=0o700)
            environment = {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "CODEX_HOME": str(home / ".codex"),
                "AGENT_SKILLS_DIR": str(home / ".agent/skills"),
            }
            with mock.patch.dict(os.environ, environment):
                manifest = plan_migration(
                    [root], vault, "fixture-custodian", None, tool_versions=runtime_versions()
                )
            self.assertEqual(legacy_graft_operations(manifest["payload"]), [])

    def test_legacy_execution_refuses_before_write(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "config.toml"
            target.write_bytes(b"before\n")
            before = target.read_bytes()
            mode = stat.S_IMODE(target.stat().st_mode)
            with self.assertRaises(ContractError) as raised:
                reject_legacy_execution(
                    {
                        "projects": [
                            {
                                "private_operations": [
                                    {
                                        "change": {"kind": "build-graft"},
                                        "target": str(target),
                                    }
                                ]
                            }
                        ],
                        "shared_operations": [],
                    }
                )
            self.assertEqual(raised.exception.code, "unsupported-in-rc.3")
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), mode)


def _graft_operation(
    root: Path, target: Path, owner: str, selector: str, kind: str, earlier: list[dict]
) -> dict:
    policy = archived_graft_policy()
    rid = resource_id(owner, str(target))
    # rc.2 _operation chains by target to any earlier apply operation.
    requirement = (
        {"kind": "phase-after", "phase": "apply", "resource_id": rid}
        if any(operation["target"] == str(target) for operation in earlier)
        else {"kind": "state", "state": snapshot(target)}
    )
    return {
        "phase": "deploy",
        "resource_id": rid,
        "operation_id": operation_id("deploy", rid, selector),
        "owner_kind": owner,
        "target": str(target),
        "selector": selector,
        "change": {"kind": kind, "source_ref": policy},
        "ownership": {"kind": "template-source", "reference": policy},
        "before_requirement": requirement,
        "dependent_projects": [str(root)],
    }


def _iso(moment: datetime) -> str:
    return moment.astimezone().isoformat(timespec="microseconds")


def _z(moment: datetime) -> str:
    return (
        moment.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _stage_result(operation: dict, before: dict, after: dict, backup: dict | None) -> dict:
    return {
        "phase": operation["phase"],
        "resource_id": operation["resource_id"],
        "operation_ids": [operation["operation_id"]],
        "dependent_projects": list(operation["dependent_projects"]),
        "status": "succeeded",
        "backup_ref": backup,
        "before": before,
        "after": after,
        "error": None,
    }


def _mode_proof(
    private: Ed25519PrivateKey,
    deployment_id: str,
    operation: dict,
    mode: str,
    after: dict,
) -> dict:
    from sbtd_migration_verify import _mode_signed_bytes

    recorded = {"type": after["type"], "checksum": after["checksum"]}
    return {
        "kind": "signed-attestation",
        "resource_id": operation["resource_id"],
        "mode": mode,
        "after": recorded,
        "signature": base64.b64encode(
            private.sign(
                _mode_signed_bytes(deployment_id, operation["resource_id"], mode, recorded)
            )
        ).decode("ascii"),
    }


def _install_lineage(directory: Path, predecessor: str, successor: str):
    directory.mkdir(mode=0o700)
    private = Ed25519PrivateKey.generate()
    public = directory / "lineage.pub"
    public.write_bytes(
        private.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    )
    pair = directory / "lineage.json"
    pair.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "purpose": "runtime-lineage",
                "predecessor": predecessor,
                "successor": successor,
                "signature": base64.b64encode(
                    private.sign(_lineage_signed_bytes(predecessor, successor))
                ).decode("ascii"),
            }
        )
    )
    return private, public, pair


def _smoke_refs(evidence: Path, root: Path, started: str, finished: str) -> list[dict]:
    report = evidence / f"smoke-{root.name}.json"
    summary = evidence / f"smoke-{root.name}.md"
    summary.write_text("合成契约夹具；不证明真实host部署。\n")
    report.write_text(
        json.dumps(
            {
                "repositoryKey": "fixture/project",
                "projectRoot": str(root),
                "sourceRef": "non-git",
                "sourceCommit": None,
                "worktreeState": "unknown",
                "sourceRevision": "unknown",
                "evidenceSource": "developer-local",
                "trigger": "manual",
                "environmentAlignment": "verified",
                "evidencePublication": "local-only",
                "e2eMode": "smoke-only",
                "mockStrategy": "none",
                "startedAt": started,
                "finishedAt": finished,
                "command": ["fixture"],
                "stdout": "synthetic contract data",
                "stderr": "",
                "exitCode": 0,
                "timedOut": False,
            }
        )
    )
    evidence_path = evidence / f"smoke-{root.name}.evidence.json"
    evidence_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "runId": "fixture-smoke",
                "createdAt": finished,
                "evidenceSource": "developer-local",
                "trigger": "manual",
                "repository": {
                    "repositoryKey": "fixture/project",
                    "sourceRef": "non-git",
                    "sourceCommit": None,
                    "worktreeState": "unknown",
                },
                "sourceRevision": "unknown",
                "environmentAlignment": "verified",
                "e2eMode": "smoke-only",
                "mockStrategy": "none",
                "featureSources": [],
                "reports": [
                    {
                        "testType": "api",
                        "path": str(report),
                        "summaryMd": str(summary),
                        "sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
                        "status": "passed",
                        "mode": "smoke-only",
                    }
                ],
                "evidencePublication": "local-only",
                "secretsRedacted": True,
            }
        )
    )
    return [
        {"path": str(path), "state": snapshot(path)}
        for path in (evidence_path, report, summary)
    ]


def build_completed_historical(
    base: Path,
    *,
    predecessor: str | None = None,
    drift: bool = True,
    signed_route: bool = False,
) -> dict:
    """Model a completed rc.2 deployment without running Graft."""
    import sbtd_migration_plan as migration_plan
    from sbtd_migration import (
        _apply_projects,
        _apply_resource,
        _backup_sources,
        _groups,
        _prepare_backup_parent,
    )
    from sbtd_migration_files import backup_reference
    from tests.test_sbtd_migration_apply import legacy_project

    roots = [legacy_project(base, name) for name in ("alpha", "beta")]
    agents = roots[0] / "AGENTS.md"
    hashes_path = roots[0] / ".trellis/.template-hashes.json"
    hashes = json.loads(hashes_path.read_bytes())
    hashes["hashes"]["AGENTS.md"] = hashlib.sha256(agents.read_bytes()).hexdigest()
    hashes_path.write_bytes(canonical_json_bytes(hashes))
    home, vault, evidence = (base / name for name in ("home", "vault", "evidence"))
    for path in (home, vault, evidence):
        path.mkdir(mode=0o700)
    environment = {
        "HOME": str(home),
        "USERPROFILE": str(home),
        "CODEX_HOME": str(home / ".codex"),
        "AGENT_SKILLS_DIR": str(home / ".agent/skills"),
    }
    successor = runtime_versions()["onboard"]
    if predecessor is None:
        predecessor = "runtime-sha256:" + hashlib.sha256(b"rc2-historical-fixture").hexdigest()
    private, public, pair = _install_lineage(base / "trust", predecessor, successor)
    approval = None
    routing_public = None
    if signed_route:
        routing_key = Ed25519PrivateKey.generate()
        routing_public = public.parent / "routing.pub"
        routing_public.write_bytes(
            routing_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        )
        target = home / ".codex/AGENTS.md"
        target.parent.mkdir()
        target.write_bytes(b"Legacy global routing.\n")
        candidate = vault / "routing-candidate.md"
        pause = (SCRIPTS.parent / "assets/migration-paused-agents.txt").read_bytes()
        candidate.write_bytes(pause + b"\nApproved body.\n")
        routing = {
            "schema_version": 1,
            "items": [{
                "role": "codex-global",
                "target_path": str(target),
                "before": snapshot(target),
                "candidate_ref": {"path": str(candidate), "state": snapshot(candidate)},
                "basis": "fixture custodian approval",
            }],
        }
        routing["signature"] = base64.b64encode(
            routing_key.sign(canonical_json_bytes(routing))
        ).decode("ascii")
        approval = vault / "routing-approval.json"
        approval.write_bytes(canonical_json_bytes(routing))
    with (
        mock.patch.dict(os.environ, environment),
        mock.patch.object(migration_plan, "_ROUTING_APPROVAL_PUBLIC_KEY", routing_public)
        if routing_public is not None else nullcontext(),
    ):
        manifest = migration_plan.plan_migration(
            roots, vault, "fixture-custodian", None, tool_versions=runtime_versions(),
            routing_approvals=approval,
        )
    payload = manifest["payload"]
    created = datetime.now(timezone.utc) - timedelta(minutes=2)
    payload["created_at"] = _iso(created)
    payload["tool_versions"] = {"onboard": predecessor, "graft": ARCHIVED_GRAFT_PIN}
    payload["deployment"] = {"mode": "init-projects", "platform": "codex", "inputs": []}
    graft_ops: dict[str, list[dict]] = {}
    for project in payload["projects"]:
        if project.get("agents_no_touch") is not None:
            raise AssertionError("fixture AGENTS.md must not be an untouched template")
        root = Path(project["root"])
        earlier = project["private_operations"]
        operations = [
            _graft_operation(
                root, root / "graft", "directory", "whole-resource", "build-graft", earlier
            ),
            _graft_operation(
                root, root / "AGENTS.md", "markdown", "graft-agents", "configure-graft", earlier
            ),
        ]
        project["private_operations"].extend(operations)
        graft_ops[str(root)] = operations
    sealed = seal_document("manifest", payload)
    manifest_path = evidence / "manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(sealed))
    with mock.patch.dict(os.environ, environment):
        _backup_sources(sealed)
        applied = {}
        for group in _groups(sealed, "apply"):
            result, code = _apply_resource(sealed, group, previous=None)
            if code or result["status"] != "succeeded":
                raise AssertionError(f"fixture apply failed: {result}")
            applied[result["resource_id"]] = result
    apply_projects = _apply_projects(sealed, applied, None, None, originals_ready=True)
    manifest_id = sealed["manifest_id"]

    deploy_projects = []
    proof_specs = []
    report_started = _z(created + timedelta(seconds=18))
    report_finished = _z(created + timedelta(seconds=20))
    for project in sealed["payload"]["projects"]:
        root = Path(project["root"])
        graph = root / "graft"
        graph.mkdir()
        (graph / "INDEX.md").write_bytes(b"graph\n")
        deploy_results = []
        for operation in graft_ops[str(root)]:
            target = Path(operation["target"])
            requirement = operation["before_requirement"]
            before = (
                applied[operation["resource_id"]]["after"]
                if requirement["kind"] == "phase-after"
                else requirement["state"]
            )
            if operation["selector"] == "graft-agents" and snapshot(target) != before:
                raise AssertionError("fixture deployment must start at its declared predecessor")
            backup = None
            if before["type"] != "absent":
                destination = vault / manifest_id / "deploy" / operation["resource_id"]
                _prepare_backup_parent(destination, vault)
                backup = backup_reference(
                    {"path": str(target), "state": before}, destination, private_root=vault,
                )
            if operation["selector"] == "graft-agents":
                with target.open("ab") as stream:
                    stream.write(b"\n<!-- graft:start -->\nhistorical fixture\n<!-- graft:end -->\n")
                target.chmod(0o640)
            result = _stage_result(
                operation,
                before,
                snapshot(Path(operation["target"])),
                backup,
            )
            if operation["selector"] == "graft-agents":
                observed = f"{stat.S_IMODE(target.stat().st_mode):04o}"
                proof_specs.append((operation, observed, result["after"]))
            deploy_results.append(result)
        common = {
            "root": str(root),
            "source_ref": project["source_ref"],
            "head": project["head"],
            "reason": "",
            "nextStep": "",
            "shared_operation_ids": [],
        }
        deploy_projects.append(
            {
                **common,
                "status": "succeeded",
                "private_results": deploy_results,
                "report_refs": _smoke_refs(evidence, root, report_started, report_finished),
            }
        )
    apply_document = seal_document(
        "apply_receipt",
        {
            "manifest_id": manifest_id,
            "previous_receipt_id": None,
            "status": "applied",
            "projects": apply_projects,
            "shared_results": [
                applied[operation["resource_id"]]
                for operation in sealed["payload"]["shared_operations"]
                if operation["phase"] == "apply"
            ],
            "started_at": _iso(created + timedelta(seconds=5)),
            "finished_at": _iso(created + timedelta(seconds=10)),
        },
    )
    apply_path = evidence / f"apply-{apply_document['apply_id']}.json"
    apply_path.write_bytes(canonical_json_bytes(apply_document))
    deployment = seal_document(
        "deployment_evidence",
        {
            "manifest_id": manifest_id,
            "apply_id": apply_document["apply_id"],
            "previous_deployment_id": None,
            "status": "succeeded",
            "projects": deploy_projects,
            "shared_results": [],
            "started_at": _iso(created + timedelta(seconds=15)),
            "finished_at": _iso(created + timedelta(seconds=25)),
        },
    )
    deployment_path = evidence / "deployment.json"
    deployment_path.write_bytes(canonical_json_bytes(deployment))
    attestation = evidence / "post-write-attestation.json"
    attestation.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "purpose": "post-write-mode",
                "deployment_id": deployment["deployment_id"],
                "attestations": [
                    _mode_proof(
                        private, deployment["deployment_id"], operation, mode, after
                    )
                    for operation, mode, after in proof_specs
                ],
            }
        )
    )
    (vault / "untrusted-mode.txt").write_text("0640\n")
    if drift:
        (roots[1] / "AGENTS.md").chmod(0o600)
        (roots[1] / "graft" / "INDEX.md").write_bytes(b"graph\ntampered\n")
    return {
        "environment": environment,
        "manifest_path": manifest_path,
        "apply_path": apply_path,
        "deployment_path": deployment_path,
        "evidence": evidence,
        "public": public,
        "pair": pair,
        "private": private,
        "predecessor": predecessor,
        "successor": successor,
        "roots": roots,
        "routing_public": routing_public,
        "attestation": attestation,
    }


def _verify(built: dict):
    import sbtd_migration as migration
    import sbtd_migration_plan as migration_plan

    with (
        mock.patch.dict(os.environ, built["environment"]),
        mock.patch.object(migration, "_LINEAGE_PUBLIC_KEY", built["public"]),
        mock.patch.object(migration, "_LINEAGE_DOCUMENT", built["pair"]),
        mock.patch.object(migration_plan, "_ROUTING_APPROVAL_PUBLIC_KEY", built["routing_public"])
        if built["routing_public"] is not None else nullcontext(),
    ):
        return verify_migration(
            built["manifest_path"],
            built["apply_path"],
            built["deployment_path"],
            post_write_attestation=built.get("attestation"),
        )


class PublicVerifyTests(unittest.TestCase):
    def test_public_verify_records_three_states_and_does_not_authorize_writes(self):
        from sbtd_migration import cleanup_migration

        with tempfile.TemporaryDirectory() as directory:
            built = build_completed_historical(Path(directory).resolve())
            alpha, beta = built["roots"]
            manifest = json.loads(built["manifest_path"].read_bytes())
            apply = json.loads(built["apply_path"].read_bytes())
            deployment = json.loads(built["deployment_path"].read_bytes())
            operations = manifest["payload"]["projects"][0]["private_operations"]
            marker = next(op for op in operations if op["selector"] == "trellis-block")
            wiring = next(op for op in operations if op["selector"] == "graft-agents")
            rid = marker["resource_id"]
            self.assertEqual(
                wiring["before_requirement"],
                {"kind": "phase-after", "phase": "apply", "resource_id": rid},
            )
            apply_results = apply["payload"]["projects"][0]["private_results"]
            deploy_results = deployment["payload"]["projects"][0]["private_results"]
            apply_row = next(row for row in apply_results if row["resource_id"] == rid)
            deploy_row = next(row for row in deploy_results if row["resource_id"] == rid)
            self.assertNotEqual(apply_row["before"], apply_row["after"])
            self.assertEqual(deploy_row["before"], apply_row["after"])
            watched = (
                alpha / "AGENTS.md",
                alpha / "graft" / "INDEX.md",
                beta / "AGENTS.md",
                beta / "graft" / "INDEX.md",
            )
            before = {path: path.read_bytes() for path in watched}
            envelope, code = _verify(built)
            self.assertEqual(code, 3, envelope)
            self.assertEqual(envelope["status"], "failed")
            self.assertIn("do not clean up", envelope["nextStep"])
            rows = {
                row["target"]: row
                for row in envelope["migration"]["verification"]["payload"]["legacy_resources"]
            }
            alpha_rules = rows[str(alpha / "AGENTS.md")]
            if os.name == "posix":
                self.assertEqual(alpha_rules["status"], "verified")
                self.assertEqual(alpha_rules["mode_source"]["kind"], "signed-attestation")
            else:
                self.assertEqual(alpha_rules["status"], "not-verified")
                self.assertIsNone(alpha_rules["mode_source"])
            graft = rows[str(alpha / "graft")]
            self.assertEqual(graft["status"], "not-verified")
            self.assertIsNone(graft["mode_source"])
            self.assertEqual(graft["bytes"], "match")
            self.assertIn("no trusted", graft["reason"])
            self.assertEqual(rows[str(beta / "AGENTS.md")]["status"],
                             "drifted" if os.name == "posix" else "not-verified")
            self.assertEqual(rows[str(beta / "graft")]["bytes"], "differ")
            self.assertEqual(rows[str(beta / "graft")]["status"], "drifted")
            for path, raw in before.items():
                self.assertEqual(path.read_bytes(), raw)
            verification = envelope["migration"]["verification"]
            verification_path = built["evidence"] / "verification.json"
            verification_path.write_bytes(canonical_json_bytes(verification))
            with mock.patch.dict(os.environ, built["environment"]):
                with self.assertRaises(ContractError) as raised:
                    cleanup_migration(
                        built["manifest_path"],
                        built["apply_path"],
                        built["deployment_path"],
                        verification_path,
                        confirm_cleanup=verification["verification_id"],
                    )
            self.assertEqual(raised.exception.code, "unverified-input")
            with mock.patch("sbtd_migration_verify.os", wraps=os) as windows_os:
                windows_os.name = "nt"
                windows, _code = _verify(built)
            windows_rows = {
                row["target"]: row
                for row in windows["migration"]["verification"]["payload"]["legacy_resources"]
            }
            agents = windows_rows[str(alpha / "AGENTS.md")]
            self.assertEqual(agents["status"], "not-verified")
            self.assertIsNone(agents["mode_source"])
            self.assertIn("DACL", agents["reason"])
            self.assertEqual(windows_rows[str(beta / "graft")]["status"], "drifted")

    def test_equal_onboard_and_bad_lineage_fail_closed(self):
        import sbtd_migration as migration

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            current = runtime_versions()["onboard"]
            with self.assertRaises(ContractError) as equal:
                _verify(build_completed_historical(base / "equal", predecessor=current))
            self.assertEqual(equal.exception.code, "version-conflict")
            built = build_completed_historical(base / "bad")
            other = "runtime-sha256:" + "44" * 32
            documents = {
                "wrong-successor": (
                    built["predecessor"],
                    other,
                    _lineage_signed_bytes(built["predecessor"], other),
                ),
                "reversed": (
                    built["successor"],
                    built["predecessor"],
                    _lineage_signed_bytes(built["successor"], built["predecessor"]),
                ),
            }
            for name, (pred, succ, signed) in documents.items():
                built["pair"].write_text(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "purpose": "runtime-lineage",
                            "predecessor": pred,
                            "successor": succ,
                            "signature": base64.b64encode(built["private"].sign(signed)).decode("ascii"),
                        }
                    )
                )
                with self.subTest(name=name):
                    with self.assertRaises(ContractError) as failure:
                        _verify(built)
                    self.assertEqual(failure.exception.code, "version-conflict")
            unsigned = json.loads(built["pair"].read_text())
            unsigned.pop("signature", None)
            built["pair"].write_text(json.dumps(unsigned))
            with self.assertRaises(ContractError) as unsigned_error:
                _verify(built)
            self.assertEqual(unsigned_error.exception.code, "version-conflict")
            tampered = {
                "schema_version": 1,
                "purpose": "runtime-lineage",
                "predecessor": built["predecessor"],
                "successor": built["successor"],
                "signature": "A" * 88,
            }
            built["pair"].write_text(json.dumps(tampered))
            with self.assertRaises(ContractError) as tampered_error:
                _verify(built)
            self.assertEqual(tampered_error.exception.code, "version-conflict")
            with (
                mock.patch.dict(os.environ, built["environment"]),
                mock.patch.object(migration, "_LINEAGE_PUBLIC_KEY", base / "missing.pub"),
                mock.patch.object(migration, "_LINEAGE_DOCUMENT", base / "missing.json"),
                self.assertRaises(ContractError) as missing,
            ):
                verify_migration(
                    built["manifest_path"], built["apply_path"], built["deployment_path"]
                )
            self.assertEqual(missing.exception.code, "version-conflict")

    def test_failed_or_unobserved_deployment_is_not_completed(self):
        import sbtd_migration as migration

        with tempfile.TemporaryDirectory() as directory:
            built = build_completed_historical(Path(directory).resolve())
            original = json.loads(built["deployment_path"].read_text())
            for status in ("failed", "not-verified"):
                payload = json.loads(json.dumps(original["payload"]))
                payload["status"] = status
                for project in payload["projects"]:
                    project["status"] = status
                    project["reason"] = "the historical deployment was not observed to complete"
                    project["nextStep"] = "Do not treat this document as a completed deployment."
                path = built["evidence"] / f"{status}.json"
                path.write_bytes(canonical_json_bytes(seal_document("deployment_evidence", payload)))
                with (
                    mock.patch.dict(os.environ, built["environment"]),
                    mock.patch.object(migration, "_LINEAGE_PUBLIC_KEY", built["public"]),
                    mock.patch.object(migration, "_LINEAGE_DOCUMENT", built["pair"]),
                    self.assertRaises(ContractError) as raised,
                ):
                    verify_migration(built["manifest_path"], built["apply_path"], path)
                self.assertEqual(raised.exception.code, "binding-violation", status)

    def test_a_failed_report_is_not_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            built = build_completed_historical(Path(directory).resolve(), drift=False)
            alpha, beta = built["roots"]
            smoke = built["evidence"] / "smoke-alpha.json"
            native = built["evidence"] / "smoke-alpha.evidence.json"
            raw = json.loads(smoke.read_bytes())
            raw["exitCode"] = 1
            smoke.write_bytes(canonical_json_bytes(raw))
            report = json.loads(native.read_bytes())
            report["reports"][0]["sha256"] = snapshot(smoke)["checksum"]
            native.write_bytes(canonical_json_bytes(report))
            deployment = json.loads(built["deployment_path"].read_bytes())["payload"]
            project = deployment["projects"][0]
            self.assertEqual(project["root"], str(alpha))
            for reference in project["report_refs"]:
                reference["state"] = snapshot(Path(reference["path"]))
            built["deployment_path"].write_bytes(
                canonical_json_bytes(seal_document("deployment_evidence", deployment))
            )
            with self.assertRaisesRegex(
                ContractError, "an API smoke raw run did not exit cleanly"
            ) as raised:
                validate_deployment_reports(deployment, project)
            self.assertEqual(raised.exception.code, "report-acceptance")
            envelope, code = _verify(built)
            self.assertEqual(code, 3, envelope)
            self.assertEqual(envelope["status"], "failed")
            payload = envelope["migration"]["verification"]["payload"]
            self.assertEqual(
                {row["root"]: row["status"] for row in payload["projects"]},
                {str(alpha): "failed", str(beta): "not-verified"},
            )
            self.assertEqual(len(payload["legacy_resources"]), 4)

    def test_unreadable_or_unsafe_routing_keeps_other_historical_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            built = build_completed_historical(base, drift=False, signed_route=True)
            route = base / "home/.codex/AGENTS.md"
            alpha, beta = built["roots"]
            agents = alpha / "AGENTS.md"

            def check_unavailable() -> None:
                envelope, code = _verify(built)
                self.assertEqual(code, 2, envelope)
                self.assertEqual(envelope["status"], "blocked")
                payload = envelope["migration"]["verification"]["payload"]
                rows = {row["target"]: row for row in payload["legacy_resources"]}
                self.assertEqual(len(rows), 4)
                self.assertEqual(rows[str(beta / "graft")]["bytes"], "match")
                self.assertEqual(rows[str(agents)]["bytes"], "unreadable")
                self.assertEqual(rows[str(agents)]["status"], "not-verified")
                self.assertTrue(all(project["status"] == "blocked" for project in payload["projects"]))

            def unreadable(path: Path) -> dict:
                if path in {route, agents}:
                    raise ContractError("read-failed", "fixture unreadable routing")
                return snapshot(path)

            with mock.patch("sbtd_migration_verify.snapshot", side_effect=unreadable):
                check_unavailable()
            if os.name == "posix":
                from sbtd_migration import _check_stage_backups

                referent = route.with_name("unmanaged.md")
                referent.write_bytes(b"not an approved routing file\n")

                def replace_after_binding(results):
                    _check_stage_backups(results)
                    route.unlink()
                    agents.unlink()
                    route.symlink_to(referent)
                    os.mkfifo(agents)

                # Keep the referent in the declared root. Containment still
                # binds, but the late link and FIFO cannot supply state.
                with mock.patch(
                    "sbtd_migration._check_stage_backups",
                    side_effect=replace_after_binding,
                ):
                    check_unavailable()
                self.assertTrue(route.is_symlink())
                self.assertTrue(stat.S_ISFIFO(agents.lstat().st_mode))

                # A preexisting escape is not a safely bound observation.
                route.unlink()
                route.symlink_to(base / "outside-codex.md")
                with self.assertRaisesRegex(
                    ContractError, "shared target needs one declared root"
                ) as raised:
                    _verify(built)
                self.assertEqual(raised.exception.code, "semantic-violation")


if __name__ == "__main__":
    unittest.main()
