---
schema_version: 1
id: v2.1.0-rc.2-r2.0a-serve
workflow_mode: strict
mode_source: user
mode_note: Lead 本次明确指派 strict 模式 SBTD 任务；范围严格等于 plan.md R2.0a 行的 PR-2 段（serve 启动与访问控制 D5–D8 实现＋单测、Reviewy #142 CLEAN review 的 PR-2 项、PR-1 延后项中 serve 接线前必须落地的项）。硬边界（condition c）：不得变更 contracts/panel-manifest.json、panel-manifest.schema.json、ADR 0002 任何决策、openapi.yaml 或任何其他契约；契约变更不可避时停下并出 CONTRACT-CHANGE-NEEDED 报告。plan.md R2.0a 行在 PR-2 合并前不标 done。显式 git add 路径；不纳入 .omp-r12b-addendum.txt 与 ai/tasks/codex-verify/；不 push、不开 PR。
status: "done"
blocked_reason: null
branch: feat/v2.1.0-rc.2-r2.0a-serve
created_at: '2026-10-19T17:55:28+08:00'
updated_at: '2026-10-19T22:31:04+08:00'
completed_at: '2026-10-19T22:27:23+08:00'
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

## 实现记录（2026-10-19）

### 结构

- `sbtd-runtime/serve.py`：CLI（`PYTHONPATH=sbtd-runtime python3 -m serve [--port] [--open/--no-open] [--home]`）、Starlette＋uvicorn 应用、SecurityMiddleware（Host/Origin→auth→CSRF）、路由 `/api/v1/health`（bare Health，免会话）、`/api/v1/session/pair`、`/api/v1/metrics/catalog`、`/api/v1/statistics/query`、`/api/v1/report-snapshots/{id}`（＋`/dataset`）、`/` 静态产物（StaticFiles html=True，防穿越）。数据面每次查询经 `load_dataset(home)` 从 `EventStore`（read_only）重放真实事件；tasks 表由 `task.created` 事件 scope 派生，事件 schema 无 role 字段故不伪造 role（evaluate 对无 role 任务按 leaf 处理，与运行时 executable-leaf 观察范围一致）。审计库不可用时数据集为空且 Envelope meta 带 `AUDIT_STORE_UNAVAILABLE:*` warning＋complete=false，不编造数字。
- 契约对齐事实：openapi.yaml 的 `createReportSnapshot` 无 requestBody，故客户端不向该端点发 body；快照由服务端 SnapshotStore 挂在 `stats_query.query`（`_attach_snapshot`）上随查询生成，`snapshot_id` 随响应返回，客户端再 GET `/api/v1/report-snapshots/{id}` 取 `public_view` 构建 ReportDocument。Session schema 仅 `token_type/access_token/expires_in`（additionalProperties false），CSRF token 经 `X-CSRF-Token` 响应头下发。
- D5：lock 之后独立 `socket.bind` 双判；占用 → stderr「端口 N 已被占用，启动失败；请使用 --port 指定其他端口」，exit 2。
- D6：`$SBTD_RUNTIME_HOME/serve.lock`（O_EXCL，0600，{pid,port,started_at}）；活 pid（`os.kill(pid,0)`，EPERM 按活处理）→ 报已有实例 exit 2；死 pid／不可读／损坏 → 陈旧锁删除重试一次；前台 uvicorn，SIGINT 干净退出 rc=0 并释放锁。
- D7：ticket=`secrets.token_urlsafe(32)`，TTL 300s，任何 pair 尝试读后即毁；默认 `--open` 经 `webbrowser.open("http://127.0.0.1:PORT/#ticket=…")`；`--no-open` 或打开失败写 `pairing-ticket`（0600）并只打印文件路径；uvicorn `access_log=False`＋log_level=warning；终端输出只含无 ticket 的基础 URL。
- D8：`ALLOWED_HOSTNAMES = {localhost, 127.0.0.1, ::1}` 硬编码；Host 必须主机在白名单且端口相等（无端口即拒）；Origin 存在时必须 `http://<白名单主机>:<服务端口>` 全匹配（scheme≠http 拒）；403 body 不泄露策略细节。
- 钉法更新：`test_runtime_package_does_not_import_a_server` → `test_library_modules_do_not_import_the_server_layer`（11 个 R1 库面模块不得含 starlette／uvicorn 字样）；r1.4 spec／report 两处引用已加注。
- 依赖：`sbtd-runtime/requirements-serve.txt` 精确钉版 `jsonschema==4.26.0`（库面 event_store／contract_eval 既有依赖，补钉使该文件可独立安装）、`starlette==1.9.0`、`uvicorn==0.54.0`；CI dashboard-artifacts job 新增安装＋`test_serve.py` 步骤。

