import type { DatasetRow } from "./api.ts";
import type { Snapshot } from "./reportDocument.ts";

export function makeSnapshot(snapshotId: string): Snapshot {
  return {
    snapshot_id: snapshotId,
    created_at: "2026-10-19T15:00:00Z",
    expires_at: "2026-10-19T16:00:00Z",
    query_scope: {
      schema_version: "1.0",
      from: "2026-10-18T15:00:00Z",
      to: "2026-10-19T15:00:00Z",
      timezone: "Asia/Shanghai",
      filters: {},
      task_granularity: "executable-leaf",
      include_unlinked: false,
      include_unknown_time: false,
      metrics: ["tasks.touched"],
    },
    query_hash: "hash",
    as_of: "2026-10-19T15:00:00Z",
    effective_from: "2026-10-18T15:00:00Z",
    effective_to: "2026-10-19T15:00:00Z",
    timezone: "Asia/Shanghai",
    watermark_seq: 42,
    source_watermarks: [],
    metrics_version: "1.0",
    dataset_manifest: [
      { record_type: "task", rows: 2 },
      { record_type: "event", rows: 3 },
    ],
    unknown_time_event_ids: [],
    quality_summary: { unknown_time_events: 0 },
    warnings: [],
    redaction_policy_version: "1",
    export_schema_version: "1.0",
    snapshot_digest: "digest",
  };
}

export function makeRow(
  recordType: string,
  recordId: string,
  fields: Record<string, unknown> = {},
): DatasetRow {
  return { record_type: recordType, record_id: recordId, relation_role: "activity", fields };
}
