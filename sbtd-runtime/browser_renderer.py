"""Optional JPEG and PDF rendering for one frozen report.

HTML and CSV do not use this module. JPEG and PDF render only the HTML
produced by ``export_render.render_export``. There is no public URL or raw
HTML entry. Playwright 1.64.0 and its headless shell live under
``home/browsers``; the expected CJK package is
``fonts-noto-cjk=1:20240730+repack1-1``. Availability is
``renderer_capability`` only.
"""

from __future__ import annotations

import html
import json
import math
import os
import platform
import select
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import warnings
from pathlib import Path
from typing import Any

from export_render import render_export

PLAYWRIGHT_VERSION = "1.64.0"
BROWSER_RENDERER_VERSION = "r2.1b.1"
JPEG_WIDTH = 1440
JPEG_QUALITY = 90
# PRD suggested, freeze after measurement (建议值，实测后冻结).
# Configure these module constants before submitting jobs; each worker gets a copy.
MAX_SIDE_PX = 32000
MAX_PIXELS = 80_000_000
JPEG_SCALE_WARNING = "EXPORT_SCALE_DOWNGRADED:1x"
DEFAULT_TIMEOUT_SECONDS = 60.0
RENDERER_UNAVAILABLE = "RENDERER_UNAVAILABLE"
EXPORT_IMAGE_SIZE_LIMIT = "EXPORT_IMAGE_SIZE_LIMIT"
RENDERER_TIMEOUT = "RENDERER_TIMEOUT"
RENDERER_FAILED = "RENDERER_FAILED"
RENDERER_CANCELLED = "RENDERER_CANCELLED"
_CODES = frozenset(
    {
        RENDERER_UNAVAILABLE,
        EXPORT_IMAGE_SIZE_LIMIT,
        RENDERER_TIMEOUT,
        RENDERER_FAILED,
        RENDERER_CANCELLED,
    }
)
_REASONS = {
    "home": "renderer home is required",
    "playwright": "Playwright is not installed",
    "version": "Playwright 1.64.0 is required",
    "shell": "Chromium headless shell is not installed",
    "font": "CJK font is not installed",
}
_MAIN_URL = "https://sbtd-export.invalid/report"
_FONT_STACK = (
    '"Noto Sans CJK SC", "Noto Sans CJK JP", "Noto Sans CJK TC", '
    '"Noto Sans CJK KR", "PingFang SC", "Hiragino Sans GB", '
    '"Microsoft YaHei", sans-serif'
)
_CHROMIUM_ARGS = (
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-breakpad",
    "--disable-client-side-phishing-detection",
    "--hide-scrollbars",
    "--disable-component-extensions-with-background-pages",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-dev-shm-usage",
    "--disable-domain-reliability",
    "--disable-extensions",
    "--disable-features=Translate,BackForwardCache,MediaRouter,OptimizationHints,DialMediaRouteProvider",
    "--disable-hang-monitor",
    "--disable-renderer-backgrounding",
    "--disable-sync",
    "--disable-translate",
    "--metrics-recording-only",
    "--no-default-browser-check",
    "--no-first-run",
    "--no-pings",
    "--safebrowsing-disable-auto-update",
)
_JOB_SEMAPHORE = threading.BoundedSemaphore(1)


class RendererError(Exception):
    """Library failure. ``code`` and ``str(exc)`` are the same allowlisted token."""

    def __init__(
        self,
        code: str = RENDERER_FAILED,
        *,
        max_edge_px: int | None = None,
        max_total_pixels: int | None = None,
    ) -> None:
        if type(code) is not str or code not in _CODES:
            code = RENDERER_FAILED
        self.code = code
        if code == EXPORT_IMAGE_SIZE_LIMIT:
            self.max_edge_px = MAX_SIDE_PX if max_edge_px is None else max_edge_px
            self.max_total_pixels = (
                MAX_PIXELS if max_total_pixels is None else max_total_pixels
            )
        super().__init__(code)


def renderer_capability(home: Any, *, timeout_seconds: float = 10) -> dict[str, Any]:
    """Return only ``available`` and a stable ``reason``."""
    reason = _unavailable_reason(home, timeout_seconds)
    if reason is None:
        return {"available": True, "reason": None}
    return {"available": False, "reason": reason}


def _unavailable_reason(home: Any, timeout_seconds: float) -> str | None:
    path = _home_path(home)
    if path is None:
        return _REASONS["home"]
    version = _playwright_version()
    if version is None:
        return _REASONS["playwright"]
    if version != PLAYWRIGHT_VERSION:
        return _REASONS["version"]
    if _shell_executable(path) is None:
        return _REASONS["shell"]
    if not _cjk_font_available(timeout_seconds):
        return _REASONS["font"]
    return None


def _home_path(home: Any) -> Path | None:
    if home is None:
        return None
    if isinstance(home, Path):
        return home.absolute()
    if isinstance(home, str) and home:
        return Path(home).absolute()
    return None


def _playwright_version() -> str | None:
    try:
        from importlib.metadata import PackageNotFoundError, version
    except ImportError:
        return None
    try:
        return version("playwright")
    except PackageNotFoundError:
        return None


