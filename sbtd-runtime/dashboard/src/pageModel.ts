/*
 * Page model (PRD v0.2 §12.5/§12.6, locked decision D12).
 *
 * One ReadyView is one atomic unit: metric values, the Snapshot, and the
 * dataset rows all come from a single query roundtrip tied to one
 * snapshot_id. Panels and inline detail render from the same view, so the
 * page can never mix old and new data (§12.5; AC-38).
 *
 * Refresh semantics (D12): a poll or manual refresh keeps the previous
 * completed view on screen, marks it 正在更新, and only swaps in the new
 * view when the whole roundtrip has succeeded. A failure keeps the old view
 * and records the error — never a blanked page, never a fake 0 (§12.5).
 */

import type { DatasetRow, MetricValue } from "./api";
import type { Snapshot } from "./reportDocument";

export interface ReadyView {
  snapshot: Snapshot;
  values: Record<string, MetricValue>;
  rows: DatasetRow[];
  /** Server-declared total dataset rows (all families) for this snapshot. */
  totalRows: number;
  /** True when the dataset walk hit its page cap; UI must say so. */
  rowsTruncated: boolean;
}

export interface PageModel {
  /** The last completed view; null only before the first successful load. */
  view: ReadyView | null;
  /** A refresh is in flight; the previous view stays visible (D12). */
  updating: boolean;
  /** Last load/refresh error; rendered as error+retry, never as 0. */
  error: string | null;
}

export const INITIAL_MODEL: PageModel = {
  view: null,
  updating: true,
  error: null,
};

/** A load starts: keep the previous view, mark updating, clear stale error. */
export function beginLoad(model: PageModel): PageModel {
  return { ...model, updating: true, error: null };
}

/**
 * A whole-snapshot replace (D12): the new view is installed atomically;
 * panels and detail switch together because they share this one object.
 */
export function applySuccess(_model: PageModel, view: ReadyView): PageModel {
  return { view, updating: false, error: null };
}

/**
 * A failed (re)load: the previous completed view stays on screen and the
 * error is surfaced for retry (§12.5). With no prior view the page shows
 * the error state instead of panels.
 */
export function applyFailure(model: PageModel, message: string): PageModel {
  return { ...model, updating: false, error: message };
}

/**
 * After a whole-snapshot replace, expanded inline details survive only when
 * their record still exists in the new snapshot's rows — otherwise the
 * detail would show rows from the old snapshot next to panels from the new
 * one, which §12.5 forbids.
 */
export function retainExpansions(
  expandedIds: readonly string[],
  view: ReadyView,
): string[] {
  const present: Record<string, true> = {};
  for (const row of view.rows) present[row.record_id] = true;
  return expandedIds.filter((id) => present[id] === true);
}
