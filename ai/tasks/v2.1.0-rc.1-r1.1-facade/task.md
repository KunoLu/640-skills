---
schema_version: 1
id: v2.1.0-rc.1-r1.1-facade
workflow_mode: strict
mode_source: user
mode_note: 用户本次明确要求 SBTD strict mode。
status: "checking"
branch: feat/v2.1.0-rc.1-r1.1-facade
created_at: '2026-10-16T17:28:14.429175+08:00'
updated_at: "2026-10-16T18:05:41.414629+08:00"
completed_at: null
---
交付 v2.1.0-rc.1 的 R1.1：Facade 与旧 helper 兼容包装、显式项目注册。不做 R1.2a 事件存储，不做 R1.2b 宿主适配器，不做 HTTP 服务。

未完整调用 grill-with-docs。PRD v0.2 第 1377 行、ADR 0001 与用户本次交付清单已经固定范围：库接口、调用适配、权限／只读测试，完成门是观察开关关闭前后业务副作用等价。没有未决产品问题需要访谈。领域术语与 registry 所有权仍按 strict 触发审查。

## 范围

- 在 `sbtd-runtime/` 增加库接口，包装既有 TaskStore／TaskRouter／HandoffStore／DeveloperStore，不移动、不改写这些脚本。
- 显式项目注册写入 `SBTD_RUNTIME_HOME` 的 `registry.json`。`project_id` 不由绝对路径派生。取消注册只改授权清单。
- `observation.enabled` 缺省关闭。关闭时 Facade／适配器的项目文件副作用与直接调用 helper 相同，且不写审计文件。
- 开启观察时本包仍不实现事件库；`audit_status=gap`，不写 `audit.db`，业务写入仍不回滚。
- 只读上下文不写任务文件和审计文件。未确认的用户目录统计授权不得放宽完全只读。
- 不扫描 sibling／HOME。拒绝 symlink 根。
- `preview_route` 不调用会保存状态的 `TaskRouter.route`。身份只 `resolve`，不 `ensure`。

## 验收

- 开关关闭时，已注册项目上的适配调用与直接 helper 调用产生相同业务文件。
- 未注册根、只读、symlink、sibling 诱饵有权限测试。
- `sbtd-runtime/tests` 与相关仓库测试通过。

## 测试 seam

用户完成门已指定消费者接口：库接口、调用适配、权限／只读测试。不另开访谈。公开 seam 是 `RuntimeFacade` 与 `HelperAdapter`。旧 `TaskStore` 导入保持可用，不要求先注册。

## Book Gate Plan

| Reviewer | 客观触发／阶段 | Lifecycle | 谓词与结果 |
|---|---|---|---|
| book-ddd-distilled-modeling | 领域术语与规则，需求确认前 | before-dev | confirmed。见正文。未完整 grill。 |
| book-ddia-data-design | registry 持久化与事实源，设计确认前 | before-dev | confirmed。见正文。无事件库。 |
| book-legacy-change-safety | 既有行为缺陷或高回归既有代码 | before-dev | not-needed。不编辑既有 helper。等价性由新路径测试证明，不改变 helper 行为。 |
| book-refactoring-pass | 既有生产代码编辑前 | before-dev | not-needed。只新增 `sbtd-runtime` 文件。 |
| book-release-readiness | 生产运行时／部署／集成变化，验证后 | finish | not-needed。无服务、作业、迁移或发布。 |
| TDD | 高风险包装行为，实现前 | implement | 先红后绿。 |
| gherkin-bdd | 可观察契约行为 | before-dev | traceable。源仓不生成 .feature。 |
| ponytail | 实现选型 | implement | 包装既有 helper，不平行重写状态机，不引入依赖。 |

## DDD Boundary Review

Status: confirmed

Ubiquitous language: Facade 是既有 helper 的调用包装，不是第二任务状态机。业务副作用指 helper 已经会写的项目文件（task.md、active、index、handoff、identity）。观察开关 `observation.enabled` 只控制是否允许保存观察元数据；关闭不是取消注册。显式项目注册只改变本扩展的授权来源清单。`project_id` 不是绝对路径。完全只读是不落任务文件也不落审计文件；“项目只读但允许用户目录统计”是另一上下文，不能由未确认调用推断。`preview_route` 的 `executed=false` 表示没有执行会保存状态的路由。`resolve` 不是 `ensure`。`audit_status=gap` 不是已采集，也不是业务失败。

Bounded contexts: task.md 事实源仍由 TaskStore 拥有。用户私有 registry／config 属于 Runtime 授权与开关，不回写任务状态。观察事件库不属于本包。HTTP 查询面不在本包。

Invariants and business rules: 开关关闭且项目已显式注册时，适配调用的项目文件与直接 helper 调用相同。本包不写 audit.db／spool。未注册根不被列举或扫描。symlink 根拒绝注册。取消注册不删除项目文件。身份解析不创建 developer 文件。预览不调用 `TaskRouter.route`。不确定是否可落盘时不写。

Core / supporting / generic subdomains: 核心是包装边界、注册授权和开关等价。支撑是结构化 operation／persistence／audit 结果。通用是 JSON 文件与权限位。

Corrections to the grill-with-docs result: none。未完整 grill，没有可订正的访谈结论。

Open conflicts and questions: none。事件存储与宿主适配器留在 R1.2a／R1.2b。

## DDIA Data Design Review

Status: confirmed

Data owner and source of truth: 任务 mode／status／history 仍属 task.md。授权清单属 `SBTD_RUNTIME_HOME/registry.json`。观察开关属同目录 `config.json`，文件缺省等于关闭。本包没有 audit store，不把 registry 当成事件库或第二任务库。

Write / read / async / failure paths: 注册／取消注册／开关是显式确认后的单文件替换。任务写入只转发 helper。读取只打开已注册根。失败的权限拒绝不写文件。helper 失败不追加审计文件，也不由 Facade 回滚 helper 已写内容。无队列、无跨进程缓存。

Consistency model: 单进程读己之写。registry 与 config 用同目录临时文件替换。不宣称跨进程锁。任务一致性仍是 helper 的原子替换。

Idempotency / ordering / retry / deduplication: 同一规范根重复注册返回原 `project_id`，不复制记录。不同 checkout 不因 remote URL 合并。取消不存在的 id 拒绝且不改其他记录。损坏或未知 schema 的 registry 拒绝覆盖。

Schema / migration / backfill / rollback / replay: registry schema_version 1。无 task.md 迁移。回滚注册是取消注册，不删项目。无事件重放。

Observability and repair: 开关开启时 audit_status 为 gap，因为事件库不在本包。不返回已采集。权限拒绝与 helper 失败分开。

Required tests: 开关关闭的业务文件等价、开启时无 audit.db、只读不落盘、未注册与 sibling 诱饵、symlink 拒绝、0600、重复注册、取消不删项目、preview 不调用 route、resolve 不调用 ensure。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-16T17:28:16.272618+08:00 | planned | in-progress | R1.1 facade scope is fixed by PRD and ADR; implementation starts after the failing seam tests | docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md:1377 and docs/adr/0001-v2.1.0-rc.1-r1.0-runtime-decisions.md |
| 2026-10-16T18:05:41.414629+08:00 | in-progress | checking | R1.1 facade tests and related helper tests passed after review fixes | python3 -m unittest discover -s sbtd-runtime/tests (50 ok); tests.test_sbtd_runtime_r1_facade tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_task_state tests.test_sbtd_task_routing tests.test_sbtd_handoff tests.test_sbtd_identity (180 ok); review symlink/key/gap regressions 24 ok |
