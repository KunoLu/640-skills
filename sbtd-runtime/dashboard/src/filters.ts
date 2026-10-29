/*
 * Dimension filters (PRD v0.2 §12.5: 项目、宿主、模式等筛选与时间共同生效，
 * 当前范围摘要必须写出完整条件).
 *
 * Only the six dimensions the QueryScope contract already supports
 * (stats_query.FILTER_KEYS) are offered — the UI never invents a filter the
 * server would reject. Options are derived from the current snapshot's real
 * dataset rows, never hardcoded.
 */

import type { DatasetRow } from "./api";
import { t, type Locale, type StringKey } from "./i18n.ts";

export const FILTER_KEYS = [
  "project_ids",
  "actor_ids",
  "host_kinds",
  "workflow_modes",
  "component_ids",
  "evidence_levels",
] as const;
export type FilterKey = (typeof FILTER_KEYS)[number];

/** Dictionary key per filter dimension (labels live in i18n.ts). */
const FILTER_LABEL_KEYS: Record<FilterKey, StringKey> = {
  project_ids: "filter_project_ids",
  actor_ids: "filter_actor_ids",
  host_kinds: "filter_host_kinds",
  workflow_modes: "filter_workflow_modes",
  component_ids: "filter_component_ids",
  evidence_levels: "filter_evidence_levels",
};

/** Localized label of one filter dimension. */
export function filterLabel(locale: Locale, key: FilterKey): string {
  return t(locale, FILTER_LABEL_KEYS[key]);
}

/** Row field (report_snapshot._base_fields) backing each filter dimension. */
const FIELD_OF_FILTER: Record<FilterKey, string> = {
  project_ids: "project_id",
  actor_ids: "actor_id",
  host_kinds: "host_kind",
  workflow_modes: "workflow_mode",
  component_ids: "component_id",
  evidence_levels: "evidence_status",
};

export type FilterSelection = Partial<Record<FilterKey, string[]>>;

/** Distinct, sorted, non-empty values seen for each dimension in `rows`. */
export function deriveFilterOptions(
  rows: readonly DatasetRow[],
): Record<FilterKey, string[]> {
  const seen: Record<FilterKey, Set<string>> = {
    project_ids: new Set(),
    actor_ids: new Set(),
    host_kinds: new Set(),
    workflow_modes: new Set(),
    component_ids: new Set(),
    evidence_levels: new Set(),
  };
  for (const row of rows) {
    for (const key of FILTER_KEYS) {
      const value = row.fields[FIELD_OF_FILTER[key]];
      if (typeof value === "string" && value.length > 0) {
        seen[key].add(value);
      }
    }
  }
  return {
    project_ids: [...seen.project_ids].sort(),
    actor_ids: [...seen.actor_ids].sort(),
    host_kinds: [...seen.host_kinds].sort(),
    workflow_modes: [...seen.workflow_modes].sort(),
    component_ids: [...seen.component_ids].sort(),
    evidence_levels: [...seen.evidence_levels].sort(),
  };
}

/** Drop empty dimensions; the result maps 1:1 onto QueryScope.filters. */
export function cleanFilters(selection: FilterSelection): Record<string, string[]> {
  const result: Record<string, string[]> = {};
  for (const key of FILTER_KEYS) {
    const values = selection[key];
    if (values && values.length > 0) result[key] = [...values];
  }
  return result;
}

/**
 * The complete current-scope summary from the snapshot the page actually
 * rendered (§12.5) — the server's effective window and normalized filters,
 * not the client's request-time guesses.
 */
export function summarizeSnapshotScope(
  snapshot: {
    effective_from: string;
    effective_to: string;
    timezone: string;
    query_scope: Record<string, unknown>;
  },
  locale: Locale = "zh",
): string {
  const listJoiner = locale === "zh" ? "|" : ", ";
  const clauseJoiner = locale === "zh" ? "；" : "; ";
  const parts = [
    t(locale, "scope_time", {
      from: snapshot.effective_from,
      to: snapshot.effective_to,
      timezone: snapshot.timezone,
    }),
  ];
  const rawFilters = snapshot.query_scope["filters"];
  const filters =
    rawFilters !== null && typeof rawFilters === "object"
      ? (rawFilters as Record<string, unknown>)
      : {};
  const active = FILTER_KEYS.filter((key) => {
    const values = filters[key];
    return Array.isArray(values) && values.length > 0;
  });
  if (active.length === 0) {
    parts.push(t(locale, "scope_filters_none"));
  } else {
    const text = active
      .map((key) => {
        const values = filters[key];
        return `${filterLabel(locale, key)}=${(values as unknown[])
          .map(String)
          .join(listJoiner)}`;
      })
      .join(clauseJoiner);
    parts.push(t(locale, "scope_filters", { text }));
  }
  const granularity = snapshot.query_scope["task_granularity"];
  parts.push(
    t(locale, "scope_granularity", {
      granularity:
        typeof granularity === "string" ? granularity : "executable-leaf",
    }),
  );
  return parts.join(clauseJoiner);
}
