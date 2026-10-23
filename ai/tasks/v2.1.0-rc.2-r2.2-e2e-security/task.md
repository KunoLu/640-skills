---
schema_version: 1
id: v2.1.0-rc.2-r2.2-e2e-security
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict；主会话唯一 writer／验证 controller；仅授权 worktree 内三个本地 commit，显式路径暂存；不 push／PR／评论／merge／rebase／amend，不修改全局配置或其他 worktree。
status: in-progress
branch: feat/v2.1.0-rc.2-r2.2-pr1-disk-quota-507
created_at: '2026-10-23T12:40:31+08:00'
updated_at: '2026-10-23T16:52:17+08:00'
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
| fix1／01a16732-f9bc-7106-811b-8024b58b6a99 | openai-codex/gpt-6-astra | high | 5 / 14（PRE-COMMIT SNAPSHOT，非 FINAL） | 唯一 writer；仅三份 task 归因追加；2026-10-23T13:20:17+08:00，~/.omp/logs/640-rc2-r22-pr1/fix1/session/2026-10-23T05-19-16-412Z_01a16732-f9bc-7106-811b-8024b58b6a99.jsonl 第 1–39 行；不含后续编辑、校验、提交及最终回复 | false | 未知（未核实） |
| PR-1 ping／01a1670d-3152-7552-9c9d-4115fa5f0d26 | openai-codex/gpt-6-astra | high | 1 / 0（FINAL） | 编排方整理；--no-tools，运行结束后重数 | false | pid 77991，0 requests |
| PR-1 main／01a1670e-d268-7166-9235-0ea39b58c08f | openai-codex/gpt-6-astra | high | 79 / 134（FINAL） | 编排方整理；运行结束后重数；旧 SNAPSHOT 4/23、70/123 保留 | false | 见下方独立 title-gen 行 |
| PR-1 QuotaSafetyReview／QuotaSafetyReview.jsonl | kimi-code/k3 | max | 18 / 29（FINAL） | 编排方整理；运行结束后重数 | false | 不混入主会话 |
| PR-1 QuotaCoverageReview／QuotaCoverageReview.jsonl | kimi-code/k3 | max | 60 / 78（FINAL） | 编排方整理；运行结束后重数 | false | 不混入主会话 |
| PR-1 fix1／01a16732-f9bc-7106-811b-8024b58b6a99 | openai-codex/gpt-6-astra | high | 11 / 23（FINAL） | 编排方整理；运行结束后重数；旧 SNAPSHOT 5/14 保留 | false | pid 108184，0 requests |
| PR-1 fix2 ping／01a16750-8c95-71c5-adb8-051892aaec3c | openai-codex/gpt-6-astra | high | 1 / 0（FINAL） | 编排方整理；--no-tools，运行结束后重数 | false | pid 140277，0 requests |
| PR-1 fix2／01a16751-07b5-7411-bffd-65a03cbcabb6 | openai-codex/gpt-6-astra | high | 8 / 23（FINAL） | 编排方整理；运行结束后重数 | false | pid 140886，0 requests |
| PR-1 main title-gen／omp pid 79678 | cursor/composer-2.5 → kimi-code/k3-256k | 不适用 | 4 requests（FINAL；不计入 main） | 编排方整理；composer-2.5 ×2 无标题，k3-256k ×2 成功 | false | 无 grok、无 fallback |
| PR-2 ping／01a1676a-bfe7-73e7-8f56-8c2f5d1ac31b | openai-codex/gpt-6-astra | high | 1 / 0（编排方整理） | --no-tools；ASTRA_OK；本轮 ping，不与 PR-1 ping 混淆 | 未独立核实 | pid 161309，0 title-gen requests（编排方整理） |
| PR-2 main／01a1676b-94e2-76ab-b238-5a67bf8c65ad | openai-codex/gpt-6-astra | high | 38 / 77（PRE-COMMIT SNAPSHOT，非 FINAL） | 2026-10-23T14:44:42+08:00；~/.omp/logs/640-rc2-r22-pr2/main/session/2026-10-23T06-21-06-146Z_01a1676b-94e2-76ab-b238-5a67bf8c65ad.jsonl 第 1–200 行；按 assistant 消息／toolCall blocks 计数；后续工具、编辑、提交与回复不含在内 | false | 未核实（运行中） |
| PR-2 SecurityEvidenceReview／SecurityEvidenceReview.jsonl | kimi-code/k3 | max | 23 / 30（已结束取样，非主会话 FINAL） | 同 session 目录下同 stem 子目录；第 1–94 行，只读安全 review | false | 未核实 |
| PR-2 RecordsEvidenceReview／RecordsEvidenceReview.jsonl | kimi-code/k3 | high | 44 / 47（已结束取样，非主会话 FINAL） | 同 session 目录下同 stem 子目录；第 1–149 行，只读 records／ADR review | false | 未核实 |
| PR-2 ping／01a1676a-bfe7 | openai-codex/gpt-6-astra | high | 1 / 0（FINAL） | 编排方整理；运行结束后 session jsonl 重数 | false | pid 161309，0 requests |
| PR-2 main／01a1676b-94e2 | openai-codex/gpt-6-astra | high | 44 / 83（FINAL） | 编排方整理；运行结束后重数；旧 SNAPSHOT 38/77 保留 | false | 见独立 title-gen 行 |
| PR-2 SecurityEvidenceReview | kimi-code/k3 | max | 23 / 30（FINAL） | 编排方整理；运行结束后重数 | false | 不混入主会话 |
| PR-2 RecordsEvidenceReview | kimi-code/k3 | high | 44 / 47（FINAL） | 编排方整理；运行结束后重数 | false | 不混入主会话 |
| PR-2 fix1／01a16788-c32c | openai-codex/gpt-6-astra | high | 9 / 17（FINAL） | 编排方整理；运行结束后重数 | false | pid 176915，0 requests |
| PR-2 fix2 ping／01a167ad-99d1 | openai-codex/gpt-6-astra | high | 1 / 0（FINAL） | 编排方整理；运行结束后重数 | false | pid 200750，0 requests |
| PR-2 fix2／01a167ad-e792 | openai-codex/gpt-6-astra | high | 9 / 15（FINAL） | 编排方整理；运行结束后重数 | false | pid 201112，0 requests |
| PR-2 main title-gen／pid 161858 | cursor/composer-2.5 → kimi-code/k3-256k | 不适用 | 3 requests（FINAL；不计入 main） | 编排方整理；composer-2.5 ×2（1 success、1 no title），k3-256k ×1 success | false | 无 grok／fallback |
| PR-2 ping／fix1／fix2 ping／fix2 title-gen | 不适用 | 不适用 | 各 0 requests（FINAL） | 编排方整理；pids 161309／176915／200750／201112 | false | 与上方对应 session 分列 |
| PR-3 ping／01a167c6-9c42-74b1-a31b-fd540df6b868 | openai-codex/gpt-6-astra | high | 1 / 0（编排方整理） | --no-tools；ASTRA_OK | 未独立核实 | omp pid 213823，0 title-gen requests（编排方整理） |
| PR-3 main／01a167c7-c661-75df-85f6-fa16bfe6b8a9 | openai-codex/gpt-6-astra | high | 76 / 142（PRE-COMMIT SNAPSHOT，非 FINAL） | 2026-10-23T16:50:06+08:00；~/.omp/logs/640-rc2-r22-pr3/main/session/2026-10-23T08-01-48-129Z_01a167c7-c661-75df-85f6-fa16bfe6b8a9.jsonl 第 1–405 行；按 assistant 消息／toolCall blocks 计数，不含后续报告、编辑、校验、提交与最终回复 | false | 未核实（运行中） |
| PR-3 NativeExecutionReview／NativeExecutionReview.jsonl | kimi-code/k3 | max | 43 / 62（已结束取样，非 FINAL） | 同 session stem 子目录，第 1–180 行；2026-10-23T16:50:06+08:00 读取；只读审查与闭环 | false | 未核实 |
| PR-3 ReconciliationRecordsReview／ReconciliationRecordsReview.jsonl | kimi-code/k3 | max | 55 / 71（已结束取样，非 FINAL） | 同 session stem 子目录，第 1–207 行；2026-10-23T16:50:06+08:00 读取；只读审查与闭环 | false | 未核实 |

