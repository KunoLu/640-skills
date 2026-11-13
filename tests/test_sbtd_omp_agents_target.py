"""Tests for the PI_CODING_AGENT_DIR-aware OMP global AGENTS.md resolution.

Every test runs against temporary directories with mocked environment; the
real user home is never touched.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "sbtd-workflow-onboard" / "scripts"
ONBOARD = SCRIPTS / "onboard.py"
sys.path.insert(0, str(SCRIPTS))

import onboard
from onboard_contracts import ContractError
from sbtd_migration_files import read_file, snapshot
from sbtd_migration_plan import _PAUSE_ASSET, _approved_routing_operations
from sbtd_omp_sources import active_omp_agent_dir

_OMP_ENV_KEYS = ("PI_CODING_AGENT_DIR", "PI_CONFIG_DIR", "OMP_PROFILE", "PI_PROFILE")


def scrubbed_environ(**overrides: str) -> dict[str, str]:
    env = os.environ.copy()
    for key in _OMP_ENV_KEYS:
        env.pop(key, None)
    env.update(overrides)
    return env


class OmpAgentDirResolverTests(unittest.TestCase):
    """Direct resolver semantics, mirroring omp 18.19.0 settings."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sbtd-omp-agents-")
        self.addCleanup(self.temp_dir.cleanup)
        self.home = Path(self.temp_dir.name).resolve() / "home"
        self.home.mkdir()

    def resolve(self, **env: str) -> dict[str, object]:
        return active_omp_agent_dir(home=self.home, environ=env)

    def test_unset_variable_falls_back_to_default(self) -> None:
        resolved = self.resolve()
        self.assertEqual(resolved["agent_dir"], self.home / ".omp" / "agent")
        self.assertEqual(resolved["override"], False)
        self.assertIsNone(resolved["profile"])

    def test_empty_variable_falls_back_to_default(self) -> None:
        resolved = self.resolve(PI_CODING_AGENT_DIR="")
        self.assertEqual(resolved["agent_dir"], self.home / ".omp" / "agent")
        self.assertEqual(resolved["override"], False)

    def test_absolute_variable_selects_agent_dir(self) -> None:
        custom = self.home / "elsewhere"
        resolved = self.resolve(PI_CODING_AGENT_DIR=str(custom))
        self.assertEqual(resolved["agent_dir"], custom)
        self.assertEqual(resolved["override"], True)

    def test_relative_variable_resolves_against_process_cwd(self) -> None:
        resolved = self.resolve(PI_CODING_AGENT_DIR="relative/agent")
        self.assertEqual(
            resolved["agent_dir"], Path(os.path.abspath("relative/agent"))
        )

    def test_tilde_variable_is_not_expanded(self) -> None:
        resolved = self.resolve(PI_CODING_AGENT_DIR="~/tilde-agent")
        self.assertEqual(
            resolved["agent_dir"], Path(os.path.abspath("~/tilde-agent"))
        )
        self.assertNotEqual(resolved["agent_dir"], self.home / "tilde-agent")

    def test_whitespace_only_variable_resolves_against_process_cwd(self) -> None:
        # omp 18.19.0 truthiness: only "" falls back; " " is a real directory
        # name resolved against the process current directory.
        resolved = self.resolve(PI_CODING_AGENT_DIR=" ")
        self.assertEqual(resolved["agent_dir"], Path(os.path.abspath(" ")))
        self.assertEqual(resolved["override"], True)

    def test_config_dir_override_moves_default_root(self) -> None:
        resolved = self.resolve(PI_CONFIG_DIR="custom-omp")
        self.assertEqual(resolved["agent_dir"], self.home / "custom-omp" / "agent")
        self.assertEqual(resolved["override"], False)

    def test_absolute_config_dir_is_joined_under_home(self) -> None:
        # omp 18.19.0 path.join(home, value): a leading separator does not
        # discard home (unlike Python os.path.join).
        resolved = self.resolve(PI_CONFIG_DIR="/abs/omp-root")
        self.assertEqual(
            resolved["agent_dir"], self.home / "abs" / "omp-root" / "agent"
        )

    def test_dotdot_config_dir_escapes_home(self) -> None:
        # omp 18.19.0 path.join normalizes ".." against home; not rejected.
        resolved = self.resolve(PI_CONFIG_DIR="../escaped")
        self.assertEqual(
            resolved["agent_dir"], self.home.parent / "escaped" / "agent"
        )

    def test_named_profile_ignores_variable(self) -> None:
        resolved = self.resolve(
            PI_CODING_AGENT_DIR=str(self.home / "elsewhere"), OMP_PROFILE="work"
        )
        self.assertEqual(
            resolved["agent_dir"], self.home / ".omp" / "profiles" / "work" / "agent"
        )
        self.assertEqual(resolved["profile"], "work")
        self.assertEqual(resolved["override"], False)

    def test_variable_equal_to_derived_default_counts_as_unset(self) -> None:
        resolved = self.resolve(
            PI_CODING_AGENT_DIR=str(self.home / ".omp" / "agent")
        )
        self.assertEqual(resolved["agent_dir"], self.home / ".omp" / "agent")
        self.assertEqual(resolved["override"], False)

    def test_derived_default_comparison_uses_pi_profile_default(self) -> None:
        # omp compares the raw value against j$a(Oz(PI_PROFILE)); "default"
        # maps to the plain root, so the plain default path counts as unset.
        resolved = self.resolve(
            PI_CODING_AGENT_DIR=str(self.home / ".omp" / "agent"),
            PI_PROFILE="default",
        )
        self.assertEqual(resolved["agent_dir"], self.home / ".omp" / "agent")
        self.assertEqual(resolved["override"], False)

    def test_invalid_profile_name_rejected(self) -> None:
        with self.assertRaises(ContractError):
            self.resolve(OMP_PROFILE="Bad_Name!")


