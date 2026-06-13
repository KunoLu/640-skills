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
- 需要接入 React Bits Pro components、blocks 或 landing page sections 时，只有在项目为 React 技术栈（包括 Next.js、Vite React、Remix、TanStack Start React、使用 TanStack Router 的 React 应用等）、已初始化 shadcn/ui、registry 已配置、当前环境能读取 `REACTBITS_LICENSE_KEY`，并且项目环境已安装对应 React Bits Pro Skill 的前提下，才使用 React Bits Pro Skill。
- `impeccable shape` / `impeccable craft` 只在新视觉方向、高保真页面、大幅改版、品牌 / 营销强视觉页面、方向不清或用户明确要求时前置使用；其 brief 必须经用户确认后再进入实现。
- 常规 UI 实现完成后，先运行项目验证和浏览器 / 截图检查；如 `impeccable` 可用，再使用 `audit` / `critique` / `polish` 或 `layout`、`typeset`、`colorize`、`adapt`、`clarify`、`animate`、`harden`、`optimize` 等针对性命令做打磨。
- 如果 UI/UX 任务进入 Trellis，任务级设计结论写入 `prd.md`、`design.md` 或 `implement.md`；长期设计系统规则才写入 `docs/DESIGN.md` 或 `.trellis/spec`。

### React Bits Pro Skill

React Bits Pro Skill 是可选前端 UI 辅助，不是默认设计系统。只有同时满足以下条件时才使用：

- 当前任务是前端 UI 开发，且明确需要 React Bits Pro components、blocks、templates 或类似高级动画组件。
- 项目技术栈是 React 项目，包括 Next.js、Vite React、Remix、TanStack Start React、使用 TanStack Router 的 React 应用等，并已初始化 shadcn/ui。
- 本地 Node.js 18+ 可用，项目根目录存在 `components.json`。
- `components.json` 已配置或用户明确要求配置 React Bits Pro registry：`@reactbits-starter` 用于 components；需要 Pro / Ultimate blocks 时再使用 `@reactbits-pro`。
- 执行 `shadcn` 或 Agent 的当前环境能读取到 `REACTBITS_LICENSE_KEY` 的值；Agent 不打印、不输出、不提交该 key。
- 项目环境已安装对应 React Bits Pro Skill，例如项目中存在由 `npx shadcn@latest add @reactbits-starter/skill` 在项目根目录安装生成的 React Bits Pro `SKILL.md`。

配置要求：

- 如缺少 shadcn/ui，先让项目完成 `npx shadcn@latest init` 或遵循项目既有 shadcn 初始化流程。
- 在 `components.json` 中只合并 `registries`，不要覆盖 `$schema`、`style`、`tailwind`、`aliases` 等既有字段。
- `@reactbits-starter` registry URL 使用 `https://pro.reactbits.dev/api/r/starter/{name}.json`，Authorization header 使用 `Bearer ${REACTBITS_LICENSE_KEY}`。
- `@reactbits-pro` registry URL 使用 `https://pro.reactbits.dev/api/r/pro/{name}.json`，仅在需要 Pro / Ultimate blocks 时配置。
- 如果其他前提都满足，但项目环境中没有安装对应 React Bits Pro Skill，先在项目根目录执行 `npx shadcn@latest add @reactbits-starter/skill`。该命令是项目级安装，不是全局安装。
- 只有 React Bits Pro Skill 安装成功、项目中出现对应 `SKILL.md`，且当前环境能读取 `REACTBITS_LICENSE_KEY` 后，才读取该 Skill 并继续安装 components / blocks。
- 安装组件时优先使用 shadcn CLI；组件按项目样式栈选择 Tailwind `-tw` 或 CSS `-css` 变体，blocks 使用 `@reactbits-pro/<name>`。

跳过条件：

- 非 React 前端、TanStack 的 Vue / Solid / Svelte 等非 React adapter、Vue / Svelte / Angular / 原生 HTML 项目、后端任务、测试任务、文档任务。
- 项目未使用 shadcn/ui，且用户没有要求引入 shadcn。
- 当前环境无法读取 `REACTBITS_LICENSE_KEY`，缺少 registry，或 React Bits Pro Skill 未安装且无法安装 / 安装失败。
- 项目已有明确组件库 / design system 且需求不要求 React Bits Pro。

