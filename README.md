# Kuno Workflow 模板配置说明

本仓库是 Codex 配置、Agent 规则模板、Skill 模板和 onboard 自动化的摘录/同步源，不代表一个真实业务项目结构。当前主流程收敛为：

```text
Codex + GitNexus + Trellis + Chrome DevTools MCP + Playwright + Maestro
```

其中 Chrome DevTools MCP 负责 Web 运行时诊断，Playwright CLI 负责 Web 可重复回归，Maestro 负责移动 App E2E 和可选跨端 smoke。`web-ui-autotest-generator` 是可选专项分支，只在需要把 Web UI 回归路径固化为仓库内 Playwright 测试资产时启用；`shadcn` 是 shadcn/ui 项目的可选 external Skill，用于组件、registry、preset 和 CLI 工作流；`seo-geo` 是 bundled 的公开网站、落地页、文档站和营销页 SEO/GEO 搜索可见性检查分支；`maestro-mobile-e2e` 负责把 Mobile / Hybrid BDD 场景固化为仓库内 Maestro flow 资产。API、Web 和 Mobile / Hybrid 测试都以 BDD `.feature` 作为行为 SOT；前后端分仓或链路不完整时，先确认 contract、环境、账号、数据、设备和选择器事实，再决定 full-stack、contract-backed、mock-backed、app-mocked、smoke-only 或 blocked。

Codex plugin / connector、remote plugins、ChatGPT-hosted MCP 和 `tool_search` 属于 Agent 侧工具发现和授权能力，不是项目依赖。模板要求先确认当前会话实际暴露 callable tool，再依赖对应能力；catalog / marketplace / 本地远端版本展示只作为候选信号，session auth、OAuth、cookies 和 tokens 不写入仓库、日志、截图、报告或示例配置。

`rtk` 和 `caveman` 是上下文 / token 效率层，不是验证工具。`rtk` 作用于 shell / terminal 命令输出，普通非报告型命令默认优先作为命令前缀；unit / API / Playwright / Maestro 等报告型测试先评估缓存与文件写入风险。`caveman` 作用于 Agent 回复输出，安装后只表示可用，不自动开启；同一任务出现 3 次以上状态更新、5 个以上重复命令 / diff / 日志 / 文件摘要、上下文压力较大或自动化 / 大型 review / 验证排障进入重复轮次时，只建议用户切换，不静默启用。

## 仓库定位

本仓库维护以下源文件：

| 路径 | 用途 |
|---|---|
| `ENTRYPOINT.md` | 版本监控配置和工作流总入口。 |
| `AGENTS.md` | 本仓库自身直接生效的补充规则。 |
| `README.md` | 当前工作流的详细说明文档。 |
| `README.html` | 当前工作流的静态 HTML 说明页。 |
| `install.sh` | macOS / Linux 交互式安装入口，直接以 `kuno-workflow-onboard-skills` 目录作为 `source-root`。 |
| `install.ps1` | Windows PowerShell 交互式安装入口，参数语义与 `install.sh` 对齐。 |
| `docs/lessons.md` | Lessons 必读短入口；执行仓库操作前必须先读取。 |
| `docs/lessons/index.md` | Lessons 完整索引，按 tags、适用场景和详情路径检索。 |
| `docs/lessons/topics/**` | Lessons 完整详情，按当前任务命中后读取。 |
| `kuno-workflow-onboard-skills/` | onboard Skill 目录；普通 `sync` 时会作为完整 Skill 同步到 `/Users/lusonglin/.agent/skills/kuno-workflow-onboard-skills/`。 |
| `kuno-workflow-onboard-skills/SKILL.md` | onboard Skill 入口说明。 |
| `kuno-workflow-onboard-skills/REFERENCE.md` | onboard、安装、检测和工具配置参考。 |
| `kuno-workflow-onboard-skills/scripts/onboard.py` | init、reset、安装、检测、Trellis init 和 bootstrap 检测自动化脚本。 |
| `kuno-workflow-onboard-skills/templates/agents/AGENTS.global.md` | 全局 Agent 规则模板。 |
| `kuno-workflow-onboard-skills/templates/agents/AGENTS.project.md` | 项目级 Agent 规则模板，不在普通 sync 中同步。 |
| `kuno-workflow-onboard-skills/templates/skills/**` | 全局 Skill 模板目录，包含 `SKILL.md`、`references/`、`scripts/`、`assets/` 等。 |
| `kuno-workflow-onboard-skills/templates/project/.gitignore` | 新项目模板 `.gitignore`。 |

普通修改任务只更新本仓库内的源文件。只有用户明确输入 `sync` 或 `同步` 时，才把允许列表中的全局规则和 Skill 同步到本地生效路径；`AGENTS.project.md` 不在普通 sync 范围内。

## 工作流主线

模板遵循“项目事实优先、工具强证据启用、修改最小可验证”的原则。

```text
读取 `docs/lessons.md` 短入口，并按需读取 lessons index / topic
  -> 澄清需求与 SBTD 判断
  -> Trellis / GitNexus / Skill 按证据启用
  -> 实现或配置修改
  -> 项目原生验证
  -> BDD / Web / Mobile / 发布风险补充验证
  -> 最终报告状态、跳过原因、剩余风险
```

关键边界：

