---
schema_version: 1
id: v2.1.0-rc.2-contract-export-jpeg-pdf
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict、contract-only；仅指定 worktree 与分支；主会话唯一 writer／验证 controller；子代理仅只读；显式 git add 指定路径；Round 1–2 与 operator 提交保留，Round 3 新增提交，不改写历史、不 push、不开 PR、不评论、不 merge。
status: done
branch: contract/v2.1.0-rc.2-export-jpeg-pdf
created_at: '2026-10-22T11:27:23+08:00'
updated_at: '2026-10-22T12:14:16+08:00'
completed_at: '2026-10-22T12:14:16+08:00'
---

# JPEG／PDF 与图像超限错误：独立导出契约

## 范围与验收

授权依据：640-skills room 用户于 **2026-10-22 11:23 Asia/Shanghai** 明确「授权开契约PR」；Lord 于 **11:24 +08:00** dispatch，**11:34 +08:00** 补充细节。本轮仅本地提交，operator 负责后续 push／PR／merge。基线 `origin/main` 为 `8931c35ef1aa4a58d3675b6f8d1a8fead309ed90`，工作根 `/workspace/640-skills-contract-jpeg-pdf`，分支见 frontmatter。记录沿用 `ai/tasks/v2.1.0-rc.2-contract-export-error-responses/task.md` 的范围／证据／Gate／验证／提交／状态事件结构。

仅三个交付文件：`sbtd-runtime/contracts/openapi.yaml`、`sbtd-runtime/tests/test_golden_contracts.py`、本 task。扩展 CreateExportRequest.format 为 `[html, csv, jpeg, pdf]`，仅 createExport 新增 422 → ExportImageSizeLimit；错误 body 必须给出稳定 detail 和实际限制。保留全部 HTML／CSV 定义、其他 operation、CSV 列与版本。

禁止修改 runtime（serve.py／export_store.py／export_render.py）、Dashboard、`test_exports_http.py`、PRD／ADR／plan.md；不纳入磁盘容量错误。不得触碰其他三个 worktree `/workspace/640-skills`、`/workspace/640-skills-r2.1b`、`/workspace/sbtd-plugins-row-c`。不得暂存 `.omp-r12b-addendum.txt` 或 `ai/tasks/codex-verify/`。

验收：四格式请求、完整呈现状态、精确 enum、非法格式与必填／类型约束、精确 createExport 响应集合、错误 schema 正负例；基线 YAML 红灯／修改后绿灯；全部指定验证及只读独立 review。若契约一致性测试因 runtime 仍拒绝 jpeg/pdf 而失败，停止，不改 runtime、不提交契约，记录具体失败。

未完整调用 grill-with-docs：授权、范围、PRD 和验收明确，无需重复需求访谈。测试 seam 由用户指定为 OpenApiDraftTests／Draft202012Validator，不模拟 HTTP 成功。

### 契约验收场景

沿用请求体契约先例，在本次限定三文件任务记录保存中文正文、英文关键词；Cross-repo context: contract-only；Mock Strategy: none。OpenAPI 是持久 wire contract；不把以下契约场景冒充 runtime 实现。

```gherkin
Scenario: 固定快照可选择四种导出格式
  Given 客户端持有格式正确的 snapshot_id
  When 按 createExport 契约校验 html、csv、jpeg 或 pdf 请求
  Then 省略或完整提供 presentation_state 均被接受
  And jpg、JPEG、PDF、png 等未声明格式仍被拒绝

Scenario: JPEG 超限预检返回明确限制
  Given JPEG 在完整内容、宽度至少为标准报告宽度的 1x 输出下仍超限
  When 按 createExport 的预检失败契约校验响应
  Then HTTP 状态为 422 且 detail 为 EXPORT_IMAGE_SIZE_LIMIT
  And max_edge_px 与 max_total_pixels 必须给出正整数限制
  And 错误 detail、缺字段、错误类型或未知字段被拒绝

Scenario: JPEG 降采样通过接受响应告知用户
  Given JPEG 从 2x 降为 1x 后内容完整、宽度至少为标准报告宽度且不再超限
  When 按 createExport 的 HTTP 202 契约校验接受响应
  Then meta.warnings 包含固定字符串 EXPORT_SCALE_DOWNGRADED:1x
  And warnings 项仍为字符串且 data 仍仅含 export_id
```

## 源码证据与决定

- 已读 `git show c7a87e4`（#152）、两份指定 task 及当前 OpenApiDraftTests；沿用精确 status→`$ref` 映射与 subTest 风格。
- PRD `docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md` §9.6（841 行）：请求体或导出规模超出已验证上限 → 413／422，预检失败、明确限制、不截断。
- 同 PRD §13.5（1146–1148 行）：单边 32,000 px／总像素 80 MP 是建议值、待目标平台实测及用户决定冻结；2x 超限时，在内容完整且宽度仍 ≥ 标准报告宽度的条件下降为 1x，生成前提示用户；仅 1x 仍超限才返回 EXPORT_IMAGE_SIZE_LIMIT。AC-48（1480 行）要求不截断、不拆文件、不产生半成品成功文件、不伪造成功。
- `serve.py:425–426` 与 `export_store.py:35,255–256` 目前只接受 html/csv；`test_exports_http.py:127` 明确保留 pdf → 400。此 PR 为前置契约，不声明当前 runtime 已支持新格式。
- `serve.py` 使用 `_json({"detail": str(error)}, status)`；既有 BadRequest／NotFound／Conflict／Gone 为 description-only。新增专用响应，不引入公共错误 envelope 或 code 字段。

