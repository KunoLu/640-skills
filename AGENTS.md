# AI Tools 项目规则

本仓库是 Codex 配置文件与 Skill 的摘录/同步源，不代表一个真实业务项目结构。本文件只保留本配置摘录仓库自身直接生效的补充规则；可复用的全局规则、项目级规则和全局 Skill 模板集中维护在 `kuno-workflow-onboard-skills/`。

## Agent 规则文件路径

本配置集维护的 agent 规则文件路径如下：

- 根目录 `AGENTS.md`：保存本配置摘录仓库自身直接生效的补充规则，包括每日版本检查自动化和 `更新` / `update` 指令。
- `kuno-workflow-onboard-skills/templates/agents/AGENTS.global.md`：保存迁移后的全局规则文档。
- `kuno-workflow-onboard-skills/templates/agents/AGENTS.project.md`：保存迁移后的项目规则文档。
- `kuno-workflow-onboard-skills/templates/skills/**`：保存迁移后的全局 Skill 模板及其 references / scripts / assets。
- `kuno-workflow-onboard-skills/SKILL.md`、`kuno-workflow-onboard-skills/REFERENCE.md`、`kuno-workflow-onboard-skills/scripts/onboard.py`：保存 onboard Skill 自身的说明和安装 / 重置自动化。

每日版本检查自动化如需读取、评估或修改 agent 规则，只能使用上述路径。不要再读取或修改已删除的旧路径 `agents/`、`skills/`、根目录旧路径 `AGENTS.global.md` 和 `AGENTS.project.md`。

## Lessons 读取规则

本仓库的长期经验记录采用 `lessons-record` 的分层结构，但保留 `docs/lessons.md` 作为每次操作前的必读短入口：

- `docs/lessons.md`：必读短入口，只保存读取协议、topic 路由和高频摘要，不保存完整历史库。
- `docs/lessons/index.md`：完整索引，按 `id`、tags、适用场景和详情路径维护。
- `docs/lessons/topics/<topic>.md`：完整 lesson 详情。
- `docs/lessons/archive/YYYY-QN.md`：低频历史归档，默认不读。

每次执行本仓库操作前，必须先读取 `docs/lessons.md`，理解其中与当前任务相关的高频规则后再继续。
如果当前任务、错误信息、工具名或 tags 命中 `docs/lessons.md` 的 topic 路由或 `docs/lessons/index.md`，再读取对应 topic / archive；不要默认全文读取 `docs/lessons/topics/**`。
如果 `docs/lessons.md` 不存在或不可读取，不要假装已读取；必须在最终输出中说明跳过原因。

写入新 lesson 时，必须将完整记录写入对应 `docs/lessons/topics/<topic>.md` 并同步更新 `docs/lessons/index.md`；只有跨任务高频、缺失会反复导致错误的摘要才同步到 `docs/lessons.md`。不要把完整 lesson 历史重新堆回 `docs/lessons.md`。

## 本仓库 BDD 产物边界

本仓库是配置摘录和模板源，不是真实业务项目；不要在本仓库内生成 `.feature` 文件。
如需描述 BDD / Gherkin 规则，只能写入相关 AGENTS 模板、Skill、README 或对话说明，不要落地为本仓库的持久 `.feature` 产物。

## README 同步规则

后续每次模板内容有更新，都必须评估根目录 `README.md` 和 `README.html` 是否需要同步更新。

如果模板更新影响以下任一内容，必须在同一轮修改中同步更新 `README.md` 和 `README.html`：

- 工作流主线、工具职责边界或最终验证工具栈。
- SDD、BDD、TDD、DDD 或 SBTD 的定义、触发条件、产物位置或协作顺序。
- Chrome DevTools MCP、Playwright CLI、Playwright MCP、Maestro CLI、Maestro MCP、`web-ui-autotest-generator` 或 `seo-geo` 的检测、安装、fallback、报告状态或使用时机。
- `kuno-workflow-onboard-skills/scripts/onboard.py` 的 init、reset、安装或检查行为。
- 模板 `.gitignore`、同步路径、AGENTS 模板路径、Skill 模板路径或用户可见文档入口。

如果评估后无需更新 README，必须在最终输出中说明跳过原因。

## 本地同步规则

普通修改任务只更新本配置摘录仓库内的源文件，不要立即同步到本地 PC 的实际生效路径。

只有当用户主动输入 `同步` 或 `sync` 时，才执行本节同步流程。

同步触发后，只同步以下全局规则和全局 Skill：