- Trellis 负责复杂任务生命周期、任务产物和阶段门禁，不强制用于所有小任务。
- 如果已确认当前目录是项目根目录，且存在项目级 `AGENTS.md`，但根目录没有 `.trellis/`，Agent 必须提示项目尚未执行 `trellis init`；普通项目操作默认不代用户执行。例外是 `kuno-workflow-onboard-skills` 的 `init` / `reset`：在 Trellis CLI 已可用、用户确认 username 和可选 platform flags 后，onboard 流程可以主动运行 `trellis init -u <username> ... --yes --skip-existing`。
- Trellis CLI 升级后，已有 `.trellis/` 的项目先运行 `trellis update` 刷新生成脚本和 filesystem-safety guard；对 uninstall、archive、Channel 名称等删除 / 移动 / 路径解析操作，不绕过 dirty-data、manifest ownership 和 safe-name guard。
- Codex remote plugins、connectors 和延迟加载工具以当前会话的 `tool_search`、工具列表或 MCP 可见性检查为准；候选 catalog 不等于已授权或已可调用。
- GitNexus 只有在 MCP 可用且项目索引有效时使用，作为影响分析和变更检测辅助。
- GitNexus 的 PDG、taint、trace、多分支索引和不同 MCP transport 属于显式 opt-in 能力；使用时必须记录模式 / 分支并回到源码与测试复核。
- Skill 按场景调用，不替代项目规范、Trellis 产物、测试或人工判断。
- AGENTS 模板只承载常驻上下文必须知道的路由、触发条件、硬性安全边界和最终报告要求；详细流程、命令参数、检查清单和专项判断优先放入对应 Skill 延迟加载。
- Web 和 Mobile 验证工具分工明确，不把诊断、探索和可重复测试混为一谈。
- SEO/GEO 只面向公开 Web 搜索可见性，不替代 Web 运行时诊断、Playwright 回归、发布检查或人工内容评审。
- 跨仓或链路不完整时，mock 只能基于 contract、schema、真实响应样例、既有 fixture 或用户明确确认；mock-backed 不能冒充 full-stack 通过。
- `rtk` 是命令输出压缩层，不是测试 runner。unit test、API / integration test、Playwright Web E2E、Maestro Mobile / Hybrid E2E 或任何需要落地报告的命令，必须先评估缓存 / 回放是否会跳过文件写入；报告型正式验证默认使用原生命令或项目明确的 no-cache / report-safe 命令，缺报或旧报时原生命令复验。
- API / Web E2E / Mobile E2E / Hybrid E2E 调试轮次可以保留多份带业务名、分支名和时间戳的本地报告快照；一旦 Playwright 或 Maestro 运行产生 runner 原生报告，或 API / integration / unit runner 生成了本轮需要保留的报告，无论最终全量是否通过，都要在下一次可能清空输出的运行前生成该次运行的命名报告和同目录同 stem 的中文 Markdown 汇总。Playwright 的同 stem 以命名后的 HTML 为准，不以 `results.json` 为准。
- API / integration 的中文 Markdown 汇总必须包含 URI 覆盖矩阵，将每条覆盖范围描述映射到具体 `method + URI path`、测试脚本 / case、预期状态码或副作用，以及 `.feature` / contract / schema 依据。
- 任何工具不可用时，要标记 `blocked`、`skipped` 或 `not-needed`，不能声称对应验证已通过。

## SBTD：SDD、BDD、TDD、DDD

SBTD 是本模板对 SDD、BDD、TDD、DDD 的组合简称。它不是单独的新工具，而是用于组织需求、设计、实现和验证的协作框架。

| 概念 | 全称 | 在模板中的作用 |
|---|---|---|
| SDD | Specification-Driven Development | 用 PRD、design、implement、验收标准和长期规则说明“要做什么、为什么做、怎么验证”。在 Trellis 项目中，对应任务产物和 `.trellis/spec` 的长期规则。 |
| BDD | Behavior-Driven Development | 用 Given / When / Then 或项目已有 Gherkin 约定固化用户可见行为。新增或修改 UI、API、CLI、权限、错误、状态变化和外部集成可观察行为时，默认需要持久 BDD 场景；分仓或跨端链路先做上下文完整性 gate。主动使用 `gherkin-bdd` 且请求包含 `sync` / `同步` 时，进入 BDD Sync Mode，全量扫描当前工作树与 `features/`，多仓时先确认其他仓库更新状态再同步 `.feature`。 |
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
| Codex `tool_search` / Plugin / Connector | 发现延迟加载工具、remote / local plugin、connector 和 ChatGPT-hosted MCP 能力。 | Catalog 或 marketplace 展示不等于已授权 / 已可调用；安装需用户明确请求，session auth / OAuth / cookies / tokens 不写入项目。 |
| Chrome DevTools MCP | Web 运行时诊断、真实 Chrome 检查、console、network、storage、performance trace、screenshot 证据。 | 不作为 CI gate，不替代 Playwright E2E。 |
| Playwright CLI / `@playwright/test` | 项目内 Web E2E、Web 回归、跨浏览器检查和 CI gate。 | 不默认全局安装；项目未安装时必须先询问。 |
| Playwright MCP | Agentic Web 探索、可访问性快照、locator 辅助和临时页面检查。 | 不替代项目内 `playwright test`。 |
| Maestro CLI | Android、iOS、React Native、Flutter、Hybrid App E2E，以及可选 Chromium Web smoke。 | 不作为 Web 回归主责；Web 只做 smoke。 |
| Maestro MCP | 依赖 `maestro mcp` 的增强入口，用于设备检查、view hierarchy、截图和 flow 辅助。 | 不单独替代 Maestro CLI；当前 Agent / IDE 的 MCP 配置需包含 `JAVA_HOME` / `PATH` env。 |
| `shadcn` | shadcn/ui 项目的组件、registry、preset、CLI、docs / diff 和组件组合规则。 | 不替代通用 UI/UX 设计判断、`impeccable` 视觉打磨或 React Bits Free / 付费 tier 判定。 |
| `web-ui-autotest-generator` | 生成和审计 repo-resident Playwright 测试资产、选择器和覆盖率报告。 | 不执行 E2E；执行底座仍是项目内 Playwright CLI。 |
| `seo-geo` | 公开网站、落地页、文档站、产品页、营销页的 SEO/GEO、schema、meta、robots / sitemap 和 AI 搜索可见性专项检查。 | 不替代 Chrome DevTools MCP、Playwright CLI、项目发布检查或内容评审；不用于内部后台、API、CLI、移动 App。 |
| `maestro-mobile-e2e` | 从 BDD `.feature` 派生和维护 repo-resident Maestro Mobile / Hybrid flow，约束报告路径，并按需加载真机排障 lesson。 | 不替代 BDD、项目验证或 Maestro CLI。 |
| `rtk` | 用户级全局 CLI，用于压缩 terminal 命令输出，降低上下文占用；缺失时先说明作用并询问是否协助安装。 | 不替代测试 runner；报告型 unit / API / Playwright / Maestro 命令先评估缓存与文件写入风险，必要时使用原生命令或 fallback-native。 |
| `caveman` | 用户级全局 Agent Skill，用于压缩 Agent 回复和长任务状态更新；缺失时先说明作用并询问是否协助安装；达到全局阈值时只建议用户后续切换。 | 不替代项目 Skill、BDD、TDD、验证、GitNexus、Trellis 或最终报告；安装后不自动开启，最终报告保持完整。 |

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

