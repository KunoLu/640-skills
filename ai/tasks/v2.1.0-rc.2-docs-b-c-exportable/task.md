---
schema_version: 1
id: v2.1.0-rc.2-docs-b-c-exportable
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：本轮采用 strict；主会话为三个授权文件的唯一 writer、git 提交者与验证 controller；不启动子代理、不使用 advisor；只新增本地提交，push 与开 PR 由编排方在 omp 之外执行。
status: done
branch: docs/v2.1.0-rc.2-docs-b-c-exportable
created_at: '2026-10-25T07:54:09+08:00'
updated_at: '2026-10-25T10:42:57+08:00'
completed_at: '2026-10-25T10:42:57+08:00'
---

# rc.2：Docs 后续项 B／C 导出事件明细屏蔽口径 strict 任务

## 决定

- 用户 2026-10-25 07:50 群内确认（文档按现有代码写，run/step 等派生行随依据事件屏蔽），Lord 记录：task 行始终导出；聚合值（指标）按全部事件计算，从明细中屏蔽的事件仍计入聚合值；run、step 及其他派生行跟随其依据事件，依据事件被屏蔽时一并不导出；`privacy.exportable` 为 false 或 `privacy.classification` 不是 `local-metadata` 的事件不进入导出明细，缺省分别视为 true 与 `local-metadata`。元数据行保留，行数计数按实际导出行重算；有屏蔽时给出 `WITHHELD_NON_EXPORTABLE:<n>` 警告；HTML／JPEG／PDF／CSV 口径一致。
- 编排方整理：文档按现有实现表述，不改变过滤、聚合或格式渲染行为；本轮事件时间均通过 `TZ=Asia/Shanghai date -Iseconds` 获取。
- 用户 2026-10-25 07:50 群内确认（方案一），Lord 记录：PR 2 在 `install-and-use.md` 写明同一导出事件明细屏蔽口径，与 PRD §10.3 一致。

## 范围与边界

- 本任务为一个任务、两个 PR；本 PR 为 PR 1（后续项 C，PRD）；PR 2（后续项 B，`sbtd-runtime/docs/install-and-use.md` :154 说明）在 C 合入后进行，本轮不修改该文件。
- 本 PR 只改 `docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md`（§10.3 末尾插入小标题及一个正文段）、`ai/tasks/v2.1.0-rc.2-plan/plan.md`（第 24 行 Docs 行末列）和本 `ai/tasks/v2.1.0-rc.2-docs-b-c-exportable/task.md`。
- 排除 5.5 契约措辞、回填项、D9、E、PRD 原第 942 行及 §22 修订记录；不改任何代码、openapi／spec／info 文件。plan.md 第 90、118 行仍保留较早的派生行措辞，本轮授权只改第 24 行末列；本 PRD 按本节最新决定与实现写明 run／step 跟随依据事件屏蔽，不将旧措辞视为当前代码行为。
- Commit 1 为 PRD 与 plan.md；后续提交仅为本 task 的建立、验证记录与 checking 更新；不 amend、不 force、不 push、不执行 gh 操作、不修改 omp 全局配置。push 与开 PR 由编排方在 omp 之外执行。
- 本 task 手写，不调用 TaskStore 写入，不写 active／index／handoff／ignore／身份，不承诺自动恢复。结束状态为 checking，`completed_at: null`；本地文档交付不等于独立审查、合入、实现或发布完成。
- 未完整调用 grill-with-docs：决定、代码依据、编辑范围与验收条件均已明确，无需重复澄清。未运行独立审查；本会话未使用子代理，未使用 advisor。
- PR 2 只改 `sbtd-runtime/docs/install-and-use.md` :154 一个分句与本 task；PRD、5.5 契约、plan.md（含 :24、:90、:118；:90／:118 更正按 Lord 2026-10-25 08:05 裁定推迟到下一个回填 PR）、代码及 openapi／spec／info 文件不在本 PR。
- PR 2 沿用 strict；本轮明确授权在 `docs/v2.1.0-rc.2-docs-b-install-and-use` 分支执行，frontmatter 的 `branch` 保留 PR 1 历史值，不冒充已执行 TaskStore 重绑定或自动恢复。除 `status`、`updated_at` 外，既有字段、正文、模型记录与三条状态事件均保留；不写 active／index／handoff／ignore。
- PR 2 未完整调用 grill-with-docs：范围、实现依据与验收条件明确；上表 Book Gate Plan 的适用性沿用，仅 project-validation 适用，无生产代码、运行时、部署或领域设计变化。主会话为唯一 writer、提交者与验证 controller，不使用子代理或 advisor；本地 checking 不代表独立审查、合入或发布完成。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮适用性 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，文档前 | not-needed；未完整 grill，只落实明确决定及现有实现 |
| book-ddia-data-design | schema、迁移或持久化机制设计前 | not-needed；不改 schema、数据结构或持久化机制 |
| book-legacy-change-safety | 既有运行时行为修改前 | not-needed；仅补充文档，不改运行时行为 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；无生产代码编辑或重构 |
| book-release-readiness | 运行时或部署变化，验证后 | not-needed；无运行时、部署或发布变化，不宣称发布就绪 |
| project-validation | 文档范围、新任务契约与相关单元测试核验 | 适用；执行原生 diff、增量禁词检查、TaskDocument.parse 只读解析与指定 unittest，不调用 TaskStore 写入 |

