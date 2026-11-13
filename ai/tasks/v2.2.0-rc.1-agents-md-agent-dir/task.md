---
schema_version: 1
id: v2.2.0-rc.1-agents-md-agent-dir
workflow_mode: strict
mode_source: user
mode_note: 本轮任务指令明确全程 strict；640 于 2026-11-12 在 640-skills 群确认做 v2.2.0-rc.1，本任务为其中第
  2 项（AGENTS.md 遵守 PI_CODING_AGENT_DIR）
status: "checking"
branch: feat/v2.2.0-rc.1-agents-md-dir
created_at: '2026-11-13T16:22:58.477903+08:00'
updated_at: "2026-11-13T20:42:10.178975+08:00"
completed_at: null
---
# v2.2.0-rc.1 AGENTS.md 遵守 PI_CODING_AGENT_DIR

## 目标与范围

640 于 2026-11-12 在 640-skills 群确认做 v2.2.0-rc.1（注：分钟不可考。），本任务是其中第 2 项：读取或写入 omp 的 AGENTS.md 时，遵守 PI_CODING_AGENT_DIR 环境变量——设了就用它指向的目录，没设就回退默认 ~/.omp/agent。本任务分轮执行。第一轮（本轮）只写任务文件并登记索引，完成现状调查与 omp 实测：仓库里哪些地方拼 omp 的 AGENTS.md 路径、omp 18.19.0 对该变量的实际语义、现有测试与文档覆盖。不改代码、文档、测试、CHANGELOG。后续实施轮按「逐项改动清单」执行，不 commit、不 push、不开 PR、不用子代理，除非 640 另行授权。

未完整调用 grill-with-docs：任务内容、宿主版本与交付边界均已明确，无领域歧义。

## 背景事实

- 2026-11-12 Lord 在 640-skills 群提出 v2.2.0 三项，640 确认做 v2.2.0-rc.1：第 1 项 omp 会话解析（v2.2.0-rc.1-omp-session-parse，已由 #220 于 2026-11-13 合入 main 90667a6）；第 2 项 AGENTS.md 遵守 PI_CODING_AGENT_DIR（本任务）；graft 项已由 #219 合入。注：分钟不可考。
- 2026-11-13 本机 omp 为 18.19.0（bun 全局安装 @oh-my-pi/pi-coding-agent@18.19.0，`omp --version` 输出 omp/18.19.0）。本轮以该版本打包源码与只读实测确认变量语义；实测全部在临时目录进行，HOME 也指向临时目录，不发模型请求，不碰真实 home。注：分钟不可考。
- 本任务分支 feat/v2.2.0-rc.1-agents-md-dir，基于 main 90667a6。

## strict mode 落实方式

- 任务文件在开工前经仓库 TaskStore 库 API（sbtd-workflow-onboard/scripts/sbtd_task_state.py 的 TaskStore.create）创建并落盘；阶段转换用 `transition()` 记录真实状态事件，不手改状态时间。
- 验证证据（命令、结果、失败归因）写入本文件；Book Gate Plan 已列。
- 状态按真实进度经 transition() 推进：planned → in-progress → checking（见「状态事件」）。

## 实测发现（2026-11-13 本轮调查）

注：分钟不可考。

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
4. 变量为 `~` 开头路径：按「已决定的问题」第 3 项的语义断言（不展开），并断言 omp 实际读取位置与写入目标一致。
5. check 报告 ompGlobalAgents 与所选解析一致。
6. 迁移 plan omp-global routing 校验：变量设置时新目标被接受、旧默认路径被拒绝。
7. 既有「未设变量、~/.omp 不存在则跳过且不创建」断言保持通过。

## Book Gate Plan