Web E2E 报告规则：

- 完整环境可用时跑 full-stack Playwright E2E；只有 contract 或 mock 环境时标记 `contract-backed` 或 `mock-backed`。
- `--reporter=list` 只用于诊断或定点重跑；Web E2E 进入正式验证范围时，最终收尾必须再跑不覆盖项目 reporter 的计划范围命令，生成命名 HTML 和同 stem 中文 Markdown 汇总。
- Playwright HTML reporter 的 `outputFolder` 默认使用 runner 临时目录 `tests/e2e/reports/.playwright-html-current/`；该目录可能被每次 Playwright 运行清空，不保存正式命名报告。
- 最终正式 Playwright HTML 报告快照默认写入 `tests/e2e/reports/html/`，命名为 `playwright-report-{feature_file_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}.html`，并生成同 stem 的中文 Markdown 汇总。`branch_slug` 取当前分支，`/`、空格和特殊字符替换为 `_`。多轮调试可以保留多份带业务名、分支名和时间戳的本地快照，最终是否通过仍由 `Final Full Rerun` 表达。
- `feature_file_name` 默认取关联 BDD `.feature` 文件名去掉扩展名；smoke test 使用 `smoke`；一次运行覆盖多个 `.feature` 时优先使用 suite 名，否则使用 `multi-feature`。
- Playwright Markdown 汇总必须与命名后的 HTML 报告完全同 stem；`results.json`、`junit.xml`、`test-results/` 和默认 `index.html` 不能决定正式 Markdown 文件名。`results.md`、`result.md`、`junit.md` 或 `index.md` 不能满足最终 `Run Summary MD`。
- 命名后的 HTML 是正式报告；Playwright 默认 `index.html` 只作为 `.playwright-html-current/` 中的复制源或工具兼容产物。只要 Playwright 已产生 `index.html`、`results.json`、`junit.xml` 或等价产物，最终输出前必须确认命名后的 HTML 和同 stem 中文 `.md` 实际存在。
- 调试轮次失败后先重跑失败 spec，再跑受影响子集，最后跑计划范围内全量验证；最终全量是否通过由 `Final Full Rerun` 表达，不能用“未全绿”跳过报告文件。

API / integration 报告规则：

- API 正式报告默认写入 `tests/api/reports/`，stem 使用 `api-report-{suite_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}`；自定义 API 脚本如果没有原生 reporter，正式验证时必须捕获 stdout、stderr、exit code、命令和时间戳为 raw report，并生成同 stem 中文 Markdown 汇总。
- API Markdown 汇总必须包含 URI 覆盖矩阵。每条覆盖范围描述都要映射到具体 `method + URI path`，并记录对应测试脚本 / case、期望状态码或副作用、关联 `.feature` / contract / schema；同一覆盖描述涉及多个 endpoint 时逐行列出。
- Base URL、环境名或服务名可以单独记录，但不能用脚本名、权限链路概括或业务域名称替代 URI path；无法确定 URI 的覆盖项必须标记 `blocked` 或 `missing-uri`。不要写入真实账号、token、敏感 query/body 或生产数据。

## Maestro 集成策略

Maestro 面向移动 App 和 Hybrid App E2E。模板不推荐用 Maestro 主做 Web 回归；Web 场景只适合做少量 Chromium smoke，主责仍在 Playwright CLI。

检测和安装顺序：

1. 需要 Maestro 前先检查 Java 17+。
2. 优先执行 `java --version`，失败时回退 `java -version`。
3. 当前 JDK 满足 17+ 时优先使用当前 JDK。
4. Java 缺失或低于 17 时，先扫描本机已有 JDK，优先选择已安装且满足 17+ 的 JDK。
5. 只有本机没有可用 17+ JDK 且用户确认后，才引导安装 JDK；默认建议安装 OpenJDK Temurin 21 最新 JDK，下载来源为 `https://github.com/adoptium/temurin21-binaries/releases`。
6. 用户指定其他 Java 版本时，只允许安装 Java 17 或更高版本，拒绝任何低于 17 的版本。
7. Java 通过后检查 Maestro CLI。
8. Maestro CLI 缺失时询问用户是否安装到开发环境或 CI runner。
9. Maestro CLI 可用后再检查 Maestro MCP，并引导当前 Agent / IDE 的 MCP 配置同时包含 `command`、`args` 和 env。
10. Maestro MCP 的 `JAVA_HOME` 使用选定的 JDK home，`PATH` 必须优先包含 Maestro bin 目录和 JDK `bin` 目录，再包含系统基础路径。

Fallback：

- Maestro MCP 缺失或 MCP env 未配置但 CLI 可用时，继续使用 `maestro test` 执行已有 flow，并单独报告 MCP 状态和缺失配置。
- Maestro CLI 缺失且用户拒绝安装时，`Maestro Mobile` 标记 `blocked` 或 `skipped`。
- Java 17+ 缺失且用户未确认安装时，只报告阻塞和安装引导，不自动安装。
- 设备、模拟器、app binary、appId、bundleId、测试账号或环境不可用时，必须记录阻塞原因。

Maestro flow 资产和报告规则：

