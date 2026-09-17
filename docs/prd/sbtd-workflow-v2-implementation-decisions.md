# SBTD v2 实施调整记录

本文件记录主 [PRD](sbtd-workflow-v2-trellis-removal-graft-migration-prd.md) 在实施中经过判断的逻辑、边界或执行协议调整。任务状态、完成时间及依赖仍以主 PRD §14 为唯一事实源；本文件不复制第二份台账。没有记录的产品边界仍按主 PRD 执行。

## D-IMP-01：从规划授权进入逐任务实施

- 日期：2026-09-17。
- 依据：用户在 PRD 2.6 提交后明确要求实施全部计划，并规定逐任务分支、循环独立 review、处理 advisor、PR 合并、主分支同步、分支删除与合并后状态更新。
- 原边界：主 PRD §1／§18.2 的“本轮不执行生产代码改造”描述最初仅交付 PRD 的授权范围。
- 新边界：允许在本配置源仓库实施计划任务及隔离测试；每项从最新 main 建任务分支，完成后循环 review 至零新发现，并处理所有已收到 advisor。用户已授权通过 PR 使用 `--admin` 合并。
- 保留限制：不得把全计划开发授权扩大为真实项目迁移、HOME／全局工具接线、独立 workflow sync、hooks opt-in、旧数据清理、发布 tag 或备份销毁授权。需要具体目标、身份、环境或独立确认时仍暂停询问。推荐澄清选项的预授权不能替代缺失事实或危险操作确认。
- 理由：更新已被用户改变的执行授权，而不重写已经确认的产品安全边界。
- 验证：每项 PR 记录 task ID、分支、验证证据及审查结论；合并后核对 MERGED 与 merge SHA，再同步 main、更新主 PRD。

## D-IMP-02：合并后台账更新通过窄范围文档 PR

- 日期：2026-09-17。
- 问题：任务完成时间和 merge SHA 只有合并后才有真实证据，不能提前填入任务 PR；直接推送 main 会绕过仓库的 PR 规则。
- 决定：任务 PR 中最多记为 checking，保留未完成时间；确认任务 PR 已合并后，从 main 建 `docs/<task-id>-merged-status` 窄范围分支，立即将主 PRD 对应行更新为 done，记录实际验收完成时间、任务 PR 和 merge SHA。该状态更新也经过独立 review 与 PR 合并，不直接推送 main。完成时间记录验收与任务合并均已确认、台账实际更新的时间，不猜测未来时间。
- 顺序：任务分支验证／review／PR 合并 → main fast-forward → 核对并删除已合并任务分支 → 状态文档分支更新／review／PR 合并 → main fast-forward → 删除状态分支 → 下一项任务。Git 分支同步不触发本机 workflow sync。
- 边界：状态文档 PR 属于同一任务的收尾，不增加产品实现任务或第二套进度来源；它不再次产生需要递归追踪的产品完成事件。若状态 PR 被阻断，保留已确认的任务合并事实与待同步状态，不宣称后续依赖已解锁。
- 理由：同时满足用户“合并完成后同步更新 PRD”和仓库 protected-main 的 PR 路径，不预填成功、不依赖管理员直接推送绕过。
- 既有例外：`34a15499e8c13301ec5da7cf172bd9a94915a73d` 曾直接推送 main，远端显示绕过“Changes must be made through a pull request”；该提交没有独立 PR review，不能拿此前 `6855796…` 的审查覆盖它。本协议从 P0-02 起执行。

## D-IMP-03：区分历史事件形状与新入阻塞操作

- 日期：2026-09-17；任务：P0-03。
- 依据：PRD §7.5 同时要求持续 blocked 不追加入阻塞事件，以及归档／明确分支重绑定不改状态时 from/to 相同。仅靠一个状态对矩阵不能同时判断操作意图。
- 决定：持久格式仍为 task.md 中五列状态事件表，不新增 action 列或 sidecar。schema 的 stateEvent 校验历史行形状；新入阻塞候选额外使用 blockEntryEvent，只允许 planned/in-progress/checking → blocked。持续阻塞仅更新原因；blocked→blocked 只可能是有实际操作与授权的元数据事件，不能成为恢复扫描的新阻塞前态。
- 理由：不通过禁止合法重绑定来掩盖持续阻塞问题，也不把理由文本当可执行命令或授权证明。
- 验证：拒绝重复入阻塞的红／绿回归，以及保留 blocked 重绑定历史的正向案例；完整历史配对与真实操作授权由 P1-17/P1-18 验证。

