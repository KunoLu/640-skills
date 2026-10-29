/*
 * Real /api/v1 client (contracts/openapi.yaml). No mocked or hardcoded
 * numbers: every value rendered by the page comes from these endpoints.
 * When the service is unreachable or the session is missing, callers get a
 * typed failure and panels render their declared error / insufficient-data
 * states (§12.5) — never a 0 or a fabricated number.
 *
 * Pairing (D7): the launcher opens the page with a one-time ticket in the
 * URL fragment (`#ticket=…`). pairWithTicket exchanges it via the
 * X-Pairing-Code header (openapi.yaml pairingCode security scheme) for a
 * short-lived session Bearer plus a CSRF token (returned in the X-CSRF-Token
 * response header, since the Session schema carries only
 * token_type/access_token/expires_in). Both tokens live in sessionStorage;
 * the fragment is removed from the address bar and history immediately
 * (PRD §10.2). The ticket value itself is never logged or displayed.
 */

import type { Snapshot } from "./reportDocument";
import { parseExportFilename, type ExportFile, type ExportFormat, type ExportInput, type ExportStatus } from "./exportJob.ts";
import { DEFAULT_LOCALE, t, type Locale } from "./i18n.ts";

const SESSION_KEY = "sbtd.session";

export interface SessionCredentials {
  bearer: string;
  csrf: string;
}

export function readSession(): SessionCredentials | null {
  const raw = sessionStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as SessionCredentials;
    if (typeof parsed.bearer === "string" && typeof parsed.csrf === "string") {
      return parsed;
    }
  } catch {
    /* fall through */
  }
  return null;
}

/** Extract the one-time pairing ticket from the URL fragment, if present. */
export function readTicketFromFragment(): string | null {
  const match = /^#ticket=([A-Za-z0-9_-]+)$/.exec(window.location.hash);
  return match ? match[1] : null;
}

/**
 * Remove the ticket fragment from the address bar and browser history
 * (PRD §10.2: 读取后立即移除并销毁). Called before the pair exchange so the
 * ticket never survives navigation or history inspection.
 */
export function clearTicketFromAddressBar(): void {
  window.history.replaceState(null, "", window.location.pathname);
}

/**
 * POST /api/v1/session/pair: exchange the one-time ticket for a session
 * (openapi.yaml pairSession; the server destroys the ticket on read, so a
 * failed exchange also consumes it). On success the credentials are stored
 * in sessionStorage and returned.
 */
export async function pairWithTicket(
  ticket: string,
  locale: Locale = DEFAULT_LOCALE,
): Promise<SessionCredentials> {
  let response: Response;
  try {
    response = await fetch("/api/v1/session/pair", {
      method: "POST",
      headers: { "X-Pairing-Code": ticket },
    });
  } catch (error) {
    throw new ApiError(`network error: ${String(error)}`, null);
  }
  if (!response.ok) {
    throw new ApiError(
      `POST /api/v1/session/pair -> ${response.status}${locale === "zh" ? "（" : " ("}${t(locale, "pair_failed")}${locale === "zh" ? "）" : ")"}`,
      response.status,
    );
  }
  const session = (await response.json()) as {
    token_type?: unknown;
    access_token?: unknown;
    expires_in?: unknown;
  };
  const csrf = response.headers.get("X-CSRF-Token");
  if (
    session.token_type !== "bearer" ||
    typeof session.access_token !== "string" ||
    typeof session.expires_in !== "number" ||
    !csrf
  ) {
    throw new ApiError("POST /api/v1/session/pair: malformed session", null);
  }
  const credentials: SessionCredentials = { bearer: session.access_token, csrf };
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(credentials));
  return credentials;
}

