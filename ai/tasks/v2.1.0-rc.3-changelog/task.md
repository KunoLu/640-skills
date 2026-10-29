---
schema_version: 1
id: v2.1.0-rc.3-changelog
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：strict；omp 为唯一内容 writer，不启动子代理或 advisor；提交、推送与开 PR 由编排方执行
status: done
branch: docs/v2.1.0-rc.3-changelog
created_at: '2026-10-29T16:41:26+08:00'
updated_at: '2026-10-29T21:25:49+08:00'
completed_at: '2026-10-29T21:25:49+08:00'
---

# v2.1.0-rc.3 CHANGELOG 定稿（第 1–2 轮与 done 轮）

## 目标

定稿中英文 rc.3 CHANGELOG，补齐 #199／#201／#202，复核 rc.2 候选边界，建立 strict 任务记录并生成 index 导航。本轮只推进至 checking，completed_at 保持 null，不执行发布。

## 决定与归属

用户 2026-10-29 群内确认（要求发布 v2.1.0-rc.3），Lord 记录：准备 docs-only PR，rc.3 日期写为北京时间 2026-10-29，复核候选边界与已知限制，版本元数据不升版。注：分钟不可考。

未完整调用 grill-with-docs：第 1 轮四个写入路径、第 2 轮三个修复路径、内容归类、状态终点与验收条件明确，无领域歧义。不扩展其他用户或 Lord 归属，不读取或统计会话 jsonl。

## 范围与边界

第 1 轮范围仅以下四个文件；第 2 轮仅修改前三个文件，index 不动：

1. `CHANGELOG.md`：rc.3 日期、合并条目与候选边界。
2. `CHANGELOG.zh.md`：逐条对应英文版本。
3. `ai/tasks/v2.1.0-rc.3-changelog/task.md`：本轮任务与证据。
4. `ai/tasks/index.md`：只由约定生成器新增本任务的一行导航。

不改源码、测试、PRD、contracts 或版本元数据；不打 tag、不发 Release、不合并，不执行 Git 写命令、不联网、不安装，不启动子代理或 advisor，不读取凭据、不打印环境变量。Python 均使用 `python3 -B`，不写临时脚本、报告、active、handoff、ignore 或身份文件。

两份 CHANGELOG 顶部仍保留“创建对应 tag 后补充发布日期”的一般说明；第 1 轮将 rc.3 标题写成 2026-10-29，日期依据见「决定与归属」，不是 tag／Release 已存在的证明。第 2 轮不联网，远端 rc.3 tag／Release 状态未知，不添加发布段落。rc.2 及更早章节一字不改。

沿用两个 rc.2 模板的手写 task 先例，不调用 TaskStore 写方法；parser 与 `_history` 只读核验。第 1 轮 index 单独使用约定的 `TaskStore(Path.cwd(), read_only=True)` catalog／candidate 生成器，最终仅将候选字节写到 index；第 2 轮只在内存比较候选字节，不写 index。不声称自动恢复或 helper 状态转换已经执行。

写前已核对：分支与 frontmatter 一致，HEAD 与本地 origin/main 均为 `1eb0e14eeab1544344873e400785efa67761ca1f`，`git status --porcelain` 无输出。三个既有目标为普通文件，根、ai、ai/tasks 为目录；新任务目录此前不存在。已读取根 ignore 规则；最终以含 ignored／展开未跟踪文件的 status 检查目标可见性及写入范围。

## #199／#201／#202 归类依据

已用 `git show` 读取以下真实 diff，不以提交标题代替证据；#202 的 static bundle 跳过。

