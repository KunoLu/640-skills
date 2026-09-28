# SBTD Workflow v2：后继部署批次（P1-21）实施与验证

> 状态：设计已确认，实施进行中。本文只记录已执行事实；验证证据在完成前不预填。

## 1. 背景与设计缺口

一次性迁移批次设计要求 deployment 声明随原 plan 密封（主 PRD §10.2.1）。live 批次（manifest `81a0c3d4…`，apply `9ad02916…`）密封时未含部署声明，P2-03 apply 已完整成功；P2-04 只读预检证实 post-apply 不存在合规的新 plan/apply 链：

- `_platform_operations`（sbtd_migration_plan.py）对钉住的 136 个生成文件做存在性与漂移核对，其中 103 个平台生成物已被前批 apply 合法删除（前批 104 条 remove 操作），任何重 plan 必被 ownership-conflict 阻断。
- `_check_item_freshness` 要求发布 target 为 absent；已迁移目标不满足。
- 上述两门验证的是 apply 前态，而后继批次的前态就是前批的 after；缺口是真实的产品设计缺陷：「plan 密封时漏了 deployment 声明即永久无法部署」。

用户 2026-09-28 显式授权解除维护窗口并采纳方向 1（工具改造），另立本任务。方向 2（108 步 live 恢复后重 plan）与方向 3（维持暂停/终止）经上一会话（OMP session `01a0e61d-e6cd-73c0-9221-0f330287099c`）完整论证排除。

## 2. 设计：后继部署批次（successor deployment batch）v1

### 2.1 定义与边界

后继部署批次绑定一个「apply 已完整成功、deployment 为 null」的前批，承接其未完成的 cleanup 操作，封存新的 deployment 声明，走完 plan→apply→deploy→verify→cleanup 链。边界：

- v1 只允许前批满足：`deployment` 为 null、无 successor 绑定、apply receipt 状态 ∈ {applied, already-complete}（完整成功、自包含累计）。不允许 successor-of-successor，不允许对「本可正常部署」的批次建后继。
- 后继批次不重新迁移数据、不重新发布、不消费路由批准；paused 路由目标经跨 manifest phase-after 处理（§2.4）。
- 后继 plan 除既有 routing_approval_key 签名路径外保持零写入；该签名路径与 successor 输入互斥。
- live 零写入直到部署那一刻；不伪造证据、不回滚、不触碰备份。

### 2.2 CLI 形状

```
onboard.py migration --phase plan --projects-root <roots> --backup-root <same-vault> --custodian <same> \
  --successor-manifest <prev-manifest-file> --successor-apply-receipt <prev-apply-file> \
  --deployment-mode init|init-projects [--deployment-platform codex|omp] [--graft-hooks] --json
```

- `--successor-manifest` 与 `--successor-apply-receipt` 必须成组出现，所在私有目录经既有私密性校验（manifest 目录与 backup vault 为两个独立私有区域，不要求互相包含）；与 `--publication-decisions` / `--routing-approvals` / `--routing-approval-key` 互斥。
- `--deployment-mode` 在 successor 输入下必填（后继批次的存在目的就是携带部署声明）。
- `--projects-root` / `--backup-root` / `--custodian` 必须与前批 payload 完全一致；不扫描目录发现前批文件，两个前批文件显式传入。
- apply/verify/cleanup 及 init/init-projects 迁移部署上下文不新增参数：后继链各文档按既有 ID 绑定传递。

### 2.3 plan 验证（全只读，任一失败 blocked）

1. 前批 manifest 与 apply receipt 均为合法文档，ID 与相互绑定一致（`validate_declared_bindings`）；receipt 完整成功（§2.1）。
2. 前批 manifest `deployment` 为 null 且无 `successor` 绑定。
3. 项目根集合、backup_root、custodian 与前批 payload 一致；项目 Git 绑定重新实测。
4. 前态漂移核对（后继批次的前态 = 前批 after）：前批每个 apply succeeded 结果的资源当前状态等于 `result.after`（target 经前批 manifest 操作表解析）；任一漂移 blocked，走人工核对或既有 recovery，不自动放宽。
5. 承接核对：前批每个未完成 cleanup 操作（legacy 树退役、共享 Skills 退役）的目标当前状态仍等于其 `before_requirement.state`；缺失或漂移 blocked，不静默跳过。

### 2.4 后继 manifest 形状与跨 manifest phase-after

`manifest.payload.successor`（可选键，schema 新增）：

