---
schema_version: 1
id: v2.2.0-rc.2-release
workflow_mode: strict
mode_source: user
mode_note: 用户授权在任务 7 主线 CI 全绿后推进任务 8；可做本地发布准备，未授权公开发布。
status: "checking"
branch: release/v2.2.0-rc.2
created_at: '2026-11-25T18:10:37.782164+08:00'
updated_at: "2026-11-25T18:34:28.655369+08:00"
completed_at: null
"blocked_reason": null
---
# 任务 8：准备 rc.2 双语预发行与公开核验

任务 7 经 PR #229 合入，main `d8b2191204e368035fd69544aa74c6600961a2f6` 的 CI 45589961883 为 13/13。只清理任务 7 对应的开发分支，归档和私有证据保留。

## 发布前置与范围

上一公开标签 `v2.2.0-rc.1` 指向 `7f21401ae6c56acd5846ae6ae922111aba3af932`。只做候选准备；当前 main 不是对未来发布点的预先批准。按 `docs/release-notes-template.md`、历史 `v2.0.2` 和 `v2.2.0-rc.1` 的版式核对双语正文、双语 annotated tag 注解、旧项目升级与恢复说明。若 main 改变，必须更新发布身份并核对新提交的精确 CI。不得以任务分支的 CI 或旧 SHA 替代。

本次按用户确认的仓内模板内审，不再等待独立安装 `bilingual-release-notes`。可审阅材料为[候选 Release 正文](candidate-notes.md)和[候选标签注解](candidate-tag.txt)，均为本地文本，不是已创建的 GitHub Release 或 Git 标签。正文和注解中的 SHA 是本次候选发布点，不是承载内审材料的分支提交。

未完整调用 grill-with-docs：PRD §8–9 已规定产物与门禁。无代码、schema、部署配置修改。本次仅推进内审；公开发布仍须单独确认目标 SHA，指定 RC 为 prerelease。标签和 Release 公开后，才验证远端注解、比较范围、文档全树与升级／许可链接并交付审核复盘；不自动推广方法或销毁备份。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-25T18:10:48.099134+08:00 | planned | in-progress | 当前 Astra 会话：开始任务 8 的发布准备，检查主线、上一 tag、历史版式和方法可用性。 | 任务 7 本地与远程分支均已清理，git bundle 核验成功。未创建新标签或远端 Release。 |
| 2026-11-25T18:10:58.634287+08:00 | in-progress | blocked | 当前 Astra 会话：本地双语候选草案完成；公开发布需单独授权，且 PRD 指定的 bilingual-release-notes 当前不可调用。 | 仓内模板可读，GitHub 上 v2.0.2 与 rc.1 版式核对通过；skill:// 明确返回 Unknown skill，未安装或声称调用。候选正文、短双语注解仅存任务私有 reports。rc.2 尚无远端 tag 或 Release，比较链接尚不能当作发布后验证。未打标签、推送、创建远端草稿或发布。 |
| 2026-11-25T18:33:04.985808+08:00 | blocked | in-progress | 当前 Astra 会话：用户明确同意以仓内模板作为任务 8 本次发布规范，恢复本地候选验证与内审。 | 只替代本仓本次 bilingual-release-notes 方法入口，不安装全局 Skill，不授权公开发布。候选正文和双语注解留在本地；发布须另行确认。 |
| 2026-11-25T18:34:28.655369+08:00 | in-progress | checking | 当前 Astra 会话：按获准仓内模板完成候选文本核对，冻结本地分支交内置审查。 | 候选主线 d8b2191204e368035fd69544aa74c6600961a2f6，CI 45589961883 为 13/13。正文双语各 4 项变更、14 项修复，核对双语 changelog、升级恢复锚点、前一标签及任务 7 原生计数。正文 SHA-256 3cc6e387e2dd2b39a4b11987941e2df91f08e3620cc45ea7eaee03740e81e56a；注解 3d145760826c5d95de1ab26f5e643e4fb8b1a127d0ccda5690e6171132ec5ff3。未访问真实宿主、未推送、未打标签或发布。 |
