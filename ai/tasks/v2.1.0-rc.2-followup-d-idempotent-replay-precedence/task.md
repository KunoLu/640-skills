---
schema_version: 1
id: v2.1.0-rc.2-followup-d-idempotent-replay-precedence
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict、mode_source user；主会话唯一 writer／验证 controller。原批次恰好三个本地 commit；本修正批次仅改 Follow-up D 与磁盘上限两个 task.md，恰好追加一个本地 commit，仅显式 git add；不 push／PR／评论／merge／rebase／amend，不改其他 worktree 或全局配置，不暂存禁止路径或 reports。
status: done
branch: contract/v2.1.0-rc.2-followup-d-idempotent-replay-precedence
created_at: '2026-10-22T20:29:27+08:00'
updated_at: '2026-10-22T20:48:29+08:00'
completed_at: '2026-10-22T20:44:29+08:00'
---

# rc.2 后续项 D：createExport 幂等重放优先级契约

## 范围与验收

用户实际规则原文为「只有新请求才依次检查 503、404、410」；Lord 于 2026-10-22 约 20:24 +08:00 较早转述为「幂等重放放在渲染器检查之前」。用户规则没有点名 507 或 422，不视为对这两个优先级的批准。原批次入口 HEAD／origin/main 为 `82d42a20a6dc757356173535148fdcc7c0b9024d`（#158）；工作根 `/workspace/640-skills-fud`。原批次仅五条授权路径、三个本地提交：plan／磁盘上限 task closeout；OpenAPI／golden tests；本记录。本修正批次入口 `0fbdd01`，仅授权两个 task.md、追加一个本地提交，不改 task index、plan、OpenAPI、tests、PRD、ADR、runtime 或安装文档。未完整调用 grill-with-docs：本批是用户明确指定的记录纠偏；未决定值保持待用户确认，不补作领域决定。

原批次只定义 createExport 的契约，不实现 HTTP／Store 顺序调整。沿用 OpenApiDraftTests／Draft202012Validator、内联 golden body 与既有 vendor extension 风格，无新依赖。访问检查 401／403 与识别重放所需的 400 校验（JSON content type、必需 Idempotency-Key、合法 CreateExportRequest）仍在前；幂等记录保留期间，同 key、同 canonical request body 返回原接受结果，不是新建。当前契约只对错误码相对重放分类，没有重定义非重放准入检查的相对顺序；用户原文的「依次」503→404→410 是否需要显式固定，列入下方待确认项。不改同 key 不同 payload 行为，不新增 409。

以下保留原批次场景作为现有契约／测试的记录；其中 replay-before-507 与 replay-before-422 是**待用户确认的提议值（未决定）**，不是用户已批准的验收值。

```gherkin
Scenario: renderer 移除后的重放仍返回原接受结果
  Given 同 key 同 canonical request body 已受理且幂等记录仍保留
  And JPEG 或 PDF renderer 随后被移除
  When 客户端通过访问检查与请求校验后重放 createExport
  Then 返回原 HTTP 202 ExportAccepted 而非 503
  And data.export_id 与原接受结果相同，不创建新作业、ID 或文件

Scenario: 快照过期或消失后的重放仍返回原接受结果
  Given 已受理请求的幂等记录仍保留且其快照已过期或不存在
  When 客户端以相同 key 和 canonical request body 重放 createExport
  Then 返回原 202 而非 404 或 410
  And 原导出自身过期后 getExport 仍可返回 410

Scenario: 配额超限时的重放不重新准入
  Given 已受理请求的幂等记录仍保留且共享磁盘占用已超过配额
  When 客户端以相同 key 和 canonical request body 重放 createExport
  Then 返回原 202 而非 507 DISK_QUOTA_EXCEEDED
  And 不创建新文件

Scenario: JPEG 降级重放保留原告警且不重复预检
  Given 原接受响应包含 EXPORT_SCALE_DOWNGRADED:1x 且幂等记录仍保留
  When 客户端以相同 key 和 canonical request body 重放 createExport
  Then 返回原 data.export_id 与原 meta.warnings
  And 不重新运行 JPEG preflight，不因后来尺寸限制变化返回 422

Scenario: 非重放请求仍执行原准入检查
  Given 有效 createExport 请求不匹配保留中的幂等记录
  When renderer、快照、配额或 JPEG 尺寸检查拒绝新建
  Then 契约仍声明 503、404、410、507 或 422 对应的拒绝
  And 本次不规定这些准入检查之间的相对顺序
```

