import { test, type TestContext } from "node:test";
import assert from "node:assert/strict";
import { getCapabilities, getExport, readSession } from "./api.ts";
import type * as Api from "./api.ts";

const envelope = (data: unknown) => Response.json({ api_version: "1", request_id: "req_test", data, meta: {} });

test("concurrent protected 401s share one exchange and replay with the new session", async t => {
  const prior = Object.getOwnPropertyDescriptor(globalThis, "sessionStorage");
  const store = new Map([["sbtd.session", JSON.stringify({ bearer: "old", csrf: "old-csrf" })]]);
  const writes: string[] = [];
  Object.defineProperty(globalThis, "sessionStorage", { configurable: true, value: {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => { writes.push(value); store.set(key, value); },
    removeItem: (key: string) => store.delete(key),
  } });
  t.after(() => {
    if (prior) Object.defineProperty(globalThis, "sessionStorage", prior);
    else Reflect.deleteProperty(globalThis, "sessionStorage");
  });
  let tickets = 0, pairs = 0, replays = 0;
  t.mock.method(globalThis, "fetch", async (path: string, init: RequestInit) => {
    const headers = new Headers(init.headers);
    if (path.endsWith("/re-pair-ticket")) {
      tickets++;
      assert.equal(store.has("sbtd.session"), false);
      assert.equal(headers.get("Authorization"), "Bearer old");
      assert.equal(headers.get("X-CSRF-Token"), "old-csrf");
      assert.equal(init.body, undefined);
      return Response.json({ pairing_code: "recovery-only-in-memory", ttl_seconds: 30, expires_at: new Date(Date.now() + 30000).toISOString() });
    }
    if (path.endsWith("/pair")) {
      pairs++;
      assert.equal(headers.get("X-Pairing-Code"), "recovery-only-in-memory");
      return Response.json({ token_type: "bearer", access_token: "new", expires_in: 28800 }, { headers: { "X-CSRF-Token": "new-csrf" } });
    }
    if (headers.get("Authorization") === "Bearer old") return Response.json({ detail: "unauthorized" }, { status: 401 });
    assert.equal(headers.get("Authorization"), "Bearer new");
    replays++;
    return envelope(path.endsWith("capabilities") ? { exports: {} } : { status: "ready", error: null });
  });
  const [capabilities, job] = await Promise.all([getCapabilities(), getExport("exp_original", new AbortController().signal)]);
  assert.deepEqual(capabilities.exports, {});
  assert.equal(job.status, "ready");
  assert.deepEqual([tickets, pairs, replays, writes.length], [1, 1, 2, 1]);
  assert.equal(readSession()?.bearer, "new");
  assert.ok(writes.every(value => !value.includes("recovery-only-in-memory") && !value.includes("old-csrf")));
});

// Each module instance models a separate tab; globals are restored by TestContext.
let tab = 0;
async function fixture(t: TestContext) {
  const api: typeof Api = await import(`./api.ts?tab=${++tab}`);
  const prior = Object.getOwnPropertyDescriptor(globalThis, "sessionStorage");
  const store = new Map([["sbtd.session", JSON.stringify({ bearer: "old", csrf: "old-csrf" })]]);
  const writes: string[] = [];
  Object.defineProperty(globalThis, "sessionStorage", { configurable: true, value: {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => { store.set(key, value); writes.push(value); },
    removeItem: (key: string) => store.delete(key),
  } });
  t.after(() => {
    if (prior) Object.defineProperty(globalThis, "sessionStorage", prior);
    else Reflect.deleteProperty(globalThis, "sessionStorage");
  });
  const calls: { path: string; init: RequestInit }[] = [];
  const h = {
    api, store, writes, calls,
    ticket: async (_init: RequestInit): Promise<Response> => Response.json({
      pairing_code: "memory-ticket", expires_at: new Date(Date.now() + 30_000).toISOString(), ttl_seconds: 30,
    }),
    pair: async (_init: RequestInit): Promise<Response> => Response.json({
      token_type: "bearer", access_token: "new", expires_in: 28800,
    }, { headers: { "X-CSRF-Token": "new-csrf" } }),
    resource: async (_path: string, init: RequestInit): Promise<Response> =>
      new Headers(init.headers).get("Authorization") === "Bearer old"
        ? Response.json({ detail: "unauthorized" }, { status: 401 })
        : envelope({ status: "ready", error: null }),
  };
  t.mock.method(globalThis, "fetch", async (path: string, init: RequestInit) => {
    calls.push({ path, init });
    if (path.endsWith("/re-pair-ticket")) return h.ticket(init);
    if (path.endsWith("/pair")) return h.pair(init);
    return h.resource(path, init);
  });
  return h;
}

