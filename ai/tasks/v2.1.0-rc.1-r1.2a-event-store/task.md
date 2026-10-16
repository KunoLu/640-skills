---
schema_version: 1
id: v2.1.0-rc.1-r1.2a-event-store
workflow_mode: strict
mode_source: user
mode_note: 用户本次明确要求 SBTD strict mode。
status: "in-progress"
branch: feat/v2.1.0-rc.1-r1.2a-event-store
created_at: '2026-10-16T19:15:14.094444+08:00'
updated_at: "2026-10-16T19:46:40.848371+08:00"
completed_at: null
---
交付 v2.1.0-rc.1 的 R1.2a：事件库、去重、spool、checkpoint、质量记录。产物是本地存储与恢复机制。不做 R1.2b 宿主适配器、R1.2c 历史导入、R1.3 API。

未完整调用 grill-with-docs。PRD v0.2 第 1378 行、ADR 0001 与用户本次交付清单已经固定范围和完成门：重放、乱序、截断、崩溃、部分失败均有测试；事件符合 R1.0 event schema；观察开关关闭时不建事件库、不写 spool。没有未决产品问题需要访谈。PRD/ADR 未单独立项的存储细节采用最保守做法，并记入待确认问题，不扩大范围。

## 范围

- 在 `sbtd-runtime/` 增加本地事件库。位置是 `SBTD_RUNTIME_HOME` 的 `audit.db` 与 `spool/`。一个 SQLite 文件，WAL。原始事件与 checkpoint、质量记录分表。不建 projections.db、快照、导出或 HTTP。
- 事件必须通过 R1.0 `event.schema.json`。去重键复用 R1.0 `contract_eval.dedup_key` / `canonical_content`。同键同规范化内容只确认；同键不同内容 conflict，保留先接受的记录。
- 开关关闭、开关不可读、未确认、只读、symlink 运行时目录：不创建 `audit.db`，不写 spool。
- Facade 任务写入仍不自动产生观察事件。开关开启时既有 `audit_status=gap` 与不创建事件库的 R1.1 行为保持。Runtime 来源适配器属于 R1.2b。
- 不回放覆盖 `task.md`。不导入历史。不扫描 sibling／HOME。不把未授权 spool 文件当成本库 producer 的待入库事件。

## 验收

- 重放：相同事件再次入库只确认，接受计数不变。
- 乱序：较晚 `occurred_at` 先到、较早的后到，两条都保留；重放按入库顺序，不按发生时间覆盖。
- 截断：spool 尾部截断不补造事件；损坏的 `audit.db` 拒绝打开，不换成空库并宣称完整。
- 崩溃：spool 已落盘而数据库未提交时，重新打开能恢复且不重复计数。
- 部分失败：同一批里已提交的保留，未提交的保持 pending 或拒绝；失败不报成已全部接受。
- 开关关闭时 Facade 等价性测试仍通过。
- `sbtd-runtime/tests` 与相关仓库测试、lint 通过。

## 测试 seam

用户完成门已指定消费者接口：本地存储与恢复。公开 seam 是 `EventStore.open` / `append` / `replay` / `checkpoint` / `quality`。不另开访谈。不测私有表结构。

## Book Gate Plan

| Reviewer | 客观触发／阶段 | Lifecycle | 谓词与结果 |
|---|---|---|---|
| book-ddd-distilled-modeling | 领域术语与规则，需求确认前 | before-dev | confirmed。见正文。未完整 grill。 |
| book-ddia-data-design | 持久化事件、spool、恢复，设计确认前 | before-dev | confirmed。见正文。 |
| book-legacy-change-safety | 既有开关关闭路径高回归 | before-dev | characterized。不改 Facade 写入路径；既有等价性测试是安全网。 |
| book-refactoring-pass | 既有生产代码编辑前 | before-dev | not-needed。不编辑既有生产文件，只新增事件库。若后续必须改 Facade，先重跑本门。 |
| book-release-readiness | 生产运行时／部署／迁移，验证后 | finish | not-needed。无服务、作业、发布或 schema 迁移工具。本地库 schema_version=1，未知版本拒绝修改。 |
| TDD | 高风险存储与恢复，实现前 | implement | 先红后绿。 |
| gherkin-bdd | 可观察恢复行为 | before-dev | traceable。源仓不生成 .feature。场景在 `sbtd-runtime/spec/`。 |
| ponytail | 实现选型 | implement | stdlib sqlite3，复用 contract_eval 去重，不新依赖，不建投影。 |

