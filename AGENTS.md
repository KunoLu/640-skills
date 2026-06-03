# AI Tools 项目规则

本仓库是 Codex 配置文件与 Skill 的摘录/同步源，不代表一个真实业务项目结构。本文件只保留本配置摘录仓库自身直接生效的补充规则；通用规则已迁移到 `agents/AGENTS.global.md`，真实项目根目录模板维护在 `agents/AGENTS.project.md`。

## Agent 规则文件路径

本配置集维护的 agent 规则文件路径如下：

- 根目录 `AGENTS.md`：保存本配置摘录仓库自身直接生效的补充规则，包括每日版本检查自动化和 `更新` / `update` 指令。
- `agents/AGENTS.global.md`：保存迁移后的全局规则文档。
- `agents/AGENTS.project.md`：保存迁移后的项目规则文档。

每日版本检查自动化如需读取、评估或修改 agent 规则，只能使用上述路径。不要再读取或修改根目录旧路径 `AGENTS.global.md` 和 `AGENTS.project.md`。

## Lessons 读取规则

本仓库的长期经验记录维护在 `docs/lessons.md`。

每次执行本仓库操作前，必须先读取 `docs/lessons.md`，理解其中与当前任务相关的经验后再继续。  
如果该文件不存在或不可读取，不要假装已读取；必须在最终输出中说明跳过原因。

## 本地同步规则

普通修改任务只更新本配置摘录仓库内的源文件，不要立即同步到本地 PC 的实际生效路径。

只有当用户主动输入 `同步` 或 `sync` 时，才执行本节同步流程。

同步触发后，只同步以下全局规则和全局 Skill：

| 源文件 | 本地目标路径 |
|---|---|
| `agents/AGENTS.global.md` | `/Users/lusonglin/.codex/AGENTS.md` |
| `skills/trellis-workflow/SKILL.md` | `/Users/lusonglin/.agent/skills/trellis-workflow/SKILL.md` |
| `skills/trellis-channel/SKILL.md` | `/Users/lusonglin/.agent/skills/trellis-channel/SKILL.md` |
| `skills/project-validation/SKILL.md` | `/Users/lusonglin/.agent/skills/project-validation/SKILL.md` |
| `skills/lessons-record/SKILL.md` | `/Users/lusonglin/.agent/skills/lessons-record/SKILL.md` |

同步要求：

1. 先读取源文件，确认路径正确。
2. 将源文件复制到对应本地目标路径。
3. 使用 `cmp -s` 或等价方式确认源文件与目标文件一致。
4. 在最终输出中说明已同步的文件和校验结果。

不要同步：

- `agents/AGENTS.project.md`

`agents/AGENTS.project.md` 是用于复制到真实项目仓库根目录 `AGENTS.md` 的项目级模板，只在具体项目需要时由用户手动落地或明确要求同步。

### 同步指令

当用户输入 `同步` 或 `sync` 时：

1. 执行上面的本地同步流程。
2. 不修改 `ENTRYPOINT.md` 版本号。
3. 不归档 `UPDATE.md`。
4. 不提交或推送变更。

mattpocock/skills 默认按官方文件原样使用，本仓库只在 AGENTS 模板中维护本地使用边界。不要在本仓库内安装、fork 或改写这些官方 Skill。

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
   - `agents/AGENTS.global.md`
   - `agents/AGENTS.project.md`
   - `skills/**/SKILL.md`
7. 如果 release 改动影响某个工具的使用边界、命令建议、配置禁用项、兼容性风险或迁移步骤，即使本仓库没有对应模板文件，也要最小化更新相关 AGENTS 或 Skill 规则。
8. 由 release 触发的 AGENTS 或 Skill 规则更新必须沉淀为长期通用规则，不要在长期执行规则里写入具体版本号、一次性版本区间或临时 release 叙述；版本号和依据保留在 `UPDATE.md` 的版本分析段落中。只有当规则本身必须表达明确兼容边界时，才允许写最低/最高版本要求。
9. 除非用户手动输入 `更新` 或 `update`，否则不要把 `UPDATE.md` 中的最新版本写回 `ENTRYPOINT.md`。

## 更新指令

当用户输入 `更新` 或 `update` 时：

1. 先读取 `docs/lessons.md`，再继续执行更新流程。
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
