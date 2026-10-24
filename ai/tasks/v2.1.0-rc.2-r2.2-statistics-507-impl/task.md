---
schema_version: 1
id: v2.1.0-rc.2-r2.2-statistics-507-impl
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：strict；主会话唯一 writer／验证 controller，不使用 advisor；只作本地提交。
status: done
branch: feat/v2.1.0-rc.2-r2.2-statistics-507
created_at: '2026-10-24T10:56:51+08:00'
updated_at: '2026-10-24T11:57:00+08:00'
completed_at: '2026-10-24T11:52:52+08:00'
---

# R2.2 statistics/query HTTP 507 实现

## 决定

- 用户 2026-10-23 16:44 群内确认（方案 1），Lord 记录
- 用户 2026-10-24 10:11 群内确认（要单独开契约pr去修，修完后开507实现pr），Lord 记录
- 编排方整理：先回填 #166，再回填 #134，再 TDD 实现／文档，最后提交本记录；不 push／PR／comment／merge／rebase／amend／reset／force。

## 范围与边界

- 授权根 `/workspace/640-skills-507-impl`，入口 HEAD／origin/main `fcd835e397698ab3292d9d7614e1407ff7e0a465`，分支匹配、工作区干净。只写本 worktree，不改全局配置。
- 编排方整理：仅将 statistics_query 中传播的 DiskQuotaExceeded 映射为既有三字段 HTTP 507；不改变配额、清扫、快照复用、scope 校验或 createExport。OpenAPI、所有 JSON schema、PRD、r1.0-contract-scenarios.md 保持不变；api.ts 仅注释。
- 路径 containment／无 symlink 与 reports ignore 已核实；报告不暂存，所有提交显式路径。旧任务 branch 保留历史绑定，仅按明确范围回填合并事实，不重绑定。
- 未完整调用 grill-with-docs：契约及既有调用链确定何时拒绝、使用哪个配额，无领域歧义。沿用 507-contract／metadata-contract task 的 Markdown 记录边界及已知 TaskStore catalog/frontmatter 限制，不重复已知失败，不写 active／index／ignore／身份；未运行 helper lifecycle，不声明自动恢复可靠。
- 本地提交授权与“final pushed tip”措辞不一致，按明确禁止 push 执行：最后记录描述本地 tip，任务保持 in-progress／completed_at null，等待外部 PR／CI／review／merge。

## Book Gate Plan

| Gate | 客观触发／阶段 | 初始状态 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill／领域歧义，before-dev | not-needed；未完整 grill，无领域变化 |
| book-ddia-data-design | 共享快照写入失败路径，before-dev | confirmed；见下方 Review，所有者／锁／清扫不变 |
| book-legacy-change-safety | 既有 HTTP 缺失错误映射，before-dev | needs-safety-net；先真实 HTTP RED，再进入 characterized |
| book-refactoring-pass | 既有生产代码编辑，before-dev | 待 RED 后 Review；预计无需重构 |
| book-release-readiness | runtime 行为变化，finish | 待全部验证后评审，不宣称发布就绪 |
| TDD／gherkin-bdd／ponytail | 已确认 HTTP seam，before-dev | 真实服务＋磁盘；沿用 unittest，不新增 runner／依赖 |
| 独立 review／可读性 | 公开 HTTP 行为，check | 待只读检查；不使用 advisor，不允许子代理写入／跑验证 |
| project-validation | 编排方整理的完整命令范围，check | 待执行；原生 raw 与同 stem 中文汇总，保留失败 |

## DDIA Data Design Review

Status: confirmed。

