---
schema_version: 1
id: v2.1.0-rc.2-prd-disk-cap
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict、PRD-only；主会话唯一 writer／验证 controller；三个本地 commit，首 commit 回填 R2.1b；显式 git add，不 push、不开 PR、不评论，不暂存 .omp-r12b-addendum.txt 或 ai/tasks/codex-verify/。
status: done
branch: docs/v2.1.0-rc.2-item4-disk-cap-prd
created_at: '2026-10-22T17:10:55+08:00'
updated_at: '2026-10-22T17:16:40+08:00'
completed_at: '2026-10-22T17:16:40+08:00'
---

# rc.2 计划第 4 项：PRD §10.4 磁盘上限补充

## 用户决定与任务身份

用户于 **2026-10-22 约 17:05 Asia/Shanghai** 经 Lord、640-skills 房间决定：「开第 4 项磁盘上限 PRD PR（首 commit 回填 R2.1b）」。本会话仅完成本地提交；push／开 PR／评论由 operator 负责。

工作根 `/workspace/640-skills-item4-prd`，分支见 frontmatter；入口 HEAD 与 origin/main 均为 `c5904ef787c29bf9761f44ca4613ce0f2805daa4`。未完整调用 grill-with-docs：用户指定的决定、文档范围与排除项明确，直接沿用 plan「磁盘上限决定（用户 2026-10-21 12:58 +08:00 批准）」与「2026-10-21 计划定稿」第 4 项，不重开需求。

## 范围与验收

1. 第一个 commit 仅回填 plan 的 R2.1b 行／小节及 renderer task：#155、完整 merge SHA、mergedAt 完成时间、committer 时间、run8 最终计数与 closeout；保留历史证据。
2. 第二个 commit 仅修改 PRD §10.4：按原决定写共享按字节配额、默认 2 GB、环境变量调整、80% 预警、新建前清理、超限拒绝、不淘汰未过期快照、损坏／未知文件保留但计入、自有目录边界及后续职责。不新增数值、变量名、错误码或预警渠道。
3. 第三个 commit 仅提交本 strict 记录；复核模型计数、实际检查与本地完成边界。任务 index 沿用 rc.2 惯例不改。
4. ADR 0003 §4／§5 修订、磁盘上限错误码与错误体的独立 contract PR（含 golden tests）、R2.2 实现与容量实测校准默认值另行。本任务不涉及后续项 D（Idempotency-Key replay 先于 renderer 检查）。
5. 不改代码、contracts、golden tests、ADR、install-and-use.md、PRD 头部日期／§22／其他章节；不 push、不开 PR、不评论。

## 待定项

- 共享磁盘配额环境变量名尚未确定；由 ADR 0003 §5 修订确定。本任务不发明名称。
- §22 修订记录本轮按授权保持不变；本次变更由三个 commit 与本记录留据，无需在本轮另加一行。

## Book Gate Plan

| Gate | 客观触发／阶段 | 结论与理由 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义；before-dev | not-needed；未完整 grill，只回填已批准决定，无新领域边界。 |
| book-ddia-data-design | 持久化／schema／所有权设计稳定前 | not-needed；不设计或实施存储，逐项转录已批准决定；ADR、contract 与 R2.2 分开。 |
| book-legacy-change-safety | 既有行为变更前 | not-needed；纯文档，无行为改变。 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；无生产代码编辑。 |
| book-release-readiness | runtime／部署变化；finish | not-needed；无实现、部署或发布。 |
| TDD／gherkin-bdd | 可观察行为实现前 | not-needed；本次仅 PRD 记录，不改代码或既有场景，不新增措辞钉测。 |
| ponytail／Code Readability Review | 实现选型／手写代码检查 | not-needed；没有代码，采用最小文档增补。 |
| 独立 review | 迁移／授权／全局配置／跨服务契约／广泛接口变更 | not-needed；仅局部 PRD 转录及历史 closeout，不定义 wire contract；未派子代理。 |
| project-validation | check | 已加载；依据现有 workflow／runner 选择文档适用检查，不以 runtime 历史绿灯作为本轮证明。 |

