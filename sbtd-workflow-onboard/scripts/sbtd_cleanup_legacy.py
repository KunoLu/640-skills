"""Confirmed, project-scoped legacy cleanup with private plans and backups.

These documents have their own schema version; they are not migration contract
objects. A digest binds the displayed plan, never substitutes for scope/identity
validation. Plan writes only its private evidence, not cleanup targets.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

import onboard_contracts as contracts
from sbtd_cleanup_targets import (
    RETIRED_SKILL_NAMES,
    detect_mcp_targets,
    detect_project_targets,
    detect_skill_targets,
    legacy_mcp_locations,
    remove_json_server_key,
    remove_marker_blocks,
    remove_toml_server_table,
    strict_json_object,
)
from sbtd_migration_files import (
    backup_reference,
    install_reference,
    preflight_windows_permissions,
    read_file,
    remove_reference,
    require_private_directory,
    save_document,
    snapshot,
    write_file,
)
from sbtd_project import TaskDataError


def _fail(code: str, message: str) -> NoReturn:
    raise contracts.ContractError(code, message, exit_code=2)

_SELECTION_KEYS = {"host", "configs", "projects", "vault", "retiring_launchers"}
_EVIDENCE_KEYS = {
    "descriptor": frozenset({"kind", "path"}),
    "operation-results": frozenset({"kind", "path"}),
    "manifest-deployment": frozenset({"kind", "manifest", "deployment"}),
    "upgrade-plan-apply": frozenset({"kind", "plan", "receipt"}),
}
_COMPARE_SKIP = {"before", "trellis", "graft"}
_WINDOWS_VENDOR_OVERLAP = (
    "Windows vendor cleanup would write a retirement file without preserving its ACL. "
    "Retire the Graft entry separately, then generate a fresh cleanup plan."
)


def _retirement():
    try:
        import sbtd_retirement as retirement
    except ImportError:
        _fail("runtime-unavailable", "retirement discovery is unavailable")
    return retirement


def _history_names() -> frozenset[str]:
    from sbtd_retirement_paths import HISTORY_DIRS

    return frozenset(HISTORY_DIRS)

def _owned_path(value: object) -> Path:
    if not isinstance(value, str) or not value.strip():
        _fail("invalid-path", "retirement paths must be absolute")
    path = Path(value).expanduser()
    if not path.is_absolute():
        _fail("invalid-path", "retirement paths must be absolute")
    for part in (path, *path.parents):
        if part.exists() and part.is_symlink():
            _fail("invalid-path", "retirement paths must not follow symlinks")
    return path.resolve()



def _mode_text(path: Path) -> str | None:
    try:
        info = path.lstat()
    except OSError:
        return None
    if stat.S_ISLNK(info.st_mode):
        return None
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        return None
    return f"{stat.S_IMODE(info.st_mode):04o}"

def _contract_object(value: Any) -> dict[str, Any] | None:
    """Canonical JSON object, or None when the value is not contract JSON.

    A discovery double that is not a dict is not an authority source and must
    not be embedded in a sealed plan.
    """
    if type(value) is not dict:
        return None
    try:
        raw = contracts.canonical_json_bytes(value)
    except contracts.ContractError:
        return None
    parsed = json.loads(raw)
    if type(parsed) is not dict:
        return None
    return parsed


def _home(environ: Mapping[str, str]) -> Path:
    return Path(environ.get("HOME") or environ.get("USERPROFILE") or Path.home()).resolve()



def _canonical_report(value: Mapping[str, Any]) -> bytes:
    return contracts.canonical_json_bytes(value)


def _evidence_bindings(
    evidence: Sequence[Mapping[str, Any]], vault: Path | None
) -> list[dict[str, Any]]:
    if not evidence:
        return []
    if vault is None:
        _fail("invalid-argument", "retirement evidence requires a private vault")
    bound = []
    for item in evidence:
        if not isinstance(item, Mapping):
            _fail("invalid-argument", "retirement evidence must be a binding")
        kind = item.get("kind")
        allowed = _EVIDENCE_KEYS.get(kind)
        if allowed is None or set(item) != allowed:
            _fail("invalid-argument", "retirement evidence binding is not a known kind")
        copied = {key: item[key] for key in sorted(allowed)}
        for key in allowed - {"kind"}:
            path = _safe_path(Path(copied[key]))
            if not path.is_relative_to(vault):
                _fail(
                    "scope-conflict",
                    "retirement evidence must stay inside the private vault",
                )
            copied[key] = str(path)
        bound.append(copied)
    return bound


def _inspect_selections(
    selections: Mapping[str, Any], vault: Path | None
) -> dict[str, Any]:
    if not isinstance(selections, Mapping) or set(selections) != _SELECTION_KEYS:
        _fail("invalid-argument", "retirement selections are not the closed domain")
    host = selections["host"]
    if host not in {"codex", "omp", None}:
        _fail("invalid-argument", "retirement host is not a current domain")
    configs = selections["configs"]
    projects = selections["projects"]
    launchers = selections["retiring_launchers"]
    if (
        not isinstance(configs, list)
        or not isinstance(projects, list)
        or not isinstance(launchers, list)
    ):
        _fail("invalid-argument", "retirement selections are not the closed domain")
    copied_configs = []
    for item in configs:
        if (
            not isinstance(item, Mapping)
            or set(item) != {"role", "path"}
            or item["role"] not in {"codex-mcp", "codex-hooks", "omp-mcp"}
        ):
            _fail("invalid-argument", "retirement config is not a current domain")
        copied_configs.append(
            {"role": item["role"], "path": str(_owned_path(item["path"]))}
        )
    return {
        "host": host,
        "configs": copied_configs,
        "projects": [str(_owned_path(item)) for item in projects],
        "vault": None if vault is None else str(vault),
        "retiring_launchers": [str(_owned_path(item)) for item in launchers],
    }


def _retirement_view(
    selections: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
    *,
    purpose: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    module = _retirement()
    report = module.inspect_retirement(
        selections=dict(selections), evidence=list(evidence)
    )
    view = module.render_candidates(report, purpose=purpose)
    if not isinstance(report, dict) or not isinstance(view, dict):
        _fail("invalid-document", "retirement discovery did not return an object")
    return report, view


def _graft_identity(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Full sealed-vs-fresh authority document.

    desired, backup_ref, id, evidence paths and every other field are part of
    the comparison. Cleanup does not recompute those fields, so none are
    dropped. write_authority is read from the candidate; it is never injected.
    """
    if not isinstance(candidate, Mapping):
        _fail("invalid-document", "a retirement candidate is not an object")
    copied = _contract_object(dict(candidate))
    if copied is None:
        _fail("invalid-document", "retirement candidate is not canonical contract JSON")
    if copied.get("write_authority") is not True:
        _fail("ownership-conflict", "retirement candidate has no write authority")
    for key in ("path", "action", "before", "entries"):
        if key not in copied:
            _fail("invalid-document", "retirement candidate is missing a bound field")
    if not isinstance(copied["entries"], list):
        _fail("invalid-document", "a retirement candidate has no entry list")
    return copied


def _actionable_graft(view: Mapping[str, Any]) -> list[dict[str, Any]]:
    if view.get("stop"):
        return []
    raw = view.get("candidates") or []
    if not isinstance(raw, list):
        _fail("invalid-document", "retirement candidates are not a list")
    found: dict[str, dict[str, Any]] = {}
    for item in raw:
        if not isinstance(item, Mapping) or item.get("write_authority") is not True:
            continue
        path = str(item.get("path"))
        if Path(path).name in _history_names():
            _fail("scope-conflict", "historical graft data is not a cleanup candidate")
        if path in found:
            _fail("scope-conflict", "retirement returned two candidates for one path")
        found[path] = dict(item)
    return [found[key] for key in sorted(found)]


