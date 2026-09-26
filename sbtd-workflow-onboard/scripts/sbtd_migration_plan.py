"""Read-only batch migration planning and repeatable legacy input validation.

Grounded in Trellis v0.6.17 (commit 833a5846d18ad7a5ccd8c41c876d89cc936f5fd9)
and the main PRD sections 10.2/11 plus the P1-12 migration-runtime decisions:

- ``plan_migration`` is strictly read-only. It never creates the private
  vault, candidates, projects or HOME entries; it verifies the already
  authorized private preparation (exact publication decisions, existing
  share/redact candidates under the verified private vault, current source
  and target states) and seals a bound manifest. Missing, non-private,
  linked or otherwise unproven inputs block the plan with zero writes.
- No candidate is ever generated here and no scan result substitutes human
  approval. A legacy task is either an exact share/redact projection or an
  explicit private-only skip of its whole folder. Spec files are either
  exact share/redact projections or explicit private-only preservation.
  Lessons still require a share/redact projection. A skipped task is not
  published and does not require a handoff. Missing approval still blocks.
- Operations use only the existing contract change kinds. ``apply`` adds
  ignore protection before data writes, extracts the legacy developer name
  into the missing current identity, installs the approved candidates and
  stops managed old routing; it never deploys new wiring or runs smoke.
  ``cleanup`` only retires the legacy project tree and the exact pinned
  v1.0.15 global Skill directories; drifted or unknown global content is
  preserved untouched. No deployment producer targets are declared.
- ``validate_legacy_inputs`` repeats the complete legacy closure against a
  manifest with caller-supplied original bytes, so apply/verify revalidation
  stays sound after controlled rewrites or cleanup of the legacy sources.

Every failure is a sanitized ``ContractError`` naming the fixed rule, never
a rejected private value.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import re
import stat
import subprocess
from collections.abc import Callable, Collection, Mapping, Sequence
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn, cast
from urllib.parse import unquote, urlsplit

import onboard_contracts as contracts
from onboard_contracts import ContractError
from sbtd_identity import DeveloperStore
from sbtd_migration_files import (
    _canonical,
    _lstat,
    directory_snapshot,
    read_file,
    require_private_directory,
    snapshot,
)
from sbtd_migration_legacy import (
    read_legacy_identity,
    validate_projection_graph,
    validate_task_projection,
)

__all__ = ["plan_migration", "validate_legacy_inputs"]

_PACKAGE = Path(__file__).resolve().parents[1]
_IGNORE_ASSET = _PACKAGE / "assets" / "migration-local-ignore.txt"
_PAUSE_ASSET = _PACKAGE / "assets" / "migration-paused-agents.txt"
_OWNERSHIP_ASSET = _PACKAGE / "assets" / "migration-legacy-ownership.json"

_ABSENT = {"type": "absent", "checksum": None}
_LEGACY_DIR = ".trellis"
_LEGACY_VERSION = "0.6.17"
_TASK_JSON = "task.json"
_TASK_DOCUMENT = "task.md"
_TASK_SIDECAR = "legacy-task.json"
_DEVELOPER_NAME = ".developer"
_TEMPLATE_HASHES = ".template-hashes.json"
_VERSION_FILE = ".version"

# Known v0.6.17 layout. Gitignore may hide incidental files outside this
# layout; those stay in the directory snapshot and are deleted with the tree.
# tasks, spec and lessons stay in the approval closure even when ignored.
# A path outside this layout that git does not ignore stops the plan.
_KNOWN_LEGACY_TOP = frozenset(
    {
        _DEVELOPER_NAME,
        _TEMPLATE_HASHES,
        _VERSION_FILE,
        "tasks",
        "spec",
        "lessons",
        "workspace",
        "workflow.md",
        ".gitignore",
        ".current-task",
        ".runtime",
        "config.yaml",
        "scripts",
        "agents",
    }
)
_MANDATORY_TOP = frozenset({"tasks", "spec", "lessons"})
_GENERATED_LEGACY_TOP = frozenset({"workflow.md", "config.yaml", "scripts", "agents"})
_UNSELECTED_PLATFORM_PREFIX = frozenset({".cursor", ".opencode", ".pi"})
_PLATFORM_PREFIX = {
    ".codex": "codex",
    ".agents": "codex",
    ".claude": "claude",
    ".kimi": "kimi",
    ".omp": "oh-my-pi",
}
_ROOT_OWNED_FILES = frozenset({"AGENTS.md"})
_TRELLIS_MARKER = "TRELLIS"

_HEX64 = re.compile(r"[0-9a-f]{64}")
_LESSON_MARKER = re.compile(r"<!-- lessons:[^>]*-->")
_LESSON_ID = re.compile(r"LESSON-\d{8}-[a-z0-9]+-[a-z0-9-]+")
# Obvious secret shapes only; approval, not scanning, is the privacy gate.
_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
)

# (category root inside the legacy directory) -> shared document root.
_DOC_TARGETS = {"spec": ("docs", "spec"), "lessons": ("docs", "lessons")}

ReadOriginal = Callable[[Mapping[str, Any]], bytes]


def _fail(
    code: str,
    message: str,
    *,
    exit_code: int = 2,
    details: Mapping[str, Any] | None = None,
) -> NoReturn:
    raise ContractError(code, message, exit_code=exit_code, details=details)


# ---------------------------------------------------------------------------
# Paths, references and strict JSON
# ---------------------------------------------------------------------------


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("invalid-config", "a structured input repeats a key")
        result[key] = value
    return result


def _json_object(raw: bytes, label: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (ValueError, RecursionError, UnicodeError):
        _fail("invalid-config", f"{label} is not unambiguous JSON")


def _parts_relative(path: Path, root: Path) -> tuple[str, ...] | None:
    try:
        return path.relative_to(root).parts
    except ValueError:
        return None


def _check_safe_relative(value: str, label: str) -> tuple[str, ...]:
    if not isinstance(value, str) or not value or "\\" in value:
        _fail("invalid-config", f"{label} is not a safe relative path")
    parts = PurePosixPath(value).parts
    if (
        not parts
        or PurePosixPath(value).is_absolute()
        or any(part in {"", ".", ".."} for part in parts)
    ):
        _fail("invalid-config", f"{label} is not a safe relative path")
    return parts


def _physical_root(value: Any) -> Path:
    if not isinstance(value, (str, os.PathLike)):
        _fail("invalid-argument", "project roots must be filesystem paths")
    root = Path(value)
    try:
        resolved = root.resolve(strict=True)
    except (OSError, RuntimeError):
        _fail("scope-conflict", "a selected project root cannot be resolved")
    if resolved != root or not root.is_dir():
        _fail(
            "scope-conflict",
            "a selected project is not its recorded physical root",
        )
    return root


def _reference(path: Path) -> dict[str, Any]:
    return {"path": str(path), "state": snapshot(path)}


def _present_file_reference(path: Path, label: str) -> dict[str, Any]:
    reference = _reference(path)
    if reference["state"]["type"] != "file":
        _fail("missing-input", f"{label} is unavailable")
    return reference


def _check_reference_current(reference: Mapping[str, Any], code: str) -> None:
    path = reference.get("path")
    state = reference.get("state")
    if not isinstance(path, str) or not isinstance(state, Mapping):
        _fail(code, "a bound reference is malformed")
    if snapshot(Path(path)) != dict(state):
        _fail(code, "a bound input no longer matches its recorded state")


def _lineage_probe(path: Path) -> str:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return "absent"
    except OSError:
        _fail("read-failed", "a target parent path cannot be inspected")
    if stat.S_ISLNK(info.st_mode):
        _fail("unsafe-path", "a target parent path is a link")
    if stat.S_ISDIR(info.st_mode):
        return "directory"
    if stat.S_ISREG(info.st_mode):
        return "file"
    _fail("unsafe-path", "a target parent path is a special entry")


def _omp_root_presence(path: Path) -> str:
    """Classify only the OMP root. Do not walk children or follow links."""
    checked = _canonical(path)
    info = _lstat(checked)
    if info is None:
        return "absent"
    if stat.S_ISDIR(info.st_mode):
        return "directory"
    if stat.S_ISREG(info.st_mode):
        return "file"
    _fail("unsafe-path", "path is a link or special file, not absent")


def _check_target_lineage(target: Path, root: Path) -> None:
    """Missing parents are fine (apply creates them); existing junk is not."""
    parent = target.parent
    while parent != root:
        if parent == parent.parent:
            _fail("scope-conflict", "a managed target escapes its project")
        if _lineage_probe(parent) == "file":
            _fail("target-conflict", "a target parent path is not a directory")
        parent = parent.parent


# ---------------------------------------------------------------------------
# Private vault, pinned ownership metadata and shared-text privacy gate
# ---------------------------------------------------------------------------


def _private_vault(value: Any) -> Path:
    if not isinstance(value, (str, os.PathLike)):
        _fail("invalid-argument", "the backup root must be a filesystem path")
    return require_private_directory(Path(value))


def _ownership_pins() -> dict[str, Any]:
    document = _json_object(read_file(_OWNERSHIP_ASSET), "the legacy ownership pins")
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        _fail("invalid-config", "the legacy ownership pins are malformed")
    agents = document.get("global_agents_sha256")
    if not isinstance(agents, str) or _HEX64.fullmatch(agents) is None:
        _fail("invalid-config", "the legacy ownership pins are malformed")
    skills = document.get("skills")
    if not isinstance(skills, dict):
        _fail("invalid-config", "the legacy ownership pins are malformed")
    pinned: dict[str, dict[str, Any]] = {}
    for name, pin in skills.items():
        if not isinstance(name, str) or not name or "/" in name or name in {".", ".."}:
            _fail("invalid-config", "the legacy ownership pins are malformed")
        if (
            not isinstance(pin, Mapping)
            or pin.get("type") != "directory"
            or not isinstance(pin.get("checksum"), str)
            or _HEX64.fullmatch(pin["checksum"]) is None
        ):
            _fail("invalid-config", "the legacy ownership pins are malformed")
        pinned[name] = {"type": "directory", "checksum": pin["checksum"]}
    configurations = document.get("project_config_templates")
    if not isinstance(configurations, dict) or not configurations:
        _fail("invalid-config", "the legacy configuration pins are malformed")
    for relative, digests in configurations.items():
        _check_safe_relative(relative, "a pinned configuration path")
        if (
            not isinstance(digests, list)
            or not digests
            or any(
                not isinstance(digest, str) or _HEX64.fullmatch(digest) is None
                for digest in digests
            )
        ):
            _fail("invalid-config", "the legacy configuration pins are malformed")
    return {"agents": agents, "skills": pinned, "project_configs": configurations}


def _private_strings(vault: Path) -> tuple[str, ...]:
    from onboard import user_home

    values = {str(vault), str(user_home())}
    return tuple(sorted(value for value in values if len(value) > 3))


def _check_shared_text(
    data: bytes,
    *,
    private_strings: tuple[str, ...],
    private_digests: set[str],
    check_legacy_layout: bool = True,
    check_digests: bool = True,
) -> None:
    """Refuse obvious private path/hash/secret leaks in shared projections.

    Binary candidates cannot be inspected reliably; they ship only under
    their explicit approval and are never scanned-into-safety here. The
    sidecar records its legacy ``source_path`` and pins ``source_sha256``
    structurally (both validated by the projection contract), so only it
    skips the layout and digest substring scans.
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return
    if check_legacy_layout and _LEGACY_DIR in text:
        _fail(
            "privacy-violation",
            "a shared projection still references the retired legacy layout",
        )
    for needle in private_strings:
        if needle in text:
            _fail("privacy-violation", "a shared projection leaks a private path")
    if check_digests:
        for digest in private_digests:
            if digest in text:
                _fail("privacy-violation", "a shared projection leaks a private digest")
    for pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            _fail("privacy-violation", "a shared projection carries an obvious secret")


def _check_markdown_links(
    data: bytes, target: Path, root: Path, approved_targets: set[Path]
) -> None:
    try:
        from markdown_it import MarkdownIt
    except ImportError:
        _fail(
            "dependency-unavailable",
            "Markdown link validation requires the declared Markdown parser",
        )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return
    parser = MarkdownIt("commonmark")
    safe_link = parser.validateLink
    # Parse unsafe destinations too so the migration gate can reject them;
    # this parser only inspects tokens and never renders or opens a link.
    cast(Any, parser).validateLink = lambda _url: True
    inline_tokens = (
        child for block in parser.parse(text) for child in (block.children or ())
    )
    for token in inline_tokens:
        if token.type not in {"link_open", "image"}:
            continue
        href = token.attrGet("href" if token.type == "link_open" else "src")
        if href is None:
            continue
        if not isinstance(href, str) or not safe_link(href):
            _fail(
                "target-conflict", "a shared Markdown link uses an unsafe destination"
            )
        if re.match(r"^[A-Za-z]:", unquote(href)):
            _fail("target-conflict", "a shared Markdown link cannot name a drive path")
        try:
            parsed = urlsplit(href)
        except ValueError:
            _fail(
                "target-conflict", "a shared Markdown link has an invalid destination"
            )
        if parsed.scheme == "file":
            _fail(
                "target-conflict", "a shared Markdown link cannot name a local file URL"
            )
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        path = unquote(parsed.path)
        if path.startswith("/") or "\\" in path:
            _fail("target-conflict", "a shared Markdown link is not project-relative")
        resolved = Path(os.path.normpath(target.parent / path))
        if not resolved.is_relative_to(root) or resolved not in approved_targets:
            _fail(
                "target-conflict",
                "a shared Markdown link does not resolve to an approved publication",
            )


