---
schema_version: 1
id: v2.2.0-rc.2-host-behavior
workflow_mode: strict
mode_source: user
mode_note: rc.2 PRD；用户授权从任务 2 合入后的 main 开始任务 3。
status: "blocked"
branch: test/v2.2.0-rc.2-host-behavior
created_at: '2026-11-24T16:35:41.545526+08:00'
updated_at: "2026-11-24T16:41:39.990741+08:00"
completed_at: null
"blocked_reason": "当前 Astra 会话：任务 3 的新隔离 CODEX_HOME 未登录；按认证停止条件关闭 /loop，待本域受控官方认证。"
---
# 任务 3：新版基础行为与最小兼容调整

输入：任务 2 的 PR [#224](https://github.com/KunoLu/640-skills/pull/224) 已由明确的 admin 授权 squash。许可修复的外审 head 为 `c57ae7efc7326249b23f847f299d7bab90fd6534`，对应 [PR CI](https://github.com/KunoLu/640-skills/actions/runs/45351271714)；当前任务以 squash 后的 `b0958078cf8e9d31739bef9cf17e76973f2dfee3` 为基线，对应独立的 [main CI](https://github.com/KunoLu/640-skills/actions/runs/45354457553)。这不是发布授权。

## 范围与通过标准

在 Air 的原 Astra 实现会话组织隔离进程，分别验证 OMP `19.1.0` 和 Codex `0.171.0`。主会话不是被测 OMP 版本。配置读取、权限和真实审批（含拒绝）、工具装载与实际调用、原生事件、失败及中断需分别取证；版本号、工具清单、未登录回执和上一任务的成功调用均不能代替。

- 仅使用本任务私有 HOME、CODEX_HOME、OMP agent/session、缓存与合成项目。全局认证、信任、真实正在写入的会话日志均不读取、不复制、不迁移。仅允许在获准的隔离域走官方认证。未证明会话归属或出现意外写入立即停。
- 不启用可选 eval，不连接其他 MCP 或共享 daemon；不自动信任未知仓库。先用最小权限，只读取无敏感信息的固定文件，检查工具输入、真实退出码、返回结果和事件。失败／拒绝／中断分别保留原生记录，不用 timeout 代替确认的中断语义。
- 只在原生观察提供具体兼容性缺口后才改适配器。不混入任务 4 的 ast-grep MCP 接线，不提前发布。

## Book Gate Plan

未完整调用 grill-with-docs：PRD 已给定固定版本、范围、负例和停止条件。无新增领域术语或持久化格式设计。若发现真实行为回归，修改前执行 Legacy Safety／Refactoring，先保留旧失败和消费边界；若涉及持久化或跨进程契约，再评估 DDIA。正式结论需真实宿主验收、project-validation；若改到生产路径则再做 release readiness。

## 证据与恢复

脱敏报告仅存本任务 ignored `reports/`。当前 OMP 主角色 GPT-6.2 Astra，精确调用次数未知。保留临时域及失败现场，不清除此前任务 TEMP。身份、真实审批、全局隔离或会话占用不明时记录阻断、关循环、保留现场；不以自动切换模型或复用其他账户恢复。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-24T16:37:53.200209+08:00 | planned | in-progress | 当前 Astra 会话：开始任务 3，隔离预检及固定宿主行为验收。 | main b0958078cf8e9d31739bef9cf17e76973f2dfee3 CI 45354457553 13/13 通过，任务 2 本地及远端分支已清除。固定版 OMP 19.1.0（发行制品 SHA256 已校验）、Codex 0.171.0、Bun 1.4.4；原会话 CLI 19.1.1 保留不动。临时域 /Users/lusonglin/TEMP/640-skills-rc2-task3.IL73xkq4，未复制认证。 |
| 2026-11-24T16:41:39.990741+08:00 | in-progress | blocked | 当前 Astra 会话：任务 3 的新隔离 CODEX_HOME 未登录；按认证停止条件关闭 /loop，待本域受控官方认证。 | 固定 OMP 19.1.0、Codex CLI 0.171.0、Bun 1.4.4；已验证 OMP 临时配置读取、Codex app-server config/read 与空 MCP 配置。codex login status：exit 1，Not logged in；原交互终端确认 Loop mode disabled。详见 reports/preflight.json 与 preflight.md。没有复用凭据、发起模型调用或变更全局信任。 |
