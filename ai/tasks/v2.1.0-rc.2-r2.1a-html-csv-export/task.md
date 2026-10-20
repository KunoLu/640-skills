---
schema_version: 1
id: v2.1.0-rc.2-r2.1a-html-csv-export
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict；仅 plan R2.1a 与 D11/D15/D16。不改契约；显式 git add；不 push、不开 PR；不暂存或提交 .omp-r12b-addendum.txt、ai/tasks/codex-verify/。保持 OpenAPI、Panel manifest/schema、ADR 0001/0002/0003、PRD、CSV schema 1.1 不变。不可避免的契约变化 STOP + CONTRACT-CHANGE-NEEDED。
status: in-progress
branch: feat/v2.1.0-rc.2-r2.1a-html-csv-export
created_at: '2026-10-20T15:07:13+08:00'
updated_at: '2026-10-20T15:07:13+08:00'
completed_at: null
---

# R2.1a：离线 HTML + 全量 CSV 导出

基线 `e9cb05b84e449fe4a7dde1b5523faf7478bc310e`；R2.0c #147 于 2026-10-20T15:03:24+08:00 squash-merge，Reviewy CLEAN on `2dbf7b1`。用户 15:05 授权本任务。done 仅代表本地验收，不代表 push／PR／部署／发布。

## 范围与验收

1. 单文件离线 HTML；扫描外部 URL、script src、link href=http、@import、url(http；系统字体与明确 CJK fallback。
2. CSV 复用 serialize_csv / SnapshotStore.dataset_page，snapshot-bound cursor 全量遍历；schema 1.1 不变。
3. 创建作业固定 snapshot_id 并持 backend pin 至完成／取消／失败；测试在途 expiry/sweep 不删、结束释放；前端复用 PinRegistry。
4. ready 后默认 24h，含启动清扫；Export 清理仅 exports/，绝不触及 snapshots/ 或其他目录。
5. 有效期内重复下载 bytes/digest 不变，含 serve 重启。
6. export_id + 当前 session 下载，无路径参数；拒绝 traversal／foreign ID。
7. HTML 和 CSV 使用后端统一脱敏，manifest 记录 redaction version。
8. temp + fsync + rename 原子发布；半成品永不被下载。
9. 更新 install-and-use.md 中 exports pending 与行为说明。

## Book Gate Plan

| Gate | 触发事实 | 阶段 | 状态 |
|---|---|---|---|
| book-ddd-distilled-modeling | 作业／快照引用／会话授权与两目录所有权 | before-dev | running |
| book-ddia-data-design | 导出持久产物、manifest、异步作业与恢复 | before-dev | running |
| book-legacy-change-safety | serve 鉴权、CSV 与 snapshot 高回归面 | before-dev | planned |
| book-refactoring-pass | 修改既有生产代码 | before-dev | planned |
| book-release-readiness | HTTP 服务与导出作业 runtime 改变 | validation 后 | planned |

已读 plan、grill D11/D15/D16/R1e、PRD §10.4/§13、OpenAPI exports、CSV、SnapshotStore 接口、ADR 0003。未完整调用 grill-with-docs：范围和验收已锁定，无须重开需求。实现前继续核对实际 serve、ReportDocument 与 PinRegistry。

## 状态持久化限制

已核对分支、路径与 ignore；安装的 TaskStore.create 实际返回 `TaskStateError: task has no YAML frontmatter block`，completed_steps 为空。未写 active 指针；不修改禁止路径或旧 catalog 来绕过。此共享 task.md 是用户明确要求的交付记录，沿用 R2.0c 做法，不声称 TaskStore lifecycle／自动恢复成功。

## 验证计划

沿用 sbtd-runtime/spec 中文场景 + 英文 Given/When/Then；先建立持久化／保活／安全边界红例，再实现；主会话唯一验证 controller。执行完整 runtime Python tests、受影响 Dashboard tests、相关 CI wrapper、真实 serve 导出与重启 smoke；独立正确性与文件系统／授权 review。正式 raw 与同 stem 中文汇总保留于受 ignore 保护的 reports/。

## 风险与后续范围

- Snapshot disk-usage cap：Reviewy follow-up，仅记录，非本任务实现范围。
- R2.1b JPEG/PDF／Playwright 与 R2.2 跨平台证据不实现；Windows ACL／macOS 不冒充本机验证。
- 不修复无关历史 probe_links 失败；若命中如实保留。

## CONTRACT-CHANGE-NEEDED

尚未触发；如确认不可避免则停止实现并在此记录。

## 模型使用

| 用途 | 请求模型 | 实际模型 | assistant messages | 工具调用次数 |
|---|---|---|---|---|
| implementation / validation / integration | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra（host 标识；high 仅请求档位） | unknown | unknown |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-20T15:07:13+08:00 | planned | in-progress | 用户明确 strict 与 R2.1a；分支、基线匹配；创建明确授权共享交付记录，非 TaskStore lifecycle 成功 | git branch/rev-parse；用户附加 prompt；TaskStore.create 失败且无 completed_steps |
