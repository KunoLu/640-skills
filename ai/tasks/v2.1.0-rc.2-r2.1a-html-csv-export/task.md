---
schema_version: 1
id: v2.1.0-rc.2-r2.1a-html-csv-export
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict；仅 plan R2.1a 与 D11/D15/D16。不改契约；显式 git add；不 push、不开 PR；不暂存或提交 .omp-r12b-addendum.txt、ai/tasks/codex-verify/。保持 OpenAPI、Panel manifest/schema、ADR 0001/0002/0003、PRD、CSV schema 1.1 不变。不可避免的契约变化 STOP + CONTRACT-CHANGE-NEEDED。
status: done
blocked_reason: null
branch: feat/v2.1.0-rc.2-r2.1a-html-csv-export
created_at: '2026-10-20T15:07:13+08:00'
updated_at: '2026-10-20T22:14:25+08:00'
completed_at: '2026-10-20T21:32:47+08:00'
---

# R2.1a：离线 HTML + 全量 CSV 导出

基线 `e9cb05b84e449fe4a7dde1b5523faf7478bc310e`；R2.0c #147 于 2026-10-20T15:03:24+08:00 squash-merge，Reviewy CLEAN on `2dbf7b1`。用户 15:05 授权本任务。done 仅代表本地验收，不代表 push／PR／部署／发布。

## 范围与验收

