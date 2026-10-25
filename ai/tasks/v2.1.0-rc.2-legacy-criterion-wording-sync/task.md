---
schema_version: 1
id: v2.1.0-rc.2-legacy-criterion-wording-sync
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：本轮采用 strict，仅同步四处文档措辞并建立本 task；主会话为五个授权文件的唯一 writer 与验证 controller，不启动子代理、不使用 advisor；提交由编排方在 omp 之外执行。
status: done
branch: docs/v2.1.0-rc.2-legacy-criterion-wording-sync
created_at: '2026-10-25T14:11:50+08:00'
updated_at: '2026-10-25T15:13:39+08:00'
completed_at: '2026-10-25T15:13:39+08:00'
---

# rc.2：旧格式判定口径措辞同步

## 决定

- 用户 2026-10-25 14:03 群内确认（选项 2 加 AGENTS.project.md），Lord 记录：只统一措辞、不改行为。无基线时，事件行五列（at／from／to／reason／evidence）均非空、`at` 为 `unknown` 或合法时间戳，但不符合内置 stateEvent schema，即算旧格式，不设状态名枚举；只按 frontmatter `status` 判断，输出「旧格式事件，不追溯」，不写文件、不阻塞、不算未记录改动；空单元格、非法时间戳、非法 frontmatter、重复事件节仍为普通解析错误。
- Lord 2026-10-25 14:08 群内裁定：PRD :65 只在行末追加一句，12:46 与 18:04 两段旧归因逐字节不变；`at` 为 `unknown` 或合法时间戳与代码一致。
- 未完整调用 grill-with-docs：范围、替换文本与验收条件明确，既有实现可直接核对，无新增领域设计。

## 范围与边界

恰好五个文件：

1. `docs/prd/sbtd-workflow-v2-task-status-sync.md`：第 65 行末直接追加一句，不加空格，保持单行与文件行数。
2. `sbtd-workflow-onboard/REFERENCE.md`：第 29 行整行替换。
3. `sbtd-workflow-onboard/templates/skills/sbtd-task/references/state.md`：第 38 行仅替换限定中段，首句与末句保留。
4. `sbtd-workflow-onboard/templates/agents/AGENTS.project.md`：第 35 行仅替换限定旧格式说明，其余内容保留。
5. `ai/tasks/v2.1.0-rc.2-legacy-criterion-wording-sync/task.md`：本 strict 任务。

- 不改代码、测试、契约、schema、plan.md、index 或其他 task；不调用 TaskStore 写入，不写 `.sbtd/`、active、handoff、ignore 或身份。本 task 为手写记录，不宣称 TaskStore 恢复保证。
- 替换文本从仓库外文件读取，仅去掉末尾换行，由 Python 按字节计算补丁，经编辑工具落盘，不手抄替换内容。
- 不提交、不推送，不操作暂存区或历史，不调用平台 CLI，不修改 git／omp 全局配置；临时脚本与验证产物仅在 `/tmp`。本轮最终状态为 checking，completed_at 保持 null，不写最终 CI 结果或 done。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮适用性与证据 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求前 | not-needed；未完整 grill，既有规则与精确替换范围明确 |
| book-ddia-data-design | schema、迁移或持久化机制设计前 | not-needed；仅措辞与本任务记录，不改变机制或 schema |
| book-legacy-change-safety | 既有行为修改前 | not-needed；不改运行时行为；写前阅读解析实现与既有回归测试 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；无生产代码编辑或重构 |
| book-release-readiness | 运行时／部署变化，验证后 | not-needed；无运行时、部署或发布变化 |
| writing-for-agents／gherkin-bdd | 模板及持久场景措辞编辑前 | 已读取；沿用 REFERENCE.md 的中文场景与 English Gherkin 关键词，仅同步旧格式场景，不扩展为全仓行为审计 |
| project-validation | 编辑后 | 执行 a–f 范围核验、五模块 unittest 与四份 task 真实解析，原生输出保留在仓库外 |
| Code Readability Review／独立 review | check | 无代码／测试改动；单一任务状态文档范围，不触发独立 review；主会话核对，不冒充独立审查 |

## 验证与剩余边界