## DDD Boundary Review

Status: confirmed

Ubiquitous language: 事件库是用户私有的原始观察记录，不是任务状态机，也不是统计 API。去重确认不是第二次计数。conflict 保留先接受的事件，不覆盖。spool 是尚未提交到事件库的待入库批次。checkpoint 记录来源实例、分段、偏移和 parser 版本，不是文件 mtime。质量记录陈述接受、确认、冲突、拒绝、截断和缺口，不计算未知分母的覆盖率。重放返回已接受事件的入库顺序。观察开关关闭不是“写了再删”。`audit_status=gap` 仍表示 Facade 没有把业务写入记成已采集。

Bounded contexts: task.md 仍拥有任务 mode／status／history。registry／config 仍拥有授权与开关。事件库拥有原始观察、去重账、checkpoint 和质量记录。指标投影、快照、CSV、HTTP 不属于本包。宿主日志解析不属于本包。

Invariants and business rules: 不得从观察事件回放覆盖 task.md。开关关闭、不可读、未确认或只读时不创建事件库、不写 spool。同 `(source_id, source_event_id)` 且规范化内容相同只确认。同键内容不同不覆盖。无来源事件 ID 时键含分段、偏移和内容摘要，时间戳不是键。无法绑定任务的事件保持未关联。损坏的原始库不静默清库重建。未知 schema 拒绝修改。

Core / supporting / generic subdomains: 核心是可恢复的原始事件与去重。支撑是 checkpoint 与质量记录。通用是 SQLite WAL 与文件权限。

Corrections to the grill-with-docs result: none。未完整 grill，没有可订正的访谈结论。

Open conflicts and questions: Facade 在开关开启后是否自动写观察事件，PRD §7.1 与 R1.2b 边界未在本行结案；本包不自动写。无来源事件 ID 时，R1.0 字典把内容摘要放进键内，因此同偏移不同内容是不同键；不另造冲突规则。`event.corrected` 不在 R1.0 schema 枚举中，不发明该事件类型。

## DDIA Data Design Review

Status: confirmed

Data owner and source of truth: 已接受原始事件的事实源是 `SBTD_RUNTIME_HOME/audit.db` 的 events 表。spool 只拥有尚未提交的批次。task.md 仍是任务事实源。config.json 拥有观察开关。质量记录与 checkpoint 属于事件库，不是业务授权。

Write / read / async / failure paths: 确认开关且调用方确认后，先把批次 fsync 到 spool 的 ready 文件，再按事件提交 SQLite。读取是 `replay`，按 `ingest_seq`。无跨进程队列，无 HTTP。失败路径：schema 拒绝不入库；同键冲突不覆盖；数据库提交失败则该事件保持 pending；进程在 spool ready 之后、提交之前退出，下次打开恢复。截断的尾行不入库。`audit.db` 损坏或 schema 未知时拒绝打开，不替换成空库。

Consistency model: 单进程读己之写。一个 SQLite 文件，WAL。不承诺跨资源 exactly-once，不承诺多机共享 WAL。已提交事件对随后的 `replay` 可见。

Idempotency / ordering / retry / deduplication: 去重键与 R1.0 `canonical_content` 一致，排除 `event_id`、`recorded_at`、`ingest_seq`。入库顺序由库分配 `ingest_seq`，不信任生产者序号，也不按 `occurred_at` 重排已接受记录。重试只确认。乱序到达都保留。

