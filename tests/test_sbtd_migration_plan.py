from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import onboard_contracts as contracts
import sbtd_migration_plan
from onboard_contracts import ContractError
from sbtd_migration_files import read_file, snapshot
from sbtd_migration_plan import plan_migration, validate_legacy_inputs

from tests.test_sbtd_migration_legacy import (
    _json_bytes,
    _legacy_source,
    _sidecar,
    _task_md,
)


class MigrationPlanTests(unittest.TestCase):
    def test_planning_legacy_identity_is_read_only_and_has_no_global_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = base / "project"
            (project / ".trellis").mkdir(parents=True)
            (project / ".codex/agents").mkdir(parents=True)
            legacy = b"name=dev01\ninitialized_at=2026-09-01T12:00:00\n"
            (project / ".trellis/.developer").write_bytes(legacy)
            owned = b'name = "trellis-implement"\n'
            relative = ".codex/agents/trellis-implement.toml"
            (project / relative).write_bytes(owned)
            (project / ".trellis/.template-hashes.json").write_text(
                json.dumps(
                    {
                        "__version": 2,
                        "hashes": {relative: hashlib.sha256(owned).hexdigest()},
                    }
                )
            )
            (project / ".trellis/.version").write_text("0.6.17\n")
            home = base / "home"
            home.mkdir(mode=0o700)
            vault = base / "vault"
            vault.mkdir(mode=0o700)
            before = {
                str(path.relative_to(base)): path.read_bytes()
                for path in base.rglob("*")
                if path.is_file()
            }
            with mock.patch.dict(
                os.environ,
                {
                    "HOME": str(home),
                    "USERPROFILE": str(home),
                    "CODEX_HOME": str(home / ".codex"),
                    "AGENT_SKILLS_DIR": str(home / ".agent/skills"),
                },
            ):
                manifest = plan_migration(
                    [project],
                    vault,
                    "fixture-custodian",
                    None,
                    tool_versions={"onboard": "fixture", "graft": "0.18.0"},
                )
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        base / "missing-vault",
                        "fixture-custodian",
                        None,
                        tool_versions={"onboard": "fixture", "graft": "0.18.0"},
                    )
            operations = manifest["payload"]["projects"][0]["private_operations"]
            identities = [
                operation
                for operation in operations
                if operation["change"]["kind"] == "migrate-developer"
            ]
            self.assertEqual(
                [operation["target"] for operation in identities],
                [str(project / ".sbtd/developer")],
            )
            self.assertEqual(
                {
                    str(path.relative_to(base)): path.read_bytes()
                    for path in base.rglob("*")
                    if path.is_file()
                },
                before,
            )
            self.assertFalse((project / ".sbtd").exists())
            self.assertEqual(list(vault.iterdir()), [])
            self.assertFalse((base / "missing-vault").exists())
            self.assertEqual(list(home.iterdir()), [])


LEGACY_IDENTITY = b"name=dev01\ninitialized_at=2026-09-01T12:00:00\n"
PLATFORM_TOML = b'name = "trellis-implement"\n'
PLATFORM_REL = ".codex/agents/trellis-implement.toml"
LESSON_BODY = (
    b"<!-- lessons:index -->\nlesson body references LESSON-20260901-a1b2-topic\n"
)
SPEC_BODY = b"# spec\n\napproved spec content\n"


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _ref(path):
    return {"path": str(path), "state": snapshot(path)}


def _home_env(home):
    return mock.patch.dict(
        os.environ,
        {
            "HOME": str(home),
            "USERPROFILE": str(home),
            "CODEX_HOME": str(home / ".codex"),
            "AGENT_SKILLS_DIR": str(home / ".agent/skills"),
        },
    )


def _base_tree(base, *, identity=True, version=b"0.6.17\n"):
    project = base / "project"
    _write(project / PLATFORM_REL, PLATFORM_TOML)
    _write(
        project / ".trellis/.template-hashes.json",
        _json_bytes(
            {
                "__version": 2,
                "hashes": {PLATFORM_REL: hashlib.sha256(PLATFORM_TOML).hexdigest()},
            }
        ),
    )
    if version is not None:
        _write(project / ".trellis/.version", version)
    if identity:
        _write(project / ".trellis/.developer", LEGACY_IDENTITY)
    return project


def _item(item_id, sources, target_path, decision, candidate_path, *, required=True):
    candidate = _ref(candidate_path) if candidate_path is not None else None
    scope = {
        "sources": [dict(reference) for reference in sources],
        "target_path": str(target_path) if target_path is not None else None,
        "decision": decision,
        "candidate_ref": candidate,
    }
    return {
        "item_id": item_id,
        "sources": [dict(reference) for reference in sources],
        "target_path": scope["target_path"],
        "required": required,
        "decision": decision,
        "candidate_ref": candidate,
        "approval": {"basis": "fixture custodian approval", "scope": scope},
    }


def _decisions(vault, items):
    path = vault / "decisions.json"
    path.write_bytes(json.dumps({"schema_version": 1, "items": items}).encode("utf-8"))
    return path


def _add_task(
    project,
    vault,
    items,
    *,
    task_id="alpha",
    folder="09-01-alpha",
    decision="share",
    source_overrides=None,
    task_md_kwargs=None,
    sidecar_kwargs=None,
    with_attachment=False,
):
    source = _legacy_source(id=task_id, name=task_id, **(source_overrides or {}))
    source["id"] = task_id
    source["name"] = task_id
    source_raw = _json_bytes(source)
    folder_path = project / ".trellis/tasks" / folder
    _write(folder_path / "task.json", source_raw)
    source_rel = ".trellis/tasks/{}/task.json".format(folder)
    candidate = vault / "cand-{}".format(folder)
    target_dir = project / "ai/tasks" / task_id
    document_kwargs = {"identity": task_id}
    document_kwargs.update(task_md_kwargs or {})
    _write(candidate / "task.md", _task_md(**document_kwargs))
    sidecar_options = {"source_path": source_rel}
    sidecar_options.update(sidecar_kwargs or {})
    _write(candidate / "legacy-task.json", _sidecar(source_raw, **sidecar_options))
    source_reference = _ref(folder_path / "task.json")
    items.append(
        _item(
            folder + "-document",
            [source_reference],
            target_dir / "task.md",
            decision,
            candidate / "task.md",
        )
    )
    items.append(
        _item(
            folder + "-sidecar",
            [source_reference],
            target_dir / "legacy-task.json",
            decision,
            candidate / "legacy-task.json",
        )
    )
    if with_attachment:
        _write(folder_path / "prd.md", b"# legacy prd\n")
        _write(candidate / "prd.md", b"# legacy prd\n")
        items.append(
            _item(
                folder + "-prd",
                [_ref(folder_path / "prd.md")],
                target_dir / "prd.md",
                decision,
                candidate / "prd.md",
            )
        )
    return source_raw


