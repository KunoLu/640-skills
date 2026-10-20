---
schema_version: 1
id: v2.1.0-rc.2-contract-export-error-responses
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict、contract-only；固定指定分支，基线必须保持为首提交 parent；仅显式 git add；不 push、不开 PR、不 merge、不变基线；禁止暂存 .omp-r12b-addendum.txt 与 ai/tasks/codex-verify/；不触碰 /workspace/640-skills 与 /workspace/640-skills-r2.1a 两个 worktree；不含模型表回填（外层 controller 后续补）。
status: done
branch: contract/v2.1.0-rc.2-export-error-responses
created_at: '2026-10-20T15:12:17.324062+00:00'
updated_at: '2026-10-20T15:13:26.380438+00:00'
completed_at: '2026-10-20T15:13:26.380438+00:00'
---

# Export get/download/delete 错误响应契约

## 范围与验收

基线 `10bc530caa263c0484046128218a8fc2936f523e`（#150 合并后 main HEAD），指定分支已核对，不切分支、不变基线。仅修改 `sbtd-runtime/contracts/openapi.yaml`、`sbtd-runtime/tests/test_golden_contracts.py` 和本文件。runtime、Dashboard、panel-manifest、ADR、PRD、CSV schema、plan.md 均不修改。`.omp-r12b-addendum.txt` 与 `ai/tasks/codex-verify/` 保持原状，不暂存或提交。`/workspace/640-skills`（detached main）与 `/workspace/640-skills-r2.1a`（R2.1a 另一 worker）不触碰；R2.1a runtime 仅经 `git show` 只读取证。

背景：Reviewy B1（PR #151）指出 runtime `export_resource` 会返回 400／404 ExportNotFound／409 ExportNotReady／410 ExportGone，而 main 的 openapi.yaml 对 getExport／downloadExport／deleteExport 只声明 401/403/2xx。用户决定本契约 PR 先合（沿用 #149、#150 先例），#151 随后 rebase。Reviewy 细化：只声明各操作代码路径真实可达的状态；409 与 DELETE 缺 Idempotency-Key 的 400 只能出现在对应操作上。

验收（逐操作精确响应集合，复用既有组件，保留 401/403/2xx）：

- getExport（GET `/api/v1/exports/{export_id}`）：200 Json、401 Unauthorized、403 Forbidden、**400 BadRequest、404 NotFound、410 Gone**；**不声明 409**（get 不抛 ExportNotReady）。
- downloadExport（GET `/api/v1/exports/{export_id}/file`）：200（既有 description 与 x-sbtd-csv-columns 保留）、401、403、**400、404、409 Conflict、410**。
- deleteExport（DELETE `/api/v1/exports/{export_id}`）：204、401、403、**400、404、410**；**不声明 409**（delete 不抛 ExportNotReady）。其 400 覆盖 query params 与缺 Idempotency-Key 两分支。

新增 OpenApiDraftTests 以 `test_snapshot_get_responses_match_runtime_handlers` 风格断言精确 status→`$ref` 组件映射（含保留的 401/403/2xx）。执行用户全部指定验证命令。仅本地两个提交，不 push、不开 PR、不 merge。

未完整调用 grill-with-docs：需求及逐操作验收表已由用户明确给出，状态可由 R2.1a 分支源码逐行确认，无领域歧义。主会话唯一 writer／验证 controller，独立审查只读且不运行测试。

## 源码证据与决定

runtime 事实源为 `feat/v2.1.0-rc.2-r2.1a-html-csv-export` 分支（只读 `git show`，未编辑该 worktree）。共享 handler `export_resource` 位于 `sbtd-runtime/serve.py:577–605`；store 位于 `sbtd-runtime/export_store.py`。以下行号由主会话与独立 correctness reviewer 分别在该分支上核实。