- Data owner and source of truth：SnapshotStore 管快照，ExportStore 在 `export_store.py:261` 复用其 quota；HTTP 层不拥有另一份配额。
- Write / read / failure paths：`serve.py:535–538` → `stats_query.py:203–215` → `report_snapshot.py:883–894` → `disk_quota.py:154–165`。scope 先校验；已有未过期匹配快照先返回；新建才 sweep、测 U、在 U > L 抛异常，写文件发生在后面。
- Consistency／idempotency：保留共享锁、复用及导出重放；无新预检、预留、重试或驱逐。
- Schema／migration／rollback：无数据格式或迁移；回退代码只恢复旧 HTTP 异常行为，不删除数据。
- Observability／tests：返回异常携带的整数 U／L；HTTP 507 精确 body、无新增文件、等于上限允许、超限复用 200、非法 scope 400。

## BDD 场景

中文正文、英文关键词，沿用仓库 Markdown 场景约定；编排方整理要求本 task 持久化，不新增 .feature／runner，不编辑受保护 spec。

```gherkin
Scenario: 新统计快照被共享配额拒绝
  Given snapshots/ 与 exports/ 清扫后占用 11 字节且有效上限为 10 字节
  When 已认证客户端 POST /api/v1/statistics/query 查询新的有效 scope
  Then 返回 507 且 body 恰为 detail DISK_QUOTA_EXCEEDED、used_bytes 11、quota_bytes 10
  And 不写入新快照文件

Scenario: 等于上限允许创建且超限仍可复用
  Given 共享占用恰为 10 字节且有效上限为 10 字节
  When 已认证客户端查询新的有效 scope
  Then 返回 200 并生成可读取快照
  When 创建后共享占用超限且客户端再次查询相同 scope
  Then 返回 200 和相同 snapshot_id 且不新增快照文件

Scenario: 非法 scope 先于配额拒绝
  Given 共享占用已经超限
  When 已认证客户端查询非法 scope
  Then 返回 400 且不写入快照文件
```

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-24T10:56:51+08:00 | planned | in-progress | 用户 2026-10-24 10:11 群内确认（要单独开契约pr去修，修完后开507实现pr），Lord 记录；用户 2026-10-23 16:44 群内确认（方案 1），Lord 记录 | 编排方整理：入口根／分支／干净基线已核实；strict、唯一 writer、本地提交边界明确。 |
| 2026-10-24T11:00:49+08:00 | in-progress | in-progress | 编排方整理：#166 与 #134 回填已分别本地提交；新增真实 HTTP 回归在未改 handler 时出现预期 RED。 | commit 1 `353cd34126c2b133745cb2724e50b7ef7c532f39`；commit 2 `cf052f2a1d63ae00ddd58e01948c4ff8df0425d0`；query-507-red exit 1，1 test／1 failure，`500 != 507 : b'Internal Server Error'`，400 优先检查已通过。 |
| 2026-10-24T11:08:13+08:00 | in-progress | in-progress | 编排方整理：最小异常映射后同一回归 GREEN，独立真实 HTTP smoke 通过。 | query-507-green exit 0，1 test passed；live-http-smoke exit 0，U=18／L=17 返回精确 507，无新快照；等值创建与超限复用 200，非法 scope 400，不同 scope 再次 507。 |
| 2026-10-24T11:14:37+08:00 | in-progress | in-progress | 编排方整理：实现与文档分别本地提交，全部计划命令执行完毕；保留环境失败，不记全绿或发布就绪。 | commit 3 `1e0db12498eac10f75e53e7c1478002e2532bef0`；commit 4 `f8be1e74dde10339129bd0bc09cece8f5ff146bb`；golden 63 passed；consumers 51／3 skipped；runtime 431／1 failure／10 skipped，缺 tzdata；dashboard 22 passed、static 无变更；ruff 两项通过；两项独立只读 review 无 findings。 |
| 2026-10-24T11:17:57+08:00 | in-progress | in-progress | 编排方整理：本地交付完成，最后提交仅收录本 task；保持 in-progress／completed_at null，等待外部 PR／CI／review，合并后才 done。 | commits 1–4 SHA 见本地提交；precommit-integrity-green exit 0，八条授权路径、禁词新增行 0、schema／时间／旧记录保留、25 对当时已有 raw＋中文汇总、被测内容等同提交 blob 均通过；本 task 不含自身 SHA；未 push／开启 PR，缺 tzdata 的全量失败仍保留，发布门 blocked。 |
| 2026-10-24T11:52:52+08:00 | in-progress | done | 编排方整理：statistics/query 507 实现 PR #167 已由 Lord squash 合并，按旧规则最后一次回填合并完成状态；不改写历史事件或本地验证结论。 | PR [#167](https://github.com/KunoLu/640-skills/pull/167)；merge SHA `9ced6680cd838b9a5a2d9602a4939d981321582d`；head SHA `95f4e8e86536b0188c13f812711831cf1ec88a4c`（SHA 与提交内容经本轮 git log 核实）；git committer `%cI` `2026-10-24T11:52:51+08:00`（本轮 git log 核实）；GitHub mergedAt `2026-10-24T11:52:52+08:00`（编排方整理），两者相差 1 秒，completed_at 使用 mergedAt，done 事件 at 与之相同；合并前 CI 13/13 on `95f4e8e`，run `40058443245`（编排方整理；本轮未重跑 CI）；Reviewy CLEAN @95f4e8e（编排方整理）。 |

