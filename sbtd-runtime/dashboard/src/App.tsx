import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ApiError,
  clearTicketFromAddressBar,
  createExport,
  deleteExport,
  downloadExport,
  getCapabilities,
  getExport,
  type ExportCapabilities,
  fetchAllSnapshotRows,
  fetchReportSnapshot,
  pairWithTicket,
  queryStatistics,
  readSession,
  readTicketFromFragment,
} from "./api";
import { ExportJob, exportErrorMessage, type ExportFormat, type ExportState } from "./exportJob";
import {
  cleanFilters,
  deriveFilterOptions,
  FILTER_KEYS,
  filterLabel,
  summarizeSnapshotScope,
  type FilterKey,
  type FilterSelection,
} from "./filters";
import {
  initialLocale,
  persistLocale,
  t,
  type Locale,
  type StringKey,
} from "./i18n.ts";
import {
  applyFailure,
  applySuccess,
  beginLoad,
  INITIAL_MODEL,
  retainExpansions,
  type PageModel,
  type ReadyView,
} from "./pageModel";
import { PanelCard, type PanelStatus } from "./PanelCard";
import {
  DataQualityPanel,
  PANEL_ROW_FAMILIES,
  PanelFamilyDetail,
  TaskAuditDetailPanel,
} from "./panels";
import { ALL_METRIC_IDS } from "./registry";
import {
  DEFAULT_PRESENTATION_STATE,
  ReportDocument,
} from "./reportDocument";
import {
  buildScope,
  loadSelection,
  localTimezone,
  PRESET_IDS,
  saveSelection,
  TimeRangeError,
  validateCustomRange,
  type TimeSelection,
} from "./timeRange";

type Theme = "dark" | "light";

const POLL_INTERVAL_MS = 30_000;
const EXPORT_FORMATS: readonly (readonly [ExportFormat, StringKey])[] = [
  ["html", "export_format_html"], ["jpeg", "export_format_jpeg"], ["pdf", "export_format_pdf"], ["csv", "export_format_csv"],
];

function systemTheme(): Theme {
  return window.matchMedia("(prefers-color-scheme: light)").matches
    ? "light"
    : "dark";
}

