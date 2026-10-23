---
schema_version: 1
id: v2.1.0-rc.2-r2.2-e2e-security
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict；主会话唯一 writer／验证 controller；仅授权 worktree 内三个本地 commit，显式路径暂存；不 push／PR／评论／merge／rebase／amend，不修改全局配置或其他 worktree。
status: in-progress
branch: feat/v2.1.0-rc.2-r2.2-pr1-disk-quota-507
created_at: '2026-10-23T12:40:31+08:00'
updated_at: '2026-10-23T12:40:31+08:00'
completed_at: null
---

# R2.2 PR-1：共享磁盘配额与 507

## 用户决定与任务身份

用户 2026-10-23 12:11 +08:00 群内说开始 R2.2，Lord 记录。当前仅 PR-1；plan 的 R2.2 任务表行保持 planned，直到 PR-4 收尾。授权根 `/workspace/640-skills-r22`，入口 HEAD／origin/main `cb12b606f1ec74d8bc87da12dd0d828628fa7724`，分支如 frontmatter，无 upstream；入口工作区干净。未完整调用 grill-with-docs：用户明确行为、顺序、契约与验收，无新领域决定。

## 范围与验收

- snapshots/ 与 exports/ 共享字节上限，默认 2000000000；环境变量 `SBTD_RUNTIME_DISK_QUOTA_BYTES` 严格按 ADR 0003 §5 解析，非法值拒绝启动，不回显原值。
- 按 ADR §4 验证目录、扁平 lstat 计量普通文件；坏／未知文件保留且计数。清扫过期且无引用数据及已确认残留 temp，再测量；80% 只记日志，U > L 才拒绝，U == L 放行，不预留未来产物大小、不淘汰未过期数据。
- SnapshotStore 库拒绝携带两项 byte counts，不新增 snapshot HTTP handler。createExport 顺序保持 access 401/403 → validation 400 → replay 原 202 → 新请求 503 → 404 → 410 → 507 → 422；拒绝无 job／ID／新文件。
- TDD seams 为用户指定的真实 loopback HTTP＋stores、snapshot library 与启动 CLI；先 red 后实现。完整 runtime suite、golden 61、changed Python ruff、diff、YAML、受保护契约零 diff。原生报告保留失败与同 stem 中文汇总，不暂存 reports。
- 不修改 contracts/openapi.yaml、golden JSON、schemas、PRD 或 ADR；若必须修改则 STOP 并记录 blocker。install-and-use 仅补配置与 507 的用户操作说明；不提前执行后续项 B/C。
- 严格串行后续：PR-2 安全（AC-56、ticket 日志、ADR 风险）；PR-3 macOS／Windows CI、用户 Mac 视觉／字体（AC-33／AC-62）及对账（AC-51／AC-45）；PR-4 §18 性能、默认配额容量校准与 R2.2 收尾。PR-1 完成不等于 R2.2 done。

## Book Gate Plan

| Gate | 客观触发／阶段 | 初始状态 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义／需求前 | not-needed；未完整 grill，数据所有权由 ADR 固定。 |
| book-ddia-data-design | 共享磁盘、异步导出、清扫／设计稳定前 | pending；核实共享锁、pin、temp 在途登记及恢复顺序后输出独立 Review。 |
| book-legacy-change-safety | 既有重放与清扫高回归风险／行为编辑前 | pending；先建立 HTTP 优先级、配额与保留边界 red。 |
| book-refactoring-pass | 既有生产代码编辑／before-dev | pending；在 legacy characterized 后判断最小共享协调，无无关重构。 |
| TDD／gherkin-bdd／ponytail | 新配额外部行为／before-dev | 已加载；复用现有 Markdown spec、unittest 与标准库，不引入 runner 或依赖。 |
| 独立 review／可读性 | 两 store 与 serve 公共准入／check | pending；仅只读审查，主会话集成与验证。 |
| project-validation | 用户指定本地命令／check | pending；真实 serve smoke 独立于 tests，报告实际环境，不冒充跨平台 CI。 |
| book-release-readiness | runtime 启动与运行行为／验证后 | pending；仅 PR-1 本地就绪，不代表部署或 rc.2 发布。 |

## 验证证据

首轮事实核实：`git log -1 --format='%H %cI'` 分别读取 e748a5eddfba38cd487af9dfc5271e601de7c76b 与 cb12b606f1ec74d8bc87da12dd0d828628fa7724，得到 2026-10-23T11:28:33+08:00／2026-10-23T12:01:59+08:00；mergedAt 由 Lord 提供，换算一致。`git show de97926:ai/tasks/v2.1.0-rc.2-plan/plan.md` 核实原后续项 B 的依据原句。PRD 第 845 行归因逐字核对，旧 task 历史段落与事件不重写。

## 提交与恢复边界

1. Commit 1：仅 plan、#160 task、#161 task、本 task 四份 records，回填并开启本任务。
2. Commit 2：实现、测试与必要用户说明／既有行为 spec；不混入历史 records。
3. Commit 3：仅本 task 的验证、覆盖映射、提交与模型 SNAPSHOT 追加记录。

路径逐级检查 containment／无 symlink；reports 由 `.gitignore:4:/ai/tasks/**/reports` 保护。沿用既有 rc.2 records 明示的 TaskStore catalog/frontmatter 兼容限制及 active／index 超授权边界；使用指定共享 Markdown 记录，不声称 helper lifecycle 或自动恢复成功，不改 active／index／ignore／developer 身份。无持久格式迁移；回退实现提交不执行数据删除。仅本地提交，无发布授权。

## 模型使用

| agent/session | provider/model | thinkingLevel | assistant / toolCall | purpose | resolvedModelIsFallback | title-gen |
|---|---|---|---|---|---|---|
| astra ping／01a1670d-3152-7552-9c9d-4115fa5f0d26 | openai-codex/gpt-6-astra | high | 1 / 0（Lord 记录） | --no-tools；ASTRA_OK | false | 未知 |
| main／01a1670e-d268-7166-9235-0ea39b58c08f | openai-codex/gpt-6-astra | high | 4 / 23（PRE-COMMIT SNAPSHOT，非 FINAL） | 唯一 writer／controller；2026-10-23T12:40:31+08:00，main/session/2026-10-23T04-39-47-048Z_01a1670e-d268-7166-9235-0ea39b58c08f.jsonl 第 1–56 行 | false | 未知（运行中） |

主会话按 message.role=assistant 及其 toolCall blocks 计数，只读 model_change／thinking_level_change；后续编辑、校验、提交和最终回复不在该 SNAPSHOT 内。FINAL 由 Lord 在 PR body 报告，不将提交前取样写成最终值。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-23T12:40:31+08:00 | planned | in-progress | 用户 2026-10-23 12:11 +08:00 群内说开始 R2.2，Lord 按 plan.md 定拆分为 4 个串行 PR（PR-1 配额与 507 → PR-2 安全 → PR-3 跨平台 E2E 与对账 → PR-4 性能、校准与收尾），Lord 记录 | strict／user；授权根、分支、入口 cb12b606f1ec74d8bc87da12dd0d828628fa7724 已核实；仅三个本地提交；plan R2.2 行保持 planned。 |
