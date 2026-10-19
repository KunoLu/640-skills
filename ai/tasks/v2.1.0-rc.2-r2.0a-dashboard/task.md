---
schema_version: 1
id: v2.1.0-rc.2-r2.0a-dashboard
workflow_mode: strict
mode_source: user
mode_note: Lead 本次明确指派 strict 模式 SBTD 任务；范围严格等于 plan.md R2.0a 行的锁定决定与验收，非目标含 R2.0b（含轮询）、R2.0c、R2.1a/b、R2.2 证据；Lead 附加 SIZE GATE——通读事实源后判定 R2.0a 超出一个可审 PR 时，只做回填 commit 并在本文件写拆分提案，不开始实现。
status: "done"
blocked_reason: null
branch: feat/v2.1.0-rc.2-r2.0a-dashboard
created_at: '2026-10-19T13:30:05+08:00'
updated_at: '2026-10-19T22:31:04+08:00'
completed_at: '2026-10-19T22:27:23+08:00'
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
| 2026-10-19T13:46:11+08:00 | blocked | in-progress | 用户 2026-10-19 13:40 +08:00 决定「按建议拆」：采纳 PR-1／PR-2 拆分（提案第 1、3 项按推荐执行——PR-1 先行，ADR 0002 归属 PR-1）；本轮只实现 PR-1，验收归属与 PR 边界见「拆分决定」一节 | 用户决定「按建议拆」（2026-10-19 13:40 +08:00）；本文件「拆分决定」一节 |
| 2026-10-19T16:16:29+08:00 | in-progress | in-progress | PR-1 开为 PR #142（分支 feat/v2.1.0-rc.2-r2.0a-dashboard，tip `6f600c6`）；同步修正本文件 PR-1 状态表述（原「未推送、未开 PR」）与验证证据 tip 表述（原 735559b）；更正 test_sbtd_probe_links 措辞——真实复跑数据：a55117c 16/11/2、6f600c6 18/12/3 失败，两侧同因且均不稳定，登记 issue #143 由 R2.0a 后 chore PR 处理；延后项登记见「评审第一轮修复 › 延后非阻塞项」 | PR #142；issue #143；日志 ~/.omp/logs/640-rc2-r2.0a/probe/ |
| 2026-10-19T16:16:29+08:00 | in-progress | in-progress | 评审第一轮修复完成（Reviewy blockers B1/B2＋Codex P1/P2 与 Reviewy C1–C4）：manifest 内容 sha256＋manifest_version 配对锁定、panel-manifest JSON schema＋jsonschema 正负例、api.ts 按 openapi QueryScope／Envelope／Idempotency-Key 对齐、PanelCard 按 value＋support 形状渲染；全部验证通过，证据见「评审第一轮修复」一节；任务按拆分决定保持 in-progress 至 PR-2 合并 | 见「评审第一轮修复」验证证据（命令＋结果、mutation 表、逐字节重建、体积、审计、测试计数） |
| 2026-10-19T16:34:21+08:00 | in-progress | in-progress | B2 跟进（Reviewy／Lord 于房间要求）：测试内完成 schema 绑定——`SCHEMA_BY_VERSION = {"1.0": contracts/panel-manifest.schema.json}`，正向校验测试按 `manifest["schema_version"]` 查映射、无映射即失败（不 skip）；schema 保持 const "1.0"，manifest 不变（仍无 `$schema` 键）；新增负例——schema_version 置 "1.1"／"2.0" 的深拷贝对映射的 1.0 schema 抛 jsonschema.ValidationError 且查映射无该版本。测试计数：test_panel_manifest.py Ran 21 tests OK（20→21）；sbtd-runtime 全套 `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py'` → Ran 228 tests OK（227→228） | 本事件同 commit「test(r2.0a): bind panel manifest schema_version to its schema and reject wrong versions」；sbtd-runtime/tests/test_panel_manifest.py |
| 2026-10-19T17:55:28+08:00 | in-progress | in-progress | PR-1 已 squash-merge：PR #142 → main merge SHA `3c9cf4e`，完成时间 2026-10-19T17:32:13+08:00；按拆分决定只追加本事件，plan.md R2.0a 行保持 in_progress 至 PR-2 合并；PR-2 任务记录建立于 ai/tasks/v2.1.0-rc.2-r2.0a-serve/task.md，分支 feat/v2.1.0-rc.2-r2.0a-serve | PR #142；merge commit 3c9cf4e；ai/tasks/v2.1.0-rc.2-r2.0a-serve/task.md |
| 2026-10-19T22:31:04+08:00 | in-progress | done | PR-2 已 squash-merge：PR #144 → main merge SHA `8178b26abe75454b958d096ff58522eda7facbb4`，完成时间 2026-10-19T22:27:23+08:00（CLEAN tip `d9c5e58`）；按拆分决定「本任务保持 in-progress 直到 PR-2 合并」条件已满足，本任务记 done；plan.md R2.0a 行同步记 done；本事件为 docs-only 回填 | PR #144；merge commit 8178b26abe75454b958d096ff58522eda7facbb4；ai/tasks/v2.1.0-rc.2-plan/plan.md R2.0a 行 |

