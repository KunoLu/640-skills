---
schema_version: 1
id: v2.1.0-rc.2-f-backfill
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：strict；本会话为唯一 writer 与 git 提交者；不启动子代理、不用 advisor；push 与开 PR 由编排方在 omp 之外执行
status: in-progress
branch: docs/v2.1.0-rc.2-f-backfill
created_at: '2026-10-25T00:59:09+08:00'
updated_at: '2026-10-25T01:04:21+08:00'
completed_at: null
---

# rc.2 F 回填：#168–#172 修复轮次记录补正

## 决定

- 编排方整理：#172 合入（`4752346`）后，把 #168–#172 修复轮次中因 PRD :79（done 提交只改三处）或当时尚未结束而留下的记录缺口集中回填；PRD :65 进一步收窄不属于本轮。
- 编排方整理：未完整调用 grill-with-docs，逐项修改、来源与验收已明确，无领域歧义；所有事件使用 `TZ=Asia/Shanghai date -Iseconds` 的实际时间，不倒填。

## 范围与边界

- 仅修改 `ai/tasks/v2.1.0-rc.2-concurrency-test-race/task.md`、`ai/tasks/v2.1.0-rc.2-task-status-sync/task.md`、`ai/tasks/v2.1.0-rc.2-legacy-event-criterion-prd/task.md`、`ai/tasks/v2.1.0-rc.2-legacy-events-notice/task.md`、`ai/tasks/v2.1.0-rc.2-plan/plan.md` 与本 `ai/tasks/v2.1.0-rc.2-f-backfill/task.md`。
- 不改代码／测试／schema／contract／openapi／templates／PRD；已有事件逐字不变，更正仅追加新事件或明确标注的 F 回填注记。四个已 done task 仅追加 done → done，frontmatter 只更新 updated_at，status／created_at／completed_at 不变。
- 本 task 只承载 rc.2 修复轮次累积的记录回填；plan.md F 行（P8，`ai/tasks/v2.1.0-rc.2-f-docs-backfill/task.md`）的安装与使用文档验收不在本 task 范围，F 行不改。
- 手写，未经 TaskStore 写入；只允许只读 parse／catalog，不写 active／index／handoff／ignore／身份，不承诺自动恢复。不启动子代理，不用 advisor，不执行 gh，不 push、不 amend／reset／rebase／force，不改 git／omp 全局配置；本轮恰好一个本地提交，结束时保持 in-progress，不进入 checking／done。

## 回填清单

以下行号均指入口基线，模型行号指模型记录表内序号。计数采用 jsonl 中 assistant 消息条数／其中 toolCall 个数，数字沿用编排方已重算核对的结果，不把历史运行计为本会话执行。

