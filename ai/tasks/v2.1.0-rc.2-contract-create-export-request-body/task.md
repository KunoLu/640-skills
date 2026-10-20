---
schema_version: 1
id: v2.1.0-rc.2-contract-create-export-request-body
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict；2026-10-20 16:01 CST 已批准独立 createExport 请求契约变更。仅当前 contract 分支提交，显式 git add；不 push、不开 PR，不触 R2.1a 分支及两个禁止提交路径。
status: done
branch: contract/v2.1.0-rc.2-create-export-request-body
created_at: '2026-10-20T16:04:10.056607+08:00'
updated_at: '2026-10-20T09:42:56.591170+00:00'
completed_at: '2026-10-20T09:42:56.591170+00:00'
---

# createExport requestBody：独立契约变更

## 范围与验收

用户于 **2026-10-20 16:01 CST 批准此 contract change**；本记录可用于 operator 的 PR summary。基线 `e9cb05b84e449fe4a7dde1b5523faf7478bc310e`。只补齐 `POST /api/v1/exports` 的 JSON 请求、错误响应、契约测试和对应说明；完成不等于导出功能实现、发布或部署。

- required requestBody，命名 `CreateExportRequest`，required snapshot_id / format；format 仅 html、csv。
- optional presentation_state，采用现有 ReportDocument 的七字段结构；显式提供时完整，省略时采用既有默认呈现状态。呈现状态不修改 CSV 范围。
- request 与呈现对象封闭；动态键 map 仅接受既有 TS 模型的值类型。
- 复用 SnapshotId 参数的 string schema，不发明 UUID／新格式约束；400 BadRequest、404 NotFound、410 Gone；保留 202、403、Bearer、CSRF、Idempotency-Key。
- 查找消费者／生成器并保持同步；按既有惯例决定 info.version；CSV schema 始终 1.1。
- 契约测试、schema／引用验证、直接请求 smoke、独立 review；若修改 TS 类型才要求 typecheck。
- 禁止导出逻辑、24h retention／sweep、snapshot cap、R2.1a/b/R2.2 实现；不改 PRD、ADR 0001–0003、panel-manifest、plan R2.1a 行。
- 不暂存或提交 `.omp-r12b-addendum.txt`、`ai/tasks/codex-verify/`；不切分支、不 push、不开 PR。

## 事实与设计决定

已读 `git show f02fe5f:ai/tasks/v2.1.0-rc.2-r2.1a-html-csv-export/task.md`、PRD §13.2–13.3、OpenAPI exports/components、Dashboard `reportDocument.ts`、既有 OpenApiDraftTests 与场景。未完整调用 grill-with-docs：授权、语义与范围明确，不重复开启需求讨论。

DDD Boundary Review — confirmed。Snapshot 固定数据；Export 消费固定 snapshot_id；presentation_state 只影响呈现。Query & Snapshot 拥有查询／过期，Export 为支撑能力，访问控制为通用能力。未改变先前 grill 决定，无未决领域冲突。

DDIA Data Design Review — confirmed。OpenAPI 是 wire contract 事实源，七字段沿用既有 PresentationState；不会把 preview 行数、排序或隐藏图例当成 CSV 筛选。输入校验失败 400；找不到 404；已过期 410，不能自动换新 ID。幂等头与语义不变。没有持久数据／迁移／backfill；回滚为撤回本契约提交，必须在下游实现依赖它之前协调。测试覆盖必填、枚举、可选状态、嵌套类型、额外属性与错误响应。

## Book Gate Plan

| Gate | 触发事实 | 阶段 | 状态 |
|---|---|---|---|
| book-ddd-distilled-modeling | 固定快照与呈现／CSV 范围边界 | before-dev | passed / confirmed |
| book-ddia-data-design | 新 HTTP 请求 schema 与错误语义 | before-dev | passed / confirmed |
| book-legacy-change-safety | 不修改既有 runtime 行为；新增契约有直接 validator seam | before-dev | not-required |
| book-refactoring-pass | 无既有生产代码修改，只有声明式契约／测试／文档 | before-dev | not-required；无需重构 |
| book-release-readiness | 无 runtime／部署变更；导出端点仍未实现 | finish | not-required；不声称服务／发布就绪 |

主会话唯一 writer／验证 controller。独立 correctness 与 simplicity/readability review 在实现和 smoke 后执行。BDD 沿用 `sbtd-runtime/spec/r1.0-contract-scenarios.md`：中文正文、英文关键词；contract-only，Mock Strategy: none；测试 seam 为用户指定的 OpenAPI 文档，不模拟 HTTP 成功。

## 状态持久化限制

路径逐级检查无 symlink；本任务不存在；`git check-ignore` 确认 `.sbtd/active-task.json` 与 task reports 受保护，`git ls-files` 窄查无 tracked 本地状态／同任务文件。已知 TaskStore catalog 的 `task has no YAML frontmatter block` 失败由 R2.0c 及 f02fe5f blocker 记录提供；不重跑确认、不修改禁止路径绕过。此文件为用户明确要求的共享交付记录，沿用项目先例，不声称 TaskStore lifecycle、active 指针或自动恢复成功。未写 active／身份／ignore。

## 验证证据

本地契约验收完成，两位独立 reviewer 无阻塞问题；done 仅指本任务契约交付，不表示 R2.1a 实现／部署／发布。证据均 developer-local／dirty／local-only，不冒称 CI 或 PR head 证明。

