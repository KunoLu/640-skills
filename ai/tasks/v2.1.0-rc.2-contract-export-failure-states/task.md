---
schema_version: 1
id: v2.1.0-rc.2-contract-export-failure-states
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict、CONTRACT-ONLY；主会话唯一 writer／验证 controller；四文件范围；独立 reviewer 只读；保留 680fb0f，不 amend／rebase／push／PR。
status: done
branch: contract/v2.1.0-rc.2-export-failure-states
created_at: '2026-10-22T13:17:21+08:00'
updated_at: '2026-10-22T13:44:55+08:00'
completed_at: '2026-10-22T13:44:55+08:00'
---

# 导出 renderer 不可用与作业失败状态：独立契约

## 范围与验收

授权：用户于 **2026-10-22 约 13:14 Asia/Shanghai** 决定，由 Lord 转达；Reviewy 于同时间补充 R1（runtime 对齐归属）与 R2（status/error 关联约束）。工作根 `/workspace/640-skills-contract-export-failure`，分支见 frontmatter；基线 `origin/main` 为 `ce80ca20f9d85f77ad3ca6282ff3f21939fd2572`。保留已有 docs-only backfill 提交 `680fb0f34789af4133aa996d9cc457550e79f426`。

仅允许修改 OpenAPI、`sbtd-runtime/tests/test_golden_contracts.py`、本 task 和 `ai/tasks/v2.1.0-rc.2-plan/plan.md` 的 R2.1b 小节最小跟进说明；不改任务表。禁止 runtime、其他测试、PRD、ADR、dashboard 或其他 worktree 写入；不暂存 `.omp-r12b-addendum.txt`、`ai/tasks/codex-verify/` 或 reports。

验收：createExport 精确响应集合增加 503；封闭 detail 错误体；getExport 200 保留 Envelope 并绑定作业 schema；五个状态与两个稳定错误码；failed 必须非 null，其余状态必须 null；保留 warnings；基线 YAML 红灯、当前绿灯、真实 schema 消费者 smoke、指定验证与双独立 review。runtime 一致性失败必须如实记录，不改 runtime 或放宽契约。

未完整调用 grill-with-docs：需求、PRD 与用户指定的 OpenApiDraftTests／Draft202012Validator seam 已明确，无领域歧义。沿用 #153 task 的中文正文／英文 Gherkin 关键词和限定文件先例；Cross-repo context: contract-only；Mock Strategy: none。

### 契约验收场景

```gherkin
Scenario: 图像与 PDF renderer 不可用时在接受前拒绝
  Given 有效 jpeg 或 pdf 请求所需的可选 renderer 依赖不可用
  When 客户端按 createExport 契约处理同步拒绝
  Then HTTP 状态为 503 且 body 仅含 detail EXPORT_RENDERER_UNAVAILABLE
  And 没有作业、export_id 或半成品文件
  And html 与 csv 不适用此错误
  And jpeg 与 pdf 的不可用语义和 capabilities 报告的 unavailable 及原因一致

Scenario: 失败作业使用稳定错误码
  Given 导出作业处于 failed 状态
  When 客户端按 getExport 200 契约校验响应
  Then data.error 为 EXPORT_RENDER_TIMEOUT 或 EXPORT_RENDER_FAILED
  And null、自由文本 export failed、缺少 status 或 error 均被拒绝
  And 未来错误码只追加，客户端把未知码当通用失败

Scenario: 非失败状态没有错误码
  Given 导出作业处于 queued、generating、ready 或 cancelled 状态
  When 客户端按 getExport 200 契约校验响应
  Then data.error 必须为 null 而不能为错误码
  And Envelope 必填字段与字符串 warnings 保持兼容
  And 其他可选作业字段和扩展字段不因本次契约被拒绝
```

上述副作用与能力一致性为 R2.1b runtime 验收边界；本次只证明契约描述与 schema 实例，不冒充 HTTP renderer 实现。

## 源码证据与决定

