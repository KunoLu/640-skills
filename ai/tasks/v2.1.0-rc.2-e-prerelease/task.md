---
schema_version: 1
id: v2.1.0-rc.2-e-prerelease
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：strict；omp 为唯一内容 writer，不启动子代理或 advisor；提交、推送与开 PR 由编排方执行
status: checking
branch: docs/v2.1.0-rc.2-e-prerelease-changelog
created_at: '2026-10-28T00:04:56+08:00'
updated_at: '2026-10-28T00:14:28+08:00'
completed_at: null
---

# rc.2 E：预发布 CHANGELOG 与双语发布说明草稿

## 目标

为 `v2.1.0-rc.2` 预发布准备纯文档 CHANGELOG PR；不新增需求，不升版，不创建 tag 或 Release。两份 CHANGELOG 使用 `Unreleased`／`未发布`，不提前填写发布日期、tag SHA 或 tag CI。只有本 PR 合入、合入提交的精确 SHA CI 13/13（按作业名）全部 success、且用户明确说「发布」之后，才创建 annotated tag `v2.1.0-rc.2` 与 GitHub prerelease，不标 Latest，`v2.0.2` 仍为最新正式版。之后另一个 PR 按 rc.1 先例记录 tag SHA／日期。

## 决定与归属

以下五项来源均为 **Lord 2026-10-27 23:52 群内裁定**（编排方整理，事实目录 `meta.md:35-40`）：

1. E 单独开小 PR，仅两份 CHANGELOG 与本任务记录。
2. 本 PR 不升版本元数据，OpenAPI info 与两个 catalog 的 release 仍为 rc.1。
3. #186／#191 依据证据分类，由 Reviewy 审阅；当前审阅结果见下方第 3 轮记录。
4. 如实陈述未完成项，不写成已经验证。
5. 本 PR 合入 → 合入精确 SHA CI 13/13 按名称全绿 → 用户明确说「发布」→ annotated tag 与 GitHub prerelease；发布身份由之后的 PR 写入 CHANGELOG。

Lord 2026-10-28 群内裁定
注：分钟不可考。

D9 据 Lord 群内记录记载：用户 2026-10-27 群内确认（核验清单 v3 第 1–7 步：暗/浅主题，HTML/JPEG/PDF/CSV），Lord 记录；字体／长页／分页视觉属于第 1–7 步范围，用户群内确认已覆盖，该记录尚未回填到仓内 R2.2 task.md。Mac 视觉相关项中仅 Mac 上 JPEG／PDF 字节数仍未验证，核验清单 v3 本身不含字节检查；其余性能／规模／容量项仍未验证，R2.2 仍为 `in-progress`、收尾 pending。

Reviewy 2026-10-28 群内审阅：NOT CLEAN（3 个阻塞项 B1–B3 及若干非阻塞项）
注：分钟不可考。

编排方整理：未完整调用 grill-with-docs，需求、来源、四个写入目标与验收条件明确，无领域歧义。历史事实仅来自事实目录与仓库，不联网补查，不读取或统计会话 jsonl；下表历史模型计数沿用编排方整理的数据。

## 范围与边界

- 仓库内恰好三个文件：`CHANGELOG.md`、`CHANGELOG.zh.md`、`ai/tasks/v2.1.0-rc.2-e-prerelease/task.md`。另交付仓库外的发布说明草稿（编排方保管，不入库）。
- 不改 openapi／contracts／tests／PRD／ADR／plan.md／源码／static 或其他文件；不升版本元数据，不建 tag／Release，不安装依赖、不构建、不联网、不执行 gh、不提交、不推送，不进行 git 写操作。
- `ai/tasks/v2.1.0-rc.2-plan/plan.md:25-26` 两处指针本 PR 不改：E 行指向本 PR 才创建的本文件；F 行指向 `ai/tasks/v2.1.0-rc.2-f-docs-backfill/task.md`，实际目录为 `ai/tasks/v2.1.0-rc.2-f-backfill/`。交由编排方在 PR 描述中说明，不在本 PR 修正 plan。
- 参照 F 记录先例手写本 task，未经 TaskStore 写入；只运行只读 parser，不写 active／index／handoff／ignore／身份。不创建额外报告或临时脚本，不承诺自动恢复。测试自身的系统临时目录例外；Python 命令均加 `-B`。
- 第 1 轮开始写入前已核对授权根、分支、干净工作区；当时 HEAD 与 origin/main 均为 `55d7b6230f1fe9f302cc06b5100376bdd344aae5`。四个授权目标及父目录无 symlink；三个仓库路径无 ignore 匹配；两个新文件此前不存在。第 2 轮起点为 PR #192 tip `e0a8b7c3db2bb0bc1b4aeb7d011f42aa826e0e5b`，分支匹配、工作区干净，四个现存目标均为普通文件且路径无 symlink，三个仓库路径无 ignore 匹配；本轮只修改四个授权文件。

