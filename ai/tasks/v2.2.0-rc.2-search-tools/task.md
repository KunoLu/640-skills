---
schema_version: 1
id: v2.2.0-rc.2-search-tools
workflow_mode: strict
mode_source: user
mode_note: 'rc.2 PRD；用户已确认在 #225 合入、主线 CI 全绿、清理任务 3 分支后启动任务 4。'
status: "blocked"
branch: test/v2.2.0-rc.2-search-tools
created_at: '2026-11-24T23:22:36.394772+08:00'
updated_at: "2026-11-24T23:27:36.808864+08:00"
completed_at: null
"blocked_reason": "当前 Astra 原会话：固定服务的直接 stdio 预检已通过；新隔离 CODEX_HOME 未登录，按认证停止门关闭循环。"
---
# 任务 4：替代检索能力

基线：任务 3 的 PR [#225](https://github.com/KunoLu/640-skills/pull/225) 已由用户授权 admin squash。通过外审的分支 head `9ac6ac21b619411bf9ff7106d10f8399f2bf67b8` 对应 [PR CI](https://github.com/KunoLu/640-skills/actions/runs/45382265087)；新 main 为 `f74eea505c88945f812b370f4349d901daf99e01`，对应独立的 [main CI](https://github.com/KunoLu/640-skills/actions/runs/45420223638)。本任务不是 Graft 退役、全局同步或发布授权。

## 固定输入与范围

Codex ast-grep MCP 的官方仓库为 `https://github.com/ast-grep/ast-grep-mcp`，本任务锁定完整提交 `51d5a23f025c73c02032a98748dc06942548c5e1`。执行时核对分离检出的 HEAD；后续引用固定 SHA，而非 main 或浮动版本。`main.py` 声明四个只读工具：`find_code`、`find_code_by_rule`、`dump_syntax_tree`、`test_match_code_rule`。静态声明不等于已装载、获批准或成功执行。隔离 ast-grep CLI 资产选用官方 `0.51.3` Darwin arm64，压缩包 SHA-256 `7954eab1e2803d1485f263377be7f359db6d3915312b5d773cd575eb009330b1`。

## 验收与停止条件

1. 新建任务私有环境、缓存及合成项目。先核验固定服务的 stdio 握手和四种查询的实际语义，保留结果和拒绝非放行工具的负例。直接 MCP 协议不能代替宿主审批。
2. Codex `0.171.0` 只暴露这四个只读工具，逐项观测原生审批与调用；OMP `19.1.0` 核对对应原生检索。既有任务凭据不复制，不开启 eval 或共享 daemon，不改变真实全局信任。需要人工认证或无法证明域隔离时暂停。
3. 分开验证 Onboard 的拒绝无写入、获准前备份、重复运行幂等和回退。仅处置任务私有夹具；真实宿主写入另行授权。保留 Graft，不提前进入任务 5。
4. 真实场景有具体消费链失败时才修改项目；工具列表、安装成功和模拟回执均不能代替端到端验收。未通过的条件单列为 pending 或 blocked，不报完成。

## 工程与证据

strict。未完整调用 grill-with-docs：PRD 任务 4 已确定四项能力、审批、写入授权及恢复边界。当前仅开工，未承诺任何宿主通过。Book Gate Plan：领域建模不适用；若触及安装／配置或持久状态，在生产编辑前执行 Legacy Safety、Refactoring 与适用 DDIA；已有场景与红绿证据先行，之后 project-validation 和适用的 Release Readiness。不得在本仓库写 `.feature`。本地验收后执行内置 `/review`，独审与 CI 绑定精确 SHA。

脱敏原生报告及同 stem 中文汇总放在本任务 ignored `reports/`。当前实现主会话沿用 Astra，模型调用次数未知。不要读取/复制凭据、导入活动会话或把临时安装发布为全局配置。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-24T23:23:06.770772+08:00 | planned | in-progress | 当前 Astra 原会话：开始任务 4，验证固定检索工具的私有 stdio 与按宿主审批。 | main f74eea505c88945f812b370f4349d901daf99e01 对应 CI 45420223638 的 13 个作业均成功。首轮 macOS runner 未分配，原回执保留；只重排 runtime-e2e-macos。任务 3 同名开发分支本地／远端均已删除。新检索工具源码精确 SHA 51d5a23f025c73c02032a98748dc06942548c5e1，私有 TEMP /Users/lusonglin/TEMP/640-skills-rc2-task4.3vv7gXpM，未复制凭据或接线。 |
| 2026-11-24T23:27:36.808864+08:00 | in-progress | blocked | 当前 Astra 原会话：固定服务的直接 stdio 预检已通过；新隔离 CODEX_HOME 未登录，按认证停止门关闭循环。 | 上游 51d5a23f025c73c02032a98748dc06942548c5e1、ast-grep 0.51.3。四项真实只读工具均返回预期结果，未知工具被拒，夹具字节未变，server exit 0。Codex CLI 0.171.0 login status 返回 Not logged in/exit 1。直接 stdio 非宿主审批；OMP 原生对照及 Onboard 写入授权、备份、幂等待验。未发起 OAuth、未更改全局配置，详见 reports/preflight.json 和 preflight.md。 |
