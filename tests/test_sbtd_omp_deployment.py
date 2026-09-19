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
from sbtd_graft_deployment import execute_migration_deployment, load_deployment_context
from sbtd_migration import apply_migration, runtime_versions
from sbtd_migration_files import snapshot
from sbtd_migration_plan import plan_migration, validate_legacy_inputs

from tests.test_sbtd_migration_apply import file_contents, legacy_project
from tests.test_sbtd_migration_plan import _reader


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
            self.assertEqual(
                {
                    (operation["target"], operation["selector"])
                    for operation in operations
                    if operation["selector"] == "graft-omp-mcp"
                },
                {(str(agent / "mcp.json"), "graft-omp-mcp")},
            )
            self.assertFalse(
                any(
                    operation["selector"] in {"graft-mcp", "graft-hooks"}
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
            self.assertEqual(
                payload["deployment"],
                {"mode": "init-projects", "platform": "omp", "inputs": []},
            )
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

    def test_omp_render_uses_active_profile_sources_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            home = base / "home"
            root = legacy_project(base, "project")
            agent = home / ".omp/profiles/work/agent"
            agent.mkdir(parents=True)
            target = agent / "mcp.json"
            binding = {
                "root": str(root),
                "node": "/fixture/node",
                "cli": "/fixture/graft/dist/cli.js",
                "python": "/fixture/python",
                "launcher": str(
                    Path(__file__).resolve().parents[1]
                    / "sbtd-workflow-onboard/scripts/sbtd_graft_entry.py"
                ),
            }
            operation = {
                "selector": "graft-omp-mcp",
                "target": str(target),
            }
            environment = {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "OMP_PROFILE": "work",
                "CODEX_HOME": str(home / ".codex"),
            }
            before = file_contents(base)
            with mock.patch.dict(os.environ, environment):
                from sbtd_graft_deployment import render_configuration

                candidate = render_configuration(operation, b"", [binding])
            self.assertEqual(file_contents(base), before)
            servers = __import__("json").loads(candidate)["mcpServers"]
            self.assertEqual(len(servers), 1)
            server = next(iter(servers.values()))
            self.assertEqual(server["command"], binding["python"])
            self.assertEqual(server["cwd"], str(root))
            self.assertEqual(server["env"], {"DO_NOT_TRACK": "1", "DNT": "1"})

    def test_inherited_equivalent_connection_leaves_absent_omp_config_unwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = legacy_project(base, "project")
            home = base / "home"
            agent = home / ".omp/agent"
            codex = home / ".codex"
            private = base / "private"
            for path in (agent, codex, private):
                path.mkdir(parents=True, mode=0o700)
            binding = {
                "root": str(root),
                "node": "/fixture/node",
                "cli": "/fixture/cli.js",
                "python": "/fixture/python",
                "launcher": str(
                    Path(__file__).resolve().parents[1]
                    / "sbtd-workflow-onboard/scripts/sbtd_graft_entry.py"
                ),
            }
            from sbtd_omp_wiring import desired_omp_server

            desired = desired_omp_server(binding)
            (agent / "config.yml").write_text(
                "enabledProviders: [codex]\n", encoding="utf-8"
            )
            (codex / "config.toml").write_text(
                "[mcp_servers.sbtd-graft]\n"
                f'command = "{desired["command"]}"\n'
                "args = "
                + json.dumps(desired["args"])
                + "\n"
                f'cwd = "{desired["cwd"]}"\n'
                '[mcp_servers.sbtd-graft.env]\nDO_NOT_TRACK = "1"\nDNT = "1"\n',
                encoding="utf-8",
            )
            target = agent / "mcp.json"
            policy = (
                Path(__file__).resolve().parents[1]
                / "sbtd-workflow-onboard/assets/graft-build-policy.json"
            )
            operation = {
                "phase": "deploy",
                "resource_id": "fixture-resource",
                "operation_id": "fixture-operation",
                "selector": "graft-omp-mcp",
                "target": str(target),
                "change": {
                    "kind": "configure-graft",
                    "source_ref": {
                        "path": str(policy),
                        "state": {
                            "type": "file",
                            "checksum": __import__(
                                "onboard_contracts"
                            ).GRAFT_BUILD_POLICY_SHA256,
                        },
                    },
                },
                "dependent_projects": [str(root)],
            }
            environment = {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "CODEX_HOME": str(codex),
            }
            with mock.patch.dict(os.environ, environment):
                from sbtd_graft_deployment import execute_resource

                result = execute_resource(
                    operation,
                    expected={"type": "absent", "checksum": None},
                    root=agent,
                    private_root=private,
                    backup_path=private / "backup",
                    bindings=[binding],
                    runtime={},
                    launcher_state=snapshot(
                        Path(__file__).resolve().parents[1]
                        / "sbtd-workflow-onboard"
                    ),
                )
            self.assertEqual(result["status"], "succeeded", result)
            self.assertEqual(result["after"], {"type": "absent", "checksum": None})
            self.assertFalse(target.exists())


    def test_full_omp_deployment_writes_active_mcp_and_no_host_hooks(self):
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
                runtime = {
                    "node": "/fixture/node",
                    "cli": "/fixture/cli.js",
                    "python": "/fixture/python",
                }

                def graph(project, _runtime):
                    (project / "graft").mkdir()
                    (project / "graft/fixture").write_bytes(b"synthetic native output")

                def smoke(project, smoke_runtime, evidence_dir):
                    source_ref, head = manifest["payload"]["projects"][0][
                        "source_ref"
                    ], manifest["payload"]["projects"][0]["head"]
                    moment = datetime.now(timezone.utc).isoformat()
                    report = evidence_dir / "api-report-omp-smoke.json"
                    summary = evidence_dir / "api-report-omp-smoke.md"
                    envelope_path = evidence_dir / "api-report-omp-smoke.evidence.json"
                    raw = {
                        "repositoryKey": hashlib.sha256(
                            str(project).encode()
                        ).hexdigest(),
                        "projectRoot": str(project),
                        "sourceRef": source_ref,
                        "sourceCommit": head,
                        "worktreeState": "dirty",
                        "sourceRevision": "dirty",
                        "evidenceSource": "developer-local",
                        "trigger": "manual",
                        "environmentAlignment": "verified",
                        "evidencePublication": "local-only",
                        "e2eMode": "smoke-only",
                        "mockStrategy": "none",
                        "startedAt": moment,
                        "finishedAt": moment,
                        "command": [
                            smoke_runtime["node"],
                            smoke_runtime["cli"],
                            "check",
                            ".",
                            "--json",
                        ],
                        "stdout": "synthetic native output",
                        "stderr": "",
                        "exitCode": 0,
                        "processExitCode": 0,
                        "timedOut": False,
                    }
                    report.write_text(json.dumps(raw), encoding="utf-8")
                    summary.write_text("合成 smoke 摘要。\n", encoding="utf-8")
                    envelope = {
                        "schemaVersion": 1,
                        "runId": "omp-smoke",
                        "createdAt": moment,
                        "evidenceSource": "developer-local",
                        "trigger": "manual",
                        "repository": {
                            "repositoryKey": raw["repositoryKey"],
                            "sourceRef": source_ref,
                            "sourceCommit": head,
                            "worktreeState": "dirty",
                        },
                        "sourceRevision": "dirty",
                        "environmentAlignment": "verified",
                        "e2eMode": "smoke-only",
                        "mockStrategy": "none",
                        "featureSources": [],
                        "reports": [
                            {
                                "testType": "api",
                                "path": str(report),
                                "summaryMd": str(summary),
                                "sha256": hashlib.sha256(
                                    report.read_bytes()
                                ).hexdigest(),
                                "status": "passed",
                                "mode": "smoke-only",
                            }
                        ],
                        "evidencePublication": "local-only",
                        "secretsRedacted": True,
                    }
                    envelope_path.write_text(json.dumps(envelope), encoding="utf-8")
                    return [
                        {"path": str(path), "state": snapshot(path)}
                        for path in (report, envelope_path, summary)
                    ]

                with (
                    mock.patch(
                        "sbtd_graft_deployment.verified_runtime", return_value=runtime
                    ),
                    mock.patch(
                        "sbtd_graft_deployment.build_project_graph", side_effect=graph
                    ),
                    mock.patch(
                        "sbtd_graft_deployment.run_project_smoke", side_effect=smoke
                    ),
                ):
                    result, code = execute_migration_deployment(context)
                self.assertEqual(code, 0, result)
                self.assertEqual(result["status"], "succeeded")
                target = home / ".omp/agent/mcp.json"
                servers = json.loads(target.read_text(encoding="utf-8"))["mcpServers"]
                self.assertEqual(len(servers), 1)
                server = next(iter(servers.values()))
                self.assertEqual(server["command"], runtime["python"])
                self.assertEqual(
                    server["args"][2],
                    str(
                        home
                        / ".agent/skills/sbtd-workflow-onboard/scripts/sbtd_graft_entry.py"
                    ),
                )
                self.assertEqual(server["cwd"], str(root))
                self.assertFalse((home / ".codex/hooks.json").exists())
                self.assertFalse((home / ".codex/config.toml").exists())
                saved = result["deploymentEvidence"]["evidence"]["payload"]
                self.assertEqual(saved["status"], "succeeded")
                self.assertTrue(output.is_file())


if __name__ == "__main__":
    unittest.main()