def _add_spec(project, vault, items, *, body=SPEC_BODY, candidate_body=None):
    _write(project / ".trellis/spec/auth.md", body)
    _write(
        vault / "cand-spec/auth.md", body if candidate_body is None else candidate_body
    )
    items.append(
        _item(
            "spec-auth",
            [_ref(project / ".trellis/spec/auth.md")],
            project / "docs/spec/auth.md",
            "share",
            vault / "cand-spec/auth.md",
        )
    )


def _add_lessons_tree(project, vault, items, *, candidate_body=None):
    nested = b"topic note\n"
    _write(project / ".trellis/lessons/index.md", LESSON_BODY)
    _write(project / ".trellis/lessons/topics/x.md", nested)
    _write(
        vault / "cand-lessons/index.md",
        LESSON_BODY if candidate_body is None else candidate_body,
    )
    _write(vault / "cand-lessons/topics/x.md", nested)
    items.append(
        _item(
            "lessons-tree",
            [
                _ref(project / ".trellis/lessons/index.md"),
                _ref(project / ".trellis/lessons/topics/x.md"),
            ],
            project / "docs/lessons",
            "share",
            vault / "cand-lessons",
        )
    )


def _full_fixture(base):
    """Approved project with task closure (file form), spec and lessons tree."""
    project = _base_tree(base)
    vault = base / "vault"
    vault.mkdir(mode=0o700)
    home = base / "home"
    home.mkdir(mode=0o700)
    items = []
    _add_task(project, vault, items, with_attachment=True)
    _add_spec(project, vault, items)
    _add_lessons_tree(project, vault, items)
    decisions = _decisions(vault, items)
    return project, vault, home, decisions


def _tree_bytes(base):
    return {
        str(path.relative_to(base)): path.read_bytes()
        for path in base.rglob("*")
        if path.is_file()
    }


def _plan(project, vault, decisions, home, roots=None):
    with _home_env(home):
        return plan_migration(
            roots or [project],
            vault,
            "fixture-custodian",
            decisions,
            tool_versions={"onboard": "fixture", "graft": "0.18.0"},
        )


def _reader(reference):
    return Path(reference["path"]).read_bytes()


