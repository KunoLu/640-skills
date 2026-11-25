---
schema_version: 1
id: v2.2.0-rc.2-graft-retirement
workflow_mode: strict
mode_source: user
mode_note: 用户授权 main CI 全绿后按已确认 PRD 推进任务 5；§4 要求 strict。
status: "blocked"
branch: feat/v2.2.0-rc.2-graft-retirement
created_at: '2026-11-25T10:04:13.021586+08:00'
updated_at: "2026-11-25T10:06:53.031814+08:00"
completed_at: null
"blocked_reason": "当前 Astra 会话：首轮清单已列出两个当前域 MCP 候选，尚无绑定实际写入及可恢复原件的证据，按 PRD §7 停止真实退役。"
---
# 任务 5：替代检索验收后退役 Graft

基线：PR #226 squash `d6e0bc3c0e366a65d1abd5e25ebc78969e1e9329`，[main CI](https://github.com/KunoLu/640-skills/actions/runs/45527867674) 13/13；任务 4 宿主与配置证据在其本地 ignored reports，未迁移或删除。

## 范围与顺序

按 2026-11-23 PRD §7 任务 5：先列出 Codex／OMP 每个候选的精确位置、SBTD 写入凭证及恢复手段；无凭证不得退役。同名、内容相似、路径存在均不能单独证明写入者。保留用户与第三方条目、未知项及 hook 文件。真实宿主写入须在展示新鲜清单后单独确认。不改主线、不同步、不执行任务 6 或发布。

正向验收：仅清除获准且现场与历史证据吻合的条目，运行两次不产生额外改动，恢复后逐项比对。负向验收：替代能力未通过、来源不明、漂移、路径不安全或恢复材料不完整时拒绝相应写入。提供双语 breaking、旧项目升级与恢复说明。

## 工程与验证门禁

当前阶段为只读盘点，未批准真实宿主清除。strict：生产编辑前完成 Legacy Change Safety、Refactoring；持久配置的迁移证据和可回退设计须经 DDIA、migration。验证用任务 5 私有 TEMP 合成配置，不沿用任务 4 凭据或环境；精确 SHA 内置 `/review`、外审、CI 分别记录。当前主会话 Astra，精确调用次数未知。未完整调用 grill-with-docs：输入、归属门和负例已由 PRD 明定；不把无法证明的归属作为需求假设。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-25T10:04:23.039998+08:00 | planned | in-progress | 当前 Astra 会话：在新 main 派生分支开始任务 5 归属及恢复清单预检。 | 本地及远端任务 4 分支已按冻结 SHA 移除，保留任务 4 私有报告与源 bundle；独立任务 5 TEMP 640-skills-rc2-task5.MLZgBxWU。未写真实宿主或执行退役。 |
| 2026-11-25T10:06:53.031814+08:00 | in-progress | blocked | 当前 Astra 会话：首轮清单已列出两个当前域 MCP 候选，尚无绑定实际写入及可恢复原件的证据，按 PRD §7 停止真实退役。 | Codex mcp_servers.sbtd-graft 与 OMP mcpServers.sbtd-graft 均存在；四类 Codex hook 中目标启动器命中 0。OMP 原件目录不是成功部署回执，Codex 已知备份路径经过别名，未跟随。可删除集合为空，宿主写入 0。见 reports/inventory.json、inventory.md。需受控的既有部署回执位置或明确改为隔离夹具演练；禁止按名称删除。 |
