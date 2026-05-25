# Codex 项目级规则

## 项目事实源

- 当前项目的代码、配置、测试、README、CI、任务产物和工具输出优先于历史记忆和通用假设。
- agentmemory 只作为 MCP-only 历史上下文层；召回结果不能替代当前项目文件、GitNexus、Graphify 或测试结果。
- 如果本项目有更深层 `AGENTS.md`，修改对应目录文件前必须读取并遵守。

---

## Agent Memory MCP-only

本项目沿用全局 agentmemory 规则，并补充以下项目级用法：

- 任务涉及本项目历史架构决策、业务规则、Trellis workflow、GitNexus / Graphify 使用约定、测试策略、故障复盘或跨会话持续开发时，先 recall / search。
- recall 后先总结可用历史上下文，再读取当前项目文件和必要工具输出。
- 任务完成后，仅当产生长期价值结论时 remember / save，例如架构决策、关键问题根因、重要修复方案、工具策略、验证策略和后续风险。
- 不要记录 API Key、密码、token、敏感凭据、个人隐私、完整日志或无长期复用价值的临时信息。

---

## Trellis

仅当当前项目存在 Trellis 强证据时使用 Trellis：

- 存在 `.trellis/`
- 存在 `.trellis/workflow.md`
- 存在 `$trellis-*`
- 本项目更深层 `AGENTS.md` 明确说明使用 Trellis

如果 Trellis 可用：

- 调用 `trellis-workflow` Skill。
- 读取 `.trellis/workflow.md`。
- 读取相关 `.trellis/spec`。
- 如果存在当前活跃任务，优先读取 `prd.md`、`design.md`、`implement.md`。
- 不要绕过 `.trellis/workflow.md` 或手动跳过 Trellis phase。
- 不要把一次性任务计划写入 `.trellis/spec`；长期规范、架构决策、业务规则变化才应沉淀到 `.trellis/spec`。

---

## GitNexus

GitNexus 通过全局 `gitnexus-mcp` 提供能力，不作为 Skill 管理。

仅当 GitNexus MCP 可用且当前项目已建立索引时使用 GitNexus。强证据包括：

- 当前项目存在 `.gitnexus/`
- `gitnexus status` 显示已有索引
- GitNexus MCP 的已索引仓库列表包含当前项目路径
- 本项目更深层 `AGENTS.md` 明确说明 GitNexus 已启用

使用规则：

- 修改代码前，优先通过 GitNexus MCP 执行影响分析。
- 修改代码后，优先通过 GitNexus MCP 执行变更检测。
- GitNexus 结果必须与实际 diff、测试结果、Trellis 任务产物和项目规范交叉核对。
- 如果 GitNexus 不可用或当前项目未建立索引，跳过 GitNexus，不阻塞任务。

---

## Graphify

仅当当前项目存在 Graphify 输出或用户明确要求时使用 Graphify：

- 存在 `graphify-out/graph.json`
- 存在 `graphify-out/wiki/index.md`
- 用户明确输入 `/graphify` 或要求使用 Graphify

使用规则：

- 代码库问题优先使用 `graphify query "<question>"`、`graphify path "<A>" "<B>"` 或 `graphify explain "<concept>"` 获取局部上下文。
- `graphify-out/GRAPH_REPORT.md` 仅用于广泛架构审查，或 query/path/explain 信息不足时读取。
- 修改代码后，如项目已维护 Graphify 图谱且命令可用，运行 `graphify update .` 更新图谱。
- Graphify 建图或语义抽取命令返回非零退出码时，按真实失败处理，优先检查 LLM provider、API Key、网络和抽取日志，不要接受静默空图作为成功结果。
- Graphify 输出的跨语言 INFERRED `calls` 边不能单独作为事实依据；涉及调用关系、影响分析或架构结论时，先重新建图或回到源码 / 局部 query 交叉验证。
- Graphify 负责当前项目知识图谱；agentmemory 只记录可复用的建图结论、限制和后续注意事项。

---

## Trellis Channel

普通任务不要使用 `trellis channel`。

仅当用户明确要求多 Agent、多模型、worker、forum、thread、并行评审、交叉验证或外部 orchestrator 协作时，才使用 Channel。

如果需要使用 Channel：

- 调用 `trellis-channel` Skill。
- 不要仅因任务复杂、文件多或跨模块就启用 Channel。
- Channel 结论必须整理回 task artifacts 或 `.trellis/spec`；只有长期复用价值的摘要才写入 agentmemory。
- Channel runtime、events、forum、thread、原始 worker 日志默认不要提交到远程仓库，也不要写入 agentmemory。

---

## 目录规则

按项目策略保留或提交：

- `.trellis/spec/`
- `.trellis/workflow.md`
- `.trellis/tasks/<task>/prd.md`
- `.trellis/tasks/<task>/design.md`
- `.trellis/tasks/<task>/implement.md`

默认不要提交：

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

优先使用当前项目已有命令：

1. 项目 `AGENTS.md` 或更深层规则定义的命令。
2. README、package scripts、Makefile、CI 配置中的命令。
3. `project-validation` Skill 根据修改范围建议的命令。

常见回退命令：

```bash
rtk npm run lint
rtk npm run test
rtk npm run build
rtk ruff check .
rtk ruff format .
rtk ty check .
rtk pytest
rtk go test ./...
```

如果 `rtk` 不可用，回退为项目原生命令。

---

## Lessons

出现 bug 修复、回滚、工具判断错误、工作流阶段错误、验证失败、GitNexus 影响分析不匹配或 Channel / worker 上下文丢失时，调用 `lessons-record` Skill。

优先记录到当前项目内可审查的位置，例如：

- `.trellis/spec/lessons.md`
- `docs/lessons.md`
- `.codex/lessons.md`

如果 agentmemory MCP 可用，且 lesson 对跨会话任务有长期价值，可额外保存一段摘要；agentmemory 不替代项目内 lesson 文件。
