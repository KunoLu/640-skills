"""R1.1 facade, registration, and read-only checks.

Scenario text lives in spec/r1.1-facade-scenarios.md. This repository does
not create .feature files. The consumer seams are RuntimeFacade and
HelperAdapter. Old helper imports stay usable without registration.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT.parent / "sbtd-workflow-onboard" / "scripts"
for path in (ROOT, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from sbtd_handoff import HandoffPolicy, HandoffStore
from sbtd_identity import DeveloperStore
from sbtd_task_routing import RouteRequest, TaskRouter
from sbtd_task_state import TaskStore

from facade import FacadeError, HelperAdapter, RuntimeFacade


AUDIT_NAMES = {"audit.db", "projections.db", "spool", "snapshots", "exports", "backups"}
HANDOFF_CONTENT = {
    "goal": "Continue synthetic work",
    "decisions": ["keep scope"],
    "completed": ["registered the root"],
    "remaining": ["finish the slice"],
    "changed_files": ["task.md"],
    "verification": ["compare business files"],
    "do_not_repeat": ["do not scan siblings"],
    "next_action": "compare the trees",
    "limitations": "no event store in this slice",
}


class FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        moment = datetime(2026, 10, 16, 8, 0, tzinfo=timezone.utc)
        if tz is not None:
            return moment.astimezone(tz)
        return moment


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull},
        capture_output=True,
        check=True,
    )


def _init_project(parent: Path, name: str = "project") -> Path:
    root = parent / name
    root.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main", str(root)],
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull},
        capture_output=True,
        check=True,
    )
    (root / ".gitignore").write_text("/.sbtd/\n/docs/handoffs/\n", encoding="utf-8")
    return root


def _business_files(root: Path) -> dict[str, bytes]:
    found: dict[str, bytes] = {}
    marker = str(root).encode()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if relative == ".git" or relative.startswith(".git/"):
            continue
        if path.is_file() and not path.is_symlink():
            found[relative] = path.read_bytes().replace(marker, b"<root>")
    return found


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


class FacadeRegistrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="sbtd-r11-")
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name)
        self.home = self.parent / "runtime-home"
        self.root = _init_project(self.parent)
        for name in ("sbtd_task_state.datetime", "sbtd_handoff.datetime"):
            clock = mock.patch(name, FrozenDateTime)
            clock.start()
            self.addCleanup(clock.stop)

    def _facade(self, root: Path | None = None, **kwargs) -> RuntimeFacade:
        return RuntimeFacade(self.home, root or self.root, **kwargs)

    def _adapter(self, root: Path | None = None, **kwargs) -> HelperAdapter:
        return HelperAdapter(root or self.root, self.home, **kwargs)

    def _register(self, root: Path | None = None) -> str:
        result = self._facade(root).register_project(confirmed=True)
        self.assertEqual(result.operation_status, "succeeded")
        self.assertTrue(result.state_persisted)
        self.assertFalse(result.payload["project_id"].startswith("/"))
        self.assertNotIn(str(root or self.root), result.payload["project_id"])
        return result.payload["project_id"]

    def test_switch_off_matches_direct_helper_and_writes_no_audit(self) -> None:
        direct_root = _init_project(self.parent, "direct")
        wrapped_root = _init_project(self.parent, "wrapped")
        self._register(wrapped_root)
        self.assertFalse(self._facade(wrapped_root).observation_enabled)
        direct = TaskStore(direct_root)
        adapter = self._adapter(wrapped_root)
        direct.create("slice", body="Keep the helper path.\n", confirmed=True)
        adapter.create("slice", body="Keep the helper path.\n", confirmed=True)
        direct.transition(
            "slice", "in-progress", reason="started", evidence="scope", confirmed=True
        )
        adapter.transition(
            "slice", "in-progress", reason="started", evidence="scope", confirmed=True
        )
        direct.set_mode("slice", "lite", note="user kept the short path", confirmed=True)
        adapter.set_mode("slice", "lite", note="user kept the short path", confirmed=True)
        self.assertEqual(_business_files(direct_root), _business_files(wrapped_root))
        self.assertFalse((self.home / "audit.db").exists())
        self.assertFalse((self.home / "spool").exists())
        self.assertTrue((self.home / "registry.json").is_file())

    def test_switch_on_reports_gap_without_event_store(self) -> None:
        direct_root = _init_project(self.parent, "direct-on")
        wrapped_root = _init_project(self.parent, "wrapped-on")
        facade = self._facade(wrapped_root)
        enabled = facade.set_observation_enabled(True, confirmed=True)
        self.assertEqual(enabled.audit_status, "gap")
        self.assertTrue(facade.observation_enabled)
        self._register(wrapped_root)
        TaskStore(direct_root).create(
            "slice", body="Observation must not fork the write.\n", confirmed=True
        )
        result = facade.create(
            "slice", body="Observation must not fork the write.\n", confirmed=True
        )
        self.assertEqual(result.operation_status, "succeeded")
        self.assertTrue(result.state_persisted)
        self.assertEqual(result.audit_status, "gap")
        self.assertNotEqual(result.audit_status, "recorded")
        self.assertEqual(_business_files(direct_root), _business_files(wrapped_root))
        for name in AUDIT_NAMES:
            self.assertFalse((self.home / name).exists(), name)

    def test_unregistered_and_sibling_bait_are_not_read(self) -> None:
        bait = self.parent / "sibling-bait"
        bait.mkdir()
        (bait / "secret.txt").write_text("do not read", encoding="utf-8")
        os.chmod(bait, 0)
        self.addCleanup(os.chmod, bait, 0o755)
        other = _init_project(self.parent, "other")
        TaskStore(other).create("foreign", body="Not this root.\n", confirmed=True)
        refused = self._facade().list_tasks()
        self.assertEqual(refused.operation_status, "refused")
        self.assertFalse(refused.state_persisted)
        self.assertFalse(refused.executed)
        project_id = self._register()
        listed = self._facade().list_registered_projects()
        self.assertEqual([item["project_id"] for item in listed.payload], [project_id])
        self.assertNotIn("foreign", str(listed.payload))
        tasks = self._facade().list_tasks()
        self.assertEqual(tasks.payload, [])
        self.assertFalse((self.home / "audit.db").exists())

    def test_read_only_context_writes_nothing(self) -> None:
        before_project = _business_files(self.root)
        facade = self._facade(read_only=True, allow_user_dir_stats=True)
        facade.set_observation_enabled(True, confirmed=True)
        registered = facade.register_project(confirmed=True)
        created = facade.create("slice", body="Must not land.\n", confirmed=True)
        with mock.patch.object(DeveloperStore, "ensure", side_effect=AssertionError("ensure")):
            identity = facade.resolve_identity()
        self.assertEqual(registered.operation_status, "refused")
        self.assertEqual(created.operation_status, "refused")
        self.assertFalse(created.state_persisted)
        self.assertEqual(identity.operation_status, "succeeded")
        self.assertFalse(identity.state_persisted)
        self.assertEqual(identity.payload["status"], "needs-name")
        self.assertEqual(_business_files(self.root), before_project)
        self.assertFalse(self.home.exists())

    def test_symlink_root_and_runtime_home_are_refused(self) -> None:
        link = self.parent / "linked-root"
        link.symlink_to(self.root, target_is_directory=True)
        refused = RuntimeFacade(self.home, link).register_project(confirmed=True)
        self.assertEqual(refused.operation_status, "refused")
        self.assertFalse(self.home.exists())
        self.home.mkdir()
        (self.home / "notes.txt").write_text("keep", encoding="utf-8")
        os.chmod(self.home, 0o755)
        linked_home = self.parent / "linked-home"
        linked_home.symlink_to(self.home, target_is_directory=True)
        home_refused = RuntimeFacade(linked_home, self.root).register_project(confirmed=True)
        self.assertEqual(home_refused.operation_status, "refused")
        self.assertEqual((self.home / "notes.txt").read_text(encoding="utf-8"), "keep")
        self.assertFalse((self.home / "registry.json").exists())

    def test_registry_permissions_idempotence_and_unregister(self) -> None:
        self.home.mkdir()
        (self.home / "notes.txt").write_text("keep", encoding="utf-8")
        broken = self.home / "registry.json"
        broken.write_text('{"schema_version": 99}\n', encoding="utf-8")
        blocked = self._facade().register_project(confirmed=True)
        self.assertEqual(blocked.operation_status, "refused")
        self.assertEqual(broken.read_text(encoding="utf-8"), '{"schema_version": 99}\n')
        broken.unlink()
        first = self._facade().register_project(
            alias="demo", repository_id="repo-explicit", confirmed=True
        )
        _git(self.root, "remote", "add", "origin", "https://example.invalid/same.git")
        again = self._facade().register_project(confirmed=True)
        self.assertEqual(first.payload["project_id"], again.payload["project_id"])
        self.assertEqual(again.payload["repository_id"], "repo-explicit")
        other = _init_project(self.parent, "same-remote")
        _git(other, "remote", "add", "origin", "https://example.invalid/same.git")
        separate = RuntimeFacade(self.home, other).register_project(confirmed=True)
        self.assertIsNone(separate.payload["repository_id"])
        self.assertNotEqual(separate.payload["project_id"], first.payload["project_id"])
        self.assertEqual(_mode(self.home), 0o700)
        self.assertEqual(_mode(self.home / "registry.json"), 0o600)
        self.assertEqual((self.home / "notes.txt").read_text(encoding="utf-8"), "keep")
        TaskStore(self.root).create("kept", body="Still here.\n", confirmed=True)
        before = (self.root / ".sbtd/tasks/kept/task.md").read_bytes()
        removed = self._facade().unregister_project(first.payload["project_id"], confirmed=True)
        self.assertEqual(removed.operation_status, "succeeded")
        self.assertEqual((self.root / ".sbtd/tasks/kept/task.md").read_bytes(), before)
        listed = self._facade().list_registered_projects().payload
        self.assertEqual([item["project_id"] for item in listed], [separate.payload["project_id"]])
        self.assertFalse((self.home / "audit.db").exists())

    def test_preview_route_does_not_call_saving_route(self) -> None:
        self._register()
        request = RouteRequest(
            intent="new",
            task_id="previewed",
            explicit_mode="strict",
            confirmed=True,
            body="Must stay unwritten.\n",
        )
        with mock.patch.object(TaskRouter, "route", side_effect=AssertionError("route")):
            preview = self._facade().preview_route(request)
        self.assertFalse(preview.executed)
        self.assertFalse(preview.state_persisted)
        self.assertEqual(preview.operation_status, "preview")
        self.assertFalse((self.root / ".sbtd").exists())
        applied = self._facade().apply_route(request)
        self.assertTrue(applied.state_persisted)
        self.assertTrue((self.root / "ai/tasks/previewed/task.md").is_file())

    def test_handoff_prepare_does_not_write_and_save_matches_helper(self) -> None:
        direct_root = _init_project(self.parent, "handoff-direct")
        wrapped_root = _init_project(self.parent, "handoff-wrapped")
        self._register(wrapped_root)
        for root in (direct_root, wrapped_root):
            TaskStore(root).create("slice", body="Handoff subject.\n", confirmed=True)
        prepared = self._facade(wrapped_root).prepare_handoff(
            "slice", content=HANDOFF_CONTENT, trigger="manual", policy=HandoffPolicy()
        )
        self.assertFalse(prepared.executed)
        self.assertFalse(prepared.state_persisted)
        self.assertFalse((wrapped_root / "docs/handoffs").exists())
        direct = HandoffStore(TaskStore(direct_root)).save(
            "slice",
            content=HANDOFF_CONTENT,
            trigger="manual",
            policy=HandoffPolicy(),
            confirmed=True,
            redaction_confirmed=True,
        )
        adapted = self._adapter(wrapped_root).save_handoff(
            "slice",
            content=HANDOFF_CONTENT,
            trigger="manual",
            policy=HandoffPolicy(),
            confirmed=True,
            redaction_confirmed=True,
        )
        self.assertEqual(direct.status, adapted.status)
        self.assertEqual(_business_files(direct_root), _business_files(wrapped_root))

    def test_old_helper_import_does_not_require_registration(self) -> None:
        isolated = self.parent / "unused-home"
        with mock.patch.dict(os.environ, {"SBTD_RUNTIME_HOME": str(isolated)}):
            created = TaskStore(self.root).create(
                "plain", body="Old import still writes.\n", confirmed=True
            )
        self.assertEqual(created.document.frontmatter["id"], "plain")
        self.assertFalse(isolated.exists())
        with self.assertRaises(FacadeError):
            self._adapter().create("plain", body="Blocked.\n", confirmed=True)

    def test_intermediate_symlink_cannot_redirect_root_or_home(self) -> None:
        target = self.parent / "escaped"
        target.mkdir()
        (target / "secret.txt").write_text("secret", encoding="utf-8")
        link = self.parent / "jump"
        link.symlink_to(target, target_is_directory=True)
        child = link / "child"
        child.mkdir()
        before = (target / "secret.txt").read_bytes()
        refused = RuntimeFacade(self.home, child).register_project(confirmed=True)
        self.assertEqual(refused.operation_status, "refused")
        self.assertFalse(self.home.exists())
        self.assertEqual((target / "secret.txt").read_bytes(), before)
        elsewhere = self.parent / "elsewhere"
        (elsewhere / "nested").mkdir(parents=True)
        (elsewhere / "other").mkdir()
        dotdot = self.parent / "dotdot"
        dotdot.symlink_to(elsewhere / "nested", target_is_directory=True)
        escaped = dotdot / ".." / "other"
        escaped_refused = RuntimeFacade(self.home, escaped).register_project(confirmed=True)
        self.assertEqual(escaped_refused.operation_status, "refused")
        self.assertFalse((elsewhere / "other" / ".sbtd").exists())
        real_home = self.parent / "real-home"
        real_home.mkdir()
        (real_home / "notes.txt").write_text("keep", encoding="utf-8")
        mode_before = _mode(real_home)
        home_link = self.parent / "home-jump"
        home_link.symlink_to(real_home, target_is_directory=True)
        home_refused = RuntimeFacade(home_link / "nested", self.root).register_project(
            confirmed=True
        )
        self.assertEqual(home_refused.operation_status, "refused")
        self.assertEqual((real_home / "notes.txt").read_text(encoding="utf-8"), "keep")
        self.assertFalse((real_home / "nested").exists())
        self.assertEqual(_mode(real_home), mode_before)

    def test_registry_and_config_updates_keep_unrelated_keys(self) -> None:
        self.home.mkdir(mode=0o700)
        (self.home / "registry.json").write_text(
            json.dumps(
                {"schema_version": 1, "projects": [], "actors": [{"actor_id": "kept"}]}
            )
            + "\n",
            encoding="utf-8",
        )
        (self.home / "config.json").write_text(
            json.dumps({"schema_version": 1, "display": {"timezone": "UTC"}}) + "\n",
            encoding="utf-8",
        )
        registered = self._facade().register_project(confirmed=True)
        self.assertEqual(registered.operation_status, "succeeded")
        enabled = self._facade().set_observation_enabled(True, confirmed=True)
        self.assertEqual(enabled.operation_status, "succeeded")
        registry = json.loads((self.home / "registry.json").read_text(encoding="utf-8"))
        config = json.loads((self.home / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(registry["actors"], [{"actor_id": "kept"}])
        self.assertEqual(config["display"], {"timezone": "UTC"})
        self.assertTrue(config["observation"]["enabled"])

    def test_unreadable_switch_is_a_gap_not_disabled(self) -> None:
        self._register()
        facade = self._facade()
        facade.set_observation_enabled(True, confirmed=True)
        (self.home / "config.json").write_text("{", encoding="utf-8")
        result = facade.create("slice", body="Still the helper write.\n", confirmed=True)
        self.assertEqual(result.operation_status, "succeeded")
        self.assertTrue(result.state_persisted)
        self.assertEqual(result.audit_status, "gap")
        self.assertNotEqual(result.audit_status, "disabled")
        self.assertTrue((self.root / ".sbtd/tasks/slice/task.md").is_file())
        self.assertFalse((self.home / "audit.db").exists())


if __name__ == "__main__":
    unittest.main()