- 需要从 Mobile / Hybrid BDD 场景生成或维护 Maestro flow 时，调用 `maestro-mobile-e2e`。
- Flow 固定写入 `maestro/flow/`，使用 `.yml` 扩展名。
- 文件名和 YAML `name` 使用英文业务场景名；文件名使用 lower-kebab-case，例如 `maestro/flow/login-success.yml`。
- iOS 和 Android 需要明显不同 flow 时，可使用 `maestro/flow/ios/*.yml` 和 `maestro/flow/android/*.yml`；平台 smoke 可使用 `maestro/flow/ios/smoke.yml` 和 `maestro/flow/android/smoke.yml`。
- 全量回归 / smoke flow 固定为 `maestro/flow/smoke.yml`。
- 每个 flow 必须追踪到源 `.feature` 路径、场景名称、平台范围和测试模式。
- Maestro CLI 最终正式 report 固定写入项目根目录 `.maestro/reports/`。
- 报告命名为 `maestro-report-{flow_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}.xml` 或 `.html`，并生成同 stem 的中文 `.md` 运行汇总；`flow_name` 取 Maestro flow 文件名 stem，smoke flow 使用 `smoke`，是否生成 HTML 遵循项目或用户对人类可读报告的需要。
- 优先让 Maestro 直接输出到带分支名和时间戳的文件；如果项目 wrapper 只能输出到固定目录或固定文件，使用 `.maestro/reports/.maestro-current/` 作为临时输出，再复制 / 提升为 `maestro-report-{flow_name}-{branch_slug}-{timestamp}`。`~/.maestro/tests`、`.maestro-current/`、固定 `report.xml` / `report.html` 都不是正式保留报告。
- stdout-only Maestro run 只用于诊断或定点重跑，不能满足正式 Mobile / Hybrid E2E 报告 gate；正式验证收尾必须补跑 `--format` / `--output` 或项目等价 reporter，无法产出时标记 blocked。
- Maestro 官方默认运行 artifacts 仍在用户 home 下的 `~/.maestro/tests`；它不是仓库内测试资产。
- iOS 真机遇到 driver setup、端口转发、view hierarchy、tap crash 或版本已知问题时，`maestro-mobile-e2e` 按标签 / 关键字懒加载对应 lesson；未命中时不预先套用临时补丁。

移动端上下文 gate：

- 生成或运行 flow 前确认平台、app artifact、bundleId / appId、设备 / 模拟器 / 云测、后端依赖、base URL / launch args / deep link、账号、数据、权限、稳定 selector 和系统 UI。
- 缺少关键事实时，`Maestro Flow Assets` 标记 `blocked`，不生成脆弱 flow。
- contract-backed 或 app-mocked flow 只能证明对应 contract / mock 假设成立，不能报告为 full-stack Mobile E2E 通过。

## Chrome DevTools MCP 和 Playwright MCP

这两个 MCP 都是 Agent 交互能力，不是项目依赖。

- Chrome DevTools MCP：用于真实 Chrome 运行时诊断，适合白屏、console error、network、cookie、storage、性能 trace、截图和临时复现。
- Playwright MCP：用于 Agentic Web 探索、可访问性快照、locator 生成辅助和页面结构理解。

MCP 配置由 Agent 或 IDE 提供。`scripts/onboard.py` 只做检查和引导，不把 MCP 配置文件复制进业务项目；根目录安装脚本在用户明确选择平台和 MCP server 后，可以执行平台 CLI 配置或写入 Oh My Pi 的 `mcp.json`。Codex plugin / connector 与 ChatGPT-hosted MCP 也遵循同一边界：先确认当前会话可见 callable tool，授权状态由 Agent / connector 管理，不把 session auth 材料写入项目。

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

默认沉淀路径：

- `tests/e2e/manifest/ui-test-manifest.json`
- `tests/e2e/manifest/ui-selector-audit.json`
- `tests/e2e/manifest/ui-test-coverage.json`

调用 `web-ui-autotest-generator` 的脚本时，模板要求显式传入 `tests/e2e/manifest/` 下的参数路径，不依赖 Skill 示例里的根目录默认值：

```bash
generate_manifest.py --root . --out tests/e2e/manifest/ui-test-manifest.json --pretty
audit_selectors.py --root . --out tests/e2e/manifest/ui-selector-audit.json --pretty
check_coverage.py --root . --manifest tests/e2e/manifest/ui-test-manifest.json --selector-audit tests/e2e/manifest/ui-selector-audit.json --tests-dir tests/e2e --out tests/e2e/manifest/ui-test-coverage.json --pretty
```

失败分析 `ui-test-repair-plan.json` 是运行产物，不是稳定测试资产；如生成，默认放到 `tests/e2e/manifest/ui-test-repair-plan.json` 并通过 `.gitignore` 忽略。验证或 Trellis check 收尾时，必须确认三个可入库 JSON 位于 `tests/e2e/manifest/`，且项目根目录没有残留同名 JSON。

## `shadcn` Skill 使用边界

`shadcn` 只在 shadcn/ui 项目、组件 registry、preset 或 CLI 工作流需要时启用。

适用场景：

- 项目存在 `components.json`，或用户要求初始化 / 维护 shadcn/ui。
- 需要执行或评估 `shadcn init/add/search/view/docs/diff/info/migrate/preset`、preset code、registry item、第三方 / 私有 / 付费 registry 或 shadcn MCP 配置。
- 需要修复 shadcn 组件组合、forms、icons、semantic tokens、Tailwind v3 / v4、Base UI vs Radix API、chat primitives、registry import path rewrite 或已安装组件更新策略。

执行和报告规则：

- UI/UX 任务中先用 `ui-ux-pro-max` 明确产品方向、信息架构、可访问性和设计系统约束，再用 `shadcn` 处理组件来源、CLI、registry 和具体实现规则。
- 按项目 package manager 选择 `npx shadcn@latest`、`pnpm dlx shadcn@latest` 或 `bunx --bun shadcn@latest`。
- 添加或更新组件前先检查 `components.json`、`shadcn info`、已安装组件和项目别名；涉及组件 API 时先查 `shadcn docs`。
- registry 未明确时先询问用户；更新已有组件时先用 `--dry-run` / `--diff`，未经用户明确确认不使用覆盖式更新。

不适用场景：

- 非 shadcn/ui 项目，且用户没有要求引入 shadcn。
- 只是通用 UI 设计判断、视觉 polish、后端、测试、文档或非 React UI 栈任务。
- React Bits Free / 付费 tier、付费 Skill 安装或 key 可用性判定；这些按 React Bits tier 规则单独处理。

## React Bits tier 选择边界

React Bits 不是 shadcn/ui 的必装依赖。安装和 reset 默认保持 shadcn/ui only；只有检测到目标项目是 React + shadcn/ui（存在 `components.json`），且任务需要更强视觉表达、动画组件、blocks 或 landing sections 时，才询问用户是否启用 React Bits。

确认顺序：

