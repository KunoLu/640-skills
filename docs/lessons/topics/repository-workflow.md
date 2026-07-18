# Repository Workflow Lessons

本 topic 保存当前配置摘录仓库定位、AGENTS / ENTRYPOINT / README、同步、版本检查和仓库级规则相关 lessons。

## LESSON-20260701-entrypoint-version-baseline: ENTRYPOINT Version Baseline

- 日期：历史记录迁移，原始日期未记录
- 标签：automation, entrypoint, update
- 适用场景：每日版本检查、`ENTRYPOINT.md` 写回、`UPDATE.md` 生成
- 严重级别：high
- 来源：迁移自 `docs/lessons.md`
- 原始标题：每日版本检查不得推进 ENTRYPOINT 当前版本
- 问题：每日版本检查自动化在发现 Codex 新版本后，把 `ENTRYPOINT.md` 中的当前版本从 `v0.131.0` 自动更新到了 `v0.132.0`，且 `UPDATE.md` 使用了英文内容。
- 根因：automation prompt 没有明确区分“每日检查”和用户手动输入 `更新` / `update` 后的写回动作，也没有要求 `UPDATE.md` 必须使用中文。
- 修复：每日自动化只读取 `ENTRYPOINT.md` 当前版本作为固定比对起点，只用中文刷新 `UPDATE.md`，不得写回 `ENTRYPOINT.md`；只有用户手动输入 `更新` / `update` 时才允许更新版本号并归档。
- 预防：后续涉及自动化写入项目基线文件时，必须在 prompt 和 `AGENTS.md` 中同时明确“只读基线”和“手动确认写回”的边界。

## LESSON-20260701-config-excerpt-repo-boundary: Config Excerpt Repo Boundary

- 日期：历史记录迁移，原始日期未记录
- 标签：repository, templates, scope
- 适用场景：判断当前仓库角色、修改 AGENTS / Skill 模板、迁移配置摘录
- 严重级别：high
- 来源：迁移自 `docs/lessons.md`
- 原始标题：配置摘录仓库不得按真实业务项目判断
- 问题：维护 Codex 配置摘录时，容易把仓库内的 `AGENTS.md`、`skills/`、`ENTRYPOINT.md` 当成真实业务项目结构来解释，从而引入“当前仓库直接生效”“当前仓库事实源”等误导措辞。
- 根因：配置摘录仓库同时保存全局规则、项目级规则模板和 Skill 镜像，外观类似项目根目录，但其目标是为后续同步和复用配置，不代表正在开发的业务仓库。
- 修复：将相关文档改为“配置文件与 Skill 的摘录/同步源”，避免把配置摘录仓库误写成真实工作项目的事实源。
- 预防：后续修改本仓库时，先区分“配置摘录源”和“真实工作项目”；不要因为缺少 `.trellis/`、`.gitnexus/` 等目录就改写模板规则的适用边界。

## LESSON-20260701-project-agents-template-boundary: Project Agents Template Boundary

- 日期：历史记录迁移，原始日期未记录
- 标签：agents, templates, scope
- 适用场景：修改 `AGENTS.project.md`、根 `AGENTS.md` 或全局 / 项目模板
- 严重级别：high
- 来源：迁移自 `docs/lessons.md`
- 原始标题：项目级 AGENTS 模板不得镜像配置仓库根 AGENTS
- 问题：`agents/AGENTS.project.md` 被错误改成了与本配置仓库根 `AGENTS.md` 基本相同的内容，丢失了它作为真实项目仓库根目录 `AGENTS.md` 模板的角色。
- 根因：没有区分三类文件：`agents/AGENTS.global.md` 是 Codex 全局规则模板，`agents/AGENTS.project.md` 是真实项目级规则模板，本仓库根 `AGENTS.md` 只是配置摘录仓库自身规则。
- 修复：重新将 `agents/AGENTS.project.md` 调整为真实项目级模板，承接全局规则并补充项目事实源、Trellis、GitNexus、Channel、验证和 Lessons 的项目级约束。
- 预防：后续同步规则时，不能把本仓库根 `AGENTS.md` 复制到 `agents/AGENTS.project.md`；两者加载位置、适用对象和内容职责不同。

## LESSON-20260701-local-sync-explicit-trigger: Local Sync Explicit Trigger

