/*
 * Panel manifest: the single source of truth for panels (D14).
 * Imported directly from contracts/ — there is no second copy.
 */

import manifestJson from "../../contracts/panel-manifest.json";

export interface PanelManifestEntry {
  panel_id: string;
  title_zh: string;
  order: number;
  desktop_span: 6 | 12;
  kind: "kpi" | "chart" | "table";
  metric_ids: string[];
  field_dependencies: string[];
  export_required: boolean;
  always_visible: boolean;
  insufficient_data_zh: string;
}

export interface PanelManifest {
  schema_version: string;
  manifest_version: string;
  release: string;
  source: string;
  panels: PanelManifestEntry[];
}

export const MANIFEST: PanelManifest = manifestJson as PanelManifest;