| PR／归类 | 提交 SHA | 已读改动文件与依据 |
|---|---|---|
| #199 → Fixed／修复，并入 #196 | `247735ac1994328d1ec62ab7a14e0c81d39e97c5` | 仅 `tests/test_onboard_external_skills.py` 与 `tests/run_ci.py`。前者按 last-match-wins 核验 `sbtd-workflow-onboard/**` 与 `/LICENSE` 的有效 `-text`，拒绝 payload 规则后重开 text 转换的子规则；后者将 `WindowsShimExecutionTests` 两个真实 cmd.exe 用例加入 `WINDOWS_CASES` 必需原生集，防止选中但 skip 仍绿。是 #196 两个回归守卫的加固，无生产代码变化。 |
| #201 → Added／新增，并入 #200 | `612076e7c648b4b141036491489312f9d530c727` | `sbtd-runtime/dashboard/src/App.tsx`、`i18n.ts`、`i18n.test.ts` 与 `sbtd-runtime/export_render.py`。`footer_rows_note` 恢复「行预览 基于」的空格；测试钉住 `footer_export_note`、`footer_rows_note`、`error_unpaired`，并断言插值后无残留占位符。`live_badge` 入双语词典；`_presentation` 对非字符串 locale 以 isinstance 守卫回落 zh；capability 保存原始 error，渲染时按当前语言翻译，effect 不再依赖 locale。属于 #200 新增双语能力的 review 修复，不另起重复条目。 |
| #202 → Changed／变更，紧接 #200 | `15892b14ba81ac8c92618d24f0fae189174db114` | `sbtd-runtime/dashboard/src/App.tsx`、`PanelCard.tsx`、`app.css`；`sbtd-runtime/contracts/panel-manifest.json`；`sbtd-runtime/tests/test_panel_manifest.py`；`docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md`。本地时钟用 `toLocaleTimeString` 与 `hourCycle: "h23"`；标题居左、右侧明细按钮与 panel-id 成组，按钮透明 ghost；明细表格发丝行线与行 hover。component-usage 半宽 order 8→7，gate-matrix 整宽 7→8，blockers 与 component-usage 同排；仅就 panels 数组按 panel_id 比较，除 order 外数据字段不变；manifest_version 1.0.0→1.1.0，release 仍为 rc.2，EXPECTED_MANIFEST_SHA256、EXPECTED_MANIFEST_VERSION、PANEL_IDS 与 PRD v0.2 panel 表顺序同步。h23 午夜问题在该 PR 开发中修正，不作为已发布缺陷列入 Fixed。 |

另核对 `sbtd-runtime/export_render.py:310-322`：`_ordered_panels` 按 manifest order 排序，`default_presentation` 据此生成 panel_order，因此新默认顺序同样作用于导出。这里是源码核验，不是本轮导出实测。

## 候选边界复核表

比较基线为 `v2.1.0-rc.2`（`e45565aa940f41bb42c3a62d00921b505f2caa30`）至 `1eb0e14eeab1544344873e400785efa67761ca1f`；rc.2 原候选边界逐项复核如下。

| 项目 | 结论 | 依据 |
|---|---|---|
| 版本元数据不统一升到 rc.3 | 成立 | 当前四份 contract 元数据见下一节；本 PR 零 contract 写入。rc.2 标签的 manifest_version 为 1.0.0，#202 已升到 1.1.0，release 仍为 v2.1.0-rc.2，不表示 manifest_version 自 rc.2 起未变。 |
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
| `sbtd-runtime/contracts/panel-manifest.json`：`release`／`manifest_version` | `v2.1.0-rc.2`／`1.1.0`；rc.2 标签中后者为 `1.0.0`，由 #202 升为 `1.1.0` |

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

第 1 轮实际检查如下，均在当时本地未提交工作区执行；Python 均使用 `python3 -B`，检查脚本只在内存运行，没有落盘脚本或额外报告。

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

7. 只读证据补验：七个 runtime 文件的 rc.2 至 HEAD `git diff --stat` 均无输出；#202 前后 manifest 的 panels 数组解析为按 panel_id 索引的对象，去掉 order 后完全相同，仅 gate-matrix 7→8、component-usage 8→7，输出 `RUNTIME_SEVEN_FILES_UNCHANGED; MANIFEST_ORDER_ONLY_OK`。此处相同仅指 panels 数组的上述比较，不含 manifest 顶层；顶层 manifest_version 确由 1.0.0 升到 1.1.0。这是源码／数据对照，不是运行时测试。
8. 整组检查 exit 0，输出 `DOCUMENT_SELF_CHECK_OK`。记录上述结果后，再对最终文档执行同组只读复核；最终行数与复核结果随交付回复提供。未执行的性能／平台／CI 检查仍为未知，不据此关闭 R2.2 或声称发布就绪。

rtk：not-needed，使用约定原生命令。BDD：skipped，无行为或 .feature 变化；Cross-repo context／API Contract：not-needed；Mock Strategy：none。单元／集成／Web／Mobile E2E、构建、额外 lint／formatter 与全量 CI 不运行：本轮纯文档且写入范围封闭。Final Test Report／Run Summary MD：not-needed，不创建额外报告。独立 review：not-needed，未触发生产迁移、授权或跨系统接口修改条件；未启动子代理或 advisor，自核不是独立审查。

