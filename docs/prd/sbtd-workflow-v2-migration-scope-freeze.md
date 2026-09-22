# P2-01：迁移范围、备份责任与保留安排冻结

## 1. 授权与边界

- 任务：P2-01；唯一状态事实源为[主 PRD §14](sbtd-workflow-v2-trellis-removal-graft-migration-prd.md#14-优先级实施台账)。
- 开发起点：`main` `03541a97f3804f8966cd5c4ff3f579793f9d4175`；任务分支 `p2-01-migration-scope-freeze`。
- 用户授权：开始 P2 与 P2-01 冻结。没有 apply、独立部署、cleanup、本机 workflow sync、hooks opt-in、全局卸载、rc/tag、正式发布或备份销毁授权。
- 本项交付：把本批 **release scope**、host/HOME 批次、非敏感 custodian、私有 `backup_root`、保留/复核安排和**拟**清理范围写成可回读记录。盘点只读；私有准备不等于批准 apply。
- 本配置源仓库不是默认迁移目标。未点名的用户项目、`~/.codex`、`~/.omp` 或其他 HOME **不得扫描**。Git author、OS 用户、lessons 分隔名 `640` 都不能当成 custodian。

## 2. Book Gate Plan

Gate Plan 只使用 `planned / running / passed / blocked / not-required`。各 reviewer 的结果词表写在独立审查节，不填进本表。

| Gate | 判定／触发事实 | 状态 |
|---|---|---|
| DDIA | required；本项冻结迁移范围、备份所有权、私有准备、保留门与恢复边界，设计稳定前必须审查 | passed |
| Legacy safety | 无既有行为缺陷修复，不改生产运行代码 | not-required |
| DDD | 无新领域术语或上下文归属变化 | not-required |
| Refactoring | 不改生产实现 | not-required |
| Release readiness | 本项不是 rc、v2.0.0 或真实部署完成 | not-required |
| grill-with-docs | 沿用已批准迁移边界，无新实质歧义 | not-required |

本仓库仍不创建 `.trellis/`、`ai/tasks/` 或 `.feature`。真实目标项目的新目录不自动变成本仓库目录。已记录用户部分原文；HOME/Skill 根、共享闭包、未选平台、backup_root、保留与拟清理仍未冻结。当前会话环境变量不得自动当成真实 HOME。

### 2.1 DDIA Data Design Review

```text
DDIA Data Design Review
Status: confirmed
Data owner and source of truth: 用户拥有真实项目树和 HOME。非敏感 custodian（用户原文，不得从 Git/OS/lessons 推断）拥有 backup_root、原件、候选、阶段/恢复收据和已登记副本。本冻结文件与主 PRD 只拥有可追踪协议层：逻辑名、host 选择、保留政策、拟清理类别、私有记录是否回读成功。目标项目绝对路径、HEAD、工作区状态与目录结构只进私有层。manifest 尚未存在；plan 之后才成为迁移绑定事实源。task.md 不因本项成为迁移 SoT。
Write / read / async / failure paths: 第 3 节字段全部齐后，才开始第 4 节授权盘点。点名本身不是盘点授权。字段未齐时不得访问目标项目任何路径，包括项目根 `AGENTS.md`；“先读 AGENTS.md”只是盘点开始后的第一步，不是提前读取许可。字段未齐时的项目读取是门禁外观察，不得填第 3 节当前值，不得计入第 6 节，也不得把精确路径或项目规则正文写入本文件或主 PRD。本源仓只写冻结协议与台账。私有准备记录只在用户给出删除范围外路径后写入；私有准备不等于 apply。任一项第 3 节字段缺失则保持 in-progress，不进 P2-02，不写项目/HOME。未点名路径不扫描。无队列/后台/跨服务异步。
Consistency model: 范围以用户原文为强一致输入。第 4 节盘点是字段齐后对点名路径的当时观察，不承诺之后不变。门禁外观察不是盘点，也不能当 apply 前态。共享 HOME/Skill 消费者要么整批纳入，要么明确隔离；未知消费者时全局卸载 not-allowed。原件指纹与敏感路径只留私有层。
Idempotency / ordering / retry / deduplication: 重复记录同一 pending 字段不是突变。同一项目点名两次不扩大扫描。拟清理清单不是 P2-05 清理确认，也不是 P3-04 销毁授权。cleanup/recovery/uninstall 永不删备份。
Schema / migration / backfill / rollback / replay: 本项不改迁移 schema、不 apply、不 backfill。它冻结后续 plan 必填 HITL 输入。实现变化后仍须重新 plan，不复用未绑定的旧盘点或门禁外观察当 apply 前态。回滚本项只需撤回协议文档；因尚未写用户数据，无数据回放。若在 manifest 前放弃，终止分支仍须在删除范围外私有记录保存并回读 custodian/归属/精确范围/独立授权/确认时间。
Observability and repair: 协议层表格显示 pending/已填，且只显示逻辑名。私有层保存精确路径/大小/checksum 并回读。回读失败视为未冻结。无后台催办；在 P2/P3 检查点由责任人复核，间隔 ≤30 天。
Required tests: 第 3 节齐后才开始第 4 节；盘点第一步才读项目根 `AGENTS.md`。证明本文件与主 PRD 不含目标项目绝对路径、HEAD、原件指纹、盘点结构或项目 `AGENTS.md` 正文。独立 review 无剩余 P0/P1。不把门禁外观察、提前读 `AGENTS.md` 或后续 apply/恢复演练算作本项通过。
```

本审查确认的是冻结协议本身可以稳定：缺字段就 fail-closed。它不是真实 apply、部署、cleanup、sync、tag 或备份销毁授权。已接受的原文见第 3 节；未齐字段保持 pending，不进 P2-02。

## 3. 本项必须冻结的字段

以下任一项缺失，P2-01 保持 in-progress，不进入 P2-02，不写项目／HOME。

| 字段 | 必须由用户提供 | 当前值 |
|---|---|---|
| 至少一个实际项目根 | 用户提供绝对路径与当前分支或 `detached:<full-sha>` 或明确非 Git；**精确路径只进私有层**，本表只记逻辑名与声明分支 | 已接受逻辑名 `demo`，声明分支 `main`。精确路径、HEAD、工作区与远程跟踪不进本文件。**640-skills 不纳入。** |
| 每个项目的旧 Trellis 结构 | 用户说明或第 4 节授权盘点后记录；不猜版本。协议层只记类别／是否存在，细节进私有层 | pending。用户未说明版本或结构。字段未齐前不得盘点填此栏。 |
| 验证 host | Codex、OMP 或两者 | 已接受：两者 |
| 有效 HOME / Skill 根 | 每个 host 的实际配置根；共用者须整批纳入或明确隔离。精确路径只进私有层 | pending。用户要求先解释。未扫描未点名 HOME。当前会话环境变量不得自动冻结。 |
| 共享批次闭包 | 同 HOME／Skill／全局入口的依赖项目名单，或隔离方案 | pending。仅点名 demo；未知同 HOME 消费者时不得假设独用。 |
| 未选平台 | Claude／Kimi 等只盘点、不修改；依赖未解前禁止全局卸载 | pending |
| 非敏感 custodian | 责任人标识；不从 Git/OS/lessons 推断 | 已接受用户原文：`kuno`。未从 Git/OS/lessons 推断。 |
| 私有 `backup_root` | 仓库外专用目录；不得与受管目标互相包含。精确路径只进私有层 | **拒绝**用户给出的通用下载目录：不是专用 backup_root。待用户给出空的专用目录。精确路径不进本文件。 |
| 最低保留与复核 | 默认：覆盖 P3 两周观察，并至少保留至正式发布后 14 天，取较晚者；首次及后续间隔 ≤30 天 | pending。用户要求先解释默认政策，尚未书面接受或给出更严规则。 |
| 拟清理范围 | 项目旧目录／受管接线／全局旧工具分别列出；本批是否允许全局清理 | pending。协议默认推荐（不是盘点证据）：本批只盘点；项目内受管旧条目待第 4 节后才可列为 P2-05 候选；共享消费者未明时全局卸载 not-allowed。用户尚未书面接受。 |
| 本配置源仓库 | 默认不纳入 | 已接受：不纳入 |
| 可选仓库外私有冻结文件 | 可选；只读用户点名的一份 | 已接受：不需要 |
| 私有准备记录位置 | 删除范围外、可写、可回读的既有私有记录或迁移报告路径。精确路径只进私有层 | pending。可在专用 `backup_root` 内另建；不等于上面的可选冻结文件。 |

推荐澄清选项不能代替这些事实。第 3 节全部字段有用户原文后，才允许按第 4 节只读已点名路径；未点名路径始终不读。用户给出的精确路径写入私有层后，本文件只保留逻辑名。

### 3.1 本轮用户原文与裁决（2026-09-22）

1. 项目：逻辑名 `demo`，声明分支 `main`。未写该项目。精确路径不进本文件。
2. host：Codex 与 OMP。
3. HOME／Skill 根：用户先要解释，未提供路径。
4. custodian：`kuno`。
5. `backup_root`：用户给出的通用下载目录已拒绝。
6. 保留政策：用户先要解释，未接受默认值。
7. 拟清理：用户要推荐；推荐尚未变成用户原文。
8. 640-skills：不纳入。
9. 可选私有冻结文件：不需要。

字段不齐，P2-01 保持 in-progress。未备份、未 apply、未 sync、未清理。

### 3.2 门禁外观察（不得推进 P2-01）

2026-09-22 在 HOME/Skill 根、共享闭包、未选平台、`backup_root`、保留与拟清理仍 pending 时，曾读取点名项目 `demo` 的项目根。该读取早于第 4 节，**不是盘点**。当时取得的精确路径、HEAD、工作区状态与目录结构：

- 不得写入第 3 节当前值，也不得留在本文件或主 PRD
- 不得满足第 6 节第 2 项
- 不得作为拟清理清单或共享闭包证据
- 字段齐后必须按第 4 节重新盘点；精确路径只进私有层；不得复用本次观察当 apply 前态

未写该项目。未扫描未点名 HOME。当时观察未写入第 3 节当前值，也不进本文件或主 PRD。

第 3 节未齐时不得访问目标项目任何路径，包括项目根 `AGENTS.md`。“先读 AGENTS.md”只约束授权盘点开始之后的顺序，不能用来在字段未齐时提前读该项目。项目规则正文不进本文件；授权盘点开始时再读。

## 4. 只读盘点规则（字段齐后才执行）

第 3 节任一字段 pending 时，不得执行本节，也不得访问目标项目任何路径，包括项目根 `AGENTS.md`。用户点名项目根不等于盘点授权。门禁外观察不得填入第 3 节当前值，不得计入第 6 节验收。

授权盘点开始时（第 3 节已齐），对每个目标项目先读项目根 `AGENTS.md`；若它声明更深层 `AGENTS.md` 优先，再只读那些已证明存在的更深路径。未读项目根 `AGENTS.md` 不得继续访问该项目其他路径。

对每个已授权项目根，分开记录，不混成“仓库很干净”：

1. Git tracked 内容、当前完整 SHA、工作区是否 dirty。
2. ignored / untracked：`.trellis`、task.json、jsonl、workspace journal、身份、报告、缓存。
3. 项目内平台产物所有权：`.codex`、`.omp` 等受管旧条目 vs 用户自定义。
4. 声明的 HOME／Skill 根里、与本批项目相关的 MCP／hooks／全局 Skill／包版本；未授权根不读。
5. 未完成 workspace 上下文：缺手批准 handoff 的项目在相关迁移前保持 blocked（PLAN-008 已修代码缺口，真实项目仍要有交接／恢复证据）。
6. 身份：只报告 `.trellis/.developer` 与 `.sbtd/developer` 是否存在及是否合法，不改写。

盘点输出分两层：

- **可追踪协议层**（本文件／主 PRD）：非敏感决定、项目逻辑名、声明分支、host 选择、保留政策、拟清理类别、私有记录是否已回读。禁止写入目标项目绝对路径、HEAD、工作区状态、目录结构或原件指纹。
- **私有层**（`backup_root` 或用户指定准备记录）：精确路径、大小、checksum、敏感结构、publication_decisions 候选。原件指纹不进共享仓库、公共报告或公开日志。

## 5. 明确不做

- 不 `migration apply` / `verify` / `cleanup`，不带迁移上下文的 `init`／`init-projects`。
- 不 sync live automation，不安装或卸载真实 Graft／Trellis／GitNexus，不改 hooks。
- 不创建 tag，不缩短保留窗，不删除备份。
- 不把干净 `git status`、现有 tag 或目录存在当成完整备份。
- 不把本项同意当成 P2-05 清理确认或 P3-04 销毁确认。
- 不把门禁外项目读取当成第 4 节盘点、第 3 节 Trellis 结构冻结或拟清理证据。
- 第 3 节未齐时不访问目标项目任何路径，包括 `AGENTS.md`。
- 授权盘点开始后，不在未读该项目根 `AGENTS.md` 的情况下继续访问其其他路径。读 `AGENTS.md` 本身仍不是完整第 4 节盘点。
- 不把目标项目绝对路径、HEAD、工作区状态或盘点结构写入本文件或主 PRD。

## 6. 验收

P2-01 标 done 前必须同时成立：

1. 第 3 节字段均有用户原文；custodian、`backup_root`、拟清理范围、保留安排和目标项目精确路径可在私有记录中回读。本文件只保留逻辑名。
2. 每个目标项目有只读盘点：tracked／untracked、身份、声明 HOME 范围内的共享消费者。该盘点必须发生在第 3 节齐之后；盘点第一步才读项目根 `AGENTS.md`。门禁外观察和第 3 节未齐时的任何项目读取都不算盘点。
3. 共享入口要么整批纳入，要么有明确隔离 HOME／Skill 根；未解依赖则全局卸载为 not-allowed。
4. 用户书面接受 §11.8 最低保留，或因更严要求停止迁移并另定保全方案。
5. 独立 review 无剩余 P0／P1；生产代码本项默认不改。

完成后仍不解锁真实 apply。P2-02 要另一次授权，才能在隔离副本和隔离 HOME 演练。
