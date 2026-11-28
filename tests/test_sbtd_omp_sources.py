from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard/scripts"
sys.path.insert(0, str(SCRIPTS))

from onboard_contracts import ContractError
from sbtd_omp_sources import discover_omp_sources


class OmpSourceDiscoveryTests(unittest.TestCase):
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
            result = discover_omp_sources(
                [root],
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
            after = {
                str(path.relative_to(base)): path.read_bytes()
                for path in base.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)

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
                discover_omp_sources([root], home=home, environ={})
            self.assertEqual(project_failure.exception.code, "invalid-config")
            with self.assertRaises(ContractError) as overlay_failure:
                discover_omp_sources(
                    [root],
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
                discover_omp_sources([root], home=home, environ={})
            self.assertEqual(failure.exception.code, "invalid-config")
            self.assertEqual(legacy.read_bytes(), before)

    def test_native_provider_disabled_blocks_deployment(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            home = base / "home"
            root = base / "project"
            agent = home / ".omp/agent"
            agent.mkdir(parents=True)
            root.mkdir()
            (agent / "config.yml").write_text(
                "disabledProviders: [native]\n", encoding="utf-8"
            )
            with self.assertRaises(ContractError) as failure:
                discover_omp_sources([root], home=home, environ={})
            self.assertEqual(failure.exception.code, "invalid-config")

    def test_project_and_claude_disabled_extensions_block_analysis(self):
        cases = (
            (".omp/config.yml", "disabledExtensions: [mcp:fixture]\n"),
            (".omp/settings.json", '{"disabledExtensions":["mcp:fixture"]}'),
            (".claude/settings.json", '{"disabledExtensions":["mcp:fixture"]}'),
        )
        for relative, content in cases:
            with (
                self.subTest(relative=relative),
                tempfile.TemporaryDirectory() as directory,
            ):
                base = Path(directory).resolve()
                home = base / "home"
                root = base / "project"
                home.mkdir()
                target = root / relative
                target.parent.mkdir(parents=True)
                target.write_text(content, encoding="utf-8")
                with self.assertRaises(ContractError) as failure:
                    discover_omp_sources([root], home=home, environ={})
                self.assertEqual(failure.exception.code, "invalid-config")

    def test_enabled_claude_user_disabled_extensions_block_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            home = base / "home"
            root = base / "project"
            agent = home / ".omp/agent"
            claude = home / ".claude"
            agent.mkdir(parents=True)
            claude.mkdir(parents=True)
            root.mkdir()
            (agent / "config.yml").write_text(
                "enabledProviders: [claude]\n", encoding="utf-8"
            )
            (claude / "settings.json").write_text(
                '{"disabledExtensions":["mcp:fixture"]}', encoding="utf-8"
            )
            with self.assertRaises(ContractError) as failure:
                discover_omp_sources([root], home=home, environ={})
            self.assertEqual(failure.exception.code, "invalid-config")

    def test_enabled_claude_plugin_sources_block_without_rewriting_them(self):
        for provider in ("claude", "omp"):
            with (
                self.subTest(provider=provider),
                tempfile.TemporaryDirectory() as directory,
            ):
                base = Path(directory).resolve()
                home = base / "home"
                root = base / "project"
                agent = home / ".omp/agent"
                plugins = (
                    home / ".claude/plugins/installed_plugins.json"
                    if provider == "claude"
                    else home / ".omp/plugins/installed_plugins.json"
                )
                agent.mkdir(parents=True)
                root.mkdir()
                (agent / "config.yml").write_text(
                    "enabledProviders: [claude-plugins]\n", encoding="utf-8"
                )
                plugins.parent.mkdir(parents=True)
                original = b'{"plugins": {"fixture": []}}\n'
                plugins.write_bytes(original)
                with self.assertRaises(ContractError) as failure:
                    discover_omp_sources([root], home=home, environ={})
                self.assertEqual(failure.exception.code, "invalid-config")
                self.assertEqual(plugins.read_bytes(), original)

    def test_plugin_discovery_covers_default_override_xdg_and_project_registries(self):
        for source in (
            "default",
            "claude",
            "override",
            "xdg",
            "profile",
            "project",
            "ancestor",
        ):
            with (
                self.subTest(source=source),
                tempfile.TemporaryDirectory() as directory,
            ):
                base = Path(directory).resolve()
                home = base / "home"
                root = base / "project"
                agent = home / ".omp/agent"
                agent.mkdir(parents=True)
                root.mkdir()
                environment = {}
                plugins = home / ".omp/plugins/installed_plugins.json"
                if source == "claude":
                    (agent / "config.yml").write_text("enabledProviders: [claude]\n")
                    plugins = home / ".claude/plugins/installed_plugins.json"
                elif source == "override":
                    environment["CLAUDE_CONFIG_DIR"] = str(base / "claude-home")
                    plugins = base / "claude-home/plugins/installed_plugins.json"
                elif source == "xdg":
                    environment["XDG_DATA_HOME"] = str(base / "xdg")
                    plugins = base / "xdg/omp/plugins/installed_plugins.json"
                elif source == "profile":
                    environment["OMP_PROFILE"] = "work"
                    plugins = home / ".omp/profiles/work/plugins/installed_plugins.json"
                elif source == "project":
                    plugins = root / ".omp/plugins/installed_plugins.json"
                elif source == "ancestor":
                    plugins = base / ".omp/plugins/installed_plugins.json"
                plugins.parent.mkdir(parents=True)
                original = b'{"plugins":{"fixture@marketplace":[{"installPath":"/synthetic/plugin"}]}}'
                plugins.write_bytes(original)
                with self.assertRaises(ContractError) as failure:
                    discover_omp_sources(
                        [root], home=home, environ=environment
                    )
                self.assertEqual(failure.exception.code, "invalid-config")
                self.assertEqual(plugins.read_bytes(), original)
                self.assertFalse((agent / "mcp.json").exists())

