---
schema_version: 1
id: v2.1.0-rc.1-r1.4-acceptance
workflow_mode: strict
mode_source: user
mode_note: 用户本次明确要求 SBTD strict task（task.md 结构对齐 R1.3），且 R1.4 只做验收收口，不开新产品功能。
status: "done"
branch: feat/v2.1.0-rc.1-r1.4-acceptance
created_at: '2026-10-17T14:31:56+08:00'
updated_at: '2026-10-17T14:40:38+08:00'
completed_at: '2026-10-17T14:40:38+08:00'
---
交付 v2.1.0-rc.1 的 R1.4：安全、审计边界与版本兼容的**验收收口**。产物是验收场景文档、验收报告、安装／使用文档、锁定既有行为的验收测试与 CI 包装。不新增产品 API、不建落盘快照存储、不起 HTTP 服务、不做 Dashboard／JPEG／PDF，不动 `/api/v1/exports*` 的 rc.2 标记，不改契约语义。

未完整调用 grill-with-docs。PRD v0.2 §15.2 R1.4 行、§16.1／§16.2 验收矩阵（AC-01…AC-32）与 R1 适用的导出安全（AC-50、AC-53）、§20.1 需求一交付物、§20.3 需求一完成定义，加上用户本次交付清单（场景 md＋验收报告＋文档＋锁定测试＋CI 包装），已固定范围与完成门：UI 尚不存在时所有 R1 用户场景可完成，并如实说明不能采集的范围。没有未决产品问题需要访谈。

## 范围

- 新增 `sbtd-runtime/spec/r1.4-acceptance-scenarios.md`：安全／审计边界／版本兼容验收场景（中文正文、英文 Given/When/Then），每条场景标注对应的既有或新增测试。覆盖审计边界（观察关闭无 audit.db、未注册／相邻目录／symlink 拒绝、观察路径不改写 task.md、只读不写）、去重与冲突（同键确认、冲突保留先接受者）、版本兼容（事件 schema 1.0、QueryScope 1.0、CSV 1.1＋末列 reasoning_tokens、未来版本如实拒绝）、无远程业务控制端点（AC-32 的库面语义）、以及 R1 诚实缺口（codex smoke、进程内快照、无 HTTP／Dashboard）。
- 新增 `sbtd-runtime/tests/test_r1_acceptance.py`：验收锁定测试。钉住版本针（`CSV_SCHEMA_VERSION == "1.1"`、`COLUMNS[-1] == "reasoning_tokens"`、OpenAPI `x-sbtd-csv-schema-version` 与 `x-sbtd-csv-columns`、QueryScope const `"1.0"`、事件 schema `schema_version` const `"1.0"`、exports* 仍为 `v2.1.0-rc.2` 且非 rc.1 阻塞）、QueryScope 对未来 schema 版本的如实拒绝、OpenAPI 无远程业务控制操作，以及经由既有 EventStore 表面的薄验收冒烟（观察关闭无 audit.db／spool、只读 open 不落盘、同键确认、冲突保留先接受者）。不复制既有重夹具；AC→测试的完整映射靠场景文档与报告引用既有测试名。
- 新增 CI 包装 `tests/test_sbtd_runtime_r1_acceptance.py`（沿用既有 importlib 模式）。
- 新增 `sbtd-runtime/docs/install-and-use.md`：§20.1「安装／使用文档」——可选启用、项目授权／注册、观察关闭、升级注意、卸载与数据保留（audit.db／spool／registry），如实声明 R1 无 Dashboard。交叉引用 docs/host-adapters.md。
- 新增 `sbtd-runtime/docs/r1.4-acceptance-report.md`：§20.1 交付物与关键 AC（01–32、50、53）到测试名＋命令＋结果的映射；版本兼容叙述（event 1.0／QueryScope 1.0／CSV 1.1）；明确「有意推迟（非 R1.4 产品工作）」一节：Dashboard／JPEG／PDF／HTTP 导出服务／落盘快照保留／CORS 等。
- OpenAPI 只做验收标注：info summary 提及 R1.4 验收收口；不改路径／schema 语义，`/api/v1/exports*` 保持 `v2.1.0-rc.2`。
- CHANGELOG 双语 Unreleased 条目（沿用 R1.3 风格），更新 `ai/tasks/index.md`。

