---
schema_version: 1
id: v2.1.0-rc.2-runtime-perf-default-events
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：本轮采用 strict；omp 主会话为授权文件唯一 writer 与验证 controller，不启动子代理、不用 advisor；提交由编排方在 omp 之外执行。
status: checking
branch: fix/v2.1.0-rc.2-runtime-perf-default-events
created_at: '2026-10-25T12:06:58+08:00'
updated_at: '2026-10-25T12:17:34+08:00'
completed_at: null
---

# rc.2：runtime_perf 默认事件数与规模说明

## 决定

- Lord 2026-10-25 11:25 群内裁定：`--events` 默认值改为 `10_000`（此前未找到用户给出的数值；用户可在 PR 上更改）；无 `--events` 的运行须标注「未达 1M 档」；显式 `--events 1000000` 行为不变。
- 未完整调用 grill-with-docs：需求、授权范围与兼容性条件明确，源码可回答规模判定问题，无新增领域歧义。

## 范围与边界

- 仅修改 `sbtd-runtime/tests/runtime_perf.py`、必要的 `sbtd-runtime/tests/test_runtime_perf_smoke.py` 与本 task；不改 `sbtd-runtime/docs/install-and-use.md`（其命令显式传 `--events 1000000`）、PRD、契约、schema、golden、plan.md、index 或其他 task。
- 按 `docs/prd/sbtd-workflow-v2-task-status-sync.md` 第五节第 5 点，done 在 Reviewy CLEAN 后由仅改本 task.md 的提交写入，不在本 PR 当前提交中；PRD 未要求本 PR 回填 #177 合入（plan.md:8 的例行回填约定已按该 PRD 停用），本 PR 不回填 #177（编排方整理）。
- 本轮仅建立一条 planned → in-progress 事件；会话 2 补充无参数默认运行等证据后再转 checking。本轮 completed_at 保持 null。
- 手写本 task，不调用 TaskStore 写入，不写 `.sbtd/`、active、handoff、ignore 或身份；不承诺 TaskStore 自动恢复。不操作暂存区或历史，不提交、不推送、不调用 gh，不修改全局配置。临时文件和运行产物仅放 `/tmp/rtperf.TH7Bu6` 或测试创建的仓库外临时目录。

### 实现决定与保留路径

- 仅以请求事件数 `< 1_000_000` 触发新增 `reference_scale_note`，默认运行和显式小规模请求一致标注「未达 1M 档」。`write_report()` 在 raw JSON 与中文摘要写出同一说明；CLI 在原最终 JSON 后追加说明行。
- 小规模请求在 seed 前保留仅含 requested_events 的 dataset，seed 成功后由原返回值覆盖；因此 seed 失败也能标注，不假造实际事件数。1M 及更大请求不增加这个初始字段，不改变原失败路径。
- 不以实际事件数触发新标注：请求 1M 但因 seed 软时限截断时也必须保持旧输出。`seed()` 的 requested_events／events／truncated 保持原实现；实际 CSV event 行数的 `>= 1_000_000` 阈值继续独立决定 `export_csv.reference_scale_status`，不降低参考规模。
- CSV full-buffer／not streaming 的 reason、eligible=False、latency_status、streaming_requirement、audit 索引说明全部不改；报告 stem 仍直接使用 args.events，显式 1M 时相同。
- 1M 路径逐处对比：默认值仅作用于省略参数；小规模 dataset 初始化分支不进入；write_report 标注分支不进入、摘要插值为空串；stdout 附加行分支不进入。因此相同 report 下字典、JSON、MD 不变，给定相同路径与测量值时原 stdout JSON 与 stem 构造不变。
- 字节对比固定相同合成 report；真实跨版本运行的 source_hashes 会反映源码变化，created_at／seconds 等也依赖真实运行，不伪造为旧值或宣称跨次完整实测报告天然相同。

### 行为场景与验证映射

