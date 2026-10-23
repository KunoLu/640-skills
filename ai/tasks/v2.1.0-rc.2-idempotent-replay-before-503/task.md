---
schema_version: 1
id: v2.1.0-rc.2-idempotent-replay-before-503
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict；主会话唯一 writer／验证 controller；仅本 worktree 本地追加提交，显式 git add；不 push／PR／评论／merge／rebase／amend，不改 OpenAPI／schema／PRD／ADR／全局配置或其他 worktree，不暂存 reports、.env、.omp-r12b-addendum.txt 或 ai/tasks/codex-verify/。
status: done
branch: fix/v2.1.0-rc.2-idempotent-replay-before-503
created_at: '2026-10-23T09:51:34+08:00'
updated_at: '2026-10-23T10:09:34+08:00'
completed_at: '2026-10-23T10:09:34+08:00'
---

# rc.2 后续项 D runtime：幂等重放先于 503 与准入检查

## 范围与验收

任务来源：用户 2026-10-23 约 09:46 +08:00「640 step 1: fix PR」；Lord 2026-10-22 23:26 +08:00 最终清单、Reviewy 条件及 Lord／Reviewy 2026-10-23 09:47 +08:00 补充（来源：编排方转述）。入口 origin/main／HEAD `de97926811410e7d61d846fc8e95ddaa0738bfbf`（PR #159 squash-merge），授权根 `/workspace/640-skills-s1fix`。未完整调用 grill-with-docs：规则与契约已明确，无新领域决定。

首 commit `c595001` 仅 plan 与契约 follow-up D task：核实 #159 两类时间、最终 13／31，旧状态事件逐字保留；B／C 移至 E 前 Docs P6.5，E P7／F P8 与其他任务表行不变，F 仅发布记录回填。该 commit 已完成，不混入 runtime。

本次仅修复 createExport：401／403 访问检查及识别重放所需 400 校验后，同 key／canonical payload 重放返回原 202、ID 与 warnings，不执行能力检查、pin、JPEG preflight 或新建。不同 payload 仍 400；新请求保持 503→404→410→507→422 的适用顺序。507 为契约定义，runtime 配额尚未实现（R2.2），不新增配额逻辑或伪造用例。更新安装说明及既有 `sbtd-runtime/spec/r2.1b-renderer-scenarios.md`；沿用中文场景／英文 Gherkin 关键词、Markdown spec 与 unittest，不引入 .feature runner。

用户已指定 HTTP seam。新增回归放 `HttpRendererSeamTests`，复用真实 loopback HTTP／Store、用户认可的 renderer worker 替身；不是实际浏览器或跨平台 E2E。必须先运行新用例证明未修改 serve.py 的红灯，再修复、定向复跑、全 runtime suite、golden 61 与消费者 smoke。现有覆盖只引用不重复。

## Book Gate Plan

| Gate | 客观触发／阶段 | 状态 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill／领域歧义 | not-needed；未完整 grill，无领域歧义。 |
| book-ddia-data-design | 跨请求幂等与读路径／设计前 | confirmed；已独立输出 DDIA Data Design Review：ExportStore 唯一所有者，锁内读取 replay ID／warnings，共享 canonical digest；miss 后保留 create 的两次锁内检查，无新索引、持久格式或迁移。 |
| book-legacy-change-safety | 既有 HTTP 行为缺陷／生产编辑前 | characterized；已输出 Legacy Change Safety Review：修正 fixture 后基线 5 tests／4 failures／17.110s；503 遮蔽原 202 及冲突 key 的 400，404／410／422 保留路径已通过。无需新 seam。 |
| book-refactoring-pass | 既有生产代码编辑／legacy characterized 后 | proceed（normal）；已输出 Refactoring Review：仅提取现有 fingerprint 计算供 create／lookup 共用；保留 create 双重 replay 检查、访问控制、错误映射及新请求准入顺序，不夹带重构。 |
| book-release-readiness | runtime 行为／验证后 | ready（仅本次本地修复范围）；已输出 Release Readiness Review：必需验证通过、无迁移，既有锁／去重与生命周期不变，安装说明给出重放与 quota 边界。撤回修复提交无需数据清理；不等同整个 rc.2 发布验收。 |
| TDD／gherkin-bdd／ponytail | 明确 HTTP seam／before-dev、check | 复用既有 spec 与 unittest；最小 Store 只读查询，无第二份索引、依赖或配额。 |
| 独立 review／可读性 | 幂等公共 HTTP 行为／check | correct；ReplayRuntimeReview 与 ReplayCoverageReview 均无 findings，confidence 0.9；两位只读，未运行 build／lint／tests／formatter。主会话唯一 writer／controller；不是外部 Reviewy 的 PR 审查。 |
| project-validation | 用户指定命令／check | 指定 golden／runtime、定向 HTTP、真实进程 smoke、ruff check／format、YAML／报告消费者检查通过；原生命令保存 raw 与同 stem 中文汇总，rtk skipped-for-report。 |

