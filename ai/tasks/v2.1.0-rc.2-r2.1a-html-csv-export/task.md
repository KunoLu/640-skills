---
schema_version: 1
id: v2.1.0-rc.2-r2.1a-html-csv-export
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict；仅 plan R2.1a 与 D11/D15/D16。不改契约；显式 git add；不 push、不开 PR；不暂存或提交 .omp-r12b-addendum.txt、ai/tasks/codex-verify/。保持 OpenAPI、Panel manifest/schema、ADR 0001/0002/0003、PRD、CSV schema 1.1 不变。不可避免的契约变化 STOP + CONTRACT-CHANGE-NEEDED。
status: blocked
blocked_reason: CONTRACT-CHANGE-NEEDED：POST /api/v1/exports 未定义 requestBody 或 snapshot_id、格式、presentation_state 输入；实现必需新增外部请求约定，超出当前不改契约授权。
branch: feat/v2.1.0-rc.2-r2.1a-html-csv-export
created_at: '2026-10-20T15:07:13+08:00'
updated_at: '2026-10-20T15:09:39.646430+08:00'
completed_at: null
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
| book-ddd-distilled-modeling | 作业／快照引用／会话授权与两目录所有权 | before-dev | blocked；领域不变量已明确，创建作业的 HTTP 输入未定义 |
| book-ddia-data-design | 导出持久产物、manifest、异步作业与恢复 | before-dev | blocked；不能在未定义的输入协议上稳定作业设计 |
| book-legacy-change-safety | serve 鉴权、CSV 与 snapshot 高回归面 | before-dev | planned；因契约 STOP 未进入行为修改，未声称 characterized |
| book-refactoring-pass | 修改既有生产代码 | before-dev | planned；因契约 STOP 未修改生产代码 |
| book-release-readiness | HTTP 服务与导出作业 runtime 改变 | validation 后 | planned；未实现／未测试，不声称 release ready |

已读 plan、grill D11/D15/D16/R1e、PRD §10.4/§13、OpenAPI exports 与全部 components schemas、CSV、SnapshotStore、serve、ReportDocument、PinRegistry、ADR 0003。未完整调用 grill-with-docs：范围和验收已锁定，无须重开需求。Python LSP references 实际返回 No language server found，已以源码查找 serialize_csv 与 API 调用证据补充。尚未进入生产编辑。

## 状态持久化限制

已核对分支、路径与 ignore；安装的 TaskStore.create 实际返回 `TaskStateError: task has no YAML frontmatter block`，completed_steps 为空。未写 active 指针；不修改禁止路径或旧 catalog 来绕过。此共享 task.md 是用户明确要求的交付记录，沿用 R2.0c 做法，不声称 TaskStore lifecycle／自动恢复成功。

## 验证计划

原计划沿用 sbtd-runtime/spec 中文场景 + 英文 Given/When/Then，主会话唯一验证 controller，执行 runtime Python tests、受影响 Dashboard tests、CI wrapper、真实 serve 导出／重启 smoke 和独立复核。因用户明确 STOP 条件已触发，本轮未进入这些阶段；不创建未实现的场景／测试／报告占位，不把契约诊断算功能验收。

## 风险与后续范围

- Snapshot disk-usage cap：Reviewy follow-up，仅记录，非本任务实现范围。
- R2.1b JPEG/PDF／Playwright 与 R2.2 跨平台证据不实现；Windows ACL／macOS 不冒充本机验证。
- 不修复无关历史 probe_links 失败；若命中如实保留。

## CONTRACT-CHANGE-NEEDED

**已触发；按用户硬边界停止实现。**

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
| 主会话：契约调查／docs backfill／STOP 记录（未实施生产代码） | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra（host 标识；high 仅请求档位） | unknown（未取得完整会话日志计数） | unknown |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-20T15:07:13+08:00 | planned | in-progress | 用户明确 strict 与 R2.1a；分支、基线匹配；创建明确授权共享交付记录，非 TaskStore lifecycle 成功 | git branch/rev-parse；用户附加 prompt；TaskStore.create 失败且无 completed_steps |
| 2026-10-20T15:09:39.646430+08:00 | in-progress | blocked | CONTRACT-CHANGE-NEEDED：创建导出缺少固定快照／格式／呈现状态的请求协议；按用户硬边界停止，不自行扩展外部契约 | openapi.yaml:414–430、661–747；PRD §13.2–13.3；实际 YAML 解析 requestBody_present=False，参数仅 CsrfToken/IdempotencyKey；八个受保护文件逐字节未变 |
