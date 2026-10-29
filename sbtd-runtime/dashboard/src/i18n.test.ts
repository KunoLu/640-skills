import { test } from "node:test";
import assert from "node:assert/strict";
import { t } from "./i18n.ts";

const KEYS = [
  "refresh", "theme_to_dark", "theme_to_light", "aria_time_range",
  "custom", "aria_export", "export_format_html", "export_format_jpeg",
  "export_format_pdf", "export_format_csv", "export_tooltip", "cancel_export",
  "renderer_checking", "warning_prefix", "aria_custom_range", "custom_start",
  "custom_end", "custom_tz", "apply", "aria_filters", "filter_no_values",
  "aria_active_filters", "chip_remove_title", "watermark_unknown", "watermark",
  "updating", "current_scope", "refresh_failed", "load_failed", "retry",
  "error_unpaired", "footer_export_note", "footer_rows_note",
  "locale_switch_label", "locale_en", "locale_zh",
  "unsupported", "detail_collapse", "detail_show", "query_failed",
  "field_dependencies",
  "family_task", "family_run", "family_step", "family_gate", "family_component",
  "family_invocation", "family_validation_run", "family_validation_case",
  "family_usage", "family_artifact", "family_event", "family_data_quality",
  "family_rows", "loaded_suffix", "truncated_note", "truncated_short",
  "no_family_records", "dq_coverage_heading", "col_family",
  "col_rows", "dq_gaps", "unknown_time_events", "snapshot_warnings",
  "value_none", "not_carried", "source_watermark", "no_declared_watermark",
  "watermark_seq_item", "task_timeline", "no_steps", "th_step", "th_attempt",
  "th_start", "th_duration", "th_status", "events_preview", "no_events",
  "task_summary", "th_task", "th_role", "aria_coverage", "aria_gaps",
  "aria_step_timeline", "aria_events_preview",
  "filter_project_ids", "filter_actor_ids", "filter_host_kinds",
  "filter_workflow_modes", "filter_component_ids", "filter_evidence_levels",
  "scope_time", "scope_filters_none", "scope_filters", "scope_granularity",
  "invalid_timezone", "range_unparseable", "range_order", "range_future",
  "custom_label",
  "export_err_401", "export_err_400", "export_err_404", "export_err_409",
  "export_err_410", "export_err_422", "export_err_503", "export_err_507",
  "export_err_timeout", "export_err_render_failed", "export_err_generic",
  "export_requesting", "export_queued", "export_ready", "export_cancelled",
  "export_generating", "export_wait_timeout", "pair_failed",
] as const;

test("every key translates in both locales and interpolates", () => {
  for (const key of KEYS) {
    for (const locale of ["en", "zh"] as const) {
      const text = t(locale, key, { warning: "w", message: "m", deps: "d" });
      assert.ok(typeof text === "string" && text.length > 0, `${locale}.${key}`);
      assert.ok(!text.includes("{warning}"), `${locale}.${key} interpolation`);
    }
  }
});

test("zh stays byte-identical to the legacy UI strings", () => {
  assert.equal(t("zh", "unsupported"), "不支持");
  assert.equal(t("zh", "detail_show"), "明细");
  assert.equal(t("zh", "updating"), "正在更新…");
  assert.equal(t("zh", "filter_project_ids"), "项目");
  assert.equal(t("zh", "family_validation_run"), "验证运行");
  assert.equal(t("zh", "export_err_507"), "磁盘配额不足");
  assert.equal(
    t("zh", "family_rows", { family: "任务", shown: 3, total: 20 }),
    "任务：展示 3 条／范围内总 20 条",
  );
});

test("en renders the aligned english copy", () => {
  assert.equal(t("en", "unsupported"), "Not supported");
  assert.equal(t("en", "locale_zh"), "中文");
  assert.equal(
    t("en", "family_rows", { family: "Tasks", shown: 3, total: 20 }),
    "Tasks: showing 3 of 20 in range",
  );
});
