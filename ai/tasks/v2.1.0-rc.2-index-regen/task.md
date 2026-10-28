---
schema_version: 1
id: v2.1.0-rc.2-index-regen
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：strict；omp 为唯一内容 writer，不启动子代理或 advisor；提交、推送与开 PR 由编排方执行
status: done
branch: docs/v2.1.0-rc.2-index-regen
created_at: '2026-10-28T13:04:24+08:00'
updated_at: '2026-10-28T13:36:08+08:00'
completed_at: '2026-10-28T13:36:08+08:00'
---

# rc.2 共享任务索引自动块重生成与本任务记录

## 目标

用 sbtd_task_state.py 的索引生成逻辑重生成 `ai/tasks/index.md` 自动块，只增加缺失行（含本任务自身一行），既有行逐字节保留、顺序不变。第 1 次提交进入 checking，done 在第 1 次提交 CI 通过后的第 2 次提交写入，届时再次运行生成逻辑。

## 决定与归属

用户 2026-10-28 群内确认（三个都要做，按你建议的执行），Lord 记录。注：分钟不可考。

本 PR 步骤（以 sbtd_task_state.py 生成逻辑重生成 index.md 自动块、只增行且不删改不重排既有行、本任务目录须在索引中列出、checking 与 done 分两次提交）为 Lord 2026-10-28 群内裁定。
注：分钟不可考。

用户 2026-10-28 群内确认（确认没问题后，可以直接合并），Lord 记录。注：分钟不可考。
按该确认，Lord 记录本 PR 为预先授权合并：精确 SHA 获 Reviewy 审阅 CLEAN 且 Lord 按名称核对 13/13 后，由 Lord 直接 squash-merge，不再等待另一次「合入」；该授权仅适用于本 PR。合并只由 Lord 执行，omp 与编排方不合并；不打 tag、不发 Release。

编排方整理：未完整调用 grill-with-docs，因范围、生成命令、验收条件明确，无领域歧义。事实来自本任务提示与仓库；不联网补查，不读取或统计会话 jsonl。

## 范围与边界

恰好两个文件：

1. `ai/tasks/v2.1.0-rc.2-index-regen/task.md`：手写本任务的 strict 模式、归属、生成方式、模型与状态事件、本地自检记录；允许新建其父目录。
2. `ai/tasks/index.md`：只通过下方 G_WRITE 写入生成结果，不手写或手工编辑。

不改 plan.md、CHANGELOG、其他 task.md、源码、测试。不写其他任何文件，不建临时文件、临时脚本或报告；不调用子代理、task 工具或 advisor；不执行任何 gh 命令、git 写操作、联网、安装依赖或构建；不打印环境变量，不读 .env、凭据、密钥或 token 文件，不读取或统计会话 jsonl；Python 一律加 `-B`。

沿用 plan-rows-backfill task.md 的 frontmatter 字段顺序、节结构、Book Gate Plan 五行、模型表与五列事件表，归属写法参考 tag-backfill task.md。手写本记录，未经 TaskStore 写方法写入；本记录只运行真实 parser 与静态只读 `TaskStore._history`。索引命令仅实例化 `read_only=True` 的 TaskStore 并调用只读方法，不调用 `_write`、create、transition、set_mode、promote、archive、select、rebind、protect_local_state 等写方法；不写 active／handoff／ignore／身份，不声称 helper 自动恢复成功。

写前核对：分支 `docs/v2.1.0-rc.2-index-regen`，HEAD `ecab0f085abb81e7f979b61df254b0e53e187df0`，`git status --porcelain` 无输出。结构模板全文、归属模板前 60 行、index.md 全文及生成逻辑指定段落已通读。两个目标及父路径无 symlink、路径未逃逸；index.md 为已跟踪普通文件，新任务及其目录此前不存在，工作目录下不存在 `.sbtd/tasks`；`git check-ignore --no-index` 对两个目标均 exit 1、无输出，新目标未跟踪。

## 生成方式与只增核对

编排方整理，生成逻辑已在本会话只读核对：

