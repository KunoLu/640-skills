---
schema_version: 1
id: v2.1.0-rc.2-r2.2-e2e-security
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict；主会话唯一 writer／验证 controller；仅授权 worktree 内三个本地 commit，显式路径暂存；不 push／PR／评论／merge／rebase／amend，不修改全局配置或其他 worktree。
status: in-progress
branch: feat/v2.1.0-rc.2-r2.2-pr1-disk-quota-507
created_at: '2026-10-23T12:40:31+08:00'
updated_at: '2026-10-25T04:36:10+08:00'
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
| 2026-10-23T17:35:29+08:00 | in-progress | in-progress | PR-3 fix1 strict 绑定及 CI 失败记录（编排方整理；Lord 2026-10-23 17:08 +08:00 room message）。原 11 checks passed；runtime-e2e-macos 与 runtime-e2e-windows failed，未达到 13/13。 | run 39928738092 on 1f5145417d3b146de8f9079ed6badeacbcae9e3d；本地读取 ci-artifacts-1 两份原生 JSON 与 ci-failed-1.log。授权根 /workspace/640-skills-r22-pr3、分支 feat/v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation，入口 SHA 匹配且工作树干净；沿用 PR-3 追加绑定与 Markdown 记录边界，不改历史 frontmatter branch／mode_source／事件，不声称 TaskStore helper 成功。 |
| 2026-10-23T17:35:29+08:00 | in-progress | in-progress | macOS 根因与修复：临时 home 经过 /var → /private/var，生产 symlink 拒绝正确；只在 E2E fixtures 解析真实路径。 | CI macOS-26.6.2-arm64／Python 3.12.10，0.226s，StoreError: runtime home symlink is refused。runtime_e2e.py、test_export_reconciliation.py、test_serve_signals.py 的 runtime home 使用 Path.resolve；driver 清理检查使用同一 resolved home。Linux symlink TMPDIR＋真实 Chromium 实跑通过；macOS 待 CI 复跑。 |
| 2026-10-23T17:35:29+08:00 | in-progress | in-progress | Windows 根因与修复：Python 3.12 没有 os.fchmod；event_store 的 chmod 异常发生在 fdopen 前，unlink 打开文件造成 WinError 32，遮蔽 AttributeError；facade 同型代码一并修复。 | CI Windows Server 2025／Python 3.12.10，6.36s，spool/.ready.* 文件占用。两个 callsite 改为 fdopen 上下文内设置权限：有 fchmod 则使用 fd，否则 path chmod；写入前设 0600、异常关闭后才 unlink。新增 4 tests red→green，真实 append/replay／config 持久化及权限失败不发布、fd 在 unlink 前关闭；Windows 待 CI 复跑。 |
| 2026-10-23T17:35:29+08:00 | in-progress | in-progress | fix1 本地验证完成；driver 失败证据新增完整 traceback，未转换失败为 PASS；R2.2 保持 in-progress。 | 最终 runtime 402 tests／392 passed／10 既有 skipped／0 failures，golden 61 OK，定向 4 与子集 37 OK；Linux 普通及 symlink TMPDIR 的 real Chromium 四格式 E2E 通过。关闭下载端口负例 exit 1，JSON 与 MD 均保留完整 traceback。7 changed Python ruff check／format --check 通过；冻结目录 stat 空。macOS/Windows 待 CI 复跑；N/N=13/13 gate 未完成。 |
| 2026-10-23T17:48:01+08:00 | in-progress | in-progress | fix1 独立 review 闭环与最终证据追加；上方 runtime-full-final 标签保留，其最终性由本事件补充，不改旧行。 | PrivateWriteReview 发现四个新测试在原本无 fchmod 的平台会被 mock teardown 二次 delattr 破坏；已改为 pop＋仅原属性存在时 addCleanup 恢复，复审 correct／无 blocker。进入测试前即无 fchmod 的 4-case smoke 通过；最终 runtime-full-review-closed 为 402 tests／392 passed／10 既有 skipped／0 failures，128.687s；ruff 7 文件通过。NativeFlowReview 静态核查原生流程，无 blocking finding；不代表 CI。 |
| 2026-10-23T17:48:01+08:00 | in-progress | in-progress | fix1 本地 Commit A 已创建，Commit B 仅追加本 task 证据；macOS/Windows 待 CI 复跑，13/13 是目标门而非本轮结果。 | A 34d26a912451b1c69e2cc107c0ecf4938284a2ed：fix(runtime): portable 0600 writes and resolved native E2E temp homes (R2.2 PR-3 fix1)，7 Python files；44 个提交 runtime Python blob 与最终 full raw 哈希逐一一致，是内容身份重验证，不是提交后 CI。无 push／PR／评论／merge／rebase／amend／force；R2.2 status in-progress，completed_at null。 |
| 2026-10-23T18:12:29+08:00 | in-progress | in-progress | PR-3 fix2 strict 开工与本轮绑定追加（编排方整理；Lord 2026-10-23 18:03 +08:00 room message，延续 17:08 gate）。旧 11 checks green 为编排方整理；两个 native jobs failed，13/13 未达到。 | run 39934849292 on a5e9ee036d257d85f4422b0191caf889c82be077；完整读取 ci-artifacts-2 两份 JSON。当前授权根 /workspace/640-skills-r22-pr3、分支 feat/v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation，入口 SHA 匹配且工作区干净。沿用既有 PR-3 Markdown 绑定与 TaskStore 兼容边界，不改历史 frontmatter branch，不声称 helper rebind／自动恢复。 |
| 2026-10-23T18:30:15+08:00 | in-progress | in-progress | fix2 原生失败与 fix1 已证明范围追加（编排方整理）。两 runner 均已安装 Chromium headless shell 156.0.8078.4、serve :6400、pair 200／重用 401、catalog 200，正常退出 0、锁移除、端口关闭；fix1 的 resolved home／fchmod blocker 已越过。 | Windows Server 2025／Python 3.12.10：query 400；macOS 26.6.2 arm64／Python 3.12.10：HTML／CSV 202→ready→download 200，JPEG／PDF capabilities available，JPEG POST 500。旧 JSON 未保存错误正文／serve stderr，不能据此确认唯一错误码。 |
| 2026-10-23T18:30:15+08:00 | in-progress | in-progress | fix2 根因与最小修复：Windows IANA 数据库缺口已由本地真实 query／DST seam 验证，serve requirements 无条件固定 tzdata==2026.5；macOS Python 3.12 缺 os.waitid 已由官方文档与缺 API red 验证，renderer 改用不回收 leader 的 kqueue 退出通知。 | 生产不改时区校验、字体／capability、安全规则或错误协议；先 killpg、再 wait、最后以真实退出码读取结果。两项缺陷明确，但旧 CI 缺错误正文／stderr，未声称它们是该次 native run 的唯一故障。macOS/Windows 待 CI 复跑。 |
| 2026-10-23T18:30:15+08:00 | in-progress | in-progress | fix2 本地验证追加；新增 7 个测试，原生证据补齐脱敏日志和非预期响应正文，不把失败转 PASS。 | Linux real Chromium 四格式两轮通过；精确凭据正则审计 JSON／MD 零泄漏；nonreaping adapter＋真实 worker／后代清理 3 cases 通过。最终 full 409 tests／399 passed／10 既有 skipped／0 failures，golden 61 OK，workflow 52 OK，5 changed Python ruff check／format --check 通过。初轮缺测试依赖及 lint／fixture 失败保留，后续结论见本轮验证表；13/13 待 native CI。 |
| 2026-10-23T18:43:47+08:00 | in-progress | in-progress | fix2 独立 review P2 闭环：Darwin worker 在 kqueue 注册前退出可报 ESRCH；新增精确 ProcessLookupError 处理，不捕获其他 OSError、不提前 reap、不假定成功。 | 注册竞态 2 tests／2 errors red → worker suite 4 passed；NativeWaitReview 复审 correct／confidence 0.85。EvidenceSecurityReview correct／confidence 0.85，唯一 P3 保守截断标记按 blocker-only 范围 defer。两位均只读，不运行 tests／lint。 |
| 2026-10-23T18:43:47+08:00 | in-progress | in-progress | fix2 最终本地结果追加，覆盖上一轮 full 标签；macOS/Windows 待 CI 复跑，R2.2 继续 in-progress。 | 最终 runtime-full-reviewed 411 tests／401 passed／10 既有 skipped／0 failures，144.781s；新增共 9 tests。真实 Chromium 四格式复跑通过，driver 24.737s；nonreaping 真实进程 smoke 3 cases 通过；5 changed Python lint／format 通过。13/13 仍未得到新 CI 证据，无发布。 |
| 2026-10-23T18:45:27+08:00 | in-progress | in-progress | fix2 Commit A 本地创建，Commit B 仅追加本 task；实现与本地验证交付，macOS/Windows 待 CI 复跑。 | A 7f17563cf354e23c4bf4b83c5369c23b001b8a72：fix(runtime): pin tzdata, preserve native E2E diagnostics and fix macOS worker wait (R2.2 PR-3 fix2)。46 个提交 runtime Python blob SHA-256 与最终 full raw.hashes 全部一致，是内容身份核验，不是提交后 CI。最终 YAML／append-only／归因／diff 检查通过，冻结目录 stat 空；无 push／PR／评论／merge／rebase／amend／force。 |
| 2026-10-23T18:53:51+08:00 | in-progress | in-progress | PR-3 fix3 strict 开工（编排方整理）；延续 PR-3 授权根与追加绑定，历史 frontmatter branch／mode／事件不改。 | 入口 8f87df4c58e23fde48940adb519bd1be88a15b50，分支 feat/v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation，工作区干净；完整读取 run 39941735241 两份 JSON（含 serve_logs）：两个 native jobs failed，Windows 四格式已渲染下载，query 200；macOS JPEG preflight RENDERER_FAILED。旧 11 checks 状态本轮未获知，不推定。 |
| 2026-10-23T19:06:45+08:00 | in-progress | in-progress | fix3 本地诊断与验证追加；macOS/Windows 待 CI 复跑，13/13 gate 尚未完成。 | Windows helper 的 None 崩溃已 red→green；CPython 3.12.10 Windows reader 方法在 Linux 上重现解码异常导致 stdout None，具体 runner 编码仍是未证实推断。Linux 四格式两轮通过；JPEG POST500／PDF failed-job 故障注入均 exit1 并记录 worker 诊断；非 waitid adapter 下真实 Chromium 诊断重跑成功仍不改变原 HTTP500 的失败结论。 |
| 2026-10-23T19:06:45+08:00 | in-progress | in-progress | fix3 指定本地检查通过；初轮失败与原始记录保留，未新增 skip 或弱化断言。 | 定向15、golden61、workflow52；runtime416 tests／406 passed／10既有 skipped／0 failures（148.533s）；5 changed Python ruff check／format --check、diff --check、冻结目录 stat 空、yaml.safe_load／历史逐行保留／新归因检查通过；独立 review 尚在进行，结论另追加。 |
| 2026-10-23T19:14:52+08:00 | in-progress | in-progress | fix3 独立 review 闭环与本地 Commit A 追加；macOS/Windows 待 CI 复跑，未声明13/13。 | WorkerEvidenceReview correct／0.87、PdfExtractionReview correct／0.88，均只读／无blocking finding／未运行tests；两项P3非阻塞观察按blocking-only范围保留。A 09bd3fbcde6771e5182fc42c25beb5ff61f48fa8，7文件；48个runtime Python提交blob与最终full被测哈希一致，是内容身份重验证，不是新CI。Commit B仅本task追加记录。 |
| 2026-10-25T02:53:57+08:00 | in-progress | in-progress | 写入者：PR-4 main；开始入口进度核对（编排方整理） | status-sync §四.1；原最后事件 2026-10-24T09:25:04+08:00，缺 #165–#167；历史正文／事件保留。 |
| 2026-10-25T02:53:57+08:00 | in-progress | in-progress | 写入者：PR-4 main；完成入口核对与 #165–#167 进度补写（编排方整理） | 上表 SHA／git %cI 已核实，mergedAt／head 分列；三个对应 task status done；plan 已完整，不改。 |
| 2026-10-25T02:53:57+08:00 | in-progress | in-progress | 写入者：PR-4 main；记录用户 2026-10-24 22:48 群内确认（D9 等 Mac 证据时停），Lord 记录 | 先完成无需 Mac 证据的部分；AC-33／AC-62 人工视觉／字体只能来自用户 Mac 真机，不用 CI／Linux 替代。 |
| 2026-10-25T02:53:57+08:00 | in-progress | in-progress | 写入者：PR-4 main；开始 PR-4 strict 性能、容量与可做收尾（编排方整理） | 授权根／分支／入口及 #168–#173 基线见上；只作本地提交，不操作远端，不改冻结目录或默认值。 |
| 2026-10-25T02:53:57+08:00 | in-progress | in-progress | 写入者：PR-4 main；开始性能基准实现与实测（编排方整理） | PRD §14.1／§18，实际规模与 met／not-met／not-measured 如实记录；不修性能。 |
| 2026-10-25T03:18:40+08:00 | in-progress | in-progress | 写入者：PR-4 main；性能实现进度：基准初稿、极小 smoke 与 1000 事件试跑完成，较大规模仍在实测 | 首轮 smoke 2 OK／7.333s；1000 事件完整 append 用时 49.178s，约 20.334 条／秒，仅作为安排生成时限的本地依据，不外推百万性能。百万请求规模的 900 秒限时生成已启动，最终报告以实际接受数量为准。 |
| 2026-10-25T03:51:43+08:00 | in-progress | in-progress | 写入者：PR-4 main；完成性能基准实现与本机可用测量，未达到百万参考规模 | 1000／10000／11500 实际事件三档完成；基准总墙钟 2385.937s（39.766 分钟，不含开发／验证）；最大档真实 UI 11520 事件 p95=9.315s，not-met。JSON／同 stem 中文摘要与导出样本均已保存；生产无修改。 |
| 2026-10-25T03:51:43+08:00 | in-progress | in-progress | 写入者：PR-4 main；开始本地全量验证与提交前边界检查（编排方整理） | golden、runtime、workflow/task、changed Python ruff、parse／YAML、append-only／新增行限制／冻结目录；仍保持 in-progress，不关闭 R2.2。 |
| 2026-10-25T04:00:17+08:00 | in-progress | in-progress | 写入者：PR-4 main；完成本地验证与代码提交前检查，保留首轮环境失败 | golden 实际 63 OK；runtime 首轮 433 tests／1 failure／10 skipped（缺已声明 tzdata），仅本 worktree reports 内安装既有 requirements 后，定向 1 OK、子集 27 OK、最终 433 tests／423 passed／10 skipped／160.464s；workflow/task 135 OK；ruff check／format 两文件通过；parse／YAML／append-only／新增行限制／冻结目录通过。 |
| 2026-10-25T04:00:17+08:00 | in-progress | in-progress | 写入者：PR-4 main；开始三档容量汇总与默认配额校准（编排方整理） | 复用三档真实 snapshot／HTML／CSV／manifest st_size，计算 24h TTL 假设与 80% 点；JPEG／PDF 不可用，不将缺失值当 0 或宣称完整四格式容量已通过。 |
| 2026-10-25T04:02:20+08:00 | in-progress | in-progress | 写入者：PR-4 main；完成三档可测容量校准与默认值结论 | 18 份 HTML／CSV 样本 SHA-256／st_size 与源报告一致；部分一套 2,579,665／25,507,472／29,329,547 B。保持默认 2,000,000,000，不改代码；完整四格式因 JPEG/PDF unavailable 未测，未当 0。 |
| 2026-10-25T04:07:55+08:00 | in-progress | in-progress | 写入者：PR-4 main；开始最终记录收口与 AC／目标映射（编排方整理） | 三个本地提交已创建；50 个 Python 文件与最终 full 被测 hash 一致；只追加本 task，禁止改 plan 行或完成状态。 |
| 2026-10-25T04:07:55+08:00 | in-progress | in-progress | 写入者：PR-4 main；完成最终证据整理；PR-4 可在无 Mac 证据下完成的部分已本地完成；R2.2 保持 in-progress，等待用户 Mac 证据 | 性能／容量／验证／覆盖映射见 PR-4 追加节；D9 未满足，completed_at null；按用户 2026-10-24 22:48 群内确认（D9 等 Mac 证据时停），Lord 记录；不 push，不宣称发布就绪。 |
| 2026-10-25T04:36:10+08:00 | in-progress | in-progress | 写入者：PR-4 operator；记录补正：授权根改写为 `/workspace/640-skills-r22-pr4`，PR-4 模型表单列 main 内部辅助 model_usage 行 | Reviewy 要求的路径写法；session jsonl 只读复核 26 条 purpose find、typesafe/jev-latest，不计入 main 93 / 163 与 ping 1 / 0；历史正文与事件保留，status／completed_at 不变。 |

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

## R2.2 PR-3 fix1（编排方整理，2026-10-23）

### 范围、Book Gate 与实现边界

未完整调用 grill-with-docs：本轮是明确的两个平台 blocker 与失败证据补充，无领域歧义。strict 沿用原 task；唯一 writer／验证 controller 为主会话。未修改 contracts、PRD、schema、golden、CI job 条件、skip 或业务断言；不操作其他 worktree／全局配置，不 push／PR／评论／merge／rebase／amend／force。

| Gate | 客观触发／阶段 | fix1 证据／状态 |
|---|---|---|
| DDD | 完整 grill／领域歧义，需求前 | not-needed；无完整 grill，无新领域规则。 |
| Legacy Change Safety | 既有持久化 portability bug，生产编辑前 | characterized；CI 原始失败＋本地缺失 fchmod 的 4 个 red，保留 symlink／ownership／0600／原子写／异常传播。 |
| DDIA Data Design | 私有 spool／JSON 写入失败路径，设计前 | confirmed；所有权、格式、commit／replay 顺序不变；权限先于数据，关闭先于 replace／unlink；无迁移／重试／新锁。 |
| Refactoring | 既有生产代码编辑前 | proceed（normal）；无重构需要，复用 fdopen 和既有 chmod；不引入跨模块 helper 或依赖。 |
| TDD | 缺失平台 API 与清理边界 | 4 tests 首轮 AttributeError red；最终 4 passed。测试 seam 为真实 EventStore.append/replay 和 RuntimeFacade.set_observation_enabled；仅平台 API 缺失与 chmod 拒绝用 mock。 |
| Ponytail／可读性 | 实际 smoke 后 | Lean already；两个短条件分支，无抽象层；显式上下文所有权，无吞掉权限错误。测试检查真实写入、发布 mode、清理顺序与失败副作用。 |
| project-validation | 本地验证 | passed（Linux 指定范围）；见下表及 raw。 |
| 独立 review | 安全写入／跨平台路径，check | 已启动 PrivateWriteReview 与 NativeFlowReview，只读且不运行测试；最终结论另追加。 |
| Release Readiness | runtime portability，验证后 | blocked（原生 CI 未复跑）；本地修复交付不是 13/13 或发布就绪。 |

