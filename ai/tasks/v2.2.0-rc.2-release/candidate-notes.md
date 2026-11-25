## Release identity / 发布身份

- Annotated tag / 标注标签: `v2.2.0-rc.2`
- Commit / 提交: `d8b2191204e368035fd69544aa74c6600961a2f6`
- Exact-commit CI / 精确提交 CI: https://github.com/KunoLu/640-skills/actions/runs/45589961883 (13/13)
- Native scope verified / 原生范围核验: Task 7 tested isolated macOS hosts; Codex/OMP ingested 4/6 events and accepted none on replayed input. / 任务 7 的隔离 macOS 宿主实测：Codex／OMP 首次接受 4／6 条事件，重复导入均零新增。

## English

### Changed

- Use the project-designated glossary, or `GLOSSARY.md` at the project root by default. Before applying terms extracted from a legacy `CONTEXT.md`, show the exact diff and obtain explicit approval. Do not automatically migrate or overwrite the legacy file.
- Stop ordinary `init` and default `check`/`plan` from creating, updating, or removing a global Graft MCP definition for Codex/OMP, with or without a verified runtime. Explicit project roots still maintain the local fence/graph; graph presence does not prove host registration. `reset`, `init-projects`, migration-context `init`, and explicit `--graft-hooks` / `--graft-retire-legacy` retain their existing contracts and validation. Existing global Graft MCP/hook configuration remains untouched by the ordinary path; no machine-wide retirement is claimed.
- Pin host acceptance to `codex@0.171.0` + `omp@19.1.0` and require both hosts instead of the historical one-host fallback. Both completed isolated Air tool-call, ingestion and duplicate-import smoke checks on 2026-11-23; retain earlier cloud smoke records in `smoke_history`. Version matching alone, old reports and parser fixtures are not passing evidence. This baseline does not certify the full approval/MCP/failure/interruption matrix or release readiness, upgrade existing installations, or change the original Astra session.
- Document the breaking impact of removing Graft from an existing project, how to verify ownership before removal, and how to restore its wiring without overwriting later edits. No host configuration changes automatically.

### Fixed

- Both root installers now preview the selected action before confirmation. `plan --action reset` shows the global Graft MCP targets that reset plans to write; plain `plan` still previews init and does not authorize writes.
- Preserve actual file-operation results in installation JSON even when Graft wiring is skipped. Before optional setup, both root installers check for action-aware previews without importing modules from the caller's working directory by default.
- Pin the four Linux validation jobs to `ubuntu-24.04`, where the fixed Python `3.12.10` build is available. This avoids setup failures after `ubuntu-latest` moved to Ubuntu 26.04; Python/Node versions, action SHAs, native platform coverage, test shards and report failure gates remain unchanged.
- Normalize the official `codex-cli` version banner at Codex ingestion so stored events and receipts use the same version as capability pins. Add CLI-to-store/replay/capability regressions, retain old/unknown/prerelease rejection, and preserve existing raw-version observations on re-import conflicts instead of silently migrating them.
- Ship the original MIT texts for Phosphor metadata and the work behind Impeccable's platform references. Standalone external installs and explicit upgrades now carry their applicable licenses and notices with the skill; source pins and rollback boundaries are unchanged.
- Preserve read-only source modes when staging notices. Explicit upstream installs now check the covered files and repository attribution against the reviewed baseline before replacing either affected Skill.
- Restore an existing read-only Skill directory from its verified private backup without deleting the live tree first. A failed cutover preserves the previous installation or reports the retained paths.
- Prevent directory cutovers from replacing an unexpected occupant; check retired paths and directory permissions on recovery retries. Undo a new read-only installation without changing its live permissions, and report staging or backup directories left by failed installer cleanup.
- Preserve the external install result when source workspace cleanup fails. Recovery preflight now returns a content-addressed reference to retained-object evidence in the private vault instead of exposing the object's path or dropping it at the subprocess boundary.
- Clean removable read-only content in installer-owned source workspaces without reporting a failed installation. Actual cleanup failures still retain their paths and transaction results.
- Publish and replace read-only external Skill directories on Linux without making live installations writable. An incomplete migration runtime again returns a structured `blocked` response instead of a startup traceback.
- Clean read-only subdirectories in private staging and verified retired Skill trees. Direct staging and commit calls reject linked paths before changing the target; CLI path resolution is unchanged. Native macOS CI now covers the external installer regression.
- Refuse OMP session imports before opening the event store when the host cannot determine the target lease or returns incomplete lease metadata.
- Distinguish an explicit user denial from an ordinary failed OMP tool result when the journal carries the matching approval decision. Existing stored events are not rewritten.

## 简体中文

### 变更

