---
schema_version: 1
id: v2.1.0-rc.2-r2.0b-filters-detail
workflow_mode: strict
mode_source: user
mode_note: Lead 本次明确指派 strict 模式 SBTD 任务；范围严格等于 plan.md R2.0b 行＋PRD §12.5／§12.6／§12.4 data-quality＋D12（grill Q6b-A）。硬边界：不得变更 contracts/openapi.yaml、contracts/panel-manifest.json、panel-manifest.schema.json、ADR 0002 决策或任何其他契约；不实现 R2.0c 快照落盘、R2.1a/b 导出格式、R2.2 E2E 证据；不改 PRD 正文；契约变更不可避时停下并出 CONTRACT-CHANGE-NEEDED 报告。显式 git add 路径；不纳入 .omp-r12b-addendum.txt 与 ai/tasks/codex-verify/；不 push、不开 PR。plan.md R2.0b 行在本 PR 合并前不标 done。
status: "done"
blocked_reason: null
branch: feat/v2.1.0-rc.2-r2.0b-filters-detail
created_at: '2026-10-19T23:07:33+08:00'
updated_at: '2026-10-20T11:05:30+08:00'
completed_at: '2026-10-20T03:14:10+08:00'
---

R2.0b：筛选、数据质量、页内详情。分支 `feat/v2.1.0-rc.2-r2.0b-filters-detail` 基于 main `1415134`（PR #145 squash-merge 产物）。模型记录纠正：requested astra; actual k3/grok per session logs（用户 2026-10-20 指令提供）。

## 事实源（已通读）

- `ai/tasks/v2.1.0-rc.2-plan/plan.md`（R2.0b 行）与 `grill-r1.md`（D12＝Q6b-A：30s 轮询自动整份替换、保留上一份视图并标注「正在更新」、常显水位时间；AC-52 保活语义：导出作业固定 snapshot_id 并持引用直到完成／取消）
- `docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md` §12.3–12.6、AC-38/39/40/52
- `sbtd-runtime/dashboard/src/*`（R2.0a 骨架：App／PanelCard／api／registry／reportDocument／manifest）
- `sbtd-runtime/serve.py`（statistics/query 每次重放真实事件库；`/api/v1/report-snapshots/{id}` 与 `/dataset` cursor 分页）
- `sbtd-runtime/stats_query.py`（QueryScope：range.from/to/timezone、filters 六维 project_ids/actor_ids/host_kinds/workflow_modes/component_ids/evidence_levels；非法 range 400 不静默默认）
- `sbtd-runtime/report_snapshot.py`（Snapshot.public_view 携带 quality_summary／dataset_manifest／unknown_time_event_ids／warnings；dataset_page cursor 语义）
- `ai/tasks/v2.1.0-rc.2-r2.0a-serve/task.md`（任务记录与验证惯例）

## 范围（等于 plan.md R2.0b＋指派验收，不扩项）

首个 commit 回填 R2.0a closeout：PR #145／merge SHA `1415134817015580067274b843cc73bcc8e37441`／2026-10-19T22:54:44+08:00 入 plan.md R2.0a 行与 r2.0a-serve task.md 状态事件（#144／`8178b26…`／2026-10-19T22:27:23+08:00 保持准确），plan.md R2.0b 行记 in_progress 与本分支、implement 模型。

1. 应用筛选后全页 Panel 与页内详情共用同一 `snapshot_id`（§12.5，AC-38），不混合新旧数据。
2. data-quality Panel 如实声明覆盖／缺口／未关联，永不以 0 或绿灯冒充（AC-39）。
3. 自动刷新不影响在途导出（AC-52）：导出 UI 属 R2.1a，本任务实现 snapshot-pin／refresh 语义（导出作业创建时固定 snapshot_id；UI 轮询刷新只替换「当前视图」引用，从不动 pin），并以单测证明 pin 跨轮询刷新不变；文档化 R2.1a 如何凭 pin 取数使 AC-52 可验收。
4. 时间范围控件：OMP 式预置 1h/24h/7d/30d/90d/All＋自定义（from/to/timezone）；默认 24h；记忆上次 preset 但每次查询重新解析相对窗口 anchor（§12.5）；无效范围明确报错，绝不静默回退 24h。
5. 工具栏顺序：可选刷新／主题 → 时间范围 → 导出占位（禁用 stub 指向 R2.1a，不实现四格式）。
6. QueryScope 已有维度筛选（project/host/mode 等六维）与时间共同生效；显示完整当前范围摘要。
7. 点击任务／行在同页展开页内详情（task-audit-detail 式）：步骤时间线／事件预览，标「展示 N 条／范围内总 M 条」（§12.6）；图表点击默认同页展开明细。
8. Panel 查询错误显示 error／retry，永不显示假 0（§12.5）。
9. 重建 dashboard 静态产物；保持 artifact budget／BYTE_IDENTICAL CI 约定；体积变化仅以实测数字更新基线。