`event_store._write_ready` 与 `facade._write_json` 是生产代码中仅有的两处 `os.fchmod`；源码调用方分别为 append 与 _save_document。LSP references 返回 No language server found，改用源码调用点分析，不宣称 LSP/typecheck 通过。原有 POSIX 0600 路径保持 fd chmod，Windows fallback 不冒充 NTFS ACL 证明；权限异常仍传播。新增 success tests 删除 os.fchmod，检查真正的 append/replay／config 可读、路径 chmod 0600 被执行、POSIX 可观察 mode；failure tests 令临时文件 chmod 拒绝，检查无发布、fd 在实际 unlink 入口已经关闭。

`runtime_e2e.py` 仅增加 resolved home 与 traceback；`traceback.format_exc()` 写入 JSON 的 traceback 字段，同时放入 MD「失败、修复与复跑」代码块，原一行 error 保留。两个内嵌测试的 runtime home 同步 resolve；PDF 抽取临时目录只是 pdftotext 输入，不作为 runtime home，无需改变生产拒绝规则。

显式 changed-file ruff gate 暴露旧 facade／facade test 的 UTC alias、import 顺序与格式问题；仅在本次 7 个 changed Python 内使用 ruff format，实际重排 3 个文件，并修正 UTC alias／import 空行，随后全量重跑。不扩大到全仓格式化；失败报告原样保留。

### 原生路径静态核查

- macOS：三处 runtime temp home 都 resolve；生产 _path_has_symlink 不改；PDF-only temp 路径不进入 Store。
- Windows：两处 fchmod 均 capability-guarded；getuid 检查原有 hasattr guard；O_DIRECTORY／目录 fsync 与 killpg 原有 POSIX guard，无新增 POSIX-only call。
- CTRL_BREAK：ServeProcess 与 BreakShutdownTests 均使用 CREATE_NEW_PROCESS_GROUP；发送 CTRL_BREAK_EVENT，serve 既有 SIGBREAK default_int_handler／finally 清锁不变。Linux 仅模拟信号生命周期，不冒充 Windows 控制台证据。
- Playwright：两 native jobs 固定 Python 3.12.10 与 requirements；install --only-shell chromium 将 PLAYWRIGHT_BROWSERS_PATH 指向本次 home/browsers；renderer 按 pinned revision 和 Darwin arm64／Windows exe 路径查找，worker 使用同一 browser 根。
- 编码与端口：job PYTHONUTF8=1；driver 安装输出、ServeProcess、signal test 用 UTF-8；默认端口先探测，占用时显式 --port；不改变生产端口策略。
- 文件锁／清理：seed EventStore 在 finally close；HTTP 连接读取后 close；serve communicate／kill 等待先于 TemporaryDirectory 退出；browser context 的 browser.close 与 worker 清理保持原实现。两轮真实 Linux smoke 确认临时 home 删除、serve.lock 移除、端口关闭、退出 0。
- gate：未改 validation.yml，未新增 if／continue-on-error／skip／neutral；既有 artifact if: always() 仅保留失败证据，不绕过执行。renderer 真不可用才按原设计记录 unavailable＋503；serve／pair／API／HTML／CSV 不可降级。

### 本地验证命令与结果

环境 Linux 6.12.94+／x64，Python 3.13.5。Evidence Source developer-local，Source Revision dirty（入口完整 SHA 1f5145417d3b146de8f9079ed6badeacbcae9e3d＋当轮工作树），Evidence Publication local-only；原生 subprocess 保存 command／stdout／stderr／exit／时间／worktree／环境及 44 个 runtime Python 文件哈希。rtk skipped-for-report；不以包装器缓存证明执行。报告为 ignored reports/fix1-<label>-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-<YYYYMMDDTHHMMSSffffff>.json 与同 stem 九节中文 .md，失败轮未覆盖、不暂存。

命令公共环境：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests RUFF_NO_CACHE=true`。下列 `P` 是既有隔离环境的实际 python3：`ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/reports/renderer-venv/bin/python3`；未安装全局依赖。`CHANGED` 恰为 `sbtd-runtime/event_store.py sbtd-runtime/facade.py sbtd-runtime/tests/runtime_e2e.py sbtd-runtime/tests/test_export_reconciliation.py sbtd-runtime/tests/test_serve_signals.py sbtd-runtime/tests/test_event_store.py sbtd-runtime/tests/test_facade_registration.py`。

```sh
python3 -B -m unittest \
  test_event_store.EventStoreTests.test_append_without_fchmod_preserves_private_spool \
  test_event_store.EventStoreTests.test_permission_failure_closes_spool_before_cleanup \
  test_facade_registration.FacadeRegistrationTests.test_observation_without_fchmod_persists_private_config \
  test_facade_registration.FacadeRegistrationTests.test_permission_failure_closes_config_before_cleanup -v
python3 -B -m unittest test_event_store test_facade_registration -v
python3 -B sbtd-runtime/tests/runtime_e2e.py --output /tmp/r22-pr3-fix1-e2e
$P -B sbtd-runtime/tests/runtime_e2e.py --install-browser --output /tmp/r22-pr3-fix1-e2e
TMPDIR=<本轮临时目录/link，指向同目录/real> $P -B sbtd-runtime/tests/runtime_e2e.py --install-browser --output /tmp/r22-pr3-fix1-e2e-symlink
PLAYWRIGHT_DOWNLOAD_HOST=http://127.0.0.1:9 $P -B sbtd-runtime/tests/runtime_e2e.py --install-browser --output /tmp/r22-pr3-fix1-e2e-negative
python3 -m unittest sbtd-runtime/tests/test_golden_contracts.py
python3 -B -m unittest discover -s sbtd-runtime/tests
ruff check $CHANGED
ruff format --check $CHANGED
git diff --check
git diff origin/main --stat -- sbtd-runtime/contracts docs/prd
```

| raw label／本轮 | 结果 | unittest／墙钟秒 |
|---|---|---|
| portability-red | 4 tests／4 AttributeError errors，未改生产代码 | 0.130／0.380 |
| portability-green（首次，保留失败 label） | 3 passed／1 failure：测试错误期望 append 后仍保留 ready；实际成功提交会消费 spool。改为发布时检查 mode，不修改生产去保留文件 | 0.117／0.377 |
| portability-green-corrected | 4 passed | 0.126／0.373 |
| private-write-subset | 37 passed | 3.628／3.864 |
| native-linux | exit 0，passed-with-renderer-unavailable；真实 serve／pair／API／HTML／CSV 通过，系统 python3 无 Playwright，不计四格式通过 | driver 4.824／4.967 |
| native-linux-renderer | exit 0，四格式 real Chromium，13 Panels／PDF text／CJK／3-case suite／清理通过 | driver 23.841／24.056 |
| native-symlink-renderer | exit 0，symlink TMPDIR，同样四格式／3 cases／清理通过 | driver 23.006／23.221 |
| traceback-negative | 预期 exit 1；关闭的下载端口，安装失败不转 PASS；另用 python3 断言 JSON traceback 含 stack／exercise 且完整出现在 MD | driver 4.638／4.841 |
| golden | 61 tests，OK | 0.316／0.415 |
| runtime-full | 402 tests／392 passed／10 既有 skipped，0 failures | 130.277／130.603 |
| ruff-check／ruff-format | 初轮 exit 1；3 lint 问题／3 files would be reformatted，失败保留 | —／0.020、0.011 |
| ruff-format-apply／ruff-check-final | 3 files reformatted；剩余 import 空行 I001，exit 1，已修正且保留失败 | —／0.011、0.010 |
| portability-final | 加强 chmod fallback 与 unlink 前关闭断言后，4 passed | 0.125／0.350 |
| private-write-subset-final | 37 passed | 3.479／3.705 |
| runtime-full-final（Final Full Rerun） | 402 tests／392 passed／10 既有 skipped，0 failures；基线 398，新增 4 | 139.045／139.377 |
| ruff-check-final-closed／ruff-format-final-closed | All checks passed；7 files already formatted，exit 0 | —／0.013、0.009 |
| diff-check-final／frozen-paths | exit 0；contracts／docs/prd stat 为空 | —／0.006、0.002 |

最终 full raw stem：`reports/fix1-runtime-full-final-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-20261023T173255305180`。driver 原生 raw／同 stem MD：`/tmp/r22-pr3-fix1-e2e/runtime-e2e-linux-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-20261023T092716Z`；symlink 轮在 `/tmp/r22-pr3-fix1-e2e-symlink/`，stem 时间 `20261023T092740Z`；负例在 `/tmp/r22-pr3-fix1-e2e-negative/`，stem 时间 `20261023T092824Z`。每份 driver 记录逐请求 URI／状态，正向含配对、snapshot query、capabilities、四格式创建／轮询／下载；不包含认证值。

BDD traceable：复用既有 R1.1／R1.2a 私有持久化与 R2.2 native scenarios，不新增产品规则／runner。Cross-repo context not-needed；API Contract verified（冻结目录无变化）；真实 E2E backend-only + real renderer／Mock Strategy none；普通 suite 可选 renderer 仍为既有 stub。未改 UI，Chrome/Playwright MCP、Maestro 不需要；实际 Playwright Python／Chromium 已执行。原 full-suite 10 skips 如实保留，未新增 skip，native driver 的 3 cases 无 skip。

### 剩余风险与恢复边界

**macOS/Windows 待 CI 复跑。** 必须由 operator 后续 push 后的原生 CI 达到全部 N/N（当前 13/13），不能用本地 Linux、API 删除模拟或代码审查替代。原生 console signal／NTFS 文件锁、浏览器下载、平台 CJK 字体仍由该 runner 证明；Windows chmod 不是 ACL 证明。本轮未发现需要 contract／PRD／schema／golden 修改的新问题；历史 statistics/query 超配额 507／500 的 contract PR 边界仍保留，不处理。无迁移、数据清理或发布；可撤回代码提交恢复旧行为，不保证旧版在 Windows Python 3.12 可运行。临时 smoke symlink／home 已清理，保留本轮失败与成功 reports；不声称 helper lifecycle 或自动恢复成功。

### fix1 独立审查闭环与最终提交证据（17:48 +08:00 追加）

PrivateWriteReview：生产改动正确；初轮两项 P1 分别定位 event-store／facade 的 regression test：`patch.object(os, "fchmod", create=True)` 内删除 mock 属性，当原平台没有该属性时，mock teardown 还会 delattr 导致 AttributeError。四个测试已用 `os.__dict__.pop("fchmod", None)` 与条件 `addCleanup(setattr, ...)` 修正；Linux 恢复原 API，原本缺失的平台保持缺失。复审 correct／confidence 0.9，最终 SIM117 合并 assertRaisesRegex 上下文后的关闭顺序亦复核，无 remaining blocker。NativeFlowReview：三处 resolved home、两处 private write、guarded POSIX calls、CTRL_BREAK、Playwright 安装与 lookup、UTF-8、端口及清理链全部静态核查，无 blocking finding；只读审查，不运行 tests／lint／formatter。

追加验证命令：常规定向 4-case 命令及 `python3 -B -m unittest test_event_store test_facade_registration -v` 重跑；另用 `python3 -B -c <script>` 在 suite 载入前执行 `os.__dict__.pop("fchmod", None)`，运行同四个 case，随后断言属性仍不存在，完整脚本保存在 portability-initially-absent-final raw.command。它证明“原本没有 API”时测试自身不会在 teardown 报错，仍不是 native Windows 证据。

| raw label | 实际结果 | unittest／墙钟秒 |
|---|---|---|
| portability-reviewed | 4 passed | 0.135／0.364 |
| portability-initially-absent | 4 passed；suite 前已无 fchmod | 0.105／0.314 |
| private-write-subset-reviewed | 37 passed | 3.362／3.589 |
| runtime-full-reviewed | 402 tests／392 passed／10 skipped，OK | 129.697／130.018 |
| ruff-check-reviewed | exit 1，删去 del 语句后暴露两个 SIM117；合并相邻 with，不改异常断言或执行顺序，失败原样保留 | —／0.024 |
| ruff-check-review-closed／ruff-format-review-closed | All checks passed；7 files already formatted，exit 0 | —／0.013、0.010 |
| portability-initially-absent-final | 4 passed；最终上下文形态 | 0.120／0.355 |
| runtime-full-review-closed（本轮最终 Final Full Rerun） | 402 tests／392 passed／10 既有 skipped／0 failures | 128.687／128.999 |

最终 raw／同 stem 中文汇总为 `reports/fix1-runtime-full-review-closed-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-20261023T174451931254.{json,md}`。前面 runtime-full-final／runtime-full-reviewed 等 label 原样保留，不能作为后续 test 编辑后的最终结果。生产修复及 driver 行为未因 review 改变；两次真实 Chromium E2E 的证据仍按其原始 SHA／dirty 状态保留。

`python3 -B -c <records-check>` 实际执行 yaml.safe_load，确认 frontmatter 除 updated_at 之外逐字段不变、原 394 行除 updated_at 无删除／重写、所有旧状态事件逐字保留、新增文本无禁用归因措辞、validation.yml 与入口 blob 一致；完整脚本在 records-check raw.command。`git diff --check` 通过；`git diff origin/main --stat -- sbtd-runtime/contracts docs/prd sbtd-runtime/golden` 为空。44 个 runtime Python 提交 blob SHA-256 与最终 full raw.hashes 一致；不把提交前测试改称提交后执行。

Commit A：`34d26a912451b1c69e2cc107c0ecf4938284a2ed`，`fix(runtime): portable 0600 writes and resolved native E2E temp homes (R2.2 PR-3 fix1)`；文件为 event_store.py、facade.py、tests/runtime_e2e.py、tests/test_event_store.py、tests/test_export_reconciliation.py、tests/test_facade_registration.py、tests/test_serve_signals.py，均在 sbtd-runtime/ 下。Commit B：`docs(task): append native CI fix1 evidence and pending rerun (R2.2 PR-3)`，只含本 task，SHA 由最终输出给出避免自引用。全部显式路径暂存，reports／.omp-r12b-addendum.txt／ai/tasks/codex-verify／.env* 不暂存。

Release Readiness Review 保持 blocked：本地指定范围已通过，原生 N/N=13/13 仍待 operator push 后 CI。上方「当前 13/13」仅指当前目标检查总数，不是通过结果。真实 Windows 控制台信号／Job Object 清理、macOS 字体与 CDP glyph family、CDN 下载和端口竞争仍需原生证据；没有据此弱化 gate 或修改契约。Final Test Report／Run Summary MD generated；Targeted Rerun／Affected Subset Rerun／Final Full Rerun passed（Linux）；Evidence Publication local-only。

## R2.2 PR-3 fix2 Book Gate Plan（编排方整理）

未完整调用 grill-with-docs：平台 blocker、诊断证据与验收明确，无领域歧义。主会话唯一 writer／验证 controller；只读调查不执行测试。仅本地 code／records 两个提交，不改 contract／PRD／schema／golden，不降低 13/13 门槛。

| Gate | 触发／阶段 | 本轮状态／证据 |
|---|---|---|
| DDD／DDIA | 领域／持久化设计前 | not-needed；无完整 grill、领域歧义、数据机制或格式变更。 |
| Legacy Change Safety | 既有平台故障／编辑前 | characterized；两份 CI 原始失败；本地清空 TZPATH 且阻断 tzdata 后真实 normalize_scope 拒绝合法时区，恢复包后 query 接受且 DST 日为 82800 秒。 |
| Refactoring | 既有 driver 编辑前 | proceed（normal）；无需生产重构，保留安全与可用性断言，仅补依赖和诊断边界。 |
| TDD／BDD／ponytail | 证据安全／实现前 | 复用真实 serve 与既有中文 Markdown／English Gherkin；先补失败证据、脱敏／截断回归，再最小实现。 |
| project-validation／独立 review／可读性 | check | pending；真实 Chromium 四格式、本地指定 suites 与静态检查，主会话控制运行；原生 raw 与同 stem 中文汇总。 |
| Release Readiness | runtime dependency／验证后 | pending；macOS/Windows 待 CI 复跑，本地通过不能替代 native 13/13。 |

### fix2 根因、设计与静态平台核查

- Windows：`stats_query.normalize_scope` 调用 `ZoneInfo`；缺 IANA 数据时抛 `ZoneInfoNotFoundError`，转为 `QueryScopeError`／query 400。另一个生产调用点是 `contract_eval.civil_window_seconds`。无条件 pin 同时覆盖 Windows 与无系统数据库的精简 Linux；系统数据库仍优先。PyPI JSON 当次返回 2026.5、非 yanked（https://pypi.org/project/tzdata/）。requirements 沿用 `==` 固定版本、无 hash 的既有风格；两 native jobs 已安装此文件，workflow consistency tests 无需变更。
- macOS：Python 3.12 官方 `os.waitid` 文档明确 not available on macOS（https://docs.python.org/3.12/library/os.html#os.waitid）；旧代码仅以 `os.name == "posix"` 判断可用性。缺 API seam 真实进入 `_execute_job` 后出现 AttributeError。新路径使用 `select.kqueue`／`KQ_NOTE_EXIT`，不使用会提前 reap 的 `proc.poll`；通知只表示退出，真正状态由原 `_terminate_group` 在 killpg 后 wait 得到，再交 `_read_result`。Darwin kevent 初次注册也检测已发生条件；退出前／后注册的真实 native 行为仍待 CI。
- **DDIA Data Design Review: confirmed（新增 worker 生命周期触发，前表 not-needed 仅是初始范围）。** worker 独占 session／PGID，结果文件事实源和 job/profile 清理所有者不变；先终止组再 reap，队列 finally close；取消、超时和非零退出均失败。无新缓存、重试、schema、迁移或持久化路径。
- **Legacy Change Safety Review: characterized；Refactoring Review: proceed（normal）。** missing-waitid red 为 2 tests／4 AttributeError errors；green 覆盖成功、非零、信号退出与取消。沿用真实子进程 cleanup tests，另通过 Linux waitid-backed kqueue adapter 实跑 timeout／crash／cancel，检查清理前 PID 未回收、后代和 profile 删除、队列关闭；不把模拟 adapter 当 Darwin kernel 证明。
- macOS 字体路径不作猜改：本次 CI capability 为 available，已通过静态字体文件探测；生产 renderer 没有 CDP 字体 family 断言。后续 E2E family 检查使用小写 substring，`.PingFang SC` 同样匹配 `pingfang`。PLAYWRIGHT_BROWSERS_PATH、shell 路径、profile HOME／XDG、sandbox 参数、权限及 st_uid 检查不改；Chromium launch、真实字体与时序仍待 native run。
- PDF 没有 JPEG 同步 preflight，202 后仍经过同一 `_execute_job`，因此同受 waitid portability 影响。四格式后续 Panel／数值／CJK 断言保持；`assert_pdf_text` 缺 `pdftotext` 时原样返回 `source-document-only: pdftotext unavailable; no dependency added`，不是新 skip 或四格式失败放行。Linux 本次实际抽取 PDF 文本并验证 Panel、CJK、关键值。

### fix2 诊断证据与安全边界

driver 统一记录每次请求，包括初次配对和 ticket 重用；非预期状态在断言前记录脱敏正文（最多 4096 字符）。首次配对即使返回非预期状态，也先将返回的 access_token 与 CSRF 纳入原 secrets 列表。session 身份就是 Bearer token，serve 没有第二个 session cookie。finally 停止或强杀服务后，保存 stdout／stderr（各 16384 字符）、runtime-home 日志（每文件 16384、合计 65536 字符／32 文件）及截断标记。未启动 serve 的失败明确记录 not started，而非伪造输出。

所有已知凭据先替换再截断；异常／traceback／嵌入测试输出也在 JSON／MD 落盘前做最终脱敏与布尔断言。原始 stdout／stderr／home logs 中的凭据或 ticket URL 仍使 E2E 失败，脱敏不是豁免。测试对真实配对凭据只做布尔比较，不把失败值打印进报告；仅人工 synthetic markers 用于泄漏／截断负例。新增测试为 `test_runtime_e2e_evidence.py` 4 cases、`test_renderer_process_wait.py` 2 cases、`test_stats_query.py` 1 case；未新增 skip。

### fix2 本地验证命令、失败保留与结果

环境 Linux 6.12.94+／x64、Python 3.13.5；入口 a5e9ee036d257d85f4422b0191caf889c82be077＋dirty 工作树，developer-local／local-only。`P=ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/reports/renderer-venv/bin/python3`；只在这个既有本地 venv 安装声明依赖，不改全局环境。共同环境 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests RUFF_NO_CACHE=true`。rtk skipped-for-report，原生 subprocess 保存 stdout／stderr／exit／完整命令、时间、环境及全部 runtime Python SHA-256。