## D-IMP-04：显式时间断言与规范表示

- 日期：2026-09-17；任务：P0-03。
- 发现：当前 jsonschema 的可选 date-time checker 未注册，单写 format 会接受缺时区或不存在的日期。
- 决定：v1 时间规范表示为带秒的 `YYYY-MM-DDTHH:mm:ss[.fraction]Z` 或显式 `±HH:mm`；schema 约束词法形状，验证端必须另做真实日历和时区断言。测试通过标准库解析注册 checker，不新增运行依赖。历史补录事件才可 at=unknown；新入阻塞等当前操作事件使用实际时间。只有能证明等价且保留旧原件时，迁移才把其他有时区的旧 ISO 8601 表示规范化；缺时区或来源不明不能按当前时区补造，按历史未知处理。
- 理由：让验证结果不依赖可选格式包的安装状态；规范序列化不改变实际时刻，历史无法证明仍保留未知。
- 验证：无时区与 2 月 31 日输入均被拒绝，迁移未知时间 null 和历史 unknown 补录边界保持；实际时钟与跨事件顺序由 P1 实现证明。

## D-IMP-05：P0-04 候选先行，P0-07 原子发布入口

- 日期：2026-09-17；任务：P0-04／P0-07。
- 冲突：P0-04 先交付 sbtd-task，P0-07 又要求新目录／catalog／旧入口原子切换；用户要求每项分别合入 main，若先放正式 SKILL.md，会被递归 discovery 看见尚未与 catalog 对齐的新入口。
- 决定：P0-04 的完整入口保存为 `docs/prd/sbtd-task-candidate/entrypoint.md`，references/schema/LICENSE/NOTICE 自包含，不使用 discovery 文件名。P0-07 在同一原子变更中把完整候选移入 `sbtd-workflow-onboard/templates/skills/sbtd-task/`、将入口命名为 SKILL.md、切换 catalog、删除两个旧有效目录，并迁移引用／断言；不保留候选副本或兼容 alias。
- schema 从 P0-03 路径原样移入候选 references，始终一个 canonical 副本；bytes、URN 与行为不变，迁移消费者路径。历史报告不重写。
- 理由：保持每任务可独立 review/合并，又不发布半切换的可发现 Skill；这只是阶段资产路径调整，不延后 P0-04 的内容完成、不缩减 P0-07 的真实安装验收。
- 验证：候选无 SKILL.md、catalog 仍为既有15项bundled；隔离复制并以最终入口名打开后所有内部链接可达，schema摘要与原版一致；P0-07仍必须真实执行catalog驱动的隔离安装。

## D-IMP-06：完整 grill 后的 DDD 门禁不按模式降级

- 日期：2026-09-17；任务：P0-04。
- 冲突：原 PRD §8.2 允许 default/lite 在后置 DDD Skill 缺失时用替代检查前进，与完整 grill 后必须调用具名 reviewer 并取得可见通过结果的门禁冲突；review/advisor 已明确指出。
- 决定：完整 grill 后，三模式均必须调用 book-ddd-distilled-modeling，输出独立 DDD Boundary Review 并按其状态／修正回路通过。不可用、不可读取或必要证据缺失均 blocked，不能确认需求／进入设计；不以内嵌建模、替代检查或降模式绕过。
- 保留轻量边界：未触发完整grill后置门禁的default/lite领域分析仍可按风险使用可用方法；该门禁不取消图工具等无关可选能力的正常降级，未决实质歧义始终限制相关决定。此调整不把全部普通任务变成 strict，也不自动授权安装缺失 Skill。
- 验证与追溯：同步公共入口、主 PRD 与 P0-02 保留表，补 MR-27。旧 P0-10 的26项审查／完成记录保留；新增边界在 P0-04 review 验收，真实 host 证明仍属 P1。

## D-IMP-07：公共规则与被调用 Skill 同批激活

