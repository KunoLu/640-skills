---
schema_version: 1
id: v2.2.0-rc.3-host-baseline
workflow_mode: strict
mode_source: user
mode_note: rc.3 PRD D11、D13：T2 实测只提交任务记录，原生证据只保留在本地。
status: "checking"
branch: test/v2.2.0-rc.3-host-baseline
created_at: '2026-11-27T11:03:03.289188+08:00'
updated_at: "2026-11-27T17:34:27.919762+08:00"
completed_at: null
"blocked_reason": null
---
# T2：三宿主行为基线和退役演练

## T1 合入回执

[PR #232](https://github.com/KunoLu/640-skills/pull/232) 的受审 head `2fce542894c279a0268a1fba2d3e985f1b19a0b6`：OMP 内置审查与 agy 独立复审均为 CLEAN，[PR validation](https://github.com/KunoLu/640-skills/actions/runs/45922706149) 13/13。agy 核销了 F1 和两个 P1，无新发现；这是静态审查，不是宿主 smoke。合入后 main 为 `dc228de75b4587df8abf05315e30bc7b9ebbb4ef`，内容树与受审 head 相同，[main validation](https://github.com/KunoLu/640-skills/actions/runs/45930622708) 13/13。已验证 T1 的本地和远程开发分支均不存在；未删除私有报告。T3 需保护 OMP 全局 AGENTS 导入链并评估探测进程 DNT；T4 评估宿主中性表述。

## 实测范围和停止条件

按 PRD Phase 0：分开验证 agy 的全局规则、同名 Skills、受保护配置与输出格式；三宿主的配置读取、真实审批及拒绝、工具装载和调用、事件、失败和中断；另测 Codex 延迟 MCP 启动、OMP lease／JSON／配置来源。用合成配置演练旧接线退役和悬空检测，不触碰真实宿主或启动原生结构图工具。只记录实际观察，不拿单纯版本匹配、主会话、历史报告或夹具作为真实行为通过凭证。

rc.3 精确验收 pin：`codex@0.172.0`、`omp@19.2.1`、`agy@1.5.18`。按用户在 D5 提前复核后的决定，只有 agy 的验收目标从 `1.5.16` 改为 `1.5.18`。本次复核时 agy 官方 CLI Latest 仍为 `1.5.16`；验收目标不改写该观察，也不改变官方版本监控的取值规则。后续适配和 T6 能力矩阵按这些目标执行；冻结前仍需复核，验收通过仍需相应版本的真实行为矩阵和 smoke。

每个宿主独用隔离 HOME、缓存、配置和合成项目。Codex／OMP 只允许隔离域内官方登录。agy 可复用当前 macOS 用户已有登录并由官方客户端自动刷新；T2 与 T7 不宣称钥匙串零写入。静默复用失败后，用户另行授权本轮 T2 在隔离域用同一 Google 个人账号执行一次官方浏览器登录。重新认证所得的行为证据不算原登录静默复用成功；失败或取消不重试。不得登出、提取或复制凭据、修改钥匙串权限或使用替代认证。永久授权或访问非预期条目时停止。不更新真实宿主。原生证据及中文摘要保存在本任务 ignored reports，不提交认证或会话正文。

## Book Gate Plan

本任务不改生产代码。无新领域、数据设计、迁移实现或重构：DDD、DDIA、migration 和 Refactoring 不触发。Legacy Safety 以本轮真实观察为后续 T3 的特征证据，不预记通过。验证以本机真实隔离进程为准；未执行不写通过，无部署／发布门。未完整调用 grill-with-docs：范围、四类退役夹具和停止条件已由 PRD 定稿。

## Phase 0：实测结果与下游约束

以下是本机 macOS arm64 的 T2 结果，不是 Linux／Windows 原生 smoke，也不是 T7 的入库、去重和重放验收。表中所有批准和拒绝，均由测试控制器回应真实宿主协议（Codex app-server RPC、OMP rpc-ui、agy ACP `session/request_permission`），不是人在 UI/TUI 中点击。协议决定、工具执行结果和模型回合终态分别取证；回合成功不等于工具成功。

| 固定宿主 | 原生配置与调用 | 拒绝、失败和中断 |
|---|---|---|
| Codex `0.172.0` | `initialize` 返回任务专用 `codexHome`，`config/read` 返回只读策略；`untrusted` 线程内单次批准 `cksum` 后退出 0。另测真实模型 MCP 调用，批准后服务端收到请求。 | 命令拒绝为 `declined` 且无退出码，批准读取缺失文件退出 1；MCP 拒绝后服务端无调用，批准缺失文件得到 ENOENT。`turn/interrupt` 后终态 `interrupted`。 |
| OMP `19.2.1` | `--mode json` 的真实模型回合成功且无回退；RPC 单次批准合成文件的 `read` 后得到标记。离线 `config path` 的四组目录对照见下文。 | rpc-ui 控制器选择 Deny 时为 `denied by user`，无界面 JSON 则为 `no interactive UI available`；批准读缺失文件得到错误；RPC `abort` 后为 `aborted`。活动租约 held，退出后释放；原生 unknown 进入生产守卫后退出 2，未创建 runtime 目录。 |
| agy `1.5.18` | 经本轮授权的隔离 Google 个人 OAuth 重新认证，首个无工具真实回合成功。ACP `run_command` 收到 `allow_once` 后读到合成标记。 | 同一命令获 `reject_once`，工具为 failed；批准读缺失文件后是 `No such file`，不能由 ACP 包装层的 completed 判断成功。收到原生回合更新后发 `session/cancel`，终态 `cancelled`。 |

**Codex 与 OMP。** Codex 官方完整包的主二进制与已验证的独立二进制逐字相同。只用独立二进制时，目录可列出，未取得模型实际调用证据。可选 stdio MCP 延迟启动试验是协议客户端直调、没有模型回合：在同一 app-server 进程中新建线程，缓存存在时服务到首次调用才启动；跨进程对照不能证明这一性质。

OMP `19.2.1` 在新隔离 HOME 的 `config path` 实测：不设覆盖为 `~/.omp/agent`；只设 `PI_CODING_AGENT_DIR` 则采用指定目录；只传 `--profile t2check` 为 `~/.omp/profiles/t2check/agent`；两者同时指定时仍取 named profile。此结论仅限 agent 目录解析，不证明对应目录内已退役任何 MCP。前轮 `--config <overlay> config get` 未显示覆盖层，不能用那个输出证明审批生效；运行时 `always-ask` 会话记录和实际审批回复是独立证据。

**T3：退役与归属。** 50/50 是隔离夹具检查数，不是生产退役 CLI 的结果。删除夹具启动器桩后，Codex/OMP MCP 和 Codex hooks 三项既有已证明归属，又指向缺失启动器；围栏没有启动器路径，仍可证明归属。`verify_owned_*` 接受形状既不能检测悬空，也不能证明写入者：缺少回执的同形项、写后被追加注释的配置都可通过形状检查。对记录的启动器路径独立 `lstat`；用写入回执、实际写后校验和及所需模式核对归属和漂移。D6 下，已证明归属且悬空的项经确认和备份后退役；归属不明且指向将删除或已缺失启动器的项不能据名清理，阻断相应 reset／upgrade。

四个正例均保留原有第三方内容，用 `write_file` 写回。二次执行零写，回退恢复四文件字节与权限。未知归属、第三方同名、写后编辑、无成功创建凭证、不安全路径均未改目标。T3 必须另测三类正例：`before.type=absent` 且有成功创建凭证时用 `remove_reference` 删除；固定根 `sbtd-graft-<root-hash>` 的有凭证退役；named profile 和 `PI_CODING_AGENT_DIR` 各自生效的 OMP 目标文件。rc.2 单测与目录解析观察不能替代这些端到端检查。

**T4：规则与 Skills。** 无工具提示能返回 `~/.gemini/AGENTS.md` 与 `~/.gemini/config/AGENTS.md` 各自的标记，证明累加加载。同名 slash skill 选择 `~/.gemini/config/skills` 的夹具；只存在于 `~/.agents/skills` 的另一项也能调用，该目录在本测试中是指向 `~/.agent/skills` 的符号链接。四次同模型、同提示对照的首步 `input_tokens + cache_read_tokens` 依次为 10660（两文件）、10628（仅根文件）、10537（均无）、10663（恢复两文件）。两文件相对均无增加 123／126；这是整体输入观察，不能当成固定逐文件费率。`/context` 没有取得 Rules 分类计数，也没有代用户接受交互条款。

T4 要区分 Onboard 安装根与 agy 实际加载来源：即使写入 `~/.agents/skills`，`~/.gemini/config/skills` 的旧同名项仍可遮蔽它。`plan/check` 应报告这一同名冲突及实际来源；不得据此覆盖用户副本。

**T4：受保护配置。** 目标仅为隔离 HOME 的 `~/.gemini/config/mcp_config.json`，由真实 `run_command` 调用 Onboard 的 `snapshot`、`backup_reference`、`write_file` 文件原语。原首轮 `agy-acp-matrix-01` 的 `deny`、`standard-deny` 在 PTY 尚不可用时得到拒绝；原次轮 `agy-acp-matrix-02` 放行任务 PTY 后才有普通模式批准写入。不要跨这两轮构造控制对。返修用同一 PTY 策略补做五项：普通读取拒绝、普通受保护写拒绝和 `--sandbox` 受保护写拒绝均为 `reject_once`、工具 failed、目标未改；普通写 `allow_once` 后磁盘确实新增合成 server 并保留原项；`--sandbox` 写获 `allow_once`（无 `BypassSandbox=true`），包装层 completed，但嵌套 `sandbox_apply` 报 `Operation not permitted`，目标未改。

实际触发的是通用 `run_command` 审批，不足以证明 `mcp_config.json` 有独立的路径级审批门。未撤掉外层文件隔离；缺少非嵌套 `agy --sandbox` 对受保护配置与普通文件的同条件写入对照。T4 不得推定内层路径策略、特定 errno 或 Onboard 错误码；拒绝、沙箱启动失败及任一 `OSError`／`ContractError` 均须 fail-closed，如实报告所处步骤和实际错误，不把工具包装层完成当作磁盘写入成功。上述观察不是对 T4 安装菜单的验收。

**T5：`agy-stream-json-1`。** agy `--version` 的 stdout 是裸字符串 `1.5.18`。两种输入的本轮样本都没有可用的宿主版本字段；按 FR-5 独立传入并精确验证 `--host-version`，不从模型名或目录猜版本。

只消费 `event=step_update` 且 `step_update.step_type=tool` 的工具事实。`init`、`result`、`user_input`、`agent_response` 均不是工具执行；`init.tools` 是目录，不一定等于实际工具名。两个原生样本的同一工具步先 `ACTIVE`，再分别为 `DONE`（`read_file`，工具层成功）或 `ERROR`（`call_mcp_tool`，工具层失败，不能据此细分拒绝）。`step_update.tool_name` 是外层名称，实测与 `tool_info.name` 同时存在且相等；T5 不在两者冲突时任选其一。MCP 的 `tool_info.parameters.ServerName/ToolName` 实测为裸字符串，用于构造 `mcp:<server>.<tool>`；不采集 `Arguments`、输出、错误消息、命令或模型正文。旧投影 `agy-mcp-shapes-01.json` 的 scope 误写了批准规则，以同 stem 中文勘误为准：实际是 `request-review`、零服务端调用。`result.status=SUCCESS` 与进程退出 0 均不能把工具 `ERROR` 改判成功。

实测工具步无时间戳或独立 call ID。`occurred_at=null`，不得拿接收时间填充；`duration_seconds` 在 ACTIVE 未见，终态样本有浮点秒，不能当作时间戳。T5 以进程内一致、合法的 `conversation_id`（UUID）绑定非负整数 `step_index`，用相同索引聚合更新；不要按流行号识别一次调用。派生键规则见下。这里只锁定观测到的枚举，未知状态、孤立终态与相互冲突的标识不能视为成功。

**T5：`agy-transcript-jsonl-1`。** 20 份已结束、大小和 mtime 稳定的合成样本中，见 `USER_INPUT`、`PLANNER_RESPONSE`、`GENERIC`、`SYSTEM_MESSAGE`，状态为 `DONE` 或 `ERROR`，来源为 `USER_EXPLICIT`、`MODEL` 或 `SYSTEM`；不是对未来发行版的枚举穷举。13 行声明工具调用，均为单项 `PLANNER_RESPONSE.tool_calls[]`，只有 `name`、`args`，无调用 ID。MCP 的 `args.ServerName/ToolName` 是内含 JSON 引号的字符串：仅对两个身份字段 JSON 解码一次，要求结果为合法字符串再构造组件名，不把引号拼入标识。不要对业务参数、`content`、`thinking`、输出或 `error` 文本取值入库。

| 已知夹具事实 | 紧随单调用 planner 的结果行（索引 +1） | T5 可判定的上限 |
|---|---|---|
| 读取成功、命令成功、读缺失文件、嵌套沙箱拒绝执行 | 均为 `GENERIC/DONE`，无 error 键 | 只知该步骤已结束，不知底层调用成功与否；不能一律计入 `succeeded`。 |
| 控制器经协议拒绝、MCP 工具报错 | 均为 `GENERIC/ERROR`，有字符串 error，无独立 error code/type | 至多标记工具层失败，不能推出 `declined`，也不能解析错误消息来区分。 |

结果行本身无工具名、call ID、会话 ID 或结构化退出码。只在同一已绑定会话中、单一待配对调用且相邻索引唯一时关联；多调用批次未实测，不把下一条 `GENERIC` 分配给任意一个工具。无法证明的关联、未知枚举或冲突行应计入跳过／缺口，不合成完成事件。`created_at` 为带 Z 的秒级时间，可作该行 `occurred_at`，同秒可重复，不是键；没有可靠耗时就保留空值。

**T5 身份与重放约束（派生规则，不是宿主原生字段）。** 流取经验证且前后一致的 `conversation_id`；离线行不含该 ID，必须由显式输入的受控、归属唯一的会话目录 UUID 绑定 `transcript.jsonl`。本次发现同名会话数据库 stem 与目录一致；不要求读取数据库正文。导入仍需确认会话结束、`--confirmed` 和前后 stat 一致；裸复制文件、路径越界、多个候选或归属不明时拒绝，不按文件名 `transcript.jsonl`、mtime 或正文猜 ID。每格式独立 `source_id`；`source_event_id` 由会话 UUID、调用起点索引（流的工具步／离线的 planner 步）、该步调用序号（本样本均为 0）和阶段 `start`/`finish` 确定派生，编码需无歧义且不超过 128 字符。同一调用两阶段共享 `invocation_id`；重复 ACTIVE 更新不生成新开始。`(source_id, source_event_id)` 保证同格式同原件重放用同一键，不以接收时间、随机 ID 或原始正文摘要去重。两种格式没有原生跨格式调用 ID，不应将同一会话两份输入重复计入一组验收。

**证据与维护范围。** 详细测试报告保留在本任务的 ignored `reports/`。关键组为 `codex-live-matrix-02`、`codex-live-mcp-approval-02`、`codex-mcp-same-process-02`、`omp-followup-01/snapshot`、`omp-unknown-guard-01`、`retirement-t2-01/result`、`agy-budget-accounting-04`、`agy-acp-matrix-01`、`agy-acp-matrix-02`、`agy-tool-witnesses-04`、`agy-parser-shapes-02` 和 `agy-mcp-shapes-01`；每组均有同 stem 中文汇总。保留未成功的控制轮。没有改产品、运行时契约、安装器或监控规则；双语 README、CHANGELOG 和版本检查 prompt 无用户可见行为要同步。

外审返修增加五组本地证据：`agy-stream-tool-contract-01`、`agy-transcript-result-rows-01`、`omp-directory-precedence-r2`、`agy-pty-paired-r2`、`agy-pty-outcomes-r2`。`phase0-evidence.sha256` 更新为 89 项；原 79 项的字节和旧清单原件（`phase0-evidence-0b1c6b2.sha256`）均保留。两轮清单范围都是 JSON/XML/中文摘要，不包含未发布的会话正文或登录资料。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-27T11:03:13.975367+08:00 | planned | in-progress | OMP：开始 核对三宿主测试入口及精确版本 | {"changed_files": [], "evidence_files": [], "sync_files": {}, "validation": ""} |
| 2026-11-27T11:03:56.108763+08:00 | in-progress | blocked | OMP：完成隔离版本预检；agy 已从 PRD 所述本机 1.5.16 变为 1.5.18，与 T2 精确验收 pin 不符，按定稿差异规则停止。 | 本地三组 --version 均 exit 0：codex-cli 0.171.0（目标 0.172.0），omp/19.2.1（匹配），agy 1.5.18（目标 1.5.16）。见 ignored reports/{codex,omp,agy}-version.txt 及同 stem 中文摘要。没有启动真实会话、登录或退役操作；未改变 pin、真实宿主或钥匙串。需可用的受信 agy 1.5.16 或经用户决定提前执行 D5 复核；Codex 仍需独立的匹配版本。 |
| 2026-11-27T12:02:53.960956+08:00 | blocked | in-progress | OMP：用户指定 agy 验收 pin 为 1.5.18，解除旧 agy 版本不匹配的阻断。 | D5 查询的 CLI Latest 为 1.5.16；此次为用户明确指定的验收例外，不作为官方 Latest 证据。 |
| 2026-11-27T12:03:04.707518+08:00 | in-progress | blocked | OMP：Codex 隔离预检为 0.171.0，仍缺已验证的 0.172.0 测试入口。 | 确认验收目标为 Codex 0.172.0、OMP 19.2.1、agy 1.5.18；后两者在已有预检中匹配。没有安装或升级，也没有新的 smoke。 |
| 2026-11-27T12:05:13.199147+08:00 | blocked | in-progress | OMP：用户授权在 T2 私有环境安装 Codex 0.172.0 并继续实测；保留 agy 1.5.18。 | 仅限任务私有测试域；不更新全局 CLI，不读取或复制真实认证。开始获取并验证固定发行物。 |
| 2026-11-27T12:13:31.273703+08:00 | in-progress | in-progress | OMP：完成 安装固定 Codex 并核对隔离宿主预检与离线协议 | {"changed_files": [], "evidence_files": [], "sync_files": {}, "validation": "Codex 官方 rust-v0.172.0 macOS arm64 资产 SHA-256 bd121f8abd6b28b3fc476da04a348e25a83e89eda19d39107f68f8e966053092。三宿主版本全匹配。Codex config/read 和同进程跨线程 optional stdio 实调用通过，缓存线程首次调用前无新启动、调用后增加一个并返回合成标记；不是模型审批。OMP 空 lease、隔离配置路径、禁用共享 MCP 后的 RPC get_state 成功；首次 RPC -11 已保留，未归因为产品缺陷。agy 1.5.18 的离线 ACP initialize 成功，未访问钥匙串。rc.2 归属夹具首轮缺 tomlkit，复用已有解释器后 7 passed、4 subtests passed，不是 rc.3 完整退役演练。原生或脱敏协议证据与中文汇总在本任务 ignored reports。"} |
| 2026-11-27T12:13:41.820165+08:00 | in-progress | blocked | OMP：三宿主版本阻断已解除；下一阶段 Codex／OMP 真实模型回合需要在各自私有 HOME 内完成人工官方登录。 | Codex login status 返回 Not logged in（exit 1），account/read 无账号且 requiresOpenaiAuth=true；OMP 使用独立新 HOME，未导入登录。未执行真实模型回合、审批矩阵或 D10 agy 钥匙串 smoke。不要在真实 HOME 登录或导出凭据；恢复后逐项补证。 |
| 2026-11-27T12:16:30.581259+08:00 | blocked | in-progress | OMP：收到用户已登录的回报，继续 T2 的隔离取证；逐宿主核对该身份是否对任务测试进程可用。 | 既有隔离 Codex login status 仍返回 Not logged in；不推断用户未登录、不搜索其他域。继续不依赖该账号的原生测试和退役演练，独立核验 OMP 与 agy。 |
| 2026-11-27T12:30:34.086827+08:00 | in-progress | in-progress | OMP：完成 取证隔离 Codex 0.172.0 行为矩阵 | {"changed_files": [], "evidence_files": [], "sync_files": {}, "validation": "用户澄清 OMP 登录先成功，Codex 设备码请求失败且 Teams 成员不可使用。隔离 Codex 指定系统公有 CA 后，原生 doctor 的 provider HTTP 从 fail 到 ok；未改代理或系统信任。改用官方浏览器登录，隔离 login status exit 0、account/read=chatgpt。完整包 SHA-256 0970016d48209a09c4039139629ed79b4a31c5e3d864e792c043419d98fa6466，与此前独立发行物的主二进制逐字一致。真实 readOnly/untrusted 线程按精确命令接收一次性审批，批准成功 exit 0、拒绝无退出码、批准缺失文件 exit 1、主动中断 interrupted。真实 MCP 回合同样获得三次匹配审批：允许实际读取，拒绝无服务端调用，允许缺失文件产生 ENOENT。保留初次仅列出目录却无模型调用的两份结果。#62366 同进程延迟启动见前轮原生证据；#62194 保留 exec resume 权限的上游变化只作记录，未作验收结论。"} |
| 2026-11-27T12:36:29.957993+08:00 | in-progress | in-progress | OMP：完成 验证 OMP 真实行为及 T2 退役演练 | {"changed_files": [], "evidence_files": [], "sync_files": {}, "validation": "OMP 19.2.1：真实 JSON 模型回合成功，无模型回退；RPC 明确拒绝、一次批准成功、ENOENT、abort；无交互审批 fail-closed 不算人工拒绝。活动 lease 为 held，退出后释放；不安全合成 lease 进入 unknown，生产适配器默认守卫退出 2 且未创建数据目录，恢复 0700 后为阴性。默认与 named profile 来源已验证。退役夹具验收 50/50：两个 MCP、Codex hooks、项目围栏；启动器缺失后三类悬空，围栏仍可证；第二次零写，恢复四项字节和原权限；五类负例均无目标写入。无真实 Graft/npx/清理；不冒充 T3 的生产退役实现。详见 ignored reports/omp-followup-01/snapshot、omp-unknown-guard-01、retirement-t2-01/result 的 JSON 及同 stem 中文汇总。"} |
| 2026-11-27T12:36:40.471005+08:00 | in-progress | blocked | OMP：Codex 和 OMP 已完成本轮真实行为矩阵；剩余阻断是 agy D10 的已有登录复用与钥匙串不写入的可验证边界。 | agy 1.5.18，隔离 ACP initialize 成功，缺省／合成 mcp_config.json 的原生 list 差分通过。已放置两份规则、同名与链接 Skill；ACP session/new 返回 -32603。仅放行回环、保持钥匙串和外网禁用的无终端负例提示 authentication required 后停止；没有执行登录、登出或复制凭据。这不是实际 D10 复用失败，也不能证明真实登录无效。官方文档描述静默复用，当前无已验证的只读钥匙串运行／写入审计边界；未开放无限制安全服务。规则预算、同名 Skills 优先级、受保护配置审批、成功 stream-json / transcript 字段和 agy 真实矩阵均未通过。T2 不开 PR、不进 T3。 |
| 2026-11-27T14:33:03.038033+08:00 | blocked | in-progress | OMP：用户修订 D10，开始在隔离 HOME 使用当前 macOS 用户的既有 agy 登录。 | 仅允许官方客户端自动刷新该登录；不要求零写入证明，不访问凭据内容，不改变其他隔离与停止条件。先做一次无交互复用探针，再按真实结果决定是否继续。 |
| 2026-11-27T14:34:50.686057+08:00 | in-progress | blocked | OMP：修订 D10 已生效；隔离 agy 在放行系统钥匙串服务及网络后仍要求登录，按停止条件结束本次复用尝试。 | 原始签名 agy 1.5.18、当前 macOS 用户、任务专用 HOME、无 API key/ADC、关闭 stdin；允许官方自动刷新，不要求零写入。一次真实无工具提示，login_required，exit 1，无成功回应；未主动登录、登出、重试或改变钥匙串权限。账号类型及失败根因未知。证据 reports/agy-d10-reuse-01.json 和同 stem 中文汇总。三宿主门禁未齐；不开验收 PR、不交外审。 |
| 2026-11-27T15:22:22.435723+08:00 | blocked | in-progress | OMP：已获一次隔离域官方浏览器登录授权，账号类别为用户确认的 Google 个人账号。 | 仅限原始签名 agy 1.5.18 的 acp --login，使用任务 HOME 和系统浏览器；认证交互只对用户可见，不允许第二次尝试。 |
| 2026-11-27T15:22:33.565450+08:00 | in-progress | blocked | OMP：已准备一次性登录入口并请求本机 Terminal 打开，等待人工交互结果；未证明认证成功。 | 启动器 bash -n、隔离 --check（版本及原生 --login 帮助）通过。只检查本次启动标记及退出码，不捕获终端内容；后续以同一隔离域的原生请求验证。 |
| 2026-11-27T15:27:46.873455+08:00 | blocked | in-progress | OMP：用户报告 agy 已登录，任务隔离域的一次性官方登录回执 exit 0；开始用同一域验证真实模型回合。 | 仅检查一次性预留标记和退出码，未读取凭据或登录界面；本轮是授权的重新认证，不记为此前的静默复用。 |
| 2026-11-27T15:43:31.773506+08:00 | in-progress | in-progress | OMP：完成 验证隔离域 agy 登录后的规则、Skills、审批、原生事件与失败／中断 | {"changed_files": [], "evidence_files": ["ai/tasks/v2.2.0-rc.3-host-baseline/reports/phase0-evidence.sha256"], "sync_files": {"ai/tasks/v2.2.0-rc.3-host-baseline/reports/phase0-evidence.sha256": {"mtime_ns": 1795765400582803617, "sha256": "999402d0b63507dac8b0fcab8eeef1c602b1c0cd9192dc4f202e3b42911ca1fb", "size": 7263}}, "validation": "一次性 Google 个人 OAuth 后真实回合 SUCCESS；不是此前的静默复用。批准的合成读取、拒绝、缺失文件、原生 cancel、普通受保护文件写入与 --sandbox 嵌套失败分别有证据，未绕过沙箱。36 份 JSON 均有同 stem 汇总，关键回执断言通过；完整报告清单的 SHA-256 绑定本轮本地证据。"} |
| 2026-11-27T15:43:53.840949+08:00 | in-progress | checking | OMP：Phase 0 结果与限制已登记，开始在精确 PR head 执行内置 /review；外审和 CI 尚待完成。 | 只提交任务记录与索引。三宿主、私有退役夹具与正式发布验收分开；没有提交报告、登录材料或产品变更。 |
| 2026-11-27T17:16:48.365325+08:00 | checking | in-progress | OMP：收到 agy 对 0b1c6b2dbefea5eb26de46ffd8630ab9dd4c7a07 的 CHANGES_REQUESTED；开始补证事件格式、配置来源、审批与退役边界。 | agy 只读复核旧清单 79/79；旧 head 内审 CLEAN、validation 45960511880 为 13/13，均不抵消 P1-1、P2-1 至 P2-4。同步处理两项 P3；不降低外层隔离，不改生产模块或回写历史事件。 |
| 2026-11-27T17:34:06.554353+08:00 | in-progress | in-progress | OMP：完成 补证两种 agy 事件格式、同 PTY 审批、OMP 来源和退役边界 | {"changed_files": [], "evidence_files": ["ai/tasks/v2.2.0-rc.3-host-baseline/reports/phase0-evidence.sha256", "ai/tasks/v2.2.0-rc.3-host-baseline/reports/phase0-evidence-0b1c6b2.sha256"], "sync_files": {"ai/tasks/v2.2.0-rc.3-host-baseline/reports/phase0-evidence-0b1c6b2.sha256": {"mtime_ns": 1795771178675921020, "sha256": "999402d0b63507dac8b0fcab8eeef1c602b1c0cd9192dc4f202e3b42911ca1fb", "size": 7263}, "ai/tasks/v2.2.0-rc.3-host-baseline/reports/phase0-evidence.sha256": {"mtime_ns": 1795772035773406384, "sha256": "6e06247736cadc40aa3841ca033d8210399d040711abc9d5a7b80399733506f4", "size": 8211}}, "validation": "P1-1 与 P2-1/2/3/4 已按实测修正；两项 P3 已澄清。同一外层隔离下追加五个 ACP 对照，不主张非嵌套策略。新旧清单均逐文件验算通过；T5 派生身份仅为后续约束，尚未实现入库。"} |
| 2026-11-27T17:34:27.919762+08:00 | in-progress | checking | OMP：完成外审返修并开始新 head 全 PR 内置 /review。 | 新 SHA 须重做 OMP 内审、agy 复审与 CI；旧 13/13 不继承。 |
