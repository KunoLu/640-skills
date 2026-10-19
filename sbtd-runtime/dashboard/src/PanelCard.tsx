import type { ReactNode } from "react";
import type { MetricValue, MetricStratum } from "./api";
import type { PanelDefinition } from "./registry";

export type PanelStatus =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; values: Record<string, MetricValue | undefined> };

/**
 * Render a metric value per its contract shape (contract_eval.evaluate):
 * scalars render directly; objects render as "key value" pairs; arrays as
 * "、"-joined items. Null at any nesting depth renders as "unknown" — never
 * the string "null" — because a missing host-reported field (e.g.
 * cache_read_tokens) is unknown data, not a literal. String(value) on an
 * object would print "[object Object]" — never acceptable on a data panel.
 */
function renderValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "unknown";
  }
  if (Array.isArray(value)) {
    return value.map(renderValue).join("、");
  }
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    if (entries.length === 0) {
      return "unknown";
    }
    return entries
      .map(([key, item]) => `${key} ${renderValue(item)}`)
      .join("、");
  }
  return String(value);
}

/**
 * Partial/conditional markers (PRD §12.3: unknown／partial 不用绿色；overview
 * 文案「展示 unknown／partial 与原因」). A metric is marked when the evaluator
 * declares conditional support, reports missing samples (`missing: true`),
 * or sets a non-decidable `sample_status`.
 */
function markers(entry: MetricValue): string[] {
  const result: string[] = [];
  if (entry.support === "conditional") {
    result.push("conditional");
  }
  if (entry.missing === true) {
    result.push("partial");
  }
  if (
    typeof entry.sample_status === "string" &&
    entry.sample_status !== "decidable"
  ) {
    result.push(entry.sample_status);
  }
  return result;
}

/**
 * Stratified rates (e.g. validations.run_pass_rate): the top-level value is
 * null by design and each stratum carries its own rate result. A stratum
 * with no decidable sample renders unknown plus its sample_status — never 0,
 * never "null".
 */
function StrataList({ strata }: { strata: Record<string, MetricStratum> }) {
  const names = Object.keys(strata);
  if (names.length === 0) return null;
  return (
    <ul className="panel-strata">
      {names.map((name) => {
        const entry = strata[name];
        const status =
          entry && typeof entry === "object" ? entry.sample_status : undefined;
        return (
          <li key={name}>
            {name} {renderValue(entry?.value)}
            {typeof status === "string" && status !== "decidable"
              ? `（${status}）`
              : ""}
          </li>
        );
      })}
    </ul>
  );
}

/**
 * One metric cell: the metric's availability/support metadata decides the
 * rendering. An unsupported metric is labelled as such with its reason; a
 * supported/conditional metric with a null value renders unknown with its
 * reason and the panel's declared insufficient-data note — never 0, never a
 * fabricated number. Strata render whenever present, even when the
 * top-level value is null.
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
  } else {
    const reason = entry.reason ?? entry.missing_reason;
    const strata =
      entry.strata && typeof entry.strata === "object" ? entry.strata : null;
    const hasStrata = strata !== null && Object.keys(strata).length > 0;
    if (entry.value === null || entry.value === undefined) {
      body = (
        <>
          <span className="panel-state-unknown">
            unknown{reason ? `（${String(reason)}）` : ""}
            {hasStrata ? "" : ` — ${insufficientDataZh}`}
          </span>
          {hasStrata && <StrataList strata={strata} />}
        </>
      );
    } else {
      body = (
        <>
          {renderValue(entry.value)}
          {hasStrata && <StrataList strata={strata} />}
        </>
      );
    }
    const marks = markers(entry);
    if (marks.length > 0) {
      body = (
        <>
          {body}{" "}
          <span className="panel-markers">
            {marks.map((mark) => (
              <span key={mark} className="panel-marker">
                {mark}
              </span>
            ))}
          </span>
        </>
      );
    }
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
