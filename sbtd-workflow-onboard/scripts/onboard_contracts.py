"""Strict codec and semantic contracts for SBTD Onboard v1 exchange objects.

Boundary (docs/prd/sbtd-workflow-v2-onboard-contracts.md, main PRD section 10.2):

- Pure functions over caller-provided Python values and raw bytes. This module
  never reads ``object_ref`` targets, never scans directories, never performs
  network or mutation, and never infers that a stage whose document was not
  supplied was unexecuted.
- Schema validity, canonical IDs and declared bindings prove structure and
  declared relationships only. They are not filesystem safety, authorization,
  execution or smoke proof; runtime producers own those checks.
- ``jsonschema`` is imported lazily inside the validation path so that module
  import, pure argument parsing and the existing CLI keep working without the
  dependency. Missing ``jsonschema`` fails closed with a clear ContractError;
  there is no fallback weak validator.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

SCHEMA_VERSION = 1
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "onboard-contracts.schema.json"
SCHEMA_ID = "urn:sbtd:onboard-contracts:schema:1"

# kind -> (schema $def name, payload digest key or None)
_DOCUMENT_KINDS: dict[str, tuple[str, str | None]] = {
    "publication_decisions": ("publication_decisions", None),
    "manifest": ("manifest", "manifest_id"),
    "apply_receipt": ("apply_receipt", "apply_id"),
    "verification": ("verification", "verification_id"),
    "cleanup_receipt": ("cleanup_receipt", "cleanup_id"),
    "deployment_evidence": ("deployment_evidence", "deployment_id"),
    "recovery_plan": ("recovery_plan", "plan_id"),
    "recovery_receipt": ("recovery_receipt", "receipt_id"),
    "migration_envelope": ("migration_envelope", None),
    "recovery_envelope": ("recovery_envelope", None),
}

_STAGE_RECEIPT_PHASES = {
    "apply_receipt": "apply",
    "deployment_evidence": "deploy",
    "cleanup_receipt": "cleanup",
}
_PHASE_RECEIPTS = {phase: kind for kind, phase in _STAGE_RECEIPT_PHASES.items()}

_PHASE_ORDER = {"apply": 0, "deploy": 1, "cleanup": 2}
_INVERSE_PHASE_ORDER = {"cleanup": 0, "deploy": 1, "apply": 2}

_BINDABLE_KINDS = frozenset(
    {
        "apply_receipt",
        "verification",
        "cleanup_receipt",
        "deployment_evidence",
        "recovery_plan",
        "recovery_receipt",
    }
)
_RAW_KINDS = frozenset({"manifest"} | _BINDABLE_KINDS)

_CUMULATIVE_KINDS: dict[str, tuple[str, str]] = {
    "apply_receipt": ("apply_id", "previous_receipt_id"),
    "cleanup_receipt": ("cleanup_id", "previous_receipt_id"),
    "deployment_evidence": ("deployment_id", "previous_deployment_id"),
    "recovery_receipt": ("receipt_id", "previous_receipt_id"),
}

# Retired public Trellis report fields (PRD section 10.2 cutover). The JSON
# writer refuses them instead of silently aliasing them to new names.
_RETIRED_TOP_LEVEL_KEYS = frozenset({"trellis", "trellisInit", "trellisProjectSetup"})

_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)

_ENVELOPE_PROJECT_STATUSES = {
    ("migration", "plan"): frozenset({"planned", "blocked", "failed"}),
    ("migration", "apply"): frozenset(
        {"applied", "already-complete", "blocked", "failed"}
    ),
    ("migration", "verify"): frozenset({"verified", "blocked", "failed"}),
    ("migration", "cleanup"): frozenset(
        {"cleaned", "already-complete", "blocked", "failed"}
    ),
    ("recovery", "plan"): frozenset({"planned", "blocked", "failed"}),
    ("recovery", "apply"): frozenset(
        {"restored", "already-complete", "blocked", "failed"}
    ),
}

# (mode, phase) -> (artifact holder field, artifact key, artifact document kind)
_ENVELOPE_ARTIFACT = {
    ("migration", "plan"): ("migration", "manifest", "manifest"),
    ("migration", "apply"): ("migration", "apply_receipt", "apply_receipt"),
    ("migration", "verify"): ("migration", "verification", "verification"),
    ("migration", "cleanup"): ("migration", "cleanup_receipt", "cleanup_receipt"),
    ("recovery", "plan"): ("recovery", "plan", "recovery_plan"),
    ("recovery", "apply"): ("recovery", "receipt", "recovery_receipt"),
}

_ENVELOPE_IDENTIFIER_KEYS = {
    "migration": frozenset({"manifest_id", "verification_id"}),
    "recovery": frozenset({"manifest_id", "plan_id", "receipt_id"}),
}

_STAGE_SUCCESS_STATUSES = {
    "apply": frozenset({"applied", "already-complete"}),
    "deploy": frozenset({"succeeded"}),
    "cleanup": frozenset({"cleaned", "already-complete"}),
}

__all__ = [
    "ContractError",
    "canonical_json_bytes",
    "load_document",
    "make_envelope",
    "operation_id",
    "recovery_step_id",
    "resource_id",
    "seal_document",
    "validate_cumulative",
    "validate_declared_bindings",
    "validate_deployment_result",
    "validate_document",
    "write_json_response",
]


class ContractError(Exception):
    """Sanitized contract failure.

    ``message`` names the fixed rule that failed and never echoes rejected
    values, raw jsonschema messages or private digests. ``code`` is a stable
    machine token; ``exit_code`` follows the PRD migration semantics
    (2 = invalid input or state conflict, 3 = digest/preservation failure).
    """

    def __init__(self, code: str, message: str, *, exit_code: int = 2) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code


# ---------------------------------------------------------------------------
# Canonical serialization and stable identifiers
# ---------------------------------------------------------------------------


def canonical_json_bytes(value: Any) -> bytes:
    """UTF-8 canonical JSON: sorted keys, compact separators, no ASCII escaping."""
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ContractError(
            "non-json-value", "value cannot be serialized as canonical contract JSON"
        ) from error
    try:
        return text.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ContractError(
            "malformed-unicode", "value contains unpaired Unicode surrogates"
        ) from error


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _raw_digest(raw: bytes | bytearray) -> str:
    return hashlib.sha256(bytes(raw)).hexdigest()


def resource_id(owner_kind: str, target: str) -> str:
    """SHA-256 of the canonical JSON array [owner_kind, normalized_target_path]."""
    _require_strings(("owner_kind", owner_kind), ("target", target))
    return _digest([owner_kind, target])


def operation_id(phase: str, resource: str, selector: str) -> str:
    """SHA-256 of the canonical JSON array [phase, resource_id, selector]."""
    _require_strings(
        ("phase", phase), ("resource_id", resource), ("selector", selector)
    )
    return _digest([phase, resource, selector])


def recovery_step_id(manifest: str, phase: str, resource: str) -> str:
    """SHA-256 of ["recovery", manifest_id, phase, resource_id]; stable per resource/phase."""
    _require_strings(
        ("manifest_id", manifest), ("phase", phase), ("resource_id", resource)
    )
    return _digest(["recovery", manifest, phase, resource])


def _require_strings(*pairs: tuple[str, Any]) -> None:
    for name, value in pairs:
        if not isinstance(value, str):
            raise ContractError("invalid-argument", f"{name} must be a string")


# ---------------------------------------------------------------------------
# Strict decoding
# ---------------------------------------------------------------------------


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("duplicate-key", "JSON object contains a duplicate key")
        result[key] = value
    return result


def _parse_number(text: str) -> int:
    # Contract v1 defines integers only; any non-integer JSON number literal is
    # a wrong type, and non-finite results are rejected outright.
    value = float(text)
    if not math.isfinite(value):
        raise ContractError("non-finite-number", "JSON number is not finite")
    raise ContractError(
        "unexpected-type", "contract v1 documents do not allow non-integer numbers"
    )


def _reject_constant(text: str) -> Any:
    raise ContractError("non-finite-number", "JSON literal is not a finite number")


def _decode_strict(raw: bytes | bytearray | str) -> Any:
    if isinstance(raw, (bytes, bytearray)):
        try:
            text = bytes(raw).decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise ContractError(
                "invalid-utf8", "document is not strict UTF-8"
            ) from error
    elif isinstance(raw, str):
        text = raw
    else:
        raise ContractError("unexpected-type", "raw document must be bytes or str")
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=_parse_number,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as error:
        raise ContractError(
            "invalid-json", "document is not well-formed JSON"
        ) from error


def _check_json_safe(value: Any, *, allow_numbers: bool = False) -> None:
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ContractError(
                "non-finite-number", "value contains a non-finite number"
            )
        if not allow_numbers:
            raise ContractError(
                "unexpected-type",
                "contract v1 documents do not allow non-integer numbers",
            )
        return
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ContractError(
                "malformed-unicode", "value contains unpaired Unicode surrogates"
            ) from error
        return
    if isinstance(value, list):
        for item in value:
            _check_json_safe(item, allow_numbers=allow_numbers)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ContractError(
                    "unexpected-type", "JSON object keys must be strings"
                )
            _check_json_safe(key, allow_numbers=allow_numbers)
            _check_json_safe(item, allow_numbers=allow_numbers)
        return
    raise ContractError(
        "unexpected-type", "value is not representable as contract JSON"
    )


# ---------------------------------------------------------------------------
# Lazy jsonschema validator with real format checks
# ---------------------------------------------------------------------------

_VALIDATOR: Any = None


def _is_timestamp(value: object) -> bool:
    if not isinstance(value, str):
        return True
    if not _TIMESTAMP_RE.match(value):
        raise ValueError("timestamp must be RFC 3339 with seconds and a timezone")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must carry a timezone offset")
    return True


def _is_normalized_absolute_path(value: object) -> bool:
    if not isinstance(value, str):
        return True
    if not value or "\x00" in value:
        raise ValueError("path must be non-empty and NUL-free")
    if not os.path.isabs(value):
        raise ValueError("path must be absolute")
    if os.path.normpath(value) != value:
        raise ValueError("path must be normalized")
    return True


def _contract_validator() -> Any:
    global _VALIDATOR
    if _VALIDATOR is not None:
        return _VALIDATOR
    try:
        import jsonschema
    except ImportError as error:
        raise ContractError(
            "validator-unavailable",
            "contract validation requires jsonschema; "
            "install sbtd-workflow-onboard/requirements.txt",
        ) from error
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(
            "schema-unavailable",
            "onboard contract schema is missing or unreadable next to the module",
        ) from error
    format_checker = jsonschema.FormatChecker()
    format_checker.checks("date-time", raises=ValueError)(_is_timestamp)
    format_checker.checks("normalized-absolute-path", raises=ValueError)(
        _is_normalized_absolute_path
    )
    jsonschema.Draft202012Validator.check_schema(schema)
    _VALIDATOR = jsonschema.Draft202012Validator(schema, format_checker=format_checker)
    return _VALIDATOR


def _schema_validate(value: Any, def_name: str, kind: str) -> None:
    validator = _contract_validator()
    evolved = validator.evolve(schema={"$ref": f"{SCHEMA_ID}#/$defs/{def_name}"})
    error = next(evolved.iter_errors(value), None)
    if error is not None:
        location = "$"
        for part in error.absolute_path:
            location += f".{part}" if isinstance(part, str) else f"[{part}]"
        raise ContractError(
            "schema-violation", f"{kind} violates the contract schema at {location}"
        )


# ---------------------------------------------------------------------------
# Semantic invariant helpers
# ---------------------------------------------------------------------------


def _fail(code: str, message: str, *, exit_code: int = 2) -> NoReturn:
    raise ContractError(code, message, exit_code=exit_code)


def _path_contains(parent: str, child: str) -> bool:
    return Path(child).is_relative_to(Path(parent))


def _check_publication_items(items: list[dict[str, Any]]) -> None:
    seen_ids: set[str] = set()
    targets: list[str] = []
    for item in items:
        if item["item_id"] in seen_ids:
            _fail("semantic-violation", "duplicate publication item_id")
        seen_ids.add(item["item_id"])
        expected_scope = {
            "sources": item["sources"],
            "target_path": item["target_path"],
            "decision": item["decision"],
            "candidate_ref": item["candidate_ref"],
        }
        if item["approval"]["scope"] != expected_scope:
            _fail(
                "semantic-violation",
                "approval.scope is not an exact snapshot of the declared item fields",
            )
        source_paths = [source["path"] for source in item["sources"]]
        if len(set(source_paths)) != len(source_paths):
            _fail(
                "semantic-violation",
                "duplicate source path within one publication item",
            )
        if item["decision"] == "private-only":
            if item["required"]:
                _fail(
                    "semantic-violation", "required publication cannot be private-only"
                )
            if item["target_path"] is not None or item["candidate_ref"] is not None:
                _fail(
                    "semantic-violation",
                    "private-only items must keep target_path and candidate_ref null",
                )
        elif item["target_path"] is not None:
            targets.append(item["target_path"])
    target_paths = {Path(target) for target in targets}
    if len(target_paths) != len(targets):
        _fail("semantic-violation", "duplicate publication target_path")
    for target in target_paths:
        if any(parent in target_paths for parent in target.parents):
            _fail(
                "semantic-violation",
                "publication target paths overlap lexically (parent/child)",
            )


def _check_operation_ids(operation: Mapping[str, Any]) -> None:
    if operation["resource_id"] != resource_id(
        operation["owner_kind"], operation["target"]
    ):
        _fail(
            "id-mismatch",
            "operation resource_id does not match the canonical owner/target digest",
            exit_code=3,
        )
    if operation["operation_id"] != operation_id(
        operation["phase"], operation["resource_id"], operation["selector"]
    ):
        _fail(
            "id-mismatch",
            "operation_id does not match the canonical phase/resource/selector digest",
            exit_code=3,
        )


def _check_operation(operation: Mapping[str, Any]) -> None:
    _check_operation_ids(operation)
    if operation["dependent_projects"] != sorted(operation["dependent_projects"]):
        _fail("semantic-violation", "operation dependent_projects must be sorted")
    requirement = operation["before_requirement"]
    if requirement["kind"] == "phase-after":
        if requirement["resource_id"] != operation["resource_id"]:
            _fail(
                "semantic-violation",
                "phase-after before_requirement must reference the same resource",
            )
        if _PHASE_ORDER[requirement["phase"]] >= _PHASE_ORDER[operation["phase"]]:
            _fail(
                "semantic-violation",
                "phase-after before_requirement must reference an earlier phase",
            )


def _check_manifest_payload(payload: Mapping[str, Any]) -> None:
    projects = payload["projects"]
    roots = [project["root"] for project in projects]
    if len(set(roots)) != len(roots):
        _fail("semantic-violation", "duplicate project root in manifest")
    root_set = set(roots)
    backup_root = payload["backup_root"]
    for root in roots:
        if _path_contains(root, backup_root) or _path_contains(backup_root, root):
            _fail(
                "semantic-violation",
                "backup_root must be outside the selected projects",
            )
    for item in payload["publication_decisions"]["items"]:
        target = item["target_path"]
        if target is not None and not any(
            _path_contains(root, target) for root in roots
        ):
            _fail(
                "semantic-violation",
                "publication target is outside the selected projects",
            )
        candidate = item["candidate_ref"]
        if candidate is not None and any(
            _path_contains(root, candidate["path"]) for root in roots
        ):
            _fail(
                "semantic-violation",
                "publication candidate must stay outside project roots",
            )

    seen_operation_ids: set[str] = set()
    resource_owners: dict[str, tuple[str, str | None]] = {}
    target_owners: dict[Path, tuple[str, tuple[str, str | None]]] = {}
    phases_by_resource: dict[str, set[str]] = {}
    requirements: dict[tuple[str, str], Mapping[str, Any]] = {}

    def register(operation: Mapping[str, Any], owner: tuple[str, str | None]) -> None:
        _check_operation(operation)
        target = operation["target"]
        if _path_contains(target, backup_root) or _path_contains(backup_root, target):
            _fail("semantic-violation", "backup_root overlaps a managed target")
        identity = (operation["resource_id"], owner)
        if target_owners.setdefault(Path(target), identity) != identity:
            _fail(
                "semantic-violation",
                "one target cannot have conflicting resource owners",
            )
        rid, phase = operation["resource_id"], operation["phase"]
        phases_by_resource.setdefault(rid, set()).add(phase)
        requirement = operation["before_requirement"]
        if requirements.setdefault((rid, phase), requirement) != requirement:
            _fail(
                "semantic-violation", "resource selectors disagree on the before-state"
            )
        if operation["operation_id"] in seen_operation_ids:
            _fail("semantic-violation", "duplicate operation_id in manifest")
        seen_operation_ids.add(operation["operation_id"])
        existing = resource_owners.setdefault(operation["resource_id"], owner)
        if existing != owner:
            _fail(
                "semantic-violation",
                "resource is owned by more than one project or by both private "
                "and shared operation sets",
            )

    for project in projects:
        for operation in project["private_operations"]:
            if not _path_contains(project["root"], operation["target"]):
                _fail("semantic-violation", "private target must belong to its project")
            if operation["dependent_projects"] != [project["root"]]:
                _fail(
                    "semantic-violation",
                    "private operation dependent_projects must be exactly the owning project root",
                )
            register(operation, ("private", project["root"]))
    for operation in payload["shared_operations"]:
        register(operation, ("shared", None))
    for (rid, phase), requirement in requirements.items():
        earlier = [
            prior
            for prior in phases_by_resource[rid]
            if _PHASE_ORDER[prior] < _PHASE_ORDER[phase]
        ]
        if earlier:
            expected = {
                "kind": "phase-after",
                "phase": max(earlier, key=_PHASE_ORDER.__getitem__),
                "resource_id": rid,
            }
            if requirement != expected:
                _fail(
                    "semantic-violation",
                    "resource must follow its latest declared phase",
                )
        elif requirement["kind"] != "state":
            _fail(
                "semantic-violation",
                "initial resource phase needs a concrete before-state",
            )

    shared_by_id = {op["operation_id"]: op for op in payload["shared_operations"]}
    referenced: dict[str, list[str]] = {op_id: [] for op_id in shared_by_id}
    for project in projects:
        for op_id in project["shared_operation_ids"]:
            if op_id not in shared_by_id:
                _fail(
                    "semantic-violation",
                    "project references an unknown shared operation_id",
                )
            referenced[op_id].append(project["root"])
    for op_id, operation in shared_by_id.items():
        if operation["dependent_projects"] != sorted(referenced[op_id]):
            _fail(
                "semantic-violation",
                "shared operation dependent_projects do not match the exact reverse "
                "reference set from projects",
            )

    for shared_root in payload["shared_roots"]:
        if not set(shared_root["dependent_projects"]) <= root_set:
            _fail(
                "semantic-violation",
                "shared_root dependent_projects must reference declared projects",
            )
    for operation in payload["shared_operations"]:
        matching_roots = [
            root
            for root in payload["shared_roots"]
            if _path_contains(root["path"], operation["target"])
        ]
        if len(matching_roots) != 1 or not set(operation["dependent_projects"]) <= set(
            matching_roots[0]["dependent_projects"]
        ):
            _fail(
                "semantic-violation",
                "shared target needs one declared root covering its dependencies",
            )


def _check_original_reference(result: Mapping[str, Any], reference_key: str) -> None:
    before = result["before"]
    reference = result[reference_key]
    if reference is not None and (
        before is None or before["type"] == "absent" or reference["state"] != before
    ):
        _fail(
            "semantic-violation", "original reference must match a known before-state"
        )
    if (
        result["status"] == "succeeded"
        and before["type"] != "absent"
        and reference is None
    ):
        _fail("semantic-violation", "successful write needs its original reference")


def _check_project_dependencies(
    project: Mapping[str, Any], dependencies: list[Mapping[str, Any]]
) -> None:
    severity = {"blocked": 1, "failed": 2}
    if any(
        severity.get(result["status"], 0) > severity.get(project["status"], 0)
        for result in dependencies
    ):
        _fail("semantic-violation", "project status masks a dependent resource failure")


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _check_temporal(payload: Mapping[str, Any]) -> None:
    if _parse_timestamp(payload["started_at"]) > _parse_timestamp(
        payload["finished_at"]
    ):
        _fail("semantic-violation", "started_at must not be after finished_at")


def _aggregate(
    stage_statuses: list[str],
    priority: tuple[str, ...],
    success: str,
    complete: str | None,
) -> str:
    present = set(stage_statuses)
    for status in priority:
        if status in present:
            return status
    if complete is not None and success not in present:
        return complete
    return success


def _check_stage_payload(kind: str, payload: Mapping[str, Any]) -> None:
    phase = _STAGE_RECEIPT_PHASES[kind]
    roots = [project["root"] for project in payload["projects"]]
    if len(set(roots)) != len(roots):
        _fail("semantic-violation", "duplicate project root in stage document")

    shared_ids: set[str] = set()
    seen_shared: set[str] = set()
    for result in payload["shared_results"]:
        if result["phase"] != phase:
            _fail("semantic-violation", f"{kind} results must record phase {phase}")
        if result["resource_id"] in seen_shared:
            _fail("semantic-violation", "duplicate shared result for one resource")
        seen_shared.add(result["resource_id"])
        shared_ids.add(result["resource_id"])
        _check_original_reference(result, "backup_ref")
    for project in payload["projects"]:
        seen_private: set[str] = set()
        for result in project["private_results"]:
            if result["phase"] != phase:
                _fail("semantic-violation", f"{kind} results must record phase {phase}")
            if result["resource_id"] in seen_private:
                _fail("semantic-violation", "duplicate private result for one resource")
            seen_private.add(result["resource_id"])
            _check_original_reference(result, "backup_ref")
        if seen_private & shared_ids:
            _fail(
                "semantic-violation",
                "a resource cannot appear in both private and shared result sets",
            )
        dependencies = [
            *project["private_results"],
            *(
                result
                for result in payload["shared_results"]
                if project["root"] in result["dependent_projects"]
            ),
        ]
        _check_project_dependencies(project, dependencies)

    _check_temporal(payload)
    statuses = [project["status"] for project in payload["projects"]]
    if kind == "apply_receipt":
        expected = _aggregate(
            statuses, ("failed", "blocked"), "applied", "already-complete"
        )
    elif kind == "cleanup_receipt":
        expected = _aggregate(
            statuses, ("failed", "blocked"), "cleaned", "already-complete"
        )
    else:
        expected = _aggregate(
            statuses, ("failed", "blocked", "not-verified"), "succeeded", None
        )
    if payload["status"] != expected:
        _fail(
            "semantic-violation",
            "stage status does not match the priority aggregation of project statuses",
        )


def _check_verification_payload(payload: Mapping[str, Any]) -> None:
    roots = [project["root"] for project in payload["projects"]]
    if len(set(roots)) != len(roots):
        _fail("semantic-violation", "duplicate project root in verification")
    shared_ids: set[str] = set()
    for candidate in payload["shared_cleanup_candidates"]:
        if candidate["resource_id"] in shared_ids:
            _fail("semantic-violation", "duplicate shared cleanup candidate")
        shared_ids.add(candidate["resource_id"])
    for project in payload["projects"]:
        seen: set[str] = set()
        for candidate in project["cleanup_candidates"]:
            if candidate["resource_id"] in seen:
                _fail(
                    "semantic-violation", "duplicate cleanup candidate for one project"
                )
            seen.add(candidate["resource_id"])
        if seen & shared_ids:
            _fail(
                "semantic-violation",
                "a resource cannot be both a private and a shared cleanup candidate",
            )
    statuses = [project["status"] for project in payload["projects"]]
    expected = _aggregate(statuses, ("failed", "blocked"), "verified", None)
    if payload["status"] != expected:
        _fail(
            "semantic-violation",
            "verification status does not match the priority aggregation of project statuses",
        )


def _check_recovery_plan_payload(payload: Mapping[str, Any]) -> None:
    if payload["status"] == "blocked" and not payload["conflicts"]:
        _fail("semantic-violation", "a blocked recovery plan must record its conflicts")
    if payload["status"] == "planned" and payload["conflicts"]:
        _fail("semantic-violation", "a planned recovery plan cannot record conflicts")

    roots = [project["root"] for project in payload["projects"]]
    if len(set(roots)) != len(roots):
        _fail("semantic-violation", "duplicate project root in recovery plan")

    steps = payload["steps"]
    for step in steps:
        if step["expected_current"] == step["restore_to"]:
            _fail("semantic-violation", "recovery step must reverse a state transition")
        if payload["input_evidence"][_PHASE_RECEIPTS[step["phase"]]] is None:
            _fail(
                "semantic-violation",
                "recovery step needs a source-stage evidence reference",
            )
        backup = step["backup_ref"]
        target = step["restore_to"]
        if target["type"] == "absent":
            if backup is not None:
                _fail(
                    "semantic-violation", "absent restore target cannot carry a backup"
                )
        elif backup is None or backup["state"] != target:
            _fail(
                "semantic-violation", "restore target needs a matching original backup"
            )
        if step["step_id"] != recovery_step_id(
            payload["manifest_id"], step["phase"], step["resource_id"]
        ):
            _fail(
                "id-mismatch",
                "recovery step_id does not match the canonical digest",
                exit_code=3,
            )
    inverse_order = [_INVERSE_PHASE_ORDER[step["phase"]] for step in steps]
    if inverse_order != sorted(inverse_order):
        _fail(
            "semantic-violation",
            "recovery steps must be ordered cleanup, then deploy, then apply",
        )

    positions = {step["step_id"]: index for index, step in enumerate(steps)}
    if len(positions) != len(steps):
        _fail("semantic-violation", "duplicate recovery step_id")
    for index, step in enumerate(steps):
        for dependency in step["depends_on"]:
            if dependency not in positions:
                _fail(
                    "semantic-violation", "recovery step depends on an unknown step_id"
                )
            if positions[dependency] >= index:
                _fail(
                    "semantic-violation",
                    "recovery step dependencies must precede the step in inverse order",
                )

    by_resource: dict[str, list[Mapping[str, Any]]] = {}
    for step in steps:
        by_resource.setdefault(step["resource_id"], []).append(step)
    for resource, group in by_resource.items():
        phases = [step["phase"] for step in group]
        if len(set(phases)) != len(phases):
            _fail(
                "semantic-violation",
                "multiple recovery steps for one resource and phase",
            )
        for index in range(1, len(group)):
            current = group[index - 1]
            following = group[index]
            if current["restore_to"] != following["expected_current"]:
                _fail(
                    "semantic-violation",
                    "recovery state chain is broken: restore_to must equal the next "
                    "step's expected_current for the same resource",
                )
            if current["step_id"] not in following["depends_on"]:
                _fail(
                    "semantic-violation",
                    "recovery step must depend on the earlier inverse step of the same resource",
                )

    resources = payload["resources"]
    resource_ids = [entry["resource_id"] for entry in resources]
    if len(set(resource_ids)) != len(resource_ids):
        _fail("semantic-violation", "duplicate resource entry in recovery plan")
    resource_by_id = {entry["resource_id"]: entry for entry in resources}
    for resource, group in by_resource.items():
        entry = resource_by_id.get(resource)
        if entry is None:
            _fail(
                "semantic-violation", "recovery step references an undeclared resource"
            )
        if entry["state"] != group[0]["expected_current"]:
            _fail(
                "semantic-violation",
                "resource snapshot differs from its first inverse step",
            )
        declared_ops = sorted(op for step in group for op in step["operation_ids"])
        if sorted(entry["operation_ids"]) != declared_ops:
            _fail(
                "semantic-violation",
                "recovery resource operation_ids do not match its steps",
            )
        for step in group:
            if set(step["dependent_projects"]) != set(entry["dependent_projects"]):
                _fail(
                    "semantic-violation",
                    "recovery step dependent_projects do not match the resource entry",
                )

    step_op_ids = {op for step in steps for op in step["operation_ids"]}
    declared_shared = set(payload["shared_operation_ids"])
    if not declared_shared <= step_op_ids:
        _fail(
            "semantic-violation",
            "recovery plan shared_operation_ids reference unknown operations",
        )
    for step in steps:
        if (
            len(step["dependent_projects"]) > 1
            and not set(step["operation_ids"]) <= declared_shared
        ):
            _fail(
                "semantic-violation",
                "operations of a multi-project resource must be listed in shared_operation_ids",
            )


def _check_recovery_receipt_payload(payload: Mapping[str, Any]) -> None:
    completed = set(payload["completed_step_ids"])
    pending = set(payload["pending_step_ids"])
    if completed & pending:
        _fail(
            "semantic-violation",
            "recovery step_ids cannot be both completed and pending",
        )

    results = payload["results"]
    result_by_step: dict[str, Mapping[str, Any]] = {}
    for result in results:
        if result["step_id"] in result_by_step:
            _fail("semantic-violation", "duplicate recovery step result")
        result_by_step[result["step_id"]] = result
        if result["step_id"] != recovery_step_id(
            payload["manifest_id"], result["phase"], result["resource_id"]
        ):
            _fail(
                "id-mismatch",
                "recovery result step identity does not match",
                exit_code=3,
            )
        _check_original_reference(result, "protection_ref")
        if result["status"] == "succeeded" and result["step_id"] not in completed:
            _fail("semantic-violation", "a succeeded recovery step must be completed")
    if not set(result_by_step) <= completed | pending:
        _fail(
            "semantic-violation",
            "recovery step result references a step that is neither completed nor pending",
        )
    for step_id in completed:
        result = result_by_step.get(step_id)
        if result is None or result["status"] != "succeeded":
            _fail(
                "semantic-violation",
                "every completed recovery step needs a succeeded result",
            )

    shared_seen: set[str] = set()
    grouped_steps: set[str] = set()
    for shared in payload["shared_results"]:
        if shared["resource_id"] in shared_seen:
            _fail("semantic-violation", "duplicate shared recovery result")
        shared_seen.add(shared["resource_id"])
        for step_id in shared["step_ids"]:
            result = result_by_step.get(step_id)
            if result is None or result["resource_id"] != shared["resource_id"]:
                _fail(
                    "semantic-violation",
                    "shared recovery result references an unknown or foreign step_id",
                )
            if set(result["dependent_projects"]) != set(shared["dependent_projects"]):
                _fail(
                    "semantic-violation",
                    "shared recovery result dependent set does not match its steps",
                )
            grouped_steps.add(step_id)
    for result in results:
        if (
            len(result["dependent_projects"]) > 1
            and result["step_id"] not in grouped_steps
        ):
            _fail(
                "semantic-violation",
                "results of a multi-project resource must be grouped in shared_results",
            )
    if payload["status"] in {"restored", "already-complete"} and (
        pending or any(result["status"] != "succeeded" for result in results)
    ):
        _fail(
            "semantic-violation", "successful recovery cannot retain unfinished steps"
        )
    if payload["runtime_readiness"] == "verified" and not payload["report_refs"]:
        _fail(
            "semantic-violation", "verified runtime readiness needs report references"
        )
    for project in payload["projects"]:
        _check_project_dependencies(
            project,
            [
                result
                for result in results
                if project["root"] in result["dependent_projects"]
            ],
        )

    _check_temporal(payload)
    statuses = [project["status"] for project in payload["projects"]]
    expected = _aggregate(
        statuses, ("failed", "blocked"), "restored", "already-complete"
    )
    if payload["status"] != expected:
        _fail(
            "semantic-violation",
            "recovery status does not match the priority aggregation of project statuses",
        )


def _check_envelope(value: Mapping[str, Any], kind: str) -> None:
    mode = value["mode"]
    phase = value["phase"]
    roots = [project["root"] for project in value["projects"]]
    if len(set(roots)) != len(roots):
        _fail("semantic-violation", "duplicate project root in envelope")
    allowed = _ENVELOPE_PROJECT_STATUSES[(mode, phase)]
    severity = {"blocked": 1, "failed": 2}
    envelope_severity = severity.get(value["status"], 0)
    for project in value["projects"]:
        if project["status"] not in allowed:
            _fail(
                "semantic-violation",
                "envelope project status is not valid for this phase",
            )
        if severity.get(project["status"], 0) > envelope_severity:
            _fail(
                "semantic-violation",
                "envelope status masks a failed or blocked project",
            )

    holder, artifact_key, doc_kind = _ENVELOPE_ARTIFACT[(mode, phase)]
    artifact = value[holder]
    if artifact:
        document = artifact[artifact_key]
        validate_document(document, doc_kind)
        payload = document["payload"]
        if severity.get(payload.get("status"), 0) > envelope_severity:
            _fail("semantic-violation", "envelope status masks its artifact outcome")
        if envelope_severity == 0 and value["status"] != payload.get(
            "status", "planned"
        ):
            _fail(
                "semantic-violation",
                "envelope success variant differs from its artifact",
            )
        if doc_kind == "manifest":
            linked = value["manifest_id"] == document["manifest_id"]
        elif doc_kind == "apply_receipt":
            linked = value["manifest_id"] == payload["manifest_id"]
        elif doc_kind == "verification":
            linked = (
                value["manifest_id"] == payload["manifest_id"]
                and value["verification_id"] == document["verification_id"]
            )
        elif doc_kind == "cleanup_receipt":
            linked = (
                value["manifest_id"] == payload["manifest_id"]
                and value["verification_id"] == payload["verification_id"]
            )
        elif doc_kind == "recovery_plan":
            linked = (
                value["manifest_id"] == payload["manifest_id"]
                and value["plan_id"] == document["plan_id"]
            )
        else:
            linked = (
                value["manifest_id"] == payload["manifest_id"]
                and value["plan_id"] == payload["plan_id"]
                and value["receipt_id"] == document["receipt_id"]
            )
        if not linked:
            _fail(
                "semantic-violation",
                "envelope identifiers do not match the embedded artifact",
            )
        artifact_roots = sorted(project["root"] for project in payload["projects"])
        if sorted(roots) != artifact_roots:
            _fail(
                "semantic-violation",
                "envelope project scope does not match the embedded artifact scope",
            )
        summaries = {project["root"]: project for project in value["projects"]}
        for project in payload["projects"]:
            summary = summaries[project["root"]]
            if (
                project.get("status") is not None
                and severity.get(summary["status"], 0) == 0
                and summary["status"] != project["status"]
            ):
                _fail(
                    "semantic-violation", "project summary changed the success variant"
                )
            if severity.get(project.get("status"), 0) > severity.get(
                summary["status"], 0
            ):
                _fail(
                    "semantic-violation", "project summary masks the artifact's outcome"
                )

    if value["status"] in ("blocked", "failed") and (
        not value["reason"].strip() or not value["nextStep"].strip()
    ):
        _fail(
            "semantic-violation",
            "blocked or failed envelopes must carry an explanatory reason and nextStep",
        )


# ---------------------------------------------------------------------------
# Document validation entry points
# ---------------------------------------------------------------------------


def _kind_info(kind: Any) -> tuple[str, str | None]:
    if not isinstance(kind, str) or kind not in _DOCUMENT_KINDS:
        _fail("unknown-kind", "unknown contract document kind")
    return _DOCUMENT_KINDS[kind]


def validate_document(value: Any, kind: str) -> Any:
    """Schema, semantic-invariant and canonical-ID validation for one document."""
    def_name, id_key = _kind_info(kind)
    if not isinstance(value, dict):
        _fail("unexpected-type", f"{kind} document must be a JSON object")
    _check_json_safe(value)
    _schema_validate(value, def_name, kind)
    record = value.get("payload", value)
    if kind in _CUMULATIVE_KINDS:
        _, previous_key = _CUMULATIVE_KINDS[kind]
        if record[previous_key] is None and (
            record["status"] == "already-complete"
            or any(
                project["status"] == "already-complete"
                for project in record["projects"]
            )
        ):
            _fail("semantic-violation", "already-complete needs a predecessor identity")
    for project in record.get("projects", []):
        if project.get("status") in {"failed", "blocked"} and (
            not project["reason"].strip() or not project["nextStep"].strip()
        ):
            _fail(
                "semantic-violation",
                "failed or blocked projects need a reason and nextStep",
            )
    if kind == "publication_decisions":
        _check_publication_items(value["items"])
    elif kind == "manifest":
        _check_publication_items(value["payload"]["publication_decisions"]["items"])
        _check_manifest_payload(value["payload"])
    elif kind in _STAGE_RECEIPT_PHASES:
        _check_stage_payload(kind, value["payload"])
    elif kind == "verification":
        _check_verification_payload(value["payload"])
    elif kind == "recovery_plan":
        _check_recovery_plan_payload(value["payload"])
    elif kind == "recovery_receipt":
        _check_recovery_receipt_payload(value["payload"])
    else:
        _check_envelope(value, kind)
    if id_key is not None and value[id_key] != _digest(value["payload"]):
        _fail(
            "id-mismatch",
            f"{kind} id does not match the canonical payload digest",
            exit_code=3,
        )
    return value


def load_document(raw: bytes | bytearray | str, kind: str) -> Any:
    """Strict UTF-8 JSON decode followed by full contract validation."""
    _kind_info(kind)
    return validate_document(_decode_strict(raw), kind)


def seal_document(kind: str, payload: Any) -> dict[str, Any]:
    """Wrap a payload as {schema_version, payload, <id>} and validate the result."""
    _, id_key = _kind_info(kind)
    if id_key is None:
        _fail("unknown-kind", f"{kind} documents are not sealed with a payload digest")
    document = {
        "schema_version": SCHEMA_VERSION,
        "payload": payload,
        id_key: _digest(payload),
    }
    validate_document(document, kind)
    return document


# ---------------------------------------------------------------------------
# Declared cross-document bindings
# ---------------------------------------------------------------------------


def _declared_resources(
    payload: Mapping[str, Any],
) -> tuple[
    dict[str, dict[str, dict[str, set[str]]]],
    dict[str, dict[str, set[str]]],
    dict[str, set[str]],
    dict[str, tuple[str, str]],
]:
    """Index manifest operations.

    Returns (private, shared, shared_dependents, resource_identity) where
    private maps root -> resource_id -> phase -> operation_ids, shared maps
    resource_id -> phase -> operation_ids, shared_dependents maps resource_id
    to the dependent project set, and resource_identity maps resource_id to
    (owner_kind, target).
    """
    private: dict[str, dict[str, dict[str, set[str]]]] = {}
    shared: dict[str, dict[str, set[str]]] = {}
    dependents: dict[str, set[str]] = {}
    identity: dict[str, tuple[str, str]] = {}

    def note(operation: Mapping[str, Any]) -> None:
        identity.setdefault(
            operation["resource_id"], (operation["owner_kind"], operation["target"])
        )

    for project in payload["projects"]:
        entry = private.setdefault(project["root"], {})
        for operation in project["private_operations"]:
            entry.setdefault(operation["resource_id"], {}).setdefault(
                operation["phase"], set()
            ).add(operation["operation_id"])
            note(operation)
    for operation in payload["shared_operations"]:
        shared.setdefault(operation["resource_id"], {}).setdefault(
            operation["phase"], set()
        ).add(operation["operation_id"])
        dependents.setdefault(operation["resource_id"], set()).update(
            operation["dependent_projects"]
        )
        note(operation)
    return private, shared, dependents, identity


def _check_raw_hash(kind: str, expected: str, raw_documents: Mapping[str, Any]) -> None:
    raw = raw_documents.get(kind)
    if raw is None:
        return
    if _raw_digest(raw) != expected:
        _fail(
            "binding-violation",
            f"{kind} raw bytes do not match the declared content digest",
            exit_code=3,
        )


def _bind_input_evidence(
    input_evidence: Mapping[str, Any], raw_documents: Mapping[str, Any]
) -> None:
    for key, reference in input_evidence.items():
        raw = raw_documents.get(key)
        if raw is None:
            continue
        if reference is None:
            _fail(
                "binding-violation",
                "raw evidence was supplied for a slot declared null",
            )
        if reference["state"]["checksum"] != _raw_digest(raw):
            _fail(
                "binding-violation",
                "input evidence file digest does not match the supplied raw bytes",
                exit_code=3,
            )


def _expected_before(
    requirement: Mapping[str, Any],
    stage_results: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    if requirement["kind"] == "state":
        return requirement["state"]
    if requirement["phase"] not in stage_results:
        return None
    predecessor = stage_results[requirement["phase"]].get(requirement["resource_id"])
    if predecessor is None or predecessor["after"] is None:
        _fail(
            "binding-violation",
            "supplied predecessor does not prove the required state",
        )
    return predecessor["after"]


def _bind_stage_states(
    requirements: Mapping[tuple[str, str], Mapping[str, Any]],
    stage_results: Mapping[str, Mapping[str, Any]],
) -> None:
    for phase, results in stage_results.items():
        for rid, result in results.items():
            if result["before"] is None:
                continue
            expected = _expected_before(requirements[(phase, rid)], stage_results)
            if expected is not None and result["before"] != expected:
                _fail(
                    "binding-violation",
                    "result before-state differs from its declared requirement",
                )


def _bind_success_gate(
    predecessor: Mapping[str, Any] | None, allowed: set[str]
) -> None:
    if predecessor is not None and predecessor["payload"]["status"] not in allowed:
        _fail(
            "binding-violation", "supplied predecessor did not pass the required phase"
        )


def _bind_stage_receipt(
    manifest_payload: Mapping[str, Any], document: Mapping[str, Any], phase: str
) -> None:
    private, shared, _, _ = _declared_resources(manifest_payload)
    payload = document["payload"]
    manifest_projects = {
        project["root"]: project for project in manifest_payload["projects"]
    }
    if {project["root"] for project in payload["projects"]} != set(manifest_projects):
        _fail(
            "binding-violation",
            "stage document project scope differs from the manifest",
        )

    shared_phase = {
        rid: phases[phase] for rid, phases in shared.items() if phase in phases
    }
    phase_operation_ids = {
        operation_id
        for operations in shared_phase.values()
        for operation_id in operations
    }
    phase_dependents: dict[str, set[str]] = {}
    for operation in manifest_payload["shared_operations"]:
        if operation["phase"] == phase:
            phase_dependents.setdefault(operation["resource_id"], set()).update(
                operation["dependent_projects"]
            )

    observed_shared: dict[str, set[str]] = {}
    for result in payload["shared_results"]:
        rid = result["resource_id"]
        if rid not in shared_phase:
            _fail("binding-violation", "shared result is not declared for this phase")
        if set(result["operation_ids"]) != shared_phase[rid]:
            _fail(
                "binding-violation",
                "shared result operation_ids differ from the manifest",
            )
        if set(result["dependent_projects"]) != phase_dependents[rid]:
            _fail(
                "binding-violation", "shared result dependencies differ from this phase"
            )
        for root in result["dependent_projects"]:
            observed_shared.setdefault(root, set()).update(result["operation_ids"])

    for project in payload["projects"]:
        root = project["root"]
        declared = {
            rid: phases[phase]
            for rid, phases in private.get(root, {}).items()
            if phase in phases
        }
        seen: dict[str, Mapping[str, Any]] = {}
        for result in project["private_results"]:
            rid = result["resource_id"]
            if rid not in declared:
                _fail(
                    "binding-violation",
                    "result references a resource not declared for this project and phase",
                )
            if set(result["operation_ids"]) != declared[rid]:
                _fail(
                    "binding-violation",
                    "private result operation_ids differ from the manifest",
                )
            if set(result["dependent_projects"]) != {root}:
                _fail(
                    "binding-violation",
                    "private result dependencies differ from its project",
                )
            seen[rid] = result

        references = set(project["shared_operation_ids"])
        if references != observed_shared.get(root, set()):
            _fail(
                "binding-violation",
                "project references do not match observed shared results",
            )
        completed = project["status"] in _STAGE_SUCCESS_STATUSES[phase] or (
            phase == "deploy" and project["status"] == "not-verified"
        )
        if not completed:
            continue
        if any(
            project[field] != manifest_projects[root][field]
            for field in ("source_ref", "head")
        ):
            _fail(
                "binding-violation",
                "completed project revision differs from its manifest",
            )
        expected_shared = (
            set(manifest_projects[root]["shared_operation_ids"]) & phase_operation_ids
        )
        if references != expected_shared:
            _fail(
                "binding-violation",
                "completed project is missing a declared shared result",
            )
        for rid in declared:
            result = seen.get(rid)
            if result is None or result["status"] != "succeeded":
                _fail(
                    "binding-violation",
                    "a completed project must record every declared private resource",
                )


def _bind_verification(
    manifest_payload: Mapping[str, Any],
    document: Mapping[str, Any],
    apply_document: Mapping[str, Any] | None,
    requirements: Mapping[tuple[str, str], Mapping[str, Any]],
    stage_results: Mapping[str, Mapping[str, Any]],
    raw_documents: Mapping[str, Any],
) -> None:
    private, shared, dependents, identity = _declared_resources(manifest_payload)
    payload = document["payload"]
    if apply_document is not None and payload["apply_id"] != apply_document["apply_id"]:
        _fail(
            "binding-violation",
            "verification apply_id does not match the apply receipt",
        )
    _check_raw_hash(
        "deployment_evidence", payload["deployment_evidence_hash"], raw_documents
    )
    manifest_projects = {
        project["root"]: project for project in manifest_payload["projects"]
    }
    if {project["root"] for project in payload["projects"]} != set(manifest_projects):
        _fail(
            "binding-violation", "verification project scope differs from the manifest"
        )

    def check_candidate(
        candidate: Mapping[str, Any],
        declared_ops: set[str],
        declared_deps: set[str],
        verified: bool,
    ) -> None:
        if set(candidate["operation_ids"]) != declared_ops:
            _fail(
                "binding-violation",
                "cleanup candidate operation_ids do not exactly match the declared set",
            )
        if set(candidate["dependent_projects"]) != declared_deps:
            _fail(
                "binding-violation",
                "cleanup candidate dependent_projects do not match the manifest",
            )
        if candidate["target"] != identity[candidate["resource_id"]][1]:
            _fail(
                "binding-violation",
                "cleanup candidate target does not match the manifest resource",
            )
        if verified:
            expected = _expected_before(
                requirements[("cleanup", candidate["resource_id"])], stage_results
            )
            if expected is not None and candidate["state"] != expected:
                _fail(
                    "binding-violation",
                    "verified candidate differs from its predecessor",
                )

    shared_cleanup = {
        rid: phases["cleanup"] for rid, phases in shared.items() if "cleanup" in phases
    }
    covered_shared: set[str] = set()
    for candidate in payload["shared_cleanup_candidates"]:
        rid = candidate["resource_id"]
        if rid not in shared_cleanup:
            _fail(
                "binding-violation",
                "shared cleanup candidate is not a declared shared cleanup resource",
            )
        verified = any(
            project["status"] == "verified"
            and project["root"] in dependents.get(rid, set())
            for project in payload["projects"]
        )
        check_candidate(
            candidate, shared_cleanup[rid], dependents.get(rid, set()), verified
        )
        covered_shared.add(rid)

    for project in payload["projects"]:
        root = project["root"]
        if project["status"] == "verified" and any(
            project[field] != manifest_projects[root][field]
            for field in ("source_ref", "head")
        ):
            _fail(
                "binding-violation",
                "verified project revision differs from its manifest",
            )
        declared = {
            rid: phases["cleanup"]
            for rid, phases in private.get(root, {}).items()
            if "cleanup" in phases
        }
        covered: set[str] = set()
        for candidate in project["cleanup_candidates"]:
            rid = candidate["resource_id"]
            if rid not in declared:
                _fail(
                    "binding-violation",
                    "cleanup candidate is not a declared cleanup resource for this project",
                )
            check_candidate(
                candidate, declared[rid], {root}, project["status"] == "verified"
            )
            covered.add(rid)
        if project["status"] == "verified" and covered != set(declared):
            _fail(
                "binding-violation",
                "a verified record must enumerate every declared cleanup candidate",
            )
        if project["status"] == "verified" and any(
            root in dependents.get(rid, set()) and rid not in covered_shared
            for rid in shared_cleanup
        ):
            _fail(
                "binding-violation",
                "verified project is missing a shared cleanup candidate",
            )
    if payload["status"] == "verified" and covered_shared != set(shared_cleanup):
        _fail(
            "binding-violation",
            "a verified record must enumerate every declared shared cleanup candidate",
        )


def _bind_recovery_plan(
    manifest_payload: Mapping[str, Any],
    document: Mapping[str, Any],
    stage_results: Mapping[str, Mapping[str, Any]],
) -> None:
    private, shared, dependents, identity = _declared_resources(manifest_payload)
    for root, resources in private.items():
        for resource in resources:
            dependents[resource] = {root}
    payload = document["payload"]
    manifest_roots = {project["root"] for project in manifest_payload["projects"]}
    selected = {project["root"] for project in payload["projects"]}
    if not selected <= manifest_roots:
        _fail(
            "binding-violation",
            "recovery plan selects projects outside the manifest batch",
        )

    all_ops: dict[str, dict[str, set[str]]] = {}
    for phases in private.values():
        for rid, phase_ops in phases.items():
            for phase, op_ids in phase_ops.items():
                all_ops.setdefault(rid, {}).setdefault(phase, set()).update(op_ids)
    for rid, phase_ops in shared.items():
        for phase, op_ids in phase_ops.items():
            all_ops.setdefault(rid, {}).setdefault(phase, set()).update(op_ids)

    for entry in payload["resources"]:
        rid = entry["resource_id"]
        if rid not in all_ops:
            _fail(
                "binding-violation", "recovery resource is not declared in the manifest"
            )
        declared_ops = {op for op_ids in all_ops[rid].values() for op in op_ids}
        if not set(entry["operation_ids"]) <= declared_ops:
            _fail(
                "binding-violation",
                "recovery resource operation_ids do not match the manifest",
            )
        if identity[rid] != (entry["owner_kind"], entry["target"]):
            _fail(
                "binding-violation",
                "recovery resource owner/target does not match the manifest",
            )
        if set(entry["dependent_projects"]) != dependents[rid]:
            _fail(
                "binding-violation",
                "recovery resource dependencies differ from the manifest",
            )
    for step in payload["steps"]:
        rid = step["resource_id"]
        declared = all_ops.get(rid, {}).get(step["phase"])
        if declared is None or set(step["operation_ids"]) != declared:
            _fail(
                "binding-violation",
                "recovery step operation_ids do not match the manifest for its phase",
            )
        result = stage_results.get(step["phase"], {}).get(rid)
        if (
            result is None
            or result["before"] is None
            or result["after"] is None
            or step["expected_current"] != result["after"]
            or step["restore_to"] != result["before"]
            or step["backup_ref"] != result["backup_ref"]
        ):
            _fail(
                "binding-violation",
                "recovery inverse lacks a matching supplied stage result",
            )
    expected_shared = {
        operation_id
        for step in payload["steps"]
        if step["resource_id"] in shared
        for operation_id in step["operation_ids"]
    }
    if set(payload["shared_operation_ids"]) != expected_shared:
        _fail("binding-violation", "recovery plan lost declared shared ownership")
    if payload["status"] == "planned":
        for step in payload["steps"]:
            if not set(step["dependent_projects"]) <= selected:
                _fail(
                    "binding-violation",
                    "a planned recovery must keep the shared dependent-project closure "
                    "inside the selected scope",
                )


def _bind_recovery_receipt(
    document: Mapping[str, Any], plan_document: Mapping[str, Any] | None
) -> None:
    payload = document["payload"]
    if plan_document is None:
        return
    if payload["plan_id"] != plan_document["plan_id"]:
        _fail("binding-violation", "recovery receipt plan_id does not match the plan")
    plan_payload = plan_document["payload"]
    _bind_success_gate(plan_document, {"planned"})
    if {project["root"] for project in payload["projects"]} != {
        project["root"] for project in plan_payload["projects"]
    } or payload["input_evidence"] != plan_payload["input_evidence"]:
        _fail(
            "binding-violation",
            "recovery receipt scope or evidence differs from its plan",
        )
    plan_steps = {step["step_id"]: step for step in plan_document["payload"]["steps"]}
    pending = set(payload["pending_step_ids"])
    for project in payload["projects"]:
        if project["status"] in {"restored", "already-complete"} and any(
            step["step_id"] in pending and project["root"] in step["dependent_projects"]
            for step in plan_steps.values()
        ):
            _fail(
                "binding-violation", "restored project retains dependent pending steps"
            )
    completed = set(payload["completed_step_ids"])
    recorded = completed | pending
    if recorded != set(plan_steps):
        _fail(
            "binding-violation",
            "completed plus pending step_ids must equal the plan's steps",
        )
    if any(
        not set(plan_steps[step_id]["depends_on"]) <= completed for step_id in completed
    ):
        _fail(
            "binding-violation", "completed recovery step has an unfinished dependency"
        )
    for result in payload["results"]:
        step = plan_steps.get(result["step_id"])
        if step is None:
            _fail(
                "binding-violation",
                "recovery result references a step outside the plan",
            )
        if (
            result["resource_id"] != step["resource_id"]
            or result["phase"] != step["phase"]
            or set(result["operation_ids"]) != set(step["operation_ids"])
            or set(result["dependent_projects"]) != set(step["dependent_projects"])
        ):
            _fail(
                "binding-violation",
                "recovery step result does not match the planned step",
            )
        if result["status"] == "succeeded" and (
            result["before"] != step["expected_current"]
            or result["after"] != step["restore_to"]
        ):
            _fail(
                "binding-violation",
                "successful recovery result differs from its planned states",
            )
    shared_operations = set(plan_document["payload"]["shared_operation_ids"])
    expected_groups: dict[str, set[str]] = {}
    for result in payload["results"]:
        if set(result["operation_ids"]) & shared_operations:
            expected_groups.setdefault(result["resource_id"], set()).add(
                result["step_id"]
            )
    actual_groups = {
        result["resource_id"]: set(result["step_ids"])
        for result in payload["shared_results"]
    }
    if actual_groups != expected_groups:
        _fail(
            "binding-violation",
            "recovery results lost declared shared resource grouping",
        )


def validate_declared_bindings(
    manifest: Any,
    documents: Mapping[str, Any],
    raw_documents: Mapping[str, bytes | bytearray] | None = None,
) -> dict[str, Any]:
    """Validate declared bindings between a manifest and supplied stage documents.

    Only caller-provided objects and raw bytes are checked. A supplied recovery
    plan requires the source stage for each inverse step; other absent kinds
    are not inferred as unexecuted. No filesystem reads take place.
    """
    validate_document(manifest, "manifest")
    manifest_payload = manifest["payload"]
    manifest_id = manifest["manifest_id"]
    raw = dict(raw_documents or {})

    supplied: dict[str, Any] = {}
    if not isinstance(documents, Mapping):
        _fail("unexpected-type", "documents must be a mapping of kind to document")
    for kind, document in documents.items():
        if kind not in _BINDABLE_KINDS:
            _fail("unknown-kind", "unsupported document kind for declared bindings")
        supplied[kind] = validate_document(document, kind)
    for kind, blob in raw.items():
        if kind not in _RAW_KINDS:
            _fail("unknown-kind", "unsupported raw document kind")
        if not isinstance(blob, (bytes, bytearray)):
            _fail("unexpected-type", "raw documents must be bytes")
        try:
            decoded = load_document(blob, kind)
        except ContractError:
            raise ContractError(
                "binding-violation",
                "supplied raw bytes do not form a valid bound document",
                exit_code=3,
            ) from None
        expected = manifest if kind == "manifest" else supplied.get(kind)
        if expected is not None and decoded != expected:
            _fail(
                "binding-violation",
                "raw bytes describe a different supplied document",
                exit_code=3,
            )
        if kind != "manifest":
            supplied.setdefault(kind, decoded)

    for kind, document in supplied.items():
        if document["payload"]["manifest_id"] != manifest_id:
            _fail("binding-violation", f"{kind} is not bound to the supplied manifest")

    stage_results = {
        phase: {
            result["resource_id"]: result
            for result in _collect_stage_results(supplied[kind]["payload"]).values()
        }
        for kind, phase in _STAGE_RECEIPT_PHASES.items()
        if kind in supplied
    }
    requirements = {
        (op["phase"], op["resource_id"]): op["before_requirement"]
        for project in manifest_payload["projects"]
        for op in project["private_operations"]
    }
    for operation in manifest_payload["shared_operations"]:
        requirements[(operation["phase"], operation["resource_id"])] = operation[
            "before_requirement"
        ]
    apply_document = supplied.get("apply_receipt")
    if apply_document is not None:
        _bind_stage_receipt(manifest_payload, apply_document, "apply")
    deployment = supplied.get("deployment_evidence")
    if deployment is not None:
        _bind_success_gate(apply_document, {"applied", "already-complete"})
        if apply_document is not None and (
            deployment["payload"]["apply_id"] != apply_document["apply_id"]
        ):
            _fail(
                "binding-violation",
                "deployment evidence apply_id does not match the apply receipt",
            )
        _bind_stage_receipt(manifest_payload, deployment, "deploy")
    verification = supplied.get("verification")
    if verification is not None:
        _bind_success_gate(apply_document, {"applied", "already-complete"})
        _bind_success_gate(deployment, {"succeeded"})
        _bind_verification(
            manifest_payload,
            verification,
            apply_document,
            requirements,
            stage_results,
            raw,
        )
    cleanup = supplied.get("cleanup_receipt")
    if cleanup is not None:
        _bind_success_gate(apply_document, {"applied", "already-complete"})
        _bind_success_gate(deployment, {"succeeded"})
        _bind_success_gate(verification, {"verified"})
        if verification is not None and (
            cleanup["payload"]["verification_id"] != verification["verification_id"]
        ):
            _fail(
                "binding-violation",
                "cleanup receipt verification_id does not match the verification",
            )
        if apply_document is not None and (
            cleanup["payload"]["apply_id"] != apply_document["apply_id"]
        ):
            _fail(
                "binding-violation",
                "cleanup receipt apply_id does not match the apply receipt",
            )
        _check_raw_hash(
            "deployment_evidence",
            cleanup["payload"]["deployment_evidence_hash"],
            raw,
        )
        _bind_stage_receipt(manifest_payload, cleanup, "cleanup")
    _bind_stage_states(requirements, stage_results)
    plan = supplied.get("recovery_plan")
    if plan is not None:
        _bind_recovery_plan(manifest_payload, plan, stage_results)
        _bind_input_evidence(plan["payload"]["input_evidence"], raw)
    receipt = supplied.get("recovery_receipt")
    if receipt is not None:
        _bind_recovery_receipt(receipt, plan)
        _bind_input_evidence(receipt["payload"]["input_evidence"], raw)
    return supplied


# ---------------------------------------------------------------------------
# Cumulative receipt preservation
# ---------------------------------------------------------------------------


def _collect_stage_results(payload: Mapping[str, Any]) -> dict[tuple[str, ...], Any]:
    collected: dict[tuple[str, ...], Any] = {}
    for project in payload["projects"]:
        for result in project["private_results"]:
            collected[
                ("private", project["root"], result["phase"], result["resource_id"])
            ] = result
    for result in payload["shared_results"]:
        collected[("shared", result["phase"], result["resource_id"])] = result
    return collected


def _preserves_original_reference(
    old: Mapping[str, Any], new: Mapping[str, Any], reference_key: str
) -> bool:
    before = old["before"]
    if new["before"] != before:
        return False
    original, replacement = old[reference_key], new[reference_key]
    if original == replacement:
        return True
    # A failed copy may be retried only while the recorded original is untouched.
    if original is not None or replacement is None or before is None:
        return False
    return (
        before["type"] != "absent"
        and old["after"] == before
        and replacement["state"] == before
    )


def validate_cumulative(previous: Any, current: Any, kind: str) -> Any:
    """Prove a retry receipt preserves prior success and original references.

    ``previous=None`` marks a first run: the current document must declare a
    null previous receipt reference. Otherwise the current document must link
    the previous document's ID and carry every previously succeeded result
    forward with its original before/after and backup (or protection) refs.
    """
    if kind not in _CUMULATIVE_KINDS:
        _fail("unknown-kind", "kind does not support cumulative validation")
    id_key, previous_key = _CUMULATIVE_KINDS[kind]
    validate_document(current, kind)
    if previous is None:
        if current["payload"][previous_key] is not None:
            _fail(
                "cumulative-violation",
                "a first-run document must declare a null previous reference",
                exit_code=3,
            )
        return current
    validate_document(previous, kind)
    if current["payload"][previous_key] != previous[id_key]:
        _fail(
            "cumulative-violation",
            "current document does not reference the supplied previous document",
            exit_code=3,
        )
    if current["payload"]["manifest_id"] != previous["payload"]["manifest_id"]:
        _fail(
            "cumulative-violation",
            "cumulative documents are bound to different manifests",
            exit_code=3,
        )

    binding_fields = {
        "apply_receipt": (),
        "deployment_evidence": ("apply_id",),
        "cleanup_receipt": ("apply_id", "verification_id", "deployment_evidence_hash"),
        "recovery_receipt": ("plan_id", "input_evidence"),
    }[kind]
    if any(
        current["payload"][key] != previous["payload"][key] for key in binding_fields
    ):
        _fail(
            "cumulative-violation",
            "retry changed its bound evidence chain",
            exit_code=3,
        )
    if {project["root"] for project in current["payload"]["projects"]} != {
        project["root"] for project in previous["payload"]["projects"]
    }:
        _fail("cumulative-violation", "retry changed its project scope", exit_code=3)

    previous_projects = {
        project["root"]: project for project in previous["payload"]["projects"]
    }
    completed_statuses = {"applied", "cleaned", "restored", "already-complete"}
    if current["payload"]["status"] == "already-complete" and (
        previous["payload"]["status"] not in completed_statuses
    ):
        _fail(
            "cumulative-violation",
            "already-complete requires prior phase success",
            exit_code=3,
        )
    for project in current["payload"]["projects"]:
        if project["status"] == "already-complete" and (
            previous_projects[project["root"]]["status"] not in completed_statuses
        ):
            _fail(
                "cumulative-violation",
                "project completion lacks prior success",
                exit_code=3,
            )

    if kind == "recovery_receipt":
        previous_steps = set(previous["payload"]["completed_step_ids"]) | set(
            previous["payload"]["pending_step_ids"]
        )
        current_steps = set(current["payload"]["completed_step_ids"]) | set(
            current["payload"]["pending_step_ids"]
        )
        if previous_steps != current_steps:
            _fail(
                "cumulative-violation",
                "retry changed the recovery step universe",
                exit_code=3,
            )
        previous_results = {
            result["step_id"]: result for result in previous["payload"]["results"]
        }
        current_results = {
            result["step_id"]: result for result in current["payload"]["results"]
        }
        if not set(previous["payload"]["completed_step_ids"]) <= set(
            current["payload"]["completed_step_ids"]
        ):
            _fail(
                "cumulative-violation",
                "previously completed recovery steps are missing from the retry",
                exit_code=3,
            )
        for step_id, old in previous_results.items():
            new = current_results.get(step_id)
            if new is None or not _preserves_original_reference(
                old, new, "protection_ref"
            ):
                _fail(
                    "cumulative-violation",
                    "a retry lost an original recovery before-state or protection reference",
                    exit_code=3,
                )
            if old["status"] != "succeeded":
                continue
            new = current_results.get(step_id)
            if (
                new is None
                or new["status"] != "succeeded"
                or new["before"] != old["before"]
                or new["after"] != old["after"]
                or new["protection_ref"] != old["protection_ref"]
            ):
                _fail(
                    "cumulative-violation",
                    "a previously succeeded recovery step lost its original result "
                    "or protection reference",
                    exit_code=3,
                )
        return current

    previous_results = _collect_stage_results(previous["payload"])
    current_results = _collect_stage_results(current["payload"])
    for key, old in previous_results.items():
        new = current_results.get(key)
        if new is None or not _preserves_original_reference(old, new, "backup_ref"):
            _fail(
                "cumulative-violation",
                "a retry lost an original before-state or backup reference",
                exit_code=3,
            )
        if old["status"] != "succeeded":
            continue
        new = current_results.get(key)
        if (
            new is None
            or new["status"] != "succeeded"
            or new["before"] != old["before"]
            or new["after"] != old["after"]
            or new["backup_ref"] != old["backup_ref"]
            or set(new["operation_ids"]) != set(old["operation_ids"])
            or set(new["dependent_projects"]) != set(old["dependent_projects"])
        ):
            _fail(
                "cumulative-violation",
                "a previously succeeded result lost its original before/backup state",
                exit_code=3,
            )
    return current


# ---------------------------------------------------------------------------
# Envelopes, deployment results and the single-JSON writer
# ---------------------------------------------------------------------------


def make_envelope(
    mode: str,
    phase: str,
    status: str,
    projects: list[dict[str, Any]],
    reason: str,
    next_step: str,
    artifact: Any = None,
    identifiers: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build and validate a migration or recovery phase envelope.

    ``artifact`` is the stage document (for example the manifest for a
    migration plan phase); it is wrapped under the fixed phase key, or the
    holder stays an empty object. ``identifiers`` carries the honest id fields
    (null when not applicable).
    """
    if mode not in _ENVELOPE_IDENTIFIER_KEYS:
        _fail("unknown-kind", "mode must be migration or recovery")
    if (mode, phase) not in _ENVELOPE_ARTIFACT:
        _fail("unknown-kind", "phase is not valid for this mode")
    supplied = dict(identifiers or {})
    if not set(supplied) <= _ENVELOPE_IDENTIFIER_KEYS[mode]:
        _fail("unknown-kind", "unexpected identifier field for this mode")
    holder, artifact_key, _ = _ENVELOPE_ARTIFACT[(mode, phase)]
    body: dict[str, Any] = {}
    if artifact is not None:
        if not isinstance(artifact, dict):
            _fail("unexpected-type", "artifact must be a contract document")
        body[artifact_key] = artifact
    envelope: dict[str, Any] = {
        "mode": mode,
        "phase": phase,
        "status": status,
        "projects": projects,
        "reason": reason,
        "nextStep": next_step,
        holder: body,
    }
    for key in _ENVELOPE_IDENTIFIER_KEYS[mode]:
        envelope[key] = supplied.get(key)
    kind = "migration_envelope" if mode == "migration" else "recovery_envelope"
    return validate_document(envelope, kind)


