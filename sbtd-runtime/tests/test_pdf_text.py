"""PDF extraction limitations must not masquerade as verified PDF text."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_export_reconciliation import assert_pdf_text


class PdfTextTests(unittest.TestCase):
    def test_missing_stdout_is_a_reasoned_limitation(self) -> None:
        with (
            patch("shutil.which", return_value="pdftotext"),
            patch(
                "subprocess.run", return_value=subprocess.CompletedProcess([], 0, None)
            ),
        ):
            result = assert_pdf_text(self, b"%PDF-fake", ["overview"])
        self.assertTrue(result.startswith("source-document-only:"))
        self.assertIn("no stdout", result)

    def _extract(self, output: bytes, code: int = 0) -> str:
        # A real subprocess exercises decoding, including Windows reader threads.
        run = subprocess.run
        with tempfile.TemporaryDirectory() as temporary:
            fake = Path(temporary) / "pdftotext.py"
            fake.write_text(
                "import sys\n"
                "assert '-enc' in sys.argv and sys.argv[sys.argv.index('-enc') + 1] == 'UTF-8'\n"
                f"sys.stdout.buffer.write({output!r})\n"
                f"sys.exit({code})\n",
                encoding="utf-8",
            )

            def invoke(argv, **kwargs):
                return run([sys.executable, str(fake), *argv[1:]], **kwargs)

            with (
                patch("shutil.which", return_value="pdftotext"),
                patch("subprocess.run", side_effect=invoke),
            ):
                return assert_pdf_text(
                    self, b"%PDF-fake", ["overview"], {"tasks.touched": "3"}
                )

    def test_unusable_extraction_records_reason(self) -> None:
        for output, code, reason in (
            (b"", 0, "empty"),
            (b" \n\f", 0, "empty"),
            (b"\xff\xfe", 0, "UTF-8"),
            (b"not extracted", 7, "exit 7"),
        ):
            with self.subTest(output=output, code=code):
                result = self._extract(output, code)
                self.assertTrue(result.startswith("source-document-only:"))
                self.assertIn(reason, result)

    def test_utf8_text_is_verified_and_incorrect_content_still_fails(self) -> None:
        valid = "overview 概览 数据质量 tasks.touched 3\n"
        self.assertTrue(
            self._extract(valid.encode()).startswith("downloaded-pdf-text:")
        )
        for broken in (
            valid.replace("overview", "other"),
            valid.replace("概览", "other"),
            valid.replace("数据质量", "other"),
            valid.replace(" 3", " 4"),
        ):
            with self.subTest(text=broken), self.assertRaises(AssertionError):
                self._extract(broken.encode())


if __name__ == "__main__":
    unittest.main()
