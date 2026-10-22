---
schema_version: 1
id: v2.1.0-rc.2-r2.1b-renderer
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict；仅指定 worktree 与分支。显式 git add；不 push、不开 PR、不评论、不 merge；不暂存 .omp-r12b-addendum.txt 或 ai/tasks/codex-verify/。冻结 OpenAPI、Panel manifest、ADR 0001–0003、PRD、CSV schema。JPEG/PDF 仅库级实现，HTTP 继续拒绝；契约缺口记录而不停止其余工作。
status: in_progress
blocked_reason: null
branch: feat/v2.1.0-rc.2-r2.1b-renderer
created_at: '2026-10-22T11:12:22+08:00'
updated_at: '2026-10-22T12:17:20.268311+08:00'
completed_at: null
---

# R2.1b：JPEG/PDF 独立 renderer

基线 `8931c35ef1aa4a58d3675b6f8d1a8fead309ed90`（R2.1a #151）。本地验收不代表评审、合并、部署或发布。

## 范围与验收

1. JPEG/PDF 复用 R2.1a 服务端静态 HTML、ExportStore 作业、snapshot pin、原子发布、manifest/digest、24h 保留及启动清扫。
2. Playwright 可选、精确钉版；only-shell Chromium 安装到 `$SBTD_RUNTIME_HOME/browsers/`；依赖清单钉 fonts-noto-cjk，记录实测体积。
3. 每作业子进程与临时 profile；路由拒绝外联和 file；单作业信号量、超时及清理。
4. JPEG 按 §13.5 像素预检、降采样与安全失败；PDF 按 §13.6 可搜索、中日英字体嵌入、长表与页脚。
5. 四格式沿用同一 event-detail exportable/classification 过滤；不改变 derived rows 或 withheld 值。
6. 缺依赖仅 JPEG/PDF 不可用并附原因；HTTP jpeg/pdf 仍 400。
7. 单元、真实浏览器、全量指定回归、真实 runtime snapshot smoke、独立复核及冻结契约检查。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-22T11:12:22+08:00 | planned | in_progress | 用户指定 strict；授权 worktree、分支与基线匹配；建立共享交付记录 | pwd、git status/branch/rev-parse；用户任务 |
| 2026-10-22T12:17:20.268311+08:00 | in_progress | in_progress | Run 1b 从 ceb202e 续接；库级实现、真实 smoke、指定回归与两位独立复核完成。本地验收通过，保留 in_progress 等待 operator 提审／契约后续，不宣称已发布 | runtime-final-full 341／7 skip；renderer-final-full 39／1 Windows skip；contracts 69、OpenAPI 16；smoke-receipt.json；reviewer closure |

## 决策

- 未完整调用 grill-with-docs：用户范围、锁定决定与冻结契约边界明确，不重开需求。
- 后续项 A 已决定（用户 2026-10-22 11:13 +08:00）：保持 #151 行为，仅屏蔽 exportable=false 或 classification != local-metadata 的 event-detail 行；派生 task/run/aggregate 不过滤。四格式共用同一过滤管线，不新增 withheld 值。后续项 B 安装使用说明按此范围回填。
- 配额决定仅登记在 plan，R2.2 才实现。
- 沿用 R2.1a 已记录的 TaskStore catalog/frontmatter 限制，不重跑已知失败、不改 active/ignore；本文件是用户明确要求的共享交付，不声称 helper lifecycle 或自动恢复成功。

## Book Gate Plan

