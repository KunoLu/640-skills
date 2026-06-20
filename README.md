# Kuno Workflow 模板配置说明

本仓库是 Codex 配置、Agent 规则模板、Skill 模板和 onboard 自动化的摘录/同步源，不代表一个真实业务项目结构。当前主流程收敛为：

```text
Codex + GitNexus + Trellis + Chrome DevTools MCP + Playwright + Maestro
```

其中 Chrome DevTools MCP 负责 Web 运行时诊断，Playwright CLI 负责 Web 可重复回归，Maestro 负责移动 App E2E 和可选跨端 smoke。`web-ui-autotest-generator` 是可选专项分支，只在需要把 Web UI 回归路径固化为仓库内 Playwright 测试资产时启用。

## 仓库定位

本仓库维护以下源文件：

| 路径 | 用途 |
|---|---|
| `ENTRYPOINT.md` | 版本监控配置和工作流总入口。 |
| `AGENTS.md` | 本仓库自身直接生效的补充规则。 |
| `README.md` | 当前工作流的详细说明文档。 |
| `README.html` | 当前工作流的静态 HTML 说明页。 |
| `docs/lessons.md` | 本仓库长期经验记录，执行仓库操作前必须先读取。 |
| `kuno-workflow-onboard-skills/SKILL.md` | onboard Skill 入口说明。 |
| `kuno-workflow-onboard-skills/REFERENCE.md` | onboard、安装、检测和工具配置参考。 |
| `kuno-workflow-onboard-skills/scripts/onboard.py` | init、reset、安装和检测自动化脚本。 |
| `kuno-workflow-onboard-skills/templates/agents/AGENTS.global.md` | 全局 Agent 规则模板。 |
| `kuno-workflow-onboard-skills/templates/agents/AGENTS.project.md` | 项目级 Agent 规则模板，不在普通 sync 中同步。 |
| `kuno-workflow-onboard-skills/templates/skills/**/SKILL.md` | 全局 Skill 模板。 |
| `kuno-workflow-onboard-skills/templates/project/.gitignore` | 新项目模板 `.gitignore`。 |

普通修改任务只更新本仓库内的源文件。只有用户明确输入 `sync` 或 `同步` 时，才把允许列表中的全局规则和 Skill 同步到本地生效路径；`AGENTS.project.md` 不在普通 sync 范围内。

## 工作流主线

模板遵循“项目事实优先、工具强证据启用、修改最小可验证”的原则。

```text
读取规则和 lessons
  -> 澄清需求与 SBTD 判断
  -> Trellis / GitNexus / Skill 按证据启用
  -> 实现或配置修改
  -> 项目原生验证
  -> BDD / Web / Mobile / 发布风险补充验证
  -> 最终报告状态、跳过原因、剩余风险
```

关键边界：

- Trellis 负责复杂任务生命周期、任务产物和阶段门禁，不强制用于所有小任务。
- GitNexus 只有在 MCP 可用且项目索引有效时使用，作为影响分析和变更检测辅助。
- Skill 按场景调用，不替代项目规范、Trellis 产物、测试或人工判断。
- Web 和 Mobile 验证工具分工明确，不把诊断、探索和可重复测试混为一谈。
- 任何工具不可用时，要标记 `blocked`、`skipped` 或 `not-needed`，不能声称对应验证已通过。

## SBTD：SDD、BDD、TDD、DDD

SBTD 是本模板对 SDD、BDD、TDD、DDD 的组合简称。它不是单独的新工具，而是用于组织需求、设计、实现和验证的协作框架。

| 概念 | 全称 | 在模板中的作用 |
|---|---|---|
| SDD | Specification-Driven Development | 用 PRD、design、implement、验收标准和长期规则说明“要做什么、为什么做、怎么验证”。在 Trellis 项目中，对应任务产物和 `.trellis/spec` 的长期规则。 |
| BDD | Behavior-Driven Development | 用 Given / When / Then 或项目已有 Gherkin 约定固化用户可见行为。新增或修改 UI、API、CLI、权限、错误、状态变化和外部集成可观察行为时，默认需要持久 BDD 场景。 |
| TDD | Test-Driven Development | 对 bug 修复、核心业务逻辑、算法、数据转换、高风险路径和回归敏感模块采用测试先行。BDD 固化可观察行为，TDD 把它转成可执行测试和红绿重构循环。 |
| DDD | Domain-Driven Design | 在业务术语、规则、bounded context 或模型边界不清时，用统一语言、CONTEXT、ADR 和 `book-ddd-distilled-modeling` 降低歧义。 |