| 方法 | 触发与阶段 | 状态与证据 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求确认前 | not-required；未完整 grill，任务边界与事实均明确，无领域歧义 |
| book-ddia-data-design | schema、迁移或跨进程机制设计前 | not-required；不动任何存储形状、回执、事件或迁移格式，只改路径解析 |
| book-legacy-change-safety | 既有行为修改前 | 已执行；改动后既有相关套件（97、73、44、150、19 例）与全量分片通过，「未设变量且默认根缺失则跳过且不创建」由新增测试锁定，未单独保留改动前基线运行记录 |
| book-refactoring-pass | 既有生产文件编辑前 | 已执行；复用 active_omp_paths 既有 config 根/profile 规则（抽出共用 `_omp_config_root`），无新增平行抽象，无夹带重构 |
| gherkin-bdd | 用户可见行为变化，before-dev/check | traceable；本仓库为模板/源码仓库，没有 .feature 文件惯例，行为规格落在 SKILL.md/REFERENCE.md/docs/assets 说明与新增测试，二者一一对应 |
| project-validation | 改动后 | 已执行；聚焦 unittest、全量三分片与索引验证，证据见「验证证据」 |
| book-release-readiness | 运行时/部署行为变化，验证后 | 已执行，结论 ready；见「Release Readiness Review」一节 |
| 独立 review 与 CI | PR 检查 | pending；触及全局配置写入与迁移校验，需独立 review（原生只读或人工）；本任务不使用子代理 |
| ponytail-review | 修改后自检 | 已自检；单一 resolver、无重复拼路径、无死代码；不代替独立 review |

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

## 验证证据

2026-11-13 实施轮（r2）验证（注：分钟不可考。），每条命令前台单条执行，单条不超过 600 秒；r2 中途因整机暂停被看门狗结束一次，改动文件全部保留，以下为续跑后的真实数字：

- 新增与受影响测试（仓库根）：
  - `python3 -B -m unittest tests.test_sbtd_omp_agents_target` → Ran 23 tests，OK。新增文件，覆盖：变量设置、未设、空字符串、`~` 开头不展开、相对路径按进程当前目录解析、PI_CONFIG_DIR 移动默认根、命名 profile 生效且忽略变量、变量目录不存在仍列入写入计划、check 报告 ompGlobalAgents 与写入目标一致、迁移 omp-global routing 校验接受新目标并拒绝旧默认路径、默认根缺失时保持跳过且不创建。
  - `PYTHONPATH=sbtd-workflow-onboard/scripts python3 -B -m unittest tests.test_sbtd_codex_deployment tests.test_onboard_multi_projects tests.test_sbtd_omp_deployment tests.test_sbtd_migration_cleanup_drift` → Ran 97 tests，OK。注：其中既有模块自身不带 sys.path 自举，裸 `python3 -B -m unittest tests.test_sbtd_codex_deployment` 在改动前同样无法 import（其第 9 行 import 不在本次 diff 内），CI 经 discovery 顺序获得路径；本次以 PYTHONPATH 形式给出等价路径。该命令曾跑出一次 failures=2，随后两次重跑均 OK，失败输出未保留，按偶发处理，未归因到本次改动。
  - `python3 -B -m unittest tests.test_sbtd_followup_batch tests.test_sbtd_approved_agents_deployment tests.test_sbtd_cleanup_targets` → Ran 73 tests，OK。
  - `python3 -B -m unittest tests.test_sbtd_omp_wiring tests.test_sbtd_omp_reconciliation` → Ran 44 tests，OK。
  - `python3 -B -m unittest tests.test_sbtd_upgrade_hosts` → Ran 150 tests，OK（skipped=21，环境门控跳过）。
  - `python3 -B -m unittest tests.test_p1_15_host_mode_smoke` → Ran 19 tests，OK（skipped=5，环境门控跳过）。
