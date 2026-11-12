---
schema_version: 1
id: v2.2.0-rc.1-host-gate-omp-18190
workflow_mode: strict
mode_source: user
mode_note: 本轮任务指令明确全程 strict；640 于 2026-11-12 在 640-skills 群内确认门禁变更（选甲：发布 v2.2.0-rc.1
  预发布）
status: "checking"
branch: contract/v2.2.0-rc.1-host-gate-omp-18190
created_at: '2026-11-12T19:32:36.897157+08:00'
updated_at: "2026-11-12T19:57:23.857704+08:00"
completed_at: null
---
# v2.2.0-rc.1 宿主验收门禁契约变更

## 目标与范围

640 于 2026-11-12 在 640-skills 群内确认本次门禁变更（选甲：发布 v2.2.0-rc.1 预发布）；据此将宿主验收门禁从 codex@0.167.1 + omp@18.18.8 换为 codex@0.167.1 + omp@18.19.0（codex 不变，只改 omp）。只改契约、相关版本说明、golden 与测试、双语 CHANGELOG 和本任务/index；不改适配器逻辑、ENTRYPOINT、README 或 release notes，不 commit/push/开 PR，不用子代理。

未完整调用 grill-with-docs：换针决定（见上）、版本、真实冒烟事实与交付边界均明确，无领域歧义。

## strict mode 落实方式

- 任务文件在开工前经 TaskStore library API 创建并落盘；阶段转换用 `transition()` 记录真实状态事件，不手改状态时间。
- 验证证据（命令、结果、失败归因）写入本文件；Book Gate Plan 已列。
- 冒烟证据来自真实宿主运行（云主机实测），不用 parser fixture 作为实测证据；本轮不声称重新运行宿主，冒烟数字照实记录。
- 状态停在 checking，等待独立 review 与 CI；本 bot 不合并。

## Book Gate Plan

| 方法 | 触发与阶段 | 状态与证据 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，before-dev | not-required；均未触发 |
| book-ddia-data-design | 静态共享契约扩展，before-dev | confirmed；矩阵直接加载，host_capability 只读 acceptance_pins；smoke_history 不参与判定，其 omp 条目由单对象扩为按时间倒序数组以同时保留 18.18.8 与 18.11.1 两条历史记录，全仓 Python 检索无代码消费该字段，无存储迁移 |
| book-legacy-change-safety | 弱测试或高风险既有行为，before-dev | not-required；仅换静态 pin，既有 golden 覆盖，解析与存储逻辑不变 |
| book-refactoring-pass | 既有生产文件编辑前 | proceed / normal；仅 omp_adapter docstring 修改，无生产逻辑改动 |
| gherkin-bdd | 当前门禁分类可观察，before-dev/check | traceable；沿用中文 Markdown spec 与英文关键字；换针场景更新为 omp 18.19.0 pinned、18.18.8 归入 unsupported，对应既有 gate/golden 测试与五版本参数化断言 |
| project-validation | 契约与测试改动后 | 已执行聚焦门禁、任务/workflow 与索引验证，证据见下；全量以 CI 为准 |
| book-release-readiness | 运行时/部署/发布风险，验证后 | not-required；不部署、不发布，不改适配器执行逻辑 |
| 独立 review 与 CI | 契约 PR 检查 | pending；状态停在 checking；本任务不使用子代理 |
| ponytail-review / Code Readability Review | 修改后自检 | 无新增抽象或依赖；参数表仅加一行旧版本 unsupported，无逻辑重构；不代替独立 review |

## 设计与保留行为

- `contract_eval.capability_matrix()` 直接加载 JSON，`host_capability()` 只遍历 `acceptance_pins`；`smoke_history` 不参与判定，全仓 Python 检索无消费代码。`event.schema.json` 只校验观察事件，不校验矩阵。schema_version 与 release（仍为 v2.1.0，发布身份对齐属发布时动作）不变。
- `smoke_history.omp` 由单对象改为按时间倒序的数组 [18.18.8 记录, 18.11.1 记录]：照上一轮「旧冒烟记录移入 smoke_history」的做法，同时不丢弃既有 18.11.1 历史证据。
- golden 更新 3 条合成事件的 omp 版本：`evt_inv2_start`、`evt_inv2_finish`、`evt_gap`；codex 事件保持 0.167.1。`expected.json` 只断言指标、分子分母和来源事件，不含宿主版本，保持不变。golden 不是实测证据，不改事件日期、ID 或指标数值。
- omp 历史会话形状夹具不依赖门禁，`test_omp_adapter.py` 保持原样。适配器解析、lease、开关、入库、去重与重放逻辑均不改。
- codex 侧完全不变：acceptance pin、smoke.codex 记录、codex_adapter.py、现场 smoke 指令均保持 0.167.1。