## 验证证据

记录提交前消费者 smoke 已通过：yaml.safe_load、status done／completed_at／历史 branch 不变、旧状态事件前缀逐字不变、受保护任务表各行逐字相等；`git diff --check` exit 0。只读 `git log -1 --format=%cI de97926` 得 `2026-10-22T22:43:14+08:00`；`gh pr view 159 --json mergedAt,mergeCommit,state` 得 MERGED／预期 SHA／`2026-10-22T14:43:15Z`（+08:00 为 `2026-10-22T22:43:15+08:00`）。fix batch 2 JSONL 84 行：13 assistant／31 toolCall、openai-codex/gpt-6-astra、high、fallback false。

507 not-applicable：工具 grep `DISK_QUOTA_EXCEEDED|\b507\b` 搜索 `sbtd-runtime/*.py` 无匹配。契约 #159 仍定义 replay precedes 507；不把缺 runtime 路径写成通过。LSP status 实际返回 No language servers configured for this project，改用已读源码与定向引用搜索。

### 原生验证命令与结果

执行环境 Linux／Python 3.13.5，工作根为授权 worktree；以下命令均 native，`rtk: skipped-for-report`。8 对报告位于本 task ignored `reports/`，每对 `.json` raw 与同 stem 九节中文 `.md`；raw 含命令、stdout／stderr、退出码、真实时间、完整 HEAD `c595001` 对应 SHA、环境和五个被测文件 SHA-256。`Evidence Source: developer-local`、`Source Revision: dirty`、`Environment Alignment: unverified`、`Evidence Publication: local-only`，不是新 PR-head CI。

定向命令（红／绿使用同一组 5 tests）：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python -B -m unittest \
  test_renderer_integration.HttpRendererSeamTests.test_replay_precedes_unavailable_renderer_for_jpeg_and_pdf \
  test_renderer_integration.HttpRendererSeamTests.test_replay_precedes_missing_and_gone_snapshot \
  test_renderer_integration.HttpRendererSeamTests.test_new_requests_keep_renderer_snapshot_and_size_precedence \
  test_renderer_integration.HttpRendererSeamTests.test_replay_still_requires_access_and_valid_request \
  test_renderer_integration.HttpRendererSeamTests.test_idempotent_jpeg_replay_keeps_warning_without_new_preflight -v
