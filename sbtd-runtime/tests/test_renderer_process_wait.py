"""macOS Python 3.12 worker exit observation must not reap before group cleanup."""

from __future__ import annotations

import errno
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import browser_renderer


class WorkerExitTests(unittest.TestCase):
    def test_exit_observation_preserves_cleanup_and_actual_worker_status(self) -> None:
        for returncode in (0, 7, -9):
            with self.subTest(returncode=returncode):
                self._run_worker(returncode=returncode, cancelled=False)

    def test_cancellation_closes_exit_queue_and_terminates_worker(self) -> None:
        self._run_worker(returncode=-9, cancelled=True)

    def test_exit_before_registration_preserves_real_result(self) -> None:
        for returncode in (0, 7):
            with self.subTest(returncode=returncode):
                self._run_worker(
                    returncode=returncode,
                    cancelled=False,
                    registration_error=ProcessLookupError(errno.ESRCH, "worker exited"),
                )

    def test_other_registration_errors_fail_and_clean_up(self) -> None:
        self._run_worker(
            returncode=-9,
            cancelled=False,
            registration_error=PermissionError(errno.EPERM, "registration denied"),
        )

    def _run_worker(
        self,
        *,
        returncode: int,
        cancelled: bool,
        registration_error: OSError | None = None,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            job = Path(temporary)
            (job / "request.json").write_text(
                json.dumps({"home": temporary, "format": "jpeg", "preflight": True}),
                encoding="utf-8",
            )
            (job / "result.json").write_text(
                json.dumps({"scale": 2, "warnings": []}), encoding="utf-8"
            )
            process = Mock(pid=12345, returncode=None)
            process.poll.side_effect = AssertionError("leader reaped before killpg")
            queue = Mock()
            queue.control.side_effect = (
                registration_error
                if registration_error is not None
                else [[], [], [object()]]
            )
            native_select = SimpleNamespace(
                kqueue=Mock(return_value=queue),
                kevent=Mock(),
                KQ_FILTER_PROC=-5,
                KQ_EV_ADD=1,
                KQ_EV_ONESHOT=16,
                KQ_NOTE_EXIT=0x80000000,
            )
            cleaned = []

            def terminate(proc):
                self.assertIsNone(proc.returncode, "leader was reaped before cleanup")
                cleaned.append(proc.pid)
                proc.returncode = returncode

            # Deliberately no waitid: this is the Python 3.12 Darwin API surface.
            native_os = SimpleNamespace(name="posix", environ=os.environ)
            with (
                patch.object(browser_renderer, "os", native_os),
                patch.object(browser_renderer, "select", native_select, create=True),
                patch.object(
                    browser_renderer.subprocess, "Popen", return_value=process
                ),
                patch.object(
                    browser_renderer, "_terminate_group", side_effect=terminate
                ),
            ):
                if registration_error is not None and not isinstance(
                    registration_error, ProcessLookupError
                ):
                    with self.assertRaises(type(registration_error)):
                        browser_renderer._execute_job(
                            job, job, lambda: False, time.monotonic() + 5
                        )
                elif cancelled or returncode:
                    with self.assertRaises(browser_renderer.RendererError) as caught:
                        browser_renderer._execute_job(
                            job, job, lambda: cancelled, time.monotonic() + 5
                        )
                    self.assertEqual(
                        caught.exception.code,
                        "RENDERER_CANCELLED" if cancelled else "RENDERER_FAILED",
                    )
                else:
                    payload, result = browser_renderer._execute_job(
                        job, job, lambda: False, time.monotonic() + 5
                    )
                    self.assertEqual(payload, b"")
                    self.assertEqual(result, {"scale": 2, "warnings": []})
            self.assertEqual(cleaned, [12345])
            queue.close.assert_called_once_with()
            process.poll.assert_not_called()


if __name__ == "__main__":
    unittest.main()
