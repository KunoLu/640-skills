---
schema_version: 1
id: v2.2.0-rc.2-search-tools
workflow_mode: strict
mode_source: user
mode_note: 'rc.2 PRD；用户已确认在 #225 合入、主线 CI 全绿、清理任务 3 分支后启动任务 4。'
status: "done"
branch: test/v2.2.0-rc.2-search-tools
created_at: '2026-11-24T23:22:36.394772+08:00'
updated_at: "2026-11-25T10:03:01.866351+08:00"
completed_at: "2026-11-25T10:03:01.866351+08:00"
"blocked_reason": null
---
# 任务 4：替代检索能力

基线：任务 3 的 PR [#225](https://github.com/KunoLu/640-skills/pull/225) 已由用户授权 admin squash。通过外审的分支 head `9ac6ac21b619411bf9ff7106d10f8399f2bf67b8` 对应 [PR CI](https://github.com/KunoLu/640-skills/actions/runs/45382265087)；新 main 为 `f74eea505c88945f812b370f4349d901daf99e01`，对应独立的 [main CI](https://github.com/KunoLu/640-skills/actions/runs/45420223638)。本任务不是 Graft 退役、全局同步或发布授权。

## 固定输入与范围

Codex ast-grep MCP 的官方仓库为 `https://github.com/ast-grep/ast-grep-mcp`，本任务锁定完整提交 `51d5a23f025c73c02032a98748dc06942548c5e1`。执行时核对分离检出的 HEAD；后续引用固定 SHA，而非 main 或浮动版本。`main.py` 声明四个只读工具：`find_code`、`find_code_by_rule`、`dump_syntax_tree`、`test_match_code_rule`。静态声明不等于已装载、获批准或成功执行。隔离 ast-grep CLI 资产选用官方 `0.51.3` Darwin arm64，压缩包 SHA-256 `7954eab1e2803d1485f263377be7f359db6d3915312b5d773cd575eb009330b1`。

## 验收与停止条件

1. 新建任务私有环境、缓存及合成项目。先核验固定服务的 stdio 握手和四种查询的实际语义，保留结果和拒绝非放行工具的负例。直接 MCP 协议不能代替宿主审批。
2. Codex `0.171.0` 只暴露这四个只读工具，逐项观测原生审批与调用；OMP `19.1.0` 核对对应原生检索。既有任务凭据不复制，不开启 eval 或共享 daemon，不改变真实全局信任。需要人工认证或无法证明域隔离时暂停。
3. 分开验证 Onboard 的拒绝无写入、获准前备份、重复运行幂等和回退。仅处置任务私有夹具；真实宿主写入另行授权。保留 Graft，不提前进入任务 5。
4. 真实场景有具体消费链失败时才修改项目；工具列表、安装成功和模拟回执均不能代替端到端验收。未通过的条件单列为 pending 或 blocked，不报完成。

## 工程与证据

strict。未完整调用 grill-with-docs：PRD 任务 4 已确定四项能力、审批、写入授权及恢复边界。当前仅开工，未承诺任何宿主通过。Book Gate Plan：领域建模不适用；若触及安装／配置或持久状态，在生产编辑前执行 Legacy Safety、Refactoring 与适用 DDIA；已有场景与红绿证据先行，之后 project-validation 和适用的 Release Readiness。不得在本仓库写 `.feature`。本地验收后执行内置 `/review`，独审与 CI 绑定精确 SHA。

脱敏原生报告及同 stem 中文汇总放在本任务 ignored `reports/`。当前实现主会话沿用 Astra，模型调用次数未知。不要读取/复制凭据、导入活动会话或把临时安装发布为全局配置。

## 隔离宿主与配置证据

- **Codex 允许列表负例：**固定服务 `tools/list` 返回四项。本次 thread 通过启动参数只放行其中三项，`mcpServerStatus/list` 的有效清单恰为三项。请求使用被排除的 `test_match_code_rule` 后，turn 正常结束，既没有该工具的审批或执行事件，也没有 `tools/call` 到达连接另一端。服务本身仍提供该工具，不把不存在的工具名或模型自述单独当成负例证据。未写入持久信任或变更夹具。
- **Onboard 拒绝路径：**生产 `check_language_tooling` 在专用合成 HOME 中发现 OMP 的 `enable-ast-grep` 待写项，`apply_language_tooling(..., confirmed=False)` 返回 `needs-confirmation`、`writes=[]`。逐文件核对内容、权限、修改时间，无变化、无备份。这个已有接口用于 OMP；它不是 Codex ast-grep MCP 的配置安装器。`confirmed=True`、备份及幂等不能从此负例推定。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-24T23:23:06.770772+08:00 | planned | in-progress | 当前 Astra 原会话：开始任务 4，验证固定检索工具的私有 stdio 与按宿主审批。 | main f74eea505c88945f812b370f4349d901daf99e01 对应 CI 45420223638 的 13 个作业均成功。首轮 macOS runner 未分配，原回执保留；只重排 runtime-e2e-macos。任务 3 同名开发分支本地／远端均已删除。新检索工具源码精确 SHA 51d5a23f025c73c02032a98748dc06942548c5e1，私有 TEMP /Users/lusonglin/TEMP/640-skills-rc2-task4.3vv7gXpM，未复制凭据或接线。 |
| 2026-11-24T23:27:36.808864+08:00 | in-progress | blocked | 当前 Astra 原会话：固定服务的直接 stdio 预检已通过；新隔离 CODEX_HOME 未登录，按认证停止门关闭循环。 | 上游 51d5a23f025c73c02032a98748dc06942548c5e1、ast-grep 0.51.3。四项真实只读工具均返回预期结果，未知工具被拒，夹具字节未变，server exit 0。Codex CLI 0.171.0 login status 返回 Not logged in/exit 1。直接 stdio 非宿主审批；OMP 原生对照及 Onboard 写入授权、备份、幂等待验。未发起 OAuth、未更改全局配置，详见 reports/preflight.json 和 preflight.md。 |
| 2026-11-24T23:36:12.833016+08:00 | blocked | in-progress | 当前 Astra 会话：用户授权的任务 4 隔离 Codex 官方登录成功，解除认证阻断。 | 同一任务 4 CODEX_HOME 的 codex login 和 login status 均 exit 0；脱敏回执 reports/codex-login-1.json。未执行逐工具审批、OMP 登录或全局配置写入，未重启 /loop。 |
| 2026-11-24T23:44:29.511704+08:00 | in-progress | in-progress | 当前 Astra 原会话：开始 隔离 Codex 四工具逐项审批与未放行负例；独立核对 Onboard 拒绝分支 | {"changed_files": [], "evidence_files": [], "sync_files": {}, "validation": ""} |
| 2026-11-25T00:15:56.212781+08:00 | in-progress | blocked | 当前 Astra 原会话：任务 4 的 Codex 逐项本地验收到点，循环已关闭；OMP 私有域无可用固定模型，等待本域官方认证授权。未接线真实配置。 | Codex 四项各有一次匹配的原生单次批准、宿主完成和真实服务语义匹配，夹具未改；另测四选三负例零转发。额外未知工具直调的控制器失败（exit 1），不作通过证据。OMP 独立域 models openai-codex --json --no-extensions 退出 0，但模型数为 0；未发模型请求。Onboard 拒绝无写入，同意／备份／幂等／恢复未执行。见 ignored reports/codex-approval/{approved,withheld,omp-readiness,onboard-refusal}.json 及同 stem 中文摘要。 |
| 2026-11-25T07:46:12.496562+08:00 | blocked | in-progress | 当前 Astra 会话：已确认任务 4 专用 OMP 官方登录并恢复无配置写入的原生检索验收。 | 登录 exit 0；私有域 models openai-codex --json --no-extensions 返回十项，含固定模型 gpt-6.2-astra；astGrep.enabled 为 false。未授权持久配置。 |
| 2026-11-25T07:47:21.431380+08:00 | in-progress | blocked | 当前 Astra 会话：任务 4 OMP 认证已核实；原生检索未启用，共享 MCP 配置为开。停在任务私有一次性配置写入授权门，循环保持关闭。 | 固定 OMP 登录 exit 0，10 项可用模型中精确匹配一项。只读 config get：astGrep.enabled=false、mcp.shared=true。未启动 RPC、未发起工具调用或写入宿主配置。见 reports/codex-approval/omp-post-login.json 和同 stem 中文报告。 |
| 2026-11-25T07:49:52.982179+08:00 | blocked | in-progress | 当前 Astra 会话：用户已授权仅在任务 4 临时目录创建一次性配置，开始私有 OMP 原生只读检索。 | 不写宿主持久配置；继续关闭共享 MCP、只允许合成夹具的精确调用。不含 Onboard 确认写入。 |
| 2026-11-25T07:53:48.142306+08:00 | in-progress | blocked | 当前 Astra 会话：已完成获准的一次性 OMP 原生只读检索本地验收，循环保持关闭；下一步 Onboard 私有夹具同意写入、备份、幂等和恢复待单独授权。 | OMP 19.1.0 临时覆盖 astGrep.enabled=true、mcp.shared=false；仅对 ast_grep 的 sample.py 精确调用原生 Approve Once。模型 openai-codex/gpt-6.2-astra，搜 1 文件、1 个 announce(value) 匹配；工具开始／结束各一，轮次 completed/settled、宿主 exit 0，夹具 SHA-256 不变。删除该覆盖后隔离域读取恢复基线 false/true。见 reports/codex-approval/omp-native-search.json 及同 stem 中文报告。不是 Onboard 同意写入、独审或发布结论。 |
| 2026-11-25T07:55:33.013847+08:00 | blocked | in-progress | 当前 Astra 会话：用户已授权仅写入一次性合成 OMP 配置夹具，开始 Onboard 备份、重复运行及原字节恢复验收。 | 只执行生产 language_tooling 接口；不运行全局 init/reset，不触及已认证宿主。 |
| 2026-11-25T07:56:55.911322+08:00 | in-progress | checking | 当前 Astra 会话：已完成获准的 Onboard 新合成配置夹具验收，保持循环关闭，转入检查。 | macOS 隔离生产 check/apply：拒绝零写；获准后原子替换前实测 0600 备份与仍在位原件字节相同；新配置仅启用 astGrep.enabled。二次检查及应用均无待写，无写入，内容、权限与 mtime 未变。验收驱动以备份替回，配置 SHA-256 与原件一致，不宣称自动恢复。见 reports/onboard-private-accept/acceptance.json 和同 stem 中文汇总。没有修改生产代码、已认证宿主或全局配置，未提交、推送或发布。 |
| 2026-11-25T08:05:03.925639+08:00 | checking | checking | 当前 Astra 会话：完成 任务 4 本地工作树双路独立内审及原审查人复核 | {"changed_files": [], "evidence_files": ["ai/tasks/v2.2.0-rc.2-search-tools/reports/internal-review/review.json", "ai/tasks/v2.2.0-rc.2-search-tools/reports/internal-review/review.md", "ai/tasks/v2.2.0-rc.2-search-tools/reports/internal-review/evidence.zip"], "sync_files": {"ai/tasks/v2.2.0-rc.2-search-tools/reports/internal-review/evidence.zip": {"mtime_ns": 1795564951658549097, "sha256": "57eacc572d5236d1eb044bf7bd0986acdebc86c720d7d4966074d98e41bcc04f", "size": 7834}, "ai/tasks/v2.2.0-rc.2-search-tools/reports/internal-review/review.json": {"mtime_ns": 1795565043212468758, "sha256": "d8170feb17c66db42f4a1cde0a48ace3f3ed4c40ea4d4ed134ea0ff66dc4d1a9", "size": 982}, "ai/tasks/v2.2.0-rc.2-search-tools/reports/internal-review/review.md": {"mtime_ns": 1795565057009850558, "sha256": "643b877c2a13d8aa0e8fb064121c59b54e7902f6a5a259d8f8ebecf1cb737f3d", "size": 1627}}, "validation": "Onboard 首审 CLEAN；宿主首审退回四项证据，补充分离 HEAD、离线四项原生结果、历史批准参数及结果投影、负例零转发计数后，原审查人关闭 F1–F4，限本地授权范围 CLEAN。附加未知工具探针仍为驱动 exit 1、宿主退出码未知，离线重放不代替历史正文。十份私有证据投影已校验。本轮未重启认证宿主、未提交或推送；待冻结精确提交并绑定附件后外审、核对同 SHA CI。"} |
| 2026-11-25T10:03:01.866351+08:00 | checking | done | 当前 Astra 会话：外部独审 CLEAN、PR #226 已合入、精确主线提交 CI 全绿；按用户确认收尾。 | {"clean_sha": "6da39c49765b1b28412ca58932868342e3cbe408", "ci_run": "45525529727", "main_sha": "d6e0bc3c0e366a65d1abd5e25ebc78969e1e9329", "main_ci_run": "45527867674", "main_jobs_passed": 13, "review_scope": "两路内置 reviewer 与外部独审；无交互 /review 执行回执"} |
