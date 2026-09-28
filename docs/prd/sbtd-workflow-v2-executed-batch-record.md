# P2-06 密封批次已执行事实登记

本文件只登记已经发生的 live apply 事实。它不是 P2-03 的关闭合同，不修改 AC-18，也不把缺证据写成通过。

## 1. 与 P2-03 的边界

- P2-03 仍是 in-progress。当前验收为主 PRD §15.2 的 C1–C6 与 AC-17/18/29/30 的本阶段子项，全部由 P2-03 拥有。
- 本批仍没有原始 partial apply receipt，旧 Trellis 仍没有可写证据；历史事实不改为通过。按用户采纳的 D-IMP-15，partial retry 必须另有新隔离真实生产者证明，旧 Trellis 可写回退保证明确撤回，runtime_readiness 保持 not-verified；本登记不证明这些新检查通过。
- `2026-09-27T19:20:54+0800` 的旧 §15.2 已被独立审查判为非法 waiver，该历史判定保留。当前 §15.2 已与有效 AC-18 同步修订，需完成新 required 验证和独立审查；本项不复活旧关闭尝试，不关闭 P2-03。
- P2-04 的 P2-03 前置保持不变。本项完成、登记或审查都不授权 P2-04、cleanup、删备份、sync、改 hooks、host smoke、108 步 live 回滚，或调用已退役 Trellis。

## 2. 本项只登记的事实

这些事实已经发生。登记它们不等于 AC-18 通过。

1. live apply status `applied`。manifest `81a0c3d4bc63d906da67f6502b4f218d14a0d410376ad4ad9b354d93f5e280d2`。apply_id `9ad029161fe57421a682ed44adaddf8c54d73c45d84eea7ea3341d5fa4497c6f`。
2. 同一密封批次的完整回执重试 status `already-complete`。apply_id `3621a7fc6a1e3758338cb5e6114f20a5933bb2a830d0e6a0f13e5bfdebbc8ccc`。没有再写 live。
3. 恢复续作代码在提交 `bb8eb0b3fe68e151c1dea6aec285ff294f321116`。未执行 live recovery apply。

## 3. 本项验收

本项可以单独记录为已建立。它的完成条件只有：台账有独立行，且该行没有把 AC-18 或 P2-03 写成通过。

本项 done 以后，P2-03 仍须自行满足当前 C1–C6、独立就绪审查和任务／状态 PR 收口；本项不把原 AC-18 的缺证据写成通过，不解除 P2-04 对 P2-03 的依赖。
