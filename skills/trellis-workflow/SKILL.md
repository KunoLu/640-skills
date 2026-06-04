---
name: trellis-workflow
description: Use for Trellis workflow tasks, including requirement clarification handoff, reading .trellis/workflow.md, task artifacts, before-dev, check, finish-work, update-spec, workflow template handling, and parent/child task handling. Do not use for non-Trellis projects.
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

## 需求澄清与 PRD 入口

Trellis 负责任务生命周期，不替代需求澄清、领域术语对齐或 PRD 生成。

当用户只给出初始需求，且需求涉及项目领域模型、业务术语、长期规则、现有文档或架构决策时：

1. 在创建或改写 Trellis task artifacts 前，优先使用 `grill-with-docs`。
2. 先读取项目已有文档与相关代码，例如 `docs/CONTEXT.md`、`docs/contexts/<context>/CONTEXT.md`、`docs/adr/`、`.trellis/spec`、README 和相关实现；如果项目已采用根目录 `CONTEXT.md` 或 `CONTEXT-MAP.md`，也一并读取；能从项目事实回答的问题，不要反问用户。
3. 按 `grill-with-docs` 的节奏一次只问一个关键问题，并给出推荐答案。
4. 术语达成长期共识时，才写入项目指定的 context 文档；默认使用 `docs/CONTEXT.md`，多上下文项目使用 `docs/contexts/<context>/CONTEXT.md`；不要新建根目录 `CONTEXT.md`，除非项目已采用该路径或项目规则明确指定；不要把 CONTEXT 写成临时规格书。
5. 只有决策同时满足“难回滚、缺少背景会令人意外、有真实取舍”时，才建议写 ADR；默认写入 `docs/adr/*.md`，多上下文项目写入 `docs/contexts/<context>/adr/*.md`。
6. 达成共识后，先输出需求确认摘要，覆盖目标、用户 / 场景、范围内外、术语、约束、验收标准和未决问题。
7. 用户确认摘要后，再使用 `to-prd` 生成 Markdown PRD；在 Trellis 项目中，PRD 终稿写入或更新 `.trellis/tasks/<task>/prd.md`。
8. PRD 确认后，再使用 `to-issues` 拆成 Trellis-ready vertical slices，标注依赖顺序、AFK / HITL、验收标准和测试策略；拆解结果应落为 `.trellis/tasks/<task>/...` 下的 parent / child task artifacts。
9. 最后按 `.trellis/workflow.md` 创建或选择 task，并继续 Trellis 阶段。

如果需求只是通用方案质询、没有项目文档或领域术语约束，可使用 `grill-me` 替代 `grill-with-docs`。

`$trellis-brainstorm` 可用于 Trellis 内澄清不明确需求，但当需求需要对照项目文档、领域语言或 ADR 时，不替代 `grill-with-docs`。

在需求确认摘要、PRD 或 task artifacts 尚未稳定前，不要执行 `$trellis-before-dev` 或开始实现。

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

## Trellis TDD Workflow 与 `tdd` Skill

Trellis `tdd` workflow 是任务生命周期和阶段编排；`tdd` Skill 是具体实现时的测试先行方法。两者可以组合，但不能互相替代。

当项目实际使用 Trellis TDD workflow，或用户明确要求 Trellis TDD 时：

- 继续按 `.trellis/workflow.md` 执行 Trellis 阶段。
- 开发前仍执行 `$trellis-before-dev`。
- 具体实现中，如 `tdd` Skill 可用，使用 `tdd` 指导 red-green-refactor。
- 开发后仍执行 `$trellis-check` 和项目验证命令。

当项目使用 Trellis `native` workflow 时：

- 不因 `native` workflow 而禁止 `tdd` Skill。
- 仅在 bug 修复、核心业务逻辑、算法、数据转换、同步 / 导入 / 导出、高风险修改或需要回归测试时按需使用 `tdd`。
- 不为简单文案、样式、配置说明或纯文档修改强制使用 `tdd`。

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
- `$trellis-brainstorm`：澄清 Trellis 任务内的不明确需求；需要项目文档和领域术语对齐时，先使用 `grill-with-docs`

## Codex Sub-agent 生成文件排障

Codex 平台的 Trellis sub-agent TOML 由模板和 context prelude injector 共同生成。

如果 `.codex/agents/trellis-check.toml` 或 `.codex/agents/trellis-implement.toml` 中重复出现 `Required: Load Trellis Context First`：

- 优先运行 `trellis update` 重新生成 `.codex/agents/`。
- 不要手工保留或维护重复 prelude。
- 更新后检查每个相关 agent 文件只保留一份 context-loading prelude，并仍能定位 active task、读取 `check.jsonl` / `implement.jsonl` 和 task artifacts。

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
