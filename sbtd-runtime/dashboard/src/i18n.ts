/*
 * Dashboard UI i18n (2026-10): zero-dependency two-locale dictionary.
 *
 * Boundary: this covers dashboard UI chrome (controls, panel frames, table
 * headers, empty states, feedback). Server-computed diagnostic vocabulary
 * (metric reasons, contract-eval notes) and exported report artifacts are
 * separate surfaces; exported artifacts follow presentation_state.locale
 * server-side (export_render.py).
 */

export type Locale = "en" | "zh";

export const DEFAULT_LOCALE: Locale = "en";
const STORAGE_KEY = "sbtd.locale";

export function initialLocale(): Locale {
  const saved = localStorage.getItem(STORAGE_KEY);
  return saved === "en" || saved === "zh" ? saved : DEFAULT_LOCALE;
}

export function persistLocale(locale: Locale): void {
  localStorage.setItem(STORAGE_KEY, locale);
  document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";
}

const zh = {
  refresh: "刷新来源",
  theme_to_dark: "深色主题",
  theme_to_light: "浅色主题",
  aria_time_range: "时间范围",
  custom: "自定义",
  aria_export: "导出",
  export_format_html: "HTML 网页",
  export_format_jpeg: "JPEG 长图",
  export_format_pdf: "PDF 文档",
  export_format_csv: "CSV 数据",
  export_tooltip:
    "导出当前快照，自动刷新不影响在途导出",
  cancel_export: "取消导出",
  renderer_checking: "正在检查 renderer 可用性",
  warning_prefix: "警告：{warning}",
  aria_custom_range: "自定义时间范围",
  custom_start: "开始",
  custom_end: "结束",
  custom_tz: "时区",
  apply: "应用",
  aria_filters: "维度筛选",
  filter_no_values: "（范围内无取值）",
  aria_active_filters: "当前筛选",
  chip_remove_title: "点击移除该筛选",
  watermark_unknown: "数据水位：未知（尚未取得快照）",
  watermark:
    "数据水位：{asOf}（快照 {snapshotId}，watermark_seq {watermarkSeq}）",
  updating: "正在更新…",
  current_scope: "当前范围：{scope}",
  refresh_failed: "刷新失败：{error}（仍显示上一份已完成快照视图）",
  load_failed: "加载失败：{error}",
  retry: "重试",
  error_unpaired:
    "未配对：本页须经 sbtd-runtime serve 自动打开的配对链接访问" +
    "（ticket 一次性且短时有效；过期请重启 serve）",
  footer_export_note:
    "全页报告导出包含所有统计 Panel、其图表／表格，以及当前展开的详情；CSV " +
    "包含筛选范围内全部安全结构化记录，不受预览行数限制。",
  footer_rows_note:
    "注意：本快照数据集共 {totalRows} 行，页面仅加载前若干页，行预览" +
    "基于已加载部分；统计指标与 Panel 数值不受影响（服务端全量计算）。",
  locale_switch_label: "语言",
  locale_en: "EN",
  locale_zh: "中文",

  // PanelCard
  unsupported: "不支持",
  detail_collapse: "收起明细",
  detail_show: "明细",
  query_failed: "查询失败：{message}（错误不显示 0，可重试）",
  field_dependencies: "字段依赖：{deps}",

  // family labels
  family_task: "任务",
  family_run: "运行",
  family_step: "步骤",
  family_gate: "Gate",
  family_component: "组件",
  family_invocation: "调用",
  family_validation_run: "验证运行",
  family_validation_case: "验证用例",
  family_usage: "用量",
  family_artifact: "工件",
  family_event: "事件",
  family_data_quality: "数据质量",

  // panels.tsx
  family_rows: "{family}：展示 {shown} 条／范围内总 {total} 条",
  loaded_suffix: "（已加载）",
  truncated_note: "（数据集过大仅加载前若干页，预览基于已加载部分）",
  truncated_short: "（数据集过大仅加载前若干页）",
  no_family_records: "范围内无{family}记录。",
  dq_coverage_heading: "覆盖（dataset manifest，实测行数）",
  col_family: "数据族",
  col_rows: "行数",
  dq_gaps: "缺口与未关联",
  unknown_time_events: "未知发生时间事件：{count} 条",
  snapshot_warnings: "快照告警：{warnings}",
  value_none: "无",
  not_carried: "unknown（快照未携带）",
  source_watermark: "来源水位：{value}",
  no_declared_watermark: "无声明（单一本地来源）",
  watermark_seq_item: "水位序号 watermark_seq：{seq}",
  task_timeline: "步骤时间线（展示 {shown} 条／该任务范围内 {total} 条）",
  no_steps: "范围内无该任务的步骤记录。",
  th_step: "步骤",
  th_attempt: "尝试",
  th_start: "开始",
  th_duration: "耗时 ms",
  th_status: "状态",
  events_preview: "事件预览（最新优先；展示 {shown} 条／该任务范围内 {total} 条）",
  no_events: "范围内无该任务的事件。",
  task_summary: "任务摘要：展示 {shown} 条／范围内总 {total} 条",
  th_task: "任务",
  th_role: "角色",
  aria_coverage: "覆盖",
  aria_gaps: "缺口与未关联",
  aria_step_timeline: "步骤时间线",
  aria_events_preview: "事件预览",

  // filters.ts
  filter_project_ids: "项目",
  filter_actor_ids: "主体",
  filter_host_kinds: "宿主",
  filter_workflow_modes: "模式",
  filter_component_ids: "组件",
  filter_evidence_levels: "证据等级",
  scope_time: "时间 {from} → {to}（{timezone}）",
  scope_filters_none: "筛选：无",
  scope_filters: "筛选：{text}",
  scope_granularity: "任务粒度 {granularity}",

  // timeRange.ts
  invalid_timezone: "无效时区：{timezone}（需为 IANA 时区名，如 Asia/Shanghai）",
  range_unparseable: "起止时间无法解析；请同时给出有效的开始与结束时间",
  range_order: "开始时间必须早于结束时间；不会静默回退到 24h",
  range_future: "所选范围完全在未来，范围内不可能有已入库数据",
  custom_label: "自定义 {from} → {to}（{timezone}）",

  // exportJob.ts
  export_err_401: "会话已过期，请重启 serve 并重新配对",
  export_err_400: "导出请求无效",
  export_err_404: "快照或导出不存在",
  export_err_409: "未就绪，请稍候",
  export_err_410: "快照或导出已过期，请刷新后重新导出",
  export_err_422: "导出尺寸超限",
  export_err_503: "renderer 不可用",
  export_err_507: "磁盘配额不足",
  export_err_timeout: "导出渲染超时",
  export_err_render_failed: "导出渲染失败",
  export_err_generic: "导出失败",
  export_requesting: "正在创建导出",
  export_queued: "导出已排队",
  export_ready: "导出已就绪，开始下载",
  export_cancelled: "导出已取消",
  export_generating: "正在生成导出",
  export_wait_timeout: "导出等待超时，已停止轮询；可取消该作业或重新导出",

  // api.ts
  pair_failed: "配对失败：ticket 无效或已过期",
} as const;