- 日期：历史记录迁移，原始日期未记录
- 标签：sync, local-config, scope
- 适用场景：同步本仓库配置到本机实际生效路径
- 严重级别：high
- 来源：迁移自 `docs/lessons.md`
- 原始标题：本地配置同步必须显式触发
- 问题：本地同步规则曾写成全局规则或全局 Skill 发生修改后“还应同步到本地 PC”，容易导致普通编辑任务立即覆盖实际生效的本地 Codex 配置。
- 根因：没有区分“维护仓库源文件”和“落地到本地实际路径”两个动作，触发语义不够明确。
- 修复：将同步逻辑改为只有用户主动输入 `同步` 或 `sync` 时才执行；普通修改任务只更新仓库源文件。
- 预防：后续新增同步目标或同步规则时，必须明确触发词、同步范围、校验方式，并保持项目级模板 `agents/AGENTS.project.md` 不自动同步。

## LESSON-20260701-automation-rules-template-boundary: Automation Rules Template Boundary

- 日期：历史记录迁移，原始日期未记录
- 标签：automation, templates, agents
- 适用场景：根据自动化或 release notes 修改长期规则
- 严重级别：high
- 来源：迁移自 `docs/lessons.md`
- 原始标题：自动化规则不得写入可复用模板
- 问题：每日版本更新中，为了约束本仓库自动化如何把 release 结论沉淀为通用规则，曾把该要求误写入 `agents/AGENTS.global.md` 和 `agents/AGENTS.project.md`，污染了给其他项目直接复用的全局/项目级模板。
- 根因：没有先判断规则的适用主体，把“本配置摘录仓库的自动化运行逻辑”和“真实项目会继承的长期 agent 行为规范”混为一谈。
- 修复：撤回两份 agents 模板中的自动化专用规则，只在根 `AGENTS.md` 保留每日版本检查自动化约束；`skills/trellis-channel/SKILL.md` 仅保留与 Trellis Channel 实际使用边界相关的通用规则。
- 预防：后续根据 release notes 修改规则时，先分类目标文件角色：根 `AGENTS.md` 可写本仓库自动化流程，`agents/AGENTS.global.md` / `agents/AGENTS.project.md` 只写对真实项目普遍成立的行为规范，`skills/**/SKILL.md` 只写该 Skill 自身长期有效的使用规则。

## LESSON-20260701-entrypoint-table-semantic-writeback: ENTRYPOINT Table Semantic Writeback

- 日期：历史记录迁移，原始日期未记录
- 标签：entrypoint, update, markdown
- 适用场景：写回 `ENTRYPOINT.md` 版本字段
- 严重级别：high
- 来源：迁移自 `docs/lessons.md`
- 原始标题：ENTRYPOINT 版本写回必须限定表格语义
- 问题：手动 `update` 写回 `ENTRYPOINT.md` 时，脚本用“第一列等于工具名”的宽泛表格正则替换版本，误改了“工具定位”表里的“是否进入主流程”列，并把“当前版本汇总”表压成一行。
- 根因：没有按 Markdown 章节和表头定位，只用工具名匹配任意表格行，导致同名工具在非版本表格中也被当成版本记录。
- 修复：立即用精确补丁恢复非版本表格，只保留版本监控表、工具当前关注版本和当前版本汇总中的版本更新。
- 预防：后续写回 `ENTRYPOINT.md` 时必须先按章节标题和表头定位目标表，再按列名更新“当前使用版本”或“当前版本记录”；不要对全文表格做工具名全局替换。

## LESSON-20260701-display-task-config-boundary: Display Task Config Boundary

- 日期：历史记录迁移，原始日期未记录
- 标签：docs, config, scope
- 适用场景：展示型 / 文档型任务中出现 `.gitignore`、`.gitattributes` 等配置片段
- 严重级别：medium
- 来源：迁移自 `docs/lessons.md`
- 原始标题：展示型任务中的参考配置不得直接写入当前仓库
- 问题：在规划模板/Skill 展示 HTML 时，用户提供 `.gitignore` 和 `.gitattributes` 参考规则，本应作为 HTML 中给其他代码仓库使用的配置说明，却被误写入当前配置摘录仓库。
- 根因：没有先确认用户提供的配置片段属于“展示内容”还是“当前仓库变更”，忽略了本仓库是配置摘录源且用户正在讨论 HTML 展示内容的上下文。
- 修复：立即恢复当前仓库 `.gitignore` 原内容，并删除误新增的 `.gitattributes`。
- 预防：后续展示型、文档型任务中，用户给出的配置片段默认先视为文档内容候选；只有用户明确要求修改当前仓库配置文件时，才落地到仓库根配置。

