"""macOS Python 3.12 worker exit observation must not reap before group cleanup."""

from __future__ import annotations

import errno
import json
import os
import subprocess
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


class GroupPermissionTests(unittest.TestCase):
    def test_sigkill_eperm_returns_result_only_after_reap_and_esrch(self) -> None:
        self._run_cleanup(kill_denied=True)

    def test_probe_eperm_then_esrch_returns_result(self) -> None:
        self._run_cleanup(probes=("denied", "gone"))

    def test_group_still_present_after_reap_fails(self) -> None:
        for probe in ("alive", "denied"):
            with self.subTest(probe=probe):
                self._run_cleanup(
                    kill_denied=True, probes=(probe,), expected_failure=True
                )

    def test_worker_failure_survives_eperm_cleanup(self) -> None:
        for failure in ("exit", "error", "missing"):
            with self.subTest(failure=failure):
                self._run_cleanup(
                    kill_denied=True, worker_failure=failure, expected_failure=True
                )

    def test_unreaped_leader_cannot_turn_eperm_into_success(self) -> None:
        self._run_cleanup(kill_denied=True, wait_timeout=True, expected_failure=True)

    def _run_cleanup(
        self,
        *,
        kill_denied: bool = False,
        probes: tuple[str, ...] = ("gone",),
        worker_failure: str | None = None,
        wait_timeout: bool = False,
        expected_failure: bool = False,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            job = Path(temporary)
            (job / "request.json").write_text(
                json.dumps({"home": temporary, "format": "jpeg", "preflight": True}),
                encoding="utf-8",
            )
            if worker_failure != "missing":
                (job / "result.json").write_text(
                    json.dumps({"scale": 2, "warnings": []}), encoding="utf-8"
                )
            if worker_failure == "error":
                (job / "error.json").write_text(
                    json.dumps({"code": "RENDERER_FAILED"}), encoding="utf-8"
                )
            returncode = 7 if worker_failure == "exit" else 0
            process = Mock(pid=12345, returncode=None)
            probe_count = 0

            def reap(timeout):
                if wait_timeout:
                    raise subprocess.TimeoutExpired("worker", timeout)
                process.returncode = returncode
                return returncode

            def killpg(pid, sig):
                nonlocal probe_count
                self.assertEqual(pid, process.pid)
                if sig == 9:
                    self.assertIsNone(process.returncode)
                    if kill_denied:
                        raise PermissionError(errno.EPERM, "zombie group")
                    return
                self.assertEqual(sig, 0)
                self.assertEqual(process.returncode, returncode, "probe before reap")
                state = probes[min(probe_count, len(probes) - 1)]
                probe_count += 1
                if state == "gone":
                    raise ProcessLookupError(errno.ESRCH, "group gone")
                if state == "denied":
                    raise PermissionError(errno.EPERM, "group inaccessible")

            process.wait.side_effect = reap
            native_os = SimpleNamespace(
                name="posix",
                environ=os.environ,
                killpg=Mock(side_effect=killpg),
                waitid=Mock(
                    return_value=SimpleNamespace(si_status=returncode, si_code=1)
                ),
                P_PID=1,
                WEXITED=4,
                WNOHANG=1,
                WNOWAIT=0x1000000,
                CLD_EXITED=1,
            )
            with (
                patch.object(browser_renderer, "os", native_os),
                patch.object(browser_renderer, "signal", SimpleNamespace(SIGKILL=9)),
                patch.object(
                    browser_renderer.subprocess, "Popen", return_value=process
                ),
                patch.object(
                    browser_renderer.time, "monotonic", side_effect=range(100)
                ),
                patch.object(browser_renderer.time, "sleep"),
            ):
                if wait_timeout:
                    with self.assertRaises(subprocess.TimeoutExpired):
                        browser_renderer._execute_job(job, job, None, 100)
                elif expected_failure:
                    with self.assertRaises(browser_renderer.RendererError) as caught:
                        browser_renderer._execute_job(job, job, None, 100)
                    self.assertEqual(caught.exception.code, "RENDERER_FAILED")
                else:
                    self.assertEqual(
                        browser_renderer._execute_job(job, job, None, 100),
                        (b"", {"scale": 2, "warnings": []}),
                    )
            process.wait.assert_called_once_with(timeout=5)
            process.poll.assert_not_called()
            if not wait_timeout:
                self.assertGreaterEqual(probe_count, 1)


if __name__ == "__main__":
    unittest.main()