- `git status --short --branch && git rev-parse --show-toplevel && git log -1 --format='%H %s'`：指定根、分支、基线匹配；仅两个用户禁止路径 untracked。
- `git show f02fe5f:ai/tasks/v2.1.0-rc.2-r2.1a-html-csv-export/task.md`：读取原 blocker，无分支切换。
- `git check-ignore .sbtd/active-task.json ai/tasks/v2.1.0-rc.2-contract-create-export-request-body/reports/probe.json && git ls-files -- .sbtd ai/tasks/v2.1.0-rc.2-contract-create-export-request-body`：保护成立，无 tracked 输出。
- eval availability：PyYAML、jsonschema、referencing 可用；openapi_spec_validator／openapi_core 未安装；不静默安装依赖。

### 实际修改与版本决定

- `sbtd-runtime/contracts/openapi.yaml`：required JSON body → CreateExportRequest；ExportPresentationState 对齐现有 TS 七字段，动态 map 值类型与 TS 一致；复用 SnapshotId/schema；新增 400/404/410 引用，BadRequest 描述覆盖请求体／格式错误。
- `sbtd-runtime/tests/test_golden_contracts.py`：5 个新 test_create_export_*；使用既有 jsonschema，不引入依赖。现有根 CI wrapper 自动装载此 TestCase。
- `sbtd-runtime/spec/r1.0-contract-scenarios.md`：新增四个中文／英文关键词契约场景。
- `sbtd-runtime/docs/install-and-use.md`：新增明确标注「服务实现仍待交付」的请求协议说明。
- 本 task：scope、gate、决策、原生命令与模型列表。

没有找到 createExport TS 客户端／生成类型／OpenAPI 生成器／API docs 页面；`reportDocument.ts` 既有 PresentationState 已完全匹配，无需修改，TS 类型与构建产物不变。源码搜索覆盖 runtime、dashboard、CI、脚本和既有 API 文档；没有启动生成器。`info.version` 保持 **1.0.0**：`git log -4 --format='%h %s' -- sbtd-runtime/contracts/openapi.yaml` 与 `git show c02c43c -- sbtd-runtime/contracts/openapi.yaml` 显示此前 additive CSV 契约只加元数据，未 bump info.version。此次不引入自动版本策略。CSV schema **1.1**、其列顺序、rc.2 exports 标注均由现有测试继续验证。

### 已执行命令与结果

所有命令在仓库根运行；原生 stdout／stderr／exit code／时间／平台存于 ignored `reports/<name>.json`，同 stem 中文汇总为 `.md`，不发布。

| 命令 | 结果 | raw / 中文汇总 stem |
|---|---|---|
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_golden_contracts.OpenApiDraftTests.test_create_export_accepts_html_and_csv_without_presentation -v` | red：1 error，KeyError requestBody；实现后 green：1 passed | contract-red；contract-tracer-green |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_golden_contracts.OpenApiDraftTests -v` | 10 passed，0.057s | contract-focused |
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py' -v` | 261 tests；260 passed、1 skipped（Windows junction）；18.570s | runtime-final |
| `python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_runtime_r1_acceptance -v` | 63 passed，0.597s；与 runtime 重叠，不重复计数 | contract-wrappers-final |
| `ruff check sbtd-runtime/tests/test_golden_contracts.py` | exit 1：既有 19–30 行 imports I001；与历史 task 记录一致，未修改该段，不修无关 lint | contract-lint |
| `ruff format --check sbtd-runtime/tests/test_golden_contracts.py` | exit 0；1 file already formatted | contract-format |
| `PYTHONPATH=sbtd-runtime:. python3 -B -c <smoke source>` | exit 0：8 个 component schema 合法、95 个本地 ref 可解析；真实 SnapshotStore ID 序列化后 html/csv 接受，pdf／缺 ID／畸形 JSON 拒绝 | schema-request-smoke |

最后一行的 **完整可复现命令（包括 `-c` 源码）** 保存在 `reports/schema-request-smoke.json` 的 `command` 数组及同 stem `.md` 的运行命令区；该 throwaway 脚本仅在进程内运行，未留下生产／测试脚手架。Schema smoke 没有调用导出 HTTP，400/404/410 仅验证声明，不声称错误处理已实现。

### 验证边界

- BDD: traceable；四个新场景对应五项 test_create_export_*；Cross-repo context: contract-only；API Contract: verified（本地 schema／引用／请求层）；Mock Strategy: none。
- rtk: skipped-for-report，保留原生命令输出；Final Test Report / Run Summary MD: generated；Targeted Rerun: passed；Final Full Rerun: passed（上述 runtime／wrapper 计划范围，保留 skip）。
- OpenAPI 完整 meta-schema lint：未安装独立 validator，仓库未配置 spec lint，不安装新依赖；执行已有 PyYAML/jsonschema 组件／引用／实例验证，不冒充完整 OAS lint。
- typecheck、Dashboard build／UI E2E 未运行：没有 TS／UI／静态产物修改。全仓无关 workflow／probe_links suite 未运行，不处理历史 flakes。
- Graft: skipped，以源码／契约引用为影响证据；未修改已有导出符号，无 LSP refactor；未使用网络／cloud 索引。
- 未实现或验证 export HTTP、生成、保留／清理；没有部署／发布。撤回本提交只能撤回契约，后续 R2.1a 必须显式依赖此契约并独立验证。

### 独立 review 与可读性

- ContractMaintainability（只读 reviewer）：场景／测试映射、根 wrapper pickup、文档边界与 consumer sync 均无问题；结论 Lean already and readable/traceable。
- 唯一 optional shrink：完整 presentation 在 html/csv 各验证一次可少约 5 行。保留 CSV 用例，明确防止将来误把 presentation_state 限为 HTML；不引入重复 helper／新依赖。
- 主会话只读 `TaskDocument.parse` 成功：strict／checking、2 个真实事件；未运行 TaskStore catalog，未写 active，不撤回前述恢复限制。
- ContractCorrectness（只读 reviewer）：overall_correctness correct，无 actionable findings；核对 3.1 Schema 引用、required body、七字段模型、负例、错误复用及 scope。静态审查未冒充 OAS linter／HTTP 测试；无修正回路待关闭。摘要保存 `reports/independent-reviews.md`。

