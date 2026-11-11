---
schema_version: 1
id: v2.1.0-rc.5-host-gate-codex-0167-omp-18188
workflow_mode: strict
mode_source: user
mode_note: "用户 2026-11-11 15:10 群内确认（rc.5 全程 strict、每个 PR 自带 CHANGELOG、主模型 astra），Lord 记录"
status: "checking"
branch: contract/rc5-host-gate-codex-0167-omp-18188
created_at: '2026-11-11T14:48:27.312232+08:00'
updated_at: "2026-11-11T19:18:45+08:00"
completed_at: null
---
# rc.5 宿主验收门禁契约变更

## 目标与范围

用户 2026-11-11 14:43 群内确认（选择选项 1：以单独契约 PR 换门禁），Lord 记录；据此将门禁换为 codex@0.167.1 + omp@18.18.8。只改契约、相关版本说明、golden 与测试、双语 CHANGELOG 和本任务/index；不改适配器逻辑、ENTRYPOINT、README 或 release notes，不 commit/push/开 PR，不用子代理。

未完整调用 grill-with-docs：用户决定（见下）、版本、真实冒烟事实与交付边界均明确，无领域歧义。

## strict mode 落实方式

- 任务文件在开工前创建并落盘；每个阶段用 `TaskStore` 记录真实状态事件，不手改状态时间。
- 验证证据（命令、结果、失败归因）写入本文件；Book Gate Plan 已列，已有验证结果与本轮补充证据分开记录。
- 冒烟证据来自真实宿主运行（云主机实测），不用 parser fixture 作为实测证据。
- 第 3 轮仅修订任务记录、ADR 第 8 节与矩阵 smoke_note 的归属措辞，并检查生成索引；不改生产代码、门禁语义或测试，双语 CHANGELOG 保持不变。无新增领域、数据、重构或发布风险，不触发新的 Book Gate；下方既有 Gate 结果为前轮证据，不冒充本轮重新执行。
- 状态停在 checking，等待 Reviewy 对完整 SHA 的审查与 CI 13/13；合并需 640 说「合入」后由 Lord 合并，本 bot 不合并。

## Book Gate Plan

| 方法 | 触发与阶段 | 状态与证据 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，before-dev | not-required；均未触发 |
| book-ddia-data-design | 静态共享契约扩展，before-dev | confirmed；矩阵直接加载，host_capability 只读 acceptance_pins；smoke_history 不参与判定，无存储迁移 |
| book-legacy-change-safety | 弱测试或高风险既有行为，before-dev | not-required；仅换静态 pin，既有 golden 覆盖，解析与存储逻辑不变 |
| book-refactoring-pass | 既有生产文件编辑前 | proceed / normal；no refactor needed，仅 docstring/help 修改 |
| gherkin-bdd | 当前门禁分类可观察，before-dev/check | traceable；沿用中文 Markdown spec 与英文关键字；完成门、非门禁不影响指标、换针后三类场景分别对应既有 gate/golden 测试与新增四版本测试 |
| project-validation | 契约与测试改动后 | 已执行聚焦门禁与 runtime 验证；Linux 全量主动中止，失败归因与验证边界见下文；全量以 CI 三平台分片为准 |
| book-release-readiness | 运行时/部署/发布风险，验证后 | not-required；不部署、不发布，不改适配器执行逻辑 |
| 独立 review 与 CI | 契约 PR 检查 | pending；编排方要求停在 checking；本任务各轮均不使用子代理 |
| ponytail-review / Code Readability Review | 修改后自检 | 无新增抽象或依赖；一个四版本参数表覆盖新旧分类，无逻辑重构；不代替独立 review |

## 设计与保留行为

- `contract_eval.capability_matrix()` 直接加载 JSON，`host_capability()` 只遍历 `acceptance_pins`；全仓消费者检索未发现矩阵专用 schema 或拒绝额外字段的校验。`event.schema.json` 仅校验观察事件，不校验矩阵。新增可选 `smoke_history` 与数据字典说明，不改 schema_version、release 或评估器。
- 当前 `smoke` 与历史 `smoke_history` 都按宿主保存 status、host_version、smoked_at、evidence。旧 omp 的 pass 保留，但不影响当前旧版本的 unsupported 分类；兜底完成门仍 ≥1，parser fixture 不算真实证据。
- `evaluate()` 对 accepted 事件的 host 调用 `host_capability()`，capability 与指标计算分开。golden 更新 8 条合成事件的版本：`evt_loaded`、`evt_inv1_start`、`evt_inv1_host`、`evt_inv1_finish`、`evt_inv1_conflict`、`evt_inv2_start`、`evt_inv2_finish`、`evt_gap`。`expected.json` 只断言指标、分子分母和来源事件，不含宿主版本，故保持不变。golden 不是实测证据，不改事件日期、ID 或指标数值。
- OMP 历史会话形状夹具不依赖门禁，保持 `test_omp_adapter.py` 原样。适配器解析、lease、开关、入库、去重与重放逻辑均不改。
- TaskStore 源码提供 Python library API，没有 CLI：第 1 轮用 `create(..., mode="strict", confirmed=True)` 创建任务并自动更新 index/受 ignore 保护的 active 引用，各轮用 `transition()` 记录真实状态事件；不手改状态时间。独立克隆分支与授权分支一致，任务路径不存在冲突，既有 ignore 保护已核对，不改 ignore。

