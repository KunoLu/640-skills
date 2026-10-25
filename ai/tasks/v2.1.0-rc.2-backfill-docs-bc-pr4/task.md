---
schema_version: 1
id: v2.1.0-rc.2-backfill-docs-bc-pr4
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：本 PR 采用 strict；omp 主会话为本轮文件唯一 writer 与验证 controller，提交、push、开 PR 由编排方在 omp 之外执行；不启动子代理、不用 advisor。
status: in-progress
branch: docs/v2.1.0-rc.2-backfill-docs-bc-pr4
created_at: '2026-10-25T10:45:43+08:00'
updated_at: '2026-10-25T10:53:09+08:00'
completed_at: null
---

# rc.2：Docs B／C、R2.2 PR-4／F 记录与 plan 更正 strict 回填任务

## 决定

- Lord 2026-10-25 10:39 群内裁定：开本回填 PR。
- 用户 2026-10-25 07:50 群内确认（方案一），Lord 记录：导出时 run／step 等派生行随依据事件一并不导出，task 行与聚合行始终导出，聚合按全部事件计算（PRD §10.3 已随 #175 写明，install-and-use 已随 #176 写明）。
- Lord 2026-10-25 08:05 群内裁定：plan.md :90／:118 的旧派生行措辞在本回填 PR 更正。

## 范围与边界

- 编排方整理：本 PR 五个提交依次为：
  1. 只回填 #175／#176 合入并关闭 docs-b-c task；提交 `8608564` 已完成。
  2. docs-b-c 记录补正（B 分支名、模型计数与辅助 model_usage 行）并建立本 task。
  3. R2.2 task（`ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/task.md`）追加更正事件与说明（:247 事件依据、10000 档审计 not-met 原因、#174 实际数字），不改任何既有事件。
  4. F 回填 task（`ai/tasks/v2.1.0-rc.2-f-backfill/task.md`）:76 正文中 attempt 1 macos-bash-installer 的措辞更正。
  5. `ai/tasks/v2.1.0-rc.2-plan/plan.md` 追加 :90／:118 派生行口径更正。
- 本轮仅执行提交 2 的文件交付：向 `ai/tasks/v2.1.0-rc.2-docs-b-c-exportable/task.md` 插入四行，并新建本 task。docs-b-c 的 frontmatter、既有正文与全部六条状态事件逐字节保留，不追加状态事件；提交 1 的写入保持不变。
- 排除 `sbtd-runtime/tests/runtime_perf.py` 等任何代码改动（另开后续 PR）、PRD（含 :65）、契约、`install-and-use.md`、`index.md`。按仓库现有规则，新 task 不要求 plan.md 任务表行或 index 条目，本 PR 不加。
- 本 task 在提交 2 建立 planned → in-progress 事件；提交 3、4 各追加一条 in-progress → in-progress 进度事件；提交 5 追加最后的 in-progress → checking。各轮在模型记录表追加本会话行；本轮不提前写入后续事件，不关闭本 task。
- 本 task 手写，不调用 TaskStore 写入，不写 `.sbtd/`、active、handoff、ignore 或身份，不生成报告文件；不承诺 TaskStore 重绑定或自动恢复。不运行 gh，不操作暂存区或提交历史，不修改全局配置。
- 未完整调用 grill-with-docs：决定、回填内容、授权范围与验收条件明确，无需重复澄清。无代码、schema、运行时或领域设计变化；不启动子代理、不用 advisor，未执行独立审查。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮适用性 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，文档前 | not-needed；未完整 grill，仅整理明确决定与历史记录，无领域歧义 |
| book-ddia-data-design | schema、迁移或持久化机制设计前 | not-needed；仅记录与计划文档，不改 schema、数据结构或持久化机制 |
| book-legacy-change-safety | 既有运行时行为修改前 | not-needed；不改代码或运行时行为，历史记录按授权纯插入保留 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；无生产代码编辑或重构 |
| book-release-readiness | 运行时或部署变化，验证后 | not-needed；无运行时、部署或发布变化，不宣称发布就绪 |
| project-validation | 文档范围与任务记录解析核验 | 适用；使用指定原生 Python 命令执行 TaskDocument.parse，只读检查 diff、删除行清单与新增行禁词，不调用 TaskStore 写入 |

## 验证与剩余边界