## 拆分决定（用户 2026-10-19 13:40 +08:00「按建议拆」）

用户批准按「SIZE GATE 拆分提案」拆为 PR-1 → PR-2。**本轮只实现 PR-1。**

### plan.md 行归属

- plan.md R2.0a 保持单行，不拆行；只有在 **PR-2 合并后**该行才记 done。
- PR-1 合并只在本文件追加一条状态事件（不改 plan.md 行状态）。
- PR-2 的第一个 commit 回填 PR-1 的 PR 号、merge SHA 与完成时间（沿用 plan.md「每个 PR 的第一个 commit 回填上一行」规则，此处上一行即 R2.0a 的 PR-1 段）。

### 验收项归属（逐项）

| 验收项（plan.md R2.0a 行） | 归属 |
|---|---|
| Panel manifest schema 版本化＋golden 钉测（仿 `test_golden_contracts`） | **PR-1** |
| 前端注册表与 ReportDocument 均由 manifest 派生 | **PR-1** |
| 源码重建产物与入仓产物逐字节一致的 CI 检查 | **PR-1** |
| 设计规格把 OMP 参考点写成自有 token 定义（D17） | **PR-1** |
| 产物体积预算与 npm 审计基线由本任务 ADR 固定 | **PR-1**（ADR 0002 全文，含 `#ticket` 风险／缓解／残余风险） |
| `serve` 按 D5–D8 实现启动、实例锁、配对与 Host／Origin 校验＋单测 | **PR-2** |

`#ticket` 风险拆分：**ADR 0002 完整文本（风险、缓解、残余风险）落在 PR-1**；把缓解措施落实为代码（终端不打印 ticket、ticket 短时一次性）属 **PR-2** 实现。

### PR 边界（硬性）

- **PR-1 不含任何 serve 代码**，也不含 Python 侧 serve 的 stub／壳（`test_runtime_package_does_not_import_a_server` 钉法保持不动）。
- **PR-2 不得变更 PR-1 定下的 manifest schema 与 ADR 0002 决策**；任何变更须单独提出，不随 PR-2 夹带。

### PR-1 当前状态（2026-10-19 17:55 +08:00 更新）

PR-1 实现完成、全部验证通过（见「验证证据 › PR-1 实现验证」），commits `0c20db4`（feat）、`adb229d`（ADR 0002）、`735559b`（CI job），随后追加验证记录 commit `6f600c6`；PR-1 以 tip `6f600c6` 开为 PR #142，**已于 2026-10-19T17:32:13+08:00 squash-merge 入 main（merge SHA `3c9cf4e`）**。按拆分决定：本任务保持 in-progress 直到 PR-2 合并；PR-2 任务记录为 `ai/tasks/v2.1.0-rc.2-r2.0a-serve/task.md`。

## SIZE GATE 拆分提案（2026-10-19，已按用户 13:40 决定采纳）

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

### PR-1 实现验证（2026-10-19，验证时 tip `735559b`；其后追加 docs commit `6f600c6` 为 PR #142 tip）

