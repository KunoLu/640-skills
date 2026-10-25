---
schema_version: 1
id: v2.1.0-rc.2-backfill-model-counts
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：本轮采用 strict，仅回填三个 task 并建立本 task；主会话为四个授权文件唯一 writer 与验证 controller，不启动子代理、不使用 advisor；提交由编排方在 omp 之外执行。
status: done
branch: docs/v2.1.0-rc.2-backfill-model-counts
created_at: '2026-10-25T17:15:26+08:00'
updated_at: '2026-10-25T18:20:04+08:00'
completed_at: '2026-10-25T18:20:04+08:00'
---

# rc.2：#178／#177／#179 task 模型计数与时间说明回填

## 决定

- 依据 Lord 2026-10-25 17:11 群内裁定（确认 backfill 三项范围），编排方整理：为 #178、#179 两个 task 的模型记录表追加漏记会话行与按 jsonl 统计的计数更正说明，原「未知」写法保留；为 #177 回填 task 追加一条 done → done 事件，补充上一条 done 事件中「12:4x」的时间说明，原事件逐字保留。
- 计数由编排方整理，编排方只读统计会话 jsonl，仅计数 `type=message` 的 assistant 消息、其中的 toolCall 块与 `type=model_usage` 记录；本会话未读取 jsonl 内容，仅查看本会话目录中的文件名。
- 未完整调用 grill-with-docs：范围、追加文本与验收条件明确，既有解析实现与先例可直接核对，无新增领域歧义。

## 范围与边界

恰好四个文件：

1. `ai/tasks/v2.1.0-rc.2-runtime-perf-default-events/task.md`：模型记录表追加两行，注释追加一段；frontmatter 不变。
2. `ai/tasks/v2.1.0-rc.2-backfill-docs-bc-pr4/task.md`：追加 done → done 事件，仅额外修改 frontmatter 的 updated_at；status 与 completed_at 不变。
3. `ai/tasks/v2.1.0-rc.2-legacy-criterion-wording-sync/task.md`：模型记录表追加五行，注释追加一段；frontmatter 不变。
4. `ai/tasks/v2.1.0-rc.2-backfill-model-counts/task.md`：本 strict 任务，最终保持 checking、completed_at=null。

- 不包含 install-and-use.md 默认值说明、F :76 措辞及「合法时间戳」精确化 PR；不改代码、测试、契约、PRD、plan.md 或其他文件。
- 三个既有 task 只追加，唯一既有行变更为 #177 的 updated_at。追加内容从仓库外文件读取并去掉末尾换行，由 Python 按字节逐行计算补丁，经编辑工具落盘，不手抄文本。
- 本 task 沿用既有手写记录方式，不调用 TaskStore 写入，不写 `.sbtd/`、active、handoff、ignore 或身份，不改变历史 task 的 branch，不承诺 TaskStore 自动恢复。
- 不提交、不推送，不操作暂存区或历史，不调用平台 CLI，不修改全局配置；临时脚本与验证产物只放 `/tmp`。本轮不读取环境变量值或会话 jsonl 内容。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮适用性与证据 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求前 | not-needed；未完整 grill，仅回填明确的历史记录 |
| book-ddia-data-design | schema、迁移或持久化机制设计前 | not-needed；沿用现有 task 结构，不改 schema 或持久化机制 |
| book-legacy-change-safety | 既有行为修改前 | not-needed；不改运行时行为，以基线逐字节保留检查约束文档追加 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；无生产代码修改或重构 |
| book-release-readiness | 运行时或部署变化，验证后 | not-needed；无运行时、部署或发布变化 |
| project-validation | 编辑后 | 适用；执行 a–f 限定检查、八模块 unittest 与四份 task 原生解析 |
| Code Readability Review／独立 review | check | 无代码或测试改动，单一任务记录范围，不触发独立 review；主会话核对，不冒充独立审查 |

## 验证与剩余边界