| Gate | 触发事实与阶段 | 本轮结论／证据 |
|---|---|---|
| book-ddd-distilled-modeling | 未重开 grill，无领域规则变更 | not-needed；沿用已锁定 Query & Snapshot / Export / Renderer Isolation 所有权 |
| book-ddia-data-design | 跨进程渲染与持久导出，before-dev | confirmed；固定 HTML 输入，现有 ExportStore 原子发布／pin／恢复；无迁移或重放 |
| book-legacy-change-safety | 既有导出与服务高回归面，before-dev | characterized；before-dev-safety 35 tests，34 passed／1 Windows skip |
| book-refactoring-pass | 既有生产代码修改前 | proceed / normal；无需前置重构，保留过滤和 HTTP 校验；Python LSP 不可用，源码补充调用分析 |
| book-release-readiness | runtime 子进程与可选安装变化，check 后 | ready（仅本次 Linux 库级验收）；指定套件与真实 smoke 通过，两位 reviewer 有效发现关闭；HTTP 开放／跨平台实测／完整 AC-51 仍按授权归后续 |

测试 seam 为用户明确要求的 ExportStore、renderer 隔离／预检、capabilities 与真实 PDF/JPEG。主会话为唯一验证 controller。BDD 沿用 spec 中文正文＋英文关键词，不引入 Gherkin runner。Round 1 未提交场景已复用并修正 A 的状态。

## 验证证据

Run 1 初始检查与 ignore 事实沿用当轮记录。Run 1b 首次只读核对：仅既有未提交 `sbtd-runtime/spec/r2.1b-renderer-scenarios.md`；分支正确，HEAD 为 `ceb202e`。步骤 (a) 未重做；只在指定 worktree 写入。

主会话唯一验证 controller；子代理均未执行测试、lint、formatter 或 build。原始输出 `.txt`、命令／时间／源 SHA `.json` 与同 stem 中文汇总 `.md` 全部保存在 **`/workspace/smoke-r2.1b/`**，不入仓。证据为 `developer-local / dirty / local-only`，不是 CI 或 PR-head 验证；提交后通过 `validated-source-hashes.json` 与 `final-tip.json` 记录代码内容等价绑定，不用旧 HEAD 冒充新代码已运行。

### 最终计划范围

