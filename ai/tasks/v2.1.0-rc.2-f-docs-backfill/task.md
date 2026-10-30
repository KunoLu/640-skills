---
schema_version: 1
id: v2.1.0-rc.2-f-docs-backfill
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：strict；omp 为唯一内容 writer，不启动子代理或 advisor；提交、推送与开 PR 由编排方执行
status: done
branch: docs/v2.1.0-rc.2-r2.2-f-closeout
created_at: '2026-10-30T10:22:54+08:00'
updated_at: '2026-10-30T10:33:12+08:00'
completed_at: '2026-10-30T10:33:12+08:00'
---

# v2.1.0-rc.2 F：docs 回填核验与 F 行收口

## 目标与归属

`ai/tasks/v2.1.0-rc.2-plan/plan.md:26` 的 seq F「docs 回填」为 P8；要求见该文件「### F — docs 回填」节（:101–105）：锁定决定 D10；验收为①安装与使用文档更新落盘快照 24h 行为（消除 r1.4 报告 deferred 条目对应差异说明）②renderer 安装授权文档按实际所选模式显示体积③常规 docs 回填 PR 不修改 PRD 正文。后续项 B／C 已移至 E 前 Docs 步骤（P6.5），F 不重复执行。

用户 2026-10-30 群内确认（F 行标记 done 并补记），Lord 记录。注：分钟不可考。

编排方整理：按状态机约定在合入前记录 done。第 1 轮进入 checking，第 2 轮记录 done 并更新 plan 行。本任务只核验既有已合入文档并收口 F 行，不新增或修改文档正文，不升 PRD。

未完整调用 grill-with-docs：验收条目、证据行、归属与写入边界明确，无领域歧义。文档记录完成不代表运行时验收、发布就绪或本 PR CI 通过。

## 与 f-backfill 的边界

`v2.1.0-rc.2-f-backfill` 是独立记录任务，见 plan.md:31 及 `ai/tasks/v2.1.0-rc.2-f-backfill/task.md:25` 记录的 Lord 2026-10-25 01:10 群内裁定；不承接 P8 F 行工作。本任务目录即 F 行第 8 列计划路径，此前不存在，见 `ai/tasks/v2.1.0-rc.2-plan-rows-backfill/task.md:50` 注记；第 1 轮亦已检查目录不存在并建立本任务，第 2 轮不改指向 f-backfill。

## 验收证据

编排方整理：executor 已逐行读取并核对以下 5 行。本会话亦逐行 read 复核，内容与下表概述一致；引入提交分别通过 `git blame -L <n>,<n> --porcelain sbtd-runtime/docs/install-and-use.md` 核实，n 依次为 33、90、94、250、177。

| install-and-use.md 行 | 实际内容概述 | 支撑的 F 要求 | 引入提交 |
|---|---|---|---|
| :33 | 运行时家目录布局中 `snapshots/` 注释：R2.0c 临时 ReportSnapshot，24h 默认 TTL，0700/0600 | ① 落盘快照 24h（布局） | `e9cb05b`（#147） |
| :90 | 卸载与数据保留：ReportSnapshot 保存在 `snapshots/`，退出服务不删除；默认创建后 24 小时过期，下次启动清扫无引用过期快照 | ① 落盘快照 24h、启动清扫 | `e9cb05b`（#147） |
| :94 | 「快照与保留（R2.0c）」节：`SnapshotStore(home)` 默认 TTL 86400 秒（24 小时），创建／复用返回 `expires_at`，重启不续期，TTL 内凭原 `snapshot_id` 读取相同快照 | ① 落盘快照 24h（库面细节） | `e9cb05b`（#147） |
| :250 | serve 行为：R2.0c 起快照落盘 `snapshots/`，默认 TTL 24h，创建告知 expires_at；TTL 内重启仍可读取；R2.2 PR-1 起按共享配额规则清扫 | ① 落盘快照 24h（serve 侧） | `83b14ba`（#162） |
| :177 | renderer 安装：本次 Linux x64 `--only-shell` 实测下载 shell 约 120 MiB、FFmpeg 约 2.2 MiB；解压后 `browsers/` apparent size 290,381,668 bytes（约 277 MiB），实际分配 291,356,672 bytes（约 278 MiB）；不含 venv、字体及导出产物，不是所有平台的通用占用值 | ② 按实际所选模式（`--only-shell`）显示体积 | `c5904ef`（#155） |

