---
name: trellis-channel
description: Use when the user requests Trellis Channel, multi-agent, worker, forum, parallel review, cross-validation, or when project rules require high-risk code review / validation preflight. Do not spawn workers unless the user has requested or confirmed Channel runtime.
---

# Trellis Channel Skill

当用户明确要求多 Agent、多模型、worker、forum、thread、并行评审、交叉验证、外部 orchestrator 协作，或项目级规则要求高风险代码 review / 验证 preflight 时，使用本 Skill。

`trellis channel` 是显式协作运行时，不是普通 Trellis 工作流的默认入口。

调用本 Skill 做 preflight 不等于启动 Channel runtime。除非用户已明确要求 Channel，或在 preflight 后明确确认，否则不得静默 `spawn` worker。

---

## 核心判断

- 复杂度决定是否进入 Trellis planning。
- 协作形态决定是否启用 Channel。
- 大任务拆分优先使用 parent / child task trees。
- 不要因为任务大、文件多、跨模块或复杂，就自动启用 Channel。
- 不要因为任务复杂就切换到 `channel-driven-subagent-dispatch` workflow。
- 代码 review / 验证审查可以主动触发 Channel preflight；真正启动 runtime 仍需要用户明确要求或确认。

---

## 不应使用 Channel 的场景

- 普通单 Agent 代码修改
- 简单问答
- 小型 bug 修复
- 常规重构
- 添加测试
- 文档修改
- 普通 Trellis 任务
- 仅因为任务复杂
- 仅因为文件较多
- 仅因为任务需要 `prd.md` / `design.md` / `implement.md`
- 仅因为任务需要 parent / child task
- 只是运行 lint / test / build / browser check
- 没有 active Trellis task、没有明确 diff、没有可审查 task artifacts
- 低风险单文件改动，且项目验证命令已经覆盖

---

## 可以主动 Preflight 的场景

以下场景可以主动调用本 Skill 做 preflight：

- 用户要求 code review、提交前 review、测试验证审查、验证覆盖检查、并行评审、交叉验证或多个 reviewer 视角
- `$trellis-check` 或项目验证后仍存在高风险验证缺口
- GitNexus impact / detect_changes 返回 HIGH 或 CRITICAL
- 变更跨越前端、后端、数据库、部署、测试资产、外部服务或发布流程
- 验证失败后经过修复，需要独立复核失败原因、覆盖范围和剩余风险
- Trellis PRD / design / implement 与实际 diff、验证结果或回滚策略需要独立一致性检查

如果用户已明确要求以下协作形态，可以在 preflight 后继续使用 Channel runtime：

- 多 Agent 协作
- 多模型对比
- Claude / Codex / 其他 worker 分工
- 基于 worker 的实现或评审
- forum / thread 式讨论
- 并行评审
- 交叉验证
- 需要跨 worker 保留持久对话记录
- 需要中途向 worker 发送消息
- 需要 interrupt 当前 worker turn
- 需要等待多个 worker 输出
- 外部 orchestrator 管理 worker 生命周期

---

## Preflight 输出

启动 Channel runtime 前，必须先输出 preflight：

- Active task
- Channel goal
- Trigger reason
- Why Channel instead of inline / parent-child task
- Review / validation target
- Proposed worker roles
- Read-only workers
- Writer worker, if any
- Validation controller, if any
- Allowed file areas
- Forbidden actions
- Required inputs
- Expected outputs
- Writeback target
- Stop condition
- Cleanup plan

如果用户未明确要求 Channel runtime，preflight 之后必须询问是否启用，不得直接 spawn worker。

---

## 基本规则

- Channel 不替代 `.trellis/workflow.md`。
- Channel 不替代 `$trellis-before-dev`。
- Channel 不替代 `$trellis-check`。
- Channel 不替代 `$trellis-finish-work`。
- Channel 不替代项目验证命令、GitNexus、Playwright、Maestro、Chrome DevTools MCP、浏览器检查或人工最终判断。
- Channel 结论不会自动成为 `.trellis/spec`。
- Channel runtime / events / forum / thread 记录默认属于本地协作日志。
- Channel 运行时文件默认不要提交到远程仓库。
- `.trellis/agents/<name>.md` 是 Channel agent 定义文件，不是 runtime 日志；如果 workflow 依赖这些定义，应按项目策略保留或提交。
- 如果 `trellis channel spawn` 报告 `Agent '<name>' not found`，或 workflow 引用缺失的 `.trellis/agents/<name>.md`，先运行 `trellis update` 生成 agent 定义，再继续。

长期结论必须整理进入以下位置之一：

- `.trellis/tasks/<task>/prd.md`
- `.trellis/tasks/<task>/design.md`
- `.trellis/tasks/<task>/implement.md`
- `.trellis/spec`，仅当结论属于长期项目规范时

## Review / Validation Runbook

Review Channel 默认只读。适合的 worker 角色包括：

- `architecture-reviewer`
- `test-coverage-reviewer`
- `ui-ux-reviewer`
- `api-data-contract-reviewer`
- `release-risk-reviewer`

Validation Channel 用于验证计划、覆盖率审查和独立复核，不替代主会话运行项目验证。

规则：

- 主会话负责最终运行或确认验证命令。
- worker 可以建议命令，审查 Playwright report / trace、Maestro artifacts、Chrome DevTools MCP 截图 / trace / network 证据、项目测试日志，并指出验证缺口。
- 同一 checkout 不要并行运行会互相影响的验证命令。
- Docker、数据库迁移、浏览器 E2E、Vercel deploy 等环境敏感验证应由主会话串行控制。
- 如果 worker 指出必须修改代码，回到主会话确认后再由唯一 writer 执行。