1. 单文件离线 HTML；扫描外部 URL、script src、link href=http、@import、url(http；系统字体与明确 CJK fallback。
2. CSV 复用 serialize_csv / SnapshotStore.dataset_page，snapshot-bound cursor 全量遍历；schema 1.1 不变。
3. 创建作业固定 snapshot_id 并持 backend pin 至完成／取消／失败；测试在途 expiry/sweep 不删、结束释放；前端复用 PinRegistry。
4. ready 后默认 24h，含启动清扫；Export 清理仅 exports/，绝不触及 snapshots/ 或其他目录。
5. 有效期内重复下载 bytes/digest 不变，含 serve 重启。
6. export_id + 当前 session 下载，无路径参数；拒绝 traversal／foreign ID。
7. HTML 和 CSV 使用后端统一脱敏，manifest 记录 redaction version。
8. temp + fsync + rename 原子发布；半成品永不被下载。
9. 更新 install-and-use.md 中 exports pending 与行为说明。

## Book Gate Plan

| Gate | 触发事实 | 阶段 | 状态 |
|---|---|---|---|
| book-ddd-distilled-modeling | 作业／快照引用／会话授权与两目录所有权 | before-dev | round 2 confirmed：#148 消除输入缺口；沿用 runtime-home 授权，Export 不拥有 snapshots 清理 |
| book-ddia-data-design | 导出持久产物、manifest、异步作业与恢复 | before-dev | round 2 confirmed：artifact 后 manifest 原子发布、SHA-256、ready 后 24h；中断作业不自动恢复 |
| book-legacy-change-safety | serve 鉴权、CSV 与 snapshot 高回归面 | before-dev | characterized：修改前 38 tests，37 passed／1 Windows skip；HTTP tracer red 405 != 202 |
| book-refactoring-pass | 修改既有生产代码 | before-dev | proceed：无需前置重构；保留现有鉴权、SnapshotStore、CSV schema；只扩展输出 seam |
| book-release-readiness | HTTP 服务与导出作业 runtime 改变 | validation 后 | planned；等待本轮实现、测试与独立复核 |

已读 plan、grill D11/D15/D16/R1e、PRD §10.4/§13、OpenAPI exports 与全部 components schemas、CSV、SnapshotStore、serve、ReportDocument、PinRegistry、ADR 0003。未完整调用 grill-with-docs：范围和验收已锁定，无须重开需求。Python LSP references 实际返回 No language server found，已以源码查找 serialize_csv 与 API 调用证据补充。尚未进入生产编辑。

## 状态持久化限制

已核对分支、路径与 ignore；安装的 TaskStore.create 实际返回 `TaskStateError: task has no YAML frontmatter block`，completed_steps 为空。未写 active 指针；不修改禁止路径或旧 catalog 来绕过。此共享 task.md 是用户明确要求的交付记录，沿用 R2.0c 做法，不声称 TaskStore lifecycle／自动恢复成功。

## 验证计划

原计划沿用 sbtd-runtime/spec 中文场景 + 英文 Given/When/Then，主会话唯一验证 controller，执行 runtime Python tests、受影响 Dashboard tests、CI wrapper、真实 serve 导出／重启 smoke 和独立复核。因用户明确 STOP 条件已触发，本轮未进入这些阶段；不创建未实现的场景／测试／报告占位，不把契约诊断算功能验收。

## 风险与后续范围

- Snapshot disk-usage cap：Reviewy follow-up，仅记录，非本任务实现范围。
- R2.1b JPEG/PDF／Playwright 与 R2.2 跨平台证据不实现；Windows ACL／macOS 不冒充本机验证。
- 不修复无关历史 probe_links 失败；若命中如实保留。

## CONTRACT-CHANGE-NEEDED（round 1 历史；已由 #148 解决）

**Round 1 曾触发并停止实现；#148 于 2026-10-20 18:47 +08:00 合并，已提供所缺请求契约。本节保留历史，不代表当前仍阻塞。**

### 事实与不可绕过的缺口

- `sbtd-runtime/contracts/openapi.yaml:414–430`：`POST /api/v1/exports` 仅定义 localSession、CsrfToken、IdempotencyKey 和 403／202 响应；没有 requestBody，没有 snapshot_id、format 或 presentation_state 输入参数。
- 同文件 `components.schemas:661–747` 只有 Health、Session、Envelope、Meta、QueryScope、IngestBatch，没有导出创建请求 schema。路径级亦无补充参数。
- PRD §13.2（1105–1114 行）要求点击时固定当前 snapshot_id 和页面展示状态；§13.3（1124 行）列出呈现状态。格式选择也必须进入创建作业请求。现有 `ReportDocument` 与 `PinRegistry` 只提供客户端模型，不能补上 HTTP wire contract。
- 现有 `dashboard/src/api.ts:245–247` 对同类情况明确记载：report-snapshots POST 未定义 requestBody，因此客户端不向它发送 scope，而使用已有声明 scope 的 statistics/query。
- `Envelope.data: {}` 的开放性只适用于响应，不是创建请求的输入定义。

缺少 requestBody 不等于 OpenAPI 明文禁止任何 HTTP body；本次阻塞理由是**必需的外部请求约定未定义，不能在“不改契约”的授权下自行确定并隐藏于实现**。私加 JSON body／query／header 都新增外部约定；借用 Idempotency-Key 携带数据改变其语义；选择服务端“最近快照”会破坏客户端固定 snapshot_id／多标签／自动刷新不变量。ADR 0004 仅允许内部实现决策，也不能替代这个外部契约。

### 恢复所需的最小决定

由 operator／用户明确授权补齐 `createExport` 的请求契约（至少 snapshot_id、HTML/CSV 格式选择、presentation_state 及相应校验语义），或提供已批准且可核验的既有输入协议并明确允许按它实现。不是请求放宽为默认最近快照，也不建议改 CSV schema、Panel manifest 或既有 ADR 决策。本轮未编辑任何受保护契约；不改契约。

### 独立可见门禁结论

DDD Boundary Review — blocked。Snapshot 为固定数据；Export Job 为固定快照＋呈现状态的一次生成任务；Query & Snapshot／Export 分别拥有 snapshots／exports 清理；Access Control 拥有 session。导出是支撑子域、访问控制为通用能力。保留 pin、刷新隔离、CSV 全量不变量；对既有 grill 的领域决定无修正，新增发现仅为 HTTP 输入契约缺口。

DDIA Data Design Review — blocked。SnapshotStore 是固定数据源；Export 拥有文件和 manifest。请求输入必须在 pin／异步生成前确定；当前无法稳定该写路径。幂等键不能替代业务输入；一致性目标为固定快照与固定产物字节。尚无格式／迁移／重放／回滚变更；修复信号为批准后的输入协议。所需测试仍为本文件九项验收，未执行、未通过。

## 本轮交付与验证

结论：**blocked / CONTRACT-CHANGE-NEEDED**，不是 R2.1a 完成；completed_at 保持 null。只完成用户要求的第一提交；后续仅保存 STOP 证据。plan R2.1a 保留用户要求的 in_progress（已启动但未完成）；R2.1b+ planned 不变。

修改文件：

1. `ai/tasks/v2.1.0-rc.2-plan/plan.md`：R2.0c #147 done、完整 merge SHA／时间，R2.1a in_progress／分支／请求模型。
2. `ai/tasks/v2.1.0-rc.2-r2.0c-snapshot-persistence/task.md`：合并 closeout、实际 mode_note、五个模型及 assistant message 计数 80／16／15／88／3，工具调用 unknown；历史 completed_at 不变。
3. 本文件：strict 骨架、门禁触发事实、阻塞证据、验证边界、模型与状态事件。

提交：

- `9dd017efe9f5900d91a79743b749b37966891cd9` — `docs: close R2.0c and start strict R2.1a exports`。
- 随后的 docs-only STOP 记录提交，其最终 tip SHA 在提交后 stdout 与本地 `reports/closeout-tip.json` receipt 记录；避免 task.md 自引用其自身 commit hash。

实际执行：

| 命令／调用 | 结果 |
|---|---|
| `pwd && git status --short && git branch --show-current && git rev-parse HEAD` | 根／指定分支／e9cb05b 基线匹配；仅用户禁止的两个 untracked 路径 |
| `git check-ignore .sbtd/active-task.json ai/tasks/v2.1.0-rc.2-r2.1a-html-csv-export/reports/probe.json` 与 `git ls-files` 窄路径检查 | 本地状态及 reports 受 ignore 保护；相关本地状态无 tracked 输出 |
| 安装的 `TaskStore.create(..., mode='strict', confirmed=True)` | 失败：task has no YAML frontmatter block；completed_steps 为空，未持久化 active |
| eval Python：`yaml.safe_load(openapi)` 后解析 createExport 与 components | requestBody_present=False；参数恰为两个 header；schemas 六项，无导出请求；responses 403/202 |
| eval Python：八个受保护文件逐字节比较 `git show e9cb05b:<path>` 与当前文件 | 全部相同：OpenAPI、Panel manifest/schema、ADR 0001/0002/0003、PRD、csv_export.py；CSV 1.1 未改 |
| 显式三路径 `git add` 与第一 `git commit` | 成功；3 files changed；禁止路径未暂存或提交 |

未执行 runtime Python tests、Dashboard tests、pin/sweep/digest/离线扫描/原子写入场景、serve restart smoke、独立代码复核、build/lint：用户要求命中契约硬边界后 STOP 并结束，本轮无生产／前端／测试变更，不把原实现通过作为 R2.1a 证据。验收 1–8 均未实现／未验证；验收 9 安装文档保留 pending，避免错误宣称导出可用。没有修改、修复或重跑无关 probe_links 失败。

验证仅为 developer-local 契约诊断，非正式功能测试报告、非 CI／full-stack；未 push、未开 PR、未发布。TaskStore catalog 问题保留且未绕过，自动恢复不可靠；后续须显式处理 blocked task 与输入契约授权。Snapshot disk-usage cap 仍仅为 follow-up。

## 模型使用

| 用途 | 请求模型 | 实际模型 | assistant messages | 工具调用次数 |
|---|---|---|---|---|
| Round 1 主会话：契约调查／docs backfill／STOP 记录；session 01a15822-15df-7329-b854-f224871df557 | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra | 17（operator 核验 session logs） | unknown |

Round 1 title generation：unknown。本轮请求模型 `openai-codex/gpt-6-astra:high`，实际 host 标识 `openai-codex/gpt-6-astra`；完整计数待交付时按可用证据记录。

## Round 2 恢复

已 rebase 到 `6e2cc56f386c603179ee6efd6004a24b5391ffc8`；旧 docs 提交现为 `240d31b`、`7ec402e`，以上旧 SHA 仅为 round-1 历史。#148 的 CreateExportRequest、202 export_id、400／404／410、SnapshotId pattern 与完整 panel_order 规则为本轮冻结输入。

R2.0c task 的 mode_note、80／16／15／88／3 模型计数、#147 closeout 与 plan R2.0c done 行已核对存在且正确，不重复回填。未完整调用 grill-with-docs：原验收与本轮契约明确。继续 strict；沿用已知 TaskStore catalog 限制，不重跑已失败调用、不写 active／ignore／身份；本共享记录是用户明确要求的交付，不声称 helper 恢复成功。

### Round 2 before-dev 决策与证据

- DDD Boundary Review — confirmed：Snapshot 是固定范围／水位；Export 为支撑子域，AccessControl 为通用能力。既有配对 session 均读取该 runtime home，不添加租户／用户模型；重启重新配对后可读该 home 的 ready 产物，外部 home 的 ID 不可见。前端 PinRegistry 只固定 ID，backend pin 保证在途存活。无 grill 修正、无未决领域冲突。
- DDIA Data Design Review — confirmed：SnapshotStore 为数据事实源；Export 拥有固定 bytes 与 manifest。接受前 pin，终态 finally release；artifact 与 manifest 同目录 temp／fsync／rename，manifest 为 ready 发布标记。SHA-256 校验下载；ready 起 86400 秒，重启不续期；清扫仅 exports。无需迁移／backfill；中断作业不重放，失败／取消不冒充 ready；撤回实现保留原始事件与快照。
- Legacy Change Safety Review — characterized：`reports/r2-before-dev-safety.{json,md}` 38 tests／1 skip；真实 `POST /api/v1/exports` tracer 红例 `405 != 202`，`reports/r2-http-tracer-red.{json,md}`。保留 cursor 绑定、CSV 空值／公式转义、snapshot TTL、鉴权。
- Refactoring Review — proceed / normal：不需要重构；新增 storage／render 两模块、serve 局部路由。Python LSP references 返回 No language server found；源码调用点已核对。无 seam-only 例外。
- BDD：`sbtd-runtime/spec/r2.1a-export-scenarios.md`，中文正文／英文关键词；真实本地 HTTP 与文件为测试 seam；Cross-repo context: complete；Mock Strategy: none（故障注入仅文件发布边界）。主会话唯一验证 controller；两个实现 slice 独占 storage 与 rendering 文件，不运行测试／lint／formatter。

## Round 2 实现与验证

实现提交 `e087b25ed0de119f97e043628c41965d2a254142`。新增 `export_store.py`、`export_render.py`，扩展 CSV 输出 seam 与 serve 导出路由；场景、测试、安装文档和 CI 入口同步。未新增 ADR：manifest／digest 决定记录在安装文档，不改变外部契约。

行为：请求按冻结契约校验；接受前 pin，成功、失败、取消、关闭和 worker 启动失败均释放。artifact 后 manifest 原子发布，下载和重启重新校验 SHA-256。ready 起 86400 秒，启动清扫只删除已验证的 `exports/` 文件。HTML 为静态单文件；CSV 走 snapshot cursor，schema 1.1。后端输出层对文本、结构化键／叶子及嵌入 JSON 标识脱敏，manifest 记录版本。

### 复核与门禁

- ExportLifecycleReview：`openai-codex/gpt-6.1-sol`。三轮前发现的目录替换清理、sweep 与 finally 竞态、FIFO 非阻塞打开均已用失败回归修复；复核关闭，无剩余 actionable 缺陷。可选重复状态字段未删，避免行为改动。
- ExportOutputReview：`kimi-code/k3`。结构化指标键／叶子、复合标识和未知时间预览的脱敏缺口均由红绿回归修复；最终复核 correct，无剩余 actionable 缺陷。
- Code Readability：沿用现有 serve／SnapshotStore 错误、权限和原子发布形状；长渲染函数保留数据面板 seam，不拆无关抽象。
- Ponytail Review：生命周期可选减少约 7 行重复状态，不采纳；输出侧重复扫描已合并。无新依赖。
- Release Readiness Review — ready（仅本地 R2.1a，不是部署／发布）：失败保持 pin 释放和安全错误；取消只影响本作业；摘要不符、半成品和替换目录不提供或清理外部文件。一个 worker 串行，无远程暴露。无新增指标、告警或队列上限；状态由 getExport 观察。回滚只撤回代码，不迁移或删除原始事件、快照和已下载文件。

### 验证证据

主会话是唯一验证 controller。rtk：skipped-for-report。所有正式结果为 developer-local／dirty／local-only；实现提交后仅 task 证据待提交，不冒充 CI 或 PR head。

| 命令 | 结果 | raw／中文汇总 |
|---|---|---|
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py' -v` | 298 tests：296 passed、2 skipped，55.998s；skip 为 Windows junction evidence only | `reports/r2-runtime-final-redaction` |
| `python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_runtime_r1_acceptance -v` | 65 passed，0.634s；与 runtime 重叠，不累计 | `reports/r2-contract-acceptance-final` |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_golden_contracts.OpenApiDraftTests -v` | 12 passed，0.070s；最终 runtime discovery 再次覆盖 | `reports/r2-openapi-full` |
| `ruff check` 七个改动 Python 文件 | All checks passed | `reports/r2-python-final-redaction-check` |
| `ruff format --check` 同一范围 | 7 files already formatted | `reports/r2-python-final-redaction-format` |
| 真实 `python3 -B -m serve` 两次启动、配对、HTML／CSV 下载、Ctrl-C 重启 smoke | HTML 14100 bytes、CSV 51855 bytes／139 行；两次 SHA-256 相同且等于 manifest；到期时间不变 | `reports/r2-final-restart-smoke` |

浏览器检查最终 smoke HTML：13 个 Panel 均可见，脚本 0，页面资源请求 0；系统字体栈含 CJK fallback，图表文字为浅色 `rgb(231, 237, 245)`。首次完整浏览器检查曾记录 favicon 请求，随后 HTML 使用 `data:,` favicon，最终网络记录只有 HTML 自身。截图由 Playwright 返回，不入 Git。

红绿回归均保留：HTTP tracer `405 != 202`；结构化秘密、结构化指标、嵌入标识、worker 启动失败、排队取消、目录替换清理、发布后 sweep。修复后对应 green 报告保留。未运行 dashboard tests／typecheck／build：dashboard 源码和静态产物未改。未运行全仓 workflow 或历史 probe_links，不修复、不重跑、不称全仓通过。

`git diff 6e2cc56f386c603179ee6efd6004a24b5391ffc8 -- sbtd-runtime/contracts/openapi.yaml` 为空。panel manifest/schema、ADR 0001–0003、PRD、CSV schema 1.1 未改。无 CONTRACT-CHANGE-NEEDED。

## 模型使用

| 用途 | 请求模型 | 实际模型 | assistant messages | 工具调用次数 |
|---|---|---|---|---|
| Round 2 主会话 | openai-codex/gpt-6-astra:high | xai-oauth/grok-4.7 | unknown | unknown |
| ExportStorage 实现 | 未指定 | xai-oauth/grok-4.7 | unknown | unknown |
| ExportRendering 实现 | 未指定 | xai-oauth/grok-4.7 | unknown | unknown |
| ExportLifecycleReview | 未指定 | openai-codex/gpt-6.1-sol | unknown | unknown |
| ExportOutputReview | 未指定 | kimi-code/k3 | unknown | unknown |

无 advisor、无 fallback。Round 2 title generation：unknown。

## 风险与恢复边界

- done 只表示本地实现和指定验收完成；未 push、未开 PR、未部署、未发布。plan 行保持 in_progress，等待后续 PR／merge 回填。
- 一个本地 worker，无队列上限、指标或告警。本地单用户可接受；远程或多用户并发不在本授权范围。
- 在途作业不跨进程恢复；重启只恢复通过摘要校验的 ready 文件。SHA-256 检测损坏，不抵御同机管理员篡改。
- Snapshot 磁盘容量上限仍是 follow-up。Windows ACL、macOS／Windows 视觉和 JPEG／PDF 不属于本任务。
- TaskStore catalog 限制未绕过；此文件是用户明确要求的共享记录，不承诺自动恢复。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-20T15:07:13+08:00 | planned | in-progress | 用户明确 strict 与 R2.1a；分支、基线匹配；创建明确授权共享交付记录，非 TaskStore lifecycle 成功 | git branch/rev-parse；用户附加 prompt；TaskStore.create 失败且无 completed_steps |
| 2026-10-20T15:09:39.646430+08:00 | in-progress | blocked | CONTRACT-CHANGE-NEEDED：创建导出缺少固定快照／格式／呈现状态的请求协议；按用户硬边界停止，不自行扩展外部契约 | openapi.yaml:414–430、661–747；PRD §13.2–13.3；实际 YAML 解析 requestBody_present=False，参数仅 CsrfToken/IdempotencyKey；八个受保护文件逐字节未变 |
| 2026-10-20T18:50:07+08:00 | blocked | in-progress | #148 merged as 6e2cc56 supplied createExport request contract；已 rebased onto 6e2cc56；用户明确恢复 strict R2.1a | round-2 prompt；当前分支匹配、HEAD 7ec402e；重新读取冻结 OpenAPI 请求／202／错误／panel_order；清除 blocked_reason |
| 2026-10-20T20:35:58+08:00 | in-progress | checking | HTML／CSV、作业存储、冻结请求校验、测试／场景／文档已实现；真实 serve 重启与浏览器报告 smoke 通过，独立复核进行中 | runtime 首次完整 291 tests／2 skips；wrapper 65、OpenAPI 12；新增输出／pin 边界红绿证据；reports/r2-full-panel-restart-smoke；浏览器 13 panels、0 scripts、0 resources |
| 2026-10-20T21:32:47+08:00 | checking | done | 本地 HTML／CSV 导出验收、独立复核和最终套件完成；不表示 push、PR、部署或发布 | 实现 e087b25ed0de119f97e043628c41965d2a254142；runtime 298／2 skip；wrapper 65；OpenAPI 12；ruff passed；真实重启 smoke SHA-256 不变；两位 reviewer 关闭；OpenAPI diff 为空 |

## Re-verify（round-2 grok 回退后 k3:max 复核）

为何运行：round-2 主会话 `01a158ee-5891-719d-a34c-8ca96493a8a6` 在 `openai-codex/gpt-6-astra` 104 条 assistant messages 后回退到 `xai-oauth/grok-4.7`（54 条，约 2026-10-20 21:19 Asia/Shanghai 起，model_change 2026-10-20T13:19:15Z），全程无 advisor；实现与部分证据落于回退段。按 operator 规则用已知模型复核一次。本节为合规复核记录，不改 frontmatter `status`／`completed_at`，不新增状态事件。

执行命令（verbatim）：`cd /workspace/640-skills-r2.1a && timeout 10800 omp -p --model kimi-code/k3:max --auto-approve "$(cat ~/.omp/logs/640-r21a-reverify-k3max/prompt.md)" </dev/null`

复核对象：同一分支 `feat/v2.1.0-rc.2-r2.1a-html-csv-export` @ `796ff45d9f069b71da93824e3ad26e1e81b56a91`（已 rebase onto `10bc530`；实现提交现为 `3fcb5cf`，本文件 round-2 段落引用的 `e087b25…` 为 rebase 前 SHA，仅作历史）。不切换分支、不 rebase、不 push、不开 PR、不 amend。未完整调用 grill-with-docs：验收标准与冻结契约无歧义，复核范围由 operator prompt 锁定；不重开 before-dev 门禁，check 阶段证据为全量 diff 复核＋完整测试执行。

### 验收清单复核（diff 对逐条验收）

| # | 验收 | 证据 | 结论 |
|---|---|---|---|
| 1 | 单文件离线 HTML；无外部 URL／script src／link href=http／@import／url(http；系统字体＋CJK fallback | `export_render.py` `_html` 仅内联 `<style>`＋`<link rel="icon" href="data:,">`；`_CSS` 字体栈含 PingFang SC／Hiragana Sans GB／Microsoft YaHei／Noto Sans CJK SC·JP；`test_export_render.py::test_html_contains_every_panel_and_shared_metric_values` 断言 FORBIDDEN 全部缺失、CJK 字体全部存在 | PASS |
| 2 | CSV 复用 serialize_csv／SnapshotStore.dataset_page，snapshot-bound cursor 全量遍历；schema 1.1 不变 | `export_render._walk_rows` 以 `dataset_page(snapshot_id, cursor, DEFAULT_PAGE_SIZE)` 循环至 `next_cursor is None`；`csv_export.CSV_SCHEMA_VERSION = "1.1"` 未改，仅新增可选 `rows`／`value_transform` 参数且缺省路径不变；`test_csv_cursor_walk_matches_schema_without_truncation`（limit=2 分页走完全量） | PASS |
| 3 | 创建固定 snapshot_id 并持 backend pin 至完成／取消／失败；在途 expiry/sweep 不删、结束释放 | `ExportStore.create` 先入队前 `snapshots.pin`，`_run` finally `release`，`close`/`delete` 同路径释放；`test_pin_precedes_render_and_releases_on_each_terminal_state`、`test_two_jobs_hold_the_snapshot_until_each_releases`、`test_sweep_between_publish_and_finally_still_releases_pin`、`test_worker_start_failure_releases_snapshot_pin`；前端 dashboard 未改，PinRegistry 复用为文档级说明 | PASS |
| 4 | ready 后默认 24h，含启动清扫；清理仅 exports/ | `EXPORT_TTL_SECONDS = 86400`；`__init__` 执行 `_restore()` 后 `sweep()`；sweep 仅删已验证配对；`test_sweep_and_startup_touch_only_verified_expired_exports` | PASS |
| 5 | 有效期内重复下载 bytes/digest 不变，含 serve 重启 | `_read_ready` 每次重校 SHA-256；`test_ready_manifest_is_stable_across_download_and_restart`、`test_identical_download_bytes_and_digest_after_real_restart`、`test_download_does_not_extend_retention` | PASS |
| 6 | export_id＋当前 session 下载，无路径参数；拒绝 traversal／foreign ID | `export_resource` 拒绝 query 参数（400）；`_check_id` 仅接受 `exp_[0-9a-f]{32}`；SecurityMiddleware Bearer 不变；`test_download_auth_path_boundary_and_delete`、`test_foreign_home_and_traversal_cannot_read_bytes`、`test_required_headers_and_idempotent_creation`（缺 Authorization 401） | PASS |
| 7 | HTML／CSV 后端统一脱敏，manifest 记录 redaction version | `redact_text`／`redact_cell`／`_redact_node`；CSV 走 `value_transform=redact_cell`；metadata 含 `redaction_policy_version`；`test_redaction_is_shared_and_does_not_change_metrics`、`test_structured_secret_text_is_redacted_in_both_formats`、`test_structured_metric_keys_and_leaves_are_redacted`、`test_embedded_identifier_secrets_are_redacted` | PASS |
| 8 | temp＋fsync＋rename 原子发布；半成品永不被下载 | `_write_temp` 同目录 mkstemp＋0600＋fsync，`os.replace`＋`_fsync_dir`，manifest 后发布为 ready 标记；`_fail`／`_mark_cancelled` 清理 artifact；`test_partial_and_corrupt_files_are_never_ready` | PASS |
| 9 | install-and-use.md 更新 exports 行为说明 | 文档段落由「服务实现仍待交付」改为「R2.1a：离线 HTML／全量 CSV 导出」，含 202/export_id、24h 保留、清扫边界、脱敏与原子发布说明 | PASS |

plan R2.1a 行与 D11（exports/ 24h、export_id 寻址、0700/0600——`mkdir(mode=0o700)`、`os.chmod`、temp 0600，POSIX 权限测试 `test_private_modes_links_and_replaced_directory`）、D15（后端输出层统一脱敏）、D16（系统字体栈＋CJK fallback）均随上表覆盖；spec 11 个场景全部有对应测试。

### 契约未变检查

- `git diff 10bc530..HEAD -- sbtd-runtime/contracts/` 为空（0 行），含 OpenAPI 与 panel-manifest/schema。
- `git diff --name-only 10bc530..HEAD` 全部 16 个文件中无任何 PRD、ADR 0001/0002/0003、dashboard、schema/manifest 路径；`CSV_SCHEMA_VERSION` 仍为 `"1.1"`。无 CONTRACT-CHANGE-NEEDED。

### 测试执行（developer-local，raw 输出在仓外 `/tmp/r21a-reverify/`，不入 Git）

| 命令 | 实际结果 | exit |
|---|---|---|
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py' -v` | Ran 301 tests，OK（skipped=2，均 "Windows junction evidence only"），46.797s | 0 |
| `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_runtime_r1_acceptance -v` | Ran 68 tests，OK，0.579s | 0 |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_golden_contracts.OpenApiDraftTests -v` | Ran 15 tests，OK，0.060s | 0 |
| `RUFF_NO_CACHE=true ruff check <7 个 diff 改动 .py>` | All checks passed! | 0 |
| `RUFF_NO_CACHE=true ruff format --check <同范围>` | 7 files already formatted | 0 |

计数与 round-2 记录（298／65／12）的 +3 差异已由 rebase base 解释：#150 契约测试随 `10bc530` 引入（OpenApiDraftTests 6e2cc56=12 → 10bc530=15，HEAD 仍为 15），非本轮新增。已知跳过：2 个 Windows junction 测试（与 round-2 相同）；dashboard tests／typecheck／build 未运行（dashboard 源码与静态产物未改）；本轮未重跑真实 serve 重启 smoke 与浏览器检查——round-2 证据在案（HTML 14100 bytes、CSV 51855 bytes、两次 SHA-256 相同、13 panels／0 scripts／0 resources），离线不变量由上述测试断言覆盖。工作树复核后干净，无 `__pycache__`／`.ruff_cache` 落入仓内。

### 复核结论

**PASS（无代码变更）**：九项验收与 D11/D15/D16 全部有实现与测试证据，契约 diff 为空，四套测试与 ruff 全绿，未发现 blocker，无需修复提交，无 CONTRACT-CHANGE-NEEDED。本轮仅新增本节 docs 记录。

### 模型使用（operator 按 session jsonl 回填）

| 用途 | 请求模型 | 实际模型 | assistant messages | 工具调用次数 |
|---|---|---|---|---|
| 复核主会话 | kimi-code/k3:max | unknown | unknown | unknown |
| 会话标题生成 | unknown | unknown | unknown | unknown |

本轮未派生 subagent。
