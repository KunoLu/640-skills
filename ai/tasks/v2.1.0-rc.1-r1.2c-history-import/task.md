---
schema_version: 1
id: v2.1.0-rc.1-r1.2c-history-import
workflow_mode: strict
mode_source: user
mode_note: 用户本次明确要求 SBTD strict mode。
status: "done"
branch: feat/v2.1.0-rc.1-r1.2c-history-import
created_at: '2026-10-17T04:10:52.136051+08:00'
updated_at: "2026-10-17T04:45:53.629+08:00"
completed_at: "2026-10-17T04:45:53.629+08:00"
---
交付 v2.1.0-rc.1 的 R1.2c：把已有 task.md 状态历史和验证产物导入 R1.2a 事件库。产物是安全解析器和证据关系。不做 R1.2b 宿主适配器的重做，不做 R1.3 API、HTTP 或 Dashboard。

未完整调用 grill-with-docs。PRD v0.2 第 7.1 节、第 7.5 节与第 1380 行 R1.2c，加上用户本次交付清单，已经固定范围和完成门：不伪造历史发生时间，不因为 HTML 标题里有 passed 就记通过，不改写 task.md，导入前必须有显式批准的项目和来源范围。没有未决产品问题需要访谈。

## 范围

- 新增 `sbtd-runtime/history_import.py`。`build_scan_plan` 只记录调用方点名的项目根和来源，不列目录、不读文件、不扫描 sibling／HOME。`approve_scan_plan` 才把计划标成已批准。未批准不调用 `EventStore.append`。
- task.md 状态表复用 `TaskDocument.parse`。`at` 为 `unknown` 或无法证明时 `occurred_at` 为 null。`recorded_at` 只表示本次导入观察到的时间。不从 frontmatter 的 `created_at` 补 `task.created`。`task_uid` 保持 null，除非调用方显式传入。当前 frontmatter 模式不回写到历史行，`mode_at_event` 为 `unknown`。
- 验证产物复用 `validate_validation_evidence.validate_v2` 与 `parse_junit`／`parse_playwright`。报告关系放在 `validation`、`external_refs`、`correlation`。事件 schema 没有 `artifact` 对象，不新增载荷字段。扩展值只放标量。
- `validation.result=passed` 只在校验器接受、`e2eMode` 直接等于 `narrow`／`full-stack`／`contract-backed`、且解析出的用例有 passed 且没有 failed 时出现。HTML 标题不产生通过。
- 来源类型是 `artifact-imported`。观察开关关闭时不建 `audit.db`、不写 spool。不改写 task.md。
- 场景在 `sbtd-runtime/spec/r1.2c-history-import-scenarios.md`。测试在 `sbtd-runtime/tests/test_history_import.py`。

## 验收

- 未批准的扫描计划不导入，且只包含点名路径。
- 越界路径和符号链接被拒绝。
- 状态表里能证明的时间原样保留，`unknown` 为 null，task.md 字节不变。
- `done → planned` 是 `task.reopened`，不产生伪造的 `task.created`。
- 校验通过的 envelope 记 `passed` 与 `artifact-verified`；HTML 标题和无法映射的 `e2eMode` 不记通过。
- 同一计划再次导入只确认。开关关闭时不创建事件库。
- `sbtd-runtime/tests` 与相关仓库测试、ruff 通过。

## 测试 seam

公开 seam 是 `build_scan_plan`、`approve_scan_plan`、`import_plan`。消费方是 R1.2a `EventStore.append`。不测私有表结构。

## Book Gate Plan

| Reviewer | 客观触发／阶段 | Lifecycle | 谓词与结果 |
|---|---|---|---|
| book-ddd-distilled-modeling | 领域术语与规则，需求确认前 | before-dev | confirmed。见正文。未完整 grill。 |
| book-ddia-data-design | 导入写入事件库，设计确认前 | before-dev | confirmed。见正文。 |
| book-legacy-change-safety | 既有事件构造默认值 | before-dev | characterized。`base_event` 只加可选参数，默认仍是 host-observed／execution-observed。 |
| book-refactoring-pass | 既有生产代码编辑前 | before-dev | proceed。只给 `base_event` 加默认参数，不重构适配器。 |
| book-release-readiness | 生产运行时／部署，验证后 | finish | not-needed。无服务、作业、迁移或发布。导入是显式调用的本地解析。 |
| TDD | 扫描计划与解析，实现前 | implement | 先红后绿。 |
| gherkin-bdd | 可观察导入行为 | before-dev | traceable。源仓不生成 .feature。场景在 `sbtd-runtime/spec/r1.2c-history-import-scenarios.md`。 |
| ponytail | 实现选型 | implement | 复用 TaskDocument、现有证据校验器和 EventStore。不新依赖，不第二套 XML 解析。 |

## DDD Boundary Review

Status: confirmed

Ubiquitous language: 扫描计划是只读的范围说明，不是导入。批准是单独动作。导入把已有文件翻译成观察事件，不修改任务事实源。`occurred_at` 为空表示历史时间不可证明，`recorded_at` 表示导入时观察到。`artifact-verified` 只表示校验器接受了原生报告，不表示任务 done。HTML 标题不是结果。证据关系是 validation 事件上的 external_refs 与 correlation，不是一个新的 artifact 对象。

