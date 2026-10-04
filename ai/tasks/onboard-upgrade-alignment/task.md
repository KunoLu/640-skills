---
schema_version: 1
id: onboard-upgrade-alignment
workflow_mode: strict
mode_source: user
mode_note: 用户明确要求在新开发分支以 strict 完成已确认四阶段方案；本机应用、同步、旧资产清理、新分支合并及发布未授权。
status: "checking"
branch: feat/onboard-upgrade-alignment
created_at: '2026-10-03T22:31:25.791160+08:00'
updated_at: "2026-10-04T08:19:54.113257+08:00"
completed_at: null
---
# Onboard 通用升级对齐、恢复与分层验收

## 授权与范围

用户确认完整四阶段方案。PR #109 经本轮明确 admin 授权合并为 f24fe3b59beb584e39a53683840a3be5c79ffe58；本地及远程旧分支已删除。本任务基于合并后的 main，新分支 feat/onboard-upgrade-alignment，禁止本机应用、同步、旧资产实际清理及新分支合并发布。

实现固定基线、完整内容差异、多配置域、upgrade plan/apply/verify、恢复、自升级、九个 GitNexus Skills 清理能力、运行时与 PATH 检查、真实宿主分层验收、两安装器和文档。现有 init/reset/migration 授权含义保持。

需求已由前轮方案确认，未完整调用 grill-with-docs；使用明确术语与持久行为场景，无额外领域假设。规格与门禁见本目录 design.md；持久场景见仓库 Onboard REFERENCE 的升级章节。

后续明确授权与信任选择见 [decisions.md](decisions.md)：允许提交/推送本分支及创建草稿 PR 运行三平台 CI；仍不合并或发布。私有 vault 由操作人独占管理并作为受信历史，hash 不抵御拥有写权限者整组伪造历史。隔离真实 host probe 不等于原GUI重载。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-03T22:31:26.747654+08:00 | planned | in-progress | 已完成旧分支合并清理，在新分支启动获批 strict 实施 | PR #109 MERGED; 用户已确认四阶段方案 |
| 2026-10-04T08:19:54.113257+08:00 | in-progress | checking | 完整升级与恢复及真实隔离宿主已验证，进入最终回归与精确head三平台CI | final-native-*报告；公开installed-copy跨路径retry/recovery回归通过；独立复核已修正 |
