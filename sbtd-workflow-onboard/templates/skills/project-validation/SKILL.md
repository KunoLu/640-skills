---
name: project-validation
description: Use after code changes to choose and run validation commands for Node, JavaScript, TypeScript, Python, Go, Dart, Java, Kotlin, C++, Swift, or Objective-C projects. Prefer project-defined commands and report skipped checks and risks.
---

# 项目验证 Skill

代码修改后使用本 Skill。

## 通用规则

- 优先使用项目已定义的命令。
- 当 `rtk` 可用时，非报告型命令优先使用 `rtk`；unit test、API / integration test、Playwright Web E2E、Maestro Mobile / Hybrid E2E 或任何需要生成报告文件的命令，先按 `rtk` 与报告型测试 Gate 判断。
- 不绕过项目配置。
- 除非任务需要，不修改 lock 文件。
- 如果完整检查成本较高，先运行聚焦检查。
- 说明跳过的检查和剩余风险。

## `rtk` 与报告型测试 Gate

`rtk` 是命令输出压缩层，不是测试 runner。执行验证命令前先区分“只需要终端事实”和“必须产生文件副作用”。

- lint、typecheck、静态分析、build、只读检查或不依赖落地报告的诊断命令，通常可以优先使用 `rtk`。
- unit test、API / integration test、Playwright Web E2E、Maestro Mobile / Hybrid E2E、Flutter / Xcode / Gradle / Maven 等测试命令如果本轮需要保留 coverage、JUnit、HTML、JSON、trace、raw report 或 Markdown 汇总，默认优先使用项目原生命令，或项目明确提供的 no-cache / report-safe 命令。
- 只有确认 `rtk` 对该命令不会 cache hit、replay 输出、跳过 runner 写文件副作用，且报告路径可被校验时，才使用 `rtk` 包裹报告型测试命令。
- 如果已经用 `rtk` 执行了报告型测试，必须校验预期报告文件存在、mtime / size 在本轮运行后变化、内容能对应本轮命令和 case / spec / flow。缺失、陈旧、空文件、内容不匹配、或输出显示 cache hit / replay / skipped 写入时，立即用原生命令重跑，并以原生命令结果和落地报告为准。
- API 自定义脚本、Playwright、Maestro、unit runner 的 stdout 结果不能替代报告文件 gate；该命令属于正式验证时，必须落地 raw report / 原生报告和同 stem Markdown 汇总，或标记 blocked。
- 最终输出必须报告 `rtk`: `used` / `skipped-for-report` / `fallback-native` / `not-available` / `not-needed`，并说明原因。

## Book-derived 验证补充

项目验证负责选择并运行 lint / test / build / typecheck 等命令，不替代 book-derived skills。

生产路径相关的服务、API、后台任务、队列、外部集成、数据管道或部署敏感变更，在基础项目验证后必须主动判定是否调用 `book-release-readiness`。如果验证暴露了数据一致性、迁移、回放、幂等或跨服务数据流风险，回到 `book-ddia-data-design` 补齐设计 / 检查结论后再完成。

这一步只记录当前任务风险、验证缺口和剩余风险；不要因为生产风险审查而新增与任务无关的重构或测试框架。

## BDD / Gherkin 验证补充

当任务新增或修改用户可见行为，或 diff 中包含 `.feature` / 持久 BDD 规格路径时，必须验证 BDD 一致性。

场景编写、审查或回填问题回到 `gherkin-bdd` Skill 处理；本 Skill 只负责修改后的验证选择、执行和风险报告。

检查顺序：

1. 确认用户可见行为是否有对应持久 BDD 场景；纯内部变更或无语义 UI polish 跳过时，记录跳过原因。
2. 检查 `.feature` / 持久 BDD 规格的语言决策是否被执行并与文件内容一致：
   - 项目已有 `.feature` 时，新增或修改内容必须沿用同一 bounded context 或功能区的既有 Gherkin 语言和关键词风格。
   - 项目原本没有 `.feature`，且用户未明确要求其他语言时，新增 `.feature` 的场景标题、描述和步骤文本默认应为中文；Gherkin 结构关键字使用英语。
   - 英文产品名、代码标识符、领域专名可以保留英文，但不能把整份新 `.feature` 写成英文。
   - 不要只依赖 `git diff --check` 判断语言正确性；必须人工复核，或使用轻量检查辅助发现明显违例。
