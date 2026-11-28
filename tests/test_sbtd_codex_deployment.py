from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from onboard import GLOBAL_AGENTS_TEMPLATE
from onboard_contracts import ContractError, canonical_json_bytes
from sbtd_deployment import (
    attach_deployment,
    execute_migration_deployment,
    load_deployment_context,
)
from sbtd_migration import apply_migration, runtime_versions
from sbtd_migration_files import snapshot
from sbtd_migration_plan import plan_migration

from tests.test_sbtd_migration_apply import legacy_project


def _isolated_home(home, codex_home, skills_root):
    return {
        "HOME": str(home),
        "USERPROFILE": str(home),
        "CODEX_HOME": str(codex_home),
        "AGENT_SKILLS_DIR": str(skills_root),
        "PI_CONFIG_DIR": ".omp",
        "PI_CODING_AGENT_DIR": "",
        "OMP_PROFILE": "default",
        "PI_PROFILE": "default",
    }


class DeploymentContextTests(unittest.TestCase):
    def test_attach_deployment_normalizes_nested_skills_root_under_codex_home(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root, codex_home = base / "project", base / "codex"
            root.mkdir()
            roots = [str(root)]
            payload = {
                "projects": [
                    {
                        "root": str(root),
                        "private_operations": [],
                    }
                ],
                "shared_operations": [],
                "shared_roots": [
                    {
                        "kind": "skills",
                        "path": str(codex_home / "skills"),
                        "dependent_projects": roots,
                    }
                ],
            }
            with mock.patch.dict(
                os.environ,
                _isolated_home(base / "home", codex_home, codex_home / "skills"),
                clear=True,
            ):
                attach_deployment(payload, project_only=False, hooks_authorized=False)
            self.assertEqual(
                payload["shared_roots"],
                [
                    {
                        "kind": "codex-home",
                        "path": str(codex_home),
                        "skills_root": str(codex_home / "skills"),
                        "dependent_projects": roots,
                    }
                ],
            )
            targets = {operation["target"] for operation in payload["shared_operations"]}
            self.assertIn(str(codex_home / "AGENTS.md"), targets)
            self.assertIn(str(codex_home / "skills/sbtd-task"), targets)

    def test_attach_deployment_normalizes_nested_skills_root_under_omp_home(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root, codex_home, omp_home = (
                base / "project",
                base / "codex",
                base / "home/.omp/agent",
            )
            root.mkdir()
            roots = [str(root)]
            payload = {
                "projects": [
                    {
                        "root": str(root),
                        "private_operations": [],
                    }
                ],
                "shared_operations": [],
                "shared_roots": [
                    {
                        "kind": "skills",
                        "path": str(omp_home / "skills"),
                        "dependent_projects": roots,
                    }
                ],
            }
            with mock.patch.dict(
                os.environ,
                _isolated_home(base / "home", codex_home, omp_home / "skills"),
                clear=True,
            ):
                attach_deployment(
                    payload,
                    project_only=False,
                    hooks_authorized=False,
                    platform="omp",
                )
            self.assertEqual(
                payload["shared_roots"],
                [
                    {
                        "kind": "codex-home",
                        "path": str(codex_home),
                        "dependent_projects": roots,
                    },
                    {
                        "kind": "omp-home",
                        "path": str(omp_home.parent),
                        "skills_root": str(omp_home / "skills"),
                        "dependent_projects": roots,
                    },
                ],
            )
            targets = {operation["target"] for operation in payload["shared_operations"]}
            self.assertIn(str(omp_home / "AGENTS.md"), targets)
            self.assertIn(str(omp_home / "skills/sbtd-task"), targets)
            self.assertFalse(omp_home.parent.exists())

    def test_context_validates_scope_and_unused_private_output_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = legacy_project(base, "project")
            home, vault, evidence = (
                base / name for name in ("home", "vault", "evidence")
            )
            for path in (home, vault, evidence):
                path.mkdir(mode=0o700)
            environment = _isolated_home(home, home / ".codex", home / ".agent/skills")
            with mock.patch.dict(os.environ, environment):
                manifest = plan_migration(
                    [root],
                    vault,
                    "fixture",
                    None,
                    tool_versions=runtime_versions(),
                    deployment_mode="init",
                )
                manifest_path = evidence / "manifest.json"
                manifest_path.write_bytes(canonical_json_bytes(manifest))
                applied, code = apply_migration(
                    manifest_path, confirmed=True, no_routing_approvals=True
                )
                self.assertEqual(code, 0, applied)
                receipt = applied["migration"]["apply_receipt"]
                apply_path = evidence / ("apply-" + receipt["apply_id"] + ".json")
                before = snapshot(base)
                context = load_deployment_context(
                    manifest_path,
                    apply_path,
                    evidence / "deployment.json",
                    previous_path=None,
                    mode="init",
                    roots=[root],
                    hooks_authorized=False,
                )
                self.assertEqual(context.applied["apply_id"], receipt["apply_id"])
                self.assertEqual(snapshot(base), before)
                with self.assertRaises(ContractError):
                    load_deployment_context(
                        manifest_path,
                        apply_path,
                        evidence / "wrong-mode.json",
                        previous_path=None,
                        mode="init-projects",
                        roots=[root],
                        hooks_authorized=False,
                    )
                self.assertEqual(snapshot(base), before)
                for output, roots, hooks in (
                    (vault / "not-the-manifest-directory.json", [root], False),
                    (evidence / "deployment.json", [base], False),
                    (evidence / "deployment.json", [root], True),
                    (manifest_path, [root], False),
                ):
                    with (
                        self.subTest(output=output.name, hooks=hooks),
                        self.assertRaises(ContractError),
                    ):
                        load_deployment_context(
                            manifest_path,
                            apply_path,
                            output,
                            previous_path=None,
                            mode="init",
                            roots=roots,
                            hooks_authorized=hooks,
                        )
                    self.assertEqual(snapshot(base), before)
                with mock.patch("sbtd_deployment.datetime") as clock:
                    clock.now.return_value.isoformat.return_value = (
                        "2000-01-01T00:00:00+00:00"
                    )
                    with self.assertRaises(ContractError) as failure:
                        load_deployment_context(
                            manifest_path,
                            apply_path,
                            evidence / "clock-rollback.json",
                            previous_path=None,
                            mode="init",
                            roots=[root],
                            hooks_authorized=False,
                        )
                    self.assertEqual(failure.exception.code, "state-conflict")
                self.assertEqual(snapshot(base), before)

    def test_shared_scope_creation_failure_retains_prior_writes_in_saved_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = legacy_project(base, "project")
            home, vault, evidence = (
                base / name for name in ("home", "vault", "evidence")
            )
            for path in (home, vault, evidence):
                path.mkdir(mode=0o700)
            active = home / "active-codex"
            skills = home / ".agent/skills"
            rules = active / "AGENTS.md"
            environment = _isolated_home(home, active, skills)
            with mock.patch.dict(os.environ, environment):
                manifest = plan_migration(
                    [root],
                    vault,
                    "fixture",
                    None,
                    tool_versions=runtime_versions(),
                    deployment_mode="init",
                )
                manifest_path = evidence / "manifest.json"
                manifest_path.write_bytes(canonical_json_bytes(manifest))
                applied, code = apply_migration(
                    manifest_path, confirmed=True, no_routing_approvals=True
                )
                self.assertEqual(code, 0, applied)
                operations = {
                    operation["resource_id"]: operation
                    for operation in manifest["payload"]["shared_operations"]
                    if operation["phase"] == "deploy"
                }
                rules_id = next(
                    rid for rid, operation in operations.items()
                    if operation["target"] == str(rules)
                )
                receipt = applied["migration"]["apply_receipt"]
                output = evidence / "deployment.json"
                context = load_deployment_context(
                    manifest_path,
                    evidence / ("apply-" + receipt["apply_id"] + ".json"),
                    output,
                    previous_path=None,
                    mode="init",
                    roots=[root],
                    hooks_authorized=False,
                )
                original_mkdir = Path.mkdir

                def deny_skills_root(path, *args, **kwargs):
                    if path == skills:
                        raise PermissionError("synthetic skills scope creation failure")
                    return original_mkdir(path, *args, **kwargs)

                with mock.patch.object(Path, "mkdir", deny_skills_root):
                    result, code = execute_migration_deployment(context)
                self.assertEqual((code, result["status"]), (2, "blocked"), result)
                self.assertEqual(result["deploymentEvidence"]["path"], str(output))
                saved = result["deploymentEvidence"]["evidence"]["payload"]
                rows = {row["resource_id"]: row for row in saved["shared_results"]}
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[rules_id]["status"], "succeeded")
                self.assertEqual(rows[rules_id]["before"]["type"], "absent")
                self.assertEqual(rows[rules_id]["after"], snapshot(rules))
                self.assertEqual(rules.read_bytes(), GLOBAL_AGENTS_TEMPLATE.read_bytes())
                if os.name == "posix":
                    self.assertEqual(stat.S_IMODE(active.stat().st_mode), 0o700)
                rules_inode = rules.stat().st_ino
                blocked = next(row for row in rows.values() if row["status"] == "blocked")
                self.assertEqual(Path(operations[blocked["resource_id"]]["target"]).parent, skills)
                self.assertEqual(blocked["before"], blocked["after"])
                self.assertFalse(skills.exists())
                self.assertFalse(saved["projects"][0]["report_refs"])
                self.assertFalse((root / "graft").exists())
                self.assertNotIn(
                    b"<!-- graft:start -->", (root / "AGENTS.md").read_bytes()
                )
                before_retry = snapshot(root)
                retry_path = evidence / "retry.json"
                retry = load_deployment_context(
                    manifest_path,
                    evidence / ("apply-" + receipt["apply_id"] + ".json"),
                    retry_path,
                    previous_path=output,
                    mode="init",
                    roots=[root],
                    hooks_authorized=False,
                )
                retried, code = execute_migration_deployment(retry)
                self.assertEqual(code, 0, retried)
                self.assertEqual(retried["status"], "succeeded")
                self.assertTrue(retried["projects"][0]["report_refs"])
                self.assertFalse((root / "graft").exists())
                self.assertEqual(snapshot(root), before_retry)
                cumulative = retried["deploymentEvidence"]["evidence"]["payload"]
                retried_rows = {row["resource_id"]: row for row in cumulative["shared_results"]}
                self.assertEqual(retried_rows[rules_id], rows[rules_id])
                self.assertEqual(rules.stat().st_ino, rules_inode)
                self.assertEqual(retried_rows[blocked["resource_id"]]["status"], "succeeded")
                self.assertTrue((skills / "sbtd-task/SKILL.md").is_file())
                self.assertFalse((active / "config.toml").exists())
                with mock.patch("sbtd_deployment.datetime") as clock:
                    clock.now.return_value.isoformat.return_value = receipt["payload"][
                        "finished_at"
                    ]
                    with self.assertRaises(ContractError) as failure:
                        load_deployment_context(
                            manifest_path,
                            evidence / ("apply-" + receipt["apply_id"] + ".json"),
                            evidence / "previous-clock-rollback.json",
                            previous_path=retry_path,
                            mode="init",
                            roots=[root],
                            hooks_authorized=False,
                        )
                    self.assertEqual(failure.exception.code, "state-conflict")
                self.assertFalse((evidence / "previous-clock-rollback.json").exists())

                unsaved_path = evidence / "unsaved.json"
                third = load_deployment_context(
                    manifest_path,
                    evidence / ("apply-" + receipt["apply_id"] + ".json"),
                    unsaved_path,
                    previous_path=retry_path,
                    mode="init",
                    roots=[root],
                    hooks_authorized=False,
                )
                with mock.patch(
                    "sbtd_deployment.save_document",
                    side_effect=OSError("synthetic evidence write failure"),
                ):
                    unsaved, code = execute_migration_deployment(third)
                self.assertEqual(code, 5)
                self.assertIsNone(unsaved["deploymentEvidence"])
                self.assertFalse(unsaved_path.exists())
                compared = retried["deploymentEvidence"]["evidence"]["payload"]
                self.assertEqual(
                    {item["resource_id"]: item for item in unsaved["operationResults"]},
                    {
                        item["resource_id"]: item
                        for item in compared["projects"][0]["private_results"]
                        + compared["shared_results"]
                    },
                )
                self.assertEqual(snapshot(root), before_retry)

class DeploymentSharedRootTests(unittest.TestCase):
    def _copy_operation(self, source, target, root, target_state=None):
        recorded = snapshot(target) if target_state is None else target_state
        return {
            "before_requirement": {"kind": "state", "state": recorded},
            "change": {
                "kind": "copy-file",
                "source_ref": {"path": str(source), "state": snapshot(source)},
            },
            "dependent_projects": [str(root)],
            "operation_id": "fixture-operation",
            "owner_kind": "markdown",
            "ownership": {
                "kind": "template-source",
                "reference": {"path": str(source), "state": snapshot(source)},
            },
            "phase": "deploy",
            "resource_id": "fixture-resource",
            "selector": "global-rules",
            "target": str(target),
        }

    def _execute(self, operation, root, vault, expected=None):
        from sbtd_deployment import execute_resource

        target = Path(operation["target"])
        return execute_resource(
            operation,
            expected=snapshot(target) if expected is None else expected,
            root=Path(root),
            private_root=Path(vault),
            backup_path=Path(vault) / "deploy" / operation["resource_id"],
        )

    def test_shared_root_with_unrelated_symlink_deploys(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root, vault = base / "shared-root", base / "vault"
            root.mkdir(mode=0o700)
            vault.mkdir(mode=0o700)
            elsewhere = base / "elsewhere"
            elsewhere.mkdir()
            (elsewhere / "payload").write_bytes(b"unrelated payload\n")
            os.symlink(elsewhere, root / "plugins")
            source = base / "source.md"
            source.write_bytes(b"canonical template\n")
            target = root / "AGENTS.md"
            target.write_bytes(b"paused routing\n")
            result = self._execute(self._copy_operation(source, target, root), root, vault)
            self.assertEqual(result["status"], "succeeded", result)
            self.assertEqual(target.read_bytes(), b"canonical template\n")
            self.assertTrue((root / "plugins").is_symlink())
            self.assertEqual(os.readlink(root / "plugins"), str(elsewhere))
            backup = result["backup_ref"]
            self.assertIsNotNone(backup)
            self.assertEqual(
                Path(backup["path"]).read_bytes(), b"paused routing\n"
            )

    def test_shared_root_symlink_scope_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            real, vault = base / "real-root", base / "vault"
            real.mkdir(mode=0o700)
            vault.mkdir(mode=0o700)
            link = base / "link-root"
            os.symlink(real, link)
            source = base / "source.md"
            source.write_bytes(b"canonical template\n")
            target = link / "AGENTS.md"
            target.write_bytes(b"paused routing\n")
            absent = {"type": "absent", "checksum": None}
            result = self._execute(
                self._copy_operation(source, target, link, target_state=absent),
                link,
                vault,
                expected=absent,
            )
            self.assertEqual(result["status"], "blocked", result)
            self.assertEqual(target.read_bytes(), b"paused routing\n")

    def test_shared_root_non_directory_scope_is_rejected(self):
        # The target snapshot precheck rejects a non-directory scope before the
        # scope-root branch can fire; this proves the fail-closed outcome (no
        # writes, original untouched), not which guard raised first.
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            vault = base / "vault"
            vault.mkdir(mode=0o700)
            scope_file = base / "scope-file"
            scope_file.write_bytes(b"not a directory\n")
            source = base / "source.md"
            source.write_bytes(b"canonical template\n")
            target = scope_file / "AGENTS.md"
            absent = {"type": "absent", "checksum": None}
            operation = self._copy_operation(
                source, target, scope_file, target_state=absent
            )
            result = self._execute(
                operation,
                scope_file,
                vault,
                expected={"type": "absent", "checksum": None},
            )
            self.assertEqual(result["status"], "blocked", result)
            self.assertEqual(scope_file.read_bytes(), b"not a directory\n")

    def test_absent_shared_root_is_created_private(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            vault = base / "vault"
            vault.mkdir(mode=0o700)
            root = base / "fresh-root"
            source = base / "source.md"
            source.write_bytes(b"canonical template\n")
            target = root / "AGENTS.md"
            absent = {"type": "absent", "checksum": None}
            operation = self._copy_operation(source, target, root, target_state=absent)
            result = self._execute(
                operation,
                root,
                vault,
                expected={"type": "absent", "checksum": None},
            )
            self.assertEqual(result["status"], "succeeded", result)
            import stat as stat_module

            mode = stat_module.S_IMODE(root.stat().st_mode)
            self.assertEqual(mode & 0o077, 0)
            self.assertEqual(target.read_bytes(), b"canonical template\n")

    def test_full_deployment_with_symlinked_shared_root(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = legacy_project(base, "project")
            home, vault, evidence = (
                base / name for name in ("home", "vault", "evidence")
            )
            for path in (home, vault, evidence):
                path.mkdir(mode=0o700)
            active = home / "active-codex"
            active.mkdir(mode=0o700)
            elsewhere = home / "elsewhere"
            elsewhere.mkdir()
            (elsewhere / "payload").write_bytes(b"unrelated payload\n")
            os.symlink(elsewhere, active / "plugins")
            environment = _isolated_home(home, active, home / ".agent/skills")
            with mock.patch.dict(os.environ, environment):
                manifest = plan_migration(
                    [root],
                    vault,
                    "fixture",
                    None,
                    tool_versions=runtime_versions(),
                    deployment_mode="init",
                )
                manifest_path = evidence / "manifest.json"
                manifest_path.write_bytes(canonical_json_bytes(manifest))
                applied, code = apply_migration(
                    manifest_path, confirmed=True, no_routing_approvals=True
                )
                self.assertEqual(code, 0, applied)
                receipt = applied["migration"]["apply_receipt"]
                context = load_deployment_context(
                    manifest_path,
                    evidence / ("apply-" + receipt["apply_id"] + ".json"),
                    evidence / "deployment.json",
                    previous_path=None,
                    mode="init",
                    roots=[root],
                    hooks_authorized=False,
                )

                result, code = execute_migration_deployment(context)
                self.assertEqual(code, 0, result)
                self.assertEqual(result["status"], "succeeded")
                saved = result["deploymentEvidence"]["evidence"]["payload"]
                self.assertEqual(saved["status"], "succeeded")
                self.assertTrue(saved["projects"][0]["report_refs"])
                for resource in saved["shared_results"]:
                    self.assertEqual(resource["status"], "succeeded", resource)
                self.assertTrue((active / "plugins").is_symlink())
                self.assertEqual(os.readlink(active / "plugins"), str(elsewhere))
                self.assertEqual((elsewhere / "payload").read_bytes(), b"unrelated payload\n")
                rules = active / "AGENTS.md"
                operation = next(
                    item for item in manifest["payload"]["shared_operations"]
                    if item["phase"] == "deploy" and item["target"] == str(rules)
                )
                outcome = next(
                    row for row in saved["shared_results"]
                    if row["resource_id"] == operation["resource_id"]
                )
                self.assertEqual(outcome["after"], snapshot(rules))
                self.assertEqual(rules.read_bytes(), GLOBAL_AGENTS_TEMPLATE.read_bytes())
                self.assertFalse((active / "config.toml").exists())


if __name__ == "__main__":
    unittest.main()
