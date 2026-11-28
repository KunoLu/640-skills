from __future__ import annotations
# ruff: noqa: I001 -- local scripts require the explicit test path before import.

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard/scripts"
sys.path.insert(0, str(SCRIPTS))


from onboard_contracts import ContractError, canonical_json_bytes
from sbtd_deployment import execute_migration_deployment, load_deployment_context
from sbtd_migration import apply_migration, runtime_versions
from sbtd_migration_files import save_document, snapshot
from sbtd_migration_plan import plan_migration, validate_legacy_inputs
from sbtd_migration_verify import verify_migration
from sbtd_recovery import apply_recovery, plan_recovery

from tests.test_sbtd_migration_apply import file_contents, legacy_project
from tests.test_sbtd_migration_plan import _ownership_asset_context, _reader


class OmpDeploymentPlanTests(unittest.TestCase):
    def test_omp_migration_plan_binds_profile_sources_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = legacy_project(base, "project")
            home, vault = base / "home", base / "vault"
            agent = home / ".omp/profiles/work/agent"
            codex = home / ".codex"
            for path in (agent, codex, vault):
                path.mkdir(parents=True, mode=0o700)
            (agent / "config.yml").write_text(
                "enabledProviders: [codex]\n", encoding="utf-8"
            )
            (codex / "config.toml").write_text(
                '[mcp_servers.foreign]\ncommand = "/foreign/server"\n',
                encoding="utf-8",
            )
            environment = {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "OMP_PROFILE": "work",
                "CODEX_HOME": str(home / "ignored-codex-home"),
                "AGENT_SKILLS_DIR": str(home / ".agent/skills"),
            }
            before = file_contents(base)
            with mock.patch.dict(os.environ, environment):
                manifest = plan_migration(
                    [root],
                    vault,
                    "fixture",
                    None,
                    tool_versions=runtime_versions(),
                    deployment_mode="init",
                    deployment_platform="omp",
                )
                validate_legacy_inputs(manifest, _reader)
            self.assertEqual(file_contents(base), before)
            payload = manifest["payload"]
            self.assertEqual(payload["deployment"]["mode"], "init")
            self.assertEqual(payload["deployment"]["platform"], "omp")
            self.assertIn(
                str(codex / "config.toml"),
                {item["path"] for item in payload["deployment"]["inputs"]},
            )
            operations = [
                operation
                for operation in payload["shared_operations"]
                if operation["phase"] == "deploy"
            ]
            self.assertTrue(operations)
            self.assertFalse(
                any(
                    operation["selector"]
                    in {"graft-mcp", "graft-hooks", "graft-omp-mcp", "graft-agents"}
                    or operation["change"]["kind"] in {"build-graft", "configure-graft"}
                    for operation in operations
                )
            )
            self.assertTrue(
                any(
                    operation["change"]["kind"] in {"copy-file", "copy-directory"}
                    for operation in operations
                )
            )

    def test_project_only_omp_plan_declares_no_global_config(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = legacy_project(base, "project")
            home, vault = base / "home", base / "vault"
            home.mkdir(mode=0o700)
            vault.mkdir(mode=0o700)
            environment = {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "CODEX_HOME": str(home / ".codex"),
                "AGENT_SKILLS_DIR": str(home / ".agent/skills"),
            }
            before = file_contents(base)
            with mock.patch.dict(os.environ, environment):
                manifest = plan_migration(
                    [root],
                    vault,
                    "fixture",
                    None,
                    tool_versions=runtime_versions(),
                    deployment_mode="init-projects",
                    deployment_platform="omp",
                )
                validate_legacy_inputs(manifest, _reader)
            self.assertEqual(file_contents(base), before)
            payload = manifest["payload"]
            self.assertIsNone(payload["deployment"])
            self.assertFalse(
                any(
                    operation["phase"] == "deploy"
                    for operation in payload["shared_operations"]
                )
            )

    def test_inherited_source_drift_blocks_apply_before_any_write(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = legacy_project(base, "project")
            home, vault, evidence = (
                base / name for name in ("home", "vault", "evidence")
            )
            agent = home / ".omp/agent"
            codex = home / ".codex"
            for path in (agent, codex, vault, evidence):
                path.mkdir(parents=True, mode=0o700)
            (agent / "config.yml").write_text(
                "enabledProviders: [codex]\n", encoding="utf-8"
            )
            source = codex / "config.toml"
            source.write_text(
                '[mcp_servers.foreign]\ncommand = "/foreign/one"\n',
                encoding="utf-8",
            )
            environment = {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "CODEX_HOME": str(codex),
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
                    deployment_platform="omp",
                )
                manifest_path = evidence / "manifest.json"
                manifest_path.write_bytes(canonical_json_bytes(manifest))
                source.write_text(
                    '[mcp_servers.foreign]\ncommand = "/foreign/two"\n',
                    encoding="utf-8",
                )
                before = file_contents(base)
                with self.assertRaises(ContractError):
                    apply_migration(manifest_path, confirmed=True)
            self.assertEqual(file_contents(base), before)


    def test_full_omp_deployment_writes_active_rules_and_no_mcp_or_hooks(self):
        from onboard import GLOBAL_AGENTS_TEMPLATE

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = legacy_project(base, "project")
            home, vault, evidence = (
                base / name for name in ("home", "vault", "evidence")
            )
            for path in (home, vault, evidence):
                path.mkdir(mode=0o700)
            active = home / "active-omp" / "agent"
            active.mkdir(parents=True, mode=0o700)
            mcp = active / "mcp.json"
            foreign_mcp = b'{"mcpServers": {"foreign": {"command": "existing-server", "args": []}}}\n'
            mcp.write_bytes(foreign_mcp)
            environment = {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "CODEX_HOME": str(home / ".codex"),
                "PI_CODING_AGENT_DIR": str(active),
                "OMP_PROFILE": "default",
                "PI_PROFILE": "default",
                "PI_CONFIG_DIR": ".omp",
                "CLAUDE_CONFIG_DIR": str(home / ".claude"),
                "AGENT_SKILLS_DIR": str(home / ".agent/skills"),
                "GIT_CONFIG_NOSYSTEM": "1",
            }
            for command in (
                ["git", "init", "-b", "main", str(root)],
                ["git", "-C", str(root), "config", "user.email", "fixture@test"],
                ["git", "-C", str(root), "config", "user.name", "fixture"],
                ["git", "-C", str(root), "add", "-A"],
                ["git", "-C", str(root), "commit", "-m", "legacy state"],
            ):
                subprocess.run(
                    command,
                    check=True,
                    capture_output=True,
                    env={**os.environ, **environment},
                )
            with mock.patch.dict(os.environ, environment):
                manifest = plan_migration(
                    [root],
                    vault,
                    "fixture",
                    None,
                    tool_versions=runtime_versions(),
                    deployment_mode="init",
                    deployment_platform="omp",
                )
                manifest_path = evidence / "manifest.json"
                manifest_path.write_bytes(canonical_json_bytes(manifest))
                applied, code = apply_migration(
                    manifest_path, confirmed=True, no_routing_approvals=True
                )
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
                result, code = execute_migration_deployment(context)
                self.assertEqual(code, 0, result)
                self.assertEqual(result["status"], "succeeded")
                refs = result["projects"][0]["report_refs"]
                self.assertTrue(refs)
                self.assertTrue(all(Path(ref["path"]).is_file() and Path(ref["path"]).stat().st_size > 0 for ref in refs))
                self.assertEqual((active / "AGENTS.md").read_bytes(), GLOBAL_AGENTS_TEMPLATE.read_bytes())
                self.assertEqual(mcp.read_bytes(), foreign_mcp)
                self.assertFalse((home / ".omp/agent/AGENTS.md").exists())
                self.assertFalse((home / ".omp/agent/mcp.json").exists())
                self.assertFalse((home / ".codex/hooks.json").exists())
                installed = [
                    Path(operation["target"])
                    for operation in manifest["payload"]["shared_operations"]
                    if operation["phase"] == "deploy"
                    and operation["change"]["kind"] == "copy-file"
                ]
                self.assertTrue(installed)
                self.assertTrue(all(path.is_file() for path in installed))
                self.assertTrue(output.is_file())


def _legacy_project_with_host_configs(base):
    """Legacy project carrying ownership-pinned generated host configs.

    Mirrors the production batch whose approved manifest removes the
    project's recorded ``.codex/config.toml`` and ``.claude/settings.json``
    during apply; both paths are sealed OMP deployment inputs.
    """
    root = legacy_project(base, "project")
    host_configs = {
        ".codex/config.toml": b'model = "recorded"\n',
        ".claude/settings.json": b'{"legacyRouting": true}\n',
    }
    (root / ".claude").mkdir()
    owned = {
        ".codex/agents/trellis-implement.toml": (
            root / ".codex/agents/trellis-implement.toml"
        ).read_bytes(),
        **host_configs,
    }
    for relative, raw in host_configs.items():
        (root / relative).write_bytes(raw)
    (root / ".trellis/.template-hashes.json").write_text(
        json.dumps(
            {
                "__version": 2,
                "hashes": {
                    name: hashlib.sha256(raw).hexdigest()
                    for name, raw in owned.items()
                },
            }
        )
    )
    return root, host_configs


def _proven_input_environment(home, host_configs, base):
    environment = {
        "HOME": str(home),
        "USERPROFILE": str(home),
        "CODEX_HOME": str(home / ".codex"),
        "AGENT_SKILLS_DIR": str(home / ".agent/skills"),
    }
    asset = _ownership_asset_context(
        base,
        None,
        config_pins={
            relative: [hashlib.sha256(raw).hexdigest()]
            for relative, raw in host_configs.items()
        },
    )
    return environment, asset


class OmpDeploymentProvenInputTests(unittest.TestCase):
    """Bound-stage-proof recognition for sealed OMP configuration inputs.

    An approved apply removal changes a sealed deployment input between
    planning and deployment; revalidation must recognize exactly that
    proven change while every unapproved, unbound or mutated state keeps
    the drift rejection before any write.
    """

    def setUp(self):
        overrides = mock.patch.dict(
            os.environ,
            {
                name: ""
                for name in (
                    "OMP_PROFILE",
                    "PI_PROFILE",
                    "PI_CONFIG_DIR",
                    "PI_CODING_AGENT_DIR",
                    "CLAUDE_CONFIG_DIR",
                    "XDG_DATA_HOME",
                )
            },
        )
        overrides.start()
        self.addCleanup(overrides.stop)

    def _plan_and_apply(self, root, vault, evidence, asset, environment):
        with mock.patch.dict(os.environ, environment), asset:
            manifest = plan_migration(
                [root],
                vault,
                "fixture",
                None,
                tool_versions=runtime_versions(),
                deployment_mode="init",
                deployment_platform="omp",
            )
            manifest_path = evidence / "manifest.json"
            manifest_path.write_bytes(canonical_json_bytes(manifest))
            applied, code = apply_migration(
                manifest_path, confirmed=True, no_routing_approvals=True
            )
            self.assertEqual(code, 0, applied)
        receipt = applied["migration"]["apply_receipt"]
        apply_path = evidence / ("apply-" + receipt["apply_id"] + ".json")
        return manifest, manifest_path, apply_path, receipt

    def _deploy_context(self, manifest_path, apply_path, output, root):
        return load_deployment_context(
            manifest_path,
            apply_path,
            output,
            previous_path=None,
            mode="init",
            roots=[root],
            hooks_authorized=False,
        )

    def test_apply_proven_host_config_removal_deploys_and_verifies(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root, host_configs = _legacy_project_with_host_configs(base)
            home, vault, evidence = (
                base / name for name in ("home", "vault", "evidence")
            )
            for path in (home, vault, evidence):
                path.mkdir(mode=0o700)
            environment, asset = _proven_input_environment(home, host_configs, base)
            with mock.patch.dict(os.environ, environment), asset:
                manifest = plan_migration(
                    [root],
                    vault,
                    "fixture",
                    None,
                    tool_versions=runtime_versions(),
                    deployment_mode="init",
                    deployment_platform="omp",
                )
                sealed = {
                    item["path"]: item["state"]
                    for item in manifest["payload"]["deployment"]["inputs"]
                }
                for relative in host_configs:
                    self.assertEqual(sealed[str(root / relative)]["type"], "file")
                manifest_path = evidence / "manifest.json"
                manifest_path.write_bytes(canonical_json_bytes(manifest))
                applied, code = apply_migration(
                    manifest_path, confirmed=True, no_routing_approvals=True
                )
                self.assertEqual(code, 0, applied)
                for relative in host_configs:
                    self.assertFalse((root / relative).exists())
                receipt = applied["migration"]["apply_receipt"]
                operations = {
                    operation["resource_id"]: operation
                    for operation in manifest["payload"]["projects"][0][
                        "private_operations"
                    ]
                }
                proven_targets = {str(root / relative) for relative in host_configs}
                proven = [
                    result
                    for result in receipt["payload"]["projects"][0][
                        "private_results"
                    ]
                    if operations[result["resource_id"]]["target"] in proven_targets
                ]
                self.assertEqual(len(proven), len(host_configs))
                for result in proven:
                    self.assertEqual(result["status"], "succeeded")
                    self.assertEqual(
                        result["after"], {"type": "absent", "checksum": None}
                    )
                    self.assertTrue(Path(result["backup_ref"]["path"]).is_file())
                apply_path = evidence / ("apply-" + receipt["apply_id"] + ".json")

                # A bound retry receipt preserves the proven removals and
                # must pass the same revalidation.
                retried, retry_code = apply_migration(
                    manifest_path,
                    previous_receipt_path=apply_path,
                    confirmed=True,
                    no_routing_approvals=True,
                )
                self.assertEqual(retry_code, 0, retried)
                self.assertEqual(retried["status"], "already-complete")

                context = self._deploy_context(
                    manifest_path, apply_path, evidence / "deployment.json", root
                )
                result, code = execute_migration_deployment(context)
                self.assertEqual(code, 0, result)
                self.assertEqual(result["status"], "succeeded")
                for relative in host_configs:
                    self.assertFalse((root / relative).exists())
                verified, verify_code = verify_migration(
                    manifest_path, apply_path, evidence / "deployment.json"
                )
                self.assertEqual(verify_code, 0, verified)

    def test_unproven_input_removal_refuses_deploy_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = legacy_project(base, "project")
            home, vault, evidence = (
                base / name for name in ("home", "vault", "evidence")
            )
            agent = home / ".omp/agent"
            codex = home / ".codex"
            for path in (agent, codex, vault, evidence):
                path.mkdir(parents=True, mode=0o700)
            (agent / "config.yml").write_text(
                "enabledProviders: [codex]\n", encoding="utf-8"
            )
            source = codex / "config.toml"
            source.write_text(
                '[mcp_servers.foreign]\ncommand = "/foreign/server"\n',
                encoding="utf-8",
            )
            environment = {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "CODEX_HOME": str(codex),
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
                    deployment_platform="omp",
                )
                self.assertIn(
                    str(source),
                    {
                        item["path"]
                        for item in manifest["payload"]["deployment"]["inputs"]
                    },
                )
                manifest_path = evidence / "manifest.json"
                manifest_path.write_bytes(canonical_json_bytes(manifest))
                applied, code = apply_migration(
                    manifest_path, confirmed=True, no_routing_approvals=True
                )
                self.assertEqual(code, 0, applied)
                receipt = applied["migration"]["apply_receipt"]
                # Nobody approved or recorded touching this sealed input.
                source.unlink()
                with self.assertRaises(ContractError) as drift:
                    self._deploy_context(
                        manifest_path,
                        evidence / ("apply-" + receipt["apply_id"] + ".json"),
                        evidence / "deployment.json",
                        root,
                    )
            self.assertEqual(drift.exception.code, "state-conflict")
            self.assertIn("drifted", str(drift.exception))
            self.assertFalse((evidence / "deployment.json").exists())
            self.assertFalse((agent / "mcp.json").exists())

    def test_mutated_proven_input_refuses_deploy_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root, host_configs = _legacy_project_with_host_configs(base)
            home, vault, evidence = (
                base / name for name in ("home", "vault", "evidence")
            )
            for path in (home, vault, evidence):
                path.mkdir(mode=0o700)
            environment, asset = _proven_input_environment(home, host_configs, base)
            _manifest, manifest_path, apply_path, _receipt = self._plan_and_apply(
                root, vault, evidence, asset, environment
            )
            with mock.patch.dict(os.environ, environment), asset:
                # The proven outcome is absent; unapproved new bytes are
                # refused by the original-reference and input closures.
                (root / ".codex/config.toml").write_bytes(b'model = "unapproved"\n')
                with self.assertRaises(ContractError) as drift:
                    self._deploy_context(
                        manifest_path, apply_path, evidence / "deployment.json", root
                    )
            self.assertEqual(drift.exception.code, "state-conflict")
            self.assertFalse((evidence / "deployment.json").exists())
            self.assertFalse((home / ".omp/agent/mcp.json").exists())

    def test_mutated_retained_original_refuses_deploy_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root, host_configs = _legacy_project_with_host_configs(base)
            home, vault, evidence = (
                base / name for name in ("home", "vault", "evidence")
            )
            for path in (home, vault, evidence):
                path.mkdir(mode=0o700)
            environment, asset = _proven_input_environment(home, host_configs, base)
            manifest, manifest_path, apply_path, receipt = self._plan_and_apply(
                root, vault, evidence, asset, environment
            )
            operations = {
                operation["resource_id"]: operation
                for operation in manifest["payload"]["projects"][0][
                    "private_operations"
                ]
            }
            removal = next(
                result
                for result in receipt["payload"]["projects"][0]["private_results"]
                if operations[result["resource_id"]]["target"]
                == str(root / ".codex/config.toml")
            )
            with mock.patch.dict(os.environ, environment), asset:
                # A proven change requires its intact retained original.
                Path(removal["backup_ref"]["path"]).write_bytes(b"mutated\n")
                with self.assertRaises(ContractError) as drift:
                    self._deploy_context(
                        manifest_path, apply_path, evidence / "deployment.json", root
                    )
            self.assertEqual(drift.exception.code, "state-conflict")
            self.assertFalse((evidence / "deployment.json").exists())
            self.assertFalse((home / ".omp/agent/mcp.json").exists())

    def test_recovery_restores_proven_removed_host_configs(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root, host_configs = _legacy_project_with_host_configs(base)
            home, vault, evidence = (
                base / name for name in ("home", "vault", "evidence")
            )
            for path in (home, vault, evidence):
                path.mkdir(mode=0o700)
            environment, asset = _proven_input_environment(home, host_configs, base)
            _manifest, manifest_path, apply_path, _receipt = self._plan_and_apply(
                root, vault, evidence, asset, environment
            )
            with mock.patch.dict(os.environ, environment), asset:
                planned, plan_code = plan_recovery(
                    manifest_path, apply_receipt_path=apply_path
                )
                self.assertEqual(plan_code, 0, planned)
                plan = planned["recovery"]["plan"]
                plan_path = evidence / "recovery-plan.json"
                save_document(plan_path, plan, private_root=evidence)
                restored, recovery_code = apply_recovery(
                    plan_path, confirm_recovery=plan["plan_id"]
                )
                self.assertEqual(recovery_code, 0, restored)
                for relative, raw in host_configs.items():
                    self.assertEqual((root / relative).read_bytes(), raw)

if __name__ == "__main__":
    unittest.main()