- **拆分决定记录**：commit `90b45ba docs(r2.0a): record split decision, acceptance ownership and PR boundaries`。
- **新钉测**：`PYTHONPATH=sbtd-runtime python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_panel_manifest.py'` → Ran 13 tests, OK。
- **sbtd-runtime 全套**：`PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py'` → Ran 220 tests, OK（基线 207 ＋ 新增 13；AC-32 库面无服务钉测不受影响——PR-1 无 serve 代码）。
- **lint／typecheck**：`ruff format --check` 与 `ruff check`（test_panel_manifest.py、check_artifacts.py）→ 全过；`python3 -m compileall` 通过；`tsc --noEmit` 随 `npm run build` 通过。
- **npm ci ＋ 构建**：干净 `rm -rf node_modules && npm ci`（70 包）后 `npm run build` 成功（vite 6.4.4，36 modules）。
- **逐字节重建（D1）**：`npm ci` 干净重建前后 `find static -type f | sort | xargs sha256sum` diff 为空 → BYTE_IDENTICAL_OK；CI `dashboard-artifacts` job 以「重建后 `git status --porcelain` 为空」钉住同一性质。
- **产物体积（ADR 0002 §1）**：`python3 sbtd-runtime/dashboard/check_artifacts.py` → OK: 3 files, 241,853 bytes（预算 524,288；最大单文件 236,927／预算 409,600）。【更正 2026-10-19：此处原记 237,933／233,356 为评审第一轮修复前实测，基线应以合并态为准，见「评审第一轮修复」与本条更正】
- **npm 审计基线（ADR 0002 §2）**：`npm audit --audit-level=high` → found 0 vulnerabilities（vite 5.4.21 原带 1 high＋1 moderate，改钉 6.4.4 清零，plugin-react 4.7.0 声明兼容 ^6.0.0）。
- **UI 冒烟**：`python3 -m http.server` 服务 `static/`，Playwright 实测：13 个 Panel 全部按 manifest 顺序渲染（region 数=13，`panelCount: 13`）；API 不可达时所有 Panel 显示「查询失败…错误不显示 0」而非 0（§12.5）；主题切换深 `#14171c` ↔ 浅 `#f5f7fa` 双向生效并持久化 localStorage；时间范围 24h 激活、7d/30d/自定义 disabled（R2.0b 边界）；导出四键 disabled（R2.1a 边界）；水位行显示「未知（尚未取得快照）」。冒烟后服务器与 `.playwright-mcp/` 已清理。
- **全仓套件**：`python3 -B tests/run_ci.py --platform linux` → 2349 tests，FAILED (failures=1, skipped=66)。唯一失败为 `test_sbtd_probe_links.MaterializeAuthorizationTests` 内用例。**预先存在的环境相关失败，与 PR-1 无关**；本 PR 未触碰 `sbtd_probe_links` 及其脚本链路。**措辞更正（2026-10-19）**：此前所写「单测独立运行通过」「基线失败 3 条」不准确。真实数据（2026-10-19，`python3 -B -m unittest tests.test_sbtd_probe_links.MaterializeAuthorizationTests` 各独立运行 20 次）：基线 `a55117c` 对 test_replaced_link_with_identical_text_is_refused／test_link_text_change_is_refused／test_link_swap_during_copy_is_refused_after_copy 三用例分别失败 16／11／2 次，`6f600c6`（PR #142 tip）分别失败 18／12／3 次；两侧失败原因相同（L878 ContractError not raised；L867 'link-mismatch' != 'identity-mismatch'），两个 SHA 上均不稳定。已登记 issue #143，由 R2.0a 之后的 chore PR 处理；运行日志在 `~/.omp/logs/640-rc2-r2.0a/probe/`。

### 拆分决定前（SIZE GATE 阶段）