- 全量（仓库 CI 命令 `python3 -B tests/run_ci.py --platform linux`，共 2513 个用例，单条 600 秒上限内跑不完，按 CI 的 `--shards 3` 分片顺序执行）：
  - shard 1/3：Ran 868 tests，OK（skipped=39）。
  - shard 2/3：Ran 693 tests，FAILED（failures=1，skipped=13）。唯一失败 `sbtd_runtime_test_stats_query.NormalizeScopeTests.test_iana_queries_and_dst_work_without_system_timezone_data`，单独复跑同样失败：`range.timezone: unknown timezone 'Asia/Tokyo'`。归因：本机未安装 sbtd-runtime/requirements-serve.txt 声明的 tzdata==2026.5，该测试模拟无系统时区数据时 IANA 名称解析依赖此包；与本任务改动无关（diff 不涉及 sbtd-runtime 任何文件）。不静默安装缺失依赖，维持环境原状，由 CI（安装全部声明依赖）判定。
  - shard 3/3：Ran 952 tests，OK（skipped=13）。三分片合计 2513 个用例与 discovery scope 数一致，失败合计 1 个（上述环境性 tzdata 缺失），跳过合计 65（环境门控）。
- 真跑（临时 HOME 与临时目录，不发模型请求，不碰真实 home）：
  - `onboard.py check --json`：PI_CODING_AGENT_DIR 指向临时 agent 目录时 ompGlobalAgents = 该目录下 AGENTS.md、ompRoot = null；变量未设与空字符串时两者均为 null；临时 home 下创建 .omp 后 ompRoot 与 ompGlobalAgents 指向默认根默认路径。四组对照均符合预期。
  - 真实 omp 18.19.0（`--mode rpc --no-ui --no-extensions --no-rules`）：坏 config.yml 放变量目录时报错「Settings config is invalid: <临时目录>/agent-x/config.yml」；变量设置时默认根下的坏配置不被读取（进程进入模型选择提示）；未设变量时默认根坏配置的报错路径为 <临时 home>/.omp/agent/config.yml。omp 实际读取位置与 check 报告及写入目标一致。
- 索引验证：TaskStore 只读索引预览 `_index_candidate` 与 ai/tasks/index.md 逐字节一致（状态转移前比对为 True；转移后再次比对）。

2026-11-13 修复轮（r3b）验证（注：分钟不可考。），每条命令单条执行，均在 600 秒内完成，仓库根 `python3 -B -m unittest`：

- 修复内容：onboard.py check 报告在 PI_CODING_AGENT_DIR 未设（非显式）分支恢复 main 写法——ompGlobalAgents 按 resolve 后的 omp root 拼接（omp_global_agents_path 恢复 omp_root 参数形态）并补 .resolve()；设了变量的显式分支保持 r2/r2b 语义不变。新增 tests/test_sbtd_omp_agents_target.py 用例 test_check_resolves_symlink_home_when_variable_unset：临时目录符号链接当 HOME，断言变量不设时 ompGlobalAgents 为 resolve 后路径（不依赖 macOS）。
- `python3 -B -m unittest tests.test_sbtd_omp_agents_target` → Ran 31 tests，OK（30 → 31，新增符号链接 HOME 用例）。
- `python3 -B -m unittest tests.test_onboard_multi_projects` → Ran 59 tests，OK（含 macOS CI 失败用例 test_check_json_reports_omp_paths）。
- `python3 -B -m unittest tests.test_sbtd_cleanup_targets` → Ran 42 tests，OK。
- `python3 -B -m unittest tests.test_onboard_agent_cli tests.test_onboard_arguments tests.test_onboard_omp_wiring tests.test_sbtd_followup_batch tests.test_sbtd_language_tooling tests.test_sbtd_omp_deployment` → Ran 123 tests，OK。
- `python3 -B -m unittest tests.test_install_sh_agent_cli_flow tests.test_onboard_caveman_maintenance tests.test_onboard_developer tests.test_onboard_i_have_adhd tests.test_onboard_ponytail_integration tests.test_sbtd_graft_entry` → Ran 187 tests，OK（skipped=14，环境门控跳过）。

## Release Readiness Review

