"""Read-only project smoke for a fresh migration deployment.

The child is the installed ``scripts/onboard.py`` ``check-projects`` probe.
It is not Graft, not a host event, and not a business API pass. The sealed
record stores only a closed projection, never raw probe text or a project-tree
snapshot. Caller checks sealed deployment targets.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess

import tempfile
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import onboard_contracts as contracts
from onboard_contracts import ContractError, canonical_json_bytes
from sbtd_migration_verify import (
    ONBOARD_CLI_BOOTSTRAP,
    ONBOARD_CLI_SMOKE_SCHEMA,
    onboard_cli_smoke_command,
)

_DEADLINE_SECONDS = 120
_ABSENT = {"type": "absent", "checksum": None}
_KEEP_ENV = frozenset(
    {
        "PATH",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "SYSTEMROOT",
        "WINDIR",
        "TMPDIR",
        "TMP",
        "TEMP",
    }
)
_DOCUMENT_KEYS = frozenset(
    {
        "schema",
        "projectRoot",
        "sourceRef",
        "sourceCommit",
        "startedAt",
        "finishedAt",
        "command",
        "exitCode",
        "status",
        "mockStrategy",
        "onboardVersion",
        "projection",
        "projectionSha256",
    }
)


def _fail(code: str, message: str, exit_code: int = 2) -> None:
    raise ContractError(code, message, exit_code=exit_code)


def _safe_directory(path: Path, label: str) -> Path:
    if not path.is_absolute() or path != path.resolve():
        _fail("unsafe-path", f"{label} must be an absolute canonical path")
    if path.is_symlink() or not path.is_dir():
        _fail("unsafe-path", f"{label} must be a real directory")
    if path == Path(path.anchor):
        _fail("unsafe-path", f"{label} must not be a filesystem root")
    return path


def _source_identity(root: Path) -> tuple[str, str | None]:
    from sbtd_migration import _project_revision

    branch, head = _project_revision(root)
    if head is None:
        return "non-git", None
    if branch is None:
        return "HEAD", head
    if not isinstance(branch, str) or any(character in branch for character in "\r\n\x00"):
        _fail("unknown-revision", "the selected project's branch name is not a closed label")
    return branch, head


def _child_environment(home: Path) -> dict[str, str]:
    environment = {
        key: value for key, value in os.environ.items() if key in _KEEP_ENV
    }
    environment.update(
        HOME=str(home),
        USERPROFILE=str(home),
        XDG_CONFIG_HOME=str(home / "config"),
        XDG_CACHE_HOME=str(home / "cache"),
        XDG_DATA_HOME=str(home / "data"),
        DO_NOT_TRACK="1",
        DNT="1",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONNOUSERSITE="1",
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
        LC_ALL=environment.get("LC_ALL", "C.UTF-8"),
    )
    return environment


def _installed_runtime_versions() -> dict[str, str]:
    from sbtd_migration import runtime_versions

    versions = runtime_versions()
    version = versions.get("onboard")
    if not isinstance(version, str) or not version.startswith("runtime-sha256:"):
        _fail("runtime-unavailable", "the installed Onboard version is not sealed")
    return versions


def _closed_projection(raw: str, root: Path) -> dict[str, Any]:
    try:
        document = json.loads(raw)
    except (json.JSONDecodeError, RecursionError, UnicodeError):
        _fail("invalid-document", "check-projects did not return one JSON object")
    projects = document.get("projects") if isinstance(document, dict) else None
    item = projects[0] if isinstance(projects, list) and len(projects) == 1 else None
    sbtd = item.get("sbtd") if isinstance(item, dict) else None
    projected = {
        "mode": "check-projects",
        "projects": [
            {
                "projectRoot": item.get("projectRoot") if isinstance(item, dict) else None,
                "sbtd": {"status": sbtd.get("status") if isinstance(sbtd, dict) else None},
            }
        ],
    }
    project = projected["projects"][0]
    if (
        not isinstance(document, dict)
        or document.get("mode") != "check-projects"
        or project["projectRoot"] != str(root)
        or not isinstance(project["sbtd"]["status"], str)
    ):
        _fail("scope-conflict", "check-projects did not return this exact project")
    return projected


def _require_canonical_input(
    kind: str, document: Mapping[str, Any], raw: bytes
) -> None:
    if raw != canonical_json_bytes(document):
        _fail("invalid-document", f"migration {kind} is not canonical JSON")


def _bound_document(path: Path, kind: str) -> tuple[Path, dict[str, Any], bytes]:
    from sbtd_migration import _private_document
    from sbtd_migration_files import read_file, require_private_directory

    candidate = Path(path)
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        _fail("unsafe-path", f"migration {kind} must be an existing canonical file")
    if (
        not candidate.is_absolute()
        or candidate != resolved
        or candidate.is_symlink()
        or not candidate.is_file()
    ):
        _fail("unsafe-path", f"migration {kind} must be an existing canonical file")
    require_private_directory(candidate.parent)
    document, raw = _private_document(candidate, kind)
    _require_canonical_input(kind, document, raw)
    if read_file(candidate) != raw:
        _fail("state-conflict", f"migration {kind} changed while being read")
    return candidate, document, raw


def _predecessor_project(
    manifest: Mapping[str, Any], previous: Mapping[str, Any], root: Path
) -> Mapping[str, Any]:
    payload = manifest["payload"]
    previous_payload = previous["payload"]
    if sorted(project["root"] for project in payload["projects"]) != sorted(
        project["root"] for project in previous_payload["projects"]
    ) or any(payload[field] != previous_payload[field] for field in ("backup_root", "custodian", "retention")):
        _fail("lineage-conflict", "the migration predecessor changed the authorized batch")
    matches = [project for project in previous_payload["projects"] if project["root"] == str(root)]
    if len(matches) != 1:
        _fail("scope-conflict", "the predecessor does not bind this exact project root")
    return matches[0]


def _bound_smoke_context(
    root: Path, manifest_path: Path, apply_path: Path, *, current: Mapping[str, str]
) -> tuple[dict[str, Any] | None, str, str, bytes, bytes]:
    """Prove the retained tree for this fresh probe, not for historical report reads."""
    import sbtd_migration as migration
    from sbtd_deployment import reject_legacy_execution
    from sbtd_migration_files import read_file, require_private_directory, snapshot
    from sbtd_migration_plan import (
        _check_cleanup_operation,
        _validate_successor_project_operations,
        _verify_followup_predecessor,
        _verify_successor_predecessor,
    )

    selected = _safe_directory(Path(root), "project root")
    manifest_path, manifest, manifest_raw = _bound_document(manifest_path, "manifest")
    apply_path, applied, apply_raw = _bound_document(apply_path, "apply_receipt")
    contracts.validate_declared_bindings(
        manifest,
        {"apply_receipt": applied},
        {"manifest": manifest_raw, "apply_receipt": apply_raw},
    )
    contracts._bind_success_gate(applied, {"applied", "already-complete"})
    payload = manifest["payload"]
    declaration = payload["deployment"]
    if (
        declaration is None
        or declaration["mode"] not in {"init", "init-projects"}
        or declaration["platform"] not in {"codex", "omp"}
    ):
        _fail("missing-deployment-plan", "bound smoke requires an executable deployment declaration")
    reject_legacy_execution(payload)
    sealed = payload["tool_versions"]
    if sealed != current:
        predecessor, successor = migration._verified_runtime_pair()
        if (
            sealed.get("graft") != current.get("graft")
            or sealed.get("onboard") != predecessor
            or current.get("onboard") != successor
        ):
            _fail("version-conflict", "the migration plan belongs to a different installed implementation")
    migration._check_evidence_apply_boundary(manifest_path, manifest)
    require_private_directory(Path(payload["backup_root"]))
    migration._check_source_backups(manifest)
    migration._check_stage_backups({"apply": migration._result_index(applied)})
    projects = [project for project in payload["projects"] if project["root"] == str(selected)]
    if len(projects) != 1:
        _fail("scope-conflict", "the manifest does not bind this exact project root")
    project = projects[0]
    if migration._project_revision(selected) != (project["source_ref"], project["head"]):
        _fail("revision-conflict", "the selected project revision changed after planning")
    tree = selected / ".trellis"
    followup = payload.get("followup")
    successor = payload.get("successor")
    if followup is not None:
        if declaration["mode"] != "init" or declaration["platform"] != "omp":
            _fail("followup-conflict", "a followup smoke requires its sealed OMP deployment")
        (
            previous_manifest,
            _previous_apply,
            _previous_deployment,
            _previous_verification,
            previous_cleanup,
            _ancestors,
        ) = _verify_followup_predecessor(manifest)
        previous = _predecessor_project(manifest, previous_manifest, selected)
        if (
            project["sources"]
            or project["platforms"] != previous["platforms"]
            or project.get("agents_no_touch") != previous.get("agents_no_touch")
            or payload["publication_decisions"] != {"schema_version": 1, "items": []}
            or payload["routing_approvals"] is not None
            or any(
                operation["phase"] != "deploy"
                for item in payload["projects"]
                for operation in item["private_operations"]
            )
            or any(operation["phase"] != "deploy" for operation in payload["shared_operations"])
        ):
            _fail("followup-conflict", "the followup changed its inherited project scope")
        cleanup = [operation for operation in previous["private_operations"] if operation["phase"] == "cleanup"]
        if (
            len(cleanup) != 1
            or len(previous["sources"]) != 1
            or Path(previous["sources"][0]["path"]) != tree
            or previous["sources"][0]["state"]["type"] != "directory"
        ):
            _fail("followup-conflict", "the predecessor lacks exact retained-tree cleanup ownership")
        _check_cleanup_operation(selected, cleanup[0], previous["sources"][0])
        outcome = migration._result_index(previous_cleanup).get(cleanup[0]["resource_id"])
        if (
            outcome is None
            or outcome["status"] != "succeeded"
            or outcome["after"] != _ABSENT
            or snapshot(tree) != _ABSENT
        ):
            _fail("state-conflict", "the confirmed predecessor cleanup no longer proves legitimate absence")
        state = None
    else:
        if successor is not None:
            previous_manifest, previous_apply = _verify_successor_predecessor(manifest)
            previous = _predecessor_project(manifest, previous_manifest, selected)
            if (
                project["sources"] != previous["sources"]
                or project["platforms"] != previous["platforms"]
                or project.get("agents_no_touch") != previous.get("agents_no_touch")
            ):
                _fail("lineage-conflict", "the successor changed its inherited project scope")
            _validate_successor_project_operations(selected, project)
            if [operation for operation in project["private_operations"] if operation["phase"] == "cleanup"] != [
                operation for operation in previous["private_operations"] if operation["phase"] == "cleanup"
            ]:
                _fail("lineage-conflict", "the successor changed retained-tree cleanup ownership")
            migration._check_source_backups(previous_manifest)
            migration._check_stage_backups({"apply": migration._result_index(previous_apply)})
        cleanup = [operation for operation in project["private_operations"] if operation["phase"] == "cleanup"]
        if len(cleanup) != 1 or len(project["sources"]) != 1:
            _fail("ownership-conflict", "the manifest lacks exact retained-tree cleanup ownership")
        source = project["sources"][0]
        if Path(source["path"]) != tree or source["state"]["type"] != "directory":
            _fail("ownership-conflict", "the retained tree is not the sealed legacy source")
        _check_cleanup_operation(selected, cleanup[0], source)
        state = snapshot(tree)
        if state["type"] != "directory" or state != source["state"]:
            _fail("state-conflict", "the retained tree is missing or differs from its sealed state")
    if read_file(manifest_path) != manifest_raw or read_file(apply_path) != apply_raw:
        _fail("state-conflict", "migration evidence changed during bound smoke validation")
    if snapshot(tree) != (state if state is not None else _ABSENT):
        _fail("state-conflict", "the retained tree changed during bound smoke validation")
    return state, manifest["manifest_id"], applied["apply_id"], manifest_raw, apply_raw


def bound_retained_tree(root: Path, manifest_path: Path, apply_path: Path) -> dict[str, Any] | None:
    """Return the proven retained tree state, or None after proven followup cleanup."""
    return _bound_smoke_context(
        root, manifest_path, apply_path, current=_installed_runtime_versions()
    )[0]


def run_project_smoke(
    root: Path,
    evidence_dir: Path,
    *,
    context_paths: tuple[Path, Path] | None = None,
) -> list[dict[str, Any]]:
    """Run trusted check-projects and seal the closed projection. Raise on failure."""
    from sbtd_migration_files import require_private_directory, save_document, snapshot, write_file

    selected = _safe_directory(Path(root), "project root")
    home = Path(os.environ.get("HOME") or os.environ.get("USERPROFILE") or Path.home()).resolve()
    if selected == home:
        _fail("unsafe-path", "project root must not be HOME")
    vault = require_private_directory(_safe_directory(Path(evidence_dir), "evidence directory"))
    if selected == vault or selected.is_relative_to(vault) or vault.is_relative_to(selected):
        _fail("scope-conflict", "evidence directory must not overlap the project root")
    versions = _installed_runtime_versions()
    bound = (
        _bound_smoke_context(selected, *context_paths, current=versions)
        if context_paths is not None
        else None
    )
    source_ref, source_commit = _source_identity(selected)
    identity = versions["onboard"]
    started = datetime.now(timezone.utc)
    command = onboard_cli_smoke_command(selected, context_paths=context_paths)
    if len(command) < 5 or command[4] != ONBOARD_CLI_BOOTSTRAP:
        _fail("runtime-unavailable", "the installed check-projects command is not the sealed bootstrap")
    timed_out = False
    completed = None
    try:
        with tempfile.TemporaryDirectory(prefix="sbtd-smoke-home-") as raw_home:
            child_home = Path(raw_home)
            os.chmod(child_home, 0o700)
            completed = subprocess.run(
                command,
                cwd=Path(command[5]).parent,
                env=_child_environment(child_home),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="strict",
                timeout=_DEADLINE_SECONDS,
                check=False,
            )
    except subprocess.TimeoutExpired:
        timed_out = True
    except (OSError, UnicodeError, ValueError, IndexError):
        _fail("native-operation-failed", "check-projects could not be started", 5)
    if timed_out or completed is None:
        _fail("native-operation-failed", "check-projects did not finish before the deadline", 5)
    if _installed_runtime_versions() != versions:
        _fail("state-conflict", "the installed Onboard version changed during check-projects", 5)
    if bound is not None and context_paths is not None:
        from sbtd_migration_files import read_file

        expected_state, _manifest_id, _apply_id, manifest_raw, apply_raw = bound
        if read_file(context_paths[0]) != manifest_raw or read_file(context_paths[1]) != apply_raw:
            _fail("state-conflict", "migration evidence changed during check-projects", 5)
        if snapshot(selected / ".trellis") != (expected_state if expected_state is not None else _ABSENT):
            _fail("state-conflict", "the retained tree changed during check-projects", 5)
    if completed.returncode != 0:
        _fail("state-conflict", "check-projects did not exit cleanly", 5)
    raw = completed.stdout
    if not isinstance(raw, str):
        _fail("invalid-document", "check-projects stdout is not text")
    projection = _closed_projection(raw, selected)
    del raw
    if projection["projects"][0]["sbtd"]["status"] != "success":
        _fail(
            "state-conflict",
            "check-projects sbtd.status is not success; exit 0 or a plan is not enough",
            5,
        )
    finished = datetime.now(timezone.utc)
    if finished < started:
        _fail("state-conflict", "the smoke clock moved backwards")
    document = {
        "schema": ONBOARD_CLI_SMOKE_SCHEMA,
        "projectRoot": str(selected),
        "sourceRef": source_ref,
        "sourceCommit": source_commit,
        "startedAt": started.isoformat(),
        "finishedAt": finished.isoformat(),
        "command": command,
        "exitCode": completed.returncode,
        "status": "passed",
        "mockStrategy": "none",
        "onboardVersion": identity,
        "projection": projection,
        "projectionSha256": hashlib.sha256(canonical_json_bytes(projection)).hexdigest(),
    }
    expected_keys = _DOCUMENT_KEYS
    if bound is not None:
        document["manifestId"] = bound[1]
        document["applyId"] = bound[2]
        expected_keys = _DOCUMENT_KEYS | {"manifestId", "applyId"}
    if set(document) != expected_keys or command != onboard_cli_smoke_command(selected, context_paths=context_paths):
        _fail("invalid-document", "the smoke record is not the closed check-projects identity")
    stem = (
        "onboard-cli-smoke-"
        + hashlib.sha256(str(selected).encode("utf-8")).hexdigest()[:16]
        + "-"
        + started.strftime("%Y_%m_%d-%H_%M_%S-%f")
    )
    report_path = vault / f"{stem}.json"
    summary_path = vault / f"{stem}.md"
    summary = (
        "# Onboard check-projects 部署 smoke\n\n"
        "- 实际执行已安装的 scripts/onboard.py check-projects --json。只读探测。\n"
        "- 不启动 Graft，不调用 LLM 或 cloud，不执行项目脚本。\n"
        f"- 进程退出码：{completed.returncode}。sbtd.status=success。mockStrategy=none。\n"
        "- 证据只保存封闭投影 mode、projectRoot、sbtd.status 及其 canonical 摘要。\n"
        "- 不保存原始 stdout、stderr、stdin、凭证、项目脚本或项目树快照。\n"
        "- 此记录不是宿主事件验收，也不是业务 API 通过证明。\n"
    )
    report_ref = save_document(report_path, document, private_root=vault)
    write_file(summary_path, summary.encode("utf-8"), _ABSENT, scope=vault)
    return [report_ref, {"path": str(summary_path), "state": snapshot(summary_path)}]
