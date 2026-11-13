---
schema_version: 1
id: v2.2.0-rc.1-graft-0290
workflow_mode: strict
mode_source: user
mode_note: 本轮任务指令明确全程 strict；640 于 2026-11-12 在 640-skills 群确认 graft 按 0.29.0 继续支持（选甲）及
  A-G 配套改动
status: "in-progress"
branch: feat/v2.2.0-rc.1-graft-0290
created_at: '2026-11-12T23:30:01.587596+08:00'
updated_at: "2026-11-13T11:34:50.760571+08:00"
completed_at: null
---
# v2.2.0-rc.1 graft 0.29.0 支持与配套修正

## 目标与范围

640 于 2026-11-12 在 640-skills 群确认：graft 仍标为已弃用，但按 0.29.0 继续支持（选甲，以后可能摘除）。据此完成七项配套改动（A–G，见逐项改动清单）：pin 与校验值升级、启动器环境开关、Codex 钩子内部模块核对、旧图重建说明、--graft-hooks 文档修正、onboard 的 lsp/ast_grep 检测与引导、双语 CHANGELOG 未发布段更新。

本任务分轮执行。第一轮只写任务文件并登记索引，不改代码、文档、测试、CHANGELOG。后续实施轮不 commit、不 push、不开 PR、不用子代理，除非 640 另行授权。

未完整调用 grill-with-docs：七项内容、版本号、开关名单与验收方式均已由 640 确认，无领域歧义。

## strict mode 落实方式

- 任务文件在开工前经仓库 TaskStore 库 API（sbtd-workflow-onboard/scripts/sbtd_task_state.py 的 TaskStore.create）创建并落盘；阶段转换用 `transition()` 记录真实状态事件，不手改状态时间。
- 验证证据（命令、结果、失败归因）写入本文件；Book Gate Plan 已列。
- 状态停在 planned，实施轮开始后再按真实进度转换。

## 640 的决定（2026-11-12 在 640-skills 群确认）

- A. graft 版本：仍标已弃用，按 0.29.0 继续支持（选甲，以后可能摘除）。把所有写死的 0.28.0 改成 0.29.0，包括下载地址和校验值。0.29.0 的 npm 包 integrity 暂记为 `sha512-dYZA/fAI6f2uCt4OZiyAtDZ2itvD4cP1SkMwLwIa51LdEcHyPmeGwH/pbWE4qS2BfG/TqEbT6piHc+kcai/i4g==`，实施轮再从 npm registry 核对一次。
- B. 不触发登录弹窗（选乙）：启动器 sbtd_graft_entry.py 启动 graft 时，给 graft 子进程的环境加上 DO_NOT_TRACK=1（主开关，上游 README 有写），再加三个保险开关 TRAIL_CLOUD=0、GRAFT_NO_BROWSER=1、GRAFT_NO_RENAME_NOTICE=1（这三个 README 没写）。不改 Codex 全局配置。已知 0.29.0 的行为：浏览器只在 TTY 下的 `graft login` 里打开；Trail 登录提示只在 trail 品牌下出现；DO_NOT_TRACK 关掉遥测并让 cloudEnabled 为假；GRAFT_NO_RENAME_NOTICE 关掉每日改名提示和每周建议 graft upgrade 的那行。
- C. Codex 钩子 assets/graft-hook-entry.mjs 用到 0.28 的内部模块：在 0.29.0 的包里核对这些内部模块路径还在不在，必要时修改；Codex 宿主上的真跑由 CodeX 负责。
- D. 升级后旧的代码图会被拒绝，需要重建：写进升级引导和 rc.1 说明（CHANGELOG 中英两份）。
- E. 修掉 `--graft-hooks` 的文档错误：对照 install.sh、install.ps1、onboard 脚本里这个参数的实际处理，与 SKILL.md、REFERENCE.md、ENTRYPOINT.md、docs 里的说法逐条比对；找不到错就如实写没找到，不编。
- F. lsp/ast_grep 检测和引导：onboard 流程检测项目用了哪些语言，检查 omp 的 lsp 和 ast_grep 是否可用（语言服务器装没装、~/.omp/agent/config.yml 里 astGrep.enabled），缺了就引导：先问是否同意，同意给出安装/配置步骤，拒绝跳过并说明影响。omp 自带清单外的语言（例如 Julia）引导在全局 ~/.omp/agent/lsp.yml 写自定义条目。
- G. 同步更新 CHANGELOG.md 和 CHANGELOG.zh.md 的未发布段。

## 逐项改动清单

行号为编辑前基线（分支 feat/v2.2.0-rc.1-graft-0290，基线 main 5ce59d2）的行号。

### A. pin 0.28.0 → 0.29.0

全仓 `git grep '0\.28\.0'` 共 23 个文件 65 处。当前要改 13 个文件 25 处，外加 1 条 integrity 字符串（不含 0.28.0 字面量，必须同改）；不改 10 个文件 40 处。

当前要改：

| 文件 | 基线行 | 内容 | 改法 |
|---|---|---|---|
| sbtd-workflow-onboard/scripts/graft_runtime.py | 50 | GRAFT_PINNED_VERSION = "0.28.0" | 改 "0.29.0" |
| 同上 | 52 | GRAFT_TARBALL_URL 指向 graft-0.28.0.tgz | 改 graft-0.29.0.tgz |
| 同上 | 53-55 | GRAFT_TARBALL_INTEGRITY（0.28.0 的 sha512） | 改 0.29.0 的 sha512，实施轮先对 npm registry 核对 |
| 同上 | 14 | 模块 docstring 的 tarball 说明 | 改 0.29.0 |
| 同上 | 101 | _ADVICE_MISSING 文案 | 改 0.29.0 |
| sbtd-workflow-onboard/scripts/sbtd_graft_entry.py | 3, 21, 37, 869, 1002 | 模块与函数 docstring 五处版本 | 改 0.29.0 |
| sbtd-workflow-onboard/assets/graft-build-policy.json | 1 | "version":"0.28.0" | 改 "0.29.0"，形状不变 |
| sbtd-workflow-onboard/assets/graft-hook-entry.mjs | 10, 17 | 注释两处版本 | 改 0.29.0（模块路径核对见 C） |
| sbtd-workflow-onboard/assets/graft-instructions.txt | 3 | fence 文案版本 | 改 0.29.0 |
| sbtd-workflow-onboard/SKILL.md | 154 | install-graft 说明的 pin | 改 0.29.0 |
| sbtd-workflow-onboard/REFERENCE.md | 166 | pin 说明 | 改 0.29.0 |
| install.sh | 922 | fallback 显示串 | 改 0.29.0 |
| install.ps1 | 635 | $package fallback | 改 0.29.0 |
| ENTRYPOINT.md | 25, 91, 239, 330 | 监控表、工具表、graft 节、版本汇总 | 改 0.29.0；ENTRYPOINT 规则是基线跟已发布 workflow 的 pin，本次 pin 变化由本任务同步 |
| tests/test_sbtd_graft_entry.py | 33, 91, 607 | stamp 与 package.json 夹具版本 | 改 0.29.0 |
| tests/test_sbtd_probe_links.py | 55 | GRAFT_VERSION | 改 0.29.0 |
| tests/test_sbtd_upgrade_hosts.py | 29 | GRAFT_VERSION | 改 0.29.0 |