export type StringKey = keyof typeof zh;

const en: Record<StringKey, string> = {
  refresh: "Refresh",
  theme_to_dark: "Dark theme",
  theme_to_light: "Light theme",
  aria_time_range: "Time range",
  custom: "Custom",
  aria_export: "Export",
  export_format_html: "HTML Page",
  export_format_jpeg: "JPEG Image",
  export_format_pdf: "PDF Document",
  export_format_csv: "CSV Data",
  export_tooltip:
    "Export the current snapshot; auto-refresh does not affect in-flight exports",
  cancel_export: "Cancel export",
  renderer_checking: "Checking renderer availability",
  warning_prefix: "Warning: {warning}",
  aria_custom_range: "Custom time range",
  custom_start: "Start",
  custom_end: "End",
  custom_tz: "Time zone",
  apply: "Apply",
  aria_filters: "Dimension filters",
  filter_no_values: "(no values in range)",
  aria_active_filters: "Active filters",
  chip_remove_title: "Click to remove this filter",
  watermark_unknown: "Data watermark: unknown (no snapshot yet)",
  watermark:
    "Data watermark: {asOf} (snapshot {snapshotId}, watermark_seq {watermarkSeq})",
  updating: "Updating…",
  current_scope: "Current scope: {scope}",
  refresh_failed: "Refresh failed: {error} (showing the last completed snapshot)",
  load_failed: "Load failed: {error}",
  retry: "Retry",
  error_unpaired:
    "Not paired: open this page via the pairing link that sbtd-runtime serve " +
    "opens automatically (the ticket is one-time and short-lived; restart serve if it expired)",
  footer_export_note:
    "A full-page report export contains every statistics panel with its charts/tables " +
    "and the currently expanded details; CSV contains all safe structured records in the " +
    "filtered range and is not limited by preview rows.",
  footer_rows_note:
    "Note: this snapshot dataset has {totalRows} rows; the page loads only the first " +
    "pages and row previews reflect the loaded part; statistics and panel values are " +
    "unaffected (computed server-side over the full dataset).",
  locale_switch_label: "Language",
  locale_en: "EN",
  locale_zh: "中文",

  unsupported: "Not supported",
  detail_collapse: "Hide details",
  detail_show: "Details",
  query_failed: "Query failed: {message} (errors are never shown as 0; retry)",
  field_dependencies: "Field dependencies: {deps}",

  family_task: "Tasks",
  family_run: "Runs",
  family_step: "Steps",
  family_gate: "Gates",
  family_component: "Components",
  family_invocation: "Invocations",
  family_validation_run: "Validation runs",
  family_validation_case: "Validation cases",
  family_usage: "Usage",
  family_artifact: "Artifacts",
  family_event: "Events",
  family_data_quality: "Data quality",

  family_rows: "{family}: showing {shown} of {total} in range",
  loaded_suffix: " (loaded)",
  truncated_note:
    " (dataset too large — only the first pages were loaded; preview reflects the loaded part)",
  truncated_short: " (dataset too large — only the first pages loaded)",
  no_family_records: "No {family} records in range.",
  dq_coverage_heading: "Coverage (dataset manifest, measured rows)",
  col_family: "Family",
  col_rows: "Rows",
  dq_gaps: "Gaps and unlinked",
  unknown_time_events: "Events with unknown time: {count}",
  snapshot_warnings: "Snapshot warnings: {warnings}",
  value_none: "None",
  not_carried: "unknown (not carried by the snapshot)",
  source_watermark: "Source watermark: {value}",
  no_declared_watermark: "None declared (single local source)",
  watermark_seq_item: "Watermark seq (watermark_seq): {seq}",
  task_timeline: "Step timeline (showing {shown} of {total} for this task)",
  no_steps: "No step records for this task in range.",
  th_step: "Step",
  th_attempt: "Attempt",
  th_start: "Start",
  th_duration: "Duration ms",
  th_status: "Status",
  events_preview: "Event preview (newest first; showing {shown} of {total} for this task)",
  no_events: "No events for this task in range.",
  task_summary: "Task summary: showing {shown} of {total} in range",
  th_task: "Task",
  th_role: "Role",
  aria_coverage: "Coverage",
  aria_gaps: "Gaps and unlinked",
  aria_step_timeline: "Step timeline",
  aria_events_preview: "Event preview",

  filter_project_ids: "Projects",
  filter_actor_ids: "Actors",
  filter_host_kinds: "Hosts",
  filter_workflow_modes: "Modes",
  filter_component_ids: "Components",
  filter_evidence_levels: "Evidence levels",
  scope_time: "Time {from} → {to} ({timezone})",
  scope_filters_none: "Filters: none",
  scope_filters: "Filters: {text}",
  scope_granularity: "Task granularity {granularity}",

  invalid_timezone: "Invalid time zone: {timezone} (must be an IANA name, e.g. Asia/Shanghai)",
  range_unparseable: "Cannot parse start/end; provide both a valid start and end",
  range_order: "Start must be before end; no silent fallback to 24h",
  range_future: "The selected range lies entirely in the future; no data can exist in it",
  custom_label: "Custom {from} → {to} ({timezone})",

  export_err_401: "Session expired; restart serve and pair again",
  export_err_400: "Invalid export request",
  export_err_404: "Snapshot or export does not exist",
  export_err_409: "Not ready yet; please wait",
  export_err_410: "Snapshot or export expired; refresh and export again",
  export_err_422: "Export size limit exceeded",
  export_err_503: "Renderer unavailable",
  export_err_507: "Disk quota exceeded",
  export_err_timeout: "Export render timed out",
  export_err_render_failed: "Export render failed",
  export_err_generic: "Export failed",
  export_requesting: "Creating export",
  export_queued: "Export queued",
  export_ready: "Export ready; starting download",
  export_cancelled: "Export cancelled",
  export_generating: "Generating export",
  export_wait_timeout:
    "Timed out waiting for the export; polling stopped — cancel the job or export again",

  pair_failed: "Pairing failed: ticket invalid or expired",
};

const DICTS: Record<Locale, Record<StringKey, string>> = { en, zh };

/** Translate `key`, substituting `{name}` placeholders from `vars`. */
export function t(
  locale: Locale,
  key: StringKey,
  vars?: Record<string, string | number>,
): string {
  let text = DICTS[locale][key];
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      text = text.replaceAll(`{${name}}`, String(value));
    }
  }
  return text;
}
