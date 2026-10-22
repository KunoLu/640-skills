---
schema_version: 1
id: v2.1.0-rc.2-r2.1b-renderer
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict；仅指定 worktree 与分支。显式 git add；不 push、不开 PR、不评论、不 merge；不暂存 .omp-r12b-addendum.txt 或 ai/tasks/codex-verify/。冻结 OpenAPI、Panel manifest、ADR 0001–0003、PRD、CSV schema。JPEG/PDF 仅库级实现，HTTP 继续拒绝。#153（open，tip 2084d71，另一 agent）映射 jpeg/pdf 与 createExport 尺寸预接受；合并且 main 以 merge 并入前不接线。
status: in_progress
blocked_reason: null
branch: feat/v2.1.0-rc.2-r2.1b-renderer
created_at: '2026-10-22T11:12:22+08:00'
updated_at: '2026-10-22T12:59:34.599901+08:00'
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
| 2026-10-22T11:13:00+08:00 | in_progress | in_progress | 补记用户后续项 A 决定：保持 #151 事件明细屏蔽行为；不新增 withheld，不为 A 开 contract PR | 用户 round-2 指令；保留四格式 event-detail 屏蔽一致性回归，AC-51 完整验收仍归 R2.2 |
| 2026-10-22T12:17:20.268311+08:00 | in_progress | in_progress | Run 1b 从 ceb202e 续接；库级实现、真实 smoke、指定回归与两位独立复核完成。本地验收通过，保留 in_progress 等待 operator 提审／契约后续，不宣称已发布 | runtime-final-full 341／7 skip；renderer-final-full 39／1 Windows skip；contracts 69、OpenAPI 16；smoke-receipt.json；reviewer closure |
| 2026-10-22T12:35:13.972967+08:00 | in_progress | in_progress | Round 2：A/B/C 与独立 contract PR 登记、模型回填、F 文档越界修正；补齐事前降级通知／配置跨进程传递和 capabilities 认证回归；本地指定回归与真实 smoke 通过 | round2/runtime-final-full 344／8 skip；renderer-final-full 42／1 Windows skip；contracts 69、OpenAPI 16；runtime-final/smoke-receipt.json |
| 2026-10-22T12:59:34.599901+08:00 | in_progress | in_progress | Round 3 库级 PR #153 对齐、受理前 preflight、AC-42 kana／9pt 页脚完成；本地验收通过，HTTP／合并与跨平台仍不冒充完成 | r3/kana-smoke；kana 720；renderer-final-full 44／1 skip；runtime-native-final-full 346／9 skip；ruff-final；两位独立 reviewer 无发现 |

## 决策

- 未完整调用 grill-with-docs：用户范围、锁定决定与冻结契约边界明确，不重开需求。
- 后续项 A 已决定（用户 2026-10-22 11:13 +08:00）：保持 #151 行为，仅屏蔽 `exportable=false` 或 `classification != local-metadata` 的 event-detail 行；派生 task/run/aggregate 不过滤。四格式共用同一过滤管线，不新增 `withheld` 值，不为 A 开 contract PR。保留 AC-51 四格式事件明细屏蔽一致性测试作为该决定的回归保护；AC-51 完整验收仍在 R2.2，不宣称本轮通过 AC-51。
- 后续项 B 仅在 F 回填 `install-and-use.md`。后续项 C 根据用户约 11:15 授权及 11:19 放置修订，与计划第 4 项 PRD §10.4 磁盘上限补充同属单独 PRD docs PR；明确两种 event 明细屏蔽条件及派生行不受影响，与 B 措辞一致。本轮不改 PRD，也不提前交付 B。
- 独立 JPEG/PDF contract PR #153（https://github.com/KunoLu/640-skills/pull/153；tip `2084d71`；status open；另一 agent 提交，非本任务会话所开）。用户 2026-10-22 11:23 +08:00 授权，11:24 指定他人完成。范围：`CreateExportRequest.format` 加 `jpeg`／`pdf`；仅 createExport 预接受 422 `{detail: 'EXPORT_IMAGE_SIZE_LIMIT', max_edge_px, max_total_pixels}`；202 `meta.warnings` 精确 `EXPORT_SCALE_DOWNGRADED:1x`；golden tests。不含第 4 项磁盘上限错误码，后续项 C 仍留在计划第 4 项。合并后 main 以 merge（非 rebase）并入 R2.1b 才开放 HTTP；本轮不接线、不评论、不 merge。
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