- 入口只读核验：项目根与分支匹配，初始工作树干净；origin/main 为 `1b609bcfeb1bface01cec9eb5877feddf27d6121`，HEAD 为提交 1 `8608564`。两个授权路径及父路径无 symlink，均位于项目内，新 task 原先不存在；`git ls-files --stage` 仅列出 docs-b-c task，`git check-ignore --no-index` 无命中、退出码 1。
- 写前执行指定 `PYTHONDONTWRITEBYTECODE=1 python3 -B -c` 解析命令：从 `sbtd-workflow-onboard/scripts` 导入 `sbtd_task_document`，docs-b-c task 输出 `done False 6 2026-10-25T10:42:57+08:00`。本 task 的 created_at、updated_at 与唯一事件时间取自实际 `TZ=Asia/Shanghai date +%Y-%m-%dT%H:%M:%S+08:00` 输出，晚于 docs-b-c 末条事件。
- 写后分别对两个 task 执行指定 `PYTHONDONTWRITEBYTECODE=1 python3 -B -c` 解析命令：docs-b-c 为 `done False 6 2026-10-25T10:42:57+08:00`，本 task 为 `in-progress False 1 None`。`git diff --check` 无输出、退出码 0；`git diff --stat` 仅列 docs-b-c 的 4 insertions，未跟踪的新 task 另用 `git diff --no-index --stat -- /dev/null <本 task>` 纳入检查；对应 `--check` 无输出，no-index 退出码 1 表示存在新增差异。
- 全部 diff 与 docs-b-c 单文件 diff 分别执行 `grep '^-[^-]'`：均无输出、退出码 1，删除行清单为空。Python 按字节逐行比较 HEAD，确认仅在原第 32、70、72 行之后分别插入 1、2、1 行，frontmatter 与状态事件表完全不变。对 diff 新增行及新 task 全文执行禁词与主目录路径 grep：0 命中；`git status --short --untracked-files=all` 仅列两个授权文件。辅助核验脚本首次因非 ASCII bytes 字面量触发 SyntaxError、未执行检查；改用 UTF-8 编码后核验通过，未写脚本文件。
- 验证边界：仅本地文档与任务解析证据，不冒充 CI、独立审查、合入或发布结论。BDD、构建、代码 lint、单元测试、浏览器／移动端与完整 E2E：skipped，仅文档记录补正，无代码、UI 或运行时行为变化。API Contract／Cross-repo context：not-needed；Mock Strategy：none；rtk：not-needed，使用精确原生 git 与指定 Python 命令。Evidence Source：developer-local；Source Revision：dirty；Environment Alignment：not-needed；Evidence Publication：local-only；不生成正式测试报告。
- 提交 3 入口核验（编排方整理）：HEAD 为提交 2 `811a21b`，分支匹配、初始工作树干净；两个授权 task 均已跟踪，路径及父路径无 symlink、位于项目内，`git check-ignore --no-index` 均无命中、退出码 1。写前按指定原生 Python 命令解析，R2.2 为 `in-progress False 53 None`，本 task 为 `in-progress False 1 None`。本轮仅追加历史记录，不重绑定 R2.2 既有 branch，不调用 TaskStore；事件时间与 updated_at 取自实际 `TZ=Asia/Shanghai date +%Y-%m-%dT%H:%M:%S+08:00` 输出，晚于两文件既有末条事件。`git show --stat 7cbb929`、`git show --numstat --format= 7cbb929` 与 `%cI` 已只读核对；R2.2 task 的 224 个变更行实际为 +223／−1。
- 提交 3 写后核验（编排方整理）：分别执行指定 `PYTHONDONTWRITEBYTECODE=1 python3 -B -c` 解析命令，R2.2 为 `in-progress False 54 None`（原 53 条事件加 1），本 task 为 `in-progress False 2 None`。`git diff --check` 退出码 0；`git diff --stat` 只含两个授权 task；全部 diff 与 R2.2 单文件 diff 的删除行检查均仅有各自旧 updated_at。按字节比较 `git show HEAD:<path>` 与工作树，原第 247 行含换行符不变，全部既有事件及其余既有正文逐字保留，新增位置符合授权。新增行禁词与主目录路径 grep 为 0 命中，退出码 1；未跟踪文件清单为空。辅助检查首次把其他章节的历史事件摘录也计入状态事件，触发断言失败；限定到「状态事件」章节后通过，未改正文规避检查、未落盘脚本或报告。BDD、构建、lint、单元测试与 E2E 均 skipped：仅文档记录补正，无产品行为变化；rtk not-needed，使用精确原生命令；证据仅为本地 dirty 工作树检查，不是新 CI 或发布证明。
- 提交 4 核验（编排方整理）：入口 HEAD 为提交 3 `ebc3bb3`，分支匹配、工作树干净；两个授权 task 均已跟踪、无 ignore 匹配，路径及父路径无 symlink。先解析 HEAD 的 F task 得到 `done False 6 2026-10-25T02:23:12+08:00`；写后分别执行指定 `PYTHONDONTWRITEBYTECODE=1 python3 -B -c` 解析命令，F 结果与 HEAD 相同，本 task 为 `in-progress False 3 None`。Python 按字节比较确认 F 仅第 76 行指定分句替换，其余字节、frontmatter 与全部事件不变；本 task 仅 updated_at 变更及授权位置追加，既有事件保留。`git diff --check` 退出码 0，`git diff --stat` 只含两个授权文件；`git diff -U0 -- ai/tasks/v2.1.0-rc.2-f-backfill/task.md` 仅第 76 行一删一增。`grep '^-[^-]'` 仅列旧 updated_at，因 F 正文为 Markdown 列表、删除行以双减号起始，另用 Python 排除文件头后确认全部删除行恰为旧 updated_at 与 F 原第 76 行。新增行禁词与主目录路径 grep 为 0 命中、退出码 1；无未跟踪或暂存改动。新增事件及 updated_at 使用实际 `TZ=Asia/Shanghai date +%Y-%m-%dT%H:%M:%S+08:00` 输出，晚于既有末条事件。本条补入后再次执行相同解析与边界检查。历史 CI 依据为编排方整理，本轮未执行 gh；BDD、构建、lint、单元测试与 E2E skipped，仅文档更正，无产品行为变化；rtk not-needed，使用原生命令。证据为 developer-local／dirty／local-only，不是新 CI、独立审查或发布证明，不生成报告文件。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | 产出 | 会话文件 |
|---|---|---|---|---|---|
| 1 | ping（2026-10-25 10:42:00 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-25T02-42-00-922Z_01a170ef-b85a-7335-920c-eb0be0a01cea.jsonl` |
| 2 | 提交 1 会话（docs-b-c 合入回填） | openai-codex/gpt-6-astra（high） | 8／19（编排方整理，按 jsonl 统计；无 model_usage 记录） | docs-b-c task 合入回填 | `2026-10-25T02-42-31-999Z_01a170f0-31bf-73d7-9e3d-bc2732619e90.jsonl` |
| 3 | 提交 2 会话（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告 | docs-b-c 记录补正、建立本 task | `2026-10-25T02-45-20-882Z_01a170f2-c572-7456-bfcf-982e9fd2b3c6.jsonl` |
| 4 | 提交 3 会话（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告 | R2.2 task 记录补正 | `2026-10-25T02-49-16-483Z_01a170f6-5dc3-7674-b6e6-3bdc370727d3.jsonl` |
| 5 | 提交 4 会话（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告 | F task :76 措辞更正 | `2026-10-25T02-52-46-744Z_01a170f9-9318-7571-adb0-311f5b0c8a4c.jsonl` |

模型记录更正（编排方整理，按 jsonl 统计）：第 3 行提交 2 会话实际 14／25，无 model_usage 记录；原「未知」原文保留。
模型记录更正（编排方整理，按 jsonl 统计）：第 4 行提交 3 会话实际 14／33，无 model_usage 记录；原「未知」原文保留。

每个 omp 会话一行；omp 会话未使用子代理；内部辅助 model_usage 记录如有另列一行。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-25T10:45:43+08:00 | planned | in-progress | 编排方整理：建立回填 strict 任务，提交 1 `8608564` 已完成，开始提交 2 | 基线 `1b609bc`；提交 1 `8608564`；本轮入口根目录、分支、干净工作树、路径与 ignore 检查通过，写前 docs-b-c 只读解析为 done、非旧格式、六条事件；本轮解析与差异检查记录见验证与剩余边界。 |
| 2026-10-25T10:49:48+08:00 | in-progress | in-progress | 编排方整理：提交 3——R2.2 task 追加记录补正事件与说明节 | 提交 2 `811a21b` 已完成；R2.2 task 仅 updated_at 一行变更，第 247 行及全部既有事件逐字保留；解析与检查结果见验证节。 |
| 2026-10-25T10:53:09+08:00 | in-progress | in-progress | 编排方整理：提交 4——F 回填 task :76 attempt 1 macos-bash-installer 措辞更正 | 提交 3 `ebc3bb3` 已完成；F task 仅第 76 行一处分句替换，frontmatter 与事件不变；依据 gh run view 40115693146 --attempt 1 只读核实（编排方整理）；解析与检查结果见验证节。 |
