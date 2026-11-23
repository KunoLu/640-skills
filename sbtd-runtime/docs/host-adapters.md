# R1.2b 宿主来源适配器：omp 与 codex

`sbtd-runtime/omp_adapter.py` 与 `sbtd-runtime/codex_adapter.py` 把宿主已经记录的结构化事实翻译成 R1.0 观察事件（`contracts/event.schema.json`），写入 R1.2a 事件库（`event_store.py`）。适配器不制造宿主没有记录的执行，不写 task.md，不绕过观察开关；开关关闭时 `EventStore.open` 拒绝，适配器报错退出。

共用核心在 `host_adapter.py`：事件骨架、结构化回执（`IngestReceipt`）。回执陈述一次 ingest 的真实结果（读取记录数、跳过数、产出事件数、accepted/duplicate/conflict/rejected、被丢弃扩展键、checkpoint、parser_version）。**回执不是宿主能力证明**；capability matrix 的 smoke 状态只由真实 smoke 更新。

`installation_id` / `device_id` 是调用方显式参数（opaque 随机标识，PRD §5.2）。当前没有任何运行时组件自动签发它们，适配器拒绝伪造。

## 扩展值策略（extensions.py）

schema 约束：最多 8 个键，值只能是 string（≤256）、number、boolean、null。规范化与丢弃策略（与 `spec/r1.2b-host-adapter-scenarios.md` 一致，每条有测试）：

1. 嵌套对象压平成点连接键（`{"a": {"b": 1}}` → `a.b`）。
2. 数组整体丢弃（`dropped-array`），不压平。
3. 字符串超过 256 字符丢弃（`dropped-too-long`），不截断。
4. 非有限数值丢弃（`dropped-non-finite`）。
5. 其他非标量值丢弃（`dropped-unsupported`）。
6. 命中 #132 秘密键匹配的键丢弃（`dropped-secret`）；匹配在压平之后进行，`.` 视为分词符（`a.github_token` 也会命中）。事件库的整事件拒绝仍是第二道防线。
7. 超过 8 键时：先按调用方声明的 priority 顺序保留，其余按字母序，第 9 个起丢弃（`dropped-over-limit`）。

所有丢弃都进入回执的 `dropped` 清单（键名 + 原因）。

## omp 适配器（当前门禁 omp@19.1.0；旧版本保留为历史实测）

来源：omp 会话 JSONL，适配器只读显式给出的路径，不改会话文件、不扫描 HOME。真实字段形状来自历史会话；19.1.0 于 2026-11-23 完成 Air 隔离基础调用与入库／重复导入实测，适配器逻辑不变。映射（parser_version `omp-session-jsonl-1`）：

- assistant 消息的 `toolCall` 项 → `invocation.started`（component `tool:<name>`，occurred_at 取记录时间戳）。
- `read` 且 `arguments.path` 为 `skill://<名>` → 额外产出 `skill.loaded`（component `skill:<名>`；只陈述宿主读入了 skill 资源，不陈述执行通过）。该 read 调用本身仍记 invocation 对。
- `toolResult` → `invocation.finished`（`isError=true` → failed；duration_ms 为记录时间戳差、wall 基准）。
- 参数、输出、消息正文不进事件（observation.level=metadata）。其余记录类型与坏尾行跳过并计数。
- `occurred_at` 只保留符合 schema 的时间戳（RFC 3339 带时区）；畸形时间戳置 null，不拒绝整事件，该调用也不产出 duration。
- toolResult 没有对应已观察 toolCall（orphan）时 `state.previous=null`，不伪造 `running`，也不产出 measurement（schema 无 null measurement，块整体省略）。
- `component_id` 超过 128 字符（schema maxLength）的 toolCall 整体跳过并计数，不产出事件。
- CLI 在 `installation_id`／`device_id` 为空时以 exit 2 + JSON error 拒绝，不创建 audit.db。
- 读取前 lease 守卫：文件名携带会话 id（`<时间戳>Z_<uuid>.jsonl`）时，CLI 先执行 `omp session lease --json -- <id>`；id 在 held 列表（运行中 omp 持有、可能正在写）→ exit 2 + JSON error 拒绝读取，不打开事件库；探测失败（CLI 不可用／超时／非零退出／输出不可解析）→ 失败关闭，exit 2 + JSON error。文件名不含会话 id 的外来文件（pack／复制）不适用该守卫；`--no-lease-check` 显式跳过。lease 是即时建议性信号，不消除检查后 omp 开始写入的竞态窗口；重复 ingest 的去重语义不受影响。

18.19.0 的其他记录类型（统计来源：2026-11-13 对 16 个真实 18.19.0 会话文件、共 2751 行的实测）逐类核对过，跳过并计数是有意设计：

