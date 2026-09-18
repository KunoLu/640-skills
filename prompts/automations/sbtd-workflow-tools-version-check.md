你在 ~/github/640-skills 中执行工具版本更新检查。

仓库定位：

- 本仓库是 Coding Agent 配置文件与 Skill 的摘录 / 同步源，不是真实业务项目。
- 本文件是 Orca 自动化 `SBTD Workflow Tools Version Check` 的版本化 prompt 源；每次仓库代码或工作流规则改动后都要评估是否需要同步调整。只有用户明确执行 `sync` / `同步` 时，才比较本文件与 live automation 并按差异同步；`update` / `更新` 与二者无关。
- 如发现路径匹配不上情况，以当前仓库已追踪文件和本 prompt 为准；本机若有 `AGENTS.md` 可作补充。

严格遵守：

- 先读取项目根目录的 `docs/lessons.md`；如果当前任务命中 repository-workflow、validation-scripts 或其他 topic 路由，再读取对应 `docs/lessons/topics/*.md`。
- 读取项目根目录的 `ENTRYPOINT.md`。若本机存在 `AGENTS.md` 则读取，缺失时跳过并继续，不得把它的存在当作 Gate。
- Agent 规则文件路径：本机若存在 `AGENTS.md`，以其“Agent 规则文件路径”章节为准；缺失时以本 prompt 与已追踪仓库文件为准。
- 当前可读取、评估或验证的本仓库版本化规则、文档、安装器、模板、Skill 或契约测试源路径仅限：`AGENTS.md`、`ENTRYPOINT.md`、`UPDATE.md`、`CHANGELOG.md`、`README.md`、`README.html`、`install.sh`、`install.ps1`、`sbtd-workflow-onboard/catalog.json`、`sbtd-workflow-onboard/catalog.schema.json`、`sbtd-workflow-onboard/SKILL.md`、`sbtd-workflow-onboard/REFERENCE.md`、`sbtd-workflow-onboard/scripts/onboard.py`、`sbtd-workflow-onboard/scripts/onboard_arguments.py`、`sbtd-workflow-onboard/scripts/onboard_contracts.py`、`sbtd-workflow-onboard/onboard-contracts.schema.json`、`sbtd-workflow-onboard/requirements.txt`、`sbtd-workflow-onboard/templates/agents/AGENTS.global.md`、`sbtd-workflow-onboard/templates/agents/AGENTS.project.md`、`sbtd-workflow-onboard/templates/project/.gitignore`、`sbtd-workflow-onboard/templates/skills/**`、`sbtd-workflow-onboard/assets/external-skills/stable/MANIFEST.json`、`sbtd-workflow-onboard/assets/external-skills/stable/THIRD_PARTY_NOTICES.md`、`sbtd-workflow-onboard/assets/external-skills/stable/licenses/**`、`sbtd-workflow-onboard/assets/external-skills/stable/skills/ponytail*/**`、`tests/**`、`prompts/automations/sbtd-workflow-tools-version-check.md`。
- 无人值守自动化仅可创建或修改：`UPDATE.md`；以及在第 11、12 步的证据和范围满足时可修改的 `AGENTS.md`、`CHANGELOG.md`、`README.md`、`README.html`、`prompts/automations/sbtd-workflow-tools-version-check.md`、`sbtd-workflow-onboard/SKILL.md`、`sbtd-workflow-onboard/REFERENCE.md`、`sbtd-workflow-onboard/templates/agents/**`、`sbtd-workflow-onboard/templates/skills/**`。其余允许路径只能读取、评估或验证。
- `install.sh`、`install.ps1`、`sbtd-workflow-onboard/scripts/onboard.py`、`sbtd-workflow-onboard/scripts/onboard_arguments.py`、`sbtd-workflow-onboard/scripts/onboard_contracts.py`、`sbtd-workflow-onboard/onboard-contracts.schema.json`、`sbtd-workflow-onboard/requirements.txt`、`sbtd-workflow-onboard/catalog.json`、`sbtd-workflow-onboard/catalog.schema.json`、`sbtd-workflow-onboard/templates/project/.gitignore` 与 `tests/**` 只能读取、评估或验证，不得由无人值守自动化修改。
- 除验证 P0-07 目录确实缺失的只读存在性断言外，不要读取、修改或复活已删除的旧路径：`kuno-workflow-onboard-skills/`、根目录旧 `AGENTS.global.md`、根目录旧 `AGENTS.project.md`、顶层 `agents/`、顶层 `skills/`、`sbtd-workflow-onboard/templates/skills/trellis-workflow/`、`sbtd-workflow-onboard/templates/skills/trellis-channel/`。任务路由由 bundled `sbtd-task` 承担；不得在任何规则、模板或文档中恢复 `trellis-workflow` / `trellis-channel` / Trellis Channel 运行路由，也不得把旧 bootstrap 当作 `sbtd-task` 别名。
- P0-07 只证明 catalog 与 bundled 载荷的原子切换，不证明完整 v2 CLI、`init` / `reset`、host 集成或旧项目 / 用户全局迁移完成；这些仍属 P1。评估或更新文档时，保留现有 Trellis / v1 CLI 行为的「过渡实现」边界，不把 `sbtd-task` 写成旧 bootstrap 或 Channel 路由的 alias，也不建议把本开发分支的混合 legacy 生命周期应用到真实项目。
- `UPDATE.md` 的正文内容必须使用中文。
- 不要修改 `ENTRYPOINT.md` 中任何工具的当前版本号；`ENTRYPOINT.md` 只作为版本比对基线读取。
- 只有用户在交互中手动输入“更新”或“update”时，才允许把 `UPDATE.md` 中的最新版本写回 `ENTRYPOINT.md`；定时自动化任务绝不执行这个写回动作。
- 不要执行 `git commit`、`git push`、`gh repo create` 或任何远程写入动作。
- 不要自行提交或推送变更；自动化完成后保留工作区 diff，等待用户手动确认。
- 无人值守自动化不得通过提问请求 `update` / `sync` / commit / push 授权，也不得把未回答的确认当作继续依据；这些动作只有用户在交互会话中明确要求时才属于独立工作流，定时任务本身不得升级权限。
- 执行 shell 命令时优先使用 `rtk` 前缀；`rtk` 不可用时再回退原生命令。若 `rtk` 出现包装器参数解析异常，必须用原生命令复验同一事实。
- 如果 `.trellis/` 不存在或 `.trellis/workflow.md` 不存在，不要假装 Trellis 阶段已执行；记录为跳过原因。

