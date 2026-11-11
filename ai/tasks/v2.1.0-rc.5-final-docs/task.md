---
schema_version: 1
id: v2.1.0-rc.5-final-docs
workflow_mode: strict
mode_source: user
mode_note: 用户 2026-11-11 15:10 群内确认（rc.5 全程用 strict），Lord 记录。
status: checking
branch: docs/rc5-final-docs
created_at: '2026-11-12T01:12:16+08:00'
updated_at: '2026-11-12T01:28:57+08:00'
completed_at: null
---

# rc.5 最终文档清理

## 目标与本轮边界

本 PR 做 rc.5 最终文档清理：把过时状态句改成与已合入实现一致，保留原方案和历史事实。

第 1 轮只建立本 task.md，以及正式生成器更新的 `ai/tasks/index.md`。生产文档正文和双语 CHANGELOG 实现条目留待后续轮次；本轮不实现、不提交、不推送、不开 PR、不发出上游 issue，不运行 Git 写命令。提交由编排方稍后处理。不建立 active、handoff、developer 或其他工作流记录。保持 checking，completed_at 为 null。

第 2 轮执行下列既有 8 项计划；下文第 1 轮的“本轮不实现”“后续预期”“尚未执行”保留为历史，不代表第 2 轮结果。第 2 轮当前证据见「第 2 轮本地验证」。本轮不提交、不推送、不开 PR、不发布、不发出上游 issue；status 保持 checking，completed_at 保持 null。

未完整调用 grill-with-docs：边界明确，当前文档与合入记录能回答本轮问题，不新增领域决定。

## 决策来源

- 用户 2026-11-11 15:10 群内确认（rc.5 全程用 strict），Lord 记录。
- 用户 2026-11-11 15:08 群内确认（graft 甲：保持 pin 0.28.0，graft 仍为可选；graft 文档放最终文档 PR，不放当时那一项），Lord 记录。
- 用户 2026-11-11 23:59 群内授权：需要拍板的选择交由群成员投票，按推荐最多的选项执行；授权有效至 rc.5 发布。Lord 记录。
- Lord 将 #214 squash 合入 main，合并提交 `7f20fbcce29c8d982d51aaaaa9ac19fcda3cf5a2`，提交时间 `2026-11-12T01:06:47+08:00`，并删除远端开发分支。提交时间不是群内确认时间。
- 上述合入之后，Lord 于 2026-11-12 01:07（北京时间）群内调度：先清掉本地 #214 分支，然后照常开始最终文档 PR，先写 task.md；本 PR 多补一句“rc.3 #197 已去掉 v1.0.15 本地补丁”。这是 Lord 群内调度，采纳 Reviewy 的建议；未提供精确到秒的调度时刻。本会话未执行或核验本地分支清理。
- Reviewy 审查 #214 @ `3fbc37c3ac2900c6fa653e2ec795364b263fb0a8` 给出 CLEAN，并建议最终文档补记上述事实。四项 impeccable 旧问题在新上游副本再现，风险低、不卡 #214。Reviewy 提请投票：甲为保持上游原样、向上游提 issue、以后重新锁版本时自然带上修复；乙为另开 PR 重打 v1.0.15 本地补丁。Reviewy 投甲，Lord 合入时投甲，OMP 于 2026-11-12 01:07 投甲，随后 Researchy、CodeX 亦投甲。
- 按 640 2026-11-11 23:59 授权的群内投票结果：甲 5 票同意、0 票反对，投票人为 Reviewy、Researchy、CodeX、Lord、OMP；OMP 于 2026-11-12 01:07 投票，Lord 于 2026-11-12 01:07 记录结果，均为北京时间且未提供秒数。执行口径：impeccable 保持上游原样副本，不重新打 v1.0.15 本地补丁。给 `pbakaus/impeccable` 提 issue 记入本 task，但本 PR 不负责发出，由谁发出尚未确定；草稿，未发出；发不发等 640 确认。

群内事实、评审结论和远端操作采用本轮提供的已核实背景，不冒充本会话访问群聊或 GitHub 得到的证据。下面的文件行号与本地 Git 事实均为本轮亲自读取。

## 范围与非目标

范围：下表 1–8 项的文档措辞清理；在既有唯一 rc.5 未发布标题下各追加一条对应的中英文 CHANGELOG 条目；上游 issue 草稿仅存在于本 task。

非目标：契约／schema／PRD／ADR 决策变更；接口字段或状态码变化；外部 skills 副本、stable 快照与 catalog；graft 版本、pin 与 Caveman pin；实现代码、测试、安装器、运行时及前端文件；旧契约／文档任务；发出上游 issue；发布或 tag。v2.1.0 正式版不动，等 640 授权。

若后续发现必须改契约／schema／PRD／ADR 决策，记录分歧并停止扩展范围，另开 PR 等用户决定，不借“文档清理”改方案。本轮不改下表任何生产文件。

## 当前源码依据

基准 main：`7f20fbcce29c8d982d51aaaaa9ac19fcda3cf5a2`；当前分支与 front matter 一致，起始工作区干净。行号全部来自本轮读取，不沿用提示行号。