主会话按 message.role=assistant 及其 toolCall blocks 计数，只读 model_change／thinking_level_change；后续编辑、校验、提交和最终回复不在该 SNAPSHOT 内。FINAL 由 Lord 在 PR body 报告，不将提交前取样写成最终值。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-23T12:40:31+08:00 | planned | in-progress | 用户 2026-10-23 12:11 +08:00 群内说开始 R2.2，Lord 按 plan.md 定拆分为 4 个串行 PR（PR-1 配额与 507 → PR-2 安全 → PR-3 跨平台 E2E 与对账 → PR-4 性能、校准与收尾），Lord 记录 | strict／user；授权根、分支、入口 cb12b606f1ec74d8bc87da12dd0d828628fa7724 已核实；仅三个本地提交；plan R2.2 行保持 planned。 |
| 2026-10-23T13:09:16+08:00 | in-progress | checking | PR-1 red→green、真实进程 smoke、最终全量与静态检查完成，进入提交／证据收口；初始 Gate pending 的已执行结论见追加记录。 | corrected HTTP red 2 tests／3 failures；最终定向 16 passed／7.536s；full 394／384 passed／10 skipped／126.036s；golden 61 passed／0.391s；两位独立 reviewer correct，P3 已闭环；contract/PRD/ADR stat 空，三份 YAML 与新归因检查通过。 |
| 2026-10-23T13:10:53+08:00 | checking | in-progress | PR-1 本地实现与验证完成；R2.2 继续开放，PR-1 完成不等于 R2.2 done。严格串行 PR-2 安全 → PR-3 跨平台与对账 → PR-4 性能／校准／收尾仍待执行，plan R2.2 行保持 planned。 | 本地 commits 6da85134ff5e5270c3ac16181338b1612d8fc4a8、62a10b452feb7dfd3b1ea59886775659679871b3；第三 commit 仅本记录。八个 Python 提交 blob 与 final full-suite hash 一致；无 push／PR／部署／发布，completed_at 保持 null。 |
| 2026-10-23T13:20:17+08:00 | in-progress | in-progress | 归因更正（append-only）：acdad55 基线第 44 行「mergedAt 由 Lord 提供」、第 157 行 ping「1 / 0（Lord 记录）」、第 163 行「FINAL 由 Lord 在 PR body 报告」的主体均应为 operator。operator 执行 gh 查询、ping、独立计数并撰写 PR body；main session 01a1670e-d268-7166-9235-0ea39b58c08f 的 FINAL 将由 operator 在 PR body 报告。本轮 fix1 仅追加 PRE-COMMIT SNAPSHOT，不冒充 FINAL；第 18 行与原第 169 行 12:11 拆分决定的 Lord 记录归因正确，原样保留。 | 本轮用户提供的操作事实：operator 分别运行 gh pr view 160 --json mergedAt,mergeCommit 与 gh pr view 161 --json mergedAt,mergeCommit，取得 mergedAt 2026-10-23T03:28:33Z／2026-10-23T04:01:59Z 及 mergeCommit e748a5eddfba38cd487af9dfc5271e601de7c76b／cb12b606f1ec74d8bc87da12dd0d828628fa7724；operator 运行并计数 ping。本轮 python3 只读复核 ~/.omp/logs/640-rc2-r22-pr1/ping/session/2026-10-23T04-38-00-274Z_01a1670d-3152-7552-9c9d-4115fa5f0d26.jsonl：9 行、1 assistant／0 toolCall、openai-codex/gpt-6-astra、thinking_level_change=high、resolvedModelIsFallback=false；fix1 模型取样见追加表行，计数口径为 type=message 且 message.role=assistant 的消息／其中 toolCall blocks。本轮沿用 strict／user，仅获准一个本地 records commit；未完整调用 grill-with-docs（明确归因修正，无领域歧义）；DDD／DDIA／legacy／refactoring／release Gate、TDD／BDD 与独立 review 对本轮纯记录更正 not-needed，无代码、契约或部署变更；沿用既有 TaskStore 限制，不改 active／index 或历史 branch，不声称 helper lifecycle／自动恢复成功，不执行远端操作。 |
| 2026-10-23T13:52:35+08:00 | in-progress | in-progress | 归因更正（append-only）：2026-10-23T13:20:17+08:00 行的操作证据归因应为「编排方整理」，不是「用户提供」；涉及 gh 查询（gh pr view 160 --json mergedAt,mergeCommit、gh pr view 161 --json mergedAt,mergeCommit）、#160 PR body 编辑（2026-10-23 12:37 +08:00，gh pr edit 160 --body-file）及 session 计数复核。13:20:17 行逐字保留，本轮仅更正归因，不重新执行上述操作。 | Reviewy NOT CLEAN @ e67c472 (B1), Lord ruling 2026-10-23; append-only. |
| 2026-10-23T14:21:40+08:00 | in-progress | in-progress | PR-1 #162 squash-merge 回填（编排方整理）；R2.2 继续开放。 | PR https://github.com/KunoLu/640-skills/pull/162；head 01304fb7fbf45e8d9b7294b9000d5fccbb030f4a；merge SHA 83b14baee4e282d4863e693813b14a02c2b126b3；完成时间 2026-10-23T14:18:38+08:00，mergedAt 2026-10-23T06:18:38Z；本次 git log -1 --format='%H %cI' 83b14ba 核实 committer 时间一致。Lord 于 14:19 +08:00 宣布合并；CI run 39908593840 on 01304fb，11/11 pass（编排方整理；本轮不请求远端）。 |
| 2026-10-23T14:21:40+08:00 | in-progress | in-progress | PR-1 FINAL 模型／title-gen 追加回填；旧 SNAPSHOT 不改。 | 编排方整理：每次运行结束后从 session jsonl 重数，七个运行与 main title-gen 见新增 FINAL 表行；均 resolvedModelIsFallback false。本轮未重新读取历史日志，不冒称独立复核。 |
| 2026-10-23T14:21:40+08:00 | in-progress | in-progress | PR-2 strict 开工；用户 2026-10-23 12:11 +08:00 群内确认（开始 R2.2），Lord 记录；四串行 PR 拆分为编排方整理。 | 当前授权根 /workspace/640-skills-r22-pr2，分支 feat/v2.1.0-rc.2-r2.2-pr2-security，入口 HEAD 83b14baee4e282d4863e693813b14a02c2b126b3、工作区干净；历史 frontmatter branch 保留，本事件记录本轮绑定。仅三个本地 commit，不操作远端。未完整调用 grill-with-docs：验收与真实 loopback HTTP／进程日志 seam 已明确。沿用既有 TaskStore 兼容限制，不宣称 helper lifecycle／自动恢复，不写 active／index。 |
| 2026-10-23T14:21:40+08:00 | in-progress | in-progress | 更正 PR-1 Release Readiness 边界：statistics/query 超配额可能走通用 500 为「待用户决定（contract PR）」，未在 R2.2 PR-1／PR-2 修复；原 Release Readiness 行逐字保留。 | 不擅自新增 HTTP 映射，不修改 contract／schema／PRD／golden；本项停止于风险登记。 |
| 2026-10-23T14:44:42+08:00 | in-progress | in-progress | PR-2 安全证据本地完成；新增测试为 unchanged-production characterization，未发现需要生产修复的缺陷。PR-2 done 不等于 R2.2 done；R2.2 继续 in-progress，plan R2.2 行继续 planned 至 PR-4。 | Commit 1 3bf85861413eb09d7437ac52e529d047fffbeeff；commit 2 864ae0067fbc1f5400fb1d1531ef75f2615b89c1；第三 commit 仅本 task。最终 runtime 395 tests／385 passed／10 skipped，golden 61 passed；真实 CLI smoke 与安全子集通过；两位独立 reviewer correct，无 blocker。无远端操作、部署或发布。 |
| 2026-10-23T14:44:42+08:00 | in-progress | in-progress | PR-2 模型 PRE-COMMIT SNAPSHOT 与编排方整理的本轮 ping 追加；不改旧 SNAPSHOT／FINAL，不把运行中取样当最终值。 | main session 第 1–200 行 38／77；两位 reviewer 已结束取样见模型表；当前 writer 实际 openai-codex/gpt-6-astra high，无 fallback。 |
| 2026-10-23T14:53:18+08:00 | in-progress | in-progress | 归因更正（append-only）：14:21:40 「PR-2 strict 开工」行中「四串行 PR 拆分为编排方整理」应为：用户 2026-10-23 12:11 +08:00 群内说开始 R2.2，Lord 按 plan.md 定拆分为 4 个串行 PR，Lord 记录；原行逐字保留。 | 编排方整理：本文件 2026-10-23T12:40:31+08:00 planned→in-progress 事件；ai/tasks/v2.1.0-rc.2-plan/plan.md:73。 |
| 2026-10-23T15:33:52+08:00 | in-progress | in-progress | 归因更正（append-only）：d6f6419 基线 :202（HTTP／进程 seam）与 :227（§11）两处操作指令的归因应为「编排方整理」（Lord 的 prompt 指令），并非用户在群内作出的指示；原行逐字保留。 | Reviewy NOT CLEAN @ d6f6419（B1）；Lord 2026-10-23 15:32 +08:00 确认；append-only. |
| 2026-10-23T16:02:31+08:00 | in-progress | in-progress | PR-2 #163 squash-merge 回填（编排方整理）；R2.2 继续开放。 | https://github.com/KunoLu/640-skills/pull/163；head 2d2dbb2c18a0e130d8e63a9994fa0c64e7147cc5；merge SHA 4d29fc5a76482950965d929715d3096e66a57b54；本轮 git log -1 --format='%H %cI' 4d29fc5 核实 %cI 2026-10-23T15:59:11+08:00；GitHub mergedAt 2026-10-23T15:59:12+08:00（07:59:12Z）为编排方整理，两时刻相差 1 秒，不合并。 |
| 2026-10-23T16:02:31+08:00 | in-progress | in-progress | PR-2 合并前检查与合并后分支删除回填。 | 编排方整理：Lord 15:59 +08:00 room message／operator verification；head 2d2dbb2，OPEN、MERGEABLE、CI 11/11（run 39919059914）；合并后远端 branch deleted，返回 Branch not found；本轮不请求远端。 |
| 2026-10-23T16:02:31+08:00 | in-progress | in-progress | PR-2 Reviewy CLEAN 与 FINAL 模型回填；旧 SNAPSHOT 不改。 | 编排方整理：Reviewy CLEAN @ 2d2dbb2，model recount confirmed；运行结束后 session jsonl 计数及 title-gen 见新增 FINAL 表行，全部 resolvedModelIsFallback false。本轮未读取历史 session，不冒称独立重数。 |
| 2026-10-23T16:02:31+08:00 | in-progress | in-progress | 归因更正（append-only）：本次编辑前 4d29fc5 文件第 25 行（TDD seams）、第 39 行（project-validation 本地命令）、第 103 行（真实进程 smoke／worker seam）、第 133 行（独立 review／task slug 路径）四处旧归因应为「编排方整理」，不是群内用户陈述；原行逐字保留。 | Lord 的 prompt 指令；CodeX 提出后 Lord 于 2026-10-23 15:50–15:59 +08:00 间确认，具体分钟编排方未获知。本轮按内容定位并核实编辑前行号；第 203 行已有 15:33:52 更正，本事件不重复改写。 |
| 2026-10-23T16:02:31+08:00 | in-progress | in-progress | PR-3 strict 开工与本轮绑定追加（编排方整理）；历史 frontmatter／事件不重写。 | 本轮明确授权 /workspace/640-skills-r22-pr3、feat/v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation，入口 HEAD 4d29fc5a76482950965d929715d3096e66a57b54，工作区干净；延续既有 TaskStore 兼容限制，只更新指定 Markdown，不声称 helper rebind／自动恢复，不写 active／index。未完整调用 grill-with-docs：范围与验收已明确，无领域歧义；仅本地提交。 |
| 2026-10-23T16:52:17+08:00 | in-progress | in-progress | PR-3 本地实现、真实 Linux E2E 与对账验证完成；原生 macOS／Windows 仍 pending CI，不声明跨平台验收或发布就绪。 | Commit 1 3da831f6926b8fa0031ab18b9c5551cfff9c59e6；commit 2 6649a5e322871fb9683095395fcff4294ca70e68；最终 runtime 398 tests／388 passed／10 skipped，golden 61 passed；原生 driver 四格式与 3 cases 无 skip；两个只读 reviewer correct、findings 闭环。R2.2 status in-progress、plan 第 22 行 planned 保持，PR-4 未执行。 |
| 2026-10-23T16:52:17+08:00 | in-progress | in-progress | PR-3 CI 门与真实证据来源追加（编排方整理的验收）：新增原生 jobs 必须执行，不允许条件绕过或 continue-on-error。 | runtime-e2e-macos／runtime-e2e-windows；预期 11+2=13 checks，原 11 个 job 实例配置逐项保持。安装失败强制失败并保留证据；安装后 capability 真不可用时记录 unavailable／原因且验证 503，不能算四格式通过。无 push／PR／评论／merge，等待 operator 后续 push 后 CI。 |
| 2026-10-23T16:52:17+08:00 | in-progress | in-progress | 引用注记（append-only）：开工边界中的 test_serve.py:313 是 4d29fc5 基线行号；稳定符号为 PairingTests.test_pair_once_only_and_ticket_never_in_output，本轮 helper 编辑后声明位于第 317 行；旧注记原样保留。 | ReconciliationRecordsReview 已独立核实 313→317；覆盖仍仅 --no-open，浏览器自动打开路径未测。不是新增归因更正，不改写既有状态事件。 |
| 2026-10-23T16:52:17+08:00 | in-progress | in-progress | PR-3 模型 PRE-COMMIT SNAPSHOT 追加，不作 FINAL；历史记录与旧计数不改。 | 2026-10-23T16:50:06+08:00 main jsonl 第 1–405 行 76/142，astra high／fallback false；两位 kimi-code/k3 max reviewer 取样见模型表；ping 为编排方整理。 |

