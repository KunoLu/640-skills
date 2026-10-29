import type { PresentationState } from "./reportDocument.ts";
import { DEFAULT_LOCALE, t, type Locale, type StringKey } from "./i18n.ts";

export type ExportFormat = "html" | "csv" | "jpeg" | "pdf";
export interface ExportStatus {
  status: "queued" | "generating" | "ready" | "failed" | "cancelled";
  error: string | null;
  warnings?: string[];
}
export interface ExportState {
  status: ExportStatus["status"] | "requesting";
  message: string;
  warnings: string[];
}
export interface ExportInput {
  snapshot_id: string;
  format: ExportFormat;
  presentation_state: PresentationState;
}
export interface ExportFile { blob: Blob; filename: string }
export interface ExportApi {
  createExport(input: ExportInput, key: string, signal: AbortSignal): Promise<{ export_id: string; warnings?: string[] }>;
  getExport(id: string, signal: AbortSignal): Promise<ExportStatus>;
  deleteExport(id: string, key: string): Promise<void>;
  downloadExport(id: string, format: ExportFormat, signal: AbortSignal): Promise<ExportFile>;
}

export function exportErrorMessage(error: unknown, locale: Locale = DEFAULT_LOCALE): string {
  const e = error as { status?: number; detail?: string; code?: string; requestId?: string; message?: string } | null;
  const statusKeys: Record<number, StringKey> = {
    401: "export_err_401", 400: "export_err_400",
    404: "export_err_404", 409: "export_err_409", 410: "export_err_410",
    422: "export_err_422", 503: "export_err_503", 507: "export_err_507",
  };
  const codeKeys: Record<string, StringKey> = {
    EXPORT_RENDER_TIMEOUT: "export_err_timeout", EXPORT_RENDER_FAILED: "export_err_render_failed",
  };
  const code = e?.code || "";
  const key = statusKeys[e?.status ?? 0] || codeKeys[code] || "export_err_generic";
  const message = t(locale, key);
  const detail = e?.detail || (!code ? e?.message : "");
  return [message, detail, code, e?.requestId && `request_id=${e.requestId}`].filter(Boolean).join(locale === "zh" ? "；" : "; ");
}

export function parseExportFilename(disposition: string | null, fallback: string): string {
  const extended = /(?:^|;)\s*filename\*\s*=\s*UTF-8''([^;]*)/i.exec(disposition || "");
  const plain = /(?:^|;)\s*filename\s*=\s*(?:"((?:\\.|[^"\\])*)"|([^;]*))/i.exec(disposition || "");
  let name = "";
  try { if (extended) name = decodeURIComponent(extended[1].trim()); } catch { /* use filename or fallback */ }
  if (!name && plain) name = (plain[1] ?? plain[2]).replace(/\\(.)/g, "$1").trim();
  // A server-supplied filename is a basename, never a path or control sequence.
  return name && !/[\\/\u0000-\u001f\u007f]/.test(name) && name !== "." && name !== ".." ? name : fallback;
}

function sleep(ms: number, signal: AbortSignal): Promise<void> {
  // Keep the fixed ES2022 target; Promise.withResolvers requires ES2024.
  return new Promise((resolve, reject) => {
    signal.throwIfAborted();
    const abort = () => { clearTimeout(timer); reject(signal.reason); };
    const timer = setTimeout(() => { signal.removeEventListener("abort", abort); resolve(); }, ms);
    signal.addEventListener("abort", abort, { once: true });
  });
}

/** One instance per click. The backend owns pinning; this owns observation only. */
export class ExportJob {
  readonly input: ExportInput;
  readonly key: string;
  readonly controller = new AbortController();
  id: string | null = null;
  private api: ExportApi;
  private changed: (state: ExportState) => void;
  private options: { maxPolls?: number; initialDelay?: number; maxDelay?: number; sleep?: typeof sleep; uuid?: () => string };
  private warnings: string[] = [];

  constructor(snapshotId: string, format: ExportFormat, state: PresentationState,
    api: ExportApi, changed: (state: ExportState) => void, options: ExportJob["options"] = {}) {
    this.input = { snapshot_id: snapshotId, format, presentation_state: {
      theme: state.theme, report_width_px: state.report_width_px,
      expanded_detail_ids: [...state.expanded_detail_ids], table_sort: { ...state.table_sort },
      preview_row_sets: { ...state.preview_row_sets }, panel_order: [...state.panel_order],
      legend_state: { ...state.legend_state }, locale: state.locale,
    } };
    this.key = (options.uuid ?? (() => crypto.randomUUID()))();
    this.api = api;
    this.changed = changed;
    this.options = options;
  }

  stop(): void { this.controller.abort(); }

  async cancel(): Promise<void> {
    this.stop();
    if (this.id) await this.api.deleteExport(this.id, this.key);
  }

  private emit(status: ExportState["status"], message: string): void {
    if (!this.controller.signal.aborted) this.changed({ status, message, warnings: [...this.warnings] });
  }

  async run(): Promise<ExportFile | undefined> {
    const signal = this.controller.signal;
    const wait = this.options.sleep ?? sleep;
    const locale = this.input.presentation_state.locale;
    let delay = this.options.initialDelay ?? 1000;
    try {
      signal.throwIfAborted();
      this.emit("requesting", t(locale, "export_requesting"));
      let accepted;
      // Only a transport failure is retried, once, with the exact same payload/key.
      try { accepted = await this.api.createExport(this.input, this.key, signal); }
      catch (error) {
        signal.throwIfAborted();
        if (!error || typeof error !== "object" || !("status" in error) || error.status !== null) throw error;
        await wait(delay, signal);
        signal.throwIfAborted();
        accepted = await this.api.createExport(this.input, this.key, signal);
      }
      signal.throwIfAborted();
      this.id = accepted.export_id;
      this.warnings = accepted.warnings ?? [];
      this.emit("queued", t(locale, "export_queued"));
      for (let poll = 0; poll < (this.options.maxPolls ?? 40); poll++) {
        signal.throwIfAborted();
        try {
          const status = await this.api.getExport(this.id, signal);
          signal.throwIfAborted();
          this.warnings = [...new Set([...this.warnings, ...(status.warnings ?? [])])];
          if (status.status === "ready") {
            const file = await this.api.downloadExport(this.id, this.input.format, signal);
            signal.throwIfAborted();
            this.emit("ready", t(locale, "export_ready"));
            return file;
          }
          if (status.status === "failed" || status.status === "cancelled") {
            this.emit(status.status, status.status === "cancelled" ? t(locale, "export_cancelled") : exportErrorMessage({ code: status.error }, locale));
            return;
          }
          this.emit(status.status, status.status === "queued" ? t(locale, "export_queued") : t(locale, "export_generating"));
        } catch (error) {
          if (!error || typeof error !== "object" || !("status" in error) || error.status !== 409) throw error;
          this.emit("generating", exportErrorMessage(error, locale));
        }
        if (poll + 1 < (this.options.maxPolls ?? 40)) {
          await wait(delay, signal);
          delay = Math.min(delay * 1.5, this.options.maxDelay ?? 5000);
        }
      }
      this.emit("failed", t(locale, "export_wait_timeout"));
    } catch (error) {
      if (!signal.aborted) this.emit("failed", exportErrorMessage(error, locale));
    }
  }
}
