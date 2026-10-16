---
schema_version: 1
id: v2.1.0-rc.1-r1.0-contracts
workflow_mode: strict
mode_source: user
mode_note: 用户本次明确要求 SBTD strict mode，并指定 strict.md。
status: "done"
branch: feat/v2.1.0-rc.1-r1.0-contracts
created_at: '2026-10-16T13:31:08.139862+08:00'
updated_at: "2026-10-16T14:15:43.663354+08:00"
completed_at: "2026-10-16T14:15:43.663354+08:00"
---
交付 v2.1.0-rc.1 的 R1.0 数据与权限契约。不实现 R1.1 及以后的 Facade、存储、采集器或 HTTP 服务。

未完整调用 grill-with-docs。PRD v0.2、已接受 ADR 0001 与用户本次交付清单已经固定放置目录、核心子集、鉴权和宿主门禁。没有未决产品问题需要访谈。领域术语与数据所有权仍按 strict 触发审查，不把“未 grill”写成 DDD 或 DDIA 豁免。

## 范围

- 新顶层 `sbtd-runtime/`：数据字典、事件 JSON Schema、指标目录、OpenAPI 草案、capability pin、golden dataset、可执行名词／分母／去重测试。
- ADR Q6 表格「必须实际采集到」改为「通过条件」，与只标记单个宿主 unsupported 一致。
- 不引入 starlette／uvicorn，不改 task.md 事实源，不实现 Dashboard。

## 验收

- golden dataset 上的名词、分母和去重规则有可执行测试，且通过。
- §7.2 核心子集加组件真实调用可计算；§8.2 其余指标预留并标 unsupported，不返回 0。
- token／费用为条件性字段：有来源则保留，缺失可见且不为 0。
- OpenAPI 草案按 ADR Q5 固定 loopback、一次性配对换会话、CSRF、Host／Origin。
- 仓库禁止 `.feature`；持久场景使用 `sbtd-runtime/spec/r1.0-contract-scenarios.md`，中文正文，英文 Given／When／Then。

## 测试 seam

公开接口是 `sbtd-runtime/contract_eval.py` 的 `evaluate(dataset, scope)` 与事件 schema 校验。用户完成门已指定该消费者接口，不另开访谈。

## Book Gate Plan

| Reviewer | 客观触发／阶段 | Lifecycle | 谓词与结果 |
|---|---|---|---|
| book-ddd-distilled-modeling | 领域术语与规则，需求确认前 | before-dev | confirmed。见正文 DDD Boundary Review。未完整 grill，本审查不是 grill 二次订正。 |
| book-ddia-data-design | schema、事实源、去重与恢复边界，设计确认前 | before-dev | confirmed。R1.0 不落库；纯函数评估 golden。见正文 DDIA Data Design Review。 |
| book-legacy-change-safety | 既有行为缺陷或高回归既有代码 | before-dev | not-needed。不改既有生产行为；ADR 只改措辞。 |
| book-refactoring-pass | 既有生产代码编辑前 | before-dev | not-needed。只新增文件，不编辑既有生产代码。 |
| book-release-readiness | 生产运行时／部署／集成变化，验证后 | finish | not-needed。无服务、作业、迁移或发布；OpenAPI 只是草案。 |
| TDD | 数据换算与分母，实现前 | implement | 先红后绿。seam 为 evaluate。 |
| gherkin-bdd | 可观察契约行为 | before-dev | traceable。源仓不生成 .feature。 |
| ponytail | 实现选型 | implement | 单模块纯函数，不引入新依赖。 |

## DDD Boundary Review

Status: confirmed

Ubiquitous language: 任务状态、运行状态、Gate 结论、测试结果、发布是不同名词。组件真实调用只指 Skill／Tool 的 invocation attempt；available／loaded 不是调用。unsupported 不是 0，也不是连坐标记。token／费用缺失不是 0 或免费。分母为 0 的成功率是无可判定样本。叶子任务与汇总父任务分开。证据 validated、declared、present、stale 不同。重放确认、内容冲突、多来源合并是三种去重结果。

Bounded contexts: task.md 事实源；Runtime 观察投影；分宿主 capability；本地 API 权限；未来 Dify 只预留。观察库不回写任务状态。

Invariants and business rules: 同键同内容只确认；同键异内容 conflict 且不覆盖；时间戳不能单独做去重键；同一 invocation 多来源合并为一个执行对象；父子相同 request 用量不双计；未关联事件不按最近任务补齐；核心子集不得整类 unsupported；单宿主失败只标该宿主。

Core / supporting / generic subdomains: 核心是观察名词、去重和分母；支撑是 OpenAPI 权限草案与 capability pin；通用是 JSON Schema／OpenAPI 载体。

Corrections to the grill-with-docs result: none。未完整 grill，没有可订正的访谈结论。

Open conflicts and questions: none。快照不可变与宿主真实 smoke 已写入契约，分别留到 R1.3 与 R1.2b，不在本包假装完成。

## DDIA Data Design Review

Status: confirmed

Data owner and source of truth: 任务 mode／status 仍属 task.md。观察事件的未来所有者是用户私有 audit store；本包只固定 schema，并用内存纯函数评估 golden。指标是可重建投影。registry 与长期凭证属 `SBTD_RUNTIME_HOME`，不进 Git。capability pin 是仓库契约，不是探测结果。

Write / read / async / failure paths: R1.0 无写入路径、无 HTTP、无队列。evaluate 不修改输入。冲突保留先接受的事件并报告 conflict。缺失用量保持缺失。未实现指标返回 unsupported，不写 0。

Consistency model: 单次内存评估是确定性强一致。无跨进程缓存。未来存储的至少一次投递只在 schema 预留 ingest_seq、watermark 与 Idempotency-Key。

Idempotency / ordering / retry / deduplication: 优先键 `(source_id, source_event_id)` 加规范化内容。无来源 ID 时用分段、偏移和内容摘要。同一 invocation／operation 合并。冲突是毒消息，不覆盖。

Schema / migration / backfill / rollback / replay: schema 1.0 封闭信封，extensions 只收白名单标量。本包无迁移。回滚是撤销契约文件，无数据迁移。

Observability and repair: 采集缺口与 unsupported 是一等结果。spool、checkpoint、SQLite 不在本阶段。

Required tests: schema、去重处置、分母字面量、缺失不为 0、unsupported 不为 0、单宿主 capability、时间窗口。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-16T13:31:16.528516+08:00 | planned | in-progress | 前置门已记录，开始实现 R1.0 契约 | ai/tasks/v2.1.0-rc.1-r1.0-contracts/task.md |
| 2026-10-16T14:15:40.412329+08:00 | in-progress | checking | 契约测试与独立审查修正已完成，进入验收 | python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts on bc0d7a6 |
| 2026-10-16T14:15:43.663354+08:00 | checking | done | R1.0 名词、分母和去重测试通过，审查 P2 已修 | ai/tasks/v2.1.0-rc.1-r1.0-contracts/check.md |