## 旧版本 grep 逐条决定表

初始全仓扫描使用专用 grep，正则与 `rg -n '0\.163\.0|18\.11\.1'` 相同。下列行号指编辑前基线，列出每个命中；同一行的两个版本采用同一决定。复扫残留只属于历史事实、换针说明或旧版本 unsupported 断言。

| 文件（仓库相对路径） | 基线行 | 决定与理由 |
|---|---|---|
| CHANGELOG.md | 22 | 保留：rc.4 当时不改门禁的历史决定 |
| CHANGELOG.md | 115 | 保留：rc.1 原始 smoke 历史 |
| CHANGELOG.zh.md | 22 | 保留：与英文 rc.4 历史对应 |
| CHANGELOG.zh.md | 115 | 保留：与英文 rc.1 历史对应 |
| ai/tasks/v2.1.0-rc.1-r1.0-review-fixes/task.md | 59 | 保留：旧任务验收不变量 |
| ai/tasks/v2.1.0-rc.1-r1.2b-host-adapters/task.md | 15 | 保留：旧任务范围与门禁 |
| 同上 | 25 | 保留：当时文档交付范围 |
| 同上 | 33 | 保留：旧 omp 验收要求 |
| 同上 | 34 | 保留：旧 codex 指令要求 |
| 同上 | 39 | 保留：历史 fixture 来源 |
| 同上 | 68 | 保留：当时字段形状边界 |
| 同上 | 130 | 保留：旧 omp smoke 标题 |
| 同上 | 132 | 保留：原始运行记录，不重写旧任务 |
| 同上 | 142 | 保留：旧 omp 原始回执 |
| 同上 | 148 | 保留：当时重放结果和 codex pending 状态 |
| 同上 | 156 | 保留：历史状态事件 |
| 同上 | 162 | 保留：旧 codex 版本事实 |
| ai/tasks/v2.1.0-rc.1-r1.4-acceptance/task.md | 90 | 保留：旧验收任务边界 |
| docs/adr/0001-v2.1.0-rc.1-r1.0-runtime-decisions.md | 106 | 保留：原 Q4 对 Q6 的历史引用 |
| 同上 | 147 | 保留：原 Q6 决策；仅文末追加第 8 节 |
| 同上 | 157 | 保留：原分宿主验收规则 |
| 同上 | 161 | 保留：原 codex 门禁 |
| 同上 | 162 | 保留：原 omp 门禁 |
| sbtd-runtime/codex_adapter.py | 18 | 更新：当前现场 smoke 指令版本 |
| 同上 | 221 | 更新：CLI help 版本示例 |
| sbtd-runtime/omp_adapter.py | 9 | 保留 18.11.1 历史，并补充 18.18.8 实测 |
| sbtd-runtime/contracts/capability-matrix.json | 7 | 更新：codex acceptance pin |
| 同上 | 11 | 更新：omp acceptance pin |
| 同上 | 20 | 更新：completion_gate codex |
| 同上 | 21 | 更新：completion_gate omp |
| 同上 | 34 | 迁入 smoke_history：保留旧 omp 版本与 pass |
| 同上 | 40 | 迁入 smoke_history：保留旧 codex 版本与 unsupported；证据改用仓内旧 task 引用 |
| 同上 | 45 | 更新：当前两宿主 pass，解释历史不参与门禁 |
| sbtd-runtime/docs/host-adapters.md | 23 | 更新当前标题，保留旧 omp 历史标识 |
| 同上 | 25 | 保留旧字段来源，补充新 omp 实测 |
| 同上 | 48 | 更新当前 codex 标题 |
| 同上 | 62 | 更新当前门禁，说明历史与不变规则 |
| 同上 | 64 | 更新 codex 现场步骤标题 |
| 同上 | 66 | 更新 codex 前置版本 |
| 同上 | 69 | 更新 codex 版本检查注释 |
| 同上 | 99 | 更新 codex 通过判定版本 |
| sbtd-runtime/docs/install-and-use.md | 125 | 更新当前双宿主门禁与结果 |
| sbtd-runtime/docs/r1.4-acceptance-report.md | 104 | 保留：旧正式验收报告，不重写历史 |
| sbtd-runtime/golden/dataset.json | 1525 | 更新：evt_loaded 当前 codex pin 样本 |
| 同上 | 1576 | 更新：evt_inv1_start |
| 同上 | 1635 | 更新：evt_inv1_host，同一调用的宿主观察 |
| 同上 | 1694 | 更新：evt_inv1_finish |
| 同上 | 1753 | 更新：evt_inv1_conflict，保留原冲突语义 |
| 同上 | 1812 | 更新：evt_inv2_start 当前 omp pin 样本 |
| 同上 | 1871 | 更新：evt_inv2_finish |
| 同上 | 2922 | 更新：evt_gap 当前 omp 采集缺口 |
| sbtd-runtime/spec/r1.0-contract-scenarios.md | 103 | 更新当前针，保留 codex 0.164.0 非门禁例 |
| 同上 | 123 | 更新兜底完成门的当前宿主 |
| sbtd-runtime/spec/r1.2b-host-adapter-scenarios.md | 136 | 更新当前 codex smoke 指令引用 |
| sbtd-runtime/tests/test_codex_adapter.py | 6 | 更新当前 smoke 文档引用，仅 docstring |
| sbtd-runtime/tests/test_golden_contracts.py | 105 | 更新完成门集合断言 |
| 同上 | 292 | 更新 golden codex pinned 断言 |
| 同上 | 293 | 更新 golden omp pinned 断言 |
| 同上 | 296 | 移入四版本参数化断言：新针 pinned、旧针 unsupported |
| sbtd-runtime/tests/test_omp_adapter.py | 4 | 保留：历史字段形状来源 |
| 同上 | 51 | 保留：原 session runtime 版本 |
| 同上 | 61 | 保留：原 toolCall runtime 版本 |
| 同上 | 88 | 保留：原 toolResult runtime 版本 |
| 同上 | 104 | 保留：原 toolResult runtime 版本 |
| 同上 | 177 | 保留：解析器忠实转录原宿主版本的断言 |
| 同上 | 311 | 保留：历史会话 ingest 回执版本断言 |

