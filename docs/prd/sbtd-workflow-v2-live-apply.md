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
- `2026-09-25T09:00:24+0800` 只修了 OMP 家目录存在性检查，不扫子树。当时写了「不跟随链接」，该句不完整：只 `lstat` 了最后一级，父目录是符号链接时仍会被跟随。重跑只读 plan 退出码 2，status `blocked`，reason 为 `customized legacy global routing requires explicit reconciliation`。Codex 与 OMP 两份共享路由文件都未改。未生成 manifest。未 apply。
- `2026-09-25T09:04:58+0800` 存在性检查改为逐级 no-follow，仍不扫子树。父目录是符号链接时在分类前拒绝。重跑只读 plan 仍退出码 2，status `blocked`，reason 仍为 `customized legacy global routing requires explicit reconciliation`。未改两份共享路由，未生成 manifest，未 apply。
- `2026-09-25T09:12:15+0800` 回滚警告：不得单独回滚 `2bb2089`。那会回到 `2e5e42c`，父目录符号链接仍会被跟随。要恢复修复前的整树扫描，必须成对撤回 `2bb2089` 与 `2e5e42c` 并复验。当前安全实现保持不动。
- `2026-09-25T09:54:00+0800` 只读核对两份共享路由，未改文件。两份都不等于 v1.0.15 暂停销，也不等于当前短模板，且仍含旧工具名。OMP 与销同目录，只改了 3 个小节。Codex 少了 `i-have-adhd` 小节，交互工具节已改名，另有 8 个小节与销不同。暂停块不在任一文件中。未 plan，未 apply。
- `2026-09-25T09:55:51+0800` 撤回「保留两份定制路由、不暂停、改计划器放行」。该建议违反协议 §1 的旧路由停用。现有含旧工具名的定制路由就是所有权门的阻断对象。跳过暂停会让旧入口继续生效。plan 保持 blocked。不新增无暂停例外。未改两份路由，未改计划器，未 apply。
- `2026-09-25T10:02:11+0800` 按受控暂停方案在私有层准备了 Codex 与 OMP 两份路由候选。开头是暂停块原文。两个旧入口小节已换成一段否定句。其余定制规则保留，只改了会继续调用旧入口的句子。候选未批准，未写入 live，未改计划器，未 plan，未 apply。
- `2026-09-25T10:06:44+0800` 两份全局候选不能证明 demo 旧入口已停用。候选写明项目 `AGENTS.md` 优先于全局规则。live 项目规则第 50–57 行仍要求加载 `trellis-workflow`、读取 `.trellis/workflow.md`；第 173–193 行管理块仍要求优先使用 Trellis 命令。这是独立阻断。批准两份全局候选不得放行 plan 或 apply。项目级规则还没有单独的受控停用候选。未改项目文件，未 plan，未 apply。
- `2026-09-25T10:09:05+0800` 在私有层准备了 demo 项目规则的受控停用候选。开头是暂停块原文。`## Trellis` 到目录清单、以及 `TRELLIS:START` 到 `TRELLIS:END` 管理块已换成一段否定句。Channel 加载句和 lesson 写入旧目录的句子已改成不得执行。filesystem-safety 与非法 dispatch fail-closed 两条保留。候选未批准，未写入 live，未 plan，未 apply。批准这一份仍不能单独放行 plan。
- `2026-09-25T10:16:26+0800` 用户书面「批准」只绑定 demo 项目规则候选，checksum `cb5f99ea620f77028ab7323aae1cf4c0989230afd9385da40aa9811370e5f767`。不绑定两份全局候选。未写入 live。未改计划器。未 plan。未 apply。这一份批准不能放行 plan。
- `2026-09-25T10:18:13+0800` 撤回对两份全局候选的绑定。用户那句只批准已展示的否定句，不能覆盖未展示的 `to-spec` / `to-tickets` 落盘改写、Lessons 路径改写和 Skill 文案改写。私有批准记录已改为 withdrawn-not-binding。未写入 live。未 plan。未 apply。
- `2026-09-25T10:21:27+0800` 用户按已展示 SHA 批准两份全局候选。Codex `f206428ce4ccb2dc67b364f81264d851401cda67ad94b2f60dda1a2ccef034a9`。OMP `e52100f279aad36e2c629b3dc11dc9f12ba79fe9a1044e4b1401e5125eb16577`。写入前复核与这两个 SHA 一致。未写入 live。未改计划器。未 plan。未 apply。
- `2026-09-25T10:24:41+0800` 撤回「计划器只接受三个 SHA」的实现建议。共享暂停校验只认可 pinned `ensure-file-block`，apply 只追加暂停块，不写入已批候选。项目 `AGENTS.md` 的现有操作只删管理块。硬编码放行会让 plan 变绿却执行错误暂停。未改计划器，未写 live，未 plan。

## 4. 明确不做

- 不把隔离副本的批准、manifest 或回执套到 live。
- 不改隔离现场，不删备份，不 cleanup，不 sync，不改 hooks，不部署，不 smoke。
- 不把本启动写成 done。完成时间留到 live apply 回执和任务 PR 之后的状态 PR。
- 不启动 P2-04。
- 不得单独回滚 `2bb2089`。它的父提交 `2e5e42c` 只检查最后一级。成对撤回这两笔才会回到整树扫描，撤回后必须复验。

## 5. 继续前必须另有的事实

