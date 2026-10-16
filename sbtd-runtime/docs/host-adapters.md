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

## omp 适配器（omp@18.11.1）

来源：omp 会话 JSONL（`~/.omp/agent/sessions/<cwd-slug>/<file>.jsonl`），适配器只读显式给出的路径，不改会话文件、不扫描 HOME。真实字段形状来自本机 18.11.1 会话。映射（parser_version `omp-session-jsonl-1`）：

- assistant 消息的 `toolCall` 项 → `invocation.started`（component `tool:<name>`，occurred_at 取记录时间戳）。
- `read` 且 `arguments.path` 为 `skill://<名>` → 额外产出 `skill.loaded`（component `skill:<名>`；只陈述宿主读入了 skill 资源，不陈述执行通过）。该 read 调用本身仍记 invocation 对。
- `toolResult` → `invocation.finished`（`isError=true` → failed；duration_ms 为记录时间戳差、wall 基准）。
- 参数、输出、消息正文不进事件（observation.level=metadata）。其余记录类型与坏尾行跳过并计数。
- `occurred_at` 只保留符合 schema 的时间戳（RFC 3339 带时区）；畸形时间戳置 null，不拒绝整事件，该调用也不产出 duration。
- toolResult 没有对应已观察 toolCall（orphan）时 `state.previous=null`，不伪造 `running`，也不产出 measurement（schema 无 null measurement，块整体省略）。
- `component_id` 超过 128 字符（schema maxLength）的 toolCall 整体跳过并计数，不产出事件。
- CLI 在 `installation_id`／`device_id` 为空时以 exit 2 + JSON error 拒绝，不创建 audit.db。

用法：

```bash
python3 sbtd-runtime/omp_adapter.py <session.jsonl> \
  --runtime-home "$SBTD_RUNTIME_HOME" \
  --installation-id <opaque-id> --device-id <opaque-id> --confirmed
```

重复 ingest 同一文件：靠 `(source_id, source_event_id)` 去重只确认，不重复计数。

## codex 适配器（codex@0.163.0，smoke 由另一 bot 执行）

来源：`codex exec --json` 的 JSONL（stdin 实时管道或保存的捕获文件）。该流无时间戳，occurred_at 一律为 null（PRD §8.4.8 进入“时间不可定位”集合），recorded_at 为入库时间。流内也没有宿主版本，调用方用 `--host-version` 传入 `codex --version` 的输出。映射（parser_version `codex-exec-jsonl-1`）：

- `item.started` / `item.completed`，item.type ∈ {command_execution, web_search, collab_tool_call, file_change} → component kind `tool`；`mcp_tool_call` → kind `mcp`、component_id `mcp:<server>.<tool>`。
- status：completed→succeeded、failed→failed、declined→declined。exit_code 作为扩展标量保留。
- `thread.started` 提供 session_id；`item.updated`、`turn.*`、`error`、未知 item 类型跳过并计数。
- `item.completed` 没有对应 `item.started`（orphan）时 `state.previous=null`，不伪造 `running`。
- 命令、输出、参数不进事件。CLI 在 `installation_id`／`device_id` 为空时以 exit 2 + JSON error 拒绝。

本仓库不安装不运行 codex。字段形状以公开 exec JSONL 格式（`thread.started` / `item.started` / `item.completed` / `turn.completed`）为准，未在本机验证。

## capability matrix 与 smoke 状态

`contracts/capability-matrix.json` 冻结门禁针 `codex@0.163.0` + `omp@18.11.1`，其他版本 unsupported。`smoke` 节记录每宿主真实 smoke 结果：`pass`（真实运行采到 Skill 或 Tool 调用事件）、`unsupported`（固定版本拿不到结构化调用事件，如实标记）、`pending`（尚未执行）。parser fixture 不算 smoke 证据（ADR 0001 Q6）。

## codex@0.163.0 真实 smoke 指令（另一 bot 执行）

前置：本机已安装 `codex@0.163.0` 且有可用登录（ChatGPT 登录或 API key）。**不要**升级或降级 codex；版本不符则该宿主标 `unsupported` 并停止。

```bash
# 0. 版本钉核对：输出必须含 0.163.0
codex --version

# 1. 独立运行时家目录并开启观察开关
export SBTD_RUNTIME_HOME="$(mktemp -d)/runtime"
python3 - <<'PY'
import json, os
from pathlib import Path
home = Path(os.environ["SBTD_RUNTIME_HOME"])
home.mkdir(mode=0o700, parents=True, exist_ok=True)
(home / "config.json").write_text(json.dumps({
    "schema_version": 1,
    "observation": {"enabled": True, "level": "metadata", "failure_policy": "best-effort"},
}) + "\n")
PY
INSTALLATION_ID="$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
DEVICE_ID="$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"

# 2. 真实运行（强制一次 shell 工具调用），JSONL 既落捕获文件又实时入库
codex exec --json --sandbox read-only \
  "Use the shell tool to run exactly: echo sbtd-r12b-smoke. Then reply with the word done." \
  | tee /tmp/codex-r12b-smoke.jsonl \
  | python3 sbtd-runtime/codex_adapter.py \
      --runtime-home "$SBTD_RUNTIME_HOME" \
      --installation-id "$INSTALLATION_ID" --device-id "$DEVICE_ID" \
      --host-version "$(codex --version)" --confirmed
```

通过判定（全部满足才算 `pass`）：

1. `codex --version` 输出含 `0.163.0`。
2. `/tmp/codex-r12b-smoke.jsonl` 中存在至少一行 `item.started` 或 `item.completed`，其 `item.type` ∈ {command_execution, mcp_tool_call, web_search, collab_tool_call, file_change}（原始行片段记入证据）。
3. 适配器回执（第 2 步 stdout 的 JSON）`events_emitted >= 1` 且 `accepted >= 1`。
4. 重放核对：

```bash
python3 - <<'PY'
import os
from pathlib import Path
import sys
sys.path.insert(0, "sbtd-runtime")
from event_store import EventStore
with EventStore.open(Path(os.environ["SBTD_RUNTIME_HOME"]), read_only=True) as store:
    events = store.replay()
    print(sorted({e["event_type"] for e in events}))
    print([e.get("component") for e in events])
PY
```

输出须含 `invocation.started` 或 `invocation.finished`，且至少一个 component 的 kind 为 `tool` 或 `mcp`。

失败处理：固定版本拿不到结构化调用事件（流里没有 item.* 行、或适配器回执 accepted 为 0）时，把 `capability-matrix.json` 的 `smoke.codex` 标为 `unsupported` 并写明真实原因；不得用 parser fixture 代替，不得报 PASS。通过后把 `smoke.codex` 置为 `pass`，附上 smoke 日期、宿主版本原文与原始输出片段位置。
