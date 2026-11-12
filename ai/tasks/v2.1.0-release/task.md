---
schema_version: 1
id: v2.1.0-release
workflow_mode: strict
mode_source: user
mode_note: 用户 2026-11-12 07:26 群内确认按甲开始 v2.1.0 正式版；Lord 调度本项沿用先写 task.md、Reviewy 对完整 SHA 给 CLEAN、CI 13/13 再 squash 合入的流程。
status: checking
branch: docs/v2.1.0-release
created_at: '2026-11-12T08:10:32+08:00'
updated_at: '2026-11-12T14:49:51+08:00'
completed_at: null
---

# v2.1.0 正式版文档与发布身份

## 目标与本轮边界

本 PR 做 v2.1.0 正式版的文档与发布身份：README 发布身份与安装 tag、双语 CHANGELOG（rc.5 补发布身份段、新增 v2.1.0 一节）、契约发布标记与配套身份文字、相关测试钉。

第 1 轮只建立本 task.md，以及正式生成器更新的 `ai/tasks/index.md`。文档正文、契约发布标记和测试钉留待后续实现轮；本轮不实现、不提交、不推送、不开 PR、不打 tag、不发 Release，不运行 Git 写命令。提交由编排方稍后处理。不建立 active、handoff、developer 或其他工作流记录。保持 checking，completed_at 为 null。

第 2 轮按计划改完全部生产文件（README 中英、CHANGELOG 中英、5 个契约文件、3 个测试文件的发布身份与测试钉），定向测试 104 项已通过，但会话在后续命令 Deadline exceeded 后结束，未回填本记录、未跑完剩余验证。第 3 轮补跑定向测试、根工作流测试与 index 复核后，云主机重启导致会话中断，全量单测结果丢失（见状态事件）。第 4 轮补完全部剩余验证（含全量单测与基线对照）并回填本记录。第 2、3、4 轮同样不提交、不推送、不开 PR、不打 tag、不发 Release；提交与 PR 由编排方处理。

未完整调用 grill-with-docs：边界明确，当前源码与已核实背景能回答本轮问题，不新增领域决定。

## 决策来源

