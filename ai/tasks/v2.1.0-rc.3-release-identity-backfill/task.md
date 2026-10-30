---
schema_version: 1
id: v2.1.0-rc.3-release-identity-backfill
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：strict；omp 为唯一内容 writer，不启动子代理或 advisor；提交、推送与开 PR 由编排方执行
status: done
branch: docs/v2.1.0-rc.3-release-identity-backfill
created_at: '2026-10-30T08:20:02+08:00'
updated_at: '2026-10-30T08:23:14+08:00'
completed_at: '2026-10-30T08:23:14+08:00'
---

# v2.1.0-rc.3 发布身份补记与 ENTRYPOINT Graft 版本同步

## 目标与归属

补记 rc.3 已有发布身份，按 rc.2 逐句镜像中英文发布段；仅同步 ENTRYPOINT 四处版本，保留 #198 历史句，建立 strict 单轮 planned → in-progress → checking → done 记录与生成器导航。

用户 2026-10-30 群内决定（预发布算已发布的 SBTD workflow 版本，同步 ENTRYPOINT 的 Graft 版本到 0.28.0），Lord 记录。注：分钟不可考。

用户 2026-10-30 群内决定（本轮文档在本地自检完成后按 planned → in-progress → checking → done 落盘，done 在合入前记录），Lord 记录。注：分钟不可考。

未完整调用 grill-with-docs：路径、逐字改动、发布事实、归属与验收条件明确，无领域歧义。done 仅表示本地文档工作完成与上述决定，不代表发布、合入、PR CI 或独立审阅。本 PR CI 尚待运行，未合并；审阅结果未知。

## 范围与写入安全

仅以下五个文件：

1. `CHANGELOG.md`：rc.3 标题后新增一段发布身份及空行。
2. `CHANGELOG.zh.md`：逐项等价中文段落。
3. `ENTRYPOINT.md`：基线第 25、91、239、330 行的 0.22.0 改为 0.28.0，其余字节不变。
4. `ai/tasks/v2.1.0-rc.3-release-identity-backfill/task.md`：本任务与实际证据。
5. `ai/tasks/index.md`：仅写生成器候选字节，新增一行导航。

写前分支为 `docs/v2.1.0-rc.3-release-identity-backfill`，HEAD 与本地 origin/main 均为 `6390705037caf281a63834a1c72eabace49ebeef`，`git status --porcelain` 无输出。四个既有目标均已跟踪、为普通文件，新任务此前不存在；目标及父路径无 symlink、均位于授权根内；`git check-ignore --no-index` exit 1、无输出。实际检查输出 `PATH_SAFETY_OK 4 tracked regular files; new task absent; no symlinks; no ignore matches`。

沿用前例手写 task，不调用 TaskStore 写方法；使用真实 TaskDocument parser、只读 `_history` 与 `TaskStore(Path.cwd(), read_only=True)` 的 `_catalog`／`_index_candidate` 核验，不声称 helper 状态转换或自动恢复已执行。已全文阅读两个前例，并阅读 parser 的 frontmatter／事件表、状态转换、completed_at、history、catalog 与 index candidate 实现。done 为终态；最终 updated_at = completed_at = done 事件 at。

不联网、不安装、不执行 Git 写命令、不操作 tag／Release、不提交或推送；不读取凭据、不打印环境变量、不读取或统计会话 jsonl。main 启动时 omp 工具白名单不含 task 工具（子代理禁用）；本轮不启动子代理或 advisor。Python 均用 `python3 -B`；不落盘临时脚本或额外报告，不写 active／handoff／ignore／身份。

## 发布事实与证据来源

编排方据 gh／git 核实：

