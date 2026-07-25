# UPDATE

本次检查日期：2026-07-25。`ENTRYPOINT.md` 是固定比较基线；本次没有回写其中任何当前使用版本。

## Codex v0.145.0 -> v0.145.0

- **检测结果**：`openai/codex` 的最新 stable release 为 `rust-v0.145.0`，与基线版本规范化后相同；更新的 `rust-v0.146.0-alpha.*` 属于 prerelease，按 `stable-only` 策略排除。
- **来源与依据**：GitHub Releases latest：<https://api.github.com/repos/openai/codex/releases/latest>。
- **破坏性变更与迁移**：没有跨版本区间；无需汇总 release note、compare、迁移 manifest 或发布包内容。
- **Agent harness 影响**：无版本变更，不修改规则、模板或安装行为。

## Trellis v0.6.8 -> v0.6.9

- **检测结果**：`mindfold-ai/trellis` 未提供 GitHub “latest release”（API 返回 404），但 tags 显示最新 stable tag 为 `v0.6.9`；基线 `v0.6.8` 至目标版本共 28 个提交。
- **来源与依据**：
  - tags：<https://api.github.com/repos/mindfold-ai/trellis/tags?per_page=100>；
  - compare：<https://api.github.com/repos/mindfold-ai/trellis/compare/v0.6.8...v0.6.9>；
  - release commit 与文件列表：<https://api.github.com/repos/mindfold-ai/trellis/commits/4a5a8df3da295a84fde7ef626fa6cd710c94e1f6>；
  - 官方 `0.6.9` migration manifest：`packages/cli/src/migrations/manifests/0.6.9.json`。仓库根 `CHANGELOG.md` 在该 tag 不存在（raw URL 返回 404），因此不把缺失的 release body / changelog 当作“无可追溯变更”。
- **Release 汇总**：新增 Snow CLI 平台；对 Python、Pi 和 OpenCode 的子代理上下文注入加入可配置字节上限与二进制文件引用提示；`prompt_injection.skip_keyword` 可为单次提示关闭 per-turn workflow-state 注入；Codex 生成的 `trellis-*.toml` 现在保留用户设置的 `model` 与 `model_reasoning_effort`；Channel 支持受限的 `trusted_context_dirs` 与顶层 Trellis symlink 自动信任；脚本新增结构化 session 与 task metadata 操作；append-only journal 的合并冲突得到缓解。
- **破坏性变更与迁移**：manifest 标记 `breaking: false`、`recommendMigrate: false`，没有强制 migration。采用该版本时仍应先运行 `trellis update`，复查生成 diff；不手动移动受管目录或绕过 containment / safe-name guard。
- **Agent harness 影响与处理**：更新 `trellis-workflow`，要求保留默认的受限上下文注入、把 `0`（无限制）视为显式用户风险、正确理解单次 skip keyword、以窄 allowlist 管理 linked-worktree context，并在更新后复查可保留的 Codex 子代理模型字段。更新 `trellis-channel`，禁止用宽泛父目录、嵌套 symlink 或手工解引用绕过 Channel context containment。
- **本地规则扫描与处理决定**：升级前以 `context_injection`、`no-trellis`、`trusted_context_dirs`、`auto_trust_trellis_symlinks`、`Snow CLI`、`model_reasoning_effort`、`set-meta`、`task.py create --meta`、`add_session`、`journal-` 扫描 `AGENTS.md`、版本化 prompt、catalog/schema、Onboard 文档与脚本、全局/项目 AGENTS 模板及全部 bundled Skill；均无既有命中。只有 `trellis-workflow` 与 `trellis-channel` 直接承担这些 Trellis runtime 边界，因此最小化更新这两个 Skill。`AGENTS.md`、catalog/schema、Onboard 安装脚本和 AGENTS 模板不承担该运行时配置契约，保持不变。

## GitNexus v1.6.9 -> v1.6.9

- **检测结果**：最新 stable release 仍为 `v1.6.9`，与基线相同。
- **来源与依据**：GitHub Releases latest：<https://api.github.com/repos/abhigyanpatwari/GitNexus/releases/latest>。
- **破坏性变更与迁移**：没有跨版本区间；无需新增迁移或规则。
- **Agent harness 影响**：无版本变更，不修改规则、模板或安装行为。

## Playwright v1.61.1 -> v1.61.1

- **检测结果**：最新 stable release 仍为 `v1.61.1`，与基线相同。
- **来源与依据**：GitHub Releases latest：<https://api.github.com/repos/microsoft/playwright/releases/latest>。
- **破坏性变更与迁移**：没有跨版本区间；无需新增迁移或规则。
- **Agent harness 影响**：无版本变更，不修改规则、模板或安装行为。

## Maestro cli-2.7.0 -> cli-2.7.0

- **检测结果**：最新 stable release 仍为 `cli-2.7.0`，与基线相同。
- **来源与依据**：GitHub Releases latest：<https://api.github.com/repos/mobile-dev-inc/Maestro/releases/latest>。该 release body 仅链接上游 changelog；本次没有跨版本区间，因此不需要从该链接继续汇总版本差异。
- **破坏性变更与迁移**：没有跨版本区间；无需新增迁移或规则。
- **Agent harness 影响**：无版本变更，不修改规则、模板或安装行为。

## 本仓库文档维护判断

- **CHANGELOG.md**：已更新未发布章节；本次改变了 bundled Skill 的用户可见 Trellis 更新与安全边界。
- **README.md / README.html**：未修改。安装方式、Onboard 行为、工作流主线、工具职责、用户可见路径和验证栈均未改变；新增内容是 Trellis 升级后的专项运行时约束，保留在对应 Skill 避免把 README 扩展成上游变更日志。
- **版本化 automation prompt**：未修改。现有 prompt 已要求完整版本证据、release 概念扫描、最小规则修改与文档维护判断；本次没有出现新的自动化流程、扫描范围或验证契约。
- **Orca live automation**：未读取、未比较、未写入；本次不是用户显式 `sync` / `同步`。
