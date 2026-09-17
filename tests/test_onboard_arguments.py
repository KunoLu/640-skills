from __future__ import annotations

import contextlib
import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARGUMENTS = ROOT / "sbtd-workflow-onboard" / "scripts" / "onboard_arguments.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("onboard_arguments", ARGUMENTS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


onboard_arguments = _load_module()
parse_workflow_args = onboard_arguments.parse_workflow_args


class ParseErrorAssertions(unittest.TestCase):
    def assert_parse_error(self, argv, *needles: str) -> str:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
            self.assertRaises(SystemExit) as caught,
        ):
            parse_workflow_args(argv)
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(stdout.getvalue(), "")
        message = stderr.getvalue()
        self.assertTrue(message.strip())
        for needle in needles:
            self.assertIn(needle, message)
        return message


class CommonModeGrammarTests(ParseErrorAssertions):
    def test_check_parses_with_common_options_and_developer(self) -> None:
        args = parse_workflow_args(
            [
                "check",
                "--projects-root",
                "/repo/one,/repo/two",
                "--skip-project-agents",
                "--global-agents-path",
                "/home/me/.codex/AGENTS.md",
                "--global-skills-dir",
                "/home/me/.codex/skills",
                "--platform",
                "codex",
                "--developer",
                "dev01",
                "--json",
            ]
        )
        self.assertEqual(args.mode, "check")
        self.assertEqual(args.projects_root, "/repo/one,/repo/two")
        self.assertTrue(args.skip_project_agents)
        self.assertEqual(args.global_agents_path, "/home/me/.codex/AGENTS.md")
        self.assertEqual(args.global_skills_dir, "/home/me/.codex/skills")
        self.assertEqual(args.platform, "codex")
        self.assertEqual(args.developer, "dev01")
        self.assertTrue(args.json)
        self.assertFalse(args.yes)

    def test_check_allows_omitted_projects_root(self) -> None:
        args = parse_workflow_args(["check"])
        self.assertIsNone(args.projects_root)

    def test_plan_and_reset_parse_common_options(self) -> None:
        plan = parse_workflow_args(["plan", "--platform", "omp", "--developer", "a1"])
        self.assertEqual(plan.mode, "plan")
        reset = parse_workflow_args(["reset", "--yes", "--json"])
        self.assertEqual(reset.mode, "reset")
        self.assertTrue(reset.yes)

    def test_init_projects_requires_projects_root(self) -> None:
        self.assert_parse_error(["init-projects"], "--projects-root")
        args = parse_workflow_args(["init-projects", "--projects-root", "/repo/one"])
        self.assertEqual(args.projects_root, "/repo/one")

    def test_check_projects_grammar(self) -> None:
        self.assert_parse_error(["check-projects"], "--projects-root")
        args = parse_workflow_args(
            ["check-projects", "--projects-root", "/repo/one", "--json"]
        )
        self.assertEqual(args.mode, "check-projects")
        self.assertTrue(args.json)
        self.assert_parse_error(
            ["check-projects", "--projects-root", "/repo/one", "--yes"],
            "--yes",
        )

    def test_developer_rejects_non_matching_values(self) -> None:
        self.assert_parse_error(["check", "--developer", "Alice"], "--developer")
        self.assert_parse_error(["check", "--developer", "dev_1"], "--developer")
        self.assert_parse_error(["check", "--developer", ""], "--developer")
        self.assert_parse_error(["check", "--developer", "dev-1"], "--developer")


class MigrationContextTests(ParseErrorAssertions):
    def test_init_accepts_full_migration_context(self) -> None:
        args = parse_workflow_args(
            [
                "init",
                "--migration-manifest",
                "/private/manifest.json",
                "--migration-apply-receipt",
                "/private/apply.json",
                "--previous-deployment-evidence",
                "/private/previous.json",
                "--deployment-evidence-out",
                "/private/next.json",
                "--yes",
                "--json",
            ]
        )
        self.assertEqual(args.migration_manifest, "/private/manifest.json")
        self.assertEqual(args.migration_apply_receipt, "/private/apply.json")
        self.assertEqual(args.previous_deployment_evidence, "/private/previous.json")
        self.assertEqual(args.deployment_evidence_out, "/private/next.json")

    def test_init_accepts_group_without_previous(self) -> None:
        args = parse_workflow_args(
            [
                "init-projects",
                "--projects-root",
                "/repo/one",
                "--migration-manifest",
                "m.json",
                "--migration-apply-receipt",
                "a.json",
                "--deployment-evidence-out",
                "out.json",
            ]
        )
        self.assertIsNone(args.previous_deployment_evidence)

    def test_partial_group_is_rejected(self) -> None:
        self.assert_parse_error(
            ["init", "--migration-manifest", "m.json"],
            "--migration-apply-receipt",
            "--deployment-evidence-out",
        )
        self.assert_parse_error(
            [
                "init",
                "--migration-manifest",
                "m.json",
                "--migration-apply-receipt",
                "a.json",
            ],
            "--deployment-evidence-out",
        )

    def test_previous_alone_cannot_complete_the_group(self) -> None:
        self.assert_parse_error(
            ["init", "--previous-deployment-evidence", "previous.json"],
            "--migration-manifest",
        )

    def test_migration_context_is_rejected_on_other_modes(self) -> None:
        self.assert_parse_error(
            ["check", "--migration-manifest", "m.json"], "--migration-manifest"
        )
        self.assert_parse_error(
            ["plan", "--deployment-evidence-out", "out.json"],
            "--deployment-evidence-out",
        )
        self.assert_parse_error(
            ["reset", "--migration-apply-receipt", "a.json"],
            "--migration-apply-receipt",
        )