- annotated tag `v2.1.0-rc.3`：tag 对象 `1715486dfb6da359d6ec6646e923a70795e4a8fd`，指向提交 `ce37b6d5d7487109a92856c7a2c41a8f86efdfba`，tagger 时间 `2026-10-29T21:20:12+08:00`。
- 编排方据 gh 核实：[Release v2.1.0-rc.3](https://github.com/KunoLu/640-skills/releases/tag/v2.1.0-rc.3) 为 prerelease（isPrerelease true，isDraft false），未标 Latest；releases/latest 为 `v2.0.2`；发布时间 `2026-10-29 21:20:20 (UTC+8)`。
- 编排方据 gh 核实：精确提交 CI run [40868198008](https://github.com/KunoLu/640-skills/actions/runs/40868198008)，headSha `ce37b6d5d7487109a92856c7a2c41a8f86efdfba`，attempt 1，conclusion success。13/13 作业按名称 success：dashboard-artifacts、linux-full、linux-shards (1)、linux-shards (2)、linux-shards (3)、macos-bash-installer、runtime-e2e-macos、runtime-e2e-windows、windows-powershell-installer、windows-shards (1)、windows-shards (2)、windows-shards (3)、windows-shards (4)。各平台测试计数未采集（unknown）。

编排方执行的核实命令清单（本会话不联网，不执行 gh 或 ls-remote）：

```sh
git ls-remote --tags origin
git cat-file -t v2.1.0-rc.3
git cat-file -p v2.1.0-rc.3
gh release view v2.1.0-rc.3 --json tagName,isPrerelease,isDraft,publishedAt,url
gh api repos/KunoLu/640-skills/releases/latest
gh run view 40868198008 --json headSha,attempt,conclusion,status,jobs
```

本会话本地只读复核：`git rev-parse v2.1.0-rc.3` 输出上述 tag 对象，`git rev-parse 'v2.1.0-rc.3^{commit}'` 输出上述完整提交；`git cat-file -t v2.1.0-rc.3` 输出 `tag`；`git cat-file -p v2.1.0-rc.3` 的 object 与上述提交一致，tagger epoch 为 `1793280012 +0800`。这些只证明本地 tag，不替代远端 Release／CI 核验。已有提交 CI 不覆盖本 PR 改动。

## ENTRYPOINT pin 依据与历史保留

- `sbtd-workflow-onboard/scripts/graft_runtime.py:50`：`GRAFT_PINNED_VERSION = "0.28.0"`。
- `sbtd-workflow-onboard/assets/graft-build-policy.json`：`"version":"0.28.0"`。
- `git log -1 --format='%H %s' -- sbtd-workflow-onboard/scripts/graft_runtime.py` 输出 `4093baf616146062525b95643f70d55ead5c9a02 chore: 受管 Graft pin 晋升 0.22.0 → 0.28.0（Trail-code 时代） (#198)`。
- 改前 `git grep -n '0\.22\.0' -- ENTRYPOINT.md` 恰为第 25、91、239、330 行；首尾为 `v0.22.0`，中间两行为 `@nanonets/graft@0.22.0`。只替换这四处，不改策略或重新运行 Graft。
- 两份 CHANGELOG 基线第 20 行 #198 历史句逐字节保留；新增发布段不含版本同步内容。

改前 `git grep -l '0\.22\.0'` 除 ENTRYPOINT 外列出以下文件。它们的旧版本历史内容全部保留；两份 CHANGELOG 仅新增发布段，index 仅新增导航，其余文件完全不动：

- `CHANGELOG.md`
- `CHANGELOG.zh.md`
- `ai/tasks/graft-pin-0.22.0/check.md`
- `ai/tasks/graft-pin-0.22.0/cutover.md`
- `ai/tasks/graft-pin-0.22.0/global-consolidation.md`
- `ai/tasks/graft-pin-0.22.0/review.md`
- `ai/tasks/graft-pin-0.22.0/task.md`
- `ai/tasks/graft-trail-code-upgrade-eval/eval-report.md`
- `ai/tasks/graft-trail-code-upgrade-eval/task.md`
- `ai/tasks/index.md`
- `docs/lessons/topics/repository-workflow.md`
- `docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.1.md`
- `docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md`
- `tests/test_sbtd_upgrade_hosts.py`

## Book Gate Plan

| Gate | 客观触发／阶段 | 适用性与结果 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求前 | not-needed；未完整 grill，既有事实与文档边界明确 |
| book-ddia-data-design | schema、迁移、持久化机制设计前 | not-needed；不改数据格式或持久化机制 |
| book-legacy-change-safety | 既有行为修改前 | not-needed；纯文档，无行为改动，历史字节保留 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；不改生产代码、不重构 |
| book-release-readiness | 运行时／部署变化，验证后 | not-needed；仅补记已发布事实与文档版本，不发布、安装或部署 |

before-dev：身份、范围、前例、源码 pin 与安全检查已完成。check：运行文档真实 parser／history／index 与约定测试，结果记录于下节。finish-work：验收后以真实时间追加 done，保留未合并、PR CI 尚待运行的边界。不触发独立复核条件：没有生产迁移、授权机制、全局配置、安装实现或跨系统接口修改；自核不是独立审阅。

## 验证与剩余边界

每条状态事件 at 均来自写入前单独执行 `TZ=Asia/Shanghai date '+%Y-%m-%dT%H:%M:%S+08:00'` 的真实输出，不以发布或合入时间代替。创建时间为 `2026-10-30T08:20:02+08:00`。

Evidence Source：developer-local；Source Revision：dirty；基线 `6390705037caf281a63834a1c72eabace49ebeef`；Environment Alignment：unverified；Evidence Publication：local-only。本地自检不是本 PR tip CI 或运行时验收。

rtk：not-needed，采用约定原生命令。BDD：skipped，纯文档，无行为或 .feature 改动，语言与场景同步不适用；Cross-repo context／API Contract：not-needed；Mock Strategy：none。UI／E2E、平台性能／容量、构建、额外 lint／formatter、全量 CI 不运行：封闭文档范围且禁止额外产物与联网。Final Test Report／Run Summary MD：not-needed，仅在本任务保存本地原生命令输出，不建立正式报告。未关闭 R2.2，不声称发布就绪或自动恢复可靠。

### checking 阶段实际自检

1. parser 与只读 history 命令（exit 0）：

   ```sh
   python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at')); from sbtd_task_state import TaskStore; print('HISTORY', TaskStore._history(d))" ai/tasks/v2.1.0-rc.3-release-identity-backfill/task.md
   ```

   ```text
   ai/tasks/v2.1.0-rc.3-release-identity-backfill/task.md checking False 3 None
   HISTORY (None, True)
   ```

2. index 先生成候选，实际输出 `INDEX_SAME False False`；仅将候选所需的导航行写入，随后用下方原生命令核对全文件字节，exit 0，输出 `INDEX_SAME True True`。catalog 同时输出 13 行「旧格式事件，不追溯」，来自既有任务；本任务 legacy_events 为 False。

   ```sh
   python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); print('INDEX_SAME', b==a, a==Path('ai/tasks/index.md').read_bytes())"
   ```

3. `python3 -B -c` 内存检查：从 HEAD 两份 rc.2 发布段仅替换版本、tag 对象、提交 SHA 与 CI run，构造 rc.3 新段；断言当前全文等于 HEAD 在标题后插入该段与空行的结果，基线第 20 行现位于第 22 行且字节相同。双语链接、版本、SHA 与代码标识多重集合一致；源码预发布边界句逐字沿用。ENTRYPOINT 全文等于 HEAD 仅四处版本替换；index 删除唯一新导航行后等于 HEAD。禁词检查覆盖本任务全文及全部五文件新增行（含未跟踪 task 全文）；首项不区分大小写，其余固定子串。实际输出（exit 0）：

   ```text
   CHANGELOG_EXACT_INSERT_OK CHANGELOG.md +2 -0; BASELINE_LINE20_BYTES_OK; FORBIDDEN_RELEASE_TERMS 0
   CHANGELOG_EXACT_INSERT_OK CHANGELOG.zh.md +2 -0; BASELINE_LINE20_BYTES_OK; FORBIDDEN_RELEASE_TERMS 0
   BILINGUAL_RELEASE_IDENTIFIERS_OK; RC2_BOUNDARY_SENTENCES_EXACT
   ENTRYPOINT_EXACT_OK lines=25,91,239,330 +4 -4
   ENTRYPOINT_OLD_VERSION_COUNT 0; git grep exit 1
   INDEX_EXACT_ONE_ADDITION_OK
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
   BAN_COUNTS_OK 14 x 2 = 28 zero counts; TASK_PATH_PREFIX 0
   DIFF_CHECK_OK exit 0; no output
   GIT_STATUS_BEGIN
    M CHANGELOG.md
    M CHANGELOG.zh.md
    M ENTRYPOINT.md
    M ai/tasks/index.md
   ?? ai/tasks/v2.1.0-rc.3-release-identity-backfill/task.md
   GIT_STATUS_END
   SCOPE_OK 5 files; DOCUMENT_SELF_CHECK_OK
   ```

4. 已实际执行 `python3 -B -m pytest -q -p no:cacheprovider tests/test_workflow_contracts.py`，exit 1。错误原文的消息部分为 `No module named pytest`（解释器绝对路径按记录约束省略）。环境缺少 pytest，测试未运行，不安装依赖；不将此结果写成测试通过。Targeted Rerun：not-needed，非测试用例失败；Final Full Rerun：blocked，缺测试运行器。其余文档检查通过不替代此测试。

5. done 以本地文档验收与上述群内决定为依据，按约定记录测试缺依赖例外；本 PR CI 尚待运行，未合并，审阅结果未知。done 写入后再次执行同组只读自检，最终复核结果随交付列出。

### done 后实际复核

done 落盘后已再次运行上述 parser／history、index、完整内存文档约束与 pytest 命令。前三项 exit 0；文档约束逐行输出与 checking 阶段一致，仍为五个授权文件，禁词及路径前缀计数均为 0，`git diff --check` 无输出。新增状态验证的实际输出：

```text
ai/tasks/v2.1.0-rc.3-release-identity-backfill/task.md done False 4 2026-10-30T08:23:14+08:00
HISTORY (None, True)
DONE_TIMESTAMPS_MATCH 2026-10-30T08:23:14+08:00
INDEX_SAME True True
```

index catalog 仍输出 13 行既有任务的「旧格式事件，不追溯」。pytest 再次 exit 1，错误消息仍为 `No module named pytest`；测试未运行，不冒称通过。未生成报告、未安装依赖、未提交或合并。本节只记录复核结果，不新增状态事件，不改变 done 时间；最终落盘再核验文档记录与范围。

## 模型记录

| 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | model_usage | 产出 |
|---|---|---|---|---|
| ping | openai-codex/gpt-6-astra（high） | 1／0（编排方据会话 jsonl 统计（executor-counted）） | 无 model_usage 记录（编排方据会话 jsonl 统计（executor-counted）） | 连通性记录；本轮不读取会话文件 |
| main（本会话） | openai-codex/gpt-6-astra（high） | 本会话落盘时尚未结束，计数不在本文件自计；以编排方报告为准（executor-counted） | 本会话落盘时尚未结束，计数不在本文件自计；以编排方报告为准（executor-counted） | 五文件文档同步与本地自检 |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-30T08:20:02+08:00 | planned | planned | created：建立 strict 文档任务，限定五个文件。 | 写入前单独执行 TZ=Asia/Shanghai date '+%Y-%m-%dT%H:%M:%S+08:00'；分支、HEAD、干净工作区、路径安全与前例已核对。 |
| 2026-10-30T08:21:02+08:00 | planned | in-progress | 开始插入双语发布段并同步 ENTRYPOINT 四处版本。 | 转换前单独执行 TZ=Asia/Shanghai date '+%Y-%m-%dT%H:%M:%S+08:00'；本地 tag、#198 pin 与四处旧版本均已核对，Release／CI 来源与边界已记录。 |
| 2026-10-30T08:21:47+08:00 | in-progress | checking | 双语发布段与四处版本已写入，进入最终本地检查。 | 转换前单独执行 TZ=Asia/Shanghai date '+%Y-%m-%dT%H:%M:%S+08:00'；生成器输出 INDEX_SAME False False，按候选内容仅新增本任务导航，随后核验字节一致性。 |
| 2026-10-30T08:23:14+08:00 | checking | done | 本地文档自检完成，按单轮约定在合入前记录 done。用户 2026-10-30 群内决定（本地自检完成后记录 done），Lord 记录。注：分钟不可考。 | 写入前单独执行 TZ=Asia/Shanghai date '+%Y-%m-%dT%H:%M:%S+08:00'；parser checking False 3 None、HISTORY (None, True)、INDEX_SAME True True；精确字节约束、14 项禁词与路径前缀计数、五文件范围及 diff --check 均通过；pytest 命令 exit 1，No module named pytest，按缺依赖例外记录未运行，未安装。未提交、未合并；本 PR CI 尚待运行，审阅结果未知，不以已发布提交 CI 冒充本 PR 验证；done 后复跑同组只读检查。 |