export function App() {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem("sbtd.theme");
    return saved === "light" || saved === "dark" ? saved : systemTheme();
  });
  const [locale, setLocale] = useState<Locale>(initialLocale);
  const [model, setModel] = useState<PageModel>(INITIAL_MODEL);
  const [selection, setSelection] = useState<TimeSelection>(loadSelection);
  const [filters, setFilters] = useState<FilterSelection>({});
  const [customOpen, setCustomOpen] = useState(false);
  const [customError, setCustomError] = useState<string | null>(null);
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");
  const [customTz, setCustomTz] = useState(localTimezone);
  const [expandedPanels, setExpandedPanels] = useState<Record<string, true>>({});
  const [expandedTasks, setExpandedTasks] = useState<string[]>([]);

  const [capabilities, setCapabilities] = useState<ExportCapabilities | null>(null);
  const [capabilityError, setCapabilityError] = useState("");
  const [exportState, setExportState] = useState<ExportState | null>(null);
  const [exportBusy, setExportBusy] = useState(false);
  const [exportLabel, setExportLabel] = useState("");
  const exportRef = useRef<ExportJob | null>(null);
  const blobUrls = useRef(new Set<string>());
  const hasView = model.view !== null;

  useEffect(() => {
    if (!hasView) return;
    const controller = new AbortController();
    getCapabilities(controller.signal).then(
      value => { if (!controller.signal.aborted) setCapabilities(value); },
      error => { if (!controller.signal.aborted) setCapabilityError(exportErrorMessage(error, locale)); },
    );
    return () => controller.abort();
  }, [hasView, locale]);

  useEffect(() => () => {
    exportRef.current?.stop();
    exportRef.current = null;
    for (const url of blobUrls.current) URL.revokeObjectURL(url);
    blobUrls.current.clear();
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("sbtd.theme", theme);
  }, [theme]);
  useEffect(() => {
    persistLocale(locale);
  }, [locale]);

  /**
   * One load = one query roundtrip = one snapshot_id. Metric values, the
   * Snapshot and the dataset rows are installed atomically via applySuccess,
   * so panels and inline detail always share one snapshot (§12.5; AC-38).
   * load intentionally does NOT depend on theme: theme is presentation_state
   * applied at ReportDocument derivation, never a re-query trigger.
   */
  const load = useCallback(async (sel: TimeSelection, selFilters: FilterSelection) => {
    setModel((current) => beginLoad(current));
    try {
      // TimeSelection is validated before it is stored; buildScope still
      // throws on a corrupt restored selection — never a silent 24h.
      const scope = buildScope(sel, cleanFilters(selFilters), ALL_METRIC_IDS, new Date(), locale);
      const stats = await queryStatistics(scope);
      const snapshotId = stats.snapshot_id;
      if (typeof snapshotId !== "string" || snapshotId.length === 0) {
        throw new ApiError("statistics response carried no snapshot_id", null);
      }
      const snapshot = await fetchReportSnapshot(snapshotId);
      const dataset = await fetchAllSnapshotRows(snapshotId);
      const view: ReadyView = {
        snapshot,
        values: stats.metrics,
        rows: dataset.rows,
        totalRows: dataset.total,
        rowsTruncated: dataset.truncated,
      };
      setModel((current) => applySuccess(current, view));
      // Whole-snapshot replace (D12): inline expansions survive only when
      // their record exists in the new snapshot — never old detail next to
      // new panels.
      setExpandedTasks((ids) => retainExpansions(ids, view));
    } catch (error) {
      setModel((current) => applyFailure(current, String(error)));
    }
  }, [locale]);

  // Latest selection/filters for the poll tick; the interval itself never
  // re-arms, so a filter change cannot cause overlapping poll loops.
  const paramsRef = useRef({ selection, filters });
  paramsRef.current = { selection, filters };
  const loadRef = useRef(load);
  loadRef.current = load;

  const reload = useCallback(() => {
    void loadRef.current(paramsRef.current.selection, paramsRef.current.filters);
  }, []);

  // D12: re-resolve every 30s; presets use fixed query-bucket ceilings (§12.5).
  // A query may reuse the same snapshot_id. Keep the previous view until
  // loading completes, then replace the whole snapshot.
  useEffect(() => {
    const timer = setInterval(reload, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [reload]);

  // Bootstrap (D7): a one-time ticket in the URL fragment is exchanged for a
  // session before any data query; the fragment leaves the address bar and
  // history immediately. Without ticket and without an existing session the
  // page says so honestly instead of querying into a 401.
  useEffect(() => {
    const ticket = readTicketFromFragment();
    if (ticket !== null) {
      clearTicketFromAddressBar();
      pairWithTicket(ticket, locale)
        .then(() =>
          loadRef.current(paramsRef.current.selection, paramsRef.current.filters),
        )
        .catch((error: unknown) =>
          setModel((current) => applyFailure(current, String(error))),
        );
      return;
    }
    if (readSession() === null) {
      setModel((current) =>
        applyFailure(current, t(locale, "error_unpaired")),
      );
      return;
    }
    void loadRef.current(paramsRef.current.selection, paramsRef.current.filters);
  }, []);

  const report = useMemo(() => {
    if (model.view === null) return null;
    return new ReportDocument(model.view.snapshot, {
      ...DEFAULT_PRESENTATION_STATE,
      theme,
      locale,
      expanded_detail_ids: [...Object.keys(expandedPanels), ...expandedTasks],
    });
  }, [model.view, theme, locale, expandedPanels, expandedTasks]);

  const unavailableReason = (format: ExportFormat) => {
    if (format === "html" || format === "csv") return "";
    const capability = capabilities?.exports[format];
    return capability?.available ? "" : capability?.reason || capabilityError || t(locale, "renderer_checking");
  };

  const startExport = async (format: ExportFormat) => {
    if (!report || exportBusy || unavailableReason(format)) return;
    exportRef.current?.stop();
    const job = new ExportJob(report.snapshot.snapshot_id, format, report.presentation_state,
      { createExport, getExport, deleteExport, downloadExport }, setExportState);
    exportRef.current = job;
    setExportBusy(true);
    setExportLabel(`${format.toUpperCase()} · ${report.snapshot.effective_from} — ${report.snapshot.effective_to} (${report.snapshot.timezone})`);
    const file = await job.run();
    if (exportRef.current !== job || job.controller.signal.aborted) return;
    try {
      if (file) {
        const url = URL.createObjectURL(file.blob);
        blobUrls.current.add(url);
        const link = document.createElement("a");
        link.href = url;
        link.download = file.filename;
        document.body.append(link);
        try { link.click(); } finally {
          link.remove();
          setTimeout(() => { URL.revokeObjectURL(url); blobUrls.current.delete(url); }, 0);
        }
      }
    } catch (error) {
      setExportState(current => ({ status: "failed", message: exportErrorMessage(error, locale), warnings: current?.warnings ?? [] }));
    }
    setExportBusy(false);
  };

  const cancelExport = async () => {
    const job = exportRef.current;
    if (!job?.id) return;
    setExportBusy(true);
    try {
      await job.cancel();
      if (exportRef.current === job) setExportState(current => ({
        status: "cancelled", message: t(locale, "export_cancelled"), warnings: current?.warnings ?? [],
      }));
    } catch (error) {
      if (exportRef.current === job) setExportState(current => ({
        status: "failed", message: exportErrorMessage(error, locale), warnings: current?.warnings ?? [],
      }));
    }
    if (exportRef.current === job) setExportBusy(false);
  };

  const selectPreset = (preset: (typeof PRESET_IDS)[number]) => {
    const next: TimeSelection = { kind: "preset", preset };
    setSelection(next);
    saveSelection(next);
    setCustomOpen(false);
    setCustomError(null);
    void load(next, filters);
  };

  const applyCustom = () => {
    try {
      // Validation only — throws TimeRangeError, never falls back to 24h.
      validateCustomRange(customFrom, customTo, customTz, new Date(), locale);
    } catch (error) {
      setCustomError(
        error instanceof TimeRangeError ? error.message : String(error),
      );
      return;
    }
    const next: TimeSelection = {
      kind: "custom",
      from: customFrom,
      to: customTo,
      timezone: customTz.trim() || localTimezone(),
    };
    setSelection(next);
    saveSelection(next);
    setCustomOpen(false);
    setCustomError(null);
    void load(next, filters);
  };

  const toggleFilterValue = (key: FilterKey, value: string) => {
    const current = filters[key] ?? [];
    const nextValues = current.includes(value)
      ? current.filter((item) => item !== value)
      : [...current, value];
    const next: FilterSelection = { ...filters, [key]: nextValues };
    setFilters(next);
    void load(selection, next);
  };

  const togglePanel = (panelId: string) => {
    setExpandedPanels((current) => {
      const next = { ...current };
      if (next[panelId] === true) {
        delete next[panelId];
      } else {
        next[panelId] = true;
      }
      return next;
    });
  };

  const toggleTask = (taskUid: string) => {
    setExpandedTasks((ids) =>
      ids.includes(taskUid)
        ? ids.filter((id) => id !== taskUid)
        : [...ids, taskUid],
    );
  };

  const view = model.view;
  const panelStatus: PanelStatus =
    view === null
      ? model.error !== null
        ? { kind: "error", message: model.error }
        : { kind: "loading" }
      : { kind: "ready", values: view.values };
  const filterOptions = view === null ? null : deriveFilterOptions(view.rows);
  const activeFilterCount = Object.values(cleanFilters(filters)).reduce(
    (sum, values) => sum + values.length,
    0,
  );

  return (
    <div className="page">
      <header className="topbar">
        <div className="topbar-main">
          <h1 className="brand">SBTD<span className="brand-sep">/</span>Runtime Dashboard</h1>
          <div className="controls">
            {(view !== null || model.updating) && (
              <span className="live-badge" role="status">
                <span className="live-dot" aria-hidden="true" />
                {model.updating
                  ? t(locale, "updating")
                  : `Live · ${view!.snapshot.as_of.slice(11, 16)}`}
              </span>
            )}
            <button type="button" onClick={reload} disabled={model.updating}>
              {t(locale, "refresh")}
            </button>
            <div className="segmented" role="group" aria-label={t(locale, "aria_time_range")}>
              {PRESET_IDS.map((preset) => (
                <button
                  key={preset}
                  type="button"
                  className={
                    selection.kind === "preset" && selection.preset === preset
                      ? "segment-active"
                      : undefined
                  }
                  aria-pressed={
                    selection.kind === "preset" && selection.preset === preset
                  }
                  onClick={() => selectPreset(preset)}
                >
                  {preset}
                </button>
              ))}
              <button
                type="button"
                className={
                  selection.kind === "custom" ? "segment-active" : undefined
                }
                aria-pressed={selection.kind === "custom"}
                aria-expanded={customOpen}
                onClick={() => setCustomOpen(!customOpen)}
              >
                {t(locale, "custom")}
              </button>
            </div>
            <div className="segmented" role="group" aria-label={t(locale, "aria_export")}>
              {EXPORT_FORMATS.map(([format, labelKey]) => (
                <button
                  key={format}
                  type="button"
                  disabled={!report || exportBusy || Boolean(unavailableReason(format))}
                  title={unavailableReason(format) || t(locale, "export_tooltip")}
                  onClick={() => void startExport(format)}
                >
                  {t(locale, labelKey)}
                </button>
              ))}
            </div>
            {exportRef.current?.id && exportState?.status !== "ready" && exportState?.status !== "cancelled" && (
              <button type="button" onClick={() => void cancelExport()}
                disabled={exportRef.current.controller.signal.aborted && exportBusy}>{t(locale, "cancel_export")}</button>
            )}
            <button
              type="button"
             
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            >
              {t(locale, theme === "dark" ? "theme_to_light" : "theme_to_dark")}
            </button>
            <div className="segmented" role="group" aria-label={t(locale, "locale_switch_label")}>
              <button
                type="button"
                className={locale === "en" ? "segment-active" : undefined}
                aria-pressed={locale === "en"}
                onClick={() => setLocale("en")}
              >
                {t(locale, "locale_en")}
              </button>
              <button
                type="button"
                className={locale === "zh" ? "segment-active" : undefined}
                aria-pressed={locale === "zh"}
                onClick={() => setLocale("zh")}
              >
                {t(locale, "locale_zh")}
              </button>
            </div>
          </div>
        </div>
        <div className="export-feedback" role="status" aria-live="polite">
          {(["jpeg", "pdf"] as const).map(format => unavailableReason(format) && (
            <p className="export-unavailable" key={format}>{format.toUpperCase()}{locale === "zh" ? "：" : ": "}{unavailableReason(format)}</p>
          ))}
          {exportState && <>
            <p className={exportState.status === "failed" ? "export-error" : undefined}>
              {exportLabel}{locale === "zh" ? "：" : ": "}{exportState.message}
            </p>
            {exportState.warnings.map(warning => <p className="export-warning" key={warning}>{t(locale, "warning_prefix", { warning })}</p>)}
          </>}
        </div>
        {customOpen && (
          <div className="custom-range" role="group" aria-label={t(locale, "aria_custom_range")}>
            <label>
              {t(locale, "custom_start")}
              <input
                type="text"
                value={customFrom}
                placeholder="2026-10-18T00:00:00+08:00"
                onChange={(event) => setCustomFrom(event.target.value)}
              />
            </label>
            <label>
              {t(locale, "custom_end")}
              <input
                type="text"
                value={customTo}
                placeholder="2026-10-19T00:00:00+08:00"
                onChange={(event) => setCustomTo(event.target.value)}
              />
            </label>
            <label>
              {t(locale, "custom_tz")}
              <input
                type="text"
                value={customTz}
                placeholder="Asia/Shanghai"
                onChange={(event) => setCustomTz(event.target.value)}
              />
            </label>
            <button type="button" onClick={applyCustom}>
              {t(locale, "apply")}
            </button>
            {customError !== null && (
              <p className="panel-state panel-state-error" role="alert">
                {customError}
              </p>
            )}
          </div>
        )}
        {filterOptions !== null && (
          <div className="filter-bar" aria-label={t(locale, "aria_filters")}>
            {FILTER_KEYS.map((key) => (
              <label key={key} className="filter-field">
                {filterLabel(locale, key)}
                <select
                  multiple
                  size={Math.min(Math.max(filterOptions[key].length, 1), 4)}
                  value={filters[key] ?? []}
                  onChange={(event) => {
                    const options = [...event.target.selectedOptions].map(
                      (option) => option.value,
                    );
                    const next: FilterSelection = { ...filters, [key]: options };
                    setFilters(next);
                    void load(selection, next);
                  }}
                >
                  {filterOptions[key].length === 0 ? (
                    <option disabled value="">
                      {t(locale, "filter_no_values")}
                    </option>
                  ) : (
                    filterOptions[key].map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))
                  )}
                </select>
              </label>
            ))}
          </div>
        )}
        {activeFilterCount > 0 && (
          <div className="filter-chips" aria-label={t(locale, "aria_active_filters")}>
            {FILTER_KEYS.flatMap((key) =>
              (filters[key] ?? []).map((value) => (
                <button
                  key={`${key}=${value}`}
                  type="button"
                  className="filter-chip"
                  onClick={() => toggleFilterValue(key, value)}
                  title={t(locale, "chip_remove_title")}
                >
                  {filterLabel(locale, key)}={value} ✕
                </button>
              )),
            )}
          </div>
        )}
        <p className="watermark">
          {view !== null
            ? t(locale, "watermark", {
                asOf: view.snapshot.as_of,
                snapshotId: view.snapshot.snapshot_id,
                watermarkSeq: view.snapshot.watermark_seq,
              })
            : t(locale, "watermark_unknown")}
          {model.updating && view !== null && (
            <span className="updating-badge" role="status">
              {t(locale, "updating")}
            </span>
          )}
        </p>
        {view !== null && (
          <p className="scope-summary">
            {t(locale, "current_scope", { scope: summarizeSnapshotScope(view.snapshot, locale) })}
          </p>
        )}
        {model.error !== null && view !== null && (
          <p className="panel-state panel-state-error" role="alert">
            {t(locale, "refresh_failed", { error: model.error })}
            <button type="button" onClick={reload}>
              {t(locale, "retry")}
            </button>
          </p>
        )}
        {model.error !== null && view === null && (
          <p className="panel-state panel-state-error" role="alert">
            {t(locale, "load_failed", { error: model.error })}
            <button type="button" onClick={reload}>
              {t(locale, "retry")}
            </button>
          </p>
        )}
      </header>
      <main className="grid">
        {(report === null ? [] : report.panels).map(({ definition }) => {
          if (definition.panel_id === "data-quality") {
            return (
              <DataQualityPanel
                key={definition.panel_id}
                definition={definition}
                status={panelStatus}
                view={view}
                locale={locale}
              />
            );
          }
          if (definition.panel_id === "task-audit-detail") {
            return (
              <TaskAuditDetailPanel
                key={definition.panel_id}
                definition={definition}
                status={panelStatus}
                view={view}
                expandedTaskIds={expandedTasks}
                onToggleTask={toggleTask}
                locale={locale}
              />
            );
          }
          const hasDetail = PANEL_ROW_FAMILIES[definition.panel_id] !== undefined;
          return (
            <PanelCard
              key={definition.panel_id}
              definition={definition}
              status={panelStatus}
              detailExpanded={expandedPanels[definition.panel_id] === true}
              onToggleDetail={
                hasDetail ? () => togglePanel(definition.panel_id) : undefined
              }
              locale={locale}
              detail={
                view !== null && hasDetail ? (
                  <PanelFamilyDetail panelId={definition.panel_id} view={view} locale={locale} />
                ) : undefined
              }
            />
          );
        })}
      </main>
      <footer className="page-footer">
        {t(locale, "footer_export_note")}
        {view !== null && view.rowsTruncated && (
          <>
            <br />
            {t(locale, "footer_rows_note", { totalRows: view.totalRows })}
          </>
        )}
      </footer>
    </div>
  );
}