- `git status --short`／`git log --oneline -3`：分支 feat/v2.1.0-rc.2-r2.0a-dashboard 基于 main a55117c；仅 `.omp-r12b-addendum.txt` 与 `ai/tasks/codex-verify/` 两个既有未跟踪项，未纳入任何 commit（PR-1 各 commit 同样保持排除）。
- 事实源通读：plan.md、grill-r1.md、PRD §10.4/§12.4/§13.3–13.4、ADR 0001 全文；R1 现状经 `sbtd-runtime/` 目录、`test_golden_contracts.py`、openapi.yaml 摘要核对（纯库面、无 npm 链）。
- 工具链核查：`node v22.20.0`、`npm 10.9.3` 可用；Python 3.13.5（CI 钉 3.12.10，ADR 0001 §2）。
- 回填 commit：`a858f96 docs(plan): backfill task 0 (#141 a55117c) and start R2.0a`（plan.md 第 0 行 done＋R2.0a in_progress、plan task.md done＋状态事件、本任务记录建立）。
- DDIA Data Design Review（strict gate，manifest 契约触发）：confirmed——panel-manifest.json 为 Panel 单一事实源，构建期内联＋逐字节重建 CI 保证产物与契约不漂移，schema_version／manifest_version 双针，metric_id 参照完整性由钉测对 metrics-catalog.json 校验。

## 评审第一轮修复（PR #142 review round 1，2026-10-19）

范围严格等于评审项：Reviewy blockers B1/B2、Codex P1/P2 与 Reviewy 同文件项 C1–C4；不含 serve 代码与 Python stub（PR-2），不改 ADR 0002 决策，`.omp-r12b-addendum.txt` 与 `ai/tasks/codex-verify/` 保持未跟踪。strict gate：Legacy Change Safety Review＝characterized（red 复现：scratch 中 span 6→12＋未知额外键在旧测试下 13/13 全过）、Refactoring Review＝proceed（no refactor needed）、DDIA Data Design Review＝confirmed、Release Readiness Review＝ready；ponytail-review 一处采纳（删去无消费者的 exported EnvelopeMeta，net −9 行）。

### 修复内容

- **B1（test_panel_manifest.py）**：新增 `test_canonical_content_hash_matches_manifest_version`——对 canonical JSON（sorted keys、compact separators、ensure_ascii=False、UTF-8）的 sha256 与 `manifest_version` 配对锁定（`EXPECTED_MANIFEST_VERSION="1.0.0"` ＋ `EXPECTED_MANIFEST_SHA256=fa9ffa78…878d01`）；任何内容变更（值改、键增删、数组项重排）若不同时更新 `EXPECTED_MANIFEST_SHA256` pin 即失败，失败信息要求两个 pin 一起更新；`manifest_version` 本身的同步 bump 由 code review 强制，测试不机械检查版本号递增。
- **B2（contracts/panel-manifest.schema.json 新增）**：仿 event.schema.json（draft 2020-12、`$id: urn:sbtd:runtime:panel-manifest:1.0`），root 与 panel 级 `additionalProperties: false`、required 全字段、desktop_span enum [6,12]、kind enum [kpi,chart,table]、order integer 1..13、panels minItems=maxItems=13、field_dependencies minItems=1、metric_ids uniqueItems。实例文件不带 `$schema` 指针，沿用仓内 event.schema.json 由测试显式加载的惯例。测试新增 `SchemaValidationTests`（jsonschema 正例＋负例：root 额外键拒、panel 额外键拒、缺 title_zh 拒、空 field_dependencies 拒），`test_required_fields_and_shape` 的子集检查改为精确键集合 `assertEqual(set(panel), REQUIRED_PANEL_FIELDS)`。
- **C1（dashboard/src/api.ts）**：`QueryScope` 严格按 openapi.yaml QueryScope——`{schema_version:"1.0", range:{from,to,timezone}, metrics:string[]}` 必填，`filters`／`task_granularity("executable-leaf"|"all")`／`include_unlinked`／`include_unknown_time` 为全部可选集；删除扁平 from/to 与契约外的 task_uids。`defaultScope24h(metrics, now)` 由调用方传入指标；`registry.ts` 新增 `ALL_METRIC_IDS`（manifest 派生、去重、manifest 顺序），App.tsx 用之。
- **C2（api.ts）**：`/api/v1/statistics/query` 与 `/api/v1/report-snapshots` 解包 Envelope（校验 api_version "1"、request_id、data、meta）取 `data`；畸形 Envelope 抛 ApiError 不静默当空数据；meta.warnings console.warn 浮现；非 2xx 时解析错误体附 request_id／warnings 进 ApiError。`/api/v1/health` 按契约 Health schema 不解包。
- **C3（api.ts）**：`createReportSnapshot` 每次调用以 `crypto.randomUUID()` 发送 `Idempotency-Key` 头（openapi.yaml report-snapshots ~L606-611 必填参数）。
- **C4（PanelCard.tsx）**：按 evaluate() 的 metric value 形状渲染——`support==="unsupported"` 显示「不支持 — reason」；value 为 null/undefined 显示 insufficient_data_zh 不足态（附 reason）；对象值递归渲染为「key value、…」键值对，数组以「、」连接；不再对对象 `String(value)` 出「[object Object]」。无 mock 数据。

