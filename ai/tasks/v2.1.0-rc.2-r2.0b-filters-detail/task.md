---
schema_version: 1
id: v2.1.0-rc.2-r2.0b-filters-detail
workflow_mode: strict
mode_source: user
mode_note: Lead 本次明确指派 strict 模式 SBTD 任务；范围严格等于 plan.md R2.0b 行＋PRD §12.5／§12.6／§12.4 data-quality＋D12（grill Q6b-A）。硬边界：不得变更 contracts/openapi.yaml、contracts/panel-manifest.json、panel-manifest.schema.json、ADR 0002 决策或任何其他契约；不实现 R2.0c 快照落盘、R2.1a/b 导出格式、R2.2 E2E 证据；不改 PRD 正文；契约变更不可避时停下并出 CONTRACT-CHANGE-NEEDED 报告。显式 git add 路径；不纳入 .omp-r12b-addendum.txt 与 ai/tasks/codex-verify/；不 push、不开 PR。plan.md R2.0b 行在本 PR 合并前不标 done。
status: "in-progress"
blocked_reason: null
branch: feat/v2.1.0-rc.2-r2.0b-filters-detail
created_at: '2026-10-19T23:07:33+08:00'
updated_at: '2026-10-19T23:07:33+08:00'
completed_at: null
---

R2.0b：筛选、数据质量、页内详情。分支 `feat/v2.1.0-rc.2-r2.0b-filters-detail` 基于 main `1415134`（PR #145 squash-merge 产物）。实现模型 `openai-codex/gpt-6-astra:high`。

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

（待填）

## 验证证据

（待填）

## CONTRACT-CHANGE-NEEDED

无（预期；如触发按硬边界停下报告）。

## 模型使用证据（models-used）

| 用途 | 模型 | 调用次数 |
|---|---|---|
| 实现（implement：本任务全部 commit） | `openai-codex/gpt-6-astra:high` | unknown（未记录） |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-19T23:07:33+08:00 | planned | in-progress | R2.0b 任务记录建立；事实源通读完成；首个 commit 为 R2.0a closeout 回填（#145／1415134／22:54:44）＋plan.md R2.0b 行 in_progress（docs only） | 本文件「事实源」；Lead 指派消息（2026-10-19 ~23:01 +08:00） |