class MigrationPlanReviewRegressions(unittest.TestCase):
    def test_generated_legacy_tree_is_preserved_until_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = _base_tree(base)
            vault = base / "vault"
            vault.mkdir(mode=0o700)
            home = base / "home"
            home.mkdir(mode=0o700)
            hashes_path = project / ".trellis/.template-hashes.json"
            metadata = json.loads(hashes_path.read_text())
            generated = {
                ".trellis/config.yaml": b"workflow: native\n",
                ".trellis/scripts/task.py": b"# generated legacy entrypoint\n",
                ".trellis/agents/implement.md": b"# generated agent\n",
                ".agents/skills/start/SKILL.md": b"# generated Codex skill\n",
            }
            for relative, raw in generated.items():
                _write(project / relative, raw)
                metadata["hashes"][relative] = hashlib.sha256(raw).hexdigest()
            hashes_path.write_bytes(_json_bytes(metadata))
            _write(project / ".trellis/.gitignore", b"workspace/\n")
            _write(project / ".trellis/.current-task", b"")
            _write(project / ".trellis/tasks/.gitkeep", b"")
            before = _tree_bytes(base)
            manifest = _plan(project, vault, None, home)
            with _home_env(home):
                validate_legacy_inputs(manifest, _reader)
            apply_targets = {
                operation["target"]
                for operation in manifest["payload"]["projects"][0][
                    "private_operations"
                ]
                if operation["phase"] == "apply"
            }
            self.assertIn(str(project / ".agents/skills/start/SKILL.md"), apply_targets)
            self.assertFalse(
                any(
                    Path(target).is_relative_to(project / ".trellis")
                    for target in apply_targets
                )
            )
            self.assertEqual(_tree_bytes(base), before)

    def test_share_cannot_rewrite_directly_copied_members(self):
        for member, item_id in (
            ("cand-spec/auth.md", "spec-auth"),
            ("cand-lessons/topics/x.md", "lessons-tree"),
            ("cand-09-01-alpha/prd.md", "09-01-alpha-prd"),
        ):
            with (
                self.subTest(member=member),
                tempfile.TemporaryDirectory() as directory,
            ):
                base = Path(directory).resolve()
                project, vault, home, decisions = _full_fixture(base)
                (vault / member).write_bytes(b"unapproved replacement\n")
                items = json.loads(decisions.read_text())["items"]
                item = next(item for item in items if item["item_id"] == item_id)
                item["candidate_ref"] = _ref(Path(item["candidate_ref"]["path"]))
                item["approval"]["scope"]["candidate_ref"] = item["candidate_ref"]
                _decisions(vault, items)
                before = _tree_bytes(base)
                with self.assertRaises(ContractError):
                    _plan(project, vault, decisions, home)
                self.assertEqual(_tree_bytes(base), before)

    def test_customized_legacy_global_routing_blocks_without_touching_foreign_text(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = _base_tree(base)
            vault = base / "vault"
            vault.mkdir(mode=0o700)
            home = base / "home"
            home.mkdir(mode=0o700)
            _write(
                home / ".codex/AGENTS.md",
                b"Use trellis-workflow for every task.\n\n# Foreign user rules\nKeep these.\n",
            )
            before = _tree_bytes(base)
            with self.assertRaises(ContractError):
                _plan(project, vault, None, home)
            self.assertEqual(_tree_bytes(base), before)

    def test_recorded_hash_cannot_claim_foreign_shared_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = _base_tree(base)
            vault = base / "vault"
            vault.mkdir(mode=0o700)
            home = base / "home"
            home.mkdir(mode=0o700)
            relative = ".codex/config.toml"
            foreign = b'model = "user-choice"\n\n[agents]\nmax_depth = 1\n'
            _write(project / relative, foreign)
            metadata_path = project / ".trellis/.template-hashes.json"
            metadata = json.loads(metadata_path.read_text())
            metadata["hashes"][relative] = hashlib.sha256(foreign).hexdigest()
            metadata_path.write_bytes(_json_bytes(metadata))
            before = _tree_bytes(base)
            with self.assertRaises(ContractError):
                _plan(project, vault, None, home)
            self.assertEqual(_tree_bytes(base), before)


class MigrationWorkflowOwnershipTests(unittest.TestCase):
    def test_unowned_workflow_requires_explicit_private_only_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            project, vault, home, decisions = _full_fixture(Path(directory).resolve())
            workflow = project / ".trellis/workflow.md"
            workflow.write_bytes(b"# Custom workflow\nPreserve this user policy.\n")
            before = _tree_bytes(project)
            with self.assertRaises(ContractError):
                _plan(project, vault, decisions, home)
            self.assertEqual(_tree_bytes(project), before)
            items = json.loads(decisions.read_text())["items"]
            items.append(
                _item(
                    "custom-workflow",
                    [_ref(workflow)],
                    None,
                    "private-only",
                    None,
                    required=False,
                )
            )
            _decisions(vault, items)
            manifest = _plan(project, vault, decisions, home)
            with _home_env(home):
                validate_legacy_inputs(manifest, _reader)
            self.assertEqual(_tree_bytes(project), before)
            self.assertEqual(
                manifest["payload"]["projects"][0]["sources"][0]["state"],
                snapshot(project / ".trellis"),
            )

    def test_resealed_manifest_cannot_drop_custom_workflow_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            project, vault, home, decisions = _full_fixture(Path(directory).resolve())
            workflow = project / ".trellis/workflow.md"
            workflow.write_bytes(b"# Custom workflow\nPreserve this user policy.\n")
            items = json.loads(decisions.read_text())["items"]
            items.append(
                _item(
                    "custom-workflow",
                    [_ref(workflow)],
                    None,
                    "private-only",
                    None,
                    required=False,
                )
            )
            _decisions(vault, items)
            manifest = _plan(project, vault, decisions, home)
            payload = json.loads(json.dumps(manifest["payload"]))
            payload["publication_decisions"]["items"] = [
                item
                for item in payload["publication_decisions"]["items"]
                if item["item_id"] != "custom-workflow"
            ]
            changed = contracts.seal_document("manifest", payload)
            before = _tree_bytes(project)
            with _home_env(home), self.assertRaises(ContractError):
                validate_legacy_inputs(changed, _reader)
            self.assertEqual(_tree_bytes(project), before)

    def test_original_inventory_uses_only_an_exact_private_backup(self):
        from sbtd_migration import _backup_sources, _source_backup_paths

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, decisions = _full_fixture(base)
            source_root = project / ".trellis"
            workflow = source_root / "workflow.md"
            workflow.write_bytes(b"# Custom workflow\nPreserve this user policy.\n")
            (source_root / "tasks/.gitkeep").write_bytes(b"")
            items = json.loads(decisions.read_text())["items"]
            items.append(
                _item(
                    "custom-workflow",
                    [_ref(workflow)],
                    None,
                    "private-only",
                    None,
                    required=False,
                )
            )
            _decisions(vault, items)
            manifest = _plan(project, vault, decisions, home)
            backup = _source_backup_paths(manifest)[str(source_root)]
            with _home_env(home):
                _backup_sources(manifest)
                source_root.rename(base / "retired-source")

                def original(reference):
                    path = Path(reference["path"])
                    if path.is_relative_to(source_root):
                        path = backup / path.relative_to(source_root)
                    return read_file(path, reference["state"])

                before = snapshot(base)
                validate_legacy_inputs(manifest, original)
                self.assertEqual(snapshot(base), before)
                (backup / "workflow.md").write_bytes(b"changed private original\n")
                with self.assertRaises(ContractError):
                    validate_legacy_inputs(manifest, original)
                self.assertEqual(
                    (base / "retired-source/workflow.md").read_bytes(),
                    b"# Custom workflow\nPreserve this user policy.\n",
                )


class MigrationPlanBatchTests(unittest.TestCase):
    def test_full_batch_plan_and_repeatable_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, decisions = _full_fixture(base)
            before = _tree_bytes(base)
            manifest = _plan(project, vault, decisions, home)
            with _home_env(home):
                self.assertIsNone(validate_legacy_inputs(manifest, _reader))
            payload = manifest["payload"]
            self.assertEqual(manifest["schema_version"], 1)
            self.assertRegex(manifest["manifest_id"], r"^[0-9a-f]{64}$")
            self.assertEqual(payload["backup_root"], str(vault))
            self.assertEqual(payload["shared_operations"], [])
            record = payload["projects"][0]
            self.assertEqual(record["root"], str(project))
            self.assertEqual(record["platforms"], ["codex"])
            self.assertIsNone(record["source_ref"])
            self.assertIsNone(record["head"])
            self.assertEqual(
                [source["path"] for source in record["sources"]],
                [str(project / ".trellis")],
            )
            operations = record["private_operations"]
            phases = {op["phase"] for op in operations}
            self.assertEqual(phases, {"apply", "cleanup"})
            cleanup = [op for op in operations if op["phase"] == "cleanup"]
            self.assertEqual(
                [(op["target"], op["change"]["kind"]) for op in cleanup],
                [(str(project / ".trellis"), "remove")],
            )
            by_kind = {}
            for operation in operations:
                by_kind.setdefault(operation["change"]["kind"], []).append(operation)
            self.assertEqual(
                [op["target"] for op in by_kind["migrate-developer"]],
                [str(project / ".sbtd/developer")],
            )
            removed = {op["target"] for op in by_kind["remove"]}
            self.assertEqual(
                removed, {str(project / PLATFORM_REL), str(project / ".trellis")}
            )
            blocks = by_kind["ensure-file-block"]
            self.assertEqual(
                [op["target"] for op in blocks], [str(project / ".gitignore")]
            )
            self.assertEqual(blocks[0]["owner_kind"], "gitignore")
            copies = {op["target"] for op in by_kind["copy-file"]}
            self.assertEqual(
                copies,
                {
                    str(project / "ai/tasks/alpha/task.md"),
                    str(project / "ai/tasks/alpha/legacy-task.json"),
                    str(project / "ai/tasks/alpha/prd.md"),
                    str(project / "docs/spec/auth.md"),
                },
            )
            directories = by_kind["copy-directory"]
            self.assertEqual(
                [op["target"] for op in directories], [str(project / "docs/lessons")]
            )
            self.assertEqual(
                payload["publication_decisions"]["items"],
                json.loads(decisions.read_text())["items"],
            )
            roundtrip = contracts.load_document(
                contracts.canonical_json_bytes(manifest), "manifest"
            )
            self.assertEqual(roundtrip, manifest)
            # Read-only: nothing changed anywhere, including the vault.
            self.assertEqual(_tree_bytes(base), before)

    def test_git_revision_and_head_are_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, decisions = _full_fixture(base)
            env = {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "GIT_CONFIG_NOSYSTEM": "1",
            }
            for command in (
                ["git", "init", "-b", "main", str(project)],
                ["git", "-C", str(project), "config", "user.email", "fixture@test"],
                ["git", "-C", str(project), "config", "user.name", "fixture"],
                ["git", "-C", str(project), "add", "-A"],
                ["git", "-C", str(project), "commit", "-m", "legacy state"],
            ):
                subprocess.run(
                    command, check=True, capture_output=True, env={**os.environ, **env}
                )
            head = subprocess.run(
                ["git", "-C", str(project), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
                env={**os.environ, **env},
            ).stdout.strip()
            manifest = _plan(project, vault, decisions, home)
            record = manifest["payload"]["projects"][0]
            self.assertEqual(record["source_ref"], "main")
            self.assertEqual(record["head"], head)

    def test_validate_rejects_tampered_originals_and_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, decisions = _full_fixture(base)
            manifest = _plan(project, vault, decisions, home)

            def tampered_source(reference):
                data = _reader(reference)
                if reference["path"].endswith("task.json"):
                    return data + b" "
                return data

            with _home_env(home):
                with self.assertRaises(ContractError):
                    validate_legacy_inputs(manifest, tampered_source)

            def tampered_identity(reference):
                data = _reader(reference)
                if reference["path"].endswith(".developer"):
                    return b"name=other9\n"
                return data

            with _home_env(home):
                with self.assertRaises(ContractError):
                    validate_legacy_inputs(manifest, tampered_identity)
            # A candidate mutated after approval breaks the recorded state.
            target = vault / "cand-spec/auth.md"
            target.write_bytes(b"changed after approval\n")
            with _home_env(home):
                with self.assertRaises(ContractError):
                    validate_legacy_inputs(manifest, _reader)


class MigrationPlanVaultTests(unittest.TestCase):
    def test_vault_must_exist_be_private_and_outside_projects(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = _base_tree(base)
            home = base / "home"
            home.mkdir(mode=0o700)
            with _home_env(home):
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        base / "missing",
                        "c",
                        None,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )
                self.assertFalse((base / "missing").exists())
                loose = base / "loose"
                loose.mkdir(mode=0o755)
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        loose,
                        "c",
                        None,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )
                link = base / "link"
                real = base / "real"
                real.mkdir(mode=0o700)
                link.symlink_to(real)
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        link,
                        "c",
                        None,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )
                inside = project / ".vault"
                inside.mkdir(mode=0o700)
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        inside,
                        "c",
                        None,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )
            self.assertEqual(_tree_bytes(project), _tree_bytes(project))

    def test_overlapping_or_aliased_roots_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = _base_tree(base)
            vault = base / "vault"
            vault.mkdir(mode=0o700)
            home = base / "home"
            home.mkdir(mode=0o700)
            with _home_env(home):
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project, project / ".trellis"],
                        vault,
                        "c",
                        None,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project / ".codex" / ".."],
                        vault,
                        "c",
                        None,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )

    def test_decisions_document_must_live_inside_the_vault(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = _base_tree(base)
            vault = base / "vault"
            vault.mkdir(mode=0o700)
            home = base / "home"
            home.mkdir(mode=0o700)
            outside = base / "decisions.json"
            outside.write_bytes(b'{"schema_version": 1, "items": []}')
            with _home_env(home):
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        vault,
                        "c",
                        outside,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )
            self.assertEqual(
                _tree_bytes(base)[str(outside.relative_to(base))],
                b'{"schema_version": 1, "items": []}',
            )


