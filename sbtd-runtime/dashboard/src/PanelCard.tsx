import type { PanelDefinition } from "./registry";

export type PanelStatus =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; values: Record<string, unknown> };

/**
 * One manifest-defined panel. The skeleton renders the panel frame, its
 * metric bindings, and honest states: loading, error (never 0, §12.5), or
 * the manifest's declared insufficient-data note when metrics are absent.
 */
export function PanelCard({
  definition,
  status,
}: {
  definition: PanelDefinition;
  status: PanelStatus;
}) {
  return (
    <section
      className="panel"
      style={{ gridColumn: definition.gridColumn }}
      aria-label={definition.title_zh}
      data-panel-id={definition.panel_id}
    >
      <header className="panel-header">
        <h2>{definition.title_zh}</h2>
        <span className="panel-id">{definition.panel_id}</span>
      </header>
      {status.kind === "loading" && (
        <p className="panel-state" role="status">
          正在更新…
        </p>
      )}
      {status.kind === "error" && (
        <p className="panel-state panel-state-error" role="alert">
          查询失败：{status.message}（错误不显示 0，可重试）
        </p>
      )}
      {status.kind === "ready" && (
        <dl className="panel-metrics">
          {definition.metric_ids.map((metricId) => {
            const value = status.values[metricId];
            return (
              <div key={metricId} className="panel-metric">
                <dt>{metricId}</dt>
                <dd>
                  {value === undefined || value === null ? (
                    <span className="panel-state-unknown">
                      unknown — {definition.insufficient_data_zh}
                    </span>
                  ) : (
                    String(value)
                  )}
                </dd>
              </div>
            );
          })}
          {definition.metric_ids.length === 0 && (
            <p className="panel-state">
              字段依赖：{definition.field_dependencies.join("、")}
            </p>
          )}
        </dl>
      )}
    </section>
  );
}
