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
  FILTER_LABELS_ZH,
  summarizeSnapshotScope,
  type FilterKey,
  type FilterSelection,
} from "./filters";
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
const EXPORT_FORMATS = [
  ["html", "HTML 网页"], ["jpeg", "JPEG 长图"], ["pdf", "PDF 文档"], ["csv", "CSV 数据"],
] as const;

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
      error => { if (!controller.signal.aborted) setCapabilityError(exportErrorMessage(error)); },
    );
    return () => controller.abort();
  }, [hasView]);

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
      const scope = buildScope(sel, cleanFilters(selFilters), ALL_METRIC_IDS);
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
  }, []);

  // Latest selection/filters for the poll tick; the interval itself never
  // re-arms, so a filter change cannot cause overlapping poll loops.
  const paramsRef = useRef({ selection, filters });
  paramsRef.current = { selection, filters };
  const loadRef = useRef(load);
  loadRef.current = load;

  const reload = useCallback(() => {
    void loadRef.current(paramsRef.current.selection, paramsRef.current.filters);
  }, []);

  // D12: every 30s re-query the current scope; the window anchor is
  // re-resolved per query (§12.5), the previous view stays until the new
  // snapshot is fully loaded, then the page swaps whole-snapshot.
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
      pairWithTicket(ticket)
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
        applyFailure(
          current,
          "未配对：本页须经 sbtd-runtime serve 自动打开的配对链接访问" +
            "（ticket 一次性且短时有效；过期请重启 serve）",
        ),
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
      expanded_detail_ids: [...Object.keys(expandedPanels), ...expandedTasks],
    });
  }, [model.view, theme, expandedPanels, expandedTasks]);

  const unavailableReason = (format: ExportFormat) => {
    if (format === "html" || format === "csv") return "";
    const capability = capabilities?.exports[format];
    return capability?.available ? "" : capability?.reason || capabilityError || "正在检查 renderer 可用性";
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
      setExportState(current => ({ status: "failed", message: exportErrorMessage(error), warnings: current?.warnings ?? [] }));
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
        status: "cancelled", message: "导出已取消", warnings: current?.warnings ?? [],
      }));
    } catch (error) {
      if (exportRef.current === job) setExportState(current => ({
        status: "failed", message: exportErrorMessage(error), warnings: current?.warnings ?? [],
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
      validateCustomRange(customFrom, customTo, customTz);
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
        <h1>SBTD Runtime Dashboard</h1>
        <div className="controls">
          <button type="button" onClick={reload} disabled={model.updating}>
            刷新来源
          </button>
          <button
            type="button"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? "浅色" : "深色"}主题
          </button>
          <div className="segmented" role="group" aria-label="时间范围">
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
              自定义
            </button>
          </div>
          <div className="segmented" role="group" aria-label="导出">
            {EXPORT_FORMATS.map(([format, label]) => (
              <button
                key={format}
                type="button"
                disabled={!report || exportBusy || Boolean(unavailableReason(format))}
                title={unavailableReason(format) || "导出当前快照，自动刷新不影响在途导出"}
                onClick={() => void startExport(format)}
              >
                {label}
              </button>
            ))}
          </div>
          {exportRef.current?.id && exportState?.status !== "ready" && exportState?.status !== "cancelled" && (
            <button type="button" onClick={() => void cancelExport()}
              disabled={exportRef.current.controller.signal.aborted && exportBusy}>取消导出</button>
          )}
        </div>
        <div className="export-feedback" role="status" aria-live="polite">
          {(["jpeg", "pdf"] as const).map(format => unavailableReason(format) && (
            <p className="export-unavailable" key={format}>{format.toUpperCase()}：{unavailableReason(format)}</p>
          ))}
          {exportState && <>
            <p className={exportState.status === "failed" ? "export-error" : undefined}>
              {exportLabel}：{exportState.message}
            </p>
            {exportState.warnings.map(warning => <p className="export-warning" key={warning}>警告：{warning}</p>)}
          </>}
        </div>
        {customOpen && (
          <div className="custom-range" role="group" aria-label="自定义时间范围">
            <label>
              开始
              <input
                type="text"
                value={customFrom}
                placeholder="2026-10-18T00:00:00+08:00"
                onChange={(event) => setCustomFrom(event.target.value)}
              />
            </label>
            <label>
              结束
              <input
                type="text"
                value={customTo}
                placeholder="2026-10-19T00:00:00+08:00"
                onChange={(event) => setCustomTo(event.target.value)}
              />
            </label>
            <label>
              时区
              <input
                type="text"
                value={customTz}
                placeholder="Asia/Shanghai"
                onChange={(event) => setCustomTz(event.target.value)}
              />
            </label>
            <button type="button" onClick={applyCustom}>
              应用
            </button>
            {customError !== null && (
              <p className="panel-state panel-state-error" role="alert">
                {customError}
              </p>
            )}
          </div>
        )}
        {filterOptions !== null && (
          <div className="filter-bar" aria-label="维度筛选">
            {FILTER_KEYS.map((key) => (
              <label key={key} className="filter-field">
                {FILTER_LABELS_ZH[key]}
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
                      （范围内无取值）
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
          <div className="filter-chips" aria-label="当前筛选">
            {FILTER_KEYS.flatMap((key) =>
              (filters[key] ?? []).map((value) => (
                <button
                  key={`${key}=${value}`}
                  type="button"
                  className="filter-chip"
                  onClick={() => toggleFilterValue(key, value)}
                  title="点击移除该筛选"
                >
                  {FILTER_LABELS_ZH[key]}={value} ✕
                </button>
              )),
            )}
          </div>
        )}
        <p className="watermark">
          {view !== null
            ? `数据水位：${view.snapshot.as_of}（快照 ${view.snapshot.snapshot_id}，watermark_seq ${view.snapshot.watermark_seq}）`
            : "数据水位：未知（尚未取得快照）"}
          {model.updating && view !== null && (
            <span className="updating-badge" role="status">
              正在更新…
            </span>
          )}
        </p>
        {view !== null && (
          <p className="scope-summary">
            当前范围：{summarizeSnapshotScope(view.snapshot)}
          </p>
        )}
        {model.error !== null && view !== null && (
          <p className="panel-state panel-state-error" role="alert">
            刷新失败：{model.error}（仍显示上一份已完成快照视图）
            <button type="button" onClick={reload}>
              重试
            </button>
          </p>
        )}
        {model.error !== null && view === null && (
          <p className="panel-state panel-state-error" role="alert">
            加载失败：{model.error}
            <button type="button" onClick={reload}>
              重试
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
              detail={
                view !== null && hasDetail ? (
                  <PanelFamilyDetail panelId={definition.panel_id} view={view} />
                ) : undefined
              }
            />
          );
        })}
      </main>
      <footer className="page-footer">
        全页报告导出包含所有统计 Panel、其图表／表格，以及当前展开的详情；CSV
        包含筛选范围内全部安全结构化记录，不受预览行数限制。
        {view !== null && view.rowsTruncated && (
          <>
            <br />
            注意：本快照数据集共 {view.totalRows} 行，页面仅加载前若干页，行预览
            基于已加载部分；统计指标与 Panel 数值不受影响（服务端全量计算）。
          </>
        )}
      </footer>
    </div>
  );
}
