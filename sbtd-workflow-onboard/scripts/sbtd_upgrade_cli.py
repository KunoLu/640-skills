"""Public upgrade CLI: explicit inputs, phase-local consent, one redacted JSON result."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from onboard_contracts import ContractError
from sbtd_cleanup_targets import strict_json_object
from sbtd_migration_files import read_file, save_document, snapshot


def _load(value: str) -> dict[str, Any]:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("input path must not be empty")
    path = Path(value).expanduser().absolute()
    state = snapshot(path)
    if state["type"] != "file":
        raise ValueError("input must be a regular JSON file")
    return strict_json_object(read_file(path, state))


def _save(plan: dict[str, Any], output: str | None) -> str | None:
    if output is None:
        return None
    vault = Path(plan["payload"]["backup_root"])
    path = Path(output).expanduser().absolute()
    save_document(path, plan, private_root=vault)
    return str(path)


def _emit(args: Any, document: dict[str, Any], code: int) -> int:
    # Human output uses the same metadata-only document; never print raw errors
    # from JSON/TOML parsers or subprocess output that could contain credentials.
    print(json.dumps(document, ensure_ascii=False, allow_nan=False,
                     indent=None if args.json else 2))
    return code


def _failure(args: Any, error: Exception, mode: str) -> int:
    code = getattr(error, "exit_code", 2)
    return _emit(args, {"mode": mode, "phase": args.phase, "status": "blocked",
                        "reason": getattr(error, "code", "invalid-input"),
                        "nextStep": "Check input paths, private vault, declared dependencies and the selected phase; preserve originals."},
                 code if code in (2, 3) else 2)


def _validate_supplied_paths(args: Any, names: tuple[str, ...]) -> None:
    for name in names:
        value = getattr(args, name, None)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("a supplied path must not be blank")


def run_upgrade(args: Any) -> int:
    if args.phase == "verify" and args.probe and not args.yes:
        return _emit(args, {"mode": "upgrade", "phase": "verify", "status": "blocked",
                            "reason": "probe-confirmation-required"}, 2)
    try:
        _validate_supplied_paths(args, ("scope", "backup_root", "output", "plan", "receipt"))
        from sbtd_upgrade import apply_upgrade, plan_upgrade, verify_upgrade

        if args.phase == "plan":
            plan = plan_upgrade(_load(args.scope), Path(args.backup_root).expanduser().absolute())
            output = _save(plan, args.output)
            result = {"mode": "upgrade", "phase": "plan", "plan": plan, "plan_path": output}
            status = plan["payload"].get("status", "planned")
            return _emit(args, result, 2 if status == "blocked" else 0)
        plan = _load(args.plan)
        receipt = _load(args.receipt) if args.receipt is not None else None
        if args.phase == "apply":
            confirmed = args.confirm_plan if args.yes else None
            result = apply_upgrade(plan, confirmed=confirmed, receipt=receipt)
        else:
            result = verify_upgrade(plan, receipt=receipt, probe=args.probe)
        status = result.get("status", result.get("payload", {}).get("status"))
        code = 3 if status in {"failed", "partial"} else 0 if status in {"complete", "aligned"} else 2
        return _emit(args, result, code)
    except (ContractError, OSError, ValueError, TypeError, KeyError, ImportError) as error:
        return _failure(args, error, "upgrade")


def run_upgrade_recovery(args: Any) -> int:
    try:
        _validate_supplied_paths(
            args, ("upgrade_plan", "upgrade_receipt", "upgrade_recovery_plan",
                   "output", "recovery_receipt"),
        )
        from sbtd_upgrade import apply_recovery, plan_recovery

        if args.phase == "plan":
            plan = plan_recovery(_load(args.upgrade_plan), _load(args.upgrade_receipt))
            output = _save(plan, args.output)
            return _emit(args, {"mode": "recovery", "phase": "plan", "plan": plan,
                                "plan_path": output},
                         2 if plan["payload"].get("status") == "blocked" else 0)
        plan = _load(args.upgrade_recovery_plan)
        receipt = _load(args.recovery_receipt) if args.recovery_receipt is not None else None
        result = apply_recovery(plan, confirmed=args.confirm_recovery, receipt=receipt)
        status = result.get("status", result.get("payload", {}).get("status"))
        code = 3 if status in {"failed", "partial"} else 0 if status == "complete" else 2
        return _emit(args, result, code)
    except (ContractError, OSError, ValueError, TypeError, KeyError, ImportError) as error:
        return _failure(args, error, "recovery")
