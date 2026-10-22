"""R2.1b library JPEG/PDF integration; spec/r2.1b-renderer-scenarios.md.

Traces missing-renderer capabilities, HTTP jpeg/pdf acceptance, shared
event-detail withholding, and ExportStore lifecycle for image and PDF jobs.
Browser execution is patched only at browser_renderer._render_document.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contract_eval import parse_instant
from export_render import RENDERER_VERSION, ExportRenderer, default_presentation
from export_store import ExportGone, ExportNotReady, ExportStore
from report_snapshot import SnapshotStore
from stats_query import query
from test_csv_export import _dataset, _rows, _scope
from test_serve import (
    ServeProcess,
    _enable_observation,
    _free_port,
    _seed_golden_events,
    pair,
    request,
)

EXCLUDED_EVENT_IDS = frozenset({"evt_created_leaf", "evt_leaf_progress"})
MARKER_NOT_EXPORTABLE = "PRIVATE_EXPORTABLE_FALSE_MARKER"
MARKER_CLASSIFICATION = "PRIVATE_NON_LOCAL_METADATA_MARKER"
PRIVATE_MARKERS = (MARKER_NOT_EXPORTABLE, MARKER_CLASSIFICATION)
WITHHELD_WARNING = "WITHHELD_NON_EXPORTABLE:2"
KEPT_EVENT_ID = "evt_leaf_done_2"
KEPT_RUN_ID = "run_leaf_1"
KEPT_TASK_ID = "task_leaf"
MIME = {
    "html": "text/html; charset=utf-8",
    "csv": "text/csv; charset=utf-8",
    "jpeg": "image/jpeg",
    "pdf": "application/pdf",
}
BROWSER_RENDERER_VERSION = "r2.1b.1"
JPEG_PREFIX = b"\xff\xd8\xff"
PDF_PREFIX = b"%PDF-"
SAFE_RENDERER_CODES = frozenset(
    {
        "RENDERER_UNAVAILABLE",
        "EXPORT_IMAGE_SIZE_LIMIT",
        "RENDERER_TIMEOUT",
        "RENDERER_FAILED",
        "RENDERER_CANCELLED",
    }
)


def _presentation() -> dict:
    return default_presentation()


def _detail_presentation() -> dict:
    state = default_presentation()
    state["expanded_detail_ids"] = [
        KEPT_TASK_ID,
        "activity-trend",
        "mode-decisions",
        "blockers",
    ]
    state["preview_row_sets"] = {
        "activity-trend": 10000,
        "activity-trend:event": 10000,
        "mode-decisions": 10000,
        "mode-decisions:event": 10000,
        "blockers": 10000,
        "blockers:run": 10000,
        "task-audit-detail": 10000,
        "task-audit-detail:event": 10000,
    }
    return state


def _privacy_dataset() -> dict:
    dataset = _dataset()
    for event in dataset["events"]:
        if event["event_id"] == "evt_created_leaf":
            event["privacy"]["exportable"] = False
            event["extensions"] = {"actor_alias": MARKER_NOT_EXPORTABLE}
            event.setdefault("state", {})["current"] = MARKER_NOT_EXPORTABLE
        elif event["event_id"] == "evt_leaf_progress":
            event["privacy"]["classification"] = "conversation"
            event["extensions"] = {"actor_alias": MARKER_CLASSIFICATION}
            event.setdefault("state", {})["current"] = MARKER_CLASSIFICATION
    return dataset


def _counts(meta: dict) -> dict[str, int]:
    return {item["record_type"]: item["rows"] for item in meta["dataset_manifest"]}


def _until(store: ExportStore, export_id: str, *, status: str = "ready") -> dict:
    deadline = time.monotonic() + 5
    last = None
    while time.monotonic() < deadline:
        last = store.get(export_id)
        if last["status"] == status:
            return last
        if status == "ready" and last["status"] in ("failed", "cancelled"):
            raise AssertionError(last)
        time.sleep(0.01)
    raise AssertionError(last)


def _accept_call(args: tuple, kwargs: dict) -> tuple[str, str]:
    html = kwargs.get("html", args[0] if args else None)
    format_name = kwargs.get("format", args[1] if len(args) > 1 else None)
    if not isinstance(html, str) or "<html" not in html.lower():
        raise AssertionError("browser worker did not receive report HTML text")
    if html.startswith(("http://", "https://", "file:")):
        raise AssertionError("browser worker received a URL")
    if format_name not in ("jpeg", "pdf"):
        raise AssertionError(f"unexpected browser format {format_name!r}")
    if "home" not in kwargs or not callable(kwargs.get("cancelled")):
        raise AssertionError("worker call omitted home or cancelled")
    if "presentation" not in kwargs:
        raise AssertionError("worker call omitted presentation")
    timeout = kwargs.get("timeout_seconds", 60)
    if type(timeout) is bool or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise AssertionError("worker timeout is not a positive deadline")
    return html, format_name


def _artifact(format_name: str) -> bytes:
    if format_name == "jpeg":
        return JPEG_PREFIX + b"\xd9"
    return PDF_PREFIX + b"1.4\n%%EOF\n"


def _renderer_home() -> Path | None:
    raw = os.environ.get("SBTD_RENDERER_TEST_HOME")
    if not raw:
        return None
    home = Path(raw)
    if not (home / "browsers").is_dir():
        return None
    return home


def _browser_binaries(home: Path) -> set[str]:
    root = home / "browsers"
    return {
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and "chrome-headless-shell" in path.name
    }


@contextmanager
def _patched_worker(side_effect):
    """Patch availability and the private worker boundary, not render_export."""
    with (
        mock.patch(
            "browser_renderer.renderer_capability",
            return_value={"available": True, "reason": None},
            create=True,
        ),
        mock.patch(
            "browser_renderer._render_document",
            side_effect=side_effect,
            create=True,
        ),
    ):
        yield


class RendererLibraryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="sbtd-renderer-")
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "runtime"
        self.dataset = _dataset()
        self.scope = _scope(self.dataset, ["tasks.touched"])
        self.snapshots = SnapshotStore(self.home)
        self.snapshot = self.snapshots.create_or_reuse(self.dataset, self.scope)
        self.stores: list[ExportStore] = []
        self.addCleanup(self._close_stores)

    def _close_stores(self) -> None:
        for store in self.stores:
            store.close()

    def _open(
        self,
        renderer,
        home: Path | None = None,
        snapshots: SnapshotStore | None = None,
    ) -> ExportStore:
        store = ExportStore(
            home or self.home,
            snapshots or self.snapshots,
            renderer,
        )
        self.stores.append(store)
        return store

    def test_close_cancels_preflight_and_releases_its_pin(self) -> None:
        from browser_renderer import RendererError

        entered = threading.Event()
        release = threading.Event()
        errors = []
        renderer = ExportRenderer(self.snapshots, home=self.home)
        store = self._open(renderer)

        def measure(*_args, **kwargs):
            entered.set()
            while not release.wait(0.01):
                kwargs["cancelled"]()
            return b"", {"scale": 2, "warnings": []}

        def create():
            try:
                store.create(
                    self.snapshot.snapshot_id,
                    "jpeg",
                    _presentation(),
                    prepare=renderer.prepare,
                )
            except (RendererError, ValueError) as error:
                errors.append(error)

        with _patched_worker(measure):
            thread = threading.Thread(target=create)
            thread.start()
            try:
                self.assertTrue(entered.wait(5))
                store.close()
                removed = self.snapshots.sweep(
                    now=datetime.now(UTC) + timedelta(days=2)
                )
                self.assertIn(self.snapshot.snapshot_id, removed)
                self.assertEqual(list((self.home / "exports").iterdir()), [])
            finally:
                release.set()
                thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], RendererError)
        self.assertEqual(errors[0].code, "RENDERER_CANCELLED")

    def test_html_and_csv_do_not_require_a_renderer_home(self) -> None:
        """Scenario: 缺少可选依赖不影响原有格式."""
        renderer = ExportRenderer(self.snapshots)
        for format_name in ("html", "csv"):
            with self.subTest(format=format_name):
                payload, meta = renderer(
                    self.snapshot,
                    format_name,
                    _presentation(),
                    lambda: False,
                )
                self.assertTrue(payload)
                self.assertEqual(meta["mime_type"], MIME[format_name])
                self.assertEqual(meta["format"], format_name)
                self.assertNotIn(str(self.home), json.dumps(meta))

    def test_jpeg_and_pdf_digest_is_stable_across_download_and_restart(self) -> None:
        """Scenario: 图像和文档复用现有产物生命周期."""
        captured: list[dict] = []

        def render(*args, **kwargs):
            html, format_name = _accept_call(args, kwargs)
            self.assertEqual(Path(kwargs["home"]), self.home)
            captured.append({"html": html, "format": format_name})
            self.assertIn(self.snapshot.snapshot_id, html)
            return _artifact(format_name), {}

        renderer = ExportRenderer(self.snapshots, home=self.home)
        with _patched_worker(render):
            store = self._open(renderer)
            published = {}
            for format_name in ("jpeg", "pdf"):
                export_id = store.create(
                    self.snapshot.snapshot_id,
                    format_name,
                    _presentation(),
                )
                info = _until(store, export_id)
                first, downloaded = store.download(export_id)
                again, repeated = store.download(export_id)
                published[format_name] = (export_id, info, first)
                self.assertEqual(downloaded["format"], format_name)
                self.assertEqual(downloaded["mime_type"], MIME[format_name])
                self.assertEqual(repeated["mime_type"], MIME[format_name])
                self.assertEqual(again, first)
                digest = hashlib.sha256(first).hexdigest()
                self.assertEqual(downloaded["sha256"], digest)
                self.assertEqual(len(downloaded["sha256"]), 64)
                self.assertEqual(downloaded["byte_count"], len(first))
                self.assertEqual(downloaded["byte_size"], len(first))
                self.assertEqual(downloaded["snapshot_id"], self.snapshot.snapshot_id)
                self.assertEqual(
                    downloaded["renderer_version"], BROWSER_RENDERER_VERSION
                )
                self.assertNotIn("aborted_urls", json.dumps(downloaded))
                self.assertNotIn(str(self.home), json.dumps(downloaded))
                ready = parse_instant(info["ready_at"])
                expires = parse_instant(info["expires_at"])
                self.assertEqual(expires - ready, timedelta(seconds=86400))
                self.assertEqual(store.get(export_id)["expires_at"], info["expires_at"])
                names = sorted(path.name for path in (self.home / "exports").iterdir())
                self.assertIn(f"{export_id}.bin", names)
                self.assertIn(f"{export_id}.json", names)
                manifest = (self.home / "exports" / f"{export_id}.json").read_text(
                    encoding="utf-8"
                )
                self.assertNotIn(str(self.home), manifest)
            self.assertEqual([item["format"] for item in captured], ["jpeg", "pdf"])
            calls = len(captured)
            store.close()
            restored = self._open(renderer)
            for format_name, (export_id, info, first) in published.items():
                blob, info2 = restored.download(export_id)
                self.assertEqual(blob, first)
                self.assertEqual(info2["sha256"], hashlib.sha256(first).hexdigest())
                self.assertEqual(info2["expires_at"], info["expires_at"])
                self.assertEqual(info2["ready_at"], info["ready_at"])
                self.assertEqual(info2["mime_type"], MIME[format_name])
                self.assertEqual(info2["renderer_version"], BROWSER_RENDERER_VERSION)
            self.assertEqual(len(captured), calls)

    def test_download_does_not_extend_24h_and_sweep_stays_in_exports(self) -> None:
        """Scenario: 图像和文档复用现有产物生命周期."""
        sentinel = self.home / "audit.db"
        sentinel.write_bytes(b"untouched")
        outside = Path(self.temporary.name) / "handoff.md"
        outside.write_text("keep", encoding="utf-8")

        def render(*args, **kwargs):
            _html, format_name = _accept_call(args, kwargs)
            self.assertEqual(Path(kwargs["home"]), self.home)
            return _artifact(format_name), {}

        renderer = ExportRenderer(self.snapshots, home=self.home)
        with _patched_worker(render):
            store = self._open(renderer)
            export_id = store.create(self.snapshot.snapshot_id, "jpeg", _presentation())
            info = _until(store, export_id)
            expires = parse_instant(info["expires_at"])
            blob, _downloaded = store.download(export_id)
            self.assertEqual(store.sweep(now=expires - timedelta(seconds=1)), [])
            self.assertEqual(store.download(export_id)[0], blob)
            self.assertEqual(store.get(export_id)["expires_at"], info["expires_at"])
            self.assertEqual(store.sweep(now=expires), [export_id])
            with self.assertRaises(ExportGone):
                store.download(export_id)
            self.assertFalse((self.home / "exports" / f"{export_id}.bin").exists())
            self.assertFalse((self.home / "exports" / f"{export_id}.json").exists())
            self.assertEqual(sentinel.read_bytes(), b"untouched")
            self.assertEqual(outside.read_text(encoding="utf-8"), "keep")
            self.assertTrue((self.home / "snapshots").is_dir())

    def test_in_flight_jpeg_holds_the_snapshot_and_success_releases_it(self) -> None:
        """Pin precedes publish; success releases the snapshot reference."""
        home = Path(self.temporary.name) / "pin-home"
        now = datetime.now(UTC)
        snapshots = SnapshotStore(home, ttl_seconds=86400)
        snapshot = snapshots.create_or_reuse(self.dataset, self.scope, now=now)
        expired = now + timedelta(days=1)
        entered = threading.Event()
        release = threading.Event()
        self.addCleanup(release.set)

        def render(*args, **kwargs):
            _accept_call(args, kwargs)
            self.assertEqual(Path(kwargs["home"]), home)
            entered.set()
            cancelled = kwargs["cancelled"]
            while not release.is_set():
                if cancelled():
                    raise RuntimeError("cancelled")
                time.sleep(0.005)
            return _artifact("jpeg"), {}

        renderer = ExportRenderer(snapshots, home=home)
        with _patched_worker(render):
            store = self._open(renderer, home, snapshots)
            export_id = store.create(snapshot.snapshot_id, "jpeg", _presentation())
            self.assertTrue(entered.wait(5), "worker boundary was not called")
            self.assertEqual(snapshots.sweep(now=expired), [])
            self.assertEqual(
                snapshots.get(snapshot.snapshot_id, now=expired).snapshot_id,
                snapshot.snapshot_id,
            )
            self.assertFalse((home / "exports" / f"{export_id}.json").exists())
            with self.assertRaises(ExportNotReady):
                store.download(export_id)
            release.set()
            info = _until(store, export_id)
            self.assertEqual(info["mime_type"], MIME["jpeg"])
            self.assertIsNone(info["error"])
            store.close()
            self.assertEqual(snapshots.sweep(now=expired), [snapshot.snapshot_id])

    def test_browser_format_without_home_fails_safe_and_releases_the_pin(self) -> None:
        """Absent renderer home is a safe library error, not a published file."""
        home = Path(self.temporary.name) / "no-home"
        now = datetime.now(UTC)
        snapshots = SnapshotStore(home, ttl_seconds=86400)
        snapshot = snapshots.create_or_reuse(self.dataset, self.scope, now=now)
        expired = now + timedelta(days=1)
        renderer = ExportRenderer(snapshots)
        store = self._open(renderer, home, snapshots)
        export_id = store.create(snapshot.snapshot_id, "pdf", _presentation())
        info = _until(store, export_id, status="failed")
        self.assertEqual(info["error"], "RENDERER_UNAVAILABLE")
        self.assertNotIn(str(home), json.dumps(info))
        self.assertNotIn("/", info["error"])
        with self.assertRaises(ExportNotReady):
            store.download(export_id)
        self.assertFalse((home / "exports" / f"{export_id}.json").exists())
        self.assertFalse((home / "exports" / f"{export_id}.bin").exists())
        store.close()
        self.assertEqual(snapshots.sweep(now=expired), [snapshot.snapshot_id])

    def test_renderer_error_text_is_not_persisted(self) -> None:
        """RendererError persists an allowlisted code, never caller text."""
        from browser_renderer import RendererError

        secret = str(self.home / "secret-export-path")
        unsafe = RendererError(f"disk full at {secret}")
        self.assertEqual(unsafe.code, "RENDERER_FAILED")
        self.assertEqual(str(unsafe), "RENDERER_FAILED")
        self.assertNotIn(secret, str(unsafe))
        allowed = RendererError("RENDERER_TIMEOUT")
        self.assertEqual(allowed.code, "RENDERER_TIMEOUT")
        self.assertEqual(str(allowed), allowed.code)
        self.assertIn(allowed.code, SAFE_RENDERER_CODES)

        def explode(snapshot, format_name, presentation, cancelled):
            if format_name == "csv":
                raise RendererError("RENDERER_TIMEOUT")
            raise RendererError(f"disk full at {secret}")

        store = self._open(explode)
        leaked = store.create(self.snapshot.snapshot_id, "html", _presentation())
        timed = store.create(self.snapshot.snapshot_id, "csv", _presentation())
        leaked_info = _until(store, leaked, status="failed")
        timed_info = _until(store, timed, status="failed")
        self.assertEqual(leaked_info["error"], "RENDERER_FAILED")
        self.assertEqual(timed_info["error"], "RENDERER_TIMEOUT")
        encoded = json.dumps([leaked_info, timed_info])
        self.assertNotIn(secret, encoded)
        self.assertNotIn("disk full", encoded)
        self.assertNotIn(str(self.home), encoded)
        with self.assertRaises(ExportNotReady):
            store.download(leaked)

    def test_four_formats_withhold_the_same_event_detail(self) -> None:
        """Scenario: 四格式不泄漏被屏蔽事件明细."""
        dataset = _privacy_dataset()
        scope = _scope(
            dataset,
            [
                "tasks.touched",
                "steps.success_rate_observed",
                "duration.step_p50/p95",
            ],
        )
        snapshot = self.snapshots.create_or_reuse(dataset, scope)
        answer = query(dataset, scope)
        presentation = _detail_presentation()
        event_ids = {
            row["record_id"] for row in snapshot.rows if row["record_type"] == "event"
        }
        task_ids = {
            row["record_id"] for row in snapshot.rows if row["record_type"] == "task"
        }
        run_ids = {
            row["record_id"] for row in snapshot.rows if row["record_type"] == "run"
        }
        self.assertEqual(event_ids & EXCLUDED_EVENT_IDS, EXCLUDED_EVENT_IDS)
        self.assertIn(KEPT_EVENT_ID, event_ids)
        self.assertIn(KEPT_TASK_ID, task_ids)
        self.assertIn(KEPT_RUN_ID, run_ids)
        base = {item["record_type"]: item["rows"] for item in snapshot.dataset_manifest}
        captured: list[dict] = []

        def render(*args, **kwargs):
            html, format_name = _accept_call(args, kwargs)
            self.assertEqual(Path(kwargs["home"]), self.home)
            captured.append({"html": html, "format": format_name})
            return _artifact(format_name), {}

        renderer = ExportRenderer(self.snapshots, home=self.home)
        with _patched_worker(render):
            html_payload, html_meta = renderer(
                snapshot, "html", presentation, lambda: False
            )
            csv_payload, csv_meta = renderer(
                snapshot, "csv", presentation, lambda: False
            )
            store = self._open(renderer)
            jpeg_id = store.create(snapshot.snapshot_id, "jpeg", presentation)
            pdf_id = store.create(snapshot.snapshot_id, "pdf", presentation)
            _until(store, jpeg_id)
            _until(store, pdf_id)
            _, jpeg_meta = store.download(jpeg_id)
            _, pdf_meta = store.download(pdf_id)

        self.assertEqual([item["format"] for item in captured], ["jpeg", "pdf"])
        html = html_payload.decode("utf-8")
        csv_text = csv_payload.decode("utf-8")
        rows = _rows(csv_payload)
        exported_events = {
            row["record_id"] for row in rows if row["record_type"] == "event"
        }
        exported_tasks = {
            row["record_id"] for row in rows if row["record_type"] == "task"
        }
        exported_runs = {
            row["record_id"] for row in rows if row["record_type"] == "run"
        }
        self.assertEqual(event_ids - exported_events, EXCLUDED_EVENT_IDS)
        self.assertEqual(exported_tasks, task_ids)
        self.assertEqual(exported_runs, run_ids)
        self.assertIn(KEPT_EVENT_ID, exported_events)
        metrics = {
            row["metric_id"]: row["metric_value"]
            for row in rows
            if row["record_type"] == "metric"
        }
        self.assertEqual(metrics["tasks.touched"], "2")
        self.assertEqual(metrics["steps.success_rate_observed"], "1/2")
        self.assertEqual(
            metrics["tasks.touched"],
            str(answer["metrics"]["tasks.touched"]["value"]),
        )
        self.assertEqual(
            metrics["steps.success_rate_observed"],
            str(answer["metrics"]["steps.success_rate_observed"]["value"]),
        )
        documents = [html, csv_text, *(item["html"] for item in captured)]
        for document in documents:
            for secret in (*PRIVATE_MARKERS, *EXCLUDED_EVENT_IDS):
                self.assertNotIn(secret, document)
            self.assertIn(KEPT_TASK_ID, document)
            self.assertIn(KEPT_RUN_ID, document)
        self.assertIn(KEPT_EVENT_ID, html)
        for item in captured:
            self.assertIn(snapshot.snapshot_id, item["html"])
            self.assertIn(WITHHELD_WARNING, item["html"])
            self.assertIn(KEPT_EVENT_ID, item["html"])
        self.assertIn(WITHHELD_WARNING, html)
        metas = (html_meta, csv_meta, jpeg_meta, pdf_meta)
        counts = [_counts(meta) for meta in metas]
        self.assertEqual(counts[0], counts[1])
        self.assertEqual(counts[0], counts[2])
        self.assertEqual(counts[0], counts[3])
        for family, rows_before in base.items():
            expected = rows_before - 2 if family == "event" else rows_before
            self.assertEqual(counts[0][family], expected, family)
        for meta in metas:
            self.assertIn(WITHHELD_WARNING, meta["warnings"])
            self.assertEqual(meta["snapshot_id"], snapshot.snapshot_id)
        self.assertEqual(html_meta["renderer_version"], RENDERER_VERSION)
        self.assertEqual(csv_meta["renderer_version"], RENDERER_VERSION)
        self.assertEqual(jpeg_meta["renderer_version"], BROWSER_RENDERER_VERSION)
        self.assertEqual(pdf_meta["renderer_version"], BROWSER_RENDERER_VERSION)
        self.assertNotIn("aborted_urls", json.dumps(jpeg_meta))
        self.assertNotIn("aborted_urls", json.dumps(pdf_meta))

    def test_real_pdf_text_omits_withheld_event_detail(self) -> None:
        """Optional real PDF text check. Skips only a missing tool or browser."""
        home = _renderer_home()
        if home is None:
            self.skipTest(
                "SBTD_RENDERER_TEST_HOME is unset or has no browsers/ install"
            )
        if shutil.which("pdftotext") is None:
            self.skipTest("pdftotext is not installed")
        from browser_renderer import renderer_capability

        capability = renderer_capability(home)
        if not capability["available"]:
            self.skipTest(capability["reason"])
        binaries = _browser_binaries(home)
        dataset = _privacy_dataset()
        scope = _scope(dataset, ["tasks.touched", "steps.success_rate_observed"])
        snapshot = self.snapshots.create_or_reuse(dataset, scope)
        renderer = ExportRenderer(self.snapshots, home=home)
        store = self._open(renderer)
        export_id = store.create(snapshot.snapshot_id, "pdf", _detail_presentation())
        deadline = time.monotonic() + 180
        info = None
        while time.monotonic() < deadline:
            info = store.get(export_id)
            if info["status"] == "ready":
                break
            if info["status"] in ("failed", "cancelled"):
                self.fail(info)
            time.sleep(0.05)
        else:
            self.fail(info)
        blob, meta = store.download(export_id)
        self.assertEqual(meta["mime_type"], MIME["pdf"])
        self.assertEqual(meta["renderer_version"], BROWSER_RENDERER_VERSION)
        self.assertIn(WITHHELD_WARNING, meta["warnings"])
        self.assertNotIn("aborted_urls", json.dumps(meta))
        self.assertTrue(blob.startswith(PDF_PREFIX))
        pdf_path = Path(self.temporary.name) / "withheld.pdf"
        pdf_path.write_bytes(blob)
        extracted = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            check=False,
            capture_output=True,
        )
        self.assertEqual(extracted.returncode, 0, extracted.stderr)
        text = extracted.stdout.decode("utf-8", errors="replace")
        compact = "".join(text.split())
        self.assertTrue(compact, "pdftotext returned no searchable text")
        for secret in (*PRIVATE_MARKERS, *EXCLUDED_EVENT_IDS):
            self.assertNotIn(secret, compact)
        self.assertIn(KEPT_TASK_ID, compact)
        self.assertEqual(_browser_binaries(home), binaries)

    def test_preflight_measures_real_snapshot_without_capture(self) -> None:
        """Public preflight measures snapshot HTML and does not capture."""
        home = _renderer_home()
        if home is None:
            self.skipTest(
                "SBTD_RENDERER_TEST_HOME is unset or has no browsers/ install"
            )
        from browser_renderer import (
            BrowserRenderer,
            RendererError,
            _make_job_dir,
            _make_profile,
            renderer_capability,
        )

        capability = renderer_capability(home)
        if not capability["available"]:
            self.skipTest(capability["reason"])
        presentation = _presentation()
        sentinel = Path(self.temporary.name) / "capture-called"
        worker = (
            "import sys\n"
            f"sys.path.insert(0, {str(ROOT)!r})\n"
            "from pathlib import Path\n"
            "from playwright.sync_api import Page\n"
            "from browser_renderer import _worker_entry\n"
            f"sentinel = {str(sentinel)!r}\n"
            "def forbid(self, *args, **kwargs):\n"
            "    Path(sentinel).write_text('captured', encoding='utf-8')\n"
            "    raise RuntimeError('preflight must not capture')\n"
            "Page.screenshot = forbid\n"
            "Page.pdf = forbid\n"
            "sys.exit(_worker_entry(sys.argv[1]))\n"
        )
        jobs: list[Path] = []
        profiles: list[Path] = []

        def track_job() -> Path:
            path = _make_job_dir()
            jobs.append(path)
            return path

        def track_profile() -> Path:
            path = _make_profile()
            profiles.append(path)
            return path

        def assert_idle() -> None:
            self.assertFalse(sentinel.exists())
            self.assertFalse((self.home / "exports").exists())
            for path in (*jobs, *profiles):
                self.assertFalse(path.exists(), path)

        renderer = BrowserRenderer(home, self.snapshots)
        with (
            mock.patch(
                "browser_renderer._worker_argv",
                side_effect=lambda job: [sys.executable, "-c", worker, str(job)],
            ),
            mock.patch("browser_renderer._make_job_dir", side_effect=track_job),
            mock.patch("browser_renderer._make_profile", side_effect=track_profile),
        ):
            normal = renderer.preflight(self.snapshot, "jpeg", presentation)
            self.assertEqual(normal, {"scale": 2, "warnings": ["UNKNOWN_OCCURRED_AT"]})
            assert_idle()
            # 2x of this snapshot exceeds 9_000_000 px; 1x of the same page fits.
            with mock.patch("browser_renderer.MAX_PIXELS", 9_000_000):
                downgraded = renderer.preflight(self.snapshot, "jpeg", presentation)
            self.assertEqual(
                downgraded,
                {
                    "scale": 1,
                    "warnings": [
                        "UNKNOWN_OCCURRED_AT",
                        "EXPORT_SCALE_DOWNGRADED:1x",
                    ],
                },
            )
            assert_idle()
            with (
                mock.patch("browser_renderer.MAX_SIDE_PX", 1439),
                mock.patch("browser_renderer.MAX_PIXELS", 1_234_567),
                self.assertRaises(RendererError) as caught,
            ):
                renderer.preflight(self.snapshot, "jpeg", presentation)
            error = caught.exception
            self.assertEqual(error.code, "EXPORT_IMAGE_SIZE_LIMIT")
            self.assertEqual(str(error), "EXPORT_IMAGE_SIZE_LIMIT")
            self.assertEqual(error.max_edge_px, 1439)
            self.assertEqual(error.max_total_pixels, 1_234_567)
            self.assertNotIn("1439", str(error))
            self.assertNotIn("1234567", str(error))
            assert_idle()
            pdf = renderer.preflight(self.snapshot, "pdf", presentation)
            self.assertEqual(pdf, {"scale": None, "warnings": ["UNKNOWN_OCCURRED_AT"]})
            assert_idle()


class FrozenHttpExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="sbtd-renderer-http-")
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        _enable_observation(self.home)
        _seed_golden_events(self.home)
        self.port = _free_port()
        self.server = ServeProcess(self.home, self.port, "--no-open")
        self.addCleanup(self.stop_server)
        self.server.wait_ready()
        self.authenticate()

    def stop_server(self) -> None:
        if self.server.proc.poll() is None:
            self.server.stop()

    def authenticate(self) -> None:
        ticket = (self.home / "pairing-ticket").read_text(encoding="utf-8").strip()
        status, session, headers = pair(self.port, ticket)
        self.assertEqual(status, 200)
        self.headers = {
            "Authorization": f"Bearer {session['access_token']}",
            "X-CSRF-Token": headers["x-csrf-token"],
        }

    def snapshot(self) -> str:
        status, _, body = request(
            self.port,
            "POST",
            "/api/v1/statistics/query",
            body=_scope(_dataset(), ["tasks.touched"]),
            headers={**self.headers, "Idempotency-Key": uuid.uuid4().hex},
        )
        self.assertEqual(status, 200, body)
        return json.loads(body)["data"]["snapshot_id"]

    def create(self, format_name: str, snapshot_id: str | None = None):
        return request(
            self.port,
            "POST",
            "/api/v1/exports",
            body={
                "snapshot_id": snapshot_id or self.snapshot(),
                "format": format_name,
            },
            headers={**self.headers, "Idempotency-Key": uuid.uuid4().hex},
        )

    def ready(self, export_id: str) -> dict:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            status, _, body = request(
                self.port,
                "GET",
                f"/api/v1/exports/{export_id}",
                headers=self.headers,
            )
            self.assertEqual(status, 200, body)
            info = json.loads(body)["data"]
            if info["status"] == "ready":
                return info
            self.assertNotIn(info["status"], ("failed", "cancelled"), info)
            time.sleep(0.02)
        self.fail("export did not become ready")

    def test_http_pdf_is_accepted_then_fails_without_renderer(self) -> None:
        """Missing renderer keeps the async PDF path: 202, then failed."""
        status, _, body = self.create("pdf")
        self.assertEqual(status, 202, body)
        export_id = json.loads(body)["data"]["export_id"]
        deadline = time.monotonic() + 10
        info = None
        while time.monotonic() < deadline:
            status, _, payload = request(
                self.port,
                "GET",
                f"/api/v1/exports/{export_id}",
                headers=self.headers,
            )
            self.assertEqual(status, 200, payload)
            info = json.loads(payload)["data"]
            if info["status"] in ("failed", "cancelled", "ready"):
                break
            time.sleep(0.02)
        else:
            self.fail(info)
        self.assertEqual(info["status"], "failed", info)
        self.assertEqual(info["error"], "RENDERER_UNAVAILABLE")
        self.assertNotIn(str(self.home), json.dumps(info))
        status, _, download = request(
            self.port,
            "GET",
            f"/api/v1/exports/{export_id}/file",
            headers=self.headers,
        )
        self.assertEqual(status, 409, download)

    def test_capabilities_require_session_and_allowed_host_origin(self) -> None:
        for headers, expected in (
            ({}, 401),
            ({**self.headers, "Host": "external.invalid"}, 403),
            ({**self.headers, "Origin": "https://external.invalid"}, 403),
        ):
            with self.subTest(headers=list(headers), expected=expected):
                status, _, body = request(
                    self.port,
                    "GET",
                    "/api/v1/capabilities",
                    headers=headers,
                    host=headers.get("Host"),
                )
                self.assertEqual(status, expected, body)
                self.assertNotIn(b"http_available", body)

    def test_capabilities_absence_leaves_html_and_csv_usable(self) -> None:
        """Scenario: 缺少可选依赖不影响原有格式."""
        status, _, body = request(
            self.port,
            "GET",
            "/api/v1/capabilities",
            headers=self.headers,
        )
        self.assertEqual(status, 200, body)
        payload = json.loads(body)
        self.assertEqual(
            set(payload),
            {"api_version", "request_id", "data", "meta"},
        )
        exports = payload["data"]["exports"]
        self.assertEqual(set(exports), {"html", "csv", "jpeg", "pdf"})
        available = {
            "available": True,
            "reason": None,
            "http_available": True,
        }
        self.assertEqual(exports["html"], available)
        self.assertEqual(exports["csv"], available)
        self.assertFalse(exports["jpeg"]["available"])
        self.assertFalse(exports["pdf"]["available"])
        self.assertIsInstance(exports["jpeg"]["reason"], str)
        self.assertTrue(exports["jpeg"]["reason"])
        self.assertIsNone(exports["html"]["reason"])
        self.assertEqual(exports["jpeg"]["http_available"], False)
        self.assertEqual(
            exports["jpeg"]["http_available"], exports["jpeg"]["available"]
        )
        self.assertEqual(exports["pdf"]["http_available"], False)
        self.assertEqual(exports["pdf"]["http_available"], exports["pdf"]["available"])
        self.assertEqual(exports["jpeg"], exports["pdf"])
        encoded = json.dumps(payload)
        self.assertNotIn(str(self.home), encoded)
        snapshot_id = self.snapshot()
        for format_name, media_type in (
            ("html", "text/html"),
            ("csv", "text/csv"),
        ):
            with self.subTest(format=format_name):
                status, _, created = self.create(format_name, snapshot_id)
                self.assertEqual(status, 202, created)
                self.assertEqual(json.loads(created)["meta"]["warnings"], [])
                export_id = json.loads(created)["data"]["export_id"]
                info = self.ready(export_id)
                self.assertEqual(info["mime_type"], MIME[format_name])
                status, response_headers, blob = request(
                    self.port,
                    "GET",
                    f"/api/v1/exports/{export_id}/file",
                    headers=self.headers,
                )
                self.assertEqual(status, 200, blob)
                content_type = {
                    key.lower(): value for key, value in response_headers.items()
                }["content-type"]
                self.assertIn(media_type, content_type)
                self.assertTrue(blob)

    def test_http_unknown_format_is_rejected_without_a_job(self) -> None:
        """Invalid formats stay 400 and create no export files."""
        snapshot_id = self.snapshot()
        before = sorted(path.name for path in (self.home / "exports").glob("exp_*"))
        for format_name in ("png", "jpg", "JPEG", "PDF"):
            with self.subTest(format=format_name):
                status, _, body = self.create(format_name, snapshot_id)
                self.assertEqual(status, 400, body)
                self.assertNotIn(b"export_id", body)
        after = sorted(path.name for path in (self.home / "exports").glob("exp_*"))
        self.assertEqual(after, before)

    def test_http_jpeg_missing_renderer_is_unhandled_without_a_job(self) -> None:
        """JPEG preflight RendererError stays unhandled and creates no job."""
        snapshot_id = self.snapshot()
        before = sorted(path.name for path in (self.home / "exports").glob("exp_*"))
        status, _, body = self.create("jpeg", snapshot_id)
        self.assertEqual(status, 500, body)
        self.assertNotIn(b"export_id", body)
        self.assertNotIn(str(self.home).encode(), body)
        after = sorted(path.name for path in (self.home / "exports").glob("exp_*"))
        self.assertEqual(after, before)


def _openapi() -> dict:
    import yaml

    document = ROOT / "contracts" / "openapi.yaml"
    return yaml.safe_load(document.read_text(encoding="utf-8"))


def _create_export_validator(status: str):
    import jsonschema

    doc = _openapi()
    declared = doc["paths"]["/api/v1/exports"]["post"]["responses"]
    if status not in declared:
        raise AssertionError(f"createExport does not declare {status}")
    response = declared[status]
    if "$ref" in response:
        name = response["$ref"].rsplit("/", 1)[-1]
        response = doc["components"]["responses"][name]
    schema = ((response.get("content") or {}).get("application/json") or {}).get(
        "schema"
    )
    if schema is None:
        return None
    return jsonschema.Draft202012Validator(doc).evolve(schema=schema)


class _LoopbackApp:
    """In-process uvicorn so tests can patch browser_renderer._render_document."""

    def __init__(self, home: Path) -> None:
        import uvicorn
        from serve import BIND_HOST, TICKET_FILE_NAME, AccessControl, create_app

        self.port = _free_port()
        self.access = AccessControl()
        self.snapshots = SnapshotStore(home)
        self.exports = ExportStore(
            home, self.snapshots, ExportRenderer(self.snapshots, home=home)
        )
        with (
            mock.patch("serve.SnapshotStore", return_value=self.snapshots),
            mock.patch("serve.ExportStore", return_value=self.exports),
        ):
            self.app = create_app(home, self.access, self.port)
        ticket = home / TICKET_FILE_NAME
        fd = os.open(ticket, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(self.access.ticket + "\n")
        os.chmod(ticket, 0o600)
        config = uvicorn.Config(
            self.app,
            host=BIND_HOST,
            port=self.port,
            log_level="warning",
            access_log=False,
            timeout_graceful_shutdown=2,
        )
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(
            target=self.server.run, name="sbtd-http-test", daemon=True
        )
        self.thread.start()
        try:
            self._wait_ready()
        except BaseException:
            self.stop()
            raise

    def _wait_ready(self) -> None:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if not self.thread.is_alive():
                raise AssertionError("in-process serve exited before ready")
            try:
                status, _, _ = request(self.port, "GET", "/api/v1/health")
            except OSError:
                time.sleep(0.05)
                continue
            if status == 200:
                return
            time.sleep(0.05)
        raise AssertionError("in-process serve did not become ready")

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(15)
        if self.thread.is_alive():
            raise AssertionError("HTTP test server did not stop")


class HttpRendererSeamTests(unittest.TestCase):
    """App HTTP jpeg/pdf behavior mocked at browser_renderer._render_document."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="sbtd-renderer-seam-")
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        _enable_observation(self.home)
        _seed_golden_events(self.home)
        self.calls: list[dict] = []
        self.mode = "ok"
        self.entered = threading.Event()
        self.release = threading.Event()
        self.release.set()
        self._patches = _patched_worker(self._worker)
        self._patches.__enter__()
        self.addCleanup(self._patches.__exit__, None, None, None)
        self.server = _LoopbackApp(self.home)
        self.addCleanup(self.server.stop)
        self.addCleanup(self.release.set)
        self.port = self.server.port
        self.authenticate()

    def authenticate(self) -> None:
        ticket = (self.home / "pairing-ticket").read_text(encoding="utf-8").strip()
        status, session, headers = pair(self.port, ticket)
        self.assertEqual(status, 200)
        self.headers = {
            "Authorization": f"Bearer {session['access_token']}",
            "X-CSRF-Token": headers["x-csrf-token"],
        }

    def _worker(self, *args, **kwargs):
        from browser_renderer import RendererError

        html = kwargs.get("html", args[0] if args else None)
        if isinstance(html, bytes):
            html = html.decode("utf-8")
            if args:
                args = (html, *args[1:])
            kwargs = {**kwargs, "html": html}
        html, format_name = _accept_call(args, kwargs)
        preflight = bool(kwargs.get("preflight"))
        self.calls.append(
            {
                "html": html,
                "format": format_name,
                "preflight": preflight,
                "scale": kwargs.get("locked_scale"),
            }
        )
        if self.mode == "block" and preflight:
            self.entered.set()
            if not self.release.wait(10):
                raise AssertionError("blocked preflight was not released")
        if self.mode == "block_job" and not preflight:
            self.entered.set()
            if not self.release.wait(10):
                raise AssertionError("blocked job was not released")
        if format_name == "jpeg" and preflight and self.mode == "size":
            raise RendererError(
                "EXPORT_IMAGE_SIZE_LIMIT",
                max_edge_px=kwargs["max_side_px"],
                max_total_pixels=kwargs["max_pixels"],
            )
        if format_name == "jpeg" and preflight and self.mode == "fail_preflight":
            raise RendererError("RENDERER_FAILED")
        if not preflight and self.mode == "fail_job":
            raise RendererError("RENDERER_FAILED")
        scale = 1 if format_name == "jpeg" and self.mode == "downgrade" else 2
        warnings = (
            ["EXPORT_SCALE_DOWNGRADED:1x"]
            if format_name == "jpeg" and self.mode == "downgrade"
            else []
        )
        if preflight:
            return b"", {
                "scale": scale if format_name == "jpeg" else None,
                "warnings": list(warnings),
            }
        return _artifact(format_name), {
            "scale": scale if format_name == "jpeg" else None,
            "warnings": list(warnings),
        }

    def snapshot(self) -> str:
        status, _, body = request(
            self.port,
            "POST",
            "/api/v1/statistics/query",
            body=_scope(_dataset(), ["tasks.touched"]),
            headers={**self.headers, "Idempotency-Key": uuid.uuid4().hex},
        )
        self.assertEqual(status, 200, body)
        return json.loads(body)["data"]["snapshot_id"]

    def post(self, format_name: str, snapshot_id: str, *, key: str | None = None):
        return request(
            self.port,
            "POST",
            "/api/v1/exports",
            body={"snapshot_id": snapshot_id, "format": format_name},
            headers={**self.headers, "Idempotency-Key": key or uuid.uuid4().hex},
        )

    def until(self, export_id: str, status: str, *, timeout: float = 10) -> dict:
        deadline = time.monotonic() + timeout
        info = None
        while time.monotonic() < deadline:
            got, _, body = request(
                self.port,
                "GET",
                f"/api/v1/exports/{export_id}",
                headers=self.headers,
            )
            self.assertEqual(got, 200, body)
            info = json.loads(body)["data"]
            if info["status"] == status:
                return info
            if status == "ready" and info["status"] in ("failed", "cancelled"):
                self.fail(info)
            time.sleep(0.02)
        self.fail(info)

    def download(self, export_id: str):
        return request(
            self.port,
            "GET",
            f"/api/v1/exports/{export_id}/file",
            headers=self.headers,
        )

    def content_type(self, headers: dict[str, str]) -> str:
        return {key.lower(): value for key, value in headers.items()}["content-type"]

    def assert_schema(self, status: int, body: bytes) -> None:
        validator = _create_export_validator(str(status))
        if validator is not None:
            self.assertEqual(list(validator.iter_errors(json.loads(body))), [])

    def export_names(self) -> list[str]:
        return sorted(path.name for path in (self.home / "exports").glob("exp_*"))

    def test_jpeg_and_pdf_download_mocked_worker_bytes(self) -> None:
        snapshot_id = self.snapshot()
        for format_name in ("jpeg", "pdf"):
            with self.subTest(format=format_name):
                self.calls.clear()
                self.mode = "ok"
                status, _, body = self.post(format_name, snapshot_id)
                self.assertEqual(status, 202, body)
                self.assert_schema(202, body)
                accepted = json.loads(body)
                self.assertEqual(set(accepted["data"]), {"export_id"})
                if format_name == "pdf":
                    self.assertEqual(accepted["meta"]["warnings"], [])
                export_id = accepted["data"]["export_id"]
                info = self.until(export_id, "ready")
                self.assertEqual(info["mime_type"], MIME[format_name])
                status, headers, blob = self.download(export_id)
                self.assertEqual(status, 200, blob)
                self.assertIn(
                    MIME[format_name].split(";", 1)[0], self.content_type(headers)
                )
                self.assertTrue(
                    blob.startswith(
                        JPEG_PREFIX if format_name == "jpeg" else PDF_PREFIX
                    )
                )
                preflight = [call for call in self.calls if call["preflight"]]
                jobs = [call for call in self.calls if not call["preflight"]]
                if format_name == "pdf":
                    self.assertEqual(preflight, [])
                    self.assertEqual(len(jobs), 1)
                else:
                    self.assertEqual(len(preflight), 1)
                    self.assertEqual(len(jobs), 1)
                    self.assertEqual(preflight[0]["html"], jobs[0]["html"])
                    self.assertEqual(jobs[0]["scale"], 2)

    def test_jpeg_size_limit_is_422_without_job_file_or_pin(self) -> None:
        snapshot_id = self.snapshot()
        self.mode = "size"
        before = self.export_names()
        with (
            mock.patch("browser_renderer.MAX_SIDE_PX", 2222),
            mock.patch("browser_renderer.MAX_PIXELS", 333333),
        ):
            status, _, body = self.post("jpeg", snapshot_id)
        self.assertEqual(status, 422, body)
        self.assert_schema(422, body)
        self.assertEqual(
            json.loads(body),
            {
                "detail": "EXPORT_IMAGE_SIZE_LIMIT",
                "max_edge_px": 2222,
                "max_total_pixels": 333333,
            },
        )
        self.assertEqual(self.export_names(), before)
        self.assertEqual(self.server.exports._jobs, {})
        removed = self.server.snapshots.sweep(now=datetime.now(UTC) + timedelta(days=2))
        self.assertIn(snapshot_id, removed)

    def test_jpeg_downgrade_warning_matches_accepted_schema(self) -> None:
        self.mode = "downgrade"
        status, _, body = self.post("jpeg", self.snapshot())
        self.assertEqual(status, 202, body)
        self.assert_schema(202, body)
        accepted = json.loads(body)
        self.assertEqual(set(accepted["data"]), {"export_id"})
        self.assertEqual(
            accepted["meta"]["warnings"],
            ["UNKNOWN_OCCURRED_AT", "EXPORT_SCALE_DOWNGRADED:1x"],
        )
        info = self.until(accepted["data"]["export_id"], "ready")
        self.assertEqual(info["mime_type"], MIME["jpeg"])
        jobs = [call for call in self.calls if not call["preflight"]]
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["scale"], 1)

    def test_create_export_statuses_match_openapi(self) -> None:
        snapshot_id = self.snapshot()
        status, _, body = self.post("png", snapshot_id)
        self.assertEqual(status, 400, body)
        self.assert_schema(400, body)
        self.assertNotIn(b"export_id", body)
        status, _, body = self.post("jpeg", "snap_" + "f" * 32)
        self.assertEqual(status, 404, body)
        self.assert_schema(404, body)
        expired = SnapshotStore(self.home, ttl_seconds=1).create_or_reuse(
            _dataset(),
            _scope(_dataset(), ["steps.attempts"]),
            now=datetime.now(UTC) - timedelta(seconds=3),
        )
        status, _, body = self.post("csv", expired.snapshot_id)
        self.assertEqual(status, 410, body)
        self.assert_schema(410, body)
        self.mode = "downgrade"
        status, _, body = self.post("jpeg", snapshot_id)
        self.assertEqual(status, 202, body)
        self.assert_schema(202, body)
        self.assertIn(
            "EXPORT_SCALE_DOWNGRADED:1x", json.loads(body)["meta"]["warnings"]
        )
        self.until(json.loads(body)["data"]["export_id"], "ready")
        self.mode = "size"
        limited = self.snapshot()
        with (
            mock.patch("browser_renderer.MAX_SIDE_PX", 2222),
            mock.patch("browser_renderer.MAX_PIXELS", 333333),
        ):
            status, _, body = self.post("jpeg", limited)
        self.assertEqual(status, 422, body)
        self.assert_schema(422, body)
        self.assertEqual(json.loads(body)["max_edge_px"], 2222)
        self.assertEqual(json.loads(body)["max_total_pixels"], 333333)

    def test_capabilities_http_available_follows_renderer(self) -> None:
        status, _, body = request(
            self.port, "GET", "/api/v1/capabilities", headers=self.headers
        )
        self.assertEqual(status, 200, body)
        exports = json.loads(body)["data"]["exports"]
        for name in ("html", "csv", "jpeg", "pdf"):
            with self.subTest(format=name):
                self.assertTrue(exports[name]["available"])
                self.assertIsNone(exports[name]["reason"])
                self.assertTrue(exports[name]["http_available"])
                self.assertEqual(
                    exports[name]["http_available"], exports[name]["available"]
                )

    def test_idempotent_jpeg_replay_keeps_warning_without_new_preflight(self) -> None:
        self.mode = "downgrade"
        snapshot_id = self.snapshot()
        key = uuid.uuid4().hex
        status, _, body = self.post("jpeg", snapshot_id, key=key)
        self.assertEqual(status, 202, body)
        first = json.loads(body)
        self.assertIn("EXPORT_SCALE_DOWNGRADED:1x", first["meta"]["warnings"])
        self.until(first["data"]["export_id"], "ready")
        preflight = sum(1 for call in self.calls if call["preflight"])
        jobs = sum(1 for call in self.calls if not call["preflight"])
        status, _, body = self.post("jpeg", snapshot_id, key=key)
        self.assertEqual(status, 202, body)
        self.assert_schema(202, body)
        second = json.loads(body)
        self.assertEqual(second["data"], first["data"])
        self.assertEqual(second["meta"]["warnings"], first["meta"]["warnings"])
        self.assertEqual(sum(1 for call in self.calls if call["preflight"]), preflight)
        self.assertEqual(sum(1 for call in self.calls if not call["preflight"]), jobs)
        self.server.stop()
        self.server = _LoopbackApp(self.home)
        self.addCleanup(self.server.stop)
        self.port = self.server.port
        self.authenticate()
        status, _, body = self.post("jpeg", snapshot_id, key=key)
        self.assertEqual(status, 202, body)
        restored = json.loads(body)
        self.assertEqual(restored["data"], first["data"])
        self.assertEqual(restored["meta"]["warnings"], first["meta"]["warnings"])
        self.assertEqual(sum(1 for call in self.calls if call["preflight"]), preflight)
        self.assertEqual(sum(1 for call in self.calls if not call["preflight"]), jobs)

    def test_in_flight_jpeg_holds_snapshot_pin_until_ready(self) -> None:
        self.mode = "block_job"
        self.release.clear()
        self.entered.clear()
        snapshot_id = self.snapshot()
        holder: dict = {}

        def create() -> None:
            holder["result"] = self.post("jpeg", snapshot_id)

        thread = threading.Thread(target=create)
        thread.start()
        self.assertTrue(self.entered.wait(5), "job seam was not entered")
        thread.join(5)
        self.assertFalse(thread.is_alive())
        status, _, body = holder["result"]
        self.assertEqual(status, 202, body)
        export_id = json.loads(body)["data"]["export_id"]
        future = datetime.now(UTC) + timedelta(days=2)
        snapshots = self.server.snapshots
        self.assertNotIn(snapshot_id, snapshots.sweep(now=future))
        self.release.set()
        self.until(export_id, "ready")
        deadline = time.monotonic() + 2
        removed: list[str] = []
        while time.monotonic() < deadline:
            removed = snapshots.sweep(now=future)
            if snapshot_id in removed:
                break
            time.sleep(0.01)
        self.assertIn(snapshot_id, removed)

    def test_jpeg_preflight_does_not_block_the_event_loop(self) -> None:
        import http.client

        self.mode = "block"
        self.release.clear()
        self.entered.clear()
        snapshot_id = self.snapshot()
        holder: dict = {}

        def create() -> None:
            holder["result"] = self.post("jpeg", snapshot_id)

        thread = threading.Thread(target=create)
        thread.start()
        self.addCleanup(self.release.set)
        self.assertTrue(self.entered.wait(5), "preflight seam was not entered")
        started = time.monotonic()
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=1)
        try:
            connection.request(
                "GET",
                "/api/v1/health",
                headers={"Host": f"127.0.0.1:{self.port}"},
            )
            response = connection.getresponse()
            response.read()
            elapsed = time.monotonic() - started
            self.assertEqual(response.status, 200)
            self.assertLess(elapsed, 1)
        finally:
            connection.close()
        self.release.set()
        thread.join(10)
        self.assertEqual(holder["result"][0], 202, holder["result"][2])

    def test_jpeg_job_error_is_failed_and_download_conflict(self) -> None:
        self.mode = "fail_job"
        status, _, body = self.post("jpeg", self.snapshot())
        self.assertEqual(status, 202, body)
        export_id = json.loads(body)["data"]["export_id"]
        info = self.until(export_id, "failed")
        self.assertEqual(info["error"], "RENDERER_FAILED")
        self.assertNotIn(str(self.home), json.dumps(info))
        status, _, download = self.download(export_id)
        self.assertEqual(status, 409, download)
        self.assertEqual(self.export_names(), [])

    def test_jpeg_non_size_preflight_error_is_unhandled(self) -> None:
        snapshot_id = self.snapshot()
        self.mode = "fail_preflight"
        status, _, body = self.post("jpeg", snapshot_id)
        self.assertEqual(status, 500, body)
        self.assertNotIn(b"export_id", body)
        self.assertEqual(self.export_names(), [])
        removed = self.server.snapshots.sweep(now=datetime.now(UTC) + timedelta(days=2))
        self.assertIn(snapshot_id, removed)


class RealBrowserHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        renderer_home = _renderer_home()
        if renderer_home is None:
            self.skipTest(
                "SBTD_RENDERER_TEST_HOME is unset or has no browsers/ install"
            )
        from browser_renderer import renderer_capability

        capability = renderer_capability(renderer_home)
        if not capability["available"]:
            self.skipTest(capability["reason"] or "renderer unavailable")
        self.renderer_home = renderer_home
        self.binaries = _browser_binaries(renderer_home)
        self.temporary = tempfile.TemporaryDirectory(prefix="sbtd-renderer-http-real-")
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        shutil.copytree(renderer_home / "browsers", self.home / "browsers")
        shared = renderer_capability(self.home)
        if not shared["available"]:
            self.skipTest(shared["reason"] or "shared renderer unavailable")
        _enable_observation(self.home)
        _seed_golden_events(self.home)
        self.port = _free_port()
        self.server = ServeProcess(self.home, self.port, "--no-open")
        self.addCleanup(self.stop_server)
        self.server.wait_ready()
        ticket = (self.home / "pairing-ticket").read_text(encoding="utf-8").strip()
        status, session, headers = pair(self.port, ticket)
        self.assertEqual(status, 200)
        self.headers = {
            "Authorization": f"Bearer {session['access_token']}",
            "X-CSRF-Token": headers["x-csrf-token"],
        }

    def stop_server(self) -> None:
        if self.server.proc.poll() is None:
            self.server.stop()

    def test_real_browser_http_jpeg_and_pdf_download(self) -> None:
        status, _, body = request(
            self.port, "GET", "/api/v1/capabilities", headers=self.headers
        )
        self.assertEqual(status, 200, body)
        exports = json.loads(body)["data"]["exports"]
        for name in ("jpeg", "pdf"):
            self.assertTrue(exports[name]["available"], exports[name])
            self.assertTrue(exports[name]["http_available"], exports[name])
        status, _, queried = request(
            self.port,
            "POST",
            "/api/v1/statistics/query",
            body=_scope(_dataset(), ["tasks.touched"]),
            headers={**self.headers, "Idempotency-Key": uuid.uuid4().hex},
        )
        self.assertEqual(status, 200, queried)
        snapshot_id = json.loads(queried)["data"]["snapshot_id"]
        prefixes = {"jpeg": JPEG_PREFIX, "pdf": PDF_PREFIX}
        for format_name in ("jpeg", "pdf"):
            with self.subTest(format=format_name):
                status, _, created = request(
                    self.port,
                    "POST",
                    "/api/v1/exports",
                    body={"snapshot_id": snapshot_id, "format": format_name},
                    headers={**self.headers, "Idempotency-Key": uuid.uuid4().hex},
                )
                self.assertEqual(status, 202, created)
                accepted = json.loads(created)
                self.assertEqual(set(accepted["data"]), {"export_id"})
                if format_name == "pdf":
                    self.assertEqual(accepted["meta"]["warnings"], [])
                export_id = accepted["data"]["export_id"]
                deadline = time.monotonic() + 180
                info = None
                while time.monotonic() < deadline:
                    status, _, payload = request(
                        self.port,
                        "GET",
                        f"/api/v1/exports/{export_id}",
                        headers=self.headers,
                    )
                    self.assertEqual(status, 200, payload)
                    info = json.loads(payload)["data"]
                    if info["status"] == "ready":
                        break
                    self.assertNotIn(info["status"], ("failed", "cancelled"), info)
                    time.sleep(0.05)
                else:
                    self.fail(info)
                self.assertEqual(info["mime_type"], MIME[format_name])
                status, headers, blob = request(
                    self.port,
                    "GET",
                    f"/api/v1/exports/{export_id}/file",
                    headers=self.headers,
                )
                self.assertEqual(status, 200, blob)
                content_type = {key.lower(): value for key, value in headers.items()}[
                    "content-type"
                ]
                self.assertIn(MIME[format_name].split(";", 1)[0], content_type)
                self.assertTrue(blob.startswith(prefixes[format_name]))
        self.assertEqual(_browser_binaries(self.renderer_home), self.binaries)


if __name__ == "__main__":
    unittest.main()