| 字段 | 固定语义 |
|---|---|
| `manifest_id` / `apply_id` | 前批 manifest 与完整成功 apply receipt 的 ID；plan 时已对真实文件验证 |
| `apply_results` | 前批 apply 全部资源结果（私有 + 共享 `resource_result` 数组合并）；每项 status 为 succeeded 且 after 非 null；经本 manifest 哈希绑定 |

- `projects[]`：root/platforms/sources 继承前批（sources 状态必须等于当前实测，否则按 §2.3-4 blocked）；`private_operations` 仅含前批 legacy cleanup 操作原样承接 + 部署附加操作。
- `shared_operations`：前批未完成 cleanup（Skills 退役）原样承接 + 部署共享操作；`shared_roots` 覆盖承接与部署目标。
- `publication_decisions` 固定为 `{schema_version:1, items:[]}`；`routing_approvals` 固定为 null。
- `custodian` / `backup_root` / `retention` 继承前批；`created_at` 为本次；`tool_versions` 为当前运行时（跨运行时仍走既有签名 lineage）。
- 部署操作的 `before_requirement` 可声明 `{"kind":"phase-after","phase":"apply","resource_id":R}`，其中 R 是**前批** apply 阶段同资源操作（跨 manifest 引用）。解析使用 `successor.apply_results` 的嵌入结果，不是本批 apply receipt。同 manifest 内既有引用语义不变。
- 安装模板目标：本批无 pause 前驱但 `successor.apply_results` 含同资源 succeeded 结果时，`attach_deployment` 封存跨 manifest phase-after；`validate_deployment_declarations` 对 successor payload 接受并强制该形状（替代既有「同 payload pause 前驱」分支），其余再推导不变。

### 2.5 消费侧行为

- **解析叠层**：deploy/verify/cleanup/recovery 中 `phase-after` 期望值的计算，对含 successor 绑定的 manifest 使用「嵌入前批结果 ∪ 本批 receipt 结果」叠层，本批结果优先；叠层只用于期望值计算，不进入结果枚举、状态绑定或备份重叠核对（嵌入结果的 backup_ref 由前批 receipt 链负责，不在本批重复核对）。
- **apply（后继）**：无 apply 操作，标准流程产出空结果成功 receipt，并按本批 manifest_id 备份 sources，供后续 `_check_source_backups`。
- **deploy**：`load_deployment_context` 以叠层解析 before 期望；绑定、授权闭环、漂移核对、证据原子保存不变。
- **verify/cleanup**：承接的 cleanup 操作按既有语义验证与执行；`validate_declared_bindings` / `_bind_stage_states` 以同一叠层计算期望。
- **闭合集再推导**（`validate_legacy_inputs` successor 分支）：每项目非部署私有操作恰为一条 legacy cleanup；shared 仅含 cleanup 退役与部署集合；跳过 inventory/publication/identity/platform-removal 重推导（已由前批 receipt 证明，属 apply 前态门）；`validate_deployment_declarations` 与 `_bind_approved_routing`（null 通过）照常。

### 2.6 负面与 fail-closed

- 前批 receipt 非完整成功 / 前批 `deployment` 非 null / 前批含 successor 绑定 → blocked。
- 任一前批 after 漂移、承接 cleanup 前态漂移 → blocked；不恢复前态、不伪造证据。
- 篡改后继 manifest（删减 cleanup、新增操作、替换嵌入结果）→ ID 与闭合集校验拒绝。
- 无 successor 绑定的 manifest 行为完全不变（既有同资源、同 payload 校验）。

### 2.7 证据链

successor manifest + 其 apply receipt + deployment evidence + verification + cleanup receipt 全部按既有 ID 绑定逐级传递；`successor.manifest_id/apply_id` 记录前批身份；前批 receipt、备份、现场保留，不改写。

## 3. 实施记录

实际改动（分支 `p1-21-successor-deploy-batch`，基线 main `506f66e`）：

