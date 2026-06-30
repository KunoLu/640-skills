---
name: project-validation
description: Use after code changes to choose and run validation commands for Node, JavaScript, TypeScript, Python, Go, Dart, Java, Kotlin, C++, Swift, or Objective-C projects. Prefer project-defined commands and report skipped checks and risks.
---

# 项目验证 Skill

代码修改后使用本 Skill。

## 通用规则

- 优先使用项目已定义的命令。
- 当 `rtk` 可用时，优先使用 `rtk`。
- 不绕过项目配置。
- 除非任务需要，不修改 lock 文件。
- 如果完整检查成本较高，先运行聚焦检查。
- 说明跳过的检查和剩余风险。

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

## Web / Mobile 测试工具 Gate

修改 Web UI、路由、表单、登录态、权限、跨页面流程、API 集成、发布流程、移动 App 用户旅程、Hybrid App 或关键用户路径后，必须按全局 / 项目级 `AGENTS.md` 的工具职责边界主动判定 Chrome DevTools MCP、Playwright MCP、Playwright CLI、Maestro CLI、Maestro MCP 和 `web-ui-autotest-generator` 是否适用。

本 Skill 只负责验证阶段 gate：

- 先按修改范围选择最小有效验证：项目测试、浏览器诊断、Playwright Web 回归、Maestro 移动 / Hybrid flow、或 Web UI 测试资产覆盖评估。
- 对 API / Web / Mobile / Hybrid 链路，先判定 `E2E Mode`: `full-stack` / `contract-backed` / `mock-backed` / `app-mocked` / `smoke-only` / `backend-only` / `blocked`。mock-backed、app-mocked 或 contract-backed 测试只能证明对应 contract / mock 假设成立，不能报告为 full-stack 通过。
- API / integration 测试优先继承项目既有测试框架和报告配置；没有项目约定且需要本轮正式报告时，默认报告目录为 `tests/api/reports/`。
- Web 可重复回归必须优先运行项目已有 Playwright CLI 命令；Chrome DevTools MCP / Playwright MCP 只提供诊断、探索或 locator 证据。
- Web E2E 最终正式 HTML 报告默认进入 `tests/e2e/reports/html/`，除非项目 Playwright 配置已有更强约定；Playwright 默认生成的 `index.html` 可作为中间产物或工具兼容产物，命名后的 HTML 才是正式报告。
- Maestro 相关验证必须先满足 Java 17+ 和 Maestro CLI；MCP 缺失但 CLI 可用时，继续执行已有 `maestro test` flow 并单独报告 MCP 状态。
- 需要从 BDD 场景生成或维护 Mobile / Hybrid Maestro flow 时，调用 `maestro-mobile-e2e`，并确认可入库 flow 资产位于 `maestro/flow/`。
- Maestro 最终正式报告必须写入项目根目录 `.maestro/reports/`；默认只生成一个项目需要的原生报告格式，命名为 `maestro-report-{flow_name}-{YYYY_mm_dd}-{HH_MM_SS}.xml` 或 `maestro-report-{flow_name}-{YYYY_mm_dd}-{HH_MM_SS}.html`。`flow_name` 取 Maestro flow 文件名 stem，smoke flow 使用 `smoke`；HTML 只在项目或用户需要人类可读报告时生成。
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

- 调试轮次不要沉淀多份正式测试报告。失败后的定点重跑可以使用 stdout、runner 临时目录或项目默认临时产物排障，但最终正式报告只保留最后一次计划范围内全量通过的报告。
- 最终全量通过后，在同一报告目录生成一份 Markdown 汇总，文件名与正式报告共享同一时间戳和 stem，仅扩展名为 `.md`。
- 默认目录：API / integration 使用 `tests/api/reports/`，Playwright HTML 正式报告使用 `tests/e2e/reports/html/`，Maestro 使用 `.maestro/reports/`。
- Playwright 命名：`playwright-report-{feature_file_name}-{YYYY_mm_dd}-{HH_MM_SS}.html` + `playwright-report-{feature_file_name}-{YYYY_mm_dd}-{HH_MM_SS}.md`。`feature_file_name` 默认取关联 BDD `.feature` 文件名去掉扩展名；smoke test 固定使用 `smoke`；一次运行覆盖多个 `.feature` 时优先使用明确 suite 名，否则使用 `multi-feature`。如果不是 smoke 且无法追踪到 BDD `.feature`，不要编造文件名，先将 BDD 追踪标记为 `blocked`。
- Maestro 命名：`maestro-report-{flow_name}-{YYYY_mm_dd}-{HH_MM_SS}.xml` 或 `maestro-report-{flow_name}-{YYYY_mm_dd}-{HH_MM_SS}.html`，并生成 `maestro-report-{flow_name}-{YYYY_mm_dd}-{HH_MM_SS}.md`。`flow_name` 取 Maestro flow 文件名 stem，smoke flow 使用 `smoke`，不改成 `feature_file_name`；源 `.feature` 路径和场景名写入 Markdown 汇总。
- Playwright 默认 HTML reporter 生成 `index.html` 时，可在最终全量通过后将其移动或复制为上述正式报告名；命名后的 HTML 是正式报告，是否保留 `index.html` 由项目配置决定。
- API 命名示例：`api-report-{YYYY_mm_dd}-{HH_MM_SS}.xml` + `api-report-{YYYY_mm_dd}-{HH_MM_SS}.md`。
- 如果项目配置强制多个 reporter，只把最后一次全量通过运行生成的 reporter 集合视为正式报告；Markdown 汇总仍只生成一份。
- 未最终全量通过时，不生成或声明“全量通过”正式报告；最终输出说明失败 / 阻塞原因、已尝试命令和剩余风险。

