---
schema_version: 1
id: v2.2.0-rc.2-host-behavior
workflow_mode: strict
mode_source: user
mode_note: rc.2 PRD；用户授权从任务 2 合入后的 main 开始任务 3。
status: "checking"
branch: test/v2.2.0-rc.2-host-behavior
created_at: '2026-11-24T16:35:41.545526+08:00'
updated_at: "2026-11-24T17:25:45.151680+08:00"
completed_at: null
"blocked_reason": null
---
# 任务 3：新版基础行为与最小兼容调整

输入：任务 2 的 PR [#224](https://github.com/KunoLu/640-skills/pull/224) 已由明确的 admin 授权 squash。许可修复的外审 head 为 `c57ae7efc7326249b23f847f299d7bab90fd6534`，对应 [PR CI](https://github.com/KunoLu/640-skills/actions/runs/45351271714)；当前任务以 squash 后的 `b0958078cf8e9d31739bef9cf17e76973f2dfee3` 为基线，对应独立的 [main CI](https://github.com/KunoLu/640-skills/actions/runs/45354457553)。这不是发布授权。

## 范围与通过标准

在 Air 的原 Astra 实现会话组织隔离进程，分别验证 OMP `19.1.0` 和 Codex `0.171.0`。主会话不是被测 OMP 版本。配置读取、权限和真实审批（含拒绝）、工具装载与实际调用、原生事件、失败及中断需分别取证；版本号、工具清单、未登录回执和上一任务的成功调用均不能代替。

- 仅使用本任务私有 HOME、CODEX_HOME、OMP agent/session、缓存与合成项目。全局认证、信任、真实正在写入的会话日志均不读取、不复制、不迁移。仅允许在获准的隔离域走官方认证。未证明会话归属或出现意外写入立即停。
- 不启用可选 eval，不连接其他 MCP 或共享 daemon；不自动信任未知仓库。先用最小权限，只读取无敏感信息的固定文件，检查工具输入、真实退出码、返回结果和事件。失败／拒绝／中断分别保留原生记录，不用 timeout 代替确认的中断语义。
- 只在原生观察提供具体兼容性缺口后才改适配器。不混入任务 4 的 ast-grep MCP 接线，不提前发布。

## Book Gate Plan

未完整调用 grill-with-docs：PRD 已给定固定版本、范围、负例和停止条件。无新增领域术语或持久化格式设计。若发现真实行为回归，修改前执行 Legacy Safety／Refactoring，先保留旧失败和消费边界；若涉及持久化或跨进程契约，再评估 DDIA。正式结论需真实宿主验收、project-validation；若改到生产路径则再做 release readiness。

## 证据与恢复

脱敏报告仅存本任务 ignored `reports/`。当前 OMP 主角色 GPT-6.2 Astra，精确调用次数未知。保留临时域及失败现场，不清除此前任务 TEMP。身份、真实审批、全局隔离或会话占用不明时记录阻断、关循环、保留现场；不以自动切换模型或复用其他账户恢复。

## 本地验收结果

在同一台 Air 上分别启动固定版本、独立认证域的子进程。Codex `0.171.0` 通过 `app-server --listen stdio://`，实际线程模型为 `gpt-6.2-astra`；OMP `19.1.0` 通过 `--mode rpc --no-session --tools read --approval-mode always-ask-cached`，实际模型为 `openai-codex/gpt-6.2-astra`。控制器只对本次合成夹具作一次性决定，不批准整个目录、会话或后续调用。

| 观察点 | Codex | OMP |
|---|---|---|
| 调用成功和失败 | 客户端注册的 `read_fixture` 实际读到标记；读缺失文件触发 `ENOENT`，宿主工具项为 `failed` | 内置 `read` 一次性批准后读到标记；对缺失路径同样批准后返回工具错误 |
| 原生审批 | 对 `/usr/bin/cksum task3-marker.txt` 分别 `decline` 与 `accept`：前者 `declined`、无退出码，后者 `completed`、退出 0 | 两次读同一标记文件：`Deny` 对应拒绝错误且无标记，`Approve Once` 对应成功及预期内容 |
| 主动中断 | 收到 `turn/started` 后发送 `turn/interrupt`，应答后终态 `interrupted` | 收到 `agent_start` 后发送 `abort`，应答后 `prompt_result.status=aborted`、`sessionSettled=true` |

两端进程均正常退出 0。上述是模型发起工具调用、控制器回应真实审批协议的证据，不代表人工 TUI 点击，也不代表中断了已运行的外部命令。OMP 的独立模型目录在登录后包含目标模型；沙箱禁止 OMP 读取 Codex 的已认证目录。固定二进制、配置读取和认证就绪回执见本任务本地 `reports/`。

首轮 OMP 控制器误把“首次写入前没有持久化租约”判为无法继续：未提交模型提示，已关闭循环，子进程正常退出。固定版只在写入时取得会话锁。最终改用新建私有目录和显式内存会话，启动时验证无历史消息、无会话文件、无 held/unknown ID；没有导入活动日志。首轮结果与最终 `omp-turns.jsonl` 分开保留。

隔离探针不修改全局信任，不加载额外 MCP 或可选 eval。真实配置文件的抽查元数据保持一致；活跃主会话的 OMP 数据库元数据与早期快照不同，未读取内容，也不据此宣称整机无写入。未观察到需要调整本项目适配器的具体缺口；没有产品代码差异。本地验收不代替当前提交内审、独立复核或精确提交 CI。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-24T16:37:53.200209+08:00 | planned | in-progress | 当前 Astra 会话：开始任务 3，隔离预检及固定宿主行为验收。 | main b0958078cf8e9d31739bef9cf17e76973f2dfee3 CI 45354457553 13/13 通过，任务 2 本地及远端分支已清除。固定版 OMP 19.1.0（发行制品 SHA256 已校验）、Codex 0.171.0、Bun 1.4.4；原会话 CLI 19.1.1 保留不动。临时域 /Users/lusonglin/TEMP/640-skills-rc2-task3.IL73xkq4，未复制认证。 |
| 2026-11-24T16:41:39.990741+08:00 | in-progress | blocked | 当前 Astra 会话：任务 3 的新隔离 CODEX_HOME 未登录；按认证停止条件关闭 /loop，待本域受控官方认证。 | 固定 OMP 19.1.0、Codex CLI 0.171.0、Bun 1.4.4；已验证 OMP 临时配置读取、Codex app-server config/read 与空 MCP 配置。codex login status：exit 1，Not logged in；原交互终端确认 Loop mode disabled。详见 reports/preflight.json 与 preflight.md。没有复用凭据、发起模型调用或变更全局信任。 |
| 2026-11-24T16:50:20.739682+08:00 | blocked | in-progress | 当前 Astra 会话：用户已授权的任务 3 隔离 Codex 官方登录完成，解除该认证阻断。 | 同一临时 CODEX_HOME 的 codex login 与 login status 均 exit 0；仅保留脱敏回执 reports/codex-login.json。未启动 OMP 登录、模型请求或 /loop。 |
| 2026-11-24T16:59:16.609066+08:00 | in-progress | blocked | 当前 Astra 会话：Codex 隔离真实调用及审批／失败／中断已验证；OMP 独立域尚无可用模型，已关闭循环，等待用户完成本域官方认证。 | Codex 0.171.0：read_fixture 成功与 ENOENT、原生 cksum 审批 decline 与一次性 accept/exit 0、turn/interrupt ACK 和 interrupted；host exit 0。OMP 19.1.0 不可读取 Codex 凭据；只读尝试 exit 1、无工具事件，官方 models 目录为 0 并提示配置认证。见 reports/codex-turns.jsonl、codex-turns.md、omp-readiness.json、omp-readiness.md。未启动 OMP 登录、未推送。 |
| 2026-11-24T17:19:30.007255+08:00 | blocked | in-progress | 当前 Astra 会话：用户已完成独立 OMP 官方登录，恢复固定宿主验收。 | OMP 19.1.0 同一沙箱的 models openai-codex --json --no-extensions 退出 0；十个可用模型含 gpt-6.2-astra。专用 session 目录为空，未读取认证库或正在写入的 session 日志。 |
| 2026-11-24T17:25:45.151680+08:00 | in-progress | checking | 当前 Astra 会话：固定 OMP 的隔离 RPC 行为验收完成，循环已关闭，冻结本地提交内审。 | 新内存会话 4/4：Deny 拒读、Approve Once 读到合成标记、已批准的缺失路径返回工具错误、agent_start 后 abort 获 ACK 与 aborted 终态。22 行脱敏事件；进程 exit 0、退出后无 held/unknown。首轮错误前置断言单独保留。见 reports/omp-turns.md、omp-turns.jsonl 和先前 Codex 同 stem 报告。尚非独审、CI、合入或发布结论。 |