Round 2 before-dev：Legacy Change Safety=`characterized`，`round2/preflight-red` 两项真实失败分别证明低于 1440px 的降级未拒绝、父进程配置／事前告警未生效；保留完整输出、错误码、隔离清理与四格式过滤回归。Refactoring=`proceed / normal`，无需前置重构。DDIA=`confirmed`：配置随现有 request 进入独立 worker；降级通知／确认只在临时 job 目录，通知返回前不截图，取消／超时／处理器异常均沿用清理和不发布语义；不改数据格式、恢复或 HTTP。Python LSP status／references 均实际不可用，使用源码调用点补充。Round 2 release gate 见本轮验证收口，不以 Run 1b 的 ready 替代。

上表与 Round 2 段落是既有轮次证据，不是 Round 3 门禁结果。

Round 3 before-dev：strict、分支与干净入口 `4476b3136e280077816518faa996a59e1ca4f329` 已核对。未完整调用 grill-with-docs：本轮接口、验收与冻结边界明确，无新领域歧义。Legacy Change Safety=`characterized`：`r3/contract-preflight-red` 实测旧 warning、无 public preflight、异常无 caps；`r3/footer-before` 原 PDF 页脚实测 6pt；operator 的零 kana 结果直接采纳，不重跑确认。安全网沿用尺寸／通知／隔离／HTTP 冻结测试，并扩展本轮 public preflight 回归。Refactoring=`proceed / normal`：无需前置重构；复用既有 worker／预算／信号量／清理。DDIA=`confirmed`：无新持久状态、无迁移；SnapshotStore／ExportStore 所有权不变，preflight 不创建导出作业。预检不预留资源；调用者负责 snapshot 生命周期，至受理保持 snapshot／presentation／配置固定，生成仍复检。Python LSP references 实际不可用，源码补充调用分析。沿用已知 TaskStore catalog/frontmatter 限制，不重试 helper、不声称自动恢复；本共享记录保存用户明确 strict 选择。

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

### Round 2：决定回填与剩余项收口

本轮入口 HEAD=`6caf067`，工作区干净、分支匹配，strict 沿用用户选择；round-1 六个提交均已存在，不重做已完成的安装、字体下载、隔离实现或四格式屏蔽测试。

修改范围：`plan.md`／本 task 登记 A 决定、B 在 F、C 与第 4 项 PRD docs PR 同行、独立 JPEG/PDF contract PR 和 merge-main 前置条件；安装文档输出安全 bullet 恢复基线，仅「两格式→四格式」并追加消费同一过滤 HTML 的中性说明。spec／ADR 0004 去掉 A 决策归因，决定只在 plan/task；既有行为场景与同源过滤仍保留。

预检补齐：`MAX_SIDE_PX`／`MAX_PIXELS` 标为建议值、实测后冻结，并随作业传入 worker；2x→1x 要求完整内容、至少 1440 CSS px，重测后复检。截图前 worker 通知、父进程同步发出 `RuntimeWarning` 并重检取消／超时，再确认继续；manifest 保留同一 warning。处理器异常不确认，沿用进程清理／安全错误／不发布。没有改 `serve.py` 或任何 HTTP 错误映射。

本轮报告统一在 **`/workspace/smoke-r2.1b/round2/`**，每个 stem 保留 native `.txt`、中文九节 `.md` 与命令／时间／源码身份 `.json`。均为 `developer-local / dirty / local-only`，不是 CI 或 PR-head；最终提交用 `validated-source-hashes.json` 对照实际文件字节作等价绑定。