```sh
$P -m pip install -r sbtd-runtime/requirements-serve.txt
$P -m pip install -r sbtd-workflow-onboard/requirements.txt
$P -B -m unittest test_renderer_process_wait test_runtime_e2e_evidence test_stats_query -v
PYTHONTZPATH= $P -B sbtd-runtime/tests/runtime_e2e.py --install-browser --output /tmp/r22-pr3-fix2-e2e
$P -B -m unittest sbtd-runtime/tests/test_golden_contracts.py
python3 -B -m unittest tests.test_workflow_contracts tests.test_ci_selection
$P -B -m unittest test_facade_registration.FacadeRegistrationTests.test_preview_route_does_not_call_saving_route test_history_import test_renderer_integration.HttpRendererSeamTests -v
$P -B -m unittest discover -s sbtd-runtime/tests
ruff check sbtd-runtime/browser_renderer.py sbtd-runtime/tests/runtime_e2e.py sbtd-runtime/tests/test_runtime_e2e_evidence.py sbtd-runtime/tests/test_renderer_process_wait.py sbtd-runtime/tests/test_stats_query.py
ruff format --check sbtd-runtime/browser_renderer.py sbtd-runtime/tests/runtime_e2e.py sbtd-runtime/tests/test_runtime_e2e_evidence.py sbtd-runtime/tests/test_renderer_process_wait.py sbtd-runtime/tests/test_stats_query.py
git diff --check
git diff origin/main --stat -- sbtd-runtime/contracts docs/prd sbtd-runtime/golden
```

三个无落盘 smoke 脚本的完整 `python3 -B -c <script>` 命令在对应 raw.command：timezone-diagnosis 清空 TZPATH 并阻断／恢复 tzdata；nonreaping-process-smoke 用 Linux 内核 waitid 模拟 kqueue 事件、实际运行 3 个后代进程清理 case；native-redaction-audit 包装实际 driver，将本次凭据仅留内存，对 JSON／MD 做精确值正则查找，不输出值。

| raw label | 结果 | 原生 unittest／driver 秒；墙钟秒 |
|---|---|---|
| timezone-diagnosis | 无数据库拒绝合法时区；包内 fallback 接受，DST=82800；exit 0 | —；0.166 |
| evidence-red | 3 errors；新增证据 API 尚未实现 | 0.002；0.140 |
| evidence-green | 2 failures；测试误算 30 字符截断并假定默认 uvicorn stderr 有 shutdown 文案，非产品缺陷 | 3.795；3.984 |
| evidence-corrected | 3 passed；修正 fixture，删无根据的日志文案断言 | 3.785；3.971 |
| macos-wait-red | 2 tests／4 errors；缺 os.waitid，实际进入生产等待路径 | 0.008；0.137 |
| targeted-green | 31 tests／1 failure；系统 python3 未装 tzdata，空 TZPATH 正确暴露安装缺口 | 7.700；7.855 |
| ruff-check／ruff-format-check | ISC004 字符串括号与 3 个 changed files 格式；失败保留 | —；0.015／0.012 |
| targeted-venv | 31 passed；使用装有 serve 精确依赖的既有 venv | 7.828；8.058 |
| native-linux | real Chromium 四格式、13 Panels、PDF text／CJK、3-case suite 与清理通过；空 PYTHONTZPATH | 24.379；24.607 |
| nonreaping-process-smoke | 3 passed／0 skipped；真实 Linux worker／后代，kqueue 为 nonreaping adapter | 1.327；1.545 |
| native-redaction-audit | 四格式通过；ticket／Bearer session／CSRF 三种本次真实值在 JSON／MD 零命中 | 23.366；23.597 |
| golden／runtime-full（环境失败） | venv 缺 PyYAML／Markdown parser；golden 37 tests／1 error，full 381 tests／3 failures／32 errors／10 skipped；没有删断言或改产品 | 0.250／78.077；0.427／78.466 |
| install-test-dependencies | 按现有 onboard requirements 安装 PyYAML／markdown-it-py／tomlkit／mdurl 到本地 venv，exit 0 | —；0.776 |
| golden-corrected | 61 tests，OK | 0.319；0.479 |
| workflow | 52 tests，OK；validation.yml 未改 | 0.419；0.560 |
| environment-failures-targeted | 32 tests，OK；环境失败路径复跑 | 69.225；69.554 |
| runtime-full-final | 409 tests／399 passed／10 既有 skipped／0 failures | 145.248；145.687 |
| ruff-check-final／ruff-format-final | All checks passed／5 files already formatted | —；0.014／0.012 |
| diff-check | exit 2；本轮 task 追加段落末尾空行；随后继续追加本段消除 EOF 空行，不改历史 | —；0.005 |
| frozen-paths | exit 0，三个冻结目录 stat 为空 | —；0.002 |

全部 raw／中文汇总 stem 为 `reports/fix2-<label>-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-<YYYYMMDDTHHMMSSffffff>.{json,md}`；失败轮不覆盖、不暂存。最终 full stem 时间 `20261023T182721174302`。真实 driver JSON／MD：`/tmp/r22-pr3-fix2-e2e/runtime-e2e-linux-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-20261023T102101Z`；精确脱敏审计轮在 `/tmp/r22-pr3-fix2-e2e-audited/`，stem 时间 `20261023T102336Z`。

### fix2 验收边界

BDD traceable：沿用 `spec/r2.2-native-e2e-scenarios.md` 中文场景／English keywords，不新增 runner；时区恢复既有 QueryScope／DST 语义。Cross-repo context not-needed；API Contract verified（冻结目录无变化）；真实 E2E backend-only + real renderer／Mock Strategy none；缺 API 回归为明确的平台 seam 模拟，普通全量 renderer cases 仍保留既有 stub／10 skips。未改 UI，不运行 Chrome／Playwright MCP 或 Maestro；Playwright Python CLI／真实 Chromium 已运行。LSP references 返回 No language server found，使用源码调用点核查；ty 不可用，未安装全局工具，不声称 typecheck 通过。

**Ponytail Review／Code Readability Review：Lean already。** 使用 stdlib kqueue，未引入 ctypes ABI、Python 版本提升、重试、额外服务或第二套 renderer；保留真实进程组所有权与日志泄漏断言。readiness 仍受 native CI 约束。

### fix2 诊断负例与独立安全审查追加

`preflight-diagnostics-negative`（18:32:54 +08:00）为明确故障注入 smoke：仅本次真实 serve 子进程把 worker seam 设为 `RendererError(RENDERER_FAILED)`，capability 仍 available，HTML／CSV 真正完成后 JPEG 返回 500。driver 保持 exit 1／failed，JSON 同时保存 `Internal Server Error` 正文、stderr 与 runtime-home `runtime.log` 的 `export preflight failed: RENDERER_FAILED`；退出 0、锁／端口清理通过。外层诊断检查 exit 0／7.750s 墙钟，driver 7.516s；不把注入 renderer 当真实渲染成功。完整无落盘脚本在 raw.command；driver 原生证据 `/tmp/r22-pr3-fix2-e2e-negative/runtime-e2e-linux-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-20261023T103254Z.{json,md}`。

EvidenceSecurityReview：correct／confidence 0.85；已复核当前 snapshot，无 blocking finding。凭据先登记再断言、先脱敏再截断、JSON／MD／traceback 全局脱敏、原始日志泄漏仍 fail、startup／stop-timeout 清理与真实凭据布尔断言均通过只读 review。唯一 P3：`response_body_truncated` 比较原始字节数与 4096 字符 cap，多字节正文可能完整保存却保守标记 truncated；不影响正文、安全或 pass/fail。按编排方整理的“仅修 blocker”边界不改，reviewer 同意 defer；不是新契约决定。

`records-check` 已实际调用 `yaml.safe_load`，除 updated_at 外 frontmatter 逐字段不变、旧行仅 updated_at 替换、旧状态事件全部逐字保留，新增文本无禁用归因，validation.yml 与入口 blob 相同。`diff-check-corrected` exit 0。同 stem 九节中文总报告／raw：`reports/fix2-verification-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-20261023T183427.{json,md}`；列出命令、每轮失败／复跑与 API URI 矩阵，不替代 CI。

### fix2 native lifecycle review 闭环与最终验证

NativeWaitReview 初轮 P2：Darwin `NOTE_EXIT` 注册可能在子进程已退出／正在退出时以 ESRCH 拒绝，不能直接传播为渲染故障。该结论有 Chromium `base/process/kill_mac.cc` 的同型调用与竞态说明支持（https://raw.githubusercontent.com/chromium/chromium/main/base/process/kill_mac.cc）。前文“初次注册检测已发生条件”的一般 kevent 描述不能替代此平台例外，按本段补充，不改旧记录。

修复只在注册调用捕获 `ProcessLookupError`，设 `leader_exited`；loop 不再轮询无效注册，但仍执行原取消／deadline 检查。finally 保持 killpg→wait、关闭队列，`_read_result` 使用实际退出码；EPERM／其他 OSError 仍传播且清理。新增 rc=0／rc=7 已退出回归与 EPERM 保留回归，均检查 cleanup 前 returncode 为 None、无 poll、清理一次、queue close。独立复审全部 checkpoint 通过，P2 CLOSED，verdict correct；未宣称 macOS kernel 实测。

| 追加 raw label | 实际结果 | 原生秒；墙钟秒 |
|---|---|---|
| registration-race-red | 2 tests／2 errors；ESRCH 路径真实进入生产函数，EPERM case 本来通过 | 0.006；见 raw.seconds |
| registration-race-green | worker suite 4 tests，OK | 0.157；见 raw.seconds |
| nonreaping-process-smoke-reviewed | 真实 Linux worker／后代 timeout／crash／cancel 3 passed，0 skipped | 1.326；见 raw.seconds |
| ruff-check-reviewed／ruff-format-reviewed | All checks passed／5 files already formatted | 见 raw.seconds |
| native-linux-reviewed | real Chromium 四格式、PDF text／CJK、13 Panels、3-case suite、退出清理通过；空 PYTHONTZPATH | 24.737；24.954 |
| runtime-full-reviewed（最终 Final Full Rerun） | 411 tests／401 passed／10 既有 skipped／0 failures | 144.781；145.199 |

追加命令：`$P -B -m unittest test_renderer_process_wait.WorkerExitTests.test_exit_before_registration_preserves_real_result test_renderer_process_wait.WorkerExitTests.test_other_registration_errors_fail_and_clean_up -v`（red）、`$P -B -m unittest test_renderer_process_wait -v`（green）；其余与前节 full／ruff／smoke 相同，最终 E2E 输出改为 `/tmp/r22-pr3-fix2-e2e-reviewed`。精确 native stem `runtime-e2e-linux-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-20261023T104014Z`；最终 full raw stem 时间 `20261023T184039008844`。

记录笔误更正：前文 preflight-diagnostics-negative 的墙钟 `7.750s` 应为 raw.seconds=`7.731662s`（四舍五入 7.732s）；driver 7.516s 与 exit1／外层检查 exit0 均不变。失败及旧报告原样保留，不用后续结果改写早期证据。

最终九节中文总报告与同 stem raw 为 `reports/fix2-verification-review-closed-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-20261023T184347.{json,md}`，追加 review／竞态复跑，前份 18:34 汇总保留为中间轮。Final Test Report／Run Summary MD generated；Targeted Rerun／Affected Subset Rerun／Final Full Rerun passed（Linux）；Source Revision dirty／Evidence Publication local-only。

**Release Readiness Review: blocked（native gate）。** 本地实现与指定验证完成，不等于 macOS／Windows 或 release ready。仍须 operator push 后原生 CI 13/13；macOS kqueue／字体／Chromium launch 与 Windows 全四格式链未在本机证明。60s budget、单 worker、pin／原子发布、安全校验及 unavailable 原设计均未弱化。无迁移／数据清理；回退代码提交会恢复旧平台缺陷，不承诺修复前版本可用。无需要 contract／PRD／schema／golden 修改的新问题；历史 statistics/query 超配额 500／507 继续「待用户决定（contract PR）」，本轮未处理。D9 人工视觉、PR-4 性能／容量不在本轮验收。

### fix2 本地提交与恢复边界

Commit A：`7f17563cf354e23c4bf4b83c5369c23b001b8a72`，`fix(runtime): pin tzdata, preserve native E2E diagnostics and fix macOS worker wait (R2.2 PR-3 fix2)`。恰为 `sbtd-runtime/` 下 8 文件：`browser_renderer.py`、`requirements-serve.txt`、`docs/install-and-use.md`、`spec/r2.2-native-e2e-scenarios.md`、`tests/runtime_e2e.py`、`tests/test_renderer_process_wait.py`、`tests/test_runtime_e2e_evidence.py`、`tests/test_stats_query.py`。最终 full 被测 46 个 runtime Python 文件与提交 blob SHA-256 逐一相同；保留原始 a5e9ee0＋dirty 证据，不改称新 SHA 上运行。

Commit B：`docs(task): append native CI fix2 diagnosis and verification (R2.2 PR-3)`，仅本 task，SHA 由最终输出提供避免自引用。全部显式路径暂存；reports／.omp-r12b-addendum.txt／ai/tasks/codex-verify／.env* 均不暂存。未操作其他 worktree 或 omp 全局配置；task status in-progress、completed_at null、历史 frontmatter branch 与旧事件保持，只有 updated_at 更新。沿用追加 Markdown 记录边界，不声称 TaskStore helper lifecycle／自动恢复成功。

## R2.2 PR-3 fix3 Book Gate Plan（编排方整理）

未完整调用 grill-with-docs：两个 blocker、诊断要求与验收明确，无领域歧义。沿用既有 Markdown 记录／TaskStore 兼容边界，不声称 helper lifecycle／自动恢复；不写 active／index，不改历史绑定。仅本地 code／records 两提交，13/13 gate 不变。

| Gate | 触发／阶段 | 本轮计划／状态 |
|---|---|---|
| DDD／DDIA | 领域／持久化设计前 | not-needed；无完整 grill、领域歧义或持久化设计变化；如生产生命周期需改则重新评估。 |
| Legacy Change Safety | 既有 PDF helper／诊断失败，编辑前 | needs-safety-net；CI 已证明 None 崩溃与隐藏 preflight 错误；先补 fake pdftotext 与真实失败 worker 回归。 |
| Refactoring | 生产编辑前 | 计划不改生产；只诊断有证据的根因，不猜改 killpg／字体／sandbox；若需生产修复先执行 gate。 |
| TDD／BDD／ponytail | 证据行为，编辑前 | 已加载；复用既有 Markdown 中文场景／English keywords、unittest、真实 driver；不增加依赖或 runner。 |
| project-validation／独立 review／可读性 | check | pending；真实 Linux 四格式与强制失败诊断／脱敏检查、golden 61、runtime ≥411、workflow 52、changed Python ruff、冻结边界／YAML；独立只读 review。 |
| Release Readiness | native E2E，验证后 | pending；macOS/Windows 待 CI 复跑，不把本地验证等同 13/13 或发布就绪。 |

### fix3 已验证原因与仍待原生证据的假设

