from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard/scripts"
sys.path.insert(0, str(SCRIPTS))

import sbtd_migration_plan
from onboard_contracts import ContractError, canonical_json_bytes
from sbtd_migration import apply_migration, runtime_versions
from sbtd_migration_plan import plan_migration


def legacy_project(base: Path, name: str) -> Path:
    root = base / name
    (root / ".trellis/workspace/dev01").mkdir(parents=True)
    (root / ".codex/agents").mkdir(parents=True)
    (root / ".trellis/.developer").write_bytes(
        b"name=dev01\ninitialized_at=2026-09-01T12:00:00\n"
    )
    (root / ".trellis/.version").write_text("0.6.17\n")
    (root / ".trellis/workspace/dev01/journal-1.md").write_text(
        "Synthetic private legacy journal.\n"
    )
    (root / ".trellis/workspace/dev01/untracked.bin").write_bytes(
        b"\x00retained-private-fixture\xff"
    )
    (root / ".gitignore").write_text(".trellis/\n.gitnexus/\n")
    (root / "AGENTS.md").write_bytes(
        b"Foreign project rule.\n<!-- TRELLIS:START -->\nLegacy route.\n<!-- TRELLIS:END -->\n"
    )
    owned = {
        ".codex/agents/trellis-implement.toml": b'name = "trellis-implement"\n',
    }
    for relative_name, raw in owned.items():
        (root / relative_name).write_bytes(raw)
    (root / ".trellis/.template-hashes.json").write_text(
        json.dumps(
            {
                "__version": 2,
                "hashes": {
                    name: hashlib.sha256(raw).hexdigest() for name, raw in owned.items()
                },
            }
        )
    )
    return root