| 执行命令 | 结果 | 报告 stem |
|---|---|---|
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py' -v` | 344 tests：336 passed、8 skipped；60.480s | `runtime-final-full` |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. SBTD_RENDERER_TEST_HOME=/workspace/smoke-r2.1b/home /workspace/venv-r2.1b/bin/python -B -m unittest test_browser_renderer test_renderer_integration test_renderer_windows -v` | 42 tests：41 passed、1 Windows skip；28.564s | `renderer-final-full` |
| `python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_runtime_r1_acceptance -v` | 69 passed；0.548s | `contracts-final-full` |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_golden_contracts.OpenApiDraftTests -v` | 16 passed；0.060s | `openapi-final-full` |
| `ruff format`、`ruff check`、`ruff format --check`：browser_renderer.py、test_browser_renderer.py、test_renderer_integration.py | 三文件全部通过；最终完整回归在格式化后运行 | `round2-ruff-format` |
| `PYTHONPATH=sbtd-runtime:. /workspace/venv-r2.1b/bin/python -B /workspace/smoke-r2.1b/round2/smoke.py` | 真实追加 72 条中／日／英事件，经 EventStore→load_dataset→SnapshotStore→ExportStore；四格式 ready，摘要匹配；配置降级及超限失败均验证 | `round2-runtime-smoke-final` |
| `pdffonts`、`pdftotext -layout`、`pdftoppm -f 1 -singlefile -png -r 60`，输入 `round2/runtime-final/report.pdf` | CJK 嵌入、三语可搜索；12 页；已查看新生成 page-1.png | `round2-pdffonts`、`round2-pdftotext`、`round2-pdf-preview` |

系统套件 8 skips = 5 个需显式 browser home 的场景＋3 个 Windows 场景；venv 已执行前 5 项，Windows 原生证据仍归 R2.2。Dashboard 未修改，跳过其测试／构建；没有重装已验证依赖或运行无关全仓检查。rtk=`skipped-for-report`，native 保留真实输出。

Smoke 产物在 `round2/runtime-final/`：`report.html`、`report.csv`、`report.jpg`、`report.pdf`、`downgraded.jpg`、`page-1.png`、`smoke-receipt.json`。默认 JPEG **2880×25494**，降级 **1440×12744**；2x／1x 字体布局舍入会改变高度，不把两者高度恰好二分当作契约。固定高度真实回归另证完整 **1440×31999**、32001 安全失败及宽内容不截断。通知记录时 job=`generating`、artifact 不存在；最终 manifest 有 warning。1x 超限 job=`failed`、error=`EXPORT_IMAGE_SIZE_LIMIT`、无产物／manifest 且 download 拒绝。原 round-1 route-abort 日志与浏览器体积证据保留，不冒充本轮重新测量；本轮真实隔离回归已再执行。

失败记录保留：`preflight-red` 两个产品缺口；`preflight-green` 的 Host 测试误用 helper 会覆盖的 header（改用 `host` 参数后 `http-auth-green` 通过）；`round2-runtime-smoke` 的 throwaway 脚本误用异常名、`round2-runtime-smoke-green` 的不成立高度二分断言；`round2-ruff` 的 SIM117。脚本／断言修正后 smoke 与最终套件通过，无遗留产品失败。没有以降低预检标准修复 smoke。

持久回归保留四格式同一 snapshot 屏蔽集合／计数、HTML／CSV／JPEG/PDF 源与真实 PDF 文本 omission；新增 capabilities 无认证 401、非法 Host／Origin 403，既有 JPEG/PDF POST 400 与 `http_available=false` 测试通过。预检新增低于标准宽度拒绝、配置跨 worker 生效、实际 screenshot 入口前告警、拒绝通知无截图与清理、成功 1x 完整输出。AC-51 完整验收未在本轮执行或宣称通过。

独立安全复核 `RoundTwoSafetyReview`：`Findings: []`，覆盖通知顺序、配置传播、取消／超时／异常清理及 Store 发布边界；只读，未运行测试。其额外建议为给「通知处理器返回后取消／超时」补专门分支回归，非阻断发现；现有检查与生命周期回归保留。Ponytail Review：无新增公共 API、队列、依赖或第二存储路径，保留最小临时通知／确认以保证调用方在截图前收到告警，无可安全删除的控制步骤。Code Readability Review：生产逻辑限于单模块，预检与存储所有权未混合，测试在用户指定预检／HTTP／Store seam 验证行为。

独立范围复核 `RoundTwoScopeReview`：`correct`，A/B/C 放置、HTTP 冻结、AC-51 边界、模型回填、安装 safety bullet 基线逐字比对均通过；唯一 P3 建议已采纳：CONTRACT-CHANGE-NEEDED 第 3 项改成待另行决策的信息项，不扩大 11:23 授权 PR 的范围。两位 reviewer 均只读，不充当验证 controller。

Round 2 Release Readiness=`ready`（仅用户授权的 Linux 库级交付，不代表 HTTP／跨平台／发布就绪）：指定完整套件与真实 Store smoke 通过；单作业信号量、总预算、取消、处理器异常清理与不发布语义保留；降级可提前观察且 manifest 留据。配置／代码回滚无需迁移，不删除原始事件或产物；未安装／卸载全局依赖。BDD=`traceable`（既有中文场景＋英文关键词，renderer／integration unittest），Cross-repo context=`complete`，API Contract=`verified`（冻结 html/csv），Mock Strategy=`user-approved`；实际浏览器／库 smoke 不混称 HTTP 四格式 E2E。Final Full Rerun=`passed`；原生/raw 与同 stem 中文汇总已校验章节／配对；跨平台与完整 AC-51 按用户计划仍归 R2.2。

### Round 3：AC-42 假名证据、页脚与契约库级对齐

证据根目录 **`/workspace/smoke-r2.1b/r3/`**；既有 venv `/workspace/venv-r2.1b`、browser home `/workspace/smoke-r2.1b/home`，未重装依赖／字体。本轮单独 `r3/home` 写入 72 条真实事件，经 EventStore → load_dataset → SnapshotStore → ExportStore，非 golden fixture。快照 `snap_562bef29d39a4d7cb44ee9f28b787d25`。原生 `.txt`、命令／时间／入口 SHA `.json` 与同 stem 中文 `.md` 保留；developer-local／dirty／local-only，不冒充 CI 或发布。

- 混合字段完整字符串：`中文验收：任务完成 日本語のテキスト・カタカナ検証 English mixed`。`pdftotext -layout report.pdf -` 中逐字找到；U+3040–U+30FF 计数 **720**，出现于 PDF 第 9／10／11 页。`pdftotext.txt`、`kana-evidence.json` 记录文本与计数；不再用 kanji-only 的 `日本語` 作为日文假名覆盖证据。
- `pdffonts.txt`：`NotoSansCJKsc-Regular`／Bold 和 `NotoSansCJKjp-Regular` 均嵌入（emb/sub/uni=yes）。SC CJK 字体也覆盖本次假名；不把 JP 字体存在单独解释为所有日文字形均选用 JP face。
- `report.jpg`：完整 **2880×25494**；`report.pdf`：A3 横向 **12 页**。`smoke-receipt.json` 保存 ready／SHA-256／manifest；下载摘要实际匹配。`downgraded.jpg` 的通知与 manifest 精确包含 `EXPORT_SCALE_DOWNGRADED:1x`。
- `pdftoppm -f 9 -singlefile -png -r 80 report.pdf page-kana` → `page-kana.png`；已查看，第 9 页完整显示假名字符串。第 1 页同命令 → `page-1.png`。Pillow 从 JPEG 原图 `(1260,19130,2630,19520)` 裁出 `jpeg-kana-crop.png`，2 倍放大为 `jpeg-kana-zoom.png`；已查看，中文／平假名／片假名／English 均可读。
- 页脚根因：`8px` 等效 **6pt**，`pdftohtml -xml -zoom 1` 对原 `report.pdf` 的 fontspec 12／13／14 均为 6（`footer-before.txt`）。仅将 footer template 改为 **9pt**；同命令对新 PDF 实测页脚字体均为 **9pt**（`footer-after.txt`），`footer-zoom.png` 已查看，标题／范围／短 snapshot／页码均保留，没有改正文 CSS。
- `kana-smoke` 原生执行证明 public preflight 在无 exports 目录时返回 JPEG 2x／PDF None；调整配置后返回 1x＋固定 warning；1x 超限直接抛异常，caps 实测 `(1439,30000000)`。没有受理／生成失败作业来冒充 pre-acceptance 结果。HTTP 仍未接线。

独立复核：`RoundThreeSafetyReview` Findings=`[]`，确认公共 preflight 与生成共用生命周期、无 capture／publication、有效 caps 跨进程回传、固定 warning 顺序及冻结 HTTP；`RoundThreeScopeReview`=`correct`（confidence 0.96），PR #153 映射／后续项 C／模型回填／剩余缺口／kana／9pt 证据一致。两者只读，未运行验证；其静态生产／范围结论不冒充尚未完成的新增测试执行结果。Ponytail Review：复用 worker 与结果文件，无新增存储、缓存、队列或依赖，无需额外抽象。Code Readability Review：public preflight 的生命周期与生成集中在 `_run`，捕获前直接返回测量结果，IPC 只新增允许的数值 caps。

#### Round 3 最终验证与收口

| 命令／检查 | 实际结果 | `r3/` 报告 stem |
|---|---|---|
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. SBTD_RENDERER_TEST_HOME=/workspace/smoke-r2.1b/home /workspace/venv-r2.1b/bin/python -B -m unittest test_browser_renderer test_renderer_integration test_renderer_windows -v` | **44 tests：43 passed、1 Windows skip；35.327s** | `renderer-final-full` |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py' -v` | **346 tests：337 passed、9 skipped；59.944s** | `runtime-native-final-full` |
| 同系统 Python，`-m unittest test_facade_registration test_history_import -v` | 24 passed；2.469s | `native-environment-targeted` |
| renderer venv，`-m unittest test_browser_renderer.PreflightTests test_renderer_integration.RendererLibraryTests.test_preflight_measures_real_snapshot_without_capture -v` | 6 passed；6.099s | `preflight-targeted` |
| `ruff check`、`ruff format --check`：browser_renderer.py、test_browser_renderer.py、test_renderer_integration.py | 全部通过；3 files already formatted | `ruff-final`、`ruff-format-check` |
| venv `python -B /workspace/smoke-r2.1b/r3/smoke.py`＋pdftotext／pdffonts／pdftohtml／pdftoppm | 真实 Store ready、摘要匹配、exact string 72 次、kana 720、页脚 9pt；已查看 PNG | `kana-smoke`、`pdftotext`、`pdffonts`、`footer-after`、`pdf-preview-kana`、`pdf-preview-footer` |

