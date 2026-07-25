# UPDATE

本次检查以 `ENTRYPOINT.md` 的“当前使用版本”为固定起点；未写回该文件，也未访问或修改 Orca live automation。以下来源均于 2026-07-24 检查。

## Codex v0.145.0 -> v0.145.0

- **检测结果**：GitHub `releases/latest` 返回稳定版 `rust-v0.145.0`；仓库同时存在 `rust-v0.146.0-alpha.5`，但当前通道为 `stable-only`，因此不纳入比较。
- **release 汇总与兼容性**：没有高于起点的稳定发布，故没有跨版本 release note、破坏性变更或迁移步骤需要执行。
- **证据补充**：稳定 release API 有效；无需对未发生的升级区间读取 compare、commit diff、manifest 或 npm tarball。
- **工作流影响分析**：以 `Codex`、MCP、plugin / connector 等关键词扫描 `AGENTS.md`、版本化 prompt、Onboard catalog / schema / Skill / Reference / 脚本、两份 AGENTS 模板和 bundled Skills；现有规则已将 Codex CLI 与延迟工具发现分开描述。没有上游稳定版差异可沉淀为新规则。

## Trellis v0.6.8 -> v0.6.8

- **检测结果**：`releases/latest` 返回 404，改以 GitHub tags 为准；最新稳定 tag 为 `v0.6.8`。
- **release 汇总与兼容性**：没有高于起点的稳定 tag，故没有跨版本 release note、破坏性变更或迁移步骤需要执行。
- **证据补充**：该仓库未提供可用的 latest release；tags API 提供了当前 tag 与 commit `dc68f5a92a68489b681c511f4a784e413d724e85`。由于没有升级区间，未读取 compare、commit diff 或升级 manifest。
- **工作流影响分析**：扫描命中 Trellis 初始化、`trellis update`、任务和 Skill 编排规则；没有新 tag 可改变当前边界。当前仓库不存在 `.trellis/workflow.md`，本次未执行 Trellis 阶段。

## GitNexus v1.6.9 -> v1.6.9

- **检测结果**：GitHub `releases/latest` 返回 `v1.6.9`。
- **release 汇总与兼容性**：该 release 的多仓 HTTP 路由 / consumer、PDG trace、默认 workspace index 随 checkout 分支、Java / Python taint 模型以及 `gitnexus analyze` 重建索引建议，均属于当前基线版本；没有高于起点的稳定发布。
- **破坏性变更与迁移**：没有跨版本迁移。上游 release 对升级到该版本建议重新执行 `gitnexus analyze`，但本次未升级，故不触发该操作。
- **证据补充**：release body、升级命令和 compare 链接均可用；因没有升级区间，未额外读取 commit diff 或发布包。
- **工作流影响分析**：关键词 `gitnexus analyze`、PDG、taint、FTS、group 在受检规则和 Onboard 内容中已有职责边界；不存在需要新增或修改的长期规则。

## Playwright v1.61.1 -> v1.61.1

- **检测结果**：GitHub `releases/latest` 返回 `v1.61.1`。
- **release 汇总与兼容性**：release body 仅列出 matcher 覆盖、UI mode API 调用计数、WebSocket trace 时间、Node 22.15 sync loader 与 pnpm workspace ESM loader 的修复；没有高于起点的稳定发布。
- **破坏性变更与迁移**：没有跨版本迁移或规则变更。
- **证据补充**：release body 可用；因没有升级区间，未读取 compare、commit diff 或 npm tarball。
- **工作流影响分析**：扫描命中 Playwright CLI / MCP 的既有检测、报告和职责边界；没有新稳定版本要求改写。

## Maestro cli-2.7.0 -> cli-2.7.0

- **检测结果**：GitHub `releases/latest` 返回 `cli-2.7.0`，与起点一致。
- **release 汇总**：release body 指向官方 changelog；`2.7.0` 记录了 per-flow artifact manifest、每步截图与失败 hierarchy、`describe_cloud_run`、Unicode 输入，以及 iOS / Android / Web / CLI 的修复。
- **破坏性变更与迁移**：没有跨版本升级。`maestro chat` 已停止并引导到 Maestro MCP；本仓库未依赖该命令。为避免遗漏当前基线已具备的 Cloud 诊断能力，已将终态 Cloud per-flow run 的状态 / artifact 读取写入 Maestro MCP 边界和 `maestro-mobile-e2e` 工作流。
- **证据补充**：release API 可用；正文不足时已读取官方 `CHANGELOG.md` 的 `2.7.0` 章节。没有高于起点的版本，因此无需 compare、commit diff、migration manifest 或发布包分析。
- **工作流影响分析**：关键词扫描确认现有内容只覆盖设备检查、hierarchy、截图和 flow 辅助，未覆盖 Cloud terminal-run artifacts。已最小化更新 `AGENTS.global.md` 模板、Maestro Skill 与两份用户可见 README；其余受检文件没有需要修改的命中。

## 本轮规则与文档结论

- 更新了可复用的 Maestro MCP 边界：Cloud 运行到终态后，使用 `get_cloud_run_status` 获得 per-flow run 标识；需要诊断时用 `describe_cloud_run` 读取该 run 的状态和 artifacts。完整 archive 仅在确有需要时请求，避免把诊断 artifact 误当作正式测试报告。
- 已更新 `CHANGELOG.md` 的未发布章节，以及 `README.md` / `README.html` 的工具职责说明。版本化 automation prompt 不涉及 Maestro Cloud 操作流程，保持不变。
- `ENTRYPOINT.md` 只读：所有区间起点均与其版本监控表一致，没有写回任何工具版本号。
