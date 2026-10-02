# SBTD v2：全局会话 Graft MCP 整改 PRD

## 1. 状态、来源与主 PRD 关系

- 用户在本次会话明确确认 OMP session `01a0fb46-a6aa-7305-9db5-6942c2a05be9` 最后一轮修正方案，并要求新建分支、按 strict 实施。
- 实施分支：`feat/graft-global-session-mcp`；起始 HEAD：`39cf00bb7299d9f7b92153a5bd147382a40c478d`。
- 主线：[去 Trellis 化与 Graft 替换主 PRD](sbtd-workflow-v2-trellis-removal-graft-migration-prd.md)。本文承接全局安装／会话项目解析整改；主 PRD 保留原始审核、已执行批次与发布台账，不重写历史成功的含义。
- 文档选择：新增关联 PRD。整改横跨安装、全局配置、项目初始化、受管 launcher 和旧接线迁移，具有独立验收生命周期；不把完整实现设计继续堆入主 PRD。原主 PRD P3-05 承接实际环境退役，P3-04 继续拥有备份销毁边界。
- 当前状态：源码与本地验证已完成，已创建 [PR #108](https://github.com/KunoLu/640-skills/pull/108)；精确提交的三平台结果以该 PR Checks 为准，不以旧 head 结果证明新 head。本轮不自动合并，真实 PC 切换及发布另行记账。
- 前序可行性证明仅覆盖真实 OMP CLI/RPC、Codex CLI/app-server 与 Orca 终端到诊断 MCP 的 cwd 传递；不是新 Graft 查询实现证明。未验证的 GUI 专用启动器／managed-daemon／SDK 不扩大宣称。
- 现有五份未提交文档修改属于前序调查成果，保留，不 reset、不丢弃。

## 2. 目标与授权

每个所选 host 的有效配置域只有一条通用受管 `sbtd-graft` stdio 定义；无固定 cwd、无固定项目 `--root`。进程实际 cwd 决定一条连接的唯一项目。全局安装可不选项目；项目初始化只准备本项目规则、图与 stamp。一次批量初始化和随后逐次追加使用同一项目操作，不引入 daemon、跨项目路由服务或全局项目注册表。

本轮授权仓库代码、测试、文档和隔离验证，不自动授权真实 HOME 接线替换、全局安装、sync、发布、终止用户连接或备份销毁。真实 PC 切换须先展示精确前态／目标清单。已确认的条件清理只有在替代生效、host 验收、旧连接停止且无运行／恢复用途时才成立；不得以方案确认代替这些事实。

## 3. 领域及不变量

- 全局运行时：正式安装的 Onboard launcher、声明依赖 Python、固定 pin Node/Graft。不得把验证 TEMP 路径作为正式安装默认目标。
- 配置域：OMP active profile、普通 Codex HOME 或宿主实际使用的 Codex HOME；一份逻辑定义不等于整个 PC 只有一份物理配置文件。
- 项目：当前工作目录所属的明确 Git repository/worktree；取最近边界，不能跳过未初始化嵌套仓去借外层图。
- 连接：启动时确定项目，整个生命周期不换根；shell cd 或协议 roots 变化不把旧连接切向别的项目。
- 无项目、HOME、中立共同父目录、缺图、旧 stamp、越界／symlink/reparse、工作区聚合图均 fail closed，不自动初始化、联网修复或回退 demo。
- 保持 pin、DNT、Python 启动隔离、私有 HOME、dotenv／LLM／cloud 隔离及每请求图路径复验。
- hooks 保持独立 opt-in；hook/analyze 的显式 root 不是全局 MCP 的项目绑定。
- 用户文件拥有所有权；仅凭 `sbtd-graft-*` 名字不足以删除。原迁移计划、回执、备份不可变，新切换保存新前态，不伪造旧证据。

## 4. 行为规格与验收

本仓禁止持久 `.feature`，使用本文中文场景及 English Given/When/Then；现有 unittest 承接自动化，不新增 BDD 框架。

| ID | Scenario / Given / When / Then | 验证边界 |
|---|---|---|
| GM-01 | Given 未选择项目且运行时就绪；When 安装所选 host 全局配置；Then 生成一条不含 cwd/root 的通用定义，不能声称任何图已可查询 | 全局 plan/init 与配置读回 |
| GM-02 | Given A 已初始化且全局定义存在；When 仅追加 B；Then A 的配置／图和全局定义不变，B 可独立查询 | 单项／批量等价及文件快照 |
| GM-03 | Given A/B 有不同真实代码图；When 同一全局定义启动并发连接；Then A 只命中 A，B 只命中 B，连接不共享根 | 真实 Graft + OMP/Codex/Orca 已用入口 |
| GM-04 | Given 已初始化仓库的子目录或 linked worktree；When MCP 启动；Then 锁定最近真实仓／worktree 根，不借主 checkout 图 | 原生 CLI 与根解析测试 |
| GM-05 | Given HOME／无仓／共同父目录／未初始化嵌套仓／缺图／旧 stamp／越界数据；When MCP 启动或请求；Then 非零或协议拒绝，原文件不变、不启动错误项目 | 安全拒绝与无副作用断言 |
| GM-06 | Given 已有无关 MCP 和用户配置；When 重复同一全局安装；Then 无关字节／语义保留，通用定义幂等；不同运行时或同名未知配置拒绝隐式覆盖 | TOML/JSON 候选及安装回归 |
| GM-07 | Given 精确旧受管固定根条目及独立迁移授权；When 切换至通用定义；Then 仅删除已验证归属和授权范围的旧项，保全前态；漂移、中断、重试、恢复均可核验 | 新切换计划／备份与回归；旧证据解析保留 |
| GM-08 | Given 无独立迁移授权或继承源含未知／冲突旧项；When 普通安装；Then 明确冲突，不删除或隐藏旧项、不清空 HOME | 所有权拒绝 |
| GM-09 | Given init-projects 模式；When 初始化一个或多个项目；Then 不写 HOME，复用全局连接且不隐式升级运行时 | 项目初始化集成 |
| GM-10 | Given 原受管安全策略；When 全局入口运行；Then pin/DNT/环境隔离／每请求复验仍生效，root 参数不能覆写 MCP cwd 选择 | 既有守卫回归 |

必过：全量项目测试、相应三平台 CI、独立代码与安全复核。未执行的远程 CI、未授权 live 切换不得标通过。所有正式本地证据保留原生/raw 与同 stem 中文汇总，dirty 证据仅 local-only。

## 5. 设计与最小实施边界

1. 在既有 `sbtd_graft_entry.py` 中按最近安全 `.git` 边界解析项目，再由 `_trusted_git` 选择项目外绝对 PATH 中的真实 Git，对实际启动 cwd 执行 `git rev-parse --show-toplevel --is-inside-git-dir`。探针移除继承的 `GIT_*`、禁用 system/global Git 配置；HOME 是停止边界，bare／Git 管理目录及顶层不匹配 fail closed，不借外层图。MCP CLI 不接受固定 root，hook/analyze 保持显式根约束；校验前不创建临时 HOME、不调用 native Graft。
2. Codex/OMP 既有候选渲染器改为单一 `sbtd-graft`；运行时身份与项目列表分离，无项目时仍能渲染。多个项目不能携带不同全局运行时。
3. `sbtd_graft_deployment.py` 复用现有资源操作、snapshot、前态备份与失败状态；全局阶段无项目可运行，init-projects 不写 HOME。逐项本地图生成不修改其他项目。
4. 旧固定根配置只作为显式迁移输入和历史回执验证格式保留，不再生成，不保留旧 MCP CLI alias。非授权旧项 fail closed；切换只改所有权已证明的精确条目，保留用户配置、历史备份和恢复路径。
5. 原生产任务表仍由主 PRD 拥有；本地 strict 任务记录仅恢复本次执行。PRD 记录需求、设计和验收，不充当第二模式状态源。

### 5.1 旧运行时切换的明确输入

普通安装遇到旧固定根条目时拒绝隐式替换。`--graft-retire-legacy`（Bash 同名，PowerShell `-GraftRetireLegacy`）仅授权已选根、完整旧 argv/env/cwd/hash 形状与运行时身份匹配的条目退役，不授权目录删除。

从旧 TEMP／旧 pin 切换到不同稳定运行时时，另传 `--graft-legacy-bindings <private-json>`（PowerShell `-GraftLegacyBindings`），由维护者从实际旧配置和保留证据核对后提供：

```json
{
  "schema_version": 1,
  "bindings": [
    {
      "root": "/absolute/selected-project",
      "python": "/absolute/old-runtime/python",
      "node": "/absolute/old-runtime/node",
      "cli": "/absolute/old-runtime/dist/cli.js",
      "launcher": "/absolute/old-onboard/scripts/sbtd_graft_entry.py"
    }
  ]
}
```

输入必须位于受保护私有目录且在部署写目标之外；闭集字段、重复 root、非绝对路径、非所选根均拒绝。计划保存输入快照，执行前漂移／缺失阻断零写入；逐资源仍核对配置前态并保留原件。该文件是本次操作者明确指定的旧运行时契约，不是从名字推测授权，也不修改历史 manifest。旧继承源不由另一 host 的安装器擅改，需在其真实归属配置域另行处理。

无 `--graft-retire-legacy` 的输入文件、project-only 全局退役、把本次退役选项混入已密封历史迁移部署均拒绝。源码没有自动销毁旧运行时或备份的入口。

## 6. Book Gate Plan 与 before-dev

| Gate | 客观触发 | 阶段 | 状态／证据 |
|---|---|---|---|
| DDD | 前序讨论已明确配置域／项目／连接边界；没有完整 grill，本轮无未决领域歧义 | 需求 | not-needed；术语见 §3 |
| DDIA | 全局持久配置、项目图、切换和恢复所有权 | 设计前 | confirmed：单文件候选、预期前态检查、原子资源提交及既有备份；跨资源失败如实部分完成，禁止覆盖漂移 |
| Legacy | 原固定项目连接语义与迁移历史有回归风险 | 代码前 | characterized：修改前原生候选复现追加 B 产生两个 cwd 绑定；空批次不渲染。既有配置／launcher／迁移 tests 为安全网 |
| Refactoring | strict 修改既有生产代码 | 代码前 | proceed：沿用 launcher、候选渲染与资源执行 seam，无前置结构重构 |
| Release | 安装／宿主启动／迁移行为变化 | 测试后 | pending，不能用方案或单测代替 |

未完整调用 grill-with-docs：用户已确认具有实测依据的最终方案，无需重问已明确问题。LSP references 调用返回无可用 language server，因此本轮影响分析用实际源码、符号搜索和契约测试；未调用有未证明副作用的 Graft 查询。

TDD 公共 seam：用户确认的 MCP 进程启动、安装 CLI、TOML/JSON 配置候选、项目初始化和迁移资源输出。保留修改前失败原因，测试消费者可见隔离／边界／幂等／所有权行为，不新增源码文字断言。

## 7. 实施跟踪与验证证据

| 切片 | 交付 | 当前状态 |
|---|---|---|
| GM-A | cwd 根解析与会话固定、拒绝边界、launcher 回归 | 已实施；复核后加入实际 cwd 的 bare/admin 拒绝与可信 Git 探针 |
| GM-B | 单全局 Codex/OMP 候选、旧项所有权及回执验证 | 已实施；复核后收紧旧项闭集形状，项目继承不再代替全局覆盖 |
| GM-C | 全局安装／本地初始化分离、无项目支持及切换契约 | 已实施；完整安装写集避让批准文件、首写／逐资源复验，尊重 --no-mcp |
| GM-D | 真 Graft A/B、宿主验证、全套测试与独立复核 | 复核后聚焦 92 项、全量 1425 项（8 skipped）通过；独立代码／安全复审 GO。真实批量／逐次图等价、A/B 并发与 Codex／OMP／Orca 查询通过；精确 head 三平台 CI 见 PR #108 Checks，首个 Windows 失败及修正见下文 |
| GM-E | README 两种入口、automation、CHANGELOG、主 PRD 同步 | 已同步行为／迁移边界、长期 lesson、PR 入口及本地验证证据；合并和 live 状态保持独立 |

修改前原生复现：两个项目候选追加后 server_count=2，均固定 cwd；期望一条通用定义的断言 exit 1。首次会话 Python 缺 tomlkit 属于环境失败，保留但不作为产品 red；随后复用既有依赖完整的验证解释器得到上述真实 red。

恢复边界：本轮保留起始 dirty patch，不改真实生效 MCP 或删除历史环境。用户随后明确授权本地检查和复核收口后提交、推送本分支并创建 PR，取得精确提交的三平台 CI；不授权合并、发布或 live 切换。另明确授权只用本轮 Orca 专用终端和隔离 HOME 查询合成图，完成后关闭终端并移除本轮临时注册，不删除项目文件。源码回退不能替代 HOME／ignored 数据恢复；live 退役继续遵守主 PRD P3-05/P3-04。

### 7.1 本地验证记录

- `full-suite-02`：原生 `python -B -m unittest discover -s tests -p 'test_*.py'`，1425 tests，8 skipped，exit 0；首轮 1414 tests／8 skipped 记录仍保留，不冒充复核后结果。
- `review-fixes-focused-02`：批准完整写集／首写及构图期间漂移、MCP opt-out、OMP 生效域与闭集退役、launcher、候选渲染和隔离 92 项通过。此前 fixture 语法失败记录保留；修复的是测试括号，不是压低安全断言。
- `post-review-native/native-smoke`：真实 Graft 0.21.1；逐次 A/B/C 与批量同源项目的图 bytes、AGENTS bytes 和除实际生成时间外的 stamp 相等；新增 B 不改 A／全局定义；A/B 并发和子目录查询正确。同一 Codex app-server 两线程查询各自图。
- `omp-smoke-post-review-02`：两个原生 OMP 会话共享同一隔离全局配置，分别得到 `alpha_only`／`beta_only`；回环确定性模型只调度真实工具调用，不模拟 Graft，不声称真实模型推理。增强输出采集后的复跑 exit 0，约 1.08s。前次 150s 超时发生在全量测试重叠期间，控制器 0 请求且初版驱动未保全 TimeoutExpired 的子进程输出；重叠负载是可能因素，尚未证明确切根因，不能写成产品缺陷已修复。
- `orca-host-entry-01`：经追加授权，用一个本轮专用 Orca 终端、隔离 HOME，runner 不改 cwd、不传 thread cwd；Codex 与 OMP 均从继承目录查询真实图成功。shell wait 的 `stop_unverified` 不作为成功退出证据；随后关闭返回 `ptyKilled=true`，本轮注册已 metadata-only 移除，合成项目文件仍存在。
- 代码复审：原 4 项问题均关闭；安全复审：原 5 项问题均关闭，重复问题合并修正。Ponytail 无可安全删除的生产抽象；保留现有候选、资源和隔离边界。Code Readability 已核对手写代码／测试；未改 vendor/generated。
- 静态验证：Bash 语法与 PowerShell 原生 parser 通过；新增／改造模块的 ruff 检查和 onboard 既有诊断分别记录；onboard 的 ty 基线及当前均为 92 项既有诊断，不把已有错误标为通过。
- 报告位置为本轮私有 `sbtd-global-session-mcp-*` 证据目录，保留 raw／同 stem 中文汇总与失败记录；提交前证据均为 developer-local / dirty / local-only。远程 CI 只能以随后创建的 PR 精确 head 为准。

### 7.2 精确提交 CI 与 Windows 测试辅助修正

[PR #108](https://github.com/KunoLu/640-skills/pull/108) 的首个 head `6373f9cf4a7a4e6c78edb4179455cf58ecd0cce3`，Windows job `110949024431`（run `37040462165`）在 `SessionRootResolutionTests` 报 7 个错误：全部来自测试 `read_reply` 对匿名管道调用 `select.select`，原生日志为 `WinError 10038`（not a socket）。安装器／工作流 50 项与 pwsh 15 项此前通过。这个失败不证明 Git 路径解析有误，不能据此放宽生产路径安全守卫。

测试 helper 改为带超时的后台 `readline`，保留全部协议与拒绝断言；本地完整 launcher 43 项及 ruff 通过。生产模块不因该测试平台问题改变。新 head 必须重新取得 Linux／macOS／Windows 结果，旧 head 的绿色或失败记录只作为历史证据保留；最终 Checks 与本地任务记录共同提供完成证据。本 PR 合并前，主 PRD P1-25 保持 checking，不冒充已进入 main。
