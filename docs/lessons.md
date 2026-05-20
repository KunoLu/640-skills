# Lessons

## 每日版本检查不得推进 ENTRYPOINT 当前版本

- 问题：每日版本检查自动化在发现 Codex 新版本后，把 `ENTRYPOINT.md` 中的当前版本从 `v0.131.0` 自动更新到了 `v0.132.0`，且 `UPDATE.md` 使用了英文内容。
- 根因：automation prompt 没有明确区分“每日检查”和用户手动输入 `更新` / `update` 后的写回动作，也没有要求 `UPDATE.md` 必须使用中文。
- 修复：每日自动化只读取 `ENTRYPOINT.md` 当前版本作为固定比对起点，只用中文刷新 `UPDATE.md`，不得写回 `ENTRYPOINT.md`；只有用户手动输入 `更新` / `update` 时才允许更新版本号并归档。
- 预防：后续涉及自动化写入项目基线文件时，必须在 prompt 和 `AGENTS.md` 中同时明确“只读基线”和“手动确认写回”的边界。