- `title`（无 id，仅 v/title/updatedAt/pad）：只有会话标题，无执行事实。
- `model_change`、`thinking_level_change`：宿主配置事实，R1.0 事件模型没有对应事件类型；其 `runtime.version` 已用于填 host_version。
- `custom`：四种 customType——`tool_execution_start` 与 toolCall 记录重复；`session_exit` 无对应事件类型；`date-cwd-reminder`、`system-prompt-digest` 属提示内部。
- `custom_message`：宿主展示层消息，无执行事实。
- `role=user` 消息：metadata 观察级别不采提示正文。

18.19.0 形状细节：session 头 version 3 且无 runtime 键（version 不参与校验，只取 id）；toolCall 项多一个 intent 键，id 不含「|」；thinking 块带 thinkingSignature；toolResult 的 message 多 content/details/timestamp 键。这些差异不改变映射。

用法：

```bash
python3 sbtd-runtime/omp_adapter.py <session.jsonl> \
  --runtime-home "$SBTD_RUNTIME_HOME" \
  --installation-id <opaque-id> --device-id <opaque-id> --confirmed
  # 可选：--no-lease-check 显式跳过 lease 守卫
```

重复 ingest 同一文件：靠 `(source_id, source_event_id)` 去重只确认，不重复计数。

### omp@19.1.0 当前基础 smoke（pass，2026-11-23）

Air 本机，独立 HOME、PI_CODING_AGENT_DIR、session-dir、缓存、临时目录与受控测试项目均位于本任务 TEMP。用户通过官方登录取得隔离认证，不复制主会话凭据；原 Astra 实现会话未变。

`omp -p --mode json` 显式使用 `openai-codex/gpt-6-astra`、仅允许 read，审批模式 `always-ask`。2026-11-23T05:10:59Z–05:11:04Z，进程 exit 0，真实读取 `probe.txt`。已结束会话 lease 的 held／unknown 均为空，13 行会话被原适配器读取、跳过 9 行、产出并接受 2 条事件；重复导入 accepted=0、duplicate=2，conflict/rejected 均为 0。

此前无凭据启动的 exit 1 保留为失败。该结果只证明基础调用、采集与重放路径，不证明完整审批、MCP、失败与中断矩阵已通过。命令、私有证据与限制见[任务 1](../../ai/tasks/v2.2.0-rc.2-baseline/task.md)。

### omp@18.19.0 历史 smoke（pass，2026-11-12）

来源：**云主机实测**。`omp --version` → `omp/18.19.0`，2026-11-12 18:51:03–18:51:17 +08:00，退出码 0、stdout `done`。模型 kimi-code/k3:max；强制一次 read 工具调用，再将会话文件交给 `omp_adapter.py`。

会话 12 行，sha256 `c5f79ec94f0cedcdbde4eabb472124bd7ea030e5e9457a56df5abeea012116a0`；第 1 行 type=title 且无 id（18.19.0 新出现），第 2 行 session 头 version 3；toolResult 的 toolName=read、isError=false。

`omp_adapter.py`（main `a70f270`）回执：records_read=12，records_skipped=8，events_emitted=2，accepted=2，duplicate=0，conflict=0，rejected=0，dropped=[]；重复导入 accepted=0、duplicate=2。

当时旧矩阵把 18.19.0 判为 unsupported、18.18.8 判为 pinned；rc.1 换针后两者分类反转，不改变实测事实。rc.2 当前 pin 为 19.1.0，这两版均为历史。

### omp@18.18.8 历史 smoke（pass，2026-11-11）

来源：**云主机实测**。`omp --version` → `omp/18.18.8`，14:40:30–14:40:38 +08:00，退出码 0、stdout `done`。会话 13 行，session header version 3，runtime.version=18.18.8；第 8 行 read toolCall，第 11 行同 toolCallId 的 toolResult，isError=false；新类型 `credential_pin` 按未知类型跳过计数。回执 records_read=13、records_skipped=9、events_emitted=2、accepted=2、duplicate/conflict/rejected=0、dropped=[]；重复导入 accepted=0、duplicate=2。完整记录见 `ai/tasks/v2.1.0-rc.5-host-gate-codex-0167-omp-18188/task.md`，矩阵保留于 `smoke_history.omp`；历史 pass 不等于当前 pinned。

### omp@18.11.1 历史 smoke（pass，2026-10-17）