## R2.2 PR-2 Book Gate Plan（追加）

| Gate | 客观触发／阶段 | 本轮状态 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill／领域歧义，需求前 | not-needed；未完整 grill，D5–D8 既定，无新领域决定。 |
| book-ddia-data-design | 数据／schema／持久化设计前 | not-needed；仅安全证据，不改数据机制。 |
| book-legacy-change-safety／book-refactoring-pass | 生产行为／代码编辑前 | not-needed（计划无生产编辑）；若测试证明缺陷，先加载适用 gate 再最小修复。 |
| TDD／ponytail | 用户指定 HTTP／进程 seam，测试前 | 已加载；先补缺失测试并运行，既成实现通过则如实记 characterization，不伪造 red。 |
| 独立 review／Code Readability Review | 安全授权证据，check | pending；主会话唯一 writer／controller，独立只读审查安全覆盖与记录。 |
| project-validation | 本地测试后 | 已加载；定向真实 server、独立 smoke、golden、全量、ruff、diff／YAML；原生 raw 与同 stem 中文报告。 |
| book-release-readiness | runtime／部署变化，验证后 | not-needed（计划无生产编辑／部署）；若实际修复改变行为则重新判定。 |

本轮 ADR 0002 §3 只追加验证注记，既有风险决定不重写；不新增 BDD 行为，复用 R2.0a 安全规范。R2.2 task status 保持 in-progress，plan 任务表 R2.2 行保持 planned 至 PR-4。

