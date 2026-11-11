---
schema_version: 1
id: v2.1.0-rc.5-host-gate-codex-0167-omp-18188
workflow_mode: strict
mode_source: user
mode_note: 用户明确要求 strict；只改文件，最终停在 checking 等 review 与 CI
status: "checking"
branch: contract/rc5-host-gate-codex-0167-omp-18188
created_at: '2026-11-11T14:48:27.312232+08:00'
updated_at: "2026-11-11T14:58:06.921787+08:00"
completed_at: null
---
# rc.5 宿主验收门禁契约变更

## 目标与范围

按用户 640 于 2026-11-11 14:43（北京时间）群内选项 1，将门禁换为 codex@0.167.1 + omp@18.18.8。只改契约、相关版本说明、golden 与测试、双语 CHANGELOG 和本任务/index；不改适配器逻辑、ENTRYPOINT、README 或 release notes，不 commit/push/开 PR，不用子代理。

未完整调用 grill-with-docs：用户决定、版本、真实冒烟事实与交付边界均明确，无领域歧义。

## Book Gate Plan

| 方法 | 触发与阶段 | 状态与证据 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，before-dev | not-required；均未触发 |
| book-ddia-data-design | 静态共享契约扩展，before-dev | confirmed；矩阵直接加载，host_capability 只读 acceptance_pins；smoke_history 不参与判定，无存储迁移 |
| book-legacy-change-safety | 弱测试或高风险既有行为，before-dev | not-required；仅换静态 pin，既有 golden 覆盖，解析与存储逻辑不变 |
| book-refactoring-pass | 既有生产文件编辑前 | proceed / normal；no refactor needed，仅 docstring/help 修改 |
| gherkin-bdd | 当前门禁分类可观察，before-dev/check | traceable；沿用中文 Markdown spec 与英文关键字；完成门、非门禁不影响指标、换针后三类场景分别对应既有 gate/golden 测试与新增四版本测试 |
| project-validation | 契约与测试改动后 | planned；runtime、Linux 全量、四版本分类与路径检查 |
| book-release-readiness | 运行时/部署/发布风险，验证后 | not-required；不部署、不发布，不改适配器执行逻辑 |
| 独立 review 与 CI | 契约 PR 检查 | pending；用户要求留在 checking，本轮不使用子代理 |
| ponytail-review / Code Readability Review | 修改后自检 | 无新增抽象或依赖；一个四版本参数表覆盖新旧分类，无逻辑重构；不代替独立 review |

## 设计与保留行为

- `contract_eval.capability_matrix()` 直接加载 JSON，`host_capability()` 只遍历 `acceptance_pins`；全仓消费者检索未发现矩阵专用 schema 或拒绝额外字段的校验。`event.schema.json` 仅校验观察事件，不校验矩阵。新增可选 `smoke_history` 与数据字典说明，不改 schema_version、release 或评估器。
- 当前 `smoke` 与历史 `smoke_history` 都按宿主保存 status、host_version、smoked_at、evidence。旧 omp 的 pass 保留，但不影响当前旧版本的 unsupported 分类；兜底完成门仍 ≥1，parser fixture 不算真实证据。
- `evaluate()` 对 accepted 事件的 host 调用 `host_capability()`，capability 与指标计算分开。golden 更新 8 条合成事件的版本：`evt_loaded`、`evt_inv1_start`、`evt_inv1_host`、`evt_inv1_finish`、`evt_inv1_conflict`、`evt_inv2_start`、`evt_inv2_finish`、`evt_gap`。`expected.json` 只断言指标、分子分母和来源事件，不含宿主版本，故保持不变。golden 不是实测证据，不改事件日期、ID 或指标数值。
- OMP 历史会话形状夹具不依赖门禁，保持 `test_omp_adapter.py` 原样。适配器解析、lease、开关、入库、去重与重放逻辑均不改。
- TaskStore 源码提供 Python library API，没有 CLI：本轮用 `create(..., mode="strict", confirmed=True)` 创建任务并自动更新 index/受 ignore 保护的 active 引用，用 `transition()` 记录真实状态事件；不手改状态时间。独立克隆分支与授权分支一致，任务路径不存在冲突，既有 ignore 保护已核对，不改 ignore。

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

ENTRYPOINT.md 监控基线不在范围；README、release notes、旧 ai/tasks 与旧 CHANGELOG 条目均不改。新增双语 Unreleased 各一条 Changed/变更，逐条同义。

## 冒烟证据（来源：云主机实测）

本节只记录用户提供的执行事实，不声称本轮编辑重新运行宿主。

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
| 文件编辑 | omp 18.18.8；openai-codex/gpt-6-astra（thinking high） | 待 PR 报告补记；工具限 read/write/edit/bash/grep/glob/find/todo，无子代理 |
| codex 冒烟 | codex 0.167.1；模型未知 | 1 turn |
| omp 冒烟 | omp 18.18.8；openai-codex/gpt-6-astra high | 2 次 |

## 验证证据