- `sbtd-workflow-onboard/onboard-contracts.schema.json`：`manifest_payload` 增加可选 `successor` 键与 `successor_binding` 定义（manifest_id/apply_id/apply_results，apply_results 为 resource_result 数组、minItems 1）。
- `sbtd-workflow-onboard/scripts/onboard_contracts.py`：新增公开 `resolution_stage_results`（successor 嵌入结果叠层，只用于期望值解析）；`_bind_stage_states` 增加 resolution 参数，`validate_declared_bindings` 以叠层调用；`_check_recovery_goal` 对 successor manifest 的 phase-after 初始态经叠层解析；`_check_manifest_payload` 增加 successor 绑定语义校验（deployment 必填、嵌入结果均为 succeeded 且 after 非 null、resource_id 唯一）与「无同 manifest 前驱的 phase-after 须命中嵌入结果」分支。
- `sbtd-workflow-onboard/scripts/sbtd_migration_plan.py`：新增 `_load_successor_predecessor`（成对输入、canonical 校验、完整绑定与成功门、deployment 为 null 且非 successor 的前批门）与 `_plan_successor`（根集合/vault/custodian 一致、前批 after 与承接 cleanup 前态逐一实测漂移即 blocked、payload 组装与 attach）；`plan_migration` 增加 successor 分支与互斥校验；`validate_legacy_inputs` 增加 successor 闭集分支（`_validate_successor_project_operations`：非部署私有操作恰为一条 legacy cleanup；shared 与部署校验照常）。
- `sbtd-workflow-onboard/scripts/sbtd_graft_deployment.py`：`attach_deployment` 增加 `successor_pauses`（前批共享 apply 路由操作 target→resource），暂停／被替换路由目标封存跨 manifest phase-after；`validate_deployment_declarations` 增加 successor 嵌入结果分支；`load_deployment_context` 以叠层解析 before 期望。
- `sbtd-workflow-onboard/scripts/sbtd_migration.py`：plan CLI 透传 successor 参数。
- `sbtd-workflow-onboard/scripts/onboard_arguments.py`：plan 新增 `--successor-manifest`／`--successor-apply-receipt` 选项与成对／互斥／必填 `--deployment-mode` 校验。
- 文档：主 PRD 2.8（§10.2.2、§10.2.4、§14.4 P1-21、§14.5 P2-04 依赖与 blocked 事实、§18.3 事件）；`REFERENCE.md` 迁移命令形状与 successor 段落；`README.md`／`README.html` 各一段；`CHANGELOG.md` v2.0.0（未发布）新增条目。install.sh/install.ps1 对 migration 为整参转发，无参数白名单，无需改动。
- 测试：新增 `tests/test_sbtd_successor_batch.py`（7 项）。

## 4. 验证证据

验证环境：`/Users/lusonglin/TEMP/sbtd-v2-p1-21-venv`（Python 3.13，按 `sbtd-workflow-onboard/requirements.txt` 声明依赖安装 + pytest）。系统 conda python3.13 缺 tomlkit，早期一次单测失败经对照证实为解释器依赖缺失，与本改动无关，全部正式结果取自声明依赖 venv。

- 红绿隔离测试（零 live 接触，`tests/test_sbtd_successor_batch.py`，7 passed / 6.7s）：
  - 红：post-apply 以「before=当前态」的新批准重 plan，仍在 `_platform_operations` 被 ownership-conflict 阻断（钉住的 `.codex` 生成物已被前批合法删除），证实缺口存在。
  - 绿：successor plan 封存绑定 manifest（successor 绑定 ID、空 publication、null routing、仅一条 legacy cleanup、暂停路由目标为跨 manifest phase-after），`validate_legacy_inputs` 通过；successor apply 返回 applied（previous_receipt_id 为 null）并按本批 manifest_id 备份 sources；`load_deployment_context` 通过且暂停模板的期望前态等于当前实测（改动前此处为 missing-deployment-plan/binding-violation）。successor plan 前后 base 快照一致（零写入）。
  - 负面：非完整成功回执 → binding-violation；前批已含 deployment → successor-conflict；前批 after 漂移 → state-conflict；删 cleanup 重封 → semantic-violation；清空嵌入结果 → schema 拒绝；CLI 缺对／缺 deployment-mode／与 publication、routing 输入混用／用于 apply 阶段均被 argparse 拒绝。
- 定点回归：迁移／部署／参数 10 个既有测试文件 192 passed、41 subtests passed（venv）。
- 全量：`/Users/lusonglin/TEMP/sbtd-v2-p1-21-venv/bin/python -m pytest tests/ -q -p no:cacheprovider` → 1160 passed, 8 skipped（既有平台 skip）, 806 subtests passed, 399.75s。
- `ruff check` 全部改动文件：All checks passed。

未执行：真实部署执行、live successor 批次（归 P2-04 重做）、verify/cleanup 的 live 链、Windows 原生、sync/live automation。

## 5. Review 与 findings

（待独立只读审查后填写。）

## 6. 任务合并与状态

（待任务 PR／状态 PR 闭环后填写。）