def _check_lessons_preserved(source_raw: bytes, candidate_raw: bytes) -> None:
    try:
        source_text = source_raw.decode("utf-8")
        candidate_text = candidate_raw.decode("utf-8")
    except UnicodeDecodeError:
        _fail("privacy-unproven", "lessons content cannot be inspected safely")
    needed = set(_LESSON_MARKER.findall(source_text)) | set(
        _LESSON_ID.findall(source_text)
    )
    if any(token not in candidate_text for token in needed):
        _fail(
            "preservation-failure",
            "the approved projection dropped lesson markers or IDs",
        )


# ---------------------------------------------------------------------------
# Candidate byte access (candidates are never rewritten by later phases, so a
# verified state plus a safe read is the original approved bytes)
# ---------------------------------------------------------------------------


def _candidate_files(candidate: Mapping[str, Any]) -> set[str]:
    state, entries = directory_snapshot(Path(candidate["path"]))
    if state != candidate["state"]:
        _fail("state-conflict", "an approved candidate changed after approval")
    return {entry["path"] for entry in entries if entry["type"] == "file"}


def _candidate_bytes(candidate: Mapping[str, Any], member: str | None) -> bytes:
    state = candidate["state"]
    path = Path(candidate["path"])
    if state["type"] == "file":
        if member is not None:
            _fail("candidate-conflict", "a file candidate has no members")
        return read_file(path, state)
    if member is None:
        _fail("candidate-conflict", "a directory candidate needs a member name")
    parts = _check_safe_relative(member, "candidate member")
    if snapshot(path) != state:
        _fail("state-conflict", "an approved candidate changed after approval")
    return read_file(path.joinpath(*parts))


def _approved_target_files(
    closures: Mapping[
        tuple[str, ...], Sequence[tuple[Mapping[str, Any], list[tuple[str, ...]]]]
    ],
    documents: Sequence[tuple[str, Mapping[str, Any], list[tuple[str, ...]]]],
) -> set[Path]:
    targets: set[Path] = set()
    for records in closures.values():
        for item, _rels in records:
            if item["decision"] == "private-only":
                continue
            candidate = item["candidate_ref"]
            target = Path(item["target_path"])
            if candidate["state"]["type"] == "file":
                targets.add(target)
            else:
                targets.update(
                    target / member for member in _candidate_files(candidate)
                )
    for _category, item, _rels in documents:
        if item["decision"] == "private-only":
            continue
        candidate = item["candidate_ref"]
        target = Path(item["target_path"])
        if candidate["state"]["type"] == "file":
            targets.add(target)
        else:
            targets.update(target / member for member in _candidate_files(candidate))
    return targets


# ---------------------------------------------------------------------------
# Publication item classification and closure validation (shared by plan and
# validate; only the source-byte reader differs)
# ---------------------------------------------------------------------------


def _classify_project_items(
    root: Path, items: Sequence[Mapping[str, Any]]
) -> tuple[
    dict[tuple[str, ...], list[tuple[Mapping[str, Any], list[tuple[str, ...]]]]],
    list[tuple[str, Mapping[str, Any], list[tuple[str, ...]]]],
    list[Mapping[str, Any]],
]:
    primaries: dict[
        tuple[str, ...], list[tuple[Mapping[str, Any], list[tuple[str, ...]]]]
    ] = {}
    attachments: list[tuple[Mapping[str, Any], list[tuple[str, ...]]]] = []
    documents: list[tuple[str, Mapping[str, Any], list[tuple[str, ...]]]] = []
    optional: list[Mapping[str, Any]] = []
    handoff_root = root / "docs" / "handoffs"
    for item in items:
        rels: list[tuple[str, ...]] = []
        for reference in item["sources"]:
            rel = _parts_relative(Path(reference["path"]), root)
            if rel is None or len(rel) < 2 or rel[0] != _LEGACY_DIR:
                _fail(
                    "approval-conflict",
                    "a publication source is not legacy project data",
                )
            rels.append(rel)
        target = item["target_path"]
        if target is not None and Path(target).parent == handoff_root:
            if any(rel[1] not in {"workspace", ".runtime"} for rel in rels):
                _fail("approval-conflict", "handoff sources must be legacy context")
            optional.append(item)
            continue
        top = rels[0][1]
        if any(rel[1] != top for rel in rels):
            _fail("approval-conflict", "one publication item mixes legacy categories")
        if top == "tasks":
            task_sources = [rel for rel in rels if rel[-1] == _TASK_JSON]
            if task_sources:
                if len(task_sources) != 1:
                    _fail(
                        "approval-conflict",
                        "an item cannot bind several task sources",
                    )
                folder = task_sources[0][:-1]
                if len(folder) < 3:
                    _fail(
                        "approval-conflict",
                        "a legacy task source must live in its own folder",
                    )
                inside = (
                    len(rel) > len(folder) and rel[: len(folder)] == folder
                    for rel in rels
                )
                if not all(inside):
                    _fail(
                        "approval-conflict",
                        "a task item binds sources outside its task folder",
                    )
                if item["decision"] == "private-only":
                    if item["required"]:
                        _fail(
                            "approval-conflict",
                            "a private task skip must be explicitly optional",
                        )
                    optional.append(item)
                    continue
                candidate = item["candidate_ref"]
                if len(rels) != 1 and (
                    candidate is None or candidate["state"]["type"] != "directory"
                ):
                    _fail(
                        "approval-conflict",
                        "a file task projection binds exactly its task source",
                    )
                primaries.setdefault(folder, []).append(
                    (item, [rel[len(folder) :] for rel in rels])
                )
            else:
                attachments.append((item, rels))
        elif top in _DOC_TARGETS:
            if any(len(rel) < 3 for rel in rels):
                _fail(
                    "approval-conflict",
                    "a legacy document source must be a file below its category",
                )
            if top == "spec" and item["decision"] == "private-only":
                if item["required"]:
                    _fail(
                        "approval-conflict",
                        "private spec preservation must be explicitly optional",
                    )
                optional.append(item)
                continue
            documents.append((top, item, [rel[2:] for rel in rels]))
        else:
            if item["decision"] != "private-only":
                _fail(
                    "approval-conflict",
                    "generated or journal legacy data stays private-only",
                )
            optional.append(item)
    for item, rels in attachments:
        matches = [
            folder
            for folder in primaries
            if all(
                len(rel) > len(folder) and rel[: len(folder)] == folder for rel in rels
            )
        ]
        if item["decision"] == "private-only":
            if item["required"]:
                _fail(
                    "approval-conflict",
                    "a private task attachment must be explicitly optional",
                )
            optional.append(item)
            continue
        if len(matches) == 0:
            _fail(
                "approval-conflict",
                "a task attachment has no unique approved task",
            )
        folder = max(matches, key=len)
        primaries[folder].append((item, [rel[len(folder) :] for rel in rels]))
    return primaries, documents, optional


def _check_task_target(root: Path, target: Path, projection: Any) -> None:
    tasks = root / "ai" / "tasks"
    if projection.archive_bucket is None:
        expected = tasks / projection.legacy_id
    else:
        expected = tasks / "archive" / projection.archive_bucket / projection.legacy_id
    if target != expected:
        _fail("target-conflict", "a migrated task must use its derived task location")


def _check_task_closure(
    root: Path,
    folder: tuple[str, ...],
    records: Sequence[tuple[Mapping[str, Any], list[tuple[str, ...]]]],
    read_source: ReadOriginal,
    private_strings: tuple[str, ...],
    approved_targets: set[Path],
) -> tuple[Any, str]:
    items = [record[0] for record in records]
    decisions = {item["decision"] for item in items}
    if len(decisions) != 1 or not decisions <= {"share", "redact"}:
        _fail(
            "approval-required",
            "a legacy task needs exactly one share or redact approval",
        )
    decision = next(iter(decisions))
    if any(not item["required"] for item in items):
        _fail("approval-required", "a legacy task projection cannot be optional")
    source_map: dict[str, Mapping[str, Any]] = {}
    for item, rels in records:
        for rel, reference in zip(rels, item["sources"]):
            source_map.setdefault(PurePosixPath(*rel).as_posix(), reference)
    directory_form = (
        len(records) == 1
        and records[0][0]["candidate_ref"]["state"]["type"] == "directory"
    )
    sibling_candidates: dict[str, bytes] = {}
    if directory_form:
        item = records[0][0]
        candidate = item["candidate_ref"]
        target = Path(item["target_path"])
        members = _candidate_files(candidate)
        expected = (set(source_map) - {_TASK_JSON}) | {_TASK_DOCUMENT, _TASK_SIDECAR}
        if members != expected:
            _fail(
                "candidate-conflict",
                "the approved task tree drops obligated projections or adds "
                "unknown members",
            )
        task_raw = _candidate_bytes(candidate, _TASK_DOCUMENT)
        sidecar_raw = _candidate_bytes(candidate, _TASK_SIDECAR)
        for rel in source_map:
            if rel != _TASK_JSON:
                sibling_candidates[rel] = _candidate_bytes(candidate, rel)
        form = "directory"
    else:
        document_records = [
            record
            for record in records
            if Path(record[0]["target_path"]).name == _TASK_DOCUMENT
        ]
        if len(document_records) != 1:
            _fail(
                "candidate-conflict",
                "a legacy task needs exactly one migrated task document",
            )
        document_item = document_records[0][0]
        target = Path(document_item["target_path"]).parent
        sidecar_records = [
            record
            for record in records
            if Path(record[0]["target_path"]).name == _TASK_SIDECAR
        ]
        if (
            len(sidecar_records) != 1
            or Path(sidecar_records[0][0]["target_path"]).parent != target
        ):
            _fail(
                "candidate-conflict",
                "a legacy task needs exactly one migrated sidecar next to its document",
            )
        sidecar_item = sidecar_records[0][0]
        primaries = [
            record
            for record in records
            if any(rel == (_TASK_JSON,) for rel in record[1])
        ]
        if {id(record[0]) for record in primaries} != {
            id(document_item),
            id(sidecar_item),
        }:
            _fail(
                "approval-conflict",
                "a task source is bound by exactly its document and sidecar "
                "projections",
            )
        task_raw = _candidate_bytes(document_item["candidate_ref"], None)
        sidecar_raw = _candidate_bytes(sidecar_item["candidate_ref"], None)
        for record_item, rels in records:
            if record_item in (document_item, sidecar_item):
                continue
            if (
                len(rels) != 1
                or record_item["candidate_ref"]["state"]["type"] != "file"
            ):
                _fail(
                    "approval-conflict",
                    "one approved attachment item per legacy file",
                )
            rel = PurePosixPath(*rels[0]).as_posix()
            if Path(record_item["target_path"]) != target.joinpath(*rels[0]):
                _fail(
                    "target-conflict",
                    "an approved attachment keeps its legacy name inside the "
                    "task directory",
                )
            sibling_candidates[rel] = _candidate_bytes(
                record_item["candidate_ref"], None
            )
        form = "file"
    source_raw = read_source(source_map[_TASK_JSON])
    source_path = PurePosixPath(*folder, _TASK_JSON).as_posix()
    projection = validate_task_projection(
        source_raw,
        task_raw,
        sidecar_raw,
        source_path=source_path,
        decision=decision,
    )
    _check_task_target(root, target, projection)
    sibling_sources = {
        rel: read_source(reference)
        for rel, reference in source_map.items()
        if rel != _TASK_JSON
    }
    digests = {hashlib.sha256(source_raw).hexdigest()}
    digests.update(hashlib.sha256(raw).hexdigest() for raw in sibling_sources.values())
    _check_shared_text(
        task_raw, private_strings=private_strings, private_digests=digests
    )
    _check_markdown_links(task_raw, target / _TASK_DOCUMENT, root, approved_targets)
    for relative, candidate_raw in sibling_candidates.items():
        if decision == "share" and candidate_raw != sibling_sources[relative]:
            _fail(
                "candidate-conflict", "a shared attachment must preserve source bytes"
            )
        _check_shared_text(
            candidate_raw, private_strings=private_strings, private_digests=digests
        )
        _check_markdown_links(candidate_raw, target / relative, root, approved_targets)
    _check_shared_text(
        sidecar_raw,
        private_strings=private_strings,
        private_digests=digests,
        check_legacy_layout=False,
        check_digests=False,
    )
    return projection, form


