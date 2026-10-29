---
schema_version: 1
id: v2.1.0-rc.3-changelog
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：strict；omp 为唯一内容 writer，不启动子代理或 advisor；提交、推送与开 PR 由编排方执行
status: checking
branch: docs/v2.1.0-rc.3-changelog
created_at: '2026-10-29T16:41:26+08:00'
updated_at: '2026-10-29T16:47:50+08:00'
completed_at: null
---

# v2.1.0-rc.3 CHANGELOG 定稿（第 1 轮）

## 目标

定稿中英文 rc.3 CHANGELOG，补齐 #199／#201／#202，复核 rc.2 候选边界，建立 strict 任务记录并生成 index 导航。本轮只推进至 checking，completed_at 保持 null，不执行发布。

## 决定与归属

Lord 2026-10-29 群内安排（依用户「发布 v2.1.0-rc.3」要求）：准备 docs-only PR，rc.3 日期写为北京时间 2026-10-29，复核候选边界与已知限制，版本元数据不升版。注：分钟不可考。

未完整调用 grill-with-docs：四个写入路径、内容归类、状态终点与验收条件明确，无领域歧义。不扩展其他用户或 Lord 归属，不读取或统计会话 jsonl。

## 范围与边界

仅以下四个文件：

1. `CHANGELOG.md`：rc.3 日期、合并条目与候选边界。
2. `CHANGELOG.zh.md`：逐条对应英文版本。
3. `ai/tasks/v2.1.0-rc.3-changelog/task.md`：本轮任务与证据。
4. `ai/tasks/index.md`：只由约定生成器新增本任务的一行导航。

不改源码、测试、PRD、contracts 或版本元数据；不打 tag、不发 Release、不合并，不执行 Git 写命令、不联网、不安装，不启动子代理或 advisor，不读取凭据、不打印环境变量。Python 均使用 `python3 -B`，不写临时脚本、报告、active、handoff、ignore 或身份文件。

两份 CHANGELOG 顶部仍保留“创建对应 tag 后补充发布日期”的一般说明；本次按上述安排先将 rc.3 标题写成 2026-10-29，是本轮日期安排，不是 tag／Release 已存在的证明。当前 rc.3 tag／Release 尚不存在，不添加发布段落。rc.2 及更早章节一字不改。

沿用两个 rc.2 模板的手写 task 先例，不调用 TaskStore 写方法；parser 与 `_history` 只读核验。index 单独使用约定的 `TaskStore(Path.cwd(), read_only=True)` catalog／candidate 生成器，最终仅将候选字节写到 index。不声称自动恢复或 helper 状态转换已经执行。

写前已核对：分支与 frontmatter 一致，HEAD 与本地 origin/main 均为 `1eb0e14eeab1544344873e400785efa67761ca1f`，`git status --porcelain` 无输出。三个既有目标为普通文件，根、ai、ai/tasks 为目录；新任务目录此前不存在。已读取根 ignore 规则；最终以含 ignored／展开未跟踪文件的 status 检查目标可见性及写入范围。

## #199／#201／#202 归类依据

已用 `git show` 读取以下真实 diff，不以提交标题代替证据；#202 的 static bundle 跳过。

