"""Local observation store: raw events, dedup, spool, checkpoint, quality.

This is the R1.2a storage seam. It does not wrap task writes, import history,
or serve HTTP. Callers must confirm, and the observation switch must already
be on. A refused open creates no audit.db and no spool.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self
from urllib.parse import quote

import jsonschema
from contract_eval import canonical_content, dedup_key, validate_events

SCHEMA_VERSION = "1"
_HEADER = "sbtd_spool"
_SCHEMA_ERRORS = (
    jsonschema.ValidationError,
    jsonschema.SchemaError,
    TypeError,
    ValueError,
    KeyError,
    json.JSONDecodeError,
)


class StoreError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Outcome:
    status: str
    event_id: str | None = None
    code: str | None = None


@dataclass(frozen=True)
class AppendResult:
    outcomes: tuple[Outcome, ...]


@dataclass(frozen=True)
class Quality:
    accepted: int
    duplicate: int
    conflict: int
    rejected: int
    truncated: int
    pending: int
    unlinked: int
    last_error_code: str | None


@dataclass(frozen=True)
class Checkpoint:
    source_id: str
    source_instance: str
    segment_id: str
    offset: int
    parser_version: str | None
    ingest_seq: int


def _path_has_symlink(path: Path) -> bool:
    absolute = path if path.is_absolute() else path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        if part == ".":
            continue
        if part == "..":
            if current != Path(absolute.anchor):
                current = current.parent
            continue
        current = current / part
        if current.is_symlink():
            return True
    return False


def _observation_state(home: Path) -> str:
    if not home.exists():
        return "off"
    if home.is_symlink() or not home.is_dir():
        return "unreadable"
    path = home / "config.json"
    if not path.exists():
        return "off"
    if path.is_symlink():
        return "unreadable"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return "unreadable"
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        return "unreadable"
    observation = data.get("observation")
    if isinstance(observation, dict) and observation.get("enabled") is True:
        return "on"
    return "off"


def _chmod(path: Path, mode: int) -> None:
    os.chmod(path, mode)


def _restrict_db(home: Path) -> None:
    for name in ("audit.db", "audit.db-wal", "audit.db-shm"):
        path = home / name
        if path.is_file() and not path.is_symlink():
            _chmod(path, 0o600)


def _key_text(event: dict[str, Any]) -> str:
    return json.dumps(list(dedup_key(event)), ensure_ascii=False, separators=(",", ":"))


def _payload(event: dict[str, Any]) -> str:
    return json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _complete_lines(raw: bytes) -> tuple[list[bytes], bool]:
    if not raw:
        return [], False
    truncated = not raw.endswith(b"\n")
    if truncated and b"\n" not in raw:
        return [], True
    body = raw.rsplit(b"\n", 1)[0] if truncated else raw
    return [line for line in body.split(b"\n") if line], truncated


class EventStore:
    def __init__(
        self, home: Path, connection: sqlite3.Connection, *, read_only: bool
    ) -> None:
        self.home = home
        self._conn = connection
        self._read_only = read_only

    @classmethod
    def open(
        cls,
        home: Path,
        *,
        confirmed: bool = False,
        read_only: bool = False,
    ) -> EventStore:
        root = Path(home)
        if _path_has_symlink(root):
            raise StoreError("runtime home symlink is refused")
        state = _observation_state(root)
        if state == "unreadable":
            raise StoreError("observation switch cannot be read")
        if state != "on":
            raise StoreError("observation is not enabled")
        database = root / "audit.db"
        spool = root / "spool"
        if database.is_symlink() or spool.is_symlink():
            raise StoreError("store symlink is refused")
        if read_only:
            if not database.is_file():
                raise StoreError("event store does not exist")
            _require_intact(database)
            connection = sqlite3.connect(_ro_uri(database), uri=True)
            return cls(root, connection, read_only=True)
        if not confirmed:
            raise StoreError("confirmation required")
        root.mkdir(mode=0o700, exist_ok=True)
        _chmod(root, 0o700)
        spool.mkdir(mode=0o700, exist_ok=True)
        _chmod(spool, 0o700)
        if database.exists():
            _require_intact(database)
        connection = sqlite3.connect(database)
        try:
            _chmod(database, 0o600)
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA busy_timeout=5000")
            _ensure_schema(connection)
            _restrict_db(root)
            store = cls(root, connection, read_only=False)
            store._recover()
            return store
        except Exception:
            connection.close()
            raise

    def close(self) -> None:
        if self._conn is None:
            return
        if not self._read_only:
            try:
                self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except sqlite3.DatabaseError:
                pass
        self._conn.close()
        self._conn = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()

    def append(self, events: list[dict[str, Any]]) -> AppendResult:
        if self._read_only:
            raise StoreError("read-only context cannot persist")
        if not isinstance(events, list):
            raise StoreError("append requires a list of events")
        outcomes: list[Outcome] = []
        accepted_input: list[dict[str, Any]] = []
        for event in events:
            event_id = event.get("event_id") if isinstance(event, dict) else None
            try:
                validate_events([event])
            except _SCHEMA_ERRORS:
                self._mark("rejected", None, "schema-rejected")
                outcomes.append(
                    Outcome(
                        "rejected",
                        str(event_id) if event_id else None,
                        "schema-rejected",
                    )
                )
                continue
            if _secret_extension(event):
                self._mark(
                    "rejected", event["provenance"]["source_id"], "secret-rejected"
                )
                outcomes.append(
                    Outcome("rejected", event["event_id"], "secret-rejected")
                )
                continue
            accepted_input.append(event)
        if outcomes and not accepted_input:
            self._conn.commit()
        if not accepted_input:
            return AppendResult(tuple(outcomes))
        segment_id = uuid.uuid4().hex
        path, offsets = self._write_ready(segment_id, accepted_input)
        for event, offset in zip(accepted_input, offsets, strict=True):
            status = self._commit_event(event, segment_id, offset)
            outcomes.append(
                Outcome(
                    status, event["event_id"], None if status == "accepted" else status
                )
            )
        path.unlink(missing_ok=True)
        return AppendResult(tuple(outcomes))

    def replay(self) -> list[dict[str, Any]]:
        rows = self._conn.execute("SELECT payload FROM events ORDER BY ingest_seq")
        return [json.loads(row[0]) for row in rows]

    def quality(self) -> Quality:
        counts = {"duplicate": 0, "conflict": 0, "rejected": 0, "truncated": 0}
        for kind, count in self._conn.execute(
            "SELECT kind, COUNT(*) FROM quality GROUP BY kind"
        ):
            if kind in counts:
                counts[kind] = count
        accepted = self._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        unlinked = self._conn.execute(
            "SELECT COUNT(*) FROM events WHERE unlinked=1"
        ).fetchone()[0]
        last = self._conn.execute(
            "SELECT code FROM quality ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return Quality(
            accepted=accepted,
            duplicate=counts["duplicate"],
            conflict=counts["conflict"],
            rejected=counts["rejected"],
            truncated=counts["truncated"],
            pending=self._pending(),
            unlinked=unlinked,
            last_error_code=None if last is None else last[0],
        )

    def checkpoints(self) -> tuple[Checkpoint, ...]:
        rows = self._conn.execute(
            """
            SELECT source_id, source_instance, segment_id, offset, parser_version, ingest_seq
            FROM checkpoints
            ORDER BY ingest_seq
            """
        )
        return tuple(
            Checkpoint(
                source_id=row[0],
                source_instance=row[1],
                segment_id=row[2],
                offset=row[3],
                parser_version=row[4],
                ingest_seq=row[5],
            )
            for row in rows
        )

    def _write_ready(
        self, segment_id: str, events: list[dict[str, Any]]
    ) -> tuple[Path, list[int]]:
        spool = self.home / "spool"
        instance = self._instance()
        header = {
            _HEADER: 1,
            "segment_id": segment_id,
            "source_instance": instance,
        }
        blob = (json.dumps(header, separators=(",", ":")) + "\n").encode("utf-8")
        offsets: list[int] = []
        for event in events:
            line = {_HEADER: 1, "event": event}
            blob += (
                json.dumps(line, ensure_ascii=False, separators=(",", ":")) + "\n"
            ).encode("utf-8")
            offsets.append(len(blob))
        fd, temporary = tempfile.mkstemp(prefix=".ready.", dir=spool)
        temporary_path = Path(temporary)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(blob)
                handle.flush()
                os.fsync(handle.fileno())
            target = spool / f"{segment_id}.ready"
            os.replace(temporary_path, target)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
        _chmod(target, 0o600)
        return target, offsets

    def _commit_event(self, event: dict[str, Any], segment_id: str, offset: int) -> str:
        status = self._classify(event)
        if status == "accepted":
            self._insert(event)
        self._advance_checkpoint(event, segment_id, offset)
        self._conn.commit()
        return status

    def _classify(self, event: dict[str, Any]) -> str:
        key = _key_text(event)
        canonical = canonical_content(event)
        existing = self._conn.execute(
            "SELECT canonical FROM events WHERE dedup_key=?", (key,)
        ).fetchone()
        if existing is not None:
            if existing[0] == canonical:
                self._mark("duplicate", event["provenance"]["source_id"], "duplicate")
                return "duplicate"
            self._mark("conflict", event["provenance"]["source_id"], "conflict")
            return "conflict"
        by_id = self._conn.execute(
            "SELECT canonical FROM events WHERE event_id=?", (event["event_id"],)
        ).fetchone()
        if by_id is not None:
            code = "duplicate" if by_id[0] == canonical else "conflict"
            self._mark(code, event["provenance"]["source_id"], code)
            return code
        return "accepted"

    def _insert(self, event: dict[str, Any]) -> None:
        seq = self._conn.execute(
            "SELECT COALESCE(MAX(ingest_seq), 0) + 1 FROM events"
        ).fetchone()[0]
        unlinked = 1 if event.get("scope", {}).get("task_uid") is None else 0
        self._conn.execute(
            """
            INSERT INTO events(ingest_seq, event_id, dedup_key, canonical, payload, source_id, unlinked)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                seq,
                event["event_id"],
                _key_text(event),
                canonical_content(event),
                _payload(event),
                event["provenance"]["source_id"],
                unlinked,
            ),
        )

    def _advance_checkpoint(
        self, event: dict[str, Any], segment_id: str, offset: int
    ) -> None:
        seq = self._conn.execute(
            "SELECT COALESCE(MAX(ingest_seq), 0) FROM events"
        ).fetchone()[0]
        provenance = event["provenance"]
        self._conn.execute(
            """
            INSERT INTO checkpoints(
                source_id, segment_id, source_instance, offset, parser_version, ingest_seq
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id, segment_id) DO UPDATE SET
                offset=excluded.offset,
                parser_version=excluded.parser_version,
                ingest_seq=excluded.ingest_seq
            """,
            (
                provenance["source_id"],
                segment_id,
                self._instance(),
                offset,
                provenance.get("parser_version"),
                seq,
            ),
        )

    def _recover(self) -> None:
        spool = self.home / "spool"
        if not spool.is_dir():
            return
        for path in sorted(spool.glob("*.ready")):
            if path.is_symlink():
                continue
            raw = path.read_bytes()
            lines, truncated = _complete_lines(raw)
            if not lines:
                if truncated:
                    self._mark("truncated", None, "truncated-spool")
                    self._conn.commit()
                continue
            try:
                header = json.loads(lines[0])
            except json.JSONDecodeError:
                continue
            if not isinstance(header, dict) or header.get(_HEADER) != 1:
                continue
            if header.get("source_instance") != self._instance():
                continue
            segment_id = str(header.get("segment_id") or path.stem)
            offset = len(lines[0]) + 1
            for line in lines[1:]:
                offset += len(line) + 1
                try:
                    body = json.loads(line)
                    event = body["event"]
                    validate_events([event])
                except _SCHEMA_ERRORS:
                    self._mark("rejected", None, "schema-rejected")
                    self._conn.commit()
                    continue
                if _secret_extension(event):
                    self._mark("rejected", None, "secret-rejected")
                    self._conn.commit()
                    continue
                source_id = event["provenance"]["source_id"]
                if offset <= self._checkpoint_offset(source_id, segment_id):
                    continue
                self._commit_event(event, segment_id, offset)
            if truncated:
                self._mark("truncated", None, "truncated-spool")
                self._conn.commit()
                quarantined = path.with_suffix(".truncated")
                path.replace(quarantined)
                _chmod(quarantined, 0o600)
            else:
                path.unlink(missing_ok=True)

    def _pending(self) -> int:
        spool = self.home / "spool"
        if not spool.is_dir():
            return 0
        pending = 0
        for path in spool.glob("*.ready"):
            if path.is_symlink() or not self._owned_ready(path):
                continue
            lines, _truncated = _complete_lines(path.read_bytes())
            for line in lines[1:]:
                try:
                    event = json.loads(line)["event"]
                    validate_events([event])
                except _SCHEMA_ERRORS:
                    continue
                row = self._conn.execute(
                    "SELECT 1 FROM events WHERE dedup_key=?",
                    (_key_text(event),),
                ).fetchone()
                if row is None:
                    pending += 1
        return pending

    def _owned_ready(self, path: Path) -> bool:
        lines, _truncated = _complete_lines(path.read_bytes())
        if not lines:
            return False
        try:
            header = json.loads(lines[0])
        except json.JSONDecodeError:
            return False
        return (
            isinstance(header, dict)
            and header.get(_HEADER) == 1
            and header.get("source_instance") == self._instance()
        )

    def _checkpoint_offset(self, source_id: str, segment_id: str) -> int:
        row = self._conn.execute(
            "SELECT offset FROM checkpoints WHERE source_id=? AND segment_id=?",
            (source_id, segment_id),
        ).fetchone()
        return 0 if row is None else int(row[0])

    def _instance(self) -> str:
        row = self._conn.execute(
            "SELECT value FROM meta WHERE key='source_instance'"
        ).fetchone()
        if row is None:
            raise StoreError("audit schema is not version 1")
        return str(row[0])

    def _mark(self, kind: str, source_id: str | None, code: str) -> None:
        self._conn.execute(
            "INSERT INTO quality(kind, source_id, code, detail) VALUES (?, ?, ?, ?)",
            (kind, source_id, code, code),
        )