- **Windows 已验证缺陷**：`assert_pdf_text` 直接将 `result.stdout` 交给成员／正则断言，没有处理不可用的抽取结果。CI 四格式均 ready、下载成功且记录 SHA-256；之后 `text=None` 导致 TypeError。代码没有重赋值 stdout，driver／ServeProcess 未包装该 run 调用。新增 None case 精确复现同一 TypeError 后修复。
- **Windows 机制已验证，runner 触发条件仍未知**：读取 CPython v3.12.10 `Lib/subprocess.py`，Windows `_readerthread` 在 `buffer.append(fh.read())` 内解码；reader 抛异常后 buffer 为空，`_communicate` 将其变成 None。无落盘脚本抽取并执行该版本两个真实方法，UTF-8 reader 读 `0x80` → 后台 UnicodeDecodeError／stdout None，二进制 reader → 原 bytes。源码 https://raw.githubusercontent.com/python/cpython/v3.12.10/Lib/subprocess.py 。本机是 Linux 方法级复现，不是 Windows runner；CI JSON 没有 driver reader-thread stderr／pdftotext 路径版本，无法断言具体 cp1252／GBK 或排除其他管道读异常。
- **Windows 修复**：使用 `shutil.which` 的实际路径；`-enc UTF-8 -layout`，二进制 capture 后在主线程严格 decode。缺工具、执行异常／超时、非零退出、None／空文本／编码失败分别给出 `source-document-only` 原因；不声称文本已验证。可用非空文本的所有 Panel、两项 CJK 与关键值断言保持。fake pdftotext 真 subprocess 覆盖空白、无效 UTF-8、exit7、正确中文和四种错误正文；None case 使用 CompletedProcess seam。
- **macOS 已验证范围**：fix2 后仍为 JPEG POST500，serve stderr 明确 `export preflight failed: RENDERER_FAILED`；HTML／CSV 通过、capability available。尚不能定位唯一生产失败站点，不将 kqueue、字体或 killpg 假设写成已修复根因。
- **macOS 路径排查**：生产 `_platform_cjk_files` 已通过 capability；生产 worker 不做 CDP family 名称断言。driver 的 glyph 检查在四格式下载后才执行，不可能产生当前 JPEG POST500；`.PingFang SC` 已匹配 pingfang，Hiragino Sans GB 匹配 hiragino，STHeiti 未包含但不是此次 preflight 的已证原因。`chromium_sandbox=False`、profile HOME、PLAYWRIGHT_BROWSERS_PATH、kqueue、killpg／EPERM／ESRCH 与两秒清理边界均未猜改。
- **macOS 剩余假设**：Chromium launch／capture 的内部异常、kqueue 错误、或成功 worker 后的进程组清理失败。下一次 CI 的 worker exit、结果／错误文件、stderr、显式 exception site／context 将区分这些来源。没有足够证据安全修改生产逻辑，保持 fail closed。

### fix3 测试侧诊断与安全边界

`runtime_e2e_diagnostics.py` 只由 native driver 在可用 JPEG／PDF 的 POST／轮询失败时调用。输入是已下载的同快照 HTML（记录 SHA-256）和同一 runtime home，不打开／修改 Store。JPEG POST 失败重放 preflight，JPEG／PDF 已受理 job 失败重放渲染；沿用 `_render_document` → `_write_job` → `_execute_job` → worker entry → wait／killpg／Job Object → `_read_result`，生产代码不改。单独诊断尝试不是原失败的精确时序复现，也不把重放成功当原导出成功。

测试侧 worker 包装 `_write_error`，保留 `__cause__`／被 `from None` 抑制的 `__context__` 及 traceback／最后 frame site；父侧在生产清理删除 job 前保存 stdout／stderr、退出码、error.json／result.json／exception.json 是否存在和内容。先替换已知凭据，再对每个文本字段截断到16384字符并记 truncated。诊断结果也进入同 stem MD；原请求／job 断言仍向上抛出，driver 必须 exit1。生产服务仍只记录安全错误码，不扩大生产日志或 HTTP 错误内容。

两项新 worker regression 分别证明失败子进程的异常链／无结果／脱敏，以及“worker exit0＋有效 result.json，但 cleanup 抛错”的准确区分；后一项注入清理异常但先执行真实 kill／wait，不遗留进程。独立 real Chromium 非 waitid smoke 使用 Linux waitid-backed kqueue adapter，证明诊断沿用该分支且关闭队列；不是 Darwin kernel 或 Job Object 实测。

### fix3 本地命令、结果与报告

环境 Linux 6.12.94+／x64、Python 3.13.5；`P=ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/reports/renderer-venv/bin/python3`。共同环境 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests RUFF_NO_CACHE=true`。rtk skipped-for-report；所有正式检查用原生 subprocess 保存完整 command／stdout／stderr／exit、时间、入口 SHA `8f87df4c58e23fde48940adb519bd1be88a15b50`、worktree、branch 和全部 runtime Python SHA-256；developer-local／dirty／local-only，不冒充 CI。

```sh
$P -B -m unittest test_pdf_text.PdfTextTests.test_missing_stdout_is_a_reasoned_limitation -v
$P -B -m unittest test_pdf_text -v
$P -B -m unittest test_runtime_e2e_evidence.NativeEvidenceTests.test_failed_worker_records_exception_chain_and_result_absence test_runtime_e2e_evidence.NativeEvidenceTests.test_cleanup_failure_keeps_successful_worker_result -v
$P -B -m unittest test_runtime_e2e_evidence test_pdf_text -v
$P -B sbtd-runtime/tests/runtime_e2e.py --install-browser --output /tmp/r22-pr3-fix3-e2e
$P -B -m unittest test_pdf_text test_runtime_e2e_evidence test_renderer_process_wait test_export_reconciliation -v
$P -B -m unittest sbtd-runtime/tests/test_golden_contracts.py
python3 -B -m unittest tests.test_workflow_contracts tests.test_ci_selection
$P -B -m unittest discover -s sbtd-runtime/tests
ruff check sbtd-runtime/tests/runtime_e2e.py sbtd-runtime/tests/runtime_e2e_diagnostics.py sbtd-runtime/tests/test_export_reconciliation.py sbtd-runtime/tests/test_pdf_text.py sbtd-runtime/tests/test_runtime_e2e_evidence.py
ruff format --check sbtd-runtime/tests/runtime_e2e.py sbtd-runtime/tests/runtime_e2e_diagnostics.py sbtd-runtime/tests/test_export_reconciliation.py sbtd-runtime/tests/test_pdf_text.py sbtd-runtime/tests/test_runtime_e2e_evidence.py
git diff --check
git diff origin/main --stat -- sbtd-runtime/contracts docs/prd sbtd-runtime/golden
```

另有四个 `$P -B -c <script>` smoke：forced-worker-failures、native-redaction-audit、nonwaitid-replay-smoke、windows-reader-mechanism；完整可复现无落盘脚本均在对应 raw.command。records-check 同样保存完整脚本，实际使用 yaml.safe_load；只允许 updated_at frontmatter 差异，原历史行按顺序逐字保留，added-only 禁用归因零命中，validation.yml 与入口 byte-identical。工具调用层曾出现一次 throwaway smoke 字符串嵌套 SyntaxError，未启动 runner／未产生产品失败；修正脚本引号后实际执行如下，未隐藏原工具结果。

| raw label | 实际结果 | 原生耗时／墙钟秒 |
|---|---|---|
| pdf-none-red | 1 test／1 TypeError error，同 CI 崩溃 | 0.002／0.248 |
| pdf-green | 3 tests OK | 0.143／0.375 |
| worker-diagnostics-red | 2 errors，诊断模块尚未实现 | 0.001／0.225 |
| worker-diagnostics-green | 9 tests OK；包含真实查询／配对失败负例 | 7.840／8.082 |
| ruff-check／ruff-format-check | 初轮3 lint问题／5文件需格式化，失败保留 | —／0.016、0.010 |
| ruff-format-apply／ruff-check-corrected | 仅5 changed Python 格式化；All checks passed | —／0.011、0.009 |
| native-linux | 四格式 real Chromium、PDF文本／CJK／13 Panels／3-case suite／退出清理 passed | driver23.658／23.893 |
| forced-worker-failures | JPEG POST500 与 PDF failed-job 两次 driver 均 exit1；worker诊断完整；外层断言 exit0 | driver7.965、11.793／合计19.987 |
| native-redaction-audit | 四格式 real Chromium passed；实际ticket／Bearer／CSRF在JSON／MD精确匹配零 | driver23.316／23.547 |
| nonwaitid-replay-smoke | 真实Chromium诊断exit0／result存在，但原HTTP500 driver仍exit1；队列关闭 | driver8.797／9.011 |
| targeted-final | 15 tests OK | 7.689／7.886 |
| golden | 61 tests OK | 0.317／0.482 |
| workflow | 52 tests OK | 0.424／0.545 |
| runtime-full | 416 tests／406 passed／10既有skipped／0 failures | 148.533／149.016 |
| ruff-check-final／ruff-format-final | All checks passed／5 files already formatted | —／0.013、0.010 |
| diff-check／frozen-paths | exit0／冻结三个目录stat空 | —／0.005、0.002 |
| records-check | YAML／append-only／归因／workflow不变均通过 | —／0.041 |
| windows-reader-mechanism | 真实CPython方法级复现：解码失败→None，binary→原bytes | —／0.216 |

报告统一在本 task ignored `reports/`，最终带分支与时间的 stem 为 `fix3-<label>-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-<YYYYMMDDTHHMMSSffffff>`，扩展名 `.json`／同 stem 九节中文 `.md`。初始 report helper 的 Path.with_suffix 将带点分支误当扩展名，已保留原报告并生成带完整时间戳的副本；没有覆盖／删除失败，报告不暂存。最终 full stem 时间 `20261023T190144534827`；本地 Python 内容 SHA-256 逐一核对仍与该被测快照相同。

driver 原生证据：`/tmp/r22-pr3-fix3-e2e/` 的 stem 时间 `20261023T105756Z`；审计轮 `/tmp/r22-pr3-fix3-e2e-audited/` 为 `20261023T110014Z`；强制失败 `/tmp/r22-pr3-fix3-e2e-negative/jpeg/`／`pdf/` 为 `20261023T105926Z`／`20261023T105934Z`；非 waitid 轮 `/tmp/r22-pr3-fix3-nonwaitid/` 为 `20261023T110113Z`。每份均为 `runtime-e2e-linux-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-<时间>.{json,md}`，逐请求状态和证据保留。

### fix3 Gate 与剩余边界

Legacy Change Safety Review: characterized，None red→green 和 worker错误／清理边界安全网已执行。Refactoring Review: proceed（normal），无生产重构；DDD／DDIA not-needed，无领域／数据设计变化。Ponytail Review: Lean already；复用生产worker生命周期、stdlib mock／临时文件，不增加依赖或生产debug开关。Code Readability Review：抽取失败与内容不符明确分开；诊断模块独立于driver正常流程，避免复制生产worker／进程清理实现。

BDD traceable：修改既有 `spec/r2.2-native-e2e-scenarios.md`，中文场景／English keywords，无新runner；上述15-case命令及真实driver对应场景。API Contract verified（冻结目录不变）；Cross-repo context not-needed。真实四格式E2E为backend-only＋real renderer／Mock Strategy none；forced-worker／非waitid为明确故障／平台seam模拟，不能称原生平台通过。普通suite仍保留10既有skips／既有worker stub。未改UI，不运行Chrome／Playwright MCP或Maestro；Playwright Python CLI／真实Chromium已运行。LSP实际返回No language server found，使用源码调用点，不声称typecheck通过。

**Release Readiness Review: blocked（native gate）。** 本地实现与指定验证通过不等于13/13、跨平台验收或发布；macOS/Windows 待 CI 复跑。主会话无push／PR／评论／merge／rebase／amend／force，不操作其他worktree／全局配置。只撤回代码提交即可回退测试侧行为，无迁移或生产数据清理；保留失败证据。用户Mac人工视觉／字体与PR-4性能／容量不在本轮范围。未发现新的contract／PRD／schema／golden变更需要；既存statistics/query超配额500／507仍为「待用户决定（contract PR）」，本轮未处理。独立review与提交证据随后追加。

### fix3 独立 review、最终提交与恢复边界追加

WorkerEvidenceReview：correct／confidence0.87，无blocking finding；静态核实同home／同HTML重放、文件在cleanup前捕获、真实reaped退出码、Windows Job Object join、Darwin非waitid分支、被抑制context、脱敏后截断与原失败重抛。P3仅两项：stdio先完整读入内存再截断；末尾异常链next标记为context但无后继。按编排方整理的blocking-only边界不扩大修复；不是内存有硬上限的证明。reviewer确认PDF抽取不能产出文本时的限制记录是本轮明确授权，非空错误文本仍必须fail。docs编辑不在该reviewer责任范围。

PdfExtractionReview：correct／confidence0.88，无blocking finding；核实None／empty／nonzero／encoding分支、UTF-8 bytes捕获、CJK／Panel／key-value断言、fake subprocess和driver调用点；独立读取CPythonv3.12.10源码，认可“机制已证明、runner触发未证明”的区分。该review同时核查诊断原失败保留、生产生命周期与spec一致性；records读取截止19:06:45状态。两位均未运行tests／lint／build，不将主会话测试写成reviewer独立实跑。

Commit A：`09bd3fbcde6771e5182fc42c25beb5ff61f48fa8` — `fix(runtime): Windows pdftotext handling and native renderer worker diagnostics (R2.2 PR-3 fix3)`。恰为7文件：`sbtd-runtime/tests/runtime_e2e.py`、`runtime_e2e_diagnostics.py`、`test_export_reconciliation.py`、`test_pdf_text.py`、`test_runtime_e2e_evidence.py`（后四项同tests目录），以及`sbtd-runtime/spec/r2.2-native-e2e-scenarios.md`、`sbtd-runtime/docs/install-and-use.md`。没有修改生产renderer、schema、contract、PRD、golden或workflow。

提交后运行 `$P -B -c <commit-a-content-identity>`，逐一比较48个提交runtime Python blob SHA-256与最终runtime-full raw.hashes，全部相同；完整脚本在同label raw.command。这是被测内容身份重验证，原始full证据仍是入口8f87df4＋dirty，不改称09bd3fb上新执行。最终汇总`reports/fix3-verification-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-20261023T191003.{json,md}`保留；review-closed汇总另存，不覆盖原native／失败报告。

Commit B：`docs(task): append native CI fix3 diagnosis and verification (R2.2 PR-3)`，仅本task，SHA由最终回复提供以避免自引用。只按显式路径暂存；reports／.omp-r12b-addendum.txt／ai/tasks/codex-verify／.env*均不暂存。task继续in-progress、completed_at null；历史frontmatter／事件保持，仅updated_at更新。沿用Markdown追加绑定与既有TaskStore兼容边界，不宣称helper lifecycle或自动恢复成功。无远端操作／部署／发布。macOS/Windows 待 CI 复跑；本地交付不等于13/13 gate通过。

## R2.2 PR-3 fix4 入口与 Book Gate Plan（编排方整理）

编排方整理：Lord 2026-10-23 19:35 +08:00 fix4 order／rulings，仅修两个已证 CI blocker；strict 不变。授权根 `/workspace/640-skills-r22-pr3`、分支 `feat/v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation`、入口 `75c1c93678a0d50726a397ed5a16bece8778bdcd`，工作区干净。沿用既有 PR-3 追加绑定；保留历史 frontmatter 与所有旧事件，仅更新 updated_at，不调用会重写历史绑定的 TaskStore，不宣称 helper lifecycle／自动恢复。

编排方整理的 CI 证据：run `39945077815` on `75c1c93` 为 10/13；runtime-e2e-windows 已通过四格式、PDF text、CTRL_BREAK；runtime-e2e-macos、linux-shards (2)、linux-full 失败。A：成功 worker 的 result.json 无 warnings／aborted_urls、scale=2，无 error.json；finally killpg(SIGKILL) 在 Darwin zombie-only group 抛 EPERM，遮蔽成功结果。B：shards 只安装 Onboard requirements，缺 tzdata，空系统时区测试失败。已有证据作为事实，不重跑旧 CI 试图确认。

裁定：A 只有 reap 后 probe 明确 ESRCH 才能成功；持续 EPERM、存活组或超时仍失败，真实 worker error／非零退出／缺结果仍失败；Linux WNOWAIT 和 Windows Job Object 路径不改。B 仅在 linux-shards 原安装行追加 `-r sbtd-runtime/requirements-serve.txt`，补齐缺失依赖，不是 bypass。13 个 checks 名称／条件／矩阵／断言不改，不新增 skip／neutral／continue-on-error；contracts／PRD／schema／golden 不改。

未完整调用 grill-with-docs：根因、范围、错误边界与验收明确，无领域歧义。BDD 沿用既有 native E2E Markdown 场景及 unittest，不另建 runner／spec；本轮具体回归为成功结果仅在组已消失后返回、仍存在或权限不明的组 fail closed、worker 真实失败保持失败。测试 seam 为编排方整理明确的 mock killpg＋真实 `_execute_job`／`_terminate_group`／结果读取链。

| Gate | 客观触发／阶段 | 本轮状态／计划 |
|---|---|---|
| DDD／DDIA | 需求／数据设计前 | not-needed；无完整 grill、领域歧义、持久化或跨服务设计变更。 |
| Legacy Change Safety | 既有进程清理 bug／编辑前 | needs-safety-net；先在既有 process-wait 文件补 EPERM red 与失败保留回归，不引入生产 seam。 |
| Refactoring／ponytail | 生产编辑前 | pending；限定现有 cleanup 的异常分支，不改等待／所有权架构。 |
| TDD／BDD | 行为编辑前 | killpg seam 已明确；既有中文场景／English keywords，红绿验证不冒充 Darwin kernel。 |
| project-validation／独立 review／可读性 | check | pending；runtime full、tzdata 空 TZPATH、fresh venv shards、golden、workflow、真实四格式、lint／YAML／冻结边界。 |
| Release Readiness | runtime／验证后 | pending；macOS 待 CI 复跑；本机不能证明 13/13，不 push／发布。 |

### fix4 实现、审查与状态事件（编排方整理）

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-23T19:40:37+08:00 | in-progress | in-progress | A 的平台模拟 red：5 tests、8 errors，均为 cleanup 未处理 EPERM；既有 CI 根因不重新猜测 | reports/fix4-eperm-red-* 原生 stdout／stderr／command |
| 2026-10-23T19:40:55+08:00 | in-progress | in-progress | A 最小实现后 9 process-wait tests 通过；B 单行依赖补齐 | process-green；validation.yml 单行 diff |
| 2026-10-23T20:11:42+08:00 | in-progress | in-progress | code commit 已创建，追加绑定 SHA 的 shards 重跑，不覆盖前轮报告 | e771f0822dcaafa477e8447b6ea998cbe405de75 |
| 2026-10-23T20:35:12+08:00 | in-progress | in-progress | A/B 代码交付；最新额外 shard 重跑暴露范围外 link identity 失败，发布 gate blocked；macOS 待 CI 复跑 | fix4-linux-shards-final；filesystem-identity-probe；无 scope widening |

**A**：原 SIGKILL 捕获增加 PermissionError，但不把该异常当作成功。继续原 `proc.wait(timeout=5)`；原两秒 alive probe 允许 EPERM 继续探测，唯一成功出口仍为 ESRCH。持续 EPERM／存活组到 deadline 抛 RENDERER_FAILED；reap 超时继续传播失败。`_read_result`、Linux waitid/WNOWAIT、Windows Job Object 与其调用顺序均不改。新增五个测试覆盖 SIGKILL EPERM→reap→ESRCH、probe EPERM→ESRCH、持续 EPERM／alive、worker exit7／error.json／缺 result.json、reap timeout；无 skip。独立 review 指出 Windows 不暴露 signal.SIGKILL，测试已将 signal namespace 纳入平台模拟，生产不变。

**B**：只修改 `.github/workflows/validation.yml` 的 linux-shards 安装行，追加已有 pinned serve requirements（含 tzdata==2026.5）。没有修改 step 名称、条件、矩阵、其他 job、contracts 或任何 assertion。workflow 两组 52 tests 通过，无需 expectation 变更。新增依赖使 serve-dependent tests 实际执行；不属于 bypass。

Legacy Change Safety Review: characterized（原实现 EPERM red、真实结果与失败边界回归）；Refactoring Review: proceed／normal（无重构）；Ponytail Review／Code Readability Review: Lean already，沿用原等待／deadline，不增加新架构。CleanupSafetyReview：correct，confidence 0.90，无 blocker；RegressionGateReview：correct，confidence 0.85，Windows 测试常量修正已复审 CLOSED。两位只读、未执行 tests／lint／build；实际验证由主会话独占。LSP 返回 No language server found，源码检索确认唯一生产 cleanup 调用为 `_execute_job`。

### fix4 全部本地验证命令与结果

环境 Linux 6.12.94+／x64、Python 3.13.5；CI Python 仍为 3.12.10，此处不是原生 macOS／Windows 证明。共同环境 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests RUFF_NO_CACHE=true`。rtk skipped-for-report；原生 subprocess 保存 stdout／stderr／exit／命令／时间、真实入口 SHA、worktree、branch 与 48 个 runtime Python SHA-256。所有报告 developer-local／dirty／local-only，不冒充 PR-head CI。