`sbtd-runtime/docs/r1.4-acceptance-report.md:103` 的 deferred 条目写「当前快照是进程内对象，进程退出即消失。差异已在 install-and-use.md 写明」。本会话执行：

```sh
git log --format='%h %cI %s' -S '进程退出' -- sbtd-runtime/docs/install-and-use.md
```

实际输出：

```text
e9cb05b 2026-10-20T15:03:24+08:00 feat(r2.0c): persist ReportSnapshot to disk (24h TTL, atomic write, startup sweep) (#147)
0ca91b2 2026-10-17T14:58:06+08:00 chore(r1.4): rc.1 acceptance evidence and lock tests (#139)
```

另逐个执行 `git show --format= --unified=0 <sha> -- sbtd-runtime/docs/install-and-use.md`（sha 为 `0ca91b2`、`e9cb05b`），核实差异说明由 #139 引入、#147 移除并以上述 24h 行为替换。grep 工具以 `进程内对象|进程退出即消失` 检查当前 install-and-use.md，实际返回 `No matches found`。r1.4 报告是 rc.1 历史验收记录，本任务不修改。

③：本 PR 不修改 `docs/prd/` 下任何文件，第 2 轮以 diff 自检复核；本任务不升 PRD。:177 只是 Linux x64 的单次实测，不代表 macOS／Windows 占用；本任务不做新测量、不重跑安装。

## 范围与写入安全

本 PR 共四个文件：

1. `ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/task.md`：历史逐字节保留，仅允许 frontmatter status／updated_at／completed_at 与追加事件、收口节。
2. `ai/tasks/v2.1.0-rc.2-plan/plan.md`：第 1 轮不改，第 2 轮仅更新第 23、26 两行。
3. `ai/tasks/v2.1.0-rc.2-f-docs-backfill/task.md`：本任务与实际核验记录。
4. `ai/tasks/index.md`：只写生成器候选字节。

第 1 轮只写第 1、3、4 项；第 2 轮只写第 1、2、3 项，index 仅在生成器候选不一致时重写候选字节。不改 install-and-use.md 等文档正文、代码、contract、schema、PRD、CHANGELOG、openapi、ENTRYPOINT 或其他 task。手写 task，不调用 TaskStore 写方法；只读 parser／`_history`／`_catalog`／`_index_candidate` 核验，不声称 helper lifecycle、rebind 或自动恢复已执行。R2.2 的历史 branch 保留，本轮授权分支见本任务 frontmatter 与 R2.2 追加节。

第 1 轮写前分支与本任务 branch 一致，HEAD 与本地 origin/main 均为 `cddf15e5116257b875c20d8eee8a8c96f844ede9`；`git status --porcelain --untracked-files=all` 无输出。两个既有写入目标为已跟踪普通文件，新任务目录不存在；目标与父路径无 symlink、位于授权根内；`git check-ignore --no-index` exit 1、无输出。内存检查实际输出：

```text
PATH_SAFETY_OK 2 tracked regular files; new task directory absent; no symlinks; no ignore matches; origin/main matches HEAD
```

不联网、不安装、不执行 Git 写命令、不启动子代理或 advisor；不读取凭据或会话 jsonl，不打印环境变量，不写 active／handoff／ignore／身份。不落盘临时脚本或报告；Python 仅用 `python3 -B -c` 内存执行，命令前台完成。

## Book Gate Plan

| Gate | 客观触发／阶段 | 适用性与结果 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求前 | not-needed；未完整 grill，F 要求与独立任务边界明确 |
| book-ddia-data-design | schema、迁移、持久化机制设计前 | not-needed；仅核验既有文档，不改格式或持久化机制 |
| book-legacy-change-safety | 既有行为修改前 | not-needed；纯文档记录，无行为改动，历史字节保留 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；不改生产代码、不重构 |
| book-release-readiness | 运行时／部署变化，验证后 | not-needed；不发布、安装或部署，不改运行时 |

