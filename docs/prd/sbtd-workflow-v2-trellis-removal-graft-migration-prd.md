# SBTD Workflow v2：去 Trellis 化与 Graft 替换实施 PRD

## 1. 文档状态与执行边界

| 项目 | 内容 |
|---|---|
| 文档版本 | 2.7（进入逐任务实施；基线与模式契约，当前进度以 §14 为准） |
| 文档状态 | 产品与流程决策已确认；已获本源仓库逐任务开发及 PR 合并授权；实际任务状态与证据见 §14，合并不等于 v2 发布 |
| 创建日期 | 2026-09-16 |
| 推荐目标 tag | **v2.0.0**；候选发布可使用 `v2.0.0-rc.1`，本轮不创建 tag |
| 代码基线 | `KunoLu/640-skills`，`v1.0.15`，完整 commit `bc8eec1549928fb0966254751b96b611b6334183` |
| 初次审核 HEAD | `3139be4f6b7476f84b2affbd3667bed003119f94`，`main`；在该初次审核快照，相对基线仅 `CHANGELOG.md` 一行日期变更，实施代码相同 |
| 初次审核工作树 | 初次审核时 clean；本文件在本会话创建并持续修订，不将初次状态冒充最终实现状态 |
| 最近核对代码快照 | `main`，`5ad87208167d6cf1ef97444cb84d7cb5fde5f065`；2026-09-17 核对，修订本版前工作区 clean。相对代码基线仅 CHANGELOG、ENTRYPOINT、归档和本 PRD 变化；安装器、模板、catalog 与生产测试未变。此 SHA 是固定核对快照，不表示后续提交的实时 HEAD |
| 原始输入 | 用户提供《SBTD去Trellis化与Graft替换改造方案.md》，方案版本 v2.0，2026-09-16 |
| 输入 SHA-256 | `eeefc2d47eb53c0df1094adcd02f983a0b5dbcd74f6af8c5d34038b7a7ba2fcf` |
| Graft 审核候选 | npm `@nanonets/graft@0.18.0`，registry `gitHead=de8456e892bad5aeee11403e47fb2227773eb27e`；已在 darwin/arm64 Node v24.15.0 隔离 HOME 实测，见第 9.8 节 |
| 当前交付范围 | 按 §14 依赖顺序实施本源仓库计划；每项独立分支、验证、循环 review、处理 advisor、PR 合并和合并后台账更新。初期 PRD 与 P0-01 证据仍保留 |
| 独立授权边界 | 真实 HOME／host 接线及工具安装卸载、真实项目迁移、本机 workflow sync、live automation、hooks opt-in、清理、tag／发布及备份销毁仍需具体范围和相应确认；本源仓库开发与隔离验证不等于这些授权 |
| 实施跟踪事实源 | 本文第 14 节任务台账；每完成一项立即同步状态、实际完成时间和证据 |

**结论：接受总体方向，不能原样照搬输入方案。** 去 Trellis、引入 `sbtd-task`、使用 Graft 结构图是可实施方向；“完整对等”“永不 stale”“零联网”“Git tag 可完整回滚”“CI 已经兜底”均不能作为已证实前提。本文已将这些表述改为明确边界、缺口和发布门禁。

最终采用 `default / lite / strict` 三种任务执行模式：所有新需求先路由和评估；若其他模式更合适，必须在实际执行前暂停并解释、询问，用户坚持原模式则遵从。default 按需使用 SBTD，lite 使用精简清单，strict 严格执行完整的适用流程；不再把所有任务默认纳入强流程。

不翻译 OMP hooks、不启用 Graft `--deep`、不设 GitNexus/Graft 双工具并行运行期的决定保持。Graft 自动提示 hooks 默认不安装，用户明确选择且能力验证通过后才启用；strict 也不自动代表授权安装 hooks。handoff 保留主动交接，但以暂停、切会话、真实上下文压力或明确续接需要触发，取消与 caveman 3／5 次计数绑定。

已确认允许安装下载及 npm 版本元数据查询；关闭遥测，禁止代码、查询、项目数据上传，禁止 LLM/cloud 路径。完全离线时优先本地已安装能力，Graft 不可用则用源码／LSP 等方法继续安全工作，不把联网或工具安装成功当成普通任务启动条件。

default 的最小任务记录默认在本地忽略的 `.sbtd/tasks/`；lite／strict 或明确需要共享、长期追踪的任务进入可追踪的 `ai/tasks/`。模式与用户选择及时持久化，handoff 只是快照。lessons 身份由 `.sbtd/developer` 按需建立；老项目身份和 ignore 的迁移只在显式授权后执行，清理旧目录／规则前再次确认。

本版记录用户在本会话最后要求“汇总所有讨论并最终落地”的确认；此前“待说明”“待确认”的模式和目录讨论已在正文收敛。早先的双路径表述被三模式替代，default 默认 tracked task、约 10k 常驻／6k 入口、低阈值 handoff、根 ignore 五行目标均不再作为有效目标。第 21 节逐项映射最终决定、实现任务和验收。

本仓库是配置摘录与模板源，不是真实业务项目。本轮不执行 `trellis init`，不创建 `.trellis/`、`ai/tasks/` 或 `.feature`。真实目标项目将采用的新目录不自动变成本仓库目录。本文路径遵循用户指定的 `docs/prd/`，不迁入未来的任务目录。

## 2. 版本建议：为什么是 v2.0.0

本产品的公开契约不仅是 Python 函数，还包括安装 CLI、JSON 输出、Skill 名称、任务目录、状态语义、生成配置和用户遵循的工作流。

| 变化 | 兼容性影响 |
|---|---|
| 删除 `trellis-workflow`、`trellis-channel`，改用 `sbtd-task` | 用户原有调用入口失效，不保留运行时 alias |
| `.trellis/tasks`／spec／lessons／identity 改路径 | 旧项目需要显式数据迁移，不能透明升级 |
| 删除 `--trellis-*` 参数和 `trellisInit`／`trellisProjectSetup` JSON 字段 | 脚本调用者必须同步修改 |
| GitNexus CLI／MCP／索引契约改为 Graft | 工具 API 和能力集合不兼容，部分功能明确退出 |
| Trellis hooks／状态机／Channel 改为规则、检查清单、原生复核 | 强制方式、恢复方式和协作能力改变 |
| 安装、reset、project-only 和迁移边界变化 | 需独立验证用户文件保护及配置所有权 |