- 首先已读 `git show ce80ca2`（#153）、`git show c7a87e4`（#152）与前一 JPEG/PDF task；复用专用 response、const detail、Draft202012Validator、subTests 和精确 status→$ref 映射。
- PRD `docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md` §9.6 第 843 行：数据库／renderer 不可用 → 503，区分只读查询、HTML／CSV 与图像／PDF 能力。请求有效，问题是服务端依赖不可用，不是 4xx 请求缺陷，且不同于 422 图像尺寸限制。
- PRD 第 725 行定义 GET /api/v1/capabilities 的采集／导出／来源能力及版本；第 1169 行要求缺依赖时菜单标注不可用及原因。OpenAPI 当前 getCapabilities 200 引用通用 Json／Envelope，data 无专用 schema；本次不新增 capabilities schema，仅用 unavailable 描述保持语义一致。
- `export_store.py:157–192` 的 `_public_view` 总是返回 status/error；另有 export_id、format、snapshot_id、时间、mime_type、byte_count/byte_size、sha256、版本、panel_ids、dataset_manifest、范围、timezone、warnings 等。只收紧 status/error，其他属性保持开放，不强制这些字段。
- `export_store.py:465–532`：generating、failed、cancelled 分支及失败清理；`488–493` 的收尾分支和 `_fail:513–524` 当前写自由文本 `export failed`，包括 HTML／CSV。R1 是已知 contract-leads-runtime mismatch，不以测试全绿掩盖。
- `export_store.py:85,92` 初始 queued／error=None；`544–551,598–605` 发布 ready／error=None；与 generating／failed／cancelled 合并为精确五状态。既有 `test_export_store.py:278` 明确断言自由文本 `export failed`；该范围外测试保持不变，不以它通过证明新失败码已落地。

## 决策

| 项目 | 决定与理由 |
|---|---|
| 同步 HTTP | createExport 新增 503 → ExportRendererUnavailable；仅 jpeg/pdf 所需 renderer 不可用（Playwright、chromium shell、optional extra 等）；html/csv 永不返回此错误 |
| 同步 body | 封闭 object，required [detail]，string const EXPORT_RENDERER_UNAVAILABLE；接受前返回，无 job、export_id 或 partial file |
| 查询响应 | getExport 200 → ExportStatus，allOf 复用 Envelope，data → ExportJob；不改变 get/download/delete 原有错误集合 |
| 作业状态 | status enum 精确 queued、generating、ready、failed、cancelled；status/error 必填；其余字段开放且非必填 |
| R2 关联 | JSON Schema 2020-12 if/then/else：failed 时 error 为非 null 字符串码，其他状态为 null；自由文本不合法 |
| 错误演进 | 当前码 EXPORT_RENDER_TIMEOUT、EXPORT_RENDER_FAILED；未来条目（如磁盘容量第 4 行）只追加码，客户端对未知码按通用失败处理；当前 producer schema 仍拒绝未声明码 |
| warnings | Meta.warnings 不变；data.warnings 复用相同字符串数组语义，不改 #153 的 EXPORT_SCALE_DOWNGRADED:1x |
| R1 runtime 归属 | R2.1b 接失败路径时将现有 HTML/CSV 失败映射 EXPORT_RENDER_FAILED、超时映射 EXPORT_RENDER_TIMEOUT，并在 202 前返回 503 EXPORT_RENDERER_UNAVAILABLE；本次不实现 |

## CONTRACT-CHANGE

变更：新增 createExport 503 专用错误；将 getExport 通用 Json 收紧为 Envelope<ExportJob>，固定状态和错误码关联。兼容性：503 为 additive；getExport 为 tightening，现有自由文本失败不符合新契约。消费者：R2.1b runtime 与 dashboard；客户端须容忍未来未知错误码，视为通用失败。无持久数据迁移／回放；回滚需先协调消费者，再撤回本次契约提交，保留 680fb0f。

### Runtime alignment (R2.1b) — PR body