- 术语以项目指定的术语表为准，默认使用项目根目录的 `GLOSSARY.md`。应用从旧 `CONTEXT.md` 提取的术语前，须展示精确差异并取得明确批准。不得自动迁移或覆盖旧文件。
- 普通 `init` 和默认 `check`/`plan` 不再为 Codex／OMP 创建、更新或移除全局 Graft MCP 定义，与 runtime 是否已验证可用无关。显式项目根仍维护项目本地围栏／图；图存在不证明宿主已接线。`reset`、`init-projects`、migration-context `init` 及显式 `--graft-hooks` / `--graft-retire-legacy` 保持既有契约和校验。普通路径不改动既有全局 Graft MCP/hook 配置，也不宣称完成整机退役。
- 将宿主验收固定为 `codex@0.171.0` + `omp@19.1.0`，要求两个宿主均通过，不再采用历史单宿主兜底。两者于 2026-11-23 完成 Air 隔离工具调用、入库与重复导入基础冒烟；旧云端记录保留于 `smoke_history`。仅版本匹配、旧报告和 parser fixture 均不是通过证据。本基线不证明完整审批／MCP／失败／中断矩阵或发布就绪，不升级既有安装，也不改变原 Astra 会话。
- 补充旧项目移除 Graft 的不兼容影响、移除前的归属核验及不覆盖后续编辑的接线恢复步骤。不自动更改宿主配置。

### 修复

- 两个根安装器现按所选动作生成确认前计划。`plan --action reset` 显示 reset 计划写入的全局 Graft MCP 目标；普通 `plan` 仍预览 init，不授权写入。
- 即使跳过 Graft 接线，安装 JSON 仍保留实际文件操作结果。两端根安装器在可选安装前检查所选来源是否支持按动作预览，预检不再隐式从调用者工作目录导入模块。
- 将四个 Linux 验证作业固定到提供 Python `3.12.10` 制品的 `ubuntu-24.04`，避免 `ubuntu-latest` 转向 Ubuntu 26.04 后的环境准备失败；Python／Node 版本、action SHA、原生平台覆盖、测试分片及报告失败门禁均保持不变。
- 在 Codex 导入边界规范化官方 `codex-cli` 版本标识，让存储事件、回执与能力 pin 使用同一版本表示；新增 CLI→入库／重放→能力判断回归，保留旧版／未知版／预发布版拒绝，并在重导入冲突时保全既有 raw-version 观察，不静默迁移。
- 随包交付 Phosphor 元数据及 Impeccable 平台参考文档原作的 MIT 全文。独立安装外部技能和显式升级均随技能交付适用的许可证和通知；来源 pin 与回退边界不变。
- 组装通知时保留只读来源模式；显式上游安装在替换受影响的两个技能前，按已审基线校验适用文件和仓库归属声明。
- 恢复已存在的只读技能目录时，先校验私有备份，再受保护地换入原件，不先删除正式目录。换入失败时保全原安装，或报告需处理的保全路径。
- 目录换入不覆盖意外占位，恢复重试核对退役路径及目录权限。撤销本批首次安装的只读目录时不放宽正式目标权限；安装器清理失败会报告遗留的暂存目录或备份目录。
- 来源工作目录清理失败时保留外部技能安装的实际结果；恢复预检返回私有 vault 中保全对象证据的内容摘要引用，不暴露对象路径，也不再因跨进程而丢失引用。
- 安装器自建来源工作目录中的只读内容可清理时，不再误报安装失败；确实无法清理时仍保留遗留路径及实际事务结果。
- Linux 可发布和替换只读外部技能目录，不向正式安装添加写权限。迁移运行模块不完整时重新返回结构化 `blocked` 回执，而非启动异常堆栈。
- 清理私有暂存与已核验退役技能目录中的只读子目录。直接调用暂存和提交接口时，在改动目标前拒绝含链接的路径；CLI 路径解析不变。macOS 原生 CI 增加外部安装器回归覆盖。
- OMP 无法判断目标会话租约或返回不完整的租约信息时，导入器在打开事件库前拒绝读取。
- OMP 会话含匹配的明确拒绝决议时，将用户拒绝与普通工具失败分开记录，不改写已有事件。

## Deployment boundary / 部署边界

Removing Graft is a breaking change for projects still using its graph or hooks. This release does not retire existing entries, register new hosts, or upgrade an installation. Test the replacement first, verify ownership and back up the wired state; restore only when the target matches the recorded post-change state. [Upgrade and restore](https://github.com/KunoLu/640-skills/blob/d8b2191204e368035fd69544aa74c6600961a2f6/README.md#graft-retirement).

移除 Graft 会破坏依赖其图或钩子的旧项目。本版不自动退役已有条目、注册宿主或升级现有安装。先实测替代检索，核验归属并备份接线状态；仅在目标匹配记录的变更后状态时恢复。[升级与恢复](https://github.com/KunoLu/640-skills/blob/d8b2191204e368035fd69544aa74c6600961a2f6/README.zh.md#graft-retirement)。

Full comparison / 完整对比: https://github.com/KunoLu/640-skills/compare/v2.2.0-rc.1...v2.2.0-rc.2