依照 [SemVer](https://semver.org/lang/zh-CN/)，上述任意一项不兼容公开契约变更已足以采用 major。**推荐从 v1.0.15 直接进入 v2.0.0；不推荐 v1.1.0。** 只有保留全部旧契约、将新流程作为可选增量时才适合 minor，但那与本次干净切换目标冲突。

版本区分：本文版本 `2.7`、产品 tag `v2.0.0`、Graft 候选 `0.18.0`、未来 task frontmatter 的 `schema_version: 1` 是不同命名空间，不能互相替代。

正常发布顺序：P0 契约／验证 → P1 实现及候选验证 → 可选 rc → P2 授权切换 → P3 观察／发布验收 → v2.0.0；备份处置 P3-04 在发布回滚窗口结束后，或按第 11.8 节明确终止分支独立授权执行，不反向阻塞发布。rc 不是双工作流并行期；既有 v1.0.15 tag 和已发布 CHANGELOG 不覆写。

## 3. 已核验的仓库事实

### 3.1 基线规模与真实耦合

以下为本轮读取和脚本计算结果，**不是 token 实测值**：

| 文件／项目 | 已核验结果 | 设计影响 |
|---|---|---|
| `templates/agents/AGENTS.global.md` | 569 行、79,085 UTF-8 bytes、45,103 字符 | 不能以“行数”推算模型 token 或每任务费用 |
| `templates/agents/AGENTS.project.md` | 175 行、16,856 bytes | project-only fallback 必须保留 |
| `templates/skills/trellis-workflow/SKILL.md` | 479 行、49,138 bytes | 有阶段／BDD／Book／Testing 门禁，不只是 Trellis 命令说明 |
| `scripts/onboard.py` | 7,197 行 | 替换涉及执行路径、报告结构和失败语义，不能只改 CLI_TOOLS |
| `install.sh`／`install.ps1` | 1,339／1,045 行 | 必须保持两种安装入口一致 |
| `catalog.json` | 15 bundled、19 external、2 agent-template、1 project-template | 删除两个 bundled、新增一个后预期 14 bundled；19 external 不变 |
| `.github/**` | 本轮未发现 CI 配置 | “CI 兜底”是新增交付，不能当作现状 |
| Graft | 当前实现尚无集成 | 需要新增能力验证、CLI／MCP 适配和安全安装 |

上表中 `templates/`、`scripts/` 均位于 `sbtd-workflow-onboard/` 下，不是根目录旧路径。

### 3.2 关键代码与规则证据

| 证据位置（相对仓库根） | 当前事实 | 必须处理 |
|---|---|---|
| `sbtd-workflow-onboard/scripts/onboard.py:319-414` | Trellis/GitNexus 全局 CLI；22 个 Trellis platform flags | 删除 Trellis 独立平台维度；新增 Graft 能力检测 |
| 同文件 `1047-1122` | GitNexus MCP 配置由 detected executable 生成 | 复用结构化配置模式，不退回无版本 `npx -y` 作为默认 |
| 同文件 `2563-2581`、`2660-2697` | Git ignore 双向探针和错误定位 | 同步更新到新数据目录，保留实际 Git 语义校验 |
| 同文件 `5615-5958` | Trellis 平台解析、逐项目 init、bootstrap 和聚合状态 | 用 SBTD 脚手架与 bootstrap 检查替代 |
| 同文件 `6341-6342`、`6805-6839` | `trellisInit`、`trellisProjectSetup`；退出码 2／5／6 | 一次性迁移两端消费者，保持 JSON 单根文档和非零失败语义 |
| 同文件 `6508-6535` | 写操作需要 `--yes`；check 与 check-projects 只读入口 | 不把 Graft 自维护副作用带入 check |
| `install.sh:943-952,1182-1224` | 全局工具安装与 GitNexus MCP 菜单 | Bash 与 PowerShell 同步调整、配置只写被选平台 |
| `sbtd-workflow-onboard/catalog.json:30-40` | 两个待移除 bundled entries | catalog、目录、计数、安装、文档一并切换 |
| `templates/project/.gitignore:49-81` | `.trellis/*` 及有限任务文档 re-inclusion | `task.json`／jsonl 等不能假设已被 Git 保存 |
| `templates/skills/lessons-record/SKILL.md:34-118` | 分隔名、worktree fallback、marker、ID、可选 union | 保留身份和写入不变量，不重命名历史 ID |
| `ENTRYPOINT.md:13-51` | 版本监控与公开安装边界 | Graft 新监控行、同步表与 fresh-clone 入口需版本化 |
| `docs/lessons/topics/repository-workflow.md:319-329,343-353,391-439` | 幂等写入、active Codex HOME、所有权和只读 probe 陷阱 | 纳入 Graft 安装与迁移验收 |

### 3.3 既有测试资产

主要受影响：`tests/test_onboard_multi_projects.py`、`test_workflow_contracts.py`、`test_install_sh_agent_cli_flow.py`、`test_onboard_ponytail_integration.py`、`test_onboard_caveman_maintenance.py`。

必须保持的回归：`test_onboard_external_skills.py`、`test_onboard_i_have_adhd.py`、`test_onboard_agent_cli.py`、`test_validation_evidence_v2.py`、`test_knowledge_base_p1.py`。

现有 `init/reset` 对 bundled 与 external Skills 的维护策略并不相同；不得把本次替换变成对全部全局 Skill 的无差别重装／删除。现有 `codex / claude / kimi / oh-my-pi` 通用 Agent 适配是独立维度：本次只对 Codex／OMP 承诺新 SBTD 主流程实测，不顺手删除 Claude／Kimi 的独立 CLI/MCP 适配，也不自动给它们安装 Graft。

## 4. 原方案逐项评估与修正

| ID | 输入方案主张 | 评估 | 本 PRD 决定 |
|---|---|---|---|
| A01 | 去掉 Trellis，收回 AGENTS + Skills | 接受并按模式分层 | 无 Trellis runtime；default 按需、lite 精简清单、strict 保留完整适用阶段，不引入替代调度框架 |
| A02 | task.md 与 index 即可 100% 替代 task.py | 不成立 | 本地／共享唯一 task.md 为事实源，指针与索引仅导航；最小校验不变成 default/lite 的启动门禁 |
| A03 | 唯一 in-progress 就是 active task | 有空档 | checking 可恢复；区分父汇总与实际执行对象，结合本地引用、分支与用户指令选择 |
| A04 | GitNexus detect_changes 等于 graft check | 不成立 | check 只报告 freshness；diff 和 blast 分别负责真实变化与结构影响 |
| A05 | 每次查询 refresh，stale 机制上不存在 | 不成立 | pinned 源码在锁等待失败／异常时会返回旧图；禁用开关和 stat 快路径也存在 |
| A06 | Graft 结构层无需 key，因此零网络依赖 | 需限定 | 结构分析无 LLM；安装、版本查询仍联网，遥测单独关闭；按用户补充决策执行 |
| A07 | `graft version` 作为只读版本探针 | 不接受作为默认 | 默认使用 `graft --version`，还需证明无副作用；`version` 含最新 npm 查询 |
| A08 | `--agents agents --yes` 仍可能固定接线 Claude | 与 pinned 实现不符 | explicit agents 优先，所选 host 不是 Claude；同时防止其 OpenCode 等附带目标写入 |
| A09 | OMP 可直接继承 Codex MCP | 不作前提 | 从 active host 配置解析并握手；必要时显式 OMP stdio 配置，不翻译 hooks |
| A10 | 无 hooks 功能完全不降级 | 需限定 | 主动查询可刷新结构图，但被动 markdown projections 不随每次 query 全量刷新 |
| A11 | 六个 Graft MCP 工具与 GitNexus MCP 对等 | 不成立 | 仅覆盖核心结构查询；无直接 blast MCP、route_map、taint、PDG、rename 等对等承诺 |
| A12 | 共同父目录自动 build | 有越权扫描风险 | 逐项目默认。禁止对父目录 `graft init`／`build`／MCP。多仓=对每个已授权仓根独立调用后只读汇总，不因共父目录扫描或接线兄弟项目 |
| A13 | `--deep` 不启用 | 接受并补齐 | 同时禁止 `blast --name`、brain connect 等其他 LLM/cloud 路径 |
| A14 | 三张检查清单、原生独立复核 | strict 保留，其他模式按需 | 不声称保留 Channel 持久协作语义；共同安全边界不因模式变轻而消失 |
| A15 | handoff 沿用 caveman 3／5 阈值 | 最终取消计数绑定 | 主动交接改为暂停／切会话／真实上下文压力等事件，仅有实际信息变化才更新 |
| A16 | 无 SessionStart hook 却自动恢复 | 软规则而非硬保证 | 公共轻量入口先读取有效任务模式；明确“继续该任务”不重复确认；未知／冲突时才询问 |
| A17 | lessons 协议一字不改 | 保留原件与身份语义，区分共享投影 | 原始 ID/marker/正文私有无损保全，普通写入不改他人历史；共享迁移结果先过隐私门，不为“原样”公开敏感内容 |
| A18 | tag + reset --hard 完整回滚 | 不安全 | tag 不含 ignored/untracked 或 HOME；使用完整备份清单与 scoped restore，保留新写入 |
| A19 | Trellis runtime/jsonl 可以直接丢弃 | 不安全 | 先盘点并保存；未知文件／字段／自定义配置不能按目录名推断为可删除生成物 |
| A20 | 父子任务目录天然兼容 | 未获证实 | 导入器读取实际 task metadata 和关系；不假定所有 Trellis 版本采用嵌套结构 |
| A21 | 缺 created 就从 git 推断；done 自动归档 | 有伪造历史风险 | 记录推断来源；无法证明则 null，完成日期未知不按当前日期归档 |
| A22 | 全局 sed 替换引用，抽查 5 条 links | 不足 | 按文件职责改写，保留历史证据；完整检查所有迁移路径和链接目标 |
| A23 | 删除两个 Skill 后移入 archive | discovery 风险 | 历史由 Git tag 保存；不在可递归发现目录留可安装旧 SKILL.md 副本 |
| A24 | 所有 templates/scripts 不含旧词即合格 | 误报／漏报 | 当前有效契约零旧依赖；历史、原样镜像、迁移器的旧输入是明确允许清单 |
| A25 | 现有 CI 可兜底 | 无仓库证据 | 新增可执行 CI gate；模型是否真的遵循清单仍需真实 host 行为验证 |
| A26 | 固定开销降低 60%+ | 未提供可复算 token 证据 | 当作目标假设；按模型、tokenizer、缓存、任务类型分别实测 |
| A27 | P0 模板完成时 scripts 也无旧引用 | 阶段验收自相矛盾 | P0 验收契约／模板；P1 完成时才验全链路零旧运行依赖 |
| A28 | P3 不允许回退架构 | 不接受安全绝对化 | 保持不设双运行期；数据损失／重大缺陷仍允许授权恢复到备份版本 |

## 5. 产品目标、非目标与成功条件

### 5.1 目标

1. 主流程成为 `Codex / OMP + sbtd-task + Graft + Chrome DevTools MCP + Playwright + Maestro`。
2. 删除 Trellis CLI、生成角色、每轮 breadcrumb、jsonl 策展和 Channel runtime 的运行依赖。
3. 三种模式均围绕 SBTD 展开，按明确的默认动作、适用检查和产物厚度执行；任务可以续接，不以缺辅助工具或形式文档阻断 default/lite 的普通安全工作。
4. 保留 SDD／BDD／TDD／DDD、五类 Book Review、Ponytail／可读性和验证能力；strict 保留完整适用门禁，default/lite 按风险使用，不默认全量加载或输出全部表格。
5. 新项目安全初始化，旧项目可显式迁移；项目及 HOME 数据均有明确所有权、备份与失败处理。
6. 默认 Graft 结构分析不付 LLM 费用；降级可见，绝不以空图或成功退出码证明无影响。
7. 后续实施以本文任务表记录每一项真实完成时间与证据。

### 5.2 非目标

- 不引入 OpenSpec、另一套 task daemon、数据库、调度服务或自定义通用 Agent runtime。
- 不实现 Graft 没有的 PDG／taint／API route graph；不维护 Graft fork。
- 不实现 OMP 原生 post-edit extension；将来需要另行评估，不计入本次完成条件。
- 不自动替真实项目新建 CI、迁移业务 BDD 内容、修改 API contract 或升级业务依赖。
- 不修改 `assets/external-skills/stable/**` 的原样 Skill 内容、MANIFEST pin 或 license；若上游内容出现旧词，由 SBTD 外层规则定向覆盖。
- 不把 `sync`、`update`、安装、数据迁移、发布混成一个动作。
- 不将当前仓库所有历史 PRD／lessons／CHANGELOG 中的 Trellis/GitNexus 字样清空。

### 5.3 完成分层

- **PRD 完成**：本轮文档内容和任务表校验完成，不代表 v2 已实现。
- **实现完成**：P0/P1 必需任务及候选验收完成，不代表真实项目已迁移。
- **逐项目迁移完成**：每个获授权项目的数据、接线、恢复与 smoke 全部通过。
- **v2.0.0 发布就绪**：release scope 内 P0/P1、P2 和 P3-01～P3-03 的发布门禁满足，无未接受高风险；P3-04 跟踪正常发布或明确终止后的独立备份处置，不作为创建 tag 的前置，未满足所选分支门禁不能标 done。

## 6. 领域边界和数据所有权

### 6.1 DDD Boundary Review

| 字段 | 最终审核结果 |
|---|---|
| Status | `confirmed`，产品边界已收敛 |
| Ubiquitous language | 执行模式＝怎么组织工作；存储位置＝本地或共享；任务状态＝工作进展；handoff＝交接摘要；spec＝长期规则；developer＝lessons 分隔名 |
| Bounded contexts | 配置源、任务执行、本地恢复、项目规范／经验、用户级接线、代码图和测试证据分别管理 |
| Invariants and business rules | 用户模式选择优先；模式不缩减明确交付；一个任务一个有效模式记录；共享任务不等于 strict；指针／handoff 不成为第二模式事实源 |
| Core / supporting / generic subdomains | 任务执行为核心；模式恢复、身份和迁移为支撑；代码图与测试工具为通用辅助 |
| Corrections to the grill-with-docs result | 未完整执行 grill；通过本会话澄清修正双路径含混、default 默认 tracked 任务、低阈值交接和全局强制门禁 |
| Open conflicts and questions | 无未决产品边界；Graft 适配、真实 host 与迁移能力仍须实施验证 |

### 6.2 DDIA Data Design Review

| 字段 | 最终审核结果 |
|---|---|
| Status | `confirmed`，仅表示设计要求明确，非实现或恢复演练通过 |
| Data owner and source of truth | `.sbtd/tasks/` 或 `ai/tasks/` 中唯一有效 task.md 拥有模式与状态；本地 active-task 仅存引用；handoff 为快照；用户拥有 HOME |
| Write / read / async / failure paths | 选择／切换模式后及时保存；跨会话先读取模式；共享提升先写候选并校验、再切换引用、最后退役原件；失败保留可恢复原件 |
| Consistency model | 单任务模式不双写；index 可重建；损坏记录禁止覆盖，default/lite 可继续与损坏记录无关的安全工作，strict 不虚报门禁通过 |
| Idempotency / ordering / retry / deduplication | 同一任务原地更新，不按会话重复建任务；同内容重复提升 no-op；并发写前核对预期内容；模式切回 default 不自动删除共享历史 |
| Schema / migration / backfill / rollback / replay | 任务 ID 不随存储位置改变；旧任务缺模式保留未知并询问，不默认降成 default；身份仅合法原名迁移；本地文件不自动跨机器同步 |
| Observability and repair | 模式来源／选择理由、有效任务引用、更新时间、迁移 manifest 和私有备份；缺失或失效引用先核对，不按最近 mtime 猜测 |
| Required tests | 路由拒绝、模式恢复、陈旧 handoff、双副本／提升中断、身份分支、非法路径、只读目录、ignore、重复迁移、恢复冲突 |

### 6.3 本次 PRD 与未来执行门禁的区别

本轮文档归并已完成 DDD／DDIA 设计审核；未修改生产代码，因此本轮 Legacy／Refactoring／Release Readiness 为 on-demand、not-required。未来实现本产品的状态管理、安装和迁移时，仍按该开发任务的客观风险执行安全审核和验证。产品提供 default/lite 的可降级体验，不等于安装器可以忽略越权写入、迁移程序可以缺备份，或 v2 发布可以跳过本文约定的验收。

## 7. 三种模式、任务记录与项目目录

### 7.1 模式定义与实际步骤

| 模式 | 大白话 | 默认步骤 | 文档与检查厚度 |
|---|---|---|---|
| `default` | 按需使用 SBTD，直接把事情做好 | 理解需求 → 查相关事实 → 实施 → 针对性验证 → 交付 | 不强制先列完整清单、写 PRD 三件套或输出全部 Gate；实际项目任务只保留本地最小记录 |
| `lite` | 按简短清单做 | 简要目标／边界 → 短任务清单 → 逐项实施与检查 → 汇总验证 → 更新必要记录 | 有固定轻骨架和共享短任务卡；不强制独立 PRD/design/implement，不机械运行所有专项审核 |
| `strict` | 按完整强制流程做 | 需求及适用审核 → PRD／设计／拆分 → before-dev → 实施 → check／独立复核 → 记录与 finish-work | 规定节点均须检查，命中的强制项必须完成；不适用项明确说明，不生成虚假产物 |

三者都使用 SBTD 的需求、设计、验证与交接方法，区别是组织方式和强制程度，不是功能范围或质量承诺。用户即使选择 default，明确要求 PRD、任务表、完成时间或报告，也必须完整交付。用户要求“先出方案、不要实现”时，任何模式都不能越过该边界。

default/lite 缺 Graft、某个 Skill、任务索引或非必要文档时，应采用可用方法继续，不强迫先安装或修复框架。缺测试环境限制的是验证结论：可以交付已完成代码并明确未验证内容，不能伪称通过。未授权删除、密钥泄露风险、没有可靠备份的破坏性迁移等仍暂停对应危险动作，不无差别冻结整个任务。项目原有 CI／合规和用户明确验收不会被模式选择静默取消。

例如未来“补充 Onboard 离线处理”：default 查逻辑、实现、验证并交付；lite 先列“版本不可达、本地工具缺失、离线验证”短清单再逐项做；strict 另外履行完整适用的需求、设计、审核和证据流程。三者必须实现用户要求的同样行为。

### 7.2 所有任务共用的初始模式路由

```text
收到新需求或续作指令
→ 确定任务身份与当前模式
→ 只读核对必要事实，评估模式适配
→ 若其他模式更合适：暂停实际执行，说明理由并询问
→ 用户决定最终模式
→ 保存已确定模式；判断是否需 grill 澄清
→ 按最终模式执行
```

1. 路由适用于任何新需求，包括文档／问答；不意味着纯咨询也要在仓库创建任务。先识别用户是否限定只读／不改文件，这一范围约束高于模式持久化。初始评估只能做必要的只读调查，不能在等待模式决定时先编辑、安装或执行迁移。
2. 模式来源顺序：当前明确用户选择 → 同一任务已确认／持久化模式 → 新任务未指定时 `default`。同一目标的“继续”、修订、恢复不重置成 default；新目标重新路由，不擅自继承上一个任务的 strict。
3. 无论当前 default、lite 还是 strict，只要基于具体范围／风险判断另一模式更适合，必须暂停并向用户说明当前模式、推荐模式、具体原因以及保留原模式的选项。也允许建议从 strict 降到 default/lite，不只升级。
4. 用户坚持原模式就按其选择执行；不得自动切换、通过反复询问逼迫升级，或缩减交付。保存已说明风险和拒绝建议；只有需求明显扩大或出现新的实质风险才重新建议，不在每个工具调用、阶段或新会话机械重问。
5. 推荐确认是用户明确要求的共同入口暂停点，不能被 default/lite 的“流程不阻断”原则取消。权限／数据安全确认同样独立存在；辅助工具缺失不构成擅自更改模式的理由。
6. 不同模式不是新的 CLI 调度框架。公共 AGENTS 仅持有短路由和模式恢复规则，具体清单按模式加载。严禁为了完成路由先加载 strict 全部规范、所有 reviewer 或整份历史任务库。
7. 用户可以在任务中途明确切换。先说明新增／减少的流程义务并保存决定；切到 strict 必须补足接下来要求的有效证据，不能把此前未执行步骤自动标为通过；切回 default 不删除既有共享产物。

### 7.3 本地／共享任务与唯一事实源

| 情况 | 位置 | 默认追踪策略 |
|---|---|---|
| default 普通项目任务 | `.sbtd/tasks/<task-id>/task.md` | 本地忽略；保存最小模式和续接记录 |
| lite | `ai/tasks/<task-id>/task.md` | 可追踪；短清单就是主要任务产物 |
| strict | `ai/tasks/<task-id>/` | 可追踪；task.md 及适用的完整任务产物 |
| default 明确需要共享、跨机器或长期追踪 | 提升到 `ai/tasks/<task-id>/task.md` | 保持 default 模式，不因共享自动转 strict |
| 纯问答／概念解释 | 对话内路由 | 不为每轮咨询创建仓库文件 |
| 显式只读／不改文件的审查、调查、问答等 | 模式和临时清单仅在会话内 | 三模式都不创建或更新任何任务、书签、handoff、身份、ignore；持久化须另行授权 |

“可追踪”不表示自动 git add、commit、push。只安装全局工作流、不曾 onboard 当前项目，仍可在已确认的目标根开展工作；建立最小任务记录不等于授权执行完整项目初始化或全局接线。default 本地记录不要求先有 developer，developer 仅服务 lessons 写入。

**只读优先：** 用户明确要求 read-only/no changes 时，不为满足模式或流程而请求先初始化或添加 ignore，也不写已有 task 的状态／事件。可以读取已授权的现有记录，模式选择和审查结果只在会话中表达；明确未落盘，因此不保证下次会话自动恢复。strict 的持久化要求在该只读审查范围内不适用，不能把只读审查的完成冒充完整开发流程通过。默认会写图缓存、HOME 或自动更新接线的 Graft 命令也不得作为“只读查询”运行；仅用已验证无副作用的路径，否则改用直接源码读取。后续用户另行授权修订时，重新确定写入范围，不沿用只读任务为隐式写授权。

**首次本地写入的保护检查：** 未 onboard／未迁移项目可能尚未忽略 `.sbtd` 或 `docs/handoffs`。写入任何本地任务、身份、书签或交接前，先检查实际 Git ignore 及是否已被 tracked。尚未保护时说明风险并请求仅添加所需 `/.sbtd`／`/docs/handoffs` 规则的窄授权，保留所有旧规则，不执行完整初始化或迁移；可以与用户名询问一并说明，但提供名字不自动等于授权改 ignore。未获授权则暂不写本地文件，沿用“记录／身份未保存”的处理；default/lite 的安全工作仍可继续，不能谎称本地记录已受保护。非 Git 项目只说明本地保存，不伪称存在 Git 忽略保障。

`.sbtd/active-task.json` 是当前工作目录的书签，仅包含 schema、task ID 和相对路径，不复制 mode、status 或恢复正文：

```json
{
  "schema_version": 1,
  "task_id": "onboard-offline-support",
  "task_path": ".sbtd/tasks/onboard-offline-support/task.md"
}
```

引用仅能指向本项目 `.sbtd/tasks/` 或 `ai/tasks/` 内的合法任务，拒绝绝对路径、`..`、symlink 逃逸和任意外部文件。`ai/tasks/index.md` 只索引共享任务；展示状态可由 task 派生，不存第二份权威模式。本地任务不为导航再生成一套共享索引。

共享提升使用同一任务格式和 ID：写目标候选 → 完整校验 → 更新有效引用及共享索引 → 确认后退役原本地记录。失败保留原件与恢复信息；不同时更新两份模式，不靠较新 mtime 选赢家。存在提升中断或双副本时先按有效引用和内容对账恢复，不能覆盖新用户修改。共享任务切回 default 后继续保留共享历史，不自动降回本地或删除文档。

同一目录内保存成功可支持跨会话；新电脑、新 clone 或新 worktree 不自动拥有未提交任务和 ignored 文件。需要跨环境续接时提前提升并由用户传递／提交任务记录；不把写入磁盘说成已同步。若目录不可写，default/lite 说明记录未保存并继续可安全完成部分，不声称能可靠恢复；strict 对必需任务产物仍保留未完成状态。

### 7.4 task.md 数据契约

下面是示例，不是已经实现的接口；本地与共享记录采用同一小型格式：

```yaml
---
schema_version: 1
id: onboard-offline-support
workflow_mode: lite
mode_source: user
mode_note: 用户选择短清单方式，已说明的模式建议不重复询问
status: in-progress
parent: null
branch: feature/offline-support
created_at: "2026-09-16T10:00:00+08:00"
updated_at: "2026-09-16T10:00:00+08:00"
completed_at: null
---
```

| 字段／内容 | 约束 |
|---|---|
| `schema_version` | 整数 1；未知版本不自动解释或覆盖 |
| `id` | 存储根无关的稳定逻辑 ID，可为 `parent/child`；移动到共享或归档后不改 ID，不能只凭同名 basename 找任务 |
| `workflow_mode` | `default / lite / strict`；可写的新实际任务必须记录，显式只读任务只在会话中保留；旧迁移记录可暂为 null，恢复前询问 |
| `mode_source` | `default` 表示新任务未指定后的默认选择；`user` 表示明确指定或确认；`migration-unknown` 仅用于无法证明旧模式的迁移数据 |
| `mode_note` | 简短保存选择理由、已拒绝的建议和已说明风险；有变化才更新，不复制全部对话 |
| `status` | `planned / in-progress / checking / done / blocked`；状态字段不是强制加载 strict 的开关 |
| `parent` | 父逻辑 ID 或 null，关系无环且可解析；最小独立 default 记录可省略无用扩展字段 |
| `branch` | 原始分支；detached 使用 `detached:<full-sha>`；非 Git 为 null，作用域限制在当前目录 |
| 时间字段 | 新任务使用带时区 ISO 8601；完成时记录实际 completed_at；重开前先保留第 7.5 节的完成事件，再清空当前值；历史未知时间为 null 并写来源 |
| 可选扩展 | blocked 时 `blocked_reason` 非空，解除后清空；自动恢复前态从状态事件获取，未知时由用户选择，不再建立 blocked_from 副本；E2E 按实际范围扩展 |
| 正文 | default 最小目标／进度／下一步；lite 加短清单；strict 按适用产物扩展；完成、阻塞／解除、重开事件采用第 7.5 节固定表 |

在允许写入的任务中，模式初定或切换后尽早保存，不能等到 handoff 时才第一次记录。澄清前允许仅保存任务身份与已确认模式的最小恢复记录，但不能虚构 PRD、设计、验收或拆分已完成。显式只读按第 7.3 节不落盘，新模式未获用户确认时不能提前改写。不引入可执行 frontmatter，不写真实凭据／敏感个人信息。

### 7.5 状态、父子任务与校验范围

| 转换 | default/lite | strict |
|---|---|---|
| planned → in-progress | 需求足以安全执行、共同路由确认已完成；不要求先补齐整套流程文件 | before-dev 及全部适用前置门禁通过 |
| in-progress → checking | 正在对已实施范围做针对性检查 | 改动、smoke 和完整检查材料就绪 |
| checking → in-progress | 记录待修项继续处理 | 保留失败证据，返回实施阶段 |
| checking → done | 满足明确交付并如实记录验证局限；不把缺非必要 Skill 当成完成障碍 | check／finish-work 全部必需项通过 |
| 未完成 → blocked | 同一文件更新中记录真实前态的入阻塞事件和原因；不冻结无关安全工作 | 记录从哪个阶段阻塞，保留尚未通过的 Gate |
| blocked → 恢复 | 原因解除后恢复最近有效入阻塞事件的前态；旧前态未知时由用户明确选择 | 恢复原阶段继续必要检查，不把解除阻塞当成 Gate 已通过，不直接跳到 done |
| done → planned | 明确重开；先在同一 task.md 保留旧完成及本次重开事件，再清空 completed_at | 同左，不自动承认旧证据适用于新范围 |

任务记录、模式恢复不要求每次咨询更新全部状态；实际项目任务应在关键变化、暂停和完成时更新，不每次工具调用写流水账。用户明确要求逐项完成时间时，所有模式都立即同步相应台账。

#### 完成、阻塞、重开和归档事件的持久载体

不新增 sidecar 或日志服务：在允许写入的 `task.md` 正文中使用唯一的 `## 状态事件` 表。实际出现完成、进入／解除 blocked、重开、归档或明确重绑定时建立并追加，不为普通工具调用写流水账：

```markdown
| at | from | to | reason | evidence |
|---|---|---|---|---|
```

- `at`：事件实际发生的带时区 ISO 8601 时间；迁移补录且无法证明历史时间时使用 `unknown`，在 reason 写明来源，不能使用迁移当前时间假扮旧完成时间。
- `from`／`to`：转换前后状态枚举；仅补录既有完成记录且前态不可证明时允许 `from=unknown`、`to=done`。归档或分支重绑定不改变状态时两列相同，reason 明确动作和原／新相对路径或分支。
- `reason`：完成验收摘要、阻塞／解除原因、用户重开理由或归档／重绑定授权说明；不得为空。Markdown 特殊字符按表格规则转义。
- `evidence`：当时的安全相对路径或正式证据标识；确实无历史证据时写 `not-recorded` 并解释，不捏造链接或把临时文件当持久证据。
- 转为 done 时，追加完成事件并使 `completed_at` 等于该事件时间。重开前若旧记录只有 completed_at，则先按可证明的旧时间和证据补录完成事件，再追加 `done→planned` 的重开事件。补录不能修改已有事件。
- 从 `planned / in-progress / checking` 进入 blocked 时，追加 `from=<实际前态>, to=blocked`，并在同一文件更新中设置 status、blocked_reason、updated_at。持续 blocked 仅更新当前原因，不追加会覆盖原恢复依据的 `blocked→blocked` 入阻塞事件，也不改旧事件。
- 有可信记录时，解除从最后一次**尚未匹配解除事件**的入阻塞记录取得恢复状态，追加 `from=blocked, to=<该前态>`，清空当前 blocked_reason。目标仅可为 planned/in-progress/checking；不能猜测前态或直接恢复 done。模式切换不改变这项依据；历史未知／冲突按下一条处理。
- 历史 blocked 任务没有可信入阻塞事件，或事件与当前状态矛盾时，不从相邻完成记录、当前模式或旧文档措辞猜测。请用户明确选择本次恢复阶段，记录解除事件及“旧前态未知／冲突、用户选择”的原因；不伪造一条声称知道历史前态的入阻塞事件。只读任务不补写事件，其他安全工作仍遵守模式边界。
- 单个 task 的事件追加、status、completed_at 和 updated_at 作为一次文件更新提交；写失败保留原文件。按预期旧内容检查重复操作，已完成相同转换不重复追加。祖先联动重开先按祖先到子任务顺序逐文件更新，部分失败报告已完成步骤，不能宣称整批成功。
- 归档携带整份 task.md 及全部事件，仅更新路径／索引；不能只靠 Git 历史保留事件，因为 default 本地任务未必被 Git 跟踪。校验必须证明重开后旧完成时间和证据仍可读取；显式只读任务不为此写入事件。

当前 checkout 的同一职责只有一个 writer；存在多个未完成任务不等于让它们共享同一执行身份。父任务可处于汇总 in-progress 而不抢占叶子名额；子任务全部 done 后，父级集成成为实际执行对象并完成自己的验收。重开子任务须先在同一授权操作中重开已 done 的祖先，保留历史完成事件；部分写入失败停止状态推进并报告。

最小只读校验可由既有 Onboard `check-projects` 共用：schema、mode 枚举、ID、父子、引用 containment、索引和时间；不是新 scheduler。损坏 task/index 时不猜模式、不伪造完成、不新建同名替身。default/lite 可继续不依赖该损坏记录的安全工作，并如实说明暂不能更新状态；strict 的必要产物仍须修复。多候选须由用户选择，不自动挑最新文件。

共享已完成任务归档仍需用户确认；按可靠完成日期进入 `archive/YYYY-QN/`，日期未知历史进入 `archive/undated/`。本地记录不会因归档自动公开；删除本地记录也不是每次任务收尾必做动作。

### 7.6 strict 的三张强制清单

| Gate | 必须证明 |
|---|---|
| before-dev | 需求稳定；grill 使用状态和必要 DDD 审核明确；适用 DDIA／legacy／refactoring 通过；读取相关规范及命中 lessons；用户可见行为按 BDD 契约落盘；Ponytail 与影响分析完成 |
| check | PRD／行为规格／design／implement／规范／实际修改一致；smoke → ponytail-review → Code Readability → project-validation；必要独立复核和 release-readiness 通过 |
| finish-work | 必需检查通过；optional 风险接受有责任人；必要 spec／lessons 已完成；更新任务、索引及明确要求的台账；交付证据与剩余风险 |

所有规定节点必须判定，只有真正不适用时明确 not-needed；strict 不是给每个任务硬跑所有工具。required validation 不通过不能以“用户接受 skipped-with-risk”冒充完成；需要切换模式按共同路由取得用户确认，但切换也不豁免数据安全或项目原有发布规则。

default/lite 只借用相关方法，不自动执行这三张完整清单，也不默认输出五 Gate 大表。缺少某一 Skill 时以可用方法检查相关风险并说明，不声称已调用或通过该 Skill。实际选择进入某专项审核时，准确遵循其适用输出，不把“按需”写成“可以伪造审核”。

### 7.7 sbtd-task 与常驻规则的分层

所有需求的轻量路由／模式恢复放在公共规则入口，不以 ai/tasks 存在或先加载 strict Skill 为前提。`sbtd-task` 承载实际任务生命周期和模式分支：default 只需最小记录／恢复能力；lite 读取短清单；strict 才按需加载完整阶段 references。不因任务复杂或项目已有 ai/tasks 自动强制 strict。

常驻 SBTD 核心目标约 2k tokens；sbtd-task 公共／轻量入口目标 ≤3k tokens。strict 的完整适用规则放在同一 Skill 内的按需 references，能力不删，真实加载成本单独计算。19 个 external Skills 安装可用不意味着每个任务都要读取；不新增三个重复核心 Skill 或通用调度系统。无全局规则的 project-only 情况保留短 fallback，不把公共恢复入口藏在 strict 分支。

### 7.8 复核与 Channel 边界

不保留 Trellis Channel 的持久进程、共享日志和 worker 生命周期。主会话默认承担实施与检查，不强制每个任务启动 implement/check 双角色。default/lite 根据实际风险安排检查；strict 命中持久数据迁移、权限／身份、全局配置、安装／卸载、跨服务 contract、广泛公共接口或跨至少三个已定义子系统／热点影响时，必须独立复核。

“子系统”依据实际 package/service 或项目规范；“热点”依据已定义关键符号或可引用 coupling 结果，不拿任意目录／主观词充数。图失败、语言不支持或空结果不证明没有风险。工具不支持时使用源码／LSP／contract 补齐；无法消除的数据安全风险依旧限制危险操作。原生只读 subagent 或独立会话／人工复核可用，不默认启动 Channel；同一验证环境只有一个 controller。

### 7.9 最终项目目录层级与创建边界

标记：`[T]` 可追踪但不自动提交；`[L]` 本地忽略；`[条件]` 需要时才创建。不是一次 init 生成全部目录，更不把它们全部复制到当前模板源仓库。

```text
project/
├── AGENTS.md                              [T] 项目规则与短模式路由
├── .gitignore                             [T]
├── .gitattributes                         [T/条件] union merge 等显式选择
├── .sbtd/                                 [L]
│   ├── developer                          lessons 身份，name=...
│   ├── active-task.json                   当前任务书签，仅 ID/相对路径
│   └── tasks/<task-id>/task.md             default 本地最小记录
├── ai/tasks/                              [T/条件]
│   ├── index.md                           共享任务导航
│   ├── <task-id>/
│   │   ├── task.md                        lite/strict 或已提升的 default
│   │   ├── legacy-task.json               [T/迁移任务] 脱敏只读旧元数据快照
│   │   ├── prd.md                         [条件]
│   │   ├── design.md                      [条件]
│   │   ├── implement.md                   [条件]
│   │   └── <child-task-id>/                [条件] 独立可交付子任务
│   │       └── task.md                     及实际所需的其他产物
│   ├── 00-bootstrap-guidelines/task.md     [条件] 明确要求规范初始化
│   └── archive/
│       ├── YYYY-QN/
│       └── undated/
├── docs/
│   ├── spec/                              [T/条件] 长期项目规范
│   │   ├── lessons.md                     唯一 lessons 短入口
│   │   └── <topic>.md                     架构/API/数据/权限等
│   ├── lessons/                           [T/条件]
│   │   ├── index.md
│   │   ├── topics/<topic>.md
│   │   └── archive/YYYY-QN.md
│   ├── handoffs/<date>-<task-key>.md       [L/条件] 交接摘要
│   ├── CONTEXT.md                         [T/条件] 稳定领域语言
│   ├── adr/<decision>.md                  [T/条件]
│   ├── contexts/<context>/                [T/条件] 多上下文时采用
│   │   ├── CONTEXT.md
│   │   └── adr/
│   ├── PRODUCT.md                         [T/条件] UI 产品上下文
│   └── DESIGN.md                          [T/条件] UI 设计上下文
├── features/<feature>.feature             [T/条件] 真实项目 BDD
├── tests/
│   ├── unit/                              [T/条件] 沿用既有路径
│   │   └── reports/                       [L]
│   ├── api/                               [T/条件]
│   │   └── reports/                       [L] 命名报告与同 stem 中文 MD
│   └── e2e/                               [T/条件]
│       ├── <scenario>.spec.ts
│       ├── manifest/
│       │   ├── ui-test-manifest.json       [T/条件]
│       │   ├── ui-selector-audit.json      [T/条件]
│       │   ├── ui-test-coverage.json       [T/条件]
│       │   └── ui-test-repair-plan.json    [L]
│       └── reports/                       [L]
│           ├── .playwright-html-current/  runner 临时目录
│           └── html/                      命名 HTML 与同 stem 中文 MD
├── maestro/flow/                          [T/条件]
│   ├── smoke.yml
│   ├── ios/
│   └── android/
├── .maestro/                              [条件] 本地工具运行内容
│   ├── reports/                           [L]
│   ├── cache/                             [L]
│   ├── tmp/                               [L]
│   └── runs/                              [L]
├── graft/                                 [L/条件] 可重建代码图与缓存
├── .graft/                                [L/条件] Graft 本地项目配置
├── .impeccable/                           [条件] 专项 UI 工具
│   ├── design.json                        按该工具及项目约定管理
│   ├── live/                              本地运行产物按既有规则忽略
│   └── critique/                          [L]
├── .chrome-devtools-mcp/                   [L/条件]
├── .playwright-mcp/                        [L/条件]
└── test-results/                          [L/条件] runner 临时产物
```

既有测试／规范目录优先，不为了模板重排项目。spec 只在长期规则变化时维护，与模式无关；default 也可能需要改长期规范，strict 没有长期变化则不硬造 spec。任务计划不写进 spec，mode 不写入长期领域规范充当当前状态。

lessons 短入口必须唯一：新项目默认 docs/spec/lessons.md；既有项目明确采用 docs/lessons.md 等分层入口则沿用。本模板源仓库保留 docs/lessons.md，也不创建 features。不把全局 Skills／Onboard 脚本／Codex 用户级 MCP 与 hooks／OMP 用户级 MCP 复制进每个项目。旧 `.codex/`、`.omp/` 等目录只清理有所有权证据的 Trellis 内容，不能整目录删除。

## 8. 跨会话恢复、grill 与 lessons 身份

### 8.1 模式持久化与 handoff

只依靠聊天或 handoff 不可靠：崩溃可能发生在交接前，旧 handoff 可能记录旧模式，本地忽略文件也不随 clone 同步。模式事实源必须是第 7 节的唯一有效 task.md；index 是导航，active-task 是书签，handoff 中的 mode 只是带时间和任务身份的快照。

新会话恢复顺序：

1. 用户明确指定的任务／当前合法引用优先，核对项目、任务 ID 和分支；多个候选先询问。任务分支与当前 checkout 不匹配时进入下述分支冲突处理，不能继续写入或自动改任务 branch。
2. 先读取 task.md 的模式、来源和已作出的选择，再读取关联 handoff 与所需产物。当前用户明确的新模式在本会话优先生效；允许写入且无分支冲突时立即尝试保存，显式只读时不保存。保存失败不退回旧模式，但须说明恢复不可靠；strict 必需产物未保存时，相应门禁仍未完成。
3. task 与旧 handoff 不一致时以有效 task 为准并说明快照过期。只有 handoff 时将其作为恢复线索，确认后补记录，不能默认为可信新模式。
4. 老任务没有 mode、记录不可读取／不合法时询问选择，不静默回到 default。遇到新实质风险仍遵守推荐切换确认；同一已拒绝理由不因换会话而重复询问。
5. 在任务身份和分支没有冲突时，用户说“继续这个任务”已构成恢复意愿，不额外问一次是否恢复；发现 7 天内、分支匹配、未完成交接时才主动提示。超过 7 天不自动恢复，但任务不作废，仍可手动选择。

**跨分支／worktree 冲突：** 展示 task 中的 branch 与已记录的历史 HEAD（若有）、当前 checkout 的 branch 和完整 HEAD。历史 SHA 缺失写 unknown，不猜测；同一普通分支上提交自然前进不是仅凭 SHA 不同就触发冲突，detached 绑定的 SHA 不同或 Git／非 Git 绑定变化则需确认。暂停业务修改和任务元数据写入，由用户选择：

1. 在正确的分支／worktree 继续：遵守当前 host 的工作树管理与 dirty-data 保护，不自动 stash、强制 checkout 或丢弃改动。
2. 明确把任务重绑定到当前分支：核对该分支实际代码与已有证据，记录第 7.5 节重绑定事件后更新 branch；这不自动改变 workflow_mode，也不证明旧验证适用于新分支。
3. 仅只读查看：不切分支、不重绑定、不写 task/handoff，按只读优先规则继续。

“继续该任务”、选择一个执行模式或允许读取 handoff 都不等于重绑定授权。分支冲突确认是独立的安全边界，不违反“正常续作不重复确认”；无论 default/lite/strict 均不得静默选错分支。

主动 handoff 的共同触发：用户暂停、clear／切会话／切分支且有未完成上下文、真实上下文压力、或确有跨会话续作需要的里程碑。取消“3 次状态更新／5 次工具结果”触发，也不把进入 checking 本身当成所有任务必写交接的理由。它不替代初次模式保存。

显式只读任务的交接只在对话中输出，不为上述触发创建或更新 handoff 文件；不得用“自动交接”绕过零写入约束。

handoff 默认仍为 `docs/handoffs/{YYYY_mm_dd}-{task-key}.md`；task-key 对完整逻辑 ID 安全编码，同名子任务不撞名。同任务当天更新同一文件，跨天按需建立；仅信息变化才写，不按每个工具调用刷文件。包括任务 ID、mode 快照及选择说明、branch/HEAD、更新时间、目标、已完成、决策、文件、已尝试命令与结果、未决项、下一步、不要重复事项、脱敏说明和有效的自动模式退出状态。

`本任务不要自动交接`／`本任务恢复自动交接` 与会话级关闭／恢复分别生效；手动要求 handoff 仍可执行。`normal mode` 属于表达风格，不改变 SBTD 执行模式或交接策略。caveman 自动压缩与 default/lite/strict 不是同一“模式”命名空间，不因输出变短而放松验收。

done 任务不生成未完成恢复提示；不预读所有交接历史，不扫描其他项目。公共入口确保三种模式都有恢复机会，但无 SessionStart hook 不能承诺 host 必定加载规则，未保存成功不能承诺可靠续接。

### 8.2 grill-with-docs 前置询问

先模式路由，再判断是否需 grill；模式切换与需求澄清是两个独立决定。三种模式都可以使用 grill，不因选择 lite／strict 就机械询问或重复访谈：

| 情况 | 行为 |
|---|---|
| 目标／范围／验收已经清楚 | 直接继续，简短说明未完整调用原因 |
| 可从项目代码／文档查清 | 先只读查证，解决后继续，不把工具能回答的事实反问用户 |
| 仍有影响方案的歧义，且涉及领域／术语／既有文档 | 在实质性 PRD／设计／拆分或实现前说明具体领域点，询问是否用 grill，提供推荐选项 |
| 用户明确要求 grill | 进入澄清，不重复询问是否使用 |
| 用户拒绝正式 grill | 根据已明确需求继续；必要的关键问题仍要问，不把拒绝方法解释为可以猜业务要求 |

不得编造“预计 N 轮”或时间估计。完整 grill 后三种模式均保留独立的 DDD 边界审核，不能把访谈内 domain-modeling 当替代：strict 遵守完整 reviewer gate；default/lite 以可用方法完成同类独立检查，准确说明没有调用缺失 Skill，不因安装包缺失机械停工；真实领域歧义未消除时仍不得盲目执行相关危险／不可逆决定。

本会话没有完整执行 grill-with-docs；通过用户逐轮提问和项目事实完成澄清，最终由用户要求统一落地。不得把此记录写成“已完整调用 grill”。

### 8.3 lessons 身份建立与日常获取

身份文件固定为 `<project>/.sbtd/developer`，内容 `name=<分隔名>`。只服务 lessons 隔离，不是每个任务必须先填写的账户系统；不是 Git author 或真实姓名，用户可以选择稳定的团队内标识。

**日常写入解析顺序：** 当前项目合法 `.sbtd/developer` → 当前是 linked worktree 且本地文件缺失时读取主 checkout 的合法文件 → 仍缺失则询问。已有文件不合法或类型冲突时不能跳过它去猜别的来源；主 checkout 文件只读取，不复制。禁止从 Git user.name、提交作者、系统用户名、环境变量或历史 workspace 目录推断。

**明确 Onboard 初始化：** 接收新的 `--developer <name>`，或者在需要建立身份时询问；告知将写入当前项目的路径。多项目使用同一名称需用户确认，不擅自全局推断。现有身份 reset 不覆盖；显式新名字与既有名字不同则先裁决。

**仅全局已装、当前项目未 onboard：** 不要求先完整 onboard。普通任务先正常执行；首次确需写共享 lesson 且无可用身份时，Agent 主动询问合法开发者标识，说明将创建 `.sbtd/developer`。用户提供后校验并只建立必要目录和身份文件，不顺带安装工具、生成整套 tasks/spec、改全局配置或执行 Trellis 迁移。

名称必须匹配 `^[a-z0-9]+$`，不能把 `Alice`、`alice.wang`、中文或其他不合法值自动转换。用户暂不提供时 default/lite 暂不写共享 lesson、说明未保存，其他安全工作继续；strict 若 lesson 为必需项则保留未完成，不能虚报全部流程通过。

### 8.4 lessons 记录不变量

路径采用第 7.9 节的唯一短入口及 `docs/lessons/{index,topics,archive}`。日常写入只修改自己的 marker block，新 ID 为 `LESSON-YYYYMMDD-<name>-<slug>`，先查重，历史 ID 不重命名；读取命中文件时读所有人的块。迁移时原文完整保存在私有备份，进入共享目录的正文、marker 和 ID 另受第 11.2 节隐私门约束，不能以“原样保留”公开敏感内容；无法生成安全且引用一致的投影则阻断该项目，不擅自篡改其他人的历史原件。

身份文件本地忽略，lessons 索引和正文可追踪。可选 union merge 仅覆盖 append-only 的 docs/lessons/**，不扩大到会改写的短入口，不默认安装。只记录真正有长期价值的经验，不把普通任务流水账写成 lesson；任何模式缺身份都不能凭匿名占位名写共享内容。Trellis 身份迁移的完整分支见第 11.6 节。

## 9. Graft 集成契约

### 9.1 能力边界

| 原用途 | 新路径 | 不能声称的能力 |
|---|---|---|
| 理解／定位 | `ask`、`map`、`skeleton`；MCP find_code/file_api/repo_map | 自然语言 ask 不等于 LLM 推理或跨语言完整语义解析 |
| 调用依赖 | `callers`、MCP trace_calls；必要时源码／LSP | 不等于编译器级引用完整性；同名、动态调用、反射需复核 |
| 改前影响分析 | 读取相关 symbol 的 callers 与实际源码 | 不用未发生的 diff 冒充改前 blast |
| 改后影响分析 | 显式 diff 基线 + `blast` CLI + 源码／测试 | 六个 MCP 工具中没有直接 blast，check_freshness 不能替代 |
| 新鲜度 | `check`／MCP check_freshness | 只报告漂移，不修复、不检测业务正确性 |
| 多仓理解 | 对每个已授权仓根独立 `ask`／`map`／MCP，任务内只读汇总 | 禁止父目录 Graft 入口；不自动形成跨服务调用边 |
| PDG／taint／route map／group／rename | 本次不提供；使用原生源码／LSP／contract 分析 | 不做工具名或返回结构兼容 shim |

基础 Graft 解析并不覆盖本仓库所有 Markdown／YAML／Shell／PowerShell／JSON 文本契约；广泛扫描依然使用文件检索和真实消费者检查。`graft grep` 的“全部”仅针对已索引文件，不是仓库所有文本。

### 9.2 安装与版本

- P0 使用 `@nanonets/graft@0.18.0` 精确候选验证；正式采用版本记录包版本、gitHead、tarball integrity。实施时若更换版本，先重跑 capability matrix，不直接使用漂移的 latest 结果。
- Node 最低以候选包 metadata 为准，当前为 `>=20`；native tree-sitter 和 grammar 安装必须在目标系统验证，不能承诺“没有原生依赖”。
- check 默认检测可执行路径和 `graft --version`；不运行 `graft version`、`init`、`build`、telemetry mutation 或会偷偷 bootstrap 配置的 CLI。
- 只读 check/plan 必须做 HOME 和项目字节级副作用测试；如果仅执行版本命令也写入内容，应改为读取已安装 package metadata 或隔离探针，不弱化只读契约。
- 安装缺失工具前明确确认；传入 `--yes` 只授权已展示的安装计划，不授权删除旧数据、修改未选平台或上传代码。
- 安装前及所有后续受管入口均设置 `DO_NOT_TRACK=1`，包括 MCP、新会话 Codex hooks 和 Onboard 调用的 CLI，避免仅首次进程关闭遥测；全局安装授权后再持久化 telemetry disable。project-only 不修改 HOME 状态，后续受管查询仍须携带 DNT。用户自行绕过受管入口执行任意命令不在此保证内，文档须给出相同安全运行约束。
- 默认 MCP 使用检测且验证过的本地 executable；必要时用明确 Node 路径和 CLI entry，验证 GUI／精简 PATH；不默认 `npx -y @nanonets/graft` 每次拉取最新版。

### 9.3 平台接线和所有权

| 模式 | 项目内容 | 用户级内容 | 必须禁止 |
|---|---|---|---|
| Codex 完整 init/reset | 授权的项目规则、Graft marker 与图 | 仅授权的 active Codex HOME MCP；hooks 默认关闭，单独 opt-in | 不因 strict 或其他 agent 目录存在而自动安装 hooks／接线 |
| OMP 完整 init/reset | 授权的项目规则、AGENTS marker 与图 | 仅有效 OMP MCP 配置；检测继承来源避免重复定义 | 不写 Codex hooks，不把 Codex matcher 翻译成 OMP event |
| project-only | 按选择建立必要项目规则和最小状态；已有 CLI 可做授权的项目内图 | 无 | 不装全局包／Skill、不写 HOME，不默认生成全部 tasks/spec |
| check/plan | 只读检查和明确计划 | 只读检查 | 不 refresh 图、不升级接线、不生成 cache |

上游 `init --agents agents` 的 explicit 列表优先于 `--yes`，不会固定安装 Claude。然而该 host 可能因已检测到 OpenCode 而附带写入 `opencode.json`；全局 Codex 路径也不能假定就是当前 `CODEX_HOME`。

**接线实现要求：** 先通过精确版本 dry-run 和隔离 HOME 快照确认副作用。项目写入可用候选命令 `graft init <project> --agents agents --no-global --no-mcp --no-hooks --no-statusline --no-build`，再按授权显式 build。P0-01 已证实这些 flag 被接受，且 `--no-hooks` 对独立 `CODEX_HOME` 字节级零写入。上游默认（省略 `--no-hooks`）会写入 `hooks.json` 与 `hooks/graft/graft-hooks.cjs`；**没有正向 `--hooks` flag**。SBTD 必须始终传 `--no-hooks`，除非用户单独授权省略该跳过项。不得把省略 `--no-hooks` 写成显式 opt-in。MCP 使用现有 installer adapter，仅配置被选 host。hooks 不可用不影响显式 CLI/MCP 分析，不伪造有效性。

Codex hook 与 Graft marker、MCP key 的写入者必须唯一，不能 Onboard 合并一次、Graft 隐式再写一次。维护全局配置前保存原内容及 ownership；回滚只还原本次拥有的条目，保留其他 MCP、hook、注释和用户修改。

**AGENTS 写入顺序与幂等：** 当前 `onboard.py:6123-6131` 把项目 AGENTS 作为普通 file operation，`copy_operation():2550-2552` 会覆盖文件。因此每次 init/reset 必须先完成已授权的项目模板写入，再执行 Graft marker 接线，最后校验最终文件；不能只在第一次安装时接线。接线失败不报告该项目 setup 成功，保留备份和失败阶段。测试覆盖 `init→init`、`init→reset→reset` 以及跳过模板写入但维护既有接线：最终必须恰好一组完整 Graft fence，模板规则及已确认保留的项目自定义内容仍在，其他 MCP/hook 条目不丢失。自定义内容的冲突按授权覆盖／保留规则处理，不能靠后置接线掩盖模板覆盖造成的丢失。

OMP 新会话必须做 `initialize`、`tools/list` 和实际 query；`mcp.json` 存在不是可用证明。对多项目 MCP 必须验证每次调用绑定的 repo root，不能让常驻服务所有查询都落到第一个项目。CLI 和 MCP 都不可用时按失败／降级状态报告。

Graft 还存在版本变化后的自动 wiring reconciliation。P0-01 已证候选 init flags 被接受，且 `--no-hooks` 对独立 `CODEX_HOME` 字节级零写入。**版本变化后**原 `--no-global / --no-hooks / --no-mcp` 是否持续有效，以及图 cache 丢失、旧 stamp 缺字段和升级路径，改挂 **P1-04 独占**（OMP 路径由 P1-05 遵守同一禁令，不另起一套测试）。未证明安全前不能在 project-only/check 中启动这种自维护路径。

### 9.4 新鲜度与 diff

1. query-time refresh 是默认机制而非强保证。`--no-refresh`、`GRAFT_NO_REFRESH`、失败、锁竞争、unsupported/ignored files 都必须计入证据限制。
2. 默认 fingerprint 可按 size/mtime 快速判断；有时间戳保留等风险的验证使用 `GRAFT_REFRESH=hash` 或显式重建并记录成本。
3. 刷新失败／busy 时，即使命令退出 0 也不能报告当前图已验证。先重试或显式 build/check；仍不可用则图仅 advisory，以源码／LSP 和测试补齐。
4. 普通 query 主要刷新结构层，不等于刷新全部 markdown cards；直接读被动卡片前需要确认其来源／build 状态。OMP 无 hooks 时明确此限制。
5. `graft check` 不自动刷新，freshness 非零不能当成“程序测试失败”；freshness 为零也不证明影响完整。
6. `blast` 默认比较 working tree 与 HEAD，clean 时会回退到最后一个 commit；必须记录其实际 basis，不能把上一提交误称为本任务影响。
7. `blast --base <ref>` 比较 `<ref>...HEAD`，只覆盖对应提交范围，不包含额外 working-tree 改动；PR 验证记录解析后的 base/merge-base/head SHA。
8. 未追踪文件可进入部分图读取，但 `git diff` 不自动包含它们。另列 untracked、deleted、renamed、mode-only、unindexed 文件；不得为了让 blast 看见而自动 stage 用户文件。
9. 删除符号／文件后当前图可能已丢失旧依赖，改前 callers 证据与实际 diff 必须补齐。空 blast 不是无风险证明。

### 9.5 多仓、worktree 与跨服务

逐项目 setup 是默认。**2026-09-17 用户确认：禁止对含未选子仓的父目录调用 Graft；P1 只对明确的单个仓库根调用。** 不得对父目录执行 `graft init`／`build`／MCP。多个项目共父目录不授权扫描或接线兄弟仓。

若任务需要同时理解多个已授权仓：对每个仓根**独立**调用 Graft，再在任务里做**只读汇总**。这不是 `graft init <parent>`：上游对父目录 init 会接线其下全部 git 子仓，无法只接已选清单。本次不把「选父目录 + 清单一致」做成联邦入口。

`--follow-nested-repos`、`--follow-submodules` 默认关闭，各自独立授权；不能为了补一条边扩大到所有嵌套仓库。linked worktree、不同 branch、同名 symbol、从子目录查询均需 fixture 验证。跨服务因果关系最终依赖 routes/client/contract/Revision Set，不依赖图排名。

### 9.6 网络与隐私

已授权：安装下载、npm 版本元数据。禁止：遥测、`--deep`、`blast --name`、brain connect/cloud、任何自动 LLM enrichment、对外发布图与代码。

不配置、打印或持久化 `GRAFT_API_KEY` 等真实密钥，不修改用户全局环境来实现本任务。所有受管 CLI/MCP/hook 子进程必须限制会启用 LLM/cloud 的环境继承和配置读取；检测到已连接 cloud／自定义 provider 时阻断该接入计划并提示，不静默断开用户其他用途。以新会话和 project-only 后续调用证明限制持续生效，不能只验证安装进程。

原始图／blast 可包含源码、diff 和 Git 作者信息；默认不上传 PR、公网 viewer 或知识服务器。若报告需要 blast，优先 `--no-owners` 和最小脱敏摘要，不能把真实作者信息、源码片段无条件放到公共 artifacts。

最终状态：`Graft: used / skipped / blocked / not-available`，附实际 CLI/MCP、根、版本和覆盖限制；仅在使用或不可用影响结论时报告，不给每个无关 default/lite 任务输出全工具表。安装失败不得报成功，但安装状态与用户任务交付分开。strict 必需的是适用影响分析及验证证据，不把 Graft 单一工具作为不可替代前提；其他模式按第 7 节降级。

### 9.7 完全离线处理（已确认）

- 联网许可不是任务启动条件。Node、Graft 及解析依赖已完整安装时，使用已安装且已验证的本地版本，结构分析不要求访问 LLM 或取得 npm 最新版本。
- npm 版本查询失败记为 `unknown/unreachable`，不以“无法确认最新版本”阻断本地分析，不自动升级或循环重试。上游版本探针默认 2 秒超时、失败返回不可达；这不等于整个 CLI 从不尝试联网。
- 图缺失可使用已安装依赖尝试本地 build；建图、查询或 MCP 失败，则用源码检索、LSP 等可用方式继续，明确 Graft 未提供的辅助证据。
- Graft 未安装或 native 依赖缺失时，不反复运行安装命令；无法离线取得完整依赖就报告安装未完成，继续能够安全完成的用户任务。安装状态与任务交付状态分别报告，不把降级说成 Graft 安装成功。
- 离线首次安装仅在已有完整、经校验且适配目标 OS/arch/Node 的依赖产物时尝试；单个顶层 npm tarball 不保证足够。不新增受管离线镜像产品或维护上游 fork。
- P0-01／AC-10：预装后 `graft build`／`ask` 在 `sandbox-exec` 下 exit 0。`graft version` 在同一 sandbox 仍打印 `latest on npm: 0.18.0`（exit 0），故版本探针 fail-closed **仍待验证**，不能当作已断网。`blast --name` 无 key 时 stderr 提示后仍 exit 0、不调用 LLM。

离线策略与三模式共同生效：已安装本地能力优先，工具不可用换方法，无法实际执行的部分如实报告；default/lite 不因缺辅助工具或形式文档冻结普通任务，strict 对其真正必需的证据仍不能虚报通过。

### 9.8 P0-01 隔离 spike 结果（2026-09-17T10:14:26+08:00）

环境：darwin 27 arm64，Node v24.15.0，npm 12.0.2。隔离 `HOME`／`CODEX_HOME`／XDG／npm prefix；开发者 `~/.codex` 配置与仓库 `graft/` 前后摘要一致。完整日志在本机 `/tmp/sbtd-p0-01-graft-spike/`（不入库）。

npm 12 默认 `allowScripts` 会挡住 Graft／tree-sitter 生命周期脚本；仅 `ignore-scripts=false` 不够。必须显式 `--allow-scripts`（含 `tree-sitter-cli`）。脚本被挡时 CLI 在 import 期因缺少 `tree-sitter-kotlin` native（Node ABI 137）崩溃，**不得把该次 exit 1 当成命令语义**。

安装后的 `package.json` 无 `gitHead`；registry 元数据仍有 pin。integrity 以 npm dist 为准。

| 能力 | 状态 | 证据要点 | AC |
|---|---|---|---|
| `@nanonets/graft@0.18.0` 隔离安装并可运行 `graft --version` | proven | 允许 scripts 后 exit 0，stdout `0.18.0` | AC-01 |
| 结构 `build`／`ask`／`callers`／`skeleton`／`grep`／`map`／`blast`／`check` | proven | 最小 Python/JS fixture；无 LLM | AC-01、AC-07 |
| `check` 在编辑后 STALE 且不自动 refresh | proven | 改 `app.py` 后 exit 1，stdout `graph check: STALE` | AC-07 |
| MCP stdio `initialize`＋`tools/list` | proven | 六工具：`graft_find_code`、`graft_file_api`、`graft_check_freshness`、`graft_trace_calls`、`graft_find_all`、`graft_repo_map`；无 blast 工具 | AC-01、AC-08 |
| 候选 init flags `--no-global --no-mcp --no-hooks --no-statusline --no-build` | proven | 单仓 exit 0；跳过 HOME 写入 | AC-08 |
| 上游默认安装 Codex hooks | proven（默认不安全） | 省略 `--no-hooks` 写入隔离 `CODEX_HOME` 的 `hooks.json` 与 `graft-hooks.cjs` | AC-08 |
| `--no-hooks` 零 hook 写入 | proven | 独立 `CODEX_HOME` 前后 digest 相同，仅占位 `config.toml` | AC-08 |
| 正向 `--hooks`／显式 opt-in flag | **unsupported** | `graft init --help` 无正向开关；不能把省略 `--no-hooks` 当 opt-in | AC-08 |
| 预装后离线 build/query | proven | sandbox 下 build/ask exit 0 | AC-10 |
| 离线 `graft version` fail-closed | still-to-verify（**P1-03 所有**） | sandbox 仍 exit 0 并显示 npm latest。不阻断 P0-01；P1-03 必须用真实断网证明版本探针不可达 | AC-10 |
| `blast --name` 无 key 不走 LLM | proven（仍须禁该 flag） | stderr `no API key ... keep their symbol names`，exit 0 | AC-10 |
| 只对选定仓 `build` 时未选 sibling 零写入 | proven | selected-b build 前后 sibling digest 不变 | AC-09 |
| 父目录 `graft init` 不联邦未选仓 | **unsupported／安全失败**（产品已收口） | 上游 `init <parent>` 会接线全部 git 子仓。用户已确认 SBTD **永不**对含未选子仓的父目录调用 Graft；P1 只对显式单个仓库根调用。P1-06 仍须证明实现遵守此禁令 | AC-09 |
| 隔离 uninstall dry-run 后 `-y --no-global` | proven | 项目内 Graft 接线移除，开发者 HOME 未改 | AC-01、AC-08 |
| 开发者真实 HOME／Codex／仓库 graft 路径 | proven | 受管路径摘要一致；newer 文件仅为 OMP session 噪音 | AC-08 |
| 版本变化后 reconciliation 保持 `--no-global/--no-hooks/--no-mcp`；cache 丢失、缺 stamp、升级 | still-to-verify（**P1-04 所有**） | spike 未覆盖。不阻断 P0-01；未证明前 project-only/check 不启动自维护 | AC-08 |

**P0-01 台账为 `done`。** spike 证据见第 9.8 节。AC-09 不以「上游不再联邦」通过，而以用户确认的调用禁令收口：禁止对含未选子仓的父目录调 Graft，P1 只对明确的单个仓库根调用。Graft 没有正向 `--hooks` flag；SBTD 的 opt-in 是用户确认后持久保存的授权，用来省略 `--no-hooks`。未获该授权必须传 `--no-hooks`。§9.3 剩余升级／cache／stamp／reconciliation 改挂 P1-04，不阻断 P0-01。

## 10. Onboard、catalog 和公开安装契约

### 10.1 安装命令行为（不是 default/lite/strict 执行模式）

| 命令／模式 | 目标行为 |
|---|---|
| public `skills add` | 只安装自包含 Onboard 目录；不自动安装其余 Skill、CLI、AGENTS 或初始化项目 |
| `plan` | 展示选定 host、项目、全局路径来源、Graft 版本及预期写入、migration 冲突；完全只读 |
| `check`／`check-projects` | 只读报告；新增 SBTD 结构和 Graft 可用性，不触发旧 Trellis 初始化 |
| `init` | 仅选定项目的授权安装与必要脚手架；保留任务／spec／lessons，不强制每个项目预建完整任务包，不暗中迁移旧 Trellis 数据 |
| `reset` | 保留现有 Skill 维护语义；不覆盖项目历史／身份／业务文件，不把 reset 当旧项目迁移或清理命令 |
| `init-projects` | 严格 project-only；缺 CLI 报告缺失，不越权装全局包；只处理本次明确选择的项目文件 |
| `migration --phase ...` | 固定 plan/apply/verify/cleanup 四阶段；apply 只迁移数据和停旧路由，新部署／smoke 独立属于 P2-04；命令、manifest 和二次确认见第 10.2.1 节 |
| `recovery --phase ...` | 仅 manifest-scoped 恢复 plan/apply；输出原子保存的 recovery plan／receipt，不增加 journal、锁、证据索引或备份处置子系统 |
| `sync` | 仍是显式本机发布动作，先 Orca 精确名称 preflight，后范围内复制／校验／live prompt 比对 |
| `update` | 仍只按既有规则写回版本基线和归档 UPDATE；不附带 sync、迁移或 live automation 修改 |

只全局安装／升级 v2 不扫描或改写所有老项目。Agent 进入旧项目可提示是否迁移，未经确认不改旧数据和 ignore。全局已安装、项目未 onboard 也可正常执行需求或按第 8.3 节仅建立身份；这不授权完整初始化。新目录是按需资产，不是安装成功必须凑齐的目录清单。

首次按需写本地记录需要的 ignore 保护可以按第 7.3 节取得窄授权；它只追加所需新保护，不能借此移走 `.trellis` 数据或删除旧规则，不等于完整老项目迁移。

### 10.2 CLI 与 JSON cutover

删除公开 Trellis flags，不留隐藏兼容 alias：`--trellis-user / --trellis-platform / --skip-trellis-init / --skip-trellis-bootstrap` 及 PowerShell 对应参数。新身份使用 `--developer`；SBTD 跳过开关只有存在实际场景才增加，不能机械一比一改名。

目标报告字段为 `sbtdInit`（安装计划）、`sbtdProjectSetup`（逐项目安装结果）、`graft`（版本／graph／wiring）、`migration`（四阶段迁移）；仅带下述迁移部署上下文的init/init-projects另返回`deploymentEvidence`。Python是唯一实现入口，Bash／PowerShell只转发同一参数／JSON／退出码，不设计另一套字段或阶段。

继续保证 stdout 只有一个 JSON 根对象；进度和诊断走 stderr；逐项目保留 status/reason/nextStep，不以聚合状态隐去失败项目。既有 `0=success, 2=needs-user/blocked, 3=file verification failure, 4=Ponytail provider conflict, 5=project setup failed, 6=bootstrap-required` 的已覆盖语义尽量保留，不重复赋予相反含义。若新增迁移专用退出码，必须在两安装器和文档同步声明。

#### 10.2.1 显式迁移 CLI、manifest 与清理授权


plan 可接收 `--publication-decisions <private-file>`：在运行 plan **之前**，用户或其授权 Agent 经明确的私有准备授权，在仓库外准备 share/redact 的安全候选并逐项裁决，记录源 checksum、目标、批准依据及已存在候选的路径／checksum；private-only 可选内容不要求共享候选。plan 只读验证并嵌入 manifest.payload.publication_decisions，必要项缺候选／批准则 blocked。私有准备不写项目或 HOME，纳入同一责任人和备份保留范围；apply 只复验已绑定候选，不新增裁决。
以下是 v2 必须实现的公开契约，当前 CLI 尚未提供。沿用现有 `--projects-root` 的逗号分隔绝对路径输入约定；路径规范化／去重、containment 和冲突校验完成后才形成计划。

下文“migration apply／verify／cleanup”均为 `migration --phase <阶段>` 的简称，不另增同义子命令或兼容 alias。

| 阶段 | 统一调用形状 | 允许的副作用 |
|---|---|---|
| plan | `onboard.py migration --phase plan --projects-root <roots> --backup-root <private-dir> --custodian <label> [--publication-decisions <private-file>] --json` | 只读验证下述版本化候选输入并绑定责任／保留策略；仅无待发布产物、全部输入可按既定规则私有保留时可省略该文件；不创建目录或部署 |
| apply | `onboard.py migration --phase apply --manifest <plan-file> [--apply-receipt <apply-file>] --yes --json` | 初次不带receipt；重试显式传入并验证manifest绑定，跳过成功且后态未变项，仅续作合法未完成项；不部署、smoke或最终删除旧数据 |
| verify | `onboard.py migration --phase verify --manifest <plan-file> --apply-receipt <apply-file> --deployment-evidence <evidence-file> --json` | P2-04 独立部署和真实 smoke 完成后，只读核对所有项目及当前清理候选，输出验收记录；不自动部署、查询会写缓存的工具或清理 |
| cleanup | `onboard.py migration --phase cleanup --manifest <plan-file> --apply-receipt <apply-file> --deployment-evidence <evidence-file> --verification <verification-file> [--cleanup-receipt <cleanup-file>] --confirm-cleanup <verification-id> --json` | 初次或携合法累计receipt重试，均再次确认并复验完整证据链；仅处理绑定的剩余旧内容，普通--yes不代替确认 |

plan/apply/verify的stdout均为单JSON对象；诊断走stderr。调用者只在获授权私有报告位置保存对象，不写共享任务树；显式保存stdout不改变plan/verify只读语义。P2-04统一使用下述带迁移上下文的现有init/init-projects入口部署并生成证据；apply/verify不递归调用它。sync仍是独立显式动作并保留Orca preflight，不作为同批次第二个部署写入者；途中另行sync若改变受管状态，按冲突停止，不伪造累计记录。

所有阶段顶层固定字段：`mode: "migration"`、`phase`、`status`、`manifest_id`、`verification_id`（不适用为 null）、`projects`、`reason`、`nextStep`、`migration`。`migration` 中仅放当前阶段产物：plan 的 `manifest`、apply 的 `apply_receipt`、verify 的 `verification`、cleanup 的 `cleanup_receipt`；失败且没有有效产物时为空对象。后续文件参数接收相应子对象，例如 `response.migration.manifest`，不接收整个 envelope。状态枚举为 `planned / applied / verified / cleaned / already-complete / blocked / failed`；项目结果不被聚合状态隐藏。

数据对象采用 `{schema_version: 1, payload: {...}, <对应_id>: <sha256>}`；manifest、apply_receipt、verification、cleanup_receipt 的 ID 键分别固定为 `manifest_id`、`apply_id`、`verification_id`、`cleanup_id`。ID 是 payload 的 UTF-8 JSON（键排序、紧凑分隔、非 ASCII 不强制转义、禁止非有限数值）SHA-256，不含自身；输入 ID 缺失或不匹配拒绝处理。哈希只证明内容一致，不是用户授权或真实测试发生的密码学证明：

- manifest payload 固定记录：规范化项目根／共享 HOME 批次、source ref/HEAD（非 Git 为 null）、源文件和相关配置的路径／类型／checksum、目标预期旧状态、允许操作及所有权证据、拟清理范围、私有备份位置、适用 Onboard/Graft 版本。只允许受管结构化操作，不能把 manifest 内任意字符串作为 shell 命令执行。
- manifest 另记录 custodian、backup_root、创建时间及第 11.8 节保留要求；backup_root 必须是明确的仓库外私有位置，不混入无关数据，不新增 control/data 布局或 lifecycle 配置文件。恢复计划与收据仅保存在 manifest 所在的已授权私有目录，见第 10.2.3 节。
- apply_receipt 绑定 manifest_id，分别记录项目私有操作与批次 shared_results；项目只引用共享 ID。项目 applied 需本阶段全部依赖成功；全批次成功才允许 P2-04。执行成功或可处理的部分失败时，将 receipt 原子保存到 manifest 所在私有目录再返回 stdout 副本；突然退出未留下有效收据且状态不符时 blocked，不承诺无证据自动恢复。
- apply 的 --apply-receipt 只在同 manifest 的续作／完成核对时使用；初次仍验证全部前态。完整成功记录且后态未变返回 already-complete；合法部分记录先核对累计已完成后态，跳过这些操作，再核对未完成项前态并续作。无可信收据且当前不再是初始前态时 blocked，不自动发现收据或按目标恰好相同猜成功。
- apply／cleanup 每次成功或可处理失败均输出一份**自包含累计收据**：保留前次已完成结果、该阶段原始 before 和 backup_ref，合入本次结果及尚未完成项；不能只返回本次增量。payload.previous_receipt_id 初次为 null、续作为输入收据 ID，用于关联而非索引扫描；最新收据本身足以供 verify/recovery 消费。新收据原子保存为新文件，旧收据不可改写，不能因重试以中间状态覆盖原备份。
- P2-04 生成迁移外层 deployment evidence，绑定 manifest_id、同一项目／共享 HOME 范围、实际 ref/HEAD、累计部署操作及原始before/backup_ref、当前结果／配置checksum和真实验证报告引用。正常或可处理失败均原子保存到manifest私有目录；尚无smoke时只记录实际操作和未验证状态，不能声明部署验收通过。重试保留已完成操作及原始备份，最新单份外层记录足以供recovery使用；原生验证证据schema不变，资源改变后旧smoke不得冒充当前成功。计划、mock或合法哈希不代替真实证据。
- verification payload 绑定 manifest_id、apply_id、deployment evidence 文件的原始 bytes SHA-256、验收时 refs、被保留的新资产状态，以及实际 cleanup 候选的路径／类型／操作／当前内容 checksum；输出 verification_id。共享配置按受管条目清理，保留 foreign entries。
- 首次 cleanup 必须读取命令中传入的 manifest、apply_receipt、deployment evidence、verification，重算各 ID／文件哈希并核对相互绑定、项目范围、成功状态与实际候选。只给哈希而没有可读取证据对象不得清理。每个破坏性操作前复验预期状态；内容变化或证据缺失返回 blocked，要求重新核对／verify 并再次确认。plan 源／目标前态变化不能按旧 manifest 初次 apply。
- --confirm-cleanup 必须等于本次展示且用户刚确认的 verification_id；缺失、错误或未绑定当前清单的旧 ID 返回 blocked。合法 partial receipt 可继续绑定同一 verification_id，但须重新展示已完成／剩余范围并取得本次确认，Agent／wrapper 不得复用旧同意或自动填参。cleanup 正常成功或可处理失败都原子保存累计 cleanup_receipt 再返回；payload 绑定 manifest_id、verification_id、apply_id、deployment evidence 哈希、实际操作、保留资产和实际 refs／路径／checksum／不存在状态。
- cleanup 重试须显式传入 --cleanup-receipt 并核对完整证据绑定。完整成功记录及后态一致才 already-complete；合法部分记录按第 10.2.2 节跳过成功且未变资源、续作前态仍匹配的未完成资源，不因“部分失败”本身拒绝。缺失／不完整收据、未知写入或后态冲突才 blocked，不扫描索引或凭目录消失猜成功；无法续作的已知部分写入可另走独立恢复。cleanup 永不删除原件备份、候选、manifest 或恢复收据，处置另按第 11.8 节人工授权。

**共同值格式（仅现有私有交换文件，不新增服务）：**

- `state` 固定为 `{type, checksum}`，type 为 `absent/file/directory`；absent 的 checksum 为 null，其余为小写64位SHA-256。普通文件摘要取原始bytes；目录摘要取按相对POSIX路径排序的完整条目数组之规范JSON摘要，条目固定 `{path,type,checksum}`，文件记录bytes摘要、目录记录null，根自身不入数组，空目录条目必须保留；symlink或不支持类型拒绝。权限／所有权安全检查独立执行，摘要不能代替它们。
- `object_ref` 固定为 `{path,state}`，path为规范化绝对路径，引用必须可读取且state匹配；输入源、候选、备份及报告不可用absent。未知当前状态用null表示时只限下述失败结果，不能冒充absent。路径仍服从containment、私有目录和非symlink约束。
- 以下新JSON格式均使用UTF-8；所有列出的键必填，允许null的情形逐项列明；未知schema_version、未知键／枚举、重复JSON键、错误类型或非法摘要均拒绝，不自动改名、补默认值或吞掉未知字段。

**publication-decisions v1：**

文件根固定为 `{schema_version: 1, items: [...]}`；manifest.payload.publication_decisions 嵌入这个完整对象，而非自由格式文本或仅文件路径。每项代表一份完整共享候选（或一组只私有保留的源），内部字段的删改已体现在候选中；不为每个正文token增加策略对象。

| items[] 字段 | 类型／固定语义 |
|---|---|
| item_id | 非空字符串，在本文件内唯一；仅为私有输入关联键，不改旧task/lesson ID |
| sources | 非空object_ref数组；单项内源路径不重复，不同候选可引用相同源 |
| target_path | share/redact为选定项目授权共享范围内的规范化绝对路径；private-only为null |
| required | boolean；plan按迁移盘点和保全契约独立核对，不能用false降级必要产物 |
| decision | 精确枚举share、redact、private-only |
| candidate_ref | share/redact为已存在的仓库外私有候选object_ref；private-only为null |
| approval | 固定为`{basis,scope}`；basis为非空批准理由／人工溯源说明；scope固定含`sources,target_path,decision,candidate_ref`，是获批时对应字段的完整结构快照，类型同本项字段 |

plan逐字段核对approval.scope与本项sources/target_path/decision/candidate_ref完全一致，再验证真实源／候选状态、必要产物覆盖及目标前态。private-only的获批target_path/candidate_ref均须为null。未知键、缺失或不匹配只读blocked；不尝试从自由文本basis自动判定批准内容。scope和hash仅证明所声明批准范围未漂移，不认证操作者身份或替代真实用户授权；准备授权与apply前实际确认仍独立要求。非null target_path不得重复、别名冲突或父子重叠，一个目标的多个源合并为一项。必要项缺失或被标为private-only、未知项、重复item_id／目标及候选不符均拒绝。share/redact均检查完整候选的隐私；private-only仅保留可选私有内容、不发布。只有无待发布产物且全部可私有保留时才可省略输入，此时嵌入`{schema_version:1,items:[]}`，不能跳过必要产物。

**deployment-evidence v1：**

外层固定为 `{schema_version:1, payload:{...}, deployment_id:<sha256>}`，deployment_id 使用本节规范payload哈希；verify/cleanup同时验证此ID及已绑定的文件原始bytes哈希。由P2-04的部署执行路径生产，三个消费者verify/cleanup/recovery读取同一对象，不修改其引用的原生报告schema。

| payload 字段 | 类型／固定语义 |
|---|---|
| manifest_id / apply_id | 对应本批次manifest及完整成功apply_receipt的ID，须交叉核对 |
| previous_deployment_id | 初次null；重试为此前部署外层记录ID；当前文件仍须自包含累计结果 |
| status | succeeded、not-verified、blocked、failed之一 |
| projects | 项目结果数组，规范化root唯一，集合必须与manifest一致 |
| shared_results | 本阶段共享resource_result数组；同resource一次结果，项目仅引用 |
| started_at / finished_at | 本次执行实际RFC3339时间，带时区；不伪造尚未发生事件 |

每个projects[]对象固定包含`root,source_ref,head,status,reason,nextStep,private_results,shared_operation_ids,report_refs`。root绑定manifest项目；source_ref为实际分支字符串，detached为null；head为实际完整OID字符串，非Git两者均null。status同上，reason/nextStep为字符串，失败／阻塞须解释原因及下一步。private_results为该项目私有resource_result数组，shared_operation_ids引用共享结果中的操作；report_refs为原生验证证据及正式报告的object_ref数组，无报告时为空，不捏造通过。每项目状态结合全部私有／共享依赖及当前真实smoke判定；全部成功且所需报告齐全才succeeded，操作完成但未验证为not-verified，阻塞为blocked，实际操作或验证失败为failed。批次按failed→blocked→not-verified→succeeded优先级汇总，不掩盖逐项目结果。

resource_result固定为`{phase,resource_id,operation_ids,dependent_projects,status,backup_ref,before,after,error}`，对应第10.2.2节的资源结果，不引入第二套操作ID；这里phase必须为deploy。operation_ids/dependent_projects为去重数组，与manifest精确匹配；私有资源依赖仅本项目，共享资源依赖全部声明项目，资源不得同时进入私有与共享集合。私有操作也沿用下节resource_id/operation_id推导规则。status为succeeded/failed/blocked；before/after为state或null（无法观测），backup_ref为原始私有备份object_ref或null；error为字符串或null。成功必须有可核对前后态，原件存在时备份必须匹配before、原件不存在时backup_ref为null；失败／阻塞必须如实保留已知状态和错误，不把未知状态当未执行。未执行操作由manifest与结果差集表示，不生成虚假成功记录。

verify/cleanup只接受部署整体succeeded且所有引用证据当前有效的对象；recovery也可接受合法的部分完成记录（status为not-verified、failed或blocked），仅对可证明状态生成恢复步骤，不增加partial枚举。必要before/after或备份缺失、scope/ID不符则blocked；不能因JSON合法或哈希匹配就允许清理。原始备份及累计结果跨重试保留，新文件原子保存，旧文件不改写。

**P2-04部署证据的显式I/O（不是新migration阶段）：**

统一形状为`onboard.py init --migration-manifest <manifest-file> --migration-apply-receipt <apply-file> [--previous-deployment-evidence <previous-file>] --deployment-evidence-out <new-private-file> --yes --json`；纯project-only批次可将init换为已有init-projects。其余既有scope/host参数必须与manifest相符，不得扩大范围；project-only遇到HOME操作直接拒绝。首次不传previous，重试必须显式传入，不扫描目录寻找前次结果。这些附加参数只对init/init-projects有效，除previous外须成组出现；普通init语义不变。

入口先验证manifest、完整成功apply_receipt、版本／授权范围及前次deployment evidence的ID、manifest_id/apply_id、资源后态；再按phase=deploy执行现有受管安装／接线和smoke路径，不执行apply/cleanup或清单外安装。缺必要工具或scope冲突则停止，不能借普通init扩大副作用；部署须取得本次安装确认，不复用migration apply的同意。已成功资源跳过且沿用原before/backup_ref，只续作前态仍匹配项；smoke未成功时重新验证，不能靠旧测试或metadata补写成功。

--deployment-evidence-out须是manifest私有目录内的未占用普通文件目标，在任何部署写入前校验可安全创建；不得覆盖previous或无关文件。正常或可处理失败后原子保存累计外层证据。单一init JSON中`deploymentEvidence`固定为`{path,evidence}`，path为实际保存位置，evidence为完整deployment-evidence v1对象；尚无合法证据或保存失败时为null并返回非零，保留真实错误、备份及现有结果，不声称可自动恢复。普通无上下文init不返回此附加字段。后续--deployment-evidence读取已保存的evidence对象文件，重试将其显式作为previous输入；原生报告仍按既有reporter产出并引用。

#### 10.2.2 共享 HOME／Skill 根的批次级操作

共享文件不能复制成“项目 A 的写入”和“项目 B 的写入”。同一迁移 manifest 用 `payload.shared_operations` 统一拥有它们；`payload.projects[].shared_operation_ids` 只引用相关 ID。共享范围仍须包含全部依赖项目或明确隔离，不能靠去重绕过授权。

| 字段／集合 | 固定含义 |
|---|---|
| `resource_id` | 对 `[owner_kind, normalized_target_path]` 按第 10.2.1 节规范 JSON 做 SHA-256；标识物理配置文件或完整受管 Skill 目录，不由某个消费项目拥有 |
| `operation_id` | 对 `[phase, resource_id, selector]` 的规范 JSON 做 SHA-256；phase 为 apply/deploy/cleanup，selector 是精确受管条目／marker，整资源操作用固定值 `whole-resource` |
| `dependent_projects` | 引用该操作的规范化项目根集合，取自 manifest 的 projects[].root；排序去重，须与 projects[].shared_operation_ids 的反向引用完全一致，漏项／未知 ID 在写入前拒绝 |
| `shared_operations[]` | 每operation_id唯一，使用下述统一operation描述；跨项目共享资源只在此集合拥有，项目仅引用 |
| `shared_results[]` | 按 phase/resource_id 记录一次资源更新：operation_ids、依赖集合、status（succeeded/failed/blocked）、backup_ref、整体 before/after 及错误说明；原资源不存在则 backup_ref 为 null 并记录不存在前态；未执行不生成成功结果 |

项目私有操作固定存于`payload.projects[].private_operations`数组，覆盖该项目apply/deploy/cleanup三阶段；不是未声明的自由文本动作。它与shared_operations使用同一operation结构，固定键为`operation_id,phase,resource_id,owner_kind,target,selector,change,ownership,before_requirement,dependent_projects`。phase为apply/deploy/cleanup；owner_kind是安装器已支持的实际配置所有者／格式，target是规范化绝对路径，selector为精确受管条目或whole-resource；ID按上表计算。change/ownership为P1-01统一schema中的受管结构化变更与归属证明，由同一Python计划器生产／消费，未知变更种类拒绝，不接受任意shell字符串或新命令DSL。

before_requirement固定为二选一：`{kind:"state",state:<state>}`，或`{kind:"phase-after",phase:<earlier-phase>,resource_id:<same-resource>}`。后者只能引用同资源更早阶段的实际累计后态，不能引用自身／后续阶段；执行及verify时必须取得对应证据。私有dependent_projects只能为本项目root；HOME等共享资源统一进入shared_operations，不能复制成项目私有项。

所有operation_id在全manifest内唯一；同phase/resource的多个selector先合并一次写入，资源不能跨私有项目或私有／共享集合重复拥有。项目private_results及shared_results均以phase/resource_id唯一，重复结果直接拒绝、不后写覆盖。结果中的operation_ids须精确等于该资源本阶段声明的集合；未知ID、遗漏其中部分操作、重复或scope冲突拒绝。合法失败可缺尚未执行资源的结果，其未完成集合由manifest减已记录集合得到；阶段succeeded须全部声明资源/操作都有成功结果，不能靠省略私有操作通过verify。

资源所属配置类型指文件的实际所有者／格式，不是当前消费它的 Agent：OMP 读取同一个 Codex 配置不会形成第二个资源。规范化遵循实际平台路径语义，拒绝 symlink／越界；同一物理路径不能因别名、大小写写法或两个 host 名称被登记为不同资源。所有者／格式不明或互相冲突则 blocked，不随意选择解析器。

这里的 deploy 是共享资源所属的阶段，不新增 migration --phase deploy 命令；apply 只调度 phase=apply，P2-04 才执行 deploy，cleanup 只执行已确认的 cleanup。已有文件的别名／硬链接或配置所有权无法唯一归一化时，计划阶段拒绝该资源，不生成两个会写同一物理对象的 ID。

同一 phase 对同一 resource 的多个受管条目，先合并成一个候选文件／目录变更，验证它们可兼容，再以**一次备份、一次整体前态校验、一次资源写入**完成。共享文件中不相关用户条目保持原样；重叠 selector 或无法确定兼容性的变更先报冲突，不靠重排或多次覆盖解决。逻辑 operation_id 可有多个，但不因此写同一文件多次。

apply_receipt、P2-04 的迁移部署记录及 cleanup_receipt 分别携带本阶段 shared_results；部署记录作为迁移外层绑定信息引用现有原生验证证据，不改通用 project-validation schema。verification 绑定这些资源结果和依赖集合。项目 A 私有操作成功但某共享依赖失败时，A 不能宣称 applied；共享失败使所有依赖项目的本阶段未就绪，未执行的后续阶段不混入当前 applied 判定。

重试先按累计结果逐资源核对：已成功且未变的资源跳过，不让第二个项目用旧前态执行；未完成资源仅在当前仍为预期前态时续作。部分资源已写但未完成、缺可信结果或用户改动时停止该续作，保留证据并选择独立 recovery／人工核对，不把未知状态当未执行。资源跨阶段前后态须衔接；存在后续阶段结果时，不重放旧阶段覆盖新配置。重试不重新备份／写入已成功资源，新收据沿用其原始before/backup_ref及结果。

回滚按资源及阶段逆序只执行一次，使用第 10.2.3 节 recovery plan/apply。共享恢复必须覆盖 dependent_projects 的授权闭包；范围不完整则计划 blocked，不借一个项目的同意修改其他项目配置。用户修改冲突保留原件和备份，不以 force/reset --hard 强行恢复。

已有 manifest/receipt 不可变。恢复结果持久化为独立 recovery_receipt，引用原证据及资源，不修改原 receipt，不按项目复制共享恢复。部署仍只归 P2-04；恢复入口不增加 migration 阶段、常驻服务或新的 Agent 调度框架。

迁移命令成功／已完成返回 0；缺授权、输入／manifest 不合法、状态过期或冲突返回 2；checksum／保全／验收不通过返回 3；实际文件操作失败返回 5，并保留备份和逐项目结果。现有 Ponytail 冲突 4 与 bootstrap-required 6 的含义不复用。参数解析错误遵循 argparse 的 stderr＋2；进入处理器且指定 --json 后，成功或失败均保持单一 JSON envelope。

#### 10.2.3 Manifest-scoped 恢复入口

不新增 journal、写入锁、证据索引、常驻进程或 backup-set lifecycle 子系统。只复用已有 manifest、完整／部分阶段收据、before 备份，以及同一私有目录中的原子 recovery plan／receipt。操作按既有单 controller 边界执行；有并发写入迹象或无法确认受管资源状态时拒绝自动恢复，不冒充具备并发写隔离能力。

| 动作 | 调用形状 | 副作用 |
|---|---|---|
| 恢复计划 | `onboard.py recovery --phase plan --manifest <file> [--apply-receipt <apply-file>] [--deployment-evidence <evidence-file>] [--cleanup-receipt <cleanup-file>] [--projects-root <roots>] --json` | 只读核对明确传入的阶段证据和备份，返回计划；范围必须满足共享／保护授权闭包 |
| 恢复执行 | `onboard.py recovery --phase apply --plan <file> [--recovery-receipt <receipt-file>] --confirm-recovery <plan-id> --json` | 独立确认后执行或按可信累计收据续作；不能临时改变范围，原子保存新恢复收据 |

plan 接受可选 `--apply-receipt`、`--deployment-evidence`、`--cleanup-receipt`，各自只能出现一次，输入可以是失败阶段留下的合法部分记录；缺成功 smoke 不妨碍为失败部署生成恢复计划。缺某阶段证据不视为该阶段未执行：只要当前资源不能与完整可证明的阶段链核对，就 blocked。没有任何记录且所有受管资源仍等于 manifest 前态时，可以报告无需恢复；不能从“目录不见了”推断恢复成功。

plan 可用 `--projects-root` 指定 manifest 内的项目子集，默认整个批次；所选资源必须包含保护规则依赖和全部共享 dependent_projects，否则返回 blocked，要求用户扩大范围或另行人工核对，不静默丢弃共享操作。apply 不接受临时改变范围的参数。

输出固定为单 JSON：`mode=recovery、phase、status、manifest_id、plan_id、receipt_id、projects、reason、nextStep、recovery`，recovery 中为 plan 或 receipt，未生成时为空对象；status 为 planned/restored/already-complete/blocked/failed。退出码沿用 0/2/3/5，参数解析错误 stderr＋2。Bash/PowerShell 只转发，不重新实现恢复判定。文件对象采用 `{schema_version:1,payload,plan_id或receipt_id}` 和第 10.2.1 节规范哈希；这些 ID 不是人的授权证明。

`recovery_plan.payload` 固定包含 manifest_id、选定项目和共享授权闭包、明确输入证据的路径／哈希、当前 refs／资源状态、目标 pre-apply、按 cleanup→deploy→apply 排列的逆向步骤、每步稳定 step_id／resource_id／原 operation_ids／依赖顺序／backup_ref／expected_current／restore_to、冲突及风险。默认恢复本次迁移前的受管文件状态，不恢复无关业务数据、Git 历史或全局 npm 包。已知未落地步骤不产生恢复动作，不能证明的步骤不猜测。

调用者经用户授权把返回的 plan 子对象以“同目录临时文件＋原子替换”保存到 manifest 目录；plan 命令本身仍只读。该目录必须已确认私有、非目标仓库、非 symlink 逃逸；所有恢复输出只允许在该目录内的专用普通文件，拒绝覆盖无关文件。明确传入的外部私有阶段证据仅只读，路径和哈希固定到 plan，不扫描它们的父目录。

执行前展示完整资源和共享依赖范围，用户的 --confirm-recovery 必须匹配当前 plan_id，不能复用 --yes/--confirm-cleanup。初次执行重核所有起始快照、证据、before 备份和 refs；写入前逐步校验 expected_current。变化则重新计划和确认。恢复旧敏感内容前先恢复必要 ignore／私有权限；若将公开敏感内容、移除仍在使用的新本地保护、删除未受管文件或覆盖用户新工作，计划 blocked，不为“回到原样”绕过安全。

recovery_receipt.payload 固定包含 plan_id、manifest_id、输入证据绑定、每个逆向步骤的累计结果／实际前后态、共享资源唯一结果、已完成和未完成 step_ids、失败原因、开始／结束时间及恢复前保护副本引用。正常成功或可处理失败均原子保存新收据；重试保留此前已完成步骤及原保护副本引用，合入本次结果，不能仅保存增量。previous_receipt_id 初次为null、重试为输入收据ID，旧收据不改；单份最新收据足以继续该plan。多资源恢复不是事务，部分失败明确显示。

apply 重试可显式提供 --recovery-receipt：先验证同 plan 的记录，针对每个资源只核对最后一个已执行逆向步骤的后态，跳过已完成 step_ids，再按顺序继续未完成项；不能同时拿已经被覆盖的中间后态作当前状态。全部目标匹配才 restored，完整成功记录及后态未变才 already-complete。若进程突然退出、收据未保存，或无法证明某项写入属于该计划，则保留备份并 blocked，交由人工对账，不引入写前日志／锁机制来承诺无证据恢复。

restored 仅证明受管文件对账完成；receipt 另含 `runtime_readiness=not-verified/verified/blocked` 和真实证据引用。缺旧 Trellis/GitNexus CLI、包或 host 时不能宣称旧流程可运行，不自动联网重装或启动服务。P2 的恢复演练另检查原工具／host 的可用性。恢复成功不删除备份，备份处置为第 11.8 节的人工授权操作规程，不新增 CLI action。

### 10.3 catalog 与旧 Skill 退役

- 15 bundled 减去两个 Trellis Skills，加一个 sbtd-task，目标 14；external 仍为19。
- **P0-07 为原子交付：** 将 `skill:trellis-workflow`、`skill:trellis-channel` 两条 catalog entries 删除，新增 `skill:sbtd-task`（source 为 `templates/skills/sbtd-task`），同时切换源目录、完整 Skill 资产、计数及断言。不得交付“只有新 SKILL、catalog 仍装旧 Skill”或 catalog 指向不存在目录的中间发布包。以隔离目录执行 catalog 驱动的 bundled 安装路径，确认实际目标含完整 sbtd-task 且新安装不产生两个旧目录；这是 P0 可独立验证的安装层断言，不等待 P1 全部 Graft/host 功能。P1 再验证完整 init/reset。
- `catalog.schema.json` 是结构契约，不因 entry 改动无意义升版；确需新增 metadata 才修改 schema 和最小示例。
- 旧 bundled 目录从有效源树删除；历史由 `v1.0.15` 及 Git history 保存，不在 Onboard 安装目录内部 archive 活的旧入口。
- 用户全局目录的两个旧 Skill 必须在新 canonical 校验后按身份／内容／symlink 安全策略退役。仅名字匹配不授权删除；unknown drift 保存并报告，需要用户裁决。
- 全局 AGENTS、Skill 目录路径优先级、Onboard rename migration、mattpocock migration、Ponytail provider conflict、caveman pin 维护和 i-have-adhd 安装边界继续有效。
- 本机可选根 `AGENTS.md` 不能作为新 clone 必需前提。新 sync 路由必须在受追踪 `ENTRYPOINT.md`／版本化说明中可恢复，不能只改本机忽略副本。

## 11. 存量项目安全迁移

### 11.1 授权与备份

不存在已授权的真实项目清单。本 PRD 定义迁移能力和流程，P2 执行前必须取得项目根、当前分支／完整 SHA、旧 Trellis 产物版本或实际结构、平台及有效 HOME、是否允许清理全局旧接线。

P2-01必须由用户冻结release scope：至少一个实际目标项目、Codex／OMP验证环境及共用HOME／Skill根的项目批次。共享入口的依赖项目须全部纳入切换批次或采用明确隔离的HOME／Skill根；未选Claude／Kimi等平台只盘点，不修改，依赖未解决前禁止全局卸载。未经授权的必需步骤保持blocked。P2-04始终只走带迁移上下文的init/init-projects，不把sync/live automation是否存在变成另一种部署分支。

部署顺序固定：P2-02 在授权项目的隔离副本及隔离 HOME／Skill 根演练，不改 live；P2-03 在确认的维护窗口为整个共享批次迁移数据并停用旧路由；P2-04 才发布对应新全局规则／Skills／接线，并对全部项目执行新流程 smoke。该批次切换完成前不恢复日常 Agent 工作。试点与隔离验证不构成两套工具同时运行真实任务的并行期。

sync/live automation只可作为批次外的独立授权动作，保留其既有Orca preflight和完整校验；需要时在生成本批次plan前完成，或在批次验收完成／明确终止且必要恢复验收后另行执行。本批次中不得用sync改写manifest管理资源，也不能把init成功虚报为已sync；外部变更使前态/后态失配时停止并重新核对。没有live automation不替换或缩减P2-04。P2-03覆盖全部授权原项目（含演练项目原件），单项目范围也有明确对象；批次后sync造成的新状态不由旧receipt自动恢复承诺覆盖。

Git tracked 内容、ignored/untracked 数据、工作区 journal、身份、HOME MCP/hooks、全局 Skill 和包版本分开盘点。**clean git status 与一个 tag 不能替代完整备份**；尤其当前模板默认并不保证 task.json、jsonl、workspace 被 Git 跟踪。

备份在仓库外私有目录，权限限制，记录类型、大小、checksum、原路径和恢复策略；敏感原件及其确定性指纹不得进入共享仓库、公共报告或公开日志。backup_root 必须专用且与受管目标不互相包含。所有共享迁移输出均受第 11.2 节统一隐私门控制；备份保留／销毁独立于旧目录 cleanup，见第 11.8 节。

可以由用户选择建立 Git 回退点，但不自动 tag、stash、commit 或执行 `reset --hard`。发现未提交工作时先保护并协商，而不是通过清空工作区获得“干净”。

P2-01 同时明确非敏感 custodian 标识、备份位置和第 11.8 节保留安排；不从 Git author／lessons 分隔名推断。migration plan 将 custodian 和最低保留要求记入已有 manifest，用户在 apply 前确认。后续责任人复核写在既有迁移报告中，不创建 lifecycle 配置文件或自动处置系统。

### 11.2 迁移映射

| 源 | 目标 | 保全／转换规则 |
|---|---|---|
| `.trellis/spec/**` | `docs/spec/**` | 先核对冲突与共享性，安全内容保留并改有效引用；敏感原件只私有保全 |
| `.trellis/lessons/**` | `docs/lessons/**` | 原始 marker/ID/正文在私有备份完整保存；共享投影必须通过隐私门，无法安全保留必要身份／引用时阻断该项 |
| `.trellis/spec/lessons.md` | canonical 短入口 | 与既有入口冲突先明确唯一位置，脱敏后不得留下含私有信息的索引或链接 |
| tasks 中 prd/design/implement 及附件 | `ai/tasks/<logical-id>/` | 字段、正文、文件名、链接、附件内容和元数据逐项审查，不因原先 tracked 就视为安全 |
| task.json | task.md + legacy-task.json + 私有原件 | 已知字段映射和未知字段快照都先经过同一隐私门；不能只过滤 legacy.original |
| 平铺或嵌套 parent/children | 显式逻辑关系 | 按实际 metadata 校验引用、循环、重名；不假定原目录层级 |
| 历史 archive | `ai/tasks/archive/YYYY-QN/` | 依据已证明完成时间；无法证明则 undated，记录来源 |
| `.trellis/.developer` | `.sbtd/developer` | 仅合法 name= 可直接迁；非法不改写，请用户指定 |
| jsonl context manifests | 私有迁移备份 | 不再作为运行时输入；先保留文件和其中独有上下文引用，不能靠 Git history 假定可恢复 |
| workspace journals | 私有完整备份 + 未完成任务 handoff | 摘要只是恢复入口，不替代原件保存 |
| workflow/config/scripts/agents/Channel 日志 | 分类：受管生成物／自定义内容／未知 | 自定义长期规则迁入规范；生成物最后清理；未知保留并阻断删除 |
| `.codex/**`、`.omp/**` 等平台产物 | 按 ownership manifest 清理旧 Trellis 条目 | 不删除整个 host 配置目录或非 Trellis extensions/hooks |
| `.gitnexus/`、外部索引、全局 MCP/hooks | 独立退役计划 | 不把单个项目迁移视为授权卸载所有其他项目仍使用的全局工具 |

#### 所有共享迁移输出的统一隐私门

此门覆盖任何从旧数据产生、将进入可追踪位置的内容：task.md 的已知字段和事件、PRD/design/implement、spec、lessons、索引、历史归档、附件、文件名、链接及共享迁移摘要；不只覆盖 legacy-task.json。不重写本次迁移范围外的业务文件或 Git 历史。源已被 tracked 不构成安全证明。

共享投影在经授权的 plan 前私有准备中完成，decision 与批准依据由 plan 校验并嵌入 manifest.payload.publication_decisions。apply 只读取、复验和应用这些已绑定候选，不在执行中首次生成待批准共享内容。自动扫描未命中不证明安全；必要交付／引用未决则 plan blocked，可选内容可 private-only，二进制没有可靠检查和明确批准时不共享。

share 才可原样投影；redact 只输出经确认的安全版本；private-only 的原件留私有备份，可选附件可在共享文档中写不含原名／路径／摘要指纹的安全说明。密钥、PII、生产数据或私有哈希不写入占位内容。必要 ID、marker、目标链接或任务含义无法安全表达时，停止该项目并请用户决定安全替代方案，不能靠占位假装完整迁移通过，也不擅自更改他人的历史原件。

apply 在任何共享写入前验证其候选都有批准的 decision 且 checksum 一致；verify 再核对实际产物与批准投影一致、必需信息和链接仍满足验收。任何漏审、候选变动或未决 blocked 都不允许清理原件。私有恢复／验收证据本身也要按受众处理：原始内容／路径／哈希只在私有区域，公开报告仅给脱敏结果，不能把扫描命中的敏感值打印到日志中。

“无损保全”指私有原件可核验恢复，并非强迫把敏感原文公开；常规 lesson 写入不改他人块的规则不授权迁移器公开敏感历史。验收须覆盖已知 description/evidence 字段、Markdown 正文、附件内容与文件名、spec/lessons/索引、已 tracked 源以及无法检查的二进制，不只测 legacy.original。

#### task.json 未知字段的无损保全载体

每个迁移任务使用固定的 `ai/tasks/<logical-id>/legacy-task.json` 作为可追踪的历史 sidecar；归档时随任务目录携带。它不是新状态源：只读保留旧内容，普通 task 状态、mode 或重开操作不更新它，不执行其中的命令／路径。

| 字段 | schema 与用途 |
|---|---|
| `schema_version` | 整数 1 |
| `source_path` | 旧 task.json 的安全项目相对路径；路径本身敏感时为 null，精确位置仅在私有 manifest |
| `source_sha256` | `64 位小写十六进制字符串 / null`。仅原件和路径全部确认可共享、parse_status=valid 且 redacted_paths 为空时可公开原始 bytes SHA-256；任何脱敏、整体私有化、路径保密或安全性不明时必须为 null，原始 checksum 仅私有保存 |
| `original` | 旧 JSON 完整对象的共享安全快照，包含已知和未知字段，保留 JSON 类型、数组顺序和嵌套；不与新 task.md frontmatter 合并 |
| `redacted_paths` | 被隐私过滤的 JSON Pointer 列表，对应 original 中置 null 的位置；字段名／指针本身敏感或整体不可安全公开时，original 为 null、列表为 `[""]`，公开副本不泄露原键名 |
| `parse_status` | `valid / invalid`；重复键、无法无损解析或损坏 JSON 为 invalid，original 为 null，不猜测修复 |

原始 bytes **无论是否脱敏都完整保存到私有备份**，由私有 manifest 记录恢复路径、权限和原始 checksum。共享快照不泄露敏感值还不够：公开私有原件的确定性摘要会允许对可预测／低熵内容进行候选验证，所以 source_sha256 的可见性必须服从上表，不能用原件裸哈希替代脱敏。

不新增 HMAC、密钥管理或随机引用系统。私有 manifest 用本来就有的项目根、任务逻辑 ID 和 sidecar 目标路径关联原件及其 checksum；这些私有映射和包含私有内容的 manifest/receipt 摘要不复制到 tracked sidecar、公共日志或发布报告。脱敏后的共享内容可独立阅读，但不能声称仅靠该文件验证或还原私有原件。

旧字段仍只属于 original，不覆盖当前任务。source_sha256 为 null 时，幂等／原件一致判断必须通过已有私有映射核对原始 checksum 和共享快照；两个 null 或两个相同的脱敏快照都不证明原件相同。私有映射缺失、目标冲突或来源不明时保留目标并人工对账，不覆盖、不伪报 already-complete。invalid 原件不丢弃，其任务不标成正常迁移通过。

清理旧源前，在私有环境验证原件 bytes checksum 和恢复可用性；无脱敏且完全可共享时核对所有键／值／类型／数组顺序，有脱敏时核对仅指定位置被置 null、其余不变。测试包括敏感值和敏感路径、低熵原件、public hash 必须为 null、私有 checksum 仍能核验、不同私有原件得到同样共享快照时不能误判幂等，以及私有映射缺失、损坏输入和目标冲突。不得在测试日志中打印真实私有原件或裸摘要。

### 11.3 状态转换规则

旧值先与项目实际 task.json／对应版本语义核对，再映射 `pending→planned`、`in-progress→in-progress`、`checking/review→checking`、`done/completed→done`。`archived` 不天然证明任务成功，须结合原状态及产物；不能确定则 blocked 并保存原值。

不明状态、空对象、损坏 JSON、未知 schema、缺父任务、多执行对象均进入冲突清单；不能隐去失败。旧任务没有可证明的 default/lite/strict 选择时 `workflow_mode: null`、`mode_source: migration-unknown`，恢复时询问，不因来源是 Trellis 就自动填 strict，也不默认降成 default。身份、任务状态和完成时间缺失分别报告，不用当前操作者或迁移日期补造。

### 11.4 执行顺序

1. 先只读盘点项目和拟迁移范围；经用户明确授权，仅在仓库外私有位置准备共享候选和逐项 publication_decisions，不写项目/HOME、不清理旧数据。私有准备可与迁移范围确认一并授权，但不等于批准 apply；准备副本即纳入责任人保留／处置范围，放弃迁移也不能遗漏它们。
2. 运行只读 migration plan 校验源、已批准候选、身份、ignore、共享依赖及目标前态，生成绑定的 manifest。用户确认该计划后才以 --yes 执行 apply；在此之前不写项目 ignore 或应用数据，也不把“候选还不存在”推迟到 apply 后处理。
3. 所有写入前验证 manifest、批次范围及已绑定的候选checksum、批准、数量、父子关系、legacy保全和links。初次核对源／目标前态；重试显式传入--apply-receipt，验证累计已完成后态、未完成前态。源已被本次合法操作改写时，以收据当前后态及原始备份证明候选来源，不拿旧checksum比较已改写文件；未改写源仍核对当前checksum。未知状态／候选或批准变化先停止，不能在保护写入后才发现前置校验失败。
4. 仅对待执行项备份原件与ignore并核验，再添加新保护、保留旧规则；成功项和原始备份不重复写入。每次资源操作前仍复验预期状态，随后由第5步统一应用未完成候选；不生成新publication裁决或扩大范围，必要变化须重新准备／plan／确认。
5. 仍在该次 apply 内，将合格且未完成的候选应用为新数据并停用受管旧路由；已成功项不重放，旧数据保留待最终清理。原子保存一份包含既有及本次结果的累计批次 apply_receipt，项目私有结果及共享结果各自唯一。**apply 不部署新规则／Skills／MCP/hooks，不执行新流程 smoke。** 全批次 applied 后才由 P2-04 独立部署；部分失败保留源、备份和累计证据，不进入部署或清理。
6. P2-04 独立部署和新流程 smoke 完成后，运行 migration verify 绑定实际验收与清理候选；再向用户展示旧目录、生成物、接线和 ignore 清单，**再次确认清理**并取得对应 verification_id。初始迁移同意或普通 --yes 不代替这次确认。
7. 用户确认后可在同一次迁移、同一会话立即执行清理，不需要等下一次会话；但不是“新 ignore 四行写好了就删旧规则”。未确认、有未知文件或迁移失败时，保留旧目录及保护规则。全局 CLI 卸载仍需核对其他项目依赖。
8. 清理后再检查新共享资产可追踪、本地资产被忽略、用户自定义配置完整，输出脱敏逐项目报告并更新台账；不自动 commit/push。

唯一执行归属：P2-03／migration apply 只迁移数据和停旧路由；P2-04 独立部署新接线并运行 smoke；P2-05／migration verify＋cleanup 负责验收绑定、第二次确认、清理和复验。批次所有项目准备完成前不进入 P2-04，同一职责不得在 apply 和部署阶段重复执行。多项目不构成原子事务，失败项目不标完成，也不自动回滚其他成功项目。

### 11.5 回滚与幂等

- 回滚只针对本次拥有的写入；比较预期迁移后内容再恢复，若用户已改动则冲突停下，保存新旧两份供合并。
- 不用 `graft uninstall` 代替迁移恢复。它不是 npm 卸载，也可能保留不可解析配置，不能还原 Trellis 任务和 HOME 原始状态。
- 先执行 uninstall dry-run；应用需要明确授权，避免移除其他项目共享的全局 Graft 接线。
- 二次迁移若源／目标与 manifest 相符应 no-op 或续作，不重复创建 task、index 行、marker 或 MCP key；若内容变化须重新计划。
- 恢复使用第 10.2.3 节的 manifest-scoped plan／receipt；部分 apply/deploy/cleanup 的已证明写入按顺序恢复，缺证据则阻断而非猜测。恢复或争议未解决时保留唯一备份；正常成功后的保留／销毁按第 11.8 节人工规程，cleanup 不处理备份。

### 11.6 老项目身份迁移的精确条件

这是老项目内的显式数据迁移，不是重新执行 trellis init，也不根据用户记忆判断是否“初始化过”。满足以下全部条件才从 `.trellis/.developer` 自动沿用原名：

1. 用户授权迁移该项目；普通 check、模式路由、读 lesson、全局安装不触发迁移。
2. 源为项目内正常可读文件，相关父路径无逃逸／symlink 异常，包含唯一明确的合法 `name=`。
3. 名字满足 `^[a-z0-9]+$`，原样使用，不能自动小写化／去标点。
4. 当前 `.sbtd/developer` 确实缺失，不是同名目录、损坏链接或其他冲突；`.sbtd` 父路径也安全。
5. 仅当前 worktree 的新身份确实缺失且本地路径安全时，检查主 checkout；其新身份合法则只读沿用，不迁移本地旧身份。当前新身份已存在时，按下表同名、异名或异常分支处理，不能越过本地文件去用主 checkout 覆盖它。

| 旧身份 | 新身份／环境 | 处理 |
|---|---|---|
| 合法 | 新文件缺失且无主 checkout 新身份 | 授权后原名写入，校验一致 |
| 合法 | 新文件同名且合法 | 已完成，幂等不重复写 |
| 合法 | 新文件不同名且合法 | 冲突，请用户决定，不覆盖 |
| 不合法 | 新文件缺失 | 请用户提供合规名字，不改写旧名 |
| 不存在 | 新文件合法 | 使用新身份 |
| 两边不存在 | 无主 checkout 身份 | 按第 8.3 节在初始化或首次写 lesson 时询问 |
| 任一相关路径异常 | 文件类型、内容或 containment 不明 | 暂停该身份写入／迁移，保留原件，不绕过检查 |

新身份写入成功只证明身份迁移这一项，不立即删除旧文件。旧 `.trellis/.developer` 随完整备份、数据迁移、验收及再次确认清理处理。历史 lesson 的名字、ID 和其他人的 block 均不追溯改名。

### 11.7 新旧 .gitignore 的最终处理清单

**项目模板与配置源仓库根是两份独立契约，禁止整份互相覆盖。** 新模板删除旧工具段；已有项目必须保留旧保护直到迁移验证和清理确认完成。

#### 保留项目模板中的通用规则

| 分类 | 保留的现有规则 |
|---|---|
| 临时文件 | `.tmp/`、`.cache/`、`*.log`、`*.tmp`、`.DS_Store`、`Thumbs.db` |
| 依赖／构建／环境 | `node_modules/`、`dist/`、`build/`、`.next/`、`out/`、`.env`、`.env.local`、`.env.*.local` |
| Python | `__pycache__/`、`*.pyc`、`.venv/`、`venv/`、`.pytest_cache/`、`.ruff_cache/`、`.mypy_cache/`、`.ty_cache/` |
| Claude | `.claude/projects/`、`.claude/worktrees/`、`.claude/settings.local.json` |
| Codex | `.codex/cache/`、`.codex/tmp/`、`.codex/logs/`、`.codex/sessions/`、`.codex/state/`、`.codex/hooks/*.local.*` |
| OMP | `.omp/plugins/` |
| Impeccable | `.impeccable/live/server.json`、`.impeccable/live/sessions/`、`.impeccable/live/annotations/`、`.impeccable/critique/` |
| 浏览器／runner 临时目录 | `.chrome-devtools-mcp/`、`.playwright-mcp/`、`playwright-report/`、`test-results/`、`blob-report/`、`/output/` |
| 报告／修复产物 | `tests/e2e/manifest/ui-test-repair-plan.json`、`tests/api/reports/`、`tests/unit/reports/`、`tests/e2e/reports/` |
| 截图／视频／trace | `tests/e2e/**/screenshots/`、`tests/e2e/**/videos/`、`tests/e2e/**/traces/`、`tests/e2e/**/*.trace.zip` |
| Maestro | `.maestro/cache/`、`.maestro/tmp/`、`.maestro/runs/`、`.maestro/reports/` |
| 其他 | `.worktrees/`、`/AGENTS.md.*` 备份文件 |

保留旧 Agent 本地缓存规则不代表自动接入那些平台；也不借本次迁移清理与需求无关的通用规则。

#### 从 v2 新模板删除的旧工具规则

```gitignore
.trellis/*
!.trellis/agents/
!.trellis/agents/**
!.trellis/spec/
!.trellis/spec/**
!.trellis/lessons/
!.trellis/lessons/**
!.trellis/workflow.md
!.trellis/tasks/
!.trellis/tasks/*/
!.trellis/tasks/*/prd.md
!.trellis/tasks/*/design.md
!.trellis/tasks/*/implement.md
.gitnexus/
```

同时删除这两段的失效标题／说明及注释示例 `# !.trellis/tasks/**`。旧项目不是按上述字符串全局盲删，只处理有模板来源／用户授权证明的旧段；未知用户自定义规则保留并报告。

#### 项目模板新增四条

```gitignore
# SBTD local state
/.sbtd
/docs/handoffs

# Graft local artifacts
/graft
/.graft
```

开头 `/` 限定根路径，避免误伤 packages/graft；末尾不带 `/` 使同名目录／文件／symlink 路径都被忽略，仍不代表允许异常路径被安装器使用。整个 `.sbtd` 已覆盖身份、书签和 default 记录，不再重复添加逐文件规则。若保留路径已是用户业务目录，先报告冲突，不直接忽略业务文件。

共享资产不加入忽略：项目 AGENTS.md、ai/tasks（含子任务和 archive）、docs/spec、docs/lessons、CONTEXT／ADR、features、maestro/flow，以及 manifest 中的 ui-test-manifest／ui-selector-audit／ui-test-coverage。已有 broad `ai/`、`docs/`、`tests/` 规则造成冲突时指出来源、请用户确认收窄，不堆大量失效 `!` 或撤销用户全部规则。

#### 老项目迁移时序及幂等

只安装／升级全局工作流不改老项目 ignore；普通 init/reset 不承担旧规则清理。显式迁移中先追加新保护、保留旧规则，再迁移和验证；旧目录完成授权清理或安全迁出、用户确认旧规则清单后才删除旧段。临时同时保留两套 ignore 不等于双工具并行运行。

当前 `onboard.py:2511-2533` 仅按缺失行追加，不会删除旧规则，不能把“换模板再 init”当迁移成功。v2 迁移需有受管段识别、定向删除、原件备份和重复执行证明。Graft 自维护可能再追加 `graft/`：只对已证明受管的条目归一化，并复验范围，不误删用户规则。ignore 不会自动取消 tracked 状态，发现本地敏感产物已被追踪时单独报告并取得处理授权。

#### 640-skills 根目录七行契约

```gitignore
.DS_Store
/.sbtd
/docs/handoffs
/graft
/.graft
__pycache__/
AGENTS.md
```

此七行替代先前拟定的 Graft 五行目标，因为源仓库也需要保护 default 本地状态及交接。不把业务项目模板全份写到根。根 AGENTS.md 保持 ignored/local-only，业务项目 AGENTS.md 可追踪，ENTRYPOINT 和本 PRD 可追踪。P0-09 同步精确测试及当前有效维护说明，历史 lessons 不重写；删除旧两目录 ignore 前同样先处置残留。本轮不实际修改该文件。

### 11.8 私有备份保留与人工授权销毁

这是责任人的操作规程，不新增处置 CLI、lifecycle 文件、journal、锁、定时服务或证据索引。migration cleanup、Graft uninstall、任务 done 和恢复成功均不删除备份。manifest 记录 custodian、明确的私有 backup_root、受管备份清单及最低保留要求；责任人保管原件、候选、阶段收据和已登记副本，不自动上传云端。

正常发布路径的最低保留门：覆盖 P3 两周观察，并至少保留至正式发布后 14 天，取两者较晚结束时间；项目可明确延长。该政策不是开发工期。责任人在 P2-01 同意这些条件；更严格隐私／法律要求与保留门冲突时，先停止实际迁移并确定替代保全方案，不暗中缩短可回滚窗口。明确放弃迁移／取消发布适用下述独立分支，延期本身不算取消。

责任人每次复核在既有私有准备记录或迁移报告中记录非敏感标识、复核时间、下次日期、保留／待销毁结论与原因，首次及后续间隔不超过30天。观察完成和发布时刻引用真实记录，未知不视为窗口结束；发布延迟须明确续留及下次日期。逾期不授权删除，也不阻断无关普通任务。不新增后台提醒器；在P2/P3检查点及责任人复核时核对。

P3-04 有两个条件分支，均须无未解决迁移／恢复问题、无使用备份的操作、无审计保留要求，并另取销毁授权：正常发布分支须 P3-03 已完成且上述保留窗口结束；明确放弃迁移／取消发布分支不依赖 P3-03 或不存在的发布日期，须记录用户终止决定、完成并验收必要恢复、由责任人明确关闭剩余回滚需求。plan 前仅准备候选后放弃时，须核实未写项目／HOME，才可记录不需要恢复；事实不明先停止处置。两分支都可关闭同一个 P3-04，不把未发生的发布任务伪填 done。P3-03 发布前只验证备份完整及责任／后续复核安排有效，不依赖 P3-04。

**pre-manifest责任与授权前置：** 即使P2-01尚未完成、manifest尚不存在，进入终止分支时，也必须在删除范围之外的既有私有准备记录或迁移报告中，按下述步骤保存非敏感custodian标识、候选归属、精确处置范围、本次独立销毁授权及实际确认时间，并回读成功后才可删除；不能从当前操作者、Git author或lessons分隔名推定责任人。任一项缺失（包括确认时间）或删除前保存/回读失败，P3-04保持blocked、零删除、不得done。记录齐全仍须满足必要恢复验收、回滚需求关闭及其余条件；只补齐既有记录，不要求完成无关P2-01事项，不新增格式、身份系统或处置服务。

单独销毁步骤固定如下，生产者是 custodian 或其本次明确授权的 Agent，使用现有受控文件操作工具，不是新增迁移子系统：

1. 只读核对 manifest、阶段／恢复收据、实际备份和登记副本，列出精确路径、类型、所有权及将失去的恢复能力。尚无 manifest 时，以私有 publication-decisions 候选清单和准备授权／迁移报告为盘点输入，只处理能证明归属的准备产物；清单缺失或不完整先人工核实，不凭目录名称猜测。原始值和 checksum 仅在私有核对，不进入公共报告。未知文件、symlink 逃逸或当前被其他操作使用时停止。
2. 选定删除范围之外的既有私有准备记录或迁移报告作为本次授权和结果的同一记录位置，先验证私有性、可写性及可沿用原格式安全补记；不要求pre-manifest阶段已有迁移报告，也不向封闭schema的publication-decisions对象任意加字段。展示精确清单及不可逆后果，取得责任人**本次独立明确确认**，不复用迁移/cleanup/restore旧同意。将custodian、候选归属、精确处置范围、本次授权及实际确认时间先保存，并回读核对写入成功，才进入第3步；记录缺失、不可写或保存核对失败均blocked、零删除、不得done。
3. 在同一受控操作窗口逐项复核未变后删除，仅处理清单中对象。未声明内容或变化导致停止，不能扩大成任意目录递归清空。原始数据、候选以及含敏感路径／摘要的受管证据副本均需列入；不能只删原件而把敏感副本无限保留。
4. 检查清单内目标已不存在，在第2步同一记录中追加实际删除／失败／剩余结果，不等删除之后才首次记录授权。完成后按隐私边界整理为不含原始数据、私有指纹或敏感定位信息的简短审计说明，保留批准/完成时间、安全范围、真实结果及回滚能力终止事实；未解决的剩余路径仅私有保留并继续复核，不公开。
5. 中断或失败时保留真实结果，不能假成功；重试重新核对剩余清单并再次确认，不把后来重建的同名文件当成旧备份删除。没有剩余对象时只报告核对结果，不再执行删除。

销毁结束后明确 `recovery_available=false`；原件校验、同源判断或回滚需要已销毁证据时报告 unavailable，不以 null 或目录缺失代替证明。工具仅证明授权对象的逻辑删除，不承诺 SSD 安全擦除、系统快照或未声明第三方副本清除；这些外部副本及相应隐私风险由责任人另行处理并说明。

## 12. 按模式应用的工程能力与共同证据边界

| 契约 | 保持要求 |
|---|---|
| SDD／BDD／TDD／DDD | strict 保留完整适用次序和 no-new-uncovered-behavior；default/lite 按任务风险及明确交付使用方法，不默认每次创建全部产物；项目原有强制规范仍有效；本源仓库不新增 `.feature` |
| 五类 Book Review | strict 按 objective trigger、Plan/reviewer 状态和修正回路强制执行；default/lite 不机械加载全套 Gate，缺 Skill 以可用方法分析，不冒充已调用或通过 |
| Legacy／Refactoring seam | 实际使用该安全方法时保留 safety-seam-only 顺序；不要用形式缺失阻断无关 default/lite 工作，也不能删真实数据安全措施 |
| Ponytail／可读性 | 保留简洁、可维护和针对性验证；strict 执行完整 smoke→review→裁决顺序，其他模式避免为了输出审核表而重复劳动 |
| Web | DevTools 做诊断，Playwright CLI 做回归，MCP 探索不冒充 CI |
| Mobile | Java 17+，Maestro CLI 是执行器，MCP 是辅助；平台范围／artifact／环境明确 |
| 报告 | branch_slug + 时间戳命名；正式快照不留在 runner current；HTML／XML 与同 stem 中文 MD 配对 |
| API | 每条覆盖描述映射 method + URI，记录 case、期望和 contract，不能仅写业务名 |
| Evidence | repo key、原始 ref、完整 SHA、worktree state、source、trigger、environment、publication；dirty local 不证明 PR head |
| Knowledge | 只读 ingest 不改源，Revision Set 固定，Evidence Decision／manifest／checksum／attestation 不降级 |
| Mock | 基于 contract／fixture／用户授权；不冒充 full-stack |
| rtk | 报告型命令优先 native 或已证明 report-safe；不能以缓存输出证明本轮产物 |
| 外部 Skill | 19 required stable mirror 原样保留；不 fork，不因替换工具自动升级 |
| 隐私 | 真实账号、密钥、PII、生产数据不进入规则、测试、日志、截图、图报告 |

三模式改变的是调用时机、强制程度和产物厚度，不改变真实测试／工具的语义。实际进入正式验证或声明发布就绪时，仍须满足相应报告、证据和隐私契约；default/lite 不必对所有不相关工具输出全表，但不能将未验证写成通过。bundled 全局／项目规则、工作流及 reviewer 的强制触发范围须一起按模式更新；不能只改 router 而让旧常驻句子继续把 default/lite 变成 strict。external stable Skill 不手工改写，SBTD 调用边界负责按需使用。

## 13. 文件改造与文档同步清单

| 范围 | 计划动作 | 说明 |
|---|---|---|
| `sbtd-workflow-onboard/templates/skills/sbtd-task/` | 单一任务 Skill，按三模式分层 | 公共恢复／lite 入口轻量，strict 清单按需加载，不造三个重复 Skill |
| `templates/skills/trellis-workflow/`、`trellis-channel/` | 退役删除有效目录 | 历史 Git 保存，迁移器只接受旧输入 |
| `templates/agents/AGENTS.global.md` | 短模式路由、Graft、恢复／grill、共同安全边界 | 默认不全量加载或输出 Gate，用户推荐确认不能省略 |
| `templates/agents/AGENTS.project.md` | 三模式入口、项目路径和最小 fallback | 全局已装但项目未 onboard 仍可执行，身份只按需建立 |
| `templates/skills/lessons-record/` | 新身份、首次写入询问、迁移及模式边界 | marker／ID／ownership 保持，不让缺名字冻结 default/lite 无关工作 |
| 其余所有 bundled Skills | 有效旧路由与模式触发逐文件裁决 | 包括 book-*、project-validation、BDD、knowledge、Maestro、SEO；外部镜像保持原样 |
| `catalog.json`／`catalog.schema.json`／`examples/` | entries、校验与示例同步 | 15→14 bundled，19 external 保持 |
| `scripts/onboard.py` | check／plan／setup／身份／迁移／最小状态能力 | 复用既有安全文件操作，支持本地记录提升、ignore 定向迁移，不重建调度器 |
| `install.sh`／`install.ps1` | 参数、菜单、Graft 安装与 host adapter | Bash 3.2、EOF、空数组及 PowerShell 运行验证 |
| `templates/project/.gitignore` | 保留通用段、删除旧工具段、新增四条根锚定规则 | default 本地记录被忽略；共享任务／spec／lessons 可追踪；老项目按授权阶段迁移 |
| 根 `.gitignore` | P0-09 独立切换七行契约与精确断言 | 见第 11.7 节；保护 .sbtd/handoff/Graft，保留根 AGENTS.md local-only |
| `ENTRYPOINT.md` | 新工具监控、主线、source/sync 入口 | 新 Graft 版本仅在采用时写入；不执行本轮 update |
| `README.md`／`README.html` | 新主线、迁移／兼容边界和命令 | 实现同轮同步，不能提前声称 v2 已可用 |
| `prompts/automations/sbtd-workflow-tools-version-check.md` | 移除有效 Trellis/GitNexus 监控规则，纳入 Graft | 普通修改只动版本化源；live 仍只在 sync |
| `CHANGELOG.md` | 实施时新增顶部 `v2.0.0（未发布）` | 本轮仅 PRD，不改已发布历史 |
| `tests/**` | 行为、迁移、两平台、报告与旧路由回归 | 不仅把字符串断言改名 |
| `.github/workflows/` | 新增本仓库必要 CI | 只验证可机器证明事项，权限最小，无真实 HOME／secrets |

第 11.7 节是新旧 ignore 的唯一完整规则清单；P0-08 负责业务项目模板，P0-09 负责配置源仓库七行契约，P1-12 负责老项目定向迁移，不能互相替代。相关测试、有效维护说明和 Git 正反探针必须同步，不改历史 lesson，不提前创建图或本机运行态。

**残留策略：** 当前有效入口／模板／普通执行路径不得依赖 Trellis/GitNexus。允许旧词的范围必须明确列出：本 PRD 与既有历史文档、已发布 CHANGELOG／archive、原样 external mirror、迁移器和旧输入 fixture。不能用“全仓零匹配”删除历史；也不能把真实遗留运行调用藏进允许清单。

初期 PRD 阶段仅修订本文并记录 P0-01 隔离 spike，当时 README.md、README.html、版本化 automation prompt、ENTRYPOINT 与 CHANGELOG 未因 v2 规划改变。实施阶段逐任务评估并同步实际受影响入口，不提前声称尚未实现的能力；live automation 仍仅在显式 workflow sync 中发布。授权与执行协议调整记录在 [实施调整记录](sbtd-workflow-v2-implementation-decisions.md)。

## 14. 优先级实施台账

### 14.1 台账维护协议

这是本次改造的**唯一总进度表**。会话 todo、子任务文件、报告只能提供证据，不代替更新本表。

- 状态枚举：`planned / in-progress / checking / done / blocked`。各行记录实际状态，未验收且未确认任务 PR 合并前不预填 done。
- `完成时间` 为实际验收通过且台账同步时的带时区 ISO 8601；未完成使用 `—`，不是预计日期。
- 每完成一个任务，先核对其验收及依赖，再**同一轮立即**更新状态、完成时间、证据／备注，不等整个 phase 结束。状态变 checking 不是完成。
- 单行部分完成时保持 in-progress/checking；只有确实可独立交付才拆新稳定 ID，并更新依赖。P2 项目清单确认后逐项目拆行，父项汇总不能冒充每项目证据。
- blocked 填写具体缺失项和解除条件；恢复时清楚记录。重开 done 时清空当前完成时间，并在第 18 节保留旧完成事件。
- 每轮启动先读本文及当前任务；检查其他参与者是否更新过相同行。不要凭旧会话状态覆写；同一职责只允许一个更新者。
- AFK 表示满足 gate 后 Agent 可自主完成；HITL 表示授权／验收／发布必须有人确认，不表示该任务所有代码都由人手写。
- P0 为实施前置，P1 为仓库交付，P2 为授权环境切换，P3 为观察与发布；优先级不是工期估计。
- 保留既有任务 ID 和历史完成时间，新增任务使用新 ID；同优先级按依赖执行，不按 ID 数值先后强行排序。本文台账维护是用户明确交付，不能因实施中选择 default/lite 而省略，也不复制为所有业务项目的通用必填 PRD。
- 依赖栏只列无条件前置；P3-04 的正常发布／终止分支由验收栏及第 11.8 节裁决。依赖栏无条目不代表可直接销毁，必须记录所选分支的完整证据和单独授权。
- 本次逐任务开发按用户要求从最新 main 建任务分支。循环独立 review 无新发现且已收到 advisor 全部处理后才合并；确认 MERGED 后同步 main、清理已合并分支，并立即通过窄范围文档 PR 更新本表的完成状态、实际时间及合并证据。状态 PR 完成前不解锁下一项依赖；具体顺序见实施调整记录 D-IMP-02。

**AC 引用分层：** P0 模板／协议任务只证明对应契约、模板或 case 设计，不提前宣称 P1 运行 AC 全部通过。例外：P0-01 必须做上游真实能力 spike；P0-02 取得既有行为基线；P0-07 必须实际执行隔离的 catalog/bundled 安装断言；P0-09 必须运行根 ignore 契约及 Git 探针。其余新行为运行证明归属 P1 对应实现任务，P1-15 汇总 P1 范围 AC。真实项目由 P2-04 产生部署／smoke 子项证据，P2-05 完成逐项目迁移集成验收；不会要求前置任务先证明后续阶段尚未产生的结果。

P1 同样区分接口基础与行为完成：P1-01 仅交付参数解析、字段/schema 和统一 envelope 的聚焦契约检查，不拥有可执行恢复或 AC-35 的完成证明；P1-20 是恢复行为实现及 AC-35 的唯一交付所有者，P1-14/15 负责集成复验。P1-01 完成不代表 recovery 已可对用户发布，完整发行仍须全部前置实现与验证就绪。

P1-04/05/12/13 分别验收各自阶段的真实操作及前后态／备份证据，不提前宣称跨阶段恢复完成；AC-18/33 中的完整恢复子项由依赖这些生产者的 P1-20 验收，再交 P1-14/15 集成复验。

P0/P1 开工统一以 R-09 done 为前置；本轮修复期间不沿旧 R-06 状态启动实施。台账根依赖随当前审核更新，R-09 重开时暂停尚未开始的实施；不把历史评审完成当当前契约已收敛。

**P0 安全失败分支：** 未选平台写入、project-only 写 HOME、禁用标志无法持续生效等任一项实测失败，阻断对应模式及依赖任务。只能修改接线设计或候选版本后复验；日常图不可用的 advisory 降级不能用来豁免安装／接线安全。

### 14.2 本轮评审任务

| ID | 优先级 | 任务／交付 | 依赖 | 验收与证据 | 类型 | 状态 | 完成时间 |
|---|---|---|---|---|---|---|---|
| R-01 | P0 | 核验 v1.0.15 与工作树基线 | — | 第 3 节；tag/HEAD/diff/clean 及文件计量结果 | AFK | done | 2026-09-16T16:50:55+08:00 |
| R-02 | P0 | 审核仓库耦合及 Graft 上游能力 | R-01 | 第 4、9、19 节；源码而非单独 README 推断 | AFK | done | 2026-09-16T16:50:55+08:00 |
| R-03 | P0 | 版本建议、领域／迁移审核和联网裁决 | R-02 | 第 1、2、6 节；用户选择允许版本元数据 | HITL | done | 2026-09-16T16:50:55+08:00 |
| R-04 | P0 | 交付并校验详细 PRD 与台账 | R-03 | 第 16.4 节结构检查与读者复核通过；第 18.3 节记录收口 | AFK | done | 2026-09-16T17:06:42+08:00 |
| R-05 | P0 | 评估并补齐 catalog／接线顺序／测试隔离／根 ignore concern | R-04 | 第 20 节；该轮修订及结构检查通过，后续模式决策由 R-06 归并 | AFK | done | 2026-09-16T17:19:19+08:00 |
| R-06 | P0 | 全会话最终决策归并与无遗漏校验 | R-05 | 第 21 节 37 项决策覆盖、结构与独立读者复核、隔离 Git ignore 探针通过；见第 16.4 节 | AFK | done | 2026-09-16T20:16:09+08:00 |
| R-07 | P0 | 复核并修复六项 review 与批次 concern | R-06 | 第 22 节；六项修复、结构与接口形状校验、定点文档复核通过；仅 PRD 修复 | AFK | done | 2026-09-16T20:48:53+08:00 |
| R-08 | P0 | 修复复审的 blocked／共享资源／摘要隐私缺口 | R-07 | 第 22.1 节；三项修复、结构／依赖检查及定点文档复核通过，仅 PRD 修改 | AFK | done | 2026-09-16T21:35:11+08:00 |
| R-09 | P0 | 修复恢复／隐私／保留缺口并循环 review 至收敛 | R-08 | §22.2；重开后第11轮全文review零新发现，确认时间/记录载体/验收分层及advisor问题闭合；48任务/37AC/35修复映射检查通过，旧完成与重开事件保留 | AFK | done | 2026-09-17T08:20:32+08:00 |

### 14.3 P0：能力验证与核心契约

| ID | 优先级 | 任务／主要文件 | 依赖 | 验收／完成证据 | 类型 | 状态 | 完成时间 |
|---|---|---|---|---|---|---|---|
| P0-01 | P0 | Graft 精确候选 capability spike；隔离 HOME 和最小 Git fixtures | R-09 | 第 9.8 节。spike 实测完成。AC-09 收口：禁止对含未选子仓的父目录调 Graft，P1 只对显式仓根调用。AC-10 已证离线 build/ask 与无 LLM `--name` 降级；版本探针 fail-closed 改挂 P1-03。§9.3 剩余升级／cache／stamp／reconciliation 改挂 **P1-04**。报告：`tests/api/reports/api-report-sbtd-graft-install-p0-01-graft-capability-spike-2026_09_17-10_14_26.json` 与同 stem `.md`／`.logs/`（local-only） | AFK | done | 2026-09-17T10:33:14+08:00 |
| P0-02 | P0 | 既有行为基线与按模式保留契约清单 | R-09 | AC-02/14/23 基线／契约子项；[保留清单](sbtd-workflow-v2-behavior-baseline.md)。最终提交 `41a43f3…` 原生267 tests/65.741s、隔离CLI smoke及分型报告校验通过；P002FinalReview零发现。[PR #9](https://github.com/KunoLu/640-skills/pull/9) 已合入，merge `50a7e873cfa3224b8c02419b4cb146d5ed88fa6d`；不宣称v2运行AC通过 | AFK | done | 2026-09-17T13:44:48+08:00 |
| P0-03 | P0 | 本地／共享 task schema、mode、引用、父子与历史事件 | P0-02、P0-10 | AC-03/24/28/31；唯一事实源、分支冲突、重开完成事件保全及模式恢复契约 | AFK | planned | — |
| P0-04 | P0 | sbtd-task 公共／lite 入口与 strict references 分层 | P0-03 | AC-02/04/20/23；同一 Skill 按模式加载，不默认创建全任务包或执行 strict 清单 | AFK | planned | — |
| P0-05 | P0 | AGENTS 公共路由、恢复、grill 与轻量 fallback | P0-01、P0-04 | AC-04/05/22/23；任何新需求先评估，推荐必须暂停确认，拒绝后不反复劝升 | AFK | planned | — |
| P0-06 | P0 | lessons-record 新身份来源、首次询问与模式边界 | P0-03 | AC-06/25；ID/marker 不变，无 onboard 项目按需只建身份，缺名不冻结 default/lite 无关工作 | AFK | planned | — |
| P0-07 | P0 | 原子切换 catalog entries、源目录和 bundled 安装断言 | P0-04、P0-06 | AC-11；两旧 entry 换 sbtd-task；隔离真实安装目标正确，14 bundled／19 external | AFK | planned | — |
| P0-08 | P0 | 项目 ignore 的保留／删除／四条新增规则 | P0-03、P0-06 | AC-12/26；default 本地忽略、共享资产可追踪，规则根锚定且不误伤业务子目录 | AFK | planned | — |
| P0-09 | P0 | 源仓库根七行 ignore、维护说明与精确测试 | R-09 | AC-12/16；保护 .sbtd/handoff/Graft，旧残留安全处理，不复制项目模板 | AFK | planned | — |
| P0-10 | P0 | 三模式路由／强制程度／显式交付覆盖契约 | P0-02 | AC-22/23 契约子项；[路由与24项场景](sbtd-workflow-v2-mode-routing-contract.md) 覆盖来源、双向建议、拒绝保持、续作、grill次序及安全边界；P1运行证明另行验收，待独立review／PR合并 | AFK | checking | — |

### 14.4 P1：安装器、迁移能力与仓库交付

| ID | 优先级 | 任务／主要文件 | 依赖 | 验收／完成证据 | 类型 | 状态 | 完成时间 |
|---|---|---|---|---|---|---|---|
| P1-01 | P1 | onboard参数、交换schema与统一envelope基础契约 | P0-07 | AC-13/29接口子项，含批准快照、私有操作、init迁移上下文和deploymentEvidence；只证明解析/校验基础，行为归对应任务 | AFK | planned | — |
| P1-02 | P1 | 按需脚手架、最小状态校验与 bootstrap 边界 | P1-01、P0-08 | AC-03/12/13/23；不 onboard 也可开展普通任务；reset 保留数据；bootstrap 不强制每项目生成 | AFK | planned | — |
| P1-03 | P1 | Graft CLI 检测／确认安装／遥测与版本约束 | P0-01、P1-01 | AC-07/10/13；只读无副作用，安装前 DNT，失败不报成功。**独占** AC-10 剩余：真实断网下 `graft version`／npm 元数据不可达且不循环安装，不得用仍能查出 latest 的 sandbox 冒充 | AFK | planned | — |
| P1-04 | P1 | Codex接线、显式opt-in hooks及部署证据生产 | P1-02、P1-03、P1-12、P0-05 | AC-08/18/29/33/35的部署及恢复输入子项；共享去重、默认无hooks、模板后接线；隔离真实执行init上下文及累计证据续作/保存。**独占** §9.3 剩余：版本变化后 reconciliation 仍保持 `--no-global/--no-hooks/--no-mcp`；图 cache 丢失、旧 stamp 缺字段、升级路径。未证明前不得在 project-only/check 启动自维护 | AFK | planned | — |
| P1-05 | P1 | OMP接线、CLI分析及部署证据生产 | P1-02、P1-03、P1-12、P0-05 | AC-08/18/29/33/35的部署及恢复输入子项；继承资源去重、无Codex hooks；隔离握手/query及init上下文累计证据生产。遵守 P1-04 对 Graft 自维护路径的禁令，不另起一套升级／cache／stamp 测试 | AFK | planned | — |
| P1-06 | P1 | 多项目／worktree 隔离；禁止父目录 Graft 入口 | P1-02、P1-04、P1-05 | AC-09/13；只对显式仓根调用；未选 sibling 零写入；多仓理解=逐仓调用后只读汇总，证明未对父目录 init/build/MCP | AFK | planned | — |
| P1-07 | P1 | Bash installer 及迁移／recovery 转发 | P1-01、P1-03、P1-06、P1-20 | AC-13/29/35；只转发统一接口，独立确认，不实现另一套恢复或处置逻辑 | AFK | planned | — |
| P1-08 | P1 | PowerShell installer 及迁移／recovery 对等转发 | P1-01、P1-03、P1-06、P1-20 | AC-13/29/35；Windows 真执行与统一输入／结果，不绕过资源授权 | AFK | planned | — |
| P1-09 | P1 | 全部 bundled 旧路由清理与强制触发按模式裁决 | P0-05、P0-06、P1-01 | AC-02/14/16/23；不只改 router；Book/BDD 按模式，Knowledge/evidence 和 external mirror 保持 | AFK | planned | — |
| P1-10 | P1 | ENTRYPOINT 监控与可恢复 sync source | P0-01、P0-07、P1-01 | AC-15/16；Graft pin/源明确，update 不变成迁移或 live sync | AFK | planned | — |
| P1-11 | P1 | README.md/html、Onboard docs、prompt、CHANGELOG 同步 | P1-07、P1-08、P1-09、P1-10、P1-12、P1-13、P1-17、P1-18、P1-19、P1-20 | AC-15/37；记录恢复能力及证据不足边界，备份保留／人工销毁规程，不提前声称发布 | AFK | planned | — |
| P1-12 | P1 | 批次私有/共享资源、隐私门、迁移及verify消费 | P1-02、P1-19、P0-06、P0-08 | AC-17/18/25/26/29/30/33/34/35/36相应子项；批准快照/闭集校验，verify拒绝错误部署ID/scope/status/report；累计receipt原子保存，无journal/锁 | AFK | planned | — |
| P1-13 | P1 | 受管旧资源退役及cleanup证据消费 | P1-04、P1-05、P1-12 | AC-11/18/29/33/35清理及恢复输入子项；cleanup核对部署ID/scope/报告/资源完整链，共享清理一次，保留前后态及备份；完整恢复归P1-20 | AFK | planned | — |
| P1-14 | P1 | 模式／安装／迁移／恢复回归与CI | P0-09、P1-07、P1-08、P1-09、P1-12、P1-13、P1-17、P1-18、P1-19、P1-20 | AC-18/19/22/23/24/25/26/27/28/29/30/31/32/33/34/35/36及AC-37实现期子项；真实producer→verify→cleanup→recovery链及partial续作/缺证据拒绝；AC-37仅保护/阻断与隔离规程演练，不等待真实发布窗口或销毁 | AFK | planned | — |
| P1-15 | P1 | Codex/OMP 三模式 smoke、token 计量及最终验证 | P1-11、P1-14 | AC-04/14/19/20/22/23/24；六个 host×mode 组合含模式拒绝／恢复，真实证据不伪造 | AFK | planned | — |
| P1-16 | P1 | 候选 release-readiness 与可选 rc 发布 | P1-15 | reviewer ready；用户批准后才创建不可变 rc tag，记录 SHA/日期 | HITL | planned | — |
| P1-17 | P1 | 最小任务、active 引用、提升与恢复事件 | P1-02、P0-03 | AC-03/24/27/31/32；blocked 前态跨会话可恢复，重复阻塞不丢原态，未知历史需用户选择；单文件原子更新 | AFK | planned | — |
| P1-18 | P1 | 公共路由、跨分支恢复和只读交接 | P0-05、P1-17 | AC-05/22/24/27/28；分支不符不写，切换／重绑定须选择；只读不建 handoff、旧模式不丢 | AFK | planned | — |
| P1-19 | P1 | developer 按需建立与 worktree 身份解析 | P1-02、P0-06 | AC-06/25；未 onboard 的首次保护与名字询问、本地身份优先、合法/冲突分支、窄写入不全量初始化 | AFK | planned | — |
| P1-20 | P1 | Manifest-scoped recovery plan／receipt 与恢复执行 | P1-12、P1-04、P1-05、P1-13 | AC-18/35；基于实际各阶段实现证明完整/partial apply/deploy/cleanup恢复与重试，最后后态、共享闭包、无证据blocked | AFK | planned | — |

P1-12在生产者之前用冻结schema的合法／非法fixture证明消费者边界，不宣称真实部署通过；P1-04/05分别产生真实host证据，P1-13验证实际cleanup消费，P1-20验证恢复，最终P1-14才验收完整链。P1-12拥有共用序列化／累计保存实现；host适配器贡献资源结果，由现有init编排统一调用，不各写一份同批次文件。

AC-37分层验收：P1-11交付规程文档；P1-14只证明cleanup不删备份，以及custodian、候选归属、精确范围、本次独立授权、实际确认时间逐项缺失或删除前记录保存/回读失败时均blocked、零删除、不得done，并进行隔离规程演练，不用模拟授权或日期冒充真实处置。P2-01/P2-05确认实际责任与保留安排，P3-01记录真实观察；实际保留窗口或终止分支事实、独立授权及销毁结果归P3-04。P1不依赖P3-04完成，不新增处置程序来替代人工规程。

### 14.5 P2：授权环境切换

| ID | 优先级 | 任务／交付 | 依赖 | 验收／完成证据 | 类型 | 状态 | 完成时间 |
|---|---|---|---|---|---|---|---|
| P2-01 | P2 | 冻结迁移范围、备份责任及保留安排 | P1-16 | AC-37；确认custodian/备份清单/复核安排与拟清理范围；迁移授权不代替cleanup或备份销毁确认 | HITL | planned | — |
| P2-02 | P2 | 隔离副本迁移及可调用恢复演练 | P2-01 | AC-17/18/35/36；有证据的部分apply/deploy/cleanup分别恢复；验证文件后另测旧工具可用，缺证据安全拒绝 | HITL | planned | — |
| P2-03 | P2 | 运行 migration apply：数据迁移和旧路由停用 | P2-02 | AC-17/18/29/30；全批次 applied receipt、legacy 校验；不部署新接线、不 smoke，失败不进入 P2-04 | HITL | planned | — |
| P2-04 | P2 | 独立部署新规则／Skills／接线并逐项目smoke | P2-03、P1-11、P1-13 | AC-08/15/18/29部署子项及AC-21的host query/smoke子项；通过init迁移上下文唯一部署，显式前次输入和新证据输出，失败不清理；不混入独立sync | HITL | planned | — |
| P2-05 | P2 | migration verify、再次确认、cleanup及逐项目集成验收 | P2-04 | AC-18/21/26/29/37；完整数据/链接/恢复证据，授权清理后复验、脱敏逐项目报告及用户验收；不删备份，记录保留安排 | HITL | planned | — |

### 14.6 P3：观察与正式发布

| ID | 优先级 | 任务／交付 | 依赖 | 验收／完成证据 | 类型 | 状态 | 完成时间 |
|---|---|---|---|---|---|---|---|
| P3-01 | P3 | 两周观察内 3–5 个真实任务与备份复核 | P2-05 | AC-20/21/22/24/37；覆盖两host三模式；备份保持完整，有问题继续保留，记录真实观察完成时间 | HITL | planned | — |
| P3-02 | P3 | 修正观察问题并复跑验证 | P3-01 | 修复与恢复问题关闭，原备份继续保护，不将观察完成当销毁许可 | AFK | planned | — |
| P3-03 | P3 | 最终 readiness、用户确认与 v2.0.0 发布 | P3-02 | required gates通过，恢复演练证据和备份后续安排有效；不依赖 P3-04 完成 | HITL | planned | — |
| P3-04 | P3 | 正常发布或明确终止后的备份人工复核与授权处置 | —（条件门见验收栏） | AC-37；正常需P3-03完成及保留门结束；终止需终止决定、必要恢复验收/回滚需求关闭；无P2-01/manifest仍须在既有私有准备记录或迁移报告保存custodian/归属/精确范围/本次独立授权/实际确认时间，缺任一项或删除前保存回读失败均blocked、零删除、不得done；两分支均重新授权，延期记录下次复核日 | HITL | planned | — |

以上 `planned` 表示未执行，不是自动授权。尤其 P2/P3 依赖实际环境、用户决定和真实观察，不以纸面设计完成来替代。

## 15. 可检验验收条件

| AC | 验收条件 | 最小证明方式 |
|---|---|---|
| AC-01 | 精确候选 Graft 能安装、运行且能力边界明确 | 隔离 HOME/项目真实包运行；记录 OS/arch/Node/package/integrity；错误原文与退出码 |
| AC-02 | 三模式保留各自适用的工程方法和 strict Gate | strict 完整阶段及失败阻断；default/lite 不全量加载；共同安全／用户明确交付不降级；fallback 可用 |
| AC-03 | 本地／共享任务状态可恢复且真实 | mode/schema/引用、父子和重开；blocked 以事件原态恢复，历史未知询问；完成时间/证据保留，索引不成为状态源 |
| AC-04 | Codex 与 OMP 的三模式执行均可用 | default/lite/strict 六个组合；需求澄清、实施验证、记录恢复及 strict Gate，mock 不替代 host 实测 |
| AC-05 | 主动 handoff 按真实事件触发并正确恢复 | 暂停/切会话/压力、取消 3/5；只读不落盘；分支一致时明确继续不重问，冲突按 AC-28 单独处理 |
| AC-06 | lessons 身份与历史资产保全 | 合法/非法/缺失、主 checkout 回退、首次写入询问；不猜名字；marker/ID 不变；全部 detail links 可达 |
| AC-07 | freshness 和 diff 不夸大 | 修改后 query、check 前后；busy/失败/disabled；same-size+mtime；untracked/deleted/rename/unsupported；basis 明确 |
| AC-08 | Host 接线顺序、幂等、默认无 hooks 与隔离正确 | 模板后接线、二次 init/reset 单 fence；默认不装 hooks，opt-in 真事件验证；隔离 HOME/Codex/OMP 根，预期外零写入 |
| AC-09 | 多仓和 worktree 不越界 | 两个选定仓与一个未选 sibling **零写入**；证明未对父目录做 `init`／`build`／MCP；工作树不同 branch；MCP root 对应**选定仓根** |
| AC-10 | 联网与完全离线策略均符合用户选择 | 受管入口 DNT、无 LLM/cloud/代码上传；允许 npm 元数据。P0-01 已证预装后离线 build/ask。**版本不可达／不循环安装**由 P1-03 用真实断网证明 |
| AC-11 | 可安装 catalog 与全局 Skill cutover 正确 | P0 原子替换两旧 entry 为 sbtd-task；隔离 catalog 安装实际得到完整新 Skill；14 bundled／19 external；完整 init/reset，旧身份冲突保留 |
| AC-12 | 项目四条新增与源仓库七行 ignore 各自正确 | 保留通用段；根精确断言独立于模板；真实 Git 正反探针、broad ignore 冲突、packages/graft 不误伤、重复构建不变宽 |
| AC-13 | CLI/JSON/两安装器一致 | Python 命令真实运行；单 JSON；非零错误；Bash3.2/EOF/PTY；Windows PowerShell；project-only 不装全局工具 |
| AC-14 | 验证语义不变且强制触发正确分层 | strict Book/BDD/Ponytail 序列保留，default/lite 不被旧全局句子强制；external/caveman/i-have-adhd/Evidence v2/Knowledge 回归 |
| AC-15 | 文档与发布／sync／update 边界一致 | README.md/html、ENTRYPOINT、prompt、CHANGELOG、Onboard docs 对照；live 只在显式 sync |
| AC-16 | 零旧运行依赖且历史保留 | 按 source/fixture/history/vendor 分类的扫描报告；允许清单外零旧调用／路由 |
| AC-17 | 迁移数据完整、无越权 | tracked/ignored/untracked、自定义内容、平铺父子、undated；legacy-task.json 与私有原件按 AC-30 完整核对，不只测已知字段 |
| AC-18 | 幂等、批次失败与可执行恢复 | 共享资源只恢复一次；partial receipt 重试及最后资源后态；有证据时 recovery 可执行，无证据/用户修改则blocked；旧运行时可用性单独验证 |
| AC-19 | 本仓库 validation 与 CI 可复现 | unit 全量、语法／结构检查、受控 integration、fresh clone、CI clean SHA、正式 raw+同 stem MD |
| AC-20 | 三模式 token 收益可复算，不缩减交付或安全 | 公共核心约 2k、轻入口 ≤3k 为测量目标；分模式／host 统计完整加载和质量，不将文档字数或旧 −60% 假设冒充实测 |
| AC-21 | 授权项目真正迁移成功 | 每项目报告、全部数据／链接、host query、新流程、恢复验证和用户验收；不存在抽样代替全数据校验 |
| AC-22 | 所有需求初始路由且用户最终选择优先 | 新任务缺省 default、显式选择／续作继承；三模式双向推荐先暂停；拒绝保持且不重复；新实质风险才重评 |
| AC-23 | default/lite 真正非强流程，同时保留必要确认 | default 按需、lite 固定短清单、strict 完整适用 Gate；缺 Skill/工具/索引不冻结无关安全任务；显式产物和安全/真实性不被省略 |
| AC-24 | 模式持久化、恢复和提升无双重事实源 | 只读例外优先；普通 default 本地、显式提升可共享；新选择立即生效、保存失败不回退；跨分支不自动重绑定，旧 handoff 不覆盖 |
| AC-25 | 身份建立与迁移条件精确且不越权 | 未 onboard 首次保护和名字询问，只建必要身份；本地新身份优先，确实缺失才查主 checkout；旧合法/新缺失可授权迁，同名幂等、异名或异常停该迁移 |
| AC-26 | 老项目 ignore 迁移需两次确认且时序正确 | 全局升级不改项目；确认迁移后先新保护保留旧段；搬迁验收后再次确认清理；可同会话继续，失败/未确认不删，tracked 内容不擅自取消追踪 |
| AC-27 | 显式只读高于三模式持久化 | 各模式的 review/调查零写入 task/active/handoff/developer/ignore；不运行有缓存/接线副作用的查询；仅会话模式，不谎称可恢复 |
| AC-28 | 跨分支恢复须独立裁决 | 普通分支不符、detached SHA 不符、缺历史 SHA/非 Git 绑定；选择正确 worktree/明确重绑定/只读查看；不自动 stash/checkout/改 branch；同分支正常新提交不过度阻断 |
| AC-29 | 四阶段迁移及独立部署I/O可验证 | plan前私有候选/批准快照，apply只备份/保护/应用；init迁移上下文显式接收manifest/apply/previous并返回已保存证据；三端一致，cleanup绑定完整链及再次确认，过期拒绝 |
| AC-30 | 旧元数据保全与所有共享投影安全 | 原件私有完整保全；已知字段和legacy.original均经过publication decision；公开敏感hash为null；同样脱敏快照不假幂等 |
| AC-31 | 完成、阻塞、重开及归档事件持久 | task 事件 at/from/to/reason/evidence；blocked/unblocked 和旧完成均保留；原子更新、祖先顺序、重复转换不重复事件、归档携带、历史未知不伪造 |
| AC-32 | blocked 前态可跨会话准确恢复 | planned/in-progress/checking 各自阻塞后恢复原态；持续阻塞不覆盖；模式切换不改原态；旧事件缺失/冲突需用户指定、不直接 done；只读不写 |
| AC-33 | 共享 HOME 操作具有批次级唯一性 | 两项目/两 host 共享同文件，只一资源备份/写入；不同条目合并，冲突先拒绝；依赖集合齐全；第二消费者重试不重复操作，跨阶段衔接，回滚不撤销未授权消费者配置 |
| AC-34 | 脱敏不会泄露私有原件摘要 | 部分/全部脱敏、敏感路径、invalid/安全性不明时 public hash 为 null；低熵合成原件哈希不进入共享物或公共日志；私有仍可核验，不引入 HMAC/密钥系统 |
| AC-35 | Manifest-scoped 恢复入口及收据闭合 | plan只读、独立确认、apply原子receipt；完整/部分apply、deploy、cleanup逆向及重试；共享闭包、保护先行；无receipt/后态不明拒绝，不引journal/锁/索引 |
| AC-36 | 全部可追踪迁移产物通过隐私门 | 已知description/evidence、正文、附件及文件名、spec/lessons/索引、已tracked源、不可检查二进制；必要项未决blocked，可选private-only；候选/实际checksum与decision一致 |
| AC-37 | 备份保留和人工销毁分层验收 | 实现期：cleanup不删备份；无P2-01/manifest时custodian、候选归属、精确范围、本次独立授权、实际确认时间先保存并回读，逐项缺失或删除前保存/回读失败均blocked/零删除/不得done；载体为删除范围外的既有私有准备记录或迁移报告。实际处置：正常观察+发布后14天门及≤30天复核，或终止决定/恢复验收/回滚需求关闭；删除前授权、变化/中断重核、真实结果及外部副本风险；不建处置子系统 |

### 15.1 必须覆盖的负面场景

路径 `..`、绝对路径逃逸、symlink、同名用户文件、未知 task status、父子循环、非法 name、多个 active 叶子、残留旧 MCP、坏 TOML/JSON、只读 HOME、图缺失／锁竞争、相同 mtime 修改、untracked、新符号／删除符号、非支持语言、无网络安装失败、同根重复初始化、部分项目失败、未确认卸载、恢复目标被用户继续修改。

新增模式负面场景：用户拒绝推荐后仍被自动升级、把续作重置 default、把 caveman lite 当执行模式、恢复读旧 handoff 覆盖当前选择、默认生成 tracked tasks、共享后降模式自动删历史、指针越界／双副本、未 onboard 先强迫填用户名、3/5 次工具结果触发无意义交接、只写新 ignore 就删除旧数据。

这些负面场景分别保护数据、权限、错误与恢复契约。不要将永久测试写成单纯字段转发、mock 原样回声或模板措辞检查；配置仓库必要的路由契约检查必须按真实行为子句组织。

## 16. 验证策略、报告和发布门禁

### 16.1 实施前后验证

实施前读取 legacy/refactoring reviewer 并建立保留行为证明；迁移及核心状态逻辑采用 TDD。简单文档不强制 TDD，明确跳过理由。

沿用现有 unittest 组织；以下是实施时计划命令，不是本轮已执行记录：

```bash
python3 -m unittest discover -s tests -p 'test_onboard_multi_projects.py' -v
python3 -m unittest discover -s tests -p 'test_install_sh_agent_cli_flow.py' -v
python3 -m unittest discover -s tests -p 'test_workflow_contracts.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
bash -n install.sh
```

新增测试模块按实际职责加入既有 discover。macOS 必须用 `/bin/bash` 的 Bash 3.2 运行安装器的隔离交互 smoke，不仅用 `bash -n`；Windows 必须有真实 PowerShell 安装路径结果。Python/JSON/catalog/Markdown 结构校验使用项目既有方式；不为本次工作随意增加格式化依赖。

Graft 真实 smoke 与 installer fixture 分开：mock CLI 可以测 Onboard 错误分支和计划输出，不能证明上游 init、MCP、图刷新或网络行为。所有 P0/P1 安装、init/reset、query/MCP、升级接线及 uninstall 的真实包测试都使用临时项目与隔离 HOME；Codex 的 `CODEX_HOME`、OMP 的实际配置根，以及平台实际使用的 USERPROFILE/XDG 路径按解析结果指向隔离目录，不假定只设置一个 HOME 就足够。启动前检查解析后路径 containment，任一路径仍指向开发者真实配置即停止该测试。比较隔离目录运行前后快照，断言只产生预期文件、仅写选定 host；project-only 连隔离 HOME 都不得写。没有证明路径隔离之前不运行真实 init。dry-run 和 mock 补充覆盖计划输出，但不替代真实包副作用验证。P2 的真实环境部署则需要单独授权。

### 16.2 CI 实施要求

新增最小 GitHub Actions 工作流运行现有和新增聚焦／全量验证，包含 Linux/macOS/Windows 所需分工、pin 安装工具版本及 clean checkout。至少 `contents: read`，不默认上传含代码图／HOME 的 artifacts，不让来自不可信 PR 的代码取得 secrets。

CI 可以校验状态、路由、文件、报告和退出码；**CI 不能独自证明 LLM 实际阅读规范、独立审查真实发生或 handoff 自动触发**。这些必须保留受控 host 实测记录。

### 16.3 正式报告

实施中若 installer/Graft/migration 的集成运行作为正式证据，使用原生命令捕获 stdout、stderr、exit code、开始／结束时间、版本和场景列表，保存到 runner 不会覆盖的命名快照，并生成同 stem 中文 Markdown。可沿用 `tests/api/reports/` 的 integration 报告约定，suite_name 明确为 `sbtd-graft-install`／`sbtd-migration`；不是 HTTP API 的场景在 URI 矩阵注明 `not-needed（本地 CLI 集成，无 HTTP endpoint）`，不得虚构 URI。

unit 继承项目报告约定；Web／Mobile formal run 继续沿用既有 Playwright/Maestro report pair。失败报告也保存，不把 Final Test Report 和 Final Full Rerun 混用。

所有正式证据按 project-validation 记录来源、完整 SHA、worktree 状态、环境对齐和 publication。测试名、工具和 scope 必须与实际运行一致。

### 16.4 初期 PRD 与 P0-01 验证记录（历史）

本轮主体是审核并写 PRD，另已完成隔离 HOME 的 P0-01 Graft 0.18.0 capability spike（见 9.8）。已执行基线读取、差异核对、文件计量、npm metadata／pinned source／Context7 文档交叉检查；随后对本文执行结构、任务 ID、依赖、状态、时间和本地路径检查。

历史版本 2.2 为 45 项任务／34 条 AC。2.3 保留旧 ID 和完成时间，新增 R-09、P1-20、P3-04 及 AC-35～37。文档 2.6 快照为 48 项任务、37 条 AC；当时 R-01～R-09 与 P0-01 已完成，其余 38 项实施／发布后任务未执行。后续实际进度以 §14 为准，不把本历史快照当作实时统计。

文档 2.0 当时的结构检查与读者复核已通过，详见 R-06 历史记录；随后独立 reviewer 发现的六项契约缺口在本版修订。第 22 节记录本版验证范围，R-07 仅在修订和最终校验通过后标记完成，不能以此前通过的读者检查否定新发现。

PR #8 合并前，独立 reviewer `PrdLoopReview1` 对 `68557966f460a92fe5cb84431870f08732ad8691` 相对 `main` 的完整分支差异完成审查，结论为 `APPROVE`、`findings: []`。该结论只覆盖受审文档快照，不是 GitHub 平台 reviewer 批准、CI 或运行时验收，也不自动覆盖本版新增的追溯说明。合并及最近核对事实见第 1、18.3、19.1 节；38 项待实施状态不因审查或合并改变。

本轮在临时 Git 仓库验证 PRD 中的候选规则：项目模板 10 个应忽略／17 个应可追踪路径，源仓库七行规则 8 个应忽略／5 个应可追踪路径，均通过；真实项目模板及根 `.gitignore` 未修改。这是 ignore 语义证明，不是安装器／Graft／三模式运行验证。命令使用原生 `git check-ignore --no-index --stdin -z` 获取准确机器结果，不依赖 rtk 缓存。

未执行生产 unit 全量、真实 HOME／host 的 Graft 安装／MCP smoke、Codex/OMP 生产接线、Playwright 或 Maestro。隔离 spike 不能报告为 v2 运行时通过。`rtk: used` 用于基线 Git 命令；文档检查用 eval 原生执行，不依赖缓存或报告回放。

Web/Mobile、Knowledge Ingest、API Contract、E2E Mode、Evidence Publication 本轮均 `not-needed`。P0-01 已有 local-only 报告，不是 published／CI／host 证据。生产 CI/Graft 运行验证仍是 P1 待办。GitNexus 未参与本轮辅助分析；本地未见索引，本次采用直接源码与静态调用面审计，不声称 GitNexus 无依赖。

## 17. 轻量化目标、成本边界与观察方案

最终目标不是“同样长的流程换名字”，而是按模式减少不必要加载、产物和重复执行：default 按需完成；lite 固定短骨架；strict 保留完整适用步骤。减少的是文书、固定审批、重复读规则、无必要双角色和计数触发交接，不减少明确功能、必要调查、验证、数据保护及诚实交付。

原方案 40k–60k → 15k–20k、14.5k → 9.5k、−60% 属于未提供可复算依据的假设，不能对外保证。本轮只计量过 lines/bytes/characters，未发现可用目标 tokenizer，未为计量安装新依赖；原 10k 常驻／6k 入口目标由下面更轻的分层目标替代。

| 层级 | 最终目标与计量要求 |
|---|---|
| SBTD 公共常驻核心 | 约 2k tokens，保留模式路由／恢复、必要安全、真实性和精确指针；不把当前完整 PRD 放进常驻上下文 |
| sbtd-task 公共／lite 入口 | ≤3k tokens；strict 细节按需 references，不拆成多个重复核心 Skill |
| default 运行 | 不固定加载全工作流、所有 reviewer、完整历史或输出全工具状态；实际本地小记录的读写成本仍计入 |
| lite 运行 | 短清单与逐项验证；长期共享任务卡按需更新，不强制三件套和每次审批 |
| strict 运行 | 完整适用 Gate 与证据保持；共享规则只读所需部分，不承诺与 default 同样低成本 |
| Graft 与 hooks | 辅助工具按需查询；默认不装自动提示 hooks，opt-in 时输出及后台行为单独计量 |
| Skill 安装与加载 | 19 external 的安装可用性不等于逐任务加载；省 tokens 主要靠减少实际读取和重复执行，不机械删除工具数量 |
| 总成本／质量 | 同模型/tokenizer/任务条件记录 input/output/cache、工具描述、handoff、模式确认、延迟、漏依赖和回归结果；bytes÷4 不作精确 token 证据 |

这些是待实施测量的目标，不是当前已实现数字；公共预算只指 SBTD 可控内容，不包含 host 固定 system prompt 或用户业务上下文。不能把所有模式都将读取的内容搬入 references 后从总账扣掉，也不能为达标删除安全和明确验收。

P3 两周观察窗口内完成 3–5 个真实任务，样本整体覆盖 Codex/OMP、三模式、至少一个跨模块任务、一次跨会话恢复及高风险适用 Gate。P1 先完成六个 host×mode 受控验证；观察不是全面统计实验，披露样本限制。两周是观察窗口，不是工期估计。

不设旧新工具并行运行期；基线使用已保存 v1 日志或隔离同构任务。流程自愿化不能保证与 Trellis 的强制执行／持久协作完全等价；要保留的是主要工程效果，同时公开强制性下降与图能力缺口。收益不足时检查重复加载／无效产物，披露实测而非造百分比。

## 18. 风险、解除条件与变更日志

### 18.1 风险登记

| 风险 | 严重度 | 处理／发布条件 |
|---|---|---|
| Graft refresh fail-soft 被当作当前完整图 | 高 | AC-07 必须验证告警／覆盖限制；源码和测试补齐，不以退出 0 放行 |
| 全局 init 写错 HOME 或未选 host | 高 | AC-08/13 字节级副作用和真实 host 证明；未通过禁接线 |
| 删除 ignored task.json/journal 或自定义 runtime | 严重 | 完整备份、未知内容保留、AC-17/18；禁止仅 Git tag 回滚 |
| 本地／共享双副本或跨会话模式丢失 | 高 | AC-03/24；task 唯一模式源，书签／handoff 不覆盖；写入失败如实声明，提升中断可恢复 |
| 新身份非法或历史 LESSON-ID 断链 | 高 | 原样保留、完整 links 与 marker 校验；不抽样 |
| 图对 Markdown/Shell/PowerShell 未覆盖 | 高 | 文本检索、消费者检查、安装器测试，不以 Graft grep 为全仓证据 |
| 无意义 handoff 或重问模式抵消轻量收益 | 中 | 取消 3/5 计数触发，保存用户拒绝建议，事件触发去重，AC-05/22/24 与 P3 实测 |
| CI 被误写成“提示词门禁硬强制” | 高 | 机器校验和真实 host 证据分开报告 |
| Graft native 安装或 Windows 不兼容 | 高 | P0/P1 目标系统真实运行，缺环境明确 blocked，不静默缩小发布支持 |
| 移除旧全局工具影响尚未迁移项目 | 高 | 依赖项目盘点和单独卸载授权；没有双运行期也允许旧包暂存不执行 |
| token 收益不及预期 | 中 | 测量后披露，不用厂商 benchmark 冒充 SBTD 实测 |
| 原样 external Skill 内仍提旧工具 | 中 | 不改镜像；SBTD caller 边界覆盖并做有效路由测试 |
| default/lite 被旧强制句子重新变成 strict | 高 | AC-02/14/23；跨 global/project/bundled 一并按模式裁决，不只加一个选择器 |
| 仅全局升级就改老项目或过早删除旧 ignore | 严重 | AC-25/26；显式迁移、先新保护、备份搬迁验收、再次确认清理，失败保留旧保护 |

### 18.2 当前待验证／待授权项

1. P0-01 **done**（2026-09-17T10:33:14+08:00）。AC-09 产品收口已确认。AC-10 剩余「`graft version` 断网 fail-closed」改挂 **P1-03**。§9.3 剩余升级／cache／stamp／reconciliation 改挂 **P1-04**，均不阻断 P0-01。P1-06 必须证明未对父目录 init/build/MCP。Graft 无正向 `--hooks` flag；未授权必须传 `--no-hooks`。
2. P2-01 未提供目标项目清单、真实 HOME 和清理范围；不得猜测或遍历用户项目替代授权。
3. Windows、Codex/OMP host 环境及正式证据 runner 在对应任务开始前确认；不可用就记录 blocked。
4. 用户已授权本源仓库按任务分支实施、循环 review 和 PR 合并（可使用 --admin），以及合并后台账更新。P2 真实项目范围、本机 workflow sync、hooks opt-in、旧数据／全局工具清理、tag／发布、备份销毁仍按对应独立确认门执行，不能从总开发授权推断。

### 18.3 状态事件记录

| 时间 | 任务／事件 | 记录 |
|---|---|---|
| 2026-09-16T16:50:55+08:00 | R-01/R-02/R-03 | 基线、源码审计、major 建议及 DDD/DDIA 设计要求完成；联网边界获用户明确选择 |
| 2026-09-16T17:06:42+08:00 | R-04 | PRD 结构校验和最终读者复核通过；4 项评审 done，32 项实施 planned，未执行安装／迁移／sync／发布 |
| 2026-09-16T17:19:19+08:00 | R-05 | 四项 concern 补齐，新增 P0-09；共 38 项、21 条 AC，依赖及文档结构检查通过；轻量非阻断调整未写入 |
| 2026-09-16T17:39:20+08:00 | 用户确认／文档 1.2 | 四项 concern 结果接受；第 9.7 节及 AC-10 记录离线降级策略；两条路径和轻量化目标未批准、未改写 |
| 2026-09-16T19:58:08+08:00 | 最终决策归并开始 | 用户表示无其他问题并要求全量落地；三模式、default 本地记录、身份与两阶段清理均进入最终正文，R-06 校验后收口 |
| 2026-09-16T20:16:09+08:00 | R-06／文档 2.0 | 全会话最终决定落地；37 项决策、43 项任务、26 条 AC；结构、读者复核及临时 Git 探针通过；仅文档完成，37 项实施均 planned |
| 2026-09-16T20:36:07+08:00 | R-07 修订开始 | 复核后采纳六项发现；撤回对 L647 P1 的排除判断，明确 apply/部署/清理唯一归属，补齐其余数据与权限契约 |
| 2026-09-16T20:48:53+08:00 | R-07／文档 2.1 | 六项 review 契约修复完成；44 项任务、31 条 AC、37 项决策及 6 项修复映射有效；定点文档复核和临时 sidecar ignore 探针通过，未实现运行代码 |
| 2026-09-16T21:24:02+08:00 | R-08 修订开始 | 采纳复审三项问题，复用事件表保存 blocked 前态、共享资源批次去重、脱敏原件裸哈希仅私有保存 |
| 2026-09-16T21:35:11+08:00 | R-08／文档 2.2 | blocked 前态、共享批次资源、脱敏摘要隐私三项修复完成；45 项任务／34 条 AC／9 项修复映射校验及定点文档复核通过，未实现运行代码 |
| 2026-09-16T22:32:24+08:00 | R-09 循环开始 | 用户要求修复—review直到零新发现并处理advisor；本轮补恢复入口、全产物隐私门及备份人工保留／销毁 |
| 2026-09-17T00:23:44+08:00 | R-09／文档2.3完成 | 初始3项及循环新增17项发现已处理，第7轮完整review零新发现，advisor全部关闭；48任务/37AC/37决策/29修复映射校验通过，39项实施仍planned，仅修改PRD |
| 2026-09-17T07:51:40+08:00 | R-09重开 | pre-manifest责任/授权契约补强后，仅做定点检查不足以沿用旧零发现结论；接受advisor blocker，清空当前完成时间，等待当前正文完整复审，历史完成事件保留 |
| 2026-09-17T08:20:32+08:00 | R-09重新完成 | 重开后修复F-30～F-35，第11轮对新契约全文复审零发现；确认时间与载体一致、授权先落盘、AC-37分层通过，48任务/37AC/35修复映射校验通过；39项实施仍planned |
| 2026-09-17T10:14:26+08:00 | P0-01／文档 2.4 | 隔离 HOME 实测 `@nanonets/graft@0.18.0`。当时误标 done。父目录 init 联邦未选 sibling 为 unsupported／安全失败；无正向 hooks flag；npm 12 需显式 allow-scripts。不是 AC 全通过。 |
| 2026-09-17T10:30:55+08:00 | P0-01 done→blocked | AC-09 未通过不能标 done，否则会解锁 P0-05。完成时间清空为 `—`；10:14:26 事件保留为 spike 实测记录。 |
| 2026-09-17T10:33:14+08:00 | P0-01 blocked→done | 用户确认：禁止对含未选子仓的父目录调 Graft，P1 只对明确的单个仓库根调用。AC-09 以此收口；P1-06 仍须证明实现。 |
| 2026-09-17T10:41:11+08:00 | §9.5 收紧 | 联邦不得再用 `graft init <parent>`。多仓只允许逐仓独立调用后的只读汇总。 |
| 2026-09-17T10:56:03+08:00 | PR #8 review 修正 | AC-10 版本探针剩余改挂 P1-03。A12、§9.1、AC-09 删除父目录联邦入口，改为显式仓根＋禁止父目录 init/build/MCP。 |
| 2026-09-17T11:17:51+08:00 | PR #8 二次 review 修正 | §9.3 剩余接线安全改挂 P1-04。§1／§16.4 划出隔离 P0-01 spike；未执行实施／发布后任务改为 38。 |
| 2026-09-17T11:31:21+08:00 | PR #8 三次 review 修正 | 本文当前版本引用改为 2.5。§22.2 当前摘要改为 38 项剩余并划出隔离 spike；历史 2.4／39 项事件行不改。 |
| 2026-09-17T12:02:48+08:00 | PR #8 合入 main | 用户明确授权 admin 合并后，[PR #8](https://github.com/KunoLu/640-skills/pull/8) 已合并，merge commit 为 `5ad87208167d6cf1ef97444cb84d7cb5fde5f065`。仅合入 PRD／spike 结论，不代表 v2 实现、CI 或发布验收通过。 |
| 2026-09-17T12:13:17+08:00 | 文档 2.6／最近代码快照核对 | 区分初次审核与最近核对快照，补记 §16.4 的合并前文档审查结论。生产代码未变，台账仍为 48 项：10 done、38 planned；spike 证据仍为 local-only。 |
| 2026-09-17T13:21:00+08:00 | 进入实施／P0-02 checking | 用户授权逐任务分支、循环 review、PR 合并及合并后台账更新；边界见实施调整记录。P0-02 已从 main `34a1549…` 建分支，既有 267 项测试及真实只读 CLI smoke 通过，保留清单已形成；正式报告与 review／PR 收尾未完成，不预填 done。 |
| 2026-09-17T13:44:48+08:00 | P0-02 checking→done | 确认 PR #9 于 13:44:24+08:00 合并（`50a7e873cfa3224b8c02419b4cb146d5ed88fa6d`）后更新台账。P002FinalReview 已核对 `41a43f3…` 全部任务及精确HEAD报告；unit：`tests/unit/reports/unit-report-sbtd-baseline-p0-02-behavior-baseline-2026_09_17-13_31_16.json`；CLI：`tests/api/reports/api-report-sbtd-cli-smoke-p0-02-behavior-baseline-2026_09_17-13_31_16.json`，各有同stem中文摘要及v1 envelope，均local-only。仅完成P0-02，后续实现仍待办。 |
| 2026-09-17T13:53:31+08:00 | P0-10 checking | 从已同步 main `f8a7f3a…` 建任务分支；主PRD已消除本项歧义，未完整调用grill；DDD边界confirmed。三模式路由契约与MR-01～MR-24场景完成草案，待文档校验及独立review，不冒充P1运行验收。 |

后续仅追加有意义的状态事件：完成、阻断、重开、验收范围变化和用户授权。不把每条工具调用写成流水账。任务当前状态仍以第 14 节为准。

## 19. 证据索引

### 19.1 本地证据

- 快照身份：第 1 节分别记录产品代码基线 `bc8eec1549928fb0966254751b96b611b6334183`、初次审核 HEAD `3139be4f6b7476f84b2affbd3667bed003119f94` 与最近核对代码快照 `5ad87208167d6cf1ef97444cb84d7cb5fde5f065`；三者用途不同，不将历史审核 HEAD 当作实时 HEAD。最近核对使用 `git rev-parse HEAD`、`git status --short --branch`、`git diff --stat <代码基线> HEAD` 及源码／配置读取。
- Onboard 生产代码与测试：第 3 节精确路径；代码基线与最近核对快照中的这些文件相同。ENTRYPOINT 的 OMP 版本记录已由 `v18.2.0` 更新为 `v18.2.2`，另有 CHANGELOG 日期及归档变化；这些不构成 v2 生产集成。
- 本仓库维护边界：[ENTRYPOINT](../../ENTRYPOINT.md)、[README](../../README.md)、[项目 lessons 短入口](../lessons.md)、[安装及身份 lessons](../lessons/topics/repository-workflow.md)。
- P0-01 隔离 spike 正式快照：`tests/api/reports/api-report-sbtd-graft-install-p0-01-graft-capability-spike-2026_09_17-10_14_26.json`、同 stem 中文 `.md`、同 stem `.logs/`（38 个 case 的完整 stdout/stderr/exit）。local-only，未纳入版本库，也未改项目 `.gitignore`（P0-09）。不能证明 PR head。矩阵摘要以第 9.8 节为准。

### 19.2 Graft 官方证据

可变文档只用于发现；关键行为用 npm 0.18.0 与对应 gitHead 固定。npm repository 字段仍使用 `context-graph-engine` 名称，GitHub 对外入口为 NanoNets/Graft，二者不可未经核对当成不同实现。

- [npm 0.18.0 metadata](https://registry.npmjs.org/@nanonets/graft/0.18.0)：version、Node、依赖、gitHead、tarball integrity。
- [固定源码根](https://github.com/NanoNets/Graft/tree/de8456e892bad5aeee11403e47fb2227773eb27e)。
- [init CLI](https://github.com/NanoNets/Graft/blob/de8456e892bad5aeee11403e47fb2227773eb27e/src/cli.ts)：explicit agents 优先、check 不 refresh、版本与接线命令。
- [host registry](https://github.com/NanoNets/Graft/blob/de8456e892bad5aeee11403e47fb2227773eb27e/src/hosts/registry.ts)：host 集合，未有 OMP native host。
- [refresh](https://github.com/NanoNets/Graft/blob/de8456e892bad5aeee11403e47fb2227773eb27e/src/graph/refresh.ts)：失败／busy 可返回旧图、graphOnly、worktree seed。
- [fingerprint](https://github.com/NanoNets/Graft/blob/de8456e892bad5aeee11403e47fb2227773eb27e/src/graph/fingerprint.ts)：size/mtime 快路径与 hash 模式。
- [diff basis](https://github.com/NanoNets/Graft/blob/de8456e892bad5aeee11403e47fb2227773eb27e/src/blast/diff.ts)：working tree、clean fallback、三点基线、删除与重命名。
- [MCP tools](https://github.com/NanoNets/Graft/blob/de8456e892bad5aeee11403e47fb2227773eb27e/src/mcp/tools.ts)：六个主要工具、check 的不同语义。
- [upkeep](https://github.com/NanoNets/Graft/blob/de8456e892bad5aeee11403e47fb2227773eb27e/src/upkeep.ts)：npm 版本检查、wiring stamp 与自动 reconciliation。
- [版本探针](https://github.com/NanoNets/Graft/blob/de8456e892bad5aeee11403e47fb2227773eb27e/src/cli-meta.ts)：npm 查询默认 2 秒超时，失败返回不可达，离线不会据此伪造最新版本。
- [telemetry gate](https://github.com/NanoNets/Graft/blob/de8456e892bad5aeee11403e47fb2227773eb27e/src/telemetry/gate.ts)：DNT／CI／disabled 与版本检查不是同一个 gate。
- [uninstall/retract](https://github.com/NanoNets/Graft/blob/de8456e892bad5aeee11403e47fb2227773eb27e/src/hosts/retract.ts)：所有权清理与不可解析配置保留。
- [官方 README](https://github.com/NanoNets/Graft/blob/de8456e892bad5aeee11403e47fb2227773eb27e/README.md)：有“always Claude”等与 explicit 分支不一致的文字，不单独作为接线保证。
- Context7 `/nanonets/graft`：本轮用于交叉查询文档；其 main 缓存不替代 pinned source。

## 20. 五项 concern 的最终裁决

| Concern | 最终判断 | 正文／交付 |
|---|---|---|
| catalog 必须切换，否则新 Skill 不安装 | 成立；不是只新建 SKILL.md | 第 10.3 节、P0-07、AC-11：两旧 entries 原子替换为 sbtd-task，隔离真实安装断言 |
| 模板覆盖可能抹掉 Graft marker | 成立 | 第 9.3 节、P1-04/05、AC-08：每次先模板后接线，重复 init/reset 单 fence、保留规则 |
| 真实 init 可能污染开发者 HOME | 成立，不能只隔离项目目录 | 第 16.1 节、AC-08：HOME/CODEX_HOME/OMP/平台根 containment 与快照，mock/dry-run 不替代真实包 |
| 根 ignore 的精确五行绑定旧工具 | 成立，根与项目模板分别维护 | P0-09、AC-12：最终是第 11.7 节七行契约，增加 default 本地状态保护；旧五行目标已被替代 |
| default 全部写 tracked ai/tasks 会恢复默认产物成本 | 采纳 | 第 7.3 节、P1-17、AC-24：默认本地 .sbtd/tasks；lite/strict 或明确共享时提升，存储不绑定模式 |

历史阶段的“待确认”仅保留在第 18.3 节作为当时事件，不再是有效产品待决项。实际代码、模板和本机配置尚未改造；文档确认与运行时验收严格分开。

## 21. 全会话最终决策覆盖矩阵

以下按最终决定覆盖原方案、所有追问及 concern。正文是详细契约，矩阵用于核对没有遗漏；早期被替代建议不与最终规则并列生效。

| 决策 ID | 最终确认点 | 正文 | 实施任务 | 验收 |
|---|---|---|---|---|
| D-01 | v1.0.15 精确基线；推荐 major v2.0.0，不用 v1.1.0 | 1–3 | P1-10、P1-11、P3-03 | AC-15 |
| D-02 | 去 Trellis runtime／jsonl／Channel，不引入 OpenSpec 或替代调度器，不留旧 Skill alias | 4–5、7.7–7.8、10.3 | P0-04、P0-07、P1-09、P1-13 | AC-02、AC-11、AC-16 |
| D-03 | Graft 结构层接入，明确 freshness/diff/MCP/PDG 等不对等边界，禁止 deep/name/cloud | 3–4、9 | P0-01、P1-03 | AC-01、AC-07、AC-10 |
| D-04 | 允许安装及 npm 元数据；安装前及持续受管入口 DNT，禁止代码／查询／项目数据上传 | 9.2、9.6 | P1-03、P1-04、P1-05 | AC-08、AC-10 |
| D-05 | 完全离线用本地版本；版本不可达不阻断；缺图／依赖／MCP 可降级且不循环安装 | 9.7、9.8 | P1-03 | AC-10、AC-23 |
| D-06 | Codex active HOME／OMP 实际来源、GUI PATH、MCP 根绑定；不自动接线未选平台 | 9.3、10 | P1-04、P1-05、P1-06 | AC-08、AC-09、AC-13 |
| D-07 | OMP 不翻译 Codex hooks；自动提示 hooks 默认关闭，启用需独立 opt-in，原生 OMP 扩展不在范围 | 5.2、9.3、17 | P0-01、P1-04、P1-05 | AC-08、AC-20 |
| D-08 | default 按需、lite 短清单、strict 完整适用强流程，三者都使用 SBTD | 7.1、7.6、12 | P0-10、P0-04、P1-09 | AC-02、AC-04、AC-23 |
| D-09 | 任何新需求先做初始模式路由；纯问答路由不等于创建任务文件 | 7.2–7.3 | P0-05、P1-18 | AC-22、AC-24 |
| D-10 | 当前明确选择优先；同任务续作继承；新任务未指定才 default | 7.2、8.1 | P1-17、P1-18 | AC-22、AC-24 |
| D-11 | 任一模式发现其他模式更合适，先暂停、说明理由、询问，支持双向推荐 | 7.2 | P0-10、P1-18 | AC-22 |
| D-12 | 用户坚持原模式就执行；保存已拒绝建议，新实质风险才重新建议 | 7.2、7.4、8.1 | P1-17、P1-18 | AC-22、AC-24 |
| D-13 | 模式不缩减明确交付；default/lite 非必要缺失不冻结任务，安全／真实性只限制相关动作或声明 | 7.1、7.5–7.6、12 | P0-10、P1-09 | AC-14、AC-23 |
| D-14 | 先路由再按歧义判断 grill；清楚不重问；拒绝方法不等于允许猜需求；完整 grill 后独立 DDD | 8.2 | P0-05、P1-18 | AC-02、AC-04、AC-22 |
| D-15 | strict 不自行跳适用 Gate；不适用可标明；切换模式需确认，不能伪造历史通过 | 7.2、7.6、12 | P0-04、P1-09 | AC-02、AC-23 |
| D-16 | 公共约 2k、轻入口 ≤3k；少手续不减实际功能／必要验证；收益不承诺 −60% | 7.7、17 | P0-04、P1-15、P3-01 | AC-20 |
| D-17 | default 本地最小 task，不默认污染 Git；模式确定时保存，不等到 handoff | 7.3–7.4 | P1-17 | AC-03、AC-24 |
| D-18 | lite/strict 共享短／完整任务；default 可按明确需要提升，模式和存储独立，降模式不删共享历史 | 7.3 | P1-17 | AC-24 |
| D-19 | task 是模式事实源；active-task 只存书签；index 导航、handoff 快照；提升单写且可恢复 | 7.3–7.5、8.1 | P0-03、P1-17、P1-18 | AC-03、AC-24 |
| D-20 | 跨会话先读模式；旧 handoff 不覆盖；缺模式／多候选询问；明确继续不重问；本地不自动跨机 | 7.3、8.1 | P1-18 | AC-05、AC-24 |
| D-21 | handoff 保留主动但取消 3/5 次计数；真实事件触发、去重、退出控制，区别输出模式 | 8.1、17 | P0-05、P1-18 | AC-05、AC-22 |
| D-22 | spec 仅长期规则变化时维护；任务／模式／临时计划不混入 spec；lessons 短入口唯一 | 7.9、8.4 | P0-06、P1-09 | AC-06、AC-14、AC-23 |
| D-23 | 完整目录包含本地／共享任务、spec、lessons、handoff、条件测试/UI/图目录；全局 Skills/MCP 不复制进项目 | 7.9、10 | P1-02、P1-04、P1-05 | AC-12、AC-13、AC-23 |
| D-24 | 全局已装但项目未 onboard：首次需要写 lesson 主动问名字，仅建立身份，不做完整初始化 | 8.3 | P1-19 | AC-25 |
| D-25 | developer 在 .sbtd；当前／主 checkout／用户来源顺序；严格小写数字、不猜测、reset 不覆盖 | 8.3、11.6 | P0-06、P1-19 | AC-06、AC-25 |
| D-26 | 老合法名字仅显式迁移；目标缺失且无主身份才迁；同名幂等、异名冲突、异常停该操作；不立即删旧文件 | 11.6 | P1-12、P1-19 | AC-25 |
| D-27 | 历史lesson原件私有无损保留；共享投影先过隐私门；正常写入只改自己的块，ID查重和union边界保持 | 8.4、11.2 | P0-06、P1-12 | AC-06、AC-17、AC-36 |
| D-28 | 新模板保留通用规则、删旧工具段、加四条根锚定规则；源仓根独立七行，业务 AGENTS 可追踪 | 11.7 | P0-08、P0-09 | AC-12、AC-26 |
| D-29 | 全局升级不改老项目；ignore 先加新保护再搬迁，验收后再次确认清理，可同会话接着执行 | 10.1、11.4、11.7 | P1-12、P2-03、P2-04、P2-05 | AC-17、AC-18、AC-26 |
| D-30 | catalog 两旧换一新原子交付，14 bundled／19 external，真实安装断言与原样镜像边界 | 10.3、20 | P0-07 | AC-11 |
| D-31 | 每次模板写入后再接 Graft，二次 init/reset 单 fence，规则及其他配置保留 | 9.3、20 | P1-04、P1-05 | AC-08 |
| D-32 | 真实包测试必须隔离 HOME 和 host 根；dry-run/mock 只辅助，不能污染开发者配置 | 16.1、20 | P0-01、P1-14 | AC-08、AC-19 |
| D-33 | 完整数据盘点、私有备份、未知字段／journal 保留；Git tag 不代替备份、禁止 reset --hard 回滚 | 11 | P1-12、P2-02、P2-03 | AC-17、AC-18、AC-25 |
| D-34 | 安装／迁移／sync／update／发布分离，CLI/JSON/退出码同步，未选 host 与全局依赖不误删 | 9–11、13 | P1-01、P1-07、P1-08、P1-10、P1-13 | AC-08、AC-13、AC-15、AC-18 |
| D-35 | 保留真实测试／报告／Evidence/Knowledge/隐私语义；CI 不是模型必然遵循流程的证明 | 12、16 | P1-09、P1-14、P1-15 | AC-14、AC-19 |
| D-36 | 优先级表、依赖、AFK/HITL、状态、实际完成时间；每完成一项同轮更新；不把设计完成当实现完成 | 5.3、14–15 | R-06、P1-15、P3-03 | AC-03、AC-19、AC-21 |
| D-37 | 无双工具并行期；候选/迁移/观察/发布；有证据的恢复可调用，备份按正常保留门或明确终止分支独立确认处置 | 2、10.2.3、11.8、14、17 | P1-20、P2-02、P3-01、P3-03、P3-04 | AC-18、AC-20、AC-21、AC-35、AC-37 |

### 21.1 被最终决定替代的早期建议

- 双路径只是解释阶段的过渡说法，最终接口只有 default/lite/strict 三模式。
- default 不留任何记录会丢跨会话模式；default 一律 tracked task 又太重。最终选择本地最小记录，需要共享才提升。
- 所有任务同一套强制清单被三模式分层替代；strict 完整适用步骤保留，default/lite 不因非必要形式项卡住。
- 3/5 次计数 handoff 被事件触发替代；自动交接没有取消。输出压缩开关不是执行模式开关。
- 原 10k/6k 文本目标与 −60% 预测不作为最终保证；采用约 2k/≤3k 分层目标并实际计量。
- 根 ignore 最初 Graft 五行目标因 default 本地状态保护而扩展为七行；旧模板通用规则没有全部删除。
- 迁移初始同意不等于清理最终同意；添加新 ignore 后不能立即删除旧段，必须先完成搬迁验收并再次确认。

## 22. Review 发现与 concern 修复对照

文档 2.1 修复了下列六项问题，包括此前被排除但实际仍有歧义的 L647 批次部署职责。后续复审发现的三项缺口在第 22.1 节处理；各项均为 PRD 契约修订，不代表运行代码已实现。

| 发现 | 判断／修订 | 实施任务 | 验收 |
|---|---|---|---|
| F-01 P1：迁移 apply 与独立部署重叠 | apply 仅数据／保护／停旧路由；P2-04 独立部署与 smoke；P2-05 verify/确认/cleanup | P1-12、P2-03、P2-04、P2-05 | AC-18、AC-29 |
| F-02 P2：只读任务仍可能写状态 | 只读约束高于模式落盘，三模式均不写任务／handoff／ignore，不运行未验证无副作用查询 | P1-17、P1-18 | AC-27 |
| F-03 P2：未知元数据没有固定载体 | 固定 legacy-task.json 历史快照与私有原始 bytes；schema、隐私、冲突、checksum/round-trip 明确 | P1-12 | AC-17、AC-30 |
| F-04 P2：迁移和二次清理 API 未冻结 | migration --phase 四阶段、manifest/receipt ID、独立 cleanup 参数、过期拒绝及统一 JSON/退出码 | P1-01、P1-07、P1-08、P1-12 | AC-13、AC-29 |
| F-05 P2：重开会丢完成事件归属 | task.md 内固定 Markdown 状态事件表，完成／重开同文件更新；保留旧时间与证据，不建日志服务 | P0-03、P1-17 | AC-03、AC-31 |
| F-06 P2：分支不匹配没有处理结果 | 暂停写入，用户选择正确 worktree／明确重绑定／只读；普通续作确认不代替分支授权 | P1-18 | AC-05、AC-28 |

结构与契约校验覆盖本轮新增阶段、字段、任务依赖及 AC 映射；不运行生产迁移或写开发者 HOME。README.md、README.html、版本化 automation prompt 和 CHANGELOG 仍不变，因为本轮只修 PRD，没有实际产品能力发布。后续实现仍由对应任务同步这些入口。

文档 2.1 当时通过了 44 项任务、31 条 AC、37 项决策及 6 项修复映射的结构检查和定点复核，详见历史记录。该结果不覆盖后续发现的 blocked 前态、共享资源唯一归属或摘要隐私问题。

临时 Git 仓库探针确认新 `legacy-task.json` 在任务和归档路径均可追踪，`.sbtd` 本地任务仍被忽略；未修改实际 ignore 文件。未执行生产测试、迁移 CLI 或 Graft 运行验证，因为它们仍是待实现能力。上述通过只证明本版 PRD 的结构和契约一致性，不宣称旧数据已迁移或生产部署安全性已实测。

### 22.1 文档 2.2 的复审修复

| 发现 | 最小修复 | 实施任务 | 验收 |
|---|---|---|---|
| F-07 P2：blocked 没有恢复前态 | 进入／解除 blocked 纳入原事件表；持续阻塞不丢原态，未知旧前态由用户选择，不增加 blocked_from 副本 | P1-17 | AC-03、AC-31、AC-32 |
| F-08 P1：共享 HOME 操作按项目重复归属 | 资源／条目稳定 ID、批次 shared_operations/results、项目引用依赖集合；同文件合并，一次执行／恢复，跨阶段衔接 | P1-12、P1-04、P1-05、P1-13 | AC-18、AC-33 |
| F-09 P1：脱敏 sidecar 暴露私有原件裸哈希 | 敏感或未知原件的 source_sha256 为 null，原 hash 只私有保存；幂等核对私有映射，不用 null 相等或同样脱敏文本证明同源 | P1-12 | AC-30、AC-34 |

本轮只修改本 PRD，不修改 README.md、README.html、版本化 automation prompt、CHANGELOG 或运行代码；这些入口仍描述已实现产品。本版验证只证明文档结构和契约闭合，不声明批次幂等或隐私实现已经运行验证。

文档 2.2 当时的 45 项任务、34 条 AC 和定点复核结果见 R-08；该结果不覆盖后续恢复入口、全产物隐私和备份保留发现。本轮实际结果记录在下节，不沿用旧通过结论。

### 22.2 恢复、隐私及保留修复与 review 循环

| 发现 | 最小修复 | 实施任务 | 验收 |
|---|---|---|---|
| F-10 P1：恢复缺可调用入口／收据 | 只增加manifest目录内的recovery plan/receipt；有证据的部分失败可恢复，证据不足blocked，不建journal/锁/索引 | P1-20、P2-02 | AC-18、AC-35 |
| F-11 P1：隐私门只覆盖legacy sidecar | 已知字段、正文、附件、文件名、spec/lessons/索引统一publication decision；私有原件与共享投影分开 | P1-12 | AC-30、AC-36 |
| F-12 P2：备份成功后无保留／销毁边界 | cleanup不删备份；明确责任人、观察／回滚窗口和人工复核，单独确认销毁；处置任务不反向阻塞tag | P1-11、P2-01、P2-05、P3-04 | AC-37 |
| F-13 P1：候选准备与 plan/apply 时序循环 | 明确授权的仓库外候选准备在plan之前；plan验证绑定，apply只复验应用，AC-29同步 | P1-12 | AC-29、AC-36 |
| F-14 P2：P1-01与P1-20恢复验收归属重叠 | P1-01仅参数/schema/envelope基础契约，不持有AC-35；P1-20独占恢复行为交付 | P1-01、P1-20 | AC-13、AC-35 |
| F-15 P2：取消或放弃后的处置依赖不可达 | P3-04改为正常发布／明确终止两条条件门；无manifest时以私有候选清单和授权证据盘点 | P3-04 | AC-37 |
| F-16 P2：恢复验收未等待实际cleanup实现 | P1-20增加P1-13依赖；各阶段先证明操作与证据，跨阶段恢复统一后验收 | P1-13、P1-20 | AC-18、AC-33、AC-35 |
| F-17 P1：apply重试无收据输入 | 公开可选--apply-receipt；绑定manifest、按累计结果续作或完成核对 | P1-01、P1-12 | AC-13、AC-18、AC-29 |
| F-18 P1：cleanup部分失败一律blocked且增量证据不闭合 | 合法partial receipt允许续作；阶段及恢复新收据自包含累计结果，旧证据/原备份不覆盖 | P1-12、P1-13、P1-20 | AC-18、AC-29、AC-35 |
| F-19 P2：逐项目完整验收过早归P2-04 | P2-04仅部署/smoke子项；P2-05完成AC-21集成验收和逐项目报告 | P2-04、P2-05 | AC-21 |
| F-20 P1：实施根任务仍依赖旧审核 | P0根改为R-09；P0/P1开工统一等待本轮收敛，间接依赖随DAG生效 | P0-01、P0-02、P0-09、P0-10 | AC-03、AC-21 |
| F-21 P1：plan调用表漏候选输入 | 将--publication-decisions列入公开形状，限定仅无共享发布分支可省略 | P1-01、P1-12 | AC-13、AC-29、AC-36 |
| F-22 P1：recovery调用表漏证据和续作输入 | plan列全阶段证据及范围参数，apply列--recovery-receipt，与后文校验一致 | P1-01、P1-20 | AC-13、AC-35 |
| F-23 P1：候选裁决输入缺机器schema | 冻结UTF-8 JSON v1、逐项字段/枚举/唯一性及缺失/未知拒绝规则 | P1-01、P1-12 | AC-29、AC-36 |
| F-24 P1：部署外层证据缺消费schema | 冻结versioned外层、状态、累计资源/报告引用及消费者验证；不改原生报告schema | P1-01、P1-04、P1-05、P1-20 | AC-18、AC-29、AC-35 |
| F-25 P1：批准记录自由文本不可机器比对 | approval直接携带获批scope结构快照，逐值匹配；真实授权独立，不建批准服务 | P1-01、P1-12 | AC-29、AC-36 |
| F-26 P1：部署证据无续作I/O | 现有init/init-projects附加显式manifest/apply/previous/out参数，返回deploymentEvidence；不增migration阶段 | P1-01、P1-04、P1-05 | AC-13、AC-18、AC-29 |
| F-27 P1：项目私有部署操作没有闭集 | 固定projects[].private_operations及唯一性/前态依赖；结果覆盖与失败差集可校验 | P1-01、P1-12、P1-20 | AC-18、AC-29、AC-35 |
| F-28 P2：生产消费未进入P1唯一台账 | P1-04/05生产、P1-12 verify、P1-13 cleanup、P1-20恢复，P1-14真实全链；接口fixture不冒充集成 | P1-04、P1-05、P1-12、P1-13、P1-14、P1-20 | AC-18、AC-29、AC-35 |
| F-29 P1：旧scope分支仍让P2-04选择sync | 删除替换部署分支；P2-04只走init上下文，sync/live仅批次外另行授权，不旁路证据链 | P1-11、P2-01、P2-04 | AC-15、AC-18、AC-29 |
| F-30 P1：删除前未保证本次授权持久化 | 先保存custodian/归属/范围/授权及时间并回读成功，再删除；结果后补，失败零删除 | P1-11、P1-14、P3-04 | AC-37 |
| F-31 P2：AC-37漏四项前置负面验收 | 逐项缺失及删除前授权记录保存/回读失败均blocked、零删除、不得done | P1-14、P3-04 | AC-37 |
| F-32 P1：P1-14整体引用AC-37反向等待发布 | 明确实现期子项与P2/P3实际安排/观察/处置验收分层，不形成发布反依赖 | P1-11、P1-14、P2-01、P2-05、P3-01、P3-04 | AC-37 |
| F-33 P2：pre-manifest处置被既有迁移报告卡住 | 授权与结果可复用删除范围外的既有私有准备记录，沿用格式且删除前核验可写 | P1-11、P1-14、P3-04 | AC-37 |
| F-34 P1：实际确认时间缺失未纳入阻断验收 | 正文、P1-14分层证明、P3-04及AC-37均包含确认时间；缺失同样blocked/零删除/不得done | P1-14、P3-04 | AC-37 |
| F-35 P2：前置段与步骤允许的记录载体不一致 | 统一为删除范围外的既有私有准备记录或迁移报告，不要求另建记录格式 | P1-11、P1-14、P3-04 | AC-37 |

Advisor 处理：nextStep 命名与批次 apply_receipt 的旧意见已在当前正文修复；L647 唯一部署归属已修复。新 blocker“不要新增 journal/锁/证据索引/处置子系统”已采纳，撤回草稿中这些设计，仅保留 manifest-scoped recovery plan/receipt 与人工备份规程。原 Trellis workspace journal 是待保全的历史数据，不是新运行子系统。

后续advisor补强与重新验收：pre-manifest终止分支的custodian、候选归属、精确范围、本次独立授权及实际确认时间须在删除前保存并回读；缺项即blocked。先前定点检查不能替代完整review，因此已按blocker重开R-09，修复后续F-30～F-35，再由第11轮完整复审确认当前契约；没有把第三轮或旧快照结论追认为本次专项证据。旧完成、重开和重新完成均留在§18.3。

| 本次循环轮次 | Reviewer | 受审快照 SHA-256 | 新发现 | 处理 |
|---|---|---|---|---|
| 1 | ConvergeReviewOne | 38d58c85036f9c41405508e4068fe84dfdef650f54809086272106f81f8e3029 | 2 | F-13、F-14 已修订，须由后续新快照复审确认 |
| 2 | ConvergeReviewTwo | 48bc11b088c91fee39608cdca28dcd2c47b0f5c99825e4925d6d63c2971666b6 | 2 | F-13/F-14已获确认；新增F-15/F-16已修订，须后续新快照复审确认 |
| 3 | ConvergeReviewThree | 1f0400934313d3885158cf9130fc2d2a7cb4b0c78957c8562ee412eba77c45b7 | 4 | F-17～F-20已修订，须后续新快照复审确认 |
| 4 | ConvergeReviewFour | 3c35f236a548bfde755f6536e895a332b666093c5c9b2088f71c49f25d095969 | 4 | 恢复顺序/累计证据/阶段归属获确认；F-21～F-24已修订，待新快照复审 |
| 5 | ConvergeReviewFive | 1a4c27853933b63853e1688ceb0e3a80a05800000d7cb8833c75db5faf8c17e2 | 4 | F-25～F-28已修订，待新快照复审 |
| 6 | ConvergeReviewSix | 87348e5439b3856d09e10a5a326dd9a0e8ea533dddc23cfde86ca33ad9ca0380 | 1 | F-25～F-28获确认；残留sync边界F-29已修订，待新快照复审 |
| 7 | ConvergeReviewSeven | cdd2da66b0a219032792d59ea2c8c49798639a67821efd264af9b4b9062bc226 | 0 | ready；全文无新实质性问题，确认F-29与全篇部署/恢复契约一致 |
| 8 | ConvergeReviewFinal | 511322a4580acc01f51727fbb76f84a919ebe871c1a62d12115563cda0461a33 | 0 | 当时最终落盘快照通过；不覆盖之后的advisor定点契约修改 |
| 9 | PostAdvisorFullReview | f112e8c7587190af51a3f154f127d37d883bb3a3fd81390ddded0733d577630c | 4 | R-09重开后完整复审；F-30～F-33已修订，须对新快照继续复审 |
| 10 | PostAdvisorRecheck | 1c22ef74dec4208be2f0d853f4018a07536e521710d9f360b0f2761def0a5fe8 | 2 | 阶段分层/删除前保存已获确认；F-34/F-35已修订，待新快照全文复审 |
| 11 | PostAdvisorThirdReview | 9f01be78f9f912785b20c58a9f377ea6184a8f1ea453c4ef1eb2e192af10fc84 | 0 | ready；全文复核确认时间/载体一致、删除前保存及P1/P3验收分层，重开后的契约收敛 |

各行保留当轮状态；第7/8轮结果只覆盖当时快照，第11轮才覆盖之后的pre-manifest契约补强及F-30～F-35修复。当时结构检查通过48项任务、37条AC、37项决策、35项修复映射、43张表及5条本地链接。文档2.6快照中R-01～R-09与P0-01完成，其余38项实施／发布后任务仍planned；后续实时状态以§14为准。P0-01隔离spike见第9.8节（local-only），不是生产／host／CI运行验证。不把文档复审冒充v2已交付。

以上第 1～11 轮保留 R-09 当时的审查历史。后续 PR #8 分支在 `68557966f460a92fe5cb84431870f08732ad8691` 的独立零发现审查另见 §16.4，合并事实见 §18.3；不改写旧 reviewer 快照或将文档合并视为实施任务完成。

上述历史文档复审的停止条件：每轮更新受审文件，由独立 reviewer 完整只读复核，处理成立发现及 advisor，直至当时快照零新发现、结构／依赖检查通过。进入实施后，每项任务分别执行该修复／复审循环及 §14.1 的 PR／状态同步协议；历史文档通过不证明后续代码、真实迁移或备份销毁已完成。

**最终约束：本文汇总的是已确认需求和实施契约，不是已交付 v2。只有具体任务的验收通过、台账状态及实际完成时间同步、证据可复查，才允许将对应任务标记 done。**
