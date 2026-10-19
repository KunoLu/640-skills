/*
 * Export snapshot pinning (AC-52: 导出期间新数据不影响当前文件).
 *
 * The export UI itself is R2.1a scope. What R2.0b must guarantee is the
 * semantic an export job will rely on: creating an export pins the current
 * snapshot_id, and that pin is a separate, immutable reference. The 30s
 * poll / whole-snapshot replace (D12) only ever swaps the page's *current
 * view*; it never touches a pin. R2.1a will create a pin at job creation
 * and fetch the ReportDocument/dataset strictly by the pinned id, so an
 * in-flight export provably ignores later data.
 *
 * This registry is deliberately independent of the page model: nothing in
 * pageModel.ts can see or mutate it.
 */

export interface SnapshotPin {
  readonly pin_id: string;
  readonly snapshot_id: string;
  readonly pinned_at: string;
}

export class PinRegistry {
  private pins: Record<string, SnapshotPin> = {};
  private sequence = 0;

  /** Pin a snapshot id for an export job; returns the pin handle. */
  pin(snapshotId: string, now: Date = new Date()): SnapshotPin {
    this.sequence += 1;
    const pin: SnapshotPin = {
      pin_id: `pin_${this.sequence}`,
      snapshot_id: snapshotId,
      pinned_at: now.toISOString(),
    };
    this.pins[pin.pin_id] = pin;
    return pin;
  }

  /**
   * Resolve a pin to its snapshot id. The answer is the id captured at pin
   * creation, no matter how many page refreshes happened since.
   */
  resolve(pinId: string): string | null {
    const pin = this.pins[pinId];
    return pin === undefined ? null : pin.snapshot_id;
  }

  /** Release the pin when the export job finishes or is cancelled. */
  release(pinId: string): boolean {
    if (this.pins[pinId] === undefined) return false;
    delete this.pins[pinId];
    return true;
  }

  /** Number of live pins (export jobs in flight); for status display. */
  count(): number {
    return Object.keys(this.pins).length;
  }
}
