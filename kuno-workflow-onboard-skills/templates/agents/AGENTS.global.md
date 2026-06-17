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
- 不要在未读取相关 `.trellis/spec` 的情况下实现长期规则相关修改；其中 `.trellis/spec/lessons.md` 只作为短入口和高优先级摘要。
- 不要默认读取完整 `.trellis/lessons/**`；先通过 `.trellis/lessons/index.md`、tags、错误信息或当前任务主题按需检索，再读取命中的 topic / archive 文件。
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
- 如果项目存在 `.gitnexusrc` 或需要指定默认分支，遵循项目配置；必要时使用 `gitnexus analyze --default-branch <branch>` 重新分析。
- 当影响分析结果存在同名符号、跨文件歧义或输出过大时，优先使用 GitNexus 提供的 `uid` / `file` / `kind` 约束和分页 / summary-only 能力缩小范围。
- 通过 GitNexus MCP 枚举已索引仓库时，`list_repos` 可能返回分页对象；使用 `limit` / `offset` 翻页直到 `pagination.hasMore` 为 false，不要把单页结果当作完整仓库列表。
- 对跨服务 API、HTTP route / consumer、gRPC 或前后端调用链的结论，必须回到实际路由、客户端调用和 diff 交叉核对。
- 如果需要移除 GitNexus 集成，优先使用 `gitnexus uninstall` 的 dry-run 查看将删除的 MCP 配置、Skill 和 hooks；只有用户明确确认后才加 `--force`，并复核配置 diff。
- 可选 tree-sitter grammar 缺失、跳过或回退构建不一定代表 `gitnexus analyze` 失败；若输出提示 optional grammar、prebuild / toolchain fallback 或 `GITNEXUS_SKIP_OPTIONAL_GRAMMARS`，把相关语言覆盖作为风险记录，并结合实际源码和查询结果复核。
- 大仓库分析中出现 skipped large files、内存墙、FTS 损坏或 repair 提示时，把这些作为索引完整性风险；需要时运行 GitNexus 提供的修复或重建命令后再依赖结果。

如果 GitNexus MCP 不可用或项目未建立索引：

- 跳过 GitNexus。
- 不阻塞任务。
- 不假设索引存在。
- 仅在该判断影响任务风险时，在最终输出中说明已跳过。

### TestSprite

TestSprite 作为测试计划、UI/E2E、API 集成和回归验证辅助工具使用，不替代项目自己的 lint / test / build、浏览器检查或人工测试评审。

仅当存在强证据时，才认为 TestSprite 可用：

- 当前 MCP 工具列表中存在 TestSprite 相关工具。
- 当前 IDE / Agent 环境已明确配置 TestSprite MCP server 和 API Key。
- 项目级 `AGENTS.md` 或测试文档明确说明使用 TestSprite，且当前环境能调用对应 MCP 工具。

涉及端到端流程、UI/API 集成、测试计划、回归验证、发布前 smoke 或 Trellis 验收时，必须主动判定 TestSprite 状态：`run` / `blocked` / `skipped`。调用会打开外部 UI 的 TestSprite bootstrap / 配置工具前，先准备本次测试范围对应的 PRD、`projectPath`、`localPort`、`type` 和 `testScope`；配置门户、PRD 上传、测试账号、认证方式或服务不可用时，只能输出 `blocked` 和剩余配置项。

真实账号、密钥、PII 和生产数据不得写入仓库、PRD、测试代码、日志或报告。TestSprite 产物是否入库按项目策略决定。

## Skills 调用规则

**规则**：相关 Skill 可用且任务场景明确匹配时，优先调用对应 Skill；不可用时直接跳过，不阻塞任务。

不要因为任务简单就跳过已明确匹配的 Skill。  
如果任务场景与 Skill 的使用场景不匹配，或仅存在弱关联，则不要强行调用 Skill。

