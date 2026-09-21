from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from onboard_contracts import ContractError, canonical_json_bytes
from sbtd_graft_deployment import (
    attach_deployment,
    execute_migration_deployment,
    load_deployment_context,
)
from sbtd_migration import apply_migration, runtime_versions
from sbtd_migration_files import snapshot
from sbtd_migration_plan import plan_migration

from tests.test_sbtd_migration_apply import legacy_project


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
                        "private_operations": [{"owner_kind": "gitignore"}],
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
            with (
                mock.patch("onboard.default_codex_home", return_value=codex_home),
                mock.patch("onboard.detect_omp_root", return_value=None),
                mock.patch(
                    "onboard.resolve_global_skills_dir",
                    return_value=(codex_home / "skills", "fixture"),
                ),
                mock.patch(
                    "sbtd_graft_deployment.deployment_operations",
                    return_value=({str(root): []}, []),
                ),
                mock.patch(
                    "sbtd_graft_deployment._installation_templates", return_value=[]
                ),
            ):
                attach_deployment(payload, project_only=False, hooks_authorized=False)
            self.assertEqual(
                payload["shared_roots"],
                [
                    {
                        "kind": "codex-home",
                        "path": str(codex_home),
                        "dependent_projects": roots,
                    }
                ],
            )

    def test_attach_deployment_normalizes_nested_skills_root_under_omp_home(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root, codex_home, omp_home = (
                base / "project",
                base / "codex",
                base / "omp/agent",
            )
            root.mkdir()
            roots = [str(root)]
            payload = {
                "projects": [
                    {
                        "root": str(root),
                        "private_operations": [{"owner_kind": "gitignore"}],
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
            with (
                mock.patch("onboard.default_codex_home", return_value=codex_home),
                mock.patch("onboard.detect_omp_root", return_value=omp_home.parent),
                mock.patch(
                    "onboard.resolve_global_skills_dir",
                    return_value=(omp_home / "skills", "fixture"),
                ),
                mock.patch(
                    "sbtd_graft_deployment.deployment_operations",
                    return_value=({str(root): []}, []),
                ),
                mock.patch(
                    "sbtd_graft_deployment._installation_templates", return_value=[]
                ),
                mock.patch(
                    "sbtd_omp_sources.discover_omp_sources",
                    return_value={
                        "agent_dir": str(omp_home),
                        "inputs": [],
                    },
                ),
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
                        "dependent_projects": roots,
                    },
                ],
            )

    def test_context_validates_scope_and_unused_private_output_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = legacy_project(base, "project")
            home, vault, evidence = (
                base / name for name in ("home", "vault", "evidence")
            )
            for path in (home, vault, evidence):
                path.mkdir(mode=0o700)
            environment = {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "CODEX_HOME": str(home / ".codex"),
                "AGENT_SKILLS_DIR": str(home / ".agent/skills"),
            }
            with mock.patch.dict(os.environ, environment):
                manifest = plan_migration(
                    [root],
                    vault,
                    "fixture",
                    None,
                    tool_versions=runtime_versions(),
                    deployment_mode="init-projects",
                )
                manifest_path = evidence / "manifest.json"
                manifest_path.write_bytes(canonical_json_bytes(manifest))
                applied, code = apply_migration(manifest_path, confirmed=True)
                self.assertEqual(code, 0, applied)
                receipt = applied["migration"]["apply_receipt"]
                apply_path = evidence / ("apply-" + receipt["apply_id"] + ".json")
                before = snapshot(base)
                context = load_deployment_context(
                    manifest_path,
                    apply_path,
                    evidence / "deployment.json",
                    previous_path=None,
                    mode="init-projects",
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
                        mode="init",
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
                            mode="init-projects",
                            roots=roots,
                            hooks_authorized=hooks,
                        )
                    self.assertEqual(snapshot(base), before)
                with mock.patch("sbtd_graft_deployment.datetime") as clock:
                    clock.now.return_value.isoformat.return_value = (
                        "2000-01-01T00:00:00+00:00"
                    )
                    with self.assertRaises(ContractError) as failure:
                        load_deployment_context(
                            manifest_path,
                            apply_path,
                            evidence / "clock-rollback.json",
                            previous_path=None,
                            mode="init-projects",
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
            environment = {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "CODEX_HOME": str(active),
                "AGENT_SKILLS_DIR": str(home / ".agent/skills"),
            }
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
                applied, code = apply_migration(manifest_path, confirmed=True)
                self.assertEqual(code, 0, applied)
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

                def deny_active_home(path, *args, **kwargs):
                    if path == active:
                        raise PermissionError("synthetic scope creation failure")
                    return original_mkdir(path, *args, **kwargs)

                def isolated_native_boundary(project, _runtime):
                    (project / "graft").mkdir()
                    (project / "graft/fixture").write_bytes(b"synthetic native output")

                runtime = {
                    "node": "/fixture/node",
                    "cli": "/fixture/cli.js",
                    "python": "/fixture/python",
                }
                with (
                    mock.patch(
                        "sbtd_graft_deployment.verified_runtime", return_value=runtime
                    ),
                    mock.patch(
                        "sbtd_graft_deployment.build_project_graph",
                        side_effect=isolated_native_boundary,
                    ),
                    mock.patch.object(Path, "mkdir", deny_active_home),
                ):
                    result, code = execute_migration_deployment(context)
                self.assertNotEqual(code, 0)
                self.assertEqual(result["deploymentEvidence"]["path"], str(output))
                saved = result["deploymentEvidence"]["evidence"]["payload"]
                self.assertEqual(saved["status"], "blocked")
                self.assertEqual(len(saved["projects"][0]["private_results"]), 2)
                for resource in saved["projects"][0]["private_results"]:
                    self.assertEqual(resource["status"], "succeeded")
                    self.assertIsNotNone(resource["after"])
                self.assertFalse(active.exists())
                self.assertIn(
                    b"<!-- graft:start -->", (root / "AGENTS.md").read_bytes()
                )
                self.assertEqual(
                    (root / "graft/fixture").read_bytes(), b"synthetic native output"
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
                with (
                    mock.patch(
                        "sbtd_graft_deployment.verified_runtime", return_value=runtime
                    ),
                    mock.patch(
                        "sbtd_graft_deployment.build_project_graph",
                        side_effect=AssertionError(
                            "completed graph must not be rebuilt"
                        ),
                    ),
                    mock.patch(
                        "sbtd_graft_deployment.run_project_smoke",
                        side_effect=OSError("synthetic smoke failure"),
                    ),
                ):
                    retried, code = execute_migration_deployment(retry)
                self.assertNotEqual(code, 0)
                second = retried["deploymentEvidence"]["evidence"]["payload"]
                self.assertEqual(second["status"], "failed")
                self.assertEqual(
                    second["projects"][0]["private_results"],
                    saved["projects"][0]["private_results"],
                )
                self.assertEqual(snapshot(root), before_retry)
                self.assertTrue((active / "config.toml").is_file())
                self.assertTrue((home / ".agent/skills/sbtd-task/SKILL.md").is_file())
                with mock.patch("sbtd_graft_deployment.datetime") as clock:
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
                with (
                    mock.patch(
                        "sbtd_graft_deployment.verified_runtime", return_value=runtime
                    ),
                    mock.patch(
                        "sbtd_graft_deployment.run_project_smoke",
                        side_effect=OSError("synthetic smoke failure"),
                    ),
                    mock.patch(
                        "sbtd_graft_deployment.save_document",
                        side_effect=OSError("synthetic evidence write failure"),
                    ),
                ):
                    unsaved, code = execute_migration_deployment(third)
                self.assertEqual(code, 5)
                self.assertIsNone(unsaved["deploymentEvidence"])
                self.assertFalse(unsaved_path.exists())
                self.assertEqual(
                    {item["resource_id"]: item for item in unsaved["operationResults"]},
                    {
                        item["resource_id"]: item
                        for item in second["projects"][0]["private_results"]
                        + second["shared_results"]
                    },
                )
                self.assertEqual(snapshot(root), before_retry)


if __name__ == "__main__":
    unittest.main()
