---
schema_version: 1
id: v2.2.0-rc.2-release
workflow_mode: strict
mode_source: user
mode_note: 用户要求任务 8 采用 strict；先准备及审查候选，后单独授权在已验证的主线提交发布 rc.2。
status: "checking"
branch: release/v2.2.0-rc.2
created_at: '2026-11-25T18:10:37.782164+08:00'
updated_at: "2026-11-25T22:20:57.173836+08:00"
completed_at: null
"blocked_reason": null
---
# 任务 8：准备 rc.2 双语预发行与公开核验

任务 7 经 PR #229 合入，main `d8b2191204e368035fd69544aa74c6600961a2f6` 的 CI 45589961883 为 13/13。只清理任务 7 对应的开发分支，归档和私有证据保留。

## 已发布制品与收尾范围

[v2.2.0-rc.2 预发行版](https://github.com/KunoLu/640-skills/releases/tag/v2.2.0-rc.2) 于 **2026-11-25 13:39:38 UTC** 发布。双语 annotated tag 对象 `613e0ba7cee07e17c71ee5906ecb1c3a6aca8eca` 指向主线 `d8b2191204e368035fd69544aa74c6600961a2f6`；[与 rc.1 的公开对比](https://github.com/KunoLu/640-skills/compare/v2.2.0-rc.1...v2.2.0-rc.2) 共 8 次提交。`rc.1` 解引用为 `7f21401ae6c56acd5846ae6ae922111aba3af932`。

用户授权使用[仓内模板](../../../docs/release-notes-template.md)。公开[正文](candidate-notes.md)及[标签注解](candidate-tag.txt)与受审提交 `7e0c78f2571db15e62446e3413f8eade1132f36f` 的字节一致。文案提交与产品发布点不同；本次日期回填不移动标签，也不重发制品。

[审核复盘](review-retrospective.md)区分发现、误报、返修回归与时间开销。是否推广双层审核由用户决定。未完整调用 grill-with-docs：PRD §8–9 与本次指示已经明确范围。本轮不合并 PR、不删除分支或私有证据；不能用发布成功替代任务收尾门禁。

## 发布后交付

见[文档全树核对](postrelease-audit.md)：日期回填、不可变归档的逐文件比对、仓内链接例外，以及 8 项现行文档与实现差异的分支订正分别记录。审核复盘已交付，未自动推广。#223–#229 已合入且相应分支已清理；任务 1 仍缺 `done` 状态事件。当前分支待收尾变更审查，PR #230 未合入；不能把已经公开的预发行版再算作本分支的合入。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-25T18:10:48.099134+08:00 | planned | in-progress | 当前 Astra 会话：开始任务 8 的发布准备，检查主线、上一 tag、历史版式和方法可用性。 | 任务 7 本地与远程分支均已清理，git bundle 核验成功。未创建新标签或远端 Release。 |
| 2026-11-25T18:10:58.634287+08:00 | in-progress | blocked | 当前 Astra 会话：本地双语候选草案完成；公开发布需单独授权，且 PRD 指定的 bilingual-release-notes 当前不可调用。 | 仓内模板可读，GitHub 上 v2.0.2 与 rc.1 版式核对通过；skill:// 明确返回 Unknown skill，未安装或声称调用。候选正文、短双语注解仅存任务私有 reports。rc.2 尚无远端 tag 或 Release，比较链接尚不能当作发布后验证。未打标签、推送、创建远端草稿或发布。 |
| 2026-11-25T18:33:04.985808+08:00 | blocked | in-progress | 当前 Astra 会话：用户明确同意以仓内模板作为任务 8 本次发布规范，恢复本地候选验证与内审。 | 只替代本仓本次 bilingual-release-notes 方法入口，不安装全局 Skill，不授权公开发布。候选正文和双语注解留在本地；发布须另行确认。 |
| 2026-11-25T18:34:28.655369+08:00 | in-progress | checking | 当前 Astra 会话：按获准仓内模板完成候选文本核对，冻结本地分支交内置审查。 | 候选主线 d8b2191204e368035fd69544aa74c6600961a2f6，CI 45589961883 为 13/13。正文双语各 4 项变更、14 项修复，核对双语 changelog、升级恢复锚点、前一标签及任务 7 原生计数。正文 SHA-256 3cc6e387e2dd2b39a4b11987941e2df91f08e3620cc45ea7eaee03740e81e56a；注解 3d145760826c5d95de1ab26f5e643e4fb8b1a127d0ccda5690e6171132ec5ff3。未访问真实宿主、未推送、未打标签或发布。 |
| 2026-11-25T20:48:58.683352+08:00 | checking | in-progress | 当前 Astra 会话：收到冻结提交的外部独审 CHANGES_REQUESTED，返修正文身份与双语术语说明。 | 5dbdafc4ef4022fdde16678034af10e79fcb9d5b：P2 已审原字节不宜原样发布；P3 中英文差异与旧文件保护说明不够对等。旧摘要保留为历史，注解不动。不涉及发布授权。 |
| 2026-11-25T20:49:54.150161+08:00 | in-progress | checking | 当前 Astra 会话：P2/P3 返修后冻结本地提交，交新 SHA 内审及外部复核。 | 发布原文以同目录受版本控制的 candidate-notes.md 为准，SHA-256 a2c9da530386eba784bc7927055b482df0e854c92559d6463f1b09815ec824ec；candidate-tag.txt 保持 3d145760826c5d95de1ab26f5e643e4fb8b1a127d0ccda5690e6171132ec5ff3。模板身份行及目标 SHA 不需发布时改写；两种语言均写明展示精确差异、明确批准、不自动迁移或覆盖。双语 4/14，其他原文字节与先前审阅范围一致。此前事件及 reports 中的旧稿仅作历史证据。未推送、未打标签、未发布。 |
| 2026-11-25T21:45:04.014818+08:00 | checking | in-progress | 当前 Astra 会话：rc.2 已按授权公开并核验，开始双语日期、文档全树核对和内外审复盘。 | 发布点 d8b2191204e368035fd69544aa74c6600961a2f6，标签对象 613e0ba7cee07e17c71ee5906ecb1c3a6aca8eca，2026-11-25T13:39:38Z 发布；公开正文和注解等于受审提交 7e0c78f 原件，PR #230 保持打开。不移动 tag、不改 Release、不合并或删除分支。 |
| 2026-11-25T22:08:01.044191+08:00 | in-progress | checking | 当前 Astra 会话：完成双语日期、发布文档全树核对及审核方式复盘，收尾文档冻结交内审；不修改已发布制品。 | 日期独立提交 d7f0923。公开归档 830/830 Git 文件一致，361 份可解析文档共 1476 个引用，仓内目标 974 通过、3 个历史私有例外，另 499 未按文件爬取。8 项语义差异在工作分支订正，5 个定向契约通过。见同目录 postrelease-audit.md、review-retrospective.md 和本地 reports。任务 1 仍 checking；任务 8 未标 done，未更新远端 PR 或全局规则。 |
| 2026-11-25T22:18:58.685657+08:00 | checking | in-progress | 当前 Astra 会话：用户授权修复 c80d2d1 整分支内审指出的两项预览说明 P2。 | project-only 包装器确认前不展示本地 Graft 明细；reset 预览在跳过接线时没有 graftWiring。只修读者指引，不改安装器或已公开制品。 |
| 2026-11-25T22:20:57.173836+08:00 | in-progress | checking | 当前 Astra 会话：两项 P2 预览说明已修正，冻结本地文档提交复审。 | 真实 Bash project-only dry-run 只列范围摘要；Python 缺 --yes 拒绝，合成项目无写入。Claude/Kimi 及全局 Codex/OMP --no-mcp 的 reset plan 均省略 graftWiring；另 3 项定向测试通过，覆盖 planned 目标及不可用／阻断。见 reports/preview-fix/verify.log 和 verify.md。仅更新两份指引及任务文档，不改安装器、已发布标签或 Release。 |
