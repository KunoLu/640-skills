from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import sbtd_upgrade_hosts as hosts
from onboard_contracts import ContractError


def _package(base: Path) -> Path:
    root = base / "package"
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    return root


def _runtime(base: Path, name: str = "runtime") -> dict[str, str]:
    directory = base / name
    directory.mkdir(exist_ok=True)
    paths: dict[str, str] = {}
    for key, filename in (("python", "python"), ("node", "node"), ("cli", "cli.js")):
        target = directory / filename
        target.write_bytes(b"")
        paths[key] = str(target)
    return paths


def _codex_host(base: Path, runtime: dict[str, str]) -> dict:
    account = base / "account"
    return {
        "id": "codex-account",
        "platform": "codex",
        "config_home": str(account / ".codex"),
        "config": str(account / ".codex" / "config.toml"),
        "runtime": dict(runtime),
        "skills_roots": [],
        "project_roots": [],
        "onboard_root": str(base / "package"),
    }


def _omp_host(base: Path, runtime: dict[str, str], *, profile: str | None = None) -> dict:
    account = base / "account"
    config_home = account / ".omp"
    config = (
        config_home / "agent" / "mcp.json"
        if profile is None
        else config_home / "profiles" / profile / "agent" / "mcp.json"
    )
    return {
        "id": "omp-account",
        "platform": "omp",
        "config_home": str(config_home),
        "config": str(config),
        "runtime": dict(runtime),
        "skills_roots": [],
        "project_roots": [],
        "onboard_root": str(base / "package"),
    }


