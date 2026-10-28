---
schema_version: 1
id: v2.1.0-rc.2-tag-backfill
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：strict；omp 为唯一内容 writer，不启动子代理或 advisor；提交、推送与开 PR 由编排方执行
status: done
branch: docs/v2.1.0-rc.2-tag-backfill-d9
created_at: '2026-10-28T08:03:26+08:00'
updated_at: '2026-10-28T08:31:20+08:00'
completed_at: '2026-10-28T08:31:20+08:00'
---

# rc.2 tag 发布事实补记与 R2.2 D9 记录

## 目标

补记 `v2.1.0-rc.2` annotated tag、Release 与精确提交 CI 的既有发布事实，追加 R2.2 D9 群内记录，并记录本 PR 的 strict 范围、本地自检与剩余边界。只做文档补记，不执行发布，不以 D9 视觉记录替代性能／规模／容量证据，不关闭 R2.2。

## 决定与归属

用户 2026-10-28 群内指示开本 PR，Lord 记录。
注：分钟不可考。

范围限制与 checking → done 两步写法为 Lord 2026-10-28 群内裁定。
注：分钟不可考。

编排方整理：第 1 轮进入 checking；done 在第 2 轮按上述裁定写入，依据见状态事件。未完整调用 grill-with-docs，因三个授权路径、逐字事实、追加规则与验收条件明确，无领域歧义。事实仅来自本任务提示与仓库，不联网补查，不读取或统计会话 jsonl。

## 范围与边界

仓库内恰好三个文件：

1. `ai/tasks/v2.1.0-rc.2-tag-backfill/task.md`：新建本 PR 的任务、归属、发布事实与验证记录。
2. `ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/task.md`：仅更新 frontmatter 的 updated_at、在主状态事件表末尾追加一条同状态事件、在文件末尾追加 D9 与状态判定；其余历史字节不动。
3. `ai/tasks/v2.1.0-rc.2-e-prerelease/task.md`：仅文件末尾追加发布后补记；frontmatter 与三条状态事件不动。

不改 CHANGELOG.md／CHANGELOG.zh.md／openapi／contracts／tests／PRD／ADR／plan.md／ai/tasks/index.md／源码／其他 task.md，不改版本号，不碰 tag／Release。不写仓库外文件，不建临时文件、临时脚本或报告；不调用子代理、task 工具或 advisor；不执行 gh、git 写操作、联网、安装依赖或构建；不打印环境变量、不读凭据文件；Python 命令均加 `-B`。

沿用 E 模板手写记录，未经 TaskStore 写入；只运行真实 parser 与只读 `_history` 一致性逻辑，不写 active／index／handoff／ignore／身份。历史 task 的分支字段保留，本轮仅按明确授权追加，不声称 helper rebind 或自动恢复成功。

写前核对：本 worktree 分支为 `docs/v2.1.0-rc.2-tag-backfill-d9`，HEAD 为 `e45565aa940f41bb42c3a62d00921b505f2caa30`，`git status --porcelain` 无输出。两个既有目标全文已通读，新文件此前不存在；三个目标及父路径无 symlink，既有目标为普通文件；`git check-ignore --no-index` 对三个目标均 exit 1、无输出，两个既有目标均已跟踪，新目标未跟踪。

## #140 先例对照

#140 先例（编排方只读核对 `gh pr view 140 --json files` 与 `gh pr diff 140`）：#140 只改 `CHANGELOG.md` 与 `CHANGELOG.zh.md` 两个文件（各 +6／−4）：把 `## Unreleased`／`## 未发布` 改为 `## v2.1.0-rc.1 (2026-10-17)`／`## v2.1.0-rc.1（2026-10-17）`，新增一段发布说明（Release 链接、未标 Latest、annotated tag 指向的完整 SHA、精确提交 CI 链接与作业数），并调整条目分类。按 Lord 2026-10-28 群内裁定，本 PR 不改 CHANGELOG 已发布内容、版本号、openapi、PRD、plan.md、tag、Release；因此 #140 先例要求的 CHANGELOG 改动（章节改名与日期、发布段、tag SHA、CI 链接）本 PR 均不执行，留待用户决定。当前 main 上两份 CHANGELOG 的 rc.2 内容仍位于 `## Unreleased`／`## 未发布` 下。
注：分钟不可考。

