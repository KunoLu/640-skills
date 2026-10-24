# SBTD v2：任务状态及时更新

## 基线与范围

- 归因：用户 2026-10-24 11:11 群内确认（最终修订方案确认），Lord 记录。
- 落地方式与生效点：用户 2026-10-24 11:14 群内确认；新 PRD＋plan.md 追加，分 PR-a／PR-b 落地，新规则自 PR-a 合入起生效。
- 事实源与交叉引用：[任务状态运行时](sbtd-workflow-v2-task-state-runtime.md)、[任务数据契约](sbtd-workflow-v2-task-data-contract.md)及 `sbtd-task/references/state.md`。沿用既有状态、原子写入和历史证据规则，不另起数据契约副本。
- 编排方整理：本文按确认方案第一至第九节组织。不追溯条款的依据与归因单列。群内时间均为 +08:00。status-sync 跨两个 PR 的任务结构：用户 2026-10-24 11:14 群内确认（落地方案），Lord 记录。
- 本文为工作流规则 PRD，不宣称相关脚本、测试或运行时改动已经实施。

## 一、根因

1. 项目把「合入 SHA 和合入时间」当成了 done 的前提。这些信息合入后才有，只能靠下一个 PR 回填。没有下一个 PR 时，状态就一直不会更新，r1.2b 就是这样漏掉的。
2. 状态常常在收尾时一次性补写。中途被打断、omp 中止或超时、只改代码的修复轮次，都会把状态漏掉。
3. 进展只记在聊天或记忆里，没有写进 task.md。
4. 用户决策等待项没有在用户回复后当场关闭。
5. 「下一个 PR 回填上一个 PR」不是 sbtd 的规则，是项目自己的约定（`ai/tasks/v2.1.0-rc.2-plan/plan.md:8`）。sbtd 对 done 的定义只是「验收证据成立」（`AGENTS.project.md:29`）。

## 二、总原则

1. 状态更新与回填是每个工作流节点的第一步，default、lite、strict 三种模式都适用。
2. 状态在当下的改动里写完。取消「首个 commit 回填上一个 PR」这条项目约定，合入 SHA 和时间不再写回 task.md。
3. 检查只用 git 或本地文件，不绑定 gh、GitLab、Bitbucket 等平台工具，也不放进 CI。
4. 沿用 sbtd 现有规则：状态流转、原子写入、写不进去时报告「未持久化」（`AGENTS.project.md:27`）、证明不了的记「不可考」、不补造历史。

## 三、前置判断（两件事分开判断）

1. branch 字段看项目是不是 git 项目。复用 `TaskStore.current_binding()`，不直接跑 `git rev-parse`，避免在未跟踪或被忽略的目录里误判。
   - git 项目：记真实分支，或 `detached:<完整 SHA>`。
   - 真正的非 git 项目：记 `branch: null`。
2. 核对方式看 task.md 有没有被 git 跟踪。用 `git ls-files --error-unmatch` 判断。
   - A. lite 或 strict 模式，task.md 在 `ai/tasks/` 下且被跟踪，有远端：走 git 核对。
   - B. 同上，但没有远端：只比对本地 HEAD、工作区和 task.md，不查远端，也不会误判成已丢弃。
   - C. default 模式（`.sbtd/` 被 ignore），或任何未被跟踪的 task.md，或真正的非 git 项目：走文件核对。

## 四、通用节点规则（所有情况都适用）

1. 开始任务、换会话、中断恢复时：先核对 task.md 和实际进度，方式按第五节或第六节。有差异先补写，再做别的。
2. 执行中：每一步成对记事件，开始时写「开始 X」，做完写「完成 X + 验证结果」。中断后看最后一条事件就知道断在哪一步。
3. 收到审查结论或用户决定后：下一个动作就是记事件，用户决策等待项当场关闭。
4. 结束会话前：先把 task.md 写成当前的真实状态，再退出。
5. 写入规则：只追加、不改写；每次写之前先重读最新内容；每条事件带写入者和时间；原子写入。
6. 发现不一致时：追加一条「发现未记录的改动」事件，列出差异，交给用户判断，不自动改状态，也不自动 reopen。
7. 一个 task 拆成多个 PR 或多轮时：中间各轮只更新进度，最后一轮写完成状态。
8. detached HEAD 或多个 worktree：以 task.md 里记录的 branch 为准去比，不用当前 worktree 的分支名。

### 不追溯条款：checking-before-done

历史上从 in-progress 直接跳到 done 的记录保持原样不追改；新规则生效后，task 必须先进入 `checking`（`sbtd-task/references/state.md:42`）才能写 `done`。

归因：依据 `sbtd-task/references/state.md:42` 与「用户 2026-10-24 10:39 群内「我选B」」，编排方整理。

## 五、git 核对（A 和 B 两种情况）

1. 核对方法：
   - A：`git fetch` 后，用 `git show origin/<默认分支>:<task.md>` 和本地内容对比。只比内容，不看 commit 的祖先关系，squash 合入也适用。
   - B：只比对本地内容。
