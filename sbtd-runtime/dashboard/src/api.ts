/*
 * Real /api/v1 client (contracts/openapi.yaml). No mocked or hardcoded
 * numbers: every value rendered by the page comes from these endpoints.
 * When the service is unreachable or the session is missing, callers get a
 * typed failure and panels render their declared error / insufficient-data
 * states (§12.5) — never a 0 or a fabricated number.
 *
 * Session note: the Bearer token and CSRF token are read from
 * sessionStorage, where the pairing flow (PR-2, D7) stores them after
 * exchanging the one-time #ticket. PR-1 ships no pairing UI.
 */

import type { Snapshot } from "./reportDocument";

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

export class ApiError extends Error {
  readonly status: number | null;
  constructor(message: string, status: number | null) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const session = readSession();
  const headers: Record<string, string> = {};
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
    });
  } catch (error) {
    throw new ApiError(`network error: ${String(error)}`, null);
  }
  if (!response.ok) {
    throw new ApiError(`${method} ${path} -> ${response.status}`, response.status);
  }
  return (await response.json()) as T;
}

/** QueryScope schema_version 1.0 (ADR 0001 / test_r1_acceptance pins). */
export interface QueryScope {
  schema_version: "1.0";
  from: string;
  to: string;
  timezone: string;
  task_granularity?: string;
  include_unlinked?: boolean;
  include_unknown_time?: boolean;
  task_uids?: string[];
  filters?: Record<string, string[]>;
}

export function defaultScope24h(now: Date = new Date()): QueryScope {
  const to = now;
  const from = new Date(now.getTime() - 24 * 3600 * 1000);
  return {
    schema_version: "1.0",
    from: from.toISOString(),
    to: to.toISOString(),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  };
}

export interface Health {
  status: string;
  [key: string]: unknown;
}

export function fetchHealth(): Promise<Health> {
  return request<Health>("GET", "/api/v1/health");
}

/** POST /api/v1/report-snapshots → 201 with Snapshot public view. */
export function createReportSnapshot(scope: QueryScope): Promise<Snapshot> {
  return request<Snapshot>("POST", "/api/v1/report-snapshots", { scope });
}

/** POST /api/v1/statistics/query — metric values keyed by metric_id. */
export interface StatisticsResult {
  metrics: Record<string, unknown>;
  meta?: Record<string, unknown>;
}

export function queryStatistics(scope: QueryScope): Promise<StatisticsResult> {
  return request<StatisticsResult>("POST", "/api/v1/statistics/query", scope);
}
