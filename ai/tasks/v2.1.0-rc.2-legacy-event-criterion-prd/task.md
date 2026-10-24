---
schema_version: 1
id: v2.1.0-rc.2-legacy-event-criterion-prd
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：本轮采用 strict；主会话为两个授权文件的唯一 writer、git 提交者与验证 controller；恰好两个本地提交，不启动子代理、不使用 advisor；push 与开 PR 由编排方在 omp 之外执行。
status: done
branch: docs/v2.1.0-rc.2-legacy-event-criterion-prd
created_at: '2026-10-24T18:36:34+08:00'
updated_at: '2026-10-25T01:14:14+08:00'
completed_at: '2026-10-24T20:39:06+08:00'
---

# rc.2：旧格式事件判定口径 PRD strict 任务

## 决定

- 用户 2026-10-24 18:04 群内确认（方案一），Lord 记录：在没有基线事件的文件中，一条历史事件行若五列（at／from／to／reason／evidence）均完整、但不符合仓库内置 stateEvent schema（例如任何 schema 版本中都不存在的状态 `verifying`、`in_progress`），也算旧格式；按 frontmatter `status` 判断该 task 当前状态，在本次运行输出中提示「旧格式事件，不追溯」，不阻塞，永不改写该旧文件；五列不完整等其他无法解析的情况仍按第 5 点作为普通解析错误报告。详见 [PRD「旧格式事件规则」](../../../docs/prd/sbtd-workflow-v2-task-status-sync.md#旧格式事件规则)。PRD 保留原 12:46 归因及原有内容的含义，在同一行追加这次放宽。
- 用户 2026-10-24 18:05 群内确认（先收尾 #169），Lord 记录：先收尾 #169，再做本 PRD PR。
- 编排方整理：本轮指令中的范围、提交顺序、手写记录方式与模型记录要求按本节及下文执行；全部时间使用 Asia/Shanghai（+08:00），本轮事件时间由 `TZ=Asia/Shanghai date -Iseconds` 获取。

## 范围与边界

- 本 PR 只修改 `docs/prd/sbtd-workflow-v2-task-status-sync.md` 第 65 行，并新建本 `task.md`；不改 PRD 其他行、不改 plan.md 或其他文件。
- 编排方整理：Commit 1 只提交 PRD 判定口径；Commit 2 只提交本 strict 任务。本会话内执行两个 `git commit`，不 amend、不 force、不 push、不执行 gh 操作、不修改 omp 全局配置。
- 按新的任务状态规则，本 PR 不回填 #169 的合并记录；本 task 保持 `in-progress`，`completed_at: null`，不把本地文档交付写成实现、审查、合入或发布完成。
- 本 task.md 为手写，未经 TaskStore 写入。编排方整理：当前 `TaskStore.inspect()` → `_catalog()` 解析全部 task.md 时，被以下 3 个旧 task.md 以 `task state event fails the bundled stateEvent schema` 失败阻塞：`ai/tasks/v2.1.0-rc.1-csv-reasoning-tokens/task.md`、`ai/tasks/v2.1.0-rc.1-r1.3-stats-api/task.md`、`ai/tasks/v2.1.0-rc.2-r2.1b-renderer/task.md`。本轮沿用该已报告事实，不重跑失败调用，不改写这些旧文件。
- 修复（fix4）在本 PRD PR 合入后另开实现 PR 进行；本 PR 只改规则文档与本 task，不宣称当前解析器已经支持放宽口径。
- 未完整调用 grill-with-docs：归因、规则边界、交付顺序与验收条件已明确，无需重复澄清。未运行独立审查；本会话未使用子代理（task／reviewer／subagent），未使用 advisor。
- 本轮仅以仓库 `sbtd_task_state` 模块的 `TaskDocument.parse` 只读验证本 task，不调用 TaskStore 写入，不写 active／index／handoff／ignore／身份；不承诺自动恢复。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮适用性 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，文档前 | not-needed；未完整 grill，只整理已有明确决定 |
| book-ddia-data-design | schema、迁移或持久化机制设计前 | not-needed；不改 schema 或持久化机制，fix4 的实现设计不在本 PR |
| book-legacy-change-safety | 既有运行时行为修改前 | not-needed；不改运行时代码，不重写旧事件 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；仅一行 PRD 与一个任务记录 |
| book-release-readiness | 运行时或部署变化，验证后 | not-needed；无实现、部署或发布，本轮不宣称发布就绪 |
| project-validation | 文档范围及新任务契约核验 | 只读执行 diff／新增行禁词／TaskDocument.parse 检查，不调用 TaskStore 写入 |

## 验证与剩余边界

- Commit 1 提交前已核对：PRD 相对 origin/main 仅第 65 行变化、原文及原 12:46 归因保留；`git diff --check` 干净，新增行禁词命中 0。
- 新 task 的提交前检查覆盖 frontmatter、状态事件、真实分支、模型会话路径和两个文件的改动范围；验证结果追加到状态事件表，不提前宣称通过。
- 本轮为文档与记录的本地只读核验，不运行单元／集成／E2E 或全量 CI，不创建额外报告文件；真实解析 smoke 只证明本 task 符合现有契约，不证明 fix4 已实现。BDD：skipped（无运行时实现）；API Contract／Cross-repo context：not-needed；Mock Strategy：none；rtk：not-needed（原生 git 精确 diff 与只读 Python 解析）。
- 旧 task 的 catalog 阻塞仍存在；本轮不修复、不掩盖，也不把手写记录描述为 TaskStore 持久化成功。push 与开 PR 由编排方在 omp 之外执行。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | 产出 | 会话文件 |
|---|---|---|---|---|---|
| 1 | ping（2026-10-24 18:34:50 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `~/.omp/agent/sessions/--workspace-640-skills-legacy-criterion-prd--/2026-10-24T10-34-50-279Z_01a16d7a-3e27-753f-902d-c9382d9eaa5a.jsonl` |
| 2 | main（本会话） | openai-codex/gpt-6-astra（high） | 15／28 | PRD 第 65 行与本 task；两个本地提交由本会话执行 | `~/.omp/logs/640-legacy-criterion-prd/s1/2026-10-24T10-35-42-024Z_01a16d7b-0848-725a-a972-00009e1d972f.jsonl` |
| 3 | fix1 ping（2026-10-24 18:45:18 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `~/.omp/agent/sessions/--workspace-640-skills-legacy-criterion-prd--/2026-10-24T10-45-18-838Z_01a16d83-d576-72f2-b10b-7c4f01f5fa43.jsonl` |
| 4 | fix1 main s1 | openai-codex/gpt-6-astra（high） | 14／30 | Reviewy b26fbf1 阻塞修复：PRD :65 与决定第一条去掉「只」「一次」；其本地提交 097df0c 未 push，编排方 reset --soft 后由 s2 重新提交 | `~/.omp/logs/640-legacy-criterion-prd/fix1/s1/2026-10-24T10-45-53-074Z_01a16d84-5b32-7189-a3d2-538fe24a5977.jsonl` |
| 5 | fix1 main s2（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告；F 回填（编排方整理，按 jsonl 统计）：11／25 | 模型记录第 2 行改为 15／28，并以一个本地提交提交 fix1 全部改动 | `~/.omp/logs/640-legacy-criterion-prd/fix1/s2/2026-10-24T10-50-52-187Z_01a16d88-eb9b-72ad-a101-6049e1b0b78a.jsonl` |
| 6 | done ping（2026-10-24 19:32:06 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `~/.omp/agent/sessions/--workspace-640-skills-legacy-criterion-prd--/2026-10-24T11-32-06-935Z_01a16dae-ae97-72d1-8195-77ac8e9b86b1.jsonl` |
| 7 | done main s1 | openai-codex/gpt-6-astra（high） | 9／18 | 本地 done 提交 46d2b94（in-progress → done，会使本 task 成为旧格式）未 push，按 Lord 19:36 方案 A 丢弃 | `~/.omp/logs/640-legacy-criterion-prd/done/s1/2026-10-24T11-33-35-231Z_01a16db0-077f-74b1-8c81-8c38ba04f5bf.jsonl` |
| 8 | checking ping（2026-10-24 19:37:45 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `~/.omp/agent/sessions/--workspace-640-skills-legacy-criterion-prd--/2026-10-24T11-37-45-337Z_01a16db3-d879-706c-bf6f-6a5c5bc52035.jsonl` |
| 9 | checking main s1（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告；F 回填（编排方整理，按 jsonl 统计）：9／21 | 补记 in-progress → checking 与模型记录第 6–9 行，以一个本地提交提交 | `~/.omp/logs/640-legacy-criterion-prd/checking/s1/2026-10-24T11-38-28-854Z_01a16db4-8275-7227-9a0e-4da313b71c7e.jsonl` |
| 10 | done2 ping（2026-10-24 20:38:23 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查（F 回填，编排方整理） | `~/.omp/agent/sessions/--workspace-640-skills-legacy-criterion-prd--/2026-10-24T12-38-23-865Z_01a16deb-5d79-746d-ab68-8d641285a96e.jsonl` |
| 11 | done2 main s1 | openai-codex/gpt-6-astra（high） | 11／21 | done 提交（PR 分支 tip `1098d88`，squash 合入为 `3c49524`）（checking → done，按 PRD :79）；F 回填，编排方整理 | `~/.omp/logs/640-legacy-criterion-prd/done2/s1/2026-10-24T12-38-49-155Z_01a16deb-c043-70cc-a74b-6d71add943e0.jsonl` |

编排方整理：每个 omp 会话一行；本会话未使用子代理。push 与开 PR 由编排方在 omp 之外执行。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-24T18:36:34+08:00 | planned | in-progress | 编排方整理，主会话记录：建立手写 strict 任务，开始任务记录与交付核验。 | 根目录与分支已核对；授权路径无 symlink，新 task 不存在且未被 ignore；未调用 TaskStore 写入；at 为实际记录时间，不倒填群内决定时间。 |
| 2026-10-24T18:36:34+08:00 | in-progress | in-progress | 编排方整理，主会话记录：记录已完成的 PRD 判定口径修改与 Commit 1。 | commit `d79c129`；只改 PRD 第 65 行且保持单行，原文归因保留；git diff --check 干净，新增行禁词命中 0；本事件 at 为记录时间，不冒充提交时间。 |
| 2026-10-24T18:37:26+08:00 | in-progress | in-progress | 编排方整理，主会话记录：完成手写任务记录与本地只读自检，开始 Commit 2 提交。 | 仓库 sbtd_task_state.TaskDocument.parse 已通过；strict／in-progress、id／branch、completed_at=null 与现有事件 schema 校验通过；git diff --check、git diff --cached --check、git diff origin/main --check 均干净；git diff origin/main --stat 仅含两个授权文件，新增行禁词命中 0。本事件追加后提交前再次只读解析；本轮不调用 TaskStore 写入、不执行 push。 |
| 2026-10-24T18:51:13+08:00 | in-progress | in-progress | Reviewy b26fbf1 审查阻塞：PRD :65 「只提示一次」超出用户 18:04 原话，改回与第 2 点一致的「提示」；编排方整理 | 编排方整理：按 Lord 18:45 裁定（Reviewy 同意），同一提交将模型记录第 2 行改为实际计数 15／28（Reviewy 依 jsonl 01a16d7b-0848 核对）；git diff b26fbf1 --stat 仅含 PRD 与本 task.md 两个文件；PRD diff 仅第 65 行删除「只」「一次」且仍为单行；PRD :65 与决定第一条「一次」计数均为 0；git diff --check 干净，新增行禁词命中 0；仓库 sbtd_task_state.TaskDocument.parse 已通过；本轮不调用 TaskStore 写入、不执行 push。 |
| 2026-10-24T19:38:41+08:00 | in-progress | checking | 送审时漏记 checking，现补记，编排方整理：Reviewy 2026-10-24 19:31 群内对 `70cea1c` 给出 CLEAN；Lord 19:36 裁定按方案 A 先补 checking。 | Reviewy CLEAN SHA `70cea1c024f0fc34763c84c6e9d3b07b0b55c8ea`；CI run `40087854878` 13／13 success；编排方整理：按 Lord 19:37 裁定，模型记录表新增第 6–9 行；本次手写，未经 TaskStore 写入（TaskStore._catalog() 被 3 个旧 task.md 阻塞）；提交前以仓库 sbtd_task_state.TaskDocument.parse 读取通过（status=checking，非旧格式）。 |
| 2026-10-24T20:39:06+08:00 | checking | done | 编排方整理：Reviewy 2026-10-24 20:05 群内对 `47dbc6a` 给出 CLEAN，按 PRD :79 关闭。 | Reviewy CLEAN SHA `47dbc6aeff5b179c9a96aca97ada8c2593eb33d4`；CI run `40090906238` 13／13 success |
| 2026-10-25T01:01:15+08:00 | done | done | 编排方整理：更正 2026-10-24T19:38:41 事件中的 Reviewy CLEAN 时间。 | 该事件写「Reviewy 2026-10-24 19:31 群内对 `70cea1c` 给出 CLEAN」，Reviewy 群内更正实际为 19:18；原事件逐字保留，以本事件为准。 |
| 2026-10-25T01:01:31+08:00 | done | done | 编排方整理：F 回填模型记录与 plan.md 行。 | 第 5 行 fix1 main s2 11／25、第 9 行 checking main s1 9／21（均按 jsonl 统计，原「未知」原文保留）；新增第 10 行 done2 ping 1／0、第 11 行 done2 main s1 11／21；按 Lord 2026-10-24 18:42 群内裁定，plan.md 任务表为本 task 追加一行，四列写「见 task.md／PR 页面」；旧事件逐字不变，completed_at 不变；手写，未经 TaskStore 写入。 |
| 2026-10-25T01:14:14+08:00 | done | done | 编排方整理：F 回填 done 提交 tip 上 CI run `40094994851` 的 attempt 2 重跑记录。 | gh run view 40094994851 --attempt 1／2 --json jobs 核实：head `1098d88`（done 提交 tip，squash 合入为 `3c49524`）；attempt 1（2026-10-24 20:41:45 +08:00 创建）conclusion failure，linux-shards (2) failure（测试 :228 并发时序竞争，后由 #171 修复）、linux-full 汇总门 failure，其余 11 个 job success；attempt 2（2026-10-24 21:02:35 +08:00 创建）仅重跑 linux-shards (2)（21:02:38–21:19:33）与 linux-full（21:19:36–21:19:52），均 success，其余 11 个 job 沿用 attempt 1 结果，conclusion success，13／13；attempt 2 由编排方未先询问即重跑。合入前 tip 的 CI 证据为 attempt 2；本文件 2026-10-24T20:39:06 done 事件引用的是 CLEAN SHA `47dbc6a` 上的 CI run `40090906238`（attempt 1，13／13 success），不是 40094994851；原事件逐字不变。 |