Skill 不替代项目规范、任务产物、测试和人工判断。  
如果 Skill 与项目 `AGENTS.md`、`.trellis/workflow.md` 或 `.trellis/spec` 冲突，以项目规则为准。

### grill-with-docs 使用状态透明度

在准备开始开发需求、进入 PRD / Trellis task、需求最终确认、PRD / design / implement review gate、或询问是否开始实现前，必须对 `grill-with-docs` 的使用状态做用户可见说明：

- 如果已完整执行 `grill-with-docs` 的逐问题澄清流程，明确说明“已调用 `grill-with-docs`”，并简述已解决的关键产品 / 领域边界。
- 如果只读取了 `grill-with-docs` Skill 文件、只借用了其中 evidence-first 原则，或仅通过代码 / 文档自行判断，不得声称已调用；必须明确说明“未完整调用 `grill-with-docs`”。
- 未完整调用时，必须给出具体原因，例如：需求不涉及项目领域模型或长期术语；问题可完全由现有文档 / 代码回答；只是 Trellis 启动实现的 review gate；Skill 不可用 / 不可读取；用户明确要求跳过。
- 在每次需求最终确认、PRD / design / implement review gate、或询问是否开始实现前，如果未完整调用 `grill-with-docs`，必须主动询问用户是否需要先用 `grill-with-docs` 再评估一次。

| Skill | 使用场景 | 调用时机 |
|---|---|---|
| `trellis-workflow` | Trellis 生命周期、任务产物、阶段检查 | 发现项目使用 Trellis 后 |
| `trellis-channel` | Trellis Channel / 多 Agent / 多模型协作、代码 review / 验证 preflight | 用户明确要求 Channel、worker、forum、thread、并行评审，或项目级高风险 review / validation gate 需要 Channel preflight 时 |
| `project-validation` | 判断代码修改后的验证策略 | 修改代码后、执行验证前 |
| `lessons-record` | 记录长期经验教训 | bug 修复、回滚、工具误判、验证失败、上下文丢失后 |
| `book-refactoring-pass` | 行为保持型重构检查 | 修改既有代码且结构阻碍当前实现、清理与行为变更可能混杂时 |
| `book-legacy-change-safety` | 遗留 / 弱测试代码安全修改 | 目标代码行为不清、测试不足、依赖隐藏或回归风险高时 |
| `book-ddd-distilled-modeling` | 轻量领域建模、统一语言和 bounded context 判断 | 需求涉及业务术语、领域规则、上下文边界或模型歧义，进入 PRD / design 前 |
| `book-ddia-data-design` | 数据密集型设计风险检查 | 修改存储、事件、队列、缓存、迁移、数据所有权或跨服务数据流时 |
| `book-release-readiness` | 生产就绪与发布风险检查 | 服务、API、任务、队列、外部集成或部署敏感路径实现后 / check 阶段 |
| `diagnose` | 诊断 bug、测试失败、运行时错误、性能回归、日志异常、线上问题或数据不一致 | 问题根因不清或需要系统化排障时 |
| `tdd` | 测试先行、回归测试、复杂逻辑验证、高风险修改 | 需要用测试固化行为再实现时 |
| `grill-me` | 通用需求澄清、方案质询、计划压力测试 | 用户希望先打磨计划、决策或设计时 |
| `grill-with-docs` | 结合项目文档澄清需求、术语、领域模型和 ADR / CONTEXT 沉淀 | 项目内需求或方案进入 PRD / Trellis 前 |
| `handoff` | 长会话交接、上下文压缩、跨会话继续任务 | `/clear`、新会话、Trellis 暂停或多会话交接前 |
| `write-a-skill` | 创建或维护自定义 Skill | 用户要求新增、改造或沉淀 Skill 时 |
| `zoom-out` | 陌生模块、系统上下文、调用方地图和抽象层级提升 | 修改不熟悉代码区域前或上下文不清时 |
| `to-prd` | 将当前对话和代码库理解整理为 Markdown PRD | 需求需要沉淀为 PRD 时 |
| `to-issues` | 将 PRD、plan 或 spec 拆成实现任务 | 需要 Trellis-ready Markdown task 或 vertical slices 时 |
| `ui-ux-pro-max` | UI/UX 初稿计划、修改前设计判断和体验质量检查 | 涉及 UI/UX 的需求进入实现或 Trellis 任务设计前 |
| `impeccable` | 前端 UI/UX 塑形、审计、打磨、反模板化和视觉质量收尾 | `ui-ux-pro-max` 明确初稿方向后按条件前置 `shape` / `craft`，或实现后的 `audit` / `critique` / `polish` 阶段；仅在 Skill 可用且上下文可用时 |
| `web-ui-autotest-generator` | Web UI Playwright 测试资产生成、选择器审计和覆盖率报告 | 用户明确要求生成 Web UI 自动化测试，或测试阶段发现关键 Web UI 回归路径需要固化为仓库内可维护测试资产时 |
| `React Bits Pro Skill` | React / shadcn UI 项目中接入 React Bits Pro components、blocks 或 landing page sections | 前端 UI 开发任务明确需要 React Bits Pro，且技术栈、registry、项目内 Skill 和可读取 license key 条件均满足时 |

