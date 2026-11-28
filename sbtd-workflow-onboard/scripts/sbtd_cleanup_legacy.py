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
    assert_private_file,
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
_COMPARE_SKIP = {"before", "trellis", "graft", "vendor_modes_before"}
_LEGACY_ONLY_NOTICE = "Graft retirement inspection is blocked; only the displayed legacy cleanup is in scope."
_WINDOWS_VENDOR_OVERLAP = (
    "Windows vendor cleanup would write a retirement file without preserving its ACL. "
    "Retire the Graft entry separately, then generate a fresh cleanup plan."
)
_VENDOR_MODE_UNPROVEN = (
    "Vendor cleanup lacks bound per-target mode evidence. Generate a fresh plan, "
    "or preserve the backups and reconcile the old receipt before retry or rollback."
)
_VENDOR_OVERLAP_UNPROVEN = (
    "The vendor footprint overlaps another cleanup target without a bound transition for that target. "
    "Separate those cleanup targets and plan again."
)
_VENDOR_REFUSALS = {
    "vendor-mode-unproven": _VENDOR_MODE_UNPROVEN,
    "vendor-overlap-unproven": _VENDOR_OVERLAP_UNPROVEN,
    "windows-retirement-vendor-overlap": _WINDOWS_VENDOR_OVERLAP,
}


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
    return _safe_path(path)



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
        "projects": list(map(str, dict.fromkeys(_owned_path(item) for item in projects))),
        "vault": None if vault is None else str(vault),
        "retiring_launchers": [str(_owned_path(item)) for item in launchers],
    }


def _inspect_graft(
    selections: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
    *,
    inspect_omp_alternate: bool = False,
) -> dict[str, Any]:
    module = _retirement()
    configs = selections["configs"]
    projects = [Path(root) for root in selections["projects"]]
    reports = []
    if configs and projects:
        # An absent config has no footprint to overlap a project. Keep the
        # selected path sealed so a newly present overlap still blocks apply.
        for config in configs:
            path = Path(config["path"])
            if any(path.is_relative_to(root) or root.is_relative_to(path) for root in projects):
                try:
                    _safe_path(path).lstat()
                except FileNotFoundError:
                    continue
                _fail("scope-conflict", "a selected retirement config overlaps a project")
        reports.extend([
            module.inspect_retirement(selections={**selections, "projects": []}, evidence=list(evidence)),
            module.inspect_retirement(selections={**selections, "configs": []}, evidence=list(evidence)),
        ])
    else:
        reports.append(module.inspect_retirement(selections=dict(selections), evidence=list(evidence)))
    if inspect_omp_alternate and selections["host"] == "omp":
        alternate = [
            {"role": "omp-mcp", "path": str(Path(config["path"]).with_name(".mcp.json"))}
            for config in configs if config["role"] == "omp-mcp"
        ]
        if alternate:
            # OMP also loads this file, but historical writes to mcp.json
            # never confer ownership of the alternate name.
            watched = module.inspect_retirement(
                selections={**selections, "configs": alternate, "projects": []},
                evidence=[],
            )
            if watched.get("items") or watched.get("errors"):
                reports.append(watched)
    if len(reports) == 1:
        return reports[0]
    merged = module.merge_reports(reports)
    # Each scope uses the same descriptor. Splitting an inspection does not
    # turn it into multiple evidence sources.
    descriptors = merged.pop("evidence_descriptors", [])
    if descriptors:
        if any(descriptor != descriptors[0] for descriptor in descriptors[1:]):
            _fail("state-conflict", "retirement evidence changed during inspection")
        merged["evidence_descriptor"] = descriptors[0]
    merged["retiring_launchers"] = selections["retiring_launchers"]
    return merged