def _common_directory_prefix(paths: Sequence[tuple[str, ...]]) -> tuple[str, ...]:
    prefix = paths[0][:-1]
    for rel in paths[1:]:
        current = rel[:-1]
        index = 0
        while (
            index < len(prefix)
            and index < len(current)
            and prefix[index] == current[index]
        ):
            index += 1
        prefix = prefix[:index]
    return prefix


def _check_document_item(
    root: Path,
    category: str,
    item: Mapping[str, Any],
    rels: Sequence[tuple[str, ...]],
    read_source: ReadOriginal,
    private_strings: tuple[str, ...],
    approved_targets: set[Path],
) -> None:
    if item["decision"] not in {"share", "redact"} or not item["required"]:
        _fail(
            "approval-required",
            "legacy spec and lessons projections cannot be omitted or optional",
        )
    candidate = item["candidate_ref"]
    target = Path(item["target_path"])
    documents_root = root.joinpath(*_DOC_TARGETS[category])
    pairs: list[tuple[str, bytes, bytes, Path]] = []
    if candidate["state"]["type"] == "file":
        if len(rels) != 1:
            _fail(
                "approval-conflict",
                "a file candidate projects exactly one legacy document",
            )
        if target != documents_root.joinpath(*rels[0]):
            _fail(
                "target-conflict",
                "a legacy document projection keeps its relative path",
            )
        pairs.append(
            (
                rels[0][-1],
                read_source(item["sources"][0]),
                _candidate_bytes(candidate, None),
                target,
            )
        )
    else:
        common = _common_directory_prefix(rels)
        if target != (documents_root.joinpath(*common) if common else documents_root):
            _fail(
                "target-conflict",
                "an approved document tree keeps its legacy relative position",
            )
        members = _candidate_files(candidate)
        expected = {PurePosixPath(*rel[len(common) :]).as_posix() for rel in rels}
        if members != expected:
            _fail(
                "candidate-conflict",
                "an approved document tree does not match its legacy sources",
            )
        for rel, reference in zip(rels, item["sources"]):
            member = PurePosixPath(*rel[len(common) :]).as_posix()
            pairs.append(
                (
                    member,
                    read_source(reference),
                    _candidate_bytes(candidate, member),
                    target / member,
                )
            )
    digests = {hashlib.sha256(source_raw).hexdigest() for _, source_raw, _, _ in pairs}
    for member, source_raw, candidate_raw, output in pairs:
        if item["decision"] == "share" and candidate_raw != source_raw:
            _fail("candidate-conflict", "a shared document must preserve source bytes")
        _check_shared_text(
            candidate_raw, private_strings=private_strings, private_digests=digests
        )
        _check_markdown_links(candidate_raw, output, root, approved_targets)
        if category == "lessons" and member.endswith(".md"):
            _check_lessons_preserved(source_raw, candidate_raw)


def _validate_project_closures(
    root: Path,
    closures: Mapping[
        tuple[str, ...], Sequence[tuple[Mapping[str, Any], list[tuple[str, ...]]]]
    ],
    documents: Sequence[tuple[str, Mapping[str, Any], list[tuple[str, ...]]]],
    read_source: ReadOriginal,
    private_strings: tuple[str, ...],
) -> tuple[dict[str, Any], dict[tuple[str, ...], str]]:
    """Validate one project's closures; return projections and task forms."""
    approved_targets = _approved_target_files(closures, documents)
    projections: dict[str, Any] = {}
    forms: dict[tuple[str, ...], str] = {}
    for folder, records in closures.items():
        projection, form = _check_task_closure(
            root, folder, records, read_source, private_strings, approved_targets
        )
        if projection.legacy_id in projections:
            _fail("graph-conflict", "legacy task identities must be unique")
        projections[projection.legacy_id] = projection
        forms[folder] = form
    validate_projection_graph(projections)
    for category, item, rels in documents:
        _check_document_item(
            root, category, item, rels, read_source, private_strings, approved_targets
        )
    return projections, forms


# ---------------------------------------------------------------------------
# Repeatable legacy input validation
# ---------------------------------------------------------------------------


def _assign_items(
    roots: Sequence[Path], items: Sequence[Mapping[str, Any]]
) -> dict[Path, list[Mapping[str, Any]]]:
    assigned: dict[Path, list[Mapping[str, Any]]] = {root: [] for root in roots}
    for item in items:
        covering = [
            root
            for root in roots
            if all(
                _parts_relative(Path(reference["path"]), root) is not None
                for reference in item["sources"]
            )
        ]
        if len(covering) != 1:
            _fail(
                "scope-conflict",
                "a publication item's sources do not belong to exactly one selected project",
            )
        root = covering[0]
        target = item["target_path"]
        if target is not None and _parts_relative(Path(target), root) is None:
            _fail("scope-conflict", "a publication target leaves its owning project")
        assigned[root].append(item)
    return assigned


def validate_legacy_inputs(
    manifest: Mapping[str, Any], read_original: ReadOriginal
) -> None:
    """Re-validate the complete legacy closure of a sealed manifest.

    The caller has already proven the bound references current or resolved
    their originals after controlled rewrites; ``read_original`` supplies
    those known original bytes. Candidates are re-read against their
    recorded state. Beyond the publication closures, every declared
    operation must match the closed set derivable from the bound legacy
    sources, the ownership metadata and the approved candidates: a re-sealed
    manifest with altered, invented or missing operations is rejected even
    when it is schema-valid. Nothing here writes or substitutes approval.
    """
    payload = manifest["payload"]
    items = payload["publication_decisions"]["items"]
    roots = [Path(project["root"]) for project in payload["projects"]]
    assigned = _assign_items(roots, items)
    private_strings = _private_strings(Path(payload["backup_root"]))
    for project in payload["projects"]:
        root = Path(project["root"])
        closures, documents, optional = _classify_project_items(root, assigned[root])
        projections, forms = _validate_project_closures(
            root, closures, documents, read_original, private_strings
        )
        _validate_project_operations(root, project, assigned[root], read_original)
        original = project["sources"][0]
        inventory_root = Path(original["path"])
        if snapshot(inventory_root) != original["state"]:
            from sbtd_migration import _source_backup_paths

            require_private_directory(Path(payload["backup_root"]))
            inventory_root = _source_backup_paths(manifest)[original["path"]]
        state, entries = directory_snapshot(inventory_root)
        if state != original["state"]:
            _fail("state-conflict", "the complete original inventory is unavailable")
        metadata = next(
            (entry for entry in entries if entry["path"] == _TEMPLATE_HASHES), None
        )
        if metadata is None or metadata["type"] != "file":
            _fail("invalid-config", "the original ownership metadata is unavailable")
        hashes = _parse_template_hashes(
            _json_object(
                read_file(
                    inventory_root / _TEMPLATE_HASHES,
                    {"type": "file", "checksum": metadata["checksum"]},
                ),
                "the original ownership metadata",
            )
        )
        _inventory_coverage(entries, closures, forms, documents, optional, root, hashes)
        _check_context_handoffs(
            root,
            entries,
            closures,
            projections,
            assigned[root],
            read_original,
            project["source_ref"],
            project["head"],
        )
    _validate_shared_operations(payload, sorted(str(root) for root in roots))
    from sbtd_graft_deployment import validate_deployment_declarations

    validate_deployment_declarations(payload)
    _bind_approved_routing(payload, roots, bind_live=False)


# ---------------------------------------------------------------------------
# Operation-set legitimacy gate (shared by apply and verify consumers)
# ---------------------------------------------------------------------------


def _check_operation_common(operation: Mapping[str, Any], root: Path) -> None:
    if operation["dependent_projects"] != [str(root)]:
        _fail("semantic-violation", "a private operation binds foreign dependents")
    if _parts_relative(Path(operation["target"]), root) is None:
        _fail("semantic-violation", "a private operation leaves its project")
    requirement = operation["before_requirement"]
    if requirement["kind"] != "state":
        _fail("semantic-violation", "operations start from a concrete state")


def _check_identity_operation(
    root: Path, operation: Mapping[str, Any], read_original: ReadOriginal
) -> None:
    if (
        operation["phase"] != "apply"
        or operation["owner_kind"] != "file"
        or operation["selector"] != "name"
    ):
        _fail("semantic-violation", "developer extraction shape was altered")
    _check_operation_common(operation, root)
    if Path(operation["target"]) != root / ".sbtd" / "developer":
        _fail("semantic-violation", "developer extraction target was altered")
    if operation["before_requirement"] != _state_requirement(_ABSENT):
        _fail("semantic-violation", "developer extraction requires a missing target")
    change = operation["change"]
    source = change["source_ref"]
    if (
        Path(source["path"]) != root / _LEGACY_DIR / _DEVELOPER_NAME
        or source["state"]["type"] != "file"
    ):
        _fail("semantic-violation", "developer extraction source was altered")
    ownership = operation["ownership"]
    if (
        ownership["kind"] != "config-entry"
        or ownership["key_path"] != ["name"]
        or ownership["reference"] != source
    ):
        _fail("semantic-violation", "developer extraction ownership was altered")
    if read_legacy_identity(read_original(source)) != change["name"]:
        _fail(
            "identity-conflict",
            "the legacy identity no longer matches the approved operation",
        )


def _check_ignore_operation(
    root: Path, operation: Mapping[str, Any], read_original: ReadOriginal
) -> None:
    if (
        operation["phase"] != "apply"
        or operation["owner_kind"] != "gitignore"
        or operation["selector"] != "local-ignore"
    ):
        _fail("semantic-violation", "the ignore protection shape was altered")
    _check_operation_common(operation, root)
    if Path(operation["target"]) != root / ".gitignore":
        _fail("semantic-violation", "the ignore protection target was altered")
    asset = {"path": str(_IGNORE_ASSET), "state": snapshot(_IGNORE_ASSET)}
    if operation["change"] != {"kind": "ensure-file-block", "source_ref": asset}:
        _fail("semantic-violation", "the ignore protection content was altered")
    if operation["ownership"] != {"kind": "template-source", "reference": asset}:
        _fail("semantic-violation", "the ignore protection ownership was altered")
    from onboard import missing_file_lines

    before = operation["before_requirement"]
    if before["kind"] != "state" or before["state"]["type"] not in {"file", "absent"}:
        _fail(
            "semantic-violation", "ignore protection needs a fixed original file state"
        )
    original = (
        b""
        if before["state"]["type"] == "absent"
        else read_original({"path": operation["target"], "state": before["state"]})
    )
    try:
        needed = missing_file_lines(
            read_file(_IGNORE_ASSET, asset["state"]).decode("utf-8"),
            original.decode("utf-8"),
        )
    except UnicodeDecodeError:
        _fail("invalid-config", "managed ignore content is not UTF-8 text")
    if not needed:
        _fail(
            "semantic-violation", "ignore protection was already complete before apply"
        )


def _check_cleanup_operation(
    root: Path, operation: Mapping[str, Any], legacy_reference: Mapping[str, Any]
) -> None:
    if (
        operation["phase"] != "cleanup"
        or operation["owner_kind"] != "directory"
        or operation["selector"] != "whole-resource"
        or operation["change"] != {"kind": "remove"}
    ):
        _fail("semantic-violation", "the legacy retirement shape was altered")
    _check_operation_common(operation, root)
    if Path(operation["target"]) != root / _LEGACY_DIR:
        _fail("semantic-violation", "the legacy retirement target was altered")
    if operation["ownership"] != {
        "kind": "template-source",
        "reference": dict(legacy_reference),
    }:
        _fail("semantic-violation", "the legacy retirement ownership was altered")
    if operation["before_requirement"] != _state_requirement(legacy_reference["state"]):
        _fail("semantic-violation", "the legacy retirement before-state was altered")


