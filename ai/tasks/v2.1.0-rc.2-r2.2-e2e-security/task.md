---
schema_version: 1
id: v2.1.0-rc.2-r2.2-e2e-security
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict；主会话唯一 writer／验证 controller；仅授权 worktree 内三个本地 commit，显式路径暂存；不 push／PR／评论／merge／rebase／amend，不修改全局配置或其他 worktree。
status: in-progress
branch: feat/v2.1.0-rc.2-r2.2-pr1-disk-quota-507
created_at: '2026-10-23T12:40:31+08:00'
updated_at: '2026-10-23T13:10:53+08:00'
completed_at: null
---

# R2.2 PR-1：共享磁盘配额与 507

## 用户决定与任务身份

用户 2026-10-23 12:11 +08:00 群内说开始 R2.2，Lord 记录。当前仅 PR-1；plan 的 R2.2 任务表行保持 planned，直到 PR-4 收尾。授权根 `/workspace/640-skills-r22`，入口 HEAD／origin/main `cb12b606f1ec74d8bc87da12dd0d828628fa7724`，分支如 frontmatter，无 upstream；入口工作区干净。未完整调用 grill-with-docs：用户明确行为、顺序、契约与验收，无新领域决定。

## 范围与验收

- snapshots/ 与 exports/ 共享字节上限，默认 2000000000；环境变量 `SBTD_RUNTIME_DISK_QUOTA_BYTES` 严格按 ADR 0003 §5 解析，非法值拒绝启动，不回显原值。
- 按 ADR §4 验证目录、扁平 lstat 计量普通文件；坏／未知文件保留且计数。清扫过期且无引用数据及已确认残留 temp，再测量；80% 只记日志，U > L 才拒绝，U == L 放行，不预留未来产物大小、不淘汰未过期数据。
- SnapshotStore 库拒绝携带两项 byte counts，不新增 snapshot HTTP handler。createExport 顺序保持 access 401/403 → validation 400 → replay 原 202 → 新请求 503 → 404 → 410 → 507 → 422；拒绝无 job／ID／新文件。
- TDD seams 为用户指定的真实 loopback HTTP＋stores、snapshot library 与启动 CLI；先 red 后实现。完整 runtime suite、golden 61、changed Python ruff、diff、YAML、受保护契约零 diff。原生报告保留失败与同 stem 中文汇总，不暂存 reports。
- 不修改 contracts/openapi.yaml、golden JSON、schemas、PRD 或 ADR；若必须修改则 STOP 并记录 blocker。install-and-use 仅补配置与 507 的用户操作说明；不提前执行后续项 B/C。
- 严格串行后续：PR-2 安全（AC-56、ticket 日志、ADR 风险）；PR-3 macOS／Windows CI、用户 Mac 视觉／字体（AC-33／AC-62）及对账（AC-51／AC-45）；PR-4 §18 性能、默认配额容量校准与 R2.2 收尾。PR-1 完成不等于 R2.2 done。

## Book Gate Plan

| Gate | 客观触发／阶段 | 初始状态 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义／需求前 | not-needed；未完整 grill，数据所有权由 ADR 固定。 |
| book-ddia-data-design | 共享磁盘、异步导出、清扫／设计稳定前 | pending；核实共享锁、pin、temp 在途登记及恢复顺序后输出独立 Review。 |
| book-legacy-change-safety | 既有重放与清扫高回归风险／行为编辑前 | pending；先建立 HTTP 优先级、配额与保留边界 red。 |
| book-refactoring-pass | 既有生产代码编辑／before-dev | pending；在 legacy characterized 后判断最小共享协调，无无关重构。 |
| TDD／gherkin-bdd／ponytail | 新配额外部行为／before-dev | 已加载；复用现有 Markdown spec、unittest 与标准库，不引入 runner 或依赖。 |
| 独立 review／可读性 | 两 store 与 serve 公共准入／check | pending；仅只读审查，主会话集成与验证。 |
| project-validation | 用户指定本地命令／check | pending；真实 serve smoke 独立于 tests，报告实际环境，不冒充跨平台 CI。 |
| book-release-readiness | runtime 启动与运行行为／验证后 | pending；仅 PR-1 本地就绪，不代表部署或 rc.2 发布。 |

