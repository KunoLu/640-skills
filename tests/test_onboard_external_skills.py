from __future__ import annotations

import argparse
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import cast
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
ONBOARD = ROOT / "sbtd-workflow-onboard" / "scripts" / "onboard.py"
sys.path.insert(0, str(ONBOARD.parent))


class ExternalSkillInstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sbtd-external-skills-test-")
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.skills_dir = self.root / "skills"
        self.fake_repo = self.root / "upstream"
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.git_log = self.root / "git.log"
        self.env = os.environ.copy()
        self.env["HOME"] = str(self.home)
        self.env["FAKE_EXTERNAL_REPO"] = str(self.fake_repo)
        self.env["FAKE_GIT_LOG"] = str(self.git_log)
        self.env["PATH"] = os.pathsep.join((str(self.bin_dir), "/usr/bin", "/bin"))
        self.module_counter = 0

    def write_executable(self, name: str, body: str) -> Path:
        target = self.bin_dir / name
        target.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
        target.chmod(target.stat().st_mode | stat.S_IXUSR)
        return target

    def write_fake_git(self, *, clone_succeeds: bool) -> None:
        status = "0" if clone_succeeds else "1"
        self.write_executable(
            "git",
            f"""
            #!/bin/sh
            printf '%s\n' "$*" >> "$FAKE_GIT_LOG"
            if [ "$1" = "clone" ]; then
              destination=""
              for argument in "$@"; do destination="$argument"; done
              if [ "{status}" -ne 0 ]; then
                printf 'simulated clone failure\n' >&2
                exit {status}
              fi
              mkdir -p "$destination"
              cp -R "$FAKE_EXTERNAL_REPO"/. "$destination"/
              exit 0
            fi
            if [ "$1" = "-C" ] && [ "$3" = "rev-parse" ]; then
              printf '1111111111111111111111111111111111111111\n'
              exit 0
            fi
            exit 0
            """,
        )

    def write_upstream_skill(self, name: str, marker: str) -> None:
        target = self.fake_repo / "skills" / "engineering" / name
        target.mkdir(parents=True, exist_ok=True)
        (target / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: fixture\n---\n\n{marker}\n",
            encoding="utf-8",
        )

    def write_existing_skill(self, name: str, marker: str) -> None:
        target = self.skills_dir / name
        target.mkdir(parents=True, exist_ok=True)
        (target / "SKILL.md").write_text(marker, encoding="utf-8")

    def write_valid_skill(self, root: Path, name: str, marker: str = "fixture") -> Path:
        root.mkdir(parents=True, exist_ok=True)
        (root / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: fixture\n---\n\n{marker}\n",
            encoding="utf-8",
        )
        return root

    def load_onboard_module(self):
        self.module_counter += 1
        module_name = f"onboard_external_test_{id(self)}_{self.module_counter}"
        spec = importlib.util.spec_from_file_location(module_name, ONBOARD)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load onboard module from {ONBOARD}")
        loader = cast(importlib.machinery.SourceFileLoader, spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        self.addCleanup(sys.modules.pop, module_name, None)
        loader.exec_module(module)
        return module

    def run_onboard(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            (sys.executable, str(ONBOARD), *args),
            check=False,
            capture_output=True,
            text=True,
            env=self.env,
            timeout=30,
        )

    def install(self, skills: str, source: str) -> subprocess.CompletedProcess[str]:
        return self.run_onboard(
            "install-external-skills",
            "--skills",
            skills,
            "--source",
            source,
            "--global-skills-dir",
            str(self.skills_dir),
            "--yes",
            "--json",
        )

    def test_upstream_uses_repository_when_the_contract_is_valid(self) -> None:
        self.write_fake_git(clone_succeeds=True)
        self.write_upstream_skill("diagnosing-bugs", "upstream marker")
        original = b"Repository license from this acquired revision.\n"
        (self.fake_repo / "LICENSE").write_bytes(original)

        completed = self.install("diagnosing-bugs", "upstream")

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout)
        result = next(
            item for item in payload["results"] if item.get("name") == "diagnosing-bugs"
        )
        self.assertEqual(result["sourceUsed"], "upstream")
        self.assertEqual(
            result["sourceRevision"], "1111111111111111111111111111111111111111"
        )
        self.assertIn(
            "upstream marker",
            (self.skills_dir / "diagnosing-bugs" / "SKILL.md").read_text(),
        )
        self.assertEqual(
            (self.skills_dir / "diagnosing-bugs/SBTD-NOTICES/mattpocock-skills-LICENSE").read_bytes(),
            original,
        )

    def test_auto_uses_vendored_stable_without_accessing_upstream(self) -> None:
        self.write_fake_git(clone_succeeds=True)
        self.write_upstream_skill("diagnosing-bugs", "upstream marker")

        completed = self.install("diagnosing-bugs", "auto")

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout)
        result = next(
            item for item in payload["results"] if item.get("name") == "diagnosing-bugs"
        )
        self.assertEqual(result["sourceUsed"], "stable")
        self.assertIsNone(result["fallbackReason"])
        self.assertTrue(result["stableSet"])
        self.assertFalse(self.git_log.exists())
        self.assertNotIn(
            "upstream marker",
            (self.skills_dir / "diagnosing-bugs" / "SKILL.md").read_text(),
        )

    def test_standalone_notices_survive_reinstall_and_stay_scoped(self) -> None:
        package = ONBOARD.parents[1] / "assets/external-skills"
        for name, expected in (
            ("impeccable", ("stable/licenses/impeccable-LICENSE", "stable/licenses/impeccable-NOTICE.md",
                            "notices/platform-design-skills-LICENSE")),
            ("ui-ux-pro-max", ("stable/licenses/ui-ux-pro-max-skill-LICENSE",
                               "notices/phosphor-core-NOTICE", "notices/phosphor-core-LICENSE")),
        ):
            target = self.skills_dir / name / "SBTD-NOTICES"
            for attempt in ("install", "reinstall"):
                with self.subTest(skill=name, attempt=attempt):
                    result = self.install(name, "stable")
                    self.assertEqual(result.returncode, 0, result.stdout)
                    self.assertEqual(
                        {p.name: p.read_bytes() for p in target.iterdir()},
                        {Path(p).name: (package / p).read_bytes() for p in expected},
                    )

    @unittest.skipUnless(os.name == "posix", "POSIX directory mode contract")
    def test_readonly_stage_preserves_mode_on_success_and_failure(self) -> None:
        from sbtd_external_notices import copy_notices

        source = self.root / "license"
        source.write_bytes(b"upstream terms\n")
        for succeeds in (False, True):
            stage = self.root / str(succeeds)
            stage.mkdir(mode=0o700)
            stage.chmod(0o555)
            self.addCleanup(stage.chmod, 0o700)
            overlay = {"SBTD-NOTICES/LICENSE": source if succeeds else self.root / "absent"}
            if succeeds:
                copy_notices(stage, overlay)
                self.assertEqual((stage / "SBTD-NOTICES/LICENSE").read_bytes(), source.read_bytes())
            else:
                with self.assertRaises(FileNotFoundError):
                    copy_notices(stage, overlay)
            self.assertEqual(stat.S_IMODE(stage.stat().st_mode), 0o555)

    @unittest.skipUnless(sys.platform == "darwin", "macOS read-only directory reparenting")
    def test_readonly_existing_skill_reinstalls_without_losing_notices(self) -> None:
        target = self.skills_dir / "impeccable"
        for attempt in range(2):
            if attempt:
                (target / "SKILL.md").write_bytes(b"old payload")
                target.chmod(0o555)
            result = self.install("impeccable", "stable")
            self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotEqual((target / "SKILL.md").read_bytes(), b"old payload")
        self.assertTrue((target / "SBTD-NOTICES/platform-design-skills-LICENSE").is_file())
        self.assertFalse(list(self.skills_dir.glob(".sbtd-external-*")))

    def test_upstream_supplement_requires_reviewed_content_and_attribution(self) -> None:
        stable = ONBOARD.parents[1] / "assets/external-skills/stable"
        self.write_fake_git(clone_succeeds=True)
        skill = self.fake_repo / "plugin/skills/impeccable"
        shutil.copytree(stable / "skills/impeccable", skill)
        for name in ("LICENSE", "NOTICE.md"):
            shutil.copyfile(stable / f"licenses/impeccable-{name}", self.fake_repo / name)
        # A different revision with unrelated changes can still use the same evidence.
        (skill / "other.md").write_text("unrelated update", encoding="utf-8")
        result = self.install("impeccable", "upstream")
        self.assertEqual(result.returncode, 0, result.stdout)
        target = self.skills_dir / "impeccable"
        (target / "local-marker").write_bytes(b"unchanged")
        for changed in (skill / "reference/ios.md", skill / "reference/android.md", self.fake_repo / "NOTICE.md"):
            original = changed.read_bytes()
            with self.subTest(changed=changed.name):
                if changed.name == "ios.md":
                    changed.rename(changed.with_suffix(".moved"))
                else:
                    changed.write_bytes(bytes([original[0] ^ 1]) + original[1:])
                result = self.install("impeccable", "upstream")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("attribution", result.stdout)
                self.assertEqual((target / "local-marker").read_bytes(), b"unchanged")
            changed.write_bytes(original)

    def test_stable_mode_does_not_invoke_git(self) -> None:
        self.write_fake_git(clone_succeeds=False)

        completed = self.install("diagnosing-bugs", "stable")

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout)
        result = next(
            item for item in payload["results"] if item.get("name") == "diagnosing-bugs"
        )
        self.assertEqual(result["sourceUsed"], "stable")
        self.assertFalse(self.git_log.exists())

    def test_strict_upstream_failure_leaves_every_existing_target_unchanged(
        self,
    ) -> None:
        self.write_fake_git(clone_succeeds=True)
        self.write_upstream_skill("diagnosing-bugs", "new diagnosing-bugs")
        self.write_existing_skill("diagnosing-bugs", "old diagnosing-bugs")
        self.write_existing_skill("tdd", "old tdd")

        completed = self.install("diagnosing-bugs,tdd", "upstream")

        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(
            (self.skills_dir / "diagnosing-bugs" / "SKILL.md").read_text(),
            "old diagnosing-bugs",
        )
        self.assertEqual((self.skills_dir / "tdd" / "SKILL.md").read_text(), "old tdd")

    def test_auto_uses_one_stable_set_for_the_whole_repository_group(self) -> None:
        self.write_fake_git(clone_succeeds=True)

        completed = self.install("diagnosing-bugs,tdd", "auto")

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout)
        installed = {
            item["name"]: item
            for item in payload["results"]
            if item.get("name") in {"diagnosing-bugs", "tdd"}
        }
        self.assertEqual(
            {item["sourceUsed"] for item in installed.values()}, {"stable"}
        )
        self.assertEqual(
            len({item["stableSet"] for item in installed.values()}), 1
        )
        self.assertFalse(self.git_log.exists())

    def test_stable_promotion_requires_explicit_confirmation(self) -> None:
        completed = self.run_onboard(
            "promote-external-skills-stable",
            "--repository",
            "mattpocock-skills",
            "--revision",
            "2" * 40,
            "--stable-set",
            "2099-01-01.1",
            "--json",
        )

        self.assertEqual(completed.returncode, 2)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["repository"], "mattpocock-skills")
        self.assertEqual(payload["revision"], "2" * 40)

    def test_complete_vendored_stable_set_installs_without_network(self) -> None:
        self.write_fake_git(clone_succeeds=False)

        completed = self.run_onboard(
            "install-external-skills",
            "--all",
            "--source",
            "stable",
            "--global-skills-dir",
            str(self.skills_dir),
            "--yes",
            "--json",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout)
        installed = [
            item for item in payload["results"] if item.get("phase") == "commit"
        ]
        catalog = json.loads(
            (ROOT / "sbtd-workflow-onboard" / "catalog.json").read_text(
                encoding="utf-8"
            )
        )
        expected_count = sum(
            entry["kind"] == "external-skill" for entry in catalog["entries"]
        )
        self.assertEqual(len(installed), expected_count)
        self.assertEqual({item["sourceUsed"] for item in installed}, {"stable"})
        self.assertTrue(
            all(
                (self.skills_dir / item["name"] / "SKILL.md").is_file()
                for item in installed
            )
        )
        self.assertFalse(self.git_log.exists())

    def test_stable_reset_install_replaces_retired_writing_skill(self) -> None:
        self.write_valid_skill(
            self.skills_dir / "writing-great-skills",
            "writing-great-skills",
            "retired canonical",
        )
        self.write_valid_skill(
            self.skills_dir / "write-a-skill",
            "write-a-skill",
            "older legacy alias",
        )

        completed = self.run_onboard(
            "install-external-skills",
            "--all",
            "--source",
            "stable",
            "--global-skills-dir",
            str(self.skills_dir),
            "--yes",
            "--json",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout)
        self.assertTrue(
            (self.skills_dir / "writing-for-agents" / "SKILL.md").is_file()
        )
        self.assertFalse((self.skills_dir / "writing-great-skills").exists())
        self.assertFalse((self.skills_dir / "write-a-skill").exists())
        self.assertTrue(
            any(
                item.get("name") == "writing-great-skills"
                and item.get("replacement") == "writing-for-agents"
                and item.get("status") == "removed"
                for item in payload["results"]
            )
        )

    def test_migrate_external_skills_installs_replacements_for_all_legacy_aliases(
        self,
    ) -> None:
        legacy_names = (
            "diagnose",
            "write-a-skill",
            "writing-great-skills",
            "to-prd",
            "to-issues",
            "zoom-out",
        )
        for name in legacy_names:
            self.write_valid_skill(self.skills_dir / name, name, "legacy")

        completed = self.run_onboard(
            "migrate-external-skills",
            "--source",
            "stable",
            "--global-skills-dir",
            str(self.skills_dir),
            "--yes",
            "--json",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "migrated")
        self.assertEqual(
            {
                item["name"]
                for item in payload["results"]
                if item.get("status") == "removed"
            },
            set(legacy_names),
        )
        for name in legacy_names:
            self.assertFalse((self.skills_dir / name).exists(), name)
        for name in (
            "diagnosing-bugs",
            "writing-for-agents",
            "to-spec",
            "to-tickets",
        ):
            self.assertTrue((self.skills_dir / name / "SKILL.md").is_file(), name)

    def test_removed_zoom_out_recommendation_uses_current_route(self) -> None:
        completed = self.install("zoom-out", "stable")

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Removed external skill", completed.stderr)
        self.assertIn("codebase-design", completed.stderr)
        self.assertNotIn("GitNexus", completed.stderr)

    def test_migrate_external_skills_aborts_before_installing_on_identity_conflict(
        self,
    ) -> None:
        self.write_valid_skill(self.skills_dir / "diagnose", "diagnose", "legacy")
        self.write_valid_skill(
            self.skills_dir / "to-prd",
            "user-owned-to-prd",
            "must not be replaced",
        )

        completed = self.run_onboard(
            "migrate-external-skills",
            "--source",
            "stable",
            "--global-skills-dir",
            str(self.skills_dir),
            "--yes",
            "--json",
        )

        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "failed")
        self.assertTrue((self.skills_dir / "diagnose").exists())
        self.assertTrue((self.skills_dir / "to-prd").exists())
        self.assertFalse((self.skills_dir / "diagnosing-bugs").exists())
        self.assertTrue(
            any(
                item.get("name") == "to-prd"
                and item.get("status") == "failed"
                and item.get("phase") == "preflight-legacy-identity"
                for item in payload["results"]
            )
        )

    def test_migrate_external_skills_requires_confirmation_before_writes(
        self,
    ) -> None:
        self.write_valid_skill(self.skills_dir / "to-prd", "to-prd", "legacy")

        completed = self.run_onboard(
            "migrate-external-skills",
            "--source",
            "stable",
            "--global-skills-dir",
            str(self.skills_dir),
            "--json",
        )

        self.assertEqual(completed.returncode, 2, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "needs-confirmation")
        self.assertTrue((self.skills_dir / "to-prd").exists())
        self.assertFalse((self.skills_dir / "to-spec").exists())

    def test_stable_install_preserves_identity_conflicting_legacy_skill(self) -> None:
        self.write_valid_skill(
            self.skills_dir / "writing-great-skills",
            "user-owned-writing-skill",
            "must not be deleted",
        )

        completed = self.run_onboard(
            "install-external-skills",
            "--all",
            "--source",
            "stable",
            "--global-skills-dir",
            str(self.skills_dir),
            "--yes",
            "--json",
        )

        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertFalse((self.skills_dir / "writing-for-agents").exists())
        self.assertTrue((self.skills_dir / "writing-great-skills").exists())
        self.assertTrue(
            any(
                item.get("name") == "writing-great-skills"
                and item.get("status") == "failed"
                and item.get("phase") == "preflight-legacy-identity"
                for item in payload["results"]
            )
        )
        self.assertEqual(list(self.skills_dir.glob(".sbtd-external-staging-*")), [])

    def test_reset_migration_removes_retired_writing_skill_when_replacement_exists(
        self,
    ) -> None:
        onboard = self.load_onboard_module()
        self.write_valid_skill(
            self.skills_dir / "writing-for-agents",
            "writing-for-agents",
            "replacement",
        )
        self.write_valid_skill(
            self.skills_dir / "writing-great-skills",
            "writing-great-skills",
            "retired canonical",
        )
        self.write_valid_skill(
            self.skills_dir / "write-a-skill",
            "write-a-skill",
            "older legacy alias",
        )

        plan = onboard.build_external_migration_plan(
            argparse.Namespace(global_skills_dir=str(self.skills_dir))
        )
        results = onboard.run_external_migration(plan)

        self.assertEqual(plan["status"], "planned")
        self.assertEqual(plan["requiredCanonical"], ["writing-for-agents"])
        self.assertFalse((self.skills_dir / "writing-great-skills").exists())
        self.assertFalse((self.skills_dir / "write-a-skill").exists())
        self.assertEqual(
            {
                item["name"]
                for item in results
                if item.get("status") == "removed"
            },
            {"writing-great-skills", "write-a-skill"},
        )

    def test_reset_migration_preserves_identity_conflicting_legacy_skill(
        self,
    ) -> None:
        onboard = self.load_onboard_module()
        self.write_valid_skill(
            self.skills_dir / "writing-for-agents",
            "writing-for-agents",
            "replacement",
        )
        self.write_valid_skill(
            self.skills_dir / "writing-great-skills",
            "user-owned-writing-skill",
            "must not be deleted",
        )

        plan = onboard.build_external_migration_plan(
            argparse.Namespace(global_skills_dir=str(self.skills_dir))
        )
        results = onboard.run_external_migration(plan)

        self.assertTrue((self.skills_dir / "writing-great-skills").exists())
        self.assertTrue(
            any(
                item.get("name") == "writing-great-skills"
                and item.get("status") == "failed"
                and item.get("phase") == "preflight-legacy-identity"
                for item in results
            )
        )

    def test_reset_migration_rejects_dangling_legacy_symlink(self) -> None:
        onboard = self.load_onboard_module()
        self.write_valid_skill(
            self.skills_dir / "writing-for-agents",
            "writing-for-agents",
            "replacement",
        )
        legacy = self.skills_dir / "writing-great-skills"
        legacy.symlink_to(self.root / "missing-user-owned-skill")

        plan = onboard.build_external_migration_plan(
            argparse.Namespace(global_skills_dir=str(self.skills_dir))
        )
        results = onboard.run_external_migration(plan)

        self.assertEqual(plan["status"], "planned")
        self.assertTrue(legacy.is_symlink())
        self.assertTrue(
            any(
                item.get("name") == "writing-great-skills"
                and item.get("status") == "failed"
                and item.get("phase") == "preflight-legacy-identity"
                for item in results
            )
        )

    def test_commit_reports_cleanup_residue_without_undoing_new_install(self):
        onboard = self.load_onboard_module()
        real_remove = shutil.rmtree
        for phase in ("staging", "rollback"):
            with self.subTest(phase=phase):
                slots = self.root / phase
                self.write_valid_skill(slots / "tdd", "tdd", "previous")

                def leave(path, *args, prefix=".sbtd-external-" + phase + "-", **kwargs):
                    if Path(path).name.startswith(prefix):
                        if not kwargs.get("ignore_errors"):
                            raise PermissionError("test refused cleanup")
                        return
                    return real_remove(path, *args, **kwargs)

                with mock.patch.object(shutil, "rmtree", side_effect=leave):
                    results, tx = onboard.execute_external_skill_install(
                        argparse.Namespace(source="stable"), ["tdd"], slots
                    )
                self.assertEqual(tx["status"], "committed-cleanup-incomplete")
                self.assertFalse(tx["rolledBack"])
                self.assertEqual([str(p) for p in slots.glob(".sbtd-external-" + phase + "-*")], tx["retainedPaths"])
                self.assertTrue(any(row["status"] == "failed" and row["phase"] == "cleanup" for row in results))
                self.assertTrue((slots / "tdd/SBTD-NOTICES/mattpocock-skills-LICENSE").is_file())

    @unittest.skipUnless(os.name == "posix", "POSIX read-only source directory")
    def test_owned_readonly_source_workspace_does_not_fail_committed_install(self):
        onboard = self.load_onboard_module()
        resolve = onboard.resolve_external_install_sources
        workspaces = []

        def resolve_with_readonly_files(selected, source, workspace):
            resolved = resolve(selected, source, workspace)
            directory = workspace / "readonly"
            directory.mkdir()
            (directory / "metadata").write_bytes(b"source material")
            directory.chmod(0o555)
            workspaces.append(workspace)
            return resolved

        with mock.patch.object(onboard, "resolve_external_install_sources", side_effect=resolve_with_readonly_files):
            results, tx = onboard.execute_external_skill_install(
                argparse.Namespace(source="stable"), ["tdd"], self.skills_dir
            )
        workspace, = workspaces
        if workspace.exists():
            self.addCleanup(shutil.rmtree, workspace)
            self.addCleanup((workspace / "readonly").chmod, 0o700)
        self.assertEqual(tx["status"], "committed")
        self.assertFalse(workspace.exists())
        self.assertFalse(tx.get("retainedPaths"))
        self.assertTrue(any(item["name"] == "tdd" and item["status"] == "installed" for item in results))
        self.assertTrue((self.skills_dir / "tdd/SBTD-NOTICES/mattpocock-skills-LICENSE").is_file())

    def test_source_workspace_cleanup_keeps_completed_install_receipt(self):
        onboard = self.load_onboard_module()
        remove = shutil.rmtree
        paths = []

        def fail_workspace(path, *args, **kwargs):
            if Path(path).name.startswith("sbtd-onboard-external-sources-"):
                paths.append(str(path))
                raise PermissionError("source workspace busy")
            return remove(path, *args, **kwargs)

        with mock.patch.object(shutil, "rmtree", side_effect=fail_workspace):
            results, tx = onboard.execute_external_skill_install(
                argparse.Namespace(source="stable"), ["tdd"], self.skills_dir
            )
        self.addCleanup(remove, paths[0])
        self.assertTrue((self.skills_dir / "tdd/SBTD-NOTICES/mattpocock-skills-LICENSE").is_file())
        self.assertEqual(tx["status"], "committed-cleanup-incomplete")
        self.assertFalse(tx["rolledBack"])
        self.assertEqual(tx["retainedPaths"], paths)
        self.assertTrue(any(item["name"] == "tdd" and item["status"] == "installed" for item in results))
        self.assertTrue(any(item["phase"] == "cleanup" and item["target"] == paths[0] for item in results))

    def test_prepare_reports_primary_failure_and_retained_stage(self):
        onboard = self.load_onboard_module()
        remove = shutil.rmtree

        def refuse_stage(path, *args, **kwargs):
            if Path(path).name.startswith(".sbtd-external-staging-"):
                raise PermissionError("cannot clear test stage")
            return remove(path, *args, **kwargs)

        with (
            mock.patch.object(onboard, "copy_notices", side_effect=OSError("primary notice failure")),
            mock.patch.object(shutil, "rmtree", side_effect=refuse_stage),
        ):
            results, tx = onboard.execute_external_skill_install(
                argparse.Namespace(source="stable"), ["tdd"], self.skills_dir
            )
        self.assertFalse((self.skills_dir / "tdd").exists())
        self.assertIn("primary notice failure", results[0]["error"])
        self.assertEqual(tx["status"], "aborted-before-commit-cleanup-incomplete")
        self.assertTrue((Path(tx["retainedPaths"][0]) / "tdd/SKILL.md").is_file())

    def test_rollback_failure_retains_the_only_backup_copy(self) -> None:
        onboard = self.load_onboard_module()
        self.write_valid_skill(
            self.skills_dir / "diagnosing-bugs", "diagnosing-bugs", "old"
        )
        staging = self.root / "staging"
        self.write_valid_skill(staging / "diagnosing-bugs", "diagnosing-bugs", "new")
        resolved = {
            "diagnosing-bugs": {
                "repo": "fixture",
                "sourceUsed": "upstream",
                "sourceRevision": "1" * 40,
                "stableSet": None,
                "fallbackReason": None,
            }
        }
        real_move = onboard.rename_directory_exclusive
        move_count = 0

        def failing_move(source, destination):
            nonlocal move_count
            move_count += 1
            if move_count in {2, 3}:
                raise OSError("simulated commit/restore failure")
            return real_move(source, destination)

        with mock.patch.object(onboard, "rename_directory_exclusive", side_effect=failing_move):
            _, transaction = onboard.commit_external_skill_transaction(
                ["diagnosing-bugs"], resolved, self.skills_dir, staging
            )

        self.assertEqual(transaction["status"], "rollback-failed")
        rollback_path = Path(transaction["rollbackPath"])
        self.assertTrue((rollback_path / "diagnosing-bugs" / "SKILL.md").is_file())
        self.assertIn(
            "old", (rollback_path / "diagnosing-bugs" / "SKILL.md").read_text()
        )

    def test_init_and_reset_json_preserve_failed_rollback_recovery(self) -> None:
        for mode in ("init", "reset"):
            with self.subTest(mode=mode):
                onboard = self.load_onboard_module()
                skills_dir = self.root / mode / "skills"
                original = skills_dir / "diagnosing-bugs" / "SKILL.md"
                original.parent.mkdir(parents=True)
                original.write_text("previous payload", encoding="utf-8")
                args = onboard.build_parser().parse_args(
                    [
                        mode,
                        "--global-skills-dir",
                        str(skills_dir),
                        "--global-agents-path",
                        str(self.home / "global.md"),
                        "--yes",
                        "--json",
                    ]
                )
                real_move = onboard.rename_directory_exclusive
                skills_root = skills_dir.resolve()

                def reject_install_and_restore(
                    source,
                    destination,
                    *args,
                    target_root=skills_root,
                    move=real_move,
                    **kwargs,
                ):
                    destination = Path(destination)
                    if (
                        destination.name == "diagnosing-bugs"
                        and destination.parent == target_root
                    ):
                        raise OSError("simulated install and restore failure")
                    return move(source, destination, *args, **kwargs)

                stdout = io.StringIO()
                stderr = io.StringIO()
                with (
                    mock.patch.dict(
                        os.environ,
                        {"HOME": str(self.home), "PATH": str(self.bin_dir)},
                        clear=True,
                    ),
                    mock.patch.object(
                        onboard, "rename_directory_exclusive", side_effect=reject_install_and_restore
                    ),
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(stderr),
                ):
                    code = onboard.run(mode, args)

                self.assertEqual(code, 4, stderr.getvalue())
                payload = json.loads(stdout.getvalue())
                transaction = payload["requiredExternalInstall"]["transaction"]
                self.assertEqual(transaction["status"], "rollback-failed")
                recovery = (
                    Path(transaction["rollbackPath"]) / "diagnosing-bugs" / "SKILL.md"
                )
                self.assertEqual(
                    recovery.read_text(encoding="utf-8"), "previous payload"
                )

    def test_stable_manifest_paths_cannot_escape_the_declared_root(self) -> None:
        onboard = self.load_onboard_module()
        stable_root = self.root / "stable"
        stable_root.mkdir()
        outside = self.write_valid_skill(self.root / "outside", "diagnosing-bugs")
        manifest = {
            "stableSet": "fixture",
            "repositories": {
                "mattpocock-skills": {
                    "url": onboard.EXTERNAL_SKILL_SOURCES["diagnosing-bugs"]["repo"],
                    "revision": "1" * 40,
                }
            },
            "skills": {
                "diagnosing-bugs": {
                    "repository": "mattpocock-skills",
                    "stablePath": "../outside",
                    "treeSha256": onboard.external_tree_sha256(outside),
                }
            },
        }

        with self.assertRaisesRegex(RuntimeError, "relative path|declared root"):
            onboard.stable_external_skill_source(
                manifest, "diagnosing-bugs", stable_root
            )

        outside_license = self.root / "LICENSE"
        outside_license.write_text("fixture", encoding="utf-8")
        metadata = {
            "repositories": {
                "fixture": {
                    "revision": "1" * 40,
                    "licenseFiles": [{"source": "LICENSE", "stablePath": "../LICENSE"}],
                }
            }
        }
        with self.assertRaisesRegex(RuntimeError, "relative path|declared root"):
            onboard.validate_external_stable_metadata(metadata, stable_root)

    def test_promotion_rejects_source_subpath_outside_the_cloned_repository(
        self,
    ) -> None:
        onboard = self.load_onboard_module()
        stable_root = self.root / "stable"
        shutil.copytree(onboard.EXTERNAL_STABLE_ROOT, stable_root)
        manifest_path = stable_root / "MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        original_stable_set = manifest["stableSet"]
        outside = self.root / "outside-ui-ux-pro-max"
        shutil.copytree(
            onboard.EXTERNAL_STABLE_ROOT / "skills" / "ui-ux-pro-max",
            outside,
        )
        manifest["skills"]["ui-ux-pro-max"]["sourceSubpath"] = str(outside)
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        fake_repo = self.root / "promotion-repo"
        fake_repo.mkdir()
        shutil.copy2(
            onboard.EXTERNAL_STABLE_ROOT
            / "licenses"
            / "ui-ux-pro-max-skill-LICENSE",
            fake_repo / "LICENSE",
        )

        def fake_clone(_repo, _revision, destination):
            shutil.copytree(fake_repo, destination, dirs_exist_ok=True)
            return True, ""

        args = argparse.Namespace(
            repository="ui-ux-pro-max-skill",
            revision="2" * 40,
            stable_set="fixture",
            yes=True,
            json=True,
        )
        with (
            mock.patch.object(onboard, "EXTERNAL_STABLE_ROOT", stable_root),
            mock.patch.object(onboard, "EXTERNAL_STABLE_MANIFEST", manifest_path),
            mock.patch.object(
                onboard, "clone_repo_at_revision", side_effect=fake_clone
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            status = onboard.promote_external_skills_stable(args)

        self.assertNotEqual(status, 0)
        self.assertEqual(
            json.loads(manifest_path.read_text(encoding="utf-8"))["stableSet"],
            original_stable_set,
        )

    def test_promotion_prunes_retired_stable_skill_directory(self) -> None:
        onboard = self.load_onboard_module()
        stable_root = self.root / "stable"
        shutil.copytree(onboard.EXTERNAL_STABLE_ROOT, stable_root)
        manifest_path = stable_root / "MANIFEST.json"
        self.write_valid_skill(
            stable_root / "skills" / "writing-great-skills",
            "writing-great-skills",
            "retired stable content",
        )
        fake_repo = self.root / "promotion-repo"
        shutil.copytree(
            onboard.EXTERNAL_STABLE_ROOT / "skills" / "ui-ux-pro-max",
            fake_repo / ".claude" / "skills" / "ui-ux-pro-max",
        )
        shutil.copy2(
            onboard.EXTERNAL_STABLE_ROOT
            / "licenses"
            / "ui-ux-pro-max-skill-LICENSE",
            fake_repo / "LICENSE",
        )

        def fake_clone(_repo, _revision, destination):
            shutil.copytree(fake_repo, destination, dirs_exist_ok=True)
            return True, ""

        args = argparse.Namespace(
            repository="ui-ux-pro-max-skill",
            revision="2" * 40,
            stable_set="fixture",
            yes=True,
            json=True,
        )
        with (
            mock.patch.object(onboard, "EXTERNAL_STABLE_ROOT", stable_root),
            mock.patch.object(onboard, "EXTERNAL_STABLE_MANIFEST", manifest_path),
            mock.patch.object(
                onboard, "clone_repo_at_revision", side_effect=fake_clone
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            status = onboard.promote_external_skills_stable(args)

        self.assertEqual(status, 0)
        self.assertFalse((stable_root / "skills" / "writing-great-skills").exists())

    def test_prune_rejects_symlinked_stable_skills_root(self) -> None:
        onboard = self.load_onboard_module()
        stable_root = self.root / "stable"
        stable_root.mkdir()
        outside = self.root / "outside"
        outside.mkdir()
        (stable_root / "skills").symlink_to(outside, target_is_directory=True)

        with self.assertRaisesRegex(RuntimeError, "skills directory is invalid"):
            onboard.prune_unmanaged_stable_skill_directories(
                {"skills": {}}, stable_root
            )

    def test_bundled_migration_reports_legacy_deletion_failure(self) -> None:
        onboard = self.load_onboard_module()
        canonical = self.write_valid_skill(
            self.skills_dir / "sbtd-workflow-onboard",
            "sbtd-workflow-onboard",
        )
        legacy = self.write_valid_skill(
            self.skills_dir / "kuno-workflow-onboard-skills",
            "kuno-workflow-onboard-skills",
        )
        plan = {
            "status": "required",
            "migrations": [
                {
                    "canonicalName": "sbtd-workflow-onboard",
                    "canonicalTarget": str(canonical),
                    "legacyTargets": [str(legacy)],
                }
            ],
        }

        with mock.patch.object(
            onboard,
            "remove_existing_target",
            side_effect=OSError("simulated deletion failure"),
        ):
            results = onboard.run_bundled_skill_migration(plan)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "failed")
        self.assertEqual(results[0]["target"], str(legacy))
        self.assertIn("simulated deletion failure", results[0]["error"])

    def test_invalid_canonical_skill_is_reinstalled_before_legacy_removal(self) -> None:
        onboard = self.load_onboard_module()
        self.write_valid_skill(self.skills_dir / "diagnose", "diagnose", "legacy")
        self.write_valid_skill(
            self.skills_dir / "diagnosing-bugs", "wrong-name", "invalid canonical"
        )
        args = argparse.Namespace(global_skills_dir=str(self.skills_dir))

        missing = onboard.missing_required_external_skills(args)

        self.assertIn("diagnosing-bugs", missing)
        plan = {
            "status": "planned",
            "targetDir": str(self.skills_dir),
            "removeLegacy": ["diagnose"],
        }
        results = onboard.run_external_migration(plan)
        self.assertTrue((self.skills_dir / "diagnose" / "SKILL.md").is_file())
        self.assertTrue(any(item.get("phase") == "preflight" for item in results))

    def test_auto_requires_the_stable_manifest_without_cloning_upstream(self) -> None:
        onboard = self.load_onboard_module()
        clone = mock.Mock(side_effect=AssertionError("upstream must not be cloned"))

        with (
            mock.patch.object(
                onboard, "EXTERNAL_STABLE_MANIFEST", self.root / "missing.json"
            ),
            mock.patch.object(onboard, "clone_repo", clone),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "cannot read stable External Skills manifest"
            ):
                onboard.resolve_external_install_sources(
                    ["diagnosing-bugs"], "auto", self.root / "workspace"
                )

        clone.assert_not_called()

    def test_upstream_does_not_mask_unexpected_internal_errors_with_stable(self) -> None:
        onboard = self.load_onboard_module()
        stable_loader = mock.Mock(side_effect=RuntimeError("stable should not load"))

        with (
            mock.patch.object(onboard, "clone_repo", return_value=(True, "")),
            mock.patch.object(onboard, "cloned_repo_revision", return_value="1" * 40),
            mock.patch.object(
                onboard,
                "source_dir_for_external_skill",
                side_effect=AssertionError("unexpected internal error"),
            ),
            mock.patch.object(onboard, "load_external_stable_manifest", stable_loader),
        ):
            with self.assertRaisesRegex(AssertionError, "unexpected internal error"):
                onboard.resolve_external_install_sources(
                    ["diagnosing-bugs"], "upstream", self.root / "workspace"
                )

        stable_loader.assert_not_called()

    def test_tree_digest_ignores_locally_generated_bytecode_caches(self) -> None:
        """A local pytest run must not change a pinned Skill's checksum.

        Every exclusion the digest declares is exercised, not a sample of them:
        an untested entry can be dropped from either the digest or the copy
        filter without a test noticing. The copy filter is asserted against the
        same fixture, because the two lists are only useful while they agree --
        a cache file the copy keeps but the digest ignores reaches an installed
        Skill without moving `treeSha256`, which is the drift these exclusions
        exist to prevent.
        """

        onboard = self.load_onboard_module()
        self.assertEqual(
            set(onboard.EXTERNAL_TREE_DIGEST_EXCLUDED_DIRS)
            | set(onboard.EXTERNAL_TREE_DIGEST_EXCLUDED_SUFFIXES),
            {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".pyc", ".pyo"},
            "this test enumerates the exclusions below; a new one needs a fixture here.",
        )

        skill_root = self.root / "digest-skill"
        (skill_root / "scripts" / "tests").mkdir(parents=True)
        (skill_root / "SKILL.md").write_text("# skill\n", encoding="utf-8")
        (skill_root / "scripts" / "core.py").write_text("VALUE = 1\n", encoding="utf-8")
        # A directory may legitimately be named like a bytecode file. It is real
        # content, so it is pinned here and must survive both filters.
        (skill_root / "scripts" / "pkg.pyc").mkdir()
        (skill_root / "scripts" / "pkg.pyc" / "module.py").write_text(
            "KEPT = True\n", encoding="utf-8"
        )

        pinned_digest = onboard.external_tree_sha256(skill_root)

        cache_files = []
        for cache_dir in (
            "scripts/__pycache__",
            "scripts/tests/__pycache__",
            ".pytest_cache",
            ".ruff_cache",
            ".mypy_cache",
        ):
            target = skill_root / cache_dir
            target.mkdir(parents=True, exist_ok=True)
            entry = target / "core.cpython-313.pyc"
            entry.write_bytes(b"\x00compiled")
            cache_files.append(entry.relative_to(skill_root))
        for stray in ("scripts/stray.pyc", "scripts/stray.pyo"):
            entry = skill_root / stray
            entry.write_bytes(b"\x00compiled")
            cache_files.append(entry.relative_to(skill_root))

        self.assertEqual(
            onboard.external_tree_sha256(skill_root),
            pinned_digest,
            "bytecode and tool caches must not affect the external Skill tree digest.",
        )

        copied = self.root / "digest-skill-copy"
        shutil.copytree(skill_root, copied, ignore=onboard.external_copy_ignore())
        for relative in cache_files:
            with self.subTest(dropped=relative.as_posix()):
                self.assertFalse(
                    (copied / relative).exists(),
                    "a cache entry the digest ignores must not reach a copy.",
                )
        self.assertTrue(
            (copied / "scripts" / "pkg.pyc" / "module.py").is_file(),
            "a directory named like bytecode holds real content and must be copied.",
        )
        self.assertEqual(
            onboard.external_tree_sha256(copied),
            pinned_digest,
            "the copy filter and the digest must drop exactly the same entries.",
        )

        (skill_root / "scripts" / "core.py").write_text("VALUE = 2\n", encoding="utf-8")
        self.assertNotEqual(
            onboard.external_tree_sha256(skill_root),
            pinned_digest,
            "real source changes must still change the external Skill tree digest.",
        )


class StableSetCheckoutPortabilityTests(unittest.TestCase):
    """M01/M02 regression guard (2026-10-26 Windows migration).

    The stable set is pinned by raw-byte digests; cross-platform checkout
    portability comes from the committed root `.gitattributes` rule that
    disables text conversion for `sbtd-workflow-onboard/**`, not from
    digest-time line-ending normalization (decision recorded 2026-10-28:
    normalization was evaluated and rejected in favour of the raw-byte
    contract). These two tests pin both halves of that contract.
    """

    def load_module(self):
        module_name = f"onboard_portability_test_{id(self)}"
        spec = importlib.util.spec_from_file_location(module_name, ONBOARD)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load onboard module from {ONBOARD}")
        loader = cast(importlib.machinery.SourceFileLoader, spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        self.addCleanup(sys.modules.pop, module_name, None)
        loader.exec_module(module)
        return module

    def test_every_stable_skill_matches_its_manifest_digest(self) -> None:
        onboard = self.load_module()
        stable_root = (
            ROOT / "sbtd-workflow-onboard" / "assets" / "external-skills" / "stable"
        )
        manifest = json.loads(
            (stable_root / "MANIFEST.json").read_text(encoding="utf-8")
        )
        skills = manifest["skills"]
        self.assertEqual(len(skills), 19)
        for name, skill in skills.items():
            with self.subTest(skill=name):
                actual = onboard.external_tree_sha256(
                    stable_root / skill["stablePath"]
                )
                self.assertEqual(
                    actual,
                    skill["treeSha256"],
                    "stable payload drifted from the pinned manifest digest.",
                )

    def test_gitattributes_disables_text_conversion_for_pinned_payload(self) -> None:
        entries: list[tuple[str, set[str]]] = []
        for line in (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            pattern, _, attrs = line.partition(" ")
            entries.append((pattern, set(attrs.split())))

        def enables_text(attrs: set[str]) -> bool:
            return "text" in attrs or any(
                a.startswith(("text=", "eol")) for a in attrs
            )

        # git applies the last matching rule per attribute; a later rule that
        # re-enables text conversion must fail this guard instead of being
        # hidden by the earlier -text line still being present.
        def effective_text_attr(pattern: str) -> str | None:
            value: str | None = None
            for pat, attrs in entries:
                if pat != pattern:
                    continue
                if "-text" in attrs:
                    value = "-text"
                elif enables_text(attrs):
                    value = "text"
            return value

        for pattern in ("sbtd-workflow-onboard/**", "/LICENSE"):
            self.assertEqual(
                effective_text_attr(pattern),
                "-text",
                f"{pattern} must resolve to -text under last-match-wins so "
                "Windows autocrlf cannot rewrite raw-byte digests.",
            )
        seen_payload_rule = False
        for pattern, attrs in entries:
            if pattern == "sbtd-workflow-onboard/**":
                seen_payload_rule = True
                continue
            if seen_payload_rule and pattern.startswith("sbtd-workflow-onboard/"):
                self.assertFalse(
                    enables_text(attrs),
                    f"later rule {pattern} re-enables text conversion below the "
                    "pinned payload.",
                )


if __name__ == "__main__":
    unittest.main()
