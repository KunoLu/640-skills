---
schema_version: 1
id: v2.2.0-rc.2-release-acceptance
workflow_mode: strict
mode_source: user
mode_note: 用户要求主线 CI 全绿后继续原计划；执行 rc.2 PRD 任务 7，strict。
status: "done"
branch: test/v2.2.0-rc.2-release-acceptance
created_at: '2026-11-25T16:32:34.200219+08:00'
updated_at: "2026-11-25T18:09:14.702098+08:00"
completed_at: "2026-11-25T18:09:14.702098+08:00"
"blocked_reason": null
---
# 任务 7：统一回归与真实分发／安装许可验收

## 基线与范围

核验合入后源码 `479095dc21747ffa471898fe6a2ac92f233edcfe`。PR #228 对应 PR CI 45570440726、main CI 45573097426 均为 13/13，但不替代本轮实测。区分远端分发归档、单技能实际安装结果、隔离升级与回退、固定宿主行为及仓库测试。旧报告、模拟或源码检查不能单独把任何真实宿主项记为通过；无可验证证据记 unknown，已证实不支持才记 unsupported。

按 PRD 核对成功／审批拒绝／失败／中断、冲突、未知会话、重复导入／执行、旧配置保护；逐安装单元比对通知正文与适用范围，检查升级及失败回退。形成双语 breaking 指引、版本 pin 和缺陷清单。本轮不授权发布、标签、真实全局安装、Graft 现场清理或使用其他任务认证；归档须标明来源 SHA，不冒充尚不存在的 rc.2 release 制品。涉及登录、信任或不可证明的会话归属立即停止相应路径。

## 门禁

以任务 7 私有 TEMP、隔离 HOME 与受控合成仓库取证；原生 JSON／日志与同 stem 中文摘要存 ignored reports。未完整调用 grill-with-docs：任务 7 矩阵和阻断条件由 PRD 明确。当前为验证任务；如发现产品错误，保留原始失败，修复前按 strict 补对应方法。Astra 原会话，精确模型调用次数未知。未关闭发布门禁不得进入任务 8。

## 本地验收与发布准备清单

| 项目 | 结果与证据边界 |
|---|---|
| Codex `0.171.0` | `app-server` 对合成命令拒绝、一次性批准；批准后读缺失文件的原生命令退出 1，再次请求仍需批准。`turn/interrupt` 获应答且终态为 `interrupted`。独立 `exec --json` 中 `/usr/bin/true`、`/usr/bin/false` 经生产适配器重放为成功／失败，退出码 0／1。拒绝和中断不从 exec 数据推断。 |
| OMP `19.1.0` | 独立持久化会话的 `read` 拒绝、成功、缺失三种结果分别重放为 `declined`、`succeeded`、`failed`。`agent_start` 后主动 `abort` 获应答与 `aborted`。这是回合中断，不证明中止了运行中的外部程序。 |
| 所有权与重复消费 | OMP 在本轮实际写入时持有租约，正常退出、确认释放后才读原件。另一合成 ID 返回 `unknown`，生产导入退出 2，未建观察库。Codex／OMP 首次分别接受 4／6 条；再次导入分别确认 4／6 条重复，零新增、冲突或拒收。宿主版本均命中 `acceptance_pins`。旧报告路径和仅有单测日志的输入均被本轮证据检查拒绝。 |
| 许可与安装 | 固定主线 SHA 的 GitHub 源码归档实装、重装 19 个外部技能，核对 23 份通知的范围和字节；Phosphor 1512 项。升级冲突先阻断，显式 replace／preserve 后核验结果；中途失败恢复旧 inode、字节及通知。不是已发布标签制品。 |
| 配置冲突与旧条目 | 在合成配置上验收计划后漂移拒写、无退役授权不动旧条目。未访问或清理真实宿主 Graft 接线。首轮 SEO 契约因归档无 Git 索引而出错；保留原始失败，仅在同 SHA 的隔离 Git 检出补跑该项，许可文件与归档字节一致，1/1 通过。 |