def validate_deployment_result(value: Any) -> Any:
    """Validate the init deploymentEvidence field: null or {path, evidence}."""
    if value is None:
        return None
    if not isinstance(value, dict):
        _fail("unexpected-type", "deployment result must be null or an object")
    _check_json_safe(value)
    _schema_validate(value, "deployment_result", "deployment_result")
    validate_document(value["evidence"], "deployment_evidence")
    return value


def write_json_response(value: Any, stream: Any = None) -> str:
    """Validate and emit exactly one JSON root object.

    Fixed migration/recovery phase envelopes are fully validated; retired
    top-level Trellis fields are refused rather than silently aliased. Other
    producer payload bodies keep their own runtime-owned semantics. Returns
    the serialized text.
    """
    if not isinstance(value, dict):
        _fail("unexpected-type", "JSON response must be a single root object")
    retired = _RETIRED_TOP_LEVEL_KEYS & set(value)
    if retired:
        _fail(
            "retired-field",
            "response contains a retired top-level Trellis field; use the current "
            "report fields instead",
        )
    mode = value.get("mode")
    if mode == "migration":
        validate_document(value, "migration_envelope")
    elif mode == "recovery":
        validate_document(value, "recovery_envelope")
    else:
        _check_json_safe(value, allow_numbers=True)
    text = canonical_json_bytes(value).decode("utf-8")
    out = sys.stdout if stream is None else stream
    out.write(text + "\n")
    return text