| PR／归类 | 提交 SHA | 已读改动文件与依据 |
|---|---|---|
| #199 → Fixed／修复，并入 #196 | `247735ac1994328d1ec62ab7a14e0c81d39e97c5` | 仅 `tests/test_onboard_external_skills.py` 与 `tests/run_ci.py`。前者按 last-match-wins 核验 `sbtd-workflow-onboard/**` 与 `/LICENSE` 的有效 `-text`，拒绝 payload 规则后重开 text 转换的子规则；后者将 `WindowsShimExecutionTests` 两个真实 cmd.exe 用例加入 `WINDOWS_CASES` 必需原生集，防止选中但 skip 仍绿。是 #196 两个回归守卫的加固，无生产代码变化。 |
| #201 → Added／新增，并入 #200 | `612076e7c648b4b141036491489312f9d530c727` | `sbtd-runtime/dashboard/src/App.tsx`、`i18n.ts`、`i18n.test.ts` 与 `sbtd-runtime/export_render.py`。`footer_rows_note` 恢复「行预览 基于」的空格；测试钉住 `footer_export_note`、`footer_rows_note`、`error_unpaired`，并断言插值后无残留占位符。`live_badge` 入双语词典；`_presentation` 对非字符串 locale 以 isinstance 守卫回落 zh；capability 保存原始 error，渲染时按当前语言翻译，effect 不再依赖 locale。属于 #200 新增双语能力的 review 修复，不另起重复条目。 |
| #202 → Changed／变更，紧接 #200 | `15892b14ba81ac8c92618d24f0fae189174db114` | `sbtd-runtime/dashboard/src/App.tsx`、`PanelCard.tsx`、`app.css`；`sbtd-runtime/contracts/panel-manifest.json`；`sbtd-runtime/tests/test_panel_manifest.py`；`docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md`。本地时钟用 `toLocaleTimeString` 与 `hourCycle: "h23"`；标题居左、右侧明细按钮与 panel-id 成组，按钮透明 ghost；明细表格发丝行线与行 hover。component-usage 半宽 order 8→7，gate-matrix 整宽 7→8，blockers 与 component-usage 同排；按 panel_id 比较仅 order 变化，数据字段不变；manifest_version 1.0.0→1.1.0，release 仍为 rc.2，hash pin、PANEL_IDS 与 PRD 表同步。h23 午夜问题在该 PR 开发中修正，不作为已发布缺陷列入 Fixed。 |

另核对 `sbtd-runtime/export_render.py:310-322`：`_ordered_panels` 按 manifest order 排序，`default_presentation` 据此生成 panel_order，因此新默认顺序同样作用于导出。这里是源码核验，不是本轮导出实测。

## 候选边界复核表

比较基线为 `v2.1.0-rc.2`（`e45565aa940f41bb42c3a62d00921b505f2caa30`）至 `1eb0e14eeab1544344873e400785efa67761ca1f`；rc.2 原候选边界逐项复核如下。

| 项目 | 结论 | 依据 |
|---|---|---|
| 版本元数据不统一升到 rc.3 | 成立 | 当前四份 contract 元数据见下一节；本轮零 contract 写入。 |
| runtime 可选、观察默认关闭、显式注册／开启、前台 serve、仅 127.0.0.1、Ctrl-C 退出、无后台采集器／定时器 | 成立 | rc.2 原边界；facade.py 区间 diff 无输出，serve.py 唯一变化为 presentation_state 接受可选 locale；不改变启动或绑定。 |
| 快照已落盘；源码发布不执行安装、workflow sync、迁移、宿主重载或备份处置 | rc.2 遗留 | rc.2 原边界；report_snapshot.py 无区间改动，本轮只改文档，不执行部署。 |
| R2.2 状态与尚缺的性能／规模／容量证据 | 成立 | R2.2 task frontmatter 为 in-progress、completed_at 为 null；:1264-1272 与 :1288-1294 仍列 macOS／Windows 原生性能、Mac JPEG/PDF 字节数、百万事件／1万任务／10万步骤及百万 CSV、完整四格式容量／平台资源上限／最大长图 CSV 规模、R2.2 收尾。rc.2 至 HEAD 的相关变更未补这些证据。 |
| 浅色主题导出无 CI 覆盖 | rc.2 遗留 | rc.2 原限制；区间内 .github 无改动，runtime 测试改动仅 locale 导出／HTTP 接受与 panel manifest；新增导出测试仍使用默认 dark，未新增浅色导出 CI 场景。 |
| 审计全量 replay／排序分页、CSV 完整缓冲、11,500 事件而非百万级、Windows ACL 缺本机实证、query.executed 不持久化 | rc.2 遗留 | rc.2 原限制与 R2.2 未完成表；stats_query.py、csv_export.py、event_store.py、facade.py 区间 diff 无输出，不把旧有小规模测量当本轮验证。 |
| 查询桶限制 (1)：全库指纹、固定单页 30 秒轮询上界 2880／天，降幅未知，288／天目标非硬上限 | rc.2 遗留 | rc.2 编号列表；stats_query.py、report_snapshot.py 无区间改动，timeRange.ts 仅 i18n，预置 300 秒取整未改。 |
| 查询桶限制 (2)：请求仍发送，不保证新 snapshot_id 或性能收益 | rc.2 遗留 | 同上；本轮无收益测量。 |
| 查询桶限制 (3)：后端不拒绝晚于 as_of 的取整终点 | rc.2 遗留 | stats_query.py 未改；serve.py 仅可选 locale。 |
| 查询桶限制 (4)：复用时 meta.as_of 与 snapshot.as_of 可不同 | rc.2 遗留 | stats_query.py、report_snapshot.py 未改。 |
| 查询桶限制 (5)：仅前端预置取整，不自动取整所有 API 请求 | rc.2 遗留 | timeRange.ts 保留取整逻辑；openapi.yaml 仅增加 locale 描述。 |
| 401 不自动重新配对；导出轮询停止并提示重启 serve，主快照 30 秒轮询不因此停止 | rc.2 遗留 | api.ts、exportJob.ts 的区间 diff 为 locale 文案／传递调整，401 控制流未改。 |
| 快照内存淘汰未实现，启动仍加载全部快照 | rc.2 遗留 | report_snapshot.py 未改，磁盘清扫与文件校验缓存仍不等于内存淘汰。 |
| 缓存／offload 注意事项，包括身份字段未变的改写、取消后的工作线程、可变返回对象及条件性异常映射证据不足 | rc.2 遗留 | report_snapshot.py、export_store.py、disk_quota.py、stats_query.py 无区间改动；serve.py 仅可选 locale，不改 rc.2 所述机制。 |
| 仓库外新增性能／容量结果及本 PR CI 结果 | 未知 | 本轮不联网、不运行平台测量或 CI，不以文档检查替代。 |