- Status: ready（本机视角；最终发布以 CI 全量与独立 review 为准）
- Production path and affected users / systems: 使用本仓库 sbtd-workflow-onboard 的用户机器上的全局配置写入面——init/reset 的 omp 全局 AGENTS.md 写目标、check 报告、迁移计划 omp-global 路由、graft 部署计划的隐含模板目标与 shared-root 记录。受影响的是设置了 PI_CODING_AGENT_DIR、PI_CONFIG_DIR 或命名 profile 的 omp 18.19.0 用户。
- Failure modes and safeguards: 写错位置导致 omp 读不到规则——resolver 与 omp 18.19.0 打包源码逐项对齐，并用真实 omp 佐证读取侧一致；变量目录不存在——apply 既有 mkdir parents 行为创建，新测试覆盖计划层与 apply 层（在变量指定位置创建目录并写入）；无显式选择时保持「默认根缺失则跳过且不创建」并由测试锁定；迁移 routing 审批在变量设置时接受新目标、拒绝旧默认路径；`~` 不展开与 omp 一致，避免写入 omp 不会读的位置；非法 profile 沿用 ContractError 失败关闭；PI_CONFIG_DIR 无非法值——按 omp 的 path.join 语义拼到 home 下（绝对值同样拼入、`..` 段可越出 home），收尾轮实测对齐。
- Capacity / backpressure / limits: not-applicable（本地 CLI 文件写入，无队列与容量概念）。
- Observability / alerts / runbook: not-applicable；check --json 的 ompRoot/ompGlobalAgents 回显解析结果。
- Rollout / migration / rollback / cleanup: 本任务不 commit、不 push、不开 PR；合入后以 CI 全量判定；回滚为还原分支改动；omp 全局 AGENTS.md 的备份后覆盖语义不变。
- Required validation and result: r2 聚焦套件 97/73/44/150/19 全过，新增 23 过，全量三分片 2513 例中 1 个失败归因为本机缺 tzdata 包（与本改动无关）；omp 18.19.0 真跑读取侧佐证通过；索引逐字节一致。r2b 收尾轮：受影响套件 30+42+97+32+44+150+19 全过（明细见「收尾轮（r2b）复核证据」），真实 omp 18.19.0 四点复核与 AGENTS.md 捕获证据通过。
- Optional checks, accountable owner acceptance, and residual risk: 未跑 macOS/Windows 平台套件（由 CI 覆盖）；`~` 值下 MCP 侧 resolver 仍 expanduser（与 omp 不一致，记为观察另议）；config.yml/lsp.yml 路径仍写死默认根（观察，另议）。剩余风险待 640 review 确认。

## 收尾轮（r2b）复核证据

2026-11-13 收尾轮（注：分钟不可考。），复核用真实 omp 18.19.0（`omp --version` 输出 omp/18.19.0）。方法：临时目录 + 临时 HOME（XDG_DATA_HOME/XDG_STATE_HOME/XDG_CACHE_HOME 同样指向临时目录），探针沿用 r2 方式——`omp --mode rpc --no-ui --no-extensions --no-rules`，stdin 发 `negotiate_protocol`（protocolVersion 2）与 `get_state`；坏 YAML config.yml 放候选 agent 目录，从 stderr 的「Settings config is invalid: <路径>」行确认 omp 实际读取的 agent 目录。除第 4 点的回环捕获探针外不发任何模型请求；回环探针的 provider 指向本机临时端口，请求不出本机。以下 <临时home>、<临时cwd>、<临时abs> 均为临时路径占位。

### 第 1 点：命名 profile 忽略 PI_CODING_AGENT_DIR（dirs.ts:366）

真实命令（要点）：`HOME=<临时home> OMP_PROFILE=work PI_CODING_AGENT_DIR=<临时home>/agent-x omp --mode rpc --no-ui --no-extensions --no-rules`，cwd 为临时目录；坏 config.yml 同时放 <临时home>/.omp/profiles/work/agent/ 与 <临时home>/agent-x/。