// Keep the repository's ES2022 target (withResolvers requires ES2024).
function held<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(r => { resolve = r; });
  return { promise, resolve };
}
const unauthorized = () => Response.json({ detail: "unauthorized" }, { status: 401 });
const signal = () => new AbortController().signal;

test("late old-generation 401 replays without erasing the replacement", async t => {
  const h = await fixture(t);
  const late = held<Response>();
  h.resource = async (path, init) => {
    if (new Headers(init.headers).get("Authorization") === "Bearer old") {
      return path.endsWith("late") ? late.promise : unauthorized();
    }
    return envelope({ status: "ready", error: null });
  };
  const pending = h.api.getExport("late", signal());
  await h.api.getExport("first", signal());
  late.resolve(unauthorized());
  assert.equal((await pending).status, "ready");
  assert.equal(h.writes.length, 1);
  assert.equal(h.calls.filter(c => c.path.endsWith("re-pair-ticket")).length, 1);
  assert.equal(h.api.readSession()?.bearer, "new");
});

test("only authenticated protected 401s recover; health and initial pair never recurse", async t => {
  const h = await fixture(t);
  for (const status of [403, 404, 410]) {
    h.resource = async () => Response.json({ detail: "failure" }, { status });
    await assert.rejects(h.api.getExport("original", signal()), { status });
  }
  h.resource = async () => { throw new TypeError("network"); };
  await assert.rejects(h.api.getCapabilities(), { status: null });
  h.resource = async () => unauthorized();
  await assert.rejects(h.api.fetchHealth(), { status: 401 });
  h.pair = async () => unauthorized();
  await assert.rejects(h.api.pairWithTicket("startup"), { status: 401 });
  h.store.clear();
  await assert.rejects(h.api.getCapabilities(), { status: 401 });
  assert.equal(h.calls.some(c => c.path.endsWith("re-pair-ticket")), false);
});

test("a replayed 401 terminates recovery and blocks further automatic requests", async t => {
  const h = await fixture(t);
  h.resource = async () => unauthorized();
  await assert.rejects(h.api.getExport("original", signal()), { status: 401 });
  const before = h.calls.length;
  await assert.rejects(h.api.getCapabilities(), { status: 401 });
  assert.equal(h.calls.length, before);
  assert.equal(h.api.getRecoveryState(), "manual");
  assert.equal(h.store.size, 0);
  assert.equal(h.calls.filter(c => c.path.endsWith("re-pair-ticket")).length, 1);
  assert.equal(h.calls.filter(c => c.path.endsWith("/original")).length, 2);
});

test("recovery failures and lost responses are never retried or exposed", async t => {
  for (const stage of ["ticket", "pair"] as const) {
    for (const status of [401, 403, 429, 500, null]) {
      await t.test(`${stage} ${status ?? "lost"}`, async t => {
        const h = await fixture(t);
        h[stage] = async () => {
          if (status === null) throw new Error("secret-transport-detail");
          return Response.json({ detail: "secret-server-detail" }, { status });
        };
        await assert.rejects(h.api.getCapabilities(), error => {
          assert.ok(error instanceof h.api.ApiError);
          assert.equal(error.status, 401);
          assert.equal(error.message.includes("secret"), false);
          return true;
        });
        assert.equal(h.writes.length, 0);
        assert.equal(h.store.size, 0);
        assert.equal(h.api.getRecoveryState(), "manual");
        assert.equal(h.calls.filter(c => c.path.endsWith("re-pair-ticket")).length, 1);
        assert.equal(h.calls.filter(c => c.path.endsWith("/pair")).length, stage === "pair" ? 1 : 0);
      });
    }
  }
});

