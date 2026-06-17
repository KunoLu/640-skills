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

## Web / E2E 测试工具 Gate

修改 Web UI、路由、表单、登录态、权限、跨页面流程、API 集成、发布流程或关键用户路径后，必须按项目级 `AGENTS.md` 主动判定 TestSprite 和 `web-ui-autotest-generator` 是否适用。

TestSprite 适用于：

- 端到端业务流程、UI / API 集成、回归验证、测试计划生成或发布前 smoke。
- Trellis 验收标准要求 UI、E2E、API 或回归验证。
- 修复用户可见 bug 后需要独立回归验证。
- GitNexus impact / detect_changes 为 HIGH / CRITICAL，且影响 Web、API 或发布流程。

TestSprite 规则：

- 先确认 TestSprite MCP 是否可调用、服务 URL / `localPort` 是否可访问、`projectPath`、`type`、`testScope` 是否明确。
- 调用会打开外部 UI 的 bootstrap / 配置工具前，必须先确认或生成本次测试范围对应的 PRD 文件，并向用户输出可上传 PRD 的绝对路径、测试范围、`projectPath`、`localPort`、`type` 和 `testScope`。
- 如果项目已存在 `.testsprite/config.json`，不要为了新增测试、修改测试或重跑测试重新 bootstrap。
- 配置门户、PRD 上传、测试账号、认证方式或测试环境缺失时，输出 `blocked` 和剩余配置项，不要声称已完成 TestSprite 测试。

`web-ui-autotest-generator` 适用于：

- 关键 Web UI 回归路径需要固化为仓库内可维护测试资产。
- 项目已有 Playwright / Cypress，需要扩展覆盖。
- TestSprite、浏览器验证或人工复核发现应进入 CI / 本地 E2E 的覆盖缺口。
- 用户明确要求 Playwright、E2E suite、Web UI 自动化测试代码或 UI 回归测试。

`web-ui-autotest-generator` 规则：

- 可以先只做覆盖评估，不必每次生成大量测试。
- 先生成或复核 `ui-test-manifest.json`、`ui-selector-audit.json`，再决定是否扩展 Page Object 和 spec。
- 环境、账号、数据准备、清理策略、业务规则或选择器不稳定时，只输出覆盖缺口和阻塞说明，不强行生成脆弱测试。
- 只有用户明确同意修改产品代码时，才补充 `data-testid`、`data-cy` 或可访问名称。

最终输出必须包含：

- `TestSprite`: `run` / `blocked` / `skipped`，原因、PRD 上传路径、执行结果或阻塞项。
- `Web UI 自动化测试资产`: `generated` / `coverage-only` / `blocked` / `skipped`，原因、生成文件、执行命令或剩余风险。

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
