---
schema_version: 1
id: v2.1.0-rc.2-plan-rows-backfill
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：strict；omp 为唯一内容 writer，不启动子代理或 advisor；提交、推送与开 PR 由编排方执行
status: checking
branch: docs/v2.1.0-rc.2-plan-rows-backfill
created_at: '2026-10-28T11:15:10+08:00'
updated_at: '2026-10-28T11:17:37+08:00'
completed_at: null
---

# rc.2 plan.md 两处补正与本任务记录

## 目标

仅在 plan.md 的 F 行原任务路径后加注，并在 R2.1c 行后追加 tag-backfill 已完成记录；保留其余字节，记录本 PR 的 strict 范围、本地自检与剩余边界。本轮最终进入 checking，不写 done，不核定 F 行工作是否已完成。

## 决定与归属

用户 2026-10-28 群内确认（三个都要做，按你建议的执行），Lord 记录。

本 PR 两处计划补正、两个文件范围与本轮停在 checking 的范围依据为 Lord 2026-10-28 群内裁定。
注：分钟不可考。

编排方整理：未完整调用 grill-with-docs，因逐字修改、事实归属、文件范围与验收条件明确，无领域歧义。事实来自本任务提示与仓库；不联网补查，不读取或统计会话 jsonl。

## 范围与边界

恰好两个文件：

1. `ai/tasks/v2.1.0-rc.2-plan/plan.md`：F 行仅第 8 列追加注记；任务表 R2.1c 行后、空行前追加一行 tag-backfill。其余行逐字节不动。
2. `ai/tasks/v2.1.0-rc.2-plan-rows-backfill/task.md`：新建本任务的 strict 模式、归属、核查决定、模型与状态事件、本地自检记录；允许新建其父目录。

不改 E 行、各节正文、依赖顺序说明、`ai/tasks/index.md`、CHANGELOG、openapi、PRD、版本号、其他 task.md。不写其他文件，不建临时文件、临时脚本或报告；不调用子代理、task 工具或 advisor；不执行 gh、git 写操作、联网、安装依赖或构建；不打印环境变量，不读 .env 或凭据文件；Python 均加 `-B`。

沿用 tag-backfill task.md 的 frontmatter 字段顺序、节结构、Book Gate Plan 五行、模型表与五列事件表，手写本记录，未经 TaskStore 写入；只运行真实 parser 与静态只读 `_history`，不实例化 TaskStore，不调用其写方法。不写 active／index／handoff／ignore／身份，不声称 helper 自动恢复成功。

写前核对：分支 `docs/v2.1.0-rc.2-plan-rows-backfill`，HEAD `d2a6e376a6a2d6b88a14694f8e832cd19f690719`，`git status --porcelain` 无输出。plan.md 与模板全文已通读，F 裁定仅只读核对 `ai/tasks/v2.1.0-rc.2-f-backfill/task.md:25`。两个目标及父路径无 symlink、路径未逃逸；plan.md 为已跟踪普通文件，新任务及其目录此前不存在；`git check-ignore --no-index` 对两个目标均 exit 1、无输出，新目标未跟踪。

## F 行核查与决定

编排方整理：F 行（plan.md 基线 :26）第 8 列为 `ai/tasks/v2.1.0-rc.2-f-docs-backfill/task.md`。截至 main `d2a6e37`，`ai/tasks/` 下不存在 `v2.1.0-rc.2-f-docs-backfill/`；与 f 相关的目录只有 `v2.1.0-rc.2-f-backfill/`（由 PR #173 合入提交 `d45cfc8` 新建，2026-10-25T02:47:54+08:00）。该路径自 PR #141（`a55117c`）建表时即为计划路径。

plan.md 基线 :31 的 f-backfill 行写明「独立于 P8 F 行」；`ai/tasks/v2.1.0-rc.2-f-backfill/task.md:25` 记录 Lord 2026-10-25 01:10 群内裁定：保留 task id `v2.1.0-rc.2-f-backfill`、不并入 P8，P8 F 行的安装与使用文档工作不由该 task 承担。该行已只读核对，与独立任务边界一致。

plan.md「### F — docs 回填」节的 F 工作是 D10 的安装与使用文档回填（落盘快照 24h 行为、renderer 安装体积）。改指 f-backfill 与上述裁定矛盾，因此不改指向，只在原路径后加注：

`ai/tasks/v2.1.0-rc.2-f-docs-backfill/task.md（该目录未创建；f-backfill 行独立于本行，不承接本行工作，见 Lord 2026-10-25 01:10 群内裁定，ai/tasks/v2.1.0-rc.2-f-backfill/task.md:25）`

