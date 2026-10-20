"""Real HTTP acceptance for spec/r2.1a-export-scenarios.md."""

from __future__ import annotations

import copy
import hashlib
import http.client
import json
import tempfile
import time
import unittest
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from report_snapshot import SnapshotStore
from test_csv_export import _dataset, _scope
from test_serve import (
    ServeProcess,
    _enable_observation,
    _free_port,
    _seed_golden_events,
    pair,
    request,
)


class ExportHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
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
        ticket = (self.home / "pairing-ticket").read_text().strip()
        status, session, headers = pair(self.port, ticket)
        self.assertEqual(status, 200)
        self.headers = {
            "Authorization": f"Bearer {session['access_token']}",
            "X-CSRF-Token": headers["x-csrf-token"],
            "Idempotency-Key": uuid.uuid4().hex,
        }

    def snapshot(self) -> str:
        status, _, body = request(
            self.port,
            "POST",
            "/api/v1/statistics/query",
            body=_scope(_dataset(), ["tasks.touched", "usage.tokens"]),
            headers=self.headers,
        )
        self.assertEqual(status, 200, body)
        return json.loads(body)["data"]["snapshot_id"]

    def test_accepts_fixed_snapshot_and_returns_export_id(self) -> None:
        status, _, body = request(
            self.port,
            "POST",
            "/api/v1/exports",
            body={"snapshot_id": self.snapshot(), "format": "csv"},
            headers=self.headers,
        )
        self.assertEqual(status, 202, body)
        data = json.loads(body)["data"]
        self.assertEqual(set(data), {"export_id"})
        self.assertIsInstance(data["export_id"], str)

    def create_export(self, body: dict, *, headers: dict | None = None):
        return request(
            self.port,
            "POST",
            "/api/v1/exports",
            body=body,
            headers=headers or {**self.headers, "Idempotency-Key": uuid.uuid4().hex},
        )

    def presentation(self) -> dict:
        manifest = json.loads(
            (
                Path(__file__).resolve().parents[1] / "contracts/panel-manifest.json"
            ).read_text()
        )
        return {
            "theme": "light",
            "report_width_px": 1440,
            "expanded_detail_ids": [],
            "table_sort": {},
            "preview_row_sets": {},
            "panel_order": [p["panel_id"] for p in manifest["panels"]],
            "legend_state": {},
        }

    def ready(self, export_id: str) -> dict:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            status, _, body = request(
                self.port, "GET", f"/api/v1/exports/{export_id}", headers=self.headers
            )
            self.assertEqual(status, 200, body)
            info = json.loads(body)["data"]
            if info["status"] == "ready":
                return info
            self.assertNotIn(info["status"], ("failed", "cancelled"), info)
            time.sleep(0.02)
        self.fail("export did not become ready")

    def test_closed_request_and_presentation_validation(self) -> None:
        valid = {"snapshot_id": self.snapshot(), "format": "csv"}
        cases = [
            {},
            {"snapshot_id": valid["snapshot_id"]},
            {"format": "html"},
            {**valid, "snapshot_id": "snap_bad"},
            {**valid, "snapshot_id": 123},
            {**valid, "snapshot_id": "snap_" + "a" * 32 + "\n"},
            {**valid, "format": "pdf"},
            {**valid, "format": None},
            {**valid, "format": ["html"]},
            {**valid, "extra": True},
            {**valid, "presentation_state": None},
            {**valid, "presentation_state": {}},
        ]
        state = self.presentation()
        for name, value in [
            ("theme", "auto"),
            ("report_width_px", -1),
            ("report_width_px", True),
            ("report_width_px", float("inf")),
            ("expanded_detail_ids", [1]),
            ("table_sort", {"table": 1}),
            ("preview_row_sets", {"table": -1}),
            ("preview_row_sets", {"table": True}),
            ("legend_state", {"series": 1}),
            ("extra", "unknown"),
        ]:
            cases.append({**valid, "presentation_state": {**state, name: value}})
        for name in state:
            incomplete = copy.deepcopy(state)
            del incomplete[name]
            cases.append({**valid, "presentation_state": incomplete})
        for body in cases:
            with self.subTest(body=body):
                status, _, _ = self.create_export(body)
                self.assertEqual(status, 400)
        for value in (0, 0.5):
            body = {
                **valid,
                "presentation_state": {
                    **state,
                    "report_width_px": value,
                    "preview_row_sets": {"table": value},
                },
            }
            status, _, payload = self.create_export(body)
            self.assertEqual(status, 202, payload)
            self.ready(json.loads(payload)["data"]["export_id"])

    def test_panel_order_requires_complete_unique_manifest_permutation(self) -> None:
        state = self.presentation()
        ids = state["panel_order"]
        for order in (
            [],
            ids[:-1],
            ids + [ids[0]],
            [*ids[:-1], "foreign-panel"],
            [*ids[:-1], ids[0]],
        ):
            with self.subTest(order=order):
                status, _, _ = self.create_export(
                    {
                        "snapshot_id": self.snapshot(),
                        "format": "html",
                        "presentation_state": {**state, "panel_order": order},
                    }
                )
                self.assertEqual(status, 400)
        reverse = list(reversed(ids))
        status, _, body = self.create_export(
            {
                "snapshot_id": self.snapshot(),
                "format": "html",
                "presentation_state": {**state, "panel_order": reverse},
            }
        )
        self.assertEqual(status, 202, body)
        export_id = json.loads(body)["data"]["export_id"]
        self.ready(export_id)
        status, _, body = request(
            self.port, "GET", f"/api/v1/exports/{export_id}/file", headers=self.headers
        )
        self.assertEqual(status, 200)
        text = body.decode()
        positions = [text.index(f'id="{panel_id}"') for panel_id in reverse]
        self.assertEqual(positions, sorted(positions))

    def test_missing_foreign_and_expired_snapshot_errors(self) -> None:
        with tempfile.TemporaryDirectory() as other:
            foreign = SnapshotStore(Path(other)).create_or_reuse(
                _dataset(), _scope(_dataset(), ["tasks.touched"])
            )
            for snapshot_id in ("snap_" + "f" * 32, foreign.snapshot_id):
                status, _, _ = self.create_export(
                    {"snapshot_id": snapshot_id, "format": "csv"}
                )
                self.assertEqual(status, 404)
        # The existing single-writer contract permits this test setup only while
        # the server is idle; it reads files by ID, not just its startup index.
        expired = SnapshotStore(self.home, ttl_seconds=1).create_or_reuse(
            _dataset(),
            _scope(_dataset(), ["steps.attempts"]),
            now=datetime.now(UTC) - timedelta(seconds=3),
        )
        status, _, _ = self.create_export(
            {"snapshot_id": expired.snapshot_id, "format": "csv"}
        )
        self.assertEqual(status, 410)

    def test_download_auth_path_boundary_and_delete(self) -> None:
        status, _, body = self.create_export(
            {"snapshot_id": self.snapshot(), "format": "csv"}
        )
        self.assertEqual(status, 202, body)
        export_id = json.loads(body)["data"]["export_id"]
        self.ready(export_id)
        path = f"/api/v1/exports/{export_id}/file"
        self.assertEqual(request(self.port, "GET", path)[0], 401)
        self.assertEqual(
            request(
                self.port, "GET", path, headers={"Authorization": "Bearer foreign"}
            )[0],
            401,
        )
        for suffix in ("?file_path=/etc/passwd", "?path=../snapshots"):
            self.assertEqual(
                request(self.port, "GET", path + suffix, headers=self.headers)[0], 400
            )
        for foreign in ("exp_" + "f" * 32, "%2e%2e%2fconfig.json", "..%5cconfig.json"):
            self.assertEqual(
                request(
                    self.port,
                    "GET",
                    f"/api/v1/exports/{foreign}/file",
                    headers=self.headers,
                )[0],
                404,
            )
        status, _, _ = request(
            self.port, "DELETE", f"/api/v1/exports/{export_id}", headers=self.headers
        )
        self.assertEqual(status, 204)
        self.assertNotEqual(
            request(self.port, "GET", path, headers=self.headers)[0], 200
        )

    def test_identical_download_bytes_and_digest_after_real_restart(self) -> None:
        exports = []
        snapshot_id = self.snapshot()
        for format_name in ("html", "csv"):
            status, _, body = self.create_export(
                {"snapshot_id": snapshot_id, "format": format_name}
            )
            self.assertEqual(status, 202, body)
            export_id = json.loads(body)["data"]["export_id"]
            info = self.ready(export_id)
            path = f"/api/v1/exports/{export_id}/file"
            first = request(self.port, "GET", path, headers=self.headers)
            second = request(self.port, "GET", path, headers=self.headers)
            self.assertEqual(first[0], 200)
            self.assertEqual(first[2], second[2])
            self.assertEqual(info["sha256"], hashlib.sha256(first[2]).hexdigest())
            self.assertEqual(info["byte_count"], len(first[2]))
            self.assertEqual(
                datetime.fromisoformat(info["expires_at"])
                - datetime.fromisoformat(info["ready_at"]),
                timedelta(hours=24),
            )
            exports.append((path, first[2], info))
        _, _, code = self.server.stop()
        self.assertEqual(code, 0)
        self.server = ServeProcess(self.home, self.port, "--no-open")
        self.server.wait_ready()
        self.authenticate()
        for path, original, info in exports:
            status, _, blob = request(self.port, "GET", path, headers=self.headers)
            self.assertEqual(status, 200, blob)
            self.assertEqual(
                hashlib.sha256(blob).hexdigest(), hashlib.sha256(original).hexdigest()
            )
            self.assertEqual(blob, original)
            current = self.ready(info["export_id"])
            self.assertEqual(current["expires_at"], info["expires_at"])
            self.assertEqual(current["sha256"], info["sha256"])

    def test_required_headers_and_idempotent_creation(self) -> None:
        body = {"snapshot_id": self.snapshot(), "format": "csv"}
        for missing, expected in (
            ("Authorization", 401),
            ("X-CSRF-Token", 403),
            ("Idempotency-Key", 400),
        ):
            headers = {k: v for k, v in self.headers.items() if k != missing}
            self.assertEqual(self.create_export(body, headers=headers)[0], expected)
        first = self.create_export(body, headers=self.headers)
        second = self.create_export(body, headers=self.headers)
        self.assertEqual(first[0], 202)
        self.assertEqual(json.loads(first[2])["data"], json.loads(second[2])["data"])
        self.assertEqual(
            self.create_export({**body, "format": "html"}, headers=self.headers)[0], 400
        )

    def test_malformed_json_and_wrong_media_type_are_bad_requests(self) -> None:
        for body, media_type in (
            (b"", "application/json"),
            (b"{", "application/json"),
            (b"\xff", "application/json"),
            (b"[]", "application/json"),
            (b"null", "application/json"),
            (b"{}", "text/plain"),
        ):
            with self.subTest(body=body, media_type=media_type):
                connection = http.client.HTTPConnection(
                    "127.0.0.1", self.port, timeout=10
                )
                try:
                    connection.request(
                        "POST",
                        "/api/v1/exports",
                        body=body,
                        headers={**self.headers, "Content-Type": media_type},
                    )
                    response = connection.getresponse()
                    response.read()
                    self.assertEqual(response.status, 400)
                finally:
                    connection.close()