def _ro_uri(path: Path) -> str:
    return f"file:{quote(path.resolve().as_posix(), safe='/')}?mode=ro"


def _secret_extension(event: dict[str, Any]) -> bool:
    extensions = event.get("extensions")
    if not isinstance(extensions, dict):
        return False
    return any(_secret_key(key) for key in extensions)


def _secret_key(key: object) -> bool:
    normalized = "".join(ch for ch in str(key).casefold() if ch.isalnum())
    return normalized in {
        "apikey",
        "accesstoken",
        "refreshtoken",
        "idtoken",
        "token",
        "password",
        "passwd",
        "secret",
        "clientsecret",
        "cookie",
        "authorization",
        "bearer",
        "oauth",
        "oauthtoken",
    }


def _require_intact(database: Path) -> None:
    if database.is_symlink() or not database.is_file() or database.stat().st_size < 16:
        raise StoreError("audit database is damaged; gap file not written")
    try:
        connection = sqlite3.connect(_ro_uri(database), uri=True)
        try:
            row = connection.execute("PRAGMA integrity_check").fetchone()
        finally:
            connection.close()
    except sqlite3.DatabaseError as exc:
        raise StoreError("audit database is damaged; gap file not written") from exc
    if row is None or row[0] != "ok":
        raise StoreError("audit database is damaged; gap file not written")


