---
schema_version: 1
id: v2.1.0-rc.2-adr0003-disk-cap
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict；主会话唯一 writer／验证 controller；仅指定 worktree，恰好三个本地 commit；不 push／PR／评论／merge／rebase，不改全局配置或其他 checkout；仅显式 git add，排除 .omp-r12b-addendum.txt 与 ai/tasks/codex-verify/。
status: done
branch: docs/v2.1.0-rc.2-item4-adr0003-disk-cap
created_at: '2026-10-22T17:47:41+08:00'
updated_at: '2026-10-22T18:10:32+08:00'
completed_at: '2026-10-22T18:10:32+08:00'
---

# rc.2 计划第 4 项：ADR 0003 §4／§5 磁盘上限

## 用户决定与任务身份

用户明确 strict、唯一 writer 与三个本地提交。工作根 `/workspace/640-skills-item4-adr`；入口 HEAD／origin/main 均为 `b73ebe501cb529d11e6829b02a363fd7f4f4274a`（#156）。未完整调用 grill-with-docs：已批准的 PRD §10.4、plan 决定与本次交付边界明确，不重开需求。

## 范围与验收

1. 仅 plan 与 PRD task 回填 #156、完整 SHA、mergedAt／committer 时间及主会话最终 26／57，保留历史状态事件。
2. 仅 ADR 0003 §4／§5 正文定义清扫与共享配额配置；不改标题、§1–§3，不加 revision log，不改代码、契约、golden tests、PRD、其他 ADR 或安装文档。
3. 本任务文件随第三个 commit 提交；task index 按 rc.2 惯例不改。记录真实命令与模型证据；local done 不代表 push、PR、合并、实现或发布。

## 待定项／决策

- **请 Reviewy／用户重点复核环境变量名：** `SBTD_RUNTIME_DISK_QUOTA_BYTES`。沿用 `SBTD_RUNTIME_HOME` 的 runtime 家族，显式标注 bytes；仅作用于 snapshots/ + exports/，不是全 HOME 限额。
- **请 Reviewy／用户重点复核默认字节值：** 2,000,000,000（十进制 2 GB），不是 2,147,483,648（2 GiB）；不暗改 PRD 单位。容量实测校准归 R2.2。
- **请 Reviewy／用户重点复核非法值策略：** serve 启动读取一次；未设置使用默认值，设置后只接受 ASCII 十进制正整数，允许前导零；空／空白／带单位／符号／小数／指数／零／负数／不可精确表示值拒绝启动，不隐藏拼写错误，不回显原值。
- **请 Reviewy／用户重点复核清扫顺序与边界：** 保护在途与恢复引用 → 过期无引用 ready 导出对 → 过期未 pin 快照 → 确认残留 temp → 重新计量 → 80% 预警／超限拒绝 → 新建。扁平目录直接普通文件按 st_size 累加，manifest、坏／未知／孤立产物及在途 temp 都计入；不跟随链接、不递归意外目录。
- 准入按清扫后的现有占用，不预留未知产物大小；恰等上限不属“仍超限”，允许新建，可能瞬时越限，不回删未过期数据。此取舍需 Reviewy／用户注意，不能宣传为文件系统硬限额。
- §2 原有遗留 temp 保留规则由 §4 明确、局部取代；其余 §1–§3 原文保留。错误码字符串／HTTP 状态／body 仍由尚未开始的独立 contract PR 定义，本轮未发明；实现与安全／容量验证归 R2.2。

## Book Gate Plan