class BuildOperationsTargetTests(unittest.TestCase):
    """The init/reset write target follows the same resolution."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sbtd-omp-build-")
        self.addCleanup(self.temp_dir.cleanup)
        base = Path(self.temp_dir.name).resolve()
        self.home = base / "home"
        self.home.mkdir()
        self.codex_home = base / "codex"
        self.project = base / "project"
        self.project.mkdir()
        self.skills = base / "skills"

    def operations(self, **env: str) -> list[onboard.Operation]:
        args = argparse.Namespace(
            projects_root=str(self.project),
            skip_project_agents=False,
            global_agents_path=None,
            global_skills_dir=str(self.skills),
        )
        patched = scrubbed_environ(
            HOME=str(self.home), USERPROFILE=str(self.home), CODEX_HOME=str(self.codex_home)
        )
        patched.update(env)
        with mock.patch.dict(os.environ, patched, clear=True):
            return onboard.build_operations("init", args)

    @staticmethod
    def omp_targets(ops: list[onboard.Operation]) -> list[Path]:
        return [op.target for op in ops if op.label == "omp global AGENTS.md"]

    def test_variable_dir_written_even_when_missing(self) -> None:
        agent_dir = self.home / "explicit-agent"
        ops = self.operations(PI_CODING_AGENT_DIR=str(agent_dir))
        self.assertEqual(
            self.omp_targets(ops), [(agent_dir / "AGENTS.md").resolve()]
        )

    def test_variable_wins_over_existing_default_root(self) -> None:
        (self.home / ".omp").mkdir()
        agent_dir = self.home / "explicit-agent"
        ops = self.operations(PI_CODING_AGENT_DIR=str(agent_dir))
        self.assertEqual(
            self.omp_targets(ops), [(agent_dir / "AGENTS.md").resolve()]
        )

    def test_default_target_when_root_exists(self) -> None:
        omp_root = self.home / ".omp"
        omp_root.mkdir()
        ops = self.operations()
        self.assertEqual(
            self.omp_targets(ops), [(omp_root / "agent" / "AGENTS.md").resolve()]
        )

    def test_skipped_when_default_root_missing(self) -> None:
        ops = self.operations()
        self.assertEqual(self.omp_targets(ops), [])

    def test_empty_variable_keeps_skip_behavior(self) -> None:
        ops = self.operations(PI_CODING_AGENT_DIR="")
        self.assertEqual(self.omp_targets(ops), [])

    def test_profile_targets_profile_agent_dir(self) -> None:
        ops = self.operations(OMP_PROFILE="work")
        self.assertEqual(
            self.omp_targets(ops),
            [
                (
                    self.home / ".omp" / "profiles" / "work" / "agent" / "AGENTS.md"
                ).resolve()
            ],
        )

    def test_config_dir_moves_detected_root_and_target(self) -> None:
        (self.home / "custom-omp").mkdir()
        patched = scrubbed_environ(
            HOME=str(self.home),
            USERPROFILE=str(self.home),
            CODEX_HOME=str(self.codex_home),
            PI_CONFIG_DIR="custom-omp",
        )
        with mock.patch.dict(os.environ, patched, clear=True):
            self.assertEqual(
                onboard.detect_omp_root(), (self.home / "custom-omp").resolve()
            )
        ops = self.operations(PI_CONFIG_DIR="custom-omp")
        self.assertEqual(
            self.omp_targets(ops),
            [(self.home / "custom-omp" / "agent" / "AGENTS.md").resolve()],
        )

    def test_absolute_config_dir_root_detected_under_home(self) -> None:
        joined = self.home / "abs" / "omp-root"
        joined.mkdir(parents=True)
        patched = scrubbed_environ(
            HOME=str(self.home),
            USERPROFILE=str(self.home),
            CODEX_HOME=str(self.codex_home),
            PI_CONFIG_DIR="/abs/omp-root",
        )
        with mock.patch.dict(os.environ, patched, clear=True):
            self.assertEqual(onboard.detect_omp_root(), joined.resolve())

    def omp_operation(self, ops: list[onboard.Operation]) -> onboard.Operation:
        (operation,) = [op for op in ops if op.label == "omp global AGENTS.md"]
        return operation

    def test_missing_variable_dir_created_and_written_on_apply(self) -> None:
        agent_dir = self.home / "fresh-agent"
        self.assertFalse(agent_dir.exists())
        ops = self.operations(PI_CODING_AGENT_DIR=str(agent_dir))
        operation = self.omp_operation(ops)
        action = onboard.copy_operation(operation)
        self.assertEqual(action, "copied")
        written = agent_dir / "AGENTS.md"
        self.assertTrue(written.is_file())
        self.assertEqual(written.read_bytes(), Path(operation.source).read_bytes())

    def test_tilde_value_creates_literal_tilde_directory_under_cwd(self) -> None:
        # omp 18.19.0 never expands "~": "~/tilde-agent" resolves to a
        # directory literally named "~" under the process current directory,
        # and the write creates it there -- never under the user home.
        cwd = Path(self.temp_dir.name).resolve() / "cwd"
        cwd.mkdir()
        previous = os.getcwd()
        try:
            os.chdir(cwd)
            ops = self.operations(PI_CODING_AGENT_DIR="~/tilde-agent")
            operation = self.omp_operation(ops)
            self.assertEqual(
                operation.target, cwd / "~" / "tilde-agent" / "AGENTS.md"
            )
            onboard.copy_operation(operation)
        finally:
            os.chdir(previous)
        self.assertTrue((cwd / "~" / "tilde-agent" / "AGENTS.md").is_file())
        self.assertFalse((self.home / "tilde-agent").exists())


class CheckReportTests(unittest.TestCase):
    """The check report names the same target the write path uses."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sbtd-omp-check-")
        self.addCleanup(self.temp_dir.cleanup)
        base = Path(self.temp_dir.name).resolve()
        self.home = base / "home"
        self.home.mkdir()
        self.env = scrubbed_environ(
            HOME=str(self.home),
            USERPROFILE=str(self.home),
            CODEX_HOME=str(base / "codex"),
        )

    def check_paths(self, **env: str) -> dict[str, object]:
        merged = dict(self.env)
        merged.update(env)
        completed = subprocess.run(
            (sys.executable, str(ONBOARD), "check", "--json"),
            check=False,
            capture_output=True,
            text=True,
            env=merged,
            timeout=120,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)["paths"]

    def test_check_reports_variable_target(self) -> None:
        agent_dir = self.home / "explicit-agent"
        paths = self.check_paths(PI_CODING_AGENT_DIR=str(agent_dir))
        self.assertEqual(
            paths["ompGlobalAgents"], str(agent_dir / "AGENTS.md")
        )
        self.assertIsNone(paths["ompRoot"])

    def test_check_reports_default_when_root_exists(self) -> None:
        omp_root = self.home / ".omp"
        omp_root.mkdir()
        paths = self.check_paths()
        self.assertEqual(paths["ompRoot"], str(omp_root))
        self.assertEqual(paths["ompGlobalAgents"], str(omp_root / "agent" / "AGENTS.md"))

    def test_check_resolves_symlink_home_when_variable_unset(self) -> None:
        real_home = self.home / "real-home"
        omp_root = real_home / ".omp"
        omp_root.mkdir(parents=True)
        link_home = self.home / "link-home"
        try:
            link_home.symlink_to(real_home, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"symlink creation unavailable: {error}")
        paths = self.check_paths(HOME=str(link_home), USERPROFILE=str(link_home))
        self.assertEqual(
            paths["ompGlobalAgents"],
            str((omp_root / "agent" / "AGENTS.md").resolve()),
        )

    def test_check_reports_none_when_unconfigured(self) -> None:
        paths = self.check_paths()
        self.assertIsNone(paths["ompRoot"])
        self.assertIsNone(paths["ompGlobalAgents"])
        paths = self.check_paths(PI_CODING_AGENT_DIR="")
        self.assertIsNone(paths["ompRoot"])
        self.assertIsNone(paths["ompGlobalAgents"])


