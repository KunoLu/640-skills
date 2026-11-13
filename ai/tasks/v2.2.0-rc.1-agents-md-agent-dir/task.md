---
schema_version: 1
id: v2.2.0-rc.1-agents-md-agent-dir
workflow_mode: strict
mode_source: user
mode_note: 本轮任务指令明确全程 strict；640 于 2026-11-12 在 640-skills 群确认做 v2.2.0-rc.1，本任务为其中第
  2 项（AGENTS.md 遵守 PI_CODING_AGENT_DIR）
status: planned
branch: feat/v2.2.0-rc.1-agents-md-dir
created_at: '2026-11-13T16:22:58.477903+08:00'
updated_at: '2026-11-13T16:22:58.477903+08:00'
completed_at: null
---
# v2.2.0-rc.1 AGENTS.md 遵守 PI_CODING_AGENT_DIR

## 目标与范围

640 于 2026-11-12 在 640-skills 群确认做 v2.2.0-rc.1，本任务是其中第 2 项：读取或写入 omp 的 AGENTS.md 时，遵守 PI_CODING_AGENT_DIR 环境变量——设了就用它指向的目录，没设就回退默认 ~/.omp/agent。本任务分轮执行。第一轮（本轮）只写任务文件并登记索引，完成现状调查与 omp 实测：仓库里哪些地方拼 omp 的 AGENTS.md 路径、omp 18.19.0 对该变量的实际语义、现有测试与文档覆盖。不改代码、文档、测试、CHANGELOG。后续实施轮按「逐项改动清单」执行，不 commit、不 push、不开 PR、不用子代理，除非 640 另行授权。

未完整调用 grill-with-docs：任务内容、宿主版本与交付边界均已明确，无领域歧义。

## 背景事实

- 2026-11-12 Lord 在 640-skills 群提出 v2.2.0 三项，640 确认做 v2.2.0-rc.1：第 1 项 omp 会话解析（v2.2.0-rc.1-omp-session-parse，已由 #220 于 2026-11-13 合入 main 90667a6）；第 2 项 AGENTS.md 遵守 PI_CODING_AGENT_DIR（本任务）；graft 项已由 #219 合入。注：分钟不可考。
- 2026-11-13 本机 omp 为 18.19.0（bun 全局安装 @oh-my-pi/pi-coding-agent@18.19.0，`omp --version` 输出 omp/18.19.0）。本轮以该版本打包源码与只读实测确认变量语义；实测全部在临时目录进行，HOME 也指向临时目录，不发模型请求，不碰真实 home。
- 本任务分支 feat/v2.2.0-rc.1-agents-md-dir，基于 main 90667a6。

## strict mode 落实方式

- 任务文件在开工前经仓库 TaskStore 库 API（sbtd-workflow-onboard/scripts/sbtd_task_state.py 的 TaskStore.create）创建并落盘；阶段转换用 `transition()` 记录真实状态事件，不手改状态时间。
- 验证证据（命令、结果、失败归因）写入本文件；Book Gate Plan 已列。
- 状态停在 planned，实施轮开始后再按真实进度转换。

## 实测发现（2026-11-13 本轮调查）

### omp 18.19.0 对 PI_CODING_AGENT_DIR 的实际语义

打包源码（dist/cli.js）：

- 设置对象的 agentDir：变量非空时 `path.resolve(变量值)`，否则 `configRoot/agent`；configRoot 为 系统 home 下 PI_CONFIG_DIR 或 .omp。命名 profile 生效（OMP_PROFILE 优先于 PI_PROFILE）时用 profiles/<name>/agent，且忽略 PI_CODING_AGENT_DIR。变量值与推导出的默认 agent 目录完全相等时按未设处理。空字符串是假值，回退默认。相对路径按进程 cwd 解析；`~` 不做展开（path.resolve 语义，`~/x` 会变成 cwd 下的 `~/x`）。
- 用户级 AGENTS.md 由「Load AGENTS.md from .omp/ directories」加载器从 agentDir/AGENTS.md 读取；变量同时决定会话存储目录（帮助文本：PI_CODING_AGENT_DIR - Session storage directory，默认 ~/.omp/agent）。

只读实测（临时目录，不设真实 home，不发模型请求）：

