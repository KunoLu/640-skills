"""R2.0a PR-2: ``serve`` — local dashboard HTTP service (locked decisions D5–D8).

Starlette + uvicorn (ADR 0001 §2) over the R1 in-process library surface
(``stats_query`` / ``report_snapshot``); no mocked numbers. Contract:
``contracts/openapi.yaml`` — this module aligns to it and never amends it.

- D5: a busy port fails startup with a ``--port`` hint and a non-zero exit.
- D6: foreground Ctrl-C shutdown; ``--open`` by default; an instance lock
  under SBTD_RUNTIME_HOME plus a second, independent port check; a stale
  lock (dead pid / unreadable / corrupt) is treated as invalid.
- D7: a one-time ticket reaches the browser only via the URL fragment of
  the auto-opened URL; it is exchanged (``X-Pairing-Code`` header) for a
  short-lived session Bearer + CSRF token, destroyed on read, never logged,
  never printed to the terminal. Without a browser the ticket is written to
  a 0600 file under SBTD_RUNTIME_HOME for manual pairing (ADR 0002 §3).
- D8: Host whitelist (localhost / 127.0.0.1 / [::1] with the exact serving
  port) and Origin full match, rules hardcoded — no configuration surface.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import math
import os
import re
import secrets
import socket
import sys
import uuid
import webbrowser
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from event_store import EventStore, StoreError
from export_render import ExportRenderer, default_presentation, load_panel_manifest
from export_store import ExportGone, ExportNotFound, ExportNotReady, ExportStore
from history_read import CursorError
from report_snapshot import (
    SnapshotGone,
    SnapshotNotFound,
    SnapshotStore,
    validate_snapshot_home,
)
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from stats_query import QueryScopeError, query, serve_catalog

BIND_HOST = "127.0.0.1"
DEFAULT_PORT = 6400
TICKET_TTL_SECONDS = 300
SESSION_TTL_SECONDS = 8 * 3600
LOCK_FILE_NAME = "serve.lock"
TICKET_FILE_NAME = "pairing-ticket"
# D8: hardcoded whitelist, no configuration surface.
ALLOWED_HOSTNAMES = frozenset({"localhost", "127.0.0.1", "::1"})
# Envelope meta projection_version: R1/R2.0a has no projection store
# (projections.db is never created); "0" states that honestly.
PROJECTION_VERSION = "0"

_PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = _PACKAGE_DIR / "dashboard" / "static"


class ServeError(Exception):
    """Startup precondition failure (port busy, live instance lock)."""


def default_runtime_home() -> Path:
    return Path(os.environ.get("SBTD_RUNTIME_HOME") or Path.home() / ".sbtd-runtime")


# --- D8: Host / Origin -----------------------------------------------------


def _split_host_port(authority: str) -> tuple[str, int | None] | None:
    """Parse a Host authority; returns (lowercased hostname, port) or None."""
    authority = authority.strip()
    if not authority:
        return None
    if authority.startswith("["):
        end = authority.find("]")
        if end == -1:
            return None
        hostname = authority[1:end]
        rest = authority[end + 1 :]
        if not rest:
            return hostname, None
        if not rest.startswith(":") or not rest[1:].isdigit():
            return None
        return hostname, int(rest[1:])
    if authority.count(":") > 1:
        # Bare IPv6 literal without brackets in a Host header.
        try:
            ipaddress.ip_address(authority)
        except ValueError:
            return None
        return authority.lower(), None
    if ":" in authority:
        hostname, _, port_text = authority.rpartition(":")
        if not port_text.isdigit():
            return None
        return hostname.lower(), int(port_text)
    return authority.lower(), None


def host_allowed(host_header: str | None, port: int) -> bool:
    """Host must name a loopback hostname and the exact serving port (D8)."""
    if host_header is None:
        return False
    parsed = _split_host_port(host_header)
    if parsed is None:
        return False
    hostname, host_port = parsed
    return hostname in ALLOWED_HOSTNAMES and host_port == port


def origin_allowed(origin: str | None, port: int) -> bool:
    """Absent Origin (non-browser client) passes; a present Origin must fully
    match http://<whitelisted host>:<serving port> (D8)."""
    if origin is None:
        return True
    try:
        parts = urlsplit(origin)
    except ValueError:
        return False
    if parts.scheme != "http":
        return False
    hostname = (parts.hostname or "").lower()
    if hostname not in ALLOWED_HOSTNAMES:
        return False
    return parts.port == port


