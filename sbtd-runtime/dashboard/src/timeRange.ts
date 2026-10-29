/*
 * Time range selection (PRD v0.2 §12.5): OMP-style presets
 * 1h/24h/7d/30d/90d/All plus a Custom from/to/timezone entry. Default 24h.
 *
 * Hard rules implemented here:
 * - The last selection is remembered (localStorage), but preset bounds are
 *   re-resolved per query using a fixed 300-second UTC-epoch query bucket.
 *   Calls in the same bucket keep the same window; custom ranges stay exact.
 * - An invalid range (unparseable, from >= to, unknown timezone, entirely
 *   in the future) raises TimeRangeError with a clear message. Nothing here
 *   ever substitutes the 24h default silently (§12.5: 不能 silently 回退 24h).
 */

import type { QueryScope, QueryScopeRange } from "./api";
import { t, type Locale } from "./i18n.ts";

export const PRESET_IDS = ["1h", "24h", "7d", "30d", "90d", "all"] as const;
export type PresetId = (typeof PRESET_IDS)[number];
export const DEFAULT_PRESET: PresetId = "24h";

const HOUR_MS = 3600 * 1000;
const DAY_MS = 24 * HOUR_MS;
const QUERY_BUCKET_MS = 300_000;

const PRESET_DURATION_MS: Record<Exclude<PresetId, "all">, number> = {
  "1h": HOUR_MS,
  "24h": DAY_MS,
  "7d": 7 * DAY_MS,
  "30d": 30 * DAY_MS,
  "90d": 90 * DAY_MS,
};

/**
 * "All" means every ingested event the store holds; the lower bound is the
 * epoch so no real event falls outside the window. Stated honestly in the
 * scope summary rather than pretending an unbounded query exists.
 */
export const ALL_RANGE_FROM = "1970-01-01T00:00:00.000Z";

export class TimeRangeError extends Error {}

export type TimeSelection =
  | { kind: "preset"; preset: PresetId }
  | { kind: "custom"; from: string; to: string; timezone: string };

export function localTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
}

/** True when the IANA timezone name is usable by this runtime. */
export function isValidTimezone(timezone: string): boolean {
  if (timezone.length === 0) return false;
  try {
    new Intl.DateTimeFormat("en-US", { timeZone: timezone });
    return true;
  } catch {
    return false;
  }
}

/**
 * Resolve a preset using the ceiling of `now` in fixed query buckets, separate
 * from chart trend buckets. An exact boundary stays put; non-All durations
 * remain actual elapsed hours, not local calendar days.
 */
export function resolvePresetRange(
  preset: PresetId,
  now: Date,
  timezone: string = localTimezone(),
): QueryScopeRange {
  const endMs = Math.ceil(now.getTime() / QUERY_BUCKET_MS) * QUERY_BUCKET_MS;
  const to = new Date(endMs).toISOString();
  if (preset === "all") {
    return { from: ALL_RANGE_FROM, to, timezone };
  }
  const from = new Date(endMs - PRESET_DURATION_MS[preset]);
  return { from: from.toISOString(), to, timezone };
}

/**
 * Validate and normalize a custom range. Accepts anything Date.parse
 * understands. Throws TimeRangeError — never returns a fallback range.
 */
export function validateCustomRange(
  fromRaw: string,
  toRaw: string,
  timezoneRaw: string,
  now: Date = new Date(),
  locale: Locale = "zh",
): QueryScopeRange {
  const timezone = timezoneRaw.trim() || localTimezone();
  if (!isValidTimezone(timezone)) {
    throw new TimeRangeError(
      t(locale, "invalid_timezone", { timezone: timezoneRaw }),
    );
  }
  const from = new Date(fromRaw);
  const to = new Date(toRaw);
  if (Number.isNaN(from.getTime()) || Number.isNaN(to.getTime())) {
    throw new TimeRangeError(t(locale, "range_unparseable"));
  }
  if (!(from.getTime() < to.getTime())) {
    throw new TimeRangeError(t(locale, "range_order"));
  }
  if (from.getTime() > now.getTime()) {
    throw new TimeRangeError(t(locale, "range_future"));
  }
  return { from: from.toISOString(), to: to.toISOString(), timezone };
}

/** Resolve a selection: bucket-ceiling presets, exact custom bounds. */
export function resolveRange(
  selection: TimeSelection,
  now: Date = new Date(),
  locale: Locale = "zh",
): QueryScopeRange {
  if (selection.kind === "preset") {
    return resolvePresetRange(selection.preset, now);
  }
  return validateCustomRange(
    selection.from,
    selection.to,
    selection.timezone,
    now,
    locale,
  );
}

/** Build the full QueryScope for the current selection + dimension filters. */
export function buildScope(
  selection: TimeSelection,
  filters: Record<string, string[]>,
  metrics: string[],
  now: Date = new Date(),
  locale: Locale = "zh",
): QueryScope {
  const cleanFilters: Record<string, string[]> = {};
  for (const [key, values] of Object.entries(filters)) {
    if (values.length > 0) cleanFilters[key] = [...values];
  }
  const scope: QueryScope = {
    schema_version: "1.0",
    range: resolveRange(selection, now, locale),
    metrics: [...metrics],
  };
  if (Object.keys(cleanFilters).length > 0) scope.filters = cleanFilters;
  return scope;
}

const SELECTION_KEY = "sbtd.timeRange";

/** Remember the last selection (§12.5: 记忆上次 preset). */
export function saveSelection(selection: TimeSelection): void {
  try {
    localStorage.setItem(SELECTION_KEY, JSON.stringify(selection));
  } catch {
    /* storage unavailable: memory-only, still functional */
  }
}

/** Restore the remembered selection, or the 24h default when absent/invalid. */
export function loadSelection(): TimeSelection {
  try {
    const raw = localStorage.getItem(SELECTION_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as TimeSelection;
      if (
        parsed.kind === "preset" &&
        (PRESET_IDS as readonly string[]).includes(parsed.preset)
      ) {
        return parsed;
      }
      if (
        parsed.kind === "custom" &&
        typeof parsed.from === "string" &&
        typeof parsed.to === "string" &&
        typeof parsed.timezone === "string"
      ) {
        return parsed;
      }
    }
  } catch {
    /* fall through to default */
  }
  return { kind: "preset", preset: DEFAULT_PRESET };
}

/** Full human-readable range line for the scope summary (§12.5). */
export function describeRange(range: QueryScopeRange): string {
  return `${range.from} → ${range.to}（${range.timezone}）`;
}

/** Short label for the active selection, used on the toolbar. */
export function selectionLabel(
  selection: TimeSelection,
  locale: Locale = "zh",
): string {
  if (selection.kind === "preset") return selection.preset;
  return t(locale, "custom_label", {
    from: selection.from,
    to: selection.to,
    timezone: selection.timezone,
  });
}