### 自定义 Skills 使用边界

- `ui-ux-pro-max`：仅在涉及 UI、交互、布局、视觉、组件体验、前端可用性时调用。作为 UI/UX 任务的默认初稿计划入口，用于产品类型、目标用户、信息架构、交互模型、风格、配色、字体、可访问性、栈约束和设计系统方向判断；不替代项目已有 design system、tokens、组件库和品牌规范。
- `impeccable`：仅在前端 UI/UX 任务需要塑形、审计、批判、打磨、反模板化、视觉层级、排版、配色、动效、响应式、可访问性或最终 polish 时调用。默认作为 `ui-ux-pro-max` 的下游执行与质检 Skill：`ui-ux-pro-max` 先形成初稿计划和设计系统方向，`impeccable` 再按条件形成高保真 brief、实现检查项或 polish backlog。
- `impeccable` 为可选 Skill；如果未出现在可用 Skill 列表、Skill 文件不可读取、引用脚本不可执行，或其 setup 需要初始化项目上下文但用户未明确要求初始化，则跳过 `impeccable`，继续使用 `ui-ux-pro-max`、项目设计规范和浏览器验证，不阻塞任务。
- `web-ui-autotest-generator`：仅在 Web UI / E2E 测试需要生成、审计或评估可入库测试资产时调用。测试阶段如果改动关键 Web UI 业务流、修复用户可见 UI 回归、项目已有 Playwright / Cypress 需扩展覆盖、或 Trellis 验收要求可重复 UI 回归，必须主动判定是否调用；不需要长期测试资产时可跳过但要说明。具体执行与产物策略遵循项目级 `AGENTS.md` 和 `project-validation` Skill。
- `agent-rules-books` 派生 Skill 仅作为按需专项审查视角，不替代项目规范、Trellis task artifacts、`.trellis/spec`、GitNexus、`tdd`、项目测试、`project-validation`、TestSprite 或人工评审。默认只纳入 `book-refactoring-pass`、`book-legacy-change-safety`、`book-ddd-distilled-modeling`、`book-ddia-data-design`、`book-release-readiness`；不默认纳入 APoSD、Clean Architecture、PoEAA 等项目风格更强的扩展。多个 book-derived Skill 同时可能适用时，优先选择当前主风险对应的 1-2 个，不要把 5 个当作固定 checklist 全量调用。
- `book-refactoring-pass`：仅在既有代码结构阻碍当前修改、行为变更和结构整理可能混杂、或 review 需要判断是否先重构时使用。输出应限定为当前行为边界、最小重构步骤、安全网和验证命令；不要推动任务外的大重写。
- `book-legacy-change-safety`：仅在遗留代码、测试不足、当前行为不清或隐藏依赖导致修改风险较高时使用。优先配合 `diagnose`、`tdd` 和 GitNexus 影响分析，用 characterization test、最小 seam 或聚焦检查锁定行为后再修改。
- `book-ddd-distilled-modeling`：仅在需求涉及业务术语、领域规则、bounded context、上下文边界或模型歧义时使用，通常位于 `grill-with-docs` 之后、`to-prd` / `design.md` 之前。不要把一次性领域推断直接写入长期 context 或 `.trellis/spec`。
- `book-ddia-data-design`：仅在存储、事件、队列、缓存、迁移、schema 演进、数据所有权或跨服务数据流变更时使用。重点检查 source of truth、一致性模型、幂等、乱序、重试、回放、迁移 / 回滚、观测和修复路径。
- `book-release-readiness`：仅在生产路径相关的服务、API、任务、队列、外部集成或部署敏感变更后使用，通常位于项目验证后或 `$trellis-check` 阶段。重点检查 timeout、retry、fallback、隔离、backpressure、观测、告警、rollout 和 rollback；不阻塞与当前项目无关的理论风险。
- `trellis-channel` 可以被项目级规则主动用于高风险代码 review / 验证覆盖 preflight，但 preflight 不等于启动 Channel runtime。除非用户已明确要求 Channel，或在 preflight 后明确确认，否则不得静默 spawn worker。
- `React Bits Pro Skill`：仅在前端 UI 任务明确需要 React Bits Pro，且项目是 React + shadcn/ui、`components.json` 存在、registry / `REACTBITS_LICENSE_KEY` / 项目内 React Bits Pro Skill 均可用时调用。任一前提不满足则跳过并说明原因；不要读取、输出、提交 license key。具体 registry 和安装细节由项目级 `AGENTS.md` 约束。
- 如果使用 `impeccable` 生成或维护项目上下文，默认将 `PRODUCT.md` 和 `DESIGN.md` 放在项目根目录的 `docs/` 下，即 `docs/PRODUCT.md` 和 `docs/DESIGN.md`；不要在项目根目录创建重复副本。`.impeccable/design.json` sidecar 仍按 `impeccable` 默认保留在项目根目录 `.impeccable/` 下。
- `impeccable` 上下文文件必须避免多源冲突：如果项目根目录、`.agents/context/`、`docs/` 中同时存在 `PRODUCT.md` 或 `DESIGN.md`，以项目 `AGENTS.md` 指定路径为准；在读取和写入前先确认实际采用的上下文目录，避免同名文件分散在多个位置。
- UI/UX Skill 编排：
    - 初始需求 / 初稿计划：先用 `ui-ux-pro-max` 判断产品类型、目标用户、信息架构、交互模型、风格、配色、字体、布局、响应式策略和可访问性基线；如果任务进入 Trellis，将结论写入任务级 `prd.md`、`design.md` 或 `implement.md`。
    - 前置设计升级：只有在新视觉方向、高保真页面、大幅改版、品牌 / 营销强视觉页面、方向不清或用户明确要求时，才在实现前使用 `impeccable shape`；`impeccable craft` 只在 brief 已确认且需要完整设计执行时使用，并遵守其中的用户确认 gate。
    - 既有 UI 审查：先用 `ui-ux-pro-max` 的优先级清单覆盖可访问性、交互、性能、响应式、排版和颜色；再在 `impeccable` 可用时用 `audit` / `critique` 生成问题 backlog。
    - 实现后收尾：功能完成后，先运行项目验证和浏览器 / 截图检查；如 `impeccable` 可用，用 `polish` 或 `layout`、`typeset`、`colorize`、`adapt`、`clarify`、`animate`、`harden`、`optimize` 等针对性命令做最终质量 pass。
    - 冲突处理：项目 `AGENTS.md`、设计系统、tokens、组件库和已确认品牌规范优先；可访问性、响应式和项目验证不可降级。`impeccable` 的硬性反模板化规则可否决 `ui-ux-pro-max` 的泛化风格建议，除非项目既有品牌规范明确要求该设计语言。