def _check_platform_closure(
    root: Path,
    operations: list[Mapping[str, Any]],
    platforms: Sequence[str],
    read_original: ReadOriginal,
) -> None:
    """The remaining operations must be exactly the recorded platform files."""
    if not operations:
        if platforms:
            _fail(
                "semantic-violation",
                "the recorded platform retirement operations are missing",
            )
        return
    hashes_reference: Mapping[str, Any] | None = None
    file_targets: set[str] = set()
    marker_targets: set[str] = set()
    replacement_targets: set[str] = set()
    for operation in operations:
        if operation["selector"] == _ROUTING_SELECTOR:
            if operation["change"].get("kind") != "copy-file":
                _fail(
                    "semantic-violation",
                    "an approved routing replacement must copy its candidate",
                )
            replacement_targets.add(operation["target"])
            continue
        if operation["phase"] != "apply" or operation["change"] != {"kind": "remove"}:
            _fail("semantic-violation", "an unknown private operation was added")
        _check_operation_common(operation, root)
        if operation["before_requirement"]["state"]["type"] != "file":
            _fail("semantic-violation", "a platform operation before-state drifted")
        ownership = operation["ownership"]
        if ownership["kind"] == "template-source":
            if (
                operation["owner_kind"] != "file"
                or operation["selector"] != "whole-resource"
            ):
                _fail("semantic-violation", "a platform removal shape was altered")
            if hashes_reference is None:
                hashes_reference = ownership["reference"]
            elif ownership["reference"] != hashes_reference:
                _fail(
                    "semantic-violation",
                    "platform removals must bind the same ownership metadata",
                )
            file_targets.add(operation["target"])
        elif ownership["kind"] == "managed-marker":
            if (
                operation["owner_kind"] != "markdown"
                or operation["selector"] != "trellis-block"
                or ownership["marker"] != _TRELLIS_MARKER
            ):
                _fail("semantic-violation", "a marker removal shape was altered")
            if ownership["reference"] != {
                "path": operation["target"],
                "state": operation["before_requirement"]["state"],
            }:
                _fail("semantic-violation", "a marker removal ownership was altered")
            marker_targets.add(operation["target"])
        else:
            _fail("semantic-violation", "an unknown private ownership was added")
    if hashes_reference is None:
        _fail(
            "semantic-violation",
            "the recorded platform ownership metadata is missing",
        )
    if Path(hashes_reference["path"]) != root / _LEGACY_DIR / _TEMPLATE_HASHES:
        _fail("semantic-violation", "the platform ownership reference was altered")
    hashes = _parse_template_hashes(
        _json_object(read_original(hashes_reference), "the legacy ownership metadata")
    )
    expected_files: set[str] = set()
    expected_markers: set[str] = set()
    derived_platforms: set[str] = set()
    for relative in hashes:
        parts = PurePosixPath(relative).parts
        target = str(root.joinpath(*parts))
        if parts[0] == _LEGACY_DIR:
            continue
        if parts[0] in _UNSELECTED_PLATFORM_PREFIX:
            _fail(
                "scope-conflict",
                "unselected legacy host routing requires reconciliation",
            )
        if len(parts) > 1 and parts[0] in _PLATFORM_PREFIX:
            derived_platforms.add(_PLATFORM_PREFIX[parts[0]])
            expected_files.add(target)
        elif len(parts) == 1 and parts[0] in _ROOT_OWNED_FILES:
            expected_markers.add(target)
        else:
            _fail("unknown-content", "a recorded generated path cannot be classified")
    if marker_targets & replacement_targets:
        _fail(
            "approval-conflict",
            "an approved routing replacement cannot also delete the marker block",
        )
    covered_markers = marker_targets | (replacement_targets & expected_markers)
    if file_targets != expected_files or covered_markers != expected_markers:
        _fail(
            "semantic-violation",
            "platform operations do not match the recorded ownership metadata",
        )
    if sorted(derived_platforms) != list(platforms):
        _fail("semantic-violation", "the declared platforms were altered")


def _validate_project_operations(
    root: Path,
    project: Mapping[str, Any],
    items: Sequence[Mapping[str, Any]],
    read_original: ReadOriginal,
) -> None:
    sources = project["sources"]
    if (
        len(sources) != 1
        or Path(sources[0]["path"]) != root / _LEGACY_DIR
        or sources[0]["state"]["type"] != "directory"
    ):
        _fail("semantic-violation", "a project binds exactly its legacy tree")
    deployment = [
        operation
        for operation in project["private_operations"]
        if operation["phase"] == "deploy"
    ]
    remaining = [
        operation
        for operation in project["private_operations"]
        if operation["phase"] != "deploy"
    ]
    expected_publications = [
        _publication_operation(root, item)
        for item in sorted(
            (item for item in items if item["decision"] != "private-only"),
            key=lambda item: item["target_path"],
        )
    ]
    for expected in expected_publications:
        if expected not in remaining:
            _fail(
                "semantic-violation",
                "a required publication operation is missing or altered",
            )
        remaining.remove(expected)
    identities = [
        operation
        for operation in remaining
        if operation["change"].get("kind") == "migrate-developer"
    ]
    if len(identities) > 1:
        _fail("semantic-violation", "developer extraction was duplicated")
    if identities:
        remaining.remove(identities[0])
        _check_identity_operation(root, identities[0], read_original)
    needs_protection = bool(expected_publications or identities or deployment)
    protection = [
        operation for operation in remaining if operation["owner_kind"] == "gitignore"
    ]
    if protection:
        if not needs_protection or len(protection) != 1:
            _fail("semantic-violation", "the ignore protection scope was altered")
        # Later phases see the applied file. Validate the frozen operation,
        # not whether its pre-apply change is still needed in today's file.
        _check_ignore_operation(root, protection[0], read_original)
        remaining.remove(protection[0])
    elif needs_protection and _ignore_operation(root) is not None:
        _fail("semantic-violation", "the required ignore protection is missing")
    cleanups = [operation for operation in remaining if operation["phase"] == "cleanup"]
    if len(cleanups) != 1:
        _fail(
            "semantic-violation",
            "the legacy tree retirement is missing or duplicated",
        )
    remaining.remove(cleanups[0])
    _check_cleanup_operation(root, cleanups[0], sources[0])
    _check_platform_closure(root, remaining, project["platforms"], read_original)


_ROUTING_ROLES = frozenset({"codex-global", "omp-global", "demo-project"})
_ROUTING_SELECTOR = "approved-routing-replacement"
_ROUTING_APPROVAL_PUBLIC_KEY = _PACKAGE / "assets" / "routing-approval.pub"


def _routing_crypto():
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
            Ed25519PublicKey,
        )
        from cryptography.hazmat.primitives.serialization import (
            load_pem_private_key,
            load_pem_public_key,
        )
    except ImportError:
        _fail(
            "validator-unavailable",
            "prepare the installed Skill's declared requirements before migration",
        )
    return (
        InvalidSignature,
        Ed25519PrivateKey,
        Ed25519PublicKey,
        load_pem_private_key,
        load_pem_public_key,
    )


def _routing_approval_public_key():
    """The installed approval key. Callers cannot replace it with a path."""
    invalid, _private, public_type, _load_private, load_public = _routing_crypto()
    try:
        key = load_public(_ROUTING_APPROVAL_PUBLIC_KEY.read_bytes())
    except (OSError, ValueError, TypeError, invalid):
        _fail("runtime-unavailable", "the installed routing approval key is unusable")
    if not isinstance(key, public_type):
        _fail("runtime-unavailable", "the installed routing approval key is not Ed25519")
    return key


def _approval_signed_bytes(document: Mapping[str, Any]) -> bytes:
    return contracts.canonical_json_bytes(
        {"schema_version": document["schema_version"], "items": document["items"]}
    )


def _verify_routing_approval_signature(document: Mapping[str, Any]) -> None:
    invalid, _private, _public, _load_private, _load_public = _routing_crypto()
    signature = document.get("signature")
    if not isinstance(signature, str) or not signature:
        _fail("invalid-config", "the routing approval record has no signature")
    try:
        raw = base64.b64decode(signature, validate=True)
        _routing_approval_public_key().verify(raw, _approval_signed_bytes(document))
    except (invalid, ValueError, TypeError):
        _fail(
            "approval-conflict",
            "the routing approval signature does not match the installed key",
        )


def _sign_routing_approval(
    approval_path: Path, key_path: Path, vault: Path, roots: Sequence[Path]
) -> None:
    """Sign one existing approval file. No other path is written."""
    invalid, private_type, _public, load_private, _load_public = _routing_crypto()
    if (
        ".." in key_path.parts
        or not key_path.is_absolute()
        or key_path.is_symlink()
        or not key_path.is_file()
        or key_path.is_relative_to(vault)
        or any(
            key_path.is_relative_to(root) or root.is_relative_to(key_path) for root in roots
        )
    ):
        _fail(
            "private-scope",
            "the routing approval key must stay outside the vault and selected projects",
        )
    if not approval_path.is_relative_to(vault):
        _fail("private-scope", "routing approvals must live inside the private vault")
    require_private_directory(approval_path.parent)
    document = _json_object(read_file(approval_path), "the routing approval record")
    if not isinstance(document, dict) or "items" not in document:
        _fail("invalid-config", "the routing approval record is malformed")
    try:
        private = load_private(key_path.read_bytes(), password=None)
    except (OSError, ValueError, TypeError):
        _fail("invalid-argument", "the routing approval key is unusable")
    if not isinstance(private, private_type):
        _fail("invalid-argument", "the routing approval key is not Ed25519")
    document["signature"] = base64.b64encode(
        private.sign(_approval_signed_bytes(document))
    ).decode("ascii")
    try:
        _routing_approval_public_key().verify(
            base64.b64decode(document["signature"]), _approval_signed_bytes(document)
        )
    except (invalid, ValueError, TypeError):
        _fail(
            "approval-conflict",
            "the routing approval key does not match the installed public key",
        )
    approval_path.write_bytes(contracts.canonical_json_bytes(document))



def _load_routing_approvals(path: Any, vault: Path) -> list[dict[str, Any]]:
    """Load the private routing approval record. Plan never creates it."""
    if path is None:
        return []
    if not isinstance(path, (str, os.PathLike)):
        _fail("invalid-argument", "the routing approval path must be a path")
    approval_path = Path(path)
    if ".." in approval_path.parts or not approval_path.is_absolute():
        _fail("invalid-argument", "the routing approval path is not canonical")
    if not approval_path.is_relative_to(vault):
        _fail("private-scope", "routing approvals must live inside the private vault")
    require_private_directory(approval_path.parent)
    document = _json_object(read_file(approval_path), "the routing approval record")
    if (
        not isinstance(document, dict)
        or document.get("schema_version") != 1
        or set(document) != {"schema_version", "items", "signature"}
        or not isinstance(document["items"], list)
    ):
        _fail("invalid-config", "the routing approval record is malformed")
    _verify_routing_approval_signature(document)
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in document["items"]:
        if (
            not isinstance(item, dict)
            or set(item) != {"role", "target_path", "before", "candidate_ref", "basis"}
            or item["role"] not in _ROUTING_ROLES
            or not isinstance(item["target_path"], str)
            or not isinstance(item["basis"], str)
            or not item["basis"].strip()
            or not isinstance(item["before"], dict)
            or not isinstance(item["candidate_ref"], dict)
        ):
            _fail("invalid-config", "a routing approval item is malformed")
        if item["target_path"] in seen:
            _fail("approval-conflict", "a routing target is approved more than once")
        seen.add(item["target_path"])
        items.append(item)
    return items


def _approved_routing_operations(
    items: Sequence[Mapping[str, Any]],
    roots: Sequence[Path],
    vault: Path,
    approval_path: Path,
    *,
    bind_live: bool = True,
) -> tuple[list[dict[str, Any]], dict[Path, list[dict[str, Any]]]]:
    """Bind each approved candidate to its live target. Mismatch blocks."""
    from onboard import default_codex_home, omp_global_agents_path, user_home

    pause = read_file(_PAUSE_ASSET)
    approval_ref = {"path": str(approval_path), "state": snapshot(approval_path)}
    shared: list[dict[str, Any]] = []
    private: dict[Path, list[dict[str, Any]]] = {root: [] for root in roots}
    dependents = sorted(str(root) for root in roots)
    for item in items:
        target = Path(item["target_path"])
        if (
            not target.is_absolute()
            or ".." in target.parts
            or target.name != "AGENTS.md"
            or target.is_relative_to(vault)
        ):
            _fail("approval-conflict", "a routing target is not a live AGENTS.md")
        role = item["role"]
        owner: Path | None = None
        if role == "codex-global":
            if target != default_codex_home() / "AGENTS.md":
                _fail(
                    "approval-conflict", "a codex routing approval names another file"
                )
        elif role == "omp-global":
            omp_home = user_home() / ".omp"
            if _omp_root_presence(omp_home) != "directory":
                _fail(
                    "ownership-conflict",
                    "the existing OMP root is not a safe directory",
                )
            if target != omp_global_agents_path(omp_home):
                _fail("approval-conflict", "an omp routing approval names another file")
        else:
            matches = [root for root in roots if target == root / "AGENTS.md"]
            if len(matches) != 1:
                _fail(
                    "approval-conflict",
                    "a project routing approval is outside the batch",
                )
            owner = matches[0]
        recorded = item["before"]
        if not isinstance(recorded, Mapping) or recorded.get("type") != "file":
            _fail("approval-conflict", "a routing approval does not bind a file")
        if bind_live:
            before = snapshot(target)
            if before != recorded:
                _fail(
                    "state-conflict", "a routing target no longer matches its approval"
                )
        else:
            before = dict(recorded)
        candidate = item["candidate_ref"]
        candidate_path = Path(candidate.get("path", ""))
        if (
            not candidate_path.is_absolute()
            or ".." in candidate_path.parts
            or not candidate_path.is_relative_to(vault)
            or snapshot(candidate_path) != candidate.get("state")
        ):
            _fail("state-conflict", "an approved routing candidate changed")
        raw = read_file(candidate_path, candidate["state"])
        if not raw.startswith(pause):
            _fail(
                "candidate-conflict",
                "an approved routing candidate lacks the pause block",
            )
        operation = _operation(
            "apply",
            "markdown",
            target,
            _ROUTING_SELECTOR,
            {"kind": "copy-file", "source_ref": copy.deepcopy(candidate)},
            {
                "kind": "approved-candidate",
                "reference": copy.deepcopy(candidate),
                "approval_ref": approval_ref,
                "role": role,
            },
            _state_requirement(before),
            dependents if owner is None else [str(owner)],
        )
        if owner is None:
            shared.append(operation)
        else:
            private[owner].append(operation)
    return shared, private


