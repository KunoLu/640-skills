"""Follow-up predecessor gates: configure-graft section ownership.

A completed batch's configure-graft outcomes (Codex config.toml, hooks.json,
OMP mcp.json, project AGENTS.md fences) are gated by managed-section
ownership, not whole-file equality: the host runtime may append sections
beside the graft-owned entries. Every case builds its own temporary
predecessor chain; nothing reads private deployment evidence.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from onboard_contracts import ContractError
from sbtd_codex_wiring import (
    codex_hooks_candidate,
    codex_mcp_candidate,
    project_agents_candidate,
)
from sbtd_migration_files import snapshot
from sbtd_migration_plan import _check_followup_predecessor_outcomes
from sbtd_omp_wiring import desired_omp_server


def _bindings(root):
    return {
        "root": str(root),
        "node": "/fixture/node",
        "cli": "/fixture/pkg/dist/cli.js",
        "python": "/fixture/python",
        "launcher": "/fixture/pkg/scripts/sbtd_graft_entry.py",
    }


def _omp_server_name(root):
    digest = hashlib.sha256(str(root).encode("utf-8")).hexdigest()
    return f"sbtd-graft-{digest[:16]}"


def _chain(target, selector, roots, *, kind="configure-graft"):
    operation = {
        "phase": "deploy",
        "resource_id": "resource-1",
        "target": str(target),
        "selector": selector,
        "change": {"kind": kind, "source_ref": "policy"},
        "dependent_projects": sorted(str(root) for root in roots),
    }
    manifest = {"payload": {"projects": [], "shared_operations": [operation]}}
    result = {"status": "succeeded", "after": snapshot(Path(target))}
    return [(manifest, {"deploy": {"resource-1": result}})]


def _check(target, selector, roots, *, kind="configure-graft"):
    return _check_followup_predecessor_outcomes(
        _chain(target, selector, roots, kind=kind), overwritten=()
    )


class FollowupSectionGateTests(unittest.TestCase):
    def assert_conflict(self, target, selector, roots, *, kind="configure-graft"):
        with self.assertRaises(ContractError) as error:
            _check(target, selector, roots, kind=kind)
        self.assertEqual(error.exception.code, "state-conflict")

    def _codex_config(self, base, roots):
        target = base / "config.toml"
        target.write_bytes(
            codex_mcp_candidate(b"", [_bindings(root) for root in roots])
        )
        return target

    def test_toml_host_appended_sections_do_not_block(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = base / "project"
            target = self._codex_config(base, [root])
            target.write_bytes(
                target.read_bytes()
                + b'\n[hooks.state.persist]\nenabled = true\n'
                + b'[projects."/other"]\ntrust_level = "trusted"\n'
                + b"[desktop]\nnotifications = false\n"
            )
            outcome = _check(target, "graft-mcp", [root])
            self.assertIn(str(target), outcome)

    def test_toml_managed_entry_tampering_still_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = base / "project"

            target = self._codex_config(base, [root])
            changed = target.read_bytes().replace(
                b"/fixture/pkg/dist/cli.js", b"/fixture/pkg/dist/other.js"
            )
            self.assertNotEqual(changed, target.read_bytes())
            target.write_bytes(changed)
            self.assert_conflict(target, "graft-mcp", [root])

            target = self._codex_config(base, [root])
            text = target.read_text(encoding="utf-8")
            start = text.index("[mcp_servers.")
            target.write_text(text[:start], encoding="utf-8")
            self.assert_conflict(target, "graft-mcp", [root])

            target = self._codex_config(base, [root])
            extra = dict(_bindings(root))
            extra["root"] = str(base / "other")
            target.write_bytes(
                codex_mcp_candidate(
                    target.read_bytes(), [_bindings(root), extra]
                )
            )
            self.assert_conflict(target, "graft-mcp", [root])

            target = self._codex_config(base, [root])
            changed = target.read_bytes().replace(b'DNT = "1"', b'DNT = "0"')
            self.assertNotEqual(changed, target.read_bytes())
            target.write_bytes(changed)
            self.assert_conflict(target, "graft-mcp", [root])

            target.unlink()
            self.assert_conflict(target, "graft-mcp", [root])

    def test_omp_host_appended_server_does_not_block(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = base / "project"
            target = base / "mcp.json"
            document = {
                "mcpServers": {
                    _omp_server_name(root): desired_omp_server(_bindings(root))
                }
            }
            target.write_text(json.dumps(document), encoding="utf-8")
            document["mcpServers"]["unrelated"] = {
                "type": "stdio",
                "command": "/usr/bin/true",
                "args": [],
            }
            target.write_text(json.dumps(document), encoding="utf-8")
            outcome = _check(target, "graft-omp-mcp", [root])
            self.assertIn(str(target), outcome)

    def test_omp_managed_entry_tampering_still_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = base / "project"
            target = base / "mcp.json"
            document = {
                "mcpServers": {
                    _omp_server_name(root): desired_omp_server(_bindings(root))
                }
            }
            target.write_text(json.dumps(document), encoding="utf-8")
            managed = document["mcpServers"][_omp_server_name(root)]
            managed["args"][-1] = "/fixture/pkg/dist/other.js"
            target.write_text(json.dumps(document), encoding="utf-8")
            self.assert_conflict(target, "graft-omp-mcp", [root])

    def test_agents_user_text_outside_fence_does_not_block(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = base / "project"
            target = base / "AGENTS.md"
            target.write_bytes(project_agents_candidate(b"# Project\n"))
            target.write_bytes(
                target.read_bytes() + b"\nUser notes outside the fence.\n"
            )
            outcome = _check(target, "graft-agents", [root])
            self.assertIn(str(target), outcome)

    def test_agents_fence_tampering_still_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = base / "project"
            target = base / "AGENTS.md"
            original = project_agents_candidate(b"# Project\n")

            target.write_bytes(
                original.replace(
                    b"\n<!-- graft:end -->", b"\nedited\n<!-- graft:end -->"
                )
            )
            self.assert_conflict(target, "graft-agents", [root])

            target.write_bytes(b"# Project with no fence at all\n")
            self.assert_conflict(target, "graft-agents", [root])

            target.write_bytes(original + original)
            self.assert_conflict(target, "graft-agents", [root])

    def _hooks(self, base, roots):
        target = base / "hooks.json"
        target.write_bytes(
            codex_hooks_candidate(
                b"", [_bindings(root) for root in roots], authorized=True
            )
        )
        return target

    def test_hooks_unrelated_hook_does_not_block(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = base / "project"
            target = self._hooks(base, [root])
            document = json.loads(target.read_bytes())
            document["hooks"]["SessionStart"].append(
                {
                    "matcher": "startup",
                    "hooks": [
                        {"type": "command", "command": "/usr/bin/true", "timeout": 5}
                    ],
                }
            )
            target.write_text(json.dumps(document), encoding="utf-8")
            outcome = _check(target, "graft-hooks", [root])
            self.assertIn(str(target), outcome)

    def test_hooks_managed_command_tampering_still_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = base / "project"
            target = self._hooks(base, [root])
            changed = target.read_bytes().replace(
                b"/fixture/pkg/dist/cli.js", b"/fixture/pkg/dist/other.js", 1
            )
            self.assertNotEqual(changed, target.read_bytes())
            target.write_bytes(changed)
            self.assert_conflict(target, "graft-hooks", [root])

    def test_non_configure_graft_drift_still_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = base / "project"
            target = base / "notes.txt"
            target.write_bytes(b"original\n")
            chain = _chain(target, "whole-resource", [root], kind="ensure-file-block")
            outcome = _check_followup_predecessor_outcomes(chain, overwritten=())
            self.assertIn(str(target), outcome)
            target.write_bytes(b"drifted\n")
            with self.assertRaises(ContractError) as error:
                _check_followup_predecessor_outcomes(chain, overwritten=())
            self.assertEqual(error.exception.code, "state-conflict")


if __name__ == "__main__":
    unittest.main()