本 PR 仅修改契约与 golden tests，不修改 runtime。
当前 HTML/CSV 的失败仍写自由文本 `export failed`，不符合新错误码 schema。
R2.1b 接入失败路径时，须映射普通失败为 `EXPORT_RENDER_FAILED`。
超时须映射为 `EXPORT_RENDER_TIMEOUT`。
JPEG/PDF renderer 依赖不可用须在 202 前返回 503 `EXPORT_RENDERER_UNAVAILABLE`。
该拒绝不得创建 job、export_id 或半成品文件，HTML/CSV 不适用此 503。
capabilities 须对相应格式报告 unavailable 及原因；本 PR 不新增其 schema。
这是已知 contract-leads-runtime mismatch，不代表 runtime 或发布已就绪。

## Book Gate Plan

| Gate | 触发事实 | 阶段 | 状态 |
|---|---|---|---|
| book-ddia-data-design | wire schema 与异步失败边界 | before-dev | confirmed |
| book-ddd-distilled-modeling | 无完整 grill、无领域歧义 | before-dev | not-required |
| book-legacy-change-safety | 不改 runtime 行为；已有直接 validator seam | before-dev | not-required |
| book-refactoring-pass | 已读路由；声明式 schema／测试，无生产代码修改 | before-dev | not-required；no refactor needed |
| book-release-readiness | 无 runtime／部署变更 | finish | not-required；不得声称发布就绪 |

DDIA Data Design Review — confirmed。OpenAPI 是 wire contract 事实源，ExportStore 拥有既有作业状态；接受前拒绝与接受后失败明确分离。无一致性、幂等、排序、重试、去重、存储、迁移或回放改变。已知实现漂移交由 R2.1b 修复，稳定错误码为消费端诊断信号。以 schema 实例、精确响应集合、基线红灯、独立 smoke 与现有全套测试验证。Ponytail：复用 Envelope／validator，最小 if/then/else，无依赖、helper 或公共错误抽象。

## 状态持久化限制

根／分支／HEAD／origin/main 已核对，初始工作树干净；四条写入路径逐级无 symlink，新 task 不存在。`git check-ignore -v` 命中 `.gitignore:4:/ai/tasks/**/reports`，新 task 无 tracked 文件。沿用 #153 已记载的 TaskStore catalog `task has no YAML frontmatter block` 限制，不重复确认；helper 的 index／active 写入也超四文件授权。本文件为用户指定共享记录，不声称 TaskStore helper、active 或自动恢复成功；不写身份／ignore。

## 验证证据

全部命令在授权 worktree 根运行，环境前缀 `env PYTHONDONTWRITEBYTECODE=1 RUFF_NO_CACHE=true PYTHONPATH=sbtd-runtime:sbtd-runtime/tests`。Python 3.13.5／Linux，本地开发工作树；Evidence Source: developer-local；Source Revision: dirty；Evidence Publication: local-only；Environment Alignment: unverified。原始 command（含完整 `-c` 脚本）、stdout/stderr、exit code、时间、HEAD、分支、环境及契约／测试 SHA-256 存入 ignored `reports/<stem>.json`，同 stem 中文汇总为 `.md`。原生运行避免报告缓存，rtk: skipped-for-report；不把提交前 HEAD 680fb0f 当新 PR-head 证明。