上述 gh 操作为既有先例核对事实，本会话未执行。仓库当前两份 CHANGELOG 的第 10 行分别为 `## Unreleased`／`## 未发布`。本 PR 不执行的清单：章节改名与日期、发布说明段、tag SHA、精确提交 CI 链接；不借补记改变条目分类。

## 发布事实

编排方整理：

- annotated tag `v2.1.0-rc.2`：tag 对象 `77a7cce8176a28e1868e2bac9f7c0b9f2d896702`，指向提交 `e45565aa940f41bb42c3a62d00921b505f2caa30`（PR #192 squash 合入 main 的提交），tagger 时间 `2026-10-28T07:41:16+08:00`。
- GitHub Release [v2.1.0-rc.2](https://github.com/KunoLu/640-skills/releases/tag/v2.1.0-rc.2)：prerelease，未标 Latest；v2.0.2 仍为 Latest；发布时间 2026-10-28 07:41:18 (UTC+8)。
- 该精确提交的 CI：run [40602350203](https://github.com/KunoLu/640-skills/actions/runs/40602350203)，workflow `validation`，event `push`，branch main，attempt 1，conclusion `success`，2026-10-28 07:40:45 (UTC+8) 完成；按名称 13/13 作业 success：dashboard-artifacts、linux-full、linux-shards (1)、linux-shards (2)、linux-shards (3)、macos-bash-installer、runtime-e2e-macos、runtime-e2e-windows、windows-powershell-installer、windows-shards (1)、windows-shards (2)、windows-shards (3)、windows-shards (4)。各平台测试计数 unknown（未采集）。

这些是既有发布事实，不是本 PR 新运行的 CI；不以 main 精确提交的成功结果冒充本 PR tip 的验证。

## D9 与 R2.2 状态判定

编排方整理：用户 2026-10-27 群内确认（核验清单 v3 第 1–7 步：暗/浅主题，HTML/JPEG/PDF/CSV），Lord 记录（注：分钟不可考。）；据 Lord 群内记录，这七步在 MacBook Air 上全部通过。字体／长页／分页视觉属于第 1–7 步范围，用户 2026-10-27 群内确认已覆盖，Lord 记录（注：分钟不可考。）。Mac 视觉相关项中仅 Mac 上 JPEG／PDF 字节数仍未验证，核验清单 v3 本身不含字节检查。

两段逐字片段来自 `CHANGELOG.zh.md:49`，是群内记录，不是仓库内测量或 CI 证据，本 PR 未核实用户实际执行的清单。R2.2 原表及既有事件是历史记录，不改写；D9 行与「Mac 上 JPEG／PDF 字节数、字体／长页／分页视觉」行的视觉／字体部分由新追加节覆盖，字节数仍未验证。

判定依据：R2.2 task 基线 :20-27「范围与验收」，其中 PR-4 §18 性能、默认配额容量校准与 R2.2 收尾在 :27（提示定位为 :25）；基线 :1263-1271「R2.2 PR-4 完成项与阻塞项」表。D9 记录已有，但 macOS 实机性能、Mac 上 JPEG／PDF 字节数、原生 Windows 性能、百万事件／1万任务／10万步骤及百万CSV、完整四格式容量／平台资源上限／最大长图CSV规模仍为 pending 未验证，完成条件未满足。R2.2 保持 `status: in-progress`、`completed_at: null`，不加 checking／done 事件，plan R2.2 行不改；R2.2 收尾仍 pending。主状态事件新增一行后，原阻塞表顺延一行，引用使用编辑前基线行号。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮适用性与结果 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求前 | not-needed；仅补记既有事实，未完整 grill，范围与归属明确 |
| book-ddia-data-design | schema、迁移或持久化机制设计前 | not-needed；不改数据格式或持久化机制，仅追加文档记录 |
| book-legacy-change-safety | 既有行为修改前 | not-needed；无行为修改，历史正文与事件保留 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；不改生产代码，不做重构 |
| book-release-readiness | 运行时或部署变化，验证后 | not-needed；仅补记既有发布事实，不操作 tag／Release，不执行部署，不声称本 PR 发布就绪 |

## 验证与剩余边界

- 时间均来自写入对应行前单独执行 `TZ=Asia/Shanghai date -Iseconds` 的实际输出：T2 为 `2026-10-28T08:02:27+08:00`，用于 R2.2 同状态事件与 updated_at；T1 为 `2026-10-28T08:03:26+08:00`，用于本任务建立事件与 created_at。本轮先追加 R2.2、E，再建立本任务。
- 修改前在仓库根运行下列 parser 命令，R2.2 实际输出 `ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/task.md in-progress False 54 None`，exit 0。

  ```sh
  python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" <path>
  ```

- 已用 `grep -F` 对 `CHANGELOG.zh.md` 第 49 行分别检查片段 A、B，实际输出 `CHANGELOG.zh.md:49 A grep -F exit 0` 与 `CHANGELOG.zh.md:49 B grep -F exit 0`。首次内存检查因换行转义产生 Python SyntaxError，未执行检查、未写文件；修正内存命令后两项通过，不改源文档迎合检查。
- 三文件写入后按上方命令各运行一次 parser：本任务 `in-progress False 1 None`，R2.2 `in-progress False 55 None`，E `done False 3 2026-10-28T02:08:01+08:00`，均 exit 0。R2.2 主状态事件从修改前 54 条变为 55 条，恰增一条。
- 只读调用 `TaskStore._history(TaskDocument.parse(...))`，未实例化 TaskStore，三个文件实际均为 `history consistent = True`。历史字节检查输出 `HISTORY_BYTES_OK; deleted lines: R2 updated_at only; E additions only`：E 原文件为当前文件逐字节前缀；R2.2 去掉唯一新事件并还原 updated_at 后，原文件为逐字节前缀。原 frontmatter 其余字段、历史事件与阻塞表保留。
- 片段 A、B 对 `CHANGELOG.zh.md:49` 各执行一次 `grep -F`，对本任务及 R2.2 各执行两次 `grep -F`，六项均 exit 0；两个目标中的片段均与源行逐字一致。
- `git status --porcelain` 实际输出如下；另用 `--untracked-files=all` 展开新目录，恰为范围节三个 task.md，无其他路径。`git diff --check` exit 0、无输出；删除行仅 R2.2 的旧 updated_at 一行，E 只有新增行。

  ```text
   M ai/tasks/v2.1.0-rc.2-e-prerelease/task.md
   M ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/task.md
  ?? ai/tasks/v2.1.0-rc.2-tag-backfill/
  ```

- 禁词检查范围为本文件全文，以及 R2.2／E 的 `git diff -U0 -- <file>` 经 `grep '^+'`、`grep -v '^+++'` 取得的新增行。首项大小写不敏感，其余固定子串计数，另查无日期的用户分钟归属；17 项 × 3 范围共 51 个计数均为 0。实际输出 `BAN_COUNTS_OK 17 x 3 = 51 zero counts` 与 `DOCUMENT_SELF_CHECK_OK`，exit 0。下表用 Unicode 码点表示禁用项，不把码点文本算作命中。

| 禁用项（Unicode 码点） | 本文件全文 | R2.2 新增行 | E 新增行 |
|---|---|---|---|
| 1：U+0063 U+006F U+006E U+0066 U+0069 U+0072 U+006D U+0065 U+0064 | 0 | 0 | 0 |
| 2：U+7528 U+6237 U+6307 U+5B9A | 0 | 0 | 0 |
| 3：U+5DE6 U+53F3 | 0 | 0 | 0 |
| 4：U+540E U+7EED U+56DE U+586B | 0 | 0 | 0 |
| 5：U+0076 U+0069 U+0074 U+0065 U+0073 U+0074 | 0 | 0 | 0 |
| 6：U+002F U+0068 U+006F U+006D U+0065 U+002F U+0062 U+006F U+0078 | 0 | 0 | 0 |
| 7：U+007E U+002F | 0 | 0 | 0 |
| 8：U+8FBE U+6807 | 0 | 0 | 0 |
| 9：U+7528 U+6237 U+63D0 U+4F9B | 0 | 0 | 0 |
| 10：U+672C U+6B21 U+4EFB U+52A1 U+63D0 U+4F9B U+7684 | 0 | 0 | 0 |
| 11：U+7F16 U+6392 U+65B9 U+8F6C U+8FF0 | 0 | 0 | 0 |
| 12：U+7528 U+6237 U+6240 U+6307 | 0 | 0 | 0 |
| 13：U+7F16 U+6392 U+65B9 U+63D0 U+4F9B U+7684 | 0 | 0 | 0 |
| 14：U+0043 U+006F U+0064 U+0065 U+0058 U+0020 U+7FA4 U+5185 U+8865 U+5145 | 0 | 0 | 0 |
| 15：U+002F U+0077 U+006F U+0072 U+006B U+0073 U+0070 U+0061 U+0063 U+0065 | 0 | 0 | 0 |
| 16：U+7F16 U+6392 U+65B9 U+63D0 U+4F9B | 0 | 0 | 0 |
| 17：U+7528 U+6237 后直接接空白及无日期的两位分钟时间 | 0 | 0 | 0 |

- 完成正文、验证记录写入及上述自检后，单独执行 `TZ=Asia/Shanghai date -Iseconds`，实际输出 `2026-10-28T08:05:52+08:00`，用于 checking 事件与 updated_at；本任务两条事件时间单调不减。checking 落盘后再次运行同一组只读检查，三个 parser 实际输出如下，均 exit 0：

  ```text
  ai/tasks/v2.1.0-rc.2-tag-backfill/task.md checking False 2 None
  ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/task.md in-progress False 55 None
  ai/tasks/v2.1.0-rc.2-e-prerelease/task.md done False 3 2026-10-28T02:08:01+08:00
  ```

- checking 后复核：三个文件仍均 `history consistent = True`；历史字节检查通过；A、B 六项 `grep -F` 均 exit 0；17 项 × 3 范围计数均 0；两种 git status 输出与上方一致；`git diff --check` exit 0、无输出；最终输出 `DOCUMENT_SELF_CHECK_OK`。这些结果仅证明文档解析、事件链与本次变更约束，不证明未测性能或本 PR CI。
- 编排方整理：第 1 轮提交 `5defaab4dfaa0c95456f297c990077ef6b682f1d` 的 run [40606793366](https://github.com/KunoLu/640-skills/actions/runs/40606793366) attempt 1 13/13 按名称 success，2026-10-28 08:28:11 (UTC+8) 完成；done 提交 tip 的 CI 以 done 提交 tip 的 CI 为准。D9 外性能／规模／容量 pending 项未验证，未在本轮重测；两份 CHANGELOG 的发布章节改动留待用户决定。
- Evidence Source：developer-local；Source Revision：dirty；Environment Alignment：unverified；Evidence Publication：local-only。基线完整 SHA 为 `e45565aa940f41bb42c3a62d00921b505f2caa30`，验证对象为本 worktree 的文档改动，不是正式 CI／发布验收报告。
- rtk：not-needed，采用约定原生命令；Final Test Report／Run Summary MD：not-needed，不创建额外报告文件。BDD：skipped，仅文档、无 .feature 或行为变化；Cross-repo context／API Contract：not-needed；Mock Strategy：none。未运行单元／集成／Web／Mobile E2E、构建、额外 lint／formatter 或全量 CI；没有代码变化，且禁止文件副作用、构建与联网。独立 review：not-needed，单一文档记录范围，不触发严格独立复核条件；未调用子代理或 advisor，不冒称独立审查。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | model_usage | 产出 |
|---|---|---|---|---|---|
| 1 | ping 第 1 次 | openai-codex/gpt-6-astra（high） | 1／0（2026-10-28 07:59:59 (UTC+8) 开始，编排方据会话 jsonl 统计（executor-counted）） | 0 | 连通性检查 |
| 2 | main 第 1 次（2026-10-28 08:01:11 (UTC+8) 开始） | openai-codex/gpt-6-astra（high） | 22／47（编排方据会话 jsonl 统计（executor-counted）） | 0 | 三个文件的全部内容修改与本地自检 |
| 3 | main 第 1 次内部辅助 | typesafe/jev-latest（purpose find） | —（不计入 main 与 ping） | 24（编排方据会话 jsonl 统计（executor-counted）） | omp 内部检索辅助调用 |
| 4 | ping 第 2 次 | openai-codex/gpt-6-astra（high） | 1／0（2026-10-28 08:29:42 (UTC+8) 开始，编排方据会话 jsonl 统计（executor-counted）） | 0 | 连通性检查 |
| 5 | main 第 2 次（本会话，done 提交） | openai-codex/gpt-6-astra（high） | 本会话落盘时尚未结束，计数不在本文件自计；以编排方报告为准（executor-counted） | 以编排方报告为准 | done 事件、frontmatter、CI 结果与模型表补记 |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-28T08:03:26+08:00 | planned | in-progress | 编排方整理：按明确的 strict 文档范围建立本任务，由 omp 唯一写入。 | 开始写本文件前单独执行 TZ=Asia/Shanghai date -Iseconds 的实际输出；分支、基线、干净工作区与目标路径已核对；未经 TaskStore 写入。 |
| 2026-10-28T08:05:52+08:00 | in-progress | checking | 编排方整理：本地自检完成，进入 checking；本 PR 的 CI 尚待运行，不标完成。 | 转换前本任务 parser 为 in-progress False 1 None；落盘后复核为 checking False 2 None；R2.2 in-progress False 55 None；E done False 3 2026-10-28T02:08:01+08:00；三个 history consistent = True；17 项 × 3 范围禁词计数均 0；git status 仅两个授权修改文件与新任务目录，展开后恰为三个 task.md；git diff --check exit 0、无输出；历史字节保留、唯一删除行为 R2.2 旧 updated_at；片段 A、B 六项 grep -F 均 exit 0；DOCUMENT_SELF_CHECK_OK。 |
| 2026-10-28T08:31:20+08:00 | checking | done | 编排方整理：第 1 轮提交 CI 13/13 按名称全绿，按 Lord 裁定以 checking → done 两步写法提交 done commit（Lord 归属：日期 2026-10-28，注：分钟不可考。） | 在 done 提交中补记：第 1 轮提交 `5defaab4dfaa0c95456f297c990077ef6b682f1d`（编排方 commit 并普通 push，非 force、非 amend），PR [#193](https://github.com/KunoLu/640-skills/pull/193)（base main，未合并）；该 SHA 的 CI：run [40606793366](https://github.com/KunoLu/640-skills/actions/runs/40606793366)，workflow `validation`，event `pull_request`，attempt 1，conclusion `success`，2026-10-28 08:28:11 (UTC+8) 完成；按名称 13/13 作业 success：dashboard-artifacts、linux-full、linux-shards (1)、linux-shards (2)、linux-shards (3)、macos-bash-installer、runtime-e2e-macos、runtime-e2e-windows、windows-powershell-installer、windows-shards (1)、windows-shards (2)、windows-shards (3)、windows-shards (4)。本 PR 无 Reviewy 审阅记录；done 依据为 CI 与 Lord 群内裁定的 checking → done 两步写法（Lord 归属：日期 2026-10-28，注：分钟不可考。），不是审阅 CLEAN。该 CI 仅适用于 `5defaab`，不适用于本 done 提交，done 提交 tip 的 CI 以 done 提交 tip 的 CI 为准；未合并；R2.2 仍 in-progress。 |

以上保留 planned → in-progress 与 in-progress → checking 两条既有事件，并在 done 提交中补记 checking → done 转换；完成依据见 done 事件；未合并。
