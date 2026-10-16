---
schema_version: 1
id: v2.1.0-rc.1-r1.2b-host-adapters
workflow_mode: strict
mode_source: user
mode_note: 用户本次明确要求 SBTD strict mode。
status: "in-progress"
branch: feat/v2.1.0-rc.1-r1.2b-host-adapters
created_at: '2026-10-17T00:21:58.098736+08:00'
updated_at: "2026-10-17T02:20:49.156419+08:00"
completed_at: null
---
交付 v2.1.0-rc.1 的 R1.2b：Codex／OMP 宿主来源适配器，把 Skill／Tool 真实调用事件写入 R1.2a 事件库。产物是宿主 capability matrix 更新与结构化回执。不做 R1.2c 历史导入、R1.3 查询 API、HTTP 服务或 Dashboard。

未完整调用 grill-with-docs。PRD v0.2 第 1379 行、ADR 0001 Q4／Q6、capability-matrix.json 与用户本次交付清单已经固定范围和完成门：两宿主门禁针 `codex@0.163.0` 与 `omp@18.11.1`；真实 smoke 采到 Skill 或 Tool 调用才算通过；omp smoke 由本机真实执行，codex 不安装不运行、由另一 bot 按本任务给出的精确指令执行；omp 不支持时如实标 unsupported，不报 PASS。没有未决产品问题需要访谈。

## 范围

- 新增 `sbtd-runtime/extensions.py`：扩展值规范化。只允许标量（string≤256、number、boolean、null）；嵌套对象压平成 `a.b` 键；数组、超长字符串、非有限数值被丢弃；超过 8 个键时按文档化策略丢弃；#132 的秘密键匹配在入库前先把秘密键丢弃（事件库仍保留整事件拒绝作为第二道防线）。
- 新增 `sbtd-runtime/host_adapter.py`：宿主适配共用核心。按 R1.0 schema 构造事件（installation_id／device_id 由调用方显式给出，不伪造）、调用 `EventStore.append`、返回结构化回执（读取记录数、产出事件数、accepted/duplicate/conflict/rejected、被丢弃扩展键及原因、checkpoint、parser_version）。观察开关关闭时打开被拒，适配器不另造旁路。
- 新增 `sbtd-runtime/omp_adapter.py`：解析 omp 会话 JSONL。assistant 消息的 toolCall 项 → `invocation.started`（read 且 path 为 `skill://` 时记 `skill.loaded`）；toolResult → `invocation.finished`（isError 映射失败，duration 由记录时间戳差得出、wall 基准）。source_event_id 用宿主记录自带 ID。checkpoint 记录文件偏移，重复 ingest 只确认不重复计数。
- 新增 `sbtd-runtime/codex_adapter.py`：解析 `codex exec --json` JSONL。item.started/item.completed 中 command_execution、mcp_tool_call、web_search、collab_tool_call、file_change 映射为 invocation 事件。该流无时间戳：文件重放时 occurred_at=null；stdin 实时管道时可选到达时间戳（文档化）。不安装不运行 codex。
- 场景文件 `sbtd-runtime/spec/r1.2b-host-adapter-scenarios.md`；测试在 `sbtd-runtime/tests/`，CI 入口包装在 `tests/`。
- 更新 `sbtd-runtime/contracts/capability-matrix.json` 的 smoke 状态：omp 用真实 smoke 结果，codex 标 pending（另一 bot 执行）。
- 文档 `sbtd-runtime/docs/host-adapters.md`：适配器用法、扩展丢弃策略、codex@0.163.0 精确 smoke 指令、omp smoke 证据摘要。

## 验收

