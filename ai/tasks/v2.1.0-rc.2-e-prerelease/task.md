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
3. #186／#191 依据证据分类，由 Reviewy 审阅；审阅结果尚未产生。
4. 如实陈述未完成项，不写成已经验证。
5. 本 PR 合入 → 合入精确 SHA CI 13/13 按名称全绿 → 用户明确说「发布」→ annotated tag 与 GitHub prerelease；发布身份由之后的 PR 写入 CHANGELOG。

编排方整理：未完整调用 grill-with-docs，需求、来源、四个写入目标与验收条件明确，无领域歧义。历史事实仅来自事实目录与仓库，不联网补查，不读取或统计会话 jsonl；下表历史模型计数沿用编排方整理的数据。

## 范围与边界

- 仓库内恰好三个文件：`CHANGELOG.md`、`CHANGELOG.zh.md`、`ai/tasks/v2.1.0-rc.2-e-prerelease/task.md`。另交付仓库外的发布说明草稿（编排方保管，不入库）。
- 不改 openapi／contracts／tests／PRD／ADR／plan.md／源码／static 或其他文件；不升版本元数据，不建 tag／Release，不安装依赖、不构建、不联网、不执行 gh、不提交、不推送，不进行 git 写操作。
- `ai/tasks/v2.1.0-rc.2-plan/plan.md:25-26` 两处指针本 PR 不改：E 行指向本 PR 才创建的本文件；F 行指向 `ai/tasks/v2.1.0-rc.2-f-docs-backfill/task.md`，实际目录为 `ai/tasks/v2.1.0-rc.2-f-backfill/`。交由编排方在 PR 描述中说明，不在本 PR 修正 plan。
- 参照 F 记录先例手写本 task，未经 TaskStore 写入；只运行只读 parser，不写 active／index／handoff／ignore／身份。不创建额外报告或临时脚本，不承诺自动恢复。测试自身的系统临时目录例外；Python 命令均加 `-B`。
- 开始写入前已核对授权根、分支、干净工作区；HEAD 与 origin/main 均为 `55d7b6230f1fe9f302cc06b5100376bdd344aae5`。四个授权目标及父目录无 symlink；三个仓库路径无 ignore 匹配；两个新文件此前不存在。

## 分类与覆盖依据

- **#186 → Added／新增**：`classify-186-191.md:7-18` 记录此前四个导出按钮不可用，之后接入创建、轮询、下载、取消与页面展示状态。虽然它补齐 R2.1a 开发期遗漏，但 rc.1 没有 Dashboard，按上一发布版本比较属于新增用户可见能力；不把开发期遗漏写成已发布版本回归。
- **#191 → Changed／变更**：`classify-186-191.md:24-31` 记录既有预置窗口由精确当前时间改为固定 300 秒 UTC epoch 桶上界，改变查询范围语义以保持桶内 query_hash 稳定。没有新增用户能力，也未发现将其定性为缺陷修复的事实依据。
- 两项分类均待 Reviewy 审阅，本轮自核不是 Reviewy 审阅通过。
- `meta.md:4-7`：本次覆盖 #141–#191，排除 #143，共 50 个 PR；#140 已在 rc.1 发布记录。已通读 `meta.md`、`classify-186-191.md`、`unfinished.md`、`known-limitations.md`、`rc1-release-body.md` 及 `all-prs.md`，并逐字核对 50 份独立 PR 文件均包含在汇编中。CHANGELOG 按用户可见主题合并，每个 PR 至少有一处标准链接。

## 未完成项与 D9

编排方整理：`unfinished.md` 引自 `ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/task.md`，frontmatter 原样状态为 `status: in-progress`、`completed_at: null`。以下保留源文件 :1263-1271 的表格原文，均为 **pending，未验证**，不是通过证据：

| pending 项 | 精确原因／停止边界 |
|---|---|
| D9：AC-33／AC-62 用户 Mac 人工视觉／字体确认——pending | 原因：只能由用户 Mac 真机产出，本会话无法产出，按用户 2026-10-24 22:48 群内确认（D9 等 Mac 证据时停），Lord 记录 |
| macOS 实机性能——pending | 本机仅Linux VM，不能生成Mac原生版本／硬件／性能报告；等用户Mac证据，可用同一脚本复跑 |
| Mac 上 JPEG／PDF 字节数、字体／长页／分页视觉——pending | 只能在Mac实际renderer／字体下取得；本机JPEG/PDF unavailable，Linux HTML几何不能替代 |
| 原生 Windows 性能——pending | 无Windows真机，本轮无CI运行授权／远端操作；后续只能以真实CI runner报告标注来源，不能冒充真机 |
| 百万事件／1万任务／10万步骤及百万CSV——pending | 本轮完整写入成本与软时限只取得最大11500事件；未外推，CSV实现非流式，性能优化不在本PR |
| 完整四格式容量／平台资源上限／最大长图CSV规模——pending | JPEG/PDF缺实测与平台证据；缺失值未当0，未修改默认值／PRD／schema；需要规则变更的项另行处理 |
| R2.2 收尾——pending | D9未满足，不执行任务完成状态、completed_at或plan R2.2行变更；status保持in-progress、completed_at保持null，plan原行逐字不变 |