before-dev：身份、范围、前例、证据行、提交与路径安全已核对。check：执行真实 parser／history／index 与文档约束自检。finish-work：第 1 轮进入 checking，第 2 轮记录 done 并更新 plan 行。不触发独立复核条件：没有生产迁移、授权机制、全局配置、安装实现或跨系统接口修改；自核不是独立审阅。

## 验证与剩余边界

每条事件写入前单独执行 `TZ=Asia/Shanghai date '+%Y-%m-%dT%H:%M:%S+08:00'`，使用真实输出，不倒填。created_at 为第一条事件 at；第 1 轮 completed_at 保持 null，第 2 轮与 done 事件 at 同步。

Evidence Source：developer-local；Source Revision：dirty；基线 `cddf15e5116257b875c20d8eee8a8c96f844ede9`；Environment Alignment：unverified；Evidence Publication：local-only。本地文档检查不是本 PR tip CI 或运行时验收。

rtk：not-needed，采用约定原生命令。BDD：skipped，纯记录，无行为或 .feature 改动，语言与场景同步不适用；Cross-repo context／API Contract：not-needed；Mock Strategy：none。UI／E2E、平台性能／容量、构建、额外 lint／formatter、全量 CI 不运行：封闭文档范围且禁止额外产物与联网。Final Test Report／Run Summary MD：not-needed，仅在本任务保存本地核验结果，不建立正式报告。

编排方整理：第 1 轮写入后的工作树上，编排方在 uv 临时环境执行 `uv run --no-project --with pytest --with pyyaml --with jsonschema python -B -m pytest -q -p no:cacheprovider tests/test_workflow_contracts.py`，实际输出 `39 passed, 224 subtests passed in 0.53s`（2026-10-30T10:28:31+08:00）。本会话不运行 pytest，不把他方结果写成本会话通过。

R2.2 改前已实际执行 parser／history（exit 0），输出：

```text
ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/task.md in-progress False 55 None
HISTORY (None, True)
```

本会话逐个执行 `git log -1 --format='%H %cI %s' <sha>` 核实 R2.2 收口节所列 12 个提交，SHA／PR 号／主题全部一致；不把提交时间写成合入时间，不新增运行时测量。

### 第 1 轮 checking 阶段实际自检

1. 对两个 task.md 各执行一次下列命令，`<path>` 分别为 R2.2 与本任务的相对路径，均 exit 0：

   ```sh
   python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at')); from sbtd_task_state import TaskStore; print('HISTORY', TaskStore._history(d))" <path>
   ```

   ```text
   ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/task.md checking False 56 None
   HISTORY (None, True)
   ai/tasks/v2.1.0-rc.2-f-docs-backfill/task.md checking False 3 None
   HISTORY (None, True)
   ```

2. index 的只读候选命令：

   ```sh
   python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path('.'), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); print('INDEX_SAME', b==a, a==Path('ai/tasks/index.md').read_bytes())"
   ```

   写前实际输出 `INDEX_SAME False False`。以同样的 `_catalog()`／`_index_candidate` 计算候选，在内存命令中执行 `Path('ai/tasks/index.md').write_bytes(a)`，输出 `INDEX_WRITTEN True`。随后再次执行只读候选命令，exit 0，输出 `INDEX_SAME True True`。这三次 catalog 每次另输出 13 行 `旧格式事件，不追溯`，来自既有任务；两个本轮任务的 legacy_events 均为 False。

3. `python3 -B -c` 内存禁词检查：本任务全文为第一列计数；`git diff -U0 -- ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/task.md ai/tasks/index.md` 的新增行（不含文件头）为第二列。BAN 1–14 对应本轮禁词清单顺序，第 1 项不区分大小写，其余固定子串；额外路径前缀仅扫描本任务与 R2.2 新增行，额外归属短语扫描全部新增内容。实际输出，exit 0：

   ```text
   BAN 1 0 0
   BAN 2 0 0
   BAN 3 0 0
   BAN 4 0 0
   BAN 5 0 0
   BAN 6 0 0
   BAN 7 0 0
   BAN 8 0 0
   BAN 9 0 0
   BAN 10 0 0
   BAN 11 0 0
   BAN 12 0 0
   BAN 13 0 0
   BAN 14 0 0
   WORKSPACE 0 0
   GROUP_DECISION 0 0
   BAN_COUNTS_OK
   ```