- 日期：2026-09-17；任务：P0-05／P0-07。
- 冲突：若 P0-05 立即覆盖生效模板，安装出的新 AGENTS 会调用尚未注册／安装的 sbtd-task；保留旧 catalog 又会混用两套路由。
- 决定：P0-05 完整规则候选存放于 `docs/prd/sbtd-agent-candidates/{global,project}.md`，详细方法／工具／输出协议进入已有 sbtd-task 候选 references。P0-07 增加 P0-05 依赖，并在 D-IMP-05 的同一切换中将两份候选替换正式 AGENTS 模板、迁移全部候选引用、移除候选目录。内容评审在 P0-05 完成；正式安装验证由 P0-07 执行。
- 保留边界：不延后需求内容、不把候选包装成已经激活，不提前更新实际运行说明或写入 HOME；P1 仍负责真实 host 与 token 计量。项目独立 fallback 不要求全局 Skill 已安装，但不能替代 strict 必需 reviewer 或完整 grill 后的具名 DDD 门禁。
- 理由：让调用方、被调用方和 catalog 保持一致，同时满足逐任务 PR 与无兼容 alias 的干净切换。
- 验证：临时安装布局中检查候选链接／schema／资产完整性，验证正式模板及 catalog 在本任务中未变化；P0-07 必须真实执行更新后的完整安装路径，不以此静态检查代替。

## D-IMP-08：lessons 身份规则与新路由同批切换

- 日期：2026-09-17；任务：P0-06／P0-07。
- 冲突：当前生效AGENTS仍要求旧身份来源，若P0-06先替换同名lessons-record，会在一次安装中混用旧调用方与新身份路径。
- 决定：完整新版Skill放在`docs/prd/lessons-record-candidate/entrypoint.md`及references/LICENSE/NOTICE，非discovery；同步补齐P0-05的两份AGENTS候选身份边界。P0-07已有P0-06依赖，在同一原子切换中替换正式lessons-record完整目录、迁移引用并移除候选，不保留alias或双份canonical。bundled计数不因此变化。
- 保留边界：P0-06交付全部规则内容和分支评审；P0-07验真实安装，P1-19验身份文件／worktree执行，P1-12验迁移。此阶段不创建用户身份、不迁移旧文件、不改当前生效Skill或安装器。
- 验证：隔离最终包名的完整性与链接、LICENSE/NOTICE逐字一致；当前正式Skill及模板／catalog不变。无需为规则文本制造源码断言测试，语义交由独立review，实际行为验收保留其P1所有者。

## D-IMP-09：身份缺失与未知／异常的精确区分

- 日期：2026-09-17；任务：P0-06。
- 发现：两轮review发现“无有效身份／无主身份”可能把现存异常或未知worktree当作缺失；仅修候选仍留下主PRD简略表述，P1实现可能依据不同来源作相反决定。
- 决定：首次建立／旧名复制都需本地文件确实缺失与安全父路径，并已证实非linked（含已确认非Git），或已证实linked且主新文件也确实缺失、路径安全。现存非法／不可读／不安全的允许来源停该解析；Git/worktree归属未知不能证明无主来源。合法主新身份先于所有旧名决定，只读沿用。
- 同步：主PRD §8.3／§11.6／AC-25／D-25/26、独立Skill、迁移reference及两份路由候选／验收矩阵遵循同一判定；不修改历史报告以冒充早已验证。
- 边界：这是把原“异常不得绕过／本地新身份优先”的约束消歧，不授权任何真实身份写入、Git修复、迁移或名字映射。缺证据限制身份建立，default/lite其他安全工作仍可继续。
- 验证：P0独立语义review，P1-19/P1-12分别以真实缺失、非法、不可读、未知worktree与主身份优先分支证明执行；单纯unit旧套件通过不算此新行为的运行证明。

## D-IMP-10：catalog 切换不冒充完整生命周期就绪

- 日期：2026-09-17；任务：P0-07。
- 事实：PRD已把P0-07限定为真实catalog/bundled安装层，完整CLI、init/reset、host和迁移留给P1；当前旧bootstrap提示却仍要求调用本项删除的Skill，文档也可能让用户把新payload当成完整v2安装器。
- 决定：保持现有bootstrap检测状态及数据路径，仅将失效的requiredAction改为保全旧产物、请求显式SBTD迁移，不执行退役Gate或把旧文件解释为新任务。README两份与Onboard说明明确未发布阶段及不得在真实项目运行本开发分支旧生命周期；完整实现／验证后由P1文档任务解除此限制。
- 验收：P0-07真实执行既有catalog planner/copy路径，证明14 bundled／19 external元数据、完整树和init/reset复制策略；不把此smoke或mock-backed旧CLI测试宣称为完整v2或真实host证明。P1的所有任务和验收义务不减少。
- 安全：只删除本仓库已确认无用户改动的两旧有效源目录；不自动处理用户已安装旧Skill，不改HOME、live automation、监控版本或任何真实项目。
- 追溯：源目录切换以单个完整提交发布，移动前保留私有文件快照；旧报告继续绑定旧head，新证明在最终提交重新产生。并行worker的中途验证不计入验收，最终统一由主线程执行。

