---
schema_version: 1
id: v2.2.0-rc.1-omp-session-parse
workflow_mode: strict
mode_source: user
mode_note: 本轮任务指令明确全程 strict；640 于 2026-11-12 在 640-skills 群确认做 v2.2.0-rc.1，本任务为其中第
  1 项（omp 会话解析）
status: "checking"
branch: feat/v2.2.0-rc.1-omp-session-parse
created_at: '2026-11-13T13:33:23.229821+08:00'
updated_at: "2026-11-13T15:03:27.667559+08:00"
completed_at: null
---
# v2.2.0-rc.1 omp 会话解析：18.19.0 格式核对

## 目标与范围

640 于 2026-11-12 在 640-skills 群确认做 v2.2.0-rc.1，本任务是其中第 1 项：让 sbtd-runtime/omp_adapter.py 正确解析 omp 18.18.x 起的会话文件格式。本任务分轮执行。第一轮（本轮）只写任务文件并登记索引，完成现状调查与真实会话实测：当前适配器认哪些记录、跳过哪些、跳过时有没有计数或原因；用真实 18.19.0 会话文件统计各类型出现次数并实际导入对照。不改代码、文档、测试、CHANGELOG。后续实施轮按「逐项改动清单」执行，不 commit、不 push、不开 PR、不用子代理，除非 640 另行授权。

未完整调用 grill-with-docs：任务内容、宿主版本、冒烟事实与交付边界均已明确，无领域歧义。

## 背景事实

- 2026-11-12 Lord 在 640-skills 群提出 v2.2.0 三项，640 确认做 v2.2.0-rc.1：第 1 项 omp 会话解析（本任务）；第 2 项 AGENTS.md 遵守 PI_CODING_AGENT_DIR（不在本任务）；graft 项已由 #219 完成。
- 2026-11-12 omp 18.19.0 冒烟（门禁 PR #218 的证据，记录在 ai/tasks/v2.2.0-rc.1-host-gate-omp-18190/task.md）：会话 12 行；第 1 行 type=title 且无 id 字段（18.19.0 新出现，加 --no-title 也有）；第 2 行 session 头 version 3；适配器回执 records_read=12、records_skipped=8、events_emitted=2、accepted=2，再次导入 duplicate=2。适配器能跑通但跳过 8 行，本任务查清这 8 行分别是什么、该不该跳。
- 2026-11-13 本机留有 16 个 omp 18.19.0 真实会话文件（v220-graft 任务各轮产出，sessions-r1 至 sessions-r3h 共 16 个目录各一份）。本轮以只读方式统计与试导入；会话文件不复制进仓库，本文件不写它们的路径，统计只写数字与字段名，不贴会话正文。

## strict mode 落实方式

- 任务文件在开工前经仓库 TaskStore 库 API（sbtd-workflow-onboard/scripts/sbtd_task_state.py 的 TaskStore.create）创建并落盘；阶段转换用 `transition()` 记录真实状态事件，不手改状态时间。
- 验证证据（命令、结果、失败归因）写入本文件；Book Gate Plan 已列。
- 状态停在 planned，实施轮开始后再按真实进度转换。

## 实测发现（2026-11-13 本轮调查）

### 适配器现状（sbtd-runtime/omp_adapter.py）

- 认三类记录：
  - `type=session`（:172-176）：消费，取 id 作 session_id；不校验 version；id 非 str 时静默不取值也不计跳过。
  - `type=message` 且 role=assistant（:184）：遍历 content 列表，只处理 `type=toolCall` 项——id、name 均 str 且 `tool:<name>` 不超过 128 字符 → invocation.started；name=read 且 arguments.path 以 `skill://` 开头 → 另产 skill.loaded。text/thinking 等其他块静默忽略、不计数；content 非列表则整条跳过并计数（:187）。
  - `type=message` 且 role=toolResult（:262）：message.toolCallId 与记录 id 均 str → invocation.finished（isError=true → failed；duration_ms 为两条记录时间戳差）；字段缺失则跳过并计数（:266）。