本地 `git log -6 --format='%H %s'` 确认：#214 为上述 HEAD；#213 为 `a2a3aa72281e9127de821f19fb5056ad76306d16`；#212 为 `e4c76707b368fb5e9873852ca3ce25abd67a6573`；#209 为 `6c5eef24e6cd4f1dba3872683d26b99a703c059b`；#210 为 `f2887297b2e098b8339758bba918afaa842fbe79`；ADR 0003 文档项实际是 #211（`947fb55ae112cfa66563f322a1c39c2ebcfd944b`），不是 #210。

| 计划项 | 当前文件:行 | 现状摘要 | 后续是否改动 |
|---|---|---|---|
| 1. README 发布身份 | `README.md:19,33`；`README.zh.md:19,33` | 横幅及安装提示均为 v2.0.1。本地 tag 有 v2.0.2、v2.1.0-rc.4，无 v2.1.0 正式版或 rc.5 tag；`CHANGELOG.md:35,155-157`、`CHANGELOG.zh.md:35,155-157` 明确 v2.0.2 为最新正式版、rc.4 为预发布 | 是。建议横幅写“最新正式版 v2.0.2 已发布”／“Latest stable v2.0.2 is released”，链接及安装提示 tag 改 v2.0.2；不把 rc.5 或 v2.1.0 称正式版。本轮只提建议 |
| 2a. ADR 0001 §8 是否已存在 | `docs/adr/0001-v2.1.0-rc.1-r1.0-runtime-decisions.md:182-209,213` | §8 正文已存在；213 行仍写“由另一契约 PR 追加，本分支基线尚未包含该节” | 是。仅把 213 行改为 §8 已由 #209 合入，保留编号及 §8 决策 |
| 2b. ADR 0001 §9 当前实现状态 | `docs/adr/0001-v2.1.0-rc.1-r1.0-runtime-decisions.md:215-217,246,266,268,270-271` | 215／217 仍待评审、批准后另开实现；246／266 将 pair no-store 写成 planned／尚未发送；268 仍称前端后续实现；270 仍称仅契约、operation planned、serve 未路由；271 的“未来实现”措辞未跟进 | 是。状态说明改为 #212 已实现，原契约 PR 的先后经过用过去时保留；246 仅改括号内实现状态，266 仅改 planned 状态句，268 仅去掉“后续”时态，270 说明路由和 marker 已实现，271 仅调整实现时态。保密、认证、回退条件及所有方案正文不变 |
| 3a. OpenAPI pair／取票描述 | `sbtd-runtime/contracts/openapi.yaml:59-60,99-100,1124` | pair 仍称 proposed／not yet implemented；取票 description 仍称 serve 尚未路由、另开 PR、pending security review；RePairTicket 仍称 Proposed recovery response | 是。只更正描述中的过时状态，指向 #212 已实现；1124 去掉 Proposed，不改响应 schema、字段、期限或状态码 |
| 3b. OpenAPI 已修正部分 | `sbtd-runtime/contracts/openapi.yaml:81,97`；`:69,123,150-151` | pair no-store 说明与取票 x-sbtd-implementation 均已 implemented；其他 no-store 句是仍有效的规范，不是待实现状态 | 已在 main 修正，无需改动。保留 info 级 `contract-only`（`:5-6`，表示文档来源，不表示未实现），不把 library 操作机械改成 implemented |
| 4a. 双语 rc.5 标题及已合入条目 | `CHANGELOG.md:10,16,22,24,26`；`CHANGELOG.zh.md:10,16,22,24,26` | 两文件各只有一个 rc.5 未发布标题；16 为 #212 实现、22 为 #213 实现、24 为 #209 换门禁、26 为 #214 re-pin。条目未直接标 PR 号，关联以本地合入日志和内容核对 | 保留这些实现／变更条目；后续仅在既有 Changed／变更下各追加一条本 PR 条目，不新建第二组标题 |
| 4b. #210 过时状态句 | `CHANGELOG.md:14`；`CHANGELOG.zh.md:14` | 英文末尾“Not implemented or routed by serve; implementation requires 640's contract approval and a separate PR.”；中文末尾“尚未实现，serve 未路由；实现待 640 批准契约后另开 PR。” | 是。仅末尾改为“契约先行，后续已由 #212 实现并接入 serve”及英文对应；保留当时新增契约、60／30 秒、错误码的事实，不删第 16 行 |
| 4c. 相邻 ADR 0003 遗留状态句 | `CHANGELOG.md:20`；`CHANGELOG.zh.md:20` | 英文末尾“Documentation only; implementation will follow in a separate PR.”；中文末尾“仅文档，实现另开 PR。”；本地日志表明原文档 PR 为 #211 | 是。仅末尾改为“本条记录文档先行，后续已由 #213 实现”及英文对应；保留 8 份／LRU 方案与第 22 行实现条目。这是未发布区状态更正，不把文档 PR 改称实现 PR |
| 5. ADR 0003 §6 | `docs/adr/0003-v2.1.0-rc.2-r2.0c-snapshot-persistence.md:68-70,74-102` | 68 行仍“实现另开代码 PR”；70 行的交付顺序仍用将来语气。74–102 为 8 份、LRU、磁盘保留、安全与回退方案 | 是。68 状态说明 #213 已实现；70 将“先文档、后代码”保留为已发生的顺序，不宣称部署／发布完成。74–102 方案及测试要求不改 |
| 6a. graft README | `README.md:407,414-416`；`README.zh.md:398,405-407` | 辅助定位，安装单独确认，版本指向受管运行时；无冲突版本字面量 | 已在 main 修正，无需改动 graft 段；README 只因第 1 项列入将改 |
| 6b. graft ENTRYPOINT | `ENTRYPOINT.md:25,91,239-242,330` | 三处版本均 0.28.0；按需启用，不可用用源码／LSP／contract 补充 | 已在 main 修正，无需改动 |
| 6c. graft Onboard Skill | `sbtd-workflow-onboard/SKILL.md:145,151-154,214` | 明确 optional／auxiliary、单独确认、固定 0.28.0；缺失不阻断无关初始化 | 已在 main 修正，无需改动。149 行 Mandatory Global Installation Policy 统领 required Skills，正文已排除 graft 必装，不借此重写 Skill |
| 6d. graft REFERENCE | `sbtd-workflow-onboard/REFERENCE.md:119,164-166` | 119／166 已明确辅助、可拒绝、pin 0.28.0；164 标题仍为 Required Global Tools，易让读者把下方 graft 当必装 | 正文已在 main 修正；仅计划把 164 标题改为 Global Tools and Optional Graft，消除标题误导，不改安装策略、命令或 pin |
| 6e. 其他非 archive 说明 | `prompts/automations/sbtd-workflow-tools-version-check.md:52-58`；`sbtd-workflow-onboard/templates/skills/sbtd-task/SKILL.md:46` | 自动化只跟已发布 workflow pin，不随官方 latest 或 update 升 graft；任务 Skill 明确 graft optional | 已在 main 修正，无需改动 |
| 6f. 旧版本命中分类 | `docs/prd/sbtd-workflow-v2-trellis-removal-graft-migration-prd.md:12-19`；`docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md:87-92` | 前者为 v2.0.0 交付／审核候选记录，19 行仍有“当前受管 pin 0.21.1”；后者为 v2.0.2 基线参考的 0.22.0，并非本轮运行 pin。非 archive 检索还命中旧 spike、lesson、验收记录 | 不改。保留带 SHA／日期的审核与基线事实，不把这些旧证据改造成 0.28.0 实测；PRD 不列入将改文件，当前使用说明以上述活入口为准 |
| 7. impeccable 补记位置 | `CHANGELOG.md:18-26,63`；`CHANGELOG.zh.md:18-26,63,463` | rc.3 #197 已记整组上游重锁，但未记覆盖 v1.0.15 本地补丁；463 行是旧修复事实，不能倒改 | 后续在 rc.5 新增双语条目内补“rc.3 #197 已去掉 v1.0.15 本地补丁”，并说明保持上游原样、不重打。新条目补充今天的说明，不改 v1.0.15／rc.3 正文 |
| 8. issue 草稿依据 | `CHANGELOG.zh.md:463`；`ai/tasks/v2.1.0-rc.5-external-skills-repin/task.md:202-214` | 旧修复方向及第 2 轮四项再现证据；212 行说明下载暂存并发旧模式未再现，不混入本次四项 | 本 task 写草稿；不改旧 task，不修外部副本，不发出 issue，负责人未确定 |

