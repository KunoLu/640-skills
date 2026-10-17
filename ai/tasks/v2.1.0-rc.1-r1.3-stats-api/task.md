---
schema_version: 1
id: v2.1.0-rc.1-r1.3-stats-api
workflow_mode: strict
mode_source: user
mode_note: 用户本次明确要求 SBTD strict task（task.md 结构对齐 R1.2c）。
status: "done"
branch: feat/v2.1.0-rc.1-r1.3-stats-api
created_at: '2026-10-17T08:46:30+08:00'
updated_at: '2026-10-17T09:43:07+08:00'
completed_at: '2026-10-17T09:43:07+08:00'
---
交付 v2.1.0-rc.1 的 R1.3：统计查询、历史读取、ReportSnapshot、数据集 cursor 分页与全量 CSV 序列化，产物是库模块与 unittest。不做 R1.4 安全／版本兼容收口，不做 R2 Dashboard／JPEG／PDF，不动 `/api/v1/exports*` 的 rc.2 标记，不改契约语义。

未完整调用 grill-with-docs。PRD v0.2 §8.4／§8.5／§9（含 §9.5）／§13.8 与 §15.2 R1.3 行，加上用户本次交付清单和三条硬门，已经固定范围和完成门：半开区间 `[from, to)`；query／timeseries／dataset／CSV 共享同一 snapshot_id；缺失数据不编造（不填 0、0 样本成功率不是 100%）。没有未决产品问题需要访谈。

## 范围

- 新增 `sbtd-runtime/stats_query.py`：QueryScope 规范化（schema_version、range、timezone、filters、metrics 校验，无效输入明确报错，不静默默认）、指标目录服务、统计 query 与 timeseries。指标值一律调用 `contract_eval.evaluate`，不复制分母规则；filters 在进入 evaluate 前收窄事件总体。timeseries 按 §8.5 默认桶规则切分，每桶仍是 `[start, end)` 半开子窗口。
- 新增 `sbtd-runtime/report_snapshot.py`：不可变快照（query_hash、watermark_seq、source_watermarks、dataset_manifest、snapshot_digest）。相同规范化 scope 且冻结视图内容指纹未变时复用同一 snapshot_id；迟到事件（包括 payload `ingest_seq=0` 的真实生产者事件）生成新 id。QueryScope filters 同时收窄指标与明细行。dataset cursor 绑定 snapshot_id，跨快照翻页报错。明细数据族按稳定序排列，页合计等于 manifest 总数，不缺不重。
- 新增 `sbtd-runtime/csv_export.py`：§13.8 固定列、`record_type` 数据族、UTF-8 BOM、公式注入转义（`= + - @` 及前导控制字符）、null 留空不填 0、全量遍历 snapshot dataset，不截断。
- 新增 `sbtd-runtime/history_read.py`：事件列表读取（task_uid／类型／半开时间窗过滤、稳定排序、不透明 cursor 分页）与 `task_history`（任务状态／模式历史）。复用 `EventStore.replay()` 输出，不改 append／dedup。
- 不新增 ASGI 服务：本包仍是库实现，OpenAPI 把 R1.3 相关操作标成 `library`，`/api/v1/exports*` 保持 `v2.1.0-rc.2`。
- 场景在 `sbtd-runtime/spec/r1.3-stats-api-scenarios.md`。测试在 `sbtd-runtime/tests/test_stats_query.py`、`test_report_snapshot.py`、`test_csv_export.py`、`test_history_read.py`，CI 包装 `tests/test_sbtd_runtime_r1_stats_api.py`。

## 验收

- 半开区间：`occurred_at == to` 的事件不计入；Tokyo／UTC／DST（25 小时民事日）都有测试。
- 共享快照：query、timeseries、dataset 各页、CSV 全部引用同一 snapshot_id；cursor 跨快照被拒绝。
- 不编造数字：0 可判定样本的成功率为 `null` + `no-decidable-sample`；缺失 token／cost 为空而非 0；CSV null 留空。
- golden 完成门：对 `sbtd-runtime/golden/dataset.json` 按 `query_scope` 查询，指标值与 `expected.json` 一致；CSV 遍历完整数据集不截断，行数与 manifest 合计一致。
- cursor 分页全范围无缺页无重复；无效 cursor 明确报错。
- `sbtd-runtime/tests` 全部通过，既有 R1 包装测试无回归，ruff format／check 干净（仅沿用既有的有意 BLE001 模式）。