- 变量指向放有坏 YAML config.yml 的临时 agent 目录，RPC 模式（--mode rpc --no-ui --no-extensions --no-rules）执行 get_state，报错「Settings config is invalid: <临时目录>/agent/config.yml」——配置确实从变量指向的目录读取。
- 变量为空字符串或不设：同一命令正常返回 ready/negotiate/get_state，临时 home 下无 .omp——回退默认。
- 变量为相对路径（cwd 为其上级目录）：报同样的配置错误，报错路径为 cwd 拼接后的绝对路径——相对路径按 cwd 解析。
- 变量为 `~` 开头字面值：不报错（该路径不存在，无配置可读）——`~` 未被展开。
- `omp --version` 不加载配置：四种取值下都正常输出版本号。
- 仓库既有佐证：sbtd-workflow-onboard/scripts/sbtd_upgrade_hosts.py:2180-2207 的 OMP 探针固定以 PI_CODING_AGENT_DIR 指向临时夹具目录驱动真实 omp RPC，omp 从该目录加载 mcp 配置。

### 仓库涉及位置（AGENTS.md 读/写路径，逐处）

1. sbtd-workflow-onboard/scripts/onboard.py:531-537 `detect_omp_root()`：只看 user_home()/.omp 是否存在（resolve 后须为目录），不看 PI_CODING_AGENT_DIR、PI_CONFIG_DIR、profile。读（存在性判断）。
2. sbtd-workflow-onboard/scripts/onboard.py:540-541 `omp_global_agents_path(omp_root)`：返回 omp_root/agent/AGENTS.md。
3. sbtd-workflow-onboard/scripts/onboard.py:2188-2202 check 报告：paths.ompRoot 与 paths.ompGlobalAgents 由上面两函数产出。读。
4. sbtd-workflow-onboard/scripts/onboard.py:6202-6213 `build_operations`：omp_root 存在时把「omp global AGENTS.md」操作目标定为 omp_global_agents_path(omp_root)，与 Codex 目标相同文件时去重。写（备份后覆盖全局模板）。
5. sbtd-workflow-onboard/scripts/sbtd_graft_deployment.py:497-516 `_omp_agents_template_target`：用 detect_omp_root 与 user_home()/.omp 推导 OMP init 部署隐含创建的 AGENTS.md 目标；:628 附近同样用 detect_omp_root。写计划。
6. sbtd-workflow-onboard/scripts/sbtd_migration_plan.py:2348-2356：omp-global routing 审批校验，omp_home = user_home()/.omp，目标须等于 omp_global_agents_path(omp_home)；:4616-4622：routing_targets 组装，omp 根存在为目录时加入 omp-home 目标。写计划的归属校验。
7. sbtd-workflow-onboard/scripts/sbtd_omp_sources.py:56-90 `active_omp_paths`：仓库里唯一已按 PI_CODING_AGENT_DIR / PI_CONFIG_DIR / profile 解析 agent 目录的 resolver（expanduser 后 resolve，空串回退默认，命名 profile 时忽略变量），只服务 mcp/config 类目标，AGENTS.md 没用它。
8. sbtd-workflow-onboard/scripts/sbtd_cleanup_targets.py:455-470、482：mcp.json 探针清单已含显式 PI_CODING_AGENT_DIR 项与 active_omp_paths 解析项，以及 profiles 下各 agent/mcp.json；不涉及 AGENTS.md，不用改。
9. sbtd-workflow-onboard/scripts/sbtd_language_tooling.py:151-152、215-219、281、626：config.yml 与 lsp.yml 固定拼 Path.home()/.omp/agent，不看变量。超出本项「AGENTS.md」范围，记为观察，见「需要决定的问题」。
10. sbtd-runtime/：没有 AGENTS.md 或 omp agent 目录相关代码（适配器只读显式给出的会话文件路径）。不用改。
11. onboard.py:2677（GITIGNORE_MUST_TRACK_PROBES 含 AGENTS.md）、:5815 project_scaffold_conflict、sbtd_trellis_uninstall.py、sbtd_cleanup_legacy.py:304、sbtd_codex_wiring.py:721、sbtd_migration.py:473：均为项目根 AGENTS.md 或 Codex 目标，与 omp agent 目录无关，不用改。

### 测试与文档现状

测试（无一覆盖「变量设置时 omp 全局 AGENTS.md 目标」）：

- tests/test_sbtd_codex_deployment.py:47、101：mock detect_omp_root 控制 omp AGENTS.md 写不写，无变量用例。
- tests/test_sbtd_omp_deployment.py:593、tests/test_sbtd_followup_batch.py:247、tests/test_sbtd_migration_cleanup_drift.py:180、tests/test_p1_15_host_mode_smoke.py:1391、tests/test_sbtd_omp_wiring.py:455、494、tests/test_sbtd_omp_reconciliation.py:92：PI_CODING_AGENT_DIR 只用于 mcp 路径相关断言，无 AGENTS.md 用例。