F 行其他 7 列不动。本 PR 不核定 F 行工作是否已完成；目录与建表历史采用编排方整理的事实，不冒称本会话重新执行历史调查。

## 新增行

在任务表 R2.1c 行之后、空行之前追加恰好一行 tag-backfill，8 列，单元格内无未转义分隔符。任务内容为 rc.2 发布后回填：tag 发布事实、R2.2 D9 记录、CHANGELOG 发布章节，归属采用上方用户确认原文。

四列口径依据：用户 2026-10-24 15:52 群内确认（plan.md 任务表四列口径 C'），Lord 记录（`ai/tasks/v2.1.0-rc.2-task-status-sync/task.md:131`）：尚未 done 的行四列写「见 task.md／PR 页面」，已填写的历史 done 行不动。tag-backfill 已 done，按本 PR 指令四列写实值，格式沿用 seq 0–R2.1b 已 done 行：状态列「done（PR #193 已 squash-merge）」、PR 列 `#193`、完整 merge SHA、+08:00 完成时间；不改其他行四列。

编排方整理：PR #193 已 squash-merge；模板 frontmatter `status: done` 已在本会话通读核对。两类时间分别记录，完成时间采用 GitHub mergedAt，不以 git committer 时间代替：

| PR | merge SHA | GitHub mergedAt（+08:00） | GitHub mergedAt（UTC） | git committer 时间 |
|---|---|---|---|---|
| #193 | d2a6e376a6a2d6b88a14694f8e832cd19f690719 | 2026-10-28T09:40:34+08:00 | 2026-10-28T01:40:34Z | 2026-10-28T09:40:33+08:00 |

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮适用性与结果 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求前 | not-needed；未完整 grill，仅补正既有计划记录，范围与归属明确 |
| book-ddia-data-design | schema、迁移或持久化机制设计前 | not-needed；沿用既有任务格式，不改 schema 或持久化机制 |
| book-legacy-change-safety | 既有行为修改前 | not-needed；无行为修改，仅两处计划补正及新任务记录 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；不改生产代码，不做重构 |
| book-release-readiness | 运行时或部署变化，验证后 | not-needed；仅记录既有合并事实，不操作 tag／Release，不执行部署，不声称本 PR 发布就绪 |

## 验证与剩余边界

- T1 为 `2026-10-28T11:15:10+08:00`，来自开始写本文件前单独执行 `TZ=Asia/Shanghai date -Iseconds` 的实际输出，用于 created_at 与 planned → in-progress 事件。
- 写前路径检查实际输出两个目标均 `PATH_SAFE ignore=none`，plan.md `tracked=True`，新任务 `tracked=False`，以及 `NEW_TASK_DIRECTORY_ABSENT=True`，exit 0。
- 写入后在仓库根执行以下原生命令，exit 0，实际输出 `ai/tasks/v2.1.0-rc.2-plan-rows-backfill/task.md in-progress False 1 None`：

  ```sh
  python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" ai/tasks/v2.1.0-rc.2-plan-rows-backfill/task.md
  ```

- 只读调用 `TaskStore._history(TaskDocument.parse(...))`，未实例化 TaskStore，实际输出 `history consistent = True`。frontmatter 字段顺序、strict／user、首事件时间与 created_at、末事件时间与 updated_at、空 completed_at 均检查通过。
- 内存中以 `git show HEAD:ai/tasks/v2.1.0-rc.2-plan/plan.md` 的原始字节构造两处约定修改，与落盘全文比较，实际输出 `PLAN_EXACT_BYTES_OK F_column_8_only=True other_bytes_unchanged=True`。任务表按未转义分隔符计数，含表头、分隔行共 19 行，每行 8 列；新行紧随 R2.1c，下一行为空，实际输出 `PLAN_TABLE_OK rows=19 columns=8 tag_after_R2.1c=True blank_after_tag=True`。`git diff -U0` 对 plan.md 的删除行恰为 F 原行，新增恰两行，实际输出 `PLAN_DIFF_OK deleted=1_F added=2`。
- 对 plan.md diff 新增行与本文件全文逐项检查全部 17 项禁用规则：首项大小写不敏感，其余固定子串及无日期分钟归属正则；每项两范围计数均为 `[0, 0]`。实际输出 `BAN_COUNTS_OK 17 x 2 = 34 zero counts`，其中第 15 项路径子串亦为 0；检查输出以 Unicode 码点标识禁用字面量。
- `git status --porcelain` 仅显示下列修改文件与新目录；`--untracked-files=all` 展开后新目录恰为 `ai/tasks/v2.1.0-rc.2-plan-rows-backfill/task.md`。`git diff --check` exit 0、无输出。整组内存只读检查最终输出 `DOCUMENT_SELF_CHECK_OK`，exit 0；不创建自检脚本。

  ```text
   M ai/tasks/v2.1.0-rc.2-plan/plan.md
  ?? ai/tasks/v2.1.0-rc.2-plan-rows-backfill/
  ```

