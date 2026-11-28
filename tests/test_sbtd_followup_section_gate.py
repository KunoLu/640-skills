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
from sbtd_migration_plan import _check_followup_predecessor_outcomes


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
            "projects": [{"private_operations": [operation]}],
            "shared_operations": [],
        }
    }
    result = {"status": "succeeded", "after": after}
    return [(manifest, {"deploy": {operation["resource_id"]: result}})]


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
