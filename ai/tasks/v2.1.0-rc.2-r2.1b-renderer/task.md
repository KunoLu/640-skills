---
schema_version: 1
id: v2.1.0-rc.2-r2.1b-renderer
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict；仅指定 worktree 与分支。显式 git add；不 push、不开 PR、不评论、不 merge；不暂存 .omp-r12b-addendum.txt 或 ai/tasks/codex-verify/。冻结 OpenAPI、Panel manifest、ADR 0001–0003、PRD、CSV schema。JPEG/PDF 仅库级实现，HTTP 继续拒绝；契约缺口记录而不停止其余工作。
status: in_progress
blocked_reason: null
branch: feat/v2.1.0-rc.2-r2.1b-renderer
created_at: '2026-10-22T11:12:22+08:00'
updated_at: '2026-10-22T11:12:22+08:00'
completed_at: null
---

# R2.1b：JPEG/PDF 独立 renderer

基线 `8931c35ef1aa4a58d3675b6f8d1a8fead309ed90`（R2.1a #151）。本地验收不代表评审、合并、部署或发布。

## 范围与验收

1. JPEG/PDF 复用 R2.1a 服务端静态 HTML、ExportStore 作业、snapshot pin、原子发布、manifest/digest、24h 保留及启动清扫。
2. Playwright 可选、精确钉版；only-shell Chromium 安装到 `$SBTD_RUNTIME_HOME/browsers/`；依赖清单钉 fonts-noto-cjk，记录实测体积。
3. 每作业子进程与临时 profile；路由拒绝外联和 file；单作业信号量、超时及清理。
4. JPEG 按 §13.5 像素预检、降采样与安全失败；PDF 按 §13.6 可搜索、中日英字体嵌入、长表与页脚。
5. 四格式沿用同一 event-detail exportable/classification 过滤；不改变 derived rows 或 withheld 值。
6. 缺依赖仅 JPEG/PDF 不可用并附原因；HTTP jpeg/pdf 仍 400。
7. 单元、真实浏览器、全量指定回归、真实 runtime snapshot smoke、独立复核及冻结契约检查。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-22T11:12:22+08:00 | planned | in_progress | 用户指定 strict；授权 worktree、分支与基线匹配；建立共享交付记录 | pwd、git status/branch/rev-parse；用户任务 |

## 决策

- 未完整调用 grill-with-docs：用户范围、锁定决定与冻结契约边界明确，不重开需求。
- 后续项 A（exportable 语义）仍未决；其决定可能要求提审前同时调整四格式。本次只保持主分支现有过滤。
- 配额决定仅登记在 plan，R2.2 才实现；A、B 不预设结论。
- 沿用 R2.1a 已记录的 TaskStore catalog/frontmatter 限制，不重跑已知失败、不改 active/ignore；本文件是用户明确要求的共享交付，不声称 helper lifecycle 或自动恢复成功。

## 验证证据

初始只读检查：工作区干净；指定分支及基线匹配；`.sbtd/active-task.json` 与本任务 reports 受 ignore 保护，无相关 tracked 本地状态。实现、测试与 smoke 结果将在实际执行后补记。

## 模型使用

主会话请求 `openai-codex/gpt-6-astra:high`；host 标识 `openai-codex/gpt-6-astra`。用途：计划、实现、验证、交付；次数 unknown，operator 按 session jsonl 回填。子代理实际模型将在调用后记录。
