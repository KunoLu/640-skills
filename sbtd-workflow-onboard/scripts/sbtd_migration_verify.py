"""Read-only migration verification and deployment report acceptance.

Boundary (docs/prd/sbtd-workflow-v2-migration-runtime.md, main PRD 10.2/11):

- ``verify_migration`` consumes the explicit private manifest, apply receipt
  and deployment evidence with the strict codec, proves document IDs, raw
  bindings, closure and complete predecessor success before observing
  anything, then checks actual resources against their last completed phase
  states, every retained original backup, the private source originals, the
  approved publication projections and the declared cleanup candidates. It
  never writes projects, HOME or the vault, never deploys, runs no smoke and
  performs no receipt discovery; the sealed verification is returned inside
  the read-only envelope for the authorized caller to store privately. When
  the bound deployment evidence carries current-state reconciliation
  provenance, the verification payload exposes
  ``acceptance_basis = "current-state"``; ordinary executed-origin evidence
  keeps the historical shape with no marker.
- ``validate_deployment_reports`` re-validates the native validation-evidence
  v1/v2 envelopes and their raw runner reports for one supplied deployment
  project record. The caller owns actual project Git and filesystem truth;
  this helper only checks the supplied scope facts against readable,
  checksum-matching report references bound to the current deployment
  attempt. A passing native envelope alone is not acceptance: the current
  attempt window, the raw API smoke exit status, the project root/ref/HEAD
  binding, the verified environment and the non-mock mode are all checked.
  Non-API reports remain non-acceptance-bearing but must be v2 typed reports
  with a passed locator-bound case; v1/untyped auxiliary formats are rejected
  rather than parsed generically. JSON shape or hash equality is never
  execution or host authenticity proof, and fixture-based checks never prove
  a real deployment happened.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

import onboard_contracts as contracts
import sbtd_migration as migration
from sbtd_migration_files import read_file, snapshot
from sbtd_project import _reject_json_duplicates

__all__ = [
    "ONBOARD_CLI_BOOTSTRAP",
    "ONBOARD_CLI_SMOKE_SCHEMA",
    "onboard_cli_smoke_command",
    "validate_deployment_reports",
    "verify_migration",
]

_PACKAGE = Path(__file__).resolve().parents[1]
_EVIDENCE_VALIDATOR = (
    _PACKAGE
    / "templates"
    / "skills"
    / "project-validation"
    / "scripts"
    / "validate_validation_evidence.py"
)

# Genuine, non-mock runner modes from the unchanged native evidence schema;
# contract-backed/app-mocked/blocked/not-needed runs cannot prove acceptance.
_GENUINE_MODES = frozenset({"full-stack", "smoke-only", "backend-only"})
ONBOARD_CLI_SMOKE_SCHEMA = "sbtd-onboard-cli-smoke-1"
ONBOARD_CLI_BOOTSTRAP = (
    "import os,runpy,sys;sys.argv=sys.argv[1:];"
    "sys.path.insert(0,os.path.dirname(sys.argv[0]));"
    "runpy.run_path(sys.argv[0],run_name='__main__')"
)
_ONBOARD_CLI_SMOKE_KEYS = frozenset(
    {
        "schema",
        "projectRoot",
        "sourceRef",
        "sourceCommit",
        "startedAt",
        "finishedAt",
        "command",
        "exitCode",
        "status",
        "mockStrategy",
        "onboardVersion",
        "projection",
        "projectionSha256",
    }
)
_ONBOARD_CLI_SMOKE_BOUND_KEYS = _ONBOARD_CLI_SMOKE_KEYS | {"manifestId", "applyId"}


def onboard_cli_smoke_command(
    root: Path, *, context_paths: tuple[Path, Path] | None = None
) -> list[str]:
    """Exact check-projects argv. Token membership is not acceptance."""
    command = [
        sys.executable,
        "-I",
        "-B",
        "-c",
        ONBOARD_CLI_BOOTSTRAP,
        str((migration._PACKAGE / "scripts" / "onboard.py").resolve()),
        "check-projects",
        "--projects-root",
        str(root),
        "--json",
    ]
    if context_paths is not None:
        manifest_path, apply_path = context_paths
        command.extend(
            [
                "--migration-manifest",
                str(manifest_path),
                "--migration-apply-receipt",
                str(apply_path),
            ]
        )
    return command

_PROJECT_OUTCOME = {
    "verified": ("", ""),
    "not-verified": (
        "historical Graft bytes match, but no trusted post-write permission evidence exists",
        "Do not clean up or repair. Missing mode evidence does not authorize a write.",
    ),
    "failed": (
        "actual resources or bound deployment reports differ from the proven migration state",
        "Inspect the private evidence; do not clean up or patch historical bytes.",
    ),
    "blocked": (
        "not every required state could be observed",
        "Restore access to the declared evidence and repeat verification before cleanup.",
    ),
}
_VERIFY_OUTCOME = {
    "verified": (
        "",
        "Review the recorded cleanup candidates and confirm cleanup explicitly with this verification_id.",
    ),
    "not-verified": (
        "historical Graft evidence has no trusted post-write permission proof",
        "Preserve originals. This result does not authorize cleanup, deployment, or repair.",
    ),
    "failed": (
        "not every project passed migration acceptance",
        "Inspect the private per-project evidence; preserve originals and do not clean up.",
    ),
    "blocked": (
        "verification could not observe every required state",
        "Resolve the observation gap and repeat verification before cleanup.",
    ),
}
_VERIFY_EXIT = {"verified": 0, "not-verified": 2, "blocked": 2, "failed": 3}


def _fail(code: str, message: str, exit_code: int = 2) -> NoReturn:
    raise contracts.ContractError(code, message, exit_code=exit_code)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="microseconds")

_MODE_TEXT = re.compile(r"^0[0-7]{3}$")
_NO_WRITE = "Do not clean up, deploy, or repair. This result does not authorize a write."


def _mode_signed_bytes(
    deployment_id: str, resource_id: str, mode: str, after: Mapping[str, Any]
) -> bytes:
    """Bytes covered by one attestation. Not the deployment document hash."""
    return contracts.canonical_json_bytes(
        {
            "schema_version": 1,
            "purpose": "post-write-mode",
            "deployment_id": deployment_id,
            "resource_id": resource_id,
            "mode": mode,
            "after": {"type": after.get("type"), "checksum": after.get("checksum")},
        }
    )


def _installed_lineage_key() -> Any:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    key_path = migration._LINEAGE_PUBLIC_KEY
    key = load_pem_public_key(read_file(key_path, snapshot(key_path)))
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError
    return key


def _attested_mode(
    proofs: list[Any],
    deployment_id: str,
    resource_id: str,
    after: Mapping[str, Any],
) -> tuple[str | None, dict[str, str] | None]:
    """A signature over this deployment. A result field is not one."""
    matches = [
        proof
        for proof in proofs
        if isinstance(proof, Mapping) and proof.get("resource_id") == resource_id
    ]
    if len(matches) != 1:
        return None, None
    proof = matches[0]
    mode = proof.get("mode")
    signature = proof.get("signature")
    recorded = {"type": after.get("type"), "checksum": after.get("checksum")}
    if (
        proof.get("kind") != "signed-attestation"
        or not isinstance(mode, str)
        or _MODE_TEXT.fullmatch(mode) is None
        or proof.get("after") != recorded
        or proof.get("deployment_id") != deployment_id
        or not isinstance(signature, str)
        or not signature
    ):
        return None, None
    try:
        from cryptography.exceptions import InvalidSignature

        _installed_lineage_key().verify(
            base64.b64decode(signature, validate=True),
            _mode_signed_bytes(deployment_id, resource_id, mode, after),
        )
    except (InvalidSignature, ValueError, TypeError, OSError, contracts.ContractError):
        return None, None
    return mode, {"kind": "signed-attestation", "purpose": "post-write-mode"}


def _posix_mode(path: Path) -> str | None:
    """POSIX permission bits only. Windows DACL is not invented from chmod."""
    if os.name != "posix":
        return None
    try:
        info = path.lstat()
    except OSError:
        return None
    if stat.S_ISLNK(info.st_mode) or not (
        stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)
    ):
        return None
    return f"{stat.S_IMODE(info.st_mode):04o}"


def _classify_legacy_resource(
    operation: Mapping[str, Any],
    result: Mapping[str, Any] | None,
    state: Mapping[str, Any] | None,
    proofs: list[Any],
    deployment_id: str,
) -> dict[str, Any]:
    """Compare recorded bytes and a signed post-write mode. No writes."""
    record: dict[str, Any] = {
        "resource_id": operation["resource_id"],
        "target": operation["target"],
        "bytes": "unreadable",
        "mode": "absent",
        "status": "not-verified",
        "mode_source": None,
        "reason": "the live resource could not be read; an absent or unreadable path is not drift",
    }
    if (
        state is None
        or result is None
        or result.get("status") != "succeeded"
        or not isinstance(result.get("after"), Mapping)
    ):
        return record
    after = result["after"]
    record["bytes"] = "match" if state == after else "differ"
    # post_write_mode on the result is ignored. Resealing that field is not proof.
    mode, source = _attested_mode(proofs, deployment_id, operation["resource_id"], after)
    if mode is not None and os.name == "posix":
        live = _posix_mode(Path(operation["target"]))
        if live is None:
            record["reason"] = (
                "recorded bytes were observed, but the live POSIX mode could not be read; this is not drift"
            )
        else:
            record["mode"] = "match" if live == mode else "differ"
            record["mode_source"] = source
    elif mode is not None:
        record["reason"] = (
            "recorded bytes were observed, but this platform has no POSIX mode and no DACL evidence"
        )
    if record["bytes"] == "differ" or record["mode"] == "differ":
        record["status"] = "drifted"
        record["reason"] = (
            "recorded bytes differ from the live resource"
            if record["bytes"] == "differ"
            else "the trusted post-write mode differs from the live POSIX mode"
        )
    elif record["mode"] == "match":
        record["status"] = "verified"
        record["reason"] = "recorded bytes and the trusted post-write mode match"
    elif record["bytes"] == "match" and mode is None:
        record["reason"] = (
            "recorded bytes match, but no trusted post-write permission evidence exists"
        )
    return record



def _evidence_validator() -> Any:
    """Lazy self-contained load of the unchanged native evidence validator."""
    try:
        spec = importlib.util.spec_from_file_location(
            "validate_validation_evidence", _EVIDENCE_VALIDATOR
        )
        if spec is None or spec.loader is None:
            raise ImportError
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except (ImportError, OSError):
        _fail(
            "validator-unavailable",
            "the native validation-evidence validator is unavailable",
        )


def _reject_report_constant(literal: str) -> NoReturn:
    raise ValueError


def _decode_report(content: bytes) -> Any:
    """Lenient JSON for report bytes; strict UTF-8, no duplicate keys/non-finite."""
    try:
        text = bytes(content).decode("utf-8", errors="strict")
        return json.loads(
            text,
            object_pairs_hook=_reject_json_duplicates,
            parse_constant=_reject_report_constant,
        )
    except (ValueError, RecursionError, UnicodeError, contracts.ContractError):
        return None


def _attempt_time(container: Mapping[str, Any], key: str) -> Any:
    try:
        parsed = contracts._parse_timestamp(container[key])
        timestamp, _fraction = parsed
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("timestamp must carry an explicit UTC offset")
        return parsed
    except (KeyError, TypeError, ValueError, AttributeError):
        _fail("unexpected-type", "deployment scope fields are missing or invalid")


def _report_path(root: Path, recorded: Any) -> Path:
    if not isinstance(recorded, str) or not recorded:
        _fail("unexpected-type", "deployment report paths are missing or invalid")
    candidate = Path(recorded)
    return candidate if candidate.is_absolute() else root / candidate


def _bound_reports(project_record: Mapping[str, Any]) -> dict[str, bytes]:
    """Actual nofollow bytes of every declared report ref, checksum-bound."""
    refs = project_record.get("report_refs")
    if not isinstance(refs, list):
        _fail("unexpected-type", "deployment report references are missing or invalid")
    bound: dict[str, bytes] = {}
    for reference in refs:
        if (
            not isinstance(reference, Mapping)
            or not isinstance(reference.get("path"), str)
            or not isinstance(reference.get("state"), Mapping)
        ):
            _fail(
                "unexpected-type",
                "deployment report references are missing or invalid",
            )
        try:
            bound[reference["path"]] = read_file(
                Path(reference["path"]), reference.get("state")
            )
        except contracts.ContractError:
            _fail(
                "report-unavailable",
                "a bound deployment report is unavailable or changed",
                3,
            )
    return bound


def _accept_raw_smoke(
    content: bytes,
    report: Mapping[str, Any],
    envelope: Mapping[str, Any],
    *,
    started: Any,
    finished: Any,
    root: Path,
    source_ref: Any,
    head: Any,
) -> None:
    """Raw API runner JSON: real exit, current attempt, exact scope, non-mock."""
    value = _decode_report(content)
    if not isinstance(value, dict):
        _fail("report-acceptance", "an API smoke raw report is not a JSON object", 3)
    exit_code = value.get("exitCode")
    if isinstance(exit_code, bool) or not isinstance(exit_code, int) or exit_code != 0:
        _fail("report-acceptance", "an API smoke raw run did not exit cleanly", 3)
    if value.get("timedOut") is not False:
        _fail("report-acceptance", "an API smoke raw run timed out", 3)
    command = value.get("command")
    if (
        not isinstance(command, list)
        or not command
        or not all(isinstance(item, str) and item for item in command)
    ):
        _fail(
            "report-acceptance",
            "an API smoke raw run lacks its executed command",
            3,
        )
    if not isinstance(value.get("stdout"), str) or not isinstance(
        value.get("stderr"), str
    ):
        _fail(
            "report-acceptance",
            "an API smoke raw run lacks its captured output",
            3,
        )
    process_exit = value.get("processExitCode")
    if "processExitCode" in value and (
        isinstance(process_exit, bool)
        or not isinstance(process_exit, int)
        or process_exit != 0
    ):
        _fail(
            "report-acceptance",
            "an API smoke raw run process exit contradicts its clean exit",
            3,
        )
    raw_started = _attempt_time(value, "startedAt")
    raw_finished = _attempt_time(value, "finishedAt")
    if raw_started > raw_finished or raw_started < started or raw_finished > finished:
        _fail(
            "report-acceptance",
            "an API smoke raw run is outside the current deployment attempt",
            3,
        )
    if value.get("projectRoot") != str(root):
        _fail("report-acceptance", "an API smoke raw run is bound to another root", 3)
    if value.get("sourceRef") != source_ref or value.get("sourceCommit") != head:
        _fail(
            "report-acceptance",
            "an API smoke raw run is bound to another revision",
            3,
        )
    if (
        value.get("environmentAlignment") != "verified"
        or value.get("mockStrategy") != "none"
        or value.get("e2eMode") != report["mode"]
    ):
        _fail(
            "report-acceptance",
            "an API smoke raw run is not a verified non-mock smoke",
            3,
        )
    repository = envelope["repository"]
    provenance = {
        "repositoryKey": repository.get("repositoryKey"),
        "sourceRef": repository.get("sourceRef"),
        "sourceCommit": repository.get("sourceCommit"),
        "worktreeState": repository.get("worktreeState"),
        "sourceRevision": envelope.get("sourceRevision"),
        "evidenceSource": envelope.get("evidenceSource"),
        "trigger": envelope.get("trigger"),
        "environmentAlignment": envelope.get("environmentAlignment"),
        "evidencePublication": envelope.get("evidencePublication"),
        "e2eMode": envelope.get("e2eMode"),
        "mockStrategy": envelope.get("mockStrategy"),
    }
    if any(value.get(key) != expected for key, expected in provenance.items()):
        _fail(
            "report-acceptance",
            "an API smoke raw run is not bound to the enclosing envelope",
            3,
        )


def _accept_auxiliary_report(
    content: bytes,
    report: Mapping[str, Any],
    envelope: Mapping[str, Any],
    validator: Any,
) -> None:
    """Require a v2 typed report and locator-bound passing case, not a smoke."""
    if envelope.get("schemaVersion") != 2:
        _fail(
            "report-acceptance",
            "an auxiliary deployment report has no typed format contract",
            3,
        )
    report_format = report.get("reportFormat")
    if report_format not in {"junit-xml-v1", "playwright-json-v1"}:
        _fail(
            "report-acceptance",
            "an auxiliary deployment report does not declare a supported typed format",
            3,
        )
    report_sha = report["sha256"].lower()
    links = [
        link
        for link in envelope["scenarioLinks"]
        if link["reportSha256"].lower() == report_sha
    ]
    if not links:
        _fail(
            "report-acceptance",
            "an auxiliary deployment report has no source locator provenance",
            3,
        )
    try:
        cases = (
            validator.parse_junit(content)
            if report_format == "junit-xml-v1"
            else validator.parse_playwright(content)
        )
        locators = {
            locator["sourceLocatorDigest"]: locator
            for locator in envelope["sourceLocators"]
        }
        for link in links:
            locator = locators[link["sourceLocatorDigest"]]
            if any(
                locator.get(key) != envelope["repository"].get(key)
                for key in ("repositoryKey", "sourceRef")
            ):
                _fail(
                    "report-acceptance",
                    "an auxiliary source locator belongs to another repository or revision",
                    3,
                )
            matched = (
                validator.match_junit(cases, link["testCaseSelector"])
                if report_format == "junit-xml-v1"
                else validator.match_playwright(cases, link["testCaseSelector"])
            )
            if len(matched) != 1 or matched[0]["outcome"] != "passed":
                _fail(
                    "report-acceptance",
                    "an auxiliary deployment report does not prove its passed case",
                    3,
                )
            if validator.unique_binding(matched[0]) != validator.source_locator_digest(
                locator
            ):
                _fail(
                    "report-acceptance",
                    "an auxiliary deployment report is bound to another source locator",
                    3,
                )
    except (KeyError, TypeError, validator.EvidenceError):
        _fail(
            "report-acceptance",
            "an auxiliary deployment report failed typed content or provenance validation",
            3,
        )


def _accept_report(
    report: Any,
    envelope: Mapping[str, Any],
    validator: Any,
    *,
    started: Any,
    finished: Any,
    root: Path,
    source_ref: Any,
    head: Any,
    bound: Mapping[str, bytes],
) -> bool:
    """One native report entry; returns True for a genuine API smoke."""
    if not isinstance(report, Mapping):
        _fail("unexpected-type", "deployment report entries are missing or invalid")
    if report.get("status") != "passed":
        _fail(
            "report-acceptance",
            "a deployment report did not pass its declared run",
            3,
        )

    content = bound.get(str(_report_path(root, report.get("path"))))
    if content is None:
        _fail(
            "report-acceptance",
            "a deployment report is not one of the declared bound references",
            3,
        )
    sha256 = report.get("sha256")
    if (
        not isinstance(sha256, str)
        or hashlib.sha256(content).hexdigest() != sha256.lower()
    ):
        _fail("report-acceptance", "a deployment report digest does not match", 3)
    summary_path = str(_report_path(root, report.get("summaryMd")))
    if bound.get(summary_path) is None:
        _fail(
            "report-unavailable",
            "a deployment report summary is not a declared bound reference",
            3,
        )

    if report.get("testType") != "api":
        _accept_auxiliary_report(content, report, envelope, validator)
        return False
    if report.get("mode") not in _GENUINE_MODES:
        _fail(
            "report-acceptance",
            "an API deployment report did not pass a genuine non-mock run",
            3,
        )
    _accept_raw_smoke(
        content,
        report,
        envelope,
        started=started,
        finished=finished,
        root=root,
        source_ref=source_ref,
        head=head,
    )
    return True


def _accept_envelope(
    validator: Any,
    envelope: Mapping[str, Any],
    *,
    started: Any,
    finished: Any,
    root: Path,
    source_ref: Any,
    head: Any,
    bound: Mapping[str, bytes],
) -> bool:
    """Native v1/v2 validation plus current-attempt scope acceptance."""
    try:
        if envelope["schemaVersion"] == 1:
            validator.validate_v1(envelope)
        else:
            validator.validate_v2(envelope, root)
    except validator.EvidenceError as error:
        if error.code == "VALIDATOR_UNAVAILABLE":
            _fail(
                "validator-unavailable",
                "the native validation-evidence validator dependency is unavailable",
            )
        _fail("report-acceptance", "native deployment evidence failed validation", 3)
    created = _attempt_time(envelope, "createdAt")
    if created < started or created > finished:
        _fail(
            "report-acceptance",
            "native deployment evidence is outside the current deployment attempt",
            3,
        )
    if (
        envelope.get("environmentAlignment") != "verified"
        or envelope.get("mockStrategy") != "none"
        or envelope.get("e2eMode") not in _GENUINE_MODES
    ):
        _fail(
            "report-acceptance",
            "deployment evidence is not environment-verified non-mock smoke",
            3,
        )
    repository = envelope.get("repository")
    if not isinstance(repository, Mapping):
        _fail("unexpected-type", "deployment evidence repository is missing")
    commit = repository.get("sourceCommit")
    if (
        repository.get("sourceRef") != source_ref
        or (commit.lower() if isinstance(commit, str) else None) != head
    ):
        _fail(
            "report-acceptance",
            "deployment evidence is bound to another revision",
            3,
        )
    api_smoke = False
    for report in envelope["reports"]:
        api_smoke |= _accept_report(
            report,
            envelope,
            validator,
            started=started,
            finished=finished,
            root=root,
            source_ref=source_ref,
            head=head,
            bound=bound,
        )
    return api_smoke


def _matches_onboard_cli_producer(
    recorded: Any,
    deployment_payload: Mapping[str, Any],
    verified_manifest: Mapping[str, Any] | None,
) -> bool:
    reconciliation = deployment_payload.get("reconciliation")
    if reconciliation is not None:
        if not isinstance(reconciliation, Mapping):
            return False
        versions = reconciliation.get("runtime_versions")
        if not isinstance(versions, Mapping) or recorded != versions.get("onboard"):
            return False

    if verified_manifest is None:
        return recorded == migration.runtime_versions()["onboard"]

    sealed = verified_manifest["payload"]["tool_versions"]
    if "graft" in sealed:
        # The archived runtime produced native reports, not Onboard CLI captures.
        return False
    # Context validation has already authenticated any historical observer.
    if reconciliation is not None or recorded == sealed["onboard"]:
        return True

    # An ordinary deployment can execute after an authorized hop. Without a
    # retained observer proof, only the exact installed forward pair grants it.
    current = migration.runtime_versions()["onboard"]
    return recorded == current and migration._verified_runtime_pair() == (
        sealed["onboard"], current
    )


def _accept_onboard_cli_smoke(
    document: Mapping[str, Any],
    *,
    started: Any,
    finished: Any,
    root: Path,
    source_ref: Any,
    head: Any,
    deployment_payload: Mapping[str, Any],
    verified_manifest: Mapping[str, Any] | None,
    context_paths: tuple[Path, Path] | None,
) -> None:
    """Trusted local check-projects capture. Not a business API pass."""
    expected_keys = (
        _ONBOARD_CLI_SMOKE_BOUND_KEYS
        if context_paths is not None
        else _ONBOARD_CLI_SMOKE_KEYS
    )
    if set(document) != expected_keys or document.get("schema") != ONBOARD_CLI_SMOKE_SCHEMA:
        _fail(
            "report-acceptance",
            "an Onboard CLI smoke record is not the trusted check-projects identity",
            3,
        )
    if document.get("status") != "passed" or document.get("mockStrategy") != "none":
        _fail(
            "report-acceptance",
            "an Onboard CLI smoke record is not a non-mock passed run",
            3,
        )
    exit_code = document.get("exitCode")
    if isinstance(exit_code, bool) or exit_code != 0:
        _fail("report-acceptance", "an Onboard CLI smoke record did not exit cleanly", 3)
    if document.get("projectRoot") != str(root) or document.get("sourceRef") != source_ref:
        _fail(
            "report-acceptance",
            "an Onboard CLI smoke record is bound to another root or revision",
            3,
        )
    commit = document.get("sourceCommit")
    if (commit.lower() if isinstance(commit, str) else None) != head:
        _fail(
            "report-acceptance",
            "an Onboard CLI smoke record is bound to another root or revision",
            3,
        )
    if not _matches_onboard_cli_producer(
        document.get("onboardVersion"), deployment_payload, verified_manifest
    ):
        _fail(
            "report-acceptance",
            "an Onboard CLI smoke record does not match its authorized producer runtime",
            3,
        )
    raw_started = _attempt_time(document, "startedAt")
    raw_finished = _attempt_time(document, "finishedAt")
    if raw_started > raw_finished or raw_started < started or raw_finished > finished:
        _fail(
            "report-acceptance",
            "an Onboard CLI smoke record is outside the current deployment attempt",
            3,
        )
    if context_paths is not None:
        manifest_id = deployment_payload.get("manifest_id")
        apply_id = deployment_payload.get("apply_id")
        if (
            not isinstance(manifest_id, str)
            or not isinstance(apply_id, str)
            or document.get("manifestId") != manifest_id
            or document.get("applyId") != apply_id
        ):
            _fail(
                "report-acceptance",
                "an Onboard CLI smoke record is bound to another migration apply",
                3,
            )
    if document.get("command") != onboard_cli_smoke_command(
        root, context_paths=context_paths
    ):
        _fail(
            "report-acceptance",
            "an Onboard CLI smoke record did not run the installed check-projects command",
            3,
        )
    projection = document.get("projection")
    digest = document.get("projectionSha256")
    expected = {
        "mode": "check-projects",
        "projects": [{"projectRoot": str(root), "sbtd": {"status": "success"}}],
    }
    if (
        projection != expected
        or not isinstance(digest, str)
        or hashlib.sha256(contracts.canonical_json_bytes(expected)).hexdigest() != digest.lower()
    ):
        _fail(
            "report-acceptance",
            "an Onboard CLI smoke projection is not the closed check-projects identity",
            3,
        )


def validate_deployment_reports(
    deployment_payload: Mapping[str, Any],
    project_record: Mapping[str, Any],
    *,
    epoch_started: Any = None,
    context_paths: tuple[Path, Path] | None = None,
    verified_manifest: Mapping[str, Any] | None = None,
) -> None:
    """Re-validate one project's bound deployment reports against the attempt.

    ``deployment_payload`` supplies the current attempt window; ``project_record``
    supplies the declared root/source_ref/head scope and report_refs. A first
    attempt must produce every report inside its exact window; a cumulative
    retry (non-null ``previous_deployment_id``) may retain earlier reports
    within the same bound apply epoch, so the caller passes that epoch's lower
    bound (the bound apply receipt's finished_at) separately as
    ``epoch_started`` while the deployment bytes stay immutable. Every
    reference must still be the exact recorded file, at least one native
    validation-evidence v1/v2 envelope must pass its own unchanged schema
    validation, and at least one genuine non-mock API smoke raw run must be
    bound to this root, revision and window. When ``context_paths`` is supplied,
    an Onboard CLI record must also carry this payload's manifest/apply IDs and
    the exact argv for those paths; genuine native API evidence stays separate.
    Fresh acceptance requires the installed runtime, which must also match
    the reconciliation observer when present. Pass ``verified_manifest`` only
    after checking the completed evidence's bindings, runtime and provenance.
    Sanitized ContractError only.
    """
    if not isinstance(deployment_payload, Mapping) or not isinstance(
        project_record, Mapping
    ):
        _fail(
            "unexpected-type", "deployment payload and project record must be mappings"
        )
    started = _attempt_time(deployment_payload, "started_at")
    finished = _attempt_time(deployment_payload, "finished_at")
    if started > finished:
        _fail("unexpected-type", "the deployment attempt window is invalid")
    if deployment_payload.get("previous_deployment_id") is not None:
        if not isinstance(epoch_started, str):
            _fail("unexpected-type", "the bound apply epoch is missing or invalid")
        started = _attempt_time({"epoch_started": epoch_started}, "epoch_started")
        if started > finished:
            _fail("unexpected-type", "the bound apply epoch is invalid")
    try:
        root = Path(project_record["root"])
        source_ref = project_record["source_ref"]
        head = project_record["head"]
    except (KeyError, TypeError):
        _fail("unexpected-type", "deployment scope fields are missing or invalid")
    # Native schemas keep their required string ref. These explicit labels
    # represent branchlessness, not invented branch names; outer refs stay null.
    if source_ref is None:
        source_ref = "HEAD" if head is not None else "non-git"
    bound = _bound_reports(project_record)
    decoded = [_decode_report(content) for content in bound.values()]
    cli_smoke = [
        value
        for value in decoded
        if isinstance(value, dict) and value.get("schema") == ONBOARD_CLI_SMOKE_SCHEMA
    ]
    envelopes = [
        value
        for value in decoded
        if isinstance(value, dict)
        and value.get("schemaVersion") in (1, 2)
        and isinstance(value.get("reports"), list)
    ]
    if cli_smoke:
        if len(cli_smoke) != 1:
            _fail(
                "report-acceptance",
                "multiple Onboard CLI smoke identities are bound to this project",
                3,
            )
        _accept_onboard_cli_smoke(
            cli_smoke[0],
            started=started,
            finished=finished,
            root=root,
            source_ref=source_ref,
            head=head,
            deployment_payload=deployment_payload,
            verified_manifest=verified_manifest,
            context_paths=context_paths,
        )
        if not envelopes:
            return
    validator = _evidence_validator()
    if not envelopes:
        _fail(
            "report-unavailable",
            "no native validation-evidence envelope is bound to this project",
            3,
        )
    api_smoke = False
    for envelope in envelopes:
        api_smoke |= _accept_envelope(
            validator,
            envelope,
            started=started,
            finished=finished,
            root=root,
            source_ref=source_ref,
            head=head,
            bound=bound,
        )
    if not api_smoke:
        _fail(
            "report-acceptance",
            "no genuine API smoke report is bound to this project",
            3,
        )

def _check_approved_routing(
    manifest: Mapping[str, Any], *, collect: bool = False
) -> set[str]:
    """Re-derive approved project AGENTS bytes. A copy digest is not success.

    Selector ``approved-agents:<sha256>`` must name the signed paused
    candidate minus the pause-file prefix and at most one following blank.
    The live file must equal that rederived body. The sealed source stays
    the paused candidate and is not the expected render. Historical D7
    collection records a drifted target and continues; it does not abort
    unrelated rows.
    """
    from sbtd_deployment import APPROVED_AGENTS, approved_agents_selector
    from sbtd_migration_plan import approved_agents_provenance

    drifted: set[str] = set()

    def note(target: str, message: str) -> None:
        if collect:
            drifted.add(target)
            return
        migration._fail("approved-routing-drift", message)

    _origin, bodies = approved_agents_provenance(manifest)
    prefix = APPROVED_AGENTS + ":"
    deployed = {
        operation["target"]: operation
        for operation in migration._operations(manifest)
        if operation["phase"] == "deploy"
        and isinstance(operation.get("selector"), str)
        and operation["selector"].startswith(prefix)
    }
    for target, operation in deployed.items():
        expected = bodies.get(target)
        if not isinstance(expected, bytes) or operation["selector"] != approved_agents_selector(expected):
            note(target, "an approved project AGENTS body was not rederived from the signed candidate")
            continue
        try:
            live = read_file(Path(target))
        except contracts.ContractError:
            note(target, "an approved project AGENTS file is not the signed body")
            continue
        if live != expected:
            note(target, "an approved project AGENTS file is not the signed body")
    rendered = set(deployed) | {
        operation["target"]
        for operation in migration._operations(manifest)
        if operation["phase"] == "deploy" and operation["selector"] == "graft-agents"
    }
    for operation in migration._operations(manifest):
        if operation["selector"] != "approved-routing-replacement":
            continue
        target = operation["target"]
        if target in rendered:
            continue
        candidate = operation["change"]["source_ref"]
        expected_state = snapshot(Path(candidate["path"]))
        if expected_state is None or snapshot(Path(target)) != expected_state:
            note(target, "an approved routing file no longer matches its candidate")
    return drifted



def _load_post_write_attestation(
    path: Path | None, deployment_id: str
) -> list[dict[str, Any]]:
    """Private signed sidecar. Embedded deployment fields are not proof."""
    if path is None:
        return []
    from sbtd_migration_files import require_private_directory

    attestation = Path(path)
    require_private_directory(attestation.parent)
    before = snapshot(attestation)
    if before.get("type") != "file":
        _fail("binding-violation", "an unsigned post-write attestation is not accepted")
    raw = read_file(attestation, before)
    if snapshot(attestation) != before:
        _fail("state-conflict", "the post-write attestation changed during verification")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        _fail("binding-violation", "an unsigned post-write attestation is not accepted")
    entries = document.get("attestations") if isinstance(document, dict) else None
    if (
        not isinstance(document, dict)
        or document.get("schema_version") != 1
        or document.get("purpose") != "post-write-mode"
        or not isinstance(entries, list)
        or not entries
    ):
        _fail("binding-violation", "an unsigned post-write attestation is not accepted")
    if document.get("deployment_id") != deployment_id:
        return []
    proofs: list[dict[str, Any]] = []
    for proof in entries:
        if (
            not isinstance(proof, Mapping)
            or not isinstance(proof.get("signature"), str)
            or not proof.get("signature")
            or not isinstance(proof.get("resource_id"), str)
            or not isinstance(proof.get("mode"), str)
            or not isinstance(proof.get("after"), Mapping)
        ):
            _fail("binding-violation", "an unsigned post-write attestation is not accepted")
        after = proof["after"]
        try:
            from cryptography.exceptions import InvalidSignature

            _installed_lineage_key().verify(
                base64.b64decode(proof["signature"], validate=True),
                _mode_signed_bytes(
                    deployment_id, proof["resource_id"], proof["mode"], after
                ),
            )
        except (InvalidSignature, ValueError, TypeError, OSError, contracts.ContractError):
            _fail("binding-violation", "an unsigned post-write attestation is not accepted")
        proofs.append(
            {
                "kind": "signed-attestation",
                "deployment_id": deployment_id,
                "resource_id": proof["resource_id"],
                "mode": proof["mode"],
                "after": {"type": after.get("type"), "checksum": after.get("checksum")},
                "signature": proof["signature"],
            }
        )
    return proofs


def verify_migration(
    manifest_path: Path,
    apply_receipt_path: Path,
    deployment_evidence_path: Path,
    *,
    post_write_attestation: Path | None = None,
) -> tuple[dict[str, Any], int]:
    """Read-only acceptance of one migrated batch; returns (envelope, exit_code).

    Hard input, binding, stale-context or preservation violations raise a
    sanitized ContractError (2 = input/conflict, 3 = digest/preservation).
    Per-project acceptance outcomes are recorded independently in a sealed
    verification bound to the manifest, the apply receipt and the deployment
    evidence raw bytes; nothing is written and no receipt is discovered.
    """
    manifest_path = Path(manifest_path)
    manifest, manifest_raw = migration._private_document(manifest_path, "manifest")
    apply_document, apply_raw = migration._private_document(
        Path(apply_receipt_path), "apply_receipt"
    )
    deployment, deployment_raw = migration._private_document(
        Path(deployment_evidence_path), "deployment_evidence"
    )
    documents = {"apply_receipt": apply_document, "deployment_evidence": deployment}
    raw_documents = {
        "manifest": manifest_raw,
        "apply_receipt": apply_raw,
        "deployment_evidence": deployment_raw,
    }
    contracts.validate_declared_bindings(manifest, documents, raw_documents)
    legacy_ops = migration._legacy_deploy_operations(manifest)
    contracts._bind_success_gate(deployment, {"succeeded"})
    legacy_by_id = {operation["resource_id"]: operation for operation in legacy_ops}
    legacy_records: list[dict[str, Any]] = []
    seen_legacy: set[str] = set()
    migration._validate_context(
        manifest_path,
        manifest,
        previous=apply_document,
        deployment=deployment,
        readonly_legacy=True,
    )
    migration._check_source_backups(manifest)
    stage_results = {
        "apply": migration._result_index(apply_document),
        "deploy": migration._result_index(deployment),
    }
    migration._check_stage_backups(stage_results)
    if legacy_ops:
        route_drift = _check_approved_routing(manifest, collect=True)
    else:
        _check_approved_routing(manifest)
        route_drift = set()

    epoch_started = None
    if deployment["payload"].get("previous_deployment_id") is not None:
        epoch_started = apply_document["payload"]["finished_at"]

    payload = manifest["payload"]
    track_freshness = (
        deployment["payload"].get("reconciliation") is not None
        or payload.get("followup") is not None
    )
    observed_states: dict[str, Mapping[str, Any]] = {}
    private, shared, dependents, identity = contracts._declared_resources(payload)
    publications = {
        item["target_path"]: item["candidate_ref"]["state"]
        for item in payload["publication_decisions"]["items"]
        if item["decision"] != "private-only"
    }
    requirements = {
        (operation["phase"], operation["resource_id"]): operation["before_requirement"]
        for operation in migration._operations(manifest)
    }

    deployment_id = deployment["deployment_id"]
    proofs = _load_post_write_attestation(post_write_attestation, deployment_id)
    failed_roots: set[str] = set()
    blocked_roots: set[str] = set()
    for project in deployment["payload"]["projects"]:
        try:
            validate_deployment_reports(
                deployment["payload"],
                project,
                epoch_started=epoch_started,
                context_paths=(manifest_path, Path(apply_receipt_path)),
                verified_manifest=manifest,
            )
        except contracts.ContractError as error:
            if error.code == "validator-unavailable":
                raise
            failed_roots.add(project["root"])
        except OSError:
            failed_roots.add(project["root"])

    cleanup_dependents: dict[str, set[str]] = {}
    for operation in payload["shared_operations"]:
        if operation["phase"] == "cleanup":
            cleanup_dependents.setdefault(operation["resource_id"], set()).update(
                operation["dependent_projects"]
            )
    shared_candidates: list[dict[str, Any]] = []
    for rid in sorted(shared, key=lambda item: identity[item][1]):
        phases = shared[rid]
        if "cleanup" not in phases:
            continue
        owner_kind, target = identity[rid]
        expected_type = "directory" if owner_kind == "directory" else "file"
        try:
            state = snapshot(Path(target))
            expected = contracts._expected_before(
                requirements[("cleanup", rid)], stage_results
            )
        except (contracts.ContractError, OSError, RuntimeError):
            blocked_roots.update(cleanup_dependents[rid])
            continue
        if track_freshness:
            observed_states[target] = state
        shared_candidates.append(
            {
                "resource_id": rid,
                "operation_ids": sorted(phases["cleanup"]),
                "target": target,
                "state": state,
                "dependent_projects": sorted(cleanup_dependents[rid]),
            }
        )
        if state["type"] not in {"absent", expected_type} or (
            expected is not None and state != expected
        ):
            failed_roots.update(cleanup_dependents[rid])

    projects: list[dict[str, Any]] = []
    for manifest_project in payload["projects"]:
        root = manifest_project["root"]
        drift = root in failed_roots or any(
            Path(target) == Path(root) or Path(target).is_relative_to(Path(root))
            for target in route_drift
        )
        blocked = root in blocked_roots
        project_rows: list[dict[str, Any]] = []
        retained_assets: list[dict[str, Any]] = []
        cleanup_candidates: list[dict[str, Any]] = []
        retained_resources = {
            rid: phases
            for rid, phases in private.get(root, {}).items()
            if "cleanup" not in phases or identity[rid][1] in publications
        }
        retained_resources.update(
            {
                rid: phases
                for rid, phases in shared.items()
                if root in dependents.get(rid, set())
                and ("cleanup" not in phases or identity[rid][1] in publications)
            }
        )
        for rid in sorted(retained_resources, key=lambda item: identity[item][1]):
            phases = retained_resources[rid]
            owner_kind, target = identity[rid]
            expected_type = "directory" if owner_kind == "directory" else "file"
            try:
                state = snapshot(Path(target))
            except (contracts.ContractError, OSError, RuntimeError):
                state = None
            if state is not None:
                if track_freshness:
                    observed_states[target] = state
                if state["type"] != "absent":
                    retained_assets.append({"path": target, "state": state})
                if target in publications and state != publications[target]:
                    drift = True
            elif rid not in legacy_by_id:
                blocked = True
                continue
            last_phase = max(
                (phase for phase in phases if phase != "cleanup"),
                key=contracts._PHASE_ORDER.__getitem__, default=None,
            )
            result = stage_results.get(last_phase, {}).get(rid)
            if rid in legacy_by_id:
                record = _classify_legacy_resource(
                    legacy_by_id[rid], result, state, proofs, deployment_id
                )
                if rid not in seen_legacy:
                    legacy_records.append(record)
                    seen_legacy.add(rid)
                project_rows.append(record)
                if record["status"] == "drifted":
                    drift = True
                continue
            if (
                state["type"] not in {"absent", expected_type}
                or result is None
                or result["status"] != "succeeded"
                or result["after"] != state
            ):
                drift = True
        declared_cleanup = {
            rid: phases["cleanup"]
            for rid, phases in private.get(root, {}).items()
            if "cleanup" in phases
        }
        for rid in sorted(declared_cleanup, key=lambda item: identity[item][1]):
            owner_kind, target = identity[rid]
            expected_type = "directory" if owner_kind == "directory" else "file"
            try:
                state = snapshot(Path(target))
                expected = contracts._expected_before(
                    requirements[("cleanup", rid)], stage_results
                )
            except (contracts.ContractError, OSError, RuntimeError):
                blocked = True
                continue
            if track_freshness:
                observed_states[target] = state
            cleanup_candidates.append(
                {
                    "resource_id": rid,
                    "operation_ids": sorted(declared_cleanup[rid]),
                    "target": target,
                    "state": state,
                    "dependent_projects": [root],
                }
            )
            if state["type"] not in {"absent", expected_type} or (
                expected is not None and state != expected
            ):
                drift = True
        if drift:
            status = "failed"
        elif blocked:
            status = "blocked"
        elif legacy_ops:
            status = "not-verified"
        else:
            status = "verified"
        if legacy_ops:
            parts = [row["reason"] for row in project_rows]
            reason = " ".join(parts) if parts else _PROJECT_OUTCOME[status][0]
            if (
                status == "not-verified"
                and project_rows
                and all(row["status"] == "verified" for row in project_rows)
            ):
                reason += " Matching historical Graft evidence does not authorize a write."
            next_step = _NO_WRITE
        else:
            reason, next_step = _PROJECT_OUTCOME[status]
        projects.append(
            {
                "root": root,
                "source_ref": manifest_project["source_ref"],
                "head": manifest_project["head"],
                "status": status,
                "reason": reason,
                "nextStep": next_step,
                "retained_assets": retained_assets,
                "cleanup_candidates": cleanup_candidates,
            }
        )

    status = contracts._aggregate(
        [project["status"] for project in projects],
        ("failed", "not-verified", "blocked"),
        "verified",
        None,
    )
    verification_payload: dict[str, Any] = {
        "manifest_id": manifest["manifest_id"],
        "apply_id": apply_document["apply_id"],
        "deployment_evidence_hash": hashlib.sha256(
            bytes(deployment_raw)
        ).hexdigest(),
        "status": status,
        "projects": projects,
        "shared_cleanup_candidates": shared_candidates,
        "verified_at": _now(),
    }
    if legacy_records:
        verification_payload["legacy_resources"] = legacy_records
    if deployment["payload"].get("reconciliation") is not None:
        # The bound evidence is a provenance-marked current-state observation
        # of an interrupted deployment, not an executed-origin receipt; expose
        # that acceptance basis explicitly so downstream consumers and the
        # contract binding cannot mistake it for observed historical success.
        verification_payload["acceptance_basis"] = "current-state"
    verification = contracts.seal_document("verification", verification_payload)
    contracts.validate_declared_bindings(
        manifest, {**documents, "verification": verification}, raw_documents
    )
    if status in {"not-verified", "failed", "blocked"}:
        joined = " ".join(
            project["reason"] for project in projects if project["reason"].strip()
        )
        fallback, next_step = _VERIFY_OUTCOME[status]
        reason = joined or fallback
    else:
        reason, next_step = _VERIFY_OUTCOME[status]
    envelope = contracts.make_envelope(
        "migration",
        "verify",
        status,
        migration._summary_projects(verification),
        reason,
        next_step,
        verification,
        {
            "manifest_id": manifest["manifest_id"],
            "verification_id": verification["verification_id"],
        },
    )
    provenance = migration._require_reconciliation_provenance(manifest, deployment)
    if status == "verified" and track_freshness:
        for project in payload["projects"]:
            no_touch = project.get("agents_no_touch")
            if no_touch is not None:
                provenance += (no_touch["target"], no_touch["template"])
        # Refresh the same observed states, including absent resources, after
        # all semantic/lineage work. Previously failed outcomes stay unchanged.
        migration._check_source_backups(manifest)
        migration._check_stage_backups(stage_results)
        for target, state in observed_states.items():
            migration._check_reference({"path": target, "state": state})
        for project in deployment["payload"]["projects"]:
            for reference in project["report_refs"]:
                migration._check_reference(reference)
    for reference in provenance:
        migration._check_reference(reference)
    return envelope, _VERIFY_EXIT[status]
