---
schema_version: 1
id: v2.1.0-rc.2-r2.0c-snapshot-persistence
workflow_mode: strict
mode_source: user
mode_note: 用户明确选择 strict；仅 plan.md R2.0c 与 D13；显式 git add 路径。本地 run 未自行 push；operator 按 Lord 2026-10-20 11:06 指令在本地绿色后 push 并开 PR #147，随后经复核合并。不改契约。禁止暂存或提交 .omp-r12b-addendum.txt 与 ai/tasks/codex-verify/；不修改 contracts、ADR 0001/0002 决策或 PRD 正文。
status: done
branch: feat/v2.1.0-rc.2-r2.0c-snapshot-persistence
created_at: '2026-10-20T11:05:30+08:00'
updated_at: '2026-10-20T15:03:24+08:00'
completed_at: '2026-10-20T11:25:19+08:00'
---

# R2.0c：临时 ReportSnapshot 落盘

基线 `2d147c98ce2874fa2621b95ff816e1781c02f93f`（R2.0b #146 squash-merge，2026-10-20T04:14:03+08:00）。用户 2026-10-20 11:02 Asia/Shanghai 授权开始。completed_at 保留本地验收完成时间；后续 operator push／开 PR #147，Reviewy 在 tip `2dbf7b1` CLEAN，2026-10-20T15:03:24+08:00 squash-merge 为 `e9cb05b84e449fe4a7dde1b5523faf7478bc310e`；plan 行现已关闭。不把合并等同部署或发布。

## 范围与验收

1. SnapshotStore 从进程内 3600s 改为 runtime home/snapshots/ 落盘、默认 24h；创建返回 expires_at。
2. 临时文件写入、fsync、atomic rename；版本头与校验和验证；截断、缺校验和、错误版本均不可读取为有效快照。
3. 启动清扫过期快照，只触及 snapshots/；exports/、审计库、配置、源任务／报告／handoff 不受影响。
4. 被引用快照不得因 expiry/sweep 删除；提供后端 pin 生命周期及 R2.0b PinRegistry → R2.1a 对接说明，不实现导出作业。
5. TTL 内 serve 重启后可凭 snapshot_id 解析原快照。
6. runtime 既有约定：目录 0700、文件 0600；拒绝 symlink 越界。
7. 清理授权独立引用 PRD §10.4 / D13；AC-61 不覆盖快照清理。
8. 新 ADR 0003 固定快照格式版本及 checksum，不改既有 ADR 决策。
9. 更新 sbtd-runtime/docs/install-and-use.md 的进程内／3600s／R2.0c pending 描述。

## 事实与实施顺序

已读 plan.md R2.0c、grill-r1.md D13/Q6c-A/R1e/DDD Query & Snapshot、PRD §10.2–10.4、ADR 0001 runtime home、report_snapshot.py、stats_query.py、serve.py、R2.0b task 与 PinRegistry 调用证据。

未完整调用 grill-with-docs：D13 和验收已锁定，本次不重新开放需求。既有 expires_at 已在 Snapshot.public_view；OpenAPI Envelope.data 无字段限制，新增查询返回 expires_at 无需契约修改。Python LSP references 返回 No language server found；源码搜索确认调用点仅 serve 与 snapshot/CSV 测试。

提交顺序：docs backfill → ADR → production implementation → tests/docs → evidence closeout。测试先在工作区建立红例，依用户要求在第四提交收录。不修改 R2.1a+ planned 状态。

## Book Gate Plan

| Gate | 触发事实 | 阶段 | 状态 |
|---|---|---|---|
| book-ddd-distilled-modeling | 引用保活与清理所有权需区分 UI pin 与服务端 pin | before-dev | passed / confirmed；Query & Snapshot 与 Export 清理目录互不越界；UI pin 不冒充后端保活 |
| book-ddia-data-design | 新持久格式、跨进程读取与 crash recovery | before-dev | passed / confirmed；v1 + SHA-256，原子发布、拒绝损坏文件、恢复引用先于 sweep |
| book-legacy-change-safety | 既有 snapshot/cursor/CSV 行为高回归面 | before-dev | passed / characterized；改前 24 项 snapshot/CSV 测试通过；serve symlink 修正另有真实红例 |
| book-refactoring-pass | 修改既有 Python 生产代码 | before-dev | passed / proceed；无需前置重构，保留 scope/watermark/cursor/CSV 语义 |
| book-release-readiness | serve 启动行为及持久 runtime 改变 | validation 后 | passed / ready（仅本地 R2.0c）；最终范围绿色、独立 review 已关闭；不等于跨平台、部署或发布就绪 |