- 其余一律 records_skipped+1：坏 JSON 行（:166）、非 dict 行（:169）、非 message 类型（:177-179，含 title、model_change、thinking_level_change、custom、custom_message）、其他 role 的消息（:313，含 user）。toolCall 缺 id/name（:195）与 component_id 超长（:199）也计入同一计数。
- 跳过只有总数计数，没有按类型或原因的细分：「不认识的新类型」与「认识的形状缺字段」混在同一个 records_skipped 里。
- host_version 取自记录的 runtime.version（:136-140）；session 头不带 runtime，其 version 字段不参与任何判断。
- 测试与文档：tests/test_omp_adapter.py 夹具为 18.11.1 形状（toolCall id 含「|」）；docs/host-adapters.md:25-34 为映射清单，:30 写明「其余记录类型与坏尾行跳过并计数」；spec/r1.2b-host-adapter-scenarios.md:46 起为 OMP 节，:91 附近是未识别类型记录与坏行跳过计数的场景。

### 16 个真实 18.19.0 会话文件的统计

2026-11-13 只读统计，共 2751 行，无坏 JSON 行。16 个文件中 sessions-r1 与 r1b、sessions-r2 与 r2b、sessions-r3/r3b/r3c/r3c2 分别同一会话 id（同一会话不同时刻的快照，行数递增），其余各自独立；统计不含本任务自己的会话。

顶层 type 合计：

| type | 次数 | 适配器处理 |
|---|---|---|
| message | 1695 | 按 role 映射或跳过 |
| custom | 987 | 跳过并计数 |
| title | 16 | 跳过并计数 |
| session | 16 | 消费（取 session_id） |
| model_change | 16 | 跳过并计数（runtime.version 用于 host_version） |
| thinking_level_change | 16 | 跳过并计数 |
| custom_message | 5 | 跳过并计数 |

每文件各 1 条 title、session、model_change、thinking_level_change；custom_message 只出现在 sessions-r2、r2b、r3d。

message 明细：role=assistant 743、role=toolResult 928、role=user 24。assistant content 块：text 1111、thinking 550、toolCall 928。toolCall 按 name：bash 619、read 169、edit 116、grep 12、write 10、glob 2。toolResult 的 isError=true 共 18（bash 16、write 1、edit 1），其余 910 为 false。

字段形状（只列字段名与值特征，不含内容）：

- title：`{type, v, title, updatedAt, pad}`，v=1，无 id——16 个文件全部如此，与门禁冒烟记录一致。
- session：version=3，`{cwd, id, timestamp, type, version}`，无 runtime。
- model_change：parentId 为 null，带 runtime.version。
- thinking_level_change：`{type, id, parentId, timestamp, runtime, thinkingLevel, configured}`，configured 为 null。
- custom 的 customType 分布：tool_execution_start 928、session_exit 24、date-cwd-reminder 18、system-prompt-digest 17。
- custom_message：`{type, customType, content, display, details, attribution, id, parentId, timestamp, runtime}`。
- toolCall 项比 18.11.1 夹具多一个 intent 键；id 全部为 str 且不含「|」（夹具 id 含「|」，形状差异不影响解析）。
- thinking 块为 `{type, thinking, thinkingSignature}`；toolResult 的 message 多 content、details、timestamp 键。
- message 时间戳全部符合 RFC 3339 带时区（Z 结尾）。
- 每个会话文件旁有同名目录（<会话 id>/）存放编号的 .bash.log 工具输出日志；适配器只读显式给出的 .jsonl，不涉及该目录。

### 真实导入回执

本轮用当前适配器对 5 个真实文件实际导入：每个文件用临时目录下独立的 runtime home（按既有 facade 做法写 config.json 开启 observation），走 CLI 真实 lease 守卫（omp 18.19.0，会话均已结束，held 为空），exit 全为 0。

| 文件 | 行数 | records_read | records_skipped | events_emitted | accepted | duplicate | conflict | rejected | dropped |
|---|---|---|---|---|---|---|---|---|---|
| sessions-r1 | 96 | 96 | 42 | 70 | 70 | 0 | 0 | 0 | [] |
| sessions-r2 | 404 | 404 | 149 | 281 | 281 | 0 | 0 | 0 | [] |
| sessions-r2c | 46 | 46 | 21 | 28 | 28 | 0 | 0 | 0 | [] |
| sessions-r3d | 166 | 166 | 64 | 112 | 112 | 0 | 0 | 0 | [] |
| sessions-r3h | 54 | 54 | 25 | 36 | 36 | 0 | 0 | 0 | [] |