对照后未发现必须改契约／schema／PRD／ADR 决策的开放问题。上游四项已知问题仍在，记录投票处理口径不等于问题已修复。

## 后续实现计划与预期将改的文件

以下都是后续预期，不是本轮已改。实现前重新核对基线漂移，只改上表列出的状态文字。双语 CHANGELOG 各追加一条本 PR 条目，覆盖最终文档对齐、graft 仍可选且 pin 不动、impeccable 补记；不编造本轮没有执行的验证或上游 issue 链接。

| 相对仓库路径 | 后续预期改动 |
|---|---|
| `README.md`、`README.zh.md` | 第 19／33 行发布身份和安装示例对齐最新正式版 v2.0.2 |
| `docs/adr/0001-v2.1.0-rc.1-r1.0-runtime-decisions.md` | §9 过时状态／时态，§8 已存在说明；不动决策 |
| `sbtd-runtime/contracts/openapi.yaml` | 59–60、99–100、1124 的描述状态；不动契约结构及 implemented 标记 |
| `docs/adr/0003-v2.1.0-rc.2-r2.0c-snapshot-persistence.md` | §6 开头状态／交付时态，不动 §6 方案 |
| `sbtd-workflow-onboard/REFERENCE.md` | 仅 Required Global Tools 标题，明确 graft 可选 |
| `CHANGELOG.md`、`CHANGELOG.zh.md` | 仅 rc.5 第 14／20 行末尾状态更正，并在既有 Changed／变更各追加一条；其余历史事实和实现条目保留 |
| `ai/tasks/v2.1.0-rc.5-final-docs/task.md`、`ai/tasks/index.md` | 记录后续真实轮次与证据；index 仅由正式生成器维护 |

实现时必须小心：不把“文档先行”改成“当时已实现”；不改已发布历史事实；不改 ADR 决策正文、接口字段／状态码、外部 skills 副本、catalog、graft 版本或 Caveman pin。旧 PRD／契约任务不回写。当前轮仅记录这些计划。

