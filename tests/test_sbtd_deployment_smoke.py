"""Consumer tests for the trusted check-projects smoke. No Graft."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from onboard import native_git_argv
from onboard_contracts import ContractError, canonical_json_bytes
from sbtd_deployment_smoke import run_project_smoke
from sbtd_migration import apply_migration, runtime_versions
from sbtd_migration_files import snapshot
from sbtd_migration_plan import plan_migration
from sbtd_migration_verify import (
    ONBOARD_CLI_BOOTSTRAP,
    ONBOARD_CLI_SMOKE_BOUND_SCHEMA,
    ONBOARD_CLI_SMOKE_SCHEMA,
    onboard_cli_smoke_command,
)
from tests.test_sbtd_migration_apply import legacy_project


def _private(path: Path) -> Path:
    path.mkdir(mode=0o700)
    return path


class DeploymentSmokeTests(unittest.TestCase):
    def test_isolated_check_projects_seals_closed_projection(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw).resolve()
            project = base / "project"
            evidence = _private(base / "evidence")
            project.mkdir()
            marker = project / "marker.txt"
            marker.write_bytes(b"keep-me\n")
            leak = "LEAK-TOKEN-9f3a"
            (project / "package.json").write_text(
                json.dumps({"scripts": {"secret-smoke-cmd": f"echo {leak}"}}),
                encoding="utf-8",
            )
            unrelated = base / "outside-secret.txt"
            unrelated.write_text("SYMLINK-SECRET-not-inspected\n", encoding="utf-8")
            link = project / "unrelated.link"
            link.symlink_to(unrelated)
            before = marker.read_bytes()
            refs = run_project_smoke(project, evidence)
            self.assertEqual(len(refs), 2)
            report, summary = refs
            for ref in refs:
                path = Path(ref["path"])
                self.assertTrue(path.is_relative_to(evidence))
                self.assertEqual(ref["state"]["type"], "file")
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    ref["state"]["checksum"],
                )
            self.assertEqual(summary["path"], str(Path(report["path"]).with_suffix(".md")))
            report_bytes = Path(report["path"]).read_bytes()
            summary_bytes = Path(summary["path"]).read_bytes()
            for secret in (leak.encode(), b"secret-smoke-cmd", b"SYMLINK-SECRET-not-inspected"):
                self.assertNotIn(secret, report_bytes)
                self.assertNotIn(secret, summary_bytes)
            document = json.loads(report_bytes)
            self.assertEqual(set(document), {
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
            })
            self.assertNotIn("stdout", document)
            self.assertNotIn("stdoutSha256", document)
            self.assertEqual(document["schema"], ONBOARD_CLI_SMOKE_SCHEMA)
            self.assertNotIn("schemaVersion", document)
            self.assertEqual(document["projectRoot"], str(project))
            self.assertEqual(document["sourceRef"], "non-git")
            self.assertIsNone(document["sourceCommit"])
            self.assertEqual(document["status"], "passed")
            self.assertEqual(document["exitCode"], 0)
            self.assertEqual(document["mockStrategy"], "none")
            self.assertEqual(document["onboardVersion"], runtime_versions()["onboard"])
            command = document["command"]
            self.assertEqual(command, onboard_cli_smoke_command(project))
            projection = document["projection"]
            self.assertEqual(projection, {
                "mode": "check-projects",
                "projects": [{"projectRoot": str(project), "sbtd": {"status": "success"}}],
            })
            self.assertEqual(
                document["projectionSha256"],
                hashlib.sha256(canonical_json_bytes(projection)).hexdigest(),
            )
            self.assertEqual(marker.read_bytes(), before)
            self.assertTrue(link.is_symlink())
            self.assertEqual(unrelated.read_text(encoding="utf-8"), "SYMLINK-SECRET-not-inspected\n")
            self.assertFalse(any(path.suffix == ".err" for path in evidence.iterdir()))
            self.assertEqual(sorted(path.suffix for path in evidence.iterdir()), [".json", ".md"])

    def test_native_git_ignores_checkout_path_and_cli_uses_private_scratch(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw).resolve()
            project = base / "project"
            project.mkdir()
            evidence = _private(base / "evidence")
            git = Path(native_git_argv(project)[0])
            project_bin = project / "bin"
            project_bin.mkdir()
            path = os.pathsep.join((str(project_bin), "bin", "", str(git.parent)))
            real_run = subprocess.run
            git_calls = []
            scratch_dirs = []

            def observe_call(argv, **kwargs):
                if argv[4:5] == [ONBOARD_CLI_BOOTSTRAP]:
                    scratch = Path(kwargs["env"]["HOME"])
                    scratch_dirs.append(scratch)
                    self.assertEqual(scratch.parent, evidence)
                    self.assertEqual(kwargs["cwd"], scratch)
                    self.assertEqual(kwargs["env"]["PATH"], str(git.parent))
                    for key in ("TMPDIR", "TMP", "TEMP"):
                        self.assertEqual(kwargs["env"][key], str(scratch))
                else:
                    git_calls.append(Path(argv[0]))
                    self.assertEqual(Path(argv[0]), git)
                    self.assertEqual(kwargs["cwd"], git.parent)
                    self.assertFalse(kwargs.get("shell", False))
                return real_run(argv, **kwargs)

            with (
                mock.patch.dict(os.environ, {"PATH": path}),
                mock.patch.object(subprocess, "run", side_effect=observe_call),
            ):
                reports = run_project_smoke(project, evidence)
            self.assertEqual(len(reports), 2)
            self.assertGreaterEqual(len(git_calls), 2)
            self.assertEqual(len(scratch_dirs), 1)
            self.assertFalse(scratch_dirs[0].exists())

    def test_ref_or_head_change_after_real_check_prevents_publication(self):
        for change in ("ref", "head"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as raw:
                base = Path(raw).resolve()
                project = base / "project"
                project.mkdir()
                evidence = _private(base / "evidence")
                real_run = subprocess.run

                def git(*args):
                    return real_run(
                        native_git_argv(project, *args), check=True, capture_output=True,
                    )

                def commit(message):
                    git(
                        "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                        "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", message,
                    )

                git("init", "-b", "main")
                commit("before check")
                checked = []

                def change_after_check(argv, **kwargs):
                    result = real_run(argv, **kwargs)
                    if argv[4:5] == [ONBOARD_CLI_BOOTSTRAP]:
                        self.assertEqual(result.returncode, 0)
                        checked.append(True)
                        if change == "ref":
                            git("symbolic-ref", "HEAD", "refs/heads/other")
                            git("update-ref", "HEAD", "refs/heads/main")
                        else:
                            commit("after check")
                    return result

                with (
                    mock.patch.object(subprocess, "run", side_effect=change_after_check),
                    self.assertRaises(ContractError) as failure,
                ):
                    run_project_smoke(project, evidence)
                self.assertEqual(failure.exception.code, "revision-conflict")
                self.assertEqual(checked, [True])
                self.assertEqual(list(evidence.iterdir()), [])

    def test_unsafe_root_and_unsuccessful_child_write_nothing(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw).resolve()
            evidence = _private(base / "evidence")
            target = base / "real"
            target.mkdir()
            link = base / "link"
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(ContractError):
                run_project_smoke(link, evidence)
            self.assertFalse(any(evidence.iterdir()))
            blocked = base / "blocked"
            blocked.mkdir()
            (blocked / ".trellis").mkdir()
            with self.assertRaises(ContractError) as raised:
                run_project_smoke(blocked, evidence)
            self.assertNotEqual(raised.exception.code, "report-acceptance")
            self.assertNotEqual(raised.exception.exit_code, 0)
            self.assertFalse(any(path.suffix == ".json" for path in evidence.iterdir()))
            self.assertFalse((blocked / "AGENTS.md").exists())


def _migration_arguments(manifest_path: Path, apply_path: Path) -> list[str]:
    return [
        "--migration-manifest",
        str(manifest_path),
        "--migration-apply-receipt",
        str(apply_path),
    ]


def _run_cli(root: Path, home: Path, extra: list[str] | None = None):
    environment = {
        key: os.environ[key]
        for key in (
            "PATH",
            "LANG",
            "LC_ALL",
            "LC_CTYPE",
            "SYSTEMROOT",
            "WINDIR",
            "TMPDIR",
            "TMP",
            "TEMP",
        )
        if key in os.environ
    }
    environment.update(
        HOME=str(home),
        USERPROFILE=str(home),
        XDG_CONFIG_HOME=str(home / "config"),
        XDG_CACHE_HOME=str(home / "cache"),
        XDG_DATA_HOME=str(home / "data"),
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONNOUSERSITE="1",
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
    )
    return subprocess.run(
        onboard_cli_smoke_command(root) + (extra or []),
        cwd=home,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=120,
        check=False,
    )


def _applied_retained_project(base: Path):
    root = legacy_project(base, "project")
    home = _private(base / "home")
    vault = _private(base / "vault")
    evidence = _private(base / "evidence")
    environment = {
        "HOME": str(home),
        "USERPROFILE": str(home),
        "CODEX_HOME": str(home / ".codex"),
        "AGENT_SKILLS_DIR": str(home / ".agent/skills"),
    }
    with mock.patch.dict(os.environ, environment):
        manifest = plan_migration(
            [root], vault, "fixture-custodian", None, tool_versions=runtime_versions(),
            deployment_mode="init", deployment_platform="codex",
        )
        manifest_path = evidence / "manifest.json"
        manifest_path.write_bytes(canonical_json_bytes(manifest))
        applied, code = apply_migration(
            manifest_path, confirmed=True, no_routing_approvals=True
        )
    if code != 0 or applied.get("status") != "applied":
        raise AssertionError(applied)
    receipt = applied["migration"]["apply_receipt"]
    apply_path = evidence / f"apply-{receipt['apply_id']}.json"
    if not apply_path.is_file() or json.loads(apply_path.read_text()) != receipt:
        raise AssertionError("the real apply receipt was not saved")
    return root, evidence, manifest_path, apply_path


class BoundMigrationSmokeTests(unittest.TestCase):
    def test_non_migration_retained_tree_is_real_cli_exit_two(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = base / "project"
            (root / ".trellis").mkdir(parents=True)
            home = _private(base / "home")
            before = snapshot(root)
            completed = _run_cli(root, home)
            self.assertEqual(completed.returncode, 2, completed)
            document = json.loads(completed.stdout)
            self.assertEqual(document["mode"], "check-projects")
            self.assertEqual(len(document["projects"]), 1)
            project = document["projects"][0]
            self.assertEqual(project["projectRoot"], str(root))
            self.assertEqual(project["sbtd"]["status"], "needs-user")
            self.assertTrue(project["sbtd"]["legacyPresent"])
            self.assertEqual(snapshot(root), before)

    def test_real_bound_apply_succeeds_without_project_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root, evidence, manifest_path, apply_path = _applied_retained_project(base)
            cli_home = _private(base / "cli-home")
            arguments = _migration_arguments(manifest_path, apply_path)
            retained_before = snapshot(root / ".trellis")
            before = snapshot(root)
            manifest_before = manifest_path.read_bytes()
            apply_before = apply_path.read_bytes()

            completed = _run_cli(root, cli_home, arguments)
            self.assertEqual(completed.returncode, 0, completed)
            checked = json.loads(completed.stdout)["projects"][0]
            self.assertEqual(checked["projectRoot"], str(root))
            self.assertEqual(checked["sbtd"]["status"], "success")
            self.assertTrue(checked["sbtd"]["legacyPresent"])
            self.assertEqual(snapshot(root), before)

            retained = str(root / ".trellis")
            with (
                mock.patch.dict(os.environ, {key: retained for key in ("TMPDIR", "TMP", "TEMP")}),
                mock.patch.object(tempfile, "tempdir", retained),
            ):
                refs = run_project_smoke(
                    root, evidence, context_paths=(manifest_path, apply_path)
                )
            self.assertEqual(len(refs), 2)
            document = json.loads(Path(refs[0]["path"]).read_bytes())
            self.assertEqual(document["schema"], ONBOARD_CLI_SMOKE_BOUND_SCHEMA)
            self.assertEqual(set(document["producer"]), {"imageSha256", "invocationSha256"})
            self.assertEqual(document["projectRoot"], str(root))
            self.assertEqual(document["status"], "passed")
            self.assertEqual(document["exitCode"], 0)
            self.assertEqual(
                document["command"], onboard_cli_smoke_command(root) + arguments
            )
            self.assertEqual(
                document["projection"],
                {
                    "mode": "check-projects",
                    "projects": [
                        {"projectRoot": str(root), "sbtd": {"status": "success"}}
                    ],
                },
            )
            self.assertTrue((root / ".trellis").is_dir())
            self.assertEqual(snapshot(root / ".trellis"), retained_before)
            self.assertEqual(snapshot(root), before)
            self.assertEqual(manifest_path.read_bytes(), manifest_before)
            self.assertEqual(apply_path.read_bytes(), apply_before)

    def _assert_bound_smoke_blocked(
        self,
        root: Path,
        evidence: Path,
        manifest_path: Path,
        apply_path: Path,
    ):
        retained_before = snapshot(root / ".trellis")
        with self.assertRaises(ContractError) as raised:
            run_project_smoke(
                root, evidence, context_paths=(manifest_path, apply_path)
            )
        self.assertNotEqual(raised.exception.exit_code, 0)
        self.assertEqual(snapshot(root / ".trellis"), retained_before)
        self.assertEqual(list(evidence.glob("onboard-cli-smoke-*")), [])

    def test_drift_foreign_root_and_bad_receipts_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root, evidence, manifest_path, apply_path = _applied_retained_project(base)

            foreign = base / "foreign"
            (foreign / ".trellis").mkdir(parents=True)
            self._assert_bound_smoke_blocked(
                foreign, evidence, manifest_path, apply_path
            )

            bad_path = evidence / "bad-apply.json"
            bad_path.write_bytes(b"{")
            self._assert_bound_smoke_blocked(root, evidence, manifest_path, bad_path)

            incomplete_path = evidence / "incomplete-apply.json"
            incomplete_path.write_bytes(
                canonical_json_bytes(
                    {"apply_id": json.loads(apply_path.read_text())["apply_id"]}
                )
            )
            self._assert_bound_smoke_blocked(
                root, evidence, manifest_path, incomplete_path
            )

            linked_path = evidence / "linked-apply.json"
            linked_path.symlink_to(apply_path)
            self._assert_bound_smoke_blocked(root, evidence, manifest_path, linked_path)
            self.assertTrue(linked_path.is_symlink())

            journal = root / ".trellis/workspace/dev01/journal-1.md"
            journal.write_bytes(journal.read_bytes() + b"unrecorded drift\n")
            self._assert_bound_smoke_blocked(root, evidence, manifest_path, apply_path)

    def test_links_and_active_state_errors_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root, evidence, manifest_path, apply_path = _applied_retained_project(base)
            pointer = root / ".sbtd/active-task.json"
            self.assertFalse(pointer.exists())

            pointer.write_bytes(b"{")
            self._assert_bound_smoke_blocked(root, evidence, manifest_path, apply_path)
            self.assertEqual(pointer.read_bytes(), b"{")

            pointer.unlink()
            outside = base / "outside-active.json"
            outside.write_bytes(b"{}\n")
            pointer.symlink_to(outside)
            self._assert_bound_smoke_blocked(root, evidence, manifest_path, apply_path)
            self.assertTrue(pointer.is_symlink())
            self.assertEqual(outside.read_bytes(), b"{}\n")


if __name__ == "__main__":
    unittest.main()
