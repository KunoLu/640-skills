---
schema_version: 1
id: v2.1.0-rc.2-r2.1c-export-menu
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：strict、方案 B；主会话唯一 writer 与验证 controller，不启动子代理或 advisor；仅授权前端、构建产物及两份任务文档，提交由编排方执行。
status: done
branch: feat/v2.1.0-rc.2-r2.1c-export-menu
created_at: '2026-10-26T11:14:16+08:00'
updated_at: '2026-10-26T12:10:12+08:00'
completed_at: '2026-10-26T12:10:12+08:00'
---

# R2.1c：四格式导出菜单接线

## 决定与范围

- 用户 2026-10-26 11:10 群内确认（开始 r2.1c，选方案 B：导出传页面 7 字段 presentation_state、跟随页面主题含浅色；openapi.yaml:699 的 409 措辞与 422／503／507 的 {detail} 错误体按现状兼容、另开 PR），Lord 记录。
- 基线 `fbaff7be6b3da703cd83f4438a6a66c24e95673e`；入口工作树干净，分支匹配；授权路径及父目录无 symlink／逃逸，`git check-ignore --no-index` exit 1、无命中。
- 认领 `docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md`：U-07（:60）、§13.2（:1113–1126）、AC-36（:1475）、AC-52（:1496）；部分涉及 AC-43（:1487，界面部分）、AC-44（:1488）。补 R2.1a 漏掉的前端接线，不是新需求：PRD:1406 已列菜单接入，`ai/tasks/v2.1.0-rc.2-r2.1a-html-csv-export/task.md:219` 明记前端 dashboard 未改。
- 不在范围：AC-45–51、AC-53–59（后端已交付），AC-33、AC-62（D9）；不改后端、OpenAPI、PRD、依赖、其他测试或 task/index。
- 未完整调用 grill-with-docs：方案与验收明确，直接复核既有契约，无新增领域歧义。
- 按参考 task 手写共享交付记录，不调用会联写 index／active 的 TaskStore；不声明 TaskStore 自动恢复。临时报告仅在 `/tmp`，不写 active、handoff、ignore 或身份文件。

## Book Gate Plan

| Gate | 触发／阶段 | 结论与证据 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill／领域歧义，需求前 | not-needed；未完整 grill，复用现有 export/snapshot 定义 |
| book-ddia-data-design | 异步作业、重试，设计前 | confirmed；后端拥有 pin，点击固定七字段与快照；每点击新键、重试同键，409 等待、401 停止，无 schema 变更 |
| book-legacy-change-safety | 既有占位接线前 | characterized；基线 App:297–308 恒禁用，:476–478 旧文案；保留配对、刷新、筛选，现有 22 测试及新增逻辑测试保护 |
| book-refactoring-pass | 生产代码编辑前 | proceed / normal；不做无关重构，复用 request、ReportDocument 与样式 token |
| book-release-readiness | 验证后 | blocked（发布门禁）；限定本地验证通过，新提交 CI、独立复核与 D9 未执行；本 task 保持 checking，不声明发布就绪 |
| gherkin-bdd / TDD | 行为编辑前 | 以下中文场景、英文关键词；受写入范围限制保存在本 task，自动化追踪到 exportJob.test.ts；不新增 spec 文件 |
| 独立 review | 跨客户端 API 接线，check | 本会话不执行；不启动子代理或 advisor，主会话自核不冒充独立审查，保持 checking 交外部复核 |

LSP references 实际返回 `No language server found for this action`；以 api.ts 的 ApiError 调用点及后端契约源码检索补充影响分析，不声明 LSP 覆盖。

## 行为场景

