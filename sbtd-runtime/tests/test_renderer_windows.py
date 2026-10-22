"""Native Windows regression for renderer descendants after worker crash."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


@unittest.skipUnless(os.name == "nt", "Windows Job Object evidence requires Windows")
class WindowsJobTests(unittest.TestCase):
    def test_worker_exit_does_not_release_descendant_ownership(self) -> None:
        import ctypes
        from ctypes import wintypes

        from renderer_windows import WindowsJob

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        job = WindowsJob()
        self.addCleanup(job.close)
        with tempfile.TemporaryDirectory(prefix="sbtd-windows-job-") as temporary:
            pid_file = Path(temporary) / "descendant.pid"
            profile_file = Path(temporary) / "profile.lock"
            ready_file = Path(temporary) / "ready"
            child_script = (
                "import pathlib, sys, time; handle=open(sys.argv[1], 'w'); "
                "handle.write('held'); handle.flush(); "
                "pathlib.Path(sys.argv[2]).write_text('ready'); time.sleep(60)"
            )
            script = (
                "import os, pathlib, subprocess, sys\n"
                "from renderer_windows import join_job\n"
                "join_job(sys.argv[1])\n"
                f"child = subprocess.Popen([sys.executable, '-c', {child_script!r}, "
                f"{str(profile_file)!r}, {str(ready_file)!r}])\n"
                "pathlib.Path(sys.argv[2]).write_text(str(child.pid))\n"
                "os._exit(1)\n"
            )
            runtime = str(Path(__file__).resolve().parents[1])
            worker = subprocess.Popen(
                [sys.executable, "-c", script, job.name, str(pid_file)],
                env={**os.environ, "PYTHONPATH": runtime},
            )
            self.addCleanup(worker.kill)
            self.assertEqual(worker.wait(timeout=15), 1)
            deadline = time.monotonic() + 5
            while not ready_file.exists():
                self.assertLess(
                    time.monotonic(), deadline, "child did not open profile"
                )
                time.sleep(0.01)
            child_pid = int(pid_file.read_text())
            handle = kernel.OpenProcess(0x00100000, False, child_pid)  # SYNCHRONIZE
            self.assertTrue(handle, "descendant must still be alive before job close")
            try:
                self.assertEqual(
                    kernel.WaitForSingleObject(handle, 0), 258
                )  # WAIT_TIMEOUT
                job.close()
                self.assertEqual(kernel.WaitForSingleObject(handle, 0), 0)
                profile_file.unlink()  # teardown must finish before profile deletion
                self.assertFalse(profile_file.exists())
            finally:
                kernel.CloseHandle(handle)


if __name__ == "__main__":
    unittest.main()