## LESSON-20260701-github-release-source-crosscheck: GitHub Release Source Crosscheck

- 日期：历史记录迁移，原始日期未记录
- 标签：github, release, update
- 适用场景：判断上游最新版本或 changelog
- 严重级别：medium
- 来源：迁移自 `docs/lessons.md`
- 原始标题：GitHub blob 页面不得作为唯一最新版本依据
- 问题：每日版本检查中，GitHub blob 页面和网页搜索片段一度显示某工具最新版本仍停在旧版本，但 GitHub Releases 与 raw changelog 已发布新版本。
- 根因：只看渲染后的 changelog blob 或搜索片段会受页面缓存、折叠和抓取结果影响，无法保证覆盖最新 release 条目。
- 修复：改用 GitHub Releases 页面和 raw changelog 交叉确认，校正本次版本区间。
- 预防：后续每日版本检查遇到 changelog / release 信息不一致时，至少交叉检查 GitHub Releases、raw changelog 或 tags；不要把 GitHub blob 渲染页或搜索片段当作唯一最新版本依据。

## LESSON-20260701-post-merge-hard-rule-validation: Post Merge Hard Rule Validation

- 日期：历史记录迁移，原始日期未记录
- 标签：git, repository, validation
- 适用场景：合并或快进远程分支后
- 严重级别：high
- 来源：迁移自 `docs/lessons.md`
- 原始标题：合并远程分支后仍需校验仓库硬规则
- 问题：将远程 `main` 快进到本地后，远程历史中的 `.pi/` 被带入本地，违反本仓库 `.gitignore` 必须严格三行的规则。
- 根因：合并远程分支时只关注 Git 历史推进，容易忽略远程已有提交也可能与当前仓库硬规则冲突。
- 修复：推送前重新校验 `.gitignore` 精确内容，删除 `.pi/` 并保留 `.DS_Store`、`.gitnexus/`、`.trellis/` 三行。
- 预防：后续在 `main` 合并、快进或推送前，都要运行 `.gitignore` 精确三行检查；即使变更来自远程已有提交，也不能跳过本仓库规则验证。
- 状态更新（2026-07-16）：Python 验证会生成仓库根或 `tests/` 下的 `__pycache__/`，因此当前 canonical 契约已调整为 `.DS_Store`、`.gitnexus/`、`.trellis/`、`__pycache__/` 四行；自动化和测试必须断言这四行，不得继续套用历史三行规则。
- 状态更新（2026-07-18）：并行审核确认，把仓库必需的 `AGENTS.md` 和 authoritative `ENTRYPOINT.md` 同时设为 ignored / untracked 会让新 clone 缺少启动规则和版本基线；已恢复二者由 Git 追踪，当前 canonical `.gitignore` 恢复为 `.DS_Store`、`.gitnexus/`、`.trellis/`、`__pycache__/` 四行。

## LESSON-20260718-required-controls-tracked-source: Required Controls Need a Tracked Source

- 日期：2026-07-18
- 标签：repository, controls, gitignore, bootstrap, review
- 适用场景：调整仓库启动规则、版本基线、根 `AGENTS.md` / `ENTRYPOINT.md` 的追踪或忽略策略
- 严重级别：high
- 来源：8-agent 未提交变更审核及 fresh-clone 契约测试复核
- 问题：将根 `AGENTS.md` 和 `ENTRYPOINT.md` 从索引移除并加入 `.gitignore`，同时又要求每次仓库操作在二者缺失时立即停止；当前工作站保留副本，但新 clone 无法取得规则和版本基线。
- 根因：只验证了既有工作树的“文件仍存在”，没有验证远程 clone 的可恢复性，也没有提供 tracked canonical source 和先于 Gate 执行的 bootstrap。
- 修复：恢复 `AGENTS.md` 和 `ENTRYPOINT.md` 由 Git 追踪，`.gitignore` 恢复四行；README、automation prompt 和契约测试同步改为断言 tracked controls，并让测试直接检查 Git 索引。
- 预防：任何启动前必需文件必须直接受版本控制，或同时提供受版本控制的 canonical source 与可在 Gate 前执行的 bootstrap；不得把文件设为 ignored / untracked 后又把其存在作为所有操作的前置条件。