## R2.2 PR-2 安全覆盖与验证（2026-10-23）

### 既有覆盖与补缺范围

先映射再补缺：既有 `test_serve.py:401`／`:417` 覆盖 GET health 的外部 Host／错误端口／跨 Origin 和合法白名单；`:454` 覆盖 Bearer／CSRF；`test_renderer_integration.py:823` 覆盖 capabilities 外部 Host／Origin 拒绝和数据字段不泄漏。原配对测试覆盖 200、重用 401、stdout/stderr ticket 不出现及错票读后即毁。本轮保留这些用例，只扩展日志捕获并新增一个完整 HTTP 安全矩阵；总数从 394 增至 395。

下表测试路径均相对于 `sbtd-runtime/tests/`；实现未改，状态码取既有 middleware／OpenAPI 403，而非新定契约。

| 验收 | 测试 file:line | 请求／关键断言 |
|---|---|---|
| AC-56 外部域名 Host／DNS rebinding | `test_renderer_integration.py:1017`，HostOriginSecurityTests.test_rejected_origins_cannot_pair_read_or_create_exports | `Host: evil.example`；POST /api/v1/session/pair、GET /api/v1/report-snapshots/{id}、POST /api/v1/exports 均 403 |
| AC-56 错误端口 | 同上 | Host 与 Origin 分别用非监听端口；同三路径均 403，端口上界避免构造 65536 |
| AC-56 跨 Origin 读／写 | 同上 | `Origin: https://evil.example`；有效 Bearer／CSRF、有效 snapshot／CSV payload 仍 403 |
| 拒绝不泄漏／无 CORS／无副作用 | 同上 | 所有拒绝响应精确 `{"detail":"forbidden"}`；大小写无关检查不存在 Access-Control-Allow-Origin；每次 GET／export POST 拒绝后 `_jobs == {}` 且 exports/ 为空；拒绝 pair 不消耗 ticket，随后合法 pair 200；合法 GET 200 和 export 202 作为正向控制 |
| ticket／Bearer never logged | `test_serve.py:313`，PairingTests.test_pair_once_only_and_ticket_never_in_output | 真实 serve 子进程，从既有 0600 文件取 ticket；startup → pair 200 → 带 Bearer GET /api/v1/metrics/catalog 200 → reused／wrong pair 401 → SIGINT exit 0；stdout、stderr、Python DEBUG file、home 下 .log／logs 文件均无 ticket／错误 ticket／Bearer／CSRF，无 `#ticket=`；DEBUG marker 证实捕获有效，秘密断言不回显值 |
| 错 ticket 首次尝试会销毁原票 | `test_serve.py:355`，既有 test_wrong_ticket_unauthorized_and_destroys | 首次 wrong 401 后，正确原票也 401；保留原测试，不重复实现 |
| ADR 风险与缓解 1／3 | `docs/adr/0002-v2.1.0-rc.2-r2.0a-dashboard-frontend-decisions.md:68–73` | 在 §3 末尾追加日期、测试引用及 --no-open/Linux 证据边界；原风险文本不改，保留同机进程参数可见的不可消除窗口；随 commit 2 提交 |

