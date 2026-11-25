---
schema_version: 1
id: v2.2.0-rc.2-graft-retirement
workflow_mode: strict
mode_source: user
mode_note: 用户授权 main CI 全绿后按已确认 PRD 推进任务 5；§4 要求 strict。
status: "checking"
branch: feat/v2.2.0-rc.2-graft-retirement
created_at: '2026-11-25T10:04:13.021586+08:00'
updated_at: "2026-11-25T12:29:15.652748+08:00"
completed_at: null
"blocked_reason": null
---
# 任务 5：替代检索验收后退役 Graft

基线：PR #226 squash `d6e0bc3c0e366a65d1abd5e25ebc78969e1e9329`，[main CI](https://github.com/KunoLu/640-skills/actions/runs/45527867674) 13/13；任务 4 宿主与配置证据在其本地 ignored reports，未迁移或删除。

## 范围与顺序

按 2026-11-23 PRD §7 任务 5：先列出 Codex／OMP 每个候选的精确位置、SBTD 写入凭证及恢复手段；无凭证不得退役。同名、内容相似、路径存在均不能单独证明写入者。保留用户与第三方条目、未知项及 hook 文件。真实宿主写入须在展示新鲜清单后单独确认。不改主线、不同步、不执行任务 6 或发布。

正向验收：仅清除获准且现场与历史证据吻合的条目，运行两次不产生额外改动，恢复后逐项比对。负向验收：替代能力未通过、来源不明、漂移、路径不安全或恢复材料不完整时拒绝相应写入。提供双语 breaking、旧项目升级与恢复说明。

## 工程与验证门禁

