"""R2.1b library JPEG/PDF integration; spec/r2.1b-renderer-scenarios.md.

Traces missing-renderer capabilities, frozen HTTP rejection, shared
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
        self.assertEqual(exports["pdf"]["http_available"], False)
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

    def test_http_jpeg_and_pdf_are_rejected_without_a_job(self) -> None:
        """Scenario: HTTP 继续服从冻结契约."""
        snapshot_id = self.snapshot()
        before = sorted(path.name for path in (self.home / "exports").glob("exp_*"))
        for format_name in ("jpeg", "pdf"):
            with self.subTest(format=format_name):
                status, _, body = self.create(format_name, snapshot_id)
                self.assertEqual(status, 400, body)
                self.assertNotIn(b"export_id", body)
        after = sorted(path.name for path in (self.home / "exports").glob("exp_*"))
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