来源：**云主机实测**。`omp -p` 强制 read，12 行会话；回执 records_read=12、records_skipped=8、events_emitted=2、accepted=2、duplicate/conflict/rejected=0、dropped=[]。重放 `tool:read` 的 started/finished，succeeded、duration_ms=27（wall）；重复导入 accepted=0、duplicate=2，重放仍为 2 条。原始字段片段及回执见 `ai/tasks/v2.1.0-rc.1-r1.2b-host-adapters/task.md`，矩阵保留于 `smoke_history.omp`；历史 pass 不等于当前 pinned。

## codex 适配器（当前门禁 codex@0.171.0）

来源：`codex exec --json` 的 JSONL（stdin 实时管道或保存的捕获文件）。该流无时间戳，occurred_at 一律为 null（PRD §8.4.8 进入“时间不可定位”集合），recorded_at 为入库时间。流内也没有宿主版本，调用方用 `--host-version` 传入 `codex --version` 的输出。映射（parser_version `codex-exec-jsonl-1`）：

`codex --version` 的原文（例如 `codex-cli 0.171.0`）仍可直接传给 `--host-version`。Codex 解析入口只去掉外围空白和官方 `codex-cli ` 标识，事件与回执统一得到 `0.171.0`；裸版本输入保持不变，预发布后缀不丢弃。能力比较器继续精确匹配，不通过别名或默认当前版本放行旧版、unknown、alpha、beta 或 RC。

parser_version 仍表示 `codex-exec-jsonl-1` 的 JSONL 映射格式；具体实现另以 Git SHA 和适配器文件 SHA-256 识别。旧库中已经保存的 raw-version 事件不自动改写；用修复后的规范化结果重导入相同 source_event_id，可能按既有规则报告 conflict 并保留旧事件。需要重算旧捕获时显式选择新观察库，不覆盖原库或删除失败证据。

- `item.started` / `item.completed`，item.type ∈ {command_execution, web_search, collab_tool_call, file_change} → component kind `tool`；`mcp_tool_call` → kind `mcp`、component_id `mcp:<server>.<tool>`。
- status：completed→succeeded、failed→failed、declined→declined。exit_code 作为扩展标量保留。
- `thread.started` 提供 session_id；`item.updated`、`turn.*`、`error`、未知 item 类型跳过并计数。
- `item.completed` 没有对应 `item.started`（orphan）时 `state.previous=null`，不伪造 `running`。
- 命令、输出、参数不进事件。CLI 在 `installation_id`／`device_id` 为空时以 exit 2 + JSON error 拒绝。

默认单元测试不安装或运行 codex。0.171.0 已于 2026-11-23 完成 Air 隔离基础调用与入库／重复导入实测；0.167.1 云主机证据保留在下方历史节，不用于当前通过判定。

## capability matrix 与 smoke 状态

`contracts/capability-matrix.json` 当前门禁针为 `codex@0.171.0` + `omp@19.1.0`，其他版本 unsupported。`pinned` 只表示版本匹配，不是验收通过。rc.2 要求两个宿主均有本轮 Air 隔离真实调用证据，并完成所有适用验收；旧 R1 至少一个宿主通过的兜底仅作历史。`failed`、`unsupported`、`unknown`、`pending` 均不得当作 PASS。

`smoke` 记录当前基础冒烟，`smoke_history` 按宿主以数组保留旧证据。基础 smoke pass 不代表整版发布就绪；任务 3 的权限／审批、MCP、失败和中断矩阵须另行验收。旧版本、旧主机和 parser fixture 不能替代本轮证据。

## 当前固定版本的隔离 smoke

开始前核对 `omp --version` 为 `omp/19.1.0`、`codex --version` 为 `codex-cli 0.171.0`、Bun 满足 `>=1.4.4`；不符或未知则阻断，不跟随 latest。只在获准的临时根内准备 HOME、agent、CODEX_HOME、session-dir、缓存和受控测试项目。账号只通过单独获准的官方登录流程使用，不复制 auth.json／agent.db，不更换原实现会话模型。

本轮 `$SMOKE_ROOT` 位于用户指定的 `$HOME/TEMP/`。以下命令要求其子目录与仅含 `sbtd-rc2-task1-isolated-smoke` 的 `probe.txt` 已准备好；登录须先获授权。它们是临时测试进程，不是新的实现主会话。

```bash
HOME="$SMOKE_ROOT/isolated/codex-user-home" \
CODEX_HOME="$SMOKE_ROOT/isolated/codex-home" \
TMPDIR="$SMOKE_ROOT/tmp" TMP="$SMOKE_ROOT/tmp" TEMP="$SMOKE_ROOT/tmp" \
XDG_CACHE_HOME="$SMOKE_ROOT/cache" \
codex exec --json --ephemeral --ignore-user-config --ignore-rules \
  --sandbox read-only -c 'approval_policy="never"' --model gpt-6-astra \
  --cd "$SMOKE_ROOT/isolated/probe-project" --skip-git-repo-check \
  'Use the shell tool exactly once to run: cat probe.txt . Do not write files or use network tools.'
```