如果跳过 React Bits Pro Skill，应说明具体缺失前提，并继续使用项目已有组件库、`ui-ux-pro-max`、`impeccable` 或普通前端实现流程。

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
- 读取相关 `.trellis/spec`；其中 `.trellis/spec/lessons.md` 只作为短入口和高优先级摘要。
- 不要默认读取完整 `.trellis/lessons/**`；先通过 `.trellis/lessons/index.md`、tags、错误信息或当前任务主题按需检索，再读取命中的 topic / archive 文件。
- 如果存在当前活跃任务，优先读取 `prd.md`、`design.md`、`implement.md`。
- 不要绕过 `.trellis/workflow.md` 或手动跳过 Trellis phase。
- 不要把一次性任务计划写入 `.trellis/spec`；长期规范、架构决策、业务规则变化才应沉淀到 `.trellis/spec`。
- 使用 registry-backed spec templates 时，`trellis update` 可能刷新 `.trellis/spec`；必须复核 hash / conflict 提示和实际 diff，不要静默覆盖项目长期规范。

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
- 如果项目存在 `.gitnexusrc` 或需要指定默认分支，遵循项目配置；必要时使用 `gitnexus analyze --default-branch <branch>` 重新分析。
- 当影响分析结果存在同名符号、跨文件歧义或输出过大时，优先使用 GitNexus 的 `uid` / `file` / `kind` 约束和分页 / summary-only 能力缩小范围。
- 通过 GitNexus MCP 枚举已索引仓库时，`list_repos` 可能返回分页对象；使用 `limit` / `offset` 翻页直到 `pagination.hasMore` 为 false，不要把单页结果当作完整仓库列表。
- 对跨服务 API、HTTP route / consumer、gRPC 或前后端调用链的结论，必须回到实际路由、客户端调用和 diff 交叉核对。
- 如果需要移除 GitNexus 集成，优先使用 `gitnexus uninstall` 的 dry-run 查看将删除的 MCP 配置、Skill 和 hooks；只有用户明确确认后才加 `--force`，并复核配置 diff。
- 可选 tree-sitter grammar 缺失、跳过或回退构建不一定代表 `gitnexus analyze` 失败；若输出提示 optional grammar、prebuild / toolchain fallback 或 `GITNEXUS_SKIP_OPTIONAL_GRAMMARS`，把相关语言覆盖作为风险记录，并结合实际源码和查询结果复核。
- 大仓库分析中出现 skipped large files、内存墙、FTS 损坏或 repair 提示时，把这些作为索引完整性风险；需要时运行 GitNexus 提供的修复或重建命令后再依赖结果。
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
- 中大型项目内需求：`grill-with-docs` → 需求确认摘要 → `to-prd` → `to-issues` 输出 Trellis-ready Markdown tasks → Trellis workflow → GitNexus impact-analysis → Codex implementation → 项目测试 / TestSprite（MCP / 配置门户可用时）；如果需要把 Web UI 回归路径固化为入库测试资产，再使用 `web-ui-autotest-generator`。
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
- 如果 channel workflow 或 `trellis channel spawn` 提示缺少 `.trellis/agents/<name>.md`，先运行 `trellis update` 生成 channel runtime agent 定义，再继续。
- Channel 结论必须整理回 task artifacts 或 `.trellis/spec`。
- Channel runtime、events、forum、thread、原始 worker 日志默认不要提交到远程仓库。

---

## 目录规则

按项目策略保留或提交：

- `.trellis/spec/`
- `.trellis/lessons/`
- `.trellis/agents/`
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

## TestSprite / E2E 验证辅助

TestSprite 用于测试计划、UI/E2E、API 集成和回归验证辅助，不替代项目已有 lint、unit test、integration test、build、浏览器检查或人工测试评审。

启用条件：

- 当前环境已配置 TestSprite MCP server 和 API Key，且 MCP 工具可调用。
- 需求涉及端到端业务流程、UI、API 集成、测试计划生成、回归验证或 Trellis 验收需要 TestSprite 辅助。
- 本地应用、测试环境或 API 服务可访问，并能确认 `projectPath`、`localPort`、测试类型和测试范围。

使用规则：