任务流程：

1. 读取 `ENTRYPOINT.md`，并优先解析“## 0. 版本监控配置”表格中“是否启用监控”为“是”的工具。
2. 每个工具至少读取这些字段：工具、GitHub 仓库、当前使用版本、版本通道策略、备注。
3. 将 `ENTRYPOINT.md` 中的“当前使用版本”作为该工具本次比对的固定起始版本；即使 `UPDATE.md` 里已有旧的更新区间，也不要把起始版本推进到 `UPDATE.md` 里的目标版本。
4. 对每个启用工具，按该工具备注和本 prompt 的专用规则找出应比较的最新版本。默认从对应 GitHub 仓库获取 releases 或 tags。OMP 按第 4.1 步以 npm `@oh-my-pi/pi-coding-agent` 为监控对象。
4.1. OMP 的监控对象是 npm 包 `@oh-my-pi/pi-coding-agent`（CLI `omp`），不是 `can1357/oh-my-pi` monorepo 的任意 release。判定顺序：
  - 从 `ENTRYPOINT.md` 读取 OMP 当前基线，格式必须是 `v<semver>`。
  - 查询 npm `@oh-my-pi/pi-coding-agent` 的 `dist-tags.latest`，先校验其为不含 `v` 前缀的 stable semver。
  - 通过该校验后，把 canonical OMP 目标定义为 `v<package-version>`。比较 `ENTRYPOINT.md` 基线、`UPDATE.md` 标题的目标版本、以及后续 `update` / `更新` 写回版本监控表和“当前版本汇总”，都必须使用该形式；不得把裸 `18.1.14`、`omp/18.1.14` 或未加 `v` 的 npm latest 写入任何版本字段。
  - 验证 GitHub `can1357/oh-my-pi` 存在对应 `v<package-version>` tag/Release。
  - 读取该 tag 的 `packages/coding-agent/package.json`，确认 `name=@oh-my-pi/pi-coding-agent` 且 `version=<package-version>`。
  - 用该 tag 的 Release body、tagged source 和 compare 补证据；只分析进入 OMP CLI/runtime 的变化，不得把 monorepo 中其他包的任意 release 当作 OMP CLI 更新。
  - 本机 `omp --version` 只核验安装状态，解析时去掉 `omp/` 前缀，不得覆盖 `ENTRYPOINT.md` 基线，也不得写入 `UPDATE.md` 标题。
  - npm latest、tagged `packages/coding-agent/package.json` 与 GitHub tag/Release 不一致时报告证据冲突，不得静默推进目标版本。
