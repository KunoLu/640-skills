---
schema_version: 1
id: v2.1.0-rc.2-r2.2-statistics-507-contract
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：strict、CONTRACT-ONLY、三个本地提交；主会话唯一 writer／验证 controller，不使用 advisor。
status: in-progress
branch: contract/v2.1.0-rc.2-r2.2-statistics-507
created_at: '2026-10-24T09:25:04+08:00'
updated_at: '2026-10-24T09:35:45+08:00'
completed_at: null
---

# R2.2 statistics/query 507 契约

## 决定、范围与边界

- 用户 2026-10-23 16:44 群内确认（方案 1），Lord 记录：PR-3 合并后先开 queryStatistics 的 507 DISK_QUOTA_EXCEEDED contract PR，复用 #158（82d42a2）错误体；契约合并后再做小实现 PR，随后 PR-4。
- 用户 2026-10-24 09:22 群内确认（开始），Lord 记录。
- 编排方整理：仅改 OpenAPI、既有 golden／契约测试、spec／plan／task；不改 runtime、PRD、schema，不操作 #164 正文，不 push／PR／comment／merge／rebase／amend／force。
- 授权根 `/workspace/640-skills-507-contract`；入口 HEAD／origin/main `253dceccc77fb0b7b929a81ac28e4c53d6968240`，工作区干净，分支已核实。先 records 回填、再 contract＋golden＋spec、最后本记录；显式路径暂存，不暂存 reports、.omp-r12b-addendum.txt、ai/tasks/codex-verify/、.env*。
- 未完整调用 grill-with-docs：既定决定、共享错误体和验收 seam 明确，无领域歧义。沿用 sibling contract task 的 Markdown 持久化边界与已记录 TaskStore catalog/frontmatter 限制，不重试已知失败，不写 active／index／ignore／身份，不声称 helper lifecycle 或自动恢复成功。旧 task 的 branch 是历史绑定，本次仅追加 #164 回填，不重绑定。

## Book Gate Plan

| Gate | 客观触发／阶段 | 初始状态 |
|---|---|---|
| book-ddia-data-design | 公开响应契约／稳定设计前 | 已加载；待源码确认 snapshot 写入与拒绝语义后输出 Review。 |
| book-ddd-distilled-modeling | 完整 grill／领域歧义 | not-needed；未完整 grill，沿用既定领域边界。 |
| book-legacy-change-safety | 既有运行行为修改 | not-needed；contract-only，不改 runtime。 |
| book-refactoring-pass | 生产代码编辑 | 已读路由；not-needed，无生产代码编辑或重构。 |
| book-release-readiness | runtime／部署／发布变化 | not-needed；契约领先实现，不声明发布就绪。 |
| TDD／gherkin-bdd／ponytail | 契约消费者 seam／before-dev | 已加载；复用 OpenApiDraftTests，先 red 后最小 YAML 修改，无新依赖。 |
| 独立 review／可读性 | 公共契约／check | pending；只读 review，不使用 advisor；主会话唯一验证 controller。 |
| project-validation | 编排方整理的验收命令／check | 已加载；golden、OpenAPI consumers、runtime full、schema consumer smoke、ruff 与 diff；保留原生失败和同 stem 中文汇总。 |

## BDD 场景

语言沿用 `sbtd-runtime/spec/r1.0-contract-scenarios.md`：中文正文、英文关键词，不新增 .feature 或 runner。契约 seam 不等于 live HTTP 已实现。