上述场景现在只由 golden tests 验证优先级分类、响应集合与原 ID／告警示例的 schema；无新作业／文件、无重复预检、状态变化后的真实重放及告警保留均由 R2.2 实现并以 HTTP／Store 场景验证。本次不冒充运行时行为证明。

## 待定项／Review flags

### Proposed values for user decision

1. **extension 名称与形状**：采用用户建议的 `x-sbtd-idempotent-replay`，`response: "202"`、`evaluated_after: ["400", "401", "403"]`、`precedes: ["404", "410", "422", "503", "507"]`。这些数组是相对重放的分类，不是各自内部排序；复用既有 x-sbtd-* 风格，无新抽象。
2. **重放优先于 507 `DISK_QUOTA_EXCEEDED`：待用户确认的提议值（未决定）**。Reviewy、Lord、CodeX、Researchy 房间共识（2026-10-22 约 20:36 +08:00 转达）采纳的新契约提议值：重放不创建作业／文件、不使用新增配额，所以提议置于 507 之前。#158 明确未重定义重放／已有 ID 复用的优先级；不是沿袭 #158 的既定顺序，也不是用户已决定。
3. **createExport-only**：不改变 createReportSnapshot 已有 ID 复用相对 507 的未定义状态；不扩展其他操作。
4. **同 key 不同 payload**：PRD §9.6 写 409，runtime 的 `_existing_idempotent` 抛 ValueError，经 handler 映射 400；createExport 未声明 409。本次不改变该行为或补码，保留差异供独立决定。
5. **重放优先于 422：待用户确认的提议值（未决定）**。用户原文只点名 503／404／410；保留原接受结果、不重复 JPEG preflight 的 422 放置是提议，不由原文自动推导为批准。
6. **新请求 503→404→410 的相互顺序：待用户确认的提议值（未决定）**。用户原文明确说「依次」；当前 extension 数组只是各码相对重放的分类，并未固定非重放检查之间的顺序。当前 runtime 已先检查 503，再进入 Store 的 404／410 检查；是否在契约中显式固定此顺序，须用户决定，本批不修改契约或 runtime。

### 决定与依据边界

