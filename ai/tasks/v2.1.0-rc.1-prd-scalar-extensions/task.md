---
schema_version: 1
id: v2.1.0-rc.1-prd-scalar-extensions
workflow_mode: strict
mode_source: user
mode_note: 用户本次明确要求 strict 模式，并要求把任务记录写盘。
status: "checking"
branch: docs/v2.1.0-rc.1-prd-scalar-extensions
created_at: '2026-10-16T23:37:07.631749+08:00'
updated_at: "2026-10-16T23:37:49.596787+08:00"
completed_at: null
---
修订 PRD v0.2，使扩展字段表述与已发布的 `event.schema.json` 一致：扩展值标量-only（string、number、boolean、null），嵌套数据由宿主适配器拍平（如 `a.b` 键）或丢弃。同时在 `ai/tasks/v2.1.0-rc.1-secret-key-match/task.md` 把 PRD-vs-schema 开放项标记为已解决（2026-10-16 用户决定），并把 Book Gate Plan 中“扩展值可嵌套后入库”的触发行改为“嵌套扩展值被 schema 拒绝，不入库”。

未完整调用 grill-with-docs。用户已直接给出决定与措辞，无未决产品问题；schema 与实现已于 PR #132 发布，本轮只做文档对齐。纯文档 PR，不改代码、schema 或场景。

## 范围

- 只改 `docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md` 的扩展行，以及 `ai/tasks/v2.1.0-rc.1-secret-key-match/task.md` 的开放项与 gate 表触发行。
- 不改 `sbtd-runtime/` 代码、`event.schema.json`、场景、测试或变更日志。
- `group_dimensions` 的 JSON 小对象表述属于指标模型，不在本次决定范围。

## 验收

- PRD 扩展行写明标量-only（string、number、boolean、null），嵌套数据由宿主适配器拍平或丢弃。
- secret-key-match task.md 开放项标记已解决并注明 2026-10-16 用户决定。
- gate 表触发行不再声称嵌套扩展值入库。
- 提交、推送、开 PR 到 main，不合并。

## Book Gate Plan

| Reviewer | 客观触发／阶段 | Lifecycle | 谓词与结果 |
|---|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 后或领域歧义，需求确认前 | before-dev | not-needed。未完整 grill；用户决定已定，无新边界。 |
| book-ddia-data-design | schema／持久化设计稳定前 | before-dev | not-needed。不改 schema、数据或所有权；文档对齐已发布 schema。 |
| book-legacy-change-safety | 既有行为变更前 | before-dev | not-needed。不改任何行为。 |
| book-refactoring-pass | 既有生产代码编辑前 | before-dev | not-needed。无生产代码编辑。 |
| book-release-readiness | 运行时／部署变更，验证后 | finish | not-needed。纯文档。 |
| TDD | 高风险行为 | implement | not-needed。无代码改动。 |
| gherkin-bdd | 可观察行为 | before-dev | not-needed。无行为变化。 |
| ponytail | 实现选型 | implement | not-needed。文档措辞最小改动。 |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-16T23:37:10.365966+08:00 | planned | in-progress | PRD extension row and secret-key-match task record edits are applied | docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md extension row now scalar-only; ai/tasks/v2.1.0-rc.1-secret-key-match/task.md open item resolved and gate trigger fixed |
| 2026-10-16T23:37:49.596787+08:00 | in-progress | checking | docs-only diff reviewed against acceptance criteria | git diff: PRD extension row scalar-only, open item resolved with 2026-10-16 decision, gate trigger fixed; no code/schema/test changes; wording not pinned by any test (grep-verified) |
