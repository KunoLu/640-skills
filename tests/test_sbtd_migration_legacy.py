from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from onboard_contracts import ContractError
from sbtd_migration_legacy import (
    read_legacy_identity,
    validate_projection_graph,
    validate_task_projection,
)

SOURCE_PATH = ".trellis/tasks/09-01-alpha/task.json"
DONE_EVENT = {
    "at": "unknown",
    "from": "unknown",
    "to": "done",
    "reason": "legacy completion fact",
    "evidence": "legacy task.json status",
}


def _json_bytes(value):
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def _legacy_source(**overrides):
    base = {
        "id": "alpha",
        "name": "alpha",
        "title": "Alpha task",
        "description": "legacy description",
        "status": "planning",
        "createdAt": "2026-09-01",
        "completedAt": None,
        "branch": None,
        "base_branch": "main",
        "parent": None,
        "children": [],
        "subtasks": [],
        "meta": {"votes": 3, "score": 1.5, "flag": True},
        "custom_unknown": {"nested": ["x", 2]},
    }
    base.update(overrides)
    return base


def _task_md(
    *,
    identity="alpha",
    status="planned",
    parent=None,
    branch=None,
    created_at=None,
    updated_at=None,
    completed_at=None,
    workflow_mode=None,
    mode_source="migration-unknown",
    extra=(),
    events=(),
):
    fields = [
        ("schema_version", 1),
        ("id", identity),
        ("workflow_mode", workflow_mode),
        ("mode_source", mode_source),
        ("mode_note", "legacy Trellis task without mode proof"),
        ("status", status),
        ("branch", branch),
        ("created_at", created_at),
        ("updated_at", updated_at),
        ("completed_at", completed_at),
    ]
    if parent is not None:
        fields.append(("parent", parent))
    fields.extend(extra)
    lines = ["---"]
    lines.extend(
        key + ": " + json.dumps(value, ensure_ascii=False) for key, value in fields
    )
    lines.append("---")
    lines.append("")
    lines.append("# task " + identity)
    lines.append("")
    if events:
        lines.append("## 状态事件")
        lines.append("")
        lines.append("| at | from | to | reason | evidence |")
        lines.append("|---|---|---|---|---|")
        for event in events:
            lines.append(
                "| {at} | {from} | {to} | {reason} | {evidence} |".format(**event)
            )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _sidecar(
    source_raw,
    *,
    original="auto",
    source_path=SOURCE_PATH,
    sha="auto",
    redacted=(),
    parse_status="valid",
):
    if original == "auto":
        original = json.loads(source_raw.decode("utf-8"))
    if sha == "auto":
        sha = hashlib.sha256(source_raw).hexdigest()
    return _json_bytes(
        {
            "schema_version": 1,
            "source_path": source_path,
            "source_sha256": sha,
            "original": original,
            "redacted_paths": list(redacted),
            "parse_status": parse_status,
        }
    )


def _projection(
    source=None,
    *,
    source_path=SOURCE_PATH,
    decision="share",
    task_raw=None,
    sidecar_raw=None,
):
    source = _legacy_source() if source is None else source
    source_raw = _json_bytes(source)
    if task_raw is None:
        task_raw = _task_md()
    if sidecar_raw is None:
        sidecar_raw = _sidecar(source_raw, source_path=source_path)
    return validate_task_projection(
        source_raw, task_raw, sidecar_raw, source_path=source_path, decision=decision
    )


def _done_projection(source_path, **source_overrides):
    source = _legacy_source(
        status="completed", completedAt="2026-09-05", **source_overrides
    )
    return _projection(
        source,
        source_path=source_path,
        task_raw=_task_md(identity=source["id"], status="done", events=[DONE_EVENT]),
    )


class LegacyIdentityTests(unittest.TestCase):
    def test_pinned_metadata_is_not_a_second_name_or_normalization_permission(self):
        raw = b"name=dev01\ninitialized_at=2026-09-01T12:00:00\n"
        self.assertEqual(read_legacy_identity(raw), "dev01")
        for invalid in (
            b"name=dev01\nname=dev01\n",
            b"name=Alice\ninitialized_at=2026-09-01T12:00:00\n",
            b"name=dev_01\ninitialized_at=2026-09-01T12:00:00\n",
        ):
            with self.subTest(raw=invalid), self.assertRaises(ContractError):
                read_legacy_identity(invalid)

    def test_unparseable_or_missing_identity_facts_are_rejected(self):
        self.assertEqual(read_legacy_identity(b"name=dev01\n"), "dev01")
        for invalid in (
            b"initialized_at=2026-09-01T12:00:00\n",
            b"name=dev01\ninitialized_at=one\ninitialized_at=two\n",
            b"name=dev01\nnot-a-declaration\n",
            b"name = dev01\n",
            b"\xff\xfe",
        ):
            with self.subTest(raw=invalid), self.assertRaises(ContractError):
                read_legacy_identity(invalid)