## Gate 结论

- **Legacy Change Safety Review — characterized。** 修改前真实 `python -m serve` 子进程返回 500，RED 在 HTTP seam 失败；先验证非法 scope 400。保留新建／复用顺序、清扫、配额、export 与鉴权行为；安全网是新增真实进程／socket／磁盘回归及既有 quota、snapshot、renderer suites。没有新增 seam。
- **Refactoring Review — proceed，normal。** 生产改动仅 `serve.py:539–547` 九行异常映射；沿用 create_export 三字段 body，不引入 helper、依赖、重试或 HTTP 层配额预检。无 refactor needed，无借机 import 清理。
- **Ponytail／Code Readability。** 无可删除的过度抽象。回归是一条隔离的生命周期场景，使用既有 ServeProcess／request／pair／snapshot；环境 patch 只影响新子进程启动配置，不 mock 配额或 HTTP 响应。测试覆盖精确 body／整数类型／拒绝无文件／未知文件保留／等值准入／同 ID 复用。后续 smoke 另以两个目录真实文件证明共享计量与新 scope 再拒绝。
- **BDD: traceable。** 本 task 三个中文场景、英文关键词，由 `test_exports_http.ExportHttpTests.test_statistics_snapshot_quota_refusal_and_reuse` 追踪；无新 .feature／runner，受保护 spec 不动。Cross-repo context: not-needed（单仓本地 API）；API Contract: verified（queryStatistics 507 共享 response 与实现一致；旧 deferred 说明单列后续）；Mock Strategy: none（新增路径）；E2E Mode: backend-only。只改 TS 注释，没有 UI 逻辑变化，因此未运行浏览器／Mobile MCP、Playwright CLI、Maestro 或 UI 测试生成器。
- **独立只读 review。** HttpQuotaReview 覆盖 handler、调用链、测试、docs／api.ts；MergeRecordReview 覆盖两个回填提交的精确字段、时间、归因与 append-only。两者均 no findings／correct，confidence 0.92／1.0，无编辑／测试／lint／build，不是 advisor 或外部 PR review。review 返回文本个别旧行号不作准；源码触发点见本记录。#166 CI／Reviewy 仍只是编排方整理，不能由 reviewer 概述升级成本轮核实／重跑。新 task 的后续证据由主会话检查，不冒充已独立 review。
- **Release Readiness Review — blocked（发布门，不是本地交付遗漏）。** 影响 statistics/query 客户端；拒绝同步返回 507，不产生本次快照；复用、等值准入及 400 安全网通过。容量／背压／清扫／80% log-only 行为不变，runbook 为 install-and-use.md 共享配额节。无迁移、外部服务或部署；撤回边界为本地代码／测试／文档提交，不删除运行数据。所需验证均已执行，但 stats_query 定向与全量因缺 tzdata 失败，因此不能标 ready；需依赖具备的环境复跑，随后外部 PR／CI／review／merge。无可选门以虚构 owner acceptance 豁免。

