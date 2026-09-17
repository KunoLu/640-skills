# P0-07 catalog 与正式 payload 原子切换

## 本项边界

本项落实主 [PRD](sbtd-workflow-v2-trellis-removal-graft-migration-prd.md) §10.3／AC-11，从`main @ f1cb5809f5b225837e8be146a51e29b3d5c87ee2`建立`p0-07-catalog-cutover`。P0-04/05/06的内容与调用方在同一提交进入正式安装源；安装层证明不等于完整v2 CLI、init/reset、host、迁移或发布完成。

| 变化 | 正式源／结果 |
|---|---|
| 两个退役bundled entries换成一个 | `skill:sbtd-task` → `templates/skills/sbtd-task`，targetRole为skill，无alias |
| 公共任务Skill完整移入 | [SKILL.md](../../sbtd-workflow-onboard/templates/skills/sbtd-task/SKILL.md)、7份reference/schema、LICENSE/NOTICE，共10资产 |
| 身份Skill完整替换 | [lessons-record](../../sbtd-workflow-onboard/templates/skills/lessons-record/SKILL.md)及显式migration reference、LICENSE/NOTICE，共4资产 |
| 两份规则正式替换 | [全局](../../sbtd-workflow-onboard/templates/agents/AGENTS.global.md)、[项目](../../sbtd-workflow-onboard/templates/agents/AGENTS.project.md) |
| 移除旧有效源 | `templates/skills/trellis-workflow`与`trellis-channel`；不在包内archive旧入口 |
| 集合与schema | 14 bundled／19 external；catalog schema与task-data schema版本／内容保持 |
| 消费者 | schema测试定位、有效Markdown链接、安装测试fixtures、文档清单与原子安装回归一起迁移 |

原候选目录移除，历史路径仅保留于阶段追溯文本；历史原生报告不重写。用户全局目录的旧Skill处置属于P1-13的独立身份／内容安全路径，本项不访问或清理真实HOME。现有external stable镜像、Ponytail provider、Caveman维护、i-have-adhd和初始化目录优先级不改。

## 保持与有限行为改变

catalog仍是唯一安装集合事实源。使用既有`build_operations`／`copy_operation`，不增加安装器、dispatch runtime或兼容shim。保留init跳过合法Skill壳、reset替换受管包、保留不相关目录的现有语义；不把逐项复制说成跨文件事务。

旧bootstrap检测仍保留原状态与数据路径，但其`requiredAction`不再要求调用已删除的Skill；提示保全数据并取得显式SBTD迁移授权，不把旧产物直接解释为新任务，也不宣称runtime就绪。完整移除旧CLI生命周期属于P1，不在P0-07伪造完成。

README两种格式、Onboard入口／REFERENCE及版本化automation prompt必须准确说明当前未发布阶段：正式payload/catalog已切换，完整v2生命周期尚未就绪，不建议对真实项目运行本开发分支的旧生命周期。该限制由P1实际实现／验证解除，不能通过文本提前宣称ready。ENTRYPOINT的监控切换／完整sync事实源仍归P1-10，未改其版本。

## Book Gate Plan

| Skill | 选择与触发事实 | 阶段 | Gate state |
|---|---|---|---|
| book-legacy-change-safety | required：安装目录、discovery和catalog的隐含依赖及回归风险 | 首次切换前 | passed |
| book-refactoring-pass | required：正式规则／目录迁移及生产bootstrap提示修改 | legacy刻画后、实现前 | passed |
| book-ddia-data-design | required：catalog安装集合事实源和同批切换一致性 | 设计稳定前 | passed |
| book-release-readiness | required：安装可见payload改变 | 适用验证后 | planned |
| book-ddd-distilled-modeling | on-demand：沿用已确认领域与模式，无新歧义，未完整grill | 不触发 | not-required |

Legacy Change Safety Review：characterized。移前从精确commit导出tracked包，在启动前隔离HOME/CODEX_HOME/XDG/TMPDIR，真实执行planner/copy；15 bundled／19 external元数据、19个操作、完整树、模板复制、第二次init跳过15个合法包、reset替换受管包且保留不相关Skill均通过。没有调用完整init或第三方CLI。

Refactoring Review：proceed，normal。整目录移动16个候选资产，schema不改，不引入新抽象。删除前核对目标目录内容与HEAD完全一致、没有未知／symlink条目，并保存私有完整备份；其他写入者不触碰这些目标。LSP无可用server，按已知路径／调用点迁移。正式测试在所有写入完成后统一运行。

DDIA Data Design Review：confirmed。catalog与源树／调用方以同一Git提交发布；临时工作树不是部署事务。安装目标权限／写入策略不变，无新状态服务或journal；失败处理不扩大为真实项目迁移。source rollback是目标范围的Git逆向修改，不是删除用户安装或reset --hard。