| operationId | 状态 | 本次动作 | serve.py 映射（R2.1a 分支） | export_store.py 抛出位置（R2.1a 分支） |
|---|---|---|---|---|
| getExport | 400 | 新增 BadRequest | `serve.py:579–580` query params 拒绝先于方法分发 | —（handler 直接返回） |
| getExport | 404 | 新增 NotFound | `serve.py:600–601` ExportNotFound | `export_store.py:622`（`_locked_job`，`:615–622`） |
| getExport | 410 | 新增 Gone | `serve.py:602–603` ExportGone | `export_store.py:619`（`_locked_job`）；`:341` ready 且过期 |
| downloadExport | 400 | 新增 BadRequest | `serve.py:579–580`（同上，先方法分发） | — |
| downloadExport | 404 | 新增 NotFound | `serve.py:600–601` | `export_store.py:622`（`_locked_job`） |
| downloadExport | 409 | 新增 Conflict | `serve.py:604–605` ExportNotReady | `export_store.py:349`（`download` 中 status != "ready" 抛出，`:344–353`） |
| downloadExport | 410 | 新增 Gone | `serve.py:602–603` | `export_store.py:619`；`:352` ready 且过期 |
| deleteExport | 400 | 新增 BadRequest | `serve.py:579–580` query params；`:583–584` 缺 Idempotency-Key → `"Idempotency-Key is required"` | — |
| deleteExport | 404 | 新增 NotFound | `serve.py:600–601` | `export_store.py:364`（`:355–380`） |
| deleteExport | 410 | 新增 Gone | `serve.py:602–603` | `export_store.py:361`（gone 集合） |

`ExportNotFound`／`ExportGone`／`ExportNotReady` 定义于 `export_store.py:53–61`。

关键差异化证据（防止把 409 毯式加到 get/delete）：

- `get`（`export_store.py:324–342`）：status != "ready" 时**返回 200 状态视图**（`_public_view`，`:328–337`），不抛 ExportNotReady；ready 且过期抛 ExportGone（`:341`）。故 getExport 无 409。
- `download`（`:344–353`）：status != "ready" 抛 ExportNotReady（`:349`）。409 仅属于 download。
- `delete`（`:355–380`）：仅抛 ExportGone（`:361`）／ExportNotFound（`:364`），永不抛 ExportNotReady。故 deleteExport 无 409。

### 考虑但未新增的状态

- 409（getExport／deleteExport）：无对应抛出路径，见上；精确集合测试同时锁定其缺席。
- 422／500／default：handler 无框架参数验证或声明式意外错误映射，不作推测性新增。
- 401／403／200／204：既有声明原样保留（#150 的 401、inline 200 `Authorized export bytes` 及其 x-sbtd-csv-columns、204 `Cancelled or cleaned` 均未改写）。
- createExport 及其他所有操作：不在本次范围，diff 确认未触碰。

## Book Gate Plan

| Gate | 触发事实 | 阶段 | 状态 |
|---|---|---|---|
| book-ddia-data-design | 持久 export job 之上的 HTTP 失败 wire contract | before-dev | passed / confirmed |
| book-ddd-distilled-modeling | 无完整 grill、无领域术语或边界歧义 | before-dev | not-required |
| book-legacy-change-safety | 不修改 runtime 行为；R2.1a 分支异常→HTTP 映射 seam 明确 | before-dev | not-required |
| book-refactoring-pass | 仅声明式契约／测试／任务记录，无生产代码编辑 | before-dev | not-required |
| book-release-readiness | 不改 runtime／部署／外部集成行为 | finish | not-required；不声称发布就绪 |

DDIA Data Design Review — confirmed。ExportStore（R2.1a 分支）是 job 状态与错误事实源，serve.py 仅做异常→HTTP 映射；本任务把既有映射声明进 openapi.yaml，无数据、schema、写入路径、一致性、幂等、排序、重试、去重、migration、backfill 或 replay 变更。DELETE 的 Idempotency-Key 要求经 400 声明，不改变幂等语义。回滚只撤回契约／测试；下游已依赖声明时须协调。验证用精确状态集合／组件引用断言与对基线的红灯证明。Ponytail：复用既有四个组件与 unittest，不新增 schema／依赖／helper。

## 状态持久化限制

指定根／分支／基线匹配；`readlink -f ai/tasks` 为普通目录无 symlink，任务目录创建前不存在。`git check-ignore .sbtd/active-task.json ai/tasks/v2.1.0-rc.2-contract-export-error-responses/reports/probe.json` 两项均匹配保护（exit 0）；`git ls-files -- .sbtd ai/tasks/v2.1.0-rc.2-contract-export-error-responses` 输出为空。沿用 #148/#149/#150 已记录的 TaskStore catalog `task has no YAML frontmatter block` 限制，不重复运行确认、不修改其他任务绕过；TaskStore.create 还会写 index/active，超出用户三文件授权。本文件为用户明确要求的共享交付记录，不声称 TaskStore helper 生命周期、active 或自动恢复成功；不写 active／身份／ignore。原生报告存于仓库外 `/home/box/sbtd-evidence/v2.1.0-rc.2-contract-export-error-responses/`，遵守仅三个允许文件写入仓库的边界。