test("recovery pauses newly started requests and one cancelled waiter does not cancel others", async t => {
  const h = await fixture(t);
  const started = held<void>(), release = held<void>();
  let exchangeSignal: AbortSignal | null | undefined;
  const ticket = h.ticket;
  h.ticket = async init => { exchangeSignal = init.signal; started.resolve(); await release.promise; return ticket(init); };
  const controller = new AbortController();
  const cancelled = h.api.getExport("cancelled", controller.signal);
  const rejected = assert.rejects(cancelled, { name: "AbortError" });
  await started.promise;
  const active = h.api.getExport("active", signal());
  assert.equal(h.calls.some(c => c.path.endsWith("/active")), false);
  controller.abort();
  await rejected;
  assert.equal(exchangeSignal?.aborted, false);
  release.resolve();
  assert.equal((await active).status, "ready");
  assert.equal(h.calls.filter(c => c.path.endsWith("/cancelled")).length, 1);
  assert.equal(h.api.readSession()?.bearer, "new");
});

test("last cancelled waiter prevents late pairing success from installing a session", async t => {
  const h = await fixture(t);
  const started = held<void>(), release = held<void>();
  const pair = h.pair;
  h.pair = async init => { started.resolve(); await release.promise; return pair(init); };
  const controller = new AbortController();
  const request = h.api.getExport("original", controller.signal);
  const rejected = assert.rejects(request, { name: "AbortError" });
  await started.promise;
  controller.abort();
  await rejected;
  release.resolve();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.writes.length, 0);
  assert.equal(h.store.size, 0);
  assert.equal(h.calls.filter(c => c.path.endsWith("/original")).length, 1);
});

test("five-second deadline includes the recovery response body", async t => {
  const h = await fixture(t);
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const started = held<void>();
  h.ticket = async init => {
    const body = held<Record<string, unknown>>();
    init.signal!.addEventListener("abort", () => body.resolve({
      pairing_code: "late", ttl_seconds: 30, expires_at: new Date(Date.now() + 30_000).toISOString(),
    }), { once: true });
    started.resolve();
    const response = Response.json({});
    response.json = () => body.promise;
    return response;
  };
  const request = h.api.getCapabilities();
  const rejected = assert.rejects(request, { status: 401 });
  await started.promise;
  t.mock.timers.tick(5000);
  await rejected;
  assert.equal(h.calls.some(c => c.path.endsWith("/pair")), false);
  assert.equal(h.store.size, 0);
});

test("ticket TTL and original window cannot be extended by a slow response", async t => {
  const h = await fixture(t);
  let tick = 0;
  t.mock.method(performance, "now", () => tick);
  const ticket = h.ticket;
  h.ticket = async init => { tick = 30_001; return ticket(init); };
  await assert.rejects(h.api.getCapabilities(), { status: 401 });
  assert.equal(h.calls.some(c => c.path.endsWith("/pair")), false);
  assert.equal(h.store.size, 0);
});

test("an already elapsed client window fails before sending any recovery request", async t => {
  const h = await fixture(t);
  h.store.set("sbtd.session", JSON.stringify({ bearer: "old", csrf: "old-csrf", expiresAt: Date.now() - 60_001 }));
  await assert.rejects(h.api.getCapabilities(), { status: 401 });
  assert.equal(h.calls.length, 1);
});