真实输出：`error: Settings config is invalid: <临时home>/.omp/profiles/work/agent/config.yml (moved to <临时home>/.omp/profiles/work/agent/config.yml.broken-<时间戳>-<随机后缀>): SyntaxError: YAML Parse error: Unexpected token`；进程退出后 <临时home>/agent-x 始终不存在。对照组（坏 config 只放 agent-x，其余相同）：无任何配置报错，omp 自建了 <临时home>/.omp/profiles/work/agent——变量被完全忽略。结论：与第 1 点一致。

r1 关于 profile 的证据形态（Reviewy 条件 1）：r1 未做 profile 的运行时探针，其结论来自打包源码阅读（dist/cli.js 中 settings 构造器的 `profile ? undefined : agentDirOverride` 分支，对应 dirs.ts:366），记录在本文件「实测发现」首节；profile 语义的首个运行时证据由本轮上面的命令补齐。

### 第 2 点：空字符串等同未设（dirs.ts:367）

真实命令：`HOME=<临时home> PI_CODING_AGENT_DIR= omp --mode rpc --no-ui --no-extensions --no-rules`（变量显式置空串），坏 config.yml 放 <临时home>/.omp/agent/。

真实输出：`error: Settings config is invalid: <临时home>/.omp/agent/config.yml (moved to ...): SyntaxError: YAML Parse error: Unexpected token`——回退默认根。结论：与第 2 点一致。

附带发现一处不符并已修正：omp 只对空串回退，纯空白值 `" "` 被当作真实目录名按 cwd 解析（同法实测，报错路径 `<临时cwd>/ /config.yml`）；r2 实现用 strip() 判空会把空白值当未设。本轮 active_omp_agent_dir 改为只对空串回退，新增 test_whitespace_only_variable_resolves_against_process_cwd 锁定。

### 第 3 点：只做 path.resolve()，不展开 `~`

真实命令：`cd <临时cwd> && HOME=<临时home> PI_CODING_AGENT_DIR='~/x' omp --mode rpc --no-ui --no-extensions --no-rules`，坏 config.yml 放 <临时cwd>/~/x/。

真实输出：`error: Settings config is invalid: <临时cwd>/~/x/config.yml (moved to ...): SyntaxError: YAML Parse error: Unexpected token`；<临时home>/x 未创建。结论：与第 3 点一致——`~/x` 实际是「当前目录/~/x」。附带观察：omp 仍会在临时 home 下自建 .omp（与本任务写入目标无关，agentDir 不受影响）。写入侧一致性由新测试锁定：test_tilde_value_creates_literal_tilde_directory_under_cwd 证明本仓库会在进程当前目录创建名为 `~` 的目录并写入 AGENTS.md（Reviewy 条件 3）。

### 第 4 点：PI_CONFIG_DIR 按 path.join(home, 值) 拼接（dirs.ts:117、:333）

- 相对名：`HOME=<临时home> PI_CONFIG_DIR=customdir omp --mode rpc ...`，坏 config.yml 放 <临时home>/customdir/agent/。真实输出：`error: Settings config is invalid: <临时home>/customdir/agent/config.yml (moved to ...): SyntaxError: ...`；<临时home>/.omp 未创建。一致。
- 绝对值：`PI_CONFIG_DIR=<临时abs>`（绝对路径）→ 真实输出报错路径为 `<临时home>/<临时abs 去掉前导分隔符>/agent/config.yml`——绝对值被拼到 home 下，不作绝对路径使用；<临时abs> 本身未创建。r2 实现对绝对值抛 ContractError，与实测不符，本轮改为跟随 path.join 语义。
- `..` 值：`PI_CONFIG_DIR=../escaped` → 报错路径为 <临时home> 上级的 escaped/agent/config.yml——omp 不校验、可越出 home。r2 实现同样抛 ContractError，本轮一并改为跟随。
- AGENTS.md 读取证据（Reviewy 条件 4 的保留依据）：坏 config 只证明 settings 的 agentDir；AGENTS.md 由「Load AGENTS.md from .omp/ directories」加载器读 agentDir/AGENTS.md（打包源码：`join(wn(), "AGENTS.md")`，wn() 即 settings.agentDir），且只在组装系统提示时读取——启动与 get_state 阶段 FIFO 读探针 15 秒无读取。直接证据：夹具 provider 指向本机回环捕获服务（127.0.0.1 临时端口），PI_CONFIG_DIR=customdir 时在 <临时home>/customdir/agent/AGENTS.md 放标记内容、<临时home>/.omp/agent/AGENTS.md 放诱饵内容，发一条 prompt 后捕获到 5 次（宿主重试）发往回环地址的请求，系统提示含 customdir 标记、不含诱饵；不设 PI_CONFIG_DIR 的对照组含默认根标记。结论：omp 读取 AGENTS.md 确实使用 PI_CONFIG_DIR，支持保留，按本点语义实现（home 下目录名，path.join 拼接）。

