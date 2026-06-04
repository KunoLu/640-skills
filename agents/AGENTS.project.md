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

UI/UX 任务编排：

- 涉及 UI、交互、布局、视觉、组件体验或前端可用性时，初稿计划默认先使用 `ui-ux-pro-max`，明确产品类型、目标用户、信息架构、交互模型、响应式策略、可访问性基线和项目设计系统约束。
- `impeccable shape` / `impeccable craft` 只在新视觉方向、高保真页面、大幅改版、品牌 / 营销强视觉页面、方向不清或用户明确要求时前置使用；其 brief 必须经用户确认后再进入实现。
- 常规 UI 实现完成后，先运行项目验证和浏览器 / 截图检查；如 `impeccable` 可用，再使用 `audit` / `critique` / `polish` 或 `layout`、`typeset`、`colorize`、`adapt`、`clarify`、`animate`、`harden`、`optimize` 等针对性命令做打磨。
- 如果 UI/UX 任务进入 Trellis，任务级设计结论写入 `prd.md`、`design.md` 或 `implement.md`；长期设计系统规则才写入 `docs/DESIGN.md` 或 `.trellis/spec`。

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

需求进入 PRD / Trellis task 前：

- 如果用户只给出初始需求，且需求涉及本项目领域模型、业务术语、长期规则、已有文档或架构决策，先使用 `grill-with-docs` 澄清。
- `grill-with-docs` 阶段应先读取项目文档和相关代码；能从项目事实回答的问题，不要反问用户。
- 一次只问一个关键问题，并给出推荐答案；达成共识后输出需求确认摘要。
- 长期领域上下文默认写入 `docs/CONTEXT.md`，ADR 默认写入 `docs/adr/*.md`，多上下文项目使用 `docs/contexts/<context>/CONTEXT.md` 和 `docs/contexts/<context>/adr/*.md`；不要新建根目录 `CONTEXT.md`，除非本项目已采用该路径或更深层 `AGENTS.md` 明确指定。
- 需求确认摘要经用户确认后，再使用 `to-prd` 生成 Markdown PRD，并用 `to-issues` 拆成 Trellis-ready vertical slices。
- 在 Trellis 项目中，PRD 终稿应写入 `.trellis/tasks/<task>/prd.md`；拆解后的 parent / child tasks 和实现切片应落到 `.trellis/tasks/<task>/...` 下的 task artifacts。未确定 task 路径前，不要把最终 PRD 或 issue 清单长期落到 `docs/`。
- 如果需求不依赖项目文档或领域术语，只是通用方案质询，可使用 `grill-me`。

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
- 中大型项目内需求：`grill-with-docs` → 需求确认摘要 → `to-prd` → `to-issues` 输出 Trellis-ready Markdown tasks → Trellis workflow → GitNexus impact-analysis → Codex implementation → 项目测试 / TestSprite。
- 不依赖项目文档或领域术语的通用方案质询：`grill-me` → 方案确认 → `to-prd` / `to-issues`（需要时）→ Codex implementation。
- 高风险后端逻辑、算法或数据同步：`grill-with-docs` → `to-prd` → `to-issues` → Trellis TDD workflow → `tdd` → GitNexus impact-analysis → 回归测试。
- 陌生模块或上下文不清：`zoom-out` → GitNexus exploring / impact-analysis → Codex implementation。
- 长任务暂停、`/clear`、新会话或交接前：`handoff`。
- 需要创建或维护 Skill 时：`write-a-skill`。

`to-prd` 默认输出 Markdown PRD；`to-issues` 默认输出 vertical-slice Markdown tasks。在 Trellis 项目中，这些产物最终应进入 `.trellis/tasks/<task>/prd.md`、`design.md`、`implement.md` 或 parent / child task artifacts。除非用户明确要求，不自动发布到 GitHub、Linear 或任何 issue tracker。

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

默认记录到 `.trellis/spec/lessons.md`。

除非用户明确指定或更深层 `AGENTS.md` 改写，不写入 `docs/lessons.md`、`.codex/lessons.md` 或其他位置。