4. `python3 -B -c` 读取 `git diff -U0 -- ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/task.md` 并筛选删除行，等价检查只删除旧 status／updated_at；另以 `git show HEAD:<path>` 对照原始字节，验证 R2.2 原有正文／表格／事件完整保留、只追加一条事件与末节。index 删除唯一 F 新导航行后与 HEAD 逐字节相等，且 R2.2 条目存在；plan.md 与 HEAD 逐字节相等。随后实际执行 `git diff --check` 与 `git status --porcelain --untracked-files=all`。整体 exit 0，输出：

   ```text
   -status: in-progress
   -updated_at: '2026-10-28T08:02:27+08:00'
   R22_HISTORY_BYTES_OK
   INDEX_TWO_ENTRIES_OK
   INDEX_EXACT_ONE_ADDITION_OK
   PLAN_BYTES_UNCHANGED
   DIFF_CHECK_OK exit 0; no output
    M ai/tasks/index.md
    M ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/task.md
   ?? ai/tasks/v2.1.0-rc.2-f-docs-backfill/task.md
   SCOPE_OK 3 files
   ```

以上结果仅证明本地文档约束；不替代 pytest、CI、Mac／Windows 测量或发布验收。所有待核实提交与 5 个文档行均匹配，没有因不符而省略的事实。此节只补记自检，不增加状态事件，不改变 updated_at 或 completed_at。

### done 前实际自检

第 2 轮在两个任务仍为 checking 时执行上述 parser＋history 命令及 index 只读候选命令；均 exit 0。parser／history 实际输出：

```text
ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/task.md checking False 56 None
HISTORY (None, True)
ai/tasks/v2.1.0-rc.2-f-docs-backfill/task.md checking False 3 None
HISTORY (None, True)
```

index 实际输出如下；13 条旧格式提示来自既有任务，两个本轮任务的 legacy_events 均为 False。候选字节一致，本轮未重写 index。

```text
旧格式事件，不追溯
旧格式事件，不追溯
旧格式事件，不追溯
旧格式事件，不追溯
旧格式事件，不追溯
旧格式事件，不追溯
旧格式事件，不追溯
旧格式事件，不追溯
旧格式事件，不追溯
旧格式事件，不追溯
旧格式事件，不追溯
旧格式事件，不追溯
旧格式事件，不追溯
INDEX_SAME True True
```

禁词／历史／范围检查采用 `python3 -B -c` 内存命令：F 全文与 `git diff HEAD -U0 --` 后接 R2.2、plan、index 三个路径的新增行分别计数；BAN 1–14 顺序同第 1 轮。历史正文与 `git show HEAD:<path>` 比较；R2.2 删除行仅限 frontmatter 三个状态字段，checking 时实际只删旧 status／updated_at。plan 全文件逐行比较仅第 23、26 行变化，并逐列断言仅约定单元格变化、8 列及 9 个竖线保持；index 仅增加 F 相对链接一行。

自检脚本两次断言失败均保留说明：首次错误地在 HEAD 正文末尾额外拼接一个换行；诊断输出 `HISTORY_BOUNDARY 210355 210355 True`、`TRAILING_NEWLINES 1 1`，改为原字节比较。第二次错误地用仓库根相对路径匹配 index 中相对链接；read 核实后改为实际相对链接。两次只修正内存检查表达式，没有因此改动文件。完成后的真实输出按执行顺序汇集如下；最后一段命令 exit 0：

```text
BAN 1 0 0
BAN 2 0 0
BAN 3 0 0
BAN 4 0 0
BAN 5 0 0
BAN 6 0 0
BAN 7 0 0
BAN 8 0 0
BAN 9 0 0
BAN 10 0 0
BAN 11 0 0
BAN 12 0 0
BAN 13 0 0
BAN 14 0 0
WORKSPACE 0 0
GROUP_DECISION 0 0
BAN_COUNTS_OK
R22_ALLOWED_DELETIONS 2
R22_HISTORY_BYTES_OK
PLAN_EXACT_ROWS_OK 23 26; 8 columns; 9 pipes
INDEX_EXACT_ONE_ADDITION_OK
DIFF_CHECK_OK exit 0; no output
 M ai/tasks/index.md
 M ai/tasks/v2.1.0-rc.2-plan/plan.md
 M ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/task.md
?? ai/tasks/v2.1.0-rc.2-f-docs-backfill/task.md
SCOPE_OK 4 files
PROTECTED_STAT_EMPTY
```