rc.3 CHANGELOG 将遗留实现限制合为一条，明确指向 rc.2 同名小节，不复制完整编号列表、不改 rc.2 原文。

## 版本元数据现状

| 文件／字段 | 当前值 |
|---|---|
| `sbtd-runtime/contracts/openapi.yaml`：`info.x-sbtd-release` | `v2.1.0-rc.1` |
| 同文件 info summary | 仍含 `Contract draft for v2.1.0-rc.1` |
| 同文件导出 operation 的 `x-sbtd-release` | `v2.1.0-rc.2` |
| `sbtd-runtime/contracts/capability-matrix.json`：`release` | `v2.1.0-rc.1` |
| `sbtd-runtime/contracts/metrics-catalog.json`：`release` | `v2.1.0-rc.1` |
| `sbtd-runtime/contracts/panel-manifest.json`：`release`／`manifest_version` | `v2.1.0-rc.2`／`1.1.0` |

本 PR 不升版本；标题日期不表示这些 contract 已统一升版。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮适用性与结果 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求前 | not-needed；未完整 grill，文档范围与归类明确 |
| book-ddia-data-design | schema、迁移或持久化机制设计前 | not-needed；只记录既有元数据，不改数据机制 |
| book-legacy-change-safety | 既有行为修改前 | not-needed；无行为修改，历史章节保留 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；不改生产代码、不重构 |
| book-release-readiness | 运行时或部署变化，验证后 | not-needed；仅定稿文档，不执行发布、部署或声称发布就绪 |

## 验证与剩余边界

本轮实际检查如下，均在本地未提交工作区执行；Python 均使用 `python3 -B`，检查脚本只在内存运行，没有落盘脚本或额外报告。