```sh
R=ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/reports
P=$R/renderer-venv/bin/python3
V=$R/fix4-shards-bra6vd7i/venv
S=$V/bin/python3
python3 -m venv "$V"
$S -m pip install -r sbtd-workflow-onboard/requirements.txt -r sbtd-runtime/requirements-serve.txt
$P -m pip check
$P -B -m unittest test_renderer_process_wait.GroupPermissionTests -v
$P -B -m unittest test_renderer_process_wait -v
PYTHONTZPATH= $S -B -m unittest test_stats_query.NormalizeScopeTests.test_iana_queries_and_dst_work_without_system_timezone_data -v
$P -B -m unittest discover -s sbtd-runtime/tests
$P -B -m unittest sbtd-runtime/tests/test_golden_contracts.py
python3 -B -m unittest tests.test_workflow_contracts tests.test_ci_selection
$P -B sbtd-runtime/tests/runtime_e2e.py --install-browser --output /tmp/r22-pr3-fix4-e2e
PATH="$V/bin:$PATH" $S -m compileall -q sbtd-workflow-onboard/scripts tests
PATH="$V/bin:$PATH" $S -B tests/run_ci.py --platform linux --shard 2 --shards 3 --output "$R/fix4-linux-shards"
PATH="$V/bin:$PATH" $S -B tests/run_ci.py --platform linux --shard 1 --shards 3 --output "$R/fix4-linux-shards"
PATH="$V/bin:$PATH" $S -B tests/run_ci.py --platform linux --shard 3 --shards 3 --output "$R/fix4-linux-shards"
$S -B tests/run_ci.py --platform linux --shards 3 --output "$R/fix4-linux-shards" --verify-reports
VALIDATION_SHA=75c1c93678a0d50726a397ed5a16bece8778bdcd $S -B tests/run_ci.py --platform linux --shards 3 --output "$R/fix4-linux-shards" --verify-reports
VALIDATION_SHA=e771f0822dcaafa477e8447b6ea998cbe405de75 PATH="$V/bin:$PATH" $S -B tests/run_ci.py --platform linux --shard 2 --shards 3 --output "$R/fix4-linux-shards-final"
VALIDATION_SHA=e771f0822dcaafa477e8447b6ea998cbe405de75 PATH="$V/bin:$PATH" $S -B tests/run_ci.py --platform linux --shard 1 --shards 3 --output "$R/fix4-linux-shards-final"
VALIDATION_SHA=e771f0822dcaafa477e8447b6ea998cbe405de75 PATH="$V/bin:$PATH" $S -B tests/run_ci.py --platform linux --shard 3 --shards 3 --output "$R/fix4-linux-shards-final"
VALIDATION_SHA=e771f0822dcaafa477e8447b6ea998cbe405de75 $S -B tests/run_ci.py --platform linux --shards 3 --output "$R/fix4-linux-shards-final" --verify-reports
$S -B -m unittest tests.test_sbtd_probe_links.MaterializeAuthorizationTests.test_replaced_link_with_identical_text_is_refused tests.test_sbtd_probe_links.MaterializeAuthorizationTests.test_link_text_change_is_refused -v
ruff check sbtd-runtime/browser_renderer.py sbtd-runtime/tests/test_renderer_process_wait.py
ruff format --check sbtd-runtime/browser_renderer.py sbtd-runtime/tests/test_renderer_process_wait.py
git diff --check
git diff origin/main --stat -- sbtd-runtime/contracts docs/prd sbtd-runtime/golden
git diff 75c1c93 -- .github
```

另执行 `python3 -B -c <records-check>`、`python3 -B -c <commit-a-content-identity>`、`$S -B -c <filesystem-identity-probe>`；每份完整无落盘脚本均保存于对应 raw.command。records-check 首次脚本字符串换行转义 SyntaxError，修正后 yaml.safe_load／append-only／新增归因／workflow 单行断言通过；未更改产品去迁就检查。没有生成待清理源码脚手架。

| raw label／轮次 | 原生结果 | 墙钟秒 |
|---|---|---|
| eperm-red | 5 tests、8 errors，预期 red；原实现 EPERM 直接传播 | 0.212 |
| process-green／process-final | 各 9 tests OK，最终修正测试平台常量后重跑 | 0.356／0.363 |
| fresh-venv／shard-deps／renderer-deps | 创建新 venv、双 requirements 安装成功；pip check 无 broken requirements | 1.908／2.401／0.319 |
| empty-tzpath | 1 test OK，fresh venv 的 tzdata==2026.5，无系统 TZPATH | 0.190 |
| golden／workflow | 61 OK／52 OK | 0.463／0.528 |
| runtime-full／runtime-full-final | 各 421 tests，411 passed／10 既有 skipped／0 failures；最终轮原生 158.296s | 145.250／158.657 |
| native-linux | 四格式 real Chromium、PDF UTF-8／CJK／关键值、13 Panels、3-case suite、SIGINT exit0／lock／port 清理 passed；driver 23.883s | 24.107 |
| shard-compileall | exit0，沿用 workflow 预编译步骤 | 0.609 |
| linux-shard-2／1／3（首轮） | 816／694／877 tests，779／680／865 passed，37／14／12 既有 skips，全部0 failures | 402.729／494.422／415.738 |
| shard-coverage | exit1：缺 VALIDATION_SHA；不是 tests 失败 | 0.045 |
| shard-coverage-corrected | exit1：首轮原生 source_sha=null，无法补 env 修复旧报告身份，保留旧报告 | 0.055 |
| linux-shard-2-final | 816 tests，778 passed／37 skipped／1 failure：test_link_text_change_is_refused | 423.193 |
| linux-shard-1-final | 694 tests，679 passed／14 skipped／1 failure：test_replaced_link_with_identical_text_is_refused | 510.845 |
| linux-shard-3-final | 877 tests，865 passed／12 skipped／0 failures | 397.942 |
| shard-coverage-final | exit1：严格拒绝 unsuccessful shard；未绕过 | 0.044 |
| unrelated-links-targeted | 2 tests、1 failure：link_text_change 再现 link-mismatch != identity-mismatch；identical_text 此轮通过 | 0.133 |
| filesystem-identity-probe | 200/200 次 symlink unlink/recreate 后 dev／inode／ctime_ns tuple 相同，exit0；仅环境诊断 | 0.033 |
| ruff-check／ruff-check-final | All checks passed | 0.016／0.017 |
| ruff-format-check | exit1，单处测试调用换行需调整；手工最小格式修正 | 0.013 |
| ruff-format-final／ruff-format-reviewed | 2 files already formatted | 0.010／0.011 |
| diff-check／frozen-paths／github-diff | exit0；冻结三个目录 stat 空；.github 恰一安装行 | 0.007／0.002／0.002 |
| records-check／records-check-corrected | 首轮脚本 SyntaxError exit1；修正后 YAML／append-only／added-only 归因／workflow 检查 exit0 | 0.020／0.062 |
| commit-a-content-identity | 48 个最终 full 被测 runtime Python SHA-256 与 code commit blob 全部相同 | 0.100 |

报告 stem 统一 `reports/fix4-<label>-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-<YYYYMMDDTHHMMSSffffff>.{json,md}`，同 stem 九节中文汇总；失败不覆盖。最终 runtime full 时间 `20261023T200741572668`；原生 E2E `/tmp/r22-pr3-fix4-e2e/runtime-e2e-linux-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-20261023T114420Z.{json,md}`。shards 首轮／绑定 SHA 轮分别在 `reports/fix4-linux-shards/`、`reports/fix4-linux-shards-final/`，原生逐例结果与 skipped 原因完整保留。首轮 source_sha=null 的限制由外层真实 source metadata 明确记录，不能冒充可聚合 CI 证据。

### fix4 发布与范围边界

**最新全范围验证不是全绿。** 额外绑定 SHA 重跑的两处失败位于未修改的 `test_sbtd_probe_links.MaterializeAuthorizationTests`；该实现用 device／inode／ctime_ns 识别替换。独立 OS smoke 证明本机能在删除重建后得到相同 tuple，与失败路径一致，但不声称已修复该身份问题。首轮三个 shards 全绿不抹掉后轮失败；不加 sleep／skip、不弱化断言、不改范围外授权实现，不用重复运行筛选绿色结果。解除这项阻断需要独立授权的 link identity 调查／修复或可靠平台证据，不属于本次 A/B。

**Release Readiness Review: blocked。** A/B 定向与 runtime full／真实 Chromium E2E 通过；最新额外 shard 汇总失败；macOS 待 CI 复跑，13/13 gate 未完成。编排方整理的 Windows 前轮 CI 通过仅属于 run39945077815，不冒充新 SHA 上结果。资源限制、原五秒 reap／两秒 group deadline、取消／超时错误、单 worker 与结果校验保持；不增加生产日志或 fallback。无迁移、数据清理或部署；代码回退会恢复旧 EPERM／缺依赖缺陷，不承诺旧版本可用。

BDD traceable：沿用 `sbtd-runtime/spec/r2.2-native-e2e-scenarios.md` 的原生导出与退出／失败清理场景，中文场景／English keywords；本轮不改 spec／PRD／contracts／schema／golden。Cross-repo context not-needed；API Contract verified（冻结路径空 diff）；EPERM 测试 Mock Strategy 为编排方整理明确授权的 OS seam，real Chromium E2E 为 backend-only／Mock Strategy none。UI／Maestro／浏览器 MCP not-needed；已有 Python Playwright driver 已运行。Final Test Report／Run Summary MD generated；Targeted Rerun A/B passed；Final Full Rerun runtime passed、额外 shards failed；Evidence Source developer-local／Source Revision dirty／Evidence Publication local-only。无 ty／原生 Darwin kernel 检查声明。

### fix4 本地提交与恢复边界

Commit A：`e771f0822dcaafa477e8447b6ea998cbe405de75` — `fix(runtime): treat Darwin EPERM on reaped renderer group as gone; install serve deps on Linux shards (R2.2 PR-3 fix4)`。仅 `sbtd-runtime/browser_renderer.py`、`sbtd-runtime/tests/test_renderer_process_wait.py`、`.github/workflows/validation.yml`；无 workflow expectation 改动。提交后内容身份检查证明最终 runtime full 的 48 个文件与 commit blob 相同；原始证据仍保留真实入口 75c1c93＋dirty，不改称新 SHA 上执行。

Commit B：`docs(task): append CI fix4 blockers, verification and remaining risks (R2.2 PR-3)`，仅本 task，SHA 由最终回复给出，避免自引用。全部显式路径暂存；reports／.omp-r12b-addendum.txt／ai/tasks/codex-verify／.env* 不暂存。task 保持 in-progress／completed_at null，旧 frontmatter 除 updated_at 外逐字段不变、旧行逐字保留。无 push／PR／comment／merge／rebase／amend／force，无其他 worktree／omp 全局配置变更；无自动恢复或发布完成声明。

最终记录检查追加：`records-final` exit0／0.053s、`diff-check-final` exit0／0.005s。37 份本轮 raw 均生成同 stem 九节中文 companion，检查章节顺序与 raw 配对通过；完整清单与逐轮命令在 `reports/fix4-verification-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-20261023T203512.{json,md}`。37 份为命令轮次，不是37个测试；所有失败／跳过原样保留。首轮 shards 合计2387 tests／2324 passed／63 skipped／0 failures；绑定 SHA 的最终轮2387 tests／2322 passed／63 skipped／2 failures，绝不标记全范围 passed。最终记录与 code 分开提交；reports 不暂存。

## R2.2 PR-3 fix5 入口与 Book Gate Plan（编排方整理）

用户 2026-10-23 22:26 +08:00 群内确认 1A 2重跑，Lord 记录。编排方整理：1A 为本轮 glyph gate retarget；2 为 operator 已执行的失败 jobs 诊断重跑，不是 merge gate。strict 延续；授权根 `/workspace/640-skills-r22-pr3`、分支 `feat/v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation`、入口 `771d728441003e9b37ec26b10e067a60036391c7` 已核实，入口工作区干净。沿用第 212 行 PR-3 追加绑定和既有 Markdown／TaskStore 兼容边界，不调用 helper rebind、不宣称自动恢复；历史 frontmatter 除 updated_at 外不改，所有旧行保留。

未完整调用 grill-with-docs：修复范围与验收已明确，无新领域歧义。已逐行核实 `ai/tasks/v2.1.0-rc.2-plan/grill-r1.md:120,209,238` 的 Q4-D／Q9-C／D9，以及 `sbtd-runtime/spec/r2.2-native-e2e-scenarios.md:17,53`：字形门属于受控 renderer；CI 自动化与 Mac 人工视觉证据分开。编排方整理的失败为 run39955043747 attempt1/job120418673815、attempt2/job120468636401：四格式 passed 后下载 HTML glyph assertion 失败，fonts null；本轮不把该诊断重跑当 merge gate，也不声称本地复现了 macOS 字体选择。

| Gate | 客观触发／阶段 | 本轮状态／计划 |
|---|---|---|
| DDD／DDIA | 领域歧义／共享持久模型 | not-needed；未完整 grill，无领域、schema、cache、迁移或所有权变化。 |
| Legacy Change Safety | 既有 E2E 门与失败证据／编辑前 | needs-safety-net；已确认下载 HTML 调用与返回前断言导致 evidence 赋值未完成；补纯字体选择／断言及 HTML record-only 回归。 |
| Refactoring／Release Readiness | 生产代码／部署行为 | not-needed；仅 test driver、tests 与证据边界文字，生产 renderer／字体栈／workflow 不改；发布状态仍 pending CI。 |
| TDD／ponytail／BDD | 既有 gate retarget | 复用 unittest、default_presentation 与 _prepare_document；分别检查 JPEG/PDF；保持原 marker、fonts.ready、Panel、CJK text 断言；场景行不改。 |
| project-validation／可读性 | check | pending；定向、runtime full、golden、真实 Linux renderer smoke、ruff、diff、added-only 归因、YAML／append-only 检查；原生 raw 与同 stem 中文汇总，reports 不暂存。 |

### fix5 状态事件（追加）

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-23T22:39:56+08:00 | in-progress | in-progress | fix5 strict 开工与既有 PR-3 绑定延续（编排方整理）；仅两个本地提交 | Q9-C／Q4-D／D9 与调用链已核实；LSP references 返回 No language server found，源码检索仅一个 caller；macOS pending CI，未达到 13/13。 |

### fix5 实现与独立观察（编排方整理）

`serve.py:431` 对省略 presentation_state 的请求使用 `default_presentation(manifest)`；`export_render.py:145-155` 为 dark／1440px／完整 panel_order。driver 同样调用该函数，将下载的同快照 HTML 分别传给 `_prepare_document(html, "jpeg", presentation)` 与 `_prepare_document(html, "pdf", presentation)`；两种实际生成的格式均检查，不以相似样式省略 PDF。生产 `_capture` 在 `browser_renderer.py:1210` 使用该准备函数。CDP 完整 response（所有 fonts entry 原样，包括 familyName、postScriptName 若有、isCustomFont、glyphCount）逐文档立即放入共享 evidence，全部采集完成后才运行字体／Panel／CJK text 断言，避免 JPEG 断言阻止 PDF 字体采集。每条带 developer-local／ci、platform、not pixel OCR 与断言边界标签；main 的异常处理随后序列化同一 evidence，不覆盖 fonts。

**Separate observation，仅登记不修复：下载 HTML 已有显式 CJK fallback。** `sbtd-runtime/export_render.py:24-28` 先列 `-apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial`，随后明确列 `"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", "Noto Sans CJK JP", sans-serif`。JPEG/PDF 使用 `browser_renderer.py:65-69` 的 Noto Sans CJK SC／JP／TC／KR、PingFang SC、Hiragino Sans GB、Microsoft YaHei、sans-serif，由 `:342` 强制覆盖全部元素；本轮均不修改。存在 fallback 不等于已证明 macOS 下载 HTML 选用了哪种字体，原 CI fonts null 无此证据。

Legacy Change Safety Review: characterized；CI 观察与源码建立问题／保留行为边界，新增纯 helper／record path／异常报告回归。4 cases red 为 3 AttributeError errors＋1 failure（缺 helper），不是本地重现 macOS glyph 选择；实现后定向 10 tests OK／7.923s、exit0／墙钟8.171s。marker 仍恰为 cjk、pingfang、hiragino、yahei、simsun、unicode。ruff check 首轮 exit0；format 首轮 exit1，仅 evidence_source 长行，随后按 formatter 给出的换行最小修正；失败报告保留。BDD 沿用中文场景／English keywords，只在证据边界增加一句，所有 scenario 行原样保持。

### fix5 验证结果、真实字体与复核（编排方整理）