推荐顺序不是死板流程，而是风险驱动：

1. 领域语言或边界不清时，先做 DDD 轻量建模。
2. 需求需要沉淀时，用 SDD 写清规格、范围和验收。
3. 有用户可见行为时，用 BDD 固化场景。
4. 需要高信心实现时，用 TDD 让测试驱动代码变化。

## 工具职责边界

| 工具 | 主责 | 不负责 |
|---|---|---|
| Chrome DevTools MCP | Web 运行时诊断、真实 Chrome 检查、console、network、storage、performance trace、screenshot 证据。 | 不作为 CI gate，不替代 Playwright E2E。 |
| Playwright CLI / `@playwright/test` | 项目内 Web E2E、Web 回归、跨浏览器检查和 CI gate。 | 不默认全局安装；项目未安装时必须先询问。 |
| Playwright MCP | Agentic Web 探索、可访问性快照、locator 辅助和临时页面检查。 | 不替代项目内 `playwright test`。 |
| Maestro CLI | Android、iOS、React Native、Flutter、Hybrid App E2E，以及可选 Chromium Web smoke。 | 不作为 Web 回归主责；Web 只做 smoke。 |
| Maestro MCP | 依赖 `maestro mcp` 的增强入口，用于设备检查、view hierarchy、截图和 flow 辅助。 | 不单独替代 Maestro CLI。 |
| `web-ui-autotest-generator` | 生成和审计 repo-resident Playwright 测试资产、选择器和覆盖率报告。 | 不执行 E2E；执行底座仍是项目内 Playwright CLI。 |

同一浏览器上下文同一时间只允许一个 controller，避免 Chrome DevTools MCP、Playwright MCP 和 Playwright CLI 互相污染状态。

## Playwright 集成策略

Playwright CLI 是项目级 Web E2E 依赖，不是全局默认工具。

检测顺序：

1. 检查目标项目是否有 `package.json`。
2. 检查 `@playwright/test`、`playwright` 依赖、Playwright 配置、`tests/e2e` 或 E2E scripts。
3. 如果 Web 回归或 `web-ui-autotest-generator` 需要 Playwright，但项目内缺失 CLI，先询问用户是否安装到项目 devDependency。
4. 用户确认后按项目包管理器安装，安装成功后继续验证流程。
5. 用户拒绝或安装失败时，`Playwright CLI` 标记 `skipped-by-user` 或 `blocked`，`Playwright Web Tests` 标记 `blocked` 或 `skipped`。

Fallback：

- 可使用 Chrome DevTools MCP 做运行时诊断。
- 可使用 Playwright MCP 做页面探索、可访问性快照或 locator 辅助。
- 不能声称 Web E2E 或回归测试已通过。

## Maestro 集成策略

Maestro 面向移动 App 和 Hybrid App E2E。模板不推荐用 Maestro 主做 Web 回归；Web 场景只适合做少量 Chromium smoke，主责仍在 Playwright CLI。

检测和安装顺序：

1. 需要 Maestro 前先检查 Java 17+。
2. 优先执行 `java --version`，失败时回退 `java -version`。
3. Java 缺失或低于 17 时，说明 Maestro 需要 Java 17+。
4. 默认建议安装 OpenJDK Temurin 21 最新 JDK，下载来源为 `https://github.com/adoptium/temurin21-binaries/releases`。
5. 用户指定其他 Java 版本时，只允许安装 Java 17 或更高版本，拒绝任何低于 17 的版本。
6. Java 通过后检查 Maestro CLI。
7. Maestro CLI 缺失时询问用户是否安装到开发环境或 CI runner。
8. Maestro CLI 可用后再检查 Maestro MCP。

Fallback：

- Maestro MCP 缺失但 CLI 可用时，继续使用 `maestro test` 执行已有 flow，并单独报告 MCP 状态。
- Maestro CLI 缺失且用户拒绝安装时，`Maestro Mobile` 标记 `blocked` 或 `skipped`。
- 设备、模拟器、app binary、appId、bundleId、测试账号或环境不可用时，必须记录阻塞原因。