### 提交与交付边界

提交仅显式添加上述五个文件，使用 conventional message `feat(contract): add createExport requestBody`。自身 commit SHA 不自引用；实际提交结果由最终会话输出及提交后本地 `reports/commit-receipt.json` 记录。提交前保存已验证四个契约／测试／场景／说明文件的 SHA-256，提交后与 Git blob 比较，防止把不同内容冒充已验证版本；task.md 单独解析模式与状态事件。既有两个 untracked 路径保留，不切分支、不 push、不开 PR。

## 模型列表（operator 可补全）

| 用途 | 请求模型 | 实际模型 | assistant messages | 工具调用次数 |
|---|---|---|---|---|
| 主会话 | 未另指定 | openai-codex/gpt-6-astra（host 标识） | unknown | unknown |
| ContractCorrectness（独立只读 reviewer） | host 默认 reviewer | unknown（host 未返回模型标识，operator 可补全） | unknown | unknown |
| ContractMaintainability（独立只读 reviewer） | host 默认 reviewer | unknown（host 未返回模型标识，operator 可补全） | unknown | unknown |

## PR round 2：202 接受响应

用户明确要求继续 strict；基线 `58dcc038bdf51ca47380d4e988d2301188122e69`，分支不变。本轮仅修改 createExport 的 202、对应测试及本 task；保留原轮验收证据。未完整调用 grill-with-docs：需求、授权和验收均明确。沿用上文 TaskStore 已知限制，仅更新用户要求的共享交付记录，不重试 catalog，不声称生命周期 helper 或自动恢复成功。

### 本轮 Book Gate Plan

| Gate | 触发事实 | 阶段 | 状态 |
|---|---|---|---|
| book-ddia-data-design | createExport 接受响应的 wire schema | before-dev | passed / confirmed：OpenAPI 为事实源；复用 ExportId/schema 与 Envelope；无持久化迁移；幂等、失败路径不变 |
| book-legacy-change-safety | 既有响应没有要求 export_id | before-dev | passed / characterized：新增响应实例回归修改前 6 个子用例失败；修改后通过；无需生产 seam |
| book-refactoring-pass | 只改声明式契约／测试，无生产代码重构 | before-dev | not-required |
| book-ddd-distilled-modeling | 本轮无完整 grill、无新增领域规则或边界歧义 | before-dev | not-required；沿用既有 Export／Snapshot 边界 |
| book-release-readiness | 没有 runtime／部署变更，export HTTP 仍未实现 | finish | not-required；不声明服务／发布就绪 |

DDIA：接受响应只交付供既有查询／下载路径使用的 ID，不表示文件已完成。不增加 status、URL 或时间字段；PRD §13.2–13.3 未要求这些接受响应字段。无 backfill/replay；撤回本契约前需协调已依赖消费者。验证覆盖 ID 必填／类型／封闭 data、Envelope 保留，以及其他 operation 不变。

本轮 BDD（contract-only，Mock Strategy: none）：用户限定两份说明仅在已有 202 描述时修改；经读取均无 202 描述，故保持不变，在本明确交付 task 中记录本轮验收场景。语言沿用中文正文、英文关键词；由 `test_create_export_202_requires_export_id_and_preserves_envelope` 追踪。

```gherkin
Scenario: 导出接受响应提供后续查询与下载所需标识
  Given 客户端提交固定快照的 HTML 或 CSV 导出请求
  When 按 createExport 的 202 契约校验接受响应
  Then data 必须是仅含字符串 export_id 的对象
  And 缺失 export_id、错误类型或未知 data 字段均被拒绝
  And api_version、request_id、meta 保持既有 Envelope 约束
```

## PRD §13.2–13.3 input → requestBody field mapping

以下所有引用均来自 `docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md`；表列出创建导出的输入及实际承载边界，不把预检／渲染／下载步骤冒充新增输入。

| PRD 简短原文及路径／章节 | requestBody 字段 | 承载情况／边界 |
|---|---|---|
| `docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md` §13.2：“HTML 网页、JPEG 长图、PDF 文档、CSV 数据”“选择一种格式” | `format` | HTML／CSV 已承载；**JPEG／PDF NOT carried**，本 PR 已批准范围仅 html/csv，后续 R2.1b，不在本轮扩枚举 |
| 同路径 §13.2：“固定当前已完成 snapshot_id”；§13.3：`ReportDocument(snapshot, presentation_state)` | `snapshot_id` | 已承载快照引用；snapshot 内容不复制进请求 |
| 同路径 §13.2：“页面展示状态”；§13.3：`presentation_state` | `presentation_state` | 可承载完整七字段状态；省略时沿用既有默认状态，不保证省略时还原用户非默认页面 |
| 同路径 §13.3：“主题” | `presentation_state.theme` | 已承载 dark/light |
| 同路径 §13.3：“标准报告宽度” | `presentation_state.report_width_px` | 已承载 CSS 像素宽度 |
| 同路径 §13.3：“展开的明细对象” | `presentation_state.expanded_detail_ids` | 已承载展开对象 ID 列表 |
| 同路径 §13.3：“表格排序” | `presentation_state.table_sort` | 已承载 table ID → 排序字符串 |
| 同路径 §13.3：“当前预览行集” | `presentation_state.preview_row_sets` | 沿用现有模型 table ID → 预览行数；**显式行 ID／任意行集 NOT carried**。固定快照＋排序＋行数供呈现使用，不是 CSV 范围 |
| 同路径 §13.3：“Panel 顺序” | `presentation_state.panel_order` | 已承载 Panel ID 顺序 |
| 同路径 §13.3：“图例状态”“隐藏某条系列属于显示状态” | `presentation_state.legend_state` | 已承载 series ID → 可见性；保留隐藏说明是渲染要求，不是额外输入 |