- `sbtd-workflow-onboard/scripts/sbtd_task_state.py` 无 CLI（模块文档串写明 No CLI）。index 自动块由 `TaskStore._index_candidate(records, previous)` 生成，records 来自 `TaskStore._catalog()`：扫描 `.sbtd/tasks` 与 `ai/tasks` 下所有 task.md，按 frontmatter id 排序，`_index_rows` 只列 `ai/tasks/` 下的任务，每行仅 `- [id](相对路径)`，不含状态、日期或 PR 信息。标记 `<!-- sbtd-task-index:start -->` 与 `<!-- sbtd-task-index:end -->` 之外的字节保持不动；块内若有不属于新旧行集合的行或重复行则报错拒绝。G_WRITE 实例化 `read_only=True` 的 TaskStore，只调用只读的 `_catalog`、`_index_candidate`、`_index_rows`，以 `Path.write_bytes` 写入生成结果，不调用 TaskStore 写方法，不写 active／handoff／ignore／身份。
- 编排方只读预览（main `ecab0f085abb81e7f979b61df254b0e53e187df0`，生成结果输出到仓库外，未写仓库）：现有自动块 19 行，生成 67 行，新增 48 行（rc.1 一行 `v2.1.0-rc.1-r1.3-stats-api`，rc.2 47 行）；既有 19 行逐字节保留且相对顺序不变；标记外前后缀逐字节相同；无删除、无改写、无重排。
- 加入本任务目录后预期生成 68 行，相对 main 新增 49 行（含本任务自身一行 `- [v2.1.0-rc.2-index-regen](v2.1.0-rc.2-index-regen/task.md)`，按 id 排序位于 `v2.1.0-rc.2-idempotent-replay-before-503` 与 `v2.1.0-rc.2-legacy-criterion-wording-sync` 两行之间）。因为索引按目录扫描，本任务 task.md 必须先存在再运行 G_WRITE，本任务行才会出现。
- 索引行不含状态列，因此本任务从 checking 改为 done 时重生成，预期 index.md 字节不变；plan.md 任务表四列口径 C'（未 done 行写「见 task.md／PR 页面」）不适用于本索引，生成结果中不出现该措辞。

在仓库根执行，命令原文如下。

G_WRITE（写 index.md）：

```sh
python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); Path('ai/tasks/index.md').write_bytes(a); print('INDEX_REGEN', 'changed=%s' % (b!=a), 'rows=%d' % len(s._index_rows(r)))"
```

G_PREVIEW（只读，比较生成结果与落盘 index.md，不写文件）：

```sh
python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); print('INDEX_PREVIEW_SAME', Path('ai/tasks/index.md').read_bytes()==a, 'rows=%d' % len(s._index_rows(r)))"
```

编排方整理：两条命令运行时 stderr 会打印 13 行「旧格式事件，不追溯」（来自 `sbtd_task_document.py` 对历史 task 旧格式事件的提示），属预期，不是错误。

本次实际结果：先建立本任务 task.md，再运行 G_WRITE，输出 `INDEX_REGEN changed=True rows=68`，exit 0，stderr 实际为上述 13 行提示。自动块 68 行无重复，相对基线新增 49 行、删除 0；既有 19 行逐字节保留且相对顺序不变，标记外前后缀逐字节相同。本任务行紧随 `v2.1.0-rc.2-idempotent-replay-before-503`，紧邻下一行 `v2.1.0-rc.2-legacy-criterion-wording-sync`；索引仅含导航行，无状态、日期或 PR 列。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮适用性与结果 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求前 | not-needed；未完整 grill，仅重生成导航索引并新增任务记录，范围与归属明确 |
| book-ddia-data-design | schema、迁移或持久化机制设计前 | not-needed；沿用既有任务格式与索引生成逻辑，不改 schema 或持久化机制 |
| book-legacy-change-safety | 既有行为修改前 | not-needed；无行为修改，仅运行既有生成逻辑重生成导航索引并新增任务记录 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；不改生产代码，不做重构 |
| book-release-readiness | 运行时或部署变化，验证后 | not-needed；无发布变化，不操作 tag／Release，不执行部署，不声称本 PR 发布就绪 |

## 验证与剩余边界