历史记录不改：

| 文件 | 处数 | 理由 |
|---|---|---|
| CHANGELOG.md（36, 79, 96） | 3 | 已发布版本条目，不重写 |
| CHANGELOG.zh.md（36, 79, 96） | 3 | 同上 |
| ai/tasks/graft-trail-code-upgrade-eval/eval-report.md | 7 | 旧评估报告，历史证据 |
| ai/tasks/graft-trail-code-upgrade-eval/task.md | 4 | 旧任务记录 |
| ai/tasks/v2.1.0-rc.3-changelog/task.md | 1 | 旧任务记录 |
| ai/tasks/v2.1.0-rc.3-release-identity-backfill/task.md | 5 | 旧任务记录 |
| ai/tasks/v2.1.0-rc.5-external-skills-repin/task.md | 4 | 旧任务记录 |
| ai/tasks/v2.1.0-rc.5-final-docs/task.md | 5 | 旧任务记录 |
| ai/tasks/v2.1.0-release/task.md | 5 | 旧任务记录 |
| sbtd-runtime/dashboard/package-lock.json（1619, 1682, 1683） | 3 | React scheduler 0.28.0，与 graft 无关 |

### B. 启动器环境开关（不触发登录弹窗）

- 事实核对：DO_NOT_TRACK=1 与 DNT=1 已在 graft_runtime.py:127-128 的 `_managed_env` 设置，sbtd_graft_entry.py:1118 的 `managed_environment` 继承该环境。本轮确认其保留并在文档说明，不重复添加。
- 新增三个保险开关：TRAIL_CLOUD=0、GRAFT_NO_BROWSER=1、GRAFT_NO_RENAME_NOTICE=1，加在 sbtd_graft_entry.py 的 `managed_environment`（现 1131-1136 行一带已有 GRAFT_NO_GITIGNORE、GRAFT_NO_IGNORE、GRAFT_NO_REFRESH），使 mcp、hook、analyze 三条子进程路径（_run_mcp 环境在 1824 行、_run_hook 在 1855 行、_run_analyze 在 1923 行，均经 managed_environment）同时生效。
- 不改 Codex 全局配置。
- 每个开关单独真跑验收，开和关各一次，记录它管的是哪个提示：DO_NOT_TRACK 管遥测与 cloudEnabled；TRAIL_CLOUD 管 Trail 登录提示；GRAFT_NO_BROWSER 管浏览器打开；GRAFT_NO_RENAME_NOTICE 管每日改名提示与每周升级提示。

### C. Codex 钩子内部模块核对

- 现状：graft-hook-entry.mjs 只导入 `dist/claude/hooks.js`（ENTRY_SUFFIX，第 33 行）并调用其 `main(event)`；启动器侧 `_proven_hook_module`（sbtd_graft_entry.py:1455）每次事件前重证该路径。
- 实施轮在真实 0.29.0 包内核对：`dist/claude/hooks.js` 是否仍在、是否仍导出 `main(event)`。路径或形状变了就改桥接与启动器校验，并同步 graft-hook-entry.mjs 第 10、17 行注释与 sbtd_graft_entry.py 相关 docstring。
- Codex 宿主上的真跑由 CodeX 负责，本任务如实记录其结果。

### D. 旧图重建说明

- 0.29.0 拒绝旧版代码图，升级后需要重建。写入升级引导（sbtd-workflow-onboard 内 upgrade 相关文案的合适位置，实施轮定具体文件与行）和 CHANGELOG 双语未发布段（见 G）。

### E. --graft-hooks 文档错误

逐条比对结果（行号为基线行号）：

- 实际处理：onboard.py:7116 为 check/plan/init/reset/init-projects 注册 `--graft-hooks`；onboard_arguments.py:269 与 :361 为 migration 注册；init-projects 传入被拒绝「project-only setup cannot change global hooks or retire global MCP entries」（sbtd_graft_deployment.py:2213-2217）；非 codex 平台传入被拒绝「OMP wiring does not include Codex hooks」（sbtd_graft_deployment.py:2218-2222）。
- install.sh 全文无 hooks 字样；init/reset 主流程对未识别参数执行 `die "Unknown option: $1"`（install.sh:800）；只有 migration/recovery/cleanup-legacy/upgrade 经 forward_workflow_mode 原样转发其余参数（install.sh:312-336、1346）。
- install.ps1 的 param 块（install.ps1:2-24）无 GraftHooks 参数，未识别命名参数在 PowerShell 参数绑定时失败；仅 -WorkflowMode 路径转发剩余参数（install.ps1:290-341）。
- 发现的错误（1 处）：REFERENCE.md:701 末句「The root installers forward this option through the implemented deployment flags.」与实际不符——两个根安装器的 init/reset 主流程都不接收 `--graft-hooks`，只有 migration 族透传路径能转发。改法：改写该句，说明根安装器只在 migration 族 workflow 透传路径转发该参数，init/reset 主流程不接收，需要时对安装后的 onboard.py 直接传。
- 比对后未发现问题：SKILL.md:41「Hooks remain a separate Codex --graft-hooks opt-in plus host trust.」与实际一致；REFERENCE.md:718-719 的示例直接调 onboard.py，与行为一致；REFERENCE.md:720「init-projects 不能装全局 hooks」与 sbtd_graft_deployment.py:2213 一致；ENTRYPOINT.md 无 --graft-hooks 表述，无错可改；docs/ 下仅 docs/prd/ 三处历史设计记录（trellis PRD 第 556、622、819、1716 行，successor-batch 第 31 行，live-apply 第 10、46 行），属历史记录不重写。
- 备查：CHANGELOG.md:250 与 CHANGELOG.zh.md:250 的 P1-07 历史条目提到 Bash 安装器转发 `--graft-hooks`，属已发布历史条目，不重写；其措辞与现状的差异记录在此备查。

### F. lsp/ast_grep 检测与引导

现状：onboard 无 lsp/ast_grep 检测（sbtd-workflow-onboard 内检索 pyright、rust-analyzer、gopls、astGrep、lsp.yml 零命中）。

实现位置：

- 新模块 sbtd-workflow-onboard/scripts/sbtd_language_tooling.py：按项目标记文件检测语言（Python：pyproject 或 .py；Rust：Cargo.toml + .rs；TS：package.json + tsconfig + .ts；Go：go.mod + .go；Julia：.jl；检测表可扩展）；检查 omp lsp 可用性（对应语言服务器是否安装）与 ast_grep 可用性（~/.omp/agent/config.yml 的 astGrep.enabled）；生成引导文案。
- 接入点：`build_project_check`（onboard.py:1480）加每项目语言检测；`build_check_results`（onboard.py:2125）加全局 lsp/ast_grep 检查项；init/init-projects 流程在写入前询问是否同意安装/配置：同意给出安装/配置步骤，拒绝则跳过并说明影响。
- omp 清单外语言（例如 Julia）：引导在全局 ~/.omp/agent/lsp.yml 写自定义条目。
- 写进引导的已知事实：omp 按启动目录找项目标记，在上层目录启动时子目录里的 Rust/TS/Go 项目找不到语言服务器；pyright 在没有 pyproject 的 git 仓库里靠全局 lsp.yml 的 rootMarkers 加 .git 才能识别。
- 验收真跑后清理：删除 Julia 的 lsp.yml 条目和只为测试安装的组件；pyright、rust-analyzer、typescript-language-server、gopls、bash-language-server、marksman 六个保留。