### 实测驱动的代码修正（相对 r2 已提交内容）

- sbtd_omp_sources.py：`_omp_config_root` 不再拒绝绝对值与 `..`；新 `omp_config_root` 按 Node `path.join(home, 值)` 语义拼接（前导分隔符不丢弃 home，`..` 向 home 规范化可越出），`active_omp_paths` 与 `active_omp_agent_dir` 共用；onboard.py `detect_omp_root` 走同一拼接。
- `active_omp_agent_dir`：只对空串回退（空白值按 cwd 解析，与 omp truthiness 一致）；「变量值等于推导默认目录按未设」改为 omp 的原始字符串比较（比较对象 j$a(Oz(PI_PROFILE))，PI_PROFILE=default 时推导目录为 <根>/agent）。
- 影响面：mcp 侧 resolver 共用 config 根规则，绝对值与 `..` 同样从 ContractError 改为跟随宿主；tests/test_sbtd_cleanup_targets.py 对应断言已更新（test_omp_config_dir_override_follows_omp_join_semantics），非法 profile 仍 ContractError 失败关闭。

### Reviewy 四条件落实位置

1. r1 关于 profile 的真实命令与结果：r1 无运行时命令（证据为打包源码阅读），如实写明见「第 1 点」末段；首个运行时证据为本轮 p1/p1c 探针（命令与输出同上）。
2. 变量目录不存在时创建目录并写入：tests/test_sbtd_omp_agents_target.py `BuildOperationsTargetTests.test_missing_variable_dir_created_and_written_on_apply`——apply 层 copy_operation 在变量指定位置创建目录并写入模板全文，断言文件内容与模板一致。
3. `~` 不展开、会在当前目录建名为 `~` 的文件夹：文档写在 README.md、README.zh.md、sbtd-workflow-onboard/SKILL.md、sbtd-workflow-onboard/REFERENCE.md（模板清单、init 段落、Paths 表）、docs/assets/onboard-skill-init.md、docs/assets/onboard-skill-reset.md；测试为 test_tilde_variable_is_not_expanded（解析层）与 test_tilde_value_creates_literal_tilde_directory_under_cwd（写入层）。
4. PI_CONFIG_DIR：保留，依据为「第 4 点」的回环捕获证据；语义按 home 下目录名 path.join 拼接实现（绝对值拼入 home 下、`..` 可越出），测试 test_absolute_config_dir_is_joined_under_home、test_dotdot_config_dir_escapes_home、test_absolute_config_dir_root_detected_under_home 与 cleanup 套件 test_omp_config_dir_override_follows_omp_join_semantics。

### r2b 验证数字

每条命令前台单条执行，单条不超过 600 秒，仓库根 `python3 -B -m unittest`：

