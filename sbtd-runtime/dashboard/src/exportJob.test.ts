import { test } from "node:test";
import assert from "node:assert/strict";
import { ExportJob, exportErrorMessage, parseExportFilename } from "./exportJob.ts";
import type { ExportApi, ExportState, ExportStatus } from "./exportJob.ts";
import { ApiError, createExport, getExport, deleteExport, downloadExport, getCapabilities } from "./api.ts";
import type { PresentationState } from "./reportDocument.ts";

const presentation = (): PresentationState => ({
  theme: "light", report_width_px: 1440, expanded_detail_ids: ["task_a"],
  table_sort: { tasks: "name" }, preview_row_sets: { tasks: 10 },
  panel_order: ["tasks"], legend_state: { total: false }, locale: "zh",
});
function harness(statuses: ExportStatus["status"][] = ["queued", "generating", "ready"]) {
  const seen: ExportState[] = [], delays: number[] = [];
  let reads = 0, downloads = 0;
  const api: ExportApi = {
    createExport: async () => ({ export_id: "exp_a", warnings: ["EXPORT_SCALE_DOWNGRADED:1x"] }),
    getExport: async () => ({ status: statuses[Math.min(reads++, statuses.length - 1)], error: null }),
    deleteExport: async () => {},
    downloadExport: async () => { downloads++; return { blob: new Blob(["report"]), filename: "report.html" }; },
  };
  const job = () => new ExportJob("snap_a", "html", presentation(), api, s => seen.push(s), {
    uuid: () => "key_a", sleep: async ms => { delays.push(ms); }, maxPolls: 5,
  });
  return { api, seen, delays, job, reads: () => reads, downloads: () => downloads };
}

test("queued and generating reach ready with one file and retained warnings", async () => {
  const h = harness();
  const file = await h.job().run();
  assert.equal(await file?.blob.text(), "report");
  assert.equal(file?.filename, "report.html");
  assert.deepEqual(h.seen.map(s => s.status), ["requesting", "queued", "queued", "generating", "ready"]);
  assert.deepEqual(h.seen.at(-1)?.warnings, ["EXPORT_SCALE_DOWNGRADED:1x"]);
  assert.equal(h.downloads(), 1);
});

test("failed and cancelled are terminal and never download", async () => {
  for (const status of ["failed", "cancelled"] as const) {
    const h = harness([status]);
    h.api.getExport = async () => ({ status, error: status === "failed" ? "EXPORT_RENDER_TIMEOUT" : null });
    assert.equal(await h.job().run(), undefined);
    assert.equal(h.seen.at(-1)?.status, status);
    assert.match(h.seen.at(-1)!.message, status === "failed" ? /渲染超时/ : /已取消/);
    assert.equal(h.reads(), 0);
    assert.equal(h.downloads(), 0);
  }
});

test("polling stops at its cap with exponential backoff capped at five seconds", async () => {
  const h = harness(["generating"]);
  const job = new ExportJob("snap_a", "pdf", presentation(), h.api, s => h.seen.push(s), {
    maxPolls: 7, sleep: async ms => { h.delays.push(ms); },
  });
  await job.run();
  assert.equal(h.reads(), 7);
  assert.deepEqual(h.delays, [1000, 1500, 2250, 3375, 5000, 5000]);
  assert.equal(h.seen.at(-1)?.status, "failed");
  assert.match(h.seen.at(-1)!.message, /等待超时/);
  assert.equal(h.downloads(), 0);
});

test("cancelling aborts polling, sends DELETE, and ignores a late ready response", async () => {
  const h = harness();
  let resolve!: (s: ExportStatus) => void;
  const late = new Promise<ExportStatus>(r => { resolve = r; });
  const deleted: string[] = [];
  let signal: AbortSignal | undefined;
  h.api.getExport = async (_id, s) => { signal = s; return late; };
  h.api.deleteExport = async (id, key) => { deleted.push(id, key); };
  const job = h.job();
  const running = job.run();
  await Promise.resolve();
  const before = [...h.seen];
  await job.cancel();
  resolve({ status: "ready", error: null });
  await running;
  assert.equal(signal?.aborted, true);
  assert.deepEqual(deleted, ["exp_a", "key_a"]);
  assert.deepEqual(h.seen, before);
  assert.equal(h.downloads(), 0);
});

test("stopping during backoff prevents another request or stale UI write", async () => {
  const h = harness(["queued"]);
  const job = new ExportJob("snap_a", "csv", presentation(), h.api, s => h.seen.push(s), {
    sleep: async () => { job.stop(); },
  });
  await job.run();
  assert.equal(h.reads(), 1);
  assert.equal(h.seen.at(-1)?.status, "queued");
  assert.equal(h.downloads(), 0);
});

