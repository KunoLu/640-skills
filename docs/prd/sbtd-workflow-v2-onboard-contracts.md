# P1-01：Onboard 协议基础与接入边界

## 交付与非目标

本项交付可实际调用的纯Python参数解析、版本化交换对象校验、canonical ID和单JSON输出契约；不是新的迁移执行器。按主PRD §10.2及§14，包含publication-decisions批准快照、manifest的私有／共享操作、阶段收据、deployment-evidence及init迁移上下文、recovery plan／receipt、migration／recovery envelope。

实现放在自包含Onboard目录内，由同一Python实现供后续生产者／消费者接入。现有`onboard.py`公开入口与两种安装器本项保持原行为；不注册没有执行实现的命令，不放置返回伪成功／占位blocked的handler。新增模块不提供第二个CLI入口。接入相关行为时须同批迁移直接调用者、删除被替代参数／字段，不留兼容alias；见[D-IMP-12](sbtd-workflow-v2-implementation-decisions.md#d-imp-12协议基础与可执行入口原子接入分开)。接口验证通过不能标记P1-04/05/12/13/20行为或AC-35完成。

## Book Gate Plan 与首次编辑前结果

| Skill | 触发／范围 | 阶段 | Gate state |
|---|---|---|---|
| book-legacy-change-safety | mandatory：既有公开CLI、JSON和退出码边界必须保持 | 首次实现前 | passed |
| book-refactoring-pass | mandatory：已核对现有parser/run/计划与两端消费者，避免半切换 | 首次实现前 | passed |
| book-ddd-distilled-modeling | required：资源／操作／批准快照／阶段结果的模型边界 | schema稳定前 | passed |
| book-ddia-data-design | mandatory：持久交换对象、ID、共享归属和累计证据 | schema稳定前 | passed |
| book-release-readiness | required：新增协议解析／校验／输出语义，仅限接口层 | 首轮独立review发现后重新验证／审核 | running |

未完整grill-with-docs：产品边界已由PRD收敛，当前落地机器字段及原子接入时序，不推断新的用户授权或真实环境。

Legacy Change Safety Review：characterized，normal。基线`9e45e867e9be850e93ab7f2133172da142faf013`上的真实CLI四场景证明：check-projects单JSON／两个项目无全局检查；参数错误stderr+2且不写入；未注册migration明确拒绝；旧plan帮助仍可用。隔离HOME和两项目均保持为空。正式本地证据为`tests/api/reports/api-report-onboard-interface-baseline-p1-01-interface-contracts-2026_09_18-01_02_56.json`及同stem中文汇总／已验证envelope；这是现有行为刻画，不是新协议通过。

Refactoring Review：proceed，normal。既有build_parser/run/build_plan_payload和Bash/PowerShell消费者已定位；本项新增内聚契约模块，不为接口阶段改造旧执行生命周期。已有jsonschema验证模式可复用，不自制通用schema引擎，不先抽取无实际可变性的adapter。安全网是现有公开入口刻画、现有回归及新增真实契约调用；运行接线重构随对应行为任务完成。

DDD Boundary Review：confirmed。resource是物理资源；operation是phase/resource/selector逻辑操作；state是路径类型与摘要，不是阶段status。approval.scope只保存声明的批准结构快照，hash/JSON合法不代表人的授权。协议层、实际资源盘点／授权、执行／证据生产分开；共享资源只有一个拥有者，私有操作只属于本项目，未知状态不当absent，未执行不当成功。核心是迁移／恢复工作流，协议是支撑，JSON和摘要是通用能力。grill修正not-applicable；没有阻塞性产品问题。

DDIA Data Design Review：confirmed。版本化schema和同一Python语义校验是机器契约事实源；本项不读取object_ref所指内容来声称它存在、安全或已被授权，不改项目／HOME。严格UTF-8、闭集、类型、枚举、重复键和非有限数检查；ID按规范payload JSON派生，数组顺序与批准快照保留。累计收据、阶段依赖及绑定只定义/校验声明关系；真实文件、symlink/权限/物理别名、授权、smoke和恢复由既定阶段验证。没有新的journal、锁、调度器或证据索引。

## 实现约束

- 复用已在owned project-validation/knowledge代码中采用的Draft 2020-12 `jsonschema`；在Onboard目录声明同一受限major依赖。缺失时fail-closed，不自动pip安装或回退为弱验证；本机已有依赖，无本轮全局安装。
- 所有列明字段必填，允许null的分支显式建模；未知版本／键／枚举、重复JSON键、非有限数、错误类型和非法摘要拒绝，不自动改名或补默认值。
- publication-decisions逐项核对approval.scope的sources/target_path/decision/candidate_ref，检查ID及目标冲突。结构快照和哈希只证明声明未漂移，真实授权独立。
- manifest私有／共享操作使用同一结构；resource/operation ID按PRD计算。owner_kind表示实际资源所有者／格式，而非读取它的Agent；重复拥有、重复ID、无效前阶段引用及依赖集合冲突拒绝。change只能是已定义的受管结构化操作，不接收shell字符串或另造命令DSL。
- deploymentEvidence仅在显式init/init-projects迁移上下文出现；必需参数成组，previous单独提供不能补成上下文。普通init不得因此扩张范围；本项只固定参数与返回结构，不执行部署或保存receipt。
- migration/recovery阶段参数闭集按PRD；cleanup普通--yes不能代替confirm-cleanup，recovery apply不能临时改变项目范围。参数错误遵循argparse stderr+2；实际授权/绑定/文件失败的envelope由已进入处理器的生产者负责。
- 错误诊断只报告固定字段／规则，不把敏感原值、私有哈希或原始JSON拼进公开错误。原生验证证据schema和external stable镜像均不修改。

## 验证策略

新增可保留回归只覆盖真实接口边界：严格解码、合法round-trip、canonical顺序/Unicode/伪造ID、闭集与类型、批准scope漂移、私有/共享ID及依赖冲突、阶段参数误用、累计结果和envelope约束。采用真实纯函数与真实子进程调用，不用mock回声或源码字符串断言充当新行为证明。本仓不生成.feature，按中文PRD追溯。

冻结完整变更后重跑项目计划全量和独立契约smoke，保留正式命名报告、中文汇总、envelope及真实SHA；接口fixture/合法hash不能升级成迁移、部署、恢复或host通过。私有编辑备份保留到最终head验证、独立review和实施PR合并以后。

## 安装副本与依赖证明

Onboard目录复制／`npx skills add`只交付文件，不执行pip。jsonschema必须惰性加载，不能让新协议依赖破坏现有CLI或纯参数解析；缺依赖校验明确失败，不回退为只检查几个字段。使用者通过实际运行解释器执行`python -m pip install -r <installed-onboard>/requirements.txt`准备校验依赖；该步骤不是本项对用户全局环境的隐式授权。

完成证据必须包括完整隔离安装副本：无第三方site-packages的进程能运行原有CLI/参数解析，但契约校验fail-closed；独立私有venv从副本requirements真实安装依赖后，加载副本自身schema并通过契约调用。记录解释器与实际包版本，不能仅用源码目录或宿主已装jsonschema的CI结果声称安装副本已可用。

## 模块协作接口

- `scripts/onboard_arguments.py`提供`parse_workflow_args(argv)`：返回argparse Namespace，覆盖check/check-projects/plan/init/reset/init-projects及完整目标migration/recovery语法。只解析与检查参数组合，不读写用户路径；不是现行onboard.py入口接线。保留已有非Trellis公共选项，拒绝旧四个Trellis参数、缩写alias、重复单值证据参数和跨phase参数。
- `scripts/onboard_contracts.py`负责严格解码、schema/内部不变量、sealed payload摘要、声明间绑定与累计保全、envelope及单JSON序列化；schema为`onboard-contracts.schema.json`。参考项目已有jsonschema模式，但依赖惰性加载，错误不包含被拒绝的原值。
- 结构化change只复用当前文件／目录复制、ignore缺行追加与已受管删除四类低层操作：`copy-file/copy-directory/ensure-file-block/remove`；不会解释任意shell文本。后续实际执行器如需要新的受管种类，须以真实实现同批扩展闭集schema与校验，不能用自由字段提前放开。owner_kind是file/directory/markdown/gitignore/json/toml实际资源类别，不以消费Agent给同一物理路径重复命名；真实格式／归属仍在阶段入口确认。
- manifest补齐未在PRD逐字命名的机器载体：projects中的platforms/sources，shared_roots记录HOME/Skill根与依赖项目；源引用与before_requirement承载源／目标状态；retention只记录正常／明确终止的人工保留要求，不新增生命周期配置或自动处置入口。
- recovery step_id使用规范JSON数组`["recovery",manifest_id,phase,resource_id]`的SHA-256，保持同一逻辑资源／原阶段稳定；不替代原operation_ids。recovery共享结果仅集中引用同一资源的step_ids，不复制到每个项目。
- 校验声明的关联与累计字段不代表引用对象已读取／实际状态匹配。绑定函数仅处理调用方明确提供的对象和raw bytes，不扫描文件，也不把缺阶段证据推断成未执行；提供recovery plan时，每个inverse步骤必须有非空来源引用及同时提供的对应阶段结果，不能跳过未提供阶段的provenance校验。其他未提供对象不作运行事实推断；实际命令须按PRD要求提供并核对完整证据链。

## 集成检查与证据边界

参数worker曾违反显式skip-validation要求运行scoped测试，该结果未计入验收。主线程在两个写入者结束后统一验证：参数38项通过；codec首轮因9个类初始化失败只执行62项，不能视为完整覆盖。恢复fixture修复后原文件实际99项；首次冻结head的codec为121项，独立review后继续补充关系回归。

主线程修复了实际复现的声明漏洞：成功结果缺失／错配原始备份、恢复保护与计划状态不符、共享单依赖归属丢失、前阶段引用缺失、同目标所有者冲突、私有／备份／发布路径声明越界、raw bytes与对象不一致、失败严重程度被envelope掩盖、累计原始引用或上游证据可替换、成功缺报告及未完成步骤。真实partial允许省略未执行结果，但成功项目不能借整体failed逃避本阶段完整覆盖。各回归保留red/green与定点／影响范围报告；反例曾未真正改变时间字段，已改为显式不同时间及不同ID，不把无效变异当可靠red证明。

目录／候选／状态均为合成契约fixture；所有这些通过只证明结构与声明一致性，不证明对应路径、权限、授权、操作或报告真实存在。已准备并实际执行完整隔离candidate安装副本：无jsonschema时原CLI帮助／纯解析仍可用且校验validator-unavailable；私有venv按副本requirements实际安装jsonschema 4.26.0后14份对象及绑定／单JSON通过；暂移副本schema后schema-unavailable，未回读源码，随后恢复。该阶段为dirty本地证据，最终head必须另行完整重跑。

Code Readability Review：新模块与测试已按项目Ruff格式整理；去掉收集／排序全部错误后只消费首项的多余工作，真实无site-packages子进程替代对私有validator缓存的修改。类型修正采用Mapping只读参数、准确NoReturn和真实模块装载检查，不加ignore/cast掩盖错误。新5个Python文件Ruff/ty通过；受影响旧workflow测试的Ruff为5→5，无新增。公共自动化范围测试保留只读／可写集合安全边界，不再钉整句路径顺序，也不声称证明LLM执行。

200项影响范围及提交前完整425 tests/83.124s/exit0通过；现行onboard.py、install.sh、install.ps1与开发基线一致。该轮仍为dirty本地证据，提交后必须重新生成最终head全量与完整安装副本报告，再独立review；不提前填写本任务done或后续行为验收。

## Scoped Release Readiness Review

- Status：首轮接口readiness已被独立协议review阻断，修正后须重新执行验证／审核；不代表公开CLI、部署、迁移或恢复执行就绪。
- Production path／影响：新解析、版本化数据及输出函数；现行Python入口／两安装器未激活它们。
- Failure modes／防护：严格输入、ID／批准／归属／累计／失败状态约束，依赖或副本schema缺失fail-closed；不执行不可信命令，不把合法hash当授权。
- Capacity／backpressure：无服务、队列或后台任务；仅进程内解析／校验，compiled schema不缓存用户数据。
- Observability／runbook：ContractError保留明确code/exit_code且不回显被拒绝原值；requirements与缺依赖处理已在实际安装副本验证和文档说明。
- Rollout／rollback／cleanup：仍按D-IMP-12由对应生产者原子接入，真实引用/权限/别名/授权/报告真实性必须另验；当前只改受管源，源码备份保持至实施PR合并之后，不触碰真实迁移备份。
- Required validation：新5个Python文件Ruff/ty通过；旧workflow测试Ruff5→5无新增；425项提交前全量与完整副本缺依赖／可用／缺schema三路径通过。最终head在提交后重跑。
- Optional checks／剩余边界：无本项服务、Web交互或设备链路；未声明Windows真执行、Codex/OMP运行或跨阶段恢复通过，这些归既定P1验证任务，不把缺失证明转成通过。

## 首轮独立 review 与修正

冻结head `db58bae22326fb0a889b89e6ced062b290d3c603` 的425项全量、精确安装副本及静态证据保留为历史。`P101SurfaceReviewOne`在参数／文档／安装证据范围零新发现；`P101ProtocolReviewOne`提出9项协议关系finding，全部采纳。前述冻结head不具备合并许可；新head必须重新完整验证并独立review。

修正范围：阶段结果before与manifest／明确提供的上阶段after相符；部署／验收／清理／恢复执行的已提供前置对象成功门；恢复inverse精确来源于阶段结果；私有／共享失败严重性不能降级；partial备份／保护引用与已知before一致；shared target落入唯一且依赖闭包兼容的shared root；恢复receipt与plan的项目scope及input_evidence一致；项目恢复状态不能掩盖依赖失败／pending；所有failed／blocked逐项目记录必须有reason与nextStep。

红测构造曾发生错位编辑及不相关ID/fixture错误；已恢复提交中的原121项，再逐块追加并语法检查。只计修正后隔离反例：8项测试、20个预期assertion失败、无fixture error。未知before的失败fixture不再携带虚构备份；专用可续作fixture明确提供原始before/backup。首轮修复后这些反例通过，不以损坏或提前失败的反例声称覆盖。

恢复状态边界经原reviewer再次核对PRD §10.2.1／§10.2.3：不要求每个源资源status均为succeeded；failed／blocked但前后态已知、确有变化、原始备份完整的部分写入仍可恢复。inverse必须精确复制after/before/backup，未知状态、备份不完整及before==after不产生可执行逆向动作；真实文件证明仍属执行阶段。额外正向／负向测试先证明合法partial未被拒绝，并复现两种no-op被误接受后修复。

F3补充正向边界实际复现：只有apply阶段证据的合法恢复plan曾被“资源必须列出manifest全部阶段operation”拒绝。资源现在只需列出manifest内已证明步骤的operation子集，步骤本身仍须完整匹配相应phase/resource声明，资源与步骤集合继续精确一致；不补造deploy/cleanup动作。此项定点red/green后，完整协议131项通过，提交前全量435项／61.548s通过。以上均为dirty证据，不能替代修复后冻结head证明。

本轮Code Readability／Ponytail复核：保留原始备份／保护引用这一共享不变量，删除仅单行转发的旧result wrapper；阶段前态绑定与恢复inverse证据保持独立职责，不增加通用validation框架。新修改代码／测试Ruff与ty通过；wrapper删除后纳入最终全量重跑。README.md／README.html及版本化automation prompt无需再次改写：既有内部接口、依赖准备和只读边界不变；CHANGELOG已有未发布协议能力条目，本次为同一未合并能力的关系校验修正，不新增用户可见命令或发布叙述。

## 第二轮独立 review

冻结head `1eaa9878c3b05b5e06feab2ed50ec213b603e3d6` 已取得435项／118.184s全量、精确安装副本、静态和envelope验证，仍因第二轮review不得合并。`P101SurfaceReviewTwo`指出argparse会回显未知token／非法choice／无值flag的显式输入；三分支以合成sentinel复现后统一覆盖error诊断，保留静态usage、退出2和空stdout，parser39项与实际三分支smoke通过。移除47处incidental wording pins，不重钉新文案。该修正只改parser及其测试，协议review范围保持冻结直至其返回。

`P101ProtocolReviewTwo`的11项finding均采纳，进入新修复轮：最新前序阶段衔接、manifest同资源同阶段前态一致、完成状态的ref/HEAD快照绑定、verified候选状态绑定、逐项目verified候选完整性、每步恢复的已提供来源、plan内no-op拒绝、首次already-complete拒绝、累计pending步骤宇宙保全、成功envelope与artifact精确一致、私有／共享ownership反例不被无关containment提前拒绝。新head须重新全量／安装副本验证并独立review，当前不标ready或done。

另一个advisory提出所有failed／blocked的已知before都应强制非空备份，未采纳该扩大限制：原reviewer据PRD727/729/765/788确认，备份／保护创建本身失败时须允许保存真实失败与nullable引用；已提供引用不得矛盾，自动inverse另须完整来源。已用真实函数验证未写入缺备份、已写入缺备份时inverse拒绝、恢复保护创建失败三场景；不会把nullable失败收据当作可恢复证明。

第二轮协议反例先取得10项测试／18个预期失败；pending反例曾因共享可变payload污染旧ID而假绿，已先deepcopy保留旧收据，修正后真实复现丢失pending。ownership两项先通过无冲突scope正向控制，再引入满足containment且具有独立operation ID的重复claim，避免无关拒绝。来源门收紧后同步更新全部受影响恢复测试调用者，补齐实际source stages；单依赖共享恢复另建完整合法证据链及正向控制，不让缺来源门掩盖原来的ownership/state/scope负面场景。

阶段状态索引现在一次构建，供前态、verified候选和恢复inverse复用；manifest先保证同资源同阶段只有一个前态，并按本资源最新已声明阶段衔接。已完成／verified项目同时绑定source_ref/head；failed／blocked诊断仍可记录观察差异。候选状态仅在声明verified的相应项目／共享依赖上要求与已提供前序一致，不阻止失败验收记录真实漂移。累计already-complete须有对应前次成功，恢复completed/pending总集合不得丢失；成功envelope及逐项目摘要不得改写artifact的完成变体。

同一消费边界补充证明：canonical ID合法但无前收据identity的already-complete项目，在load_document中曾仍可进入；三类收据均已复现并把该内在矛盾前置到对象校验，重试时仍核对实际传入的前收据成功状态。恢复receipt另核对completed步骤的全部显式depends_on都已completed；以完整来源复现“deploy inverse仍pending、后置apply inverse却完成”后修复，逐项目归因反例改选叶步骤以避免无关依赖错误造成假绿。

F5的合法续作边界再次获原reviewer确认并实测：before/after均已知且相等、原件非absent、旧backup_ref/protection_ref为空时，重试可建立首份匹配before的引用；未知状态或已落地变化不能事后补拍所谓原件；任何已有非空原始引用保持不变。三类收据的合法无写入失败曾被拒绝，已取得真实red并修正，unknown/changed负面边界保留。当前协议144项全部通过，最终head全量／安装副本与下一轮独立review仍待执行。

第二轮修复后的提交前验证：parser39项、协议144项及全量449项／61.674s通过；新5个Python文件Ruff、格式与ty通过。可读性复核保留集中不变量的helper，移除临时共享字典和测试中未用状态的提前构造，已纳入该全量。以上是dirty本地证据；不把它重标为后续冻结commit结果，安装副本、诊断隐私及nullable失败smoke须在新head重新执行后再发起第三轮独立review。
