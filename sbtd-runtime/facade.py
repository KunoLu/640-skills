"""R1.1 runtime facade and explicit project registration.

Wraps the existing task, route, handoff, and identity helpers. It does not
reimplement their state machine, and it does not create an event store.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from sbtd_handoff import HandoffStore
from sbtd_identity import DeveloperStore
from sbtd_project import TaskDataError, open_regular_file
from sbtd_task_routing import TaskRouter
from sbtd_task_state import (
    TaskSnapshot,
    TaskStateError,
    TaskStore,
    TaskTransfer,
)

_AUDIT_NAMES = (
    "audit.db",
    "projections.db",
    "spool",
    "snapshots",
    "exports",
    "backups",
)


class FacadeError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class OperationResult:
    operation_status: str
    state_persisted: bool
    audit_status: str
    executed: bool
    payload: Any = None
    reason: str | None = None


def _dump(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _reject_duplicate_keys(items: list[tuple[str, Any]]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for key, value in items:
        if key in data:
            raise ValueError(f"duplicate key {key}")
        data[key] = value
    return data


def _reject_nonfinite(token: str) -> None:
    raise ValueError(token)


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


def _new_id(prefix: str, taken: set[str]) -> str:
    while True:
        value = prefix + secrets.token_hex(8)
        if value not in taken:
            return value


def _task_payload(snapshot: TaskSnapshot) -> dict[str, Any]:
    fields = snapshot.document.frontmatter
    return {
        "task_id": fields["id"],
        "task_path": snapshot.task_path,
        "status": fields["status"],
        "workflow_mode": fields["workflow_mode"],
        "text": snapshot.document.text,
    }


def _public_project(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": record["project_id"],
        "alias": record.get("alias"),
        "root": record["root"],
        "repository_id": record.get("repository_id"),
        "worktree_id": record["worktree_id"],
        "registration_state": record.get("registration_state", "registered"),
    }


class RuntimeFacade:
    def __init__(
        self,
        runtime_home: Path,
        root: Path | None = None,
        *,
        read_only: bool = False,
        allow_user_dir_stats: bool = False,
    ) -> None:
        self.runtime_home = Path(runtime_home)
        self.root = None if root is None else Path(root)
        self.read_only = read_only
        # R1.1 has no event store. This flag is recorded so a later store can
        # tell the two read-only meanings apart; it never authorizes a write here.
        self.allow_user_dir_stats = allow_user_dir_stats

    @property
    def observation_enabled(self) -> bool:
        if self._observation_state() == "unreadable":
            raise FacadeError("observation switch cannot be read")
        return self._observation_state() == "on"

    def preview_registration(
        self,
        *,
        alias: str | None = None,
        repository_id: str | None = None,
    ) -> OperationResult:
        return self.register_project(
            alias=alias, repository_id=repository_id, confirmed=False
        )

    def register_project(
        self,
        *,
        alias: str | None = None,
        repository_id: str | None = None,
        confirmed: bool = False,
    ) -> OperationResult:
        try:
            canonical = str(self._canonical_root())
        except FacadeError as exc:
            return self._refused(exc.reason)
        if _path_has_symlink(self.runtime_home):
            return self._refused("runtime home symlink is refused")
        if not confirmed:
            return self._result(
                "preview",
                False,
                False,
                payload={
                    "root": canonical,
                    "alias": alias,
                    "repository_id": repository_id,
                },
            )
        if self.read_only:
            return self._refused("read-only context cannot persist")
        try:
            projects = self._projects()
        except FacadeError as exc:
            return self._refused(exc.reason)
        existing = next(
            (item for item in projects if item.get("root") == canonical), None
        )
        if existing is not None:
            if repository_id is not None and repository_id != existing.get(
                "repository_id"
            ):
                return self._refused(
                    "repository_id conflicts with the existing registration"
                )
            if alias is not None and existing.get("alias") not in (None, alias):
                return self._refused("alias conflicts with the existing registration")
            return self._ok(False, _public_project(existing))
        record = {
            "project_id": _new_id(
                "prj_", {str(item.get("project_id")) for item in projects}
            ),
            "alias": alias,
            "root": canonical,
            "repository_id": repository_id,
            "worktree_id": _new_id("wt_", set()),
            "registration_state": "registered",
            "registered_at": datetime.now(UTC).isoformat(),
        }
        self._save_document("registry.json", {"projects": [*projects, record]})
        return self._ok(True, _public_project(record))

    def unregister_project(
        self, project_id: str, *, confirmed: bool = False
    ) -> OperationResult:
        if self.read_only:
            return self._refused("read-only context cannot persist")
        if _path_has_symlink(self.runtime_home):
            return self._refused("runtime home symlink is refused")
        if not confirmed:
            return self._result(
                "preview", False, False, payload={"project_id": project_id}
            )
        try:
            projects = self._projects()
        except FacadeError as exc:
            return self._refused(exc.reason)
        kept = [item for item in projects if item.get("project_id") != project_id]
        if len(kept) == len(projects):
            return self._refused("project is not registered")
        self._save_document("registry.json", {"projects": kept})
        return self._ok(
            True, {"project_id": project_id, "registration_state": "unregistered"}
        )

    def list_registered_projects(self) -> OperationResult:
        if _path_has_symlink(self.runtime_home):
            return self._refused("runtime home symlink is refused")
        try:
            projects = self._projects()
        except FacadeError as exc:
            return self._refused(exc.reason)
        return self._ok(False, [_public_project(item) for item in projects])

    def inspect_project(self, project_id: str) -> OperationResult:
        listed = self.list_registered_projects()
        if listed.operation_status != "succeeded":
            return listed
        for item in listed.payload:
            if item["project_id"] == project_id:
                return self._ok(False, item)
        return self._refused("project is not registered")

    def set_observation_enabled(
        self, enabled: bool, *, confirmed: bool = False
    ) -> OperationResult:
        if self.read_only:
            return self._refused("read-only context cannot persist")
        if _path_has_symlink(self.runtime_home):
            return self._refused("runtime home symlink is refused")
        if not isinstance(enabled, bool):
            return self._refused("observation.enabled must be a boolean")
        if not confirmed:
            return self._result("preview", False, False, payload={"enabled": enabled})
        try:
            self._save_document(
                "config.json",
                {
                    "observation": {
                        "enabled": enabled,
                        "level": "metadata",
                        "failure_policy": "best-effort",
                    }
                },
            )
        except FacadeError as exc:
            return self._refused(exc.reason)
        return OperationResult(
            "succeeded",
            True,
            "gap" if enabled else "disabled",
            True,
            payload={"enabled": enabled},
        )

    def list_tasks(self) -> OperationResult:
        guard = self._guard(write=False)
        if guard is not None:
            return guard
        try:
            # Existing enumeration. TaskStore has no public list; a second walker would drift.
            records = TaskStore(self.root)._catalog()
        except TaskStateError as exc:
            return self._failed(exc.reason)
        return self._ok(
            False,
            [
                {
                    "task_id": task_id,
                    "task_path": snapshot.task_path,
                    "status": snapshot.document.frontmatter["status"],
                    "workflow_mode": snapshot.document.frontmatter["workflow_mode"],
                }
                for task_id, snapshot in sorted(records.items())
            ],
        )

    def inspect_task(self, task_id: str) -> OperationResult:
        return self._read_task("inspect", task_id)

    def get_task_history(self, task_id: str) -> OperationResult:
        guard = self._guard(write=False)
        if guard is not None:
            return guard
        try:
            snapshot = TaskStore(self.root, read_only=True).inspect(task_id)
        except TaskStateError as exc:
            return self._failed(exc.reason)
        return self._ok(
            False, {"task_id": task_id, "events": list(snapshot.document.events)}
        )

    def preview_route(self, request: Any) -> OperationResult:
        guard = self._guard(write=False)
        if guard is not None:
            return guard
        intent = getattr(request, "intent", None)
        if intent not in ("new", "continue", "question"):
            raise ValueError("intent must be new, continue or question")
        return self._result(
            "preview",
            False,
            False,
            payload={"status": "preview", "persisted": False, "intent": intent},
        )

    def apply_route(self, request: Any) -> OperationResult:
        guard = self._guard(write=True)
        if guard is not None:
            return guard
        try:
            decision = TaskRouter(TaskStore(self.root)).route(request)
        except TaskStateError as exc:
            return self._failed(exc.reason)
        return OperationResult(
            "succeeded" if decision.status == "ready" else decision.status,
            bool(decision.persisted),
            self._audit(),
            True,
            payload={
                "status": decision.status,
                "mode": decision.mode,
                "persisted": decision.persisted,
                "reason": decision.reason,
            },
        )

    def create(self, task_id: str, **kwargs: Any) -> OperationResult:
        return self._store_call("create", task_id, **kwargs)

    def select(self, task_id: str, **kwargs: Any) -> OperationResult:
        return self._store_call("select", task_id, **kwargs)

    def transition(self, task_id: str, status: str, **kwargs: Any) -> OperationResult:
        return self._store_call("transition", task_id, status, **kwargs)

    def set_mode(self, task_id: str, mode: str, **kwargs: Any) -> OperationResult:
        return self._store_call("set_mode", task_id, mode, **kwargs)

    def resume(self, task_id: str, **kwargs: Any) -> OperationResult:
        return self._store_call("resume", task_id, **kwargs)

    def reopen(self, task_id: str, **kwargs: Any) -> OperationResult:
        return self._store_call("reopen", task_id, **kwargs)

    def prepare_promote(self, task_id: str, **kwargs: Any) -> OperationResult:
        kwargs["retire_source"] = False
        return self._store_call("promote", task_id, **kwargs)

    def retire_original(self, task_id: str, **kwargs: Any) -> OperationResult:
        kwargs["retire_source"] = True
        return self._store_call("promote", task_id, **kwargs)

    def prepare_archive(self, task_id: str, **kwargs: Any) -> OperationResult:
        kwargs["retire_source"] = False
        return self._store_call("archive", task_id, **kwargs)

    def current_binding(self) -> OperationResult:
        return self._read_task("current_binding")

    def recovery_candidates(self, task_id: str | None = None) -> OperationResult:
        return self._read_task("recovery_candidates", task_id)

    def rebind(self, task_id: str, **kwargs: Any) -> OperationResult:
        return self._store_call("rebind", task_id, **kwargs)

    def inspect_handoff(self, relative_path: str) -> OperationResult:
        guard = self._guard(write=False)
        if guard is not None:
            return guard
        try:
            payload = HandoffStore(TaskStore(self.root, read_only=True)).load(
                relative_path
            )
        except TaskStateError as exc:
            return self._failed(exc.reason)
        return self._ok(False, payload)

    def list_handoffs(self) -> OperationResult:
        guard = self._guard(write=False)
        if guard is not None:
            return guard
        try:
            payload = HandoffStore(TaskStore(self.root, read_only=True)).reminders()
        except TaskStateError as exc:
            return self._failed(exc.reason)
        return self._ok(False, payload)

    def prepare_handoff(self, task_id: str, **kwargs: Any) -> OperationResult:
        guard = self._guard(write=False)
        if guard is not None:
            return guard
        kwargs["confirmed"] = False
        try:
            result = HandoffStore(TaskStore(self.root, read_only=True)).save(
                task_id, **kwargs
            )
        except TaskStateError as exc:
            return self._failed(exc.reason)
        return self._result(
            "preview",
            False,
            False,
            payload={"status": result.status, "reason": result.reason},
        )

    def save_handoff(self, task_id: str, **kwargs: Any) -> OperationResult:
        guard = self._guard(write=True)
        if guard is not None:
            return guard
        try:
            result = HandoffStore(TaskStore(self.root)).save(task_id, **kwargs)
        except TaskStateError as exc:
            return self._failed(exc.reason)
        return OperationResult(
            "succeeded" if result.persisted else result.status,
            bool(result.persisted),
            self._audit(),
            bool(result.persisted),
            payload={
                "status": result.status,
                "path": result.path,
                "reason": result.reason,
            },
        )

    def resolve_identity(self) -> OperationResult:
        if self.root is None or _path_has_symlink(self.root):
            return self._refused("symlink or missing project root is refused")
        try:
            result = DeveloperStore(self.root, read_only=True).resolve()
        except TaskStateError as exc:
            return self._failed(exc.reason)
        return self._ok(
            False,
            {
                "status": result.status,
                "name": result.name,
                "source": result.source,
                "reason": result.reason,
            },
        )

    def _store_call(self, name: str, *args: Any, **kwargs: Any) -> OperationResult:
        guard = self._guard(write=True)
        if guard is not None:
            return guard
        try:
            result = getattr(TaskStore(self.root), name)(*args, **kwargs)
        except TaskStateError as exc:
            return self._failed(exc.reason)
        return self._ok(True, _describe(result))

    def _read_task(self, name: str, *args: Any) -> OperationResult:
        guard = self._guard(write=False)
        if guard is not None:
            return guard
        try:
            result = getattr(TaskStore(self.root, read_only=True), name)(*args)
        except TaskStateError as exc:
            return self._failed(exc.reason)
        return self._ok(False, _describe(result))

    def _guard(self, *, write: bool) -> OperationResult | None:
        if write and self.read_only:
            return self._refused("read-only context cannot persist")
        try:
            if self._registered() is None:
                return self._refused("project root is not explicitly registered")
        except FacadeError as exc:
            return self._refused(exc.reason)
        return None

    def _registered(self) -> dict[str, Any] | None:
        canonical = str(self._canonical_root())
        for record in self._projects():
            if record.get("root") == canonical:
                return record
        return None

    def _canonical_root(self) -> Path:
        if self.root is None:
            raise FacadeError("project root is required")
        if _path_has_symlink(self.root):
            raise FacadeError("symlink project root is refused")
        if not self.root.is_dir():
            raise FacadeError("project root is not a directory")
        return self.root.resolve(strict=True)

    def _projects(self) -> list[dict[str, Any]]:
        data = self._read_json("registry.json")
        if data is None:
            return []
        projects = data.get("projects")
        if not isinstance(projects, list) or not all(
            isinstance(item, dict) for item in projects
        ):
            raise FacadeError("registry schema is not version 1")
        return projects

    def _read_json(self, name: str) -> dict[str, Any] | None:
        home = self.runtime_home
        if _path_has_symlink(home):
            raise FacadeError("runtime home symlink is refused")
        if not home.exists():
            return None
        path = home / name
        if not path.exists():
            return None
        try:
            with open_regular_file(path, name) as handle:
                raw = handle.read()
            data = json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_nonfinite,
            )
        except (
            TaskDataError,
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            ValueError,
        ) as exc:
            raise FacadeError(f"{name} cannot be parsed") from exc
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise FacadeError(f"{name} schema is not version 1")
        return data

    def _write_json(self, name: str, payload: dict[str, Any]) -> None:
        if name in _AUDIT_NAMES:
            raise FacadeError("event storage is not part of R1.1")
        home = self.runtime_home
        if _path_has_symlink(home):
            raise FacadeError("runtime home symlink is refused")
        if home.exists() and not home.is_dir():
            raise FacadeError("runtime home is not a directory")
        home.mkdir(mode=0o700, exist_ok=True)
        os.chmod(home, 0o700)
        target = home / name
        if target.is_symlink():
            raise FacadeError(f"{name} symlink is refused")
        fd, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=home)
        try:
            with os.fdopen(fd, "wb") as handle:
                if hasattr(os, "fchmod"):
                    os.fchmod(handle.fileno(), 0o600)
                else:
                    os.chmod(temporary, 0o600)
                handle.write(_dump(payload))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise
        os.chmod(target, 0o600)

    def _observation_state(self) -> str:
        try:
            config = self._read_json("config.json")
        except FacadeError:
            return "unreadable"
        if not config:
            return "off"
        observation = config.get("observation")
        if isinstance(observation, dict) and observation.get("enabled") is True:
            return "on"
        return "off"

    def _audit(self) -> str:
        return "disabled" if self._observation_state() == "off" else "gap"

    def _save_document(self, name: str, updates: dict[str, Any]) -> None:
        current = self._read_json(name)
        payload = {} if current is None else dict(current)
        payload.update(updates)
        payload["schema_version"] = 1
        self._write_json(name, payload)

    def _result(
        self,
        status: str,
        persisted: bool,
        executed: bool,
        payload: Any = None,
        reason: str | None = None,
    ) -> OperationResult:
        return OperationResult(
            status, persisted, self._audit(), executed, payload, reason
        )

    def _ok(self, persisted: bool, payload: Any) -> OperationResult:
        return self._result("succeeded", persisted, persisted, payload)

    def _refused(self, reason: str) -> OperationResult:
        if self.read_only:
            kind = (
                "project read-only, user-dir stats not stored in R1.1"
                if self.allow_user_dir_stats
                else "fully read-only"
            )
            reason = f"{reason} ({kind})"
        return self._result("refused", False, False, reason=reason)

    def _failed(self, reason: str) -> OperationResult:
        return self._result("failed", False, False, reason=reason)


def _describe(result: Any) -> Any:
    if isinstance(result, TaskSnapshot):
        return _task_payload(result)
    if isinstance(result, TaskTransfer):
        return {
            "status": result.status,
            "task_id": result.task.document.frontmatter["id"],
            "source_path": result.source_path,
            "target_path": result.target_path,
        }
    if isinstance(result, tuple):
        return [_describe(item) for item in result]
    return result


class HelperAdapter:
    """Old helper call shape. Registered + switch off matches a direct call."""

    def __init__(
        self, root: Path, runtime_home: Path, *, read_only: bool = False
    ) -> None:
        self.root = Path(root)
        self.runtime_home = Path(runtime_home)
        self.read_only = read_only

    def create(self, task_id: str, **kwargs: Any) -> TaskSnapshot:
        return self._store_call("create", task_id, **kwargs)

    def select(self, task_id: str, **kwargs: Any) -> TaskSnapshot:
        return self._store_call("select", task_id, **kwargs)

    def transition(self, task_id: str, status: str, **kwargs: Any) -> TaskSnapshot:
        return self._store_call("transition", task_id, status, **kwargs)

    def set_mode(self, task_id: str, mode: str, **kwargs: Any) -> TaskSnapshot:
        return self._store_call("set_mode", task_id, mode, **kwargs)

    def resume(self, task_id: str, **kwargs: Any) -> TaskSnapshot:
        return self._store_call("resume", task_id, **kwargs)

    def reopen(self, task_id: str, **kwargs: Any) -> TaskSnapshot:
        return self._store_call("reopen", task_id, **kwargs)

    def apply_route(self, request: Any) -> Any:
        self._require()
        return TaskRouter(TaskStore(self.root)).route(request)

    def save_handoff(self, task_id: str, **kwargs: Any) -> Any:
        self._require()
        return HandoffStore(TaskStore(self.root)).save(task_id, **kwargs)

    def _store_call(self, name: str, *args: Any, **kwargs: Any) -> Any:
        self._require()
        return getattr(TaskStore(self.root), name)(*args, **kwargs)

    def _require(self) -> None:
        facade = RuntimeFacade(self.runtime_home, self.root, read_only=self.read_only)
        if self.read_only:
            raise FacadeError("read-only context cannot persist")
        if facade._registered() is None:
            raise FacadeError("project root is not explicitly registered")