## 验收

- 「本地 API 包」= 既有 `sbtd-runtime/` 库面；文档给出 PYTHONPATH 导入用法；不发明 PyPI 发布。
- 场景文档每条验收场景可追溯到具体测试名；R1 范围外 AC 在报告中明确标 deferred 到 R2，不悄悄声称已完成。
- CSV 合同（#137 已并入）：`export_schema_version=1.1`，末列 `reasoning_tokens` 是 `output_tokens` 子集、绝不回加、未报告留空不填 0——全部有锁定断言。
- 快照保持进程内语义；§10 的 24 小时保留期期望与当前实现差异在报告与文档中如实写明。
- `sbtd-runtime/tests` 全部通过，新增 R1.4 CI 包装通过，既有 R1 包装无回归，ruff format／check 干净（仅沿用既有的有意 BLE001 模式）。

## 测试 seam

公开 seam 是 `csv_export.CSV_SCHEMA_VERSION`／`COLUMNS`、`stats_query.SCHEMA_VERSION`／`normalize_scope`／`serve_catalog`、`event_store.EventStore.open`／`append`／`replay`，以及 `contracts/openapi.yaml`、`contracts/event.schema.json` 两个契约文件。验收测试只通过这些公开表面钉住行为，不测私有表结构、不发明新产品 API。

## Book Gate Plan

| Reviewer | 客观触发／阶段 | Lifecycle | 谓词与结果 |
|---|---|---|---|
| book-ddd-distilled-modeling | 领域术语与规则，需求确认前 | before-dev | confirmed。见正文。未完整 grill。 |
| book-ddia-data-design | 保留期／版本兼容的数据设计表述，设计确认前 | before-dev | confirmed。见正文。 |
| book-legacy-change-safety | 既有行为变更 | before-dev | not-needed。不改既有模块行为；只加验收测试、文档与契约标注。 |
| book-refactoring-pass | 既有生产代码编辑前 | before-dev | not-needed。不编辑既有生产代码。 |
| book-release-readiness | 生产运行时／部署，验证后 | finish | not-needed。无服务、作业、迁移或发布；验收产物为文档与测试。 |
| TDD | 验收锁定断言 | implement | 版本针与薄验收断言先写；对当前主干应直接转绿，只在针错误时先红。 |
| gherkin-bdd | 可观察验收行为 | before-dev | traceable。源仓不生成 .feature。场景在 `sbtd-runtime/spec/r1.4-acceptance-scenarios.md`。 |
| ponytail | 实现选型 | implement | 复用既有 EventStore／stats_query／csv_export 表面与既有测试做 AC 映射。不新依赖，不起 HTTP 服务，不建落盘快照存储。 |

## DDD Boundary Review

Status: confirmed

Ubiquitous language: 验收（acceptance）是把 §16 验收矩阵钉到可执行测试与报告，不是新功能。审计边界：观察开关关闭时无任何审计落盘；注册根之外的路径（未注册、相邻目录、symlink）一律拒绝。版本兼容：事件 `schema_version` 1.0 是入库前提；QueryScope `schema_version` 必须是 `"1.0"`，未知未来版本明确报错而非静默接受；CSV `export_schema_version` 1.1 表示末列追加 `reasoning_tokens` 后的列集（1.0 早于该列）。「诚实缺口」指如实报告 R1 不能采集或尚未实现的范围，不用 0、绿灯或空词冒充。

Bounded contexts: 事件库仍拥有原始观察、去重与 checkpoint；facade 仍拥有注册与业务副作用边界；本工作包只拥有「验收证据的组织」——场景、报告、锁定测试。契约文件（openapi.yaml、event.schema.json）语义不变，只加验收标注。Dashboard、导出服务、远程控制不属于本包也不属于 R1。