def _attach_graft(
    groups: Sequence[list[dict[str, Any]]], graft_candidates: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    by_path = {item["path"]: item for group in groups for item in group}
    standalone = []
    for graft in graft_candidates:
        path = str(graft["path"])
        existing = by_path.get(path)
        if existing is None:
            standalone.append(dict(graft, kind="graft-retire", path=path))
            continue
        if graft.get("action") == "remove-file":
            _fail(
                "unsupported-operation",
                "a created retirement file cannot share another cleanup edit",
            )
        existing["graft"] = dict(graft, path=path)
    return standalone


def _descriptor_evidence(value: str | None, vault: Path) -> list[dict[str, str]]:
    if not value:
        return []
    path = _safe_path(Path(value).expanduser())
    if not path.is_relative_to(vault):
        _fail(
            "scope-conflict",
            "retirement evidence must stay inside the private vault",
        )
    return [{"kind": "descriptor", "path": str(path)}]


def _host_domains(environ: Mapping[str, str]) -> list[tuple[str, list[dict[str, str]]]]:
    home = Path(
        environ.get("HOME") or environ.get("USERPROFILE") or str(Path.home())
    ).resolve()
    codex = Path(environ.get("CODEX_HOME") or (home / ".codex"))
    from sbtd_omp_sources import active_omp_paths

    active = active_omp_paths(home=home, environ=environ)
    return [
        (
            "codex",
            [
                {"role": "codex-mcp", "path": str(codex / "config.toml")},
                {"role": "codex-hooks", "path": str(codex / "hooks.json")},
            ],
        ),
        ("omp", [{"role": "omp-mcp", "path": str(active["target"])}]),
    ]


def _cleanup_selections(
    roots: Sequence[Path], vault: Path, environ: Mapping[str, str]
) -> list[dict[str, Any]]:
    projects = [str(root) for root in roots]
    selections = []
    for host, configs in _host_domains(environ):
        bound = []
        for item in configs:
            bound.append(
                {"role": item["role"], "path": str(_safe_path(Path(item["path"])))}
            )
        selections.append(
            {
                "host": host,
                "configs": bound,
                "projects": list(projects),
                "vault": str(vault),
                "retiring_launchers": [],
            }
        )
    return selections


def _merged_graft(
    roots: Sequence[Path],
    environ: Mapping[str, str],
    vault: Path,
    evidence: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Inspect the active host domain. Do not embed a non-document merge."""
    module = _retirement()
    selections = _cleanup_selections(roots, vault, environ)
    reports = []
    for item in selections:
        report, _view = _retirement_view(item, evidence, purpose="cleanup")
        copied = _contract_object(report)
        if copied is None:
            _fail("invalid-document", "retirement inspection is not canonical contract JSON")
        reports.append(copied)
    merged = _contract_object(module.merge_reports(reports))
    # A non-document merge result is not authority. Render from the canonical
    # per-host report instead of embedding or following that object.
    view = _contract_object(
        module.render_candidates(merged if merged is not None else reports[-1], purpose="cleanup")
    )
    if view is None:
        _fail("invalid-document", "retirement candidate view is not canonical contract JSON")
    sealed = {"reports": reports, "selections": selections}
    if merged is not None:
        sealed["merged"] = merged
    return sealed, view, _actionable_graft(view)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="microseconds")


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(contracts.canonical_json_bytes(payload)).hexdigest()


def _safe_path(path: Path) -> Path:
    if not path.is_absolute() or path != path.resolve():
        _fail("invalid-path", "cleanup paths must be absolute canonical paths")
    if any(part.is_symlink() for part in (path, *path.parents)):
        _fail("invalid-path", "cleanup paths must not follow symlinks")
    return path


def _roots(roots: Sequence[Path], vault: Path, home: Path) -> list[Path]:
    result: list[Path] = []
    for root in roots:
        _safe_path(root)
        if not root.is_dir() or root in {home, Path(root.anchor)}:
            _fail("scope-conflict", "select a project, not HOME or a filesystem root")
        if root.is_relative_to(vault) or vault.is_relative_to(root):
            _fail(
                "scope-conflict", "backup directory must be outside selected projects"
            )
        if any(
            root.is_relative_to(other) or other.is_relative_to(root) for other in result
        ):
            _fail(
                "scope-conflict",
                "cleanup project roots must be distinct and non-nested",
            )
        result.append(root)
    if not result:
        _fail("scope-conflict", "cleanup requires explicitly selected project roots")
    return result


def _all_candidates(plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    payload = plan["payload"]
    candidates = [
        item for project in payload["projects"] for item in project["candidates"]
    ]
    for kind in ("skills", "mcp"):
        candidates.extend(payload["shared"][kind]["candidates"])
    graft = payload.get("graftRetirement") or {}
    candidates.extend(graft.get("candidates") or [])
    return candidates

def _graft_candidate(candidate: Mapping[str, Any]) -> Mapping[str, Any] | None:
    return candidate if candidate.get("kind") == "graft-retire" else candidate.get("graft")


def _windows_vendor_overlap(plan: Mapping[str, Any]) -> bool:
    if os.name != "nt":
        return False
    candidates = _all_candidates(plan)
    retirement = {Path(item["path"]) for item in candidates if _graft_candidate(item) is not None}
    if not retirement:
        return False
    return any(
        path.is_relative_to(resource) or resource.is_relative_to(path)
        for item in candidates if item["kind"] == "trellis-uninstall"
        for resource in (Path(row["path"]) for row in item["trellis"]["payload"]["resources"])
        for path in retirement
    )



def _check_candidate_paths(plan: Mapping[str, Any], vault: Path) -> None:
    seen: list[Path] = []
    for candidate in _all_candidates(plan):
        path = _safe_path(Path(candidate["path"]))
        if path.is_relative_to(vault) or vault.is_relative_to(path):
            _fail("scope-conflict", "backup directory overlaps a cleanup target")
        if any(
            path.is_relative_to(other) or other.is_relative_to(path) for other in seen
        ):
            _fail("scope-conflict", "cleanup targets must be distinct and non-nested")
        seen.append(path)


def _blocked(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for group in [*payload["projects"], *payload["shared"].values()]
        for item in group["blocked"]
    ]


def _seal_candidates(detected: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidates": [
            dict(item, before=snapshot(Path(item["path"])))
            for item in detected["candidates"]
        ],
        "blocked": detected["blocked"],
    }


def plan_cleanup_legacy(
    roots: Sequence[Path],
    backup_root: Path,
    *,
    skills_root: Path,
    environ: Mapping[str, str],
    retirement_evidence: str | None = None,
) -> tuple[dict[str, Any], int]:
    vault = require_private_directory(_safe_path(backup_root))
    home = Path(
        environ.get("HOME") or environ.get("USERPROFILE") or Path.home()
    ).resolve()
    selected = _roots(roots, vault, home)
    _safe_path(skills_root)
    projects = []
    for root in selected:
        detected = detect_project_targets(root)
        ready = []
        for candidate in detected["candidates"]:
            if candidate["kind"] == "trellis-uninstall":
                from sbtd_trellis_uninstall import prepare_trellis_uninstall

                try:
                    candidate["trellis"] = prepare_trellis_uninstall(
                        root, environ=environ
                    )
                    if candidate["trellis"]["payload"]["status"] != "ready":
                        detected["blocked"].append(
                            {
                                "path": candidate["path"],
                                "kind": candidate["kind"],
                                "reason": candidate["trellis"]["payload"].get(
                                    "unavailable_code", "uninstall-unavailable"
                                ),
                            }
                        )
                        continue
                except (contracts.ContractError, OSError, ValueError) as error:
                    detected["blocked"].append(
                        {
                            "path": candidate["path"],
                            "kind": candidate["kind"],
                            "reason": getattr(error, "code", "uninstall-unavailable"),
                        }
                    )
                    continue
            ready.append(candidate)
        detected["candidates"] = ready
        projects.append(dict(_seal_candidates(detected), root=str(root)))
    shared = {
        "skills": _seal_candidates(
            detect_skill_targets(skills_root, retired=RETIRED_SKILL_NAMES)
        ),
        "mcp": _seal_candidates(detect_mcp_targets(environ=environ)),
    }
    evidence = _descriptor_evidence(retirement_evidence, vault)
    _report, view, grafts = _merged_graft(selected, environ, vault, evidence)
    standalone = _attach_graft(
        [project["candidates"] for project in projects]
        + [shared["skills"]["candidates"], shared["mcp"]["candidates"]],
        grafts,
    )
    payload = {
        "purpose": "cleanup-legacy",
        "created_at": _now(),
        "backup_root": str(vault),
        "home": str(home),
        "skills_root": str(skills_root),
        "projects": projects,
        "shared": shared,
        "graftRetirement": {
            "selections": _report["selections"],
            "evidence": evidence,
            "report": _report,
            "view": view,
            "candidates": _seal_candidates({"candidates": standalone, "blocked": []})[
                "candidates"
            ],
        },
    }
    plan = {"schema_version": 1, "payload": payload, "plan_id": _digest(payload)}
    _check_candidate_paths(plan, vault)
    retirement_block = None
    if _windows_vendor_overlap(plan):
        retirement_block = _WINDOWS_VENDOR_OVERLAP
    elif os.name == "nt" and view.get("stop"):
        retirement_block = view.get("stop_reason") or "Windows retirement inspection is blocked."
    status = (
        "blocked"
        if _blocked(payload) or retirement_block is not None
        else ("planned" if _all_candidates(plan) else "nothing-to-clean")
    )
    destination = vault / f"cleanup-legacy-plan-{plan['plan_id']}.json"
    save_document(destination, plan, private_root=vault)
    return {
        "mode": "cleanup-legacy",
        "phase": "plan",
        "status": status,
        **({"reason": retirement_block} if retirement_block else {}),
        "plan_id": plan["plan_id"],
        "projects": [{"root": str(root), "status": status} for root in selected],
        "cleanup_legacy": {"plan": plan, "plan_path": str(destination)},
    }, 2 if status == "blocked" else 0


def _read_document(path: Path, id_key: str) -> dict[str, Any]:
    _safe_path(path)
    require_private_directory(path.parent)
    document = strict_json_object(read_file(path))
    if (
        type(document.get("schema_version")) is not int
        or document["schema_version"] != 1
        or set(document) != {"schema_version", "payload", id_key}
    ):
        _fail("invalid-document", "unsupported cleanup document")
    if not isinstance(document["payload"], dict) or document[id_key] != _digest(
        document["payload"]
    ):
        _fail(
            "binding-violation",
            "cleanup document content does not match its identifier",
        )
    return document


def _render(candidate: Mapping[str, Any], raw: bytes, *, vault: Path) -> bytes:
    graft = _graft_candidate(candidate)
    if graft is not None:
        raw = _retirement().render_candidate_bytes(raw, graft, vault=vault)
    if candidate["kind"] == "marker-blocks":
        return remove_marker_blocks(raw)
    if candidate["kind"] == "graft-retire":
        return raw
    if candidate["kind"] != "mcp-server-remove":
        _fail("unsupported-operation", "candidate is not a supported file edit")
    remove = (
        remove_toml_server_table
        if candidate["format"] == "toml"
        else remove_json_server_key
    )
    for key in candidate["keys"]:
        raw = remove(raw, key)
    return raw


def _goal(candidate: Mapping[str, Any], backup: Mapping[str, Any], *, vault: Path) -> dict[str, Any]:
    if candidate["kind"] == "graft-retire":
        # This is the same desired state sealed and rechecked before apply.
        return dict(candidate["desired"])
    if candidate.get("action") == "remove-file" or candidate["kind"] in {
        "directory-remove",
        "skill-directory",
        "trellis-uninstall",
    }:
        return {"type": "absent", "checksum": None}
    raw = read_file(Path(backup["path"]), backup["state"])
    return {
        "type": "file",
        "checksum": hashlib.sha256(_render(candidate, raw, vault=vault)).hexdigest(),
    }


def _validate_scope(
    plan: Mapping[str, Any],
    done: Mapping[str, Any],
    progressed: Mapping[str, Any],
    environ: Mapping[str, str],
) -> None:
    payload = plan["payload"]
    if payload.get("purpose") == "retirement-reset":
        _validate_retirement(plan, done, environ)
        return
    vault = require_private_directory(Path(payload["backup_root"]))
    home = Path(
        environ.get("HOME") or environ.get("USERPROFILE") or Path.home()
    ).resolve()
    if str(home) != payload["home"]:
        _fail("scope-conflict", "cleanup HOME changed since the plan")
    _roots([Path(p["root"]) for p in payload["projects"]], vault, home)
    # The confirmed plan owns this selection; ambient settings cannot redirect it.
    skills_root = _safe_path(Path(payload["skills_root"]))
    if _blocked(payload):
        _fail(
            "blocked-target", "resolve blocked cleanup targets and generate a new plan"
        )
    _check_candidate_paths(plan, vault)
    if _windows_vendor_overlap(plan):
        _fail("windows-retirement-vendor-overlap", _WINDOWS_VENDOR_OVERLAP)

    def compare(sealed, detected):
        if detected["blocked"]:
            _fail("blocked-target", "current target inspection is blocked")
        remaining = {
            item["path"]: {
                k: v for k, v in item.items() if k not in _COMPARE_SKIP
            }
            for item in sealed
            if item["path"] not in done and item["path"] not in progressed
        }
        # A receipt-proven vendor transition fully explains why a pending
        # candidate no longer matches its sealed detection; every other path
        # keeps the exact sealed comparison, and the pending path is still
        # held to its recorded transition state below.
        if remaining != {
            item["path"]: item
            for item in detected["candidates"]
            if item["path"] not in progressed
        }:
            _fail(
                "scope-conflict",
                "cleanup candidates differ from current scoped detection",
            )

    for project in payload["projects"]:
        root = Path(project["root"])
        expected = {
            "trellis-uninstall": root / ".trellis",
            "directory-remove": root / ".gitnexus",
            "marker-blocks": root / "AGENTS.md",
        }
        for item in project["candidates"]:
            if expected.get(item["kind"]) != Path(item["path"]) or (
                item["kind"] == "trellis-uninstall" and item["root"] != str(root)
            ):
                _fail(
                    "scope-conflict", "project cleanup path or operation is not allowed"
                )
        compare(project["candidates"], detect_project_targets(root))
    for item in payload["shared"]["skills"]["candidates"]:
        if (
            item["kind"] != "skill-directory"
            or item["name"] not in RETIRED_SKILL_NAMES
            or Path(item["path"]) != skills_root / item["name"]
        ):
            _fail("scope-conflict", "unknown shared Skill deletion")
    compare(
        payload["shared"]["skills"]["candidates"],
        detect_skill_targets(skills_root, retired=RETIRED_SKILL_NAMES),
    )
    if done:
        # Removed keys no longer appear in detection. Their locations must
        # still belong to this environment before a retry or rollback.
        locations = {str(path) for _, path, _, _ in legacy_mcp_locations(environ)}
        for item in payload["shared"]["mcp"]["candidates"]:
            if item["kind"] != "mcp-server-remove" or item["path"] not in locations:
                _fail("scope-conflict", "legacy MCP target is outside the selected environment")
    compare(payload["shared"]["mcp"]["candidates"], detect_mcp_targets(environ=environ))
    for candidate in _all_candidates(plan):
        current = snapshot(Path(candidate["path"]))
        # Pending targets sit at their sealed before-state, or exactly at the
        # expected_after a successful vendor transition recorded for them.
        completed = done.get(candidate["path"])
        if completed is not None:
            allowed = completed["after"]
        else:
            advance = progressed.get(candidate["path"])
            allowed = (
                advance["expected_current"]
                if advance is not None
                else candidate["before"]
            )
        if current != allowed:
            _fail(
                "state-conflict", "cleanup target changed after plan or prior receipt"
            )
    _recheck_graft(plan, purpose="cleanup", done=done, progressed=progressed, environ=environ)


def _graft_index(plan: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    index = {}
    for item in _all_candidates(plan):
        graft = _graft_candidate(item)
        if graft is not None:
            if graft.get("path") != item["path"] or graft.get("before") != item["before"]:
                _fail("binding-violation", "a composed retirement target differs from its cleanup path or state")
            index[item["path"]] = _graft_identity(graft)
    return index


def _fresh_graft(
    selections: Sequence[Mapping[str, Any]],
    evidence: Sequence[Mapping[str, Any]],
    *,
    purpose: str,
) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for item in selections:
        _report, view = _retirement_view(item, evidence, purpose=purpose)
        if view.get("stop") and (purpose == "reset" or os.name == "nt"):
            _fail("blocked-target", "retirement inspection is blocked")
        for candidate in _actionable_graft(view):
            path = str(candidate["path"])
            identity = _graft_identity(candidate)
            if path in found and found[path] != identity:
                _fail("scope-conflict", "retirement domains disagree on one path")
            found[path] = identity
    return found


_HOST_CONFIG_ROLES = {
    None: frozenset(),
    "codex": frozenset({"codex-mcp", "codex-hooks"}),
    "omp": frozenset({"omp-mcp"}),
}


def _active_config_paths(environ: Mapping[str, str]) -> dict[str, str]:
    found = {}
    for _host, configs in _host_domains(environ):
        for item in configs:
            found[item["role"]] = str(_safe_path(Path(item["path"])))
    return found


def _bound_launchers(launchers: Any, vault: Path, config_paths: set[str]) -> list[str]:
    if not isinstance(launchers, list):
        _fail("invalid-document", "retirement launchers are not a list")
    bound = []
    for item in launchers:
        path = _safe_path(Path(item))
        text = str(path)
        if text != item:
            _fail("scope-conflict", "retirement launcher path is not canonical")
        if path.is_relative_to(vault) or vault.is_relative_to(path):
            _fail("scope-conflict", "retirement launcher overlaps the private vault")
        if text in config_paths:
            _fail("scope-conflict", "a config target cannot be disguised as a launcher")
        bound.append(text)
    return bound


def _bound_projects(projects: Any, vault: Path, home: Path) -> list[str]:
    if not isinstance(projects, list):
        _fail("invalid-document", "retirement projects are not a list")
    if not projects:
        return []
    roots = []
    for item in projects:
        path = _safe_path(Path(item))
        if str(path) != item:
            _fail("scope-conflict", "retirement project path is not canonical")
        roots.append(path)
    return [str(root) for root in _roots(roots, vault, home)]


def _bound_reset_selections(
    plan: Mapping[str, Any], environ: Mapping[str, str], vault: Path
) -> dict[str, Any]:
    """Reject an untrusted reset plan whose domain is not the active environment."""
    payload = plan["payload"]
    stored = payload.get("selections")
    graft = payload.get("graftRetirement") or {}
    if not isinstance(stored, dict) or stored != graft.get("selections"):
        _fail("binding-violation", "retirement selections are not bound to the plan")
    if stored.get("vault") != str(vault):
        _fail("scope-conflict", "retirement vault is not the active private vault")
    host = stored.get("host")
    if host not in _HOST_CONFIG_ROLES:
        _fail("scope-conflict", "retirement host is not the active domain")
    active = _active_config_paths(environ)
    configs = stored.get("configs")
    if not isinstance(configs, list):
        _fail("invalid-document", "retirement configs are not a list")
    seen: set[str] = set()
    for item in configs:
        if not isinstance(item, Mapping) or set(item) != {"role", "path"}:
            _fail("invalid-document", "retirement config is not a current domain")
        role = item["role"]
        if role not in _HOST_CONFIG_ROLES[host] or role not in active or role in seen:
            _fail("scope-conflict", "retirement config is outside the active host domain")
        seen.add(role)
        if item["path"] != active[role]:
            _fail("scope-conflict", "retirement config path is not the active domain target")
    projects = _bound_projects(stored.get("projects"), vault, _home(environ))
    if projects != stored.get("projects"):
        _fail("scope-conflict", "retirement project selection is not the active domain")
    launchers = _bound_launchers(
        stored.get("retiring_launchers"), vault, set(active.values())
    )
    if launchers != stored.get("retiring_launchers"):
        _fail("scope-conflict", "retirement launcher selection is not canonical")
    return stored


def _bound_cleanup_selections(
    plan: Mapping[str, Any], environ: Mapping[str, str], vault: Path
) -> list[dict[str, Any]]:
    payload = plan["payload"]
    expected = _cleanup_selections(
        [Path(project["root"]) for project in payload["projects"]], vault, environ
    )
    graft = payload.get("graftRetirement") or {}
    report_selections = (graft.get("report") or {}).get("selections")
    if graft.get("selections") != expected or (
        report_selections is not None and report_selections != expected
    ):
        _fail("scope-conflict", "retirement selections do not match the active domain")
    return expected


def _allowed_graft_paths(selections: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> set[str]:
    groups = [selections] if isinstance(selections, Mapping) else list(selections)
    allowed = set()
    for item in groups:
        allowed.update(config["path"] for config in item.get("configs") or [])
        allowed.update(str(Path(root) / "AGENTS.md") for root in item.get("projects") or [])
    return allowed


def _assert_graft_domain(plan: Mapping[str, Any], allowed: set[str]) -> None:
    for path in _graft_index(plan):
        if path not in allowed:
            _fail("scope-conflict", "retirement target is outside the active domain")


def _assert_graft_backups(plan: Mapping[str, Any], vault: Path) -> None:
    for item in _all_candidates(plan):
        graft = _graft_candidate(item)
        if not isinstance(graft, Mapping) or graft.get("backup_ref") is None:
            continue
        backup = graft["backup_ref"]
        if not isinstance(backup, Mapping) or set(backup) != {"path", "state"}:
            _fail("binding-violation", "retirement original is not a backup reference")
        path = _safe_path(Path(backup["path"]))
        if not path.is_relative_to(vault) or path == Path(str(graft.get("path"))):
            _fail("scope-conflict", "retirement original is outside the private vault")
        if snapshot(path) != backup["state"]:
            _fail("backup-conflict", "retirement original does not match its recorded state")


def _recheck_graft(
    plan: Mapping[str, Any],
    *,
    purpose: str,
    done: Mapping[str, Any],
    progressed: Mapping[str, Any] | None = None,
    environ: Mapping[str, str],
) -> None:
    """Compare the sealed candidate to a fresh inspection. Do not adopt the fresh one."""
    payload = plan["payload"]
    sealed = payload.get("graftRetirement")
    # Old plans omit this block. Leave their sealed candidates alone.
    if sealed is None:
        if _graft_index(plan):
            _fail("binding-violation", "retirement candidates require a sealed inspection")
        return
    if not isinstance(sealed, dict):
        _fail("invalid-document", "retirement block is not an object")
    vault = require_private_directory(Path(payload["backup_root"]))
    if purpose == "reset":
        selections = [_bound_reset_selections(plan, environ, vault)]
        allowed = _allowed_graft_paths(selections[0])
    else:
        selections = _bound_cleanup_selections(plan, environ, vault)
        allowed = _allowed_graft_paths(selections)
    evidence = sealed.get("evidence") or []
    if not isinstance(evidence, list):
        _fail("invalid-document", "retirement evidence is not a list")
    evidence = _evidence_bindings(evidence, vault)
    _assert_graft_domain(plan, allowed)
    _assert_graft_backups(plan, vault)
    if os.name == "nt":
        for item in _all_candidates(plan):
            path = item["path"]
            if _graft_candidate(item) is not None and path in done:
                _preflight_restore_row(done[path], item, vault, allowed, rehearse_permissions=False)
    skip = done.keys() | (progressed or {}).keys()
    fresh = {
        path: identity
        for path, identity in _fresh_graft(selections, evidence, purpose=purpose).items()
        if path not in skip
    }
    sealed_index = {
        path: identity
        for path, identity in _graft_index(plan).items()
        if path not in skip
    }
    if sealed_index != fresh:
        _fail("scope-conflict", "retirement candidates differ from current inspection")


def _validate_retirement(
    plan: Mapping[str, Any], done: Mapping[str, Any], environ: Mapping[str, str]
) -> None:
    payload = plan["payload"]
    if payload.get("stop") or payload["projects"] or any(
        payload["shared"][kind]["candidates"] or payload["shared"][kind]["blocked"]
        for kind in ("skills", "mcp")
    ):
        _fail("blocked-target", "a retirement-only plan cannot carry other cleanup")
    vault = require_private_directory(Path(payload["backup_root"]))
    _check_candidate_paths(plan, vault)
    _recheck_graft(plan, purpose="reset", done=done, environ=environ)
    for candidate in _all_candidates(plan):
        if candidate.get("kind") != "graft-retire":
            _fail("scope-conflict", "a retirement-only plan contains another cleanup kind")
        if candidate["path"] not in done and snapshot(Path(candidate["path"])) != candidate["before"]:
            _fail("state-conflict", "retirement target changed after the plan")

def _vendor_transitions(
    candidate: Mapping[str, Any], row: Mapping[str, Any], vault: Path
) -> dict[str, dict[str, Any]]:
    """Per-path effects of a succeeded vendor uninstall, bound to the plan.
    The receipt's vendor outcome proves a transition only when it is bound to
    the plan's sealed prepared resources: identical roots and prepared
    identity, a successful zero vendor exit, exact per-resource identity
    (resource id, kind, relative path, derived successful status) and
    ``before``/``expected_after`` states, an immutable original backup inside
    the private vault for every resource, and no unlisted, duplicated or
    omitted path or resource identifier.
    """
    outcome = row.get("vendor")
    prepared = candidate["trellis"]
    payload = prepared["payload"]
    if (
        not isinstance(outcome, Mapping)
        or outcome.get("status") != "removed"
        or type(outcome.get("exit")) is not int
        or outcome.get("exit") != 0
        or outcome.get("prepared_id") != prepared.get("prepared_id")
        or prepared.get("prepared_id") != _digest(payload)
        or outcome.get("root") != payload["root"]
        or payload["root"] != candidate["root"]
    ):
        _fail("binding-violation", "receipt vendor outcome is not bound to the plan")
    if not isinstance(outcome.get("results"), list):
        _fail("binding-violation", "receipt vendor results must be a list")
    resources = {}
    resource_ids = set()
    for resource in payload["resources"]:
        if not isinstance(resource, Mapping):
            _fail("binding-violation", "a prepared vendor resource is malformed")
        if (
            resource.get("path") in resources
            or resource.get("resource_id") in resource_ids
        ):
            _fail(
                "binding-violation",
                "prepared vendor resources repeat a path or identifier",
            )
        resources[resource.get("path")] = resource
        resource_ids.add(resource.get("resource_id"))
    transitions: dict[str, dict[str, Any]] = {}
    seen_ids = set()
    for result in outcome["results"]:
        if not isinstance(result, Mapping):
            _fail("binding-violation", "a receipt vendor result is malformed")
        path = result.get("path")
        resource = resources.get(path)
        if resource is None or path in transitions:
            _fail(
                "binding-violation",
                "receipt vendor outcome lists an unbound or repeated path",
            )
        expected_after = resource.get("expected_after")
        if not isinstance(expected_after, Mapping):
            _fail("binding-violation", "a prepared vendor resource is malformed")
        successful = "removed" if expected_after.get("type") == "absent" else "scrubbed"
        if (
            result.get("resource_id") != resource.get("resource_id")
            or result.get("resource_id") in seen_ids
            or result.get("kind") != resource.get("kind")
            or result.get("relative") != resource.get("relative")
            or result.get("status") != successful
            or result.get("before") != resource["before"]
            or result.get("after") != expected_after
        ):
            _fail(
                "binding-violation",
                "receipt vendor result differs from the prepared transition",
            )
        seen_ids.add(result["resource_id"])
        backup = result.get("backup_ref")
        if not backup:
            _fail("binding-violation", "receipt vendor result keeps no original")
        backup_path = _safe_path(Path(backup["path"]))
        if (
            not backup_path.is_relative_to(vault)
            or backup.get("state") != resource["before"]
            or snapshot(backup_path) != resource["before"]
        ):
            _fail("backup-conflict", "vendor backup is unavailable or changed")
        transitions[path] = {
            "before": resource["before"],
            "expected_current": result["after"],
            "backup_ref": backup,
        }
    if len(transitions) != len(resources):
        _fail("binding-violation", "receipt vendor outcome omits a prepared path")
    return transitions


def _previous_receipt(path: Path | None, plan: Mapping[str, Any], vault: Path):
    if path is None:
        return None, {}, {}
    previous = _read_document(path, "receipt_id")
    if previous["payload"]["plan_id"] != plan["plan_id"]:
        _fail("binding-violation", "cleanup receipt belongs to a different plan")
    candidates = {item["path"]: item for item in _all_candidates(plan)}
    done = {}
    progressed: dict[str, dict[str, Any]] = {}
    for row in previous["payload"]["results"]:
        candidate = candidates.get(row["path"])
        if (
            candidate is None
            or row["kind"] != candidate["kind"]
            or row["before"] != candidate["before"]
        ):
            _fail("binding-violation", "receipt contains an unbound cleanup result")
        backup = row["backup_ref"]
        if backup:
            backup_path = _safe_path(Path(backup["path"]))
            if (
                not backup_path.is_relative_to(vault)
                or snapshot(backup_path) != candidate["before"]
            ):
                _fail("backup-conflict", "receipt backup is unavailable or changed")
        if row["status"] == "succeeded":
            if not backup or row["after"] != _goal(candidate, backup, vault=vault):
                _fail(
                    "binding-violation",
                    "receipt success does not prove the intended result",
                )
            done[row["path"]] = row
            progressed.pop(row["path"], None)
            if candidate["kind"] == "trellis-uninstall":
                for resource_path, transition in _vendor_transitions(
                    candidate, row, vault
                ).items():
                    if resource_path == row["path"] or resource_path in done:
                        continue
                    other = candidates.get(resource_path)
                    if other is None:
                        # Not a cleanup candidate: only the recorded vendor
                        # transition may explain its current state.
                        if (
                            snapshot(_safe_path(Path(resource_path)))
                            != transition["expected_current"]
                        ):
                            _fail(
                                "state-conflict",
                                "vendor-cleaned path changed after the receipt",
                            )
                        continue
                    if transition["before"] != other["before"]:
                        _fail(
                            "binding-violation",
                            "vendor transition does not match the sealed candidate",
                        )
                    progressed[resource_path] = transition
        else:
            advance = progressed.get(row["path"])
            allowed = (
                advance["expected_current"] if advance is not None else row["before"]
            )
            if row["after"] != allowed:
                _fail(
                    "partial-cleanup",
                    "partial cleanup requires reconciliation before retry",
                )
        vendor = row.get("vendor")
        if vendor is None or row["status"] == "succeeded":
            continue
        if (
            not isinstance(vendor, Mapping)
            or not isinstance(vendor.get("results"), list)
            or any(not isinstance(resource, Mapping) for resource in vendor["results"])
        ):
            _fail("binding-violation", "failed vendor evidence is malformed")
        if vendor["status"] == "partial" or any(
            resource["after"] != resource["before"] for resource in vendor["results"]
        ):
            _fail(
                "partial-cleanup",
                "vendor side effects require reconciliation before retry",
            )
    return previous, done, progressed


def _rejection(phase: str, reason: str, code: int = 2):
    return {
        "mode": "cleanup-legacy",
        "phase": phase,
        "status": "blocked" if code == 2 else "failed",
        "plan_id": None,
        "projects": [],
        "reason": reason,
        "nextStep": "Preserve backups; reconcile the failure before retrying.",
        "cleanup_legacy": {},
    }, code


def apply_cleanup_legacy(
    plan_path: Path,
    *,
    confirm_cleanup: str | None,
    cleanup_receipt_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> tuple[dict[str, Any], int]:
    environ = dict(os.environ) if environ is None else environ
    try:
        plan = _read_document(plan_path, "plan_id")
        vault = require_private_directory(plan_path.parent)
        if str(vault) != plan["payload"]["backup_root"]:
            _fail(
                "scope-conflict",
                "plan moved from its declared private evidence directory",
            )
        if confirm_cleanup != plan["plan_id"]:
            _fail("confirmation-required", "confirm this plan_id before cleanup")
        previous, done, progressed = _previous_receipt(
            cleanup_receipt_path, plan, vault
        )
        _validate_scope(plan, done, progressed, environ)
    except (
        contracts.ContractError,
        TaskDataError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ) as error:
        return _rejection(
            "apply",
            _WINDOWS_VENDOR_OVERLAP if getattr(error, "code", None) == "windows-retirement-vendor-overlap"
            else "cleanup confirmation, scope, identity or evidence validation failed",
        )
    from sbtd_migration import _prepare_backup_parent

    candidates = _all_candidates(plan)
    results = (
        {row["path"]: row for row in previous["payload"]["results"]} if previous else {}
    )
    started = _now()
    status = "cleaned"
    backups: dict[str, dict[str, Any]] = {}
    # Preserve every original before the vendor can edit another candidate (AGENTS).
    try:
        for index, item in enumerate(candidates):
            if item["path"] in done:
                continue
            advance = progressed.get(item["path"])
            if advance is not None:
                # The original is already preserved by the succeeded vendor
                # run; reuse that immutable backup instead of demanding the
                # target still match its sealed before-state.
                backups[item["path"]] = advance["backup_ref"]
                continue
            destination = vault / plan["plan_id"] / "cleanup" / f"{index:03d}"
            _prepare_backup_parent(destination, vault)
            graft = _graft_candidate(item)
            if os.name == "nt" and graft is not None:
                from sbtd_retirement import backup_candidate, retained_windows_permissions

                backup = backup_candidate(graft, destination=destination, vault=vault)
                retained = retained_windows_permissions(backup, graft.get("windows_acl_digest"), vault=vault)
                preflight_windows_permissions(Path(item["path"]), retained)
            else:
                backup = backup_reference(
                    {"path": item["path"], "state": item["before"]},
                    destination,
                    private_root=vault,
                )
            backups[item["path"]] = backup
    except (contracts.ContractError, TaskDataError, OSError):
        return _rejection(
            "apply", "backup preservation failed; no cleanup execution started", 3
        )
    current_states = {
        item["path"]: (
            progressed[item["path"]]["expected_current"]
            if item["path"] in progressed
            else item["before"]
        )
        for item in candidates
    }
    for index, item in enumerate(candidates):
        if item["path"] in done:
            continue
        path = Path(item["path"])
        graft = _graft_candidate(item)
        native = os.name == "nt" and graft is not None
        row = {
            "resource_id": f"cleanup-{index:03d}",
            "kind": item["kind"],
            "path": str(path),
            "status": "failed",
            "before": item["before"],
            "after": None,
            "mode_before": _mode_text(path) if item["before"]["type"] != "absent" else None,
            "mode_after": None,
            "backup_ref": backups[str(path)],
        }
        if native:
            row["mode_before"] = graft["mode"]
            row["windows_acl_digest"] = graft["windows_acl_digest"]
        try:
            if snapshot(path) != current_states[str(path)]:
                _fail("state-conflict", "target changed during cleanup")
            if native and _mode_text(path) != row["mode_before"]:
                _fail("state-conflict", "retirement target mode changed during cleanup")
            if item["kind"] == "graft-retire":
                # Sealed plan item only. Fresh inspection compares; it does not supply bytes.
                receipt_path = vault / plan["plan_id"] / "retirement" / f"{index:03d}.json"
                _prepare_backup_parent(receipt_path, vault)
                _retirement().apply_candidate(
                    item,
                    scope=path.parent,
                    vault=vault,
                    expected={
                        "type": item["before"]["type"],
                        "checksum": item["before"]["checksum"],
                        "mode": item["mode"],
                        **({"windows_acl_digest": row["windows_acl_digest"]} if native else {}),
                    },
                    receipt_path=receipt_path,
                    **({"backup_path": Path(backups[str(path)]["path"])} if native else {}),
                )
                row["retirement_receipt"] = str(receipt_path)
            elif item["kind"] == "trellis-uninstall":
                from sbtd_trellis_uninstall import execute_trellis_uninstall

                outcome = execute_trellis_uninstall(
                    Path(item["root"]), item["trellis"], vault, environ=environ
                )
                row["vendor"] = outcome
                for resource in outcome["results"]:
                    if resource["path"] in current_states:
                        current_states[resource["path"]] = resource["after"]
                if outcome["status"] != "removed":
                    _fail("uninstall-failed", "vendor uninstall did not complete")
            elif item["kind"] in {"directory-remove", "skill-directory"}:
                remove_reference(path, current_states[str(path)], scope=path.parent)
            else:
                original = read_file(Path(backups[str(path)]["path"]), item["before"])
                native_options = {}
                if native:
                    from sbtd_retirement import retained_windows_permissions

                    native_options = {
                        "windows_permissions": retained_windows_permissions(
                            backups[str(path)], row["windows_acl_digest"], vault=vault,
                        ),
                        "expected_windows_digest": row["windows_acl_digest"],
                        "windows_mode": int(row["mode_before"], 8),
                    }
                write_file(
                    path,
                    _render(item, original, vault=vault),
                    current_states[str(path)],
                    scope=path.parent,
                    **native_options,
                )
            row["after"] = snapshot(path)
            row["mode_after"] = (
                None if row["after"]["type"] == "absent" else _mode_text(path)
            )
            if row["after"] != _goal(item, backups[str(path)], vault=vault):
                _fail(
                    "post-state-conflict",
                    "cleanup result differs from the intended state",
                )
            if native:
                if row["after"]["type"] == "file" and row["mode_after"] != row["mode_before"]:
                    _fail("post-state-conflict", "cleanup changed the captured retirement mode")
                row["windows_acl_digest_after"] = (
                    None if row["after"]["type"] == "absent" else row["windows_acl_digest"]
                )
                _retired_matches(row, native=True)
            row["status"] = "succeeded"
        except (contracts.ContractError, TaskDataError, OSError, ValueError) as error:
            row["error"] = getattr(error, "code", "operation-failed")
            if native:
                row.pop("windows_acl_digest_after", None)
            try:
                row["after"] = snapshot(path)
            except (contracts.ContractError, OSError):
                row["after"] = None
            status = "failed"
        results[str(path)] = row
        if status == "failed":
            break
    payload = {
        "plan_id": plan["plan_id"],
        "started_at": started,
        "finished_at": _now(),
        "status": status,
        "results": list(results.values()),
    }
    receipt = {"schema_version": 1, "receipt_id": _digest(payload), "payload": payload}
    destination = vault / f"cleanup-legacy-receipt-{receipt['receipt_id']}.json"
    try:
        save_document(destination, receipt, private_root=vault)
    except (contracts.ContractError, TaskDataError, OSError):
        return _rejection(
            "apply",
            "cleanup may have written targets; receipt persistence failed; preserve the private backup directory",
            3,
        )
    envelope = {
        "mode": "cleanup-legacy",
        "phase": "apply",
        "status": status,
        "plan_id": plan["plan_id"],
        "projects": [
            {"root": p["root"], "status": status} for p in plan["payload"]["projects"]
        ],
        "cleanup_legacy": {"receipt": receipt, "receipt_path": str(destination)},
    }
    if plan["payload"].get("purpose") == "retirement-reset":
        # Not the composed confirmation digest shown beside ordinary template writes.
        envelope["purpose"] = "retirement-reset"
        envelope["retirement_plan_id"] = plan["plan_id"]
        envelope["receipt_path"] = str(destination)
    return envelope, 0 if status == "cleaned" else 3


def _argument_path(value: str) -> Path:
    if not value.strip():
        _fail("invalid-path", "cleanup path must not be empty")
    return _safe_path(Path(value).expanduser())


def _retirement_payload(
    selections: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
    report: Mapping[str, Any],
    view: Mapping[str, Any],
    candidates: list[dict[str, Any]],
    *,
    vault: Path | None,
    stop: bool,
) -> dict[str, Any]:
    return {
        "purpose": "retirement-reset",
        "backup_root": None if vault is None else str(vault),
        "selections": dict(selections),
        "evidence": list(evidence),
        "projects": [],
        "shared": {
            "skills": {"candidates": [], "blocked": []},
            "mcp": {"candidates": [], "blocked": []},
        },
        "graftRetirement": {
            "selections": dict(selections),
            "evidence": list(evidence),
            "report": report,
            "view": view,
            "candidates": candidates,
        },
        "stop": stop,
    }


def plan_reset_retirement(
    *,
    selections: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]] = (),
    vault: Path | None = None,
    report: Mapping[str, Any] | None = None,
    confirm: str | None = None,
) -> dict[str, Any]:
    """Read-only preview, or recompute, persist, and apply a retirement-only plan."""
    vault_path = None if vault is None else require_private_directory(_safe_path(Path(vault)))
    bound = _evidence_bindings(evidence, vault_path)
    selected = _inspect_selections(selections, vault_path)
    fresh, view = _retirement_view(selected, bound, purpose="reset")
    if report is not None and _canonical_report(report) != _canonical_report(fresh):
        _fail("binding-violation", "retirement report does not match a fresh inspection")
    stop = bool(view.get("stop"))
    grafts = [] if stop else _actionable_graft(view)
    sealed = [] if stop else _seal_candidates({
        "candidates": [
            dict(item, kind="graft-retire", path=str(item["path"])) for item in grafts
        ],
        "blocked": [],
    })["candidates"]
    payload = _retirement_payload(
        selected, bound, fresh, view, sealed, vault=vault_path, stop=stop
    )
    plan_id = _digest(payload)
    plan = {"schema_version": 1, "payload": payload, "plan_id": plan_id}
    status = "blocked" if stop else ("planned" if sealed else "nothing-to-clean")
    preview = {
        "mode": "cleanup-legacy",
        "phase": "plan",
        "purpose": "retirement-reset",
        "status": status,
        "plan_id": plan_id,
        "retirement_plan_id": plan_id,
        "plan": plan,
        "graftRetirement": view,
        "writes": False,
    }
    if confirm is None:
        return preview
    if confirm != plan_id:
        _fail("confirmation-required", "confirm the sealed retirement-only plan_id")
    if stop or vault_path is None:
        return {
            **preview,
            "phase": "apply",
            "status": "blocked",
            "plan_path": None,
            "receipt_path": None,
            "receipt_id": None,
        }
    destination = vault_path / f"cleanup-legacy-plan-{plan_id}.json"
    save_document(destination, plan, private_root=vault_path)
    if not sealed:
        return {
            **preview,
            "phase": "apply",
            "status": "nothing-to-clean",
            "plan_path": str(destination),
            "receipt_path": None,
            "receipt_id": None,
        }
    applied, _code = apply_cleanup_legacy(destination, confirm_cleanup=plan_id)
    receipt = applied.get("cleanup_legacy", {}).get("receipt") or {}
    return {
        "mode": "cleanup-legacy",
        "phase": "apply",
        "purpose": "retirement-reset",
        "status": applied["status"],
        "plan_id": plan_id,
        "retirement_plan_id": plan_id,
        "plan_path": str(destination),
        "receipt_path": applied.get("cleanup_legacy", {}).get("receipt_path"),
        "receipt_id": receipt.get("receipt_id"),
        "graftRetirement": view,
        "writes": applied["status"] == "cleaned",
    }


_CLEANUP_RESTORE_KINDS = frozenset({
    "marker-blocks",
    "directory-remove",
    "skill-directory",
    "trellis-uninstall",
    "mcp-server-remove",
})


def _retired_matches(row: Mapping[str, Any], *, native: bool = False) -> None:
    path = _safe_path(Path(row["path"]))
    if str(path) != row["path"]:
        _fail("binding-violation", "restore path is not canonical")
    if snapshot(path) != row["after"]:
        _fail("state-conflict", "retired target no longer matches its receipt")
    if row["after"]["type"] == "absent":
        return
    if not isinstance(row.get("mode_after"), str) or _mode_text(path) != row["mode_after"]:
        _fail("state-conflict", "retired target mode does not match its receipt")
    if native:
        from sbtd_retirement import capture_windows_permissions

        capture_windows_permissions(path, row.get("windows_acl_digest_after"))


def _preflight_backup(row: Mapping[str, Any], vault: Path, live: Path) -> None:
    backup = row.get("backup_ref")
    if not isinstance(backup, Mapping) or "path" not in backup or "state" not in backup:
        _fail("backup-conflict", "restore has no trusted backup")
    backup_path = _safe_path(Path(backup["path"]))
    if not backup_path.is_relative_to(vault) or backup_path == live:
        _fail("scope-conflict", "restore backup is outside the private vault")
    if snapshot(backup_path) != row["before"] or backup.get("state") != row["before"]:
        _fail("backup-conflict", "restore backup does not match the recorded original")
    if row["before"]["type"] == "absent":
        return
    mode = row.get("mode_before")
    if not isinstance(mode, str) or _mode_text(backup_path) != mode:
        _fail("state-conflict", "restore backup mode does not match the recorded mode")


def _preflight_retirement_receipt(
    row: Mapping[str, Any], candidate: Mapping[str, Any], vault: Path, target: Path,
) -> None:
    receipt_path = _safe_path(Path(row["retirement_receipt"]))
    if not receipt_path.is_relative_to(vault) or not receipt_path.is_file():
        _fail("scope-conflict", "retirement receipt is outside the private vault")
    document = strict_json_object(read_file(receipt_path))
    payload = document.get("payload")
    if (
        set(document) != {"schema_version", "payload", "receipt_id"}
        or document.get("schema_version") != 1
        or not isinstance(payload, dict)
        or document.get("receipt_id") != _digest(payload)
    ):
        _fail("binding-violation", "retirement receipt is not a sealed document")
    schema = getattr(_retirement(), "RECEIPT_SCHEMA", None)
    if (
        payload.get("schema") != schema
        or payload.get("target") != str(target)
        or payload.get("candidate_id") != candidate.get("id")
        or payload.get("action") != candidate.get("action")
    ):
        _fail("binding-violation", "retirement receipt target is not the restore path")
    if (
        payload.get("before") != row["before"]
        or payload.get("after") != row["after"]
        or payload.get("mode_before") != row.get("mode_before")
        or payload.get("mode_after") != row.get("mode_after")
    ):
        _fail("state-conflict", "retirement receipt does not match the cleanup row")
    if os.name == "nt" and any(payload.get(key) != row.get(key) for key in (
        "backup_ref", "windows_acl_digest", "windows_acl_digest_after",
    )):
        _fail("binding-violation", "the retirement receipt does not bind the same Windows ACL backup")
    backup = payload.get("backup_ref")
    if not isinstance(backup, Mapping) or "path" not in backup:
        _fail("backup-conflict", "retirement receipt has no trusted backup")
    backup_path = _safe_path(Path(backup["path"]))
    if not backup_path.is_relative_to(vault) or backup_path == target:
        _fail("scope-conflict", "retirement receipt backup is outside the private vault")
    if snapshot(backup_path) != row["before"]:
        _fail("backup-conflict", "retirement receipt backup does not match the recorded original")
    if row["before"]["type"] != "absent" and _mode_text(backup_path) != row.get("mode_before"):
        _fail("state-conflict", "retirement receipt backup mode does not match the recorded mode")


def _rollback_allowed(
    plan: Mapping[str, Any], environ: Mapping[str, str], vault: Path
) -> set[str]:
    payload = plan["payload"]
    if payload.get("purpose") == "retirement-reset":
        return _allowed_graft_paths(_bound_reset_selections(plan, environ, vault))
    if payload.get("graftRetirement") is None:
        return set()
    return _allowed_graft_paths(_bound_cleanup_selections(plan, environ, vault))


def _preflight_restore_row(
    row: Mapping[str, Any],
    candidate: Mapping[str, Any],
    vault: Path,
    allowed: set[str],
    *,
    rehearse_permissions: bool = True,
) -> None:
    path = _safe_path(Path(row["path"]))
    if str(path) != candidate["path"]:
        _fail("binding-violation", "restore path is not the sealed candidate")
    kind = candidate.get("kind")
    graft = _graft_candidate(candidate)
    native = os.name == "nt" and graft is not None
    if row.get("retirement_receipt"):
        if kind != "graft-retire" or str(path) not in allowed:
            _fail(
                "binding-violation",
                "only a retirement-owned target inside the active domain can be restored from a retirement receipt",
            )
        _preflight_retirement_receipt(row, candidate, vault, path)
    elif kind == "graft-retire":
        _fail("binding-violation", "retirement removal has no receipt")
    elif kind not in _CLEANUP_RESTORE_KINDS:
        _fail("scope-conflict", "rollback refused an unknown cleanup kind")
    if native:
        if str(path) not in allowed:
            _fail("scope-conflict", "the Windows retirement target is outside the active domain")
        digest = graft.get("windows_acl_digest")
        if (
            row.get("windows_acl_digest") != digest
            or "windows_acl_digest_after" not in row
            or row["windows_acl_digest_after"] != (None if row["after"]["type"] == "absent" else digest)
            or row.get("mode_before") != graft.get("mode")
            or row.get("mode_after") != (None if row["after"]["type"] == "absent" else row["mode_before"])
        ):
            _fail("binding-violation", "cleanup receipt does not match the sealed retirement permissions")
    _retired_matches(row, native=native)
    _preflight_backup(row, vault, path)
    if native:
        from sbtd_retirement import retained_windows_permissions

        retained = retained_windows_permissions(row["backup_ref"], digest, vault=vault)
        if rehearse_permissions:
            preflight_windows_permissions(path, retained)


def _restore_retired(row: Mapping[str, Any], vault: Path, target: Path, *, native: bool) -> None:
    path = _safe_path(target)
    if str(path) != row["path"]:
        _fail("binding-violation", "restore target is not the sealed plan path")
    if row.get("retirement_receipt"):
        receipt_path = _safe_path(Path(row["retirement_receipt"]))
        _retirement().restore_candidate(
            receipt_path,
            scope=path.parent,
            vault=vault,
            expected={
                "type": row["after"]["type"],
                "checksum": row["after"]["checksum"],
                "mode": row.get("mode_after"),
                **({"windows_acl_digest": row["windows_acl_digest_after"]} if native else {}),
            },
            target=path,
        )
        return
    elif row["before"]["type"] == "directory":
        install_reference(
            {"path": row["backup_ref"]["path"], "state": row["backup_ref"]["state"]},
            path,
            row["after"],
            scope=path.parent,
        )
    elif row["before"]["type"] == "file":
        native_options = {}
        if native:
            from sbtd_retirement import retained_windows_permissions

            if _mode_text(path) != row["mode_after"]:
                _fail("state-conflict", "retirement target mode changed during rollback")
            native_options = {
                "windows_permissions": retained_windows_permissions(
                    row["backup_ref"], row["windows_acl_digest"], vault=vault,
                ),
                "expected_windows_digest": row["windows_acl_digest_after"],
                "windows_mode": int(row["mode_before"], 8),
            }
        write_file(
            path,
            read_file(Path(row["backup_ref"]["path"]), row["before"]),
            row["after"],
            scope=path.parent,
            **native_options,
        )
    else:
        _fail("unsupported-operation", "rollback cannot restore this retired resource")
    if native:
        from sbtd_retirement import capture_windows_permissions

        capture_windows_permissions(path, row["windows_acl_digest"])
    elif row["before"]["type"] != "absent":
        mode = row.get("mode_before")
        if not isinstance(mode, str):
            _fail("state-conflict", "rollback has no recorded pre-retirement mode")
        os.chmod(path, int(mode, 8))
    if snapshot(path) != row["before"] or _mode_text(path) != row.get("mode_before"):
        _fail("post-state-conflict", "rollback did not restore the recorded bytes and mode")


def rollback_cleanup_legacy(
    plan_path: Path,
    *,
    confirm_cleanup: str | None,
    cleanup_receipt_path: Path,
    environ: Mapping[str, str] | None = None,
) -> tuple[dict[str, Any], int]:
    """Restore succeeded rows only after plan, domain, state and backup checks."""
    environ = dict(os.environ) if environ is None else environ
    try:
        plan = _read_document(plan_path, "plan_id")
        vault = require_private_directory(plan_path.parent)
        if str(vault) != plan["payload"]["backup_root"]:
            _fail("scope-conflict", "plan moved from its declared private evidence directory")
        if confirm_cleanup != plan["plan_id"]:
            _fail(
                "confirmation-required",
                "confirm the sealed plan_id; a composed confirmation digest is not a rollback id",
            )
        receipt_path = _safe_path(cleanup_receipt_path)
        if not receipt_path.is_relative_to(vault) or receipt_path == plan_path:
            _fail("scope-conflict", "cleanup receipt is outside the plan vault")
        receipt, done, progressed = _previous_receipt(receipt_path, plan, vault)
        _validate_scope(plan, done, progressed, environ)
        allowed = _rollback_allowed(plan, environ, vault)
        candidates = {item["path"]: item for item in _all_candidates(plan)}
        rows = []
        for row in receipt["payload"]["results"]:
            if row.get("status") != "succeeded":
                continue
            candidate = candidates.get(row["path"])
            if (
                candidate is None
                or row["kind"] != candidate["kind"]
                or row["before"] != candidate["before"]
                or not row.get("backup_ref")
            ):
                _fail("binding-violation", "receipt success is not bound to the plan")
            sealed_target = _safe_path(Path(candidate["path"]))
            if str(sealed_target) != row["path"]:
                _fail("binding-violation", "receipt path is not the sealed plan target")
            _preflight_restore_row(row, candidate, vault, allowed)
            rows.append((row, sealed_target, os.name == "nt" and _graft_candidate(candidate) is not None))
    except (
        contracts.ContractError,
        TaskDataError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ):
        return _rejection(
            "rollback",
            "rollback confirmation, scope, identity or evidence validation failed",
        )
    try:
        for row, sealed_target, native in reversed(rows):
            _restore_retired(row, vault, sealed_target, native=native)
    except (contracts.ContractError, TaskDataError, OSError, ValueError):
        return _rejection(
            "rollback",
            "rollback failed after a retired resource changed; preserve the private backups",
            3,
        )
    return {
        "mode": "cleanup-legacy",
        "phase": "rollback",
        "status": "rolled-back",
        "plan_id": plan["plan_id"],
        "retirement_plan_id": plan["plan_id"]
        if plan["payload"].get("purpose") == "retirement-reset"
        else None,
        "projects": [
            {"root": project["root"], "status": "rolled-back"}
            for project in plan["payload"]["projects"]
        ],
        "cleanup_legacy": {"receipt_path": str(receipt_path)},
    }, 0


def run_cleanup_legacy(args: Any) -> int:
    try:
        if args.phase == "plan":
            from onboard import resolve_global_skills_dir

            roots = [
                _argument_path(value.strip()) for value in args.projects_root.split(",")
            ]
            skills_root, _source = resolve_global_skills_dir(args.global_skills_dir)
            envelope, code = plan_cleanup_legacy(
                roots,
                _argument_path(args.backup_root),
                skills_root=skills_root,
                environ=dict(os.environ),
                retirement_evidence=getattr(args, "retirement_evidence", None),
            )
        elif args.phase == "rollback":
            envelope, code = rollback_cleanup_legacy(
                _argument_path(args.plan),
                confirm_cleanup=args.confirm_cleanup,
                cleanup_receipt_path=_argument_path(args.cleanup_receipt),
                environ=dict(os.environ),
            )
        else:
            envelope, code = apply_cleanup_legacy(
                _argument_path(args.plan),
                confirm_cleanup=args.confirm_cleanup,
                cleanup_receipt_path=_argument_path(args.cleanup_receipt)
                if args.cleanup_receipt
                else None,
                environ=dict(os.environ),
            )
    except (
        contracts.ContractError,
        TaskDataError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        ImportError,
    ):
        envelope, code = _rejection(
            args.phase,
            "cleanup scope, dependencies or private evidence could not be validated",
        )
    if args.json:
        # Standalone cleanup envelope, not a migration-schema document.
        print(contracts.canonical_json_bytes(envelope).decode("utf-8"))
    else:
        print(f"Cleanup legacy {args.phase}: {envelope['status']}")
        rollback_id = envelope.get("retirement_plan_id") or envelope.get("plan_id")
        receipt = envelope.get("receipt_path") or (
            envelope.get("cleanup_legacy") or {}
        ).get("receipt_path")
        if rollback_id and receipt:
            print(f"Rollback confirm is sealed plan_id {rollback_id}")
            print(f"Private receipt {receipt}")
        print(
            envelope.get(
                "reason",
                "Inspect private --json output before confirming any deletion.",
            )
        )
    return code