失败处理与重跑顺序：

1. 首轮失败后，分类根因：产品代码、测试代码、BDD / 规格、mock / contract drift、环境 / 账号 / 数据 / 设备、flaky / timing、或任务外失败。
2. 当前任务范围内可修复时，修复后先重跑失败 case / failed spec / failed flow。
3. 定点重跑通过后，运行受影响子集，例如同 `.feature`、同 API endpoint、同页面流、同测试文件、同 Maestro flow 或同平台 smoke。
4. 最后运行计划范围内的全量验证；只有该轮通过才生成正式原生报告和 Markdown 汇总。
5. 如果 runner 因 fail-fast 停在第一个失败，修复并定点通过后，必须继续运行未覆盖的后续测试，或直接重跑计划范围内全量验证。
6. 不默认从中间 resume 一个已污染的测试环境；只有项目 runner 明确支持可靠 resume 时才使用。

Markdown 汇总必须记录：

- 测试范围、运行 case / spec / flow 列表、`E2E Mode`、`Mock Strategy`、`.feature` 路径和场景名。
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

## 语言验证通用规则

所有语言都优先继承项目已有 CI、README、Makefile、package scripts、Gradle / Maven wrapper、Xcode scheme、CMake preset 或更深层 `AGENTS.md` 定义的命令。下面命令只是缺少项目明确约定时的候选项。

验证时同时说明：

- 代码规范 / lint / format 检查是否运行。
- unit test 是否运行。
- integration / API / E2E 是否与本次改动相关。
- 报告路径是否由项目配置生成；模板不为 unit test 强制统一报告目录。
- 跳过或阻塞的原因。

## Node / JavaScript / TypeScript

优先使用项目包管理器和 CI scripts，不切换包管理器。常见命令：

优先：

```bash
rtk npm run lint
rtk npm run typecheck
rtk npm run test
rtk npm run build
```

回退：

```bash
npm run lint
npm run typecheck
npm run test
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

优先：

```bash
rtk ruff check .
rtk ruff format .
rtk ty check .
rtk pytest
```

回退：

```bash
uv run ruff check .
uv run ruff format .
uv run ty check .
uv run pytest
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

优先：

```bash
rtk go test ./...
```

回退：

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

常见候选：

```bash
rtk dart format --set-exit-if-changed .
rtk dart analyze
rtk dart test
```

Flutter 项目常见候选：

```bash
rtk flutter analyze
rtk flutter test
```

规则：

- 修改 Dart 代码后，运行项目约定的 format / analyze。
- 修改业务逻辑、状态管理、数据转换、widget 行为或 bug 修复时，运行 unit test / widget test。
- Flutter integration test、Maestro Mobile E2E 或平台构建只在改动触及对应用户旅程、平台能力或发布风险时运行。

---

## Java

优先使用项目 wrapper 和 CI tasks，不绕过 Gradle / Maven 配置。

Gradle 常见候选：

```bash
rtk ./gradlew test
rtk ./gradlew check
```

Maven 常见候选：

```bash
rtk mvn test
rtk mvn verify
```

规则：

- 修改 Java 代码后，运行项目配置的 Checkstyle、Spotless、PMD、Error Prone 或等价 lint / format gate。
- 修改业务逻辑、API、持久化、并发或 bug 修复时，运行 unit test。
- 涉及集成、容器、数据库或外部服务时，按项目 CI 运行 integration test profile；不可用时说明阻塞原因。

---

## Kotlin

优先使用项目 Gradle wrapper、Android Gradle Plugin、Kotlin Multiplatform 或 CI 任务。

常见候选：

```bash
rtk ./gradlew test
rtk ./gradlew check
```

Android 项目常见候选：

```bash
rtk ./gradlew testDebugUnitTest
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
rtk ctest --test-dir build --output-on-failure
```

规则：

- 修改 C++ 代码后，运行项目配置的 `clang-format`、`clang-tidy`、`cppcheck` 或等价静态检查。
- 修改核心逻辑、内存所有权、并发、ABI/API、序列化或 bug 修复时，运行 unit test。
- 如果项目没有已配置 build 目录，按 README / CI 创建或选择 build 目录；无法确定时先询问或记录阻塞，不随意生成长期构建配置。

---

## Swift

优先继承 SwiftPM、Xcode scheme、xcodebuild、XcodeBuildMCP 或 CI 配置。

SwiftPM 常见候选：

```bash
rtk swift test
```

Xcode 常见候选：

```bash
rtk xcodebuild test -scheme <scheme> -destination <destination>
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
rtk xcodebuild test -scheme <scheme> -destination <destination>
```

规则：

- 修改 Objective-C / Objective-C++ 代码后，运行项目配置的 clang-format、clang-tidy、OCLint 或等价 lint / static analysis gate。
- 修改业务逻辑、runtime、category、delegate、桥接层、内存管理、C++ interop 或 bug 修复时，运行 XCTest unit test。
- 涉及真机能力、系统权限、Hybrid bridge 或跨页面移动流程时，按项目约定运行 Xcode UI test 或 Maestro Mobile E2E。
- 如果 workspace、scheme、destination、provisioning 或 signing 不明确，记录阻塞并说明需要的项目事实。