复跑核对：sessions-r2c 第二次导入 accepted=0、duplicate=28，去重语义正常；replay 得 invocation.started 14 条、invocation.finished 14 条（succeeded 13、failed 1，对应该文件 1 条 isError=true 的 bash 结果），无负 duration。host_version 全部为 18.19.0（来自 model_change 的 runtime.version）。

逐条核对：每个文件的 records_skipped 都等于 title(1)+model_change(1)+thinking_level_change(1)+custom+custom_message+user 之和（例如 r2c：1+1+1+17+0+1=21，r2：1+1+1+143+2+1=149）；events_emitted 等于 toolCall 数乘 2 再加 skill:// 读取产出的 skill.loaded（r2 有 3 条，其余 4 个文件为 0）。没有无法归因的跳过。

### 结论：跳过的行分别是什么、该不该跳

- 门禁冒烟文件（12 行、skipped=8）与 16 个实测文件的所有跳过行都落在这几类：title、model_change、thinking_level_change、custom、custom_message、user 消息。逐类判断：
  - title：只有会话标题字段（v/title/updatedAt/pad），无执行事实 → 该跳。
  - model_change、thinking_level_change：宿主配置事实，R1.0 事件模型没有对应事件类型；其 runtime.version 已被用来填 host_version → 该跳。
  - custom：tool_execution_start 与 toolCall 记录重复；session_exit 无对应事件类型；date-cwd-reminder、system-prompt-digest 属提示内部 → 该跳。
  - custom_message：宿主展示层消息，无执行事实 → 该跳。
  - user 消息：metadata 观察级别不采提示正文 → 该跳。
- 16 个文件 928 对 toolCall/toolResult 全部成对映射，无解析失败、无 rejected、无 conflict、无 dropped；5 个文件真实导入的回执与逐行归因完全一致。结论：适配器对 18.19.0 的既有映射（toolCall/toolResult/skill 读取）解析正确，没找到解析错或该采而跳的记录。要改的是把 18.19.0 实测形状同步进注释、文档、规格并补回归夹具；适配器逻辑没找到要改的。

## 逐项改动清单

行号为编辑前基线（分支 feat/v2.2.0-rc.1-omp-session-parse，基线 main 5b95849）的行号。

1. sbtd-runtime/omp_adapter.py 模块 docstring 映射清单（:12-20）：补 18.19.0 实测形状——title 无 id、thinking_level_change、custom_message、custom 各 customType、session 头 version 3 且无 runtime、toolCall 带 intent 键、thinking 块带 thinkingSignature、toolResult 的 message 带 content/details/timestamp；写明这些类型跳过并计数是有意设计。只改注释，不改逻辑。
2. sbtd-runtime/docs/host-adapters.md omp 节（:25-34 映射清单，:30「其余记录类型与坏尾行跳过并计数」）：补一小段列出 18.19.0 其他记录类型（title、model_change、thinking_level_change、custom 四种 customType、custom_message、user 消息），逐项写明跳过是有意的及原因，注明统计来源为 2026-11-13 实测。
3. sbtd-runtime/spec/r1.2b-host-adapter-scenarios.md OMP 节（:46 起，未识别类型与坏行跳过计数场景在 :91 附近）：加一条场景——18.19.0 新记录类型（title/thinking_level_change/custom/custom_message/user 消息）跳过并计数，且不影响 toolCall/toolResult 映射与去重。
4. sbtd-runtime/tests/test_omp_adapter.py：加 18.19.0 形状的脱敏最小夹具与测试（见「要加的测试」），不放真实会话内容。
5. 适配器解析逻辑：没找到要改的。跳过计数是否细分见「需要 640 拍板的问题」，默认不动回执形状。

## 要加的测试

全部用脱敏最小夹具复现 18.19.0 形状，不含真实会话内容：

