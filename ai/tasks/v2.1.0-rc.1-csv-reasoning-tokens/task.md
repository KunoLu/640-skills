---
schema_version: 1
id: v2.1.0-rc.1-csv-reasoning-tokens
workflow_mode: strict
mode_source: user
mode_note: 用户本次明确要求 SBTD strict，单独的契约变更 PR。
status: "done"
branch: feat/v2.1.0-rc.1-csv-reasoning-tokens
created_at: '2026-10-17T10:36:00+08:00'
updated_at: '2026-10-17T12:57:37+08:00'
completed_at: '2026-10-17T12:57:37+08:00'
---
本次是契约变更：在 CSV 固定列末尾追加 `reasoning_tokens`。范围是 PRD §13.8 固定列清单、OpenAPI 导出下载的机器可读列清单、`csv_export.COLUMNS`、golden 数据与对应测试。不开始 R1.4，不扩大范围。

未完整调用 grill-with-docs。用户已固定措辞：追加在固定列末尾、既有列顺序不变、它是 `output_tokens` 的子集不能再加到 output 上、宿主未报告时值为 null 且 CSV 单元格留空绝不填 0。没有未决产品问题需要访谈。

## 范围

- PRD §13.8 固定列清单末尾追加 `reasoning_tokens`，并补一句语义说明（子集、不双算、null 留空）。
- `sbtd-runtime/contracts/openapi.yaml`：OpenAPI 原本没有 CSV 列清单，本次在 `downloadExport`（`/api/v1/exports/{export_id}/file` GET）的 200 响应增加 `x-sbtd-csv-columns` 机器可读完整列表与 `x-sbtd-csv-column-notes` 语义说明。
- `sbtd-runtime/csv_export.py`：`COLUMNS` 末尾追加 `"reasoning_tokens"`，模块 docstring 同步语义。不改序列化逻辑。
- golden：`sbtd-runtime/golden/dataset.json` 的 req_1 `reasoning_tokens` 由 null 改为 2；`expected.json` 的 `usage.tokens.reasoning_tokens` 期望值随之从 null 变 2，`output_tokens` 保持 5。
- 测试：`test_csv_export.py` 锁定末列与既有列顺序及 null 留空；`test_golden_contracts.py` 锁定 OpenAPI `x-sbtd-csv-columns` 与 `csv_export.COLUMNS` 一致；`test_stats_query.py` 更新 golden 期望值断言。
- 场景加在 `sbtd-runtime/spec/r1.3-stats-api-scenarios.md`（reasoning_tokens 是 output 子集，未报告留空）。

## 验收

- `COLUMNS[-1] == "reasoning_tokens"`，`metadata_value` 是倒数第二列，既有列顺序断言不变。
- OpenAPI `x-sbtd-csv-columns` 与 `csv_export.COLUMNS` 完全一致，由测试锁定。
- `output_tokens` 不加上 `reasoning_tokens`（不双算）；宿主未报告时单元格留空，绝不填 0。
- golden oracle 通过：`usage.tokens` 的 `reasoning_tokens=2`、`output_tokens=5`。
- `sbtd-runtime/tests` 全部通过，R1 包装测试无回归；ruff 对本次触及文件干净，`test_golden_contracts.py` 沿用 main 上既有的 1 个 I001 与格式 finding，不由本 PR 引入或改动。

## 测试 seam

公开 seam 是 `csv_export.COLUMNS`／`serialize_csv` 与 OpenAPI 草案文档。断言末列身份、既有列顺序、null 留空、OpenAPI 列清单与序列化器一致。不测私有实现。

## Book Gate Plan

| Reviewer | 客观触发／阶段 | Lifecycle | 谓词与结果 |
|---|---|---|---|
| book-ddd-distilled-modeling | 领域术语与规则，需求确认前 | before-dev | not-needed。术语既有：`usage.tokens` 已含 reasoning 语义。未完整 grill。 |
| book-ddia-data-design | 派生读视图列追加，设计确认前 | before-dev | confirmed。见正文。 |
| book-legacy-change-safety | 既有 CSV 列契约变更 | before-dev | characterized。见正文。 |
| book-refactoring-pass | 既有生产代码编辑前 | before-dev | not-needed。只在 `COLUMNS` 追加一个字符串并改 docstring，无结构变化。 |
| book-release-readiness | 生产运行时／部署，验证后 | finish | not-needed。无服务、作业、迁移或发布；库模块由调用方显式调用。 |
| TDD | 列顺序与导出行为 | implement | 先红后绿。 |
| gherkin-bdd | 可观察导出行为 | before-dev | traceable。源仓不生成 .feature。场景在 `sbtd-runtime/spec/r1.3-stats-api-scenarios.md`。 |
| ponytail | 实现选型 | implement | 只追加一列，复用既有行投影；不新依赖，不引入列配置机制。 |

## DDIA Data Design Review

Status: confirmed

Data owner and source of truth: CSV 是快照 dataset 的派生只读视图，不是事实源。新增列是追加，向后兼容读取按列名定位；既有列的位置、含义与序列化规则不变。