3. 如果项目原本没有 `.feature`，新增 `.feature` 在注释、tag、表格、doc string 和结构关键字之外没有中文字符，且没有用户覆盖说明或项目规则覆盖，将 `BDD` 标记为 `blocked`，先回到 `gherkin-bdd` 修正语言。
4. 如果项目已有 Gherkin runner（例如 Cucumber、behave、pytest-bdd、cucumber-js）或 package / Makefile / CI 中有 BDD 命令，优先运行项目定义的 BDD 命令。
5. 如果没有 Gherkin runner，不主动引入新框架；使用项目已有测试框架运行追踪到场景的 unit / integration / E2E 测试。
6. 确认每个新增或修改场景都能追踪到自动化测试，追踪方式可以是测试名、注释、目录结构或项目约定。
7. 无法自动化的场景必须有 `@todo` 或项目等价标记、阻塞原因和临时人工验证说明。
8. 如果 PRD、`.feature`、测试和代码冲突，先回到规格对齐，不要用验证结果掩盖冲突。
9. 对前后端分仓、跨服务、Web + API、Mobile + API 或 Hybrid 链路，检查是否已记录上下文完整性：`Cross-repo context`: `complete` / `contract-only` / `environment-only` / `missing`。
10. 需要 mock 时，确认 mock 行为来自 API contract、schema、真实响应样例、既有 fixture 或用户确认；否则将 `Mock Strategy` 标记为 `blocked`，不要用猜测的 mock 生成测试。

最终输出中必须说明：

- `BDD`: `run` / `traceable` / `blocked` / `skipped`。
- 涉及的 `.feature` 或持久 BDD 规格路径。
- BDD 语言状态：沿用项目既有风格、默认中文场景文本 + 英文关键词、用户明确覆盖，或 `blocked` 的原因。
- 运行的 BDD runner 或追踪测试命令。
- `Cross-repo context`: `complete` / `contract-only` / `environment-only` / `missing`，如不相关则说明 `not-needed`。
- `API Contract`: `verified` / `user-provided` / `stale` / `missing` / `not-needed`。
- `Mock Strategy`: `none` / `contract-backed` / `user-approved` / `blocked`。
- 未自动化场景、阻塞原因和剩余风险。

## 验证证据来源与版本契约

只有正式测试报告需要作为 PR 证据或被知识库读取时，才应用 `references/validation-evidence-contract.md` 和 `references/validation-evidence.schema.json`。普通本地诊断、未发布的调试报告和一次性排障不强制生成 evidence sidecar。

项目已配置产品注册表时，调用 `knowledge-base-integration` 的 `decision` 入口确定 Evidence Contract、Intent 和 Targets；不得再根据报告目录、分支名或任意 CI 环境猜测用途。Knowledge-server smoke 由该 Skill 的 `smoke` 入口生成 P1.1 bundle，本 Skill 继续负责项目原生验证和报告质量 Gate。P1.1 只接收当前命令开始后新建或刷新的 runner report 与同 stem 中文 Markdown，聚合 envelope 必须引用 artifact manifest、checksums 和实际 runner attestation；stale、缺失、非中文、digest 不一致或环境来源不可信时不得把 Evidence 标记为通过。

- 开发者本地证据使用 `Evidence Source: developer-local`；CI runner 生成的证据使用 `Evidence Source: ci`；知识库服务器独立复验使用 `Evidence Source: knowledge-server`。三者不得覆盖或相互冒充。
- 正式证据必须记录 repository key、原始 source ref、完整 commit SHA、worktree state、trigger 和创建时间。`branch_slug` 只用于文件名，不是代码版本标识。
- dirty worktree 只能标记 `Source Revision: dirty` 和 `Evidence Publication: local-only`，不能作为 PR head 的正式证明。
- PR 证据必须与当前 PR head SHA 完全一致；新增 commit 后旧证据自动失效。
- Phase 3.4 commit plan 或创建提交前产生的结果只能记录为本地 evidence 状态。提交后、发布或更新 PR Check 前，必须针对最终 PR head SHA 重新生成或复验证据，并更新同 stem sidecar / 聚合 envelope；`developer-local` 与 `ci` 都适用。
- `ci` evidence 必须来自 clean checkout 并使用 `Source Revision: exact`。CI 执行不等于已发布：目标系统接收后才标记 `published`，未配置发布器时为 `not-configured`，要求发布但失败时为 `blocked`；CI evidence 不得标记 `local-only`。
- 知识库服务器证据必须记录所有参与仓库的精确 revision set，并记录 `Environment Alignment`。指定 `staging` 等目标分支时，先解析到精确 SHA 再运行。
- 不要求 `.feature` 添加 Feature ID 或 Scenario ID。行为来源用 repository key、feature path、Feature / Rule / Scenario 名称、可选 Examples fingerprint、source ref 和 SHA 定位。
- 每份正式报告可在同目录生成同 report stem 的 `.evidence.json`；跨工具编排器也可以在隔离 runtime / evidence bundle 中生成一个聚合 envelope。所有 envelope 都必须通过 Schema 校验并引用原生报告、同 stem 中文 Markdown 汇总和 SHA-256。
- 发布证据前必须脱敏。`published` 只表示证据已被目标系统接收，不表示测试通过，也不得把 `smoke-only`、`contract-backed`、`mock-backed` 或 `app-mocked` 提升为 `full-stack`。