Invariants and business rules: 同 `(source_id, source_event_id)` 同内容只确认；同键不同内容冲突且先接受者不被覆盖。观察关闭、未确认、只读、symlink 的 runtime home 不创建 audit.db 与 spool。未报告的可选字段（reasoning_tokens、cache tokens、cost）留空，绝不填 0。未来 schema 版本被拒绝并指明字段，不降级解释。

Core / supporting / generic subdomains: 核心是审计边界与版本兼容的可证明性。支撑是 AC→测试的映射组织。通用是文档与报告格式。

Corrections to the grill-with-docs result: none。未完整 grill。

Open conflicts and questions: AC-05「并列 worktree 分开」在事件 scope 模型（project/repository/worktree 三段身份）与 facade 注册测试层面覆盖，没有独立的 worktree 移动场景测试；在报告中如实标注覆盖方式。codex 真实 smoke 由另一 bot 执行，本包只核对 capability matrix 的如实标记。

## DDIA Data Design Review

Status: confirmed

Data owner and source of truth: 本工作包不产生新业务数据。验收报告与场景是文档；锁定测试只读契约文件与调用既有库表面。audit.db／registry.json 的所有权不变。

Write / read / async / failure paths: 验收测试的写路径只有临时目录里的 EventStore 冒烟（同键确认、冲突保留），进程结束即清理。无迁移、无回填。

Consistency model: 版本兼容叙述固定为：事件 schema 1.0（入库拒绝未来版本）、QueryScope 1.0（normalize_scope 拒绝非 1.0）、CSV 1.1（#137 追加列，顺序不变、只增不改）。三者各自独立演进，报告逐条钉到测试。

Idempotency / ordering / retry / deduplication: 验收测试重复运行无残留（全部临时目录）。CI 包装沿用 importlib 模式，重复发现不产生冲突名。

Schema / migration / backfill / rollback: 无 schema 变更。OpenAPI 仅 info summary 标注，路径与 schema 不动；exports* 保持 rc.2。

Observability and repair: 报告记录每条验收命令的真实输出计数；失败记录保留，不以旧 HEAD 或缓存输出证明新提交。

Required tests: 版本针（event 1.0／QueryScope 1.0／CSV 1.1／reasoning_tokens 末列／exports rc.2）；QueryScope 未来版本拒绝；观察关闭无 audit.db；只读 open 不落盘；同键确认；冲突保留先接受者；OpenAPI 无远程业务控制操作。

## 待确认问题

1. AC-05 的 worktree 分离目前靠 scope 三段身份与注册测试间接覆盖；如后续要求独立的 worktree 移动场景测试，属新测试工作而非本收口范围。
2. §10.4 的 ReportSnapshot 24 小时保留期是「临时快照」期望；当前实现为进程内对象，进程退出即消失，比 24h 更短。报告与文档如实陈述该差异；落盘保留属未来工作，不在 R1.4 建。
3. codex@0.163.0 真实 smoke 状态以 capability-matrix.json 为准，本任务不改 smoke 结果。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-17T14:31:56+08:00 | planned | in-progress | R1.4 是验收收口：PRD §15.2 R1.4 行、§16.1/§16.2、§20.1/§20.3 与用户交付清单固定了范围；场景与锁定测试先于报告 | docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md:1386, :1410, :1661; sbtd-runtime/spec/r1.4-acceptance-scenarios.md |
| 2026-10-17T14:40:38+08:00 | in-progress | done | 场景、锁定测试、CI 包装、安装／使用文档与验收报告全部落地；全部验收行为由测试钉住，R2 项在报告 deferred 节明确声明 | `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py'` → Ran 207 tests, OK（基线 191 + 新增 16）；`python3 -B -m unittest tests.test_sbtd_runtime_r1_acceptance` → Ran 16 tests, OK；既有 R1 包装（contracts/facade/event_store/host_adapters/history_import/stats_api）→ Ran 191 tests, OK；`ruff format --check` 与 `ruff check` 对两个新 Python 文件干净；OpenAPI 仅 info summary 标注，`/api/v1/exports*` 保持 `v2.1.0-rc.2` |