严格检查：中文场景＋英文 Given/When/Then，沿用 sbtd-runtime/spec/*.md；SnapshotStore 和真实 serve 为用户指定测试 seam；corruption/sweep/restart/pin/permissions 回归；独立只读 review；可读性与 ponytail-review；project-validation。全仓 run_ci 历史运行约 46 分钟，不视为 quick；优先 runtime suite 与 CI 对应 focused checks，跳过原因最终如实记录。

## 状态持久化限制

已实际调用安装的 TaskStore.create；返回 `TaskStateError: task has no YAML frontmatter block`，未建立本任务或 active 指针。既有 R2.0b 记录同类 catalog 冲突涉及禁止修改的 ai/tasks/codex-verify/；本次不更改该路径。此文件为用户明确要求的共享交付记录，非 TaskStore 成功证据，不承诺自动恢复。ignore 已确认保护 .sbtd/active-task.json 与 ai/tasks/**/reports；未写本地状态。

## 验证证据

### 最终结论与命令

本地 R2.0c 验收完成；当时本地 run **没有自行 push、没有自行开 PR、没有发布**。随后 operator 按 Lord 11:06 指令 push 并开 PR #147，已复核合并（见 closeout 状态事件）。验收代码／测试 tip SHA：`3aab4a96df8588da7288785fceca751b18312c67`。最终 docs-only closeout commit 的完整 tip SHA 与五次提交列表在提交后写入 [reports/closeout-tip.json](reports/closeout-tip.json)，并在会话最终 stdout 输出；该 receipt 是本地 ignored 证据，不入提交。

| 实际命令（仓库根） | 结果 |
|---|---|
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py' -v` | 256 tests，255 passed，0 failed，1 skipped，17.962s；skip 仅 Windows junction |
| `python3 -B -m unittest tests.test_sbtd_runtime_r1_stats_api -v` | 73 tests，72 passed，0 failed，1 skipped，4.428s；为上项子集，不重复加总 |
| `npm --prefix sbtd-runtime/dashboard test` | 22 passed，0 failed，含 R2.0b AC-52 pin 跨轮询保持原 ID |
| `ruff check sbtd-runtime/report_snapshot.py sbtd-runtime/stats_query.py sbtd-runtime/serve.py sbtd-runtime/tests/test_snapshot_persistence.py sbtd-runtime/tests/test_report_snapshot.py sbtd-runtime/tests/test_csv_export.py tests/test_sbtd_runtime_r1_stats_api.py` | passed；此前 `ruff format` 仅格式化改动 Python 文件 |
| `python3 sbtd-runtime/dashboard/check_artifacts.py` | passed；3 files，260361 bytes ≤ 524288 |
| `python3 -B tests/run_ci.py --platform linux --list --output ai/tasks/v2.1.0-rc.2-r2.0c-snapshot-persistence/reports/ci-discovery` | exit 0，2363 selected，包含全部 14 个 SnapshotPersistenceTests；仅发现检查，不称为全仓测试通过 |
| eval `run_restart_smoke()`，实际启动两次 `python3 -B -m serve --port <临时端口> --home <隔离目录> --no-open` | passed；真实 EventStore golden 数据、真实配对／鉴权 HTTP、两次 Ctrl-C exit 0；原 ID、91 行数据、摘要和有效期逐值一致 |

最终原生 raw 与同 stem 中文九节汇总：`reports/validation-final-20261020-1125.{json,md}`。执行区间 2026-10-20T11:23:27.855763+08:00–11:23:55.775732+08:00；Linux 6.12.94+ x86_64、Python 3.13.5。Evidence Source: developer-local；Source Revision: dirty（仅 task.md 验证元数据及用户原有 untracked，生产／测试已提交）；Evidence Publication: local-only；rtk: skipped-for-report（早期 lint 使用 rtk）。中间轮 253 tests / 0 failure 的 `reports/runtime-intermediate-20261020-1118.{json,md}` 保留，不覆盖失败历史或冒充最终证据。

### 逐项验收证据