相关任务的最终输出额外报告：

- `Evidence Source`: `developer-local` / `ci` / `knowledge-server` / `not-needed`。
- `Source Revision`: `exact` / `dirty` / `unknown` / `not-needed`。
- `Environment Alignment`: `verified` / `unverified` / `mismatch` / `not-needed`。
- `Evidence Publication`: `local-only` / `published` / `blocked` / `not-configured` / `not-needed`。

## Web / Mobile 测试工具 Gate

修改 Web UI、路由、表单、登录态、权限、跨页面流程、API 集成、发布流程、移动 App 用户旅程、Hybrid App 或关键用户路径后，必须按全局 / 项目级 `AGENTS.md` 的工具职责边界主动判定 Chrome DevTools MCP、Playwright MCP、Playwright CLI、Maestro CLI、Maestro MCP 和 `web-ui-autotest-generator` 是否适用。

本 Skill 只负责验证阶段 gate：

- 先按修改范围选择最小有效验证：项目测试、浏览器诊断、Playwright Web 回归、Maestro 移动 / Hybrid flow、或 Web UI 测试资产覆盖评估。
- 对 API / Web / Mobile / Hybrid 链路，先判定 `E2E Mode`: `full-stack` / `contract-backed` / `mock-backed` / `app-mocked` / `smoke-only` / `backend-only` / `blocked`。mock-backed、app-mocked 或 contract-backed 测试只能证明对应 contract / mock 假设成立，不能报告为 full-stack 通过。
- API / integration 测试优先继承项目既有测试框架和报告配置；没有项目约定且需要本轮正式报告时，默认正式快照目录为 `tests/api/reports/`。如果 runner 需要会被下一轮清空或覆盖的临时输出目录，默认使用 `tests/api/reports/.api-current/`，运行结束后再复制 / 提升为包含当前分支 `branch_slug` 和时间戳的报告。自定义 API 脚本只向终端输出时只能算诊断；如果它是本轮正式验证，必须捕获 stdout、stderr 和 exit code 为 `tests/api/reports/.api-current/` 下的 raw report，再提升到 `tests/api/reports/` 并生成同 stem 中文 Markdown 汇总。
- API / integration 的正式 Markdown 汇总必须提供 URI 覆盖矩阵：每条覆盖范围描述都要映射到具体 `method + URI path`，并记录对应测试脚本 / case、期望状态码或副作用、关联 `.feature` / contract / schema 依据。多个 endpoint 支撑同一覆盖范围时逐行列出；Base URL、环境名和服务名可单独记录，但不得只用脚本名、领域名或覆盖概括替代 URI path。不要写入真实账号、token、敏感 query/body 或生产数据。
- Web 可重复回归必须优先运行项目已有 Playwright CLI 命令；Chrome DevTools MCP / Playwright MCP 只提供诊断、探索或 locator 证据。Playwright 的 `--reporter=list` 只能用于诊断或定点重跑；Web E2E 进入正式验证范围时，收尾前必须再运行不覆盖项目 reporter 的计划范围命令，或将报告状态标记为 `blocked`。
- Web E2E 正式 HTML 报告快照默认进入 `tests/e2e/reports/html/`，除非项目 Playwright 配置已有更强约定；Playwright HTML reporter 的 `outputFolder` 默认使用 runner 临时目录 `tests/e2e/reports/.playwright-html-current/`。该目录可能被每次 Playwright 运行清空，只能作为中间产物或工具兼容产物来源；命名后的 HTML 才是正式报告。
- Maestro 相关验证必须先满足 Java 17+ 和 Maestro CLI；MCP 缺失但 CLI 可用时，继续执行已有 `maestro test` flow 并单独报告 MCP 状态。
- 需要从 BDD 场景生成或维护 Mobile / Hybrid Maestro flow 时，调用 `maestro-mobile-e2e`，并确认可入库 flow 资产位于 `maestro/flow/`。
- Maestro 正式报告必须写入项目根目录 `.maestro/reports/`；默认只生成一个项目需要的原生报告格式，命名为 `maestro-report-{flow_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}.xml` 或 `maestro-report-{flow_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}.html`。`flow_name` 取 Maestro flow 文件名 stem，smoke flow 使用 `smoke`；HTML 只在项目或用户需要人类可读报告时生成。优先让 Maestro 直接输出到包含分支名和时间戳的文件；如项目包装命令只能输出到会被重建的目录，使用 `.maestro/reports/.maestro-current/` 作为临时目录，再复制 / 提升到正式报告名。stdout-only Maestro run 只能用于诊断或定点重跑；Mobile / Hybrid E2E 进入正式验证范围时，收尾前必须使用 `--format` / `--output` 或项目等价 reporter 产生命名报告，或将报告状态标记为 `blocked`。
- iOS 真机 Maestro 执行遇到 driver setup、端口转发、view hierarchy、tap crash 或版本已知问题时，先由 `maestro-mobile-e2e` 按标签 / 关键字懒加载 lesson 并修复，再重跑最小失败 flow。
- 只有需要把 Web UI 回归固化为仓库内测试资产时，才调用 `web-ui-autotest-generator`；环境、账号、数据准备、清理策略或选择器不稳定时，只输出覆盖缺口和阻塞说明。
- 调用 `web-ui-autotest-generator` 前后，必须遵循本路径契约，避免 external Skill 示例或脚本默认值把 JSON 写到项目根目录：
  - `generate_manifest.py --root . --out tests/e2e/manifest/ui-test-manifest.json --pretty`
  - `audit_selectors.py --root . --out tests/e2e/manifest/ui-selector-audit.json --pretty`
  - `check_coverage.py --root . --manifest tests/e2e/manifest/ui-test-manifest.json --selector-audit tests/e2e/manifest/ui-selector-audit.json --tests-dir tests/e2e --out tests/e2e/manifest/ui-test-coverage.json --pretty`
  - `analyze_failures.py --report tests/e2e/reports/results.json --out tests/e2e/manifest/ui-test-repair-plan.json --pretty`
