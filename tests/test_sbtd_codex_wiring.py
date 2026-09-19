from __future__ import annotations

import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard/scripts"
sys.path.insert(0, str(SCRIPTS))


class CodexCandidateTests(unittest.TestCase):
    def binding(self, base):
        return {
            name: str(base / value)
            for name, value in {
                "root": "project",
                "node": "runtime/node",
                "cli": "package/dist/cli.js",
                "python": "runtime/python",
                "launcher": "installed/scripts/sbtd_graft_entry.py",
            }.items()
        }

    def test_hooks_require_authorization_and_preserve_every_foreign_handler(self):
        from sbtd_codex_wiring import codex_hooks_candidate

        with tempfile.TemporaryDirectory() as directory:
            binding = self.binding(Path(directory).resolve())
            original = b'{"description":"user-owned","hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"echo keep-prompt","timeout":5}]}],"Stop":[{"hooks":[{"type":"command","command":"echo keep-stop","timeout":5}]}]}}\n'
            self.assertEqual(
                codex_hooks_candidate(original, [binding], authorized=False), original
            )
            rendered = codex_hooks_candidate(original, [binding], authorized=True)
            parsed = json.loads(rendered)
            self.assertEqual(parsed["description"], "user-owned")
            for event, command in (
                ("UserPromptSubmit", "echo keep-prompt"),
                ("Stop", "echo keep-stop"),
            ):
                commands = [
                    handler["command"]
                    for group in parsed["hooks"][event]
                    for handler in group["hooks"]
                ]
                self.assertEqual(commands.count(command), 1)
            self.assertEqual(
                codex_hooks_candidate(rendered, [binding], authorized=True), rendered
            )
            self.assertNotIn("trusted_hash", rendered.decode())

    def test_modified_managed_executable_paths_are_not_silently_replaced(self):
        from onboard_contracts import ContractError
        import sbtd_codex_wiring as wiring

        with tempfile.TemporaryDirectory() as directory:
            binding = self.binding(Path(directory).resolve())
            # POSIX dialect, pinned so the shlex round-trip below is truthful
            # on any host; the Windows dialect has its own variant.
            with mock.patch.object(wiring, "_WINDOWS", False):
                original = wiring.codex_hooks_candidate(b"", [binding], authorized=True)
                for boundary in ("python", "--node", "--entry"):
                    document = json.loads(original)
                    handler = document["hooks"]["UserPromptSubmit"][0]["hooks"][0]
                    arguments = shlex.split(handler["command"])
                    position = (
                        0 if boundary == "python" else arguments.index(boundary) + 1
                    )
                    arguments[position] = str(
                        Path(directory) / "user-modified-executable"
                    )
                    handler["command"] = shlex.join(arguments)
                    changed = json.dumps(document).encode()
                    with (
                        self.subTest(boundary=boundary),
                        self.assertRaises(ContractError),
                    ):
                        wiring.codex_hooks_candidate(
                            changed, [binding], authorized=True
                        )

    def test_agents_fence_update_preserves_non_owned_bytes(self):
        from onboard_contracts import ContractError
        from sbtd_codex_wiring import project_agents_candidate

        original = b"# User instructions\r\nKeep this spacing.  \r\n<!-- graft:start -->\nOld instructions.\n<!-- graft:end -->\r\n\nUser suffix.\n"
        candidate = project_agents_candidate(original)
        self.assertTrue(
            candidate.startswith(b"# User instructions\r\nKeep this spacing.  \r\n")
        )
        self.assertTrue(candidate.endswith(b"\r\n\nUser suffix.\n"))
        self.assertNotIn(b"Old instructions.", candidate)
        self.assertEqual(project_agents_candidate(candidate), candidate)
        with self.assertRaises(ContractError):
            project_agents_candidate(original + b"<!-- graft:start -->broken")

    def test_mcp_bindings_keep_projects_distinct_and_preserve_foreign_toml(self):
        import tomlkit
        from sbtd_codex_wiring import codex_mcp_candidate

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            first = self.binding(base / "one")
            second = self.binding(base / "two")
            original = b'# User comment\nmodel = "user-model"\n\n[mcp_servers.foreign]\ncommand = "keep-me" # preserve this comment\n'
            candidate = codex_mcp_candidate(original, [first, second])
            parsed = tomlkit.parse(candidate.decode())
            self.assertEqual(parsed["model"], "user-model")
            self.assertEqual(parsed["mcp_servers"]["foreign"]["command"], "keep-me")
            self.assertIn(b"# User comment", candidate)
            self.assertIn(b"# preserve this comment", candidate)
            servers = [
                value
                for key, value in parsed["mcp_servers"].items()
                if key != "foreign"
            ]
            self.assertEqual(
                {server["cwd"] for server in servers}, {first["root"], second["root"]}
            )
            for server in servers:
                self.assertEqual(
                    server["args"][server["args"].index("--root") + 1], server["cwd"]
                )
            self.assertEqual(codex_mcp_candidate(candidate, [first, second]), candidate)

    def test_stop_hook_timeout_outlasts_the_native_sync_cap(self):
        from sbtd_codex_wiring import codex_hooks_candidate

        with tempfile.TemporaryDirectory() as directory:
            binding = self.binding(Path(directory).resolve())
            parsed = json.loads(codex_hooks_candidate(b"", [binding], authorized=True))
            # Native sync may consume its full 120-second cap; the host must
            # leave time for the managed launcher to observe and clean it up.
            self.assertGreater(parsed["hooks"]["Stop"][0]["hooks"][0]["timeout"], 120)

    def test_windows_hook_command_round_trips_argv_and_stays_idempotent(self):
        import sbtd_codex_wiring as wiring

        with tempfile.TemporaryDirectory() as directory:
            binding = self.binding(Path(directory).resolve() / "root with spaces")
            original = (
                b'{"description":"user-owned","hooks":{"Stop":[{"hooks":'
                b'[{"type":"command","command":"echo keep & echo both","timeout":5}]}]}}\n'
            )
            with mock.patch.object(wiring, "_WINDOWS", True):
                rendered = wiring.codex_hooks_candidate(
                    original, [binding], authorized=True
                )
                parsed = json.loads(rendered)
                groups = parsed["hooks"]["Stop"]
                owned = [
                    handler["command"]
                    for group in groups
                    for handler in group["hooks"]
                    if handler["command"] != "echo keep & echo both"
                ]
                self.assertEqual(len(owned), 1)
                self.assertNotIn("'", owned[0])
                self.assertIn('"', owned[0])
                # The foreign handler — metacharacters and all — is preserved.
                self.assertEqual(
                    [h["command"] for g in groups for h in g["hooks"]].count(
                        "echo keep & echo both"
                    ),
                    1,
                )
                self.assertEqual(parsed["description"], "user-owned")
                self.assertEqual(
                    wiring.codex_hooks_candidate(rendered, [binding], authorized=True),
                    rendered,
                )

    def test_windows_foreign_owned_shaped_command_is_never_claimed_or_refused(self):
        import sbtd_codex_wiring as wiring

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            binding = self.binding(base)
            foreign_argv = [
                binding["python"],
                binding["launcher"],
                "hook",
                "--root",
                str(base / "foreign&%!root project"),
                "--node",
                binding["node"],
                "--entry",
                binding["cli"],
                "--event",
                "stop",
            ]
            foreign_command = subprocess.list2cmdline(foreign_argv)
            original = json.dumps(
                {
                    "hooks": {
                        "Stop": [
                            {
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": foreign_command,
                                        "timeout": 5,
                                    }
                                ]
                            }
                        ]
                    }
                }
            ).encode()
            with mock.patch.object(wiring, "_WINDOWS", True):
                rendered = wiring.codex_hooks_candidate(
                    original, [binding], authorized=True
                )
                commands = [
                    handler["command"]
                    for group in json.loads(rendered)["hooks"]["Stop"]
                    for handler in group["hooks"]
                ]
                # Same launcher shape but a different root: strictly foreign —
                # preserved verbatim, never refused for its metacharacters and
                # never reconciled into the managed entry.
                self.assertEqual(commands.count(foreign_command), 1)
                self.assertEqual(len(commands), 2)

    def test_windows_paths_with_live_cmd_operators_are_refused(self):
        from onboard_contracts import ContractError
        import sbtd_codex_wiring as wiring

        unsafe = {
            "root": "unsafe&command",
            "python": "%COMSPEC%",
            "launcher": "unsafe!expanded!",
            "node": "unsafe|command",
            "cli": "unsafe\ncommand",
        }
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            for key, value in unsafe.items():
                binding = self.binding(base)
                binding[key] = str(base / value)
                with self.subTest(key=key), mock.patch.object(wiring, "_WINDOWS", True):
                    with self.assertRaises(ContractError) as failure:
                        wiring.codex_hooks_candidate(b"", [binding], authorized=True)
                    self.assertEqual(failure.exception.code, "invalid-argument")
            # POSIX rendering is unchanged: the same path is safely quoted,
            # not refused (dialect pinned so this is truthful on any host).
            binding = self.binding(base)
            binding["root"] = str(base / "unsafe&segment")
            with mock.patch.object(wiring, "_WINDOWS", False):
                rendered = wiring.codex_hooks_candidate(b"", [binding], authorized=True)
            command = json.loads(rendered)["hooks"]["Stop"][0]["hooks"][0]["command"]
            self.assertIn("'", command)
            self.assertEqual(shlex.split(command)[4], binding["root"])

    def test_windows_modified_managed_executable_paths_are_not_silently_replaced(self):
        from onboard_contracts import ContractError
        import sbtd_codex_wiring as wiring

        with tempfile.TemporaryDirectory() as directory:
            binding = self.binding(Path(directory).resolve())
            with mock.patch.object(wiring, "_WINDOWS", True):
                original = wiring.codex_hooks_candidate(b"", [binding], authorized=True)
                for boundary in ("python", "--node", "--entry"):
                    document = json.loads(original)
                    handler = document["hooks"]["UserPromptSubmit"][0]["hooks"][0]
                    arguments = wiring._split_hook_command(handler["command"])
                    position = (
                        0 if boundary == "python" else arguments.index(boundary) + 1
                    )
                    arguments[position] = str(
                        Path(directory) / "user-modified-executable"
                    )
                    handler["command"] = subprocess.list2cmdline(arguments)
                    changed = json.dumps(document).encode()
                    with (
                        self.subTest(boundary=boundary),
                        self.assertRaises(ContractError),
                    ):
                        wiring.codex_hooks_candidate(
                            changed, [binding], authorized=True
                        )


if __name__ == "__main__":
    unittest.main()