- 先说明 shadcn/ui 提供常规应用组件，React Bits Free / 付费 tier 只是可选增强。
- 询问用户选择继续 shadcn/ui only、安装 React Bits Free，或使用已有付费 Starter / Pro / Ultimate。
- React Bits Free 只有在本工作流已有明确免费 source / registry / 安装命令时才安装；未配置时说明暂不可自动安装。
- 付费 Starter / Pro / Ultimate 必须由用户确认，且当前环境能读取 `REACTBITS_LICENSE_KEY`；不打印、不输出、不提交该 key。
- reset 时保留检测到的既有 React Bits Free、Starter、Pro 或 Ultimate tier / registry，不用默认免费版覆盖。

## `seo-geo` 使用边界

`seo-geo` 只在公开 Web 资产需要搜索可见性检查时启用。

适用场景：

- 用户明确要求 SEO、GEO、AI search visibility、ChatGPT / Perplexity / Google AI Overview 可见性、schema、JSON-LD、meta tags、robots.txt、sitemap.xml、canonical 或关键词研究。
- 当前变更影响公开网站、落地页、文档站、产品页、营销页、公开博客或公开 README 页面。
- 发布前验收标准明确包含搜索引擎、AI 搜索引用、社交分享预览、结构化数据或 crawl / indexing 检查。

不适用场景：

- 内部后台、登录后页面、API、CLI、移动 App、纯后端、测试资产、文档内部重排或无公开 URL 的一次性 UI 调整。
- 只需要 Web 运行时诊断、截图、console / network 证据或 Playwright 回归。
- `seo-geo` Skill 未安装且当前任务不以搜索可见性为主要目标。

执行和报告规则：

- 优先确认目标 URL、preview URL、生产 / staging 环境、是否允许抓取、是否已有 sitemap / robots / schema 约定。
- 没有公网 URL 或 preview URL 时，只做源码 / HTML 静态检查；最终报告 `SEO/GEO: static-only` 或 `blocked`，不能声称线上 SEO/GEO 已验证。
- 基础 audit 不要求 DataForSEO；DataForSEO login / password 只作为关键词、SERP、backlink、domain overview 等增强分析的可选凭据。
- 关键词量、SERP、AI 搜索可见性和平台抓取规则具有时效性，必须用当前可用来源核对。
- 不得把 DataForSEO login / password、Search Console 数据、付费报告、真实账号、密钥、PII 或生产敏感 URL 写入仓库、日志、截图、测试或正式报告。
- 最终输出或 Trellis check summary 必须报告 `SEO/GEO`: `audited` / `static-only` / `blocked` / `skipped` / `not-needed`。

## 跨仓测试模式和报告闭环

API、Web E2E、Mobile E2E、Hybrid E2E 或发布前 smoke 进入正式验证时，先选择测试模式：

| 模式 | 含义 | 报告边界 |
|---|---|---|
| `full-stack` | 真实前后端 / app / 环境 / 数据可用。 | 可报告完整链路通过。 |
| `contract-backed` | 完整链路不可用，但有可靠 API contract、schema、fixture 或真实响应样例。 | 只证明符合 contract。 |
| `mock-backed` / `app-mocked` | 使用 mock backend、fixture、launch args 或 app test mode。 | 只证明 mock 假设下的客户端 / app 行为。 |
| `backend-only` | 只验证 API provider 或服务端集成。 | 不等于 Web / Mobile E2E。 |
| `smoke-only` | 只验证启动、登录页、主导航等低依赖路径。 | 不等于完整回归。 |
| `blocked` | contract、环境、账号、数据、设备、artifact 或 selector 缺失。 | 不生成通过报告。 |

正式报告和 Markdown 汇总：

- API / integration 默认目录：`tests/api/reports/`。
- API / integration runner 临时输出默认目录：`tests/api/reports/.api-current/`。
- Playwright HTML reporter 临时输出默认目录：`tests/e2e/reports/.playwright-html-current/`。
- Playwright HTML 正式报告快照默认目录：`tests/e2e/reports/html/`。
- Maestro 默认目录：`.maestro/reports/`。
- Unit test 报告默认继承项目配置；缺少项目约定但需要本地正式证据时，使用 `tests/unit/reports/`，临时输出使用 `tests/unit/reports/.unit-current/`。
- 执行 unit / API / Playwright / Maestro 报告型测试前先记录 `rtk` 决策：`used` / `skipped-for-report` / `fallback-native` / `not-available` / `not-needed`。如果 `rtk` 后报告文件缺失、mtime / size 未变化、内容不对应本轮命令，或输出显示 cache hit / replay / skipped 写入，必须原生命令重跑并以原生结果为准。
- 调试轮次可以保留多份本地命名报告快照；一旦 Playwright 或 Maestro 运行产生 runner 原生报告，或 API / integration / unit runner 生成了本轮需要保留的报告，无论最终全量是否通过，都生成该次运行的命名报告和一份同目录同 stem 的中文 `.md` 汇总。API、Playwright 和 Maestro 的正式报告 stem 必须包含 `branch_slug`；`branch_slug` 取当前 git / CI 分支，detached HEAD 使用 `detached-{short_sha}`，非 git 环境使用 `unknown-branch`，并将 `/`、空格和特殊字符替换为 `_`。
- 正式验证范围不能由 runner 是否已经产出报告倒推决定。API / Web E2E / Mobile E2E / Hybrid E2E 一旦进入正式验证范围，stdout-only、terminal-only 或 diagnostic-only 命令不能满足最终报告 gate：API 自定义脚本必须捕获 stdout / stderr / exit code 为 `api-report-*-{branch_slug}-*.txt` / `.json` raw report，Playwright `--reporter=list` 后必须补跑正式 reporter，Maestro stdout-only 后必须补跑 `--format` / `--output` 或项目等价 reporter；无法产出时标记 `Final Test Report: blocked` 和 `Run Summary MD: blocked`。
- 通用防覆盖规则：`coverage/`、`test-results/`、固定 `junit.xml`、runner 的 `current` / `latest` 目录和各工具临时输出目录都可能被下一轮运行清空、覆盖或重建；需要保留时，先复制 / 提升到正式快照目录和时间戳 stem，再启动下一轮会改写同一输出的命令。
- Playwright 报告命名为 `playwright-report-{feature_file_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}.html`；smoke 使用 `smoke`，多 `.feature` 运行优先使用 suite 名，否则使用 `multi-feature`。
- Playwright `.md` 汇总必须使用命名 HTML 的同 stem，不得使用 `results.json` / `junit.xml` / 默认 `index.html` 的 stem。
- Maestro 报告继续使用 `maestro-report-{flow_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}` stem；`flow_name` 取 flow 文件名，不改成 `feature_file_name`。
- API 报告使用 `api-report-{suite_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}` stem；unit 报告使用 `unit-report-{suite_name}-{YYYY_mm_dd}-{HH_MM_SS}` stem。缺少明确 suite 时可以省略 `{suite_name}`，但不能省略 `{branch_slug}`，也不能使用会被下一轮覆盖的固定文件名作为正式报告。没有原生 reporter 的 API 正式验证至少保留 `.txt` / `.json` raw report 和同 stem `.md`。
- `.md` 汇总使用中文撰写，状态枚举值、命令、文件路径、case / spec / flow 名称、错误原文和技术标识符可以保留英文；内容记录运行 case / spec / flow 列表、关联 BDD `.feature` 路径和场景名、总轮次、每轮命令、失败 case / spec / flow、失败原因、修复动作、修改文件摘要、定点重跑、影响范围重跑、最终全量重跑、跳过项和剩余风险。
- 失败修复后先重跑失败 case / spec / flow，再跑受影响子集，最后跑计划范围内全量验证；fail-fast 停在首个失败时，修复后必须继续跑未覆盖测试或重跑全量。
- 汇总和报告不得写入真实账号、密钥、PII、生产数据、完整 token 或敏感请求头。