- 调用 `web-ui-autotest-generator` 后，必须验证可入库 JSON 资产实际位于 `tests/e2e/manifest/`：`ui-test-manifest.json`、`ui-selector-audit.json`、`ui-test-coverage.json`。
- 如果项目根目录存在 `ui-test-manifest.json`、`ui-selector-audit.json` 或 `ui-test-coverage.json`，验证不能标记为完成；先迁移到 `tests/e2e/manifest/` 并同步引用，或将 `Web UI 测试资产` 标记为 `blocked` 并说明原因。
- `ui-test-repair-plan.json` 属于失败分析运行产物；如生成，默认检查路径为 `tests/e2e/manifest/ui-test-repair-plan.json`，并确认它不会被误当作长期测试资产提交。
- Playwright CLI、Java、Maestro CLI、MCP 配置、测试账号、认证方式、测试环境、设备、模拟器、app binary、appId / bundleId 或服务 URL 不可用时，记录 `blocked` 或 `skipped`，不要声称对应验证已通过。

最终输出按全局 / 项目级 `AGENTS.md` 定义的状态枚举报告相关工具状态、运行命令、失败或阻塞原因、生成文件和剩余风险。

## 测试报告与重跑闭环

API、Web E2E、Mobile E2E、Hybrid E2E 或发布前 smoke 进入正式验证时，执行以下报告和重跑规则。项目已有 CI / reporter 配置优先；模板只定义缺省行为和最终报告语义。

报告规则：