- 正文与验证记录写入、自检完成后，单独执行 `TZ=Asia/Shanghai date -Iseconds`，实际输出 `2026-10-28T11:17:37+08:00`，用于 checking 事件与 updated_at；两条事件时间单调不减，completed_at 保持 null。
- checking 落盘后再次执行上方 parser 命令，实际输出 `ai/tasks/v2.1.0-rc.2-plan-rows-backfill/task.md checking False 2 None`，exit 0；同组内存只读检查再次输出 `history consistent = True`、`TASK_FIELDS_EVENTS_OK status=checking events=2` 与 `DOCUMENT_SELF_CHECK_OK`，exit 0。计划字节、8 列与插入位置、唯一删除行、34 个禁词计数、两种 status 与 diff whitespace 检查结果均保持通过；仅证明本地文档约束，不证明本 PR CI。
- 编排方整理：仓库内 tests、scripts、.github、sbtd-workflow-onboard/scripts、sbtd-runtime/tests 中无读取 plan.md 的代码（编排方 grep 实测）。本会话未重跑该检索，不把既有调查当作本轮运行结果。
- Evidence Source：developer-local；Source Revision：dirty；Environment Alignment：unverified；Evidence Publication：local-only。基线完整 SHA 为 `d2a6e376a6a2d6b88a14694f8e832cd19f690719`，验证对象为当前 worktree 的文档改动，不是本 PR tip 的正式 CI／发布验收证明。
- rtk：not-needed，使用约定原生命令。Final Test Report／Run Summary MD：not-needed，不创建额外报告。BDD：skipped，纯文档，无行为或 .feature 变化，无需场景语言与 runner 检查；Cross-repo context／API Contract：not-needed；Mock Strategy：none。单元／集成／Web／Mobile E2E、构建、额外 lint／formatter 与全量 CI 未运行：无代码变化，且禁止文件副作用、构建与联网。独立 review：not-needed，单一文档范围未触发严格独立复核条件；未调用子代理或 advisor，不冒称独立审查。
- 本 PR 的 CI 尚待运行；本轮不提交、不推送、不开 PR、不合并。模型计数不自计；F 工作完成情况不在本 PR 核定范围。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | model_usage | 产出 |
|---|---|---|---|---|---|
| 1 | ping 第 1 次 | openai-codex/gpt-6-astra（high） | 1／0（2026-10-28 11:13:57 (UTC+8) 开始，编排方据会话 jsonl 统计（executor-counted）） | 0 | 连通性检查 |
| 2 | main 第 1 次（本会话） | openai-codex/gpt-6-astra（high） | 本会话落盘时尚未结束，计数不在本文件自计；以编排方报告为准（executor-counted） | 以编排方报告为准 | plan.md 两处修改、本任务记录与本地自检 |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-28T11:15:10+08:00 | planned | in-progress | 编排方整理：按明确的 strict 文档范围建立本任务，由 omp 唯一写入。 | 开始写本文件前单独执行 TZ=Asia/Shanghai date -Iseconds 的实际输出；分支、基线、干净工作区与目标路径已核对；未经 TaskStore 写入。 |
| 2026-10-28T11:17:37+08:00 | in-progress | checking | 编排方整理：本地自检完成，进入 checking；本 PR 的 CI 尚待运行，不标完成。 | 转换前 parser 为 in-progress False 1 None；落盘后复核为 checking False 2 None；history consistent = True；plan.md 全文与两处约定修改逐字节一致，F 仅第 8 列变化，表格 19 行均 8 列，新增行紧随 R2.1c 且后接空行，删除行仅 F 原行；17 项 × 2 范围禁词计数均 0；git status 仅 plan.md 与新任务目录，展开后恰一个 task.md；git diff --check exit 0、无输出；DOCUMENT_SELF_CHECK_OK；本行时间来自写入前单独执行 date 的实际输出。 |