def _retirement_view(
    selections: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
    *,
    purpose: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    module = _retirement()
    report = _inspect_graft(selections, evidence, inspect_omp_alternate=purpose != "cleanup")
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


def _domain_paths(
    host: str | None, home: Path, environ: Mapping[str, str],
) -> list[dict[str, str]]:
    if host == "codex":
        domain = Path(environ.get("CODEX_HOME") or home / ".codex")
        return [{"role": role, "path": str(domain / name)} for role, name in (
            ("codex-mcp", "config.toml"), ("codex-hooks", "hooks.json"),
        )]
    if host == "omp":
        from sbtd_omp_sources import active_omp_paths

        active = active_omp_paths(home=home, environ=environ)
        override = environ.get("PI_CODING_AGENT_DIR", "")
        if not active["profile"] and override.strip():
            lexical = Path(override).expanduser().absolute()
            physical = lexical.resolve()
            if physical == active["agent_dir"] and physical != lexical:
                _fail("invalid-path", "retirement cannot follow a linked OMP agent directory")
        return [{"role": "omp-mcp", "path": str(active["target"])}]
    return []


def _cleanup_selections(
    roots: Sequence[Path], vault: Path, environ: Mapping[str, str]
) -> list[dict[str, Any]]:
    projects = [str(root) for root in roots]
    home = _home(environ)
    selections = []
    for host in ("codex", "omp"):
        bound = [
            {"role": item["role"], "path": str(_safe_path(Path(item["path"])))}
            for item in _domain_paths(host, home, environ)
        ]
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
    selections: Sequence[Mapping[str, Any]],
    evidence: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Use the same merged inspection and stop rules for plan and apply."""
    module = _retirement()
    reports = []
    for item in selections:
        copied = _contract_object(_inspect_graft(item, evidence))
        if copied is None:
            _fail("invalid-document", "retirement inspection is not canonical contract JSON")
        reports.append(copied)
    merged = _contract_object(module.merge_reports(reports))
    if merged is None:
        _fail("invalid-document", "merged retirement inspection is not canonical contract JSON")
    view = _contract_object(module.render_candidates(merged, purpose="cleanup"))
    if view is None:
        _fail("invalid-document", "retirement candidate view is not canonical contract JSON")
    sealed = {"reports": reports, "selections": selections, "merged": merged}
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
        if root in result:
            continue
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
    graft = payload.get("graftRetirement")
    if graft is not None:
        if not isinstance(graft, Mapping) or not isinstance(graft.get("candidates"), list):
            _fail("invalid-document", "retirement candidates are not a list")
        for item in graft["candidates"]:
            if not isinstance(item, Mapping) or item.get("kind") != "graft-retire":
                _fail("scope-conflict", "a retirement candidate contains another cleanup kind")
            candidates.append(item)
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



def _unbound_vendor_overlap(plan: Mapping[str, Any]) -> bool:
    candidates = _all_candidates(plan)
    targets = {Path(candidate["path"]) for candidate in candidates}
    for candidate in candidates:
        if candidate["kind"] != "trellis-uninstall":
            continue
        footprint = {Path(path) for path in _vendor_resources(candidate)}
        if any(
            target.is_relative_to(resource) or resource.is_relative_to(target)
            for target in targets - footprint for resource in footprint
        ):
            return True
    return False


def _blocked_graft_paths(view: Mapping[str, Any]) -> set[Path] | None:
    paths = [item.get("path") for item in view.get("blocked", [])]
    if not paths or any(not isinstance(path, str) or not Path(path).is_absolute() for path in paths):
        return None
    return {Path(path) for path in paths}


def _cleanup_retirement_block(plan: Mapping[str, Any], view: Mapping[str, Any]) -> str | None:
    if not view.get("stop"):
        return None
    reason = view.get("stop_reason") or "Retirement inspection is blocked."
    candidates = _all_candidates(plan)
    blocked = _blocked_graft_paths(view)
    if (
        os.name == "nt" or plan["payload"]["graftRetirement"].get("evidence")
        or not candidates or blocked is None
        or any(_graft_candidate(item) is not None for item in candidates)
    ):
        return reason
    # A case-insensitive spelling alias is not proof of a disjoint effect.
    blocked_spellings = {path: Path(str(path).casefold()) for path in blocked}
    for item in candidates:
        path = Path(item["path"])
        footprint = [path]
        if item["kind"] == "trellis-uninstall":
            footprint.extend(Path(target) for target in _vendor_resources(item))
        for target in footprint:
            spelling = Path(str(target).casefold())
            for unsafe, blocked_spelling in blocked_spellings.items():
                if not (spelling.is_relative_to(blocked_spelling) or blocked_spelling.is_relative_to(spelling)):
                    continue
                # A regular hardlink cannot establish Graft ownership. The
                # existing legacy parser can still authorize an exact named
                # GitNexus key edit; atomic replacement preserves other keys
                # and does not change bytes at other linked names.
                if (
                    unsafe == path == target and item["kind"] == "mcp-server-remove"
                    and item["keys"] and set(item["keys"]) <= {"gitnexus", "gitnexus-mcp"}
                ):
                    info = path.lstat()
                    if stat.S_ISREG(info.st_mode) and info.st_nlink > 1:
                        continue
                return reason
    return None


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
                    resources = _vendor_resources(candidate)
                    candidate["vendor_modes_before"] = {
                        path: _mode_text(Path(path)) for path in resources
                    }
                    _vendor_modes(candidate["vendor_modes_before"], resources)
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
    _report, view, grafts = _merged_graft(_cleanup_selections(selected, vault, environ), evidence)
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
    plan = {"schema_version": 1, "payload": payload}
    _check_candidate_paths(plan, vault)
    retirement_block = None
    if _windows_vendor_overlap(plan):
        retirement_block = _WINDOWS_VENDOR_OVERLAP
    elif _unbound_vendor_overlap(plan):
        retirement_block = _VENDOR_OVERLAP_UNPROVEN
    elif any(item["reason"] == "vendor-mode-unproven" for item in _blocked(payload)):
        retirement_block = _VENDOR_MODE_UNPROVEN
    else:
        retirement_block = _cleanup_retirement_block(plan, view)
        if retirement_block is not None:
            payload["graftRetirement"]["blocked"] = True
    status = (
        "blocked"
        if _blocked(payload) or retirement_block is not None
        else ("planned" if _all_candidates(plan) else "nothing-to-clean")
    )
    plan["plan_id"] = _digest(payload)
    notice = retirement_block or (_LEGACY_ONLY_NOTICE if view.get("stop") and status == "planned" else None)
    destination = vault / f"cleanup-legacy-plan-{plan['plan_id']}.json"
    save_document(destination, plan, private_root=vault)
    return {
        "mode": "cleanup-legacy",
        "phase": "plan",
        "status": status,
        **({"reason": notice} if notice else {}),
        "plan_id": plan["plan_id"],
        "projects": [{"root": str(root), "status": status} for root in selected],
        "cleanup_legacy": {"plan": plan, "plan_path": str(destination)},
    }, 2 if status == "blocked" else 0


def _read_document(
    path: Path, id_key: str, *, vault: Path | None = None,
) -> dict[str, Any]:
    _safe_path(path)
    require_private_directory(path.parent)
    if os.name == "nt":
        if vault is not None:
            for parent in path.parents[1:]:
                if not parent.is_relative_to(vault):
                    break
                require_private_directory(parent)
        assert_private_file(path)
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
    *,
    legacy_retry: bool = False,
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
    blocked = _blocked(payload)
    if any(item["reason"] == "vendor-mode-unproven" for item in blocked):
        _fail("vendor-mode-unproven", _VENDOR_MODE_UNPROVEN)
    if blocked:
        _fail(
            "blocked-target", "resolve blocked cleanup targets and generate a new plan"
        )
    _check_candidate_paths(plan, vault)
    if _windows_vendor_overlap(plan):
        _fail("windows-retirement-vendor-overlap", _WINDOWS_VENDOR_OVERLAP)
    if not legacy_retry and _unbound_vendor_overlap(plan):
        _fail("vendor-overlap-unproven", _VENDOR_OVERLAP_UNPROVEN)

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
        path = candidate["path"]
        # Pending targets sit at their sealed before-state, or exactly at the
        # expected_after a successful vendor transition recorded for them.
        completed = done.get(path)
        if completed is not None:
            _retired_matches(completed, check_mode=not legacy_retry)
            continue
        if candidate["kind"] == "trellis-uninstall":
            _preflight_vendor(candidate, vault, legacy_retry=legacy_retry)
        advance = progressed.get(path)
        allowed = advance["after"] if advance is not None else candidate["before"]
        if snapshot(Path(path)) != allowed:
            _fail("state-conflict", "cleanup target changed after plan or prior receipt")
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
    if host not in (None, "codex", "omp"):
        _fail("scope-conflict", "retirement host is not the active domain")
    active = {
        item["role"]: item["path"] for item in _domain_paths(host, _home(environ), environ)
    }
    configs = stored.get("configs")
    if not isinstance(configs, list):
        _fail("invalid-document", "retirement configs are not a list")
    seen: set[str] = set()
    for item in configs:
        if not isinstance(item, Mapping) or set(item) != {"role", "path"}:
            _fail("invalid-document", "retirement config is not a current domain")
        role = item["role"]
        if role not in active or role in seen:
            _fail("scope-conflict", "retirement config is outside the active host domain")
        seen.add(role)
        if item["path"] != str(_safe_path(Path(active[role]))):
            _fail("scope-conflict", "retirement config path is not the active domain target")
    projects = _bound_projects(stored.get("projects"), vault, _home(environ))
    if projects != stored.get("projects"):
        _fail("scope-conflict", "retirement project selection is not the active domain")
    reserved = set(active.values())
    if "omp-mcp" in active:
        reserved.add(str(Path(active["omp-mcp"]).with_name(".mcp.json")))
    launchers = _bound_launchers(stored.get("retiring_launchers"), vault, reserved)
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
    sealed_view = sealed.get("view") or {}
    if purpose == "cleanup" and (
        sealed.get("blocked") or (os.name == "nt" and sealed_view.get("stop"))
    ):
        _fail("blocked-target", "the sealed retirement inspection is blocked")
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
    for item in _all_candidates(plan):
        path = item["path"]
        if _graft_candidate(item) is not None and path in done:
            _preflight_restore_row(done[path], item, vault, allowed, rehearse_permissions=False)
    if purpose == "reset":
        _report, view = _retirement_view(selections[0], evidence, purpose="reset")
        candidates = _actionable_graft(view)
        if view.get("stop"):
            _fail("blocked-target", "retirement inspection is blocked")
    else:
        _report, view, candidates = _merged_graft(selections, evidence)
        reason = _cleanup_retirement_block(plan, view)
        if reason is not None:
            _fail("blocked-target", reason)
        original_blocked = _blocked_graft_paths(sealed_view)
        if view.get("stop"):
            live_blocked = _blocked_graft_paths(view)
            if original_blocked is None or live_blocked is None or not (
                live_blocked <= original_blocked if done else live_blocked == original_blocked
            ):
                _fail("scope-conflict", "the blocked retirement scope changed after confirmation")
        elif sealed_view.get("stop") and not done:
            _fail("scope-conflict", "the blocked retirement scope changed after confirmation")
    skip = done.keys() | (progressed or {}).keys()
    fresh = {
        str(candidate["path"]): _graft_identity(candidate)
        for candidate in candidates
        if candidate["path"] not in skip
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
        if candidate["path"] not in done and snapshot(Path(candidate["path"])) != candidate["before"]:
            _fail("state-conflict", "retirement target changed after the plan")


def _vendor_resources(candidate: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    from sbtd_trellis_uninstall import _bound_resource_path, _checked_state

    prepared = candidate["trellis"]
    payload = prepared["payload"]
    root = _safe_path(Path(candidate["root"]))
    if (
        payload.get("root") != str(root)
        or payload.get("status") != "ready"
        or prepared.get("prepared_id") != _digest(payload)
        or not isinstance(payload.get("resources"), list)
    ):
        _fail("binding-violation", "vendor preparation is not bound to the project")
    resources = {}
    paths: set[Path] = set()
    ids = set()
    for resource in payload["resources"]:
        if not isinstance(resource, Mapping):
            _fail("binding-violation", "a prepared vendor resource is malformed")
        path = _safe_path(_bound_resource_path(root, resource))
        identity = resource.get("resource_id")
        if path in paths or not isinstance(identity, str) or identity in ids:
            _fail("binding-violation", "prepared vendor resources repeat a path or identifier")
        kind = resource.get("kind")
        before = _checked_state(resource.get("before"))
        after = _checked_state(resource.get("expected_after"))
        if (
            (kind == "vendor-trellis-dir") != (str(path) == candidate["path"])
            or kind not in {"vendor-delete", "vendor-scrub", "vendor-trellis-dir", "vendor-prune-dir"}
            or before["type"] == "absent"
            or (kind in {"vendor-trellis-dir", "vendor-prune-dir"} and before["type"] != "directory")
            or (kind == "vendor-scrub" and before["type"] != "file")
            or after["type"] != ("file" if kind == "vendor-scrub" else "absent")
        ):
            _fail("binding-violation", "a prepared vendor resource has an unsupported transition")
        resources[str(path)] = resource
        paths.add(path)
        ids.add(identity)
    if candidate["path"] not in resources:
        _fail("binding-violation", "vendor preparation omits the selected .trellis directory")
    return resources


def _vendor_modes(
    modes: Any, resources: Mapping[str, Mapping[str, Any]], *, state: str = "before",
) -> Mapping[str, str | None]:
    if not isinstance(modes, Mapping) or modes.keys() != resources.keys():
        _fail("vendor-mode-unproven", _VENDOR_MODE_UNPROVEN)
    for path, mode in modes.items():
        if resources[path][state]["type"] == "absent":
            valid = mode is None
        else:
            valid = isinstance(mode, str) and len(mode) == 4 and all(char in "01234567" for char in mode)
        if not valid:
            _fail("vendor-mode-unproven", _VENDOR_MODE_UNPROVEN)
    return modes


def _vendor_backup_path(vault: Path, candidate: Mapping[str, Any], index: int) -> Path:
    return vault / candidate["trellis"]["prepared_id"] / "resources" / f"{index:03d}"


def _preflight_vendor(
    candidate: Mapping[str, Any], vault: Path, *, legacy_retry: bool = False,
    require_backups: bool = False,
) -> None:
    resources = _vendor_resources(candidate)
    mode_bound = not (legacy_retry and "vendor_modes_before" not in candidate)
    modes = _vendor_modes(candidate.get("vendor_modes_before"), resources) if mode_bound else {}
    for index, (path, resource) in enumerate(resources.items()):
        target = Path(path)
        if snapshot(target) != resource["before"] or (mode_bound and _mode_text(target) != modes[path]):
            _fail("state-conflict", "a vendor target changed after its pre-state was recorded")
        backup = _vendor_backup_path(vault, candidate, index)
        if require_backups or os.path.lexists(backup):
            _preflight_backup({
                "before": resource["before"], "mode_before": modes.get(path),
                "backup_ref": {"path": str(backup), "state": resource["before"]},
            }, vault, target, check_mode=mode_bound)


def _vendor_transitions(
    candidate: Mapping[str, Any], row: Mapping[str, Any], vault: Path, *, legacy_retry: bool = False,
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
    if (
        not isinstance(outcome, Mapping)
        or outcome.get("status") != "removed"
        or type(outcome.get("exit")) is not int
        or outcome.get("exit") != 0
        or outcome.get("prepared_id") != prepared.get("prepared_id")
        or outcome.get("root") != candidate["root"]
    ):
        _fail("binding-violation", "receipt vendor outcome is not bound to the plan")
    if not isinstance(outcome.get("results"), list):
        _fail("binding-violation", "receipt vendor results must be a list")
    resources = _vendor_resources(candidate)
    mode_bound = not (
        legacy_retry and "vendor_modes_before" not in candidate and "vendor_modes_after" not in row
    )
    modes_before = _vendor_modes(candidate.get("vendor_modes_before"), resources) if mode_bound else {}
    modes_after = (
        _vendor_modes(row.get("vendor_modes_after"), resources, state="expected_after") if mode_bound else {}
    )
    backup_paths = {
        path: _vendor_backup_path(vault, candidate, index)
        for index, path in enumerate(resources)
    }
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
        if not isinstance(backup, Mapping) or backup.get("path") != str(backup_paths[path]):
            _fail("binding-violation", "vendor backup is not bound to the prepared resource")
        transition = {
            "path": path,
            "before": resource["before"],
            "after": result["after"],
            "backup_ref": backup,
        }
        if mode_bound:
            transition.update(mode_before=modes_before[path], mode_after=modes_after[path])
        _preflight_backup(transition, vault, Path(path), check_mode=mode_bound)
        transitions[path] = transition
    if len(transitions) != len(resources):
        _fail("binding-violation", "receipt vendor outcome omits a prepared path")
    return {path: transitions[path] for path in resources}


def _retirement_options(
    item: Mapping[str, Any], plan_id: str, index: int, vault: Path,
) -> dict[str, Any]:
    path = Path(item["path"])
    return {
        "scope": path.parent,
        "vault": vault,
        "expected": {
            **item["before"], "mode": item["mode"],
            **({"windows_acl_digest": item["windows_acl_digest"]} if os.name == "nt" else {}),
        },
        "receipt_path": vault / plan_id / "retirement" / f"{index:03d}.json",
        "backup_path": vault / plan_id / "cleanup" / f"{index:03d}",
        "plan_id": plan_id,
    }


def _completed_retirement(
    item: Mapping[str, Any], outcome: Mapping[str, Any], options: Mapping[str, Any], index: int,
) -> dict[str, Any]:
    return {
        "resource_id": f"cleanup-{index:03d}",
        "kind": item["kind"],
        "path": item["path"],
        "status": "succeeded",
        "writes": True,
        "retirement_plan_id": options["plan_id"],
        "retirement_receipt": str(options["receipt_path"]),
        **{key: outcome[key] for key in ("before", "after", "mode_before", "mode_after", "backup_ref")},
        **{key: outcome[key] for key in (
            "retirement_completion", "windows_acl_digest", "windows_acl_digest_after",
        ) if key in outcome},
    }


def _retirement_writes(results: Mapping[str, Mapping[str, Any]]) -> bool | None:
    effects = {
        row.get("writes", True if row["status"] == "succeeded" else None)
        for row in results.values()
    }
    return True if True in effects else None if None in effects else False


def _previous_receipt(
    path: Path | None, plan: Mapping[str, Any], vault: Path, environ: Mapping[str, str],
    *, legacy_retry: bool = False,
):
    candidates = _all_candidates(plan)
    by_path = {item["path"]: item for item in candidates}
    results = {}
    if path is not None:
        if not _safe_path(path).is_relative_to(vault):
            _fail("scope-conflict", "cleanup receipt is outside the plan vault")
        previous = _read_document(path, "receipt_id", vault=vault)
        if previous["payload"]["plan_id"] != plan["plan_id"]:
            _fail("binding-violation", "cleanup receipt belongs to a different plan")
        for row in previous["payload"]["results"]:
            candidate = by_path.get(row["path"])
            if (
                candidate is None or row["kind"] != candidate["kind"]
                or row["before"] != candidate["before"] or row["path"] in results
            ):
                _fail("binding-violation", "receipt contains an unbound cleanup result")
            results[row["path"]] = row
    if any(item["kind"] == "graft-retire" for item in candidates):
        _assert_graft_domain(plan, _bound_graft_paths(plan, environ, vault))
    done = {}
    progressed: dict[str, dict[str, Any]] = {}
    vendor_rows = {}
    for index, candidate in enumerate(candidates):
        target = candidate["path"]
        row = results.get(target)
        if candidate["kind"] == "graft-retire" and not (
            row is not None and row["status"] == "succeeded" and "retirement_plan_id" not in row
        ):
            options = _retirement_options(candidate, plan["plan_id"], index, vault)
            try:
                outcome = _retirement().reconcile_candidate(
                    candidate, **options,
                    retirement_completion=row.get("retirement_completion") if row else None,
                )
            except contracts.ContractError as error:
                if error.code == "retirement-interrupted" and any(
                    "retirement_plan_id" in completed for completed in done.values()
                ):
                    error.details = {**(error.details or {}), "writes": 1}
                raise
            if outcome is not None and outcome["result"] == "skipped-complete":
                measured = _completed_retirement(candidate, outcome, options, index)
                if row is not None and row.get("retirement_completion") is not None:
                    # Reconciliation already matched the embedded copy to any
                    # durable receipt. Preserve the original receipt row.
                    measured["retirement_completion"] = row["retirement_completion"]
                if row is not None and row["status"] == "succeeded" and row != measured:
                    _fail("binding-violation", "cleanup receipt does not match the measured retirement")
                row = results[target] = measured
            elif row is not None and row["status"] == "succeeded":
                _fail("binding-violation", "cleanup receipt has no measured retirement")
            elif row is not None and (
                row.get("writes") is True
                or ("writes" in row and row["writes"] is None and outcome is None)
            ):
                _fail("retirement-interrupted", "cleanup requires a measured retirement outcome")
        if row is None:
            continue
        backup = row["backup_ref"]
        if backup:
            _preflight_backup(
                row, vault, Path(target),
                check_mode=not legacy_retry or row.get("mode_before") is not None,
            )
        if row["status"] == "succeeded":
            if not backup or row["after"] != _goal(candidate, backup, vault=vault):
                _fail(
                    "binding-violation",
                    "receipt success does not prove the intended result",
                )
            advance = progressed.get(row["path"])
            if advance is not None and "mode_before" in advance and row.get("mode_before") != advance["mode_before"]:
                _fail("binding-violation", "cleanup result does not bind the pre-vendor mode")
            done[row["path"]] = row
            progressed.pop(row["path"], None)
            if candidate["kind"] == "trellis-uninstall":
                transitions = _vendor_transitions(candidate, row, vault, legacy_retry=legacy_retry)
                vendor_rows[row["path"]] = transitions
                for resource_path, transition in transitions.items():
                    if resource_path == row["path"]:
                        if any(row.get(key) != transition[key] for key in ("after", "mode_before", "mode_after") if key in transition):
                            _fail("binding-violation", "cleanup result does not match the vendor directory transition")
                        continue
                    if resource_path in done or resource_path in progressed:
                        _fail("binding-violation", "another cleanup result already covers this vendor target")
                    other = by_path.get(resource_path)
                    if other is not None and transition["before"] != other["before"]:
                        _fail("binding-violation", "vendor transition does not match the sealed candidate")
                    progressed[resource_path] = transition
        else:
            advance = progressed.get(row["path"])
            allowed = (
                advance["after"] if advance is not None else row["before"]
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
    for transition in progressed.values():
        _retired_matches(transition, check_mode="mode_after" in transition)
    return results, done, progressed, vendor_rows


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
        # rc.2 cleanup had byte/state receipts, with no modes and no Graft
        # retirement scope. Resume only that already-sealed, non-Graft work.
        legacy_retry = cleanup_receipt_path is not None and "graftRetirement" not in plan["payload"]
        results, done, progressed, _vendor_rows = _previous_receipt(
            cleanup_receipt_path, plan, vault, environ, legacy_retry=legacy_retry,
        )
        _validate_scope(plan, done, progressed, environ, legacy_retry=legacy_retry)
    except (
        contracts.ContractError,
        TaskDataError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ) as error:
        if getattr(error, "code", None) == "retirement-interrupted":
            envelope, code = _rejection("apply", "retirement outcome is unproven; preserve the private vault")
            details = getattr(error, "details", None) or {}
            envelope["writes"] = True if details.get("writes") == 1 else None
            if details.get("retirement_intent"):
                envelope["cleanup_legacy"]["retirement_intent"] = details["retirement_intent"]
            return envelope, code
        return _rejection("apply", _VENDOR_REFUSALS.get(
            getattr(error, "code", None), "cleanup confirmation, scope, identity or evidence validation failed",
        ))
    from sbtd_migration import _prepare_backup_parent

    candidates = _all_candidates(plan)
    reset = plan["payload"].get("purpose") == "retirement-reset"
    started = _now()
    status = "cleaned"
    backups: dict[str, dict[str, Any]] = {}
    modes_before = {}
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
                modes_before[item["path"]] = advance.get("mode_before")
                continue
            destination = vault / plan["plan_id"] / "cleanup" / f"{index:03d}"
            _prepare_backup_parent(destination, vault)
            graft = _graft_candidate(item)
            mode = _mode_text(Path(item["path"]))
            if mode is None or (graft is not None and mode != graft.get("mode")):
                _fail("state-conflict", "cleanup could not bind the original mode before backing up")
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
            modes_before[item["path"]] = mode
            _preflight_backup({
                "before": item["before"], "mode_before": mode, "backup_ref": backup,
            }, vault, Path(item["path"]))
    except (contracts.ContractError, TaskDataError, OSError):
        envelope, code = _rejection(
            "apply", "backup preservation failed; no cleanup execution started", 3
        )
        if reset:
            envelope["writes"] = _retirement_writes(results)
        return envelope, code
    current_states = {
        item["path"]: (
            progressed[item["path"]]["after"]
            if item["path"] in progressed
            else item["before"]
        )
        for item in candidates
    }
    current_modes = {
        path: progressed[path]["mode_after"] if path in progressed else mode
        for path, mode in modes_before.items()
        if path not in progressed or "mode_after" in progressed[path]
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
            "mode_before": modes_before[str(path)],
            "mode_after": None,
            "backup_ref": backups[str(path)],
        }
        if native:
            row["windows_acl_digest"] = graft["windows_acl_digest"]
        standalone = item["kind"] == "graft-retire"
        if standalone:
            row["writes"] = False
        try:
            if snapshot(path) != current_states[str(path)] or (
                str(path) in current_modes and _mode_text(path) != current_modes[str(path)]
            ):
                _fail("state-conflict", "target bytes or mode changed during cleanup")
            if standalone:
                # The intent and receipt use the same verified per-plan backup on both systems.
                options = _retirement_options(item, plan["plan_id"], index, vault)
                _prepare_backup_parent(options["receipt_path"], vault)
                row["writes"] = None
                outcome = _retirement().apply_candidate(item, **options)
                results[str(path)] = _completed_retirement(item, outcome, options, index)
                continue
            if item["kind"] == "trellis-uninstall":
                from sbtd_trellis_uninstall import execute_trellis_uninstall

                outcome = execute_trellis_uninstall(
                    Path(item["root"]), item["trellis"], vault, environ=environ,
                    before_execute=lambda: _preflight_vendor(
                        item, vault, legacy_retry=legacy_retry, require_backups=True,
                    ),
                )
                row["vendor"] = outcome
                if outcome["status"] != "removed":
                    _fail("uninstall-failed", "vendor uninstall did not complete")
                if "vendor_modes_before" in item:
                    row["vendor_modes_after"] = {
                        path: _mode_text(Path(path)) for path in item["vendor_modes_before"]
                    }
                for resource_path, transition in _vendor_transitions(item, row, vault, legacy_retry=legacy_retry).items():
                    mode_bound = "mode_after" in transition
                    _retired_matches(transition, check_mode=mode_bound)
                    if resource_path in current_states:
                        current_states[resource_path] = transition["after"]
                        if mode_bound:
                            current_modes[resource_path] = transition["mode_after"]
                        else:
                            current_modes.pop(resource_path, None)
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
            if standalone and row["writes"] is None:
                details = getattr(error, "details", None) or {}
                if details.get("retirement_intent"):
                    row["retirement_intent"] = details["retirement_intent"]
                if "writes" in details:
                    row["writes"] = None if details["writes"] is None else bool(details["writes"])
                elif row["after"] == row["before"] and _mode_text(path) == row["mode_before"]:
                    row["writes"] = False
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
        envelope, code = _rejection(
            "apply",
            "cleanup may have written targets; receipt persistence failed; preserve the private backup directory",
            3,
        )
        envelope["plan_id"] = plan["plan_id"]
        if reset:
            envelope["writes"] = _retirement_writes(results)
        return envelope, code
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
    if reset:
        # Not the composed confirmation digest shown beside ordinary template writes.
        envelope["purpose"] = "retirement-reset"
        envelope["retirement_plan_id"] = plan["plan_id"]
        envelope["receipt_path"] = str(destination)
        envelope["writes"] = _retirement_writes(results)
    elif ((plan["payload"].get("graftRetirement") or {}).get("view") or {}).get("stop"):
        envelope["graftRetirement"] = {"status": "blocked", "scope": "legacy-only"}
        envelope["reason"] = _LEGACY_ONLY_NOTICE
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
    environ: Mapping[str, str] | None = None,
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
    if not os.path.lexists(destination):
        save_document(destination, plan, private_root=vault_path)
    elif read_file(destination) != _canonical_report(plan):
        _fail("binding-violation", "the saved retirement plan differs from the confirmed plan")
    if not sealed:
        return {
            **preview,
            "phase": "apply",
            "status": "nothing-to-clean",
            "plan_path": str(destination),
            "receipt_path": None,
            "receipt_id": None,
        }
    applied, _code = apply_cleanup_legacy(destination, confirm_cleanup=plan_id, environ=environ)
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
        "writes": applied.get("writes", False),
        **({"reason": applied["reason"]} if "reason" in applied else {}),
    }


_CLEANUP_RESTORE_KINDS = frozenset({
    "marker-blocks",
    "directory-remove",
    "skill-directory",
    "trellis-uninstall",
    "mcp-server-remove",
})


def _retired_matches(row: Mapping[str, Any], *, native: bool = False, check_mode: bool = True) -> None:
    path = _safe_path(Path(row["path"]))
    if str(path) != row["path"]:
        _fail("binding-violation", "restore path is not canonical")
    if snapshot(path) != row["after"]:
        _fail("state-conflict", "retired target no longer matches its receipt")
    if not check_mode:
        return
    if row["after"]["type"] == "absent":
        if "mode_after" not in row or row["mode_after"] is not None:
            _fail("binding-violation", "a removed target must record an absent mode")
        return
    if not isinstance(row.get("mode_after"), str) or _mode_text(path) != row["mode_after"]:
        _fail("state-conflict", "retired target mode does not match its receipt")
    if native:
        from sbtd_retirement import capture_windows_permissions

        capture_windows_permissions(path, row.get("windows_acl_digest_after"))


def _preflight_backup(row: Mapping[str, Any], vault: Path, live: Path, *, check_mode: bool = True) -> None:
    backup = row.get("backup_ref")
    if not isinstance(backup, Mapping) or "path" not in backup or "state" not in backup:
        _fail("backup-conflict", "restore has no trusted backup")
    backup_path = _safe_path(Path(backup["path"]))
    if not backup_path.is_relative_to(vault) or backup_path == live:
        _fail("scope-conflict", "restore backup is outside the private vault")
    if snapshot(backup_path) != row["before"] or backup.get("state") != row["before"]:
        _fail("backup-conflict", "restore backup does not match the recorded original")
    if not check_mode or row["before"]["type"] == "absent":
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
    payload = _read_document(receipt_path, "receipt_id", vault=vault)["payload"]
    schema = getattr(_retirement(), "RECEIPT_SCHEMA", None)
    if (
        payload.get("schema") != schema
        or payload.get("target") != str(target)
        or payload.get("candidate_id") != candidate.get("id")
        or "plan_id" in payload
        or "intent_id" in payload
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


def _bound_graft_paths(
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
        if "retirement_plan_id" not in row:
            _preflight_retirement_receipt(row, candidate, vault, path)
        if row.get("mode_before") != candidate.get("mode") or row.get("mode_after") != (
            None if row["after"]["type"] == "absent" else candidate.get("mode")
        ):
            _fail("binding-violation", "retirement receipt mode differs from the sealed candidate")
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
    _retired_matches(row, native=native)
    if row.get("retirement_receipt"):
        receipt_path = _safe_path(Path(row["retirement_receipt"]))
        intent_options = {}
        if "retirement_plan_id" in row:
            intent_options = {
                "plan_id": row["retirement_plan_id"],
                "backup_path": Path(row["backup_ref"]["path"]),
                "retirement_completion": row.get("retirement_completion"),
            }
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
            **intent_options,
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
    _restored_matches(row, path)


def _restored_matches(row: Mapping[str, Any], path: Path) -> None:
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
        _results, done, progressed, vendor_rows = _previous_receipt(receipt_path, plan, vault, environ)
        _validate_scope(plan, done, progressed, environ)
        allowed = _bound_graft_paths(plan, environ, vault)
        rows = []
        for candidate in _all_candidates(plan):
            row = done.get(candidate["path"])
            if row is None:
                continue
            sealed_target = _safe_path(Path(candidate["path"]))
            if str(sealed_target) != row["path"]:
                _fail("binding-violation", "receipt path is not the sealed plan target")
            _preflight_restore_row(row, candidate, vault, allowed)
            native = os.name == "nt" and _graft_candidate(candidate) is not None
            if row["kind"] == "trellis-uninstall":
                for path, transition in vendor_rows[row["path"]].items():
                    if path == row["path"]:
                        rows.append((row, sealed_target, native))
                    elif path not in done:
                        rows.append((transition, Path(path), False))
            else:
                rows.append((row, sealed_target, native))
        directories = {
            target: Path(row["backup_ref"]["path"]) for row, target, _native in rows
            if row["before"]["type"] == "directory"
        }
        restore = []
        covered = {}
        for row, target, native in reversed(rows):
            # A pruned directory's verified original already contains its
            # deleted children. Restore it once, but prove each child's mode too.
            parent = next((parent for parent in reversed(target.parents) if parent in directories), None)
            if parent is None:
                if not target.parent.is_dir():
                    _fail("state-conflict", "a rollback parent directory is missing")
                restore.append((row, target, native))
                continue
            original = directories[parent] / target.relative_to(parent)
            _preflight_backup({
                **row, "backup_ref": {"path": str(original), "state": row["before"]},
            }, vault, target)
            covered.setdefault(parent, []).append((row, target))
    except (
        contracts.ContractError,
        TaskDataError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ) as error:
        if getattr(error, "code", None) == "retirement-interrupted":
            return _rejection("rollback", "retirement outcome is unproven; preserve the private vault")
        return _rejection("rollback", _VENDOR_REFUSALS.get(
            getattr(error, "code", None), "rollback confirmation, scope, identity or evidence validation failed",
        ))
    try:
        for row, sealed_target, native in restore:
            _restore_retired(row, vault, sealed_target, native=native)
            for nested, path in covered.get(sealed_target, ()):
                _restored_matches(nested, path)
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
