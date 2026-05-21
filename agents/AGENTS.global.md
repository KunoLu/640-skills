# Codex 全局规则

## 优先级

- 当前仓库的 `AGENTS.md` 优先于全局规则。
- 当前目录更深层的 `AGENTS.md` 优先于上层规则。
- 项目已有规范、测试、配置和工作流优先于通用假设。
- 不要假设可选工具一定可用。
- 优先采用最小、可验证、可回滚的修改。
- 除非用户明确要求，不要扩大任务范围。

---

## 命令执行规则

- 执行 shell / terminal 命令时，优先使用 `rtk` 前缀。
- 如果 `rtk` 不可用，则回退到原生命令。
- 不要因为 `rtk` 不可用而中止任务。

示例：

```bash
rtk git status
rtk npm run test
rtk pytest
rtk go test ./...
```

---

## 工具可用性判断

只有存在直接或强证据时，才认为某个工具可用。

### Trellis

满足以下任一条件时，认为 Trellis 可用：

- 存在 `.trellis/`
- 存在 `.trellis/workflow.md`
- 存在 `$trellis-*`
- 项目级 `AGENTS.md` 明确说明使用 Trellis

如果 Trellis 可用：
- 调用 `trellis-workflow` Skill。
- 遵循 .trellis/workflow.md。
- 不手动跳过 Trellis 阶段。
- 不绕过项目级 Trellis 规则。

无论 Skill 是否可用，都必须遵守以下最低规则：

- 不要在未读取 `.trellis/workflow.md` 的情况下改变任务状态。
- 不要在未读取相关 `.trellis/spec` 的情况下实现长期规则相关修改。
- 如果存在当前任务产物，优先读取 `prd.md`、`design.md`、`implement.md`。

### GitNexus

GitNexus 通过全局安装的 `gitnexus-mcp` 提供能力，不作为 Skill 管理。

仅当同时满足以下条件时，才使用 GitNexus：

1. GitNexus MCP 可用。
2. 当前项目已建立 GitNexus 索引。

强证据包括：

- MCP 工具列表中存在 GitNexus 相关工具。
- 存在 `.gitnexus/`。
- `gitnexus status` 显示已有索引。
- `gitnexus index` 已经成功执行过。
- 项目级 `AGENTS.md` 明确说明 GitNexus 已启用。

使用规则：

- 修改代码前，优先通过 GitNexus MCP 执行影响分析。
- 修改代码后，优先通过 GitNexus MCP 执行变更检测。
- GitNexus 只作为影响分析和变更验证辅助，不替代 Trellis 任务产物、测试或代码评审。

如果 GitNexus MCP 不可用或项目未建立索引：

- 跳过 GitNexus。
- 不阻塞任务。
- 不假设索引存在。
- 仅在该判断影响任务风险时，在最终输出中说明已跳过。

### agentmemory

agentmemory 只作为 MCP-only 历史上下文层使用，不作为 Skill、hook 或自动会话记录能力来假设。

仅当同时满足以下条件时，才使用 agentmemory：

1. agentmemory MCP 工具可用。
2. 当前任务需要历史上下文。

适合 recall / search 的场景：

- 跨会话持续开发任务。
- 涉及项目架构、业务规则或历史决策。
- 涉及 Trellis workflow、GitNexus、Graphify、TestSprite 等既有使用约定。
- 涉及之前排查过的故障、性能问题、测试问题。
- 用户明确要求参考、沿用、回忆或记住之前内容。

使用规则：

- 任务开始前，如符合条件，先通过 agentmemory MCP recall / search，并简要总结可用上下文。
- agentmemory 返回内容只作为历史线索；当前事实必须以用户正在处理的项目文件、工具输出、测试结果和用户最新指令为准。
- 任务完成后，只有产生长期价值结论时，才通过 agentmemory MCP remember / save。
- 不记录 API Key、密码、token、敏感凭据、个人隐私、临时噪音或无复用价值的过程信息。

如果 agentmemory MCP 不可用，或任务不需要历史上下文：

- 跳过 agentmemory。
- 不阻塞任务。
- 不假设存在历史记忆。

---

## Skills 调用规则

**规则**：相关 Skill 可用且任务场景明确匹配时，优先调用对应 Skill；不可用时直接跳过，不阻塞任务。