## 旧版本 grep 逐条决定表

全仓扫描 `git grep -n "18.18.8"`，下列行号为编辑前基线。复扫残留只属于历史记录、换针说明或旧版本 unsupported 断言。

| 文件（仓库相对路径） | 基线行 | 原内容摘要 | 决定 | 理由 |
|---|---|---|---|---|
| CHANGELOG.md | 49 | rc.5 已发布条目：门禁换为 codex@0.167.1 + omp@18.18.8 | 保留为历史 | 已发布版本条目不改写 |
| CHANGELOG.zh.md | 49 | 同上中文条目 | 保留为历史 | 与英文条目对应 |
| ai/tasks/v2.1.0-rc.5-dashboard-401-repair-impl/task.md | 56 | 旧任务引用当时门禁 | 保留为历史 | 旧任务记录不重写 |
| ai/tasks/v2.1.0-rc.5-host-gate-codex-0167-omp-18188/task.md | 17 | 旧任务目标与范围 | 保留为历史 | 旧任务记录不重写 |
| 同上 | 82 | 旧决定表行 | 保留为历史 | 同上 |
| 同上 | 138 | 旧 omp 冒烟节标题 | 保留为历史 | 同上 |
| 同上 | 140 | 旧冒烟执行记录 | 保留为历史 | 同上 |
| 同上 | 142 | 旧会话形状记录 | 保留为历史 | 同上 |
| 同上 | 143 | 旧回执记录 | 保留为历史 | 同上 |
| 同上 | 145 | 旧矩阵分类说明 | 保留为历史 | 同上 |
| 同上 | 152 | 旧模型记录 | 保留为历史 | 同上 |
| 同上 | 159 | 旧冒烟模型记录 | 保留为历史 | 同上 |
| 同上 | 170 | 旧验证证据 | 保留为历史 | 同上 |
| docs/adr/0001-v2.1.0-rc.1-r1.0-runtime-decisions.md | 182 | §8 标题 | 保留为历史 | ADR 历史决策不改写 |
| 同上 | 186 | §8 决定正文 | 保留为历史 | 同上 |
| 同上 | 191 | §8 omp 版本事实 | 保留为历史 | 同上 |
| 同上 | 201 | §8 omp 冒烟证据 | 保留为历史 | 同上 |
| 同上 | 213 | §9 对 §8 的引用 | 保留为历史 | 同上 |
| sbtd-runtime/contracts/capability-matrix.json | 11 | acceptance pin omp 18.18.8 | 改为 18.19.0 | 当前门禁引用 |
| 同上 | 21 | completion_gate hosts omp@18.18.8 | 改为 omp@18.19.0 | 当前门禁引用 |
| 同上 | 34 | smoke.omp host_version omp/18.18.8 | 改为 omp/18.19.0（新 smoke 记录） | 当前门禁引用 |
| 同上 | 36 | smoke.omp evidence（18.18.8 冒烟证据） | 替换为 18.19.0 新证据；旧记录整段移入 smoke_history.omp 数组首位 | 照上一轮做法，历史不入当前 smoke |
| 同上 | 59 | smoke_note（rc.5 换针说明） | 更新为本次换针说明 | 当前门禁说明 |
| sbtd-runtime/docs/host-adapters.md | 23 | omp 适配器节标题（当前门禁 omp@18.18.8） | 改为 omp@18.19.0，18.18.8 列入历史实测 | 当前门禁引用 |
| 同上 | 25 | 字段形状来源说明 | 补充 18.19.0 于 2026-11-12 实测 | 当前门禁引用 |
| 同上 | 48 | 18.18.8 smoke 证据节标题 | 替换为 18.19.0 证据节 | 当前门禁引用 |
| 同上 | 50 | 18.18.8 冒烟执行记录 | 替换为 18.19.0 记录 | 当前门禁引用 |
| 同上 | 54 | 18.18.8 会话形状 | 替换为 18.19.0 会话形状 | 当前门禁引用 |
| 同上 | 56 | 18.18.8 回执与重放 | 替换为 18.19.0 回执 | 当前门禁引用 |
| 同上 | 58 | 旧矩阵分类说明 | 更新为 18.19.0/18.18.8 分类反转说明 | 当前门禁引用 |
| 同上 | 78 | capability matrix 节当前针与 smoke_history 说明 | 更新当前针为 omp@18.19.0，smoke_history 增列 omp@18.18.8 | 当前门禁引用 |
| sbtd-runtime/docs/install-and-use.md | 125 | 当前门禁双宿主说明 | 改为 codex@0.167.1 + omp@18.19.0 及各自实测日期 | 当前门禁引用 |
| sbtd-runtime/golden/dataset.json | 1812 | evt_inv2_start host_version | 改为 18.19.0 | golden 当前 omp pin 样本 |
| 同上 | 1871 | evt_inv2_finish host_version | 改为 18.19.0 | 同上 |
| 同上 | 2922 | evt_gap host_version | 改为 18.19.0 | golden 当前 omp 采集缺口 |
| sbtd-runtime/omp_adapter.py | 9 | docstring 实测记录 | 补充 18.19.0 于 2026-11-12 实测，保留 18.18.8 历史 | 当前实测说明 |
| sbtd-runtime/spec/r1.0-contract-scenarios.md | 103 | 非门禁宿主场景当前针 | 改为 omp 18.19.0 | 当前门禁引用 |
| 同上 | 109 | 换针场景 Given 当前针 | 改为 omp 18.19.0 | 当前门禁引用 |
| 同上 | 111 | 换针场景 Then pinned | 改为 omp 18.19.0 pinned，And 增列 omp 18.18.8 unsupported | 当前门禁引用 |
| 同上 | 129 | 兜底完成门场景宿主 | 改为 omp@18.19.0 | 当前门禁引用 |
| sbtd-runtime/tests/test_golden_contracts.py | 105 | 完成门集合断言 | 改为 omp@18.19.0 | 当前门禁引用 |
| 同上 | 119 | 参数化 omp pinned | 改为 18.19.0 pinned，新增 18.18.8 unsupported | 参数化：新针 pinned、旧针 unsupported |
| 同上 | 304 | golden capability omp pinned 断言 | 改为 omp@18.19.0 | 当前门禁引用 |

