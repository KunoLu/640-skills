"""Native E2E failure evidence: useful diagnostics without credential disclosure."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import runtime_e2e


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


if __name__ == "__main__":
    unittest.main()