4.2. Caveman Skill Installer 的监控对象是 `JuliusBrussee/caveman` 的纯 `v<semver>` installer / skill tag 线，例如 `v2.6.0`；必须忽略 `bin-v*` engine binary、`cli-v*`、`pi-v*` 等其他产品线，即使 GitHub `releases/latest` 指向它们。`UPDATE.md` 只记录该 v* tag 线的差异，`更新` / `update` 只可写回 ENTRYPOINT 的 Caveman 版本字段；不得自动改写 `sbtd-workflow-onboard/scripts/onboard.py` 中的 `CAVEMAN_PINNED_REF`、`CAVEMAN_PINNED_REVISION`、core hash 或 `CAVEMAN_KNOWN_FAMILY_SHA256`。真正的维护基线升级必须先人工评审目标 tag 的完整受管 family（`caveman`、`caveman-*`、`cavecrew`、`cavecrew-*`）与安装器 / hook 行为，再在同一仓库改动中同步更新 ref、revision、core hash、family 内容指纹与测试。
5. 版本规范化要求：
  - `v` / `V` 前缀大小写不影响比较。
  - 当前版本是 stable 且策略为 stable-only 时，只比较更新的 stable 版本。
  - 当前版本是 prerelease 且策略为 same-prerelease-channel 时，只比较同一 prerelease 通道内的新版本，例如 `v0.6.0-beta.18` 只比较 `v0.6.0-beta.x` 中更高 beta 序号，不主动跳到 stable。
  - 如果跨越多个版本，汇总从 `ENTRYPOINT.md` 当前版本到最新版本之间所有 release notes。
6. 如果 GitHub release body 缺失、为空或明显不足以判断变更，不要直接写成“无可追溯变更”；必须继续从官方 docs / changelog、GitHub compare、具体 commit diff 和变更文件列表、migration / upgrade manifest、npm metadata / tarball / 发布文件结构等来源补充证据，并在 `UPDATE.md` 中说明哪些来源有依据、哪些来源缺失。
6.1. 对 Trellis、Codex dispatch、sub-agent、hook 或 Channel 的变更，必须额外核验目标 stable tag 的有效配置、workflow 模板和 migration manifest；区分功能首次引入、默认值变化与既有能力的 bug fix。`.trellis/**` 是共享 workflow gate，不是平台身份；若结论涉及平台调度，还必须读取对应生成的平台集成与 agent / worker 定义，并区分“已配置平台目录”与“当前 host”。`.codex/**` 与 `.omp/**` 可共存；静态 tag 工件不得选择运行时。不得把 Codex `codex.dispatch_mode`、Inline 或其 fallback 泛化到 OMP，不得以未发布 `main` 分支文本覆盖 tagged stable 版本结论。若这些依据无法完整取得，必须在 `UPDATE.md` 中逐项说明缺失依据和剩余不确定性，不得以 release body 充分为由跳过；缺少任一项时不得形成或更新平台调度规则。
7. 若本次至少有一个启用工具检测到可分析新版本，才创建或刷新 `UPDATE.md`；否则不要改 `UPDATE.md`。结构必须为：
 `# UPDATE`
 `## <工具名> <起始版本> -> <目标版本>`
  其中起始版本必须等于 `ENTRYPOINT.md` 中当前版本，目标版本必须等于最新检测并完成比对分析的版本；然后用中文写入 release 汇总、破坏性变更、迁移说明、对 agent harness workflow 的影响分析。本步骤只适用于本次版本检查运行。仅为检测到可分析新版本的启用工具创建或刷新区间章节，每个这样的工具只保留一个章节。无新版本则不新建章节，不要为补齐 OMP 或其他新监控工具而写 `当前版本 -> 当前版本`。普通仓库修改不得改 `UPDATE.md`。