CI 与安装脚本检查：`.github/`、`install.sh`、`install.ps1` 已检查，无 omp 版本固定命中。install 脚本中 `omp` 仅为 oh-my-pi 平台别名，无版本字符串；`.github/workflows/validation.yml` 无 omp 版本引用；`.github/test-weights.json` 仅含测试名 `test_omp_version_monitoring_contract`，无版本固定。

## 冒烟证据（来源：云主机实测）

冒烟在宿主上真实执行，本任务只照实记录数字，不声称本轮编辑重新运行宿主；不写本机路径与任何密钥片段。

### omp 18.19.0 — pass

- `omp --version` → `omp/18.19.0`；2026-11-12 18:51:03–18:51:17 +08:00；退出码 0、stdout `done`；模型 kimi-code/k3:max；强制一次 read 工具调用。
- 会话文件 12 行，sha256 `c5f79ec94f0cedcdbde4eabb472124bd7ea030e5e9457a56df5abeea012116a0`；第 1 行 type=title 且无 id（18.19.0 新出现）；第 2 行 session 头 version 3；toolResult toolName=read、isError=false。
- `omp_adapter.py`（main `a70f270`）回执：records_read=12、records_skipped=8、events_emitted=2、accepted=2、duplicate=0、conflict=0、rejected=0、dropped=[]；再次导入 accepted=0、duplicate=2。
- 改动前矩阵分类：18.19.0 → unsupported、18.18.8 → pinned；本次换针后两者分类反转，不改变实测事实。

### codex 0.167.1 — pass（沿用 2026-11-11 实测）

- 本轮 codex 针不变，不重跑；证据保留于 `smoke.codex` 与 `ai/tasks/v2.1.0-rc.5-host-gate-codex-0167-omp-18188/task.md`。

## 本任务模型记录

- 主 agent 用 k3:max，密钥从环境变量 KIMI_API_KEY 读取。
- 模型调用统计（只用了 kimi-code/k3:max，没有用其他模型）：

| 轮次 | 用途 | 模型 | 回复次数 | 工具调用次数 | 工具报错次数 | 结果 |
|---|---|---|---|---|---|---|
| 第 1 轮 | 换针编辑 | kimi-code/k3:max | 96 | 110 | 2 | 中止，无仓库改动 |
| 第 2 轮 | 换针编辑、验证、写 task.md | kimi-code/k3:max | 26 | 49 | 3 | 正常结束 |
| 第 3 轮 | 补本节模型记录 | kimi-code/k3:max | 5 | 4 | 0 | 正常结束 |

- 第 1 轮中止原因（以会话日志为准，只有这一个原因）：同一个工具调用反复出错，陷入循环。证据：2026-11-12 18:59:52 起，模型反复调用任务清单工具 todo，参数为 init 但缺少清单，每次报错原文为「Errors: Missing list for init operation」；到 19:27:15 共调用 85 次，omp 自带的循环检测提示过「连续 71 次参数完全相同」，模型仍未停止；19:27 人工结束该轮，会话日志最后写入 19:27:20。第 1 轮没有留下任何仓库改动。第 2 轮起不再给模型 todo 工具。
- omp 18.19.0 冒烟：模型 kimi-code/k3:max（实测事实）。
- codex 0.167.1 冒烟：沿用 2026-11-11 实测，模型未知（JSONL 未记录），本轮未重跑。

