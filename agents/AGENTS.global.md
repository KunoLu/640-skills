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

### Graphify

Graphify 为可选架构可视化工具，不进入默认 Agent Harness 主流程。

仅当同时满足以下条件时，才使用 Graphify：

1. 用户明确提到 Graphify、`$graphify`、知识图谱或图谱可视化。
2. 当前环境已确认安装 Graphify，并且相关命令可执行。

使用规则：

- 不因项目存在 `graphify-out/` 就主动调用 Graphify。
- 不因代码范围大、架构不清或影响范围不明就主动调用 Graphify；这些场景优先使用 `zoom-out`、GitNexus exploring / impact-analysis 和项目文件。
- 如果 Graphify 不可用，直接跳过，不阻塞任务。
- Graphify 输出只能作为辅助线索；涉及调用关系、影响分析、架构结论或修复范围时，必须回到源码、项目文档、GitNexus、测试或工具输出交叉验证。

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
| `diagnose` | 诊断 bug、测试失败、运行时错误、性能回归、日志异常、线上问题或数据不一致 | 问题根因不清或需要系统化排障时 |
| `tdd` | 测试先行、回归测试、复杂逻辑验证、高风险修改 | 需要用测试固化行为再实现时 |
| `grill-me` | 通用需求澄清、方案质询、计划压力测试 | 用户希望先打磨计划、决策或设计时 |
| `grill-with-docs` | 结合项目文档澄清需求、术语、领域模型和 ADR / CONTEXT 沉淀 | 项目内需求或方案进入 PRD / Trellis 前 |
| `handoff` | 长会话交接、上下文压缩、跨会话继续任务 | `/clear`、新会话、Trellis 暂停或多会话交接前 |
| `write-a-skill` | 创建或维护自定义 Skill | 用户要求新增、改造或沉淀 Skill 时 |
| `zoom-out` | 陌生模块、系统上下文、调用方地图和抽象层级提升 | 修改不熟悉代码区域前或上下文不清时 |
| `to-prd` | 将当前对话和代码库理解整理为 Markdown PRD | 需求需要沉淀为 PRD 时 |
| `to-issues` | 将 PRD、plan 或 spec 拆成实现任务 | 需要 Trellis-ready Markdown task 或 vertical slices 时 |
| `ui-ux-pro-max` | UI/UX 修改 | before-dev 前 |
| `impeccable` | 前端 UI/UX 塑形、审计、打磨、反模板化和视觉质量收尾 | `ui-ux-pro-max` 明确设计方向后，或实现后的 audit / polish 阶段；仅在 Skill 可用且上下文可用时 |

### 自定义 Skills 使用边界