| 命令 | 实际结果 | raw／中文汇总 stem |
|---|---|---|
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py' -v` | 341 tests；334 passed、7 skipped；57.318s | `runtime-final-full` |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. SBTD_RENDERER_TEST_HOME=/workspace/smoke-r2.1b/home /workspace/venv-r2.1b/bin/python -B -m unittest test_browser_renderer test_renderer_integration test_renderer_windows -v` | 39 tests；38 passed、1 Windows skip；22.330s | `renderer-final-full` |
| `python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_runtime_r1_acceptance -v` | 69 passed；0.566s | `contracts-final-full` |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_golden_contracts.OpenApiDraftTests -v` | 16 passed；0.062s | `openapi-final-full` |
| `ruff check --fix` 九个修改 Python 文件，随后 `ruff format --check` 同一范围 | 仅删除最后一个未使用测试 import；0 remaining；9 files already formatted。随后完整套件使用最终文件运行 | `ruff-final-clean`、`ruff-final-clean-format` |
| 独立 venv 安装 `requirements-renderer.txt`、`requirements-serve.txt`，`PLAYWRIGHT_BROWSERS_PATH=…/home/browsers python -m playwright install --only-shell chromium` | 成功；Playwright 1.64.0／shell 156.0.8078.4 revision 1248 | `renderer-pip-install`、`renderer-browser-install` |
| 真实 EventStore→load_dataset→SnapshotStore→ExportStore smoke，非 golden fixture | HTML／CSV／JPEG／PDF ready，下载 SHA-256 匹配 manifest；重新构造 Store 后摘要与到期时间不变 | `runtime-smoke-final`、`smoke-receipt.json` |
| `pdffonts report.pdf`、`pdftotext -layout report.pdf -`、`pdfinfo report.pdf`、`pdftoppm -f 1 -singlefile -png -r 60 report.pdf page-1` | 嵌入 NotoSansCJK 字体、中文／日本語／English 可搜索；A3 横向 12 页；已查看第 1 页 PNG | `pdffonts-final`、`pdftotext-final`、`pdfinfo-final`、`pdf-preview-final` |
| 同一报告注入受控 img／fetch／file 探针的私有 renderer seam smoke | HTTP img／fetch 均 route abort，监听服务 hits=[]；两作业 profile 新鲜、不同且删除；本地文件 canary 不在 PDF 文本 | `route-smoke-final`、`route-abort-log.json` |
| Chromium 原生 file 拒绝诊断 | console 明确 `Not allowed to load local resource`；file iframe 在路由前被拒绝，未伪称它进入 route-abort 列表 | `file-denial` |

系统 Python 的 7 skips：4 个显式未启用的真实浏览器场景＋3 个 Windows 场景；独立 venv 已实际运行前 4 项，剩余 Windows Job Object 原生测试跳过。套件间有重叠，不能把这些数量相加成独立用例数。未运行 Dashboard tests／build-consistency：`dashboard/` 未修改。未运行全仓 workflow 或已知无关 probe_links；指定范围没有未解决的无关失败。

### Smoke 产物与体积

- 最终快照：`snap_dd558322924d46e98f627efdf29f565a`。本轮真实追加 72 条带中日英可见 worktree 字段的新事件；throwaway home 保留上一轮 72 个任务，所以 dataset 含 144 个 task context 行、当前范围 72 个 event 行，未改既有查询语义。
- `/workspace/smoke-r2.1b/report.jpg`：5,971,450 bytes；完整 2880×25494 JPEG；SHA-256 `7a2eba9dc6da16a48ce69acc150d3f5a984493a6e39905fca7efb934b05d7ace`。
- `/workspace/smoke-r2.1b/report.pdf`：737,479 bytes；12 页、1191.12×842.88 pt；SHA-256 `d55afc95df6a5c83779088510de57ed2900ecff71a50466bf2e7ca7dd4034b9e`。
- 同目录 `report.html`、`report.csv`、`page-1.png`、字体／文本原生输出、`route-abort-log.json`、`file-denial.txt` 和 `smoke-receipt.json`。此前成功产物保留为 `before-review-*`。
- `du -sb …/home/browsers`：**290,381,668 bytes，约 277 MiB**；`du -sB1`：291,356,672 bytes。仅 only-shell＋FFmpeg 解压安装，不含 venv／字体。原生安装下载日志为 120 MiB＋2.2 MiB。
- 本机 `fonts-noto-cjk=1:20240730+repack1-1`，SC／JP 均由 fc-match 解析到 NotoSansCJK-Regular.ttc；没有本轮全局字体安装或字体入仓。

### 复核、红绿证据与 BDD

- RendererSecurityReview：最终 `Findings: []`，代码级关闭相对 home、父进程异常泄露、准备预算、信号量取消竞争及 Windows 后代清理发现；明确 Windows 原生证据仍待 R2.2。
- RendererOutputReview：最终 `correct`，confidence 0.85；两个 P3 证据建议已执行：真实 31,999 CSS px→1x 的 SOF 精确 1440×31999；32,001 px 安全失败；PDF 标题／范围／时区／短快照至少出现两次，区别正文与页脚。
- 保留失败原始报告：`renderer-store-tracer-red`（原库拒绝 jpeg）、`browser-unit-red`（新模块尚未实现）、`renderer-focused-first`（错误测试期望 55,555px 可通过，已修正）、`renderer-real-first`（file 路由日志假设错误）、`worker-crash-red`、`security-review-red`、`semaphore-cancellation-red`、`jpeg-width-preflight-red`。后四者对应生产修复及绿例均保留，不删除／覆盖失败证据。
- 实测宽内容探针曾输出 32002×1800，证明不能只把 viewport 1440 代入预检。已测量实际 scrollWidth／scrollHeight，1x 回退后重新测量，并在截图前复检；16001px 宽内容现在完整 1x。
- POSIX 以 `waitid(..., WNOWAIT)` 保留 worker PID 至进程组清理，避免 worker 先退出留下 Chromium，也避免回收 PID 后误杀复用的进程组。Windows 用 Job Object 显式 terminate→等待 ActiveProcesses=0→close，再删除 profile；不以创建进程组标志冒充树所有权。
- Ponytail Review：删除自写递归清理，使用 `shutil.rmtree`；删除冗余 viewport 重设、重复 source-reuse 测试、mock 回声断言、未授权的 32 MB HTML 限制和不可靠 sandbox 探测。保留实际资源所有权／安全校验 seam，不做无关重构。
- Code Readability Review：消费者仍只用 ExportRenderer／ExportStore；Windows 系统结构隔离在小型平台模块；行为断言集中在输出、边界与生命周期。lessons-record 已评估，因果与预防已落于 ADR／代码注释／持久回归，本轮不另建身份或 lesson 库。
- BDD：`traceable`；`sbtd-runtime/spec/r2.1b-renderer-scenarios.md`，中文正文＋英文 Gherkin 关键词；Cross-repo context=`complete`；API Contract=`verified`（冻结格式）；Mock Strategy=`user-approved`（缺依赖／故障／生命周期），真实浏览器与真实 runtime smoke 独立记录。

| 场景 | 持久测试／原生证据 |
|---|---|
| 缺依赖与 HTTP 冻结 | `CapabilityTests`、`FrozenHttpExportTests` |
| 四格式同一 withheld 集合／计数、派生行不变 | `RendererLibraryTests.test_four_formats_withhold_the_same_event_detail`；真实 PDF 文本 omission case |
| 无外联与新 profile | `IsolationTests`、`RealBrowserTests.test_route_abort_fresh_profiles_and_jpeg_2x`；route／file smoke |
| JPEG 长图／降级／超限 | `PreflightTests`、真实 31999／32001／16001-wide case、JPEG SOF／实际产物 |
| PDF 中日英／长表／重复表头／页脚 | `RealBrowserTests.test_pdf_is_searchable_a3_with_embedded_cjk`；pdffonts／pdftotext／page-1 |
| 取消／超时／崩溃清理 | `IsolationTests`；`WindowsJobTests`（本机 skip） |
| 既有存储生命周期复用 | `RendererLibraryTests` 的 pin／digest／restart／sweep cases；真实 Store 重启 smoke |

## 模型使用

| 轮次／用途 | 请求模型 | 实际模型 | assistant messages | 工具调用次数 |
|---|---|---|---|---|
| Run 1 主会话：计划首提交、只读设计；session 01a16197-919f-7482-b4ca-4d8cef45a0e5 | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra | 15 | 52 |
| Run 1 BrowserRenderer：只读研究，无写入 | omp task role | xai-oauth/grok-4.7 | 7 | 18 |
| Run 1 RendererIntegrationTests：只读研究，无写入 | omp task role | xai-oauth/grok-4.7 | 5 | 16 |
| Run 1b 主会话：续接实现、验证、交付 | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra（host 标识） | unknown | unknown |
| Run 1b BrowserImplementation：renderer 与单元／真实浏览器测试 | omp 默认 task role，未显式覆盖 | xai-oauth/grok-4.7 | unknown | unknown |
| Run 1b RendererIntegration：库／HTTP／过滤一致性测试 | omp 默认 task role，未显式覆盖 | xai-oauth/grok-4.7 | unknown | unknown |
| Run 1b RendererSecurityReview：独立只读安全复核及修正闭环 | omp 配置 security-reviewer role | openai-codex/gpt-6-astra | unknown | unknown |
| Run 1b RendererOutputReview：独立只读输出／集成／简化复核 | omp 配置 reviewer role | kimi-code/k3 | unknown | unknown |

Run 1 计数与无 fallback 来自 operator 本轮 resume note；两子代理 resolvedModelIsFallback=false。本轮主会话 host 与子代理完成结果／model_change 元数据提供上述实际模型；没有把所有子代理写成 Grok。精确次数由 operator 按 session jsonl 回填，不推测；未知计数不表示零。主会话 session 为 `01a161a4-776d-75bb-aef2-39a6e00bc50f`。

## 提交与交付边界

1. `ceb202e` — `docs(plan): backfill R2.1a and record 10-21 plan`（Run 1 已完成；本轮不重做）。
2. `4c46b85` — `docs(adr): define isolated library renderer decisions`。
3. `ca9478a` — `feat(runtime): add isolated JPEG and PDF library renderer`（含复用的场景文件）。
4. `1987db4` — `test(runtime): cover renderer isolation and four-format consistency`。
5. `30b7518` — `docs(runtime): document pinned optional renderer installation`。
6. 随后的 task／plan 证据提交：最终完整 tip SHA 写入 `/workspace/smoke-r2.1b/final-tip.json` 及 stdout，避免本文件自引用自身提交哈希。

主要修改：新增 `browser_renderer.py`、`renderer_windows.py`；扩展 `export_render.py`、`export_store.py`、`serve.py`；新增三个 renderer 测试文件并删除旧 pdf 拒绝断言；复用场景、ADR 0004、安装文档、两份依赖清单；更新本 task 与 plan 的后续项 A 决定。

已执行 `git diff 8931c35 -- sbtd-runtime/contracts/ docs/prd/ 'docs/adr/0001*' 'docs/adr/0002*' 'docs/adr/0003*'`，输出为空。CSV schema／Panel manifest 未改。仅显式路径 git add；不暂存／提交禁止路径；未 push、未开 PR、未评论 GitHub、未 merge，未触及主 checkout。

`status` 保持 **in_progress**，`completed_at=null`：本地 Linux 库级验收完成，但 operator 提审／合并、HTTP 契约接线与 R2.2 跨平台／完整 AC-51 仍不冒充完成。原生/raw 与同 stem 中文汇总已生成，Final Full Rerun=`passed`（条件 skip 如上），rtk=`skipped-for-report`；工具诊断不是 CI。

恢复／回滚：无数据迁移；撤回代码不删除 audit.db、snapshots、exports 或浏览器下载文件。在途作业不跨重启恢复；浏览器依赖不自动安装／下载；配额仍待 R2.2。应用级隔离显式 `chromium_sandbox=False`，不承诺 OS sandbox 或抵御浏览器漏洞。TaskStore 历史限制未绕过，不声称自动恢复成功。

## CONTRACT-CHANGE-NEEDED

本轮仅库级 JPEG/PDF；`POST /api/v1/exports` 仍拒绝两格式并返回 400。不修改冻结契约，不用自由 JSON 响应绕过创建请求的格式枚举。

1. `sbtd-runtime/contracts/openapi.yaml:777–799`，尤其 `:794–796`：`CreateExportRequest.format` 只有 `[html, csv]`。HTTP 开放必须由独立契约 PR 加入 `jpeg`／`pdf`，本实现不提前放行。
2. 同文件 `:739–768` 的 response 定义及 `:757–758` BadRequest 只有描述，没有 `EXPORT_IMAGE_SIZE_LIMIT` 的错误码／错误体协议。PRD §13.5 要求 1x 仍超限可辨识失败；契约 PR 必须确定该错误在异步 failed 作业与／或创建响应中的位置、HTTP 状态和安全字段，不能只把通用 400 当作尺寸语义。
3. 同一 response/schema 区没有 renderer 不可用的错误协议。需要确定缺 Playwright／专用 browser／必需字体的可辨识错误码及异步作业／创建失败语义；本轮仅库级安全错误与 capabilities 原因，不据此自行增加 HTTP 格式或错误契约。超时／渲染失败如要成为稳定客户端枚举，也应在同一契约 PR 明确。
4. `/api/v1/capabilities` `:71–84` 已是自由 Json/Envelope 响应；新增按格式的依赖可用性与 `http_available=false` 不需要本轮修改 schema。没有新增 `withheld` 值、过滤规则或 CSV schema。

Operator 已于 2026-10-22 11:24 +08:00 指定：由他人完成已授权契约 PR；合并后将 main **merge（非 rebase）** 进入本分支，再接 HTTP JPEG/PDF。本轮不执行该 merge、不 push／开 PR／评论。