## 测试 seam

公开 seam 是 `normalize_scope`／`serve_catalog`／`query`／`timeseries`、`SnapshotStore.create_or_reuse`／`get`／`dataset_page`、`serialize_csv`、`list_events`／`task_history`／`paginate`。指标语义的消费方是 `contract_eval.evaluate`，不在本包重算。不测私有表结构。

## Book Gate Plan

| Reviewer | 客观触发／阶段 | Lifecycle | 谓词与结果 |
|---|---|---|---|
| book-ddd-distilled-modeling | 领域术语与规则，需求确认前 | before-dev | confirmed。见正文。未完整 grill。 |
| book-ddia-data-design | 快照／水位／cursor／CSV 数据设计，设计确认前 | before-dev | confirmed。见正文。 |
| book-legacy-change-safety | 既有行为变更 | before-dev | not-needed。不改既有模块；只新增库文件和契约标记。 |
| book-refactoring-pass | 既有生产代码编辑前 | before-dev | not-needed。不编辑既有生产代码。 |
| book-release-readiness | 生产运行时／部署，验证后 | finish | not-needed。无服务、作业、迁移或发布；库模块由调用方显式调用。 |
| TDD | 查询／快照／CSV 行为，实现前 | implement | 先红后绿。 |
| gherkin-bdd | 可观察查询与导出行为 | before-dev | traceable。源仓不生成 .feature。场景在 `sbtd-runtime/spec/r1.3-stats-api-scenarios.md`。 |
| ponytail | 实现选型 | implement | 复用 contract_eval、metrics-catalog、EventStore.replay。不新依赖，不起 HTTP 服务，不实现 Dashboard／JPEG／PDF。 |

## DDD Boundary Review

Status: confirmed

Ubiquitous language: 查询区间是半开 `[from, to)`，`occurred_at == to` 在窗外。ReportSnapshot 是某一查询条件在某一接收水位下的不可变视图；`query_hash` 标识筛选语义，`watermark_seq` 标识取数上界。同一 response family（query／timeseries／dataset／CSV）共享一个 snapshot_id；cursor 属于某个快照，不属于查询。`no-decidable-sample` 表示没有可判定样本，不是 0% 也不是 100%。缺失的 token／cost 是 unknown／null，不是 0。`record_type` 数据族区分一行表示什么；明细族用于核验，不与 metric 汇总行相加。

Bounded contexts: `contract_eval` 仍拥有名词、分母与去重语义；本包只拥有 QueryScope 校验、总体收窄、快照身份、分页与 CSV 序列化。事件库仍拥有原始观察与 checkpoint；本包只通过 `replay()` 读。任务事实源仍是 task.md；history 读取不改写它。HTTP 服务、exports 作业、Dashboard 不属于本包。

Invariants and business rules: 无效时间／维度／指标报错，不替换成默认范围。快照不混页；过期快照不冒用旧 id。导出遍历完整筛选范围，不截断。用户文本按 `csv-text-escape-v1` 转义。null 不填 0。

Core / supporting / generic subdomains: 核心是共享快照与半开窗口下的忠实统计。支撑是 QueryScope 规范化与 cursor 分页。通用是 CSV 引号／BOM／转义。

Corrections to the grill-with-docs result: none。未完整 grill。

Open conflicts and questions: QueryScope `filters.evidence_levels` 映射到 `provenance.evidence_status`（证据等级）；`include_unknown_time` 只影响未知时间事件是否进入明细与附属集合展示，不改变 evaluate 的窗口归属规则。数据集 tasks 投影由调用方提供；从事件推导时只造最小 task 记录，不猜测 role。

## DDIA Data Design Review

Status: confirmed

Data owner and source of truth: 事件库拥有原始观察；快照是派生的不可变读视图，不是新事实源。快照不落盘、不改写事件；进程内存持有，过期即拒绝读取。