## LESSON-20260701-entrypoint-detail-section-contract: ENTRYPOINT Detail Section Contract

- 日期：历史记录迁移，原始日期未记录
- 标签：entrypoint, validation, markdown
- 适用场景：校验 `ENTRYPOINT.md` 详情章节
- 严重级别：medium
- 来源：迁移自 `docs/lessons.md`
- 原始标题：ENTRYPOINT 详情章节校验不得硬编码行名
- 问题：手动 `update` 后的结构化验证脚本硬编码检查 GitNexus 详情章节必须存在 `当前关注版本` 行，但 `ENTRYPOINT.md` 的 GitNexus 章节并不使用该行名，导致校验脚本误报失败。
- 根因：校验脚本没有继续沿用“以版本监控表和当前版本汇总表为主数据源”的规则，而是对单个详情章节写了脆弱的文本包含断言。
- 修复：把验证改回按 Markdown 表格语义解析 `## 0. 版本监控配置`、归档文件区间和 `## 8. 当前版本汇总`，只对确实存在且有稳定结构的字段做断言。
- 预防：后续验证 `ENTRYPOINT.md` 写回结果时，以章节标题、表头和列名为准；不要为某个工具详情章节硬编码一整行文案或假设所有工具章节都有同名字段。

## LESSON-20260709-installer-mcp-generated-config: Installer MCP Generated Config

- 日期：2026-07-09
- 标签：installer, mcp, workflow
- 适用场景：修改根安装脚本、`onboard.py` manualChecks 或已知 MCP server 配置
- 严重级别：medium
- 来源：用户在另一台 Mac 运行 `bash install.sh` 时选择 GitNexus MCP 后，脚本要求手动输入已可从全局 `gitnexus` CLI 推断的 MCP 命令。
- 问题：GitNexus CLI 已经全局安装，MCP 配置实际只需要本机 `gitnexus` 可执行文件路径和 `mcp` 参数，但安装器仍把 GitNexus 当作完全自定义 stdio server，让用户手输命令。
- 根因：`onboard.py check` 没有为 GitNexus MCP 产出结构化 `mcpServerConfig`，根安装脚本也只对 Maestro MCP 读取生成配置，导致已知 server 的配置事实和交互式安装流程脱节。
- 修复：让 `onboard.py check` 在检测到本机 `gitnexus` CLI 路径时生成 `command = <detected path>`、`args = ["mcp"]` 和 JSON / TOML 示例；`install.sh` / `install.ps1` 消费这份配置，只有路径缺失时才回退到人工输入。
- 预防：后续新增或维护已知 MCP server 时，优先在 `onboard.py` 的 manual check 中沉淀 `mcpServerConfig`，根安装器只适配选定 platform；不要把可检测的 command / args / env 重新变成人工输入。

## LESSON-20260709-external-skill-rename-canonical: External Skill Rename Canonical

- 日期：2026-07-09
- 标签：installer, skills, workflow, migration
- 适用场景：维护 external Skill 列表、mattpocock/skills 映射、install/reset 迁移逻辑
- 严重级别：medium
- 来源：用户在另一台 Mac 运行 `bash install.sh` 时，`to-prd` 和 `to-issues` 安装失败；上游 mattpocock/skills 已改为 `to-spec` 和 `to-tickets`。
- 问题：本仓库仍把旧 Skill 名称和旧 subpath 当作 canonical，安装器克隆上游后找不到唯一匹配目录，fallback 扫描列出大量候选并失败。
- 根因：external Skill 配置没有跟随上游 frontmatter / 目录名更新，也没有把旧名作为 legacy alias 纳入迁移删除流程。
- 修复：将默认外部 Skill、模板编排和 subpath 映射迁到 `to-spec` / `to-tickets`；`to-prd` / `to-issues` 只作为 legacy alias；`init` / `reset` 和直接 external install 检测到旧目录时先删除，再安装 canonical 新目录。
- 预防：后续维护 external Skill 时，先用上游仓库当前 `SKILL.md` frontmatter 和目录结构确认 canonical 名称；旧名只能进入 alias / migration，不要继续放在默认安装列表或长期 workflow 主链路中。