### G. CHANGELOG 双语未发布段

- 在 CHANGELOG.md 与 CHANGELOG.zh.md 的「## v2.2.0-rc.1 (Unreleased)」（基线第 10-16 行）追加本节改动的双语条目：pin 0.28.0 → 0.29.0（含 integrity 核对）、三个新环境开关、hook 模块核对结果、旧图需重建说明、--graft-hooks 文档修正、lsp/ast_grep 检测引导。已发布段落的 0.28.0 历史条目不改。

## Book Gate Plan

| 方法 | 触发与阶段 | 状态与证据 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求确认前 | not-required；未完整 grill，七项决定均已确认，无领域歧义 |
| book-ddia-data-design | schema、迁移或跨进程机制设计前 | proceed / 轻量；graft-build-policy.json 只改 version 值不改形状， wiring stamp 形状不变，无存储迁移；F 项只读 ~/.omp/agent/config.yml 与 lsp.yml，不写任务状态 |
| book-legacy-change-safety | 既有行为修改前 | required；改启动器环境、安装器文案与 onboard 检测流程前，先跑 tests/test_sbtd_graft_entry.py、tests/test_sbtd_probe_links.py、tests/test_sbtd_upgrade_hosts.py、tests/test_sbtd_graft_isolation.py 建立保留行为基线 |
| book-refactoring-pass | 既有生产文件编辑前 | proceed；只做必要修改，不夹带重构 |
| gherkin-bdd | 用户可见行为变化 | required；F 项 onboard 新引导的同意/拒绝两条路要有场景覆盖 |
| project-validation | 改动后 | required；聚焦测试 + 索引验证，全量以 CI 为准 |
| book-release-readiness | 运行时行为变化，验证后 | required；环境开关与检测流程改运行时行为，发布前评 |
| 独立 review 与 CI | PR 检查 | pending；本任务不用子代理 |
| ponytail-review | 修改后自检 | required；无新增抽象与依赖 |

## 验收标准

- A：上述 13 个文件的 25 处字面量与 1 条 integrity 全部改为 0.29.0；integrity 与 npm registry 实测一致；复扫 `git grep '0\.28\.0'` 残留只属于「历史记录不改」清单；tests/test_sbtd_graft_entry.py、tests/test_sbtd_probe_links.py、tests/test_sbtd_upgrade_hosts.py 及相关 graft 测试通过。
- B：0.29.0 真跑中四个开关各自开/关一次，记录各管哪个提示；DO_NOT_TRACK 原有设置保持；Codex 全局配置不变。
- C：0.29.0 包内 `dist/claude/hooks.js` 路径与 `main(event)` 形状核对结果写入本文件；如需修改，改动与证据一并记录；Codex 宿主真跑结果由 CodeX 提供并记录。
- D：升级引导与双语 CHANGELOG 均写明旧图会被 0.29.0 拒绝、需要重建。
- E：REFERENCE.md:701 末句改写为与 install.sh/install.ps1 实际行为一致；其余比对结论（无错）如实保留。
- F：云主机真跑 5 种语言样例 ×（同意/拒绝）共 10 条路径全部有记录：Python（git 仓库、无 pyproject）、Rust（Cargo.toml + .rs）、TS（package.json + tsconfig + .ts）、Go（go.mod + .go）、Julia（.jl，演示自定义 lsp.yml 条目）；跑完删除 Julia 的 lsp.yml 条目与测试专用组件，六个语言服务器保留。
- G：CHANGELOG.md 与 CHANGELOG.zh.md 未发布段双语条目一致，逐项对应。

## 真跑计划

- A（云主机）：实施轮先从 npm registry 核对 0.29.0 的 integrity，再真实安装 @nanonets/graft@0.29.0 并经受管链路 build 冒烟；记录版本输出与图产物。
- B（云主机，状态：r3c3 已跑完 8 条，其中两组未验证到）：四个开关 DO_NOT_TRACK、TRAIL_CLOUD、GRAFT_NO_BROWSER、GRAFT_NO_RENAME_NOTICE 逐个真跑，每个各开一次、各关一次，记录每个开关管的提示是否出现/消失。r3c3 已跑完 8 条：DO_NOT_TRACK 与 GRAFT_NO_RENAME_NOTICE 两组开/关对照成立；TRAIL_CLOUD 与 GRAFT_NO_BROWSER 两组未能触发对应提示，开关有没有用没验证到，不算通过。证据见「验证证据」节 r3c3 小节。
- C：仓库内静态核对 0.29.0 包内容（实施轮已做）；Codex 钩子真跑由 CodeX 负责，本任务只记录。CodeX 真跑结果已写入「验证证据」节 CodeX 小节。
- F（云主机，状态：10 条已全部跑完）：5 种语言样例（Python/Rust/TS/Go/Julia）各走同意/拒绝两条路共 10 条路径，记录检测输出、引导文案与实际安装/配置/跳过结果；跑完按 F 项清理规则还原环境。r3d 已跑完 Python/Rust/TS 共 6 条（证据见「验证证据」节 r3d 小节）；r3e 已跑完 Go 与 Julia 共 4 条，Julia 同意路径另在真实全局 lsp.yml 上演示了自定义条目写入并已逐字节还原（证据见「验证证据」节 r3e 小节）。
- 验证命令（实施轮执行并记录结果）：聚焦 unittest（test_sbtd_graft_entry、test_sbtd_probe_links、tests.test_sbtd_upgrade_hosts、test_graft_runtime、test_sbtd_graft_isolation）、TaskStore 只读索引预览比对、`git grep '0\.28\.0'` 复扫。pytest 不在本环境装，按项目既有方式用 unittest 运行同一文件。

## 验证证据

### r2 轮全量测试（在 omp 会话外面跑）

- 执行位置：这次全量测试在 omp 会话外面跑——OMP 机器人在云主机 shell 里直接执行，不是 omp 会话跑的。
- 命令：`python3 -m unittest discover -s tests -p 'test_*.py' -v`（云主机没有装 pytest）。
- 测的提交：392348c；Python 3.13.5。
- 时间：开始 2026-11-13 02:24:37 +0800，结束 2026-11-13 04:03:32 +0800；unittest 报告用时 1413.492 秒；中间云主机多次整体暂停，墙钟时间因此远大于 unittest 计时。
- 汇总：Ran 2484，failures=1，skipped=65，errors=0，其余 2418 项通过，退出码 1。
- 唯一失败：sbtd-runtime/tests/test_stats_query.py 的 NormalizeScopeTests.test_iana_queries_and_dst_work_without_system_timezone_data。
- 失败归因：2026-11-13 04:25:53 +0800 在 main 5ce59d2 上用同一条 unittest discover 命令加 `-k` 该用例名单跑，同样失败，报 ModuleNotFoundError: No module named 'tzdata' → ZoneInfoNotFoundError 'Asia/Tokyo'。结论：云主机 Python 没装 tzdata 包，是环境问题，main 上一样，不是本分支引起的；以 CI 结果为准。
- 分支核对（r2c 记录轮在本工作树执行）：`git diff --name-only 5ce59d2..HEAD` 经 `grep -i stats` 过滤无任何命中；`git log 5ce59d2..HEAD -- sbtd-runtime/tests/test_stats_query.py sbtd-runtime/stats_query.py sbtd-runtime/stats/` 为空；本任务在基线 5ce59d2 之上的三个提交（cfda1ff、3959711、392348c）不触碰 sbtd-runtime 下任何文件。核对结论：本分支没改 sbtd-runtime/stats 相关文件。