**requestBody 无 PRD 来源字段：无。** 所有字段均在表内；具体 wire 名称、类型及 optional/default 是上一轮已批准的既有模型映射，并非 PRD 原文规定。§13.2 的固定时间范围／筛选通过 snapshot_id 间接固定；预检数据完整性、renderer／容量、授权／脱敏、生成校验、取消与下载是行为或独立流程，不是本 requestBody 必须新增的字段。Bearer、CSRF、Idempotency-Key 是既有协议头，不冒充 §13.2–13.3 的请求体输入。本轮不修改上述既有输入边界，也不需要修改 createExport 之外的操作。

## 202 export_id

上一轮 createExport 的 202 仍引用通用 `Json` → `Envelope`，其中 `data: {}` 没有要求返回 export_id。本 PR 本轮新增 `ExportAccepted` response，以 `allOf` 组合原有 `Envelope` 与 `data: CreateExportAccepted`；新数据 schema 为封闭 object，required `[export_id]`，其类型引用 `#/components/parameters/ExportId/schema`。不添加其他接受响应字段，不改变 Envelope 的 api_version/request_id/meta，也不改变 getExport、deleteExport、downloadExport 或其他 operation。

### 本轮验证结果

原生输出、退出码、命令、时间、基线 SHA、Linux 环境均保存于本 task 的 ignored `reports/r2-*.json`，同 stem 中文 `.md` 汇总；失败报告保留。rtk: skipped-for-report。证据为 developer-local／dirty／local-only，不冒称 CI、HTTP 导出或已发布 PR head。

| 命令（仓库根） | 实际结果 | raw／中文汇总 stem |
|---|---|---|
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_golden_contracts.OpenApiDraftTests.test_create_export_202_requires_export_id_and_preserves_envelope -v` | 修改前 1 test、6 个失败子用例；修改后 1 passed | `r2-response-red`、`r2-response-green` |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_golden_contracts.OpenApiDraftTests -v` | 最终 11 passed，0.070s | `r2-openapi-final-format-fix` |
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py' -v` | 最终 262 tests：261 passed、1 skipped，18.688s；skip 为 Windows junction evidence only | `r2-runtime-final-format-fix` |
| `python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_runtime_r1_acceptance -v` | 最终 64 passed，0.608s；与 runtime 重叠，不累计计数 | `r2-contract-acceptance-final-format-fix` |
| `ruff check sbtd-runtime/tests/test_golden_contracts.py` | exit 1：既有 19–30 行 import I001；该段未改，沿用上一轮，不修范围外 lint | `r2-ruff-check` |
| `ruff format --check sbtd-runtime/tests/test_golden_contracts.py` | 首轮 exit 1：新测试两处换行；已修正，最终 exit 0：1 file already formatted | `r2-ruff-format`、`r2-ruff-format-fixed` |
| `python3 -B -c <response smoke source>` | exit 0：9 个 component schema、98 个本地引用；JSON 响应 round-trip、缺 ID 拒绝、ID 可用于既有查询／下载路径；结构比较证明除 createExport 202 和两个新增 component 外整个 OpenAPI 不变 | `r2-response-smoke` |

Smoke 完整 `-c` 源码在 `r2-response-smoke.json` 的 command 数组及同 stem `.md`，无落盘脚手架。初次 suite 成功证据另保留 `r2-openapi-targeted`、`r2-runtime-final`、`r2-contract-acceptance-final`；格式修正后最终套件已完整重跑。

BDD: traceable（本轮 task 场景 → 新响应回归）；Cross-repo context: contract-only；API Contract: verified（schema／引用／实例层）；Mock Strategy: none。Final Test Report / Run Summary MD: generated；Targeted Rerun: passed；Final Full Rerun: passed（计划测试范围，保留 Windows skip）；**lint 并非全绿**。完整 OAS meta-schema validator 未安装，沿用既有 jsonschema，不添加依赖。没有 TS／UI／runtime 变更，因此不运行 typecheck、Dashboard build、浏览器 E2E 或 export HTTP；不执行全仓无关 workflow suite。Graft: skipped，以精确契约结构比较和源码为证据；没有修改既有导出符号，无需 LSP rename/refactor。

Code Readability Review：测试沿用既有 unittest/jsonschema 验证方式；一个响应样本、显式负例、独立子用例定位；不引入 helper 抽象、依赖或 HTTP mock。Ponytail 实现选择：复用 Envelope 和 ExportId schema，不复制公共字段、不添加未要求的接受响应字段。

独立只读 review 已完成（均未运行测试，主会话唯一验证 controller）：
- ResponseCorrectness：overall_correctness correct；确认 allOf、Envelope 保留、ID 类型和其他操作不变、负例有效。唯一 P3 非阻塞建议为测试固定 `ExportAccepted` 组件名称；**不采纳**：用户允许示例命名，等价重命名不是消费者可见缺陷；测试应验证响应行为而非内部引用名称。
- MappingReadability：输入映射完整准确，无 PRD 来源遗漏；确认 JPEG/PDF、显式预览行集及默认状态边界已标明；PRD 无额外接受响应字段要求。Simplicity / Code Readability：Lean already，net 0 lines to cut，无阻塞问题。
- 两位 reviewer 均覆盖最终换行后的测试版本；无待修复 correctness finding。主会话检查最终报告同 stem 配对、九节顺序、无模板占位、退出码一致；完成只指本轮契约交付，不表示 runtime／部署／发布就绪。