class MigrationPhaseTests(ParseErrorAssertions):
    def test_plan_phase_shape(self) -> None:
        args = parse_workflow_args(
            [
                "migration",
                "--phase",
                "plan",
                "--projects-root",
                "/repo/one,/repo/two",
                "--backup-root",
                "/private/backup",
                "--custodian",
                "release-owner",
                "--json",
            ]
        )
        self.assertEqual(args.mode, "migration")
        self.assertEqual(args.phase, "plan")
        self.assertEqual(args.backup_root, "/private/backup")
        self.assertEqual(args.custodian, "release-owner")
        self.assertIsNone(args.publication_decisions)

    def test_plan_phase_accepts_publication_decisions(self) -> None:
        args = parse_workflow_args(
            [
                "migration",
                "--phase",
                "plan",
                "--projects-root",
                "/repo/one",
                "--backup-root",
                "/private/backup",
                "--custodian",
                "release-owner",
                "--publication-decisions",
                "/private/decisions.json",
            ]
        )
        self.assertEqual(args.publication_decisions, "/private/decisions.json")

    def test_plan_phase_missing_required_inputs(self) -> None:
        self.assert_parse_error(
            [
                "migration",
                "--phase",
                "plan",
                "--projects-root",
                "/repo/one",
                "--custodian",
                "release-owner",
            ],
            "--backup-root",
        )
        self.assert_parse_error(
            ["migration", "--phase", "plan", "--projects-root", "/repo/one"],
            "--backup-root",
            "--custodian",
        )

    def test_apply_phase_shapes(self) -> None:
        first = parse_workflow_args(
            ["migration", "--phase", "apply", "--manifest", "/private/manifest.json"]
        )
        self.assertEqual(first.manifest, "/private/manifest.json")
        self.assertIsNone(first.apply_receipt)
        self.assertFalse(first.yes)

        retry = parse_workflow_args(
            [
                "migration",
                "--phase",
                "apply",
                "--manifest",
                "/private/manifest.json",
                "--apply-receipt",
                "/private/apply.json",
                "--yes",
                "--json",
            ]
        )
        self.assertEqual(retry.apply_receipt, "/private/apply.json")
        self.assertTrue(retry.yes)

    def test_apply_phase_requires_manifest(self) -> None:
        self.assert_parse_error(["migration", "--phase", "apply"], "--manifest")

    def test_verify_phase_shape(self) -> None:
        args = parse_workflow_args(
            [
                "migration",
                "--phase",
                "verify",
                "--manifest",
                "m.json",
                "--apply-receipt",
                "a.json",
                "--deployment-evidence",
                "d.json",
                "--json",
            ]
        )
        self.assertEqual(args.deployment_evidence, "d.json")

    def test_verify_phase_requires_full_evidence_chain(self) -> None:
        self.assert_parse_error(
            ["migration", "--phase", "verify", "--manifest", "m.json"],
            "--apply-receipt",
            "--deployment-evidence",
        )
        self.assert_parse_error(
            [
                "migration",
                "--phase",
                "verify",
                "--manifest",
                "m.json",
                "--apply-receipt",
                "a.json",
            ],
            "--deployment-evidence",
        )

    def test_cleanup_phase_shape(self) -> None:
        args = parse_workflow_args(
            [
                "migration",
                "--phase",
                "cleanup",
                "--manifest",
                "m.json",
                "--apply-receipt",
                "a.json",
                "--deployment-evidence",
                "d.json",
                "--verification",
                "v.json",
                "--cleanup-receipt",
                "c.json",
                "--confirm-cleanup",
                "verification-id-value",
                "--json",
            ]
        )
        self.assertEqual(args.verification, "v.json")
        self.assertEqual(args.cleanup_receipt, "c.json")
        self.assertEqual(args.confirm_cleanup, "verification-id-value")

    def test_cleanup_phase_requires_bound_evidence(self) -> None:
        self.assert_parse_error(
            [
                "migration",
                "--phase",
                "cleanup",
                "--manifest",
                "m.json",
                "--apply-receipt",
                "a.json",
                "--deployment-evidence",
                "d.json",
            ],
            "--verification",
        )

    def test_deploy_phase_does_not_exist(self) -> None:
        self.assert_parse_error(
            ["migration", "--phase", "deploy", "--manifest", "m.json"],
            "deploy",
        )

    def test_cross_phase_options_are_rejected(self) -> None:
        self.assert_parse_error(
            [
                "migration",
                "--phase",
                "plan",
                "--projects-root",
                "/repo/one",
                "--backup-root",
                "/private/backup",
                "--custodian",
                "owner",
                "--apply-receipt",
                "a.json",
            ],
            "--apply-receipt",
        )
        self.assert_parse_error(
            [
                "migration",
                "--phase",
                "apply",
                "--manifest",
                "m.json",
                "--publication-decisions",
                "p.json",
            ],
            "--publication-decisions",
        )
        self.assert_parse_error(
            [
                "migration",
                "--phase",
                "verify",
                "--manifest",
                "m.json",
                "--apply-receipt",
                "a.json",
                "--deployment-evidence",
                "d.json",
                "--cleanup-receipt",
                "c.json",
            ],
            "--cleanup-receipt",
        )
        self.assert_parse_error(
            [
                "migration",
                "--phase",
                "cleanup",
                "--manifest",
                "m.json",
                "--apply-receipt",
                "a.json",
                "--deployment-evidence",
                "d.json",
                "--verification",
                "v.json",
                "--projects-root",
                "/repo/one",
            ],
            "--projects-root",
        )

    def test_yes_cannot_replace_confirm_cleanup(self) -> None:
        self.assert_parse_error(
            [
                "migration",
                "--phase",
                "cleanup",
                "--manifest",
                "m.json",
                "--apply-receipt",
                "a.json",
                "--deployment-evidence",
                "d.json",
                "--verification",
                "v.json",
                "--yes",
            ],
            "--yes",
        )
        self.assert_parse_error(
            [
                "migration",
                "--phase",
                "plan",
                "--projects-root",
                "/repo/one",
                "--backup-root",
                "/private/backup",
                "--custodian",
                "owner",
                "--yes",
            ],
            "--yes",
        )

    def test_missing_consent_tokens_parse_for_blocked_envelope(self) -> None:

        cleanup_args = parse_workflow_args(
            [
                "migration",
                "--phase",
                "cleanup",
                "--manifest",
                "m.json",
                "--apply-receipt",
                "a.json",
                "--deployment-evidence",
                "d.json",
                "--verification",
                "v.json",
            ]
        )
        self.assertIsNone(cleanup_args.confirm_cleanup)