- 使用前先读取项目 PRD、Trellis task artifacts、README、API 文档和现有测试；必要时先整理 PRD 草稿、测试范围、登录需求、环境 URL、测试账号需求和补充执行说明。
- 当前官方流程中，`testsprite_bootstrap_tests` 会打开 Testing Configuration / Configuration Portal。不要把配置页面、PRD 上传、测试账号或认证信息填写描述成可由 Codex 后台自动跳过。
- Codex 可以准备 PRD 文件、测试需求摘要、端口、MCP 参数和 `additionalInstruction`；配置门户中的测试类型 / 范围、应用 URL、PRD 上传、测试账号或认证方式仍需按 TestSprite 页面完成。
- 只有用户明确授权浏览器自动化且不涉及敏感真实凭据时，才可协助填写本地配置页面中的非敏感信息。真实账号、密钥、PII 和生产数据不得写入仓库、PRD、测试代码、日志或报告。
- 如果 TestSprite MCP 不可用、配置门户未完成、登录凭据缺失、PRD 未上传或测试环境不可访问，只输出阻塞说明、已准备材料和剩余配置项，不强行声称已完成 TestSprite 测试。
- TestSprite 产物默认按项目策略处理：`test_plan.json` 和 `_prd.json` 倾向保留；具体测试执行代码、报告、截图、trace、video 和临时结果默认不提交，除非团队明确要固化。

---

## Web UI / E2E 测试资产

普通 UI 检查优先使用项目已有验证、浏览器 / 截图检查和 TestSprite 辅助；只有需要把 Web UI 回归路径固化到项目仓库时，才启用 `web-ui-autotest-generator`。

启用条件：

- 用户明确要求生成 Web UI 自动化测试、Playwright、E2E suite 或 UI 回归测试代码。
- 关键 Web UI 业务流需要长期回归，例如登录后流程、CRUD、表单校验、权限、跨页面流转、下载 / 上传。
- 项目已有 Playwright，需要扩展可维护测试覆盖。
- Trellis 任务验收标准明确包含 Web UI/E2E 且需要可重复运行的入库测试资产。

使用规则：

- 优先沿用项目已有 Playwright / Cypress / 测试目录 / fixture / mock / CI 约定；不要因为默认模板存在就切换测试框架。
- 先生成或复核 `ui-test-manifest.json`、`ui-selector-audit.json`，再扩展 Page Object 和 spec；清单错误时先修清单。
- 没有稳定测试账号、测试环境、数据准备、清理策略或业务规则时，只输出阻塞说明和覆盖缺口，不强行生成脆弱测试。
- 不写入真实生产账号、密钥、PII 或生产数据。需要测试账号和环境变量时，只写占位说明。
- 只有用户明确同意修改产品代码时，才补充 `data-testid`、`data-cy` 或可访问名称等测试选择器。
- 生成后必须运行可用的项目验证和 E2E 命令；无法运行时说明尝试命令、阻塞原因、替代检查和剩余风险。

产物策略：

- 可按项目策略提交：`tests/e2e/`、Page Object、fixture、必要 mock、`playwright.config.*`、必要 package scripts 和 CI 配置。
- 按团队审查策略决定是否提交：`ui-test-manifest.json`、`ui-selector-audit.json`、`ui-test-coverage.json`、`tests/e2e/reports/summary.md`。
- 默认不要提交：`playwright-report/`、`test-results/`、trace、video、screenshot、HTML report、一次性 `ui-test-repair-plan.json`。

`web-ui-autotest-generator` 不替代 TestSprite。TestSprite 继续作为测试计划、E2E 和回归验证辅助；`web-ui-autotest-generator` 只在需要 repo-resident Playwright 测试资产时补充。

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

Trellis 项目默认采用分层 lessons 结构：

- `.trellis/spec/lessons.md`：必读短入口，只保存高优先级摘要、读取协议和索引指引。
- `.trellis/lessons/index.md`：按 `id`、tags、适用场景和详情路径维护索引。
- `.trellis/lessons/topics/<topic>.md`：保存分主题 lesson 详情。
- `.trellis/lessons/archive/YYYY-QN.md`：保存低频历史归档，默认不读。

记录 lesson 时，默认写入 `.trellis/lessons/topics/<topic>.md` 并更新 `.trellis/lessons/index.md`；只有跨任务高频、缺失会反复导致错误的摘要才同步到 `.trellis/spec/lessons.md`。不要把完整 lesson 历史长期堆在 `.trellis/spec/lessons.md`。

除非用户明确指定或更深层 `AGENTS.md` 改写，否则不写入其他位置。只有确认项目没有使用 Trellis 时，才默认写入到 `docs/lessons.md`。