class MigrationPlanClosureTests(unittest.TestCase):
    def _tree_closure_fixture(self, base):
        project = _base_tree(base)
        vault = base / "vault"
        vault.mkdir(mode=0o700)
        home = base / "home"
        home.mkdir(mode=0o700)
        folder_path = project / ".trellis/tasks/09-01-alpha"
        source_raw = _json_bytes(_legacy_source())
        _write(folder_path / "task.json", source_raw)
        _write(folder_path / "prd.md", b"# legacy prd\n")
        candidate = vault / "cand-tree"
        _write(candidate / "task.md", _task_md())
        _write(candidate / "legacy-task.json", _sidecar(source_raw))
        _write(candidate / "prd.md", b"# legacy prd\n")
        item = _item(
            "09-01-alpha-tree",
            [_ref(folder_path / "task.json"), _ref(folder_path / "prd.md")],
            project / "ai/tasks/alpha",
            "share",
            candidate,
        )
        return project, vault, home, candidate, item

    def test_whole_tree_task_closure_is_one_directory_operation(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, _candidate, item = self._tree_closure_fixture(base)
            decisions = _decisions(vault, [item])
            before = _tree_bytes(base)
            manifest = _plan(project, vault, decisions, home)
            with _home_env(home):
                self.assertIsNone(validate_legacy_inputs(manifest, _reader))
            operations = manifest["payload"]["projects"][0]["private_operations"]
            copies = [
                (op["change"]["kind"], op["target"])
                for op in operations
                if op["change"]["kind"] in {"copy-file", "copy-directory"}
            ]
            self.assertEqual(
                copies, [("copy-directory", str(project / "ai/tasks/alpha"))]
            )
            self.assertEqual(_tree_bytes(base), before)

    def test_tree_candidate_member_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, candidate, item = self._tree_closure_fixture(base)
            # The approved tree silently drops the existing prd attachment.
            (candidate / "prd.md").unlink()
            item = _item(
                item["item_id"],
                item["sources"],
                item["target_path"],
                item["decision"],
                candidate,
            )
            decisions = _decisions(vault, [item])
            with _home_env(home):
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        vault,
                        "c",
                        decisions,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )
            # An unknown extra member is just as unacceptable.
            _write(candidate / "prd.md", b"# migrated prd\n")
            _write(candidate / "smuggled.md", b"extra\n")
            item = _item(
                item["item_id"],
                item["sources"],
                item["target_path"],
                item["decision"],
                candidate,
            )
            decisions = _decisions(vault, [item])
            with _home_env(home):
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        vault,
                        "c",
                        decisions,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )

    def test_missing_approval_never_substitutes_scan_results(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, _decisions_path = _full_fixture(base)
            with _home_env(home):
                # Tasks/spec/lessons exist but no approval document was given.
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        vault,
                        "c",
                        None,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )
                # An approval that covers only the task is still incomplete.
                items = []
                _add_task(project, base / "vault2", items)
            vault2 = base / "vault2"
            vault2.mkdir(mode=0o700, exist_ok=True)
            partial = _decisions(vault2, items)
            with _home_env(home):
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        vault2,
                        "c",
                        partial,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )

    def test_private_only_cannot_cover_mandatory_projections(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = _base_tree(base)
            vault = base / "vault"
            vault.mkdir(mode=0o700)
            home = base / "home"
            home.mkdir(mode=0o700)
            folder_path = project / ".trellis/tasks/09-01-alpha"
            _write(folder_path / "task.json", _json_bytes(_legacy_source()))
            items = [
                _item(
                    "hidden-task",
                    [_ref(folder_path / "task.json")],
                    None,
                    "private-only",
                    None,
                )
            ]
            decisions = _decisions(vault, items)
            with _home_env(home):
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        vault,
                        "c",
                        decisions,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )

    def test_malformed_scope_and_duplicate_candidates_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, decisions = _full_fixture(base)
            document = json.loads(decisions.read_text())
            # Approval scope no longer matches the declared item fields.
            document["items"][0]["approval"]["scope"]["decision"] = "redact"
            decisions.write_bytes(json.dumps(document).encode("utf-8"))
            with _home_env(home):
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        vault,
                        "c",
                        decisions,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )
            document = json.loads(
                _decisions(
                    vault,
                    json.loads((base / "vault/decisions.json").read_text())["items"],
                ).read_text()
            )
            document["items"][1]["candidate_ref"] = document["items"][0][
                "candidate_ref"
            ]
            decisions.write_bytes(json.dumps(document).encode("utf-8"))
            with _home_env(home):
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        vault,
                        "c",
                        decisions,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )

    def test_unknown_legacy_content_and_platform_drift_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, decisions = _full_fixture(base)
            _write(project / ".trellis/mystery.txt", b"unknown\n")
            with _home_env(home):
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        vault,
                        "c",
                        decisions,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, decisions = _full_fixture(base)
            # An unrecorded platform file is foreign user data: it is neither
            # removed nor allowed to block planning.
            _write(project / ".codex/agents/rogue.toml", b'name = "rogue"\n')
            manifest = _plan(project, vault, decisions, home)
            removed = {
                op["target"]
                for op in manifest["payload"]["projects"][0]["private_operations"]
                if op["change"]["kind"] == "remove"
            }
            self.assertNotIn(str(project / ".codex/agents/rogue.toml"), removed)
            self.assertEqual(
                (project / ".codex/agents/rogue.toml").read_bytes(),
                b'name = "rogue"\n',
            )
            # Drifted managed content never authorizes removal either.
            (project / PLATFORM_REL).unlink()
            drifted = b'name = "trellis-implement"\n# drifted\n'
            _write(project / PLATFORM_REL, drifted)
            with _home_env(home):
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        vault,
                        "c",
                        decisions,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )

    def test_graph_conflicts_and_stale_targets_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = _base_tree(base)
            vault = base / "vault"
            vault.mkdir(mode=0o700)
            home = base / "home"
            home.mkdir(mode=0o700)
            items = []
            _add_task(project, vault, items)
            _add_task(
                project,
                vault,
                items,
                task_id="beta",
                folder="09-02-beta",
                source_overrides={"parent": "09-99-ghost"},
                task_md_kwargs={"parent": None},
            )
            decisions = _decisions(vault, items)
            with _home_env(home):
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        vault,
                        "c",
                        decisions,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, decisions = _full_fixture(base)
            # An approved target already exists: apply could not prove safety.
            _write(project / "ai/tasks/alpha/task.md", b"occupied\n")
            with _home_env(home):
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        vault,
                        "c",
                        decisions,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )

    def test_existing_current_identity_precedes_legacy_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, decisions = _full_fixture(base)
            _write(project / ".sbtd/developer", b"name=other9\n")
            manifest = _plan(project, vault, decisions, home)
            self.assertFalse(
                any(
                    op["change"]["kind"] == "migrate-developer"
                    for op in manifest["payload"]["projects"][0]["private_operations"]
                )
            )
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, decisions = _full_fixture(base)
            (project / ".trellis/.developer").write_bytes(b"name=a\nname=b\n")
            with _home_env(home):
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        vault,
                        "c",
                        decisions,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )


