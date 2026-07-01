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
- 问题：将远程 `main` 快进到本地后，远程历史中的 `.gitignore` 第四行 `.pi/` 被带入本地，违反本仓库 `.gitignore` 必须严格三行的规则。
- 根因：合并远程分支时只关注 Git 历史推进，容易忽略远程已有提交也可能与当前仓库硬规则冲突。
- 修复：推送前重新校验 `.gitignore` 精确内容，删除 `.pi/` 并保留 `.DS_Store`、`.gitnexus/`、`.trellis/` 三行。
- 预防：后续在 `main` 合并、快进或推送前，都要运行 `.gitignore` 精确三行检查；即使变更来自远程已有提交，也不能跳过本仓库规则验证。

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