ENTRYPOINT.md 监控基线不在范围；README、release notes、旧 ai/tasks 与旧 CHANGELOG 条目均不改。双语 CHANGELOG 的 rc.5 未发布节各保留一条 Changed/变更，逐条同义。

## 冒烟证据（来源：云主机实测）

冒烟由 CodeX bot（codex）与 OMP bot（omp）执行，编排方整理；不声称本轮编辑重新运行宿主。

### codex 0.167.1 — pass

- 执行者 CodeX bot；`codex --version` → `codex-cli 0.167.1`；开始 2026-11-11 14:36:15 +08:00；main `80f1426` 只读副本。
- 命令形态 `codex exec --json --sandbox read-only`，提示执行 `echo sbtd-r12b-smoke`。JSONL 7 行，依次为 thread.started、turn.started、item.completed(agent_message)、item.started(command_execution)、item.completed(command_execution, exit_code=0, status=completed)、item.completed(agent_message "done")、turn.completed；一次真实工具调用。
- 回执 source_id=codex-exec，host_version=`codex-cli 0.167.1`，parser_version=codex-exec-jsonl-1，records_read=7，records_skipped=4，events_emitted=2，accepted=2，duplicate=0，conflict=0，rejected=0，dropped=[]。
- 重放 invocation.started + invocation.finished，component `tool:command_execution`（kind tool）。运行完成，命令 exit_code=0；进程退出码未单独记录 → 未知。使用全局默认模型，JSONL 没有模型名 → 未知；1 turn。
- codex 首次真实冒烟通过。2026-10-17 的 0.163.0 因 ChatGPT 后端 HTTP 403／workspace routing discovery failed 未采到事件，unsupported 历史不改写。

### omp 18.18.8 — pass

- 执行者 OMP bot；`omp --version` → `omp/18.18.8`；2026-11-11 14:40:30–14:40:38 +08:00，main `80f1426` 只读副本旁临时目录；退出码 0、stdout `done`。
- `omp -p --model openai-codex/gpt-6-astra:high --tools read,write,edit,bash,grep,glob,find,todo --no-title`，提示强制 read 读取一个系统文件再回复 done。host-adapters.md 只有 codex 现场步骤；本次参照 2026-10-17 omp 18.11.1 冒烟做法，将会话文件交给 omp_adapter.py。
- 会话 13 行，session header version 3，runtime.version=18.18.8；第 8 行 assistant toolCall name=read；第 11 行 toolResult 同 toolCallId、toolName=read、isError=false。新记录类型 credential_pin 按未知类型跳过并计数，不报错。
- 回执 source_id=omp-session，host_version=18.18.8，parser_version=omp-session-jsonl-1，records_read=13，records_skipped=9，events_emitted=2，accepted=2，duplicate=0，conflict=0，rejected=0，dropped=[]；重复导入 accepted=0、duplicate=2。
- 重放 invocation.started（2026-11-11T06:40:35.617Z）+ invocation.finished（2026-11-11T06:40:35.645Z），component `tool:read`，succeeded，duration_ms=28（wall）。
- 当时旧矩阵：18.18.8 unsupported、18.11.1 pinned；本次改为 18.18.8 pinned、18.11.1 unsupported。stderr 有一条 MCP server `sbtd-graft` 连接失败警告，本次冒烟不依赖它。
- 模型 openai-codex/gpt-6-astra、thinking high，2 次调用（1 次工具调用回合 + 1 次最终回复）。

## 本任务模型记录