- Scenario：省略事件数。Given 有效输出目录；When 解析未提供 `--events` 的命令；Then requested_events 为 10000，正常或 seed 失败的报告与 CLI 均说明「未达 1M 档」。本轮参数解析与失败路径检查；完整默认实跑留给会话 2。
- Scenario：显式小规模。Given 请求 101 事件；When 运行真实 CLI；Then 原数据／CSV／测量断言保持，raw JSON、同 stem 中文摘要、stdout 均有规模说明。映射既有 smoke 用例。
- Scenario：保持百万请求。Given 请求 1000000（或更大），CSV event 行数为 11500 或 1000000；When 写出相同合成 report；Then 新旧字典、JSON 和 MD 逐字节一致，未增加小规模说明。映射仓库外对比检查，不实跑百万事件。
- BDD 使用中文场景与 English 关键词；本轮授权不包含独立 .feature／既有规范文件，场景留在本 task 并关联现有 unittest，不引入新 runner，不冒充产品 BDD 全量验收。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮判定与结论 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求前 | not-needed；未完整 grill，无领域规则变更或歧义 |
| book-ddia-data-design | 持久化、schema、迁移或跨服务设计前 | not-needed；仅本地测量报告新增条件说明，不改变存储机制、产品 schema 或服务流 |
| book-legacy-change-safety | 既有工具行为变化、1M 字节兼容风险，编辑前 | characterized；已完整阅读工具并运行旧版参数／合成报告，保留既有 smoke，选用旧新字节比较安全网；无需 seam |
| book-refactoring-pass | 既有测试工具修改前，保守执行 | proceed／normal；no refactor needed；集中报告说明，小规模分支隔离，不重构测量与生成逻辑 |
| book-release-readiness | 生产运行时或部署变化，验证后 | not-needed；只改 developer-local 测试工具，不改生产运行时／部署，不宣称发布就绪 |
| gherkin-bdd／ponytail | CLI 规模含义变化，实施前 | 上述三个场景约束改动，标准库与现有 unittest，拒绝新增抽象或测量优化 |
| project-validation | 实施后 | 执行指定 smoke、合成报告字节比较、参数解析、可用 Ruff 与 task 解析；证据仅本地 |
| Code Readability Review／独立 review | check | 主会话自审；单一测试工具子系统，不触发强制独立 review；不启动子代理或 advisor，不冒充独立审查 |

## 验证与剩余边界

