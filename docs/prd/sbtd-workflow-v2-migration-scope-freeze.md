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

本仓库仍不创建 `.trellis/`、`ai/tasks/` 或 `.feature`。真实目标项目的新目录不自动变成本仓库目录。尚未接受任何用户冻结输入。

### 2.1 DDIA Data Design Review

```text
DDIA Data Design Review
Status: confirmed
Data owner and source of truth: 用户拥有真实项目树和 HOME。非敏感 custodian（用户原文，不得从 Git/OS/lessons 推断）拥有 backup_root、原件、候选、阶段/恢复收据和已登记副本。本冻结文件只拥有可追踪协议层：逻辑名、host 选择、保留政策、拟清理类别、私有记录是否回读成功。manifest 尚未存在；plan 之后才成为迁移绑定事实源。task.md 不因本项成为迁移 SoT。
Write / read / async / failure paths: P2-01 对项目/HOME 只读且仅读取用户点名的绝对路径。本源仓只写冻结协议与台账。私有准备记录只在用户给出删除范围外路径后写入；私有准备不等于 apply。任一项第 3 节字段缺失则保持 in-progress，不进 P2-02，不写项目/HOME。未点名路径不扫描。无队列/后台/跨服务异步。
Consistency model: 范围以用户原文为强一致输入。盘点是点名路径的当时观察，不承诺之后不变。共享 HOME/Skill 消费者要么整批纳入，要么明确隔离；未知消费者时全局卸载 not-allowed。原件指纹与敏感路径只留私有层。
Idempotency / ordering / retry / deduplication: 重复记录同一 pending 字段不是突变。同一项目点名两次不扩大扫描。拟清理清单不是 P2-05 清理确认，也不是 P3-04 销毁授权。cleanup/recovery/uninstall 永不删备份。
Schema / migration / backfill / rollback / replay: 本项不改迁移 schema、不 apply、不 backfill。它冻结后续 plan 必填 HITL 输入。实现变化后仍须重新 plan，不复用未绑定的旧盘点当 apply 前态。回滚本项只需撤回协议文档；因尚未写用户数据，无数据回放。若在 manifest 前放弃，终止分支仍须在删除范围外私有记录保存并回读 custodian/归属/精确范围/独立授权/确认时间。
Observability and repair: 协议层表格显示 pending/已填。私有层保存路径/大小/checksum 并回读。回读失败视为未冻结。无后台催办；在 P2/P3 检查点由责任人复核，间隔 ≤30 天。
Required tests: 用户点名后只读那些路径的 tracked/untracked/身份/声明 HOME 共享消费者。证明本文件不含原件指纹。独立 review 无剩余 P0/P1。不把后续 apply/恢复演练算作本项通过。
```

本审查确认的是冻结协议本身可以稳定：缺字段就 fail-closed。它不是真实 apply、部署、cleanup、sync、tag 或备份销毁授权。第 3 节字段仍全部 pending，在用户给出原文前不接受/冻结 P2 输入。

## 3. 本项必须冻结的字段

以下任一项缺失，P2-01 保持 in-progress，不进入 P2-02，不写项目／HOME。

| 字段 | 必须由用户提供 | 当前值 |
|---|---|---|
| 至少一个实际项目根 | 绝对路径；每个项目的当前分支或 `detached:<full-sha>` 或明确非 Git | pending |
| 每个项目的旧 Trellis 结构 | 用户说明或授权后只读该项目根；不猜版本 | pending |
| 验证 host | Codex、OMP 或两者 | pending |
| 有效 HOME / Skill 根 | 每个 host 的实际配置根；共用者须整批纳入或明确隔离 | pending |
| 共享批次闭包 | 同 HOME／Skill／全局入口的依赖项目名单，或隔离方案 | pending |
| 未选平台 | Claude／Kimi 等只盘点、不修改；依赖未解前禁止全局卸载 | pending |
| 非敏感 custodian | 责任人标识；不从 Git/OS/lessons 推断 | pending |
| 私有 `backup_root` | 仓库外专用目录；不得与受管目标互相包含 | pending |
| 最低保留与复核 | 默认：覆盖 P3 两周观察，并至少保留至正式发布后 14 天，取较晚者；首次及后续间隔 ≤30 天 | pending |
| 拟清理范围 | 项目旧目录／受管接线／全局旧工具分别列出；本批是否允许全局清理 | pending |
| 私有准备记录位置 | 删除范围外、可写、可回读的既有私有记录或迁移报告路径 | pending |

推荐澄清选项不能代替这些事实。用户写出绝对路径、标识和目录后，才允许只读那些路径。

## 4. 只读盘点规则（字段齐后才执行）

对每个已授权项目根，分开记录，不混成“仓库很干净”：

1. Git tracked 内容、当前完整 SHA、工作区是否 dirty。
2. ignored / untracked：`.trellis`、task.json、jsonl、workspace journal、身份、报告、缓存。
3. 项目内平台产物所有权：`.codex`、`.omp` 等受管旧条目 vs 用户自定义。
4. 声明的 HOME／Skill 根里、与本批项目相关的 MCP／hooks／全局 Skill／包版本；未授权根不读。
5. 未完成 workspace 上下文：缺手批准 handoff 的项目在相关迁移前保持 blocked（PLAN-008 已修代码缺口，真实项目仍要有交接／恢复证据）。
6. 身份：只报告 `.trellis/.developer` 与 `.sbtd/developer` 是否存在及是否合法，不改写。

盘点输出分两层：

- **可追踪协议层**（本文件／主 PRD）：非敏感决定、项目逻辑名、host 选择、保留政策、拟清理类别、私有记录是否已回读。
- **私有层**（`backup_root` 或用户指定准备记录）：精确路径、大小、checksum、敏感结构、publication_decisions 候选。原件指纹不进共享仓库、公共报告或公开日志。

## 5. 明确不做

- 不 `migration apply` / `verify` / `cleanup`，不带迁移上下文的 `init`／`init-projects`。
- 不 sync live automation，不安装或卸载真实 Graft／Trellis／GitNexus，不改 hooks。
- 不创建 tag，不缩短保留窗，不删除备份。
- 不把干净 `git status`、现有 tag 或目录存在当成完整备份。
- 不把本项同意当成 P2-05 清理确认或 P3-04 销毁确认。

## 6. 验收

P2-01 标 done 前必须同时成立：

1. 第 3 节字段均有用户原文，并可在私有记录中回读 custodian、`backup_root`、拟清理范围和保留安排。
2. 每个目标项目有只读盘点：tracked／untracked、身份、声明 HOME 范围内的共享消费者。
3. 共享入口要么整批纳入，要么有明确隔离 HOME／Skill 根；未解依赖则全局卸载为 not-allowed。
4. 用户书面接受 §11.8 最低保留，或因更严要求停止迁移并另定保全方案。
5. 独立 review 无剩余 P0／P1；生产代码本项默认不改。

完成后仍不解锁真实 apply。P2-02 要另一次授权，才能在隔离副本和隔离 HOME 演练。
