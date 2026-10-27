import { test } from "node:test";
import assert from "node:assert/strict";

import {
  ALL_RANGE_FROM,
  buildScope,
  describeRange,
  loadSelection,
  resolvePresetRange,
  saveSelection,
  selectionLabel,
  TimeRangeError,
  validateCustomRange,
  type TimeSelection,
} from "./timeRange.ts";

const NOW = new Date("2026-10-19T15:00:00.000Z");

test("presets keep exact durations ending at the next query bucket boundary", () => {
  const cases: Record<string, number> = {
    "1h": 3600_000,
    "24h": 24 * 3600_000,
    "7d": 7 * 24 * 3600_000,
    "30d": 30 * 24 * 3600_000,
    "90d": 90 * 24 * 3600_000,
  };
  for (const [preset, ms] of Object.entries(cases)) {
    const range = resolvePresetRange(
      preset as "1h", new Date("2026-10-15T16:00:10Z"), "Asia/Shanghai",
    );
    assert.equal(range.to, "2026-10-15T16:05:00.000Z");
    assert.equal(
      Date.parse(range.to) - Date.parse(range.from),
      ms,
      `${preset} window size`,
    );
    assert.equal(range.timezone, "Asia/Shanghai");
  }
});

test("all preset starts at the epoch and ends at the query bucket boundary", () => {
  const range = resolvePresetRange("all", new Date("2026-10-15T16:03:00Z"), "UTC");
  assert.equal(range.from, ALL_RANGE_FROM);
  assert.equal(range.to, "2026-10-15T16:05:00.000Z");
});

test("relative presets advance both bounds after a query bucket boundary (§12.5)", () => {
  const earlier = resolvePresetRange("24h", new Date("2026-10-15T16:00:10Z"), "UTC");
  const later = resolvePresetRange("24h", new Date("2026-10-15T16:05:00.001Z"), "UTC");
  assert.deepEqual(earlier, {
    from: "2026-10-14T16:05:00.000Z",
    to: "2026-10-15T16:05:00.000Z",
    timezone: "UTC",
  });
  assert.deepEqual(later, {
    from: "2026-10-14T16:10:00.000Z",
    to: "2026-10-15T16:10:00.000Z",
    timezone: "UTC",
  });
});

test("valid custom range normalizes to ISO with the given timezone", () => {
  const range = validateCustomRange(
    "2026-10-18T00:00:07.123+08:00",
    "2026-10-19T00:03:12.345+08:00",
    "Asia/Shanghai",
    NOW,
  );
  assert.equal(range.from, "2026-10-17T16:00:07.123Z");
  assert.equal(range.to, "2026-10-18T16:03:12.345Z");
  assert.equal(range.timezone, "Asia/Shanghai");
});

test("invalid custom ranges raise TimeRangeError and never fall back to 24h", () => {
  const invalid: Array<[string, string, string]> = [
    ["not-a-date", "2026-10-19T00:00:00Z", "UTC"], // unparseable
    ["2026-10-19T00:00:00Z", "2026-10-19T00:00:00Z", "UTC"], // from == to
    ["2026-10-19T01:00:00Z", "2026-10-19T00:00:00Z", "UTC"], // from > to
    ["2026-10-18T00:00:00Z", "2026-10-19T00:00:00Z", "Not/AZone"], // bad IANA tz
    ["2027-01-01T00:00:00Z", "2027-01-02T00:00:00Z", "UTC"], // entirely future
  ];
  for (const [from, to, tz] of invalid) {
    assert.throws(
      () => validateCustomRange(from, to, tz, NOW),
      TimeRangeError,
      `${from}→${to}@${tz} must be rejected`,
    );
  }
});

test("buildScope carries range, metrics and non-empty filters only", () => {
  const selection: TimeSelection = { kind: "preset", preset: "7d" };
  const scope = buildScope(
    selection,
    { host_kinds: ["omp"], workflow_modes: [] },
    ["tasks.touched"],
    new Date("2026-10-15T16:03:00Z"),
  );
  assert.equal(scope.schema_version, "1.0");
  assert.deepEqual(scope.range, {
    from: "2026-10-08T16:05:00.000Z",
    to: "2026-10-15T16:05:00.000Z",
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  });
  assert.deepEqual(scope.filters, { host_kinds: ["omp"] });
  assert.deepEqual(scope.metrics, ["tasks.touched"]);
});