## 分类与覆盖依据

- **#186 → Added／新增**：`classify-186-191.md:7-18` 记录此前四个导出按钮不可用，之后接入创建、轮询、下载、取消与页面展示状态。虽然它补齐 R2.1a 开发期遗漏，但 rc.1 没有 Dashboard，按上一发布版本比较属于新增用户可见能力；不把开发期遗漏写成已发布版本回归。
- **#191 → Changed／变更**：`classify-186-191.md:24-31` 记录既有预置窗口由精确当前时间改为固定 300 秒 UTC epoch 桶上界，改变查询范围语义以保持桶内 query_hash 稳定。没有新增用户能力，也未发现将其定性为缺陷修复的事实依据。
- Reviewy 对 PR #192 tip `e0a8b7c` 与 `7b7cd8e` 的审阅均为 NOT CLEAN；第 3 轮修订待复审，自核不是 Reviewy 审阅通过。
- `meta.md:4-7`：本次覆盖 #141–#191，排除 #143，共 50 个 PR；#140 已在 rc.1 发布记录。已通读 `meta.md`、`classify-186-191.md`、`unfinished.md`、`known-limitations.md`、`rc1-release-body.md` 及 `all-prs.md`，并逐字核对 50 份独立 PR 文件均包含在汇编中。CHANGELOG 按用户可见主题合并，每个 PR 至少有一处标准链接。

## 未完成项与 D9

编排方整理：`unfinished.md` 引自 `ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/task.md`，frontmatter 原样状态为 `status: in-progress`、`completed_at: null`。以下保留源文件 :1263-1271 的表格原文；表中 **pending，未验证** 为尚未回填的仓库记录，不是通过证据。D9 新群内记录及其限定范围见表后：

| pending 项 | 精确原因／停止边界 |
|---|---|
| D9：AC-33／AC-62 用户 Mac 人工视觉／字体确认——pending | 原因：只能由用户 Mac 真机产出，本会话无法产出，按用户 2026-10-24 22:48 群内确认（D9 等 Mac 证据时停），Lord 记录 |
| macOS 实机性能——pending | 本机仅Linux VM，不能生成Mac原生版本／硬件／性能报告；等用户Mac证据，可用同一脚本复跑 |
| Mac 上 JPEG／PDF 字节数、字体／长页／分页视觉——pending | 只能在Mac实际renderer／字体下取得；本机JPEG/PDF unavailable，Linux HTML几何不能替代 |
| 原生 Windows 性能——pending | 无Windows真机，本轮无CI运行授权／远端操作；后续只能以真实CI runner报告标注来源，不能冒充真机 |
| 百万事件／1万任务／10万步骤及百万CSV——pending | 本轮完整写入成本与软时限只取得最大11500事件；未外推，CSV实现非流式，性能优化不在本PR |
| 完整四格式容量／平台资源上限／最大长图CSV规模——pending | JPEG/PDF缺实测与平台证据；缺失值未当0，未修改默认值／PRD／schema；需要规则变更的项另行处理 |
| R2.2 收尾——pending | D9未满足，不执行任务完成状态、completed_at或plan R2.2行变更；status保持in-progress、completed_at保持null，plan原行逐字不变 |

用户 2026-10-27 群内确认（核验清单 v3 第 1–7 步：暗/浅主题，HTML/JPEG/PDF/CSV），Lord 记录
注：分钟不可考。

编排方整理：据 Lord 群内记录，用户在 MacBook Air 上完成上述七步，全部通过；字体／长页／分页视觉属于第 1–7 步范围，用户 2026-10-27 群内确认已覆盖，Lord 记录。该记录尚未回填到仓内 R2.2 task.md（`ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/task.md`），不是仓库内的通过证据；本 E 任务未核实用户实际执行的清单。R2.2 仍为 `in-progress`、`completed_at: null`，R2.2 收尾仍 pending。