| AC | 实现／证据 |
|---|---|
| 1：24h 与有效期 | `SnapshotStore(home)` 要求显式 runtime home；默认 86400s；`Snapshot.public_view`、`query`、`timeseries` 返回 expires_at。`test_restart_preserves_snapshot_rows_cursor_and_expiry` 精确比较创建时间＋24h；`test_creation_responses_report_original_expiry` 验证复用不续期。OpenAPI Envelope.data 本已开放，无契约变更。 |
| 2：崩溃一致性 | v1 JSON envelope，SHA-256 canonical payload；temp 0600→flush/fsync→atomic replace→POSIX 目录 fsync→发布内存索引。`test_corrupt_files_are_never_snapshots` 的截断／缺 checksum／错误版本三项及 bool version／checksum 篡改／非法 payload／重复字段均拒读且原件保留；fsync/rename 注入失败不发布半成品；子进程 rename 前 os._exit(73)，遗留 temp 经重启仍不可凭内部 ID 读取。 |
| 3：启动清扫仅 snapshots | `test_startup_sweep_touches_only_owned_expired_snapshots` 实测过期合法快照删除，live snapshot 保留；逐字节验证 exports、audit.db、config、registry、spool、backups、源 task/report/handoff、未知文件、嵌套目录、损坏文件、temp 不变。symlink/hardlink/path traversal 用例证明不越界。 |
| 4：pin 保护 | `pin/release` 计数与 `get/dataset_page/sweep` 共用 RLock；双引用跨到期可读，释放一项仍保留，最后释放后可清扫且旧 ID 不复用；`pinned_snapshot_ids` 在 startup sweep 前安装恢复引用。ADR 0003 §3 与安装文档明确 UI PinRegistry ≠ 后端引用、R2.1a finally release／先恢复引用后构造 store。未实现 exports 或 pin HTTP API。 |
| 5：serve 重启 | 最终 smoke ID `snap_673cb55d87c542a9b17d1ac8b7ab9984`；两次启动 snapshot/dataset 均 HTTP 200，91 行逐值一致；digest `a489df91705038d0a561611f53dec4fdef27a69bc7bc854e04873337dd306fc6`；expires_at `2026-10-21T03:23:55.203985Z` 未改变。库面另测分页 cursor 重启续读。 |
| 6：权限／路径 | `test_private_permissions_include_temporary_file` 实测 home/snapshots 0700，temp/final 0600；只读 preflight 在 serve 首次 mkdir/chmod/lock 前执行；真实 symlink CLI 测试保留外部锁、权限和条目。Windows reparse 属性检查替代 3.12-only junction API；Windows 实机测试 skipped，不声称 ACL 已验证。 |
| 7：清理授权 | ADR 0003 §4、安装文档与场景独立引用 PRD §10.4 临时快照行＋D13；明确 AC-61 不覆盖快照清理，Export 不清理 snapshots，Snapshot 不清理 exports。 |
| 8：ADR | `docs/adr/0003-v2.1.0-rc.2-r2.0c-snapshot-persistence.md`：格式整数 **1**，checksum **SHA-256**（`sha256:<64 hex>`）；不改 ADR 0001/0002 决策。 |
| 9：文档 | `sbtd-runtime/docs/install-and-use.md` 更新布局、退出保留、默认 TTL、重启、清扫、错误处理、pin hook 与恢复／回滚限制；历史 R1.4 报告和场景保留为当时证据，不改写历史。 |

### 严格审查与红绿记录

- 改前 snapshot/CSV 24 项通过；restart tracer 红例为旧构造器把 PosixPath 当 TTL 导致 TypeError，实现后通过。
- corruption 扩展暴露 expires_at=42 在类型验证前触发 AttributeError；改为先验证字段类型，定点与影响子集通过。深嵌套样本在本机未触发 RecursionError；异常处理另用 decoder fault injection 验证，不伪称真实复现。
- 独立正确性 review（`openai-codex/gpt-6.1-sol`）发现新测试未纳入根 CI；已接既有 wrapper，真实 wrapper 73 项与 discovery 14 项证明修正，复核无 findings。
- 独立安全 review（`openai-codex/gpt-6-astra`）发现 serve 先改 symlink 目标再拒绝、Python 3.11 junction fallback、decoder recursion 未分类。真实 CLI 红例证明目标锁被覆盖；修正前置 preflight、reparse 检查、损坏边界处理后，定点两项与最终套件通过，复核无 findings。两位 reviewer 均只读，未执行测试，不把 review 当测试证据。
- Ponytail Review：无需新增抽象、依赖、配置或调度器；保留真实 pin/preflight seam，无建议删减。Code Readability Review：显式磁盘读写／清扫／引用职责，错误处理保持损坏文件，不混入导出或授权 API。
- BDD: traceable；`sbtd-runtime/spec/r2.0c-snapshot-persistence-scenarios.md` 中文场景＋英文关键词，映射 unittest；E2E Mode: backend-only；无浏览器 UI 改动；无跨仓依赖。

### 提交清单

1. `65c3cf30d8acb4a72685683bd410004af48eaf64` — docs backfill：R2.0b #146 done、真实模型纠正、R2.0c strict skeleton 与 plan in_progress。
2. `eb42c680034c540deb4f702af770298d3db35c81` — ADR 0003：format v1 + SHA-256。
3. `86256c34edcc34a64df470ad6e8c124a7a76d614` — 磁盘存储、校验、TTL、启动 sweep、pin、serve preflight、创建 expires_at。
4. `3aab4a96df8588da7288785fceca751b18312c67` — 测试、CI wrapper、中文场景、安装文档。
5. docs-only closeout — 本任务证据与 checking→done；提交后实际完整 SHA 见上述 closeout-tip receipt 与 stdout。最终 commit 不改变运行代码或测试。

