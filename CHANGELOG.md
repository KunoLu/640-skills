# CHANGELOG

本文件按 Git tag 记录用户可见变更，最新版本位于最上方。未发布章节在创建对应 tag 后补充发布日期。

## v1.0.2（未发布）

### 许可

- 新增根目录 `LICENSE`，仓库整体采用 Apache License 2.0。
- README 源文件表同步标注许可证入口。

## v1.0.1（2026-07-18）

### 修复

- 删除仓库根目录下指向不存在 `.agents/skills/sbtd-workflow-onboard` 的 `.claude/skills/sbtd-workflow-onboard` broken symlink，避免 Claude Code 误判项目级 Skill 来源。
- 保持根 `sbtd-workflow-onboard/` 为唯一公开 discovery entrypoint，不再提交由本地 Agent 安装器生成的项目级 alias。

### 文档

- README 同时提供默认分支最新内容和指定 Git tag 两种安装命令。
- 明确 `skills@latest` 固定的是 npm 上的 Skills CLI 版本通道；未带 `#ref` 的仓库 URL 安装默认分支 `main` 的最新 commit，而不是最新 tag。
- 明确正式 tag 保持不可变，修复通过新的 patch tag 发布。
- 新增根 `CHANGELOG.md`，从 `v1.0.0` 起按 tag、中文、倒序维护发布记录。

### 验证

- 增加仓库契约检查，禁止重新提交 `.claude` 项目级 Skill alias。
- 增加 README 最新版本 / 指定 tag 安装示例和 CHANGELOG 顺序检查。

## v1.0.0（2026-07-18）

### 新增

- 将 Onboard 能力收敛为根目录自包含 `sbtd-workflow-onboard` Skill，提供唯一 `SKILL.md` discovery entrypoint。
- 新增机器可读 `catalog.json`、Draft 2020-12 Schema、bundled Skill 模板和带来源校验的 external Skill stable fallback。
- 支持一个或多个项目路径的 `plan`、`init`、`reset` 和 project-only `init-projects` 流程。
- 支持通过官方 `npx skills add --global` bootstrap Onboard Skill，再由 Agent 执行完整初始化或重置。
- 纳入 Knowledge Base P1.1、Playwright / Maestro 验证契约、分层 lessons 和 SEO/GEO 等可选专项 Skill。

### 变更

- 仓库由旧 `kuno-workflow-onboard-skills` 布局迁移到 `sbtd-workflow-onboard`，canonical Skill 安装成功后按身份校验删除 legacy Onboard 目录。
- external Skill canonical 名称迁移为 `to-spec` / `to-tickets`，旧 `to-prd` / `to-issues` 仅作为迁移输入并在成功安装后删除。
- 根 `AGENTS.md` 和 `ENTRYPOINT.md` 保持 Git 追踪，分别作为仓库规则和版本监控的可恢复基线。
- 普通仓库维护、显式 `sync` 和手动 `update` 职责分离；只有 `sync` 按差异发布版本化 prompt 到 Orca live automation。
- 扩展 README 的全局安装、多项目、project-only、回滚、安全边界和响应式 HTML 说明。
- 将 Knowledge Base 集成方案移动到 `docs/prd/`，并归档 Codex `v0.144.5` 更新报告。

### 验证

- 增加 catalog、安装事务、legacy migration、多项目初始化、Agent CLI、Knowledge Base 和仓库工作流契约测试。
- 发布前全量 Python 测试共 88 项通过，并完成 README HTML 桌面端和移动端 Chromium smoke 验证。