### 验证证据（全部实际执行）

- **mutation 表（B1 要求，scratch copy 逐一变异后跑 test_panel_manifest）**：

  | 变异 | 结果 |
  |---|---|
  | M1 span 6→12（task-lifecycle） | 失败 1 测试（hash pin）✓ |
  | M2 title 改动（overview） | 失败 1 测试（hash pin）✓ |
  | M3 kind chart→table（task-lifecycle） | 失败 1 测试（hash pin）✓ |
  | M4 overview metric_ids 6→1 | 失败 1 测试（hash pin）✓ |
  | M5 field_dependencies 置空 | 失败 2 测试（hash pin＋schema minItems）✓ |
  | M6 未知额外 panel 键 | 失败 3 测试（hash pin＋schema additionalProperties＋精确键集合）✓ |

- **manifest 钉测**：`PYTHONPATH=sbtd-runtime python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_panel_manifest.py'` → Ran 21 tests, OK（13→21）。【更正 2026-10-19：原记 20，B2 跟进后实为 21】
- **sbtd-runtime 全套**：`PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py'` → Ran 228 tests, OK（220＋8 新增）。【更正 2026-10-19：原记 227，B2 跟进后实为 228】
- **lint**：`ruff format --check` 通过；`ruff check` 的 I001 与既有 test_golden_contracts.py 完全同型（sys.path 插入后 import jsonschema），属仓内既有惯例，未改；`python3 -m compileall` 通过。
- **type check／构建**：`npm run build`（tsc --noEmit ＋ vite build）通过，36 modules。
- **逐字节重建（钉版工具链，vite 6.4.4 精确钉＋package-lock）**：连续两次 `npm run build` 后 `find static -type f | sort | xargs sha256sum` diff 为空 → BYTE_IDENTICAL_OK。
- **产物体积**：`python3 sbtd-runtime/dashboard/check_artifacts.py` → OK: 3 files, 241,853 bytes（预算 524,288；最大单文件 236,927＜409,600）。
- **npm audit**：`npm audit --audit-level=high` → found 0 vulnerabilities。
- **UI 冒烟（Playwright，本机 http.server 服务新 static/）**：stub fetch 返回契约 Envelope 后切主题触发重查，实测——① C1 线上请求体：`{schema_version:"1.0", range:{from,to,timezone:"Asia/Shanghai"}, metrics:[31 个 manifest 派生 id]}`，无 task_uids、无扁平 from/to；② C3 请求头含 `Idempotency-Key: a706ef76-2323-4903-ab7a-101b2f6f5a96`；③ C2 Envelope 解包生效（水位行显示快照 as_of）；④ C4 渲染：对象值 `tasks.status_at_end` 显示「done 1、unknown 2、in-progress 1」（非 [object Object]），unsupported 显示「不支持 — outside-v2.1.0-rc.1-core-subset」，缺失指标显示「unknown — 未提供 usage 显示不支持／未知，不填 0…」。冒烟后服务器与 `.playwright-mcp/` 已清理。

### 延后非阻塞项（PR-2／后续）

1. **App.tsx load 依赖 theme**：`load` 的 useCallback 依赖 theme，切换主题会重新查询（PR-2 接 serve 前修）。
2. **panel 测试只在 dashboard-artifacts job 跑**：test_panel_manifest.py 未纳入 run_ci.py，仅 CI 该 job 执行。
3. **CI 重建检查失败时不打印 diff**：dashboard-artifacts 的逐字节检查 `test -z "$(git status --porcelain)"` 失败时无 diff 输出。
4. **派生链测试为子串匹配**：DerivationChainTests 用 `assertIn` 子串核对源码引用，非 AST 级校验。
