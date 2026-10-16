# SBTD Runtime 数据字典（v2.1.0-rc.1 / R1.0）

本字典固定 R1.0 名词。它不改 `task.md` 事实源，也不实现 HTTP 服务。R1.2a 把原始观察写入用户私有 `audit.db`；指标计算仍见 `metrics-catalog.json`，事件形状仍见 `event.schema.json`。

## 事实源

| 名词 | 所有者 | 统计层可以做什么 | 不可以做什么 |
|---|---|---|---|
| 任务 mode／status／history | 有效 `task.md` | 只读投影 | 回放观察事件覆盖任务文件 |
| active task | `active-task.json` 指向的记录 | 引用 | 拥有 mode／status |
| 观察事件 | 用户私有 `audit.db` | 原始记录 | 当成业务授权或法律不可抵赖，或回放覆盖 task.md |
| 指标 | 版本化投影 | 从已接受事件重建 | 用 0 或 mock 填未实现指标 |
| registry／长期凭证 | `SBTD_RUNTIME_HOME` | 用户私有映射 | 写入项目 tracked 文件 |
| capability pin | 本目录 `capability-matrix.json` | 固定验收宿主与兜底完成门决策 | 代替 R1.2b 真实 smoke |

## 标识

ID 是不透明字符串，唯一性不依赖事件时间，也不从 MAC、邮箱、用户名或绝对路径派生。

| 标识 | 含义 |
|---|---|
| `installation_id` / `device_id` | 本地安装与设备。重装后的跨设备关联必须显式建立 |
| `actor_id` | 统计主体。可空。不是 OS 账户、Git 作者或组织认证 |
| `project_id` / `repository_id` / `worktree_id` | 项目、仓库与 checkout。同仓不同 worktree 不合并 |
| `task_uid` / `logical_task_id` | 观察域任务与 SBTD 原完整 ID。冲突时隔离，不按 mtime 选胜者 |
| `task_run_id` | 一次执行轮次。重开可以新 run；续接可以保持同 run |
| `step_run_id` / `attempt_no` | 步骤实例与重试次数 |
| `invocation_id` / `attempt_id` | 逻辑调用与真实尝试。每次真实尝试只计一次 |
| `event_id` / `source_event_id` | 接收事件与来源事件。后者用于幂等 |
| `request_id` | 用量请求。父子汇总与明细共享同一请求时只计一次 |

## 必须分开的状态

| 对象 | 词表 |
|---|---|
| Task | `planned` / `in-progress` / `checking` / `blocked` / `done` |
| TaskRun | `running` / `paused` / `succeeded` / `failed` / `cancelled` / `interrupted` / `unknown` |
| StepRun | `planned` / `running` / `succeeded` / `failed` / `blocked` / `skipped` / `cancelled` / `interrupted` / `unknown` |
| Gate applicability | `required` / `not-required` / `undecided` |
| Gate result | `passed` / `needs-clarification` / `failed` / `unknown`，并保留 reviewer 原词 |
| Evidence | `missing` / `declared` / `present` / `validated` / `stale` / `invalid` / `unknown` |
| Source health | `healthy` / `delayed` / `partial` / `paused` / `unavailable` / `unsupported` |

任务 done、run succeeded、Gate passed、测试 passed、产物 published 不能互相隐式改写。`skill.loaded` 与 `component.available` 不是组件真实调用。组件真实调用只指 Skill 或 Tool 的 `invocation.started` attempt。

## 版本字段

不得用一个 `source_revision` 同时代表工作流、业务提交、任务文件和统计口径。

| 字段 | 所属 |
|---|---|
| `schema_version` | 事件信封，当前 `1.0` |
| `api_version` | HTTP 契约，当前 `1` |
| `metrics_version` | 指标公式，当前 `1.0.0` |
| `projection_version` | 可重建投影。R1.0 只预留 |
| `producer_version` / `parser_version` | 采集器与解析器 |
| `host_version` | 宿主发行版本。验收针只认 capability pin |
| `scope_revision` | 某次 Gate 或验证评价的输入范围 |
| `workflow_source_revision` | 当时的工作流规则 revision，不按新规则重判旧 Gate |
| `source_commit_sha` | 业务仓库完整提交 |
| `worktree_revision` | 已授权工作树身份；dirty 变化也要区分 |
| `task_document_revision` | 读取到的 task.md 字节版本 |

## 去重

1. 有 `source_event_id` 时，键是 `(source_id, source_event_id)`。
2. 同键且规范化内容相同：确认，不重复计数。规范化内容排除 `event_id`、`recorded_at`、`ingest_seq`。
3. 同键且内容不同：conflict，保留先接受的事件，不覆盖。
4. 没有来源事件 ID 时，键是来源、分段、偏移和内容摘要。时间戳本身不够。
5. 同一 `invocation_id` + `attempt_id` 被多个来源观察到时，合并为一个执行对象，保留全部 `source_id`。事件数不是调用数。
6. 同一 `request_id` 同时有父级 rollup 和子级 detail 时，只保留 detail，不把 token 加两次。
7. 无法绑定任务的事件留在未关联集合。禁止按最近任务或相近时间补齐。

## 时间与未知

- 保存带时区的瞬间。查询窗口是 `[from, to)`。
- `occurred_at` 为空时进入时间不可定位集合，不回填导入时间，默认不进入指定窗口。
- 范围前开始、范围内结束的 run 计入相交活动，但不计为范围内新启动。
- 缺少结束且没有可靠中断事实的 run 是 unknown，不是 interrupted，也不是 failed。
- 历史状态按 `occurred_at` 归约，不按入库顺序覆盖更晚发生的状态。
- 执行区间与查询窗口相交的任务计入 touched，但不因此计为窗口内新启动。
- 成功率分母为 0 时是无可判定样本，不是 0% 或 100%。blocked、cancelled、unknown 不藏进成功。
- 日历日长用绝对瞬间相减。同一时区对象的墙上时钟相减会吞掉 DST 偏移变化。

## 条件性用量

token 与费用不是 rc.1 必做指标。来源提供则保留原字段。缺失、`subscription`、`unknown` 必须可见，数值不为 0，也不显示成免费。`cost_status` 为 missing、subscription 或 unknown 时，`cost_amount` 只能是 null。不同币种不相加，不发明汇率。

## 支持边界

rc.1 可计算：任务状态、执行轮次、步骤、Skill／Tool 实际调用、Gate、测试证据、采集健康。§8.2 其余指标留在目录中并标 `unsupported`，查询不得返回 0。单个宿主版本不在 pin 内时，只该宿主标 `unsupported`，不取消指标类别或其他宿主。

## Dify 预留

`tenant_id`、`workspace_id`、`initiated_by`、`requested_by`、`executed_by`、`external_refs`、`trace_id`、`approval_ref` 可以空。空引用不是权限，也不启用远程写入。外部引用不携带密钥或对话正文。
