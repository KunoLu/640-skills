# Codex 项目级规则

## 项目事实源

- 当前项目的代码、配置、测试、README、CI、任务产物和工具输出优先于通用假设。
- 如果本项目有更深层 `AGENTS.md`，修改对应目录文件前必须读取并遵守。

---

## UI/UX 设计上下文

默认继承全局规则：`impeccable` 的项目上下文文件维护在 `docs/PRODUCT.md` 和 `docs/DESIGN.md`。

项目级补充：

- 如果本项目已有明确设计文档路径或更深层 `AGENTS.md` 指定其他路径，以项目事实为准。
- 不要在项目根目录、`.agents/context/`、`docs/` 中维护多份同名上下文文件。
- 如果 `docs/` 会被文档站公开发布，先确认这些设计上下文是否允许公开；不允许公开时，按项目发布配置排除，或由项目 `AGENTS.md` 指定其他路径。

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

## mattpocock/skills 项目级编排

本项目只接入以下官方 mattpocock/skills，并默认原样使用：

- `diagnose`
- `tdd`
- `grill-me`
- `grill-with-docs`
- `handoff`
- `write-a-skill`
- `zoom-out`
- `to-prd`
- `to-issues`

编排说明：

- 普通 bug、测试失败或运行时异常：`diagnose` → GitNexus debugging（根因不清时）→ Codex fix → `tdd` / regression test → 项目测试。
- 线上问题、日志异常或数据不一致：`diagnose` 先建立时间线、事实、假设和排除项，再进入修复或缓解。
- 中大型需求：`grill-me` 或 `grill-with-docs` → `to-prd` → `to-issues` 输出 Trellis-ready Markdown tasks → Trellis workflow → GitNexus impact-analysis → Codex implementation → 项目测试 / TestSprite。
- 高风险后端逻辑、算法或数据同步：`grill-with-docs` → `to-prd` → `to-issues` → Trellis TDD workflow → `tdd` → GitNexus impact-analysis → 回归测试。
- 陌生模块或上下文不清：`zoom-out` → GitNexus exploring / impact-analysis → Codex implementation。
- 长任务暂停、`/clear`、新会话或交接前：`handoff`。
- 需要创建或维护 Skill 时：`write-a-skill`。

`to-prd` 默认输出 Markdown PRD；`to-issues` 默认输出 vertical-slice Markdown tasks。除非用户明确要求，不自动发布到 GitHub、Linear 或任何 issue tracker。

---

## Graphify

Graphify 降级为可选架构可视化工具。仅当用户明确输入 `$graphify`、提到 Graphify、知识图谱或图谱可视化，并且当前环境已确认安装 Graphify 且相关命令可执行时使用。

使用规则：

- 不因项目存在 `graphify-out/` 就主动调用 Graphify。
- 不因代码范围大、架构不清或影响范围不明就主动调用 Graphify；这些场景优先使用 `zoom-out`、GitNexus exploring / impact-analysis 和项目文件。
- 如果 Graphify 不可用，直接跳过，不阻塞任务。
- 代码库问题优先使用 `graphify query "<question>"`、`graphify path "<A>" "<B>"` 或 `graphify explain "<concept>"` 获取局部上下文。
- `graphify-out/GRAPH_REPORT.md` 仅用于广泛架构审查，或 query/path/explain 信息不足时读取。
- 只有本次任务已按上述条件启用 Graphify，且项目已维护 Graphify 图谱时，代码修改后才考虑运行 `graphify update .` 更新图谱。
- 更新已有图谱时，优先让 `graphify update .` 按磁盘状态协调删除文件后的节点；不要用手工改图谱或仅依赖增量标志来处理 ghost node。
- 如果 Graphify hook 因 `graphify-out/` 变化反复触发，可用 `GRAPHIFY_SKIP_HOOK=1` 做一次性跳过并检查 hook 日志；不要提交无意义的图谱 churn。
- Graphify 可抽取 MCP 配置中的服务、包引用和 env var 名称，但不应依赖它读取或保留 env 值；涉及凭据时仍按敏感信息处理。
- 中文查询效果依赖当前 Graphify 安装的中文分词支持；查询中文复合词结果异常时，先检查可选中文 extra 是否安装，再回退到更明确的关键词或源码验证。
- Graphify 建图或语义抽取命令返回非零退出码时，按真实失败处理，优先检查 LLM provider、API Key、网络和抽取日志，不要接受静默空图作为成功结果。
- 安装、升级或由 Skill 调用 Graphify 时，优先使用当前官方推荐的 `uv tool install`、`uv tool upgrade` 或 `uv tool run graphifyy ...` 路径；在 macOS / Windows 上不要假设裸 `pip install` 后的 Python 环境与 CLI、hook 或 Skill 运行环境一致。
- Graphify 的 `references` 语义边可能携带 `parameter_type`、`return_type`、`generic_arg`、`field`、`attribute` 等上下文；分析类型依赖时优先用这些上下文缩小范围，并区分 `inherits` 与 `implements`。
- `graphify-out/GRAPH_REPORT.md` 中的 `Import Cycles` 只能作为循环依赖审查线索；重构前仍需回到源码、import 图或局部 query 验证。
- 使用 `graphify provider add/list/show/remove` 配置自定义 OpenAI-compatible backend 时，确认 API key env、provider 优先级和数据驻留要求；`~/.graphify/providers.json` 视为本机配置，不要提交或写入项目文档。
- 如果图谱社区名称仍是 `Community N` 这类占位名，且 Graphify 已按规则启用并配置了可用 backend，可用 `graphify label <path>` 重新生成社区名称；社区标签只能辅助导航，不替代源码和局部 query/path/explain 验证。
- Graphify 抽取异常或 JS/TS 工作区文件被跳过时，可用 `GRAPHIFY_DEBUG=1` 获取完整 traceback；`.graphifyignore` 中以 `/` 开头的规则按仓库根目录锚定，不要当作任意层级匹配。
- Graphify 输出的跨语言 INFERRED `calls` 边不能单独作为事实依据；涉及调用关系、影响分析或架构结论时，先重新建图或回到源码 / 局部 query 交叉验证。
- Graphify 升级后，如果结论依赖旧图谱中的文件 / symbol node ID、社区标签、TypeScript 继承边、JS/TS 声明节点、Markdown 代码块节点、Lua import、跨语言 `references` / `calls`、`graph.json` diff 稳定性或安装路径信息，先重新建图或运行 `graphify update .`，再回到源码 / 局部 query 交叉验证。

---

## Trellis Channel

普通任务不要使用 `trellis channel`。

仅当用户明确要求多 Agent、多模型、worker、forum、thread、并行评审、交叉验证或外部 orchestrator 协作时，才使用 Channel。

如果需要使用 Channel：

- 调用 `trellis-channel` Skill。
- 不要仅因任务复杂、文件多或跨模块就启用 Channel。
- Channel 结论必须整理回 task artifacts 或 `.trellis/spec`。
- Channel runtime、events、forum、thread、原始 worker 日志默认不要提交到远程仓库。

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
