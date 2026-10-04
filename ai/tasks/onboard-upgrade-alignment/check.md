# 升级对齐验证与复核

## 当前证据边界

四阶段仓库能力实现、隔离运行和独立复核已完成；代码提交 `befa24eb7ef68c884a125af313528551b7d97af0` 的三平台 CI 全部通过（[run 37168994920](https://github.com/KunoLu/640-skills/actions/runs/37168994920)）。全部本地原始输出和同stem中文汇总保留在本目录 reports/；其中含本地运行路径，不随PR上传。提交前证据不冒充精确head；本机应用、同步、旧资产实际清理、新PR合并及发布均未执行。

## 已执行

- 原有参数/清理77项安全网通过；初次默认解释器缺tomlkit的失败保留，声明依赖解释器复跑。
- 升级CLI先red：缺upgrade入口。
- 完整受影响范围309项通过，1项原生Windows专用跳过；后续52项事务/CLI回归通过。
- 真实公开CLI在独立临时根完成33Skills、全局AGENTS、Codex/OMP与zsh profile安装；安装副本只读verify通过。
- 安装副本原生probe：Codex app-server及OMP RPC均加载33个受管Skills、6个固定Graft工具、版本0.21.1；zsh实际解析到选择的Graft路径。无模型请求，原GUI/既有会话未重载。
- 两根安装器真实plan均通过，非法phase均由实际Python拒绝；本机PowerShell不等于Windows证明。
- 真实完整包回归：旧安装对齐后删除测试bootstrap，使用已安装新CLI重试并恢复旧载荷通过；实际用户仓库或HOME未删除/覆盖。
- 新库存/host/CLI的ruff与ty通过。既有集成文件ruff基线27项、当前26项、新增0项，不夹带旧代码重构。
- 历史失败保留：4512758 原生Windows为23 failures/85 errors；2d8b474为canonical LICENSE换行不一致；141ba14为固定字节夹具、Git Bash省略.exe别名及完整生命周期180秒窗口不足。均已按真实失败修正；befa24e原生完整复跑通过，不以本地模拟替代。
- 首轮本地全量1643项含2 failures/5 errors/11 skipped；运行期间源码继续修正导致摘要及已加载模块不一致，该轮不得作为最终证明。失败原始报告保留；最终全量转到冻结提交的CI，避免边写边测。

## 独立复核修正

库存：排除缓存仍检查危险链接、跨平台稳定摘要顺序、bounded严格YAML身份、私密name不输出、来源schema/URL/自包校验、双向重叠。

宿主/CLI：已选OMP项目继承来源、安装目标launcher、继承连接验收、无跟随链接的Skills复制、真实shell解析、准确Skill启用/命令身份、隔离host不冒充live重载、空参数/partial退出码。

事务：逐资源恢复资格全字段绑定、当前scope派生、私有vault明确受信历史、未知部分改动保护、缓存稳定重试与恢复保守性、保留空父目录、同版安装位置迁移。库存、CLI/host、事务与Windows修正分别独立复核，最终无未解决的范围内问题。

## 方法与适用性

BDD: traceable，REFERENCE Upgrade Alignment的U01—U15中文场景，英文Given/When/Then；仓库禁止.feature，使用unittest。无跨业务服务/API，Cross-repo context与API Contract均not-needed。协议脚本化测试属contract-backed；原生宿主验收属isolated-host/selected-projection，不是live部署。Web/mobile测试工具not-needed；README.html仅文档内容更新，未改变交互。rtk: skipped-for-report，确保原生runner与raw证据。

Ponytail/Code Readability Review：保留真实库存、宿主差异和安全事务seam；无插件框架/daemon/密钥服务。使用既有catalog、文件事务、宿主候选和strict JSON能力，删除重复JSON解析器、无用变量与冗余断言，不因行数删掉恢复/授权保护。

## Final Full Rerun

| 原生平台／检查 | 代码提交 befa24e 的结果 |
|---|---|
| Linux 全量 unittest discover | 1650 tests，OK，19平台／条件skip |
| Linux 最低支持 TOML 编辑器 | 56 tests，OK |
| macOS 安装器及既有工作流 | 271 tests，OK，2 skip |
| macOS upgrade/recovery | 205 tests，OK，3原生Windows专用skip |
| Windows 安装器／工作流 | 49 tests，OK；PowerShell子集15 tests，OK |
| Windows upgrade/recovery | 205 tests，OK，5平台／条件skip；完整33Skills安装/已安装副本重试/恢复、DACL、Git Bash与PowerShell已执行 |

原始CI矩阵与每平台日志／同stem中文汇总：本地 `reports/ci-code-final*`。Evidence Source: ci；Source Revision: exact；Environment Alignment: verified（各自原生runner）；GitHub Checks已发布。Final Full Rerun: passed。没有把平台不适用skip视为该平台能力证明。

## Release Readiness Review

- Status: ready，仅表示本次仓库能力交付，不代表v2正式发布或用户环境部署。
- Production path: 显式升级与恢复、选定Skills/配置域、独立清理能力；init/reset/migration既有含义保持。
- Safeguards: 受管来源/身份/路径校验，完整原件，写入意图，累计实测回执，失败停止，恢复资格与当前漂移保护；无整机原子承诺。
- Capacity: 本地串行文件操作；无服务队列/跨服务backpressure。宿主探测有协议与进程期限；Windows完整生命周期测试保留900秒窗口，未通过删测试或跳过Windows规避失败。
- Observability/runbook: JSON分阶段结果、备份/回执路径、REFERENCE升级与恢复说明、磁盘/协议/隔离host/清理分层状态。
- Rollout/recovery: PR保持draft，未应用HOME。恢复保留原件和空父目录。历史vault由操作人独占管理且显式受信，hash不认证整组伪造历史；来源存疑必须停。
- Required validation: 上表精确提交CI、公开CLI真实安装/重试/恢复、macOS真实Codex/OMP隔离宿主、独立复核均完成。Windows实际Codex/OMP GUI部署不属于本轮授权，不能据协议夹具宣称已完成该部署。
- Residual boundary: 原GUI/既有连接未重载，未知定制需要决定，跨版本旧计划可能source-stale；非发布承诺。没有未获接受的可选检查豁免。
