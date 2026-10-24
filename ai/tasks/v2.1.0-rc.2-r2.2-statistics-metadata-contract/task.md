---
schema_version: 1
id: v2.1.0-rc.2-r2.2-statistics-metadata-contract
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：strict、CONTRACT/METADATA-ONLY；主会话唯一 writer／验证 controller，不使用 advisor，仅本地 commits 2、3。
status: done
branch: contract/v2.1.0-rc.2-r2.2-statistics-metadata
created_at: '2026-10-24T10:19:17+08:00'
updated_at: '2026-10-24T10:57:29+08:00'
completed_at: '2026-10-24T10:53:09+08:00'
---

# R2.2 HTTP-routed operations metadata contract

## 决定

- 用户 2026-10-24 10:11 群内确认（要单独开契约pr去修，修完后开507实现pr），Lord 记录
- 用户 2026-10-24 10:16 群内确认（1A 2A），Lord 记录
- 编排方整理：1A 删除已有 HTTP route 的 operation-level library marker，不发明替代值；2A 覆盖四个操作与 info summary。

## 范围与边界

- 编排方整理：仅 OpenAPI 元数据、一个既有风格 golden 测试、install-and-use.md 首段与本 task；不改 runtime、PRD、schemas、其他操作或 spec 场景文档。metadata-only，不新增运行行为；BDD 场景仅在本记录保留，不新增 .feature／runner。
- 编排方整理：commit 1 `c1f09bb` 与其 plan.md／statistics-507-contract/task.md 不修改；不 push／PR／comment／merge／rebase／amend／force，不写其他 worktree／全局配置。显式路径暂存，不暂存 reports、.omp-r12b-addendum.txt、ai/tasks/codex-verify/、.env*。
- 授权根 `/workspace/640-skills-stats-metadata-contract`，入口分支匹配、工作区干净，origin/main `9ceb53021aa5e90d6369eed037f0b05ab719e928`。目标路径 containment／无 symlink 已核对，reports 受 `.gitignore:4` 保护且未跟踪。
- 未完整调用 grill-with-docs：决定、元数据 seam 与范围明确，无领域歧义。沿用既有 statistics-507-contract/task.md 记录的 Markdown 持久化边界与 TaskStore catalog/frontmatter 限制；不重试已知失败，不写 active／index／ignore／身份，不声称 helper lifecycle 或自动恢复成功。
- 编排方整理：statistics/query HTTP handler 当前仅捕获 QueryScopeError（serve.py:535–538）；本次不声明或实现 HTTP 507 映射。

## 路由逐项核实

| operationId | method + path | serve.py 路由行 | handler 行 | 结论 |
|---|---|---|---|---|
| getMetricCatalog | GET /api/v1/metrics/catalog | 686 | metric_catalog:520–524 | path／method 匹配，修改元数据 |
| queryStatistics | POST /api/v1/statistics/query | 687 | statistics_query:526–544 | path／method 匹配，修改元数据，不声明 507 runtime mapping |
| getReportSnapshot | GET /api/v1/report-snapshots/{snapshot_id} | 693–697 | get_snapshot:546–555 | path／method 匹配，修改元数据 |
| getSnapshotDataset | GET /api/v1/report-snapshots/{snapshot_id}/dataset | 698–702 | get_snapshot_dataset:557–570 | path／method 匹配，修改元数据 |

## Book Gate Plan

| Gate | 客观触发／阶段 | 初始状态 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill／领域歧义，before-dev | not-needed；未完整 grill，无领域变化 |
| book-ddia-data-design | schema／共享数据／跨服务流变化，before-dev | not-needed；只改实现状态元数据，无 schema／数据流变化 |
| book-legacy-change-safety | 既有运行行为变化，before-dev | not-needed；runtime untouched |
| book-refactoring-pass | 生产代码编辑，before-dev | 已读；not-needed，只有契约文本／测试／文档，无生产代码编辑 |
| book-release-readiness | runtime／部署／发布变化，finish | not-needed；不涉及发布，不声明 release-ready |
| TDD／gherkin-bdd／ponytail | 公开契约元数据 seam，before-dev | 已加载；一个 subTest 测试，RED 后最小修改，无新抽象／依赖 |
| 独立 review／可读性 | 公开契约，check | 待只读独立检查；主会话唯一验证 controller，不使用 advisor |
| project-validation | 编排方整理的验收命令，check | 已加载；保存原生输出及同 stem 中文汇总，保留已知环境失败 |

