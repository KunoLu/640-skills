"""任务节点核对与进展记录；仅 Git／本地文件，不接入平台或 CI。"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from sbtd_project import open_regular_file
from sbtd_task_document import TaskDocument
from sbtd_task_state import TaskSnapshot, TaskStateError, TaskStore


@dataclass(frozen=True)
class ProgressCheck:
    task: TaskSnapshot
    method: str
    differences: tuple[str, ...]
    notes: tuple[str, ...] = ()
    discarded: bool = False


class TaskSync:
    def __init__(self, store: TaskStore) -> None:
        self.store = store

    def _git(self, *args: str) -> str:
        result = self.store._git(*args)
        if result.returncode:
            raise TaskStateError(
                "Git 核对失败；不可考",
                "保留 task，检查远端／引用／本地 Git 可用性后重试",
            )
        return result.stdout.rstrip("\n")

    def _relative(self, path: str) -> str:
        if (
            not isinstance(path, str)
            or not path
            or path == "."
            or PurePosixPath(path).as_posix() != path
            or any(part in (".git", ".sbtd") for part in PurePosixPath(path).parts)
        ):
            raise TaskStateError(
                "核对路径必须为明确的项目相对文件／目录，不能包含 Git 或私有状态"
            )
        self.store._path(path)
        return path

    def _inventory(
        self, scope: tuple[str, ...], extra: tuple[str, ...], task_path: str
    ) -> dict[str, dict[str, Any]]:
        paths = set(extra)
        for relative in scope:
            directory = self.store._path(self._relative(relative))
            if not directory.exists():
                continue
            if not directory.is_dir():
                raise TaskStateError("声明范围不是目录")

            def unreadable(error: OSError) -> None:
                raise TaskStateError("声明范围无法完整读取") from error

            for base, directories, files in os.walk(
                directory, followlinks=False, onerror=unreadable
            ):
                for name in directories:
                    self.store._path(
                        (Path(base) / name).relative_to(self.store.root).as_posix()
                    )
                paths.update(
                    (Path(base) / name).relative_to(self.store.root).as_posix()
                    for name in files
                )
        result = {}
        for relative in sorted(paths):
            self._relative(relative)
            if relative == task_path:
                continue  # task 自身由事件保全，不能计算自引用哈希。
            path = self.store._path(relative)
            if not path.exists():
                continue
            try:
                with open_regular_file(path, "进展文件") as handle:
                    before = path.stat()
                    digest = (
                        hashlib.file_digest(handle, "sha256").hexdigest()
                        if hasattr(hashlib, "file_digest")
                        else hashlib.sha256(handle.read()).hexdigest()
                    )
                    after = path.stat()
                if (before.st_ino, before.st_size, before.st_mtime_ns) != (
                    after.st_ino,
                    after.st_size,
                    after.st_mtime_ns,
                ):
                    raise TaskStateError("核对期间文件变化；重新读取后再记录")
            except OSError:
                raise TaskStateError("进展文件无法读取") from None
            result[relative] = {
                "sha256": digest,
                "mtime_ns": after.st_mtime_ns,
                "size": after.st_size,
            }
        return result

    @staticmethod
    def _scope(document: TaskDocument) -> tuple[str, ...]:
        scope = document.frontmatter.get("sync_scope", [])
        if not isinstance(scope, list) or not all(
            isinstance(item, str) for item in scope
        ):
            raise TaskStateError("sync_scope 必须为目录路径列表")
        return tuple(scope)

    @staticmethod
    def _last_inventory(document: TaskDocument) -> dict[str, Any] | None:
        for event in reversed(document.events):
            try:
                evidence = json.loads(event["evidence"])
            except ValueError:
                continue
            if isinstance(evidence, dict) and "sync_files" in evidence:
                files = evidence["sync_files"]
                if not isinstance(files, dict):
                    raise TaskStateError("文件核对证据损坏")
                for path, value in files.items():
                    if (
                        not isinstance(value, dict)
                        or not isinstance(path, str)
                        or not isinstance(value.get("sha256"), str)
                        or re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is None
                    ):
                        raise TaskStateError("文件核对证据损坏")
                return files
        return None

    def check(
        self,
        task_id: str | None = None,
        *,
        remote: str = "origin",
        default_branch: str | None = None,
    ) -> ProgressCheck:
        selected = self.store.inspect(task_id)
        document = selected.document
        binding = self.store.current_binding()
        differences: list[str] = []
        notes: list[str] = []
        if document.legacy_events:
            notes.append("旧格式事件，不追溯")
        if document.baseline_changed:
            differences.append("旧事件基线 sha256／事件行数变化")
        if document.frontmatter["branch"] != binding:
            differences.append("分支绑定变化：需明确重绑定；核对仍使用 task 记录分支")
        tracked = (
            binding is not None
            and self.store._git(
                "ls-files", "--error-unmatch", "--", selected.task_path
            ).returncode
            == 0
        )
        shared = selected.task_path.startswith("ai/tasks/") and document.frontmatter[
            "workflow_mode"
        ] in ("lite", "strict")
        if tracked and shared:
            remotes = self._git("remote").splitlines()
            method = "A" if remotes else "B"
            recorded = document.frontmatter["branch"]
            discarded = False
            if method == "A":
                if self.store.read_only:
                    raise TaskStateError("只读工作不执行 fetch；远端核对未执行")
                if remote not in remotes:
                    raise TaskStateError("核对远端未配置；明确选择实际远端")
                self._git("fetch", "--no-tags", remote)
                if default_branch is None:
                    head = self._git("ls-remote", "--symref", remote, "HEAD")
                    names = [
                        line.split("\t")[0].removeprefix("ref: refs/heads/")
                        for line in head.splitlines()
                        if line.startswith("ref: refs/heads/")
                    ]
                    if len(names) != 1:
                        raise TaskStateError("默认分支不可考；明确指定 default_branch")
                    default_branch = names[0]
                self._git("check-ref-format", "refs/heads/" + default_branch)
                reference = "refs/remotes/" + remote + "/" + default_branch
                self._git("rev-parse", "--verify", reference + "^{commit}")
                present = self._git("ls-tree", reference, "--", selected.task_path)
                remote_status = None
                if not present:
                    notes.append("默认分支未包含 task；不可考，不推断丢弃")
                else:
                    remote_result = self.store._git(
                        "show", reference + ":" + selected.task_path
                    )
                    if remote_result.returncode:
                        raise TaskStateError("默认分支 task 无法读取；不可考")
                    remote_text = remote_result.stdout
                    remote_status = TaskDocument.parse(remote_text).frontmatter[
                        "status"
                    ]
                    if remote_text != document.text:
                        differences.append("默认分支 task 内容与工作区不同")
                if recorded and not recorded.startswith("detached:"):
                    self._git("check-ref-format", "refs/heads/" + recorded)
                    heads = self._git(
                        "ls-remote", "--heads", remote, "refs/heads/" + recorded
                    )
                    if (
                        not heads
                        and remote_status is not None
                        and remote_status != "done"
                    ):
                        discarded = True
                        differences.append(
                            "记录分支远端已不存在且默认分支 task 非 done：按已丢弃处理，交人工判断"
                        )
                elif recorded and recorded.startswith("detached:"):
                    notes.append("detached 绑定无远端分支存在性判定")
            else:
                head = self.store._git("show", "HEAD:" + selected.task_path)
                if head.returncode:
                    notes.append("本地 HEAD 未包含 task；不可考，不推断丢弃")
                elif head.stdout != document.text:
                    differences.append("本地 HEAD task 内容与工作区不同")
            if recorded:
                reference = (
                    recorded.removeprefix("detached:")
                    if recorded.startswith("detached:")
                    else "refs/heads/" + recorded
                )
                branch_task = self.store._git(
                    "show", reference + ":" + selected.task_path
                )
                if branch_task.returncode:
                    notes.append("记录分支 task 不可考")
                elif branch_task.stdout != document.text:
                    differences.append("记录分支 task 内容与工作区不同")
            return ProgressCheck(
                selected, method, tuple(differences), tuple(notes), discarded
            )
        previous = self._last_inventory(document)
        scope = self._scope(document)
        if not scope or previous is None:
            notes.append(
                "文件核对范围或快照缺失：不可考；下次真实节点记录范围与文件证据"
            )
        else:
            current = self._inventory(scope, tuple(previous), selected.task_path)
            for path in sorted(previous.keys() | current.keys()):
                if path not in previous:
                    differences.append("新增文件：" + path)
                elif path not in current:
                    differences.append("删除文件：" + path)
                elif previous[path]["sha256"] != current[path]["sha256"]:
                    differences.append("文件内容变化：" + path)
        return ProgressCheck(selected, "C", tuple(differences), tuple(notes))

    def record(
        self,
        task_id: str,
        *,
        step: str,
        writer: str,
        completed: bool = False,
        validation: str = "",
        files: tuple[str, ...] = (),
        evidence_files: tuple[str, ...] = (),
        scope: tuple[str, ...] | None = None,
        confirmed: bool = False,
    ) -> TaskSnapshot:
        selected = self.store._selected_for_write(task_id, confirmed)
        document = selected.document
        self.store._require_known_mode(document)
        if (
            not step.strip()
            or not writer.strip()
            or (completed and not validation.strip())
        ):
            raise TaskStateError("进展事件需要写入者、步骤及完成时的验证结果")
        if not self.store._history(document)[1]:
            raise TaskStateError("任务历史与当前状态冲突")
        directories = tuple(scope) if scope is not None else self._scope(document)
        for path in directories:
            self._relative(path)
        previous = self._last_inventory(document) or {}
        inventory = self._inventory(
            directories, tuple(previous) + files + evidence_files, selected.task_path
        )
        for path in evidence_files:
            if path not in inventory:
                raise TaskStateError("验收证据文件缺失")
        moment = self.store._now(document)
        status = document.frontmatter["status"]
        target = "in-progress" if status == "planned" and not completed else status
        fields: dict[str, Any] = {"updated_at": moment, "status": target}
        if scope is not None:
            fields["sync_scope"] = list(directories)
        event = {
            "at": moment,
            "from": status,
            "to": target,
            "reason": writer + "：" + ("完成 " if completed else "开始 ") + step,
            "evidence": json.dumps(
                {
                    "validation": validation,
                    "changed_files": list(files),
                    "evidence_files": list(evidence_files),
                    "sync_files": inventory,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        }
        return self.store._save(selected, document.updated(fields, event=event))

    def record_check(
        self, result: ProgressCheck, *, writer: str, confirmed: bool = False
    ) -> TaskSnapshot:
        task_id = result.task.document.frontmatter["id"]
        selected = self.store._selected_for_write(task_id, confirmed)
        if selected.document.text != result.task.document.text:
            raise TaskStateError("核对后 task 已变化；重读后再判断")
        if not writer.strip():
            raise TaskStateError("核对事件需要写入者")
        if not result.differences:
            return selected
        document = selected.document
        moment = self.store._now(document)
        status = document.frontmatter["status"]
        candidate = document.updated(
            {"updated_at": moment},
            event={
                "at": moment,
                "from": status,
                "to": status,
                "reason": writer + "：发现未记录的改动",
                "evidence": "；".join(result.differences)
                + "；交人工判断，不自动改变状态或 reopen。",
            },
        )
        return self.store._save(selected, candidate)

    def check_finish_commit(self, task_path: str, *, commit: str = "HEAD") -> None:
        """只验证本地收尾 diff；不声称 CLEAN 或 CI run 真实通过。"""
        self.store._path(task_path)
        revision = self._git("rev-parse", "--verify", commit + "^{commit}")
        parents = self._git("rev-list", "--parents", "-n", "1", revision).split()
        if len(parents) != 2:
            raise TaskStateError("收尾必须为一个非 merge 提交")
        parent = parents[1]
        paths = (
            self._git(
                "diff-tree", "--no-commit-id", "--name-only", "-z", "-r", revision
            )
            .rstrip("\0")
            .split("\0")
        )
        if paths != [task_path]:
            raise TaskStateError("收尾修改了其他文件：需要整轮重审")
        before_raw = self.store._git("show", parent + ":" + task_path)
        after_raw = self.store._git("show", revision + ":" + task_path)
        if before_raw.returncode or after_raw.returncode:
            raise TaskStateError("收尾 task 必须为已有文件")
        before, after = (
            TaskDocument.parse(before_raw.stdout),
            TaskDocument.parse(after_raw.stdout),
        )
        if (
            before.frontmatter["status"] != "checking"
            or after.frontmatter["status"] != "done"
            or len(after.events) != len(before.events) + 1
        ):
            raise TaskStateError("收尾必须 checking → done 且仅追加一条事件")
        event = after.events[-1]
        try:
            evidence = json.loads(event["evidence"])
        except ValueError:
            raise TaskStateError("收尾证据必须仅含 clean_sha 与 ci_run") from None
        if (
            not isinstance(evidence, dict)
            or set(evidence) != {"clean_sha", "ci_run"}
            or evidence["clean_sha"] != parent
            or not isinstance(evidence["ci_run"], str)
            or not evidence["ci_run"].strip()
            or event["from"] != "checking"
            or event["to"] != "done"
            or event["at"] == "unknown"
            or after.frontmatter["completed_at"] != event["at"]
            or after.frontmatter["updated_at"] != event["at"]
        ):
            raise TaskStateError("收尾事件或 CLEAN SHA／CI run 证据不符合限定")
        candidate = before.updated(
            {
                key: after.frontmatter[key]
                for key in ("status", "completed_at", "updated_at")
            },
            event=event,
        )
        before_mode = self._git("ls-tree", parent, "--", task_path).split()[0]
        after_mode = self._git("ls-tree", revision, "--", task_path).split()[0]
        if candidate.text != after.text or before_mode != after_mode:
            raise TaskStateError("收尾修改了其他行或文件模式：需要整轮重审")
