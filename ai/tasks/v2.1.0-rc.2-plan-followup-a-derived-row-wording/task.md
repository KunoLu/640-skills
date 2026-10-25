---
schema_version: 1
id: v2.1.0-rc.2-plan-followup-a-derived-row-wording
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：本轮采用 strict，仅追加 plan.md 一行并建立本 task；主会话为两个授权文件唯一 writer 与验证 controller，不启动子代理、不使用 advisor；提交由编排方执行。
status: checking
branch: docs/v2.1.0-rc.2-plan-followup-a-derived-row-wording
created_at: '2026-10-25T18:55:11+08:00'
updated_at: '2026-10-25T18:59:34+08:00'
completed_at: null
---

# rc.2：plan.md 后续项 A 派生行措辞追加更正

## 决定

- 用户 2026-10-25 14:13 群内确认（本项派生行措辞单开 PR 修正），Lord 记录。
- 用户 2026-10-25 07:50 群内确认（Docs B/C 与 exportable 选方案一），Lord 记录：run、step 等派生行随其依据事件一并不导出，task 行与聚合行始终导出，聚合按全部事件计算。括号外行为说明为编排方整理的概括，不作为原话引用。
- Lord 2026-10-25 18:50 群内裁定（批准方案与措辞定稿）。
- 未完整调用 grill-with-docs：范围、追加文本与验收明确；源码、测试与已对齐文档可直接核对，无新增领域歧义。

## 范围与边界

恰好两个文件：

1. `ai/tasks/v2.1.0-rc.2-plan/plan.md`：仅在原第 114 行后插入外部文件 `/workspace/640-legacy-wording-verify/plan-followup-a-line.txt` 去掉末尾换行后的单行，保留行首三个空格；Python 读取并按字节计算插入内容，经编辑工具落盘，不手抄。原第 114 行、其余原行与文件末尾换行不变。
2. `ai/tasks/v2.1.0-rc.2-plan-followup-a-derived-row-wording/task.md`：本 strict 任务记录，最终保持 checking、completed_at=null。

背景：原 `plan.md:114` 的「task/run/聚合派生行不屏蔽」与 #151 以来行为不一致。当前基线逐项核对证据如下，源码、测试和已对齐文档行号均与初查一致：

- `sbtd-runtime/export_render.py:268-286` 的 `_non_exportable_ids` 按 `exportable is False` 或 `classification != "local-metadata"` 收集被屏蔽 event_id；`:289-296` 的 `_row_event_id` 对 event 行取 record_id，其他行取 fields.event_id；`:299-303` 的 `_withheld` 不屏蔽 task 行，其余行按 event_id 屏蔽。
- `sbtd-runtime/report_snapshot.py:207`、`:238`：run／step 行 fields 来自 `_base_fields(...)`，`:122` 携带依据事件的 event_id。
- `sbtd-runtime/csv_export.py:192-217` 的 `_metric_rows` 在 `:196` 对 `snapshot.dataset` 调用 query；`sbtd-runtime/export_render.py:924` 同样查询该全量 dataset，聚合不因明细屏蔽而改变。
- `sbtd-runtime/tests/test_export_render.py:229-275` 的 `test_redaction_is_shared_and_does_not_change_metrics`：事件设为 exportable=false 后，指标不变且该事件行不导出；本轮仅核对该测试源码，不将其列为已运行测试。
- 已对齐文档：`docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md:894-896`、`sbtd-runtime/docs/install-and-use.md:154`。
- 原 `plan.md:90` 已由 `:92` 的追加条款更正；原 `:119` 已由原 `:120` 更正，本轮插入后分别为 `:120`、`:121`。这些历史行均不改。
- 不改 index、任务表、其他 task、旧状态事件、PRD、使用文档、代码或测试；时间戳措辞不在本 PR。
- 沿用参考 task 的手写记录方式，不调用 TaskStore 写入，不写 `.sbtd/`、active、handoff、ignore 或身份；不承诺 TaskStore 自动恢复。不提交、不推送，不操作暂存区、历史或全局配置；临时文件仅放 `/tmp`，不读取环境变量值或会话 jsonl 内容。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮适用性与证据 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求前 | not-needed；未完整 grill，既有行为明确，仅追加措辞更正 |
| book-ddia-data-design | schema、迁移或持久化机制设计前 | not-needed；沿用 task 结构，不改 schema 或持久化机制 |
| book-legacy-change-safety | 既有行为修改前 | not-needed；不改运行时行为，以基线字节比较保护历史文档 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；无生产代码修改 |
| book-release-readiness | 运行时或部署变化，验证后 | not-needed；无运行时、部署或发布变化 |
| project-validation | 文档落盘后 | 适用；执行八项限定检查、八模块 unittest 与真实 task 解析 |
| Code Readability Review／独立 review | check | not-needed；无代码或测试修改，不触发独立 review；主会话核对，不冒充独立审查 |

## 验证与剩余边界

