"""Catalog-driven upgrade inventory: baseline, difference, safety and scope tests.

Scenarios trace design.md U01/U02/U04/U05/U14/U15: the fixed baseline is
content-bound (never path/mtime), content-valid older shells are drift rather
than "aligned", known-old requires shipped evidence, stable/identity/symlink
tampering fails closed, selected shared roots are deduplicated, decisions are
explicit, and output carries relative names plus digests only — never content.
All tests are deterministic against synthetic fixture packages; the real
package is only scanned read-only for catalog coverage proof.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "sbtd-workflow-onboard" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import sbtd_upgrade_inventory as inventory
from onboard_contracts import ContractError, canonical_json_bytes

ONBOARD_PY = SCRIPTS / "onboard.py"
_REFERENCE_MODULE = None


def reference_onboard():
    """The established stable tree-digest implementation (cross-check oracle)."""
    global _REFERENCE_MODULE
    if _REFERENCE_MODULE is None:
        spec = importlib.util.spec_from_file_location("onboard_reference", ONBOARD_PY)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load onboard reference module")
        loader = cast(importlib.machinery.SourceFileLoader, spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules["onboard_reference"] = module
        loader.exec_module(module)
        _REFERENCE_MODULE = module
    return _REFERENCE_MODULE


OLD_AGENTS = b"# Legacy global routing\nOld managed instructions.\n"
NEW_AGENTS = b"# SBTD global routing\nCurrent managed instructions.\n"
BUNDLED = ("alpha-skill", "beta-skill")
EXTERNAL = ("gamma-skill", "delta-skill")
SELF_NAME = "sbtd-workflow-onboard"
UPSTREAM_REPO = "https://github.com/example/upstream.git"
UPSTREAM_REVISION = "1" * 40


def skill_md(name: str, body: str = "managed body") -> str:
    return f"---\nname: {name}\ndescription: fixture {name}\n---\n\n{body}\n"


def build_package(root: Path) -> Path:
    """One synthetic but fully valid Onboard package fixture."""
    pkg = root / "pkg"
    (pkg / "scripts").mkdir(parents=True)
    (pkg / "scripts" / "onboard.py").write_text("# fixture runtime\n", encoding="utf-8")
    (pkg / "requirements.txt").write_text("jsonschema>=4,<5\n", encoding="utf-8")
    (pkg / "catalog.schema.json").write_text("{}\n", encoding="utf-8")
    (pkg / "onboard-contracts.schema.json").write_text("{}\n", encoding="utf-8")
    (pkg / "SKILL.md").write_text(skill_md(SELF_NAME), encoding="utf-8")

    agents_dir = pkg / "templates" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "AGENTS.global.md").write_bytes(NEW_AGENTS)

    for name in BUNDLED:
        skill_dir = pkg / "templates" / "skills" / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(skill_md(name), encoding="utf-8")
    beta_notes = pkg / "templates" / "skills" / "beta-skill" / "references"
    beta_notes.mkdir()
    (beta_notes / "notes.md").write_text("beta notes\n", encoding="utf-8")

    stable = pkg / "assets" / "external-skills" / "stable"
    (stable / "licenses").mkdir(parents=True)
    (stable / "licenses" / "upstream-LICENSE").write_text(
        "MIT fixture license\n", encoding="utf-8"
    )
    for name in EXTERNAL:
        skill_dir = stable / "skills" / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(skill_md(name), encoding="utf-8")
    gamma_scripts = stable / "skills" / "gamma-skill" / "scripts"
    gamma_scripts.mkdir()
    (gamma_scripts / "tool.sh").write_text("#!/bin/sh\ntrue\n", encoding="utf-8")

    reference = reference_onboard()
    manifest = {
        "schemaVersion": 1,
        "stableSet": "2026-01-01.1",
        "promotedAt": "2026-01-01",
        "repositories": {
            "upstream": {
                "url": UPSTREAM_REPO,
                "revision": UPSTREAM_REVISION,
                "license": "MIT",
                "licenseFiles": [
                    {"source": "LICENSE", "stablePath": "licenses/upstream-LICENSE"}
                ],
            }
        },
        "skills": {
            name: {
                "repository": "upstream",
                "sourceSubpath": f"vendor/{name}",
                "stablePath": f"skills/{name}",
                "treeSha256": reference.external_tree_sha256(stable / "skills" / name),
            }
            for name in EXTERNAL
        },
    }
    (stable / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    ownership = {
        "schema_version": 1,
        "source_tag": "v9.9.9",
        "source_commit": "2" * 40,
        "global_agents_sha256": hashlib.sha256(OLD_AGENTS).hexdigest(),
        "project_source_commit": "3" * 40,
        "project_config_templates": {".codex/config.toml": ["4" * 64]},
        "skills": {},
    }
    ownership_path = pkg / "assets" / "migration-legacy-ownership.json"
    ownership_path.write_text(json.dumps(ownership, indent=2) + "\n", encoding="utf-8")

    entries = [
        {
            "id": "agent:codex-global",
            "kind": "agent-template",
            "source": "templates/agents/AGENTS.global.md",
            "targetRole": "codex-global-agents",
        },
        {
            "id": f"skill:{SELF_NAME}",
            "kind": "bundled-skill",
            "source": ".",
            "targetRole": "skill:sbtd-workflow-onboard",
        },
    ]
    entries += [
        {
            "id": f"skill:{name}",
            "kind": "bundled-skill",
            "source": f"templates/skills/{name}",
            "targetRole": "skill",
        }
        for name in BUNDLED
    ]
    entries += [
        {
            "id": f"skill:{name}",
            "kind": "external-skill",
            "source": {
                "repo": UPSTREAM_REPO,
                "subpath": f"vendor/{name}",
                "aliases": [name],
            },
            "targetRole": "external-skill",
        }
        for name in EXTERNAL
    ]
    catalog = {
        "$schema": "./catalog.schema.json",
        "schemaVersion": 1,
        "name": "sbtd-workflow-onboard",
        "entries": entries,
    }
    (pkg / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    return pkg


def skill_names(pkg: Path) -> set[str]:
    catalog = json.loads((pkg / "catalog.json").read_text(encoding="utf-8"))
    return {
        entry["id"].removeprefix("skill:")
        for entry in catalog["entries"]
        if entry["kind"] in {"bundled-skill", "external-skill"}
    }


def install_all(pkg: Path, root: Path) -> None:
    """Install every catalog skill exactly as the payload sources dictate."""
    root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(pkg, root / SELF_NAME)
    for name in BUNDLED:
        shutil.copytree(pkg / "templates" / "skills" / name, root / name)
    for name in EXTERNAL:
        shutil.copytree(
            pkg / "assets" / "external-skills" / "stable" / "skills" / name,
            root / name,
        )


def by_name(document: dict) -> dict[str, dict]:
    return {Path(resource["target"]).name: resource for resource in document["resources"]}


class InventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sbtd-upgrade-inventory-")
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name).resolve()
        self.pkg = build_package(self.base)
        self.skills_root = self.base / "skills"

    def scope(self, **overrides) -> dict:
        document = {"schema_version": 1}
        document.update(overrides)
        return document

    def build(self, scope: dict, **kwargs):
        kwargs.setdefault("package_root", self.pkg)
        return inventory.build_inventory(scope, **kwargs)

    def assert_code(self, code: str, scope: dict, **kwargs) -> ContractError:
        with self.assertRaises(ContractError) as raised:
            self.build(scope, **kwargs)
        self.assertEqual(raised.exception.code, code)
        return raised.exception


class BaselineTests(InventoryTests):
    def test_baseline_is_content_bound_not_path_or_mtime(self):
        scope = self.scope(skills_roots=[str(self.skills_root)])
        first = self.build(scope)

        relocated = self.base / "elsewhere" / "pkg-copy"
        relocated.parent.mkdir()
        shutil.copytree(self.pkg, relocated)
        second = self.build(scope, package_root=relocated)
        self.assertEqual(first["baseline"]["baseline_id"], second["baseline"]["baseline_id"])
        self.assertNotEqual(
            first["baseline"]["source"]["path"], second["baseline"]["source"]["path"]
        )

        template = self.pkg / "templates" / "agents" / "AGENTS.global.md"
        os.utime(template, (1_800_000_000, 1_800_000_000))
        third = self.build(scope)
        self.assertEqual(first["baseline"]["baseline_id"], third["baseline"]["baseline_id"])

    def test_baseline_id_tracks_payload_source_and_constraint_bytes(self):
        scope = self.scope(skills_roots=[str(self.skills_root)])
        original = self.build(scope)["baseline"]["baseline_id"]

        def rebuilt_id() -> str:
            return self.build(scope)["baseline"]["baseline_id"]

        template = self.pkg / "templates" / "agents" / "AGENTS.global.md"
        template.write_bytes(NEW_AGENTS + b"x")
        self.assertNotEqual(original, rebuilt_id())
        template.write_bytes(NEW_AGENTS)
        self.assertEqual(original, rebuilt_id())

        runtime = self.pkg / "scripts" / "onboard.py"
        original_runtime = runtime.read_bytes()
        runtime.write_bytes(original_runtime + b"# drift\n")
        self.assertNotEqual(original, rebuilt_id())
        runtime.write_bytes(original_runtime)

        requirements = self.pkg / "requirements.txt"
        original_requirements = requirements.read_bytes()
        requirements.write_bytes(original_requirements + b"tomlkit<1\n")
        self.assertNotEqual(original, rebuilt_id())
        requirements.write_bytes(original_requirements)
        self.assertEqual(original, rebuilt_id())

    def test_baseline_shape_and_engine_source_reference(self):
        document = self.build(self.scope(skills_roots=[str(self.skills_root)]))
        baseline = document["baseline"]
        self.assertEqual(baseline["schema_version"], 1)
        self.assertRegex(baseline["baseline_id"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(baseline["source"]["path"], str(self.pkg))
        self.assertEqual(baseline["source"]["state"]["type"], "directory")
        self.assertEqual(
            baseline["source"]["state"],
            inventory.payload_directory_state(self.pkg),
        )
        catalog_ids = [entry["id"] for entry in baseline["catalog"]["entries"]]
        self.assertIn("agent:codex-global", catalog_ids)
        self.assertEqual(set(baseline["stable"]["skills"]), set(EXTERNAL))
        upstream = baseline["stable"]["repositories"]["upstream"]
        self.assertEqual(upstream["revision"], UPSTREAM_REVISION)
        self.assertEqual(upstream["license"], "MIT")
        self.assertEqual(
            [entry["path"] for entry in upstream["license_files"]],
            ["licenses/upstream-LICENSE"],
        )
        self.assertIn("scripts/onboard.py", baseline["runtime"]["implementation"])

    def test_resource_references_are_engine_consumable(self):
        agents_target = self.base / "AGENTS.md"
        document = self.build(
            self.scope(
                skills_roots=[str(self.skills_root)],
                agents_targets=[str(agents_target)],
            )
        )
        for resource in document["resources"]:
            source = Path(resource["source"]["path"])
            self.assertTrue(
                source == self.pkg or str(source).startswith(str(self.pkg) + os.sep)
            )
            if resource["kind"] == "skill":
                self.assertEqual(
                    resource["source"]["state"], inventory.payload_directory_state(source)
                )
            else:
                self.assertEqual(
                    resource["source"]["state"], inventory.payload_file_state(source)
                )
            self.assertNotEqual(resource["desired"]["type"], "absent")
            self.assertTrue(resource["id"].endswith(f"@{resource['target']}"))


class MissingCurrentDriftTests(InventoryTests):
    def test_missing_payload_is_install_without_writes(self):
        """U01: an empty selected root inventories everything, writes nothing."""
        before = {str(path.relative_to(self.pkg)) for path in self.pkg.rglob("*")}
        document = self.build(self.scope(skills_roots=[str(self.skills_root)]))
        resources = by_name(document)
        self.assertEqual(set(resources), skill_names(self.pkg))
        for name, resource in resources.items():
            self.assertEqual(resource["classification"], "missing", name)
            self.assertEqual(resource["decision"], "install", name)
            self.assertEqual(resource["before"], {"type": "absent", "checksum": None}, name)
            self.assertEqual(resource["details"], {}, name)
        self.assertFalse(self.skills_root.exists())
        after = {str(path.relative_to(self.pkg)) for path in self.pkg.rglob("*")}
        self.assertEqual(before, after)

    def test_exact_install_is_current_and_keep(self):
        install_all(self.pkg, self.skills_root)
        document = self.build(self.scope(skills_roots=[str(self.skills_root)]))
        for name, resource in by_name(document).items():
            self.assertEqual(resource["classification"], "current", name)
            self.assertEqual(resource["decision"], "keep", name)
            self.assertEqual(resource["before"], resource["desired"], name)
            self.assertEqual(resource["details"], {}, name)

    def test_declared_caches_do_not_change_identity(self):
        """Existing exclusion semantics: generated caches never cause drift."""
        install_all(self.pkg, self.skills_root)
        cache_dir = self.skills_root / "alpha-skill" / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "cached.pyc").write_bytes(b"\x00\x01")
        (self.skills_root / "alpha-skill" / "loose.pyc").write_bytes(b"\x02")
        document = self.build(self.scope(skills_roots=[str(self.skills_root)]))
        resource = by_name(document)["alpha-skill"]
        self.assertEqual(resource["classification"], "current")
        self.assertEqual(resource["decision"], "keep")

    def test_content_valid_older_shell_is_drift_not_aligned(self):
        """U02: a content-valid older shell lists full differences and waits."""
        install_all(self.pkg, self.skills_root)
        target = self.skills_root / "alpha-skill"
        (target / "SKILL.md").write_text(
            skill_md("alpha-skill", "older managed body"), encoding="utf-8"
        )
        extra = target / "scripts"
        extra.mkdir()
        (extra / "custom.sh").write_text("#!/bin/sh\necho custom\n", encoding="utf-8")
        document = self.build(self.scope(skills_roots=[str(self.skills_root)]))
        resource = by_name(document)["alpha-skill"]
        self.assertEqual(resource["classification"], "unknown-drift")
        self.assertEqual(resource["decision"], "blocked")
        self.assertTrue(resource["details"]["decision_required"])
        changed = {entry["path"]: entry for entry in resource["details"]["changed"]}
        self.assertIn("SKILL.md", changed)
        self.assertEqual(
            changed["SKILL.md"]["before_sha256"],
            hashlib.sha256(skill_md("alpha-skill", "older managed body").encode()).hexdigest(),
        )
        self.assertEqual(
            changed["SKILL.md"]["desired_sha256"],
            hashlib.sha256(skill_md("alpha-skill").encode()).hexdigest(),
        )
        self.assertEqual(
            [entry["path"] for entry in resource["details"]["extra"]],
            ["scripts/custom.sh"],
        )

    def test_missing_payload_files_are_listed(self):
        install_all(self.pkg, self.skills_root)
        (self.skills_root / "beta-skill" / "references" / "notes.md").unlink()
        document = self.build(self.scope(skills_roots=[str(self.skills_root)]))
        resource = by_name(document)["beta-skill"]
        self.assertEqual(resource["classification"], "unknown-drift")
        self.assertEqual(resource["details"]["missing"], ["references/notes.md"])

    def test_drift_decisions_are_explicit(self):
        install_all(self.pkg, self.skills_root)
        target = self.skills_root / "alpha-skill"
        (target / "SKILL.md").write_text(skill_md("alpha-skill", "custom"), encoding="utf-8")

        replace = self.build(
            self.scope(
                skills_roots=[str(self.skills_root)],
                decisions={str(target): "replace"},
            )
        )
        self.assertEqual(by_name(replace)["alpha-skill"]["decision"], "replace")

        preserve = self.build(
            self.scope(
                skills_roots=[str(self.skills_root)],
                decisions={str(target): "preserve"},
            )
        )
        preserved = by_name(preserve)["alpha-skill"]
        self.assertEqual(preserved["decision"], "preserve")
        self.assertEqual(preserved["classification"], "unknown-drift")

    def test_missing_preserve_and_current_idempotence(self):
        install_all(self.pkg, self.skills_root)
        missing_target = self.skills_root / "alpha-skill"
        shutil.rmtree(missing_target)
        current_target = self.skills_root / "beta-skill"
        document = self.build(
            self.scope(
                skills_roots=[str(self.skills_root)],
                decisions={
                    str(missing_target): "preserve",
                    str(current_target): "replace",
                },
            )
        )
        resources = by_name(document)
        self.assertEqual(resources["alpha-skill"]["decision"], "preserve")
        self.assertEqual(resources["beta-skill"]["decision"], "keep")


class KnownOldAgentsTests(InventoryTests):
    def test_pinned_legacy_agents_is_known_old_with_evidence(self):
        agents_target = self.base / "AGENTS.md"
        agents_target.write_bytes(OLD_AGENTS)
        document = self.build(self.scope(agents_targets=[str(agents_target)]))
        (resource,) = document["resources"]
        self.assertEqual(resource["kind"], "agents")
        self.assertEqual(resource["classification"], "known-old")
        self.assertEqual(resource["decision"], "blocked")
        self.assertEqual(
            resource["details"]["evidence"],
            {
                "kind": "legacy-ownership-pin",
                "asset": "assets/migration-legacy-ownership.json",
                "field": "global_agents_sha256",
            },
        )

    def test_known_old_follows_explicit_decision(self):
        agents_target = self.base / "AGENTS.md"
        agents_target.write_bytes(OLD_AGENTS)
        for value in ("replace", "preserve"):
            document = self.build(
                self.scope(
                    agents_targets=[str(agents_target)],
                    decisions={str(agents_target): value},
                )
            )
            (resource,) = document["resources"]
            self.assertEqual(resource["classification"], "known-old")
            self.assertEqual(resource["decision"], value)

    def test_mixed_unknown_agents_requires_a_decision(self):
        """Unknown mixed content is never silently aligned or overwritten."""
        agents_target = self.base / "AGENTS.md"
        agents_target.write_bytes(b"# user mixed content\nunrelated rules\n")
        document = self.build(self.scope(agents_targets=[str(agents_target)]))
        (resource,) = document["resources"]
        self.assertEqual(resource["classification"], "unknown-drift")
        self.assertEqual(resource["decision"], "blocked")
        self.assertTrue(resource["details"]["decision_required"])

        replaced = self.build(
            self.scope(
                agents_targets=[str(agents_target)],
                decisions={str(agents_target): "replace"},
            )
        )
        self.assertEqual(replaced["resources"][0]["decision"], "replace")

    def test_current_agents_is_keep(self):
        agents_target = self.base / "AGENTS.md"
        agents_target.write_bytes(NEW_AGENTS)
        document = self.build(self.scope(agents_targets=[str(agents_target)]))
        (resource,) = document["resources"]
        self.assertEqual(resource["classification"], "current")
        self.assertEqual(resource["decision"], "keep")


class SourceIntegrityTests(InventoryTests):
    def test_stable_payload_tampering_fails(self):
        skill_md_path = (
            self.pkg
            / "assets"
            / "external-skills"
            / "stable"
            / "skills"
            / "gamma-skill"
            / "SKILL.md"
        )
        skill_md_path.write_text(skill_md("gamma-skill", "tampered"), encoding="utf-8")
        self.assert_code("source-untrusted", self.scope(skills_roots=[str(self.skills_root)]))

    def test_stable_manifest_pin_tampering_fails(self):
        manifest_path = (
            self.pkg / "assets" / "external-skills" / "stable" / "MANIFEST.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["skills"]["gamma-skill"]["treeSha256"] = "0" * 64
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        self.assert_code("source-untrusted", self.scope(skills_roots=[str(self.skills_root)]))

    def test_stable_provenance_must_match_catalog(self):
        manifest_path = (
            self.pkg / "assets" / "external-skills" / "stable" / "MANIFEST.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["repositories"]["upstream"]["url"] = "https://github.com/example/other.git"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        self.assert_code("source-untrusted", self.scope(skills_roots=[str(self.skills_root)]))

    def test_missing_license_file_fails(self):
        os.remove(
            self.pkg / "assets" / "external-skills" / "stable" / "licenses" / "upstream-LICENSE"
        )
        self.assert_code("source-untrusted", self.scope(skills_roots=[str(self.skills_root)]))

    def test_bundled_source_frontmatter_tampering_fails(self):
        target = self.pkg / "templates" / "skills" / "alpha-skill" / "SKILL.md"
        target.write_text(skill_md("renamed-skill"), encoding="utf-8")
        self.assert_code("source-untrusted", self.scope(skills_roots=[str(self.skills_root)]))

    def test_link_inside_stable_payload_fails(self):
        (self.pkg / "assets" / "external-skills" / "stable" / "skills" / "gamma-skill" / "link.md").symlink_to(
            "SKILL.md"
        )
        self.assert_code("unsafe-path", self.scope(skills_roots=[str(self.skills_root)]))


class IdentityConflictTests(InventoryTests):
    def prepare_alpha(self) -> Path:
        self.skills_root.mkdir()
        target = self.skills_root / "alpha-skill"
        target.mkdir()
        return target

    def test_frontmatter_mismatch_is_identity_conflict(self):
        target = self.prepare_alpha()
        (target / "SKILL.md").write_text(skill_md("someone-else"), encoding="utf-8")
        document = self.build(self.scope(skills_roots=[str(self.skills_root)]))
        resource = by_name(document)["alpha-skill"]
        self.assertEqual(resource["classification"], "identity-conflict")
        self.assertEqual(resource["decision"], "blocked")
        self.assertEqual(
            resource["details"]["identity"],
            {
                "kind": "frontmatter-mismatch",
                "expected": "alpha-skill",
                "actual_sha256": hashlib.sha256(b"someone-else").hexdigest(),
            },
        )

    def test_missing_skill_md_is_identity_conflict(self):
        target = self.prepare_alpha()
        (target / "notes.txt").write_text("foreign\n", encoding="utf-8")
        document = self.build(self.scope(skills_roots=[str(self.skills_root)]))
        resource = by_name(document)["alpha-skill"]
        self.assertEqual(resource["classification"], "identity-conflict")
        self.assertEqual(resource["details"]["identity"]["kind"], "skill-md-missing")

    def test_unknown_identity_cannot_be_overwritten_by_decision(self):
        target = self.prepare_alpha()
        (target / "SKILL.md").write_text(skill_md("someone-else"), encoding="utf-8")
        self.assert_code(
            "decision-conflict",
            self.scope(
                skills_roots=[str(self.skills_root)],
                decisions={str(target): "replace"},
            ),
        )

    def test_type_conflict_preserve_is_allowed_replace_is_not(self):
        self.skills_root.mkdir()
        target = self.skills_root / "alpha-skill"
        target.write_text("a file where a directory is expected\n", encoding="utf-8")
        document = self.build(
            self.scope(
                skills_roots=[str(self.skills_root)],
                decisions={str(target): "preserve"},
            )
        )
        resource = by_name(document)["alpha-skill"]
        self.assertEqual(resource["classification"], "identity-conflict")
        self.assertEqual(resource["details"]["identity"]["kind"], "type-conflict")
        self.assertEqual(resource["decision"], "preserve")
        self.assert_code(
            "decision-conflict",
            self.scope(
                skills_roots=[str(self.skills_root)],
                decisions={str(target): "replace"},
            ),
        )

    def test_agents_directory_target_is_type_conflict(self):
        agents_target = self.base / "AGENTS.md"
        agents_target.mkdir()
        document = self.build(self.scope(agents_targets=[str(agents_target)]))
        (resource,) = document["resources"]
        self.assertEqual(resource["classification"], "identity-conflict")
        self.assertEqual(resource["details"]["identity"]["kind"], "type-conflict")


class ScopeValidationTests(InventoryTests):
    def test_unknown_keys_and_wrong_types_are_rejected(self):
        root = str(self.skills_root)
        self.assert_code("invalid-config", self.scope(skills_roots=[root], bogus=True))
        self.assert_code("invalid-config", self.scope(schema_version=2, skills_roots=[root]))
        self.assert_code("invalid-config", self.scope(skills_roots=root))
        self.assert_code("invalid-config", self.scope(skills_roots=[root], decisions=[]))
        self.assert_code(
            "invalid-config", self.scope(skills_roots=[root], decisions={root: "overwrite"})
        )

    def test_empty_selection_is_rejected(self):
        self.assert_code("invalid-config", self.scope())
        self.assert_code("invalid-config", self.scope(skills_roots=[], hosts=[]))

    def test_relative_and_overlapping_roots_are_rejected(self):
        self.assert_code("unsafe-path", self.scope(skills_roots=["relative/skills"]))
        self.assert_code(
            "unsafe-path",
            self.scope(skills_roots=[str(self.base), str(self.skills_root)]),
        )

    def test_duplicate_roots_are_processed_once(self):
        single = self.build(self.scope(skills_roots=[str(self.skills_root)]))
        doubled = self.build(
            self.scope(skills_roots=[str(self.skills_root), str(self.skills_root)])
        )
        self.assertEqual(single["resources"], doubled["resources"])
        self.assertEqual(len(single["domains"]), len(doubled["domains"]))

    def test_agents_target_cannot_overlap_a_skills_root(self):
        self.assert_code(
            "unsafe-path",
            self.scope(
                skills_roots=[str(self.skills_root)],
                agents_targets=[str(self.skills_root / "AGENTS.md")],
            ),
        )

    def test_decisions_must_target_selected_resources(self):
        self.assert_code(
            "decision-conflict",
            self.scope(
                skills_roots=[str(self.skills_root)],
                decisions={str(self.base / "nowhere"): "replace"},
            ),
        )

    def host_entry(self, **overrides) -> dict:
        entry = {
            "id": "orca",
            "platform": "codex",
            "config_home": str(self.base / "home" / ".codex"),
            "config": str(self.base / "home" / ".codex" / "config.toml"),
            "skills_roots": [str(self.skills_root)],
            "runtime": {"python": str(self.base / "py"), "node": None, "cli": None},
            "project_roots": [str(self.base)],
        }
        entry.update(overrides)
        return entry

    def test_single_host_root_derives_installed_onboard(self):
        document = self.build(self.scope(
            skills_roots=[str(self.skills_root)], hosts=[self.host_entry()]
        ))
        (host_domain,) = [row for row in document["domains"] if row["kind"] == "host"]
        self.assertEqual(host_domain["onboard_root"], str(self.skills_root / SELF_NAME))

    def test_multiple_host_roots_need_explicit_installed_onboard(self):
        second = self.base / "second-skills"
        roots = [str(self.skills_root), str(second)]
        host = self.host_entry(skills_roots=roots)
        self.assert_code("scope-conflict", self.scope(skills_roots=roots, hosts=[host]))
        host["onboard_root"] = str(second / SELF_NAME)
        document = self.build(self.scope(skills_roots=roots, hosts=[host]))
        (host_domain,) = [row for row in document["domains"] if row["kind"] == "host"]
        self.assertEqual(host_domain["onboard_root"], str(second / SELF_NAME))
        host["onboard_root"] = str(self.pkg)
        self.assert_code("unsafe-path", self.scope(skills_roots=roots, hosts=[host]))

    def test_host_only_binding_is_explicit_but_unsupported_platform_needs_none(self):
        host = self.host_entry(skills_roots=[])
        self.assert_code("scope-conflict", self.scope(hosts=[host]))
        host["onboard_root"] = str(self.pkg)
        document = self.build(self.scope(hosts=[host]))
        (host_domain,) = document["domains"]
        self.assertEqual(host_domain["onboard_root"], str(self.pkg))
        host["onboard_root"] = "relative/onboard"
        self.assert_code("unsafe-path", self.scope(hosts=[host]))
        del host["onboard_root"]
        host["platform"] = "claude"
        document = self.build(self.scope(hosts=[host]))
        self.assertIsNone(document["domains"][0]["onboard_root"])

    def test_host_validation(self):
        root = str(self.skills_root)
        hosts = [self.host_entry(), self.host_entry(id="dup")]
        hosts.append(hosts[0].copy())
        self.assert_code("invalid-config", self.scope(skills_roots=[root], hosts=hosts))
        self.assert_code(
            "invalid-config",
            self.scope(skills_roots=[root], hosts=[self.host_entry(skills_roots=[str(self.base)])]),
        )
        self.assert_code(
            "unsafe-path",
            self.scope(
                skills_roots=[root],
                hosts=[self.host_entry(config=str(self.base / "elsewhere.toml"))],
            ),
        )
        self.assert_code(
            "invalid-config",
            self.scope(
                skills_roots=[root], hosts=[self.host_entry(executable="relative/codex")]
            ),
        )
        self.assert_code(
            "invalid-config",
            self.scope(skills_roots=[root], hosts=[self.host_entry(extra="nope")]),
        )

    def test_host_executable_and_domains_echo(self):
        host = self.host_entry(executable=str(self.base / "bin" / "codex"))
        document = self.build(self.scope(skills_roots=[str(self.skills_root)], hosts=[host]))
        (host_domain,) = [d for d in document["domains"] if d["kind"] == "host"]
        self.assertEqual(host_domain["id"], "host:orca")
        self.assertEqual(host_domain["executable"], str(self.base / "bin" / "codex"))
        self.assertEqual(host_domain["skills_roots"], [str(self.skills_root)])

    def test_shell_profile_validation_and_domain(self):
        profile = {
            "path": str(self.base / ".zshrc"),
            "shell": "zsh",
            "bin": str(self.base / "bin"),
        }
        document = self.build(self.scope(shell_profiles=[profile]))
        (domain,) = document["domains"]
        self.assertEqual(domain["kind"], "shell")
        self.assertEqual(domain["shell"], "zsh")
        self.assert_code(
            "invalid-config",
            self.scope(shell_profiles=[{**profile, "shell": "fish"}]),
        )
        self.assert_code(
            "invalid-config",
            self.scope(shell_profiles=[{**profile, "extra": 1}]),
        )

    def test_decisions_pass_through_for_host_and_shell_targets(self):
        host = self.host_entry()
        profile = {"path": str(self.base / ".zshrc"), "shell": "zsh", "bin": str(self.base / "bin")}
        document = self.build(
            self.scope(
                skills_roots=[str(self.skills_root)],
                hosts=[host],
                shell_profiles=[profile],
                decisions={
                    str(self.base / "home" / ".codex" / "config.toml"): "preserve",
                    str(self.base / ".zshrc"): "replace",
                },
            )
        )
        self.assertTrue(document["resources"])


class SymlinkSafetyTests(InventoryTests):
    def test_symlinked_root_component_is_rejected(self):
        real = self.base / "real"
        real.mkdir()
        link = self.base / "link"
        link.symlink_to(real)
        self.assert_code(
            "unsafe-path", self.scope(skills_roots=[str(link / "skills")])
        )

    def test_symlinked_skill_target_is_rejected(self):
        install_all(self.pkg, self.skills_root)
        target = self.skills_root / "alpha-skill"
        shutil.rmtree(target)
        target.symlink_to(self.pkg / "templates" / "skills" / "alpha-skill")
        self.assert_code("unsafe-path", self.scope(skills_roots=[str(self.skills_root)]))

    def test_link_inside_target_tree_is_rejected(self):
        install_all(self.pkg, self.skills_root)
        (self.skills_root / "alpha-skill" / "link.md").symlink_to("SKILL.md")
        self.assert_code("unsafe-path", self.scope(skills_roots=[str(self.skills_root)]))

    def test_space_and_unicode_paths_are_safe(self):
        root = self.base / "空间 skills"
        document = self.build(self.scope(skills_roots=[str(root)]))
        self.assertTrue(document["resources"])
        self.assertTrue(
            all(resource["target"].startswith(str(root)) for resource in document["resources"])
        )


class DomainTests(InventoryTests):
    def test_shared_root_is_deduplicated_and_attributed(self):
        host = {
            "id": "orca",
            "platform": "codex",
            "config_home": str(self.base / "home"),
            "config": str(self.base / "home" / "config.toml"),
            "skills_roots": [str(self.skills_root)],
            "runtime": {"python": None, "node": None, "cli": None},
            "project_roots": [],
        }
        document = self.build(
            self.scope(skills_roots=[str(self.skills_root)], hosts=[host])
        )
        skill_domains = [d for d in document["domains"] if d["kind"] == "skills"]
        self.assertEqual(len(skill_domains), 1)
        self.assertEqual(
            skill_domains[0]["selected_by"], ["skills_roots", "host:orca"]
        )
        self.assertEqual(
            len(skill_domains[0]["resources"]), len(skill_names(self.pkg))
        )

    def test_duplicate_onboard_copies_are_explained(self):
        second_root = self.base / "second"
        document = self.build(
            self.scope(skills_roots=[str(self.skills_root), str(second_root)])
        )
        domains = {
            domain["path"]: domain
            for domain in document["domains"]
            if domain["kind"] == "skills"
        }
        expected = sorted(
            [str(self.skills_root / SELF_NAME), str(second_root / SELF_NAME)]
        )
        for path in (str(self.skills_root), str(second_root)):
            onboard_copy = domains[path]["onboard_copy"]
            self.assertIsNotNone(onboard_copy)
            self.assertEqual(onboard_copy["duplicates"], expected)
            self.assertFalse(onboard_copy["is_source"])

    def test_source_package_selected_is_same_location_current(self):
        installed_pkg = self.base / SELF_NAME
        shutil.copytree(self.pkg, installed_pkg)
        document = self.build(
            self.scope(skills_roots=[str(self.base)]), package_root=installed_pkg
        )
        resources = by_name(document)
        onboard_resource = resources[SELF_NAME]
        self.assertEqual(onboard_resource["classification"], "current")
        self.assertEqual(onboard_resource["decision"], "keep")
        (domain,) = [d for d in document["domains"] if d["kind"] == "skills"]
        self.assertTrue(domain["onboard_copy"]["is_source"])


class DeterminismPrivacyTests(InventoryTests):
    def test_byte_identical_repeated_inventory(self):
        install_all(self.pkg, self.skills_root)
        target = self.skills_root / "alpha-skill"
        (target / "SKILL.md").write_text(skill_md("alpha-skill", "custom"), encoding="utf-8")
        scope = self.scope(skills_roots=[str(self.skills_root)])
        first = self.build(scope)
        second = self.build(scope)
        self.assertEqual(first, second)
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
        targets = [resource["target"] for resource in first["resources"]]
        self.assertEqual(targets, sorted(targets))
        domain_ids = [domain["id"] for domain in first["domains"]]
        self.assertEqual(domain_ids, sorted(domain_ids))

    def test_output_never_carries_file_content(self):
        """U15: differences report relative names and digests, never bytes."""
        install_all(self.pkg, self.skills_root)
        marker = "SECRET-MARKER-7391"
        target = self.skills_root / "alpha-skill"
        (target / "SKILL.md").write_text(
            skill_md("alpha-skill", marker), encoding="utf-8"
        )
        (target / "extra.txt").write_text(marker, encoding="utf-8")
        document = self.build(self.scope(skills_roots=[str(self.skills_root)]))
        self.assertNotIn(marker, json.dumps(document))
        # The frontmatter name is user-controlled file content too.
        (target / "SKILL.md").write_text(skill_md(marker), encoding="utf-8")
        mismatched = self.build(self.scope(skills_roots=[str(self.skills_root)]))
        self.assertNotIn(marker, json.dumps(mismatched))
        self.assertEqual(
            by_name(mismatched)["alpha-skill"]["details"]["identity"]["actual_sha256"],
            hashlib.sha256(marker.encode("utf-8")).hexdigest(),
        )


class RealPackageCoverageTests(unittest.TestCase):
    """The shipped package inventories every catalog Skill and stable pin."""

    def test_real_catalog_coverage_and_stable_pins(self):
        with tempfile.TemporaryDirectory(prefix="sbtd-upgrade-inventory-real-") as temporary:
            root = Path(temporary).resolve() / "skills"
            document = inventory.build_inventory(
                {"schema_version": 1, "skills_roots": [str(root)]}
            )
        real_pkg = SCRIPTS.parent
        names = skill_names(real_pkg)
        resources = by_name(document)
        self.assertEqual(set(resources), names)
        for resource in resources.values():
            self.assertEqual(resource["classification"], "missing")
            self.assertEqual(resource["decision"], "install")
        manifest = json.loads(
            (real_pkg / "assets" / "external-skills" / "stable" / "MANIFEST.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(set(document["baseline"]["stable"]["skills"]), set(manifest["skills"]))
        for name, pin in manifest["skills"].items():
            self.assertEqual(
                resources[name]["desired"],
                {"type": "directory", "checksum": pin["treeSha256"]},
                name,
            )
        self.assertIn(
            "scripts/sbtd_upgrade_inventory.py",
            document["baseline"]["runtime"]["implementation"],
        )


class ReviewRegressionTests(InventoryTests):
    def manifest_path(self) -> Path:
        return self.pkg / "assets/external-skills/stable/MANIFEST.json"

    def test_agents_ancestor_of_skills_root_is_rejected(self):
        agents = self.base / "AGENTS.md"
        self.assert_code(
            "unsafe-path",
            self.scope(agents_targets=[str(agents)], skills_roots=[str(agents / "skills")]),
        )

    def test_package_boolean_schema_versions_are_not_integer_versions(self):
        paths = (
            (self.pkg / "catalog.json", "schemaVersion"),
            (self.manifest_path(), "schemaVersion"),
            (self.pkg / "assets/migration-legacy-ownership.json", "schema_version"),
        )
        for path, key in paths:
            with self.subTest(document=path.name):
                original = path.read_bytes()
                document = json.loads(original)
                document[key] = True
                path.write_text(json.dumps(document), encoding="utf-8")
                self.assert_code("source-untrusted", self.scope(skills_roots=[str(self.skills_root)]))
                path.write_bytes(original)

    def test_self_catalog_source_must_be_the_complete_package(self):
        shell = self.pkg / "templates/skills/minimal-self"
        shell.mkdir(parents=True)
        (shell / "SKILL.md").write_text(skill_md(SELF_NAME), encoding="utf-8")
        path = self.pkg / "catalog.json"
        catalog = json.loads(path.read_bytes())
        for entry in catalog["entries"]:
            if entry["id"] == f"skill:{SELF_NAME}":
                entry["source"] = "templates/skills/minimal-self"
        path.write_text(json.dumps(catalog), encoding="utf-8")
        self.assert_code("source-untrusted", self.scope(skills_roots=[str(self.skills_root)]))

    def test_existing_whitespace_delimiters_allow_explicit_content_upgrade(self):
        install_all(self.pkg, self.skills_root)
        target = self.skills_root / "alpha-skill"
        (target / "SKILL.md").write_bytes(b"--- \t\nname: alpha-skill\n--- \t\nold body\n")
        document = self.build(self.scope(
            skills_roots=[str(self.skills_root)],
            decisions={str(target): "replace"},
        ))
        resource = by_name(document)["alpha-skill"]
        self.assertEqual(resource["classification"], "unknown-drift")
        self.assertEqual(resource["decision"], "replace")

    def test_ambiguous_oversized_or_unterminated_identity_is_not_owned(self):
        install_all(self.pkg, self.skills_root)
        target = self.skills_root / "alpha-skill" / "SKILL.md"
        secret = "SECRET-NAME-IN-DUPLICATE-HEADER"
        headers = (
            f"---\nname: alpha-skill\nname: {secret}\n---\n".encode(),
            b"---\nname: alpha-skill\n" + b"x" * (64 * 1024) + b"\n---\n",
            b"---\nname: alpha-skill\n",
        )
        for raw in headers:
            with self.subTest(header_length=len(raw)):
                target.write_bytes(raw)
                document = self.build(self.scope(skills_roots=[str(self.skills_root)]))
                resource = by_name(document)["alpha-skill"]
                self.assertEqual(resource["classification"], "identity-conflict")
                self.assertIsNone(resource["details"]["identity"]["actual_sha256"])
                self.assertNotIn(secret, json.dumps(document))

    def test_legitimate_large_markdown_body_does_not_hide_valid_identity(self):
        install_all(self.pkg, self.skills_root)
        target = self.skills_root / "alpha-skill" / "SKILL.md"
        with target.open("wb") as handle:
            handle.write(skill_md("alpha-skill").encode())
            for _ in range(4):
                handle.write(b"x" * (1024 * 1024))
        original_open = inventory.open_regular_file
        header_bytes = []

        @contextlib.contextmanager
        def bounded_open(path, label):
            with original_open(path, label) as handle:
                if Path(path) != target:
                    yield handle
                    return

                class BoundedReader:
                    def fileno(self):
                        return handle.fileno()

                    def read(self, size=-1):
                        self_test.assertGreater(size, 0, "whole-body read is forbidden")
                        return handle.read(size)

                    def readline(self, size=-1):
                        self_test.assertGreater(size, 0)
                        self_test.assertLessEqual(size, 64 * 1024 + 1)
                        line = handle.readline(size)
                        header_bytes.append(len(line))
                        return line

                yield BoundedReader()

        self_test = self
        with mock.patch.object(inventory, "open_regular_file", side_effect=bounded_open):
            document = self.build(self.scope(skills_roots=[str(self.skills_root)]))
        self.assertLess(sum(header_bytes), 64 * 1024)
        resource = by_name(document)["alpha-skill"]
        self.assertEqual(resource["classification"], "unknown-drift")
        self.assertEqual(resource["decision"], "blocked")

    def test_explicit_null_collections_and_boolean_schema_are_rejected(self):
        for key in ("skills_roots", "agents_targets", "hosts", "shell_profiles", "decisions"):
            with self.subTest(key=key):
                scope = self.scope(skills_roots=[str(self.skills_root)])
                scope[key] = None
                self.assert_code("invalid-config", scope)
        self.assert_code(
            "invalid-config",
            self.scope(schema_version=True, skills_roots=[str(self.skills_root)]),
        )

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires a native FIFO")
    def test_special_skill_target_is_rejected_as_unsafe(self):
        self.skills_root.mkdir()
        os.mkfifo(self.skills_root / "alpha-skill")
        self.assert_code("unsafe-path", self.scope(skills_roots=[str(self.skills_root)]))

    def test_large_extra_file_has_a_streamed_difference_digest(self):
        install_all(self.pkg, self.skills_root)
        asset = self.skills_root / "alpha-skill" / "extra.bin"
        digest = hashlib.sha256()
        block = b"x" * (1024 * 1024)
        with asset.open("wb") as handle:
            for _ in range(3):
                handle.write(block)
                digest.update(block)
        document = self.build(self.scope(skills_roots=[str(self.skills_root)]))
        self.assertEqual(
            by_name(document)["alpha-skill"]["details"]["extra"],
            [{"path": "extra.bin", "sha256": digest.hexdigest()}],
        )

    def test_unsafe_entries_inside_excluded_caches_are_rejected(self):
        install_all(self.pkg, self.skills_root)
        for name in ("__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"):
            with self.subTest(cache=name):
                nested = self.skills_root / "alpha-skill" / name / "nested"
                nested.mkdir(parents=True)
                link = nested / "unsafe.pyc"
                link.symlink_to(self.pkg / "SKILL.md")
                self.assert_code("unsafe-path", self.scope(skills_roots=[str(self.skills_root)]))
                link.unlink()

    def test_digest_order_is_independent_of_platform_normcase(self):
        tree = self.base / "case-order"
        tree.mkdir()
        (tree / "Z.md").write_bytes(b"upper")
        (tree / "a.md").write_bytes(b"lower")
        expected = hashlib.sha256()
        for name, raw in (("Z.md", b"upper"), ("a.md", b"lower")):
            encoded = name.encode()
            expected.update(len(encoded).to_bytes(8, "big"))
            expected.update(encoded)
            expected.update(len(raw).to_bytes(8, "big"))
            expected.update(raw)
        with mock.patch.object(inventory.os.path, "normcase", side_effect=str.lower):
            state = inventory.payload_directory_state(tree)
        self.assertEqual(state["checksum"], expected.hexdigest())

    def test_producer_and_scanner_share_platform_independent_order(self):
        """Stable pins are minted by onboard.external_tree_sha256: it must
        order exactly like the inventory scanner on every OS. The top-level
        uppercase file vs lowercase subdirectory shape is where Windows
        normcase folding flips Path-object ordering (the gamma-skill
        regression); the explicit iteration below pins plain POSIX order."""
        tree = self.base / "gamma-order"
        (tree / "scripts").mkdir(parents=True)
        (tree / "SKILL.md").write_bytes(b"upper top\n")
        (tree / "scripts" / "tool.sh").write_bytes(b"lower sub\n")
        expected = hashlib.sha256()
        for name, raw in (("SKILL.md", b"upper top\n"), ("scripts/tool.sh", b"lower sub\n")):
            encoded = name.encode()
            expected.update(len(encoded).to_bytes(8, "big"))
            expected.update(encoded)
            expected.update(len(raw).to_bytes(8, "big"))
            expected.update(raw)
        self.assertEqual(
            reference_onboard().external_tree_sha256(tree), expected.hexdigest()
        )
        self.assertEqual(
            inventory.payload_directory_state(tree)["checksum"], expected.hexdigest()
        )

    def test_matching_invalid_catalog_and_manifest_urls_are_untrusted(self):
        catalog_path = self.pkg / "catalog.json"
        original_catalog = catalog_path.read_bytes()
        original_manifest = self.manifest_path().read_bytes()
        for invalid in ("https://", "https://bad host/path", "https://host/path?secret=value"):
            with self.subTest(url=invalid):
                catalog = json.loads(original_catalog)
                manifest = json.loads(original_manifest)
                for entry in catalog["entries"]:
                    if entry["kind"] == "external-skill":
                        entry["source"]["repo"] = invalid
                manifest["repositories"]["upstream"]["url"] = invalid
                catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
                self.manifest_path().write_text(json.dumps(manifest), encoding="utf-8")
                self.assert_code("source-untrusted", self.scope(skills_roots=[str(self.skills_root)]))

    def test_unhashable_manifest_repository_ids_are_contract_errors(self):
        original = self.manifest_path().read_bytes()
        for invalid in ([], {}):
            with self.subTest(repository=invalid):
                manifest = json.loads(original)
                manifest["skills"]["gamma-skill"]["repository"] = invalid
                self.manifest_path().write_text(json.dumps(manifest), encoding="utf-8")
                self.assert_code("source-untrusted", self.scope(skills_roots=[str(self.skills_root)]))

    def test_missing_self_or_global_agents_catalog_entries_are_untrusted(self):
        catalog_path = self.pkg / "catalog.json"
        original = catalog_path.read_bytes()
        for entry_id in ("skill:sbtd-workflow-onboard", "agent:codex-global"):
            with self.subTest(entry=entry_id):
                catalog = json.loads(original)
                catalog["entries"] = [entry for entry in catalog["entries"] if entry["id"] != entry_id]
                catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
                self.assert_code("source-untrusted", self.scope(skills_roots=[str(self.skills_root)]))

    def test_nested_absent_agents_targets_are_rejected(self):
        target = self.base / "AGENTS.md"
        self.assert_code(
            "unsafe-path",
            self.scope(agents_targets=[str(target), str(target / "nested")]),
        )

    def test_conflicting_duplicate_profiles_are_rejected_identical_are_deduped(self):
        profile = {"path": str(self.base / ".zshrc"), "shell": "zsh", "bin": str(self.base / "bin")}
        for change in ({"shell": "powershell"}, {"bin": str(self.base / "other-bin")}, {"shell": []}):
            with self.subTest(change=change):
                self.assert_code(
                    "invalid-config",
                    self.scope(shell_profiles=[profile, {**profile, **change}]),
                )
        document = self.build(self.scope(shell_profiles=[profile, profile.copy()]))
        self.assertEqual(len(document["domains"]), 1)

    def test_linked_stable_root_is_rejected_before_reading_its_manifest(self):
        stable = self.pkg / "assets/external-skills/stable"
        foreign = self.base / "unselected"
        shutil.move(str(stable), foreign)
        # If inventory reads through the link before refusing, this malformed
        # manifest would raise source-untrusted instead of unsafe-path.
        (foreign / "MANIFEST.json").write_bytes(b"UNSELECTED-PRIVATE-CONTENT")
        stable.symlink_to(foreign, target_is_directory=True)
        self.assert_code("unsafe-path", self.scope(skills_roots=[str(self.skills_root)]))

    def test_linked_catalog_source_is_rejected_before_reading_its_contents(self):
        source = self.pkg / "templates/skills/alpha-skill"
        foreign = self.base / "unselected-skill"
        shutil.move(str(source), foreign)
        (foreign / "SKILL.md").write_bytes(b"UNSELECTED-PRIVATE-CONTENT")
        source.symlink_to(foreign, target_is_directory=True)
        self.assert_code("unsafe-path", self.scope(skills_roots=[str(self.skills_root)]))


if __name__ == "__main__":
    unittest.main()