```gherkin
Feature: 从当前报告导出单个文件
  Scenario: 固定当前快照和展示状态
    Given 页面显示已完成快照且主题为浅色
    When 选择一种导出格式后页面刷新或改变筛选
    Then 在途导出保持原快照与原七字段展示状态
    And 每次新选择使用新幂等键而网络重试使用原键
  Scenario: 作业进度和有界等待
    Given 导出经历 queued 和 generating
    When 作业 ready
    Then 下载带会话认证的文件并释放临时链接
    And 未就绪的 409 继续等待而达到轮询上限显示超时
  Scenario: 取消与旧响应隔离
    Given 导出正在生成
    When 取消导出或页面卸载
    Then 旧轮询停止且其结果不能覆盖后续导出
    And 显式取消向后端发送 DELETE
  Scenario: 错误与降级可见
    Given 服务返回认证过期、请求错误、快照失效或资源限制
    When 导出处理该响应
    Then 显示对应提示、原 detail 或错误码而不吞掉 request_id
    And JPEG 的 EXPORT_SCALE_DOWNGRADED:1x 警告可见
  Scenario: 能力和工具栏顺序
    Given renderer 不可用
    When 查看导出菜单
    Then JPEG 和 PDF 保留置灰并显示原因而 HTML 和 CSV 不受影响
    And 时间筛选仍位于四格式按钮左侧
```

## 契约与验证边界

- `sbtd-runtime/contracts/openapi.yaml:699–700` 引用 Conflict 的下载 409 措辞，以及 422／503／507 的 `{detail}` 非 envelope 错误体，按现状兼容，不改契约，另开 PR。
- DELETE 也需要 Idempotency-Key：OpenAPI:562、serve.py:666–670；未就绪 409 实际在 serve.py:688–689，草稿 :686–687 是 410。
- 真机四格式点击（含浅色）放 D9，本 PR 未做。不把 node 假网络／假时钟测试或浏览器契约 smoke 当成用户 Mac 验证。

## 实现与测试追踪

以下源码路径均相对 `sbtd-runtime/dashboard/src/`；测试均在 `exportJob.test.ts`，以实际新行号为准。

| 行为要求 | 实现位置 | 对应测试名／证据 |
|---|---|---|
| queued／generating／ready 与一次文件下载，保留 JPEG 警告 | `exportJob.ts:4–12,119–140`；`App.tsx:403–412` | :28 `queued and generating reach ready with one file and retained warnings` |
| failed／cancelled 终态不下载 | `exportJob.ts:132–135` | :38 `failed and cancelled are terminal and never download` |
| 最多 40 次轮询，1s 起 ×1.5，封顶 5s，上限停止并提示超时；测试可注入间隔及次数 | `exportJob.ts:99–149` | :50 `polling stops at its cap with exponential backoff capped at five seconds` |
| 显式取消 DELETE，停止信号，迟到 ready 不下载 | `exportJob.ts:88–96,120–129`；`api.ts:415–417`；`App.tsx:249–264` | :63 `cancelling aborts polling, sends DELETE, and ignores a late ready response` |
| 退避中取消、卸载或新点击后旧结果不写新状态 | `exportJob.ts:53–61,95–96,110–124`；`App.tsx:108–113,222–229` | :84 `stopping during backoff prevents another request or stale UI write`；:130 `a newer click cannot receive an older creation or download response` |
| 每点击新 UUID；仅传输失败重试一次、复用原 key／payload，轮询不换键；AC-52 固定点击时 snapshot_id，刷新不串 | `exportJob.ts:74–85,106–120`；`App.tsx:205–212,220–227` | :95 `new clicks use new keys; transport retry and polls retain the clicked snapshot and seven fields`；浏览器 smoke 在生成中换主题并刷新 |
| presentation_state 恰好七字段，嵌套值复制，跟随 light／dark 及已展开详情 | `exportJob.ts:76–81`；`App.tsx:205–212` | 同 :95；断言七字段、原 light 不受页面改 dark 与数组／字典变动影响 |
| 401 停止轮询并提示重启 serve 重新配对；400／404／410／422／503／507 保留 detail | `exportJob.ts:27–40,147–149`；`api.ts:139–160` | :151 `401 stops immediately; other fatal HTTP errors do not retry or download` |
| 轮询／下载 409 当未就绪继续等待，不作为失败 | `exportJob.ts:137–144` | :165 `409 from polling or file download waits and eventually downloads once` |
| HTTP 映射、max_edge_px、request_id、EXPORT_RENDER_TIMEOUT／EXPORT_RENDER_FAILED／未知码 | `api.ts:98–109,139–160`；`exportJob.ts:27–40` | :187 `error mappings preserve detail, failure code, and request id`；:218 API 用例 |
| 文件名 UTF-8 filename*、quoted／bare filename、错误编码回退与不安全路径回退 | `exportJob.ts:43–51`；`api.ts:419–425` | :205 `Content-Disposition supports UTF-8, quoted, bare, malformed, and unsafe names` |
| capabilities／POST／GET／DELETE／file，Bearer、POST／DELETE CSRF 与幂等键，204 不解析 JSON；二进制 blob | `api.ts:112–165,395–425` | :218 `API authentication, 204 cancellation, binary download and both error body shapes`；真实 Python serve／native smoke |
| jpeg／pdf 依能力置灰且原因可见、不隐藏；html／csv 独立；生成中整体禁用 | `App.tsx:98–106,214–224,385–413` | 浏览器契约 smoke：缺 renderer 两按钮置灰、原因可见，HTML／CSV 可用；生成时 CSV disabled |
| ready 使用 object URL 下载，使用后与卸载释放，不用裸 API 链接 | `App.tsx:108–113,230–244` | 浏览器观察两次 download，URL created=2／revoked=2；迟到下载由 :130 覆盖 |
| 固定格式与时间范围可见，时间筛选在导出左侧，删除旧占位文案，少量状态样式 | `App.tsx:227,355–413,579–581`；`app.css:82–90` | 浏览器控件顺序、390px 无横向溢出；源码复核，不将文案钉成永久测试 |

