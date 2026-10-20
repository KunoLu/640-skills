---
schema_version: 1
id: v2.1.0-rc.2-r2.0c-snapshot-persistence
workflow_mode: strict
mode_source: user
mode_note: 用户明确选择 strict；仅 plan.md R2.0c 与 D13。显式 git add 路径；不 push、不开 PR；禁止暂存或提交 .omp-r12b-addendum.txt 与 ai/tasks/codex-verify/。不修改 contracts、ADR 0001/0002 决策或 PRD 正文；不可避免的契约变化须 STOP + CONTRACT-CHANGE-NEEDED。
status: in-progress
branch: feat/v2.1.0-rc.2-r2.0c-snapshot-persistence
created_at: '2026-10-20T11:05:30+08:00'
updated_at: '2026-10-20T11:05:30+08:00'
completed_at: null
---

# R2.0c：临时 ReportSnapshot 落盘

基线 `2d147c98ce2874fa2621b95ff816e1781c02f93f`（R2.0b #146 squash-merge，2026-10-20T04:14:03+08:00）。用户 2026-10-20 11:02 Asia/Shanghai 授权开始。任务 done 仅指本地验收完成，不指发布或合并；plan 行在合并前保持 in_progress。

## 范围与验收

1. SnapshotStore 从进程内 3600s 改为 runtime home/snapshots/ 落盘、默认 24h；创建返回 expires_at。
2. 临时文件写入、fsync、atomic rename；版本头与校验和验证；截断、缺校验和、错误版本均不可读取为有效快照。
3. 启动清扫过期快照，只触及 snapshots/；exports/、审计库、配置、源任务／报告／handoff 不受影响。
4. 被引用快照不得因 expiry/sweep 删除；提供后端 pin 生命周期及 R2.0b PinRegistry → R2.1a 对接说明，不实现导出作业。
5. TTL 内 serve 重启后可凭 snapshot_id 解析原快照。
6. runtime 既有约定：目录 0700、文件 0600；拒绝 symlink 越界。
7. 清理授权独立引用 PRD §10.4 / D13；AC-61 不覆盖快照清理。
8. 新 ADR 0003 固定快照格式版本及 checksum，不改既有 ADR 决策。
9. 更新 sbtd-runtime/docs/install-and-use.md 的进程内／3600s／R2.0c pending 描述。

## 事实与实施顺序

已读 plan.md R2.0c、grill-r1.md D13/Q6c-A/R1e/DDD Query & Snapshot、PRD §10.2–10.4、ADR 0001 runtime home、report_snapshot.py、stats_query.py、serve.py、R2.0b task 与 PinRegistry 调用证据。

未完整调用 grill-with-docs：D13 和验收已锁定，本次不重新开放需求。既有 expires_at 已在 Snapshot.public_view；OpenAPI Envelope.data 无字段限制，新增查询返回 expires_at 无需契约修改。Python LSP references 返回 No language server found；源码搜索确认调用点仅 serve 与 snapshot/CSV 测试。

提交顺序：docs backfill → ADR → production implementation → tests/docs → evidence closeout。测试先在工作区建立红例，依用户要求在第四提交收录。不修改 R2.1a+ planned 状态。

## Book Gate Plan

| Gate | 触发事实 | 阶段 | 状态 |
|---|---|---|---|
| book-ddd-distilled-modeling | 引用保活与清理所有权需区分 UI pin 与服务端 pin | before-dev | planned |
| book-ddia-data-design | 新持久格式、跨进程读取与 crash recovery | before-dev | planned |
| book-legacy-change-safety | 既有 snapshot/cursor/CSV 行为高回归面 | before-dev | planned |
| book-refactoring-pass | 修改既有 Python 生产代码 | before-dev | planned |
| book-release-readiness | serve 启动行为及持久 runtime 改变 | validation 后 | planned |

严格检查：中文场景＋英文 Given/When/Then，沿用 sbtd-runtime/spec/*.md；SnapshotStore 和真实 serve 为用户指定测试 seam；corruption/sweep/restart/pin/permissions 回归；独立只读 review；可读性与 ponytail-review；project-validation。全仓 run_ci 历史运行约 46 分钟，不视为 quick；优先 runtime suite 与 CI 对应 focused checks，跳过原因最终如实记录。

## 状态持久化限制

已实际调用安装的 TaskStore.create；返回 `TaskStateError: task has no YAML frontmatter block`，未建立本任务或 active 指针。既有 R2.0b 记录同类 catalog 冲突涉及禁止修改的 ai/tasks/codex-verify/；本次不更改该路径。此文件为用户明确要求的共享交付记录，非 TaskStore 成功证据，不承诺自动恢复。ignore 已确认保护 .sbtd/active-task.json 与 ai/tasks/**/reports；未写本地状态。

## 验证证据

尚未执行实现验证；不得把 planned gate 或文档完成视为验收通过。

## CONTRACT-CHANGE-NEEDED

未触发：保持全部既有 contracts、ADR 0001/0002 与 PRD 正文不变。

## 模型使用

| 用途 | 请求模型 | 实际模型 | 调用次数 |
|---|---|---|---|
| implementation / validation / closeout | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra（当前 host 标识；high 为请求档位） | unknown |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-20T11:05:30+08:00 | planned | in-progress | 用户明确 strict 与 R2.0c 范围，分支及基线匹配；共享记录创建，不声称 TaskStore 持久化成功 | git status/rev-parse；D13；本文件状态持久化限制 |
