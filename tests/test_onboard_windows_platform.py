from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
ONBOARD = ROOT / "sbtd-workflow-onboard" / "scripts" / "onboard.py"
sys.path.insert(0, str(ONBOARD.parent))


def load_onboard(test: unittest.TestCase, name: str):
    spec = importlib.util.spec_from_file_location(name, ONBOARD)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load onboard module from {ONBOARD}")
    loader = cast(importlib.machinery.SourceFileLoader, spec.loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    test.addCleanup(sys.modules.pop, name, None)
    loader.exec_module(module)
    return module


class SubprocessCommandTests(unittest.TestCase):
    """Windows npm global CLIs are .CMD/.BAT batch launchers, not PE
    executables; direct Win32 exec fails with error 193 (migration M03).
    subprocess_command() must route only those shims through cmd.exe."""

    def setUp(self) -> None:
        self.onboard = load_onboard(self, f"onboard_win_shim_{id(self)}")
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sbtd-win-shim-test-")
        self.addCleanup(self.temp_dir.cleanup)
        self.bin_dir = Path(self.temp_dir.name) / "bin"
        self.bin_dir.mkdir()

    def write_shim(self, name: str) -> Path:
        target = self.bin_dir / name
        target.write_text("@echo off\r\n", encoding="utf-8")
        return target

    def convert(self, command: tuple[str, ...], resolved: str | None) -> object:
        with (
            mock.patch.object(
                self.onboard.platform, "system", return_value="Windows"
            ),
            mock.patch.object(self.onboard.shutil, "which", return_value=resolved),
        ):
            return self.onboard.subprocess_command(command)

    def test_cmd_shim_routes_through_cmd_exe(self) -> None:
        shim = self.write_shim("faketool.cmd")
        command = self.convert(("faketool", "--version"), str(shim))
        self.assertIsInstance(command, str)
        assert isinstance(command, str)
        self.assertTrue(command.startswith('cmd.exe /d /s /c "'))
        self.assertTrue(command.endswith('"'))
        self.assertIn(str(shim), command)
        self.assertIn("--version", command)

    def test_bat_shim_routes_through_cmd_exe(self) -> None:
        shim = self.write_shim("faketool.bat")
        command = self.convert(("faketool",), str(shim))
        self.assertIsInstance(command, str)
        assert isinstance(command, str)
        self.assertTrue(command.startswith('cmd.exe /d /s /c "'))

    def test_native_exe_keeps_argv_tuple(self) -> None:
        shim = self.write_shim("faketool.exe")
        original = ("faketool", "--version")
        self.assertEqual(self.convert(original, str(shim)), original)

    def test_non_windows_keeps_argv_tuple(self) -> None:
        original = ("faketool", "--version")
        with mock.patch.object(
            self.onboard.platform, "system", return_value="Darwin"
        ):
            self.assertEqual(self.onboard.subprocess_command(original), original)

    def test_unresolved_launcher_keeps_argv_tuple(self) -> None:
        original = ("faketool", "--version")
        self.assertEqual(self.convert(original, None), original)

    def test_path_with_spaces_is_quoted(self) -> None:
        spaced = Path(self.temp_dir.name) / "bin dir"
        spaced.mkdir()
        shim = spaced / "faketool.cmd"
        shim.write_text("@echo off\r\n", encoding="utf-8")
        command = self.convert(("faketool", "a b"), str(shim))
        self.assertIsInstance(command, str)
        assert isinstance(command, str)
        expected = subprocess.list2cmdline([str(shim), "a b"])
        self.assertEqual(command, f'cmd.exe /d /s /c "{expected}"')


@unittest.skipUnless(os.name == "nt", "Windows batch shim execution")
class WindowsShimExecutionTests(unittest.TestCase):
    """Real cmd.exe execution of a .CMD shim on PATH (migration M03/M04)."""

    def setUp(self) -> None:
        self.onboard = load_onboard(self, f"onboard_win_exec_{id(self)}")
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sbtd-win-exec-test-")
        self.addCleanup(self.temp_dir.cleanup)
        self.bin_dir = Path(self.temp_dir.name) / "bin"
        self.bin_dir.mkdir()
        shim = self.bin_dir / "faketool.cmd"
        shim.write_text("@echo faketool 1.2.3\r\n", encoding="utf-8")
        self.env_patch = mock.patch.dict(
            os.environ,
            {"PATH": os.pathsep.join((str(self.bin_dir), os.environ["PATH"]))},
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_check_cli_tool_executes_cmd_shim_found_on_path(self) -> None:
        result = self.onboard.check_cli_tool(
            {
                "name": "faketool",
                "versionArgs": ("--version",),
                "globalInstall": "",
                "projectInstall": "",
                "advice": "",
            }
        )
        self.assertTrue(result["installed"])
        self.assertIn("1.2.3", str(result["version"]))

    def test_project_command_executes_cmd_shim_found_on_path(self) -> None:
        completed = self.onboard.run_project_command(
            ("faketool", "--version"), cwd=Path.cwd()
        )
        self.assertIsNotNone(completed)
        assert completed is not None
        self.assertEqual(completed.returncode, 0)
        self.assertIn("faketool 1.2.3", completed.stdout)


class DecodeToleranceTests(unittest.TestCase):
    """Detection subprocess output may carry local code-page bytes that the
    default UTF-8 decoder cannot parse (migration M04); run_command must
    replace undecodable bytes instead of losing the whole result."""

    def setUp(self) -> None:
        self.onboard = load_onboard(self, f"onboard_decode_{id(self)}")
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sbtd-decode-test-")
        self.addCleanup(self.temp_dir.cleanup)

    @unittest.skipIf(os.name == "nt", "POSIX shell fixture")
    def test_run_command_tolerates_non_utf8_output(self) -> None:
        script = Path(self.temp_dir.name) / "emit.sh"
        script.write_bytes(b"#!/bin/sh\nprintf '\\377\\376ok'\n")
        script.chmod(0o755)
        completed = self.onboard.run_command(("sh", str(script)))
        self.assertIsNotNone(completed)
        assert completed is not None
        self.assertEqual(completed.returncode, 0)
        self.assertIn("ok", completed.stdout)


class JavaBinaryPathTests(unittest.TestCase):
    """Windows JDKs ship bin/java.exe; detecting only bin/java misjudges an
    installed JDK as missing (migration M05)."""

    def setUp(self) -> None:
        self.onboard = load_onboard(self, f"onboard_win_java_{id(self)}")
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sbtd-win-java-test-")
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.home = self.root / "jdk-21"
        (self.home / "bin").mkdir(parents=True)

    def test_java_home_accepts_java_exe(self) -> None:
        exe = self.home / "bin" / "java.exe"
        exe.write_bytes(b"MZ")
        with mock.patch.object(
            self.onboard.platform, "system", return_value="Windows"
        ):
            self.assertEqual(self.onboard.java_binary_path(self.home), exe)
            self.assertEqual(
                self.onboard.usable_java_home(self.home), self.home.resolve()
            )
            self.assertEqual(
                self.onboard.infer_java_home_from_path(str(exe)),
                self.home.resolve(),
            )

    def test_windows_still_accepts_bare_java(self) -> None:
        launcher = self.home / "bin" / "java"
        launcher.write_bytes(b"#!/bin/sh\n")
        with mock.patch.object(
            self.onboard.platform, "system", return_value="Windows"
        ):
            self.assertEqual(self.onboard.java_binary_path(self.home), launcher)
            self.assertEqual(
                self.onboard.usable_java_home(self.home), self.home.resolve()
            )

    def test_posix_ignores_java_exe(self) -> None:
        (self.home / "bin" / "java.exe").write_bytes(b"MZ")
        with mock.patch.object(
            self.onboard.platform, "system", return_value="Linux"
        ):
            self.assertEqual(
                self.onboard.java_binary_path(self.home),
                self.home / "bin" / "java",
            )
            self.assertIsNone(self.onboard.usable_java_home(self.home))

    def test_find_java_home_accepts_java_exe_on_windows(self) -> None:
        exe = self.home / "bin" / "java.exe"
        exe.write_bytes(b"MZ")
        with mock.patch.object(
            self.onboard.platform, "system", return_value="Windows"
        ):
            self.assertEqual(self.onboard.find_java_home(self.root), self.home)

    def test_find_java_home_posix_layout_unchanged(self) -> None:
        (self.home / "bin" / "java").write_bytes(b"#!/bin/sh\n")
        self.assertEqual(self.onboard.find_java_home(self.root), self.home)


if __name__ == "__main__":
    unittest.main()