## 最终验证工具栈

最终验证阶段按以下顺序和风险叠加：

| 层级 | 工具 / 方法 | 触发条件 | 状态要求 |
|---|---|---|---|
| 项目原生验证 | lint、typecheck、unit、integration、build、项目 README / Makefile / CI 命令 | 修改代码后默认执行可用的最小有效验证 | 记录命令和结果 |
| BDD 追踪 | `gherkin-bdd`、`.feature`、BDD runner 或测试名追踪 | 新增或修改用户可见行为 | `BDD`: `run` / `traceable` / `blocked` / `skipped` |
| 跨仓上下文 | contract、环境、账号、数据、设备、selector、app artifact | API / Web / Mobile / Hybrid 链路不完整 | `Cross-repo context`: `complete` / `contract-only` / `environment-only` / `missing` |
| GitNexus | MCP 影响分析、变更检测 | GitNexus MCP 可用且项目索引有效 | 成功使用或说明跳过原因 |
| Web 诊断 | Chrome DevTools MCP | 需要真实浏览器现场证据 | `diagnosed` / `inspected` / `blocked` / `skipped` / `not-needed` |
| Web 回归 | Playwright CLI | Web UI、路由、表单、权限、跨页面流程、API 集成、浏览器兼容 | `Playwright Web Tests`: `run` / `failed` / `blocked` / `skipped` |
| Web 测试资产 | `web-ui-autotest-generator` | 需要把 Web UI 回归固化入仓库 | `generated` / `coverage-only` / `blocked` / `skipped` |
| SEO/GEO | `seo-geo` | 公开 Web 资产需要搜索可见性、schema、meta、robots / sitemap 或 AI 搜索引用检查 | `SEO/GEO`: `audited` / `static-only` / `blocked` / `skipped` / `not-needed` |
| Mobile / Hybrid E2E | Java 17+、Maestro CLI、Maestro MCP | Android、iOS、RN、Flutter、Hybrid App 用户旅程 | `Maestro Mobile`: `run-local` / `run-cloud` / `blocked` / `skipped` / `not-needed` |
| 发布风险 | `book-release-readiness`、Channel preflight | 生产路径、外部集成、部署敏感、高风险变更或高 reasoning 多 worker 并发 | 记录风险、fallback、rollback 和用量风险 |

`project-validation` 覆盖 Node / JavaScript / TypeScript、Python、Go、Dart / Flutter、Java、Kotlin、C++、Swift 和 Objective-C 的代码规范检查、typecheck / static analysis、unit test 与项目 CI 继承规则；unit test 报告路径默认继承项目配置，不由模板统一硬编码，但需要作为本轮证据保留的 unit 报告不能只停留在会被 runner 重写的 coverage / JUnit 固定路径。

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
- `Maestro Flow Assets`: `generated` / `reused` / `blocked` / `skipped`
- `Web UI 测试资产`: `generated` / `coverage-only` / `blocked` / `skipped`
- `Cross-repo context`: `complete` / `contract-only` / `environment-only` / `missing` / `not-needed`
- `API Contract`: `verified` / `user-provided` / `stale` / `missing` / `not-needed`
- `E2E Mode`: `full-stack` / `contract-backed` / `mock-backed` / `app-mocked` / `smoke-only` / `backend-only` / `blocked` / `not-needed`
- `Mobile Platform Scope`: `ios` / `android` / `both` / `hybrid` / `not-needed`
- `Mock Strategy`: `none` / `contract-backed` / `user-approved` / `blocked` / `not-needed`
- `Final Test Report`: `generated` / `blocked` / `not-supported` / `not-needed`
- `Run Summary MD`: `generated` / `blocked` / `not-needed`
- `rtk`: `used` / `skipped-for-report` / `fallback-native` / `not-available` / `not-needed`
- `Targeted Rerun`: `passed` / `failed` / `blocked` / `not-needed`
- `Final Full Rerun`: `passed` / `failed` / `blocked` / `skipped-with-risk` / `not-needed`
- `SEO/GEO`: `audited` / `static-only` / `blocked` / `skipped` / `not-needed`

## 模板 `.gitignore` 工具与测试产物策略

项目模板在 Codex 与 Trellis 规则之间仅忽略 OMP 的本地插件安装目录 `.omp/plugins/`；`trellis init --omp` 生成的 `.omp/agents/`、`.omp/commands/`、`.omp/skills/` 和 `.omp/extensions/` 应由 Git 追踪。模板同时忽略本地运行态和报告产物，保留可维护测试资产。当前相关片段如下：

