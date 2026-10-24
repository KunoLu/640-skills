# v2.1.0-rc.2 实施计划（R2：Local Dashboard + 四格式导出）

依据：PRD v0.2 §15.3 R2 工作包（`docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md`）；grill R1 锁定决定 D1–D17（`grill-r1.md`，用户 2026-10-19 11:47 确认）；底座为 R1 已验收接口（main `eaf26d3`：`sbtd-runtime/` 库面、`contracts/openapi.yaml`、schema 1.1 CSV），不得用 mock 数字冒充真实接口（§15.0）。

## 执行规则（每行适用）

- 每个任务均为 strict 模式 SBTD 任务，任务记录落 `ai/tasks/<id>/task.md`。
- 每个 PR 的第一个 commit 回填上一行的 PR、merge SHA 与完成时间（+08:00）。
- Reviewy 在 tip 上 CLEAN 后，Lord squash-merge；合并后本地与远端分支均删除。
- 锁定决定编号（D1–D17）见 `grill-r1.md`「锁定决定清单」。

## 任务表（按优先级排序）

| seq | 任务 | 优先级 | 状态 | PR | merge SHA | 完成时间 | strict 任务记录 |
|---|---|---|---|---|---|---|---|
| 0 | 计划：grill + DDD + 任务表 | P0 | done（PR #141 已 squash-merge；Reviewy DDD Boundary Review 复审通过） | #141 | a55117c | 2026-10-19T13:09:42+08:00 | ai/tasks/v2.1.0-rc.2-plan/task.md |
| R2.0a | OMP 风格单页、Panel registry（`contracts/panel-manifest.json` + golden 钉测）、ReportDocument、`serve` 启动与访问控制（D5–D8） | P1 | done（PR-1 #142 与 PR-2 #144 均已 squash-merge；closeout 回填 PR #145 已 squash-merge） | #142（PR-1）；#144（PR-2）；#145（closeout 回填） | 3c9cf4e（PR-1）；8178b26abe75454b958d096ff58522eda7facbb4（PR-2）；1415134817015580067274b843cc73bcc8e37441（#145） | 2026-10-19T22:54:44+08:00（#145 合并、行正式关闭；PR-2 功能合并 2026-10-19T22:27:23+08:00） | ai/tasks/v2.1.0-rc.2-r2.0a-dashboard/task.md（PR-1）；ai/tasks/v2.1.0-rc.2-r2.0a-serve/task.md（PR-2） |
| R2.0b | 筛选、数据质量、页内详情 | P2 | done（PR #146 已 squash-merge；requested astra; actual k3/grok per session logs） | #146 | 2d147c98ce2874fa2621b95ff816e1781c02f93f | 2026-10-20T04:14:03+08:00 | ai/tasks/v2.1.0-rc.2-r2.0b-filters-detail/task.md |
| R2.0c | 临时 ReportSnapshot 落盘：24h 默认保留＋启动清扫过期＋崩溃一致性 | P3 | done（PR #147 已 squash-merge；Reviewy CLEAN on 2dbf7b1） | #147 | e9cb05b84e449fe4a7dde1b5523faf7478bc310e | 2026-10-20T15:03:24+08:00 | ai/tasks/v2.1.0-rc.2-r2.0c-snapshot-persistence/task.md |
| R2.1a | 离线 HTML + 全量 CSV 导出（导出副本 `exports/` 下 24h） | P4 | done（PR #151 已 squash-merge；requested astra; implement 起于 openai-codex/gpt-6-astra:high，2026-10-20 21:19 起 fallback 到 xai-oauth/grok-4.7，后续轮次 kimi-code/k3:max，per session logs） | #151 | 8931c35ef1aa4a58d3675b6f8d1a8fead309ed90 | 2026-10-21T07:07:34+08:00 | ai/tasks/v2.1.0-rc.2-r2.1a-html-csv-export/task.md |
| R2.1b | JPEG/PDF 独立 renderer（Playwright 可选 extra，`--only-shell`，精确钉版，renderer 环境含 fonts-noto-cjk）；#153 合并 ce80ca2 经 376ea0c merge 纳入后接线 HTTP jpeg/pdf | P5 | done（PR #155 已 squash-merge；openai-codex/gpt-6-astra:high 主会话，reviewer 子代理 kimi-code/k3，per session logs） | #153（契约已合并）；本行实现 PR [#155](https://github.com/KunoLu/640-skills/pull/155) | c5904ef787c29bf9761f44ca4613ce0f2805daa4 | 2026-10-22T16:22:16+08:00 | ai/tasks/v2.1.0-rc.2-r2.1b-renderer/task.md |
| R2.2 | 跨平台 E2E（CI macOS/Windows runner + 用户 Mac 视觉／字体确认）、安全（Host/Origin、ticket、脱敏分层）、性能、导出对账 | P6 | planned | — | — | — | ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/task.md |
| Docs | 后续项 B（`install-and-use.md` 事件明细屏蔽说明）+ 后续项 C（第 7 项，单独 PRD docs PR） | P6.5 | planned | — | — | — | —（执行时建立 strict 任务记录） |
| E | prerelease v2.1.0-rc.2：中英双语发布说明 + CHANGELOG | P7 | planned | — | — | — | ai/tasks/v2.1.0-rc.2-e-prerelease/task.md |
| F | docs 回填 | P8 | planned | — | — | — | ai/tasks/v2.1.0-rc.2-f-docs-backfill/task.md |