- 2026-11-12，Lord 在 main `c4227666e2127eca70af591f2e83ad35d7d8bcb6` 上打了注释 tag `v2.1.0-rc.5`（tag 对象 `328b875a8af6eee2cf03c250b4ac17208e6f6531`），并发布预发布 Release（https://github.com/KunoLu/640-skills/releases/tag/v2.1.0-rc.5）。该提交上的 CI 是 [43073411484](https://github.com/KunoLu/640-skills/actions/runs/43073411484)，只跑了一次，13/13 个 job 按名字全部 success，于 2026-11-12T02:12:14+08:00 跑完。Release 标成预发布，不标 Latest；当时 Latest 仍是 v2.0.2。此前的自动推进授权到此结束。
- 用户 2026-11-12 07:15 群内确认（impeccable 的上游 issue 要发，但先给 640 看草稿，点头后再发；v2.1.0 正式版发布说明里要写上这 4 个已知上游问题。正式版本身仍须另行授权），Lord 记录。未提供精确到秒的时刻。
- 用户 2026-11-12 07:18 群内确认按已审草稿原文发出，Lord 记录。未提供精确到秒的时刻。
- Lord 已按该草稿原文发出上游 issue [pbakaus/impeccable#1408](https://github.com/pbakaus/impeccable/issues/1408)，用账号 KunoLu 发出，标题和正文与草稿一致，创建时间 2026-11-12T07:19:31+08:00（GitHub 时间 2026-11-11T23:19:31Z）。本 PR 不再起草或重发该 issue，只在正式版说明里引用已发出的链接。
- Researchy 核对该草稿引用属实，并提到一个可选补充：这 4 处在当时上游 main `b4bff162` 上还在。Lord 说明 issue 已按 640 确认过的原文发出，那句可选说明没有加进去；要补得 640 点头后才能在 #1408 下追加评论。本 PR 不追加该评论，也不把这句可选说明写进 CHANGELOG，除非 640 另行确认。
- 用户 2026-11-12 07:26 群内确认（契约里的版本标记只改成 `v2.1.0`，不改字段和状态码；按此口径开始 v2.1.0 正式版），Lord 记录。未提供精确到秒的时刻。
- 随后 Lord 群内调度 @OMP 开始正式版文档 PR，先写 task.md；写完先报群，再实现、开 PR。tag 和 Release 先不要打；合入后双语发布说明和 tag 注释还要给 Reviewy 审，对上完整 SHA、CI 13/13 和两份文件原文再打。这是 Lord 的调度，不是用户提出的实现方案。
- Reviewy 赞成甲：只把那些 rc 号改成 `v2.1.0`，字段和状态码不动。并补流程：文档 PR 合入后，双语发布说明和 tag 注释也要先给 Reviewy 审，对上完整 SHA、CI 13/13，并把结论绑到那两份文件的原文后再打 tag，跟 rc.5 一样。已知限制按说明写上即可，不必这次补做。
- Researchy 对照当前 main `c4227666`（即 rc.5 tag 指向的提交）核实：README 中英文第 19、33 行还是 v2.0.2；CHANGELOG 中英文 rc.5 标题还写着未发布；契约里的版本标记对得上；`manifest_version` 是 `1.1.0`，graft 仍是 0.28.0；还没有 `v2.1.0` 这个 tag。并指出选甲必须一并改的配套项：`openapi.yaml` 顶部摘要句、`data-dictionary.md` 标题、`test_golden_contracts.py` 与 `test_panel_manifest.py` 断言；改 `panel-manifest.json` 的 `release` 后 `EXPECTED_MANIFEST_SHA256` 会变，只更新哈希钉，不升 `manifest_version`；refresh 断言对照 `c4227666` 核实比的是该字段不存在，应改成断言字段不存在。
- 调度后 Lord、Reviewy、CodeX、Researchy 补充口径：`openapi.yaml` 顶部摘要里 “Contract draft for v2.1.0-rc.1” 和 “exports* stay v2.1.0-rc.2” 改成正式版口径；`data-dictionary.md` 标题里的 `v2.1.0-rc.1` 改成 `v2.1.0`；`test_golden_contracts.py`、`test_panel_manifest.py` 里对着这些 rc 号的断言一起改；`test_r1_acceptance.py:189` 把导出接口的 `x-sbtd-release` 钉在 `v2.1.0-rc.2`，要改成 `v2.1.0`；测试失败提示可能写着顺手升 `manifest_version`，这次不升，仍保持 `1.1.0`，只改哈希；refresh 断言不补字段、不只改比较值，改成断言该字段不存在；Researchy 已扫过 `sbtd-runtime/tests` 和仓库根目录 `tests/`，除这三个测试文件没有别的断言再钉这些 rc 号；情景文档、ADR、PRD，以及 `outside-v2.1.0-rc.1-core-subset` 这类历史用语不是发布号，这次不用改；OpenAPI 的 `info.version: 1.0.0`、能力表里的历史证据路径、ADR 文件名不要动；字段和状态码一律不动。
- 用户 2026-11-12 08:02 群内确认（主模型改用 k3:max），Lord 记录。本项主模型由 astra 改为 k3:max，原因：astra 三次尝试因 OpenAI 服务故障未能连上。
- 本轮之前有一次 k3:max 运行（2026-11-12 08:03 开始），因要按 08:02 确认改写依据措辞，开始后两分钟内被编排方中止，未写任何仓库文件；其会话日志已被编排方删除，调用次数无法统计。
- Lord 2026-11-12 09:23 群内确认：实现范围以 Reviewy 列的完整范围为准；refresh 断言不补字段、不只改比较值，改为断言该字段不存在；新节标题定选项一（`## v2.1.0 (Unreleased)`／`## v2.1.0（未发布）`，不放日期与 Release 链接）。未提供精确到秒的时刻。
- Lord 群内调度本任务实现轮起只用 k3:max；单次运行以 `--config` 覆盖关闭自动换模型（`retry.modelFallback: false`），不改 omp 全局配置。第 2 轮与第 4 轮均按此执行。
- 用户 2026-11-12 13:54 群内确认（改用 API key），Lord 记录。第 3 轮云主机重启后 Kimi Code 账号登录失效，第 4 轮起改用 Kimi Code API key，经启动参数传入。第 4 轮正式开始前有两次启动未成功（一次因账号登录失效、一次因未取到 key），均在任何模型调用前退出，未产生会话日志，模型调用 0 次。

群内事实、评审结论和远端操作采用本轮提供的已核实背景，不冒充本会话访问群聊或 GitHub 得到的证据。下面的文件行号与本地 Git 事实均为本轮亲自读取。

## 范围与非目标

范围：下表 1–8 项的文档与发布身份改动及配套测试钉更新。

非目标：契约／schema／PRD／ADR 决策内容（字段、状态码、方案、完成门）；OpenAPI `info.version`；`manifest_version`（保持 `1.1.0`）；能力表历史证据路径与 ADR 文件名；graft 版本、pin 与 Caveman pin；外部 skills 副本；补做 R2.2 大规模性能验证或浅色主题导出 CI；在 #1408 追加评论；打 tag 或发 Release。

若后续对照发现必须改契约／schema／PRD／ADR 的决策内容，把分歧记为开放问题并停止扩展范围，不借本 PR 改方案。本轮不改下表任何生产文件。

## 当前源码依据

基准 main：`c4227666e2127eca70af591f2e83ad35d7d8bcb6`（本分支 HEAD，起始工作区干净）。本轮 `git rev-parse` 核实：`v2.1.0-rc.5` 的 tag 对象为 `328b875a8af6eee2cf03c250b4ac17208e6f6531`，指向 `c4227666e2127eca70af591f2e83ad35d7d8bcb6`；`git tag -l` 只有 v2.1.0-rc.1 至 rc.5，无 `v2.1.0` tag。行号全部来自本轮读取，不沿用提示行号。

| 计划项 | 当前文件:行 | 现状摘要 | 后续是否改动 |
|---|---|---|---|
| 1. README 发布身份与安装 tag | `README.md:19,33`；`README.zh.md:19,33` | 英文横幅 “Latest stable v2.0.2 is released”、中文横幅“最新正式版 v2.0.2 已发布”；两处安装提示均从 v2.0.2 tag 安装 | 已改（第 2 轮）。发布身份与安装 tag 为 v2.1.0，不扩写其他段落；tag 由合入后的发布动作创建，本 PR 不打。第 4 轮核对行号：`README.md:19,33`、`README.zh.md:19,33` |
| 2. rc.5 节补发布身份 | `CHANGELOG.md:10`；`CHANGELOG.zh.md:10`；格式参照 `CHANGELOG.md:37`、`CHANGELOG.zh.md:37`（rc.4 发布身份段） | 两处 rc.5 标题仍写 “(Unreleased)”／“（未发布）”，无发布身份段；tag 已于 2026-11-12 创建并发布预发布 Release | 已改（第 2 轮）。标题补日期 2026-11-12 并按 rc.4 格式补发布身份段（Release 链接、tag 对象 `328b875a8af6eee2cf03c250b4ac17208e6f6531`、指向提交 `c4227666e2127eca70af591f2e83ad35d7d8bcb6`、CI 43073411484 的 13/13 与 2026-11-12T02:12:14+08:00 跑完）；未改写该节已有功能条目的历史事实。第 4 轮核对行号：`CHANGELOG.md:30-32`、`CHANGELOG.zh.md:30-32` |
| 3. 新增 v2.1.0 一节 | `CHANGELOG.md:3`、`CHANGELOG.zh.md:3`（文件头规则）；本轮 grep 确认两文件现有 `## v2.1.0` 标题仅 rc.1–rc.5 | 文件头写明：未发布章节在创建对应 tag 后补充发布日期 | 已改（第 2 轮）。按 Lord 2026-11-12 09:23 群内确认采用选项一：`## v2.1.0 (Unreleased)`／`## v2.1.0（未发布）`，无日期、无 Release 链接。第 4 轮核对行号：新节为 `CHANGELOG.md:10-28`、`CHANGELOG.zh.md:10-28` |
| 4. impeccable 已知上游问题与 graft 边界 | `CHANGELOG.md:28`、`CHANGELOG.zh.md:28`（rc.5 条目已记保持上游原样）；`CHANGELOG.zh.md:463`（v1.0.15 旧修复事实）；`ENTRYPOINT.md:25,91,239-242,330`（graft 0.28.0 pin） | rc.5 条目已记 rc.3 #197 去掉 v1.0.15 本地补丁、按授权保持上游原样不重打；graft pin 0.28.0 不变 | 已改（第 2 轮）。新 v2.1.0 一节已写 4 个已知上游问题并附 #1408 链接，说明保持上游原样、不打本地补丁；说明 graft 仍是 0.28.0、不用动。4 项内容与已发出的 issue 和先前源码记录一致，未编造新的复现。第 4 轮核对：`CHANGELOG.md:18-28`、`CHANGELOG.zh.md:18-28`；`ENTRYPOINT.md` 未改 |
| 5a. 契约发布标记 | `sbtd-runtime/contracts/openapi.yaml:7`（`info.x-sbtd-release: v2.1.0-rc.1`）；`openapi.yaml:609,650,673,700`（四个导出 operation `x-sbtd-release: v2.1.0-rc.2`）；`sbtd-runtime/contracts/capability-matrix.json:3` 与 `sbtd-runtime/contracts/metrics-catalog.json:4`（`release` 为 `v2.1.0-rc.1`）；`sbtd-runtime/contracts/panel-manifest.json:4`（`release` 为 `v2.1.0-rc.2`） | 均为 rc 发布号 | 已改（第 2 轮）。这些发布标记均为 `v2.1.0`，字段和状态码未改；`manifest_version` 保持 `1.1.0`。第 4 轮核对行号：`openapi.yaml:7,609,650,673,700`、`capability-matrix.json:3`、`metrics-catalog.json:4`、`panel-manifest.json:4`（`manifest_version` 在 `panel-manifest.json:3`） |
| 5b. 配套身份文字 | `sbtd-runtime/contracts/openapi.yaml:5`（summary 含 “Contract draft for v2.1.0-rc.1” 与 “exports* stay v2.1.0-rc.2”）；`sbtd-runtime/contracts/data-dictionary.md:1`（标题含 `v2.1.0-rc.1`） | 同一套发布身份的配套文字；不改属决策，属发布身份对齐 | 已改（第 2 轮）。改成正式版口径：summary 现为 “Contract for v2.1.0. … exports* stay v2.1.0”，标题现为「SBTD Runtime 数据字典（v2.1.0 / R1.0）」。第 4 轮核对行号：`openapi.yaml:5`、`data-dictionary.md:1` |
| 5c. 不动的版本字样 | `sbtd-runtime/contracts/openapi.yaml:4`（`version: 1.0.0`）；`sbtd-runtime/dashboard/artifact-budget.json:3`（`set_by` 指向 ADR 0002 文件名）；`docs/adr/0001-v2.1.0-rc.1-r1.0-runtime-decisions.md`、`docs/adr/0002-v2.1.0-rc.2-r2.0a-dashboard-frontend-decisions.md` 文件名与正文；`docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md:9,1367-1369,1677-1679` | `info.version` 不是仓库发布号；ADR 文件名与能力表历史证据路径属历史事实；PRD 的 rc.1／rc.2 阶段定义是历史记录，且第 9 行已写目标发布 v2.1.0 | 不改。第 4 轮核对：`openapi.yaml:4` 仍为 `version: 1.0.0`；`artifact-budget.json`、两个 ADR 文件名与正文、PRD 三处均未在 git diff 中 |
| 5d. 核对后不改的同类命中 | `sbtd-runtime/contract_eval.py:195`（`outside-v2.1.0-rc.1-core-subset` 原因码）；`sbtd-runtime/stats_query.py:107`（group_by 未实现的错误文案，属 rc.1 核心子集范围事实）；`sbtd-runtime/docs/install-and-use.md:3,96,112,116`；`sbtd-runtime/docs/host-adapters.md:62,144`；`sbtd-runtime/docs/r1.4-acceptance-report.md:3,5,40`；`sbtd-runtime/spec/r1.0-contract-scenarios.md:137`、`sbtd-runtime/spec/r1.3-stats-api-scenarios.md:3`、`sbtd-runtime/spec/r1.4-acceptance-scenarios.md:3,109-110`；`docs/prd/sbtd-workflow-v2-task-status-sync.md:17,117` | 历史起点／范围叙述、情景文档、验收报告与证据路径；按调度后补充口径这次不改 | 不改。第 4 轮核对：这些文件均未在 git diff 中。若独立评审认为其中某处属当前发布身份，记开放问题并停止扩展 |
| 6a. golden contracts 断言 | `sbtd-runtime/tests/test_golden_contracts.py:1418,1420,1422` | 1418 断言导出 operation 的 `x-sbtd-release` 为 `v2.1.0-rc.2`；1420 断言 `info.x-sbtd-release` 为 `v2.1.0-rc.1`；1422 为 `assertNotEqual(refresh.get("x-sbtd-release"), "v2.1.0-rc.2")` | 已改（第 2 轮）。1418／1420 断言为 `v2.1.0`；1422 按 09:23 确认改为 `assertNotIn("x-sbtd-release", refresh)`，即断言字段不存在，未补字段、未只改比较值。第 4 轮核对行号不变：`test_golden_contracts.py:1418,1420,1422` |
| 6b. panel manifest 断言 | `sbtd-runtime/tests/test_panel_manifest.py:96`；`:81-84` | 96 断言 `release == "v2.1.0-rc.2"`；81 行 `EXPECTED_MANIFEST_VERSION = "1.1.0"`；82-84 行 `EXPECTED_MANIFEST_SHA256` 钉内容哈希 | 已改（第 2 轮）。96 断言 `v2.1.0`；82-84 的 SHA256 钉更新为 `57d94cb9018a7e544d6ea8010b255c43993b19587825e1652d7040399576749f`，`manifest_version` 保持 `1.1.0` 未升。第 4 轮用测试内同一算法（`json.dumps` sort_keys、紧凑分隔符、UTF-8 后 sha256）亲自重算，与该钉一致；核对行号：`test_panel_manifest.py:81-84,96` |
| 6c. r1 acceptance 断言 | `sbtd-runtime/tests/test_r1_acceptance.py:189` | 断言导出 operation 的 `x-sbtd-release` 为 `v2.1.0-rc.2` | 已改（第 2 轮）。断言为 `v2.1.0`。第 4 轮核对行号不变：`test_r1_acceptance.py:189` |
| 6d. 同类断言检索 | 本轮 grep `v2\.1\.0-rc` 覆盖 `sbtd-runtime/tests/` 与根 `tests/`；另检索 `"v2.1.0"` 字面量 | rc 断言命中仅上述三个测试文件；根 `tests/` 无命中；无测试钉 plain `v2.1.0` | 第 4 轮复核：grep `v2\.1\.0-rc` 覆盖 5 个契约文件与 3 个测试文件，无作为当前发布身份的 rc.1／rc.2 残留；`capability-matrix.json` 内残留命中均为 `ai/tasks/v2.1.0-rc.5-host-gate-codex-0167-omp-18188/`、`ai/tasks/v2.1.0-rc.1-r1.2b-host-adapters/` 等历史证据路径，按口径不改。与 Researchy 扫描结论一致，无其他同类断言需列入 |
| 7. 已知限制现有表述 | `CHANGELOG.md:75-76`、`CHANGELOG.zh.md:75-76`（rc.3 候选边界节）；原始完整表述 `CHANGELOG.md:118-121`、`CHANGELOG.zh.md:118-121`（rc.2 节）；rc.5 节（`CHANGELOG.md:10-33`）无候选边界小节 | R2.2 大规模性能验证等待验证项、浅色主题导出无 CI 覆盖等自 rc.2 起延续 | 已改（第 2 轮）。新 v2.1.0 一节「Candidate Boundaries and Known Limitations」／「候选边界与已知限制」按原意续写这些已知限制，写明系 rc.2/rc.3 延续、非 rc.5 或本发布新欠，不列入实现工作。第 4 轮核对：`CHANGELOG.md:26-28`、`CHANGELOG.zh.md:26-28` |
| 8. graft 边界 | `ENTRYPOINT.md:25,91,239-242,330` | graft 仍可选、pin 0.28.0 | 不改。第 4 轮核对：`ENTRYPOINT.md` 未在 git diff 中，graft 版本、pin 与安装器均未动；新节已写明 graft 仍可选、pin 保持 0.28.0 的边界说明 |

对照后未发现必须改契约／schema／PRD／ADR 决策的开放问题。第 4 轮复核全部改动后此结论不变；第 4 轮全量单测 2 项失败：基线 `c4227666` 临时 worktree 上用同型命令复跑，这 2 个用例同样失败（`test_runtime_perf_smoke.py` 2 项 1 失败，`test_stats_query.py` 25 项 1 失败），失败栈均指向 zoneinfo 无法加载 Asia/Tokyo；本机未装 tzdata（`import tzdata` ModuleNotFoundError），CI 经 `sbtd-runtime/requirements-serve.txt:8` 钉装 `tzdata==2026.5`。本 PR 未改动这两个测试及其被测代码（`git diff --stat` 核实，改动仅 13 个计划内文件），不构成开放问题。

## v2.1.0 一节标题写法推荐

- 选项一（推荐）：先写「## v2.1.0 (Unreleased)」／「## v2.1.0（未发布）」，不写 Release 链接；合入后打 tag 时再补日期与链接。理由：`CHANGELOG.md:3`／`CHANGELOG.zh.md:3` 的文件头规则写明未发布章节在创建对应 tag 后补日期；本 PR 不打 tag，合入后才会打，先写日期或链接会把尚未存在的 tag／Release 写成已发布，且链接在合入时是死链。
- 选项二：按授权当天写成 2026-11-12 并预留 https://github.com/KunoLu/640-skills/releases/tag/v2.1.0 链接。风险：本 PR 合入时该 tag／Release 尚不存在，与文件头规则冲突。

## 后续实现计划与预期将改的文件

第 2 轮已按下表改完全部预期文件；第 4 轮逐一重读核对，与计划一致、无基线漂移，行号见上表「后续是否改动」列。下表保留为计划与实际的对照记录。

| 相对仓库路径 | 后续预期改动 |
|---|---|
| `README.md`、`README.zh.md` | 第 19／33 行发布身份与安装 tag 对齐 v2.1.0 |
| `CHANGELOG.md`、`CHANGELOG.zh.md` | rc.5 标题补日期 2026-11-12 并按 rc.4 格式补发布身份段；新增 v2.1.0 一节（含 impeccable 4 项与 #1408、保持上游原样不打本地补丁、graft 仍 0.28.0、既有已知限制按原意续写）；不改写已有功能条目的历史事实 |
| `sbtd-runtime/contracts/openapi.yaml` | 第 5 行摘要改正式版口径；第 7 行与 609／650／673／700 行发布标记改 `v2.1.0`；`info.version` 不动 |
| `sbtd-runtime/contracts/capability-matrix.json`、`sbtd-runtime/contracts/metrics-catalog.json` | 第 3／4 行 `release` 改 `v2.1.0` |
| `sbtd-runtime/contracts/panel-manifest.json` | 第 4 行 `release` 改 `v2.1.0`；`manifest_version` 保持 `1.1.0` |
| `sbtd-runtime/contracts/data-dictionary.md` | 第 1 行标题改 `v2.1.0` |
| `sbtd-runtime/tests/test_golden_contracts.py` | 1418／1420 改 `v2.1.0`；1422 改成断言 refresh 无该字段 |
| `sbtd-runtime/tests/test_panel_manifest.py` | 96 改 `v2.1.0`；82-84 的 SHA256 钉按新内容更新；81 不动 |
| `sbtd-runtime/tests/test_r1_acceptance.py` | 189 改 `v2.1.0` |
| `ai/tasks/v2.1.0-release/task.md`、`ai/tasks/index.md` | 记录后续真实轮次与证据；index 仅由正式生成器维护 |

实现边界均已兑现：未改字段与状态码；未改 `manifest_version`、`info.version`；未改历史证据路径与 ADR 文件名；未把尚未打出的 v2.1.0 tag／Release 写成已经发布；未改写已发布历史事实。

## 验收标准（第 4 轮逐条核对结果）

1. README 中英发布身份与安装 tag 为 v2.1.0 —— 已达成：第 2 轮改，第 4 轮核对 `README.md:19,33`、`README.zh.md:19,33`；tag 尚未打，由合入后的发布动作创建，文案未把 tag／Release 写成已存在。
2. rc.5 CHANGELOG 已补日期 2026-11-12 与 Release 链接等发布身份，且未改写已有功能条目事实 —— 已达成：`CHANGELOG.md:30-32`、`CHANGELOG.zh.md:30-32`。
3. 新增 v2.1.0 一节含 impeccable 4 个已知上游问题、#1408 链接、保持上游原样不打本地补丁、graft 仍 0.28.0，以及既有已知限制（R2.2 大规模性能验证、浅色主题导出 CI 覆盖等）按原意续写 —— 已达成：`CHANGELOG.md:10-28`、`CHANGELOG.zh.md:10-28`，标题为选项一（无日期、无链接）。
4. 指定发布标记（openapi info 与四个导出 operation、capability-matrix、metrics-catalog、panel-manifest 的 `release`）与配套身份文字（openapi 摘要、data-dictionary 标题）改为 `v2.1.0` —— 已达成：`openapi.yaml:5,7,609,650,673,700`、`capability-matrix.json:3`、`metrics-catalog.json:4`、`panel-manifest.json:4`、`data-dictionary.md:1`。
5. `manifest_version` 仍为 `1.1.0`；字段和状态码未改；`info.version` 未改 —— 已达成：`panel-manifest.json:3` 为 `1.1.0`，`openapi.yaml:4` 为 `version: 1.0.0`；git diff 仅含发布身份文字与测试钉。
6. 相关测试钉已更新（refresh 改为断言字段不存在、SHA256 钉更新）且指定测试通过 —— 已达成：`test_golden_contracts.py:1422` 为 `assertNotIn("x-sbtd-release", refresh)`；`test_panel_manifest.py:82-84` 哈希钉经第 4 轮用测试内同一算法重算一致；定向测试 104 项在第 2、3、4 轮均 OK、退出 0。
7. 未打 tag、未发 Release —— 已达成：第 1 轮核实无 `v2.1.0` tag；第 2、3、4 轮均未提交、未推送、未开 PR、未打 tag、未发 Release。第 4 轮唯一 Git 写类操作是为基线对照临时 `git worktree add --detach` 基线目录，对照完已 `git worktree remove`，worktree 列表恢复原状。

仍为待办：独立评审（编排方提交开 PR 后由 Reviewy 对完整 SHA diff 给结论）、CI 13/13、合入、tag／Release（合入后双语发布说明与 tag 注释另需 Reviewy 审，对上完整 SHA、CI 13/13 与两份文件原文后再打）。

## 计划中的测试证据

第 1 轮只建立记录，未改实现。第 2 轮完成实现并跑过定向测试；第 3 轮补跑定向、根工作流与 index 复核；第 4 轮补完全量单测（含基线对照）、index 与全部文字／范围检查。各轮实际命令、结果与退出码见「验证证据」表。实现轮要求的证据项：

- 更新后的 golden contracts／panel manifest／r1 acceptance 等相关测试 —— 已执行（第 2、3、4 轮，104 项 OK、退出 0）。
- 措辞 grep／范围检查：只允许上表将改文件；发布身份位置不再残留 rc 号；历史叙述、路径、注释不误改 —— 已执行（第 4 轮，通过）。
- `git diff --check` —— 已执行（第 4 轮，无输出、退出 0）。

## Strict Book Gate Plan

第 1 轮以记录和计划为主；第 2 轮完成生产文件改动；第 3、4 轮完成验证。独立评审、CI、合入、tag／Release 仍待后续。未完整调用 grill-with-docs：边界明确，不新增领域决定。

| Gate | 触发条件／阶段 | 本轮状态与后续动作 |
|---|---|---|
| DDD | 完整 grill 或领域歧义，需求稳定前 | not-needed：未完整调用 grill-with-docs，不新增领域决定 |
| DDIA | schema、缓存、迁移或跨服务设计变化，设计前 | not-needed：只改发布标记文字，不改数据设计 |
| Legacy safety | 首次行为变化前建立安全网 | not-needed：无既有行为变化；全部改动为发布身份文字与测试钉 |
| Refactoring／ponytail | strict 首次生产编辑前按实际范围判断 | 已复核：第 2 轮生产 diff 全部为发布身份文字与测试钉，无逻辑分支、无抽象增减，最小改动成立；第 4 轮重读确认范围与第 1 轮计划一致 |
| BDD／TDD | 新行为或高风险覆盖缺口 | not-needed：不新增行为；测试钉随发布身份同步更新 |
| Project validation | 记录生成后与后续实现后分别验证 | 已执行：第 1–4 轮分别完成 index 重生成、定向与根工作流测试、全量单测（含基线对照）、文字／范围 grep 与 diff 检查；结果见「验证证据」 |
| 独立评审 | 后续文档 diff，合入前 | pending：编排方提交开 PR 后由 Reviewy 对完整 SHA diff 给结论；合入后双语发布说明与 tag 注释另需 Reviewy 审，对上完整 SHA、CI 13/13 与两份文件原文后再打 tag |
| Release readiness | 运行时／部署风险，测试门后 | not-needed：无运行时／部署变化；不宣称 v2.1.0 发布就绪 |
| CI／合入 | 后续 PR 最终提交 | pending：第 1–4 轮均不提交、不推送、不开 PR、不打 tag；提交与 PR 由编排方处理 |

## 验证证据

Evidence Source：developer-local；Source Revision：dirty（生产文件已改、未提交）；Evidence Publication：local-only；Environment Alignment：not-needed。Linux x64。本节为第 1–4 轮本地证据，不是 CI／正式 PR-head 报告。第 2、3 轮结果来自编排方对该两轮会话日志与工作区的只读核对；第 4 轮结果为本会话实际运行。

| 命令／检查 | 实际结果 | 退出码 |
|---|---|---|
| `git log --oneline -3`、`git tag -l 'v2.1.0*'`、`git status --short --branch` | HEAD 为 `c422766`（#215 合入 main 的 squash 提交）；tag 仅 v2.1.0-rc.1 至 rc.5；分支 docs/v2.1.0-release 跟踪 origin/main，起始干净 | 0 |
| `git rev-parse v2.1.0-rc.5 v2.1.0-rc.5^{}`、`git tag -l v2.1.0` | tag 对象 `328b875a8af6eee2cf03c250b4ac17208e6f6531`，指向 `c4227666e2127eca70af591f2e83ad35d7d8bcb6`；无 `v2.1.0` tag | 0 |
| `namei -l`、`git ls-files --stage --`、`git check-ignore -v --no-index --`（新 task 路径与 index） | 父路径无 symlink；新 task 目录不存在；index 为已跟踪普通文件 100644；无 ignore 匹配 | 1（新目录不存在）／0／1（无匹配） |
| `TZ=Asia/Shanghai date --iso-8601=seconds` | 开始写文件时为 2026-11-12T08:10:32+08:00；用于 front matter 与本轮事件记录时间 | 0 |
| read／grep 当前源码 | 已核对上表全部计划项；refresh operation（`openapi.yaml:472-491`）确认无 `x-sbtd-release`；两处 tests 目录 rc 断言仅三个文件；根 `tests/` 无 rc 命中 | 工具成功，无 shell 退出码 |
| write 建立本 task | 亲手建立第 1 轮计划；不调用 task 状态写 API、子代理或 find | 工具成功，无 shell 退出码 |
| 正式生成器写入 index | `INDEX_REGEN changed=True rows=86`；85→86，只新增本任务一行；既有「旧格式事件，不追溯」提示为既有提示，不视为失败 | 0 |
| 只读预览 index | `INDEX_PREVIEW_SAME True rows=86`；逐字节一致 | 0 |
| `python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts` | 99 项通过，失败 0、跳过 0，`OK`，32.161 秒 | 0 |
| `git diff --check`、`git status --short --untracked-files=all`、`git diff --stat`、`git diff -- ai/tasks/index.md` | 空白检查无输出；只有 index 修改与本 task 未跟踪；diff 证实只加本任务链接一行 | 0 |
| 新文案专用 grep（本机路径、禁用归因措辞、非「契约」的「约」字、自动推进授权时刻套话） | 无匹配 | 工具成功，无 shell 退出码 |
| 第 2 轮 `cd sbtd-runtime && python3 -B -m unittest tests.test_golden_contracts tests.test_panel_manifest tests.test_r1_acceptance` | 104 项通过，`OK`，0.978s（第 2 轮会话日志真实结果） | 0 |
| 第 2 轮随后一条 bash（列 `sbtd-runtime/tests/` 与 requirements 文件） | `Tool execution was aborted: Deadline exceeded`，会话以 session_exit reason=dispose kind=normal 结束；sbtd-runtime 全量单测、根工作流测试、index 复核、范围／文案 grep 与该轮记录未完成 | 无（中止） |
| 第 3 轮 定向测试（同第 2 轮命令） | 104 项通过，`OK` | 0 |
| 第 3 轮 `python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts` | 99 项通过，`OK` | 0 |
| 第 3 轮 index 重生成（正式生成器，同第 1 轮命令） | `changed=False rows=86` | 0 |
| 第 3 轮 sbtd-runtime 全量单测 discover 几次尝试 | 被转到后台、结果丢失；随后云主机重启，会话中断（无正常结束） | 未取得 |
| 第 4 轮 重读全部已改文件（diff 与全文） | 与第 1 轮计划及 Lord 2026-11-12 09:23 群内确认口径一致；未发现须改契约字段、状态码、schema、PRD 或 ADR 决策内容之处；未重写任何已正确的生产文件 | 工具成功，无 shell 退出码 |
| 第 4 轮 定向测试（同第 2 轮命令） | 104 项通过，`OK`，0.885s | 0 |
| 第 4 轮 `PYTHONPATH=sbtd-runtime timeout 900 python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py'`（与 `.github/workflows/validation.yml` 的 `PYTHONPATH=sbtd-runtime python -B -m unittest discover -s sbtd-runtime/tests -p '<pattern>'` 同型；CI 按 pattern 分组跑，无单条全量命令，本条为本轮实际所跑） | 481 项，199.1s，`FAILED (failures=2, skipped=10)`。失败 2 项：`test_stats_query.NormalizeScopeTests.test_iana_queries_and_dst_work_without_system_timezone_data`、`test_runtime_perf_smoke.RuntimePerfSmokeTests.test_cli_preserves_dataset_and_reports_unmeasured_boundaries`，失败栈均指向 zoneinfo 无法加载 Asia/Tokyo | 1 |
| 第 4 轮 基线对照：`git worktree add --detach`（基线 `c4227666e2127eca70af591f2e83ad35d7d8bcb6` 临时目录，本轮唯一 Git 写类操作）后以同型命令分别跑 `test_runtime_perf_smoke.py`（2 项，1 失败）与 `test_stats_query.py`（25 项，1 失败） | 基线 `c4227666` 临时 worktree 上用同型命令复跑，这 2 个用例同样失败（`test_runtime_perf_smoke.py` 2 项 1 失败，`test_stats_query.py` 25 项 1 失败），失败栈均指向 zoneinfo 无法加载 Asia/Tokyo；本机未装 tzdata（`import tzdata` ModuleNotFoundError），CI 经 `sbtd-runtime/requirements-serve.txt:8` 钉装 `tzdata==2026.5`；本 PR 未改动这两个测试及其被测代码（`git diff --stat` 核实，改动仅 13 个计划内文件）；对照完已 `git worktree remove`，worktree 列表恢复原状。未 pip 安装或卸载任何包 | 1（预期失败） |
| 第 4 轮 `python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts` | 99 项通过，`OK`，261.4s | 0 |
| 第 4 轮 index 重生成（正式生成器，同第 1 轮命令） | `INDEX_REGEN changed=False rows=86`（「旧格式事件，不追溯」为既有提示，不视为失败） | 0 |
| 第 4 轮 `git diff --check`、`git status --short`、`git diff --stat` | 空白检查无输出；改动仅计划内 13 个文件与本 task 目录，69 插入 22 删除 | 0 |
| 第 4 轮 面板清单哈希重算（测试内同一算法：`json.dumps` sort_keys、紧凑分隔符、UTF-8 后 sha256） | 得 `57d94cb9018a7e544d6ea8010b255c43993b19587825e1652d7040399576749f`，与 `test_panel_manifest.py:82-84` 的钉一致 | 0 |
| 第 4 轮 文案与范围 grep | 5 个契约文件与 3 个测试文件无作为当前发布身份的 `v2.1.0-rc.1`／`v2.1.0-rc.2` 残留；`capability-matrix.json` 残留命中均为历史证据路径；`manifest_version` 为 1.1.0、`info.version` 为 1.0.0；新写内容无本机路径、无禁用归因措辞、无自动推进授权时刻套话；中文新节「约」仅见于「契约」；CHANGELOG 两文件 rc.1 历史节各有一处既有 smoke 证据本机路径，属已发布历史事实，非新写内容 | 工具成功，无 shell 退出码 |

第 1–4 轮合计已执行：读源码与重读核对、写 task、正式生成／预览 index、定向测试（3 轮均通过）、根工作流测试（2 轮均通过）、sbtd-runtime 全量单测（481 项，2 项失败）、基线对照、文字／范围 grep 与 diff 检查。Final Full Rerun：completed with failures（481 项中 2 项失败；基线 `c4227666` 临时 worktree 上用同型命令复跑，这 2 个用例同样失败，失败栈均指向 zoneinfo 无法加载 Asia/Tokyo；本机未装 tzdata（`import tzdata` ModuleNotFoundError），CI 经 `sbtd-runtime/requirements-serve.txt:8` 钉装 `tzdata==2026.5`；本 PR 未改动这两个测试及其被测代码；其余 479 项通过、10 项跳过）；Targeted Rerun：passed（104 项）。

仍未执行：runtime e2e（需装浏览器）与三平台安装器（按本轮要求不跑）、dashboard npm 测试（本 PR 无前端改动）、真实宿主验收与 CI（待编排方提交后由 PR 触发）。BDD：skipped（无场景或行为变化）；Cross-repo context：not-needed；API Contract：not-needed（未改 API 字段与状态码，仅发布标记文字对齐）；Mock Strategy：none。Final Test Report／Run Summary MD：not-needed（developer-local 证据，不生成正式报告）。独立评审、提交、开 PR、合入、tag／Release 未完成，由编排方与 Reviewy 接续。恢复边界：全部改动未提交，`git diff` 所列 13 个文件与本 task 目录即全部范围；没有本机安装或生产状态需要回滚，临时基线 worktree 已移除。

## 模型记录

| 轮次 | 模型 | 用途 | 模型调用 | 工具调用 |
|---|---|---|---|---|
| 第 1 轮 | kimi-code/k3（thinking max） | 只读核对、任务计划、index 生成与本地验证 | 27（会话日志实数，编排方第 2 轮开始前复核） | 48（会话日志实数，编排方第 2 轮开始前复核） |
| 第 1 轮 | openai-codex/gpt-6-astra | 2026-11-12 07:29、07:30、07:32 三次尝试，各 1 次调用均报错（OpenAI 服务故障，返回「站点无法加载」页面），未产出、未写任何文件 | 3（会话日志实数） | 0 |
| 第 1 轮 | openai-codex/gpt-6.1-sol | 每次 astra 报错后，omp 按全局备用模型配置自动改用 gpt-6.1-sol 再试 1 次，共 3 次，也报错，未产出 | 3（会话日志实数） | 0 |
| 第 1 轮 | kimi-code/k3:max（2026-11-12 08:03 开始的先前运行） | 因要按 08:02 确认改写依据措辞，开始后两分钟内被编排方中止，未写任何仓库文件 | 未知（会话日志已删除） | 未知（会话日志已删除） |
| 第 1 轮 | 其他模型 | 本会话日志未出现其他模型名 | 0 | 0 |
| 第 2 轮 | kimi-code/k3（thinking max） | 按计划改生产文件并跑定向验证；单次运行 `--config` 覆盖关闭自动换模型（`retry.modelFallback: false`），未改全局配置；会话在定向测试通过后因后续命令 Deadline exceeded 结束 | 16（会话日志实数，编排方在第 2 轮结束后复核） | 37（会话日志实数，编排方在第 2 轮结束后复核） |
| 第 2 轮 | 其他模型 | 会话日志未出现其他模型名（other_assistant={}） | 0 | 0 |
| 第 3 轮 | kimi-code/k3（thinking max） | 补跑定向测试、根工作流测试与 index 复核；全量单测 discover 被转后台、结果丢失；会话因云主机重启中断 | 47（会话日志实数，编排方只读统计） | 50（会话日志实数，编排方只读统计） |
| 第 3 轮 | 其他模型 | 会话日志未出现其他模型名（other_assistant={}） | 0 | 0 |
| 第 4 轮 | kimi-code/k3（thinking max） | 补完验证（全量单测、基线对照、index、grep）并更新本 task；单次运行 `--config` 覆盖关闭自动换模型（`retry.modelFallback: false`），未改全局配置 | 41（会话日志实数，编排方第 4 轮结束后复核） | 88（同上） |
| 第 4 轮 | 启动未成功的两次尝试 | 一次因账号登录失效、一次因未取到 key，均在任何模型调用前退出，未产生会话、未调用模型 | 0 | 0 |
| 第 4 轮 | 其他模型 | 会话日志未出现其他模型名（other_assistant={}） | 0（会话日志实数） | 0（会话日志实数） |
| 第 5 轮 | kimi-code/k3（thinking max） | 按 Reviewy 与 Lord 群内提醒修改 task 文字，不改生产文件；单次运行 `--config` 覆盖除关闭自动换模型外，还把 smol、commit、tiny、task、advisor、vision、judge、astra 各用途都指定为 kimi-code/k3:max，依据 Lord 2026-11-12 14:11、14:23 群内调度，未改全局配置 | 17（会话日志实数） | 28（会话日志实数） |

改模型依据：用户 2026-11-12 08:02 群内确认（主模型改用 k3:max），Lord 记录。

计数方法：在 omp 会话日志中筛选 `role=assistant`、`provider=kimi-code`、`model=k3` 的消息计模型调用，同一记录内 `toolCall` 条目计工具调用。只读统计脚本输出 `main_assistant=21`、`main_toolcalls=43`，退出 0，未写仓库。统计之后实际发起 5 次 edit 调用（front matter 时间两次、模型表计数三次，其中一次路径写错未生效）与一次纯文本收尾，因此模型调用按 21+6=27、工具调用按 43+5=48 推算，不是事后重读日志的实测总数。astra 3 次与 gpt-6.1-sol 3 次为会话日志实数；被中止的 k3:max 运行未知（会话日志已删除）；find 工具 0；子代理 0。本次计数 edit 为最后一次工具调用，之后不再运行校验。

第 1–4 轮复核与补记（编排方只读统计脚本对相应会话目录复核，均未写仓库）：

- 第 1 轮：编排方第 2 轮开始前复核输出 `main_assistant=27`、`main_toolcalls=48`、`main_errors=0`，与原推算一致；第 1 轮 k3 行据此由「推算」改标「会话日志实数」。
- 第 2 轮：编排方在该轮结束后复核输出 `main_assistant=16`、`main_toolcalls=37`、`main_errors=2`、`other_assistant={}`。2 次错误不编造原因；该轮最后一条工具结果为 `Tool execution was aborted: Deadline exceeded`。
- 第 3 轮：编排方只读统计输出 `main_assistant=47`、`main_toolcalls=50`、`main_errors=2`、`other_assistant={}`；2 次错误为运行日志里的 `ECONNRESET` 自动重试；另有 sbtd-graft MCP 连接失败警告，该 MCP 工具该轮不可用。
- 第 4 轮：只读统计脚本输出 `main_assistant=39`、`main_toolcalls=87`、`main_errors=0`、`other_assistant={}`，退出 0、未写仓库，系该轮进行中统计；当时按 39+2=41、87+1=88 推算并标「推算」。第 4 轮结束后编排方只读统计输出 `main_assistant=41`、`main_toolcalls=88`、`main_errors=0`、`other_assistant={}`，与推算一致，第 4 轮 k3 行据此由「推算」改标「会话日志实数，编排方第 4 轮结束后复核」。
- find 工具各轮均为 0；子代理各轮均为 0。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-12T08:10:32+08:00 | planned | checking | started：用户 2026-11-12 07:26 群内确认按甲开始正式版后，Lord 群内调度开始正式版文档 PR，本轮只写 task.md（及正式生成的 index），不改生产文档 | 本轮分支／HEAD／干净起始状态核对；`v2.1.0-rc.5` tag 对象与指向提交核实，无 `v2.1.0` tag；当前文件精确行号见源码依据表；本事件 at 为记录时间，不是群内确认或调度的秒数 |
| 2026-11-12T08:10:32+08:00 | checking | checking | 07:26 选甲的执行口径：契约里的版本标记只改成 `v2.1.0`，不改字段和状态码；Researchy 指出的 openapi 摘要句、data-dictionary 标题和测试钉作为配套列入计划；`manifest_version` 保持 `1.1.0` 不升；refresh 断言改成断言字段不存在。#1408 已于 2026-11-12T07:19:31+08:00 发出，本 PR 只引用不重发 | 本轮读取 openapi.yaml:5,7,609,650,673,700、capability-matrix.json:3、metrics-catalog.json:4、panel-manifest.json:3-4、data-dictionary.md:1、test_golden_contracts.py:1418,1420,1422、test_panel_manifest.py:81-84,96、test_r1_acceptance.py:189；grep 确认两处 tests 目录无其他 rc 断言 |
| 2026-11-12T08:57:08+08:00 | checking | checking | 第 1 轮完成任务计划、正式 index 与指定本地校验；生产文档与契约标记实现仍待后续，保持 checking，completed_at 保持 null。本项主模型依据用户 2026-11-12 08:02 群内确认（主模型改用 k3:max），Lord 记录 | INDEX_REGEN changed=True rows=86；INDEX_PREVIEW_SAME True rows=86；99 项工作流测试通过、退出 0；git diff --check 退出 0、范围仅本 task 与 index；新文案 grep 无匹配；未打 tag、未发 Release；无必须改契约决策的开放问题 |
| 2026-11-12T10:56:49+08:00 | checking | checking | 第 2 轮：生产文件已按第 1 轮计划改完，定向测试 104 项通过、退出 0；随后一条 bash 因 Deadline exceeded 中止，会话以 session_exit reason=dispose kind=normal 结束（本事件 at 为会话结束时间），task 记录与剩余验证未完成，completed_at 保持 null | 定向测试 104 项 OK、0.978s；main_assistant=16、main_toolcalls=37、main_errors=2（会话日志实数，编排方在该轮结束后只读复核）；未提交、未推送、未开 PR、未打 tag |
| 2026-11-12T11:59:51+08:00 | checking | checking | 第 3 轮：跑完定向测试、根工作流测试与 index 复核后，云主机重启导致会话中断（本事件 at 为会话日志最后写入时间，会话无正常结束，不编造退出码）；全量单测 discover 被转后台、结果丢失，task 记录未回填，completed_at 保持 null | 定向 104 项 OK、退出 0；根工作流 99 项 OK、退出 0；index changed=False rows=86；main_assistant=47、main_toolcalls=50、main_errors=2（ECONNRESET 自动重试；会话日志实数，编排方只读统计） |
| 2026-11-12T14:21:11+08:00 | checking | checking | 第 4 轮：补完全部剩余验证并回填本记录；待编排方提交开 PR 与 Reviewy 审查，保持 checking，completed_at 保持 null | 重读已改文件与第 1 轮计划及 09:23 确认口径一致；定向 104 项 OK、退出 0；全量单测 481 项 FAILED（failures=2、skipped=10）、退出 1，2 项失败在基线 `c4227666` 临时 worktree 用同型命令复跑同样失败，失败栈均指向 zoneinfo 无法加载 Asia/Tokyo；本机未装 tzdata（`import tzdata` ModuleNotFoundError），CI 经 `sbtd-runtime/requirements-serve.txt:8` 钉装 `tzdata==2026.5`；本 PR 未改动这两个测试及其被测代码；根工作流 99 项 OK、退出 0；index changed=False rows=86；git diff --check 通过、范围仅计划内 13 文件与本 task；哈希钉重算一致；文案／范围 grep 通过；未打 tag、未发 Release |
| 2026-11-12T14:49:51+08:00 | checking | checking | 第 5 轮：按 Reviewy 与 Lord 群内提醒改写基线对照表述、补记改用 API key、第 4 轮计数改标实数；未改生产文件 | 指定全文 grep：禁用措辞、本机路径与 key 片段均无命中，唯一命中为 5d 行既有 PRD 文件名内的连字符子串（本轮之前已存在的既有内容，非新写）；`git diff --check` 无输出、退出 0；`git status --short` 仅原 13 个计划文件与本 task 目录；index 正式生成器重生成 `INDEX_REGEN changed=False rows=86`；`git diff --stat` 核实本 PR 未改动全量单测 2 项失败的测试及其被测代码 |
