---
schema_version: 1
id: P3-03
workflow_mode: strict
mode_source: user
mode_note: 用户接受建议，明确选择strict用于v2.0.0最终发布审查
status: "in-progress"
branch: "release/v2.0.0"
created_at: '2026-10-14T00:02:56.566903+08:00'
updated_at: "2026-10-14T07:39:18.007306+08:00"
completed_at: null
---
# P3-03 最终 readiness、用户确认与 v2.0.0 发布

## 身份、模式与授权

用户要求开始P3-03，并明确选择strict。项目640-skills，从main创建release/v2.0.0候选分支并经用户明确授权重绑定；P3-01/P3-02/P3-05已完成。当前授权包含发布审查、候选准备/验证及已展示九文件的commit/push/PR；不包含合并、创建或推送tag、GitHub Release、管理员绕过、本机sync/升级或备份销毁。最终发布范围须在精确候选CI通过后另行确认。
当前工作树已存在主PRD和关联MCP PRD的前序收口修改，保留不重置。目标为v2.0.0；P3-04仍planned，已接受的原位保留责任不变。
未完整调用grill-with-docs：发布目标、依赖、AC和安全合同已在PRD明确，无新领域建模或产品范围设计。

## 验收与验证计划

- 将主PRD AC-01至AC-37、P0/P1/P2/P3证明与当前候选逐项对照，区分历史、复用、新复跑及未通过。
- 核对真实tag/commit/CI与工作树，准备真实未发布说明；不以旧SHA或dirty测试冒充最终tag验证。
- 使用项目原生runner及已有依赖完成适用本机验证、隔离CLI/安装包smoke；三平台CI须精确绑定实际最终候选SHA。
- 独立复核发布范围/证据和安装载荷/文档一致性，合法发现修正后重验；无产品修改不强行新增测试或重构。
- 输出独立Release Readiness Review；required缺失不得改作风险接受。只有ready和用户精确发布确认后才执行发布，核对实际tag/远端/发布状态后登记done。

## Book Gate Plan

| Gate | 客观触发 | 阶段 | 状态 |
|---|---|---|---|
| DDD | 未完整grill、无新领域歧义 | before-dev | not-needed |
| DDIA | 本轮仅审查既有迁移/恢复证据，不设计或修改数据协议 | before-dev | not-needed；若新增迁移/恢复改动立即重评 |
| Legacy safety | 尚无既有行为修复 | before-dev | not-needed；发现需改产品时先刻画 |
| Refactoring | 尚无生产代码编辑 | before-dev | not-needed；不夹带重构 |
| TDD/BDD | 无新增行为，沿用主PRD及既有测试；源仓禁止.feature | check | traceable：AC-01～37映射及既有行为场景；无新增代码不做TDD |
| Project validation | 最终发布候选验证 | check | 本机macOS完整687项通过/20原生skip、完整副本CLI通过；最终clean SHA三平台CI待建立 |
| Code readability / Ponytail | 仅状态/发布文档时无生产diff | check | not-needed；若改手写代码重新触发 |
| Independent review | 迁移、安装、权限与宿主配置产品正式发布 | check | 两路独立只读review无新增范围内缺陷；精确最终SHA及发布授权仍待完成 |
| Release readiness | 正式运行时/安装载荷发布 | finish | blocked：本机验证已通过，最终候选CI与发布授权未完成；不以风险接受替代required gates |

## 发布边界

恢复只承诺已验收的受管数据/配置，不承诺旧Trellis可写回退。备份保管与2026-10-27或P3-03前人工复核节点沿用P3-05接受记录。计量不宣称跨模式节省比例；受控host样本不冒充五个独立自然业务任务。其他账户、生产业务部署、secret轮换、全机升级和备份销毁不在发布权限内。

## 候选准备与本机审查（2026-10-14）

- 基础main为`c91a66f1aef83d10db37440768a62811719611fc`。GitHub实际validation run38239933475九个job均success，原生artifacts下载后SHA/成功状态/必需原生用例核验一致；只证明基础提交，不冒充本轮dirty候选。远端已有rc.1～rc.4，尚无v2.0.0；rc.4已有GitHub prerelease。
- 修正双语README过期RC横幅，改为发布tag/CHANGELOG事实源；稳定版未发布章节移至CHANGELOG顶部并说明累计RC范围与证据限制；Onboard SKILL/REFERENCE改为区分能力、版本证据及独立部署授权，不提前声称发布。automation prompt无需改，监控/同步契约未变；未修改生产代码、templates或签名资产。
- 发布内容由ReleaseEvidenceReview和ReleasePackageReview独立只读复核，无新增范围内内容/实现缺陷。Onboard Markdown不进入迁移runtime指纹，但完整upgrade包baseline会变化；旧plan必须按真实包校验，不能用文档变更绕过source-stale。两种指纹的含义不混淆。
- 原生`python -B tests/run_ci.py --platform macos`首轮687项有1失败/20skip：测试期望0755目录被拒绝，但077下实际创建为0700。仅改变子进程umask的定点对照证明077失败/022通过；首轮mask未单独采集，不伪造确切当时值。固定子进程umask022后同范围完整687项exit0、20原生skip，221.500秒；完整Onboard快照前后不变。失败、定点诊断和最终全量分别保留。
- 完整Onboard副本的实际CLI preflight、相同根去重、非绝对路径拒绝及/bin/bash入口smoke通过；临时HOME保持空，副本逐文件一致并已清理。首轮验证器误把重复根当拒绝输入，已按现行规范纠正并保存失败，不改产品。无新增安装/模型请求/真实HOME写入。
- 20个macOS原生skip包含Windows专属路径/PowerShell/Git Bash、大小写敏感卷及opt-in Codex；不当作对应平台通过。最终候选三平台CI仍为必需，历史base CI和本机dirty证据不替代。
- 私有原生报告/中文汇总位于本任务被忽略的`reports/readiness-main-2026_10_14-00_03_03/`：含37AC映射、两路review原文、baseline CI原生报告、首轮失败、诊断、完整复跑、CLI smoke、Release Readiness Review和分阶段publication-plan。不发布raw/HOME/账号/图。
- 既有LESSON-20260930-kuno-umask-sensitive-test-evidence及同日full-suite lesson覆盖本次环境教训，不另造重复lesson。本机准备完成时readiness为blocked；随后用户明确授权候选PR阶段，TaskStore于2026-10-14T07:39:18.007306+08:00将main绑定改为release/v2.0.0。最终精确SHA三平台CI仍待取得，合并/tag/稳定GitHub Release另行确认。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-14T00:03:03.769895+08:00 | planned | in-progress | 用户要求开始P3-03并选择strict；P3-02/P3-05依赖已done，启动发布审查与候选验证，发布写入另行确认 | 主PRD §14.6 P3-03、§15/16及本轮模式选择 |
| 2026-10-14T07:39:18.007306+08:00 | in-progress | in-progress | Explicit branch rebinding from "main" to "release/v2.0.0": 用户明确授权创建release/v2.0.0候选分支并重绑定本任务，仅commit/push/PR取证，不合并或发布 | 本轮用户选择：授权候选PR阶段；九文件范围已展示 |