| 工作 | 宿主／模型 | 调用次数与边界 |
|---|---|---|
| 第 1 轮文件编辑（omp 18.18.8 会话统计） | 主模型 openai-codex/gpt-6-astra（thinking high）；`typesafe/jev-latest` | 主模型 31 次 assistant 调用；`typesafe/jev-latest`：omp find 工具内部调用 45 次。工具调用：read 50、bash 11、grep 11、todo 9、edit 8、find 2、glob 1；无 task 工具、无子代理 |
| 第 2 轮文件编辑（omp 会话日志统计，executor 调度 bot 统计） | 主模型 openai-codex/gpt-6-astra（thinking high）；`typesafe/jev-latest` | 主模型 18 次 assistant 调用；`typesafe/jev-latest`：find 未调用，0 次；工具调用 read 16、bash 10、todo 10、grep 5、edit 4、write 1（write 为仓外一次性检查脚本，不是仓库文件）；无 task 工具、无子代理 |
| 第 3 轮文件编辑（编排方第 4 轮按会话日志复核） | 主模型 openai-codex/gpt-6-astra（thinking high）；`typesafe/jev-latest` | 主模型 17 次 assistant 调用；`typesafe/jev-latest`：omp find 工具内部调用 11 次；工具调用 39 次：read 12、bash 10、todo 6、grep 4、edit 3、find 2、glob 1、write 1（仓外一次性检查脚本）；无 task 工具、无子代理 |
| 第 4 轮冲突处理会话 1（第 1 个提交） | 主模型 openai-codex/gpt-6-astra（thinking high） | 模型调用 8 次、工具调用 19 次；find 未调用；无 task 工具、无子代理 |
| 第 4 轮冲突处理会话 2（第 2 个提交） | 主模型 openai-codex/gpt-6-astra（thinking high） | 模型调用 5 次、工具调用 9 次；find 未调用；无 task 工具、无子代理 |
| 第 4 轮记录会话（本会话） | 主模型 openai-codex/gpt-6-astra（thinking high） | 模型调用 13 次、工具调用 33 次；计数脚本读得 astra_assistant=11、astra_toolcalls=32，按已有条数＋最终 edit＋收尾推算：模型 11＋1 次最终 edit 回合＋1 次纯文本收尾＝13，工具 32＋1 次最终 edit＝33；此 edit 为最后一次工具调用，其后仅纯文本收尾；日志 other_assistant={}、model_usage={}；find 未调用；无 task 工具、无子代理 |
| codex 0.167.1 冒烟 | 模型未知 | 1 次 codex 调用（1 turn） |
| omp 18.18.8 冒烟 | openai-codex/gpt-6-astra high | 2 次调用 |
| executor（调度 bot） | 不参与仓库文件编辑 | 只做 git commit/push、gh pr create 与验证命令，未直接编辑仓库文件 |

find 归属：第 1、3 轮 find 的后台归属来自会话日志字段，每条记录为 `"purpose":"find","provider":"typesafe","model":"jev-latest"`；按这些日志字段计数，第 1 轮 45 次、第 3 轮 11 次，不能归为主模型调用；第 2 轮与第 4 轮 find 未调用。

第 4 轮计数方法：omp 会话日志中筛选 `role=assistant`、`provider=openai-codex`、`model=gpt-6-astra` 的消息计模型调用，同一记录内 `toolCall` 条目计工具调用；其他模型仅在日志记录了其名字时才列出并计数。第 4 轮三会话日志均未记录其他模型名（如 jev-latest、composer），次数 0。

## 验证证据