上面最后三项对应实际 `git diff --check`、`git status --porcelain --untracked-files=all` 与 `git diff --stat HEAD -- docs/prd sbtd-runtime contracts CHANGELOG.md CHANGELOG.zh.md ENTRYPOINT.md`；受保护路径 stat 无输出。done 写入后再执行同组自检，并检查 updated_at／completed_at／最后事件 at 一致；结果只在最终回复报告，不再写回本文件。

## 模型记录

编排方整理：下表模型与计数口径来自 executor 统计（据会话 jsonl）；第 1 轮全部 assistant 消息模型为 openai-codex/gpt-6-astra。本会话不读取会话文件、不自计最终次数；旧验收证据及第 1 轮自检中的「本会话」指第 1 轮，done 前自检为第 2 轮实际执行。

| 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | model_usage | 产出 |
|---|---|---|---|---|
| ping | openai-codex/gpt-6-astra（high） | 1／0（executor 统计） | 无 model_usage 记录（executor 统计） | 连通性确认 |
| main 第 1 轮 | openai-codex/gpt-6-astra（high） | 20／51（read 16、bash 20、todo 6、grep 4、edit 4、write 1；task 工具调用 0；executor 统计） | 无 model_usage 记录（executor 统计） | R2.2 checking、本任务建立、index 生成 |
| main 第 2 轮（本会话） | openai-codex/gpt-6-astra（high） | 本会话落盘时尚未结束，计数不在本文件自计；以编排方报告为准（executor 统计） | 本会话落盘时尚未结束，计数不在本文件自计；以编排方报告为准（executor 统计） | R2.2 与本任务 done、plan.md 两行同步 |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-30T10:22:54+08:00 | planned | planned | created：建立 strict 文档任务，仅核验既有文档与 F 行收口证据。 | 写入前单独执行 TZ=Asia/Shanghai date '+%Y-%m-%dT%H:%M:%S+08:00'；分支、基线、路径安全、前例、5 个文档行及引入提交已核实。 |
| 2026-10-30T10:24:11+08:00 | planned | in-progress | 开始整理 F 验收证据与两轮收口边界，不修改文档正文。 | 转换前单独执行 TZ=Asia/Shanghai date '+%Y-%m-%dT%H:%M:%S+08:00'；5 行 read／blame 一致，旧差异说明的引入与移除已核实，R2.2 已追加 checking 记录。 |
| 2026-10-30T10:24:27+08:00 | in-progress | checking | F 验收证据、独立任务边界与 Book Gate Plan 已记录，进入本地文档自检；本轮不写 done。 | 转换前单独执行 TZ=Asia/Shanghai date '+%Y-%m-%dT%H:%M:%S+08:00'；文档正文不变，接下来以 parser／history、生成器 index 候选与范围／历史保全／禁词扫描核验。 |
| 2026-10-30T10:33:12+08:00 | checking | done | 本地文档核验完成，按单轮约定在合入前记录 done。用户 2026-10-30 群内确认（F 行标记 done 并补记），Lord 记录。注：分钟不可考。编排方整理：按状态机约定在合入前记录 done。 | done 前 parser：R2.2 checking False 56 None、本任务 checking False 3 None；两者 HISTORY (None, True)；INDEX_SAME True True；禁词计数全部 0；R22_HISTORY_BYTES_OK；plan 仅第 23、26 两行且均 8 列；index 仅增一行；diff --check exit 0；SCOPE_OK 4 files；受保护路径 stat 空。pytest（编排方整理）：39 passed, 224 subtests passed in 0.53s（2026-10-30T10:28:31+08:00），非本会话执行。详见「done 前实际自检」。未提交、未合并；本 PR CI 尚待运行，审阅结果未知。 |