上方表格是 r2.2 task.md:1263-1271 的原文引用，其中 D9 及「Mac 上 JPEG／PDF 字节数、字体／长页／分页视觉」行的 pending 状态为仓库原记录；「本机／本轮」属于源记录的历史上下文，不是本 E 任务重新测量的结果。按 Lord 裁定，Mac 视觉相关项中仅「Mac 上 JPEG／PDF 字节数」仍未验证，核验清单 v3 本身不含字节检查；字体／长页／分页视觉属于第 1–7 步范围，用户 2026-10-27 群内确认已覆盖，Lord 记录，该记录尚未回填到仓内 R2.2 task.md。macOS 实机性能、原生 Windows 性能、百万事件／1万任务／10万步骤及百万CSV、完整四格式容量／平台资源上限／最大长图CSV规模仍未验证，R2.2 收尾仍 pending。#186 浅色导出仍无 CI 覆盖；据 Lord 群内记录，用户群内确认的清单包含浅主题，该记录尚未回填到仓内 R2.2 task.md。

## 已知限制来源

编排方整理：`known-limitations.md` 的结论为：仓库中未找到"沿用之前五条"字样；唯一五条编号列表为 #191（`ai/tasks/v2.1.0-rc.2-contract-bucket-ceiling/task.md:105-119`），不是 rc.1 的通用限制列表。

- #191 五项分别为：全库事件指纹下持续到达时单页固定 30 秒轮询仍可达 2880 快照／天（不含手动请求或多页，降幅不可考）；30 秒轮询请求不减少、不保证不同 snapshot_id 或性能收益；后端不拒绝晚于 as_of 的取整终点；复用时响应 meta.as_of 可能不同于 snapshot.as_of；只取整前端预置，不自动取整所有 API 请求。无新数据每日 288 次只是来源不可考的目标，不作为硬上限或收益承诺。
- 延后项另列：401 重新配对未实现，401 时导出轮询停止并提示重启 serve 后重新配对，页面每 30 秒的主快照轮询不因此停止；快照内存淘汰未实现，启动仍装载全部快照，无内存淘汰策略。不虚构 LRU／懒加载已经落地。
- #190 的 N1–N4 是另一个四项列表，不当作上述五条来源：同一文件身份不变的窄窗口改写可能命中缓存；load_dataset 的条件性异常映射变化仅有代码推断；取消时信号量不等于仍运行线程的硬上限；库调用方改写 create_or_reuse 返回对象可能影响后续缓存读取。保留证据边界，不作生产吞吐或全面平台保证。
- 审计仍为全量 replay／排序后分页，CSV 生成仍完整缓冲；Windows ACL 无本机实证，query.executed 不持久化。R2.2 小规模测量不等于 AC-62 通过。

## 版本与部署边界

编排方整理，依据 `meta.md:15-28`：`sbtd-runtime/contracts/openapi.yaml` 的 `info.x-sbtd-release` 与 info summary、`sbtd-runtime/contracts/capability-matrix.json` 和 `sbtd-runtime/contracts/metrics-catalog.json` 的 `release` 有意仍为 `v2.1.0-rc.1`，本 PR 不升版。`sbtd-runtime/` 仍可选，观察默认关闭；serve／Dashboard 只由显式前台命令启动、只绑定 `127.0.0.1`，Ctrl-C 退出，无后台定时清扫。快照已落盘 `snapshots/`，24h TTL；导出在 `exports/`，共享默认 2,000,000,000 字节磁盘配额。`sbtd dashboard`／`sbtd ui` 关键词本身不是启动许可；Onboard 不安装或复制 runtime。源码预发布不执行本机安装、workflow sync、项目迁移、宿主重载或备份处置。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮适用性与结果 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求前 | not-needed；仅记录文档，未完整 grill，边界明确 |
| book-ddia-data-design | schema、迁移或持久化机制设计前 | not-needed；不改持久化机制，只记录既有事实 |
| book-legacy-change-safety | 既有行为修改前 | not-needed；无行为修改，历史 CHANGELOG 保留 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；不改生产代码 |
| book-release-readiness | 运行时或部署变化，验证后 | not-needed；本 PR 仅准备文档，不执行发布或部署，不声称发布就绪 |