### r3c3 轮 B 项开关真跑（在 omp 会话里跑）

执行方式：8 条全部走真实启动器。驱动脚本导入本工作树的 sbtd_graft_entry 并调用其 `main()`，`managed_environment` 真实构造，graft 子进程由启动器真实拉起；驱动脚本与原版启动器的偏差只有三处——临时 HOME 落到按用例命名的目录、退出后把临时 HOME 改名保留供检查（不删除）、“关”的用例从受管环境里只删一个开关。graft 为临时隔离目录里的 0.29.0（`--version` 实测 0.29.0），node 为 v22.20.0，项目根是临时目录里的 git 仓库（带 graft/ 上下文与接线 stamp，启动器校验通过）。启动器命令统一为 `analyze … check`（只读命令）。任务文件不落本机路径，下文 `<r3tmp>` 指本轮在临时目录下的隔离目录，`<node>` 指 realpath 后的 node v22.20.0。

公共命令形状（每条只换用例名与被删开关）：

```
python3 <r3tmp>/drive.py <用例> <被删开关或 -> -- analyze --root <r3tmp>/repo --node <node> --entry <r3tmp>/prefix/lib/node_modules/@nanonets/graft/dist/cli.js check
```

伪终端的两条在最外层套了 `env -u CI -u CLAUDECODE script -qec '<上面这条>' /dev/null`。

1. DO_NOT_TRACK 开（非伪终端；启动器默认，DO_NOT_TRACK=1 保留）：2026-11-13 07:37:54 +0800 开始，同秒结束，退出码 0。stderr 为空；stdout 是 check 的 JSON（`graph.ok=true`、`nodes=2`、`pendingIds` 为 a.py 与 a.py#f）。保留的临时 HOME 里 `.graft/` 只有启动器预置的 update-check.json，没有 telemetry.json、没有 telemetry-queue.ndjson。结论：默认开的状态下遥测告知不出现、遥测事件不入队。
2. DO_NOT_TRACK 关（非伪终端；只删 DO_NOT_TRACK，DNT=1 与其余默认不变）：2026-11-13 07:38:02 +0800，退出码 0。stderr 出现一次性遥测告知两行：「· graft collects anonymous usage stats (no code, no file paths, no queries).」与「  What exactly: https://github.com/trailhq/Trail-Code/blob/main/TELEMETRY.md. Turn it off with `graft telemetry disable`.」；stdout JSON 与第 1 条一致。保留 HOME 里 `.graft/telemetry.json` 记下 noticeShownAt=2026-11-12T23:38:02Z 与 flushedAt，`.graft/telemetry-queue.ndjson` 排队两条匿名事件（first_run 与 query，command=check，properties 含 app_version=0.29.0、os=linux、node_major=22）。结论：DO_NOT_TRACK 管遥测——删掉后告知出现、事件本地入队，与第 1 条构成对照。边界：本轮未抓包，是否有外发请求不在证据范围内；cloudEnabled 在本条仍为假（TRAIL_CLOUD=0 保留）。
3. TRAIL_CLOUD 开（非伪终端；TRAIL_CLOUD=0 保留）：2026-11-13 07:38:13 +0800，退出码 0，stderr 为空，stdout JSON 同第 1 条。结论：默认开的状态下无 Trail 登录提示。
4. TRAIL_CLOUD 关（非伪终端；只删 TRAIL_CLOUD）：2026-11-13 07:38:20 +0800，退出码 0，stderr 为空，stdout 与第 3 条逐字节一致（diff 无输出）。这条没测出区别，原因照实写：0.29.0 的 cloudEnabled 除了看 TRAIL_CLOUD 还要求 telemetryOn（dist/cloud/workspace.js），而启动器默认的 DO_NOT_TRACK=1 在本条仍保留，telemetryOn 为假，所以删掉 TRAIL_CLOUD 后 cloudEnabled 依然为假；Trail 登录提示（status 里的「workspace not signed in · run trail login」）只出现在 status 输出，而启动器 analyze 的封闭只读命令集（ask/map/skeleton/callers/check/grep/blast）不含 status/login。在「只删一个开关、其余保持启动器默认」的限制下，这条路上 TRAIL_CLOUD 没有可观察口。
5. GRAFT_NO_BROWSER 开（非伪终端；GRAFT_NO_BROWSER=1 保留；记录 opener 调用的 shim xdg-open 放在 PATH 最前）：2026-11-13 07:38:38 +0800，退出码 0，stderr 为空，stdout 与基线一致；opener 日志跑前 1 行、跑后 1 行（现存那 1 行是上一轮调查遗留，非本轮产生）。结论：默认开的状态下无浏览器打开。
6. GRAFT_NO_BROWSER 关（非伪终端；只删 GRAFT_NO_BROWSER，shim 同第 5 条）：2026-11-13 07:38:45 +0800，退出码 0，stderr 为空，stdout 与基线一致；opener 日志跑前 1 行、跑后 1 行，没有新增。这条没测出区别，原因照实写：0.29.0 里 openBrowser 只有一个调用点（dist/cli.js 的 login 流程），analyze 的封闭只读命令集走不到 login，所以开、关两条都不会触发浏览器。
7. GRAFT_NO_RENAME_NOTICE 开（伪终端，`env -u CI -u CLAUDECODE script -qec … /dev/null`；GRAFT_NO_RENAME_NOTICE=1 保留）：2026-11-13 07:38:54 +0800，退出码 0。伪终端日志里 JSON 带 CRLF 行尾，证明子进程 stderr 确是 TTY；grep「graft is now trail」命中 0 行。结论：默认开的状态下改名提示在 TTY 下也不出现。
8. GRAFT_NO_RENAME_NOTICE 关（伪终端，同样 `env -u CI -u CLAUDECODE`；只删 GRAFT_NO_RENAME_NOTICE）：2026-11-13 07:43:52 +0800，退出码 0。伪终端日志开头出现两行：「· graft is now trail. this ran trail build --check, and graft keeps working (shown once a day)」「· run graft upgrade to get the trail command too」，随后是 check 的 JSON；保留 HOME 里 `.graft/rename-notice.json` 写入 `{"shownAt":1794527033296}`。结论：GRAFT_NO_RENAME_NOTICE 管每日改名提示与每周升级提示——删掉后提示在 TTY 下出现，与第 7 条构成对照。注：提示里的「this ran trail build --check」是 0.29.0 把 graft check 映射成 trail 叫法（包内 RENAMED 表），照实记录。