## 决策

| 项目 | 决定与理由 |
|---|---|
| 名称 | detail const `EXPORT_IMAGE_SIZE_LIMIT`，直接采用 PRD §13.5／AC-48；语义为渲染图像尺寸或总像素数超出限制 |
| HTTP | POST /api/v1/exports 返回 HTTP 422，Content-Type 为 application/json；JSON 请求有效且很小，超限对象是预期渲染输出，符合 §9.6 的 413／422 选择 |
| body | 沿用 runtime 的 `{"detail": ...}` 错误体惯例，不加 code 或成功 envelope；封闭 object，必填 detail（string，const EXPORT_IMAGE_SIZE_LIMIT）、max_edge_px（integer，minimum 1，实际单边像素上限）、max_total_pixels（integer，minimum 1，实际总像素上限）；限制数值不以 const／enum／maximum／default 冻结 |
| operation | 仅 POST /api/v1/exports 的 createExport：生成前、202 接受前预检失败。其余 get/download/delete 无此同步错误路径，不毯式添加 |
| 异步边界 | R2.1b 必须保证此预检先于 202；若只能在接受后检测，需独立明确 getExport failed 状态／错误信息契约与无半成品成功文件保证；本次不扩张查询 schema，不把后置失败伪称 HTTP 422 |
| JPEG／PDF | 四格式 enum 是请求选择契约；§13.5 图像限制错误针对 JPEG，PDF 仍按 §13.6 单文件多页语义，不套用 JPEG 单图上限 |
| 兼容与回滚 | html/csv 及幂等／认证／CSRF／202 envelope 不变；仅新增可选格式和失败响应。撤回实现提交前需协调依赖此契约的 R2.1b；无数据迁移或回放 |
| Round 3 降采样通知 | 固定格式 `EXPORT_SCALE_DOWNGRADED:1x`，由 createExport 的 HTTP 202 ExportAccepted 在 `meta.warnings` 携带；Meta.warnings 原本是 string-typed，因此不引入结构化项或 CreateExportAccepted 新字段；运行时生成前发出通知由 R2.1b 实现 |

上限数值 冻结 待定（待目标平台实测及用户决定；PRD 建议值 32,000 px／80 MP 仅为建议）。

Round 2 仅在 `ExportImageSizeLimit.description` 补充触发语义：2x 超限时，在内容保持完整且宽度仍 ≥ 标准报告宽度的条件下降为 1x，并在生成前通知用户；只有 1x 仍超限才返回 `EXPORT_IMAGE_SIZE_LIMIT`。不得截断、拆成多个文件、产生部分／半成品输出或伪造成功。降采样逻辑及通知本身属于 **R2.1b runtime，不在本 PR 实现范围**；无需新 schema 字段。

## Book Gate Plan

| Gate | 触发事实 | 阶段 | 状态 |
|---|---|---|---|
| book-ddia-data-design | 新请求枚举与失败 wire schema | before-dev | passed / confirmed |
| book-ddd-distilled-modeling | 无完整 grill、无领域歧义 | before-dev | not-required |
| book-legacy-change-safety | 无 runtime 行为修改，既有直接 validator seam | before-dev | not-required |
| book-refactoring-pass | 已读路由；仅声明式契约／测试，无生产代码编辑或结构摩擦 | before-dev | not-required；no refactor needed |
| book-release-readiness | 无 runtime／部署变更 | finish | not-required；不声称实现或发布就绪 |

DDIA Data Design Review — confirmed。OpenAPI 是 wire contract 事实源；Export 负责固定快照导出，runtime job 状态不变。新失败只在接受前声明；接受后失败需 R2.1b 单独处理。无共享持久数据写入／一致性／重试／排序／去重／迁移／backfill／replay 变化。detail 与两项实际限制是诊断信号。以实例校验、精确响应集合、红灯证明和现有全套 runtime 测试约束兼容性。Ponytail：内联一个 response schema，复用现有 validator，不加依赖、helper 或公共错误抽象。

Round 2 DDIA Data Design Review — confirmed：PRD／OpenAPI 仍为需求／wire contract 事实源；仅补充接受前失败条件，不改变字段、异步 job 状态、一致性、幂等、持久数据、迁移或回放。沿用 Round 1 Gate 适用性；无生产代码重构或发布动作。轻量 golden guard 约束两项限制字段不得出现 const／enum／maximum，保留已有实例验证，不钉死描述措辞。