- 调试轮次可以沉淀多份本地命名测试报告快照，以便后续对比失败、修复和最终运行；不要删除同一任务中已有的 `playwright-report-*`、`maestro-report-*`、`api-report-*` 或 `unit-report-*` 快照。stdout-only、terminal-only 和 diagnostic-only 命令不能满足最终报告 gate：Playwright `--reporter=list`、只打印终端输出的 API 自定义脚本、以及未启用 `--format` / `--output` 或项目等价 reporter 的 Maestro run 都只能记录为诊断或定点重跑。最终状态只以最后一次计划范围内的运行记录 `Final Full Rerun`。
- 报告型测试必须先记录 `rtk` 决策：`skipped-for-report` 表示为保证 runner 写入报告文件而直接使用原生命令；`fallback-native` 表示 `rtk` 输出或缓存行为导致报告缺失、陈旧或不可证明，已改用原生命令复验。不能只凭 `rtk` 的缓存 / 回放输出声明报告生成或测试通过。
- 一旦执行 Playwright 或 Maestro 运行并产生 runner 原生报告，无论最终全量是否通过，都必须在正式报告快照目录生成命名后的原生报告和同 stem Markdown 汇总。API / integration 和 unit test 如果本轮生成了需要作为证据保留的原生报告，也适用同一规则。对 Playwright，“正式报告快照目录”默认是 `tests/e2e/reports/html/`，不是 `results.json` 所在上级目录，也不是 Playwright HTML reporter 的临时 `outputFolder`。`Final Test Report: generated` 只表示报告文件存在；最终是否全绿由 `Final Full Rerun` 记录。
- 默认目录：API / integration 正式快照使用 `tests/api/reports/`，API 临时输出使用 `tests/api/reports/.api-current/`；Playwright HTML reporter 临时输出使用 `tests/e2e/reports/.playwright-html-current/`，Playwright HTML 正式报告快照使用 `tests/e2e/reports/html/`；Maestro 正式快照使用 `.maestro/reports/`，必要时临时输出使用 `.maestro/reports/.maestro-current/`；unit test 正式报告默认继承项目配置，缺少约定但需要本地证据时使用 `tests/unit/reports/`，必要时临时输出使用 `tests/unit/reports/.unit-current/`。
- 分支名必须进入 API、Playwright 和 Maestro 的正式报告 stem。先从当前 git branch 或项目 / CI 明确的 branch ref 获取原始分支名；detached HEAD 使用 `detached-{short_sha}`；非 git 环境使用 `unknown-branch`。生成文件名时使用 `branch_slug`：只保留字母、数字、`.`、`_`、`-`，将 `/`、空格和其他特殊字符替换为 `_`；Markdown 汇总中记录原始分支名和 `branch_slug`。
- 当报告作为 PR 或知识库证据时，必须同时按验证证据契约记录原始 source ref、完整 commit SHA、worktree state、evidence source、trigger、source revision、environment alignment 和 publication status；不得把 `branch_slug` 当作版本身份。
- 通用防覆盖规则：`coverage/`、`test-results/`、固定 `junit.xml`、runner 的 `current` / `latest` 目录、以及上述点号临时目录都视为 runner 托管输出。它们可能在下一次运行前被清空、覆盖或重建；需要保留时，必须先复制 / 提升到正式快照目录和时间戳 stem，再启动下一次会改写同一 runner 输出的命令。
- Playwright 命名：`playwright-report-{feature_file_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}.html` + `playwright-report-{feature_file_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}.md`。`feature_file_name` 默认取关联 BDD `.feature` 文件名去掉扩展名；smoke test 固定使用 `smoke`；一次运行覆盖多个 `.feature` 时优先使用明确 suite 名，否则使用 `multi-feature`。如果不是 smoke 且无法追踪到 BDD `.feature`，不要编造文件名，先将 BDD 追踪标记为 `blocked`。
- Maestro 命名：`maestro-report-{flow_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}.xml` 或 `maestro-report-{flow_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}.html`，并生成 `maestro-report-{flow_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}.md`。`flow_name` 取 Maestro flow 文件名 stem，smoke flow 使用 `smoke`，不改成 `feature_file_name`；源 `.feature` 路径和场景名写入 Markdown 汇总。
- Playwright 默认 HTML reporter 生成 `index.html` 时，在每次需要保留的运行结束后必须从 `tests/e2e/reports/.playwright-html-current/` 将其复制为上述正式报告名；命名后的 HTML 是正式报告。正式报告不得保存在 `.playwright-html-current/` 中，因为下一次 Playwright 运行可能清空该目录。Markdown 汇总必须与命名后的 HTML 完全同 stem；不得把 `results.json`、`junit.xml`、`test-results/` 或默认 `index.html` 的 stem 用作最终 Markdown 文件名，`results.md`、`result.md`、`junit.md`、`index.md` 均不能满足 `Run Summary MD: generated`。如果 Playwright 已产生 `results.json`、`junit.xml` 或等价结果但没有 `index.html`，先按项目配置重跑或补启用 HTML reporter，不能用 JSON / JUnit 报告替代命名 HTML 和同 stem `.md`。如果 HTML reporter 目录中存在 `data/`、trace、附件或其他相对资源，必须同时复制完整资源目录，或生成以 `playwright-report-{feature_file_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}/index.html` 为入口的完整快照目录，并让 Markdown 汇总指向该入口。
- API 命名示例：`api-report-{suite_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}.xml` / `.json` / `.txt` + `api-report-{suite_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}.md`；没有明确 suite 时使用 `api-report-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}` stem。没有原生 reporter 的 API / integration 命令，如果仍是本轮正式验证证据，必须把 stdout、stderr、exit code、运行命令和时间戳捕获为 `.txt` 或 `.json` raw report，不能只在最终回复里粘贴终端结果。
- API Markdown 汇总必须包含“覆盖范围 -> API URI”映射表。推荐列为：覆盖范围、HTTP 方法、URI path、测试脚本 / case、期望状态码、验证的副作用或响应字段、关联 BDD / contract。没有 route manifest 时从测试源码、OpenAPI / schema、客户端调用或实际请求日志提取；无法确定 URI 时将该覆盖项标记为 `blocked` 或 `missing-uri`，不要用空泛覆盖描述冒充完整报告。
- Unit 命名示例：`unit-report-{suite_name}-{YYYY_mm_dd}-{HH_MM_SS}.xml` / `.json` / `.html` / `.lcov` + `unit-report-{suite_name}-{YYYY_mm_dd}-{HH_MM_SS}.md`。unit test 不强制每轮生成正式报告；但一旦项目命令或 CI 兼容命令已经产生本轮要保留的报告，就不能只依赖会被下一轮重写的 coverage 或 JUnit 固定路径。
- 如果项目配置强制多个 reporter，每次需要保留的运行只生成一组命名报告和一份 Markdown 汇总；最终结论仍以最后一次计划范围内运行判断。
- 未最终全量通过时，仍生成该次运行的命名报告和同 stem Markdown 汇总，但不得声明“全量通过”或“full-stack 通过”；最终输出说明失败 / 阻塞原因、已尝试命令和剩余风险。
- 如果 CLI 未安装、环境预检阻塞或 runner 崩溃到没有任何原生报告产物，`Final Test Report` 和 `Run Summary MD` 标记为 `blocked`，并说明缺失原因；只要 runner 已有原生产物，就不得把 `Run Summary MD` 标记为 `not-needed`。