## 验证证据

首轮事实核实：`git log -1 --format='%H %cI'` 分别读取 e748a5eddfba38cd487af9dfc5271e601de7c76b 与 cb12b606f1ec74d8bc87da12dd0d828628fa7724，得到 2026-10-23T11:28:33+08:00／2026-10-23T12:01:59+08:00；mergedAt 由 Lord 提供，换算一致。`git show de97926:ai/tasks/v2.1.0-rc.2-plan/plan.md` 核实原后续项 B 的依据原句。PRD 第 845 行归因逐字核对，旧 task 历史段落与事件不重写。

### PR-1 最终验证（2026-10-23，developer-local）

实现已在本地 commit `62a10b452feb7dfd3b1ea59886775659679871b3` 完成。以下为本次原生执行结果；不是 CI、部署或 rc.2 发布验收。环境 Linux 6.12.94+／x64、Python 3.13.5；主会话唯一 writer／验证 controller。报告在本目录 ignored `reports/`，每轮 `.json` raw 保存 command、stdout、stderr、exit、完整 HEAD、环境、时间与 Python 文件 SHA-256，并有同 stem 九节中文 `.md`。失败轮均保留；报告不暂存。`rtk: skipped-for-report`；native subprocess 确保没有包装器缓存作为测试证据。

HTTP red 与定向 green 的两个明确 seam：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest \
  test_renderer_integration.HttpRendererSeamTests.test_replay_precedes_shared_disk_quota \
  test_renderer_integration.HttpRendererSeamTests.test_new_requests_quota_follows_snapshot_and_precedes_size -v
```

unit red：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest test_disk_quota -v`。

最终定向命令（review-targeted）：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest \
  test_disk_quota \
  test_renderer_integration.HttpRendererSeamTests.test_replay_precedes_shared_disk_quota \
  test_renderer_integration.HttpRendererSeamTests.test_new_requests_quota_follows_snapshot_and_precedes_size -v
