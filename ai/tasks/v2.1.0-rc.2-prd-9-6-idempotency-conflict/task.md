---
schema_version: 1
id: v2.1.0-rc.2-prd-9-6-idempotency-conflict
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict、option A、PRD-only；主会话唯一 writer／验证 controller；只作两个本地 commit，不 push／开 PR／评论／merge／rebase／amend；仅显式 git add 授权路径。
status: done
branch: docs/v2.1.0-rc.2-prd-9-6-idempotency-conflict
created_at: '2026-10-23T10:45:17+08:00'
updated_at: '2026-10-23T10:48:16+08:00'
completed_at: '2026-10-23T10:48:16+08:00'
---

# rc.2 第 2 步：PRD §9.6 Idempotency-Key payload 冲突

## 用户决定与任务身份

任务来源：用户 2026-10-23「640 step 2: PRD §9.6 PR, option A」启动指令。用户于 **2026-10-22 23:23／23:24 Asia/Shanghai** 选择 option A（来源：编排方转述）：createExport 同 key 不同 payload 返回 HTTP 400；snapshot 写成待定，未实现 HTTP 入口，等 POST 路由实现时另开 PRD PR 决定；refresh／ingest 保留 409。

入口工作根 `/workspace/640-skills-s2prd`，分支见 frontmatter；HEAD 与 origin/main 均为 `de97926811410e7d61d846fc8e95ddaa0738bfbf`（PR #159 squash-merge）。入口 `git status --short` 为空。第 1 步 [PR #160](https://github.com/KunoLu/640-skills/pull/160) 已 OPEN、under review（来源：编排方转述；本会话不请求远端核验），满足 Lord 要求的开工前提；不读取或修改其 worktree。

未完整调用 grill-with-docs：用户决定、最小修改范围与验收均明确，只转录已批准决定，无新领域设计。

## 范围与验收

1. 仅修改 `docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md` §9.6 最后一段：createExport 400、createReportSnapshot 待定、refresh／ingest 409；保留同 key 同 payload 返回同结果、导出重试不产生多个无法追踪文件，并内联引用决定时间与来源。
2. 检查 §13 导出文本、§16 AC 与 §17 场景是否直接依赖旧句；无直接依赖则不改。AC-07 是 ingest 来源 ID 冲突，继续 409。
3. 第二个文件仅为本 strict task.md；index 按 rc.2 惯例不改。不改代码、OpenAPI、contracts/schema/golden、plan、install-and-use、ADR 或其他文档。
4. PRD 头部日期与 §22 修订记录沿用 PR #156 先例保持不变，由本记录与提交留据。plan「每个 PR 的第一个 commit 回填上一行」本次不适用：用户仅授权 PRD + task.md，且 #160 尚未合并，无可回填结果。
5. 验证包含 runtime／test grep、CI 适用性、Markdown 消费者 smoke、frontmatter YAML、指定 golden sanity 与 Git 范围检查；不新增措辞钉测，不把文档完成说成实现或发布。
6. 两个本地提交按用户指定顺序及标题，第一份只含 PRD，第二份只含本记录。不暂存 `.omp-r12b-addendum.txt`、`ai/tasks/codex-verify/`、`reports/` 或任何 `.env`；不修改全局配置，不触碰其他 worktree。

## 待定项

- createReportSnapshot 的同 key 不同 payload HTTP 处理待定：尚无 POST 路由实现，contract 标记 `x-sbtd-implementation: library`；等 POST 路由实现时另开 PRD PR 决定，不填状态码。
- createExport 的 400 **没有专用错误码名称**。`sbtd-runtime/contracts/openapi.yaml:516–517` 引用 `components.responses.BadRequest`；`:807–808` 只有 description，没有 code/schema。runtime 返回通用 `{"detail": "invalid export request"}`；不发明 code 字符串。
- 仅标记、不修改 `components.responses.Conflict`（`openapi.yaml:813–814`）：仍写 “Same idempotency key with a different payload, or a source-event conflict.”，refresh／ingest 分别在 `:372–373`、`:398–399` 引用其 409，与保留规则一致；createExport 的 `:509–527` 不引用 Conflict。

## Book Gate Plan

| Gate | 客观触发／阶段 | 结论与理由 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义；before-dev | not-needed；未完整 grill，仅转录明确批准的决定，无新领域边界。 |
| book-ddia-data-design | 持久化／schema／所有权设计稳定前 | not-needed；不设计或实现数据、缓存或幂等机制，不修改 wire contract。 |
| book-legacy-change-safety | 既有行为变更前 | not-needed；纯 PRD 转录，无 runtime 行为修改。 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；无生产代码编辑。 |
| book-release-readiness | runtime／部署变化；finish | not-needed；无实现、部署或发布。 |
| TDD／gherkin-bdd | 可观察行为实现前 | not-needed；不实现行为或新增场景，检查已有场景与覆盖，不新增文案测试。 |
| ponytail／Code Readability Review | 实现选型／手写代码检查 | not-needed；无代码，采用单段最小修订。 |
| 独立 review | 迁移／授权／全局配置／跨服务契约／广泛接口变更 | not-needed；沿用 disk-cap 先例，仅局部转录既定决定，不定义 wire contract；未派子代理。 |
| project-validation | check | 已加载；按现有 workflow／runner 与用户指定命令作本地文档及 golden sanity，不冒充 CI。 |