## Chrome DevTools MCP 和 Playwright MCP

这两个 MCP 都是 Agent 交互能力，不是项目依赖。

- Chrome DevTools MCP：用于真实 Chrome 运行时诊断，适合白屏、console error、network、cookie、storage、性能 trace、截图和临时复现。
- Playwright MCP：用于 Agentic Web 探索、可访问性快照、locator 生成辅助和页面结构理解。

MCP 配置由 Agent 或 IDE 提供。模板只做检查和引导，不把 MCP 配置文件复制进业务项目。

## `web-ui-autotest-generator` 使用边界

`web-ui-autotest-generator` 只在需要生成、审计或评估可入库 Web UI 测试资产时启用。

适用场景：

- 用户明确要求生成 Web UI 自动化测试、Playwright、E2E suite 或 UI 回归测试代码。
- 关键 Web UI 用户路径需要进入仓库长期维护。
- 项目已有 Playwright，需要扩展可维护覆盖。
- Trellis 验收要求可重复 UI 回归。
- Chrome DevTools MCP、Playwright MCP、Playwright CLI 或人工复核发现了应进入 CI / 本地 E2E 的覆盖缺口。

不适用场景：

- 只需要一次性页面诊断。
- 只需要截图或 console / network 证据。
- 不准备把测试资产长期维护到仓库。
- 项目不接受 Playwright CLI 或测试数据、账号、环境暂不可用。

## 最终验证工具栈

最终验证阶段按以下顺序和风险叠加：

| 层级 | 工具 / 方法 | 触发条件 | 状态要求 |
|---|---|---|---|
| 项目原生验证 | lint、typecheck、unit、integration、build、项目 README / Makefile / CI 命令 | 修改代码后默认执行可用的最小有效验证 | 记录命令和结果 |
| BDD 追踪 | `gherkin-bdd`、`.feature`、BDD runner 或测试名追踪 | 新增或修改用户可见行为 | `BDD`: `run` / `traceable` / `blocked` / `skipped` |
| GitNexus | MCP 影响分析、变更检测 | GitNexus MCP 可用且项目索引有效 | 成功使用或说明跳过原因 |
| Web 诊断 | Chrome DevTools MCP | 需要真实浏览器现场证据 | `diagnosed` / `inspected` / `blocked` / `skipped` / `not-needed` |
| Web 回归 | Playwright CLI | Web UI、路由、表单、权限、跨页面流程、API 集成、浏览器兼容 | `Playwright Web Tests`: `run` / `failed` / `blocked` / `skipped` |
| Web 测试资产 | `web-ui-autotest-generator` | 需要把 Web UI 回归固化入仓库 | `generated` / `coverage-only` / `blocked` / `skipped` |
| Mobile / Hybrid E2E | Java 17+、Maestro CLI、Maestro MCP | Android、iOS、RN、Flutter、Hybrid App 用户旅程 | `Maestro Mobile`: `run-local` / `run-cloud` / `blocked` / `skipped` / `not-needed` |
| 发布风险 | `book-release-readiness`、Channel preflight | 生产路径、外部集成、部署敏感或高风险变更 | 记录风险、fallback、rollback |

全局工具状态建议在最终输出中集中列明：

- `Chrome DevTools MCP`: `diagnosed` / `inspected` / `blocked` / `skipped` / `not-needed`
- `Playwright MCP`: `explored` / `locator-assisted` / `blocked` / `skipped` / `not-needed`
- `Playwright CLI`: `available` / `installed` / `missing` / `skipped-by-user` / `blocked`
- `Playwright Web Tests`: `run` / `failed` / `blocked` / `skipped`
- `Java`: `available` / `installed` / `missing` / `incompatible` / `blocked` / `skipped-by-user`
- `Maestro CLI`: `available` / `installed` / `missing` / `skipped-by-user` / `blocked`
- `Maestro MCP`: `available` / `configured` / `unavailable` / `blocked` / `skipped`
- `Maestro Mobile`: `run-local` / `run-cloud` / `blocked` / `skipped` / `not-needed`
- `Maestro Web Smoke`: `run` / `blocked` / `skipped` / `not-needed`
- `Web UI 测试资产`: `generated` / `coverage-only` / `blocked` / `skipped`