| Gate | 客观触发／阶段 | 状态 |
|---|---|---|
| book-ddia-data-design | 持久化数据清扫／恢复设计，稳定设计前 | confirmed；已加载并输出独立 DDIA Data Design Review：两 store 各自所有权，共享计量；单 writer 串行化清扫／在途登记／准入，坏文件保留，无格式迁移；R2.2 补边界与恢复验证。 |
| book-ddd-distilled-modeling | 完整 grill／领域歧义 | not-needed；未完整 grill，沿用已批准的 Snapshot／Export 归属。 |
| book-legacy-change-safety／book-refactoring-pass | 既有行为／生产代码编辑 | not-needed；文档设计，不改运行行为或代码。 |
| book-release-readiness | runtime／部署／发布变化 | not-needed；本轮无实现、部署或发布。 |
| TDD／gherkin-bdd／ponytail／代码可读性 | 行为实现／手写代码 | not-needed；无代码或场景实现，不新增措辞钉测。 |
| 独立 review | 清理授权边界 | correct；DecisionReview 无发现；SweepSafety 一项 P3（80% 预警渠道归属）已补明归 R2.2，原 reviewer 只读复核 CLOSED，无剩余发现。两 reviewer 仅只读，主会话唯一 writer。 |
| project-validation | 文档 check | 已加载；使用范围检查与 Markdown／YAML 消费者 smoke，不运行 formatter 或全套测试。 |

## 验证证据

- 已读指定 plan、PRD task、ADR、PRD §10.1／§10.4，及 `git show 9fc31f8`、`git show b73ebe5` 的完整原生 diff。`git diff-tree --no-commit-id --name-only -r b73ebe5` 列出四个文件，无 task index，沿用其不改 index 惯例。
- `git show -s --format=%cI b73ebe5` 实际输出 `2026-10-22T17:42:54+08:00`。#156 mergedAt 与 PRD 会话最终 26／57 采用 operator 已核实事实，不请求 GitHub API、不重跑该历史会话。
- 只读源代码：`report_snapshot.py` 的 `.snapshot-*.tmp`、`snap_<id>.json`、校验／pins／sweep；`export_store.py` 的 `.export-*.tmp`、`exp_<id>.bin` + `.json`、ready 发布／恢复／成对删除。没有 per-export 子目录；现有实现没有本次新设计的统一配额或在途 temp 清扫登记，ADR 明确为 R2.2 待实现规则。
- 已执行 `git grep -ohE 'SBTD_[A-Z0-9_]+' | sort | uniq -c | sort -rn`：入口 `SBTD_RUNTIME_HOME` 51 次、`SBTD_RENDERER_TEST_HOME` 13 次，输出无既有配额变量。采用 runtime 家族与显式字节单位。
- Python 3.13.5、`MarkdownIt('commonmark').enable('table')` 实际解析／渲染 ADR，两个章节、清扫有序列表、删除集合与配置 code span 可消费；两任务 YAML 用 `yaml.safe_load` 解析，非空时间用 `datetime.fromisoformat` 校验 +08:00。PRD task 原历史事件行逐字不变、仅追加 closeout；合并时间字段正确。未落盘临时脚本。
- 已读 `.github/workflows/validation.yml` 的 Linux／Dashboard 验证入口及 `tests/run_ci.py` 平台选择；本轮只作文档消费者 smoke 与授权范围诊断，不把 runtime 测试当作未实现配额的证明。未运行 formatter、全套测试、代码 lint、单元、API、浏览器或跨平台验证；用户禁止 formatter／全套测试，其他项与纯文档 diff 无关。
- 前两个 commit 后实际执行 `git diff --stat origin/main..HEAD`：

  ```text
   ai/tasks/v2.1.0-rc.2-plan/plan.md                  |  4 +--
   ai/tasks/v2.1.0-rc.2-prd-disk-cap/task.md          | 17 +++++++------
   .../0003-v2.1.0-rc.2-r2.0c-snapshot-persistence.md | 29 +++++++++++++++++++---
   3 files changed, 37 insertions(+), 13 deletions(-)
  ```

  最终预期只增加本记录，共四条路径：`ai/tasks/v2.1.0-rc.2-plan/plan.md`、`ai/tasks/v2.1.0-rc.2-prd-disk-cap/task.md`、`docs/adr/0003-v2.1.0-rc.2-r2.0c-snapshot-persistence.md`、`ai/tasks/v2.1.0-rc.2-adr0003-disk-cap/task.md`。
