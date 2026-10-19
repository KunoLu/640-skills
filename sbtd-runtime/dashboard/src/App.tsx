import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ApiError,
  clearTicketFromAddressBar,
  defaultScope24h,
  fetchReportSnapshot,
  pairWithTicket,
  queryStatistics,
  readSession,
  readTicketFromFragment,
  type MetricValue,
  type QueryScope,
} from "./api";
import { PanelCard, type PanelStatus } from "./PanelCard";
import { ALL_METRIC_IDS, PANEL_REGISTRY } from "./registry";
import {
  DEFAULT_PRESENTATION_STATE,
  ReportDocument,
  type Snapshot,
} from "./reportDocument";

type Theme = "dark" | "light";

type PageState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; snapshot: Snapshot; values: Record<string, MetricValue> };

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
  const [state, setState] = useState<PageState>({ kind: "loading" });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("sbtd.theme", theme);
  }, [theme]);

  // load intentionally does NOT depend on theme: presentation_state.theme is
  // applied when the ReportDocument is derived below, so switching theme
  // never re-queries the API.
  const load = useCallback(async (scope: QueryScope) => {
    setState({ kind: "loading" });
    try {
      const stats = await queryStatistics(scope);
      const snapshotId = stats.snapshot_id;
      if (typeof snapshotId !== "string" || snapshotId.length === 0) {
        throw new ApiError(
          "statistics response carried no snapshot_id",
          null,
        );
      }
      const snapshot = await fetchReportSnapshot(snapshotId);
      setState({ kind: "ready", snapshot, values: stats.metrics });
    } catch (error) {
      setState({ kind: "error", message: String(error) });
    }
  }, []);

  // Bootstrap (D7): a one-time ticket in the URL fragment is exchanged for a
  // session before any data query; the fragment leaves the address bar and
  // history immediately. Without ticket and without an existing session the
  // page says so honestly instead of querying into a 401.
  useEffect(() => {
    const ticket = readTicketFromFragment();
    if (ticket !== null) {
      clearTicketFromAddressBar();
      void pairWithTicket(ticket)
        .then(() => load(defaultScope24h(ALL_METRIC_IDS)))
        .catch((error: unknown) =>
          setState({ kind: "error", message: String(error) }),
        );
      return;
    }
    if (readSession() === null) {
      setState({
        kind: "error",
        message:
          "未配对：本页须经 sbtd-runtime serve 自动打开的配对链接访问" +
          "（ticket 一次性且短时有效；过期请重启 serve）",
      });
      return;
    }
    void load(defaultScope24h(ALL_METRIC_IDS));
  }, [load]);

  const report = useMemo(() => {
    if (state.kind !== "ready") return null;
    return new ReportDocument(state.snapshot, {
      ...DEFAULT_PRESENTATION_STATE,
      theme,
    });
  }, [state, theme]);

  const watermark = report ? report.snapshot.as_of : null;

  return (
    <div className="page">
      <header className="topbar">
        <h1>SBTD Runtime Dashboard</h1>
        <div className="controls">
          <button
            type="button"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? "浅色" : "深色"}主题
          </button>
          <div
            className="segmented"
            role="group"
            aria-label="时间范围"
          >
            <button type="button" className="segment-active" aria-pressed="true">
              24h
            </button>
            <button type="button" disabled title="R2.0b 交付筛选后启用">
              7d
            </button>
            <button type="button" disabled title="R2.0b 交付筛选后启用">
              30d
            </button>
            <button type="button" disabled title="R2.0b 交付筛选后启用">
              自定义
            </button>
          </div>
          <div className="segmented" role="group" aria-label="导出">
            {["HTML 网页", "JPEG 长图", "PDF 文档", "CSV 数据"].map((label) => (
              <button
                key={label}
                type="button"
                disabled
                title="R2.1a 交付导出后启用"
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        <p className="watermark">
          {watermark
            ? `数据水位：${watermark}`
            : "数据水位：未知（尚未取得快照）"}
        </p>
      </header>
      <main className="grid">
        {PANEL_REGISTRY.map((definition) => {
          const status: PanelStatus =
            state.kind === "loading"
              ? { kind: "loading" }
              : state.kind === "error"
                ? { kind: "error", message: state.message }
                : { kind: "ready", values: state.values };
          return (
            <PanelCard
              key={definition.panel_id}
              definition={definition}
              status={status}
            />
          );
        })}
      </main>
      <footer className="page-footer">
        全页报告导出包含所有统计 Panel、其图表／表格，以及当前展开的详情；CSV
        包含筛选范围内全部安全结构化记录，不受预览行数限制。（导出为 R2.1a
        范围，当前不可用。）
      </footer>
    </div>
  );
}
