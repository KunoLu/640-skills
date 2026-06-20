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
3. 读取相关 `.trellis/spec`；其中 `.trellis/spec/lessons.md` 是短入口和高优先级摘要。
4. 不要默认读取完整 `.trellis/lessons/**`；先通过 `.trellis/lessons/index.md`、tags、错误信息或当前任务主题按需检索，再读取命中的 topic / archive 文件。
5. 如果存在当前活跃任务，读取：
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
7. 输出需求确认摘要、PRD / design / implement review gate 或 `task.py start` 前，必须说明 `grill-with-docs` 使用状态；未完整调用时，说明原因并询问用户是否需要先用该 Skill 再评估一次。
8. 用户确认摘要后，再使用 `to-prd` 生成 Markdown PRD；在 Trellis 项目中，PRD 终稿写入或更新 `.trellis/tasks/<task>/prd.md`。
9. PRD 确认后，再使用 `to-issues` 拆成 Trellis-ready vertical slices，标注依赖顺序、AFK / HITL、验收标准和测试策略；拆解结果应落为 `.trellis/tasks/<task>/...` 下的 parent / child task artifacts。
10. 最后按 `.trellis/workflow.md` 创建或选择 task，并继续 Trellis 阶段。

如果需求只是通用方案质询、没有项目文档或领域术语约束，可使用 `grill-me` 替代 `grill-with-docs`。

`$trellis-brainstorm` 可用于 Trellis 内澄清不明确需求，但当需求需要对照项目文档、领域语言或 ADR 时，不替代 `grill-with-docs`。

### grill-with-docs 使用状态透明度

在 Phase 1 planning、需求确认摘要、PRD / design / implement review gate、或 `task.py start` 前，按全局规则说明是否完整调用 `grill-with-docs`；未完整调用时说明原因，并询问用户是否需要先用该 Skill 再评估一次。

在需求确认摘要、PRD 或 task artifacts 尚未稳定前，不要执行 `$trellis-before-dev` 或开始实现。

## Workflow 模板规则

如果 Trellis 支持 workflow templates，可在初始化或后续通过 `trellis workflow` 选择 / 切换 workflow。

默认规则：

- 未经用户明确要求，不主动切换 workflow 模板。
- `native` 可作为默认标准 workflow。
- `tdd` 仅在用户明确要求 TDD、项目已经采用测试驱动流程，或当前任务属于高风险且适合测试先行的行为修改时使用。
- BDD 不是独立 workflow 模板；用户可见行为默认通过 `gherkin-bdd` 作为 workflow overlay 执行。
- `channel-driven-subagent-dispatch` 仅在用户明确要求 Channel / 多 Agent / sub-agent 分发流程时使用。
- 即使存在 `channel-driven-subagent-dispatch` 模板，也不得仅因任务复杂就自动切换或启用该模板。
- 切换 workflow 后，必须重新读取 `.trellis/workflow.md`，并以新文件为准。
- 如果 workflow 引用 `.trellis/agents/<name>.md` 但文件不存在，先运行 `trellis update` 生成缺失的 channel runtime agent 定义，再继续 Channel workflow。

判断原则：

- 复杂度决定是否进入 Trellis planning。
- 协作形态决定是否启用 Channel 或 channel-driven workflow。
- 大任务优先考虑 parent / child task，不默认切换到 Channel workflow。

Workflow 选择表：

| 场景 | 推荐方式 |
|---|---|
| 文档、配置说明、样式、小模板、低风险局部修改 | `native` workflow |
| bug 修复、核心业务逻辑、算法、数据转换、同步 / 导入 / 导出、需要回归测试的修改 | `native` workflow + 主动判定 `tdd` Skill |
| 权限、计费、状态机、关键数据一致性、复杂算法、高风险后端逻辑或项目已明确采用测试驱动流程 | Trellis `tdd` workflow + `tdd` Skill |
| UI、API、CLI、导出文件、通知、权限结果、错误响应、状态变化或外部集成可观察行为 | 当前 workflow + `gherkin-bdd` overlay |

