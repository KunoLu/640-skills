import { test } from "node:test";
import assert from "node:assert/strict";

import { applySuccess, beginLoad, INITIAL_MODEL } from "./pageModel.ts";
import { PinRegistry } from "./snapshotPin.ts";
import { makeRow, makeSnapshot } from "./testFixtures.ts";
import type { ReadyView } from "./pageModel.ts";

function makeView(snapshotId: string): ReadyView {
  return {
    snapshot: makeSnapshot(snapshotId),
    values: {},
    rows: [makeRow("task", "task_a")],
    totalRows: 1,
    rowsTruncated: false,
  };
}

test("pin resolves to the snapshot captured at creation", () => {
  const registry = new PinRegistry();
  const pin = registry.pin("snap_1", new Date("2026-10-19T15:00:00Z"));
  assert.equal(registry.resolve(pin.pin_id), "snap_1");
  assert.equal(pin.pinned_at, "2026-10-19T15:00:00.000Z");
  assert.equal(registry.count(), 1);
});

test("AC-52: a pinned snapshot id is unchanged across a poll refresh", () => {
  const registry = new PinRegistry();
  // Export job created against the current view: it pins snap_1.
  const model0 = applySuccess(INITIAL_MODEL, makeView("snap_1"));
  const pin = registry.pin(model0.view!.snapshot.snapshot_id);

  // The 30s poll (D12) then replaces the whole page snapshot twice.
  const model1 = applySuccess(beginLoad(model0), makeView("snap_2"));
  const model2 = applySuccess(beginLoad(model1), makeView("snap_3"));
  assert.equal(model2.view?.snapshot.snapshot_id, "snap_3");

  // The in-flight export still resolves to the snapshot it pinned.
  assert.equal(registry.resolve(pin.pin_id), "snap_1");
  assert.equal(registry.count(), 1);
});

test("release drops only the released pin", () => {
  const registry = new PinRegistry();
  const first = registry.pin("snap_1");
  const second = registry.pin("snap_2");
  assert.equal(registry.release(first.pin_id), true);
  assert.equal(registry.resolve(first.pin_id), null);
  assert.equal(registry.resolve(second.pin_id), "snap_2");
  assert.equal(registry.release("pin_unknown"), false);
  assert.equal(registry.count(), 1);
});