## 各行锁定决定与验收

### 0 — 计划（grill + DDD + 任务表）

- 锁定决定：本轮产出 D1–D17 本身；Q5-C（D10）决定本计划放任务目录而非 PRD。
- 状态：done。R1 全部 17 个子问题已由用户 2026-10-19 11:47 锁定；Reviewy 按 book-ddd-distilled-modeling 出的独立 DDD Boundary Review 意见已全部折入（grill-r1.md 修订记录 R1e），复审通过；随 PR #141 squash-merge 入 main（merge SHA `a55117c`，完成时间 2026-10-19T13:09:42+08:00）。
- 验收：D1–D17 写入 `grill-r1.md`；DDD 初稿按锁定结果更新；本任务表落地；Boundary Review 通过。

### R2.0a — OMP 风格单页、Panel registry、ReportDocument

- PR 拆分（用户 2026-10-19 13:40「按建议拆」）：PR-1（前端骨架＋manifest＋重建一致 CI＋ADR 0002）已 squash-merge——PR #142，merge SHA `3c9cf4e`，完成时间 2026-10-19T17:32:13+08:00；PR-2（`serve` 与访问控制 D5–D8）已 squash-merge——PR #144，merge SHA `8178b26abe75454b958d096ff58522eda7facbb4`，完成时间 2026-10-19T22:27:23+08:00，任务记录 `ai/tasks/v2.1.0-rc.2-r2.0a-serve/task.md`。本行随 PR-2 合并记 done。

- 锁定决定：D1（产物入仓＋重建一致 CI）、D2（Vite 精确钉版）、D14（`contracts/panel-manifest.json` 单一事实源）、D17（仅参考 OMP 视觉、零复制）；Local Server & Access Control 上下文的实现——D5（端口占用即启动失败并提示 `--port`）、D6（前台 Ctrl-C、默认 `--open`、实例锁＋端口双判、陈旧锁按无效处理）、D7（一次性 ticket 经 fragment 配对换 session／Bearer、读后即毁、不进日志）、D8（Host／Origin 严格白名单，规则硬编码）。
- 验收：Panel manifest schema 版本化并有 golden 钉测（仿 `test_golden_contracts`）；前端注册表与 ReportDocument 均由 manifest 派生；源码重建产物与入仓产物逐字节一致的 CI 检查通过；设计规格把 OMP 参考点写成自有 token 定义；产物体积预算与 npm 审计基线由本任务 ADR 固定；`serve` 按 D5–D8 实现启动、实例锁、配对与 Host／Origin 校验（本任务出实现与单测，`#ticket` URL 命令行参数可见风险与缓解写入本任务 ADR），跨平台与安全证据由 R2.2 统一产出。
- Closeout 回填（R2.0b 首个 commit 补记）：docs 回填 PR #145 已 squash-merge 入 main，merge SHA `1415134817015580067274b843cc73bcc8e37441`，合并时间 2026-10-19T22:54:44+08:00；该 PR 把 PR-2（#144，`8178b26abe75454b958d096ff58522eda7facbb4`，2026-10-19T22:27:23+08:00）合并后的 R2.0a 行与两条任务记录记为 done 并补 models-used 证据。