- **用户已决定**：仅原文「只有新请求才依次检查 503、404、410」；较早 Lord 转述不是扩大决定范围的依据。
- **房间共识提议，不是用户决定**：replay-before-507 与 replay-before-422 均为**待用户确认的提议值（未决定）**。原批次 OpenAPI／golden tests 已写入这两个放置值，不使其自动成为已批准决定；本批只纠正记录，留待用户确认。
- 已读 [PRD v0.2 §9.6](../../../docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md#section-9)（`docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md:845`）：「同 key 同 payload 返回同结果；同 key 不同 payload 返回 409。导出重试不得产生多个无法追踪的文件。」
- 已读 PRD §10.4（`docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md:908`）：清理后仍超限则「拒绝新建」，配额拒绝针对新建。
- 已读 [ADR 0003 §4 step 4](../../../docs/adr/0003-v2.1.0-rc.2-r2.0c-snapshot-persistence.md#4-清理授权边界)（`docs/adr/0003-v2.1.0-rc.2-r2.0c-snapshot-persistence.md:52`）：「仅通过上述准入后才开始本次新建／接受新导出作业」；「已有 ID 复用／幂等回放不是新建，不在此重定义其契约优先级」。
- **证据限度**：这些仅间接支持「重放不是新建、准入针对新建」。PRD 与 ADR 均未明确排列 replay 与 507 的先后；未找到显式依据。不能把房间提议写成 PRD／ADR 已决定的优先级。

已读 R2.1b task「后续项 D」（Reviewy 2026-10-22，PR #156 引用）、PRD §9.6、ADR 0003 §4 step 4，以及当前四个 response 描述。`serve.py:create_export` 在 Store 调用前检查 renderer，因此仍会先返回 503；`ExportStore.create` 内先查幂等再 pin／preflight，`_existing_idempotent` 可返回已清扫导出的旧 ID。`sbtd-runtime/docs/install-and-use.md:189` 明确写「JPEG／PDF createExport 的依赖检查先于幂等重放」，并说明已清理告警 metadata 不额外保留；这与新契约的优先级及原告警保留要求不一致。已知 contract-ahead-of-implementation drift 归 R2.2，文档由 R2.2／F 对齐，本次按授权不编辑。

## Book Gate Plan

| Gate | 客观触发／阶段 | 状态 |
|---|---|---|
| book-ddia-data-design | wire contract／跨请求幂等回放，稳定设计前 | confirmed；已加载并输出独立 DDIA Data Design Review。OpenAPI 为契约事实源、ExportStore 为记录所有者；无持久格式变更或迁移，重放不重新准入；实现漂移归 R2.2。 |
| book-ddd-distilled-modeling | 完整 grill／领域歧义 | not-needed；未完整 grill，沿用既有领域与用户明确规则。 |
| book-legacy-change-safety | 既有运行行为修改 | not-needed；不修改 runtime，已有 validator seam。 |
| book-refactoring-pass | 生产代码修改 | not-needed；声明式契约与测试，无生产代码编辑或重构。 |
| book-release-readiness | runtime／部署／发布变化 | not-needed；契约领先实现，不宣称发布就绪。 |
| TDD／gherkin-bdd／ponytail | 消费者契约／before-dev、check | confirmed；基线红灯、最终 golden 绿灯、独立 schema 消费者 smoke；中文场景／英文关键词，无新依赖或抽象。Ponytail Review：无需删减，两个测试分别保护分类完备性与接受响应兼容性。 |
| 独立 review／可读性 | 公共契约／check | correct；ReplayContractReview、ReplayEvidenceReview 均无 findings；两位只读，不运行测试／lint／build／formatter；主会话唯一 writer／controller。 |
| project-validation | 用户指定两条 suite／check | 完成指定 golden／runtime suite、消费者 smoke 与格式检查；不运行根 native CI。既有 import I001 不重跑确认、不修范围外 import。 |

本修正批次 Gate 适用性：仅纠正两份任务记录，不改变契约、生产代码、schema 或运行行为；DDD／DDIA／legacy／refactoring／release gates、TDD 与运行时 BDD not-needed，不重用原批次通过状态冒充本批执行。纠偏依据是本次用户转达的四方共识；以 Markdown／frontmatter 文档消费者诊断、历史事件保留核对及 Git 范围／空白检查验证，不生成报告或改写既有测试证据。

## 验证证据

在授权 worktree 根、Linux／Python 3.13.5，原生命令附加 `PYTHONDONTWRITEBYTECODE=1 RUFF_NO_CACHE=true PYTHONPATH=sbtd-runtime:sbtd-runtime/tests`。七对本地报告位于本任务 ignored `reports/`，每个 stem 为 raw `.json` + 九节中文 `.md`，保留完整命令、stdout／stderr、退出码、时间、HEAD、环境与被测 SHA-256。`rtk: skipped-for-report`；`Evidence Source: developer-local`、`Source Revision: dirty`、`Environment Alignment: unverified`、`Evidence Publication: local-only`。当时 HEAD `8625ed6` 不是新 PR-head CI 证据。

| 命令 | 实际结果 | 报告 stem |
|---|---|---|
| `python -B -c <baseline YAML red script>` | exit 1（预期）；2 tests，0.049s，1 failure／1 error；缺少 replay extension 导致 None 不符与 KeyError | baseline-red |
| `python -B -m unittest sbtd-runtime/tests/test_golden_contracts.py -v` | 首轮 exit 0；61 passed，0.330s | golden-green |
| `ruff format --check sbtd-runtime/tests/test_golden_contracts.py` | 首轮 exit 1；新增 response 索引表达式需换行；仅换行修正后 exit 0，1 file already formatted | format-check／format-final |
| `python -B -c <contract consumer smoke script>` | exit 0；原 ID／告警 JSON round-trip 与新 request_id 合法，非法 warning／缺 ID 被拒绝；撤去本次契约改动后 YAML 解析结构等于基线 | contract-smoke |
| `python -B -m unittest sbtd-runtime/tests/test_golden_contracts.py -v` | 最终 exit 0；61 passed，0.319s | golden-final |
| `python -B -m unittest discover -s sbtd-runtime/tests` | 最终 exit 0；374 tests，364 passed／10 skipped，112.502s | runtime-full |

基线从 `git show origin/main:sbtd-runtime/contracts/openapi.yaml` 读取，并断言工作树 YAML 字节完全相同；TemporaryDirectory 内写入基线，进程内替换测试模块 OPENAPI，仅运行两个新增测试，不 stash／reset 或改写工作树契约。完整脚本留在 raw.command，临时目录已自动清理。

新增分类测试精确断言 extension 三键及其值，`precedes` 是声明响应的子集，`precedes ∪ evaluated_after ∪ {202}` 精确等于全部 createExport 响应码集合；未来新增码不能漏分类。第二测试从 extension 解析 response，断言 ExportAccepted 引用，再用 Draft202012Validator 验证原 export_id 与原 JPEG 降级 warning 的内联 golden body。不增加描述措辞断言；schema 本身不能证明历史值相等或未重复预检，后者是 R2.2 行为验收。

消费者 smoke 实际解析 extension 与 response schema，经 JSON 编解码校验原接受字段；request_id 可为本次请求值，不误冻结整个 envelope。去掉新 extension／operation description，恢复三个 response 描述后，YAML 结构与基线完全相等：响应集合、所有 schema、ExportImageSizeLimit、snapshot 操作及其他操作均未变。没有落盘执行脚手架。

手写测试可读性复核：沿用 unittest 与已有 validator，无 helper／依赖；测试名对应契约边界，中文注释明确响应 schema 不等于运行行为。格式修正只换行，最终两 suite 覆盖修正后的内容。`ruff check` 未运行：前置 task 已记录同文件未改 import 的 I001，不重复确认已知问题；不宣称 lint 全绿。runtime 原生输出未列逐例 skip 名称，不猜原因；重叠 suite 不累计通过数。

`BDD: traceable`（本 task 五场景，中文／英文关键词）；`Cross-repo context: contract-only`；`API Contract: verified`（schema）；`E2E Mode: contract-backed`；`Mock Strategy: none`（新增用例）。`Final Test Report`／`Run Summary MD: generated`；`Targeted Rerun: passed`；`Final Full Rerun: passed` 仅指指定 runtime suite，不是根 native CI。根 CI 按用户要求不运行；无新的 live HTTP 重放、renderer 移除、quota 实现、浏览器、跨平台或发布验证；既有 suite 通过不消除已知 runtime 漂移。无独立完整 OAS linter 证明，只使用既有 PyYAML／Draft202012Validator。

| 最终被测文件 | SHA-256 |
|---|---|
| sbtd-runtime/contracts/openapi.yaml | a7b7e24ae3ecc5dc83367f499783646fdbdafa50dc486f969a00c41a3da23709 |
| sbtd-runtime/tests/test_golden_contracts.py | 0f83217feb49e92b3cc470e00b0ef7167461122f3b610d58bba046050105cebf |

首 commit 前已执行 MarkdownIt／PyYAML 文档消费者 smoke：frontmatter 可解析、完成时间合法且 +08:00；磁盘上限 task 原状态事件逐字不变，只追加一条 closeout，两 reviewer 行逐字不变。#158 mergedAt／主会话最终 39／73 采用用户核实事实；实际 `git show -s --format=%cI 82d42a2` 为 `2026-10-22T20:23:39+08:00`。

### 记录诊断与独立审查

本 task 与磁盘上限 task 的 frontmatter／事件已用安装 Skill 的 `task-data.schema.json`、Draft202012Validator／FormatChecker 验证，+08:00 日历时间可解析，MarkdownIt 可消费表格；七对报告已核对九节顺序、无模板占位符、raw 内容与实际命令结果一致、同 stem 配对且全部 ignored。这是文档诊断，不是 TaskStore 生命周期证明。

- ReplayContractReview：correct，confidence 0.9，无 findings；核对 PRD／ADR、访问与校验前置、保留期、原接受语义、503／507 排除、snapshot 范围、非重放不排序、409 排除、runtime／安装文档漂移及数据所有权边界。
- ReplayEvidenceReview：correct，confidence 0.9，无 findings；核对 #158／92d6a35 closeout 风格、两类时间、最终 39／73 与旧快照／reviewer 行保留、单条事件；核对分类测试、golden schema、基线字节身份、全部七对 raw／中文报告、最终哈希与计数。
- 两位均为 omp 原生只读 reviewer，不冒充外部 Reviewy；无有效 finding、无需修正回路。主会话负责最终记录与提交。Ponytail／Code Readability Review：无需重构或新增抽象；无新增需要单独身份记录的长期 lesson，不写 developer／lesson。

## 提交与恢复边界

入口工作树干净；五路径逐级确认无 symlink／路径逃逸，新 task 不存在且不受 ignore；reports 命中 `.gitignore:4:/ai/tasks/**/reports`。沿用已读 rc.2 task 的 TaskStore catalog/frontmatter 限制，不重跑已知失败；helper active／index 写入超授权。使用 edit/write 保存用户指定共享记录，不声称 TaskStore helper 生命周期或自动恢复成功，不写 active、ignore、身份或全局配置。磁盘上限 task 的 branch 保留历史绑定，closeout 不重绑定。

撤回仅涉及契约／文档提交，无数据迁移，不删除用户数据；消费者采用前须协调契约。local done 不等同 push、PR、合并、R2.2 实现、部署或发布。报告、`.omp-r12b-addendum.txt`、`ai/tasks/codex-verify/` 均不暂存。

1. `8625ed66235f09807e04c97a8dac7e677a58a3af` — `docs(plan): backfill rc.2 item 4 error contract (#158 / 82d42a2) and close task record`，仅 plan 与磁盘上限 task。
2. `ffd6baac3822c2b7324d8082af1c255b8c1de237` — `contract(openapi): idempotent replay precedes createExport admission checks (rc.2 follow-up D)`，仅 OpenAPI 与 golden tests。已提交 blob 的 SHA-256 与最终被测内容相等；这是内容身份核对，不冒称提交后的新 CI。
3. `docs(task): record rc.2 follow-up D idempotent replay precedence contract task`，仅本记录，自身 SHA 由最终 stdout 给出，避免自引用。

前两次均显式 `git add <paths>`，`git diff --check`／`git diff --cached --check` 退出 0；第三次同样只暂存本 task。最终 log／stat／status 与五路径集合由提交后回执给出，不额外修改 plan 的 in_progress（本地完成不等于契约 PR 已合并）。

本修正批次仅追加 `docs(task): mark follow-up D 507/422 placement as proposed; finalize #158 reviewer counts`；前述三个提交不 amend／rebase。两个 task 的历史 branch／completed_at 保持不变；本 task 仅更新 updated_at 并追加一条记录纠偏事件，#158 只修正用户明确授权的 closeout 行及最终计数说明。沿用 edit 保存共享记录的既有限制，不调用 TaskStore 或宣称生命周期／自动恢复成功。

## 模型使用

| agent/session | provider/model | thinkingLevel (from thinking_level_change) | assistant messages / toolCall blocks | purpose | resolvedModelIsFallback | title-generation count | job-widget entries (unknown when not recorded) |
|---|---|---|---|---|---|---|---|
| 主会话／01a16395-ab3a-73c1-9aa1-a67ba48277bd | openai-codex/gpt-6-astra | high | 33 / 65（提交前 snapshot） | 唯一 writer、验证 controller | false | 未记录 / unknown | 未记录 / unknown |
| ReplayContractReview／ReplayContractReview.jsonl | kimi-code/k3 | max | 30 / 47（提交前 snapshot） | 只读契约语义／runtime 漂移复核 | false | 未记录 / unknown | 未记录 / unknown |
| ReplayEvidenceReview／ReplayEvidenceReview.jsonl | kimi-code/k3 | max | 30 / 42（提交前 snapshot） | 只读 golden／closeout／验证证据复核 | false | 未记录 / unknown | 未记录 / unknown |
| 本修正批次主会话／01a163a7-0d9a-753c-9f6f-d41cc0ff342f | openai-codex/gpt-6-astra | high | 4 / 15（本修正批次提交前 snapshot） | 两份 task 记录纠偏，唯一 writer／验证 controller | false | 未记录 / unknown | 未记录 / unknown |

统计时间 `2026-10-22T20:44:29+08:00`；只读 Python `json.loads` 解析 `~/.omp/agent/sessions/--workspace-640-skills-fud--/2026-10-22T12-28-35-514Z_01a16395-ab3a-73c1-9aa1-a67ba48277bd.jsonl` 第 1–170 行，同 stem 目录的 ReplayContractReview 第 1–134 行、ReplayEvidenceReview 第 1–124 行。统计 `type=message`／`role=assistant` 及其 `type=toolCall` blocks；均是第三次提交前快照，不含后续记录、提交和最终输出，不宣称主会话最终总数。

模型来自 message／model_change，thinking 明确来自 `thinking_level_change`，不是按 effort 推断；resolvedModelIsFallback 均为 false，无 fallback，未改模型配置。每个 JSONL 有一个 title 条目，但不等于 title-generation request 次数，故 unknown；未记录 `type=model_usage`／同名 customType，不把缺记录写成 job-widget 0。

本修正批次统计时间 `2026-10-22T20:48:29+08:00`；只读 Python `json.loads` 解析 `~/.omp/agent/sessions/--workspace-640-skills-fud--/2026-10-22T12-47-34-810Z_01a163a7-0d9a-753c-9f6f-d41cc0ff342f.jsonl` 第 1–38 行，按相同口径得 4 assistant messages／15 toolCall blocks。会话 ID／cwd／本次用户请求匹配；model_change 为 openai-codex/gpt-6-astra、resolvedModelIsFallback=false，thinking_level_change 为 high。此为提交前快照，不含后续编辑、验证、提交及最终输出，不是最终计数；title-generation／job-widget 次数未记录，保持 unknown。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-22T20:29:27+08:00 | planned | in-progress | 用户 strict、三提交与五路径授权；保存模式与验收场景 | HEAD／origin/main 82d42a20a6dc757356173535148fdcc7c0b9024d；路径安全；PRD／ADR／rc.2 先例；DDIA confirmed |
| 2026-10-22T20:38:15+08:00 | in-progress | checking | 基线红灯、最终两 suite 与消费者 smoke 通过，进入独立审查与记录收口 | 8625ed6；golden 61 passed／0.319s；runtime 374／10 skipped／112.502s；格式修正后通过；最终内容哈希一致 |
| 2026-10-22T20:44:29+08:00 | checking | done | 本地契约交付收口；前两个 commit 已完成，第三个只保存本记录；两位独立 review 无 findings，不等同提审／合并／R2.2 实现或发布 | ffd6baac3822c2b7324d8082af1c255b8c1de237；golden 61 passed／0.319s；runtime 374／10 skipped／112.502s；schema smoke／格式通过；被测内容与提交 blob 一致；主会话提交前 snapshot 33／65 |
| 2026-10-22T20:48:29+08:00 | done | done | 记录纠偏：按用户转达的 Reviewy／Lord／CodeX／Researchy 房间共识，区分用户原规则与未决定的 507／422 提议，并修正 #158 reviewer 最终计数；仅追加一个本地 commit，不改变原完成时间或旧事件 | 入口 0fbdd01；用户原文「只有新请求才依次检查 503、404、410」；PRD :845／:908、ADR 0003 :52 仅间接支持，无 replay-vs-507 显式排序依据；507／422 均待用户确认；非重放相互顺序列为 review flag；#158 最终主会话 39／73、QuotaContractReview 18／22、QuotaEvidenceReview 21／34 采用 operator 已核实事实；本批主会话提交前 snapshot 4／15 |
