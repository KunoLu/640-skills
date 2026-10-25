"""Small real CLI run: accepted events, complete CSV and honest report boundaries."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from runtime_perf import distribution


class RuntimePerfSmokeTests(unittest.TestCase):
    def test_cli_preserves_dataset_and_reports_unmeasured_boundaries(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary).resolve()
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(Path(__file__).with_name("runtime_perf.py")),
                    "--events",
                    "101",
                    "--samples",
                    "2",
                    "--seed-seconds",
                    "60",
                    "--output",
                    str(output),
                ],
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
                timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(next(output.glob("runtime-perf-*.json")).read_text())
            self.assertEqual(report["dataset"]["events"], 101)
            self.assertEqual(report["dataset"]["tasks"], 2)
            self.assertEqual(report["dataset"]["steps"], 10)
            self.assertFalse(report["dataset"]["truncated"])
            self.assertEqual(report["csv_rows"]["event"], 101)
            self.assertEqual(report["csv_rows"]["step"], 10)
            self.assertEqual(report["csv_rows"]["task"], 2)
            self.assertEqual(report["html_panel_count"], 13)
            self.assertEqual(
                report["measurements"]["export_csv"]["status"], "not-measured"
            )
            self.assertEqual(report["measurements"]["event_to_visible"]["n"], 0)
            self.assertEqual(report["measurements"]["audit_100"]["status"], "not-met")
            self.assertEqual(report["measurements"]["audit_100"]["n"], 2)
            self.assertEqual(report["serve_exit"], 0)
            self.assertFalse(list(output.glob("perf-home-*")))
            raw = next(output.glob("runtime-perf-*.json"))
            self.assertTrue(raw.with_suffix(".md").is_file())
            self.assertIn("未达 1M 档", report["reference_scale_note"])
            self.assertIn("未达 1M 档", raw.with_suffix(".md").read_text())
            self.assertIn("未达 1M 档", result.stdout)

    def test_nearest_rank_keeps_tail_and_empty_is_unmeasured(self):
        values = list(range(1, 21))
        result = distribution(values)
        self.assertEqual((result["p50"], result["p95"], result["max"]), (10, 19, 20))
        self.assertEqual(distribution([])["p95"], None)


if __name__ == "__main__":
    unittest.main()