- `ui-ux-pro-max`：仅在涉及 UI、交互、布局、视觉、组件体验、前端可用性时调用。作为 UI/UX 任务的默认设计智能入口，用于产品类型、目标用户、风格、配色、字体、可访问性、栈约束和设计系统方向判断；不替代项目已有 design system、tokens、组件库和品牌规范。
- `impeccable`：仅在前端 UI/UX 任务需要塑形、审计、批判、打磨、反模板化、视觉层级、排版、配色、动效、响应式、可访问性或最终 polish 时调用。默认作为 `ui-ux-pro-max` 的下游执行与质检 Skill：`ui-ux-pro-max` 先给设计系统和领域建议，`impeccable` 再把具体界面收敛为 brief、实现检查项或 polish backlog。
- `impeccable` 为可选 Skill；如果未出现在可用 Skill 列表、Skill 文件不可读取、引用脚本不可执行，或其 setup 需要初始化项目上下文但用户未明确要求初始化，则跳过 `impeccable`，继续使用 `ui-ux-pro-max`、项目设计规范和浏览器验证，不阻塞任务。
- 如果使用 `impeccable` 生成或维护项目上下文，默认将 `PRODUCT.md` 和 `DESIGN.md` 放在项目根目录的 `docs/` 下，即 `docs/PRODUCT.md` 和 `docs/DESIGN.md`；不要在项目根目录创建重复副本。`.impeccable/design.json` sidecar 仍按 `impeccable` 默认保留在项目根目录 `.impeccable/` 下。
- `impeccable` 上下文文件必须避免多源冲突：如果项目根目录、`.agents/context/`、`docs/` 中同时存在 `PRODUCT.md` 或 `DESIGN.md`，以项目 `AGENTS.md` 指定路径为准；在读取和写入前先确认实际采用的上下文目录，避免同名文件分散在多个位置。
- UI/UX Skill 编排：
    - 新页面 / 新组件 / 大幅改版：先用 `ui-ux-pro-max` 判断产品类型、目标用户、风格、配色、字体、布局和可访问性基线；再在 `impeccable` 可用时使用 `shape` 形成任务级 design brief，获得用户确认后再实现。
    - 端到端高质量视觉实现：`ui-ux-pro-max` 输出设计系统方向；`impeccable craft` 只在 brief 已确认且需要完整设计执行时使用，并遵守其中的用户确认 gate。
    - 既有 UI 审查：先用 `ui-ux-pro-max` 的优先级清单覆盖可访问性、交互、性能、响应式、排版和颜色；再在 `impeccable` 可用时用 `audit` / `critique` 生成问题 backlog。
    - 实现后收尾：运行项目验证和浏览器 / 截图检查；如 `impeccable` 可用，用 `polish` 或 `layout`、`typeset`、`colorize`、`adapt`、`clarify`、`animate`、`harden`、`optimize` 等针对性命令做最终质量 pass。
    - 冲突处理：项目 `AGENTS.md`、设计系统、tokens、组件库和已确认品牌规范优先；可访问性、响应式和项目验证不可降级。`impeccable` 的硬性反模板化规则可否决 `ui-ux-pro-max` 的泛化风格建议，除非项目既有品牌规范明确要求该设计语言。
- **mattpocock/skills** 仅纳入 `diagnose`、`tdd`、`grill-me`、`grill-with-docs`、`handoff`、`write-a-skill`、`zoom-out`、`to-prd`、`to-issues`。
- **mattpocock/skills** 优先原样使用官方 Skill；除非用户明确要求，不 fork、不改写官方 Skill 文件。
- **mattpocock/skills** 相关 skill 使用边界说明：
    - `diagnose` 用于系统化排障；代码级问题根因不清时结合 GitNexus debugging，修复前有风险时结合 GitNexus impact-analysis，并补充或更新回归测试。
    - `tdd` 适用于 bug 修复、核心业务逻辑、算法行为、数据转换、导入 / 导出 / 同步逻辑和高风险修改；不要强制用于简单文案、样式、配置说明或一次性脚本。
    - `grill-me` 用于通用计划、设计和决策的质询；如果问题可通过读取当前项目文件回答，先探索项目文件。
    - `grill-with-docs` 用于项目内需求澄清、领域术语对齐、CONTEXT.md 或 ADR 沉淀；不要把 CONTEXT.md 写成临时规格书。
    - `handoff` 交接内容应包含当前目标、已完成工作、关键决策、文件 / 产物、已尝试命令、开放问题、建议下一步 Skill、不要重复事项和敏感信息脱敏说明。
    - `write-a-skill` 创建的新 Skill 默认使用 `SKILL.md` 作为入口，长内容拆到 reference，确定性操作优先脚本化，description 必须写清触发场景。
    - `zoom-out` 用于先看模块边界、调用方和系统上下文；如果进入实现，再结合 GitNexus exploring / impact-analysis。
    - `to-prd` 默认输出 Markdown PRD；不要发布到 GitHub、Linear 或任何 issue tracker，除非用户明确要求。
    - `to-issues` 中的 issue 视为通用实现任务；默认输出 Trellis-ready Markdown vertical slices，标注 AFK / HITL、依赖顺序、验收标准和测试策略，不自动发布到 issue tracker。

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

执行 `/clear`、长任务暂停、新会话切换或交接前，如当前任务存在未完成上下文，优先使用 `handoff` Skill 生成交接摘要。

如果 `handoff` 不可用，按以下字段手工总结：

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