1. 文件首行 title 记录（无 id、v=1）：跳过并计数，后续 session 头仍正确设置 session_id。
2. thinking_level_change、custom_message、四种 customType 的 custom、user 消息：各自跳过并计数，事件产出不受影响。
3. session 头 version 3 且无 runtime 键：host_version 由后续 model_change 的 runtime.version 提供，事件 host.host_version 正确。
4. assistant content 含 thinking 块（带 thinkingSignature）与 text 块：不计跳过、不产事件，同一消息内 toolCall 正常映射。
5. toolCall 带 intent 键且 id 不含「|」：正常映射 invocation.started；toolResult 的 message 带 content/details/timestamp 键：正常映射 invocation.finished，duration 正确。
6. 新夹具端到端：第一次导入 accepted 等于事件数，第二次全部 duplicate（沿用既有重复导入断言方式）。

## Book Gate Plan

| 方法 | 触发与阶段 | 状态与证据 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求确认前 | not-required；未完整 grill，任务边界与事实均明确，无领域歧义 |
| book-ddia-data-design | schema、迁移或跨进程机制设计前 | proceed / 轻量；不动事件与回执形状、无存储迁移；若 640 选择细分跳过计数则升级为 required（回执形状变更，host_adapter.py:143-176 与 codex 适配器需对齐） |
| book-legacy-change-safety | 既有行为修改前 | not-required；适配器逻辑不改。若实施轮结论反转需要动解析逻辑，先跑 tests/test_omp_adapter.py 建立保留行为基线再改 |
| book-refactoring-pass | 既有生产文件编辑前 | proceed；只改注释、文档、规格、测试，不夹带重构 |
| gherkin-bdd | 用户可见行为变化，before-dev/check | traceable；沿用中文 Markdown spec，新增场景与新夹具一一对应，无新 .feature |
| project-validation | 改动后 | 已执行聚焦 unittest 与索引验证，证据见「验证证据」；全量以 CI 为准 |
| book-release-readiness | 运行时/部署行为变化，验证后 | not-required；适配器逻辑不改、不部署不发布。若动解析逻辑则 required |
| 独立 review 与 CI | PR 检查 | pending；本任务不使用子代理 |
| ponytail-review | 修改后自检 | 已自检：仅注释、文档、规格、测试与双语 CHANGELOG 变动，无新增抽象与依赖；不代替独立 review |

## 验收标准

- 注释、文档、规格与 18.19.0 实测形状一致，各跳过类型写明是有意设计及原因。
- 「要加的测试」6 项全部落地并通过；tests/test_omp_adapter.py 既有测试全部保持通过。
- 改动后用至少 3 个真实 18.19.0 会话文件复跑导入，回执与本节基线数字逐字段一致（适配器逻辑不改，预期完全一致；若 640 拍板细分跳过计数，按拍板结果更新预期）。
- 仓库内不出现真实会话正文与本机绝对路径；索引验证通过。

## 真跑计划

- 实施轮后用 sessions-r1 至 sessions-r3h 中至少 3 个真实 18.19.0 会话文件复跑导入（本轮已跑 r1、r2、r2c、r3d、r3h 五个并留基线数字）：临时目录独立 runtime home、按既有 facade 做法开启 observation、lease 守卫走真实 omp CLI；对比回执逐字段。
- 聚焦验证命令：`python3 -B -m unittest tests.test_omp_adapter`（本环境无 pytest，按项目既有方式用 unittest 运行同一文件，不伪造 pytest 结果）；TaskStore 只读索引预览与 ai/tasks/index.md 逐字节比对。
- 全量套件与发布验证以 CI 为准；本任务不 commit、不 push、不开 PR。

## 验证证据

2026-11-13 实施轮验证，每条命令前台单条执行：

- 基线（加新测试前）：sbtd-runtime 下 `python3 -B -m unittest tests.test_omp_adapter` → 24 tests，8.690s，OK。
- 改动后聚焦测试：
  - sbtd-runtime 下 `python3 -B -m unittest tests.test_omp_adapter` → 30 tests（既有 24 + 新增 6），2.081s，OK。
  - sbtd-runtime 下 `python3 -B -m unittest tests.test_golden_contracts` → 66 tests，0.331s，OK。
  - 仓库根 `python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts` → 99 tests，33.011s，OK。