class MigrationRoutingApprovalTests(unittest.TestCase):
    """omp-global routing approvals bind to the resolved AGENTS.md."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sbtd-omp-route-")
        self.addCleanup(self.temp_dir.cleanup)
        base = Path(self.temp_dir.name).resolve()
        self.home = base / "home"
        self.home.mkdir()
        self.project = base / "project"
        self.project.mkdir()
        self.vault = base / "vault"
        self.vault.mkdir()
        pause = read_file(_PAUSE_ASSET)
        self.candidate = self.vault / "candidate.md"
        self.candidate.write_bytes(pause + b"\napproved routing\n")
        self.approval = self.vault / "approval.json"
        self.approval.write_text("{}", encoding="utf-8")

    def bind(self, target: Path, **env: str):
        items = [
            {
                "role": "omp-global",
                "target_path": str(target),
                "before": {"type": "file", "checksum": "0" * 64},
                "candidate_ref": {
                    "path": str(self.candidate),
                    "state": snapshot(self.candidate),
                },
                "basis": "test routing",
            }
        ]
        patched = scrubbed_environ(
            HOME=str(self.home), USERPROFILE=str(self.home)
        )
        patched.update(env)
        with mock.patch.dict(os.environ, patched, clear=True):
            return _approved_routing_operations(
                items, [self.project], self.vault, self.approval, bind_live=False
            )

    def test_variable_target_accepted(self) -> None:
        agent_dir = self.home / "explicit-agent"
        target = agent_dir / "AGENTS.md"
        shared, _private = self.bind(target, PI_CODING_AGENT_DIR=str(agent_dir))
        self.assertEqual(len(shared), 1)
        self.assertEqual(shared[0]["target"], str(target))

    def test_default_target_rejected_when_variable_set(self) -> None:
        (self.home / ".omp").mkdir()
        stale = self.home / ".omp" / "agent" / "AGENTS.md"
        with self.assertRaises(ContractError):
            self.bind(stale, PI_CODING_AGENT_DIR=str(self.home / "explicit-agent"))

    def test_default_target_accepted_when_root_exists(self) -> None:
        (self.home / ".omp").mkdir()
        target = self.home / ".omp" / "agent" / "AGENTS.md"
        shared, _private = self.bind(target)
        self.assertEqual(len(shared), 1)
        self.assertEqual(shared[0]["target"], str(target))

    def test_default_target_rejected_when_root_missing(self) -> None:
        target = self.home / ".omp" / "agent" / "AGENTS.md"
        with self.assertRaises(ContractError):
            self.bind(target)


if __name__ == "__main__":
    unittest.main()