```

| 轮次／report label | 结果（unittest 耗时；墙钟） | 开始时间 +08:00 |
|---|---|---|
| http-red | 2 tests／3 failures，7.224s；7.452s。其中一个 fixture 错误：原 warnings 还包含 UNKNOWN_OCCURRED_AT，不能把降级 warning 当作唯一值 | 12:44:21 |
| http-red-corrected | 2 tests／3 failures，7.000s；7.190s。未改生产代码；新 key 实际 202／422 而非 507，原重放已返回原 202 | 12:44:44 |
| unit-red | 13 tests／13 errors，10.048s；10.190s。缺少 quota 模块／构造参数；非法配置仍启动，受 10s 测试 deadline 终止 | 12:45:54 |
| targeted-first-green（实际失败，保留原 label） | 15 tests／1 failure／1 error，7.641s；7.843s。两处新测试把 keyword-only `_scope(metrics=...)` 误作位置参数，修正 fixture，不改产品去迁就测试 | 12:47:46 |
| targeted-green | 15 passed，7.467s；7.660s | 12:49:48 |
| stores-subset | 33 tests／2 errors／2 skipped，1.201s；1.350s。旧 Recording 未暴露共享 quota；foreign-home fixture 错用了本地 snapshots；迁移两个调用方，保留 pin／隔离断言 | 12:49:56 |
| stores-corrected | 上述两用例 2 passed，0.120s；0.271s | 12:50:31 |
| standalone-red | 1 test／1 error，0.028s；0.169s。独立 SnapshotStore 重启未恢复 export 清扫所有者，过期产物余留 811 字节而误拒绝 | 12:52:07 |
| standalone-green | 同一用例 1 passed，0.034s；0.175s；复用 ExportStore 读取／清扫规则，无新 parser 或 worker | 12:52:35 |
| golden | 61 passed，0.391s；0.538s；契约／golden 未改 | 12:52:50 |
| runtime-full | 394 tests，384 passed／10 skipped，131.998s；132.392s | 12:52:51 |
| targeted-final | 16 passed，7.773s；8.023s | 12:57:27 |
| process-smoke-final | 真实 serve 子进程，exit 0，3.690s | 12:57:35 |
| runtime-full-final | 394 tests，384 passed／10 skipped，129.360s；129.729s | 12:57:38 |
| review-targeted（最终定向） | 16 passed，7.536s；7.725s；加入独立 review 建议的真实保留／错误优先级断言 | 13:06:28 |
| review-full（Final Full Rerun） | 394 tests，384 passed／10 skipped，126.036s；126.378s；基线 378，新增 14 unit＋2 HTTP | 13:06:36 |
| review-ruff-check | All checks passed，exit 0，0.016s | 13:08:42 |
| review-ruff-format | 8 files already formatted，exit 0，0.058s | 13:08:42 |

精确报告 stem：`reports/api-report-<label>-feat_v2.1.0-rc.2-r2.2-pr1-disk-quota-507-2026-10-23T<HH-MM-SS>+08-00`；扩展名 `.json`／`.md`。上表给出 label 与开始时间。全量 runner 未逐例输出 skip 原因，保留其真实 10 skipped，不把总数写成全 passed；原生详细定向报告列出选中方法和全部 failure traceback。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest sbtd-runtime/tests/test_golden_contracts.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest discover -s sbtd-runtime/tests
RUFF_NO_CACHE=true ruff check sbtd-runtime/disk_quota.py sbtd-runtime/report_snapshot.py sbtd-runtime/export_store.py sbtd-runtime/serve.py sbtd-runtime/tests/test_disk_quota.py sbtd-runtime/tests/test_renderer_integration.py sbtd-runtime/tests/test_snapshot_persistence.py sbtd-runtime/tests/test_export_store.py
RUFF_NO_CACHE=true ruff format --check sbtd-runtime/disk_quota.py sbtd-runtime/report_snapshot.py sbtd-runtime/export_store.py sbtd-runtime/serve.py sbtd-runtime/tests/test_disk_quota.py sbtd-runtime/tests/test_renderer_integration.py sbtd-runtime/tests/test_snapshot_persistence.py sbtd-runtime/tests/test_export_store.py
git diff --check
git diff origin/main --stat -- sbtd-runtime/contracts docs/prd docs/adr
```

最终 diff 检查 exit 0，三个受保护目录 stat 为空。三份 touched task.md frontmatter 由 `yaml.safe_load` 解析通过；旧 done／completed_at／历史事件前缀不变、plan 全部任务表行逐字保持；对新增归因段落与当前结论执行专用 grep，禁用措辞零命中。初轮 ruff 发现测试里的缺显式 check=False、两处 nested with、宽泛 Exception，修正后上述 8 文件全部通过；无生产 lint suppression。LSP references 返回 No language server found，使用源码／契约及已知调用方检索；ty 未安装，未声称 typecheck 通过，不安装全局工具。