Schema / migration / backfill / rollback / replay: 库 schema_version 为 1。无历史导入，无回填。未知版本拒绝修改。回滚不删除已接受原始事件。重放不改 task.md。

Observability and repair: 质量记录保存 accepted、duplicate、conflict、rejected、truncated、pending、gap。不计算覆盖率百分比。checkpoint 保存 source_id、source_instance、segment_id、offset、parser_version。连缺口文件都写不了时，不宣称缺口已持久化。

Required tests: 重放不重复计数；乱序两条都在且顺序是入库序；spool 截断不补造；损坏库拒绝且不换空库；崩溃后恢复一次；部分失败不把未提交事件报成已接受；开关关闭零审计文件。

## Legacy Change Safety Review

Status: characterized

Behavior to change: 无。本包不改变 Facade 或 helper 的可观察行为。

Behavior to preserve: 开关关闭时适配调用与直接 helper 的业务文件相同，且没有 audit.db／spool。开关开启时 Facade 仍报 gap，且任务写入不创建审计文件。

Current reproduction evidence: 既有 `test_switch_off_matches_direct_helper_and_writes_no_audit` 与 `test_switch_on_reports_gap_without_event_store` 已在 main 9933c79 通过（R1.1 #130）。本任务开始前不改这些测试的断言。

Safety net: 上述既有测试保持为回归网。新增事件库测试使用独立运行时目录，不经过 Facade 写入。

Hidden dependencies / seam: 事件库自行读取 config.json 的 `observation.enabled`，不调用 Facade 写路径。

Validation plan: 实现后重跑 `sbtd-runtime/tests`。

Review mode: normal

## Refactoring Review

Status: proceed

Review mode: normal

Existing-code scope: 不计划编辑既有生产文件。`contract_eval.py` 只被导入，不改其纯函数语义。

Behavior that must remain unchanged: Facade 与 helper 行为。

Structural friction: 无。新模块独立。

Decision and smallest safe step: no refactor needed。

Safety net and validation: 既有 facade 测试。

Deferred refactors: 不把去重逻辑从 contract_eval 抽到第三模块。

## 待确认问题

1. 观察开启后，Facade 业务写入是否应自动产生观察事件。本包不产生；R1.2b 之前开关开启的 Facade 仍是 gap。
2. 无来源事件 ID 时，同分段同偏移但内容不同是否应 conflict。R1.0 字典把摘要放进键，本包照做，不另造冲突。
3. `event.corrected` / `supersedes_event_id` 未进入 R1.0 schema。本包不发明更正事件，冲突只保留先接受的记录。
4. 入库时是否覆盖生产者带来的 `recorded_at` / `ingest_seq`。本包保存生产者原文，库内顺序只用自己的 `ingest_seq` 列；规范化比较仍排除这两个字段和 `event_id`。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-16T19:17:54.444262+08:00 | planned | in-progress | R1.2a scope is fixed by PRD and ADR; failing seam tests start before the store exists | docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md:1378 and docs/adr/0001-v2.1.0-rc.1-r1.0-runtime-decisions.md |
| 2026-10-16T19:45:43.998163+08:00 | in-progress | checking | R1.2a store tests and review fixes passed | python3 -B -m unittest discover -s sbtd-runtime/tests (70 ok); ruff check/format passed |
| 2026-10-16T19:45:47.731677+08:00 | checking | done | R1.2a event store, dedup, spool, checkpoint, and quality records are delivered | https://github.com/KunoLu/640-skills/pull/131 head 27c4201f951c219c0195ca583500fb8fb7dbb6a3; sbtd-runtime tests 70 passed |
| 2026-10-16T19:46:37.089145+08:00 | done | planned | review found camelCase secret names and foreign pending counts after the first done mark | event_store.py secret normalizer and pending ownership filter |
| 2026-10-16T19:46:40.848371+08:00 | planned | in-progress | apply the remaining secret-name and pending-count fixes | sbtd-runtime/tests/test_event_store.py secret and foreign pending assertions |
