---
schema_version: 1
id: v2.1.0-rc.2-contract-create-export-request-body
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict；2026-10-20 16:01 CST 已批准独立 createExport 请求契约变更。仅当前 contract 分支提交，显式 git add；不 push、不开 PR，不触 R2.1a 分支及两个禁止提交路径。
status: done
branch: contract/v2.1.0-rc.2-create-export-request-body
created_at: '2026-10-20T16:04:10.056607+08:00'
updated_at: '2026-10-20T16:17:54.846339+08:00'
completed_at: '2026-10-20T16:17:54.846339+08:00'
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

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-20T16:04:10.056607+08:00 | planned | in-progress | 用户明确 strict 与 contract-only 授权；保存共享交付记录，非 TaskStore 成功声明 | 分支／基线检查；prompt；PRD §13.2–13.3；f02fe5f blocker |
| 2026-10-20T16:09:58.204636+08:00 | in-progress | checking | 请求契约／测试／场景／文档已实现；本地 schema smoke 与 runtime、CI wrapper 通过，等待独立复核 | reports/schema-request-smoke、runtime-final、contract-wrappers-final；既有 I001 保留，Windows junction skip |
| 2026-10-20T16:17:54.846339+08:00 | checking | done | 本地 contract-only 验收完成，两位独立复核无阻塞问题；保留既有 I001 与 Windows-only skip，不声称导出 runtime 或发布完成 | runtime 261/1 skip；wrapper 63 passed；schema 8/refs 95 smoke；contract-focused 10 passed；format passed；独立 review 记录 |