小结：8 条里 4 条验证到开关作用——DO_NOT_TRACK 两条与 GRAFT_NO_RENAME_NOTICE 两条各自构成开/关对照，结果符合预期。TRAIL_CLOUD 两条与 GRAFT_NO_BROWSER 两条均未能触发对应提示，开关有没有用没验证到，不算通过；原因照上面第 4、6 条记录保留：启动器只走 analyze 的封闭只读命令集，Trail 登录提示只在 status 输出出现、浏览器只在 login 流程打开，这条路碰不到登录和浏览器（TRAIL_CLOUD 一条还叠加启动器默认 DO_NOT_TRACK=1 使 telemetryOn 为假）。

### r3d 轮 F 项前半真跑（在 omp 会话里跑）：Python/Rust/TS × 同意/拒绝共 6 条

执行方式：样例项目建在临时目录 `<r3dtmp>`（python-proj 是 git 仓库、无 pyproject.toml、内含 a.py；rust-proj 含 Cargo.toml 与 src/main.rs；ts-proj 含 package.json、tsconfig.json 与 src/index.ts）。驱动脚本导入本工作树的 onboard 模块，用 onboard 自己的 build_parser() 解析参数（`init --projects-root <样例项目> --yes --json`，同意路径再加 `--language-tooling`），再调用 init 流程使用的同一入口 run_language_tooling_step（onboard.py 第 7115 行处被 init 调用），并用同一输出函数 print_language_tooling（onboard.py 第 7160 行处被 init 调用）打印。与完整 init 流程的偏差只有两处：HOME 指向按用例新建的空目录（真实全局 config.yml 与 lsp.yml 不参与、不被写）；「拒绝」用例把 PATH 中语言服务器所在目录替换为排除该服务器二进制的影子目录（符号链接目录，服务器真实文件不动，不卸载任何东西）。版本：omp 18.19.0；pyright 1.1.414；rust-analyzer 0.3.3113-standalone；typescript-language-server 5.3.0。公共命令形状：`python3 <r3dtmp>/drive.py <用例名> <refuse|consent> <语言> <服务器命令> <hide|show>`。

1. Python 拒绝（hide pyright）：2026-11-13 10:08:02 +0800 开始，10:08:03 结束，退出码 0。检测输出：项目识别为 Python（依据扩展名 .py；markers 为空，因为没有 pyproject.toml）；`Python server pyright: missing`；`omp ast-grep: not-configured`。引导文案：「Python was detected but no omp language server for it is on PATH.」，步骤「Install a server, for example: npm install -g pyright」；报告 notes 原文：「A Git repository without pyproject.toml needs the global ~/.omp/agent/lsp.yml to add .git to pyright's rootMarkers, or omp does not treat it as a Python project root.」。实际动作：零写入（`writes: []`），临时 HOME 跑后没有任何文件；状态 needs-confirmation；跳过影响：ast-grep 结构化搜索保持不可用。结论：拒绝路径符合预期——检测正确、引导给出、配置不写。
2. Python 同意（pyright 在 PATH 上）：2026-11-13 10:08:10 +0800 开始，同秒结束，退出码 0。检测输出：`Python server pyright: available`。实际动作：写入 enable-ast-grep → 临时 HOME 的 .omp/agent/config.yml，文件内容为 `astGrep:` 加 `  enabled: true` 两行；状态 configured；未写 lsp.yml，未安装任何组件。结论：同意路径符合预期——只写 astGrep 配置，语言服务器本体按设计不代装。
3. Rust 拒绝（hide rust-analyzer）：2026-11-13 10:08:24 +0800 开始，同秒结束，退出码 0。检测输出：项目识别为 Rust（markers 命中 Cargo.toml，扩展名 .rs）；`Rust server rust-analyzer: missing`。引导步骤：「Install a server, for example: rustup component add rust-analyzer」。实际动作：零写入，临时 HOME 跑后没有任何文件；状态 needs-confirmation。结论：拒绝路径符合预期。
4. Rust 同意（rust-analyzer 在 PATH 上）：2026-11-13 10:08:31 +0800 开始，同秒结束，退出码 0。检测输出：`Rust server rust-analyzer: available`。实际动作：写入 enable-ast-grep → 临时 HOME 的 config.yml（astGrep.enabled: true）；状态 configured；未写 lsp.yml，未安装任何组件。结论：同意路径符合预期。
5. TypeScript 拒绝（hide typescript-language-server）：2026-11-13 10:08:36 +0800 开始，同秒结束，退出码 0。检测输出：项目识别为 TypeScript（markers 命中 package.json 与 tsconfig.json，扩展名 .ts）；`TypeScript server typescript-language-server: missing`。引导步骤：「Install a server, for example: npm install -g typescript-language-server typescript」。实际动作：零写入，临时 HOME 跑后没有任何文件；状态 needs-confirmation。结论：拒绝路径符合预期。
6. TypeScript 同意（typescript-language-server 在 PATH 上）：2026-11-13 10:08:42 +0800 开始，同秒结束，退出码 0。检测输出：`TypeScript server typescript-language-server: available`。实际动作：写入 enable-ast-grep → 临时 HOME 的 config.yml；状态 configured；未写 lsp.yml，未安装任何组件。结论：同意路径符合预期。

小结：6 条全部跑通，结果与预期一致——检测输出、引导文案、同意/拒绝两路的写入差异都符合 F 项设计；三种语言都在 omp 自带清单内，同意路径不产生 lsp.yml 写入；onboard 不代装语言服务器本体，引导只列安装命令。真实全局文件跑前跑后 sha256 不变：lsp.yml 跑前 e4b18a8e0a6224c66ac85fa6b34db2a30e594861536888996b7541d66e54aaa0、跑后 e4b18a8e0a6224c66ac85fa6b34db2a30e594861536888996b7541d66e54aaa0；config.yml 跑前 7f193e4fb8b92960b07a12911aaa9f40d37e748ecf764ba347282071a44bbf56、跑后 7f193e4fb8b92960b07a12911aaa9f40d37e748ecf764ba347282071a44bbf56。跑后 pyright、pyright-langserver、rust-analyzer、typescript-language-server、gopls、bash-language-server、marksman 全部仍在 PATH 上。本轮没发现阻塞问题，代码没改、测试没改（实施轮已有的语言工具单测 26 项在本轮跑前复跑通过：python3 -m unittest tests.test_sbtd_language_tooling，OK，0.034 秒）。`<r3dtmp>` 下的样例项目、临时 HOME、影子目录与日志全部保留在临时目录供检查；没有为测试安装任何组件，无需卸载。Go 与 Julia 的同意/拒绝共 4 条由 r3e 真跑。

### r3e 轮 F 项后半真跑（在 omp 会话里跑）：Go/Julia × 同意/拒绝共 4 条

