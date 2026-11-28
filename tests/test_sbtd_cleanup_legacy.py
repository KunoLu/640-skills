from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from onboard_contracts import canonical_json_bytes, operation_id, resource_id
from sbtd_cleanup_legacy import apply_cleanup_legacy, plan_cleanup_legacy
from sbtd_migration_files import (
    backup_reference,
    remove_reference,
    require_private_directory,
    snapshot,
)

AGENTS_RAW = (
    b"<!-- TRELLIS:START -->\nlegacy route\n<!-- TRELLIS:END -->\n\n"
    b"<!-- gitnexus:start -->\nlegacy index notes\n<!-- gitnexus:end -->\n\n"
    b"# own rules\n\n<!-- graft:start -->\nfence\n<!-- graft:end -->\n"
)
AGENTS_CLEAN = b"\n\n# own rules\n\n<!-- graft:start -->\nfence\n<!-- graft:end -->\n"
AGENTS_LEGACY_ONLY = (
    b"<!-- TRELLIS:START -->\nlegacy route\n<!-- TRELLIS:END -->\n\n"
    b"<!-- gitnexus:start -->\nlegacy index notes\n<!-- gitnexus:end -->\n"
)
AGENTS_ONLY_SCRUBBED = (
    b"<!-- gitnexus:start -->\nlegacy index notes\n<!-- gitnexus:end -->\n"
)


def _vendor_scrub(raw: bytes) -> bytes:
    """Test-only vendor effect: drop the TRELLIS block and its blank line."""
    start = raw.index(b"<!-- TRELLIS:START -->")
    stop = raw.index(b"<!-- TRELLIS:END -->") + len(b"<!-- TRELLIS:END -->")
    if raw[stop : stop + 2] == b"\r\n":
        stop += 2
    elif raw[stop : stop + 1] == b"\n":
        stop += 1
    if raw[stop : stop + 1] == b"\n":
        stop += 1
    return raw[:start] + raw[stop:]


def _fake_vendor_prepare(root, *, environ=None):
    """Test-only vendor seam; production always uses the installed tl CLI."""
    root = Path(root)
    agents = root / "AGENTS.md"
    trellis = root / ".trellis"
    payload = {
        "root": str(root),
        "status": "ready",
        "resources": [
            {
                "resource_id": "trellis-000",
                "kind": "vendor-scrub",
                "path": str(agents),
                "relative": "AGENTS.md",
                "before": snapshot(agents),
                "expected_after": {
                    "type": "file",
                    "checksum": hashlib.sha256(
                        _vendor_scrub(agents.read_bytes())
                    ).hexdigest(),
                },
            },
            {
                "resource_id": "trellis-001",
                "kind": "vendor-trellis-dir",
                "path": str(trellis),
                "relative": ".trellis",
                "before": snapshot(trellis),
                "expected_after": {"type": "absent", "checksum": None},
            },
        ],
    }
    return {
        "schema_version": 1,
        "kind": "trellis-uninstall-prepare",
        "prepared_id": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
        "payload": payload,
    }


def _fake_vendor_execute(root, prepared, backup_root, *, environ=None, before_execute=None, partial=False):
    """Run test-double vendor effects with real private backups and measures."""
    vault = Path(backup_root)
    backup_dir = require_private_directory(vault / prepared["prepared_id"], create=True)
    resources_dir = require_private_directory(backup_dir / "resources", create=True)
    resources = prepared["payload"]["resources"]
    backups = [
        backup_reference(
            {"path": resource["path"], "state": resource["before"]},
            resources_dir / f"{index:03d}",
            private_root=vault,
        )
        for index, resource in enumerate(resources)
    ]
    if before_execute is not None:
        before_execute()
    for resource in resources:
        path = Path(resource["path"])
        if resource["kind"] == "vendor-scrub":
            path.write_bytes(_vendor_scrub(path.read_bytes()))  # Test double only.
        elif not partial:
            if path.is_dir():
                shutil.rmtree(path)  # Test double only; production never deletes .trellis.
            else:
                path.unlink()
    results = []
    for resource, backup_ref in zip(resources, backups):
        after = snapshot(Path(resource["path"]))
        results.append(
            {
                "resource_id": resource["resource_id"],
                "kind": resource["kind"],
                "path": resource["path"],
                "relative": resource["relative"],
                "before": resource["before"],
                "backup_ref": backup_ref,
                "after": after,
                "status": (
                    ("scrubbed" if resource["kind"] == "vendor-scrub" else "removed")
                    if after == resource["expected_after"]
                    else "unchanged"
                ),
            }
        )
    return {
        "status": "partial" if partial else "removed",
        "root": str(root),
        "prepared_id": prepared["prepared_id"],
        "exit": 1 if partial else 0,
        "results": results,
        "errors": ["vendor-refused: simulated refusal"] if partial else [],
    }


@contextmanager
def _fake_vendor(*, prepare=_fake_vendor_prepare, execute=None):
    with (
        mock.patch(
            "sbtd_trellis_uninstall.prepare_trellis_uninstall",
            side_effect=prepare,
        ),
        mock.patch(
            "sbtd_trellis_uninstall.execute_trellis_uninstall",
            side_effect=execute or _fake_vendor_execute,
        ),
    ):
        yield


def _refuse_gitnexus_removal(path, expected, *, scope):
    if Path(path).name == ".gitnexus":
        raise OSError("simulated removal failure")
    return remove_reference(path, expected, scope=scope)


class CleanupLegacyFixture:
    def __init__(self, base: Path) -> None:
        self.base = base.resolve()
        self.home = self.base / "home"
        self.vault = self.base / "vault"
        self.skills = self.home / ".agent/skills"
        self.project = self.base / "project"
        self.home.mkdir(mode=0o700)
        require_private_directory(self.vault, create=True)
        self.skills.mkdir(parents=True)
        (self.home / ".codex").mkdir()
        (self.home / ".codex/config.toml").write_text(
            '[mcp_servers.gitnexus]\ncommand = "gitnexus"\n\n'
            '[mcp_servers.context7]\ncommand = "npx"\n'
        )
        (self.home / ".claude.json").write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "gitnexus": {"command": "gitnexus"},
                        "playwright": {"command": "npx"},
                    }
                }
            )
        )
        for relative in (".kimi-code/mcp.json", ".omp/agent/mcp.json"):
            config = self.home / relative
            config.parent.mkdir(parents=True)
            config.write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "gitnexus": {"command": "gitnexus"},
                            "custom-index": {
                                "command": "node",
                                "args": [
                                    "/opt/node_modules/gitnexus/dist/cli/index.js",
                                    "mcp",
                                ],
                            },
                            "browser": {"command": "npx", "args": ["@playwright/mcp"]},
                        }
                    }
                )
            )
        (self.project / ".gitnexus/index").mkdir(parents=True)
        (self.project / ".gitnexus/index/db.bin").write_bytes(b"\x00db\xff")
        (self.project / "AGENTS.md").write_bytes(AGENTS_RAW)
        skill = self.skills / "trellis-workflow"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            "---\nname: trellis-workflow\n---\nOld 1.0.7 payload\n"
        )
        self.environ = {
            "HOME": str(self.home),
            "USERPROFILE": str(self.home),
            "CODEX_HOME": str(self.home / ".codex"),
            "AGENT_SKILLS_DIR": str(self.skills),
            "PATH": os.environ.get("PATH", ""),
        }

    def plan(self):
        envelope, code = plan_cleanup_legacy(
            [self.project], self.vault, skills_root=self.skills, environ=self.environ
        )
        return envelope, code

    def prepare(self):
        envelope, code = self.plan()
        if code:
            raise AssertionError(envelope)
        return Path(envelope["cleanup_legacy"]["plan_path"]), envelope["plan_id"]

    def apply(self, path, confirmation, receipt=None):
        return apply_cleanup_legacy(
            path,
            confirm_cleanup=confirmation,
            cleanup_receipt_path=receipt,
            environ=self.environ,
        )


class CleanupLegacyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.fixture = CleanupLegacyFixture(Path(self.temporary.name))

    def test_gitnexus_skill_retirement_requires_confirmation_and_preserves_original(self):
        """U12: fresh cleanup retires an exact old Skill, not a prefix neighbor."""
        fixture = self.fixture
        skill = fixture.skills / "gitnexus-cli"
        skill.mkdir()
        payload = b"---\nname: gitnexus-cli\n---\nUser-retained old tool instructions\n"
        (skill / "SKILL.md").write_bytes(payload)
        neighbor = fixture.skills / "gitnexus-cli-extra"
        neighbor.mkdir()
        (neighbor / "SKILL.md").write_bytes(payload)
        before = snapshot(skill)
        plan_path, plan_id = fixture.prepare()
        _rejected, code = fixture.apply(plan_path, "not-the-displayed-plan")
        self.assertNotEqual(code, 0)
        self.assertEqual(snapshot(skill), before)
        result, code = fixture.apply(plan_path, plan_id)
        self.assertEqual(code, 0, result)
        self.assertFalse(skill.exists())
        self.assertEqual((neighbor / "SKILL.md").read_bytes(), payload)
        rows = result["cleanup_legacy"]["receipt"]["payload"]["results"]
        retired = next(row for row in rows if row["path"] == str(skill))
        self.assertEqual(retired["status"], "succeeded")
        self.assertEqual(snapshot(Path(retired["backup_ref"]["path"])), before)

    def test_plan_preserves_targets_and_lists_actual_contents(self):
        fixture = self.fixture
        original = snapshot(fixture.project)
        envelope, code = fixture.plan()
        self.assertEqual(code, 0)
        self.assertEqual(envelope["status"], "planned")
        self.assertEqual(snapshot(fixture.project), original)
        payload = envelope["cleanup_legacy"]["plan"]["payload"]
        self.assertEqual(
            [p["kind"] for p in payload["projects"][0]["candidates"]],
            ["directory-remove", "marker-blocks"],
        )
        self.assertEqual(
            [p["host"] for p in payload["shared"]["mcp"]["candidates"]],
            ["codex", "claude", "kimi", "omp"],
        )

    def test_project_local_codex_home_without_config_does_not_block_cleanup(self):
        fixture = self.fixture
        codex_home = fixture.project / ".codex"
        fixture.environ["CODEX_HOME"] = str(codex_home)
        plan, plan_id = fixture.prepare()
        applied, code = fixture.apply(plan, plan_id)
        self.assertEqual((code, applied["status"]), (0, "cleaned"), applied)
        self.assertFalse(codex_home.exists())
        self.assertEqual((fixture.project / "AGENTS.md").read_bytes(), AGENTS_CLEAN)
        from onboard_contracts import ContractError

        codex_home.mkdir()
        config = codex_home / "config.toml"
        config.write_bytes(b"# existing project-local configuration\n")
        with self.assertRaisesRegex(ContractError, "config overlaps a project"):
            fixture.plan()
        self.assertEqual(config.read_bytes(), b"# existing project-local configuration\n")

    def test_retirement_only_list_rejects_a_legacy_kind(self):
        from onboard_contracts import ContractError
        from sbtd_cleanup_legacy import _all_candidates

        envelope, code = self.fixture.plan()
        self.assertEqual(code, 0)
        payload = envelope["cleanup_legacy"]["plan"]["payload"]
        # Exercise the structural boundary without supplying a mutation target.
        payload["graftRetirement"]["candidates"] = [{"kind": "directory-remove"}]
        for purpose in ("cleanup-legacy", "retirement-reset"):
            with self.subTest(purpose=purpose), self.assertRaisesRegex(
                ContractError, "retirement candidate contains another cleanup kind",
            ):
                payload["purpose"] = purpose
                _all_candidates(_seal_document(payload, "plan_id"))

    def test_omp_directory_aliases_do_not_duplicate_cleanup_targets(self):
        fixture = self.fixture
        if not (fixture.home / ".OMP").is_dir():
            self.skipTest("requires case-insensitive directory aliases")
        fixture.environ["PI_CONFIG_DIR"] = ".OMP"
        envelope, code = fixture.plan()
        self.assertEqual((code, envelope["status"]), (0, "planned"))
        candidates = envelope["cleanup_legacy"]["plan"]["payload"]["shared"]["mcp"][
            "candidates"
        ]
        self.assertEqual(
            [row["path"] for row in candidates if row["host"] == "omp"],
            [str(fixture.home / ".omp/agent/mcp.json")],
        )
        cleaned, code = fixture.apply(
            Path(envelope["cleanup_legacy"]["plan_path"]), envelope["plan_id"]
        )
        self.assertEqual((code, cleaned["status"]), (0, "cleaned"))
        self.assertEqual(
            json.loads((fixture.home / ".omp/agent/mcp.json").read_bytes()),
            {
                "mcpServers": {
                    "browser": {"command": "npx", "args": ["@playwright/mcp"]}
                }
            },
        )

    def test_distinct_hardlinked_config_entries_are_both_cleaned(self):
        fixture = self.fixture
        claude = fixture.home / ".claude.json"
        omp = fixture.home / ".omp/agent/mcp.json"
        omp.unlink()
        omp.hardlink_to(claude)
        unselected = fixture.base / "other-configuration.json"
        unselected.hardlink_to(claude)
        original = unselected.read_bytes()
        planned, code = fixture.plan()
        self.assertEqual((code, planned["status"]), (0, "planned"), planned)
        self.assertIn("Graft retirement inspection is blocked", planned["reason"])
        envelope, code = fixture.apply(Path(planned["cleanup_legacy"]["plan_path"]), planned["plan_id"])
        self.assertEqual((code, envelope["status"]), (0, "cleaned"))
        self.assertEqual(envelope["graftRetirement"], {"status": "blocked", "scope": "legacy-only"})
        expected = {"mcpServers": {"playwright": {"command": "npx"}}}
        self.assertEqual(json.loads(claude.read_bytes()), expected)
        self.assertEqual(json.loads(omp.read_bytes()), expected)
        self.assertEqual(unselected.read_bytes(), original)

    def test_uninspected_hardlinked_config_cannot_retire_a_renamed_key(self):
        fixture = self.fixture
        claude = fixture.home / ".claude.json"
        omp = fixture.home / ".omp/agent/mcp.json"
        raw = canonical_json_bytes({"mcpServers": {"renamed": {"command": "gitnexus"}}})
        claude.write_bytes(raw)
        omp.unlink()
        omp.hardlink_to(claude)
        planned, code = fixture.plan()
        self.assertEqual((code, planned["status"]), (2, "blocked"), planned)
        refused, code = fixture.apply(Path(planned["cleanup_legacy"]["plan_path"]), planned["plan_id"])
        self.assertEqual((code, refused["status"]), (2, "blocked"), refused)
        self.assertEqual(claude.read_bytes(), raw)
        self.assertEqual(omp.read_bytes(), raw)
        self.assertTrue((fixture.project / ".gitnexus").is_dir())

    @unittest.skipUnless(os.name == "posix", "legacy-only cleanup policy")
    def test_disjoint_legacy_cleanup_discloses_blocked_retirement(self):
        fixture = self.fixture
        hooks = fixture.home / ".codex/hooks.json"
        hooks.write_bytes(b"{")
        planned, code = fixture.plan()
        self.assertEqual((code, planned["status"]), (0, "planned"), planned)
        self.assertIn("Graft retirement inspection is blocked", planned["reason"])
        applied, code = fixture.apply(Path(planned["cleanup_legacy"]["plan_path"]), planned["plan_id"])
        self.assertEqual((code, applied["status"]), (0, "cleaned"), applied)
        self.assertEqual(applied["graftRetirement"], {"status": "blocked", "scope": "legacy-only"})
        self.assertEqual(hooks.read_bytes(), b"{")
        self.assertFalse((fixture.project / ".gitnexus").exists())
        blocked, code = fixture.plan()
        self.assertEqual((code, blocked["status"]), (2, "blocked"), blocked)

    def test_confirmation_is_required_before_every_target_write(self):
        fixture = self.fixture
        path, _plan_id = fixture.prepare()
        for confirmation in (None, "0" * 64):
            with self.subTest(confirmation=confirmation):
                before = snapshot(fixture.project)
                envelope, code = fixture.apply(path, confirmation)
                self.assertEqual((code, envelope["status"]), (2, "blocked"))
                self.assertEqual(snapshot(fixture.project), before)

    def test_confirmed_cleanup_preserves_neighbors_and_backups(self):
        fixture = self.fixture
        path, plan_id = fixture.prepare()
        envelope, code = fixture.apply(path, plan_id)
        self.assertEqual((code, envelope["status"]), (0, "cleaned"), envelope)
        self.assertFalse((fixture.project / ".gitnexus").exists())
        self.assertFalse((fixture.skills / "trellis-workflow").exists())
        self.assertEqual((fixture.project / "AGENTS.md").read_bytes(), AGENTS_CLEAN)
        self.assertEqual(
            json.loads((fixture.home / ".claude.json").read_text()),
            {"mcpServers": {"playwright": {"command": "npx"}}},
        )
        self.assertEqual(
            (fixture.home / ".codex/config.toml").read_text().strip(),
            '[mcp_servers.context7]\ncommand = "npx"',
        )
        for relative in (".kimi-code/mcp.json", ".omp/agent/mcp.json"):
            self.assertEqual(
                json.loads((fixture.home / relative).read_text()),
                {
                    "mcpServers": {
                        "browser": {"command": "npx", "args": ["@playwright/mcp"]}
                    }
                },
            )
        for row in envelope["cleanup_legacy"]["receipt"]["payload"]["results"]:
            self.assertEqual(row["status"], "succeeded")
            self.assertEqual(snapshot(Path(row["backup_ref"]["path"])), row["before"])
        rerun, code = fixture.apply(
            path, plan_id, Path(envelope["cleanup_legacy"]["receipt_path"])
        )
        self.assertEqual((code, rerun["status"]), (0, "cleaned"), rerun)
        self.assertEqual((fixture.project / "AGENTS.md").read_bytes(), AGENTS_CLEAN)

    def test_rehashed_plan_cannot_delete_unselected_directory(self):
        fixture = self.fixture
        path, _plan_id = fixture.prepare()
        unrelated = fixture.base / "unrelated"
        unrelated.mkdir()
        (unrelated / "keep.txt").write_text("user data")
        document = json.loads(path.read_text())
        candidate = document["payload"]["projects"][0]["candidates"][0]
        candidate["path"] = str(unrelated)
        candidate["before"] = snapshot(unrelated)
        document["plan_id"] = hashlib.sha256(
            canonical_json_bytes(document["payload"])
        ).hexdigest()
        path.write_text(json.dumps(document))
        envelope, code = fixture.apply(path, document["plan_id"])
        self.assertEqual((code, envelope["status"]), (2, "blocked"))
        self.assertEqual((unrelated / "keep.txt").read_text(), "user data")
        self.assertTrue((fixture.project / ".gitnexus").is_dir())

    def test_drift_after_plan_blocks_all_writes(self):
        fixture = self.fixture
        path, plan_id = fixture.prepare()
        (fixture.project / ".gitnexus/index/late.bin").write_bytes(b"drift")
        envelope, code = fixture.apply(path, plan_id)
        self.assertEqual((code, envelope["status"]), (2, "blocked"))
        self.assertEqual((fixture.project / "AGENTS.md").read_bytes(), AGENTS_RAW)

    def test_unavailable_vendor_is_blocked_not_an_executable_candidate(self):
        fixture = self.fixture
        (fixture.project / ".trellis").mkdir()
        fixture.environ["PATH"] = ""
        envelope, code = fixture.plan()
        self.assertEqual((code, envelope["status"]), (2, "blocked"))
        project = envelope["cleanup_legacy"]["plan"]["payload"]["projects"][0]
        self.assertFalse(
            any(item["kind"] == "trellis-uninstall" for item in project["candidates"])
        )
        self.assertEqual(project["blocked"][0]["kind"], "trellis-uninstall")
        self.assertTrue((fixture.project / ".trellis").is_dir())

    def test_malformed_global_config_is_not_reported_as_clean(self):
        fixture = self.fixture
        (fixture.home / ".claude.json").write_text("invalid")
        envelope, code = fixture.plan()
        self.assertEqual((code, envelope["status"]), (2, "blocked"))
        self.assertEqual(
            envelope["cleanup_legacy"]["plan"]["payload"]["shared"]["mcp"]["blocked"][
                0
            ]["host"],
            "claude",
        )

    def test_backup_directory_inside_project_is_rejected(self):
        from onboard_contracts import ContractError

        fixture = self.fixture
        vault = fixture.project / "vault"
        vault.mkdir(mode=0o700)
        with self.assertRaises(ContractError):
            plan_cleanup_legacy(
                [fixture.project],
                vault,
                skills_root=fixture.skills,
                environ=fixture.environ,
            )
        self.assertTrue((fixture.project / ".gitnexus").is_dir())

    def test_nested_cleanup_candidates_are_rejected_before_plan_writes(self):
        from onboard_contracts import ContractError

        for direction in ("skill-under-index", "index-under-skill"):
            with (
                self.subTest(direction=direction),
                tempfile.TemporaryDirectory() as temp,
            ):
                fixture = CleanupLegacyFixture(Path(temp))
                skill = fixture.skills / "trellis-workflow"
                if direction == "skill-under-index":
                    fixture.skills = fixture.project / ".gitnexus"
                    shutil.move(str(skill), str(fixture.skills / skill.name))
                    fixture.environ["AGENT_SKILLS_DIR"] = str(fixture.skills)
                else:
                    fixture.project = skill
                    (skill / ".gitnexus").mkdir()
                before = snapshot(fixture.base)
                with self.assertRaises(ContractError) as raised:
                    fixture.plan()
                self.assertEqual(raised.exception.code, "scope-conflict")
                self.assertEqual(snapshot(fixture.base), before)

    def test_old_overlapping_plan_is_rejected_before_any_deletion(self):
        fixture = self.fixture
        path, _plan_id = fixture.prepare()
        document = json.loads(path.read_text())
        skill = fixture.skills / "trellis-workflow"
        fixture.skills = fixture.project / ".gitnexus"
        nested = fixture.skills / skill.name
        shutil.move(str(skill), str(nested))
        fixture.environ["AGENT_SKILLS_DIR"] = str(fixture.skills)
        payload = document["payload"]
        payload["skills_root"] = str(fixture.skills)
        payload["shared"]["skills"]["candidates"][0]["path"] = str(nested)
        for candidate in payload["projects"][0]["candidates"]:
            if candidate["kind"] == "directory-remove":
                candidate["before"] = snapshot(fixture.skills)
        document["plan_id"] = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
        path.write_text(json.dumps(document))
        before = snapshot(fixture.base)

        envelope, code = fixture.apply(path, document["plan_id"])

        self.assertEqual((code, envelope["status"]), (2, "blocked"))
        self.assertEqual(snapshot(fixture.base), before)

    def test_plan_symlink_is_rejected(self):
        fixture = self.fixture
        path, plan_id = fixture.prepare()
        link = fixture.vault / "link.json"
        link.symlink_to(path)
        envelope, code = fixture.apply(link, plan_id)
        self.assertEqual((code, envelope["status"]), (2, "blocked"))

    def test_write_failure_preserves_backup_and_records_partial_results(self):
        fixture = self.fixture
        path, plan_id = fixture.prepare()
        with mock.patch(
            "sbtd_cleanup_legacy.write_file", side_effect=OSError("write denied")
        ):
            envelope, code = fixture.apply(path, plan_id)
        self.assertEqual((code, envelope["status"]), (3, "failed"))
        rows = envelope["cleanup_legacy"]["receipt"]["payload"]["results"]
        self.assertEqual([r["status"] for r in rows], ["succeeded", "failed"])
        self.assertEqual((fixture.project / "AGENTS.md").read_bytes(), AGENTS_RAW)
        self.assertTrue((fixture.skills / "trellis-workflow").exists())

    @unittest.skipUnless(os.name == "posix", "POSIX mode fixture")
    def test_retry_rejects_mode_drift_in_completed_backup_before_next_write(self):
        fixture = self.fixture
        plan, plan_id = fixture.prepare()
        with mock.patch("sbtd_cleanup_legacy.write_file", side_effect=OSError("write denied")):
            first, code = fixture.apply(plan, plan_id)
        self.assertEqual((code, first["status"]), (3, "failed"), first)
        receipt = first["cleanup_legacy"]
        row = receipt["receipt"]["payload"]["results"][0]
        self.assertEqual((row["kind"], row["status"]), ("directory-remove", "succeeded"))
        backup = Path(row["backup_ref"]["path"])
        backup.chmod(int(row["mode_before"], 8) ^ 0o020)
        refused, code = fixture.apply(plan, plan_id, Path(receipt["receipt_path"]))
        self.assertEqual((code, refused["status"]), (2, "blocked"), refused)
        self.assertEqual((fixture.project / "AGENTS.md").read_bytes(), AGENTS_RAW)
        self.assertTrue((fixture.skills / "trellis-workflow").exists())

    def test_real_cli_plan_and_refusal_return_one_json_document(self):
        fixture = self.fixture
        env = dict(os.environ, **fixture.environ, PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "onboard.py"),
                "cleanup-legacy",
                "--phase",
                "plan",
                "--projects-root",
                str(fixture.project),
                "--backup-root",
                str(fixture.vault),
                "--json",
            ],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads(result.stdout)
        rejected = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "onboard.py"),
                "cleanup-legacy",
                "--phase",
                "apply",
                "--plan",
                plan["cleanup_legacy"]["plan_path"],
                "--json",
            ],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(rejected.returncode, 2, rejected.stderr)
        self.assertEqual(json.loads(rejected.stdout)["status"], "blocked")
        self.assertEqual((fixture.project / "AGENTS.md").read_bytes(), AGENTS_RAW)

    def test_cli_explicit_skills_root_overrides_environment_and_stays_sealed(self):
        fixture = self.fixture
        custom = fixture.base / "custom-skills"
        selected = custom / "trellis-workflow"
        selected.mkdir(parents=True)
        original = b"---\nname: trellis-workflow\n---\ncustom installation\n"
        (selected / "SKILL.md").write_bytes(original)
        unselected = fixture.skills / "trellis-workflow"
        unselected_before = snapshot(unselected)
        env = dict(fixture.environ, PYTHONDONTWRITEBYTECODE="1")
        command = [sys.executable, "-B", str(SCRIPTS / "onboard.py"), "cleanup-legacy"]
        planned = subprocess.run(
            command
            + [
                "--phase",
                "plan",
                "--projects-root",
                str(fixture.project),
                "--backup-root",
                str(fixture.vault),
                "--global-skills-dir",
                str(custom),
                "--json",
            ],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(planned.returncode, 0, planned.stderr)
        plan = json.loads(planned.stdout)
        self.assertEqual(
            plan["cleanup_legacy"]["plan"]["payload"]["skills_root"], str(custom)
        )
        self.assertEqual((selected / "SKILL.md").read_bytes(), original)

        applied = subprocess.run(
            command
            + [
                "--phase",
                "apply",
                "--plan",
                plan["cleanup_legacy"]["plan_path"],
                "--confirm-cleanup",
                plan["plan_id"],
                "--json",
            ],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(applied.returncode, 0, applied.stderr)
        result = json.loads(applied.stdout)
        self.assertEqual(result["status"], "cleaned")
        self.assertFalse(selected.exists())
        self.assertEqual(snapshot(unselected), unselected_before)
        row = next(
            row
            for row in result["cleanup_legacy"]["receipt"]["payload"]["results"]
            if row["kind"] == "skill-directory"
        )
        self.assertEqual(
            (Path(row["backup_ref"]["path"]) / "SKILL.md").read_bytes(), original
        )

    def _vendor_failed_run(self):
        """Isolated first apply: vendor success, then unchanged .gitnexus failure."""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        fixture = CleanupLegacyFixture(Path(temporary.name))
        (fixture.project / ".trellis").mkdir()
        (fixture.project / ".trellis/state.json").write_text("{}")
        with _fake_vendor():
            plan_path, plan_id = fixture.prepare()
            with mock.patch(
                "sbtd_cleanup_legacy.remove_reference",
                side_effect=_refuse_gitnexus_removal,
            ):
                envelope, code = fixture.apply(plan_path, plan_id)
        self.assertEqual((code, envelope["status"]), (3, "failed"), envelope)
        return (
            fixture,
            plan_path,
            plan_id,
            Path(envelope["cleanup_legacy"]["receipt_path"]),
        )

    @unittest.skipUnless(os.name == "posix", "POSIX mode fixture")
    def test_rollback_restores_all_vendor_effects_in_reverse_once(self):
        import sbtd_cleanup_legacy as cleanup

        fixture = self.fixture
        agents = fixture.project / "AGENTS.md"
        agents.chmod(0o640)
        trellis = fixture.project / ".trellis"
        trellis.mkdir(mode=0o750)
        (trellis / "state.json").write_bytes(b"{}")
        pruned = fixture.project / "managed"
        pruned.mkdir(mode=0o750)
        nested = pruned / "obsolete.json"
        nested.write_bytes(b'{"old":true}')
        nested.chmod(0o640)
        scrubbed = fixture.project / "vendor-rules.md"
        scrubbed.write_bytes(AGENTS_RAW)
        scrubbed.chmod(0o640)

        def prepare(root, *, environ=None):
            prepared = _fake_vendor_prepare(root, environ=environ)
            payload = prepared["payload"]
            agent, trellis_resource = payload["resources"]
            absent = {"type": "absent", "checksum": None}
            agent.update(kind="vendor-delete", expected_after=absent)

            def resource(index, kind, path, after):
                return {"resource_id": f"trellis-{index:03d}", "kind": kind,
                        "path": str(path), "relative": path.relative_to(root).as_posix(),
                        "before": snapshot(path), "expected_after": after}

            payload["resources"] = [
                agent,
                resource(2, "vendor-delete", nested, absent),
                resource(3, "vendor-scrub", scrubbed, {
                    "type": "file", "checksum": hashlib.sha256(_vendor_scrub(AGENTS_RAW)).hexdigest(),
                }),
                trellis_resource,
                resource(4, "vendor-prune-dir", pruned, absent),
            ]
            return _seal_document(payload, "prepared_id") | {"kind": prepared["kind"]}

        def execute(*args, **kwargs):
            outcome = _fake_vendor_execute(*args, **kwargs)
            scrubbed.chmod(0o600)
            return outcome

        before = {path: (snapshot(path), path.stat().st_mode) for path in (agents, trellis, pruned, nested, scrubbed)}
        with _fake_vendor(prepare=prepare, execute=execute):
            plan, plan_id = fixture.prepare()
            applied, code = fixture.apply(plan, plan_id)
        self.assertEqual((code, applied["status"]), (0, "cleaned"), applied)
        self.assertEqual(agents.read_bytes(), AGENTS_CLEAN)
        self.assertEqual(scrubbed.read_bytes(), _vendor_scrub(AGENTS_RAW))
        self.assertFalse(pruned.exists())
        self.assertFalse(trellis.exists())

        receipt = Path(applied["cleanup_legacy"]["receipt_path"])
        rows = applied["cleanup_legacy"]["receipt"]["payload"]["results"]
        marker = next(row for row in rows if row["kind"] == "marker-blocks")
        self.assertEqual(marker["mode_before"], "0640")
        vendor = next(row for row in rows if row["kind"] == "trellis-uninstall")
        original = next(row["backup_ref"] for row in vendor["vendor"]["results"] if row["path"] == str(scrubbed))
        backup = Path(original["path"])
        self.assertEqual((backup.read_bytes(), backup.stat().st_mode & 0o777), (AGENTS_RAW, 0o640))

        def rollback(receipt_path):
            return cleanup.rollback_cleanup_legacy(
                plan, confirm_cleanup=plan_id, cleanup_receipt_path=receipt_path, environ=fixture.environ,
            )

        old_receipt = fixture.vault / "legacy-without-vendor-modes.json"
        old_payload = json.loads(receipt.read_bytes())["payload"]
        next(row for row in old_payload["results"] if row["kind"] == "trellis-uninstall").pop("vendor_modes_after")
        _write_sealed(old_receipt, old_payload, "receipt_id")
        retired_project = snapshot(fixture.project)
        refused, code = rollback(old_receipt)
        self.assertEqual((code, refused["status"]), (2, "blocked"))
        self.assertIn("bound per-target mode evidence", refused["reason"])
        self.assertEqual(snapshot(fixture.project), retired_project)

        backup.chmod(0o600)
        refused, code = rollback(receipt)
        self.assertEqual((code, refused["status"]), (2, "blocked"))
        self.assertEqual(snapshot(fixture.project), retired_project)
        self.assertFalse((fixture.skills / "trellis-workflow").exists())
        backup.chmod(0o640)
        with mock.patch.object(cleanup, "_restore_retired", wraps=cleanup._restore_retired) as restore:
            restored, code = rollback(receipt)
        self.assertEqual((code, restored["status"]), (0, "rolled-back"), restored)
        order = [call.args[2] for call in restore.call_args_list if call.args[2].is_relative_to(fixture.project)]
        self.assertEqual(order, [agents, fixture.project / ".gitnexus", pruned, trellis, scrubbed])
        self.assertEqual({path: (snapshot(path), path.stat().st_mode) for path in before}, before)
        self.assertEqual(backup.read_bytes(), AGENTS_RAW)

    def test_rollback_restores_vendor_effect_on_pending_marker_target(self):
        from sbtd_cleanup_legacy import rollback_cleanup_legacy

        fixture, plan, plan_id, receipt = self._vendor_failed_run()
        restored, code = rollback_cleanup_legacy(
            plan, confirm_cleanup=plan_id, cleanup_receipt_path=receipt, environ=fixture.environ,
        )
        self.assertEqual((code, restored["status"]), (0, "rolled-back"), restored)
        self.assertEqual((fixture.project / "AGENTS.md").read_bytes(), AGENTS_RAW)
        self.assertTrue((fixture.project / ".trellis" / "state.json").is_file())
        self.assertTrue((fixture.project / ".gitnexus").is_dir())

    def test_vendor_execution_requires_complete_sealed_modes(self):
        fixture = self.fixture
        (fixture.project / ".trellis").mkdir()
        execute = mock.Mock()
        with _fake_vendor(execute=execute):
            plan, _ = fixture.prepare()
            payload = json.loads(plan.read_bytes())["payload"]
            vendor = payload["projects"][0]["candidates"][0]
            vendor["vendor_modes_before"].pop(str(fixture.project / "AGENTS.md"))
            _write_sealed(plan, payload, "plan_id")
            plan_id = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
            before = snapshot(fixture.project)
            vault_files = set(fixture.vault.iterdir())
            refused, code = fixture.apply(plan, plan_id)
        self.assertEqual((code, refused["status"]), (2, "blocked"), refused)
        self.assertIn("bound per-target mode evidence", refused["reason"])
        self.assertEqual(snapshot(fixture.project), before)
        self.assertEqual(set(fixture.vault.iterdir()), vault_files)
        execute.assert_not_called()

    def test_nested_vendor_overlap_without_bound_target_blocks_before_apply(self):
        fixture = self.fixture
        trellis = fixture.project / ".trellis"
        trellis.mkdir()
        nested = fixture.project / ".gitnexus" / "index" / "db.bin"

        def prepare(root, *, environ=None):
            prepared = _fake_vendor_prepare(root, environ=environ)
            payload = prepared["payload"]
            payload["resources"].insert(0, {
                "resource_id": "trellis-002", "kind": "vendor-delete",
                "path": str(nested), "relative": nested.relative_to(root).as_posix(),
                "before": snapshot(nested), "expected_after": {"type": "absent", "checksum": None},
            })
            return _seal_document(payload, "prepared_id") | {"kind": prepared["kind"]}

        execute = mock.Mock()
        before = snapshot(fixture.project)
        with _fake_vendor(prepare=prepare, execute=execute):
            plan, code = fixture.plan()
            self.assertEqual((code, plan["status"]), (2, "blocked"), plan)
            self.assertIn("without a bound transition", plan["reason"])
            path = Path(plan["cleanup_legacy"]["plan_path"])
            blocked, code = fixture.apply(path, plan["plan_id"])
        self.assertEqual((code, blocked["status"]), (2, "blocked"), blocked)
        self.assertEqual(snapshot(fixture.project), before)
        execute.assert_not_called()

    def test_legacy_vendor_receipt_retries_without_claiming_unknown_modes(self):
        from sbtd_cleanup_legacy import rollback_cleanup_legacy

        fixture, plan, _plan_id, receipt = self._vendor_failed_run()
        payload = json.loads(plan.read_bytes())["payload"]
        payload.pop("graftRetirement")
        payload["projects"][0]["candidates"][0].pop("vendor_modes_before")
        _write_sealed(plan, payload, "plan_id")
        plan_id = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
        previous = json.loads(receipt.read_bytes())["payload"]
        previous["plan_id"] = plan_id
        for row in previous["results"]:
            for key in ("vendor_modes_after", "mode_before", "mode_after"):
                row.pop(key, None)
        _write_sealed(receipt, previous, "receipt_id")

        refused, code = rollback_cleanup_legacy(
            plan, confirm_cleanup=plan_id, cleanup_receipt_path=receipt, environ=fixture.environ,
        )
        self.assertEqual((code, refused["status"]), (2, "blocked"), refused)
        self.assertEqual((fixture.project / "AGENTS.md").read_bytes(), _vendor_scrub(AGENTS_RAW))
        retry, code = fixture.apply(plan, plan_id, receipt)
        self.assertEqual((code, retry["status"]), (0, "cleaned"), retry)
        self.assertEqual((fixture.project / "AGENTS.md").read_bytes(), AGENTS_CLEAN)
        self.assertFalse((fixture.project / ".trellis").exists())
        self.assertFalse((fixture.project / ".gitnexus").exists())
        row = next(row for row in retry["cleanup_legacy"]["receipt"]["payload"]["results"]
                   if row["kind"] == "marker-blocks")
        self.assertIsNone(row["mode_before"])

    def test_retry_uses_successful_vendor_after_states_for_remaining_candidates(self):
        fixture = self.fixture
        agents = fixture.project / "AGENTS.md"
        (fixture.project / ".trellis").mkdir()
        (fixture.project / ".trellis/state.json").write_text("{}")
        vendor_after = _vendor_scrub(AGENTS_RAW) + b"<!-- vendor-extra -->\n"

        def prepare_with_extra(root, *, environ=None):
            prepared = _fake_vendor_prepare(root, environ=environ)
            prepared["payload"]["resources"][0]["expected_after"] = {
                "type": "file",
                "checksum": hashlib.sha256(vendor_after).hexdigest(),
            }
            prepared["prepared_id"] = hashlib.sha256(
                canonical_json_bytes(prepared["payload"])
            ).hexdigest()
            return prepared

        def execute_with_extra(root, prepared, backup_root, *, environ=None, before_execute=None):
            outcome = _fake_vendor_execute(root, prepared, backup_root, environ=environ, before_execute=before_execute)
            agents.write_bytes(vendor_after)
            outcome["results"][0]["after"] = snapshot(agents)
            outcome["results"][0]["status"] = "scrubbed"
            return outcome

        with (
            mock.patch(
                "sbtd_trellis_uninstall.prepare_trellis_uninstall",
                side_effect=prepare_with_extra,
            ),
            mock.patch(
                "sbtd_trellis_uninstall.execute_trellis_uninstall",
                side_effect=execute_with_extra,
            ),
        ):
            plan_path, plan_id = fixture.prepare()
            with mock.patch(
                "sbtd_cleanup_legacy.remove_reference",
                side_effect=_refuse_gitnexus_removal,
            ):
                first, code = fixture.apply(plan_path, plan_id)
        self.assertEqual((code, first["status"]), (3, "failed"), first)
        self.assertEqual(agents.read_bytes(), vendor_after)
        receipt_path = Path(first["cleanup_legacy"]["receipt_path"])
        retry, code = fixture.apply(plan_path, plan_id, receipt_path)
        self.assertEqual((code, retry["status"]), (0, "cleaned"), retry)
        self.assertEqual(agents.read_bytes(), AGENTS_CLEAN)
        marker_row = next(
            row
            for row in retry["cleanup_legacy"]["receipt"]["payload"]["results"]
            if row["kind"] == "marker-blocks"
        )
        self.assertEqual(
            Path(marker_row["backup_ref"]["path"]).read_bytes(), AGENTS_RAW
        )

    def test_vendor_scrub_then_unchanged_failure_retries_from_original_backup(self):
        fixture, plan_path, plan_id, receipt = self._vendor_failed_run()
        self.assertFalse((fixture.project / ".trellis").exists())
        self.assertEqual(
            (fixture.project / "AGENTS.md").read_bytes(), _vendor_scrub(AGENTS_RAW)
        )
        retry, code = fixture.apply(plan_path, plan_id, receipt)
        self.assertEqual((code, retry["status"]), (0, "cleaned"), retry)
        self.assertFalse((fixture.project / ".gitnexus").exists())
        # Both legacy blocks removed; graft fence and own rules byte-exact.
        self.assertEqual((fixture.project / "AGENTS.md").read_bytes(), AGENTS_CLEAN)
        rows = retry["cleanup_legacy"]["receipt"]["payload"]["results"]
        self.assertTrue(all(row["status"] == "succeeded" for row in rows))
        agents_row = next(row for row in rows if row["kind"] == "marker-blocks")
        self.assertEqual(
            agents_row["before"],
            {"type": "file", "checksum": hashlib.sha256(AGENTS_RAW).hexdigest()},
        )
        # The pending edit rendered from the reused immutable original backup.
        self.assertEqual(
            Path(agents_row["backup_ref"]["path"]).read_bytes(), AGENTS_RAW
        )
        again, code = fixture.apply(
            plan_path,
            plan_id,
            Path(retry["cleanup_legacy"]["receipt_path"]),
        )
        self.assertEqual((code, again["status"]), (0, "cleaned"), again)
        self.assertEqual((fixture.project / "AGENTS.md").read_bytes(), AGENTS_CLEAN)

    def test_vendor_leaving_only_legacy_block_writes_rendered_file_on_retry(self):
        fixture = self.fixture
        (fixture.project / "AGENTS.md").write_bytes(AGENTS_LEGACY_ONLY)
        (fixture.project / ".trellis").mkdir()
        (fixture.project / ".trellis/state.json").write_text("{}")
        with _fake_vendor():
            plan_path, plan_id = fixture.prepare()
            with mock.patch(
                "sbtd_cleanup_legacy.remove_reference",
                side_effect=_refuse_gitnexus_removal,
            ):
                envelope, code = fixture.apply(plan_path, plan_id)
            self.assertEqual((code, envelope["status"]), (3, "failed"), envelope)
            # The vendor left only the legacy gitnexus block behind.
            self.assertEqual(
                (fixture.project / "AGENTS.md").read_bytes(), AGENTS_ONLY_SCRUBBED
            )
            retry, code = fixture.apply(
                plan_path, plan_id, Path(envelope["cleanup_legacy"]["receipt_path"])
            )
            self.assertEqual((code, retry["status"]), (0, "cleaned"), retry)
        # Both blocks were the whole file: the planned outcome keeps the
        # original file with exactly the rendered block-free bytes (the one
        # newline that separated the two legacy blocks).
        self.assertEqual((fixture.project / "AGENTS.md").read_bytes(), b"\n")
        rows = retry["cleanup_legacy"]["receipt"]["payload"]["results"]
        agents_row = next(row for row in rows if row["kind"] == "marker-blocks")
        self.assertEqual(agents_row["status"], "succeeded")
        self.assertEqual(
            agents_row["after"],
            {"type": "file", "checksum": hashlib.sha256(b"\n").hexdigest()},
        )

    def test_retry_rejects_tampered_vendor_transition(self):
        def vendor_outcome(payload):
            row = next(
                r for r in payload["results"] if r["kind"] == "trellis-uninstall"
            )
            return row["vendor"]

        def vendor_results(payload):
            return vendor_outcome(payload)["results"]

        def scrub_result(payload):
            return next(
                r for r in vendor_results(payload) if r["kind"] == "vendor-scrub"
            )

        cases = {
            "after": lambda fixture, payload: scrub_result(payload).update(
                after={"type": "file", "checksum": "0" * 64}
            ),
            "backup-state": lambda fixture, payload: scrub_result(payload)[
                "backup_ref"
            ].update(state={"type": "file", "checksum": "0" * 64}),
            "backup-path": lambda fixture, payload: scrub_result(payload)[
                "backup_ref"
            ].update(path=str(fixture.project / "AGENTS.md")),
            "unlisted-path": lambda fixture, payload: vendor_results(payload).append(
                dict(scrub_result(payload), path=str(fixture.project / "OTHER.md"))
            ),
            "duplicate-path": lambda fixture, payload: vendor_results(payload).append(
                dict(scrub_result(payload))
            ),
            "exit": lambda fixture, payload: vendor_outcome(payload).update(exit=1),
            "exit-bool": lambda fixture, payload: vendor_outcome(payload).update(
                exit=False
            ),
            "resource-id": lambda fixture, payload: scrub_result(payload).update(
                resource_id="trellis-999"
            ),
            "kind": lambda fixture, payload: scrub_result(payload).update(
                kind="vendor-delete"
            ),
            "relative": lambda fixture, payload: scrub_result(payload).update(
                relative="OTHER.md"
            ),
            "status": lambda fixture, payload: scrub_result(payload).update(
                status="removed"
            ),
            "null-first-result": lambda fixture, payload: vendor_results(
                payload
            ).__setitem__(0, None),
            "failed-vendor-not-mapping": lambda fixture, payload: payload["results"][
                -1
            ].update(vendor=[]),
            "failed-vendor-null-results": lambda fixture, payload: payload["results"][
                -1
            ].update(vendor={"status": "failed", "results": None}),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                fixture, plan_path, plan_id, receipt = self._vendor_failed_run()
                document = json.loads(receipt.read_text())
                mutate(fixture, document["payload"])
                document["receipt_id"] = hashlib.sha256(
                    canonical_json_bytes(document["payload"])
                ).hexdigest()
                receipt.write_text(json.dumps(document))
                envelope, code = fixture.apply(plan_path, plan_id, receipt)
                self.assertEqual((code, envelope["status"]), (2, "blocked"), envelope)
                self.assertEqual(
                    (fixture.project / "AGENTS.md").read_bytes(),
                    _vendor_scrub(AGENTS_RAW),
                )
                self.assertTrue((fixture.project / ".gitnexus").is_dir())

    def test_retry_rejects_null_prepared_resource(self):
        fixture, plan_path, _plan_id, receipt = self._vendor_failed_run()
        plan = json.loads(plan_path.read_text())
        candidate = plan["payload"]["projects"][0]["candidates"][0]
        candidate["trellis"]["payload"]["resources"].append(None)
        candidate["trellis"]["prepared_id"] = hashlib.sha256(
            canonical_json_bytes(candidate["trellis"]["payload"])
        ).hexdigest()
        plan["plan_id"] = hashlib.sha256(
            canonical_json_bytes(plan["payload"])
        ).hexdigest()
        plan_path.write_text(json.dumps(plan))
        document = json.loads(receipt.read_text())
        document["payload"]["plan_id"] = plan["plan_id"]
        row = next(
            r
            for r in document["payload"]["results"]
            if r["kind"] == "trellis-uninstall"
        )
        row["vendor"]["prepared_id"] = candidate["trellis"]["prepared_id"]
        document["receipt_id"] = hashlib.sha256(
            canonical_json_bytes(document["payload"])
        ).hexdigest()
        receipt.write_text(json.dumps(document))
        envelope, code = fixture.apply(plan_path, plan["plan_id"], receipt)
        self.assertEqual((code, envelope["status"]), (2, "blocked"), envelope)
        self.assertEqual(
            (fixture.project / "AGENTS.md").read_bytes(), _vendor_scrub(AGENTS_RAW)
        )
        self.assertTrue((fixture.project / ".gitnexus").is_dir())

    def test_retry_rejects_agents_edit_after_vendor_scrub(self):
        fixture, plan_path, plan_id, receipt = self._vendor_failed_run()
        edited = _vendor_scrub(AGENTS_RAW) + b"\nuser note\n"
        (fixture.project / "AGENTS.md").write_bytes(edited)
        envelope, code = fixture.apply(plan_path, plan_id, receipt)
        self.assertEqual((code, envelope["status"]), (2, "blocked"), envelope)
        self.assertEqual((fixture.project / "AGENTS.md").read_bytes(), edited)
        self.assertTrue((fixture.project / ".gitnexus").is_dir())

    def test_partial_vendor_outcome_stays_blocked_on_retry(self):
        fixture = self.fixture
        (fixture.project / ".trellis").mkdir()
        (fixture.project / ".trellis/state.json").write_text("{}")
        partial_execute = lambda *args, **kwargs: _fake_vendor_execute(
            *args, partial=True, **kwargs
        )
        with _fake_vendor(execute=partial_execute):
            plan_path, plan_id = fixture.prepare()
            envelope, code = fixture.apply(plan_path, plan_id)
            self.assertEqual((code, envelope["status"]), (3, "failed"), envelope)
            # The partial vendor scrubbed AGENTS.md but kept .trellis.
            self.assertEqual(
                (fixture.project / "AGENTS.md").read_bytes(), _vendor_scrub(AGENTS_RAW)
            )
            self.assertTrue((fixture.project / ".trellis").is_dir())
            retry, code = fixture.apply(
                plan_path, plan_id, Path(envelope["cleanup_legacy"]["receipt_path"])
            )
        self.assertEqual((code, retry["status"]), (2, "blocked"), retry)
        self.assertEqual(
            (fixture.project / "AGENTS.md").read_bytes(), _vendor_scrub(AGENTS_RAW)
        )
        self.assertTrue((fixture.project / ".trellis").is_dir())
        self.assertTrue((fixture.project / ".gitnexus").is_dir())

    def test_retry_after_second_failure_at_pending_agents_write(self):
        fixture, plan_path, plan_id, receipt = self._vendor_failed_run()
        with mock.patch(
            "sbtd_cleanup_legacy.write_file", side_effect=OSError("write denied")
        ):
            second, code = fixture.apply(plan_path, plan_id, receipt)
        self.assertEqual((code, second["status"]), (3, "failed"), second)
        # .gitnexus completed; AGENTS.md is unchanged at the vendor state, not
        # a partial cleanup that would demand reconciliation.
        self.assertFalse((fixture.project / ".gitnexus").exists())
        self.assertEqual(
            (fixture.project / "AGENTS.md").read_bytes(), _vendor_scrub(AGENTS_RAW)
        )
        third, code = fixture.apply(
            plan_path, plan_id, Path(second["cleanup_legacy"]["receipt_path"])
        )
        self.assertEqual((code, third["status"]), (0, "cleaned"), third)
        self.assertEqual((fixture.project / "AGENTS.md").read_bytes(), AGENTS_CLEAN)


class RetirementPlanTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.fixture = CleanupLegacyFixture(Path(self.temporary.name))

    def _module(self, candidates=()):
        module = mock.Mock()
        module.inspect_retirement.return_value = {"items": []}
        module.merge_reports.return_value = {"items": []}
        module.render_candidates.return_value = {
            "candidates": list(candidates),
            "stop": False,
            "preserved": [],
            "blocked": [],
            "manual": [],
        }
        module.render_candidate_bytes.side_effect = (
            lambda raw, _candidate, **_kwargs: raw.replace(
                b"<!-- graft:start -->\nfence\n<!-- graft:end -->\n", b""
            )
        )
        return module

    def test_evidence_outside_vault_is_rejected_before_inspection(self):
        from onboard_contracts import ContractError
        from sbtd_cleanup_legacy import plan_cleanup_legacy

        fixture = self.fixture
        outside = fixture.base / "evidence.json"
        outside.write_text("{}")
        with self.assertRaises(ContractError):
            plan_cleanup_legacy(
                [fixture.project],
                fixture.vault,
                skills_root=fixture.skills,
                environ=fixture.environ,
                retirement_evidence=str(outside),
            )
        self.assertFalse(any(fixture.vault.iterdir()))

    def test_reset_preview_is_stable_and_confirm_mismatch_writes_nothing(self):
        from onboard_contracts import ContractError
        from sbtd_cleanup_legacy import plan_reset_retirement

        fixture = self.fixture
        selections = {
            "host": None,
            "configs": [],
            "projects": [str(fixture.project)],
            "vault": None,
            "retiring_launchers": [],
        }
        module = self._module()
        with mock.patch("sbtd_cleanup_legacy._retirement", return_value=module):
            first = plan_reset_retirement(selections=selections, report={"items": []})
            second = plan_reset_retirement(selections=selections, report={"items": []})
        self.assertEqual(first["status"], "nothing-to-clean")
        self.assertEqual(first["plan_id"], second["plan_id"])
        self.assertFalse(first["writes"])
        self.assertFalse(any(fixture.vault.iterdir()))
        self.assertEqual(first["plan"]["payload"]["projects"], [])
        self.assertNotIn("created_at", first["plan"]["payload"])
        with mock.patch("sbtd_cleanup_legacy._retirement", return_value=module):
            with self.assertRaises(ContractError):
                plan_reset_retirement(
                    selections=selections,
                    vault=fixture.vault,
                    report={"items": []},
                    confirm="0" * 64,
                )
        self.assertFalse(any(fixture.vault.iterdir()))

    def test_rollback_restores_every_cleaned_target_and_refuses_mode_drift(self):
        from sbtd_cleanup_legacy import rollback_cleanup_legacy

        fixture = self.fixture
        agents = fixture.project / "AGENTS.md"
        before = agents.read_bytes()
        mode = agents.stat().st_mode & 0o777
        module = self._module()
        with mock.patch("sbtd_cleanup_legacy._retirement", return_value=module):
            path, plan_id = fixture.prepare()
            applied, code = fixture.apply(path, plan_id)
        self.assertEqual(code, 0, applied)
        after_mode = agents.stat().st_mode & 0o777
        agents.chmod(after_mode ^ 0o200)
        refused, code = rollback_cleanup_legacy(
            path,
            confirm_cleanup=plan_id,
            cleanup_receipt_path=Path(applied["cleanup_legacy"]["receipt_path"]),
            environ=fixture.environ,
        )
        self.assertEqual((code, refused["status"]), (2, "blocked"), refused)
        self.assertNotEqual(agents.read_bytes(), before)
        agents.chmod(after_mode)
        with mock.patch("sbtd_cleanup_legacy._retirement", return_value=module):
            restored, code = rollback_cleanup_legacy(
                path,
                confirm_cleanup=plan_id,
                cleanup_receipt_path=Path(applied["cleanup_legacy"]["receipt_path"]),
                environ=fixture.environ,
            )
        self.assertEqual((code, restored["status"]), (0, "rolled-back"), restored)
        self.assertEqual(agents.read_bytes(), before)
        self.assertEqual(agents.stat().st_mode & 0o777, mode)
        self.assertTrue((fixture.project / ".gitnexus").is_dir())
        self.assertTrue((fixture.skills / "trellis-workflow").is_dir())
        again, code = rollback_cleanup_legacy(
            path,
            confirm_cleanup=plan_id,
            cleanup_receipt_path=Path(applied["cleanup_legacy"]["receipt_path"]),
            environ=fixture.environ,
        )
        self.assertEqual((code, again["status"]), (2, "blocked"), again)
        self.assertEqual(agents.read_bytes(), before)

    def test_composed_overlap_removes_fence_without_losing_user_text(self):
        fixture = self.fixture
        agents = fixture.project / "AGENTS.md"
        candidate = {
            "path": str(agents),
            "before": {"type": "file", "checksum": __import__("hashlib").sha256(agents.read_bytes()).hexdigest()},
            "mode": f"{agents.stat().st_mode & 0o777:04o}",
            "entries": [{"role": "project-fence", "entry": "fence"}],
            "action": "edit",
            "write_authority": True,
        }
        if os.name == "nt":
            from sbtd_retirement_permissions import capture, digest

            candidate["windows_acl_digest"] = digest(capture(agents))
        module = self._module([candidate])
        with mock.patch("sbtd_cleanup_legacy._retirement", return_value=module):
            path, plan_id = fixture.prepare()
            applied, code = fixture.apply(path, plan_id)
        self.assertEqual(code, 0, applied)
        cleaned = agents.read_bytes()
        self.assertIn(b"# own rules", cleaned)
        self.assertNotIn(b"TRELLIS:START", cleaned)
        self.assertNotIn(b"graft:start", cleaned)
        self.assertFalse(module.apply_candidate.called)



def _seal_document(payload, id_key):
    return {
        "schema_version": 1,
        "payload": payload,
        id_key: hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
    }


def _write_sealed(path, payload, id_key):
    path.write_bytes(canonical_json_bytes(_seal_document(payload, id_key)))


def _operation_result(target, owner, selector, before, after, backup):
    identity = resource_id(owner, target)
    return {
        "phase": "deploy",
        "resource_id": identity,
        "operation_ids": [operation_id("deploy", identity, selector)],
        "dependent_projects": [str(Path(target).parent)],
        "status": "succeeded",
        "backup_ref": None if backup is None else {"path": str(backup), "state": before},
        "before": before,
        "after": after,
        "error": None,
    }


def _append_managed_server(config: Path, home: Path):
    launcher = home / "sbtd_graft_entry.py"
    node = home / "node"
    cli = home / "cli.js"
    python = home / "python"
    for path, payload in (
        (launcher, b"launcher"),
        (node, b"node"),
        (cli, b"cli"),
        (python, b"python"),
    ):
        path.write_bytes(payload)
    before = config.read_bytes()
    args = ["-E", "-s", str(launcher), "mcp", "--node", str(node), "--entry", str(cli)]
    extra = (
        "\n[mcp_servers.sbtd-graft]\n"
        f"command = {json.dumps(str(python))}\n"
        "args = " + json.dumps(args) + "\n"
        '[mcp_servers.sbtd-graft.env]\nDO_NOT_TRACK = "1"\nDNT = "1"\n'
    )
    config.write_bytes(before + extra.encode())
    return before, launcher


class RetirementArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.fixture = CleanupLegacyFixture(Path(self.temporary.name))

    def _fence_evidence(self):
        return self._evidence_descriptor(self._fence_result())

    def _fence_result(self):
        fixture = self.fixture
        agents = fixture.project / "AGENTS.md"
        live = agents.read_bytes()
        fence = b"<!-- graft:start -->\nfence\n<!-- graft:end -->\n"
        original = live[: -len(fence)]
        backup = fixture.vault / "agents-before.md"
        backup.write_bytes(original)
        return _operation_result(
            str(agents),
            "markdown",
            "graft-agents",
            snapshot(backup),
            snapshot(agents),
            backup,
        )

    def _evidence_descriptor(self, *records):
        fixture = self.fixture
        results = fixture.vault / "operation-results.json"
        results.write_bytes(
            json.dumps({"graftWiring": {"operationResults": list(records)}}).encode()
        )
        descriptor = fixture.vault / "descriptor.json"
        _write_sealed(
            descriptor,
            {
                "schema": "sbtd-retirement-evidence/1",
                "items": [{"kind": "operation-results", "path": str(results)}],
            },
            "descriptor_id",
        )
        return descriptor

    def _created_codex_config(self):
        fixture = self.fixture
        config = fixture.home / ".codex/config.toml"
        config.write_bytes(b"")
        _append_managed_server(config, fixture.home)
        result = _operation_result(
            str(config), "toml", "graft-mcp", {"type": "absent", "checksum": None},
            snapshot(config), None,
        )
        return config, result

    def _reset_options(self, *results, with_project=False):
        fixture = self.fixture
        descriptor = self._evidence_descriptor(*results)
        return {
            "selections": {
                "host": "codex",
                "configs": [{"role": "codex-mcp", "path": str(fixture.home / ".codex/config.toml")}],
                "projects": [str(fixture.project)] if with_project else [],
                "vault": str(fixture.vault),
                "retiring_launchers": [],
            },
            "evidence": [{"kind": "descriptor", "path": str(descriptor)}],
            "vault": fixture.vault,
            "environ": fixture.environ,
        }

    def test_plan_and_apply_use_the_same_blocked_host_merge(self):
        fixture = self.fixture
        omp = fixture.home / ".omp/agent/mcp.json"
        launcher = fixture.home / "sbtd_graft_entry.py"
        launcher.write_bytes(b"fixture; not executed")
        original = canonical_json_bytes({"mcpServers": {"sbtd-graft": {
            "type": "stdio", "command": sys.executable,
            "args": ["-E", "-s", str(launcher), "mcp", "--node", str(fixture.home / "node"),
                     "--entry", str(fixture.home / "cli.js")],
            "env": {"DO_NOT_TRACK": "1", "DNT": "1"},
        }}})
        omp.write_bytes(original)
        descriptor = self._evidence_descriptor(_operation_result(
            str(omp), "json", "graft-omp-mcp", {"type": "absent", "checksum": None}, snapshot(omp), None,
        ))
        ready, code = plan_cleanup_legacy(
            [fixture.project], fixture.vault, skills_root=fixture.skills,
            environ=fixture.environ, retirement_evidence=str(descriptor),
        )
        self.assertEqual((code, ready["status"]), (0, "planned"), ready)
        self.assertEqual(
            [row["path"] for row in ready["cleanup_legacy"]["plan"]["payload"]["graftRetirement"]["candidates"]],
            [str(omp)],
        )
        hooks = fixture.home / ".codex/hooks.json"
        hooks.write_bytes(b"{")
        preview, code = plan_cleanup_legacy(
            [fixture.project], fixture.vault, skills_root=fixture.skills,
            environ=fixture.environ, retirement_evidence=str(descriptor),
        )
        sealed = preview["cleanup_legacy"]
        graft = sealed["plan"]["payload"]["graftRetirement"]
        self.assertTrue(graft["view"]["stop"])
        self.assertEqual(graft["candidates"], [])
        self.assertEqual((code, preview["status"]), (2, "blocked"), preview)
        applied, code = fixture.apply(Path(sealed["plan_path"]), preview["plan_id"])
        self.assertEqual((code, applied["status"]), (2, "blocked"), applied)
        self.assertEqual(omp.read_bytes(), original)
        self.assertEqual(hooks.read_bytes(), b"{")
        self.assertTrue((fixture.project / ".gitnexus").is_dir())

    @unittest.skipUnless(os.name == "posix", "symlink fixture")
    def test_codex_reset_and_rollback_do_not_check_omp_paths(self):
        from sbtd_cleanup_legacy import plan_reset_retirement, rollback_cleanup_legacy

        fixture = self.fixture
        config, result = self._created_codex_config()
        original = config.read_bytes()
        link = fixture.home / "omp-linked"
        link.symlink_to(fixture.home / ".omp", target_is_directory=True)
        fixture.environ["PI_CONFIG_DIR"] = link.name
        options = self._reset_options(result)
        preview = plan_reset_retirement(**options)
        self.assertEqual(preview["status"], "planned", preview)
        applied = plan_reset_retirement(**options, confirm=preview["plan_id"])
        self.assertEqual(applied["status"], "cleaned", applied)
        self.assertFalse(config.exists())
        reverted, code = rollback_cleanup_legacy(
            Path(applied["plan_path"]), confirm_cleanup=preview["plan_id"],
            cleanup_receipt_path=Path(applied["receipt_path"]), environ=fixture.environ,
        )
        self.assertEqual((code, reverted["status"]), (0, "rolled-back"), reverted)
        self.assertEqual(config.read_bytes(), original)
        self.assertTrue(link.is_symlink())

    def test_reset_retries_an_unchanged_plan_only_when_saved_bytes_match(self):
        from onboard_contracts import ContractError
        from sbtd_cleanup_legacy import plan_reset_retirement

        config, result = self._created_codex_config()
        original = config.read_bytes()
        options = self._reset_options(result)
        preview = plan_reset_retirement(**options)
        with mock.patch("sbtd_migration_files.remove_reference", side_effect=OSError("write denied")):
            failed = plan_reset_retirement(**options, confirm=preview["plan_id"])
        self.assertEqual((failed["status"], failed["writes"]), ("failed", False), failed)
        saved = Path(failed["plan_path"])
        sealed_bytes = saved.read_bytes()
        reformatted = json.dumps(json.loads(sealed_bytes), indent=2).encode()
        saved.write_bytes(reformatted)
        with self.assertRaisesRegex(ContractError, "saved retirement plan differs"):
            plan_reset_retirement(**options, confirm=preview["plan_id"])
        self.assertEqual(saved.read_bytes(), reformatted)
        self.assertEqual(config.read_bytes(), original)
        saved.write_bytes(sealed_bytes)
        applied = plan_reset_retirement(**options, confirm=preview["plan_id"])
        self.assertEqual((applied["status"], applied["writes"]), ("cleaned", True), applied)
        self.assertFalse(config.exists())
        self.assertEqual(saved.read_bytes(), sealed_bytes)

    def test_partial_reset_rolls_back_measured_completion_if_inner_receipt_save_fails(self):
        from sbtd_cleanup_legacy import plan_reset_retirement, rollback_cleanup_legacy
        from sbtd_migration_files import save_document

        fixture = self.fixture
        agents = fixture.project / "AGENTS.md"
        raw_agents = agents.read_bytes()
        config, config_result = self._created_codex_config()
        original = config.read_bytes()
        options = self._reset_options(config_result, self._fence_result(), with_project=True)
        preview = plan_reset_retirement(**options)

        def refuse_inner_receipt(path, document, *, private_root):
            if path.parent.name == "retirement" and path.name == "000.json":
                raise OSError("receipt persistence denied")
            return save_document(path, document, private_root=private_root)

        with (
            mock.patch("sbtd_migration_files.save_document", side_effect=refuse_inner_receipt),
            mock.patch("sbtd_migration_files.write_file", side_effect=OSError("second target write denied")),
        ):
            failed = plan_reset_retirement(**options, confirm=preview["plan_id"])
        self.assertEqual((failed["status"], failed["writes"]), ("failed", True), failed)
        self.assertFalse(config.exists())
        self.assertEqual(agents.read_bytes(), raw_agents)
        receipt = Path(failed["receipt_path"])
        rows = json.loads(receipt.read_bytes())["payload"]["results"]
        self.assertEqual([row["status"] for row in rows], ["succeeded", "failed"])
        completion = rows[0]["retirement_completion"]["payload"]
        self.assertEqual(completion["backup_ref"], rows[0]["backup_ref"])
        original_backup = fixture.vault / preview["plan_id"] / "cleanup" / "000"
        self.assertEqual(Path(completion["backup_ref"]["path"]), original_backup)
        self.assertEqual(original_backup.read_bytes(), original)
        restored, code = rollback_cleanup_legacy(
            Path(failed["plan_path"]), confirm_cleanup=preview["plan_id"],
            cleanup_receipt_path=receipt, environ=fixture.environ,
        )
        self.assertEqual((code, restored["status"]), (0, "rolled-back"), restored)
        self.assertEqual(config.read_bytes(), original)
        self.assertEqual(agents.read_bytes(), raw_agents)

    def test_saved_retirement_can_resume_after_cumulative_receipt_save_fails(self):
        from sbtd_cleanup_legacy import plan_reset_retirement, rollback_cleanup_legacy
        from sbtd_migration_files import save_document

        fixture = self.fixture
        config, result = self._created_codex_config()
        original = config.read_bytes()
        options = self._reset_options(result)
        preview = plan_reset_retirement(**options)

        def refuse_cumulative_receipt(path, document, *, private_root):
            if path.name.startswith("cleanup-legacy-receipt-"):
                raise OSError("cumulative receipt persistence denied")
            return save_document(path, document, private_root=private_root)

        with mock.patch("sbtd_cleanup_legacy.save_document", side_effect=refuse_cumulative_receipt):
            interrupted = plan_reset_retirement(**options, confirm=preview["plan_id"])
        self.assertEqual((interrupted["status"], interrupted["writes"]), ("failed", True), interrupted)
        self.assertIsNone(interrupted["receipt_path"])
        self.assertFalse(config.exists())
        plan_path = Path(interrupted["plan_path"])
        retried, code = fixture.apply(plan_path, preview["plan_id"])
        self.assertEqual((code, retried["status"]), (0, "cleaned"), retried)
        receipt = Path(retried["receipt_path"])
        restored, code = rollback_cleanup_legacy(
            plan_path, confirm_cleanup=preview["plan_id"], cleanup_receipt_path=receipt, environ=fixture.environ,
        )
        self.assertEqual((code, restored["status"]), (0, "rolled-back"), restored)
        self.assertEqual(config.read_bytes(), original)

    @unittest.skipUnless(os.name == "posix", "POSIX backup naming regression")
    def test_distinct_resets_with_same_entry_keep_separate_originals(self):
        from sbtd_cleanup_legacy import plan_reset_retirement

        fixture = self.fixture
        config = fixture.home / ".codex/config.toml"
        backups = {}
        entry_id = None
        for value in ("first", "second"):
            with self.subTest(value=value):
                original = f'theme = "{value}"\n'.encode()
                config.write_bytes(original)
                _append_managed_server(config, fixture.home)
                managed = config.read_bytes()
                history_backup = fixture.vault / f"{value}-before.toml"
                history_backup.write_bytes(original)
                options = self._reset_options(_operation_result(
                    str(config), "toml", "graft-mcp", snapshot(history_backup), snapshot(config), history_backup,
                ))
                preview = plan_reset_retirement(**options)
                candidate = preview["plan"]["payload"]["graftRetirement"]["candidates"][0]
                if entry_id is None:
                    entry_id = candidate["id"]
                self.assertEqual(candidate["id"], entry_id)
                applied = plan_reset_retirement(**options, confirm=preview["plan_id"])
                self.assertEqual((applied["status"], applied["writes"]), ("cleaned", True), applied)
                self.assertEqual(config.read_bytes(), original)
                backups[fixture.vault / preview["plan_id"] / "cleanup" / "000"] = managed
        self.assertEqual(len(backups), 2)
        for path, original in backups.items():
            self.assertEqual(path.read_bytes(), original)

    def test_interrupted_reset_does_not_infer_completion_from_absent_target(self):
        from sbtd_cleanup_legacy import plan_reset_retirement, rollback_cleanup_legacy

        fixture = self.fixture
        config, result = self._created_codex_config()
        options = self._reset_options(result)
        preview = plan_reset_retirement(**options)

        def lost_outcome(*args, **kwargs):
            remove_reference(*args, **kwargs)
            raise OSError("the primitive did not report an outcome")

        with mock.patch("sbtd_migration_files.remove_reference", side_effect=lost_outcome):
            failed = plan_reset_retirement(**options, confirm=preview["plan_id"])
        self.assertEqual((failed["status"], failed["writes"]), ("failed", None), failed)
        self.assertFalse(config.exists())
        plan_path, receipt = Path(failed["plan_path"]), Path(failed["receipt_path"])
        blocked, code = fixture.apply(plan_path, preview["plan_id"], receipt)
        self.assertEqual((code, blocked["status"], blocked["writes"]), (2, "blocked", None), blocked)
        restored, code = rollback_cleanup_legacy(
            plan_path, confirm_cleanup=preview["plan_id"], cleanup_receipt_path=receipt, environ=fixture.environ,
        )
        self.assertEqual((code, restored["status"]), (2, "blocked"), restored)
        self.assertFalse(config.exists())

    def test_operation_receipt_plans_applies_rolls_back_and_retries(self):
        from sbtd_cleanup_legacy import rollback_cleanup_legacy

        fixture = self.fixture
        agents = fixture.project / "AGENTS.md"
        live = agents.read_bytes()
        descriptor = self._fence_evidence()
        envelope, code = plan_cleanup_legacy(
            [fixture.project],
            fixture.vault,
            skills_root=fixture.skills,
            environ=fixture.environ,
            retirement_evidence=str(descriptor),
        )
        self.assertEqual(code, 0, envelope)
        plan_path = Path(envelope["cleanup_legacy"]["plan_path"])
        applied, code = fixture.apply(plan_path, envelope["plan_id"])
        self.assertEqual(code, 0, applied)
        cleaned = agents.read_bytes()
        self.assertIn(b"# own rules", cleaned)
        self.assertNotIn(b"graft:start", cleaned)
        self.assertNotIn(b"TRELLIS:START", cleaned)
        receipt = Path(applied["cleanup_legacy"]["receipt_path"])
        again, code = fixture.apply(plan_path, envelope["plan_id"], receipt)
        self.assertEqual(code, 0, again)
        self.assertEqual(agents.read_bytes(), cleaned)
        restored, code = rollback_cleanup_legacy(
            plan_path,
            confirm_cleanup=envelope["plan_id"],
            cleanup_receipt_path=receipt,
            environ=fixture.environ,
        )
        self.assertEqual((code, restored["status"]), (0, "rolled-back"), restored)
        self.assertEqual(agents.read_bytes(), live)
        self.assertTrue((fixture.skills / "trellis-workflow").is_dir())
        retried, code = fixture.apply(plan_path, envelope["plan_id"])
        self.assertEqual(code, 0, retried)
        self.assertEqual(agents.read_bytes(), cleaned)

    def test_composed_mcp_cleanup_removes_only_attributed_and_legacy_servers(self):
        from sbtd_cleanup_legacy import rollback_cleanup_legacy

        fixture = self.fixture
        config = fixture.home / ".codex" / "config.toml"
        original, _ = _append_managed_server(config, fixture.home)
        live = config.read_bytes()
        backup = fixture.vault / "config-before.toml"
        backup.write_bytes(original)
        descriptor = self._evidence_descriptor(_operation_result(
            str(config), "toml", "graft-mcp", snapshot(backup), snapshot(config), backup,
        ))
        envelope, code = plan_cleanup_legacy(
            [fixture.project], fixture.vault, skills_root=fixture.skills,
            environ=fixture.environ, retirement_evidence=str(descriptor),
        )
        self.assertEqual(code, 0, envelope)
        plan = Path(envelope["cleanup_legacy"]["plan_path"])
        plan_id = envelope["plan_id"]
        applied, code = fixture.apply(plan, plan_id)
        self.assertEqual(code, 0, applied)
        retired = config.read_bytes()
        self.assertIn(b"[mcp_servers.context7]", retired)
        self.assertNotIn(b"gitnexus", retired)
        self.assertNotIn(b"sbtd-graft", retired)
        restored, code = rollback_cleanup_legacy(
            plan, confirm_cleanup=plan_id,
            cleanup_receipt_path=Path(applied["cleanup_legacy"]["receipt_path"]),
            environ=fixture.environ,
        )
        self.assertEqual(code, 0, restored)
        self.assertEqual(config.read_bytes(), live)

    @unittest.skipUnless(os.name == "nt", "Windows ACL semantics")
    def test_windows_composed_cleanup_binds_acl_on_apply_retry_and_rollback(self):
        from sbtd_cleanup_legacy import rollback_cleanup_legacy
        from tests.test_sbtd_retirement import native_file_acl

        fixture = self.fixture
        agents = fixture.project / "AGENTS.md"
        live = agents.read_bytes()
        original_mode = agents.stat().st_mode
        acl = native_file_acl(agents, world_rights="ReadAttributes")
        descriptor = self._fence_evidence()
        envelope, code = plan_cleanup_legacy(
            [fixture.project], fixture.vault, skills_root=fixture.skills,
            environ=fixture.environ, retirement_evidence=str(descriptor),
        )
        self.assertEqual(code, 0, envelope)
        plan = Path(envelope["cleanup_legacy"]["plan_path"])
        plan_id = envelope["plan_id"]
        self.assertTrue(native_file_acl(agents, world_rights="ReadData") != acl)
        blocked, code = fixture.apply(plan, plan_id)
        self.assertEqual((code, blocked["status"]), (2, "blocked"))
        self.assertEqual(agents.read_bytes(), live)
        self.assertEqual(agents.stat().st_mode, original_mode)
        self.assertTrue((fixture.project / ".gitnexus").is_dir())
        self.assertTrue(native_file_acl(agents, world_rights="ReadAttributes") == acl)
        result, code = fixture.apply(plan, plan_id)
        self.assertEqual(code, 0, result)
        cleaned = agents.read_bytes()
        self.assertIn(b"# own rules", cleaned)
        self.assertNotIn(b"graft:start", cleaned)
        self.assertNotIn(b"TRELLIS:START", cleaned)
        self.assertTrue(native_file_acl(agents) == acl, "composed apply changed Windows ACL")
        receipt = Path(result["cleanup_legacy"]["receipt_path"])
        self.assertTrue(native_file_acl(agents, world_rights="ReadData") != acl)
        # Unchanged file bytes and DOS mode cannot authorize replay or rollback.
        self.assertEqual(agents.read_bytes(), cleaned)
        self.assertEqual(agents.stat().st_mode, original_mode)
        blocked, code = fixture.apply(plan, plan_id, receipt)
        self.assertEqual((code, blocked["status"]), (2, "blocked"))
        blocked, code = rollback_cleanup_legacy(
            plan, confirm_cleanup=plan_id, cleanup_receipt_path=receipt, environ=fixture.environ,
        )
        self.assertEqual((code, blocked["status"]), (2, "blocked"))
        self.assertFalse((fixture.project / ".gitnexus").exists())
        self.assertTrue(native_file_acl(agents, world_rights="ReadAttributes") == acl)
        restored, code = rollback_cleanup_legacy(
            plan, confirm_cleanup=plan_id, cleanup_receipt_path=receipt, environ=fixture.environ,
        )
        self.assertEqual((code, restored["status"]), (0, "rolled-back"), restored)
        self.assertEqual(agents.read_bytes(), live)
        self.assertTrue(native_file_acl(agents) == acl, "composed rollback changed Windows ACL")

    @unittest.skipUnless(os.name == "nt", "Windows ACL semantics")
    def test_windows_reset_retry_refuses_acl_only_drift(self):
        from sbtd_cleanup_legacy import plan_reset_retirement
        from tests.test_sbtd_retirement import native_file_acl

        fixture = self.fixture
        agents = fixture.project / "AGENTS.md"
        acl = native_file_acl(agents, world_rights="ReadAttributes")
        descriptor = self._fence_evidence()
        selections = {
            "host": "codex",
            "configs": [{"role": "codex-mcp", "path": str(fixture.home / ".codex" / "config.toml")}],
            "projects": [str(fixture.project)], "vault": str(fixture.vault), "retiring_launchers": [],
        }
        options = {
            "selections": selections, "evidence": [{"kind": "descriptor", "path": str(descriptor)}],
            "vault": fixture.vault,
        }
        preview = plan_reset_retirement(**options)
        with mock.patch.dict(os.environ, fixture.environ, clear=True):
            applied = plan_reset_retirement(**options, confirm=preview["plan_id"])
        self.assertEqual(applied["status"], "cleaned", applied)
        self.assertEqual(native_file_acl(agents), acl)
        plan, receipt = Path(applied["plan_path"]), Path(applied["receipt_path"])
        retried, code = fixture.apply(plan, preview["plan_id"], receipt)
        self.assertEqual((code, retried["status"]), (0, "cleaned"), retried)

        cleaned = agents.read_bytes()
        mode = agents.stat().st_mode
        self.assertNotEqual(native_file_acl(agents, world_rights="ReadData"), acl)
        self.assertEqual((agents.read_bytes(), agents.stat().st_mode), (cleaned, mode))
        retained = set(fixture.vault.rglob("*"))
        refused, code = fixture.apply(plan, preview["plan_id"], receipt)
        self.assertEqual((code, refused["status"]), (2, "blocked"), refused)
        self.assertEqual((agents.read_bytes(), agents.stat().st_mode), (cleaned, mode))
        self.assertNotEqual(native_file_acl(agents), acl)
        self.assertEqual(set(fixture.vault.rglob("*")), retained)

    @unittest.skipUnless(os.name == "nt", "Windows ACL semantics")
    def test_windows_vendor_overlap_blocks_before_execution(self):
        fixture = self.fixture
        agents = fixture.project / "AGENTS.md"
        before = agents.read_bytes()
        descriptor = self._fence_evidence()
        (fixture.project / ".trellis").mkdir()
        execute = mock.Mock()
        with _fake_vendor(execute=execute):
            envelope, code = plan_cleanup_legacy(
                [fixture.project], fixture.vault, skills_root=fixture.skills,
                environ=fixture.environ, retirement_evidence=str(descriptor),
            )
            self.assertEqual((code, envelope["status"]), (2, "blocked"), envelope)
            self.assertIn("Retire the Graft entry separately", envelope["reason"])
            blocked, code = fixture.apply(Path(envelope["cleanup_legacy"]["plan_path"]), envelope["plan_id"])
            self.assertEqual((code, blocked["status"]), (2, "blocked"))
        execute.assert_not_called()
        self.assertEqual(agents.read_bytes(), before)
        self.assertTrue((fixture.project / ".trellis").is_dir())

    def test_manifest_deployment_reset_does_not_touch_skill_or_trellis(self):
        from sbtd_cleanup_legacy import plan_reset_retirement, rollback_cleanup_legacy

        fixture = self.fixture
        config = fixture.home / ".codex" / "config.toml"

        before, _launcher = _append_managed_server(config, fixture.home)
        owned = config.read_bytes()
        backup = fixture.vault / "codex-before.toml"
        backup.write_bytes(before)
        result = _operation_result(
            str(config),
            "toml",
            "graft-mcp",
            snapshot(backup),
            snapshot(config),
            backup,
        )
        manifest_payload = {
            "shared_operations": [
                {
                    "resource_id": result["resource_id"],
                    "operation_id": result["operation_ids"][0],
                    "target": str(config),
                    "selector": "graft-mcp",
                    "change": {"kind": "configure-graft"},
                }
            ],
            "projects": [],
        }
        manifest = fixture.vault / "manifest.json"
        _write_sealed(manifest, manifest_payload, "manifest_id")
        deployment_payload = {
            "manifest_id": hashlib.sha256(
                canonical_json_bytes(manifest_payload)
            ).hexdigest(),
            "shared_results": [result],
            "projects": [],
        }
        deployment = fixture.vault / "deployment.json"
        _write_sealed(deployment, deployment_payload, "deployment_id")
        selections = {
            "host": "codex",
            "configs": [
                {"role": "codex-mcp", "path": str(config)},
                {"role": "codex-hooks", "path": str(fixture.home / ".codex" / "hooks.json")},
            ],
            "projects": [],
            "vault": None,
            "retiring_launchers": [],
        }
        evidence = [
            {
                "kind": "manifest-deployment",
                "manifest": str(manifest),
                "deployment": str(deployment),
            }
        ]
        preview = plan_reset_retirement(
            selections=selections, evidence=evidence, vault=fixture.vault
        )
        self.assertEqual(preview["status"], "planned", preview)
        self.assertFalse(preview["plan"]["payload"]["projects"])
        self.assertFalse(preview["plan"]["payload"]["shared"]["skills"]["candidates"])
        with mock.patch.dict(os.environ, fixture.environ, clear=True):
            applied = plan_reset_retirement(
                selections=selections,
                evidence=evidence,
                vault=fixture.vault,
                confirm=preview["plan_id"],
            )
        self.assertEqual(applied["status"], "cleaned", applied)
        retired = config.read_bytes()
        self.assertNotIn(b"sbtd-graft", retired)
        self.assertIn(b"gitnexus", retired)
        self.assertIn(b"context7", retired)
        self.assertTrue((fixture.skills / "trellis-workflow").is_dir())
        self.assertTrue((fixture.project / ".gitnexus").is_dir())
        self.assertFalse((fixture.project / ".trellis").exists())
        plan_path = Path(applied["plan_path"])
        receipt = Path(applied["receipt_path"])
        self.assertEqual(applied["retirement_plan_id"], preview["plan_id"])
        composed = hashlib.sha256(
            canonical_json_bytes(
                {
                    "retirementPlan": preview["plan_id"],
                    "installation": [{"target": str(config)}],
                }
            )
        ).hexdigest()
        self.assertNotEqual(composed, preview["plan_id"])
        refused, code = rollback_cleanup_legacy(
            plan_path,
            confirm_cleanup=composed,
            cleanup_receipt_path=receipt,
            environ=fixture.environ,
        )
        self.assertEqual(code, 2, refused)
        self.assertEqual(config.read_bytes(), retired)
        foreign_vault = fixture.base / "other-vault"
        foreign_vault.mkdir(mode=0o700)
        foreign = foreign_vault / "receipt.json"
        foreign.write_bytes(receipt.read_bytes())
        refused, code = rollback_cleanup_legacy(
            plan_path,
            confirm_cleanup=preview["plan_id"],
            cleanup_receipt_path=foreign,
            environ=fixture.environ,
        )
        self.assertEqual(code, 2, refused)
        self.assertEqual(config.read_bytes(), retired)
        config.write_bytes(retired + b"\n# user changed config\n")
        refused, code = fixture.apply(plan_path, preview["plan_id"], receipt)
        self.assertEqual((code, refused["status"]), (2, "blocked"), refused)
        self.assertEqual(config.read_bytes(), retired + b"\n# user changed config\n")
        config.write_bytes(retired)
        mode = config.stat().st_mode & 0o777
        config.chmod(mode ^ 0o200)
        refused, code = fixture.apply(plan_path, preview["plan_id"], receipt)
        self.assertEqual((code, refused["status"]), (2, "blocked"), refused)
        self.assertEqual(config.read_bytes(), retired)
        refused, code = rollback_cleanup_legacy(
            plan_path,
            confirm_cleanup=preview["plan_id"],
            cleanup_receipt_path=receipt,
            environ=fixture.environ,
        )
        self.assertEqual(code, 2, refused)
        self.assertEqual(config.read_bytes(), retired)
        config.chmod(mode)
        restored, code = rollback_cleanup_legacy(
            plan_path,
            confirm_cleanup=applied["retirement_plan_id"],
            cleanup_receipt_path=receipt,
            environ=fixture.environ,
        )
        self.assertEqual((code, restored["status"]), (0, "rolled-back"), restored)
        self.assertEqual(config.read_bytes(), owned)
        self.assertTrue((fixture.skills / "trellis-workflow").is_dir())
        self.assertTrue((fixture.project / ".gitnexus").is_dir())

    def test_substituted_backup_and_foreign_config_do_not_write(self):
        from sbtd_cleanup_legacy import apply_cleanup_legacy, plan_reset_retirement
        from sbtd_retirement import inspect_retirement, render_candidates

        fixture = self.fixture
        config = fixture.home / ".codex" / "config.toml"
        before, _launcher = _append_managed_server(config, fixture.home)
        backup = fixture.vault / "codex-before.toml"
        backup.write_bytes(before)
        identity = {
            "id": resource_id("upgrade-host", str(config)), "kind": "mcp",
            "target": str(config), "decision": "replace",
            "before": snapshot(backup), "desired": snapshot(config),
        }
        upgrade_plan = {
            "plan_schema": "upgrade-plan",
            "status": "planned", "backup_root": str(fixture.vault),
            "resources": [
                {
                    **identity, "classification": "unknown-drift", "source": str(_launcher),
                    "details": {"launcher": {"path": str(_launcher)}},
                }
            ],
        }
        plan_file = fixture.vault / "upgrade-plan.json"
        _write_sealed(plan_file, upgrade_plan, "plan_id")
        upgrade_receipt = {
            "receipt_schema": "upgrade-receipt",
            "plan_id": hashlib.sha256(canonical_json_bytes(upgrade_plan)).hexdigest(),
            "status": "succeeded", "backup_root": str(fixture.vault),
            "resources": [
                {
                    **identity,
                    "result": "succeeded",
                    "mutated": True,
                    "after": snapshot(config),
                    "mechanical_before": snapshot(backup), "mechanical_after": snapshot(config),
                    "created_parents": [], "reason": None,
                    "backup_ref": {"path": str(backup), "state": snapshot(backup)},
                }
            ],
        }
        receipt = _seal_document(upgrade_receipt, "receipt_id")
        receipt_file = fixture.vault / f"upgrade-receipt-{receipt['receipt_id']}.json"
        receipt_file.write_bytes(canonical_json_bytes({
            **receipt, "receipt_path": str(receipt_file), "status": upgrade_receipt["status"],
        }))
        selections = {
            "host": "codex",
            "configs": [
                {"role": "codex-mcp", "path": str(config)},
                {"role": "codex-hooks", "path": str(fixture.home / ".codex" / "hooks.json")},
            ],
            "projects": [],
            "vault": None,
            "retiring_launchers": [],
        }
        evidence = [
            {
                "kind": "upgrade-plan-apply",
                "plan": str(plan_file),
                "receipt": str(receipt_file),
            }
        ]
        preview = plan_reset_retirement(
            selections=selections, evidence=evidence, vault=fixture.vault
        )
        self.assertEqual(preview["status"], "planned", preview)
        evil = json.loads(canonical_json_bytes(preview["plan"]))
        attacker = fixture.vault / "attacker.toml"
        attacker.write_bytes(b"evil = true\n")
        candidate = evil["payload"]["graftRetirement"]["candidates"][0]
        candidate["backup_ref"] = {"path": str(attacker), "state": snapshot(attacker)}
        candidate["desired"] = snapshot(attacker)
        evil["plan_id"] = hashlib.sha256(canonical_json_bytes(evil["payload"])).hexdigest()
        evil_path = fixture.vault / f"cleanup-legacy-plan-{evil['plan_id']}.json"
        evil_path.write_bytes(canonical_json_bytes(evil))
        live = config.read_bytes()
        refused, code = apply_cleanup_legacy(
            evil_path, confirm_cleanup=evil["plan_id"], environ=fixture.environ
        )
        self.assertEqual(code, 2, refused)
        self.assertEqual(config.read_bytes(), live)

        foreign = fixture.base / "not-domain" / "config.toml"
        foreign.parent.mkdir()
        foreign.write_bytes(live)
        foreign_backup = fixture.vault / "foreign-before.toml"
        foreign_backup.write_bytes(before)
        foreign_result = _operation_result(
            str(foreign),
            "toml",
            "graft-mcp",
            snapshot(foreign_backup),
            snapshot(foreign),
            foreign_backup,
        )
        foreign_evidence_path = fixture.vault / "foreign-results.json"
        foreign_evidence_path.write_bytes(
            json.dumps({"operationResults": [foreign_result]}).encode()
        )
        foreign_selections = {
            "host": "codex",
            "configs": [{"role": "codex-mcp", "path": str(foreign)}],
            "projects": [],
            "vault": str(fixture.vault),
            "retiring_launchers": [],
        }
        report = inspect_retirement(
            selections=foreign_selections,
            evidence=[{"kind": "operation-results", "path": str(foreign_evidence_path)}],
        )
        view = render_candidates(report, purpose="reset")
        self.assertTrue(view["candidates"])
        payload = {
            "purpose": "retirement-reset",
            "backup_root": str(fixture.vault),
            "selections": foreign_selections,
            "evidence": [{"kind": "operation-results", "path": str(foreign_evidence_path)}],
            "projects": [],
            "shared": {
                "skills": {"candidates": [], "blocked": []},
                "mcp": {"candidates": [], "blocked": []},
            },
            "graftRetirement": {
                "selections": foreign_selections,
                "evidence": [{"kind": "operation-results", "path": str(foreign_evidence_path)}],
                "report": report,
                "view": view,
                "candidates": [
                    dict(item, kind="graft-retire", path=str(item["path"]))
                    for item in view["candidates"]
                ],
            },
            "stop": False,
        }
        for item in payload["graftRetirement"]["candidates"]:
            item["before"] = snapshot(Path(item["path"]))
        plan_id = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
        foreign_plan = fixture.vault / f"cleanup-legacy-plan-{plan_id}.json"
        foreign_plan.write_bytes(
            canonical_json_bytes(
                {"schema_version": 1, "payload": payload, "plan_id": plan_id}
            )
        )
        foreign_before = foreign.read_bytes()
        refused, code = apply_cleanup_legacy(
            foreign_plan, confirm_cleanup=plan_id, environ=fixture.environ
        )
        self.assertEqual(code, 2, refused)
        self.assertEqual(foreign.read_bytes(), foreign_before)
        self.assertTrue((fixture.skills / "trellis-workflow").is_dir())

    def test_old_plan_without_graft_block_does_not_add_targets(self):
        fixture = self.fixture
        agents = fixture.project / "AGENTS.md"
        live = agents.read_bytes()
        fence = b"<!-- graft:start -->\nfence\n<!-- graft:end -->\n"
        backup = fixture.vault / "unused-before.md"
        backup.write_bytes(live[: -len(fence)])
        result = _operation_result(
            str(agents),
            "markdown",
            "graft-agents",
            snapshot(backup),
            snapshot(agents),
            backup,
        )
        (fixture.vault / "unused-results.json").write_bytes(
            json.dumps({"operationResults": [result]}).encode()
        )
        path, _plan_id = fixture.prepare()
        document = json.loads(path.read_text())
        self.assertIn("graftRetirement", document["payload"])
        document["payload"].pop("graftRetirement")
        document["plan_id"] = hashlib.sha256(
            canonical_json_bytes(document["payload"])
        ).hexdigest()
        path.write_bytes(canonical_json_bytes(document))
        applied, code = fixture.apply(path, document["plan_id"])
        self.assertEqual(code, 0, applied)
        cleaned = agents.read_bytes()
        self.assertIn(b"graft:start", cleaned)
        self.assertIn(b"# own rules", cleaned)
        self.assertNotIn(b"TRELLIS:START", cleaned)

    @unittest.skipUnless(os.name == "posix", "POSIX mode fixture")
    def test_legacy_plan_retry_preserves_recorded_permissions(self):
        fixture = self.fixture
        plan, _ = fixture.prepare()
        payload = json.loads(plan.read_bytes())["payload"]
        payload.pop("graftRetirement")
        _write_sealed(plan, payload, "plan_id")
        plan_id = json.loads(plan.read_bytes())["plan_id"]
        applied, code = fixture.apply(plan, plan_id)
        self.assertEqual(code, 0, applied)
        receipt = applied["cleanup_legacy"]
        agents = fixture.project / "AGENTS.md"
        row = next(r for r in receipt["receipt"]["payload"]["results"] if r["path"] == str(agents))
        changed = int(row["mode_after"], 8) ^ 0o020
        agents.chmod(changed)
        before = snapshot(fixture.project)
        refused, code = fixture.apply(plan, plan_id, Path(receipt["receipt_path"]))
        self.assertEqual((code, refused["status"]), (2, "blocked"), refused)
        self.assertEqual(agents.stat().st_mode & 0o7777, changed)
        self.assertEqual(snapshot(fixture.project), before)

    def test_backup_mode_drift_blocks_before_any_restore(self):
        from sbtd_cleanup_legacy import rollback_cleanup_legacy

        fixture = self.fixture
        path, plan_id = fixture.prepare()
        applied, code = fixture.apply(path, plan_id)
        self.assertEqual(code, 0, applied)
        agents = fixture.project / "AGENTS.md"
        cleaned = agents.read_bytes()
        row = applied["cleanup_legacy"]["receipt"]["payload"]["results"][0]
        backup = Path(row["backup_ref"]["path"])
        current = backup.stat().st_mode & 0o777
        backup.chmod(current ^ 0o200)
        refused, code = rollback_cleanup_legacy(
            path,
            confirm_cleanup=plan_id,
            cleanup_receipt_path=Path(applied["cleanup_legacy"]["receipt_path"]),
            environ=fixture.environ,
        )
        self.assertEqual((code, refused["status"]), (2, "blocked"), refused)
        self.assertEqual(agents.read_bytes(), cleaned)
        self.assertFalse((fixture.project / ".gitnexus").exists())
        self.assertFalse((fixture.skills / "trellis-workflow").exists())

    def test_reset_plan_rejects_broad_skill_cleanup(self):
        from sbtd_cleanup_legacy import apply_cleanup_legacy

        fixture = self.fixture
        skill = fixture.skills / "trellis-workflow"
        selections = {
            "host": None,
            "configs": [],
            "projects": [],
            "vault": str(fixture.vault),
            "retiring_launchers": [],
        }
        payload = {
            "purpose": "retirement-reset",
            "backup_root": str(fixture.vault),
            "selections": selections,
            "evidence": [],
            "projects": [],
            "shared": {
                "skills": {
                    "candidates": [
                        {
                            "kind": "skill-directory",
                            "name": "trellis-workflow",
                            "path": str(skill),
                            "before": snapshot(skill),
                        }
                    ],
                    "blocked": [],
                },
                "mcp": {"candidates": [], "blocked": []},
            },
            "graftRetirement": {
                "selections": selections,
                "evidence": [],
                "report": {"schema": "sbtd-retirement/1", "items": []},
                "view": {"candidates": [], "stop": False},
                "candidates": [],
            },
            "stop": False,
        }
        plan_id = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
        plan_path = fixture.vault / f"cleanup-legacy-plan-{plan_id}.json"
        plan_path.write_bytes(
            canonical_json_bytes(
                {"schema_version": 1, "payload": payload, "plan_id": plan_id}
            )
        )
        refused, code = apply_cleanup_legacy(
            plan_path, confirm_cleanup=plan_id, environ=fixture.environ
        )
        self.assertEqual(code, 2, refused)
        self.assertTrue(skill.is_dir())

if __name__ == "__main__":
    unittest.main()