8. 如果 `UPDATE.md` 中已有同一工具、同一起始版本的旧区间，例如 `## Codex v0.1.0 -> v0.1.5`，而本次最新版本为 `v0.1.6`，则把该二级标题更新为 `## Codex v0.1.0 -> v0.1.6`，并用中文替换该段落正文，不新增重复区间。
9. 如果 `ENTRYPOINT.md` 中的工具当前版本一直没有被用户手动更新，则无论自动化执行多少次，该工具在 `UPDATE.md` 中的区间起点都必须保持为 `ENTRYPOINT.md` 中的当前版本，终点为最新检测并完成比对分析的版本。
10. 评估是否需要修改本仓库规则时，不要只检查是否存在与上游同名的模板或配置文件；还必须用 release 中出现的关键概念、命令、配置项和兼容性关键词扫描以下本地文件，并在 `UPDATE.md` 的影响分析中说明命中结果和处理决定：
  - `AGENTS.md`
  - `prompts/automations/sbtd-workflow-tools-version-check.md`
  - `sbtd-workflow-onboard/catalog.json`
  - `sbtd-workflow-onboard/catalog.schema.json`
  - `sbtd-workflow-onboard/SKILL.md`
  - `sbtd-workflow-onboard/REFERENCE.md`
  - `sbtd-workflow-onboard/scripts/onboard.py`
  - `sbtd-workflow-onboard/scripts/onboard_arguments.py`
  - `sbtd-workflow-onboard/scripts/onboard_contracts.py`
  - `sbtd-workflow-onboard/onboard-contracts.schema.json`
  - `sbtd-workflow-onboard/requirements.txt`
  - `sbtd-workflow-onboard/templates/agents/AGENTS.global.md`
  - `sbtd-workflow-onboard/templates/agents/AGENTS.project.md`
  - `sbtd-workflow-onboard/templates/skills/**`
  - `install.sh`
  - `install.ps1`
  - `sbtd-workflow-onboard/templates/project/.gitignore`
  - `tests/**`
11. 根据 `UPDATE.md` 中可追溯到 release notes 或其他官方 tagged evidence 的内容，最小化修改 `AGENTS.md` 或 `sbtd-workflow-onboard/` 下相关模板 / Skill 文件：
  - 只修改 workflow、命令、配置、兼容性或工具使用规则相关内容。
  - 不做无关重写。
  - 每处修改都应能追溯到 release notes 或记录在 `UPDATE.md` 中的其他官方 tagged evidence。
  - 规则更新必须沉淀为长期通用规则，不要在长期执行规则里写入具体版本号、一次性版本区间或临时 release 叙述；版本号和依据保留在 `UPDATE.md` 的版本分析段落中。
  - 上游 external Skill 删除或重命名 canonical 名称时，必须在影响分析中确认 catalog、stable manifest、安装器 canonical / legacy 映射、全局与项目模板、README、CHANGELOG 和契约测试一致；正常 `init` / `reset` 必须先完整验证 replacement canonical，再删除所有已知 predecessor 目录。不得保留 predecessor alias、双 canonical 或未经身份确认的删除路径。
  - 自动化专用规则只能写入本仓库根 `AGENTS.md`、本 prompt 或其他自动化说明，不要污染可复用的全局 / 项目 AGENTS 模板。
  - 不要因为发现新版本就修改 `ENTRYPOINT.md` 的版本字段。
