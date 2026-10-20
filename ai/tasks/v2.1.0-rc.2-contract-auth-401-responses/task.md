---
schema_version: 1
id: v2.1.0-rc.2-contract-auth-401-responses
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict、contract-only；固定指定分支，仅显式 git add；不 push、不开 PR、不 merge；禁止暂存两个用户路径。
status: done
branch: contract/v2.1.0-rc.2-auth-401-responses
created_at: '2026-10-20T12:56:59.675195+00:00'
updated_at: '2026-10-20T22:00:00+08:00'
completed_at: '2026-10-20T13:10:05.388702+00:00'
---

# SecurityMiddleware Bearer 401 响应契约

## 范围与验收

基线 `ef8975212a4f80686d19a03f3c169bbf533eb117`，指定分支已核对，不切分支。仅修改 `sbtd-runtime/contracts/openapi.yaml`、`sbtd-runtime/tests/test_golden_contracts.py` 和本文件。runtime、Dashboard、panel-manifest、ADR、PRD、CSV schema、plan.md 均不修改。`.omp-r12b-addendum.txt` 与 `ai/tasks/codex-verify/` 保持原状，不暂存或提交。

修改前共 28 个 `/api/v1/*` operation：26 个经过 Bearer middleware，均缺少 401；两个豁免，其中 pair 已有 401。给前 26 个复用 `#/components/responses/Unauthorized`；health 不增加 401；pair 现有声明不重复、不改写、不移动。新增 OpenApiDraftTests 断言覆盖所有非豁免操作、health 与 pair；同步既有 snapshot response map 回归。运行用户指定三组 unittest、format、lint 及真实 HTTP smoke。只做本地提交。

未完整调用 grill-with-docs：需求和验收明确，源码可回答边界。主会话为唯一 writer 和验证 controller，独立 reviewer 只读。

## 源码证据

已重读当前文件：`sbtd-runtime/serve.py:361` 定义 health/pair 豁免集合；`:388–396` 对非豁免 `/api/*` 执行 Bearer 认证，`:393–395` 在 authenticate 返回 None 时返回 401；`:413–416` 为 pair 自身配对码失败 401。Host/Origin 检查与 403 在 `:382–385`，拒绝返回结束于 `:386`，先于认证；不改变顺序。health handler 为 `:410–411`。

`sbtd-runtime/contracts/openapi.yaml:69–70` 的 pair 401 声明未动。现有 Unauthorized 组件定义保持原样，当前位于 `:739–740`（修改前 `:687–688`）。全部 26 个新增引用均指向该组件；没有新增 schema 或其他状态。

### Operation evidence table（PR-body-ready）

下列 26 项均新增 `401 → #/components/responses/Unauthorized`。共享依据为 `sbtd-runtime/serve.py:388–396`，其中 `:393–395` 是实际认证失败返回；它位于路由分发之前，因此也覆盖契约中尚无业务 handler 的路径，不声称这些 handler 已实现。

| Method / URI | operationId | 本次动作 | 当前 runtime 证据 |
|---|---|---|---|
| GET `/api/v1/capabilities` | getCapabilities | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| GET `/api/v1/openapi.json` | getOpenApi | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| GET `/api/v1/projects` | listProjects | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| GET `/api/v1/actors` | listActors | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| GET `/api/v1/components` | listComponents | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| GET `/api/v1/tasks` | listTasks | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| GET `/api/v1/tasks/{task_uid}` | getTask | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| GET `/api/v1/tasks/{task_uid}/history` | getTaskHistory | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| GET `/api/v1/runs` | listRuns | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| GET `/api/v1/runs/{run_id}/steps` | listRunSteps | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| GET `/api/v1/gates` | listGates | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| GET `/api/v1/validations` | listValidations | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| GET `/api/v1/events` | listEvents | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| GET `/api/v1/collection-health` | getCollectionHealth | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| GET `/api/v1/metrics/catalog` | getMetricCatalog | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| POST `/api/v1/statistics/query` | queryStatistics | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| POST `/api/v1/statistics/timeseries` | queryTimeseries | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| POST `/api/v1/collection/refresh` | refreshCollection | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| POST `/api/v1/ingest/events` | ingestEvents | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| POST `/api/v1/report-snapshots` | createReportSnapshot | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| GET `/api/v1/report-snapshots/{snapshot_id}` | getReportSnapshot | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| GET `/api/v1/report-snapshots/{snapshot_id}/dataset` | getSnapshotDataset | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| POST `/api/v1/exports` | createExport | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| GET `/api/v1/exports/{export_id}` | getExport | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| DELETE `/api/v1/exports/{export_id}` | deleteExport | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| GET `/api/v1/exports/{export_id}/file` | downloadExport | 新增 401 | `sbtd-runtime/serve.py:388–396` |
| GET `/api/v1/health` | getHealth | 豁免，不新增 401 | `sbtd-runtime/serve.py:361,388,410–411` |
| POST `/api/v1/session/pair` | pairSession | 豁免，已有 Unauthorized 401 完全保留 | `sbtd-runtime/serve.py:361,388,413–416` |