def _shell_revision() -> str | None:
    if _playwright_version() != PLAYWRIGHT_VERSION:
        return None
    try:
        import playwright
    except ImportError:
        return None
    registry = (
        Path(playwright.__file__).resolve().parent
        / "driver"
        / "package"
        / "browsers.json"
    )
    try:
        payload = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for item in payload.get("browsers") or []:
        if not isinstance(item, dict) or item.get("name") != "chromium-headless-shell":
            continue
        revision = item.get("revision")
        if type(revision) is int:
            revision = str(revision)
        if isinstance(revision, str) and revision.isdigit():
            return revision
    return None


def _shell_relative() -> tuple[str, str] | None:
    machine = platform.machine().lower()
    system = platform.system()
    arm = machine in {"aarch64", "arm64"}
    if system == "Linux":
        folder = (
            "chrome-headless-shell-linux-arm64"
            if arm
            else "chrome-headless-shell-linux64"
        )
        return folder, "chrome-headless-shell"
    if system == "Darwin":
        folder = (
            "chrome-headless-shell-mac-arm64"
            if arm
            else "chrome-headless-shell-mac-x64"
        )
        return folder, "chrome-headless-shell"
    if system == "Windows":
        return "chrome-headless-shell-win64", "chrome-headless-shell.exe"
    return None


def _shell_executable(home: Path) -> Path | None:
    revision = _shell_revision()
    relative = _shell_relative()
    if revision is None or relative is None:
        return None
    browsers = home / "browsers"
    if not _real_dir(browsers):
        return None
    directory = browsers / f"chromium_headless_shell-{revision}"
    if not _real_dir(directory) or not _real_file(directory / "INSTALLATION_COMPLETE"):
        return None
    executable = directory.joinpath(*relative)
    if not _real_file(executable) or not os.access(executable, os.X_OK):
        return None
    try:
        executable.resolve().relative_to(browsers.resolve())
    except (OSError, ValueError):
        return None
    return executable


def _real_dir(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)


def _real_file(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode)


def _fc_match_family(family: str, timeout_seconds: float = 5) -> str | None:
    try:
        result = subprocess.run(
            ["fc-match", "-f", "%{family}", family],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _cjk_font_available(timeout_seconds: float = 10) -> bool:
    if platform.system() == "Linux":
        deadline = time.monotonic() + timeout_seconds
        for family in ("Noto Sans CJK SC", "Noto Sans CJK JP"):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            matched = _fc_match_family(family, min(5, remaining))
            if not matched or "CJK" not in matched:
                return False
        return True
    return _platform_cjk_files()


def _platform_cjk_files() -> bool:
    system = platform.system()
    if system == "Darwin":
        candidates = (
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
        )
    elif system == "Windows":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        candidates = (
            str(Path(windir) / "Fonts" / "msyh.ttc"),
            str(Path(windir) / "Fonts" / "msyh.ttf"),
            str(Path(windir) / "Fonts" / "simsun.ttc"),
        )
    else:
        return False
    return any(_real_file(Path(path)) for path in candidates)


def _jpeg_scale(css_width: int, css_height: int) -> tuple[int, str | None]:
    if type(css_width) is not int or type(css_height) is not int:
        raise RendererError(EXPORT_IMAGE_SIZE_LIMIT)
    if css_width < 1 or css_height < 1:
        raise RendererError(EXPORT_IMAGE_SIZE_LIMIT)
    if not _exceeds(css_width, css_height, 2):
        return 2, None
    if css_width >= JPEG_WIDTH and not _exceeds(css_width, css_height, 1):
        return 1, JPEG_SCALE_WARNING
    raise RendererError(EXPORT_IMAGE_SIZE_LIMIT)


def _exceeds(width: int, height: int, scale: int) -> bool:
    scaled_width = width * scale
    scaled_height = height * scale
    return (
        scaled_width > MAX_SIDE_PX
        or scaled_height > MAX_SIDE_PX
        or scaled_width * scaled_height > MAX_PIXELS
    )


def _theme(document: str, presentation: Any) -> str:
    if isinstance(presentation, dict) and presentation.get("theme") in {
        "dark",
        "light",
    }:
        return str(presentation["theme"])
    if 'data-theme="light"' in document:
        return "light"
    return "dark"


def _prepare_document(document: str, export_format: str, presentation: Any) -> str:
    theme = _theme(document, presentation)
    background = "#f4f7fb" if theme == "light" else "#14171c"
    width = ""
    if export_format == "jpeg":
        width = f".report {{ width: {JPEG_WIDTH}px !important; }}"
    style = (
        '<style id="sbtd-capture">'
        f"html, body {{ background: {background} !important; }}"
        f"html, body, body * {{ font-family: {_FONT_STACK} !important; }}"
        "* , *::before, *::after {"
        " animation: none !important; transition: none !important;"
        " caret-color: transparent !important; }"
        "html { scroll-behavior: auto !important; }"
        "body, article, section, header, main, div, nav, aside, footer {"
        " position: static !important; }"
        "html, body, .report, .panel {"
        " -webkit-print-color-adjust: exact; print-color-adjust: exact; }"
        "@media print {"
        " .grid, main { display: block !important; width: auto !important;"
        " max-width: 100% !important; }"
        " .report, .panel { display: block !important; grid-column: auto !important;"
        " width: auto !important; max-width: 100% !important;"
        " overflow: visible !important; break-inside: auto !important;"
        " page-break-inside: auto !important; }"
        " table { display: table !important; width: 100% !important;"
        " max-width: 100% !important; table-layout: auto !important; }"
        " thead { display: table-header-group !important; }"
        " tr, th, td { break-inside: avoid !important;"
        " page-break-inside: avoid !important; overflow-wrap: anywhere !important; }"
        " svg, .metric { break-inside: avoid !important; max-width: 100% !important; }"
        "}"
        f"{width}</style>"
    )
    if "</head>" in document:
        return document.replace("</head>", style + "</head>", 1)
    return style + document


def _footer_template(document: str) -> str:
    title = _between(document, "<h1>", "</h1>") or _between(
        document, "<title>", "</title>"
    )
    title = html.unescape(title or "SBTD 报告")
    ranged = _between_pattern(document)
    short = _short_snapshot(document)
    left = html.escape(f"{title} · {ranged} · {short}", quote=True)
    return (
        '<div style="font-size:9pt;width:100%;padding:0 4mm;'
        'display:flex;justify-content:space-between;">'
        f"<span>{left}</span>"
        '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span>'
        "</div>"
    )


def _between(document: str, start: str, end: str) -> str | None:
    begin = document.find(start)
    if begin < 0:
        return None
    begin += len(start)
    finish = document.find(end, begin)
    if finish < 0:
        return None
    return document[begin:finish]


def _between_pattern(document: str) -> str:
    import re

    match = re.search(r"范围：(.+?) → (.+?)（(.+?)）", document) or re.search(
        r"Range: (.+?) → (.+?) \((.+?)\)", document
    )
    if match is None:
        return "unknown"
    start, end, zone = (html.unescape(part) for part in match.groups())
    return f"{start} → {end} ({zone})"


def _short_snapshot(document: str) -> str:
    import re

    match = re.search(r"快照 ([^，<\s]+)", document) or re.search(
        r"snapshot ([^,<\s]+)", document
    )
    if match is None:
        return "unknown"
    snapshot_id = html.unescape(match.group(1))
    if snapshot_id.startswith("snap_") and len(snapshot_id) >= 13:
        return snapshot_id[:13]
    return snapshot_id[:8]


def _allow_request(
    url: str,
    *,
    resource_type: str,
    is_navigation: bool,
    is_main_frame: bool,
    already_fulfilled: bool,
) -> bool:
    return (
        not already_fulfilled
        and is_navigation
        and is_main_frame
        and resource_type == "document"
        and url == _MAIN_URL
    )


def _cancelled(callback: Any) -> bool:
    if not callable(callback):
        return False
    return bool(callback())


def _safe_warning(text: str) -> bool:
    if not text or len(text) > 200:
        return False
    lowered = text.casefold()
    return (
        "/" not in text
        and "\\" not in text
        and "file:" not in lowered
        and "http:" not in lowered
    )


def _make_profile() -> Path:
    return Path(tempfile.mkdtemp(prefix="sbtd-renderer-profile-"))


def _make_job_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="sbtd-renderer-job-"))