- 入口 `pwd && git rev-parse --show-toplevel && git rev-parse origin/main && git branch --show-current && git status --short`：退出码 0，根目录与分支匹配、工作树干净，origin/main 为 `bc82b353fdb7f11ea3aa12f84aace62afcded241`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B -c <入口路径检查>`：退出码 0；两个授权路径及全部父路径无 symlink、无逃逸，plan.md 与 origin/main 字节一致、新 task 不存在。内部 `git check-ignore --no-index <两个授权路径>` 无命中，退出码 1、stdout／stderr 空；修改前目标短语出现 3 次。
- 开始时间来自 `TZ=Asia/Shanghai date +%Y-%m-%dT%H:%M:%S+08:00`，退出码 0，不倒填群内决定时间。
- 证据仅限本地未提交工作树：Evidence Source=developer-local，Source Revision=dirty，Evidence Publication=local-only。rtk=skipped-for-report，使用精确原生命令；BDD=skipped，无行为或持久场景变化；Cross-repo context／API Contract／Environment Alignment=not-needed，Mock Strategy=none。
- 不运行 lint／format／构建、全仓测试、浏览器／移动端或发布验证：仅文档追加；不把本地验证当作 CI、独立审查、合入或发布。临时报告不保证长期保留。

### 限定验证结果

- `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/plan-followup-a-validate.py initial-checks` 与 `prechecking-checks`：均退出 0；Python 字节比较证明 plan.md 等于 origin/main 原文在原第 114 行后插入外部文本一行，原字节、三个前导空格及末尾换行均保留。
- `git diff -U0 -- ai/tasks/v2.1.0-rc.2-plan/plan.md`：退出 0；仅一条新增行，无删除行。删除行检查使用 Python 执行与 `grep -v '^--- a/'` 再筛选 `^-` 等价的过滤，未执行 shell grep 管道；prechecking-checks 中该独立过滤进程真实退出 1，stdout／stderr 空。initial-checks 的过滤 exit 字段是等价推导值，不作为真实进程退出码证据。
- `git diff --check`、`git diff --check origin/main`：均退出 0、输出为空。`git diff --stat origin/main` 退出 0，仅 plan.md 一行新增；结合 `git status --short --untracked-files=all`（退出 0）计入未跟踪的新 task，恰好两个授权文件，无其他改动。
- 新增行与新 task 全文的禁词、主目录路径、无日期时间归因及模糊分钟扫描为 0 命中；新 task 无尾随空白。短语行数使用专用 grep 工具与 Python 按行计数核对，修改前 3、修改后 4；未执行 shell `grep -c`。
- 八模块回归通过仓库外 runner 捕获以下原生命令，runner 与 unittest 均退出 0：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_sbtd_task_document tests.test_sbtd_task_legacy_events_notice tests.test_sbtd_task_recovery tests.test_sbtd_task_routing tests.test_sbtd_task_schema tests.test_sbtd_task_state tests.test_sbtd_task_status_sync tests.test_sbtd_task_sync_git
```

- 实际结果：`Ran 135 tests in 50.247s`、`OK`；stdout 空，stderr 中的 `旧格式事件，不追溯` 为既有测试夹具通知，完整保留；一轮，无失败或重试，原生输出未报告 skipped。runner 命令为 `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/plan-followup-a-validate.py unittest`。
- 真实 task 解析执行以下命令，转 checking 前退出 0、stderr 空，输出路径后字段为 `in-progress False 1 None`，解析前后文件字节不变：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" ai/tasks/v2.1.0-rc.2-plan-followup-a-derived-row-wording/task.md
```

- 原始结果位于 `/tmp/plan-followup-a-s1-20261025T185511/initial-checks.json`、`prechecking-checks.json`、`unittest.json`；八模块同 stem 中文汇总为 `unittest.md`。实际 HEAD 与 origin/main 均为 `bc82b353fdb7f11ea3aa12f84aace62afcded241`，环境为本地 Linux x64、Python 3.13.5。Final Test Report／Run Summary MD=generated；Targeted Rerun=not-needed；Final Full Rerun=passed，仅指八模块范围。
- 限定检查完成后，使用真实 `TZ=Asia/Shanghai date +%Y-%m-%dT%H:%M:%S+08:00`（退出 0）取得 `2026-10-25T18:59:34+08:00`，追加 checking 事件；updated_at 与末事件一致、completed_at 保持 null。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/plan-followup-a-validate.py checking-checks`：退出 0；转 checking 后字节、删除行、空白、范围、文字限制与计数检查均通过；同一解析命令输出路径后字段为 `checking False 2 None`，退出 0、stderr 空、文件字节不变，updated_at 等于末事件 at。结果保留于同目录 `checking-checks.json`；临时验证脚本在验证后移除，raw 报告与中文汇总保留。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | 产出 | 会话文件 |
|---|---|---|---|---|---|
| 1 | ping（2026-10-25 18:53:49 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-25T10-53-49-464Z_01a172b1-fc18-76b7-9474-e3f24e76754c.jsonl` |
| 2 | 会话 1（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告 | plan.md 插入一行与本 task | `2026-10-25T10-54-30-140Z_01a172b2-9afb-76f5-8ac2-059a3e443f48.jsonl` |

每个 omp 会话一行；未使用子代理、advisor；内部辅助 model_usage 记录（如有）由群内交付报告另列。本会话文件名仅通过会话目录文件名列表核对，未读取 jsonl 内容。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-25T18:55:11+08:00 | planned | in-progress | 编排方整理；写入者：主会话，开始 plan.md 后续项 A 措辞追加与本 task 建立 | 基线 `bc82b35`；根目录、分支、干净工作树、路径与 ignore 安全已核对，源码、测试及已对齐文档行号一致。 |
| 2026-10-25T18:59:34+08:00 | in-progress | checking | 编排方整理；写入者：主会话，plan.md 一行追加与限定验证完成，进入检查 | 基线 `bc82b35`；原字节及末尾换行保留，无删除行，文字限制 0 命中、目标短语 3→4；八模块 Ran 135 tests in 50.247s、OK、exit 0；真实 task 解析 exit 0、stderr 空且字节不变；工作树仅两个授权文件。 |