## 状态持久化限制

四条授权路径已逐级只读核对 containment 与无 symlink；入口时新 task 不存在，三份既有文件为 tracked 普通文件，新 task 不受 ignore。入口 `git status --short` 为空，未出现提示中预期的两项未跟踪文件；不创建或暂存它们。沿用 R2.1b 与 rc.2 contract task 已记录的 TaskStore catalog/frontmatter 限制，不重跑已知失败；helper 的 active／index 写入也超出本次授权。本文件是用户要求的共享记录，已保存 strict 选择，不声称 TaskStore lifecycle 或自动恢复成功，不改 active／ignore／身份。

## 验证证据

- `git show -s --format=%cI c5904ef`：`2026-10-22T16:22:15+08:00`。mergedAt 采用 operator 已核实的 `2026-10-22T08:22:16Z`，即 `2026-10-22T16:22:16+08:00`；本会话未请求 GitHub API。
- Python 只读解析 R2.1b session `2026-10-22T06-36-23-370Z_01a16253-37ca-7535-b26a-cc86989790e0.jsonl` 第 411–471 行：9 assistant messages／24 toolCall blocks，全部 `openai-codex/gpt-6-astra`，无 task 子代理调用，末事件 `session_exit`。run8 日志 `omp.2026-10-22.355356.log` 有一次 `title-generator: request` 及对应 success，模型 `cursor/composer-2.5`。
- 全仓专用 grep（Rust regex／rg 等价搜索）检索中文磁盘上限／配额、`2 GB`／`80%`、disk/storage cap/quota、SBTD 配额变量候选与环境变量表述：未发现已确定的共享配额变量名。plan 只说可用环境变量调整；grill 未命名；ADR 0003 §5 仍写无新增配置面。PRD §10.1 的 `SBTD_RUNTIME_HOME` 是存储根，不是配额变量；golden 中 `EXPORT_DISK_SIZE_LIMIT` 是错误码反例，不是环境变量或本任务决定。
- `git diff --check`：前两次 commit 前均通过；第二个 commit 后 `git diff --check origin/main..HEAD` 与工作区检查均退出 0、无输出。
- `git diff -- docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md`：已查看完整原生 diff，仅 §10.4 两条表格说明与新增四段，10 insertions／2 deletions；头部日期、§22 和其他章节不变。逐项对照用户决定，无新增数值、变量名、错误码或渠道。
- 已阅读 `.github/workflows/validation.yml` 与 `tests/run_ci.py` 的平台选择、发现与命令入口，并检索 tests 中的文档相关检查：**无适用于本 PRD／任务记录的 docs 专项检查**，无通用 Markdown lint／文档链接 checker。`test_sbtd_probe_links` 是宿主／文件系统链接行为测试，不是 Markdown 链接检查；不因名称含 links 运行无关套件。
- Python 3.13.5 只读文档消费者 smoke（`functions.eval` Python，无落盘脚本）：`MarkdownIt('commonmark').enable('table').parse(section_10_4)` 成功，1 个表格、6 行（表头＋5 数据行）、6 个段落，无代码围栏误吞；`yaml.safe_load` 解析两份任务 frontmatter，`datetime.fromisoformat` 校验非空时间，Markdown 任务表解析成功。只证明文档结构可被消费，不证明配额实现。
- 提交前诊断脚本曾把 `git diff --no-index --check /dev/null <新 task>` 的 exit 1 当失败断言；该命令 stdout／stderr 均为空，exit 1 表示新文件与 `/dev/null` 不同，不是空白错误。保留会话中的失败输出，不改文档迎合断言；正式暂存检查采用 `git diff --cached --check` 的正常退出码语义。