1. live `demo` 的批准投影必须绑定 live 原件，而不是隔离副本。缺批准时保持 blocked。
2. 批准不得要求改 hooks、删备份、cleanup，或写入隔离现场。
3. 只有新的 live plan 为 `planned` 并生成 manifest 后，才可以按本授权 apply。该 apply 仍不部署、不 smoke。
4. 归档 redact 候选已经用户书面批准，并写入私有批准文件。它仍不是 apply 授权；plan 尚未 `planned`。
5. 三份暂停候选已按 checksum 书面批准，但都未写入 live。第 6 节已补契约缺口和失败路径。实现范围不是只改计划器。该设计尚未被接受为实现授权。接受前不改 schema、计划器、apply 或 verify，不写 live。

## 6. 已批路由候选的复制与回读设计

`2026-09-25T10:42:55+0800` 只出设计，不改代码。这不是实现授权，也不是 apply 授权。

现有共享暂停只认可 pinned `ensure-file-block`，apply 只追加固定暂停块。项目 `AGENTS.md` 若命中所有权哈希，现有操作只删除 `TRELLIS` 管理块。这两条都不能写入已批全文。不得在源码里硬编码三个 SHA 来放行它们。

三项目标按角色解析，不按 SHA 名单解析：

1. Codex 全局路由：当前 Codex home 下的 `AGENTS.md`。
2. OMP 全局路由：当前 OMP home 下的全局 `AGENTS.md`。
3. demo 项目路由：本次选中的 live `demo` 根下的 `AGENTS.md`。

私有批准记录是绑定事实源。每项只含角色、live 目标、原件快照、候选引用和批准句。候选引用的 checksum 必须等于已批 SHA。源码不保存这三个 SHA。测试只用夹具，不把 live checksum 写进仓库。

plan 对每一项重新快照 live 目标和候选。任一与批准记录不一致就 blocked，不自动改批准记录。候选必须以内置暂停块原文开头。通过后只发一条既有 `copy-file` 操作：目标是 live 路径，来源是候选引用，前置状态是 live 快照，所有权指向批准记录而不是暂停销。选择器使用新的 `approved-routing-replacement`，避免被现有暂停校验当成 `ensure-file-block`。同一目标不得再发追加暂停块或只删管理块。两条同时出现就 blocked。

apply 走现有 `copy-file` 路径，写入候选全文，然后回读快照。回读 checksum 必须等于候选状态，也必须等于回执 `after`。不得走追加暂停块。

verify 再读 live 目标。当前快照必须等于回执 `after`，也必须等于已批候选 checksum。不一致就是 drift，不得报已停用。checksum 一致即全文一致，不再用关键字扫描代替回读。

这三项写入前仍须另有 `planned` manifest 和单独的 apply 确认。本设计不授权现在写 live，不授权部署、smoke、cleanup、删备份、sync 或改 hooks。

`2026-09-25T11:01:28+0800` 补失败路径。撤回「只改计划器即可实现」。本补充仍不改代码。

契约缺口：

- `ownership` 只有 `template-source`、`managed-marker`、`skill-identity`、`config-entry`。没有批准记录类型。新所有权写进 manifest 前，schema 和契约检查必须先接受它，否则文档封存失败。
- `_validate_shared_operations()` 只接受 pinned `ensure-file-block` 和 Skill `remove`。共享 `copy-file` 现在会被当成未知操作拒绝。
- 项目平台闭包只接受 `remove`。demo `AGENTS.md` 的 `copy-file` 现在会被当成未知私有操作拒绝。
- apply 的 `copy-file` 回读已经存在，但这两条校验拒绝后根本到不了它。
- verify 对已保留资源只比较回执 `after` 和当前快照。它不重新打开候选。错误的追加暂停若已成功，live 会等于回执 `after`，verify 不会发现那不是已批全文。
- 已成功的错误暂停在重试时因 live 仍等于 `after` 被跳过，不会自动改写成候选。

因此只改计划器会得到两种坏结果：manifest 封存或后续校验失败，plan 并不真绿；或者若绕过校验，apply 仍追加暂停块，verify 把错误结果当成成功。两种都不是完成。

失败路径：

- 批准记录缺失、字段不全或候选 checksum 与记录不一致：plan blocked，`approval-conflict`。零写入。
- live 快照与批准记录中的原件不一致，或候选文件与记录中的候选快照不一致：plan blocked，`state-conflict`。不自动改批准记录。
- 候选不以暂停块原文开头：plan blocked，`candidate-conflict`。
- 同一目标同时出现 `copy-file` 与 `ensure-file-block` 或管理块删除：plan blocked，`approval-conflict`。
- schema 不接受新所有权：manifest 不得封存。这不是 plan 通过。
- apply 时候选字节已变：`state-conflict`，该资源不写。
- apply 写入后回读不等于候选快照：`post-state-conflict`。停止后续资源。回执保留实际 `after`，不得报 succeeded。
- verify 发现 live 不等于回执 `after`，或不等于操作里的候选快照：drift。不得报已停用。
- 重试时上次已成功且 live 仍等于 `after`：跳过，不写第二次。
- 重试时 live 与上次 `after` 不一致：`retry-conflict`。
- 部分写入或未知写入：`unsafe-retry`。不得退回追加暂停块。

实现范围，接受前不做：

1. schema 增加批准候选所有权，并让契约检查拒绝私有范围外的引用。
2. plan 只在上述检查通过后发 `copy-file`。
3. 共享校验和项目闭包都接受这个形状，并拒绝同一目标的旧暂停操作。
4. apply 测试证明写入的是候选全文，不是追加块。
5. verify 测试证明它重开候选，并在 live 不等于候选时失败。
6. 重试测试证明成功结果不重写，部分写入不退回旧暂停。

六项都有失败测试之前，不得把 plan 变绿当成路由已停用。

