"""Export jobs for one runtime home.

Ready bytes live at ``exports/<export_id>.bin``. The sibling
``<export_id>.json`` manifest is renamed into place only after that artifact
is fsynced. Download and restart serve the artifact only when its SHA-256
matches the manifest. Sessions are not stored: visibility is this home.

Pin the snapshot before the job is queued. Release it after success, failure,
cancellation, or close. Cleanup of expired ready exports touches only
``exports/`` and only files this store can verify.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import re
import stat
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from contract_eval import parse_instant

EXPORT_TTL_SECONDS = 86400
EXPORT_FORMAT_VERSION = 1
_EXPORT_ID = re.compile(r"exp_[0-9a-f]{32}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_FORMATS = {
    "html": "text/html; charset=utf-8",
    "csv": "text/csv; charset=utf-8",
    "jpeg": "image/jpeg",
    "pdf": "application/pdf",
}
_METADATA_KEYS = (
    "mime_type",
    "redaction_policy_version",
    "export_schema_version",
    "panel_manifest_version",
    "panel_ids",
    "dataset_manifest",
    "range_from",
    "range_to",
    "timezone",
    "warnings",
    "renderer_version",
)
_RECORD_KEYS = {"idempotency_key", "payload", "manifest"}
_ENVELOPE_KEYS = {"format_version", "checksum", "record"}


class ExportNotFound(KeyError):
    """No visible export with this id exists in this runtime home."""


class ExportGone(RuntimeError):
    """The ready export expired. The id is not reused."""


class ExportNotReady(RuntimeError):
    """The export has no verified ready artifact."""


class _Job:
    def __init__(
        self,
        export_id: str,
        snapshot: Any,
        snapshot_id: str,
        format_name: str,
        presentation: dict[str, Any],
        idempotency_key: str | None,
        payload: str | None,
        created_at: str,
    ) -> None:
        self.export_id = export_id
        self.snapshot = snapshot
        self.snapshot_id = snapshot_id
        self.format = format_name
        self.presentation = presentation
        self.idempotency_key = idempotency_key
        self.payload = payload
        self.created_at = created_at
        self.status = "queued"
        self.ready_at: str | None = None
        self.expires_at: str | None = None
        self.expires_instant: datetime | None = None
        self.sha256: str | None = None
        self.byte_count: int | None = None
        self.metadata: dict[str, Any] = {}
        self.error: str | None = None
        self.public: dict[str, Any] | None = None
        self.published = False
        self.pin_held = False
        self.cancelled = False
        self.cancel_event = threading.Event()
        self.done = threading.Event()
        self.future: Any = None
        self.renderer: Any = None


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(instant: datetime) -> str:
    return instant.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _aware(now: datetime) -> datetime:
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("now must be an aware datetime")
    return now


def _canonical(payload: Any) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _request_identity(
    snapshot_id: str,
    format_name: str,
    presentation: dict[str, Any],
    idempotency_key: str | None,
) -> tuple[str | None, str]:
    try:
        payload = _canonical(
            {
                "snapshot_id": snapshot_id,
                "format": format_name,
                "presentation_state": presentation,
            }
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("presentation_state must be JSON") from exc
    # Only digests are retained for replay; request text is not export metadata.
    payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if idempotency_key is not None:
        idempotency_key = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
    return idempotency_key, payload


def _checksum(record: dict[str, Any]) -> str:
    digest = hashlib.sha256(_canonical(record).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate export field")
        result[key] = value
    return result


def _accepted_metadata(format_name: str, meta: Any) -> dict[str, Any]:
    if not isinstance(meta, dict):
        raise TypeError("manifest metadata must be a dict")
    selected = {key: meta[key] for key in _METADATA_KEYS if key in meta}
    mime = selected.get("mime_type")
    if not isinstance(mime, str) or mime == "":
        selected["mime_type"] = _FORMATS.get(format_name, "application/octet-stream")
    for key in ("panel_ids", "dataset_manifest", "warnings"):
        value = selected.get(key, [])
        if not isinstance(value, list):
            raise TypeError(f"{key} must be a list")
        selected[key] = value
    # Reject paths and other non-JSON values before they reach the manifest.
    json.dumps(selected, allow_nan=False)
    return copy.deepcopy(selected)


def _public_view(
    job: _Job,
    *,
    status: str,
    ready_at: str | None,
    expires_at: str | None,
    sha256: str | None,
    byte_count: int | None,
    metadata: dict[str, Any],
    error: str | None,
) -> dict[str, Any]:
    meta = metadata or {}
    return {
        "export_id": job.export_id,
        "status": status,
        "format": job.format,
        "snapshot_id": job.snapshot_id,
        "created_at": job.created_at,
        "ready_at": ready_at,
        "expires_at": expires_at,
        "mime_type": meta.get("mime_type"),
        "byte_count": byte_count,
        "byte_size": byte_count,
        "sha256": sha256,
        "redaction_policy_version": meta.get("redaction_policy_version"),
        "export_schema_version": meta.get("export_schema_version"),
        "panel_manifest_version": meta.get("panel_manifest_version"),
        "panel_ids": list(meta.get("panel_ids") or []),
        "dataset_manifest": copy.deepcopy(meta.get("dataset_manifest") or []),
        "range_from": meta.get("range_from"),
        "range_to": meta.get("range_to"),
        "timezone": meta.get("timezone"),
        "warnings": list(meta.get("warnings") or []),
        "renderer_version": meta.get("renderer_version"),
        "error": error,
    }


def validate_export_home(home: Path) -> None:
    """Refuse symlink, junction, or foreign ownership of the exports directory."""
    home = Path(home).absolute()
    directory = home / "exports"
    for path in (directory, *directory.parents):
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        if os.name == "nt" and not hasattr(info, "st_file_attributes"):
            raise ValueError("export reparse-point check is unavailable")
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            raise ValueError("export directory link is refused")
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError("export home must be a directory")
        if (
            path in (home, directory)
            and hasattr(os, "getuid")
            and info.st_uid != os.getuid()
        ):
            raise ValueError("export directory has unknown ownership")


class ExportStore:
    """One runtime writer's export jobs. Constructing the store starts no worker."""

    def __init__(self, home: Path, snapshots: Any, renderer: Any) -> None:
        home = Path(home).absolute()
        self._home = home
        self._directory = home / "exports"
        self._snapshots = snapshots
        self._renderer = renderer
        validate_export_home(home)
        home.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._directory.mkdir(mode=0o700, exist_ok=True)
        validate_export_home(home)
        os.chmod(home, 0o700)
        os.chmod(self._directory, 0o700)
        self._directory_identity = self._identity()
        self._lock = threading.RLock()
        self._admissions = threading.Condition(self._lock)
        self._preparing = 0
        self._closing = threading.Event()
        self._jobs: dict[str, _Job] = {}
        self._gone: set[str] = set()
        self._gone_payload: dict[str, str | None] = {}
        self._idempotency: dict[str, str] = {}
        self._executor: Any = None
        self._closed = False
        self._restore()
        self.sweep()

    def lookup_replay(
        self,
        snapshot_id: str,
        format: str,
        presentation_state: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> tuple[str, list[str]] | None:
        """Read a validated request's original acceptance without admission work."""
        key, payload = _request_identity(
            snapshot_id, format, presentation_state, idempotency_key
        )
        with self._lock:
            if self._closed:
                raise ValueError("export store is closed")
            existing = self._existing_idempotent(key, payload)
            if existing is None:
                return None
            warnings = self.acceptance_warnings(existing) if format == "jpeg" else []
            return existing, warnings

    def create(
        self,
        snapshot_id: str,
        format: str,
        presentation_state: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        prepare: Any = None,
    ) -> str:
        """Pin, optionally preflight before allocating a job, then queue one render."""
        if format not in _FORMATS:
            raise ValueError("export format must be html, csv, jpeg or pdf")
        if not isinstance(presentation_state, dict):
            raise TypeError("presentation_state must be an object")
        if idempotency_key is not None and not isinstance(idempotency_key, str):
            raise ValueError("idempotency key must be a string")
        presentation = copy.deepcopy(presentation_state)
        idempotency_key, payload = _request_identity(
            snapshot_id, format, presentation, idempotency_key
        )
        with self._lock:
            if self._closed:
                raise ValueError("export store is closed")
            existing = self._existing_idempotent(idempotency_key, payload)
            if existing is not None:
                return existing
            if prepare is not None:
                self._preparing += 1
        snapshot = None
        pinned = False
        try:
            snapshot = self._snapshots.pin(snapshot_id)
            pinned = True
            renderer = self._renderer
            warnings: list[str] = []
            if prepare is not None:
                renderer, warnings = prepare(
                    snapshot, format, presentation, cancelled=self._closing.is_set
                )
            with self._lock:
                if self._closed:
                    raise ValueError("export store is closed")
                existing = self._existing_idempotent(idempotency_key, payload)
                if existing is not None:
                    return existing
                export_id = f"exp_{uuid.uuid4().hex}"
                job = _Job(
                    export_id,
                    snapshot,
                    snapshot.snapshot_id,
                    format,
                    presentation,
                    idempotency_key,
                    payload if idempotency_key is not None else None,
                    _iso(_now()),
                )
                job.renderer = renderer
                job.metadata = {"warnings": list(warnings)}
                job.pin_held = True
                pinned = False
                self._jobs[export_id] = job
                if idempotency_key is not None:
                    self._idempotency[idempotency_key] = export_id
                try:
                    self._ensure_executor()
                    job.future = self._executor.submit(self._run, export_id)
                except Exception:
                    self._jobs.pop(export_id, None)
                    if idempotency_key is not None:
                        self._idempotency.pop(idempotency_key, None)
                    job.pin_held = False
                    pinned = True
                    raise
                return export_id
        finally:
            try:
                if pinned:
                    self._snapshots.release(snapshot.snapshot_id)
            finally:
                if prepare is not None:
                    with self._admissions:
                        self._preparing -= 1
                        self._admissions.notify_all()

    def acceptance_warnings(self, export_id: str) -> list[str]:
        """Read accepted warnings without changing idempotent replay/expiry behavior."""
        with self._lock:
            job = self._jobs.get(export_id)
            if job is None:
                return []
            metadata = job.public if job.public is not None else job.metadata
            return list(metadata.get("warnings", []))

    def get(self, export_id: str) -> dict[str, Any]:
        """Return a JSON-safe status. Ready views are re-verified from disk."""
        with self._lock:
            job = self._locked_job(export_id)
            if job.status != "ready":
                return _public_view(
                    job,
                    status=job.status,
                    ready_at=job.ready_at,
                    expires_at=job.expires_at,
                    sha256=job.sha256,
                    byte_count=job.byte_count,
                    metadata=job.metadata,
                    error=job.error,
                )
        loaded, _artifact = self._read_ready(export_id)
        if _now() >= loaded.expires_instant:
            raise ExportGone(export_id)
        return copy.deepcopy(loaded.public)

    def download(self, export_id: str) -> tuple[bytes, dict[str, Any]]:
        """Return the verified artifact. Does not extend retention."""
        with self._lock:
            job = self._locked_job(export_id)
            if job.status != "ready":
                raise ExportNotReady(export_id)
        loaded, artifact = self._read_ready(export_id)
        if _now() >= loaded.expires_instant:
            raise ExportGone(export_id)
        return artifact, copy.deepcopy(loaded.public)

    def delete(self, export_id: str) -> None:
        """Cancel this job and remove only the files it owns."""
        self._check_id(export_id)
        with self._lock:
            self._check_directory()
            if export_id in self._gone:
                raise ExportGone(export_id)
            job = self._jobs.get(export_id)
            if job is None:
                raise ExportNotFound(export_id)
            job.cancel_event.set()
            job.cancelled = True
            if job.future is not None and job.future.cancel():
                job.status = "cancelled"
                self._release_pin(job)
                job.done.set()
        job.done.wait()
        with self._lock:
            self._unlink_leaf(self._artifact_path(export_id))
            self._unlink_leaf(self._manifest_path(export_id))
            job.status = "cancelled"
            job.ready_at = None
            job.expires_at = None
            job.expires_instant = None
            job.sha256 = None
            job.byte_count = None
            job.error = None
            job.published = False
            job.public = None

    def close(self) -> None:
        """Cancel preparation/jobs, wait for cleanup, and release leftover pins."""
        with self._lock:
            if self._closed:
                self._admissions.wait_for(lambda: self._preparing == 0)
                return
            self._closed = True
            self._closing.set()
            for job in self._jobs.values():
                job.cancel_event.set()
                job.cancelled = True
            executor = self._executor
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)
        with self._lock:
            self._admissions.wait_for(lambda: self._preparing == 0)
            for job in self._jobs.values():
                if job.status in ("queued", "generating"):
                    job.status = "cancelled"
                self._release_pin(job)
                job.done.set()

    def sweep(self, now: datetime | None = None) -> list[str]:
        """Remove verified ready exports at or after their original expiry."""
        current = _now() if now is None else _aware(now)
        with self._lock:
            self._check_directory()
            candidates = [
                export_id
                for export_id, job in self._jobs.items()
                if job.status == "ready"
                and job.expires_instant is not None
                and current >= job.expires_instant
            ]
        removed = []
        for export_id in candidates:
            try:
                loaded, _artifact = self._read_ready(export_id)
            except ExportNotFound:
                continue
            if loaded.expires_instant is None or current < loaded.expires_instant:
                continue
            with self._lock:
                job = self._jobs.get(export_id)
                if job is None or job.status != "ready":
                    continue
                if not self._unlink_exclusive_pair(export_id):
                    continue
                self._jobs.pop(export_id, None)
                self._gone.add(export_id)
                self._gone_payload[export_id] = job.payload
                removed.append(export_id)
        return removed

    def _existing_idempotent(self, key: str | None, payload: str) -> str | None:
        if key is None:
            return None
        export_id = self._idempotency.get(key)
        if export_id is None:
            return None
        job = self._jobs.get(export_id)
        stored = job.payload if job is not None else self._gone_payload.get(export_id)
        if stored != payload:
            raise ValueError("idempotency key reused with a different payload")
        return export_id

    def _ensure_executor(self) -> None:
        if self._executor is None:
            # ponytail: one worker; raise max_workers if export concurrency matters
            self._executor = ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="sbtd-export"
            )

    def _run(self, export_id: str) -> None:
        job = None
        try:
            with self._lock:
                job = self._jobs.get(export_id)
                if job is None:
                    return
                if job.cancelled or self._closed:
                    job.status = "cancelled"
                    return
                job.status = "generating"
                snapshot = job.snapshot
                format_name = job.format
                presentation = job.presentation
                cancelled = job.cancel_event.is_set
            try:
                blob, meta = self._invoke(
                    snapshot, format_name, presentation, cancelled, job.renderer
                )
            except Exception as error:  # noqa: BLE001 — worker boundary releases the pin.
                from browser_renderer import (
                    RENDERER_FAILED,
                    RENDERER_TIMEOUT,
                    RendererError,
                )

                # Re-allowlist even a mutated exception; never log text or traceback.
                code = (
                    RendererError(error.code).code
                    if isinstance(error, RendererError)
                    else RENDERER_FAILED
                )
                if not cancelled() and not self._closed:
                    logging.getLogger(__name__).warning(
                        "export renderer failed: %s", code
                    )
                self._fail(export_id, timed_out=code == RENDERER_TIMEOUT)
                return
            if cancelled() or self._closed:
                self._mark_cancelled(export_id)
                return
            try:
                self._publish(job, blob, meta)
            except Exception:  # noqa: BLE001 — publication failure must release the pin.
                logging.getLogger(__name__).warning("export publication failed")
                self._fail(export_id)
        finally:
            with self._lock:
                if job is not None:
                    self._release_pin(job)
                    if job.status in ("queued", "generating"):
                        job.status = (
                            "cancelled" if job.cancelled or self._closed else "failed"
                        )
                        if job.status == "failed" and job.error is None:
                            job.error = "EXPORT_RENDER_FAILED"
                    job.done.set()

    def _invoke(
        self,
        snapshot: Any,
        format_name: str,
        presentation: dict[str, Any],
        cancelled: Any,
        renderer: Any,
    ) -> tuple[bytes, Any]:
        result = renderer(snapshot, format_name, presentation, cancelled)
        if not isinstance(result, tuple) or len(result) != 2:
            raise TypeError("renderer must return (bytes, metadata)")
        blob, meta = result
        if isinstance(blob, bytearray):
            blob = bytes(blob)
        if type(blob) is not bytes:
            raise TypeError("renderer must return bytes")
        return blob, meta

    def _fail(self, export_id: str, *, timed_out: bool = False) -> None:
        with self._lock:
            job = self._jobs.get(export_id)
            if job is None or job.published:
                return
            self._unlink_leaf(self._artifact_path(export_id))
            if job.cancelled or self._closed:
                job.status = "cancelled"
                job.error = None
            else:
                job.status = "failed"
                job.error = (
                    "EXPORT_RENDER_TIMEOUT" if timed_out else "EXPORT_RENDER_FAILED"
                )

    def _mark_cancelled(self, export_id: str) -> None:
        with self._lock:
            job = self._jobs.get(export_id)
            if job is None or job.published:
                return
            job.status = "cancelled"
            job.error = None
            self._unlink_leaf(self._artifact_path(export_id))

    def _publish(self, job: _Job, blob: bytes, meta: Any) -> None:
        if job.cancel_event.is_set() or self._closed:
            self._mark_cancelled(job.export_id)
            return
        metadata = _accepted_metadata(job.format, meta)
        digest = hashlib.sha256(blob).hexdigest()
        ready_at = _now()
        expires = ready_at + timedelta(seconds=EXPORT_TTL_SECONDS)
        public = _public_view(
            job,
            status="ready",
            ready_at=_iso(ready_at),
            expires_at=_iso(expires),
            sha256=digest,
            byte_count=len(blob),
            metadata=metadata,
            error=None,
        )
        record = {
            "idempotency_key": job.idempotency_key,
            "payload": job.payload,
            "manifest": public,
        }
        envelope = {
            "format_version": EXPORT_FORMAT_VERSION,
            "checksum": _checksum(record),
            "record": record,
        }
        body = _canonical(envelope).encode("utf-8")
        artifact_path = self._artifact_path(job.export_id)
        manifest_path = self._manifest_path(job.export_id)
        artifact_tmp = self._write_temp(blob)
        try:
            with self._lock:
                self._check_directory()
                if job.cancelled or self._closed:
                    job.status = "cancelled"
                    return
                os.replace(artifact_tmp, artifact_path)
                artifact_tmp = None
                written, _identity = self._read_regular(artifact_path)
                if hashlib.sha256(written).hexdigest() != digest or len(written) != len(
                    blob
                ):
                    self._unlink_leaf(artifact_path)
                    raise ValueError("artifact changed before publish")
            self._fsync_dir()
            manifest_tmp = self._write_temp(body)
            try:
                with self._lock:
                    self._check_directory()
                    if job.cancelled or self._closed:
                        job.status = "cancelled"
                        self._unlink_leaf(artifact_path)
                        return
                    try:
                        os.replace(manifest_tmp, manifest_path)
                        manifest_tmp = None
                        self._fsync_dir()
                    except Exception:
                        self._unlink_leaf(manifest_path)
                        self._unlink_leaf(artifact_path)
                        raise
                    job.status = "ready"
                    job.ready_at = public["ready_at"]
                    job.expires_at = public["expires_at"]
                    job.expires_instant = expires
                    job.sha256 = digest
                    job.byte_count = len(blob)
                    job.metadata = metadata
                    job.error = None
                    job.public = public
                    job.published = True
            finally:
                if manifest_tmp is not None:
                    self._unlink_leaf(manifest_tmp)
        finally:
            if artifact_tmp is not None:
                self._unlink_leaf(artifact_tmp)

    def _locked_job(self, export_id: str) -> _Job:
        self._check_id(export_id)
        self._check_directory()
        if export_id in self._gone:
            raise ExportGone(export_id)
        job = self._jobs.get(export_id)
        if job is None:
            raise ExportNotFound(export_id)
        return job

    def _restore(self) -> None:
        self._check_directory()
        for path in self._directory.iterdir():
            if path.suffix != ".json":
                continue
            export_id = path.name[:-5]
            if not _EXPORT_ID.fullmatch(export_id):
                continue
            try:
                job, _artifact = self._read_ready(export_id)
            except (
                OSError,
                ValueError,
                TypeError,
                KeyError,
                UnicodeError,
                RecursionError,
            ):
                continue
            self._jobs[export_id] = job
            if isinstance(job.idempotency_key, str):
                self._idempotency[job.idempotency_key] = export_id

    def _read_ready(self, export_id: str) -> tuple[_Job, bytes]:
        try:
            manifest_bytes, _manifest_id = self._read_regular(
                self._manifest_path(export_id)
            )
            envelope = json.loads(
                manifest_bytes.decode("utf-8"), object_pairs_hook=_unique_object
            )
            if set(envelope) != _ENVELOPE_KEYS:
                raise ValueError("invalid export header")
            version = envelope["format_version"]
            if type(version) is not int or version != EXPORT_FORMAT_VERSION:
                raise ValueError("unsupported export format")
            record = envelope["record"]
            if not isinstance(record, dict) or set(record) != _RECORD_KEYS:
                raise ValueError("invalid export record")
            if envelope["checksum"] != _checksum(record):
                raise ValueError("export checksum mismatch")
            public = record["manifest"]
            if not isinstance(public, dict) or public.get("export_id") != export_id:
                raise ValueError("export id mismatch")
            if public.get("status") != "ready":
                raise ValueError("unpublished export")
            digest = public.get("sha256")
            count = public.get("byte_count")
            if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
                raise ValueError("invalid digest")
            if type(count) is not int or count < 0 or public.get("byte_size") != count:
                raise ValueError("invalid byte count")
            artifact, _artifact_id = self._read_regular(self._artifact_path(export_id))
            if len(artifact) != count or hashlib.sha256(artifact).hexdigest() != digest:
                raise ValueError("artifact digest mismatch")
            ready_at = parse_instant(public["ready_at"])
            expires_at = parse_instant(public["expires_at"])
            if expires_at < ready_at:
                raise ValueError("invalid export lifetime")
            key = record["idempotency_key"]
            payload = record["payload"]
            if key is not None and not isinstance(key, str):
                raise ValueError("invalid idempotency key")
            if payload is not None and not isinstance(payload, str):
                raise ValueError("invalid payload")
            if (key is None) != (payload is None):
                raise ValueError("invalid idempotency record")
        except ExportNotFound:
            raise
        except (
            OSError,
            ValueError,
            TypeError,
            KeyError,
            UnicodeError,
            RecursionError,
        ):
            raise ExportNotFound(export_id) from None
        job = _Job(
            export_id,
            None,
            public["snapshot_id"],
            public["format"],
            {},
            key,
            payload,
            public["created_at"],
        )
        job.status = "ready"
        job.ready_at = public["ready_at"]
        job.expires_at = public["expires_at"]
        job.expires_instant = expires_at
        job.sha256 = digest
        job.byte_count = count
        job.public = public
        job.published = True
        job.done.set()
        return job, artifact

    def _identity(self) -> tuple[int, int]:
        info = self._directory.stat()
        return info.st_dev, info.st_ino

    def _check_directory(self) -> None:
        validate_export_home(self._home)
        if self._identity() != self._directory_identity:
            raise ValueError("export directory was replaced")

    def _check_id(self, export_id: str) -> None:
        if not isinstance(export_id, str) or not _EXPORT_ID.fullmatch(export_id):
            raise ExportNotFound(export_id)

    def _artifact_path(self, export_id: str) -> Path:
        self._check_id(export_id)
        return self._directory / f"{export_id}.bin"

    def _manifest_path(self, export_id: str) -> Path:
        self._check_id(export_id)
        return self._directory / f"{export_id}.json"

    def _read_regular(self, path: Path) -> tuple[bytes, tuple[int, int]]:
        self._check_directory()
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise ValueError("export must be a regular file")
        if info.st_nlink != 1:
            raise ValueError("export must be a regular unlinked file")
        if hasattr(os, "getuid") and info.st_uid != os.getuid():
            raise ValueError("export has unknown ownership")
        flags = (
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        )
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                raise ValueError("opened export must be a regular unlinked file")
            if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                raise ValueError("export file was replaced")
            return handle.read(), (info.st_dev, info.st_ino)

    def _write_temp(self, blob: bytes) -> Path:
        self._check_directory()
        fd, name = tempfile.mkstemp(
            prefix=".export-", suffix=".tmp", dir=self._directory
        )
        temporary = Path(name)
        try:
            with os.fdopen(fd, "wb") as handle:
                os.chmod(temporary, 0o600)
                handle.write(blob)
                handle.flush()
                os.fsync(handle.fileno())
            return temporary
        except Exception:
            self._unlink_leaf(temporary)
            raise

    def _fsync_dir(self) -> None:
        if os.name != "posix":
            return
        directory_fd = os.open(self._directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    def _unlink_leaf(self, path: Path) -> None:
        self._check_directory()
        try:
            info = path.lstat()
        except FileNotFoundError:
            return
        if stat.S_ISDIR(info.st_mode):
            return
        path.unlink()

    def _exclusive(self, path: Path) -> os.stat_result | None:
        try:
            info = path.lstat()
        except FileNotFoundError:
            return None
        if (
            stat.S_ISLNK(info.st_mode)
            or not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
        ):
            return None
        if hasattr(os, "getuid") and info.st_uid != os.getuid():
            return None
        return info

    def _unlink_exclusive_pair(self, export_id: str) -> bool:
        self._check_directory()
        artifact = self._artifact_path(export_id)
        manifest = self._manifest_path(export_id)
        artifact_info = self._exclusive(artifact)
        manifest_info = self._exclusive(manifest)
        if artifact_info is None or manifest_info is None:
            return False
        current_artifact = self._exclusive(artifact)
        current_manifest = self._exclusive(manifest)
        if (
            current_artifact is None
            or current_manifest is None
            or (current_artifact.st_dev, current_artifact.st_ino)
            != (artifact_info.st_dev, artifact_info.st_ino)
            or (current_manifest.st_dev, current_manifest.st_ino)
            != (manifest_info.st_dev, manifest_info.st_ino)
        ):
            return False
        self._check_directory()
        artifact.unlink()
        if self._exclusive(manifest) is None:
            return False
        self._check_directory()
        manifest.unlink()
        return True

    def _release_pin(self, job: _Job) -> None:
        if not job.pin_held:
            return
        job.pin_held = False
        self._snapshots.release(job.snapshot_id)
        job.snapshot = None
        job.presentation = {}
        job.renderer = None