- 入口：根目录及分支匹配，HEAD／origin/main 均为 `861c42a419a26da912fc3f38aac7c0fc5413723d`，工作树干净。`git rev-parse HEAD origin/main`、`git status --short --untracked-files=all` 退出码均 0。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/legacy-wording-prepare.py`：退出码 0；五个路径及父路径无 symlink、未逃逸，四个原文件已跟踪且与基线逐字节一致，新 task 不存在；`git check-ignore --no-index` 对五路径无命中、退出码 1。四行替换补丁按外部文本精确生成。
- 实现核对：`sbtd_task_document.py:195–254` 先校验 frontmatter 与事件节；无基线时五列非空、schema 不兼容即 legacy，`at != unknown` 继续校验时间戳；通知写 stderr，events 清空，frontmatter 保留。`sbtd_task_sync.py:149–157` 将 legacy 记入 notes 而非 differences，不把旧格式本身当作未记录改动。未发现与统一口径冲突，未改代码。
- 本地验证限定为 a–f，以下为真实运行结果。全仓测试、独立审查、跨平台、浏览器／移动端、CI 与发布不执行：本轮仅文档措辞同步，不把本地结果描述为最终合入或发布证据；无代码变化，lint／format／类型检查不适用。
- rtk：skipped-for-report，使用原生命令保留精确输出；BDD：traceable，REFERENCE.md 旧格式场景对应既有 legacy-events／status-sync／sync-git 测试；无新增 .feature 或 runner。Cross-repo context／API Contract／Environment Alignment：not-needed；Mock Strategy：none；Evidence Source：developer-local；Source Revision：dirty；Evidence Publication：local-only。

### a–c：空白、精确字节与新增文字

- `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/legacy-wording-validate.py initial-checks`：退出码 0。内部 `git diff --check` 退出码 0；新 task 额外尾随空白检查为 0。
- `git diff -U0 origin/main` 退出码 0；以 Python 对其输出执行与删除行过滤管道等价的筛选，恰为四个目标旧行，无其他删除。没有执行 shell grep 管道。
- Python 逐字节比较 `git show origin/main:<path>` 与工作区：PRD 第 65 行以整个旧行为前缀，后缀恰为外部新增句，无额外空格，仍为单行、全文件 120 行；REFERENCE 第 29 行恰为外部新文本；state 第 38 行中段之外的全部前后字节（含首句、末句）不变；AGENTS.project 第 35 行替换段之外全部不变。四个文件的其他行均逐字节不变，行数分别为 120／1038／118／62。
- 扫描四个 diff 新增行及新 task 全文：禁词、主目录路径、无日期时间归因等限制均 0 命中；未将旧 PRD 归因重新措辞。

### d：五模块回归

工作目录为仓库根；实际原生命令：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_sbtd_task_legacy_events_notice tests.test_sbtd_task_status_sync tests.test_sbtd_task_sync_git tests.test_workflow_contracts tests.test_findings_cli_regressions
```

- 通过仓库外 runner 捕获原生 stdout／stderr／exit；退出码 0，stdout 为空，stderr 为 `Ran 72 tests in 11.752s`、`OK`。仅运行一轮，无失败或重试，未报告 skipped 用例。
- stderr 中旧格式通知属于预期行为；另有临时项目的 `.gitignore` effectiveness verification skipped 提示（原文原因：no git binary or no work tree），原始输出保留，不将该临时项目的 ignore 有效性记为已验证，也不将该提示误记成 unittest 跳过用例。

### e：真实 task 只读解析