## 验收标准（后续实现轮，尚未执行）

1. 上表需改的过时状态句按 #209／#212／#213 合入事实更正，README 发布身份与 tag／CHANGELOG 一致。
2. ADR 决策、OpenAPI 字段／状态码／安全边界不变；已 implemented 部分不重复改写。
3. 已发布历史条目事实不变；保留原文档先行事实与后补实现条目。双语仅在现有 rc.5 未发布标题下追加一条或做上述状态句更正，标题各仍唯一。
4. 外部 skills 副本、catalog、graft 版本／pin、Caveman pin、实现代码、测试和安装器未改；可选 graft 的标题不再暗示必装。
5. 新双语条目明确 rc.3 #197 已去掉 v1.0.15 本地补丁，保持上游原样，不重打补丁。
6. 上游 issue 仍为本 task 中的草稿、未发出，除非 640 另行确认；负责人未确定，不把写草稿记成已报上游。
7. 独立评审、适用校验及后续 CI 分别记录；本轮记录通过不等于实现完成、合入或发布就绪。

## 计划中的测试证据

本轮尚未改生产文档，不声称已经通过文档实现测试。后续实现轮至少执行：

- 措辞 grep：逐条核对上表目标，既有 implemented、规范性 no-store 和历史记载保留；双语 rc.5 标题各一个。
- 范围检查：只允许上表将改文件；比较 ADR 决策、OpenAPI 结构／字段／状态码和已发布 CHANGELOG 原文，证明只有允许的状态措辞变化；不新增措辞快照测试。
- `python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts`：相关任务状态／工作流测试，不冒充运行时或安装验证。
- 正式 index 生成／只读一致性预览、`git diff --check`、`git status --short --untracked-files=all`、`git diff --stat`；文案归因、路径和精确时间检查。

## 上游 issue 草稿

**草稿，未发出；发不发等 640 确认。** 目标：`pbakaus/impeccable`。本 PR 不负责发出，负责人未确定。

**Title:** Four issues in the upstream skill scripts: live-poll guidance, stale comments, Svelte reset scope, and Windows download-base validation

**Body:**