```

| 命令／轮次 | 实际结果（runner 耗时；括号为墙钟） | 报告 label／真实开始时间 +08:00 |
|---|---|---|
| 上述定向命令，初次 red | exit 1；5 tests／5 failures，17.873s（18.176s）；包含一个测试 fixture Content-Type 被 helper 覆盖的问题，非额外产品缺陷 | baseline-red／09:54:31 |
| 上述定向命令，修正 fixture 后 red | exit 1；5 tests／4 failures，17.110s（17.324s）；jpeg/pdf 重放得 503 而非 202，冲突 payload 得 503 而非 400，另含一次 capability 调用关联断言；404／410／422 与新请求顺序通过 | baseline-red-corrected／09:55:14 |
| 上述定向命令，green | exit 0；5 passed，16.824s（17.035s） | targeted-green／09:56:23 |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python -B -c <process smoke>` | exit 0；4.115s；真实 serve 子进程恢复 JPEG/PDF，实际 capability unavailable，replay 原 202／ID／warnings，新 key 503，导出文件集合不变；初始 ready 产物由既有 worker 替身生成 | process-smoke／09:57:58；完整脚本在 raw.command，无落盘脚手架 |
| `RUFF_NO_CACHE=true ruff check sbtd-runtime/serve.py sbtd-runtime/export_store.py sbtd-runtime/tests/test_renderer_integration.py` | exit 0；All checks passed，0.096s | ruff-check／09:58:02 |
| `RUFF_NO_CACHE=true ruff format --check sbtd-runtime/serve.py sbtd-runtime/export_store.py sbtd-runtime/tests/test_renderer_integration.py` | exit 0；3 files already formatted，0.020s | ruff-format／09:58:02 |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python -B -m unittest sbtd-runtime/tests/test_golden_contracts.py -v` | exit 0；61 passed，0.322s（0.428s） | golden-final／09:58:11 |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python -B -m unittest discover -s sbtd-runtime/tests` | exit 0；378 tests，368 passed／10 skipped，122.100s（122.500s）；基线 374，新增 4 tests | runtime-full／09:58:11 |

报告完整 stem 规则：`reports/api-report-<label>-fix_v2.1.0-rc.2-idempotent-replay-before-503-2026-10-23T<HH-MM-SS>+08-00`；上表逐项给出 label 与时间，扩展名 `.json`／`.md`。两次 red 保留；修正 fixture 后仍在未改生产代码上运行。运行前逐字比较 serve.py／export_store.py 与 `git show origin/main:<path>` 相等；修复后的五个被测文件哈希与 full-suite raw 一致。原生 full-suite 未列逐例 skip 名称，不推断其原因，不将 378 写成全部 passed。

本次新 HTTP 证据：`test_renderer_integration.py:1328` 覆盖 jpeg/pdf 依赖消失后的原 ID／warnings、零 capability／pin／preflight、新 job 集合与 exports 文件不变；`:1364` 真实移除 snapshot 文件／sweep 后新 key 404／410，而旧 key 返回原 202；`:1406` 新请求 503 优先于 404／410，依赖可用时快照拒绝先于 JPEG 422；`:1430` replay 仍受 401／403、content type／key／request 400 和冲突 payload 400 约束。422 重放增强既有 `:1467`，不另复制同路径用例；新 key 真正得到 422，重放保留降级告警且不重复预检。

### 复用的既有测试（当前 file:line）

- `sbtd-runtime/tests/test_export_store.py:512` — canonical 字段顺序、payload 变化拒绝、空 key、无 key、重启恢复同一 ID。
- `sbtd-runtime/tests/test_export_store.py:665` — 8 个并发同 key 请求只建一个作业；本次保留 create 的锁内双重检查。
- `sbtd-runtime/tests/test_export_store.py:322` — sweep／启动清扫只触及已验证过期导出，既有保留边界不改。
- `sbtd-runtime/tests/test_exports_http.py:308` — 必需 headers、HTTP 幂等同 ID 与 payload 变化 400。
- `sbtd-runtime/tests/test_exports_http.py:210` — 缺失／外来 snapshot 404、过期 410。
- `sbtd-runtime/tests/test_renderer_integration.py:1194` — 新 jpeg/pdf 依赖不可用精确 503、零作业／文件／pin，503 先于可组合尺寸 422。
- `sbtd-runtime/tests/test_renderer_integration.py:1235` — 新 JPEG 超限精确 422／有效 caps、零作业／文件／残留 pin。
- `sbtd-runtime/tests/test_renderer_integration.py:1467`（基线 :1328）— 同 key JPEG 原告警与重启恢复，无重复预检；本次在原测试上增强后来 caps 拒绝路径。
- `sbtd-runtime/tests/test_golden_contracts.py:875` — #159 重放优先级分类；本次 golden 文件完全不改。