| 源文件 | 本地目标路径 |
|---|---|
| `kuno-workflow-onboard-skills/templates/agents/AGENTS.global.md` | `/Users/lusonglin/.codex/AGENTS.md` |
| `kuno-workflow-onboard-skills/` | `/Users/lusonglin/.agent/skills/kuno-workflow-onboard-skills/` |
| `kuno-workflow-onboard-skills/templates/skills/trellis-workflow/` | `/Users/lusonglin/.agent/skills/trellis-workflow/` |
| `kuno-workflow-onboard-skills/templates/skills/trellis-channel/` | `/Users/lusonglin/.agent/skills/trellis-channel/` |
| `kuno-workflow-onboard-skills/templates/skills/project-validation/` | `/Users/lusonglin/.agent/skills/project-validation/` |
| `kuno-workflow-onboard-skills/templates/skills/gherkin-bdd/` | `/Users/lusonglin/.agent/skills/gherkin-bdd/` |
| `kuno-workflow-onboard-skills/templates/skills/knowledge-base-integration/` | `/Users/lusonglin/.agent/skills/knowledge-base-integration/` |
| `kuno-workflow-onboard-skills/templates/skills/maestro-mobile-e2e/` | `/Users/lusonglin/.agent/skills/maestro-mobile-e2e/` |
| `kuno-workflow-onboard-skills/templates/skills/lessons-record/` | `/Users/lusonglin/.agent/skills/lessons-record/` |
| `kuno-workflow-onboard-skills/templates/skills/book-refactoring-pass/` | `/Users/lusonglin/.agent/skills/book-refactoring-pass/` |
| `kuno-workflow-onboard-skills/templates/skills/book-legacy-change-safety/` | `/Users/lusonglin/.agent/skills/book-legacy-change-safety/` |
| `kuno-workflow-onboard-skills/templates/skills/book-ddd-distilled-modeling/` | `/Users/lusonglin/.agent/skills/book-ddd-distilled-modeling/` |
| `kuno-workflow-onboard-skills/templates/skills/book-ddia-data-design/` | `/Users/lusonglin/.agent/skills/book-ddia-data-design/` |
| `kuno-workflow-onboard-skills/templates/skills/book-release-readiness/` | `/Users/lusonglin/.agent/skills/book-release-readiness/` |
| `kuno-workflow-onboard-skills/templates/skills/seo-geo/` | `/Users/lusonglin/.agent/skills/seo-geo/` |

同步要求：

1. 先读取源文件 / 目录，确认路径正确。
2. 文件目标按文件复制；Skill 目录目标必须复制整个目录，包括 `SKILL.md`、`references/`、`scripts/`、`assets/` 等子内容。
3. 同步完成后，在本机实际使用的 external Skill 根目录 `/Users/lusonglin/.agent/skills` 上执行 mattpocock legacy migration：运行 `kuno-workflow-onboard-skills/scripts/onboard.py install-external-skills --skills to-prd,to-issues --scope global --source auto --global-skills-dir /Users/lusonglin/.agent/skills --yes`，让旧 `to-prd` / `to-issues` 目录被删除，并安装 canonical `to-spec` / `to-tickets`。不要默认清理或安装 `/Users/lusonglin/.codex/skills/` 下的同名目录，除非用户明确要求。
4. 文件使用 `cmp -s` 或等价方式确认一致；目录使用 `diff -qr`、递归 checksum 或等价方式确认源目录与目标目录一致；legacy migration 使用 `test ! -e` 确认旧目录不存在，并检查 `to-spec/SKILL.md`、`to-tickets/SKILL.md` 存在。
5. 在最终输出中说明已同步的文件、legacy migration 结果和校验结果。

不要同步：

- `kuno-workflow-onboard-skills/templates/agents/AGENTS.project.md`

`kuno-workflow-onboard-skills/templates/agents/AGENTS.project.md` 是用于复制到真实项目仓库根目录 `AGENTS.md` 的项目级模板，只在具体项目需要时由用户手动落地、通过 `kuno-workflow-onboard-skills` 安装，或由用户明确要求同步。
当 `kuno-workflow-onboard-skills/` 作为 Skill 目录整体同步到 `/Users/lusonglin/.agent/skills/kuno-workflow-onboard-skills/` 时，其中携带的 `templates/agents/AGENTS.project.md` 只作为该 Skill 的模板资产保留，不视为把项目级模板同步到任何真实项目。

### 同步指令

当用户输入 `同步` 或 `sync` 时：

1. 执行上面的本地同步流程。
2. 在本机 `/Users/lusonglin/.agent/skills/` 下执行 legacy migration，将 `to-prd` / `to-issues` 替换为 `to-spec` / `to-tickets`；该步骤使用 synced onboard Skill 的 `install-external-skills` 命令，并明确传入 `--global-skills-dir /Users/lusonglin/.agent/skills`。
3. 不修改 `ENTRYPOINT.md` 版本号。
4. 不归档 `UPDATE.md`。
5. 不提交或推送变更。