class TaskProjectionTests(unittest.TestCase):
    def test_high_precision_json_cannot_be_rounded_in_the_shared_snapshot(self):
        source_raw = _json_bytes(_legacy_source()).replace(
            b'"score": 1.5', b'"score": 1.0000000000000001'
        )
        rounded = _sidecar(source_raw)
        with self.assertRaises(ContractError):
            validate_task_projection(
                source_raw,
                _task_md(),
                rounded,
                source_path=SOURCE_PATH,
                decision="share",
            )
        exact = rounded.replace(b'"score": 1.0', b'"score": 1.0000000000000001')
        validate_task_projection(
            source_raw, _task_md(), exact, source_path=SOURCE_PATH, decision="share"
        )

    def test_share_projection_preserves_identity_mode_time_and_unknown_fields(self):
        projection = _projection()
        self.assertEqual(projection.legacy_id, "alpha")
        self.assertIsNone(projection.parent)
        self.assertEqual(projection.children, ())
        self.assertEqual(projection.aliases, ("09-01-alpha",))
        frontmatter = projection.document.frontmatter
        self.assertEqual(frontmatter["status"], "planned")
        self.assertIsNone(frontmatter["workflow_mode"])
        self.assertEqual(frontmatter["mode_source"], "migration-unknown")
        self.assertIsNone(frontmatter["created_at"])
        self.assertIsNone(frontmatter["updated_at"])
        self.assertIsNone(frontmatter["completed_at"])
        self.assertEqual(projection.document.events, ())

    def test_done_task_with_date_only_completion_records_unknown_history(self):
        projection = _done_projection(SOURCE_PATH)
        frontmatter = projection.document.frontmatter
        self.assertEqual(frontmatter["status"], "done")
        self.assertIsNone(frontmatter["completed_at"])
        self.assertEqual(len(projection.document.events), 1)
        self.assertEqual(projection.document.events[0]["at"], "unknown")

    def test_full_timezone_timestamps_are_preserved_not_fabricated(self):
        source = _legacy_source(
            status="completed",
            createdAt="2026-09-01T12:00:00Z",
            completedAt="2026-09-05T10:00:00+08:00",
        )
        event = dict(DONE_EVENT, at="2026-09-05T10:00:00+08:00")
        projection = _projection(
            source,
            task_raw=_task_md(
                status="done",
                created_at="2026-09-01T12:00:00Z",
                completed_at="2026-09-05T10:00:00+08:00",
                events=[event],
            ),
        )
        frontmatter = projection.document.frontmatter
        self.assertEqual(frontmatter["created_at"], "2026-09-01T12:00:00Z")
        self.assertEqual(frontmatter["completed_at"], "2026-09-05T10:00:00+08:00")

    def test_redact_decision_keeps_private_truth_but_hides_raw_hash(self):
        source = _legacy_source(meta={"token": "s3cr3t", "votes": 3})
        source_raw = _json_bytes(source)
        original = json.loads(source_raw.decode("utf-8"))
        original["meta"]["token"] = None
        projection = _projection(
            source,
            decision="redact",
            sidecar_raw=_sidecar(
                source_raw, original=original, sha=None, redacted=["/meta/token"]
            ),
        )
        self.assertEqual(projection.legacy_id, "alpha")
        root_private = _projection(
            source,
            decision="redact",
            sidecar_raw=_sidecar(source_raw, original=None, sha=None, redacted=[""]),
        )
        self.assertEqual(root_private.legacy_id, "alpha")

    def test_invalid_source_never_becomes_a_normal_task(self):
        task_raw = _task_md()
        duplicate = b'{"id": "alpha", "id": "alpha", "status": "planning"}'
        non_finite = b'{"id": "alpha", "status": "planning", "meta": NaN}'
        broken = b'{"id": "alpha", '
        for source_raw in (duplicate, non_finite, broken):
            sidecar_raw = _sidecar(
                b"{}", original=None, sha=None, redacted=[""], parse_status="invalid"
            )
            with self.subTest(source_raw=source_raw), self.assertRaises(ContractError):
                validate_task_projection(
                    source_raw,
                    task_raw,
                    sidecar_raw,
                    source_path=SOURCE_PATH,
                    decision="redact",
                )
        source_raw = _json_bytes(_legacy_source())
        dishonest = _sidecar(
            source_raw, original=None, sha=None, redacted=[""], parse_status="invalid"
        )
        with self.assertRaises(ContractError):
            validate_task_projection(
                source_raw,
                task_raw,
                dishonest,
                source_path=SOURCE_PATH,
                decision="redact",
            )

    def test_unmapped_status_and_archive_position_alone_never_prove_done(self):
        for status in ("archived", "mystery"):
            with self.subTest(status=status), self.assertRaises(ContractError):
                _projection(_legacy_source(status=status))
        archived_path = ".trellis/tasks/archive/2026-09/09-01-alpha/task.json"
        with self.assertRaises(ContractError):
            _projection(_legacy_source(), source_path=archived_path)
        projection = _done_projection(archived_path)
        self.assertEqual(projection.document.frontmatter["status"], "done")
        self.assertEqual(projection.aliases, ("09-01-alpha",))

    def test_unfinished_task_with_completion_facts_is_rejected(self):
        with self.assertRaises(ContractError):
            _projection(_legacy_source(completedAt="2026-09-05"))
        with self.assertRaises(ContractError):
            _projection(task_raw=_task_md(events=[DONE_EVENT]))

    def test_done_task_requires_truthful_completion_event(self):
        source = _legacy_source(status="completed", completedAt="2026-09-05")
        with self.assertRaises(ContractError):
            _projection(source, task_raw=_task_md(status="done"))
        fabricated = dict(DONE_EVENT, at="2026-09-05T00:00:00Z")
        with self.assertRaises(ContractError):
            _projection(source, task_raw=_task_md(status="done", events=[fabricated]))
        wrong_from = dict(DONE_EVENT, **{"from": "planned"})
        with self.assertRaises(ContractError):
            _projection(source, task_raw=_task_md(status="done", events=[wrong_from]))

    def test_unknown_time_semantics_are_rejected(self):
        for created in ("2026-09-01T12:00:00", "2026-02-30", 20260901):
            with self.subTest(createdAt=created), self.assertRaises(ContractError):
                _projection(_legacy_source(createdAt=created))
        with self.assertRaises(ContractError):
            _projection(task_raw=_task_md(created_at="2026-09-01T00:00:00Z"))

    def test_unprovable_mode_and_update_time_stay_empty(self):
        with self.assertRaises(ContractError):
            _projection(task_raw=_task_md(workflow_mode="strict", mode_source="user"))
        with self.assertRaises(ContractError):
            _projection(task_raw=_task_md(updated_at="2026-09-01T12:00:00Z"))

    def test_ambiguous_identity_and_inferred_parent_are_rejected(self):
        with self.assertRaises(ContractError):
            _projection(_legacy_source(name="alpha-renamed"))
        with self.assertRaises(ContractError):
            _projection(task_raw=_task_md(parent="beta"))
        with self.assertRaises(ContractError):
            _projection(_legacy_source(parent=5))
        with self.assertRaises(ContractError):
            _projection(_legacy_source(children="09-02-beta"))

    def test_frontmatter_must_not_absorb_legacy_field_spellings(self):
        with self.assertRaises(ContractError):
            _projection(task_raw=_task_md(extra=(("meta", {"x": 1}),)))
        with self.assertRaises(ContractError):
            _projection(task_raw=_task_md(extra=(("createdAt", "2026-09-01"),)))

    def test_shared_snapshot_must_preserve_unknown_fields_and_types(self):
        source_raw = _json_bytes(_legacy_source())
        lossy_unknown = json.loads(source_raw.decode("utf-8"))
        del lossy_unknown["custom_unknown"]
        type_changed = json.loads(source_raw.decode("utf-8"))
        type_changed["meta"]["votes"] = 3.0
        bool_changed = json.loads(source_raw.decode("utf-8"))
        bool_changed["meta"]["flag"] = 1
        extra_key = json.loads(source_raw.decode("utf-8"))
        extra_key["invented"] = None
        for original in (lossy_unknown, type_changed, bool_changed, extra_key):
            with self.subTest(original=original), self.assertRaises(ContractError):
                _projection(sidecar_raw=_sidecar(source_raw, original=original))

    def test_hash_visibility_follows_full_shareability(self):
        source_raw = _json_bytes(_legacy_source())
        with self.assertRaises(ContractError):
            _projection(sidecar_raw=_sidecar(source_raw, sha="0" * 64))
        with self.assertRaises(ContractError):
            _projection(sidecar_raw=_sidecar(source_raw, sha=None))
        private_path = _projection(
            sidecar_raw=_sidecar(source_raw, source_path=None, sha=None)
        )
        self.assertEqual(private_path.legacy_id, "alpha")
        with self.assertRaises(ContractError):
            _projection(
                sidecar_raw=_sidecar(
                    source_raw,
                    source_path=None,
                    sha=hashlib.sha256(source_raw).hexdigest(),
                )
            )
        with self.assertRaises(ContractError):
            _projection(
                decision="redact",
                sidecar_raw=_sidecar(
                    source_raw, sha=hashlib.sha256(source_raw).hexdigest()
                ),
            )
        with self.assertRaises(ContractError):
            _projection(sidecar_raw=_sidecar(source_raw, redacted=["/meta"]))

    def test_redaction_form_is_exact(self):
        source_raw = _json_bytes(_legacy_source())
        exact = json.loads(source_raw.decode("utf-8"))
        exact["meta"]["score"] = None
        not_nulled = json.loads(source_raw.decode("utf-8"))
        for redacted, original in (
            (["/meta/nope"], exact),
            (["/meta", "/meta/score"], exact),
            (["/meta/score", "/meta/score"], exact),
            (["/custom_unknown/nested/9"], exact),
            (["/meta/score"], not_nulled),
            (["/meta/score"], None),
            ([""], exact),
        ):
            with self.subTest(redacted=redacted), self.assertRaises(ContractError):
                _projection(
                    decision="redact",
                    sidecar_raw=_sidecar(
                        source_raw, original=original, sha=None, redacted=redacted
                    ),
                )

    def test_sidecar_shape_and_source_binding(self):
        source_raw = _json_bytes(_legacy_source())
        sidecar = json.loads(_sidecar(source_raw).decode("utf-8"))
        for mutate in (
            lambda value: value.update(extra=1),
            lambda value: value.pop("original"),
            lambda value: value.update(schema_version="1"),
            lambda value: value.update(source_sha256="ABCDEF" + "0" * 58),
        ):
            candidate = copy.deepcopy(sidecar)
            mutate(candidate)
            with (
                self.subTest(candidate=sorted(candidate)),
                self.assertRaises(ContractError),
            ):
                _projection(sidecar_raw=_json_bytes(candidate))
        with self.assertRaises(ContractError):
            _projection(
                sidecar_raw=_sidecar(
                    source_raw, source_path=".trellis/tasks/09-01-other/task.json"
                )
            )


