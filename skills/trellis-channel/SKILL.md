---
name: trellis-channel
description: Use only when the user explicitly requests Trellis Channel, multi-agent, multi-model, worker, forum, thread, or parallel review collaboration. Do not use for normal single-agent Trellis work.
---

# Trellis Channel Skill

仅当用户明确要求多 Agent、多模型、worker、forum、thread、并行评审，或外部 orchestrator 协作时，使用本 Skill。

`trellis channel` 是显式协作运行时，不是普通 Trellis 工作流的默认入口。

---

## 核心判断

- 复杂度决定是否进入 Trellis planning。
- 协作形态决定是否启用 Channel。
- 大任务拆分优先使用 parent / child task trees。
- 不要因为任务大、文件多、跨模块或复杂，就自动启用 Channel。
- 不要因为任务复杂就切换到 `channel-driven-subagent-dispatch` workflow。

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

---

## 可以使用 Channel 的场景

仅当用户明确要求以下场景时，才使用 Channel：

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

## 基本规则

- Channel 不替代 `.trellis/workflow.md`。
- Channel 不替代 `$trellis-before-dev`。
- Channel 不替代 `$trellis-check`。
- Channel 不替代 `$trellis-finish-work`。
- Channel 结论不会自动成为 `.trellis/spec`。
- Channel runtime / events / forum / thread 记录默认属于本地协作日志。
- Channel 运行时文件默认不要提交到远程仓库。

长期结论必须整理进入以下位置之一：

- `.trellis/tasks/<task>/prd.md`
- `.trellis/tasks/<task>/design.md`
- `.trellis/tasks/<task>/implement.md`
- `.trellis/spec`，仅当结论属于长期项目规范时

## Worker Guard

使用 `trellis channel spawn` 时，应遵循 `.trellis/config.yaml` 中的 `channel.worker_guard` 设置。

默认原则：

- 允许 idle worker cleanup 生效。
- 允许 live worker budget 生效。
- 不要无故提高 `--max-live-workers`。
- 不要无故关闭、拉长或绕过 `--idle-timeout`。
- 不要让长期空闲 worker 常驻。
- mid-turn worker 不应被视为空闲 worker。
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
- 除非明确测试该行为，否则不要混用 Trellis Channel 和 Codex 内置多 Agent。
- 避免递归派发或嵌套子线程。

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
