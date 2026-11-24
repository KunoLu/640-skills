---
schema_version: 1
id: v2.2.0-rc.2-host-behavior
workflow_mode: strict
mode_source: user
mode_note: rc.2 PRD；用户授权从任务 2 合入后的 main 开始任务 3。
status: "checking"
branch: test/v2.2.0-rc.2-host-behavior
created_at: '2026-11-24T16:35:41.545526+08:00'
updated_at: "2026-11-24T19:03:21.375386+08:00"
completed_at: null
"blocked_reason": null
---
# 任务 3：新版基础行为与最小兼容调整

输入：任务 2 的 PR [#224](https://github.com/KunoLu/640-skills/pull/224) 已由明确的 admin 授权 squash。许可修复的外审 head 为 `c57ae7efc7326249b23f847f299d7bab90fd6534`，对应 [PR CI](https://github.com/KunoLu/640-skills/actions/runs/45351271714)；当前任务以 squash 后的 `b0958078cf8e9d31739bef9cf17e76973f2dfee3` 为基线，对应独立的 [main CI](https://github.com/KunoLu/640-skills/actions/runs/45354457553)。这不是发布授权。

## 范围与通过标准

在 Air 的原 Astra 实现会话组织隔离进程，分别验证 OMP `19.1.0` 和 Codex `0.171.0`。主会话不是被测 OMP 版本。配置读取、权限和真实审批（含拒绝）、工具装载与实际调用、原生事件、失败及中断需分别取证；版本号、工具清单、未登录回执和上一任务的成功调用均不能代替。

- 仅使用本任务私有 HOME、CODEX_HOME、OMP agent/session、缓存与合成项目。全局认证、信任、真实正在写入的会话日志均不读取、不复制、不迁移。仅允许在获准的隔离域走官方认证。未证明会话归属或出现意外写入立即停。
- 不启用可选 eval，不自动信任未知仓库。按 PRD §3.3 和任务 3 的工具装载要求验证宿主 MCP：仅允许任务私有、只读、无外部数据的测试服务；不启用共享 daemon，不安装或接线任务 4 的 ast-grep。审批、调用失败、中断分别取证。
- 只在原生观察提供具体兼容性缺口后才改适配器。不混入任务 4 的 ast-grep MCP 接线，不提前发布。

## Book Gate Plan

未完整调用 grill-with-docs：PRD 已给定固定版本、范围、负例和停止条件。无新增领域术语或持久化格式设计。若发现真实行为回归，修改前执行 Legacy Safety／Refactoring，先保留旧失败和消费边界；若涉及持久化或跨进程契约，再评估 DDIA。正式结论需真实宿主验收、project-validation；若改到生产路径则再做 release readiness。

## 证据与恢复

脱敏报告仅存本任务 ignored `reports/`。当前 OMP 主角色 GPT-6.2 Astra，精确调用次数未知。保留临时域及失败现场，不清除此前任务 TEMP。身份、真实审批、全局隔离或会话占用不明时记录阻断、关循环、保留现场；不以自动切换模型或复用其他账户恢复。

## 本地验收结果

Codex `0.171.0` 的 `app-server --listen stdio://` 在临时 `CODEX_HOME` 中返回 `config/read`：`gpt-6.2-astra`、`on-request`、`read-only`；`thread/start` 针对合成项目显式覆盖为 `untrusted`，宿主返回 `modelProvider=openai`、`sandbox.type=readOnly`。`read_fixture` 由客户端按线程注册，限定读取合成标记或一个不存在的文件。OMP `19.1.0` 的首轮 RPC 使用 `--no-session --tools read --approval-mode always-ask-cached`，实际模型为 `openai-codex/gpt-6.2-astra`。这些 RPC 决定只对本次调用有效，不批准目录或整个会话。

| 观察点 | Codex | OMP |
|---|---|---|
| 调用成功和失败 | `read_fixture` 的 `ENOENT` 来自客户端，只证明错误能传回宿主。另测原生 `/usr/bin/cksum task3-native-absent.txt`：一次性批准后 `commandExecution.status=failed`、exit 1；同线程再次请求同一命令仍收到审批，拒绝后 `declined`、无退出码 | 内置 `read` 一次性批准后读到标记；对缺失路径同样批准后返回工具错误 |
| 原生审批 | 对 `/usr/bin/cksum task3-marker.txt` 分别 `decline` 与 `accept`：前者 `declined`、无退出码，后者 `completed`、退出 0 | 两次读同一标记文件：`Deny` 对应拒绝错误且无标记，`Approve Once` 对应成功及预期内容 |
| 主动中断 | 收到 `turn/started` 后发送 `turn/interrupt`，应答后终态 `interrupted` | 收到 `agent_start` 后发送 `abort`，应答后 `prompt_result.status=aborted`、`sessionSettled=true` |

两端进程均正常退出 0。上述是模型发起工具调用、控制器回应真实审批协议的证据，不代表人工 TUI 点击，也不代表中断了已运行的外部命令。OMP 的独立模型目录在登录后包含目标模型；沙箱禁止 OMP 读取 Codex 的已认证目录。固定二进制、配置读取和认证就绪回执见本任务本地 `reports/`。

首轮 OMP 控制器误把“首次写入前没有持久化租约”判为无法继续，未提交提示便关闭循环，子进程正常退出。随后 `--no-session` 探针验证的是内存会话行为；`held=[]`、`unknown=[]` 不是写者身份证明，也不应称为“曾取得并释放租约”。返修使用独立持久化会话验证实际写者与释放，见下文。

之前的 RPC 探针没有运行这两个生产 JSONL 适配器，不能据此判断适配器兼容性。真实配置文件的抽查元数据未变；活跃主会话 OMP 数据库元数据变化的写者未确定。返修用无秘密哨兵验证 OMP 同一沙箱可写任务临时根，却被内核拒绝在根外打开测试文件写入、读取 Codex 私有域哨兵也被拒。继续的依据是已独立核实的进程隔离，不是推定全机零写入。首次 `sandbox_check` 查询连正对照都未区分，未用作通过证据。

## 外审返修：生产输入与消费结果

以下计数来自真实原件进入生产 CLI、同一文件再导入、`EventStore.replay()` 和 `host_capability()`；每组使用任务临时域中的独立 metadata 观察库。`pinned` 只证明事件携带固定版本，不代表全部行为通过。
Codex 的 `cwd` 是任务私有 `$TASK_TEMP/probe`；`thread/start.dynamicTools` 只在客户端工具用例注册 `read_fixture(name=present|missing)`，在原生命令分支不注册。新回执同时投影宿主实际 `config/read`、线程 `approvalPolicy`／`sandbox`、命令原文与决策；它与 `exec --json` 的观察库输入是两组证据。
新建未受信非 Git 目录的负例没有传 `--trust` 或 `--skip-git-repo-check`：Codex 退出 1，未开始 turn，私有 config 摘要和空目录均未改变。OMP 原生 `get_state.dumpTools` 在读验收前后列出了 `read` 和 `report_issue`，未列出 `eval`；实际执行事件只有 `read`。不能把 `--tools read` 这个请求参数误写成完整注册表里只有一个名字。


| 来源 | 首次接受／重复确认 | 实际重放 | 不可据此判断 |
|---|---:|---|---|
| `codex exec --json`，9 行 | 4／4 | `/usr/bin/true` → `succeeded`、exit 0；`/usr/bin/false` → `failed`、exit 1；两次开始事件，均为 `tool:command_execution`、`pinned` | 固定退出码探针临时只许可这两个不读写文件的程序；不是交互批准证据 |
| OMP 私有会话 JSONL，31 行 | 6／6 | 三次 `tool:read`，开始／完成各一；修正后的完成结果依次为 `declined`、`succeeded`、`failed`，均为 `pinned` | 会话中断是回合事实，无对应 invocation，不新增虚构的工具结果 |

两组重复导入均 `accepted=0`、`conflict=0`、`rejected=0`。Codex 另有两条有意区分的证据：非交互 `exec` 请求批准的运行没有 `command_execution` 决议项；在 `turn.started` 后发 SIGINT，exec 退出 1，仅输出 thread/turn 的开始。它们通过同一适配器均产生 0 个事件，因此没有可判断的 replay capability；不能把 RPC 的 `declined`／`interrupted` 补进 exec 输入。第一次普通 `cat` 尝试在嵌套 macOS 沙箱下没有产生命令项，也未计入成功。正式固定命令探针保留外层沙箱和原生 read-only 设置，结束时移除仅用于该次运行的规则。

OMP 的新会话位于本任务自建的空 0700 目录。`get_state` 的初始 `messageCount=0`、返回的会话文件当时不存在；宿主上报模型 `openai-codex/gpt-6.2-astra`。四轮结束后消息数为 14。只在写者运行时检查锁与文件元数据；首次实际写入后租约为 held，正常退出 0 后再证 `held=[]` 且 `unknown=[]`，随后才读文件。原生执行项的 `toolName=read`，并非从模型列表推断。一次控制器把无交互的 `setWidget` 展示通知当成待审批 UI，已停止并保留该失败；仅修正测试控制器，未放行未知对话或信任请求。

### 最小修复与旧数据

- 原代码仅看 `isError`，把拒绝与真实读取失败均记作 `failed`。固定版会话包含匹配工具名和调用 ID 的 `tool_approval_resolved`，可区分 `approved=false, reason="denied by user"` 与无 UI、普通失败或批准后失败。只修正该明确拒绝的完成事件，不使用工具输出正文判断。
- 原版入库的六条事件在旧库仍保留。用新解析器重导入同一原件，得到五条 duplicate、一条 conflict、零新增；回放的旧状态不变。仅在新库得到新语义。不改 schema、去重键、历史库或宿主版本 pin。
- 另用 19.1.0 真实租约 CLI 对本任务合成 ID 构造不可证明的租约，只查询守卫，不打开任何该类会话。宿主返回 `unknown=[目标]`，旧守卫却回答未持有。修正后默认 CLI 退出 2，不读日志、不建库；缺字段和畸形列表同样失败关闭。
- Graft 升级探测单列：在无受管 graph/stamp 的合成项目上实际调用生产 `_proven_project_root` 及两个 `_probe_*` 入口，均为 `unavailable/no-proven-project-root`，未启动真实升级接线。不能由 RPC、导入、旧版本注释或 MCP 测试服务推导 `sbtd_upgrade_hosts.py` 的完整部署兼容性；未安装 Graft、未伪造前置。

### 私有 MCP 行为（任务 3，不是任务 4 接线）

两个宿主分别在新建的合成目录运行同一个 stdio 只读工具 `task3fixture.read_fixture`。服务端 `env -i` 白名单不带宿主凭据变量；输入只能选择固定的 `present` 或 `missing`，分别实际读取标记或触发文件不存在。首轮系统 Python 启动器额外加入 SDK 环境变量，服务端拒绝环境检查，两个宿主均未完成调用；换用不会注入这些键的本地解释器，不放宽白名单。未复制或导出认证文件。

- Codex：通过单次 CLI 参数注册且仅放行此 MCP 工具；非交互 `exec` 不是人工审批。宿主及服务端均记录成功、`ENOENT` 两次调用。真实 exec JSONL → 4 个 `mcp:task3fixture.read_fixture` 事件，完成结果 `succeeded`／`failed`，重复 4、零冲突，重放版本均 `pinned`。
- OMP：官方 `config get mcp.shared` 确认为 `false`，daemon 端点指向不可用作 socket 目录的任务私有路径，采用进程内 MCP host。原生注册和执行名 `mcp__task3fixture_read_fixture`；两个精确调用分别批准，宿主返回标记／工具错误，服务端分别记录 `ok`／`enoent`，宿主退出 0。这次是无会话文件的私有 MCP 运行，不冒充持久化 MCP 日志。任务 4 的 ast-grep、完整 Graft 升级和其他既有 MCP 均未接线。

### 变更与验证门禁

Legacy Change Safety：`characterized`（真实拒绝映射错误与未知租约误判，分别有回归红灯）。Refactoring：`proceed`，复用解析器和现有写入边界。DDIA：`confirmed`，保留旧事件，按原键比较重复／冲突，不回填。`project-validation`：原生 `unittest` 运行 `test_omp_adapter`、`test_codex_adapter`、`test_event_store`、`test_golden_contracts` 共 136 项通过；两份修改的 Python 文件通过 Ruff，生产模块通过 ty。报告命令 `rtk: skipped-for-report`。这些结果针对返修工作树，不能替代新 head 的独审与 CI。

Release Readiness Review：上述两项运行时修复的本地门禁通过；零迁移，未知租约不打开库，重放冲突不覆盖旧数据，既有无决议事件保持原义。另有 40 项仓库工作流契约通过。发布仍被新 SHA 的独审、远端 CI 及后续版本任务门禁约束。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-24T16:37:53.200209+08:00 | planned | in-progress | 当前 Astra 会话：开始任务 3，隔离预检及固定宿主行为验收。 | main b0958078cf8e9d31739bef9cf17e76973f2dfee3 CI 45354457553 13/13 通过，任务 2 本地及远端分支已清除。固定版 OMP 19.1.0（发行制品 SHA256 已校验）、Codex 0.171.0、Bun 1.4.4；原会话 CLI 19.1.1 保留不动。临时域 /Users/lusonglin/TEMP/640-skills-rc2-task3.IL73xkq4，未复制认证。 |
| 2026-11-24T16:41:39.990741+08:00 | in-progress | blocked | 当前 Astra 会话：任务 3 的新隔离 CODEX_HOME 未登录；按认证停止条件关闭 /loop，待本域受控官方认证。 | 固定 OMP 19.1.0、Codex CLI 0.171.0、Bun 1.4.4；已验证 OMP 临时配置读取、Codex app-server config/read 与空 MCP 配置。codex login status：exit 1，Not logged in；原交互终端确认 Loop mode disabled。详见 reports/preflight.json 与 preflight.md。没有复用凭据、发起模型调用或变更全局信任。 |
| 2026-11-24T16:50:20.739682+08:00 | blocked | in-progress | 当前 Astra 会话：用户已授权的任务 3 隔离 Codex 官方登录完成，解除该认证阻断。 | 同一临时 CODEX_HOME 的 codex login 与 login status 均 exit 0；仅保留脱敏回执 reports/codex-login.json。未启动 OMP 登录、模型请求或 /loop。 |
| 2026-11-24T16:59:16.609066+08:00 | in-progress | blocked | 当前 Astra 会话：Codex 隔离真实调用及审批／失败／中断已验证；OMP 独立域尚无可用模型，已关闭循环，等待用户完成本域官方认证。 | Codex 0.171.0：read_fixture 成功与 ENOENT、原生 cksum 审批 decline 与一次性 accept/exit 0、turn/interrupt ACK 和 interrupted；host exit 0。OMP 19.1.0 不可读取 Codex 凭据；只读尝试 exit 1、无工具事件，官方 models 目录为 0 并提示配置认证。见 reports/codex-turns.jsonl、codex-turns.md、omp-readiness.json、omp-readiness.md。未启动 OMP 登录、未推送。 |
| 2026-11-24T17:19:30.007255+08:00 | blocked | in-progress | 当前 Astra 会话：用户已完成独立 OMP 官方登录，恢复固定宿主验收。 | OMP 19.1.0 同一沙箱的 models openai-codex --json --no-extensions 退出 0；十个可用模型含 gpt-6.2-astra。专用 session 目录为空，未读取认证库或正在写入的 session 日志。 |
| 2026-11-24T17:25:45.151680+08:00 | in-progress | checking | 当前 Astra 会话：固定 OMP 的隔离 RPC 行为验收完成，循环已关闭，冻结本地提交内审。 | 新内存会话 4/4：Deny 拒读、Approve Once 读到合成标记、已批准的缺失路径返回工具错误、agent_start 后 abort 获 ACK 与 aborted 终态。22 行脱敏事件；进程 exit 0、退出后无 held/unknown。首轮错误前置断言单独保留。见 reports/omp-turns.md、omp-turns.jsonl 和先前 Codex 同 stem 报告。尚非独审、CI、合入或发布结论。 |
| 2026-11-24T18:18:03.730723+08:00 | checking | in-progress | 当前 Astra 会话：收到 PR #225 完整独审 CHANGES_REQUESTED，按用户授权开始 F1–F7 返修。 | 旧 head 5ed2887700ec9e5b450fd7d0e6ab1742d768763d CI 45365740150 全绿，不证明生产消费链。先采集原生输入和执行导入、重放、能力判断，再补任务私有 MCP 及证据。保留旧 RPC 结果；未重做认证。新现场 review-fix.OUL4auh9 |
| 2026-11-24T18:33:10.723501+08:00 | in-progress | in-progress | Astra 原会话：开始 追补核对 OMP 首轮持久化探针（保留原始失败，不倒填历史） | {"changed_files": [], "evidence_files": [], "sync_files": {}, "validation": ""} |
| 2026-11-24T18:33:20.702385+08:00 | in-progress | in-progress | Astra 原会话：完成 追补核对 OMP 首轮持久化探针（保留原始失败，不倒填历史） | {"changed_files": [], "evidence_files": [], "sync_files": {}, "validation": "原始观测时间 2026-11-24T09:21:13+00:00 至 2026-11-24T09:21:14+00:00；首次写入前 held=false、unknown=false；控制器错误前置断言导致停止，未发 prompt；host exit=0 不等于验收通过。现核对原回执，非本时刻重跑。"} |
| 2026-11-24T19:03:21.375386+08:00 | in-progress | checking | 当前 Astra 会话：完成 F1–F7 本地返修验证；循环已关闭，冻结提交交内审。 | 真实 Codex exec 命令和 MCP、已结束且租约已释放的 OMP 会话均通过生产导入、重复导入、重放与版本判断。修正 OMP 明确拒绝映射、未知租约守卫；旧库保留冲突。两端私有只读 MCP 通过。136 个 runtime 测试、40 个工作流测试及目标 Ruff/ty 通过。详见 reports/review-fix/consumer.md、mcp.md 和同 stem JSON。升级探测仅验证前置不可用；不把宿主或本地证据算成外审、远端 CI 或发布。 |