## 非目标

R2.0c 落盘快照、R2.1a/b 导出格式实现、R2.2 E2E／安全／性能证据；contracts／ADR 0002 决策／PRD 正文修改；push 与开 PR；「筛选此项」交互（本期只做图表点击展开明细，不实现筛选此项）。

## 实现记录

全部变更在前端（`sbtd-runtime/dashboard/`）与 CI；`serve.py`、`stats_query.py`、`report_snapshot.py` 与全部契约文件零改动——QueryScope 六维筛选、快照／dataset 端点、quality_summary／dataset_manifest 均复用 R1/R2.0a 既有真实接口。

### 模块

- `src/timeRange.ts`：预置 1h/24h/7d/30d/90d/All（All＝from 1970 纪元，如实声明）＋自定义 from/to/timezone；`localStorage` 记忆上次选择但相对窗口每次查询重新对 `now` 解析 anchor（§12.5）；`validateCustomRange` 对无法解析、from≥to、非法 IANA 时区、完全未来的范围抛 `TimeRangeError`，全文件无任何 24h 回退路径（§12.5「不能 silently 回退 24h」由构造保证——错误路径不返回任何 range）。
- `src/filters.ts`：六维筛选（project_ids/actor_ids/host_kinds/workflow_modes/component_ids/evidence_levels，与 `stats_query.FILTER_KEYS` 一一对应）；选项从当前快照真实 dataset 行去重派生，不硬编码；`summarizeSnapshotScope` 用快照的 effective_from/to、规范化 filters、task_granularity 写出完整范围摘要（§12.5）。
- `src/pageModel.ts`：页面状态机。`ReadyView` 为不可分原子单元（values＋Snapshot＋rows 同一次 roundtrip、同一 snapshot_id）；`beginLoad` 保留上一份已完成视图并标 updating（D12）；`applySuccess` 整份原子替换；`applyFailure` 保留旧视图并记录 error 供重试；`retainExpansions` 在整份替换后只保留新快照中仍存在的展开项（不混合新旧，§12.5）。
- `src/snapshotPin.ts`：AC-52 导出 pin 语义。`PinRegistry` 与 pageModel 完全无引用关系；导出作业（R2.1a）创建时 `pin(snapshot_id)` 持引用直到完成／取消 `release`；轮询整份替换只换 page model 的当前视图，结构上无法触碰 pin。R2.1a 凭 pin 的 snapshot_id 取 ReportDocument／dataset，使「导出期间新数据不影响当前文件」可验收。
- `src/api.ts`：新增 `fetchSnapshotDatasetPage`／`fetchAllSnapshotRows`（cursor 遍历，每页校验回包 snapshot_id 等于所求——不等即报错，绝不拼接；默认上限 100 页，触及上限置 `truncated` 由 UI 如实标注）。
- `src/PanelCard.tsx`：抽出 `PanelFrame`（唯一面板框），`PanelCard` 增加可选 inline detail 展开（header「明细／收起」toggle，aria-expanded，满足 §12.3 键盘可达——「图表点击展开明细」落地为显式可聚焦 toggle）。
- `src/panels.tsx`：`DataQualityPanel`（AC-39：manifest 实测行数覆盖表＋unknown_time_event_ids＋quality_summary＋warnings＋来源水位＋watermark_seq，缺字段显示 unknown，0 只出现为实测 0）；`TaskAuditDetailPanel`（任务摘要 Top 20「展示 N／范围内总 M」M 取自快照 dataset manifest；点击任务行同页内联展开步骤时间线（步骤/尝试/开始/耗时/状态）与事件预览（最新 50 条，展示 N／该任务范围内 M））；`PanelFamilyDetail`＋`PANEL_ROW_FAMILIES`（图表/表格面板的同页明细预览，家族映射为纯呈现元数据，Panel 身份仍由 manifest 唯一拥有）。
- `src/App.tsx`：工具栏顺序 刷新/主题 → 时间范围（6 预置＋自定义）→ 导出占位（四格式 disabled，title 指向 R2.1a 与 AC-52 pin 语义）；筛选栏＋chips（点 chip 移除即重新查询）；常显水位行（as_of＋snapshot_id＋watermark_seq）与「正在更新」徽标；范围摘要行；刷新失败横幅保留旧视图＋重试；30s `setInterval` 轮询经 ref 取最新 selection/filters，不重叠不重置。
- `app.css`：新增控件与详情样式（沿用 tokens）。