Evidence Source：developer-local；Source Revision：dirty；Environment Alignment：unverified；Evidence Publication：local-only。验证绑定上述基线的本地未提交文档，不是 PR tip CI 或运行时验收。本轮不关闭 R2.2、不承诺自动恢复；提交、推送、开 PR 留给编排方。

## 第 2 轮

范围：仅修改 `CHANGELOG.md`、`CHANGELOG.zh.md`、`ai/tasks/v2.1.0-rc.3-changelog/task.md`；`ai/tasks/index.md` 不动。沿用 strict，`status: checking` 与 `completed_at: null` 保持不变，不新增状态事件。第 1 轮已提交，本轮只修 review 的两个阻塞项及相关措辞，不处理其他 review 意见。

1. 阻塞项 1：双语 #202 条目改为「#202 将 `manifest_version` 由 `1.0.0` 升到 `1.1.0`，数据字段不变」／“#202 bumps `manifest_version` from `1.0.0` to `1.1.0`, with no data-field changes”，并列明 `EXPECTED_MANIFEST_SHA256`、`EXPECTED_MANIFEST_VERSION`、`PANEL_IDS` 顺序与 PRD v0.2 panel 表顺序同步；删除暗示版本未变的布局限定。时钟、header、排序、导出默认顺序和表格句子经真实 diff／源码核对，保留原文。
2. 阻塞项 2：「决定与归属」改为「用户 2026-10-29 群内确认（要求发布 v2.1.0-rc.3），Lord 记录：准备 docs-only PR，rc.3 日期写为北京时间 2026-10-29，复核候选边界与已知限制，版本元数据不升版。注：分钟不可考。」相应日期说明改为指向该节，不另造归属。
3. 两份 CHANGELOG `:29` 复核：原当前值准确，但连续沿用语气可能被读成 manifest_version 自 rc.2 起未变。最小修改为「#202 已将 `manifest_version` 从 rc.2 时的 `1.0.0` 升为 `1.1.0`」，英文同步；`release` 仍为 `v2.1.0-rc.2`。归类依据、候选边界与版本现状表同步澄清；第 1 轮验证第 7 条限定比较对象为 panels 数组，不包含顶层版本。

### 本轮实际检查

以下结果来自本轮本地工作区；Python 全部为 `python3 -B`，脚本仅在内存运行。初次双语检查失败及修正后的完整检查结果均保留于此；不将第 1 轮结果当作本轮结果。

1. 写前身份：`git rev-parse --abbrev-ref HEAD` 输出 `docs/v2.1.0-rc.3-changelog`，`git rev-parse HEAD` 输出 `9e452c35dd7805627450a02dac6bde0ef8359f28`；`git status --porcelain` 无输出。三个目标与父路径的普通文件／symlink／根内包含关系检查输出 `PATH_SAFETY_OK 3 regular files`；已读根 ignore 规则，目标含 ignored 的 status 无输出。
2. 事实复核：执行 `git show v2.1.0-rc.2:sbtd-runtime/contracts/panel-manifest.json` 及 `git show 15892b14ba81ac8c92618d24f0fae189174db114 -- sbtd-runtime/contracts/panel-manifest.json sbtd-runtime/tests/test_panel_manifest.py docs/prd/`，读取真实 diff；另读该提交的 App.tsx、PanelCard.tsx、app.css diff 与 `export_render.py:310-322`。内存解析 #202 父提交与该提交的 manifest，核对顶层版本、release 及按 panel_id 索引的 panels 数据，输出 `MANIFEST_OK rc2=1.0.0; #202=1.0.0->1.1.0; release=v2.1.0-rc.2; panels differ only in order`。这是源码／数据证据，不是 UI 或导出实测。
3. 执行第 1 轮验证第 3 条所列原生 parser 命令，exit 0，输出 `ai/tasks/v2.1.0-rc.3-changelog/task.md checking False 3 None`；另在 `python3 -B -c` 中只读调用 `TaskStore._history(doc)`，exit 0，输出 `HISTORY (None, True)`。内存对照基线 frontmatter 字段顺序及除 updated_at 外的全部值、状态事件全文和新增模型记录，输出 `TASK_FIELDS_EVENTS_MODEL_ROWS_OK checking null; 3 unchanged events`。未新增 from=to 事件。
4. 执行以下只读 index 命令，exit 0；catalog 输出既有任务的「旧格式事件，不追溯」提示，最终输出 `INDEX_SAME True True`。本任务 parser 的 legacy_events 为 False。task 标题与正文修正未改变生成的 index 行。

   ```sh
   python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); print('INDEX_SAME', b==a, a==Path('ai/tasks/index.md').read_bytes())"
   ```