1. 初始身份：`git rev-parse HEAD` 与 `git rev-parse origin/main` 均为 `1eb0e14eeab1544344873e400785efa67761ca1f`，分支为 `docs/v2.1.0-rc.3-changelog`，修改前 `git status --porcelain` 无输出。创建、开始内容执行、进入 checking 分别单独调用 `date '+%Y-%m-%dT%H:%M:%S+08:00'`，实际时间见三条状态事件；`date '+%z'` 输出 `+0800`。本节写入前同一 date 命令输出 `2026-10-29T16:47:50+08:00`，用于 updated_at。
2. 按约定运行 index 生成器，exit 0，实际输出 `INDEX_REGEN changed=True rows=74`。catalog 同时输出既有任务的「旧格式事件，不追溯」提示；本任务单独解析为 False，不把 catalog 提示归给本任务。`git diff -- ai/tasks/index.md` 只有新增 `- [v2.1.0-rc.3-changelog](v2.1.0-rc.3-changelog/task.md)`；内存字节对照也证明删去此行即与 HEAD 原文相同，输出 `INDEX_EXACT_ONE_ADDITION_OK`。
3. 运行下方原生命令，exit 0，实际输出 `ai/tasks/v2.1.0-rc.3-changelog/task.md checking False 3 None`。另在 `python3 -B` 内只读执行 `TaskStore._history(doc)`，实际返回 `(None, True)`；frontmatter 字段顺序、strict／user 模式、分支与 HEAD 也通过断言。

   ```sh
   python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" ai/tasks/v2.1.0-rc.3-changelog/task.md
   ```

4. 禁用项检查：`python3 -B` 脚本扫描本 task 全文与两份 CHANGELOG 各自 `git diff -U0` 的新增行（排除 `+++` 文件头）。第 1 项大小写不敏感，其余按连续子串计数，14 项 × 3 范围共 42 个计数均为 0；本 task 的额外绝对路径前缀计数也为 0，输出 `BAN_COUNTS_OK 14 x 3 = 42 zero counts; TASK_PATH_PREFIX 0`。下表只用 Unicode 码点引用禁用项。

| 禁用项（Unicode 码点） | task.md 全文 | CHANGELOG.md 新增行 | CHANGELOG.zh.md 新增行 |
|---|---|---|---|
| 1：U+0063 U+006F U+006E U+0066 U+0069 U+0072 U+006D U+0065 U+0064 | 0 | 0 | 0 |
| 2：U+7528 U+6237 U+6307 U+5B9A | 0 | 0 | 0 |
| 3：U+5DE6 U+53F3 | 0 | 0 | 0 |
| 4：U+540E U+7EED U+56DE U+586B | 0 | 0 | 0 |
| 5：U+0076 U+0069 U+0074 U+0065 U+0073 U+0074 | 0 | 0 | 0 |
| 6：U+002F U+0068 U+006F U+006D U+0065 U+002F U+0062 U+006F U+0078 | 0 | 0 | 0 |
| 7：U+007E U+002F | 0 | 0 | 0 |
| 8：U+8FBE U+6807 | 0 | 0 | 0 |
| 9：U+7528 U+6237 U+63D0 U+4F9B | 0 | 0 | 0 |
| 10：U+672C U+6B21 U+4EFB U+52A1 U+63D0 U+4F9B U+7684 | 0 | 0 | 0 |
| 11：U+7F16 U+6392 U+65B9 U+8F6C U+8FF0 | 0 | 0 | 0 |
| 12：U+7528 U+6237 U+6240 U+6307 | 0 | 0 | 0 |
| 13：U+7F16 U+6392 U+65B9 U+63D0 U+4F9B U+7684 | 0 | 0 | 0 |
| 14：U+0043 U+006F U+0064 U+0065 U+0058 U+0020 U+7FA4 U+5185 U+8865 U+5145 | 0 | 0 | 0 |
| 额外：U+002F U+0077 U+006F U+0072 U+006B U+0073 U+0070 U+0061 U+0063 U+0065 | 0 | 不适用 | 不适用 |