- 扩展策略有测试：压平、数组丢弃、超长丢弃、秘密键丢弃（含 camelCase／分隔符变体）、超过 8 键按声明顺序丢弃并记录。
- omp 适配器测试：真实形状的 fixture → started/finished/skill.loaded；schema 全通过；端到端入库、重放、重复 ingest 只确认、checkpoint 续传；isError→failed；未知记录跳过；坏行不崩。
- codex 适配器测试：exec JSONL fixture → invocation 事件；文件模式 occurred_at=null；未知 item 类型跳过。
- 开关关闭时适配器不写库（既有等价性测试不破）。
- omp 真实 smoke：`omp@18.11.1` 真实运行采到至少一个 Skill 或 Tool 事件，报告含宿主版本与原始输出片段。不支持则如实记录。
- codex smoke 指令精确到可复制执行，针对 codex@0.163.0。
- `sbtd-runtime/tests`、仓库相关测试与 ruff 通过。

## 测试 seam

公开 seam 是适配器模块的解析与 `ingest` 函数及 CLI 入口，消费方是 R1.2a `EventStore`。不测私有表结构。宿主字段形状以真实观察为准：omp 字段来自本机 18.11.1 真实会话文件；codex 字段以公开 exec JSONL 格式为准，标注未在本机验证。

## Book Gate Plan

| Reviewer | 客观触发／阶段 | Lifecycle | 谓词与结果 |
|---|---|---|---|
| book-ddd-distilled-modeling | 领域术语与规则，需求确认前 | before-dev | confirmed。见正文。未完整 grill。 |
| book-ddia-data-design | 事件入库、checkpoint、回执，设计确认前 | before-dev | confirmed。见正文。 |
| book-legacy-change-safety | 既有开关关闭路径高回归 | before-dev | characterized。不改事件库与 Facade 写入路径；既有等价性测试是安全网。 |
| book-refactoring-pass | 既有生产代码编辑前 | before-dev | not-needed。只新增模块；capability-matrix.json 仅追加 smoke 状态字段。 |
| book-release-readiness | 生产运行时／部署，验证后 | finish | not-needed。无服务、作业、迁移或发布；适配器是显式调用的本地解析器。 |
| TDD | 适配器与扩展策略，实现前 | implement | 先红后绿。 |
| gherkin-bdd | 可观察适配行为 | before-dev | traceable。源仓不生成 .feature。场景在 `sbtd-runtime/spec/r1.2b-host-adapter-scenarios.md`。 |
| ponytail | 实现选型 | implement | stdlib argparse/json；复用 event_store 与 contract_eval；不新依赖。 |

## DDD Boundary Review

Status: confirmed

Ubiquitous language: 宿主适配器把宿主已经记录的结构化事实翻译成 R1.0 观察事件，不制造宿主没有记录的执行。toolCall 记录是宿主观察到的调用开始；toolResult 是终结。`skill.loaded` 只陈述宿主读入了 skill 资源，不陈述方法执行通过。结构化回执陈述一次 ingest 的读取、产出、入库结果与被丢弃扩展键，不是宿主能力证明。capability matrix 的 smoke 状态只有真实 smoke 能改成 pass；parser fixture 不算。omp 不支持时只标 omp 该项 unsupported，不牵连 codex 或指标类别。

Bounded contexts: task.md 仍拥有任务状态；事件库拥有原始事件、去重、checkpoint、质量记录；适配器只拥有“宿主记录 → 事件”的翻译与回执；capability matrix 拥有门禁针与 smoke 状态。适配器不写 task.md、不改 registry、不开 HTTP。

Invariants and business rules: 没有宿主记录就没有事件。扩展值只存标量；放不下的键被丢弃且必须点名记录。秘密键在适配器侧先丢弃，事件库侧仍拒绝残留秘密键。无法绑定任务的事件保持 unlinked，不用最近任务强关联。重复 ingest 只确认。omp 会话文件不在适配器内修改。codex exec 流无时间戳时不伪造 occurred_at。

Core / supporting / generic subdomains: 核心是两个宿主字段形状的忠实映射。支撑是 checkpoint 续传与结构化回执。通用是 JSONL 解析与标量规范化。

Corrections to the grill-with-docs result: none。未完整 grill。