不要为了“更重视测试”而把所有任务默认切到 Trellis `tdd` workflow；优先在 `native` 中按需调用 `tdd` Skill。只有任务本身需要把测试先行变成阶段约束时，才切换到 Trellis `tdd` workflow。

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
- 在 bug 修复、核心业务逻辑、算法、数据转换、同步 / 导入 / 导出、高风险修改或需要回归测试时，必须主动判定是否使用 `tdd` Skill。
- 如果主动判定后跳过 `tdd` Skill，最终输出要说明原因，例如缺少可测试接口、项目没有测试框架、修改只是文档 / 配置、或当前风险已由现有测试覆盖。
- 不为简单文案、样式、配置说明或纯文档修改强制使用 `tdd`。

---

## BDD Overlay 与 `gherkin-bdd` Skill

BDD 是用户可见行为的默认硬规则，不替代 Trellis workflow。Trellis 管任务生命周期，`gherkin-bdd` 管用户可见行为规格。

适用范围：

- UI、API、CLI、导出文件、通知、权限结果、错误响应、状态变化和外部集成系统可观察行为。
- 用户可见 bug 修复。
- Trellis `prd.md`、`design.md`、`implement.md` 或验收标准中出现的用户可见行为。

跳过范围：

- 纯内部重构、依赖 / 工具配置、机械格式化。
- 不改变行为或语义的 typo、视觉 polish、className / token / CSS 重构、布局清理。

语言规则：

- 已有 `.feature` 或项目级持久 BDD 规格时，沿用同一 bounded context 或功能区的既有语言和关键词风格。
- 项目没有 `.feature` 且用户未明确要求其他语言时，默认使用中文场景标题、描述和步骤文本，并使用英语 Gherkin 结构关键字。
- 英文 PRD、design、implement、代码标识符或产品名不能覆盖上述默认语言决策；领域专名可按 glossary / `docs/CONTEXT.md` / `.trellis/spec` 保留。

阶段编排：

1. 需求 / PRD 阶段：`prd.md` 可以草拟 Given/When/Then，但用户可见行为在实现前必须进入持久 `.feature` 或项目级规则指定的持久 BDD 规格路径。
2. 语言决策：创建或改写 `.feature` 前，先检查既有 `.feature`、BDD runner 配置和项目规则；没有既有 `.feature` 且无用户覆盖时，明确记录“中文场景文本 + 英文 Gherkin 关键词”。
3. 领域术语不清时：先使用 `grill-with-docs` 和 `book-ddd-distilled-modeling`，再定稿场景文本。
4. 开发前：运行 `$trellis-before-dev` 前，确认新增 / 修改 / 修复的用户可见行为已有对应 BDD 场景，或明确 BDD 跳过原因；同时确认场景文本符合语言决策。
5. 开发中：从 BDD 场景派生测试。已有 Gherkin runner 时绑定 step definitions 或 runner 测试；没有 runner 时使用项目已有测试框架，并用测试名、注释、目录结构或项目约定追踪到场景。
6. bug 修复：先写正确行为场景，再写失败回归测试，再修复。
7. `$trellis-check`：核对 PRD、持久 `.feature`、测试和代码是否一致，并检查 `.feature` 语言状态是否为沿用项目既有风格、默认中文场景文本 + 英文关键词、用户明确覆盖或已阻塞。

既有项目采用 `no new uncovered behavior`：未触碰的历史行为可以暂时没有 `.feature`；新增或触碰的用户可见行为必须补齐。

默认持久路径：

- 已有 `.feature` / BDD runner / 项目规则时沿用项目约定。
- 单应用项目默认 `<project-root>/features/<capability-slug>.feature`。
- monorepo 默认落在 owning workspace 下的 `features/**/*.feature`。
- `.trellis/tasks/**` 只保存过程产物，不作为默认长期行为 source of truth。

对已确认用户可见行为，持久 `.feature` 是行为 source of truth；PRD 说明背景和意图，`design.md` / `implement.md` 说明技术方案。冲突时先对齐 PRD 与 `.feature`，再实现。

---

## 任务产物

- `prd.md`：需求、约束、验收标准
- `design.md`：技术设计
- `implement.md`：实现计划

当前任务产物优先于通用假设。

`.trellis/spec` 只保存长期项目规则。

`.trellis/spec/lessons.md` 是 lessons 的必读短入口，不是完整历史库。完整 lesson 默认保存在：