共同环境：Linux 6.12.94+ x64／Python 3.13.5，`python3` 经 PATH 选择既有 `reports/renderer-venv/bin/python3`（Playwright 1.64.0），`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests RUFF_NO_CACHE=true`。系统已有 Noto CJK 字体；未发现可复用 shell，真实 driver 通过 `--install-browser` 下载 pinned Chromium headless shell 156.0.8078.4 到一次性 runtime home，随后自动移除；无全局安装或配置改动。rtk skipped-for-report，原生 subprocess 保存 command、stdout、stderr、exit、时间、真实入口 SHA／worktree／branch 与 48 个 Python 文件 hash；所有结果 developer-local／dirty／local-only，不是 macOS 证据。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest test_runtime_e2e_evidence.FontEvidenceTests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest sbtd-runtime/tests/test_runtime_e2e_evidence.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest discover -s sbtd-runtime/tests
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest sbtd-runtime/tests/test_golden_contracts.py
python3 -B sbtd-runtime/tests/runtime_e2e.py --install-browser --output ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/reports/fix5-native-linux
ruff check sbtd-runtime/tests/runtime_e2e.py sbtd-runtime/tests/test_runtime_e2e_evidence.py
ruff format --check sbtd-runtime/tests/runtime_e2e.py sbtd-runtime/tests/test_runtime_e2e_evidence.py
git diff --check
```

另执行两个无落盘 `python3 -B -c <script>` real Chromium smoke（完整脚本见对应 raw.command）：`native-linux-timeout-diagnostic` 仅将 `http.client.HTTPConnection` timeout 从既有10秒临时改成60秒后调用原 `runtime_e2e.main()`；`native-font-failure-persistence` 在同样诊断环境仅对 required 字形选择传入空候选，故意使原断言失败，真实 CDP response 不改。`records-check` 用 yaml.safe_load 解析 frontmatter，逐行核对原854行除 updated_at 完全不变、strict／in-progress、仅四个允许路径、plan 全文件及所有 scenario 行不变；新增行单独提取后执行禁用归因 grep，0 matches。`commit-content-identity` 核对48个 runtime Python commit blobs 与最终 full 被测 hash 全相同。

| raw label | exit／原生结果 | 墙钟秒 |
|---|---|---|
| font-regression-red | 1；4 tests／3 errors＋1 failure，0.015s；缺待提取 helper，不声称本地 macOS reproduction | 0.273 |
| evidence-green | 0；10 tests OK，7.923s | 8.171 |
| ruff-check／ruff-format | 0／1；check passed，format 首轮长行失败保留 | 0.262／0.065 |
| native-linux | 1；driver 19.586s，HTML／CSV passed；JPEG POST 在既有 HTTP timeout=10 处失败，尚未进入 fonts；诊断重放 worker exit0不改变原失败 | 19.806 |
| runtime-full | 0；425 tests，415 passed／10既有 skipped／0 failures，155.049s | 155.422 |
| golden | 0；61 tests OK，0.324s | 0.482 |
| ruff-final／format-final | 0／0；All checks passed／2 files already formatted | 0.013／0.010 |
| native-linux-timeout-diagnostic | 0；driver 25.179s；真实四格式／13 Panels／PDF文本／3-case suite passed，SIGINT exit0、lock移除、port关闭 | 25.403 |
| native-font-failure-persistence | 外层0；被注入 driver 1／15.503s；原 glyph assertion 失败后，HTML／JPEG／PDF完整 raw CDP response 均在 JSON，未变成 passed | 15.738 |
| diff-check／records-check | 0／0；diff、YAML、append-only、冻结范围通过 | 0.007／0.046 |
| commit-content-identity | 0；48个提交 blob 与最终full被测内容一致 | 0.106 |

**默认 Linux driver 本轮不是全绿。** 原始超时保留，不改 test_serve.py:156 的10秒 deadline、不加 retry／skip，不将诊断脚本的通过写成默认 native E2E 或 CI 通过。JPEG preflight 诊断重放成功只证明该次 worker 可以完成；超时成因未进一步归责，本轮不修复。后续60秒客户端诊断跑通原字体路径，足以证明改动的三文档采集与断言路径，不证明默认 HTTP deadline 可靠性。

以下为 `native-linux-timeout-diagnostic` 的全部 `CSS.getPlatformFontsForNode` fonts entries（Linux local，非 macOS、非 pixel OCR）；完整 response 在每个 `evidence.fonts.<format>.platform_fonts`：

| 文档 | familyName | postScriptName | isCustomFont | glyphCount | 字形断言 |
|---|---|---|---|---|---|
| html | Noto Sans CJK SC | NotoSansCJKsc-Bold | false | 2 | 仅记录、不断言 |
| html | Roboto | Roboto-Regular | false | 1 | 仅记录、不断言 |
| html | DejaVu Sans Mono | DejaVuSansMono-Bold | false | 8 | 仅记录、不断言 |
| jpeg | Noto Sans CJK SC | NotoSansCJKsc-Bold | false | 11 | asserted |
| pdf | Noto Sans CJK SC | NotoSansCJKsc-Bold | false | 11 | asserted |

所有三文档 fonts_ready=loaded、13 Panels 顺序一致、CJK text present；HTML 标签只限定平台字体字形门，原字体就绪／Panel／文本断言仍保留。四个新增精确测试名：

- `FontEvidenceTests.test_renderer_rejects_non_cjk_glyphs_and_unused_cjk_font`
- `FontEvidenceTests.test_renderer_accepts_pingfang_with_heading_glyphs`
- `FontEvidenceTests.test_downloaded_html_records_non_cjk_fonts_without_glyph_assertion`
- `FontEvidenceTests.test_failed_renderer_glyph_gate_preserves_raw_fonts_in_report`

RendererBoundaryReview：correct／0.85；EvidenceRegressionReview：correct／0.90；均只读、未运行 tests／lint／build，无剩余 finding。前者确认审查对象为 uncommitted working tree，原文“committed state”为表述失误；后者撤回两项P3：HTML label 是本轮明确要求的精确文本，旧 spec:17 与基线:53 引用经 raw 行号复核正确。真实 smoke 补足 CDP session 在多次 set_content 后仍可采集的运行证据。Code Readability Review：短纯 helper、集中断言、先采集后断言，未引入依赖／新 renderer 逻辑或过度抽象。

报告前缀为本目录 ignored `reports/fix5-<label>-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-<YYYYMMDDTHHMMSSffffff>.{json,md}`，每份 raw 配同 stem 九节中文汇总。关键时间：red `20261023T224102655178`，green `20261023T224154479721`，full `20261023T224424496059`，golden `20261023T224659922352`；全部失败轮保留。driver 原生 JSON／MD 分别位于 `reports/fix5-native-linux/`（stem末尾 `20261023T144317Z`）、`reports/fix5-native-linux-timeout-diagnostic/`（`20261023T144737Z`）、`reports/fix5-native-font-failure-persistence/`（`20261023T144823Z`）。

BDD traceable（既有 Markdown spec／中文场景＋English keywords；本轮场景零变化）；Cross-repo context not-needed；API Contract verified（冻结路径零修改）；Mock Strategy：纯 helper 合成字体样本、异常门局部注入；实际成功诊断 smoke 无 renderer stub，backend-only＋real Chromium。Final Full Rerun runtime passed、默认 native smoke failed、诊断 smoke passed，三者分别记录。ty 不可用，LSP 无 server，未声称 typecheck；macOS／Windows 原生 CI 与 Mac 人工视觉均未本地执行。未调用 advisor；两位独立只读 reviewer 不执行验证环境操作。

### fix5 本地提交与剩余边界（编排方整理）

Commit A：`d3fe6aad75ec2cf288f39e570072b23de2588236` — `fix(test): run macOS CJK glyph gate on the renderer document; record downloaded HTML fonts only (R2.2 PR-3 fix5)`；仅两个 tests Python 文件与 spec 一句。最终 full 的48个 Python hash 与提交内容一致；这是内容身份重验证，不冒称提交后重跑或 PR-head CI。

Commit B：`docs(task): append fix5 CJK gate retarget, evidence and verification (R2.2 PR-3)`；仅本 task，SHA 最终回复给出以避免自引用。task 继续 in-progress／completed_at null；plan.md:22 untouched；不修改 production renderer、export_render.py、字体栈、workflow、PRD、contracts、schema、golden。仅显式路径暂存，无 reports／.omp-r12b-addendum.txt／ai/tasks/codex-verify／.env*。不 push／PR／comment／merge／rebase／amend／force，不接触其他 worktree／omp全局配置。

**macOS pending CI**：operator 推送后才能取得新 SHA 的原生字体结果，未声明13/13。D9 用户 Mac 真机视觉／字体仍 pending；此前 fix4 全范围 link identity 失败历史不改、不以本轮runtime suite覆盖旧失败。无部署／发布完成声明；本地回退边界是撤回本轮代码提交，会恢复旧下载HTML误用字形门及失败字体证据缺失，不执行任何数据迁移或清理。

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-23T22:51:23+08:00 | in-progress | in-progress | fix5 本地代码与定向／全量验证完成，独立review闭环；默认Linux smoke超时保留，macOS pending CI（编排方整理） | A d3fe6aad75ec2cf288f39e570072b23de2588236；10定向／425full（10skipped）／61golden；真实三文档字体与失败保存已诊断验证；不声明13/13或发布就绪。 |

## R2.2 PR-3 fix6 入口与 Book Gate Plan（编排方整理）

编排方整理：Reviewy 23:24 裁定（2026-10-23 23:24 +08:00，640 room）。用户 2026-10-23 22:26 +08:00 群内确认 1A 2重跑，Lord 记录。strict 延续；授权根 `/workspace/640-skills-r22-pr3`、分支 `feat/v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation`、入口 `b2884260b13b09c56557798d697f76556ceb0da2` 已核实，入口工作区干净。沿用第 212 行 PR-3 追加绑定与既有 Markdown／TaskStore 兼容边界；不调用 helper rebind、不写 active／index、不宣称自动恢复。历史 frontmatter 除 updated_at 外不改，所有旧行逐字保留。

未完整调用 grill-with-docs：编排方整理的修复规则与验收明确，无领域歧义。仅修改 `sbtd-runtime/tests/runtime_e2e.py`、`sbtd-runtime/tests/test_runtime_e2e_evidence.py` 并追加本 task；spec 无需补充，plan 不改。仅两个本地提交，不 push／PR／comment／merge／rebase／amend／force，不接触其他 worktree 或 omp 全局配置。

编排方整理的 CI 证据：run `39974702309` on `b288426`，CI runner `macOS-26.6.2-arm64`，不是用户 Mac 真机；`runtime-e2e-macos` 失败 `AssertionError: no verified CJK font produced heading glyphs`，其余 12 checks passed。`#overview h2` 的完整字体观察如下；本轮不将该观察写成本地 macOS 实测。

| 文档 | familyName | postScriptName | glyphCount | 字形门 |
|---|---|---|---|---|
| html | Menlo | Menlo-Bold | 8 | 仅记录、不断言 |
| html | 蘋方-簡 | PingFangSC-Semibold | 2 | 仅记录、不断言 |
| html | Helvetica Neue | HelveticaNeue-Bold | 1 | 仅记录、不断言 |
| jpeg `_prepare_document` | 蘋方-簡 | PingFangSC-Semibold | 11 | asserted |
| pdf `_prepare_document` | 蘋方-簡 | PingFangSC-Semibold | 11 | asserted |

根因：macOS Chromium 的本地化 familyName「蘋方-簡」不包含现有 ASCII marker；locale-independent postScriptName `PingFangSC-Semibold` 包含 `pingfang`。修复同时检查两个名称（缺失视为空串），大小写不敏感，仍须 glyphCount > 0；原六个 marker、失败消息、JPEG/PDF 准备文档与节点范围保持。不新增中文 marker，不降低断言。

| Gate | 客观触发／阶段 | 本轮状态／计划 |
|---|---|---|
| DDD／DDIA | 领域歧义／共享持久模型 | not-needed；未完整 grill，无领域、schema、cache、迁移或所有权变化。 |
| Legacy Change Safety／TDD | 既有字体 gate bug／编辑前 | needs-safety-net；既有 helper seam 添加本地化 PostScript 名称 red，原四个 FontEvidenceTests 逐字保留；补非 CJK、空列表与零 glyph 负例。 |
| Refactoring／Release Readiness | 生产代码／部署行为 | not-needed；只改测试 driver 与回归测试，不改生产路径或发布配置。 |
| ponytail／可读性 | 最小根因修复／check | 复用现有 marker 与采集顺序；保留 raw response，另列每字体名称、glyphCount 和匹配字段。 |
| project-validation | 编排方整理的验收命令／check | pending；定向 red→green、runtime full、golden、真实字体 smoke、ruff、diff、added-only 归因、YAML／append-only 检查；raw 与同 stem 中文汇总，不暂存 reports。 |
| 独立 review | 迁移／身份／全局配置／安装／跨服务／广泛公共接口或至少三个热点 | not-needed；本轮仅一个测试证据子系统，不触发强制独立复核，不调用 advisor；主会话执行边界与可读性检查。 |

### fix6 状态事件（追加）

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-23T23:26:58+08:00 | in-progress | in-progress | fix6 strict 开工；编排方整理：Reviewy 23:24 裁定 | 分支／入口已核实；CI run39974702309 的本地化 familyName 根因；macOS pending CI after operator push，非真机验收。 |

### fix6 实现、red→green 与边界复核（编排方整理）

Legacy Change Safety Review：characterized。新增 `FontEvidenceTests.test_renderer_accepts_localized_family_with_cjk_postscript_name` 在实现前以「蘋方-簡／PingFangSC-Semibold／11」触发原 `AssertionError: no verified CJK font produced heading glyphs`，1 test／1 failure／0.001s；实现后同一测试 1 passed／0.000s。这是编排方整理的 CI 样本在真实 helper seam 的回归，不是本地复现 macOS 字体选择；根因已明确，不重跑旧 CI 来确认。

`_cjk_name_matches` 复用原 tuple `("cjk", "pingfang", "hiragino", "yahei", "simsun", "unicode")`；`verified_cjk_families` 对 familyName 与 postScriptName（缺失为空串）分别大小写不敏感匹配，保留 `glyphCount > 0` 和原失败消息。`cjk_families` 继续返回可读 familyName 列表。每个 HTML/JPEG/PDF 文档立即保存完整 `platform_fonts` raw response，另存 `font_summary`：familyName、postScriptName、glyphCount、matched_fields。matched_fields 表示名称包含 marker 的字段，不替代正 glyph 要求；全部文档先采集后断言，因此 JPEG gate 失败仍保留 PDF raw／summary。HTML 的 `"assertion": "仅记录、不断言"`、JPEG/PDF `_prepare_document` 和 `#overview h2` 均不变。

新增三个回归：

- `test_renderer_accepts_localized_family_with_cjk_postscript_name`：本地化 familyName 由 postScriptName 命中，11 glyph 通过。
- `test_renderer_rejects_non_cjk_family_and_postscript_names`：Menlo／Menlo-Bold 与 Helvetica Neue／HelveticaNeue-Bold 均有 glyph，仍抛原 AssertionError。
- `test_renderer_rejects_empty_fonts_and_zero_cjk_glyphs`：空列表、CJK family＋非 CJK postScriptName＋0 glyph、本地化 family＋CJK postScriptName＋0 glyph，三个 subcases 均拒绝。

原四个 FontEvidenceTests 逐字保留且均通过：`test_renderer_rejects_non_cjk_glyphs_and_unused_cjk_font`、`test_renderer_accepts_pingfang_with_heading_glyphs`、`test_downloaded_html_records_non_cjk_fonts_without_glyph_assertion`、`test_failed_renderer_glyph_gate_preserves_raw_fonts_in_report`。`git diff b288426 -- sbtd-runtime/tests/test_runtime_e2e_evidence.py` 仅 additions；完整旧文件逐行序列与四方法源字节检查通过。

Code Readability Review：单一短名称 predicate，两个名称明确列出，复用 matcher 避免 marker 漂移；现有返回类型、断言位置与异常语义保留。无生产代码或无关重构。严格独立 review 触发条件本轮不适用（单一测试证据子系统）；未调用 advisor，未宣称独立 review 已执行。LSP references 实际返回 `No language server found for this action`，源码检索确认 helper／record／browser callers；ty 不可用，未声称 typecheck。

### fix6 本地验证与真实 smoke（编排方整理）

共同环境：Linux 6.12.94+ x64／Python 3.13.5；既有 `reports/renderer-venv/bin/python3`。环境变量 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests RUFF_NO_CACHE=true`；rtk skipped-for-report，原生 subprocess 保留 stdout／stderr／exit／时间／worktree／完整 SHA 与48个 runtime Python SHA-256。报告为 developer-local／dirty／local-only，不是 PR-head CI。失败轮保留，全部 raw 配同 stem 九节中文汇总；reports 不暂存。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/reports/renderer-venv/bin/python3 -B -m unittest test_runtime_e2e_evidence.FontEvidenceTests.test_renderer_accepts_localized_family_with_cjk_postscript_name -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/reports/renderer-venv/bin/python3 -B -m unittest sbtd-runtime/tests/test_runtime_e2e_evidence.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/reports/renderer-venv/bin/python3 -B -m unittest discover -s sbtd-runtime/tests
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/reports/renderer-venv/bin/python3 -B -m unittest sbtd-runtime/tests/test_golden_contracts.py
RUFF_NO_CACHE=true ruff check sbtd-runtime/tests/runtime_e2e.py sbtd-runtime/tests/test_runtime_e2e_evidence.py
RUFF_NO_CACHE=true ruff format --check sbtd-runtime/tests/runtime_e2e.py sbtd-runtime/tests/test_runtime_e2e_evidence.py
git diff --check
git diff b288426 -- sbtd-runtime/tests/test_runtime_e2e_evidence.py
```

| raw label | exit／原生结果 | 墙钟秒 |
|---|---|---|
| localized-font-red | 1；1 test／1 failure，0.001s，原 glyph assertion | 0.269 |
| localized-font-green | 0；同一 test passed，0.000s | 0.244 |
| evidence-green | 0；13 tests passed，8.719s，包含原四个字体测试与六个 NativeEvidenceTests | 8.964 |
| ruff-check／ruff-format | 0／0；All checks passed／2 files already formatted | 0.281／0.035 |
| real-font-smoke | 0；真实 Linux Chrome 三文档采集成功＋注入 gate 失败仍保留三文档 raw／summary | 3.262 |
| runtime-full（Final Full Rerun） | 0；428 tests，418 passed／10既有 skipped／0 failures，159.099s | 159.504 |
| golden | 0；61 tests passed，0.390s | 0.574 |
| integrity | 0；tests additions-only／原四方法不变／task旧950行除updated_at不变／YAML／冻结范围／原marker tuple | 0.140 |
| tests-additions-diff／diff-check | 0／0；测试 diff 仅 additions／无 whitespace error | 0.005／0.021 |
| commit-content-identity | 0；48个 runtime Python commit blob 与最终 full 被测 hash 相同 | 0.132 |

