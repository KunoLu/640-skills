from __future__ import annotations

import argparse
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sbtd-workflow-onboard" / "scripts"))

import onboard
import sbtd_language_tooling as tooling


def make_executable(path: Path) -> None:
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class LanguageDetectionTests(unittest.TestCase):
    def test_python_pyproject_alone_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
            detected = tooling.detect_project_languages(root)
            self.assertEqual([item["language"] for item in detected], ["python"])
            self.assertEqual(detected[0]["markers"], ["pyproject.toml"])

    def test_python_source_file_alone_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "main.py").write_text("print(1)\n", encoding="utf-8")
            detected = tooling.detect_project_languages(root)
            self.assertEqual([item["language"] for item in detected], ["python"])

    def test_rust_requires_manifest_and_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
            self.assertEqual(tooling.detect_project_languages(root), [])
            (root / "src").mkdir()
            (root / "src" / "lib.rs").write_text("", encoding="utf-8")
            detected = tooling.detect_project_languages(root)
            self.assertEqual([item["language"] for item in detected], ["rust"])

    def test_typescript_requires_package_tsconfig_and_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text("{}\n", encoding="utf-8")
            (root / "index.ts").write_text("", encoding="utf-8")
            self.assertEqual(tooling.detect_project_languages(root), [])
            (root / "tsconfig.json").write_text("{}\n", encoding="utf-8")
            detected = tooling.detect_project_languages(root)
            self.assertEqual([item["language"] for item in detected], ["typescript"])

    def test_go_requires_go_mod_and_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "main.go").write_text("package main\n", encoding="utf-8")
            self.assertEqual(tooling.detect_project_languages(root), [])
            (root / "go.mod").write_text("module x\n", encoding="utf-8")
            detected = tooling.detect_project_languages(root)
            self.assertEqual([item["language"] for item in detected], ["go"])

    def test_julia_is_detected_as_custom_language(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "run.jl").write_text("println(1)\n", encoding="utf-8")
            detected = tooling.detect_project_languages(root)
            self.assertEqual([item["language"] for item in detected], ["julia"])
            self.assertFalse(detected[0]["builtIn"])

    def test_scan_skips_vendor_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "node_modules" / "pkg"
            nested.mkdir(parents=True)
            (nested / "lib.rs").write_text("", encoding="utf-8")
            (root / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
            self.assertEqual(tooling.detect_project_languages(root), [])

    def test_missing_root_detects_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(
                tooling.detect_project_languages(Path(directory) / "absent"), []
            )


class LanguageToolingCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.project = self.base / "project"
        self.project.mkdir()

    def make_python_project(self) -> None:
        (self.project / "pyproject.toml").write_text("[project]\n", encoding="utf-8")

    def check(self, roots: list[Path] | None = None) -> dict[str, Any]:
        return tooling.check_language_tooling(
            roots if roots is not None else [self.project], home=self.home
        )

    def test_no_languages_is_skipped(self):
        report: Any = self.check()
        self.assertEqual(report["status"], "skipped")
        self.assertEqual(report["pendingWrites"], [])

    def test_missing_server_and_ast_grep_produce_guidance_and_pending_write(self):
        self.make_python_project()
        with mock.patch.dict(os.environ, {"PATH": str(self.base / "empty-bin")}):
            report = self.check()
        self.assertEqual(report["status"], "action-required")
        self.assertFalse(report["languages"]["python"]["ready"])
        self.assertEqual(report["astGrep"]["status"], "not-configured")
        self.assertEqual(
            [write["action"] for write in report["pendingWrites"]],
            ["enable-ast-grep"],
        )
        guidance_ids = [item["id"] for item in report["guidance"]]
        self.assertIn("install-server-python", guidance_ids)
        self.assertIn("enable-ast-grep", guidance_ids)

    def test_available_server_and_enabled_ast_grep_are_ready(self):
        self.make_python_project()
        bin_dir = self.base / "bin"
        bin_dir.mkdir()
        make_executable(bin_dir / "pyright")
        config: Any = self.home / ".omp" / "agent"
        config.mkdir(parents=True)
        (config / "config.yml").write_text("astGrep:\n  enabled: true\n", encoding="utf-8")
        with mock.patch.dict(os.environ, {"PATH": str(bin_dir)}):
            report = self.check()
        self.assertEqual(report["status"], "ready")
        self.assertTrue(report["languages"]["python"]["ready"])
        self.assertEqual(report["pendingWrites"], [])

    def test_ast_grep_disabled_is_a_pending_write(self):
        self.make_python_project()
        config: Any = self.home / ".omp" / "agent"
        config.mkdir(parents=True)
        (config / "config.yml").write_text(
            "theme:\n  dark: x\nastGrep:\n  enabled: false\n", encoding="utf-8"
        )
        report: Any = self.check()
        self.assertEqual(report["astGrep"]["status"], "disabled")
        self.assertEqual(
            [write["action"] for write in report["pendingWrites"]],
            ["enable-ast-grep"],
        )

    def test_malformed_config_is_unreadable_and_never_written(self):
        self.make_python_project()
        config: Any = self.home / ".omp" / "agent"
        config.mkdir(parents=True)
        config_yml = config / "config.yml"
        config_yml.write_text("astGrep: [unclosed\n", encoding="utf-8")
        report: Any = self.check()
        self.assertEqual(report["astGrep"]["status"], "unreadable")
        result: Any = tooling.apply_language_tooling(report, confirmed=True, home=self.home)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(config_yml.read_text(encoding="utf-8"), "astGrep: [unclosed\n")

    def test_julia_without_custom_entry_needs_consent_write(self):
        (self.project / "run.jl").write_text("println(1)\n", encoding="utf-8")
        report: Any = self.check()
        julia: Any = report["languages"]["julia"]
        self.assertFalse(julia["builtIn"])
        self.assertFalse(julia["customConfigured"])
        actions = [write["action"] for write in report["pendingWrites"]]
        self.assertIn("add-lsp-server", actions)
        guidance: Any = {item["id"]: item for item in report["guidance"]}
        self.assertTrue(guidance["custom-server-julia"]["requiresConsent"])
        self.assertIn("LanguageServer", guidance["custom-server-julia"]["steps"][0])

    def test_julia_with_custom_entry_is_ready(self):
        (self.project / "run.jl").write_text("println(1)\n", encoding="utf-8")
        agent = self.home / ".omp" / "agent"
        agent.mkdir(parents=True)
        (agent / "config.yml").write_text("astGrep:\n  enabled: true\n", encoding="utf-8")
        (agent / "lsp.yml").write_text(
            "servers:\n  julia-languageserver:\n    command: julia\n"
            "    fileTypes: ['.jl']\n",
            encoding="utf-8",
        )
        report: Any = self.check()
        self.assertTrue(report["languages"]["julia"]["customConfigured"])
        self.assertEqual(
            [write for write in report["pendingWrites"] if write["action"] == "add-lsp-server"],
            [],
        )


class LanguageToolingApplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.project = self.base / "project"
        self.project.mkdir()
        (self.project / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        (self.project / "run.jl").write_text("println(1)\n", encoding="utf-8")

    def report(self) -> dict[str, Any]:
        with mock.patch.dict(os.environ, {"PATH": str(self.base / "empty-bin")}):
            return tooling.check_language_tooling([self.project], home=self.home)

    def test_refusal_writes_nothing_and_reports_impact(self):
        report: Any = self.report()
        result: Any = tooling.apply_language_tooling(report, confirmed=False, home=self.home)
        self.assertEqual(result["status"], "needs-confirmation")
        self.assertEqual(result["writes"], [])
        self.assertTrue(result["skippedImpact"])
        self.assertFalse((self.home / ".omp").exists())

    def test_consent_creates_config_and_lsp_files(self):
        result: Any = tooling.apply_language_tooling(
            self.report(), confirmed=True, home=self.home
        )
        self.assertEqual(result["status"], "configured")
        self.assertEqual(len(result["writes"]), 2)
        config: Any = yaml.safe_load(
            (self.home / ".omp" / "agent" / "config.yml").read_text(encoding="utf-8")
        )
        self.assertTrue(config["astGrep"]["enabled"])
        lsp: Any = yaml.safe_load(
            (self.home / ".omp" / "agent" / "lsp.yml").read_text(encoding="utf-8")
        )
        entry: Any = lsp["servers"]["julia-languageserver"]
        self.assertEqual(entry["fileTypes"], [".jl"])
        self.assertEqual(entry["languageId"], "julia")
        # A recheck after the writes shows ast-grep enabled and Julia covered.
        with mock.patch.dict(os.environ, {"PATH": str(self.base / "empty-bin")}):
            recheck = tooling.check_language_tooling([self.project], home=self.home)
        self.assertEqual(recheck["astGrep"]["status"], "enabled")
        self.assertTrue(recheck["languages"]["julia"]["customConfigured"])
        self.assertEqual(recheck["pendingWrites"], [])

    def test_consent_preserves_existing_config_content(self):
        agent = self.home / ".omp" / "agent"
        agent.mkdir(parents=True)
        config_yml = agent / "config.yml"
        config_yml.write_text(
            "theme:\n  dark: obsidian\nastGrep:\n  enabled: false\n", encoding="utf-8"
        )
        result: Any = tooling.apply_language_tooling(
            self.report(), confirmed=True, home=self.home
        )
        self.assertEqual(result["status"], "configured")
        config: Any = yaml.safe_load(config_yml.read_text(encoding="utf-8"))
        self.assertTrue(config["astGrep"]["enabled"])
        self.assertEqual(config["theme"], {"dark": "obsidian"})
        self.assertTrue((agent / "config.yml.sbtd-backup").is_file())

    def test_consent_handles_flow_style_ast_grep_section(self):
        agent = self.home / ".omp" / "agent"
        agent.mkdir(parents=True)
        config_yml = agent / "config.yml"
        config_yml.write_text("astGrep: {enabled: false}\n", encoding="utf-8")
        result: Any = tooling.apply_language_tooling(
            self.report(), confirmed=True, home=self.home
        )
        self.assertEqual(result["status"], "configured")
        config: Any = yaml.safe_load(config_yml.read_text(encoding="utf-8"))
        self.assertIs(config["astGrep"]["enabled"], True)

    def test_consent_preserves_existing_lsp_servers(self):
        agent = self.home / ".omp" / "agent"
        agent.mkdir(parents=True)
        (agent / "config.yml").write_text("astGrep:\n  enabled: true\n", encoding="utf-8")
        lsp_yml = agent / "lsp.yml"
        lsp_yml.write_text(
            "servers:\n  pyright:\n    rootMarkers:\n      - pyproject.toml\n      - .git\n",
            encoding="utf-8",
        )
        result: Any = tooling.apply_language_tooling(
            self.report(), confirmed=True, home=self.home
        )
        self.assertEqual(result["status"], "configured")
        lsp: Any = yaml.safe_load(lsp_yml.read_text(encoding="utf-8"))
        self.assertEqual(
            lsp["servers"]["pyright"]["rootMarkers"], ["pyproject.toml", ".git"]
        )
        self.assertIn("julia-languageserver", lsp["servers"])

    def test_malformed_lsp_fails_without_replacing_bytes(self):
        agent = self.home / ".omp" / "agent"
        agent.mkdir(parents=True)
        (agent / "config.yml").write_text("astGrep:\n  enabled: true\n", encoding="utf-8")
        lsp_yml = agent / "lsp.yml"
        lsp_yml.write_text("servers: [unclosed\n", encoding="utf-8")
        result: Any = tooling.apply_language_tooling(
            self.report(), confirmed=True, home=self.home
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(lsp_yml.read_text(encoding="utf-8"), "servers: [unclosed\n")


class OnboardWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.project = self.base / "project"
        self.project.mkdir()
        (self.project / "pyproject.toml").write_text("[project]\n", encoding="utf-8")

    def test_build_project_check_includes_languages(self):
        check: Any = onboard.build_project_check(self.project)
        self.assertEqual(
            [item["language"] for item in check["languages"]], ["python"]
        )

    def test_init_step_without_flag_is_needs_confirmation_without_writes(self):
        args = argparse.Namespace(
            projects_root=str(self.project), language_tooling=False
        )
        with mock.patch.dict(os.environ, {"HOME": str(self.home), "PATH": str(self.base / "empty-bin")}):
            result = onboard.run_language_tooling_step("init", args)
        self.assertEqual(result["status"], "needs-confirmation")
        self.assertFalse((self.home / ".omp").exists())

    def test_init_step_with_flag_applies_config_writes(self):
        args = argparse.Namespace(
            projects_root=str(self.project), language_tooling=True
        )
        with mock.patch.dict(os.environ, {"HOME": str(self.home), "PATH": str(self.base / "empty-bin")}):
            result = onboard.run_language_tooling_step("init", args)
        self.assertEqual(result["status"], "configured")
        config: Any = yaml.safe_load(
            (self.home / ".omp" / "agent" / "config.yml").read_text(encoding="utf-8")
        )
        self.assertTrue(config["astGrep"]["enabled"])

    def test_other_modes_skip_the_step(self):
        args = argparse.Namespace(projects_root=str(self.project))
        self.assertIsNone(onboard.run_language_tooling_step("check", args))

    def test_init_parser_accepts_language_tooling_flag(self):
        parser = onboard.build_parser()
        args = parser.parse_args(["init-projects", "--projects-root", "/x", "--language-tooling"])
        self.assertTrue(args.language_tooling)
        args = parser.parse_args(["init", "--projects-root", "/x"])
        self.assertFalse(args.language_tooling)


if __name__ == "__main__":
    unittest.main()
