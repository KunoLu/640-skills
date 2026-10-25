---
schema_version: 1
id: v2.1.0-rc.2-s1-model-count-backfill
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：本轮采用 strict，仅三个既有 task 追加计数说明与本 task；主会话为四个授权文件唯一 writer 与验证 controller，不启动子代理、不使用 advisor；提交由编排方执行。
status: done
branch: docs/v2.1.0-rc.2-s1-model-count-backfill
created_at: '2026-10-25T23:15:17+08:00'
updated_at: '2026-10-25T23:51:00+08:00'
completed_at: '2026-10-25T23:51:00+08:00'
---

# rc.2：#181／#182／#183 task s1 模型计数追加式回填

## 决定

- 编排方整理（Lord 当日群内裁定，具体分钟不可考）：为 #181、#182、#183 三个 task 回填会话 1（s1）的实际计数，采用方案 A——按 #180 先例（bc82b35）追加式更正：每个文件在表后注释段之后追加一个空行与一段说明，原「未知」行、表格行、frontmatter 与事件逐字节保留，不新增表格行。同一裁定要求 #181、#182 的段落一并记录其后漏记的 ping2 与会话 2 计数（#181 会话 2 为 9／16，#182 会话 2 为 12／19，ping2 均为 1／0）；#183 表中已有 ping 行，只补会话 1。本 task 自身会话行按惯例写「未知」，不再为本 task 另开回填。E（v2.1.0-rc.2 预发布）仍暂停，本项不带出新需求。
- 计数口径（编排方整理）：编排方只读统计会话 jsonl，计 `type=message` 的 assistant 消息与其中的 toolCall 块；本会话未读取 jsonl 内容。#181 会话 1 25／47，#182 会话 1 22／44，#183 会话 1 26／59；上述 ping、ping2、会话 1、会话 2 均为 openai-codex/gpt-6-astra（high）。内部辅助记录由群内交付报告另列，不写入 task。
- 未完整调用 grill-with-docs：范围、追加文本与验收明确，无新增领域歧义。

## 范围与边界

恰好四个文件：

1. `ai/tasks/v2.1.0-rc.2-plan-followup-a-derived-row-wording/task.md`（#181）：+2 行、0 删除。
2. `ai/tasks/v2.1.0-rc.2-contract-5-5-wording/task.md`（#182）：+2 行、0 删除。
3. `ai/tasks/v2.1.0-rc.2-contract-scope-wording/task.md`（#183）：+2 行、0 删除。
4. `ai/tasks/v2.1.0-rc.2-s1-model-count-backfill/task.md`：本 strict 记录，最终 checking、completed_at=null。

三段追加文本依次如下；从仓库外 para-181.txt／para-182.txt／para-183.txt 读取，Python 按字节计算插入，经编辑工具落盘，不手抄。

```text
编排方整理，按 jsonl 统计：会话 1 实际为 25／47；其后 ping2 为 1／0，会话 2 为 9／16，二者均为 openai-codex/gpt-6-astra（high），上表未单列。上方第 2 行的「未知」写法原样保留。
```

```text
编排方整理，按 jsonl 统计：会话 1 实际为 22／44；其后 ping2 为 1／0，会话 2 为 12／19，二者均为 openai-codex/gpt-6-astra（high），上表未单列。上方第 2 行的「未知」写法原样保留。
```

```text
编排方整理，按 jsonl 统计：会话 1 实际为 26／59。上方第 2 行的「未知」写法原样保留。
```

不改代码、测试、契约、PRD、plan.md、index 或其他 task，不安装依赖、不提交、不推送、不操作暂存区或历史、不改全局配置。沿用 #180 的手写记录方式，不调用 TaskStore 写入，不写 active／handoff／ignore／身份，不改变历史分支字段，不承诺 TaskStore 自动恢复。临时文件仅放 /tmp；会话文件名仅经目录列表核对，不读取 jsonl 内容或环境变量值。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮判定与证据 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求前 | not-needed；未完整 grill，仅明确历史记录回填 |
| book-ddia-data-design | schema／迁移／持久化机制设计前 | not-needed；沿用 task 格式，不改 schema 或机制 |
| book-legacy-change-safety | 既有行为修改前 | not-needed；不改行为，以基线字节比较保护原文 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；无生产代码修改 |
| book-release-readiness | 运行时／部署变化，验证后 | not-needed；无运行时、部署或发布变化，E 仍暂停 |
| gherkin-bdd／TDD | 行为、场景或状态机制变更前 | not-needed；仅使用既有记录格式，不改行为或机制 |
| project-validation | 文档落盘后 | 适用；执行精确字节、八模块回归、四文件解析与新增文本扫描 |
| Code Readability Review／独立 review | check | not-needed；无代码或测试修改，单一任务记录范围，不触发独立 review；主会话自核不冒充独立审查 |

## 验证与剩余边界