- T1 为 `2026-10-28T13:04:24+08:00`，来自开始写本文件前单独执行 `TZ=Asia/Shanghai date -Iseconds` 的实际输出，用于 created_at 与 planned → in-progress 事件。
- 写前路径检查实际输出两个目标均 `PATH_SAFE ignore=none`，index.md `tracked=True`，新任务 `tracked=False`，两项 `check-ignore_exit=1`，以及 `NEW_TASK_DIRECTORY_ABSENT=True LOCAL_TASKS_ABSENT=True`，exit 0。
- G_WRITE 实际输出 `INDEX_REGEN changed=True rows=68`，exit 0；13 行「旧格式事件，不追溯」为历史格式提示，不是错误。
- 与 `git show HEAD:ai/tasks/index.md` 原始字节在内存中比较，实际输出 `INDEX_ONLY_ADDITIONS_OK old=19 rows=68 added=49 deleted=0 unique=True`、`INDEX_BYTES_OK prefix=True suffix=True existing_bytes=True existing_order=True`、`INDEX_SELF_POSITION_OK idempotent-replay-before-503 < index-regen < legacy-criterion-wording-sync`；`git diff --numstat -- ai/tasks/index.md` 输出 `49	0	ai/tasks/index.md`。无删除、无改写、无重排；生成结果不含口径 C' 的状态措辞。
- 自检过程保留：首轮额外排序断言误把整条 Markdown 行作为排序键，触发 `AssertionError`、exit 1；这不等同于 task id 顺序错误。只读复核 `_index_rows` 与生成内容后，把内存断言改为提取 id 比较排序，完整重跑 exit 0；未改生成器或索引文件。既有行、前后缀、行数与本任务相邻位置检查均通过。
- 写入后在仓库根执行以下原生命令，exit 0，实际输出 `ai/tasks/v2.1.0-rc.2-index-regen/task.md in-progress False 1 None`：

  ```sh
  python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" ai/tasks/v2.1.0-rc.2-index-regen/task.md
  ```

- 静态只读调用 `TaskStore._history(TaskDocument.parse(...))`，此检查未实例化 TaskStore，实际输出 `HISTORY (None, True)`。frontmatter 字段顺序、strict／user、分支、首事件时间与 created_at、末事件时间与 updated_at、空 completed_at 均检查通过；模型表 6 列、事件表 5 列且单元格不换行。实际输出 `TASK_FIELDS_EVENTS_OK status=in-progress events=1`。
- 对本文件全文与 index.md 新增行逐项检查全部 17 项禁用规则：首项大小写不敏感，其余固定子串及无日期分钟归属正则；每项两范围计数均为 `[0, 0]`。实际输出 `BAN_COUNTS_OK 17 x 2 = 34 zero counts`；检查输出以 Unicode 码点标识禁用字面量。第 15 项路径子串亦为 0；群内归属无分钟时间。
- `git status --porcelain` 仅显示下列修改文件与新目录；`--untracked-files=all` 展开后新目录恰为 `ai/tasks/v2.1.0-rc.2-index-regen/task.md`。`git diff --check` exit 0、无输出。整组内存只读检查最终输出 `DOCUMENT_SELF_CHECK_OK`，exit 0；不创建自检脚本或报告。

  ```text
   M ai/tasks/index.md
  ?? ai/tasks/v2.1.0-rc.2-index-regen/
  ```

