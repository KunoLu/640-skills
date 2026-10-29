"""Golden pinned tests for contracts/panel-manifest.json (D14).

Modeled on test_golden_contracts.py: the manifest is the single source of
truth for panels (PRD v0.2 §12.4); the frontend registry, ReportDocument,
export reconciliation, and AC-45 tests all derive from it. These tests pin
the versioned schema, the thirteen §12.4 panels, and the derivation chain
so no second panel list can silently appear.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import jsonschema

from contract_eval import load_json

MANIFEST_PATH = ROOT / "contracts" / "panel-manifest.json"
SCHEMA_PATH = ROOT / "contracts" / "panel-manifest.schema.json"
SCHEMA = load_json(SCHEMA_PATH)
# Explicit schema_version → schema binding (instance files carry no $schema
# pointer, per the event.schema.json convention). A manifest whose
# schema_version has no entry here has no known schema: validation must
# fail loudly, never silently validate against the wrong (or latest) schema.
SCHEMA_BY_VERSION = {"1.0": SCHEMA_PATH}
CATALOG = load_json(ROOT / "contracts" / "metrics-catalog.json")
BUDGET = load_json(ROOT / "dashboard" / "artifact-budget.json")
DASHBOARD = ROOT / "dashboard"
STATIC = DASHBOARD / "static"

# PRD v0.2 §12.4 panel table, in declared order.
PANEL_IDS = (
    "overview",
    "task-lifecycle",
    "activity-trend",
    "mode-decisions",
    "step-performance",
    "blockers",
    "component-usage",
    "gate-matrix",
    "validation-evidence",
    "host-model-usage",
    "project-actor-summary",
    "task-audit-detail",
    "data-quality",
)

REQUIRED_PANEL_FIELDS = {
    "panel_id",
    "title_zh",
    "title_en",
    "order",
    "desktop_span",
    "kind",
    "metric_ids",
    "field_dependencies",
    "export_required",
    "always_visible",
    "insufficient_data_zh",
    "insufficient_data_en",
}

PANEL_KINDS = {"kpi", "chart", "table"}

# Pinned (manifest_version, canonical content sha256) pair. Canonical form:
# json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
# encoded as UTF-8. ANY content change to contracts/panel-manifest.json must
# update the content pin together with the intended change. Version history:
# 1.0.0 added the bilingual title_en/insufficient_data_en fields without
# touching pre-existing fields; 1.1.0 swaps the gate-matrix/component-usage
# order so two half-width panels share one row (layout-only, no field change).
EXPECTED_MANIFEST_VERSION = "1.1.0"
EXPECTED_MANIFEST_SHA256 = (
    "43f94e60bfebfd5dc2e90a1dae9b34c0f4ac5771193b1d6a7b365be0234e1584"
)


def load_manifest() -> dict:
    return load_json(MANIFEST_PATH)


class ManifestVersionTests(unittest.TestCase):
    def test_schema_version_is_pinned(self) -> None:
        manifest = load_manifest()
        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertEqual(manifest["manifest_version"], EXPECTED_MANIFEST_VERSION)
        self.assertEqual(manifest["release"], "v2.1.0-rc.2")

    def test_canonical_content_hash_matches_manifest_version(self) -> None:
        # Locks the full panel table: every panel_id, title_zh, title_en, order,
        # desktop_span, kind, metric_ids, field_dependencies, export_required,
        # always_visible, insufficient_data_zh, and the root metadata. Any
        # content change — value edit, added/removed key, reorder of array
        # items — changes the canonical hash and fails here unless the content
        # pin below was updated together with the intended change.
        manifest = load_manifest()
        self.assertEqual(manifest["manifest_version"], EXPECTED_MANIFEST_VERSION)
        canonical = json.dumps(
            manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        self.assertEqual(
            hashlib.sha256(canonical).hexdigest(),
            EXPECTED_MANIFEST_SHA256,
            "panel-manifest.json content changed: bump manifest_version and "
            "update EXPECTED_MANIFEST_VERSION/EXPECTED_MANIFEST_SHA256 together",
        )


class PanelSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest()
        cls.panels = cls.manifest["panels"]

    def test_exact_thirteen_panels_in_prd_order(self) -> None:
        self.assertEqual([p["panel_id"] for p in self.panels], list(PANEL_IDS))

    def test_order_is_a_one_to_thirteen_permutation_matching_position(self) -> None:
        for position, panel in enumerate(self.panels, start=1):
            self.assertEqual(panel["order"], position)

    def test_required_fields_and_shape(self) -> None:
        for panel in self.panels:
            with self.subTest(panel=panel["panel_id"]):
                # Exact key set, not a subset: an unknown extra key or a
                # missing required field is a contract violation.
                self.assertEqual(set(panel), REQUIRED_PANEL_FIELDS)
                self.assertIn(panel["desktop_span"], (6, 12))
                self.assertIn(panel["kind"], PANEL_KINDS)
                self.assertTrue(panel["title_zh"].strip())
                self.assertTrue(panel["title_en"].strip())
                self.assertTrue(panel["insufficient_data_zh"].strip())
                self.assertTrue(panel["insufficient_data_en"].strip())

    def test_every_panel_has_english_copy_for_the_same_ids(self) -> None:
        # Bilingual export renders title_en / insufficient_data_en when
        # presentation_state.locale is "en" and the _zh fields otherwise; both
        # languages must cover exactly the same panels.
        zh = {p["panel_id"] for p in self.panels if p["title_zh"].strip()}
        en = {p["panel_id"] for p in self.panels if p["title_en"].strip()}
        self.assertEqual(zh, en)
        self.assertEqual(len(en), 13)
        zh_notes = {
            p["panel_id"] for p in self.panels if p["insufficient_data_zh"].strip()
        }
        en_notes = {
            p["panel_id"] for p in self.panels if p["insufficient_data_en"].strip()
        }
        self.assertEqual(zh_notes, en_notes)
        self.assertEqual(len(en_notes), 13)

    def test_metric_ids_exist_in_the_metrics_catalog(self) -> None:
        catalog_ids = {m["metric_id"] for m in CATALOG["metrics"]}
        for panel in self.panels:
            with self.subTest(panel=panel["panel_id"]):
                self.assertTrue(
                    set(panel["metric_ids"]) <= catalog_ids,
                    f"unknown metric_ids: {set(panel['metric_ids']) - catalog_ids}",
                )

    def test_every_panel_is_export_required(self) -> None:
        # §12.3: 首版不提供可隐藏核心 Panel 的自定义 Dashboard；导出不能少内容。
        for panel in self.panels:
            with self.subTest(panel=panel["panel_id"]):
                self.assertIs(panel["export_required"], True)

    def test_data_quality_panel_is_always_visible(self) -> None:
        # §12.4: data-quality 必须始终存在，不能随导出隐藏（AC-39）。
        data_quality = [p for p in self.panels if p["panel_id"] == "data-quality"]
        self.assertEqual(len(data_quality), 1)
        self.assertIs(data_quality[0]["always_visible"], True)
        others = [p for p in self.panels if p["panel_id"] != "data-quality"]
        self.assertTrue(all(p["always_visible"] is False for p in others))


class SchemaValidationTests(unittest.TestCase):
    """jsonschema validation against contracts/panel-manifest.schema.json.

    Modeled on test_golden_contracts.py: the schema file is loaded directly
    (instance contracts carry no $schema pointer — the repository convention
    established with event.schema.json).
    """

    def test_manifest_validates_against_its_schema(self) -> None:
        manifest = load_manifest()
        version = manifest["schema_version"]
        schema_path = SCHEMA_BY_VERSION.get(version)
        # Fail (never skip) when the manifest declares a schema_version with
        # no mapped schema file.
        self.assertIsNotNone(
            schema_path, f"no schema mapped for schema_version {version!r}"
        )
        jsonschema.Draft202012Validator(load_json(schema_path)).validate(manifest)

    def test_unmapped_schema_versions_are_rejected(self) -> None:
        for version in ("1.1", "2.0"):
            with self.subTest(schema_version=version):
                manifest = copy.deepcopy(load_manifest())
                manifest["schema_version"] = version
                # The mapped 1.0 schema pins const "1.0": any other declared
                # version fails validation against it.
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.Draft202012Validator(SCHEMA).validate(manifest)
                # The version → schema binding itself must also fail loudly:
                # no schema is mapped for an unknown version.
                self.assertNotIn(
                    version,
                    SCHEMA_BY_VERSION,
                    f"schema_version {version!r} unexpectedly has a mapped schema",
                )

    def test_unknown_extra_root_key_is_rejected(self) -> None:
        manifest = load_manifest()
        manifest["unexpected"] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(SCHEMA).validate(manifest)

    def test_unknown_extra_panel_key_is_rejected(self) -> None:
        manifest = load_manifest()
        manifest["panels"][0]["unexpected"] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(SCHEMA).validate(manifest)

    def test_missing_required_panel_field_is_rejected(self) -> None:
        manifest = load_manifest()
        del manifest["panels"][0]["title_zh"]
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(SCHEMA).validate(manifest)

    def test_empty_field_dependencies_is_rejected(self) -> None:
        manifest = load_manifest()
        manifest["panels"][0]["field_dependencies"] = []
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(SCHEMA).validate(manifest)

    def test_load_manifest_returns_fresh_objects(self) -> None:
        # The negative tests above mutate their manifest copies; ensure the
        # loader returns independent objects so tests cannot contaminate each
        # other (load_json parses the file on every call).
        self.assertIsNot(load_manifest(), load_manifest())


class DerivationChainTests(unittest.TestCase):
    """The frontend must derive from the manifest, never restate it."""

    def test_frontend_imports_the_contracts_manifest(self) -> None:
        source = (DASHBOARD / "src" / "manifest.ts").read_text(encoding="utf-8")
        self.assertIn("../../contracts/panel-manifest.json", source)

    def test_registry_derives_from_the_manifest_module(self) -> None:
        source = (DASHBOARD / "src" / "registry.ts").read_text(encoding="utf-8")
        self.assertIn('from "./manifest"', source)

    def test_report_document_derives_from_the_registry(self) -> None:
        source = (DASHBOARD / "src" / "reportDocument.ts").read_text(encoding="utf-8")
        self.assertIn("registry", source)

    def test_no_second_manifest_copy_under_dashboard(self) -> None:
        copies = [
            p
            for p in DASHBOARD.rglob("*.json")
            if "panel-manifest" in p.name and "node_modules" not in p.parts
        ]
        self.assertEqual(copies, [])


class CommittedArtifactTests(unittest.TestCase):
    """D1: built artifacts are committed; this pins their presence, not hashes."""

    def test_static_index_exists_and_references_existing_assets(self) -> None:
        index = STATIC / "index.html"
        self.assertTrue(index.is_file())
        html = index.read_text(encoding="utf-8")
        self.assertIn("/assets/", html)
        asset_dir = STATIC / "assets"
        self.assertTrue(asset_dir.is_dir())
        self.assertTrue(any(asset_dir.glob("*.js")))
        self.assertTrue(any(asset_dir.glob("*.css")))

    def test_static_total_size_within_adr_budget(self) -> None:
        budget = BUDGET["budgets"]["static_total_bytes"]
        total = sum(p.stat().st_size for p in STATIC.rglob("*") if p.is_file())
        self.assertLessEqual(total, budget)


if __name__ == "__main__":
    unittest.main()