## 模板 `.gitignore` 测试产物策略

项目模板忽略本地运行态和报告产物，保留可维护测试资产。当前测试相关片段如下：

```gitignore
# ---------- Testing -----------
# MCP / browser controller local state
.chrome-devtools-mcp/
.playwright-mcp/

# Playwright runtime artifacts
playwright-report/
test-results/
blob-report/

# Web UI autotest generated run artifacts
ui-test-repair-plan.json
tests/e2e/reports/results.json
tests/e2e/reports/junit.xml
tests/e2e/reports/html/
tests/e2e/**/screenshots/
tests/e2e/**/videos/
tests/e2e/**/traces/
tests/e2e/**/*.trace.zip

# Maestro runtime artifacts
# Keep .maestro/*.yaml flows versioned; ignore only local runtime output.
.maestro/cache/
.maestro/tmp/
.maestro/runs/
.maestro/reports/
maestro-report/
maestro-results/
maestro-artifacts/
```

`.maestro/*.yaml` flow 默认应可入库维护；运行时 cache、runs、reports 和 artifacts 不入库。Playwright report、trace、video、screenshot 和一次性 repair plan 默认不入库。

## onboard / reset 检查范围

`kuno-workflow-onboard-skills` 的 init / reset / check 逻辑需要覆盖：

- 全局 Agent 规则和项目级 Agent 模板。
- Trellis、project-validation、gherkin-bdd、lessons、book-derived skills 等模板 Skill。
- GitNexus MCP 手动配置检查。
- Chrome DevTools MCP 手动配置检查。
- Playwright MCP 手动配置检查。
- Playwright CLI 项目级检测和安装引导。
- Java 17+、Maestro CLI 和 Maestro MCP 检测及安装引导。
- `web-ui-autotest-generator`、`ui-ux-pro-max`、`impeccable` 等可选 Skill 的存在性检查。

MCP 配置通常无法仅通过仓库文件完全证明，模板只做状态检查和配置指引。CLI 安装必须遵循用户确认和 fallback 规则。

## 同步规则

当用户输入 `sync` 或 `同步` 时：

1. 读取同步源文件并确认路径正确。
2. 只同步根 `AGENTS.md` 中允许列表里的全局规则和全局 Skill。
3. 不同步 `kuno-workflow-onboard-skills/templates/agents/AGENTS.project.md`。
4. 用 `cmp -s` 或等价方式确认源文件与目标文件一致。
5. 不修改 `ENTRYPOINT.md` 版本号。
6. 不归档 `UPDATE.md`。
7. 不提交或推送变更。

## README 同步规范

后续每次模板内容有更新，都必须评估 `README.md` 和 `README.html` 是否需要同步更新。

必须同步 README 的典型情况：

- 工作流主线、工具职责或边界发生变化。
- SDD、BDD、TDD、DDD 或 SBTD 的定义、触发条件、产物位置发生变化。
- Chrome DevTools MCP、Playwright CLI、Playwright MCP、Maestro CLI、Maestro MCP 或 `web-ui-autotest-generator` 的检测、安装、fallback 或报告状态发生变化。
- `kuno-workflow-onboard-skills/scripts/onboard.py` 的 init、reset、安装或检查行为发生变化。
- 模板 `.gitignore`、同步路径、AGENTS 模板路径或 Skill 模板路径发生用户可见变化。
- 最终验证阶段的工具栈或报告格式发生变化。

如果评估后不需要更新 README，最终输出要说明原因。若需要更新，应在同一轮修改中立即更新 `README.md` 和 `README.html`，保持两者与模板源一致。

## 更新和版本检查

每日版本检查自动化以 `ENTRYPOINT.md` 的版本监控表为基线，更新分析写入 `UPDATE.md`。只有用户输入 `update` 或 `更新` 时，才把 `UPDATE.md` 中的最新版本写回 `ENTRYPOINT.md` 并归档。

由 release 触发的 AGENTS 或 Skill 规则更新必须沉淀为长期通用规则，不把一次性版本区间写进长期执行规则。