## D-IMP-11：项目模板与语义探针同批对齐

- 日期：2026-09-17；任务：P0-08。
- 依赖：现有安装器仍以Trellis的track/ignore探针验收项目模板；仅移除模板旧段会使新模板被安装器拒绝，或令新的本地／共享路径不被检查。
- 决定：P0-08同时更新项目模板、`GITIGNORE_MUST_TRACK_PROBES`／`GITIGNORE_MUST_IGNORE_PROBES`、过时提示与真实Git fixtures。保留原NUL解析、错误来源、无Git未验证、fatal/短响应失败和追加幂等实现，不增加规则引擎。
- 保留边界：新模板删除14条旧工具规则，只新增4条根保护，56条通用规则及相对顺序保持；源仓根五行不在本项修改。既有项目的旧段／用户自定义规则不自动删除，Git索引不被改写。
- 分层：本项证明模板及直接规则判定消费者，不实现完整迁移、保留路径业务所有权或tracked数据处置。那些P1门禁不能通过一次`--no-index`规则检查宣称完成，当前过渡生命周期仍不用于真实项目部署。
- 证明：先运行真实CLI＋Git tracer，观察新本地路径红测，再同步模板／探针转绿；补文件、symlink、根锚定、共享冲突和旧规则保留，最终head再做计划全量及原生smoke。
- Review补充：共享探针覆盖PRD§7.9公开固定分支，而不仅是父目录样例；九组遗漏以18条精确排除的真实CLI红绿回归修正。代表性探针不等于自定义路径穷举或实际迁移清单验证。
- Advisor裁决：不采纳把旧`.claude/{agents,commands,hooks,settings.json}`恢复为所有v2项目必需探针的建议。§11.7明确保留旧平台缓存不代表接入，README人工清理旧`.claude/`的前提是项目确实需要追踪相应资产；新增无条件探针会误阻未接入平台的项目。保留并澄清原迁移说明，独立reviewer认可撤回该项；实际旧集成处置仍按P1授权清单。

## D-IMP-12：协议基础与可执行入口原子接入分开

- 日期：2026-09-18；任务：P1-01。
- 事实：现有Python入口的Trellis参数、计划／安装结果与两种安装器仍有直接依赖；仅换parser会让已存在调用者失配。PRD明确P1-01只交付解析／schema／envelope基础，不持有迁移、部署或恢复行为的完成证明。
- 决定：P1-01新增可直接调用、实际执行校验的纯Python契约模块与闭集schema，覆盖批准快照、私有／共享操作、init迁移上下文、deploymentEvidence及恢复输入／输出。它没有第二个CLI执行入口、不注册未实现handler、不以blocked占位handler或伪成功充当执行器。现行公开入口本项不激活新协议。
- 接入：对应P1行为生产者使用同一契约模块；激活相关公开入口时，必须同批删除被替代参数／字段并迁移直接调用者、测试和文档，不留兼容alias。P1-02/04/05/12/13/20分别承担既定生命周期／部署／迁移／恢复行为；P1-07/08仍负责完整包装器对等转发，P1-14/15复验真实链路。内部接口证明不能冒充这些行为已可发布。
- 校验边界：复用已有owned验证器采用的Draft 2020-12 `jsonschema`，在Onboard目录声明依赖；缺依赖fail-closed，不复制通用schema引擎或静默降级。严格解码、canonical ID及跨字段不变量独立补齐。文件引用存在性、symlink／权限／物理别名、真实授权、执行与报告真实性仍由实际阶段校验，不能由schema/hash推出。
- 证明：首次编辑前，现有CLI四场景验证project-only单JSON、参数错误stderr+2、未注册迁移明确拒绝与旧帮助可用，隔离HOME/两项目零写入。新增模块按真实解析／校验／序列化接口验证，再跑现有完整回归；不修改原生project-validation证据schema或stable镜像。
- 依赖执行路径：`npx skills add`与现有目录复制不会执行pip，不能由requirements文件存在推断validator可用。jsonschema惰性加载；现有CLI及纯参数解析不受缺依赖影响，校验则明确fail-closed。验收须覆盖完整隔离安装副本的缺依赖进程，以及私有venv按副本requirements实际安装后的成功校验，并记录实际解释器／依赖版本；不在真实HOME或全局Python安装。
