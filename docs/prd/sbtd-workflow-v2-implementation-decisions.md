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
