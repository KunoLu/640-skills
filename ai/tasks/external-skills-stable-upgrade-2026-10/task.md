---
schema_version: 1
id: external-skills-stable-upgrade-2026-10
workflow_mode: strict
mode_source: user
mode_note: 用户 2026-10-28 明确三个需求统一 strict mode 执行
status: "in-progress"
branch: sbtd/strict-external-skills-stable-upgrade
created_at: '2026-10-28T16:52:56.572696+08:00'
updated_at: "2026-10-28T16:53:03.332900+08:00"
completed_at: null
---
# 外部 Skills stable 集升级（2026-10）

## 目标

将 `sbtd-workflow-onboard/assets/external-skills/stable/` 的 6 个上游仓库 pin 升级到各自主线最新 HEAD，stable-set 从 `2026-09-14.6` 升到 `2026-10-28.1`：

| 仓库 | pinned | HEAD |
|---|---|---|
| mattpocock/skills | 3cca18b | 59db609 |
| pbakaus/impeccable | cb56ed6 | 3e3a917 |
| nextlevelbuilder/ui-ux-pro-max-skill | 7f69fed | 28b3b8d |
| shadcn-ui/ui | 2b3e6d4 | 96da9cc |
| DietrichGebert/ponytail | 356918e | 09c434a |
| ayghri/i-have-adhd | 4092de0 | 1ecea19 |

## 流程

1. 逐仓库 diff 审查受管子路径变化与许可证。
2. `promote-external-skills-stable` 逐仓库晋升（整组、事务、全集合校验）。
3. strict-stable 隔离安装验证 19/19。
4. 全量测试 + ui-ux-pro-max 可独立运行子集。
5. README×2／automation prompt／CHANGELOG×2 维护判断。

## 范围与边界

分支 `sbtd/strict-external-skills-stable-upgrade`。不 sync 到本机生效路径。完成后按授权开 PR、admin 合入、删分支。未完整调用 grill-with-docs：需求与验收明确（有更新则升级），无领域歧义；DDD 门不触发。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-28T16:53:03.332900+08:00 | planned | in-progress | 开始外部 skills stable 升级 | 6 个上游仓库 HEAD 经 git ls-remote 实测均超前于 manifest pin；当前 stable 19/19 摘要在本机通过（基线干净） |
