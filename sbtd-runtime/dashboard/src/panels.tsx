/*
 * Specialized panels and inline detail (PRD v0.2 §12.4/§12.5/§12.6).
 *
 * Everything here renders rows from the *current* ReadyView — the same
 * snapshot_id the metric panels render — so detail can never drift from the
 * panels (§12.5 single-snapshot rule).
 *
 * - DataQualityPanel: the manifest-required always-visible panel that
 *   declares coverage / gaps / unlinked honestly from the snapshot's own
 *   quality fields (AC-39) — never a fake 0, never a green light.
 * - TaskAuditDetailPanel: task summary Top 20; clicking a task expands its
 *   step timeline and latest-50 event preview inline, each labelled
 *   展示 N 条／范围内总 M 条 (§12.6).
 * - PANEL_ROW_FAMILIES + PanelRowsPreview: the generic inline expansion for
 *   chart/table panels (chart click expands detail on the same page).
 */

import type { DatasetRow } from "./api";
import { MetricCell, PanelFrame, type PanelStatus } from "./PanelCard";
import type { PanelDefinition } from "./registry";
import type { ReadyView } from "./pageModel";

const FAMILY_LABELS_ZH: Record<string, string> = {
  task: "任务",
  run: "运行",
  step: "步骤",
  gate: "Gate",
  component: "组件",
  invocation: "调用",
  validation_run: "验证运行",
  validation_case: "验证用例",
  usage: "用量",
  artifact: "工件",
  event: "事件",
  data_quality: "数据质量",
};

/**
 * Presentation mapping: which dataset families back each panel's inline
 * detail. This is view metadata only — panel identity and metric bindings
 * remain owned by contracts/panel-manifest.json (D14).
 */
export const PANEL_ROW_FAMILIES: Record<string, readonly string[]> = {
  "task-lifecycle": ["task"],
  "activity-trend": ["event"],
  "mode-decisions": ["event"],
  "step-performance": ["step"],
  blockers: ["run"],
  "gate-matrix": ["gate"],
  "component-usage": ["component", "invocation"],
  "validation-evidence": ["validation_run", "validation_case"],
  "host-model-usage": ["usage"],
  "project-actor-summary": ["task"],
};

/** Per-family authoritative totals from the snapshot's dataset manifest. */
export function familyTotals(view: ReadyView): Record<string, number> {
  const totals: Record<string, number> = {};
  for (const item of view.snapshot.dataset_manifest) {
    const family = item["record_type"];
    const rows = item["rows"];
    if (typeof family === "string" && typeof rows === "number") {
      totals[family] = rows;
    }
  }
  return totals;
}

function fieldText(row: DatasetRow, name: string): string {
  const value = row.fields[name];
  if (value === null || value === undefined || value === "") return "unknown";
  return String(value);
}

/** One line describing a row for preview lists; nulls render as unknown. */
function rowLabel(row: DatasetRow): string {
  const occurred = fieldText(row, "occurred_at");
  const status = row.fields["status"];
  const statusText =
    status === null || status === undefined ? "" : ` — ${String(status)}`;
  return `${occurred} ${row.record_id}${statusText}`;
}

/**
 * A bounded, honestly-labelled row preview: “展示 N 条／范围内总 M 条”
 * (§12.6). M is the snapshot manifest's authoritative family total; the
 * preview cap is page expression only, never data truncation.
 */