`_LoopbackApp` 复用真实 uvicorn socket／SnapshotStore／ExportStore，仅沿用既有构造 seam 注入真实 store 便于核对无 job；新增安全测试没有 browser renderer 行为替身。日志测试在导入 serve 前配置 root DEBUG 的 stderr 与文件 handler，不削弱生产 logging policy，不暴露新取票接口。实际安全文本为 PRD §10.2，AC-56 在 §16；用户所指 §11 亦已读，为未来集成／授权限制，不改章节或规范。

### 原生命令、结果与耗时

环境 Linux 6.12.94+／x64，Python 3.13.5。主会话唯一 writer／验证 controller；`rtk: skipped-for-report`，原生 subprocess 保留命令、输出、退出码、时间、SHA、环境和全部 41 个 runtime Python 文件哈希。报告均在本 task 的 ignored `reports/`，不暂存、不发布。

所有 unittest 命令前缀为 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests`：

```sh
python3 -B -m unittest test_renderer_integration.HostOriginSecurityTests -v
python3 -B -m unittest test_serve.PairingTests -v
python3 -B -m unittest test_serve test_renderer_integration.HostOriginSecurityTests test_renderer_integration.FrozenHttpExportTests.test_capabilities_require_session_and_allowed_host_origin -v
python3 -B -m unittest sbtd-runtime/tests/test_golden_contracts.py
python3 -B -m unittest discover -s sbtd-runtime/tests
RUFF_NO_CACHE=true ruff check sbtd-runtime/tests/test_serve.py sbtd-runtime/tests/test_renderer_integration.py
RUFF_NO_CACHE=true ruff format --check sbtd-runtime/tests/test_serve.py sbtd-runtime/tests/test_renderer_integration.py
git diff --check
git diff origin/main --stat -- sbtd-runtime/contracts docs/prd sbtd-runtime/golden
```

| report label | 开始时间 +08:00 | 实际结果 | unittest／墙钟秒 |
|---|---|---|---|
| host-origin-characterization | 14:25:02 | 1 passed；生产未改，首次 green | 3.296／3.496 |
| ticket-characterization | 14:25:33 | 2 passed；生产未改，首次 green | 1.126／1.194 |
| ruff-check | 14:25:59 | exit 1；测试 bootstrap 相邻字符串缺括号 ISC004；失败保留 | —／0.033 |
| ruff-format-check | 14:25:59 | exit 1；两个测试文件换行／class 空行；失败保留 | —／0.014 |
| process-smoke | 14:35:10 | exit 0；真实 CLI／CSV，无 renderer 替身 | —／3.901 |
| security-subset | 14:35:14 | 16 passed | 13.862／14.060 |
| golden | 14:35:40 | 61 passed，OK | 0.315／0.423 |
| ruff-check-corrected | 14:35:40 | All checks passed，exit 0 | —／0.018 |
| ruff-format-corrected | 14:35:40 | 2 files already formatted，exit 0 | —／0.012 |
| runtime-full | 14:36:00 | 395 tests，385 passed／10 skipped，OK | 134.582／134.959 |
| security-subset-final | 14:40:49 | 16 passed；cleanup 顺序修正后 | 13.329／13.535 |
| runtime-full-final | 14:41:03 | Final Full Rerun：395 tests，385 passed／10 skipped，OK | 131.450／131.804 |
| ruff-check-final | 14:43:15 | All checks passed，exit 0 | —／0.017 |
| ruff-format-final | 14:43:15 | 2 files already formatted，exit 0 | —／0.013 |

每轮 stem：`reports/api-report-<label>-feat_v2.1.0-rc.2-r2.2-pr2-security-2026-10-23T<HH-MM-SS>+08-00`，扩展名 `.json`／`.md`。最终九节中文汇总与同 stem raw：`reports/api-report-security-summary-feat_v2.1.0-rc.2-r2.2-pr2-security-2026-10-23T14-44-31+08-00.{json,md}`；汇总保留所有历史轮次，不冒称新执行。全量原生命令没有逐例输出 skip 原因，10 skipped 如实保留，不写全 passed。

真实 CLI smoke 命令为 `python3 -B -c <script>`（完整脚本在 process-smoke raw.command，无临时脚本落盘）：真实 EventStore golden → serve 启动 → 0600 文件配对 200／重用 401 → query 得真实快照 → cross-Origin GET／createExport POST 精确 403、无 CORS、exports/ 空 → 合法 CSV 202／ready／下载 200（含 export_schema_version）→ SIGINT 0；检查 stdout／stderr／DEBUG 文件无 ticket／Bearer／`#ticket=`。只打印安全结果摘要。

### Gate 结论与证据边界