`git diff --check` exit 0；`git diff origin/main --stat -- contracts` 输出为空，并额外核对实际 `sbtd-runtime/contracts` 输出为空。两份 task frontmatter 经 `yaml.safe_load` 成功；旧 task 的 status done／completed_at／branch 不变、旧事件逐字保留。报告消费检查确认同 stem、九节顺序、无未填模板、退出码／命令与 raw 一致。

`BDD: traceable`：既有 Markdown spec 中文场景／英文关键词，以上 unittest 对应，无新 BDD runner；`Cross-repo context: not-needed`（单仓），`API Contract: verified`（既有 #159 golden），`E2E Mode: mock-backed`（loopback HTTP），smoke 为真实进程／依赖检查、替身生成的 seed 产物，不冒充真实 browser 渲染。`Mock Strategy: user-approved`。`Final Test Report／Run Summary MD: generated`；`Targeted Rerun／Final Full Rerun: passed`，仅指定 runtime 范围。ty 不可用，未安装；LSP 无配置，未声称静态类型通过。根 CI、Web／Mobile、跨平台、真实浏览器视觉／字体验证未执行，本次不改其路径且由 R2.2 负责。Ponytail Review：Lean already；共享 fingerprint 避免两套 canonical 规则，无新增依赖或无用 seam。Code Readability Review：沿用现有命名、HTTP fixture 与明确条件矩阵；不重构其他模块。

独立审查闭环：ReplayRuntimeReview 核实 RLock 重入、原 fingerprint 等价、create 双重去重、HTTP 前置访问／校验与原 warning；ReplayCoverageReview 核实 HTTP 条件矩阵、既有 coverage 复用、docs/spec、首 commit 两路径及旧事件／受保护任务表行不变。均无有效 finding，无需生产修正；CoverageReview 的非阻塞行号提示已由 `:1405` 修正为 `:1406`。所有运行时测试与 smoke 均由主会话执行。首轮 fixture Content-Type 失误已在本 task 与失败报告留存，不上升为新全局规则或写入他人 lesson／developer 身份。

Release Readiness Review：服务入口仅改变重复 createExport 的查询顺序；可用性下降不重新准入已有请求，原成功/失败/取消/清扫与 worker backpressure 不变；没有新重试、队列或容量策略，507 仍待 R2.2。安全错误与现有日志机制不变，安装说明是本次操作指引。无 schema、持久格式或依赖变更；回退修复 commit 可恢复旧顺序，不执行数据清理。用户限定的本地测试全部满足；跨平台、真实 renderer 视觉／字体及 quota 属明确未授权的 R2.2 工作，本地 ready 不能代表 rc.2 发布就绪。

## 提交与恢复边界

路径逐级检查无 symlink／逃逸，新 task 不存在；reports 受 `.gitignore:4:/ai/tasks/**/reports` 保护。沿用已读 rc.2 task 记录的 TaskStore catalog/frontmatter 兼容限制，不重跑已知失败；helper active／index 写入超授权。使用 edit/write 保存指定共享 task，不声称 TaskStore helper 生命周期或自动恢复成功。task index、active、ignore 与 developer 身份不改；契约旧 task 历史 branch 不重绑定。

无持久格式／schema 迁移。撤回本次 runtime 提交恢复旧 HTTP 顺序，不删除用户数据；不会推送、提 PR、合并、部署或发布。历史事件仅追加。

本地提交：

1. `c595001` — `docs(plan): backfill #159 (de97926) merge record; move follow-ups B/C before E; record final 13/31 count`；仅两份 records。
2. `c4480deaf2b260c065bcefea3012655a8d1e4753` — `fix(serve): idempotent createExport replay precedes renderer 503 and admission checks (rc.2 follow-up D runtime)`；serve／Store／HTTP tests／安装说明／既有 spec。五个提交 blob SHA-256 与 full-suite 被测哈希逐项相等；这是内容身份重验证，不冒称提交后新 CI。
3. `docs(task): record idempotent-replay-before-503 fix task` — 仅本 task，SHA 由最终 stdout 给出，避免自引用。