- 入口核验：根目录与分支匹配，HEAD／origin/main 均为 `e85873c4f06ac4b17e90ebfcb41dc4d057316068`，初始工作树干净；三个授权路径及父路径无 symlink、未逃逸，两个 Python 文件已跟踪，新 task 不存在；`git check-ignore --no-index` 无命中、退出码 1。
- LSP references 调用返回无语言服务器；改用源码与限定范围调用点搜索：write_report 由本文件 main 调用，smoke 通过子进程执行 CLI。未变更函数签名或迁移调用方。
- 写前 `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/rtperf.TH7Bu6/compare.py baseline` 退出码 0：旧默认 1000000；请求 1M、CSV event 为 11500／1000000 的旧 JSON 与 MD 无新标注。旧版通过 `git show origin/main:sbtd-runtime/tests/runtime_perf.py` 保存到仓库外，导入路径包含 sbtd-runtime 与 sbtd-runtime/tests。
- 当前记录为实施前基线；实际 smoke、兼容比较、Ruff 与最终解析结果在执行后追加。本轮不跑百万事件，不将合成比较当作百万规模性能证明。
- 实施后 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest sbtd-runtime/tests/test_runtime_perf_smoke.py`：Ran 2 tests in 7.358s，OK，退出码 0。真实 101 事件 CLI 保留全部原断言，新增 raw JSON、中文摘要和 stdout 的规模说明断言；没有百万事件实跑或模拟服务替代。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/rtperf.TH7Bu6/compare.py compare`：退出码 0。请求 1000000／1000001 × CSV event 11500／1000000 共四组，原／新 report 字典不变，生成 JSON 和 MD 逐字节一致；请求 10000、实际 10000／100 的两组中，仅新版两类报告包含「未达 1M 档」。从 main 提取真实 parser 构建语句，仅解除独立的 output 必填约束以解析空参数，确认 `[] → 10000`、`['--events','1000000'] → 1000000`。未抽取或替换生产实现中的判定函数。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B sbtd-runtime/tests/runtime_perf.py --samples 1 --seed-seconds 0.000000001 --output /tmp/rtperf.TH7Bu6/default-seed-failure`：实际退出码 1，符合预期负向场景；省略 --events，raw dataset.requested_events=10000，execution=failed，stdout events=null；raw JSON、同 stem 中文摘要与 stdout 均有规模说明。保留失败原始产物，不将该场景写成完整默认规模执行成功。
- 仓库未发现 pyproject.toml／ruff.toml／.ruff.toml；沿用既有检查方式，已有 project-validation 环境中的 ruff 0.17.1 可用。执行 `RUFF_NO_CACHE=true ruff check sbtd-runtime/tests/runtime_perf.py sbtd-runtime/tests/test_runtime_perf_smoke.py` 与 `RUFF_NO_CACHE=true ruff format --check sbtd-runtime/tests/runtime_perf.py sbtd-runtime/tests/test_runtime_perf_smoke.py`（ruff 指向该已有环境）：分别为 All checks passed、2 files already formatted，退出码均 0，未安装依赖或生成仓库内缓存。
- Code Readability Review：通过主会话自审；说明文本只定义一次，摘要与 stdout 复用，三个小规模分支保持明确，原测量路径无改动；未新增抽象、产品优化或测试框架。非生产代码改动，ponytail-review 独立生产 diff 门 not-needed；未执行独立审查。
- 按入口要求的 `PYTHONDONTWRITEBYTECODE=1 python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" ai/tasks/v2.1.0-rc.2-runtime-perf-default-events/task.md` 解析：`in-progress False 1 None`，退出码 0。`git diff -U0 origin/main | grep -v '^--- ' | grep '^-'` 退出码 0，仅列原摘要的实际规模行与原 default=1_000_000 行两条删除；未弱化或删除原测试断言。
- `git diff --check` 退出码 0；`git status --short --untracked-files=all` 恰列三个授权文件；`git diff --cached --name-only` 为空。task 禁词／主目录路径检查与汇总九节顺序检查通过，退出码 0；最终记录补入后再次执行解析和限制检查。
- 原始输出与九节中文汇总保留于仓库外 `/tmp/rtperf.TH7Bu6/verification.json`、`verification.md`；合成报告与真实失败场景原生 JSON／同 stem MD 同目录保留。临时比较脚本与旧源码副本在验证后移除，不清理任何既有数据。
- BDD：traceable（本 task 场景 → 既有 unittest／临时对比）；rtk：skipped-for-report，使用精确原生命令；Cross-repo context／API Contract：not-needed；Mock Strategy：none；E2E Mode：smoke-only。Evidence Source：developer-local；Source Revision：dirty；Environment Alignment：not-needed；Evidence Publication：local-only；Final Test Report／Run Summary MD：generated；Final Full Rerun：passed，仅指本轮计划范围。
- 剩余边界：完整默认运行留给会话 2，百万事件运行按边界不执行；全仓测试、浏览器／移动端、Mac／Windows、CI 与发布均未执行，仅修改本地测试工具。小规模 CLI 由单行 JSON 变为 JSON 后追加说明行；1M 及更大请求无此附加输出。工作树未提交，status 保持 in-progress、completed_at=null，不声明 checking／done／发布就绪。

### 会话 2：默认运行、独立兼容比较与本地测试

- Lord 2026-10-25 11:25 群内裁定：默认值为 10_000；本会话沿用 strict，仅追加本 task 的事实证据并转 checking，不修改代码、会话 1 正文或既有状态事件。未完整调用 grill-with-docs：需求与验证边界明确，无新增领域歧义；沿用上方 Book Gate Plan，不将会话 1 的门记录改写为本会话执行。
- 入口 HEAD 为提交 1 `dbc339b795e04b9979772aee26faddc232e38daf`，origin/main 为 `e85873c4f06ac4b17e90ebfcb41dc4d057316068`，分支匹配且工作树干净。授权 task 已跟踪，路径无 symlink；`git check-ignore --no-index ai/tasks/v2.1.0-rc.2-runtime-perf-default-events/task.md` 无命中，退出码 1。手写 task，不调用 TaskStore 保存本任务，不写工作树的 `.sbtd/`、index 或其他 task。
- 以下命令工作目录均为 `/workspace/640-skills-runtime-perf-default`。先执行 `mktemp -d /tmp/rtperf2.XXXXXX`，退出码 0，得到 `/tmp/rtperf2.gtSYue`；原始输出均留在该仓库外目录。全部 Python 命令使用 `python3 -B` 并设置 `PYTHONDONTWRITEBYTECODE=1`。