### 前端（Reviewy #142 PR-2 项＋延后项）

- Reviewy 项 1：PanelCard 渲染 `conditional`／`partial`（missing=true）／非 decidable `sample_status` 标记 chip；`strata` 存在即逐层渲染（stratum value 或 unknown＋sample_status）；任意嵌套深度 null/undefined → `unknown`，绝不显示 "null"；`[object Object]` 不存在。
- Reviewy 项 3：`createReportSnapshot(scope)` 删除（其「retry 去重」注释随函数移除——openapi 语义下每次调用新 Idempotency-Key 本就不去重，修复方式是对齐契约而非保留错误注释）；新增 `fetchReportSnapshot(snapshotId)`（GET，契约内）与 pairing API（`readTicketFromFragment`／`clearTicketFromAddressBar`／`pairWithTicket`，pair 成功存 sessionStorage）。
- 延后项：`App.tsx` `load` 不再依赖 `theme`——快照与 values 入 state，ReportDocument 由 `useMemo([state, theme])` 派生，切主题零请求。
- 页面 bootstrap：有 `#ticket=` → 立即 replaceState 清地址栏与历史（§10.2）→ pair → 查询；无 ticket 无 session → 诚实「未配对」错误态，不带着 401 查询。

## 验证证据（全部实际执行）

- **serve 单测（D5–D8，真实进程／socket，无 mock 顶替被测行为）**：`PYTHONPATH=sbtd-runtime python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_serve.py'` → Ran 14 tests OK。覆盖：端口占用 rc=2＋--port 提示（D5）；同 home 第二实例报「已有实例」rc=2、死 pid 陈旧锁与损坏锁均按无效处理启动成功、Ctrl-C（SIGINT）rc=0 且锁文件移除（D6）；0600 ticket 文件、pair 200 得 bearer＋X-CSRF-Token 头、同 ticket 二次 401、错 ticket 401 且正确 ticket 随之失效（读后即毁）、ticket 不出现在进程 stdout/stderr（D7）；Host 外部域名／错误端口／`127.0.0.1.evil.com`（DNS rebinding）／无端口均 403，localhost／127.0.0.1＋正确端口 200，Origin 外部／https scheme／错端口 403、全匹配 200，静态路径同样受 Host 约束（D8）；无 bearer 401、缺／错 CSRF 403、无效 scope 400 不静默默认；`/` 与 `/assets/*` 200 且穿越（`/../../`、`/%2e%2e/`）404；HTTP 查询结果与库面 `stats_query.query` 在同一 golden 种子事件上逐指标相等，snapshot_id 可 GET 取回、未知 id 404。
- **sbtd-runtime 全套**：`PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py'` → Ran 242 tests OK（228 基线＋14 serve）。
- **lint／typecheck／构建**：`ruff format --check`、`ruff check`（serve.py、test_serve.py 全过；test_golden_contracts.py 的 I001 为仓内既有惯例未动）；`python3 -m compileall` 过；`npm run build`（tsc --noEmit＋vite build）过。
- **逐字节重建**：连续两次 `npm run build` 后 `find static -type f | sort | xargs sha256sum` diff 为空 → BYTE_IDENTICAL_OK。
- **体积**：`python3 sbtd-runtime/dashboard/check_artifacts.py` → OK: 3 files, 241,853 bytes（预算 524,288；最大单文件 `assets/index-DkNm3QhB.js` 236,927／预算 409,600）。
- **npm audit**：`npm audit --audit-level=high` → found 0 vulnerabilities。