## LESSON-20260711-external-skill-transaction-path-safety: External Skill Transaction Path Safety

- 日期：2026-07-11
- 标签：installer, skills, rollback, path-traversal, validation
- 适用场景：修改 External Skill stable manifest、上游 source promotion、canonical 存在性检查、legacy migration 或事务替换逻辑
- 严重级别：critical
- 来源：External Skills stable fallback 实现后的独立 review handoff 与回归测试
- 问题：stable manifest 和 promotion 配置中的绝对路径或 `..` 可逃逸声明根目录；只有文件存在但 frontmatter 无效的 canonical 会阻止重装并导致有效 legacy 被删除；事务恢复失败后 finally 仍删除 rollback 目录，可能销毁唯一可恢复副本。
- 根因：路径由多个调用点直接拼接而没有统一 containment seam，canonical 检测只判断 `SKILL.md` 文件存在，rollback 生命周期没有区分“完整恢复”和“恢复仍有错误”。
- 修复：集中使用解析后 containment 校验拒绝绝对路径、`..` 和 symlink 逃逸；canonical 与安装源使用同一完整 Skill 验证；rollback 仅在 commit 成功或完整恢复后清理，恢复不完整时在结果中返回并保留目录路径；`auto` 仅在上游组失败时延迟加载 stable。
- 预防：External Skill 安装器新增字段或文件操作时，必须同时验证 source root containment、完整 canonical 语义和最坏情况下的备份所有权；回归测试至少覆盖路径逃逸、无效 canonical + 有效 legacy、上游成功时 stable 不可读，以及 restore 二次失败后备份仍存在。

## LESSON-20260717-mode-exit-reentry-contract: Mode Exit Must Define Re-entry Lifecycle

- 日期：2026-07-17
- 标签：agents, workflow, caveman, state-machine, validation
- 适用场景：修改 Agent 自动模式、手动模式、退出 / 恢复指令、任务级或会话级状态，以及相应文本契约测试
- 严重级别：medium
- 来源：Caveman auto-lite 实现后的 Review handoff
- 问题：通用 `normal mode` 等退出指令只恢复了当前答复，没有禁止已经满足阈值的自动模式在同一任务内再次进入；测试只断言孤立关键词，删除完整资格条件或退出生命周期后仍可能通过。
- 根因：规则没有把手动模式、任务级自动退出、会话级自动退出和配置 `off` 建模成有优先级的状态；文本契约测试也没有按完整行为子句锁定前置条件、作用域和重入条件。
- 修复：明确通用退出建立任务级自动退出，会话级退出优先于任务级状态，显式手动启动不清除自动退出，配置 `off` 优先级最高；回归测试改为断言成组资格条件、退出作用域、显式恢复和新任务重算语义。
- 预防：后续新增任何自动模式或退出命令时，必须同时定义状态作用域、优先级、何时清除、是否允许重入和新任务 / 新会话边界；文本契约测试必须断言完整行为子句，不能只检查模式名或命令词存在。

## LESSON-20260716-orca-hub-tool-boundary: Orca CLI and Hub Have Separate Control Planes

- 日期：2026-07-16
- 标签：orca, hub, tools, worktree, automation
- 适用场景：修改 Orca worktree 元数据、检查或运行 Orca automation、向当前 harness peer 发送消息
- 严重级别：medium
- 来源：本次 SBTD Onboard 重命名任务中，创建 Orca feature branch 后尝试用 Hub `send` 更新 worktree 状态。
- 问题：Hub `send` 因没有有效 peer recipient 而失败；它不能更新 Orca worktree comment，也不能替代 Orca automation / worktree 命令。
- 根因：把当前 harness 的 peer 协调控制面与 Orca 应用持久化的 worktree / automation 控制面混为一谈。
- 修复：worktree comment 使用 `orca worktree set --worktree active --comment ... --json`；automation 使用 `orca automations show/edit/run`；Hub 只在 `hub list` 返回精确 peer id 后用于会话内 peer 消息。
- 预防：任务涉及 Orca 状态时先读取 `orca-cli` Skill 并使用 `orca`；涉及 subagent peer 协调时才使用 Hub，且发送前先确认 roster。一个控制面的成功或失败不得推断另一个控制面的状态。