真实进程 smoke 命令为 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -c <script>`，完整无落盘脚本保存在 process-smoke-final raw.command。真实 EventStore golden 数据 → 启动 serve（env cap=1000000）→ 临时本地配对 → POST /api/v1/statistics/query → POST /api/v1/exports CSV 202 → GET /api/v1/exports/{id} ready → 写入真实 1000001 字节未知文件 → 同 key 原 202／相同 ID、warnings → 新 key 精确 507／U 等于两目录字节和 → 所有文件逐字节未改变；SIGINT exit 0，stderr 含 quota 数值 warning，不打印临时认证内容。无 renderer 替身，未使用真实 browser；JPEG/PDF HTTP 测试为用户指定的既有 worker seam 替身。

### 条件 → 测试 → 断言覆盖

| 条件 | 当前测试 file:line（均在 sbtd-runtime/tests/ 下） | 关键断言 |
|---|---|---|
| default／合法及非法 env | test_disk_quota.py:38 | 2000000000、前导零；空／零／符号／空白／单位／非 ASCII／过长整数拒绝，错误仅含变量名和合法格式 |
| 非法配置启动拒绝 | test_disk_quota.py:77 | 真 subprocess exit 2、原值不回显、temp 不清扫、无 serve.lock |
| U==L 放行／共享占用／库拒绝 | test_disk_quota.py:107 | 10 字节孤立 export＋snapshot 文件实际大小，后续拒绝两 byte counts 精确，无新文件，未知文件不变、已有 ID 复用 |
| 80% log-only／不热更新 | test_disk_quota.py:132 | 7/10 无 warning、8/10 有数值日志；snapshot warnings 无 quota code；启动后 env 改为 1 不影响已解析 10 |
| 新 snapshot 前跨 store sweep | test_disk_quota.py:148 | 过期 export 对及 snapshot 清掉后 cap=1 可新建，无旧文件 |
| standalone snapshot 重启 | test_disk_quota.py:167 | 不显式构造 ExportStore 仍能清掉旧 ready 对，新 snapshot 成功 |
| 新 export sweep／恰等 cap | test_disk_quota.py:182 | 过期 export 对删除，cap 恰等 snapshot 大小仍受理新 ID |
| pin／坏文件保留计数 | test_disk_quota.py:200 | 过期 pinned snapshot 可读、坏 JSON 不删、拒绝 U 精确 |
| 已确认／不明归属 temp | test_disk_quota.py:222 | 启动前两目录残留清掉；运行期未知匹配 temp 字节保留 |
| 计量失败 | test_disk_quota.py:238 | PermissionError 向上传递，未把未知占用当 0，新 snapshot 文件集合为空 |
| 链接／FIFO／不递归／hardlink | test_disk_quota.py:255 | fixtures 在启动前建立；两 hardlink 各计 5 字节；hardlink temp、symlink 自身、外部目标、嵌套文件均保留 |
| 删除失败重新计量 | test_disk_quota.py:278 | unlink PermissionError 后仍以完整旧 snapshot 大小拒绝，文件存在 |
| prepare 后锁内再次准入 | test_disk_quota.py:299 | preflight 期间新增真实 bytes 后 507 库异常，零 job／残留 pin |
| publication 与 admission 协调 | test_disk_quota.py:315 | 暂停 temp 发布时创建线程等待，完成后按实际 bytes 拒绝；原 export ready、无残留 tmp |
| quota 下幂等重放 | test_renderer_integration.py:1328 | 原 202／ID／warnings、无新 job／文件／renderer 调用；新 key 真正 507 |
| HTTP 全顺序／精确 507 | test_renderer_integration.py:1363 | 超限下 401／403／400；503 先于 missing／gone／quota；404／410 先于 507；有效 JPEG 原会 422，超限变 507；四格式 exact keys/body/schema；无 job／文件／pin |
| crash／恢复引用／所有权原回归 | test_snapshot_persistence.py:102,146,175,207；test_export_store.py:324 | 哨兵逐字不变、有效 pin 保留、半写 temp 不升级并于重启清掉、导出校验对才可删除 |

### Gate 与设计结论追加（不改写初始 pending 记录）

- **DDIA Data Design Review: confirmed。** 磁盘 regular-file st_size 是占用事实源；两个 Store 仍各自拥有校验／清扫，共享 DiskQuota 的一个 RLock。export sweep → snapshot sweep → 已确认 temp → remeasure → warning/refusal，恢复引用先安装。render／JPEG preflight 在锁外；发布、读 ready bytes、引用变化与 sweep 串行化。prepare 前准入保证 507 在 422 前，建 job 前再次锁内 replay／quota 检查防止期间发布导致过期计量；不预留未来 bytes，无 schema／格式迁移。
- **Legacy Change Safety Review: characterized。** 生产编辑前 corrected HTTP red 明确缺少 507；保留 401／403／400、503、404／410、422 与重放。unit red 建立配置／文件边界安全网。standalone 缺口另经 red→green；旧测试只调整新清扫行为使之失效的准备顺序及共享 Store fixture，不删除其数据保留断言。
- **Refactoring Review: proceed（normal）。** 没有独立重构；新增真实共享协调器，复用各自文件 parser。SnapshotStore 单独使用时只在既有 exports/ 存在且未 defer 时恢复 ExportStore 所有者（无 worker、无在途 pin）；serve defer 后由实际 ExportStore 一次恢复／清扫，避免双重 startup 读取。
- **Ponytail Review／Code Readability Review。** Lean already；无新依赖、后台 timer、容量预留或 eviction。沿用明确的 Python 条件、原 Store fixtures 与中文 Markdown／英文 Gherkin；为安全所需的共享锁／temp 登记保留，不继续无关重构。
- **独立 review: correct。** QuotaSafetyReview 核实锁、目录／文件身份、恢复、优先级与拒绝；无 finding。QuotaCoverageReview 初轮无 P0–P2，提出 5 项 P3：hardlink-temp 在启动前准备、symlink 存活、超限下 401/403/400 三项已增强且复审 CLOSED；纯 default 构造接线断言按测试规范不新增；task slug 改名与用户指定路径冲突，不执行；reviewer 接受两项撤回。最终无 remaining findings，confidence 0.93。两位均只读、未运行测试／lint／format；不冒称外部 Reviewy 的 PR 审查。
- **project-validation: passed（本地指定范围）。** BDD traceable，三个既有 Markdown spec 更新对应行为，无新 runner；Cross-repo context not-needed；API Contract verified；HTTP renderer E2E Mode mock-backed／Mock Strategy user-approved；真实进程 CSV smoke 为 backend-only／无 mock。Final Test Report／Run Summary MD generated，Targeted Rerun／Final Full Rerun passed。raw 的 Source Revision dirty／Evidence Publication local-only 保留；commit 2 后逐一比较八个提交 Python blob SHA-256 与 review-full raw 哈希完全相同，是内容身份重验证，不伪称新 CI。
- **Release Readiness Review: ready（仅 PR-1 本地交付）。** startup 无效配置 fail closed；未知／损坏数据保留可能持续阻止新建，用户说明提供调整上限与人工确认边界。U 是清扫后已有 bytes，受理后产物允许暂时越限；共享锁内文件 I/O 的吞吐／容量校准留 PR-4。Snapshot 库异常不新增 HTTP handler；现有 statistics/query 若触发库拒绝可能走通用 500，未擅增契约映射。无部署、push、PR、迁移或发布。macOS／Windows、用户 Mac 视觉／字体、AC-56 安全、AC-51／45 对账及 §18 性能按用户串行拆分留后续 PR；本地 ready 不等于 rc.2 release ready。

`install-and-use.md` 已最小同步 ADR §5 新配置面与 507 的操作说明，并清除与本次已实现清扫／配额直接冲突的旧句；未实施后续项 B/C、未做默认值容量校准。无需要修改冻结契约的 blocker，无 STOP。

## 提交与恢复边界

1. Commit 1：仅 plan、#160 task、#161 task、本 task 四份 records，回填并开启本任务。
2. Commit 2：实现、测试与必要用户说明／既有行为 spec；不混入历史 records。
3. Commit 3：仅本 task 的验证、覆盖映射、提交与模型 SNAPSHOT 追加记录。

路径逐级检查 containment／无 symlink；reports 由 `.gitignore:4:/ai/tasks/**/reports` 保护。沿用既有 rc.2 records 明示的 TaskStore catalog/frontmatter 兼容限制及 active／index 超授权边界；使用指定共享 Markdown 记录，不声称 helper lifecycle 或自动恢复成功，不改 active／index／ignore／developer 身份。无持久格式迁移；回退实现提交不执行数据删除。仅本地提交，无发布授权。

PR-1 本地提交证据：

1. `6da85134ff5e5270c3ac16181338b1612d8fc4a8` — `docs(plan): backfill #160 (e748a5e) and #161 (cb12b60); open R2.2 task record (R2.2 PR-1 commit 1)`；仅 plan、#160 task、#161 task、本 task 四份文件。
2. `62a10b452feb7dfd3b1ea59886775659679871b3` — `feat(runtime): shared snapshots/exports disk quota with 507 DISK_QUOTA_EXCEEDED (R2.2 PR-1)`；12 文件：disk_quota.py、report_snapshot.py、export_store.py、serve.py；test_disk_quota.py、test_renderer_integration.py、test_snapshot_persistence.py、test_export_store.py；install-and-use.md；r2.0c／r2.1a／r2.1b 三份既有 spec。八个 Python blob 与最终 full-suite 被测内容逐一匹配。
3. `docs(task): record R2.2 PR-1 disk quota + 507 verification` — 仅本 task，SHA 由最终输出提供，避免自引用。PR-1 本地交付完成，不将 R2.2 status 或 plan 任务表行改为 done。