- 第 1 轮验证对象：分支 `contract/rc5-host-gate-codex-0167-omp-18188`，基线 SHA `80f14263e7d8bc6ae84f04ba94218e4857fc8b8f` 加当轮未提交文件改动；不是该旧 SHA 的精确提交验证。Evidence Source: developer-local；Source Revision: dirty；Evidence Publication: local-only。
- Red：`PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python -B -m unittest test_golden_contracts.CapabilityMatrixTests.test_gate_replacement_unpins_historical_versions`，1 个测试、4 个 subtest 均因旧矩阵新旧分类相反而失败（exit 1），证明断言覆盖真实门禁行为，不是 parser fixture 冒充宿主实测。
- `PYTHONPATH=sbtd-runtime python -B -c` 调用 `capability_matrix()` / `host_capability()`：codex 0.167.1 与 omp 18.18.8 → pinned，codex 0.163.0 与 omp 18.11.1 → unsupported；exit 0。同次检查当前 smoke 两者 pass、历史 codex unsupported / omp pass 均符合预期。
- `python -B sbtd-runtime/codex_adapter.py --help`：exit 0，实际 CLI 显示 `codex-cli 0.167.1`。
- `python -B -m ruff check sbtd-runtime/codex_adapter.py sbtd-runtime/omp_adapter.py sbtd-runtime/tests/test_golden_contracts.py sbtd-runtime/tests/test_codex_adapter.py`：exit 1，两项既有未修改位置告警：OMP lease 的 subprocess.run 缺显式 check（PLW1510）；golden 测试原 import 块排序（I001）。不改适配器逻辑、不夹带无关格式修复；lint 不报通过。
- 路径检查：对 tracked diff 新增行使用同一禁止路径正则，零命中；新 task、矩阵、host-adapters 与 omp_adapter 全文件同样零命中。原 ADR、旧 CHANGELOG、旧文档/测试中未修改的路径文本不重写，按编排方“git diff 只看新增行”界定本次新增内容。旧 codex 矩阵证据已替换为仓内旧 task 引用。
- BDD: traceable；`sbtd-runtime/spec/r1.0-contract-scenarios.md` 为中文场景/英文关键字，`r1.2b-host-adapter-scenarios.md` 仅当前 smoke 说明换针；无新 .feature。Cross-repo context: not-needed；API Contract: not-needed（无 HTTP 契约改动）；Mock Strategy: none（门禁分类调用真实评估器）。rtk: skipped-for-report（原生测试与报告）；不运行 UI/移动端或发布验证，因为本轮不改这些表面。
- Runtime：`PYTHONPATH=sbtd-runtime python -B -m unittest discover -s sbtd-runtime/tests`，458 tests，188.329s，2 failures、10 skipped，exit 1。失败为 `RuntimePerfSmokeTests.test_cli_preserves_dataset_and_reports_unmeasured_boundaries`（performance CLI execution=failed）与 `NormalizeScopeTests.test_iana_queries_and_dst_work_without_system_timezone_data`（缺 Python tzdata，Asia/Tokyo 无可用时区数据）。全部 gate/golden 与适配器测试未报失败。Playwright 未安装，renderer 相关跳过/既有 stub 不视为真实浏览器验证；未安装依赖或修改范围外实现，不伪称全绿。
- 聚焦 Green：`PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python -B -m unittest test_golden_contracts.CapabilityMatrixTests test_golden_contracts.GoldenContractTests.test_unsupported_host_does_not_unsupport_the_metric test_golden_contracts.GoldenContractTests.test_golden_oracle_matches_every_metric`，4 tests，0.003s，OK，exit 0；覆盖新旧针、兜底规则、非门禁不取消指标、全指标 golden oracle。
- 性能失败诊断：`python -B sbtd-runtime/tests/runtime_perf.py --events 101 --samples 2 --seed-seconds 60 --output "$PERF_DIAGNOSTIC_OUTPUT"`（变量代指本轮仓外临时目录，实际命令使用该目录），exit 1；原生 `runtime-perf-101-contract_rc5-host-gate-codex-0167-omp-18188-20261111T065548863178Z.json` 与同 stem 中文 `.md` 已保留。报告 error 为 `AssertionError: `、html_panel_count=12，而 panel manifest 为 13；`runtime_perf.py:476-479` 按精确字符串 `class="panel"` 计数，导出样本 overview 实为 `class="panel panel-kpi"`。这是范围外 HTML smoke 计数断言问题，不是新门禁分类失败；保留失败，不改 UI、导出或性能测试。该诊断没有完成 CSV／四格式性能验证。
- 本地 Linux 全量由 executor 调度 bot 运行并中止，编排方整理：`python -B tests/run_ci.py --platform linux --shard 1 --shards 1` 单分片运行 25 分钟上下（未精确计时），完成 1044／4914 个用例后被主动中止；单分片太慢，全量以 CI 三平台分片为准。其间唯一异常 `tests.test_sbtd_migration_cleanup_drift.FollowupUpgradeProvenanceGateTests.test_followup_rejects_upgrade_backed_predecessor_cleanup` 在高负载下报 ERROR；本分支单独重跑 2 次均 OK，在 main `80f1426` 单独跑也 OK，判定为负载相关偶发，与本改动（契约/文档/golden）无关。
- Runtime 失败归因补充（main 基线复现由 executor 调度 bot 执行）：`test_cli_preserves_dataset_and_reports_unmeasured_boundaries`、`test_iana_queries_and_dst_work_without_system_timezone_data` 已在 main `80f1426` 的独立工作树上复现同样失败，属本机环境既有问题（面板计数断言、缺 tzdata），非本 PR 引入；本轮不重复运行这些已报告的失败。
- PR #209 首个提交 `5032425e9b9305e86053b57afff16979a35fb73e`（门禁变更）；第二个提交 `c419ac8c98d1e98ee46578629c2b8adcd70643c7` 的 CI run 42978591672 13/13 全部通过（executor 调度 bot 记录）。
- 冒烟核对（编排方整理，与 CodeX bot 在群内贴出的要点核对一致）：codex-cli 0.167.1，14:36:15 开始，7 行输出，进程退出码未记录，命令 exit_code 0、completed，末行 turn.completed；回执 records_read/records_skipped/events_emitted/accepted/duplicate 为 7/4/2/2/0，重放 started+finished `tool:command_execution`，模型未知，1 次 codex 调用（1 turn）。本轮只记录核对结果，不声称重新运行宿主。
- 第 2 轮验证对象：实际 HEAD `5032425e9b9305e86053b57afff16979a35fb73e` 加本轮未提交的文档修改，分支同上；Evidence Source: developer-local；Source Revision: dirty；Environment Alignment: unverified；Evidence Publication: local-only，不作为最终 PR SHA 的 CI 证明。
- 第 2 轮只改文件，不提交、不推送、不创建 PR；保留历史状态事件的当时事实，下文新增事件与本节结果取代旧事件中 Linux 套件仍在运行的进度描述，最终状态停在 checking。
- 第 2 轮 golden：`PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python -B -m unittest test_golden_contracts`，66 tests，0.389s，OK，exit 0。
- 第 2 轮任务相关测试：用专用 grep 执行与 `rg 'CHANGELOG\.zh\.md|ai/tasks/index\.md'` 等价的检索，命中 `tests/test_sbtd_task_state.py` 与 `tests/test_workflow_contracts.py`；另在 tests、runtime tests、Onboard scripts 与 CI 配置中检索 CHANGELOG/changelog，无测试命中，未发现双语一致性测试。运行 `python -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts`，99 tests，39.344s，OK，exit 0。
- 第 2 轮文档检查：仓外一次性 Python 检查器读取 `git diff --no-ext-diff --unified=0`，仅三文件修改，新增行与 task 全文均无仓库规则禁止的本机路径（Reviewy 审查硬项）；输出 `SCOPE_OK 3 files; ADDED_LINES_LOCAL_PATHS 0; TASK_LOCAL_PATHS 0`。双语 rc.5 节均为一个 Changed/变更小节、一个条目，代码标识多重集合一致，人工逐条核对语义一致；rc.4 起已发布历史与 HEAD 相同，输出 `BILINGUAL_RC5_STRUCTURE_IDENTIFIERS_OK; RELEASED_HISTORY_UNCHANGED`。TaskDocument／TaskStore 只读校验模式、事件链及 updated_at 与末事件时间一致，输出 `TASK_STATE_OK in-progress events 3`；均 exit 0。
- 第 2 轮验证边界：rtk: not-needed（编排方指定原生命令）；BDD: skipped（仅文档，无新增场景或行为）；Cross-repo context／API Contract: not-needed；Mock Strategy: none。未重跑 Linux 全量、runtime 已知失败、宿主冒烟、lint、构建、Web／Mobile 或发布验证：本轮仅文档补齐，历史失败与全量 CI 待验边界已明确。Final Test Report／Run Summary MD: not-needed，本轮为本地定向 unittest 与文档检查，结果写入本文件，不新增正式报告；不声称独立 review 或 CI 已通过。
- 状态写入执行记录：首次 `TaskStore.transition(..., "checking", confirmed=True)` 在宿主工具设置的 30 秒上限超时，输出为历史任务的「旧格式事件，不追溯」提示；重读确认仍为 in-progress、3 条事件、updated_at 未变，没有把超时记作成功或手填时间。随后仅放宽调用时限重试同一 library API，不更改库或任务生命周期。