## Book Gate Plan

| Gate | 触发事实 | 阶段 | 状态 |
|---|---|---|---|
| book-ddia-data-design | HTTP 认证失败 wire contract | before-dev | passed / confirmed |
| book-ddd-distilled-modeling | 无完整 grill、无领域术语或边界歧义 | before-dev | not-required |
| book-legacy-change-safety | 不修改 runtime 行为，现有 middleware seam 明确 | before-dev | not-required |
| book-refactoring-pass | 仅声明式契约、测试和任务文件，无生产代码编辑 | before-dev | not-required |
| book-release-readiness | 不修改 runtime、部署或集成行为 | finish | not-required；不声称发布就绪 |

DDIA Data Design Review — confirmed。SecurityMiddleware 是 Bearer 失败事实源，OpenAPI 记录既有 HTTP 行为。无数据写入路径、一致性、幂等、顺序、重试、去重、migration、backfill 或 replay 变更；Host/Origin 拒绝仍先于 Bearer。回滚仅撤回声明和测试，需协调已依赖契约的消费者。验证所有非豁免操作的组件引用、两个豁免及真实 HTTP。Ponytail：复用现有组件和 unittest，不新增 schema、依赖或 helper。

## 状态持久化限制

已核对 task 父路径为普通目录、无 symlink，目标不存在。`git check-ignore .sbtd/active-task.json ai/tasks/v2.1.0-rc.2-contract-auth-401-responses/reports/probe.json` 两项均匹配保护；`git ls-files -- .sbtd ai/tasks/v2.1.0-rc.2-contract-auth-401-responses` 无输出。沿用 snapshot-errors / #148 记录的 TaskStore catalog `task has no YAML frontmatter block` 限制，不重跑确认、不改其他任务绕过；TaskStore.create 还会写 index/active，超出用户三文件授权。本文件为明确要求的共享交付记录，不声称 helper 生命周期、active 或自动恢复成功，不写身份／ignore。报告存于仓库外 local:// 工具产物。

## 验证命令与结果

原生命令在仓库根执行；stdout、stderr、退出码、完整命令、时区时间、完整基线 SHA、分支与 Linux 环境保存在仓库外 `local://auth-401-<stem>.json`；每项有同 stem 九节中文汇总 `.md`。rtk: skipped-for-report，避免缓存／压缩替代原生证据。证据为 developer-local / dirty / local-only，不冒充 CI、PR head 或发布证明。`PYTHONDONTWRITEBYTECODE=1`、`RUFF_NO_CACHE=true` 防止验证生成仓库缓存。

| 精确命令 | 实际结果 | raw／同 stem 中文汇总 |
|---|---|---|
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_golden_contracts.OpenApiDraftTests -v` | 15 passed，0.072s，exit 0 | `local://auth-401-openapi.{json,md}` |
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py' -v` | 266 tests：265 passed、1 skipped，18.413s，exit 0；Windows junction evidence only | `local://auth-401-runtime.{json,md}` |
| `python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_runtime_r1_acceptance -v` | 68 passed，0.764s，exit 0；与 runtime 重叠，不累计 | `local://auth-401-wrappers.{json,md}` |
| `ruff format --check sbtd-runtime/tests/test_golden_contracts.py` | 1 file already formatted，exit 0 | `local://auth-401-format.{json,md}` |
| `ruff check sbtd-runtime/tests/test_golden_contracts.py` | exit 1；仅用户已知 I001，19–30 行 import block 未修改 | `local://auth-401-lint.{json,md}` |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -c <smoke source>` | 55 real HTTP checks passed，0.545s（进程总时长），exit 0 | `local://auth-401-http-smoke.{json,md}` |

完整可复现 smoke `-c` 源码保存在 raw 的 command 字段与中文汇总「运行命令」。复用既有 ServeProcess 启动真实 serve 子进程、真实 loopback socket、临时 home，无 mock；finally 停止服务且验证 exit 0，临时目录自动清理，无新增仓库脚手架。

