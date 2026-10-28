---
schema_version: 1
id: external-skills-stable-upgrade-2026-10
workflow_mode: strict
mode_source: user
mode_note: 用户 2026-10-28 明确三个需求统一 strict mode 执行
status: "done"
branch: "main"
created_at: '2026-10-28T16:52:56.572696+08:00'
updated_at: "2026-10-28T17:34:36.303979+08:00"
completed_at: "2026-10-28T17:34:36.303979+08:00"
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
| 2026-10-28T17:33:10.380029+08:00 | in-progress | in-progress | Explicit branch rebinding from "sbtd/strict-external-skills-stable-upgrade" to "main": PR #197 已 squash 合入 main，开发分支按授权删除；任务完成记录落在 main | gh pr merge 197 --admin --squash 成功；远程分支已删除；main 已 pull |
| 2026-10-28T17:34:23.147060+08:00 | in-progress | checking | 晋升、验证与 review 完成，PR #197 CI 全绿待合入 | 19/19 摘要一致；隔离安装 committed；macOS 全量零新增失败；pin 断言更新后 143/143；ui-ux-pro-max 138 通过 4 个 M15 同类 error；独立 review 无 findings |
| 2026-10-28T17:34:36.303979+08:00 | checking | done | stable 集 2026-10-28.1 已合入 main | PR #197 tip c0e8516 CI run 40662259628 attempt 1 全绿；squash 合入 4eb8b2a；本地/远程分支已删 |
