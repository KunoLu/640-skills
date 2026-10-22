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
| R2.1a | 离线 HTML + 全量 CSV 导出（导出副本 `exports/` 下 24h） | P4 | in_progress（分支 feat/v2.1.0-rc.2-r2.1a-html-csv-export；implement 模型 openai-codex/gpt-6-astra:high） | — | — | — | ai/tasks/v2.1.0-rc.2-r2.1a-html-csv-export/task.md |
| R2.1b | JPEG/PDF 独立 renderer（Playwright 可选 extra，`--only-shell`，精确钉版，renderer 环境含 fonts-noto-cjk） | P5 | planned | — | — | — | ai/tasks/v2.1.0-rc.2-r2.1b-renderer/task.md |
| R2.2 | 跨平台 E2E（CI macOS/Windows runner + 用户 Mac 视觉／字体确认）、安全（Host/Origin、ticket、脱敏分层）、性能、导出对账 | P6 | planned | — | — | — | ai/tasks/v2.1.0-rc.2-r2.2-e2e-security/task.md |
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

- 锁定决定：D11（`exports/` 下 24h 保留、export_id 寻址、0700/0600）、D15（后端输出层统一脱敏）、D16（HTML 纯系统字体栈＋CJK fallback）。
- 验收：离线 HTML 单文件自包含、不加载外部脚本／CDN／字体（§13.4）；CSV 按 schema 1.1 全量 cursor 遍历；导出副本 ready 后默认保留 24h 并带过期清理（含下次启动清扫）；有效期内重复下载同一产物摘要不变（§13.10）；脱敏版本号写入导出 manifest。

### R2.1b — JPEG/PDF 独立 renderer

- 锁定决定：D3（`--only-shell` 安装到扩展自有目录、授权提示按实际模式显示体积）、D4（playwright 精确钉版）、D16（renderer 环境依赖清单含 fonts-noto-cjk 并钉版本）。
- 验收：Playwright 为可选 extra，未安装时仅 JPEG/PDF 标不可用并说明原因；隔离按 §13.7（独立子进程、每作业临时 profile、路由层 abort 一切外联、单作业信号量），AC-58 出断网与隔离证据；PDF 中／日／英混合文字可显示（§13.6、AC-42）；导出前等待字体完成（§13.5）。
- 契约领先实现跟进（[export-failure-states](../v2.1.0-rc.2-contract-export-failure-states/task.md)，用户／Reviewy 2026-10-22 13:14 +08:00）：R2.1b 接入失败路径时，将现有 HTML/CSV 自由文本失败映射为 `EXPORT_RENDER_FAILED`、超时映射为 `EXPORT_RENDER_TIMEOUT`；JPEG/PDF renderer 依赖不可用时在 202 前返回 503 `EXPORT_RENDERER_UNAVAILABLE`（无 job、export_id 或半成品文件，html/csv 不适用），并与 capabilities 的 unavailable 及原因保持一致。该 contract-only 任务不修改 runtime。

### R2.2 — 跨平台 E2E、安全、性能、导出对账

- 锁定决定：D9（CI runner＋用户 Mac 组合证据）、D14（Panel manifest 对账 AC-45）、D15（脱敏三层证据 AC-54/AC-55）；D5–D8 的实现归属 R2.0a（Local Server & Access Control 上下文），本行只对既成实现产出跨平台与安全证据，不改实现。
- 验收：GitHub Actions macOS／Windows runner 跑启动、API、四格式导出与字体断言（AC-33、AC-62），用户 Mac 补一轮视觉／字体确认；报告逐条标注证据来自 CI runner 还是真机，Windows 仅 CI 证据时如实写明；Host/Origin 三组负例（外部域名 Host、错误端口、跨 Origin）锁定（AC-56）；ticket 不落日志、命令行参数可见风险与缓解已入 ADR；四格式关键数值一致（AC-51）与 Panel manifest 对账（AC-45）通过；性能按 §18 基线如实记录。

### E — prerelease v2.1.0-rc.2

- 锁定决定：D10（计划摘要此时回填 CHANGELOG／docs）。
- 验收：tag v2.1.0-rc.2；中英双语发布说明；CHANGELOG 如实记录 R2 范围与已知限制；报告附真实 SHA／环境，不以旧 HEAD 或缓存输出证明新提交。

### F — docs 回填

- 锁定决定：D10（E／F 阶段回填）；PRD 若升 v0.3 须用户届时另行授权。
- 验收：安装与使用文档更新落盘快照 24h 行为（消除 r1.4 报告 deferred 条目对应差异说明）；renderer 安装授权文档按实际所选模式显示体积；PRD 正文不在本任务范围内修改。

## 依赖顺序说明

R2.0c（快照落盘）置于 R2.1a 之前：R2.1a 的导出作业固定 `snapshot_id` 并持引用直到完成，且 24h 保留语义要求快照在服务重启后仍可解析；若导出先于落盘快照落地，重启即在途导出失效、§13.10 重复下载摘要不变的证据不可重复。R2.1b 依赖 R2.1a 的 ReportDocument 序列化产物作为渲染输入。R2.2 依赖全部功能行完成后统一出证据。E／F 依次收尾。

## 风险与边界

- R2.0c 使 R2 范围较 PRD §15.3 原五行表增大，已由用户通过 D13 显式锁定并单列工作包。
- Windows 无真机，证据全部来自 CI runner，报告须如实标注（D9）。
- `#ticket` URL 出现在浏览器启动命令行参数中、同机进程可见；缓解（终端不打印、ticket 短时一次性）与残余风险写入 R2.0a/R2.2 对应 ADR（D7）。
- 本计划不改 PRD v0.2 正文；任何 PRD 偏离或升版须回到用户书面确认。