## 验证证据

- 验证对象：分支 `contract/v2.2.0-rc.1-host-gate-omp-18190`，基线 main `a70f270` 加本轮未提交文件改动；不是最终 PR SHA 的 CI 证明。Evidence Source: developer-local；Source Revision: dirty；Evidence Publication: local-only。
- 基线核对（改动前）：`PYTHONPATH=sbtd-runtime python3 -B -c` 调 `capability_matrix()` / `host_capability()`：omp 18.19.0 → unsupported、omp 18.18.8 → pinned、codex 0.167.1 → pinned；exit 0，与冒烟事实记录一致。
- `cd sbtd-runtime && python3 -m pytest -q tests/test_golden_contracts.py`：本环境未安装 pytest（No module named pytest），按项目既有方式以 unittest 运行同一文件替代，不伪造 pytest 结果。
- `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest test_golden_contracts`：66 tests，0.413s，OK，exit 0；覆盖完成门集合、五版本参数化分类（18.19.0 pinned，18.18.8/18.11.1/0.163.0 unsupported）、非门禁不取消指标、全指标 golden oracle。
- 改动后分类核对：`host_capability()` → omp 18.19.0 pinned、omp 18.18.8 unsupported、codex 0.167.1 pinned、codex 0.163.0 unsupported、omp 18.11.1 unsupported；smoke.omp=pass omp/18.19.0、smoke.codex=pass codex-cli 0.167.1、smoke_history.omp=[omp/18.18.8, omp/18.11.1]、smoke_history.codex=codex-cli 0.163.0；exit 0。
- `python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts`：99 tests，49.615s，OK，exit 0。
- 索引检查：TaskStore 只读重新生成候选，`INDEX_PREVIEW_SAME True rows=88`，与 `ai/tasks/index.md` 逐字节一致；exit 0。
- 矩阵 JSON 加载：`json.loads` 成功，`MATRIX_JSON_OK`；exit 0。
- 复扫 `git grep -n "18.18.8"`：32 处残留，全部属于决定表标「保留为历史」的条目或换针记录本身——CHANGELOG.md 2（rc.5 已发布条目、新 rc.1 条目的换针来源版本）、CHANGELOG.zh.md 2（对应中文）、rc.5 dashboard 旧任务 1、rc.5 host-gate 旧任务 10、ADR 0001 §8 共 5、capability-matrix.json 3（smoke_history.omp 历史记录 2 处与 smoke_note 换针说明 1 处）、host-adapters.md 6（18.18.8 历史 smoke 节与历史标识）、omp_adapter.py 1（docstring 历史实测记录）、spec 1（18.18.8 unsupported 断言）、test_golden_contracts.py 1（18.18.8 unsupported 参数化断言）。当前门禁引用（acceptance_pins、completion_gate、smoke.omp、dataset、spec 当前针、测试 pinned 断言）已全部为 18.19.0。
- 验证边界：rtk: not-needed（原生命令）；BDD: traceable（spec 场景同步更新，无新 .feature）；Cross-repo context／API Contract: not-needed；Mock Strategy: none（门禁分类调用真实评估器）。未重跑 Linux 全量套件、runtime discover 全量、lint、构建、Web／Mobile 与发布验证：本轮仅契约/文档/golden/测试换版本针，全量以 CI 为准。Final Test Report／Run Summary MD: not-needed，本地定向结果记于本节，不冒充 CI 或独立 review。
- 最终 SHA 与 CI 由提交推送后另行报告，本文件不预先声称 CI 通过；状态停在 checking，等待独立 review 与 CI。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-12T19:32:54.706488+08:00 | planned | in-progress | 开始已授权的宿主门禁契约变更（omp 18.18.8 → 18.19.0，codex 0.167.1 不变） | 640 于 2026-11-12 在 640-skills 群内确认（选甲：发布 v2.2.0-rc.1 预发布）；基线 main a70f270；改动前 host_capability 实测：omp 18.19.0 → unsupported、omp 18.18.8 → pinned、codex 0.167.1 → pinned |
| 2026-11-12T19:57:23.857704+08:00 | in-progress | checking | 契约、文档、golden、测试与双语 CHANGELOG 修改完成，聚焦门禁与索引验证通过，等待独立 review 与 CI | test_golden_contracts 66 tests OK（pytest 未安装，按项目既有 unittest 运行同一文件）；tests.test_sbtd_task_state + tests.test_workflow_contracts 99 tests OK；host_capability：omp 18.19.0→pinned、18.18.8→unsupported、codex 0.167.1→pinned；INDEX_PREVIEW_SAME True rows=88；MATRIX_JSON_OK；复扫 18.18.8 余 32 处全部为历史记录或换针说明；本任务未 commit/push |
