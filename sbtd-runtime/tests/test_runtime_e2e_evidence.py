"""Native E2E failure evidence: useful diagnostics without credential disclosure."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import runtime_e2e


class FontEvidenceTests(unittest.TestCase):
    def test_renderer_rejects_non_cjk_glyphs_and_unused_cjk_font(self) -> None:
        fonts = [
            {"familyName": "Helvetica", "glyphCount": 2, "isCustomFont": False},
            {"familyName": "Times", "glyphCount": 3, "isCustomFont": False},
            {"familyName": "PingFang SC", "glyphCount": 0, "isCustomFont": False},
        ]
        with self.assertRaisesRegex(
            AssertionError, "no verified CJK font produced heading glyphs"
        ):
            runtime_e2e.verified_cjk_families(fonts)

    def test_renderer_accepts_pingfang_with_heading_glyphs(self) -> None:
        self.assertEqual(
            runtime_e2e.verified_cjk_families(
                [{"familyName": "PingFang SC", "glyphCount": 2, "isCustomFont": False}]
            ),
            ["PingFang SC"],
        )

    def test_downloaded_html_records_non_cjk_fonts_without_glyph_assertion(
        self,
    ) -> None:
        record = {
            "fonts_ready": "loaded",
            "panels": ["overview"],
            "cjk_text_present": True,
            "platform_fonts": {
                "fonts": [
                    {
                        "familyName": "Helvetica",
                        "postScriptName": "Helvetica",
                        "glyphCount": 2,
                        "isCustomFont": False,
                    }
                ]
            },
        }
        runtime_e2e.assert_font_records({"html": record}, ["overview"])
        self.assertEqual(record["cjk_families"], [])
        self.assertEqual(record["status"], "passed")
        self.assertEqual(record["platform_fonts"]["fonts"][0]["glyphCount"], 2)

    def test_failed_renderer_glyph_gate_preserves_raw_fonts_in_report(self) -> None:
        fonts = {
            "fonts": [
                {
                    "familyName": "Times",
                    "postScriptName": "Times-Roman",
                    "glyphCount": 2,
                    "isCustomFont": False,
                },
                {"familyName": "PingFang SC", "glyphCount": 0, "isCustomFont": False},
            ]
        }

        def fail_glyph_gate(home, evidence, install_browser, secrets):
            evidence["fonts"] = {
                "jpeg": {
                    "fonts_ready": "loaded",
                    "panels": ["overview"],
                    "cjk_text_present": True,
                    "platform_fonts": fonts,
                }
            }
            runtime_e2e.assert_font_records(evidence["fonts"], ["overview"])

        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch.object(runtime_e2e, "exercise", side_effect=fail_glyph_gate),
                patch("sys.argv", ["runtime_e2e.py", "--output", temporary]),
            ):
                self.assertEqual(runtime_e2e.main(), 1)
            raw = next(Path(temporary).glob("*.json"))
            evidence = json.loads(raw.read_text(encoding="utf-8"))
            self.assertIn(
                "no verified CJK font produced heading glyphs", evidence["error"]
            )
            self.assertEqual(evidence["fonts"]["jpeg"]["platform_fonts"], fonts)


class NativeEvidenceTests(unittest.TestCase):
    def test_redacts_before_truncating_and_handles_overlapping_values(self) -> None:
        secrets = ["synthetic-ticket", "synthetic-ticket-extended", "synthetic-csrf"]
        text = "prefix " + " ".join(secrets) + " suffix"
        safe = runtime_e2e._safe_text(text, secrets, limit=30)
        self.assertEqual(safe, "prefix <REDACTED> <REDACTED> <")
        self.assertFalse(any(secret in safe for secret in secrets))

    def test_log_leak_fails_but_saved_evidence_is_redacted_and_capped(self) -> None:
        secrets = ["synthetic-ticket", "synthetic-bearer", "synthetic-csrf"]
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            (home / "runtime.log").write_text(
                "export preflight failed: EXPORT_FONT_UNAVAILABLE\n"
                + secrets[2]
                + "x" * 100_000,
                encoding="utf-8",
            )
            evidence = {}
            with self.assertRaisesRegex(AssertionError, "credential leaked"):
                runtime_e2e._capture_logs(
                    home, secrets[0], secrets[1], secrets, evidence
                )
            logs = evidence["serve_logs"]
            self.assertEqual(logs["stdout"], "<REDACTED>")
            self.assertEqual(logs["stderr"], "<REDACTED>")
            self.assertIn(
                "EXPORT_FONT_UNAVAILABLE", logs["runtime_home_logs"][0]["text"]
            )
            self.assertLessEqual(len(logs["runtime_home_logs"][0]["text"]), 16_384)
            self.assertTrue(logs["runtime_home_logs"][0]["truncated"])
            self.assertFalse(any(secret in json.dumps(evidence) for secret in secrets))

    def test_real_query_failure_keeps_body_logs_and_clean_shutdown(self) -> None:
        original_request = runtime_e2e.request

        def invalid_timezone(port, method, path, **kwargs):
            if path == "/api/v1/statistics/query":
                kwargs["body"]["range"]["timezone"] = "Invalid/NativeEvidence"
            return original_request(port, method, path, **kwargs)

        with tempfile.TemporaryDirectory() as temporary:
            evidence = {}
            secrets = []
            with (
                patch.object(runtime_e2e, "request", side_effect=invalid_timezone),
                patch.dict("os.environ", {"SBTD_RENDERER_TEST_HOME": ""}),
                self.assertRaisesRegex(AssertionError, "400 != 200"),
            ):
                runtime_e2e.exercise(
                    Path(temporary).resolve(), evidence, False, secrets
                )
            failed = evidence["requests"][-1]
            self.assertEqual(failed["status"], 400)
            self.assertIn("unknown timezone", failed["response_body"])
            self.assertIn("SBTD Runtime Dashboard:", evidence["serve_logs"]["stdout"])
            self.assertEqual(evidence["shutdown"]["exit_code"], 0)
            self.assertTrue(evidence["shutdown"]["port_closed"])
            self.assertFalse(any(secret in json.dumps(evidence) for secret in secrets))

    def test_unexpected_pair_status_redacts_issued_session_in_report_files(
        self,
    ) -> None:
        original_request = runtime_e2e.request
        issued = []

        def unexpected_pair(port, method, path, **kwargs):
            status, headers, payload = original_request(port, method, path, **kwargs)
            if path == "/api/v1/session/pair" and status == 200:
                issued.extend(
                    [
                        kwargs["headers"]["X-Pairing-Code"],
                        json.loads(payload)["access_token"],
                        headers["x-csrf-token"],
                    ]
                )
                return 500, headers, payload
            return status, headers, payload

        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch.object(runtime_e2e, "request", side_effect=unexpected_pair),
                patch.dict("os.environ", {"SBTD_RENDERER_TEST_HOME": ""}),
                patch("sys.argv", ["runtime_e2e.py", "--output", temporary]),
            ):
                self.assertEqual(runtime_e2e.main(), 1)
            raw = next(Path(temporary).glob("*.json"))
            evidence = json.loads(raw.read_text(encoding="utf-8"))
            failed = evidence["requests"][-1]
            self.assertEqual(failed["status"], 500)
            self.assertTrue(
                json.loads(failed["response_body"])["access_token"] == "<REDACTED>",
                "issued session was not redacted",
            )
            self.assertEqual(evidence["status"], "failed")
            self.assertEqual(len(issued), 3)
            for path in (raw, raw.with_suffix(".md")):
                text = path.read_text(encoding="utf-8")
                self.assertFalse(any(secret in text for secret in issued))

    def test_failed_worker_records_exception_chain_and_result_absence(self) -> None:
        import runtime_e2e_diagnostics as diagnostics

        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary).resolve()
            fake = home / "broken_worker.py"
            fake.write_text(
                "import sys\n"
                f"sys.path[:0] = {[str(runtime_e2e.RUNTIME), str(Path(__file__).resolve().parent)]!r}\n"
                "import browser_renderer as renderer\n"
                "from runtime_e2e_diagnostics import worker_main\n"
                "def broken(job):\n"
                "    try:\n"
                "        raise ValueError('synthetic-ticket')\n"
                "    except ValueError:\n"
                "        raise renderer.RendererError(renderer.RENDERER_FAILED) from None\n"
                "renderer._worker_run = broken\n"
                "raise SystemExit(worker_main(sys.argv[1]))\n",
                encoding="utf-8",
            )
            with patch.object(
                diagnostics,
                "_worker_argv",
                side_effect=lambda job: [sys.executable, str(fake), str(job)],
            ):
                evidence = diagnostics.diagnose(
                    home,
                    b"<html>same frozen snapshot</html>",
                    "jpeg",
                    preflight=True,
                    sanitize=lambda text: runtime_e2e._safe_text(
                        text, ["synthetic-ticket"]
                    ),
                )
            worker = evidence["workers"][0]
            self.assertEqual(worker["exit_code"], 1)
            self.assertEqual(
                json.loads(worker["files"]["error.json"]["content"]),
                {"code": "RENDERER_FAILED"},
            )
            self.assertFalse(worker["files"]["result.json"]["exists"])
            chain = json.loads(worker["files"]["exception.json"]["content"])
            self.assertEqual(
                [row["type"] for row in chain], ["RendererError", "ValueError"]
            )
            self.assertIn("broken", chain[0]["site"])
            self.assertIn("Traceback", chain[0]["traceback"])
            self.assertFalse("synthetic-ticket" in json.dumps(evidence))
            self.assertEqual(evidence["status"], "failed")
            self.assertIn("_read_result", evidence["exception_chain"][0]["site"])

    def test_cleanup_failure_keeps_successful_worker_result(self) -> None:
        import browser_renderer
        import runtime_e2e_diagnostics as diagnostics

        terminate = browser_renderer._terminate_group

        def fail_after_reaping(proc):
            terminate(proc)
            raise browser_renderer.RendererError(browser_renderer.RENDERER_FAILED)

        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary).resolve()
            command = (
                "import pathlib,sys; "
                "(pathlib.Path(sys.argv[1])/'result.json').write_text("
                '\'{"scale": 2, "warnings": []}\')'
            )
            with (
                patch.object(
                    diagnostics,
                    "_worker_argv",
                    side_effect=lambda job: [sys.executable, "-c", command, str(job)],
                ),
                patch.object(
                    browser_renderer, "_terminate_group", side_effect=fail_after_reaping
                ),
            ):
                evidence = diagnostics.diagnose(
                    home,
                    b"<html>snapshot</html>",
                    "jpeg",
                    preflight=True,
                    sanitize=lambda text: text,
                )
            worker = evidence["workers"][0]
            self.assertEqual(worker["exit_code"], 0)
            self.assertTrue(worker["files"]["result.json"]["exists"])
            self.assertEqual(
                json.loads(worker["files"]["result.json"]["content"])["scale"], 2
            )
            self.assertFalse(worker["files"]["error.json"]["exists"])
            self.assertEqual(evidence["status"], "failed")
            self.assertIn("fail_after_reaping", evidence["exception_chain"][0]["site"])


if __name__ == "__main__":
    unittest.main()