- `ai/tasks/v2.1.0-rc.2-concurrency-test-race/task.md`：:47 的 venv 与 :53 两处 Python 路径改为 `~/.local/venvs/project-validation` 及其 `bin/python3`；模型第 4 行 main s2 保留原计数文字，末尾追加 F 回填 13／34，会话路径改为 `~/.omp/logs/640-concurrency-test-fix/s2/2026-10-24T13-54-30-294Z_01a16e31-0b16-7391-9090-d2e1f83cef88.jsonl`；追加一条 done → done。来源：编排方整理：Lord 2026-10-24 群内裁定（具体分钟不可考，编排方 22:20 记录）：done 提交严格按 PRD :79，s2 会话绝对路径改为 `~/…` 归 F 回填。
- `ai/tasks/v2.1.0-rc.2-task-status-sync/task.md`：模型第 20 行 fix5 main 追加 F 回填 9／22（`~/.omp/logs/640-rc2-status-sync-prd/fix5/s1/2026-10-24T05-55-16-108Z_01a16c7a-4a0c-70ca-8a73-c550bce7b226.jsonl`）；第 30 行 PR-b fix3 main 追加 29／58（`~/.omp/logs/640-rc2-status-sync-workflow/fix3/s1/2026-10-24T08-16-42-765Z_01a16cfb-c90d-717a-bf19-896dbe18994e.jsonl`）；第 32 行 PR-b done main 追加 8／19（`~/.omp/logs/640-rc2-status-sync-workflow/done/s1/2026-10-24T10-06-42-119Z_01a16d60-7bc7-715f-9d44-494a055e0c38.jsonl`）；原「未知」保留，第 26、27 行会话路径改为 `~/…`，文件名不变。来源：编排方整理，按 jsonl 统计。
- `ai/tasks/v2.1.0-rc.2-task-status-sync/task.md`：追加 PR 描述事件。来源：用户 2026-10-24 22:42 群内确认（保留 #169 PR 描述），Lord 记录：#169 PR 描述于 2026-10-24 16:45:59 +08:00 的编辑发生在用户批准之前，用户确认保留现状，无需改动。编排方整理：userContentEdits 的 editedAt 为 `2026-10-24T08:45:59Z`；本轮不改 PR 描述，不执行 gh。
- `ai/tasks/v2.1.0-rc.2-task-status-sync/task.md`：追加本地报告事件，:48、:56 原样保留。来源：Lord 2026-10-24 18:42 群内裁定：如实记录 #169 本地测试报告已删除。编排方整理：ignored `reports/unit-report-prb-*-2026_10_24`（.txt／.md，从未提交）于 2026-10-24 18:3x 清理 worktree 时删除，不可恢复；CI run `40084725307` 13／13 与 Reviewy 复跑不受影响。
- `ai/tasks/v2.1.0-rc.2-task-status-sync/task.md`：追加取消 CI 事件。来源：Lord 2026-10-24 13:09 群内裁定：`fdbb1bd` 的 CI 结果不另加专门事件，并入 F 回填，编排方整理。编排方整理：run `40062997215` 最终 cancelled，结束于 2026-10-24 12:51:41 +08:00，既有 gh run view 核实；12:39:33 的「本轮不可考」与 12:49:42 的「仍在运行」为当时记录，逐字保留。本轮未查询平台。
- `ai/tasks/v2.1.0-rc.2-task-status-sync/task.md`：第四条新增事件汇总模型计数、路径及并发独立跟踪项引用；四条均为 done → done，顺序为 PR 描述、本地报告、取消的 CI、模型记录。来源：编排方整理；并发项来源为 Lord 2026-10-24 21:25 群内裁定。
- `ai/tasks/v2.1.0-rc.2-legacy-event-criterion-prd/task.md`：模型第 5 行 fix1 main s2 追加 F 回填 11／25，第 9 行 checking main s1 追加 9／21，原文保留；第 9 行之后、说明行之前新增第 10 行 done2 ping 1／0（2026-10-24 20:38:23 +08:00 开始，`~/.omp/agent/sessions/--workspace-640-skills-legacy-criterion-prd--/2026-10-24T12-38-23-865Z_01a16deb-5d79-746d-ab68-8d641285a96e.jsonl`）与第 11 行 done2 main s1 11／21（`~/.omp/logs/640-legacy-criterion-prd/done2/s1/2026-10-24T12-38-49-155Z_01a16deb-c043-70cc-a74b-6d71add943e0.jsonl`）。来源：编排方整理，按 jsonl 统计。只读 `git log --oneline -5 -- ai/tasks/v2.1.0-rc.2-legacy-event-criterion-prd/task.md` 仅见 `3c49524`，入口 HEAD 等于 origin/main；采用「done 提交（PR 分支 tip `1098d88`，squash 合入为 `3c49524`）」，不把 PR 分支 tip 冒充 main 提交。
- `ai/tasks/v2.1.0-rc.2-legacy-event-criterion-prd/task.md`：依次追加两条 done → done，先更正 2026-10-24T19:38:41 事件的 Reviewy CLEAN 时间（原写 19:31，群内更正实际 19:18，对应 `70cea1c`），再汇总模型与 plan 行回填，原事件逐字保留。来源：编排方整理；plan 行依据 Lord 2026-10-24 18:42 群内裁定。
- `ai/tasks/v2.1.0-rc.2-plan/plan.md`：仅在 :27 status-sync 行之后追加一行 legacy-criterion，四列为「见 task.md／PR 页面」，链接 criterion task，不改其他行。来源：Lord 2026-10-24 18:42 群内裁定；任务描述归因用户 2026-10-24 18:04 群内确认（方案一），Lord 记录。
- `ai/tasks/v2.1.0-rc.2-legacy-events-notice/task.md`：:40 project-validation 单元格末尾追加 F 回填注记，原计数是 s2 时 `ea4c161`，s3 后为新增 5 tests、task 8 模块 135 tests，见 :88、:90；:85 末尾注记「不 push」只限 s3 omp 会话，编排方在 omp 之外已 push `aeafdea`，Reviewy CLEAN，#172 squash 合入 `4752346`；:93 末尾注记「尚未执行」为 s3 落盘时状态，之后 Reviewy 对 `aeafdea` CLEAN，CI run `40108699894` 13／13 success，见第 5 条事件。来源：编排方整理：Reviewy 对 `aeafdea` CLEAN 时的三项非阻塞意见；原文保留。
- `ai/tasks/v2.1.0-rc.2-legacy-events-notice/task.md`：模型第 5 行 fix s3 追加 F 回填 17／54，原文保留；后新增第 6 行 done ping 1／0（2026-10-25 00:16:43 +08:00 开始，`~/.omp/agent/sessions/--workspace-640-skills-fix4--/2026-10-24T16-16-44-902Z_01a16eb3-4566-7686-b2d1-f8790440ff57.jsonl`）与第 7 行 done main 10／21（本地 done 提交 `0a0e5c0`，checking → done，按 PRD :79，`~/.omp/logs/640-fix4/done/2026-10-24T16-17-13-657Z_01a16eb3-b5b9-77a8-a3ad-bd4e554a7daa.jsonl`）。来源：编排方整理：CodeX 群内补充，按 jsonl 统计。
- `ai/tasks/v2.1.0-rc.2-legacy-events-notice/task.md`：依次追加两条 done → done，先补记第 3 条事件（2026-10-24T23:05:33+08:00）的「catalog 47 OK 提示 1 次」亦为已移除的去重行为，与第 2 条事件一样以 23:44:16 事件为准（每个旧文件一次，13 次）；再汇总三项行内注记与模型记录。来源：编排方整理：Reviewy 非阻塞意见；原事件不变。
- 并发测试独立跟踪项（Lord 2026-10-24 21:25 群内裁定）：已记录于 #171 `ai/tasks/v2.1.0-rc.2-concurrency-test-race/task.md` :47（修复前 main `3c49524`：单测 50／50、整文件 20／20、CPU 负载 100／100，未复现）与 :55–:57（修复后 `a6b1d70`：单测 50／50、整文件 14 tests OK、任务 4 模块 89 tests OK）；#172 `ai/tasks/v2.1.0-rc.2-legacy-events-notice/task.md` :54–:55、:78（`ea4c161` 上 10／10）亦引用；本轮只引用，不重复写入历史 task。
- 排除：PRD :65 进一步收窄；早于 #168 的其他 task 中的本机绝对路径不在本轮。来源：编排方整理。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮适用性与结果 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求前 | not-needed；仅记录文档，未完整 grill，边界明确 |
| book-ddia-data-design | schema、迁移或持久化机制设计前 | not-needed；仅记录文档，不改持久化机制 |
| book-legacy-change-safety | 既有行为修改前 | not-needed；仅记录文档，旧事件原样保留 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；仅记录文档，不改生产代码 |
| book-release-readiness | 运行时或部署变化，验证后 | not-needed；仅记录文档，无部署或发布变化 |
| project-validation | 回填后本地自检 | 本地只读解析＋task 8 模块 unittest＋catalog 探针＋diff 检查；实际结果记于下节与事件 |