Open conflicts and questions: installation_id／device_id 尚无运行时签发者（PRD §5.2 要求 opaque 随机标识）；本包要求调用方显式传入，不自动签发。omp 会话 JSONL 是否会随版本改字段，本包只对 18.11.1 真实形状负责。codex exec 的 skill 类 item 类型未证实，映射为前向兼容分支，不进 smoke 通过条件。

## DDIA Data Design Review

Status: confirmed

Data owner and source of truth: 宿主会话文件是宿主事实源，适配器只读。事件库仍是已接受事件的事实源。回执不回写宿主。capability matrix 是 smoke 状态事实源。

Write / read / async / failure paths: 适配器逐行读宿主 JSONL，产出事件交给 `EventStore.append`；spool／崩溃恢复语义完全继承 R1.2a。读宿主文件失败、权限不足、宿主目录不存在：回执记为失败原因或抛出明确错误，不产出空成功。坏行跳过并计数，不补造。

Consistency model: 与 R1.2a 相同，单进程读己之写。checkpoint 以 `(source_id, segment_id)` 记录字节偏移；重复 ingest 由偏移跳过 + 去重键双层保证只确认。omp 文件追加写入时只处理完整行，截断尾行留待下次。

Idempotency / ordering / retry / deduplication: source_event_id 取宿主记录自带 ID（omp 记录 id、codex item id+阶段）。入库顺序即 ingest_seq；不按 occurred_at 重排。重试安全。

Schema / migration / backfill / rollback / replay: 无 schema 变更、无回填。不回放覆盖 task.md。

Observability and repair: 回执包含丢弃键清单与每类结果计数。质量记录沿用事件库 accepted/duplicate/conflict/rejected。

Required tests: 端到端入库与重放；重复 ingest 只确认；checkpoint 续传；isError→failed；坏行与未知类型跳过；扩展八条策略各有测试。

## Legacy Change Safety Review

Status: characterized

Behavior to change: 无。本包不改变事件库、Facade、helper 的可观察行为。

Behavior to preserve: 开关关闭时不创建 audit.db／spool；开关开启时 Facade 仍报 gap；去重与恢复语义不变。

Current reproduction evidence: main 3dca103 上 `sbtd-runtime/tests` 71 ok；`tests.test_sbtd_runtime_r1_event_store` 与 `tests.test_sbtd_runtime_r1_facade` 30 ok。

Safety net: 上述既有测试不改断言，作为回归网。适配器测试用独立临时运行时目录。

Hidden dependencies / seam: 适配器复用 `EventStore.open` 的开关检查，不绕过 confirmed。

Validation plan: 实现后跑 `sbtd-runtime/tests`、相关仓库测试与 ruff。

Review mode: normal

## Refactoring Review

Status: proceed

Review mode: normal

Existing-code scope: 不编辑既有生产文件。`event_store.py` 的 `_secret_key` 被导入复用，不改其语义。

Behavior that must remain unchanged: 事件库与 Facade 全部既有行为。

Structural friction: 无。新模块独立。

Decision and smallest safe step: no refactor needed。

Safety net and validation: 既有测试套件。

Deferred refactors: 不把 `_secret_key` 提升为公开 API；适配器以私有导入复用并在文档注明。

## 待确认问题

1. installation_id／device_id 的自动签发归属哪个工作包。本包要求显式传入。
2. omp 会话文件是否算授权读取来源：omp 适配器只读调用方显式给出的会话文件路径，不扫描 HOME。
3. codex exec 流 occurred_at=null 进入“时间不可定位”集合（PRD §8.4.8）；stdin 实时模式可记录到达时间，是否足够 R1.3 统计口径由 R1.3 决定。

## omp@18.11.1 真实 smoke 证据（pass，2026-10-17）