- **TDD／安全网：characterization。** 两个 seam 首轮 green，未改生产代码，没有产品 red→green。唯一失败为测试代码的 lint／format，已修并保留 raw；手写复核将 PairingTests 临时目录释放改为 addCleanup LIFO，确保断言失败时先停止持有 DEBUG 文件的子进程，再删 home；随后子集／全量／ruff 均重跑通过。
- **独立 review／Code Readability Review：correct，无 blocker。** SecurityEvidenceReview 核实真实 socket、合法正向控制、四种拒绝矩阵、无 job/file、DEBUG handler 与 uvicorn 配置兼容、凭据断言及 cleanup 顺序；RecordsEvidenceReview 核实四文件回填、append-only、硬链接语义、ADR 引用，并独立复数 PR-1 七个 session／title-gen 日志。两者只读、未执行测试／lint／formatter，均覆盖最终 cleanup 修正；不是远端 Reviewy 或 CI。
- **project-validation：passed（本地指定范围）。** BDD traceable，沿用既有中文 Markdown D7/D8 与 unittest；无新用户行为／无新 .feature。Cross-repo context not-needed；API Contract verified；新增安全路径 E2E Mode backend-only／Mock Strategy none。真实 browser 自动打开、进程参数枚举、Chrome／Playwright／Maestro UI 验证不适用本次 backend 证据；不能据此宣称 UI／跨平台通过。
- **Book Gate：DDD／DDIA／legacy／refactoring／release not-needed。** 无完整 grill、无领域／数据机制／生产代码／部署变化；没有借安全证据重构实现或改 ADR 决策。Ponytail 复用两处既有 seams，不增加依赖或测试框架。
- **提交内容身份：已验证。** 最终全量原始 SHA 为 `3bf85861413eb09d7437ac52e529d047fffbeeff` 加当时测试 diff，Source Revision dirty／Evidence Publication local-only 不改写。commit 2 `864ae0067fbc1f5400fb1d1531ef75f2615b89c1` 的 41 个 runtime Python blob SHA-256 与 runtime-full-final raw.hashes 全部相同；这是内容身份重验证，不是提交后新执行或 CI。
- diff --check exit 0，contract／PRD／golden stat 为空；两份 touched task frontmatter 用 `yaml.safe_load` 解析通过；历史行保持原样，plan 行 22 不变，D 段原字节前缀保留，新增行无禁用归因措辞。LSP references 实际返回 No language server found；改用源码与 ServeProcess 调用点检索，未声称 LSP/typecheck 通过。
- Final Test Report／Run Summary MD generated；Targeted Rerun／Affected Subset Rerun／Final Full Rerun passed；Evidence Source developer-local，Environment Alignment verified 仅限本机。没有远端 CI、发布或部署证据；报告保持 ignored。

### 本地提交与开放项

1. `3bf85861413eb09d7437ac52e529d047fffbeeff` — `docs(plan,task): backfill #162 (83b14ba) merge + FINAL counts; deferred record nits (R2.2 PR-2 commit 1)`；恰为 R2.2 task、plan、install-and-use、prd-9-6 task 四文件。
2. `864ae0067fbc1f5400fb1d1531ef75f2615b89c1` — `test(serve): AC-56 Host/Origin negatives and ticket-never-logged evidence (R2.2 PR-2)`；test_serve.py、test_renderer_integration.py、ADR 0002 三文件，ADR 注记在本提交。
3. `docs(task): record R2.2 PR-2 security verification` — 仅本 task；SHA 由最终输出给出，避免自引用。

生产代码未改；contract／schema／PRD／golden 未改，无新契约变更请求。既存 statistics/query 超配额通用 500 仍为 **待用户决定（contract PR）**，本轮未处理。PR-3 继续跨平台 CI（macOS／Windows）、用户 Mac 视觉／字体 AC-33／AC-62 与四格式／Panel 对账 AC-51／AC-45；PR-4 继续 §18 性能、配额容量校准与 R2.2 收尾。浏览器启动参数同机可见的残余窗口不消除。R2.2 task in-progress／completed_at null、plan R2.2 planned 保持不变。只交付三个本地 commits；无 push／PR／评论／merge／rebase／amend，无其他 worktree／全局配置写入。恢复边界为本 worktree 提交内容，不宣称 TaskStore helper 或自动恢复成功。

## R2.2 PR-3 开工边界（追加）

- ADR 0002 §3「R2.2 PR-2 验证注记」范围补充记在本 task，不改 ADR：缓解 1「终端不打印 ticket URL」仅由 `test_serve.py:313` 的 `--no-open` 路径覆盖；浏览器自动打开路径未执行，不能推广为该路径的测试结论。本次 records-only commit 不新增或扩展测试。
- Book Gate Plan：DDD not-needed（未完整 grill、无领域歧义）；DDIA not-needed（不改持久化／schema／异步机制）；legacy/refactoring not-needed（计划不改生产代码，若发现 blocker 则先加载）；TDD／ponytail 已加载，seams 为真实 serve CLI／loopback API／四格式产物及 ReportDocument，按既成实现 characterization 如实记录；独立 review／Code Readability pending；project-validation 已加载，原生 raw 与同 stem 中文报告；release-readiness pending（新增原生 CI jobs，验证后检查证据与运行边界）。无新产品行为，不另立 BDD runner。
- 本轮仅 AC-33／62 平台 CI 与 AC-51／45 对账。macOS／Windows evidence pending CI；用户 Mac 视觉／字体仍待 D9 真机确认。statistics/query 超配额 507／500 仍为「待用户决定（contract PR）」；performance §18、配额校准与关闭 R2.2 归 PR-4。冻结 contract／schema／PRD／golden；plan 第 22 行 planned、task in-progress 不变。

## R2.2 PR-3 覆盖与验证（2026-10-23，developer-local）

### 实现范围与证据来源

唯一生产修复为 `serve.py` 的 Windows SIGBREAK 清理 blocker：固定版 uvicorn 在 ASGI shutdown 后恢复并重触发原 signal handler，默认 SIGBREAK 会直接终止，绕过 `serve.lock` 的 finally。现在在运行期将 SIGBREAK 设为 Python `default_int_handler`，复用既有 KeyboardInterrupt／锁释放路径，退出后恢复原 handler。POSIX 未提供 SIGBREAK 时保持原逻辑，不拓展 SIGTERM 产品语义。真实 Windows 行为仍待 CI；POSIX 用 SIGTERM 编号模拟 SIGBREAK 的回归明确不冒充 Windows。

`ServeProcess` 仅补 Windows 独立 console process group、CTRL_BREAK_EVENT 及 UTF-8 捕获；复用既有 EventStore／ticket／HTTP seam。`runtime_e2e.py` 在隔离临时 home 中实际启动 `python -B -m serve --no-open`，优先 localhost:6400；占用时由 harness 显式传另一端口，不改服务端 D5。依赖固定 `requirements-serve.txt`／`requirements-renderer.txt`；driver 经 Playwright `install --only-shell chromium` 安装至该临时 home 的 browsers/，结束后清理本次 home，不碰已有用户 runtime／全局配置。

