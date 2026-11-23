---
schema_version: 1
id: v2.2.0-rc.2-license
workflow_mode: strict
mode_source: user
mode_note: rc.2 已确认 PRD；用户授权任务 2 开工
status: "checking"
branch: fix/v2.2.0-rc.2-license
created_at: '2026-11-23T18:31:11.495286+08:00'
updated_at: "2026-11-23T22:00:45.130163+08:00"
completed_at: null
"blocked_reason": null
---
# 任务 2：本项目许可修复

基线：main `0d67da81b0c111b7b45888dffaf6c5d211a59944`，任务 1 已合入；主线 CI 45154435281 成功 13/13。仅本任务。原生实现/内审采用用户确认的当前 OMP 19.1.1 / GPT-6.2 Astra 会话；次数未知，不重标历史。固定宿主验收仍为 19.1.0 / 0.171.0。TEMP 仅 `~/TEMP/640-skills-rc2-task2.I2KnjNlp/`，含 tmp、cache、isolated；不复用任务 1 私有环境，不复制凭据，确认不用后按清单清理。

## 目标与验收

查明本项目分发和安装的真实来源与消费路径。核验 Phosphor 元数据数量，整包和独立安装单元保留原版权和完整 MIT。保护 Matt / SEO 原有声明、稳定镜像和来源锁。对比 Google 等本项目固定官方来源、字节及许可；一致则不索内部历史，有真实差异或附加条款则提交用户裁决。以真实整包及单技能 install/reinstall/upgrade/conflict/failure rollback 正负验收，不以源码 NOTICE 代替。隔离过程使用本任务 TEMP；原生证据及同 stem 中文汇总归本任务 ignored reports。错误修改仅在本分支撤回，不删除上游数据或发布。

## Book Gate Plan

未完整调用 grill-with-docs：PRD 已明确；先以项目字节和实装查清事实。DDD 暂不触发。既有安装变化前 Legacy Safety、Refactoring、影响面与负测；改变持久化所有权或锁格式前评估 DDIA / 迁移，不预设要修改它们。项目已有 Markdown 场景/BDD、TDD、可读性复核及 project-validation；生产安装行为若变化则验证后执行 Release Readiness。本地验收或出现权限/安全阻断即在本终端关闭 /loop；同 SHA 内置 /review → 外部独审 → 同 SHA CI → 协调方合入。不能将许可修复扩大为升级或发布授权。

## 本地交付与验收检查点

- Impeccable 的 Apache 许可、NOTICE 和原作 MIT 分开交付。后者的适用范围来自 Impeccable 固定版 NOTICE；未猜测两份参考资料的派生 revision，未改 mirror、来源锁或已有 Matt／SEO 声明。
- Legacy Safety：characterized。真实旧安装缺通知；保留原有备份／恢复、明确 replace 和 preserve 契约。DDIA：confirmed。源码 pin 继续核对未修改的上游，安装与升级统一用附带适用许可的最终目录判断目标状态。Refactoring：proceed。新增共享通知清单，沿用原事务。
- 真实隔离验收：整包复制及重装、两份平台参考和 Phosphor／Matt 单独安装、重装、真实写入失败回退、阻断未裁决漂移、实际保留、替换、verify、恢复。失败负例退出 1 和 2，正向退出 0。结果和限制见 ignored `reports/resumed/delivery.json`、`delivery.md` 及 `native/`。
- 本地 unittest 两组运行 96、201 项，后者跳过 6 项；合计 291 通过、6 跳过。Ruff 与 ty 仍有基线诊断，比较无新增，未宣称零诊断。两次实现助手因 429 未交付，由本会话实施；主模型调用次数未知。
- README.md、README.zh.md、双语 CHANGELOG、REFERENCE.md 已同步安装目录变化。版本监控 automation prompt 不改：不增加监控对象、版本写回或授权路径。TEMP 和原始报告保留，未改全局环境。
- 原终端已确认 `Loop mode disabled.`。当前仅本地验收，待对本地提交内置审查；外部独审、同 SHA CI、合入、发布均不在本次执行范围。

## 正式只读目标恢复：本地验收

本轮仅使用新的 `isolated/restore-fix.z5rLXm0P/`。源与目标机械快照、备份私有性和目录范围在替换前校验；旧目标移开后才换入经校验的候选，不向正式旧目录增加权限。新回归覆盖换入失败还原、原件内容和根模式、持久化意图后的旧 absent 窗口续作。