- **mattpocock/skills** 仅纳入 `diagnose`、`tdd`、`grill-me`、`grill-with-docs`、`handoff`、`write-a-skill`、`zoom-out`、`to-prd`、`to-issues`。
- **mattpocock/skills** 优先原样使用官方 Skill；除非用户明确要求，不 fork、不改写官方 Skill 文件。
- **mattpocock/skills** 相关 skill 使用边界说明：
    - `diagnose` 用于系统化排障；代码级问题根因不清时结合 GitNexus debugging，修复前有风险时结合 GitNexus impact-analysis，并补充或更新回归测试。
    - `tdd` 适用于 bug 修复、核心业务逻辑、算法行为、数据转换、导入 / 导出 / 同步逻辑和高风险修改；这些场景必须主动判定是否使用 `tdd`，跳过时说明原因。不要强制用于简单文案、样式、配置说明或一次性脚本。
    - `grill-me` 用于通用计划、设计和决策的质询；如果问题可通过读取当前项目文件回答，先探索项目文件。
    - `grill-with-docs`：
        - 用于项目内需求澄清、领域术语对齐、CONTEXT.md 或 ADR 沉淀；需求进入 PRD / Trellis 前优先使用；先读项目文档和代码，能从项目事实回答的问题不要反问用户；长期领域上下文默认写入 `docs/CONTEXT.md`，ADR 默认写入 `docs/adr/*.md`，多上下文项目使用 `docs/contexts/<context>/CONTEXT.md` 和 `docs/contexts/<context>/adr/*.md`；不要新建根目录 `CONTEXT.md`，除非项目已采用该路径或项目级规则明确指定；不要把 CONTEXT.md 写成临时规格书。
        - 使用状态必须遵守上文“grill-with-docs 使用状态透明度”；读取 Skill 文件或只按 evidence-first 原则自行判断，不等于完整调用。
    - `handoff` 交接内容应包含当前目标、已完成工作、关键决策、文件 / 产物、已尝试命令、开放问题、建议下一步 Skill、不要重复事项和敏感信息脱敏说明。
    - `write-a-skill` 创建的新 Skill 默认使用 `SKILL.md` 作为入口，长内容拆到 reference，确定性操作优先脚本化，description 必须写清触发场景。
    - `zoom-out` 用于先看模块边界、调用方和系统上下文；如果进入实现，再结合 GitNexus exploring / impact-analysis。
    - `to-prd` 默认输出 Markdown PRD；在 Trellis 项目中，最终 PRD 应写入或更新 `.trellis/tasks/<task>/prd.md`，未确定 task 路径前只保留为对话草稿或用户明确指定的临时文件；不要发布到 GitHub、Linear 或任何 issue tracker，除非用户明确要求。
    - `to-issues` 中的 issue 视为通用实现任务；在 Trellis 项目中，vertical slices 应落为 `.trellis/tasks/<task>/...` 下的 parent / child task artifacts，标注 AFK / HITL、依赖顺序、验收标准和测试策略；不要默认在 `docs/` 下维护最终 issue / task Markdown，也不要自动发布到 issue tracker。

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

Trellis 项目默认采用 `lessons-record` Skill 定义的分层结构：`.trellis/spec/lessons.md` 只作为短入口，完整内容进入 `.trellis/lessons/index.md`、`topics/` 或按需归档。只有确认项目没有使用 Trellis 时，才默认写入 `docs/lessons.md`。不要在普通任务中滥写 lesson。

---

## 最终目标

保持任务可验证、可维护、最小化、可回滚，并与项目规范一致。