真实 smoke 使用系统 Google Chrome `156.0.8078.47`，无下载／全局安装。命令为 venv `python3 -B -c <script>`，完整无落盘脚本保留在 `real-font-smoke` raw.command；临时 HTML fixture 含 overview heading 与 CJK 文本，JPEG/PDF 实际调用 `_prepare_document`，`browser_font_check` 实际启动浏览器并调用 CDP。仅把 `_shell_executable` 解析替换为 `/usr/bin/google-chrome`，不是 pinned shell／完整 serve E2E。成功轮 raw fonts 与 summary 逐项一致；随后只对 required helper 注入空候选，故意触发原失败消息，三文档 raw／summary 与成功轮逐项一致，未把失败 renderer 记录标为 passed。未保存临时脚本，未改 repo deadline、retry 或 renderer。

| 文档 | familyName | postScriptName | glyphCount | matched_fields |
|---|---|---|---|---|
| html | Tinos | Tinos-Bold | 9 | [] |
| html | Noto Sans CJK JP | NotoSansCJKjp-Regular | 2 | familyName、postScriptName |
| jpeg | Noto Sans CJK SC | NotoSansCJKsc-Bold | 11 | familyName、postScriptName |
| pdf | Noto Sans CJK SC | NotoSansCJKsc-Bold | 11 | familyName、postScriptName |

完整报告位置：本目录 `reports/fix6-<label>-feat_v2.1.0-rc.2-r2.2-pr3-e2e-reconciliation-<YYYYMMDDTHHMMSSffffff>.{json,md}`。关键时间 stem：red `20261023T232837373302`、green `20261023T232903499450`、evidence `20261023T232933716224`、smoke `20261023T233026772664`、full `20261023T233037012216`、golden `20261023T233316522452`。单独提取 added lines 后禁用归因 grep 0 matches；marker grep 与 AST 确认原六元 tuple 不变。YAML safe_load 通过，status／mode／completed_at 及全部其他 frontmatter 不改。仅三授权路径发生变更，生产、workflow、PRD、contracts、schema、golden、spec、plan 均 untouched。

BDD skipped：内部测试证据修复，没有产品可见行为或场景变化；Cross-repo context not-needed；API Contract not-needed（未改）；Mock Strategy contract-backed（编排方整理的 CDP 样本），真实 browser smoke 的 executable override 与失败注入单独披露。全量 suite 原生输出仍含既有 renderer stub 提示与10 skipped，不冒称全量 real-browser。Final Test Report／Run Summary MD generated；Targeted Rerun／Final Full Rerun passed，仅限上述本地范围。

### fix6 本地提交与剩余边界（编排方整理）

Commit A：`e4c2318bdbc5e0fbfa8b1db14652af475278504e` — `fix(test): match CJK markers on postScriptName for localized macOS family names (R2.2 PR-3 fix6)`，仅两个 tests Python 文件。已完成48个 runtime Python 内容身份重验证；原始 full 证据仍绑定真实入口 b288426＋dirty，不冒称提交后重跑或新 SHA 的 CI。

Commit B：`docs(task): append fix6 postScriptName matching record and verification (R2.2 PR-3)`，仅本 task，SHA 最终回复给出以避免自引用。显式路径暂存；不暂存 reports／.omp-r12b-addendum.txt／ai/tasks/codex-verify／.env*。task 继续 in-progress／completed_at null；不修改 plan，不 push／PR／comment／merge／rebase／amend／force。

**macOS pending CI after operator push**；CI runner 不等于用户 Mac 真机，D9 人工视觉／字体仍 pending，不声明13/13或部署／发布就绪。fix5 的默认 Linux driver 超时与既有其他失败历史不改，本轮 focused browser smoke 不覆盖这些边界。回退边界是撤回本轮测试代码提交，会恢复只按 familyName 匹配的旧 gate；不涉及生产数据迁移或清理。不调用 TaskStore rebind，不承诺自动恢复。

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-23T23:34:56+08:00 | in-progress | in-progress | fix6 本地代码／red→green／全量验证完成；编排方整理：Reviewy 23:24 裁定 | A e4c2318bdbc5e0fbfa8b1db14652af475278504e；13定向／428full（10skipped）／61golden；真实Linux三文档raw与summary保存验证；macOS pending CI after operator push，非真机验收。 |
| 2026-10-24T09:25:04+08:00 | in-progress | in-progress | PR-3 #164 squash-merge 回填（编排方整理）；R2.2 继续开放。 | PR https://github.com/KunoLu/640-skills/pull/164；merge SHA 253dceccc77fb0b7b929a81ac28e4c53d6968240；head 38b3b56aca559d729487665b822c76b48cf8c1f9；git committer %cI 2026-10-24T00:05:38+08:00（本轮 git show 核实）；GitHub mergedAt 2026-10-24T00:05:38+08:00（2026-10-23T16:05:38Z，编排方整理），两时间相等但分别记录；合并前 CI 13/13 on 38b3b56，run 39980290926（编排方整理；本轮未运行 CI）。 |
| 2026-10-24T09:25:04+08:00 | in-progress | in-progress | 用户 2026-10-23 16:44 群内确认（方案 1），Lord 记录：PR-3 合并后先开 statistics/query 507 DISK_QUOTA_EXCEEDED contract PR，复用 #158（82d42a2）错误体；合并后接小实现 PR，再接 PR-4。此前「待用户决定（contract PR）」已由该决定解决，旧事件原文保留。 | 用户 2026-10-24 09:22 群内确认（开始），Lord 记录；编排方整理：本轮 contract-only，记录 ai/tasks/v2.1.0-rc.2-r2.2-statistics-507-contract/task.md；不改 runtime，不宣称 queryStatistics 507 已实现；本 task 保持 in-progress，plan R2.2 行保持 planned。 |

## R2.2 PR-4 入口核对与进度补写（追加）

编排方整理：本轮 strict，主会话唯一 writer／验证 controller／本地提交者；授权根 `/workspace/640-skills-r22-pr4`（本轮授权 worktree）、分支 `feat/v2.1.0-rc.2-r2.2-pr4-perf-closeout`，入口 HEAD／origin/main `d45cfc8567e57dfe10c397c0143cf01717e1109c`，工作区干净、无 upstream。历史 frontmatter branch 保留，本节记录本轮明确绑定；沿用既有 Markdown 追加与 TaskStore 兼容边界，不调用 helper rebind，不写 active／index／ignore，不声称自动恢复可靠。未完整调用 grill-with-docs：范围、验收与 D9 停止点明确，无新领域决定。

本次补写属于 status-sync PRD §四.1 的入口进度核对，不恢复已停用的例行合并回填规则。plan.md「### R2.2」已含 #162–#167，无缺漏，不重复追加、不改任务表行。下列 SHA／git committer 时间均由本轮 `git log -1 --format='%H %cI %s' <sha>` 核实；GitHub head／mergedAt 为编排方整理，CI／Reviewy 本轮不可考。

| PR | merge SHA | git %cI | GitHub mergedAt（+08:00；Z 原值） | head；对应记录 |
|---|---|---|---|---|
| #165 | 9ceb53021aa5e90d6369eed037f0b05ab719e928 | 2026-10-24T10:10:14+08:00 | 2026-10-24T10:10:14+08:00；2026-10-24T02:10:14Z | 5bb8a564ea165c784d034eb7145def7c8b8793fc；`ai/tasks/v2.1.0-rc.2-r2.2-statistics-507-contract/task.md`，status done（只读核实） |
| #166 | fcd835e397698ab3292d9d7614e1407ff7e0a465 | 2026-10-24T10:53:09+08:00 | 2026-10-24T10:53:09+08:00；2026-10-24T02:53:09Z | 073999fbbcb7087de202227fa538b752495b4595；`ai/tasks/v2.1.0-rc.2-r2.2-statistics-metadata-contract/task.md`，status done（只读核实） |
| #167 | 9ced6680cd838b9a5a2d9602a4939d981321582d | 2026-10-24T11:52:51+08:00 | 2026-10-24T11:52:52+08:00；2026-10-24T03:52:52Z | 95f4e8e86536b0188c13f812711831cf1ec88a4c；`ai/tasks/v2.1.0-rc.2-r2.2-statistics-507-impl/task.md`，status done（只读核实）；两个时间相差 1 秒 |

期间非 R2.2 合并仅作入口事实，不修改其记录：

| PR | 完整 SHA | git %cI |
|---|---|---|
| #168 | 72e2c0602fa358f0a522a71a4e0d81b887643131 | 2026-10-24T14:15:54+08:00 |
| #169 | 6f79e9dc69cd6a7e351e9ca50cf50424b9bbb496 | 2026-10-24T18:33:40+08:00 |
| #170 | 3c49524fec9561e6feacce40638be11ecea60dc7 | 2026-10-24T21:24:18+08:00 |
| #171 | 2e5ddb5f588cf250938bc2802fffceb202e984f0 | 2026-10-24T22:48:03+08:00 |
| #172 | 47523469fff9da00d657cbfa08bc1a1154b3bc57 | 2026-10-25T00:49:36+08:00 |
| #173 | d45cfc8567e57dfe10c397c0143cf01717e1109c | 2026-10-25T02:47:54+08:00 |

#173 head `7231818eed0c9b1728403ec1e2437b145aa09cb8`，mergedAt `2026-10-25T02:47:55+08:00`（`2026-10-24T18:47:55Z`）为编排方整理，与 git committer 相差 1 秒，分别保留。

## R2.2 PR-4 Book Gate Plan（追加）

| Gate | 客观触发／阶段 | 本轮状态 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill／领域歧义，需求前 | not-needed；未完整 grill，无新领域决定。 |
| book-ddia-data-design | 数据／schema／持久化设计前 | not-needed；只测既有真实写入／快照／导出，不改数据机制。 |
| book-legacy-change-safety／book-refactoring-pass | 生产行为／代码编辑前 | not-needed；只新增基准与 smoke 测试，不优化生产代码；若触及生产先停止对应项。 |
| TDD／gherkin-bdd／ponytail | 基准与证据实现前 | ponytail 已加载；复用 EventStore／serve／现有测试 helper，标准库优先；既有产品场景不变，小规模 smoke 验证实际数据与报告，不设性能断言。 |
| 独立 review／Code Readability Review | check | 不启动子代理，主会话自审；不冒充独立审查。单一测试证据子系统，不触发强制独立 review。 |
| project-validation | check | pending；实跑基准、golden、runtime、workflow/task、ruff 与记录约束；原生 JSON＋同 stem 中文摘要，reports ignored。 |
| book-release-readiness | runtime／部署变化，验证后 | not-needed；不改生产／部署，不宣称发布就绪；R2.2 仍受 D9 阻塞。 |

## R2.2 PR-4 模型使用（追加）

| agent/session | provider/model | thinkingLevel | assistant / toolCall | purpose | resolvedModelIsFallback | title-gen |
|---|---|---|---|---|---|---|
| PR-4 ping／01a16f40-e5f7-7673-91ad-07e2c12624ae | openai-codex/gpt-6-astra | high | 1 / 0（编排方整理） | --no-tools，回复 OK | false（编排方整理） | 不可考 |
| PR-4 main／01a16f42-9934-77d9-ae02-de618d2caef2 | openai-codex/gpt-6-astra | high | 未知（落盘时本轮尚未结束），实际计数见群内交付报告 | 唯一 writer／controller；session 文件名只读核实：`~/.omp/logs/640-rc2-r22-pr4/main/session/2026-10-24T18-53-18-004Z_01a16f42-9934-77d9-ae02-de618d2caef2.jsonl` | 不可考 | 不可考 |
| PR-4 main 内部辅助 model_usage／01a16f42-9934-77d9-ae02-de618d2caef2 | typesafe/jev-latest | 不可考（记录无该字段） | 26 次调用（purpose find；不计入 main 93 / 163，也不计入 ping 1 / 0） | omp main session 内部辅助调用；只读复核 `~/.omp/logs/640-rc2-r22-pr4/main/session/2026-10-24T18-53-18-004Z_01a16f42-9934-77d9-ae02-de618d2caef2.jsonl`：type=model_usage 共 26 条，均 purpose find、provider typesafe、model jev-latest、stopReason stop，第 94–168 行，2026-10-25T02:54:55+08:00–02:56:10+08:00 | 不可考（记录无该字段） | 不适用 |

## R2.2 PR-4 初轮证据与实现边界（追加）

真实机器复核：Linux 6.12.94+／x86_64、Python 3.13.5、8 逻辑 CPU、16,779,640,832 字节 RAM（约 15.63 GiB）；授权根位于 ext4／`/dev/vdb`，lsblk 显示 vda／vdb、ROTA=1，无型号。编排方整理称本地虚拟盘；不据此宣称物理 SSD 或 PRD 的 4 CPU／8 GB 参考机。本轮使用已有 `~/.local/venvs/project-validation/bin/python3`，不新增第三方依赖、不安装全局工具。

基准只新增 `sbtd-runtime/tests/runtime_perf.py` 与小规模 `test_runtime_perf_smoke.py`，不修改生产路径。真实批量 `EventStore.append` 每批不超过 100，schema 校验、秘密拒绝、spool fsync、去重及每事件 SQL commit 全部保留；合成输入复用 golden 的合法形状，固定事件 ID／时间／内容，原 golden 文件不改。每完整 100 条含 1 任务、10 个成对步骤、79 次状态事件；报告记录完整事件大小直方图和输入 SHA-256。参考规模不足时不造 100 万／1 万／10 万结果。

1000 事件／10 任务／100 步骤原生报告：`reports/runtime-perf-1000-feat_v2.1.0-rc.2-r2.2-pr4-perf-closeout-20261024T190702573559Z.{json,md}`，总墙钟 57.581s；完整数据写入 49.178s。24h／7d 热查询与冷查询、HTML／CSV 各 n=3；冷查询不同微秒结束时间确保不复用快照，但不清 OS 缓存，既有数据均不在变更边界。原报告审计的 met 仅指延迟：源码实际 replay 全量再排序分页，索引／非全扫描要求 not-met；后续 driver 明列该结构性缺口。CSV 原报告 not-measured 指百万流式目标未测，实际较小规模全量导出有数字；源码完整缓冲，流式要求 not-met。仅记录、不优化。

真实 Playwright MCP／Chrome 156.0.8078.47 另测已启动 serve 页面：1000 原事件加 20 条单次 append 探针，实际 1020 事件；预先真实配对，不计配对时间，当前 24h scope，导航至 13 个核心 Panel，n=3：0.633／0.481／0.369s，p50=0.481s、p95=max=0.633s，当前规模 met。导出 HTML 真实浏览器实测 13 Panels、1440×5736 CSS px、fonts loaded；不是 Mac 人工视觉／字体证据。独立报告 `reports/runtime-perf-ui-feat_v2.1.0-rc.2-r2.2-pr4-perf-closeout-20261024T191106Z.{json,md}`；原 backend 报告不回写。

失败保留：初轮 ruff 有 BLE001／格式差异，收窄捕获并仅格式化新增 Python；随后 lint／format 通过。首次 shell 的 python3 缺 jsonschema，改用上述已有环境后真实 serve 启动并 SIGINT exit 0，不改生产或安装依赖。MCP VM 不提供 dynamic import／require，两个调用在读取票据前失败；改用受控文件上传读取本次合成配对票据，在工具内配对且不输出值，真实浏览器测量成功。无 token／secret 写入报告。

自审发现分页末页可少于 100，新增 smoke 改为 101 事件、2 次分页以覆盖 100＋1；不对耗时设断言。可选 `--renderer-home` 仅复制明确给出的 browsers/，使已有 pinned renderer 的 Mac／Windows 可以用同一驱动复跑；本机 Python 未安装 Playwright，真实 capabilities 返回 unavailable，JPEG／PDF POST 503 已观察，不拿系统 Chrome 或 browser MCP 替代生产 renderer。

较大规模报告：`reports/runtime-perf-1000000-feat_v2.1.0-rc.2-r2.2-pr4-perf-closeout-20261024T191005746525Z.{json,md}` 实际 11500 事件／115 任务／1150 步骤，完整写入 1185.380s、总 1559.593s；`reports/runtime-perf-10000-feat_v2.1.0-rc.2-r2.2-pr4-perf-closeout-20261024T193717099968Z.{json,md}` 实际 10000／100／1000，写入 501.746s、总 768.763s。900s 是批次间检查的软时限，前轮两批分别 320.606s、311.837s，结束超出时限；原因不可考，不能据此宣称 I/O 异常有硬 deadline。没有重复抽样筛选绿色结果，百万规模未完成。

最大档浏览器另测原 11500 条加 20 条写入探针，真实 11520 事件；n=3 为 8.927／8.879／9.315s，p50=8.927s、p95=max=9.315s，目标 3s，not-met。原最大档导出 HTML 实际 13 Panels、1440×7270 CSS px，符合本轮几何基准；不是 JPEG／PDF 或 Mac 视觉证明。报告 `reports/runtime-perf-ui-large-feat_v2.1.0-rc.2-r2.2-pr4-perf-closeout-20261024T195143Z.{json,md}` 保存真实 MCP code／结果；服务 SIGINT exit 0。此前 about:blank 几何观察出现旧页面配对 init script 访问 sessionStorage 的 SecurityError，不影响已读几何数值；较大 UI 使用全新隔离 context，driver 的几何页也改为无该 init script 的新页。

自审更正：初轮报告中「one heavy renderer worker and bounded queue」不能作为已实现结论。`export_store.py` 使用 `ThreadPoolExecutor(max_workers=1)`，提交路径没有显式队列数量上限；并发页面未负载实测，有界队列要求未证明，不能写 met。后续 driver 去掉已实现有界队列的表述，旧报告保留并以本注释限定；不擅改公共准入或契约。10000 档已对六份下载样本扫描本轮真实合成 ticket／Bearer／CSRF 及 ticket URL marker，0 命中，并核对两格式 manifest 的 13 个 Panel IDs；这不是完整隐私安全认证。

测试方法复核：本轮是明确 CLI／真实 EventStore／serve／报告 seam 的 characterization 与 smoke，不声称 red→green TDD。101 事件末页 smoke 与 nearest-rank 边界共 2 tests，复核轮 7.561s、OK。未新增产品行为，不新增 BDD runner；可选 Python Playwright 分支因本机依赖不可用未实跑，独立 MCP 真浏览器证据单列。

依赖与验证边界：首轮 runtime 全量唯一失败为 `test_iana_queries_and_dst_work_without_system_timezone_data` 的 `ModuleNotFoundError: tzdata`，不修改测试或生产去绕过。`sbtd-runtime/requirements-serve.txt:8` 已钉 `tzdata==2026.5`；本轮创建 ignored `reports/pr4-validation-venv`，仅安装已有 serve／onboard requirements，通过 PATH 选择其 python3 后复跑，不引入仓库新依赖、不修改全局环境。原始失败 raw 保留；基准仍属于原测量环境，未冒称在新验证环境重测。golden 的实际数量为 63，不照抄编排方整理的 61 估计。