不要因为任务简单就跳过已明确匹配的 Skill。  
如果任务场景与 Skill 的使用场景不匹配，或仅存在弱关联，则不要强行调用 Skill。

Skill 不替代项目规范、任务产物、测试和人工判断。  
如果 Skill 与项目 `AGENTS.md`、`.trellis/workflow.md` 或 `.trellis/spec` 冲突，以项目规则为准。

| Skill | 使用场景 | 调用时机 |
|---|---|---|
| `trellis-workflow` | Trellis 生命周期、任务产物、阶段检查 | 发现项目使用 Trellis 后 |
| `trellis-channel` | Trellis Channel / 多 Agent / 多模型协作 | 用户明确要求 Channel、worker、forum、thread、并行评审时 |
| `project-validation` | 判断代码修改后的验证策略 | 修改代码后、执行验证前 |
| `lessons-record` | 记录长期经验教训 | bug 修复、回滚、工具误判、验证失败、上下文丢失后 |
| `spec-plan` | 架构 / 数据模型 / 权限设计 | brainstorm / planning 后、update-spec 前 |
| `ui-ux-pro-max` | UI/UX 修改 | before-dev 前 |
| `git-commit-auto` | 生成提交信息 | finish-work 后 |
| `git-worktree-flow` | 隔离开发环境 | before-dev 前，需要时 |

### 自定义 Skill 使用边界

- `spec-plan`：仅用于需要长期规范沉淀的架构、数据模型、权限、API 或业务规则设计；不要用于一次性实现清单。
- `ui-ux-pro-max`：仅在涉及 UI、交互、布局、视觉、组件体验、前端可用性时调用。
- `git-commit-auto`：仅在任务已完成、验证已执行、准备生成提交信息时调用；不要在开发中途调用。
- `git-worktree-flow`：仅在需要隔离开发、并行任务、风险较高修改或避免污染当前工作区时调用。

### Skill 不可用时

如果相关 Skill 不存在、不可读取或不可执行：

- 直接跳过。
- 不要阻塞任务。
- 按当前 `AGENTS.md`、项目文件、`.trellis/workflow.md`、`.trellis/spec` 和已有上下文继续执行。
- 仅在该 Skill 对任务结果有明显影响时，在最终输出中说明已跳过。

---

## 范围控制

- 不做与任务无关的重构。
- 不在生产代码中引入 mock。
- 除非任务需要，不修改 lock 文件。
- 除非任务与工具配置相关，不修改工具配置。
- 不绕过已有项目工作流文件。
- 不手动跳过 Trellis 阶段。
- 不创建不必要的 parent / child task。
- 不把一次性任务计划写入长期项目规范。
- 不让 Codex 内置 sub-agent dispatcher 替代项目工作流。

---

## 验证最低要求

修改代码后必须进行验证。

验证优先级：

1. 项目级 `AGENTS.md` 中定义的命令。
2. 项目 README / package scripts / Makefile / CI 配置中的命令。
3. `project-validation` Skill 中的默认策略。
4. 根据修改范围选择的聚焦检查。

如果无法执行验证，必须说明：

- 尝试执行的命令
- 失败或跳过的原因
- 已执行的替代检查
- 剩余风险

---

## 上下文控制

仅在上下文污染或过大时使用 `/clear`。

执行 `/clear` 前，必须先总结：

- 当前结论
- 关键决策
- 已完成工作
- 剩余工作
- 下一步
- 当前 Trellis 任务 / 阶段，如果存在

---

## 最终输出规则

实现类任务结束时，必须包含：

- 结论
- 修改的文件
- 验证命令和结果
- 跳过的检查及原因
- 风险或回滚说明

如果相关，再补充：

- Trellis 任务 / 阶段
- GitNexus 状态
- Channel 状态
- Lessons 记录位置

---

## Lessons 规则

出现以下情况时，调用 `lessons-record` Skill：

- bug 修复
- 回滚
- 工具判断错误
- 工作流阶段错误
- 验证失败
- GitNexus 影响分析不匹配
- Channel / worker 上下文丢失

不要在普通任务中滥写 lesson。

---

## 最终目标

保持任务可验证、可维护、最小化、可回滚，并与项目规范一致。