```gitignore
# ---------- OMP ----------
# Keep Trellis-generated agents, commands, skills, and extensions versioned.
.omp/plugins/

# ---------- Testing -----------
# MCP / browser controller local state
.chrome-devtools-mcp/
.playwright-mcp/

# Playwright runtime artifacts
playwright-report/
test-results/
blob-report/

# Web UI autotest generated run artifacts
tests/e2e/manifest/ui-test-repair-plan.json
tests/api/reports/
tests/unit/reports/
tests/e2e/reports/
tests/e2e/**/screenshots/
tests/e2e/**/videos/
tests/e2e/**/traces/
tests/e2e/**/*.trace.zip

# Maestro runtime artifacts
# Keep maestro/flow/*.yml flows versioned; ignore only local runtime output and reports.
.maestro/cache/
.maestro/tmp/
.maestro/runs/
.maestro/reports/
```

`maestro/flow/*.yml` flow 默认应可入库维护；`tests/api/reports/`、`tests/unit/reports/`、`tests/e2e/reports/` 和 `.maestro/reports/` 只保存正式报告快照、Markdown 汇总和本地 / CI 运行产物，默认不入库。Playwright report、trace、video、screenshot、coverage、JUnit 固定输出和一次性 repair plan 默认不入库。

## onboard / reset 检查范围

`kuno-workflow-onboard-skills` 的 init / reset / check 逻辑需要覆盖：

- 根安装器在用户选择或传入目标 Agent 平台后、询问 `init` / `reset` 和项目路径前，立即检测对应 CLI：`codex`、`claude`、`kimi` 或 `omp`。已通过 `<command> --version` 则继续；缺失或验证失败时先确保 npm 可用，再用 npm 全局安装官方 `@latest` 包并复验命令。
- 全局 Agent 规则，以及一个或多个项目根目录下的项目级 Agent 模板和 `.gitignore`。
- 13 个 bundled Skills 和 15 个 external Skills 强制安装到全局 Skill 目录，不再提供 project/none scope 选择；两个根安装器从 `check` 的 `group=referenced` 获取 canonical 清单，不再各自维护重复数组。
- Trellis CLI 和 GitNexus CLI 强制全局安装，不再提供项目内 CLI 安装；`.trellis/` 与 `.gitnexus/` 状态仍属于各项目。
- `init` / `reset` 对每个项目根目录独立检查 `.trellis/`，执行 `trellis init -u`，并检查 `.trellis/tasks/00-bootstrap-guidelines`；一个项目需要 bootstrap 不会阻止其余项目继续检查。
- `--init-projects` / `-InitProjects` 提供独立的 project-only 模式，只执行逐项目 AGENTS、`.gitignore`、Trellis、Playwright 和 React Bits 检查配置，不检测或安装任何全局 Agent CLI、runtime、tool、Skill 或 MCP。
- GitNexus MCP 手动配置检查；检测到本机 `gitnexus` CLI 路径时，输出并供安装脚本使用 `command = "<detected-gitnexus-path>"`、`args = ["mcp"]` 的配置。
- Chrome DevTools MCP 手动配置检查。
- Playwright MCP 手动配置检查。
- Playwright CLI 按每个项目独立检测和安装引导；只有既有 Playwright/E2E 标记使其适用时才询问。
- Java 17+、Maestro CLI 和 Maestro MCP 检测及安装引导，包含 Maestro MCP 的通用 `command` / `args` / `JAVA_HOME` / `PATH` 配置示例。
- bundled `seo-geo` Skill 的存在性检查。
- External Skill 默认使用 `--source auto`：按上游仓库整组 clone、解析和验证，只有上游获取或源结构验证失败时才延迟加载并整组回退 `kuno-workflow-onboard-skills/assets/external-skills/stable/`；有效上游不依赖 stable manifest。`--source upstream` 和 `--source stable` 提供严格模式。manifest、source subpath 和 license 路径必须被各自声明的根目录包含，拒绝绝对路径、`..` 和 symlink 逃逸。全部 Skill 先暂存和验证，再用临时 rollback backup 事务替换；canonical commit 成功后才删除 legacy 目录。
- stable External Skills 的 `MANIFEST.json` 记录 stable set、精确上游 commit、subpath、tree SHA-256 和许可证/NOTICE。stable 快照保持上游原样且不得手改；只有显式 `promote-external-skills-stable --repository ... --revision <full-sha> --stable-set ... --yes` 才能整组更新。
- mattpocock external Skill 使用上游 canonical 名称；`to-prd` / `to-issues` 作为 legacy alias 迁移到 `to-spec` / `to-tickets`，canonical 安装成功后再备份和删除本地旧目录。
- `web-ui-autotest-generator`、`shadcn`、`ui-ux-pro-max`、`impeccable` 等 referenced external Skill 的存在性检查。
- React Bits tier 选择对每个 React + shadcn/ui 项目独立判断；仍保持项目级、可选并保留 license/registry 前置条件。
- `caveman` 用户级全局交互压缩 Skill 的存在性检查和安装引导。

`scripts/onboard.py` 本身仍只做 MCP 状态检查和配置指引，不直接写 Agent / IDE 的 MCP 设置。仓库根目录的 `install.sh` 和 `install.ps1` 是面向用户的交互式安装入口，会在用户选择单一目标平台并确认 MCP 选项后，调用对应平台命令或写入对应配置文件；其中 GitNexus MCP 优先使用 `check` 阶段检测到的本机 `gitnexus` 可执行文件路径和 `mcp` 参数，未检测到路径时才回退到人工输入：

目标 Agent CLI 的固定映射为：`codex → @openai/codex@latest`、`claude → @anthropic-ai/claude-code@latest`、`kimi → @moonshot-ai/kimi-code@latest`、`oh-my-pi` / `omp → @oh-my-pi/pi-coding-agent@latest`。检测和安装由 `check-agent-cli` / `install-agent-cli` 子命令承接。正常 onboarding 中 npm 同时是强制全局 Trellis/GitNexus 的前置条件；project-only `init-projects` 则完全跳过该全局门禁。

