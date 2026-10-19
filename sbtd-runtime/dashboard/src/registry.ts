/*
 * Panel registry (D14): derived from contracts/panel-manifest.json.
 * Nothing about panel identity, order, layout, or export obligations is
 * restated here — the registry is a lookup view over the manifest.
 */

import { MANIFEST, type PanelManifestEntry } from "./manifest";

export interface PanelDefinition extends PanelManifestEntry {
  /** CSS grid column span on the 12-column desktop grid (§12.3). */
  gridColumn: string;
}

function toDefinition(entry: PanelManifestEntry): PanelDefinition {
  return {
    ...entry,
    gridColumn: `span ${entry.desktop_span}`,
  };
}

/** Panels in manifest order (§12.4 order is the page order). */
export const PANEL_REGISTRY: readonly PanelDefinition[] = MANIFEST.panels
  .map(toDefinition)
  .sort((a, b) => a.order - b.order);

export const PANELS_BY_ID: Record<string, PanelDefinition> = Object.fromEntries(
  PANEL_REGISTRY.map((panel) => [panel.panel_id, panel]),
);

export const MANIFEST_VERSION: string = MANIFEST.manifest_version;

/** Every metric bound to a panel, deduplicated, in manifest order. */
export const ALL_METRIC_IDS: string[] = [
  ...new Set(MANIFEST.panels.flatMap((panel) => panel.metric_ids)),
];