提交范围仅 `sbtd-runtime/contracts/openapi.yaml`、`sbtd-runtime/tests/test_golden_contracts.py` 和本 task；其他 operation 及两份未描述 202 的说明保持不变。提交前记录已验证契约／测试 SHA-256，提交后以 Git blob 比对确认同一内容；SHA 由最终输出及 ignored commit receipt 提供，不在提交中自引用。无 push／PR／部署。TaskStore 自动恢复限制不变。

## Round 3: pattern / non-negative

用户于 2026-10-20 17:12 CST 批准本轮，明确继续 strict；起点 `b972328b0100f119a1f9764391823cb3a65c3aea`，原分支不变。只修改指定 schema、对应测试、受影响的两份说明及本记录；模型列表原样保留。未完整调用 grill-with-docs：范围明确，决策可由源码确定。沿用已记录 TaskStore catalog 限制，不重试、不写 active／身份／ignore，不声称 helper 生命周期或自动恢复成功。

### 源码证据与决定

- SnapshotId：`sbtd-runtime/report_snapshot.py:49` 为 `re.compile(r"snap_[0-9a-f]{32}")`；`:682–683` 使用 `_SNAPSHOT_ID.fullmatch(snapshot_id)`，不匹配抛出 `SnapshotNotFound`；`:663` 装载文件时也使用 fullmatch。JSON Schema 的 pattern 默认子串匹配，因此采用 `^snap_[0-9a-f]{32}$`，不改变内部正则。
- ExportId：搜索 `sbtd-runtime` 的 Python 源码及 Dashboard 源码，没有 export_id validator／正则；`sbtd-runtime/serve.py:475–489` 的 API 路由未注册 exports；`sbtd-runtime/csv_export.py:152–155` 只序列化 snapshot_id。**不添加 ExportId pattern**，保留 string，不编造 export 前缀。
- 数值：`sbtd-runtime/dashboard/src/reportDocument.ts:45` 的 `report_width_px: number`；`:48` 的 `preview_row_sets: Record<string, number>`；`:73–85` 构造器直接保存呈现状态，只验证 panel_id，无整数转换／校验。源码搜索未找到其他 runtime／dashboard 数值校验。保留两处 `type: number`，按本轮授权增加 `minimum: 0`；允许零和非负小数，不声称 Dashboard 已拒绝负值。
- 两份指定说明都使用 `snap_report` 作为合法 ID 示例（场景 `:146`、使用说明 `:113`），需替换为符合格式的 ID；仅同步受影响的标识／数值说明，不修改其他行为。

### 本轮 Book Gate Plan

| Gate | 触发事实 | 阶段 | 状态 |
|---|---|---|---|
| book-ddia-data-design | ID 与数值 wire schema | before-dev | passed / confirmed |
| book-legacy-change-safety | 既有契约缺格式／非负边界回归 | before-dev | passed / characterized：ID 8 个、负数 4 个子用例先失败；各 schema 修改后定点通过；无需新 seam |
| book-refactoring-pass | 只有声明式契约、测试和说明，无生产代码重构 | before-dev | not-required；无需新 seam |
| book-ddd-distilled-modeling | 无完整 grill、领域术语／边界歧义 | before-dev | not-required |
| book-release-readiness | 无 runtime／部署变更，export HTTP 尚未实现 | finish | not-required；不声称发布就绪 |

DDIA Data Design Review — confirmed。ID 格式以 runtime 为事实源；数值类型以既有 PresentationState 为依据，非负限制来自本轮明确授权。共享参数 schema 继续供路径及请求／响应引用；无存储、迁移、backfill、异步顺序或幂等变更。回滚仅撤回契约，须协调已依赖消费者。必需验证为 malformed ID、负数、零／小数保留及完整既有套件。

BDD 沿用指定场景文件，中文步骤＋英文关键词；contract-only，Mock Strategy: none。新增断言仍使用用户指定的 OpenApiDraftTests / jsonschema seam，不引入 HTTP mock。

### 本轮验证

已完成 red → green：`reports/r3-id-red` 保留 8 个 malformed ID 失败，`r3-id-green` 定点通过；`r3-numbers-red` 保留 4 个负数失败，`r3-numbers-green` 的 2 tests 通过（包括零／小数保留）。`r3-runtime-schema-smoke` 实际创建／读取 SnapshotStore，JSON round-trip 的 html/csv 请求通过，零／小数接受，负数与 malformed ID 拒绝，9 个 component schema 合法；未调用 export HTTP。完整命令／stdout／stderr／退出码保存在同 stem `.json`，中文汇总 `.md`，均 ignored／local-only。

Code Readability / Ponytail：复用既有用例与 validator；不增加 helper、依赖或生产实现。合法 ID 样本全部迁移，负例使用明确子用例名；没有新增整数限制。模型列表逐字比较未改变。主会话为唯一 writer／验证 controller；两项独立只读审查覆盖 schema/source correctness 与测试／说明一致性。

| 命令（仓库根） | 实际结果 | raw／同 stem 中文汇总 |
|---|---|---|
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_golden_contracts.OpenApiDraftTests -v` | 11 passed，0.066s | `reports/r3-openapi-final.{json,md}` |
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py' -v` | 262 tests：261 passed、1 skipped，17.917s；Windows junction evidence only | `reports/r3-runtime-final.{json,md}` |
| `python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_runtime_r1_acceptance -v` | 64 passed，0.576s；与 runtime 重叠，不累计计数 | `reports/r3-contract-acceptance-final.{json,md}` |
| `ruff format --check sbtd-runtime/tests/test_golden_contracts.py` | exit 0，1 file already formatted | `reports/r3-ruff-format.{json,md}` |
| `ruff check sbtd-runtime/tests/test_golden_contracts.py` | exit 1，既有 19–30 行 imports I001；未改该段，不做无关 lint 修复 | `reports/r3-ruff-check.{json,md}` |
| `PYTHONPATH=sbtd-runtime:. python3 -B -c <smoke source>` | exit 0，真实 SnapshotStore＋JSON 请求、数值边界、malformed ID、9 个 component schema | `reports/r3-runtime-schema-smoke.{json,md}` |