- 同次实际执行 `git diff origin/main..HEAD -- sbtd-runtime/ docs/prd/ 'docs/adr/0001*' 'docs/adr/0002*' 'docs/adr/0004*'`：输出为空；`git diff --check`：退出 0、无输出。前两个 commit 的 `git diff --cached --check` 也均退出 0。
- `git diff --unified=0 origin/main..HEAD -- docs/adr/0003-v2.1.0-rc.2-r2.0c-snapshot-persistence.md` 的 hunk 起点实际为 `@@ -35 +35,20 @@`、`@@ -39 +58,5 @@`、`@@ -41 +64 @@`，均在 §4 标题（原第 33 行）之后；Python 比较 §4 前缀逐字相同，header／§1–§3 未变。最终 ADR 渲染 smoke 再次通过。
- 独立只读复核：DecisionReview 另行解析 PRD 旧 session，确认最终 26／57、astra high、无 fallback／子代理；SweepSafety 对照真实源文件与既有测试内容（未执行测试），确认删除／计量边界。唯一 P3 只追加预警渠道归 R2.2 的一句说明，原 reviewer 复核已关闭；不宣称外部 Reviewy 已 CLEAN。
- 第三个 commit 暂存本记录后，实际执行 `git grep -n 'SBTD_RUNTIME_DISK_QUOTA_BYTES'` 与 `git grep -nE 'SBTD_[A-Z_]*(QUOTA|CAP|LIMIT|DISK)[A-Z_]*'`，两者输出相同的两处定义／决定：本 task 第 28 行与 ADR §5 第 58 行，名称均为 `SBTD_RUNTIME_DISK_QUOTA_BYTES`，无竞争变体名；后续本证据行引用同名，不引入别名。`git diff --check` 与 `git diff --cached --check` 均退出 0、无输出。
- 最终记录的 Markdown 消费者 smoke：解析出 Book Gate／模型使用／状态事件三个表，表头列数分别 3／8／5；`git diff --cached --name-only origin/main` 与上述四条允许路径集合完全相等（PASS）。最终提交后原生 log／show --stat／status 输出由本会话交付，不把第三个 commit 的自身 SHA 写进本文件。

本地文档诊断不是正式测试报告或 CI。`BDD: skipped`（未改场景／代码，R2.2 实现时补行为验证），`Cross-repo context: not-needed`，`API Contract: not-needed`（独立 PR），`Mock Strategy: none`，`rtk: not-needed`（用户指定原生 Git 命令与直接 Python 文档消费），`Evidence Source: developer-local`，`Evidence Publication: local-only`；`Final Test Report`／`Run Summary MD: not-needed`，不声称 runtime、部署或发布就绪。

## 提交与恢复边界

授权路径已逐级核对 containment、无 symlink；三个既有文件 tracked，新 task 不受 ignore，入口工作区干净。沿用 PRD task 已记录的 TaskStore catalog/frontmatter 限制，不重跑已知失败；helper active／index 写入超出授权。使用自身 edit/write 保存用户指定记录，不声称 TaskStore lifecycle 或自动恢复成功；不改 active、ignore、身份或模型配置。旧 PRD task 的 branch 仅作为已完成历史任务保留，不重绑定。

1. `650c3363275a9bec727d5d090de7411bd4cb5bc6` — `docs(plan): backfill rc.2 item 4 PRD (#156 / b73ebe5) and close task record`，仅 plan 与 PRD task。
2. `ec020b823a6c3b2ad850a89393c0ccd42668bb4a` — `docs(adr): ADR 0003 §4/§5 disk-cap sweep scope and quota env var (rc.2 item 4)`，仅 ADR 0003 §4／§5。
3. `docs(task): record rc.2 item 4 ADR 0003 §4/§5 disk-cap task`，仅本记录，自身 SHA 由最终 stdout 提供，避免自引用。

local done 仅指三个本地文档提交完成；push／PR 由 operator 负责，ADR 尚未合并、contract 尚未开始、配额尚未实现。撤回仅涉及本分支文档提交，无运行时或数据迁移，不删除用户数据，不操作其他 worktree 或远端。未知数据持续占用、意外子目录不计量、准入后的瞬时越限以及跨平台链接／ACL 验证均是已披露边界，不承诺恢复工具或发布就绪。

## 模型使用

