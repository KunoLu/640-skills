---
schema_version: 1
id: v2.1.0-rc.1-r1.0-review-fixes
workflow_mode: strict
mode_source: user
mode_note: '用户本次明确要求 SBTD strict mode，只修 PR #129 Reviewy 三项 review 发现。'
status: "done"
branch: feat/v2.1.0-rc.1-r1.0-contracts
created_at: '2026-10-16T15:30:27.888827+08:00'
updated_at: "2026-10-16T15:30:36.581372+08:00"
completed_at: "2026-10-16T15:30:36.581372+08:00"
---
修复 PR #129（分支 feat/v2.1.0-rc.1-r1.0-contracts）Reviewy 的三项 review 发现，不扩大范围。

未完整调用 grill-with-docs。三项修复的可观察语义已由 ADR 0001 第 166 行（兜底完成门）、PRD v0.2 第 1355 行（rc.1 不把 Dashboard／导出列为阻塞交付）与 PRD §10.2／AC-56（Host／Origin 与 CSRF 拒绝）固定，无未决产品问题。

## 范围

- `sbtd-runtime/contracts/capability-matrix.json` 增加 `completion_gate` 字段，编码 ADR 第 166 行兜底完成门：至少一个门禁宿主在真实 smoke 采到 Skill 或 Tool 调用事件才完成；两宿主均 unsupported 则 R1 不通过、回到用户重新决策，不得放行。
- `sbtd-runtime/contracts/openapi.yaml` 的 `/api/v1/exports*` 全部 operation 标注 `x-sbtd-release: v2.1.0-rc.2` 与 `x-sbtd-rc1-blocking: false`。
- `components.responses` 抽可复用 403 响应 `Forbidden`（Host／Origin 拒绝、CSRF 拒绝），挂到全部相关接口。
- 同文件既有 `smoke_note` 与数据字典第 14 行同步，不引入新评估器、不改 `contract_eval.py`、不实现 R1.2b 真实 smoke。
- 测试：`CapabilityMatrixTests` 断言 `completion_gate` 存在且语义与 ADR 一致；`OpenApiDraftTests` 断言导出接口标注与 403 复用引用。
- 不扩大范围：不改其他接口 release 标注，不改 `acceptance_pins`／`pass_condition` 既有语义，不改事件 schema 或指标目录。

## 验收

- 新增测试在契约修改前失败（红），修改后 `sbtd-runtime/tests` 与 `tests/test_sbtd_runtime_r1_contracts.py` 全部通过（绿）。
- 场景同步写入 `sbtd-runtime/spec/r1.0-contract-scenarios.md`，中文正文，英文 Given／When／Then，不生成 `.feature`。
- 独立只读复核覆盖完成门语义、导出标注与 403 权限语义。
- 修复本身已由 `11804fbb1f2130607c23df2a5fe5ae3cf5bd8af9` 提交并 push。本记录是其后的补记，不代替该修复提交。

## 测试 seam

契约文件 JSON／YAML 字段：`MATRIX` 的 `completion_gate` 与 OpenAPI doc 的 operation 级扩展、`components.responses.Forbidden` 及其 `$ref`。沿用 `sbtd-runtime/tests/test_golden_contracts.py` 的既有 fixture 加载；新增 `CapabilityMatrixTests` 类，不引入 `evaluate` 依赖。用户明确指定该文件与字段，seam 无需再确认。

## Book Gate Plan

| Reviewer | 客观触发／阶段 | Lifecycle | 谓词与结果 |
|---|---|---|---|
| book-ddd-distilled-modeling | 完成门是领域规则编码，需求确认前 | before-dev | confirmed。见正文 DDD Boundary Review。该正文写于契约编辑前，本次补记不重跑。 |
| book-ddia-data-design | 共享契约 schema 编辑，设计确认前 | before-dev | confirmed。见正文 DDIA Data Design Review。该正文写于契约编辑前，本次补记不重跑。 |
| book-legacy-change-safety | 既有行为缺陷或高回归既有代码 | before-dev | not-needed。契约 review 字段缺失，非既有运行时行为缺陷。 |
| book-refactoring-pass | 既有生产代码编辑前 | before-dev | not-needed。只编辑 JSON／YAML 契约、测试与规范文档，不改 `contract_eval.py`。 |
| book-release-readiness | 生产运行时／部署／集成变化，验证后 | finish | not-needed。OpenAPI 仍为 contract-only 草案，无服务、作业、迁移或发布。 |
| TDD | 契约字段与测试断言，实现前 | implement | 先红后绿。红因是 KeyError completion_gate／x-sbtd-release／Forbidden，共 6 error。提交后精确 SHA 两条命令各 41／41。 |
| gherkin-bdd | 可观察契约行为 | before-dev | traceable。场景入 `sbtd-runtime/spec/r1.0-contract-scenarios.md`。 |
| ponytail | 实现选型 | implement | 最小结构化字段，复用既有测试加载器，不新增评估器或依赖。 |
| 独立审查 | 授权语义与公开 API 契约 | check | confirmed。ContractReview 五项无发现。对象是提交前工作树的 5 个契约文件，不含随后的 CHANGELOG。 |