## 模型使用

| agent/session | provider/model | thinkingLevel | assistant / toolCall | purpose | resolvedModelIsFallback | title-gen |
|---|---|---|---|---|---|---|
| astra ping／01a1670d-3152-7552-9c9d-4115fa5f0d26 | openai-codex/gpt-6-astra | high | 1 / 0（Lord 记录） | --no-tools；ASTRA_OK | false | 未知 |
| main／01a1670e-d268-7166-9235-0ea39b58c08f | openai-codex/gpt-6-astra | high | 4 / 23（PRE-COMMIT SNAPSHOT，非 FINAL） | 唯一 writer／controller；2026-10-23T12:40:31+08:00，main/session/2026-10-23T04-39-47-048Z_01a1670e-d268-7166-9235-0ea39b58c08f.jsonl 第 1–56 行 | false | 未知（运行中） |
| main／01a1670e-d268-7166-9235-0ea39b58c08f（追加取样） | openai-codex/gpt-6-astra | high | 70 / 123（PRE-COMMIT SNAPSHOT，非 FINAL） | 2026-10-23T13:10:53+08:00，main/session/2026-10-23T04-39-47-048Z_01a1670e-d268-7166-9235-0ea39b58c08f.jsonl 第 1–329 行；含实现与验证，不含本次记录提交后回复 | false | 未知（运行中） |
| QuotaSafetyReview／QuotaSafetyReview.jsonl | kimi-code/k3 | max | 18 / 29（已结束取样，第 1–91 行） | 只读安全／并发／所有权审查；2026-10-23T13:10:53+08:00 读取 | false | 未知 |
| QuotaCoverageReview／QuotaCoverageReview.jsonl | kimi-code/k3 | max | 60 / 78（已结束取样，第 1–227 行） | 只读覆盖／记录审查及 P3 闭环；2026-10-23T13:10:53+08:00 读取 | false | 未知 |