## 验证与剩余边界

- 入口命令 `pwd`、`git status --porcelain`、`git branch --show-current`、`git rev-parse --show-toplevel`、`git rev-parse --short origin/main`：项目根与分支匹配，初始工作树干净，origin/main 为 `7cbb929`。Python pathlib 只读检查确认三个授权路径无 symlink 且位于项目内，新 task 不存在；`git check-ignore -- <三个授权路径>` 返回 1、无命中，`git ls-files -- <三个授权路径>` 仅列出两个既有文件。
- 代码复核：`export_render.py:268–303` 与 `306–327` 确认屏蔽条件、缺省值、事件关联与 task 保留；`privacy` 缺失或非对象时不进入屏蔽集合。`report_snapshot.py:122` 及各派生行的 `_base_fields` 调用确认 event_id 来源；`csv_export.py:192–217` 与 `export_render.py:924` 确认聚合查询使用完整 dataset。`csv_export.py:152–189,220–253` 确认元数据行单独保留；`export_render.py:910–919` 重算行数并追加警告；`browser_renderer.py:857–863` 确认 JPEG／PDF 消费同一过滤 HTML。上述关键行号与复核基线一致；警告中的 n 是屏蔽的明细行数，不是去重事件数。
- Commit 1 为 `584b121`。提交前 Python 逐行比较 origin/main 与工作树：PRD 仅在原第 893 行后插入 4 行，原第 942 行逐字保留、现位于第 946 行；plan.md 仅第 24 行末列替换。`git diff --check` 干净，`git diff --stat` 为两个文件、5 insertions／1 deletion；grep 检查 PRD 新增行、plan 改动行及新 task 全文，禁词与主目录路径命中 0。
- `python -B -m unittest tests.test_sbtd_task_schema tests.test_workflow_contracts tests.test_sbtd_task_state`：Ran 111 tests in 35.941s，OK，退出码 0；执行时文档已修改、task 为 in-progress，运行时代码与基线一致。通过 Python 禁用字节码写入并从仓库 `sbtd-workflow-onboard/scripts` 导入 `sbtd_task_document.TaskDocument`，`TaskDocument.parse` 只读解析通过：strict／in-progress、分支匹配、`completed_at=null`、非旧格式事件；未调用 TaskStore。
- Commit 2 为 `dc05cf5`。该提交后运行 `git diff --stat origin/main..HEAD`：仅三个授权文件，68 insertions／1 deletion；`git diff origin/main..HEAD -- docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md` 仅新增 4 行；`git diff --check origin/main..HEAD` 无输出、退出码 0；`git status --porcelain` 为空。本条记录的是 checking 更新提交前的已提交快照，不冒充最终提交后的统计。
- checking 更新后，仓库 `sbtd_task_document.TaskDocument.parse` 只读解析通过：status=checking、workflow_mode=strict、completed_at=null，三条状态事件有效且末条时间与 updated_at 一致；对 PRD 新增行、plan 改动行与 task 全文再次 grep，禁词与主目录路径命中 0。以上均为 developer-local／local-only 证据，不代表 CI、独立审查或发布结论。
- 本轮仅记录本地验证，不生成额外报告文件，不冒充 CI 或四格式端到端运行证据。BDD：skipped（仅描述既有行为，无新增运行时行为或场景）；API Contract／Cross-repo context：not-needed；Mock Strategy：none；rtk：not-needed（精确原生 git 与指定 Python 命令）。构建、代码 lint、浏览器／移动端及完整 E2E：skipped，原因是无代码或 UI 变更；独立审查、合入与 PR 2 不属于本轮本地交付。
- PR 2 入口核验：`pwd`、`git status --porcelain`、`git branch --show-current`、`git rev-parse HEAD origin/main` 确认 worktree 与本轮授权分支一致，初始工作树干净，HEAD／origin/main 均为 `8a144a2b6507f553e5ed6d9bd1e897b274cfc966`。Python pathlib 只读核对两个目标及其父路径无 symlink、文件位于项目内；`git ls-files --stage -- <两个目标>` 确认均已跟踪，`git check-ignore --no-index -- <两个目标>` 无命中、退出码 1。
- PR 2 写前复核：`export_render.py:268–327,905–925`、`csv_export.py:152–253`、`report_snapshot.py:122` 及 `_base_fields` 调用、`browser_renderer.py:857–863` 与 main 的 PRD §10.3 口径一致。task 行始终导出；聚合使用完整 dataset，含被屏蔽事件；run、step 等派生行按 `fields.event_id` 随依据事件屏蔽；privacy 缺失或非对象不据此屏蔽，两个属性的缺省分别为 true 与 local-metadata。元数据保留，有屏蔽时重算实际导出行数并追加警告，n 为屏蔽明细行数；HTML／CSV 共用过滤结果，JPEG／PDF 消费同一已过滤 HTML。未发现需要偏离 PRD 的实现差异。
- PR 2 状态转换依据：仓库 `task-data.schema.json` 的 stateEvent 允许 checking → in-progress，`sbtd_task_state.py:660–662` 同样允许；`sbtd_task_document.py` 通过该 schema 校验事件。所有新增事件使用真实 `TZ=Asia/Shanghai date -Iseconds` 时间，晚于既有末条；本轮不调用 TaskStore 写入。
- PR 2 验证边界：仅本地文档与任务记录验证，不生成额外报告文件，不声称 CI 或四格式端到端通过。BDD、构建、代码 lint、浏览器／移动端与完整 E2E：skipped，无代码、UI 或运行时行为变化；API Contract／Cross-repo context：not-needed；Mock Strategy：none；rtk：not-needed，使用精确原生 git 与指定 Python 命令。Evidence Source：developer-local；Evidence Publication：local-only。
- PR 2 Commit 1 为 `87e7c36`，仅含 `install-and-use.md` 的 1 insertion／1 deletion。提交前 Python 按字节比较确认文件恰为目标分句替换、其他字节与行数不变；本 task 与 origin/main 比较，既有正文及三条事件逐字节保留，仅允许的 frontmatter 值变化，其余均为追加。`git diff --check` 干净；以 `PYTHONDONTWRITEBYTECODE=1` 从仓库 scripts 导入 `TaskDocument.parse`，只读解析通过：strict／in-progress、非旧格式、completed_at=null，四条事件顺序与状态链有效，末条时间等于 updated_at。
- PR 2 指定命令 `python -B -m unittest tests.test_sbtd_task_schema tests.test_workflow_contracts tests.test_sbtd_task_state`：Ran 111 tests in 35.185s，OK，退出码 0；运行时文档已修改、task 为 in-progress，未修改测试或代码。
- PR 2 Commit 2 为 `b33c615`。该提交后 `git diff --stat origin/main..HEAD` 仅两个授权文件，15 insertions／3 deletions；`git diff --check origin/main..HEAD` 干净，`git status --porcelain` 为空。对 task diff 运行 `grep '^-[^-]'`，仅有 frontmatter 的 status、updated_at 两行；install-and-use 的 numstat 为 1／1。对完整 diff 的新增行运行 grep，禁词及主目录路径命中 0。本条为 checking 更新提交前的已提交快照；最终 checking 与基线 status 相同，最终 task 删除行应只剩 updated_at，不要求制造 status 差异。
- PR 2 checking 更新后，以 `PYTHONDONTWRITEBYTECODE=1` 从 `sbtd-workflow-onboard/scripts` 导入 `sbtd_task_document.TaskDocument`，`TaskDocument.parse` 只读解析通过：status=checking、非旧格式、completed_at=null，五条事件按时间递增且状态链连续，updated_at 等于末条事件时间。Python 再次核对历史逐字节保留；`git diff --check origin/main` 干净，增量 grep 禁词与主目录路径命中 0；task 删除行仅 updated_at，install-and-use 仍仅 1 行替换。此为最终记录提交前的本地证据，不冒充最终提交 SHA 的 CI 证明。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | 产出 | 会话文件 |
|---|---|---|---|---|---|
| 1 | ping（2026-10-25 07:52:21 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-24T23-52-21-195Z_01a17054-63cb-726d-9356-d17fda768b56.jsonl` |
| 2 | main（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告 | PRD §10.3 屏蔽口径、plan.md Docs 任务链接与本 strict 记录；本地提交由本会话执行 | `2026-10-24T23-53-33-824Z_01a17055-7f80-7022-92f3-a1e5d81fa3ac.jsonl` |
| 3 | PR 2 ping（2026-10-25 08:22:15 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-25T00-22-15-611Z_01a1706f-c53b-7061-89a4-72f78cf9982a.jsonl` |
| 4 | PR 2 main（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告 | install-and-use.md :154 屏蔽范围说明、本 task 的 PR 2 追加记录与本地验证提交 | `2026-10-25T00-22-53-874Z_01a17070-5ab2-713e-95e0-b21c885484c6.jsonl` |