| 验收 | test／job | 关键断言 | 已有证据／边界 |
|---|---|---|---|
| AC-33／AC-62 平台部分 | `tests/runtime_e2e.py`；`runtime-e2e-macos`／`runtime-e2e-windows` | 真实 CLI、health／根 HTML／catalog／statistics、文件配对 200 与重用 401；同 snapshot 四格式 202→ready→download 200、MIME／magic／size／SHA-256；SIGINT／CTRL_BREAK exit 0、锁移除、端口关闭、临时 home 删除 | Linux 本地默认 6400 实跑通过；两个 native jobs pending CI，不能宣称 Mac／Windows PASS |
| AC-51 | `ExportReconciliationTests.test_four_formats_key_values_agree`；driver 同一 HTTP snapshot 对账 | CSV metric 行 vs HTML dt/dd vs 实际 JPEG／PDF renderer 输入；库 golden 独立 pins：tasks.touched=2、steps.success_rate_observed=1/2；HTTP EventStore 重建不含 summary role，按同 snapshot API 值对比（本轮 3、1/2） | 普通 suite 明示 worker stub；native smoke 使用真实 Chromium。PDF 已有 pdftotext 时抽取下载字节，缺工具只验源文档；JPEG 不做 OCR |
| AC-45 | `ExportReconciliationTests.test_every_manifest_panel_has_export_content`；driver | 13 个 manifest Panel 与 HTML／JPEG／PDF 源文档 section.panel 的 Counter 精确相等，缺失／多余／重复均失败；CSV metric IDs 精确集合、数据族 rows 元数据 vs 实际明细计数、无 metric 的 Panel 映射到 task/run/step/event/data_quality；四格式 metadata panel_ids 相等 | 本地 stub 与 real renderer 均通过；PDF 文本含所有 Panel IDs 和 CJK；JPEG/PDF 人工视觉仍待 D9 |
| 字体／CJK | `runtime_e2e.browser_font_check` | 真实 Chromium 打开下载的 HTML，await document.fonts.ready、状态 loaded、Panel DOM 精确一致、概览／数据质量存在；CDP 读取实际产生 glyph 的 CJK 字体，不用 fallback fonts.check 冒充 | Linux 命中 Noto Sans CJK SC；Mac 视觉／字体待真机，Windows 仅 CI |
| 控制信号 blocker | `BreakShutdownTests.test_break_signal_exits_zero_and_releases_lock`；纳入 driver 3-case suite | real serve／uvicorn 收 signal 后 exit 0、锁移除；原生 Windows 用 CTRL_BREAK_EVENT，POSIX 仅编号模拟 | red -15→green 0；保留原 SIGINT／实例锁测试 |
| 安装失败不可伪造成功 | driver --install-browser，真实失败下载负例 | 先保留 command／exit／stdout／stderr，再 assert 安装 exit 0；安装失败整个 E2E exit 1 | PLAYWRIGHT_DOWNLOAD_HOST=http://127.0.0.1:9 负例实际 exit 1；随后正常下载／四格式／3 cases 通过 |

新的两项 jobs 无 job-level `if`、无 run-step 绕过条件、无 `continue-on-error`；只有 artifact upload 用 `if: always()` 保留失败，缺文件为 error。`yaml.safe_load` 后逐项比较原 jobs 完全不变，预期检查总数 **13（11+2）**；当前没有任何本 PR 原生 CI 结果。安装成功但 capability 真不可用时，HTML／CSV 仍须通过，JPEG／PDF 记录 unavailable 与安全原因、验证 503；不可把这种结果写成四格式通过。

### 精确命令、结果与失败保留

环境 Linux 6.12.94+／x64，Python 3.13.5。真实 renderer 在本 task ignored `reports/renderer-venv` 隔离环境安装精确依赖，Playwright 1.64.0／Chromium headless shell 156.0.8078.4 revision 1248；未装全局工具／未改系统字体。普通完整 suite 使用 `python3`，没有 Playwright，10 skipped 原样保留；真实 Chromium 另由 driver 明确执行，不能将二者混称。