失败处理与重跑顺序：

1. 首轮失败后，分类根因：产品代码、测试代码、BDD / 规格、mock / contract drift、环境 / 账号 / 数据 / 设备、flaky / timing、或任务外失败。
2. 当前任务范围内可修复时，修复后先重跑失败 case / failed spec / failed flow。
3. 定点重跑通过后，运行受影响子集，例如同 `.feature`、同 API endpoint、同页面流、同测试文件、同 Maestro flow 或同平台 smoke。
4. 最后运行计划范围内的全量验证；该轮通过才能声明最终全量通过，但只要 runner 产出原生报告，无论通过或失败都必须生成命名报告和 Markdown 汇总。
5. 如果 runner 因 fail-fast 停在第一个失败，修复并定点通过后，必须继续运行未覆盖的后续测试，或直接重跑计划范围内全量验证。
6. 不默认从中间 resume 一个已污染的测试环境；只有项目 runner 明确支持可靠 resume 时才使用。

Markdown 汇总必须记录：

- 汇总正文必须使用中文撰写；只有状态枚举值、命令、文件路径、case / spec / flow 名称、错误原文和技术标识符可以保留英文。
- 测试范围、运行 case / spec / flow 列表、`E2E Mode`、`Mock Strategy`、原始分支名、`branch_slug`、`.feature` 路径和场景名。
- 当报告作为 PR 或知识库证据时，记录 `Evidence Source`、repository key、原始 source ref、完整 commit SHA、worktree state、`Source Revision`、trigger、`Environment Alignment`、`Evidence Publication` 和 evidence sidecar / envelope 路径。
- API / integration 汇总必须包含 URI 覆盖矩阵，逐项映射覆盖范围和 `method + URI path`，并标出对应测试脚本 / case 与 contract / schema / `.feature` 依据。
- 最终正式报告路径、总执行轮次、每轮命令。
- 每轮失败 case / spec / flow、失败原因分类、修复动作和修改文件摘要。
- 定点重跑、受影响子集重跑和最终全量重跑结果。
- 未执行项、跳过原因、剩余风险，以及 contract / mock / 环境 / 账号 / 设备说明。
- 不写入真实账号、密钥、PII、生产数据、完整 token、敏感请求头或生产截图。