文档写死 ~/.omp/agent（AGENTS.md 相关，要改）：

- README.md:71、README.zh.md:71：init/reset 写入范围说明。
- sbtd-workflow-onboard/SKILL.md:69：同一段落。
- sbtd-workflow-onboard/REFERENCE.md:5、77、780：模板目标说明与 Paths 表。
- docs/assets/onboard-skill-init.md:93、docs/assets/onboard-skill-reset.md:94：写入范围表。

文档写死但不在本项范围（mcp.json/config.yml/lsp.yml，记为观察）：REFERENCE.md:357、654、706、764，SKILL.md:216、236。docs/archive/ 下为历史存档，不改。

## 逐项改动清单

行号为编辑前基线（分支 feat/v2.2.0-rc.1-agents-md-dir，基线 main 90667a6）的行号；实施轮以当时基线复核。

1. onboard.py:531-541：调整 omp agent 目录解析——PI_CODING_AGENT_DIR 非空时用它指向的目录，未设或空串回退 user_home()/.omp/agent；detect_omp_root 语义、omp_global_agents_path 与之一致。优先复用 active_omp_paths 的解析，不造第二套规则（profile 与 PI_CONFIG_DIR 是否一并跟随见「需要决定的问题」）。
2. onboard.py:2188-2202：check 报告 ompRoot/ompGlobalAgents 走同一解析。
3. onboard.py:6202-6213：build_operations 的「omp global AGENTS.md」目标走同一解析；保留与 Codex 目标同文件去重、保留「未设变量且 ~/.omp 不存在则跳过不创建」的既有行为。
4. sbtd_graft_deployment.py:497-516、628 附近：_omp_agents_template_target 与部署计划里的 omp 根判断跟随同一解析。
5. sbtd_migration_plan.py:2348-2356、4616-4622：omp-global routing 目标校验与组装跟随同一解析。
6. tests/：新增变量用例（见「要加的测试」），既有断言不破坏。
7. 文档：README.md:71、README.zh.md:71、sbtd-workflow-onboard/SKILL.md:69、sbtd-workflow-onboard/REFERENCE.md:5、77、780、docs/assets/onboard-skill-init.md:93、docs/assets/onboard-skill-reset.md:94 补变量语义（设了用变量目录，没设回退默认，空串回退默认）。
8. CHANGELOG.md 与 CHANGELOG.zh.md：各加一条 v2.2.0-rc.1 条目。
9. sbtd_language_tooling.py 的 config.yml/lsp.yml 路径：不在本项范围，见「需要决定的问题」。

## 要加的测试

全部只用临时目录与临时 HOME，不碰真实 home：

1. 设 PI_CODING_AGENT_DIR 指向临时目录：build_operations 的 omp global AGENTS.md 目标为该目录下 AGENTS.md；临时 home 下 .omp 是否存在都不改变该目标。
2. 不设变量且临时 home 下 .omp 存在：目标为 .omp/agent/AGENTS.md（既有行为保留）。
3. 变量为空字符串：与第 2 项相同，回退默认。
4. 变量为 `~` 开头路径：按「需要决定的问题」投票结论的语义断言（展开或不展开），并断言 omp 实际读取位置与写入目标一致。
5. check 报告 ompGlobalAgents 与所选解析一致。
6. 迁移 plan omp-global routing 校验：变量设置时新目标被接受、旧默认路径被拒绝。
7. 既有「未设变量、~/.omp 不存在则跳过且不创建」断言保持通过。

## Book Gate Plan

| 方法 | 触发与阶段 | 状态与证据 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求确认前 | not-required；未完整 grill，任务边界与事实均明确，无领域歧义 |
| book-ddia-data-design | schema、迁移或跨进程机制设计前 | not-required；不动任何存储形状、回执、事件或迁移格式，只改路径解析 |
| book-legacy-change-safety | 既有行为修改前 | required；实施轮先跑 tests/test_sbtd_codex_deployment.py 与迁移计划相关测试建立保留行为基线，再改路径解析 |
| book-refactoring-pass | 既有生产文件编辑前 | proceed；复用 active_omp_paths 既有 resolver，不新增平行抽象，不夹带无关重构 |
| gherkin-bdd | 用户可见行为变化，before-dev/check | traceable；本仓库为模板/源码仓库，没有 .feature 文件惯例，行为规格落在 SKILL.md/REFERENCE.md/docs/assets 说明与新增测试，二者一一对应 |
| project-validation | 改动后 | 聚焦 unittest 与索引验证，证据写进本文件；全量以 CI 为准 |
| book-release-readiness | 运行时/部署行为变化，验证后 | required；onboard 安装与迁移计划行为变化，验证序列完成后执行 |
| 独立 review 与 CI | PR 检查 | pending；触及全局配置写入与迁移校验，需独立 review（原生只读或人工）；本任务不使用子代理 |
| ponytail-review | 修改后自检 | 实施轮自检；不代替独立 review |