每次仅显式 `git add <path>`；报告与所有禁止路径未暂存。无自动恢复承诺，保留共享 task 的静态记录恢复边界。

## 模型使用

| agent/session | provider/model | thinkingLevel (from thinking_level_change) | assistant messages / toolCall blocks | purpose | resolvedModelIsFallback | title-generation count | job-widget entries |
|---|---|---|---|---|---|---|---|
| 本次主会话／01a16672-d532-73f1-b125-363df6adb0b0 | openai-codex/gpt-6-astra | high | 37 / 85（提交前 snapshot，2026-10-23T10:09:34+08:00） | 唯一 writer／验证 controller | false | 未知 | 未知 |
| Ping／01a16672-07b5-724c-b90e-dfe6ac1c8262 | openai-codex/gpt-6-astra | high | 1 / 0（最终） | ping | false | 未知 | 未知 |
| ReplayRuntimeReview／ReplayRuntimeReview.jsonl | kimi-code/k3 | max | 33 / 37（最终） | 只读并发／生命周期／优先级审查 | false | 未知 | 未知 |
| ReplayCoverageReview／ReplayCoverageReview.jsonl | kimi-code/k3 | max | 29 / 37（最终） | 只读测试／记录／文档审查 | false | 未知 | 未知 |

只读 JSONL 核实：主会话 `~/.omp/agent/sessions/--workspace-640-skills-s1fix--/2026-10-23T01-49-24-146Z_01a16672-d532-73f1-b125-363df6adb0b0.jsonl`，cwd／任务匹配，取样至 213 行；ping 为 `~/.omp/agent/sessions/-tmp-s1fix-ping/2026-10-23T01-48-31-541Z_01a16672-07b5-724c-b90e-dfe6ac1c8262.jsonl` 共 9 行；两 reviewer 在主会话同 stem 子目录，共 116／112 行。口径为 `type=message`／`role=assistant` 及其 `type=toolCall` blocks；model 来自 `model_change`，thinking 来自 `thinking_level_change`，不从 effort 推断。主会话与 ping 实际回复仅 astra，reviewer 仅 k3；未指定子代理模型，无 grok 回复、无 fallback。主会话计数不含后续记录编辑、校验、提交与最终回复；编排方在 PR 正文报告最终计数。title-gen／job-widget 无可用计数记录，保留未知，不记作 0。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-23T09:51:34+08:00 | planned | in-progress | 用户 strict／user；保存本地模式、范围与验证计划；首 records commit 已完成 | 授权根与分支匹配；入口 de97926811410e7d61d846fc8e95ddaa0738bfbf；c595001 仅两份 records；507 runtime grep 零匹配；LSP 无配置；无持久迁移 |
| 2026-10-23T10:00:37+08:00 | in-progress | checking | 红灯→修复→定向绿灯、真实进程 smoke 与指定 suites 已完成；进入独立审查和最终记录 | corrected red：5 tests／4 failures／17.110s；green：5 passed／16.824s；process smoke exit 0／4.115s；golden 61 passed／0.322s；runtime 378 tests／368 passed／10 skipped／122.100s；ruff check 0.096s 与 format 0.020s exit 0；8 对 raw／中文报告保留；diff check／两份 YAML／contracts 空 diff 通过；首轮 fixture 失误记录不删除 |
| 2026-10-23T10:09:34+08:00 | checking | done | 本地修复与证据收口；两位独立 review correct／无 findings，Release Readiness Review 对本次局部变更 ready；不等同 PR 审查、合并、部署或发布 | c4480deaf2b260c065bcefea3012655a8d1e4753 五个 blob 与被测哈希一致；corrected red 5／4 failures／17.110s，green 5 passed／16.824s，真实进程 smoke 4.115s；golden 61 passed／0.322s；runtime 378／368 passed／10 skipped／122.100s；ruff check／format exit 0，diff／YAML／contracts 空 diff 通过；8 对报告保留；主会话提交前 37／85，runtime reviewer 最终 33／37，coverage reviewer 最终 29／37，ping 1／0；第三 commit 仅保存本 task |