## BDD 场景

中文正文、英文关键词，沿用既有约定；本次元数据契约的消费者是读取 OpenAPI 的客户端，不等于 runtime 新行为。

```gherkin
Scenario: 已有 HTTP 路由不再被描述为仅进程内实现
  Given 四个统计与快照读取操作已有匹配 method 和 path 的本地 HTTP 路由
  When 客户端读取 OpenAPI 中这些操作的实现状态与摘要
  Then 四个操作都没有 x-sbtd-implementation 标记且摘要不再否认 HTTP 服务
  And 包摘要说明已有本地 HTTP 路由并保留 R1.4 pins 与 exports 的版本边界
  And 未路由操作的 library 标记及其他契约结构保持不变
```

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-24T10:19:17+08:00 | planned | in-progress | 用户 2026-10-24 10:11 群内确认（要单独开契约pr去修，修完后开507实现pr），Lord 记录 | 编排方整理：独立契约任务，后续 507 实现不在本次范围。 |
| 2026-10-24T10:19:17+08:00 | in-progress | in-progress | 用户 2026-10-24 10:16 群内确认（1A 2A），Lord 记录 | 编排方整理：删除四个已路由操作的 library marker，并修正摘要。 |
| 2026-10-24T10:19:17+08:00 | in-progress | in-progress | 编排方整理：strict 模式与边界已保存，路由已逐项核实。 | 四项 path／method 匹配；仅本地 commits 2、3；PR 尚未开启。 |
| 2026-10-24T10:26:08+08:00 | in-progress | in-progress | 编排方整理：metadata RED→GREEN、消费者 smoke 与计划验证完成；本地独立检查无 findings。 | golden 63 passed；consumers 51／3 skipped；runtime 430／1 failure／10 skipped，缺 tzdata；validator／format／diff-check 通过；既有 I001 保留；尚未提交 commit 2，PR 未开启。 |
| 2026-10-24T10:28:08+08:00 | in-progress | in-progress | 编排方整理：commit 2 已本地提交，提交 blob 与全量被测内容一致；追加第三次提交前模型快照。 | `77563361077680a4f78e4d35371753fbc31a8aec`；三文件 SHA-256 与 runtime-full raw.hashes 一致；未重跑 CI，不外推缺 tzdata 的失败；PR 未开启。 |
| 2026-10-24T10:29:07+08:00 | in-progress | in-progress | 编排方整理：以本 task 的 commit 3 收束本地 commits 2、3；本地交付完成，任务保持开放，PR 尚未开启。 | commit 2 `77563361077680a4f78e4d35371753fbc31a8aec`；本提交只纳入 task；commit3-integrity exit 0，禁词新增行 0、schema／事件／14 对既有 raw＋中文汇总通过；全量缺 tzdata 失败与既有 I001 保留，不声明 CI／PR review／merge。 |
| 2026-10-24T10:53:09+08:00 | in-progress | done | 编排方整理：statistics metadata 契约 PR #166 已由 Lord squash 合并，回填合并完成状态；不改写历史事件或本地验证结论。 | PR [#166](https://github.com/KunoLu/640-skills/pull/166)；merge SHA `fcd835e397698ab3292d9d7614e1407ff7e0a465`；head SHA `073999fbbcb7087de202227fa538b752495b4595`；git committer `%cI` `2026-10-24T10:53:09+08:00`（本轮 git log 核实）；GitHub mergedAt `2026-10-24T10:53:09+08:00`（`2026-10-24T02:53:09Z`，编排方整理），两者相等但分别记录；合并前 CI 13/13 on `073999f`，run `40054585051`（编排方整理；本轮未重跑 CI）；Reviewy CLEAN @073999f（编排方整理）。 |

## 未决问题

- 未决，编排方整理：已有 HTTP server 后 info-level `x-sbtd-implementation: contract-only` 是否应调整？本次保持原值；既有 golden、r1_acceptance 与 r1.4 acceptance 锁定该值，不修改这些既有断言／说明。