最终本地 23 次 CLI 调用符合预期。真实 0555 连续安装、显式升级、verify (`aligned`)、恢复 (`complete`) 均通过；恢复的目录与备份机械摘要及 0755 模式相同。本地 Git clone 的两种技能均拒绝改名与等长字节漂移。200 个 stable 文件与父提交一致。八模块运行 335 项，325 通过、10 跳过；首轮旧故障注入接缝的失败保留。详细原生回执／中文报告见新隔离目录 `final-scenario.log`、`final-scenario.md`、`affected-final.log`。旧现场、旧 vault 均未改动。未推送、未跑远端 CI；当前内审和外审不得以测试代替。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-23T18:31:21.082745+08:00 | planned | in-progress | 当前 Astra 实现会话：开始 任务 2 许可盘点与本地实现验收 | {"changed_files": [], "evidence_files": [], "sync_files": {}, "validation": ""} |
| 2026-11-23T18:40:52.296780+08:00 | in-progress | blocked | 当前 Astra 会话：固定 Impeccable NOTICE 另指已分发的两份平台文档源于 ehmo/platform-design-skills（MIT）；需用户裁决本轮是否纳入该额外归属。已关闭本任务 /loop，停止实现。 | 固定 c1e0e5492fbb524f5df84d635ecfae7dc438ec45 的官方 NOTICE 与包内逐字一致，但只有作者、MIT 名称和仓库链接，无衍生来源 revision 或 MIT 全文。reference/ios.md、android.md 确实随包分发。不是 Google 或锁定字节不一致。已核对 Google 两数据文件和 UI LICENSE 字节，关闭该项，未索内部历史。Phosphor 1512 条目、官方 2.1.1 完整 MIT、整包 NOTICE 和回归已落盘；1 项 red 后 3 项定点 green。真实 bootstrap 和单技能安装为修复前基线，安装器尚未改，重装/升级/冲突/失败回退未验收。证据见 ignored reports 和本任务 TEMP。 |
| 2026-11-23T20:44:45.853096+08:00 | blocked | in-progress | 当前 Astra 会话：用户确认纳入 Impeccable 两份平台参考文档的 MIT 归属及整包和独立技能交付 | 固定 Impeccable 的 ios.md、android.md 与官方逐字相同；其 NOTICE 明示作者 ehmo。原作 LICENSE 的 baff03e456864470db3ba8acebc41a003cbfa541 版本为 MIT，原文 Copyright (c) 2026 未署作者；分别如实保留，不将此提交冒称实际派生 revision。不改来源锁。 |
| 2026-11-23T20:57:42.031644+08:00 | in-progress | checking | 当前 Astra 实现会话：完成任务2本地许可交付与隔离验收，关闭循环，交本地提交内置审核 | 真实 CLI 15 次调用含失败回退与显式冲突负例；安装/升级/恢复结果及边界见 reports/resumed/delivery.json、delivery.md；两组回归合计 291 通过、6 跳过。未推送或发布。 |
| 2026-11-23T21:03:26.960516+08:00 | checking | in-progress | 当前 Astra 会话：用户明确授权修复本地复审的两个 P2，随后仅本地验收和内置复审 | 37c3db4 存在 0555 来源暂存 EACCES 和显式 upstream 仅按路径选择补充许可的问题。沿用原分支、来源锁、隔离 TEMP；不推送。 |
| 2026-11-23T21:14:11.434748+08:00 | in-progress | blocked | 当前 Astra 实现会话：P2 真实隔离升级遇 foreign-content-conflict 与 retained_refs，停止实现，不删除或改权保全对象；已在本终端关闭 /loop。 | 未提交 P2 检查点。真实 0555 首次安装成功，来源与安装目录保持 0555；移动/替换文档和变更 NOTICE 的 CLI 定点回归均拒绝，3 个定点测试通过。真实 apply-preserve 在完整 Onboard 包资源返回 partial、mutated=true、exit 3；后续 verify/recover、真实 upstream clone 漂移场景尚未运行。并行影响回归 299 项有 1 失败、6 跳过，启动于 macOS 提交修正之前，不作最终证明。来源锁未改。见 ignored reports/p2；不推送。 |
| 2026-11-23T21:30:12.785676+08:00 | blocked | in-progress | 当前 Astra 会话：用户授权在新隔离目录修复只读清理和重装，保留原现场，不推送 | 新隔离目录 /Users/lusonglin/TEMP/640-skills-rc2-task2.I2KnjNlp/isolated/retained-fix.GInG4Ktd；旧目标、vault、retained_refs 一律不动；重新验证只读暂存清理、额外/变化内容保全及连续两次安装。 |
| 2026-11-23T21:41:18.038635+08:00 | in-progress | blocked | 当前 Astra 会话：私有暂存清理与只读重装通过，恢复正式 0555 目标触发新的 foreign-content-conflict，按用户边界停止，不改该目标或原现场权限。已关闭 /loop。 | 新现场 /Users/lusonglin/TEMP/640-skills-rc2-task2.I2KnjNlp/isolated/retained-fix.GInG4Ktd/delivery-4xfmoa9z。私有只读子目录无漂移时正常清理；额外/改写负例保留。两次真实 0555 安装均成功、mode=0555，等长漂移定点负例通过。apply-preserve、upgrade-apply、verify 成功且 aligned；recover-plan 成功，recover-apply 退出 3。现场 snapshot 与升级后值一致、backup_ref 摘要相符；失败非早前私有 stage 清理。先保存未提交检查点进行内审；真实 clone 后续场景、最终全影响回归未完成，未推送。 |
| 2026-11-23T21:46:37.130090+08:00 | blocked | in-progress | 当前 Astra 会话：用户采纳建议，在另一新隔离目录修复正式只读目标恢复，不放宽正式目标权限 | 仅使用 /Users/lusonglin/TEMP/640-skills-rc2-task2.I2KnjNlp/isolated/restore-fix.z5rLXm0P；保全既有所有现场。校验目标和备份后受保护替换，复跑本地验收及内置复审，不推送。 |
| 2026-11-23T22:00:45.130163+08:00 | in-progress | checking | 当前 Astra 会话：任务 2 正式只读目录恢复本地验收通过，关闭 /loop，冻结提交并内置复审 | 23 次 CLI 含正负例；回退原件内容及权限一致，335 项中 325 通过、10 跳过。来源锁不变，原现场未动；不推送。 |