Bounded contexts: task.md 仍拥有任务 mode／status／history。事件库仍拥有原始观察、去重、checkpoint、质量记录。本包只拥有“点名文件 → 事件”的翻译。registry 不被读取来猜测项目。R1.3 的查询和 HTTP 不属于本包。

Invariants and business rules: 未批准不写入。不扫描未点名路径。不伪造 occurred_at。不从 HTML 标题制造 passed。不改写 task.md。不把当前模式写成历史模式。task_uid 不从路径推导。观察开关关闭时不建库。

Core / supporting / generic subdomains: 核心是状态表和验证 envelope 的忠实翻译。支撑是扫描计划的批准边界。通用是路径约束和事件库去重。

Corrections to the grill-with-docs result: none。未完整 grill。

Open conflicts and questions: 无法映射到 narrow／full-stack／contract-backed 的 e2eMode 不写入 validation 对象，以免编造必填的 e2e_scope。installation_id／device_id 仍由调用方显式传入。

## DDIA Data Design Review

Status: confirmed

Data owner and source of truth: task.md 与验证 envelope 是来源事实。事件库仍是已接受观察的事实源。扫描计划不落盘。导入不回写来源文件。

Write / read / async / failure paths: 批准后只读点名文件，产出事件交给 `EventStore.append`。spool 与崩溃恢复沿用 R1.2a。文件缺失、解析失败或校验失败不记成通过。开关关闭时打开事件库失败，不创建文件。

Consistency model: 与 R1.2a 相同，单进程读己之写。重复导入由来源键只确认。

Idempotency / ordering / retry / deduplication: task 行的 source_event_id 由相对路径和行号组成；放不进 128 字符时改用路径摘要作 segment_id，offset 为行号。验证事件用 envelope 相对路径和 runId。重试安全。

Schema / migration / backfill / rollback / replay: 无 schema 变更。这就是历史导入本身，不回填任务文件。重放不改 task.md。

Observability and repair: 回执沿用 accepted／duplicate／conflict／rejected。校验失败的 envelope 记 evidence_status=invalid，observation_level=declared。

Required tests: 未批准不写库；越界与符号链接拒绝；未知时间为 null；HTML 标题不通过；校验通过才 passed；重复导入只确认；开关关闭零审计文件。

## Legacy Change Safety Review

Status: characterized

Behavior to change: 无用户可见的既有行为。`base_event` 增加可选参数。

Behavior to preserve: 不传新参数时事件仍是 host-observed、execution-observed、evidence present、actor agent。R1.2a／R1.2b 测试断言不变。

Current reproduction evidence: 实现前先跑新增测试，预期因模块不存在而失败。既有适配器测试在实现后重跑。

Safety net: `sbtd-runtime/tests/test_omp_adapter.py` 与 `test_codex_adapter.py` 不改断言。

Hidden dependencies / seam: 导入复用 `EventStore.open` 的开关检查，不绕过 confirmed。

Validation plan: 红灯后实现，再跑 `sbtd-runtime/tests` 与相关仓库包装测试。

Review mode: normal

## Refactoring Review

Status: proceed

Review mode: normal

Existing-code scope: `sbtd-runtime/host_adapter.py` 的 `base_event`。

Behavior that must remain unchanged: 现有调用方不传新参数时的事件形状。

Structural friction: source_kind 与 evidence_status 写死在构造函数里。加默认参数即可。

Decision and smallest safe step: 只加默认参数。不把 R1.2b 适配器改成导入器。

Safety net and validation: 既有适配器测试。

Deferred refactors: 不把证据校验器搬进 sbtd-runtime。

## 待确认问题

1. installation_id／device_id 仍无运行时签发者。本包要求显式传入。
2. e2eMode 超出事件 schema 三档时，不写入 validation，也不记通过。
3. 解析器只暴露最后一次用例结果时，attempt_no 记 1，不把最后一次通过说成首次通过。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-17T04:10:59.780052+08:00 | planned | in-progress | R1.2c scope is fixed by PRD §7.1, §7.5, and work package R1.2c; failing scan-plan tests start before the importer exists | docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md:531, :584, :1380; sbtd-runtime/spec/r1.2c-history-import-scenarios.md |
| 2026-10-17T04:45:53.629+08:00 | in-progress | done | importer landed with CI wrapper; all acceptance rows verified by tests | `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p test_history_import.py` → Ran 12 tests, OK; `python3 -B -m unittest tests.test_sbtd_runtime_r1_history_import` → Ran 12 tests, OK; `python3 -B -m unittest tests.test_sbtd_runtime_r1_host_adapters tests.test_sbtd_runtime_r1_event_store` → Ran 66 tests, OK; `ruff format --check` on the three changed files clean; `ruff check` reports only two deliberate `BLE001` broad catches (any validator/parse failure means not accepted), matching event_store precedent; pre-existing sbtd-runtime lint findings unchanged |