### HTTP 覆盖矩阵

上方 operation 表的全部 26 个新增项均各执行两次：无 Authorization、无效 Bearer；均得到 HTTP 401 和 `{"detail":"unauthorized"}`，共 52 checks。路径占位符统一替换为 `smoke-id`，包括 DELETE export；原生报告及其中文汇总逐 URI 列出，不将 middleware 拒绝视为对应 handler 已实现。

| Method / URI | 场景 | 实际结果 |
|---|---|---|
| GET `/api/v1/health` | 无 Bearer | 200，`{"status":"ok"}` |
| POST `/api/v1/session/pair` | 正确配对码，无 Bearer | 200，token_type=bearer；凭据不写报告 |
| POST `/api/v1/session/pair` | 错误配对码 | 401，`{"detail":"unauthorized"}` |

### 验证边界与跳过

- BDD: skipped；无 runtime 用户行为变更，不新增 .feature，契约回归由 OpenApiDraftTests 覆盖。Cross-repo context: contract-only；API Contract: verified（静态断言与真实 middleware HTTP smoke）；Mock Strategy: none。
- E2E Mode: backend-only；Final Test Report / Run Summary MD: generated；Final Full Rerun: passed（用户指定 unittest 范围，保留平台 skip）；Targeted Rerun: not-needed。**lint 不全绿**，既有 I001 原始失败保留，不修无关 import。
- Graft: skipped，直接源码／契约证据足够；无导出符号编辑，不需要 LSP 重构。未使用 cloud 索引。
- UI、TS typecheck、Dashboard build、浏览器／移动端 E2E、全仓无关 workflow suite 未运行：无对应变更。完整 OAS meta-schema validator 未运行：沿用项目 YAML/contract 测试，不安装依赖。
- 无长期 lesson：没有新的 runtime 根因、回滚或持久工作流事故，不修改身份／lesson。报告在当前宿主工具产物中，不保证跨宿主恢复；TaskStore 限制保持可见。

### 独立审查与可读性

- AuthCorrectness：correct，无 actionable finding。独立核对 26 个新增引用、DELETE export、health 无 401、pair 相对基线 byte-for-byte 不变、serve.py 证据及 snapshot 集合加强。只读，未执行测试。
- AuthMaintainability：Lean already，无必须削减项。可选删掉 HTTP method/path guard 约 4 行，但会削弱 middleware 边界表达，主会话保留。确认 snapshot 断言是加强而非削弱、无新 import/helper/dependency。
- 主会话 Ponytail／Code Readability Review：复用现有组件和 unittest；subTest 与精确字典断言覆盖所有非豁免 operation。无 unrelated cleanup。

## 提交与恢复边界

RESULT：本次 contract-only 验收完成。本地实现提交曾为 `c9c9360a0875f24cd56db42831beb678c0af9777`（parent `ef8975212a4f80686d19a03f3c169bbf533eb117`，message `feat(contract): declare middleware Bearer 401 on authenticated /api/v1 operations`），经 PR #150 squash-merge 后，**权威实现 SHA 为 `10bc530caa263c0484046128218a8fc2936f523e`**。pre-merge 本地／PR SHA `c9c9360a0875f24cd56db42831beb678c0af9777`（实现）、`bb2ba1b4a660b24ce7c70be14bf5d420b2b368df`（证据 docs）、`a5aa704952064a48e4344f23b9a25ac4782576f0`（advisor 复核 docs，PR tip）在 squash 后作废，不以 ancestry 声称。通过 `git add sbtd-runtime/contracts/openapi.yaml sbtd-runtime/tests/test_golden_contracts.py` 显式暂存，仅这两个文件进入实现提交；82 insertions、1 deletion，无 runtime 修改。

**Squash 权威说明**：合并后以 squash commit `10bc530caa263c0484046128218a8fc2936f523e` 为权威；`git diff a5aa704952064a48e4344f23b9a25ac4782576f0 10bc530caa263c0484046128218a8fc2936f523e` 全树为空，squash 内容与 PR tip 一致。无 force-push。

提交后读取两个 Git blob 计算 SHA-256，确认与验证快照 `local://auth-401-validated-content.json` 完全一致，因此不重复执行未改变内容的测试、不重跑已知 I001 来确认。

