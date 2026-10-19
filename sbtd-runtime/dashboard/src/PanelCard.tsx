import type { ReactNode } from "react";
import type { MetricValue } from "./api";
import type { PanelDefinition } from "./registry";

export type PanelStatus =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; values: Record<string, MetricValue | undefined> };

/**
 * Render a metric value per its contract shape (contract_eval.evaluate):
 * scalars render directly; objects render as "key value" pairs; arrays as
 * "、"-joined items. String(value) on an object would print
 * "[object Object]" — never acceptable on a data panel.
 */
function renderValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map(renderValue).join("、");
  }
  if (typeof value === "object" && value !== null) {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, item]) => `${key} ${renderValue(item)}`)
      .join("、");
  }
  return String(value);
}

/**
 * One metric cell: the metric's availability/support metadata decides the
 * rendering. An unsupported metric is labelled as such with its reason; a
 * supported/conditional metric with a null value renders the panel's
 * declared insufficient-data note — never 0, never a fabricated number.
 */
function MetricCell({
  metricId,
  entry,
  insufficientDataZh,
}: {
  metricId: string;
  entry: MetricValue | undefined;
  insufficientDataZh: string;
}) {
  let body: ReactNode;
  if (entry === undefined) {
    body = (
      <span className="panel-state-unknown">
        unknown — {insufficientDataZh}
      </span>
    );
  } else if (entry.support === "unsupported") {
    body = (
      <span className="panel-state-unknown">
        不支持{entry.reason ? ` — ${String(entry.reason)}` : ""}
      </span>
    );
  } else if (entry.value === null || entry.value === undefined) {
    body = (
      <span className="panel-state-unknown">
        unknown{entry.reason ? `（${String(entry.reason)}）` : ""} —{" "}
        {insufficientDataZh}
      </span>
    );
  } else {
    body = renderValue(entry.value);
  }
  return (
    <div className="panel-metric">
      <dt>{metricId}</dt>
      <dd>{body}</dd>
    </div>
  );
}

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
          {definition.metric_ids.map((metricId) => (
            <MetricCell
              key={metricId}
              metricId={metricId}
              entry={status.values[metricId]}
              insufficientDataZh={definition.insufficient_data_zh}
            />
          ))}
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