- `.trellis/lessons/index.md`
- `.trellis/lessons/topics/<topic>.md`
- `.trellis/lessons/archive/YYYY-QN.md`

不要默认全文读取 `.trellis/lessons/**`；根据当前任务、错误信息、工具名、语言、tags 或 index 的 `read_when` 命中后，再读取对应 topic 或 archive。

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

## Trellis 更新与迁移

升级 Trellis、切换模板或发现生成文件缺失时，优先运行 `trellis update`，并在运行后重新读取 `.trellis/workflow.md`、相关 `.trellis/spec` 和当前 task artifacts。

- 如果上游 migration manifest 建议迁移，或项目中存在拼写错误的 `trellis-spec-bootstarp/` skill 目录，运行 `trellis update --migrate`，让 Trellis 处理跨平台目录重命名。
- `trellis update` 可能安装新的 bundled skills、平台模板或 `.trellis/agents/{check,implement}.md` channel runtime 文件；这些是生成的 Trellis workflow 资产，不等同于 channel runtime 日志。
- 当 Trellis 新增或重命名 AI 平台时，复核生成的 commands、skills、agents、shared skills 目录和项目 `.gitignore` / 提交策略；不要把可复用的平台模板目录、runtime 日志和本地缓存混为一类。
- 对可选平台 hooks、statusline 或状态栏类增强，不要假设 `trellis update` 会强制安装、删除或改写；只有在用户选择对应 init/update flag、项目已有配置或 manifest 明确要求时才启用，并复核生成 diff。
- 使用 registry-backed spec templates 时，`trellis update` 可能刷新 `.trellis/spec`；必须复核 hash / conflict 提示和实际 diff，不要静默覆盖项目长期规范。
- 当 Trellis 更新涉及 workflow phase、step 编号、状态路由或 resume / continue 行为时，更新后必须复核生成的 workflow、`/continue` 命令、workflow variants、bundled skill 参考和平台 prompt 是否仍与 `.trellis/workflow.md` 对齐；不要只检查带 `Phase X.Y` 字样的引用，也要检查裸编号路由。
- 如果命令提示 workflow 引用的 `.trellis/agents/<name>.md` 缺失，先运行 `trellis update`，再重试 workflow 或 Channel 操作。

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
- 持久 `.feature` 或项目级规则指定的 BDD 规格路径，适用于用户可见行为
- `design.md` / `implement.md`，如果存在
- `.trellis/spec`
- `.trellis/spec/lessons.md` 和按需命中的 `.trellis/lessons` topic / archive
- 实际代码 diff
- 验证命令结果

不得在未执行 $trellis-check 的情况下完成任务。

---

## Book-derived Skill Gate

在需求、设计、实现和验证阶段，必须按当前任务主风险主动判定 bundled book-derived skills 是否适用。它们是专项审查视角，不替代 `.trellis/workflow.md`、task artifacts、`.trellis/spec`、GitNexus、`tdd`、项目验证、Playwright、Maestro、Chrome DevTools MCP 或人工判断。

不要把 5 个 book-derived Skill 当作固定 checklist 全量调用；优先选择当前主风险对应的 1-2 个。

阶段编排：

- 需求 / PRD 阶段：业务术语、领域规则、bounded context 或模型边界不清时，先用 `grill-with-docs` 读取项目事实并澄清，再用 `book-ddd-distilled-modeling` 固化任务级语言，最后进入 `to-prd` / `to-issues`。
- 设计阶段：存储、事件、队列、缓存、迁移、schema 演进、数据所有权或跨服务数据流发生变化时，在 `design.md` / `implement.md` 稳定前使用 `book-ddia-data-design`。
- 开发前 / 开发中：既有结构阻碍当前修改、行为变更与结构整理可能混杂时，使用 `book-refactoring-pass` 规划行为保持型小步重构。
- 遗留代码修复：测试不足、行为不清、隐藏依赖或回归风险高时，在修改前使用 `book-legacy-change-safety`，并优先补 characterization test 或等价安全网。
- 验证 / 发布前：生产路径相关的服务、API、后台任务、队列、外部集成或部署敏感变更，在项目验证后、测试工具 gate / Channel preflight 前使用 `book-release-readiness`。