We recorded four issues while reviewing an unmodified copy of `plugin/skills/impeccable` pinned to commit `c1e0e5492fbb524f5df84d635ecfae7dc438ec45`. The locations below come from our recorded static source review, not a new Windows or full-browser reproduction. Our downstream v1.0.15 had local fixes; the later rc.3 refresh (#197 in KunoLu/640-skills) replaced the complete skill with upstream content and removed those patches. We now keep the upstream copy unchanged and would like fixes to come from upstream.

1. **User-visible live-poll guidance.** `scripts/live-browser.js:8025,10617,11208` still tells users to run `live-poll.mjs`. Expected direction: point users to `impeccable live-poll`, matching the compiled-engine CLI.
2. **Comments point to removed modules.** `scripts/live-browser.js:106,119,125,157,215,1731` still refers to the old vocabulary/ui-surfaces/live-server/live-accept/insert-ui modules. Our archive review did not find those runtime modules; a same-named live-accept test is not the runtime module. Expected direction: update maintenance comments to describe the compiled engine rather than deleted sources.
3. **Svelte reset clears unrelated handled history.** `resetSvelteComponentSession` calls `clearHandled()` without an id at `scripts/live-browser.js:6465`; the recorded review of `live-browser-session.js` found that the no-id path removes the entire handled key. Expected direction: clear only the current session's handled records and retain other sessions' history. We have not performed a fresh browser reproduction in this documentation round.
4. **Windows download-base input lacks URL-character validation.** The recorded review of `scripts/impeccable.cmd:128,155,163,194` found direct expansion of `IMPECCABLE_DOWNLOAD_BASE` into URLs passed to curl, without the previous delayed-expansion URL-character check. Expected direction: validate accepted URL characters safely before using the override. This requires control of the user's environment variable to affect the download address, and downloaded artifacts still pass checksum verification. We have not reproduced an exploit on Windows and do not claim a checksum bypass.

Our independent reviewer assessed these four findings as low risk and non-blocking for our upstream refresh. This is not a claim that they are fixed. The old fixed-name download/checksum temporary-file issue is not included: the recorded review found per-attempt directories with timestamp/random names, atomic mkdir and collision retries instead.

Evidence in KunoLu/640-skills at `7f20fbcce29c8d982d51aaaaa9ac19fcda3cf5a2`: `CHANGELOG.zh.md:463` records the old fix directions; `ai/tasks/v2.1.0-rc.5-external-skills-repin/task.md:202-214` records the pinned-source findings. Please review whether these should be corrected upstream so a future pin can pick them up without downstream patches.

## Strict Book Gate Plan

实现尚未开始改生产文档，本轮以记录和计划为主。已读 sbtd-task 的 strict／state 规则及 project-validation；未把计划、自审或 #214 的 CLEAN 当作本 PR 独立批准。

| Gate | 触发条件／阶段 | 本轮状态与后续动作 |
|---|---|---|
| DDD | 完整 grill 或领域歧义，需求稳定前 | not-needed：未完整调用 grill-with-docs，不新增领域决定 |
| DDIA | schema、缓存、迁移或跨服务设计变化，设计前 | not-needed：只对照已合入事实，不设计或改变数据机制 |
| Legacy safety | 首次行为变化前建立安全网 | not-needed：本轮仅记录；后续仍仅状态文字，若需改行为则停止另行决策 |
| Refactoring／ponytail | strict 首次生产编辑前按实际范围判断 | 后续生产文档编辑前复核最小改动；本轮无生产代码，不重构、不添抽象，不手改镜像 |
| BDD／TDD | 新行为或高风险覆盖缺口 | not-needed：本轮不新增行为／测试；后续纯状态措辞不增源文本断言 |
| Project validation | 记录生成后与后续实现后分别验证 | 本轮执行指定 index、两模块测试及文字／范围检查；实现验证仍待后续 |
| 独立评审 | 后续文档 diff，合入前 | pending：独立核对归因、历史及契约边界；本轮不调用子代理 |
| Release readiness | 运行时／部署风险，测试门后 | not-needed 于本轮记录；未进行发布验收，不宣称 rc.5 或 v2.1.0 发布就绪 |
| CI／合入 | 后续 PR 最终提交 | pending：本轮不提交、不推送、不开 PR |

## 验证证据

Evidence Source：developer-local；Source Revision：dirty（新增任务记录）；Evidence Publication：local-only；Environment Alignment：not-needed。基准 SHA／分支见上文，Linux x64。rtk：skipped-for-report，按本轮明确命令使用 native 输出，不使用缓存替代执行。本节为本地记录校验，不是 CI／正式 PR-head 报告。

| 命令／检查 | 实际结果 | 退出码 |
|---|---|---|
| `git status --short`、`git branch --show-current`、`git rev-parse HEAD`、`git tag --list`、`git log -6 --format='%H %s'` | 起始干净，分支／HEAD 匹配；已核对 tag 及 #209–#214 身份 | 0 |
| `namei -l` 两个目标、`git ls-files --stage --`、`git check-ignore -v --no-index --` | 父路径与 index 无链接；新 task 目录不存在；index 是已跟踪普通文件 100644；目标均无 ignore 匹配。namei 的缺失退出使首条串联 ls-files 未执行，已单独执行 ls-files 成功 | 1（新目录不存在）／0／1（无匹配） |
| `TZ=Asia/Shanghai date --iso-8601=seconds` | 开始写文件时为 2026-11-12T01:12:16+08:00；用于 front matter 及本轮事件记录时间 | 0 |
| read／grep 当前文档 | 已核对上表全部计划项；rc.5 标题各一处；issue 证据区分本轮读取与先前源码审查 | 工具成功，无 shell 退出码 |
| write 建立本 task | 亲手建立第 1 轮计划和 issue 草稿成功；不调用 task 状态写 API、子代理或 find；只使用会话内 todo 清单 | 工具成功，无 shell 退出码 |
| `python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); Path('ai/tasks/index.md').write_bytes(a); print('INDEX_REGEN', 'changed=%s' % (b!=a), 'rows=%d' % len(s._index_rows(r)))"` | `INDEX_REGEN changed=True rows=85`；84→85，只新增本任务一行；既有“旧格式事件，不追溯”提示不是失败 | 0 |
| `python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); print('INDEX_PREVIEW_SAME', Path('ai/tasks/index.md').read_bytes()==a, 'rows=%d' % len(s._index_rows(r)))"` | `INDEX_PREVIEW_SAME True rows=85`；逐字节一致，既有旧格式提示保留 | 0 |
| `python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts` | 99 项通过，失败 0、跳过 0；`OK`，31.110 秒 | 0 |
| `git diff --check`、`git status --short --untracked-files=all`、`git diff --stat`、`git diff -- ai/tasks/index.md` | 空白检查无输出；只有本 task 未跟踪与 index 修改。tracked stat 为 index 一行新增；diff 证实只加本任务链接。未跟踪 task 不进入普通 diff --stat，未为此修改 Git index | 0 |
| 专用 grep：新 task 的本机路径、禁用归因措辞及非“契约”目标用字 | 无匹配；index 新增行仅任务 id 与相对链接 | 工具成功，无 shell 退出码 |
| 补充 `git diff --no-index --check`：以空设备与新 task 比较；随后单独 `git diff --check` | no-index 无空白诊断，退出 1（新文件与空输入有差异），因此其后串联命令未执行；单独执行 tracked 空白检查无输出、退出 0。证据回填后的专用 grep 仍无匹配 | 1／0 |

本轮已执行读源码、写 task、正式生成／预览 index 和指定校验。Final Full Rerun：passed（仅上述 99 项工作流测试，不是运行时全量）；Targeted Rerun：not-needed。证据回填后只检查新增文字与空白，不重复跑实现测试。最终计数 edit 仅补模型表和推算说明，之后不再调用工具，不把该回填称为重新验证。

本轮跳过生产文档实现、运行时／前端／安装测试、全仓测试、lint／build、真实宿主和 CI：只获记录写入范围，无对应生产变化。BDD：skipped（无场景或行为变化）；Cross-repo context：not-needed；API Contract：not-needed（本轮未改 API，仅核对既有文档）；Mock Strategy：none。Final Test Report／Run Summary MD：not-needed（本地记录校验，不生成正式报告）。独立评审、实现、合入、发布未完成。恢复边界仅为本 task 与生成式 index；没有本机安装或生产状态需要回滚。

## 第 2 轮本地验证

本轮起始 HEAD 为 `7e8ed9e536f7c03e2c17c55cb6edf3828cb264ba`，分支 `docs/rc5-final-docs`，基于 main `7f20fbcce29c8d982d51aaaaa9ac19fcda3cf5a2`；开始时工作区干净。编辑前重读全部目标精确行，均与第 1 轮依据表一致，无行号漂移。生产文档改动后会话遭 SIGTERM 中断；续跑先用 `git status`／`git diff` 核对 8 个已改文件，符合计划，保留原样，未回滚或重做格式。

README 采用甲的最终结果为 5 票同意、0 票反对，已过半数，按授权执行。OMP 于 2026-11-12 01:18，Reviewy 与 Lord 于 2026-11-12 01:19，CodeX 与 Researchy 于 2026-11-12 01:23 投甲；Lord 于 2026-11-12 01:23 记录最终票数，以上均为北京时间，未提供秒数。CodeX、Researchy 各自独立确认 v2.0.2 为当前最新非预发布正式版；这些群内事实来自本轮提供的已核实背景，不替代下表本会话的命令证据。

| 计划项 | 实际改动位置／结果 |
|---|---|
| 1 | `README.md:19,33`、`README.zh.md:19,33`：横幅、Release 链接与安装 tag 对齐最新正式版 v2.0.2，其余句子不变 |
| 2 | `docs/adr/0001-v2.1.0-rc.1-r1.0-runtime-decisions.md:213,215,217,246,266,268,270-271`：§8 已由 #209 合入，§9 已由 #212 实现；原契约先行经过保留，保密、认证和回退条件不变 |
| 3 | `sbtd-runtime/contracts/openapi.yaml:59-60,99-100,1124`：仅更正三处描述；81／97、规范性 no-store、info 级 contract-only 与 library 标记均不变 |
| 4 | `CHANGELOG.md:14,20`、`CHANGELOG.zh.md:14,20`：仅改末尾状态，区分契约先行与 #212 实现、#211 文档与 #213 实现；16／22 实现条目保留 |
| 5 | `docs/adr/0003-v2.1.0-rc.2-r2.0c-snapshot-persistence.md:68,70`：#213 已实现，保留 #211 文档先行顺序；74–102 方案及测试要求不变 |
| 6 | `sbtd-workflow-onboard/REFERENCE.md:164`：仅标题改为 Global Tools and Optional Graft；安装策略、命令及 pin 不变 |
| 7 | `CHANGELOG.md:28`、`CHANGELOG.zh.md:28`：在既有 Changed／变更末尾各追加一条，覆盖本次清理，并说明 rc.3 #197 已去掉 v1.0.15 本地补丁；整份换为上游副本后，现按授权投票结果保持上游原样、不重打补丁；已发布历史不改 |
| 8 | 本 task 保留第 1 轮记录，追加第 2 轮说明、验证、模型记录及两条状态事件；index 仅正式生成器写入，内容未变；issue 草稿未发出 |

Evidence Source：developer-local；Source Revision：dirty；Evidence Publication：local-only；Environment Alignment：not-needed。Linux x64，Python 3.13.5；不是 CI 或最终 PR-head 证据。rtk：skipped-for-report，按明确命令使用 native 输出。以下均为本轮实际执行。

| 命令／检查 | 实际结果 | 退出码 |
|---|---|---|
| `git rev-parse --show-toplevel --abbrev-ref HEAD && git status --short && git rev-parse HEAD` | 仓库／分支／HEAD 匹配，起始干净；本机绝对路径不写入仓库 | 0 |
| `namei -l` 全部目标、`git ls-files --stage --`、`git check-ignore -v --no-index --` | 目标和父路径无 symlink，均为已跟踪普通文件 100644，无 ignore 命中 | 0／0／1（无匹配） |
| `TZ=Asia/Shanghai date --iso-8601=seconds` | README 编辑前核查开始时间为 `2026-11-12T01:21:31+08:00` | 0 |
| `git tag --list --sort=-v:refname` | 最新非预发布 tag 为 v2.0.2；版本更高的 tag 仅 v2.1.0-rc.1、rc.2、rc.3、rc.4，无 v2.1.0 或 rc.5 tag | 0 |
| `gh release list --limit 100` | v2.0.2 标记 Latest；比它新的 rc.1–rc.4 均标记 Pre-release | 0 |
| `gh release view v2.0.2 --json tagName,isPrerelease,isDraft,publishedAt,url` | tagName=v2.0.2，isPrerelease=false，isDraft=false，publishedAt=2026-10-15T23:12:58Z，URL 为 https://github.com/KunoLu/640-skills/releases/tag/v2.0.2 | 0 |
| `gh api repos/KunoLu/640-skills/releases/latest --jq '{tag_name,prerelease,draft,html_url}'` | tag_name=v2.0.2，prerelease=false，draft=false；与 list 的 Latest 标记一致 | 0 |
| `git status --short --untracked-files=all && git diff --stat && git diff --` 后接上述 8 个生产文件路径 | 中断后核对：8 files changed, 28 insertions(+), 24 deletions(-)；仅计划中的状态句、标题和双语新增条目，未重写正确改动 | 0 |
| 第 1 轮证据表的正式生成器写入命令原样执行，再执行同表只读预览命令 | `INDEX_REGEN changed=False rows=85`；`INDEX_PREVIEW_SAME True rows=85`；既有“旧格式事件，不追溯”提示保留，不是失败 | 0／0 |
| `python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts` | 99 项通过，失败 0、跳过 0，OK，36.017 秒 | 0 |
| `PYTHONPATH=sbtd-runtime python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_golden_contracts.py'` | 66 项通过，失败 0、跳过 0，OK，0.347 秒；实际加载 OpenAPI | 0 |
| `PYTHONPATH=sbtd-runtime python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_r1_acceptance.py'` | 16 项通过，失败 0、跳过 0，OK，0.324 秒；含 OpenAPI 版本及导出契约检查 | 0 |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest test_serve.RecoveryTests` | 13 项通过，失败 0、跳过 0，OK，0.254 秒；恢复流程及 no-store 回归；asyncio 输出一次 0.138 秒 setup 耗时提示，未失败 | 0 |
| `python3 -B local://rc5-doc-scope.py`（仓库外临时只读检查） | SCOPE_OK、OPENAPI_STRUCTURE_OK、ADR_BOUNDARIES_OK、FILE_SCOPE_OK；相对 HEAD 仅允许行变化，双语 rc.5 标题各一个、各新增一条，已发布历史逐字不变；YAML 去掉指定三处 description 后完全相等；ADR 246 括号外、266 状态句外、268／271 时态外均不变；无外部副本、catalog、pin、测试、实现或 index 变化 | 0 |
| `TZ=Asia/Shanghai date --iso-8601=seconds`、`python3 --version` | 记录时间 `2026-11-12T01:27:06+08:00`；Python 3.13.5 | 0 |
| task 回填后再次执行第 1 轮只读 index 预览命令 | `INDEX_PREVIEW_SAME True rows=85`；新记录仍可被正式生成器读取，index 未变 | 0 |
| `git diff --check`、`git status --short --untracked-files=all`、`git diff --stat`、`git diff --no-ext-diff --no-color --unified=0` | 空白检查无输出；仅上表 8 个生产文件和本 task，共 9 文件；证据回填前统计为 76 insertions(+), 25 deletions(-)，其中生产文档为 28 insertions(+), 24 deletions(-)；无未跟踪文件、无 index 改动 | 0 |
| 对上述 diff 新增行执行专用 grep：本机路径、禁用归因措辞及非“契约”目标用字 | 无匹配；固定授权短语保留，未为历史投票编造秒数 | 工具成功，无 shell 退出码 |
| `rm local://rc5-doc-scope.py && TZ=Asia/Shanghai date --iso-8601=seconds` | 仓库外临时检查脚本已清理；证据更新时刻为 `2026-11-12T01:28:57+08:00` | 0 |

已读 `.github/workflows/validation.yml`：主套件用 `tests/run_ci.py` 分片发现 tests；`tests/test_sbtd_runtime_r1_contracts.py` 与 `tests/test_sbtd_runtime_r1_acceptance.py` 将 golden／acceptance 接入发现。dashboard job 另跑 serve／export、前端及构建检查。本轮执行上述直接模块，未跑完整 13 个 CI job。检索 tests 与 runtime tests 未发现独立 CHANGELOG 检查模块；用本轮临时只读检查验证新增位置、唯一标题及历史保留，文档／REFERENCE 与 index 分别由 workflow_contracts、task_state 和正式生成器覆盖，不新增永久措辞测试。

Strict gate 更新：Refactoring Review 为 proceed／normal，仅文档状态清理，无需重构；未完整调用 grill-with-docs，无领域歧义，DDD not-needed。DDIA、legacy safety、BDD／TDD、release readiness 均 not-needed：不改数据设计或行为，不涉及部署／发布。Code Readability Review 不适用，无手写生产代码或测试修改。独立评审与最终 CI 仍 pending；未把自检或其他人的版本核查当作本 PR 独立批准。使用会话内 todo 清单，未调用任务状态写 API、子代理或 find。

Final Full Rerun：passed（仅上述 194 项本地定向测试，不是全仓或全栈）；Targeted Rerun：not-needed。BDD：skipped（无行为或场景变化）；Cross-repo context：not-needed；API Contract：verified（描述以外结构相等及相关测试，不代表部署验收）；Mock Strategy：none（本轮未新增 mock，RecoveryTests 使用既有可注入时钟装配）。Final Test Report／Run Summary MD：not-needed，本轮为本地校验而非正式 PR-head 报告。跳过全仓 lint／build、前端浏览器、安装与跨平台全量：无对应实现变化。剩余风险为待独立评审／CI，以及已记录的上游四项低风险问题；issue 草稿仍为「草稿，未发出；发不发等 640 确认」。v2.1.0 正式版不动，等 640 授权。本轮没有本机安装或生产状态需要回滚。

## 模型记录

| 轮次 | 模型 | 用途 | 模型调用 | 工具调用 |
|---|---|---|---|---|
| 第 1 轮 | openai-codex/gpt-6-astra（thinking high） | 只读核对、任务计划、issue 草稿、index 生成和本地验证 | 18（推算） | 67（推算） |
| 第 1 轮 | 其他模型 | 本会话未调用 | 0 | 0 |
| 第 2 轮 | openai-codex/gpt-6-astra | 文档状态更正、中断后续跑、Release 核查、index 与本地定向验证 | 19（推算） | 58（推算） |
| 第 2 轮 | 其他模型 | 本会话未调用 | 0 | 0 |

计数方法：在 omp 会话日志中筛选 `role=assistant`、`provider=openai-codex`、`model=gpt-6-astra` 的消息计模型调用，同一记录内 `toolCall` 条目计工具调用。只读统计脚本输出 `astra_assistant=16`、`astra_toolcalls=66`、`other_assistant={}`、`model_usage={}`，退出 0，未写仓库。此后仅一次 edit 回填次数和一次纯文本收尾，因此模型调用按 16+2=18、工具调用按 66+1=67 推算；不是事后重新读取日志的实测总数。其他模型 0，find 工具调用 0，子代理 0；计数 edit 为最后一次工具调用，之后不再运行校验。

第 2 轮计数：按给定命令运行仓库外 `count.py`，只读统计 `sessions-r2` 最新会话日志（含中断前调用），输出 `astra_assistant=17`、`astra_toolcalls=57`、`other_assistant={}`、`model_usage={}`，退出 0，未写仓库。此后仅一次 edit 回填和一次纯文本收尾，因此模型调用按 17+2=19（推算）、工具调用按 57+1=58（推算）；不是事后重新统计的实测总数。其他模型 0，find 工具调用 0，子代理 0。此计数 edit 为最后一次工具调用，之后不再校验；第 1 轮 18／67（推算）保持不变。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-12T01:12:16+08:00 | planned | checking | started：Lord 在合入 #214（合并提交 7f20fbcce29c8d982d51aaaaa9ac19fcda3cf5a2，提交时间 2026-11-12T01:06:47+08:00）之后，于 2026-11-12 01:07 群内调度开始最终文档 PR，先写 task.md；本轮只写 task.md 及正式生成的 index，不改生产文档 | 本轮分支／HEAD／干净起始状态核对；当前文档精确行号见源码依据表；本事件 at 为记录时间，不是群内调度秒数 |
| 2026-11-12T01:12:16+08:00 | checking | checking | 按 640 2026-11-11 23:59 授权的群内投票结果：甲 5 票同意、0 票反对（Reviewy、Researchy、CodeX、Lord、OMP；OMP 于 2026-11-12 01:07 投票；Lord 于 2026-11-12 01:07 记录结果），执行口径为保持上游副本、不重打本地补丁；给上游提 issue 仅以草稿记入本 task，未发出 | 本轮读取 CHANGELOG.zh.md:463 与外部 skills 任务第 2 轮 202–214 行；四项问题及风险写入草稿，负责人未确定，发不发等 640 确认；本事件 at 不是历史投票秒数 |
| 2026-11-12T01:15:47+08:00 | checking | checking | 第 1 轮完成任务计划、上游 issue 草稿、正式 index 和指定本地验证；生产文档实现仍待后续，保持 checking | INDEX_REGEN changed=True rows=85；INDEX_PREVIEW_SAME True rows=85；99 项测试通过／退出 0；git diff --check／范围核对退出 0，仅本 task 与 index；新文案 grep 无匹配；未发出 issue，无必须改契约决策的开放问题 |
| 2026-11-12T01:27:06+08:00 | checking | checking | 按 640 2026-11-11 23:59 授权的群内投票结果：README 版本采用甲（对齐最新正式版 v2.0.2，不把 rc.5 或 v2.1.0 称正式版）；OMP（2026-11-12 01:18）、Reviewy（2026-11-12 01:19）、Lord（2026-11-12 01:19）、CodeX（2026-11-12 01:23）、Researchy（2026-11-12 01:23）均投甲，5 票同意、0 票反对，已过半数，按授权执行；Lord 于 2026-11-12 01:23 记录最终票数，以上均为北京时间 | 群内事实来自本轮提供的已核实背景，未提供秒数；本事件 at 为本轮记录时间，不是投票时刻。CodeX 与 Researchy 各自独立确认 v2.0.2 最新非预发布身份；本会话另于 2026-11-12T01:21:31+08:00 执行 tag／Release 核查，Latest、prerelease=false，更高 tag 均为 rc.1–rc.4 预发布 |
| 2026-11-12T01:28:57+08:00 | checking | checking | 第 2 轮完成既有 8 项文档清理及本地定向验证；SIGTERM 中断后先核对已有 8 个生产文件改动，符合计划并保留；继续更新本 task，保持 checking，completed_at=null | tag／gh release list／view／latest API 核查 v2.0.2，退出 0；INDEX_REGEN changed=False rows=85，INDEX_PREVIEW_SAME True rows=85；99+66+16+13=194 项测试通过，各命令退出 0；临时范围／OpenAPI 结构／ADR 边界检查及 git diff --check 通过、退出 0；新增文字 grep 无匹配，9 个文件在允许范围内，临时脚本已清理；独立评审与 CI 尚未执行，issue 草稿未发出，无 Git 写命令 |