def _vault_file_ref(reference: Mapping[str, Any], vault: Path, message: str) -> Path:
    path = reference.get("path")
    if (
        not isinstance(path, str)
        or not Path(path).is_absolute()
        or ".." in Path(path).parts
        or not Path(path).is_relative_to(vault)
    ):
        _fail("private-scope", message)
    return Path(path)


def _routing_rows(
    payload: Mapping[str, Any],
) -> list[tuple[str, Path | None, Mapping[str, Any]]]:
    rows: list[tuple[str, Path | None, Mapping[str, Any]]] = []
    for operation in payload["shared_operations"]:
        if operation["selector"] == _ROUTING_SELECTOR:
            rows.append(("shared", None, operation))
    for project in payload["projects"]:
        root = Path(project["root"])
        for operation in project["private_operations"]:
            if operation["selector"] == _ROUTING_SELECTOR:
                rows.append(("private", root, operation))
    return rows


def _bind_approved_routing(
    payload: Mapping[str, Any], roots: Sequence[Path], *, bind_live: bool
) -> None:
    """Rebuild the approved set from the sealed approval ref and require a match.

    The ref lives on the payload, so dropping every routing operation cannot
    hide it. A missing, extra, or substituted operation is rejected. Role,
    target, and candidate changes fail the same comparison. The approval file
    and every declared candidate must stay inside the vault.
    """
    declared = _routing_rows(payload)
    approval = payload["routing_approvals"]
    if approval is None:
        if declared:
            _fail(
                "approval-conflict",
                "an approved routing replacement is not bound to its approval record",
            )
        return
    vault = Path(payload["backup_root"])
    approval_path = _vault_file_ref(
        approval,
        vault,
        "an approved routing record lives outside the private vault",
    )
    for _place, _root, operation in declared:
        ownership = operation["ownership"]
        candidate = operation["change"].get("source_ref")
        if not isinstance(ownership.get("approval_ref"), Mapping) or not isinstance(
            candidate, Mapping
        ):
            _fail(
                "approval-conflict",
                "an approved routing replacement is not bound to its approval record",
            )
        _vault_file_ref(
            ownership["approval_ref"],
            vault,
            "an approved routing record lives outside the private vault",
        )
        _vault_file_ref(
            candidate,
            vault,
            "an approved routing candidate lives outside the private vault",
        )
    if snapshot(approval_path) != approval["state"]:
        _fail("state-conflict", "the routing approval record changed")
    items = _load_routing_approvals(approval_path, vault)
    shared, private = _approved_routing_operations(
        items, roots, vault, approval_path, bind_live=bind_live
    )
    expected: list[tuple[str, Path | None, Mapping[str, Any]]] = [
        ("shared", None, operation) for operation in shared
    ]
    for root in roots:
        expected.extend(
            ("private", root, operation) for operation in private.get(root, [])
        )
    if [_routing_key(row) for row in declared] != [
        _routing_key(row) for row in expected
    ]:
        _fail(
            "approval-conflict",
            "an approved routing replacement does not match its approval record",
        )


def _routing_key(
    row: tuple[str, Path | None, Mapping[str, Any]],
) -> str:
    place, root, operation = row
    return contracts.canonical_json_bytes(
        {
            "place": place,
            "root": None if root is None else str(root),
            "operation": operation,
        }
    ).decode("utf-8")


def _validate_shared_operations(
    payload: Mapping[str, Any], all_roots: list[str]
) -> None:
    pins = _ownership_pins()
    pause_asset = {"path": str(_PAUSE_ASSET), "state": snapshot(_PAUSE_ASSET)}
    shared_roots = payload["shared_roots"]
    for record in shared_roots:
        if record["dependent_projects"] != all_roots:
            _fail("semantic-violation", "a shared root binds foreign dependents")
    for operation in payload["shared_operations"]:
        if operation["dependent_projects"] != all_roots:
            _fail("semantic-violation", "a shared operation binds foreign dependents")
        target = Path(operation["target"])
        covering = [
            record
            for record in shared_roots
            if _parts_relative(target, Path(record["path"])) is not None
        ]
        if len(covering) != 1:
            _fail("semantic-violation", "a shared operation leaves its roots")
        if operation["phase"] == "deploy":
            continue  # Checked as one complete producer-owned set below.
        change = operation["change"]
        ownership = operation["ownership"]
        if change.get("kind") == "ensure-file-block":
            if (
                operation["phase"] != "apply"
                or operation["owner_kind"] != "markdown"
                or operation["selector"] != "pause-legacy-routing"
                or target.name != "AGENTS.md"
            ):
                _fail("semantic-violation", "the routing pause shape was altered")
            if change["source_ref"] != pause_asset:
                _fail("semantic-violation", "the routing pause content was altered")
            pinned_state = {"type": "file", "checksum": pins["agents"]}
            if ownership["kind"] != "template-source" or ownership["reference"] != {
                "path": str(target),
                "state": pinned_state,
            }:
                _fail("semantic-violation", "the routing pause ownership was altered")
            if operation["before_requirement"] != _state_requirement(pinned_state):
                _fail("semantic-violation", "the routing pause before-state drifted")
        elif change == {"kind": "remove"}:
            if (
                operation["phase"] != "cleanup"
                or operation["owner_kind"] != "directory"
                or operation["selector"] != "whole-resource"
            ):
                _fail("semantic-violation", "a skill retirement shape was altered")
            if (
                ownership["kind"] != "skill-identity"
                or ownership["name"] not in pins["skills"]
            ):
                _fail("semantic-violation", "an unknown shared skill was added")
            pinned_state = dict(pins["skills"][ownership["name"]])
            if ownership["reference"] != {"path": str(target), "state": pinned_state}:
                _fail("semantic-violation", "a skill retirement ownership was altered")
            if operation["before_requirement"] != _state_requirement(pinned_state):
                _fail("semantic-violation", "a skill retirement before-state drifted")
        elif (
            change.get("kind") == "copy-file"
            and operation["selector"] == _ROUTING_SELECTOR
            and operation["phase"] == "apply"
            and operation["owner_kind"] == "markdown"
            and Path(operation["target"]).name == "AGENTS.md"
            and ownership.get("kind") == "approved-candidate"
            and ownership.get("reference") == change.get("source_ref")
        ):
            continue
        else:
            _fail("semantic-violation", "an unknown shared operation was added")
    pause_targets = {
        operation["target"]
        for operation in payload["shared_operations"]
        if operation["selector"] == "pause-legacy-routing"
    }
    replacement_targets = {
        operation["target"]
        for operation in payload["shared_operations"]
        if operation["selector"] == _ROUTING_SELECTOR
    }
    if pause_targets & replacement_targets:
        _fail(
            "approval-conflict",
            "an approved routing replacement cannot also append the pause block",
        )


# ---------------------------------------------------------------------------
# Plan-time inventory, freshness and ownership verification
# ---------------------------------------------------------------------------


def _check_item_freshness(root: Path, item: Mapping[str, Any], vault: Path) -> None:
    for reference in item["sources"]:
        state = reference["state"]
        if state["type"] != "file":
            _fail(
                "approval-conflict",
                "publication approval binds exact source files",
            )
        _check_reference_current(reference, "approval-conflict")
    candidate = item["candidate_ref"]
    if candidate is not None:
        candidate_path = Path(candidate["path"])
        if not candidate_path.is_relative_to(vault):
            _fail(
                "private-scope",
                "an approved candidate lives outside the private vault",
            )
        _check_reference_current(candidate, "approval-conflict")
    target = item["target_path"]
    if target is not None:
        target_path = Path(target)
        if _parts_relative(target_path, root) is None:
            _fail("scope-conflict", "a publication target leaves its project")
        if snapshot(target_path) != _ABSENT:
            _fail(
                "target-conflict",
                "a publication target already exists and is preserved for "
                "manual reconciliation",
            )
        _check_target_lineage(target_path, root)


def _load_publication_items(
    publication_path: Any, vault: Path
) -> list[Mapping[str, Any]]:
    if publication_path is None:
        return []
    if not isinstance(publication_path, (str, os.PathLike)):
        _fail("invalid-argument", "the publication decisions path must be a path")
    path = Path(publication_path)
    if ".." in path.parts or not path.is_absolute():
        _fail("invalid-argument", "the publication decisions path is not canonical")
    if not path.is_relative_to(vault):
        _fail(
            "private-scope",
            "publication decisions must live inside the private vault",
        )
    require_private_directory(path.parent)
    decisions = contracts.load_document(read_file(path), "publication_decisions")
    return decisions["items"]


def _check_legacy_version(root: Path) -> None:
    path = root / _LEGACY_DIR / _VERSION_FILE
    state = snapshot(path)
    if state["type"] != "file":
        _fail("unsupported-version", "the legacy tool version cannot be proven")
    try:
        text = read_file(path, state).decode("utf-8")
    except UnicodeDecodeError:
        _fail("unsupported-version", "the legacy tool version cannot be proven")
    if text.strip() != _LEGACY_VERSION:
        _fail(
            "unsupported-version",
            "the legacy tool version is not the characterized one",
        )


def _template_hashes(root: Path) -> tuple[dict[str, str], dict[str, Any]]:
    path = root / _LEGACY_DIR / _TEMPLATE_HASHES
    reference = _present_file_reference(path, "the legacy ownership metadata")
    document = _json_object(
        read_file(path, reference["state"]), "the legacy ownership metadata"
    )
    return _parse_template_hashes(document), reference


def _parse_template_hashes(document: Any) -> dict[str, str]:
    """Validate v0.6.17 metadata against the installed ownership pins."""
    if (
        not isinstance(document, dict)
        or document.get("__version") != 2
        or not isinstance(document.get("hashes"), dict)
    ):
        _fail("invalid-config", "the legacy ownership metadata is malformed")
    hashes: dict[str, str] = {}
    configuration_pins = _ownership_pins()["project_configs"]
    for relative, digest in document["hashes"].items():
        parts = _check_safe_relative(relative, "a legacy ownership path")
        if parts[0] == _LEGACY_DIR and (
            len(parts) < 2 or parts[1] not in _GENERATED_LEGACY_TOP
        ):
            _fail("invalid-config", "ownership metadata cannot claim legacy user data")
        if not isinstance(digest, str) or _HEX64.fullmatch(digest) is None:
            _fail("invalid-config", "the legacy ownership metadata is malformed")
        # A mutable legacy hash proves recorded bytes, not sole ownership
        # of a shared configuration. Mixed entries need reconciliation.
        if (
            len(parts) == 2
            and parts[1] in {"config.toml", "hooks.json", "settings.json"}
            and digest not in configuration_pins.get(relative, ())
        ):
            _fail("ownership-conflict", "shared configuration ownership is unproven")
        hashes[PurePosixPath(*parts).as_posix()] = digest
    return hashes


def _normalized_text_digest(raw: bytes) -> str:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        _fail(
            "ownership-conflict",
            "a recorded generated file is not inspectable text",
        )
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def _check_marker_block(text: str) -> None:
    start = f"<!-- {_TRELLIS_MARKER}:START -->"
    end = f"<!-- {_TRELLIS_MARKER}:END -->"
    if text.count(start) != 1 or text.count(end) != 1:
        _fail("ownership-conflict", "a managed marker is absent or ambiguous")
    left = text.index(start)
    try:
        text.index(end, left + len(start))
    except ValueError:
        _fail("ownership-conflict", "a managed marker is absent or ambiguous")