| 命令（共同环境前缀见上） | 退出码与计数 | 报告 stem |
|---|---|---|
| `python -B -c <base YAML red script>` | exit 1（预期）；4 tests，2 failures、2 errors：GET 200 映射、POST 503 映射不符；新 response／job schema 缺失 | `base-yaml-red` |
| `python -B -c <contract consumer smoke script>` | exit 0；JSON round-trip 消费 503 与六组有效 status/error；拒绝 503 中 export_id 和 failed 自由文本；撤去本次新增契约后 YAML 结构与 origin/main 完全相等 | `contract-smoke` |
| `python -B -m unittest sbtd-runtime/tests/test_golden_contracts.py -v` | exit 0；57 passed，0.321s | `golden-green` |
| `python -B -m unittest discover -s sbtd-runtime/tests` | exit 0；306 tests，304 passed、2 skipped，48.340s | `runtime-full` |
| `python -B -m unittest discover -s sbtd-runtime/tests -p 'test_serve.py'` | exit 0；14 passed，6.712s | `serve` |
| `python -B -m unittest discover -s sbtd-runtime/tests -p 'test_export*.py'` | exit 0；35 tests，34 passed、1 skipped，29.929s | `exports` |
| `python -B -m unittest discover -s sbtd-runtime/tests -p 'test_panel_manifest.py'` | exit 0；21 passed，0.005s | `panel-manifest` |
| `ruff format --check sbtd-runtime/tests/test_golden_contracts.py` | exit 0；1 file already formatted | `format` |
| `ruff check sbtd-runtime/tests/test_golden_contracts.py` | exit 1；仅已知 I001，19–30 行 import block 未改；不修范围外问题 | `lint` |
| `VALIDATION_SHA=680fb0f34789af4133aa996d9cc457550e79f426 python -B tests/run_ci.py --platform linux --output ai/tasks/v2.1.0-rc.2-contract-export-failure-states/reports/native-ci` | exit 0；2378 tests，2317 passed／61 skipped cases；unittest 为 63 skip events（含 subTest），0 failures；1248.153s | `native-ci/linux-1`；补充 `linux-ci-review` |

基线红灯通过 `git show origin/main:sbtd-runtime/contracts/openapi.yaml` 载入 TemporaryDirectory，进程内替换模块 OPENAPI；没有 stash 或改写工作树。四项包括两个精确映射测试及两个新测试。临时目录自动清理，smoke 无落盘脚手架。

全部 runtime／HTTP 子集通过，**没有出现 live runtime response 对新 schema 校验失败**。这不消除已知 R1 mismatch：现有自由文本断言仍通过；schema 消费者明确拒绝该值。全套两个 skip 是 Windows junction evidence only，exports 子集含其中一个；套件相互重叠，不累计通过数。

BDD: traceable；三个中文／英文关键词场景映射两个新增测试与两个精确 map；API Contract: verified；E2E Mode: contract-backed；Mock Strategy: none（新增用例）；Cross-repo context: contract-only。无 UI／浏览器／移动端改动，不执行相应工具；没有 JPEG/PDF 新渲染、超时或 capabilities HTTP 对齐实测。独立 OpenAPI meta-schema linter 未配置，本次使用项目既有 PyYAML／Draft202012Validator，不冒称完整 OAS lint。

Code Readability／Ponytail：复用 unittest、subTest 和既有 validator；一个条件约束，无 helper／依赖／runtime 改动；状态×错误矩阵覆盖两个码、null、自由文本、未来未知码、非法类型；保留 Envelope 必填／类型与开放 metadata／字符串 warnings。无必要重构或新增 durable lesson，不写身份／lesson。

根 Linux suite 原生报告 successful=true，failures 与 required_native_failures 均为空。用户提示的 `test_sbtd_probe_links.MaterializeAuthorizationTests.test_link_text_change_is_refused` 和 `test_replaced_link_with_identical_text_is_refused` 本轮均 passed；未修改这些测试，不声称修复历史失败。原生 case 计数为 2317 passed／61 skipped，unittest 为 63 skip events（含 subTest），不同粒度不简单相减。根 suite 只运行一次，未分片、未重跑确认已知问题。

Final Test Report／Run Summary MD: generated；Final Full Rerun: passed（根 Linux suite）；Targeted Rerun: not-needed（首轮修改后已绿）；**lint 仍有既有 I001，不声称所有检查全绿**。原生 `native-ci/linux-1.{json,md}` 保留，另有九节中文 `linux-ci-review.md` 与同 stem 来源／摘要回执。报告经 git check-ignore 确认 ignored，无暂存；没有报告发布或新 PR-head CI 证明。