def _ensure_schema(connection: sqlite3.Connection) -> None:
    names = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    if "meta" not in names:
        connection.executescript(
            """
            CREATE TABLE meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE events (
                ingest_seq INTEGER PRIMARY KEY,
                event_id TEXT NOT NULL UNIQUE,
                dedup_key TEXT NOT NULL UNIQUE,
                canonical TEXT NOT NULL,
                payload TEXT NOT NULL,
                source_id TEXT NOT NULL,
                unlinked INTEGER NOT NULL
            );
            CREATE TABLE checkpoints (
                source_id TEXT NOT NULL,
                segment_id TEXT NOT NULL,
                source_instance TEXT NOT NULL,
                offset INTEGER NOT NULL,
                parser_version TEXT,
                ingest_seq INTEGER NOT NULL,
                PRIMARY KEY (source_id, segment_id)
            );
            CREATE TABLE quality (
                id INTEGER PRIMARY KEY,
                kind TEXT NOT NULL,
                source_id TEXT,
                code TEXT,
                detail TEXT NOT NULL
            );
            INSERT INTO meta(key, value) VALUES ('schema_version', '1');
            """
        )
        connection.execute(
            "INSERT INTO meta(key, value) VALUES ('source_instance', ?)",
            (uuid.uuid4().hex,),
        )
        connection.commit()
        return
    version = connection.execute(
        "SELECT value FROM meta WHERE key='schema_version'"
    ).fetchone()
    if version is None or version[0] != SCHEMA_VERSION:
        raise StoreError("audit schema is not version 1")
    if (
        connection.execute(
            "SELECT value FROM meta WHERE key='source_instance'"
        ).fetchone()
        is None
    ):
        connection.execute(
            "INSERT INTO meta(key, value) VALUES ('source_instance', ?)",
            (uuid.uuid4().hex,),
        )
        connection.commit()