### R2.0b — 筛选、数据质量、页内详情

- 锁定决定：D12（30 秒轮询自动整份替换、保留上一份视图并标注、常显水位时间）。
- 验收：应用筛选后全页 Panel 与详情共用同一 `snapshot_id`（§12.5）；data-quality Panel 如实声明覆盖／缺口／未关联，不以 0 或绿灯冒充（AC-39）；自动刷新不影响在途导出（AC-52）。

### R2.0c — 临时 ReportSnapshot 落盘（Q6c-A 独立工作包）

- 锁定决定：D13（落盘 `snapshots/`、24h TTL、启动清扫、清理仅触及本扩展自有目录）。
- 验收：`SnapshotStore` 由进程内 3600s 改为落盘 24h 默认，创建时返回有效期；崩溃一致性测试——半成品快照文件（写一半、缺校验和、版本头不符）永不被当作有效快照，写入路径为「写临时文件＋原子 rename＋校验和／版本头」；启动时清扫过期快照且仅触及 `snapshots/`；清理授权边界按 §10.4 单独立据（AC-61 不覆盖快照清理）；文件格式版本号与校验和算法由本任务 ADR 固定。

### R2.1a — 离线 HTML + 全量 CSV 导出

- 状态：done；PR #151 已 squash-merge，merge SHA `8931c35ef1aa4a58d3675b6f8d1a8fead309ed90`，完成时间 `2026-10-21T07:07:34+08:00`（mergedAt `2026-10-20T23:07:34Z`）；实际模型沿革见任务表及 R2.1a session logs。
- 锁定决定：D11（`exports/` 下 24h 保留、export_id 寻址、0700/0600）、D15（后端输出层统一脱敏）、D16（HTML 纯系统字体栈＋CJK fallback）。
- 验收：离线 HTML 单文件自包含、不加载外部脚本／CDN／字体（§13.4）；CSV 按 schema 1.1 全量 cursor 遍历；导出副本 ready 后默认保留 24h 并带过期清理（含下次启动清扫）；有效期内重复下载同一产物摘要不变（§13.10）；脱敏版本号写入导出 manifest。

### R2.1b — JPEG/PDF 独立 renderer