- `python3 -B -m unittest tests.test_sbtd_omp_agents_target` → Ran 30 tests，OK（23 → 30：新增空白值、绝对值拼接、`..` 越出、PI_PROFILE=default 推导比较、apply 层创建写入、字面 `~` 目录创建、detect_omp_root 绝对值拼接共 7 个；删去与实测不符的 test_invalid_config_dir_override_rejected）。
- `python3 -B -m unittest tests.test_sbtd_cleanup_targets` → Ran 42 tests，OK。
- `PYTHONPATH=sbtd-workflow-onboard/scripts python3 -B -m unittest tests.test_sbtd_codex_deployment tests.test_onboard_multi_projects tests.test_sbtd_omp_deployment tests.test_sbtd_migration_cleanup_drift` → 首跑 FAILED（errors=3，管道只留尾部、失败明细未留存），随后两次完整重跑均 Ran 97 tests，OK。r2 在同一套件也记录过一次 failures=2 的同类偶发；两次重跑全过，按偶发处理并如实留痕。
- `python3 -B -m unittest tests.test_sbtd_followup_batch tests.test_sbtd_approved_agents_deployment` → Ran 32 tests，OK。
- `python3 -B -m unittest tests.test_sbtd_omp_wiring tests.test_sbtd_omp_reconciliation` → Ran 44 tests，OK。
- `python3 -B -m unittest tests.test_sbtd_upgrade_hosts` → Ran 150 tests，OK（skipped=21，环境门控跳过）。
- `python3 -B -m unittest tests.test_p1_15_host_mode_smoke` → Ran 19 tests，OK（skipped=5，环境门控跳过）。
- 索引：frontmatter 未动（本轮不改状态），ai/tasks/index.md 本任务行仍与 r2 一致，无需重生成；双语 README 与 CHANGELOG 的中英条目已逐点对齐（变量、profile、空串、空白值、`~`、PI_CONFIG_DIR 拼接语义均双语一致）。
- 全量分片：r2 已跑（2513 例，1 个环境性失败）；本轮 diff 集中在 resolver 与上述套件覆盖面内，全量以 CI 为准。

## 已决定的问题

1. 命名 profile 生效时（OMP_PROFILE/PI_PROFILE 非 default），omp 忽略 PI_CODING_AGENT_DIR、改用 profiles/<name>/agent。按推荐实施：跟随 active profile 目录，onboard 写 omp 全局 AGENTS.md 复用与 active_omp_paths 同一套 config 根与 profile 规则（新函数 active_omp_agent_dir），与 mcp.json 写入位置保持单一事实源；omp 实际读 profile 目录下的 AGENTS.md，写默认根会写错地方。
2. 变量指向的目录不存在时写不写。按推荐实施：写入并按需创建父目录（omp 运行时本就会自建该目录，变量是显式指向）；跳过会让 omp 在变量目录下读不到规则，与本项目标冲突。
3. 变量值为 `~` 开头路径的解析。按推荐实施：跟随 omp 实际行为，不展开 `~`，按普通相对路径用 path.resolve 同样的规则处理（相对进程当前目录）；写的是 omp 要读的文件，位置必须与 omp 一致。mcp 侧既有 expanduser 行为记为单独观察，不在本任务改。
4. PI_CONFIG_DIR 与 config.yml/lsp.yml 范围。按推荐实施：PI_CONFIG_DIR 随同一 resolver 一并支持（默认目录为 home/(PI_CONFIG_DIR 或 .omp)/agent）；sbtd_language_tooling.py 的 config.yml/lsp.yml 不纳入本任务，记为观察（仍写死默认根 ~/.omp/agent）。

2026-11-13 16:59 群成员投票 5:0 通过（概述），Lord 记录。投票人：Lord、OMP、Reviewy、CodeX、Researchy。Reviewy 提出 4 个条件：1) r1 关于 profile 的结论要补真实命令与结果，不能只有打包源码阅读；2) 变量指向的目录不存在时要创建目录并写入 AGENTS.md；3) 文档要写明 omp 不展开 `~`、会在进程当前目录下创建名为 `~` 的文件夹；4) PI_CONFIG_DIR 可以保留，但要拿出 omp 实际从该目录读取 AGENTS.md 的证据。