## 状态持久化限制

两个授权路径已逐级核对 containment、无 symlink；PRD 为 tracked 普通文件，新 task 不存在且两路径均不受 ignore。沿用 `ai/tasks/v2.1.0-rc.2-prd-disk-cap/task.md` 已记录的 TaskStore catalog/frontmatter 限制，不重跑已知失败；helper 的 active／index 写入也超出本次授权。本文件是用户指定的共享记录，保存 strict 选择与 append-only 事件；不声称 TaskStore lifecycle 或自动恢复成功，不写 active／ignore／身份。

## 验证证据

- 专用 grep：`idempot|different payload|invalid export request|ValueError` 检索 `sbtd-runtime/serve.py` 与 `sbtd-runtime/export_store.py`，再用 `def create_export|invalid export request|except \\(ValueError, UnicodeError\\)|def _existing_idempotent|different payload|Route\\(` 定位。`export_store.py:477–487` 的 `_existing_idempotent` 在 `:485–486` 对 payload 不同抛 `ValueError("idempotency key reused with a different payload")`；`serve.py:588–595` 调用 store，`:599–600` 捕获 `(ValueError, UnicodeError)` 返回通用 HTTP 400。
- 已有 store 覆盖：`sbtd-runtime/tests/test_export_store.py:512–529` 的 `test_idempotency_replays_same_payload_and_rejects_changes`，`:526–529` 断言变更 payload 抛 ValueError。**已有 HTTP 覆盖**：`sbtd-runtime/tests/test_exports_http.py:308–323` 的 `test_required_headers_and_idempotent_creation`，`:317–320` 同 key 同 payload 重放，`:321–323` 同 key 将 format 从 csv 改 html 断言 400；不是待补的 HTTP 测试缺口。本轮只读覆盖源码，不声称运行该 HTTP 测试。
- `serve.py:657–679` 完整路由表无 refresh、ingest 或 `POST /api/v1/report-snapshots`；仅 snapshot GET 与 dataset GET。`openapi.yaml:400–405` 明确 createReportSnapshot 为 library。refresh／ingest 409 是保留规范，不是已实现 HTTP 路由的证明。
- 基线 `serve.py:581–587` 的 JPEG/PDF renderer 检查仍可能先返回 503；因此上述 400 结论限于请求进入 store 的冲突处理路径，不宣称 #160 的优先级修复已合并或本次实现了它。
- PRD 全文检索 `409|Idempotency-Key`，并阅读 §16／§17：§13 无相关状态码或 key 文本，§16 仅 AC-07 的来源 ID 冲突 409；§17 无依赖旧冲突句的场景。保持这些章节及 §9.6 错误表不变。
- 已读 `.github/workflows/validation.yml` 与 `tests/run_ci.py:51–78,293–371`：workflow 对每个 PR 触发、无 paths 过滤；Linux 三片全套 tests、Windows 四片原生选择、macOS 原生选择、dashboard 构建／测试及聚合门禁均仍适用。runner discovery 为 `tests/test_*.py`，没有面向本 PRD／task 的 docs 专项 lint 或通用 Markdown lint；本地不执行完整跨平台 CI。
- 专用 grep 检索 `tests/`、`sbtd-runtime/tests/` 的 PRD 完整文件名、`docs/prd`、`Runtime_API`、`PRD_v0` 与 Markdown glob：未发现读取目标 PRD 的测试；命中的 `docs/lessons` 扫描与 migration fixture 无关，无额外 PRD 消费者测试可运行。

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python -B -m unittest sbtd-runtime/tests/test_golden_contracts.py`：exit 0，61 tests，OK；unittest 用时 0.317 秒，完整进程 wall time 0.443 秒。未修改 contract/golden；只作为用户指定 sanity，不宣称完整 runtime 或 CI 通过。
- Python 3.13.5 无落盘脚本的文档消费者 smoke：`MarkdownIt('commonmark').enable('table').parse(section_9_6)` 成功，1 个表格、9 行（含表头）、1 个段落、无 fence；`yaml.safe_load` 成功解析本 task frontmatter，strict／user 与时区时间检查通过；合计 0.002 秒。只证明文档结构可消费。
- `git diff --check` 与 `git diff --cached --check`：退出 0、无输出。`git diff origin/main --stat -- sbtd-runtime/contracts contracts sbtd-runtime/*.py`：为空；`git diff origin/main --name-only`：恰为本 task.md 与目标 PRD 两个授权文件（先显式暂存新 task，使新增文件进入比较）。
- PRD 原生 staged diff 逐项人工复核：只有 §9.6 第 845 行替换，1 insertion／1 deletion；同 payload 规则与导出可追踪性保留，三个 operation 分支符合 option A，无新错误码或保留时长。§9.6 错误表、AC-07、§13、§17、PRD 头部日期与 §22 不变。严格 Gate 逐项适用性复核完成；独立 review 不适用，未将主会话复核称为独立审查。

本轮为 developer-local 文档诊断与指定单元 sanity，`Source Revision: dirty`（基线 de97926811410e7d61d846fc8e95ddaa0738bfbf 上的两份文档），`Evidence Publication: local-only`，非正式 PR-head／CI 报告；无报告或临时脚本落盘。`rtk: not-needed`（用户指定 native 命令及直接 Python 解析）；`BDD: skipped`（纯文档转录，不新增／改变 §17 场景；保持既有中文说明＋英文 Gherkin）；`Cross-repo context: not-needed`；`API Contract: verified`（只读核对，不更改）；`Mock Strategy: none`。未运行完整 CI、HTTP/API、浏览器、跨平台及代码 lint/build：无代码或契约变化，本次不是 runtime 发布验证。

## 提交与恢复边界

1. `d4cf709d7682ec61ec52c5b3710012b529d87ee9` — `docs(prd): §9.6 Idempotency-Key payload conflict — createExport 400, snapshot pending, refresh/ingest 409 (option A)` — PRD only，已本地提交，1 insertion／1 deletion。
2. `docs(task): record rc.2 PRD §9.6 idempotency-conflict task` — 本文件 only；自身 SHA 由最终 stdout 输出，避免自引用。

本次 done 仅指本地文档交付，不等同 push、PR、合并、实现、部署或发布。无需数据迁移；恢复边界仅为两份文档，不操作远端或其他 worktree。未读取秘密、未作全局配置变更。

## 模型使用

| 用途 | 请求模型 | 实际模型／证据 | assistant messages | toolCall blocks |
|---|---|---|---|---|
| astra 连通性 ping（operator，`--no-tools`） | openai-codex/gpt-6-astra:high | session 01a166a4-25f9-7471-8ad4-14fb95fd32b7；只读核对 model_change、thinking_level_change 与唯一 ASTRA_OK 回复，无 toolCall | 1 | 0 |
| 主会话（唯一 writer；PRE-COMMIT SNAPSHOT） | openai-codex/gpt-6-astra:high | session 01a166a5-0a8a-721e-94a7-0b9a8c4233a6；model_change=openai-codex/gpt-6-astra；thinking_level_change=high；resolvedModelIsFallback=false | 11 | 42 |

**PRE-COMMIT SNAPSHOT** 取自 `2026-10-23T10:47:57+08:00`，日志 `/home/box/.omp/agent/sessions/--workspace-640-skills-s2prd--/2026-10-23T02-44-14-602Z_01a166a5-0a8a-721e-94a7-0b9a8c4233a6.jsonl` 第 1–101 行；只读提取 model_change／thinking_level_change 与 assistant／toolCall 计数，实际 assistant 均为 openai-codex/gpt-6-astra。此为提交前快照，**不是最终计数**，operator 在 PR body 报告最终值。Title-gen／job-widget：未知（未记录）；未派子代理，未改模型配置；快照无 grok 回复或 fallback，任何 grok reply 均按 fallback 计。ping 同目录日志 `2026-10-23T02-43-16-089Z_01a166a4-25f9-7471-8ad4-14fb95fd32b7.jsonl` 已核对 high／非 fallback 与 ASTRA_OK、1／0。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-23T10:45:17+08:00 | planned | in-progress | 第 2 步曾于 2026-10-23 09:46 +08:00 提前开工准备，09:47 按 Lord 安排叫停（未运行 omp、未留分支），偏差已记于 PR #160 的 task.md；本次在 #160 开出后正式开工。 | 入口 HEAD＝origin/main de97926811410e7d61d846fc8e95ddaa0738bfbf（PR #159 squash-merge）；#160 OPEN、under review（来源：编排方转述）；分支匹配、工作区干净、路径／ignore 已核对 |
| 2026-10-23T10:46:53+08:00 | in-progress | checking | §9.6 单段最小修改完成，runtime／contract／既有测试覆盖已定位，进入文档解析、范围及提交检查 | createExport 400；snapshot 待定；refresh／ingest 409；HTTP 测试已有 :321–323 的 400 断言；golden 61 passed |
| 2026-10-23T10:48:16+08:00 | checking | done | 本地文档交付收口：PRD 已提交；指定 sanity、Markdown／YAML smoke、范围检查与逐项决定复核通过；本记录随第二个本地 commit 保存，不等同 PR／合并／发布 | PRD commit d4cf709d7682ec61ec52c5b3710012b529d87ee9；golden 61 passed；diff --check clean；runtime/contracts diff empty；仅两份授权文件；PRE-COMMIT SNAPSHOT 11 assistant／42 toolCall |