class MigrationPlanPrivacyTests(unittest.TestCase):
    def test_redact_projection_and_private_hash_safety(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = _base_tree(base)
            vault = base / "vault"
            vault.mkdir(mode=0o700)
            home = base / "home"
            home.mkdir(mode=0o700)
            source = _legacy_source()
            redacted_original = json.loads(_json_bytes(source).decode("utf-8"))
            redacted_original["meta"] = None
            items = []
            _add_task(
                project,
                vault,
                items,
                decision="redact",
                sidecar_kwargs={
                    "sha": None,
                    "redacted": ["/meta"],
                    "original": redacted_original,
                },
            )
            decisions = _decisions(vault, items)
            before = _tree_bytes(base)
            manifest = _plan(project, vault, decisions, home)
            self.assertEqual(
                [
                    item["decision"]
                    for item in manifest["payload"]["publication_decisions"]["items"]
                ],
                ["redact", "redact"],
            )
            self.assertEqual(_tree_bytes(base), before)

    def test_redact_sidecar_never_pins_private_source_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = _base_tree(base)
            vault = base / "vault"
            vault.mkdir(mode=0o700)
            home = base / "home"
            home.mkdir(mode=0o700)
            items = []
            _add_task(
                project,
                vault,
                items,
                decision="redact",
                sidecar_kwargs={"redacted": ["/meta"]},
            )
            decisions = _decisions(vault, items)
            with _home_env(home):
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        vault,
                        "c",
                        decisions,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )

    def test_shared_projection_never_embeds_private_digest_or_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = _base_tree(base)
            vault = base / "vault"
            vault.mkdir(mode=0o700)
            home = base / "home"
            home.mkdir(mode=0o700)
            folder_path = project / ".trellis/tasks/09-01-alpha"
            source_raw = _json_bytes(_legacy_source())
            _write(folder_path / "task.json", source_raw)
            digest = hashlib.sha256(source_raw).hexdigest()
            candidate = vault / "cand-09-01-alpha"
            _write(candidate / "task.md", _task_md() + digest.encode("utf-8") + b"\n")
            _write(candidate / "legacy-task.json", _sidecar(source_raw))
            source_reference = _ref(folder_path / "task.json")
            items = [
                _item(
                    "09-01-alpha-document",
                    [source_reference],
                    project / "ai/tasks/alpha/task.md",
                    "share",
                    candidate / "task.md",
                ),
                _item(
                    "09-01-alpha-sidecar",
                    [source_reference],
                    project / "ai/tasks/alpha/legacy-task.json",
                    "share",
                    candidate / "legacy-task.json",
                ),
            ]
            decisions = _decisions(vault, items)
            with _home_env(home):
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        vault,
                        "c",
                        decisions,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )
            # A candidate still pointing at the retired layout is not a safe
            # rewritten link either.
            _write(candidate / "task.md", _task_md() + b"see .trellis/tasks\n")
            items[0] = _item(
                "09-01-alpha-document",
                [source_reference],
                project / "ai/tasks/alpha/task.md",
                "share",
                candidate / "task.md",
            )
            decisions = _decisions(vault, items)
            with _home_env(home):
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        vault,
                        "c",
                        decisions,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )

    def test_lessons_marker_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, decisions = _full_fixture(base)
            # Dropping the lesson marker from the approved copy is caught even
            # though the candidate checksum is honestly recomputed.
            _write(vault / "cand-lessons/index.md", b"lesson body without markers\n")
            items = json.loads(decisions.read_text())["items"]
            for item in items:
                if item["item_id"] == "lessons-tree":
                    item["candidate_ref"] = _ref(vault / "cand-lessons")
                    item["approval"]["scope"]["candidate_ref"] = item["candidate_ref"]
                    item["decision"] = "redact"
                    item["approval"]["scope"]["decision"] = "redact"
            decisions = _decisions(vault, items)
            with _home_env(home):
                with self.assertRaises(ContractError):
                    plan_migration(
                        [project],
                        vault,
                        "c",
                        decisions,
                        tool_versions={"onboard": "f", "graft": "0.18.0"},
                    )


