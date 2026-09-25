# P2-03：live 批次数据迁移与旧路由停用

## 1. 授权与边界

- 任务：P2-03。唯一状态事实源为主 PRD §14。
- 开发起点：`main` `f922991c5aef75c08e05494f9bef94b847516711`；任务分支 `p2-03-live-apply`。
- 观察时刻 `2026-09-24T23:05:27+0800` 是建立本分支时的 date 返回，不是用户消息发生时钟。
- 用户原文：「在新的任务分支下，启动 P2-03。范围仍是冻结协议的 demo／main、Codex+OMP，源仓不纳入。这是维护窗口，授权对 live 批次做数据迁移和旧路由停用。不部署新接线，不 smoke，不 cleanup，不删备份，不 sync，不改 hooks。隔离现场继续保留。」
- 该原文授权的是 live `demo` 项目的数据迁移和旧路由停用。它不授权部署、smoke、cleanup、备份销毁、sync、hooks 修改，也不授权改写隔离现场。
- 640-skills 不纳入。共享 live HOME 不是正式切换目标。全局卸载仍 not-allowed。`--graft-hooks` 不使用。
- 现有批准文件绑定隔离副本，不能拿来对 live 项目 apply，也不能拿来改隔离现场。

## 2. Book Gate Plan

| Gate | 判定 | 状态 |
|---|---|---|
| DDIA | required；本项是 live 数据迁移，写入前必须确认事实源和失败路径 | passed |
| Legacy safety | 本轮不改生产迁移代码；live 写入尚未发生 | not-required |
| DDD | 无新领域术语 | not-required |
| Refactoring | 不改生产实现 | not-required |
| Release readiness | required；live apply 是 migration／runtime 运维行为变更。适用验证完成前不得运行 reviewer，也不得把本启动写成 ready。P2-03 标 done 前必须有独立 `Release Readiness Review` | planned |
| grill-with-docs | 未完整调用。沿用已冻结范围和用户本句，不新增领域边界 | not-required |

```text
DDIA Data Design Review
Status: confirmed
Data owner and source of truth: 用户拥有 live demo 项目和共享 live HOME。custodian kuno 拥有 backup_root、私有原件和隔离现场。本协议与主 PRD 只拥有可追踪状态。精确路径只进私有层。隔离副本的批准文件不是 live 事实源。
Write / read / async / failure paths: 本轮只读 plan live demo。失败保持 live、共享 HOME、hooks 和隔离现场不变。无队列。apply 未执行。
Consistency model: live 仍是未迁移的运行事实源。隔离演练成功不等于 live 已迁移。缺批准不能记成已 apply。
Idempotency / ordering / retry / deduplication: 不复用隔离 manifest。缺批准就停止，不伪造投影。
Schema / migration / backfill / rollback / replay: 本轮不改 schema，不 backfill，不 replay。
Observability and repair: §14 的 P2-03 为 in-progress，完成时间保持 —。plan blocked 是当前可观察事实。
Required tests: 本文件和台账不含目标绝对路径；P2-04 仍 planned；本轮未 apply。
```

本审查只确认启动可以 fail-closed。它不是 apply 通过，也不是 P2-04 解锁。

`2026-09-24T23:05:27+0800` 初稿把 Release readiness 写成 not-required，理由只是本轮不部署、不发布、不 cleanup。该结论撤回。live apply 属于 migration／runtime 运维行为变更，Gate 改为 required／planned。适用验证完成前不运行 reviewer，也不把本启动写成 ready。


## 3. 当前事实

- `2026-09-24T23:10:47+0800` 只对 live `demo` 运行 migration plan。不传 `--deployment-mode`，不传 `--graft-hooks`，不使用隔离副本批准文件。
- 退出码 2，status `blocked`，reason 为 `a legacy task has no approved projections`。未生成 manifest。未 apply。
- live 项目、共享 HOME 的路由文件、hooks 和隔离现场的观察哨兵未变。
- P2-04 及之后仍为 planned。
- `2026-09-24T23:29:02+0800` 用户书面批准：bootstrap 整夹 private-only 跳过；spec 私有保全；journal 与 runtime marker private-only。归档任务只准备 redact 候选，未看前不批。未写批准文件，未 plan，未 apply。
- `2026-09-24T23:57:48+0800` 用户书面批准这份 live 归档 redact 候选。私有批准文件只绑定 live 原件：bootstrap 整夹跳过、归档 redact、spec 私有保全、journal 与 runtime marker private-only。只读 plan 退出码 2，status `blocked`，reason 为 `unowned legacy runtime content requires approval`。未覆盖的是 legacy `scripts/common/__pycache__/` 下 19 个 `.pyc`。未生成 manifest。未 apply。live 项目、共享 HOME 路由文件、hooks 和隔离现场未变。
- `2026-09-25T08:16:43+0800` 用户书面批准 19 个 pyc private-only，不发布，不删除。该决定已写入私有批准文件。重跑只读 plan 仍退出码 2，status `blocked`，reason 为 `directory contains a link or special entry`。阻断点是计划器为判断 OMP 家目录是否存在而整树扫描，碰到无关符号链接。未生成 manifest。未 apply。未改 live，未改共享路由文件，未删链接。
- `2026-09-25T09:00:24+0800` 只修了 OMP 家目录存在性检查，不扫子树、不跟随链接。重跑只读 plan 退出码 2，status `blocked`，reason 为 `customized legacy global routing requires explicit reconciliation`。Codex 与 OMP 两份共享路由文件都未改。未生成 manifest。未 apply。live 项目、hooks 和隔离现场未变。

## 4. 明确不做

- 不把隔离副本的批准、manifest 或回执套到 live。
- 不改隔离现场，不删备份，不 cleanup，不 sync，不改 hooks，不部署，不 smoke。
- 不把本启动写成 done。完成时间留到 live apply 回执和任务 PR 之后的状态 PR。
- 不启动 P2-04。

## 5. 继续前必须另有的事实

1. live `demo` 的批准投影必须绑定 live 原件，而不是隔离副本。缺批准时保持 blocked。
2. 批准不得要求改 hooks、删备份、cleanup，或写入隔离现场。
3. 只有新的 live plan 为 `planned` 并生成 manifest 后，才可以按本授权 apply。该 apply 仍不部署、不 smoke。
4. 归档 redact 候选已经用户书面批准，并写入私有批准文件。它仍不是 apply 授权；plan 尚未 `planned`。
5. 19 个 pyc 已批准为 private-only。存在性检查已不再被无关符号链接挡住。plan 仍未 `planned`：两份不匹配暂停销的共享路由文件还没有书面核对决定。