5. 禁用项脚本：从既有 Unicode 码点表还原 14 项，扫描 task 全文和两份 CHANGELOG 相对 `9e452c3` 的 `git diff -U0` 新增行，排除 `+++` 文件头；第 1 项大小写不敏感。实际逐项输出 `BAN 1 0 0 0` 至 `BAN 14 0 0 0`，汇总 `BAN_COUNTS_OK 14 x 3 = 42 zero counts; TASK_PATH_PREFIX 0`；上表的额外路径前缀也为 0。
6. 双语脚本初次 exit 1：在条目数检查通过后，额外要求句内代码标识出现顺序相同，触发 `AssertionError`。定位输出 `CODE_ORDER_DIFFERENCE 6`、`CODE_ORDER_DIFFERENCE 7`、`CODE_ORDER_DIFFERENCE 8`，是原有英中翻译语序差异；没有据此改写无关条目。改为逐条比较代码标识多重集合，条目顺序及逐条 PR 链接仍严格有序比较，SHA 多重集合也逐条比较。修正后的完整脚本 exit 0，输出如下：

   ```text
   ENTRY_COUNTS CHANGELOG.md 1 4 1 4 TOTAL 10
   ENTRY_COUNTS CHANGELOG.zh.md 1 4 1 4 TOTAL 10
   BILINGUAL_ENTRY_LINK_SHA_CODE_OK 10 entries
   HEADER_AND_RC2_HISTORY_BYTES_OK; CHANGELOG_CHANGED_LINES 19 29 only
   ```

   rc.3 均为新增 1、变更 4、修复 1、候选边界 4；两文件相对 `9e452c3` 仅第 19、29 行改变，文件头及 rc.2 起至末尾逐字节不变。
7. `git diff --check` exit 0、无输出；`git diff 9e452c3 -- ai/tasks/index.md` 无输出。`git status --porcelain --untracked-files=all` 仅输出：

   ```text
    M CHANGELOG.md
    M CHANGELOG.zh.md
    M ai/tasks/v2.1.0-rc.3-changelog/task.md
   ```

   脚本断言三条均为未暂存修改且无额外路径，输出 `SCOPE_OK 3 files; DIFF_CHECK_OK; INDEX_DIFF_EMPTY`；完整脚本最终输出 `ROUND2_DOCUMENT_SELF_CHECK_OK`，exit 0。
8. 最后写入前执行 `date '+%Y-%m-%dT%H:%M:%S+08:00'`，输出 `2026-10-29T17:58:48+08:00`，写入 updated_at；此前 `date '+%z'` 输出 `+0800`。上述记录写入后再执行最终只读复核，结果及最终 +/- 行数随交付回复列出。

验证边界：rtk 为 not-needed，使用要求的原生命令；BDD、单元／集成／UI／E2E、构建、额外 lint／formatter 与 CI 均未运行，原因是本轮只修文档且禁止额外产物，不涉及行为或 .feature 变化。Cross-repo context／API Contract 为 not-needed，Mock Strategy 为 none；Final Test Report／Run Summary MD 为 not-needed，不落盘额外报告。既有 Book Gate Plan 的不适用理由不变；未启动子代理或 advisor，自核不是独立 review。Evidence Source 为 developer-local，Source Revision 为 dirty，Environment Alignment 为 unverified，Evidence Publication 为 local-only；不声称 PR tip CI、运行时验收或发布就绪，远端 tag／Release 状态未知。未提交、推送或执行任何 Git 写命令。

## done 轮

范围：仅修改 `ai/tasks/v2.1.0-rc.3-changelog/task.md`；index 先按约定只读比较，实际输出 `INDEX_SAME True True`，不写 `ai/tasks/index.md`。本 done 记录所在分支为 `docs/v2.1.0-rc.3-changelog-done`，由编排方另开 PR；frontmatter 的 `branch` 保持任务工作分支 `docs/v2.1.0-rc.3-changelog`，不追加 rebinding 事件。

沿用 strict 与既有 Book Gate Plan；未完整调用 grill-with-docs，因本轮事实、归属、写入范围与验收条件明确。手写记录，未经 TaskStore 写入；仅使用 TaskDocument parser、`TaskStore._history` 与 read_only catalog／index candidate 核验，不声称 helper 状态转换或自动恢复已执行。`checking → done` 为合法完成转换，done 为终态；新事件的 `at`、`updated_at`、`completed_at` 使用同一真实时间，不以发布或合入时间代替记录完成时间。

