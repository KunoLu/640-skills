---
schema_version: 1
id: v2.1.0-rc.2-contract-snapshot-error-responses
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict、contract-only；保持指定分支，仅显式 git add，不 push、不开 PR、不 merge；禁止提交两个用户路径。
status: done
branch: contract/v2.1.0-rc.2-snapshot-error-responses
created_at: '2026-10-20T10:50:35.455473+00:00'
updated_at: '2026-10-20T21:41:00+08:00'
completed_at: '2026-10-20T11:10:10.473847+00:00'
---

# Snapshot GET 错误响应契约

## 范围与验收

基线 `6e2cc56f386c603179ee6efd6004a24b5391ffc8`。只修改 `sbtd-runtime/contracts/openapi.yaml`、`sbtd-runtime/tests/test_golden_contracts.py` 和本 task。允许的两份说明仅在枚举目标 GET 响应时修改；读取后没有此枚举，因此保持不变。不修改 runtime、Dashboard、panel-manifest、ADR、PRD、CSV schema 或 plan.md；保留 `.omp-r12b-addendum.txt` 和 `ai/tasks/codex-verify/`，不暂存或提交。

验收：getReportSnapshot 的响应集合为 200/403/404/410，getSnapshotDataset 为 200/400/403/404/410；错误复用 createExport 的 NotFound/Gone/BadRequest。getReportSnapshot 的 410 原已存在，不重复新增。保留已有成功／403。用 OpenApiDraftTests 验证完整集合与引用，执行用户全部指定命令及真实 HTTP smoke。仅本地提交，不 push、不开 PR、不 merge。

未完整调用 grill-with-docs：需求及验收明确，状态可从源码确认。主会话唯一 writer／验证 controller，独立审查只读且不运行测试。

## 源码证据与决定

| Operation | 状态 | 本次动作 | serve.py 映射 | report_snapshot.py 抛出位置 |
|---|---|---|---|---|
| getReportSnapshot | 404 | 新增 NotFound | `sbtd-runtime/serve.py:453–454` | `sbtd-runtime/report_snapshot.py:682–683` malformed ID；`:732–733` 缺失／不可读文件；get 在 `:916` 调用 _read |
| getReportSnapshot | 410 | 保留 Gone | `sbtd-runtime/serve.py:455–456` | `sbtd-runtime/report_snapshot.py:914–918` 已知 gone／到期且无 pin |
| getSnapshotDataset | 404 | 新增 NotFound | `sbtd-runtime/serve.py:465–466` | `sbtd-runtime/report_snapshot.py:929` 调用 get；`:682–683`、`:732–733` |
| getSnapshotDataset | 410 | 新增 Gone | `sbtd-runtime/serve.py:467–468` | `sbtd-runtime/report_snapshot.py:929` → `:914–918` |
| getSnapshotDataset | 400 | 新增 BadRequest | `sbtd-runtime/serve.py:469–470` | `sbtd-runtime/report_snapshot.py:932–937` 解码／跨快照／越界 cursor；解码抛出处 `sbtd-runtime/history_read.py:48–53` |

`SnapshotNotFound`、`SnapshotGone` 定义于 `report_snapshot.py:71–76`；CursorError 从 history_read 导入。仓库不存在 report.py（精确文件名 glob 无结果），实际 owner 为 report_snapshot.py。

SnapshotId description 保持不变：NotFound 组件仅说 missing/invisible，新增响应本身没有说明 malformed PATH ID 按 404 处理，因此该说明不重复；保留原格式／pattern 注释和 schema。两份指定说明只描述存储生命周期及 createExport／PATH 对比，没有枚举目标 GET 的响应集合，保持不变。

### 考虑但未新增的状态与后续边界

- 400（getReportSnapshot）：handler 没有 cursor／请求体校验分支；malformed ID 抛 SnapshotNotFound，返回 404，不新增 400。
- 401：**共享 SecurityMiddleware 确实在 `serve.py:394–395` 返回 401**，不是运行时不存在。本次按用户列明的 snapshot handler 错误范围不扩展公共认证契约；记录为独立后续契约缺口，不改 middleware，不把精确集合测试解释成整个 ASGI 栈仅可能这些状态。
- 422：两个 handler 没有框架参数验证／422 分支，不新增。
- 500／default：没有目标 handler 的声明式错误映射；未处理的意外异常不构成本次要承诺的响应契约，不作推测性新增。
- 403／200：原声明保留；403 对应共享 Host／Origin 拒绝（serve.py:382–385），本次不改变安全语义。
- 其他状态（如 409、429、503）：无目标 handler 证据，不新增。
- 无须 runtime 修改才能补齐本次映射；不引入运行时修复。既有 library/no HTTP server 摘要与当前 serve 实现的历史差异不在本次状态声明范围。

