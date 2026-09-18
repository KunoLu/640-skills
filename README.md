# SBTD Workflow 模板配置说明

本仓库是 Codex / OMP 配置、Agent 规则模板、Skill 模板和 onboard 自动化的摘录/同步源，不代表一个真实业务项目结构。当前处于v2未发布切换阶段：规则载荷与catalog已切换，完整运行时仍单独实施和验收。

> **未发布边界（v2 分阶段交付中）**：canonical payload 已切换为 14 bundled / 19 external Skills；项目 setup 已改为按需 SBTD 状态检查，不安装或初始化 Trellis。Graft、host 接线、任务操作和旧项目迁移仍在 P1 分阶段实施；developer 身份按需建立已由 P1-19 的显式 `--developer` 入口提供（见下），旧身份迁移仍须另行明确授权。不把本开发分支当作完整 v2 发布部署到真实项目。旧数据保留，迁移必须另行明确授权。

P1-01 的内部参数／交换契约不代表 migration/recovery 已公开可执行。P1-02 的项目检查只验证选中状态的形状与 containment，不代替完整任务恢复或验收。目录复制／`npx skills add` 不运行 pip；调用契约或已有 task 校验前，用实际解释器执行 `python -m pip install -r /path/to/installed/sbtd-workflow-onboard/requirements.txt`，准备 jsonschema 与 PyYAML。缺依赖明确阻断相关校验，不影响帮助和纯参数解析；schema/hash 合法不证明授权或真实执行。

P1-03 将 Graft CLI 检测与明确确认的安装独立实现：`check`/`plan` 只报告本地能力，`install-graft --json` 展示计划，确认后才使用 `install-graft --yes --json`。固定 `@nanonets/graft@0.18.0`、Node >=20，验证包完整性/native启动及 telemetry 持久关闭；这不代表 graph、MCP、host 接线或完整 v2 已通过。

P1-17 在 Onboard `scripts/` 内实现任务状态 Python 库（`sbtd_task_document.py`、`sbtd_task_state.py`）：task.md 是唯一状态事实源，`.sbtd/active-task.json` 只是书签；`TaskStore` 的 create／inspect／select／transition／set_mode／resume／reopen／protect_local_state／promote／archive 由 host-native 调用，不注册新全局 CLI、daemon、journal 或 `onboard.py` 子命令。Markdown 结构识别使用声明依赖 markdown-it-py>=4,<5 的 CommonMark token（parse-only、不渲染、不联网，Python>=3.10）。提升／归档为两阶段：先准备并验证目标候选与引用，单独确认后原目录原子退役进 `.sbtd/task-originals/` 保留；候选复制只用受保护临时区并在结束后清理，目录内其他逻辑任务必须 `include_tasks` 逐个授权，路径嵌套不代表所有权。非 Git 项目 branch 为 null，首次窄保护只追加 `/.sbtd/`；部分失败如实报告已完成步骤，helper 或其声明依赖未安装时明确停止写入，不得假装持久化已执行。这不代表 Windows、host 路由、身份建立或真实迁移已完成，也不代表全量验证或发布已通过。

P1-18 在同一 `scripts/` 内增加确定性路由与受保护交接库（`sbtd_task_routing.py`、`sbtd_handoff.py`），同样不注册新全局 CLI、daemon、journal 或 `onboard.py` 子命令。`TaskRouter` 只把 host 已明确的事实（`RouteRequest` 的 `new`／`continue`／`question` 意图、显式 mode、推荐回应 `accept`／`keep`、只读与确认标记）转成确定性的 `RouteDecision`（`ready`／`needs-task-choice`／`needs-mode-choice`／`needs-mode-decision`／`needs-branch-choice`／`needs-persistence-confirmation`／`persistence-failed`／`blocked`），不是自然语言意图分类器；续作先唯一确定 task 再决定 mode，拒绝建议以结构化 `mode_note` 记录并按风险标识去重，保存失败保持会话内选择并如实标记未持久化，不回退旧 mode。`TaskStore` 新增公开的 `current_binding()`／`recovery_candidates()`／`rebind(...)`：跨分支恢复要求正确 worktree、明确重绑定或只读选择；`rebind` 必须携带 `expected_branch`、`reason`、`evidence` 并经确认，只更新绑定及事件，不 checkout、不 stash、不重置 blocked 恢复历史。`HandoffStore` 只在真实 pause／context-switch／branch-switch／context-pressure／manual 续接事件触发，计数或进入 checking 不触发；task／session 自动交接退出独立锁存且 session 优先，手动请求不清除退出；`save` 返回 `saved`／`suppressed`／`conversation-only`／`branch-conflict`／`unprotected`／`unchanged`／`pending-confirmation`／`needs-redaction` 之一，写入前核对 `docs/handoffs/` 整棵窄保护与 tracked 状态且必须显式 `redaction_confirmed` 才落盘；文件名取完整逻辑任务 ID UTF-8 字节的小写 hex（大小写不敏感文件系统上仍无冲突且可逆），同任务同内容快照（仅 `created_at` 除外）不重写、跨日不单独触发；主动提醒只取 7 天内按任务去重、root／分支匹配且未完成任务的快照，旧快照仍可显式手动恢复但绝不改写 task；分支不匹配拒绝写入，handoff 永远不是 mode／status 事实源。Agent 是否真实先推荐暂停、解释风险并按模式执行完整方法仍由既有 Skill 规则与 P1-15 的真实 host 证明负责；本项不代表 Windows、host 接线、自动 SessionStart 恢复、真实迁移、全量验证或发布已通过。

P1-19 在 `scripts/` 内增加按需 developer 身份库（`sbtd_identity.py`），同样不注册新全局 CLI、daemon、initializer 或身份数据库。`DeveloperStore(root, read_only=False)` 提供只读 `resolve()`／`plan(name)` 与确认门控的 `ensure(name, confirmed=False, protect=False)`，统一返回冻结 `IdentityResult`（status／name／source／path／first_write_eligible／topology／reason／needs_protection／completed_steps，可 `dataclasses.asdict` 导出）。本地 `.sbtd/developer` 合法值（UTF-8、单条 `name=`、`^[a-z0-9]+$` 原样匹配单一 `validate_developer_name`）直接胜出且不再查 Git；仅本地确实缺失后才核验真实 Git 根、git-dir/common-dir 与 NUL 分隔 worktree registry，已验证 linked worktree 只读同仓主 checkout 当前身份、不复制回本地；现存异常（重复声明、非法值、错误类型、symlink、不可读或父路径不安全）是 conflict 而非缺失，Git 未知或不可用是 blocked 而非非 Git 证明；不从 Git／OS／环境／历史目录猜作者，普通 resolve/plan 不读旧 `.trellis/.developer`。首次建立只允许正常缺失目标：窄 `/.sbtd/` ignore 保护与名字授权分开确认，仅写 `name=<name>\n` 并回读验证，同名幂等、异名 conflict、并发胜者不覆盖、失败如实返回 completed_steps。`onboard.py` 仅经显式 `--developer <name>` 消费：`check`／`plan` 只读并在单 JSON 中展示逐项目 `developerPlan`（请求名、来源、目标、状态、needsProtection 等），conflict／blocked／needs-* 或无项目范围时 exit 2、绝不默认 cwd 或 HOME；`init`／`reset`／`init-projects` 要求 `--developer` 与 `--yes` 同现，在任何全局或项目写入之前完成全批次身份 preflight，冲突先于副作用拒绝，写入后身份失败 exit 5 且保留部分结果；无 `--developer` 行为完全不变，reset 不覆盖既有身份。根安装器本次不加 flag，全量转发仍归 P1-07／P1-08；旧身份真实迁移仍是独立 P1-12 门，不因本 helper 宣称迁移完成。这不代表 Windows、真实 host、全量验证或发布已通过。

显式身份初始化在脚手架完成后保留实际 `operationResults`；后续身份失败仍以单份 JSON 报告逐项目结果、写后 `sbtdProjectSetup`、备份和未验证项，不冒称回滚。项目目录中途不可用会结构化报告，不丢弃此前已成功的项目。


下面是旧v1工具基线，仅用于理解本文标注的过渡实现，不是v2已完成清单：

```text
Codex / OMP + GitNexus + Trellis + Chrome DevTools MCP + Playwright + Maestro
```

其中 Chrome DevTools MCP 负责 Web 运行时诊断，Playwright CLI 负责 Web 可重复回归，Maestro 负责移动 App E2E 和可选跨端 smoke。bundled `web-ui-autotest-generator` 是可选专项分支，只在需要把 Web UI 回归路径固化为仓库内 Playwright 测试资产时启用；`shadcn` 是 shadcn/ui 项目的可选 external Skill，用于组件、registry、preset 和 CLI 工作流；`seo-geo` 是 bundled 的公开网站、落地页、文档站和营销页 SEO/GEO 搜索可见性检查分支；`maestro-mobile-e2e` 负责把 Mobile / Hybrid BDD 场景固化为仓库内 Maestro flow 资产。API、Web 和 Mobile / Hybrid 测试都以 BDD `.feature` 作为行为 SOT；前后端分仓或链路不完整时，先确认 contract、环境、账号、数据、设备和选择器事实，再决定 full-stack、contract-backed、mock-backed、app-mocked、smoke-only 或 blocked。

Codex plugin / connector、remote plugins、ChatGPT-hosted MCP 和 `tool_search` 属于 Agent 侧工具发现和授权能力，不是项目依赖。模板要求先确认当前会话实际暴露 callable tool，再依赖对应能力；catalog / marketplace / 本地远端版本展示只作为候选信号，session auth、OAuth、cookies 和 tokens 不写入仓库、日志、截图、报告或示例配置。

`rtk` 和 `caveman` 是上下文 / token 效率层，不是验证工具。`rtk` 作用于 shell / terminal 命令输出，普通非报告型命令默认优先作为命令前缀；unit / API / Playwright / Maestro 等报告型测试先评估缓存与文件写入风险。`caveman` 作用于 Agent 回复输出，安装后只表示可用，不会立即进入持久压缩模式。同一主要目标达到 3 次中间状态更新、5 个独立工具结果、长任务 / 上下文压力或重复自动化 / review / 验证轮次中的任一条件时，`autoLiteEligible` 单调锁存为 true；下一条普通重复状态必须进入任务级 `auto-lite`，不再附加主观资格判断。

自动生命周期由全局 AGENTS 规则负责，external `caveman` Skill 只负责手动模式的表达风格、强度和退出。自动模式不会进入 `full`、`ultra` 等更激进等级，也不改变代码、工具、测试、验证和工作流决策。安装 / 权限 / 破坏性操作确认、安全风险、需求与 review gate、长期文档、失败与剩余风险、最终验证报告和最终答复仍保持完整输出；保护区只覆盖当前回复，不清除计数、`autoLiteEligible` 或 `autoLiteActive`，下一条普通重复状态直接恢复且不重复首次提示。

`normal mode`、`stop caveman`、`恢复完整输出`、`不要压缩` 和 `本任务不要自动压缩` 会立即恢复正常输出并在当前任务内禁止自动重入；只有用户明确说 `本任务恢复自动压缩` 或 `重新启用自动压缩` 才清除任务级退出，原有计数和资格继续保留。手动 `/caveman` 不清除任务级或会话级自动退出；`本会话关闭自动压缩` 只能由 `本会话重新启用自动压缩` 清除。

只有用户建立新的主要目标时才重置任务级计数、资格、激活和退出状态；`继续`、`确认`、授权、状态询问、故障恢复和同一目标的补充不得重置。context compaction、历史归档、恢复同一 session 或 handoff 也保持状态。若 runtime 显式配置 `off`，自动和手动模式都禁用；没有配置接口或配置缺失时按 auto 处理。

`caveman` 已安装的 workflow Skill payload 由正常 `init` / `reset` 按钉版 `v*` installer / skill 基线维护。只有受管 family 的目录集合与 payload 内容指纹全部匹配已知版本时，才判定为 `current` 或可升级的旧版；仅核心文件匹配不够。部分安装、混合版本或自定义内容只报告、不覆盖；异常核心也不能授权覆盖未知 sibling。合法升级保留备份，可替换的非 symlink 异常核心在不存在未知 companion 时修复。

替换与备份仅限 Onboard 全局目录里的 `caveman`、`caveman-*`、`cavecrew`、`cavecrew-*`；更宽的 `caveman*` / `cavecrew*` 前缀只用于 symlink fail-closed 侦测。不升级 hooks、statusline、plugin 或 extension。文本报告保留拒绝原因、备份路径和恢复错误。版本监控只提示 `v*` tag 差异，人工评审完整 family 与 installer / hook 行为后，才在同一改动中更新 pin/ref/core hash/family 指纹及测试。

