"""Historical observer authority across runtime-lineage rotation.

Regression coverage for late PR review finding 4236584337 (P2): cross-runtime
reconciled evidence produced while the installed signed pair authorized the
A→B observer must remain consumable after the installed pair rotates to B→C
under the unchanged trust key. The producer preserves the exact signed
object it was authorized by inside ``payload.reconciliation.observer_lineage``
(schema_version/purpose/predecessor/successor/signature; no trust key); the
consumer validates that embedded signature against the installed trusted key
and binds its endpoints to exactly manifest→observer, independent of the
current pair file. Legacy records without embedded proof keep the
same-runtime/current-pair fallback — and nothing more.

Fixtures run the genuine producer and read-only consumer with real Ed25519
signatures and an isolated Onboard package. The smoke subprocess sees the
same measured package files, key and pair as the producer.
"""

from __future__ import annotations

# ruff: noqa: I001 -- approved fixture imports bootstrap the local script path.

import base64
import contextlib
import dataclasses
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tests import test_sbtd_reconciliation as reconciliation
from tests.test_sbtd_reconciliation import (
    _SignedBatch,
    _interrupted_deployment,
    _reconcile,
    _reseal_deployment_evidence,
)

import onboard_contracts as contracts
import sbtd_migration as migration
from onboard_contracts import canonical_json_bytes
from sbtd_migration_files import snapshot
from sbtd_migration_verify import validate_deployment_reports, verify_migration


def setUpModule():
    reconciliation.setUpModule()


def tearDownModule():
    reconciliation.tearDownModule()


