"""Join read-only retirement discovery to ordinary Onboard plan and reset.

This module never discovers another host account. Only reset can consume the
separate digest of the displayed installation targets and retirement actions.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Mapping

from onboard_contracts import ContractError, canonical_json_bytes
from sbtd_migration_files import require_private_directory
from sbtd_retirement_paths import LEGACY_LAUNCHER_RELATIVE


def _private_path(value: str | None) -> Path | None:
    if value is None:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute() or path.resolve() != path or not path.exists():
        raise ValueError("retirement inputs must use existing absolute physical paths")
    return path


def preview(
    args, *, action, operations, skills_root: Path, home: Path, environ, plan_entries,
    other_directory_targets=(),
):
    """Return public disclosure and private in-process execution data. No writes."""
    try:
        from sbtd_cleanup_legacy import _domain_paths, _retirement_view, _safe_path

        roots = list(dict.fromkeys(
            _safe_path(Path(value.strip()).expanduser())
            for value in (getattr(args, "projects_root", None) or "").split(",") if value.strip()
        ))
        platform = (getattr(args, "platform", None) or "").strip().lower().replace("_", "-")
        host = {"codex": "codex", "oh-my-pi": "omp", "omp": "omp"}.get(platform)
        vault = _private_path(getattr(args, "retirement_backup_root", None))
        descriptor = _private_path(getattr(args, "retirement_evidence", None))
        if vault is not None:
            require_private_directory(vault)
        if descriptor is not None and (vault is None or not descriptor.is_relative_to(vault)):
            raise ValueError("retirement evidence must be inside the selected private backup root")
        active = [op for op in operations if not op.same_location]
        targets = {op.target.resolve() for op in active}
        directories = {op.target.resolve() for op in active if op.kind == "dir"}
        directories.update(path.resolve() for path in other_directory_targets)
        if vault is not None and any(
            vault.is_relative_to(target) or target.is_relative_to(vault)
            for target in directories | targets
        ):
            raise ValueError("retirement backup root overlaps an installation target")
        configs = _domain_paths(host, home, environ)
        onboard_target = (skills_root / "sbtd-workflow-onboard").resolve()
        replaced = sorted(
            str(target / LEGACY_LAUNCHER_RELATIVE)
            for target in directories
            if action == "reset" and (
                target == onboard_target or os.path.lexists(target / LEGACY_LAUNCHER_RELATIVE)
            )
        )
        selections = {"host": host, "configs": configs, "projects": [str(p) for p in roots],
                      "vault": str(vault) if vault else None, "retiring_launchers": replaced}
        evidence = [{"kind": "descriptor", "path": str(descriptor)}] if descriptor else []
        report, render = _retirement_view(
            selections, evidence, purpose=action if action in ("check", "reset") else "plan",
        )
        candidates = render["candidates"] if action == "reset" else []
        # A proven project fence is a selective write. Installing a whole
        # template afterwards would destroy both the user's rules and rollback.
        project_rules = {root / "AGENTS.md" for root in roots}
        config_paths = {Path(item["path"]) for item in configs if os.path.lexists(item["path"])}
        if host == "omp":
            config_paths.update(
                path for config in configs
                if os.path.lexists(path := Path(config["path"]).with_name(".mcp.json"))
            )
        watched = config_paths | {Path(item["path"]) for item in report["items"]}
        overlaps = {str(path) for path in watched if path.resolve() in targets}
        watched_files = watched | {path for path in project_rules if os.path.lexists(path)}
        directory_overlaps = [
            {"installationTarget": str(target), "retirementPath": str(path)}
            for target in sorted(directories)
            for path in sorted(watched_files)
            if action == "reset" and path.resolve().is_relative_to(target)
        ]
        retained = sorted(
            c["path"] for c in candidates
            if c["role"] == "agents-fence" and c["path"] in overlaps
            and Path(c["path"]) in project_rules
        )
        unsafe_overlap = action == "reset" and bool(directory_overlaps or overlaps.difference(retained))
        stop = bool(report["status"] == "blocked" or render["stop"] or unsafe_overlap)
        reason = render.get("stop_reason")
        if unsafe_overlap:
            reason = "Another installation would overwrite a preserved retirement target. Exclude that target and preview again."
        if candidates and vault is None:
            stop, reason = True, "Select an existing private --retirement-backup-root before confirming retirement."
        if host is None and any(os.path.lexists(launcher) for launcher in replaced):
            stop, reason = True, "Select the affected Codex or OMP domain explicitly before replacing an existing legacy launcher."
        execution = None
        plan_id = None
        if candidates and not stop:
            from sbtd_cleanup_legacy import plan_reset_retirement

            inputs = dict(selections=selections, evidence=evidence, vault=vault, report=report, environ=environ)
            preview_plan = plan_reset_retirement(**inputs)
            if preview_plan["status"] == "blocked":
                stop, reason = True, "The retirement-only plan is blocked. No reset writes are authorized."
            else:
                execution = (inputs, preview_plan["plan_id"])
                binding = {
                    "retirementPlan": preview_plan["plan_id"],
                    "installation": [row for row in plan_entries if row["target"] not in retained],
                    "directoryInstallation": sorted(map(str, directories)),
                }
                plan_id = hashlib.sha256(canonical_json_bytes(binding)).hexdigest()
        public = {**report, "blocked": stop, "reason": reason, "globalEffects": render["global_effects"],
                  "targetsToRetire": [str(c["path"]) for c in candidates],
                  "directoryOverlaps": directory_overlaps,
                  "skipTemplateWrites": retained, "confirmationId": plan_id}
        return public, execution
    except (ContractError, ValueError, OSError, RuntimeError) as error:
        return {"status": "blocked", "blocked": True, "items": [], "reason": getattr(error, "code", "unsafe-retirement-input"),
                "nextStep": "Preserve existing files; check the selected physical paths and private evidence."}, None


def apply_reset(public, execution, confirmation):
    """Recompute the sealed retirement-only plan before ordinary writes."""
    if public["blocked"] or execution is None or confirmation != public["confirmationId"]:
        return {"status": "blocked", "writes": False,
                "reason": "Supply the exact displayed --confirm-retirement with --yes."}, 2
    from sbtd_cleanup_legacy import plan_reset_retirement

    inputs, retirement_id = execution
    try:
        result = plan_reset_retirement(**inputs, confirm=retirement_id)
    except (ContractError, ValueError, OSError, RuntimeError) as error:
        return {"status": "failed", "writes": None, "reason": getattr(error, "code", "retirement-failed"),
                "nextStep": "Preserve the private vault. Ordinary reset writes have not started."}, 3
    if result["status"] not in ("cleaned", "retired", "nothing-to-clean"):
        return result, 2 if result["status"] == "blocked" else 3
    return result, 0


def print_report(payload: Mapping[str, Any]) -> None:
    report = payload.get("graftRetirement")
    if not isinstance(report, dict):
        return
    print(f"Legacy retirement: {report['status']}")
    retiring = set(report.get("targetsToRetire", [])) if not report.get("blocked") else set()
    for item in report.get("items", []):
        status = item.get("status")
        detail = f"; ownership: {item['verification']}" if status == "dangling" else ""
        action = item.get("action") if item["path"] in retiring else "preserve"
        print(f"- {item['path']!r}: {item['entry']!r}: {action} ({status}{detail})")
    for overlap in report.get("directoryOverlaps", []):
        print(f"- {overlap['retirementPath']!r}: overlaps installation directory {overlap['installationTarget']!r}")
    for path in report.get("skipTemplateWrites", []):
        print(f"- {path}: retire only the proven fence; do not install a replacement template")
    if report.get("globalEffects"):
        print("Global host configuration changes affect other projects using that host domain.")
    for entry in report.get("manual", []):
        where = f" (working directory: {entry['cwd']})" if entry.get("cwd") else ""
        print(f"  Manual only; inspect {entry['path']} first{where}: {entry['command']}")
    if report.get("reason"):
        print(f"  {report['reason']}")
    if report.get("nextStep"):
        print(f"  {report['nextStep']}")
    if report.get("confirmationId"):
        print(f"  Confirm these targets with --confirm-retirement {report['confirmationId']} and --yes.")