## 验证证据

原生输出保存在本目录 ignored `reports/`；每份 raw 有同 stem 中文汇总。Evidence Source: developer-local；Evidence Publication: local-only；未执行远端 CI／PR review／merge／发布。

环境：Linux 6.12.94+／x64；Python 3.13.5，解释器 `/home/box/.local/venvs/project-validation/bin/python3 -B` 存在并使用。Python 命令均设 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests`；ruff 设 `RUFF_NO_CACHE=true`。rtk: skipped-for-report，原生 subprocess 把长命令 stdout／stderr 直接写文件，raw JSON 保存完整 command、exit、墙钟秒、date -Is 时间、完整 HEAD、四个被测文件 SHA-256。TMPDIR 与 npm cache 都位于本 worktree ignored reports 内。

Source Revision: dirty（含未提交 task）；Environment Alignment: unverified；Evidence Publication: local-only。完整 suites 执行时 HEAD 为 `f8be1e74dde10339129bd0bc09cece8f5ff146bb`；RED／GREEN 时 HEAD 为 `cf052f2a1d63ae00ddd58e01948c4ff8df0425d0`，由 raw.hashes 区分未提交 handler 内容。不是最终 task commit 的重跑，更不是 PR-head CI。

下表 Python 命令前缀为上述解释器 `-B`；suite 相互重叠，不累计通过数。

| raw label | 命令 | exit／原生计数 | runner 秒／wall 秒 |
|---|---|---|---|
| query-507-red | `-m unittest test_exports_http.ExportHttpTests.test_statistics_snapshot_quota_refusal_and_reuse -v` | 1（预期）；1 test／1 failure，500 != 507 | 4.036／4.227 |
| query-507-green | 同一命令 | 0；1 passed | 4.390／4.631 |
| live-http-smoke | `-c <smoke_code>`，完整脚本在 raw.command | 0；真实子进程＋HTTP＋两目录共享文件；无 mock | 不适用／4.028 |
| golden | `-m unittest sbtd-runtime/tests/test_golden_contracts.py -v` | 0；63 passed | 0.324／0.466 |
| openapi-consumers | `-m unittest test_r1_acceptance test_renderer_integration -v` | 0；51 tests，48 passed／3 skipped | 85.311／85.575 |
| test_serve | `-m unittest test_serve -v` | 0；14 passed | 7.002／7.135 |
| test_exports_http | `-m unittest test_exports_http -v` | 0；9 passed | 35.603／35.767 |
| test_disk_quota | `-m unittest test_disk_quota -v` | 0；14 passed | 0.600／0.816 |
| test_report_snapshot | `-m unittest test_report_snapshot -v` | 0；12 passed | 0.426／0.566 |
| test_stats_query | `-m unittest test_stats_query -v` | 1；25 tests，24 passed／1 failure | 0.352／0.466 |
| runtime-full | `-m unittest discover -s sbtd-runtime/tests` | 1；431 tests，420 passed／1 failure／10 skipped | 162.463／162.908 |
| npm-ci | dashboard 下 `npm ci` | 0；72 packages added，73 audited，0 vulnerabilities；未安装新声明依赖 | 不适用／1.620 |
| dashboard-typecheck | dashboard 下 `npx tsc --noEmit` | 0 | 不适用／1.971 |
| dashboard-tests | dashboard 下 `npm test` | 0；22 passed，0 failed／skipped | 0.155354／0.365 |
| dashboard-build | dashboard 下 `npm run build` | 0；tsc＋Vite build | Vite 1.00／2.848 |
| dashboard-artifacts | `python3 sbtd-runtime/dashboard/check_artifacts.py` | 0；3 files，260361 bytes，budget 524288 | 不适用／0.032 |
| dashboard-static-status | `git status --short -- sbtd-runtime/dashboard/static/` | 0；输出为空，comment-only 构建产物未变 | 不适用／0.008 |
| ruff-format | `ruff format --check sbtd-runtime/serve.py sbtd-runtime/tests/test_exports_http.py` | 0；2 files already formatted | 不适用／0.064 |
| ruff-check | `ruff check sbtd-runtime/serve.py sbtd-runtime/tests/test_exports_http.py` | 0；All checks passed! | 不适用／0.032 |
| diff-check | `git diff --check` | 0 | 不适用／0.008 |
| protected-contract-diff | `git diff origin/main --stat -- sbtd-runtime/contracts/openapi.yaml 'sbtd-runtime/contracts/**' docs/prd sbtd-runtime/spec/r1.0-contract-scenarios.md` | 0；输出为空 | 不适用／0.004 |
| scope-stat | `git diff origin/main --stat` | 0；当时七个已跟踪授权文件，本 task 在最后提交纳入第八个 | 不适用／0.016 |

报告 stem 为 `<label>-feat_v2.1.0-rc.2-r2.2-statistics-507-<date-Is 去冒号并将 + 替换为 _>`；每轮保留 `.json`、同 stem `.md`、`.stdout`、`.stderr`。RED `2026-10-24T110049_0800`；GREEN `2026-10-24T110751_0800`；smoke `2026-10-24T110813_0800`；全量 `2026-10-24T111120_0800`。原生完整命令及 traceback 在对应 raw；没有 throwaway 脚本文件需清理。

### 失败、跳过与后续

- 定向与全量唯一 failure 都是 `test_stats_query.NormalizeScopeTests.test_iana_queries_and_dst_work_without_system_timezone_data`：`ModuleNotFoundError: No module named 'tzdata'`，继而 `ZoneInfoNotFoundError: 'No time zone found with key Asia/Tokyo'`。两轮都是明确验收选集，不是为了重复确认已知故障；未安装、修复、修改或跳过该测试，没有其他 failure。
- consumers 的 3 skips 均为 `SBTD_RENDERER_TEST_HOME is unset or has no browsers/ install`；全量简略输出给出 10 skips，不猜逐项原因。既有 renderer suites 含 worker mock／可选真实浏览器 skip，不称全真实浏览器或 full-stack 通过。
- `.github/workflows/validation.yml:136–156` 的 dashboard-artifacts job 使用 npm ci／test／build、check_artifacts.py 与干净构建检查。本轮运行所有明确要求命令并仅检查 static 路径清洁；未运行整个 CI job 或独立 `npm audit --audit-level=high`，npm ci 自带 audit 结果见表。
- OpenAPI `sbtd-runtime/contracts/openapi.yaml:898–900` 与 `sbtd-runtime/spec/r1.0-contract-scenarios.md:185–187` 仍说 HTTP mapping deferred。这是受保护的历史描述，按边界不改；需要后续独立文档／契约修正。WHEN／WHICH quota 无实质歧义：OpenAPI 877–899、新建 admission 894、quota 154–165 证据一致；createReportSnapshot 的 reuse precedence 未定义不改写 statistics_query 的既有复用行为。
- PR-4 容量校准、跨平台／真浏览器、远端 CI／PR review／merge／release 不在本次本地交付范围。R2.2 总行保持 planned。没有新增长期 lesson 规则，不写 developer 身份或 lesson。
- Final Test Report: generated；Run Summary MD: generated；Targeted Rerun: passed；Final Full Rerun: failed（缺 tzdata）。没有 push，不能称 pushed tip；记录仅描述本地交付。

## 本地提交

1. `353cd34126c2b133745cb2724e50b7ef7c532f39` — `docs(plan,task): backfill #166 (fcd835e) merge (R2.2 statistics 507 impl commit 1)`；仅 plan 与 metadata-contract task。
2. `cf052f2a1d63ae00ddd58e01948c4ff8df0425d0` — `docs(task): record R1.2b host adapters done via #134 (f2bd1fe)`；仅 R1.2b task。
3. `1e0db12498eac10f75e53e7c1478002e2532bef0` — `feat(serve): map statistics/query snapshot DiskQuotaExceeded to 507 (R2.2)`；仅 serve.py 与 test_exports_http.py。
4. `f8be1e74dde10339129bd0bc09cece8f5ff146bb` — `docs(runtime,dashboard): note statistics/query 507`；仅 install-and-use.md 与 api.ts 注释。
5. 最后提交 `docs(task): record R2.2 statistics 507 implementation verification`，仅本 task。task 无法包含自身 SHA，最终输出给出，避免自引用。