| 已验证并提交的文件 | SHA-256 |
|---|---|
| `sbtd-runtime/contracts/openapi.yaml` | `c5d239fcc0004746a7a64ecbc23b5d207a054f5243dfc8b038b6fad3250a554e` |
| `sbtd-runtime/tests/test_golden_contracts.py` | `8381d0cb49c4758d42bd7e8f58ce754966ba562763fe69010614dff39d108428` |

本完成记录以独立 docs 提交保存，从而能在 task 内记录真实实现 SHA，而不编造自身提交的自引用 SHA。暂存命令仅 `git add ai/tasks/v2.1.0-rc.2-contract-auth-401-responses/task.md`；该记录提交的 SHA 由最终 stdout 与 `local://auth-401-commit-receipt.json` 给出。最终修改文件总计三个；两个禁止路径不暂存。未 push、未开 PR、未 merge、未部署／发布。完成只指本地契约交付；回滚需撤回本次实现提交并协调依赖消费者，不改变存量 runtime 数据。TaskStore／自动恢复限制不变。

## 模型使用

来源：operator 核验的会话 jsonl `~/.omp/agent/sessions/--workspace-640-skills--/2026-10-20T12-55-55-958Z_01a15961-fb36-7762-a02b-9e81f396ea1c.jsonl` 及其子目录 `AuthCorrectness.jsonl`、`AuthMaintainability.jsonl`。计数口径：每个 jsonl 中 `type=message` 且 `message.role=assistant` 的记录，按 `message.provider/message.model` 分组，含 `stopReason` 为 error／aborted 的记录；工具调用次数为这些消息中 `type=toolCall` content block 数（与 `tool_execution_start` 自定义记录数交叉一致）。请求 tier 取自各 jsonl 的 `thinking_level_change`。主会话 astra 在一次 error 后于 2026-10-20 21:08:35（北京时间）`model_change` 至 `xai-oauth/grok-4.7`（`role: fallback`）。

会话标题生成：jsonl 仅记录 `title`／`title_change`（`source: auto`，主会话 1 次，标题 “Execute attached prompt task”），未记录生成模型或调用消息，故模型与计数为 unknown（`config.yml` 中 smol/tiny 角色为 `cursor/composer-2.5`，但会话记录未证实其被用于标题生成）。

| 用途 | 请求模型 | 实际模型 | assistant messages | 工具调用次数 |
|---|---|---|---|---|
| 主会话（回退前） | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra | 18（17 toolUse + 1 error） | 42 |
| 主会话（回退后） | fallback 角色 | xai-oauth/grok-4.7 | 12（11 toolUse + 1 stop） | 11 |
| 独立 AuthCorrectness review | kimi-code/k3:max | kimi-code/k3 | 16（14 toolUse + 1 stop + 1 error） | 27 |
| 独立 AuthMaintainability review | kimi-code/k3:high | kimi-code/k3 | 14（12 toolUse + 1 stop + 1 error） | 17 |
| 会话标题生成 | unknown | unknown | unknown（1 次 auto title 事件） | unknown |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-20T12:56:59.675195+00:00 | planned | in-progress | 用户明确 strict；根、分支、路径、runtime 与全部 operation 已核对 | 基线 ef8975212a4f80686d19a03f3c169bbf533eb117；28 operations，26 缺少 middleware 401；serve.py:361,388–396,413–416 |
| 2026-10-20T13:01:05.329412+00:00 | in-progress | checking | 契约／回归完成，指定验证与真实 HTTP smoke 已执行，进入独立审查与交付检查 | OpenAPI 15 passed；runtime 266/1 skip；wrappers 68 passed；format passed；已知 I001；55 HTTP checks |
| 2026-10-20T13:10:05.388702+00:00 | checking | done | 指定验证、真实 HTTP smoke、独立审查完成；实现提交的 blob 与验证快照一致 | 本地实现曾为 c9c9360a0875f24cd56db42831beb678c0af9777；PR #150 squash-merge 权威 SHA 10bc530caa263c0484046128218a8fc2936f523e（pre-merge SHA 作废）；contract-only，无 runtime 修改；保留已知 I001 与 Windows skip |

## Advisor 复核（astra→grok 回退后的 --advisor 重跑）

本段是证据追加，不是重开。`status` 保持 `done`，`completed_at` 保持 `2026-10-20T13:10:05.388702+00:00`。不新增状态事件：没有 planned/in-progress/checking/blocked 迁移，done→done 不是本记录允许的新 ingress。

