---
schema_version: 1
id: v2.1.0-rc.2-task-status-sync
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：strict；本轮只做文档／任务记录，主会话唯一 writer／验证 controller，不使用 advisor；恰好三个本地提交。
status: in-progress
branch: docs/v2.1.0-rc.2-task-status-sync-prd
created_at: '2026-10-24T11:59:03+08:00'
updated_at: '2026-10-24T11:59:52+08:00'
completed_at: null
---

# 任务状态及时更新：跨 PR-a／PR-b 的 strict 任务

## 决定

- 用户 2026-10-24 11:11 群内确认（最终修订方案确认），Lord 记录。
- 用户 2026-10-24 11:14 群内确认落地方式与生效点；新规则自 PR-a 合入起生效。群内时间均为 +08:00。
- 编排方整理：任务跨两个 PR 的结构由 Reviewy 提出、Lord 2026-10-24 11:16 采纳，不归为用户确认条目。
- 规则事实源：[任务状态及时更新 PRD](../../../docs/prd/sbtd-workflow-v2-task-status-sync.md)。

## 范围与边界

- 本任务跨 PR-a（本 PR：PRD＋plan 停用说明＋任务记录）与 PR-b（按 PRD 改 `sbtd-workflow-onboard` 等并配测试）。PR-a 只记进度，保持 `in-progress`；PR-b 在 CLEAN 后按 B 方案写 `done`。
- 编排方整理：本轮只回填 #167、编写 PRD、追加 plan 任务表一行和本记录。plan.md 第 8 行保持原文，本轮不追加停用说明；编排方取得真实 PR-a 号后另行追加。该说明仍属于 PR-a 的整体范围，不宣称本轮已经写入。
- PR-a 的合并 SHA／时间按新规则不写入 task.md，用 `git log origin/main -- ai/tasks/v2.1.0-rc.2-task-status-sync/task.md` 查询。PR-b 首个 commit 不回填 PR-a；审查期间进入 `checking`，被打回回到 `in-progress`；CLEAN 后只追加限定的 task 收尾 commit，Reviewy 复核该 diff，CI 全绿后才合入。
- 编排方整理：仅四个授权文档；不改代码、OpenAPI、schema、技能目录；不 push、不开 PR、不改 git 或 omp 全局配置。不记录不可证明的事实，缺证据记「不可考」。
- 入口分支与基线已核对，工作区初始干净；授权路径无 symlink 且位于本 worktree 内，新文件未被 ignore。旧任务保留历史 branch，仅回填明确授权的合并事实，不重绑定。
- 未完整调用 grill-with-docs：确认方案及提交边界完整，无新增领域决策。本轮不运行 TaskStore lifecycle，不写 active／index／ignore／身份，不声明自动恢复可靠；按编排方整理的第三个 commit 顺序保存本 strict 记录。

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