Code Readability Review：请求认证只复用原入口，job 拥有固定输入及 AbortController，React 仅负责交互与 object URL；不改 ReportDocument 定义或后端 pin。Ponytail Review：无新增依赖、通用重试框架、全局缓存或无关重构，未发现需要删除的额外层。主会话自核，不冒充独立 review。

## 验证记录

证据绑定基线完整 SHA `fbaff7be6b3da703cd83f4438a6a66c24e95673e`、分支 `feat/v2.1.0-rc.2-r2.1c-export-menu` 与本工作树未提交修改。Linux；Node v22.20.0、npm 10.9.3、Python 3.13.5。Evidence Source=developer-local；Source Revision=dirty；Environment Alignment=unverified（CI Python 为 3.12.10）；Evidence Publication=local-only；rtk=skipped-for-report，直接保留原生命令结果。

下表 `npm` 命令在 `sbtd-runtime/dashboard`，Python 命令在仓库根。每条 native/raw JSON 及同 stem 中文汇总保存在 `/tmp/r21c-<名称>.json`／`.md`；临时运行脚本收尾删除，结果保留，不保证长期存续。

| 命令 | exit | 实际结果 | 证据名称 |
|---|---|---|---|
| `node --test src/exportJob.test.ts`（初始 tracer） | 1 | 模块尚未创建，ERR_MODULE_NOT_FOUND；不是已观察到的功能断言失败 | 会话原始工具输出；失败记录保留于本节 |
| `node --test src/exportJob.test.ts`（实现 tracer 后／扩展覆盖后） | 0／0 | 1 pass／12 pass，假网络与注入 sleep，无真实网络或真实等待 | 会话原始工具输出 |
| `npm test` | 0 | 34 tests、34 pass、0 fail、0 skipped（原 22＋新增 12） | npm-test |
| `npm run build`（第一次） | 0 | tsc --noEmit＋vite build；41 modules | build-1 |
| `PYTHONDONTWRITEBYTECODE=1 python3 -B sbtd-runtime/dashboard/check_artifacts.py` | 0 | OK：3 files，267266 B ≤524288 B；最大 JS 259101 B ≤409600 B，CSS 7701 B、index.html 464 B | artifacts、rebuild |
| `npm run build`（第二次） | 0 | 再次成功；三份文件逐一 SHA-256 一致，构建前后 git status --porcelain 字节一致；不是工作树干净 | build-2、rebuild |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_serve.py'` | 0 | Ran 14 tests in 7.195s，OK；含 :436–456 的 GET /、asset 及路径越界／Host 测试 | serve |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_export*.py'` | 0 | Ran 38 tests in 36.379s，OK (skipped=1)；Windows junction evidence only；renderer reconciliation 使用既有 worker stub | exports |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_panel_manifest.py'` | 0 | Ran 21 tests in 0.012s，OK | manifest |
| `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_sbtd_task_document tests.test_sbtd_task_legacy_events_notice tests.test_sbtd_task_recovery tests.test_sbtd_task_routing tests.test_sbtd_task_schema tests.test_sbtd_task_state tests.test_sbtd_task_status_sync tests.test_sbtd_task_sync_git` | 0 | Ran 135 tests in 52.423s，OK；旧格式通知为既有夹具输出 | task-tests |
| `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/r21c-native-smoke.py`（临时脚本，收尾删除） | 0 | 直接调用既有 runtime_e2e.exercise，不安装浏览器、不走读取环境元数据的 main；GET / 200、真实 HTML 14100 B／CSV 51855 B，JPEG／PDF unavailable（Playwright is not installed）；内嵌 3 tests OK，SIGINT exit 0、lock 与端口释放 | native-smoke、native-details |
| Playwright MCP `browser_run_code_unsafe` | 不适用 | built static 页面＋契约模拟 API；两次下载、一次 DELETE、light／dark 参数、快照固定、不同点击不同 key、Bearer／CSRF、401／422、能力原因、URL 2／2、窄屏与顺序断言通过，pageerror 0 | browser-smoke |
| 下方 task 解析命令（转态前） | 0 | `in-progress False 2 None`；stderr 空 | task-parse-in-progress |
| 下方 task 解析命令（转 checking 后） | 0 | `checking False 3 None`；stderr 空 | task-parse-final |
| `git diff --check`；`git status --short --untracked-files=all`；追加范围／文字检查 | 0 | 空白检查无输出，改动仅授权路径；plan 原有行保持不变；task 无禁用措辞、三事件时间递增 | final-checks |

