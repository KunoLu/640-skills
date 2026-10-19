---
schema_version: 1
id: v2.1.0-rc.2-r2.0a-serve
workflow_mode: strict
mode_source: user
mode_note: Lead 本次明确指派 strict 模式 SBTD 任务；范围严格等于 plan.md R2.0a 行的 PR-2 段（serve 启动与访问控制 D5–D8 实现＋单测、Reviewy #142 CLEAN review 的 PR-2 项、PR-1 延后项中 serve 接线前必须落地的项）。硬边界（condition c）：不得变更 contracts/panel-manifest.json、panel-manifest.schema.json、ADR 0002 任何决策、openapi.yaml 或任何其他契约；契约变更不可避时停下并出 CONTRACT-CHANGE-NEEDED 报告。plan.md R2.0a 行在 PR-2 合并前不标 done。显式 git add 路径；不纳入 .omp-r12b-addendum.txt 与 ai/tasks/codex-verify/；不 push、不开 PR。
status: "in-progress"
blocked_reason: null
branch: feat/v2.1.0-rc.2-r2.0a-serve
created_at: '2026-10-19T17:55:28+08:00'
updated_at: '2026-10-19T17:55:28+08:00'
completed_at: null
---

R2.0a **PR-2**：`serve` 启动与访问控制（D5–D8）实现＋单测。分支 `feat/v2.1.0-rc.2-r2.0a-serve` 基于 main `3c9cf4e`（PR-1 #142 squash-merge 产物）。

## 事实源（已通读）

- `ai/tasks/v2.1.0-rc.2-r2.0a-dashboard/task.md`（拆分决定：PR-2 验收归属、PR 边界、延后非阻塞项）
- `docs/adr/0002-v2.1.0-rc.2-r2.0a-dashboard-frontend-decisions.md`（§3 `#ticket` 风险文本；缓解措施的代码实现属本 PR）
- `ai/tasks/v2.1.0-rc.2-plan/plan.md`（R2.0a 行）与 `grill-r1.md`（锁定决定 D5–D8、Local Server & Access Control 上下文）
- `docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md`（§10.2、§12.3、§13.4、§19.3）
- `docs/adr/0001-v2.1.0-rc.1-r1.0-runtime-decisions.md`（§2 Starlette+uvicorn、§5 一次性配对换 session／Bearer、0600、loopback＋Host/Origin＋CSRF）
- `sbtd-runtime/contracts/openapi.yaml`（pair／Session／CSRF／Idempotency-Key／Host-Origin 403 语义；代码对齐契约，不改契约）

## 范围（等于拆分决定的 PR-2 段，不扩项）

- 回填 commit：PR-1（#142，squash-merge `3c9cf4e`，2026-10-19T17:32:13+08:00）回填到 PR-1 任务记录与 plan.md R2.0a 行（行保持 in_progress，PR-2 合并后才 done）；同步修正 PR-1 记录中失实的表述（manifest_version 锁定方式、体积基线、测试计数）与 artifact-budget.json／ADR 0002 §1 的基线数字（仅数字，不改决策）。
- `serve`（D5–D8）：CLI 入口、前台 Ctrl-C、默认 `--open`；实例锁＋端口双判＋陈旧锁按无效处理（D6）；端口占用即失败并提示 `--port`、退出码非零（D5）；一次性 ticket 经 URL fragment 配对换 session／Bearer、读后即毁、不进日志、终端不打印（D7＋ADR 0002 §3 缓解落地）；Host／Origin 严格白名单硬编码（D8）；服务入仓的 `dashboard/static/` 产物。
- `/api/v1` 路由接 R1 真实库面（`stats_query`／`report_snapshot`），不用 mock 数字。
- 单测覆盖 D5–D8 全部行为，真实 socket／进程，不用 mock 顶替被测行为。
- 更新 `test_runtime_package_does_not_import_a_server` 钉法：R2 起允许服务层存在，钉法改为「库面模块不得 import 服务层」。
- 新 Python 依赖精确钉版，沿用仓内惯例。

### Reviewy #142 CLEAN review 落在 PR-2 的项

1. **PanelCard 必须展示 partial／conditional 数据**：指标带 `missing` 或 `sample_status` 时显示 partial／conditional 标记；`strata` 存在时渲染（如 `validations.run_pass_rate` value 为 null 但 strata 有数据）；嵌套 null 渲染为 unknown，绝不显示 "null"。按 PRD §12.3 与 overview 文案「展示 unknown／partial 与原因」。对 R1 golden 数据验证（`usage.tokens`：support conditional、missing true；`validations.run_pass_rate`）。
2. （PR-1 已修，记录于此仅备查。）
3. **api.ts 对齐 openapi.yaml**：~L182-183 注释错误声称重试可去重（每次重试生成新 Idempotency-Key 并不会去重）——修注释或让重试复用 key，以 openapi.yaml 语义为准；`createReportSnapshot` 发送 `{ scope }` 但 openapi.yaml 未为该操作定义 requestBody——客户端代码对齐 openapi.yaml。若 openapi 本身需要变更，STOP 并出 CONTRACT-CHANGE-NEEDED 报告。

### PR-1 延后项中本 PR 必须落地的项

- `App.tsx` `load` 依赖 `theme`，切换主题会重新查询——serve 接线前修复。

### 不在本 PR 的 PR-1 延后项（保持登记在原任务记录）

- test_panel_manifest.py 未纳入 run_ci.py；CI 重建检查失败不打印 diff；派生链测试为子串匹配。本 PR 的 serve 测试沿用同一惯例（不经 run_ci.py，由 CI dashboard job 执行）。

## 非目标

R2.0b／R2.0c／R2.1a/b／R2.2 全部；PRD 正文修改；契约（openapi.yaml／panel-manifest*／ADR 0002 决策）修改；跨平台与安全证据（R2.2）；push 与开 PR。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-19T17:55:28+08:00 | planned | in-progress | PR-2 任务记录建立；事实源通读完成；首个 commit 为回填＋PR-1 记录修正（docs only） | 本文件「事实源」；Lead 指派消息 |