## 逐 hunk old → new（编排方整理）

行号为 origin/main 旧行 → 本轮新行；其余 YAML 内容保持不变。

| 文件／行 | old | new |
|---|---|---|
| openapi.yaml:5 → 5 | `No server is implemented in this package; operations marked x-sbtd-implementation: library have in-process Python library surfaces under sbtd-runtime/.` | `serve.py serves the operations it routes over local HTTP; operations marked x-sbtd-implementation: library have only in-process Python library surfaces under sbtd-runtime/.`；前缀 `Contract draft for v2.1.0-rc.1.` 与完整 R1.4 pins／exports 句原样保留 |
| openapi.yaml:289 → 删除 | `x-sbtd-implementation: library`（getMetricCatalog） | 无此 key，不引入替代值 |
| openapi.yaml:290 → 289 | `Implemented as stats_query.serve_catalog (in-process, no HTTP server).` | `Implemented as stats_query.serve_catalog (served over HTTP by serve.py).` |
| openapi.yaml:309 → 删除 | `x-sbtd-implementation: library`（queryStatistics） | 无此 key |
| openapi.yaml:310 → 308 | `Implemented as stats_query.query over contract_eval.evaluate (in-process, no HTTP server).` | `Implemented as stats_query.query over contract_eval.evaluate (served over HTTP by serve.py).` |
| openapi.yaml:427 → 删除 | `x-sbtd-implementation: library`（getReportSnapshot） | 无此 key |
| openapi.yaml:428 → 425 | `Implemented as report_snapshot.SnapshotStore.get (in-process, no HTTP server).` | `Implemented as report_snapshot.SnapshotStore.get (served over HTTP by serve.py).` |
| openapi.yaml:449 → 删除 | `x-sbtd-implementation: library`（getSnapshotDataset） | 无此 key |
| openapi.yaml:450 → 446 | `Implemented as report_snapshot.SnapshotStore.dataset_page with snapshot-bound cursors; csv_export.serialize_csv walks the same full range (in-process, no HTTP server).` | `Implemented as report_snapshot.SnapshotStore.dataset_page with snapshot-bound cursors; csv_export.serialize_csv walks the same full range (served over HTTP by serve.py).` |
| install-and-use.md:3 → 3 | `sbtd-runtime/` 是 v2.1.0-rc.1 的「本地 API 包」：一个进程内 Python 库，不是服务。R1 没有 HTTP 服务、没有 Dashboard；OpenAPI（`contracts/openapi.yaml`）中未标 `x-sbtd-implementation: library` 的操作是 R2 契约，不是当前实现。 | `sbtd-runtime/` 是 v2.1.0-rc.1 起的「本地 API 包」：包含进程内 Python 库，`serve.py` 为其已路由的操作提供本地 HTTP 服务与 Dashboard；OpenAPI（`contracts/openapi.yaml`）中未标 `x-sbtd-implementation: library` 的操作已有 `serve.py` HTTP 路由或仍是 R2 契约，并非全部已实现。后接「本文覆盖」至行尾原样保留；标题不改 |
| test_golden_contracts.py:935 插入 → 935–963 | 无该测试 | 新增唯一 `OpenApiDraftTests.test_http_routed_operations_metadata_matches_serve_routes`，29 行；四个 operation 的 subTest 检查 path／method／operationId、marker absence 与不含旧否定摘要；info 不含旧否定声明；剩余 library 集合精确为 getTaskHistory、listEvents、queryTimeseries、createReportSnapshot |
| 本 task.md:1 → 新文件 | 不存在 | strict、in-progress 任务记录及 append-only 证据；不是运行时实现或发布记录 |

## Gate 执行结论（追加）