Round 3 DDIA Data Design Review — confirmed：Lord 2026-10-22 12:08 +08:00 refinement 明确通知格式与载体，无领域歧义，未完整调用 grill-with-docs。OpenAPI 是 wire contract 事实源；只更新 ExportAccepted／Meta.warnings／ExportImageSizeLimit 三处描述，保持 warnings.items 精确为 `{type: string}`、CreateExportAccepted.properties 名称集合精确为 `{export_id}`。无持久数据、一致性、幂等、排序、重试、迁移、回放或异步状态变化；通知实际发出仍属 R2.1b。复用 OpenApiDraftTests／Draft202012Validator，先对 Round 2 YAML 红灯，再做 schema 消费者 smoke、指定验证及独立只读审查；其余 Book Gate 适用性不变，无需重构或发布 Gate。

## 状态持久化限制

初始根／分支／基线匹配，git status 为空；路径逐级检查无 symlink。`git check-ignore` 证实 `.sbtd/active-task.json` 与本 task reports 受保护；`git ls-files -- .sbtd ai/tasks/v2.1.0-rc.2-contract-export-jpeg-pdf` 为空。namei 对不存在的新任务目录返回 1 是缺失确认，非写入失败。

沿用 #148/#152 已记录的 TaskStore catalog `task has no YAML frontmatter block` 限制，不重跑确认；TaskStore.create 的 index／active 写入也超出三文件范围。本文件是用户明确要求的共享交付记录，不声称 TaskStore helper 生命周期、active 或自动恢复成功；不写身份／ignore／其他任务。原始验证报告与同 stem 中文汇总仅放本任务 ignored reports，不暂存。

## 验证证据

以下至 Round 2 小节之前均为 **Round 1 历史证据**，保留原始结果，不代表本轮重跑。

所有命令在授权 worktree 根执行，使用原生工具；`PYTHONDONTWRITEBYTECODE=1 RUFF_NO_CACHE=true`，runtime 命令 `PYTHONPATH=sbtd-runtime`。rtk: skipped-for-report。环境 Linux／Python 3.13.5（CI 配置为 3.12.10，此处不是 CI 环境等价证明）。原始 command／stdout／stderr／exit code／时间／基线／平台存入本 task ignored `reports/<stem>.json`，同 stem 中文 `.md`；不暂存报告。证据为 developer-local／dirty／local-only，不冒称 PR head／部署证明。