class ScopeValidationTests(unittest.TestCase):
    def test_scope_must_be_a_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ContractError) as caught:
            hosts.build_host_resources([], package_root=Path(directory))
        self.assertEqual(caught.exception.code, "scope-conflict")

    def test_config_must_live_inside_config_home(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            host = _codex_host(base, _runtime(base))
            host["config"] = str(base / "elsewhere" / "config.toml")
            with self.assertRaises(ContractError) as caught:
                hosts.build_host_resources({"hosts": [host]}, package_root=_package(base))
        self.assertEqual(caught.exception.code, "scope-conflict")

    def test_host_skills_root_must_be_selected_top_level(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            stray = base / "stray"
            stray.mkdir()
            host = _codex_host(base, _runtime(base))
            host["skills_roots"] = [str(stray)]
            with self.assertRaises(ContractError) as caught:
                hosts.build_host_resources(
                    {"hosts": [host], "skills_roots": []}, package_root=_package(base)
                )
        self.assertEqual(caught.exception.code, "scope-conflict")

    def test_host_runtime_must_name_exactly_python_node_cli(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            host = _codex_host(base, _runtime(base))
            host["runtime"] = {"python": host["runtime"]["python"], "node": host["runtime"]["node"]}
            with self.assertRaises(ContractError) as caught:
                hosts.build_host_resources({"hosts": [host]}, package_root=_package(base))
        self.assertEqual(caught.exception.code, "scope-conflict")

    def test_duplicate_host_ids_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            host = _codex_host(base, _runtime(base))
            with self.assertRaises(ContractError) as caught:
                hosts.build_host_resources(
                    {"hosts": [host, dict(host)]}, package_root=_package(base)
                )
        self.assertEqual(caught.exception.code, "scope-conflict")

    def test_unsupported_shell_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            with self.assertRaises(ContractError) as caught:
                hosts.build_host_resources(
                    {
                        "shell_profiles": [
                            {
                                "path": str(base / ".config/fish/config.fish"),
                                "shell": "fish",
                                "bin": str(base / "bin"),
                            }
                        ]
                    },
                    package_root=_package(base),
                )
        self.assertEqual(caught.exception.code, "scope-conflict")

    def test_bin_with_newline_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            with self.assertRaises(ContractError) as caught:
                hosts.build_host_resources(
                    {
                        "shell_profiles": [
                            {
                                "path": str(base / ".bashrc"),
                                "shell": "bash",
                                "bin": str(base / "bin") + "\nrm -rf /",
                            }
                        ]
                    },
                    package_root=_package(base),
                )
        self.assertEqual(caught.exception.code, "invalid-argument")

    def test_malformed_decision_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            with self.assertRaises(ContractError) as caught:
                hosts.build_host_resources(
                    {"decisions": {"relative/path": "replace"}}, package_root=_package(base)
                )
        self.assertEqual(caught.exception.code, "scope-conflict")

    def test_missing_launcher_is_not_a_required_asset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            package = _package(base)
            self.assertFalse((package / "scripts" / "sbtd_graft_entry.py").exists())
            resources = hosts.build_host_resources(
                {"hosts": [_codex_host(base, _runtime(base))]}, package_root=package
            )
        self.assertEqual(resources, [])


class PathSeparatorRejectionTests(unittest.TestCase):
    def _build(self, base: Path, shell: str, bin_dir: str):
        return hosts.build_host_resources(
            {"shell_profiles": [{"path": str(base / "profile"), "shell": shell, "bin": bin_dir}]},
            package_root=_package(base),
        )

    @unittest.skipIf(os.name == "nt", "POSIX PATH separator case")
    def test_posix_bin_with_colon_is_rejected_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            for shell in ("bash", "zsh", "powershell"):
                with self.subTest(shell=shell):
                    with self.assertRaises(ContractError) as caught:
                        self._build(base, shell, str(base / "bin:withcolon"))
                    self.assertEqual(caught.exception.code, "unsafe-path")

    @unittest.skipIf(os.name == "nt", "POSIX PATH separator case")
    def test_posix_semicolon_bin_is_representable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            self.assertEqual(self._build(base, "bash", str(base / "bin;withsemicolon")), [])

    @unittest.skipUnless(os.name == "nt", "native Windows separator case")
    def test_windows_bin_with_semicolon_is_rejected_for_powershell(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            with self.assertRaises(ContractError) as caught:
                self._build(base, "powershell", str(base / "bin;with"))
            self.assertEqual(caught.exception.code, "unsafe-path")

    @unittest.skipUnless(os.name == "nt", "native Windows separator case")
    def test_windows_drive_tail_colon_is_rejected_for_bash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            with self.assertRaises(ContractError) as caught:
                self._build(base, "bash", "C:\\tools:bad\\bin")
            self.assertEqual(caught.exception.code, "unsafe-path")
            self.assertEqual(self._build(base, "bash", str(base / "bin")), [])


class HostPlatformNormalizationTests(unittest.TestCase):
    def test_oh_my_pi_platform_is_canonicalized_to_omp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            host = _omp_host(base, _runtime(base))
            host["platform"] = "oh-my-pi"
            self.assertEqual(
                hosts.build_host_resources({"hosts": [host]}, package_root=_package(base)), []
            )
            result = hosts.verify_hosts({"hosts": [host]}, package_root=_package(base))
            entry = result["hosts"][0]
            self.assertEqual(entry["platform"], "omp")
            self.assertEqual(entry["applicability"], "supported")
            self.assertEqual(entry["disk"]["status"], "not-applicable")

    def test_probe_does_not_start_graft_or_a_host(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            host = _omp_host(base, _runtime(base), profile="work")
            host["platform"] = "oh-my-pi"
            with mock.patch("sbtd_upgrade_hosts.subprocess", create=True) as spawned:
                result = hosts.verify_hosts(
                    {"hosts": [host]}, package_root=_package(base), probe=True
                )
            spawned.Popen.assert_not_called()
            self.assertEqual(result["hosts"][0]["host"]["checks"]["protocol"]["status"], "not-applicable")
            self.assertEqual(result["hosts"][0]["host"]["checks"]["host_load"]["status"], "not-applicable")


    def test_probe_spawns_selected_host_and_refuses_retained_server(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            host = _codex_host(base, _runtime(base))
            project = base / "project"
            project.mkdir()
            host["project_roots"] = [str(project)]
            host["skills_roots"] = []
            config = Path(host["config"])
            config.parent.mkdir(parents=True)
            config.write_text('[mcp_servers.sbtd-graft]\ncommand = "graft"\n', encoding="utf-8")
            spawned: list[list[str]] = []

            def refuse(argv, *, env, cwd):
                spawned.append(list(argv))
                raise AssertionError("retained server must not be spawned")

            with mock.patch.object(hosts, "_spawn", refuse):
                result = hosts.verify_hosts(
                    {"hosts": [host], "skills_roots": []},
                    package_root=_package(base),
                    probe=True,
                )
            self.assertEqual(spawned, [])
            load = result["hosts"][0]["host"]["checks"]["host_load"]
            self.assertEqual(load["status"], "failed")
            self.assertEqual(load["reason"], "unsafe-registered-server")
            self.assertNotIn("sbtd-graft", json.dumps(result["hosts"][0]["host"]["checks"]))

class ShellResourceTests(unittest.TestCase):
    def _profile(self, base: Path, content: bytes) -> tuple[Path, dict]:
        profile = base / "selected-profile"
        profile.write_bytes(content)
        scope = {
            "shell_profiles": [
                {"path": str(profile), "shell": "powershell", "bin": str(base / "bin")}
            ]
        }
        return profile, scope

    @unittest.skipUnless(os.name == "nt", "Windows profile retention")
    def test_windows_unicode_profile_is_not_executed_by_probe(self):
        """Unicode profile bytes stay intact. Graft command resolution is gone."""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            original = "profile \u2603\n".encode("utf-8")
            profile, scope = self._profile(base, original)
            result = hosts.verify_hosts(scope, package_root=_package(base), probe=True)
            self.assertEqual(profile.read_bytes(), original)
            self.assertEqual(result["shell_profiles"][0]["host"]["status"], "not-applicable")
            self.assertNotIn("graft", json.dumps(result))

    @unittest.skipUnless(os.name == "nt", "Windows profile retention")
    def test_windows_profile_is_not_rewritten_by_upgrade(self):
        """A new Unicode profile is not rewritten into a graft PATH block."""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            original = "# existing ANSI comment: \u00e9\r\n".encode("utf-8")
            profile, scope = self._profile(base, original)
            self.assertEqual(
                hosts.build_host_resources(scope, package_root=_package(base)), []
            )
            hosts.verify_hosts(scope, package_root=_package(base), probe=True)
            self.assertEqual(profile.read_bytes(), original)
            self.assertNotIn(b"sbtd-workflow-onboard:path:start", profile.read_bytes())