class RecoveryPhaseTests(ParseErrorAssertions):
    def test_plan_phase_shapes(self) -> None:
        minimal = parse_workflow_args(
            ["recovery", "--phase", "plan", "--manifest", "m.json"]
        )
        self.assertEqual(minimal.mode, "recovery")
        self.assertEqual(minimal.phase, "plan")
        self.assertIsNone(minimal.apply_receipt)
        self.assertIsNone(minimal.projects_root)

        full = parse_workflow_args(
            [
                "recovery",
                "--phase",
                "plan",
                "--manifest",
                "m.json",
                "--apply-receipt",
                "a.json",
                "--deployment-evidence",
                "d.json",
                "--cleanup-receipt",
                "c.json",
                "--projects-root",
                "/repo/one",
                "--json",
            ]
        )
        self.assertEqual(full.cleanup_receipt, "c.json")
        self.assertEqual(full.projects_root, "/repo/one")

    def test_plan_phase_requires_manifest(self) -> None:
        self.assert_parse_error(["recovery", "--phase", "plan"], "--manifest")

    def test_apply_phase_shapes(self) -> None:
        first = parse_workflow_args(
            ["recovery", "--phase", "apply", "--plan", "p.json"]
        )
        self.assertEqual(first.plan, "p.json")
        self.assertIsNone(first.recovery_receipt)
        self.assertIsNone(first.confirm_recovery)

        retry = parse_workflow_args(
            [
                "recovery",
                "--phase",
                "apply",
                "--plan",
                "p.json",
                "--recovery-receipt",
                "r.json",
                "--confirm-recovery",
                "plan-id-value",
                "--json",
            ]
        )
        self.assertEqual(retry.recovery_receipt, "r.json")
        self.assertEqual(retry.confirm_recovery, "plan-id-value")

    def test_apply_phase_requires_plan(self) -> None:
        self.assert_parse_error(["recovery", "--phase", "apply"], "--plan")

    def test_apply_cannot_override_projects_root(self) -> None:
        self.assert_parse_error(
            [
                "recovery",
                "--phase",
                "apply",
                "--plan",
                "p.json",
                "--projects-root",
                "/repo/one",
            ],
            "--projects-root",
        )

    def test_cross_phase_options_are_rejected(self) -> None:
        self.assert_parse_error(
            [
                "recovery",
                "--phase",
                "apply",
                "--plan",
                "p.json",
                "--manifest",
                "m.json",
            ],
            "--manifest",
        )
        self.assert_parse_error(
            [
                "recovery",
                "--phase",
                "plan",
                "--manifest",
                "m.json",
                "--recovery-receipt",
                "r.json",
            ],
            "--recovery-receipt",
        )
        self.assert_parse_error(
            [
                "recovery",
                "--phase",
                "plan",
                "--manifest",
                "m.json",
                "--confirm-recovery",
                "plan-id-value",
            ],
            "--confirm-recovery",
        )

    def test_only_plan_and_apply_phases_exist(self) -> None:
        self.assert_parse_error(
            ["recovery", "--phase", "verify", "--manifest", "m.json"], "verify"
        )
        self.assert_parse_error(
            ["recovery", "--phase", "cleanup", "--plan", "p.json"], "cleanup"
        )