## 验证命令与结果

所有命令在本 worktree 仓库根执行，带 `PYTHONDONTWRITEBYTECODE=1 RUFF_NO_CACHE=true`。原生 stdout／stderr、退出码、精确命令、UTC 捕获时间、完整基线 SHA、分支与 Linux 环境保存于仓库外 `/home/box/sbtd-evidence/v2.1.0-rc.2-contract-export-error-responses/<stem>.{json,stdout.txt,stderr.txt}`，同 stem 中文汇总为 `<stem>.md`。rtk: skipped-for-report。证据为 developer-local / dirty（提交前工作区）/ local-only，不冒称 CI、PR head 或发布证明。

| 精确命令 | 实际结果 | raw／同 stem 中文汇总 |
|---|---|---|
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_golden_contracts.OpenApiDraftTests -v` | 16 passed（含新增 test_export_responses_match_runtime_handlers，3 subTest），0.074s 内部／0.209s wall，exit 0 | `openapi.{json,md}` |
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py' -v` | 267 tests：266 passed、1 skipped（Windows junction evidence only，平台门控，与基线一致），19.453s 内部／19.822s wall，exit 0 | `runtime.{json,md}` |
| `python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_runtime_r1_acceptance -v` | 69 passed，0.625s 内部／0.765s wall，exit 0；与 runtime 套件重叠，不累计计数 | `wrappers.{json,md}` |
| `ruff format --check sbtd-runtime/tests/test_golden_contracts.py` | 1 file already formatted，exit 0 | `format.{json,md}` |
| `ruff check sbtd-runtime/tests/test_golden_contracts.py` | exit 1；仅用户已知 `I001`，19–30 行 import block 未修改；不修无关 lint | `lint.{json,md}` |
| 红灯证明：`PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -`（heredoc：把 `git show HEAD:sbtd-runtime/contracts/openapi.yaml` 注入 `OpenApiDraftTests.doc` 运行新测试） | exit 0；对基线 3 个 subTest 全失败（三操作各缺新增错误响应），证明测试真实锁定契约而非空断言；进程内执行，无仓库写入 | `red-proof.{json,md}` |

操作失误保留：首次 openapi 调用漏设 PYTHONPATH（exit 1，非项目失败），原始输出保留为 `openapi.misrun.{stdout,stderr}.txt`，随后以正确命令重跑得上表结果。

### 独立审查与可读性

- ExportCorrectness：correct（confidence 0.95），无 actionable finding。独立在 R2.1a 分支重核 `serve.py:579–605` 与 `export_store.py:324–380,615–622` 映射、逐操作精确集合、409 仅 download、组件复用、createExport 与其余操作未触碰、测试能捕捉 stray/missing status 与错误组件。只读，未执行测试。
- ExportMaintainability：lean，无必须削减项。确认 YAML 纯新增 20 行、局部顺序（401/403/2xx 后升序 4xx）与 createExport 及 #149 一致；测试为 snapshot 先例风格的最小扩展（method 字段 + inline 2xx pop），`pop` 无默认值故 inline 2xx 缺席会 KeyError，存在性仍被锁定；inline 200 内容不由本测试钉死（x-sbtd-csv-columns 已由既有测试对 `csv_export.COLUMNS` 锁定），避免措辞钉死。无死码、无重复可提取。
- 主会话在验证后完成 Ponytail／Code Readability Review：3 元组场景循环 + subTest + 精确字典断言；中文注释记录 409 缺席原因防止未来“一致性”误加；无新 import/helper/dependency、无 unrelated cleanup。

### 验证边界与跳过