def file_contents(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


class MigrationApplyTests(unittest.TestCase):
    def test_resource_preservation_failure_keeps_exit_three(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = legacy_project(base, "project")
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
                    [project], vault, "fixture", None, tool_versions=runtime_versions()
                )
                path = evidence / "manifest.json"
                path.write_bytes(canonical_json_bytes(manifest))
                before = (project / ".gitignore").read_bytes()
                with mock.patch(
                    "sbtd_migration.write_file",
                    side_effect=ContractError(
                        "checksum-mismatch", "synthetic readback failure", exit_code=3
                    ),
                ):
                    response, code = apply_migration(
                        path, confirmed=True, no_routing_approvals=True
                    )
            self.assertEqual(code, 3, response)
            self.assertEqual(response["status"], "failed")
            self.assertEqual((project / ".gitignore").read_bytes(), before)

    def test_batch_preflight_rejects_drift_before_any_project_write(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            roots = [legacy_project(base, name) for name in ("alpha", "beta")]
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
                    roots, vault, "fixture", None, tool_versions=runtime_versions()
                )
                manifest_path = evidence / "manifest.json"
                manifest_path.write_bytes(canonical_json_bytes(manifest))
                (roots[1] / "AGENTS.md").write_bytes(b"user changed the second project")
                before = file_contents(base)
                with self.assertRaises(ContractError):
                    apply_migration(manifest_path, confirmed=True)
                self.assertEqual(file_contents(base), before)
                self.assertEqual(list(vault.iterdir()), [])
                self.assertFalse((roots[0] / ".sbtd").exists())

    def test_partial_batch_retains_success_and_retries_only_unfinished_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            roots = [legacy_project(base, name) for name in ("alpha", "beta")]
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
                    roots, vault, "fixture", None, tool_versions=runtime_versions()
                )
                manifest_path = evidence / "manifest.json"
                manifest_path.write_bytes(canonical_json_bytes(manifest))
                link = os.link

                def fail_second_identity(source, destination, *args, **kwargs):
                    if Path(destination) == roots[1] / ".sbtd/developer":
                        raise OSError("synthetic second-project write failure")
                    return link(source, destination, *args, **kwargs)

                with mock.patch(
                    "sbtd_migration_files.os.link", side_effect=fail_second_identity
                ):
                    failed, code = apply_migration(
                        manifest_path, confirmed=True, no_routing_approvals=True
                    )
                self.assertEqual(code, 5, failed)
                receipt = failed["migration"]["apply_receipt"]
                statuses = {
                    project["root"]: project["status"]
                    for project in receipt["payload"]["projects"]
                }
                self.assertEqual(
                    statuses, {str(roots[0]): "applied", str(roots[1]): "failed"}
                )
                self.assertEqual(
                    (roots[0] / ".sbtd/developer").read_bytes(), b"name=dev01\n"
                )
                self.assertFalse((roots[1] / ".sbtd/developer").exists())
                saved = next(
                    path
                    for path in evidence.glob("*.json")
                    if json.loads(path.read_text()).get("apply_id")
                    == receipt["apply_id"]
                )
                first_tree = file_contents(roots[0])
                first_results = receipt["payload"]["projects"][0]["private_results"]
                retried, retry_code = apply_migration(
                    manifest_path,
                    previous_receipt_path=saved,
                    confirmed=True,
                    no_routing_approvals=True,
                )
                self.assertEqual(retry_code, 0, retried)
                final = retried["migration"]["apply_receipt"]
                self.assertEqual(
                    final["payload"]["previous_receipt_id"], receipt["apply_id"]
                )
                self.assertEqual(file_contents(roots[0]), first_tree)
                self.assertEqual(
                    final["payload"]["projects"][0]["private_results"], first_results
                )
                self.assertEqual(
                    (roots[1] / ".sbtd/developer").read_bytes(), b"name=dev01\n"
                )

    def test_unapproved_global_pause_is_refused_before_write(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = legacy_project(base, "project")
            omp_agent = root / ".omp/agents/trellis-implement.md"
            omp_agent.parent.mkdir(parents=True)
            omp_agent.write_bytes(b"# Legacy OMP agent\n")
            metadata_path = root / ".trellis/.template-hashes.json"
            metadata = json.loads(metadata_path.read_text())
            metadata["hashes"][".omp/agents/trellis-implement.md"] = hashlib.sha256(
                omp_agent.read_bytes()
            ).hexdigest()
            metadata_path.write_text(json.dumps(metadata))
            home, vault, evidence = (
                base / name for name in ("home", "vault", "evidence")
            )
            for path in (home, vault, evidence):
                path.mkdir(mode=0o700)
            router = home / ".omp/agent/AGENTS.md"
            router.parent.mkdir(parents=True)
            legacy_global = (
                b"# Legacy global routing\nUse trellis-workflow for every task.\n"
            )
            router.write_bytes(legacy_global)
            environment = {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "CODEX_HOME": str(home / ".codex"),
                "AGENT_SKILLS_DIR": str(home / ".agent/skills"),
            }
            fixture_pins = sbtd_migration_plan._ownership_pins()
            fixture_pins["agents"] = hashlib.sha256(legacy_global).hexdigest()
            with (
                mock.patch.dict(os.environ, environment),
                mock.patch.object(
                    sbtd_migration_plan, "_ownership_pins", return_value=fixture_pins
                ),
            ):
                before_plan = file_contents(base)
                manifest = plan_migration(
                    [root], vault, "fixture", None, tool_versions=runtime_versions()
                )
                self.assertEqual(file_contents(base), before_plan)
                shared = manifest["payload"]["shared_operations"]
                self.assertEqual(
                    [operation["target"] for operation in shared], [str(router)]
                )
                self.assertEqual(
                    manifest["payload"]["shared_roots"],
                    [
                        {
                            "kind": "omp-home",
                            "path": str(home / ".omp"),
                            "dependent_projects": [str(root)],
                        }
                    ],
                )
                manifest_path = evidence / "manifest.json"
                manifest_path.write_bytes(canonical_json_bytes(manifest))
                with (
                    mock.patch(
                        "sbtd_migration._render_resource",
                        side_effect=AssertionError("render"),
                    ),
                    self.assertRaises(ContractError) as error,
                ):
                    apply_migration(
                        manifest_path, confirmed=True, no_routing_approvals=True
                    )
                self.assertEqual(error.exception.code, "approval-conflict")
                self.assertEqual(router.read_bytes(), legacy_global)

    def test_private_failure_saves_retryable_partial_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            roots = [legacy_project(base, name) for name in ("alpha", "beta")]
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
                    roots, vault, "fixture", None, tool_versions=runtime_versions()
                )
                manifest_path = evidence / "manifest.json"
                manifest_path.write_bytes(canonical_json_bytes(manifest))
                link = os.link

                def fail_beta_identity(source, destination, *args, **kwargs):
                    if Path(destination) == roots[1] / ".sbtd/developer":
                        raise OSError(
                            "synthetic private write failure before the shared pause"
                        )
                    return link(source, destination, *args, **kwargs)

                with mock.patch(
                    "sbtd_migration_files.os.link", side_effect=fail_beta_identity
                ):
                    failed, code = apply_migration(
                        manifest_path, confirmed=True, no_routing_approvals=True
                    )
                self.assertEqual(code, 5, failed)
                receipt = failed["migration"]["apply_receipt"]
                statuses = {
                    project["root"]: project["status"]
                    for project in receipt["payload"]["projects"]
                }
                self.assertEqual(
                    statuses, {str(roots[0]): "applied", str(roots[1]): "failed"}
                )
                self.assertEqual(receipt["payload"]["shared_results"], [])
                for project in receipt["payload"]["projects"]:
                    self.assertEqual(project["shared_operation_ids"], [])

                self.assertEqual(
                    (roots[0] / ".sbtd/developer").read_bytes(), b"name=dev01\n"
                )
                self.assertFalse(
                    (roots[1] / ".codex/agents/trellis-implement.toml").exists()
                )
                self.assertFalse((roots[1] / ".sbtd/developer").exists())
                saved = next(
                    path
                    for path in evidence.glob("*.json")
                    if json.loads(path.read_text()).get("apply_id")
                    == receipt["apply_id"]
                )
                self.assertEqual(json.loads(saved.read_text()), receipt)
                first_tree = file_contents(roots[0])
                first_results = receipt["payload"]["projects"][0]["private_results"]
                retried, retry_code = apply_migration(
                    manifest_path,
                    previous_receipt_path=saved,
                    confirmed=True,
                    no_routing_approvals=True,
                )
                self.assertEqual(retry_code, 0, retried)
                self.assertEqual(retried["status"], "applied")
                final = retried["migration"]["apply_receipt"]
                self.assertEqual(
                    final["payload"]["previous_receipt_id"], receipt["apply_id"]
                )
                self.assertEqual(file_contents(roots[0]), first_tree)
                self.assertEqual(
                    final["payload"]["projects"][0]["private_results"], first_results
                )
                self.assertEqual(
                    {
                        project["root"]: project["status"]
                        for project in final["payload"]["projects"]
                    },
                    {
                        str(roots[0]): "already-complete",
                        str(roots[1]): "applied",
                    },
                )
                self.assertEqual(
                    (roots[1] / ".sbtd/developer").read_bytes(), b"name=dev01\n"
                )

    def test_first_apply_preserves_originals_and_retry_uses_the_saved_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = legacy_project(base, "project")
            home = base / "home"
            home.mkdir(mode=0o700)
            vault = base / "vault"
            vault.mkdir(mode=0o700)
            evidence = base / "evidence"
            evidence.mkdir(mode=0o700)
            environment = {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "CODEX_HOME": str(home / ".codex"),
                "AGENT_SKILLS_DIR": str(home / ".agent/skills"),
            }
            old_tree = file_contents(root / ".trellis")
            with mock.patch.dict(os.environ, environment):
                manifest = plan_migration(
                    [root],
                    vault,
                    "fixture-custodian",
                    None,
                    tool_versions=runtime_versions(),
                )
                manifest_path = evidence / "manifest.json"
                manifest_path.write_bytes(canonical_json_bytes(manifest))
                applied, code = apply_migration(
                    manifest_path, confirmed=True, no_routing_approvals=True
                )
                self.assertEqual(code, 0, applied)
                self.assertEqual(applied["status"], "applied")
                self.assertEqual(
                    (root / ".sbtd/developer").read_bytes(), b"name=dev01\n"
                )
                self.assertEqual(file_contents(root / ".trellis"), old_tree)
                agents = (root / "AGENTS.md").read_text()
                self.assertIn("Foreign project rule.", agents)
                self.assertIn("Legacy route.", agents)
                self.assertTrue(
                    any(
                        path.read_bytes() == b"\x00retained-private-fixture\xff"
                        for path in vault.rglob("untracked.bin")
                    )
                )
                receipt = applied["migration"]["apply_receipt"]
                saved = [
                    path
                    for path in evidence.glob("*.json")
                    if json.loads(path.read_text()).get("apply_id")
                    == receipt["apply_id"]
                ]
                self.assertEqual(len(saved), 1)
                self.assertEqual(json.loads(saved[0].read_text()), receipt)
                before_retry = file_contents(root)
                retried, retry_code = apply_migration(
                    manifest_path,
                    previous_receipt_path=saved[0],
                    confirmed=True,
                    no_routing_approvals=True,
                )
                self.assertEqual(retry_code, 0, retried)
                self.assertEqual(retried["status"], "already-complete")
                self.assertEqual(file_contents(root), before_retry)
            self.assertEqual(list(home.iterdir()), [])

    def test_retry_preserves_original_unavailable_exit_code(self):
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
                    [root], vault, "fixture", None, tool_versions=runtime_versions()
                )
                manifest_path = evidence / "manifest.json"
                manifest_path.write_bytes(canonical_json_bytes(manifest))
                first, first_code = apply_migration(
                    manifest_path, confirmed=True, no_routing_approvals=True
                )
                self.assertEqual(first_code, 0, first)
                receipt_path = next(
                    path
                    for path in evidence.glob("apply-*.json")
                    if json.loads(path.read_text()).get("apply_id")
                    == first["migration"]["apply_receipt"]["apply_id"]
                )
                backup = next(vault.rglob("journal-1.md"))
                backup.unlink()
                retried, code = apply_migration(
                    manifest_path,
                    previous_receipt_path=receipt_path,
                    confirmed=True,
                    no_routing_approvals=True,
                )
            self.assertEqual(code, 3, retried)
            self.assertEqual(retried["status"], "failed")


if __name__ == "__main__":
    unittest.main()