`i-have-adhd` 是同一对话输出层上的结构塑形 Skill，与压缩无关：它把回复塑形成行动优先的可扫读结构（首行即下一步行动、多步任务编号、每轮重述状态、结尾一个具体下一步、列表不超过 5 项）。它作为第 19 个 required external Skill 随 init/reset 自动安装，启用为会话级 opt-in：只有用户说 `/i-have-adhd`、`adhd mode`、`ADHD 输出` 或声明 ADHD 输出偏好时才启用，`stop adhd mode` 仅退出 `i-have-adhd`；`normal mode` 与 caveman 共享、同时退出两者；没有自动模式，不得自动激活。与 caveman 叠加时 caveman 管压缩强度、`i-have-adhd` 管输出结构。输出契约保护区（最终输出、review gate、失败与剩余风险、最终验证报告）保持完整结构，不受其“无复盘”规则影响；时间估计服从 harness 规则；证据不足的错误原因必须标注“假设”并走 `diagnosing-bugs` 求证，不得把推测写成确定原因。

## 安装及使用说明

### 1. 使用 `npx skills` 全局安装 Onboard Skill

只建议把 `sbtd-workflow-onboard` 安装到用户级全局 Skill 目录，使同一用户下的 Codex 会话都能发现它；不建议安装到单个项目目录，也不要省略 `--global` 后把 bootstrap Skill 变成项目依赖。

```bash
npx --yes skills@latest add \
  KunoLu/640-skills@sbtd-workflow-onboard \
  --global \
  --agent codex \
  --yes \
  --copy
```

其中 `skills@latest` 只表示使用 npm 上最新的 `skills` CLI；`KunoLu/640-skills@sbtd-workflow-onboard` source 没有 `#ref` 时，CLI 会读取仓库默认分支（当前是 `main`）的最新 commit，并不会自动选择最新 tag。需要固定 Skill 内容版本时，使用 `KunoLu/640-skills#<tag>@sbtd-workflow-onboard` 格式，把 Git tag 放在 repository shorthand 与 `@skill` filter 之间：

```bash
npx --yes skills@latest add \
  'KunoLu/640-skills#v1.0.0@sbtd-workflow-onboard' \
  --global \
  --agent codex \
  --yes \
  --copy
```

安装后检查 Codex 的全局 Skill：

```bash
npx skills list --global --agent codex
```

这一步只安装自包含的 `sbtd-workflow-onboard` Skill，不会自动执行 `scripts/onboard.py`，也不会安装 Trellis、GitNexus、其余 bundled / external Skills、写入项目 AGENTS 或初始化项目。私有仓库应使用本机 Git 已可认证的 `git+ssh://` source，不要在命令、仓库、日志或报告中写入凭据。

流程判定图：[npx skills 全局安装 Onboard Skill](docs/assets/npx-skills-global-onboard-install.md)。

### 2. 使用 Onboard Skill 执行 `init`

安装成功后，在 Codex 中明确调用该 Skill，并提供目标平台和一个或多个项目绝对路径。多个路径使用英语逗号 `,` 分隔；每个路径必须已存在且是目录，重复路径规范化后只处理一次。普通项目不要求预先建立身份、task 或 bootstrap。

```text
请使用 sbtd-workflow-onboard Skill，对 /abs/project-one,/abs/project-two 执行 init 初始化。
目标平台是 codex；多个项目路径以英语逗号分隔。
先输出 plan --json，确认计划后执行 init，并逐项目汇总 AGENTS、.gitignore 和 SBTD 状态。
```

Skill 会定位自身的全局安装目录并运行对应脚本。需要手动执行底层 CLI 时，先把实际全局 Skill 路径赋给变量；下面的路径只是示例，应以本机 `npx skills list --global --agent codex` 和 Skill 检测结果为准：

```bash
SBTD_ONBOARD_DIR="$HOME/.agents/skills/sbtd-workflow-onboard"
python "$SBTD_ONBOARD_DIR/scripts/onboard.py" plan \
  --platform codex \
  --projects-root /abs/project-one,/abs/project-two \
  --json
python "$SBTD_ONBOARD_DIR/scripts/onboard.py" init \
  --platform codex \
  --projects-root /abs/project-one,/abs/project-two \
  --yes
```

流程判定图：[Onboard Skill 执行 init](docs/assets/onboard-skill-init.md)。

### 3. 使用 Onboard Skill 执行 `reset`

后续需要更新或重置全局工具、Skills 和一个或多个项目配置时，再次明确调用同一 Skill。`reset` 的多个项目路径同样使用英语逗号分隔：

```text
请使用 sbtd-workflow-onboard Skill，对 /abs/project-one,/abs/project-two 执行 reset。
目标平台是 codex；多个项目路径以英语逗号分隔。
先输出 plan --json，保留已检测到的安全配置和 tier，再执行 reset 并逐项目汇总结果。
```

对应的底层命令示例：

```bash
SBTD_ONBOARD_DIR="$HOME/.agents/skills/sbtd-workflow-onboard"
python "$SBTD_ONBOARD_DIR/scripts/onboard.py" plan \
  --platform codex \
  --projects-root /abs/project-one,/abs/project-two \
  --json
python "$SBTD_ONBOARD_DIR/scripts/onboard.py" reset \
  --platform codex \
  --projects-root /abs/project-one,/abs/project-two \
  --yes
```

`reset` 不是迁移或数据清理：继续遵守路径、身份、备份和事务边界，保留 task、developer、spec、lessons、handoff 及旧 `.trellis` 数据；不默认生成这些可选产物。

流程判定图：[Onboard Skill 执行 reset](docs/assets/onboard-skill-reset.md)。

### 4. 使用 `--init-projects` 只初始化项目

`--init-projects` 是 project-only 模式：只处理所选项目的 AGENTS、模板 `.gitignore`、只读 SBTD 状态/bootstrap 检查，以及适用的 Playwright / React Bits 条件项；不检测、安装、更新或配置全局 Agent CLI、工具、Skills、AGENTS 或 MCP，也不需要 Trellis。

`--init-projects` 自身接收一个或多个已存在的项目绝对路径，多个路径同样用英语逗号分隔；它与普通模式的 `--projects-root` / `--action` 互斥。macOS / Linux 示例：

```bash
bash install.sh \
  --platform codex \
  --init-projects /abs/project-one,/abs/project-two \
  --yes
```

Windows PowerShell 示例：

```powershell
pwsh -File .\install.ps1 `
  -Platform codex `
  -InitProjects "C:\work\project-one,C:\work\project-two" `
  -Yes
```

通过已安装 Skill 调用同一 project-only 能力时，可以这样描述：

```text
请使用 sbtd-workflow-onboard Skill，以 init-projects project-only 模式初始化
/abs/project-one,/abs/project-two。多个项目路径以英语逗号分隔；
不要检查或修改任何全局 Agent CLI、工具、Skills、AGENTS 或 MCP。
```

对应底层命令：

```bash
python "$SBTD_ONBOARD_DIR/scripts/onboard.py" init-projects \
  --platform codex \
  --projects-root /abs/project-one,/abs/project-two \
  --yes