class _LineageAuthority:
    """Isolated Onboard package whose measured runtime and signed pair rotate.

    Rotation re-signs under the same installed key. Package variants change
    real measured bytes without changing the path executed by the smoke.
    """

    def __init__(self, directory: Path) -> None:
        self.package = directory / "lineage-runtime"
        shutil.copytree(
            migration._PACKAGE,
            self.package,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
        )
        self.entrypoint = self.package / "scripts" / "onboard.py"
        self._entrypoint_bytes = self.entrypoint.read_bytes()
        self._key = Ed25519PrivateKey.generate()
        self.public_path = self.package / "assets" / "runtime-lineage.pub"
        self.public_path.write_bytes(
            self._key.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
        self.pair_path = self.package / "assets" / "runtime-lineage.json"

    def use_runtime(self, stage: str) -> dict[str, str]:
        self.entrypoint.write_bytes(
            self._entrypoint_bytes + f"\n# Scoped lineage fixture: {stage}\n".encode("ascii")
        )
        return migration.runtime_versions()

    def sign(self, predecessor: str, successor: str) -> dict:
        signed = migration._lineage_signed_bytes(predecessor, successor)
        document = json.loads(signed)
        document["signature"] = base64.b64encode(self._key.sign(signed)).decode("ascii")
        return document

    def install(self, predecessor: str, successor: str) -> dict:
        document = self.sign(predecessor, successor)
        self.pair_path.write_bytes(canonical_json_bytes(document))
        return document


@contextlib.contextmanager
def _installed(authority: _LineageAuthority):
    """Select one on-disk package for both producer and smoke subprocess."""
    import onboard

    project_template = onboard.PROJECT_AGENTS_TEMPLATE.relative_to(migration._PACKAGE)
    with (
        mock.patch.object(migration, "_PACKAGE", authority.package),
        mock.patch.object(onboard, "PROJECT_AGENTS_TEMPLATE", authority.package / project_template),
        mock.patch.object(migration, "_LINEAGE_PUBLIC_KEY", authority.public_path),
        mock.patch.object(migration, "_LINEAGE_DOCUMENT", authority.pair_path),
    ):
        yield


def _verify(batch, manifest_path, apply_path, output_path):
    """The genuine read-only consumer, inside the batch environment."""
    with mock.patch.dict(os.environ, batch.environment):
        return verify_migration(manifest_path, apply_path, output_path)


@dataclasses.dataclass
class _Produced:
    """One genuinely produced cross-runtime observation and its context."""

    batch: _SignedBatch
    manifest_path: Path
    apply_path: Path
    missing_path: Path
    output_path: Path
    sealed: dict
    observer: dict
    successor: dict
    authority: _LineageAuthority
    pair_ab: dict
    reconciliation: dict
    report_path: Path


def _smoke_path(deployment):
    return next(
        path
        for ref in deployment["payload"]["projects"][0]["report_refs"]
        if (path := Path(ref["path"])).suffix == ".json"
    )


def _scoped_deployment(case):
    directory = tempfile.TemporaryDirectory()
    case.addCleanup(directory.cleanup)
    base = Path(directory.name).resolve()
    authority = _LineageAuthority(base)
    batch = _SignedBatch(base)
    with _installed(authority):
        authority.use_runtime("predecessor")
        manifest = batch.plan(deployment_mode="init")
        manifest_path = batch.write_manifest(manifest, "manifest.json")
        _, apply_path = batch.apply(manifest_path, routing_approvals=batch.approval)
        deployment_path = batch.evidence / "interrupted-deployment.json"
        deployed, code = batch.execute(manifest_path, apply_path, deployment_path)
    case.assertEqual(code, 0, deployed)
    return authority, batch, manifest, manifest_path, apply_path, deployment_path


def _produce_cross_runtime_observation(case) -> _Produced:
    """Genuinely reconcile A-sealed history observed by signed successor B."""
    authority, batch, manifest, manifest_path, apply_path, missing_path = _scoped_deployment(case)
    sealed = manifest["payload"]["tool_versions"]
    missing_path.unlink()
    output_path = batch.evidence / "successor-observation.json"
    with _installed(authority):
        observer = authority.use_runtime("observer")
        case.assertNotEqual(observer["onboard"], sealed["onboard"])
        pair_ab = authority.install(sealed["onboard"], observer["onboard"])
        result = _reconcile(
            batch, manifest, manifest_path, apply_path, missing_path, output_path
        )
        successor = authority.use_runtime("successor")
        case.assertNotEqual(successor["onboard"], observer["onboard"])
        case.assertEqual(authority.use_runtime("predecessor"), sealed)
    case.assertEqual(result["path"], str(output_path))
    deployment = json.loads(output_path.read_bytes())
    provenance = deployment["payload"]["reconciliation"]
    case.assertEqual(provenance["runtime_versions"], observer)
    report_path = _smoke_path(deployment)
    report = json.loads(report_path.read_bytes())
    case.assertEqual(report["onboardVersion"], observer["onboard"])
    case.assertEqual(report["command"][5], str(authority.entrypoint))
    return _Produced(
        batch=batch,
        manifest_path=manifest_path,
        apply_path=apply_path,
        missing_path=missing_path,
        output_path=output_path,
        sealed=sealed,
        observer=observer,
        successor=successor,
        authority=authority,
        pair_ab=pair_ab,
        reconciliation=provenance,
        report_path=report_path,
    )


class HistoricalObserverLineageTests(unittest.TestCase):
    def test_signed_successor_can_reconcile_and_verify_predecessor(self):
        produced = _produce_cross_runtime_observation(self)
        with _installed(produced.authority):
            self.assertEqual(produced.authority.use_runtime("observer"), produced.observer)
            verified, code = _verify(
                produced.batch, produced.manifest_path, produced.apply_path, produced.output_path
            )
        self.assertEqual(code, 0, verified)
        self.assertEqual(verified["status"], "verified")
        self.assertEqual(
            verified["migration"]["verification"]["payload"]["acceptance_basis"],
            "current-state",
        )

    def test_rotated_pair_keeps_embedded_historical_observer_authority(self):
        produced = _produce_cross_runtime_observation(self)

        # Rotation: the installed pair now authorizes B→C under the SAME,
        # unchanged trust key; the historical A→B authorization is gone from
        # the pair file.
        key_bytes = produced.authority.public_path.read_bytes()
        produced.authority.install(
            produced.observer["onboard"], produced.successor["onboard"]
        )
        self.assertEqual(produced.authority.public_path.read_bytes(), key_bytes)
        installed = json.loads(produced.authority.pair_path.read_bytes())
        self.assertEqual(
            (installed["predecessor"], installed["successor"]),
            (produced.observer["onboard"], produced.successor["onboard"]),
        )

        # Consumption as historical predecessor: the embedded proof, not the
        # rotated pair, must carry the observer's authority. The consumer
        # runs at the sealed manifest runtime, so no other lineage gate
        # intervenes; under the rotated pair the legacy fallback alone would
        # compare (B, C) against (A, B) and fail closed.
        report_bytes = produced.report_path.read_bytes()
        evidence_bytes = produced.output_path.read_bytes()
        with (
            _installed(produced.authority),
            mock.patch(
                "sbtd_deployment_smoke.run_project_smoke",
                side_effect=AssertionError("verification cannot run a fresh smoke"),
            ),
        ):
            verified, code = _verify(
                produced.batch,
                produced.manifest_path,
                produced.apply_path,
                produced.output_path,
            )
        self.assertEqual(code, 0, verified)
        self.assertEqual(verified["status"], "verified")
        self.assertEqual(
            verified["migration"]["verification"]["payload"]["acceptance_basis"],
            "current-state",
        )
        self.assertEqual(produced.report_path.read_bytes(), report_bytes)
        self.assertEqual(produced.output_path.read_bytes(), evidence_bytes)
        self.assertFalse(produced.missing_path.exists())

    def test_bound_report_must_match_observer_window_and_checksum(self):
        produced = _produce_cross_runtime_observation(self)
        original_report = produced.report_path.read_bytes()
        original_evidence = produced.output_path.read_bytes()
        mutations = {
            "consumer instead of observer": {"onboardVersion": produced.sealed["onboard"]},
            "stale report": {"startedAt": "2000-01-01T00:00:00+00:00"},
            "changed bound bytes": {},
        }
        with _installed(produced.authority):
            for case, changes in mutations.items():
                with self.subTest(case=case):
                    report = {**json.loads(original_report), **changes}
                    changed = canonical_json_bytes(report) if changes else original_report + b"\n"
                    produced.report_path.write_bytes(changed)
                    produced.output_path.write_bytes(original_evidence)
                    if changes:
                        def update_ref(payload):
                            for reference in payload["projects"][0]["report_refs"]:
                                if reference["path"] == str(produced.report_path):
                                    reference["state"] = snapshot(produced.report_path)

                        deployment = _reseal_deployment_evidence(produced.output_path, update_ref)
                        if "onboardVersion" in changes:
                            payload = deployment["payload"]
                            with self.assertRaisesRegex(contracts.ContractError, "authorized producer runtime"):
                                validate_deployment_reports(
                                    payload,
                                    payload["projects"][0],
                                    context_paths=(produced.manifest_path, produced.apply_path),
                                )
                    submitted = produced.output_path.read_bytes()
                    verified, code = _verify(
                        produced.batch, produced.manifest_path, produced.apply_path, produced.output_path
                    )
                    self.assertEqual(code, 3, verified)
                    self.assertEqual(verified["status"], "failed")
                    self.assertEqual(produced.output_path.read_bytes(), submitted)
                    self.assertEqual(produced.report_path.read_bytes(), changed)
        self.assertFalse(produced.missing_path.exists())

    def test_executed_report_survives_only_its_authorized_forward_hop(self):
        authority, batch, manifest, manifest_path, apply_path, deployment_path = _scoped_deployment(self)
        sealed = manifest["payload"]["tool_versions"]["onboard"]
        evidence_bytes = deployment_path.read_bytes()
        report_path = _smoke_path(json.loads(evidence_bytes))
        report_bytes = report_path.read_bytes()
        self.assertEqual(json.loads(report_bytes)["onboardVersion"], sealed)
        with _installed(authority):
            observer = authority.use_runtime("observer")["onboard"]
            authority.install(sealed, observer)
            verified, code = _verify(batch, manifest_path, apply_path, deployment_path)
            self.assertEqual(code, 0, verified)
            self.assertEqual(verified["status"], "verified")

            successor = authority.use_runtime("successor")["onboard"]
            authority.install(observer, successor)
            with self.assertRaises(contracts.ContractError) as failure:
                _verify(batch, manifest_path, apply_path, deployment_path)
            self.assertEqual(failure.exception.code, "version-conflict")
        self.assertEqual(report_path.read_bytes(), report_bytes)
        self.assertEqual(deployment_path.read_bytes(), evidence_bytes)

    def test_signed_retry_keeps_completed_observer_smoke(self):
        authority, batch, manifest, manifest_path, apply_path, missing = _scoped_deployment(self)
        missing.unlink()
        observed_path = batch.evidence / "current-state-evidence.json"
        retry_path = batch.evidence / "retry-deployment.json"
        sealed = manifest["payload"]["tool_versions"]["onboard"]
        with _installed(authority):
            observed = _reconcile(batch, manifest, manifest_path, apply_path, missing, observed_path)
            previous_bytes = observed_path.read_bytes()
            refs = observed["evidence"]["payload"]["projects"][0]["report_refs"]
            smoke_bytes = {ref["path"]: Path(ref["path"]).read_bytes() for ref in refs}
            self.assertEqual(
                json.loads(_smoke_path(observed["evidence"]).read_bytes())["onboardVersion"], sealed
            )
            successor = authority.use_runtime("successor")["onboard"]
            authority.install(sealed, successor)

            with mock.patch(
                "sbtd_deployment_smoke.run_project_smoke",
                side_effect=AssertionError("a retry cannot relabel a completed observation"),
            ):
                result, code = batch.execute(
                    manifest_path, apply_path, retry_path, previous_path=observed_path
                )
                self.assertEqual(code, 0, result)
                recorded = result["deploymentEvidence"]["evidence"]["payload"]
                self.assertEqual(recorded["projects"][0]["report_refs"], refs)
                self.assertEqual(recorded["reconciliation"], observed["evidence"]["payload"]["reconciliation"])
                verified, code = _verify(batch, manifest_path, apply_path, retry_path)

        self.assertEqual(code, 0, verified)
        self.assertEqual(observed_path.read_bytes(), previous_bytes)
        self.assertEqual({path: Path(path).read_bytes() for path in smoke_bytes}, smoke_bytes)
        self.assertFalse(missing.exists())

    def test_tampered_embedded_observer_lineage_is_rejected(self):
        produced = _produce_cross_runtime_observation(self)
        embedded = produced.reconciliation.get("observer_lineage")
        self.assertEqual(embedded, produced.pair_ab)
        observer_onboard = produced.observer["onboard"]
        successor_onboard = produced.successor["onboard"]
        foreign_onboard = "runtime-sha256:" + "d" * 64
        genuine_bytes = produced.output_path.read_bytes()
        manifest_before = produced.manifest_path.read_bytes()
        apply_before = produced.apply_path.read_bytes()

        def foreign_signature(document: dict) -> str:
            attacker = Ed25519PrivateKey.generate()
            signed = migration._lineage_signed_bytes(
                document["predecessor"], document["successor"]
            )
            return base64.b64encode(attacker.sign(signed)).decode("ascii")

        # Every mutation keeps the embedded object shape-valid; only its
        # truth changes. The installed pair stays A→B throughout, so the
        # current-pair fallback alone WOULD authorize the observer — each
        # rejection can only come from embedded-proof validation.
        mutations = {
            # Same endpoints, signature from an untrusted key: the installed
            # key is the only trust anchor.
            "foreign-key signature": lambda document: document.update(
                {"signature": foreign_signature(document)}
            ),
            # Well-formed but wrong signature bytes.
            "garbage signature": lambda document: document.update(
                {"signature": base64.b64encode(bytes(64)).decode("ascii")}
            ),
            # A GENUINE object signed by the trusted key, but for the rotated
            # B→C transition: valid signature, wrong endpoints for this
            # manifest→observer pair.
            "genuine signature, rotated endpoints": lambda document: document.update(
                produced.authority.sign(observer_onboard, successor_onboard)
            ),
            # Trusted-key signature over a foreign predecessor endpoint.
            "trusted key, foreign predecessor": lambda document: document.update(
                produced.authority.sign(foreign_onboard, observer_onboard)
            ),
        }

        # Baseline: the genuine record verifies under the still-installed
        # A→B pair, so each rejection below is caused by the tamper alone.
        with _installed(produced.authority):
            verified, code = _verify(
                produced.batch,
                produced.manifest_path,
                produced.apply_path,
                produced.output_path,
            )
        self.assertEqual(code, 0, verified)

        for name, mutate in mutations.items():
            with self.subTest(case=name):
                produced.output_path.write_bytes(genuine_bytes)

                def forge(payload: dict, mutate=mutate) -> None:
                    mutate(payload["reconciliation"]["observer_lineage"])

                _reseal_deployment_evidence(produced.output_path, forge)
                forged_bytes = produced.output_path.read_bytes()
                with (
                    _installed(produced.authority),
                    self.assertRaises(contracts.ContractError),
                ):
                    _verify(
                        produced.batch,
                        produced.manifest_path,
                        produced.apply_path,
                        produced.output_path,
                    )
                # Rejection is read-only: forged evidence stays as submitted,
                # cited inputs keep their bytes, the historical path stays
                # absent.
                self.assertEqual(produced.output_path.read_bytes(), forged_bytes)
                self.assertEqual(produced.manifest_path.read_bytes(), manifest_before)
                self.assertEqual(produced.apply_path.read_bytes(), apply_before)
                self.assertFalse(produced.missing_path.exists())

    def test_same_runtime_record_consumes_without_lineage_assets(self):
        batch, manifest, manifest_path, apply_path, missing_path = (
            _interrupted_deployment(self)
        )
        output_path = batch.evidence / "current-state-evidence.json"
        result = _reconcile(
            batch, manifest, manifest_path, apply_path, missing_path, output_path
        )
        self.assertEqual(result["path"], str(output_path))
        reconciliation = json.loads(output_path.read_bytes())["payload"][
            "reconciliation"
        ]
        # The observer IS the manifest runtime: no cross-runtime
        # authorization exists to preserve, so nothing is embedded.
        self.assertEqual(
            reconciliation["runtime_versions"], manifest["payload"]["tool_versions"]
        )
        self.assertIsNone(reconciliation.get("observer_lineage"))

        # Both lineage assets point at never-created paths: consumption of a
        # same-runtime record must not consult them at all.
        with (
            mock.patch.object(
                migration, "_LINEAGE_PUBLIC_KEY", batch.evidence / "never.pub"
            ),
            mock.patch.object(
                migration, "_LINEAGE_DOCUMENT", batch.evidence / "never.json"
            ),
        ):
            verified, code = _verify(batch, manifest_path, apply_path, output_path)
        self.assertEqual(code, 0, verified)
        self.assertEqual(verified["status"], "verified")
        self.assertFalse(missing_path.exists())

    def test_legacy_record_without_proof_keeps_bounded_pair_fallback(self):
        produced = _produce_cross_runtime_observation(self)
        # Strip the proof and reseal exactly the pre-embedding record shape.
        _reseal_deployment_evidence(
            produced.output_path,
            lambda payload: payload["reconciliation"].pop("observer_lineage", None),
        )
        legacy_bytes = produced.output_path.read_bytes()
        stripped = json.loads(legacy_bytes)["payload"]["reconciliation"]
        self.assertNotIn("observer_lineage", stripped)

        # Fallback retained: the still-installed A→B pair authorizes the
        # historical observer for a proof-less record.
        with _installed(produced.authority):
            verified, code = _verify(
                produced.batch,
                produced.manifest_path,
                produced.apply_path,
                produced.output_path,
            )
        self.assertEqual(code, 0, verified)
        self.assertEqual(verified["status"], "verified")

        # But the fallback stays bounded by the current pair: after rotation
        # a proof-less record has no authority left and must fail closed,
        # leaving the submitted bytes untouched.
        produced.authority.install(
            produced.observer["onboard"], produced.successor["onboard"]
        )
        with (
            _installed(produced.authority),
            self.assertRaises(contracts.ContractError) as failure,
        ):
            _verify(
                produced.batch,
                produced.manifest_path,
                produced.apply_path,
                produced.output_path,
            )
        self.assertEqual(failure.exception.code, "version-conflict")
        self.assertEqual(produced.output_path.read_bytes(), legacy_bytes)
        self.assertFalse(produced.missing_path.exists())


if __name__ == "__main__":
    unittest.main()