| 命令 | 退出码与结果 | 报告 stem |
|---|---|---|
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python -B -c <base YAML red script>` | exit 1（预期）：4 tests，6 failures、1 error；jpeg/pdf 枚举拒绝、精确 enum／422 map 失败、ExportImageSizeLimit 不存在 | `base-yaml-red` |
| `python -B -c <contract smoke script>` | exit 0：YAML parses；四格式 JSON round-trip 均接受；422 body 接受非建议默认值 24000／60000000；撤掉本次三处语义变化后整个 YAML 结构与基线完全相等 | `contract-smoke` |
| `PYTHONPATH=sbtd-runtime python -B -m unittest sbtd-runtime/tests/test_golden_contracts.py -v` | 最终 exit 0：54 passed，0.305s；初轮也 54 passed | `golden-final`；保留 `golden` |
| `PYTHONPATH=sbtd-runtime python -B -m unittest discover -s sbtd-runtime/tests` | exit 0：303 tests，301 passed、2 skipped，48.695s | `runtime-full` |
| `PYTHONPATH=sbtd-runtime python -B -m unittest discover -s sbtd-runtime/tests -p 'test_panel_manifest.py'` | exit 0：21 passed，0.004s | `panel-manifest` |
| `PYTHONPATH=sbtd-runtime python -B -m unittest discover -s sbtd-runtime/tests -p 'test_serve.py'` | exit 0：14 passed，6.828s | `serve` |
| `PYTHONPATH=sbtd-runtime python -B -m unittest discover -s sbtd-runtime/tests -p 'test_export*.py'` | exit 0：35 tests，34 passed、1 skipped，30.720s | `exports` |
| `ruff format --check sbtd-runtime/tests/test_golden_contracts.py` | 初轮 exit 1：新增非法格式 tuple 与长方法签名换行；仅修这两处，最终 exit 0：1 file already formatted | `format`、`format-final` |
| `ruff check sbtd-runtime/tests/test_golden_contracts.py` | exit 1：仅既有 I001（19–30 行 import block）；与 #148/#152 记录一致，此段未改，不修无关问题、不宣称 lint 全绿 | `lint` |
| `env PYTHONDONTWRITEBYTECODE=1 RUFF_NO_CACHE=true VALIDATION_SHA=8931c35ef1aa4a58d3675b6f8d1a8fead309ed90 python -B tests/run_ci.py --platform linux --output ai/tasks/v2.1.0-rc.2-contract-export-jpeg-pdf/reports/native-ci` | exit 1：2375 tests，2 failures、63 skip events，1249.547s；契约／验收 wrapper 70 cases 均 passed；两个失败详见下文 | `native-ci/linux-1.{json,md}`；`linux-ci-review.{json,md}` |

红灯脚本通过 `git show origin/main:sbtd-runtime/contracts/openapi.yaml` 取得基线 YAML，写入 TemporaryDirectory，再只替换测试模块 OPENAPI 路径运行四个修改测试；没有 stash 或改写工作树。完整可复现 `-c` 源码在对应 raw JSON 的 command 数组。Smoke 脚本同样只在进程内执行，无遗留脚手架。

全 runtime 套件包含 test_r1_acceptance、test_serve 与 test_exports_http；**没有出现 runtime 拒绝 jpeg/pdf 导致契约一致性失败**。既有 pdf → 400 测试保持原样并通过，框架容许 rc.2 draft contract 领先实现。两项 skip 均是 Windows junction evidence only：`test_snapshot_junction_is_refused_without_cleaning_target`、`test_export_junction_is_refused_without_cleaning_target`；exports 子集只含后者。套件与子集重叠，不累计通过数量。

根 Linux suite 的两个失败均位于未修改的 `tests/test_sbtd_probe_links.py`：

1. `MaterializeAuthorizationTests.test_link_text_change_is_refused`（867 行）：实际 `link-mismatch`，预期 `identity-mismatch`。
2. `MaterializeAuthorizationTests.test_replaced_link_with_identical_text_is_refused`（878 行）：预期 ContractError 未抛出。

源码 857–880 行测试 symlink 物化授权／身份，不涉及 OpenAPI、runtime 导出格式或本次改动；不扩张范围修复、不重跑掩盖、不宣称已知根因或 flaky。用户指定「runtime 拒绝 jpeg/pdf 引发契约一致性失败则不提交」未触发；全部契约／验收 wrapper 通过。完整失败原始报告已保留，**根 CI 不全绿**。原生 cases 为 2312 passed／61 skipped／2 failed，而 unittest 汇总为 63 skip events（含 subTest，不同粒度），不简单相减制造通过数。

根 runner 必填 `--output`，因此加本任务 ignored 报告路径；未分片。其 `source_sha`／VALIDATION_SHA 是真实基线，不代表包含修改的 PR head；报告明确 developer-local／dirty／local-only。最终契约／测试文件哈希在根 suite 前后相同。Final Test Report / Run Summary MD: generated；Targeted Rerun: passed（格式修正后的 golden）；runtime planned scope: passed（保留平台 skips）；**Final Full Rerun: failed（根 Linux 两项范围外失败）**。

### 验证边界

- BDD: traceable；中文正文／英文关键词，task 两个契约场景映射至四格式接受／非法请求／精确 map／新 body 测试。API Contract: verified（schema、实例、结构比较）；Cross-repo context: contract-only；Mock Strategy: none。
- 实际 smoke 是声明式契约消费者校验，不是 JPEG/PDF HTTP 成功或渲染证明。runtime／Dashboard／浏览器／移动端不改；不执行新渲染、TS build、UI E2E 或部署。
- `.github/workflows/validation.yml` 的三个相关 Python 步骤均已执行；根 Linux runner 另行执行并记录。未安装依赖、未执行 compileall 产生仓库缓存、未更换 TOML 依赖版本。独立完整 OpenAPI meta-schema lint 未配置；使用项目 PyYAML／Draft202012Validator，不冒充 OAS linter。
- 主会话 Code Readability／Ponytail Review：复用 unittest、subTest、既有 validator；一个 response schema，无新 helper／依赖；正负例针对格式、字段必填／类型／限制可变等消费者边界，不锁定描述措辞。独立审查结果见下。
- 报告与通过是两回事；已保留红灯、格式首轮与既有 lint 失败。没有新的 durable runtime lesson，不写身份／lesson。TaskStore 自动恢复限制不变。

### 独立审查与可读性

- ContractCorrectness：`overall_correctness: correct`，confidence 0.92，无 blocking finding；核对 PRD、完整契约 diff、当前 runtime 错误 body／格式检查、scope 与前置／异步边界。报告指出正文验证仍在填充，该事实属于审查时快照，不冒称最终记录已审核。
- ContractCoverage：`overall_correctness: correct`，confidence 0.98，无覆盖／正确性 finding；确认 root wrapper 导入全部 TestCase，新方法进入 tests/run_ci.py，runtime pdf → 400 测试不变。
- 唯一非阻塞 simplicity 建议：移除只有 createExport 的 subTest，net -1 line。保留：用户明确要求 #152 精确映射与 subTests 风格；reviewer 已确认此决定合理，无需修改。
- 两位均只读，未运行测试／lint／formatter，无共享 writer；主会话完成 Code Readability Review，无必要重构、helper 或依赖。review 覆盖的是最终格式修正后的契约／测试；未产生代码修正回路。

### Round 2 验证证据与独立审查

本轮以 `0cd5da2c61fa026bb77bb04fcfd5b377f03740b3` 为提交前 HEAD，基线与分支不变。原始命令／stdout／stderr／退出码／时间／已验证文件 SHA-256 保存在本任务 ignored `reports/round2-validation.json`，同 stem 中文汇总为 `reports/round2-validation.md`；不暂存。Evidence Source: developer-local；Source Revision: dirty；Evidence Publication: local-only；Environment Alignment: unverified（Linux／Python 3.13.5，非 CI Python 3.12.10 等价证明）；rtk: skipped-for-report。以下均为本轮新执行，环境 `PYTHONDONTWRITEBYTECODE=1 RUFF_NO_CACHE=true PYTHONPATH=sbtd-runtime:sbtd-runtime/tests`。

| 命令 | 本轮实际结果 |
|---|---|
| `python -B -c <smoke，完整源码见 raw JSON>` | exit 0；Draft202012Validator 消费 JSON round-trip 错误体，接受 16000／40000000、32000／80000000、64000／160000000 三组实际上限；两个限制字段分别加入 const／enum／maximum 的六个进程内变异均被 golden 测试拒绝，无 errors；无遗留脚本 |
| `python -B -m unittest sbtd-runtime/tests/test_golden_contracts.py -v` | exit 0；54 passed，0.305s |
| `python -B -m unittest discover -s sbtd-runtime/tests` | exit 0；303 tests，301 passed、2 skipped，47.804s |
| `python -B -m unittest discover -s sbtd-runtime/tests -p 'test_serve.py'` | exit 0；14 passed，6.702s |
| `python -B -m unittest discover -s sbtd-runtime/tests -p 'test_export*.py'` | exit 0；35 tests，34 passed、1 skipped，29.225s |
| `python -B -m unittest discover -s sbtd-runtime/tests -p 'test_panel_manifest.py'` | exit 0；21 passed，0.004s |
| `ruff format --check sbtd-runtime/tests/test_golden_contracts.py` | exit 0；1 file already formatted |
| `ruff check sbtd-runtime/tests/test_golden_contracts.py` | exit 1；仅既有 I001，19–30 行 import block 未修改；不修范围外问题 |

平台 skips 与 Round 1 一致（Windows junction）；套件重叠，不累加通过数。本轮每条命令运行一次；未重跑 Round 1 根 Linux CI，也未声称其两项范围外失败已修复。Final Test Report／Run Summary MD: generated；Targeted Rerun: not-needed；Final Full Rerun: passed（本轮指定 unittest 范围）；**lint 不全绿，整仓 CI 不作通过声明**。

BDD: traceable，仅契约场景；沿用 task 中文正文／英文关键词，不新增 .feature。API Contract: verified；Cross-repo context: contract-only；Mock Strategy: none（新增 smoke）；E2E Mode: contract-backed。未验证 JPEG/PDF 渲染、降采样或用户通知：这些是 R2.1b runtime 范围，不把描述或 schema 校验当运行时实现。目标平台实测／数值冻结／UI E2E／部署未执行。

- AddendumSemantics：correct，confidence 0.95，无 finding；独立核对 PRD 行号、五项语义、授权与 task 模型、仅 response description 的 YAML 改动、Round 1 兼容性。审查时 task 尚未最终填充验证结果，其状态观察是当时快照。
- AddendumCoverage：correct，confidence 0.98，无 finding；两字段 const／enum／maximum guard、detail const、既有实例正负例和可读性均符合要求，无描述措辞断言。
- 两位 reviewer 均只读、未运行测试／lint／formatter。主会话 Code Readability Review：复用现有 subTest 的五行 guard，无 helper／依赖／runtime 改动；无必要重构，无修正回路。

### Round 3 验证证据与独立审查

本轮提交前 HEAD 为 `36c4c1915999f478540a202d47bacd90c1f2de23`，Round 2 YAML 来自 `3c1e698`；原始基线与分支不变。全部命令／完整进程内脚本／stdout／stderr／退出码／时间／文件 SHA-256 保存在本任务 ignored `reports/round3-validation.json`，同 stem 中文汇总为 `reports/round3-validation.md`，不暂存。Evidence Source: developer-local；Source Revision: dirty；Evidence Publication: local-only；Environment Alignment: unverified（Linux／Python 3.13.5，非 CI 环境等价证明）；rtk: skipped-for-report。以下均为本轮实际执行，环境 `PYTHONDONTWRITEBYTECODE=1 RUFF_NO_CACHE=true PYTHONPATH=sbtd-runtime:sbtd-runtime/tests`。

| 命令 | 本轮实际结果 |
|---|---|
| `python -B -c <Round 2 YAML red script>` | exit 1（预期）；1 test、2 subTest failures：ExportAccepted.description 与 Meta.warnings.description 均缺固定字符串；无 errors。先确认工作树 YAML 与 `git show 3c1e698:sbtd-runtime/contracts/openapi.yaml` 相等，再用 TemporaryDirectory 替换测试模块 OPENAPI 路径，不改写工作树 |
| `python -B -m unittest test_golden_contracts.OpenApiDraftTests.test_create_export_202_carries_scale_downgrade_warning -v` | 描述补齐后 exit 0；1 passed，0.040s；精确固定字符串、string items、仅 export_id 及 Draft202012 202 envelope 全部通过 |
| `python -B -c <contract smoke script>` | exit 0；JSON round-trip 的 downgrade 202 envelope 与普通 warning 字符串均接受；结构化 warning 与 data 新字段均拒绝；撤去恰好三处描述改动后整个 YAML 结构与 Round 2 完全相等 |
| `python -B -m unittest sbtd-runtime/tests/test_golden_contracts.py -v` | exit 0；55 passed，0.313s |
| `python -B -m unittest discover -s sbtd-runtime/tests` | exit 0；304 tests，302 passed、2 skipped，48.065s |
| `python -B -m unittest discover -s sbtd-runtime/tests -p 'test_serve.py'` | exit 0；14 passed，6.776s |
| `python -B -m unittest discover -s sbtd-runtime/tests -p 'test_export*.py'` | exit 0；35 tests，34 passed、1 skipped，30.099s |
| `python -B -m unittest discover -s sbtd-runtime/tests -p 'test_panel_manifest.py'` | exit 0；21 passed，0.005s |
| `ruff format --check sbtd-runtime/tests/test_golden_contracts.py` | 首轮 exit 1，仅新测试 for tuple 换行；仅修改该行后最终 exit 0，1 file already formatted；上述完整 golden／runtime／子集均在修正后运行 |
| `ruff check sbtd-runtime/tests/test_golden_contracts.py` | exit 1；仅既有 I001，19–30 行 import block 未改，不修范围外问题 |

平台 skips 计数与历史 Windows junction 限定一致；全量与子集重叠，不累加通过数。没有出现 runtime 拒绝 jpeg/pdf 导致契约一致性失败。未重跑 Round 1 根 Linux CI，不声称其两项范围外失败已修复。Final Test Report／Run Summary MD: generated；Targeted Rerun: passed；Final Full Rerun: passed（本轮指定 unittest 范围）；**lint 不全绿，整仓 CI 不作通过声明**。原始红灯、格式首轮与 lint 失败均保留，临时目录已清理，无遗留 smoke 脚本。

BDD: traceable，新增 task 场景与新测试同名，中文正文／英文关键词，沿用 no-.feature 先例。API Contract: verified；Cross-repo context: contract-only；Mock Strategy: none（新增 smoke）；E2E Mode: contract-backed。本轮固定的是协议字符串，不锁定其余描述措辞。JPEG/PDF 新渲染、2x→1x 实际降采样、生成前发出通知、UI E2E、目标平台上限冻结和部署均未验证，属 R2.1b／目标平台范围。

- WarningContractReview：correct，confidence 0.92，无 finding；独立核对三处描述、202 引用、warnings.items 精确 string、CreateExportAccepted 仅 export_id、422 触发语义与三文件范围；确认旧 operator 模型表未改。实际模型为 reviewer 自报 kimi-code/k3，jsonl 解析值仍待 operator 回填。
- WarningCoverageReview：correct，confidence 0.90；确认两处 token 断言、精确 shape guard、Draft202012 引用解析／样例、discoverability、BDD 与红灯证据一致。唯一 P3 建议为再钉住 ExportImageSizeLimit 描述中的 token；不采纳：用户明确 golden 描述断言仅要求 ExportAccepted 与 Meta.warnings，422 本轮作为文档要求由独立 review 核对，保留最小测试范围。reviewer 自报实际模型 kimi-code/k3。
- 两位均只读，未执行测试／lint／formatter。主会话 Code Readability／Ponytail Review：复用现有 unittest／subTest／validator，无 helper、依赖、runtime 代码或无关重构；无正确性修正回路。无新 durable runtime lesson，不写身份／lesson。TaskStore／active／自动恢复限制不变。


## Round 1 提交与恢复边界


本地契约交付完成；done 不表示 runtime JPEG/PDF 已实现、整仓 CI 全绿、部署或发布就绪。实现提交 `d75ca3b57594d0010d3e0e29850a1942b35347a4`，parent 为指定基线 `8931c35ef1aa4a58d3675b6f8d1a8fead309ed90`。只执行 `git add sbtd-runtime/contracts/openapi.yaml sbtd-runtime/tests/test_golden_contracts.py`，实现提交仅两文件、116 insertions／16 deletions。

提交后读取两个 Git blob，与验证前保存的 SHA-256 完全一致；不重复运行未变化的套件、不把已有失败包装成通过：

| 文件 | 已验证／已提交 SHA-256 |
|---|---|
| sbtd-runtime/contracts/openapi.yaml | 2dd450480e79c8b3f186f52e6c4aeb1debcec31f11d829c1d42899e21eb1f0a9 |
| sbtd-runtime/tests/test_golden_contracts.py | 28323423e5815508d59056aa8ef2dc1a076ebe4d7c3cfc08d1332cebe65d61ee |

本记录以第二个 docs 提交保存，只显式添加 `ai/tasks/v2.1.0-rc.2-contract-export-jpeg-pdf/task.md`；自身提交 SHA 由最终命令输出／本地 receipt 记录，避免自引用。最终交付三文件；reports ignored、不暂存禁止路径；不 push、不开 PR、不评论、不 merge。回滚为协调撤回实现提交（下游 R2.1b 尚不得假设已合并），无持久数据恢复步骤。TaskStore／active／自动恢复限制不变；operator 负责模型计数与后续发布操作。

### Round 2 提交与恢复边界

保留 `d75ca3b` 与 `0cd5da2`，新增一个提交 `contract(export): document EXPORT_IMAGE_SIZE_LIMIT downgrade semantics`，不 amend／rebase。只显式添加 `sbtd-runtime/contracts/openapi.yaml`、`sbtd-runtime/tests/test_golden_contracts.py`、本 task；提交 SHA 以最终 `git log --oneline origin/main..HEAD` 输出为准，避免自身 SHA 自引用。未 push／PR／merge／comment；禁止路径不暂存，其他 worktree 不触碰。

本轮验证快照 SHA-256：openapi.yaml 为 `d06209d33396d584422c469cb2d2201e8e28cfe34aa155092d03218e08ba2b43`；test_golden_contracts.py 为 `56bef9031868078513300afc3ebc2a0d205310a8cd18c51d1744a8a39341e3ec`。该证据是提交前 local-only，不冒称新提交的 CI／发布证据。回滚需协调 R2.1b 消费者后撤回本轮补充提交；无数据迁移。TaskStore helper／active／自动恢复限制继续保留；本次仅维护获授权的 task.md。

### Round 3 提交与恢复边界

保留 `d75ca3b`、`0cd5da2`、`3c1e698` 与 operator 提交 `36c4c19` 及原模型表，新增提交 `contract(export): document EXPORT_SCALE_DOWNGRADED:1x warning`，不 amend／rebase。仅显式 git add 两个契约／测试文件及本 task；提交 SHA 由最终 `git log --oneline origin/main..HEAD` 给出，避免自身 SHA 自引用。不 push／PR／merge／comment，不暂存禁止路径，不触碰其他 worktree。

本轮验证快照 SHA-256：openapi.yaml 为 `8bd2d3d1617d9d1ca9d3af117a114eec05123fafc12856c410c2163d448e4df7`；test_golden_contracts.py 为 `d3e2aa3b7d0102bbecdea490abe8fd949ac6d587f2e21692503c5a3b76492d7c`。证据为提交前 local-only；done 仅表示本轮契约交付，不表示 runtime 通知已实现、整仓 CI 全绿或发布就绪。撤回本轮提交前需协调 R2.1b 消费者；无持久数据迁移或恢复。模型使用计数按用户要求留给 operator 回填。


## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-22T11:27:23+08:00 | planned | in-progress | 用户明确 strict；授权根／分支／基线与三文件范围已确认，完成 PRD／先例与 schema 设计核对 | origin/main 8931c35ef1aa4a58d3675b6f8d1a8fead309ed90；PRD §9.6／§13.5／AC-48；#152 |
| 2026-10-22T11:32:27+08:00 | in-progress | checking | 契约与测试已完成；红灯、smoke、指定 runtime 子集／全量和格式检查已执行，进入独立 review／根 CI 验证 | golden 54；runtime 303/2 skips；panel 21；serve 14；exports 35/1 skip；既有 I001 保留 |
| 2026-10-22T11:55:23+08:00 | checking | done | 指定契约／runtime 验证及双独立 review 完成；实现提交内容与验证哈希一致；明确保留根 CI 两项范围外失败与既有 I001，不声称整仓全绿 | d75ca3b57594d0010d3e0e29850a1942b35347a4；parent 为指定基线；golden 54／runtime 303；根 CI 2375 tests、2 failures、63 skip events；契约 wrapper 70 passed |
| 2026-10-22T11:58:58+08:00 | done | planned | 用户 Round 2 明确要求同任务补充；保留 Round 1 提交与完成证据，不改写历史 | 初始 git log 为 0cd5da2、d75ca3b；git status 为空；分支匹配 |
| 2026-10-22T11:58:58+08:00 | planned | in-progress | 已核对 Lord 11:34 细节、PRD 1146／1148／1480 与指定 task 模型；继续 strict 三文件范围 | 授权 11:23／dispatch 11:24；路径无 symlink；reports ignored 且未跟踪；TaskStore 既有限制不重跑 |
| 2026-10-22T12:00:13+08:00 | in-progress | checking | 响应描述与两项限制字段 golden guard 完成；两位只读 reviewer 分别核对语义与覆盖，主会话执行本轮指定验证 | YAML 仅 description 修改；HTTP／body／建议值／R2.1b 边界已记入 task；Python 3.13.5、Ruff 0.17.1 |
| 2026-10-22T12:02:52+08:00 | checking | done | Round 2 五项补充完成；指定 unittest、format、契约消费者 smoke／六个冻结变异与双独立只读 review 完成；明确保留既有 lint 与 Round 1 根 CI 失败，不声明 runtime 实现 | reports/round2-validation.json 与同 stem 中文 md；golden 54、runtime 303/2 skips、serve 14、exports 35/1 skip、panel 21；I001；AddendumSemantics／AddendumCoverage correct |
| 2026-10-22T12:09:26+08:00 | done | planned | 用户 Round 3 明确要求继续同任务，保留 Round 1–2 与 operator 模型表提交 | 初始 git status 为空；git log 为 36c4c19、3c1e698、0cd5da2、d75ca3b；分支匹配 |
| 2026-10-22T12:09:26+08:00 | planned | in-progress | strict 三文件范围；固定 warning 字符串与 202 载体已明确，路径无 symlink，沿用 TaskStore 已知限制，不重复尝试 helper 或写 active | Lord 12:08 refinement；warnings.items 为 string；CreateExportAccepted 仅 export_id；BDD／DDIA 记录见本轮段落 |
| 2026-10-22T12:11:17+08:00 | in-progress | checking | Round 2 YAML 红灯为两个描述缺少固定字符串；补充三处描述后定点测试通过，schema 消费者 smoke 证明兼容边界，进入指定全量验证与双只读审查 | 新 test_create_export_202_carries_scale_downgrade_warning；warnings string／data export_id 不变；格式首轮仅换行并已修正；无 runtime 修改 |
| 2026-10-22T12:14:16+08:00 | checking | done | Round 3 固定 warning 契约、精确 shape 与样例校验、三处描述、BDD／决策／模型行完成；红绿、smoke、指定验证与双只读 review 完成；保留既有 lint 与根 CI 风险 | reports/round3-validation.json 与同 stem md；golden 55、runtime 304/2 skips、serve 14、exports 35/1 skip、panel 21；format passed；I001；WarningContractReview／WarningCoverageReview correct |

## 模型使用

operator 于 2026-10-22 12:10 +08:00 依据 session jsonl（`~/.omp/agent/sessions/--workspace-640-skills-contract-jpeg-pdf--/`）回填。主会话命令：`timeout 10800 omp -p "$(cat PROMPT)" --model openai-codex/gpt-6-astra:high --auto-approve --cwd /workspace/640-skills-contract-jpeg-pdf`，无 `--advisor`、无配置覆盖。subagent 均由主会话以 `agent: reviewer` 派出（`~/.omp/logs/omp.2026-10-22.*.log` 的 `subagent launch timing` 记录 `"agent":"reviewer"`），未显式指定 model；内置 reviewer agent 为 `model: "@slow"`，本机 slow 角色配置为 `kimi-code/k3:max`。各子代理 jsonl 的 `session_init.resolvedModel` 实际记录为 `kimi-code/k3:high`（high 的原因未能从日志确认，如实记录），`model_change` 只记 `kimi-code/k3`、不含 thinking level。并非 config `task` 角色的 grok-4.7；全部只读。（operator 2026-10-22 13:15 +08:00 更正）全部会话 `resolvedModelIsFallback: false`，无 403、无 fallback。

| 用途 | 会话 | 请求／配置模型 | 实际模型（jsonl） | resolvedModelIsFallback | assistant messages | 工具调用次数 |
|---|---|---|---|---|---|---|
| Round 1 主会话（唯一 writer） | 01a161a5-6bf1-75f4-b636-b712d58cf6df | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra | false | 39 | 74 |
| ContractCorrectness（只读 reviewer） | Round 1 subagent | agent `reviewer`（内置 `model: "@slow"`）→ slow 角色 kimi-code/k3:max | kimi-code/k3（session_init resolvedModel `kimi-code/k3:high`） | false | 19 | 27 |
| ContractCoverage（只读 reviewer） | Round 1 subagent | agent `reviewer`（内置 `model: "@slow"`）→ slow 角色 kimi-code/k3:max | kimi-code/k3（session_init resolvedModel `kimi-code/k3:high`） | false | 13 | 24 |
| Round 2 主会话（唯一 writer） | 01a161c2-b2fc-7549-ba1e-b94c3b9f49e2 | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra | false | 18 | 40 |
| AddendumSemantics（只读 reviewer） | Round 2 subagent | agent `reviewer`（内置 `model: "@slow"`）→ slow 角色 kimi-code/k3:max | kimi-code/k3（session_init resolvedModel `kimi-code/k3:high`） | false | 7 | 11 |
| AddendumCoverage（只读 reviewer） | Round 2 subagent | agent `reviewer`（内置 `model: "@slow"`）→ slow 角色 kimi-code/k3:max | kimi-code/k3（session_init resolvedModel `kimi-code/k3:high`） | false | 5 | 9 |
| Round 3 主会话（唯一 writer） | 01a161cc-3c9b-7399-a067-841d4e763e12 | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra | false | 23 | 48 |
| WarningContractReview（只读 reviewer） | Round 3 subagent | agent `reviewer`（内置 `model: "@slow"`）→ slow 角色 kimi-code/k3:max | kimi-code/k3（session_init resolvedModel `kimi-code/k3:high`） | false | 11 | 15 |
| WarningCoverageReview（只读 reviewer） | Round 3 subagent | agent `reviewer`（内置 `model: "@slow"`）→ slow 角色 kimi-code/k3:max | kimi-code/k3（session_init resolvedModel `kimi-code/k3:high`） | false | 12 | 12 |
| Session title generation（Round 1，omp log pid 37926） | 含子代理会话标题 | omp title-generator | cursor/composer-2.5 ×4；kimi-code/k3-256k ×1 | — | 5 requests | 0 |
| Job widget（Round 1，pid 37926，2026-10-22 11:35:06 +08:00） | 后台 job 进度组件 | omp job widget | 日志未记录模型（是否为 cursor/composer-2.5 无法从日志确认） | — | 1 条「Job widget spec rejected」 | 0 |
| Session title generation（Round 2，pid 112981） | 含子代理会话标题 | omp title-generator | cursor/composer-2.5 ×4 | — | 4 requests | 0 |
| Session title generation（Round 3，pid 104959） | 含子代理会话标题 | omp title-generator | cursor/composer-2.5 ×4；kimi-code/k3-256k ×1 | — | 5 requests | 0 |