验证前后契约／测试 SHA-256 一致：

| 文件 | 已验证 SHA-256 |
|---|---|
| `sbtd-runtime/contracts/openapi.yaml` | `2307ddae5b759ae03623614923a747e5efc918f77364752f9166d418f6dc14c2` |
| `sbtd-runtime/tests/test_golden_contracts.py` | `1f9db6ac7990c5e14ae58c8a80e1a108701df8998ab21c9d59a91201489bf6ae` |

本 task frontmatter 已按 sbtd-task 的 task-data.schema.json 用 Draft202012Validator／FormatChecker 校验，并核对真实日历与 +08:00；这不是 TaskStore helper 生命周期证明。

### 独立审查

- FailureContractReview：correct，无 findings；核对四文件范围、503 的 PRD 依据／接受前边界、Envelope 合成、条件约束、开放 metadata、warnings 引用、capabilities 未扩张及 R1 runtime 漂移登记。确认实际状态赋值均在五状态 enum 内。
- FailureCoverageReview：correct，confidence 0.85，无 findings；逐项核对 5×6 status/error 矩阵、两个精确响应集合、必填字段、Envelope 正负例、开放 metadata 与两层 warnings，读取 raw 红绿／smoke／format／lint 证据。指出新增组件不存在导致基线 KeyError 是本次 add-only 契约的有效红灯；描述层副作用不等于运行时证明。
- 两位均为独立只读 reviewer，由 omp 自动分配模型，未覆盖 model；不运行 tests／lint／build／formatter、不写文件。主会话唯一 writer／验证 controller。无有效 finding，无修正回路；最终证据填充与提交由主会话负责。smoke 的实际保证为撤去新契约后 YAML **解析结构相等**，不是字节相等。

## 提交与恢复边界

契约实现提交 `89ab5d4712c84c950e3762e1508870917bfb5e2b`：`contract(export): declare renderer-unavailable 503 and export failure states`，仅 openapi.yaml＋test_golden_contracts.py，164 insertions／2 deletions；parent 为保留的 `680fb0f34789af4133aa996d9cc457550e79f426`。两个已提交 Git blob 的 SHA-256 与上表已验证内容一致；这是内容身份复核，不冒称提交后的新 CI 运行。

本 task 与 plan 的单条 R2.1b 跟进说明保存为第二个提交 `docs(task): record export failure-states contract evidence`，自身 SHA 由最终回执记录，避免自引用。仅显式 git add 四条授权路径，不暂存报告或禁止路径；无 amend／rebase／push／PR，不触碰其他 worktree。done 仅指本地契约交付，不代表 runtime 对齐、全部检查全绿或发布就绪。撤回契约前须协调 R2.1b／dashboard 消费者；无数据迁移或恢复步骤。TaskStore／active／自动恢复限制不变，operator 负责模型计数及后续发布操作。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-22T13:17:21+08:00 | planned | in-progress | 用户 strict 授权与 R1/R2 明确；根／分支／先例／PRD／状态源码已核对 | ce80ca2 基线；保留 680fb0f；四文件边界；DDIA confirmed |
| 2026-10-22T13:23:01+08:00 | in-progress | checking | 契约、测试与 R2.1b 最小说明已完成；红绿／消费者 smoke／runtime 指定检查已执行；进入根 suite 与双只读审查 | golden 57；runtime 306/2 skips；serve 14；exports 35/1 skip；panel 21；format passed；既有 I001 |
| 2026-10-22T13:44:55+08:00 | checking | done | 全部指定契约与 runtime／根验证及双独立只读 review 完成；提交契约并保持基线 backfill；仅保留已知 I001 与显式 runtime 漂移 | 89ab5d4712c84c950e3762e1508870917bfb5e2b；golden 57；runtime 306/2 skips；root 2378 tests、2317 passed／61 skipped cases、63 skip events；两 reviewer correct／无 findings |

## 模型使用

operator 回填