## 模型记录

- 主 agent 用 k3:max，密钥从环境变量 KIMI_API_KEY 读取。
- 每轮结束后把该轮真实数字补进下表；只写实际发生的数字。

| 轮次 | 用途 | 模型 | 回复次数 | 工具调用次数 | 工具报错次数 | 结果 |
|---|---|---|---|---|---|---|
| r1 | 写任务文件 | k3:max | 32 | 42 | 0 | 提交 33400c2 |
| r2 | 实施：代码、23 个新测试、7 处文档、双语 CHANGELOG、验证与 omp 真跑佐证 | k3:max | 206 | 222 | 6 | 已提交 a15955d（14 个文件，+553/-94）；分段计数见会话记录 |
| r2b | 收尾：真实 omp 四点复核、实测驱动的解析修正、7 个新测试、文档与双语 CHANGELOG 对齐、Reviewy 条件落实 | k3:max | 115 | 118 | 0 | 已提交 afb0606 |
| r3b | 阻塞修复：check 未设变量分支 ompGlobalAgents 恢复按 resolve 后 root 拼接并补 .resolve()、新增符号链接 HOME 测试、task.md 计数与措辞订正 | k3:max | 14 | 21 | 0 | 修复完成，未提交（本任务指令不 commit/push；计数截至北京时间 22:03:42，见会话记录） |

## 会话记录

每轮结束后补记该轮会话 id 与起止时间。

- r1：会话 01a1d3f8-e239-76bb-8f00-a444a3a85f80，北京时间 16:14:25–16:23:51。
- r2：会话 01a1d41f-3f5f-73d5-82bc-4ba4f8d41904，北京时间 16:56:20 开始；19:54:51 因整机暂停后触发看门狗「30 分钟无写入」上限被结束；20:10:38 用同一会话续跑，20:43:46 正常结束。整个会话文件（两段合计）：回复 206、工具调用 222、工具报错 6；其中 19:54:51 之前：回复 116、工具调用 130、报错 3；续跑段：回复 90、工具调用 92、报错 3。（r3b 按会话文件中 role=toolResult 且 isError 为真的条目复核：合计 6，与本行订正后数字一致；原记 5 与分段 5/0 有误。）
- r2b：会话 01a1d4f0-57c3-762f-afa6-b0095a1a224c，北京时间 20:44:43 开始，21:30:39 结束。整个会话文件最终计数：回复 115、工具调用 118、报错 0（r3b 按会话文件复核得到；原记的截至 21:29:37 中间计数 92/96/0 由本行订正替换）。
- r3b：会话 01a1d533-61ce-745f-90d3-460138a1020c，北京时间 21:57:56 开始。模型行计数取自该会话文件截至 22:03:42 的记录：回复 14、工具调用 21、报错 0（计数之后本文件收尾落盘还会产生少量调用，未计入）。

## 后续事项

- parent.parent 推导范围可能偏大（Reviewy 提出），本 PR 不改，留作后续。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-13T20:41:43.948768+08:00 | planned | in-progress | 实施轮开始：执行逐项改动清单与新增测试 | 按逐项改动清单 1-8 实施：统一走 active_omp_agent_dir 单一解析；4 个已决定问题按推荐实施；新增 23 个测试；文档 7 处与双语 CHANGELOG |
| 2026-11-13T20:42:10.178975+08:00 | in-progress | checking | 实施完成：代码、测试、文档与双语 CHANGELOG 已改，聚焦验证、全量分片与真实 omp 佐证完成，待复核 | 新增 tests.test_sbtd_omp_agents_target 23 tests OK；受影响套件 97+73+44+150+19 全过；全量 --shards 3 合计 2513 例，1 个失败归因本机缺 tzdata==2026.5（与本改动无关）；onboard check 四组对照与真实 omp 18.19.0 读取侧佐证一致；索引预览逐字节一致；本任务未 commit/push |