test("selection memory round-trips; corrupt/absent storage defaults to 24h", () => {
  const store: Record<string, string> = {};
  const original = globalThis.localStorage;
  Object.defineProperty(globalThis, "localStorage", {
    value: {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => {
        store[key] = value;
      },
    },
    configurable: true,
  });
  try {
    assert.deepEqual(loadSelection(), { kind: "preset", preset: "24h" });
    const custom: TimeSelection = {
      kind: "custom",
      from: "2026-10-18T00:00:00Z",
      to: "2026-10-19T00:00:00Z",
      timezone: "UTC",
    };
    saveSelection(custom);
    assert.deepEqual(loadSelection(), custom);
    store["sbtd.timeRange"] = "{corrupt";
    assert.deepEqual(loadSelection(), { kind: "preset", preset: "24h" });
  } finally {
    Object.defineProperty(globalThis, "localStorage", {
      value: original,
      configurable: true,
    });
  }
});

test("describeRange and selectionLabel state the full window honestly", () => {
  const range = resolvePresetRange("24h", NOW, "Asia/Shanghai");
  assert.equal(
    describeRange(range),
    "2026-10-18T15:00:00.000Z → 2026-10-19T15:00:00.000Z（Asia/Shanghai）",
  );
  assert.equal(selectionLabel({ kind: "preset", preset: "90d" }), "90d");
  assert.match(
    selectionLabel({
      kind: "custom",
      from: "a",
      to: "b",
      timezone: "UTC",
    }),
    /^自定义 a → b（UTC）$/,
  );
});

test("取整后查询哈希稳定", () => {
  // D 节测试②：验证完整 scope，不在前端重写后端 query_hash。
  const firstNow = new Date("2026-10-15T16:00:10.000Z");
  const secondNow = new Date("2026-10-15T16:03:00.000Z");
  const selection: TimeSelection = { kind: "preset", preset: "24h" };
  const filters = { host_kinds: ["omp"], workflow_modes: ["strict"] };
  const metrics = ["tasks.touched", "tasks.created"];
  const first = buildScope(selection, filters, metrics, firstNow);
  const second = buildScope(selection, filters, metrics, secondNow);
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  assert.deepEqual(first, {
    schema_version: "1.0",
    range: {
      from: "2026-10-14T16:05:00.000Z",
      to: "2026-10-15T16:05:00.000Z",
      timezone,
    },
    filters,
    metrics,
  });
  assert.deepEqual(second, first);
  assert.deepEqual(
    buildScope(selection, filters, metrics, new Date("2026-10-15T16:05:00.000Z")),
    first,
  );
  const next = buildScope(
    selection, filters, metrics, new Date("2026-10-15T16:05:00.001Z"),
  );
  assert.deepEqual(next, {
    ...first,
    range: {
      from: "2026-10-14T16:10:00.000Z",
      to: "2026-10-15T16:10:00.000Z",
      timezone,
    },
  });
  for (const scope of [first, next]) {
    assert.equal(Date.parse(scope.range.to) - Date.parse(scope.range.from), 86_400_000);
  }
  const custom: TimeSelection = {
    kind: "custom",
    from: "2026-10-14T16:00:07.123Z",
    to: "2026-10-15T16:03:12.345Z",
    timezone: "UTC",
  };
  for (const now of [firstNow, secondNow]) {
    assert.deepEqual(resolvePresetRange("all", now, "UTC"), {
      from: "1970-01-01T00:00:00.000Z",
      to: "2026-10-15T16:05:00.000Z",
      timezone: "UTC",
    });
    assert.deepEqual(buildScope(custom, filters, metrics, now), {
      schema_version: "1.0",
      range: { from: custom.from, to: custom.to, timezone: custom.timezone },
      filters,
      metrics,
    });
  }
});
