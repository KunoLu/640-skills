"""Target SBTD workflow CLI argument grammar (P1-01 contract foundation).

``parse_workflow_args`` is the pure, executable parse contract for the target
workflow CLI: the existing check/check-projects/plan/init/reset/init-projects
modes without the removed Trellis flags, plus the full ``migration`` and
``recovery`` phase grammar from the PRD (sections 10.2.1 and 10.2.3).

The parser only validates argument combinations. It never reads or writes user
paths, never loads referenced artifacts, and is not wired into ``onboard.py``.
Authorization is never synthesized here: absent ``--yes``/``--confirm-cleanup``/
``--confirm-recovery`` tokens still parse so the owning handler can answer with
its blocked envelope, and confirmation IDs pass through unexamined because the
parser holds no loaded artifacts to compare them against.
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Mapping, Sequence
from typing import NoReturn

__all__ = ["parse_workflow_args"]

PROG = "onboard.py"

_DEVELOPER_PATTERN = re.compile(r"^[a-z0-9]+$")

_MIGRATION_PHASES = ("plan", "apply", "verify", "cleanup")
_RECOVERY_PHASES = ("plan", "apply")

# Phase rules map each phase to (required value options, optional options).
# Consent tokens (--yes/--confirm-cleanup/--confirm-recovery) are deliberately
# optional at parse level: the PRD makes their absence a blocked envelope from
# the handler, not an argparse syntax error.
_MIGRATION_RULES = {
    "plan": (
        ("projects_root", "backup_root", "custodian"),
        ("publication_decisions", "json"),
    ),
    "apply": (
        ("manifest",),
        ("apply_receipt", "yes", "json"),
    ),
    "verify": (
        ("manifest", "apply_receipt", "deployment_evidence"),
        ("json",),
    ),
    "cleanup": (
        ("manifest", "apply_receipt", "deployment_evidence", "verification"),
        ("cleanup_receipt", "confirm_cleanup", "json"),
    ),
}
_MIGRATION_VALUE_OPTIONS = (
    "projects_root",
    "backup_root",
    "custodian",
    "publication_decisions",
    "manifest",
    "apply_receipt",
    "deployment_evidence",
    "verification",
    "cleanup_receipt",
    "confirm_cleanup",
)
_MIGRATION_FLAG_OPTIONS = ("yes", "json")

_RECOVERY_RULES = {
    "plan": (
        ("manifest",),
        (
            "apply_receipt",
            "deployment_evidence",
            "cleanup_receipt",
            "projects_root",
            "json",
        ),
    ),
    "apply": (
        ("plan",),
        ("recovery_receipt", "confirm_recovery", "json"),
    ),
}
_RECOVERY_VALUE_OPTIONS = (
    "manifest",
    "apply_receipt",
    "deployment_evidence",
    "cleanup_receipt",
    "projects_root",
    "plan",
    "recovery_receipt",
    "confirm_recovery",
)
_RECOVERY_FLAG_OPTIONS = ("json",)

# init/init-projects migration context: the three deployment evidence inputs
# are one group; --previous-deployment-evidence may only extend the group.
_MIGRATION_CONTEXT_GROUP = (
    "migration_manifest",
    "migration_apply_receipt",
    "deployment_evidence_out",
)
_MIGRATION_CONTEXT_OPTIONAL = ("previous_deployment_evidence",)


def _option_name(dest: str) -> str:
    return "--" + dest.replace("_", "-")


def _developer(value: str) -> str:
    if not _DEVELOPER_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "developer must match ^[a-z0-9]+$ (lowercase letters and digits only)"
        )
    return value


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        # argparse diagnostics can interpolate private paths and arbitrary tokens.
        # Usage is built only from this module's fixed program/option declarations.
        super().error("invalid arguments; use --help for supported syntax")


class _Once(argparse.Action):
    """Single-value option that rejects repeats instead of last-value-wins."""

    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest) is not None:
            parser.error(f"{option_string} must be provided at most once")
        setattr(namespace, self.dest, values)


def _add_common_options(
    sub: argparse.ArgumentParser, *, projects_root_required: bool
) -> None:
    sub.add_argument(
        "--projects-root",
        action=_Once,
        required=projects_root_required,
        help="Comma-separated absolute project root paths.",
    )
    sub.add_argument(
        "--skip-project-agents",
        action="store_true",
        help="Do not install project AGENTS.md.",
    )
    sub.add_argument(
        "--global-agents-path",
        action=_Once,
        help="Override Codex global AGENTS.md path.",
    )
    sub.add_argument(
        "--global-skills-dir",
        action=_Once,
        help="Override global skills directory.",
    )
    sub.add_argument(
        "--yes",
        action="store_true",
        help="Allow init/reset to write files.",
    )
    sub.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable plan.",
    )
    sub.add_argument(
        "--platform",
        action=_Once,
        help="Target Agent platform: codex, claude, kimi, oh-my-pi, or omp.",
    )
    sub.add_argument(
        "--developer",
        action=_Once,
        type=_developer,
        help="Developer identity (lowercase letters and digits).",
    )


def _add_migration_context(sub: argparse.ArgumentParser) -> None:
    sub.add_argument(
        "--migration-manifest",
        action=_Once,
        help="Migration manifest file for a migration-context deployment.",
    )
    sub.add_argument(
        "--migration-apply-receipt",
        action=_Once,
        help="Complete apply receipt bound to the migration manifest.",
    )
    sub.add_argument(
        "--previous-deployment-evidence",
        action=_Once,
        help="Previous deployment evidence file; required on retry, never alone.",
    )
    sub.add_argument(
        "--deployment-evidence-out",
        action=_Once,
        help="Unoccupied private target file for the new deployment evidence.",
    )


def _build_parser() -> tuple[
    argparse.ArgumentParser, dict[str, argparse.ArgumentParser]
]:
    parser = _ArgumentParser(
        prog=PROG,
        allow_abbrev=False,
        description="Target SBTD workflow CLI grammar (contract; not the live entry point).",
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)
    subs: dict[str, argparse.ArgumentParser] = {}

    for mode in ("check", "plan", "init", "reset", "init-projects"):
        sub = subparsers.add_parser(mode, allow_abbrev=False)
        _add_common_options(sub, projects_root_required=mode == "init-projects")
        if mode in ("init", "init-projects"):
            _add_migration_context(sub)
        subs[mode] = sub

    project_check = subparsers.add_parser("check-projects", allow_abbrev=False)
    project_check.add_argument(
        "--projects-root",
        action=_Once,
        required=True,
        help="Comma-separated absolute project root paths.",
    )
    project_check.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable project checks.",
    )
    project_check.add_argument(
        "--skip-project-agents",
        action="store_true",
        help="Exclude project AGENTS.md from installation-target checks.",
    )
    subs["check-projects"] = project_check

    migration = subparsers.add_parser("migration", allow_abbrev=False)
    migration.add_argument(
        "--phase",
        action=_Once,
        required=True,
        choices=_MIGRATION_PHASES,
        help="Migration phase: plan, apply, verify, or cleanup (no deploy phase).",
    )
    migration.add_argument(
        "--projects-root",
        action=_Once,
        help="Comma-separated absolute project root paths (plan only).",
    )
    migration.add_argument(
        "--backup-root",
        action=_Once,
        help="Private backup directory outside the repositories (plan only).",
    )
    migration.add_argument(
        "--custodian",
        action=_Once,
        help="Label of the responsible custodian (plan only).",
    )
    migration.add_argument(
        "--publication-decisions",
        action=_Once,
        help="Private publication-decisions file (plan only).",
    )
    migration.add_argument(
        "--manifest",
        action=_Once,
        help="Migration manifest file (apply/verify/cleanup).",
    )
    migration.add_argument(
        "--apply-receipt",
        action=_Once,
        help="Apply receipt: optional retry input for apply, required evidence for verify/cleanup.",
    )
    migration.add_argument(
        "--deployment-evidence",
        action=_Once,
        help="Deployment evidence file (verify/cleanup).",
    )
    migration.add_argument(
        "--verification",
        action=_Once,
        help="Verification record file (cleanup only).",
    )
    migration.add_argument(
        "--cleanup-receipt",
        action=_Once,
        help="Cleanup receipt for an explicit cleanup retry (cleanup only).",
    )
    migration.add_argument(
        "--confirm-cleanup",
        action=_Once,
        help="verification_id confirmed this run; absence stays blocked in the handler.",
    )
    migration.add_argument(
        "--yes",
        action="store_true",
        help="Authorize migration apply writes; never a cleanup consent.",
    )
    migration.add_argument(
        "--json",
        action="store_true",
        help="Print the single machine-readable envelope.",
    )
    subs["migration"] = migration

    recovery = subparsers.add_parser("recovery", allow_abbrev=False)
    recovery.add_argument(
        "--phase",
        action=_Once,
        required=True,
        choices=_RECOVERY_PHASES,
        help="Recovery phase: plan or apply.",
    )
    recovery.add_argument(
        "--manifest",
        action=_Once,
        help="Migration manifest file (plan only).",
    )
    recovery.add_argument(
        "--apply-receipt",
        action=_Once,
        help="Apply receipt evidence, possibly partial (plan only).",
    )
    recovery.add_argument(
        "--deployment-evidence",
        action=_Once,
        help="Deployment evidence, possibly partial (plan only).",
    )
    recovery.add_argument(
        "--cleanup-receipt",
        action=_Once,
        help="Cleanup receipt evidence, possibly partial (plan only).",
    )
    recovery.add_argument(
        "--projects-root",
        action=_Once,
        help="Optional manifest project subset for the recovery plan (plan only).",
    )
    recovery.add_argument(
        "--plan",
        action=_Once,
        help="Recovery plan file (apply only).",
    )
    recovery.add_argument(
        "--recovery-receipt",
        action=_Once,
        help="Recovery receipt for an explicit apply retry (apply only).",
    )
    recovery.add_argument(
        "--confirm-recovery",
        action=_Once,
        help="plan_id confirmed this run; absence stays blocked in the handler.",
    )
    recovery.add_argument(
        "--json",
        action="store_true",
        help="Print the single machine-readable envelope.",
    )
    subs["recovery"] = recovery

    return parser, subs


def _check_phase(
    sub: argparse.ArgumentParser,
    args: argparse.Namespace,
    value_options: Sequence[str],
    flag_options: Sequence[str],
    rules: Mapping[str, tuple[Sequence[str], Sequence[str]]],
) -> None:
    required, optional = rules[args.phase]
    allowed = set(required) | set(optional)
    for dest in value_options:
        if getattr(args, dest) is not None and dest not in allowed:
            sub.error(f"{_option_name(dest)} is not valid for phase {args.phase!r}")
    for dest in flag_options:
        if getattr(args, dest) and dest not in allowed:
            sub.error(f"{_option_name(dest)} is not valid for phase {args.phase!r}")
    for dest in required:
        if getattr(args, dest) is None:
            sub.error(f"{_option_name(dest)} is required for phase {args.phase!r}")


def _check_migration_context(
    sub: argparse.ArgumentParser, args: argparse.Namespace
) -> None:
    group = _MIGRATION_CONTEXT_GROUP + _MIGRATION_CONTEXT_OPTIONAL
    if all(getattr(args, dest) is None for dest in group):
        return
    missing = [
        _option_name(dest)
        for dest in _MIGRATION_CONTEXT_GROUP
        if getattr(args, dest) is None
    ]
    if missing:
        sub.error(
            "migration context requires --migration-manifest, --migration-apply-receipt "
            "and --deployment-evidence-out as a group; missing " + ", ".join(missing)
        )


def parse_workflow_args(argv: Sequence[str]) -> argparse.Namespace:
    """Parse target workflow CLI arguments into an argparse.Namespace.

    Pure parsing only: no referenced path is read or written, no artifact is
    loaded, and no consent is invented. Syntax and combination errors follow
    argparse semantics: a diagnostic on stderr and exit status 2.
    """

    parser, subs = _build_parser()
    args = parser.parse_args(argv)
    if args.mode == "migration":
        _check_phase(
            subs["migration"],
            args,
            _MIGRATION_VALUE_OPTIONS,
            _MIGRATION_FLAG_OPTIONS,
            _MIGRATION_RULES,
        )
    elif args.mode == "recovery":
        _check_phase(
            subs["recovery"],
            args,
            _RECOVERY_VALUE_OPTIONS,
            _RECOVERY_FLAG_OPTIONS,
            _RECOVERY_RULES,
        )
    elif args.mode in ("init", "init-projects"):
        _check_migration_context(subs[args.mode], args)
    return args