`--skip-git-repo-check` 只用于本轮自行建立的受控测试目录，不添加信任；不得使用 `--trust`。`approval_policy=never` 不证明真实审批允许／拒绝。OMP 对应调用在该受控目录内执行：

```bash
env -u OMP_PROFILE -u PI_PROFILE -u PI_CONFIG_DIR -u PI_SESSION_ID \
  -u ORCA_TERMINAL_HANDLE \
  HOME="$SMOKE_ROOT/isolated/omp-home" \
  PI_CODING_AGENT_DIR="$SMOKE_ROOT/isolated/omp-agent" \
  TMPDIR="$SMOKE_ROOT/tmp" TMP="$SMOKE_ROOT/tmp" TEMP="$SMOKE_ROOT/tmp" \
  XDG_CACHE_HOME="$SMOKE_ROOT/cache" \
  omp -p --mode json --model openai-codex/gpt-6-astra --tools read \
  --no-extensions --no-skills --no-rules --no-context-files --no-lsp \
  --no-title --no-judge --no-spotlight --offline \
  --session-dir "$SMOKE_ROOT/isolated/omp-sessions" \
  --approval-mode always-ask --max-time 90 \
  'Use the read tool exactly once on probe.txt. Do not write files or use network tools.'
```

分别捕获 stdout、stderr、起止时间与进程退出码，再执行适配器；不要用管道末端成功冒充宿主成功。OMP 仅消费该测试进程已结束、lease 未占用的会话文件，不读取原实现主会话活动日志。观察库使用隔离的 `SBTD_RUNTIME_HOME`，按[使用说明](install-and-use.md#可选启用与项目授权)显式启用 metadata 观察。

通过判定：固定版本匹配、宿主进程 exit 0、实际 Skill／Tool 调用成功、适配器接受对应事件，重复导入不新增事件，重放可见预期 component。任一关键项未知或失败均不通过；失败证据保留，不能把更新矩阵本身当作验证。验收结束保留必要证据，临时目录与认证存储按已确认清理清单处理，不删除其他目录。

### codex@0.171.0 当前基础 smoke（pass，2026-11-23）

Air 本机原基础 smoke 于 2026-11-23T04:50:56Z–04:51:09Z 完成，但当时未覆盖官方版本原文到能力消费者的完整链路；独立复核 F1 指出该缺口。修复后于 2026-11-23T08:40:23Z–08:40:38Z 重新执行隔离 Codex 调用，显式模型 `gpt-6-astra`，真实 `cat probe.txt` 与宿主进程均 exit 0。官方版本输出为 `codex-cli 0.171.0`；7 行捕获由修复后的原生 CLI 读取、跳过 4 行、产出并接受 2 条事件，回执与重放事件 host_version 均为 `0.171.0`，能力消费者得到 pinned。重复导入 accepted=0、duplicate=2、conflict/rejected=0。旧库与旧报告保留；可交付的脱敏原生片段、退出码、回执、重放与哈希随[任务 1](../../ai/tasks/v2.2.0-rc.2-baseline/task.md)的 E1 证据单独交接，不以本地文件存在代替独审核验。

### codex@0.167.1 历史 smoke（pass，2026-11-11）

来源：**云主机实测**，CodeX bot 执行。`codex --version` → `codex-cli 0.167.1`，开始于 14:36:15 +08:00；在 main `80f1426` 只读副本上以 `codex exec --json --sandbox read-only` 执行 `echo sbtd-r12b-smoke`。

JSONL 共 7 行：thread.started、turn.started、item.completed(agent_message)、item.started(command_execution)、item.completed(command_execution, exit_code=0, status=completed)、item.completed(agent_message "done")、turn.completed。回执 source_id=codex-exec、host_version=`codex-cli 0.167.1`、parser_version=codex-exec-jsonl-1、records_read=7、records_skipped=4、events_emitted=2、accepted=2、duplicate/conflict/rejected=0、dropped=[]。重放 `invocation.started` + `invocation.finished`，component `tool:command_execution`（kind tool）。

运行完成；工具命令 exit_code=0，但进程退出码未单独记录，未知。使用全局默认模型，JSONL 未记录模型名，未知；1 turn。这是 codex 首次真实冒烟通过。2026-10-17 的 0.163.0 因 ChatGPT 后端 HTTP 403／workspace routing discovery failed 未采到事件，unsupported 记录保留在矩阵 `smoke_history.codex` 与 `ai/tasks/v2.1.0-rc.1-r1.2b-host-adapters/task.md`。