# --- D7: one-time ticket and sessions ---------------------------------------


class AccessControl:
    """One-time pairing ticket + in-process session registry.

    The ticket is destroyed on ANY pair attempt (read-and-destroy, D7), so a
    stolen or mistyped ticket is worthless after first use — successful or
    not. Ticket and token values are never logged by this service (uvicorn
    access logging is disabled and no log statement carries them).
    """

    def __init__(
        self,
        *,
        ticket_ttl_seconds: float = TICKET_TTL_SECONDS,
        session_ttl_seconds: float = SESSION_TTL_SECONDS,
    ) -> None:
        self._ticket = secrets.token_urlsafe(32)
        self._ticket_ttl = ticket_ttl_seconds
        self._ticket_issued_at = datetime.now(UTC)
        self._session_ttl = session_ttl_seconds
        self._sessions: dict[str, dict[str, Any]] = {}

    @property
    def ticket(self) -> str:
        """Startup-only access for browser/file delivery. Never logged."""
        return self._ticket

    def _ticket_expired(self, now: datetime) -> bool:
        return now >= self._ticket_issued_at + timedelta(seconds=self._ticket_ttl)

    def pair(self, code: str | None) -> tuple[str, str, int] | None:
        """Exchange the one-time code for (bearer, csrf, expires_in).

        The ticket is destroyed by this call whether the exchange succeeds
        or fails (读后即毁, D7).
        """
        ticket = self._ticket
        self._ticket = ""
        now = datetime.now(UTC)
        if not code or not ticket or code != ticket or self._ticket_expired(now):
            return None
        bearer = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        self._sessions[bearer] = {
            "csrf": csrf,
            "expires_at": now + timedelta(seconds=self._session_ttl),
        }
        return bearer, csrf, int(self._session_ttl)

    def authenticate(self, bearer: str | None) -> dict[str, Any] | None:
        if not bearer:
            return None
        session = self._sessions.get(bearer)
        if session is None:
            return None
        if datetime.now(UTC) >= session["expires_at"]:
            del self._sessions[bearer]
            return None
        return session


# --- D6: instance lock ------------------------------------------------------


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists but owned by someone else
    except OSError:
        return False
    return True


class InstanceLock:
    """Exclusive lock file under SBTD_RUNTIME_HOME (D6).

    A stale lock — dead pid, unreadable, or corrupt content — is treated as
    invalid: removed and acquisition retried once.
    """

    def __init__(self, home: Path, port: int) -> None:
        self._path = home / LOCK_FILE_NAME
        self._port = port
        self._held = False

    def acquire(self) -> None:
        for _attempt in (1, 2):
            try:
                fd = os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                if not self._handle_existing():
                    raise ServeError(self._describe_live_instance()) from None
                continue  # stale lock removed; retry once
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "pid": os.getpid(),
                        "port": self._port,
                        "started_at": datetime.now(UTC).isoformat(),
                    },
                    handle,
                )
                handle.write("\n")
            self._held = True
            return
        raise ServeError(f"cannot acquire instance lock: {self._path}")

    def _handle_existing(self) -> bool:
        """True when the existing lock was stale and has been removed."""
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            pid = int(payload.get("pid", 0))
        except (OSError, ValueError, AttributeError):
            pid = 0  # unreadable or corrupt → stale
        if pid and _pid_alive(pid):
            return False
        try:
            self._path.unlink()
        except OSError:
            return False
        return True

    def _describe_live_instance(self) -> str:
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            pid = payload.get("pid")
            port = payload.get("port")
            return (
                f"已有 sbtd-runtime serve 实例在运行（pid {pid}，端口 {port}）；"
                "如需另起实例请使用 --port 指定其他端口"
            )
        except (OSError, ValueError):
            return f"已有 sbtd-runtime serve 实例在运行（锁文件 {self._path}）"

    def release(self) -> None:
        if not self._held:
            return
        self._held = False
        try:
            self._path.unlink()
        except OSError:
            pass