验证为本地文档诊断，非 CI／runtime／正式测试报告；无需要保留的 runner 报告或脚手架。代码 lint、单元、API、浏览器、跨平台及全仓 CI 均未运行：没有代码／契约／场景变化，磁盘配额实现与容量校准归 R2.2。`BDD: skipped`（纯文档转录；无场景路径变化），`Cross-repo context: not-needed`，`API Contract: not-needed`（独立 PR 定义），`Mock Strategy: none`；`rtk: not-needed`（使用用户指定 Git 命令与直接 Python 解析；工具压缩的完整 diff 已通过 raw artifact 读取）。`Evidence Source: developer-local`，`Evidence Publication: local-only`；不声称 PR-head CI 或发布就绪。

## 提交与恢复边界

1. `9fc31f8f94e9925b5e69bf7540214043ae1366f2` — `docs(plan): backfill R2.1b (#155 / c5904ef) and close task record`，只含 plan 与 renderer task。
2. `2941de0457233995a17968b4e094361750fae850` — `docs(prd): add shared snapshots/exports disk cap to §10.4 (rc.2 item 4)`，只含 PRD §10.4。
3. `docs(task): record rc.2 item 4 disk-cap PRD task`，只含本文件；自身完整 SHA 由最终 stdout 输出，避免自引用。

done 仅指本地文档提交完成；push／PR 由 operator 另行处理，不等同合并、实现、部署或发布。无运行时或数据迁移；撤回仅涉及这三个文档提交，不删除用户数据，不改远端或其他 worktree。ADR 0003 与 PRD 的后续设计差异已明确交由独立修订处理，不能据本任务宣称配额已生效。

## 模型使用

| 用途 | 请求模型 | 实际模型／证据 | assistant messages | toolCall blocks |
|---|---|---|---|---|
| astra 连通性 ping（operator 运行，`--no-tools`） | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra；session 01a162dd-898d-7633-b24a-468764fbe062，只读复核 | 1 | 0 |
| 本次主会话（截至提交前；唯一 writer） | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra；thinking_level_change=high；session 01a162e0-1965-7253-b000-9bc83aa78974 | 21 | 51 |

未派子代理；未修改模型配置。标题生成计数留给 operator，本记录不填本次标题生成计数。

提交前最后一次只读统计于 `2026-10-22T17:16:40+08:00`：Python `json.loads` 解析 `~/.omp/agent/sessions/--workspace-640-skills-item4-prd--/2026-10-22T09-10-16-165Z_01a162e0-1965-7253-b000-9bc83aa78974.jsonl` 第 1–129 行，筛选 `type=message`／`role=assistant` 并汇总其中 `type=toolCall` blocks，得到 21／51；全部为 astra，无 task 子代理调用。这是截至提交前的快照，不含后续回填、commit 与最终报告；不是最终会话总数。ping 来源为同目录 `2026-10-22T09-07-28-269Z_01a162dd-898d-7633-b24a-468764fbe062.jsonl`。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-22T17:10:55+08:00 | planned | in-progress | 用户明确 strict 与三个本地提交；根／分支／基线匹配，已读决定、ADR、PRD 与回填先例 | origin/main c5904ef787c29bf9761f44ca4613ce0f2805daa4；git show ceb202ee23／037fe934ea；路径与 ignore 核对 |
| 2026-10-22T17:13:53+08:00 | in-progress | checking | 回填已提交，PRD diff 已逐项对照批准决定并限定 §10.4；进入文档解析、范围检查与任务记录收口 | 首 commit 9fc31f8f94e9925b5e69bf7540214043ae1366f2；PRD 原生 diff；无共享配额变量名 |
| 2026-10-22T17:16:40+08:00 | checking | done | 本地文档交付收口：回填与 PRD 已提交，记录和提交前模型计数完成；本记录随第三个本地 commit 保存，PR 由 operator 开，不等同合并 | 9fc31f8f94e9925b5e69bf7540214043ae1366f2；2941de0457233995a17968b4e094361750fae850；diff --check 通过；Markdown／YAML smoke 通过；主会话截至提交前 21／51 |