最终输出中额外报告：

- `Final Test Report`: `generated` / `blocked` / `not-supported` / `not-needed`。
- `Run Summary MD`: `generated` / `blocked` / `not-needed`。
- `Targeted Rerun`: `passed` / `failed` / `blocked` / `not-needed`。
- `Final Full Rerun`: `passed` / `failed` / `blocked` / `skipped-with-risk` / `not-needed`。
- `Evidence Source`: `developer-local` / `ci` / `knowledge-server` / `not-needed`。
- `Source Revision`: `exact` / `dirty` / `unknown` / `not-needed`。
- `Environment Alignment`: `verified` / `unverified` / `mismatch` / `not-needed`。
- `Evidence Publication`: `local-only` / `published` / `blocked` / `not-configured` / `not-needed`。

## 语言验证通用规则

所有语言都优先继承项目已有 CI、README、Makefile、package scripts、Gradle / Maven wrapper、Xcode scheme、CMake preset 或更深层 `AGENTS.md` 定义的命令。下面命令只是缺少项目明确约定时的候选项。

验证时同时说明：

- 代码规范 / lint / format 检查是否运行。
- unit test 是否运行。
- integration / API / E2E 是否与本次改动相关。
- 报告路径是否由项目配置生成；模板不为 unit test 强制统一报告目录，但会被 runner 清空 / 覆盖的报告必须先归档到项目约定目录或 `tests/unit/reports/` 的时间戳快照后再作为证据引用。
- 跳过或阻塞的原因。

## Node / JavaScript / TypeScript

优先使用项目包管理器和 CI scripts，不切换包管理器。常见命令：

优先（lint / typecheck / build 等非报告型命令）：

```bash
rtk npm run lint
rtk npm run typecheck
rtk npm run build
```

测试命令先按 `rtk` 与报告型测试 Gate 判断；需要报告落地时优先：

```bash
npm run test
```

回退：

```bash
npm run lint
npm run typecheck
npm run build
```

当修改以下内容时，运行 typecheck：

- TypeScript 类型
- DTO
- API 返回值
- 组件 props
- 状态结构
- 共享接口

如果项目没有 `typecheck` script，不要凭空新增；记录为未定义并运行项目实际可用的类型检查或构建命令。

---

## Python

优先（lint / format / typecheck 等非报告型命令）：

```bash
rtk ruff check .
rtk ruff format .
rtk ty check .
```

测试命令先按 `rtk` 与报告型测试 Gate 判断；需要报告落地时优先：

```bash
uv run pytest
```

回退：

```bash
uv run ruff check .
uv run ruff format .
uv run ty check .
```

规则：

- 修改 Python 代码后，运行 `ruff check`。
- 涉及格式化时，运行 `ruff format`。
- 修改类型、函数签名或返回结构时，运行 `ty check`。
- 修改业务逻辑、数据处理、API 或 bug 修复时，运行 `pytest`。
- 不绕过 `pyproject.toml`、`uv.lock`、`pytest.ini` 或 `ruff.toml`。
- 如果项目使用 `mypy`、`pyright`、`tox`、`nox`、`coverage` 或 CI 定义的 test matrix，优先继承项目命令。

---

## Go

测试命令先按 `rtk` 与报告型测试 Gate 判断；需要报告落地时优先：

```bash
go test ./...
```

规则：

- 涉及格式修改时，运行 `gofmt`。
- 修改并发、错误处理、反射或格式化字符串时，运行 `go vet ./...`。
- 仅当依赖变化时，运行 `go mod tidy`。
- 不无故修改 `go.mod` 或 `go.sum`。
- 如果项目有 Makefile、CI matrix、race test、coverage 或 package 子集约定，优先继承项目命令。

---

## Dart / Flutter

优先继承项目的 Flutter / Dart CI、Melos、Makefile 或 package scripts。

常见候选（format / analyze 可优先 `rtk`；test 先按 `rtk` 与报告型测试 Gate 判断）：

```bash
rtk dart format --set-exit-if-changed .
rtk dart analyze
dart test
```

