<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **keyboy-play** (1749 symbols, 2965 relationships, 57 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/keyboy-play/context` | Codebase overview, check index freshness |
| `gitnexus://repo/keyboy-play/clusters` | All functional areas |
| `gitnexus://repo/keyboy-play/processes` | All execution flows |
| `gitnexus://repo/keyboy-play/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.agents/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.agents/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.agents/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.agents/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.agents/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.agents/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

---

# Codex 项目规则

## 项目工作流

本项目使用 Trellis 作为主要项目工作流。

执行 Trellis 相关任务时：

- 调用 `trellis-workflow` Skill。
- 读取 `.trellis/workflow.md`。
- 读取相关 `.trellis/spec`。
- 如果存在当前活跃任务，读取对应任务产物：
  - `prd.md`
  - `design.md`
  - `implement.md`

不要在未执行 `$trellis-before-dev` 的情况下开始代码修改。  
不要在未执行 `$trellis-check` 的情况下完成任务。  
只有验证通过后，才执行 `$trellis-finish-work`。

### Trellis Workflow 模板规则

- `.trellis/workflow.md` 是当前项目实际生效的 workflow，所有 Trellis 阶段判断以该文件为准。
- 如果 Trellis 支持 workflow templates，可在初始化或后续通过 `trellis workflow` 选择 / 切换 workflow。
- 未经用户明确要求，不主动切换 workflow 模板。
- `native` 可作为默认标准 workflow。
- `tdd` 仅在用户明确要求 TDD，或项目已经采用测试驱动流程时使用。
- `channel-driven-subagent-dispatch` 仅在用户明确要求 Channel / 多 Agent / sub-agent 分发流程时使用。
- 即使存在 `channel-driven-subagent-dispatch` 模板，也不得仅因任务复杂就自动切换或启用该模板。
- 切换 workflow 后，必须重新读取 `.trellis/workflow.md`，并以新文件为准。

### Trellis 执行规则

- 不要绕过 `.trellis/workflow.md`。
- 不要手动跳过 Trellis phase。
- 不要在未执行 `$trellis-before-dev` 的情况下开始代码修改。
- 不要在未执行 `$trellis-check` 的情况下完成任务。
- 只有验证通过后，才执行 `$trellis-finish-work`。
- 不要把一次性任务计划写入 `.trellis/spec`。
- 长期规范、架构决策、业务规则变化，才应沉淀到 `.trellis/spec`。
- 当前任务的临时计划、实现 checklist、阶段性讨论，应优先写入对应 task artifacts。

---

## GitNexus

本项目可以使用 **GitNexus** 进行影响分析和变更检测。

GitNexus 能力通过全局安装的 `gitnexus-mcp` 提供，**不作为 Skill 调用**。

### 使用条件

仅当以下条件满足时使用 GitNexus：

- GitNexus MCP 可用。
- 当前项目已建立 GitNexus 索引。
- 存在 `.gitnexus/`，或 `gitnexus status` 确认已有索引。

### 使用规则

当任务涉及非轻微代码影响时：

- 修改前通过 GitNexus MCP 执行影响分析。
- 修改后通过 GitNexus MCP 执行变更检测，如果可用。
- 将 GitNexus 结果与以下内容交叉核对：
  - 实际代码 diff
  - 测试结果
  - Trellis 任务产物
  - `.trellis/spec`

如果 GitNexus MCP 不可用，或当前项目未建立索引：

- 跳过 GitNexus。
- 不阻塞任务。
- 不手动假设影响范围。
- 使用代码阅读、测试和 diff 检查作为替代验证方式。

---

## Trellis Channel

普通任务不要使用 `trellis channel`。

### 核心判断

- 复杂度决定是否进入 Trellis planning。
- 协作形态决定是否启用 Channel。
- 大任务拆分优先使用 parent / child task trees。
- 不要因为任务大、文件多、跨模块或复杂，就自动启用 Channel。
- 不要因为任务复杂就切换到 `channel-driven-subagent-dispatch` workflow。

### 允许使用场景

仅当用户明确要求以下场景时，才使用 `trellis channel`：

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

如果需要使用 Channel：
- 必须调用 `trellis-channel` Skill。
- 不要仅因任务复杂就启用 Channel。

---

## 目录规则

保留或按项目策略提交：

- `.trellis/spec/`
- `.trellis/workflow.md`
- `.trellis/tasks/<task>/prd.md`
- `.trellis/tasks/<task>/design.md`
- `.trellis/tasks/<task>/implement.md`

不要提交：

- `.trellis/.developer`
- `.trellis/.runtime/`
- `.trellis/.cache/`
- `.trellis/worktrees/`
- `.trellis/.backup-*`
- `.trellis/channels/`
- `~/.trellis/channels/`
- `.gitnexus/`

---

## 验证命令

优先使用本项目已有命令。

### Node / JavaScript / TypeScript

```bash
rtk npm run lint
rtk npm run test
rtk npm run build
```

如果 `rtk` 不可用，回退为：

```bash
npm run lint
npm run test
npm run build
```

### Python

```bash
rtk ruff check .
rtk ruff format .
rtk ty check .
rtk pytest
```

如果 `rtk` 不可用，回退为：

```bash
uv run ruff check .
uv run ruff format .
uv run ty check .
uv run pytest
```

### Go

```bash
rtk go test ./...
```

如果 `rtk` 不可用，回退为：

```bash
go test ./...
```

如需判断修改范围对应的验证策略，调用 `project-validation` Skill。

---

## 项目特殊约束

- 不要绕过 `.trellis/workflow.md`。
- 不要把一次性任务计划写入 `.trellis/spec`。
- 不要提交本地运行时目录和工具缓存目录。
- 不要无故修改依赖锁文件。
- 不要把 Channel 结论直接视为项目规范；长期结论必须写回任务产物或 `.trellis/spec`。
