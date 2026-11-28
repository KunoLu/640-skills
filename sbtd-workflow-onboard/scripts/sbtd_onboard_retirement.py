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
from sbtd_omp_sources import active_omp_paths
from sbtd_retirement import inspect_retirement, render_candidates
from sbtd_retirement_paths import LEGACY_LAUNCHER_RELATIVE


def _private_path(value: str | None) -> Path | None:
    if value is None:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute() or path.resolve() != path or not path.exists():
        raise ValueError("retirement inputs must use existing absolute physical paths")
    return path


def _domain_paths(host: str | None, home: Path, environ: Mapping[str, str]) -> list[dict[str, str]]:
    if host == "codex":
        domain = Path(environ.get("CODEX_HOME") or home / ".codex")
        return [{"role": role, "path": str(domain / name)} for role, name in (
            ("codex-mcp", "config.toml"), ("codex-hooks", "hooks.json"),
        )]
    if host == "omp":
        active = active_omp_paths(home=home, environ=environ)
        override = environ.get("PI_CODING_AGENT_DIR")
        if not active["profile"] and override:
            lexical = Path(override).expanduser().absolute()
            if lexical.resolve() != lexical:
                raise ValueError("retirement cannot follow a linked OMP agent directory")
        return [{"role": "omp-mcp", "path": str(active["target"])}]
    return []


def preview(args, *, action, operations, skills_root: Path, home: Path, environ, plan_entries):
    """Return public disclosure and private in-process execution data. No writes."""
    try:
        roots = [Path(x.strip()).expanduser() for x in (getattr(args, "projects_root", None) or "").split(",") if x.strip()]
        platform = (getattr(args, "platform", None) or "").strip().lower().replace("_", "-")
        host = {"codex": "codex", "oh-my-pi": "omp", "omp": "omp"}.get(platform)
        vault = _private_path(getattr(args, "retirement_backup_root", None))
        descriptor = _private_path(getattr(args, "retirement_evidence", None))
        if vault is not None:
            require_private_directory(vault)
        if descriptor is not None and (vault is None or not descriptor.is_relative_to(vault)):
            raise ValueError("retirement evidence must be inside the selected private backup root")
        if vault is not None and any(vault == op.target or vault.is_relative_to(op.target) or op.target.is_relative_to(vault) for op in operations):
            raise ValueError("retirement backup root overlaps an installation target")
        configs = _domain_paths(host, home, environ)
        replaced = [str(op.target / LEGACY_LAUNCHER_RELATIVE) for op in operations
                    if action == "reset" and not op.same_location and op.target == skills_root / "sbtd-workflow-onboard"]
        selections = {"host": host, "configs": configs, "projects": [str(p) for p in roots],
                      "vault": str(vault) if vault else None, "retiring_launchers": replaced}
        evidence = [{"kind": "descriptor", "path": str(descriptor)}] if descriptor else []
        report = inspect_retirement(selections=selections, evidence=evidence)
        render = render_candidates(report, purpose=action if action in ("check", "reset") else "plan")
        candidates = render["candidates"] if action == "reset" else []
        # A proven project fence is a selective write. Installing a whole
        # template afterwards would destroy both the user's rules and rollback.
        targets = {str(op.target) for op in operations if not op.same_location}
        overlaps = {item["path"] for item in report["items"] if item["path"] in targets}
        project_rules = {str(root / "AGENTS.md") for root in roots}
        retained = sorted(
            c["path"] for c in candidates
            if c["role"] == "agents-fence" and c["path"] in overlaps
            and c["path"] in project_rules
        )
        unsafe_overlap = action == "reset" and bool(overlaps.difference(retained))
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

            inputs = dict(selections=selections, evidence=evidence, vault=vault, report=report)
            preview_plan = plan_reset_retirement(**inputs)
            if preview_plan["status"] == "blocked":
                stop, reason = True, "The retirement-only plan is blocked. No reset writes are authorized."
            else:
                execution = (inputs, preview_plan["plan_id"])
                binding = {
                    "retirementPlan": preview_plan["plan_id"],
                    "installation": [row for row in plan_entries if row["target"] not in retained],
                }
                plan_id = hashlib.sha256(canonical_json_bytes(binding)).hexdigest()
        public = {**report, "blocked": stop, "reason": reason, "globalEffects": render["global_effects"],
                  "targetsToRetire": [str(c["path"]) for c in candidates],
                  "skipTemplateWrites": retained, "confirmationId": plan_id}
        return public, execution
    except (ContractError, ValueError, OSError, RuntimeError) as error:
        return {"status": "blocked", "blocked": True, "items": [], "reason": getattr(error, "code", "unsafe-retirement-input"),
                "nextStep": "Preserve existing files; check the selected physical paths and private evidence."}, None


def apply_reset(public, execution, confirmation):
    """Recompute the sealed retirement-only plan before ordinary writes."""
    if public["blocked"] or execution is None or confirmation != public["confirmationId"]:
        return {"status": "blocked", "reason": "Supply the exact displayed --confirm-retirement with --yes."}, 2
    from sbtd_cleanup_legacy import plan_reset_retirement

    inputs, retirement_id = execution
    try:
        result = plan_reset_retirement(**inputs, confirm=retirement_id)
    except (ContractError, ValueError, OSError, RuntimeError) as error:
        return {"status": "failed", "reason": getattr(error, "code", "retirement-failed"),
                "nextStep": "Preserve the private vault. Ordinary reset writes have not started."}, 3
    if result["status"] not in ("cleaned", "retired", "nothing-to-clean"):
        return result, 2 if result["status"] == "blocked" else 3
    return result, 0


def print_report(payload: Mapping[str, Any]) -> None:
    report = payload.get("graftRetirement")
    if not isinstance(report, dict):
        return
    print(f"Legacy retirement: {report['status']}")
    for item in report.get("items", []):
        status = item.get("status")
        detail = f"; ownership: {item['verification']}" if status == "dangling" else ""
        print(f"- {item.get('path')}: {status}{detail}")
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