#### 无 --events 默认运行

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B sbtd-runtime/tests/runtime_perf.py --samples 2 --seed-seconds 60 --output /tmp/rtperf2.gtSYue
```

- 退出码 0，stderr 为空；stdout 完整两行：

```text
{"report": "/tmp/rtperf2.gtSYue/runtime-perf-10000-fix_v2.1.0-rc.2-runtime-perf-default-events-20261025T041346236848Z.json", "execution": "completed", "events": 1300, "seconds": 69.79541150700243}
未达 1M 档：请求事件数低于 1_000_000；本次结果不代表 1M 档通过。
```

- 上述 raw JSON 的 `dataset`：`requested_events=10000`、实际 `events=1300`、`truncated=true`、`tasks=13`、`steps=130`、`seed_limit_seconds=60.0`、`seed_seconds=62.72085263900226`。种子软时限触发截断；execution=completed 只表示这次截断数据集上的测量流程完成，不表示 10000 档或 1M 档完成。
- `reference_scale_note` 原文：`未达 1M 档：请求事件数低于 1_000_000；本次结果不代表 1M 档通过。`
- `csv_rows` 原值：`{"metadata": 17, "metric": 31, "task": 13, "step": 130, "event": 1300}`；`measurements.export_csv.reference_scale_status="not-measured"`。其 `status="not-measured"`、`latency_status="met"`、`streaming_requirement="not-met: full buffered generation"` 保持独立，不能用延迟结果替代规模或流式要求。
- 同 stem 中文摘要 `.md` 第 7 行原文摘录：`规模说明：未达 1M 档：请求事件数低于 1_000_000；本次结果不代表 1M 档通过。`

#### 显式百万参数与独立合成比较

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/rtperf2.gtSYue/compare.py
```

- 退出码 0。脚本分别执行 `git show origin/main:sbtd-runtime/tests/runtime_perf.py` 与 `git show HEAD:sbtd-runtime/tests/runtime_perf.py`，保存到 `/tmp/rtperf2.gtSYue/old_runtime_perf.py`、`/tmp/rtperf2.gtSYue/new_runtime_perf.py` 后导入；导入路径包含仓库的 `sbtd-runtime` 与 `sbtd-runtime/tests`。未执行百万事件运行。
- 对相同合成 report，请求事件数 `1000000`／`2000000` × CSV event 数 `11500`／`1000000` 共四组，分别调用原版与新版 `write_report()`：两版 report 字典均不变，`.json` 与 `.md` 逐字节一致，均无「未达 1M 档」。请求 `10000`、实际及 CSV event 数 `10000`／`100` 的两组，仅新版 JSON 与 MD 含该说明。合成字段不代表百万级测量结果。
- 从两个版本的真实 main 提取 parser 构建语句，仅解除 `--output` 必填约束以便解析空列表：旧版 `[] → 1000000`，新版 `[] → 10000`，两版 `['--events','1000000'] → 1000000`。未替换生产判定函数。

| 情形 | 参数与数据证据 | 输出差别及证据边界 |
|---|---|---|
| 无参数默认运行（省略 --events） | 真实 CLI 请求 10000，实际 1300，truncated=true，exit 0 | stdout、raw JSON、中文摘要均有「未达 1M 档」；CSV reference_scale_status=not-measured；种子截断，不能视为 10000 档或 1M 档完成 |
| 显式 --events 1000000 | 真实 argparse 结果为 1000000；合成 CSV event=11500／1000000 | 两版 JSON 与 MD 逐字节一致，无新增小规模说明；另以请求 2000000 两组核对同一边界；未实跑百万事件，不宣称百万级性能结果 |

#### 两组 unittest