## Book Gate Plan

| Gate | 触发事实 | 阶段 | 状态 |
|---|---|---|---|
| book-ddia-data-design | HTTP 失败响应 wire contract | before-dev | passed / confirmed |
| book-ddd-distilled-modeling | 无完整 grill、无领域术语或边界歧义 | before-dev | not-required |
| book-legacy-change-safety | 不修改 runtime 行为；现有明确异常和 HTTP seam | before-dev | not-required |
| book-refactoring-pass | 仅声明式响应／测试／任务记录，无生产代码编辑 | before-dev | not-required |
| book-release-readiness | 不改 runtime／部署／外部集成行为 | finish | not-required；不声称发布就绪 |

DDIA Data Design Review — confirmed。SnapshotStore 为数据与错误事实源，serve 映射为 HTTP；dataset 先 get 再解码 cursor，缺失／过期优先。无读写一致性、持久数据、幂等、重试、排序、迁移、backfill 或 replay 变更。回滚只撤回契约／测试；下游已依赖声明时须协调。验证用精确状态集合／组件引用、真实临时数据 HTTP 请求及指定套件。Ponytail：复用已有组件和 unittest，不增加 schema／依赖／helper。

## 状态持久化限制

指定根／分支／基线匹配；逐级检查 task 路径无 symlink、目标不存在；`git check-ignore .sbtd/active-task.json ai/tasks/v2.1.0-rc.2-contract-snapshot-error-responses/reports/probe.json && git ls-files -- .sbtd ai/tasks/v2.1.0-rc.2-contract-snapshot-error-responses` 确认本地保护，tracked 输出为空。沿用 #148 task 已记录的 TaskStore catalog `task has no YAML frontmatter block` 限制，不重复运行确认、不修改其他任务来绕过。本文件为用户明确要求的共享交付记录，不声称 TaskStore helper 生命周期、active 或自动恢复成功；不写 active／身份／ignore。原生报告存于仓库外 local:// 工具产物，遵守仅三个允许文件写入的边界。

## 验证命令与结果

所有命令在仓库根执行，原生 stdout／stderr／退出码／命令／时区时间／完整基线 SHA／Linux 环境保存于仓库外 `local://snapshot-errors-<stem>.json`，同 stem 中文汇总为 `.md`。rtk: skipped-for-report。证据为 developer-local / dirty / local-only，不冒称 CI、PR head 或发布证明。

| 精确命令 | 实际结果 | raw／同 stem 中文汇总 |
|---|---|---|
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_golden_contracts.OpenApiDraftTests -v` | 13 passed，0.056s，exit 0 | `local://snapshot-errors-openapi.{json,md}` |
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py' -v` | 264 tests：263 passed、1 skipped，17.368s，exit 0；skip 为 Windows junction evidence only | `local://snapshot-errors-runtime.{json,md}` |
| `python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_runtime_r1_acceptance -v` | 66 passed，0.593s，exit 0；与 runtime 重叠，不累计计数 | `local://snapshot-errors-wrappers.{json,md}` |
| `ruff format --check sbtd-runtime/tests/test_golden_contracts.py` | 1 file already formatted，exit 0 | `local://snapshot-errors-format.{json,md}` |
| `ruff check sbtd-runtime/tests/test_golden_contracts.py` | exit 1；仅用户已知 `I001`，19–30 行 import block 未修改；不修无关 lint | `local://snapshot-errors-lint.{json,md}` |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -c <smoke source>` | exit 0；13 个真实 HTTP 检查通过，0.586s（进程总时长） | `local://snapshot-errors-http-smoke.{json,md}` |

Smoke 的完整可复现 `-c` 命令（含全部源码）在该 raw 的 `command` 字段及中文汇总「运行命令」中。脚本仅在进程内运行；用既有 ServeProcess 启动真实 serve 子进程、真实 loopback socket、临时 SnapshotStore／golden dataset，没有 mock。临时数据及服务在 finally 清理，没有新增仓库脚手架。