- 验证对象：分支 `contract/rc5-host-gate-codex-0167-omp-18188`，基线 SHA `80f14263e7d8bc6ae84f04ba94218e4857fc8b8f` 加本次未提交文件改动；不是该旧 SHA 的精确提交验证。Evidence Source: developer-local；Source Revision: dirty；Evidence Publication: local-only。
- Red：`PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python -B -m unittest test_golden_contracts.CapabilityMatrixTests.test_gate_replacement_unpins_historical_versions`，1 个测试、4 个 subtest 均因旧矩阵新旧分类相反而失败（exit 1），证明断言覆盖真实门禁行为，不是 parser fixture 冒充宿主实测。
- `PYTHONPATH=sbtd-runtime python -B -c` 调用 `capability_matrix()` / `host_capability()`：codex 0.167.1 与 omp 18.18.8 → pinned，codex 0.163.0 与 omp 18.11.1 → unsupported；exit 0。同次检查当前 smoke 两者 pass、历史 codex unsupported / omp pass 均符合预期。
- `python -B sbtd-runtime/codex_adapter.py --help`：exit 0，实际 CLI 显示 `codex-cli 0.167.1`。
- `python -B -m ruff check sbtd-runtime/codex_adapter.py sbtd-runtime/omp_adapter.py sbtd-runtime/tests/test_golden_contracts.py sbtd-runtime/tests/test_codex_adapter.py`：exit 1，两项既有未修改位置告警：OMP lease 的 subprocess.run 缺显式 check（PLW1510）；golden 测试原 import 块排序（I001）。不改适配器逻辑、不夹带无关格式修复；lint 不报通过。
- 路径检查：对 tracked diff 新增行使用同一禁止路径正则，零命中；新 task、矩阵、host-adapters 与 omp_adapter 全文件同样零命中。原 ADR、旧 CHANGELOG、旧文档/测试中未修改的路径文本不重写，按用户“git diff 只看新增行”界定本次新增内容。旧 codex 矩阵证据已替换为仓内旧 task 引用。
- BDD: traceable；`sbtd-runtime/spec/r1.0-contract-scenarios.md` 为中文场景/英文关键字，`r1.2b-host-adapter-scenarios.md` 仅当前 smoke 说明换针；无新 .feature。Cross-repo context: not-needed；API Contract: not-needed（无 HTTP 契约改动）；Mock Strategy: none（门禁分类调用真实评估器）。rtk: skipped-for-report（原生测试与报告）；不运行 UI/移动端或发布验证，因为本轮不改这些表面。
- Runtime：`PYTHONPATH=sbtd-runtime python -B -m unittest discover -s sbtd-runtime/tests`，458 tests，188.329s，2 failures、10 skipped，exit 1。失败为 `RuntimePerfSmokeTests.test_cli_preserves_dataset_and_reports_unmeasured_boundaries`（performance CLI execution=failed）与 `NormalizeScopeTests.test_iana_queries_and_dst_work_without_system_timezone_data`（缺 Python tzdata，Asia/Tokyo 无可用时区数据）。全部 gate/golden 与适配器测试未报失败。Playwright 未安装，renderer 相关跳过/既有 stub 不视为真实浏览器验证；未安装依赖或修改范围外实现，不伪称全绿。
- 聚焦 Green：`PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python -B -m unittest test_golden_contracts.CapabilityMatrixTests test_golden_contracts.GoldenContractTests.test_unsupported_host_does_not_unsupport_the_metric test_golden_contracts.GoldenContractTests.test_golden_oracle_matches_every_metric`，4 tests，0.003s，OK，exit 0；覆盖新旧针、兜底规则、非门禁不取消指标、全指标 golden oracle。
- 性能失败诊断：`python -B sbtd-runtime/tests/runtime_perf.py --events 101 --samples 2 --seed-seconds 60 --output "$PERF_DIAGNOSTIC_OUTPUT"`（变量代指本轮仓外临时目录，实际命令使用该目录），exit 1；原生 `runtime-perf-101-contract_rc5-host-gate-codex-0167-omp-18188-20261111T065548863178Z.json` 与同 stem 中文 `.md` 已保留。报告 error 为 `AssertionError: `、html_panel_count=12，而 panel manifest 为 13；`runtime_perf.py:476-479` 按精确字符串 `class="panel"` 计数，导出样本 overview 实为 `class="panel panel-kpi"`。这是范围外 HTML smoke 计数断言问题，不是新门禁分类失败；保留失败，不改 UI、导出或性能测试。该诊断没有完成 CSV／四格式性能验证。
- 其余测试结果在实际运行完成后记录。本轮不提交、不推送、不创建 PR；独立 review 与 CI 仍待执行，最终状态按要求停在 checking。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-11T14:48:41.973666+08:00 | planned | in-progress | 开始已授权的宿主门禁契约变更 | 用户群内选项 1；基线 main 80f1426；本文件 Book Gate Plan |
| 2026-11-11T14:58:06.921787+08:00 | in-progress | checking | 契约与文档修改完成，聚焦门禁验证通过；保留本地套件失败，等待独立 review 与 CI | 本任务验证证据：四版本分类与 4 项聚焦测试通过；runtime 458 项有 2 个范围外失败；Linux 全量套件运行中，结果回填本节 |