### 测试（node --test，零新增运行时依赖）

`src/*.test.ts` 22 例：timeRange（预置窗口精确宽度、anchor 重解析、All 纪元、五类非法自定义全部抛错无回退、buildScope、记忆往返、摘要文案）；pageModel（beginLoad 保留旧视图、applySuccess 原子替换、applyFailure 保留＋记录、expansion 保留规则、模型结构上无 pin 引用）；snapshotPin（pin 解析、**AC-52 证明：pin 跨两次轮询整份替换后仍解析为原 snapshot_id**、release 语义）；filters（选项去重排序、cleanFilters、完整范围摘要含筛选与粒度）。测试经 Node 22.20 内建 runner 跑 TS（type stripping），仅新增 devDependency `@types/node@22.20.5`（精确钉版），npm audit 0。曾尝试 vitest：≤4.1.10 全部带 tinypool critical／mocker moderate 公告，唯一修复 5.0.5 为新 major——放弃，选零依赖方案。

### CI 与产物

- `.github/workflows/validation.yml` dashboard-artifacts job 新增 `npm test` 步骤（npm ci 之后、audit 之前）。
- 产物重建：两次连续 `npm run build` sha256 逐字节一致；`check_artifacts.py` → 3 files, 260,361 bytes（预算 524,288）；最大单文件 `assets/index-BJl0dHtS.js` 252,458（预算 409,600）；`artifact-budget.json` 基线按实测数字更新（241,853→260,361；236,927→252,458），其余字段不动。

## 验证证据（全部实际执行，本机 Linux，2026-10-19/20）

