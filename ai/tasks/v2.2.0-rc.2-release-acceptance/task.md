---
schema_version: 1
id: v2.2.0-rc.2-release-acceptance
workflow_mode: strict
mode_source: user
mode_note: 用户要求主线 CI 全绿后继续原计划；执行 rc.2 PRD 任务 7，strict。
status: "blocked"
branch: test/v2.2.0-rc.2-release-acceptance
created_at: '2026-11-25T16:32:34.200219+08:00'
updated_at: "2026-11-25T16:57:12.752546+08:00"
completed_at: null
"blocked_reason": "当前 Astra 会话：固定 OMP 已就位，任务 7 独立域没有可用的 openai-codex 模型，等待本域官方账号认证。"
---
# 任务 7：统一回归与真实分发／安装许可验收

## 基线与范围

核验合入后源码 `479095dc21747ffa471898fe6a2ac92f233edcfe`。PR #228 对应 PR CI 45570440726、main CI 45573097426 均为 13/13，但不替代本轮实测。区分远端分发归档、单技能实际安装结果、隔离升级与回退、固定宿主行为及仓库测试。旧报告、模拟或源码检查不能单独把任何真实宿主项记为通过；无可验证证据记 unknown，已证实不支持才记 unsupported。

按 PRD 核对成功／审批拒绝／失败／中断、冲突、未知会话、重复导入／执行、旧配置保护；逐安装单元比对通知正文与适用范围，检查升级及失败回退。形成双语 breaking 指引、版本 pin 和缺陷清单。本轮不授权发布、标签、真实全局安装、Graft 现场清理或使用其他任务认证；归档须标明来源 SHA，不冒充尚不存在的 rc.2 release 制品。涉及登录、信任或不可证明的会话归属立即停止相应路径。

## 门禁

以任务 7 私有 TEMP、隔离 HOME 与受控合成仓库取证；原生 JSON／日志与同 stem 中文摘要存 ignored reports。未完整调用 grill-with-docs：任务 7 矩阵和阻断条件由 PRD 明确。当前为验证任务；如发现产品错误，保留原始失败，修复前按 strict 补对应方法。Astra 原会话，精确模型调用次数未知。未关闭发布门禁不得进入任务 8。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-25T16:32:46.160196+08:00 | planned | in-progress | 当前 Astra 会话：从任务 6 已通过主线 CI 的提交启动任务 7，先验分发及本地回归。 | 任务 6 本地及远端开发分支已清理，冻结提交和 CI 回执已保全；新隔离目录 640-skills-rc2-task7.niFnD51H。不复用历史成功报告或其他任务凭据。 |
| 2026-11-25T16:36:49.662161+08:00 | in-progress | blocked | 当前 Astra 会话：已完成本轮固定提交归档、隔离安装、升级回退与离线回归；新认证域尚不能执行固定宿主矩阵，停止宿主路径，不启动循环。 | GitHub 主线源码归档 479095dc 的 19 项安装／重装、23 个通知原字节、1512 项 Phosphor 通过；真实 upgrade plan 冲突 exit 2、裁决 plan/apply exit 0，批次失败恢复旧 inode 及通知。归档回归 156 通过 6 跳过；适配器和存储 70 通过。新 CODEX_HOME login status exit 1 Not logged in；PATH OMP=19.1.1 不能替代 19.1.0。见 reports/checkpoint.json 和同 stem 中文汇总。待任务 7 独立认证及精确宿主验收，未进入任务 8、未发布。 |
| 2026-11-25T16:57:02.442425+08:00 | blocked | in-progress | 当前 Astra 会话：用户要求续作，Codex 隔离浏览器登录完成，恢复固定宿主就绪检查。 | 任务 7 codex login 与 login status 均退出 0；未访问认证原件。 |
| 2026-11-25T16:57:12.752546+08:00 | in-progress | blocked | 当前 Astra 会话：固定 OMP 已就位，任务 7 独立域没有可用的 openai-codex 模型，等待本域官方账号认证。 | 官方 arm64 v19.1.0 制品大小、SHA-256 一致，--version 实测 omp/19.1.0；离线 models openai-codex --json --no-extensions 返回 0 个模型。见 reports/host-readiness.json 和同 stem 中文摘要。未发起登录、模型请求或循环。 |