- `codex`：执行 `codex mcp add ...`。
- `claude`：固定执行 `claude mcp add ... --scope user`。
- `kimi`：执行 `kimi mcp add ...`。
- `oh-my-pi` / `omp`：固定写入全局 `~/.omp/agent/mcp.json`。

两个安装脚本的 `source-root` 都直接指向 `kuno-workflow-onboard-skills` 目录，而不是仓库根目录。默认值是当前执行目录下的 `./kuno-workflow-onboard-skills`；如果该目录不存在，或缺少 `SKILL.md`、`REFERENCE.md`、`scripts/onboard.py`、`templates/`、`assets/external-skills/stable/MANIFEST.json`，脚本会直接输出未找到或不完整的 Onboard skill 并结束安装。脚本可以被复制到其他目录独立使用，但必须能通过默认值或显式参数定位完整的 `kuno-workflow-onboard-skills`：

```bash
./install.sh --source-root /absolute/path/to/kuno-workflow-onboard-skills --platform codex
```

```powershell
.\install.ps1 -SourceRoot C:\absolute\path\to\kuno-workflow-onboard-skills -Platform codex
```

正常 onboard 可传入一个或多个逗号分隔的绝对项目根目录；未传时，安装脚本会说明支持多个绝对路径并交互询问：

```bash
./install.sh --projects-root /abs/project-one,/abs/project-two --trellis-user your-name --trellis-platform codex
```

```powershell
.\install.ps1 -ProjectsRoot "C:\work\one,C:\work\two" -TrellisUser your-name -TrellisPlatform codex
```

只初始化项目、不触碰全局安装项：

```bash
bash install.sh --platform codex --init-projects /abs/project-one,/abs/project-two
```

```powershell
.\install.ps1 -Platform codex -InitProjects "C:\work\one,C:\work\two"
```

`caveman`、RTK、Java 和 Maestro 保持原来的条件确认规则；`caveman` 安装后不自动启用压缩对话模式。13 个 bundled Skills 和 15 个 external Skills 在正常 `init` / `reset` 中作为必需全局能力处理：缺失 external Skills 默认先验证上游，上游获取或验证失败时从 Onboard 内置 stable set 回退安装，bundled Skills 写入全局目录，均不再询问 project scope。stable 自身完整性错误，以及目标侧 staging、权限、磁盘、commit 或 rollback 错误都直接失败，不会被 fallback 掩盖。已有 bundled 目标会被覆盖且不备份；External Skill 显式替换采用临时事务 rollback，完整恢复后删除临时备份，恢复不完整时保留并返回 rollback 路径；已有且验证有效的 canonical external Skill 不会在每次 init/reset 中重复下载，legacy migration 只处理旧名称。

逐项目 `init` / `reset` / `init-projects` 完成模板写入后会继续做 Trellis setup：每个缺少 `.trellis/` 的 root 都执行同一 username/platform 配置的 `trellis init -u <username> ... --yes --skip-existing`，随后分别检查 `.trellis/tasks/00-bootstrap-guidelines`。汇总状态按 `failed > blocked > needs-user > bootstrap-required > success > skipped` 处理；命中的每个项目都必须按 `trellis-workflow` 完成 bootstrap guideline 后才算 onboarding 完成。

## 同步规则

当用户输入 `sync` 或 `同步` 时：

1. 读取同步源文件并确认路径正确。
2. 只同步根 `AGENTS.md` 中允许列表里的全局规则和全局 Skill；Skill 必须按目录整体同步，不能只复制 `SKILL.md`。
3. `kuno-workflow-onboard-skills/` 也作为完整 Skill 目录同步到 `/Users/lusonglin/.agent/skills/kuno-workflow-onboard-skills/`。
4. 不把 `kuno-workflow-onboard-skills/templates/agents/AGENTS.project.md` 作为独立项目级 `AGENTS.md` 同步；它只会随 onboard Skill 作为模板资产保留。
5. 在本机实际使用的 `/Users/lusonglin/.agent/skills/` 上执行 mattpocock legacy migration：通过 synced onboard Skill 的 `install-external-skills --skills to-prd,to-issues --scope global --source auto --global-skills-dir /Users/lusonglin/.agent/skills --yes` 删除旧 `to-prd` / `to-issues`，并安装 canonical `to-spec` / `to-tickets`；普通 sync 不默认清理或安装 `/Users/lusonglin/.codex/skills/` 下的同名目录。
6. 文件用 `cmp -s` 或等价方式确认一致；Skill 目录用 `diff -qr`、递归 checksum 或等价方式确认一致；legacy migration 用旧目录不存在且 `to-spec/SKILL.md`、`to-tickets/SKILL.md` 存在作为校验。
7. 不修改 `ENTRYPOINT.md` 版本号。
8. 不归档 `UPDATE.md`。
9. 不提交或推送变更。

## README 同步规范

后续每次模板内容有更新，都必须评估 `README.md` 和 `README.html` 是否需要同步更新。

必须同步 README 的典型情况：

- 工作流主线、工具职责或边界发生变化。
- SDD、BDD、TDD、DDD 或 SBTD 的定义、触发条件、产物位置发生变化。
- Chrome DevTools MCP、Playwright CLI、Playwright MCP、Maestro CLI、Maestro MCP、`shadcn`、`web-ui-autotest-generator` 或 `seo-geo` 的检测、安装、fallback 或报告状态发生变化。
- `kuno-workflow-onboard-skills/scripts/onboard.py` 的 init、reset、安装或检查行为发生变化。
- 模板 `.gitignore`、同步路径、AGENTS 模板路径或 Skill 模板路径发生用户可见变化。
- 最终验证阶段的工具栈或报告格式发生变化。

如果评估后不需要更新 README，最终输出要说明原因。若需要更新，应在同一轮修改中立即更新 `README.md` 和 `README.html`，保持两者与模板源一致。

## 更新和版本检查

每日版本检查自动化以 `ENTRYPOINT.md` 的版本监控表为基线，更新分析写入 `UPDATE.md`。只有用户输入 `update` 或 `更新` 时，才把 `UPDATE.md` 中的最新版本写回 `ENTRYPOINT.md` 并归档。

由 release 触发的 AGENTS 或 Skill 规则更新必须沉淀为长期通用规则，不把一次性版本区间写进长期执行规则。