### 真实冒烟（本机，2026-10-19 晚，命令与结果）

- 种子：`EventStore.open(confirmed=True)` 向 `/tmp/smoke-home` 追加 golden 64 事件（61 accepted／2 duplicate／1 conflict，真实去重路径）；后追加 9 条改时间戳至当前 24h 窗口的 usage／validation 事件（9 accepted）。
- 启动：`PYTHONPATH=sbtd-runtime python3 -B -m serve --port 16400 --no-open --home /tmp/smoke-home` → 终端输出仅「未自动打开浏览器；配对 ticket 已写入 /tmp/smoke-home/pairing-ticket（0600）…」与「SBTD Runtime Dashboard: http://127.0.0.1:16400/ （Ctrl-C 退出）」，无 ticket。
- D6 锁：第二实例同 home+port → stderr「已有 sbtd-runtime serve 实例在运行（pid 303266，端口 16400）；如需另起实例请使用 --port…」rc=2。D5 双判：另一 home 同 port →「端口 16400 已被占用，启动失败；请使用 --port 指定其他端口」rc=2（且未留下锁文件）。
- D7：`stat -c %a pairing-ticket` → 600；curl pair #1 → 200 `{token_type:bearer, access_token:…, expires_in:28800}`＋`x-csrf-token` 响应头；pair #2 同 ticket → 401。
- D8：`Host: evil.com:16400`／`127.0.0.1:9999`／`127.0.0.1.evil.com:16400` → 403；`Origin: http://evil.com:16400` → 403、`Origin: http://127.0.0.1:16400` → 200；无 bearer → 401；bearer 缺 CSRF POST → 403。
- 静态：`GET /` → 200 index.html；`GET /assets/<file>` → 200 字节数等于入仓文件；`--path-as-is /../../contracts/openapi.yaml` 与 `/%2e%2e/%2e%2e/...` → 404。
- 真实查询：POST statistics/query（golden 窗口）→ `tasks.touched.value=4`、`usage.tokens` conditional、value 含 `cache_read_tokens: null`；响应 `snapshot_id` 经 GET 取回 `as_of`／`watermark_seq=20002`。
- Ctrl-C：SIGINT → 进程退出、serve.lock 移除、端口释放（后续新实例可同端口启动）。
- ticket TTL（意外实测）：三次浏览器 pair 因超过 300s TTL 得 401——过期拒绝路径真实生效；随后重启后 5 分钟内 pair 成功（200）。
- **UI 冒烟（Playwright，真 serve＋真种子数据）**：`http://127.0.0.1:16400/#ticket=…` 打开 → pair 200、fragment 从地址栏消失（`location.hash` 为空）、sessionStorage 有会话、水位行显示真实 `as_of`（2026-10-19T11:40:19Z）、13 Panel 渲染。对 R1 golden 形状逐条核对：`usage.tokens` →「input_tokens 10、output_tokens 5、cache_read_tokens unknown、reasoning_tokens 2」＋conditional＋partial chip；`usage.cost_reported` → unknown＋conditional＋partial；`validations.run_pass_rate` → unknown＋strata「narrow 1/2」「full-stack unknown（no-decidable-sample）」；`tests.final_result_distribution` →「failed 1、passed 2」；unsupported 显示「不支持 — outside-v2.1.0-rc.1-core-subset」；全页 `null` 出现 0 次、无 `[object Object]`。主题切浅色 `#f5f7fa` 再切回深色 `#14171c`，两次切换 API 请求数为零增量（network 面板核对：pair 1 次、statistics/query 每次加载 1 次、主题切换无新请求）——延后项「load 依赖 theme」修复验证通过。冒烟后进程 SIGINT、临时 home 与 `.playwright-mcp/` 已清理。
- **全仓套件**：`python3 -B tests/run_ci.py --platform linux --output /tmp/rc2-pr2-ci` → Ran 2349 tests，FAILED (failures=1, skipped=62)。唯一失败 `test_sbtd_probe_links.MaterializeAuthorizationTests.test_link_text_change_is_refused`（L867 'link-mismatch' != 'identity-mismatch'）——issue #143 已登记的基线不稳定项，失败签名与 PR-1 记录的基线复跑一致，本 PR 未触碰该链路，不修。报告原件 `/tmp/rc2-pr2-ci/linux-1.{json,md}`（runner 临时目录，非归档）。