5. 双语脚本比对：rc.3 两份小节条目数均为 Added／新增 1、Changed／变更 4、Fixed／修复 1、候选边界 4，共 10 条；PR 链接集合均为 #196–#202。10 条逐条 PR 链接及顺序一致，SHA 与代码标识多重集合一致，链接编号与 URL 尾号匹配。输出 `BILINGUAL_ENTRY_LINK_SHA_CODE_OK 10 entries`；文件头以及 rc.2 起至文件末尾均与 HEAD 逐字节一致，输出 `HEADER_AND_RC2_HISTORY_BYTES_OK`。
6. `git diff --check` exit 0、无输出。`git status --porcelain --untracked-files=all` 仅输出下列四个路径；含 `--ignored` 的目标检查无忽略项，四个目标为普通文件、目标及其父路径无 symlink。输出 `SCOPE_PATHS_IGNORE_OK 4 files; DIFF_CHECK_OK`。

   ```text
    M CHANGELOG.md
    M CHANGELOG.zh.md
    M ai/tasks/index.md
   ?? ai/tasks/v2.1.0-rc.3-changelog/task.md
   ```

7. 只读证据补验：七个 runtime 文件的 rc.2 至 HEAD `git diff --stat` 均无输出；#202 前后 manifest 解析为按 panel_id 索引的对象，去掉 order 后完全相同，仅 gate-matrix 7→8、component-usage 8→7，输出 `RUNTIME_SEVEN_FILES_UNCHANGED; MANIFEST_ORDER_ONLY_OK`。这是源码／数据对照，不是运行时测试。
8. 整组检查 exit 0，输出 `DOCUMENT_SELF_CHECK_OK`。记录上述结果后，再对最终文档执行同组只读复核；最终行数与复核结果随交付回复提供。未执行的性能／平台／CI 检查仍为未知，不据此关闭 R2.2 或声称发布就绪。

rtk：not-needed，使用约定原生命令。BDD：skipped，无行为或 .feature 变化；Cross-repo context／API Contract：not-needed；Mock Strategy：none。单元／集成／Web／Mobile E2E、构建、额外 lint／formatter 与全量 CI 不运行：本轮纯文档且写入范围封闭。Final Test Report／Run Summary MD：not-needed，不创建额外报告。独立 review：not-needed，未触发生产迁移、授权或跨系统接口修改条件；未启动子代理或 advisor，自核不是独立审查。

Evidence Source：developer-local；Source Revision：dirty；Environment Alignment：unverified；Evidence Publication：local-only。验证绑定上述基线的本地未提交文档，不是 PR tip CI 或运行时验收。本轮不关闭 R2.2、不承诺自动恢复；提交、推送、开 PR 留给编排方。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | model_usage | 产出 |
|---|---|---|---|---|---|
| 1 | ping 第 1 轮 | openai-codex/gpt-6-astra（high） | 未知（写入时本会话尚未结束；由编排方在 done 轮据会话 jsonl 统计（executor-counted）补写） | 未知（写入时本会话尚未结束；由编排方在 done 轮据会话 jsonl 统计（executor-counted）补写） | 连通性记录；本轮未读取 ping 会话 |
| 2 | main 第 1 轮 | openai-codex/gpt-6-astra（high） | 未知（写入时本会话尚未结束；由编排方在 done 轮据会话 jsonl 统计（executor-counted）补写） | 未知（写入时本会话尚未结束；由编排方在 done 轮据会话 jsonl 统计（executor-counted）补写） | 四文件文档定稿、候选边界复核与本地自检 |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-29T16:41:26+08:00 | planned | planned | created：建立 strict 文档任务，限定四个文件。 | 写入前 date '+%Y-%m-%dT%H:%M:%S+08:00' 实际输出；分支、HEAD、初始干净工作区与模板已核对。 |
| 2026-10-29T16:43:58+08:00 | planned | in-progress | 开始定稿双语 rc.3 条目与候选边界。 | 本次转换前单独执行 date '+%Y-%m-%dT%H:%M:%S+08:00'；三个提交的真实 diff、rc.2 原边界与当前元数据已核对。 |
| 2026-10-29T16:45:48+08:00 | in-progress | checking | 双语正文与任务证据已写入，进入生成 index 与本轮文档自检阶段；不标完成。 | 本次转换前单独执行 date '+%Y-%m-%dT%H:%M:%S+08:00'；日期、三个 PR 归类、四条候选边界与版本现状已写入，最终检查结果见验证节。 |