## 验收标准

- 设了 PI_CODING_AGENT_DIR：omp 全局 AGENTS.md 的读（check 报告）与写（init/reset、迁移计划、graft 部署计划）都指向变量目录；没设或空串：回退默认 ~/.omp/agent，既有行为不变。
- 写入目标与 omp 18.19.0 实际读取位置（agentDir/AGENTS.md）一致。
- 「要加的测试」全部落地并通过；既有测试全部保持通过。
- 文档与 CHANGELOG 双语条目与实际语义一致；仓库内不出现真实 home 绝对路径与密钥内容；索引验证通过。

## 真跑计划

- 实施轮后在临时目录真跑：临时 HOME、PI_CODING_AGENT_DIR 指向临时 agent 目录，跑 onboard check 的 JSON 输出确认 ompGlobalAgents 指向变量目录；不设变量与空串各跑一遍对照回退。
- 用真实 omp 18.19.0 佐证读取侧一致：复用本轮探针方式（--mode rpc --no-ui --no-extensions --no-rules，临时 HOME，不发模型请求），坏 config.yml 放变量目录时报错路径指向该目录。
- 聚焦验证命令：仓库根 `python3 -B -m unittest tests.test_sbtd_codex_deployment` 及迁移计划、omp 部署相关测试文件（实施轮按 diff 定清单）；TaskStore 只读索引预览与 ai/tasks/index.md 逐字节比对。
- 全量套件与发布验证以 CI 为准；本任务不 commit、不 push、不开 PR。

## 需要决定的问题

全自动模式下交群里投票；每个问题给选项、推荐和理由。

1. 命名 profile 生效时（OMP_PROFILE/PI_PROFILE 非 default），omp 忽略 PI_CODING_AGENT_DIR、改用 profiles/<name>/agent。onboard 写 omp 全局 AGENTS.md 是否跟随 active profile 目录？选项甲：跟随，复用 active_omp_paths 同一解析（与 mcp.json 写入位置一致，单一事实源）；选项乙：只看变量与默认根，不管 profile。推荐甲：omp 实际读 profile 目录下的 AGENTS.md，写默认根会写错地方。
2. 变量指向的目录不存在时，写不写？选项甲：写入并按需创建父目录（omp 运行时本就会自建该目录，变量是显式指向）；选项乙：与「~/.omp 不存在则跳过」对称，跳过并在报告注明。推荐甲：跳过会让 omp 在变量目录下读不到规则，与第 2 项目标冲突。
3. 变量值为 `~` 开头路径：omp 用 path.resolve 不展开 `~`（相对 cwd），仓库 active_omp_paths 用 expanduser 展开，两者不一致。AGENTS.md 目标解析跟随哪边？选项甲：跟随 omp 实际行为（写的是 omp 要读的文件，位置必须与 omp 一致）；选项乙：跟随仓库既有 resolver（与 mcp 写入解析一致）。推荐甲，理由同第 1 题；若选甲，mcp 侧既有 expanduser 行为记为单独观察，不在本任务改。
4. PI_CONFIG_DIR（改变 omp 默认根）是否一并支持，以及 sbtd_language_tooling.py 的 config.yml/lsp.yml 是否纳入本任务？选项甲：PI_CONFIG_DIR 随第 1 题同一 resolver 一并支持，config.yml/lsp.yml 不纳入（本项只点 AGENTS.md，另议）；选项乙：都只处理 PI_CODING_AGENT_DIR。推荐甲的前半、乙的后半，即甲。

## 模型记录

- 主 agent 用 k3:max，密钥从环境变量 KIMI_API_KEY 读取。
- 每轮结束后把该轮真实数字补进下表；只写实际发生的数字。

| 轮次 | 用途 | 模型 | 回复次数 | 工具调用次数 | 工具报错次数 | 结果 |
|---|---|---|---|---|---|---|

## 会话记录

每轮结束后补记该轮会话 id 与起止时间。