Smoke 的完整可复现 `-c` 源码保存在报告 command 数组及中文汇总，不留下脚手架。结构比较基线证明 OpenAPI **仅**新增 SnapshotId.pattern 与两处 minimum，ExportId 与其他 operation/schema 完全不变；源码／说明 SHA-256 保存在 `reports/r3-validated-content.json`，提交后核对 Git blob，防止将未验证内容当作已验证提交。

BDD: traceable（原场景的 ID／非负边界 → 既有 test_create_export_* 扩充）；中文步骤＋英文关键词；Cross-repo context: contract-only；API Contract: verified（schema／实例层）；Mock Strategy: none。rtk: skipped-for-report；Final Test Report / Run Summary MD: generated；Targeted Rerun: passed；Final Full Rerun: passed（计划测试范围，保留平台 skip）；**lint 并非全绿**。Evidence Source: developer-local；Source Revision: dirty；Environment Alignment: not-needed；Evidence Publication: local-only。仅本地证据，不冒称 CI 或已发布 PR head。

未运行 TS typecheck、Dashboard build、UI E2E、export HTTP、全仓无关 workflow suite：没有 TS／UI／runtime 修改，导出 HTTP 尚未实现；独立完整 OAS validator 沿用未安装限制，不新增依赖。Graft: skipped，以源码及精确 schema 比较为证据；无导出符号修改，不需 LSP refactor。没有要求范围外实现，因此无 CONTRACT-CHANGE-NEEDED。提交仅上述四个契约／测试／说明文件与本 task，显式 git add；不包含两个禁止路径，不 push、不开 PR。恢复／回滚边界与既有 TaskStore 限制不变。

独立只读 BoundaryCoverage：overall_correctness correct，无阻塞问题；确认 schema 引用生效、ID／负数／零与小数覆盖、说明及场景一致、模型列表未改。Simplicity / Code Readability：Lean，net 0 lines required；不抽取仅减少字面量的全局常量。可选 P3：Python jsonschema 的 `$` 可在末尾换行之前匹配，故 `"snap_" + "a"*32 + "\n"` 在 schema 下接受、runtime fullmatch 拒绝；主会话已用实例确认。保留用户要求的 `^...$` 形式，不额外加入 maxLength 或非便携锚点；这是 contract 比 runtime 更宽的已知边界，不会变得更严格。

独立只读 PatternCorrectness：overall_correctness correct，无 material bug；确认正则来源、共享 SnapshotId 引用、ExportId 无验证、number/minimum 选择及五文件范围。该 reviewer 对锚点与 fullmatch 的一般性等价描述以以上已实测的末尾换行例外为准，不声称逐字符完全等价。两项独立复核均无阻塞问题；10 组原生／中文报告配对、九节顺序、退出码和基线身份已核验。本轮 done 仅指契约交付验收，保留既有 I001、Windows skip 和末尾换行边界，不表示 runtime／部署／发布完成。

## Round 4: snapshot_id error semantics / panel_order

用户明确继续 strict；基线 `dff132c8b98b2e8cd597ff9d1b09c0ea6e9d0e21`，原分支不变。仅修改指定五个文件，不改模型列表、不 push／开 PR。未完整调用 grill-with-docs：两项 reviewer 决策、范围与验收明确。继续沿用 TaskStore catalog 已知限制；本共享交付记录不冒充 helper 生命周期或自动恢复成功。不新增仓内报告文件，本轮原生输出与中文汇总记录于会话工具 artifact。

### 源码证据与决定

- `sbtd-runtime/report_snapshot.py:682–683`：不符合 runtime ID fullmatch 的值抛出 SnapshotNotFound。`sbtd-runtime/serve.py:449–456` 的 get_snapshot 与 `:460–470` 的 get_snapshot_dataset 映射为 404；dataset 还映射过期 410、CursorError 400。SnapshotId 参数 description 说明 pattern 记录 runtime 格式，PATH malformed ID 是 404，不改 pattern。
- createExport 请求体：snapshot_id 不满足 pattern → 400 BadRequest；格式正确但不存在／不可见 → 404；过期 → 410。两份说明和字段 description 明确区分，不把 PATH 的 404 套用到 body。
- `sbtd-runtime/contracts/panel-manifest.json:6–189` 定义 13 个 panel，`:8` 为 overview，不存在 summary。`sbtd-runtime/dashboard/src/reportDocument.ts:53–60` 默认使用完整 registry；`:79–85` 按输入逐项绑定，未知 ID 抛错，子集只生成子集，空列表生成空报告。
- panel_order 必须是 manifest 所有 ID 的完整、唯一排列（可调整顺序，不强制默认顺序）；否则契约要求 400 BadRequest。增加 uniqueItems 与 minItems: 1；不复制 manifest enum、不改 manifest／ReportDocument。schema 只机械检查非空、去重和 string，成员资格／完整性是未来 export handler 的契约义务，不声称已实现。
- **R2.2 范围外：** getReportSnapshot（runtime get_snapshot）与 dataset 未声明 runtime 返回的 404；dataset 也未声明 410／400。本轮不补这些 response，保留现有 operations 原样。

### 本轮 Book Gate Plan