- 真实复跑（sessions-r1、sessions-r2c、sessions-r3h 三个真实 18.19.0 会话文件；每文件在仓库外临时目录用独立 runtime home，按既有 facade 做法写 config.json 开 observation，CLI 走真实 lease 守卫，omp 18.19.0，exit 全为 0，host_version 均 18.19.0）：

  | 文件 | records_read | records_skipped | events_emitted | accepted | duplicate | conflict | rejected | dropped | 对比「真实导入回执」基线 |
  |---|---|---|---|---|---|---|---|---|---|
  | sessions-r1 | 96 | 42 | 70 | 70 | 0 | 0 | 0 | [] | 逐字段一致 |
  | sessions-r2c | 46 | 21 | 28 | 28 | 0 | 0 | 0 | [] | 逐字段一致 |
  | sessions-r3h | 54 | 25 | 36 | 36 | 0 | 0 | 0 | [] | 逐字段一致 |

  sessions-r2c 第二次导入：accepted=0、duplicate=28，其余字段不变，去重语义与基线一致。
- 索引验证：TaskStore 只读重建索引候选，与 ai/tasks/index.md 逐字节一致（INDEX_PREVIEW_SAME True，rows=90）。

无失败项，无归因记录。

## 需要 640 拍板的问题

1. records_skipped 是否细分原因或类型。选项甲：在 ParseOutcome/IngestReceipt 增加按类型或原因的跳过计数（回执形状变更，host_adapter.py:143-176 与 codex 适配器需对齐，契约文档同步）；选项乙：保持现状只记总数，文档写明各类型跳过是有意的。推荐乙：回执是 R1.2b 契约的一部分，改形状牵动 codex 侧与既有测试，收益主要是诊断便利；本轮逐行归因证明现有总数足以核对，没有因不细分而漏掉的解析错误。
2. session 头 version 是否纳入校验（例如 version 非 3 时拒绝导入或单独计数）。推荐不校验、保持只取 id：18.11.1 到 18.19.0 的 version 都是 3 且适配器只用 id；加校验会把未来新版本的整体导入变成拒绝，与「未识别类型跳过并计数、不拒绝整体导入」的宽松策略不一致。

## 模型记录

- 主 agent 用 k3:max，密钥从环境变量 KIMI_API_KEY 读取。
- 每轮结束后把该轮真实数字补进下表；只写实际发生的数字。

| 轮次 | 用途 | 模型 | 回复次数 | 工具调用次数 | 工具报错次数 | 结果 |
|---|---|---|---|---|---|---|
| r1 | 写任务文件与真实会话调查 | kimi-code/k3:max | 30 | 39 | 1 | de136e5 |
| r2 | 实施：适配器注释、文档、规格、6 个回归测试、两份 CHANGELOG、验证证据 | kimi-code/k3:max | 56 | 62 | 4 | 077e22f |

## 会话记录

- r1：会话 id 01a1d348-220b-7070-aa4a-bda0dd06a0f1，开始时间 2026-11-13 13:01。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-13T13:38:29.996319+08:00 | planned | in-progress | 实施轮开始：执行逐项改动清单与新增测试 | 开始实施：按逐项改动清单 1-4 与要加的测试 6 项；需要 640 拍板的两个问题先按推荐（乙：不细分跳过计数；不校验 session version）实施，群内投票结果若不同再另起一轮调整 |
| 2026-11-13T15:03:27.667559+08:00 | in-progress | checking | 实施完成：注释、文档、规格、测试与双语 CHANGELOG 已改，聚焦验证与真实复跑通过，待复核 | test_omp_adapter 30 tests OK（既有 24 + 新增 6，基线 24 tests OK）；test_golden_contracts 66 tests OK；tests.test_sbtd_task_state + tests.test_workflow_contracts 99 tests OK；sessions-r1/r2c/r3h 复跑回执与基线逐字段一致，r2c 二次导入 accepted=0、duplicate=28；INDEX_PREVIEW_SAME True rows=90；本任务未 commit/push |