### 第 3 轮：Reviewy 措辞／记录修复

- 验证对象：分支 `contract/rc5-host-gate-codex-0167-omp-18188`，HEAD `c419ac8c98d1e98ee46578629c2b8adcd70643c7` 加本轮未提交修改；Evidence Source: developer-local；Source Revision: dirty；Environment Alignment: unverified；Evidence Publication: local-only。本轮没有 commit/push，不以旧 SHA 的 CI 代替新改动验证。
- 归属核对：冒烟执行者为 CodeX bot／OMP bot；Linux 全量、中止、main 复现与 CI 结果由 executor 调度 bot 记录；汇总与执行边界归编排方。对 `git diff origin/main` 所有新增行逐条核对归属，host-adapters.md、install-and-use.md 与双语 CHANGELOG 无需再改；其余保留的用户字样为已注明来源的决定、决定引用、审查问题分类或回到用户决策的不变规则。
- 决定时间均为北京时间：升级 codex 为 14:34，选项 1 为 14:43，strict／每 PR CHANGELOG／主模型 astra 为 15:10；统一群内确认与 Lord 记录格式，mode_note 使用带引号 YAML。本轮按 Reviewy 意见修订了这几条历史事件的归属措辞，时间与状态未改。
- 已更正首个提交 SHA 的编排方笔误，并以第二个提交的 CI run 42978591672、13/13 通过替换过期进度说明；此 CI 事实来自 executor 调度 bot 记录，本轮未重新查询 CI。
- `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python -B -m unittest test_golden_contracts`：66 tests，0.369s，OK，exit 0。
- `python -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts`：99 tests，40.602s，OK，exit 0。
- 编辑前用专用 grep 执行与 `rg -n smoke_note sbtd-runtime/tests tests` 等价的检索，零命中；无需改测试文本断言。仓外一次性 Python 检查器使用 `json.loads` 加载 capability-matrix.json 成功，除 smoke_note 外与本轮基线完全相同；双语 CHANGELOG 与本轮基线逐字节内容一致。
- 索引调用仓库 `TaskStore._index_candidate(records, records)` 重新生成候选，与 `ai/tasks/index.md` 逐字节一致，输出 `INDEX_GENERATED_BYTE_IDENTICAL unchanged`，保持文件不变。TaskStore／TaskDocument 能读取带引号 mode_note、strict 模式与一致事件链；四条历史事件的 at/from/to 与本轮基线一致，输出 `HISTORICAL_AT_FROM_TO_UNCHANGED 4`。
- 新增行检查覆盖 `git diff` 与 `git diff origin/main`：本机路径零命中、错误决定分钟零命中、五类旧归属措辞零命中、过期 CI／错误 SHA 零命中；输出两组 `LOCAL_PATHS 0`、`WRONG_DECISION_TIME 0`、`STALE_ATTRIBUTIONS 0`、`STALE_CI_SHA 0` 与 `RECORD_CHECKS_OK`。task 全文也无错误决定分钟。
- 第 3 轮模型统计由 bash 调用 Python，选取与当前仓库 cwd 对应的 omp 会话目录内最新 JSONL，并核对 session header cwd 一致；按 assistant/model、model_usage 的 provider/model/purpose 及 toolCall 名称分别计数，结果见本任务模型记录。
- 合并顺序由 Lord 定为 #208 先、#209 后；本轮修复由 executor 先在本地提交，待 #208 合入后 rebase 到 main、合并 rc.5 CHANGELOG 条目、重新生成 index 后再推送。本 bot 仅交付文件；新 SHA 仍待 Reviewy 复审相对 c419ac8 的增量与 CI 13/13。
- 验证边界：rtk: not-needed（编排方指定原生命令）；BDD: skipped（本轮无行为或场景改动）；Cross-repo context／API Contract: not-needed；Mock Strategy: none。未重跑 Linux 全量、runtime 已知失败、宿主冒烟、lint、构建、Web／Mobile 或发布验证：仅修订措辞与记录，无生产代码变更。Final Test Report／Run Summary MD: not-needed；本地定向检查结果记于本节，不冒充正式 PR-head、独立 review 或发布证据。