对下表各路径分别运行以下命令；四次退出码均 0，解析前后文件字节不变：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" <path>
```

| path | stdout（完整路径后各字段） | stdout 含旧格式通知 | stderr |
|---|---|---|---|
| `ai/tasks/v2.1.0-rc.1-r1.3-stats-api/task.md` | `done True 0 2026-10-17T09:43:07+08:00` | 否 | `旧格式事件，不追溯` |
| `ai/tasks/v2.1.0-rc.1-csv-reasoning-tokens/task.md` | `done True 0 2026-10-17T12:57:37+08:00` | 否 | `旧格式事件，不追溯` |
| `ai/tasks/v2.1.0-rc.2-r2.1b-renderer/task.md` | `done True 0 2026-10-22T16:22:16+08:00` | 否 | `旧格式事件，不追溯` |
| `ai/tasks/v2.1.0-rc.2-legacy-criterion-wording-sync/task.md`（转 checking 前） | `in-progress False 1 None` | 否 | 空 |
| `ai/tasks/v2.1.0-rc.2-legacy-criterion-wording-sync/task.md`（转 checking 后） | `checking False 2 None` | 否 | 空 |

### f：范围与证据边界

- `git status --short --untracked-files=all`、`git diff --name-only origin/main` 退出码均 0；前者恰为四个已跟踪文档修改与一个新 task，后者四项加新 task 恰为范围节中的五文件，无额外改动。
- 原始命令、stdout／stderr 与退出码保留于 `/tmp/legacy-wording-sync-s1-20261025T141150/initial-checks.json`、`unittest.json`；仅为本地 dirty 工作树证据，不等同于提交后 CI。时间由 `TZ=Asia/Shanghai date +%Y-%m-%dT%H:%M:%S+08:00` 获取，退出码 0。
- 所有 a–f 初轮核验完成后追加 checking 事件；不补写 done 或最终 CI 结果，不改变三份旧 task。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/legacy-wording-validate.py checking-checks`：退出码 0；转 checking 后重新核对 a–c、e、f，全部通过，新 task 解析输出见上表，updated_at 与最后事件时间一致、completed_at 为 null。原始输出为 `/tmp/legacy-wording-sync-s1-20261025T141150/checking-checks.json`。
- 五模块原始报告及同 stem 九节中文汇总为 `/tmp/legacy-wording-sync-s1-20261025T141150/unittest.json`、`unittest.md`。Final Test Report／Run Summary MD：generated；Targeted Rerun：not-needed；Final Full Rerun：passed，仅指本轮五模块范围。临时补丁和检查脚本在验证后移除，保留原始报告。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | 产出 | 会话文件 |
|---|---|---|---|---|---|
| 1 | ping（2026-10-25 14:09:30 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-25T06-09-30-918Z_01a171ad-b126-72a4-8ce0-d014f420241a.jsonl` |
| 2 | 会话 1（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告 | 措辞同步与本 task | `2026-10-25T06-11-23-314Z_01a171af-6832-7167-a827-612eb2a7a174.jsonl` |
| 3 | 会话 1 内部辅助 model_usage | typesafe/jev-latest（thinking 不可考） | 12 次调用（purpose find，不计入主会话 assistant 消息／toolCall） | 旧格式同步检查源码定位；只读解析本会话 jsonl 的 type=model_usage 记录 | `2026-10-25T06-11-23-314Z_01a171af-6832-7167-a827-612eb2a7a174.jsonl` |

每个 omp 会话一行；未使用子代理、advisor；内部辅助 model_usage 记录另列一行，落盘前只读统计为 12 条，未读取或输出环境变量值。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-25T14:11:50+08:00 | planned | in-progress | 编排方整理；写入者：主会话，开始旧格式口径核对与五文件措辞同步 | 基线 `861c42a`；根目录、分支及干净工作树已核对；真实时间由 Asia/Shanghai date 获取，不倒填群内决定时间；路径与 ignore 核验通过，解析实现与统一口径一致。 |
| 2026-10-25T14:15:11+08:00 | in-progress | checking | 编排方整理；写入者：主会话，四处措辞同步与 a–f 本地核验完成，进入检查 | 基线 `861c42a`；五模块 Ran 72 tests、OK、exit 0；diff 与新增 task 空白检查通过，四行精确字节替换及保留检查通过，新增行限制 0 命中；三份旧 task 为 done／legacy True／events 0 且仅 stderr 提示，新 task 非 legacy；范围恰为五文件，详见验证节。 |
| 2026-10-25T15:13:39+08:00 | checking | done | 编排方整理：Reviewy CLEAN 后写入 done；PR #179 | Reviewy CLEAN @ 4dc4c7b2837d63844b095f1fc0478e6c07a1a75d（编排方整理）；CI validation run 40170493454 attempt 1 success 13/13（编排方整理） |