## 验证与剩余边界

以下自检 1–6 保留第 1 轮执行背景；第 2 轮禁词清单仅 8 项，第 3 轮扩展为完整 14 项，当前结论以本节「第 3 轮更正（Reviewy NOT CLEAN @ 7b7cd8e）」的实测表为准，既有状态事件不改写。

- 自检 1：`git status --short` 实际仅输出下列两份修改与新 task 目录；`git diff --check` exit 0、无输出。只读字节对照证明插入新章节后，两份 CHANGELOG 的原文件前缀与全部历史章节保持原样。

  ```text
   M CHANGELOG.md
   M CHANGELOG.zh.md
  ?? ai/tasks/v2.1.0-rc.2-e-prerelease/
  ```

- 自检 2（第 1 轮）：按 `git diff -U0 -- CHANGELOG.md CHANGELOG.zh.md` 的新增行（排除文件头）与两个新文档全文执行过扫描，但当时禁词清单不完整，「禁词 0 命中」结论不准确；第 2 轮仅补查至 8 项，第 3 轮扩展为 14 项，以第 3 轮实测表为准。本 task 的本机工作区绝对路径前缀当时记录为 0 次。不扫描或修改历史章节中的既有命中。
- 自检 3：两份新章节各覆盖 50/50 个 PR，缺失列表均为 `[]`，即 #141–#191 除 #143。逐条 PR 链接及顺序相同，代码标识多重集合相同；章节条目数分别为 Added／新增 8、Changed／变更 10、Fixed／修复 6、Candidate Boundaries and Known Limitations／候选边界与已知限制 12。发布说明的中英正文与对应 CHANGELOG 新章节逐字节一致，末尾对比链接行精确匹配。
- 内存检查过程保留：第一次链接正则遗漏方括号转义，错误报出全部编号缺失；修正正则后覆盖通过。第二次错误要求翻译句内代码标识出现顺序也相同，命中 `202` 与 `export_id` 的中英语序差异；改为逐条比较标识多重集合后通过，PR 链接顺序仍逐条严格比较。未修改文档迎合检查脚本，未创建临时脚本文件。最终输出 `SELF_CHECK_1_2_3_OK`，exit 0。
- 自检 4：仓库根实际运行 `python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" ai/tasks/v2.1.0-rc.2-e-prerelease/task.md`，初次输出 `ai/tasks/v2.1.0-rc.2-e-prerelease/task.md in-progress False 1 None`，exit 0。
- 自检 5：一次运行 `python3 -B -m unittest tests.test_sbtd_task_document tests.test_sbtd_task_legacy_events_notice tests.test_sbtd_task_recovery tests.test_sbtd_task_routing tests.test_sbtd_task_schema tests.test_sbtd_task_state tests.test_sbtd_task_status_sync tests.test_sbtd_task_sync_git`，原生结果为 `Ran 135 tests in 58.284s`、`OK`，exit 0。输出包含测试路径产生的「旧格式事件，不追溯」提示，不是本 task 被识别为旧格式。未重跑该套件。
- 自检 6（第 1 轮）：checking 事件写入后再次执行上述 parser，实际输出 `ai/tasks/v2.1.0-rc.2-e-prerelease/task.md checking False 2 None`，exit 0；当时的「禁词 0 命中」结论因漏项而不准确，第 2 轮仅补查至 8 项，第 3 轮扩展为 14 项，以第 3 轮实测表为准。本 task 的本机工作区绝对路径前缀当时记录为 0。范围／diff／双语覆盖／历史字节与发布说明一致性当时通过，输出 `SELF_CHECK_1_2_3_OK`。事件时间分别来自两次单独执行 `TZ=Asia/Shanghai date -Iseconds`：`2026-10-28T00:04:56+08:00` 与 `2026-10-28T00:14:28+08:00`，后者晚于前者。当时补入结果后再次运行 parser 与禁词检查，未重跑 unittest。
- 编排方整理，基线 CI：精确 SHA `55d7b6230f1fe9f302cc06b5100376bdd344aae5`，run [40526884945](https://github.com/KunoLu/640-skills/actions/runs/40526884945)，workflow `validation`，event `push`，attempt 1，conclusion `success`，2026-10-27 23:24:24 (UTC+8) 完成。按名称 13 个作业全部 success：`dashboard-artifacts`、`linux-full`、`linux-shards (1)`、`linux-shards (2)`、`linux-shards (3)`、`macos-bash-installer`、`runtime-e2e-macos`、`runtime-e2e-windows`、`windows-powershell-installer`、`windows-shards (1)`、`windows-shards (2)`、`windows-shards (3)`、`windows-shards (4)`。该 run 各平台测试计数为 `unknown`，事实目录未采集。
- 编排方整理，PR #192 既有 tip CI：精确 SHA `e0a8b7c3db2bb0bc1b4aeb7d011f42aa826e0e5b`，run [40539754237](https://github.com/KunoLu/640-skills/actions/runs/40539754237)，workflow `validation`，event `pull_request`，attempt 1，conclusion `success`，2026-10-28 00:36:35 (UTC+8) 完成。13/13 作业 success：`dashboard-artifacts`、`linux-full`、`linux-shards (1)`、`linux-shards (2)`、`linux-shards (3)`、`macos-bash-installer`、`runtime-e2e-macos`、`runtime-e2e-windows`、`windows-powershell-installer`、`windows-shards (1)`、`windows-shards (2)`、`windows-shards (3)`、`windows-shards (4)`。本会话未联网重查；本轮修订后的新 tip 需重新运行 CI，结果尚未产生。Reviewy 对 `e0a8b7c` 为 NOT CLEAN，本轮修订待复审。保持 `checking`、`completed_at: null`；取得新 tip CI 13/13 与 Reviewy CLEAN 前不写完成事件。
- 仓库没有检查两份 CHANGELOG 一致性的测试（`meta.md:55`）；第 1 轮运行过任务模块回归与真实 TaskDocument 解析，第 2 轮只运行内存只读文档检查与真实 TaskDocument 解析，不重跑 unittest、不修改测试。
- Evidence Source：developer-local；Source Revision：dirty；Environment Alignment：unverified；Evidence Publication：local-only。不是正式 CI／发布验收报告。rtk：not-needed，采用约定原生命令；Final Test Report／Run Summary MD：not-needed，不创建额外报告文件。BDD：skipped，仅文档、无 .feature 或行为变化；Cross-repo context／API Contract：not-needed；Mock Strategy：none。不跑构建、额外 lint／formatter、Web／Mobile E2E 或全量 CI，无相应代码变更且本轮禁止构建／联网。

### 第 2 轮更正（Reviewy NOT CLEAN）

- 第 1 轮自检 2／6 与 checking 历史事件中的「禁词 0 命中」结论不准确：漏查了 `U+8FBE U+6807` 连续子串；当时 `CHANGELOG.zh.md` 新增行中的 `U+672A U+8FBE U+6807` 实有 2 处，发布说明中文段也有 2 处。本轮改为「未满足」／「未满足的结果」，历史事件行逐字节保留。为避免更正说明自身命中，禁用词以 Unicode 码点标识。
- B1 依据 `sbtd-runtime/dashboard/src/exportJob.ts:30`、`ai/tasks/v2.1.0-rc.2-r2.1c-export-menu/task.md:89` 与 `sbtd-runtime/dashboard/src/App.tsx:151-173`，将延后项限定为导出轮询停止，主快照 30 秒轮询继续；Added／新增的 #186 条目保持原样。B3 当时区分清单 v3 七步通过、仓库尚未回填与其余 pending 项；D9 范围以第 3 轮按 Lord 裁定的更正为准。N1 用 PR #192／PR #191 明确指代，PR 链接集合不变；N2 模型计数采用编排方整理的数据，未读取会话 jsonl；N3 区分既有 tip 的成功 CI 与本轮尚无结果的新 tip。
- 第 2 轮自检 1：`git status --short` 仅有 ` M CHANGELOG.md`、` M CHANGELOG.zh.md`、` M ai/tasks/v2.1.0-rc.2-e-prerelease/task.md`；`git diff --check` exit 0、无输出。两份 CHANGELOG 的章节前缀与 rc.1 及以下历史字节均与本轮起点 HEAD 一致；本 task 的完整 frontmatter、两条状态事件及 R2.2 引用表保持逐字节一致。
- 第 2 轮自检 2：使用 `git diff -U0 origin/main -- CHANGELOG.md CHANGELOG.zh.md`，只取 `+` 开头并排除 `+++` 的新增行；本 task 与发布说明全文分别扫描。下表仅为第 2 轮 8 项清单的历史实测计数，并非完整禁词清单；第 3 轮扩展为 14 项，以第 3 轮实测表为准。首项大小写不敏感，其他项为子串匹配，码点之间不含空格时即为被扫描的原字符串。

| 禁用项（Unicode 码点） | CHANGELOG.md 新增行 | CHANGELOG.zh.md 新增行 | task.md 全文 | release-body.md 全文 |
|---|---|---|---|---|
| 1：U+0063 U+006F U+006E U+0066 U+0069 U+0072 U+006D U+0065 U+0064 | 0 | 0 | 0 | 0 |
| 2：U+7528 U+6237 U+6307 U+5B9A | 0 | 0 | 0 | 0 |
| 3：U+5DE6 U+53F3 | 0 | 0 | 0 | 0 |
| 4：U+540E U+7EED U+56DE U+586B | 0 | 0 | 0 | 0 |
| 5：U+0076 U+0069 U+0074 U+0065 U+0073 U+0074 | 0 | 0 | 0 | 0 |
| 6：U+002F U+0068 U+006F U+006D U+0065 U+002F U+0062 U+006F U+0078 | 0 | 0 | 0 | 0 |
| 7：U+007E U+002F | 0 | 0 | 0 | 0 |
| 8：U+8FBE U+6807 | 0 | 0 | 0 | 0 |

- 本 task 中本机工作区绝对路径前缀（U+002F U+0077 U+006F U+0072 U+006B U+0073 U+0070 U+0061 U+0063 U+0065）实际计数为 0。
- 第 2 轮自检 3：两份新章节各覆盖 #141–#191 除 #143，均为 50/50、缺失 `[]`；各小节条目数均为 8／10／6／12。36 条的 PR 链接逐条同序，代码标识多重集合一致，既有 PR 链接集合不变；Added／新增的 #186 条目与 HEAD 相同。发布说明 English／简体中文两段与 CHANGELOG 对应新章节逐字节一致，`<<PLACEHOLDER` 恰 3 个、三条占位行及末行对比链接保持原样。
- 第 2 轮自检 4：仓库根执行上述 `python3 -B -c` TaskDocument 解析命令，输出 `ai/tasks/v2.1.0-rc.2-e-prerelease/task.md checking False 2 None`，exit 0。
- 执行过程：内存检查脚本首次启动因命令参数含零字节被拒绝，Python 未执行、未产生文件；修正脚本的代码标识正则表示后运行成功，输出 `ROUND_2_SELF_CHECK_1_2_3_OK`、exit 0。没有修改文档迎合检查脚本。本轮不运行 unittest；第 1 轮的 135 tests 不是本轮新执行结果。上述结果落盘后再执行自检 1–4，复核结果随交付回复提供。

### 第 3 轮更正（Reviewy NOT CLEAN @ 7b7cd8e）

Reviewy 2026-10-28 群内审阅 `7b7cd8e19d2593dd5b4ea9095dd65dd8c6b1fea0` 为 NOT CLEAN。
注：分钟不可考。

- 本轮保持 strict；写前重新通读四个文件全文，核对分支与上述 HEAD、干净工作区、四个既有普通文件及父路径无 symlink，三个仓库路径无 ignore 匹配。仅修改四个授权文件，不新建文件、目录或临时脚本，不调用子代理／advisor，不联网、不执行 Git 写操作或 TaskStore 写入，不读取或统计会话 jsonl。
- 更正 1（措辞与禁词）：D9 来源改为「编排方整理：据 Lord 群内记录，…」，N2 模型计数改为编排方整理的数据。第 2 轮清单仅 8 项，本轮扩展为完整 14 项；第 1 轮自检 2／6、第 2 轮自检 2 及 checking 历史事件的禁词结论不能作为完整清单通过证据，当前结果以下表为准，历史事件逐字节保留。
- 更正 2（回填边界）：删除指定任务将回填的承诺，中文统一为「尚未回填到仓内 R2.2 task.md」，英文统一为 “has not yet been backfilled into the repository's R2.2 task.md”；保留范围节第 44 行的 plan F 目录指针，不改 plan。
- 更正 3（Lord 裁定的 D9 范围）：据 Lord 群内记录，字体／长页／分页视觉属于清单第 1–7 步范围，用户 2026-10-27 群内确认已覆盖，Lord 记录；该记录尚未回填到仓内 R2.2 task.md。Mac 视觉相关项中仅 Mac 上 JPEG／PDF 字节数仍未验证，清单 v3 本身不含字节检查。保留性能／规模／容量未验证、R2.2 `in-progress` 与收尾 pending，以及浅色导出无 CI 覆盖的边界；不声称本 E 任务核实了用户实际执行的清单。两份 CHANGELOG 的两处群内归属均在同一条目内加分钟不可考注，发布草稿同步。

完整禁词实测：两份 CHANGELOG 使用 `git diff -U0 origin/main -- CHANGELOG.md CHANGELOG.zh.md` 的新增行，排除 `+++` 文件头；task.md 与 release-body.md 扫描全文。第 1 项大小写不敏感，其余项按连续子串计数；下面码点连接后才是扫描字符串，不把码点文本本身计为命中。

| 禁用项（Unicode 码点） | CHANGELOG.md 新增行 | CHANGELOG.zh.md 新增行 | task.md 全文 | release-body.md 全文 |
|---|---|---|---|---|
| 1：U+0063 U+006F U+006E U+0066 U+0069 U+0072 U+006D U+0065 U+0064 | 0 | 0 | 0 | 0 |
| 2：U+7528 U+6237 U+6307 U+5B9A | 0 | 0 | 0 | 0 |
| 3：U+5DE6 U+53F3 | 0 | 0 | 0 | 0 |
| 4：U+540E U+7EED U+56DE U+586B | 0 | 0 | 0 | 0 |
| 5：U+0076 U+0069 U+0074 U+0065 U+0073 U+0074 | 0 | 0 | 0 | 0 |
| 6：U+002F U+0068 U+006F U+006D U+0065 U+002F U+0062 U+006F U+0078 | 0 | 0 | 0 | 0 |
| 7：U+007E U+002F | 0 | 0 | 0 | 0 |
| 8：U+8FBE U+6807 | 0 | 0 | 0 | 0 |
| 9：U+7528 U+6237 U+63D0 U+4F9B | 0 | 0 | 0 | 0 |
| 10：U+672C U+6B21 U+4EFB U+52A1 U+63D0 U+4F9B U+7684 | 0 | 0 | 0 | 0 |
| 11：U+7F16 U+6392 U+65B9 U+8F6C U+8FF0 | 0 | 0 | 0 | 0 |
| 12：U+7528 U+6237 U+6240 U+6307 | 0 | 0 | 0 | 0 |
| 13：U+7F16 U+6392 U+65B9 U+63D0 U+4F9B U+7684 | 0 | 0 | 0 | 0 |
| 14：U+0043 U+006F U+0064 U+0065 U+0058 U+0020 U+7FA4 U+5185 U+8865 U+5145 | 0 | 0 | 0 | 0 |

- task.md 中本机工作区路径前缀（U+002F U+0077 U+006F U+0072 U+006B U+0073 U+0070 U+0061 U+0063 U+0065）实测计数：0。
- 回填名称 grep（U+0066 U+002D U+0062 U+0061 U+0063 U+006B U+0066 U+0069 U+006C U+006C）实测：CHANGELOG.md 0、CHANGELOG.zh.md 0、task.md 1（第 44 行既有目录名）、release-body.md 0；状态事件表无命中。此处用码点记录搜索词，避免更正记录自身增加命中。
- 第 3 轮自检 1：`git status --short` 仅输出 ` M CHANGELOG.md`、` M CHANGELOG.zh.md`、` M ai/tasks/v2.1.0-rc.2-e-prerelease/task.md`；`git diff --check` exit 0、无输出。frontmatter、完整状态事件表、完整模型表（含第 6 行）、Lord 裁定两行、plan F 指针、既有 CI 陈述所在整行与 R2.2 原文引用表均与 HEAD 逐字节一致。两份 CHANGELOG 的 rc.1 及以下历史字节与 HEAD、origin/main 均一致。
- 第 3 轮自检 2：14 项 × 4 范围共 56 个实测计数均为 0；路径前缀与回填名称计数、位置如上。没有以第 2 轮八项结果冒充完整清单结果。
- 第 3 轮自检 3：两份新章节各为 50/50 覆盖，缺失 `[]`，范围为 #141–#191 除 #143；各小节均为 8／10／6／12。36 条 PR 链接逐条同序、代码标识多重集合一致；相对 HEAD 不增删 PR 链接。release-body.md 的 English／简体中文正文与相应新章节逐字节一致，`<<PLACEHOLDER` 恰 3 个；占位行、发布身份段、部署边界段及末行对比链接的写前指纹均保持一致。内存只读检查输出 `ROUND_3_SELF_CHECK_1_2_3_OK`，exit 0。
- 第 3 轮自检 4：仓库根执行上方自检 4 的 `python3 -B -c` TaskDocument 解析命令，实际输出 `ai/tasks/v2.1.0-rc.2-e-prerelease/task.md checking False 2 None`，exit 0。
- 第 3 轮自检 5：按本轮要求不重跑 unittest；第 1 轮的 135 tests 不作为本轮新结果。仅文档，无行为变更，不跑构建、额外 lint／formatter、BDD 或 Web／Mobile E2E；rtk 为 not-needed，采用原生命令。Book Gate Plan 的 not-needed 判定保持不变。
- 以上为本轮结果写入前的实际检查；写入后再执行自检 1–4，最终复核结果随交付回复提供。证据为 developer-local、dirty、local-only，Environment Alignment 为 unverified；不创建额外报告。保持 `checking`、`completed_at: null`，不新增状态或模型记录；新 tip CI 与 Reviewy 复审未完成，本地自核不代表 CLEAN 或发布就绪。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | model_usage | 产出 |
|---|---|---|---|---|---|
| 1 | ping 第 1 次 | openai-codex/gpt-6-astra（high） | 1／0（2026-10-28 00:00:04 (UTC+8) 开始，编排方据会话 jsonl 统计（executor-counted）） | 0 | 连通性检查 |
| 2 | main 第 1 次（2026-10-28 00:00:26 (UTC+8) 开始） | openai-codex/gpt-6-astra（high） | 6／18（编排方据会话 jsonl 统计（executor-counted）） | 0 | 未写入任何文件；因提示中禁词检查范围与历史 CHANGELOG 既有命中冲突而如实停止，提示随后由编排方修正检查范围 |
| 3 | ping 第 2 次 | openai-codex/gpt-6-astra（high） | 1／0（2026-10-28 00:02:46 (UTC+8) 开始，编排方据会话 jsonl 统计（executor-counted）） | 0 | 连通性检查 |
| 4 | main 第 2 次 | openai-codex/gpt-6-astra（high） | 27／54（编排方据会话 jsonl 统计（executor-counted）） | 0 | 两份 CHANGELOG、本任务、仓库外的发布说明草稿（编排方保管，不入库）与本地自检 |
| 5 | ping 第 3 次 | openai-codex/gpt-6-astra（high） | 1／0（2026-10-28 00:49:57 (UTC+8) 开始，编排方据会话 jsonl 统计（executor-counted）） | 0 | 连通性检查 |
| 6 | main 第 3 次（本会话，Reviewy 第 1 轮修订） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），在之后的 done 提交中补记；由编排方据会话 jsonl 统计（executor-counted） | 0 | B1–B3、N1–N3 文档修订与本轮只读自检 |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-28T00:04:56+08:00 | planned | in-progress | 编排方整理：按明确的 strict 文档范围建立 E 任务，由 omp 唯一写入。 | 开始写本文件前单独执行 TZ=Asia/Shanghai date -Iseconds 的实际输出；分支、基线、干净工作区、目标不存在与路径安全已核对；事实已通读，未经 TaskStore 写入。 |
| 2026-10-28T00:14:28+08:00 | in-progress | checking | 编排方整理：本地自检完成，进入 checking；本 PR 的 CI 与 Reviewy 审阅尚待进行，不标完成。 | 单独执行 TZ=Asia/Shanghai date -Iseconds 的实际输出；八模块 Ran 135 tests in 58.284s，OK，exit 0，仅运行一次；初次 parser 为 in-progress False 1 None；双语条目数 8／10／6／12，各覆盖 50/50 PR，逐条链接与标识一致，历史字节保留；范围符合授权，diff --check 干净，新增章节及两个新文档禁词 0 命中；检查脚本修正过程见验证节；本事件后复跑 parser 与禁词检查，completed_at 保持 null。 |