原因：前序会话 `01a15961-fb36…` 从 astra 回退到 grok-4.7，房间规则要求用 `--advisor` 再复核一次并说明。本轮就是该重启。本轮 session id：unknown（环境未暴露，不能从 jsonl 读取）。operator 请求模型为 `openai-codex/gpt-6-astra:high` 且启用 advisor。本会话唯一可见的 runtime workstation 模型字段是 `xai-oauth/grok-4.7`；不能据此证明 reasoning level，也不能证明 host 实际调度就是该字段。advisor 进程模型：unknown。截至本段写入，本会话没有收到注入的 advisor advisory，因此 observed blocker count = 0。这不是“隐藏 advisor 已书面通过”的声明。

未完整调用 grill-with-docs：operator 验收清单已明确，源码和相对基线 `ef8975212a4f80686d19a03f3c169bbf533eb117` 的 diff 能回答边界，没有新的领域歧义。

### 本轮 Book Gate Plan

| Gate | 触发事实 | 阶段 | 状态 |
|---|---|---|---|
| book-ddd-distilled-modeling | 无完整 grill；复核不引入术语或上下文歧义 | before-dev | not-required |
| book-ddia-data-design | 不改数据设计或写入路径；只复核既有 HTTP 声明 | before-dev | not-required；前序 confirmed 记录不在本轮重开 |
| book-legacy-change-safety | 不修改 runtime 行为 | before-dev | not-required |
| book-refactoring-pass | 无生产代码编辑 | before-dev | not-required |
| book-release-readiness | 无 runtime、部署或集成行为变更 | finish | not-required；不声称发布就绪 |

### 源码与清单

当前 `sbtd-runtime/serve.py:361` 是 `_AUTH_EXEMPT_PATHS = {"/api/v1/health", "/api/v1/session/pair"}`。middleware Bearer 失败在 `:393–396`：`authenticate` 返回 None 时 `_json({"detail": "unauthorized"}, 401)` 并 return。pair 自身失败在 `:416`。Host/Origin 403 仍在 `:382–386`，先于认证。`serve.py` 相对基线无 diff。

当前 OpenAPI 有 28 个 `/api/v1/*` operation，与基线 operation 身份一致。26 个非豁免 operation 的 `401` 均为 `$ref: "#/components/responses/Unauthorized"`，且相对基线新增的 response key 只有这 26 个 `401`，没有删除或改写既有 response。`GET /api/v1/health`（`getHealth`）responses 仍是 `403`/`200`，无 401；该 path block 与基线 byte-equal。`POST /api/v1/session/pair`（`pairSession`）整段与基线 byte-equal（651 bytes），401 仍是既有 Unauthorized ref，未重复、未改写、未移动。`Unauthorized` 组件文本与基线 byte-equal。非豁免 401 加 pair 既有 401 共 27 处，没有指向其他 401 schema。middleware 认证失败仍只对应 401，本轮没有为它发明额外状态码。

相对基线的已提交 diff 仍只有 `sbtd-runtime/contracts/openapi.yaml`、`sbtd-runtime/tests/test_golden_contracts.py`、本文件。openapi SHA-256 仍是 `c5d239fcc0004746a7a64ecbc23b5d207a054f5243dfc8b038b6fad3250a554e`；测试文件仍是 `8381d0cb49c4758d42bd7e8f58ce754966ba562763fe69010614dff39d108428`。

### 本轮验证

命令在仓库根执行。`PYTHONDONTWRITEBYTECODE=1` 与 `RUFF_NO_CACHE=true` 只防止仓库缓存。rtk: skipped-for-report。证据为 developer-local / dirty / local-only，绑定测试时 HEAD `bb2ba1b4a660b24ce7c70be14bf5d420b2b368df`，不冒充 CI 或 PR head。

| 精确命令 | 实际结果 | raw／同 stem 中文汇总 |
|---|---|---|
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_golden_contracts.OpenApiDraftTests -v` | 15 passed，0.058s，exit 0 | `local://auth-401-advisor-openapi.{json,md}` |
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py' -v` | 266 tests：265 passed、1 skipped，18.939s，exit 0；Windows junction evidence only | `local://auth-401-advisor-runtime.{json,md}` |
| `python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_runtime_r1_acceptance -v` | 68 passed，0.643s，exit 0；与 runtime 重叠，不累计 | `local://auth-401-advisor-wrappers.{json,md}` |
| `ruff format --check sbtd-runtime/tests/test_golden_contracts.py` | 1 file already formatted，exit 0 | `local://auth-401-advisor-format.{json,md}` |
| `ruff check sbtd-runtime/tests/test_golden_contracts.py` | exit 1；仅既有 I001，19–30 行，本轮不修 | `local://auth-401-advisor-lint.{json,md}` |
| 复用 `test_serve.ServeProcess` 的短真实 HTTP smoke | 6 checks passed；serve stop rc 0 | `local://auth-401-advisor-http-smoke.{json,md}` |