失败证据保留而不覆盖：`contract-preflight-red` 是修改前的旧 warning／缺 preflight／缺 caps；`ruff-check` 为新增测试两处 SIM117，合并 with 后最终 lint 通过；`runtime-final-full` 是 **renderer venv 的失败尝试**（346 tests，3 failures、8 errors、3 skips，79.438s），该 venv 缺 workflow 所需 `markdown-it-py`，不是产品修复项。未安装新依赖，改用前两轮全量验证的系统 Python，先复跑 facade/history 24 项再跑完整 runtime 全量；最终通过以 `runtime-native-final-full` 为准。`renderer-focused-first` 是新增测试落地前的 42 tests 先行回归，不冒充最终 44 tests。

系统全量的 9 skips＝6 个需显式 browser home 的真实场景＋3 个 Windows 场景；6 个 browser 场景已由 venv 最终 renderer suite 执行通过。套件有重叠，不相加成独立测试数。未运行 Dashboard tests／build：无 Dashboard 修改。`ty` 当前不可用；未安装额外工具、不声称 typecheck 通过。本轮无需独立重跑全仓 workflow；全 runtime 已含 frozen OpenAPI golden tests，HTTP JPEG/PDF 拒绝与 capabilities 访问控制仍通过。

新增持久回归：精确 warning 字面量而非与同源常量自比；配置 caps 的直接异常及真实 worker 回传；public preflight 真实 SnapshotStore → HTML → Chromium 测量，normal／downgrade／oversize／PDF、报告原有 warning 保留，worker 禁止 screenshot／pdf，成功／失败都检查 profile/job 清理及 exports 不存在。删除测试写入的 snapshot/theme 源文本回声检查，不用 wiring 断言替代行为。真实混合文本 fixture 与 PDF 抽取断言均含 `中文日本語のテキスト・カタカナ English`。

