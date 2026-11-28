"""Follow-up predecessor gates after Graft section ownership is gone.

A sealed Graft operation is unsupported in rc.3 and must not write.
Non-Graft predecessor targets still fail closed when live bytes drift from
the recorded outcome, unless the followup batch itself overwrites that target.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from onboard_contracts import ContractError, operation_id, resource_id
from sbtd_deployment import reject_legacy_execution
from sbtd_migration_files import snapshot
from sbtd_migration_plan import (
    _check_followup_predecessor_outcomes,
    _historical_followup_fence_before,
)


def _copy_operation(target: Path) -> dict:
    rid = resource_id("markdown", str(target))
    return {
        "phase": "deploy",
        "resource_id": rid,
        "operation_id": operation_id("deploy", rid, "whole-resource"),
        "owner_kind": "markdown",
        "target": str(target),
        "selector": "whole-resource",
        "change": {"kind": "copy-file", "source_ref": {"path": str(target), "state": snapshot(target)}},
        "dependent_projects": [str(target.parent)],
    }


def _chain(operation: dict, after: dict) -> list:
    manifest = {
        "payload": {
            "projects": [{
                "root": str(Path(operation["target"]).parent),
                "private_operations": [operation],
            }],
            "shared_operations": [],
        }
    }
    result = {"status": "succeeded", "after": after}
    return [(manifest, {operation["phase"]: {operation["resource_id"]: result}})]


class FollowupPredecessorGateTests(unittest.TestCase):
    def test_configure_graft_outcome_is_unsupported_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "AGENTS.md"
            target.write_bytes(b"live rules\n")
            before = target.read_bytes()
            mode = target.stat().st_mode
            with self.assertRaises(ContractError) as raised:
                reject_legacy_execution(
                    {
                        "projects": [
                            {
                                "private_operations": [
                                    {
                                        "change": {"kind": "configure-graft"},
                                        "target": str(target),
                                    }
                                ]
                            }
                        ],
                        "shared_operations": [],
                    }
                )
            self.assertEqual(raised.exception.code, "unsupported-in-rc.3")
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(target.stat().st_mode, mode)

    def test_non_graft_predecessor_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "AGENTS.md"
            target.write_bytes(b"recorded\n")
            operation = _copy_operation(target)
            recorded = snapshot(target)
            target.write_bytes(b"recorded\nedited\n")
            with self.assertRaises(ContractError) as raised:
                _check_followup_predecessor_outcomes(
                    _chain(operation, recorded), overwritten=()
                )
            self.assertEqual(raised.exception.code, "state-conflict")
            self.assertEqual(target.read_bytes(), b"recorded\nedited\n")

    def test_retired_marker_not_unrelated_edits_is_the_predecessor_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve() / "AGENTS.md"
            target.write_bytes(b"user notes\n")
            operation = _copy_operation(target)
            operation.update(
                phase="apply", selector="trellis-block", change={"kind": "remove"},
                ownership={"kind": "managed-marker", "marker": "TRELLIS"},
            )
            recorded = snapshot(target)
            edited = b"user notes\nNew user note.\n\n```md\n<!-- TRELLIS:START -->\n```\n"
            target.write_bytes(edited)
            chain = _chain(operation, recorded)
            self.assertEqual(
                _check_followup_predecessor_outcomes(chain, overwritten=())[str(target)],
                recorded,
            )
            self.assertEqual(target.read_bytes(), edited)

            for marker in (b"<!-- TRELLIS:START -->", b"<!-- TRELLIS:END -->"):
                target.write_bytes(edited + marker + b"\n")
                with self.assertRaises(ContractError) as raised:
                    _check_followup_predecessor_outcomes(chain, overwritten=())
                self.assertEqual(raised.exception.code, "state-conflict")
                self.assertEqual(target.read_bytes(), edited + marker + b"\n")

    def test_historical_followup_uses_intact_fence_in_bound_original(self):
        # Exact body written by the rc.2 producer, not a test replacement pin.
        body = (
            b"## Graft structural evidence (managed)\n\n"
            b"This project is wired to the pinned local Graft CLI (@nanonets/graft@0.29.0) by the "
            b"SBTD onboard CLI, the only writer of this fence, host MCP entries, and Codex hook "
            b"entries. The managed launcher proves the selected graph before forwarding each MCP "
            b"request; native post-launch refresh remains disabled.\n\n"
            b"- Use the enabled global managed launcher (`sbtd_graft_entry.py`) in the active host "
            b"configuration. Its normal name is `sbtd-graft`; it has no fixed cwd/root argument "
            b"and selects the nearest initialized Git repository/worktree from the MCP process's "
            b"actual startup cwd. Confirm this connection's project before relying on its results. "
            b"Project-only setup prepares the graph, not host registration; if the global connection "
            b"is unavailable, use source/LSP evidence. Never spawn upstream `graft`/`npx` servers "
            b"or hook shims directly. The launcher revalidates graph data before every request.\n"
            b"- Each connection locks one repository root for its entire lifetime. Shell cwd changes "
            b"do not retarget it; start a new host connection for another project. HOME, missing "
            b"project context, missing/old graph state and uninitialized nested repositories fail "
            b"closed, never borrowing a demo, parent or sibling graph. A real external Git executable "
            b"must be available on an absolute PATH entry; project-local and relative PATH entries "
            b"cannot provide the root proof.\n"
            b"- If the managed launcher fails its guard (fixed stderr message, exit 2), stop using "
            b"Graft here and ask the user for an explicit wiring re-init through the onboard CLI. "
            b"Never repair, bypass or replace the guard, never run upstream "
            b"`graft init`/`mcp`/hook shims, and never hand-edit MCP/hook configuration as a workaround.\n"
            b"- Always prohibited: telemetry, `--deep`, `blast --name` or any other LLM symbol naming, "
            b"brain/trail connect, signup, pull or other cloud activation, automatic LLM enrichment, "
            b"and publishing graphs, blasts, code or query output to PRs, public viewers or knowledge "
            b"services. Do not set, print or persist `GRAFT_API_KEY` or other provider keys; managed "
            b"children start with Python startup environment isolation (`-E -s`), run with "
            b"`DO_NOT_TRACK=1`, and use a scrubbed LLM/cloud environment.\n"
            b"- Graft output is downgradable structural evidence, never proof: an empty result or "
            b"exit 0 does not prove no impact, and conclusions still need source/LSP confirmation. "
            b"If the graph is missing, stale or blocked, continue with source reading and report "
            b"Graft as skipped/blocked. Hooks are a separate persisted opt-in; absent hooks are not "
            b"a failure and must not be fabricated."
        )
        with tempfile.TemporaryDirectory() as directory:
            backup = Path(directory).resolve() / "before"

            def original(fence_body):
                backup.write_bytes(
                    b"New operator note.\n\n<!-- graft:start -->\n"
                    + fence_body
                    + b"\n<!-- graft:end -->\n\nMore unrelated text.\n",
                )
                state = snapshot(backup)
                return {
                    "status": "succeeded",
                    "before": state,
                    "backup_ref": {"path": str(backup), "state": state},
                }

            before = original(body)
            self.assertEqual(_historical_followup_fence_before(before), snapshot(backup))
            changed = original(body + b"\nUnexpected change inside the fence.")
            with self.assertRaises(ContractError) as invalid:
                _historical_followup_fence_before(changed)
            self.assertEqual(invalid.exception.code, "ownership-conflict")
            with self.assertRaises(ContractError) as replaced:
                _historical_followup_fence_before(before)
            self.assertEqual(replaced.exception.code, "state-conflict")

    def test_overwritten_non_graft_target_is_not_gated_here(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "AGENTS.md"
            target.write_bytes(b"recorded\n")
            operation = _copy_operation(target)
            recorded = snapshot(target)
            target.write_bytes(b"followup will replace\n")
            outcomes = _check_followup_predecessor_outcomes(
                _chain(operation, recorded), overwritten={str(target)}
            )
            self.assertEqual(outcomes[str(target)], recorded)
            self.assertEqual(target.read_bytes(), b"followup will replace\n")


if __name__ == "__main__":
    unittest.main()
