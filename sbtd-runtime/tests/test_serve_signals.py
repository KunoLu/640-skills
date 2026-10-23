"""AC-33 native Ctrl-Break cleanup; POSIX emulates SIGBREAK with SIGTERM.

Only the OS signal number is adapted on POSIX. The real CLI and uvicorn
capture/re-raise lifecycle execute unchanged; this is not Windows evidence.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from test_serve import REPO, RUNTIME, _free_port, request


class BreakShutdownTests(unittest.TestCase):
    def test_break_signal_exits_zero_and_releases_lock(self) -> None:
        port = _free_port()
        with tempfile.TemporaryDirectory(prefix="sbtd-break-") as temporary:
            home = Path(temporary)
            entrypoint = ["-m", "serve"]
            if os.name != "nt":
                entrypoint = [
                    "-c",
                    "import signal, runpy; signal.SIGBREAK = signal.SIGTERM; runpy.run_module('serve', run_name='__main__')",
                ]
            proc = subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    *entrypoint,
                    "--home",
                    str(home),
                    "--port",
                    str(port),
                    "--no-open",
                ],
                env={**os.environ, "PYTHONPATH": str(RUNTIME), "PYTHONUTF8": "1"},
                cwd=REPO,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                if os.name == "nt"
                else 0,
            )
            try:
                deadline = time.monotonic() + 15
                while True:
                    self.assertIsNone(proc.poll(), "serve exited before health")
                    try:
                        status, _, _ = request(port, "GET", "/api/v1/health")
                        if status == 200:
                            break
                    except OSError:
                        pass
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(0.05)
                self.assertTrue((home / "serve.lock").exists())
                proc.send_signal(
                    signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGTERM
                )
                proc.communicate(timeout=15)
                self.assertEqual(proc.returncode, 0)
                self.assertFalse((home / "serve.lock").exists())
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.communicate(timeout=15)


if __name__ == "__main__":
    unittest.main()