Round 3 Release Readiness=`ready`（仅 Linux 库级交付）：最终计划范围通过、真实输出已查看；隔离／单作业背压／总预算／取消／错误清理沿用，preflight 无持久写路径，配置与代码回滚无数据迁移。BDD=`traceable`，`sbtd-runtime/spec/r2.1b-renderer-scenarios.md` 中文正文＋英文关键词；Cross-repo context=`complete`（本仓库面），API Contract=`verified`（已读取 origin/pr153 diff，但不改本分支冻结契约），Mock Strategy=`user-approved`（既有故障替身）；真实 Chromium／Store smoke 不混称 HTTP JPEG/PDF E2E。Final Full Rerun=`passed`；Final Test Report／Run Summary MD=`generated`，rtk=`skipped-for-report`。lessons-record 已评估：kana fixture 与 pt／px 根因的预防已落在持久场景、回归和本段原生证据，不重复创建长期 lesson／身份。HTTP 接线、Windows/macOS 实测与完整 AC-51 仍按原计划归后续。

`validated-source-hashes.json` 绑定最终实际跑过的生产／测试／场景／安装文档字节；`artifact-hashes.json` 绑定 PDF／JPEG／PNG；提交后由 `final-tip.json` 记录实际 tip 和相同字节核对，不把旧入口 SHA 当作新提交执行证明。Smoke 后生产文件仅 ruff 格式化，无行为改变；最终测试使用格式化后代码。报告仍为本地证据，不声明发布或自动恢复。