- 真实 HTTP smoke：本 worktree 的 main 端 `sbtd-runtime/serve.py`（616 行）不含 `export_resource` 或任何 `/api/v1/exports/{export_id}` 路由——契约本就领先 runtime，这正是本 PR 先合、#151 后 rebase 的原因。export runtime 仅存在于 R2.1a 分支（另一 worker 的 worktree，不得编辑或运行），故本 worktree 无法对该路径做真实 HTTP smoke；动态一致性由 #151 自带 runtime 测试覆盖。本次以静态精确契约断言 + R2.1a 分支逐行源码证据 + 红灯证明为边界。
- BDD: skipped：本 worktree 无 runtime 用户可见行为变更（contract-only），不新增 .feature；契约回归由 OpenApiDraftTests 覆盖。Cross-repo context: contract-only；API Contract: verified（静态断言 + 分支源码证据）；Mock Strategy: none。
- E2E Mode: backend-only；Final Test Report / Run Summary MD: generated（仓库外证据目录）；Final Full Rerun: passed（用户指定 unittest 范围，保留平台 skip）；Targeted Rerun: not-needed。**lint 不全绿**，已知 I001 原始失败保留。
- Graft: skipped，以直接源码／契约为证据；无导出符号更改，不需 LSP refactor。未联网、未 cloud 索引。
- TS typecheck／Dashboard build／浏览器与移动端 E2E／全仓无关 workflow suite 未运行：对应文件和行为未改。完整 OAS meta-schema validator 未运行：沿用项目 YAML/contract 测试，不安装新依赖。
- 原生报告位于仓库外证据目录，不入库、不保证跨宿主自动恢复；仓库内 task 保存主要命令／结果／证据。无长期 lesson：本任务没有新 runtime 根因或新工作流事故，不修改身份／lesson 文件。

## 提交与恢复边界

RESULT：本次 contract-only 验收完成。实现提交 **`b122407f87423a860ff61fbd7a4bff268449884a`**，parent `10bc530caa263c0484046128218a8fc2936f523e`（基线保持为 parent），message 为 `contract(openapi): declare export error responses`。通过 `git add sbtd-runtime/contracts/openapi.yaml sbtd-runtime/tests/test_golden_contracts.py` 显式暂存，仅这两个文件进入实现提交；66 insertions、0 deletions，无 runtime 修改。

提交后读取两个 Git blob 计算 SHA-256，与验证快照 `validated-content.sha256` 完全一致（`committed-blobs.sha256`，diff 为空），因此不重复执行未改变内容的测试、不重跑已知 I001 来确认。

| 已验证并提交的文件 | SHA-256 |
|---|---|
| `sbtd-runtime/contracts/openapi.yaml` | `368b82fe3c3e5102b68aeffc1639cfa6690b6841932c91b5c22ec60642c33126` |
| `sbtd-runtime/tests/test_golden_contracts.py` | `c7fdea2232be47d8611359b67ed0cc1a2021884d43c34034f36e72b3214cca25` |

本完成记录以独立 docs 提交保存，从而能在 task 内记录真实实现 SHA，而不编造自身提交的自引用 SHA。暂存命令仅 `git add ai/tasks/v2.1.0-rc.2-contract-export-error-responses/task.md`；该记录提交的 SHA 由最终 stdout 与 `commit-receipt.json` 给出。最终修改文件总计三个，即上述契约／测试与本记录；两个禁止路径不暂存。未 push、未开 PR、未 merge、未 rebase、未部署／发布；模型表回填由外层 controller 后续小提交处理。完成只指本地契约交付；回滚需撤回本次实现提交并协调依赖消费者（#151 rebase），不改变存量 runtime 数据。TaskStore／自动恢复限制不变。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-20T15:05:55.350852+00:00 | planned | in-progress | 用户明确 strict；根、分支、基线、三操作存在性、组件存在性及 R2.1a 分支逐行 runtime 证据已确认 | 基线 10bc530caa263c0484046128218a8fc2936f523e；serve.py:577–605、export_store.py:324–380,615–622（R2.1a 分支，git show 只读） |
| 2026-10-20T15:09:37.258964+00:00 | in-progress | checking | 契约／测试完成（+66/-0），指定验证、红灯证明已取得，两位独立 reviewer 已派出 | OpenAPI 16 passed；runtime 267/1 skip；wrappers 69 passed；format passed；已知 I001；红灯 3 subTest 失败于基线 |
| 2026-10-20T15:13:26.380438+00:00 | checking | done | 独立审查双通过（correct / lean），实现提交的 blob 与验证快照一致；保留已知 I001 与 Windows skip | 实现提交 b122407f87423a860ff61fbd7a4bff268449884a，parent 为基线；两个 committed blob SHA-256 与验证快照一致；contract-only，无 runtime 修改 |