真实运行：在本机以 `omp -p`（omp 18.11.1）执行一次强制 `read` 工具调用的会话，宿主记录落在 `/home/box/.omp/agent/sessions/-tmp-r12b-omp-smoke/2026-10-16T17-06-22-104Z_01a145ad-d318-7734-8b78-7402c5b01884.jsonl`（12 行，cwd `/tmp/r12b-omp-smoke`）。

原始行片段（字段形状证据）：

- toolCall：`"timestamp": "2026-10-16T17:06:28.373Z"`，`"id": "call-d9b26888-01fc-4abd-aa3d-70b9f7840f07-0|fc_f54d5b30-39ec-90ed-8dad-17bd5574bee2_0"`，`"name": "read"`，`"arguments": {"path": "/etc/hostname", ...}`。
- toolResult：`"timestamp": "2026-10-16T17:06:28.400Z"`，`"id": "11aef67c"`，同一 `toolCallId`，`"toolName": "read"`，`"isError": false`。

适配器回执（`omp_adapter.py` 对该真实文件，独立临时 runtime home）：

```json
{"source_id": "omp-session", "host_kind": "omp", "host_version": "18.11.1",
 "parser_version": "omp-session-jsonl-1", "records_read": 12, "records_skipped": 8,
 "events_emitted": 2, "accepted": 2, "duplicate": 0, "conflict": 0, "rejected": 0,
 "dropped": []}
```

重放核对：`invocation.started`（tool:read，occurred_at 2026-10-16T17:06:28.373Z）与 `invocation.finished`（tool:read，succeeded，duration_ms 27，wall）。二次 ingest 回执 `accepted=0, duplicate=2`，重放仍为 2 条（只确认）。capability-matrix.json 的 `smoke.omp` 据此标 `pass`；`smoke.codex` 保持 `pending`，由另一 bot 按 `sbtd-runtime/docs/host-adapters.md` 的 codex@0.163.0 指令执行。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-17T00:22:00.985551+08:00 | planned | in-progress | R1.2b scope is fixed by PRD line 1379, ADR 0001 Q4/Q6, and the user delivery list; failing adapter tests start before adapters exist | docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md:1379 and docs/adr/0001-v2.1.0-rc.1-r1.0-runtime-decisions.md section 6 |
| 2026-10-17T02:20:49.156419+08:00 | in-progress | in-progress | 实现与修复完成：orphan 事件 state.previous=null（omp/codex）、畸形时间戳 occurred_at=null 不拒绝整事件、component_id 超 128 字符跳过并计数、CLI 空 installation_id/device_id 以 exit 2 拒绝不建库；Researchy 附录两条（先压平再做秘密键匹配、`.` 作分词符；>256 字符串只丢字段）已有实现并补测试 | `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest tests.test_sbtd_runtime_r1_host_adapters` → Ran 45 tests, OK（含 test_extensions 18 条） |
| 2026-10-17T02:20:49.156419+08:00 | in-progress | in-progress | 端到端 smoke 复核通过：omp 适配器对真实 smoke 会话文件回执 accepted=2、重复 ingest duplicate=2、重放 2 条；畸形时间戳+orphan 合成会话入库 occurred_at=null、previous=null 且被事件库接受；codex 适配器 orphan item.completed 入库 previous=null；空 identity 两 CLI 均 exit 2 且不建 audit.db。codex@0.163.0 真实 smoke 保持 pending（本仓库不安装不运行 codex） | 本文件「omp@18.11.1 真实 smoke 证据」节；capability-matrix.json smoke.omp=pass / smoke.codex=pending；指令在 sbtd-runtime/docs/host-adapters.md |

## Codex real smoke (box, 2026-10-17 CST)

- Result: **unsupported**
- Version: `codex-cli 0.163.0`
- Cause: ChatGPT backend HTTP 403 / `workspace routing discovery failed`; adapter `events_emitted=0` `accepted=0`; no allowed tool item events
- Evidence: `/workspace/codex-notes/r1.2b-smoke/`
- Matrix: `smoke.codex.status=unsupported`
