# P2-01：迁移范围、备份责任与保留安排冻结

## 1. 授权与边界

- 任务：P2-01；唯一状态事实源为[主 PRD §14](sbtd-workflow-v2-trellis-removal-graft-migration-prd.md#14-优先级实施台账)。
- 开发起点：`main` `03541a97f3804f8966cd5c4ff3f579793f9d4175`；任务分支 `p2-01-migration-scope-freeze`。
- 用户授权：开始 P2 与 P2-01 冻结。没有 apply、独立部署、cleanup、本机 workflow sync、hooks opt-in、全局卸载、rc/tag、正式发布或备份销毁授权。
- 本项交付：把本批 **release scope**、host/HOME 批次、非敏感 custodian、私有 `backup_root`、保留/复核安排和**拟**清理范围写成可回读记录。盘点只读；私有准备不等于批准 apply。
- 本配置源仓库不是默认迁移目标。未点名的用户项目、`~/.codex`、`~/.omp` 或其他 HOME **不得扫描**。Git author、OS 用户、lessons 分隔名 `640` 都不能当成 custodian。

## 2. Book Gate Plan

| Gate | 判定／触发事实 | 状态 |
|---|---|---|
| DDIA | on-demand；备份所有权、私有准备、保留门与销毁分离 | confirmed（沿用主 PRD §11.1／11.8／AC-37，不是授权真实迁移） |
| Legacy safety | on-demand；只定义只读盘点与拟清理，不改 live | characterized |
| DDD | 无新领域术语 | not-required |
| Refactoring | 不改生产实现 | not-required |
| Release readiness | 本项不是 rc 或 v2.0.0 | not-required |
| grill-with-docs | 沿用已批准迁移边界 | 未完整调用 |

本仓库仍不创建 `.trellis/`、`ai/tasks/` 或 `.feature`。真实目标项目的新目录不自动变成本仓库目录。

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