```

流程判定图：[--init-projects 只初始化项目](docs/assets/onboard-init-projects.md)。

### 5. 使用安装脚本进行交互式安装

已克隆本仓库时，也可以运行根目录安装脚本进入完整交互式流程：

```bash
bash install.sh
```

```powershell
pwsh -File .\install.ps1
```

交互式流程先明确平台、模式、项目根及 AGENTS 选择；普通模式可以先只读探测 Agent CLI，但两安装器都会在任何全局安装、MCP 写入或 Playwright / React Bits 安装之前执行完整 `check-projects` 前置检查。该检查包含 SBTD 状态、scaffold 目标和已有保留数据保护，并传递 `--skip-project-agents` 的实际范围。通过后才进入既有安装流程；Python 写入时再次复验。project-only 仍不做全局操作。Bash 保留原始交互流，EOF 明确失败，不循环提示。


这里的目标 Agent 平台只选择 CLI 与 MCP adapter，不会选择全局 AGENTS 目标。除非显式传入 `--global-agents-path` / `-GlobalAgentsPath`，正常模式始终把 Codex 全局规则模板写入解析后的 `$CODEX_HOME/AGENTS.md` 或 `~/.codex/AGENTS.md`。若用户主目录已存在 `.omp` 目录（POSIX `~/.omp`，Windows `%USERPROFILE%\.omp`），`init` / `reset` 会把同一模板备份后覆盖写入 `~/.omp/agent/AGENTS.md`；不存在则跳过且不创建 `.omp`。`--global-agents-path` 只覆盖 Codex 目标，不取消 OMP 附加写入。project-only 不写任何全局 AGENTS。

根安装器的 `--yes` / `-Yes` 确认 yes/no 提示并跳过最终执行确认，也会确认适用的可选安装提示；不猜测无默认值的选项，不授权迁移或绕过状态冲突。非交互普通模式需提供 `--platform`、`--projects-root`、`--action init|reset`；project-only 提供 `--platform`、`--init-projects`；React Bits 等适用输入仍需明确。

## 仓库定位

本仓库维护以下源文件：

| 路径 | 用途 |
|---|---|
| `ENTRYPOINT.md` | 由 Git 追踪的版本监控配置和工作流总入口，也是版本检查与 `update` / `更新` 的可恢复基线。 |
| `AGENTS.md` | 本机可选的仓库补充规则；根 `.gitignore` 忽略，不进入远程 `main`。新 clone 不包含该文件，缺失时不得作为操作前置条件。 |
| `README.md` | 当前工作流的详细说明文档。 |
| `README.html` | 当前工作流的静态 HTML 说明页。 |
| `CHANGELOG.md` | 从 `v1.0.0` 起按 Git tag、中文、最新版本在前的顺序维护发布变更。 |
| `LICENSE` | 本仓库原创内容适用的 Apache License 2.0 完整许可文本。 |
| `sbtd-workflow-onboard/LICENSE` / `NOTICE` | 自包含 Onboard Skill 的原创内容使用与仓库根一致的 Apache License 2.0，并声明 `Copyright 2026 KunoLu`；文件随公开安装和本地同步一起分发。 |
| `sbtd-workflow-onboard/templates/skills/*/LICENSE` / `NOTICE` | 除第三方衍生的 `seo-geo` 外，其余 bundled Skill 的原创内容均使用同一 Apache License 2.0 和 `Copyright 2026 KunoLu` 声明；既有第三方来源说明继续保留。 |
| `sbtd-workflow-onboard/templates/skills/web-ui-autotest-generator/LICENSE` / `NOTICE` | 个人独立实现的 bundled `web-ui-autotest-generator` 使用与仓库根一致的 Apache License 2.0；`NOTICE` 声明 `Copyright 2026 KunoLu`，两份文件随独立安装的 Skill 一起分发。 |
| `sbtd-workflow-onboard/templates/skills/seo-geo/LICENSE` / `NOTICE` | 第三方衍生的 bundled `seo-geo` 保留 ReScienceLab/opc-skills 的 Apache License 2.0；`NOTICE` 固定上游 source、revision 和本地修改范围，`Copyright 2026 KunoLu` 仅适用于本地修改。 |
| `install.sh` | macOS / Linux 交互式安装入口，直接以 `sbtd-workflow-onboard` 目录作为 `source-root`。 |
| `install.ps1` | Windows PowerShell 交互式安装入口，参数语义与 `install.sh` 对齐。 |
| `docs/lessons.md` | Lessons 必读短入口；执行仓库操作前必须先读取。 |
| `docs/lessons/index.md` | Lessons 完整索引，按 tags、适用场景和详情路径检索。 |
| `docs/lessons/topics/**` | Lessons 完整详情，按当前任务命中后读取。 |
| `docs/prd/knowledge-base-integration-prd.md` | P1 / P1.1 已实现能力与 P2 Evidence Store / PR Gate 实施方案。 |
| `docs/assets/npx-skills-global-onboard-install.md` 等 5 份流程判定图 | Onboard 安装 / init / reset / init-projects 与 SBTD 工作路径 mermaid；从「安装及使用说明」和「工作流主线」跳转。 |
| `prompts/automations/sbtd-workflow-tools-version-check.md` | Orca `SBTD Workflow Tools Version Check` 的版本化 prompt 源；每次仓库代码改动后评估是否需要调整，只有执行 `sync` 时才与 live automation 比较并按需同步。 |
| `sbtd-workflow-onboard/` | onboard Skill 目录；普通 `sync` 时会作为完整 Skill 同步到 `/Users/lusonglin/.agent/skills/sbtd-workflow-onboard/`。 |
| `sbtd-workflow-onboard/catalog.json` / `catalog.schema.json` | Bundled Skill、external Skill 上游源与模板源路径目录，以及对应 Draft 2020-12 结构契约。 |
| `sbtd-workflow-onboard/SKILL.md` | onboard Skill 入口说明。 |
| `sbtd-workflow-onboard/REFERENCE.md` | onboard、安装、检测和工具配置参考。 |
| `sbtd-workflow-onboard/scripts/onboard.py` | init、reset、安装、检测与按需 SBTD 状态/bootstrap 报告。 |
| `sbtd-workflow-onboard/templates/agents/AGENTS.global.md` | 全局 Agent 规则模板。 |
| `sbtd-workflow-onboard/templates/agents/AGENTS.project.md` | 项目级 Agent 规则模板，不在普通 sync 中同步。 |
| `sbtd-workflow-onboard/templates/skills/**` | 全局 Skill 模板目录，包含 `SKILL.md`、`references/`、`scripts/`、`assets/` 等。 |
| `sbtd-workflow-onboard/templates/project/.gitignore` | 新项目模板 `.gitignore`。 |

仓库编排按产物类型分层和自包含 Skill 目录：版本化自动化 prompt 位于 `prompts/`，Onboard 运行实现位于 `scripts/`，可安装载荷保留在 `templates/`，第三方 fallback 保留在 `assets/`。`templates/` 不提升到 Onboard 根目录，因为它明确区分“安装器实现”和“将被复制到目标位置的模板载荷”。

`ENTRYPOINT.md` 必须由 Git 追踪，保存版本检查和 `update` / `更新` 使用的 authoritative baseline；新 clone 必须直接取得它。根 `AGENTS.md` 是本机可选补充规则，已加入根 `.gitignore` 并从 Git 索引移除，不进入远程 `main`；新 clone 不包含该文件，工作树缺失时继续使用已追踪规则，不得把它的存在当作 Gate。

本配置源仓根 `.gitignore` 独立采用以下七行，不复制业务项目模板；新本地状态／handoff／Graft产物被保护，共享任务、规范、lessons和`ENTRYPOINT.md`仍可追踪：

```gitignore
.DS_Store
/.sbtd
/docs/handoffs
/graft
/.graft
__pycache__/
AGENTS.md
```

四条新规则仅锚定仓库根，覆盖同名目录、文件和symlink，不影响`packages/graft`等业务子目录。旧`.trellis/`、`.gitnexus/`不再由根文件保护；切换已有checkout前先核对磁盘与Git索引残留，存在未知或敏感内容时先保全并确认处置，不盲删或直接提交。ignore不会取消已tracked状态；这不是业务项目迁移或全局配置同步。

回滚这项规则也要先核对四个新本地根与Git索引；若已产生本地数据，先在仓库外私有保全并确认处置，在安全迁出或授权方案落实前保持保护，不能仅恢复旧文件就让这些内容暴露为可提交文件。

`docs/lessons.md`的旧五行摘要以及topics里的三／四／五行记录保留原文，均按当时状态理解，不覆盖此处现行七行契约；不得为了更新验收规则改写历史lesson。

`ENTRYPOINT.md` 的版本监控表启用 OMP：监控对象是 npm `@oh-my-pi/pi-coding-agent`（CLI `omp`），GitHub 源为 `can1357/oh-my-pi` 的对应 `v<package-version>` tag/Release。定时版本检查仅为检测到可分析新版本的启用工具（含 OMP）生成或刷新 `UPDATE.md` 区间，无新版本不写 `当前版本 -> 当前版本`；只有手动 `update` / `更新` 才写回基线。本机 `omp --version` 只作交叉校验，不得覆盖表格版本。

普通修改任务只更新本仓库内的源文件。每次仓库代码或工作流规则改动后，都必须评估 `CHANGELOG.md`、`README.md`、`README.html` 和版本化 automation prompt 是否需要同步调整。只有用户明确输入 `sync` 或 `同步` 时，才把允许列表中的全局规则和 Skill 同步到本地生效路径；sync 允许列表明确包含 bundled `web-ui-autotest-generator` 完整目录到 `/Users/lusonglin/.agent/skills/web-ui-autotest-generator/` 的映射。required external Skills `ponytail`、`ponytail-review`、`ponytail-audit`、`ponytail-debt` 与 `i-have-adhd` 不得作为同步表 `cp` / `rsync` 行；sync 在复制 Onboard 后必须用已同步的 `scripts/onboard.py install-external-skills --skills ponytail,ponytail-review,ponytail-audit,ponytail-debt,i-have-adhd --scope global --source auto --global-skills-dir /Users/lusonglin/.agent/skills --yes` 从 stable mirror 安装，并确认 5 个 `SKILL.md` 存在。随后比较版本化 prompt 与 Orca `SBTD Workflow Tools Version Check` 的完整内容，仅在存在差异时同步到 live automation 并报告结果。`update` / `更新` 只处理版本写回和归档，与版本化 prompt 和 live automation 无关；`AGENTS.project.md` 不在普通 sync 范围内。

## 任务路由与 lessons 身份（v2 canonical 模板）

本节描述当前模板载荷里的 canonical 规则，来源是 bundled `sbtd-task`（`sbtd-workflow-onboard/templates/skills/sbtd-task/SKILL.md` 及 `references/`）、v2 全局 / 项目 AGENTS 模板和 bundled `lessons-record`。这些规则文本已随载荷切换生效；在真实 host 上的完整运行证明仍属 P1 范围。

**共同路由**：开始工作前先识别任务、授权项目根、分支和只读约束。执行模式优先级：本次明确用户选择 > 同一任务已确认 / 有效记录 > 真正的新任务使用 `default`；旧任务缺模式、记录损坏或有多个合法恢复候选时必须询问，不按 mtime 或旧 handoff 猜测。认为另一模式更合适时，先说明当前模式、建议与原因、以及保持原模式的选项，并暂停实质执行等待用户决定；被拒绝后按原模式继续，没有新实质风险不重复劝升。纯问答和明确只读的任务只在会话中保留模式，不创建或更新 task、active、handoff、身份或 ignore 文件。P1-18 的 `TaskRouter`（`sbtd-workflow-onboard/scripts/sbtd_task_routing.py`）把这套规则落成确定性库调用：它只接收 host 已明确的意图与选择并返回 `RouteDecision` 状态（含 `needs-task-choice`／`needs-mode-decision`／`needs-branch-choice`／`needs-persistence-confirmation`／`persistence-failed`），不做意图分类；任务分支不匹配时只能选正确 worktree、明确 `rebind`（不 checkout / stash）或只读继续。

**三种执行模式**：

| 模式 | 工作契约 |
|---|---|
| `default` | 按需调查、实现、聚焦验证并交付；只保留必要的本地任务记录，不机械加载全部门禁。 |
| `lite` | 使用短清单和共享短任务卡，只产生必要产物；不机械补齐 PRD / design / implement 文件。 |
| `strict` | 加载 `references/strict.md`，完成适用的 before-dev / check / finish-work 义务；真正必需证据缺失时不得报通过。 |

用户明确要求的产物、项目原有规范和安全 / 真实性边界在所有模式都不降级；`default/lite/strict` 与 caveman / ADHD 等输出样式互不相干。任务持久化、恢复、handoff、方法路由、表达样式和工具边界分别按需读取 `references/state.md`、`handoff.md`、`methods.md`、`presentation.md`、`tooling.md`；任务数据结构见 `references/task-data.schema.json`。普通 default 任务的本地记录位于 `.sbtd/tasks/<id>/task.md`，lite / strict 或明确共享任务位于 `ai/tasks/<id>/task.md`；`.sbtd/active-task.json` 只存当前任务引用，handoff 只在真实暂停 / 切换 / 上下文压力或手动请求时由 `HandoffStore`（`sbtd-workflow-onboard/scripts/sbtd_handoff.py`）写入受保护的 `docs/handoffs/`，状态计数不触发，旧快照不覆盖当前 task。

**lessons 身份来源**：只有真正要写入长期 lesson 时才解析写入者身份，纯读取不建立身份。唯一自动来源是当前项目 `<repo-root>/.sbtd/developer` 中唯一的 `name=`：本地合法身份优先；仅当本地文件确实缺失、且当前 checkout 已验证为同仓 linked worktree 时，才只读主 checkout 的同一文件，不复制回本地。现存但异常的身份文件（重复声明、非法内容、错误类型、不可读、symlink 或路径不确定）是冲突而不是缺失，必须停止解析，不得绕过。允许来源都确实缺失时，说明将建立的本地路径并向用户要名字；不得从 Git / OS / 环境变量 / 历史 workspace 目录或 marker 推断。分隔名必须匹配 `^[a-z0-9]+$`，原样使用，不小写化、不去标点、不音译。旧 `.trellis/.developer` 只在用户明确授权旧项目身份迁移时按 `lessons-record` 的 `references/identity-migration.md` 处理，不再是日常身份 fallback。该链的可执行实现是 Onboard `scripts/sbtd_identity.py` 的 `DeveloperStore`（`resolve`／`plan`／`ensure`，见上方 P1-19 段）；没有显式名字不建立身份，reset 不覆盖既有身份。

## 工作流主线

模板遵循“项目事实优先、工具强证据启用、修改最小可验证”的原则。

以下流程与「关键边界」中涉及 Trellis 安装、bootstrap 检测、`.trellis/**` 和 host 集成的内容描述的是**现有过渡实现**（v1 CLI 行为），不是已验证的 v2 行为；canonical 模板的任务路由见上一节，完整 v2 切换由 P1 交付。其中提及的 Channel 仅记录旧 CLI guard，不构成当前路由或对新项目的执行建议。


```text
读取 `docs/lessons.md` 短入口，并按需读取 lessons index / topic
  -> 澄清需求与 SBTD 判断
  -> Trellis / GitNexus / Skill 按证据启用
  -> 实现或配置修改
  -> 项目原生验证
  -> BDD / Web / Mobile / 发布风险补充验证
  -> 最终报告状态、跳过原因、剩余风险
```

全路径判定图：[SBTD 支持的工作路径](docs/assets/sbtd-workflow-paths.md)。

关键边界：

- Trellis 负责复杂任务生命周期、任务产物和阶段门禁，不强制用于所有小任务。
- 当前 Onboard 不安装／调用 Trellis，也不再接受其 username、platform 或 skip 参数；没有 `.trellis/` 不构成初始化缺失。已有旧数据需显式迁移，不能当作 SBTD task 直接接管。
- Trellis CLI 升级后，已有 `.trellis/` 的项目先运行 `trellis update` 刷新生成脚本和 filesystem-safety guard；如果更新涉及 SessionStart、PreToolUse 或其他 hook 配置，先重启对应 Agent host / IDE，再验证新会话身份或 hook 行为。对 uninstall、archive、task start / set-*、Channel 名称等删除 / 移动 / 路径解析操作，不绕过 dirty-data、manifest ownership、safe-name 和 active-task pointer containment guard。升级后不要假设 `trellis update` 会改写既有 session pointer；越权任务路径按无任务处理。
- `.trellis/config.yaml`、`.trellis/workflow.md` 和 task artifacts 只定义共享 workflow gate，不标识运行平台。当前 host 与其专属生成资产决定本次执行：Codex 使用 `.codex/**`，OMP 使用 `.omp/**`；二者共存时按当前 host 选择，纯静态文件不足时标记 unknown。仅当前 host 为 Codex 且 `.codex/**` 集成可用时解释 `codex.dispatch_mode`：`auto` 由主会话协调并按职责调度 role subagent，显式 Inline 与非法显式值的 fail-closed fallback 也仅属于 Codex。仅当前 host 为 OMP 且 `.omp/**` 集成可用时使用 OMP `task` worker 和生成的 agent 定义，不得套用 Codex dispatch。单个 platform role subagent 不构成 Channel 触发，Channel 仍须用户明确请求或 preflight 后确认；每项变更职责只允许一个写入执行者，用户请求的独立只读复核可并行。
- Codex remote plugins、connectors 和延迟加载工具以当前会话的 `tool_search`、工具列表或 MCP 可见性检查为准；候选 catalog 不等于已授权或已可调用。项目级 marketplace 无效不得否定其余有效 plugin；可选 MCP 首轮工具缺失可能只是启动宽限期。内置 planning / `update_plan` 默认关闭，以当前会话工具列表为准。package-style MCP 名称（含 `:`, `@`, `/`, `.`）合法，不要改写。
- GitNexus 只有在 MCP 可用且项目索引有效时使用，作为影响分析和变更检测辅助。
- GitNexus 的 PDG、taint、trace、多分支索引和不同 MCP transport 属于显式 opt-in 能力；使用时必须记录模式 / 分支并回到源码与测试复核。CLI 升级若改变 receiver / import / interface 解析，必须重新 `gitnexus analyze` 后再依赖索引。不要把 `gitnexus watch` 当成会启动 watcher 的命令，也不要默认启动 `analyze --watch` 或 `auto-sync`。MCP allowlist 未覆盖时 GitNexus MCP 对该仓库不可用，不得当作 MCP 可读；fail-closed 只读时不走 MCP 写入；二者都不跳过 CLI 重新 analyze。
- Skill 按场景调用，不替代项目规范、Trellis 产物、测试或人工判断。
- AGENTS 模板只承载常驻上下文必须知道的路由、触发条件、硬性安全边界和最终报告要求；详细流程、命令参数、检查清单和专项判断优先放入对应 Skill 延迟加载。
- Web 和 Mobile 验证工具分工明确，不把诊断、探索和可重复测试混为一谈。
- SEO/GEO 只面向公开 Web 搜索可见性，不替代 Web 运行时诊断、Playwright 回归、发布检查或人工内容评审。
- 跨仓或链路不完整时，mock 只能基于 contract、schema、真实响应样例、既有 fixture 或用户明确确认；mock-backed 不能冒充 full-stack 通过。
- `rtk` 是命令输出压缩层，不是测试 runner。unit test、API / integration test、Playwright Web E2E、Maestro Mobile / Hybrid E2E 或任何需要落地报告的命令，必须先评估缓存 / 回放是否会跳过文件写入；报告型正式验证默认使用原生命令或项目明确的 no-cache / report-safe 命令，缺报或旧报时原生命令复验。
- API / Web E2E / Mobile E2E / Hybrid E2E 调试轮次可以保留多份带业务名、分支名和时间戳的本地报告快照；一旦 Playwright 或 Maestro 运行产生 runner 原生报告，或 API / integration / unit runner 生成了本轮需要保留的报告，无论最终全量是否通过，都要在下一次可能清空输出的运行前生成该次运行的命名报告和同目录同 stem 的中文 Markdown 汇总。Playwright 的同 stem 以命名后的 HTML 为准，不以 `results.json` 为准。
- API / integration 的中文 Markdown 汇总必须包含 URI 覆盖矩阵，将每条覆盖范围描述映射到具体 `method + URI path`、测试脚本 / case、预期状态码或副作用，以及 `.feature` / contract / schema 依据。
- 任何工具不可用时，要标记 `blocked`、`skipped` 或 `not-needed`，不能声称对应验证已通过。

## SBTD：SDD、BDD、TDD、DDD

SBTD 是本模板对 SDD、BDD、TDD、DDD 的组合简称。它不是单独的新工具，而是用于组织需求、设计、实现和验证的协作框架。

| 概念 | 全称 | 在模板中的作用 |
|---|---|---|
| SDD | Specification-Driven Development | 用 PRD、design、implement、验收标准和长期规则说明“要做什么、为什么做、怎么验证”。在 Trellis 项目中，对应任务产物和 `.trellis/spec` 的长期规则。 |
| BDD | Behavior-Driven Development | 用 Given / When / Then 或项目已有 Gherkin 约定固化用户可见行为。新增或修改 UI、API、CLI、权限、错误、状态变化和外部集成可观察行为时，默认需要持久 BDD 场景；分仓或跨端链路先做上下文完整性 gate。主动使用 `gherkin-bdd` 且请求包含 `sync` / `同步` 时，原有 BDD Sync Mode 保持不变：全量扫描当前工作树与 `features/`，多仓时先确认其他仓库更新状态再同步 `.feature`。BDD / 知识库请求具有明确 `read` / `读取` 只读意图且不含变更意图时，进入 Knowledge Ingest，按目标 ref 固定精确 SHA 并生成派生行为目录。 |
| TDD | Test-Driven Development | 对 bug 修复、核心业务逻辑、算法、数据转换、高风险路径和回归敏感模块采用测试先行。BDD 固化可观察行为，TDD 把它转成可执行测试和红绿重构循环。 |

**强制 post-grill 审核**：无论由 Agent 自发调用还是用户主动调用，每次完整执行 `grill-with-docs` 结束后都必须立即调用 bundled `book-ddd-distilled-modeling` 独立二次审核，并单独输出 `DDD Boundary Review`。该门禁在 `default` / `lite` / `strict` 三种模式下都没有替代检查：reviewer 不可用、不可读或必要证据缺失时一律 `blocked`，不得用访谈内建模、非正式替代检查或降模式绕过。`grill-with-docs` 内嵌的 external `domain-modeling` dependency 不能替代该二次审核；状态为 `needs-clarification` 时先继续澄清并重审，状态为 `blocked` 时说明阻断。未达到 `confirmed` 不得进入需求确认、PRD、design、任务记录或实现。未使用 `grill-with-docs` 时仍按业务术语、领域规则和模型歧义独立判断是否调用 DDD Skill，并说明未调用原因；只有调用与跳过存在会改变需求、领域边界或实现决策的实质权衡时才询问用户，项目事实已消除歧义时直接推进，不制造重复确认门。


### Book-derived 开发门禁

执行模式为 `strict` 的开发任务先输出 `Book Gate Plan`，依据项目事实为 5 个 bundled `book-*` Skill 标记 `required` / `on-demand`、命中原因、执行阶段和独立 Gate state。Gate state 只能是 `planned` / `running` / `passed` / `blocked` / `not-required`，并按 `planned` → `running` → `passed` / `blocked` 转换；具体 reviewer status 仅在 Skill 运行后填写。`default` / `lite` 不机械输出完整 Gate 表，按实际风险与明确交付选择方法；一旦选用或项目已有要求某方法，不得伪造证据或冒充已通过。完整 `grill-with-docs` 后的 DDD Boundary Review 是三种模式的共同强制例外。对 `strict` 任务，命中以下客观触发条件后必须调用并通过对应审核，不能再由 Agent 主观跳过：

| 审核 | 强制触发场景 | 最适合阶段与通过条件 |
|---|---|---|
| `DDD Boundary Review` | 每次完整执行 `grill-with-docs` | 需求确认 / PRD 前；`confirmed` |
| `DDIA Data Design Review` | 持久化 / 共享数据、schema / migration、shared / persistent / cross-request / cross-process cache、异步 / 跨服务数据流、数据所有权、事务边界、读写路径、backfill / replay / rollback / recovery 任一变化 | `design.md` / `implement.md` 稳定和实现开始前；`confirmed` |
| `Legacy Change Safety Review` | 修复既有行为 bug，或既有代码存在弱测试、行为不清、隐藏依赖、高回归风险任一项 | 首次行为修改前；`characterized`；安全网必须先有生产 seam 时进入 `seam-required` |
| `Refactoring Review` | 修改既有生产代码 | 首次实现编辑前；`proceed`，或先完成 `refactor-first` 并复审；legacy 为 `seam-required` 时可先用 `safety-seam-only` |
| `Release Readiness Review` | service / API / auth / billing / notification / job / queue / scheduler / external integration / data pipeline / deployment 等生产路径变化 | 所有适用 testing-tool gate 和 project validation 后、任务完成或最终发布决策前；`ready` |

同时命中 legacy 与 refactoring gate 时，正常顺序为 legacy `characterized` 后再执行 refactoring；唯一受控例外是 `seam-required` → `Refactoring Review` (`safety-seam-only`) → 最小行为保持测试 seam → legacy `characterized` → 常规 `Refactoring Review`。`needs-*`、`seam-required`、`refactor-first` 或 `blocked` 都会让 Gate state 保持 `running` 或转为 `blocked`，修正后必须重审。Release gate 中必需验证缺失只能 `blocked`，只有 optional check 可由明确 accountable owner 接受为 residual risk。未命中上述强制触发条件的其他场景仍按需调用。

推荐顺序不是死板流程，而是风险驱动：

1. 领域语言或边界不清时，先做 DDD 轻量建模。
2. 需求需要沉淀时，用 SDD 写清规格、范围和验收。
3. 有用户可见行为时，用 BDD 固化场景。
4. 需要高信心实现时，用 TDD 让测试驱动代码变化。

### BDD Knowledge Ingest

`gherkin-bdd` 的 `read / 读取` 是面向知识库的只读入口，与 `sync / 同步` 和普通 BDD 写入请求明确分开。只有请求具有明确只读意图、且不含新增、修改、更新或删除意图时才进入 Knowledge Ingest；“先读取再修改”仍走普通 BDD 工作流：

- 每个仓库由知识库或产品配置指定目标 branch、tag 或 SHA，例如 `staging`。
- 读取前把目标 ref 解析为精确 commit SHA；ref 表示选择策略，SHA 表示本次不可变快照。
- 从 Git object 或隔离 worktree 读取仓库自有 `.feature`，不切换开发者活动 worktree。
- 聚合结果是可重建派生视图；目标 ref 中的 `.feature` 仍是行为 SOT。
- 不要求或补写 `feature_id`、`scenario_id`、新 tags、owner 字段，也不引入 BDD Runner。
- 使用 repository key + path + Feature / Rule / Scenario 名称 + 可选 Examples fingerprint + SHA 作为读取 locator；跨仓相似或冲突只生成候选，不自动合并或改写。
- 输出 `Knowledge Ingest`: `run` / `partial` / `blocked` 和 `Mutation: none`。请求含 `sync` / `同步` 时，仍执行原有可写 BDD Sync Mode。

P1.1 已通过 bundled `knowledge-base-integration` Skill 落地产品注册表、Workspace Mapping、Evidence Policy 决策、目标 ref / Revision Set、完整无 ID Gherkin 目录、静态 / manifest 绑定、跨仓候选、幂等 ingest / smoke、隔离 worktree、分阶段 Smoke、基础设施重试、本地 / 命令式 Runner Adapter、可信环境对齐、artifact manifest、checksums 和 metrics。从本仓库根目录校验随 Skill 提供的示例配置：

```bash
python sbtd-workflow-onboard/templates/skills/knowledge-base-integration/scripts/knowledge_base_p1.py validate-config \
  --product sbtd-workflow-onboard/templates/skills/knowledge-base-integration/references/product.example.yaml \
  --workspace sbtd-workflow-onboard/templates/skills/knowledge-base-integration/references/workspace.local.example.yaml
```

同一 CLI 还提供 `decision`、`ingest` 和 `smoke` 子命令；各子命令的必需参数以 `--help` 和该 Skill 的说明为准。安装后则先定位 `knowledge-base-integration` Skill 根目录，再运行其 `scripts/knowledge_base_p1.py`。服务器只收集本轮命令新建或刷新的原生报告及同 stem 中文汇总，Mobile 等能力通过 Runner labels 调度。P1.1 只生成 `Evidence Publication: not-configured` 的待发布 bundle，Evidence Store、PR Check、自动失效、quarantine、retention 和远端 Gate 仍属于 P2。完整边界见 [知识库集成 P1 / P2 落地方案](docs/prd/knowledge-base-integration-prd.md)。

## 工具职责边界

| 工具 | 主责 | 不负责 |
|---|---|---|
| Codex `tool_search` / Plugin / Connector | 发现延迟加载工具、remote / local plugin、connector 和 ChatGPT-hosted MCP 能力。 | Catalog 或 marketplace 展示不等于已授权 / 已可调用；安装需用户明确请求，session auth / OAuth / cookies / tokens 不写入项目。 |
| Chrome DevTools MCP | Web 运行时诊断、真实 Chrome 检查、console、network、storage、performance trace、screenshot 证据。 | 不作为 CI gate，不替代 Playwright E2E。 |
| Playwright CLI / `@playwright/test` | 项目内 Web E2E、Web 回归、跨浏览器检查和 CI gate。 | 不默认全局安装；项目未安装时必须先询问。 |
| Playwright MCP | Agentic Web 探索、可访问性快照、locator 辅助和临时页面检查。 | 不替代项目内 `playwright test`。 |
| Maestro CLI | Android、iOS、React Native、Flutter、Hybrid App E2E，以及可选 Chromium Web smoke。 | 不作为 Web 回归主责；Web 只做 smoke。 |
| Maestro MCP | 设备检查、view hierarchy、截图、flow 辅助，以及终态 Cloud per-flow run 的状态与 artifact 诊断。 | 不单独替代 Maestro CLI；当前 Agent / IDE 的 MCP 配置需包含 `JAVA_HOME` / `PATH` env。 |
| `shadcn` | shadcn/ui 项目的组件、registry、preset、CLI、docs / diff 和组件组合规则。 | 不替代通用 UI/UX 设计判断、`impeccable` 视觉打磨或 React Bits Free / 付费 tier 判定。 |
| `web-ui-autotest-generator` | 生成和审计 repo-resident Playwright 测试资产、选择器和覆盖率报告。 | 不执行 E2E；执行底座仍是项目内 Playwright CLI。 |
| `seo-geo` | 公开网站、落地页、文档站、产品页、营销页的 SEO/GEO、schema、meta、robots / sitemap 和 AI 搜索可见性专项检查。 | 不替代 Chrome DevTools MCP、Playwright CLI、项目发布检查或内容评审；不用于内部后台、API、CLI、移动 App。 |
| `maestro-mobile-e2e` | 从 BDD `.feature` 派生和维护 repo-resident Maestro Mobile / Hybrid flow，约束报告路径，并按需加载真机排障 lesson。 | 不替代 BDD、项目验证或 Maestro CLI。 |
| `knowledge-base-integration` | 运行产品级 Knowledge Ingest、Evidence Policy、Revision Set、完整无 ID 行为目录、幂等分阶段 smoke、Runner Adapter 和证据完整性校验。 | 不修改源 `.feature`，不发布 Evidence，不写 PR Check；P2 负责远端治理。 |
| `rtk` | 用户级全局 CLI，用于压缩 terminal 命令输出，降低上下文占用；缺失时先说明作用并询问是否协助安装。 | 不替代测试 runner；报告型 unit / API / Playwright / Maestro 命令先评估缓存与文件写入风险，必要时使用原生命令或 fallback-native。 |
| `caveman` | 用户级全局 Agent Skill，用于压缩 Agent 回复和长任务状态更新；缺失时先说明作用并询问是否协助安装。同一主要目标达到 3 次中间状态更新、5 个独立工具结果、长任务 / 上下文压力或重复自动化 / review / 验证轮次中的任一条件时，`autoLiteEligible` 单调锁存，下一条普通重复状态必须进入任务级 `auto-lite`。 | 不替代项目 Skill、BDD、TDD、验证、GitNexus、Trellis 或最终报告；保护区只覆盖当前回复，只有新的主要目标重置。任务级 / 会话级退出按全局状态机处理，手动 `/caveman` 不清除自动退出。 |
| `i-have-adhd` | 第 19 个 required external Skill，把回复塑形成行动优先的可扫读结构；init/reset 从 stable 镜像离线自动安装 / 重装完整 Skill 目录（check 报告缺失并提示修复，不阻断退出码），不装上游 plugin / hook / extension。 | 不是 workflow gate，不改变代码、测试、验证、Trellis 或工作流决策；无自动模式；输出契约保护区优先；错误原因证据不足时标注“假设”。 |

同一浏览器上下文同一时间只允许一个 controller，避免 Chrome DevTools MCP、Playwright MCP 和 Playwright CLI 互相污染状态。

## Playwright 集成策略

Playwright CLI 是项目级 Web E2E 依赖，不是全局默认工具。

检测顺序：

1. 检查目标项目是否有 `package.json`。
2. 检查 `@playwright/test`、`playwright` 依赖、Playwright 配置、`tests/e2e` 或 E2E scripts。
3. 如果 Web 回归或 `web-ui-autotest-generator` 需要 Playwright，但项目内缺失 CLI，先询问用户是否安装到项目 devDependency。
4. 用户确认后按项目包管理器安装，安装成功后继续验证流程。
5. 用户拒绝或安装失败时，`Playwright CLI` 标记 `skipped-by-user` 或 `blocked`，`Playwright Web Tests` 标记 `blocked` 或 `skipped`。

Fallback：

- 可使用 Chrome DevTools MCP 做运行时诊断。
- 可使用 Playwright MCP 做页面探索、可访问性快照或 locator 辅助。
- 不能声称 Web E2E 或回归测试已通过。

Web E2E 报告规则：

- 完整环境可用时跑 full-stack Playwright E2E；只有 contract 或 mock 环境时标记 `contract-backed` 或 `mock-backed`。
- `--reporter=list` 只用于诊断或定点重跑；Web E2E 进入正式验证范围时，最终收尾必须再跑不覆盖项目 reporter 的计划范围命令，生成命名 HTML 和同 stem 中文 Markdown 汇总。
- Playwright HTML reporter 的 `outputFolder` 默认使用 runner 临时目录 `tests/e2e/reports/.playwright-html-current/`；该目录可能被每次 Playwright 运行清空，不保存正式命名报告。
- 最终正式 Playwright HTML 报告快照默认写入 `tests/e2e/reports/html/`，命名为 `playwright-report-{feature_file_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}.html`，并生成同 stem 的中文 Markdown 汇总。`branch_slug` 取当前分支，`/`、空格和特殊字符替换为 `_`。多轮调试可以保留多份带业务名、分支名和时间戳的本地快照，最终是否通过仍由 `Final Full Rerun` 表达。
- `feature_file_name` 默认取关联 BDD `.feature` 文件名去掉扩展名；smoke test 使用 `smoke`；一次运行覆盖多个 `.feature` 时优先使用 suite 名，否则使用 `multi-feature`。
- Playwright Markdown 汇总必须与命名后的 HTML 报告完全同 stem；`results.json`、`junit.xml`、`test-results/` 和默认 `index.html` 不能决定正式 Markdown 文件名。`results.md`、`result.md`、`junit.md` 或 `index.md` 不能满足最终 `Run Summary MD`。
- 命名后的 HTML 是正式报告；Playwright 默认 `index.html` 只作为 `.playwright-html-current/` 中的复制源或工具兼容产物。只要 Playwright 已产生 `index.html`、`results.json`、`junit.xml` 或等价产物，最终输出前必须确认命名后的 HTML 和同 stem 中文 `.md` 实际存在。
- 调试轮次失败后先重跑失败 spec，再跑受影响子集，最后跑计划范围内全量验证；最终全量是否通过由 `Final Full Rerun` 表达，不能用“未全绿”跳过报告文件。

API / integration 报告规则：

- API 正式报告默认写入 `tests/api/reports/`，stem 使用 `api-report-{suite_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}`；自定义 API 脚本如果没有原生 reporter，正式验证时必须捕获 stdout、stderr、exit code、命令和时间戳为 raw report，并生成同 stem 中文 Markdown 汇总。
- API Markdown 汇总必须包含 URI 覆盖矩阵。每条覆盖范围描述都要映射到具体 `method + URI path`，并记录对应测试脚本 / case、期望状态码或副作用、关联 `.feature` / contract / schema；同一覆盖描述涉及多个 endpoint 时逐行列出。
- Base URL、环境名或服务名可以单独记录，但不能用脚本名、权限链路概括或业务域名称替代 URI path；无法确定 URI 的覆盖项必须标记 `blocked` 或 `missing-uri`。不要写入真实账号、token、敏感 query/body 或生产数据。

## Maestro 集成策略

Maestro 面向移动 App 和 Hybrid App E2E。模板不推荐用 Maestro 主做 Web 回归；Web 场景只适合做少量 Chromium smoke，主责仍在 Playwright CLI。

检测和安装顺序：

1. 需要 Maestro 前先检查 Java 17+。
2. 优先执行 `java --version`，失败时回退 `java -version`。
3. 当前 JDK 满足 17+ 时优先使用当前 JDK。
4. Java 缺失或低于 17 时，先扫描本机已有 JDK，优先选择已安装且满足 17+ 的 JDK。
5. 只有本机没有可用 17+ JDK 且用户确认后，才引导安装 JDK；默认建议安装 OpenJDK Temurin 21 最新 JDK，下载来源为 `https://github.com/adoptium/temurin21-binaries/releases`。
6. 用户指定其他 Java 版本时，只允许安装 Java 17 或更高版本，拒绝任何低于 17 的版本。
7. Java 通过后检查 Maestro CLI。
8. Maestro CLI 缺失时询问用户是否安装到开发环境或 CI runner。
9. Maestro CLI 可用后再检查 Maestro MCP，并引导当前 Agent / IDE 的 MCP 配置同时包含 `command`、`args` 和 env。
10. Maestro MCP 的 `JAVA_HOME` 使用选定的 JDK home，`PATH` 必须优先包含 Maestro bin 目录和 JDK `bin` 目录，再包含系统基础路径。

Fallback：

- Maestro MCP 缺失或 MCP env 未配置但 CLI 可用时，继续使用 `maestro test` 执行已有 flow，并单独报告 MCP 状态和缺失配置。
- Maestro CLI 缺失且用户拒绝安装时，`Maestro Mobile` 标记 `blocked` 或 `skipped`。
- Java 17+ 缺失且用户未确认安装时，只报告阻塞和安装引导，不自动安装。
- 设备、模拟器、app binary、appId、bundleId、测试账号或环境不可用时，必须记录阻塞原因。

Maestro flow 资产和报告规则：

- 需要从 Mobile / Hybrid BDD 场景生成或维护 Maestro flow 时，调用 `maestro-mobile-e2e`。
- Flow 固定写入 `maestro/flow/`，使用 `.yml` 扩展名。
- 文件名和 YAML `name` 使用英文业务场景名；文件名使用 lower-kebab-case，例如 `maestro/flow/login-success.yml`。
- iOS 和 Android 需要明显不同 flow 时，可使用 `maestro/flow/ios/*.yml` 和 `maestro/flow/android/*.yml`；平台 smoke 可使用 `maestro/flow/ios/smoke.yml` 和 `maestro/flow/android/smoke.yml`。
- 全量回归 / smoke flow 固定为 `maestro/flow/smoke.yml`。
- 每个 flow 必须追踪到源 `.feature` 路径、场景名称、平台范围和测试模式。
- Maestro CLI 最终正式 report 固定写入项目根目录 `.maestro/reports/`。
- 报告命名为 `maestro-report-{flow_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}.xml` 或 `.html`，并生成同 stem 的中文 `.md` 运行汇总；`flow_name` 取 Maestro flow 文件名 stem，smoke flow 使用 `smoke`，是否生成 HTML 遵循项目或用户对人类可读报告的需要。
- 优先让 Maestro 直接输出到带分支名和时间戳的文件；如果项目 wrapper 只能输出到固定目录或固定文件，使用 `.maestro/reports/.maestro-current/` 作为临时输出，再复制 / 提升为 `maestro-report-{flow_name}-{branch_slug}-{timestamp}`。`~/.maestro/tests`、`.maestro-current/`、固定 `report.xml` / `report.html` 都不是正式保留报告。
- stdout-only Maestro run 只用于诊断或定点重跑，不能满足正式 Mobile / Hybrid E2E 报告 gate；正式验证收尾必须补跑 `--format` / `--output` 或项目等价 reporter，无法产出时标记 blocked。
- Maestro 官方默认运行 artifacts 仍在用户 home 下的 `~/.maestro/tests`；它不是仓库内测试资产。
- iOS 真机遇到 driver setup、端口转发、view hierarchy、tap crash 或版本已知问题时，`maestro-mobile-e2e` 按标签 / 关键字懒加载对应 lesson；未命中时不预先套用临时补丁。

移动端上下文 gate：

- 生成或运行 flow 前确认平台、app artifact、bundleId / appId、设备 / 模拟器 / 云测、后端依赖、base URL / launch args / deep link、账号、数据、权限、稳定 selector 和系统 UI。
- 缺少关键事实时，`Maestro Flow Assets` 标记 `blocked`，不生成脆弱 flow。
- contract-backed 或 app-mocked flow 只能证明对应 contract / mock 假设成立，不能报告为 full-stack Mobile E2E 通过。

## Chrome DevTools MCP 和 Playwright MCP

这两个 MCP 都是 Agent 交互能力，不是项目依赖。

- Chrome DevTools MCP：用于真实 Chrome 运行时诊断，适合白屏、console error、network、cookie、storage、性能 trace、截图和临时复现。
- Playwright MCP：用于 Agentic Web 探索、可访问性快照、locator 生成辅助和页面结构理解。

MCP 配置由 Agent 或 IDE 提供。`scripts/onboard.py` 只做检查和引导，不把 MCP 配置文件复制进业务项目；根目录安装脚本在用户明确选择平台和 MCP server 后，可以执行平台 CLI 配置或写入 Oh My Pi 的 `mcp.json`。Codex plugin / connector 与 ChatGPT-hosted MCP 也遵循同一边界：先确认当前会话可见 callable tool，授权状态由 Agent / connector 管理，不把 session auth 材料写入项目。

## `web-ui-autotest-generator` 使用边界

`web-ui-autotest-generator` 只在需要生成、审计或评估可入库 Web UI 测试资产时启用。

适用场景：

- 用户明确要求生成 Web UI 自动化测试、Playwright、E2E suite 或 UI 回归测试代码。
- 关键 Web UI 用户路径需要进入仓库长期维护。
- 项目已有 Playwright，需要扩展可维护覆盖。
- Trellis 验收要求可重复 UI 回归。
- Chrome DevTools MCP、Playwright MCP、Playwright CLI 或人工复核发现了应进入 CI / 本地 E2E 的覆盖缺口。

不适用场景：

- 只需要一次性页面诊断。
- 只需要截图或 console / network 证据。
- 不准备把测试资产长期维护到仓库。
- 项目不接受 Playwright CLI 或测试数据、账号、环境暂不可用。

默认沉淀路径：

- `tests/e2e/manifest/ui-test-manifest.json`
- `tests/e2e/manifest/ui-selector-audit.json`
- `tests/e2e/manifest/ui-test-coverage.json`

调用 `web-ui-autotest-generator` 的脚本时，模板要求显式传入 `tests/e2e/manifest/` 下的参数路径，不依赖 Skill 示例里的根目录默认值：

```bash
generate_manifest.py --root . --out tests/e2e/manifest/ui-test-manifest.json --pretty
audit_selectors.py --root . --out tests/e2e/manifest/ui-selector-audit.json --pretty
check_coverage.py --root . --manifest tests/e2e/manifest/ui-test-manifest.json --selector-audit tests/e2e/manifest/ui-selector-audit.json --tests-dir tests/e2e --out tests/e2e/manifest/ui-test-coverage.json --pretty
```

失败分析 `ui-test-repair-plan.json` 是运行产物，不是稳定测试资产；如生成，默认放到 `tests/e2e/manifest/ui-test-repair-plan.json` 并通过 `.gitignore` 忽略。验证或 Trellis check 收尾时，必须确认三个可入库 JSON 位于 `tests/e2e/manifest/`，且项目根目录没有残留同名 JSON。

## `shadcn` Skill 使用边界

`shadcn` 只在 shadcn/ui 项目、组件 registry、preset 或 CLI 工作流需要时启用。

适用场景：

- 项目存在 `components.json`，或用户要求初始化 / 维护 shadcn/ui。
- 需要执行或评估 `shadcn init/add/search/view/docs/diff/info/migrate/preset`、preset code、registry item、第三方 / 私有 / 付费 registry 或 shadcn MCP 配置。
- 需要修复 shadcn 组件组合、forms、icons、semantic tokens、Tailwind v3 / v4、Base UI vs Radix API、chat primitives、registry import path rewrite 或已安装组件更新策略。

执行和报告规则：

- UI/UX 任务中先用 `ui-ux-pro-max` 明确产品方向、信息架构、可访问性和设计系统约束，再用 `shadcn` 处理组件来源、CLI、registry 和具体实现规则。
- 按项目 package manager 选择 `npx shadcn@latest`、`pnpm dlx shadcn@latest` 或 `bunx --bun shadcn@latest`。
- 添加或更新组件前先检查 `components.json`、`shadcn info`、已安装组件和项目别名；涉及组件 API 时先查 `shadcn docs`。
- registry 未明确时先询问用户；更新已有组件时先用 `--dry-run` / `--diff`，未经用户明确确认不使用覆盖式更新。

不适用场景：

- 非 shadcn/ui 项目，且用户没有要求引入 shadcn。
- 只是通用 UI 设计判断、视觉 polish、后端、测试、文档或非 React UI 栈任务。
- React Bits Free / 付费 tier、付费 Skill 安装或 key 可用性判定；这些按 React Bits tier 规则单独处理。

## React Bits tier 选择边界

React Bits 不是 shadcn/ui 的必装依赖。安装和 reset 默认保持 shadcn/ui only；只有检测到目标项目是 React + shadcn/ui（存在 `components.json`），且任务需要更强视觉表达、动画组件、blocks 或 landing sections 时，才询问用户是否启用 React Bits。

确认顺序：

- 先说明 shadcn/ui 提供常规应用组件，React Bits Free / 付费 tier 只是可选增强。
- 询问用户选择继续 shadcn/ui only、安装 React Bits Free，或使用已有付费 Starter / Pro / Ultimate。
- React Bits Free 只有在本工作流已有明确免费 source / registry / 安装命令时才安装；未配置时说明暂不可自动安装。
- 付费 Starter / Pro / Ultimate 必须由用户确认，且当前环境能读取 `REACTBITS_LICENSE_KEY`；安装器固定把 Skill 写入项目的 `.agents/skills/react-bits-pro/SKILL.md`，已有目标直接覆盖且不保留备份，不打印、不输出、不提交 key。
- reset 时保留检测到的既有 React Bits Free、Starter、Pro 或 Ultimate tier / registry，不用默认免费版覆盖。

## `seo-geo` 使用边界

`seo-geo` 只在公开 Web 资产需要搜索可见性检查时启用。

适用场景：

- 用户明确要求 SEO、GEO、AI search visibility、ChatGPT / Perplexity / Google AI Overview 可见性、schema、JSON-LD、meta tags、robots.txt、sitemap.xml、canonical 或关键词研究。
- 当前变更影响公开网站、落地页、文档站、产品页、营销页、公开博客或公开 README 页面。
- 发布前验收标准明确包含搜索引擎、AI 搜索引用、社交分享预览、结构化数据或 crawl / indexing 检查。

不适用场景：

- 内部后台、登录后页面、API、CLI、移动 App、纯后端、测试资产、文档内部重排或无公开 URL 的一次性 UI 调整。
- 只需要 Web 运行时诊断、截图、console / network 证据或 Playwright 回归。
- `seo-geo` Skill 未安装且当前任务不以搜索可见性为主要目标。

执行和报告规则：

- 优先确认目标 URL、preview URL、生产 / staging 环境、是否允许抓取、是否已有 sitemap / robots / schema 约定。
- 没有公网 URL 或 preview URL 时，只做源码 / HTML 静态检查；最终报告 `SEO/GEO: static-only` 或 `blocked`，不能声称线上 SEO/GEO 已验证。
- 基础 audit 不要求 DataForSEO；DataForSEO login / password 只作为关键词、SERP、backlink、domain overview 等增强分析的可选凭据。
- 关键词量、SERP、AI 搜索可见性和平台抓取规则具有时效性，必须用当前可用来源核对。
- 不得把 DataForSEO login / password、Search Console 数据、付费报告、真实账号、密钥、PII 或生产敏感 URL 写入仓库、日志、截图、测试或正式报告。
- 最终输出或 Trellis check summary 必须报告 `SEO/GEO`: `audited` / `static-only` / `blocked` / `skipped` / `not-needed`。

## 跨仓测试模式和报告闭环

API、Web E2E、Mobile E2E、Hybrid E2E 或发布前 smoke 进入正式验证时，先选择测试模式：

| 模式 | 含义 | 报告边界 |
|---|---|---|
| `full-stack` | 真实前后端 / app / 环境 / 数据可用。 | 可报告完整链路通过。 |
| `contract-backed` | 完整链路不可用，但有可靠 API contract、schema、fixture 或真实响应样例。 | 只证明符合 contract。 |
| `mock-backed` / `app-mocked` | 使用 mock backend、fixture、launch args 或 app test mode。 | 只证明 mock 假设下的客户端 / app 行为。 |
| `backend-only` | 只验证 API provider 或服务端集成。 | 不等于 Web / Mobile E2E。 |
| `smoke-only` | 只验证启动、登录页、主导航等低依赖路径。 | 不等于完整回归。 |
| `blocked` | contract、环境、账号、数据、设备、artifact 或 selector 缺失。 | 不生成通过报告。 |

正式报告和 Markdown 汇总：

- API / integration 默认目录：`tests/api/reports/`。
- API / integration runner 临时输出默认目录：`tests/api/reports/.api-current/`。
- Playwright HTML reporter 临时输出默认目录：`tests/e2e/reports/.playwright-html-current/`。
- Playwright HTML 正式报告快照默认目录：`tests/e2e/reports/html/`。
- Maestro 默认目录：`.maestro/reports/`。
- Unit test 报告默认继承项目配置；缺少项目约定但需要本地正式证据时，使用 `tests/unit/reports/`，临时输出使用 `tests/unit/reports/.unit-current/`。
- 执行 unit / API / Playwright / Maestro 报告型测试前先记录 `rtk` 决策：`used` / `skipped-for-report` / `fallback-native` / `not-available` / `not-needed`。如果 `rtk` 后报告文件缺失、mtime / size 未变化、内容不对应本轮命令，或输出显示 cache hit / replay / skipped 写入，必须原生命令重跑并以原生结果为准。
- 调试轮次可以保留多份本地命名报告快照；一旦 Playwright 或 Maestro 运行产生 runner 原生报告，或 API / integration / unit runner 生成了本轮需要保留的报告，无论最终全量是否通过，都生成该次运行的命名报告和一份同目录同 stem 的中文 `.md` 汇总。API、Playwright 和 Maestro 的正式报告 stem 必须包含 `branch_slug`；`branch_slug` 取当前 git / CI 分支，detached HEAD 使用 `detached-{short_sha}`，非 git 环境使用 `unknown-branch`，并将 `/`、空格和特殊字符替换为 `_`。
- 正式报告要作为 PR 证据或被知识库读取时，额外生成同 report stem 的 `.evidence.json` 或由跨工具编排器生成聚合 envelope。先定位已安装的 `project-validation` Skill 根目录；通用 / 历史报告按该根目录下 `references/validation-evidence.schema.json`（v1）校验，v1 Schema 只检查 digest 形状，仍须重算报告 SHA-256；需要证明某个 Scenario 被执行时，必须使用同一根目录下的 `references/validation-evidence.v2.schema.json` 和 `scripts/validate_validation_evidence.py`，从 SHA-verified JUnit / Playwright JSON 中唯一匹配 passed case，并要求 case 内 `sbtd.sourceLocatorDigest` 等于重算 locator。证据记录 repository key、原始 source ref、完整 commit SHA、worktree state、trigger、evidence source、source revision、environment alignment、publication status、报告与同 stem 汇总的 SHA-256；`branch_slug` 只用于文件名，不是版本身份。
- `developer-local`、`ci` 和 `knowledge-server` 是三个独立 Evidence Source。dirty developer-local 结果只能是 `local-only`，不能证明 PR head；CI evidence 必须来自 clean checkout；knowledge-server 必须记录完整 Revision Set，且 `smoke-only`、contract 或 mock 结果不得提升为 full-stack。提交前的 evidence 只记录本地状态；创建最终提交后、发布或更新 PR Check 前，必须针对最终 PR head SHA 重新生成或复验并更新 sidecar / envelope，新 commit 使旧证据失效。CI 运行本身不等于已发布，只有目标系统接收后才标记 `published`。普通本地诊断不强制生成 evidence sidecar。v1 同 envelope 共存或 sidecar 自报 label 都不能当作 BDD 覆盖。
- 正式验证范围不能由 runner 是否已经产出报告倒推决定。API / Web E2E / Mobile E2E / Hybrid E2E 一旦进入正式验证范围，stdout-only、terminal-only 或 diagnostic-only 命令不能满足最终报告 gate：API 自定义脚本必须捕获 stdout / stderr / exit code 为 `api-report-*-{branch_slug}-*.txt` / `.json` raw report，Playwright `--reporter=list` 后必须补跑正式 reporter，Maestro stdout-only 后必须补跑 `--format` / `--output` 或项目等价 reporter；无法产出时标记 `Final Test Report: blocked` 和 `Run Summary MD: blocked`。
- 通用防覆盖规则：`coverage/`、`test-results/`、固定 `junit.xml`、runner 的 `current` / `latest` 目录和各工具临时输出目录都可能被下一轮运行清空、覆盖或重建；需要保留时，先复制 / 提升到正式快照目录和时间戳 stem，再启动下一轮会改写同一输出的命令。
- Playwright 报告命名为 `playwright-report-{feature_file_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}.html`；smoke 使用 `smoke`，多 `.feature` 运行优先使用 suite 名，否则使用 `multi-feature`。
- Playwright `.md` 汇总必须使用命名 HTML 的同 stem，不得使用 `results.json` / `junit.xml` / 默认 `index.html` 的 stem。
- Maestro 报告继续使用 `maestro-report-{flow_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}` stem；`flow_name` 取 flow 文件名，不改成 `feature_file_name`。
- API 报告使用 `api-report-{suite_name}-{branch_slug}-{YYYY_mm_dd}-{HH_MM_SS}` stem；unit 报告使用 `unit-report-{suite_name}-{YYYY_mm_dd}-{HH_MM_SS}` stem。缺少明确 suite 时可以省略 `{suite_name}`，但不能省略 `{branch_slug}`，也不能使用会被下一轮覆盖的固定文件名作为正式报告。没有原生 reporter 的 API 正式验证至少保留 `.txt` / `.json` raw report 和同 stem `.md`。
- `.md` 汇总使用中文撰写，状态枚举值、命令、文件路径、case / spec / flow 名称、错误原文和技术标识符可以保留英文；内容记录运行 case / spec / flow 列表、关联 BDD `.feature` 路径和场景名、总轮次、每轮命令、失败 case / spec / flow、失败原因、修复动作、修改文件摘要、定点重跑、影响范围重跑、最终全量重跑、跳过项和剩余风险。
- 失败修复后先重跑失败 case / spec / flow，再跑受影响子集，最后跑计划范围内全量验证；fail-fast 停在首个失败时，修复后必须继续跑未覆盖测试或重跑全量。
- 汇总和报告不得写入真实账号、密钥、PII、生产数据、完整 token 或敏感请求头。

## 最终验证工具栈

最终验证阶段按以下顺序和风险叠加：

| 层级 | 工具 / 方法 | 触发条件 | 状态要求 |
|---|---|---|---|
| 项目原生验证 | lint、typecheck、unit、integration、build、项目 README / Makefile / CI 命令 | 修改代码后默认执行可用的最小有效验证 | 记录命令和结果 |
| BDD 追踪 | `gherkin-bdd`、`.feature`、BDD runner 或测试名追踪 | 新增或修改用户可见行为 | `BDD`: `run` / `traceable` / `blocked` / `skipped` |
| 跨仓上下文 | contract、环境、账号、数据、设备、selector、app artifact | API / Web / Mobile / Hybrid 链路不完整 | `Cross-repo context`: `complete` / `contract-only` / `environment-only` / `missing` |
| GitNexus | MCP 影响分析、变更检测 | GitNexus MCP 可用且项目索引有效 | 成功使用或说明跳过原因 |
| Web 诊断 | Chrome DevTools MCP | 需要真实浏览器现场证据 | `diagnosed` / `inspected` / `blocked` / `skipped` / `not-needed` |
| Web 回归 | Playwright CLI | Web UI、路由、表单、权限、跨页面流程、API 集成、浏览器兼容 | `Playwright Web Tests`: `run` / `failed` / `blocked` / `skipped` |
| Web 测试资产 | `web-ui-autotest-generator` | 需要把 Web UI 回归固化入仓库 | `generated` / `coverage-only` / `blocked` / `skipped` |
| SEO/GEO | `seo-geo` | 公开 Web 资产需要搜索可见性、schema、meta、robots / sitemap 或 AI 搜索引用检查 | `SEO/GEO`: `audited` / `static-only` / `blocked` / `skipped` / `not-needed` |
| Mobile / Hybrid E2E | Java 17+、Maestro CLI、Maestro MCP | Android、iOS、RN、Flutter、Hybrid App 用户旅程 | `Maestro Mobile`: `run-local` / `run-cloud` / `blocked` / `skipped` / `not-needed` |
| 发布风险 | `book-release-readiness`；高风险改动可并行原生只读独立复核 | 生产路径、外部集成、部署敏感或高风险变更 | 记录风险、fallback、rollback 和用量风险 |

`project-validation` 覆盖 Node / JavaScript / TypeScript、Python、Go、Dart / Flutter、Java、Kotlin、C++、Swift 和 Objective-C 的代码规范检查、typecheck / static analysis、unit test 与项目 CI 继承规则；unit test 报告路径默认继承项目配置，不由模板统一硬编码，但需要作为本轮证据保留的 unit 报告不能只停留在会被 runner 重写的 coverage / JUnit 固定路径。

全局工具状态建议在最终输出中集中列明：

- `Chrome DevTools MCP`: `diagnosed` / `inspected` / `blocked` / `skipped` / `not-needed`
- `Playwright MCP`: `explored` / `locator-assisted` / `blocked` / `skipped` / `not-needed`
- `Playwright CLI`: `available` / `installed` / `missing` / `skipped-by-user` / `blocked`
- `Playwright Web Tests`: `run` / `failed` / `blocked` / `skipped`
- `Java`: `available` / `installed` / `missing` / `incompatible` / `blocked` / `skipped-by-user`
- `Maestro CLI`: `available` / `installed` / `missing` / `skipped-by-user` / `blocked`
- `Maestro MCP`: `available` / `configured` / `unavailable` / `blocked` / `skipped`
- `Maestro Mobile`: `run-local` / `run-cloud` / `blocked` / `skipped` / `not-needed`
- `Maestro Web Smoke`: `run` / `blocked` / `skipped` / `not-needed`
- `Maestro Flow Assets`: `generated` / `reused` / `blocked` / `skipped`
- `Web UI 测试资产`: `generated` / `coverage-only` / `blocked` / `skipped`
- `Knowledge Ingest`: `run` / `partial` / `blocked` / `not-needed`
- `Cross-repo context`: `complete` / `contract-only` / `environment-only` / `missing` / `not-needed`
- `API Contract`: `verified` / `user-provided` / `stale` / `missing` / `not-needed`
- `E2E Mode`: `full-stack` / `contract-backed` / `mock-backed` / `app-mocked` / `smoke-only` / `backend-only` / `blocked` / `not-needed`
- `Mobile Platform Scope`: `ios` / `android` / `both` / `hybrid` / `not-needed`
- `Mock Strategy`: `none` / `contract-backed` / `user-approved` / `blocked` / `not-needed`
- `Final Test Report`: `generated` / `blocked` / `not-supported` / `not-needed`
- `Run Summary MD`: `generated` / `blocked` / `not-needed`
- `rtk`: `used` / `skipped-for-report` / `fallback-native` / `not-available` / `not-needed`
- `Targeted Rerun`: `passed` / `failed` / `blocked` / `not-needed`
- `Final Full Rerun`: `passed` / `failed` / `blocked` / `skipped-with-risk` / `not-needed`
- `Evidence Source`: `developer-local` / `ci` / `knowledge-server` / `not-needed`
- `Source Revision`: `exact` / `dirty` / `unknown` / `not-needed`
- `Environment Alignment`: `verified` / `unverified` / `mismatch` / `not-needed`
- `Evidence Publication`: `local-only` / `published` / `blocked` / `not-configured` / `not-needed`
- `SEO/GEO`: `audited` / `static-only` / `blocked` / `skipped` / `not-needed`

## Lessons 分片与冲突边界

多人对同一仓库开发时，lessons 是被追踪且所有人都往里追加的文件，因此 `lessons-record` 要求按 lessons 分隔名分片写入。只有真正需要写入长期 lesson 时才解析写入者身份，纯读取不建立身份。分隔名的自动来源只有当前仓库 `<repo-root>/.sbtd/developer` 中唯一的 `name=`：本地合法身份优先；仅当本地文件确实缺失、且当前 checkout 已验证为同仓 linked worktree 时，才只读主 checkout 的同一文件，不复制回本地。现存但异常的身份文件（重复声明、非法内容、错误类型、不可读、symlink 或路径不确定）是冲突而不是缺失，必须停止该解析，不得用主 checkout 或其他来源绕过。允许来源都确实缺失时才说明路径并向用户要名字；不得用 `git config user.name`、提交作者、OS / 环境变量或历史 workspace 目录名推断——那些只说明历史状态，不代表当前写入者。分隔名必须匹配 `^[a-z0-9]+$`（非空、仅小写字母与数字），不合规就报告并停止、向用户要合规名字，不得改写、小写化或音译。旧 `.trellis/.developer` 只在用户明确授权旧项目身份迁移时按 `lessons-record` 的 `references/identity-migration.md` 处理，不再是日常身份 fallback。完整身份规则见「任务路由与 lessons 身份」一节和 bundled `lessons-record` Skill。

追加内容一律包在 `<!-- lessons:<name>:start -->` 与 `<!-- lessons:<name>:end -->` 之间，只写自己的块，不得重排或改动他人块；标记块只约束写入，读取时仍读所有人的块。`index.md` 中每个块自带表头，各自是完整表格，避免标记落在同一张表的行之间导致表格中断。已实测的收益边界：双方在各自已存在的块内追加可干净合并；两人首次在同一文件各建一个块仍会冲突一次，因为两处插入都落在文件末尾同一位置，解法是保留两个块。项目若要连这一次也自动消掉，可在 `.gitattributes` 中对 `docs/lessons/**/*.md` 选择性启用 `merge=union`；该项非默认，因为 union 会把同一行的并发改动双份保留。该 pattern 只覆盖 append-only 的 index、topic 与 archive；短入口 `docs/spec/lessons.md` 虽然也带标记块，但它会被裁剪改写而非纯追加，刻意不纳入 union，其首次冲突仍需手工处理。

标记块只隔离写入，不隔离 ID 命名空间：两人同日写出同一个 `LESSON-YYYYMMDD-<slug>`，会在同一 topic 文件里留下逐字相同的 heading，两条 index 行的 `detail` 锚点也逐字相同，链接与检索随即失去指向。因此 lesson ID 改为 `LESSON-YYYYMMDD-<name>-<slug>`，把分隔名原样纳入 ID。不做小写化或折叠是这条规则成立的前提：任何折叠都会把两个不同名字映射到同一 ID 段，撞号照旧；`<name>` 不含 `-` 也是同理，它保证名字恰占日期后的单个字段，名字与 slug 不会跨边界凑出同一个 ID。既有 lesson ID 不重命名，因为改 heading 会打断已有的 `detail` 锚点与交叉引用。该格式只保证新 ID 之间互不相同：保留的既有 ID 与新格式共用一个命名空间，形如 `LESSON-YYYYMMDD-<word>-<rest>` 的既有 ID 与 `<name>` 为 `<word>` 的新 ID 逐字相同，所以写入前要在 lessons 树里搜一次该 ID 和它的锚点，命中就换 slug。

## 模板 `.gitignore` 工具与测试产物策略

项目v2模板保留现有临时文件、构建／依赖、环境秘密、Python缓存、各Agent本地状态和测试报告规则；不因保留某个平台缓存规则而自动接入该平台。新本地保护只有四条根锚定、无尾随斜杠的规则：`/.sbtd`、`/docs/handoffs`、`/graft`、`/.graft`，覆盖目录、同名文件和symlink路径，但不会忽略`packages/graft`等同名业务子目录。共享的项目`AGENTS.md`、`CLAUDE.md`、`.agents/skills/**`、`ai/tasks/**`（含子任务／归档）、`docs/spec`、`docs/lessons`、CONTEXT／ADR、features、maestro/flow及三个可入库Web manifest保持可追踪；`ui-test-repair-plan.json`和报告仍属本地产物。初始化仍只追加缺失非空行，既有行不重排，重复执行保持字节幂等。写入Git worktree后，Onboard用原生`git check-ignore`验证新本地保护和共享路径规则；`ai/`、`docs/`、`tests/`等宽泛排除或重新包含本地路径时报告具体来源，缺保护时明确指出无匹配规则，Git不可用则标未验证。该检查是规则语义检查，不自动取消tracked状态，也不证明保留路径的数据所有权或迁移已完成。相关片段如下：

共享探针覆盖公开目录的固定分支：既有`docs/lessons.md`短入口、按context分组的ADR、undated任务归档、任务附属产物／bootstrap、UI上下文、测试源码、iOS／Android flow、受管React Bits Skill及根Git控制文件。使用代表性文件验证规则，不声称穷举每个自定义文件名，也不代替实际迁移清单核验。

既有项目迁移：如果旧模板已经写入 `.claude/`、`CLAUDE.md`、`.agents/` 或 `/AGENTS.md`，`init` / `reset` 的“只追加缺失行”契约不会自动删除这些既有行；确认项目需要追踪对应控制文件与生成集成后，手工删除这些旧行，并用 `git check-ignore` 复核目标路径。

这段旧规则建议以项目确实需要追踪相应资产为前提；v2不会因此重新接入旧Claude生成集成，也不会把其agents／commands／hooks设为所有项目必需的共享探针。旧集成是否保留或迁移仍须按实际项目与授权确认。

v2新模板不再含Trellis／GitNexus段。已有项目的旧保护不是按字符串盲删：先在显式迁移中追加新保护并保留旧规则，数据搬迁／验证和旧目录处置完成后，另行确认清理已证明受管的旧段；未知自定义规则保留。`init`／`reset`不会自动完成这项清理。若保留路径其实是业务数据，或已有本地产物被tracked，必须另行核对并取得处理授权；P0模板和探针更新不代表P1的所有权／迁移写入门禁已实现，不应在真实项目使用当前过渡生命周期。

```gitignore
# ---------- Claude ----------
# Keep shared agents, commands, skills, hooks, and settings versioned.
.claude/projects/
.claude/worktrees/
.claude/settings.local.json

# ---------- OMP ----------
# Keep shared agents, commands, skills, and extensions versioned.
.omp/plugins/


# ---------- AI Tools ----------
# Keep project AGENTS.md and shared .agents/skills versioned.
.worktrees/
/AGENTS.md.*

# ---------- SBTD ----------
/.sbtd
/docs/handoffs

# ---------- Graft ----------
/graft
/.graft

# ---------- Testing -----------
# MCP / browser controller local state
.chrome-devtools-mcp/
.playwright-mcp/

# Playwright runtime artifacts
playwright-report/
test-results/
blob-report/

# Web UI autotest generated run artifacts
tests/e2e/manifest/ui-test-repair-plan.json
tests/api/reports/
tests/unit/reports/
tests/e2e/reports/
tests/e2e/**/screenshots/
tests/e2e/**/videos/
tests/e2e/**/traces/
tests/e2e/**/*.trace.zip