test("new clicks use new keys; transport retry and polls retain the clicked snapshot and seven fields", async () => {
  const h = harness(["ready"]);
  const state = presentation();
  let snapshot = "snap_old", sequence = 0;
  const inputs: { snapshot: string; key: string; theme: string }[] = [];
  h.api.createExport = async (input, key) => {
    inputs.push({ snapshot: input.snapshot_id, key, theme: input.presentation_state.theme });
    if (inputs.length === 1) throw new ApiError("connection lost", null);
    return { export_id: "exp_a" };
  };
  const options = { uuid: () => `key_${++sequence}`, sleep: async () => {} };
  const first = new ExportJob(snapshot, "html", state, h.api, () => {}, options);
  snapshot = "snap_new";
  state.theme = "dark";
  state.expanded_detail_ids.push("task_new");
  state.table_sort.tasks = "date";
  state.preview_row_sets.tasks = 50;
  state.panel_order.push("quality");
  state.legend_state.total = true;
  await first.run();
  const second = new ExportJob(snapshot, "html", state, h.api, () => {}, options);
  await second.run();
  assert.deepEqual(inputs, [
    { snapshot: "snap_old", key: "key_1", theme: "light" },
    { snapshot: "snap_old", key: "key_1", theme: "light" },
    { snapshot: "snap_new", key: "key_2", theme: "dark" },
  ]);
  assert.equal(sequence, 2);
  assert.deepEqual(first.input.presentation_state, presentation());
  assert.deepEqual(Object.keys(first.input.presentation_state).sort(), [
    "expanded_detail_ids", "legend_state", "locale", "panel_order", "preview_row_sets", "report_width_px", "table_sort", "theme",
  ]);
  assert.equal(h.reads(), 2);
});

test("a newer click cannot receive an older creation or download response", async () => {
  for (const stage of ["create", "download"]) {
    const h = harness(["ready"]);
    let release!: () => void;
    const held = new Promise<void>(r => { release = r; });
    if (stage === "create") h.api.createExport = async () => { await held; return { export_id: "exp_old" }; };
    else h.api.downloadExport = async () => { await held; return { blob: new Blob(["old"]), filename: "old.csv" }; };
    const old = h.job();
    const running = old.run();
    await Promise.resolve();
    await Promise.resolve();
    old.stop();
    const before = h.seen.length;
    const newer = harness(["ready"]);
    assert.equal((await newer.job().run())?.filename, "report.html");
    release();
    assert.equal(await running, undefined);
    assert.equal(h.seen.length, before);
  }
});

test("401 stops immediately; other fatal HTTP errors do not retry or download", async () => {
  for (const status of [401, 400, 404, 410, 422, 503, 507]) {
    const h = harness();
    let reads = 0;
    h.api.getExport = async () => { reads++; throw new ApiError("HTTP failure", status, "original detail"); };
    await h.job().run();
    assert.equal(reads, 1);
    assert.equal(h.downloads(), 0);
    assert.equal(h.seen.at(-1)?.status, "failed");
    assert.match(h.seen.at(-1)!.message, /original detail/);
    if (status === 401) assert.match(h.seen.at(-1)!.message, /会话已过期，请重启 serve 并重新配对/);
  }
});

test("409 from polling or file download waits and eventually downloads once", async () => {
  for (const stage of ["poll", "file"]) {
    const h = harness(["ready"]);
    const original = stage === "poll" ? h.api.getExport : h.api.downloadExport;
    let attempts = 0;
    if (stage === "poll") h.api.getExport = async () => {
      if (++attempts === 1) throw new ApiError("not ready", 409);
      return { status: "ready", error: null };
    };
    else h.api.downloadExport = async (id, format, signal) => {
      if (++attempts === 1) throw new ApiError("not ready", 409);
      return (original as ExportApi["downloadExport"])(id, format, signal);
    };
    await h.job().run();
    assert.equal(attempts, 2);
    assert.ok(h.seen.some(s => s.status === "generating" && s.message.includes("未就绪")));
    assert.equal(h.seen.at(-1)?.status, "ready");
    assert.equal(h.downloads(), 1);
    assert.deepEqual(h.delays, [1000]);
  }
});

test("error mappings preserve detail, failure code, and request id", () => {
  const messages = new Map([
    [401, "会话已过期，请重启 serve 并重新配对"], [400, "导出请求无效"], [404, "不存在"],
    [409, "未就绪"], [410, "已过期"], [422, "尺寸超限"], [503, "renderer 不可用"], [507, "磁盘配额不足"],
  ]);
  for (const [status, message] of messages) {
    const text = exportErrorMessage(new ApiError("error", status, "raw max_edge_px=100", "", "req_a"), "zh");
    assert.ok(text.includes(message));
    assert.match(text, /raw max_edge_px=100/);
    assert.match(text, /request_id=req_a/);
  }
  for (const [code, message] of [["EXPORT_RENDER_TIMEOUT", "渲染超时"], ["EXPORT_RENDER_FAILED", "渲染失败"], ["FUTURE_ERROR", "导出失败"]]) {
    const text = exportErrorMessage({ code }, "zh");
    assert.ok(text.includes(message));
    assert.ok(text.includes(code));
  }
});