主会话按 message.role=assistant 及其 toolCall blocks 计数，只读 model_change／thinking_level_change；后续编辑、校验、提交和最终回复不在该 SNAPSHOT 内。FINAL 由 Lord 在 PR body 报告，不将提交前取样写成最终值。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-23T12:40:31+08:00 | planned | in-progress | 用户 2026-10-23 12:11 +08:00 群内说开始 R2.2，Lord 按 plan.md 定拆分为 4 个串行 PR（PR-1 配额与 507 → PR-2 安全 → PR-3 跨平台 E2E 与对账 → PR-4 性能、校准与收尾），Lord 记录 | strict／user；授权根、分支、入口 cb12b606f1ec74d8bc87da12dd0d828628fa7724 已核实；仅三个本地提交；plan R2.2 行保持 planned。 |
| 2026-10-23T13:09:16+08:00 | in-progress | checking | PR-1 red→green、真实进程 smoke、最终全量与静态检查完成，进入提交／证据收口；初始 Gate pending 的已执行结论见追加记录。 | corrected HTTP red 2 tests／3 failures；最终定向 16 passed／7.536s；full 394／384 passed／10 skipped／126.036s；golden 61 passed／0.391s；两位独立 reviewer correct，P3 已闭环；contract/PRD/ADR stat 空，三份 YAML 与新归因检查通过。 |
| 2026-10-23T13:10:53+08:00 | checking | in-progress | PR-1 本地实现与验证完成；R2.2 继续开放，PR-1 完成不等于 R2.2 done。严格串行 PR-2 安全 → PR-3 跨平台与对账 → PR-4 性能／校准／收尾仍待执行，plan R2.2 行保持 planned。 | 本地 commits 6da85134ff5e5270c3ac16181338b1612d8fc4a8、62a10b452feb7dfd3b1ea59886775659679871b3；第三 commit 仅本记录。八个 Python 提交 blob 与 final full-suite hash 一致；无 push／PR／部署／发布，completed_at 保持 null。 |