def _operation(
    phase: str,
    owner_kind: str,
    target: Path,
    selector: str,
    change: dict[str, Any],
    ownership: dict[str, Any],
    before: dict[str, Any],
    dependents: Sequence[str],
) -> dict[str, Any]:
    resource = contracts.resource_id(owner_kind, str(target))
    return {
        "operation_id": contracts.operation_id(phase, resource, selector),
        "phase": phase,
        "resource_id": resource,
        "owner_kind": owner_kind,
        "target": str(target),
        "selector": selector,
        "change": change,
        "ownership": ownership,
        "before_requirement": before,
        "dependent_projects": sorted(dependents),
    }


def _state_requirement(state: Mapping[str, Any]) -> dict[str, Any]:
    return {"kind": "state", "state": dict(state)}


def _platform_operations(
    root: Path,
    hashes: Mapping[str, str],
    hashes_reference: Mapping[str, Any],
    approved_targets: Collection[Path] = (),
) -> tuple[list[str], list[dict[str, Any]]]:
    platforms: set[str] = set()
    operations: list[dict[str, Any]] = []
    legacy_rels = [
        PurePosixPath(*PurePosixPath(relative).parts[1:]).as_posix()
        for relative in hashes
        if PurePosixPath(relative).parts[:1] == (_LEGACY_DIR,)
        and len(PurePosixPath(relative).parts) > 1
    ]
    ignored, _tracked = _legacy_index(root, legacy_rels)
    pending_unknown: list[str] = []
    for relative in sorted(hashes):
        parts = PurePosixPath(relative).parts
        legacy_rel = (
            PurePosixPath(*parts[1:]).as_posix()
            if parts[:1] == (_LEGACY_DIR,) and len(parts) > 1
            else None
        )
        target = root.joinpath(*parts)
        state = snapshot(target)
        if state["type"] != "file":
            _fail(
                "ownership-conflict",
                "a recorded generated file is unavailable",
            )
        raw = read_file(target, state)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            if legacy_rel is not None and legacy_rel in ignored:
                continue
            if legacy_rel is not None:
                pending_unknown.append(legacy_rel)
                continue
            _fail(
                "ownership-conflict",
                "a recorded generated file is not inspectable text",
            )
        if hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest() != hashes[relative]:
            _fail(
                "ownership-conflict",
                "generated content drifted; removal is not authorized",
            )
        if parts[0] == _LEGACY_DIR:
            # Generated scripts/config stay in the byte-preserved legacy tree
            # until the separately gated cleanup; never remove them during apply.
            continue
        if parts[0] in _UNSELECTED_PLATFORM_PREFIX:
            _fail(
                "scope-conflict",
                "unselected legacy host routing requires reconciliation",
            )
        if len(parts) > 1 and parts[0] in _PLATFORM_PREFIX:
            platforms.add(_PLATFORM_PREFIX[parts[0]])
            operations.append(
                _operation(
                    "apply",
                    "file",
                    target,
                    "whole-resource",
                    {"kind": "remove"},
                    {"kind": "template-source", "reference": dict(hashes_reference)},
                    _state_requirement(state),
                    [str(root)],
                )
            )
        elif len(parts) == 1 and parts[0] in _ROOT_OWNED_FILES:
            if target in approved_targets:
                continue
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                _fail(
                    "ownership-conflict",
                    "a managed root document is not inspectable text",
                )
            _check_marker_block(text)
            operations.append(
                _operation(
                    "apply",
                    "markdown",
                    target,
                    "trellis-block",
                    {"kind": "remove"},
                    {
                        "kind": "managed-marker",
                        "reference": {"path": str(target), "state": state},
                        "marker": _TRELLIS_MARKER,
                    },
                    _state_requirement(state),
                    [str(root)],
                )
            )
        else:
            _fail(
                "unknown-content",
                "a recorded generated path cannot be classified",
            )
    if pending_unknown:
        _fail_unknown(root, pending_unknown)
    if not platforms:
        _fail(
            "unknown-platform",
            "no configured platform could be proven from the ownership metadata",
        )
    return sorted(platforms), operations


def _private_task_skips(
    optional: Sequence[Mapping[str, Any]], root: Path
) -> dict[str, set[str]]:
    """Map a task folder to the members bound by one private-only skip."""
    skipped: dict[str, set[str]] = {}
    legacy = root / _LEGACY_DIR
    for item in optional:
        if item["decision"] != "private-only" or item["target_path"] is not None:
            continue
        rels = []
        for reference in item["sources"]:
            rel = _parts_relative(Path(reference["path"]), legacy)
            if rel is None:
                continue
            rels.append(rel)
        task_rels = [rel for rel in rels if rel[-1] == _TASK_JSON]
        if len(task_rels) != 1 or not task_rels[0] or task_rels[0][0] != "tasks":
            continue
        folder_parts = task_rels[0][:-1]
        folder = PurePosixPath(*folder_parts).as_posix()
        members = {PurePosixPath(*rel[len(folder_parts) :]).as_posix() for rel in rels}
        if folder in skipped:
            _fail("approval-conflict", "a legacy task has more than one private skip")
        skipped[folder] = members
    return skipped


def _session_targets_complete_skip(
    relative: tuple[str, ...] | None,
    entries: Sequence[Mapping[str, Any]],
    items: Sequence[Mapping[str, Any]],
    root: Path,
) -> bool:
    """True only when a session names one fully private-only task folder."""
    if (
        not relative
        or ".." in relative
        or len(relative) < 3
        or relative[0] != _LEGACY_DIR
        or relative[1] != "tasks"
    ):
        return False
    folder = PurePosixPath(*relative[1:]).as_posix()
    bound = _private_task_skips(items, root).get(folder)
    if not bound or _TASK_JSON not in bound:
        return False
    prefix = folder + "/"
    actual = {
        entry["path"][len(prefix) :]
        for entry in entries
        if entry["type"] == "file" and str(entry["path"]).startswith(prefix)
    }
    return bound == actual


def _git_bytes(root: Path, args: Sequence[str], stdin: bytes | None = None) -> bytes | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            input=stdin,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if completed.returncode == 128:
        return None
    if args[0] == "check-ignore" and completed.returncode not in (0, 1):
        return None
    if args[0] != "check-ignore" and completed.returncode != 0:
        return None
    return completed.stdout


def _legacy_index(
    root: Path, relative_paths: Sequence[str]
) -> tuple[set[str], set[str]]:
    """Return (ignored, tracked) paths relative to ``.trellis``.

    Ignored follows index-aware ``git check-ignore``: a tracked file is not
    ignored. If git cannot answer, nothing is treated as ignored.
    """
    prefix = f"{_LEGACY_DIR}/"
    listed = _git_bytes(root, ["ls-files", "-z", "--", _LEGACY_DIR])
    if listed is None:
        return set(), set()
    tracked = {
        path.decode()[len(prefix) :]
        for path in listed.split(b"\0")
        if path.startswith(prefix.encode())
    }
    repo_paths = [f"{prefix}{rel}" for rel in relative_paths]
    if not repo_paths:
        return set(), tracked
    checked = _git_bytes(
        root,
        ["check-ignore", "-z", "--stdin"],
        b"\0".join(path.encode() for path in repo_paths) + b"\0",
    )
    if checked is None:
        return set(), tracked
    ignored = {
        path.decode()[len(prefix) :]
        for path in checked.split(b"\0")
        if path.startswith(prefix.encode())
    }
    return ignored, tracked


def _fail_unknown(root: Path, relative_paths: Sequence[str]) -> NoReturn:
    _ignored, tracked = _legacy_index(root, relative_paths)
    _fail(
        "unknown-content",
        "tracked or unignored unknown legacy files need an explicit decision",
        details={
            "paths": list(relative_paths),
            "tracked": [path for path in relative_paths if path in tracked],
            "recommendation": (
                "Do not delete a tracked file from this list. If it is local "
                "noise, stop tracking it and ignore it, then re-run plan. If "
                "it is real legacy data, approve it explicitly before planning "
                "again."
            ),
        },
    )


def _partition_legacy_entries(
    root: Path, entries: Sequence[Mapping[str, Any]]
) -> tuple[list[Mapping[str, Any]], list[str]]:
    """Drop only gitignored paths outside the known layout.

    ``tasks``, ``spec`` and ``lessons`` stay even when gitignore matches them,
    so an ignored ``task.json`` still requires its approval.
    """
    ignored, _tracked = _legacy_index(root, [entry["path"] for entry in entries])
    classified: list[Mapping[str, Any]] = []
    unknown: list[str] = []
    for entry in entries:
        relative = entry["path"]
        top = relative.split("/", 1)[0]
        if top not in _KNOWN_LEGACY_TOP:
            if relative in ignored:
                continue
            unknown.append(relative)
            continue
        classified.append(entry)
    return classified, unknown


def _inventory_coverage(
    entries: Sequence[Mapping[str, Any]],
    closures: Mapping[
        tuple[str, ...], Sequence[tuple[Mapping[str, Any], list[tuple[str, ...]]]]
    ],
    forms: Mapping[tuple[str, ...], str],
    documents: Sequence[tuple[str, Mapping[str, Any], list[tuple[str, ...]]]],
    optional: Sequence[Mapping[str, Any]],
    root: Path,
    hashes: Mapping[str, str],
) -> None:
    """Exact bijection between classified legacy files and approvals.

    Gitignored entries stay in the directory snapshot and are omitted here.
    """
    classified, unknown = _partition_legacy_entries(root, entries)
    if unknown:
        _fail_unknown(root, unknown)
    entries = classified
    empty_task_placeholder = False
    for entry in entries:
        if entry["path"].split("/", 1)[0] not in _KNOWN_LEGACY_TOP:
            _fail("unknown-content", "the legacy directory holds unclassified content")
        if entry["path"] == "tasks/.gitkeep":
            empty_task_placeholder = (
                entry["type"] == "file"
                and entry["checksum"] == hashlib.sha256(b"").hexdigest()
            )
    files = sorted(entry["path"] for entry in entries if entry["type"] == "file")
    folder_names: set[str] = set()
    for name in files:
        parts = PurePosixPath(name).parts
        if len(parts) >= 3 and parts[0] == "tasks" and parts[-1] == _TASK_JSON:
            folder_names.add(PurePosixPath(*parts[:-1]).as_posix())
    folder_members: dict[str, list[str]] = {folder: [] for folder in folder_names}
    for name in files:
        if not name.startswith("tasks/"):
            continue
        if name == "tasks/.gitkeep" and empty_task_placeholder:
            continue
        matches = [folder for folder in folder_names if name.startswith(folder + "/")]
        if not matches:
            _fail("unknown-content", "loose legacy task data cannot be classified")
        folder = max(matches, key=len)
        folder_members[folder].append(name[len(folder) + 1 :])
    coverage: dict[str, int] = {}

    def cover(key: str) -> None:
        coverage[key] = coverage.get(key, 0) + 1

    for folder, records in closures.items():
        folder_prefix = PurePosixPath(*folder[1:]).as_posix()
        for _item, rels in records:
            for rel in rels:
                cover(folder_prefix + "/" + PurePosixPath(*rel).as_posix())
    for category, _item, rels in documents:
        for rel in rels:
            cover(category + "/" + PurePosixPath(*rel).as_posix())
    for item in optional:
        if item["target_path"] is not None:
            # Handoffs may bind the same private journals for several tasks;
            # this is provenance, not duplicate publication of the originals.
            continue
        for reference in item["sources"]:
            rel = _parts_relative(Path(reference["path"]), root / _LEGACY_DIR)
            if rel is not None:
                cover(PurePosixPath(*rel).as_posix())
    for folder, records in closures.items():
        folder_name = PurePosixPath(*folder[1:]).as_posix()
        if folder_name not in folder_members:
            _fail(
                "approval-conflict",
                "an approved task projection has no legacy source",
            )
        form = forms[folder]
        for member in folder_members[folder_name]:
            # File-form closures bind task.json exactly twice (task.md
            # projection plus sidecar); every other legacy member — including
            # existing prd/design/implement attachments — binds exactly once,
            # as does every member of a whole-tree directory approval.
            expected = 1
            if member == _TASK_JSON and form == "file":
                expected = 2
            if coverage.get(folder_name + "/" + member, 0) != expected:
                _fail(
                    "approval-required",
                    "legacy task data is not covered exactly by its approved "
                    "projections",
                )
    skipped = _private_task_skips(optional, root)
    for folder, members in folder_members.items():
        folder_tuple = (_LEGACY_DIR, *PurePosixPath(folder).parts)
        if folder_tuple in closures:
            continue
        if skipped.get(folder) != set(members):
            _fail("approval-required", "a legacy task has no approved projections")
        for member in members:
            if coverage.get(f"{folder}/{member}", 0) != 1:
                _fail(
                    "approval-required",
                    "legacy task data is not covered exactly by its approved "
                    "projections",
                )
    unowned = [
        name
        for name in files
        if name.split("/", 1)[0] in _GENERATED_LEGACY_TOP
        and f"{_LEGACY_DIR}/{name}" not in hashes
        and coverage.get(name, 0) != 1
    ]
    if unowned:
        ignored, _tracked = _legacy_index(root, unowned)
        asked = [name for name in unowned if name not in ignored]
        if asked:
            _fail_unknown(root, asked)
    for name in files:
        top = name.split("/", 1)[0]
        if top in _GENERATED_LEGACY_TOP and (
            f"{_LEGACY_DIR}/{name}" not in hashes and coverage.get(name, 0) != 1
        ):
            continue
        if top == "tasks":
            continue
        if top in _MANDATORY_TOP:
            if coverage.get(name, 0) != 1:
                _fail(
                    "approval-required",
                    "legacy documents are not covered exactly once",
                )
        elif coverage.get(name, 0) > 1:
            _fail("approval-conflict", "optional legacy data is approved at most once")


