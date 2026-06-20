---
name: project-validation
description: Use after code changes to choose and run validation commands for Node, JavaScript, TypeScript, Python, or Go projects. Prefer project-defined commands and report skipped checks and risks.
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

最终输出中必须说明：

- `BDD`: `run` / `traceable` / `blocked` / `skipped`。
- 涉及的 `.feature` 或持久 BDD 规格路径。
- BDD 语言状态：沿用项目既有风格、默认中文场景文本 + 英文关键词、用户明确覆盖，或 `blocked` 的原因。
- 运行的 BDD runner 或追踪测试命令。
- 未自动化场景、阻塞原因和剩余风险。

## Web / Mobile 测试工具 Gate

修改 Web UI、路由、表单、登录态、权限、跨页面流程、API 集成、发布流程、移动 App 用户旅程、Hybrid App 或关键用户路径后，必须按全局 / 项目级 `AGENTS.md` 的工具职责边界主动判定 Chrome DevTools MCP、Playwright MCP、Playwright CLI、Maestro CLI、Maestro MCP 和 `web-ui-autotest-generator` 是否适用。

本 Skill 只负责验证阶段 gate：

- 先按修改范围选择最小有效验证：项目测试、浏览器诊断、Playwright Web 回归、Maestro 移动 / Hybrid flow、或 Web UI 测试资产覆盖评估。
- Web 可重复回归必须优先运行项目已有 Playwright CLI 命令；Chrome DevTools MCP / Playwright MCP 只提供诊断、探索或 locator 证据。
- Maestro 相关验证必须先满足 Java 17+ 和 Maestro CLI；MCP 缺失但 CLI 可用时，继续执行已有 `maestro test` flow 并单独报告 MCP 状态。
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

## Node / JavaScript / TypeScript

优先：

```bash
rtk npm run lint
rtk npm run test
rtk npm run build
```

回退：

```bash
npm run lint
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

除非任务需要，不切换包管理器。

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