解析命令（实际执行；前后相同）：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" ai/tasks/v2.1.0-rc.2-r2.1c-export-menu/task.md
```

编辑期曾有一次补丁行号定位错误，工具报告语法错误；立即重读并修正，没有把错误留到构建阶段，也没有伪称首个 tracer 是功能性 red。最终测试与两次构建均成功；未重复运行编排方已给出的基线验证。永久测试用 node:test 与 node:assert/strict，导入 `.ts`；不新增其他测试文件或依赖。

### CI、D9 与发布边界

- **浅色导出不在 CI 覆盖范围——`test_browser_renderer.py` 不在任何 CI job，runtime-e2e 只验深色；只靠 D9 在用户 Mac 上的页面点击验证。** 读代码推断，未实际运行 CI：`.github/workflows/validation.yml:121–134` 只选 panel_manifest／serve／export*；:140–156 是 node 测试与重建预算；:287、:314 调用 runtime_e2e。`tests/run_ci.py:321` 的其余分片只发现根 tests；`runtime_e2e.py:339,362–364` 用默认展示、POST 不传 presentation_state，`export_render.py:145–154` 默认 dark。本轮 light 参数传递的 node／浏览器模拟证明不等于真实浅色文件验收。
- 真机四格式点击（含浅色）放 D9，本 PR 未做；本机没有 Python Playwright，未安装或升级依赖。真实 JPEG／PDF 渲染及字体、macOS／Windows 平台验证均未跑。Windows junction skip 由 `test_export_store.py:875–876` 定义。真实服务 smoke 的三项 reconciliation 使用既有 renderer stub，不写成四格式实测。
- BDD=traceable（本 task 中文场景＋英文关键词、node 测试与浏览器 smoke；未新增范围外 spec）；Cross-repo context=contract-only；API Contract=verified；Mock Strategy=contract-backed。Playwright MCP=explored，非 CLI regression；未新增持久 Web E2E 资产，不引入测试框架。Mobile／SEO 不适用。
- Final Test Report／Run Summary MD=generated（本地 raw 与同 stem 中文）；Targeted Rerun=passed（tracer）；Final Full Rerun=passed，仅本任务限定本地命令。不运行全仓套件或独立 lint／formatter：package.json 未定义此类脚本，TypeScript 已经 tsc 检查；未跑 npm audit 或 CI 13 job，本轮不声称 CI 通过。
- Release Readiness Review=blocked（发布门禁）：新提交 CI、独立复核、D9 证据仍缺；本会话不提交、不推送、不发布，提交与推送由编排方执行。回退为前端源码与相配 static 产物一起恢复，不涉及持久 schema 或数据迁移；服务端已受理作业继续由既有保留／清理策略管理，卸载只停止客户端观察。

### 基线行号复核

- PRD:60、1113–1126、1136、1181、1406、1475、1487–1503 与两份输入一致；R2.1a task:219、R2.0b task:58、plan 任务表:15–31 及 F:99–103 一致。实施后 plan 新增行在 :32、新节 :106–111；历史行内容不变。
- 草稿 `serve.py:686–687` 所指 409 有偏差：该范围实际是 410；409 在 :688–689。其余导出认证 :370–412、七字段 :432–442、capabilities :494–508、文件 :671–681、422／503／507 与警告原锚点一致。
- 基线 api.ts 实际 request 声明 :105，extraHeaders :109；草稿 :104 与 :108 分别是空行／body 参数。Bearer／CSRF :114–115、JSON :154 正确；配对完整保存凭据到 :94，草稿 :62–83 仅为其前半段。
- `sbtd_task_state.py` 真正写 index 在 :523，:524 为记录 written；生命周期 :659–666、`sbtd_task_sync.py:350–380` checking→done 检查范围一致。OpenAPI 409 引用在 :699–700，而冲突措辞正文在 :812–813；此为既有契约差异，不在本轮改动。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | 产出 | 会话文件 |
|---|---|---|---|---|---|
| 1 | ping（2026-10-26 11:13:10 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-26T03-13-10-144Z_01a17632-9a00-74b7-8b8a-6920407e6cd0.jsonl` |
| 2 | 会话 1（实现） | openai-codex/gpt-6-astra（high） | 38／115 | 实现、测试、构建与本 task 初稿 | `2026-10-26T03-13-24-840Z_01a17632-d368-75ae-a454-9b47366809bd.jsonl` |
| 3 | 会话 1 内部辅助 model_usage | typesafe/jev-latest（thinking 不可考） | 24 次调用（purpose find，不计入主会话 assistant 消息／toolCall） | 源码检索 | `2026-10-26T03-13-24-840Z_01a17632-d368-75ae-a454-9b47366809bd.jsonl` |
| 4 | ping2（2026-10-26 11:35:04 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-26T03-35-04-722Z_01a17646-a912-7754-9371-a969297cb5be.jsonl` |
| 5 | 会话 2（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告 | plan／task 措辞小修 | `2026-10-26T03-35-37-323Z_01a17647-286b-720d-9f6a-9f93c4ec9f42.jsonl` |

每个 omp 会话一行；未使用子代理、advisor；会话 1 的计数与内部辅助 model_usage 由编排方按 jsonl 统计（编排方整理）；会话 2 的内部辅助 model_usage（如有）由群内交付报告另列。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-26T11:14:16+08:00 | planned | in-progress | 编排方整理；写入者：主会话，开始 strict 前端导出接线 | 基线 fbaff7be6b3da703cd83f4438a6a66c24e95673e；分支、路径、ignore 核对；方案 B 与契约已复核 |
| 2026-10-26T11:21:52+08:00 | in-progress | in-progress | 编排方整理；写入者：主会话，实现与首次构建完成，进入完整验证 | npm test 34 pass（原 22＋新增 12）；npm run build exit 0；后续验证产物预算、重建一致、Python、浏览器与 task |
| 2026-10-26T11:28:33+08:00 | in-progress | checking | 编排方整理；写入者：主会话，全部限定本地验证完成，进入检查 | npm 34 pass；两次 build 字节一致；static 总量 267266 B／最大 259101 B；serve 14、export 38（1 skip）、manifest 21、task 135 均 OK；真实服务与契约浏览器 smoke 分开记录；task 解析 checking False 3 None，CI／独立复核／D9 未执行 |
| 2026-10-26T12:10:12+08:00 | checking | done | 编排方整理；写入者：主会话，Reviewy CLEAN 后写入 done；PR #186 | CLEAN 对应 SHA fd577df979093669acfdfba53bcbcc797ff75e00，CI run 40265329468 |