| Gate | 触发事实 | 阶段 | 状态 |
|---|---|---|---|
| book-ddia-data-design | 请求 schema 与错误语义；manifest 单一事实源 | before-dev | passed / confirmed：无持久化、迁移、重试或幂等变更；撤回契约须协调消费者 |
| book-legacy-change-safety | 既有 panel_order 接受空列表／重复项 | before-dev | passed / characterized：r4-panel-red 两个子用例分别因缺少 minItems／uniqueItems 失败；malformed body 用例通过；无需生产 seam |
| book-refactoring-pass | 声明式契约／测试／说明，无生产代码修改 | before-dev | not-required |
| book-ddd-distilled-modeling | 无完整 grill、无领域术语或边界歧义 | before-dev | not-required |
| book-release-readiness | 不修改 runtime／部署，export HTTP 尚未实现 | finish | not-required；不声称发布就绪 |

BDD 沿用指定 Markdown 场景，中文正文＋英文关键词；Cross-repo context: contract-only；Mock Strategy: none。主会话唯一 writer／验证 controller；验证计划为 malformed body、空／重复 panel 负例、完整 manifest 正例、OpenApiDraftTests、runtime discover、contract＋acceptance、ruff format/check 与真实 schema/runtime smoke。

### 本轮验证与范围边界

主会话使用原生命令（rtk: skipped-for-report）；完整 command（含 smoke 的 `-c` 源码）、stdout、stderr、exit code、带时区时间、基线 SHA、worktree 与环境保存在仓外 `local://r4-*.json`，同 stem `.md` 为中文汇总。未在五文件之外创建仓内报告；会话 artifact 不是 Git 中的持久证据，不承诺跨会话恢复。七组报告保留 red 与 lint failure；九节顺序、stem、退出码与模型列表逐字一致已核验。

| 命令（仓库根） | 实际结果 | raw／中文汇总 |
|---|---|---|
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_golden_contracts.OpenApiDraftTests.test_create_export_rejects_incomplete_or_invalid_presentation test_golden_contracts.OpenApiDraftTests.test_create_export_rejects_malformed_snapshot_id -v` | 修改 schema 前 2 tests：panel 的空／重复项两个子用例失败；malformed snapshot body 通过 | `local://r4-panel-red.{json,md}` |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_golden_contracts.OpenApiDraftTests -v` | 12 passed，0.064s；包含 red 用例 green，HTML／CSV malformed body 共 16 个子用例 | `local://r4-openapi-final.{json,md}` |
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py' -v` | 263 tests：262 passed、1 skipped，17.000s；Windows junction evidence only | `local://r4-runtime-final.{json,md}` |
| `python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_runtime_r1_acceptance -v` | 65 passed，0.573s；与 runtime 重叠，不累计计数 | `local://r4-contract-acceptance-final.{json,md}` |
| `ruff format --check sbtd-runtime/tests/test_golden_contracts.py` | exit 0，1 file already formatted | `local://r4-ruff-format.{json,md}` |
| `ruff check sbtd-runtime/tests/test_golden_contracts.py` | exit 1，既有 19–30 行 I001 import 排序；导入段未改，不修无关 lint | `local://r4-ruff-check.{json,md}` |
| `PYTHONPATH=sbtd-runtime:. python3 -B -c <smoke source>` | exit 0；HTML／CSV JSON round-trip、完整 13-panel 正序／逆序接受，空／重复 panel 与 malformed body 拒绝；真实 SnapshotStore.get／dataset_page 的 malformed ID 抛 SnapshotNotFound；9 个组件 schema 合法；与基线比较全部 paths 结构相同 | `local://r4-schema-runtime-smoke.{json,md}` |

测试变更证据：`sbtd-runtime/tests/test_golden_contracts.py:575–579` 从 manifest 读取完整顺序；`:618`、`:701` 替换旧的 summary／空合法 fixture；`:671–691` 独立 malformed body 回归保留原负例并覆盖 html/csv；`:726–727` 增加空列表／重复 ID 负例。没有复制 panel enum、添加依赖／helper 或修改 manifest／ReportDocument。

契约变更证据：`sbtd-runtime/contracts/openapi.yaml:646–649` 说明 PATH 404；`:701–713` 明确 body 的 400／404／410；`:760–771` 增加非空、唯一和完整排列说明。场景 `sbtd-runtime/spec/r1.0-contract-scenarios.md:152–181` 与使用说明 `sbtd-runtime/docs/install-and-use.md:118–130` 同步上述边界。

BDD: traceable；沿用中文正文＋英文关键词，场景对应 test_create_export_*。Cross-repo context: contract-only；API Contract: verified（schema／实例，不是 export HTTP）；Mock Strategy: none。Final Test Report / Run Summary MD: generated；Targeted Rerun / Final Full Rerun: passed（计划测试范围，保留平台 skip）；**lint 并非全绿**。Evidence Source: developer-local；Source Revision: dirty；Environment Alignment: not-needed；Evidence Publication: local-only。

未运行 TS typecheck、Dashboard build／UI E2E、export HTTP、全仓无关 workflow suite：无 TS／UI／runtime 修改，导出 HTTP 尚未实现。独立完整 OAS validator 沿用未安装限制，不新增依赖；jsonschema 不冒充 OAS linter。Graft: skipped，以精确 schema 比较和源码为证据；无导出符号变化，不需 LSP refactor。保留 Round 3 已知 `$` 末尾换行边界，不扩 scope。不存在必须改五文件之外的项目变更，因此不触发 CONTRACT-CHANGE-NEEDED。回滚只撤回契约，必须协调下游消费者；不表示 runtime／部署／发布完成。

### 独立复核与提交边界