### 跳过、风险与恢复边界

- 全仓 `tests/run_ci.py` 历史运行约 46 分钟，不满足用户 “if quick”；只跑相关 wrapper 与真实 discovery。已知历史 `probe_links.test_replaced_link_with_identical_text_is_refused` 未重跑、未修复，不称全仓通过。
- Windows junction 用例本机跳过；macOS/Windows、ACL 与跨平台断电耐久性证据属 R2.2；不扩项。浏览器／Maestro 不适用；静态产物未改，不重复构建。ty executable unavailable，未安装；Python LSP unavailable，源码调用分析补足。
- 24h 是逻辑有效期，物理删除由启动或显式 sweep 执行；没有新定时器。损坏／未知／未来版本文件和遗留 temp 保留，可能占盘；不擅自清理。启动装载全部有效快照，无新容量策略。
- pin 是单 store／单 runtime writer 的引用，不是持久导出作业。R2.1a 若恢复作业，必须恢复引用后再构造 store；不承诺跨进程并发 store 保活。目录检查不宣称抵御同 uid／管理员恶意竞态或重写 checksum。
- 原始 audit.db 不迁移、不清理；回滚旧版本不删新快照，但旧内存实现无法读取它们，可从原事件重新查询。清扫后的已过期 ID 不保存跨重启 tombstone。
- TaskStore 的 catalog 冲突未绕过修复禁止路径；共享任务由明确授权写入，安装 helper 的 TaskDocument 可验证本任务结构，但不声称 active/lifecycle 自动持久化成功。R2.0b 旧 in-progress→done 事件不符合当前 helper schema，作为历史保留，未为本任务改写旧证据。
- 禁止路径未暂存／未提交；contracts、ADR 0001/0002、PRD 与 R2.1a+ planned 行保持不变。无提交外的 scaffolds 或 smoke 脚本。

## CONTRACT-CHANGE-NEEDED

未触发：保持全部既有 contracts、ADR 0001/0002 与 PRD 正文不变。

## 模型使用

计数来源：用户提供的 Reviewy 2026-10-20 11:41 session log 核对；计数口径为 assistant messages，不是工具调用次数。本次仅回填该证据，不冒充重新统计历史日志。

| 用途 | 请求模型 | 实际模型 | assistant messages | 工具调用次数 |
|---|---|---|---|---|
| implementation / validation / closeout 主会话 | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra | 80 | unknown |
| 独立正确性复核 | 默认 reviewer | openai-codex/gpt-6.1-sol | 16 | unknown |
| 独立文件系统／安全复核 | 默认 security-reviewer | openai-codex/gpt-6-astra | 15 | unknown |
| advisor | unknown | xai-oauth/grok-4.6 | 88 | unknown |
| session title generation | unknown | cursor/composer-2.5 | 3 | unknown |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-20T11:05:30+08:00 | planned | in-progress | 用户明确 strict 与 R2.0c 范围，分支及基线匹配；共享记录创建，不声称 TaskStore 持久化成功 | git status/rev-parse；D13；本文件状态持久化限制 |
| 2026-10-20T11:22:25.640823+08:00 | in-progress | checking | 实现、ADR、测试、文档已落地，进入最终计划范围验证与独立复核闭环；TaskStore 自动状态仍未持久化 | 中间轮 runtime 253 通过；根 CI wrapper 73 项/1 skip；真实 serve restart smoke |
| 2026-10-20T11:25:19+08:00 | checking | done | 本地指定验收绿色；两位独立复核关闭；本任务完成不代表 merge／push／PR／部署／发布，plan R2.0c 保持 in_progress | 代码 tip 3aab4a96df8588da7288785fceca751b18312c67；runtime 256/1 skip、CI wrapper 73/1 skip、Dashboard 22、ruff/artifact passed、真实 restart smoke；reports/validation-final-20261020-1125.json 与同 stem 中文汇总 |
| 2026-10-20T15:03:24+08:00 | done | done | Closeout：operator 按 Lord 11:06 指令 push／开 PR 后，#147 squash-merged；本地完成时间不改，不改契约 | 用户 2026-10-20 15:05 指令：merge SHA e9cb05b84e449fe4a7dde1b5523faf7478bc310e；Reviewy CLEAN on tip 2dbf7b1；模型计数据 Reviewy 11:41 log check |
