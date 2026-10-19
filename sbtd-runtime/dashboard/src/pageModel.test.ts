import { test } from "node:test";
import assert from "node:assert/strict";

import {
  applyFailure,
  applySuccess,
  beginLoad,
  INITIAL_MODEL,
  retainExpansions,
  type PageModel,
  type ReadyView,
} from "./pageModel.ts";
import { makeRow, makeSnapshot } from "./testFixtures.ts";

function makeView(snapshotId: string): ReadyView {
  return {
    snapshot: makeSnapshot(snapshotId),
    values: {},
    rows: [makeRow("task", "task_a"), makeRow("event", "evt_1")],
    totalRows: 2,
    rowsTruncated: false,
  };
}

test("initial model has no view and is updating", () => {
  assert.equal(INITIAL_MODEL.view, null);
  assert.equal(INITIAL_MODEL.updating, true);
  assert.equal(INITIAL_MODEL.error, null);
});

test("beginLoad keeps the previous completed view and marks updating (D12)", () => {
  const ready = applySuccess(INITIAL_MODEL, makeView("snap_1"));
  const loading = beginLoad(ready);
  assert.equal(loading.updating, true);
  assert.equal(loading.error, null);
  assert.equal(loading.view?.snapshot.snapshot_id, "snap_1");
});

test("applySuccess replaces the whole snapshot atomically (§12.5 / AC-38)", () => {
  const ready = applySuccess(INITIAL_MODEL, makeView("snap_1"));
  const refreshed = applySuccess(beginLoad(ready), makeView("snap_2"));
  assert.equal(refreshed.view?.snapshot.snapshot_id, "snap_2");
  assert.equal(refreshed.updating, false);
  // The view is one object: panels and inline detail read the same
  // snapshot_id and the same rows — there is no path that mixes snapshots.
  assert.equal(refreshed.view?.rows.length, 2);
});

test("applyFailure keeps the previous view and records the error (§12.5)", () => {
  const ready = applySuccess(INITIAL_MODEL, makeView("snap_1"));
  const failed = applyFailure(beginLoad(ready), "boom");
  assert.equal(failed.view?.snapshot.snapshot_id, "snap_1");
  assert.equal(failed.updating, false);
  assert.equal(failed.error, "boom");
});

test("applyFailure before the first success leaves the page in error state", () => {
  const failed = applyFailure(INITIAL_MODEL, "network down");
  assert.equal(failed.view, null);
  assert.equal(failed.error, "network down");
});

test("retainExpansions keeps only records present in the new snapshot", () => {
  const view = makeView("snap_2");
  assert.deepEqual(retainExpansions(["task_a", "task_gone"], view), ["task_a"]);
  assert.deepEqual(retainExpansions([], view), []);
});

test("pageModel holds no reference to export pins (AC-52 separation)", () => {
  // The refresh path (beginLoad/applySuccess/applyFailure) takes and returns
  // only PageModel/ReadyView; there is no pin parameter or field, so a poll
  // refresh structurally cannot mutate an export pin.
  const model: PageModel = applySuccess(INITIAL_MODEL, makeView("snap_1"));
  assert.equal(Object.keys(model).sort().join(","), "error,updating,view");
});