- 状态：done；PR #155 已 squash-merge，merge SHA `c5904ef787c29bf9761f44ca4613ce0f2805daa4`，完成时间 `2026-10-22T16:22:16+08:00`（mergedAt `2026-10-22T08:22:16Z`；git committer 时间 `2026-10-22T16:22:15+08:00`）；实际模型沿革见任务表及 R2.1b task/session logs。
- 锁定决定：D3（`--only-shell` 安装到扩展自有目录、授权提示按实际模式显示体积）、D4（playwright 精确钉版）、D16（renderer 环境依赖清单含 fonts-noto-cjk 并钉版本）。
- 验收：Playwright 为可选 extra，未安装时仅 JPEG/PDF 标不可用并说明原因；隔离按 §13.7（独立子进程、每作业临时 profile、路由层 abort 一切外联、单作业信号量），AC-58 出断网与隔离证据；PDF 中／日／英混合文字可显示（§13.6、AC-42）；导出前等待字体完成（§13.5）。
- 范围：contract PR #153 已 squash-merge 为 `ce80ca2`，并经 `376ea0c` merge 纳入本分支；Round 4 接线 HTTP jpeg/pdf。JPEG 在 202 前对同一静态 HTML 预检，超限 422 携带有效 caps，降级 warning 在 202 meta，作业固定预检比例；PDF 不做图像预检。当时保持 in_progress（review pending），现已随 #155 合并记 done。
- 契约 PR #153（https://github.com/KunoLu/640-skills/pull/153；status merged；由另一 agent 提交，非本行实现 PR）。范围：`CreateExportRequest.format` 增加 `jpeg`、`pdf`；仅 createExport 预接受 422，错误体 `{detail: 'EXPORT_IMAGE_SIZE_LIMIT', max_edge_px, max_total_pixels}`；202 `meta.warnings` 精确字符串 `EXPORT_SCALE_DOWNGRADED:1x`；golden tests。不含磁盘上限错误码（仍归 10-21 计划第 4 项）；后续项 C 归第 7 项的单独 PRD docs PR，现移至 E 前 Docs 步骤。R2.1b 不修改 OpenAPI；renderer 不可用与 post-202 异步失败两个契约缺口已由 contract PR #154（`d46d4ad`，2026-10-22 14:33:35 +08:00 合并）关闭，并在 R2.1b Round 6（`18de842`）实现。
- AC-51 完整验收仍归 R2.2；R2.1b 仅保留四格式 event-detail 屏蔽集合／计数一致性测试，作为后续项 A 决定的回归保护，不宣称 AC-51 已通过。
- 契约领先实现跟进（[export-failure-states](../v2.1.0-rc.2-contract-export-failure-states/task.md)，用户／Reviewy 2026-10-22 13:14 +08:00）：**已完成**。固定字符串 `export failed` 已被 contract #154（`d46d4ad`）取代，并在 R2.1b Round 6（`18de842`）实现：所有格式（含 HTML／CSV）的 failed 作业使用 `EXPORT_RENDER_FAILED`，renderer 超时使用 `EXPORT_RENDER_TIMEOUT`；JPEG／PDF renderer 依赖不可用时在 202 前返回 503 `EXPORT_RENDERER_UNAVAILABLE`（无 job、export_id 或半成品文件，html/csv 不适用），与 capabilities 的 unavailable 及原因保持一致。原 contract-only 任务不修改 runtime；runtime 接线由 R2.1b Round 6 完成。

### R2.2 — 跨平台 E2E、安全、性能、导出对账

