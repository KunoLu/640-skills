---
schema_version: 1
id: dashboard-ui-i18n-2026-10
workflow_mode: strict
mode_source: user
mode_note: 用户 2026-10-29 明确 strict mode
status: "in-progress"
branch: sbtd/strict-dashboard-ui-alignment
created_at: '2026-10-29T10:18:06.335145+08:00'
updated_at: "2026-10-29T10:18:13.053316+08:00"
completed_at: null
---
# Dashboard UI 对齐 omp stats + 双语 i18n

## 目标（用户 2026-10-28 确认的方案）

参考 omp cli stats 页（http://127.0.0.1:3847/#/overview?range=24h）对齐 `sbtd-runtime/dashboard` 的样式、布局、色系；明确不做侧边栏分页（导出逻辑依赖单页全 panel）。panel 全分辨率自适应拉伸无留宽（直播页去 1440px 上限；导出产物 1440px 文档宽度契约不动）。右上角语言切换，默认英语可切中文。

用户确认（2026-10-29 ask）：导出产物跟随 UI 语言——`presentation_state` 增加 `locale`，`export_render.py` 增加双语模板（旧快照无 locale 时默认 zh 向后兼容）。QA 数据：开启 observation + 注册本仓库 + 导入历史（只写 ~/.sbtd-runtime）。

## 证据基线

- omp 计算样式：亮 #f2f2f3/#fff/rgb(21,21,24)，暗 #000/#09090a/rgb(237,237,239)，卡圆角 16px、边框 6% 透明，Inter var 栈 13.5px。
- 现状：`.page` max-width 1440px；概览 dt/dd 竖排；顶栏控件多行堆叠；UI 全中文硬编码；export_render.py 847 行中文硬编码。
- 截图证据：omp-stats-1440.png / omp-stats-dark-1440.png / omp-stats-390.png / sbtd-dashboard-before-*.png。

## 边界

不改导出管线逻辑（创建/轮询/取消/下载/配额/渲染器隔离），仅模板字符串双语化与 locale 透传。不引入 webfont（离线约束）。未完整调用 grill-with-docs：需求、参考页与三项确认明确；DDD 门不触发。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-29T10:18:13.053316+08:00 | planned | in-progress | 开始 dashboard UI 对齐与 i18n | 方案经用户确认（导出跟随 UI 语言；导入真实 QA 数据）；before 截图与 omp 计算样式已取证 |