```gherkin
Scenario: 统计查询所需快照被共享配额拒绝的响应契约
  Given 统计查询需要创建快照且共享配额清扫后占用为 2000000001 字节、有效上限为 2000000000 字节
  When 客户端查看 POST /api/v1/statistics/query 的响应契约
  Then 507 引用与 createExport 和 createReportSnapshot 相同的 DiskQuotaExceeded
  And 错误体仅含 detail DISK_QUOTA_EXCEEDED、used_bytes 与 quota_bytes
  And 原有 200 Json、400 BadRequest、401 Unauthorized、403 Forbidden 保持不变
```

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-24T09:25:04+08:00 | planned | in-progress | 编排方整理：strict contract-only 开工，保存模式与三提交边界。 | 用户 2026-10-24 09:22 群内确认（开始），Lord 记录；入口 SHA／分支／干净工作区已核实；六条目标路径 containment／无 symlink，reports ignore 已核实。 |
| 2026-10-24T09:32:27+08:00 | in-progress | in-progress | 编排方整理：records 已提交，507 契约 red→green 与消费者 smoke 完成；全量 suite 有环境依赖失败，不记全绿。 | commit 1 95284766652862826c13f98a4b69cb671699f133；golden 62 passed；OpenAPI consumers 51／3 skipped；runtime 429／1 failure／10 skipped，缺 tzdata；备用 venv 不存在；既有 I001 保留。 |
| 2026-10-24T09:34:54+08:00 | in-progress | in-progress | 编排方整理：contract＋golden＋spec 已本地提交；追加提交前模型取样与内容身份核验，保持任务开放。 | commit 2 1eaca41b8f29ed07521a7e8761275b3331e8fad7；三文件提交 blob 与 runtime-full 被测 SHA-256 一致；不是提交后重跑，环境依赖失败仍保留；commit 3 仅本记录，无远端操作。 |
| 2026-10-24T09:35:45+08:00 | in-progress | in-progress | 编排方整理：第三次提交前 task／归因／范围与已生成报告结构检查完成，追加实际证据；环境失败与未实现边界不变。 | commit3-integrity exit 0／0.164s；report-integrity exit 0／0.062s，核对当时已有 14 对 raw／中文汇总；commit3-diff-check exit 0／0.003s；final-scope-stat exit 0／0.007s。 |

## Gate 执行结论（追加）

- **DDIA Data Design Review: confirmed。** 已读 `serve.py:526-544` → `stats_query.py:183-215` → `report_snapshot.py:833-939` → `disk_quota.py:154-165`。查询附加快照，已有快照复用后才进入新建准入；共享配额先清扫再计量，U > L 抛出异常；当前 query HTTP handler 仅捕获 QueryScopeError，尚无 507 映射。本次只增加声明，不改变数据所有者、共享锁、一致性、写入、幂等、清扫或恢复；无迁移。既有 507 schema 与所有其他 YAML 结构由 smoke 对比基线保持不变，描述仅末尾追加。
- **TDD／BDD。** 新增精确响应集合测试，基线只有 200／400／401／403，red 因缺少 507 失败；增加共享引用后 green。对两个创建入口逐一比较同一 `$ref`，不复制或内联 schema。既有 snapshot response map 已含 507，无需改写；无其他 queryStatistics 精确响应映射测试需迁移。`tests/` 与 `sbtd-runtime/tests/` 的 `openapi.yaml` 搜索命中 golden、r1_acceptance、renderer_integration；test_serve 的两处只是路径穿越请求，不加载契约。
- **Ponytail／Code Readability。** 无新抽象、依赖、schema、生产代码或无关 import 修复。新测试沿用相邻 unittest 字典与 subTest 风格；旧断言全部保留。refactoring／legacy／release gates 仍 not-needed；不声称 runtime／发布就绪。
- **本地独立只读检查。** ContractBoundaryReview 核对 schema 身份、条件语义、精确集合和 BDD；RecordBoundaryReview 核对两文件回填、时间归因与 append-only；均返回 no findings／correct，confidence 0.95。两者未运行 tests／lint／format、未写文件，非 advisor；只记录本地检查，不代表 PR review、Reviewy CLEAN、CI 或合并。新 task 后续证据追加由主会话负责校验，不扩大两者已查快照范围。

## 验证证据

环境为授权 worktree、Linux 6.12.94+／x64、当前 `python3` 3.13.5（`/home/box/.local/venvs/project-validation/bin/python3`）。主会话唯一验证 controller；`rtk: skipped-for-report`，原生 subprocess 捕获 stdout／stderr／exit／wall time／完整 HEAD／被测文件 SHA-256。报告放本目录 ignored `reports/`，每轮同 stem `.json` raw＋九节中文 `.md`；失败轮保留，不暂存。`Evidence Source: developer-local`、`Source Revision: dirty`、`Environment Alignment: unverified`、`Evidence Publication: local-only`，不以提交前结果冒充新 SHA 的 CI。