- SnapshotSemantics（独立只读）：overall_correctness correct，无 actionable finding；核实 body 引用仅指向 SnapshotId/schema，不继承 PATH description；既有 snapshot operations／createExport responses、Bearer、CSRF、幂等头保持；源码引用准确。
- PanelContractReview（独立只读）：overall_correctness correct，无 finding；完整 13-panel fixture、两个 schema 负例及 malformed body 的错误路径断言有效，场景／说明一致，未重复枚举。Ponytail / Code Readability：Lean already，net 0 lines；保留按 manifest order 排序，与 registry 语义一致。
- 两位 reviewer 均未运行测试；主会话为唯一验证 controller。四个已验证内容的 SHA-256 在会话记录保留，提交后核对对应 Git blob；本 task 只追加真实验收和复核结果，模型列表不变。显式 git add 仅五个授权文件；两个禁止路径不暂存。无 push／PR／发布，done 仅指本轮契约交付。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-20T16:04:10.056607+08:00 | planned | in-progress | 用户明确 strict 与 contract-only 授权；保存共享交付记录，非 TaskStore 成功声明 | 分支／基线检查；prompt；PRD §13.2–13.3；f02fe5f blocker |
| 2026-10-20T16:09:58.204636+08:00 | in-progress | checking | 请求契约／测试／场景／文档已实现；本地 schema smoke 与 runtime、CI wrapper 通过，等待独立复核 | reports/schema-request-smoke、runtime-final、contract-wrappers-final；既有 I001 保留，Windows junction skip |
| 2026-10-20T16:17:54.846339+08:00 | checking | done | 本地 contract-only 验收完成，两位独立复核无阻塞问题；保留既有 I001 与 Windows-only skip，不声称导出 runtime 或发布完成 | runtime 261/1 skip；wrapper 63 passed；schema 8/refs 95 smoke；contract-focused 10 passed；format passed；独立 review 记录 |
| 2026-10-20T08:40:00.194208+00:00 | done | planned | 用户授权 PR round 2：补 createExport 202 export_id；保留上一轮完成证据并重开 | 本轮 prompt；基线 58dcc038bdf51ca47380d4e988d2301188122e69；指定分支匹配 |
| 2026-10-20T08:40:00.194208+00:00 | planned | in-progress | strict 继续；已读取 PRD 输入、Envelope 与 ExportId，限定 createExport-only | 本轮 Book Gate Plan／输入映射／202 export_id；TaskStore 限制沿用 |
| 2026-10-20T08:43:31.180755+00:00 | in-progress | checking | 202 契约与回归完成；响应 smoke、runtime、contract＋acceptance、OpenAPI 测试通过；修正新测试换行格式，独立 review 进行中 | reports/r2-response-red、r2-response-green、r2-response-smoke、r2-runtime-final、r2-contract-acceptance-final、r2-openapi-targeted；保留 ruff 初次结果 |
| 2026-10-20T08:46:27.157295+00:00 | checking | done | 本轮 createExport 202 export_id、完整输入映射与本地验收完成；两位独立 review 无阻塞；保留既有 lint 与平台 skip | 最终 runtime 262/1 skip、contract＋acceptance 64、OpenAPI 11；format passed；response smoke 9 schemas/98 refs；其他 OpenAPI 内容不变；本轮 review 结论 |
| 2026-10-20T09:13:47.338151+00:00 | done | planned | 用户授权 Round 3 pattern / non-negative；保留上一轮完成证据，重开共享交付记录 | 本轮 prompt；b972328b0100f119a1f9764391823cb3a65c3aea；分支匹配 |
| 2026-10-20T09:13:47.338151+00:00 | planned | in-progress | strict 继续；ID 与数值证据已核对；模型列表不改 | Round 3 源码证据与 Book Gate Plan；沿用 TaskStore 限制 |
| 2026-10-20T09:17:12.261988+00:00 | in-progress | checking | 两项契约收紧及负例完成；各 red→green 与真实 SnapshotStore/schema smoke 通过；开始完整验证及独立复核 | reports/r3-id-red、r3-id-green、r3-numbers-red、r3-numbers-green、r3-runtime-schema-smoke |
| 2026-10-20T09:28:23.289553+00:00 | checking | done | Round 3 契约与实例回归验收完成；两项独立复核无阻塞；保留既有 lint、平台 skip 与可选锚点边界，模型列表不变 | OpenAPI 11 passed；runtime 262/1 skip；contract＋acceptance 64 passed；format passed；SnapshotStore/schema smoke passed；reports/r3-*；独立 review 结论 |
| 2026-10-20T09:36:16.177940+00:00 | done | planned | 用户授权 Round 4；保留 Round 3 完成证据并重开 | 本轮 prompt；基线 dff132c8b98b2e8cd597ff9d1b09c0ea6e9d0e21；分支匹配 |
| 2026-10-20T09:36:16.177940+00:00 | planned | in-progress | strict 继续；核对 runtime ID 错误及 manifest／ReportDocument，限制五文件 | Round 4 源码证据与 Book Gate Plan；沿用 TaskStore 限制 |
| 2026-10-20T09:39:23.375735+00:00 | in-progress | checking | Round 4 schema／测试／场景／说明完成；原生套件与 schema/runtime smoke 通过；独立复核进行中 | OpenAPI 12；runtime 263/1 skip；contract＋acceptance 65；format passed；既有 I001；全部 paths 结构不变 |
| 2026-10-20T09:42:56.591170+00:00 | checking | done | Round 4 两项契约修正及全部指定验收完成；两位独立 reviewer 无 finding；保留既有 I001／Windows skip／pattern 末尾换行边界 | OpenAPI 12 passed；runtime 263/1 skip；contract＋acceptance 65 passed；format passed；schema/runtime smoke passed；local://r4-*；模型列表不变；仅五文件 |