mattpocock/skills 默认按官方文件原样使用。本仓库允许在 `kuno-workflow-onboard-skills/assets/external-skills/stable/` 保存带精确上游 commit、checksum 和许可证的原样 stable 镜像，供上游安装不兼容时回退；该镜像不是 fork，不得手工改写，只能通过 stable promotion 流程整组更新。除该受管 stable 镜像外，不要在本仓库内另行安装、fork 或改写这些官方 Skill。

## 每日版本检查自动化

Codex 每日版本检查自动化必须遵守：

1. `UPDATE.md` 的正文内容必须使用中文。
2. 自动化只读取 `ENTRYPOINT.md` 中的当前版本作为比对基线；不要修改 `ENTRYPOINT.md` 中任何工具的当前版本号。
3. 对同一工具多次执行自动化时，`UPDATE.md` 中的版本区间必须始终保持为：`ENTRYPOINT.md` 中该工具当前版本号 -> 最新检测并完成比对分析的版本号。
4. 如果同一工具、同一起始版本已有更新区间，后续检测到更高版本时，只更新该段二级标题的目标版本号和段落内容，不新增重复区间。
5. 如果 GitHub release body 缺失、为空或明显不足以判断变更，不要直接写成“无可追溯变更”；必须继续从以下维度补充获取版本更新信息，并在 `UPDATE.md` 中说明哪些来源有依据、哪些来源缺失：
   - 官方 docs / changelog 页面或文档仓库对应版本条目。
   - GitHub compare 区间。
   - 具体 commit diff 和变更文件列表。
   - migration manifest、upgrade manifest 或等价迁移元数据。
   - npm 包 metadata、tarball 内容、发布文件结构或本地包结构推断。
6. 评估是否需要修改本仓库规则时，不要只检查是否存在与上游同名的模板或配置文件；还必须用 release 中出现的关键概念、命令、配置项和兼容性关键词扫描以下本地文件，并在 `UPDATE.md` 的影响分析中说明命中结果和处理决定：
   - `AGENTS.md`
   - `kuno-workflow-onboard-skills/SKILL.md`
   - `kuno-workflow-onboard-skills/REFERENCE.md`
   - `kuno-workflow-onboard-skills/scripts/onboard.py`
   - `kuno-workflow-onboard-skills/templates/agents/AGENTS.global.md`
   - `kuno-workflow-onboard-skills/templates/agents/AGENTS.project.md`
   - `kuno-workflow-onboard-skills/templates/skills/**`
7. 如果 release 改动影响某个工具的使用边界、命令建议、配置禁用项、兼容性风险或迁移步骤，即使本仓库没有对应模板文件，也要最小化更新相关 AGENTS 或 Skill 规则。
8. 由 release 触发的 AGENTS 或 Skill 规则更新必须沉淀为长期通用规则，不要在长期执行规则里写入具体版本号、一次性版本区间或临时 release 叙述；版本号和依据保留在 `UPDATE.md` 的版本分析段落中。只有当规则本身必须表达明确兼容边界时，才允许写最低/最高版本要求。
9. 除非用户手动输入 `更新` 或 `update`，否则不要把 `UPDATE.md` 中的最新版本写回 `ENTRYPOINT.md`。

## 更新指令

当用户输入 `更新` 或 `update` 时：

1. 先读取 `docs/lessons.md`，并按命中情况读取 `docs/lessons/index.md` 或相关 topic，再继续执行更新流程。
2. 检查项目根目录 `archive/` 下已有的 `UPDATED-yyyy-mm-dd-index.md` 文件：
   - 以文件名中的 `yyyy-mm-dd` 作为归档日期。
   - 删除归档日期早于当前本地日期 14 天前的文件。
   - 只删除符合上述命名格式的归档文件；格式不匹配的文件不要删除，并在最终输出中说明。
3. 读取项目根目录下的 `UPDATE.md`。
4. 以 `ENTRYPOINT.md` 的 `## 0. 版本监控配置` 作为主数据源，将 `UPDATE.md` 中各工具章节记录的最新版本号写回该表格中对应工具的当前使用版本。
5. 同步更新 `ENTRYPOINT.md` 全文中同一工具对应的当前版本记录，包括“当前版本汇总”和各工具说明章节里的当前版本字段。
6. 不要误改历史对比版本、曾对比版本、release 区间、归档记录或示例文本中的版本号。
7. 将 `UPDATE.md` 重命名为 `UPDATED-yyyy-mm-dd-index.md`。
8. 将重命名后的文件移动到项目根目录下的 `archive/` 目录；如果目录不存在，则先创建。
9. 不要自行提交或推送变更；commit 和 push 只允许用户手动执行。