def _beta_projection(children=("09-01-alpha",), parent=None, parent_id=None):
    source = _legacy_source(
        id="beta", name="beta", children=list(children), parent=parent
    )
    path = ".trellis/tasks/08-15-beta/task.json"
    raw = _json_bytes(source)
    document = _task_md(identity="beta", parent=parent_id)
    return validate_task_projection(
        raw,
        document,
        _sidecar(raw, source_path=path),
        source_path=path,
        decision="share",
    )


def _alpha_projection(parent=None, parent_id=None, children=()):
    source = _legacy_source(parent=parent, children=list(children))
    raw = _json_bytes(source)
    document = _task_md(parent=parent_id)
    return validate_task_projection(
        raw,
        document,
        _sidecar(raw, source_path=SOURCE_PATH),
        source_path=SOURCE_PATH,
        decision="share",
    )


class ProjectionGraphTests(unittest.TestCase):
    def test_parent_child_graph_resolves_through_real_legacy_names(self):
        alpha = _alpha_projection(parent="08-15-beta", parent_id="beta")
        beta = _beta_projection()
        validate_projection_graph({"alpha": alpha, "beta": beta})

    def test_missing_parent_and_half_links_are_rejected(self):
        alpha = _alpha_projection(parent="09-99-ghost", parent_id="ghost")
        with self.assertRaises(ContractError):
            validate_projection_graph({"alpha": alpha})
        child_without_link = _alpha_projection(parent="08-15-beta", parent_id="beta")
        with self.assertRaises(ContractError):
            validate_projection_graph(
                {"alpha": child_without_link, "beta": _beta_projection(children=())}
            )
        with self.assertRaises(ContractError):
            validate_projection_graph(
                {"alpha": _alpha_projection(), "beta": _beta_projection()}
            )
        mismatched_document = _alpha_projection(parent="08-15-beta", parent_id="gamma")
        with self.assertRaises(ContractError):
            validate_projection_graph(
                {"alpha": mismatched_document, "beta": _beta_projection()}
            )

    def test_relationship_cycles_are_rejected(self):
        alpha = _alpha_projection(
            parent="08-15-beta", parent_id="beta", children=("08-15-beta",)
        )
        beta = _beta_projection(
            children=("09-01-alpha",), parent="09-01-alpha", parent_id="alpha"
        )
        with self.assertRaises(ContractError):
            validate_projection_graph({"alpha": alpha, "beta": beta})

    def test_duplicate_names_and_mapping_mismatch_are_rejected(self):
        alpha = _alpha_projection()
        archived_twin = _done_projection(
            ".trellis/tasks/archive/2026-08/09-01-alpha/task.json",
            id="alpha-old",
            name="alpha-old",
        )
        with self.assertRaises(ContractError):
            validate_projection_graph({"alpha": alpha, "alpha-old": archived_twin})
        with self.assertRaises(ContractError):
            validate_projection_graph({"other": alpha})


if __name__ == "__main__":
    unittest.main()
