"""rc.3 deploy cutover: refuse sealed Graft writes; write the approved body.

No smoke is invented. A sealed Graft operation fails before any backup or
target write. An approved-agents ensure-file-block writes the pause-stripped
body, not a template and not the pause prefix.
"""

from __future__ import annotations

import stat
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from onboard_contracts import ContractError, archived_graft_policy
from sbtd_deployment import approved_agents_selector, execute_resource, reject_legacy_execution
from sbtd_migration_files import snapshot
from sbtd_migration_plan import _check_followup_predecessor_outcomes

_GONE = (
    "verified_runtime",
    "build_project_graph",
    "launch_bindings",
    "run_native",
    "run_project_smoke",
    "render_configuration",
    "plan_normal_wiring",
    "execute_normal_wiring",
    "deployment_operations",
    "policy_reference",
    "archived_policy_reference",
)


class Rc3DeployCutoverTests(unittest.TestCase):
    def test_deleted_graft_launchers_are_absent(self):
        import sbtd_deployment

        for name in _GONE:
            self.assertFalse(hasattr(sbtd_deployment, name), name)

    def test_sealed_graft_operation_rejects_before_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "AGENTS.md"
            target.write_bytes(b"keep\n")
            before = target.read_bytes()
            mode = stat.S_IMODE(target.stat().st_mode)
            backup = root / "backup"
            with self.assertRaises(ContractError) as raised:
                execute_resource(
                    {
                        "resource_id": "rid",
                        "operation_id": "oid",
                        "dependent_projects": [str(root)],
                        "target": str(target),
                        "selector": "graft-agents",
                        "change": {"kind": "configure-graft"},
                    },
                    expected={"type": "file", "checksum": "unused"},
                    root=root,
                    private_root=root / "vault",
                    backup_path=backup,
                )
            self.assertEqual(raised.exception.code, "unsupported-in-rc.3")
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), mode)
            self.assertFalse(backup.exists())

    def test_reject_legacy_execution_does_not_touch_the_target(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "config.toml"
            target.write_bytes(b"before\n")
            before = target.read_bytes()
            with self.assertRaises(ContractError) as raised:
                reject_legacy_execution(
                    {
                        "projects": [
                            {
                                "private_operations": [
                                    {
                                        "selector": "graft-mcp",
                                        "change": {"kind": "copy-file"},
                                    }
                                ]
                            }
                        ],
                        "shared_operations": [],
                    }
                )
            self.assertEqual(raised.exception.code, "unsupported-in-rc.3")
            self.assertEqual(target.read_bytes(), before)

    def test_approved_agents_write_strips_pause_after_preflight(self):
        pause = (
            Path(__file__).resolve().parents[1]
            / "sbtd-workflow-onboard"
            / "assets"
            / "migration-paused-agents.txt"
        ).read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "project"
            vault = base / "vault"
            root.mkdir(mode=0o700)
            vault.mkdir(mode=0o700)
            body = b"unique-approved-body-8e2b4c\n"
            candidate = vault / "candidate.md"
            candidate.write_bytes(pause + b"\n" + body)
            target = root / "AGENTS.md"
            target.write_bytes(pause + b"\n" + body)
            before = target.read_bytes()
            result = execute_resource(
                {
                    "phase": "deploy",
                    "resource_id": "rid",
                    "operation_id": "oid",
                    "dependent_projects": [str(root)],
                    "target": str(target),
                    "selector": approved_agents_selector(body),
                    "change": {
                        "kind": "ensure-file-block",
                        "source_ref": {
                            "path": str(candidate),
                            "state": snapshot(candidate),
                        },
                    },
                },
                expected=snapshot(target),
                root=root,
                private_root=vault,
                backup_path=vault / "backup",
            )
            self.assertEqual(result["status"], "succeeded")
            self.assertEqual(target.read_bytes(), body)
            self.assertNotEqual(target.read_bytes(), before)
            self.assertFalse((vault / "approved-agents").exists())
            self.assertNotIn(b"AGENTS.project.md", target.read_bytes())

    def test_readonly_followup_binds_predecessor_graft_and_mutation_rejects(self):
        policy = archived_graft_policy()
        operation = {
            "phase": "deploy",
            "target": "/tmp/project/graft",
            "resource_id": "rid",
            "selector": "whole-resource",
            "change": {"kind": "build-graft", "source_ref": policy},
        }
        manifest = {
            "payload": {
                "projects": [
                    {
                        "root": "/tmp/project",
                        "agents_no_touch": {"bound": True},
                        "private_operations": [operation],
                    }
                ],
                "shared_operations": [],
            }
        }
        chain = [
            (
                manifest,
                {
                    "deploy": {
                        "rid": {
                            "status": "succeeded",
                            "after": {"type": "directory", "checksum": "ab" * 32},
                        }
                    }
                },
            )
        ]
        with self.assertRaises(ContractError) as raised:
            _check_followup_predecessor_outcomes(chain, overwritten=())
        self.assertEqual(raised.exception.code, "unsupported-in-rc.3")
        outcomes = _check_followup_predecessor_outcomes(
            chain, overwritten=(), bind_historical=True
        )
        self.assertEqual(
            outcomes["/tmp/project/graft"]["type"],
            "directory",
        )

    def test_real_smoke_refs_are_on_disk_and_do_not_rewrite_the_seal(self):
        from sbtd_deployment_smoke import run_project_smoke

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "project"
            evidence = base / "evidence"
            root.mkdir(mode=0o700)
            evidence.mkdir(mode=0o700)
            sealed = root / "AGENTS.md"
            sealed.write_bytes(b"sealed-approved-body\n")
            before = sealed.read_bytes()
            refs = run_project_smoke(root, evidence)
            self.assertEqual(len(refs), 2)
            report, summary = (Path(ref["path"]) for ref in refs)
            self.assertEqual(report.suffix, ".json")
            self.assertEqual(report.stem, summary.stem)
            self.assertNotEqual(summary.suffix, ".json")
            for ref in refs:
                path = Path(ref["path"])
                self.assertTrue(path.is_file())
                self.assertTrue(path.is_relative_to(evidence))
                self.assertEqual(snapshot(path), ref["state"])
            self.assertEqual(sealed.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