test("dataset recovery retains snapshot and cursor until the whole view can replace", async t => {
  const h = await fixture(t);
  h.resource = async (path, init) => {
    assert.match(path, /report-snapshots\/snap_original\/dataset/);
    if (!path.includes("?")) return envelope({
      snapshot_id: "snap_original", rows: [{ record_id: "first" }], total: 2, next_cursor: "cursor+original",
    });
    assert.ok(path.endsWith("?cursor=cursor%2Boriginal"));
    if (new Headers(init.headers).get("Authorization") === "Bearer old") return unauthorized();
    return envelope({ snapshot_id: "snap_original", rows: [{ record_id: "second" }], total: 2, next_cursor: null });
  };
  const result = await h.api.fetchAllSnapshotRows("snap_original");
  assert.deepEqual(result.rows.map(row => row.record_id), ["first", "second"]);
  assert.equal(result.truncated, false);
  assert.equal(h.calls.filter(c => c.path.includes("/dataset?")).length, 2);
  assert.equal(h.calls.some(c => c.path.includes("/statistics/")), false);
});

test("statistics and snapshot reads recover without changing request bytes or snapshot", async t => {
  for (const kind of ["statistics", "snapshot"]) {
    await t.test(kind, async t => {
      const h = await fixture(t);
      const requestScope = {
        schema_version: "1.0" as const,
        range: { from: "2026-11-10T00:00:00Z", to: "2026-11-11T00:00:00Z", timezone: "UTC" },
        metrics: ["tasks.touched"],
      };
      const sent: (BodyInit | null | undefined)[] = [];
      h.resource = async (path, init) => {
        assert.equal(path, kind === "statistics" ? "/api/v1/statistics/query" : "/api/v1/report-snapshots/snap_original");
        sent.push(init.body);
        if (new Headers(init.headers).get("Authorization") === "Bearer old") {
          requestScope.metrics.push("usage.tokens");
          return unauthorized();
        }
        return envelope({ snapshot_id: "snap_original", metrics: {} });
      };
      const response = kind === "statistics"
        ? await h.api.queryStatistics(requestScope)
        : await h.api.fetchReportSnapshot("snap_original");
      assert.equal(response.snapshot_id, "snap_original");
      assert.equal(sent.length, 2);
      assert.equal(sent[0], sent[1]);
      if (kind === "statistics") assert.deepEqual(JSON.parse(sent[1] as string).metrics, ["tasks.touched"]);
    });
  }
});

test("a fractional ticket deadline stops pair even before its five-second timeout", async t => {
  const h = await fixture(t);
  t.mock.timers.enable({ apis: ["setTimeout"] });
  h.ticket = async () => Response.json({
    pairing_code: "ephemeral", ttl_seconds: 0.25, expires_at: new Date(Date.now() + 250).toISOString(),
  });
  const started = held<void>();
  h.pair = async init => {
    started.resolve();
    return new Promise((_resolve, reject) => {
      init.signal!.addEventListener("abort", () => reject(init.signal!.reason), { once: true });
    });
  };
  const pending = h.api.getCapabilities();
  const rejected = assert.rejects(pending, { status: 401 });
  await started.promise;
  t.mock.timers.tick(250);
  await rejected;
  assert.equal(h.writes.length, 0);
  assert.equal(h.calls.filter(c => c.path.endsWith("/pair")).length, 1);
});

test("pair request times out once after five seconds", async t => {
  const h = await fixture(t);
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const started = held<void>();
  h.pair = async init => {
    started.resolve();
    return new Promise((_resolve, reject) => {
      init.signal!.addEventListener("abort", () => reject(init.signal!.reason), { once: true });
    });
  };
  const pending = h.api.getCapabilities();
  const rejected = assert.rejects(pending, { status: 401 });
  await started.promise;
  t.mock.timers.tick(5000);
  await rejected;
  assert.equal(h.store.size, 0);
  assert.equal(h.calls.filter(c => c.path.endsWith("/pair")).length, 1);
});