export class ApiError extends Error {
  readonly status: number | null;
  readonly detail: string;
  readonly code: string;
  readonly requestId: string;
  constructor(message: string, status: number | null, detail = "", code = "", requestId = "") {
    super(message);
    this.status = status;
    this.detail = detail;
    this.code = code;
    this.requestId = requestId;
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  extraHeaders?: Record<string, string>,
  signal?: AbortSignal,
  binary = false,
): Promise<T> {
  const session = readSession();
  const headers: Record<string, string> = { ...extraHeaders };
  if (session) {
    headers["Authorization"] = `Bearer ${session.bearer}`;
    if (method !== "GET") headers["X-CSRF-Token"] = session.csrf;
  }
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let response: Response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (error) {
    signal?.throwIfAborted();
    throw new ApiError(`network error: ${String(error)}`, null);
  }
  if (!response.ok) {
    let detail = "", code = "", requestId = "";
    try {
      const payload = await response.json();
      if (payload && typeof payload === "object") {
        const parts: string[] = [];
        if (typeof payload.detail === "string") parts.push(payload.detail);
        if (typeof payload.error?.code === "string") code = payload.error.code;
        if (typeof payload.request_id === "string") requestId = payload.request_id;
        for (const key of ["max_edge_px", "max_total_pixels", "used_bytes", "quota_bytes"]) {
          if (typeof payload[key] === "number") parts.push(`${key}=${payload[key]}`);
        }
        if (Array.isArray(payload.meta?.warnings)) parts.push(`warnings=${payload.meta.warnings.join(",")}`);
        detail = parts.join("; ");
      }
    } catch {
      /* Non-JSON errors still retain their HTTP status. */
    }
    throw new ApiError(
      `${method} ${path} -> ${response.status} ${detail} ${code} ${requestId}`.trim(),
      response.status, detail, code, requestId,
    );
  }
  if (binary) return response as T;
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

interface Envelope<T> {
  api_version: "1";
  request_id: string;
  data: T;
  /** openapi.yaml Meta schema; only warnings is consumed today. */
  meta: { warnings?: string[] };
}

/**
 * Unwrap the versioned response Envelope (openapi.yaml Envelope schema) and
 * return its data. Non-fatal envelope warnings are surfaced on the console;
 * a malformed envelope is an error, never silently treated as empty data.
 */
function unwrapEnvelope<T>(payload: unknown, path: string): T {
  const envelope = payload as Partial<Envelope<T>> | null;
  if (
    envelope === null ||
    typeof envelope !== "object" ||
    envelope.api_version !== "1" ||
    typeof envelope.request_id !== "string" ||
    !("data" in envelope) ||
    envelope.meta === null ||
    typeof envelope.meta !== "object"
  ) {
    throw new ApiError(`${path}: malformed response envelope`, null);
  }
  const warnings = envelope.meta.warnings;
  if (Array.isArray(warnings) && warnings.length > 0) {
    console.warn(`${path}: envelope warnings`, warnings);
  }
  return envelope.data as T;
}

/**
 * QueryScope per contracts/openapi.yaml #/components/schemas/QueryScope
 * (schema_version 1.0; ADR 0001 / test_r1_acceptance pins). The schema is
 * additionalProperties: false with required [schema_version, range, metrics];
 * every optional field below is the full optional set. Field names and
 * nesting must match the contract exactly — no flat from/to, no task_uids.
 */
export interface QueryScopeRange {
  from: string;
  to: string;
  timezone: string;
}

export interface QueryScope {
  schema_version: "1.0";
  range: QueryScopeRange;
  metrics: string[];
  filters?: Record<string, string[]>;
  task_granularity?: "executable-leaf" | "all";
  include_unlinked?: boolean;
  include_unknown_time?: boolean;
}

export function defaultScope24h(
  metrics: string[],
  now: Date = new Date(),
): QueryScope {
  const to = now;
  const from = new Date(now.getTime() - 24 * 3600 * 1000);
  return {
    schema_version: "1.0",
    range: {
      from: from.toISOString(),
      to: to.toISOString(),
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
    },
    metrics: [...metrics],
  };
}

export interface Health {
  status: string;
  [key: string]: unknown;
}

export function fetchHealth(): Promise<Health> {
  // /api/v1/health answers with the bare Health schema, not an Envelope.
  return request<Health>("GET", "/api/v1/health");
}

/**
 * GET /api/v1/report-snapshots/{snapshot_id} → 200 Envelope whose data is
 * the Snapshot public view (report_snapshot.Snapshot.public_view). The
 * snapshot id comes from the statistics query response: the server attaches
 * a SnapshotStore to stats_query.query, which mints-or-reuses the snapshot
 * for the queried scope. openapi.yaml defines no requestBody for POST
 * /api/v1/report-snapshots, so the client never posts a scope there — the
 * query is the only scope-carrying call.
 */
export function fetchReportSnapshot(snapshotId: string): Promise<Snapshot> {
  const path = `/api/v1/report-snapshots/${encodeURIComponent(snapshotId)}`;
  return request<Envelope<Snapshot>>("GET", path).then((envelope) =>
    unwrapEnvelope<Snapshot>(envelope, path),
  );
}

/**
 * POST /api/v1/statistics/query → 200 Envelope whose data carries metric
 * values keyed by metric_id (stats_query.query over contract_eval.evaluate).
 * Returns 507 with {detail: "DISK_QUOTA_EXCEEDED", used_bytes, quota_bytes}
 * when a required new snapshot is refused by the shared snapshots/ + exports/
 * quota after sweeping (used_bytes > quota_bytes; both integers).
 * Matching unexpired snapshot reuse remains 200; invalid scope remains 400.
 */

/** Stratified rate entry (e.g. validations.run_pass_rate strata). */
export interface MetricStratum {
  /** "n/d" when decidable, null when the stratum has no decidable sample. */
  value: unknown;
  sample_status?: string;
  [key: string]: unknown;
}

/** Metric value shape returned by evaluate(): value plus support metadata. */
export interface MetricValue {
  metric_id: string;
  /** supported | conditional | unsupported (metrics-catalog support field). */
  support: string;
  /** null when the metric is unsupported or has insufficient data. */
  value: unknown;
  /** Present on unsupported / conditional metrics: why no value. */
  reason?: string;
  /** Present on conditional cost metrics: why the value is missing. */
  missing_reason?: string;
  /** true when part of the sample is missing (conditional metrics). */
  missing?: boolean;
  /** decidable | no-decidable-sample (rate metrics). */
  sample_status?: string;
  /** Per-stratum rate results; top-level value may be null while these carry data. */
  strata?: Record<string, MetricStratum>;
  [key: string]: unknown;
}

export interface StatisticsResult {
  metrics: Record<string, MetricValue>;
  /** Attached by the server-side SnapshotStore (stats_query._attach_snapshot). */
  snapshot_id?: string;
  meta?: Record<string, unknown>;
  [key: string]: unknown;
}

export function queryStatistics(scope: QueryScope): Promise<StatisticsResult> {
  return request<Envelope<StatisticsResult>>(
    "POST",
    "/api/v1/statistics/query",
    scope,
  ).then((envelope) => unwrapEnvelope<StatisticsResult>(envelope, "/api/v1/statistics/query"));
}

/**
 * One dataset row (report_snapshot dataset family row): a typed record with
 * a stable id and a flat field bag. Rows power the inline detail views
 * (§12.4 task-audit-detail); they are page-level previews, never a
 * substitute for the CSV export (§12.6).
 */
export interface DatasetRow {
  record_type: string;
  record_id: string;
  relation_role: string;
  fields: Record<string, unknown>;
}

export interface DatasetPage {
  snapshot_id: string;
  rows: DatasetRow[];
  next_cursor: string | null;
  total: number;
}

/**
 * GET /api/v1/report-snapshots/{snapshot_id}/dataset?cursor=… → one page of
 * the snapshot's immutable dataset (report_snapshot.SnapshotStore.dataset_page).
 */
export function fetchSnapshotDatasetPage(
  snapshotId: string,
  cursor: string | null = null,
): Promise<DatasetPage> {
  const base = `/api/v1/report-snapshots/${encodeURIComponent(snapshotId)}/dataset`;
  const path = cursor === null ? base : `${base}?cursor=${encodeURIComponent(cursor)}`;
  return request<Envelope<DatasetPage>>("GET", path).then((envelope) =>
    unwrapEnvelope<DatasetPage>(envelope, path),
  );
}

export interface DatasetRows {
  rows: DatasetRow[];
  /** Server-declared total rows in the snapshot (all families). */
  total: number;
  /** True when the page cap stopped the walk before the last page. */
  truncated: boolean;
}

/**
 * Walk every dataset page of a snapshot. Every page must answer with the
 * requested snapshot_id — a mismatch means the server mixed snapshots,
 * which would break the single-snapshot guarantee (§12.5) and is an error,
 * never silently stitched together. The walk is capped (default 100 pages ×
 * server page size); hitting the cap sets `truncated` so the UI can say so
 * honestly instead of implying completeness.
 */
export async function fetchAllSnapshotRows(
  snapshotId: string,
  maxPages = 100,
): Promise<DatasetRows> {
  const rows: DatasetRow[] = [];
  let cursor: string | null = null;
  let total = 0;
  for (let page = 0; page < maxPages; page += 1) {
    const result: DatasetPage = await fetchSnapshotDatasetPage(snapshotId, cursor);
    if (result.snapshot_id !== snapshotId) {
      throw new ApiError(
        `dataset page answered with ${result.snapshot_id}, expected ${snapshotId}`,
        null,
      );
    }
    rows.push(...result.rows);
    total = result.total;
    if (result.next_cursor === null) {
      return { rows, total, truncated: false };
    }
    cursor = result.next_cursor;
  }
  return { rows, total, truncated: true };
}

export interface ExportCapabilities {
  exports: Record<ExportFormat, { available: boolean; reason: string | null }>;
}

export async function getCapabilities(signal?: AbortSignal): Promise<ExportCapabilities> {
  const path = "/api/v1/capabilities";
  return unwrapEnvelope(await request("GET", path, undefined, undefined, signal), path);
}

export async function createExport(input: ExportInput, key: string, signal: AbortSignal) {
  const path = "/api/v1/exports";
  const envelope = await request<Envelope<{ export_id: string }>>("POST", path, input, { "Idempotency-Key": key }, signal);
  return { ...unwrapEnvelope<{ export_id: string }>(envelope, path), warnings: envelope.meta.warnings };
}

export async function getExport(id: string, signal: AbortSignal): Promise<ExportStatus> {
  const path = `/api/v1/exports/${encodeURIComponent(id)}`;
  return unwrapEnvelope(await request("GET", path, undefined, undefined, signal), path);
}

export function deleteExport(id: string, key: string): Promise<void> {
  return request("DELETE", `/api/v1/exports/${encodeURIComponent(id)}`, undefined, { "Idempotency-Key": key });
}

export async function downloadExport(id: string, format: ExportFormat, signal: AbortSignal): Promise<ExportFile> {
  const response = await request<Response>("GET", `/api/v1/exports/${encodeURIComponent(id)}/file`, undefined, undefined, signal, true);
  return {
    blob: await response.blob(),
    filename: parseExportFilename(response.headers.get("Content-Disposition"), `sbtd-report_${id}.${format}`),
  };
}