2. 远端分支已不存在（用 `git ls-remote --heads` 查不到），而默认分支上的 task 又不是 done：按已丢弃处理，记一条事件交给用户。
3. 每次 commit 前：进展、状态和事件跟代码放进同一个 commit。直接 push、不走 PR 的场景也靠这一条，push 出去的就是最终状态。
4. push 或开 PR 前：确认 task.md 反映的就是要推送的 tip。
5. 收尾流程（用户选的 B）：
   - 审查期间保持 `checking`，被打回就直接回 in-progress。
   - CLEAN 之后追加一个只改 task.md 的 commit，写 `done` 和 `completed_at`。
   - Reviewy 只复核这处 diff，不重新整轮审查，CI 照常要求全绿后才合入。
   - **Reviewy 修订 2，Lord 2026-10-24 11:11 采纳，随最终修订方案确认**：收尾 commit 只能改三处：这个 task 的 frontmatter（`status`、`completed_at`、`updated_at`）、追加的一条 done 事件，以及这条事件的证据。证据只记 CLEAN 对应的 SHA 和 CI run。改了任何别的文件或别的行，都要整轮重审。
6. 查合入记录：`git log origin/<默认分支> -- <task.md>` 按路径查，不依赖 PR 号和提交信息；`Task: <id>` trailer 只作辅助。

## 六、文件核对（C）

1. task 在 frontmatter 里声明自己涉及的目录范围。
2. 每条「完成 X」事件记下这一步改过的文件和它们的 sha256。验收证据（构建产物、报告、截图）也按 sha256 记录，包括 git 项目里被 ignore 的文件。
3. 开始任务或恢复时：
   - 读 `.sbtd/active-task.json` 指向的 task.md 的最后一条事件。
   - 先在声明的范围里用文件清单和 mtime 筛出新增、删除和没登记的改动。
   - 再用 sha256 判断内容是不是真的变了。mtime 只负责触发检查，结果以 sha256 为准。
4. 验收：验收证据成立后改成 `checking`。需要审查的，等审查通过；不需要审查的，直接在同一步写 `done` 和真实的 `completed_at`。

### 非 git 项目节点细则

属 11:05 完整方案，用户 2026-10-24 11:11 群内确认（最终修订方案确认），Lord 记录：

- 开始任务先写 frontmatter `status: in-progress`、`branch: null`、带时区 `created_at`、目录范围并追加「开始」事件。
- 每步「开始 X」／「完成 X」含验证结果、改动文件及 sha256，更新 `updated_at`。
- 原子写入，失败报「未持久化」。
- 结束或被打断前写成真实状态。
- 恢复时按上述核对，不一致只追加事件不改状态，证明不了记「不可考」。

## 七、中途 `git init`

1. 所有 task 都追加一条重绑定事件，补上真实 branch（`AGENTS.project.md:27`）。之前的 sha256 证据原样保留，不补造 commit。
2. lite 和 strict 的 task.md 被 git 跟踪后，从这条事件之后改走 git 核对。
3. default 模式的 `.sbtd/` 仍被忽略，继续用文件核对。

## 八、兜底

Reviewy 审查时照样核对 task.md 的状态，有问题算阻塞项。这只是最后一道检查，不替代工作流里的自查。

## 九、实施

1. **Reviewy 修订 1，Lord 2026-10-24 11:11 采纳，随最终修订方案确认**：单独开 workflow 规则 PR。`plan.md:8` 原文不删，追加一条「自 PR-a 起停用，由 sbtd-workflow-v2-task-status-sync.md 替代」，并写明归因。编排方整理：PR-a 实际编号由编排方取得后补入 plan.md，本 PRD 统一使用 PR-a。
2. 落地分两个 PR（用户 2026-10-24 11:14 确认）：
   - PR-a：只加 PRD `docs/prd/sbtd-workflow-v2-task-status-sync.md`，追加 plan.md 停用说明和任务表一行，新建 strict 任务 `ai/tasks/v2.1.0-rc.2-task-status-sync/task.md`。
   - PR-b：PR-a 合入后开。按 PRD 改 `sbtd-workflow-onboard/` 的 SKILL.md、REFERENCE.md、`templates/agents/AGENTS.project.md`、`sbtd-task` 的 state reference 和相关脚本，配齐测试：三种核对方式各自的判定、多人同时写入、中途 `git init`、发现不一致时不自动 reopen。
3. 生效点：新规则从 PR-a 合入起生效（用户 2026-10-24 11:14 确认）。PR-a 的第一个 commit 按旧规则回填上一个 PR（最后一次）。PR-b 是新规则下的第一个 PR：第一个 commit 不回填 PR-a；收尾按 B 方案写 done；审查按新规则。
4. 用户 2026-10-24 11:14 群内确认（落地方案），Lord 记录：status-sync 是一个跨两个 PR 的任务。PR-a 的 task.md 只写进度（PRD 完成），状态保持 in-progress；PR-b 在 CLEAN 后按 B 方案把整个任务写 done。PR-a 的合并 SHA 和时间按新规则不写进 task.md，用 `git log origin/main -- <task.md>` 查。
5. Lord 的编排规矩同步改掉，不再要求首个 commit 回填上一个 PR。