## Ownership Rules

- Review / validation worker 默认只读。
- 同一 checkout 同一时间只允许一个 writer worker。
- 同一验证环境同一时间只允许一个 validation controller。
- 多个 worker 需要改代码时，优先拆 parent / child tasks 或使用独立 worktree。
- worker 不得 stage、commit、archive、finish-work、push、deploy，除非用户明确授权且该 worker 是唯一 writer / controller。
- worker 输出互相冲突时，由主会话裁决并写明采用 / 拒绝理由。

## Worker Prompt Envelope

发送给 worker 的 prompt 必须包含：

- Active task path
- Current phase
- Relevant `AGENTS.md` hierarchy
- Relevant `prd.md` / `design.md` / `implement.md`
- Relevant `.trellis/spec` 和按需命中的 lessons
- Role and scope
- Forbidden actions
- Output schema

## Worker Output Schema

每个 review / validation worker 必须按以下格式输出：

- Verdict: `pass` / `concerns` / `block`
- Scope reviewed
- Evidence
- Findings
- Required changes
- Optional suggestions
- Validation gaps
- Files referenced
- Confidence
- Should write back to

## Worker Guard

使用 `trellis channel spawn` 时，应遵循 `.trellis/config.yaml` 中的 `channel.worker_guard` 设置。

默认原则：

- 允许 idle worker cleanup 生效。
- 允许 live worker budget 生效。
- 不要无故提高 `--max-live-workers`。
- 不要无故关闭、拉长或绕过 `--idle-timeout`。
- 不要让长期空闲 worker 常驻。
- mid-turn worker 不应被视为空闲 worker。
- 如果用户要求高 reasoning / Ultra 级模型并发运行多个 worker，先在 preflight 中说明用量和费用风险，并优先建议降低并发、缩小 worker scope、改为串行 review，或只为关键 worker 使用高 reasoning。
- 如果 worker 因 idle timeout 被 killed，应在输出中说明。

如需覆盖默认 worker guard，必须有明确理由，例如：

- 用户明确要求长时间驻留 worker
- 外部 orchestrator 需要长期 worker
- 当前任务确实需要多个 worker 并行运行

覆盖后必须说明：

- 覆盖了哪些参数
- 覆盖原因
- 潜在资源风险
- 是否已清理 worker

## Windows Worker Spawn

在 Windows 上运行 Channel worker 时，npm CLI 可能通过 `.cmd` shim 暴露实际 provider 可执行文件。若 `trellis channel spawn`、`run` 或 supervisor 启动失败，并出现 `.cmd`、`.exe`、`spawn`、`ENOENT`、`EACCES`、provider path 或 shell 执行相关错误：

- 先确认 Trellis CLI 已升级，并在项目中运行 `trellis update` 以刷新 Channel runtime / agent 定义。
- 复核 provider CLI 本身可直接执行，例如 `codex --version` 或 `claude --version`，并记录 PATH 中解析到的实际可执行文件。
- 不要为了绕过 `.cmd` shim 问题而把 worker 启动改成任意 `shell: true` 或手写 shell wrapper；优先使用 Trellis 已提供的可 spawn executable 解析能力。
- 如果仍失败，把 provider、Trellis 版本、PATH 解析结果、spawn 错误和 worker config 记录到 task artifacts 或 Channel check summary，再决定是否降级为 inline review / validation。

---

## Message Routing

不要依赖 message tags 做 `send` / `wait` / `run` 路由。

需要定向 worker 时，优先使用：

- 明确的 `to`
- worker inbox policy
- channel events
- 当前 Trellis Channel 支持的显式路由机制

interrupt 必须使用专用 interrupt 流程，不要通过普通 tag 路由模拟。

---

## Codex 多 Agent

- Trellis 多 Agent 工作优先使用 `trellis channel`。
- 普通 Trellis task 使用 Codex inline 主会话完成。
- 不依赖 Codex 内置 `features.multi_agent_v2` 作为 Trellis 主流程。
- 不要在项目级 `.codex/config.toml` 写入 `[features.multi_agent_v2]`。
- Trellis 生成或更新 Codex project config 时，不应生成 `[features.multi_agent_v2]` block；这样可以避免不同 Codex CLI 版本对 structured feature table 的兼容性差异阻塞 Codex 启动。
- 如果项目继承了旧 Trellis 生成的 `[features.multi_agent_v2]` block，优先运行 `trellis update` 重新生成 `.codex/config.toml`，不要手工保留项目级 structured feature table 配置。
- 如确需测试或调优 Codex 内置 multi-agent，仅在确认 Codex CLI 版本兼容后，放到用户级 `~/.codex/config.toml`。
- 除非明确测试该行为，否则不要混用 Trellis Channel 和 Codex 内置 multi-agent。
- 避免递归派发、嵌套子线程或 sub-thread 套娃。

---

## 使用后必须整理

使用 Channel 后，必须将有效结论整理回项目上下文。

最低要求：

- 说明 channel 名称
- 说明 worker 类型
- 说明主要输入
- 说明主要输出
- 说明输出是否已写回 task artifacts 或 .trellis/spec
- 说明是否仍有 worker 存活
- 说明是否已清理 runtime 状态

如果 Channel 只用于临时评审或讨论，且不需要长期保存，应清理或明确说明未清理原因。

---

## 输出要求

任务结束时，如果使用过 Channel，最终输出必须包含：

- Channel 名称
- 使用的 worker / Agent
- 是否发生 interrupt
- 是否有 worker 被 idle timeout killed
- 是否存在未清理 worker
- 关键结论
- 结论写回位置
- 验证结果
- 剩余风险