- TDD：沿用 OpenApiDraftTests 的公开契约元数据 seam；单个测试在未改 YAML 时 exit 1，四个 operation subTest 各因旧 library key 失败，另有 info summary failure；1 test／5 failure records，不将 subTest 数当 test 总数。最小 YAML／doc 修改后 golden 63 tests 全通过。
- grep `tests/` 与 `sbtd-runtime/tests/`：匹配 implementation marker、旧 no-server 摘要与四个 operationId；改前仅命中 golden:1299 与 r1_acceptance:205 的 info-level contract-only 断言，以及 R1.4 summary pin；无需迁移或削弱旧断言。
- Ponytail／Code Readability：仅一组显式路由 tuple、一个 subTest 循环及剩余集合检查，无新依赖、helper、抽象或无关 import 调整。path items 当前均为 operation dict，集合遍历适用。所有五个 Book Gate 保持其初始 not-needed 原因；无 production code／schema／部署改动。
- 本地独立只读检查：MetadataContractReview（契约／路由／测试）与 MetadataRecordReview（安装说明／归因／边界／初始任务）均返回 no findings、correct，confidence 分别 0.95／0.9；均未运行测试／lint／format、未写文件，不是 advisor、PR review、CI 或 merge。其快照为提交前源码与初始 task；此后的证据追加由主会话校验，不将追加内容冒充已独立检查。
- metadata-consumer-smoke 实际解析 YAML、JSON round-trip、AST 提取 serve.py Route 的 path／method，并将允许的元数据改动恢复后与 origin/main 全结构比较相等；安装说明只有第 3 行变化且「本文覆盖」后原文相同。证明契约消费者与路由声明一致，不是 live HTTP 或 507 mapping proof。
- BDD: traceable；中文正文／英文关键词，仅本 task 的场景，经上述 golden 测试验证。编排方整理：metadata-only 不新增 spec 场景文件，既有模块说明已明确不创建 .feature；未引入 runner。Cross-repo context: contract-only；API Contract: verified（元数据声明）；Mock Strategy: none（新增测试）；E2E Mode: contract-backed。

## 验证证据

环境：授权 worktree，Linux 6.12.94+／x64，`python3` 3.13.5。主会话唯一验证 controller；`rtk: skipped-for-report`，原生命令捕获 stdout／stderr／exit／wall time／完整 HEAD／三份被测文件 SHA-256。每轮本目录 ignored `reports/` 保存同 stem `.json` raw＋九节中文 `.md`，失败输出保留，不暂存。Evidence Source: developer-local；Source Revision: dirty；Environment Alignment: unverified；Evidence Publication: local-only。没有远端 CI／PR review／merge／发布。

所有 Python 命令环境为 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests`，使用 `python3 -B`；ruff 另设 `RUFF_NO_CACHE=true`。`-c` 完整脚本存在 raw.command，无 throwaway 脚本落盘。

| raw label | 命令 | exit／实际结果 | runner 秒 | wall 秒 |
|---|---|---|---|---|
| metadata-red | `python3 -B -m unittest test_golden_contracts.OpenApiDraftTests.test_http_routed_operations_metadata_matches_serve_routes -v` | 1（预期）；1 test、5 failure records | 0.053 | 0.171 |
| golden-green | `python3 -B -m unittest sbtd-runtime/tests/test_golden_contracts.py -v` | 0；63 passed（原有 62＋新增 1） | 0.321 | 0.433 |
| openapi-consumers | `python3 -B -m unittest test_r1_acceptance test_renderer_integration -v` | 0；51 tests，48 passed／3 skipped | 80.753 | 80.970 |
| runtime-full | `python3 -B -m unittest discover -s sbtd-runtime/tests` | 1；430 tests，419 passed／1 failure／10 skipped | 144.195 | 144.695 |
| metadata-consumer-smoke | `python3 -B -c <smoke_script>` | 0；YAML parse／JSON round-trip／四项真实 route AST／基线结构恢复／doc line3 边界 | 不适用 | 0.140 |
| openapi-validator | `/tmp/osv-venv/bin/openapi-spec-validator sbtd-runtime/contracts/openapi.yaml` | 0；`sbtd-runtime/contracts/openapi.yaml: OK` | 不适用 | 0.328 |
| ruff-format | `ruff format --check sbtd-runtime/tests/test_golden_contracts.py` | 0；`1 file already formatted` | 不适用 | 0.015 |
| ruff-check | `ruff check sbtd-runtime/tests/test_golden_contracts.py` | 1；仅既有 I001，19–30 行未修改 | 不适用 | 0.013 |
| diff-check | `git diff --check` | 0 | 不适用 | 0.005 |
| openapi-diff | `git diff origin/main -- sbtd-runtime/contracts/openapi.yaml` | 0；恰好 info summary＋四项 marker 删除／summary 改写 | 不适用 | 0.003 |
| scope-stat | `git diff origin/main --stat` | 0；五个已跟踪授权文件，含 commit 1 的 plan／旧 task；新 task 将由 commit 3 纳入第六个文件 | 不适用 | 0.005 |

报告 stem 为 `<raw label>-contract_v2.1.0-rc.2-r2.2-statistics-metadata-<timestamp>`；时间戳依次为 `20261024T102055132462`、`20261024T102137856583`、`20261024T102149450395`、`20261024T102310430962`、`20261024T102555841620`、`20261024T102555991756`、`20261024T102556327982`、`20261024T102556349375`、`20261024T102556369956`、`20261024T102556380269`、`20261024T102556388982`。各 suite 有重叠，计数不相加。

### RED／GREEN 原生输出摘要

完整 stderr／stdout 在上述对应 raw（包含每项 failure traceback／全部 golden case 名称）；以下仅摘录，不代替 raw。

```text
RED — operation='getMetricCatalog' ... FAIL
RED — operation='queryStatistics' ... FAIL
RED — operation='getReportSnapshot' ... FAIL
RED — operation='getSnapshotDataset' ... FAIL
AssertionError: 'x-sbtd-implementation' unexpectedly found
AssertionError: 'No server is implemented' unexpectedly found
Ran 1 test in 0.053s
FAILED (failures=5)
exit 1

