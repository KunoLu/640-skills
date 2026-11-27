---
schema_version: 1
id: v2.2.0-rc.3-graft-removal
workflow_mode: strict
mode_source: user
mode_note: rc.3 PRD D11、D13；T2 main CI 通过后接续 T3。
status: "blocked"
branch: feat/v2.2.0-rc.3-graft-removal
created_at: '2026-11-27T18:51:31.622028+08:00'
updated_at: "2026-11-27T18:52:38.180501+08:00"
completed_at: null
"blocked_reason": "OMP：PRD D7 与 rc.2 旧回执权限字段不一致；按定稿停止条件，等待确认缺失历史权限时的逐资源结果。"
---
# T3：移除 Graft 与存量安装退役

## T2 收尾回执

[PR #233](https://github.com/KunoLu/640-skills/pull/233) 的审查对象 `de5e037d4e8713e82d7ef966f76a37682fc0669b` 同时取得 OMP 内审 CLEAN、用户转达的 agy 独立复审 CLEAN 和 [PR validation 13/13](https://github.com/KunoLu/640-skills/actions/runs/45974880972)。合入后 `main` 为 `9d9ce3fe90eaf128b8332891dd315b2c1e11e3c4`，与受审提交的树相同，[main validation 13/13](https://github.com/KunoLu/640-skills/actions/runs/45983669865)。原开发分支本地与远程均已删除，未删除私有证据。

## 范围和 Book Gate Plan

FR-7／FR-8、D6／D7：移除启动和接线能力，保持非目标宿主能力；证据不足不得退役。只在隔离夹具操作，不接触实际宿主。保留历史数据 ignore、不可变记录与原件。T4 的 agy 适配和可选 ast-grep 检测不在本 PR。

- Legacy Safety：复用已完成的 T2 50 项退役夹具，另测新建文件、固定根正例、OMP 生效目录和历史权限证据；删除模块前建立 rc.2 与保留行为基线。
- Refactoring：先保护 `omp_agents_target` 与 `sbtd_omp_sources` 的共享解析依赖；不把删除专用模块作为绕过历史校验的手段。未批准生产编辑。
- DDIA／migration：设计前确认归属、写后状态及权限证明，保留 plan_id、备份、逐项回执和条件恢复。未具备的历史证据不得补造。
- 未完整调用 grill-with-docs：已给定 PRD 与范围；下列事实差异需要用户决定，不是开放式需求访谈。后续生产路径须完成可逆验证、项目验证、Release Readiness、内外审及同 SHA CI。

## D7 事实差异（生产编辑前）

PRD 要求历史 Graft 资源按记录的字节和权限比对。rc.2 tag `d8b2191204e368035fd69544aa74c6600961a2f6` 的 `onboard-contracts.schema.json` 中 `resource_result.after` 使用封闭 `state`，只允许 `type`、`checksum`；对普通文件，`sbtd_migration_files.snapshot` 只哈希内容。相同字节从 0600 改为 0644，rc.2 生产函数返回相同状态。`backup_ref` 指向写入前备份，不等于独立的写后权限证据，尤其是新建文件。T2 控制器记录了自己的夹具模式，不会给旧部署回执增加字段。

建议：已证实字节或权限不同记 drifted；字节相同且有可信独立写后权限记录才可判两者匹配；字节相同但缺历史权限证据，标该资源 not-verified 并列明原因，不误报 drifted 或 verified，继续其他资源。该只读结果不授权退役、清理或升级。等待确认；不修改旧 schema 或回执来补历史。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-27T18:51:42.263347+08:00 | planned | in-progress | OMP：开始 核对 rc.2 历史部署权限证据与 D7 | {"changed_files": [], "evidence_files": [], "sync_files": {}, "validation": ""} |
| 2026-11-27T18:52:27.349471+08:00 | in-progress | in-progress | OMP：完成 核对 rc.2 历史部署权限证据与 D7 | {"changed_files": [], "evidence_files": ["ai/tasks/v2.2.0-rc.3-graft-removal/reports/d7-mode.json", "ai/tasks/v2.2.0-rc.3-graft-removal/reports/d7-mode.md"], "sync_files": {"ai/tasks/v2.2.0-rc.3-graft-removal/reports/d7-mode.json": {"mtime_ns": 1795776702359309029, "sha256": "671c4ed40e4d33b554a67b28b0bb702b3337f0e72b46c83dc368bed584a13c8e", "size": 543}, "ai/tasks/v2.2.0-rc.3-graft-removal/reports/d7-mode.md": {"mtime_ns": 1795776719567383037, "sha256": "cf18db78f673fa1b8f399fa4d5476f26383a6b2b3033091ae7edcb27e33dc0ac", "size": 1549}}, "validation": "发行 schema 与生产普通文件快照只含 type/checksum，0600→0644 字节未变时快照不变。D7 缺失模式不能判 verified 或 drifted。"} |
| 2026-11-27T18:52:38.180501+08:00 | in-progress | blocked | OMP：PRD D7 与 rc.2 旧回执权限字段不一致；按定稿停止条件，等待确认缺失历史权限时的逐资源结果。 | 只做 rc.2 契约及临时普通文件特征实测；不改生产路径，不填造历史权限，不执行退役。 |