### 第 4 轮：rebase 到 f288729、冲突处理与 Reviewy 修正

- 基准从 `c419ac8`（基于 main `80f1426`）变为 main `f288729`；编排方已将 #209 两个提交（原 `5032425`、`c419ac8`）rebase。第 3 轮修复提交 `434e019` 未推送，本轮由编排方用 `git cherry-pick -n` 取回、与本轮修正合为同一次提交，提交推送在本会话之后处理。第 3 轮小节中的「待 #208 合入后 rebase」安排已由本轮完成，实际顺序为 #208、#211、#210 先合入。
- 冲突与处理（编排方已核实）：第 1 个提交在 `CHANGELOG.md`、`CHANGELOG.zh.md`、`ai/tasks/index.md`、`docs/adr/0001-v2.1.0-rc.1-r1.0-runtime-decisions.md` 冲突；第 2 个提交在两份 CHANGELOG 冲突。其余文件自动合并，编排方比对确认 #209 其余内容与 `c419ac8` 相同，仅增加 main 已有的 #208／#210／#211 改动。
- 编排方仅执行 git 操作：fetch、checkout -b、rebase、对 index 的 checkout --ours、add 冲突文件、rebase --continue、cherry-pick -n；未直接编辑仓库文件。index 由编排方通过 `git checkout --ours` 取回 main 一侧，没有手工编辑；随后冲突处理会话 1 用正式生成器补上 #209 一行，输出 `INDEX_REGEN changed=True rows=81`、`INDEX_PREVIEW_SAME True rows=81`，task/workflow 99 项通过。
- 两个 omp 冲突处理会话均由主模型 `openai-codex/gpt-6-astra`（thinking high）执行。会话 1 将 #209 条目并入 main 唯一的 `## v2.1.0-rc.5 (Unreleased)`／`## v2.1.0-rc.5（未发布）` 下已有的 Changed／变更小节，排在 #211 之后，不保留 `## Unreleased`；Added→Changed→Fixed（新增→变更→修复）均保留，#210／#211／#208 条目文字未改。ADR 0001 §8 原文放在 main 已有 §9 之前，§9 写明编号接在 §8 之后，两节文字均未改。
- 会话 2 将 #209 条目换成与 `c419ac8` 一字不差的定稿，不保留其小写 `(unreleased)` 标题和第二个 Changed 小节。上述冲突处理证据来自编排方记录，不冒充本记录会话重新执行。
- Reviewy 修正 1：CHANGELOG 并入唯一 rc.5 标题及已有 Changed／变更小节，本记录会话只核对、不编辑 CHANGELOG。
- Reviewy 修正 2：第 3 轮次数改为编排方按完整日志复核的终值：astra 17 次、find 内部模型 11 次、工具 39 次，并补齐第 4 轮三会话记录及计数方法。
- Reviewy 修正 3：第 1、3 轮统一 find 内部调用措辞，第 2 轮明确 find 未调用、0 次，表下说明日志归属与主模型分开计数。
- Reviewy 修正 4：Linux 全量时间改为「单分片运行 25 分钟上下（未精确计时）」；第 3 轮正文的执行边界采用同义表述，避免非契约用字混入新增行。
- 本记录会话仅用 edit 编辑 task.md；index 仅由生成器写入且字节不变，保留 `434e019` 已暂存的 ADR 与矩阵内容，不执行 git 写命令、不使用 task 工具或子代理。记录适用于已明确的本地重放分支 `pr209-rebase`，任务原远端分支标识保留。
- 验证对象：本地 `pr209-rebase`，HEAD `a7b60c9262288e7fdf71fa30e9735def74cd0e4c` 加已暂存的第 3 轮内容及本轮记录修改；Evidence Source: developer-local；Source Revision: dirty；Environment Alignment: unverified；Evidence Publication: local-only，不是 CI 证据。