## R2.2 PR-4 容量校准（追加）

证据：`reports/pr4-capacity-feat_v2.1.0-rc.2-r2.2-pr4-perf-closeout-20261024T200220Z.{json,md}`；命令 `python3 -B -c <raw.command[2]>`，完整标准库脚本在 raw，exit 0。它读取三份具名实测报告，复核全部 18 份可用格式样本的 SHA-256／st_size，保留源报告校验和；这是派生算术复核，不是再次压测。源测量 developer-local Linux，真实 source revision／dirty 不改写。

每格式 n=3，三次落盘字节相同；下表字节均为普通文件 st_size，manifest 单列，不含 audit.db／浏览器／本地报告副本。

| 事件／任务／步骤 | 单个 7d Snapshot B | HTML 产物／manifest B | CSV 产物／manifest B | JPEG／PDF B | 一次查看＋已测两格式 B | 采样临时文件峰值 B |
|---|---|---|---|---|---|---|
| 1000／10／100 | 2,033,130 | 14,336／1,656 | 528,887／1,656 | unavailable／未测 | 2,579,665 | 2,033,130 |
| 10000／100／1000 | 20,312,945 | 18,672／1,659 | 5,172,535／1,661 | unavailable／未测 | 25,507,472 | 20,312,945 |
| 11500／115／1150 | 23,361,080 | 18,672／1,659 | 5,946,475／1,661 | unavailable／未测 | 29,329,547 | 23,361,080 |

完整「一次查看＋四格式导出」为 `S+H+C+J+P`，每格式含其 manifest；J／P 未测，完整总量和完整套数均 **not-measured**，不填 0。以下只是 HTML／CSV 子集容量：`B=S+H+C`，`floor(2,000,000,000/B)` 为静态可容纳部分套数；严格低于 80% 的套数为 `floor((1,600,000,000-1)/B)`，首次达到预警为 `ceil(1,600,000,000/B)`。部分套数也是完整四格式套数的上界，不是完整容量承诺；准入只检查当前 U，不能据此保证在途写入不越限。

| 事件 | 2GB 部分套数 | 严格低于 80% 的部分套数 | 首次达到预警的部分套数 | 24 快照＋4 组 HTML/CSV B |
|---|---|---|---|---|
| 1000 | 775 | 620 | 621 | 50,981,260 |
| 10000 | 78 | 62 | 63 | 508,288,788 |
| 11500 | 68 | 54 | 55 | 584,539,788 |

合理使用假设明确为：24h 内 24 个不同快照＋4 次四格式导出，大小取对应已测档；完整占用 `T=24S+4(H+C+J+P)`。最大档已测部分 584,539,788 B，距 80% 还有 1,015,460,212 B；只有四次 JPEG/PDF 及其 manifest、额外在途占用合计在此余量内，才可说这一完整假设成立。这个条件不是 JPEG/PDF 实测结果。24h TTL 在启动／新建时清扫，不是后台准点释放保证。

结论：**保持默认 2,000,000,000，不改代码**；已测 HTML／CSV 子集负载有余量，没有足够证据建议新默认值，但完整四格式、百万规模和 Mac 实机容量尚不能宣布充足。JPEG/PDF 受字体／平台影响，Mac 实机字节数未测；本机生产 renderer 缺 Playwright，真实 capabilities unavailable／POST 503。默认值修改、契约／PRD／schema 或最大支持规模冻结均未做：需用户群内确认后另行处理，原因是缺完整规模与原生平台证据。ADR 可选注记未追加，避免重复已有决定；install-and-use 保留原句并追加结果指引。

资源采样边界：三个规模 serve VmHWM 分别为 111,259,648／724,287,488／816,705,536 B；snapshots＋exports 总峰值下界为 11,023,197／110,560,617／127,104,873 B，20ms 临时文件峰值见表。RSS 是 serve 进程累计峰值，不是 CSV 单作业增量或 renderer 进程树峰值；目录采样可能漏掉短暂峰值，不能宣称平台资源上限已验证。

## R2.2 PR-4 最终性能结果与覆盖映射（追加）

证据来源全部 **developer-local Linux**；机器不是 PRD 参考机，也不是 macOS／Windows 真机。每份 JSON 带实际 source revision／dirty、命令、数据量、事件大小直方图、源文件 hash 与未验证项；中文摘要同 stem，样本在对应 `-artifacts/`。性能数据不重新标成最终提交或 CI 的结果，后续文字／可选浏览器分支修订不改写原始测量。

### 基准命令与实际规模

以下实际命令使用已有 `~/.local/venvs/project-validation/bin/python3`；`R` 为本 task 的 ignored `reports/`，不是 shell 全局变量修改。

```sh
python3 -B sbtd-runtime/tests/runtime_perf.py --events 1000 --samples 3 --seed-seconds 120 --output ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/reports --keep-home
python3 -B sbtd-runtime/tests/runtime_perf.py --events 1000000 --samples 3 --seed-seconds 900 --output ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/reports --keep-home
python3 -B sbtd-runtime/tests/runtime_perf.py --events 10000 --samples 3 --seed-seconds 900 --output ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/reports
```

| 请求规模 | 实际事件／任务／步骤 | 实际 CSV 数据行（不含 header） | 生成／总墙钟秒 |
|---|---|---|---|
| 1000 | 1000／10／100 | 1158：event1000＋task10＋step100＋metadata17＋metric31 | 49.178／57.581 |
| 1000000 | 11500／115／1150 | 12813：event11500＋task115＋step1150＋metadata17＋metric31 | 1185.380／1559.593 |
| 10000 | 10000／100／1000 | 11148：event10000＋task100＋step1000＋metadata17＋metric31 | 501.746／768.763 |

三档基准累计 2385.937s，约 39.766 分钟，含真实写入、查询与导出，不含开发／验证。百万参考规模 **not-measured**；没有外推吞吐、容量或性能代替实测。写入保留完整校验／fsync／去重路径，没有 SQL 直灌、猴子补丁或校验绕过。24h／7d 查询含 HTTP、磁盘读取和快照处理；审计为公开库面真实 replay→list_events→paginate，不冒称不存在的 HTTP audit 测试。

### 数字与 PRD §14.1 对比

每格为 **p50／p95／max 秒**；nearest-rank。写入 n=20，其余已测 API／导出／审计 n=3；小样本不代表稳定统计分布。met／not-met 仅对本机实际规模与测量面，不等于参考机或 AC-62 验收。

| 项目／目标 | 1000 事件 | 10000 事件 | 11500 事件 | 结论 |
|---|---|---|---|---|
| 24h 冷查询 ≤3s | 0.125／0.146／0.146 | 1.933／2.078／2.078 | 2.032／2.341／2.341 | 三档 met；冷定义为不同 scope 无快照复用，OS cache 未清 |
| 24h 热查询 ≤1s | 0.088／0.105／0.105 | 1.278／1.393／1.393 | 1.470／1.489／1.489 | 仅1000档 met，其余 not-met |
| 7d 冷查询 ≤3s | 0.238／0.246／0.246 | 2.850／3.141／3.141 | 3.409／4.092／4.092 | 仅1000档 met，其余 not-met |
| 7d 热查询 ≤1s | 0.096／0.101／0.101 | 1.429／1.432／1.432 | 3.554／5.994／5.994 | 仅1000档 met，其余 not-met |
| 审计100行 ≤0.5s | 0.012／0.020／0.020 | 0.106／0.117／0.117 | 0.134／0.145／0.145 | 延迟 met；全表 replay／排序，索引／非全扫描要求 not-met |
| HTML ≤5s | 0.647／0.671／0.671 | 39.399／39.790／39.790 | 54.957／59.619／59.619 | 仅1000档 met，其余 not-met |
| CSV 百万行流式 ≤60s | 0.999／1.016／1.016 | 41.791／41.829／41.829 | 57.113／58.034／58.034 | 当前规模耗时≤60s；百万目标 not-measured，流式要求 not-met |
| 单事件 append ≤0.020s | 0.051／0.075／0.077 | 0.049／0.058／0.067 | 0.049／0.055／0.056 | 三档 not-met；含校验／fsync／commit，不含事件构造或完整宿主 SDK |

| 其余目标 | 样本／结果 | 结论与边界 |
|---|---|---|
| UI 首次可用 ≤3s | 1020事件 n=3，0.481／0.633／0.633s；11520事件 n=3，8.927／9.315／9.315s | 前者 met，后者 not-met；真实 Playwright MCP／Chrome156.0.8078.47，预配对后导航至13个核心Panel，当前24h；非CLI回归／非Mac人工视觉 |
| 导出基准13 Panels／1440px／≤12000px高 | 1000档 HTML 1440×5736，11500档1440×7270，13 Panels／fonts loaded | 两份已测 HTML 几何 met；不是 JPEG/PDF 字体或最大长图规模验收 |
| JPEG／PDF ≤20s | n=0，p50／p95／max 未测 | not-measured；本机生产 renderer 无 Playwright，真实 capabilities unavailable／POST503；不拿 Chrome MCP 代替 |
| 采集到可见 ≤30s、实际延迟展示 | n=0 | not-measured；按代码30秒轮询，未实测端到端延迟／展示／不闪屏 |
| 并发页面／单重型作业／有界排队 | n=0 | not-measured；代码单 worker；无显式队列数量上限，不证明有界排队 |
| 内存／像素／时间／临时盘上限的平台验证 | 仅记录 serve VmHWM、目录／temp采样下界 | not-measured；资源观察不是限制／取消／故障验证，未证明完整进程树峰值 |
| 本地采集 I/O 异常不得无限等待 | 未注入I/O异常；生成批次曾超过300s | not-measured；软时限不承诺硬中断，原因不可考，不修性能 |

### AC／目标覆盖

| AC／规范 | 本轮证据 | 状态 |
|---|---|---|
| AC-62／§14.1／§18 | 三档原生 JSON＋中文摘要、真实 serve、两档浏览器观察 | developer-local 部分覆盖；参考规模和原生 macOS／Windows 性能未完成 |
| AC-33／AC-62／D9 | 仅保留原历史 CI 事实；本轮无 GitHub 查询／新 CI | 用户 Mac 人工视觉／字体 pending，不用 Linux／CI 替代 |
| AC-51／D14／AC-45 | HTML／CSV可用样本摘要／大小、数据族行数、10000档两格式13个Panel IDs | 本轮仅测量侧核对，未重做四格式人工视觉；既有对账 tests 随 full suite 执行，原 renderer stub 边界保留 |
| D15／§18.3 敏感数据证据 | 10000档六份下载样本，真实本次合成认证值及 ticket URL marker 扫描0命中 | 限定扫描，不新增完整安全认证或宿主真实数据证据 |
| ADR0003／24h TTL／共享2GB／80% | 三档真实 st_size、上节容量公式与假设 | 保持默认；仅已测子集有余量，完整四格式 not-measured |
| PRD 最大长图／CSV规模冻结 | 本机仅11500事件，JPEG/PDF不可用 | 未做：需用户群内确认后另行处理；不得修改 PRD／schema／默认值 |

## R2.2 PR-4 最终本地验证（追加）

正式汇总 `reports/pr4-verification-feat_v2.1.0-rc.2-r2.2-pr4-perf-closeout-20261024T200627Z.{json,md}` 关联截至汇总时35组原始报告的路径与SHA-256；每组九节中文摘要／raw同stem，失败保留。之后的提交前／提交后检查继续单独保存，不覆盖旧报告。两个本次 `--keep-home` 合成目录已在 serve exit0、锁移除后删除；保留样本、public manifest、原始报告和本地验证venv，不清理任何其他数据。

环境区分：基准／首轮检查使用已有 `~/.local/venvs/project-validation/bin/python3`；tzdata 对齐后的定向／子集／runtime最终全量／golden复跑使用 `reports/pr4-validation-venv/bin/python3`（PATH 选择）。共同环境为 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests`，ruff另加 `RUFF_NO_CACHE=true`。两者均Python3.13.5；不把更换验证环境称为重新性能实测。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest sbtd-runtime/tests/test_golden_contracts.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest discover -s sbtd-runtime/tests
python3 -B -m unittest tests.test_sbtd_task_document tests.test_sbtd_task_legacy_events_notice tests.test_sbtd_task_recovery tests.test_sbtd_task_routing tests.test_sbtd_task_schema tests.test_sbtd_task_state tests.test_sbtd_task_status_sync tests.test_sbtd_task_sync_git
~/.local/venvs/project-validation/bin/ruff check sbtd-runtime/tests/runtime_perf.py sbtd-runtime/tests/test_runtime_perf_smoke.py
~/.local/venvs/project-validation/bin/ruff format --check sbtd-runtime/tests/runtime_perf.py sbtd-runtime/tests/test_runtime_perf_smoke.py
git diff --check d45cfc8..HEAD
git diff d45cfc8 --stat -- sbtd-runtime/contracts docs/prd sbtd-runtime/golden
python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/task.md
```

| 轮次／raw label | 实际结果 | 原生／墙钟秒 |
|---|---|---|
| golden-final | 63 tests OK | 0.365／0.478 |
| runtime-full-final（首轮失败保留） | 433 tests，422 passed／1 failure／10 skipped；缺tzdata | 156.493／156.899 |
| workflow-task-final | 135 tests OK | 54.154／54.440 |
| timezone-targeted | 失败用例1 test OK | 0.111／0.219 |
| query-perf-subset | 27 tests OK | 7.461／7.622 |
| runtime-full-environment-aligned（最终全量） | 433 tests，423 passed／10 skipped／0 failures | 160.464／160.876 |
| golden-environment-aligned | 63 tests OK | 0.354／0.475 |
| ruff-final／format-final | All checks passed／2 files already formatted | 墙钟0.024／0.009 |
| records-capacity-staged | parse、yaml.safe_load、历史逐行保留、删事件0、新增行限制0、plan不变、四文件白名单、冻结目录空 | 墙钟1.143，exit0 |
| task-parse-pre-final | in-progress False 50 None（最终收口事件追加前） | 墙钟1.323，exit0 |
| diff-check-pre-final／protected-paths-pre-final | exit0／受保护三个目录stat空 | 墙钟0.006／0.002 |

上述 raw 文件命名 `reports/pr4-<label>-feat_v2.1.0-rc.2-r2.2-pr4-perf-closeout-<timestamp>.{json,md}`；最终 full timestamp 为 `20261025T035659804021`，原始失败为 `20261025T035233719896`，workflow为 `20261025T035510631388`。50个当前 runtime Python文件 SHA-256 与最终full raw.hashes完全相同，后续只改记录／说明；这是内容身份核对，不冒称提交后新CI。

Gate结论：DDD／DDIA／legacy／refactoring／release的生产变更触发条件均未发生，维持 not-needed；无完整grill。Ponytail／Code Readability由主会话自审：复用真实EventStore、ServeProcess和标准库，未新增依赖或生产抽象；末页、未知值、失败保留、认证值不落报告、峰值边界已复核。独立review一栏为「不启动子代理，主会话自审」，未冒称独立审查。project-validation在上述Linux范围passed；BDD skipped（内部测量，无产品行为变化）；Cross-repo context not-needed；API Contract verified（零变更）；真实基准Mock Strategy none，普通suite既有stub如实保留。未运行typecheck（ty不可用）、未部署／发布。

## R2.2 PR-4 完成项与阻塞项（追加）

已本地完成：入口 #165–#167 进度补写、strict／D9决定记录、跨平台可复跑基准及极小smoke、三档真实写入与查询／HTML／CSV／审计／append测量、两档真实浏览器观察、资源采样与有限容量校准、既有默认值保持、可用样本／manifest／双报告、指定本地检查与失败保留、四文件范围／append-only约束核验。没有优化生产性能、修改契约、引入新依赖或操作远端。

| pending 项 | 精确原因／停止边界 |
|---|---|
| D9：AC-33／AC-62 用户 Mac 人工视觉／字体确认——pending | 原因：只能由用户 Mac 真机产出，本会话无法产出，按用户 2026-10-24 22:48 群内确认（D9 等 Mac 证据时停），Lord 记录 |
| macOS 实机性能——pending | 本机仅Linux VM，不能生成Mac原生版本／硬件／性能报告；等用户Mac证据，可用同一脚本复跑 |
| Mac 上 JPEG／PDF 字节数、字体／长页／分页视觉——pending | 只能在Mac实际renderer／字体下取得；本机JPEG/PDF unavailable，Linux HTML几何不能替代 |
| 原生 Windows 性能——pending | 无Windows真机，本轮无CI运行授权／远端操作；后续只能以真实CI runner报告标注来源，不能冒充真机 |
| 百万事件／1万任务／10万步骤及百万CSV——pending | 本轮完整写入成本与软时限只取得最大11500事件；未外推，CSV实现非流式，性能优化不在本PR |
| 完整四格式容量／平台资源上限／最大长图CSV规模——pending | JPEG/PDF缺实测与平台证据；缺失值未当0，未修改默认值／PRD／schema；需要规则变更的项另行处理 |
| R2.2 收尾——pending | D9未满足，不执行任务完成状态、completed_at或plan R2.2行变更；status保持in-progress、completed_at保持null，plan原行逐字不变 |

本地提交：`b473df9b87616633eb7742f55d2b4418c061beba`（Commit1记录）、`4f32bcd5ff02bb47c44e058ea9a73067269fe1c0`（基准／smoke／使用说明／同步进度）、`ee818c45c5cbe4722bf95fd6eac8e238cacd7cbb`（容量结论与说明）；最终commit只改本task，SHA由交付回复提供，避免自引用。恢复边界为本授权worktree的本地提交；reports／本地venv未入库，不承诺自动恢复或异机可得。主会话唯一writer与git提交者，无task／subagent／advisor、gh、push、PR、merge、rebase、amend、force、全局配置修改或其他worktree操作。

最终收口候选复核（2026-10-25T04:09:51+08:00，写入者：PR-4 main）：`records-final-candidate` exit0／1.090s；`task-parse-final-candidate` exit0／1.094s，输出 **in-progress False 52 None**。yaml.safe_load通过；原事件删除0、历史行仅updated_at变更、五项新增措辞限制及HOME绝对路径限制0命中；冻结三个目录stat空、plan逐字不变、diff --check通过。最终commit之后仍按编排方整理的要求复跑记录／parse／diff检查，结果由交付回复及对应新raw报告给出，不预写未执行结果。

最终状态：PR-4 可在无 Mac 证据下完成的部分已本地完成；R2.2 保持 in-progress，等待用户 Mac 证据。