- 正文与验证记录写入、自检完成后，单独执行 `TZ=Asia/Shanghai date -Iseconds`，T2 实际输出为 `2026-10-28T13:06:49+08:00`，用于 in-progress → checking 事件与 updated_at；两条事件时间单调不减，completed_at 保持 null。
- checking 落盘后再次执行上方 parser 命令，实际输出 `ai/tasks/v2.1.0-rc.2-index-regen/task.md checking False 2 None`，exit 0；静态只读 `_history` 实际输出 `HISTORY (None, True)`，同组内存只读检查输出 `TASK_FIELDS_EVENTS_OK status=checking events=2` 与 `DOCUMENT_SELF_CHECK_OK`，exit 0。再次执行 G_PREVIEW，实际输出 `INDEX_PREVIEW_SAME True rows=68`，exit 0，stderr 为预期的 13 行「旧格式事件，不追溯」；证明 checking 状态写入后索引无需再变。只增 49 行、删除 0、既有 19 行字节与顺序、标记外前后缀、本任务相邻位置、34 个禁词计数、两种 status 与 diff whitespace 检查均保持通过；仅证明本地文档约束，不证明本 PR CI。
- 编排方整理：仓库内 tests、.github、sbtd-workflow-onboard/scripts 中无读取仓库自身 `ai/tasks/index.md` 内容的检查；`tests/test_sbtd_task_state.py` 的 index 用例使用临时目录，`tests/test_workflow_contracts.py` 只检查该路径可被跟踪（编排方 grep 实测）。本会话未重跑该检索，不把既有调查当作本轮运行结果。
- Evidence Source：developer-local；Source Revision：dirty；Environment Alignment：unverified；Evidence Publication：local-only。基线完整 SHA 为 `ecab0f085abb81e7f979b61df254b0e53e187df0`，验证对象为当前 worktree 的文档改动，不是本 PR tip 的正式 CI／发布验收证明。
- rtk：not-needed，使用约定原生命令。Final Test Report／Run Summary MD：not-needed，不创建额外报告。BDD：skipped，纯文档，无行为或 .feature 变化，无需场景语言与 runner 检查；Cross-repo context／API Contract：not-needed；Mock Strategy：none。单元／集成／Web／Mobile E2E、构建、额外 lint／formatter 与全量 CI 未运行：无代码变化，且禁止文件副作用、构建与联网。独立 review：not-needed，单一文档范围未触发严格独立复核条件；未调用子代理或 advisor，不冒称独立审查。Reviewy 审阅 CLEAN（精确 SHA）与 Lord 按名称核对 13/13 为 Lord 合并前置条件，本会话未执行该审阅。
- 提交前归属补正（checking 之后、第 1 次提交之前，frontmatter 与事件不动）：按用户 2026-10-28 群内确认（确认没问题后，可以直接合并）改写合并归属并补记模型表；补正后实际输出 `ai/tasks/v2.1.0-rc.2-index-regen/task.md checking False 2 None`、`HISTORY (None, True)`、`INDEX_PREVIEW_SAME True rows=68`（stderr 为预期的 13 行「旧格式事件，不追溯」）、`BAN_COUNTS_OK 17 zero counts` 与 `OLD_WORDING_COUNTS_OK 2 zero counts`（禁用项以 Unicode 码点逐项列出，计数全部为 0）、`git status --porcelain` 仅两行 ` M ai/tasks/index.md` 与 `?? ai/tasks/v2.1.0-rc.2-index-regen/`，`git diff --numstat -- ai/tasks/index.md` 输出 `49	0	ai/tasks/index.md`，`git diff --check` exit 0、无输出。
- done 提交：T3 为 `2026-10-28T13:36:08+08:00`，来自写 done 事件前单独执行 TZ=Asia/Shanghai date -Iseconds 的实际输出；done 状态写入后运行 G_WRITE，实际输出 `INDEX_REGEN changed=False rows=68`，git diff -- ai/tasks/index.md 无输出；parser 实际输出 `ai/tasks/v2.1.0-rc.2-index-regen/task.md done False 3 2026-10-28T13:36:08+08:00`；静态只读 _history 实际输出 `HISTORY (None, True)`；禁词全文计数 `BAN_COUNTS_OK 17 zero counts`；git status --porcelain 仅输出 ` M ai/tasks/v2.1.0-rc.2-index-regen/task.md`；git diff --check exit 0、无输出。
- 编排方整理：第 1 次提交 `3c94810776a7141f0de42b65f5fd1c8d3ff81e30` 的 run [40636776863](https://github.com/KunoLu/640-skills/actions/runs/40636776863) attempt 1 13/13 按名称 success，2026-10-28 13:34:07 (UTC+8) 完成；done 提交 tip 的 CI 以该 tip 的 CI 为准。未合并。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | model_usage | 产出 |
|---|---|---|---|---|---|
| 1 | ping 第 1 次 | openai-codex/gpt-6-astra（high） | 1／0（2026-10-28 13:02:09 (UTC+8) 开始，编排方据会话 jsonl 统计（executor-counted）） | 0 | 连通性检查 |
| 2 | main 第 1 次（2026-10-28 13:03:41 (UTC+8) 开始） | openai-codex/gpt-6-astra（high） | 17／36（编排方据会话 jsonl 统计（executor-counted）） | 0 | 本任务记录、index.md 自动块重生成与本地自检 |
| 3 | ping 第 2 次 | openai-codex/gpt-6-astra（high） | 1／0（2026-10-28 13:08:11 (UTC+8) 开始，编排方据会话 jsonl 统计（executor-counted）） | 0 | 连通性检查 |
| 4 | main 第 2 次（2026-10-28 13:08:43 (UTC+8) 开始，提交前归属补正） | openai-codex/gpt-6-astra（high） | 10／22（编排方据会话 jsonl 统计（executor-counted）） | 0 | 合并授权归属补正与模型表补记 |
| 5 | ping 第 3 次 | openai-codex/gpt-6-astra（high） | 1／0（2026-10-28 13:34:58 (UTC+8) 开始，编排方据会话 jsonl 统计（executor-counted）） | 0 | 连通性检查 |
| 6 | main 第 3 次（本会话，done 提交） | openai-codex/gpt-6-astra（high） | 本会话落盘时尚未结束，计数不在本文件自计；以编排方报告为准（executor-counted） | 以编排方报告为准 | done 事件、frontmatter、CI 结果与模型表补记，再次运行索引生成 |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-28T13:04:24+08:00 | planned | in-progress | 编排方整理：按明确的 strict 文档范围建立本任务，由 omp 唯一写入；index.md 仅由生成命令写入。 | 开始写本文件前单独执行 TZ=Asia/Shanghai date -Iseconds 的实际输出；分支、基线、干净工作区与目标路径已核对；未经 TaskStore 写方法写入。 |
| 2026-10-28T13:06:49+08:00 | in-progress | checking | 编排方整理：index.md 已由生成逻辑重生成且只增行，本地自检完成，进入 checking；本 PR 的 CI 尚待运行，不标完成。 | G_WRITE 输出 INDEX_REGEN changed=True rows=68；68 行／新增 49／删除 0，既有 19 行逐字节且顺序不变，标记外前后缀逐字节相同，本任务行位置正确；转换前 parser 为 in-progress False 1 None，静态 _history 为 (None, True)；17 项 × 2 范围禁词计数均 0；git status 仅 index.md 与新任务目录，展开后恰一个 task.md；git diff --check exit 0、无输出；DOCUMENT_SELF_CHECK_OK；本行时间来自写入前单独执行 date 的实际输出。 |
| 2026-10-28T13:36:08+08:00 | checking | done | 编排方整理：第 1 次提交内容自检通过且 CI 13/13 按名称全绿，按 Lord 裁定在内容核验后提交 done（Lord 归属：日期 2026-10-28，注：分钟不可考。） | 在 done 提交中补记：第 1 次提交 `3c94810776a7141f0de42b65f5fd1c8d3ff81e30`（编排方 commit 并普通 push），PR [#195](https://github.com/KunoLu/640-skills/pull/195)（base main，未合并）。该 SHA 的 CI：run [40636776863](https://github.com/KunoLu/640-skills/actions/runs/40636776863)，workflow `validation`，event `pull_request`，attempt 1，conclusion `success`，2026-10-28 13:34:07 (UTC+8) 完成；按名称 13/13 作业 success：dashboard-artifacts、linux-full、linux-shards (1)、linux-shards (2)、linux-shards (3)、macos-bash-installer、runtime-e2e-macos、runtime-e2e-windows、windows-powershell-installer、windows-shards (1)、windows-shards (2)、windows-shards (3)、windows-shards (4)。本 PR 截至本轮无 Reviewy 审阅记录；PR 页面上的 Codex 自动审阅显示未完成（用量限制），未产出审阅意见。done 依据为内容自检与上述 CI，按 Lord 2026-10-28 群内裁定（内容核验后再写 done，done 为第二个提交），不是审阅 CLEAN。该 CI 仅适用于 `3c94810`，不适用于本 done 提交，done 提交 tip 的 CI 以该 tip 的 CI 为准。done 状态写入后重跑 G_WRITE，实际输出 `INDEX_REGEN changed=False rows=68`，exit 0，stderr 为预期的 13 行「旧格式事件，不追溯」；git diff -- ai/tasks/index.md 无输出。合并由 Lord 在精确 SHA 获 Reviewy CLEAN 且按名称核对 13/13 后执行（用户 2026-10-28 群内确认（确认没问题后，可以直接合并），Lord 记录）。未合并。 |

以上保留 planned → in-progress 与 in-progress → checking 两条既有事件，并在 done 提交中补记 checking → done 转换；完成依据见 done 事件；未合并。
