---
schema_version: 1
id: v2.1.0-rc.2-plan
workflow_mode: strict
mode_source: user
mode_note: 用户本次明确要求 SBTD strict task（frontmatter 结构对齐 v2.1.0-rc.1-r1.4-acceptance），且任务 0 只做 grill+DDD+任务表计划，不写任何产品代码、不改 PRD 正文、不 commit、不 push。
status: "in_progress"
branch: docs/v2.1.0-rc.2-plan
created_at: '2026-10-19T10:16:55+08:00'
updated_at: '2026-10-19T11:36:31+08:00'
---
v2.1.0-rc.2 的任务 0：为 R2（Local Dashboard + HTML/CSV/JPEG/PDF 四格式导出，PRD v0.2 §15.3）做实施前计划。底座是 rc.1 已验收的 R1 接口（`sbtd-runtime/` 库面、`contracts/openapi.yaml`、`stats_query`／`csv_export`／`event_store`／`report_snapshot`），不得用 mock 数字冒充真实接口（§15.0）。

## 范围

- 只做：grill 出题（本文件 + `grill-r1.md` 第 1 轮 Q1–Q9）、DDD Boundary Review 初稿、Lord 任务表（0／R2.0a／R2.0b／R2.1a／R2.1b／R2.2／E／F）的落地计划。
- 不做：任何产品代码、PRD v0.2 正文修改、commit、push、联网安装依赖。
- grill 已通读 PRD §12、§13、§14、§15.3、§16.3／§16.4、§18、§19.3、§20.2，并核对 `sbtd-runtime/` 现状与 `sbtd-runtime/docs/r1.4-acceptance-report.md`「有意推迟」一节（Dashboard、HTML/JPEG/PDF、HTTP 导出服务、落盘快照保留、CORS 等均 deferred 到 R2）。
- 完整 grill 收敛、用户拍板后，必须调用 book-ddd-distilled-modeling 输出独立 DDD Boundary Review 并达到通过状态，才能确认需求或进入设计／实现；grill-r1.md 末尾的「DDD 初稿」只是草案，标注待用户锁定。

## 完成门

- 用户逐题确认 grill 答案（含对推荐选项的接受或改选），任务表与 DDD 边界由用户明确锁定。
- 锁定前不进入任何 R2 设计／实现；锁定后按 strict 流程另建 R2.0a 等执行任务的 Book Gate Plan。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-19T10:16:55+08:00 | planned | in-progress | 任务 0 第 1 轮 grill 已出题（Q1–Q9，含固定五题与四道 PRD 未定点），待 Reviewy/Researchy 审题、用户拍板 | ai/tasks/v2.1.0-rc.2-plan/grill-r1.md；docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md §12–§16.4、§19.3、§20.2 |
| 2026-10-19T10:43:35+08:00 | in-progress | in-progress | grill R1b 修订：吸收 Researchy/Reviewy 审题——Q1/Q2 按 §14.3/§19.3 收窄，Q3 按 ADR 0001 §2/§5 锁定前提重出并拆 Q3a–Q3d，Q6 按 §10.4 导出副本 24h 默认改写并拆出 Q6b，新增 Q10（OMP 视觉复用，许可证待核验），Q4 补 CI runner／真机证据标注，DDD 初稿同步；待复审 | ai/tasks/v2.1.0-rc.2-plan/grill-r1.md（修订记录 R1b）；docs/adr/0001-v2.1.0-rc.1-r1.0-runtime-decisions.md §2/§5 |
| 2026-10-19T11:30:50+08:00 | in-progress | in-progress | grill R1c 修订：Q6 拆为 Q6a（仅导出临时副本，§10.4 第 900 行 24h 默认）与 Q6c（临时 ReportSnapshot 是否本期落盘 24h，§10.4 第 899 行；推荐 A 落盘＋24h TTL＋启动清理，C/D 明确标注偏离 PRD 须书面批准），全文删除快照推迟的「基准／基线」表述；折入非阻塞审题意见（Q2a-A 300MB 标估算待核验＋Playwright 可选 extra、Q1a-A 补产物一致性 CI 检查、Q3c-A 终端不打印 ticket URL、Q3b-A 陈旧锁按无效处理；Q10 维持待核验）；事实已核对 PRD 第 899–900 行、report_snapshot DEFAULT_TTL_SECONDS=3600、r1.4 报告 deferred 条目；待复审 | ai/tasks/v2.1.0-rc.2-plan/grill-r1.md（修订记录 R1c）；docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md §10.4；sbtd-runtime/report_snapshot.py:38；sbtd-runtime/docs/r1.4-acceptance-report.md「有意推迟」 |
| 2026-10-19T11:36:31+08:00 | in-progress | in-progress | grill R1d 修订：吸收 Researchy 2026-10-19 事实核验——Q10 OMP 许可证查明为 MIT（oh-my-pi LICENSE，GitHub API 识别，最新 release v18.12.2），删除全部「待核验」，B/C 标许可证可行（保留版权声明＋第三方声明），维持推荐 A（零许可证义务，B 作 R2.0a ADR 升级路径）；Q2a-A 默认改 `playwright install --only-shell chromium`，体积按 Playwright 1.64.0 核验（--only-shell 100–126MB/平台，完整 chromium 300–330MB/平台，playwright 包本体约 140MB），授权提示须显示实际所选模式体积；Q3c-A 补 ADR 须注明 #ticket URL 出现在浏览器启动命令行参数、同机进程可见及缓解（终端不打印、ticket 短时一次性）；待复审 | ai/tasks/v2.1.0-rc.2-plan/grill-r1.md（修订记录 R1d）；https://github.com/can1357/oh-my-pi/blob/main/LICENSE |