def check_port_free(port: int) -> None:
    """Second, independent port judgment (D6); failure wording per D5."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind((BIND_HOST, port))
    except OSError:
        raise ServeError(
            f"端口 {port} 已被占用，启动失败；请使用 --port 指定其他端口"
        ) from None
    finally:
        probe.close()


# --- dataset: real library data, never fabricated ---------------------------


def load_dataset(home: Path) -> tuple[dict[str, Any], list[str]]:
    """Assemble the query dataset from the real audit store.

    Events come from EventStore.replay(); the tasks table is derived from
    task.created events (uid / worktree from the event scope). The event
    schema carries no role field, so no role is fabricated — evaluate()
    treats a task without a recorded summary role as a leaf, which matches
    the runtime's executable-leaf observation scope. When the store is
    absent or unreadable the dataset is honestly empty and every response
    carries an envelope warning instead of fabricated numbers.
    """
    try:
        store = EventStore.open(home, read_only=True)
    except StoreError as error:
        return {"tasks": [], "events": []}, [f"AUDIT_STORE_UNAVAILABLE:{error.reason}"]
    try:
        events = store.replay()
    finally:
        store.close()
    tasks: dict[str, dict[str, Any]] = {}
    for event in events:
        if event.get("event_type") != "task.created":
            continue
        scope = event.get("scope") or {}
        uid = scope.get("task_uid")
        if uid and uid not in tasks:
            tasks[uid] = {"task_uid": uid, "worktree_id": scope.get("worktree_id")}
    return {"tasks": list(tasks.values()), "events": events}, []


# --- HTTP layer --------------------------------------------------------------


def _envelope(data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    source = dict(meta or {})
    return {
        "api_version": "1",
        "request_id": f"req_{uuid.uuid4().hex}",
        "data": data,
        "meta": {
            "metrics_version": source.get("metrics_version", "unknown"),
            "projection_version": PROJECTION_VERSION,
            "complete": bool(source.get("complete", True)),
            "coverage_state": source.get("coverage_state", "complete"),
            "warnings": list(source.get("warnings", [])),
            "next_cursor": source.get("next_cursor"),
        },
    }


def _json(
    payload: Any, status: int = 200, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(payload, status_code=status, headers=headers)


_UNSAFE_METHODS = frozenset({"POST", "PUT", "DELETE", "PATCH"})
_AUTH_EXEMPT_PATHS = frozenset({"/api/v1/health", "/api/v1/session/pair"})


class SecurityMiddleware:
    """Pure ASGI middleware: Host/Origin whitelist (D8) on every request,
    Bearer auth on /api/v1/* (except health/pair), CSRF on unsafe methods
    (openapi.yaml x-sbtd-auth). 403 bodies reveal no policy detail."""

    def __init__(self, app: Any, access: AccessControl, port: int) -> None:
        self.app = app
        self.access = access
        self.port = port

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {
            key.decode("latin-1"): value.decode("latin-1")
            for key, value in scope["headers"]
        }
        if not host_allowed(headers.get("host"), self.port) or not origin_allowed(
            headers.get("origin"), self.port
        ):
            await _json({"detail": "forbidden"}, 403)(scope, receive, send)
            return
        path = scope["path"]
        if path.startswith("/api/") and path not in _AUTH_EXEMPT_PATHS:
            bearer = None
            authorization = headers.get("authorization", "")
            if authorization.startswith("Bearer "):
                bearer = authorization[len("Bearer ") :]
            session = self.access.authenticate(bearer)
            if session is None:
                await _json({"detail": "unauthorized"}, 401)(scope, receive, send)
                return
            if (
                scope["method"] in _UNSAFE_METHODS
                and headers.get("x-csrf-token") != session["csrf"]
            ):
                await _json({"detail": "forbidden"}, 403)(scope, receive, send)
                return
            scope["sbtd.session"] = session
        await self.app(scope, receive, send)


def _export_request(body: Any, manifest: dict) -> tuple[str, str, dict]:
    """Validate the frozen CreateExportRequest, including manifest membership."""
    if not isinstance(body, dict) or not {"snapshot_id", "format"} <= body.keys():
        raise ValueError("snapshot_id and format are required")
    if body.keys() - {"snapshot_id", "format", "presentation_state"}:
        raise ValueError("unknown export request property")
    snapshot_id = body["snapshot_id"]
    if not isinstance(snapshot_id, str) or not re.fullmatch(
        r"snap_[0-9a-f]{32}", snapshot_id
    ):
        raise ValueError("invalid snapshot_id")
    format_name = body["format"]
    if format_name not in ("html", "csv"):
        raise ValueError("format must be html or csv")
    presentation = body.get("presentation_state", default_presentation(manifest))
    required = {
        "theme",
        "report_width_px",
        "expanded_detail_ids",
        "table_sort",
        "preview_row_sets",
        "panel_order",
        "legend_state",
    }
    if not isinstance(presentation, dict) or set(presentation) != required:
        raise ValueError("presentation_state must contain exactly seven fields")
    if presentation["theme"] not in ("dark", "light"):
        raise ValueError("invalid theme")

    def nonnegative(value: Any) -> bool:
        return (
            type(value) is int
            and value >= 0
            or type(value) is float
            and math.isfinite(value)
            and value >= 0
        )

    if not nonnegative(presentation["report_width_px"]):
        raise ValueError("report_width_px must be a nonnegative number")
    for name in ("expanded_detail_ids", "panel_order"):
        value = presentation[name]
        if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
            raise ValueError(f"{name} must be a string array")
    panel_ids = {panel["panel_id"] for panel in manifest["panels"]}
    order = presentation["panel_order"]
    if len(order) != len(panel_ids) or set(order) != panel_ids:
        raise ValueError("panel_order must be a complete unique manifest permutation")
    for name, check in (
        ("table_sort", lambda value: isinstance(value, str)),
        ("preview_row_sets", nonnegative),
        ("legend_state", lambda value: type(value) is bool),
    ):
        values = presentation[name]
        if not isinstance(values, dict) or not all(check(v) for v in values.values()):
            raise ValueError(f"invalid {name}")
    return snapshot_id, format_name, presentation


def create_app(home: Path, access: AccessControl, port: int) -> Any:
    store = SnapshotStore(home)
    manifest = load_panel_manifest()
    exports = ExportStore(home, store, ExportRenderer(store))

    @asynccontextmanager
    async def lifespan(_app: Starlette):
        try:
            yield
        finally:
            await run_in_threadpool(exports.close)

    async def health(_request: Request) -> JSONResponse:
        return _json({"status": "ok"})

    async def pair(request: Request) -> JSONResponse:
        result = access.pair(request.headers.get("x-pairing-code"))
        if result is None:
            return _json({"detail": "unauthorized"}, 401)
        bearer, csrf, expires_in = result
        return _json(
            {"token_type": "bearer", "access_token": bearer, "expires_in": expires_in},
            headers={"X-CSRF-Token": csrf},
        )

    async def metric_catalog(_request: Request) -> JSONResponse:
        catalog = serve_catalog()
        return _json(
            _envelope(catalog, {"metrics_version": catalog.get("metrics_version")})
        )

    async def statistics_query(request: Request) -> JSONResponse:
        try:
            raw_scope = await request.json()
        except json.JSONDecodeError:
            return _json({"detail": "invalid JSON body"}, 400)
        if not isinstance(raw_scope, dict):
            return _json({"detail": "query scope must be a JSON object"}, 400)
        # Reload per query: the dashboard must reflect newly ingested events.
        data, warnings = load_dataset(home)
        try:
            result = query(data, raw_scope, store=store)
        except QueryScopeError as error:
            return _json({"detail": str(error)}, 400)
        meta = dict(result.get("meta") or {})
        meta["warnings"] = [*meta.get("warnings", []), *warnings]
        if warnings:
            meta["complete"] = False
            meta["coverage_state"] = "partial"
        return _json(_envelope(result, meta))

    async def get_snapshot(request: Request) -> JSONResponse:
        snapshot_id = request.path_params["snapshot_id"]
        try:
            snapshot = store.get(snapshot_id)
        except SnapshotNotFound:
            return _json({"detail": "not found"}, 404)
        except SnapshotGone:
            return _json({"detail": "gone"}, 410)
        view = snapshot.public_view()
        return _json(_envelope(view, {"metrics_version": view["metrics_version"]}))

    async def get_snapshot_dataset(request: Request) -> JSONResponse:
        snapshot_id = request.path_params["snapshot_id"]
        cursor = request.query_params.get("cursor")
        try:
            page = store.dataset_page(snapshot_id, cursor=cursor)
        except SnapshotNotFound:
            return _json({"detail": "not found"}, 404)
        except SnapshotGone:
            return _json({"detail": "gone"}, 410)
        except CursorError as error:
            return _json({"detail": str(error)}, 400)
        return _json(
            _envelope(page, {"next_cursor": page["next_cursor"], "complete": True})
        )

    async def create_export(request: Request) -> JSONResponse:
        try:
            if (
                request.headers.get("content-type", "").split(";")[0].strip()
                != "application/json"
            ):
                raise ValueError("application/json body required")
            key = request.headers.get("idempotency-key")
            if key is None:
                raise ValueError("Idempotency-Key is required")
            snapshot_id, format_name, presentation = _export_request(
                await request.json(), manifest
            )
            export_id = await run_in_threadpool(
                exports.create,
                snapshot_id,
                format_name,
                presentation,
                idempotency_key=key,
            )
        except (ValueError, UnicodeError):
            return _json({"detail": "invalid export request"}, 400)
        except SnapshotNotFound:
            return _json({"detail": "not found"}, 404)
        except SnapshotGone:
            return _json({"detail": "gone"}, 410)
        return _json(_envelope({"export_id": export_id}), 202)

    async def export_resource(request: Request) -> Response:
        export_id = request.path_params["export_id"]
        if request.query_params:
            return _json({"detail": "export paths do not accept query parameters"}, 400)
        try:
            if request.method == "DELETE":
                if request.headers.get("idempotency-key") is None:
                    return _json({"detail": "Idempotency-Key is required"}, 400)
                await run_in_threadpool(exports.delete, export_id)
                return Response(status_code=204)
            if request.url.path.endswith("/file"):
                blob, info = await run_in_threadpool(exports.download, export_id)
                return Response(
                    blob,
                    media_type=info["mime_type"],
                    headers={
                        "Content-Disposition": f'attachment; filename="sbtd-report_{export_id}.{info["format"]}"',
                        "Cache-Control": "no-store",
                        "X-Content-Type-Options": "nosniff",
                    },
                )
            info = await run_in_threadpool(exports.get, export_id)
            return _json(_envelope(info))
        except ExportNotFound:
            return _json({"detail": "not found"}, 404)
        except ExportGone:
            return _json({"detail": "gone"}, 410)
        except ExportNotReady:
            return _json({"detail": "export is not ready"}, 409)

    routes = [
        Route("/api/v1/health", health, methods=["GET"]),
        Route("/api/v1/session/pair", pair, methods=["POST"]),
        Route("/api/v1/metrics/catalog", metric_catalog, methods=["GET"]),
        Route("/api/v1/statistics/query", statistics_query, methods=["POST"]),
        Route("/api/v1/exports", create_export, methods=["POST"]),
        Route(
            "/api/v1/exports/{export_id}", export_resource, methods=["GET", "DELETE"]
        ),
        Route("/api/v1/exports/{export_id}/file", export_resource, methods=["GET"]),
        Route(
            "/api/v1/report-snapshots/{snapshot_id}",
            get_snapshot,
            methods=["GET"],
        ),
        Route(
            "/api/v1/report-snapshots/{snapshot_id}/dataset",
            get_snapshot_dataset,
            methods=["GET"],
        ),
        Mount("/", app=StaticFiles(directory=STATIC_DIR, html=True)),
    ]
    app = Starlette(routes=routes, lifespan=lifespan)
    return SecurityMiddleware(app, access, port)


# --- CLI (D5/D6 lifecycle) ---------------------------------------------------


def _deliver_ticket(
    access: AccessControl, home: Path, port: int, open_browser: bool
) -> None:
    """D7 delivery: browser fragment only, or a 0600 file fallback. The
    ticket value never reaches the terminal or any log."""
    url = f"http://{BIND_HOST}:{port}/#ticket={access.ticket}"
    opened = False
    if open_browser:
        try:
            opened = bool(webbrowser.open(url))
        except webbrowser.Error:
            opened = False
    if opened:
        print("浏览器已打开配对链接（ticket 一次性、短时有效，不打印到终端）")
        return
    ticket_path = home / TICKET_FILE_NAME
    fd = os.open(ticket_path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(access.ticket + "\n")
    os.chmod(ticket_path, 0o600)
    print(
        f"未自动打开浏览器；配对 ticket 已写入 {ticket_path}（0600），"
        "请取出后经 X-Pairing-Code 头完成配对。ticket 不打印到终端。"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sbtd-runtime serve",
        description="SBTD Runtime 本地 Dashboard 服务（loopback only，D5–D8）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"监听端口（默认 {DEFAULT_PORT}）；占用时启动失败并提示本选项",
    )
    parser.add_argument(
        "--open",
        dest="open_browser",
        action="store_true",
        default=True,
        help="启动后自动打开浏览器完成配对（默认）",
    )
    parser.add_argument(
        "--no-open",
        dest="open_browser",
        action="store_false",
        help="不打开浏览器；ticket 写入 SBTD_RUNTIME_HOME 下 0600 文件",
    )
    parser.add_argument(
        "--home",
        type=Path,
        default=None,
        help="SBTD_RUNTIME_HOME（默认取环境变量或 ~/.sbtd-runtime）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not (1 <= args.port <= 65535):
        print("--port 须在 1..65535 之间", file=sys.stderr)
        return 2
    home = args.home or default_runtime_home()
    try:
        validate_snapshot_home(home)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(home, 0o700)

    lock = InstanceLock(home, args.port)
    try:
        lock.acquire()
    except ServeError as error:
        print(str(error), file=sys.stderr)
        return 2
    try:
        check_port_free(args.port)
    except ServeError as error:
        lock.release()
        print(str(error), file=sys.stderr)
        return 2

    try:
        access = AccessControl()
        app = create_app(home, access, args.port)
    except (OSError, ValueError) as error:
        lock.release()
        print(str(error), file=sys.stderr)
        return 2

    import uvicorn

    config = uvicorn.Config(
        app,
        host=BIND_HOST,
        port=args.port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)

    _deliver_ticket(access, home, args.port, args.open_browser)
    print(f"SBTD Runtime Dashboard: http://{BIND_HOST}:{args.port}/ （Ctrl-C 退出）")
    try:
        server.run()
    except KeyboardInterrupt:
        pass
    finally:
        lock.release()
    return 0


if __name__ == "__main__":
    sys.exit(main())