## 模型使用

| 轮次／用途 | 请求模型 | 实际模型 | assistant messages | 工具调用次数 |
|---|---|---|---|---|
| Run 1 主会话：计划首提交、只读设计；session 01a16197-919f-7482-b4ca-4d8cef45a0e5 | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra | 15 | 52 |
| Run 1 BrowserRenderer：只读研究，无写入 | omp task role | xai-oauth/grok-4.7 | 7 | 18 |
| Run 1 RendererIntegrationTests：只读研究，无写入 | omp task role | xai-oauth/grok-4.7 | 5 | 16 |
| Run 1b 主会话：实现、验证、交付；session 01a161a4-776d-75bb-aef2-39a6e00bc50f | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra | 130 | 218 |
| Run 1b BrowserImplementation：renderer 实现 | omp 默认 task role，未显式覆盖 | xai-oauth/grok-4.7 | 64 | 124 |
| Run 1b RendererIntegration：库／HTTP／过滤一致性实现 | omp 默认 task role，未显式覆盖 | xai-oauth/grok-4.7 | 63 | 139 |
| Run 1b RendererSecurityReview：安全复核 | omp 配置 security-reviewer role | openai-codex/gpt-6-astra | 28 | 82 |
| Run 1b RendererOutputReview：输出／集成复核 | omp 配置 reviewer role | kimi-code/k3 | 62 | 78 |
| Round 2 主会话：决定回填、范围修正、预检通知与验证；session 01a161d9-7264-725e-9d47-caeaf21ccfd9 | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra | 51 | 112 |
| Round 2 RoundTwoSafetyReview：独立只读安全复核 | omp 配置 security-reviewer role | openai-codex/gpt-6-astra | 12 | 40 |
| Round 2 RoundTwoScopeReview：独立只读范围／输出复核 | omp 配置 reviewer role | kimi-code/k3 | 42 | 47 |
| Round 3 主会话 | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra | unknown | unknown |
| Round 3 RoundThreeDocs：plan／task 文档更新 | omp 默认 task role，未显式覆盖 | xai-oauth/grok-4.7 | unknown | unknown |
| Round 3 RoundThreeTests：预检／caps／kana 回归实现 | omp 默认 task role，未显式覆盖 | xai-oauth/grok-4.7 | unknown | unknown |
| Round 3 RoundThreeSafetyReview：独立只读安全复核 | omp 配置 security-reviewer role | openai-codex/gpt-6-astra | unknown | unknown |
| Round 3 RoundThreeScopeReview：独立只读范围／输出复核 | omp 配置 reviewer role | kimi-code/k3 | unknown | unknown |
| Session title generation | unknown | unknown | unknown | unknown |