每个 omp 会话一行；本会话未使用子代理。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-25T07:54:09+08:00 | planned | in-progress | 编排方整理，主会话记录：建立手写 strict 任务，开始 PR 1 文档交付。 | 基线 `7cbb929`；根目录、分支、初始干净工作树、路径与 ignore 检查通过；未调用 TaskStore 写入；at 为真实记录时间。 |
| 2026-10-25T07:55:51+08:00 | in-progress | in-progress | 编排方整理，主会话记录：PRD／plan 提交完成，记录本地验证结果。 | commit `584b121`；PRD 仅新增 4 行、原第 942 行不变；plan 仅第 24 行末列变化；git diff --check 干净；新增行禁词检查命中 0；指定 unittest 111 tests OK；本 task 的 TaskDocument.parse 只读解析通过。 |
| 2026-10-25T07:56:10+08:00 | in-progress | checking | 编排方整理，主会话记录：PR 1 本地文档交付完成，送审；PR 2 在 C 合入后进行。 | PRD／plan commit `584b121`，任务建立 commit `dc05cf5`；origin/main..HEAD 三文件 diff 检查通过，PRD 纯新增，git diff --check 干净，git status --porcelain 为空；指定 unittest 111 tests OK；本事件与 checking frontmatter 同步更新，completed_at 保持 null。 |
| 2026-10-25T08:23:26+08:00 | checking | in-progress | 主会话记录：PR 1（C）已以 #175 合入 `8a144a2`，开始 PR 2（B）。 | HEAD／origin/main 为 `8a144a2`，初始工作树干净；本轮在明确授权的 PR 2 分支执行，保留 PR 1 历史字段；状态 schema 允许此转换，未调用 TaskStore 写入。 |
| 2026-10-25T08:24:48+08:00 | in-progress | checking | 主会话记录：PR 2 本地交付完成，送审。 | 文档 commit `87e7c36`，任务追加 commit `b33c615`；指定 unittest 111 tests OK；两文件差异、单行替换、历史保留、diff --check 与增量禁词检查通过；本事件与 checking frontmatter 同步更新，completed_at 保持 null。 |
| 2026-10-25T10:42:57+08:00 | checking | done | 编排方整理：任务 v2.1.0-rc.2-docs-b-c-exportable 的两个 PR 均已 squash 合入，关闭。 | 编排方整理，编排方以 git／gh 只读核实：PR 1（后续项 C）#175：merge `8a144a2b6507f553e5ed6d9bd1e897b274cfc966`，git `%cI` `2026-10-25T08:20:32+08:00`，GitHub mergedAt `2026-10-25T08:20:33+08:00`（`2026-10-25T00:20:33Z`），两者相差 1 秒，分别记录；合入 head `b9f91e4`；CI run `40144860776` 13／13 success（head `b9f91e4`）；Reviewy CLEAN SHA 不可考（本 task 与 PR #175 页面均无记录）。PR 2（后续项 B）#176：merge `1b609bcfeb1bface01cec9eb5877feddf27d6121`，git `%cI` `2026-10-25T09:29:15+08:00`，GitHub mergedAt `2026-10-25T09:29:15+08:00`（`2026-10-25T01:29:15Z`），两者相等但分别记录；合入 head `3f10ee0`；Reviewy CLEAN @ `3f10ee0`（编排方整理）；CI run `40146721558` 13／13 success（head `3f10ee0`）。 |