### 事实与来源验证清单

1. 合入：编排方据 gh 核实，PR [#203](https://github.com/KunoLu/640-skills/pull/203) 已 squash 合入 main，合入提交 `ce37b6d5d7487109a92856c7a2c41a8f86efdfba`，合入时间 2026-10-29 19:48:12 (UTC+8)。编排方整理：合入时以 `--match-head-commit` 绑定 PR head `1357da53e2a7c358b2da183a2df45cbf554f4e8d`。只读 git 复核：本地 HEAD 与 origin/main 均为上述合入提交，`git show -s --format=fuller HEAD` 的标题含 `(#203)`；AuthorDate 与 CommitDate 均为 `Thu Oct 29 19:48:11 2026 +0800`，提交时间不等同于 gh 的 PR 合入时间。
2. 合入归属：编排方整理：用户 2026-10-29 群内确认（合入 #203），Lord 记录。注：分钟不可考。「决定与归属」既有发布要求整行不改。
3. 审阅：编排方整理：Reviewy 对 `1357da53e2a7c358b2da183a2df45cbf554f4e8d` 判内容 CLEAN（Reviewy 归属：日期 2026-10-29，注：分钟不可考。）。此结论绑定该 PR head，不是本轮自核或 done 记录提交的独立审阅。
4. PR CI：编排方据 gh 核实，run [40854192642](https://github.com/KunoLu/640-skills/actions/runs/40854192642)，workflow `validation`，event `pull_request`，head `1357da53e2a7c358b2da183a2df45cbf554f4e8d`。attempt 1 conclusion `failure`：`linux-shards (3)` 失败于 `test_sbtd_upgrade_hosts.RealPowerShellWinningCommandTests.test_unshadowed_winning_command_passes_real_probe`，断言 `'failed' != 'verified'`，返回 `{'status': 'failed', 'reason': 'shell-probe-timeout'}`（pwsh 探测超时）；`linux-full` 为汇总作业，因 shard 失败而 `RESULT: failure`。attempt 2 于 2026-10-29 18:23:37 开始、18:40:57 (UTC+8) 完成，13/13 按名 success。编排方整理：本 PR 只改文档，重跑后通过，推断为探测超时偶发，未做根因分析；不将推断写成已证实根因。
5. 合入提交 CI：编排方据 gh 核实，run [40868198008](https://github.com/KunoLu/640-skills/actions/runs/40868198008)，workflow `validation`，event `push`，attempt 1，head `ce37b6d5d7487109a92856c7a2c41a8f86efdfba`，2026-10-29 19:48:15 开始、20:06:08 (UTC+8) 完成，conclusion `success`。13/13 作业按名全部 success：dashboard-artifacts、linux-full、linux-shards (1)、linux-shards (2)、linux-shards (3)、macos-bash-installer、runtime-e2e-macos、runtime-e2e-windows、windows-powershell-installer、windows-shards (1)、windows-shards (2)、windows-shards (3)、windows-shards (4)。各平台测试计数：未知。
6. tag：只读 git 复核 `v2.1.0-rc.3` 为 annotated tag，tag 对象 `1715486dfb6da359d6ec6646e923a70795e4a8fd`，指向合入提交 `ce37b6d5d7487109a92856c7a2c41a8f86efdfba`。`python3 -B -c` 在内存将实际 tagger epoch `1793280012` 按 UTC+8 转换，输出 `TAGGER_TIME 2026-10-29T21:20:12+08:00`。注释为英文／简体中文双语标题、完整双语说明指向 GitHub Release，并含 `Commit:` 行；完整实际输出见下。
7. Release：编排方据 gh 核实，[v2.1.0-rc.3](https://github.com/KunoLu/640-skills/releases/tag/v2.1.0-rc.3)，名称 `v2.1.0-rc.3`，prerelease，非 draft，非 Latest；Latest 仍为 `v2.0.2`（编排方据 releases/latest 核实），2026-10-29 21:20:20 (UTC+8) 发布。编排方整理：正文为 English 与简体中文双语，依据合入后的 CHANGELOG 整理。本会话未访问 Release 或执行 gh。
8. 模型记录：编排方据会话 jsonl 统计（executor-counted）的五个已结束会话数字见下表；本会话两栏不自计。第 2 轮 main 的三条 model_usage 是 omp 自带辅助检索记录，非编排方选择的模型，不影响内容。本轮未读取或统计会话 jsonl，不记录会话文件路径。

### tag 只读复核实际输出

`git cat-file -t v2.1.0-rc.3`，exit 0：

```text
tag
```

`git cat-file -p v2.1.0-rc.3`，exit 0：

```text
object ce37b6d5d7487109a92856c7a2c41a8f86efdfba
type commit
tag v2.1.0-rc.3
tagger 640 <60886434+KunoLu@users.noreply.github.com> 1793280012 +0800

v2.1.0-rc.3: Bilingual Dashboard, omp-style visual refresh, Graft 0.28.0 pin and external Skills refresh (prerelease) / 双语 Dashboard、omp 风格视觉更新、Graft 0.28.0 pin 与外部 Skills 刷新（预发布）

See the GitHub Release for the full English and 简体中文 notes. / 完整双语说明见 GitHub Release。
Commit: ce37b6d5d7487109a92856c7a2c41a8f86efdfba
```

`git rev-parse v2.1.0-rc.3^{commit}`，exit 0：

```text
ce37b6d5d7487109a92856c7a2c41a8f86efdfba
```

`git rev-parse v2.1.0-rc.3`，exit 0：

```text
1715486dfb6da359d6ec6646e923a70795e4a8fd
```

### 本轮实际自检

1. 写前 `git rev-parse --abbrev-ref HEAD` 输出 `docs/v2.1.0-rc.3-changelog-done`；`git rev-parse HEAD` 与 `git rev-parse origin/main` 均输出 `ce37b6d5d7487109a92856c7a2c41a8f86efdfba`；初始 `git status --porcelain` 无输出。已读 ignore 规则，目标含 ignored 的 status 无输出；内存断言目标为已跟踪普通文件、父路径无 symlink、位于授权根内且字节与 HEAD 相同，输出 `PATH_SAFETY_OK tracked regular file; no symlinks; HEAD bytes match`。
2. 改前只读解析输出 `BASELINE checking False 3 None`，`TaskStore._history(doc)` 输出 `HISTORY (None, True)`。按第 2 轮所列原生命令运行只读 index 比较，exit 0，输出 `INDEX_SAME True True`；catalog 同时输出既有任务的「旧格式事件，不追溯」提示，本任务 legacy_events 为 False。
3. 写入前单独执行 `date '+%Y-%m-%dT%H:%M:%S+08:00'`，实际输出 `2026-10-29T21:25:49+08:00`，用于唯一新 done 事件及两个 frontmatter 时间字段；此前 `date '+%z'` 输出 `+0800`。
4. done 记录写入后，执行第 1 轮验证第 3 条所列原生 parser 命令，exit 0；另以 `python3 -B -c` 只读调用 `TaskStore._history(doc)`，exit 0，实际输出：

   ```text
   ai/tasks/v2.1.0-rc.3-changelog/task.md done False 4 2026-10-29T21:25:49+08:00
   HISTORY (None, True)
   ```

5. 改后按同一原生 index 命令只读比较，exit 0，实际输出 `INDEX_SAME True True`；catalog 仍有既有任务的「旧格式事件，不追溯」提示，不归给本任务。另将 index 磁盘字节与 HEAD 比较，输出 `INDEX_HEAD_BYTES_UNCHANGED`；未写 index。
6. `python3 -B -c` 内存脚本断言：前三条状态事件逐字节不变；从「目标」至「第 2 轮」末尾的历史正文整体与 HEAD 逐字节一致；基线第 22 行归属逐字节不变；frontmatter 字段顺序、除 status／updated_at／completed_at 外的所有值及单引号风格保留，done 三处时间相同；六行模型表数字、来源及本会话不自计措辞符合约定。实际输出：

   ```text
   EXISTING_EVENTS_BYTES_OK 3
   ROUND1_ROUND2_BODY_BYTES_OK
   ATTRIBUTION_LINE22_BYTES_OK
   FRONTMATTER_ORDER_VALUES_OK; DONE_TIMESTAMPS_MATCH 2026-10-29T21:25:49+08:00
   MODEL_ROWS_OK 6; CURRENT_SESSION_NOT_SELF_COUNTED
   ```

7. 同一内存脚本从既有 Unicode 码点表还原 14 项，对 task.md 全文、相对 HEAD 的 `git diff -U0` 新增行（排除 `+++` 文件头）逐项计数；第 1 项大小写不敏感，其余为连续子串。额外绝对路径前缀只扫描 task 全文。实际输出：

   ```text
   BAN 1 0 0
   BAN 2 0 0
   BAN 3 0 0
   BAN 4 0 0
   BAN 5 0 0
   BAN 6 0 0
   BAN 7 0 0
   BAN 8 0 0
   BAN 9 0 0
   BAN 10 0 0
   BAN 11 0 0
   BAN 12 0 0
   BAN 13 0 0
   BAN 14 0 0
   BAN_COUNTS_OK 14 x 2 = 28 zero counts; TASK_PATH_PREFIX 0
   ```

8. `git diff --check` exit 0、无输出；`git status --porcelain` 与加 `--untracked-files=all` 的结果相同，恰为唯一授权文件。内存脚本断言范围并输出：

   ```text
   INDEX_HEAD_BYTES_UNCHANGED
   DIFF_CHECK_OK exit 0; no output
   GIT_STATUS_BEGIN
    M ai/tasks/v2.1.0-rc.3-changelog/task.md
   GIT_STATUS_END
   SCOPE_OK 1 file
   DONE_DOCUMENT_SELF_CHECK_OK
   ```

9. 上述检查均 exit 0，Python 全部使用 `python3 -B`，未落盘临时脚本或报告；这些是真实 parser／history／生成器及文档约束自检，不是平台测试。本节写入后再执行一次最终只读复核，最终结果与 +/- 行数随交付回复列出。

### 证据边界

Evidence Source：本轮自检为 developer-local；Source Revision：dirty，基线 `ce37b6d5d7487109a92856c7a2c41a8f86efdfba`；Environment Alignment：unverified；Evidence Publication：local-only。CI 与 Release 事实来自编排方据 gh 核实，Reviewy 与群内归属为编排方整理；本地 git 仅复核本地提交与 tag，不替代远端状态核验。上述 CI 与 CLEAN 只覆盖各自 SHA，done 记录提交的 CI 与审阅结果未知，不以合入提交 CI 冒充新提交验证。不声称运行时验收，R2.2 状态不变，仍为 `in-progress`、`completed_at: null`；性能／规模／容量缺口未重测。第 1–2 轮历史正文与三条事件逐字保留，当时远端 tag／Release 未知的记录不追溯改写。

rtk：not-needed，使用约定原生命令。BDD：skipped，无行为或 .feature 变化；Cross-repo context／API Contract：not-needed；Mock Strategy：none。未运行单元／集成／UI／E2E、构建、额外 lint／formatter 或 CI，本轮为封闭范围文档补记；Final Test Report／Run Summary MD：not-needed，不创建额外报告或临时脚本。既有 Book Gate Plan 的不适用理由不变，未触发独立复核条件；未启动子代理或 advisor，自核不冒称独立 review。本轮未联网、未安装、未执行 Git 写命令、未操作 tag／Release，未提交或推送；由编排方另开 PR。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | model_usage | 产出 |
|---|---|---|---|---|---|
| 1 | ping 第 1 轮（2026-10-29 16:39:49 (UTC+8) 开始） | openai-codex/gpt-6-astra（high） | 1／0（编排方据会话 jsonl 统计（executor-counted）） | 无 model_usage 记录（编排方据会话 jsonl 统计（executor-counted）） | 连通性记录；本轮未读取 ping 会话 |
| 2 | main 第 1 轮（2026-10-29 16:39:58 (UTC+8) 开始） | openai-codex/gpt-6-astra（high） | 19／54（编排方据会话 jsonl 统计（executor-counted）） | 无 model_usage 记录（编排方据会话 jsonl 统计（executor-counted）） | 四文件文档定稿、候选边界复核与本地自检 |
| 3 | ping 第 2 轮（2026-10-29 17:54:49 (UTC+8) 开始） | openai-codex/gpt-6-astra（high） | 1／0（编排方据会话 jsonl 统计（executor-counted）） | 无 model_usage 记录（编排方据会话 jsonl 统计（executor-counted）） | 连通性记录；本轮未读取 ping 会话 |
| 4 | main 第 2 轮（2026-10-29 17:54:57 (UTC+8) 开始） | openai-codex/gpt-6-astra（high） | 17／39（编排方据会话 jsonl 统计（executor-counted）） | 存在，round2 有 3 条（typesafe/jev-latest，purpose find）；编排方据会话 jsonl 统计（executor-counted）；omp 自带辅助检索记录，非编排方选择 | 双语阻塞项、归属与证据措辞修正；本地只读自检 |
| 5 | ping done 轮（2026-10-29 21:22:32 (UTC+8) 开始） | openai-codex/gpt-6-astra（high） | 1／0（编排方据会话 jsonl 统计（executor-counted）） | 无 model_usage 记录（编排方据会话 jsonl 统计（executor-counted）） | 连通性记录；本轮未读取 ping 会话 |
| 6 | main done 轮（本会话） | openai-codex/gpt-6-astra（high） | 本会话落盘时尚未结束，计数不在本文件自计；以编排方报告为准（executor-counted） | 本会话落盘时尚未结束，计数不在本文件自计；以编排方报告为准（executor-counted） | done 事件、frontmatter、合入与发布事实、模型记录及本地只读自检 |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-29T16:41:26+08:00 | planned | planned | created：建立 strict 文档任务，限定四个文件。 | 写入前 date '+%Y-%m-%dT%H:%M:%S+08:00' 实际输出；分支、HEAD、初始干净工作区与模板已核对。 |
| 2026-10-29T16:43:58+08:00 | planned | in-progress | 开始定稿双语 rc.3 条目与候选边界。 | 本次转换前单独执行 date '+%Y-%m-%dT%H:%M:%S+08:00'；三个提交的真实 diff、rc.2 原边界与当前元数据已核对。 |
| 2026-10-29T16:45:48+08:00 | in-progress | checking | 双语正文与任务证据已写入，进入生成 index 与本轮文档自检阶段；不标完成。 | 本次转换前单独执行 date '+%Y-%m-%dT%H:%M:%S+08:00'；日期、三个 PR 归类、四条候选边界与版本现状已写入，最终检查结果见验证节。 |
| 2026-10-29T21:25:49+08:00 | checking | done | 编排方整理：PR #203 已 squash 合入 `ce37b6d`，补记 checking → done。用户 2026-10-29 群内确认（合入 #203），Lord 记录。注：分钟不可考。 | 手写，未经 TaskStore 写入；at 来自写入前单独执行 date '+%Y-%m-%dT%H:%M:%S+08:00'。编排方据 gh 核实：PR #203 于 2026-10-29 19:48:12 (UTC+8) squash 合入 main，合入提交 `ce37b6d5d7487109a92856c7a2c41a8f86efdfba`；编排方整理：合入使用 `--match-head-commit` 绑定 `1357da53e2a7c358b2da183a2df45cbf554f4e8d`，Reviewy 对该 head 判内容 CLEAN（Reviewy 归属：日期 2026-10-29，注：分钟不可考。）。编排方据 gh 核实：run 40854192642（validation，pull_request，head `1357da5`）attempt 1 failure，linux-shards (3) 的 test_sbtd_upgrade_hosts.RealPowerShellWinningCommandTests.test_unshadowed_winning_command_passes_real_probe 断言 'failed' != 'verified'，返回 {'status': 'failed', 'reason': 'shell-probe-timeout'}；linux-full 为汇总作业，因 shard 失败而 RESULT: failure；attempt 2 于 2026-10-29 18:23:37 至 18:40:57 (UTC+8) 运行，13/13 按名 success。本 PR 只改文档且重跑通过，推断为探测超时偶发，未做根因分析。编排方据 gh 核实：run 40868198008（validation，push，attempt 1，head `ce37b6d`）于 2026-10-29 19:48:15 开始、20:06:08 (UTC+8) 完成，conclusion success，13/13 按名全部 success，完整作业名见 done 轮清单；各平台测试计数未知。只读 git 复核：annotated tag v2.1.0-rc.3，对象 `1715486dfb6da359d6ec6646e923a70795e4a8fd`，指向 `ce37b6d5d7487109a92856c7a2c41a8f86efdfba`，tagger 时间 2026-10-29 21:20:12 (UTC+8)，双语注释完整实际输出见 done 轮。编排方据 gh 核实：Release https://github.com/KunoLu/640-skills/releases/tag/v2.1.0-rc.3，名称 v2.1.0-rc.3，prerelease、非 draft、非 Latest（Latest 仍 v2.0.2，编排方据 releases/latest 核实），2026-10-29 21:20:20 (UTC+8) 发布；编排方整理：English／简体中文双语正文依据合入后的 CHANGELOG。上述 CI／CLEAN 不覆盖本 done 记录提交；本轮自检见 done 轮，非运行时验收，R2.2 状态不变。 |

以上保留三条既有事件，并在 done 提交中补记 checking → done 转换；完成依据见 done 事件。
