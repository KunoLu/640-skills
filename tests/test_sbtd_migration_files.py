from __future__ import annotations

import hashlib
import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from onboard_contracts import ContractError, canonical_json_bytes
from sbtd_migration_files import (
    RetainedObjectError,
    backup_reference,
    directory_snapshot,
    install_reference,
    read_file,
    remove_reference,
    require_private_directory,
    save_document,
    snapshot,
    write_file,
)

ABSENT = {"type": "absent", "checksum": None}


def file_state(content: bytes) -> dict:
    return {"type": "file", "checksum": hashlib.sha256(content).hexdigest()}


class MigrationFileTests(unittest.TestCase):
    def test_directory_publication_uses_only_the_fully_verified_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            project = root / "project"
            project.mkdir()
            source = root / "candidate"
            source.mkdir()
            (source / "a.txt").write_bytes(b"approved-a")
            (source / "b.txt").write_bytes(b"approved-b")
            reference = {"path": str(source), "state": snapshot(source)}
            destination = project / "published"
            sync = os.fsync
            observed = []
            changed = False

            def change_after_first_published_file(descriptor):
                nonlocal changed
                sync(descriptor)
                if (
                    (destination / "a.txt").exists()
                    and not (destination / "b.txt").exists()
                    and not changed
                ):
                    (source / "b.txt").write_bytes(b"SYNTHETIC_PRIVATE_DIRECTORY_BYTES")
                    changed = True
                if (destination / "b.txt").exists():
                    observed.append((destination / "b.txt").read_bytes())

            with mock.patch(
                "sbtd_migration_files.os.fsync",
                side_effect=change_after_first_published_file,
            ):
                try:
                    install_reference(reference, destination, ABSENT, scope=project)
                except ContractError:
                    pass

            self.assertNotIn(b"SYNTHETIC_PRIVATE_DIRECTORY_BYTES", observed)
            if (destination / "b.txt").exists():
                self.assertEqual((destination / "b.txt").read_bytes(), b"approved-b")

    def test_rejected_directory_readback_keeps_a_concurrent_user_edit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            project = root / "project"
            project.mkdir()
            source = root / "candidate"
            source.mkdir()
            (source / "owned.txt").write_bytes(b"approved")
            reference = {"path": str(source), "state": snapshot(source)}
            destination = project / "published"
            actual_snapshot = snapshot
            changed = False

            def edit_after_copy(path):
                nonlocal changed
                if Path(path) == destination and destination.is_dir() and not changed:
                    (destination / "owned.txt").write_bytes(b"user-edit")
                    changed = True
                return actual_snapshot(path)

            with mock.patch(
                "sbtd_migration_files.snapshot", side_effect=edit_after_copy
            ):
                with self.assertRaises(ContractError):
                    install_reference(reference, destination, ABSENT, scope=project)

            self.assertTrue(changed)
            self.assertEqual((destination / "owned.txt").read_bytes(), b"user-edit")

    def test_unapproved_file_bytes_are_never_published_from_a_changed_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            project = root / "project"
            project.mkdir()
            source = root / "candidate.txt"
            source.write_bytes(b"approved")
            reference = {"path": str(source), "state": file_state(b"approved")}
            destination = project / "published.txt"
            destination.write_bytes(b"original")
            open_file = os.open
            changed = False

            def change_when_staging_opens(path, flags, *args, **kwargs):
                nonlocal changed
                if Path(path).parent == project and flags & os.O_CREAT and not changed:
                    source.write_bytes(b"SYNTHETIC_PRIVATE_CANDIDATE")
                    changed = True
                return open_file(path, flags, *args, **kwargs)

            rejected = False
            with mock.patch(
                "sbtd_migration_files.os.open", side_effect=change_when_staging_opens
            ):
                try:
                    install_reference(
                        reference, destination, file_state(b"original"), scope=project
                    )
                except ContractError:
                    rejected = True

            self.assertEqual(
                destination.read_bytes(), b"original" if rejected else b"approved"
            )
            self.assertNotEqual(
                destination.read_bytes(), b"SYNTHETIC_PRIVATE_CANDIDATE"
            )

    def test_conflicting_restore_reports_the_retained_object_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / "owned.txt"
            target.write_bytes(b"original")
            before = snapshot(target)
            rename = os.rename

            def competing_writer(source, destination, *args, **kwargs):
                rename(source, destination, *args, **kwargs)
                if Path(source) == target:
                    Path(destination).write_bytes(b"captured-user-version")
                    target.write_bytes(b"later-user-version")

            with mock.patch(
                "sbtd_migration_files.os.rename", side_effect=competing_writer
            ):
                with self.assertRaises(RetainedObjectError) as caught:
                    remove_reference(target, before, scope=root)

            self.assertEqual(target.read_bytes(), b"later-user-version")
            retained = caught.exception.retained_refs[0]
            retained_path = Path(retained["path"])
            self.assertEqual(retained_path.read_bytes(), b"captured-user-version")
            self.assertEqual(snapshot(retained_path), retained["state"])
            require_private_directory(retained_path.parent)
            self.assertNotIn(str(retained_path), str(caught.exception))

    def test_file_removal_preserves_a_change_after_the_initial_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / "owned.txt"
            target.write_bytes(b"original")
            expected = snapshot(target)
            actual_snapshot = snapshot
            changed = False

            def change_after_observation(path):
                nonlocal changed
                observed = actual_snapshot(path)
                if Path(path) == target and not changed:
                    changed = True
                    target.write_bytes(b"new-user-content")
                return observed

            with mock.patch(
                "sbtd_migration_files.snapshot", side_effect=change_after_observation
            ):
                with self.assertRaises(ContractError):
                    remove_reference(target, expected, scope=root)

            self.assertTrue(changed)
            self.assertEqual(target.read_bytes(), b"new-user-content")
            self.assertEqual(list(root.iterdir()), [target])

    def test_backup_does_not_follow_a_symbolic_link_in_a_source_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            project = root / "project"
            project.mkdir()
            external = root / "external"
            external.mkdir()
            (external / "private.txt").write_bytes(b"synthetic-private")
            (project / "alias").symlink_to(external, target_is_directory=True)
            vault = root / "vault"
            vault.mkdir(mode=0o700)
            reference = {
                "path": str(project / "alias/private.txt"),
                "state": file_state(b"synthetic-private"),
            }

            with self.assertRaises(ContractError):
                backup_reference(reference, vault / "copied.txt", private_root=vault)

            self.assertFalse((vault / "copied.txt").exists())
            self.assertEqual(
                (external / "private.txt").read_bytes(), b"synthetic-private"
            )

    def test_directory_swap_preserves_changes_to_the_set_aside_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            project = root / "project"
            project.mkdir()
            target = project / "owned"
            target.mkdir()
            (target / "original.txt").write_bytes(b"original")
            candidate = root / "candidate"
            candidate.mkdir()
            (candidate / "new.txt").write_bytes(b"new")
            vault = root / "vault"
            vault.mkdir(mode=0o700)
            before = snapshot(target)
            backup = backup_reference(
                {"path": str(target), "state": before},
                vault / "original",
                private_root=vault,
            )
            reference = {"path": str(candidate), "state": snapshot(candidate)}
            rename = os.rename
            retired_paths = []

            def change_after_move(source, destination, *args, **kwargs):
                rename(source, destination, *args, **kwargs)
                destination = Path(destination)
                if Path(source) == target and destination.name.startswith(
                    ".sbtd-migration-retired-"
                ):
                    retired_paths.append(destination)
                    (destination / "user-added.txt").write_bytes(b"new-user-content")

            with mock.patch(
                "sbtd_migration_files.os.rename", side_effect=change_after_move
            ):
                with self.assertRaises(ContractError):
                    install_reference(
                        reference, target, before, scope=project, backup_ref=backup
                    )

            self.assertTrue(retired_paths)
            preserved = [path / "user-added.txt" for path in [target, *retired_paths]]
            self.assertTrue(
                any(
                    path.is_file() and path.read_bytes() == b"new-user-content"
                    for path in preserved
                )
            )
            self.assertEqual(
                (vault / "original/original.txt").read_bytes(), b"original"
            )

    def test_directory_state_uses_the_published_flat_wire_vector(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "a").mkdir()
            (root / "a/x").write_bytes(b"x")
            (root / "a.child").write_bytes(b"flat")
            (root / "z").mkdir()

            state, entries = directory_snapshot(root)

            self.assertEqual(
                state,
                {
                    "type": "directory",
                    "checksum": "f62ac98e6a08aba8454796e1cf6bb706b2f653c32e839d9195ac26b7bc34798d",
                },
            )
            self.assertEqual(
                entries,
                [
                    {"path": "a", "type": "directory", "checksum": None},
                    {
                        "path": "a.child",
                        "type": "file",
                        "checksum": "5dc27af287fa554aa10fec9de8d724a7964572f1ffd24c2b00e1a3a860ce7679",
                    },
                    {
                        "path": "a/x",
                        "type": "file",
                        "checksum": "2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881",
                    },
                    {"path": "z", "type": "directory", "checksum": None},
                ],
            )

    def test_original_tree_is_complete_and_conflicting_backup_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "source"
            source.mkdir()
            (source / "empty").mkdir()
            (source / "payload.bin").write_bytes(b"\x00fixture-private\xff")
            vault = root / "vault"
            vault.mkdir(mode=0o700)
            reference = {"path": str(source), "state": snapshot(source)}
            destination = vault / "original"

            saved = backup_reference(reference, destination, private_root=vault)

            self.assertEqual(
                (destination / "payload.bin").read_bytes(), b"\x00fixture-private\xff"
            )
            self.assertTrue((destination / "empty").is_dir())
            self.assertEqual(
                (source / "payload.bin").read_bytes(), b"\x00fixture-private\xff"
            )
            self.assertEqual(saved["state"], snapshot(destination))
            (destination / "payload.bin").write_bytes(b"user-owned-change")
            with self.assertRaises(ContractError):
                backup_reference(reference, destination, private_root=vault)
            self.assertEqual(
                (destination / "payload.bin").read_bytes(), b"user-owned-change"
            )

    def test_backup_rejects_changed_source_and_leaves_no_partial_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "source"
            source.mkdir()
            (source / "data.bin").write_bytes(b"approved-bytes")
            vault = root / "vault"
            vault.mkdir(mode=0o700)
            reference = {"path": str(source), "state": snapshot(source)}
            (source / "data.bin").write_bytes(b"changed-after-approval")

            with self.assertRaises(ContractError):
                backup_reference(reference, vault / "original", private_root=vault)

            self.assertFalse((vault / "original").exists())
            self.assertEqual(
                (source / "data.bin").read_bytes(), b"changed-after-approval"
            )

    def test_backup_reuses_only_the_same_complete_original_and_keeps_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "source"
            source.mkdir()
            payload = source / "payload.bin"
            payload.write_bytes(b"private-binary\x00\xff")
            moment = 1_700_000_000_000_000_000
            os.utime(payload, ns=(moment, moment))
            if os.name == "posix":
                os.chmod(payload, 0o640)
            vault = root / "vault"
            vault.mkdir(mode=0o700)
            reference = {"path": str(source), "state": snapshot(source)}
            destination = vault / "original"

            first = backup_reference(reference, destination, private_root=vault)
            second = backup_reference(reference, destination, private_root=vault)

            self.assertEqual(first, second)
            self.assertEqual(
                (destination / "payload.bin").read_bytes(), b"private-binary\x00\xff"
            )
            self.assertEqual((destination / "payload.bin").stat().st_mtime_ns, moment)
            if os.name == "posix":
                self.assertEqual(
                    stat.S_IMODE((destination / "payload.bin").stat().st_mode), 0o640
                )

    def test_backup_refuses_conflicting_preexisting_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "source.txt"
            source.write_bytes(b"approved-original")
            vault = root / "vault"
            vault.mkdir(mode=0o700)
            destination = vault / "original.txt"
            destination.write_bytes(b"foreign-content")
            reference = {"path": str(source), "state": snapshot(source)}

            with self.assertRaises(ContractError):
                backup_reference(reference, destination, private_root=vault)

            self.assertEqual(destination.read_bytes(), b"foreign-content")
            self.assertEqual(source.read_bytes(), b"approved-original")

    def test_snapshot_separates_absence_from_links_and_special_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            self.assertEqual(snapshot(root / "missing"), ABSENT)

            (root / "secret.txt").write_bytes(b"secret")
            link = root / "link"
            link.symlink_to(root / "secret.txt")
            with self.assertRaises(ContractError):
                snapshot(link)
            broken = root / "broken"
            broken.symlink_to(root / "missing-target")
            with self.assertRaises(ContractError):
                snapshot(broken)
            with self.assertRaises(ContractError):
                snapshot(root)
            if hasattr(os, "mkfifo"):
                special_root = root / "special"
                special_root.mkdir()
                os.mkfifo(special_root / "pipe")
                with self.assertRaises(ContractError):
                    snapshot(special_root)

    def test_directory_snapshot_returns_complete_entries_with_root_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            tree = root / "legacy"
            (tree / "tasks" / "done").mkdir(parents=True)
            (tree / "tasks" / "done" / "a.json").write_bytes(b"{}")
            (tree / "empty").mkdir()

            state, entries = directory_snapshot(tree)

            self.assertEqual(state, snapshot(tree))
            by_path = {entry["path"]: entry for entry in entries}
            self.assertEqual(
                set(by_path), {"tasks", "tasks/done", "tasks/done/a.json", "empty"}
            )
            for entry in entries:
                self.assertEqual(set(entry), {"path", "type", "checksum"})
            self.assertEqual(
                by_path["empty"],
                {"path": "empty", "type": "directory", "checksum": None},
            )
            self.assertIsNone(by_path["tasks"]["checksum"])
            self.assertEqual(
                by_path["tasks/done/a.json"],
                file_state(b"{}") | {"path": "tasks/done/a.json"},
            )
            paths = [entry["path"] for entry in entries]
            self.assertLess(paths.index("tasks"), paths.index("tasks/done"))
            self.assertLess(paths.index("tasks/done"), paths.index("tasks/done/a.json"))

            absent_state, absent_entries = directory_snapshot(root / "missing")
            self.assertEqual(absent_state, ABSENT)
            self.assertEqual(absent_entries, [])

            (tree / "link").symlink_to(tree / "empty")
            with self.assertRaises(ContractError):
                directory_snapshot(tree)

    def test_write_file_commits_only_against_the_expected_before_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            scope = root / "project"
            scope.mkdir()
            target = scope / "config.json"

            write_file(target, b"v1", ABSENT, scope=scope)
            self.assertEqual(target.read_bytes(), b"v1")
            self.assertEqual(read_file(target, file_state(b"v1")), b"v1")

            with self.assertRaises(ContractError):
                write_file(target, b"v2", ABSENT, scope=scope)
            self.assertEqual(target.read_bytes(), b"v1")

            target.write_bytes(b"user-edit")
            with self.assertRaises(ContractError):
                write_file(target, b"v2", file_state(b"v1"), scope=scope)
            self.assertEqual(target.read_bytes(), b"user-edit")

            write_file(target, b"v2", file_state(b"user-edit"), scope=scope)
            self.assertEqual(target.read_bytes(), b"v2")

            with self.assertRaises(ContractError):
                read_file(target, file_state(b"user-edit"))

    def test_write_file_refuses_paths_outside_the_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            scope = root / "project"
            scope.mkdir()

            with self.assertRaises(ContractError):
                write_file(root / "elsewhere.txt", b"x", ABSENT, scope=scope)
            with self.assertRaises(ContractError):
                write_file(scope / ".." / "escape.txt", b"x", ABSENT, scope=scope)

            self.assertFalse((root / "elsewhere.txt").exists())
            self.assertFalse((root / "escape.txt").exists())

    def test_save_document_is_canonical_atomic_and_immutable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            vault = root / "vault"
            vault.mkdir(mode=0o700)
            document = {"z": [1, 2], "a": {"b": True}}
            receipt = vault / "receipt.json"

            saved = save_document(receipt, document, private_root=vault)

            raw = receipt.read_bytes()
            self.assertEqual(raw, canonical_json_bytes(document))
            self.assertEqual(
                saved,
                {
                    "path": str(receipt),
                    "state": {
                        "type": "file",
                        "checksum": hashlib.sha256(raw).hexdigest(),
                    },
                },
            )

            with self.assertRaises(ContractError):
                save_document(receipt, {"other": True}, private_root=vault)
            self.assertEqual(receipt.read_bytes(), raw)

            with self.assertRaises(ContractError):
                save_document(root / "outside.json", document, private_root=vault)
            self.assertFalse((root / "outside.json").exists())

    @unittest.skipUnless(os.name == "posix", "POSIX privacy semantics")
    def test_private_directory_gateway_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()

            open_dir = root / "open"
            open_dir.mkdir(mode=0o755)
            with self.assertRaises(ContractError):
                require_private_directory(open_dir)

            made = require_private_directory(root / "made", create=True)
            self.assertEqual(stat.S_IMODE(made.stat().st_mode), 0o700)
            require_private_directory(made)

            plain = root / "plain.txt"
            plain.write_bytes(b"x")
            with self.assertRaises(ContractError):
                require_private_directory(plain)

            link = root / "vault-link"
            link.symlink_to(made)
            with self.assertRaises(ContractError):
                require_private_directory(link)

            source = root / "source.txt"
            source.write_bytes(b"private")
            reference = {"path": str(source), "state": snapshot(source)}
            with self.assertRaises(ContractError):
                backup_reference(reference, open_dir / "backup", private_root=open_dir)

    def test_install_reference_places_files_and_directories_honestly(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            candidate = root / "candidate"
            (candidate / "empty").mkdir(parents=True)
            (candidate / "SKILL.md").write_bytes(b"# skill\n")
            scope = root / "project"
            scope.mkdir()

            directory_ref = {"path": str(candidate), "state": snapshot(candidate)}
            target = scope / "skill"
            install_reference(directory_ref, target, ABSENT, scope=scope)
            self.assertTrue((target / "empty").is_dir())
            self.assertEqual((target / "SKILL.md").read_bytes(), b"# skill\n")
            self.assertEqual(snapshot(target), directory_ref["state"])

            install_reference(directory_ref, target, snapshot(target), scope=scope)

            (target / "notes.txt").write_bytes(b"user-notes")
            drifted = snapshot(target)
            with self.assertRaises(ContractError):
                install_reference(directory_ref, target, drifted, scope=scope)
            self.assertEqual((target / "notes.txt").read_bytes(), b"user-notes")
            self.assertEqual((target / "SKILL.md").read_bytes(), b"# skill\n")

            file_ref = {
                "path": str(candidate / "SKILL.md"),
                "state": snapshot(candidate / "SKILL.md"),
            }
            document = scope / "DOC.md"
            install_reference(file_ref, document, ABSENT, scope=scope)
            self.assertEqual(document.read_bytes(), b"# skill\n")

            with self.assertRaises(ContractError):
                install_reference(file_ref, document, ABSENT, scope=scope)
            self.assertEqual(document.read_bytes(), b"# skill\n")

            changed_ref = {"path": str(candidate), "state": snapshot(candidate)}
            (candidate / "SKILL.md").write_bytes(b"# changed\n")
            with self.assertRaises(ContractError):
                install_reference(changed_ref, scope / "other", ABSENT, scope=scope)
            self.assertFalse((scope / "other").exists())

    def test_install_reference_replaces_a_directory_only_behind_a_verified_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            candidate = root / "candidate"
            candidate.mkdir()
            (candidate / "new.txt").write_bytes(b"new")
            source_ref = {"path": str(candidate), "state": snapshot(candidate)}
            scope = root / "project"
            scope.mkdir()
            target = scope / "skill"
            target.mkdir()
            (target / "old.txt").write_bytes(b"old")
            before = snapshot(target)
            vault = root / "vault"
            vault.mkdir(mode=0o700)
            backup = backup_reference(
                {"path": str(target), "state": before},
                vault / "original",
                private_root=vault,
            )

            with self.assertRaises(ContractError):
                install_reference(source_ref, target, before, scope=scope)
            self.assertEqual((target / "old.txt").read_bytes(), b"old")

            with self.assertRaises(ContractError):
                install_reference(
                    source_ref,
                    target,
                    before,
                    scope=scope,
                    backup_ref={
                        "path": str(vault / "original"),
                        "state": source_ref["state"],
                    },
                )
            self.assertEqual((target / "old.txt").read_bytes(), b"old")

            tampered = backup_reference(
                {"path": str(target), "state": before},
                vault / "second",
                private_root=vault,
            )
            (vault / "second" / "old.txt").write_bytes(b"tampered")
            with self.assertRaises(ContractError):
                install_reference(
                    source_ref, target, before, scope=scope, backup_ref=tampered
                )
            self.assertEqual((target / "old.txt").read_bytes(), b"old")

            if os.name == "posix":
                loose = root / "loose"
                loose.mkdir(mode=0o755)
                shutil.copytree(vault / "original", loose / "copy")
                with self.assertRaises(ContractError):
                    install_reference(
                        source_ref,
                        target,
                        before,
                        scope=scope,
                        backup_ref={"path": str(loose / "copy"), "state": before},
                    )
                self.assertEqual((target / "old.txt").read_bytes(), b"old")

            install_reference(
                source_ref, target, before, scope=scope, backup_ref=backup
            )

            self.assertEqual((target / "new.txt").read_bytes(), b"new")
            self.assertFalse((target / "old.txt").exists())
            self.assertEqual(snapshot(target), source_ref["state"])
            self.assertEqual((vault / "original" / "old.txt").read_bytes(), b"old")
            leftovers = [
                entry.name for entry in scope.iterdir() if entry.name != "skill"
            ]
            self.assertEqual(leftovers, [])

    @unittest.skipUnless(os.name == "nt", "Windows ACL privacy semantics")
    def test_windows_private_directory_acl_gateway(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            made = require_private_directory(root / "made", create=True)
            self.assertTrue(made.is_dir())
            require_private_directory(made)

            source = root / "source.txt"
            source.write_bytes(b"private")
            reference = {"path": str(source), "state": snapshot(source)}
            saved = backup_reference(reference, made / "backup.txt", private_root=made)
            self.assertEqual((made / "backup.txt").read_bytes(), b"private")
            self.assertEqual(saved["state"], snapshot(made / "backup.txt"))


if __name__ == "__main__":
    unittest.main()
