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
import { t, type Locale, type StringKey } from "./i18n.ts";

const FAMILY_KEYS: Record<string, StringKey> = {
  task: "family_task",
  run: "family_run",
  step: "family_step",
  gate: "family_gate",
  component: "family_component",
  invocation: "family_invocation",
  validation_run: "family_validation_run",
  validation_case: "family_validation_case",
  usage: "family_usage",
  artifact: "family_artifact",
  event: "family_event",
  data_quality: "family_data_quality",
};

/**
 * Localized family label; an unknown family id renders verbatim (the server
 * may add a family before the UI dictionary knows it).
 */
function familyLabel(locale: Locale, family: string): string {
  const key = FAMILY_KEYS[family];
  return key === undefined ? family : t(locale, key);
}

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
  locale,
}: {
  rows: readonly DatasetRow[];
  family: string;
  totals: Record<string, number>;
  truncated: boolean;
  limit?: number;
  locale: Locale;
}) {
  const shown = rows.slice(0, limit);
  const total = totals[family];
  const totalText =
    total === undefined ? `${rows.length}${t(locale, "loaded_suffix")}` : `${total}`;
  return (
    <div className="panel-detail">
      <p className="panel-detail-count">
        {t(locale, "family_rows", {
          family: familyLabel(locale, family),
          shown: shown.length,
          total: totalText,
        })}
        {truncated && t(locale, "truncated_note")}
      </p>
      {shown.length === 0 ? (
        <p className="panel-state">
          {t(locale, "no_family_records", {
            family: familyLabel(locale, family),
          })}
        </p>
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
  locale,
}: {
  panelId: string;
  view: ReadyView;
  locale: Locale;
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
          locale={locale}
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
  locale,
}: {
  definition: PanelDefinition;
  status: PanelStatus;
  view: ReadyView | null;
  locale: Locale;
}) {
  const listJoiner = locale === "zh" ? "、" : ", ";
  return (
    <PanelFrame definition={definition} status={status} locale={locale}>
      {status.kind === "ready" && view !== null && (
        <>
          <dl className="panel-metrics">
            {definition.metric_ids.map((metricId) => (
              <MetricCell
                key={metricId}
                metricId={metricId}
                entry={status.values[metricId]}
                insufficientDataZh={
                  locale === "en"
                    ? (definition.insufficient_data_en ?? definition.insufficient_data_zh)
                    : definition.insufficient_data_zh
                }
                locale={locale}
              />
            ))}
          </dl>
          <div className="quality-sections">
            <section aria-label={t(locale, "aria_coverage")}>
              <h3>{t(locale, "dq_coverage_heading")}</h3>
              <table className="detail-table">
                <thead>
                  <tr>
                    <th>{t(locale, "col_family")}</th>
                    <th>{t(locale, "col_rows")}</th>
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
                            ? familyLabel(locale, family)
                            : "unknown"}
                        </td>
                        <td>{typeof rows === "number" ? rows : "unknown"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </section>
            <section aria-label={t(locale, "aria_gaps")}>
              <h3>{t(locale, "dq_gaps")}</h3>
              <ul className="panel-detail-list">
                <li>
                  {t(locale, "unknown_time_events", {
                    count: view.snapshot.unknown_time_event_ids.length,
                  })}
                  {view.snapshot.unknown_time_event_ids.length > 0 &&
                    `${locale === "zh" ? "（" : " ("}${view.snapshot.unknown_time_event_ids
                      .slice(0, 5)
                      .join(listJoiner)}${
                      view.snapshot.unknown_time_event_ids.length > 5 ? "…" : ""
                    }${locale === "zh" ? "）" : ")"}`}
                </li>
                <li>
                  quality_summary{locale === "zh" ? "：" : ": "}
                  {Object.keys(view.snapshot.quality_summary).length === 0
                    ? t(locale, "not_carried")
                    : Object.entries(view.snapshot.quality_summary)
                        .map(([key, value]) => `${key}=${String(value)}`)
                        .join(locale === "zh" ? "；" : "; ")}
                </li>
                <li>
                  {t(locale, "snapshot_warnings", {
                    warnings:
                      view.snapshot.warnings.length === 0
                        ? t(locale, "value_none")
                        : view.snapshot.warnings.join(listJoiner),
                  })}
                </li>
                <li>
                  {t(locale, "source_watermark", {
                    value:
                      view.snapshot.source_watermarks.length === 0
                        ? t(locale, "no_declared_watermark")
                        : view.snapshot.source_watermarks
                            .map((item) => JSON.stringify(item))
                            .join(locale === "zh" ? "；" : "; "),
                  })}
                </li>
                <li>
                  {t(locale, "watermark_seq_item", {
                    seq: view.snapshot.watermark_seq,
                  })}
                </li>
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
function TaskDetail({
  view,
  taskUid,
  locale,
}: {
  view: ReadyView;
  taskUid: string;
  locale: Locale;
}) {
  const steps = stepsOfTask(view, taskUid);
  const events = eventsOfTask(view, taskUid);
  const shownSteps = steps.slice(0, STEP_PREVIEW_LIMIT);
  const shownEvents = events.slice(0, EVENT_PREVIEW_LIMIT);
  return (
    <div className="task-detail">
      <section aria-label={t(locale, "aria_step_timeline")}>
        <h4>
          {t(locale, "task_timeline", {
            shown: shownSteps.length,
            total: steps.length,
          })}
        </h4>
        {shownSteps.length === 0 ? (
          <p className="panel-state">{t(locale, "no_steps")}</p>
        ) : (
          <table className="detail-table">
            <thead>
              <tr>
                <th>{t(locale, "th_step")}</th>
                <th>{t(locale, "th_attempt")}</th>
                <th>{t(locale, "th_start")}</th>
                <th>{t(locale, "th_duration")}</th>
                <th>{t(locale, "th_status")}</th>
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
      <section aria-label={t(locale, "aria_events_preview")}>
        <h4>
          {t(locale, "events_preview", {
            shown: shownEvents.length,
            total: events.length,
          })}
        </h4>
        {shownEvents.length === 0 ? (
          <p className="panel-state">{t(locale, "no_events")}</p>
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
  locale,
}: {
  definition: PanelDefinition;
  status: PanelStatus;
  view: ReadyView | null;
  expandedTaskIds: readonly string[];
  onToggleTask: (taskUid: string) => void;
  locale: Locale;
}) {
  const tasks = view === null ? [] : taskRowsOf(view);
  const shown = tasks.slice(0, TASK_PREVIEW_LIMIT);
  const totals = view === null ? {} : familyTotals(view);
  const total = totals["task"];
  return (
    <PanelFrame definition={definition} status={status} locale={locale}>
      {status.kind === "ready" && view !== null && (
        <>
          <p className="panel-detail-count">
            {t(locale, "task_summary", {
              shown: shown.length,
              total:
                total === undefined
                  ? `${tasks.length}${t(locale, "loaded_suffix")}`
                  : total,
            })}
            {view.rowsTruncated && t(locale, "truncated_short")}
          </p>
          {shown.length === 0 ? (
            <p className="panel-state">{locale === "en" ? (definition.insufficient_data_en ?? definition.insufficient_data_zh) : definition.insufficient_data_zh}</p>
          ) : (
            <table className="detail-table">
              <thead>
                <tr>
                  <th>{t(locale, "th_task")}</th>
                  <th>{t(locale, "th_status")}</th>
                  <th>worktree</th>
                  <th>{t(locale, "th_role")}</th>
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
                      locale={locale}
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
  locale,
}: {
  row: DatasetRow;
  view: ReadyView;
  expanded: boolean;
  onToggle: () => void;
  locale: Locale;
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
            <TaskDetail view={view} taskUid={row.record_id} locale={locale} />
          </td>
        </tr>
      )}
    </>
  );
}