- 锁定决定：D9（CI runner＋用户 Mac 组合证据）、D14（Panel manifest 对账 AC-45）、D15（脱敏三层证据 AC-54/AC-55）；D5–D8 的实现归属 R2.0a（Local Server & Access Control 上下文），本行只对既成实现产出跨平台与安全证据，不改实现。
- 验收：GitHub Actions macOS／Windows runner 跑启动、API、四格式导出与字体断言（AC-33、AC-62），用户 Mac 补一轮视觉／字体确认；报告逐条标注证据来自 CI runner 还是真机，Windows 仅 CI 证据时如实写明；Host/Origin 三组负例（外部域名 Host、错误端口、跨 Origin）锁定（AC-56）；ticket 不落日志、命令行参数可见风险与缓解已入 ADR；四格式关键数值一致（AC-51）与 Panel manifest 对账（AC-45）通过；性能按 §18 基线如实记录。R2.2 实现 507 时须新增 HTTP 回归：已受理同 key 重放在配额超限下仍返回原 202、无新 job；新请求 507 位于 410 之后、422 之前。
- PR 拆分（用户 2026-10-23 12:11 +08:00 群内说开始 R2.2，Lord 记录）：PR-1 配额与 507 → PR-2 安全 → PR-3 跨平台 E2E 与对账 → PR-4 性能、校准与收尾；严格串行，每个 PR 首个 commit 回填上一 PR；行状态至 PR-4 收尾前不变。（归因更正（append-only）：用户 2026-10-23 12:11 +08:00 群内说开始 R2.2，Lord 按 plan.md 定拆分为 4 个串行 PR，Lord 记录。）
- PR-1 已 squash-merge——PR [#162](https://github.com/KunoLu/640-skills/pull/162)，merge SHA `83b14baee4e282d4863e693813b14a02c2b126b3`，完成时间 `2026-10-23T14:18:38+08:00`（mergedAt `2026-10-23T06:18:38Z`；git committer 时间一致）；编排方整理，本轮 git log 核实 SHA／committer 时间。R2.2 行状态保持 planned 至 PR-4 收尾。
- PR-2 已 squash-merge——PR [#163](https://github.com/KunoLu/640-skills/pull/163)，merge SHA `4d29fc5a76482950965d929715d3096e66a57b54`，head `2d2dbb2c18a0e130d8e63a9994fa0c64e7147cc5`；git committer `%cI` 为 `2026-10-23T15:59:11+08:00`（本轮 git log 核实）；GitHub mergedAt 为 `2026-10-23T15:59:12+08:00`（`2026-10-23T07:59:12Z`，编排方整理），两者相差 1 秒，分别记录。R2.2 行保持 planned 至 PR-4。
- PR-3 已 squash-merge——PR [#164](https://github.com/KunoLu/640-skills/pull/164)，merge SHA `253dceccc77fb0b7b929a81ac28e4c53d6968240`，head `38b3b56aca559d729487665b822c76b48cf8c1f9`；git committer `%cI` 为 `2026-10-24T00:05:38+08:00`（本轮 git 核实）；GitHub mergedAt 为 `2026-10-24T00:05:38+08:00`（`2026-10-23T16:05:38Z`，编排方整理），两者相等但分别记录。合并前 CI 13/13 on `38b3b56`（run `39980290926`，编排方整理；本轮未重跑 CI）。R2.2 行保持 planned 至 PR-4。
- statistics/query 507 契约 PR 已 squash-merge——PR [#165](https://github.com/KunoLu/640-skills/pull/165)，merge SHA `9ceb53021aa5e90d6369eed037f0b05ab719e928`，head `5bb8a564ea165c784d034eb7145def7c8b8793fc`；git committer `%cI` 为 `2026-10-24T10:10:14+08:00`（本轮 git log 核实）；GitHub mergedAt 为 `2026-10-24T10:10:14+08:00`（`2026-10-24T02:10:14Z`，编排方整理），两者相等但分别记录。合并前 CI 13/13 on `5bb8a56`（run `40051092799`，编排方整理；本轮未重跑 CI）；Reviewy CLEAN @5bb8a56（编排方整理）。R2.2 行保持 planned 至 PR-4。

### Docs — 后续项 B／C（E 前）

- 顺序依据：用户 2026-10-22 23:23 +08:00 群内确认（顺序按推荐），Lord 记录；仅将 B／C 从 F 移到 E 前，使用 P6.5，E P7／F P8 不变。
- 后续项 B：在 `install-and-use.md` 写明 `exportable=false` 仅屏蔽事件明细行，同时明确 `classification != local-metadata` 也屏蔽事件明细；task/run/aggregate 派生行不屏蔽。依据「用户 11:15 授权，10-22 15:00 确认放第 7 项」。
- 后续项 C：第 7 项另开单独 PRD docs PR，与 B 两种屏蔽条件及派生行边界措辞一致；独立于第 4 项磁盘上限 PRD docs PR。本轮仅调整计划，不改 PRD。

### E — prerelease v2.1.0-rc.2

- 锁定决定：D10（计划摘要此时回填 CHANGELOG／docs）。
- 验收：tag v2.1.0-rc.2；中英双语发布说明；CHANGELOG 如实记录 R2 范围与已知限制；报告附真实 SHA／环境，不以旧 HEAD 或缓存输出证明新提交。

### F — docs 回填

- 锁定决定：D10（E／F 阶段回填）；PRD 若升 v0.3 须用户届时另行授权。
- 验收：安装与使用文档更新落盘快照 24h 行为（消除 r1.4 报告 deferred 条目对应差异说明）；renderer 安装授权文档按实际所选模式显示体积；常规 docs 回填 PR 不修改 PRD 正文。本轮仅登记，不改 PRD。
- 后续项 B／C：已移至 E 前 Docs 步骤（P6.5，见上文「Docs — 后续项 B／C（E 前）」），F 不重复执行；顺序依据用户 2026-10-22 23:23 +08:00 群内确认（顺序按推荐），Lord 记录。

## 依赖顺序说明

R2.0c（快照落盘）置于 R2.1a 之前：R2.1a 的导出作业固定 `snapshot_id` 并持引用直到完成，且 24h 保留语义要求快照在服务重启后仍可解析；若导出先于落盘快照落地，重启即在途导出失效、§13.10 重复下载摘要不变的证据不可重复。R2.1b 依赖 R2.1a 的 ReportDocument 序列化产物作为渲染输入。R2.2 依赖全部功能行完成后统一出证据。其后 Docs（B／C）→ E → F 依次收尾。

## 2026-10-21 计划定稿（13:02 +08:00）

以下顺序于 2026-10-21 13:02 +08:00 定稿；第 4／7 项的 C 放置按 10-22 15:00 用户决定更新，现归第 7 项／F：

1. R2.1b。
2. 后续项 A 决策已定 — 用户 2026-10-22 11:13 +08:00：保持 #151 行为（事件明细行按 `exportable=false`／`classification != local-metadata` 屏蔽；task/run/聚合派生行不屏蔽；不新增 `withheld` 值；不开 contract PR）。
3. R2.1b 评审与合并。
4. 磁盘上限 PRD §10.4 补充已 done：独立 PRD docs PR [#156](https://github.com/KunoLu/640-skills/pull/156) 已 squash-merge，merge SHA `b73ebe501cb529d11e6829b02a363fd7f4f4274a`，完成时间 `2026-10-22T17:42:55+08:00`（mergedAt `2026-10-22T09:42:55Z`；git committer 时间 `2026-10-22T17:42:54+08:00`）。ADR 0003 §4/§5 修订已 done：PR [#157](https://github.com/KunoLu/640-skills/pull/157) 已 squash-merge，merge SHA `6c344d13ddf6b49882b87d52300b8d697e8aeec4`，完成时间 `2026-10-22T18:36:03+08:00`（mergedAt `2026-10-22T10:36:03Z`；git committer 时间 `2026-10-22T18:36:02+08:00`）。磁盘上限新错误码 contract PR 已 done：PR [#158](https://github.com/KunoLu/640-skills/pull/158) 已 squash-merge，merge SHA `82d42a20a6dc757356173535148fdcc7c0b9024d`，完成时间 `2026-10-22T20:23:39+08:00`（mergedAt `2026-10-22T12:23:39Z`；git committer 时间 `2026-10-22T20:23:39+08:00`，一致）；用户于 2026-10-22 20:23 +08:00 确认三项值：错误码 `DISK_QUOTA_EXCEEDED`、HTTP 507、body 字段 `detail`／`used_bytes`／`quota_bytes`。
5. R2.2（含磁盘上限实现、跨平台 E2E、AC-56、AC-45、性能与容量实测校准默认值）。
6. E 预发布。
7. F 文档 + 后续项 B + 后续项 C：B 在 `install-and-use.md` 写明事件明细屏蔽范围；C 在 F 阶段另开单独 PRD docs PR，补充「本地导出屏蔽 event-detail 行，当 `exportable=false` 或 `classification != local-metadata`；不影响 task/run/aggregate 派生行」，两种屏蔽条件均须明确，B／C 措辞一致。依据「用户 11:15 授权，10-22 15:00 确认放第 7 项」。该 PR 独立于第 4 项磁盘上限 PRD docs PR；本轮不改 PRD。

后续项 A 已决定，不再待定；JPEG/PDF 与 HTML/CSV 共用 #151 过滤路径。A 不需要 contract PR。JPEG/PDF HTTP 格式与图像尺寸错误码由独立 PR #153（已合并 `ce80ca2`，经 `376ea0c` merge 纳入 R2.1b）承担；这不取代第 4 项磁盘上限错误码 contract PR。后续项 C 按 15:00 决定归第 7 项／F 阶段。AC-51 完整验收仍归 R2.2，R2.1b 只提供四格式事件明细屏蔽一致性回归保护。

2026-10-23 更新（用户 2026-10-22 23:23 +08:00 群内确认（顺序按推荐），Lord 记录）：B／C 移至 E 前 Docs P6.5；第 7 项编号保留。

后续项 D（首见 R2.1b task「后续项 D」，PR #156 引用）：Idempotency-Key 幂等重放先于 renderer 可用性检查；契约已 done：PR [#159](https://github.com/KunoLu/640-skills/pull/159) 已 squash-merge，merge SHA `de97926811410e7d61d846fc8e95ddaa0738bfbf`，完成时间 `2026-10-22T22:43:15+08:00`（mergedAt `2026-10-22T14:43:15Z`；git committer 时间 `2026-10-22T22:43:14+08:00`）。runtime 实现由本分支 `fix/v2.1.0-rc.2-idempotent-replay-before-503` 承担，状态 in_progress，任务记录 `ai/tasks/v2.1.0-rc.2-idempotent-replay-before-503/task.md`，不再归 R2.2；配额实现仍归 R2.2。R2.2 实现 507 时须新增 HTTP 回归：已受理同 key 重放在配额超限下仍返回原 202、无新 job；新请求 507 位于 410 之后、422 之前。（2026-10-23 回填：runtime PR [#160](https://github.com/KunoLu/640-skills/pull/160) 已 squash-merge，merge SHA `e748a5eddfba38cd487af9dfc5271e601de7c76b`，完成时间 `2026-10-23T11:28:33+08:00`（mergedAt `2026-10-23T03:28:33Z`；git committer 时间一致），状态 done，与其 task.md status done 一致。）（状态对齐注记：上文「状态 in_progress」为 #160 开工时记录，现以 done 为准，与 `ai/tasks/v2.1.0-rc.2-idempotent-replay-before-503/task.md` status done 一致。）

2026-10-23 回填：rc.2 第 2 步 PRD §9.6 Idempotency-Key payload 冲突（option A）PR [#161](https://github.com/KunoLu/640-skills/pull/161) 已 squash-merge，merge SHA `cb12b606f1ec74d8bc87da12dd0d828628fa7724`，完成时间 `2026-10-23T12:01:59+08:00`（mergedAt `2026-10-23T04:01:59Z`；git committer 时间一致），任务记录 `ai/tasks/v2.1.0-rc.2-prd-9-6-idempotency-conflict/task.md`。

### 磁盘上限决定（用户 2026-10-21 12:58 +08:00 批准）

`snapshots/` 和 `exports/` 共用一个按字节计的配额，默认 2 GB，可用环境变量调整，80% 预警。每次新建快照或导出前清掉过期且未被 pin 的文件和残留临时文件，不加定时器；清完仍超限则拒绝新建并返回明确错误（含已占用量与上限），不淘汰未过期快照；损坏／无法识别的文件不删但计入占用。

实现与容量实测校准默认值归 R2.2；PRD §10.4 补充已随 #156 完成，ADR 0003 §4（清扫可触及 exports/ 与临时文件）与 §5（新增环境变量配置面）修订已随 #157 完成，独立错误码 contract PR 已随 #158 完成（merge SHA 与两类时间见上方第 4 项）；用户于 2026-10-22 20:23 +08:00 已确认 `DISK_QUOTA_EXCEEDED`、HTTP 507 与 `detail`／`used_bytes`／`quota_bytes`，附 golden 测试；本轮不实施配额。

## 风险与边界

- R2.0c 使 R2 范围较 PRD §15.3 原五行表增大，已由用户通过 D13 显式锁定并单列工作包。
- Windows 无真机，证据全部来自 CI runner，报告须如实标注（D9）。
- `#ticket` URL 出现在浏览器启动命令行参数中、同机进程可见；缓解（终端不打印、ticket 短时一次性）与残余风险写入 R2.0a/R2.2 对应 ADR（D7）。
- 本计划不改 PRD v0.2 正文；任何 PRD 偏离或升版须回到用户书面确认。