Run 1／1b 模型与计数由 operator 于 2026-10-22 从 session jsonl 核实；计数为 assistant messages／toolCall blocks，全部 `resolvedModelIsFallback: false`，无 advisor。Run 1 两子代理只读，operator 于 11:17 +08:00 停止该轮。Round 2 主会话、SafetyReview、ScopeReview 的计数亦由 operator 从 jsonl 核实，全部 `resolvedModelIsFallback: false`，无 advisor。Round 3 计数保留 unknown，等待 operator 回填，不推测、不表示零。

Round 2 两位 reviewer 均从各自运行环境确认实际模型；ScopeReview 已只读复核第 3 项修正并确认 P3 关闭，无进一步发现。其回执晚于首次 docs commit 返回，因此仅将该回执与实际模型并入同一未发布的本轮 docs commit；不改 round-1 历史。

## 提交与交付边界

1. `ceb202e` — `docs(plan): backfill R2.1a and record 10-21 plan`（Run 1 已完成；本轮不重做）。
2. `4c46b85` — `docs(adr): define isolated library renderer decisions`。
3. `ca9478a` — `feat(runtime): add isolated JPEG and PDF library renderer`（含复用的场景文件）。
4. `1987db4` — `test(runtime): cover renderer isolation and four-format consistency`。
5. `30b7518` — `docs(runtime): document pinned optional renderer installation`。
6. `6caf067` — `docs(task): record R2.1b acceptance evidence and contract gaps`（Run 1b）。
7. `12afbb4` — `fix(runtime): notify JPEG downgrade before capture`（Round 2 预检、测试与 renderer 文档）。
8. Round 2 决定回填采用用户指定 `docs(r2.1b): record follow-up A decision (keep #151 exportable behavior)`。最终 tip 与源码内容绑定记录在 `/workspace/smoke-r2.1b/round2/final-tip.json` 及 stdout，避免本文件自引用自身哈希。
9. `aea5cd6` — `feat(runtime): align renderer preflight with export contract`（Round 3：库级 preflight／固定 warning／有效 caps、kana 回归、9pt 页脚、场景与使用文档）。
10. Round 3 文档收口：`docs(task): record R2.1b AC-42 kana smoke`（本 task、plan 的 #153 登记与模型回填）；实际最终 tip 记录在 `/workspace/smoke-r2.1b/r3/final-tip.json` 及交付输出，避免自身哈希循环。

主要修改：新增 `browser_renderer.py`、`renderer_windows.py`；扩展 `export_render.py`、`export_store.py`、`serve.py`；新增三个 renderer 测试文件并删除旧 pdf 拒绝断言；复用场景、ADR 0004、安装文档、两份依赖清单；更新本 task 与 plan 的后续项 A 决定。

已执行 `git diff 8931c35 -- sbtd-runtime/contracts/ docs/prd/ 'docs/adr/0001*' 'docs/adr/0002*' 'docs/adr/0003*'`，输出为空。CSV schema／Panel manifest 未改。仅显式路径 git add；不暂存／提交禁止路径；未 push、未开 PR、未评论 GitHub、未 merge，未触及主 checkout。

Round 3 提交前已核对仅上述 7 个允许文件变化、index 初始为空；相对入口 `4476b3136e280077816518faa996a59e1ca4f329` 的 contracts／serve.py／PRD／ADR 0001–0003 diff 为空，`git diff --check` 通过。本轮仅显式 `git add <path>`，无禁止路径入 index。

