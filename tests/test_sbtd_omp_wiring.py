from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard/scripts"
sys.path.insert(0, str(SCRIPTS))

from onboard_contracts import ContractError
from sbtd_omp_sources import analyze_omp_sources
from sbtd_omp_wiring import (
    analyze_omp_configuration,
    desired_omp_server,
    omp_mcp_candidate,
)

BINDING = {
    "root": "/private/project",
    "node": "/private/node",
    "cli": "/private/graft/dist/cli.js",
    "python": "/private/python",
    "launcher": "/private/onboard/scripts/sbtd_graft_entry.py",
}


class OmpMcpCandidateTests(unittest.TestCase):
    def test_inherited_equivalent_connection_is_idempotent_without_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            desired = {
                "type": "stdio",
                "command": BINDING["python"],
                "args": [
                    "-E",
                    "-s",
                    BINDING["launcher"],
                    "mcp",
                    "--root",
                    BINDING["root"],
                    "--node",
                    BINDING["node"],
                    "--entry",
                    BINDING["cli"],
                ],
                "cwd": BINDING["root"],
                "env": {"DO_NOT_TRACK": "1", "DNT": "1"},
            }
            inherited = base / ".codex/config.toml"
            inherited.parent.mkdir(parents=True)
            inherited.write_text(
                "[mcp_servers.sbtd-graft]\n"
                f'command = "{desired["command"]}"\n'
                "args = "
                + json.dumps(desired["args"])
                + "\n"
                f'cwd = "{desired["cwd"]}"\n'
                '[mcp_servers.sbtd-graft.env]\nDO_NOT_TRACK = "1"\nDNT = "1"\n',
                encoding="utf-8",
            )
            target = base / ".omp/mcp.json"
            target.parent.mkdir(parents=True)
            target.write_text('{"mcpServers": {}}\n', encoding="utf-8")
            analysis = analyze_omp_configuration(
                target,
                [BINDING],
                [
                    {
                        "source": "codex-user",
                        "enabled": True,
                        "servers": {"sbtd-graft": desired},
                    }
                ],
            )
            candidate = omp_mcp_candidate(target.read_bytes(), analysis)
            self.assertEqual(candidate, target.read_bytes())
            self.assertEqual(analysis["writes"], [])
            self.assertEqual(len(analysis["inherited_matches"]), 1)

    def test_project_disabled_source_blocks_without_rewriting_target(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            target = base / ".omp/mcp.json"
            before = b'{"mcpServers": {}}\n'
            target.parent.mkdir(parents=True)
            target.write_bytes(before)
            with self.assertRaises(ContractError) as failure:
                analyze_omp_configuration(
                    target,
                    [BINDING],
                    [
                        {
                            "source": "codex-project",
                            "enabled": False,
                            "servers": {"sbtd-graft": {"command": "/foreign"}},
                        }
                    ],
                )
            self.assertEqual(failure.exception.code, "ownership-conflict")
            self.assertEqual(target.read_bytes(), before)

    def test_malformed_or_dynamic_configuration_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            for index, raw in enumerate(
                (
                    b'{"mcpServers":}',
                    b'{"mcpServers": {"sbtd-graft": "not-object"}}',
                    b'{"mcpServers": {"sbtd-graft": {"command": "${SBTD_LAUNCHER}"}}}',
                )
            ):
                target = base / str(index) / ".omp/mcp.json"
                target.parent.mkdir(parents=True)
                target.write_bytes(raw)
                before = {
                    str(path.relative_to(base)): path.read_bytes()
                    for path in base.rglob("*")
                    if path.is_file()
                }
                with self.subTest(index=index), self.assertRaises(ContractError):
                    analyze_omp_configuration(target, [BINDING], [])
                after = {
                    str(path.relative_to(base)): path.read_bytes()
                    for path in base.rglob("*")
                    if path.is_file()
                }
                self.assertEqual(after, before)


class OmpSourceAnalysisTests(unittest.TestCase):
    def test_named_profile_ignores_agent_override_and_keeps_reads_readonly(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            home = base / "home"
            root = base / "project"
            home.mkdir()
            root.mkdir()
            before = {
                str(path.relative_to(base)): path.read_bytes()
                for path in base.rglob("*")
                if path.is_file()
            }
            result = analyze_omp_sources(
                [root],
                [BINDING],
                home=home,
                environ={
                    "OMP_PROFILE": "work",
                    "PI_CODING_AGENT_DIR": str(base / "ignored-agent"),
                },
            )
            self.assertEqual(
                Path(result["target"]),
                home / ".omp/profiles/work/agent/mcp.json",
            )
            self.assertEqual(result["analysis"]["writes"][0]["server"]["type"], "stdio")
            after = {
                str(path.relative_to(base)): path.read_bytes()
                for path in base.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)

    def test_default_profile_honors_agent_override_and_codex_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            home = base / "home"
            root = base / "project"
            agent = base / "custom-agent"
            codex = home / ".codex"
            for path in (agent, codex, root):
                path.mkdir(parents=True)
            desired = desired_omp_server(BINDING)
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
            result = analyze_omp_sources(
                [root],
                [BINDING],
                home=home,
                environ={"PI_CODING_AGENT_DIR": str(agent)},
            )
            self.assertEqual(Path(result["target"]), agent / "mcp.json")
            self.assertEqual(result["analysis"]["writes"], [])
            self.assertEqual(
                [match["source"] for match in result["analysis"]["inherited_matches"]],
                ["codex-user"],
            )
            self.assertIn(
                {"path": str(codex / "config.toml"), "state": "file"},
                [
                    {"path": item["path"], "state": item["state"]["type"]}
                    for item in result["inputs"]
                ],
            )

    def test_project_disabled_codex_source_blocks_without_executing_it(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            home = base / "home"
            root = base / "project"
            config = root / ".codex/config.toml"
            config.parent.mkdir(parents=True)
            home.mkdir()
            config.write_text(
                "[mcp_servers.sbtd-graft]\n"
                'enabled = false\ncommand = "/definitely/not/executed"\n',
                encoding="utf-8",
            )
            before = config.read_bytes()
            with self.assertRaises(ContractError) as failure:
                analyze_omp_sources([root], [BINDING], home=home, environ={})
            self.assertEqual(failure.exception.code, "ownership-conflict")
            self.assertEqual(config.read_bytes(), before)


    def test_dynamic_overlay_or_project_provider_settings_block_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            home = base / "home"
            root = base / "project"
            home.mkdir()
            (root / ".omp").mkdir(parents=True)
            (root / ".omp/config.yml").write_text(
                "enabledProviders: [codex]\n", encoding="utf-8"
            )
            before = {
                str(path.relative_to(base)): path.read_bytes()
                for path in base.rglob("*")
                if path.is_file()
            }
            with self.assertRaises(ContractError) as project_failure:
                analyze_omp_sources([root], [BINDING], home=home, environ={})
            self.assertEqual(project_failure.exception.code, "invalid-config")
            with self.assertRaises(ContractError) as overlay_failure:
                analyze_omp_sources(
                    [root],
                    [BINDING],
                    home=home,
                    environ={"PI_CONFIG_FILES": "/private/unknown-overlay.yml"},
                )
            self.assertEqual(overlay_failure.exception.code, "invalid-config")
            after = {
                str(path.relative_to(base)): path.read_bytes()
                for path in base.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)

    def test_legacy_agent_settings_are_not_silently_reinterpreted(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            home = base / "home"
            root = base / "project"
            agent = home / ".omp/agent"
            agent.mkdir(parents=True)
            root.mkdir()
            legacy = agent / "settings.json"
            legacy.write_text('{"enabledProviders":["codex"]}', encoding="utf-8")
            before = legacy.read_bytes()
            with self.assertRaises(ContractError) as failure:
                analyze_omp_sources([root], [BINDING], home=home, environ={})
            self.assertEqual(failure.exception.code, "invalid-config")
            self.assertEqual(legacy.read_bytes(), before)

if __name__ == "__main__":
    unittest.main()