GREEN — test_http_routed_operations_metadata_matches_serve_routes ... ok
Ran 63 tests in 0.321s
OK
exit 0
```

### 失败、跳过与发布边界

- 全量唯一失败 `test_stats_query.NormalizeScopeTests.test_iana_queries_and_dst_work_without_system_timezone_data`：原生 traceback 为 `ModuleNotFoundError: No module named 'tzdata'`，继而 `ZoneInfoNotFoundError: 'No time zone found with key Asia/Tokyo'`。编排方整理已说明的 box 环境失败；没有修复、额外安装、修改或跳过此测试，也未重复运行确认已知错误。
- consumers 的 3 skips 原因为 `SBTD_RENDERER_TEST_HOME is unset or has no browsers/ install`；全量简略输出给出总计 10 skips，不猜逐项原因。原生 stdout 明确 Playwright 未安装时既有 worker stub；不称全真实浏览器或 full-stack 通过。
- ruff I001 是原有 import block，仅 1 error，未修复无关格式。HTTP 507 实现、info-level marker 调整、浏览器／移动端／跨平台／CI／外部 PR review／merge 均未执行或不在范围。
- Final Test Report: generated；Run Summary MD: generated；Targeted Rerun: passed（新增测试 RED→GREEN）；Final Full Rerun: failed（缺 tzdata）。无新长期 lesson 规则，不写 developer 身份或 lesson；不声明 helper lifecycle／自动恢复成功。

## 本地提交与恢复边界

1. `c1f09bb0fdf4efaf3ab8c2f294f95ae8774f7499` — 已有 `docs(plan,task): backfill #165 (9ceb530) merge (R2.2 statistics metadata contract commit 1)`；本轮未改其两个文件。
2. `77563361077680a4f78e4d35371753fbc31a8aec` — `contract(openapi): drop stale library markers and no-HTTP summaries on routed ops (R2.2)`；仅 OpenAPI、golden test、install-and-use，3 files changed，35 insertions／10 deletions。显式三路径 `git add`、`git diff --cached --check`、`git commit` 均 exit 0。
3. 本记录提交 subject：`docs(task): record R2.2 HTTP metadata contract verification`；只包含本 task，自身 SHA 由最终输出给出，避免自引用。记录保持 in-progress／completed_at null，不把本地提交完成当作 PR 或发布完成。

`commit2-integrity` exit 0／wall 0.132s：仅授权路径，commit 1 两文件 byte-unchanged；新增行禁用归因词匹配 0；task 分支／模式／状态／+08:00／独立决定事件／Markdown 合法；AST 实数 baseline 62 → current 63 tests。raw stem 时间 `20261024T102739752042`。