执行方式：与 r3d 相同——样例项目建在临时目录 `<r3etmp>`（go-proj 含 go.mod 与 main.go；julia-proj 只含 hello.jl），驱动脚本同样导入本工作树的 onboard 模块，用 onboard 自己的 build_parser() 解析参数（`init --projects-root <样例项目> --yes --json`，同意路径再加 `--language-tooling`），再调用 init 流程使用的同一入口 run_language_tooling_step 与同一输出函数 print_language_tooling；与完整 init 流程的偏差同样只有两处——HOME 指向按用例新建的空目录（真实全局 config.yml 与 lsp.yml 不参与、不被写），「拒绝」用例把 PATH 中语言服务器所在目录替换为排除该服务器二进制的影子符号链接目录（真实文件不动、不卸载任何东西）。版本：omp 18.19.0；gopls v0.24.0；云主机没有安装 Julia 与 Julia 语言服务器（which julia 无命中），按事实记录、本轮不安装。公共命令形状：`python3 <r3etmp>/drive.py <用例名> <refuse|consent> <语言> <服务器命令或 -> <hide|show>`。

1. Go 拒绝（hide gopls）：2026-11-13 10:29:38 +0800 开始，同秒结束，退出码 0。检测输出：项目识别为 Go（markers 命中 go.mod，扩展名 .go）；`Go server gopls: missing`；`omp ast-grep: not-configured`。引导文案：「Go was detected but no omp language server for it is on PATH.」，步骤「Install a server, for example: go install golang.org/x/tools/gopls@latest」。实际动作：零写入（`writes: []`），临时 HOME 跑后没有任何文件（find 计数 0）；状态 needs-confirmation；跳过影响：ast-grep 结构化搜索保持不可用。影子目录里 gopls 缺席、其余条目照常，真实 gopls 仍在 PATH 上。结论：拒绝路径符合预期——检测正确、引导给出、配置不写。
2. Go 同意（gopls 在 PATH 上，v0.24.0）：2026-11-13 10:29:49 +0800 开始，同秒结束，退出码 0。检测输出：`Go server gopls: available`。实际动作：写入 enable-ast-grep → 临时 HOME 的 .omp/agent/config.yml，内容为 `astGrep:` 加 `  enabled: true` 两行；状态 configured；未写 lsp.yml，未安装任何组件。结论：同意路径符合预期——只写 astGrep 配置，语言服务器本体按设计不代装。
3. Julia 拒绝（Julia 不在 omp 自带清单，无服务器二进制可隐藏）：2026-11-13 10:29:57 +0800 开始，同秒结束，退出码 0。检测输出：项目识别为 Julia（依据扩展名 .jl，markers 为空）；`Julia: custom lsp.yml entry missing`；notes 原文：「omp has no built-in Julia server; a custom entry in the global ~/.omp/agent/lsp.yml is required.」。引导文案：「Julia was detected; omp has no built-in server for it, so a custom lsp.yml entry is required.」，步骤两条：「Install the server itself: julia -e 'import Pkg; Pkg.add(\"LanguageServer\")'」与「Consent to the pending lsp.yml write to register the custom server entry shown in pendingWrites.」；pendingWrites 列出 add-lsp-server 的完整条目（command 为 julia，args 为 `--startup-file=no --history-file=no -e 'using LanguageServer; runserver()'`，fileTypes 为 .jl，rootMarkers 含 Project.toml、JuliaProject.toml、.git）。实际动作：零写入，临时 HOME 跑后没有任何文件；状态 needs-confirmation；跳过影响原文：「omp cannot attach any language server to Julia files without the custom entry.」。结论：拒绝路径符合预期——检测正确、自定义条目引导给出、配置不写。
4. Julia 同意：分两段。第一段（临时 HOME）：2026-11-13 10:30:06 +0800 开始，同秒结束，退出码 0。实际动作：写入 enable-ast-grep → 临时 HOME 的 .omp/agent/config.yml（astGrep.enabled: true）；写入 add-lsp-server → 临时 HOME 的 .omp/agent/lsp.yml，内容为 servers: 下 julia-languageserver 完整条目（与第 3 条 pendingWrites 里的形状一致）；状态 configured；未安装任何组件。第二段（真实全局 lsp.yml 演示，用模块自身的 `_add_lsp_server`——init 流程调用的同一函数——把同一自定义条目写进真实全局 ~/.omp/agent/lsp.yml）：2026-11-13 10:30:32 +0800 记录跑前 sha256 e4b18a8e0a6224c66ac85fa6b34db2a30e594861536888996b7541d66e54aaa0；10:30:42 写入完成（退出码 0），随即用真实 HOME 复跑 check_language_tooling：julia 的 customConfigured 变为 true、ready 变为 true、报告 status 变为 ready、pendingWrites 清空；10:30:46 记录写后 sha256 83a9fd0b53cce6b35e9f0b81bf824c1d15a71028e9c617046e509ad8e69cc38f，文件内容确认 julia-languageserver 条目在、既有 pyright 条目（含 .git rootMarker）原样保留。验证完毕即删：10:30:55 用该函数自己生成的 lsp.yml.sbtd-backup 逐字节还原并删掉该备份文件，删后 sha256 e4b18a8e0a6224c66ac85fa6b34db2a30e594861536888996b7541d66e54aaa0，与任务笔记目录里的备份 lsp.yml.before-r3  cmp 无输出、逐字节一致；再跑 check_language_tooling 确认 julia 回到 customConfigured false、报告 status 回到 action-required。结论：同意路径符合预期——临时 HOME 两笔写入正确；真实全局 lsp.yml 的自定义条目写入、生效、还原三步都验证到，最终文件与备份逐字节一致。

小结：4 条全部跑通，结果与预期一致——Go 在 omp 自带清单内，同意路径只写 astGrep 配置；Julia 不在清单内，引导指向全局 lsp.yml 自定义条目，同意路径的写入在临时 HOME 与真实全局文件上都验证到，真实文件已还原。真实全局文件 sha256：lsp.yml 跑前 e4b18a8e0a6224c66ac85fa6b34db2a30e594861536888996b7541d66e54aaa0、写后 83a9fd0b53cce6b35e9f0b81bf824c1d15a71028e9c617046e509ad8e69cc38f、删后 e4b18a8e0a6224c66ac85fa6b34db2a30e594861536888996b7541d66e54aaa0（与备份逐字节一致，cmp 无输出）；config.yml 本轮未动，跑前 7f193e4fb8b92960b07a12911aaa9f40d37e748ecf764ba347282071a44bbf56、跑后 7f193e4fb8b92960b07a12911aaa9f40d37e748ecf764ba347282071a44bbf56。跑后 pyright、pyright-langserver、rust-analyzer、typescript-language-server、gopls、bash-language-server、marksman 全部仍在 PATH 上。本轮没发现阻塞问题，代码没改、测试没改（实施轮已有的语言工具单测 26 项在本轮跑前复跑通过：python3 -m unittest tests.test_sbtd_language_tooling，OK，0.028 秒）。`<r3etmp>` 下的样例项目、临时 HOME、影子目录与日志全部保留在临时目录供检查；没有为测试安装任何组件，无需卸载。F 项 10 条路径至此全部真跑完成（r3d 6 条 + r3e 4 条）。

### CodeX 轮 C 项 Codex 钩子真跑（由 CodeX 在 Codex 宿主上跑，本任务照实记录）

