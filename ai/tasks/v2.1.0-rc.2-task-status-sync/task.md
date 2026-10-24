---
schema_version: 1
id: v2.1.0-rc.2-task-status-sync
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：strict；本轮 fix3b 只修改 PRD 与本 task，主会话唯一 writer／验证 controller，不使用 advisor；恰好一个提交。
status: in-progress
branch: docs/v2.1.0-rc.2-task-status-sync-prd
created_at: '2026-10-24T11:59:03+08:00'
updated_at: '2026-10-24T12:49:42+08:00'
completed_at: null
---

# 任务状态及时更新：跨 PR-a／PR-b 的 strict 任务

## 决定

- 用户 2026-10-24 11:11 群内确认（最终修订方案确认），Lord 记录。
- 用户 2026-10-24 11:14 群内确认（落地方案），Lord 记录：落地方式与生效点；新规则自 PR-a 合入起生效。群内时间均为 +08:00。
- 用户 2026-10-24 11:14 群内确认（落地方案），Lord 记录：任务跨两个 PR 的结构。
- 规则事实源：[任务状态及时更新 PRD](../../../docs/prd/sbtd-workflow-v2-task-status-sync.md)。
- 用户 2026-10-24 12:46 群内确认（旧格式事件规则修订版），Lord 记录：A／B／C 一致适用，不依赖 git 或 PR-a 合入边界；旧格式 task.md 不改写、不补造 checking，只读不写的永不写入；仅因旧格式事件解析失败时只按 frontmatter `status` 判断，运行输出提示「旧格式事件，不追溯」，不落盘、不阻塞、不算未记录改动；确需追加新事件时才在同次写入中先追加旧事件基线，记录事件行数及 sha256（不含 frontmatter），不依赖 `at` 或 git；基线内只读不校验，基线后逐行严格校验（含回填历史 done），基线 sha256 变化则追加「发现未记录的改动」交用户判断；其他解析错误照常报错。详见 [PRD「旧格式事件规则」](../../../docs/prd/sbtd-workflow-v2-task-status-sync.md#旧格式事件规则)。
- 用户 2026-10-24 12:46 群内确认（旧格式判定口径，采纳 OMP 补充），Lord 记录：「仅因旧格式」的判定标准——在没有基线事件的文件中，每一条事件行都必须能按旧格式 schema 解析；若有任何一行既不是旧格式也不是当前格式，按 PRD 该小节第 5 点作为普通解析错误报告。

## 范围与边界

- 本任务跨 PR-a（本 PR：PRD＋plan 停用说明＋任务记录）与 PR-b（按 PRD 改 `sbtd-workflow-onboard` 等并配测试）。PR-a 只记进度，保持 `in-progress`；PR-b 在 CLEAN 后按 B 方案写 `done`。
- 编排方整理：PR-a 已回填 #167、编写 PRD、追加 plan 任务表一行和本记录；commit `34a9b94` 已在 plan.md:8 原文后追加「自 PR #168 起停用，由 sbtd-workflow-v2-task-status-sync.md 替代」，PR #168 已开启。本轮 fix2 仅修正 PRD 归因格式、行号引用、trailer 理由与本记录，不改 #167 task 及其模型表。
- PR-a 的合并 SHA／时间按新规则不写入 task.md，用 `git log origin/main -- ai/tasks/v2.1.0-rc.2-task-status-sync/task.md` 查询。PR-b 首个 commit 不回填 PR-a；审查期间进入 `checking`，被打回回到 `in-progress`；CLEAN 后只追加限定的 task 收尾 commit，Reviewy 复核该 diff，CI 全绿后才合入。
- 编排方整理：仅四个授权文档；不改代码、OpenAPI、schema、技能目录；不 push、不开 PR、不改 git 或 omp 全局配置。不记录不可证明的事实，缺证据记「不可考」。
- 入口分支与基线已核对，工作区初始干净；授权路径无 symlink 且位于本 worktree 内，新文件未被 ignore。旧任务保留历史 branch，仅回填明确授权的合并事实，不重绑定。
- 未完整调用 grill-with-docs：确认方案及提交边界完整，无新增领域决策。本轮不运行 TaskStore lifecycle，不写 active／index／ignore／身份，不声明自动恢复可靠；沿用 strict 模式，本轮 fix2 恰好一个本地提交，不 push。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮结论 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，文档前 | not-needed；未完整 grill，只整理已确认方案 |
| book-ddia-data-design | 新增数据设计或迁移，设计前 | not-needed；本轮不新增设计选择，PR-b 实施前按真实触发重新评估 |
| book-legacy-change-safety | 既有运行行为变化，实施前 | not-needed；只回填记录与编写文档，不改执行路径 |
| book-refactoring-pass | 既有生产代码编辑，实施前 | not-needed；无生产代码编辑 |
| book-release-readiness | runtime／部署／发布变化，收尾 | not-needed；本轮不实施或发布，不宣称发布就绪 |
| project-validation | 文档／任务记录校验，提交前后 | 已加载；既有 schema／文档测试及真实记录解析，兼容边界单列 |

## 验证与剩余边界

- 本地命令：`python3 -B -m unittest tests.test_sbtd_task_schema tests.test_sbtd_task_document`；提交一、提交二后各 19 tests／OK。覆盖任务 schema、frontmatter 保全与状态事件表解析；不是 PR-b 新规则的行为验收。
- `git diff --check`、`git diff origin/main --stat` 与新增行禁词检查已在前两个提交后执行；范围分别为两个、三个授权文件，禁词命中 0。第三个提交及最终核验结果由本轮交付报告给出，不预写尚未发生的通过结论。
- 真实记录 smoke：#167 frontmatter schema／日期、Markdown 事件表、恰好一条追加事件、历史正文保全以及 done 事件 at 等于 completed_at 均通过。完整 `TaskDocument.parse` 对旧规则 `in-progress → done` 报 `task state event fails the bundled stateEvent schema`；按旧规则最后一次回填与不追溯条款保留，不补造 checking，不声称整篇解析通过。
- #167 的 CI／Reviewy／合并操作者为编排方整理，本轮未重跑 CI；git 可核实的 SHA／committer 时间已标注本轮 git log 核实。历史本地测试失败原文不改写。
- 本轮仅本地文档校验，未生成额外报告文件，遵守四文件写入边界；原生命令输出保留在会话工具结果。`rtk: fallback-native`，直接运行原生命令；BDD／API／浏览器／构建不适用，无代码或运行行为改动。PR-b 的测试、审查及收尾尚未执行。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-24T11:59:03+08:00 | planned | in-progress | 编排方整理，主会话记录：开始 PRD 交付记录与最终核验；按第三个 commit 顺序建立跨 PR strict 任务。 | 已读取完整确认方案及两份既有 PRD；本轮只处理 PR-a 文档进度，不提前完成跨 PR 任务。 |
| 2026-10-24T11:59:52+08:00 | in-progress | in-progress | 编排方整理，主会话记录：PRD 完成并完成本轮文档／任务记录核验；仅更新 PR-a 进度，整个任务继续 in-progress。 | PRD 已本地提交；第一至第九节、两处 Reviewy 修订、非 git 细则、两 PR 拆分与生效点、不追溯条款均已核对；两份交叉引用可达。定向 unittest 19 tests／OK；新 task 的 TaskDocument.parse、schema／事件表／分支校验通过；旧 task 的兼容拒绝与分层验证结果见上节；git diff --check 通过，新增行及新文件禁词命中 0。 |
| 2026-10-24T12:39:20+08:00 | in-progress | in-progress | 编排方整理：补记 `34a9b94` 进度，plan.md:8 原文后已追加带真实 PR #168 的停用说明，PR #168 已开启。 | commit `34a9b94`；CI run `40061290088`，13/13 on `34a9b94`（编排方整理，本轮未重跑 CI）；at 为本轮整理时间。 |
| 2026-10-24T12:39:33+08:00 | in-progress | in-progress | 编排方整理：补记 `fdbb1bd` 归因修正轮，跨两 PR 结构改为用户 2026-10-24 11:14 群内确认（落地方案），Lord 记录；非 git 细则改为属 11:05 完整方案、用户 2026-10-24 11:11 群内确认（最终修订方案确认），Lord 记录；已去除错误时间归因。 | commit `fdbb1bd` 已 push（编排方整理）；CI run `40062997215` 结果本轮不可考；at 为本轮整理时间。 |
| 2026-10-24T12:39:40+08:00 | in-progress | in-progress | 编排方整理：本轮 fix2 按 Reviewy 对 `34a9b94` 的审查意见修正归因格式、state.md／AGENTS.project.md 行号、trailer 理由与本 task 范围描述。 | 本轮修正与本事件纳入同一个本地提交，未 push；保留旧事件，status 保持 in-progress、completed_at 为 null；at 为本轮整理时间。 |
| 2026-10-24T12:48:08+08:00 | in-progress | in-progress | 用户 2026-10-24 12:46 群内确认（旧格式事件规则修订版），Lord 记录：A／B／C 一致，不依赖 git 或 PR-a 合入边界；旧格式原样保留、不补造 checking、只读不写；仅因旧格式解析失败时只按 status 判断并在运行输出提示，不落盘、不阻塞、不算未记录改动；确需追加新事件时同次先追加含事件行数及 sha256（不含 frontmatter）的旧事件基线，不依赖 at 或 git；基线内只读不校验，基线后严格逐行校验（含回填历史 done），基线哈希变化则记未记录改动交用户判断；其他解析错误照常报错。 | [PRD「旧格式事件规则」](../../../docs/prd/sbtd-workflow-v2-task-status-sync.md#旧格式事件规则)；at 为真实写入时间。 |
| 2026-10-24T12:49:41+08:00 | in-progress | in-progress | 用户 2026-10-24 12:46 群内确认（旧格式判定口径，采纳 OMP 补充），Lord 记录：「仅因旧格式」的判定口径——在没有基线事件的文件中，每一条事件行都必须能按旧格式 schema 解析；若有任何一行既不是旧格式也不是当前格式，按旧格式事件规则第 5 点作为普通解析错误报告。 | [PRD「旧格式事件规则」](../../../docs/prd/sbtd-workflow-v2-task-status-sync.md#旧格式事件规则)判定口径单列，与五点规则分开归因；at 为真实写入时间。 |
| 2026-10-24T12:49:42+08:00 | in-progress | in-progress | 编排方整理：fix3b 轮将旧格式事件规则修订版（五点）与判定口径分别写入 PRD 与本 task，纳入同一个提交。 | 两份文件中五点规则与判定口径各自单列用户 2026-10-24 12:46 群内确认归因；旧事件不动，status 保持 in-progress、completed_at 为 null；fdbb1bd 的 CI run `40062997215` 写入时仍在运行（11/12 jobs 已通过），本轮不追加其最终结果；at 为真实写入时间。 |