| Method / URI | 真实检查 | 状态／响应 |
|---|---|---|
| GET `/api/v1/report-snapshots/{snapshot_id}` | 有效、畸形 ID、格式正确但缺失、过期 | 200（ID 一致）／404／404／410；错误 detail 匹配 |
| GET `/api/v1/report-snapshots/{snapshot_id}/dataset` | 有效、畸形 ID、格式正确但缺失、过期 | 200（ID 一致）／404／404／410；错误 detail 匹配 |
| GET `/api/v1/report-snapshots/{snapshot_id}/dataset` | cursor 解码错误、跨快照、越界 | 各 400，含 detail |
| GET `/api/v1/report-snapshots/{snapshot_id}/dataset` | 畸形 ID／过期快照同时传坏 cursor | 404／410，确认 get 优先 |

### 独立审查与可读性

- SnapshotCorrectness：correct，无 actionable finding；独立核对各异常／HTTP 映射、已有 410、四个新引用和证据行号。仅只读审查，不冒充执行测试。
- SnapshotMaintainability：Lean already；net 0 lines required。确认完整 response map 防止额外状态、组件复用、200／403 保留、SnapshotId 说明不重复，以及两份可选文档无需修改。
- 两位 reviewer 的可选命名建议：测试名 `match_runtime_handlers` 容易被理解成动态检查 handler。保留当前名字，其含义为源码证据确定的预期集合；明确永久测试仅检查 OpenAPI，动态一致性由上列独立真实 HTTP smoke 提供，不把静态断言冒充 runtime 执行。
- 主会话在 smoke 后完成 Ponytail／Code Readability Review：单个两行场景矩阵、subTest 和精确字典断言；无新 import/helper/dependency、无 unrelated cleanup。

### 验证边界与跳过

- BDD: skipped：无 runtime 用户可见行为变更；用户限制说明文件仅在枚举响应时改动，已有文档不枚举本次集合，因此不新增 .feature／场景。契约边界由新 OpenApiDraftTests 回归覆盖。Cross-repo context: contract-only；API Contract: verified（声明与上述真实 backend smoke）；Mock Strategy: none。
- E2E Mode: backend-only；Final Test Report / Run Summary MD: generated；Final Full Rerun: passed（用户指定 unittest 范围，保留平台 skip）；Targeted Rerun: not-needed。**lint 不全绿**，已知 I001 失败报告保留。
- Graft: skipped，以直接源码／契约为证据；没有导出符号更改，不需 LSP refactor。未联网、未 cloud 索引。
- TS typecheck／Dashboard build／浏览器与移动端 E2E／全仓无关 workflow suite 未运行：对应文件和行为未改。完整 OAS meta-schema validator 未运行：本次沿用现有 YAML/contract 测试，不安装新依赖。
- 401 是真实共享 middleware 行为但未补入本次 handler-error 契约，见前述后续边界。SnapshotId pattern、createExport、成功响应、权限声明、组件定义均不变。
- 原生报告位于当前会话工具产物，不入库、不保证跨宿主自动恢复；仓库内 task 保存主要命令／结果／证据。无长期 lesson：本任务没有新 runtime 根因或新工作流事故，不修改身份／lesson 文件。

## 提交与恢复边界

RESULT：本次 contract-only 验收完成。本地实现提交曾为 `0cf687833c0afc59dd822b2c1577b45ed67dcd24`（message `feat(contract): declare snapshot 404/410 and dataset 400 error responses`），经 PR #149 squash-merge 后，**权威实现 SHA 为 `ef8975212a4f80686d19a03f3c169bbf533eb117`**。pre-merge 本地／PR tip SHA（含 `0cf687833c0afc59dd822b2c1577b45ed67dcd24`）在 squash 后作废，不以 ancestry 声称。通过 `git add sbtd-runtime/contracts/openapi.yaml sbtd-runtime/tests/test_golden_contracts.py` 显式暂存，仅这两个文件进入实现提交；26 insertions，无 runtime 修改。

**Squash 权威说明**：合并后以 squash commit `ef8975212a4f80686d19a03f3c169bbf533eb117` 为权威（Codex P2 on #149 曾误称 ancestry；以本处记录 squash SHA 处理，无 force-push）。