## LESSON-20260716-orca-automation-live-lookup: Orca Automation Mutation Requires Live Lookup

- 日期：2026-07-16
- 标签：orca, automation, cli, prompt, validation
- 适用场景：读取、修改或验证 Orca live automation，尤其是把版本化 prompt 同步到定时任务时
- 严重级别：medium
- 来源：同步 `SBTD Workflow Tools Version Check` prompt 时，复用了先前会话中的 automation id，并误用不存在的 `--prompt-file` 参数。
- 问题：缓存的 automation id 已失效，`orca automations edit` 返回 `Automation not found`；当前 CLI 也不支持 `--prompt-file`，首次同步未生效。
- 根因：把先前查询到的 live id 和假设的文件参数当作稳定接口，没有先用当前 Orca runtime 重新枚举 automation 并检查命令返回的有效参数。
- 修复：先运行 `orca automations list --json`，按精确名称定位当前 id；再用 `orca automations edit --id <id> --prompt <完整内容> --json` 更新，并用 `show --json` 逐字段确认 prompt、enabled、schedule、timezone、workspace mode 和 workspace path。
- 预防：每次修改 live automation 都必须在当前 runtime 中按名称重新定位 id，不复用历史会话 id；参数错误时以 CLI 返回的 `validFlags` 为准；修改后必须比较完整 prompt 并复核调度元数据。

## LESSON-20260718-automation-sync-trigger-separation: Separate Prompt Maintenance From Live Sync

- 日期：2026-07-18
- 标签：automation, prompt, sync, update, workflow
- 适用场景：修改版本化 automation prompt、普通仓库变更、执行 `sync` / `同步` 或 `update` / `更新`
- 严重级别：high
- 来源：用户纠正 automation prompt 的同步触发语义
- 问题：规则曾要求版本化 prompt 一经修改就立即写入 Orca live automation，并把每次 `update` 也绑定到 live prompt 重同步，超出了用户期望的触发范围。
- 根因：混淆了“普通代码改动后评估仓库内版本化 prompt 是否需要维护”“显式 sync 时把版本化 prompt 发布到 Orca”和“update 只推进版本基线并归档”三个独立动作。
- 修复：普通仓库改动只评估并按需更新 README 两份文件和版本化 prompt；只有显式 `sync` / `同步` 才读取 live automation、比较完整 prompt 并仅在存在差异时同步；`update` / `更新` 不检查、不修改也不同步版本化 prompt 或 live automation。
- 预防：新增维护或发布规则时，必须分别定义仓库源文件维护触发器、外部系统发布触发器和无关流程，不能用“每次修改后立即同步”把三者合并。

## LESSON-20260718-generated-agent-alias-target: Generated Agent Aliases Need a Live Canonical Target

- 日期：2026-07-18
- 标签：repository, skills, symlink, claude, discovery
- 适用场景：运行 Skills CLI、调整 Skill discovery 路径、提交 `.claude/skills` / `.agents/skills` 或迁移 canonical Skill 目录
- 严重级别：high
- 来源：`v1.0.0` 发布后检查根 `.claude/` 目录时发现 tracked broken symlink
- 问题：仓库提交了 `.claude/skills/sbtd-workflow-onboard -> ../../.agents/skills/sbtd-workflow-onboard`，但 `.agents/skills/sbtd-workflow-onboard` 不存在；Claude Code 无法通过该 alias 加载 Skill，且该路径与根目录自包含 Skill 的公开安装边界冲突。
- 根因：布局迁移时保留了本地 Skills CLI 生成的项目级 Agent alias，却没有验证 symlink target、Git 追踪状态和当前 canonical discovery entrypoint 是否一致。
- 修复：从仓库删除 `.claude` broken symlink，继续以根 `sbtd-workflow-onboard/SKILL.md` 为唯一公开 discovery entrypoint，并增加仓库契约测试禁止重新提交该 alias。
- 预防：提交任何 Agent-specific Skill alias 前必须同时验证 link target 存在、target 是当前 canonical source、alias 属于仓库设计而非本地安装副作用；全局安装模式不得把 `.claude/skills`、`.agents/skills` 等项目级生成物加入版本控制。