| agent/session | provider/model | thinkingLevel（thinking_level_change） | assistant messages / toolCall blocks | purpose | resolvedModelIsFallback | title-generation count | job-widget entries（type model_usage / purpose） |
|---|---|---|---|---|---|---|---|
| operator astra ping／01a16301-06a6-7473-b9c8-562f8f7fe65c | openai-codex/gpt-6-astra | high | 1 / 0 | `--no-tools` 连通性 | false | 0（对应日志无 request） | 未记录 / unknown |
| 主会话／01a16302-335f-70f4-a8b8-ad60413b8059 | openai-codex/gpt-6-astra | high | 25 / 52（截至提交前 snapshot） | 唯一 writer、验证 controller | false | 未记录 / unknown（日志内部 ID 与 session ID 不同，未强行归属） | 未记录 / unknown |
| DecisionReview／DecisionReview.jsonl | kimi-code/k3 | max | 14 / 20 | 只读历史回填／配置一致性复核 | false | 2 requests：cursor/composer-2.5 ×1、kimi-code/k3-256k ×1 | 未记录 / unknown |
| SweepSafety／SweepSafety.jsonl | kimi-code/k3 | max | 28 / 31 | 只读清扫安全复核，含 P3 修正复查 | false | 2 requests：cursor/composer-2.5 ×1、kimi-code/k3-256k ×1 | 未记录 / unknown |

只读 Python `json.loads` 统计时间 **2026-10-22T18:08:58+08:00**（`TZ=Asia/Shanghai date -Is`）：session 根 `~/.omp/agent/sessions/--workspace-640-skills-item4-adr--/`。ping 为 `2026-10-22T09-46-14-054Z_01a16301-06a6-7473-b9c8-562f8f7fe65c.jsonl` 第 1–9 行；排除 ping 后最新主文件为 `2026-10-22T09-47-31-039Z_01a16302-335f-70f4-a8b8-ad60413b8059.jsonl` 第 1–138 行。两个子代理位于该主文件同 stem 目录，DecisionReview 第 1–63 行、SweepSafety 第 1–100 行。统计 `type=message` 且 `role=assistant` 与其 `type=toolCall` blocks；主会话是截至提交前快照，不含随后记录回填、提交及最终输出，最终计数由 operator 报告。

模型与 fallback 来自 message／model_change，thinking 明确取 `thinking_level_change`（不是按请求 effort 推断）；两 reviewer 的 session_init 也记录 `kimi-code/k3:max`。上述 session 元数据及 custom entries 未见 `type=model_usage`／purpose job-widget 记录，故填 unknown，不编造计数。未修改模型配置；子代理实际用 kimi，不冒充 astra。

标题请求来自 `~/.omp/logs/omp.2026-10-22.452412.log`：DecisionReview 第 22／31 行、SweepSafety 第 18／27 行，各两次；这是 request 次数，不等于成功标题数或 reviewer 主模型 fallback。该日志第 9／13 行另有 cursor/composer-2.5 请求，但内部 sessionId 为 `01a16302-5de7-76bf-9d2c-a1882656144b`，与主 JSONL 不同，主表保守记 unknown。ping 对应 `omp.2026-10-22.451611.log` 的 Session exit recorded 绑定同一 ping JSONL，文件内无 title-generator request。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-22T17:47:41+08:00 | planned | in-progress | 用户指定 strict 与三个本地 commit；入口身份已核对 | 指定分支；HEAD／origin/main b73ebe501cb529d11e6829b02a363fd7f4f4274a；status 为空；授权路径安全 |
| 2026-10-22T18:03:10+08:00 | in-progress | checking | 回填已提交，ADR 设计与文档 smoke 已完成，进入独立清扫复核与最终记录 | 首 commit 650c3363275a9bec727d5d090de7411bd4cb5bc6；DecisionReview 无发现；Markdown／YAML smoke 通过 |
| 2026-10-22T18:10:32+08:00 | checking | done | 本地文档交付收口；前两次提交完成，第三次只提交本记录；两位独立复核无未关闭发现，不等同外部 Reviewy／合并／实现 | ec020b823a6c3b2ad850a89393c0ccd42668bb4a；范围与 whitespace 检查通过；ADR／任务 Markdown 与 YAML smoke 通过；主会话提交前 snapshot 25／52，最终计数由 operator 报告 |
