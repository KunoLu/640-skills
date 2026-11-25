---
schema_version: 1
id: v2.2.0-rc.2-glossary
workflow_mode: strict
mode_source: user
mode_note: 用户授权在任务 5 合入后按已确认的三文件范围推进任务 6；PRD §4 要求 strict。
status: "checking"
branch: docs/v2.2.0-rc.2-glossary
created_at: '2026-11-25T14:43:37.562879+08:00'
updated_at: "2026-11-25T14:49:16.662530+08:00"
completed_at: null
---
# 任务 6：自有入口术语表约定

基线为 PR #227 的 squash `4cc41d2fb0d9ebfea1a85c5be1eb18af9239e334`，主线 CI 45560137911 的 13 个作业均成功。任务 5 的本地、远程开发分支已删除，现场 Graft 条目和原有证据保留。

## 范围与验收

只改 `sbtd-workflow-onboard/templates/skills/` 下的 `sbtd-task/references/methods.md`、`book-ddd-distilled-modeling/SKILL.md` 和 `gherkin-bdd/SKILL.md`。保留项目显式术语约定；无约定时自有入口以项目根 `GLOSSARY.md` 为术语表。旧 `CONTEXT.md` 是可读取的证据，不自动迁移或覆盖；若需提取，先展示建议及差异，取得确认。第三方 Skill、已安装副本和真实项目文档不在范围内。

本地以三个入口独立读法验收默认、项目例外、旧上下文只读及冲突；保护已有字节，不用静态检查冒充真实宿主行为。仅改提示规则，无运行时、schema、依赖或分发变更。未完整调用 grill-with-docs：PRD 及任务 1 已明确文件、优先级和授权门。Astra 原会话，调用次数未知。范围变化或需要处理旧文档即停；任务循环到本地验收点关闭，冻结 SHA 后内审、外审、CI 分列。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-25T14:43:47.858621+08:00 | planned | in-progress | 当前 Astra 会话：任务 6 开工，先核实三个自有入口旧默认，随后修正规则并验证。 | 私有临时目录 640-skills-rc2-task6.5SsG2LIg；仓库根 GLOSSARY.md、CONTEXT.md 及 docs/CONTEXT.md 不存在，未创建。现行三个入口分别默认 docs/CONTEXT.md、向其推广或列其为词汇来源。 |
| 2026-11-25T14:49:16.662530+08:00 | in-progress | checking | 当前 Astra 原会话：三份自有规则本地验收完成；有界循环已关闭，冻结分支交内置复审。 | 三入口均优先尊重项目约定，否则使用根 GLOSSARY.md。旧 CONTEXT 仅作只读证据，先提取建议及差异，经明确确认才应用。三次无工具读者调用共 9/9 判断符合预期（不是宿主写保护），既有方法与 DDD 契约 2/2；夹具前后摘要不变，无既有文件迁移、无第三方或生效路径变更。见 reports/reader.json、contracts.log 及同 stem 中文汇总。未推送、未外审或发布。 |