短 smoke：`GET /api/v1/health` 无 Bearer → 200 `{"status":"ok"}`；`GET /api/v1/metrics/catalog` 无 Bearer 与无效 Bearer → 401 `{"detail":"unauthorized"}`；`POST /api/v1/statistics/query` 无 Bearer → 401；`GET /api/v1/exports/smoke-id` 无 Bearer → 401；`POST /api/v1/session/pair` 错误配对码 → 401。不把这 6 项写成 26 路全量 HTTP；静态 26 路仍由 OpenApiDraftTests 覆盖。凭据未写入报告。

BDD: skipped；无行为变更，不新增 .feature。Cross-repo context: contract-only。API Contract: verified。Mock Strategy: none。E2E Mode: backend-only。Final Test Report / Run Summary MD: generated（仓库外 local://）。Final Full Rerun: 指定 unittest 与 format passed；lint 的 Final Full Rerun 是 failed，仅既有 I001。Targeted Rerun: not-needed。Graft: skipped。无生产 diff，本轮不做 ponytail-review。无长期 lesson。TaskStore 未调用：transition 会改终态，create/select 会写 index/active，超出本段只改本文件的授权；不声称 helper 恢复成功。

### 本轮模型计数（operator 回填）

来源：会话 jsonl `~/.omp/agent/sessions/--workspace-640-skills--/2026-10-20T13-17-10-870Z_01a15975-6f56-7492-b227-d4359c50f047.jsonl` 及子目录 `__advisor.jsonl`（advisor 子会话 id `01a15975-887a-743e-ae1f-d78b2f7a70ea`），计数口径同「模型使用」。上文“本轮 session id：unknown”由此回填为 `01a15975-6f56-7492-b227-d4359c50f047`。

| 用途 | 请求模型 | 实际模型 | assistant messages | 工具调用次数 |
|---|---|---|---|---|
| 本轮主会话（回退前） | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra | 1（error） | 0 |
| 本轮主会话（回退后） | fallback 角色 | xai-oauth/grok-4.7 | 25（24 toolUse + 1 stop） | 53 |
| 本轮 advisor | --advisor | xai-oauth/grok-4.7 | 22（20 stop + 2 toolUse） | 2 |
| 会话标题生成 | unknown | unknown | unknown（1 次 auto title 事件） | unknown |

Advisor observed blocker = 0：22 条 advisor 消息中 1 条为非阻塞纠正（提示报告不应写成“没有 advisor 运行”），其余均为 “No side effect to stop”／“No blocker”。

中止尝试：会话 `01a15974-e768-718a-b6ea-c30f0e60bcad` 启动后 astra 立即 error 并回退 grok-4.7，随后被 operator kill，未产出提交。计数：`openai-codex/gpt-6-astra` 1（error，0 工具调用）；`xai-oauth/grok-4.7` 4（3 toolUse + 1 aborted，9 工具调用）；其 `__advisor.jsonl`（子会话 `01a15974-fe12-72a0-8ee4-c6249b9ea5a4`）`xai-oauth/grok-4.7` 2（stop，0 工具调用）；auto title 1 次，生成模型 unknown。

### 本轮结论

无 advisor blocker，无契约或测试代码变更。若本段随后单独提交，只允许 `git add ai/tasks/v2.1.0-rc.2-contract-auth-401-responses/task.md`。不暂存 `.omp-r12b-addendum.txt` 与 `ai/tasks/codex-verify/`。不 push、不开 PR、不 merge。`/workspace/640-skills-r2.1a` 本轮未写入。

## PR #150 合并后回填（operator）

本段只回填合并后权威 SHA 与模型计数，不重开任务、不新增状态事件。权威实现 SHA：`10bc530caa263c0484046128218a8fc2936f523e`（PR #150 squash）；pre-merge `c9c9360`／`bb2ba1b`／`a5aa704` 作废。本回填编辑由 omp CLI 执行，jsonl 只记录 `kimi-code/k3`，不记录 thinking tier，故以下精确命令作为 `k3:max` 请求级别的证据（未启用 --advisor）：

`cd /workspace/640-skills-r2.1a && timeout 10800 omp -p --model kimi-code/k3:max --auto-approve "$(cat ~/.omp/logs/640-r21a-backfill-150/prompt.md)" </dev/null`