所有 Python 验证环境均为 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests`，命令使用 `python3 -B`；ruff 另加 `RUFF_NO_CACHE=true`。

| 轮次／raw label | 命令 | exit／原生计数与时间 | 墙钟秒 |
|---|---|---|---|
| records-check | `python3 -B -c <records_script>` | 0；旧 task 前缀除 updated_at 逐行保持，仅追加 2 事件；plan 仅插入 1 bullet；YAML／Markdown／日期有效；新增行禁词 0 | 0.129 |
| commit1-diff-check | `git diff --check` | 0 | 0.004 |
| query-507-red | `python3 -B -m unittest test_golden_contracts.OpenApiDraftTests.test_query_statistics_declares_shared_disk_quota_refusal -v` | 1（预期）；1 test／1 failure，0.055s，精确集合缺 507 | 0.211 |
| golden-green | `python3 -B -m unittest sbtd-runtime/tests/test_golden_contracts.py -v` | 0；62 passed，0.342s | 0.462 |
| ruff-check | `ruff check sbtd-runtime/tests/test_golden_contracts.py` | 1；仅既有 I001，19–30 行 import block 未修改，不修无关 imports | 0.189 |
| ruff-format | `ruff format --check sbtd-runtime/tests/test_golden_contracts.py` | 0；1 file already formatted | 0.017 |
| contract-consumer-smoke | `python3 -B -c <smoke_script>` | 0；YAML parse、引用解析、JSON round-trip、schema 合法／非法样例与基线结构对比通过 | 0.195 |
| openapi-consumers | `python3 -B -m unittest test_r1_acceptance test_renderer_integration -v` | 0；51 tests，48 passed／3 skipped，83.935s | 84.187 |
| runtime-full | `python3 -B -m unittest discover -s sbtd-runtime/tests` | 1；429 tests，418 passed／1 failure／10 skipped，142.840s | 143.270 |
| commit2-integrity | `python3 -B -c <integrity_script>` | 0；仅授权路径、task frontmatter schema＋FormatChecker、Markdown／+08:00、旧 task 保留、R2.2 planned、新增行禁词 0 | 0.172 |
| commit2-diff-check | `git diff --check` | 0 | 0.004 |

完整 `-c` 脚本保存在 raw.command，未创建或留下 throwaway 脚本。report stem 为 `<label>-contract_v2.1.0-rc.2-r2.2-statistics-507-<YYYYMMDDTHHMMSSffffff>`；red `20261024T092701850720`，golden `20261024T092709073332`，smoke `20261024T092749231292`，consumers `20261024T092749430360`，full `20261024T092916273430`。suite 互相重叠，不累计通过数。

### 失败与未执行边界

- 全量唯一失败：`test_stats_query.NormalizeScopeTests.test_iana_queries_and_dst_work_without_system_timezone_data`；子进程明确 `ModuleNotFoundError: No module named 'tzdata'`，继而 Asia/Tokyo 不可解析。不是新增契约测试失败，不修改 runtime 或测试以绕过。编排方整理的 fallback `/workspace/640-skills/ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/reports/renderer-venv/bin/python3 -B -c 'import sys, tzdata, yaml, jsonschema; ...'` 实际 exit 127（command not found）；随后 read 返回 Path not found，路径存在性检查也为 false。未写其他 worktree、未安装依赖；依赖恢复后的定向／全量复跑未执行。
- consumers 的 3 skips 均明确为 `SBTD_RENDERER_TEST_HOME is unset or has no browsers/ install`；全量原生简略输出只给总计 10 skips，不猜逐例原因。全量 stdout 披露 Playwright 缺失时既有 worker stub；不将 suite 称为全真实浏览器验证。
- smoke 实际消费新增 query 507 引用，接受非默认配额三字段 JSON，拒绝缺 quota_bytes、多 export_id、错误 detail；移除新增 507 并恢复原描述后整份 YAML 等于 origin/main。此为契约消费者证明，不是 live query HTTP 507 或无副作用证明。
- `BDD: traceable`，持久 spec 路径为 `sbtd-runtime/spec/r1.0-contract-scenarios.md`；中文／英文关键词遵循现有约定。`Cross-repo context: contract-only`；`API Contract: verified`（声明与 schema）；`Mock Strategy: none`（新增测试）；`E2E Mode: contract-backed`。未运行浏览器／移动端／跨平台／根 CI，无新增 Gherkin runner。
- `Final Test Report: generated`；`Run Summary MD: generated`；`Targeted Rerun: passed`（507 red→green）；`Final Full Rerun: failed`（缺 tzdata）。本地检查不等同 PR review、CI、merge 或 release。

## 本地提交与恢复边界

1. `95284766652862826c13f98a4b69cb671699f133` — `docs(plan,task): backfill #164 (253dcec) merge (R2.2 statistics 507 contract commit 1)`；仅 plan 与旧 R2.2 task。
2. `1eaca41b8f29ed07521a7e8761275b3331e8fad7` — `contract(openapi): declare shared 507 for queryStatistics with golden coverage (R2.2)`；仅 OpenAPI、golden test、既有 spec。
3. `docs(task): record R2.2 statistics 507 contract verification`；仅本 task，自身 SHA 由最终输出给出，避免自引用。

