"""AC-45/51: reconcile manifest panels and metric values at export boundaries.

Real stores and renderer when SBTD_RENDERER_TEST_HOME is available; otherwise
only the existing browser-worker stub is used and explicitly reported. JPEG
checks its actual renderer input, not pixel OCR. PDF uses pdftotext if present.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from unittest import mock

from browser_renderer import _render_document, renderer_capability
from export_render import ExportRenderer, default_presentation, load_panel_manifest
from report_snapshot import SnapshotStore
from test_csv_export import _dataset, _rows, _scope
from test_renderer_integration import _accept_call, _artifact, _patched_worker

# Independent worked values from the golden fixture, not recomputed by query().
KEY_VALUES = {"tasks.touched": "2", "steps.success_rate_observed": "1/2"}


class ReportText(HTMLParser):
    """Read visible panel identities and dt/dd metric pairs, never embedded JSON."""

    def __init__(self, document: str) -> None:
        super().__init__()
        self.panels: list[str] = []
        self.metrics: dict[str, list[str]] = {}
        self.cell: str | None = None
        self.text: list[str] = []
        self.metric = ""
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "section" and "panel" in attributes.get("class", "").split():
            self.panels.append(attributes.get("id", ""))
        if tag in {"dt", "dd"}:
            self.cell = tag
            self.text = []

    def handle_data(self, data):
        if self.cell:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag != self.cell:
            return
        text = "".join(self.text).strip()
        if tag == "dt":
            self.metric = text
        else:
            self.metrics.setdefault(self.metric, []).append(text)
        self.cell = None


def assert_key_values(
    case, documents: dict[str, str], csv_payload: bytes, expected_values=None
) -> dict:
    rows = [row for row in _rows(csv_payload) if row["record_type"] == "metric"]
    observed = {}
    for metric, expected in (expected_values or KEY_VALUES).items():
        values = [row["metric_value"] for row in rows if row["metric_id"] == metric]
        case.assertEqual(values, [expected], metric)
        observed[metric] = expected
        for format_name, document in documents.items():
            values = ReportText(document).metrics.get(metric, [])
            case.assertTrue(values, f"{format_name}: missing {metric}")
            # Status qualifiers are allowed, but the entire numeric token must match.
            case.assertEqual(
                {value.split()[0] for value in values}, {expected}, format_name
            )
    return observed


def assert_panels(case, documents: dict[str, str], csv_payload: bytes) -> list[str]:
    manifest = load_panel_manifest()
    expected = [panel["panel_id"] for panel in manifest["panels"]]
    for format_name, document in documents.items():
        case.assertEqual(
            Counter(ReportText(document).panels), Counter(expected), format_name
        )
    rows = _rows(csv_payload)
    metric_ids = [row["metric_id"] for row in rows if row["record_type"] == "metric"]
    expected_metrics = {
        metric for panel in manifest["panels"] for metric in panel["metric_ids"]
    }
    case.assertEqual(
        Counter(metric_ids), Counter(expected_metrics), "CSV metric sections"
    )
    # CSV has data families, not visual panel IDs. Empty families are represented
    # by rows:<family>=0 metadata; compare declared counts with actual detail rows.
    declared = {
        row["metadata_key"].removeprefix("rows:"): int(row["metadata_value"])
        for row in rows
        if row["record_type"] == "metadata" and row["metadata_key"].startswith("rows:")
    }
    actual = Counter(
        row["record_type"]
        for row in rows
        if row["record_type"] not in {"metadata", "metric"}
    )
    case.assertEqual(
        actual, Counter({family: count for family, count in declared.items() if count})
    )
    # Non-metric panels and visual table/detail data have explicit CSV equivalents.
    families = {
        "project-actor-summary": {"task"},
        "task-audit-detail": {"task", "run", "step", "event"},
        "data-quality": {"data_quality"},
    }
    for panel in manifest["panels"]:
        case.assertTrue(
            panel["metric_ids"] or panel["panel_id"] in families, panel["panel_id"]
        )
        for family in families.get(panel["panel_id"], ()):
            case.assertIn(family, declared, panel["panel_id"])
    return expected


def assert_pdf_text(
    case, payload: bytes, panels: list[str], expected_values=None
) -> str:
    executable = shutil.which("pdftotext")
    limitation = "source-document-only: pdftotext "
    if not executable:
        return limitation + "unavailable; no dependency added"
    try:
        with tempfile.TemporaryDirectory(prefix="sbtd-reconcile-pdf-") as temporary:
            path = Path(temporary) / "report.pdf"
            path.write_bytes(payload)
            # Windows text-mode pipe readers decode in background threads; a
            # decode failure can leave stdout=None rather than raise here.
            result = subprocess.run(
                [executable, "-enc", "UTF-8", "-layout", str(path), "-"],
                capture_output=True,
                check=False,
                timeout=30,
            )
    except (OSError, subprocess.TimeoutExpired) as error:
        return limitation + f"could not extract text ({type(error).__name__})"
    if result.returncode != 0:
        return limitation + f"exit {result.returncode}; text not verified"
    if result.stdout is None:
        return limitation + "returned no stdout; text not verified"
    try:
        text = result.stdout.decode("utf-8")
    except UnicodeError:
        return limitation + "output is not UTF-8; text not verified"
    if not text.strip():
        return limitation + "returned empty text; text not verified"
    for panel in panels:
        case.assertIn(panel, text)
    case.assertIn("概览", text)
    case.assertIn("数据质量", text)
    for metric, expected in (expected_values or KEY_VALUES).items():
        case.assertRegex(
            text, re.escape(metric) + r"\s+" + re.escape(expected) + r"(?=\s|$)"
        )
    return (
        "downloaded-pdf-text: pdftotext -enc UTF-8 -layout; CJK and key values verified"
    )


class ExportReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="sbtd-reconciliation-")
        self.addCleanup(temporary.cleanup)
        home = Path(temporary.name).resolve()
        self.snapshots = SnapshotStore(home)
        manifest = load_panel_manifest()
        metrics = sorted(
            {metric for panel in manifest["panels"] for metric in panel["metric_ids"]}
        )
        self.snapshot = self.snapshots.create_or_reuse(
            _dataset(), _scope(_dataset(), metrics)
        )
        renderer_home = Path(os.environ.get("SBTD_RENDERER_TEST_HOME", str(home)))
        self.capability = renderer_capability(renderer_home)
        renderer = ExportRenderer(self.snapshots, home=renderer_home)
        self.documents = {}
        self.payloads = {}
        self.metadata = {}

        def observe(*args, **kwargs):
            document, format_name = _accept_call(args, kwargs)
            self.documents[format_name] = document
            if self.capability["available"]:
                return _render_document(*args, **kwargs)
            return _artifact(format_name), {}

        # Do not claim browser execution when using the existing optional seam.
        context = (
            mock.patch("browser_renderer._render_document", side_effect=observe)
            if self.capability["available"]
            else _patched_worker(observe)
        )
        with context:
            for format_name in ("html", "csv", "jpeg", "pdf"):
                payload, meta = renderer(
                    self.snapshot, format_name, default_presentation(), lambda: False
                )
                self.payloads[format_name] = payload
                self.metadata[format_name] = meta
        self.documents["html"] = self.payloads["html"].decode("utf-8")
        print(
            "reconciliation renderer:",
            "real Chromium"
            if self.capability["available"]
            else f"existing worker stub ({self.capability['reason']})",
        )

    def test_four_formats_key_values_agree(self) -> None:
        assert_key_values(self, self.documents, self.payloads["csv"])
        if self.capability["available"]:
            print(assert_pdf_text(self, self.payloads["pdf"], []))
        for format_name, meta in self.metadata.items():
            self.assertEqual(
                meta["snapshot_id"], self.snapshot.snapshot_id, format_name
            )

    def test_every_manifest_panel_has_export_content(self) -> None:
        panels = assert_panels(self, self.documents, self.payloads["csv"])
        for format_name, meta in self.metadata.items():
            self.assertEqual(Counter(meta["panel_ids"]), Counter(panels), format_name)
        if self.capability["available"]:
            print(assert_pdf_text(self, self.payloads["pdf"], panels))


if __name__ == "__main__":
    unittest.main()