未完整调用grill-with-docs：原子路径和阶段职责已由PRD、D-IMP-05/07/08确定。TDD采用现有行为基线及同款移后smoke，不为声明式目录变化建立测试专用实现。新增永久测试只防完整包／引用遗漏和半catalog切换；纯源码文案／顺序断言删除，不重新绑定新措辞。实际新测试是否执行过red必须按真实运行记录说明，不把旧15项快照伪称为新测试红测。

## 验证安排与当前证据

- 移前正式本地报告：`tests/api/reports/api-report-catalog-install-baseline-p0-07-catalog-cutover-2026_09_17-19_18_42.json`及同stem中文摘要/envelope。真实catalog复制通过；scope为非HTTP本地smoke、developer-local／exact／local-only，不证明完整init或host。
- 首次报告校验曾因trigger使用了schema外值失败；按实际schema更正为pre-pr并保留原错误envelope。修复临时helper时曾误用未暴露的`_ih`，无文件写入，改为直接重定义。原生安装未重跑或改写结果，最终envelope validator为OK。复用既有Config Schema Confirmation lesson，不新增重复记录。
- 移后必须从最终commit再次导出tracked包，执行相同真实planner/copy路径：14／19，完整sbtd-task与身份包、模板一致，fresh全局根及Onboard内源树均无两个旧目录，init/reset保持约定。
- 先聚焦新安装边界、schema与受影响测试，再运行计划全量；正式原生报告与同stem中文汇总绑定最终head。语义独立review覆盖整个当前diff，所有发现与advisor修复后复审。
- schema内容摘要仍须为`e568fee70b2e795a05ba448c07fbb8ffd4d85e43fe248edb3d228572dd03aa2e`。候选到正式源的字节一致性与当前链接需在最终集成时检查。

## 并行职责与证据控制

主线程拥有catalog／资产／生产提示／schema定位和docs/prd；契约测试、安装测试、分发文档三个writer文件不重叠。全部worker明确禁止中途测试／build／lint／format。

安装测试worker仍提前运行了定点tests与py_compile，该结果不作为验收证据；已要求停止进一步验证。所有写入静止后，由主线程重新运行受影响范围和最终全量，避免以漂移中的源码结果证明最终head。此偏差不授权其他worker验证或提前开始下一任务。

## 收尾范围

README.md、README.html和版本化automation prompt在本项需要更新，因为实际分发目录与路由改变；不执行live automation或workflow sync。CHANGELOG记录未发布分发变更。临时脚本不进入产品；私有移动备份在最终smoke和验证证明资产完整后清理，不触碰任何真实项目备份。P0-07状态只在真实review／PR合并后更新为done。

## Surviving contract 承接与 advisor 处理

三条测试覆盖advisor指出：规则迁移不等于规则退役，不能用移除措辞检查宣称不再需要约束。已恢复未退役公共合同的`test_i_have_adhd_required_external_contract`、`test_every_completed_grill_requires_visible_ddd_boundary_review`、`test_knowledge_ingest_requires_explicit_read_only_intent`，并保留Caveman／Book的公共发布说明检查；没有将它们冒充Agent执行证明，也没有把旧断言改绑为新的长词串。

| 保留合同 | 当前canonical承载 | 本项持续检查／迁移证明 | 尚不声称 |
|---|---|---|---|
| 完整grill后的共同DDD门禁 | AGENTS、sbtd-task公共入口、book-ddd Skill | 保留公共DDD合同测试；已审查候选到正式源再到安装副本字节一致 | host真的调用／通过reviewer |
| strict Book触发与结果合同 | sbtd-task/strict、project fallback、各book Skill | 保留各reviewer公开结果合同测试，完整搬迁保真；旧“三份旧文件重复词句”架构断言退役 | CI证明模型遵从全部流程 |
| Caveman输出状态与ADHD显式激活 | sbtd-task/presentation、外部stable payload | 保留公开说明合同；Caveman维护和ADHD真实安装／损坏拒绝测试不删 | 自动状态在真实host中已验收 |
| 名字格式、marker与历史资产 | lessons-record及migration reference | 从canonical声明提取regex执行合法／非法边界；保留实际Git合并、block ownership、仓库历史结构检查 | 新身份resolver已实现 |
| Knowledge只读意图 | 未修改的gherkin-bdd、knowledge-base实现 | 保留原Gherkin公共意图合同；现有真实ref读取／不切换工作树／幂等与报告测试不删 | 本次改变或重实现Knowledge流程 |
| 安装集合与完整包 | catalog及正式Skill目录 | schema/路径拒绝、真实完整安装树、14/19与旧目录缺席、既有provider检查 | 完整v2 init/reset或真实HOME部署 |

退役的是Trellis调度／旧路径、旧Gate词汇所有权及旧示例布局的断言，不是上表行为。P0-07额外在最终原生smoke中逐字核对`f1cb580…`中16个已审查候选资产、当前canonical与实际安装副本；这是本次搬迁保真，不替代未来回归合同或P1执行验证。

两名测试worker均提前运行了定点检查，已明确不采纳该证据并接管最终验证。worker报告仅刷新忽略的Python缓存并清理其临时fixture；主线程不会引用这些中途结果作为最终head通过依据。
