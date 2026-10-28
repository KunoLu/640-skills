---
schema_version: 1
id: windows-migration-fixes-2026-10
workflow_mode: strict
mode_source: user
mode_note: 用户 2026-10-28 明确三个需求统一 strict mode 执行
status: "done"
branch: "main"
created_at: '2026-10-28T16:00:29.266197+08:00'
updated_at: "2026-10-28T16:51:56.214242+08:00"
completed_at: "2026-10-28T16:51:56.214242+08:00"
---
# Windows 迁移问题修复移植

## 目标

将 2026-10-26 Windows 迁移总结（~/Downloads/sbtd-workflow-migration-issues-2026-10-26.md）中适用于当前仓库的修复移植回本仓库：

- M03：Windows `.CMD`/`.BAT` shim 经 `cmd.exe /d /s /c` 执行（统一 `subprocess_command()`）。
- M04：子进程输出解码容错 `errors="replace"`。
- M05：Windows Java 检测支持 `bin/java.exe`（统一 `java_binary_path()`）。
- M01/M02：保留现行 raw-byte 摘要 + `.gitattributes -text` 契约（用户 2026-10-28 确认不移植归一化），补跨 checkout 摘要稳定回归测试。
- M06/M15：RTK 双证据规则与 vendored 测试边界写入 REFERENCE 契约。
- M07–M14、M16、M17：仓库已有机制或 GitNexus/Trellis 已退役，不适用。

## 范围与边界

分支 `sbtd/strict-windows-migration-fixes`。改 `sbtd-workflow-onboard/scripts/onboard.py`、根 `tests/` 新增/扩展测试、`sbtd-workflow-onboard/REFERENCE.md`。评估 README×2、版本化 automation prompt、CHANGELOG×2。不 sync。Windows 专项测试按平台条件 skip，macOS 实测并声明证据边界。

补充授权（用户 2026-10-28 会话内指示）：本分支任务全部完成后自动开 PR、以 GitHub admin 权限合入、合入后删除分支。三个需求分支均适用。

未完整调用 grill-with-docs：需求、逐项处置与验收由迁移文档与三项用户确认（顺序 3→1→2、M02 保留 raw-byte、graft 先评估）明确给出，无领域歧义；DDD 门不触发。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-28T16:01:54.573551+08:00 | planned | in-progress | 开始移植 Windows 迁移修复 | 分支 sbtd/strict-windows-migration-fixes 已建立；仓库现状核查：onboard.py 无 subprocess_command/java_binary_path/errors=replace；无 sbtd-workflow-onboard/tests/；stable 19/19 摘要在本机通过 |
| 2026-10-28T16:28:01.009057+08:00 | in-progress | checking | 实现与本地验证完成，进入检查/提交流程 | macOS 全量 701 测试与 main 基线 162 个既有环境失败集合完全一致、零新增；新增 14 个 Windows 平台测试 12 通过 2 个按平台 skip；独立 review 三个发现（spec 键、解码测试、错误消息）已修复并复验；py_compile 与 git diff --check 通过 |
| 2026-10-28T16:51:42.815936+08:00 | checking | checking | Explicit branch rebinding from "sbtd/strict-windows-migration-fixes" to "main": PR #196 已 squash 合入 main（a08cbae），开发分支按授权删除；任务完成记录落在 main | gh pr view 196: state=MERGED mergedAt=2026-10-28T08:50:20Z；main 已含 a08cbae |
| 2026-10-28T16:51:56.214242+08:00 | checking | done | PR #196 已 admin 合入 main 并删分支 | PR #196 tip e824e7a CI run 40657154740 attempt 1 全绿（13 作业，含 windows-shards 执行新 cmd shim 用例）；squash 合入 a08cbae；本地/远程分支已删 |