# ---------------------------------------------------------------------------
# Identity, protection and legacy-tree operations
# ---------------------------------------------------------------------------


def _check_context_handoffs(
    root: Path,
    entries: Sequence[Mapping[str, Any]],
    closures: Mapping[tuple[str, ...], Any],
    projections: Mapping[str, Any],
    items: Sequence[Mapping[str, Any]],
    read_source: ReadOriginal,
    source_ref: str | None,
    head: str | None,
) -> None:
    """Bind private continuation summaries to the entire original context.

    Trellis 0.6.17 stores current_task in .runtime/sessions/*.json, not
    .current-task. Journals have no machine-readable task ownership: when
    present, explicitly approved summaries must cover every unfinished task.
    Nothing here selects an active task or manufactures a summary.
    """
    from sbtd_handoff import _REDACTION_DECLARATION, HandoffStore
    from sbtd_task_state import TaskStateError, TaskStore

    context: dict[str, Mapping[str, Any]] = {}
    active_folders: set[tuple[str, ...]] = set()
    has_journal = False
    for entry in entries:
        if entry["type"] != "file":
            continue
        parts = PurePosixPath(entry["path"]).parts
        reference = {
            "path": str(root / _LEGACY_DIR / entry["path"]),
            "state": {"type": "file", "checksum": entry["checksum"]},
        }
        if parts == (".current-task",):
            if read_source(reference).strip():
                _fail(
                    "invalid-config",
                    "legacy path-line pointers need explicit reconciliation",
                )
            continue
        session = len(parts) == 3 and parts[:2] == (".runtime", "sessions")
        if parts[0] != "workspace" and not session:
            if parts[0] == ".runtime":
                approved = any(
                    item["decision"] == "private-only" and reference in item["sources"]
                    for item in items
                )
                if not approved:
                    _fail(
                        "approval-required",
                        "unknown runtime context needs private approval",
                    )
            continue
        raw = read_source(reference)
        if parts[-1] == ".gitkeep" and not raw:
            continue
        context[reference["path"]] = reference
        if not session:
            has_journal = True
            continue
        if not parts[-1].endswith(".json"):
            _fail("invalid-config", "legacy session records must be JSON")
        record = _json_object(raw, "the legacy session")
        metadata = {
            "platform",
            "last_seen_at",
            "current_task",
            "current_run",
            "session_id",
            "sessionId",
            "sessionID",
            "conversation_id",
            "conversationId",
            "conversationID",
            "transcript_path",
            "transcriptPath",
            "transcript",
        }
        if not isinstance(record, dict) or set(record) - metadata:
            _fail("invalid-config", "legacy session has an unknown structure")
        task_ref = record.get("current_task")
        if task_ref is None:
            if record.get("current_run") is not None:
                _fail("graph-conflict", "a legacy run has no associated task")
            continue
        if not isinstance(task_ref, str) or not task_ref.strip():
            _fail("invalid-config", "legacy current_task must be a nonblank reference")
        task_path = Path(task_ref)
        if task_path.is_absolute():
            relative = _parts_relative(task_path, root)
        else:
            normalized = task_ref.replace("\\", "/")
            while normalized.startswith("./"):
                normalized = normalized[2:]
            relative = PurePosixPath(normalized).parts
            if relative and relative[0] == "tasks":
                relative = (_LEGACY_DIR, *relative)
            elif relative and relative[0] != _LEGACY_DIR:
                relative = (_LEGACY_DIR, "tasks", *relative)
        if relative is None or ".." in relative or (
            relative not in closures
            and not _session_targets_complete_skip(relative, entries, items, root)
        ):
            _fail(
                "graph-conflict",
                "legacy session task has no unique approved projection",
            )
        if relative in closures:
            active_folders.add(relative)

    needed = {
        projection.legacy_id
        for projection in projections.values()
        if projection.document.frontmatter["status"] != "done"
        and (
            has_journal
            or any(
                folder[-1] in projection.aliases or folder[-1] == projection.legacy_id
                for folder in active_folders
            )
        )
    }
    handoff_items = [
        item
        for item in items
        if item["target_path"] is not None
        and Path(item["target_path"]).parent == root / "docs" / "handoffs"
    ]
    if not needed and not handoff_items:
        return
    if not context or not needed:
        _fail(
            "approval-conflict",
            "a handoff requires identified unfinished legacy context",
        )
    store = HandoffStore(TaskStore(root, read_only=True))
    covered: set[str] = set()
    for item in handoff_items:
        if item["decision"] != "redact" or not item["required"]:
            _fail(
                "approval-required",
                "a continuation handoff needs required redact approval",
            )
        if {ref["path"]: ref for ref in item["sources"]} != context:
            _fail(
                "approval-conflict",
                "handoff approval must bind the complete private context",
            )
        candidate = item["candidate_ref"]
        if candidate["state"]["type"] != "file":
            _fail("candidate-conflict", "a handoff candidate must be a Markdown file")
        try:
            text = _candidate_bytes(candidate, None).decode("utf-8")
            handoff = store._parse_text(text)
        except (UnicodeError, TaskStateError):
            _fail("candidate-conflict", "the handoff snapshot is invalid")
        task_id = handoff["task_id"]
        if task_id not in needed or task_id in covered:
            _fail("graph-conflict", "handoff task identity is unexpected or duplicated")
        fields = projections[task_id].document.frontmatter
        expected = {
            "task_id": task_id,
            "task_path": f"ai/tasks/{task_id}/task.md",
            "project_root": str(root),
            "branch": fields["branch"],
            "head": head,
            "task_status": fields["status"],
            "workflow_mode": fields["workflow_mode"],
            "mode_source": fields["mode_source"],
            "mode_note": fields["mode_note"],
            "redaction": _REDACTION_DECLARATION,
        }
        if fields["branch"] != source_ref or any(
            handoff[key] != value for key, value in expected.items()
        ):
            _fail(
                "candidate-conflict",
                "handoff identity, revision or task state does not match",
            )
        content = handoff["content"]
        if (
            not content["goal"].strip()
            or not content["next_action"].strip()
            or not any(value.strip() for value in content["remaining"])
        ):
            _fail(
                "candidate-conflict",
                "handoff must state its goal, remaining work and next action",
            )
        target = Path(item["target_path"])
        date = datetime.fromisoformat(handoff["created_at"].replace("Z", "+00:00"))
        expected_name = f"{date:%Y_%m_%d}-{store._task_key(task_id)}.md"
        if target.name != expected_name:
            _fail(
                "target-conflict",
                "handoff filename must bind its task and snapshot date",
            )
        snapshot_fields = {
            key: value for key, value in handoff.items() if key != "summary"
        }
        if store._render(snapshot_fields) != text:
            _fail("candidate-conflict", "handoff body must match its approved snapshot")
        covered.add(task_id)
    if covered != needed:
        _fail(
            "approval-required",
            "unfinished workspace context requires approved handoffs",
        )
    tracked = store.tasks._git("ls-files", "-z", "--", "docs/handoffs")
    if head is not None and tracked.returncode:
        _fail("private-scope", "handoff tracked state cannot be verified")
    if tracked.returncode == 0 and tracked.stdout:
        _fail("private-scope", "handoff storage must not be tracked")
    _check_handoff_ignore(root, [Path(item["target_path"]) for item in handoff_items])


def _check_handoff_ignore(root: Path, targets: Sequence[Path]) -> None:
    """Evaluate planned ignore bytes without changing the selected project."""
    import tempfile

    from onboard import gitignore_verdicts
    from sbtd_migration import _append_blocks
    from sbtd_task_state import TaskStore

    ignore_path = root / ".gitignore"
    state = snapshot(ignore_path)
    current = b"" if state["type"] == "absent" else read_file(ignore_path, state)
    operation = _ignore_operation(root)
    planned = _append_blocks(current, [operation]) if operation is not None else current
    with tempfile.TemporaryDirectory(prefix="sbtd-handoff-ignore-") as directory:
        sandbox = Path(directory)
        git = TaskStore(sandbox)
        initialized = git._git("init", "--quiet")
        if initialized.returncode:
            _fail("private-scope", "handoff ignore protection cannot be verified")
        (sandbox / ".gitignore").write_bytes(planned)
        for relative in ("docs/.gitignore", "docs/handoffs/.gitignore"):
            source = root / relative
            source_state = snapshot(source)
            if source_state["type"] == "absent":
                continue
            content = read_file(source, source_state)
            target = sandbox / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        probes = (
            "docs/handoffs/",
            *(path.relative_to(root).as_posix() for path in targets),
        )
        verdicts = gitignore_verdicts(sandbox, probes, env=git._git_environment())
        if isinstance(verdicts, str) or not all(
            verdict.ignored for verdict in verdicts.values()
        ):
            _fail(
                "private-scope",
                "planned ignore rules do not protect every private handoff",
            )


def _identity_operation(root: Path) -> dict[str, Any] | None:
    legacy_path = root / _LEGACY_DIR / _DEVELOPER_NAME
    legacy_state = snapshot(legacy_path)
    store = DeveloperStore(root, read_only=True)
    resolved = store.resolve()
    if resolved.status == "ready":
        return None
    if resolved.status != "needs-name" or not resolved.first_write_eligible:
        _fail(
            "identity-conflict",
            "the current developer identity state cannot host a migration",
        )
    legacy_name: str | None = None
    if legacy_state["type"] == "file":
        legacy_name = read_legacy_identity(read_file(legacy_path, legacy_state))
    elif legacy_state["type"] != "absent":
        _fail("identity-conflict", "the legacy identity path is not a normal file")
    if legacy_name is None:
        # No old or new identity: the runtime asks on first use; a migration
        # never invents or guesses a name.
        return None
    planned = store.plan(legacy_name)
    if planned.status != "planned":
        _fail("identity-conflict", "the legacy identity cannot be migrated safely")
    target = root / ".sbtd" / "developer"
    if snapshot(target) != _ABSENT:
        _fail("identity-conflict", "the current identity target is not missing")
    _check_target_lineage(target, root)
    source = {"path": str(legacy_path), "state": legacy_state}
    return _operation(
        "apply",
        "file",
        target,
        "name",
        {"kind": "migrate-developer", "source_ref": source, "name": legacy_name},
        {"kind": "config-entry", "reference": dict(source), "key_path": ["name"]},
        _state_requirement(_ABSENT),
        [str(root)],
    )


def _ignore_operation(root: Path) -> dict[str, Any] | None:
    from onboard import missing_file_lines

    asset = _present_file_reference(_IGNORE_ASSET, "the local ignore asset")
    gitignore = root / ".gitignore"
    before = snapshot(gitignore)
    if before["type"] == "directory":
        _fail("target-conflict", "the ignore path is not a writable file")
    current = b"" if before["type"] == "absent" else read_file(gitignore, before)
    try:
        asset_text = read_file(Path(asset["path"]), asset["state"]).decode("utf-8")
        current_text = current.decode("utf-8")
    except UnicodeDecodeError:
        _fail("invalid-config", "managed ignore content is not UTF-8 text")
    if not missing_file_lines(asset_text, current_text):
        return None
    if before["type"] == "absent":
        _check_target_lineage(gitignore, root)
    return _operation(
        "apply",
        "gitignore",
        gitignore,
        "local-ignore",
        {"kind": "ensure-file-block", "source_ref": asset},
        {"kind": "template-source", "reference": dict(asset)},
        _state_requirement(before),
        [str(root)],
    )