- 版本：codex 0.167.1、node v22.20.0、graft 0.29.0（graft 装在单独目录，npm integrity 与锁定值 sha512-dYZA/fAI6f2uCt4OZiyAtDZ2itvD4cP1SkMwLwIa51LdEcHyPmeGwH/pbWE4qS2BfG/TqEbT6piHc+kcai/i4g== 一致）；测试提交 62c9e78。
- 真跑会话：2026-11-13 05:08:01 +0800 开始，05:08:26 结束，退出码 0；触发 4 个 hook 事件；调用链为 sbtd_graft_entry.py hook → graft-hook-entry.mjs → 0.29.0 包的 dist/claude/hooks.js，全程没有引用 0.28.0；INDEX.md 已注入；DO_NOT_TRACK、TRAIL_CLOUD、GRAFT_NO_BROWSER、GRAFT_NO_RENAME_NOTICE 四个开关都在 hook 拉起的进程环境里。
- 限制（照实记录）：本次用了 --dangerously-bypass-hook-trust，作用只是跳过 hook 信任提示；hooks 配置只放在临时项目的 .codex/hooks.json，信任记录在隔离的 CODEX_HOME，Codex 全局配置没改，没用禁用的参数；遥测只能算有限通过——没有抓包，是否有外发请求不在证据范围内；会话中模型调用了全局安装的 0.28.0，打印了升级提示；第一次 exec 因账号不能用的模型失败、退出码 1，但 SessionStart 已触发；直接跑启动器与 graft-hook-entry.mjs 的两次补充运行退出码都是 0，只作补充证据。
- CodeX 的更正：hook 子进程不是终端，所以「没出现改名提示」在这条路上证明不了什么；这次 hook 真跑只证明四个开关进入了进程环境，GRAFT_NO_RENAME_NOTICE 是否管用以 B 项伪终端开/关对照（r3c3 小节第 7、8 条）为准。
- 会话内模型（照 CodeX 报告记录）：gpt-5.4-mini 第一次 exec，成功请求 0 次；gpt-6.1-sol 第二次 exec，1 轮，3 次 shell 调用，1 次文件修改。
- 证据摘要文件 sha256：1dc94a9172703cf2ed9c8b4580ad28f38009726a6765a2e0562c9a75be62d0f9。

### 尚未完成的真跑项

无。B 项 8 条开关路径（r3c3 小节，TRAIL_CLOUD 与 GRAFT_NO_BROWSER 两组未触发的限制照实保留）、F 项 10 条语言路径（r3d 与 r3e 小节）、C 项 Codex 钩子真跑（CodeX 小节）均已跑完并记录。

## r3c3 运行环境与会话记录

### sbtd-graft MCP 说明

本轮 omp 启动时报 "MCP subprocess closed stdout before responding"。原因：sbtd_graft_entry.py 的 mcp 路径启动时先校验项目根——工作进程所在目录必须属于某个 Git 仓库、选中的项目根必须有 graft/ 上下文目录；本工作树没有 graft/ 目录，于是以退出码 2 退出，输出 "the selected project root has no graft/ context directory"（在非 Git 目录下则是 "the process working directory does not belong to a Git repository"）。B/F 两项真跑走命令行启动器和临时隔离目录里的 graft 0.29.0，不经过这个 MCP，所以不影响真跑结论。全局 MCP 配置指向的仍是全局安装的 graft 0.28.0，这次没改。

### 会话记录

- 原会话 01a1d190-d3cc-7617-84e5-54db40113155 因太大停用：续跑时整个会话 1.7MB，模型每次请求开头要等好几分钟，碰上云主机整机暂停就断。
- 本轮（r3c3）会话 id：01a1d21a-df8d-7313-8822-cd280f814c96；主 agent 用 k3:max，密钥从环境变量 KIMI_API_KEY 读取。
- 起止时间（均为北京时间）：进程启动 2026-11-13 07:32:18（会话文件创建时间），第一次命令 07:32:38，提交 efdf21d 于 08:02:17，进程正常退出 08:02:41（不是看门狗结束的）。
- 期间云主机暂停三次，看门狗按规则重新计时：07:43:16 检测到（间隔 288 秒）、07:48:06（170 秒）、08:01:01（593 秒）。
- 本轮次数：k3:max 回复 50 次，工具调用 55 次，工具报错 1 次；没有其他模型调用。
- 上一轮（r3c4）会话 id：01a1d26c-3cec-72ed-b034-4d75ce338dc0；主 agent 用 k3:max，密钥从环境变量 KIMI_API_KEY 读取。
- r3c4 起止时间（均为北京时间）：会话创建 2026-11-13 09:01:11，提交 742bb76 于 09:04:16，进程正常退出 09:04:28。
- r3c4 次数：k3:max 回复 10 次，工具调用 14 次，工具报错 0 次；没有其他模型调用。
- 本轮（r3d）会话 id：01a1d2a1-dfa4-723d-97a8-8a8c6f03b454；主 agent 用 k3:max，密钥从环境变量 KIMI_API_KEY 读取。
- r3d 起止时间（均为北京时间）：会话创建 2026-11-13 09:59:46（会话文件创建时间），提交 6e1c1a1 于 10:14:18，进程正常退出 10:14:38。
- r3d 次数：k3:max 回复 45 次，工具调用 56 次，工具报错 0 次；没有其他模型调用。
- 本轮（r3e）会话 id：01a1d2b9-d191-7199-89b0-f462818147bc；主 agent 用 k3:max，密钥从环境变量 KIMI_API_KEY 读取；r3e 起止时间（均为北京时间）：会话创建 2026-11-13 10:25:55（会话文件创建时间），提交 52dc012 于 10:58:38，进程正常退出 10:59:03（不是看门狗结束的）；期间云主机暂停三次，看门狗按规则重新计时：10:33:51 检测到（间隔 105 秒）、10:42:00（369 秒）、10:53:13（553 秒），联网出错重试 1 次后恢复。
- r3e 次数：k3:max 回复 40 次，工具调用 47 次，工具报错 1 次；没有其他模型调用。
- 本轮（r3f）会话 id：01a1d2e4-53af-70ec-8e9a-d4ccb86d7d35；主 agent 用 k3:max，密钥从环境变量 KIMI_API_KEY 读取；会话创建 2026-11-13 11:12:21（北京时间，会话文件创建时间）；r3f 次数由推送后的 PR 正文记录。

## 模型记录

- 主 agent 用 k3:max，密钥从环境变量 KIMI_API_KEY 读取。
- 每轮结束后把该轮真实数字填进下表；只写实际发生的数字。