# Maestro runtime artifacts
# Keep maestro/flow/*.yml flows versioned; ignore only local runtime output and reports.
.maestro/cache/
.maestro/tmp/
.maestro/runs/
.maestro/reports/
```

`maestro/flow/*.yml` flow 默认应可入库维护；`tests/api/reports/`、`tests/unit/reports/`、`tests/e2e/reports/` 和 `.maestro/reports/` 只保存正式报告快照、Markdown 汇总和本地 / CI 运行产物，默认不入库。Playwright report、trace、video、screenshot、coverage、JUnit 固定输出和一次性 repair plan 默认不入库。

## onboard / reset 检查范围

`sbtd-workflow-onboard` 的 init / reset / check 逻辑需要覆盖：

- 根安装器在用户选择或传入目标 Agent 平台后、询问 `init` / `reset` 和项目路径前，立即检测对应 CLI：`codex`、`claude`、`kimi` 或 `omp`。已通过 `<command> --version` 则继续；缺失或验证失败时先确保 npm 可用，再用 npm 全局安装官方 `@latest` 包并复验命令。
- 全局 Agent 规则，以及一个或多个项目根目录下的项目级 Agent 模板和 `.gitignore`。
- 14 个 bundled Skills 和 19 个 required external Skills 始终以全局 Skill 目录为目标，不再提供 project/none scope 选择。`init` 对已合法的 Skill 壳（普通目录、普通 `SKILL.md`、frontmatter `name` 匹配）跳过；缺失或身份无效才安装。`reset` 无备份覆盖全部 bundled Skills，并从当前 stable snapshot 强制重装全部 required external Skills。`catalog.json` 是 bundled Skill、external Skill 上游 repo/subpath/alias 和模板源路径的事实源，两个根安装器从 `check` 的 `group=referenced` 获取 external canonical 清单，不再各自维护重复数组。Catalog Schema 与运行时会在执行命令前同时拒绝绝对路径 / `..` 逃逸、错误 source 文件类型、bundled Skill frontmatter 身份不一致、非法 kind/id/target-role 组合和不完整的 HTTPS 仓库地址。已退役的 `trellis-workflow` / `trellis-channel` 不在 catalog 和模板树中，任务路由由 bundled `sbtd-task` 承担；本变更不清理用户全局目录里的旧 Skill 副本，旧资源退役由 P1-13 负责。

- Graft 仅在展示固定版本、native lifecycle 与 HOME telemetry 变更后明确确认安装；本地检测不依赖 npm latest。拒绝可选安装不触发 Node/npm 升级；project-only 不做全局 Graft/telemetry 写入。旧 GitNexus 安装路径已退役，但用户既有配置不删除。
- `init` / `reset` 在写入前检查所有所选项目的最小 SBTD 状态。可选状态缺失正常；异常和旧数据需处理，不创建同名替代品。
- `--init-projects` / `-InitProjects` 只处理逐项目 AGENTS、`.gitignore`、SBTD 检查及适用的 Playwright / React Bits，不进行全局安装。
- `AGENTS.project.md` 保存三模式入口、project-only 最小 fallback、项目路径和项目级硬边界；正常 `init` / `reset` 由全局 AGENTS + Skills 激活完整路由，public bootstrap / `init-projects` 不单独激活 book-derived 门禁。全局 AGENTS 维护共同路由与客观触发，bundled `sbtd-task` 承载 `default` / `lite` / `strict` 三模式工作契约（strict 才加载完整适用 Gate），项目模板自带全局路由不可见时的最小 objective-trigger fallback（含 Book Gate Plan 触发事实与 Gate lifecycle）；各 reviewer `SKILL.md` 独占状态、输出 schema、修正回路与 stop condition，模板与 `sbtd-task` 都不复制 reviewer 状态词表。
- 不再提供 GitNexus MCP 自动建议或专用菜单；Graft MCP/host 接线留待相应生产者完成，不用占位配置冒充可用。
- Chrome DevTools MCP 手动配置检查。
- Playwright MCP 手动配置检查。
- Playwright CLI 按每个项目独立检测和安装引导；只有既有 Playwright/E2E 标记使其适用时才询问。
- Java 17+、Maestro CLI 和 Maestro MCP 检测及安装引导，包含 Maestro MCP 的通用 `command` / `args` / `JAVA_HOME` / `PATH` 配置示例。
- bundled `seo-geo` 和 `web-ui-autotest-generator` Skill 的存在性检查；后者只在需要沉淀 Web UI 回归资产时调用。
- External Skill 默认使用 `--source auto` 从 `sbtd-workflow-onboard/assets/external-skills/stable/` 安装经过 review、精确上游 revision 和 checksum 固定的 stable set，不访问 Git 或网络；显式 `--source stable` 使用相同的确定性来源，只有用户明确选择 `--source upstream` 时才按上游仓库整组 clone、解析和验证当前版本，且失败时不回退。manifest、source subpath 和 license 路径必须被各自声明的根目录包含，拒绝绝对路径、`..` 和 symlink 逃逸。全部 Skill 先暂存和验证，再用临时 rollback backup 事务替换；canonical commit 成功后才删除 legacy 目录。
- `init` / `reset --json` 始终输出单份根 JSON；发生 required external 安装时，`requiredExternalInstall` 保留完整安装结果、逐项来源和 `transaction`（含失败时的 `rollbackPath` / `rollbackErrors`），未执行安装时为 `null`。失败仍返回非零退出码，不以丢弃诊断来保持 JSON 整洁。
- stable External Skills 的 `MANIFEST.json` 记录 stable set、精确上游 commit、subpath、tree SHA-256 和许可证/NOTICE。stable 快照保持上游原样且不得手改；只有显式 `promote-external-skills-stable --repository ... --revision <full-sha> --stable-set ... --yes` 才能整组更新。
- mattpocock external Skill 使用上游 canonical 名称。`migrate-external-skills --scope global --yes` 会先对全部受管旧目录做 identity preflight，再以已选 source 事务安装所需 canonical replacement。需要 canonical replacement 的 legacy predecessor 会在成功 transaction commit 后随临时 rollback 目录删除；只有不需要 canonical install 的 legacy-only cleanup（已有有效 replacement，或无 replacement 的 `zoom-out`）才会在删除前保留 migration backup。任何身份冲突均在安装前 fail-closed。正常 `init` / `reset` 仍只做已发现 legacy 的自动迁移。
- bundled Onboard rename migration 在 canonical `sbtd-workflow-onboard/SKILL.md` 校验成功，且 legacy `kuno-workflow-onboard-skills/SKILL.md` 的 frontmatter 仍确认旧身份时才删除旧目录；同名文件、无效 / 不相关目录或身份不匹配会在任何 target 变更前阻断 `init` / `reset` 并保留原内容，删除异常会进入失败报告；`plan` 会报告迁移目标或 identity conflict，`init-projects` 不检查或修改全局 Skill 目录。
- `shadcn`、`ui-ux-pro-max`、`impeccable` 等 referenced external Skill 的存在性检查。
- `ponytail`、`ponytail-review`、`ponytail-audit`、`ponytail-debt` 与其他 external Skills 同为 required：缺失或损坏时不询问、直接从 stable set 补装或修复，失败即阻断。SBTD 统一使用 Onboard stable skill-only provider；`check --json` 输出 `ponytailProvider`，检测到 Codex / OMP 官方 Ponytail plugin 已启用时报告 `provider=conflict`，`check` 失败且 `init` / `reset` 在写 stable copies 前阻断，根安装器同样停止。OMP 只在 `~/.omp` 已存在时执行 `omp plugin list`；缺失目录报告 `not-configured`，不得由只读检查创建。plugin 已安装但禁用只报告不阻断，CLI 不可用报告 `unknown` 而不伪造状态。Onboard 不安装、启用、禁用、信任或卸载官方 plugin；`ponytail-gain` / `ponytail-help` 只属于官方 plugin，不由 Onboard 管理。
- 方法与可读性路由由 `sbtd-task/references/methods.md` 和 `references/strict.md` 承载，AGENTS保留共同入口。正确性、安全、运行时特性、明确需求和项目约定优先，可读性与可维护性高于缩行或最小diff。`default` / `lite` 按实际风险和明确交付选择方法；`strict` 的适用开发任务在门禁通过后、首次实现编辑前使用 `ponytail`，非平凡生产diff在定点smoke后、最终验证前使用 `ponytail-review`并完成Code Readability Review，简化建议须服从可读性与安全。`ponytail-audit`仅用于明确要求的全仓审计，`ponytail-debt`用于触及或明确请求的marker；不因安装这些Skill而把所有模式改成固定强流程。
- React Bits tier 选择对每个 React + shadcn/ui 项目独立判断；仍保持项目级、可选并保留 license/registry 前置条件。
- `caveman` 用户级全局交互压缩 Skill 的存在性检查和安装引导。
- `i-have-adhd` 第 19 个 required external Skill 的存在性检查；缺失或无效时随 init/reset 或 `install-external-skills` 从 stable 镜像离线安装 / 修复。

`scripts/onboard.py` 提供检测和唯一 Graft 安装实现，不直接接入 Graft host/MCP。两个根安装器保留其他已实现 MCP 的显式选择与平台 scope；旧 GitNexus 专用分支移除，已有用户配置留存，不能用通用 custom 项静默恢复旧别名。

目标 Agent CLI 映射仍为 `codex → @openai/codex@latest`、`claude → @anthropic-ai/claude-code@latest`、`kimi → @moonshot-ai/kimi-code@latest`、`omp → @oh-my-pi/pi-coding-agent@latest`。只在缺失 Agent 或用户明确接受的 npm 工具确需安装时准备 npm；已可用的 Agent/Graft 不因 npm 缺失被重复安装。

- `codex`：执行 `codex mcp add ...`。
- `claude`：固定执行 `claude mcp add ... --scope user`。
- `kimi`：执行 `kimi mcp add ...`。
- `oh-my-pi` / `omp`：固定写入全局 `~/.omp/agent/mcp.json`。

两个安装脚本的 `source-root` 都直接指向 `sbtd-workflow-onboard` 目录，而不是仓库根目录。默认值是当前执行目录下的 `./sbtd-workflow-onboard`；如果该目录不存在，或缺少 `SKILL.md`、`REFERENCE.md`、`catalog.json`、`catalog.schema.json`、`scripts/onboard.py`、`templates/`、`assets/external-skills/stable/MANIFEST.json`，脚本会直接输出未找到或不完整的 Onboard skill 并结束安装。脚本可以被复制到其他目录独立使用，但必须能通过默认值或显式参数定位完整的 `sbtd-workflow-onboard`：

```bash
./install.sh --source-root /absolute/path/to/sbtd-workflow-onboard --platform codex
```

```powershell
.\install.ps1 -SourceRoot C:\absolute\path\to\sbtd-workflow-onboard -Platform codex
```

正常 onboard 可传入一个或多个逗号分隔的绝对项目根目录；未传时，安装脚本会说明支持多个绝对路径并交互询问：

```bash
./install.sh --platform codex --projects-root /abs/project-one,/abs/project-two --action init
```

```powershell
.\install.ps1 -Platform codex -ProjectsRoot "C:\work\one,C:\work\two" -Action init
```

只初始化项目、不触碰全局安装项：

```bash
bash install.sh --platform codex --init-projects /abs/project-one,/abs/project-two
```

```powershell
.\install.ps1 -Platform codex -InitProjects "C:\work\one,C:\work\two"
```

`caveman`、RTK、Java 和 Maestro 保持原来的条件确认规则；`caveman` 安装本身不会立即启用持久压缩对话模式。同一主要目标达到 3 次中间状态更新、5 个独立工具结果、长任务 / 上下文压力或重复自动化 / review / 验证轮次中的任一条件时，`autoLiteEligible` 单调锁存，下一条普通重复状态必须进入 `auto-lite`；保护区只覆盖当前回复，只有新的主要目标重置。任务级和会话级退出、手动模式与重新启用语义继承全局状态机。14 个 bundled Skills 和 19 个 required external Skills 在正常 `init` / `reset` 中作为必需全局能力处理：缺失 external Skills 默认从 Onboard 内置、经过 review 和 checksum 固定的 stable set 安装，不访问上游；只有显式 `--source upstream` 才获取并验证当前上游，任何失败都直接报错。bundled Skills 写入全局目录，两类 Skill 均不再询问 project scope。`sbtd-workflow-onboard` canonical Skill 写入且 frontmatter 校验通过后，旧 `kuno-workflow-onboard-skills` 目录会被删除，不保留 alias 或兼容副本。stable 自身完整性错误，以及目标侧 staging、权限、磁盘、commit 或 rollback 错误都直接失败，不存在自动 source fallback。`init` 对已合法 bundled / required external Skill 壳跳过；`reset` 无备份覆盖全部 bundled Skills，并从当前 stable snapshot 强制重装全部 required external Skills。External Skill 显式替换采用临时事务 rollback，完整恢复后删除临时备份，恢复不完整时保留并返回 rollback 路径；legacy migration 只处理旧名称。

`plan --json` 使用 `sbtdInit`，写入结果使用 `sbtdProjectSetup`；每个项目保留 `status`、`reason`、`nextStep`。只检查当前指针/目标与显式存在的 `ai/tasks/00-bootstrap-guidelines/task.md`，不扫描历史或推断最新任务。未完成 bootstrap 返回 6，异常/需用户处理返回 2；全部项目完成前置检查后才允许安装写入。无 bootstrap 不创建，done 只表示已记录状态，不是独立验收证明。旧 `.trellis` 保全并请求明确迁移，不执行旧 runtime。普通任务不依赖 onboard，reset 不清理任务或身份。显式 `--developer <name>` 时单 JSON 另含逐项目 `developerPlan`（请求名／来源／目标／状态／needsProtection），conflict、blocked、needs-* 或无项目范围时 exit 2，绝不默认 cwd 或 HOME。
