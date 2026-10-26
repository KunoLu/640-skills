import type { PresentationState } from "./reportDocument.ts";

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

export function exportErrorMessage(error: unknown): string {
  const e = error as { status?: number; detail?: string; code?: string; requestId?: string; message?: string } | null;
  const messages: Record<number, string> = {
    401: "会话已过期，请重启 serve 并重新配对", 400: "导出请求无效",
    404: "快照或导出不存在", 409: "未就绪，请稍候", 410: "快照或导出已过期，请刷新后重新导出",
    422: "导出尺寸超限", 503: "renderer 不可用", 507: "磁盘配额不足",
  };
  const codes: Record<string, string> = {
    EXPORT_RENDER_TIMEOUT: "导出渲染超时", EXPORT_RENDER_FAILED: "导出渲染失败",
  };
  const code = e?.code || "";
  const message = messages[e?.status ?? 0] || codes[code] || "导出失败";
  const detail = e?.detail || (!code ? e?.message : "");
  return [message, detail, code, e?.requestId && `request_id=${e.requestId}`].filter(Boolean).join("；");
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
      legend_state: { ...state.legend_state },
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
    let delay = this.options.initialDelay ?? 1000;
    try {
      signal.throwIfAborted();
      this.emit("requesting", "正在创建导出");
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
      this.emit("queued", "导出已排队");
      for (let poll = 0; poll < (this.options.maxPolls ?? 40); poll++) {
        signal.throwIfAborted();
        try {
          const status = await this.api.getExport(this.id, signal);
          signal.throwIfAborted();
          this.warnings = [...new Set([...this.warnings, ...(status.warnings ?? [])])];
          if (status.status === "ready") {
            const file = await this.api.downloadExport(this.id, this.input.format, signal);
            signal.throwIfAborted();
            this.emit("ready", "导出已就绪，开始下载");
            return file;
          }
          if (status.status === "failed" || status.status === "cancelled") {
            this.emit(status.status, status.status === "cancelled" ? "导出已取消" : exportErrorMessage({ code: status.error }));
            return;
          }
          this.emit(status.status, status.status === "queued" ? "导出已排队" : "正在生成导出");
        } catch (error) {
          if (!error || typeof error !== "object" || !("status" in error) || error.status !== 409) throw error;
          this.emit("generating", exportErrorMessage(error));
        }
        if (poll + 1 < (this.options.maxPolls ?? 40)) {
          await wait(delay, signal);
          delay = Math.min(delay * 1.5, this.options.maxDelay ?? 5000);
        }
      }
      this.emit("failed", "导出等待超时，已停止轮询；可取消该作业或重新导出");
    } catch (error) {
      if (!signal.aborted) this.emit("failed", exportErrorMessage(error));
    }
  }
}