命令前缀：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests`；ruff 使用 `RUFF_NO_CACHE=true`。native driver 的 python3 完整路径为 `/workspace/640-skills-r22-pr3/ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/reports/renderer-venv/bin/python3`，输出目录为本 task 的 `reports/`；所有原生命令、stdout、stderr、exit、时间和文件哈希均保存在 raw。

```sh
python3 -B -m unittest test_export_reconciliation -v
python3 -B -m unittest test_serve_signals -v
python3 -B -m unittest test_serve_signals test_serve.InstanceLockTests -v
python3 -B -m unittest sbtd-runtime/tests/test_golden_contracts.py
python3 -B -m unittest discover -s sbtd-runtime/tests
python3 -B -m unittest tests.test_workflow_contracts tests.test_ci_selection
python3 -B tests/run_ci.py --platform linux --shard 1 --shards 3 --list --output ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/reports/ci-inventory
ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/reports/renderer-venv/bin/python3 -B sbtd-runtime/tests/runtime_e2e.py --install-browser --output ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/reports
ruff check sbtd-runtime/serve.py sbtd-runtime/tests/test_serve.py sbtd-runtime/tests/test_serve_signals.py sbtd-runtime/tests/test_export_reconciliation.py sbtd-runtime/tests/runtime_e2e.py
ruff format --check sbtd-runtime/serve.py sbtd-runtime/tests/test_serve.py sbtd-runtime/tests/test_serve_signals.py sbtd-runtime/tests/test_export_reconciliation.py sbtd-runtime/tests/runtime_e2e.py
git diff --check
git diff origin/main --stat -- sbtd-runtime/contracts docs/prd sbtd-runtime/golden
```

| raw label | 开始时间 +08:00 | 原生结果 | unittest／墙钟秒 |
|---|---|---|---|
| reconciliation-characterization | 16:07:44 | 2 passed；unchanged production 首轮 green，明示 existing worker stub | 0.184／0.371 |
| native-e2e-first | 16:11:56 | exit 1；测试误用 running 状态，实际契约 generating | —／7.194 |
| native-e2e-polling-corrected | 16:18:58 | exit 1；四格式已生成，测试混用 library／HTTP tasks 表预期 2/3 | —／16.975 |
| break-shutdown-red | 16:20:24 | 1 test／1 failure；真实进程 exit -15，而非 0 | 0.649／0.733 |
| break-shutdown-green | 16:21:25 | 5 passed；含原 SIGINT／实例锁四用例 | 2.609／2.684 |
| native-e2e-snapshot-corrected | 16:21:28 | 真四格式、13 Panels、PDF text、CJK、cleanup 通过；当时 suite 2 cases | driver 25.327／25.594 |
| ruff-first | 16:23:43 | exit 1；UP017 timezone.utc，改用 datetime.UTC | —／0.022 |
| golden | 16:24:10 | 61 passed，OK | 0.331／0.445 |
| workflow-tests | 16:24:11 | 52 passed，OK | 0.510／0.650 |
| ci-dry-run | 16:24:34 | exit 2；runner 不支持 --dry-run 且要求 --output，不伪造成功 | —／0.054 |
| ruff-check／ruff-format | 16:24:34 | All checks passed／5 files already formatted | —／0.012、0.010 |
| ci-list-equivalent | 16:24:58 | --list --output 等价只列选择，exit 0；未改 run_ci.py | —／1.143 |
| native-e2e-unavailable | 16:24:59 | HTML／CSV passed；JPEG／PDF capability unavailable（Playwright 未装），503 验证；不算四格式通过 | driver 4.131／4.311 |
| runtime-full | 16:25:03 | 398 tests／388 passed／10 skipped，OK | 137.091／137.493 |
| native-e2e-final（后续 review 仍有修正，保留原 label） | 16:30:01 | 四格式通过；2-case suite | driver 24.296／24.521 |
| install-failure-negative | 16:41:23 | 关闭的本地下载端口，实际 exit 1，证明不可伪造 green；预期负例 | driver 4.638／4.867 |
| native-e2e-reviewed（最终 native smoke） | 16:42:36 | 四格式 real Chromium、13 Panels、PDF text、CJK、退出清理；suite 3 cases／0 failure／0 error／0 skipped | driver 25.231／25.454 |
| ruff-check-reviewed／ruff-format-reviewed | 16:43:01 | All checks passed／5 files already formatted | —／0.013、0.010 |
| runtime-full-reviewed（Final Full Rerun） | 16:47:06 | 398 tests／388 passed／10 skipped，OK | 132.849／133.213 |

每轮 raw／中文汇总 stem：`reports/api-report-<label>-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-2026-10-23T<HH-MM-SS>.{json,md}`。最终 driver 自身报告为 `reports/runtime-e2e-linux-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-20261023T084236Z.{json,md}`。九节中文总报告／同 stem raw：`reports/api-report-pr3-verification-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-2026-10-23T16-52-00.{json,md}`。失败轮全部保留；reports 不暂存／不发布。额外无落盘 corruption smoke 证明缺 Panel、多 Panel、错误 key value 三种变异均被拒绝，不替代正式 suite。

### Gate、review 与剩余边界

- **Legacy Change Safety Review: characterized；Refactoring Review: proceed（normal）。** 发现 SIGBREAK blocker 后、生产编辑前已加载两项 gate；real-process red→green 建立安全网。既有 SIGINT、API、配对、导出语义保持，不做无关重构。SIGBREAK 原 handler 成对安装／恢复，uvicorn 仍执行自身 ASGI shutdown。
- **TDD：对账为 characterization，退出 blocker 为 red→green。** 不为既成正确导出伪造 red。初稿两处 fixture／协议状态错误与 lint 失败如实保留；修测试，不改生产统计去迁就预期。新增中文 Markdown／English Gherkin 规范为 `sbtd-runtime/spec/r2.2-native-e2e-scenarios.md`，在生产 fix 前落盘。
- **独立 review／Code Readability：correct。** NativeExecutionReview 两项：安装失败必须 fatal、BreakShutdownTests 必须接 CI，均已修并复审 CLOSED；ReconciliationRecordsReview 的相同安装 finding 已关闭，历史行号漂移按本次追加事件解决。两位只读、不运行测试／lint／formatter，不是远端 Reviewy／CI。Ponytail 复用 stdlib／现有 worker seam，不引入框架、依赖或泛化层。
- **project-validation：passed（本地指定范围）。** BDD traceable；API Contract verified；Cross-repo context not-needed；真实 CLI smoke backend-only + real renderer／Mock Strategy none。普通 suite 的可选 browser worker 为既有 stub，明确标注。Playwright Python CLI／实际 Chromium 已执行；未改 UI，Chrome/Playwright MCP 与 Maestro 不需要。rtk skipped-for-report，原生 subprocess 保留证据；LSP 实际返回 No language server found，改用源码／调用点；ty 未安装，未声称 typecheck 通过。
- **Release Readiness Review: blocked（原生 CI／D9 验收未完成）。** 本地 code／tests 交付完成不等于 R2.2 完成或发布就绪。macOS／Windows 的 13 个 checks 必须在后续 CI 真实运行；用户 Mac 视觉／字体、JPEG/PDF 人工视觉仍待 D9。Windows 只有 CI 证据；chmod 的 POSIX mode 不证明 NTFS ACL。JPEG 不做 pixel OCR；PDF 缺 pdftotext 时报告 source-document-only，不装新抽取依赖。性能 §18／容量与默认配额校准归 PR-4。
- **提交内容身份已重验证。** 原 raw 使用真实被测 HEAD 3da831f + dirty 工作树，不改写为新 SHA。commit 2 的 44 个 runtime Python blob SHA-256 与 runtime-full-reviewed raw 全部相等；这是内容身份校验，不是提交后测试重跑／新 CI。最终 commit 只更新本 task。
- diff --check exit 0；冻结 contract／PRD／golden stat 为空。workflow YAML 解析并核对原 job 配置不变；task frontmatter 按 yaml.safe_load 校验。commit 1 提交后对 added-only 文本执行禁用归因 grep，零命中；旧行不改写。无新增 schema／contract／PRD／golden 变更请求。statistics/query 超配额 507／500 仍为 **待用户决定（contract PR）**，未处理。
- Final Test Report／Run Summary MD generated；Targeted Rerun／Affected Subset Rerun／Final Full Rerun passed（本地）。Evidence Source developer-local，Source Revision dirty 原始证据／提交内容身份已核验，Environment Alignment verified 仅 Linux，Evidence Publication local-only。无发布、部署、远端操作或用户数据删除；回退边界为撤回代码提交。沿用 Markdown 绑定记录，不宣称 TaskStore helper／自动恢复可靠。

### 本轮提交

1. `3da831f6926b8fa0031ab18b9c5551cfff9c59e6` — `docs(plan,task): backfill #163 merge and FINAL counts; scope and attribution notes (R2.2 PR-3 commit 1)`；仅 plan.md／本 task。ADR scope note 选择追加在本 task，未改 ADR 文件。
2. `6649a5e322871fb9683095395fcff4294ca70e68` — `test(runtime): native macOS/Windows E2E and four-format reconciliation; fix Ctrl-Break cleanup`；8 文件：validation.yml、serve.py、test_serve.py、test_serve_signals.py、test_export_reconciliation.py、runtime_e2e.py、r2.2-native-e2e-scenarios.md、install-and-use.md。
3. `docs(task): record R2.2 PR-3 E2E/reconciliation verification` — 仅本 task；SHA 由最终输出提供，避免自引用。R2.2 保持 in-progress，plan 第 22 行保持 planned；没有 push／PR／评论／merge／rebase／amend／force。