`commit2-content-identity` exit 0／wall 0.041s，raw stem 时间 `20261024T102808835828`：commit 2 的三个 blob 与 `runtime-full` 被测文件逐一相同；这是内容身份核验，不是提交后测试重跑或 CI：

| 文件 | SHA-256 |
|---|---|
| sbtd-runtime/contracts/openapi.yaml | `c412d516aafad3b0d9208a153247035d984c628cec3735dfd45b557a64c1b4f2` |
| sbtd-runtime/tests/test_golden_contracts.py | `ab451b357bdb88655749f8f1223aa008ad2a9df1dd2a9ee108e12eda845928e6` |
| sbtd-runtime/docs/install-and-use.md | `eb5b598f20d1335a2784c47ab73ab59606509f7249c343d77dc0db07a0ade779` |

撤回边界为本地元数据／测试／文档提交，无 runtime／数据迁移／删除。后续 507 实现仍是独立工作；本轮未 push、开启 PR、评论、merge、rebase、amend 或 force，未写其他 worktree 或全局配置。缺 tzdata 全量复跑、info-level marker 未决问题与外部 PR 流程未完成，不隐去风险。

## 模型 PRE-COMMIT SNAPSHOT

取样时间 `2026-10-24T10:28:08+08:00`；只读本 session JSONL，按 `type=message`／`message.role=assistant` 与其中 `type=toolCall` blocks 计数，不把 transcript 行数当请求数。快照在 commit 2 后、commit 3 前；之后的工具、编辑、提交与最终回复不在范围，全部为 PRE-COMMIT SNAPSHOT，非 FINAL。

| session | provider/model | thinkingLevel | assistant / toolCall | 日志行范围 | resolvedModelIsFallback |
|---|---|---|---|---|---|
| main／01a16bb3-e63d-707e-9059-89a4beebf270 | openai-codex/gpt-6-astra | high | 17 / 45（PRE-COMMIT SNAPSHOT） | 1–141 | false |
| MetadataContractReview | kimi-code/k3 | high | 9 / 15（PRE-COMMIT SNAPSHOT） | 1–48 | false（两条同值 model_change） |
| MetadataRecordReview | kimi-code/k3 | high | 14 / 20（PRE-COMMIT SNAPSHOT） | 1–63 | false（两条同值 model_change） |

日志根 `/home/box/.omp/logs/640-rc2-r22-stats-metadata-contract/main/session/`；主文件 `2026-10-24T02-18-34-429Z_01a16bb3-e63d-707e-9059-89a4beebf270.jsonl`；子代理文件在同 stem 子目录，分别 `MetadataContractReview.jsonl`、`MetadataRecordReview.jsonl`。model／fallback 来自 model_change；thinking 来自 thinking_level_change。title-generation request／job-widget 次数不可考，不填 0。`model-precommit-snapshot` exit 0／wall 0.037s，raw stem 时间 `20261024T102808885049`，命令与原生输出已保留；不使用 advisor。

## 第三次提交前检查（追加）

- `python3 -B -c <final_check_script>`，`commit3-integrity` exit 0，wall 0.246s；raw stem 时间 `20261024T102906906384`。完整命令保存在 raw.command。核对授权文件集合、commit 1 两文件未改、新增行禁用归因词匹配 0、strict／branch／in-progress／null、+08:00、两个独立决定事件、Markdown、frontmatter／stateEvent schema＋FormatChecker、AST baseline 62 → 63。
- 当时已有 14 对 raw／同 stem 中文汇总的九节顺序、无未填模板字段、exit／SHA／branch 一致、ignored 且未跟踪；RED 与 full failure 原生证据保留。14 是取样范围，不含本检查自身之后生成的一对报告。RED 汇总区分 1 个失败 test 与 5 条 failure records，不将 subTest failures 从 test 总数直接相减。
- 后续只追加本检查结论和本提交对应的最后状态事件、更新 updated_at；旧事件原文不改。第三次提交仅显式暂存本 task；报告不入库。模型计数仍是上述 PRE-COMMIT SNAPSHOT，非 FINAL。
- 此交付完成的是本地契约元数据提交，不是 507 runtime 实现、PR、CI、merge 或 release。frontmatter 保持 in-progress／completed_at null，最后事件与本提交状态一致。