class RejectionTests(ParseErrorAssertions):
    def test_removed_trellis_flags_are_rejected(self) -> None:
        self.assert_parse_error(["check", "--trellis-user", "dev"], "--trellis-user")
        self.assert_parse_error(
            ["init", "--trellis-platform", "codex"], "--trellis-platform"
        )
        self.assert_parse_error(["reset", "--skip-trellis-init"], "--skip-trellis-init")
        self.assert_parse_error(
            ["plan", "--skip-trellis-bootstrap"], "--skip-trellis-bootstrap"
        )

    def test_unknown_modes_are_rejected(self) -> None:
        self.assert_parse_error(["migrate"], "migrate")
        self.assert_parse_error(["che"], "che")
        self.assert_parse_error([], "mode")

    def test_abbreviation_aliases_are_rejected(self) -> None:
        self.assert_parse_error(["check-projects", "--proj", "/repo/one"], "--proj")
        self.assert_parse_error(["check", "--deve", "dev01"], "--deve")
        self.assert_parse_error(
            [
                "migration",
                "--pha",
                "apply",
                "--manifest",
                "m.json",
            ],
            "--pha",
        )

    def test_repeated_single_value_options_are_rejected(self) -> None:
        self.assert_parse_error(
            [
                "migration",
                "--phase",
                "apply",
                "--manifest",
                "first.json",
                "--manifest",
                "second.json",
            ],
        )
        self.assert_parse_error(
            [
                "migration",
                "--phase",
                "apply",
                "--manifest",
                "m.json",
                "--apply-receipt",
                "a.json",
                "--apply-receipt",
                "b.json",
            ],
        )
        self.assert_parse_error(["check", "--developer", "dev", "--developer", "dev"])
        self.assert_parse_error(
            [
                "check-projects",
                "--projects-root",
                "/repo/one",
                "--projects-root",
                "/repo/two",
            ],
        )
        self.assert_parse_error(["migration", "--phase", "plan", "--phase", "apply"])


class PurityTests(unittest.TestCase):
    def test_parse_never_touches_referenced_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sbtd-args-purity-") as temp:
            temp_root = Path(temp)
            manifest = temp_root / "manifest.json"
            args = parse_workflow_args(
                [
                    "migration",
                    "--phase",
                    "cleanup",
                    "--manifest",
                    str(manifest),
                    "--apply-receipt",
                    str(temp_root / "apply.json"),
                    "--deployment-evidence",
                    str(temp_root / "deploy.json"),
                    "--verification",
                    str(temp_root / "verify.json"),
                ]
            )
            self.assertEqual(args.manifest, str(manifest))
            self.assertFalse(manifest.exists())
            self.assertEqual(list(temp_root.iterdir()), [])

    def test_parse_errors_also_leave_paths_untouched(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sbtd-args-purity-") as temp:
            temp_root = Path(temp)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit):
                parse_workflow_args(
                    [
                        "init",
                        "--migration-manifest",
                        str(temp_root / "manifest.json"),
                    ]
                )
            self.assertEqual(list(temp_root.iterdir()), [])

    def test_module_imports_and_parses_without_jsonschema(self) -> None:
        script = (
            "import importlib.util\n"
            "assert importlib.util.find_spec('jsonschema') is None\n"
            f"spec = importlib.util.spec_from_file_location('onboard_arguments', {str(ARGUMENTS)!r})\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            "args = module.parse_workflow_args(['migration', '--phase', 'verify', '--manifest', 'm', '--apply-receipt', 'a', '--deployment-evidence', 'd'])\n"
            "assert args.manifest == 'm'\n"
        )
        result = subprocess.run(
            (sys.executable, "-I", "-S", "-B", "-c", script),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