test("Content-Disposition supports UTF-8, quoted, bare, malformed, and unsafe names", () => {
  for (const [header, expected] of [
    ["attachment; filename*=UTF-8''%E6%8A%A5%E5%91%8A.pdf; filename=fallback.pdf", "报告.pdf"],
    ['attachment; filename=\"report; final.csv\"', "report; final.csv"],
    ["attachment; filename=report.html", "report.html"],
    ["attachment; filename*=UTF-8''%ZZ; filename=backup.pdf", "backup.pdf"],
    ["attachment; filename*=UTF-8''%0Abad", "fallback"],
    ['attachment; filename=\"../private\"', "fallback"],
    ['attachment; filename=\"\"', "fallback"], ["attachment", "fallback"],
  ]) assert.equal(parseExportFilename(header, "fallback"), expected);
  assert.equal(parseExportFilename(null, "fallback"), "fallback");
});

test("API authentication, 204 cancellation, binary download and both error body shapes", async t => {
  const prior = Object.getOwnPropertyDescriptor(globalThis, "sessionStorage");
  Object.defineProperty(globalThis, "sessionStorage", { configurable: true, value: {
    getItem: () => JSON.stringify({ bearer: "test-session", csrf: "test-csrf" }),
  } });
  t.after(() => {
    if (prior) Object.defineProperty(globalThis, "sessionStorage", prior);
    else Reflect.deleteProperty(globalThis, "sessionStorage");
  });
  const requests: { path: string; method: string; headers: Headers; body?: string }[] = [];
  let response = new Response();
  t.mock.method(globalThis, "fetch", async (path: string, init: RequestInit) => {
    requests.push({ path, method: init.method!, headers: new Headers(init.headers), body: init.body as string });
    return response;
  });
  const envelope = (data: unknown, warnings: string[] = []) => new Response(JSON.stringify({
    api_version: "1", request_id: "req_a", data, meta: { warnings },
  }));
  const signal = new AbortController().signal;
  response = envelope({ exports: { jpeg: { available: false, reason: "missing renderer" } } });
  assert.equal((await getCapabilities(signal)).exports.jpeg.reason, "missing renderer");
  response = envelope({ export_id: "exp_a" }, ["EXPORT_SCALE_DOWNGRADED:1x"]);
  const input = { snapshot_id: "snap_a", format: "jpeg" as const, presentation_state: presentation() };
  assert.deepEqual(await createExport(input, "click-key", signal), { export_id: "exp_a", warnings: ["EXPORT_SCALE_DOWNGRADED:1x"] });
  response = envelope({ status: "ready", error: null });
  assert.equal((await getExport("exp_a", signal)).status, "ready");
  response = new Response("binary-data", { headers: { "Content-Disposition": "attachment; filename*=UTF-8''report.jpeg" } });
  const file = await downloadExport("exp_a", "jpeg", signal);
  assert.equal(await file.blob.text(), "binary-data");
  assert.equal(file.filename, "report.jpeg");
  response = new Response(null, { status: 204 });
  await deleteExport("exp_a", "click-key");
  assert.deepEqual(requests.map(r => [r.method, r.path]), [
    ["GET", "/api/v1/capabilities"], ["POST", "/api/v1/exports"], ["GET", "/api/v1/exports/exp_a"],
    ["GET", "/api/v1/exports/exp_a/file"], ["DELETE", "/api/v1/exports/exp_a"],
  ]);
  for (const r of requests) {
    assert.equal(r.headers.get("Authorization"), "Bearer test-session");
    assert.equal(r.headers.get("X-CSRF-Token"), r.method === "GET" ? null : "test-csrf");
    if (r.method !== "GET") assert.equal(r.headers.get("Idempotency-Key"), "click-key");
  }
  assert.deepEqual(JSON.parse(requests[1].body!), input);
  for (const status of [422, 503, 507]) {
    response = new Response(JSON.stringify({ detail: "raw detail", max_edge_px: 123 }), { status });
    await assert.rejects(getExport("exp_a", signal), e =>
      e instanceof ApiError && e.status === status && e.detail.includes("raw detail") && e.detail.includes("max_edge_px=123"));
  }
  response = new Response(JSON.stringify({ error: { code: "FUTURE_ERROR" }, request_id: "req_failure" }), { status: 400 });
  await assert.rejects(downloadExport("exp_a", "pdf", signal), e =>
    e instanceof ApiError && e.code === "FUTURE_ERROR" && e.requestId === "req_failure" && e.status === 400);
});
