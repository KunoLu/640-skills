# Lessons

## 每日版本检查不得推进 ENTRYPOINT 当前版本

- 问题：每日版本检查自动化在发现 Codex 新版本后，把 `ENTRYPOINT.md` 中的当前版本从 `v0.131.0` 自动更新到了 `v0.132.0`，且 `UPDATE.md` 使用了英文内容。
- 根因：automation prompt 没有明确区分“每日检查”和用户手动输入 `更新` / `update` 后的写回动作，也没有要求 `UPDATE.md` 必须使用中文。
- 修复：每日自动化只读取 `ENTRYPOINT.md` 当前版本作为固定比对起点，只用中文刷新 `UPDATE.md`，不得写回 `ENTRYPOINT.md`；只有用户手动输入 `更新` / `update` 时才允许更新版本号并归档。
- 预防：后续涉及自动化写入项目基线文件时，必须在 prompt 和 `AGENTS.md` 中同时明确“只读基线”和“手动确认写回”的边界。

## 配置摘录仓库不得按真实业务项目判断

- 问题：维护 Codex 配置摘录时，容易把仓库内的 `AGENTS.md`、`skills/`、`ENTRYPOINT.md` 当成真实业务项目结构来解释，从而引入“当前仓库直接生效”“当前仓库事实源”等误导措辞。
- 根因：配置摘录仓库同时保存全局规则、项目级规则模板和 Skill 镜像，外观类似项目根目录，但其目标是为后续同步和复用配置，不代表正在开发的业务仓库。
- 修复：将相关文档改为“配置文件与 Skill 的摘录/同步源”，把 agentmemory 的事实源表述为“当前工作项目文件、工具输出和验证结果”。
- 预防：后续修改本仓库时，先区分“配置摘录源”和“真实工作项目”；不要因为缺少 `.trellis/`、`.gitnexus/` 等目录就改写模板规则的适用边界。

## 项目级 AGENTS 模板不得镜像配置仓库根 AGENTS

- 问题：`agents/AGENTS.project.md` 被错误改成了与本配置仓库根 `AGENTS.md` 基本相同的内容，丢失了它作为真实项目仓库根目录 `AGENTS.md` 模板的角色。
- 根因：没有区分三类文件：`agents/AGENTS.global.md` 是 Codex 全局规则模板，`agents/AGENTS.project.md` 是真实项目级规则模板，本仓库根 `AGENTS.md` 只是配置摘录仓库自身规则。
- 修复：重新将 `agents/AGENTS.project.md` 调整为真实项目级模板，承接全局规则并补充项目事实源、agentmemory、Trellis、GitNexus、Graphify、Channel、验证和 Lessons 的项目级约束。
- 预防：后续同步规则时，不能把本仓库根 `AGENTS.md` 复制到 `agents/AGENTS.project.md`；两者加载位置、适用对象和内容职责不同。

## 本地配置同步必须显式触发

- 问题：本地同步规则曾写成全局规则或全局 Skill 发生修改后“还应同步到本地 PC”，容易导致普通编辑任务立即覆盖实际生效的本地 Codex 配置。
- 根因：没有区分“维护仓库源文件”和“落地到本地实际路径”两个动作，触发语义不够明确。
- 修复：将同步逻辑改为只有用户主动输入 `同步` 或 `sync` 时才执行；普通修改任务只更新仓库源文件。
- 预防：后续新增同步目标或同步规则时，必须明确触发词、同步范围、校验方式，并保持项目级模板 `agents/AGENTS.project.md` 不自动同步。