def _worker_argv(job: Path) -> list[str]:
    return [sys.executable, str(Path(__file__).resolve()), "--worker", str(job)]


def _write_job(
    job: Path,
    document: str,
    export_format: str,
    home: Path,
    presentation: Any,
    profile: Path,
    timeout_seconds: float,
    *,
    preflight: bool = False,
    locked_scale: int | None = None,
    max_side_px: int | None = None,
    max_pixels: int | None = None,
) -> None:
    side = MAX_SIDE_PX if max_side_px is None else max_side_px
    pixels = MAX_PIXELS if max_pixels is None else max_pixels
    if (
        type(side) is not int
        or side <= 0
        or type(pixels) is not int
        or pixels <= 0
        or (
            locked_scale is not None
            and (type(locked_scale) is not int or locked_scale not in (1, 2))
        )
    ):
        raise RendererError(RENDERER_FAILED)
    (job / "report.html").write_text(document, encoding="utf-8")
    payload = {
        "format": export_format,
        "preflight": preflight,
        "profile": str(profile),
        "home": str(home),
        "presentation": presentation if isinstance(presentation, dict) else None,
        "timeout_seconds": timeout_seconds,
        "max_side_px": side,
        "max_pixels": pixels,
    }
    if locked_scale is not None:
        payload["locked_scale"] = locked_scale
    (job / "request.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def _child_env(home: Path, profile: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(home / "browsers")
    env["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "1"
    env["HOME"] = str(profile)
    env["XDG_CONFIG_HOME"] = str(profile / "config")
    env["XDG_CACHE_HOME"] = str(profile / "cache")
    env["XDG_DATA_HOME"] = str(profile / "data")
    return env


def _terminate_group(proc: subprocess.Popen[bytes]) -> None:
    # The worker can crash before Chromium. Its process group still belongs
    # to this job even after the group leader has exited.
    if os.name == "posix":
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            # Darwin may deny SIGKILL for a zombie-only group. Reap first;
            # only ESRCH from the subsequent probe proves cleanup succeeded.
            pass
        proc.wait(timeout=5)
        deadline = time.monotonic() + 2
        while True:
            try:
                os.killpg(proc.pid, 0)
            except ProcessLookupError:
                return
            except PermissionError:
                # A reaped leader alone does not prove its descendants are gone.
                # Persistent EPERM must reach the same failure deadline.
                pass
            if time.monotonic() >= deadline:
                raise RendererError(RENDERER_FAILED)
            time.sleep(0.01)
    elif proc.poll() is None:
        proc.kill()
    proc.wait(timeout=5)


def _execute_job(
    job: Path,
    profile: Path,
    cancelled: Any,
    deadline: float,
) -> tuple[bytes, dict[str, Any]]:
    spec = json.loads((job / "request.json").read_text(encoding="utf-8"))
    export_format = spec.get("format")
    if export_format not in {"jpeg", "pdf"}:
        raise RendererError(RENDERER_FAILED)
    env = _child_env(Path(spec["home"]), profile)
    popen_kwargs: dict[str, Any] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "env": env,
        "cwd": str(job),
    }
    if os.name == "posix":
        popen_kwargs["start_new_session"] = True
    else:
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        if flags:
            popen_kwargs["creationflags"] = flags
    owner = None
    proc = None
    exit_queue = None
    leader_exited = False
    try:
        if os.name == "nt":
            from renderer_windows import WindowsJob

            owner = WindowsJob()
            env["SBTD_RENDERER_JOB"] = owner.name
        proc = subprocess.Popen(_worker_argv(job), **popen_kwargs)
        if os.name == "posix" and not hasattr(os, "waitid"):
            # macOS Python <3.13 lacks waitid. kqueue observes exit without
            # reaping the leader, so its PGID stays owned until group cleanup.
            exit_queue = select.kqueue()
            event = select.kevent(
                proc.pid,
                filter=select.KQ_FILTER_PROC,
                flags=select.KQ_EV_ADD | select.KQ_EV_ONESHOT,
                fflags=select.KQ_NOTE_EXIT,
            )
            try:
                exit_queue.control([event], 0, 0)
            except ProcessLookupError:
                # Darwin can reject NOTE_EXIT while the child is already dying.
                # It is still ours and unreaped; finally kills/reaps the group.
                leader_exited = True
        downgrade_notified = False
        while True:
            returncode = None
            if exit_queue is not None:
                if leader_exited or exit_queue.control(None, 1, 0):
                    break
            elif os.name == "posix":
                # Keep the exited leader unreaped: its PID/PGID cannot be
                # reused before finally terminates this job's process group.
                status = os.waitid(
                    os.P_PID, proc.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT
                )
                returncode = None
                if status is not None:
                    returncode = status.si_status
                    if status.si_code != os.CLD_EXITED:
                        returncode = -returncode
            else:
                returncode = proc.poll()
            if returncode is not None:
                break
            if _cancelled(cancelled):
                raise RendererError(RENDERER_CANCELLED)
            if time.monotonic() >= deadline:
                raise RendererError(RENDERER_TIMEOUT)
            if not downgrade_notified and _real_file(job / "downgrade"):
                # The worker cannot capture until the caller's warning handler
                # returns. A handler that raises leaves no partial artifact.
                warnings.warn(JPEG_SCALE_WARNING, RuntimeWarning, stacklevel=2)
                if _cancelled(cancelled):
                    raise RendererError(RENDERER_CANCELLED)
                if time.monotonic() >= deadline:
                    raise RendererError(RENDERER_TIMEOUT)
                downgrade_notified = True
                (job / "continue").touch()
            time.sleep(0.05)
        if _cancelled(cancelled):
            raise RendererError(RENDERER_CANCELLED)
        if time.monotonic() >= deadline:
            raise RendererError(RENDERER_TIMEOUT)
    finally:
        try:
            if owner is not None:
                owner.close()
        finally:
            try:
                if proc is not None:
                    _terminate_group(proc)
            finally:
                if exit_queue is not None:
                    exit_queue.close()
    # kqueue only reports exit, not a portable exit status. Cleanup reaps the
    # leader after killpg; use that real status, never assume success on exit.
    return _read_result(
        job, proc.returncode, export_format, preflight=spec.get("preflight", False)
    )


def _read_result(
    job: Path, returncode: int, export_format: str, *, preflight: bool = False
) -> tuple[bytes, dict[str, Any]]:
    error_path = job / "error.json"
    if _real_file(error_path):
        code = RENDERER_FAILED
        try:
            payload = json.loads(error_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            payload = None
        if isinstance(payload, dict) and type(payload.get("code")) is str:
            code = payload["code"]
        if code not in _CODES:
            code = RENDERER_FAILED
        if code == EXPORT_IMAGE_SIZE_LIMIT:
            caps = (payload.get("max_edge_px"), payload.get("max_total_pixels"))
            if any(type(value) is not int or value <= 0 for value in caps):
                raise RendererError(RENDERER_FAILED)
            raise RendererError(code, max_edge_px=caps[0], max_total_pixels=caps[1])
        raise RendererError(code)
    if returncode != 0:
        raise RendererError(RENDERER_FAILED)
    meta: dict[str, Any] = {"warnings": [], "aborted_urls": []}
    meta_path = job / "result.json"
    loaded = None
    if _real_file(meta_path):
        try:
            loaded = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            loaded = None
        if isinstance(loaded, dict):
            warnings = loaded.get("warnings") or []
            urls = loaded.get("aborted_urls") or []
            meta["warnings"] = [
                item
                for item in warnings
                if isinstance(item, str) and _safe_warning(item)
            ]
            meta["aborted_urls"] = [item for item in urls if isinstance(item, str)][
                :100
            ]
            if loaded.get("scale") in {1, 2}:
                meta["scale"] = loaded["scale"]
    if preflight:
        expected = {1, 2} if export_format == "jpeg" else {None}
        if (
            not isinstance(loaded, dict)
            or loaded.get("scale") not in expected
            or not isinstance(loaded.get("warnings"), list)
        ):
            raise RendererError(RENDERER_FAILED)
        return b"", {"scale": loaded["scale"], "warnings": meta["warnings"]}
    blob_path = job / "result.bin"
    if not _real_file(blob_path):
        raise RendererError(RENDERER_FAILED)
    blob = blob_path.read_bytes()
    prefix = b"\xff\xd8\xff" if export_format == "jpeg" else b"%PDF"
    if not blob.startswith(prefix):
        raise RendererError(RENDERER_FAILED)
    return blob, meta


def _acquire_job(cancelled: Any, deadline: float) -> None:
    while True:
        if _cancelled(cancelled):
            raise RendererError(RENDERER_CANCELLED)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RendererError(RENDERER_TIMEOUT)
        if _JOB_SEMAPHORE.acquire(timeout=min(0.05, remaining)):
            return


def _cleanup_dirs(*paths: Path | None) -> None:
    failed = False
    for path in paths:
        if path is None:
            continue
        try:
            shutil.rmtree(path)
        except FileNotFoundError:
            pass
        except OSError:
            failed = True
    if failed:
        raise RendererError(RENDERER_FAILED)


def _render_document(
    html_text: str | bytes,
    export_format: str,
    *,
    home: Any,
    cancelled: Any,
    presentation: Any,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    preflight: bool = False,
    locked_scale: int | None = None,
    max_side_px: int | None = None,
    max_pixels: int | None = None,
) -> tuple[bytes, dict[str, Any]]:
    if export_format not in {"jpeg", "pdf"}:
        raise ValueError("format must be jpeg or pdf")
    if isinstance(html_text, bytes):
        html_text = html_text.decode("utf-8")
    if type(html_text) is not str:
        raise RendererError(RENDERER_FAILED)
    if not isinstance(timeout_seconds, (int, float)) or isinstance(
        timeout_seconds, bool
    ):
        raise RendererError(RENDERER_TIMEOUT)
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise RendererError(RENDERER_TIMEOUT)
    if _cancelled(cancelled):
        raise RendererError(RENDERER_CANCELLED)
    home_path = _home_path(home)
    if home_path is None:
        raise RendererError(RENDERER_UNAVAILABLE)
    deadline = time.monotonic() + float(timeout_seconds)
    acquired = False
    profile: Path | None = None
    job: Path | None = None
    try:
        _acquire_job(cancelled, deadline)
        acquired = True
        if _cancelled(cancelled):
            raise RendererError(RENDERER_CANCELLED)
        profile = _make_profile()
        job = _make_job_dir()
        remaining = max(0.1, deadline - time.monotonic())
        _write_job(
            job,
            html_text,
            export_format,
            home_path,
            presentation,
            profile,
            remaining,
            preflight=preflight,
            locked_scale=locked_scale,
            max_side_px=max_side_px,
            max_pixels=max_pixels,
        )
        return _execute_job(job, profile, cancelled, deadline)
    finally:
        try:
            _cleanup_dirs(profile, job)
        finally:
            if acquired:
                _JOB_SEMAPHORE.release()


def _require_timeout(seconds: Any) -> float:
    if (
        type(seconds) not in (int, float)
        or isinstance(seconds, bool)
        or not math.isfinite(seconds)
        or seconds <= 0
    ):
        raise RendererError(RENDERER_TIMEOUT)
    return float(seconds)


def _html_text(prepared: bytes | str) -> str:
    if type(prepared) is bytes:
        return prepared.decode("utf-8")
    if type(prepared) is str:
        return prepared
    raise RendererError(RENDERER_FAILED)


def _static_html(
    home: Any,
    snapshots: Any,
    snapshot: Any,
    presentation: Any,
    cancelled: Any,
    deadline: float,
) -> tuple[bytes, dict[str, Any]]:
    """Render one static report inside an existing monotonic deadline."""

    def check_budget() -> bool:
        if _cancelled(cancelled):
            raise RendererError(RENDERER_CANCELLED)
        if time.monotonic() >= deadline:
            raise RendererError(RENDERER_TIMEOUT)
        return False

    check_budget()
    capability = renderer_capability(home, timeout_seconds=deadline - time.monotonic())
    check_budget()
    if not capability["available"]:
        raise RendererError(RENDERER_UNAVAILABLE)
    html_bytes, meta = render_export(
        snapshot,
        "html",
        presentation,
        check_budget,
        snapshots=snapshots,
    )
    check_budget()
    if type(html_bytes) is not bytes or not isinstance(meta, dict):
        raise RendererError(RENDERER_FAILED)
    return html_bytes, meta


class BrowserRenderer:
    """Render one snapshot to JPEG/PDF; emit a RuntimeWarning before JPEG downgrade."""

    def __init__(
        self,
        home: Any,
        snapshots: Any,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.home = home
        self.snapshots = snapshots
        self.timeout_seconds = timeout_seconds

    def __call__(
        self,
        snapshot: Any,
        export_format: str,
        presentation_state: Any,
        cancelled: Any,
        *,
        prepared_html: bytes | str | None = None,
        meta: dict[str, Any] | None = None,
        locked_scale: int | None = None,
        max_side_px: int | None = None,
        max_pixels: int | None = None,
        timeout_seconds: float | None = None,
    ):
        return self._run(
            snapshot,
            export_format,
            presentation_state,
            cancelled,
            preflight=False,
            prepared_html=prepared_html,
            meta=meta,
            locked_scale=locked_scale,
            max_side_px=max_side_px,
            max_pixels=max_pixels,
            timeout_seconds=timeout_seconds,
        )

    def preflight(
        self,
        snapshot: Any,
        export_format: str,
        presentation_state: Any,
        cancelled: Any = None,
        *,
        prepared_html: bytes | str | None = None,
        meta: dict[str, Any] | None = None,
        max_side_px: int | None = None,
        max_pixels: int | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        """Measure before acceptance, without capturing or creating an export job.

        JPEG returns scale 1/2; PDF returns None. Warnings include the report's
        existing warnings. This is not a reservation and stores nothing on the
        instance. Optional prepared HTML and caps apply only to this call; omit
        them to render the snapshot as before. Direct generation still rechecks
        layout. The caller owns the snapshot's lifetime, as for direct rendering.
        """
        return self._run(
            snapshot,
            export_format,
            presentation_state,
            cancelled,
            preflight=True,
            prepared_html=prepared_html,
            meta=meta,
            max_side_px=max_side_px,
            max_pixels=max_pixels,
            timeout_seconds=timeout_seconds,
        )

    def _run(
        self,
        snapshot: Any,
        export_format: str,
        presentation_state: Any,
        cancelled: Any,
        *,
        preflight: bool,
        prepared_html: bytes | str | None = None,
        meta: dict[str, Any] | None = None,
        locked_scale: int | None = None,
        max_side_px: int | None = None,
        max_pixels: int | None = None,
        timeout_seconds: float | None = None,
    ):
        if export_format not in {"jpeg", "pdf"}:
            raise ValueError("format must be jpeg or pdf")
        budget = self.timeout_seconds if timeout_seconds is None else timeout_seconds
        deadline = time.monotonic() + _require_timeout(budget)

        def check_budget() -> bool:
            if _cancelled(cancelled):
                raise RendererError(RENDERER_CANCELLED)
            if time.monotonic() >= deadline:
                raise RendererError(RENDERER_TIMEOUT)
            return False

        try:
            if prepared_html is None:
                html_bytes, meta = _static_html(
                    self.home,
                    self.snapshots,
                    snapshot,
                    presentation_state,
                    cancelled,
                    deadline,
                )
                document = html_bytes.decode("utf-8")
            else:
                document = _html_text(prepared_html)
                meta = dict(meta) if isinstance(meta, dict) else {}
                check_budget()
                capability = renderer_capability(
                    self.home, timeout_seconds=deadline - time.monotonic()
                )
                check_budget()
                if not capability["available"]:
                    raise RendererError(RENDERER_UNAVAILABLE)
            seam: dict[str, Any] = {}
            if locked_scale is not None:
                seam["locked_scale"] = locked_scale
            if max_side_px is not None:
                seam["max_side_px"] = max_side_px
            if max_pixels is not None:
                seam["max_pixels"] = max_pixels
            artifact, extra = _render_document(
                document,
                export_format,
                home=self.home,
                cancelled=check_budget,
                presentation=presentation_state,
                timeout_seconds=deadline - time.monotonic(),
                preflight=preflight,
                **seam,
            )
            if preflight:
                return {
                    "scale": extra["scale"],
                    "warnings": list(
                        dict.fromkeys(
                            [*(meta.get("warnings") or []), *extra["warnings"]]
                        )
                    ),
                }
            return _published(artifact, extra, meta, export_format)
        except RendererError:
            raise
        except Exception:  # noqa: BLE001 — public library errors never expose local paths.
            raise RendererError(RENDERER_FAILED) from None


def _published(
    artifact: Any,
    extra: Any,
    meta: dict[str, Any],
    export_format: str,
) -> tuple[bytes, dict[str, Any]]:
    if type(artifact) is not bytes or not artifact:
        raise RendererError(RENDERER_FAILED)
    published = dict(meta)
    published["mime_type"] = (
        "image/jpeg" if export_format == "jpeg" else "application/pdf"
    )
    published["byte_size"] = len(artifact)
    published["format"] = export_format
    published["renderer_version"] = BROWSER_RENDERER_VERSION
    warnings = list(published.get("warnings") or [])
    if isinstance(extra, dict):
        for item in extra.get("warnings") or []:
            if isinstance(item, str) and item not in warnings and _safe_warning(item):
                warnings.append(item)
    published["warnings"] = warnings
    return artifact, published


def _remaining_ms(deadline: float) -> int:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise RendererError(RENDERER_TIMEOUT)
    return max(1, int(remaining * 1000))


def _read_member(path: Path, parent: Path) -> bytes:
    if not _real_file(path):
        raise RendererError(RENDERER_FAILED)
    try:
        if path.resolve().parent != parent.resolve():
            raise RendererError(RENDERER_FAILED)
    except OSError:
        raise RendererError(RENDERER_FAILED) from None
    return path.read_bytes()


def _install_routes(context: Any, page: Any, document: str, aborted: list[str]) -> None:
    state = {"done": False}

    def handle(route: Any) -> None:
        request = route.request
        frame = request.frame
        allowed = _allow_request(
            request.url,
            resource_type=request.resource_type,
            is_navigation=bool(request.is_navigation_request()),
            is_main_frame=frame is page.main_frame,
            already_fulfilled=state["done"],
        )
        if allowed:
            state["done"] = True
            route.fulfill(
                status=200,
                content_type="text/html; charset=utf-8",
                body=document,
            )
            return
        url = getattr(request, "url", "")
        if isinstance(url, str) and len(aborted) < 100:
            aborted.append(url)
        route.abort("blockedbyclient")

    context.route(lambda _url: True, handle)
    context.route_web_socket(
        lambda _url: True,
        lambda socket: _close_socket(socket, aborted),
    )

    def close_extra(new_page: Any) -> None:
        if new_page is not page:
            new_page.close()

    context.on("page", close_extra)


def _close_socket(socket: Any, aborted: list[str]) -> None:
    url = getattr(socket, "url", "ws:")
    if isinstance(url, str) and len(aborted) < 100:
        aborted.append(url)
    socket.close()


def _wait_ready(page: Any) -> None:
    page.evaluate(
        """async () => {
          if (document.fonts && document.fonts.ready) await document.fonts.ready;
          const images = Array.from(document.images || []);
          await Promise.all(images.map((img) => img.complete ? null : new Promise((resolve) => {
            img.addEventListener("load", resolve, {once: true});
            img.addEventListener("error", resolve, {once: true});
          })));
          if (document.body) document.body.getBoundingClientRect();
        }"""
    )


def _measured_size(page: Any) -> tuple[int, int]:
    width, height = page.evaluate(
        """() => {
          const root = document.documentElement;
          const body = document.body;
          return [
            Math.ceil(Math.max(root.scrollWidth, body.scrollWidth)),
            Math.ceil(Math.max(root.scrollHeight, body.scrollHeight))
          ];
        }"""
    )
    return width, height


def _open_context(
    playwright: Any,
    shell: Path,
    profile: Path,
    scale: int,
    theme: str,
    deadline: float,
) -> Any:
    context = playwright.chromium.launch_persistent_context(
        str(profile),
        executable_path=str(shell),
        headless=True,
        # Application-level profile/routing isolation, not an OS sandbox.
        chromium_sandbox=False,
        handle_sighup=False,
        handle_sigint=False,
        handle_sigterm=False,
        args=list(_CHROMIUM_ARGS),
        viewport={"width": JPEG_WIDTH, "height": 900},
        device_scale_factor=scale,
        service_workers="block",
        accept_downloads=False,
        color_scheme=theme,
        locale="zh-CN",
        java_script_enabled=True,
        bypass_csp=False,
        ignore_https_errors=False,
        permissions=[],
        timeout=_remaining_ms(deadline),
    )
    context.set_default_timeout(_remaining_ms(deadline))
    context.set_default_navigation_timeout(_remaining_ms(deadline))
    return context


def _load_report(
    context: Any, document: str, aborted: list[str], deadline: float
) -> Any:
    page = context.pages[0] if context.pages else context.new_page()
    _install_routes(context, page, document, aborted)
    page.goto(_MAIN_URL, wait_until="domcontentloaded", timeout=_remaining_ms(deadline))
    _wait_ready(page)
    return page


def _notify_downgrade(job: Path, deadline: float) -> None:
    (job / "downgrade").touch()
    while not _real_file(job / "continue"):
        if time.monotonic() >= deadline:
            raise RendererError(RENDERER_TIMEOUT)
        time.sleep(0.05)


def _capture(
    document: str,
    export_format: str,
    presentation: Any,
    shell: Path,
    profile: Path,
    timeout_seconds: float,
    job: Path,
    *,
    preflight: bool = False,
    locked_scale: int | None = None,
) -> tuple[bytes | None, dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    prepared = _prepare_document(document, export_format, presentation)
    theme = _theme(document, presentation)
    aborted: list[str] = []
    warnings: list[str] = []
    deadline = time.monotonic() + timeout_seconds
    scale = 2 if export_format == "jpeg" else 1
    if locked_scale is not None:
        if (
            export_format != "jpeg"
            or type(locked_scale) is not int
            or locked_scale not in (1, 2)
        ):
            raise RendererError(RENDERER_FAILED)
        scale = locked_scale
    try:
        with sync_playwright() as playwright:
            context = None
            try:
                context = _open_context(
                    playwright, shell, profile, scale, theme, deadline
                )
                page = _load_report(context, prepared, aborted, deadline)
                if export_format == "jpeg":
                    css_width, css_height = _measured_size(page)
                    warning = None
                    if locked_scale is None:
                        chosen, warning = _jpeg_scale(css_width, css_height)
                        if warning:
                            warnings.append(warning)
                        if chosen != scale:
                            context.close()
                            context = None
                            scale = chosen
                            context = _open_context(
                                playwright, shell, profile, scale, theme, deadline
                            )
                            page = _load_report(context, prepared, aborted, deadline)
                            css_width, css_height = _measured_size(page)
                    if (
                        type(css_width) is not int
                        or type(css_height) is not int
                        or css_width < JPEG_WIDTH
                        or css_height < 1
                        or _exceeds(css_width, css_height, scale)
                    ):
                        raise RendererError(EXPORT_IMAGE_SIZE_LIMIT)
                    if preflight:
                        return None, {"scale": scale, "warnings": warnings}
                    if warning is not None:
                        _notify_downgrade(job, deadline)
                    payload = page.screenshot(
                        type="jpeg",
                        quality=JPEG_QUALITY,
                        full_page=True,
                        omit_background=False,
                        animations="disabled",
                        caret="hide",
                        scale="device",
                        timeout=_remaining_ms(deadline),
                    )
                else:
                    page.emulate_media(
                        media="print",
                        color_scheme=theme,
                        reduced_motion="reduce",
                    )
                    _wait_ready(page)
                    if preflight:
                        return None, {"scale": None, "warnings": warnings}
                    payload = page.pdf(
                        format="A3",
                        landscape=True,
                        print_background=True,
                        prefer_css_page_size=False,
                        display_header_footer=True,
                        header_template="<span></span>",
                        footer_template=_footer_template(document),
                        margin={
                            "top": "10mm",
                            "right": "10mm",
                            "bottom": "10mm",
                            "left": "10mm",
                        },
                        tagged=True,
                        scale=1,
                    )
            finally:
                if context is not None:
                    context.close()
    except RendererError:
        raise
    except Exception as exc:  # noqa: BLE001 — child boundary strips browser paths.
        if "Timeout" in type(exc).__name__:
            raise RendererError(RENDERER_TIMEOUT) from None
        raise RendererError(RENDERER_FAILED) from None
    return payload, {
        "warnings": warnings,
        "aborted_urls": aborted[:100],
        "scale": scale if export_format == "jpeg" else None,
    }


def _write_result(job: Path, payload: bytes | None, meta: dict[str, Any]) -> None:
    if payload is not None:
        (job / "result.bin").write_bytes(payload)
    safe = {
        "warnings": [
            item
            for item in meta.get("warnings") or []
            if isinstance(item, str) and _safe_warning(item)
        ],
        "aborted_urls": [
            item for item in meta.get("aborted_urls") or [] if isinstance(item, str)
        ][:100],
        "scale": meta.get("scale") if meta.get("scale") in {1, 2} else None,
    }
    (job / "result.json").write_text(json.dumps(safe), encoding="utf-8")


def _write_error(job: Path, error: RendererError) -> None:
    payload: dict[str, Any] = {"code": error.code}
    if error.code == EXPORT_IMAGE_SIZE_LIMIT:
        payload.update(
            max_edge_px=error.max_edge_px, max_total_pixels=error.max_total_pixels
        )
    try:
        (job / "error.json").write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        return


def _worker_run(job: Path) -> None:
    global MAX_SIDE_PX, MAX_PIXELS
    spec = json.loads(_read_member(job / "request.json", job).decode("utf-8"))
    max_side = spec.get("max_side_px")
    max_pixels = spec.get("max_pixels")
    if (
        type(max_side) is not int
        or max_side <= 0
        or type(max_pixels) is not int
        or max_pixels <= 0
    ):
        raise RendererError(RENDERER_FAILED)
    MAX_SIDE_PX, MAX_PIXELS = max_side, max_pixels
    document = _read_member(job / "report.html", job).decode("utf-8")
    export_format = spec.get("format")
    if export_format not in {"jpeg", "pdf"}:
        raise RendererError(RENDERER_FAILED)
    home = _home_path(spec.get("home"))
    profile = _home_path(spec.get("profile"))
    if home is None or profile is None or not _real_dir(profile):
        raise RendererError(RENDERER_FAILED)
    if _playwright_version() != PLAYWRIGHT_VERSION:
        raise RendererError(RENDERER_UNAVAILABLE)
    shell = _shell_executable(home)
    if shell is None:
        raise RendererError(RENDERER_UNAVAILABLE)
    timeout_seconds = spec.get("timeout_seconds")
    if not isinstance(timeout_seconds, (int, float)) or isinstance(
        timeout_seconds, bool
    ):
        timeout_seconds = DEFAULT_TIMEOUT_SECONDS
    locked_scale = spec.get("locked_scale")
    if locked_scale is not None and (
        type(locked_scale) is not int or locked_scale not in (1, 2)
    ):
        raise RendererError(RENDERER_FAILED)
    payload, meta = _capture(
        document,
        export_format,
        spec.get("presentation"),
        shell,
        profile,
        float(timeout_seconds),
        job,
        preflight=spec.get("preflight", False),
        locked_scale=locked_scale,
    )
    _write_result(job, payload, meta)


def _worker_entry(job_dir: str) -> int:
    job = Path(job_dir)
    try:
        if os.name == "nt":
            from renderer_windows import join_job

            join_job(os.environ["SBTD_RENDERER_JOB"])
        _worker_run(job)
    except RendererError as exc:
        _write_error(job, exc)
        return 1
    except Exception:  # noqa: BLE001 — only a fixed safe code crosses the process boundary.
        _write_error(job, RendererError(RENDERER_FAILED))
        return 1
    return 0


def _main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] != "--worker":
        return 2
    return _worker_entry(argv[2])


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