class MigrationPlanCurrentFindingsTests(unittest.TestCase):
    def test_archived_tasks_require_the_derived_archive_target(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = _base_tree(base)
            vault, home = base / "vault", base / "home"
            vault.mkdir(mode=0o700)
            home.mkdir(mode=0o700)
            items = []
            _add_task(
                project,
                vault,
                items,
                folder="archive/2026-09/09-01-alpha",
                source_overrides={"status": "completed", "completedAt": "2026-09-05"},
                task_md_kwargs={"status": "done", "events": [{"at": "unknown", "from": "unknown", "to": "done", "reason": "legacy completion fact", "evidence": "legacy task.json status"}]},
            )
            decisions = _decisions(vault, items)
            with _home_env(home), self.assertRaises(ContractError):
                plan_migration(
                    [project], vault, "c", decisions, tool_versions={"onboard": "f", "graft": "0.18.0"}
                )
            archive = project / "ai/tasks/archive/2026-Q3/alpha"
            for item in items:
                item["target_path"] = str(archive / Path(item["target_path"]).name)
                item["approval"]["scope"]["target_path"] = item["target_path"]
            decisions = _decisions(vault, items)
            manifest = _plan(project, vault, decisions, home)
            copies = [
                operation["target"]
                for operation in manifest["payload"]["projects"][0]["private_operations"]
                if operation["change"]["kind"].startswith("copy-")
            ]
            self.assertEqual(copies, [str(archive / "legacy-task.json"), str(archive / "task.md")])

    def test_unknown_completion_time_requires_the_undated_archive_target(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = _base_tree(base)
            vault, home = base / "vault", base / "home"
            vault.mkdir(mode=0o700)
            home.mkdir(mode=0o700)
            items = []
            _add_task(
                project,
                vault,
                items,
                folder="archive/unknown/09-01-alpha",
                source_overrides={"status": "completed"},
                task_md_kwargs={"status": "done", "events": [{"at": "unknown", "from": "unknown", "to": "done", "reason": "legacy completion fact", "evidence": "legacy task.json status"}]},
            )
            archive = project / "ai/tasks/archive/undated/alpha"
            for item in items:
                item["target_path"] = str(archive / Path(item["target_path"]).name)
                item["approval"]["scope"]["target_path"] = item["target_path"]
            manifest = _plan(project, vault, _decisions(vault, items), home)
            self.assertIn(
                str(archive / "task.md"),
                [op["target"] for op in manifest["payload"]["projects"][0]["private_operations"]],
            )

    def test_completed_active_task_is_not_implicitly_archived(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = _base_tree(base)
            vault, home = base / "vault", base / "home"
            vault.mkdir(mode=0o700)
            home.mkdir(mode=0o700)
            items = []
            _add_task(
                project, vault, items,
                source_overrides={"status": "completed"},
                task_md_kwargs={
                    "status": "done",
                    "events": [{
                        "at": "unknown", "from": "unknown", "to": "done",
                        "reason": "legacy completion fact",
                        "evidence": "legacy task.json status",
                    }],
                },
            )
            manifest = _plan(project, vault, _decisions(vault, items), home)
            targets = [
                op["target"]
                for op in manifest["payload"]["projects"][0]["private_operations"]
                if op["change"]["kind"].startswith("copy-")
            ]
            self.assertIn(str(project / "ai/tasks/alpha/task.md"), targets)
            self.assertFalse(any("/ai/tasks/archive/" in target for target in targets))

    def test_duplicate_logical_legacy_ids_block_before_projection_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = _base_tree(base)
            vault, home = base / "vault", base / "home"
            vault.mkdir(mode=0o700)
            home.mkdir(mode=0o700)
            items = []
            _add_task(project, vault, items, folder="09-01-alpha")
            _add_task(
                project, vault, items, folder="archive/unknown/09-02-alpha",
                source_overrides={"status": "completed"},
                task_md_kwargs={
                    "status": "done",
                    "events": [{
                        "at": "unknown", "from": "unknown", "to": "done",
                        "reason": "legacy completion fact",
                        "evidence": "legacy task.json status",
                    }],
                },
            )
            for item in items[2:]:
                item["target_path"] = str(
                    project / "ai/tasks/archive/undated/alpha" / Path(item["target_path"]).name
                )
                item["approval"]["scope"]["target_path"] = item["target_path"]
            with _home_env(home), self.assertRaises(ContractError) as caught:
                plan_migration(
                    [project], vault, "c", _decisions(vault, items), tool_versions={"onboard": "f", "graft": "0.18.0"}
                )
            self.assertEqual(caught.exception.code, "graph-conflict")

    def test_nested_task_files_belong_to_the_deepest_task_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = _base_tree(base)
            vault, home = base / "vault", base / "home"
            vault.mkdir(mode=0o700)
            home.mkdir(mode=0o700)
            items = []
            _add_task(
                project,
                vault,
                items,
                task_id="parent",
                folder="09-parent",
                source_overrides={"children": ["09-parent/10-child"]},
            )
            _add_task(
                project,
                vault,
                items,
                task_id="child",
                folder="09-parent/10-child",
                source_overrides={"parent": "09-parent"},
                task_md_kwargs={"parent": "parent"},
            )
            manifest = _plan(project, vault, _decisions(vault, items), home)
            self.assertEqual(len(manifest["payload"]["publication_decisions"]["items"]), 4)

    def test_optional_private_task_attachment_is_covered_without_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, decisions = _full_fixture(base)
            items = json.loads(decisions.read_text())["items"]
            attachment = next(item for item in items if item["item_id"].endswith("-prd"))
            attachment.update(required=False, decision="private-only", target_path=None, candidate_ref=None)
            attachment["approval"]["scope"].update(
                decision="private-only", target_path=None, candidate_ref=None
            )
            manifest = _plan(project, vault, _decisions(vault, items), home)
            copied = {
                operation["target"]
                for operation in manifest["payload"]["projects"][0]["private_operations"]
                if operation["change"]["kind"].startswith("copy-")
            }
            self.assertNotIn(str(project / "ai/tasks/alpha/prd.md"), copied)

    def test_shared_markdown_links_need_a_planned_local_target(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, decisions = _full_fixture(base)

            def update_spec(body):
                source = project / ".trellis/spec/auth.md"
                candidate = vault / "cand-spec/auth.md"
                _write(source, body)
                _write(candidate, body)
                items = json.loads(decisions.read_text())["items"]
                index = next(i for i, item in enumerate(items) if item["item_id"] == "spec-auth")
                items[index] = _item(
                    "spec-auth", [_ref(source)], project / "docs/spec/auth.md", "share", candidate
                )
                return _decisions(vault, items)

            manifest = _plan(
                project,
                vault,
                update_spec(
                    b"[lesson](../lessons/index.md) [web](https://example.test)\n"
                    b"[http](http://example.test/x) [mail](mailto:dev@example.test)\n"
                    b"![inline](data:image/png;base64,AAAA)\n"
                ),
                home,
            )
            self.assertEqual(manifest["payload"]["projects"][0]["root"], str(project))
            for body in (
                b"[missing](missing.md)\n",
                b"[escape](../../outside.md)\n",
                b"[file](file:///outside.md)\n",
                b"[unsafe](javascript:alert%281%29)\n",
                b"[unsafe-data](data:text/html,test)\n",
                b"![missing](missing.png)\n",
                b"[drive](C:/outside.md)\n",
                b"[encoded-drive](C%3A%2Foutside.md)\n",
                b"[drive-relative](C:secret.md)\n",
                b"![drive-relative](c:secret.png)\n",
                b"![encoded-drive-relative](c%3Asecret.png)\n",
            ):
                with self.subTest(body=body):
                    with _home_env(home), self.assertRaises(ContractError) as caught:
                        plan_migration(
                            [project], vault, "c", update_spec(body), tool_versions={"onboard": "f", "graft": "0.18.0"}
                        )
                    self.assertEqual(caught.exception.code, "target-conflict")
                    self.assertEqual(caught.exception.exit_code, 2)

    def test_current_identity_precedes_malformed_legacy_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, decisions = _full_fixture(base)
            _write(project / ".sbtd/developer", b"name=current9\n")
            _write(project / ".trellis/.developer", b"name=broken\nname=broken\n")
            manifest = _plan(project, vault, decisions, home)
            self.assertFalse(
                any(
                    op["change"]["kind"] == "migrate-developer"
                    for op in manifest["payload"]["projects"][0]["private_operations"]
                )
            )

    def test_existing_complete_ignore_protection_needs_no_duplicate_operation(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, decisions = _full_fixture(base)
            _write(project / ".gitignore", sbtd_migration_plan._IGNORE_ASSET.read_bytes())
            manifest = _plan(project, vault, decisions, home)
            project_record = dict(manifest["payload"]["projects"][0])
            project_record["private_operations"] = [
                *project_record["private_operations"], {"phase": "deploy"}
            ]
            sbtd_migration_plan._validate_project_operations(
                project, project_record, manifest["payload"]["publication_decisions"]["items"], _strict_reader
            )


class MigrationPlanSharedTests(unittest.TestCase):
    def test_drifted_shared_resources_are_preserved_without_operations(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = _base_tree(base)
            vault = base / "vault"
            vault.mkdir(mode=0o700)
            home = base / "home"
            home.mkdir(mode=0o700)
            _write(home / ".codex/AGENTS.md", b"# locally customized agents\n")
            _write(home / ".agent/skills/trellis-workflow/SKILL.md", b"custom\n")
            before = _tree_bytes(base)
            manifest = _plan(project, vault, None, home)
            self.assertEqual(manifest["payload"]["shared_operations"], [])
            self.assertEqual(_tree_bytes(base), before)

    def test_unrelated_shared_skills_are_preserved_without_blocking_retirement(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project = _base_tree(base)
            vault = base / "vault"
            vault.mkdir(mode=0o700)
            home = base / "home"
            home.mkdir(mode=0o700)
            unrelated = home / ".agent/skills/unknown-skill/SKILL.md"
            _write(unrelated, b"name: other\n")
            outside = base / "unrelated-target"
            outside.mkdir()
            (home / ".agent/skills/unrelated-link").symlink_to(outside, target_is_directory=True)
            manifest = _plan(project, vault, None, home)
            self.assertEqual(manifest["payload"]["shared_operations"], [])
            self.assertEqual(unrelated.read_bytes(), b"name: other\n")


def _strict_reader(reference):
    from sbtd_migration_files import read_file

    return read_file(Path(reference["path"]), reference["state"])


def _reseal(manifest, mutate):
    payload = json.loads(json.dumps(manifest["payload"]))
    mutate(payload)
    return contracts.seal_document("manifest", payload)


class MigrationPlanOperationGateTests(unittest.TestCase):
    """Re-sealed manifests with altered operation sets must not validate."""

    def _planned(self, base):
        project, vault, home, decisions = _full_fixture(base)
        manifest = _plan(project, vault, decisions, home)
        with _home_env(home):
            self.assertIsNone(validate_legacy_inputs(manifest, _strict_reader))
        return project, vault, home, manifest

    def test_resealed_redundant_ignore_operation_is_rejected_from_original_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, _vault, home, manifest = self._planned(base)
            _write(project / ".gitignore", sbtd_migration_plan._IGNORE_ASSET.read_bytes())

            def make_redundant(payload):
                operation = next(
                    op for op in payload["projects"][0]["private_operations"]
                    if op["owner_kind"] == "gitignore"
                )
                operation["before_requirement"]["state"] = snapshot(project / ".gitignore")

            tampered = _reseal(manifest, make_redundant)
            with _home_env(home), self.assertRaises(ContractError) as caught:
                validate_legacy_inputs(tampered, _strict_reader)
            self.assertEqual(caught.exception.code, "semantic-violation")

    def test_invented_private_operation_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, manifest = self._planned(base)
            hashes_ref = None
            for op in manifest["payload"]["projects"][0]["private_operations"]:
                if (
                    op["ownership"]["kind"] == "template-source"
                    and op["change"] == {"kind": "remove"}
                    and op["phase"] == "apply"
                ):
                    hashes_ref = op["ownership"]["reference"]
            self.assertIsNotNone(hashes_ref)

            def mutate(payload):
                target = str(Path(payload["projects"][0]["root"]) / "app.py")
                resource = contracts.resource_id("file", target)
                payload["projects"][0]["private_operations"].append(
                    {
                        "operation_id": contracts.operation_id(
                            "apply", resource, "whole-resource"
                        ),
                        "phase": "apply",
                        "resource_id": resource,
                        "owner_kind": "file",
                        "target": target,
                        "selector": "whole-resource",
                        "change": {"kind": "remove"},
                        "ownership": {
                            "kind": "template-source",
                            "reference": hashes_ref,
                        },
                        "before_requirement": {
                            "kind": "state",
                            "state": {"type": "file", "checksum": "ab" * 32},
                        },
                        "dependent_projects": [payload["projects"][0]["root"]],
                    }
                )

            tampered = _reseal(manifest, mutate)
            with _home_env(home):
                with self.assertRaises(ContractError):
                    validate_legacy_inputs(tampered, _strict_reader)

    def test_missing_protection_or_output_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, manifest = self._planned(base)

            def drop_protection(payload):
                ops = payload["projects"][0]["private_operations"]
                payload["projects"][0]["private_operations"] = [
                    op for op in ops if op["owner_kind"] != "gitignore"
                ]

            tampered = _reseal(manifest, drop_protection)
            with _home_env(home):
                with self.assertRaises(ContractError):
                    validate_legacy_inputs(tampered, _strict_reader)

            def drop_output(payload):
                ops = payload["projects"][0]["private_operations"]
                payload["projects"][0]["private_operations"] = [
                    op for op in ops if op["change"]["kind"] != "copy-directory"
                ]

            with self.assertRaises(ContractError):
                # The codec itself already refuses an unmatched approval.
                _reseal(manifest, drop_output)

    def test_altered_identity_or_platform_ownership_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, manifest = self._planned(base)

            def rename_identity(payload):
                for op in payload["projects"][0]["private_operations"]:
                    if op["change"].get("kind") == "migrate-developer":
                        op["change"]["name"] = "other9"

            tampered = _reseal(manifest, rename_identity)
            with _home_env(home):
                with self.assertRaises(ContractError):
                    validate_legacy_inputs(tampered, _strict_reader)

            def fake_platform_state(payload):
                for op in payload["projects"][0]["private_operations"]:
                    if op["change"] == {"kind": "remove"} and op["phase"] == "apply":
                        op["ownership"]["reference"]["state"] = {
                            "type": "file",
                            "checksum": "cd" * 32,
                        }

            tampered = _reseal(manifest, fake_platform_state)
            with _home_env(home):
                with self.assertRaises(ContractError):
                    validate_legacy_inputs(tampered, _strict_reader)

    def test_invented_shared_operation_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project, vault, home, manifest = self._planned(base)

            def mutate(payload):
                root = payload["projects"][0]["root"]
                shared_root = str(Path(root).parent)
                target = str(Path(shared_root) / "AGENTS.md")
                resource = contracts.resource_id("markdown", target)
                operation_id = contracts.operation_id(
                    "apply", resource, "pause-legacy-routing"
                )
                payload["shared_roots"].append(
                    {
                        "kind": "codex-home",
                        "path": shared_root,
                        "dependent_projects": [payload["projects"][0]["root"]],
                    }
                )
                payload["shared_operations"].append(
                    {
                        "operation_id": operation_id,
                        "phase": "apply",
                        "resource_id": resource,
                        "owner_kind": "markdown",
                        "target": target,
                        "selector": "pause-legacy-routing",
                        "change": {
                            "kind": "ensure-file-block",
                            "source_ref": {
                                "path": target,
                                "state": {"type": "file", "checksum": "ef" * 32},
                            },
                        },
                        "ownership": {
                            "kind": "template-source",
                            "reference": {
                                "path": target,
                                "state": {"type": "file", "checksum": "ef" * 32},
                            },
                        },
                        "before_requirement": {
                            "kind": "state",
                            "state": {"type": "file", "checksum": "ef" * 32},
                        },
                        "dependent_projects": [payload["projects"][0]["root"]],
                    }
                )
                payload["projects"][0]["shared_operation_ids"] = [operation_id]

            tampered = _reseal(manifest, mutate)
            with _home_env(home):
                with self.assertRaises(ContractError):
                    validate_legacy_inputs(tampered, _strict_reader)


if __name__ == "__main__":
    unittest.main()