- **前端单测**：`cd sbtd-runtime/dashboard && npm test`（node --test src/*.test.ts）→ 22 pass / 0 fail。Grok closeout relaunch（2026-10-20，`xai-oauth/grok-4.7:high`）复跑同结果。
- **Python 回归**：`PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py'` → Ran 242 tests in 18.564s OK（本任务未改 Python，确认无回归）。Grok closeout relaunch 复跑同结果。
- **类型与构建**：`npx tsc --noEmit` 过；`npm run build` 过；连续两次构建 `find static -type f | sort | xargs sha256sum` diff 为空 → BYTE_IDENTICAL_OK。
- **体积**：`python3 check_artifacts.py` → OK: 3 files, 260,361 bytes ≤ 524,288。
- **npm audit**：`npm audit --audit-level=high` → found 0 vulnerabilities。
- **真实冒烟（真 serve＋golden 种子事件 61 accepted／2 duplicate／1 conflict，Playwright 驱动浏览器）**：
  - 配对 → 默认 24h 加载；工具栏顺序 刷新来源/主题 → 时间范围（1h/24h/7d/30d/90d/all/自定义，24h pressed）→ 导出四格式 disabled。
  - **单一 snapshot_id（验收 1／AC-38）**：网络面板核对每个 roundtrip 的 `POST statistics/query` 响应 snapshot_id＝随后 `GET report-snapshots/{id}`＝`GET …/dataset` 完全一致（snap_61be…、snap_4186…、snap_279d…、snap_b130…、snap_d319… 各轮均一致）；Panel 与页内详情同渲染一视图。
  - **D12 轮询**：无用户操作时网络面板出现第二轮完整 roundtrip（30s poll 自动整份替换为新 snapshot_id）；替换期间视图不清空（pageModel 语义单测覆盖「正在更新」保留旧视图）。
    - 编排方整理：第 80 行记录的是 R2.0b 当时一次浏览器实测，原文保留。预置范围现按固定 300 秒查询桶（UTC epoch 对齐）向上取整，All 同规则，自定义不取整。30 秒轮询仍执行整份查询与视图替换，但不保证每轮得到不同 snapshot_id。同一查询哈希与数据指纹、未过期且有效的快照可复用；同桶新增事件改变数据指纹时生成新快照，已固定的旧快照不变。本更正的运行验证以本契约任务实施后的实际记录为准，不沿用 R2.0b 的旧结果证明新行为。
    - 实施验证记录（`date -Iseconds`：`2026-10-27T19:39:56+08:00`）：契约分支 `feat/v2.1.0-rc.2-contract-bucket-ceiling`，基准 `c126609d0c0cff3303cf293707284698cebecdc1`＋当前未提交修改；dashboard 的 `node --test src/timeRange.test.ts src/snapshotPin.test.ts` 为 12 pass／0 fail，根目录 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_report_snapshot -v` 为 13 项 OK，退出码均为 0（两命令的 TMPDIR 均指向仓库相对路径 `.tmp-omp`；此处为第 1 轮实际路径的相对表示，非本轮重跑）。测试覆盖同桶 scope 稳定、跨桶推进、All、自定义、pin，以及真实桶内／迟到事件生成新快照、旧 rows／digest／as_of／expires_at 不变。第 2 轮补充（`date -Iseconds`：`2026-10-27T19:53:48+08:00`）：编排方已执行 `npm ci --ignore-scripts`（退出码 0、锁文件未变）；本轮 Node v22.20.0，两次 `npm run build -- --configLoader native` 退出码均为 0，static 字节一致（SHA-256 清单 diff 为空、退出码 0），详细命令、临时目录隔离及变化文件见契约 task H 节。未进行本轮 CI、浏览器轮询、部署或合并验证，未提交；原 done／completed_at／历史事件保持不变。
  - **页内详情（验收 7）**：task-audit-detail 任务摘要「展示 5 条／范围内总 5 条」；点击 task_leaf 同页展开步骤时间线（step_a 尝试 1 succeeded／尝试 2 failed／step_b blocked／step_c unknown，含重试与阻塞真实形状）与事件预览（最新 50 条「展示 50 条／该任务范围内 50 条」）；activity-trend 点「明细」同页展开事件预览（该筛选窗口实测 0 条如实显示「展示 0 条／范围内总 0 条」）。
  - **筛选＋摘要（验收 6）**：宿主多选选 omp → chip「宿主=omp ✕」出现、范围摘要变为「…；筛选：宿主=omp；任务粒度 executable-leaf」、发新查询；自定义 2026-10-15 +08:00 窗口与宿主筛选同时生效（摘要两者俱在）。
  - **无效范围（验收 4）**：自定义 from>to 点应用 → 「开始时间必须早于结束时间；不会静默回退到 24h」，statistics/query 请求数 8→8（零新查询）；单测覆盖另四类非法输入。
  - **data-quality 诚实（验收 2／AC-39）**：覆盖表 12 族实测行数（含真实 0：步骤/调用/用量等在该窗口为 0）；缺口与未关联区显示 未知发生时间事件 1 条（evt_created_untimed）、quality_summary unknown_time_events=1、快照告警 UNKNOWN_OCCURRED_AT、来源水位「无声明（单一本地来源）」、watermark_seq 20002——无伪造 0／绿灯。
  - **主题无重查**：切主题背景变 #14171c，API 请求数 31→31 零增量（R2.0a 延后项语义保持）。
  - Console 仅 favicon 404（既有）；envelope warnings 为 UNKNOWN_OCCURRED_AT 如实上浮。
- **全仓套件**：`python3 -B tests/run_ci.py --platform linux --output /tmp/rc2-r2b-ci-finish2`（新鲜目录；rtk: skipped-for-report）。本机 Linux，worktree tip `c6756f98e9d89f1240816321516d990976cf1d59`，dirty 仅本文件。started 2026-10-20T02:26:13+08:00，finished 2026-10-20T03:12:37+08:00。Ran 2349 tests in 1445.577s，FAILED (failures=1, skipped=62)，exit 1。原生报告 `/tmp/rc2-r2b-ci-finish2/linux-1.md` 结果「失败」；同 stem JSON `successful: false`，`required_native_failures: []`。唯一失败 `test_sbtd_probe_links.MaterializeAuthorizationTests.test_replaced_link_with_identical_text_is_refused`（AssertionError: ContractError not raised）。本任务未改 `tests/test_sbtd_probe_links.py`；与 R2.0a closeout 记录的同一 MaterializeAuthorizationTests 失败同类，不把全仓套件记为 PASS。先前两次 finish 均未写出 json/md、不得当作结果：Astra `/tmp/rc2-r2b-ci` 仅 `linux-1.inventory.json`（~01:12 Asia/Shanghai，session_exit ~01:56）；Grok `/tmp/rc2-r2b-ci-finish` 仅 inventory（~01:59），~02:22 按令杀死（当时 CPU 仍忙、无子进程）。本次 grok relaunch 等到 runner 写完 json/md。

## AC-52 落位说明（导出 UI 未到 R2.1a 的可验收路径）

R2.1a 导出作业创建时调用 `PinRegistry.pin(当前 snapshot_id)` 并持 pin 直到完成／取消；作业取数（ReportDocument／dataset 页）一律用 pin 解析出的 snapshot_id，不读页面当前视图。D12 轮询只经 pageModel 换当前视图，pageModel 无任何 pin 字段或参数（单测断言模型键集合仅 error/updating/view）。`snapshotPin.test.ts` 的「AC-52」用例模拟「pin snap_1 → 两次轮询整份替换到 snap_3 → pin 仍解析 snap_1」，证明在途导出语义在刷新下不可变；R2.0c 落盘快照的「被引用快照不得清理」不变量由该 pin 生命周期对接（已在 grill R1e 不变量中锁定）。

## CONTRACT-CHANGE-NEEDED

无（预期；如触发按硬边界停下报告）。

## 模型使用证据（models-used）

| 用途 | 模型 | 调用次数 |
|---|---|---|
| 实现（implement） | requested `openai-codex/gpt-6-astra:high`；actual fallback `kimi-code/k3`（per session logs，用户 closeout 指令） | unknown（未记录） |
| closeout 复跑与任务记录收口 | `xai-oauth/grok-4.7`（per session logs；requested astra; actual k3/grok per session logs） | unknown（不从先前记录推断调用次数） |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-19T23:07:33+08:00 | planned | in-progress | R2.0b 任务记录建立；事实源通读完成；首个 commit 为 R2.0a closeout 回填（#145／1415134／22:54:44）＋plan.md R2.0b 行 in_progress（docs only） | 本文件「事实源」；Lead 指派消息（2026-10-19 ~23:01 +08:00） |
| 2026-10-20T03:14:10+08:00 | in-progress | done | Grok closeout relaunch 收口：finish2 全仓套件已跑完并写入真实失败结果；先前 Astra/Grok finish 仅 inventory 被杀，不把那些当结果。plan.md R2.0b 保持 in_progress 至 PR 合并。TaskStore 未持久化：catalog 被未跟踪 ai/tasks/codex-verify/task.md 无 YAML frontmatter 阻断，本文件手写状态。 | `/tmp/rc2-r2b-ci-finish2/linux-1.md` 失败；2349 tests, failures=1, skipped=62；唯一失败 test_sbtd_probe_links.MaterializeAuthorizationTests.test_replaced_link_with_identical_text_is_refused |
| 2026-10-20T04:14:03+08:00 | done | done | merged：PR #146 squash-merged；R2.0c 首个 docs commit 按用户授权回填，不改变原分支绑定与本地完成时间；requested astra; actual k3/grok per session logs | merge SHA 2d147c98ce2874fa2621b95ff816e1781c02f93f；implement requested openai-codex/gpt-6-astra、actual kimi-code/k3；closeout xai-oauth/grok-4.7；用户 2026-10-20 11:02 指令 |