四次显式暂存与 `git diff --cached --check` 均 exit 0。所有报告／npm cache／node_modules 不暂存；没有改 .env、codex-verify、.omp-r12b-addendum.txt、其他 worktree 或全局配置。撤回只需处理本地提交，不涉及数据迁移或删除；未执行任何撤回或远端操作。

## 模型 snapshot

PRE-COMMIT SNAPSHOT，非 FINAL。仅统计当前会话日志的 `type=message`／assistant 与 message.content 的 toolCall blocks，不把总行数当请求数；后续编辑／检查／提交／最终回复不在快照内。不使用 advisor。

| session | provider/model | thinkingLevel | assistant / toolCall | 日志行范围 | resolvedModelIsFallback |
|---|---|---|---|---|---|
| main／01a16bd6-cb97-72b7-abbc-4a292e3a3385 | openai-codex/gpt-6-astra | high | 25 / 75 | 1–212 | false |
| HttpQuotaReview | kimi-code/k3 | high | 22 / 32 | 1–95 | false |
| MergeRecordReview | kimi-code/k3 | high | 8 / 7 | 1–31 | false |

证据：`model-precommit-snapshot` raw，exit 0／0.064s，完整日期与计数脚本在 raw；日志根 `/home/box/.omp/logs/640-rc2-r22-507-impl/main/session/`，主文件 `2026-10-24T02-56-41-367Z_01a16bd6-cb97-72b7-abbc-4a292e3a3385.jsonl`，子代理在同 stem 子目录。provider/model、fallback、thinking 取自 model_change／thinking_level_change；其他未取样调用信息不可考。