升级前参阅 [English breaking guide](../../../README.md#graft-retirement)／[中文不兼容说明](../../../README.zh.md#graft-retirement)。版本依据为 [capability-matrix.json](../../../sbtd-runtime/contracts/capability-matrix.json)。原生证据摘要在本任务私有 `reports/host-matrix.json`、`reports/distribution.json` 和同 stem 中文报告；不公开原始认证域或会话。没有在本轮隔离矩阵内确认需修改产品的缺陷；其他平台、本分支独审、精确提交 CI 和发布均不由本地结果证明。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-25T16:32:46.160196+08:00 | planned | in-progress | 当前 Astra 会话：从任务 6 已通过主线 CI 的提交启动任务 7，先验分发及本地回归。 | 任务 6 本地及远端开发分支已清理，冻结提交和 CI 回执已保全；新隔离目录 640-skills-rc2-task7.niFnD51H。不复用历史成功报告或其他任务凭据。 |
| 2026-11-25T16:36:49.662161+08:00 | in-progress | blocked | 当前 Astra 会话：已完成本轮固定提交归档、隔离安装、升级回退与离线回归；新认证域尚不能执行固定宿主矩阵，停止宿主路径，不启动循环。 | GitHub 主线源码归档 479095dc 的 19 项安装／重装、23 个通知原字节、1512 项 Phosphor 通过；真实 upgrade plan 冲突 exit 2、裁决 plan/apply exit 0，批次失败恢复旧 inode 及通知。归档回归 156 通过 6 跳过；适配器和存储 70 通过。新 CODEX_HOME login status exit 1 Not logged in；PATH OMP=19.1.1 不能替代 19.1.0。见 reports/checkpoint.json 和同 stem 中文汇总。待任务 7 独立认证及精确宿主验收，未进入任务 8、未发布。 |
| 2026-11-25T16:57:02.442425+08:00 | blocked | in-progress | 当前 Astra 会话：用户要求续作，Codex 隔离浏览器登录完成，恢复固定宿主就绪检查。 | 任务 7 codex login 与 login status 均退出 0；未访问认证原件。 |
| 2026-11-25T16:57:12.752546+08:00 | in-progress | blocked | 当前 Astra 会话：固定 OMP 已就位，任务 7 独立域没有可用的 openai-codex 模型，等待本域官方账号认证。 | 官方 arm64 v19.1.0 制品大小、SHA-256 一致，--version 实测 omp/19.1.0；离线 models openai-codex --json --no-extensions 返回 0 个模型。见 reports/host-readiness.json 和同 stem 中文摘要。未发起登录、模型请求或循环。 |
| 2026-11-25T17:02:43.260366+08:00 | blocked | in-progress | 当前 Astra 会话：任务 7 本域 OMP 官方登录已完成，恢复双宿主实测。 | 本域浏览器登录退出 0；固定 OMP 19.1.0 官方模型查询返回 10 项，含目标 Astra。固定 Codex 0.171.0，两个专用域哨兵互相拒读。本轮重新生成合成输入、事件及回执，不引用旧通过数。 |
| 2026-11-25T17:08:13.555239+08:00 | in-progress | checking | 当前 Astra 会话：任务 7 隔离验收达到本地暂停点，已关闭原终端循环，冻结提交交内审。 | 双端真实审批、失败、中断及生产重放已核对；unknown 负例 exit 2 不建库；合成配置保护、重复导入与已完成的归档实装证据分列。保留 SEO 首轮缺 Git 索引错误，仅该项在相同源码 Git 检出补跑通过。报告型命令使用原生 runner。未推送、未发布；内审、外审及精确 SHA CI 待验。 |
| 2026-11-25T18:09:14.702098+08:00 | checking | done | 当前 Astra 会话：PR #229 已 squash 合入，精确主线 CI 全绿，任务 7 隔离验收结案；不表示已发布。 | {"clean_sha": "674f90555f57b2e7677f2e865ab6b788293ddb52", "ci_run": "45586496681", "pr": 229, "main_sha": "d8b2191204e368035fd69544aa74c6600961a2f6", "main_ci_run": "45589961883", "pr_jobs_passed": 13, "main_jobs_passed": 13, "external": "user-reported CLEAN", "bundle": "reports/closeout-229/task7.bundle", "published": false} |