- 入口 `pwd && git rev-parse --show-toplevel --abbrev-ref HEAD && git status --short --untracked-files=all && git rev-parse origin/main`：退出码 0；根目录与分支匹配、工作树干净，origin/main 为 `ebc07192ad3c73042e9ecba39965f10f64a99122`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/backfill-model-counts-prepare.py`：退出码 0；四个授权路径及父路径无 symlink、未逃逸，三个既有文件已跟踪且与 origin/main 逐字节一致，新 task 不存在。内部 `git check-ignore --no-index` 无命中、退出码 1；外部文本行数核对为 A 两行加一段、B 一行、C 五行加一段。
- 真实时间来自 `TZ=Asia/Shanghai date +%Y-%m-%dT%H:%M:%S+08:00`，退出码 0；开始时间为 `2026-10-25T17:15:26+08:00`，#177 事件及 updated_at 共用 `2026-10-25T17:15:44+08:00`，不倒填群内决定时间。
- `sbtd-workflow-onboard/scripts/sbtd_task_document.py:135–146`：事件先校验 stateEvent 与时间戳；after_baseline 下 to=done 时，from=checking 或 done 均允许。仓库先例为 `ai/tasks/v2.1.0-rc.2-concurrency-test-race/task.md:79–80` 的 done → done 回填事件；未改解析实现。
- 验证仅为本地未提交工作树证据，不冒充 CI、独立审查、合入或发布。BDD：skipped，无用户可见行为或持久场景变化；lint／format／构建、全仓测试、浏览器／移动端、跨平台与发布不执行，仅文档记录回填。
- rtk：skipped-for-report，使用精确原生命令；Cross-repo context／API Contract／Environment Alignment：not-needed；Mock Strategy：none；Evidence Source：developer-local；Source Revision：dirty；Evidence Publication：local-only。

### a–c：空白、精确字节与新增文字

- `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/backfill-model-counts-validate.py initial-checks`：退出码 0。内部 `git diff --check` 退出码 0、无输出；新 task 另查尾随空白为 0。
- `git diff -U0 origin/main` 退出码 0；以 Python 对原生输出执行与删除行过滤管道等价的筛选，排除文件头后仅有 `-updated_at: '2026-10-25T12:50:50+08:00'`，属于 #177；未执行 shell grep 管道。
- Python 按字节读取 origin/main 原文及外部追加文本，逐段构造预期文件并与工作树完整比较：A、C 的所有原行、frontmatter、既有事件按顺序逐字节保留，新增行仅为指定行及段落空行；B 除 updated_at 一行外全部原字节保留，只追加指定事件；三个文件末尾换行数量不变。不是仅依赖行数或 diff 摘要。
- 扫描 diff 新增行与新 task 全文，禁词、主目录路径、无日期时间归因等限制均 0 命中；不扫描或改写旧文中的历史措辞。

### d：八模块回归

在仓库根通过仓库外 runner 捕获以下原生命令的 stdout／stderr／exit：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_sbtd_task_document tests.test_sbtd_task_legacy_events_notice tests.test_sbtd_task_recovery tests.test_sbtd_task_routing tests.test_sbtd_task_schema tests.test_sbtd_task_state tests.test_sbtd_task_status_sync tests.test_sbtd_task_sync_git
```

- runner 命令为 `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/backfill-model-counts-validate.py unittest`；runner 与 unittest 退出码均 0，`Ran 135 tests in 50.352s`、`OK`，stdout 为空；仅一轮，无失败或重试，未报告 skipped 用例。
- unittest 的 stderr 含预期通知 `旧格式事件，不追溯`，原文保存在 `/tmp/backfill-model-counts-s1-20261025T171526/unittest.json`；此通知来自测试夹具，不是下节四个 task 的解析 stderr，不修改测试来消除通知。

### e：真实 task 解析

