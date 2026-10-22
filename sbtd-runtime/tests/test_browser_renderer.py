"""R2.1b browser renderer: capability, isolation, preflight, route policy.

Traces spec/r2.1b-renderer-scenarios.md. Real Chromium cases use
SBTD_RENDERER_TEST_HOME and skip with the missing dependency when it is unset
or the dedicated runtime is unavailable. They do not delete that install.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import warnings
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from browser_renderer import (
    EXPORT_IMAGE_SIZE_LIMIT,
    JPEG_SCALE_WARNING,
    PLAYWRIGHT_VERSION,
    RENDERER_UNAVAILABLE,
    BrowserRenderer,
    RendererError,
    _allow_request,
    _cjk_font_available,
    _jpeg_scale,
    renderer_capability,
)

_SECRET = "PRIVATE_ALIAS_SHOULD_VANISH"
_PROBE_TOKEN = "PROBE_HTTP_TOKEN_91"
_FILE_TOKEN = "PROBE_FILE_TOKEN_82"
_LATE_TOKEN = "LATE_PANEL_TOKEN_73"
_HEAD_TOKEN = "HEADTOKEN_REPEAT"


def _jpeg_size(payload: bytes) -> tuple[int, int]:
    if payload[:3] != b"\xff\xd8\xff":
        raise AssertionError("not a JPEG")
    index = 2
    while index < len(payload) - 8:
        if payload[index] != 0xFF:
            index += 1
            continue
        marker = payload[index + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            height = int.from_bytes(payload[index + 5 : index + 7], "big")
            width = int.from_bytes(payload[index + 7 : index + 9], "big")
            return width, height
        if marker in (0xD8, 0xD9) or marker == 0x01 or 0xD0 <= marker <= 0xD7:
            index += 2
            continue
        length = int.from_bytes(payload[index + 2 : index + 4], "big")
        if length < 2:
            break
        index += 2 + length
    raise AssertionError("JPEG has no SOF marker")


def _runtime_home() -> Path | None:
    raw = os.environ.get("SBTD_RENDERER_TEST_HOME")
    if not raw:
        return None
    home = Path(raw)
    if not home.is_dir():
        return None
    return home


class _QuietHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.server.hits.append(self.path)  # type: ignore[attr-defined]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"remote-body")

    def do_POST(self) -> None:
        self.do_GET()

    def log_message(self, fmt: str, *args: object) -> None:
        return


class RendererErrorTests(unittest.TestCase):
    def test_constructor_keeps_only_allowlisted_codes(self) -> None:
        allowed = RendererError(RENDERER_UNAVAILABLE)
        self.assertEqual(allowed.code, "RENDERER_UNAVAILABLE")
        self.assertEqual(str(allowed), "RENDERER_UNAVAILABLE")
        leaked = RendererError("/tmp/LEAK_PATH_99")
        self.assertEqual(leaked.code, "RENDERER_FAILED")
        self.assertEqual(str(leaked), "RENDERER_FAILED")
        self.assertNotIn("LEAK_PATH", str(leaked))
        self.assertNotIn("/tmp", str(leaked))
        with self.assertRaises(TypeError):
            RendererError("RENDERER_UNAVAILABLE", "/tmp/extra")  # type: ignore[misc]


class CapabilityTests(unittest.TestCase):
    def test_absent_home_is_unavailable_without_a_path(self) -> None:
        result = renderer_capability(None)
        self.assertEqual(
            result, {"available": False, "reason": "renderer home is required"}
        )

    def test_absent_playwright_is_distinct(self) -> None:
        with mock.patch("browser_renderer._playwright_version", return_value=None):
            result = renderer_capability(Path("/tmp"))
        self.assertEqual(
            result, {"available": False, "reason": "Playwright is not installed"}
        )

    def test_wrong_version_is_not_available_even_with_a_shell(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sbtd-cap-") as temporary:
            home = Path(temporary)
            shell = home / "browsers" / "chromium_headless_shell-1248"
            shell.mkdir(parents=True)
            (shell / "INSTALLATION_COMPLETE").write_text("")
            with mock.patch(
                "browser_renderer._playwright_version", return_value="1.63.0"
            ):
                result = renderer_capability(home)
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "Playwright 1.64.0 is required")
        self.assertNotIn("1248", result["reason"])

    def test_missing_only_shell_is_distinct_from_playwright(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sbtd-cap-") as temporary:
            home = Path(temporary)
            full = home / "browsers" / "chromium-1248"
            full.mkdir(parents=True)
            (full / "INSTALLATION_COMPLETE").write_text("")
            with (
                mock.patch(
                    "browser_renderer._playwright_version",
                    return_value=PLAYWRIGHT_VERSION,
                ),
                mock.patch("browser_renderer._shell_revision", return_value="1248"),
            ):
                result = renderer_capability(home)
        self.assertEqual(
            result,
            {
                "available": False,
                "reason": "Chromium headless shell is not installed",
            },
        )

    def test_symlink_browser_dir_is_not_the_dedicated_install(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sbtd-cap-") as temporary:
            root = Path(temporary)
            home = root / "home"
            home.mkdir()
            cache = root / "user-cache"
            cache.mkdir()
            (home / "browsers").symlink_to(cache, target_is_directory=True)
            with (
                mock.patch(
                    "browser_renderer._playwright_version",
                    return_value=PLAYWRIGHT_VERSION,
                ),
                mock.patch("browser_renderer._shell_revision", return_value="1248"),
            ):
                result = renderer_capability(home)
        self.assertEqual(result["reason"], "Chromium headless shell is not installed")

    def test_missing_cjk_font_is_distinct(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sbtd-cap-") as temporary:
            home = Path(temporary)
            with (
                mock.patch(
                    "browser_renderer._playwright_version",
                    return_value=PLAYWRIGHT_VERSION,
                ),
                mock.patch(
                    "browser_renderer._shell_executable",
                    return_value=home / "browsers" / "shell",
                ),
                mock.patch("browser_renderer._cjk_font_available", return_value=False),
            ):
                result = renderer_capability(home)
        self.assertEqual(
            result, {"available": False, "reason": "CJK font is not installed"}
        )

    def test_ready_runtime_reports_available(self) -> None:
        with (
            mock.patch(
                "browser_renderer._playwright_version",
                return_value=PLAYWRIGHT_VERSION,
            ),
            mock.patch(
                "browser_renderer._shell_executable",
                return_value=Path("/dedicated/shell"),
            ),
            mock.patch("browser_renderer._cjk_font_available", return_value=True),
        ):
            result = renderer_capability(Path("/dedicated"))
        self.assertEqual(result, {"available": True, "reason": None})
        self.assertEqual(set(result), {"available", "reason"})

    def test_fc_match_rejects_non_cjk_fallback(self) -> None:
        def family(name: str, _timeout: float) -> str:
            if name == "Noto Sans CJK SC":
                return "Noto Sans"
            return "Noto Sans CJK JP"

        with mock.patch("browser_renderer._fc_match_family", side_effect=family):
            self.assertFalse(_cjk_font_available())

    def test_fc_match_accepts_actual_cjk_families(self) -> None:
        with mock.patch(
            "browser_renderer._fc_match_family",
            side_effect=lambda name, _timeout: name,
        ):
            if os.name != "posix":
                self.skipTest("CJK fc-match check is Linux-specific")
            # The helper itself is platform-gated; force the Linux branch.
            with mock.patch("browser_renderer.platform.system", return_value="Linux"):
                self.assertTrue(_cjk_font_available())


class PreflightTests(unittest.TestCase):
    def test_short_page_stays_at_2x(self) -> None:
        scale, warning = _jpeg_scale(1440, 1000)
        self.assertEqual(scale, 2)
        self.assertIsNone(warning)
        scale, warning = _jpeg_scale(1440, 13888)
        self.assertEqual(scale, 2)
        self.assertIsNone(warning)
        scale, warning = _jpeg_scale(16000, 10)
        self.assertEqual(scale, 2)
        self.assertIsNone(warning)

    def test_2x_over_limit_falls_back_to_1x_with_warning(self) -> None:
        scale, warning = _jpeg_scale(1440, 13889)
        self.assertEqual((scale, warning), (1, JPEG_SCALE_WARNING))
        scale, warning = _jpeg_scale(1440, 16000)
        self.assertEqual(scale, 1)
        self.assertEqual(warning, JPEG_SCALE_WARNING)
        scale, warning = _jpeg_scale(16001, 10)
        self.assertEqual(scale, 1)
        scale, warning = _jpeg_scale(32000, 2500)
        self.assertEqual(scale, 1)
        scale, warning = _jpeg_scale(10000, 8000)
        self.assertEqual(scale, 1)

    def test_downgrade_never_uses_less_than_standard_width(self) -> None:
        with self.assertRaises(RendererError) as caught:
            _jpeg_scale(1439, 16001)
        self.assertEqual(caught.exception.code, EXPORT_IMAGE_SIZE_LIMIT)

    def test_1x_over_limit_is_a_safe_size_error(self) -> None:
        for width, height in (
            (1440, 32001),
            (1440, 55555),
            (32001, 10),
            (100, 800001),
            (0, 10),
            (-1, 10),
        ):
            with self.subTest(width=width, height=height):
                with self.assertRaises(RendererError) as caught:
                    _jpeg_scale(width, height)
                self.assertEqual(caught.exception.code, "EXPORT_IMAGE_SIZE_LIMIT")
                self.assertEqual(str(caught.exception), "EXPORT_IMAGE_SIZE_LIMIT")
                self.assertNotIn("/", str(caught.exception))


class IsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="sbtd-browser-unit-")
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "home"
        self.home.mkdir()
        browsers = self.home / "browsers"
        browsers.mkdir()
        (browsers / "keep").write_text("install")

    def test_parent_io_failure_is_a_safe_library_error(self) -> None:
        with (
            mock.patch(
                "browser_renderer.renderer_capability",
                return_value={"available": True, "reason": None},
            ),
            mock.patch("browser_renderer.render_export", return_value=(b"<html/>", {})),
            mock.patch(
                "browser_renderer._write_job",
                side_effect=OSError("disk full /private/profile/report.html"),
            ),
            self.assertRaises(RendererError) as caught,
        ):
            BrowserRenderer(self.home, object())(object(), "pdf", None, lambda: False)
        self.assertEqual(str(caught.exception), "RENDERER_FAILED")
        self.assertIsNone(caught.exception.__cause__)

    def test_preparation_time_counts_against_job_deadline(self) -> None:
        def slow_capability(*_args, **_kwargs):
            time.sleep(0.03)
            return {"available": True, "reason": None}

        with (
            mock.patch(
                "browser_renderer.renderer_capability", side_effect=slow_capability
            ),
            mock.patch(
                "browser_renderer.render_export",
                side_effect=AssertionError("expired job generated a source"),
            ),
            self.assertRaises(RendererError) as caught,
        ):
            BrowserRenderer(self.home, object(), timeout_seconds=0.01)(
                object(), "pdf", None, lambda: False
            )
        self.assertEqual(str(caught.exception), "RENDERER_TIMEOUT")

    def test_cancel_at_acquisition_does_not_leak_the_global_slot(self) -> None:
        from browser_renderer import _render_document

        slot = threading.BoundedSemaphore(1)
        calls = 0

        def cancellation():
            nonlocal calls
            calls += 1
            if calls == 3:
                raise RendererError("RENDERER_CANCELLED")
            return False

        with (
            mock.patch("browser_renderer._JOB_SEMAPHORE", slot),
            self.assertRaises(RendererError) as caught,
        ):
            _render_document(
                "<html/>",
                "pdf",
                home=self.home,
                cancelled=cancellation,
                presentation=None,
            )
        self.assertEqual(caught.exception.code, "RENDERER_CANCELLED")
        self.assertTrue(slot.acquire(blocking=False), "next job lost the global slot")
        slot.release()

    def _ready(self):
        return (
            mock.patch(
                "browser_renderer._playwright_version",
                return_value=PLAYWRIGHT_VERSION,
            ),
            mock.patch(
                "browser_renderer._shell_executable",
                return_value=self.home / "browsers" / "shell",
            ),
            mock.patch("browser_renderer._cjk_font_available", return_value=True),
        )

    def test_route_policy_allows_only_one_main_document(self) -> None:
        main = "https://sbtd-export.invalid/report"
        self.assertTrue(
            _allow_request(
                main,
                resource_type="document",
                is_navigation=True,
                is_main_frame=True,
                already_fulfilled=False,
            )
        )
        denied = (
            (main, "document", True, True, True),
            ("http://127.0.0.1/pixel.png", "image", False, True, False),
            ("https://example.test/steal", "fetch", False, True, False),
            ("file:///etc/passwd", "document", True, True, False),
            (main, "document", True, False, False),
            (main + "?next=file", "document", True, True, False),
            ("data:,", "image", False, True, False),
            ("javascript:alert(1)", "document", True, True, False),
            ("blob:https://sbtd-export.invalid/1", "document", True, True, False),
        )
        for url, kind, navigation, main_frame, fulfilled in denied:
            with self.subTest(url=url, kind=kind, fulfilled=fulfilled):
                self.assertFalse(
                    _allow_request(
                        url,
                        resource_type=kind,
                        is_navigation=navigation,
                        is_main_frame=main_frame,
                        already_fulfilled=fulfilled,
                    )
                )

    def test_absent_home_fails_safe(self) -> None:
        renderer = BrowserRenderer(None, object())
        with self.assertRaises(RendererError) as caught:
            renderer(object(), "jpeg", None, lambda: False)
        self.assertEqual(caught.exception.code, "RENDERER_UNAVAILABLE")
        self.assertNotIn("Traceback", str(caught.exception))

    def test_semaphore_serializes_and_cancel_does_not_start_the_waiter(self) -> None:
        entered = []
        release_first = threading.Event()
        started = threading.Event()

        def hold(*_args, **_kwargs):
            entered.append("run")
            started.set()
            self.assertTrue(release_first.wait(2))
            return b"\xff\xd8\xff\x00", {"warnings": []}

        patches = self._ready()
        with (
            patches[0],
            patches[1],
            patches[2],
            mock.patch("browser_renderer._execute_job", side_effect=hold),
        ):
            first_done = threading.Event()
            errors: list[BaseException] = []

            def first() -> None:
                try:
                    from browser_renderer import _render_document

                    _render_document(
                        "<html></html>",
                        "jpeg",
                        home=self.home,
                        cancelled=lambda: False,
                        presentation=None,
                        timeout_seconds=5,
                    )
                except BaseException as exc:  # noqa: BLE001
                    errors.append(exc)
                finally:
                    first_done.set()

            thread = threading.Thread(target=first)
            thread.start()
            self.assertTrue(started.wait(2))
            cancelled = {"stop": False}

            def second() -> None:
                try:
                    from browser_renderer import _render_document

                    _render_document(
                        "<html></html>",
                        "jpeg",
                        home=self.home,
                        cancelled=lambda: cancelled["stop"],
                        presentation=None,
                        timeout_seconds=5,
                    )
                except BaseException as exc:  # noqa: BLE001
                    errors.append(exc)

            waiter = threading.Thread(target=second)
            waiter.start()
            time.sleep(0.15)
            self.assertEqual(entered, ["run"])
            cancelled["stop"] = True
            waiter.join(2)
            self.assertFalse(waiter.is_alive())
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], RendererError)
            self.assertEqual(errors[0].code, "RENDERER_CANCELLED")
            release_first.set()
            thread.join(2)
            self.assertTrue(first_done.is_set())
            self.assertFalse(thread.is_alive())

    def test_timeout_includes_semaphore_wait(self) -> None:
        release_first = threading.Event()
        started = threading.Event()

        def hold(*_args, **_kwargs):
            started.set()
            release_first.wait(2)
            return b"%PDF-1.4", {"warnings": []}

        patches = self._ready()
        with (
            patches[0],
            patches[1],
            patches[2],
            mock.patch("browser_renderer._execute_job", side_effect=hold),
        ):
            from browser_renderer import _render_document

            def first() -> None:
                _render_document(
                    "<html></html>",
                    "pdf",
                    home=self.home,
                    cancelled=lambda: False,
                    presentation=None,
                    timeout_seconds=5,
                )

            thread = threading.Thread(target=first)
            thread.start()
            self.assertTrue(started.wait(2))
            started_wait = time.monotonic()
            with self.assertRaises(RendererError) as caught:
                _render_document(
                    "<html></html>",
                    "pdf",
                    home=self.home,
                    cancelled=lambda: False,
                    presentation=None,
                    timeout_seconds=0.2,
                )
            elapsed = time.monotonic() - started_wait
            self.assertEqual(caught.exception.code, "RENDERER_TIMEOUT")
            self.assertLess(elapsed, 1.5)
            release_first.set()
            thread.join(2)

    def test_timeout_kills_descendants_and_deletes_profile(self) -> None:
        self._assert_process_cleanup(crash=False)

    def test_worker_crash_kills_surviving_descendants(self) -> None:
        self._assert_process_cleanup(crash=True)

    def _assert_process_cleanup(self, *, crash: bool) -> None:
        if not hasattr(os, "fork"):
            self.skipTest("POSIX fork is unavailable")
        pid_file = Path(self.temporary.name) / "child.pid"
        secret = "STDERR_LEAK_/tmp/should-not-surface"
        script = (
            "import json, os, pathlib, sys, time\n"
            "job = pathlib.Path(sys.argv[1])\n"
            "spec = json.loads((job / 'request.json').read_text())\n"
            "profile = pathlib.Path(spec['profile'])\n"
            "(profile / 'marker').write_text('held')\n"
            "pid = os.fork()\n"
            "if pid == 0:\n"
            "    time.sleep(30)\n"
            "    os._exit(0)\n"
            f"pathlib.Path({str(pid_file)!r}).write_text(str(pid))\n"
            f"print({secret!r}, file=sys.stderr)\n"
            + ("os._exit(1)\n" if crash else "time.sleep(30)\n")
        )
        profiles: list[Path] = []
        real_make = __import__("browser_renderer")._make_profile

        def track() -> Path:
            path = real_make()
            profiles.append(path)
            return path

        patches = self._ready()
        with (
            patches[0],
            patches[1],
            patches[2],
            mock.patch("browser_renderer._make_profile", side_effect=track),
            mock.patch(
                "browser_renderer._worker_argv",
                side_effect=lambda job: [sys.executable, "-c", script, str(job)],
            ),
        ):
            from browser_renderer import _render_document

            with self.assertRaises(RendererError) as caught:
                _render_document(
                    "<html><body>report</body></html>",
                    "jpeg",
                    home=self.home,
                    cancelled=lambda: False,
                    presentation=None,
                    timeout_seconds=1.2,
                )
        self.assertEqual(
            caught.exception.code, "RENDERER_FAILED" if crash else "RENDERER_TIMEOUT"
        )
        self.assertNotIn("STDERR_LEAK", str(caught.exception))
        self.assertNotIn("should-not-surface", str(caught.exception))
        self.assertTrue(profiles)
        self.assertFalse(profiles[-1].exists())
        self.assertTrue((self.home / "browsers" / "keep").is_file())
        self.assertTrue(pid_file.is_file())
        child = int(pid_file.read_text())

        def reap_probe() -> None:
            try:
                os.kill(child, 9)
            except ProcessLookupError:
                pass

        self.addCleanup(reap_probe)
        with self.assertRaises(ProcessLookupError):
            os.kill(child, 0)

    def test_cancel_stops_the_job_process_and_deletes_profile(self) -> None:
        if not hasattr(os, "fork"):
            self.skipTest("POSIX fork is unavailable")
        pid_file = Path(self.temporary.name) / "cancel-child.pid"
        script = (
            "import json, os, pathlib, sys, time\n"
            "job = pathlib.Path(sys.argv[1])\n"
            "spec = json.loads((job / 'request.json').read_text())\n"
            "profile = pathlib.Path(spec['profile'])\n"
            "(profile / 'marker').write_text('held')\n"
            "pid = os.fork()\n"
            "if pid == 0:\n"
            "    time.sleep(30)\n"
            "    os._exit(0)\n"
            f"pathlib.Path({str(pid_file)!r}).write_text(str(pid))\n"
            "time.sleep(30)\n"
        )
        profiles: list[Path] = []
        real_make = __import__("browser_renderer")._make_profile

        def track() -> Path:
            path = real_make()
            profiles.append(path)
            return path

        flag = {"stop": False}

        def watch() -> None:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if pid_file.exists():
                    flag["stop"] = True
                    return
                time.sleep(0.02)

        patches = self._ready()
        with (
            patches[0],
            patches[1],
            patches[2],
            mock.patch("browser_renderer._make_profile", side_effect=track),
            mock.patch(
                "browser_renderer._worker_argv",
                side_effect=lambda job: [sys.executable, "-c", script, str(job)],
            ),
        ):
            from browser_renderer import _render_document

            threading.Thread(target=watch, daemon=True).start()
            with self.assertRaises(RendererError) as caught:
                _render_document(
                    "<html></html>",
                    "pdf",
                    home=self.home,
                    cancelled=lambda: flag["stop"],
                    presentation=None,
                    timeout_seconds=5,
                )
        self.assertEqual(caught.exception.code, "RENDERER_CANCELLED")
        self.assertFalse(profiles[-1].exists())
        self.assertTrue((self.home / "browsers" / "keep").is_file())
        child = int(pid_file.read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(child, 0)

    def test_worker_path_code_is_not_echoed(self) -> None:
        script = (
            "import json, pathlib, sys\n"
            "job = pathlib.Path(sys.argv[1])\n"
            "(job / 'error.json').write_text("
            "json.dumps({'code': '/tmp/LEAK_PATH_99'}))\n"
            "raise SystemExit(1)\n"
        )
        patches = self._ready()
        with (
            patches[0],
            patches[1],
            patches[2],
            mock.patch(
                "browser_renderer._worker_argv",
                side_effect=lambda job: [sys.executable, "-c", script, str(job)],
            ),
        ):
            from browser_renderer import _render_document

            with self.assertRaises(RendererError) as caught:
                _render_document(
                    "<html></html>",
                    "jpeg",
                    home=self.home,
                    cancelled=lambda: False,
                    presentation=None,
                    timeout_seconds=5,
                )
        self.assertEqual(caught.exception.code, "RENDERER_FAILED")
        self.assertNotIn("LEAK_PATH", str(caught.exception))
        self.assertNotIn("/tmp", str(caught.exception))

    def test_success_uses_a_fresh_profile_and_leaves_the_install(self) -> None:
        profiles: list[Path] = []
        real_make = __import__("browser_renderer")._make_profile

        def track() -> Path:
            path = real_make()
            profiles.append(path)
            (path / "job-file").write_text("x")
            return path

        def succeed(*_args):
            return b"\xff\xd8\xffok", {"warnings": []}

        patches = self._ready()
        with (
            patches[0],
            patches[1],
            patches[2],
            mock.patch("browser_renderer._make_profile", side_effect=track),
            mock.patch("browser_renderer._execute_job", side_effect=succeed),
        ):
            from browser_renderer import _render_document

            _render_document(
                "<html><body>report-body</body></html>",
                "jpeg",
                home=self.home,
                cancelled=lambda: False,
                presentation=None,
                timeout_seconds=5,
            )
            _render_document(
                "<html><body>report-body</body></html>",
                "jpeg",
                home=self.home,
                cancelled=lambda: False,
                presentation=None,
                timeout_seconds=5,
            )
        self.assertEqual(len(profiles), 2)
        self.assertNotEqual(profiles[0], profiles[1])
        for path in profiles:
            self.assertFalse(path.exists())
            self.assertFalse(str(path).startswith(str(self.home / "browsers")))
        self.assertTrue((self.home / "browsers" / "keep").is_file())


class RealBrowserTests(unittest.TestCase):
    def setUp(self) -> None:
        home = _runtime_home()
        if home is None:
            self.skipTest(
                "SBTD_RENDERER_TEST_HOME is unset; real Chromium tests skipped"
            )
        self.home = home
        capability = renderer_capability(home)
        if not capability["available"]:
            self.skipTest(f"renderer unavailable: {capability['reason']}")
        self.install = home / "browsers"
        self.marker = (
            self.install / "chromium_headless_shell-1248" / "INSTALLATION_COMPLETE"
        )
        if not self.marker.is_file():
            self.skipTest("dedicated headless shell marker is missing")
        self.marker_stat = self.marker.stat()

    def tearDown(self) -> None:
        if getattr(self, "marker", None) and self.marker.exists():
            current = self.marker.stat()
            self.assertEqual(current.st_size, self.marker_stat.st_size)
            self.assertTrue(stat.S_ISREG(current.st_mode))

    def test_route_abort_fresh_profiles_and_jpeg_2x(self) -> None:
        from browser_renderer import _make_profile, _render_document

        server = ThreadingHTTPServer(("127.0.0.1", 0), _QuietHandler)
        server.hits = []
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        canary = Path(self.temporary_canary())
        http_url = f"http://127.0.0.1:{port}/pixel.png"
        fetch_url = f"http://127.0.0.1:{port}/steal"
        file_url = canary.as_uri()
        html = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<title>SBTD 报告</title></head><body>"
            f"<p>{_PROBE_TOKEN} 中文日本語 English</p>"
            "<div style='height:1200px'>tall</div>"
            f"<img src='{http_url}'>"
            f"<iframe src='{file_url}'></iframe>"
            f"<iframe src='http://127.0.0.1:{port}/frame'></iframe>"
            "<script>"
            f"fetch({fetch_url!r}).catch(() => {{}});"
            "</script></body></html>"
        )
        profiles: list[Path] = []
        real = _make_profile

        def track() -> Path:
            path = real()
            profiles.append(path)
            return path

        with mock.patch("browser_renderer._make_profile", side_effect=track):
            jpeg, jpeg_meta = _render_document(
                html,
                "jpeg",
                home=Path(os.path.relpath(self.home)),
                cancelled=lambda: False,
                presentation={"theme": "dark"},
                timeout_seconds=60,
            )
            pdf, pdf_meta = _render_document(
                html,
                "pdf",
                home=self.home,
                cancelled=lambda: False,
                presentation={"theme": "dark"},
                timeout_seconds=60,
            )
        self.assertEqual(server.hits, [])
        self.assertGreaterEqual(len(profiles), 2)
        self.assertNotEqual(profiles[0], profiles[1])
        for path in profiles:
            self.assertFalse(path.exists())
        self.assertTrue(self.install.is_dir())
        aborted = set(jpeg_meta.get("aborted_urls") or []) | set(
            pdf_meta.get("aborted_urls") or []
        )
        self.assertIn(http_url, aborted)
        self.assertIn(fetch_url, aborted)
        width, height = _jpeg_size(jpeg)
        self.assertEqual(width, 2880)
        self.assertGreater(height, 1800)
        self.assertTrue(pdf.startswith(b"%PDF"))
        # Chromium blocks HTTPS -> file before Playwright routing. Check the
        # searchable output, not compressed PDF bytes, for the file canary.
        if shutil.which("pdftotext"):
            with tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / "probe.pdf"
                path.write_bytes(pdf)
                text = subprocess.check_output(["pdftotext", str(path), "-"])
                self.assertNotIn(_FILE_TOKEN.encode(), text)
        self.assertNotIn(b"sbtd-export.invalid", pdf)
        self.assertNotIn(str(self.home).encode(), pdf)

    def temporary_canary(self) -> str:
        with tempfile.NamedTemporaryFile(
            prefix="sbtd-canary-", suffix=".txt", delete=False
        ) as handle:
            handle.write(_FILE_TOKEN.encode())
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return handle.name

    def test_real_jpeg_downgrades_without_truncation_and_rejects_oversize(self) -> None:
        from browser_renderer import _render_document

        def document(height):
            return (
                "<html><head><style>body {margin:0}</style></head><body>"
                f"<article class='report' style='height:{height}px'>"
                "中文 Full page</article></body></html>"
            )

        payload, metadata = _render_document(
            document(31999),
            "jpeg",
            home=self.home,
            cancelled=lambda: False,
            presentation={"theme": "light"},
        )
        self.assertEqual(_jpeg_size(payload), (1440, 31999))
        self.assertIn(JPEG_SCALE_WARNING, metadata["warnings"])
        with self.assertRaises(RendererError) as caught:
            _render_document(
                document(32001),
                "jpeg",
                home=self.home,
                cancelled=lambda: False,
                presentation={"theme": "light"},
            )
        self.assertEqual(caught.exception.code, EXPORT_IMAGE_SIZE_LIMIT)

        # Wide intrinsic content must also be measured, not assumed to fit
        # the 1440 CSS-pixel viewport.
        payload, metadata = _render_document(
            '<html><body style="margin:0"><div style="width:16001px;height:10px">'
            "Wide</div></body></html>",
            "jpeg",
            home=self.home,
            cancelled=lambda: False,
            presentation={},
        )
        self.assertEqual(_jpeg_size(payload)[0], 16001)
        self.assertLessEqual(max(_jpeg_size(payload)), 32000)
        self.assertIn(JPEG_SCALE_WARNING, metadata["warnings"])

    def test_configured_limits_and_notice_apply_before_capture(self) -> None:
        from browser_renderer import _make_job_dir, _render_document

        document = (
            "<html><body style='margin:0'>"
            "<article class='report' style='height:1000px'>"
            "完整中文 Full page</article></body></html>"
        )
        jobs = []
        notices = []
        worker = (
            "import sys\n"
            f"sys.path.insert(0, {str(ROOT)!r})\n"
            "from pathlib import Path\n"
            "from playwright.sync_api import Page\n"
            "from browser_renderer import _worker_entry\n"
            "job = Path(sys.argv[1])\n"
            "original = Page.screenshot\n"
            "def capture(self, **kwargs):\n"
            "    (job / 'capture-started').touch()\n"
            "    return original(self, **kwargs)\n"
            "Page.screenshot = capture\n"
            "sys.exit(_worker_entry(str(job)))\n"
        )

        def track_job():
            job = _make_job_dir()
            jobs.append(job)
            return job

        def notice(message, *_args, **_kwargs):
            notices.append(str(message))
            self.assertFalse((jobs[-1] / "result.bin").exists())
            self.assertFalse((jobs[-1] / "capture-started").exists())
            # Rejecting the notice must stop capture, not just publication.
            raise RuntimeWarning(str(message))

        with (
            mock.patch("browser_renderer._make_job_dir", side_effect=track_job),
            mock.patch("browser_renderer.MAX_PIXELS", 2_000_000),
            mock.patch(
                "browser_renderer._worker_argv",
                side_effect=lambda job: [sys.executable, "-c", worker, str(job)],
            ),
            warnings.catch_warnings(),
        ):
            warnings.simplefilter("always")
            with (
                mock.patch("warnings.showwarning", side_effect=notice),
                self.assertRaises(RuntimeWarning),
            ):
                _render_document(
                    document,
                    "jpeg",
                    home=self.home,
                    cancelled=lambda: False,
                    presentation={},
                )
            self.assertEqual(notices, [JPEG_SCALE_WARNING])
            self.assertFalse(jobs[-1].exists())
            with warnings.catch_warnings(record=True) as caught:
                payload, metadata = _render_document(
                    document,
                    "jpeg",
                    home=self.home,
                    cancelled=lambda: False,
                    presentation={},
                )
            self.assertEqual(
                [str(item.message) for item in caught], [JPEG_SCALE_WARNING]
            )
            self.assertEqual(_jpeg_size(payload), (1440, 1000))
            self.assertIn(JPEG_SCALE_WARNING, metadata["warnings"])

        with mock.patch("browser_renderer.MAX_SIDE_PX", 1439):
            with self.assertRaises(RendererError) as caught:
                _render_document(
                    document,
                    "jpeg",
                    home=self.home,
                    cancelled=lambda: False,
                    presentation={},
                )
            self.assertEqual(caught.exception.code, EXPORT_IMAGE_SIZE_LIMIT)

    def test_pdf_is_searchable_a3_with_embedded_cjk(self) -> None:
        missing = [
            name
            for name in ("pdftotext", "pdffonts", "pdfinfo")
            if shutil.which(name) is None
        ]
        if missing:
            self.skipTest("missing PDF tools: " + ", ".join(missing))
        from browser_renderer import _render_document

        rows = "".join(
            "<tr style='height:28px'><td>ROW-"
            f"{index:03d}</td><td>padding text for height</td></tr>"
            for index in range(80)
        )
        html = (
            "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
            "<title>SBTD 报告</title></head><body>"
            "<h1>SBTD 报告</h1>"
            "<p>范围：2026-01-01T00:00:00Z → 2026-02-01T00:00:00Z（Asia/Shanghai）</p>"
            "<p>数据水位：2026-02-01T00:00:00Z（快照 "
            "snap_abcdef0123456789abcdef0123456789，watermark_seq 3）</p>"
            "<section class='panel'><h2>质量</h2><p>中文日本語 English</p>"
            f"<p>{_LATE_TOKEN}</p></section>"
            "<table><thead><tr><th>"
            f"{_HEAD_TOKEN}</th><th>状态</th></tr></thead><tbody>{rows}</tbody></table>"
            "</body></html>"
        )
        pdf, _meta = _render_document(
            html,
            "pdf",
            home=self.home,
            cancelled=lambda: False,
            presentation={"theme": "light"},
            timeout_seconds=60,
        )
        self.assertTrue(pdf.startswith(b"%PDF"))
        with tempfile.TemporaryDirectory(prefix="sbtd-pdf-") as temporary:
            path = Path(temporary) / "report.pdf"
            path.write_bytes(pdf)
            info = subprocess.run(
                ["pdfinfo", str(path)],
                check=True,
                capture_output=True,
                text=True,
            )
            text = subprocess.run(
                ["pdftotext", "-layout", str(path), "-"],
                check=True,
                capture_output=True,
                text=True,
            )
            fonts = subprocess.run(
                ["pdffonts", str(path)],
                check=True,
                capture_output=True,
                text=True,
            )
        page_line = next(
            line for line in info.stdout.splitlines() if line.startswith("Page size:")
        )
        width_text, height_text = page_line.split(":", 1)[1].strip().split(" x ", 1)
        width = float(width_text)
        height = float(height_text.split()[0])
        self.assertGreater(width, height)
        self.assertAlmostEqual(width, 1190.55, delta=2)
        self.assertAlmostEqual(height, 841.89, delta=2)
        extracted = text.stdout
        self.assertIn("中文", extracted)
        self.assertIn("日本語", extracted)
        self.assertIn("English", extracted)
        self.assertGreaterEqual("".join(extracted.split()).count("SBTD报告"), 2)
        self.assertGreaterEqual(extracted.count("2026-01-01T00:00:00Z"), 2)
        self.assertGreaterEqual(extracted.count("Asia/Shanghai"), 2)
        self.assertGreaterEqual(extracted.count("snap_abcdef01"), 2)
        self.assertRegex(extracted, r"\d+\s*/\s*\d+")
        self.assertIn(_LATE_TOKEN, extracted)
        self.assertGreaterEqual(extracted.count(_HEAD_TOKEN), 2)
        self.assertIn("ROW-000", extracted)
        self.assertIn("ROW-079", extracted)
        embedded = [
            line
            for line in fonts.stdout.splitlines()
            if "CJK" in line or "NotoSansCJK" in line or "Noto Sans CJK" in line
        ]
        self.assertTrue(embedded, fonts.stdout)
        self.assertTrue(
            any("yes" in line.lower() or "yes" in line for line in embedded)
        )


if __name__ == "__main__":
    unittest.main()
