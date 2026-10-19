---
schema_version: 1
id: v2.1.0-rc.2-r2.0a-dashboard
workflow_mode: strict
mode_source: user
mode_note: Lead 本次明确指派 strict 模式 SBTD 任务；范围严格等于 plan.md R2.0a 行的锁定决定与验收，非目标含 R2.0b（含轮询）、R2.0c、R2.1a/b、R2.2 证据；Lead 附加 SIZE GATE——通读事实源后判定 R2.0a 超出一个可审 PR 时，只做回填 commit 并在本文件写拆分提案，不开始实现。
status: "in_progress"
branch: feat/v2.1.0-rc.2-r2.0a-dashboard
created_at: '2026-10-19T13:30:05+08:00'
updated_at: '2026-10-19T13:30:05+08:00'
completed_at: null
---

R2.0a：OMP 风格单页 Dashboard 骨架、Panel registry（`contracts/panel-manifest.json` 单一事实源）、ReportDocument、`serve` 启动与访问控制（D5–D8）。底座为 R1 已验收库面（main `a55117c`：`stats_query`／`csv_export`／`report_snapshot`／`facade` 等），真实 API／数据路径，不用 mock 数字冒充真实接口（PRD §15.0）。

## 事实源（已通读）

- `ai/tasks/v2.1.0-rc.2-plan/plan.md`（R2.0a 行与「各行锁定决定与验收 › R2.0a」）
- `ai/tasks/v2.1.0-rc.2-plan/grill-r1.md`（锁定决定 D1–D17 与 DDD 初稿：Local Server & Access Control、Renderer Isolation、Query & Snapshot 上下文与不变量）
- `docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md`（§10.4、§12.4 十三 Panel、§13.3 ReportDocument、§13.4）
- `docs/adr/0001-v2.1.0-rc.1-r1.0-runtime-decisions.md`（§2 Starlette+uvicorn、§5 一次性配对换 session／Bearer、loopback＋Host/Origin＋CSRF）
- R1 现状：`sbtd-runtime/` 纯 Python 库面（无 HTTP 服务，`test_golden_contracts…test_runtime_package_does_not_import_a_server` 钉住）、`sbtd-runtime/contracts/`（openapi.yaml、metrics-catalog.json 机器可读契约先例）、`sbtd-runtime/tests/test_golden_contracts.py`（golden 钉测惯例）；仓内无 npm 工具链。

## 范围（等于 plan.md R2.0a 验收，不扩项）

- D1：前端构建产物入仓 `sbtd-runtime/dashboard/static/`；CI 检查源码重建产物与入仓产物逐字节一致。
- D2：Vite 钉精确版本＋lockfile 入仓＋CI `npm ci`＋依赖审计。
- D14：`contracts/panel-manifest.json`（schema 版本化）为 Panel 单一事实源；golden 钉测（仿 `test_golden_contracts`）；前端注册表与 ReportDocument 均由 manifest 派生。
- D17：仅参考 OMP 视觉语言、零代码／零资源复制；设计规格把 OMP 参考点写成自有 token 定义。
- Local Server & Access Control：D5（端口占用即失败并提示 `--port`）、D6（前台 Ctrl-C、默认 `--open`、实例锁＋端口双判、陈旧锁按无效处理）、D7（一次性 ticket 经 URL fragment 配对换 session／Bearer、读后即毁、不进日志、终端不打印）、D8（Host／Origin 严格白名单硬编码）。实现＋单测在本任务；跨平台与安全证据属 R2.2。
- 新 ADR（`docs/adr/` 下一编号 0002）：固定产物体积预算、npm 审计基线、`#ticket` URL 出现在浏览器启动命令行参数的风险与缓解（终端不打印、ticket 短时一次性）及残余风险。

## 非目标

R2.0b 筛选／数据质量／页内详情（含 30 秒轮询，Lead 明确排除）；R2.0c 快照落盘；R2.1a/b 导出与 renderer；R2.2 跨平台 E2E 与安全证据；PRD 正文修改。

## 验收（plan.md R2.0a 行原文）

Panel manifest schema 版本化并有 golden 钉测（仿 `test_golden_contracts`）；前端注册表与 ReportDocument 均由 manifest 派生；源码重建产物与入仓产物逐字节一致的 CI 检查通过；设计规格把 OMP 参考点写成自有 token 定义；产物体积预算与 npm 审计基线由本任务 ADR 固定；`serve` 按 D5–D8 实现启动、实例锁、配对与 Host／Origin 校验（本任务出实现与单测，`#ticket` URL 命令行参数可见风险与缓解写入本任务 ADR），跨平台与安全证据由 R2.2 统一产出。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-19T13:30:05+08:00 | planned | in-progress | 任务记录建立；开始通读事实源（plan.md、grill-r1.md、PRD §10.4/§12.4/§13、ADR 0001、R1 代码与测试惯例），随后按 Lead SIZE GATE 评估单 PR 可审性 | ai/tasks/v2.1.0-rc.2-plan/plan.md；ai/tasks/v2.1.0-rc.2-plan/grill-r1.md；docs/adr/0001-v2.1.0-rc.1-r1.0-runtime-decisions.md；sbtd-runtime/tests/test_golden_contracts.py |

## 验证证据

（随进展记录每条验证命令与结果；当前仅事实源通读与 SIZE GATE 评估，无代码改动。）