## CONTRACT-CHANGE-NEEDED

无。openapi.yaml、panel-manifest.json／schema、ADR 0002 决策均未变更；`createReportSnapshot` 的 requestBody 差异按契约对齐客户端（删 body、改走 query 附着 snapshot_id＋GET）解决，未触契约。

## 已知边界（如实声明）

- serve 测试不经 run_ci.py（沿用 PR-1 对 test_panel_manifest 的同一惯例，由 CI dashboard-artifacts job 执行）；该 PR-1 延后项本 PR 不修。
- Windows 上 `os.kill(pid, 0)` 的活 pid 判定语义未验证；跨平台与安全证据属 R2.2。
- 实例锁按 runtime home 粒度（同 home 第二实例无论端口均拒），与 D6「实例锁＋端口双判」一致。
- 审计库不可用时指标为真空集计算结果＋Envelope warning（complete=false）；页面级数据质量细化属 R2.0b。

## 模型使用证据（models-used，Lord 2026-10-19 ~22:27 +08:00 指令回填）

| 用途 | 模型 | 调用次数 |
|---|---|---|
| 实现（implement：PR-2 serve＋前端修复＋单测＋docs 各 commit） | `kimi-code/k3:high` | unknown（未记录） |
| 基线数字 commit（baseline numbers：回填＋PR-1 记录修正中的基线复跑数字） | `openai-codex/gpt-6-astra:high` | unknown（未记录） |

调用次数无原始记录可考，如实标 unknown，不补造。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-19T17:55:28+08:00 | planned | in-progress | PR-2 任务记录建立；事实源通读完成；首个 commit 为回填＋PR-1 记录修正（docs only） | 本文件「事实源」；Lead 指派消息 |
| 2026-10-19T20:28:16+08:00 | in-progress | in-progress | PR-2 实现完成：commit 1 回填＋修正（c0bbc4e）、前端修复＋产物（e708901）、serve＋单测＋CI＋钉法（bb52bf8）；serve 单测 14 OK、sbtd-runtime 全套 242 OK、逐字节重建 OK、体积 241,853≤524,288、npm audit 0、真实冒烟（D5–D8＋UI＋golden 形状）全部通过；证据见「验证证据」 | 本文件「验证证据」；commits c0bbc4e/e708901/bb52bf8 |
| 2026-10-19T20:58:16+08:00 | in-progress | in-progress | 收尾验证完成：docs（install-and-use serve 节）＋requirements-serve 补钉 jsonschema（d580ad9）；全仓 `run_ci.py --platform linux` 2349 tests、唯一失败为 issue #143 已知 test_sbtd_probe_links 不稳定项（签名与基线一致）；任务当时保持 in-progress 至本 PR 合并（plan.md R2.0a 行同理）；当时未 push、未开 PR——随后已开为 PR #144 并于 2026-10-19T22:27:23+08:00 squash-merge 入 main（merge SHA `8178b26abe75454b958d096ff58522eda7facbb4`），见下一条状态事件 | /tmp/rc2-pr2-ci/linux-1.json；commit d580ad9 |
| 2026-10-19T22:31:04+08:00 | in-progress | done | PR #144 已 squash-merge 入 main：merge SHA `8178b26abe75454b958d096ff58522eda7facbb4`，完成时间 2026-10-19T22:27:23+08:00（CLEAN tip `d9c5e58`）；plan.md R2.0a 行同步记 done；本事件为 docs-only 回填，不改代码、不重建产物 | PR #144；merge commit 8178b26abe75454b958d096ff58522eda7facbb4；ai/tasks/v2.1.0-rc.2-plan/plan.md R2.0a 行 |