| 轮次 | 用途 | 模型 | 回复次数 | 工具调用次数 | 工具报错次数 | 结果 |
|---|---|---|---|---|---|---|
| r2 | 实施 | k3:max | 115 | 139 | 0 | 完成三项提交（cfda1ff pin 0.29.0、3959711 语言检测引导、392348c 文档修正与重建说明）；进程在等后台全量测试时退出 |
| r2b | 收尾 | k3:max | 4 | 2 | 1（ECONNRESET 网络重试） | 进程在等后台测试时退出 |
| r2c | 记录 | k3:max | 10 | 14 | 0 | 只写记录：补验证证据、状态事件与 r2/r2b 模型数字，不改代码、文档、CHANGELOG、测试 |
| r3 | B/F 真跑 | k3:max | 40 | 53 | 1 | graft --version 输出 0.29.0 后云主机整机暂停，看门狗停掉进程；本文件未改、无新提交。起止实数（均为北京时间）：2026-11-13 05:01:47 起，最后写入 05:12:59，05:29:31 检测到云主机整机暂停 1004 秒，看门狗 05:31:31 结束 |
| r3b | B/F 真跑（续） | k3:max | 27（增量） | 28（增量） | 1 | 2026-11-13 05:48:58 起（北京时间），最后写入 06:06:06；期间云主机整机暂停三次：05:59:05 检测到 247 秒、06:09:18 检测到 193 秒、06:21:39 检测到 621 秒；看门狗 06:23:39 结束；无新提交 |
| r3c | B/F 真跑（续） | k3:max | 1（增量） | 0 | 1 | 2026-11-13 06:53:03 起（北京时间）；06:53:43 为改按拆分方案由启动者停止；无新提交 |
| r3c2 | B/F 真跑（续） | k3:max | 1（增量） | 0 | 1 | 2026-11-13 06:54:26 起（北京时间）；07:03:13 检测到云主机整机暂停 227 秒，看门狗 07:05:13 结束；请求被中止，模型没有输出；无新提交 |
| r3c3 | B 项真跑与记录 | k3:max | 50 | 55 | 1 | 8 条开关路径真跑完成并写入本文件（DO_NOT_TRACK、GRAFT_NO_RENAME_NOTICE 两组对照成立；TRAIL_CLOUD、GRAFT_NO_BROWSER 两组未能触发，未验证到开关作用）；本轮有一次提交，不推送 |
| r3c4 | 记录 | k3:max | 10 | 14 | 0 | 只写记录：修正 B 项措辞并补 r3c3 会话实数；提交 742bb76，不推送；进程正常退出 |
| r3d | F 项前半真跑与记录 | k3:max | 45 | 56 | 0 | Python/Rust/TS 同意/拒绝共 6 条路径真跑完成并写入本文件；提交 6e1c1a1，不推送；进程正常退出 |
| r3e | F 项后半真跑与记录 | k3:max | 40 | 47 | 1 | Go/Julia 同意/拒绝共 4 条路径真跑完成并写入本文件；Julia 同意路径在真实全局 lsp.yml 写入自定义条目后逐字节还原；提交 52dc012，不推送；进程正常退出 |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-13T00:05:32.495495+08:00 | planned | in-progress | 实施轮开始：A pin 升级、B 启动器开关、C hook 模块核对、D 重建说明、E --graft-hooks 文档修正、F 语言工具检测引导、G 双语 CHANGELOG | feat/v2.2.0-rc.1-graft-0290 工作树；基线测试 312 通过（skipped=23）：python3 -m unittest tests.test_sbtd_graft_entry tests.test_sbtd_probe_links tests.test_sbtd_upgrade_hosts tests.test_graft_runtime tests.test_sbtd_graft_isolation；npm view @nanonets/graft@0.29.0 dist.integrity 实测 sha512-dYZA/fAI6f2uCt4OZiyAtDZ2itvD4cP1SkMwLwIa51LdEcHyPmeGwH/pbWE4qS2BfG/TqEbT6piHc+kcai/i4g== 与计划值一致 |
| 2026-11-13T04:28:04.606917+08:00 | in-progress | in-progress | r2 实施轮退出：三项提交完成后进程在等后台全量测试时退出（r2c 补记，退出时刻未单独记录） | 提交 cfda1ff、3959711、392348c；模型记录表 r2 行 |
| 2026-11-13T04:28:04.606917+08:00 | in-progress | in-progress | r2b 收尾轮退出：进程同样在等后台测试时退出（r2c 补记，退出时刻未单独记录） | 模型记录表 r2b 行 |
| 2026-11-13T04:28:04.606917+08:00 | in-progress | in-progress | r2c 记录轮：只写记录——补验证证据、状态事件与 r2/r2b 模型数字，不改代码、文档、CHANGELOG、测试 | 本文件本轮改动；全量测试证据见「验证证据」节 |
| 2026-11-13T07:50:13.363609+08:00 | in-progress | in-progress | r3c3 真跑轮：B 项四开关 8 条路径真跑完成（DO_NOT_TRACK、GRAFT_NO_RENAME_NOTICE 两组对照成立；TRAIL_CLOUD、GRAFT_NO_BROWSER 两组未能触发、未验证到开关作用），sbtd-graft MCP 说明与会话记录一并写入；不改代码、文档、CHANGELOG、测试 | 验证证据节 r3c3 小节；模型记录表 r3c3 行 |
| 2026-11-13T09:03:22.669363+08:00 | in-progress | in-progress | r3c4 记录轮：只改本文件——修正 B 项措辞（TRAIL_CLOUD、GRAFT_NO_BROWSER 两组未能触发、不算通过），补 r3c3 真实次数与起止时间；不改代码、文档、CHANGELOG、测试，不跑真跑 | r3c4 会话 id 01a1d26c-3cec-72ed-b034-4d75ce338dc0，起始北京时间 2026-11-13 09:01:11；r3c4 次数由 r3d 写入 |
| 2026-11-13T10:13:16.410149+08:00 | in-progress | in-progress | r3d 真跑轮：F 项前半 Python/Rust/TS 同意/拒绝共 6 条路径真跑完成，全部符合预期；只改本文件，不改代码、文档、CHANGELOG、测试；Go 与 Julia 共 4 条由 r3e 真跑 | 验证证据节 r3d 小节；模型记录表 r3c4 行；r3d 会话 id 01a1d2a1-dfa4-723d-97a8-8a8c6f03b454，起始北京时间 2026-11-13 09:59:46；r3d 次数由 r3e 写入 |
| 2026-11-13T10:55:35.249494+08:00 | in-progress | in-progress | r3e 真跑轮：F 项后半 Go/Julia 同意/拒绝共 4 条路径真跑完成，Julia 同意路径另在真实全局 lsp.yml 演示自定义条目写入并已逐字节还原（三次 sha256 与 cmp 证据在验证证据节）；CodeX 的 Codex 钩子真跑结果写入；补 r3d 会话实数与 r3/r3b/r3c/r3c2 模型记录；只改本文件，不改代码、文档、CHANGELOG、测试 | 验证证据节 r3e 与 CodeX 小节；模型记录表 r3d 行；r3e 会话 id 01a1d2b9-d191-7199-89b0-f462818147bc，起始北京时间 2026-11-13 10:25:55；r3e 次数在推送前由下一次记录提交写入 |
| 2026-11-13T11:34:50.760571+08:00 | in-progress | in-progress | r3f 记录轮：只改本文件——补 r3e 真实次数与起止时间，准备推送开 PR；不改代码、文档、CHANGELOG、测试，不跑真跑 | r3f 会话 id 01a1d2e4-53af-70ec-8e9a-d4ccb86d7d35，起始北京时间 2026-11-13 11:12:21；r3f 次数由推送后的 PR 正文记录 |