Write / read / async / failure paths: 读路径是 `replay()` → 过滤 → `evaluate`／明细行。无写路径。cursor 只编码 snapshot_id 与 offset，不携带数据；坏 cursor 明确报错。CSV 生成遍历 cursor 全页，失败不产出半成品“成功文件”。

Consistency model: 同一快照内 query／timeseries／dataset／CSV 看到同一冻结事件集。复用由 query_hash 加冻结视图内容指纹（event_id＋canonical content＋source_watermarks）决定；真实生产者的 payload `ingest_seq` 恒为 0（EventStore 只在 SQL 列分配序号），所以指纹而非 payload 序号判定新旧。迟到事件后同 query_hash 不复用旧快照，生成新 snapshot_id；旧快照不悄悄变化。

Idempotency / ordering / retry / deduplication: 明细行按（数据族序，record_id）稳定排序；cursor 翻页确定。重复创建同条件同水位快照只复用，不复制数据。

Schema / migration / backfill / rollback / replay: 无 schema 变更。OpenAPI 只改实现标记，不改路径／schema 语义。

Observability and repair: `dataset_manifest` 记录各族总数、过滤边界与未知时间集合；`quality_summary` 沿用事件库质量计数。快照 digest 是固定数据包摘要，不是可信时间戳。

Required tests: 半开窗口（Tokyo／UTC／DST）；共享 snapshot_id；0 样本率；缺失 token／cost；golden 计数一致；cursor 合计等于 manifest；CSV BOM／转义／null 空／不截断。

## 待确认问题

1. `filters.evidence_levels` 取 `provenance.evidence_status` 语义；若后续 PRD 明确另有所指，需单独契约变更。
2. CSV 中结构化指标值（如分布）以紧凑 JSON 放在 `metric_value` 列；标量仍按数值输出。
3. 快照为进程内库对象；R1.4 若需要跨进程保留期，再按 §10 存储布局落盘，属另一工作包。
4. `group_by` 超出 R1.3 范围：非空即 QueryScopeError，不返回伪装成已分组的全局值（openapi 的 QueryScope 本就 `additionalProperties: false` 且无此字段）。
5. `watermark_seq` 报告 payload `ingest_seq` 高水位；快照复用不由它判定（见 DDIA 一致性条目）。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-17T08:46:30+08:00 | planned | in-progress | R1.3 scope is fixed by PRD §8.4/§8.5/§9/§13.8 and work package R1.3; failing query/snapshot/CSV tests start before the libraries exist | docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md:684, :706, :810, :1173, :1381; sbtd-runtime/spec/r1.3-stats-api-scenarios.md |
| 2026-10-17T09:43:07+08:00 | in-progress | done | libraries landed with CI wrapper; all acceptance rows verified by tests; independent review findings (stale reuse, unfiltered rows, hardcoded meta, silent defaults) fixed and re-verified | `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p test_*.py` → Ran 187 tests, OK; `python3 -B -m unittest tests.test_sbtd_runtime_r1_stats_api` → Ran 56 tests, OK; prior wrappers (contracts/facade/event_store/host_adapters/history_import) → OK; `ruff format --check` and `ruff check` on all new/touched files clean; golden gate: query over `golden/dataset.json` with `query_scope` matches all 34 `expected.json` metric values, 0 mismatches; dataset pages (limit 13) total 86 rows == dataset_manifest sum == CSV detail rows, no duplicates, UTF-8 BOM present |
| 2026-10-17T09:30:09+08:00 | in-progress | verifying | libraries and tests landed; running unittest + ruff before PR | sbtd-runtime/stats_query.py; report_snapshot.py; csv_export.py; history_read.py; sbtd-runtime/tests/test_*.py |
| 2026-10-17T09:30:09+08:00 | verifying | done | 182 sbtd-runtime tests OK; R1.3 CI wrapper 51 OK; golden metric values match expected; ruff clean; OpenAPI R1.3 ops marked library; exports* stay rc.2 | `python3 -m unittest discover -s sbtd-runtime/tests` (182 OK); `python3 -m unittest tests.test_sbtd_runtime_r1_stats_api` (51 OK); `ruff check` on new modules |