当前阶段为只读盘点，未批准真实宿主清除。strict：生产编辑前完成 Legacy Change Safety、Refactoring；持久配置的迁移证据和可回退设计须经 DDIA、migration。验证用任务 5 私有 TEMP 合成配置，不沿用任务 4 凭据或环境；精确 SHA 内置 `/review`、外审、CI 分别记录。当前主会话 Astra，精确调用次数未知。未完整调用 grill-with-docs：输入、归属门和负例已由 PRD 明定；不把无法证明的归属作为需求假设。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-25T10:04:23.039998+08:00 | planned | in-progress | 当前 Astra 会话：在新 main 派生分支开始任务 5 归属及恢复清单预检。 | 本地及远端任务 4 分支已按冻结 SHA 移除，保留任务 4 私有报告与源 bundle；独立任务 5 TEMP 640-skills-rc2-task5.MLZgBxWU。未写真实宿主或执行退役。 |
| 2026-11-25T10:06:53.031814+08:00 | in-progress | blocked | 当前 Astra 会话：首轮清单已列出两个当前域 MCP 候选，尚无绑定实际写入及可恢复原件的证据，按 PRD §7 停止真实退役。 | Codex mcp_servers.sbtd-graft 与 OMP mcpServers.sbtd-graft 均存在；四类 Codex hook 中目标启动器命中 0。OMP 原件目录不是成功部署回执，Codex 已知备份路径经过别名，未跟随。可删除集合为空，宿主写入 0。见 reports/inventory.json、inventory.md。需受控的既有部署回执位置或明确改为隔离夹具演练；禁止按名称删除。 |
| 2026-11-25T11:00:59.695643+08:00 | blocked | in-progress | 当前 Astra 会话：真实双端条目继续保留。用户另行授权只在新隔离夹具验证退役、重复执行和恢复。 | 不解析或改写任何现场宿主配置，不沿用认证，不运行全局安装或卸载。 |
| 2026-11-25T11:03:54.264955+08:00 | in-progress | blocked | 当前 Astra 会话：本轮隔离退役演练已完成；依用户决定保留两个真实宿主条目，真实退役仍无来源及恢复凭证。 | 生产部署写入三个合成配置并生成原件与回执。夹具控制器调用生产文件原语：移除两条 MCP、四条受管 hook；保留第三方和用户 handler，同名无证记录未动；第二次零写，三文件逐字节恢复至退役前、模式 0600。五个前置／漂移负例均拒绝。无真实宿主读写；非生产卸载 CLI，不宣称完成真实退役。见 reports/fixture-retirement/result.json、result.md、fixture-evidence.zip。 |
| 2026-11-25T11:08:53.751043+08:00 | blocked | in-progress | 当前 Astra 会话：继续仓库内双语旧项目升级与恢复指引；真实宿主保留决定不变。 | PRD 任务 5 要求双语 breaking 和恢复说明；核对既有接线、夹具与失败边界，不启动宿主或执行清理。 |
| 2026-11-25T11:10:43.977196+08:00 | in-progress | blocked | 当前 Astra 会话：双语 breaking、旧项目升级和恢复说明已补齐。按用户决定保留两个真实条目；真实退役仍缺逐项写入归属与原件证据。 | README.md 和 README.zh.md 的 graft-retirement 四步说明区分结构检索与图能力、安装前原件与退役前备份、旧绑定切换与当前全局连接退役。两份 CHANGELOG 记录文档变化，不宣称交付卸载 CLI。局部 Markdown 解析、链接、标识对照、既有夹具回执核对通过，见 reports/retirement-guide.json 和同 stem 中文汇总。只改仓库，无现场读写、无新运行时验收。监控 prompt 与版本基线无变化。 |
| 2026-11-25T11:12:33.915138+08:00 | blocked | in-progress | 当前 Astra 会话：用户要求仅在全新隔离 HOME 验证两种平台新安装是否仍会生成 Graft 接线。 | 正式路径按现有版本实测，不改产品或读取真实宿主配置；不把缺少运行时导致的跳过记作通过。 |
| 2026-11-25T11:17:34.072623+08:00 | in-progress | blocked | 当前 Astra 会话：新安装默认不再生成 Graft 接线未通过。两个现场条目仍保留；本轮只验证，未更改生产安装逻辑。 | 四个独立空 HOME，未传 --no-mcp。生产 init 两端均 exit 0、包已安装，0.30.1 与 pin 0.29.0 不符，not-available 而无接线。仅替换 verified_runtime 返回值的可用分支对照中，两端均 success，在对应 MCP 配置实际生成 sbtd-graft。不是原生 0.29.0 全链；未运行真实宿主。详见 reports/fresh-init/results.json、results.md 与私有证据包。 |
| 2026-11-25T11:19:58.863655+08:00 | blocked | in-progress | 当前 Astra 会话：用户授权修改普通 init 的默认全局 Graft 接线，不访问两个现场条目；在全新隔离 HOME 复验。 | Legacy Safety characterized：上一轮可用运行时条件对照两端都创建了条目。Refactoring proceed：在共用规划器界定默认和显式分支，不改接口。DDIA confirmed / migration：不写入或回填既有宿主配置，无 schema 变化。保留有根项目准备、reset 及显式 hooks、legacy 和 sealed migration。 |
| 2026-11-25T11:32:59.263646+08:00 | in-progress | checking | 当前 Astra 会话：普通 init 默认不接线已修正，两端隔离复验通过，进入本地检查点；真实未知项仍保留。 | 默认 init/check/plan 不产生全局 Graft MCP 操作，带根项目保留本地图与围栏；reset、显式 hooks/legacy、迁移上下文分别处理。六个隔离 HOME 安装成功，空配置不创建，预置 MCP 与 hook 原字节、inode/模式/mtime 不变；可用条件对照不触发接线运行时探测。六模块 65/65、双语契约及定向 Ruff 通过；首轮 Bash 临时文件沙箱失败单列保留。见 reports/init-default-fix/smoke.json、regression-final.log、docs.json、同 stem 中文汇总和 fresh-home-proof.zip。Release Readiness：本地通过，精确提交内审、独审、远端 CI 与发布仍未完成；真实现场未读写，未改变旧回执指纹门。 |
| 2026-11-25T12:17:36.246057+08:00 | checking | in-progress | 当前 Astra 会话：a9d18a3 原生内审 CHANGES_REQUESTED；用户指定本轮修复 P1 reset 确认前预览漏报宿主目标。 | Bash/PowerShell 在批准前传 plan 而后执行 reset。Legacy characterized；Refactoring proceed：传入选定动作并复用规划；DDIA confirmed：只读预览，不改持久数据格式或实际授权。普通 init 及真实双端条目保持不动；P2 文档项单列，不作为本次已修复。 |
| 2026-11-25T12:25:43.060930+08:00 | in-progress | checking | 当前 Astra 会话：完成指定 P1 reset 最终预览修正，冻结本地检查点；普通 init 行为不变。 | Bash 和 PowerShell 最终计划按选定动作调用只读 plan --action init&#124;reset；未指定默认 init。文本列出实际宿主目标，JSON 保持 mode=plan。两平台隔离预览零写，确认后 reset 实际资源 ID 与路径一致；Bash/Codex 和 PowerShell/OMP 拒绝确认后目标均不存在。可用 runtime 为显式测试条件，不冒称原生 0.29.0。六模块 72/72，目标 Ruff/Bash 检查通过，首次 Bash 驱动加载失败单列。见 reports/reset-preview/smoke.json、regression.log 和同 stem 中文汇总。双语 README/CHANGELOG 和版本检查影响参考同步；监控 prompt 主体与 live 配置未改。不认领此前两项 P2 文档修复；新 SHA 复审、独审、CI 和现场清理均未完成。 |
| 2026-11-25T12:27:30.806984+08:00 | checking | in-progress | 当前 Astra 会话：继续处理原生内审剩余两项 P2 文档问题，保留 P1 修正和两个现场条目。 | 区分普通接线、密封迁移和显式升级的备份定位；补充获准升级可写 Codex/OMP MCP 的条件。只修文档，不执行真实 upgrade 或宿主清理。 |
| 2026-11-25T12:29:15.652748+08:00 | in-progress | checking | 当前 Astra 会话：已修两项升级文档 P2，冻结当前分支，交 OMP 内置整分支复审。 | 三种备份来源分别核实；SKILL 和双语 README 明确选定宿主且已确认的升级 apply 可写受管 MCP。隔离 4/4 通过，双语标识与参考锚点检查通过。见 reports/upgrade-docs/verification.log 和同 stem 中文汇总。本轮不改产品行为；不把本地修正判为独审或远端 CI，不访问真实宿主配置。 |
