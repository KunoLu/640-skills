# 升级对齐验证与复核

## 当前证据边界

实现验证中，未标记完成。全部本地原始输出和同stem中文汇总保留在本目录 reports/；其中含本地运行路径，不随PR上传。提交前均为 developer-local / dirty / local-only，不证明PR head。最终三平台GitHub CI须绑定实际提交。

## 已执行

- 原有参数/清理77项安全网通过；初次默认解释器缺tomlkit的失败保留，声明依赖解释器复跑。
- 升级CLI先red：缺upgrade入口。
- 完整受影响范围309项通过，1项原生Windows专用跳过；后续52项事务/CLI回归通过。
- 真实公开CLI在独立临时根完成33Skills、全局AGENTS、Codex/OMP与zsh profile安装；安装副本只读verify通过。
- 安装副本原生probe：Codex app-server及OMP RPC均加载33个受管Skills、6个固定Graft工具、版本0.21.1；zsh实际解析到选择的Graft路径。无模型请求，原GUI/既有会话未重载。
- 两根安装器真实plan均通过，非法phase均由实际Python拒绝；本机PowerShell不等于Windows证明。
- 真实完整包回归：旧安装对齐后删除测试bootstrap，使用已安装新CLI重试并恢复旧载荷通过；实际用户仓库或HOME未删除/覆盖。
- 新库存/host/CLI的ruff与ty通过。既有集成文件ruff基线27项、当前26项、新增0项，不夹带旧代码重构。
- 草稿 PR #110，首个提交4512758：原生 Windows CI 199项中23 failures/85 errors/5 skipped。已保留完整原生日志；正在修正跨平台摘要、私有目录DACL初始化及shell/路径夹具问题，不以macOS通过替代Windows。
- 首轮本地全量1643项含2 failures/5 errors/11 skipped；运行期间源码继续修正导致摘要及已加载模块不一致，该轮不得作为最终证明。失败原始报告保留；最终全量转到冻结提交的CI，避免边写边测。

## 独立复核修正

库存：排除缓存仍检查危险链接、跨平台稳定摘要顺序、bounded严格YAML身份、私密name不输出、来源schema/URL/自包校验、双向重叠。

宿主/CLI：已选OMP项目继承来源、安装目标launcher、继承连接验收、无跟随链接的Skills复制、真实shell解析、准确Skill启用/命令身份、隔离host不冒充live重载、空参数/partial退出码。

事务：逐资源恢复资格全字段绑定、当前scope派生、私有vault明确受信历史、未知部分改动保护、缓存稳定重试与恢复保守性、保留空父目录、同版安装位置迁移。最终复核及全量回归进行中。

## 方法与适用性

BDD: traceable，REFERENCE Upgrade Alignment的U01—U15中文场景，英文Given/When/Then；仓库禁止.feature，使用unittest。无跨业务服务/API，Cross-repo context与API Contract均not-needed。协议脚本化测试属contract-backed；原生宿主验收属isolated-host/selected-projection，不是live部署。Web/mobile测试工具not-needed；README.html仅文档内容更新，未改变交互。rtk: skipped-for-report，确保原生runner与raw证据。

Ponytail/Code Readability Review：保留真实库存、宿主差异和安全事务seam；无插件框架/daemon/密钥服务。使用既有catalog、文件事务、宿主候选和strict JSON能力。已去掉无用变量与冗余断言，不因行数删掉恢复/授权保护。Release Readiness尚未通过，待最终复核与精确head三平台CI。
