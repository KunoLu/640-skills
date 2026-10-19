---
schema_version: 1
id: v2.1.0-rc.2-r2.0a-dashboard
workflow_mode: strict
mode_source: user
mode_note: Lead 本次明确指派 strict 模式 SBTD 任务；范围严格等于 plan.md R2.0a 行的锁定决定与验收，非目标含 R2.0b（含轮询）、R2.0c、R2.1a/b、R2.2 证据；Lead 附加 SIZE GATE——通读事实源后判定 R2.0a 超出一个可审 PR 时，只做回填 commit 并在本文件写拆分提案，不开始实现。
status: "blocked"
blocked_reason: "SIZE GATE 命中：通读事实源后判定 R2.0a 超出一个可审 PR（两个不相干领域、两套工具链）。已按 Lead 规则只做回填 commit 并在下文写拆分提案（PR-1 前端骨架＋manifest／registry／ReportDocument＋重建一致 CI＋ADR；PR-2 serve＋访问控制 D5–D8），未开始实现，待组内决定。"
branch: feat/v2.1.0-rc.2-r2.0a-dashboard
created_at: '2026-10-19T13:30:05+08:00'
updated_at: '2026-10-19T13:36:00+08:00'
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
| 2026-10-19T13:36:00+08:00 | in-progress | blocked | SIZE GATE 命中：R2.0a 判定超出一个可审 PR，按 Lead 规则停止于实现前；回填 commit 已完成（a858f96），拆分提案见下文「SIZE GATE 拆分提案」，待组内决定后解除阻塞 | commit a858f96「docs(plan): backfill task 0 (#141 a55117c) and start R2.0a」；本文件「SIZE GATE 拆分提案」 |

## SIZE GATE 拆分提案（2026-10-19，待组内决定）

### 判定依据

通读事实源后，R2.0a 单 PR 将同时包含两个不相干领域、两套工具链：

- **前端／契约／CI 面**：仓内从零引入 npm 工具链（React＋TypeScript＋Vite 精确钉版、lockfile、`npm ci`、依赖审计）；`contracts/panel-manifest.json`（schema 版本化）＋ golden 钉测；前端注册表与 ReportDocument 派生；OMP 风格单页骨架（§12.4 十三 Panel、深浅主题、自有 token 设计规格）；构建产物入仓 `sbtd-runtime/dashboard/static/`＋源码重建逐字节一致 CI；ADR 0002。
- **服务／访问控制面**：从零实现 Starlette＋uvicorn HTTP 层（R1 现为纯库面，`test_runtime_package_does_not_import_a_server` 钉住无服务）；`/api/v1` 路由接 R1 真实库面；静态产物服务；CLI `sbtd-runtime serve`；实例锁＋端口双判＋陈旧锁处理（D6）；端口冲突失败（D5）；一次性 ticket 配对与 session／Bearer（D7）；Host／Origin 严格白名单与 CSRF（D8）；全套单测。

合计预估 40+ 文件、数千行，任一评审者都须同时审 npm 构建链可重复性与本地服务安全语义，超出单个可审 PR。Lead 已预绘同一切分，故按 SIZE GATE 停止。

### PR-1：前端骨架＋Panel manifest／registry／ReportDocument＋重建一致 CI＋ADR

- `sbtd-runtime/dashboard/`：package.json（Vite 精确钉版）、package-lock.json、vite/ts 配置、`src/`（OMP 风格单页骨架、深浅主题、自有 token）、构建产物入仓 `static/`。
- `sbtd-runtime/contracts/panel-manifest.json`（schema 版本化）＋ golden 钉测（仿 `test_golden_contracts`）；前端注册表与 ReportDocument 由 manifest 派生。
- 设计规格文档：OMP 参考点写成自有 token 定义（D17，零复制）。
- CI：`npm ci` 后干净重建，产物与入仓产物逐字节一致检查（D1）；npm 审计基线（D2）。
- `docs/adr/0002-*.md`：产物体积预算、npm 审计基线、`#ticket` URL 命令行参数可见风险与缓解及残余风险（D7 要求随本任务 ADR 固定，先于 PR-2 实现记录决策）。
- 不改任何 R1 库面与现有钉测；无 HTTP 服务行为（AC-32 库面钉测不受影响）。

### PR-2：`serve` 启动与访问控制（D5–D8）

- 依赖 PR-1：静态产物与 manifest 已在仓内可服务。
- Starlette＋uvicorn 应用与 `/api/v1` 路由，接 R1 真实库面（`stats_query`／`report_snapshot`／`csv_export` 等），不用 mock。
- CLI 入口、前台 Ctrl-C、默认 `--open`；实例锁＋端口双判＋陈旧锁按无效处理（D6）；端口占用即失败并提示 `--port`、退出码非零（D5）。
- 一次性 ticket 经 fragment 配对换 session／Bearer、读后即毁、不进日志、终端不打印（D7）；Host／Origin 严格白名单硬编码＋CSRF（D8）。
- 单测覆盖 D5–D8；相应更新 `test_runtime_package_does_not_import_a_server` 的钉法（R2 起允许服务层存在，钉法改为契约层约束）。

### 待组内决定

1. 是否按 PR-1／PR-2 拆分执行（顺序：PR-1 先，PR-2 依赖其入仓产物）。
2. 若组内判定单 PR 可接受，则解除阻塞、本任务直接按完整范围实现。
3. 拆分时 ADR 0002 归属 PR-1（决策先行，ticket 风险条目引用 PR-2 实现），如需改归属请明示。

## 验证证据

- `git status --short`／`git log --oneline -3`：分支 feat/v2.1.0-rc.2-r2.0a-dashboard 基于 main a55117c；仅 `.omp-r12b-addendum.txt` 与 `ai/tasks/codex-verify/` 两个既有未跟踪项，未纳入任何 commit。
- 事实源通读：plan.md、grill-r1.md、PRD §10.4/§12.4/§13.3–13.4、ADR 0001 全文；R1 现状经 `sbtd-runtime/` 目录、`test_golden_contracts.py`、openapi.yaml 摘要核对（纯库面、无 npm 链）。
- 工具链核查：`node v22.20.0`、`npm 10.9.3` 可用；Python 3.13.5（CI 钉 3.12.10，ADR 0001 §2）。
- 回填 commit：`a858f96 docs(plan): backfill task 0 (#141 a55117c) and start R2.0a`（plan.md 第 0 行 done＋R2.0a in_progress、plan task.md done＋状态事件、本任务记录建立）。
- 未开始实现，无测试／lint／构建可跑；现有测试套件未改动，保持绿（未重跑，无代码变更）。
