import { test } from "node:test";
import assert from "node:assert/strict";

import {
  cleanFilters,
  deriveFilterOptions,
  summarizeSnapshotScope,
} from "./filters.ts";
import { makeRow, makeSnapshot } from "./testFixtures.ts";

test("deriveFilterOptions collects distinct sorted values per dimension", () => {
  const rows = [
    makeRow("event", "e1", { project_id: "p2", host_kind: "omp", workflow_mode: "strict" }),
    makeRow("event", "e2", { project_id: "p1", host_kind: "codex", workflow_mode: "strict" }),
    makeRow("event", "e3", { project_id: "p2", host_kind: "omp", workflow_mode: "lite" }),
    makeRow("task", "t1", { project_id: null, host_kind: "" }),
  ];
  const options = deriveFilterOptions(rows);
  assert.deepEqual(options.project_ids, ["p1", "p2"]);
  assert.deepEqual(options.host_kinds, ["codex", "omp"]);
  assert.deepEqual(options.workflow_modes, ["lite", "strict"]);
  assert.deepEqual(options.actor_ids, []);
  assert.deepEqual(options.component_ids, []);
  assert.deepEqual(options.evidence_levels, []);
});

test("cleanFilters drops empty dimensions and copies arrays", () => {
  const input = { host_kinds: ["omp"], workflow_modes: [] as string[] };
  const cleaned = cleanFilters(input);
  assert.deepEqual(cleaned, { host_kinds: ["omp"] });
  cleaned["host_kinds"]!.push("mutated");
  assert.deepEqual(input.host_kinds, ["omp"]);
});

test("summarizeSnapshotScope writes out the complete conditions (§12.5)", () => {
  const snapshot = makeSnapshot("snap_1");
  snapshot.query_scope = {
    ...snapshot.query_scope,
    filters: { host_kinds: ["omp", "codex"], workflow_modes: ["strict"] },
  };
  assert.equal(
    summarizeSnapshotScope(snapshot),
    "时间 2026-10-18T15:00:00Z → 2026-10-19T15:00:00Z（Asia/Shanghai）；" +
      "筛选：宿主=omp|codex；模式=strict；任务粒度 executable-leaf",
  );
});

test("summarizeSnapshotScope says 无 when no filter is active", () => {
  const summary = summarizeSnapshotScope(makeSnapshot("snap_1"));
  assert.match(summary, /筛选：无/);
  assert.match(summary, /任务粒度 executable-leaf/);
});