Flutter 项目常见候选：

```bash
rtk flutter analyze
flutter test
```

规则：

- 修改 Dart 代码后，运行项目约定的 format / analyze。
- 修改业务逻辑、状态管理、数据转换、widget 行为或 bug 修复时，运行 unit test / widget test。
- Flutter integration test、Maestro Mobile E2E 或平台构建只在改动触及对应用户旅程、平台能力或发布风险时运行。

---

## Java

优先使用项目 wrapper 和 CI tasks，不绕过 Gradle / Maven 配置。

Gradle 常见候选（测试命令先按 `rtk` 与报告型测试 Gate 判断；需要报告落地时优先原生命令）：

```bash
./gradlew test
./gradlew check
```

Maven 常见候选：

```bash
mvn test
mvn verify
```

规则：

- 修改 Java 代码后，运行项目配置的 Checkstyle、Spotless、PMD、Error Prone 或等价 lint / format gate。
- 修改业务逻辑、API、持久化、并发或 bug 修复时，运行 unit test。
- 涉及集成、容器、数据库或外部服务时，按项目 CI 运行 integration test profile；不可用时说明阻塞原因。

---

## Kotlin

优先使用项目 Gradle wrapper、Android Gradle Plugin、Kotlin Multiplatform 或 CI 任务。

常见候选（测试命令先按 `rtk` 与报告型测试 Gate 判断；需要报告落地时优先原生命令）：

```bash
./gradlew test
./gradlew check
```

Android 项目常见候选：

```bash
./gradlew testDebugUnitTest
```

规则：

- 修改 Kotlin 代码后，运行项目配置的 ktlint、detekt、Spotless 或等价 lint / format gate。
- 修改业务逻辑、ViewModel、repository、domain layer、serialization 或 bug 修复时，运行 unit test。
- Android instrumentation test、Compose UI test、Maestro Mobile E2E 只在改动触及设备行为或用户旅程时运行。

---

## C++

优先继承项目 CMake preset、Makefile、Bazel、Ninja、CTest 或 CI 命令；不要为验证临时重构构建系统。

常见候选：

```bash
rtk cmake --build build
ctest --test-dir build --output-on-failure
```

规则：

- 修改 C++ 代码后，运行项目配置的 `clang-format`、`clang-tidy`、`cppcheck` 或等价静态检查。
- 修改核心逻辑、内存所有权、并发、ABI/API、序列化或 bug 修复时，运行 unit test。
- 如果项目没有已配置 build 目录，按 README / CI 创建或选择 build 目录；无法确定时先询问或记录阻塞，不随意生成长期构建配置。

---

## Swift

优先继承 SwiftPM、Xcode scheme、xcodebuild、XcodeBuildMCP 或 CI 配置。

SwiftPM 常见候选（测试命令先按 `rtk` 与报告型测试 Gate 判断；需要报告落地时优先原生命令）：

```bash
swift test
```

Xcode 常见候选：

```bash
xcodebuild test -scheme <scheme> -destination <destination>
```

规则：

- 修改 Swift 代码后，运行项目配置的 SwiftFormat、SwiftLint、`swift format` 或等价 lint / format gate。
- 修改业务逻辑、model、service、view model、App Intents、serialization 或 bug 修复时，运行 XCTest / Swift Testing unit test。
- iOS UI test、device test 或 Maestro Mobile E2E 只在改动触及真实设备行为、权限、相机、上传、深链、系统弹窗或用户旅程时运行。
- 如果 Xcode scheme、destination、simulator 或 signing 不明确，记录阻塞；不要假装测试已运行。

---

## Objective-C

优先继承 Xcode workspace / project、scheme、xcodebuild、XcodeBuildMCP 或 CI 配置。

常见候选：

```bash
xcodebuild test -scheme <scheme> -destination <destination>
```

规则：

- 修改 Objective-C / Objective-C++ 代码后，运行项目配置的 clang-format、clang-tidy、OCLint 或等价 lint / static analysis gate。
- 修改业务逻辑、runtime、category、delegate、桥接层、内存管理、C++ interop 或 bug 修复时，运行 XCTest unit test。
- 涉及真机能力、系统权限、Hybrid bridge 或跨页面移动流程时，按项目约定运行 Xcode UI test 或 Maestro Mobile E2E。
- 如果 workspace、scheme、destination、provisioning 或 signing 不明确，记录阻塞并说明需要的项目事实。
