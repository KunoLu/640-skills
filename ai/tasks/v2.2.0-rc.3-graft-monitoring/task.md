---
schema_version: 1
id: v2.2.0-rc.3-graft-monitoring
workflow_mode: strict
mode_source: user
mode_note: 按 rc.3 定稿 PRD D11、D12、D13 执行 T1。
status: "checking"
branch: docs/v2.2.0-rc.3-drop-graft-monitoring
created_at: '2026-11-26T14:57:02.767206+08:00'
updated_at: "2026-11-27T09:27:37.594208+08:00"
completed_at: null
"sync_scope": ["prompts/automations/references"]
---
# T1：移除 Graft 版本监控

接手时，基线 `779483005e75615040f0c6840496b9ffd2f7bff7` 上已有 8 个未提交的文档改动。任务记录从接手时开始；不补造此前的执行事件。

## 范围与验收

只改版本监控契约，不删除 rc.2 的 Graft 运行能力。ENTRYPOINT 的监控表和汇总表不再列 Graft；版本检查不查上游、不读受管 pin、不写基线。保留其他工具及非 Graft 的平台接线与隐私检查；保留历史图数据的 ignore 路径检查。双语 README、CHANGELOG 描述同一边界。工作流描述留待 T3；agy 监控留待 T4。仓库 prompt 不代表 live automation 已同步。

## Book Gate Plan

- DDD / grill：D9 与 §5.1 已划清监控和运行能力，未完整调用 grill-with-docs，无新增领域歧义。
- Legacy Safety：非高风险代码改动；以现行文档 diff、表结构和工作流契约测试检查保留行为。
- Refactoring：无生产代码编辑。DDIA / migration：无持久化格式变化、宿主接线或数据迁移。
- Release Readiness：无部署、运行时变更或发布动作。不创建 `.feature`；仓库以版本化规则和现有契约测试描述行为。
- 验证范围：工作流契约、i-have-adhd 文档契约及 D9 允许例外。合入必须绑定同一 PR head 的 OMP 内审、agy 独立外审和 validation 13/13。外审时暂停，不提前标记完成。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-26T14:57:14.936502+08:00 | planned | in-progress | OMP：开始 核对接手的八文件并执行 OMP 内置 /review（未提交改动） | {"changed_files": [], "evidence_files": [], "sync_files": {"prompts/automations/references/version-check-impact.md": {"mtime_ns": 1795663315826479285, "sha256": "571865af252953d8df50ae2dc09b3e2d35f53caf1aae1ecdd1e8bde3f38faa69", "size": 35797}, "prompts/automations/references/version-check-scope.md": {"mtime_ns": 1795663274097958049, "sha256": "98786b6e041909b42a1a3b5774f073f4d3679a42297c71fa1bb359f903524ab8", "size": 9028}}, "validation": ""} |
| 2026-11-26T15:12:40.753878+08:00 | in-progress | in-progress | OMP：完成 核对接手的八文件并执行 OMP 内置 /review（未提交改动） | {"changed_files": ["ENTRYPOINT.md", "prompts/automations/references/version-check-impact.md"], "evidence_files": [], "sync_files": {"ENTRYPOINT.md": {"mtime_ns": 1795677024119457096, "sha256": "77da4daf374ac7f234f87fef522676bb1374e720a7191fa58857f0f7472e2577", "size": 26069}, "prompts/automations/references/version-check-impact.md": {"mtime_ns": 1795677024121350730, "sha256": "b38645204cd3426cb7cb4c5a4b8df41f3fc8c10f69adacf565973ffa1e079cc2", "size": 35943}, "prompts/automations/references/version-check-scope.md": {"mtime_ns": 1795663274097958049, "sha256": "98786b6e041909b42a1a3b5774f073f4d3679a42297c71fa1bb359f903524ab8", "size": 9028}}, "validation": "3 项意见：删除 ENTRYPOINT 引言中的旧 pin 同步例外；恢复迁移 init 的完整证据、计划范围和累计回执检查；不恢复两个 Graft 专用 wiring 模块至监控白名单（模块文档与 PRD §2.1、§5.1 一致）。修正后两文件 pytest：52 passed, 224 subtests passed。两张基线表只删 Graft 行；impact 仅保留两种 ignore 路径。"} |
| 2026-11-26T15:13:01.600831+08:00 | in-progress | checking | OMP：开始提交候选、开 PR，并在精确 head 复审；等待 agy 和 CI。 | 工作区内审意见已逐项处理；本地测试不是 PR CI。合入门禁仍未完成。 |
| 2026-11-26T18:14:18.737659+08:00 | checking | in-progress | OMP：收到 agy 独立审查 CHANGES_REQUESTED，开始修正 F1（P2）。 | PR #232，head 36296e835eee475ed8c19760f248fec242757168，validation 45773684518 为 13/13。agy 核对实际导入：OMP 来源发现、升级和迁移使用 wiring；撤回此前仅按模块职责排除二者的判断。A/B 均不恢复：专用 hooks 与遥测文件协议不属于通用要求。F2（P3）留 T3：删除模块前解开 sbtd_omp_sources 顶层导入，特征测试覆盖 omp_agents_target；另评估升级探测子进程 DNT，不是本 PR 门禁。 |
| 2026-11-26T18:15:13.984142+08:00 | in-progress | checking | OMP：完成 F1 修正与静态验证，开始新 head 的内审、CI 与 agy 复审。 | Python AST 核验来源、升级、迁移计划及验证四个消费者的导入；两个 wiring 文件均列于 scope 只读区和 impact 平台章节，未加入写入区。主 prompt、scope、impact 除 ignore 路径外无 Graft 命中。未改运行模块，未执行接线；旧 SHA 的门禁不继承。 |
| 2026-11-27T09:25:50.086027+08:00 | checking | in-progress | OMP：收到内审 REQUEST_CHANGES，开始修正迁移正文保真与宿主发行证据两项 P1。 | 受审 head cc5f929e04f60e03c58d654287ec01832ec073ff。先修正并在新 head 重新内审；取得通过结论前不交给 agy。 |
| 2026-11-27T09:27:37.594208+08:00 | in-progress | checking | OMP：完成两个 P1 修正和本地验证，开始对修正后的完整 PR 做内置 /review。 | 迁移正文只接受批准计划内的指定受管段操作及精确暂停前缀解除；宿主接线须核对发布包精确版本，含原生组件时核对生命周期。两文件 pytest 52 passed、224 subtests passed；专项路由与 D9 排除检查通过。新 SHA 的 OMP、agy、CI 门禁均不继承旧结果。 |
