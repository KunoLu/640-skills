/*
 * ReportDocument (PRD v0.2 §13.3): ReportDocument(snapshot, presentation_state).
 *
 * The single report document model shared by the page and (in R2.1a) the
 * four export formats. It is not a DOM snapshot and not outerHTML: it pairs
 * a fixed Snapshot (from the R1 report_snapshot surface) with presentation
 * state, and binds both to the panel definitions derived from the manifest
 * (D14). Panels and their data bindings come from the registry — the
 * manifest is the only place panel identity is defined.
 */

import {
  MANIFEST_VERSION,
  PANELS_BY_ID,
  PANEL_REGISTRY,
  type PanelDefinition,
} from "./registry";

/** Public view of an R1 ReportSnapshot (report_snapshot.Snapshot.public_view). */
export interface Snapshot {
  snapshot_id: string;
  created_at: string;
  expires_at: string;
  query_scope: Record<string, unknown>;
  query_hash: string;
  as_of: string;
  effective_from: string;
  effective_to: string;
  timezone: string;
  watermark_seq: number;
  source_watermarks: Record<string, unknown>[];
  metrics_version: string;
  dataset_manifest: Record<string, unknown>[];
  unknown_time_event_ids: string[];
  quality_summary: Record<string, unknown>;
  warnings: string[];
  redaction_policy_version: string;
  export_schema_version: string;
  snapshot_digest: string;
}

/** §13.3 presentation_state: affects presentation only, never CSV scope. */
export interface PresentationState {
  theme: "dark" | "light";
  report_width_px: number;
  expanded_detail_ids: string[];
  table_sort: Record<string, string>;
  preview_row_sets: Record<string, number>;
  panel_order: string[];
  legend_state: Record<string, boolean>;
}

export const DEFAULT_PRESENTATION_STATE: PresentationState = {
  theme: "dark",
  report_width_px: 1440,
  expanded_detail_ids: [],
  table_sort: {},
  preview_row_sets: {},
  panel_order: PANEL_REGISTRY.map((panel) => panel.panel_id),
  legend_state: {},
};

export interface ReportPanelBinding {
  definition: PanelDefinition;
}

export class ReportDocument {
  readonly manifest_version = MANIFEST_VERSION;
  readonly snapshot: Snapshot;
  readonly presentation_state: PresentationState;
  readonly panels: readonly ReportPanelBinding[];

  constructor(
    snapshot: Snapshot,
    presentation_state: PresentationState = DEFAULT_PRESENTATION_STATE,
  ) {
    this.snapshot = snapshot;
    this.presentation_state = presentation_state;
    this.panels = presentation_state.panel_order.map((panel_id) => {
      const definition = PANELS_BY_ID[panel_id];
      if (!definition) {
        throw new Error(`panel_id ${panel_id} not in manifest registry`);
      }
      return { definition };
    });
  }
}