export function PanelRowsPreview({
  rows,
  family,
  totals,
  truncated,
  limit = 50,
}: {
  rows: readonly DatasetRow[];
  family: string;
  totals: Record<string, number>;
  truncated: boolean;
  limit?: number;
}) {
  const shown = rows.slice(0, limit);
  const total = totals[family];
  const totalText = total === undefined ? `${rows.length}（已加载）` : `${total}`;
  return (
    <div className="panel-detail">
      <p className="panel-detail-count">
        {FAMILY_LABELS_ZH[family] ?? family}：展示 {shown.length} 条／范围内总{" "}
        {totalText} 条
        {truncated && "（数据集过大仅加载前若干页，预览基于已加载部分）"}
      </p>
      {shown.length === 0 ? (
        <p className="panel-state">范围内无{FAMILY_LABELS_ZH[family] ?? family}记录。</p>
      ) : (
        <ul className="panel-detail-list">
          {shown.map((row) => (
            <li key={row.record_id}>{rowLabel(row)}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Generic inline detail for chart/table panels (§12.5 同页展开明细). */
export function PanelFamilyDetail({
  panelId,
  view,
}: {
  panelId: string;
  view: ReadyView;
}) {
  const families = PANEL_ROW_FAMILIES[panelId] ?? [];
  const totals = familyTotals(view);
  return (
    <>
      {families.map((family) => (
        <PanelRowsPreview
          key={family}
          family={family}
          rows={view.rows.filter((row) => row.record_type === family)}
          totals={totals}
          truncated={view.rowsTruncated}
        />
      ))}
    </>
  );
}

/**
 * data-quality (AC-39, §12.4): declares coverage, gaps, unlinked and
 * unknown-time events from the snapshot's own quality fields. Every number
 * shown is measured (manifest row counts, quality_summary, real warning
 * codes); absence of a field is rendered as unknown, never as 0／绿灯.
 */
export function DataQualityPanel({
  definition,
  status,
  view,
}: {
  definition: PanelDefinition;
  status: PanelStatus;
  view: ReadyView | null;
}) {
  return (
    <PanelFrame definition={definition} status={status}>
      {status.kind === "ready" && view !== null && (
        <>
          <dl className="panel-metrics">
            {definition.metric_ids.map((metricId) => (
              <MetricCell
                key={metricId}
                metricId={metricId}
                entry={status.values[metricId]}
                insufficientDataZh={definition.insufficient_data_zh}
              />
            ))}
          </dl>
          <div className="quality-sections">
            <section aria-label="覆盖">
              <h3>覆盖（dataset manifest，实测行数）</h3>
              <table className="detail-table">
                <thead>
                  <tr>
                    <th>数据族</th>
                    <th>行数</th>
                  </tr>
                </thead>
                <tbody>
                  {view.snapshot.dataset_manifest.map((item, index) => {
                    const family = item["record_type"];
                    const rows = item["rows"];
                    return (
                      <tr key={typeof family === "string" ? family : index}>
                        <td>
                          {typeof family === "string"
                            ? (FAMILY_LABELS_ZH[family] ?? family)
                            : "unknown"}
                        </td>
                        <td>{typeof rows === "number" ? rows : "unknown"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </section>
            <section aria-label="缺口与未关联">
              <h3>缺口与未关联</h3>
              <ul className="panel-detail-list">
                <li>
                  未知发生时间事件：
                  {view.snapshot.unknown_time_event_ids.length} 条
                  {view.snapshot.unknown_time_event_ids.length > 0 &&
                    `（${view.snapshot.unknown_time_event_ids.slice(0, 5).join("、")}${
                      view.snapshot.unknown_time_event_ids.length > 5 ? "…" : ""
                    }）`}
                </li>
                <li>
                  quality_summary：
                  {Object.keys(view.snapshot.quality_summary).length === 0
                    ? "unknown（快照未携带）"
                    : Object.entries(view.snapshot.quality_summary)
                        .map(([key, value]) => `${key}=${String(value)}`)
                        .join("；")}
                </li>
                <li>
                  快照告警：
                  {view.snapshot.warnings.length === 0
                    ? "无"
                    : view.snapshot.warnings.join("、")}
                </li>
                <li>
                  来源水位：
                  {view.snapshot.source_watermarks.length === 0
                    ? "无声明（单一本地来源）"
                    : view.snapshot.source_watermarks
                        .map((item) => JSON.stringify(item))
                        .join("；")}
                </li>
                <li>水位序号 watermark_seq：{view.snapshot.watermark_seq}</li>
              </ul>
            </section>
          </div>
        </>
      )}
    </PanelFrame>
  );
}

const TASK_PREVIEW_LIMIT = 20;
const STEP_PREVIEW_LIMIT = 50;
const EVENT_PREVIEW_LIMIT = 50;

function taskRowsOf(view: ReadyView): DatasetRow[] {
  return view.rows.filter((row) => row.record_type === "task");
}

function stepsOfTask(view: ReadyView, taskUid: string): DatasetRow[] {
  return view.rows
    .filter(
      (row) => row.record_type === "step" && row.fields["task_uid"] === taskUid,
    )
    .sort((a, b) =>
      fieldText(a, "started_at").localeCompare(fieldText(b, "started_at")),
    );
}

function eventsOfTask(view: ReadyView, taskUid: string): DatasetRow[] {
  return view.rows
    .filter(
      (row) => row.record_type === "event" && row.fields["task_uid"] === taskUid,
    )
    .sort((a, b) =>
      fieldText(b, "occurred_at").localeCompare(fieldText(a, "occurred_at")),
    );
}

/** Inline detail for one expanded task: step timeline + event preview. */
function TaskDetail({ view, taskUid }: { view: ReadyView; taskUid: string }) {
  const steps = stepsOfTask(view, taskUid);
  const events = eventsOfTask(view, taskUid);
  const shownSteps = steps.slice(0, STEP_PREVIEW_LIMIT);
  const shownEvents = events.slice(0, EVENT_PREVIEW_LIMIT);
  return (
    <div className="task-detail">
      <section aria-label="步骤时间线">
        <h4>步骤时间线（展示 {shownSteps.length} 条／该任务范围内 {steps.length} 条）</h4>
        {shownSteps.length === 0 ? (
          <p className="panel-state">范围内无该任务的步骤记录。</p>
        ) : (
          <table className="detail-table">
            <thead>
              <tr>
                <th>步骤</th>
                <th>尝试</th>
                <th>开始</th>
                <th>耗时 ms</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              {shownSteps.map((row) => (
                <tr key={row.record_id}>
                  <td>{fieldText(row, "step_run_id")}</td>
                  <td>{fieldText(row, "attempt_no")}</td>
                  <td>{fieldText(row, "started_at")}</td>
                  <td>{fieldText(row, "duration_ms")}</td>
                  <td>{fieldText(row, "status")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
      <section aria-label="事件预览">
        <h4>
          事件预览（最新优先；展示 {shownEvents.length} 条／该任务范围内{" "}
          {events.length} 条）
        </h4>
        {shownEvents.length === 0 ? (
          <p className="panel-state">范围内无该任务的事件。</p>
        ) : (
          <ul className="panel-detail-list">
            {shownEvents.map((row) => (
              <li key={row.record_id}>
                {fieldText(row, "occurred_at")} {fieldText(row, "event_type")}
                {row.fields["status"] != null &&
                  ` — ${String(row.fields["status"])}`}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

/**
 * task-audit-detail (§12.4): task summary Top 20 with inline expansion.
 * Counts are measured from the snapshot's own rows; the family total comes
 * from the snapshot dataset manifest (authoritative), not from counting
 * preview rows.
 */
export function TaskAuditDetailPanel({
  definition,
  status,
  view,
  expandedTaskIds,
  onToggleTask,
}: {
  definition: PanelDefinition;
  status: PanelStatus;
  view: ReadyView | null;
  expandedTaskIds: readonly string[];
  onToggleTask: (taskUid: string) => void;
}) {
  const tasks = view === null ? [] : taskRowsOf(view);
  const shown = tasks.slice(0, TASK_PREVIEW_LIMIT);
  const totals = view === null ? {} : familyTotals(view);
  const total = totals["task"];
  return (
    <PanelFrame definition={definition} status={status}>
      {status.kind === "ready" && view !== null && (
        <>
          <p className="panel-detail-count">
            任务摘要：展示 {shown.length} 条／范围内总{" "}
            {total === undefined ? `${tasks.length}（已加载）` : total} 条
            {view.rowsTruncated && "（数据集过大仅加载前若干页）"}
          </p>
          {shown.length === 0 ? (
            <p className="panel-state">{definition.insufficient_data_zh}</p>
          ) : (
            <table className="detail-table">
              <thead>
                <tr>
                  <th>任务</th>
                  <th>状态</th>
                  <th>worktree</th>
                  <th>角色</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((row) => {
                  const taskUid = row.record_id;
                  const expanded = expandedTaskIds.includes(taskUid);
                  return (
                    <TaskRow
                      key={taskUid}
                      row={row}
                      view={view}
                      expanded={expanded}
                      onToggle={() => onToggleTask(taskUid)}
                    />
                  );
                })}
              </tbody>
            </table>
          )}
        </>
      )}
    </PanelFrame>
  );
}

function TaskRow({
  row,
  view,
  expanded,
  onToggle,
}: {
  row: DatasetRow;
  view: ReadyView;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <tr>
        <td>
          <button
            type="button"
            className="task-link"
            aria-expanded={expanded}
            onClick={onToggle}
          >
            {row.record_id}
          </button>
        </td>
        <td>{fieldText(row, "status")}</td>
        <td>{fieldText(row, "worktree_id")}</td>
        <td>{row.relation_role}</td>
      </tr>
      {expanded && (
        <tr className="task-detail-row">
          <td colSpan={4}>
            <TaskDetail view={view} taskUid={row.record_id} />
          </td>
        </tr>
      )}
    </>
  );
}