`status` 保持 **in_progress**，`completed_at=null`：本地 Linux 库级验收完成，但 operator 提审／合并、HTTP 契约接线与 R2.2 跨平台／完整 AC-51 仍不冒充完成。原生/raw 与同 stem 中文汇总已生成，Final Full Rerun=`passed`（条件 skip 如上），rtk=`skipped-for-report`；工具诊断不是 CI。

恢复／回滚：无数据迁移；撤回代码不删除 audit.db、snapshots、exports 或浏览器下载文件。在途作业不跨重启恢复；浏览器依赖不自动安装／下载；配额仍待 R2.2。应用级隔离显式 `chromium_sandbox=False`，不承诺 OS sandbox 或抵御浏览器漏洞。TaskStore 历史限制未绕过，不声称自动恢复成功。

## CONTRACT-CHANGE-NEEDED

**addressed by PR #153 (open)**：格式与 createExport 尺寸预接受协议已有独立 PR，本分支仍只做库级 JPEG/PDF。`POST /api/v1/exports` 继续拒绝两格式并返回 400。不在本分支修改冻结契约，不用自由 JSON 绕过创建请求的格式枚举。HTTP jpeg/pdf 只在 #153 合并、且 main 以 merge（非 rebase）并入本分支之后接线。open 不是 merged。

PR：https://github.com/KunoLu/640-skills/pull/153；tip `2084d71`；status open；另一 agent 提交，非本任务会话所开、未评论、未 merge。

1. `sbtd-runtime/contracts/openapi.yaml:777–799`，尤其 `:794–796`：本分支 `CreateExportRequest.format` 仍只有 `[html, csv]`。#153 将该 enum 增为含 `jpeg`、`pdf`。映射：已由 PR #153（open）提出；合并前本实现不放行 HTTP。
2. 同文件 `:739–768` 的 response 定义及 `:757–758` BadRequest 在本分支仍只有描述，没有 `EXPORT_IMAGE_SIZE_LIMIT` 协议。#153 只在 createExport 增加预接受 422，错误体恰为 `{detail: 'EXPORT_IMAGE_SIZE_LIMIT', max_edge_px, max_total_pixels}`（生效上限）。202 `meta.warnings` 的精确字符串为 `EXPORT_SCALE_DOWNGRADED:1x`；golden tests 在该 PR。映射：尺寸预接受与降级 warning 已由 PR #153（open）提出。这不覆盖 202 之后的失败语义。
3. 仍未由 #153 覆盖，保持显式：renderer 不可用（缺 Playwright、专用 browser 或必需字体）没有稳定客户端错误枚举。202 之后的失败语义（异步 failed 作业、getExport）也不在该 PR 的 createExport 422 预接受内。尺寸若只能在 202 之后检测，不能把该 422 当成已覆盖的 post-202 失败协议。超时或渲染失败若要成为稳定错误枚举，仍须另行确认协议与授权。本轮只记录缺口，不扩展 #153，不改 HTTP。
4. `/api/v1/capabilities` `:71–84` 已是自由 Json/Envelope 响应；按格式的依赖可用性与 `http_available=false` 不需要本轮修改 schema。没有新增 `withheld` 值、过滤规则或 CSV schema。磁盘上限错误码仍归计划第 4 项，后续项 C 留在该行，不在 #153。

库级入口已实现并通过 `r3/kana-smoke` 实跑：`BrowserRenderer(home, snapshots).preflight(snapshot, export_format, presentation_state, cancelled=None)` 返回恰好 `{scale: 1|2（JPEG）或 None（PDF）, warnings: list[str]}`；同一隔离 worker／布局路径，不截图、不生成 PDF、不写导出产物、不开 ExportStore 作业。返回包含既有报告告警和固定降级字符串；尺寸失败带 worker 当次有效 caps，保留 code/str allowlist。后续 HTTP 接线须先校验请求并持有 snapshot，在 `ExportStore.create`／202 之前调用 preflight，将 warning 放入 202 `meta.warnings`，捕获 size error 返回 #153 的 422 体；使用相同 snapshot／presentation／配置并让生成阶段继续复检。renderer 不可用与 post-202 失败仍按上列缺口另行决策；本轮不接线。