## DDD Boundary Review

Status: confirmed

Ubiquitous language: 「兜底完成门」是 R1 组件真实调用的发布门，不是单宿主能力标记。宿主通过＝真实 smoke 采到 Skill 或 Tool 调用事件（至少一种）；parser fixture 不是该证据。unsupported 是单宿主能力状态，不是 R1 整体失败。R1 不通过且回到用户决策，与「放行」互斥。rc.2 导出接口不是 rc.1 阻塞项；403 拒绝是权限契约结果，不是 401 凭证缺失。

Bounded contexts: 宿主 capability 验收（矩阵拥有完成门规则）；R1.2b 真实 smoke 执行（拥有宿主实测状态，本任务不运行）；API 权限契约（OpenAPI 拥有 Host／Origin 与 CSRF 拒绝的 403 语义）；发布切分（PRD §15.0 拥有 rc.1／rc.2 阻塞属性）。

Invariants and business rules: 完成门只认两个门禁宿主 `codex@0.163.0`、`omp@18.11.1`；minimum_passing_hosts＝1；两宿主均 unsupported 时不得放行、回到用户决策；parser fixture 不计入通过证据；完成门不得代替 R1.2b 真实 smoke；导出接口标 rc.2 不改变 R1 数据所有权。

Core / supporting / generic subdomains: 核心是完成门与宿主验收不变量；支撑是导出发布标注与 403 权限语义；通用是 JSON／YAML 载体。

Corrections to the grill-with-docs result: none。未完整 grill，无可订正的访谈结论。

Open conflicts and questions: none。R1.2b 真实 smoke 仍不在本任务，保留为既有边界。

## DDIA Data Design Review

Status: confirmed

Data owner and source of truth: `capability-matrix.json` 拥有完成门决策规则与 acceptance pins；宿主实测状态归 R1.2b 真实 smoke，本任务不写实测结果，矩阵 `smoke_status` 保持 `not-run`。OpenAPI 拥有 API 发布标注与响应契约。任务 mode／status 仍归 task.md。

Write / read / async / failure paths: 无写路径、无队列、无迁移。契约是只读静态文件，测试只读加载。两宿主均 unsupported 的失败路径以 `both_unsupported` 显式编码为回到用户决策，不得放行。

Consistency model: 单文件静态契约，强一致。completion_gate 与 acceptance_pins 的宿主集合一致性由测试断言，不允许漂移。

Idempotency / ordering / retry / deduplication: 不适用。无事件流；completion_gate 不新增幂等键或顺序约束。

Schema / migration / backfill / rollback / replay: 在既有 JSON 上新增字段，向后兼容；回滚＝撤销契约文件。OpenAPI 新增响应组件与 operation 级扩展，不改既有路径形状。

Observability and repair: 完成门不通过是显式契约状态，不伪造 smoke 结果。`smoke_note` 更新为说明本文件只冻结决策规则。

Required tests: `completion_gate` 字段存在且语义与 ADR 一致；导出接口标注 rc.2 且非 rc.1 阻塞；403 组件存在并被相关接口引用；非导出接口不被误标 rc.2。

## 补录

上一会话于 2026-10-16T14:54:10+08:00 写出上述 Book Gate 正文。当时 TaskStore 缺 markdown-it-py，记录未落盘，也没有使用 2026-10-16T15:20:00 这类整点时间。本次事件时间是 TaskStore 观察到的落盘时钟，不回填工作发生时间。

工作证据：修复提交 `11804fbb1f2130607c23df2a5fe5ae3cf5bd8af9`，AuthorDate 2026-10-16T15:05:16+08:00。提交后精确 SHA 复跑时间为 2026-10-16T15:05:59+08:00，两条命令各 41／41、exit 0。raw 与中文汇总在本任务 reports/，受 gitignore 保护，不入库。详见 check.md。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-16T15:30:29.667044+08:00 | planned | in-progress | 补记已完成的三项 review 修复；先前因缺 markdown-it-py 未能落盘，事件时间是落盘时钟，不回填工作发生时间 | 11804fbb1f2130607c23df2a5fe5ae3cf5bd8af9 |
| 2026-10-16T15:30:33.093313+08:00 | in-progress | checking | 提交后精确 SHA 复跑两条契约命令各 41/41 通过，进入验收记录 | ai/tasks/v2.1.0-rc.1-r1.0-review-fixes/reports/unit-report-sbtd-runtime-r1-contracts-2026_10_16-15_00_00.txt |
| 2026-10-16T15:30:36.581372+08:00 | checking | done | 独立复核五项检查无发现，Book Gate 结论已记入任务正文；completed_at 是落盘时钟，工作完成证据仍是 11804fb 与 15:05:59 的 41/41 | ai/tasks/v2.1.0-rc.1-r1.0-review-fixes/check.md |