Schema / migration / backfill / rollback / replay: 无存储 schema 变更；`event.schema.json` 早已有 `usage.reasoning_tokens`（integer|null），本变更只把它投影到导出列。`export_schema_version` 用户已决定升为 1.1（因追加 reasoning_tokens 列）。回滚是还原本提交，不动已入库事件。

Required tests: 末列身份与既有顺序、OpenAPI 列清单一致、null 留空、golden oracle 期望值。

## Legacy Change Safety Review

Status: characterized

Behavior to change: CSV 固定列清单末尾多一列 `reasoning_tokens`；golden req_1 的 usage 从“宿主未报告 reasoning”改为“报告 2”。

Behavior to preserve: 既有列顺序与含义不变；null 留空不填 0；`output_tokens` 不双算；BOM、转义、不截断规则不变。

Safety net: 既有 CSV header 测试与 golden oracle 作安全网，既有列顺序断言不变；新增红测先锁定末列与 OpenAPI 列清单一致，再改 `COLUMNS`。

Validation plan: 红测先失败（`COLUMNS[-1]` 不是 `reasoning_tokens`、OpenAPI 无 `x-sbtd-csv-columns`），再改契约与实现，然后跑 `sbtd-runtime/tests`、R1 包装测试与 ruff。

## 契约措辞

PRD §13.8（docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md）：

> `reasoning_tokens` 追加在固定列末尾，既有列顺序与含义不变；它是 `output_tokens` 的子集，不能再加到 output 上（不得 output_tokens + reasoning_tokens 双算）；宿主未报告时值为 null，CSV 单元格留空，绝不填 0。

OpenAPI `x-sbtd-csv-column-notes`（sbtd-runtime/contracts/openapi.yaml）：

> Appended last; existing column order unchanged. Subset of output_tokens; must not be added to output_tokens. When the host does not report it the value is null and the CSV cell is empty, never 0.

## 待确认问题

1. 【已解决】OpenAPI 原本没有 CSV 列清单，本次在 `downloadExport` 200 增加 `x-sbtd-csv-columns` 机器可读完整列表并以测试锁定与 `csv_export.COLUMNS` 一致；用户决定：`export_schema_version` 升为 `1.1`；OpenAPI 增加 `x-sbtd-csv-schema-version: "1.1"`。
2. golden req_1 的 `reasoning_tokens` 由 null 改为 2，`usage.tokens.reasoning_tokens` 期望值随之从 null 变 2，`output_tokens` 保持 5。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-17T10:36:00+08:00 | planned | in-progress | contract change scoped by user: append reasoning_tokens to PRD §13.8 fixed CSV columns, OpenAPI, csv_export.COLUMNS, golden and tests | docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md:1198; sbtd-runtime/csv_export.py COLUMNS; branch from origin/main cd5b26988fa31cd19895ad375fa895224601b953 |
| 2026-10-17T10:42:00+08:00 | in-progress | verifying | PRD/OpenAPI/COLUMNS/golden/tests changed; running suites | docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md; sbtd-runtime/contracts/openapi.yaml; sbtd-runtime/csv_export.py; sbtd-runtime/golden/dataset.json; sbtd-runtime/golden/expected.json; sbtd-runtime/spec/r1.3-stats-api-scenarios.md; sbtd-runtime/tests/test_csv_export.py; sbtd-runtime/tests/test_golden_contracts.py; sbtd-runtime/tests/test_stats_query.py |
| 2026-10-17T11:06:52+08:00 | verifying | done | all relevant suites pass | `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p test_*.py` → Ran 191 tests, OK (baseline main 187; +4 new); `python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_runtime_r1_event_store tests.test_sbtd_runtime_r1_facade tests.test_sbtd_runtime_r1_history_import tests.test_sbtd_runtime_r1_host_adapters tests.test_sbtd_runtime_r1_stats_api` → Ran 191 tests, OK (contracts 42 OK, stats_api 59 OK); `ruff format --check` + `ruff check` clean on csv_export.py, test_csv_export.py, test_stats_query.py; test_golden_contracts.py has the same pre-existing ruff findings (1 I001 + format) on main, unchanged by this PR; golden oracle test passes with usage.tokens reasoning_tokens=2, output_tokens=5 |
| 2026-10-17T12:57:37+08:00 | done | done | user decided bump export_schema_version 1.0→1.1 on PR #137 | `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p test_*.py` → Ran 191 tests, OK; `python3 -B -m unittest tests.test_sbtd_runtime_r1_stats_api tests.test_sbtd_runtime_r1_contracts` → Ran 101 tests, OK; `ruff format --check` + `ruff check` clean on csv_export.py, test_csv_export.py; test_golden_contracts.py keeps the same pre-existing ruff findings (1 I001 + format) on main, unchanged by this PR; new assertions lock CSV_SCHEMA_VERSION=="1.1" and OpenAPI x-sbtd-csv-schema-version=="1.1" |