| 命令 | 结果 | 退出码 |
|---|---|---|
| `python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); Path('ai/tasks/index.md').write_bytes(a); print('INDEX_REGEN', 'changed=%s' % (b!=a), 'rows=%d' % len(s._index_rows(r)))"` | `INDEX_REGEN changed=False rows=81` | 0 |
| `python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); print('INDEX_PREVIEW_SAME', Path('ai/tasks/index.md').read_bytes()==a, 'rows=%d' % len(s._index_rows(r)))"` | `INDEX_PREVIEW_SAME True rows=81` | 0 |
| `python3 -B -c "import json; json.load(open('sbtd-runtime/contracts/capability-matrix.json', encoding='utf-8')); print('MATRIX_JSON_OK')"` | `MATRIX_JSON_OK` | 0 |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest test_golden_contracts` | 66 tests，0.418s，OK | 0 |
| `python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts` | 99 tests，49.474s，OK | 0 |
| 专用 grep 检查两份 CHANGELOG 的 rc.5 标题与 rc.5 小节 | 各一个 rc.5 标题、无独立 Unreleased 标题、各一个 Changed／变更小节；Added→Changed→Fixed 均保留 | 不适用（专用工具无进程退出码） |
| `git diff origin/main --stat` | 仅 #209 原有 16 个文件 | 0 |
| `git diff --check` | 无空白错误 | 0 |
| `git diff HEAD --stat` | 仅 task.md、ADR 0001、capability-matrix.json 三个文件；后两者为 `434e019` 已暂存内容 | 0 |
| `git diff HEAD --no-ext-diff --unified=0 -- ai/tasks/v2.1.0-rc.5-host-gate-codex-0167-omp-18188/task.md`，再用专用 grep 检查新增行；专用 grep 核对决定原句及全文错误分钟 | 新增行本机路径及禁用措辞零命中（契约除外）；决定原句逐字存在，全文错误决定分钟零命中 | git 为 0；grep 不适用（专用工具无进程退出码） |

- 生成器与预览均输出既有「旧格式事件，不追溯」提示，未将其记为失败或隐藏。上述命令按表内顺序执行；文本检查完成后，仓外只读计数脚本输出 astra_assistant=11、astra_toolcalls=32、other_assistant={}、model_usage={}，exit 0，再以最后一次 edit 补入计数终值与已完成的文本检查结果，其后不再调用工具。
- 本轮只修订记录，不改生产代码、门禁语义、领域或数据设计，无新增 Book Gate；既有 Gate 不冒充本轮重跑。rtk: not-needed（采用明确的原生命令）；BDD: skipped（无行为或场景改动，既有 spec 不变）；Cross-repo context／API Contract: not-needed；Mock Strategy: none。Linux 全量、runtime 已知失败、宿主冒烟、lint、构建、Web／Mobile 与发布验证未重跑，原因是本轮仅记录修正。Final Test Report／Run Summary MD: not-needed；本地定向结果直接记录本节。
- 最终 SHA 与 CI 由提交推送后另行报告，本文件不预先声称 CI 通过；状态仍为 checking，等待 Reviewy 复审与 CI 13/13，640 说「合入」后由 Lord 合并。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-11T14:48:41.973666+08:00 | planned | in-progress | 开始已授权的宿主门禁契约变更 | 用户 2026-11-11 14:43 群内确认（选择选项 1：以单独契约 PR 换门禁），Lord 记录；基线 main 80f1426；本文件 Book Gate Plan |
| 2026-11-11T14:58:06.921787+08:00 | in-progress | checking | 契约与文档修改完成，聚焦门禁验证通过；保留本地套件失败，等待独立 review 与 CI | 本任务验证证据：四版本分类与 4 项聚焦测试通过；runtime 458 项有 2 个范围外失败；Linux 全量套件运行中，结果回填本节 |
| 2026-11-11T15:14:15.719037+08:00 | checking | in-progress | 编排方整理补齐 CHANGELOG 标题、strict 说明、模型记录与验证证据的要求 | 用户 2026-11-11 15:10 群内确认（rc.5 全程 strict、每个 PR 自带 CHANGELOG、主模型 astra），Lord 记录；仅修订双语 CHANGELOG 与本任务记录，不 commit/push、不用 task 工具或子代理 |
| 2026-11-11T15:18:19.441119+08:00 | in-progress | checking | 已补齐 rc.5 CHANGELOG 标题、strict 说明、模型记录与验证证据，等待 Reviewy 与 CI | 本轮 golden 66 tests OK；task/workflow 99 tests OK；双语结构与新增行路径检查通过；完整 SHA 由最终 PR 审查与 CI 13/13 绑定；640 说合入后由 Lord 合并，本 bot 不合并 |
| 2026-11-11T15:43:27.014335+08:00 | checking | in-progress | Reviewy 于 c419ac8c98d1e98ee46578629c2b8adcd70643c7 判 NOT CLEAN，措辞／记录问题：用户归属、决定时间格式、第 2 轮模型次数、过期 CI／SHA | PR #209 Reviewy 意见；编排方整理四项修复要求；保持 strict，仅修改文件，不 commit/push、不使用子代理 |
| 2026-11-11T15:48:14.639504+08:00 | in-progress | checking | 已修复四项，待 Reviewy 复审新 SHA 相对 c419ac8 的增量与 CI 13/13 | 第 3 轮验证证据：golden 66 tests OK；task/workflow 99 tests OK；JSON 加载、索引逐字节一致、历史事件 at/from/to 不变与新增行检查通过；模型次数来自本轮会话统计；仅改文件，未 commit/push |
| 2026-11-11T19:18:45+08:00 | checking | checking | rebase 到 main f288729（#210 合入）并处理冲突；按 Reviewy 意见修正：CHANGELOG 并入唯一 rc.5 标题、第 3 轮次数改为日志终值、find 措辞统一、时间描述改为未精确计时 | 用户 2026-11-11 群内确认（合入 #210），Lord 记录。注：分钟不可考。第 1 个提交冲突为两份 CHANGELOG、index、ADR 0001，第 2 个提交冲突为两份 CHANGELOG；编排方用 git 将 index 取回 main 后由生成器补行，omp 会话合并 CHANGELOG 条目并将 ADR §8 放在 §9 前；两份 CHANGELOG 各一个 rc.5 标题且 Added→Changed→Fixed 都保留。冲突会话 1：INDEX_REGEN changed=True rows=81、INDEX_PREVIEW_SAME True rows=81、task/workflow 99 项通过；本记录会话：INDEX_REGEN changed=False rows=81、INDEX_PREVIEW_SAME True rows=81、MATRIX_JSON_OK、golden 66 tests OK、task/workflow 99 tests OK，命令 exit 0；相对 origin/main 仅原有 16 文件。Evidence Source: developer-local，非 CI 证据；保持 checking，等待 Reviewy 与新 SHA 的 CI 13/13 |