book-derived Skill 的结论优先写入当前 task 的 `prd.md`、`design.md`、`implement.md` 或 check summary。只有长期架构、API、数据模型、权限、业务规则或技术约定才进入 `.trellis/spec`。

---

## 测试工具 Gate

在 `$trellis-check` 和项目验证后、Phase 3.4 commit plan 前，如果任务涉及 Web UI、API 集成、端到端流程、移动 App 用户旅程、Hybrid App、用户可见 bug 修复、发布前 smoke 或可重复回归验证，必须按项目级 `AGENTS.md` 和 `project-validation` Skill 主动判定 Chrome DevTools MCP、Playwright MCP、Playwright CLI、Maestro CLI、Maestro MCP 与 `web-ui-autotest-generator` 是否适用。

Trellis 阶段只负责以下要求：

- 不把 Chrome DevTools MCP、Playwright MCP、Playwright CLI、Maestro、Web UI 自动化测试资产当作 `$trellis-check`、项目验证或人工评审的替代品。
- Playwright CLI、Java、Maestro CLI、MCP 配置、测试账号、认证方式、测试环境、设备、模拟器、app binary、appId / bundleId 或服务 URL 不可用时，记录 `blocked`，不要声称已完成测试。
- 如果启用 `web-ui-autotest-generator`，Phase 3.4 commit plan 前必须确认脚本调用遵循全局 / 项目级 `AGENTS.md` 的 Web UI 测试资产路径契约，且可入库 JSON 资产位于 `tests/e2e/manifest/`：`ui-test-manifest.json`、`ui-selector-audit.json`、`ui-test-coverage.json`。
- `$trellis-check` 中必须核对项目根目录没有残留 `ui-test-manifest.json`、`ui-selector-audit.json`、`ui-test-coverage.json`。如发现残留，先迁移到 `tests/e2e/manifest/` 并同步引用；如无法迁移或确认，`Web UI 测试资产` 标记为 `blocked`，不得标记为 `generated`。
- 如生成失败分析 `ui-test-repair-plan.json`，默认路径为 `tests/e2e/manifest/ui-test-repair-plan.json`，并按项目 `.gitignore` 策略作为运行产物处理；除非用户明确要求整理为正式任务或报告，不把 repair plan 作为长期测试资产提交。
- Phase 3.4 commit plan 前必须按相关性记录 Chrome DevTools MCP、Playwright MCP / CLI / Web Tests、Java、Maestro CLI / MCP / Mobile / Web Smoke、Web UI 自动化测试资产的状态和原因。
- 状态取值和工具职责遵循全局 / 项目级 `AGENTS.md` 与 `project-validation` Skill；测试工具结论写入当前 task artifacts 或 check summary。

---

## 可选 Channel Review Gate

在 `$trellis-check` 和项目验证后、Phase 3.4 commit plan 前，如果用户明确要求代码 review、测试验证审查、并行评审或交叉验证，或当前任务满足高风险 review / validation 条件，可以调用 `trellis-channel` Skill 做 Channel preflight。

高风险 review / validation 条件包括：

- GitNexus impact / detect_changes 返回 HIGH 或 CRITICAL
- 验证失败后经过修复，需要独立复核失败原因和覆盖范围
- 变更跨越前端、后端、数据库、部署、测试资产、外部服务或发布流程
- PRD / design / implement 与实际 diff、验证结果或回滚策略需要独立一致性检查
- 多个验收标准、浏览器状态、E2E、API、Docker、Vercel、Playwright、Maestro 或 Chrome DevTools MCP 结果需要覆盖率审查

规则：

- 调用 `trellis-channel` Skill 做 preflight 不等于启动 Channel runtime。
- 除非用户已明确要求 Channel，或在 preflight 后明确确认，否则不得 spawn worker。
- Channel review / validation 不替代 `$trellis-check`、项目验证命令、GitNexus、Playwright、Maestro、Chrome DevTools MCP、浏览器检查或人工最终判断。
- 如果 Channel 发现必须修改代码，主会话应用已接受的修改后，必须重新运行聚焦验证和必要的 `$trellis-check`。
- Channel 有效结论必须写回当前 task artifacts；只有长期规则才写入 `.trellis/spec` 或 `.trellis/lessons`。

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