## 验证与剩余边界

- 入口已核对根目录、分支 `docs/v2.1.0-rc.2-f-backfill`、HEAD 与 origin/main 均为 `47523469fff9da00d657cbfa08bc1a1154b3bc57`、工作区干净；六个授权路径及父目录无 symlink、无 ignore 匹配，新 task 目录原不存在。
- 本轮验证为 Evidence Source：developer-local；Source Revision：dirty（提交前）；Environment Alignment：unverified（未对齐正式 CI）；Evidence Publication：local-only。正式验证由编排方在本提交上运行；不宣称本轮审查、CI、合入或发布通过。
- `git diff --check` 干净；新 task 以 `git add -N -- ai/tasks/v2.1.0-rc.2-f-backfill/task.md` 纳入 diff 后，`git diff --stat` 恰含六个授权文件。plan.md 仅在 status-sync 后新增 legacy-criterion 一行，其余逐字不变；status-sync :48、:56 原报告行不变。
- 对四个旧 task 与本 task 分别运行 `python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" <path>`。四个旧 task 依次为 `done False 5 2026-10-24T22:26:25+08:00`、`done False 31 2026-10-24T18:07:09+08:00`、`done False 8 2026-10-24T20:39:06+08:00`、`done False 7 2026-10-25T00:17:37+08:00`；本 task 首次为 `in-progress False 1 None`，本节与第二条事件写入后再次核对 `in-progress False 2 None`。
- `python3 -B` 调用编排方验证目录的 `catalog_probe.py`：exit 0，`CATALOG_OK 48`；13 个 LEGACY，stderr 提示 13 次，新 task 不在 LEGACY 中。探针已只读核对为 `TaskStore(Path('.'), read_only=True)`，未调用 TaskStore 写入；这是实际 catalog 读取 smoke，不是仅检查文本。
- `python3 -B -m unittest tests.test_sbtd_task_document tests.test_sbtd_task_legacy_events_notice tests.test_sbtd_task_recovery tests.test_sbtd_task_routing tests.test_sbtd_task_schema tests.test_sbtd_task_state tests.test_sbtd_task_status_sync tests.test_sbtd_task_sync_git`：Ran 135 tests in 51.713s，OK。只运行一次，未改代码或测试。
- 对 `git diff -U0` 的新增行（排除文件头）逐项检查四个禁词及本机 HOME 绝对路径，均 0 命中。四个旧 task 的原事件分别为 4、27、6、5 条，逐字节与入口基线比较全部保留，分别新增 1、4、2、2 条；frontmatter 除 updated_at 外全部不变，updated_at 等于最后新事件 at。
- 自检第 6 项字面前缀存在冲突：`git diff -U0` 中以 `-| 20` 开头的删除行实际为 1，命中本轮必须补记的模型第 20 行（fix5 main），不是状态事件；首次字面断言因此失败，未掩盖。日期限定表达式 `^-\| 20[0-9]{2}-` 匹配的旧事件删除行为 0，并以完整旧事件行逐字节比较补充证明。不能同时修改模型第 20 行又声称该宽前缀为 0；本轮如实保留该验收口径差异。
- 第二条事件写入后、提交前再次执行 diff／五文件 parse／catalog／新增行检查／旧事件保全检查；本轮不生成额外正式报告，不将 task 文档当作正式报告。Final Test Report／Run Summary MD：not-needed；Targeted Rerun：not-needed；Final Full Rerun：passed（仅上述本地八模块，不是正式验证）；rtk：not-needed，按约定原生命令。BDD：skipped，仅记录文档，无 .feature 或用户可见行为变化；Cross-repo context／API Contract：not-needed；Mock Strategy：none。不运行额外 lint／formatter、Web／Mobile E2E 或全量 CI，无相应代码变化。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | 产出 | 会话文件 |
|---|---|---|---|---|---|
| 1 | ping（2026-10-25 00:55:48 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `~/.omp/agent/sessions/--workspace-640-skills-fbackfill--/2026-10-24T16-55-49-717Z_01a16ed7-0cd5-7781-b70e-0eb1fb84351c.jsonl` |
| 2 | main（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告 | F 回填 6 个文件，一个本地提交 | `~/.omp/logs/640-f-backfill/main/sessions/2026-10-24T16-58-27-224Z_01a16ed9-7418-7494-b06c-254d97d4d57c.jsonl` |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-25T00:59:09+08:00 | planned | in-progress | 编排方整理：建立手写 strict 任务，开始 F 回填。 | 根目录、分支、HEAD、干净工作区及六个授权路径安全已核对；仅六个文件，旧事件逐字保留；手写，未经 TaskStore 写入；at 为开始写本文件时取得的实际时间。 |
| 2026-10-25T01:04:21+08:00 | in-progress | in-progress | 编排方整理：完成 F 回填与本地自检，非正式验证。 | 六个授权文件；八模块 Ran 135 tests in 51.713s，OK；四个旧 task 只读解析为 done、非旧格式，事件数 5／31／8／7，completed_at 保留；本 task 首次 in-progress False 1 None，本事件后再次解析两条事件；catalog 48 条，新 task 非 LEGACY；diff --check 干净，新增行禁词与本机 HOME 绝对路径均 0；旧事件逐字保留，日期限定的事件删除行为 0，宽前缀检查误命中模型第 20 行的差异见正文；developer-local／Source Revision: dirty／local-only，正式验证由编排方在本提交上运行；手写，未经 TaskStore 写入，保持 in-progress。 |