## 最后提交前完整性检查

- `precommit-integrity-green`：exit 0／0.265s。检查八条授权路径（含未跟踪 task）、diff 新增行禁词 0；三个 task frontmatter 通过 Skill schema／FormatChecker、时间 +08:00；旧 task 仅指定 frontmatter 修改及一条事件追加，Codex real smoke 段原文保留。
- OpenAPI／contracts／PRD／受保护 spec diff 为空；api.ts 去掉块注释后与 origin/main 相同。全量报告 raw.hashes 的四个生产／测试／文档文件与工作树及 HEAD blob 逐一相同；这是内容身份核验，不是重复测试或 CI。
- 当时已有 25 对 raw／同 stem 中文汇总通过九节结构、退出码／分支／SHA 对应及 ignored／untracked 检查，不含该检查自身与后续报告。失败轮全部保留。dashboard 汇总补录其原生 TAP 计数 22 passed，不改 raw。
- 两次临时检查脚本失败也保留：`precommit-integrity` exit 1／0.033s 为命令字符串换行转义 SyntaxError；`precommit-integrity-corrected` exit 1／0.266s 为按文本行识别标题误计 fenced command 内文本。改用现有 MarkdownIt 结构解析后通过；均非产品或测试 suite 失败，没有增加依赖或持久脚本。
- 本记录仅本地证据，不声称 TaskStore helper lifecycle、自动恢复、CI、PR review、合并或发布通过。后续授权流程需保留本次环境失败与契约 deferred 描述修正事项。