前两次显式 `git add` 后 `git diff --cached --check` 均 exit 0；commit 2 后 `git diff origin/main --stat` 的已跟踪改动仅五条授权路径，新 task 在第三次提交纳入第六条。第三次只暂存本 task，报告与禁止路径不暂存。没有 push／PR／comment／merge／rebase／amend／force，不改 #164 正文，不写其他 worktree／全局配置。

`commit2-content-identity`：exit 0，墙钟 0.031s；三个提交 blob 与 `runtime-full` raw.hashes 及工作树逐一相同，是内容身份核验，不是新运行或 CI。OpenAPI SHA-256 `3c00768ce9e2a44a8f81d0886fb491ede0a2edd1a66fd9538e4f25475a4e2d72`；golden test `e5be268ea1df319329aa5b87e9b552df0ba54e37a97521c39ba0a82be32cef8b`；spec `a0513698dcbca72f5fbbfa71d7fb5a9eb9ff0da57e36aa6528d46c7d16984e66`。`model-precommit-snapshot`：exit 0，墙钟 0.035s；两份 raw 的完整 Python 命令均在 reports，时间 stem 分别 `20261024T093454367769` 与 `20261024T093454328380`。

撤回边界仅为本地契约／测试／文档提交，不涉及数据迁移或删除。后续仍需具备 tzdata 的环境复跑全量、契约 PR 的外部流程、再做 HTTP 507 小实现 PR 与 PR-4；本 task 按编排方整理保持 in-progress／completed_at null，R2.2 总行继续 planned。无长期 lesson 规则变化，不写 developer 身份或 lesson；不声称 TaskStore helper 或自动恢复已生效。

## 模型 PRE-COMMIT SNAPSHOT

取样时间 `2026-10-24T09:34:54+08:00`；只读当前 session JSONL，按 `type=message`／`message.role=assistant` 及其中 `type=toolCall` blocks 计数，不统计总 transcript 行数为请求数。主会话后续工具／编辑／提交／最终回复不在快照内；所有下表数值均为 PRE-COMMIT SNAPSHOT，非 FINAL。

| session | provider/model | thinkingLevel | assistant / toolCall | 日志行范围 | resolvedModelIsFallback |
|---|---|---|---|---|---|
| main／01a16b82-19e9-77bc-b832-c1a51bd1abfd | openai-codex/gpt-6-astra | high | 26 / 60（PRE-COMMIT SNAPSHOT） | 1–173 | false |
| ContractBoundaryReview | kimi-code/k3 | high | 17 / 19（PRE-COMMIT SNAPSHOT） | 1–64 | false |
| RecordBoundaryReview | kimi-code/k3 | high | 6 / 7（PRE-COMMIT SNAPSHOT） | 1–29 | false |

日志根 `/home/box/.omp/logs/640-rc2-r22-507-contract/main/session/`；主文件 `2026-10-24T01-24-10-857Z_01a16b82-19e9-77bc-b832-c1a51bd1abfd.jsonl`；两份子代理文件在同 stem 子目录，分别为 `ContractBoundaryReview.jsonl`、`RecordBoundaryReview.jsonl`。模型与 fallback 来自 model_change，thinking 来自 thinking_level_change；不推测 title-generation request／job-widget 次数，均未核实，不填 0。不使用 advisor。

## 第三次提交前检查（追加）

- `python3 -B -c <integrity_script>`（`commit3-integrity`，完整脚本在 raw.command）：task frontmatter 通过 Skill schema／FormatChecker、时间 +08:00、Markdown 可解析；旧 task 除 updated_at 原文不变、R2.2 总行 planned；仅授权路径；提取 diff 新增行并纳入尚未跟踪的新 task 后，禁用归因词匹配为 0。exit 0，墙钟 0.164s。
- `python3 -B -c <report_check>`（`report-integrity`）：当时已生成的 14 对报告均有九节中文汇总、无未填模板字段、exit／SHA／branch 与 raw 一致、ignored 且未跟踪；失败报告仍在。exit 0，墙钟 0.062s。该数目是取样时范围，不含本检查自身及之后生成的报告。
- `git diff --check` exit 0，0.003s；`git diff origin/main --stat` exit 0，0.007s，commit 2 后已跟踪五文件与授权集合一致，第三次仅新增本 task。两命令及原生输出也保存 raw／同 stem 中文汇总。
- 本记录 frontmatter 与事件保持 in-progress；全量环境失败没有被改写为 skipped 或 passed。仍未运行外部 CI／PR review／merge；当前交付只是三个本地提交与真实本地证据。
