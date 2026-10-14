---
schema_version: 1
id: windows-ci-acl-optimization
workflow_mode: strict
mode_source: user
mode_note: 用户明确选择strict用于Windows CI优化及ACL安全原语改动
status: "in-progress"
branch: perf/windows-ci-acl
created_at: '2026-10-14T18:32:31.998550+08:00'
updated_at: "2026-10-14T18:32:34.668168+08:00"
completed_at: null
---
# v2.0.1 Windows CI耗时优化与进程内ACL证明

## 授权与范围

用户明确选择strict，并确认：Windows ACL进程内实现纳入v2.0.1；Windows按4分片，ACL改动完成后再评估；按“Windows实测行覆盖与分支覆盖完全一致、关键用例强制保留、移除清单经用户审阅后生效”去重；Linux/macOS同步评估优化空间。用户已授权以admin权限审批合并PR。未授权发布v2.0.1、移动tag、live同步、清理备份或修改用户本机安装。
未完整grill：目标、约束和取舍已由用户逐项确认，无领域歧义。

## 基线（原生CI，已保存逐例报告）

- 精确head CI38532355204/38538887444：Windows墙钟约56分钟，分片1/2/3为20.6/11.4/55.8分钟，测试总量5172秒/507例；Linux总量2489秒、最慢分片22.9分钟；macOS测试约5分钟。每个job准备步骤仅十几秒。
- 6个用例占Windows耗时59%，同一用例Windows比macOS慢30～60倍。先前诊断：一次恢复1250次PowerShell ACL调用耗时868.9秒，约0.7秒/次。
- `.github/test-weights.json`缺少`test_sbtd_cleanup_upgrade_integration`(1853秒)、`test_sbtd_cleanup_upgrade`(597秒)及Linux`test_sbtd_migration_cleanup_drift`的权重，导致分片严重不均；且只能按整模块分片。
- 507个Windows用例中495个同时在Linux/macOS执行（占Windows耗时99.7%）；最慢用例多为Windows关键验收，单靠去重收益有限。

## 设计与不变量

1. ACL证明改为进程内Win32安全API（ctypes），判定与原PowerShell脚本逐项一致：属主必须是当前用户；DACL每条ACE必须为允许型且主体属于当前用户/SYSTEM/Administrators；NULL DACL、未知ACE类型、无法读取或解析一律失败。按句柄读取并核对与lstat为同一目录对象，不跟随重解析点。创建时设置当前用户为属主及受保护DACL（仅当前用户FullControl，容器/对象继承），只作用于本次新建目录。不引入ACL缓存，不放宽900秒限制，不减少任何检查。原PowerShell脚本移入测试作为差分对照。
2. 分片：Windows改4片；无类级/模块级fixture的模块可按用例分配，带setUpClass/setUpModule的类或模块保持完整；权重由最新原生报告生成，选中范围缺权重时报错。
3. 去重：以ACL改动后的Windows实测覆盖为基准，计算保持行/分支覆盖完全一致的最小集合；`WINDOWS_CASES`、必需原生用例、PowerShell安装器用例及含Windows专属断言的用例强制保留；移除用例仍在Linux/macOS执行。移除清单经用户审阅后生效。
4. 先前计划的独立阶段0测量改为：以两轮已保存基线对比改动后逐例耗时；若某慢用例未明显下降再单独诊断。去重所需的覆盖测量在ACL改动后进行，避免以将被替换的代码路径为基准。

## Book Gate Plan

| Gate | 触发 | 状态 |
|---|---|---|
| DDD | 未完整grill、无新领域规则 | not-needed |
| DDIA | 私有目录所有权与证明语义 | pending：确认按句柄身份绑定、无缓存、失败关闭 |
| Legacy | 既有ACL判定行为 | pending：PowerShell对照差分刻画 |
| Refactoring | 修改生产ACL原语与CI调度 | pending：限定范围，不做无关重构 |
| TDD/BDD | ACL判定与分片行为 | pending：源仓Markdown场景，不建.feature |
| Project validation | 三平台原生CI、耗时对比 | pending |
| Independent security/readability | ACL安全原语 | pending |
| Release readiness | 安装/升级/恢复运行路径 | pending：仅PR交付，不发布 |

## 验收场景

- Given新建私有目录；When在原生Windows创建并校验；Then进程内实现与PowerShell对照结论一致，且无需启动PowerShell。
- Given目录被加入Everyone、Users或Deny ACE、属主不符、继承开启或为重解析点；When校验；Then两种实现均判定失败且不改动目录。
- Given分片计算；When选中范围缺权重或用例重复/遗漏；Then CI失败而非静默分配；各平台分片并集与原范围一致。
- Given去重后Windows范围；When按用例统计覆盖；Then生产代码行/分支覆盖与去重前一致，强制保留用例全部执行通过。
- Given最终head；When三平台CI；Then全部通过，Windows墙钟显著下降，900秒恢复期限不变。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-14T18:32:34.668168+08:00 | planned | in-progress | 用户确认ACL纳入v2.0.1、Windows4分片、覆盖一致去重及strict；开始实现 | 基线CI38532355204/38538887444；诊断run38522065660 |