def _publication_operation(root: Path, item: Mapping[str, Any]) -> dict[str, Any]:
    candidate = item["candidate_ref"]
    target = Path(item["target_path"])
    directory = candidate["state"]["type"] == "directory"
    owner_kind = (
        "directory" if directory else "markdown" if target.suffix == ".md" else "file"
    )
    return _operation(
        "apply",
        owner_kind,
        target,
        "whole-resource",
        {
            "kind": "copy-directory" if directory else "copy-file",
            "source_ref": copy.deepcopy(candidate),
        },
        {"kind": "template-source", "reference": copy.deepcopy(candidate)},
        _state_requirement(_ABSENT),
        [str(root)],
    )


def _legacy_cleanup_operation(
    root: Path, legacy_reference: Mapping[str, Any]
) -> dict[str, Any]:
    target = root / _LEGACY_DIR
    return _operation(
        "cleanup",
        "directory",
        target,
        "whole-resource",
        {"kind": "remove"},
        {"kind": "template-source", "reference": dict(legacy_reference)},
        _state_requirement(legacy_reference["state"]),
        [str(root)],
    )


# ---------------------------------------------------------------------------
# Shared HOME/config resources (owned once, full dependent closure)
# ---------------------------------------------------------------------------


def _shared_operations(
    roots: Sequence[Path],
    approved_targets: Collection[Path] = (),
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Pause the exact pinned v1.0.15 global routing, retire pinned old Skills.

    Foreign global content is preserved untouched. Customized legacy routing
    blocks instead of silently remaining active; only byte-exact known ownership
    authorizes a pause. Cleanup stays gated on later verification; no new wiring
    is deployed here.
    """
    from onboard import (
        default_codex_home,
        omp_global_agents_path,
        resolve_global_skills_dir,
        user_home,
    )

    dependents = sorted(str(root) for root in roots)
    pins = _ownership_pins()
    operations: list[dict[str, Any]] = []
    needed_roots: dict[str, str] = {}
    codex_home = default_codex_home()
    routing_targets = [("codex-home", codex_home, codex_home / "AGENTS.md")]
    omp_home = user_home() / ".omp"
    # Existence only. Every path component is checked nofollow; children are
    # not walked. Unrelated links inside the directory are not routing targets.
    omp_presence = _omp_root_presence(omp_home)
    if omp_presence == "directory":
        routing_targets.append(("omp-home", omp_home, omp_global_agents_path(omp_home)))
    elif omp_presence == "file":
        _fail("ownership-conflict", "the existing OMP root is not a safe directory")
    pause = _present_file_reference(_PAUSE_ASSET, "the maintenance asset")
    current_routing = read_file(_PACKAGE / "templates" / "agents" / "AGENTS.global.md")
    seen_targets: set[Path] = set()
    for root_kind, shared_root, agents in routing_targets:
        if agents in seen_targets:
            continue
        seen_targets.add(agents)
        if agents in approved_targets:
            continue
        agents_state = snapshot(agents)
        if agents_state == {"type": "file", "checksum": pins["agents"]}:
            operations.append(
                _operation(
                    "apply",
                    "markdown",
                    agents,
                    "pause-legacy-routing",
                    {"kind": "ensure-file-block", "source_ref": pause},
                    {
                        "kind": "template-source",
                        "reference": {"path": str(agents), "state": agents_state},
                    },
                    _state_requirement(agents_state),
                    dependents,
                )
            )
            needed_roots[str(shared_root)] = root_kind
        elif agents_state["type"] == "file":
            raw = read_file(agents, agents_state)
            if raw != current_routing and re.search(
                rb"\btrellis\b", raw, re.IGNORECASE
            ):
                _fail(
                    "ownership-conflict",
                    "customized legacy global routing requires explicit reconciliation",
                )
    skills_root, _source = resolve_global_skills_dir()
    if _lineage_probe(skills_root) == "directory":
        _physical_root(skills_root)
        for name in sorted(pins["skills"]):
            target = skills_root / name
            state = snapshot(target)
            if state["type"] == "absent":
                continue
            if state != pins["skills"][name]:
                continue  # drifted or custom content is preserved, never retired
            operations.append(
                _operation(
                    "cleanup",
                    "directory",
                    target,
                    "whole-resource",
                    {"kind": "remove"},
                    {
                        "kind": "skill-identity",
                        "reference": {"path": str(target), "state": state},
                        "name": name,
                    },
                    _state_requirement(state),
                    dependents,
                )
            )
            needed_roots[str(skills_root)] = "skills"
    shared_roots: list[dict[str, Any]] = [
        {"kind": kind, "path": path, "dependent_projects": dependents}
        for path, kind in sorted(needed_roots.items())
    ]
    shared_roots = [
        record
        for record in shared_roots
        if not any(
            other["path"] != record["path"]
            and Path(record["path"]).is_relative_to(Path(other["path"]))
            for other in shared_roots
        )
    ]
    return shared_roots, operations


# ---------------------------------------------------------------------------
# Physical alias guard (same rule as the apply-time context validation)
# ---------------------------------------------------------------------------


def _check_physical_aliases(operations: Sequence[Mapping[str, Any]]) -> None:
    seen: dict[tuple[int, int], str] = {}
    for operation in operations:
        target = Path(operation["target"])
        state = snapshot(target)
        if state["type"] == "absent":
            continue
        metadata = target.lstat()
        identity = metadata.st_dev, metadata.st_ino
        if (state["type"] == "file" and metadata.st_nlink > 1) or seen.setdefault(
            identity, str(target)
        ) != str(target):
            _fail(
                "physical-alias",
                "managed resources have ambiguous physical ownership",
            )


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------


def plan_migration(
    project_roots: Sequence[Any],
    backup_root: Any,
    custodian: Any,
    publication_path: Any,
    *,
    tool_versions: Mapping[str, Any],
    deployment_mode: str | None = None,
    hooks_authorized: bool = False,
    deployment_platform: str = "codex",
    routing_approvals: Any = None,
    routing_approval_key: Any = None,
) -> dict[str, Any]:
    """Verify the authorized preparation and seal a bound migration manifest.

    Read-only unless ``routing_approval_key`` is set. That path signs only the
    named approval file, and only after the key matches the installed public
    key. An existing verified-private ``backup_root``, exact publication
    decisions with existing candidates, current source and target states, the
    per-project Git binding, the pinned legacy ownership metadata and the
    identity chain are all validated; any conflict blocks the plan with zero
    writes instead of guessing.
    """
    if deployment_mode not in {None, "init", "init-projects"}:
        _fail("invalid-argument", "the deployment mode must be explicitly supported")
    if hooks_authorized and deployment_mode != "init":
        _fail(
            "scope-conflict",
            "global hooks require an explicitly planned full deployment",
        )
    if deployment_platform not in {"codex", "omp"}:
        _fail(
            "invalid-argument", "the deployment platform must be explicitly supported"
        )
    from sbtd_migration import _RETENTION, _project_revision

    if (
        isinstance(project_roots, (str, bytes))
        or not isinstance(project_roots, Sequence)
        or not project_roots
    ):
        _fail("invalid-argument", "at least one project root is required")
    if not isinstance(custodian, str) or not custodian.strip():
        _fail("invalid-argument", "a custodian is required")
    if (
        not isinstance(tool_versions, Mapping)
        or set(tool_versions)
        != {
            "onboard",
            "graft",
        }
        or any(
            not isinstance(value, str) or not value.strip()
            for value in tool_versions.values()
        )
    ):
        _fail(
            "invalid-argument",
            "tool versions must name the actual onboard and graft builds",
        )
    roots = [_physical_root(value) for value in project_roots]
    if len(set(roots)) != len(roots):
        _fail("scope-conflict", "duplicate project root in the selected batch")
    for index, root in enumerate(roots):
        for other in roots[index + 1 :]:
            if (
                root.samefile(other)
                or root.is_relative_to(other)
                or other.is_relative_to(root)
            ):
                _fail(
                    "scope-conflict", "selected project roots must not overlap or alias"
                )
    vault = _private_vault(backup_root)
    for root in roots:
        if vault.is_relative_to(root) or root.is_relative_to(vault):
            _fail(
                "private-scope",
                "the private backup root must stay outside the selected projects",
            )
    items = _load_publication_items(publication_path, vault)
    assigned = _assign_items(roots, items)
    private_strings = _private_strings(vault)
    if routing_approval_key is not None:
        if routing_approvals is None:
            _fail(
                "invalid-argument",
                "a routing approval key requires the routing approval file",
            )
        _sign_routing_approval(
            Path(routing_approvals), Path(routing_approval_key), vault, roots
        )
    routing_items = _load_routing_approvals(routing_approvals, vault)
    routing_path = Path(routing_approvals) if routing_approvals is not None else vault
    shared_replacements, private_replacements = (
        _approved_routing_operations(routing_items, roots, vault, routing_path)
        if routing_approvals is not None
        else ([], {})
    )
    approved_targets = {Path(item["target_path"]) for item in routing_items}

    def read_current(reference: Mapping[str, Any]) -> bytes:
        return read_file(Path(reference["path"]), reference["state"])

    projects: list[dict[str, Any]] = []
    for root in roots:
        project_items = assigned[root]
        for item in project_items:
            _check_item_freshness(root, item, vault)
        source_ref, head = _project_revision(root)
        legacy_path = root / _LEGACY_DIR
        legacy_state = snapshot(legacy_path)
        if legacy_state["type"] != "directory":
            _fail(
                "missing-legacy",
                "the selected project has no legacy Trellis data",
            )
        legacy_reference = {"path": str(legacy_path), "state": legacy_state}
        _state, entries = directory_snapshot(legacy_path)
        _check_legacy_version(root)
        hashes, hashes_reference = _template_hashes(root)
        platforms, platform_ops = _platform_operations(
            root, hashes, hashes_reference, approved_targets
        )
        closures, documents, optional = _classify_project_items(root, project_items)
        projections, forms = _validate_project_closures(
            root, closures, documents, read_current, private_strings
        )
        _inventory_coverage(entries, closures, forms, documents, optional, root, hashes)
        _check_context_handoffs(
            root,
            entries,
            closures,
            projections,
            project_items,
            read_current,
            source_ref,
            head,
        )
        identity_op = _identity_operation(root)
        publication_ops = [
            _publication_operation(root, item)
            for item in sorted(
                (item for item in project_items if item["decision"] != "private-only"),
                key=lambda item: item["target_path"],
            )
        ]
        private_ops: list[dict[str, Any]] = []
        if identity_op is not None or publication_ops:
            ignore_op = _ignore_operation(root)
            if ignore_op is not None:
                private_ops.append(ignore_op)
        if identity_op is not None:
            private_ops.append(identity_op)
        private_ops.extend(publication_ops)
        private_ops.extend(platform_ops)
        private_ops.extend(private_replacements.get(root, []))
        private_ops.append(_legacy_cleanup_operation(root, legacy_reference))
        projects.append(
            {
                "root": str(root),
                "source_ref": source_ref,
                "head": head,
                "platforms": platforms,
                "sources": [legacy_reference],
                "private_operations": private_ops,
                "shared_operation_ids": [],
            }
        )
    shared_roots, shared_ops = _shared_operations(roots, approved_targets)
    for operation in shared_replacements:
        target = Path(operation["target"])
        role = operation["ownership"]["role"]
        root_path = target.parent if role == "codex-global" else target.parent.parent
        kind = "codex-home" if role == "codex-global" else "omp-home"
        if not any(record["path"] == str(root_path) for record in shared_roots):
            shared_roots.append(
                {
                    "kind": kind,
                    "path": str(root_path),
                    "dependent_projects": sorted(str(root) for root in roots),
                }
            )
        shared_ops.append(operation)
    shared_ids = sorted(operation["operation_id"] for operation in shared_ops)
    for project in projects:
        project["shared_operation_ids"] = list(shared_ids)
    payload = {
        "projects": projects,
        "shared_roots": shared_roots,
        "shared_operations": shared_ops,
        "publication_decisions": {"schema_version": 1, "items": copy.deepcopy(items)},
        "routing_approvals": (
            {"path": str(routing_path), "state": snapshot(routing_path)}
            if routing_approvals is not None
            else None
        ),
        "custodian": custodian,
        "backup_root": str(vault),
        "created_at": datetime.now().astimezone().isoformat(timespec="microseconds"),
        "retention": copy.deepcopy(_RETENTION),
        "tool_versions": dict(tool_versions),
        "deployment": None,
    }
    if deployment_mode is not None:
        from sbtd_graft_deployment import attach_deployment

        attach_deployment(
            payload,
            project_only=deployment_mode == "init-projects",
            hooks_authorized=hooks_authorized,
            platform=deployment_platform,
        )
    _check_physical_aliases(
        [
            operation
            for project in projects
            for operation in project["private_operations"]
        ]
        + shared_ops
    )
    _bind_approved_routing(payload, roots, bind_live=True)
    return contracts.seal_document("manifest", payload)
