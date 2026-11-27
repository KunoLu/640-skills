---
schema_version: 1
id: v2.2.0-rc.3-host-baseline
workflow_mode: strict
mode_source: user
mode_note: rc.3 PRD D11、D13：T2 实测只提交任务记录，原生证据只保留在本地。
status: "checking"
branch: test/v2.2.0-rc.3-host-baseline
created_at: '2026-11-27T11:03:03.289188+08:00'
updated_at: "2026-11-27T15:43:53.840949+08:00"
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

以下是本机 macOS arm64 的 T2 结果，不是 Linux／Windows 原生 smoke，也不是 T7 的数据入库、去重和重放验收。以各自宿主发出的事件、审批回复和磁盘／服务端结果为据；回合成功不等于工具成功。

| 固定宿主 | 原生配置与调用 | 拒绝、失败和中断 |
|---|---|---|
| Codex `0.172.0` | `initialize` 返回任务专用 `codexHome`，`config/read` 返回只读策略；`untrusted` 线程内单次批准 `cksum` 后退出 0。另测真实模型 MCP 调用，批准后服务端收到请求。 | 命令拒绝为 `declined` 且无退出码，批准读取缺失文件退出 1；MCP 拒绝后服务端无调用，批准缺失文件得到 ENOENT。`turn/interrupt` 后终态 `interrupted`。 |
| OMP `19.2.1` | `--mode json` 的真实模型回合成功且无回退；RPC 只批准合成文件的 `read`，返回标记。默认 agent 目录与 named profile 分别指向隔离 HOME 下的不同路径。 | 用户拒绝与无交互 UI 拒绝可区分；批准读取缺失文件得到错误；RPC `abort` 后为 `aborted`。活动租约 held，退出后释放；原生 unknown 进入生产守卫后退出 2，不创建 runtime 目录。 |
| agy `1.5.18` | 经本轮授权的隔离 Google 个人 OAuth 重新认证，首个无工具真实回合成功。ACP `run_command` 收到 `allow_once` 后读到合成标记。 | 同一命令获 `reject_once`，工具为 failed；批准读缺失文件后是 `No such file`，不能由 ACP 包装层的 completed 判断成功。收到原生回合更新后发 `session/cancel`，终态 `cancelled`。 |

**Codex 与退役。** 官方完整包的主二进制与已验证的独立二进制逐字相同；只用独立二进制时，工具虽可列出，模型调用证据不足。对可选 stdio MCP 的缓存测试以同一 app-server 进程的新线程为单位：有缓存时服务在第一次调用时才启动；跨进程对照不证明这一性质。退役控制器使用四种 rc.2 生产渲染形态与私有文件原语；50/50 项通过。替换夹具启动器后，三个引用启动器的配置出现悬空，项目围栏仍有归属；第二次执行零写，四文件恢复原字节和权限。未知归属、同名第三方、写后编辑、缺创建证据、不安全路径的负例均未改目标。不是 T3 的生产退役入口。

**T4：规则与 Skills。** 无工具提示能返回 `~/.gemini/AGENTS.md` 与 `~/.gemini/config/AGENTS.md` 各自的标记，证明累加加载。同名 slash skill 选择 `~/.gemini/config/skills` 的夹具；只存在于 `~/.agents/skills` 的另一项也能调用，该目录在本测试中是指向 `~/.agent/skills` 的符号链接。四次同模型、同提示对照的首步 `input_tokens + cache_read_tokens` 依次为 10660（两文件）、10628（仅根文件）、10537（均无）、10663（恢复两文件）。两文件相对均无增加 123／126；这是整体输入观察，不能当成固定逐文件费率。`/context` 没有取得 Rules 分类计数，也没有代用户接受交互条款。

**T4：受保护配置。** 真实 `run_command` 调用了仓内 Onboard 的 `snapshot`、`backup_reference`、`write_file` 原语，目标仅为任务域 `~/.gemini/config/mcp_config.json`。普通模式拒绝后字节不变；单次批准后新增指定测试 server，原有 server 保留。`--sandbox` 会话也请求审批；单次批准且 `BypassSandbox=false` 后，内层 `sandbox-exec` 在外层文件隔离内报 `sandbox_apply: Operation not permitted`，目标未变。这是嵌套沙箱的实测限制，不是“已验证内层路径策略拒绝该文件”，也不是 T4 安装菜单已上线。未降低隔离以取得写入结果。

**T5：事件契约。** 实际 NDJSON 为 `event=init/step_update/result`；工具步骤可包含 `tool_info.name/parameters/output` 或 `error`。对比同一已结束进程的 `conversation_id` 和唯一 `transcript.jsonl`，读取前后大小与 mtime 均稳定；普通文件工具和 `call_mcp_tool` 均有 `tool_calls[].name/args` 形态。MCP 的 `ServerName`、`ToolName` 在流的 `parameters` 和 transcript 的 `args` 内出现，`Arguments` 不可作为事件元数据保留。有的 transcript 参数值本身是 JSON 引号编码的字符串。默认无界面 MCP 样本中工具 ERROR、服务端零调用，但 `result.status=SUCCESS`、进程退出 0；只可作失败调用形态，不计成功。后续解析不得采集命令、参数值、输出、正文或 thinking。

**证据与维护范围。** 详细测试报告保留在本任务的 ignored `reports/`。关键组为 `codex-live-matrix-02`、`codex-live-mcp-approval-02`、`codex-mcp-same-process-02`、`omp-followup-01/snapshot`、`omp-unknown-guard-01`、`retirement-t2-01/result`、`agy-budget-accounting-04`、`agy-acp-matrix-01`、`agy-acp-matrix-02`、`agy-tool-witnesses-04`、`agy-parser-shapes-02` 和 `agy-mcp-shapes-01`；每组均有同 stem 中文汇总。保留未成功的控制轮。没有改产品、运行时契约、安装器或监控规则；双语 README、CHANGELOG 和版本检查 prompt 无用户可见行为要同步。

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