- 入口 `pwd && git rev-parse --show-toplevel && git branch --show-current && git rev-parse origin/main && git status --short --untracked-files=all`：exit 0，根目录、分支匹配，工作树干净，origin/main 为 `7007574d16d95f296b80cec1ed74f37610539100`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/s1-backfill-prepare.py`：exit 0；四路径及父路径无 symlink／逃逸，三个既有文件与基线字节一致，新 task 原先不存在；内部 `git check-ignore --no-index <四路径>` exit 1、stdout／stderr 空，无命中。
- 基线内容先写入 /tmp 后以 TaskDocument 同样解析：#181／#182／#183 均为 done、legacy_events=False、事件数 3；completed_at 依次为 2026-10-25T19:28:18+08:00、2026-10-25T20:57:45+08:00、2026-10-25T22:18:53+08:00；三个进程 exit 0、stderr 空。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B /workspace/640-s1-backfill-verify/expected.py`：exit 0，三行 byte_exact True。
- 开始时间由 `TZ=Asia/Shanghai date +%Y-%m-%dT%H:%M:%S+08:00` 实际取得，exit 0，不倒填裁定时间。
- 验证边界：仅本地未提交文档工作树，不证明 CI、独立审查、合入或发布；不运行 lint／format／build、全仓测试、浏览器或移动端验证，因仅任务记录追加。BDD=skipped，无行为或持久场景变化，语言检查不适用；Cross-repo context／API Contract／Environment Alignment=not-needed，Mock Strategy=none；rtk=skipped-for-report，使用精确原生命令；Evidence Source=developer-local，Source Revision=dirty，Evidence Publication=local-only。临时证据不保证长期保留。

- `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/s1-backfill-validate.py initial`：exit 0；内部 `git diff --numstat` exit 0，三个既有文件均为 `2 0`；`git diff --check` exit 0、输出为空；`git status --short --untracked-files=all` exit 0、恰四个授权文件。四文件新增文本的禁词／路径／归因／模型名限制与常见密钥格式扫描 0 命中；三段代码块原文一致，新 task 无尾随空白。
- 以下 PARSE 命令对范围节四个路径分别执行，均 exit 0、stderr 空，解析前后字节不变；三个既有 task 仍为 `done False 3`，completed_at 与基线一致；本 task 转 checking 前为 `in-progress False 1 None`。

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" <path>
```

八模块回归在仓库根由 `TZ=Asia/Shanghai PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/s1-backfill-validate.py tests` 执行，runner 与以下原生命令均 exit 0：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_sbtd_task_document tests.test_sbtd_task_legacy_events_notice tests.test_sbtd_task_recovery tests.test_sbtd_task_routing tests.test_sbtd_task_schema tests.test_sbtd_task_state tests.test_sbtd_task_status_sync tests.test_sbtd_task_sync_git
```

- 实际结果：`Ran 135 tests in 62.666s`、`OK`；stdout 空，一轮无失败或重试，未报告 skipped；stderr 中的「旧格式事件，不追溯」为既有测试夹具通知，原样保留，不是四份真实 task 的解析 stderr。
- 原生/raw 报告与同 stem 中文汇总：`/tmp/s1-backfill-reports/unittest.json`、`unittest.md`；限定检查 raw：同目录 `initial.json`。绑定实际 HEAD `7007574d16d95f296b80cec1ed74f37610539100`、当前分支和未提交工作树。Final Test Report／Run Summary MD=generated；Targeted Rerun=not-needed；Final Full Rerun=passed，仅八模块范围。
- 全部限定验证完成后，真实 `TZ=Asia/Shanghai date +%Y-%m-%dT%H:%M:%S+08:00` exit 0，取得 `2026-10-25T23:18:17+08:00`；追加 in-progress → checking，updated_at 与最后事件时间一致，completed_at=null。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/s1-backfill-validate.py final`：exit 0；转 checking 后字节、+2／0、空白、四文件范围与新增文本扫描均通过；四份 task 的同一 PARSE 命令均 exit 0、stderr 空，三个既有 task 仍为 `done False 3`，本 task 为 `checking False 2 None`，updated_at 与末事件一致。raw 保留于 `/tmp/s1-backfill-reports/final.json`；临时准备、补丁和校验脚本在验证后移除，原始报告与中文汇总保留。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | 产出 | 会话文件 |
|---|---|---|---|---|---|
| 1 | ping（2026-10-25 23:13:29 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-25T15-13-29-780Z_01a1739f-b8b4-719f-ad1c-372ea488eeaa.jsonl` |
| 2 | 会话 1（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告 | 三个 task 追加计数说明与本 task | `2026-10-25T15-14-11-653Z_01a173a0-5c45-7623-b578-6304ee315734.jsonl` |

每个 omp 会话一行；未使用子代理、advisor；内部辅助 model_usage 记录（如有）由群内交付报告另列。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-25T23:15:17+08:00 | planned | in-progress | 编排方整理；写入者：主会话，开始三个 task 追加计数说明与本 task 建立 | 基线 `7007574`；入口干净，根目录、分支、四路径及 ignore 安全；三个基线 task 均 done、事件数 3、解析 stderr 空。 |
| 2026-10-25T23:18:17+08:00 | in-progress | checking | 编排方整理；写入者：主会话，三个 task 追加计数说明与全部限定验证完成，进入检查 | 基线 `7007574`；expected.py 三行 byte_exact True、exit 0；三个既有文件各 +2／0 删除，原字节保留；八模块 135 tests、OK、exit 0；四份 task 解析 exit 0、stderr 空，三个历史 task 仍 done、事件数 3；新增文字扫描 0 命中，工作树恰四个授权文件。 |
| 2026-10-25T23:51:00+08:00 | checking | done | 编排方整理；写入者：主会话，Reviewy CLEAN 后写入 done；PR #184 | Reviewy CLEAN @ 5c1ea7145898031683e319eb6f236ef87355db91（编排方整理）；CI validation run 40206567441 attempt 1 success 13/13（编排方整理） |