用户在 host pause 后明确要求继续。本次恢复只读确认原分支／基线、checking 状态及保留证据；`sha256sum sbtd-runtime/contracts/openapi.yaml sbtd-runtime/tests/test_golden_contracts.py` 与暂停前 `local://snapshot-errors-validated-content.json` 完全一致。提交后读取两个 Git blob 计算 SHA-256，再次确认与已验证内容一致，因此不重复执行未改变内容的测试、不重跑已知 I001 来确认。

| 已验证并提交的文件 | SHA-256 |
|---|---|
| `sbtd-runtime/contracts/openapi.yaml` | `a4dfd4a05651a4a0c8032598d8b8e04a83ca20f3b2cdd3eecf716ba33a0528d4` |
| `sbtd-runtime/tests/test_golden_contracts.py` | `00d9dde9529c6fe04a81a8473760271839967938bbadb11a89e041f684bf9996` |

本完成记录以独立 docs 提交保存，从而能在 task 内记录真实实现 SHA，而不编造自身提交的自引用 SHA。暂存命令仅 `git add ai/tasks/v2.1.0-rc.2-contract-snapshot-error-responses/task.md`；该记录提交的 SHA 由最终 stdout 与 `local://snapshot-errors-commit-receipt.json` 给出。最终修改文件总计三个，即上述契约／测试与本记录；两个禁止路径不暂存。未 push、未开 PR、未 merge、未部署／发布。完成只指本地契约交付；回滚需撤回本次实现提交并协调依赖消费者，不改变存量 runtime 数据。TaskStore／自动恢复限制不变。

## 模型使用

来源：operator 核验的会话 jsonl（与 PR #149 body 模型表一致）。计数口径为 assistant messages。主会话请求 `openai-codex/gpt-6-astra:high`，实际 `openai-codex/gpt-6-astra`；独立 review 实际 `kimi-code/k3`（请求 tiers max/high 若已知则记；本表按 PR body 核实结果）。

**分段口径（按进程，不按墙钟）**：主会话中断前 13（12 正常 + 1 aborted，jsonl 中 `stopReason: aborted`）；续跑 resume 8。若按墙钟切分则为 12+9。会话标题生成：unknown。

| 用途 | 请求模型 | 实际模型 | assistant messages | 工具调用次数 |
|---|---|---|---|---|
| 主会话，中断前（18:49–18:55 北京时间） | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra | 13（12 正常 + 1 aborted） | unknown |
| 主会话，续跑后（19:09–19:11 北京时间，同一会话 `--resume`） | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra | 8 | unknown |
| 独立 SnapshotCorrectness review | kimi-code/k3（tier max/high if known） | kimi-code/k3 | 10 | unknown |
| 独立 SnapshotMaintainability review | kimi-code/k3（tier max/high if known） | kimi-code/k3 | 9 | unknown |
| 会话标题生成 | unknown | unknown | unknown | unknown |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-20T10:50:35.455473+00:00 | planned | in-progress | 用户明确 strict；根、分支、安全路径及 handler 证据已确认 | 基线 6e2cc56f386c603179ee6efd6004a24b5391ffc8；上表 serve.py / report_snapshot.py |
| 2026-10-20T10:54:46.099185+00:00 | in-progress | checking | 四个响应引用及完整集合回归已完成，指定验证与独立审查已取得 | OpenAPI 13；runtime 264/1 skip；wrappers 66；format passed；已知 I001；13 HTTP checks；两位 reviewer 无阻塞 finding |
| 2026-10-20T11:10:10.473847+00:00 | checking | done | 暂停后确认原绑定与已测内容一致；指定验证、真实 HTTP smoke、独立审查完成并提交实现；保留已知 I001 与 Windows skip | 本地实现曾为 0cf687833c0afc59dd822b2c1577b45ed67dcd24；PR #149 squash-merge 权威 SHA ef8975212a4f80686d19a03f3c169bbf533eb117（pre-merge SHA 作废）；两个 committed blob SHA-256 与验证快照一致；contract-only，无 runtime 修改 |
| 2026-10-20T21:41:00+08:00 | done | done | Closeout backfill：以 squash `ef8975212a4f80686d19a03f3c169bbf533eb117` 为权威实现 SHA；回填模型表（主会话 13+8、review 10+9）；pre-merge SHA 作废；无 force-push | PR #149 squash `ef8975212a4f80686d19a03f3c169bbf533eb117`；operator 核验会话 jsonl / PR body |
