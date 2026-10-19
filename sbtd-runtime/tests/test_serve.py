"""D5–D8 serve tests: real sockets, real subprocesses, real audit store.

No mocks stand in for the behavior under test: servers run as real
`python -m serve` subprocesses on real loopback ports, tickets are read
from the real 0600 file, and metric values are cross-checked against the
in-process library on the same seeded events.
"""

from __future__ import annotations

import http.client
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]
REPO = RUNTIME.parent
GOLDEN = RUNTIME / "golden"


def _free_port() -> int:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


def _enable_observation(home: Path) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "observation": {
                    "enabled": True,
                    "level": "metadata",
                    "failure_policy": "best-effort",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _seed_golden_events(home: Path) -> None:
    """Ingest real golden events through the real EventStore API."""
    sys.path.insert(0, str(RUNTIME))
    from event_store import EventStore

    dataset = json.loads((GOLDEN / "dataset.json").read_text(encoding="utf-8"))
    store = EventStore.open(home, confirmed=True)
    try:
        result = store.append(dataset["events"])
    finally:
        store.close()
    accepted = [o for o in result.outcomes if o.status == "accepted"]
    if not accepted:
        raise AssertionError(f"golden events not accepted: {result.outcomes}")


class ServeProcess:
    """A real serve subprocess with captured output."""

    def __init__(self, home: Path, port: int, *extra: str) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(RUNTIME)
        self.proc = subprocess.Popen(
            [
                sys.executable,
                "-B",
                "-m",
                "serve",
                "--port",
                str(port),
                "--home",
                str(home),
                *extra,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=REPO,
        )
        self.port = port

    def wait_ready(self, timeout: float = 15.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                out, err = self.proc.communicate()
                raise AssertionError(
                    f"serve exited early rc={self.proc.returncode}\n{out}\n{err}"
                )
            try:
                status, _, _ = request(self.port, "GET", "/api/v1/health")
            except OSError:
                time.sleep(0.1)
                continue
            if status == 200:
                return
            time.sleep(0.1)
        raise AssertionError("serve did not become ready")

    def stop(self) -> tuple[str, str, int]:
        self.proc.send_signal(signal.SIGINT)
        out, err = self.proc.communicate(timeout=15)
        return out, err, self.proc.returncode

    def kill(self) -> tuple[str, str]:
        self.proc.kill()
        out, err = self.proc.communicate(timeout=15)
        return out, err


def request(
    port: int,
    method: str,
    path: str,
    *,
    body: object = None,
    headers: dict[str, str] | None = None,
    host: str | None = None,
) -> tuple[int, dict[str, str], bytes]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    merged = dict(headers or {})
    merged["Host"] = host or f"127.0.0.1:{port}"
    payload = None
    if body is not None:
        payload = json.dumps(body)
        merged["Content-Type"] = "application/json"
    conn.request(method, path, body=payload, headers=merged)
    response = conn.getresponse()
    data = response.read()
    result = (response.status, dict(response.getheaders()), data)
    conn.close()
    return result


def pair(port: int, ticket: str) -> tuple[int, dict, dict[str, str]]:
    status, headers, body = request(
        port, "POST", "/api/v1/session/pair", headers={"X-Pairing-Code": ticket}
    )
    return status, json.loads(body), {k.lower(): v for k, v in headers.items()}


class PortConflictTests(unittest.TestCase):
    """D5: busy port → startup fails, hints --port, non-zero exit."""

    def test_port_in_use_fails_with_port_hint(self) -> None:
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocker.bind(("127.0.0.1", 0))
        blocker.listen(1)
        port = blocker.getsockname()[1]
        try:
            with tempfile.TemporaryDirectory() as tmp:
                proc = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        "-m",
                        "serve",
                        "--port",
                        str(port),
                        "--no-open",
                        "--home",
                        tmp,
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env={**os.environ, "PYTHONPATH": str(RUNTIME)},
                    cwd=REPO,
                )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("--port", proc.stderr)
            self.assertIn(str(port), proc.stderr)
        finally:
            blocker.close()


class InstanceLockTests(unittest.TestCase):
    """D6: instance lock + double port judgment + stale lock invalid."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        _enable_observation(self.home)
        self.port = _free_port()
        self.server: ServeProcess | None = None

    def tearDown(self) -> None:
        if self.server is not None and self.server.proc.poll() is None:
            self.server.kill()
        self.tmp.cleanup()

    def test_second_instance_reports_live_instance(self) -> None:
        self.server = ServeProcess(self.home, self.port, "--no-open")
        self.server.wait_ready()
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "serve",
                "--port",
                str(self.port),
                "--no-open",
                "--home",
                str(self.home),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "PYTHONPATH": str(RUNTIME)},
            cwd=REPO,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("已有", proc.stderr)
        self.assertIn("--port", proc.stderr)

    def test_stale_lock_is_treated_as_invalid(self) -> None:
        lock = self.home / "serve.lock"
        # Find a pid that is actually dead right now.
        pid = 2**22
        while _pid_alive(pid):
            pid += 1
        lock.write_text(
            json.dumps({"pid": pid, "port": self.port}) + "\n", encoding="utf-8"
        )
        self.server = ServeProcess(self.home, self.port, "--no-open")
        self.server.wait_ready()  # stale lock removed, startup proceeds
        self.server.stop()
        self.server = None
        self.assertFalse(lock.exists())

    def test_corrupt_lock_is_treated_as_invalid(self) -> None:
        (self.home / "serve.lock").write_text("not json\n", encoding="utf-8")
        self.server = ServeProcess(self.home, self.port, "--no-open")
        self.server.wait_ready()

    def test_ctrl_c_shutdown_exit_zero_and_lock_removed(self) -> None:
        self.server = ServeProcess(self.home, self.port, "--no-open")
        self.server.wait_ready()
        self.assertTrue((self.home / "serve.lock").exists())
        _out, _err, rc = self.server.stop()
        self.server = None
        self.assertEqual(rc, 0)
        self.assertFalse((self.home / "serve.lock").exists())


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


class PairingTests(unittest.TestCase):
    """D7: one-time ticket pairing, read-and-destroy, never printed."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        _enable_observation(self.home)
        self.port = _free_port()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _start(self) -> ServeProcess:
        server = ServeProcess(self.home, self.port, "--no-open")
        server.wait_ready()
        return server

    def _ticket(self) -> str:
        path = self.home / "pairing-ticket"
        self.assertTrue(path.exists())
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        return path.read_text(encoding="utf-8").strip()

    def test_pair_once_only_and_ticket_never_in_output(self) -> None:
        server = self._start()
        ticket = self._ticket()
        status, session, headers = pair(self.port, ticket)
        self.assertEqual(status, 200)
        self.assertEqual(session["token_type"], "bearer")
        self.assertIsInstance(session["access_token"], str)
        self.assertGreaterEqual(session["expires_in"], 1)
        self.assertTrue(headers.get("x-csrf-token"))
        # Destroyed on read: the same ticket never pairs twice.
        again, _, _ = pair(self.port, ticket)
        self.assertEqual(again, 401)
        out, err, _rc = server.stop()
        self.assertNotIn(ticket, out)
        self.assertNotIn(ticket, err)

    def test_wrong_ticket_unauthorized_and_destroys(self) -> None:
        server = self._start()
        ticket = self._ticket()
        wrong, _, _ = pair(self.port, "wrong-" + ticket[::-1])
        self.assertEqual(wrong, 401)
        # Read-and-destroy: even the correct ticket is now worthless.
        after, _, _ = pair(self.port, ticket)
        self.assertEqual(after, 401)
        server.stop()


class HostOriginAndApiTests(unittest.TestCase):
    """D8 Host/Origin whitelist; auth/CSRF; static; real data wiring."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.home = Path(cls.tmp.name)
        _enable_observation(cls.home)
        _seed_golden_events(cls.home)
        cls.port = _free_port()
        cls.server = ServeProcess(cls.home, cls.port, "--no-open")
        cls.server.wait_ready()
        ticket = (cls.home / "pairing-ticket").read_text(encoding="utf-8").strip()
        status, session, headers = pair(cls.port, ticket)
        assert status == 200, session
        cls.bearer = session["access_token"]
        cls.csrf = headers["x-csrf-token"]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.stop()
        cls.tmp.cleanup()

    def api(self, method: str, path: str, **kwargs: object) -> tuple[int, dict, bytes]:
        status, _headers, body = request(self.port, method, path, **kwargs)  # type: ignore[arg-type]
        try:
            return status, json.loads(body), body
        except json.JSONDecodeError:
            return status, {}, body

    def test_health_needs_no_session(self) -> None:
        status, body, _ = self.api("GET", "/api/v1/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})

    def test_host_whitelist_rejects_external_and_wrong_port(self) -> None:
        cases = [
            f"evil.com:{self.port}",
            f"127.0.0.1:{self.port + 1}",
            f"127.0.0.1.evil.com:{self.port}",
            "127.0.0.1",
            "no-such-host.test:80",
        ]
        for host in cases:
            with self.subTest(host=host):
                status, _, _ = request(self.port, "GET", "/api/v1/health", host=host)
                self.assertEqual(status, 403)
        for host in (f"localhost:{self.port}", f"127.0.0.1:{self.port}"):
            status, _, _ = request(self.port, "GET", "/api/v1/health", host=host)
            self.assertEqual(status, 200)

    def test_origin_full_match(self) -> None:
        origins = [
            (f"http://evil.com:{self.port}", 403),
            (f"https://127.0.0.1:{self.port}", 403),
            ("http://127.0.0.1:9999", 403),
            (f"http://127.0.0.1:{self.port}", 200),
            (f"http://localhost:{self.port}", 200),
        ]
        for origin, expected in origins:
            with self.subTest(origin=origin):
                status, _, _ = request(
                    self.port, "GET", "/api/v1/health", headers={"Origin": origin}
                )
                self.assertEqual(status, expected)

    def test_static_served_and_confined(self) -> None:
        status, headers, body = request(self.port, "GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b'<div id="root">', body)
        lowered = {key.lower(): value for key, value in headers.items()}
        self.assertIn("text/html", lowered.get("content-type", ""))
        assets = list((RUNTIME / "dashboard" / "static" / "assets").iterdir())
        self.assertTrue(assets)
        status, _, body = request(self.port, "GET", f"/assets/{assets[0].name}")
        self.assertEqual(status, 200)
        self.assertEqual(len(body), assets[0].stat().st_size)
        # Path traversal never escapes the committed artifact directory.
        status, _, _ = request(self.port, "GET", "/../../contracts/openapi.yaml")
        self.assertIn(status, (400, 404))
        status, _, _ = request(
            self.port, "GET", "/%2e%2e/%2e%2e/contracts/openapi.yaml"
        )
        self.assertIn(status, (400, 404))
        # Host check applies to static too.
        status, _, _ = request(self.port, "GET", "/", host=f"evil.com:{self.port}")
        self.assertEqual(status, 403)

    def test_api_requires_bearer_and_csrf(self) -> None:
        status, _, _ = self.api("GET", "/api/v1/metrics/catalog")
        self.assertEqual(status, 401)
        scope = {
            "schema_version": "1.0",
            "range": {
                "from": "2026-10-15T00:00:00Z",
                "to": "2026-10-17T00:00:00Z",
                "timezone": "UTC",
            },
            "metrics": ["tasks.touched"],
        }
        status, _, _ = self.api(
            "POST",
            "/api/v1/statistics/query",
            body=scope,
            headers={"Authorization": f"Bearer {self.bearer}"},
        )
        self.assertEqual(status, 403)  # missing CSRF on unsafe method
        status, _, _ = self.api(
            "POST",
            "/api/v1/statistics/query",
            body=scope,
            headers={
                "Authorization": f"Bearer {self.bearer}",
                "X-CSRF-Token": "not-the-csrf-token",
            },
        )
        self.assertEqual(status, 403)

    def test_statistics_query_matches_library_on_same_events(self) -> None:
        sys.path.insert(0, str(RUNTIME))
        from serve import load_dataset
        from stats_query import query

        dataset, warnings = load_dataset(self.home)
        self.assertEqual(warnings, [])
        self.assertTrue(dataset["events"])
        scope = {
            "schema_version": "1.0",
            "range": {
                "from": "2026-10-15T00:00:00Z",
                "to": "2026-10-17T00:00:00Z",
                "timezone": "UTC",
            },
            "metrics": ["tasks.touched", "usage.tokens", "validations.run_pass_rate"],
        }
        status, envelope, _ = self.api(
            "POST",
            "/api/v1/statistics/query",
            body=scope,
            headers={
                "Authorization": f"Bearer {self.bearer}",
                "X-CSRF-Token": self.csrf,
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(envelope["api_version"], "1")
        self.assertIsInstance(envelope["request_id"], str)
        expected = query(dataset, scope)["metrics"]
        actual = envelope["data"]["metrics"]
        for metric_id in scope["metrics"]:
            self.assertEqual(
                actual[metric_id]["value"], expected[metric_id]["value"], metric_id
            )
            self.assertEqual(
                actual[metric_id]["support"], expected[metric_id]["support"], metric_id
            )
        # Snapshot attached by the server-side SnapshotStore is fetchable.
        snapshot_id = envelope["data"]["snapshot_id"]
        status, snap_envelope, _ = self.api(
            "GET",
            f"/api/v1/report-snapshots/{snapshot_id}",
            headers={"Authorization": f"Bearer {self.bearer}"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(snap_envelope["data"]["snapshot_id"], snapshot_id)
        # Unknown snapshot ids are honest 404s.
        status, _, _ = self.api(
            "GET",
            "/api/v1/report-snapshots/snap_does_not_exist",
            headers={"Authorization": f"Bearer {self.bearer}"},
        )
        self.assertEqual(status, 404)

    def test_invalid_scope_is_400_not_silent_default(self) -> None:
        status, _, _ = self.api(
            "POST",
            "/api/v1/statistics/query",
            body={"schema_version": "9.9", "range": {}, "metrics": []},
            headers={
                "Authorization": f"Bearer {self.bearer}",
                "X-CSRF-Token": self.csrf,
            },
        )
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