上述「本机／本轮」属于源记录的历史上下文，不是本 E 任务重新测量的结果。D9 没有通过记录；#186 浅色导出没有 CI 覆盖，不能用参数接线测试、深色 E2E 或 Linux 几何检查替代 Mac 人工视觉／字体证据。

## 已知限制来源

编排方整理：`known-limitations.md` 的结论为：仓库中未找到"沿用之前五条"字样；唯一五条编号列表为 #191（`ai/tasks/v2.1.0-rc.2-contract-bucket-ceiling/task.md:105-119`），不是 rc.1 的通用限制列表。

- #191 五项分别为：全库事件指纹下持续到达时单页固定 30 秒轮询仍可达 2880 快照／天（不含手动请求或多页，降幅不可考）；30 秒轮询请求不减少、不保证不同 snapshot_id 或性能收益；后端不拒绝晚于 as_of 的取整终点；复用时响应 meta.as_of 可能不同于 snapshot.as_of；只取整前端预置，不自动取整所有 API 请求。无新数据每日 288 次只是来源不可考的目标，不作为硬上限或收益承诺。
- 延后项另列：401 重新配对未实现，当前只停止轮询并提示重启 serve 后重新配对；快照内存淘汰未实现，启动仍装载全部快照，无内存淘汰策略。不虚构 LRU／懒加载已经落地。
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

- 自检 1：`git status --short` 实际仅输出下列两份修改与新 task 目录；`git diff --check` exit 0、无输出。只读字节对照证明插入新章节后，两份 CHANGELOG 的原文件前缀与全部历史章节保持原样。

  ```text
   M CHANGELOG.md
   M CHANGELOG.zh.md
  ?? ai/tasks/v2.1.0-rc.2-e-prerelease/
  ```

