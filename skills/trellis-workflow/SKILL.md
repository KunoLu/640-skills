---
name: trellis-workflow
description: Use for Trellis workflow tasks, including reading .trellis/workflow.md, task artifacts, before-dev, check, finish-work, update-spec, workflow template handling, and parent/child task handling. Do not use for non-Trellis projects.
---

# Trellis 工作流 Skill

当仓库使用 Trellis 时，使用本 Skill。

本 Skill 负责 Trellis 生命周期、任务产物、阶段检查、workflow 模板判断、before-dev、check、finish-work、update-spec，以及 parent / child task 处理。

---

## 开始工作前

1. 检查是否存在 `.trellis/`。
2. 读取 `.trellis/workflow.md`。
3. 读取相关 `.trellis/spec`。
4. 如果存在当前活跃任务，读取：
   - `prd.md`
   - `design.md`，如果存在
   - `implement.md`，如果存在

`.trellis/workflow.md` 是当前项目实际生效的 workflow。  
所有 Trellis 阶段判断必须以该文件为准。

---

## Workflow 模板规则

如果 Trellis 支持 workflow templates，可在初始化或后续通过 `trellis workflow` 选择 / 切换 workflow。

默认规则：

- 未经用户明确要求，不主动切换 workflow 模板。
- `native` 可作为默认标准 workflow。
- `tdd` 仅在用户明确要求 TDD，或项目已经采用测试驱动流程时使用。
- `channel-driven-subagent-dispatch` 仅在用户明确要求 Channel / 多 Agent / sub-agent 分发流程时使用。
- 即使存在 `channel-driven-subagent-dispatch` 模板，也不得仅因任务复杂就自动切换或启用该模板。
- 切换 workflow 后，必须重新读取 `.trellis/workflow.md`，并以新文件为准。

判断原则：

- 复杂度决定是否进入 Trellis planning。
- 协作形态决定是否启用 Channel 或 channel-driven workflow。
- 大任务优先考虑 parent / child task，不默认切换到 Channel workflow。

---

## 任务产物

- `prd.md`：需求、约束、验收标准
- `design.md`：技术设计
- `implement.md`：实现计划

当前任务产物优先于通用假设。

`.trellis/spec` 只保存长期项目规则。

不要把以下内容直接写入 `.trellis/spec`：

- 一次性 checklist
- 临时调研
- 本地实现笔记
- 仅当前任务适用的计划

---

## 常用命令

- `$trellis-continue`：恢复中断的工作
- `$trellis-before-dev`：代码修改前执行
- `$trellis-check`：代码修改后执行
- `$trellis-finish-work`：验证通过后执行
- `$trellis-update-spec`：更新长期项目规范
- `$trellis-brainstorm`：澄清不明确需求

---

## 开发前

运行：

```bash
$trellis-before-dev
```

执行该步骤前，不要开始实现。

---

## 开发后

运行：

```bash
$trellis-check
```

检查时必须对照：

- `prd.md`
- `design.md` / `implement.md`，如果存在
- `.trellis/spec`
- 实际代码 diff
- 验证命令结果

不得在未执行 $trellis-check 的情况下完成任务。

---

## 完成任务

运行：

```bash
$trellis-finish-work
```

仅在验证通过后执行。不得在以下情况执行 $trellis-finish-work：

- $trellis-check 未执行
- 验证失败
- task artifacts 与实际实现不一致
- .trellis/spec 中的长期规则未被满足

---

## 更新规范

仅当任务改变以下内容时，使用 `$trellis-update-spec`：

- 架构
- API
- 数据模型
- 权限
- 业务规则
- 长期技术约定
- 需要跨任务复用的项目规则

不要用于：

- 一次性 checklist
- 临时调研
- 本地实现笔记
- 仅当前任务适用的计划
- 尚未确认的设计想法

---

## Parent / Child Task

当工作过大、跨模块、跨阶段，或无法独立作为单个任务验证时，使用 parent / child task。

parent task 用于记录：

- 整体目标
- 范围
- 约束
- 阶段计划
- 最终验收策略

每个 child task 必须满足：

- 可以独立实现
- 可以独立测试
- 可以独立检查
- 有清晰边界
- 有明确验收标准

不要创建无法独立验证的 child task。

child task 完成后，应根据需要汇总回 parent task。

---

## 禁止事项

本 Skill 只保留 Trellis workflow 相关的最低禁令；其他约束遵循项目级 `AGENTS.md`。

- 不要绕过 `.trellis/workflow.md` 或手动跳过 Trellis phase。
- 不要在未执行 `$trellis-before-dev` 的情况下开始实现。
- 不要在未执行 `$trellis-check` 或验证未通过时执行 `$trellis-finish-work`。
- 不要把一次性任务计划、临时调研、本地实现笔记写入 `.trellis/spec`。
- 不要仅因任务复杂就切换 workflow 模板，尤其不要自动切换到 `channel-driven-subagent-dispatch`。