以下 PARSE 命令对各文件独立执行，退出码均 0，stderr 均为空，解析前后文件字节不变：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" <path>
```

| path | stdout（完整路径后的字段） | stderr |
|---|---|---|
| `ai/tasks/v2.1.0-rc.2-runtime-perf-default-events/task.md` | `done False 3 2026-10-25T12:50:50+08:00` | 空 |
| `ai/tasks/v2.1.0-rc.2-backfill-docs-bc-pr4/task.md` | `done False 6 2026-10-25T12:50:50+08:00` | 空 |
| `ai/tasks/v2.1.0-rc.2-legacy-criterion-wording-sync/task.md` | `done False 3 2026-10-25T15:13:39+08:00` | 空 |
| `ai/tasks/v2.1.0-rc.2-backfill-model-counts/task.md`（转 checking 前） | `in-progress False 1 None` | 空 |
| `ai/tasks/v2.1.0-rc.2-backfill-model-counts/task.md`（转 checking 后） | `checking False 2 None` | 空 |

- #177 在追加后另独立执行一次同一 PARSE 命令，结果与上表一致；done → done 事件解析成功，未触发恢复 origin/main 的失败分支，不改用正文说明替代事件。

### f：范围与证据边界

- `git status --short --untracked-files=all`：退出码 0，恰为范围节所列三个既有 task 的修改与一个新 task，无额外工作树改动。
- 初轮 a–f 检查与八模块回归完成后，使用真实 `TZ=Asia/Shanghai date +%Y-%m-%dT%H:%M:%S+08:00`（退出码 0）取得 `2026-10-25T17:18:46+08:00`，追加 in-progress → checking 事件，updated_at 同步，completed_at 保持 null。
- 初轮原始命令与输出保留于 `/tmp/backfill-model-counts-s1-20261025T171526/initial-checks.json`、`unittest.json`；绑定实际 HEAD `ebc07192ad3c73042e9ecba39965f10f64a99122`、本工作树及分支，代码未改、工作树含文档修改；不以该本地结果证明后续提交的 CI 或发布状态。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/backfill-model-counts-validate.py checking-checks`：退出码 0；转 checking 后 a–c、e、f 全部通过，四份 task 均符合最终预期，stderr 全空；新 task 的 updated_at 等于末条事件 at，completed_at=null，strict／user 保持。原始输出保留于 `/tmp/backfill-model-counts-s1-20261025T171526/checking-checks.json`。
- 八模块 raw 报告与同 stem 九节中文汇总为 `/tmp/backfill-model-counts-s1-20261025T171526/unittest.json`、`unittest.md`；Final Test Report／Run Summary MD：generated；Targeted Rerun：not-needed；Final Full Rerun：passed，仅指本轮八模块范围。临时补丁和检查脚本在验证后移除，原始报告保留；不承诺临时目录长期保留或自动恢复。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | 产出 | 会话文件 |
|---|---|---|---|---|---|
| 1 | ping（2026-10-25 17:14:19 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-25T09-14-19-286Z_01a17256-e316-77e8-b94e-94c833ed888b.jsonl` |
| 2 | 会话 1（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告 | 三个 task 记录回填与本 task | `2026-10-25T09-14-24-620Z_01a17256-f7ec-70ed-8625-8cf4a9c3e2a4.jsonl` |

每个 omp 会话一行；未使用子代理、advisor；内部辅助 model_usage 记录（如有）由群内交付报告另列。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-25T17:15:26+08:00 | planned | in-progress | 编排方整理；写入者：主会话，开始三个 task 记录回填与本 task 建立 | 基线 `ebc0719`；根目录、分支、干净工作树及授权边界已核对；路径与 ignore 检查通过，既有三文件与基线逐字节一致；解析实现与 done → done 先例已核对。 |
| 2026-10-25T17:18:46+08:00 | in-progress | checking | 编排方整理；写入者：主会话，三个 task 回填与本地 a–f 检查完成，进入检查 | 基线 `ebc0719`；八模块 Ran 135 tests in 50.352s、OK、exit 0；diff 与新 task 空白检查通过，A／C 原字节全部保留、B 仅 updated_at 变更及指定追加；新增文字限制 0 命中，四份 task 初轮解析 exit 0、stderr 空，工作树恰为四个授权文件；详见验证节。 |
| 2026-10-25T18:20:04+08:00 | checking | done | 编排方整理：Reviewy CLEAN 后写入 done；PR #180 | Reviewy CLEAN @ 7113ff49aaa97795f6af9de47f6bac2dfccf5b90（编排方整理）；CI validation run 40182684267 attempt 1 success 13/13（编排方整理） |