tests 目录实际位于仓库根；task 测试自行将 `sbtd-workflow-onboard/scripts` 加入 sys.path，因此在上述仓库根执行，无需另设 PYTHONPATH。测试使用仓库外隔离临时项目；不将测试夹具写入本工作树。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest sbtd-runtime/tests/test_runtime_perf_smoke.py
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_sbtd_task_document tests.test_sbtd_task_legacy_events_notice tests.test_sbtd_task_recovery tests.test_sbtd_task_routing tests.test_sbtd_task_schema tests.test_sbtd_task_state tests.test_sbtd_task_status_sync tests.test_sbtd_task_sync_git
```

- runtime smoke：退出码 0，`Ran 2 tests in 7.065s`，`OK`，stdout 为空。
- task 八模块：退出码 0，`Ran 135 tests in 52.197s`，`OK`，stdout 为空；stderr 中「旧格式事件，不追溯」通知保留在原始证据中，不是测试失败。两组未报告失败或跳过，未重试。
- 本轮原始 stdout／stderr／exit 与完整命令保留在 `/tmp/rtperf2.gtSYue/default-run.json`、`compare.json`、`runtime-smoke.json`、`task-unittest.json`；合并原始证据与同 stem 九节中文汇总为 `/tmp/rtperf2.gtSYue/verification.json`、`verification.md`，合成 JSON／MD 保留于 `old/`、`new/`。临时比较脚本与旧新源码副本在验证后移除，原始报告保留。
- BDD：traceable，沿用本 task 的中文场景与 English 关键词；rtk：skipped-for-report，使用原生命令；E2E Mode：smoke-only；Mock Strategy：none（合成报告比较不冒充运行时实测）；Cross-repo context／API Contract／Environment Alignment：not-needed。Evidence Source：developer-local；本轮代码在 `dbc339b` 上执行，交付仅 task 记录变化，Source Revision：dirty；Evidence Publication：local-only。Final Test Report／Run Summary MD：generated；Final Full Rerun：passed，仅指本会话计划范围。
- 剩余边界：不实跑百万事件，不执行全仓测试、CI、跨平台、浏览器视觉或发布；本会话无代码修改，不重复 lint／format 或生产代码审查门。不启动子代理、不使用 advisor，不宣称独立审查、done 或发布就绪；本 task 转 checking，completed_at 保持 null。会话 1 的历史结论按原文保留，以本小节补充当前事实。
- task 解析使用与会话 1 相同的完整 `TaskDocument.parse()` 命令（路径仍为本 task），退出码 0，实际输出 `checking False 2 None`；`git diff --check` 退出码 0；`git diff -U0 HEAD | grep -v '^--- ' | grep '^-'` 退出码 0，仅列 `-status: in-progress` 与 `-updated_at: '2026-10-25T12:09:25+08:00'`，无正文删除。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/rtperf2.gtSYue/check.py` 退出码 0：逐字节核对会话 1 正文、模型记录与原状态事件全部保留，created_at 不变；新增行禁词与主目录路径检查通过；九节中文汇总顺序、无占位符及 model_usage=0 检查通过。`git status --short --untracked-files=all` 仅列本 task 修改，`git diff --cached --name-only` 为空。原始检查结果保留于 `/tmp/rtperf2.gtSYue/record-checks.json`；补入本段后再次核对解析、diff 与范围，检查脚本随后移除。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | 产出 | 会话文件 |
|---|---|---|---|---|---|
| 1 | ping（2026-10-25 12:04:08 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-25T04-04-08-197Z_01a1713a-e785-722d-a35c-8ad474d2e5e7.jsonl` |
| 2 | 会话 1（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告 | 代码改动、测试与本 task | `2026-10-25T04-04-57-789Z_01a1713b-a93d-7597-add3-dd173102da5a.jsonl` |
| 3 | 会话 1 内部辅助 model_usage | typesafe/jev-latest（thinking 不可考） | 2 次调用（purpose find，不计入主会话 assistant 消息／toolCall） | 限定范围源码检索；只读核实本会话 type=model_usage 两条 | `2026-10-25T04-04-57-789Z_01a1713b-a93d-7597-add3-dd173102da5a.jsonl` |
| 4 | 会话 2（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告 | 默认运行证据、测试与转 checking | `2026-10-25T04-13-01-074Z_01a17143-0912-7163-8f31-489dc201560e.jsonl` |

每个 omp 会话一行；omp 会话未使用子代理；内部辅助 model_usage 记录如有另列一行。

会话 1 实际计数见群内交付报告（编排方整理）。会话 2 落盘前只读解析本会话 jsonl，`type=model_usage` 条数为 0，未新增内部辅助模型行。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-25T12:06:58+08:00 | planned | in-progress | Lord 2026-10-25 11:25 群内裁定；写入者：会话 1 主会话，开始默认事件数调整、兼容性验证与记录 | 基线 `e85873c`；入口根目录、分支、干净工作树、路径与 ignore 检查通过；旧版参数解析与合成报告基线检查退出码 0，详见验证与剩余边界。 |
| 2026-10-25T12:17:34+08:00 | in-progress | checking | Lord 2026-10-25 11:25 群内裁定；写入者：会话 2 主会话，实现与本地验证完成，进入检查 | 提交 1 `dbc339b`；无 --events 默认运行 exit 0，requested_events=10000，events=1300，truncated=true；四组百万及以上合成 JSON/MD 字节一致，两组小规模仅新版含说明，argparse 检查通过，exit 0；runtime smoke 2 tests OK、task 八模块 135 tests OK，退出码均 0；详见会话 2 验证小节。 |