- 自检 2：按 `git diff -U0 -- CHANGELOG.md CHANGELOG.zh.md` 的新增行（排除文件头）扫描，禁词 0 命中；本 task 与仓库外的发布说明草稿（编排方保管，不入库）全文扫描均为 0；本 task 的本机工作区绝对路径前缀出现 0 次。不扫描或修改历史章节中的既有命中。
- 自检 3：两份新章节各覆盖 50/50 个 PR，缺失列表均为 `[]`，即 #141–#191 除 #143。逐条 PR 链接及顺序相同，代码标识多重集合相同；章节条目数分别为 Added／新增 8、Changed／变更 10、Fixed／修复 6、Candidate Boundaries and Known Limitations／候选边界与已知限制 12。发布说明的中英正文与对应 CHANGELOG 新章节逐字节一致，末尾对比链接行精确匹配。
- 内存检查过程保留：第一次链接正则遗漏方括号转义，错误报出全部编号缺失；修正正则后覆盖通过。第二次错误要求翻译句内代码标识出现顺序也相同，命中 `202` 与 `export_id` 的中英语序差异；改为逐条比较标识多重集合后通过，PR 链接顺序仍逐条严格比较。未修改文档迎合检查脚本，未创建临时脚本文件。最终输出 `SELF_CHECK_1_2_3_OK`，exit 0。
- 自检 4：仓库根实际运行 `python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" ai/tasks/v2.1.0-rc.2-e-prerelease/task.md`，初次输出 `ai/tasks/v2.1.0-rc.2-e-prerelease/task.md in-progress False 1 None`，exit 0。
- 自检 5：一次运行 `python3 -B -m unittest tests.test_sbtd_task_document tests.test_sbtd_task_legacy_events_notice tests.test_sbtd_task_recovery tests.test_sbtd_task_routing tests.test_sbtd_task_schema tests.test_sbtd_task_state tests.test_sbtd_task_status_sync tests.test_sbtd_task_sync_git`，原生结果为 `Ran 135 tests in 58.284s`、`OK`，exit 0。输出包含测试路径产生的「旧格式事件，不追溯」提示，不是本 task 被识别为旧格式。未重跑该套件。
- 自检 6：checking 事件写入后再次执行上述 parser，实际输出 `ai/tasks/v2.1.0-rc.2-e-prerelease/task.md checking False 2 None`，exit 0；新增章节及两个新文档禁词均 0 命中，本 task 的本机工作区绝对路径前缀为 0。范围／diff／双语覆盖／历史字节与发布说明一致性也再次通过，输出 `SELF_CHECK_1_2_3_OK`。事件时间分别来自两次单独执行 `TZ=Asia/Shanghai date -Iseconds`：`2026-10-28T00:04:56+08:00` 与 `2026-10-28T00:14:28+08:00`，后者晚于前者。本结果补入后再次运行 parser 与禁词检查，不重跑 unittest。
- 编排方整理，基线 CI：精确 SHA `55d7b6230f1fe9f302cc06b5100376bdd344aae5`，run [40526884945](https://github.com/KunoLu/640-skills/actions/runs/40526884945)，workflow `validation`，event `push`，attempt 1，conclusion `success`，2026-10-27 23:24:24 (UTC+8) 完成。按名称 13 个作业全部 success：`dashboard-artifacts`、`linux-full`、`linux-shards (1)`、`linux-shards (2)`、`linux-shards (3)`、`macos-bash-installer`、`runtime-e2e-macos`、`runtime-e2e-windows`、`windows-powershell-installer`、`windows-shards (1)`、`windows-shards (2)`、`windows-shards (3)`、`windows-shards (4)`。该 run 各平台测试计数为 `unknown`，事实目录未采集。
- 本 PR 自身 CI 与 Reviewy 审阅尚待进行，不能写成已通过。保持 `completed_at: null`；之后另一轮取得 CI 13/13 与 Reviewy CLEAN 才可写入完成事件。
- 仓库没有检查两份 CHANGELOG 一致性的测试（`meta.md:55`）；本轮使用内存只读检查，并运行任务模块回归与真实 TaskDocument 解析。不修改测试。
- Evidence Source：developer-local；Source Revision：dirty；Environment Alignment：unverified；Evidence Publication：local-only。不是正式 CI／发布验收报告。rtk：not-needed，采用约定原生命令；Final Test Report／Run Summary MD：not-needed，不创建额外报告文件。BDD：skipped，仅文档、无 .feature 或行为变化；Cross-repo context／API Contract：not-needed；Mock Strategy：none。不跑构建、额外 lint／formatter、Web／Mobile E2E 或全量 CI，无相应代码变更且本轮禁止构建／联网。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | model_usage | 产出 |
|---|---|---|---|---|---|
| 1 | ping 第 1 次 | openai-codex/gpt-6-astra（high） | 1／0（2026-10-28 00:00:04 (UTC+8) 开始，编排方据会话 jsonl 统计） | 编排方据会话 jsonl 统计（executor-counted） | 连通性检查 |
| 2 | main 第 1 次（2026-10-28 00:00:26 (UTC+8) 开始） | openai-codex/gpt-6-astra（high） | 6／18（编排方据会话 jsonl 统计） | 编排方据会话 jsonl 统计（executor-counted） | 未写入任何文件；因提示中禁词检查范围与历史 CHANGELOG 既有命中冲突而如实停止，提示随后由编排方修正检查范围 |
| 3 | ping 第 2 次 | openai-codex/gpt-6-astra（high） | 1／0（2026-10-28 00:02:46 (UTC+8) 开始，编排方据会话 jsonl 统计） | 编排方据会话 jsonl 统计（executor-counted） | 连通性检查 |
| 4 | main 第 2 次（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数由编排方据会话 jsonl 统计，见 PR 描述 | 编排方据会话 jsonl 统计（executor-counted） | 两份 CHANGELOG、本任务、仓库外的发布说明草稿（编排方保管，不入库）与本地自检 |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-28T00:04:56+08:00 | planned | in-progress | 编排方整理：按明确的 strict 文档范围建立 E 任务，由 omp 唯一写入。 | 开始写本文件前单独执行 TZ=Asia/Shanghai date -Iseconds 的实际输出；分支、基线、干净工作区、目标不存在与路径安全已核对；事实已通读，未经 TaskStore 写入。 |
| 2026-10-28T00:14:28+08:00 | in-progress | checking | 编排方整理：本地自检完成，进入 checking；本 PR 的 CI 与 Reviewy 审阅尚待进行，不标完成。 | 单独执行 TZ=Asia/Shanghai date -Iseconds 的实际输出；八模块 Ran 135 tests in 58.284s，OK，exit 0，仅运行一次；初次 parser 为 in-progress False 1 None；双语条目数 8／10／6／12，各覆盖 50/50 PR，逐条链接与标识一致，历史字节保留；范围符合授权，diff --check 干净，新增章节及两个新文档禁词 0 命中；检查脚本修正过程见验证节；本事件后复跑 parser 与禁词检查，completed_at 保持 null。 |