12. 如果仓库代码、`sbtd-workflow-onboard/`、工作流规则、安装 / reset 行为或用户可见路径有更新，必须在同一轮评估 `CHANGELOG.md`、`README.md`、`README.html` 和本 prompt 是否需要同步调整；新增用户可见能力、安装方式、兼容性边界、迁移、修复或发布前验证变化时更新 `CHANGELOG.md`，其他入口只更新实际受影响的版本化文件，无需修改时在最终输出说明原因。版本检查自动化不直接读取或写入 Orca live automation。
13. 运行验证：
  - `git status --short`
  - 检查 `ENTRYPOINT.md`、`UPDATE.md`、`CHANGELOG.md`、`README.md`、`README.html`、`install.sh`、`install.ps1`、`prompts/automations/sbtd-workflow-tools-version-check.md`、`sbtd-workflow-onboard/catalog.json`、`sbtd-workflow-onboard/catalog.schema.json`、`sbtd-workflow-onboard/SKILL.md`、`sbtd-workflow-onboard/REFERENCE.md`、`sbtd-workflow-onboard/scripts/onboard.py`、`sbtd-workflow-onboard/templates/agents/AGENTS.global.md`、`sbtd-workflow-onboard/templates/agents/AGENTS.project.md`、`sbtd-workflow-onboard/templates/project/.gitignore`、`sbtd-workflow-onboard/templates/skills/**/SKILL.md`、`tests/**` 的结构是否可读；本机若存在 `AGENTS.md` 则一并检查，缺失时跳过。
  - 使用 Draft 2020-12 校验 `sbtd-workflow-onboard/catalog.json` 符合 `catalog.schema.json`，目录 id 唯一，且恰好包含 14 个 bundled entries 和 19 个 external entries。`skill:trellis-workflow`、`skill:trellis-channel` entries 及对应 `templates/skills/trellis-workflow/`、`templates/skills/trellis-channel/` 源目录必须不存在；`skill:sbtd-task` 必须存在，source 必须为 `templates/skills/sbtd-task`，且该目录实际包含 `SKILL.md`、`references/state.md`、`handoff.md`、`methods.md`、`presentation.md`、`strict.md`、`tooling.md`、`task-data.schema.json`、`LICENSE` 和 `NOTICE`。`templates/agents/AGENTS.global.md`、`AGENTS.project.md` 与 `templates/skills/lessons-record/` 必须是 v2 canonical 内容：共同 / default / lite / strict 路由、`.sbtd/developer` 身份来源，以及仅在明确授权迁移时读取旧 `.trellis/.developer`；`docs/prd/` 不得残留 sbtd-task、AGENTS 或 lessons-record 候选副本。每个 bundled Skill local source 必须位于 Onboard Skill 根目录内且实际存在，每个 external Skill source 必须包含合法的上游 repo、受限相对 subpath 和 canonical alias。验证 External Skill 默认 `auto` 与显式 `stable` 均只使用受管 stable set 且不访问网络，只有显式 `upstream` 才直接获取当前上游并在失败时直接报错。对任何 external canonical rename，隔离 global Skill 目录中同时预置 predecessor 与更早 legacy alias，执行 reset 等价的 stable install / migration，断言 replacement `SKILL.md` 存在、每个 predecessor 均不存在，且 JSON 结果记录 `removed`；若 canonical 已存在，也必须验证 legacy-only cleanup 同样删除 predecessor。若本机存在 `AGENTS.md`，同步核对其“本地同步规则”表：仓库管理且要求全局同步的 bundled Skill 必须具有正确的 source / target 映射，包含 `web-ui-autotest-generator`，同时保持 `AGENTS.project.md` 不在普通 sync 范围内；sync 不得把 Ponytail stable 路径或 i-have-adhd stable 路径列为 cp/rsync 目标，必须用已同步 Onboard 的 `install-external-skills --skills ponytail,ponytail-review,ponytail-audit,ponytail-debt,i-have-adhd --scope global --source auto` 安装并校验 5 个 `SKILL.md`；缺失时以 README 中已记录的 `web-ui-autotest-generator` 映射为准，不得因 `AGENTS.md` 缺失失败。
  - 验证 OMP 全局 AGENTS 契约，不依赖根 `AGENTS.md` 是否存在：以 `README.md`、`README.html`、`sbtd-workflow-onboard/SKILL.md` 和 `sbtd-workflow-onboard/REFERENCE.md` 为准。若用户主目录已存在 `.omp`（POSIX `~/.omp`，Windows `%USERPROFILE%\.omp`），sync / `init` / `reset` 必须把同一 `AGENTS.global.md` 覆盖写入 `~/.omp/agent/AGENTS.md`；不得创建缺失的 `.omp`，`check --json` 也不得通过 `omp plugin list` 产生副作用。`--global-agents-path` 只覆盖 Codex 目标；若该路径或项目 `AGENTS.md` 与 OMP/Codex 目标解析为同一文件，只保留一条写入操作。
  - 验证 Ponytail required stable 集成契约：`catalog.json` 中 `ponytail`、`ponytail-review`、`ponytail-audit`、`ponytail-debt` 均为标准 required external entries（无 installation policy / group / 安装确认分支）；stable `MANIFEST.json` 的 `ponytail` repository 记录精确 40 位 commit、MIT license 和 license 文件映射，4 个 Skill tree 与 checksum 完整，`THIRD_PARTY_NOTICES.md` 含对应条目；`onboard.py check --json` 输出 `ponytailProvider`，官方 plugin 已启用时 `provider=conflict` 且 `check` / `init` / `reset` 阻断；缺失 `~/.omp` 时 OMP 明确为 `not-configured` 且不执行 CLI，plugin 禁用或 CLI 不可用时不伪造状态。`AGENTS.global.md` 含共同路由、代码可读性规则和 book-derived 客观触发；`AGENTS.project.md` 含三模式入口、project-only 最小 fallback（含 Book Gate Plan 客观触发与 Gate lifecycle）、项目路径和硬边界；bundled `sbtd-task/SKILL.md` 承载共同 / `default` / `lite` / `strict` 工作契约，只有 strict 加载完整适用 Gate，不得复制 reviewer 状态词表。`sbtd-task/references/methods.md` 和 `strict.md` 承载 Ponytail / Code Readability 顺序；`lessons-record/SKILL.md` 以 `.sbtd/developer` 为唯一自动身份来源（本地合法优先，仅确实缺失且已验证 linked worktree 才只读主 checkout，旧 `.trellis/.developer` 只经 `references/identity-migration.md` 在明确授权迁移时读取）；各 `book-*/SKILL.md` 独占 reviewer 状态与修正回路；`project-validation` 不承载可读性规则。
  - 验证 `init` / `reset` 写入契约：init 跳过合法 Skill 壳，不因安装依赖覆盖合法壳；reset 按既有策略重装受管 Skills。AGENTS 备份后覆盖，项目 ignore 只追加缺行并用真实 Git 正反探针验证。写入前检查全部所选项目，异常状态、非法目标或新增保护会隐藏未确认数据时阻断；保留 task、identity、spec、lessons、handoff 和旧数据，不默认创建 bootstrap 或完整目录。project-only 无全局安装。Python与两安装器均不得接受旧Trellis username/platform/skip参数或调用Trellis初始化；`sbtdInit`／`sbtdProjectSetup`保留逐项目status/reason/nextStep，`--json`运行结果单文档，非零结果不混散文。最小状态检查不冒充完整任务恢复或验收。
  - 根安装器须在全局安装、MCP写入及可选项目安装前执行完整只读项目前置检查，不能仅在最终Python写入时检查；`check-projects`与`plan`复用状态/scaffold/保护判定，并传递`--skip-project-agents`范围。验证有效输入正向控制及冲突时零mutation；只读Agent version探测不能触发安装。
  - 协议模块／交换schema变更须核对严格解码、闭集字段、批准快照、资源归属／ID、累计证据和单JSON输出；不修改原生验证报告schema。检查公开入口与真实handler是否已原子接线，不能以文件存在或接口fixture通过冒充migration/deployment/recovery可执行，也不注册占位handler。目录复制或`npx skills add`不安装Python依赖；依赖须惰性加载、缺失fail-closed，必要时在完整隔离安装副本中分别验证无依赖和按副本requirements准备依赖的路径，不以宿主CI已有包推断用户副本可用，不改真实HOME或全局Python。


  - 验证能从 `ENTRYPOINT.md` 正确解析受监控工具表。
  - 验证 `UPDATE.md` 使用中文，且各工具区间起点等于 `ENTRYPOINT.md` 中该工具当前版本。
  - 验证 OMP 行可按表头语义解析：GitHub 仓库 `can1357/oh-my-pi`，备注含 `@oh-my-pi/pi-coding-agent`，通道 `stable-only`，启用监控为“是”，当前版本为 `v<semver>` 且不含 `omp/` 前缀。
  - 验证“当前版本汇总”中的 OMP 版本与版本监控表相同。
  - 验证 `UPDATE.md` 中已有区间章节的起点等于 `ENTRYPOINT.md` 中该工具当前版本。无新版本的启用工具可以没有章节；不得仅因新加入监控而补写 `当前版本 -> 当前版本`。
  - 验证 OMP 若已有 `UPDATE.md` 章节，起点和终点都是 `v<semver>`；该终点是后续写回 ENTRYPOINT 的唯一目标格式。
  - 验证 `ENTRYPOINT.md` 没有因为定时自动化而更新工具版本号。
  - 验证根 `.gitignore` 内容严格为七行且顺序一致：`.DS_Store`、`/.sbtd`、`/docs/handoffs`、`/graft`、`/.graft`、`__pycache__/`、`AGENTS.md`；与业务项目模板独立。用原生Git正反检查本地根、文件／symlink和同名业务子目录，确认共享任务／spec／lessons及ENTRYPOINT可追踪。旧工具根已不受该文件保护；检查磁盘与索引残留，未知或敏感内容先报告并等待授权，不自动删除、untrack或加入提交。保留历史lesson原文，只维护现行规则说明。验证 `git ls-files -- AGENTS.md ENTRYPOINT.md` 只包含 `ENTRYPOINT.md`。`AGENTS.md` 若存在可读取、评估或修改；缺失时跳过，不得把它的存在当作 Gate。
  - `docs/lessons.md`旧五行摘要和topic中的三／四／五行状态都是历史保留内容，不覆盖上面的现行七行验收。不得把历史字样当作恢复旧根规则的依据，也不为通过新验收改写历史lesson。
  - 验证 project-only 安装契约：付费 React Bits Skill 固定落在 `.agents/skills/react-bits-pro/SKILL.md` 且使用覆盖语义；项目 `.gitignore` 重复执行不产生重复行，现有通用保护保持，v2新模板无Trellis/GitNexus旧段。原生Git确认`/.sbtd`、`/docs/handoffs`、`/graft`、`/.graft`保护根级目录／文件／symlink且不误伤同名业务子目录；AGENTS/CLAUDE、共享`.agents`、ai/tasks含子任务和归档、docs/spec/lessons、CONTEXT/ADR、features、maestro/flow与三个可入库Web manifest可追踪。安装器探针与模板同批对齐；broad ai/docs/tests或重新包含冲突须返回具体来源，无规则覆盖则报告缺失规则，Git不可用不得报已验证。已有项目只追加新保护，不自动删除旧段、untrack数据或证明所有权／迁移完成；真实清理另经授权。报告目录本地留存并忽略，不推断为Git入库要求。
  - 共享路径验证还须覆盖公开固定分支：`docs/lessons.md`旧短入口、context ADR、季度／undated任务归档、任务附属产物及bootstrap、PRODUCT/DESIGN、测试源码、iOS／Android flow、受管React Bits Skill、根Git控制文件。精确排除这些分支也须返回真实规则来源并保留用户内容；代表性probe不是自定义路径穷举，也不授权恢复退役平台集成。
14. 最终输出必须说明：发现的版本区间、修改的文件、`CHANGELOG.md` / `README.md` / `README.html` / 本 prompt 的维护判断、验证命令和结果、跳过项及原因、剩余风险、`rtk` 使用状态。再次强调：不要 commit，不要 push，不要把最新版本写回 `ENTRYPOINT.md`。
