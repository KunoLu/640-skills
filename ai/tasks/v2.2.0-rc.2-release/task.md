---
schema_version: 1
id: v2.2.0-rc.2-release
workflow_mode: strict
mode_source: user
mode_note: 用户授权在任务 7 主线 CI 全绿后推进任务 8；可做本地发布准备，未授权公开发布。
status: "blocked"
branch: release/v2.2.0-rc.2
created_at: '2026-11-25T18:10:37.782164+08:00'
updated_at: "2026-11-25T18:10:58.634287+08:00"
completed_at: null
"blocked_reason": "当前 Astra 会话：本地双语候选草案完成；公开发布需单独授权，且 PRD 指定的 bilingual-release-notes 当前不可调用。"
---
# 任务 8：准备 rc.2 双语预发行与公开核验

任务 7 经 PR #229 合入，main `d8b2191204e368035fd69544aa74c6600961a2f6` 的 CI 45589961883 为 13/13。只清理任务 7 对应的开发分支，归档和私有证据保留。

## 发布前置与范围

上一公开标签 `v2.2.0-rc.1` 指向 `7f21401ae6c56acd5846ae6ae922111aba3af932`。只做候选准备；当前 main 不是对未来发布点的预先批准。按 `docs/release-notes-template.md`、历史 `v2.0.2` 和 `v2.2.0-rc.1` 的版式核对双语正文、双语 annotated tag 注解、旧项目升级与恢复说明。若 main 改变，必须更新发布身份并核对新提交的精确 CI。不得以任务分支的 CI 或旧 SHA 替代。

未完整调用 grill-with-docs：PRD §8–9 已规定产物与门禁。无代码、schema、部署配置修改，既有行为安全／数据设计／重构门不适用；发布准备检查适用，当前发布状态 blocked。单独授权且所需方法可用后才执行发布。发布后仍需验证远端 annotated tag、prerelease、比较范围、文档全树与升级／许可链接，最后交付审核复盘；不自动推广方法，不销毁历史备份。原会话 Astra，调用次数未知。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-25T18:10:48.099134+08:00 | planned | in-progress | 当前 Astra 会话：开始任务 8 的发布准备，检查主线、上一 tag、历史版式和方法可用性。 | 任务 7 本地与远程分支均已清理，git bundle 核验成功。未创建新标签或远端 Release。 |
| 2026-11-25T18:10:58.634287+08:00 | in-progress | blocked | 当前 Astra 会话：本地双语候选草案完成；公开发布需单独授权，且 PRD 指定的 bilingual-release-notes 当前不可调用。 | 仓内模板可读，GitHub 上 v2.0.2 与 rc.1 版式核对通过；skill:// 明确返回 Unknown skill，未安装或声称调用。候选正文、短双语注解仅存任务私有 reports。rc.2 尚无远端 tag 或 Release，比较链接尚不能当作发布后验证。未打标签、推送、创建远端草稿或发布。 |
