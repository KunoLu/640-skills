---
schema_version: 1
id: graft-trail-code-upgrade-eval
workflow_mode: strict
mode_source: user
mode_note: 用户 2026-10-28 明确三个需求统一 strict mode 执行
status: "done"
branch: "main"
created_at: '2026-10-28T17:36:01.819853+08:00'
updated_at: "2026-10-28T18:53:05.542354+08:00"
completed_at: "2026-10-28T18:53:05.542354+08:00"
---
# Graft 0.22.0 → Trail-code 时代升级评估与实施

## 目标

评估 `@nanonets/graft` 0.22.0 → 0.28.0（官方已更名 Trail-code，双发包 `@trailhq/trail-code` / `@nanonets/graft`，graft 命令不变）的可行性；SBTD 只用离线 code map 能力（build + ask/map/skeleton/callers/check/grep/blast），不需要云功能。

阶段 1（本评估，不改运行 pin）：隔离实测 0.28.0 离线行为，产评估报告。
阶段 2（用户确认后）：pin 切换 `graft_runtime.py`（GRAFT_PINNED_VERSION / GRAFT_TARBALL_URL / GRAFT_TARBALL_INTEGRITY）+ `graft-build-policy.json` version，更新受影响测试，真实 build 冒烟。

## 阶段 1 已得证据（/tmp 隔离环境，DO_NOT_TRACK=1）

- 0.28.0 tarball sha512 与 npm registry 一致：`sha512-zto3AJeK5qMdjhZrsrIr0Bq7agySU/aPIgBgokpPXleabiY9l83iHUETec9oeMiiBZM7YRxh4OSDMHlP4sSwBA==`。
- 裸 `graft build . --no-gitignore --no-ignore` 全离线成功，输出仍落 `graft/`（`--dir` 默认 `<repo>/graft` 保留；`.trail/cache` 迁移只发生在 trail init 管理路径），fixture 内未写 `.trail/`/hooks/`.claude/`。
- `graft telemetry` 在 DNT 下：telemetry off、update check off。
- 受管动词 `build/ask/map/skeleton/callers/check/grep/blast` 带现行精确参数（--json/--no-refresh 等）在 fixture 上全部 exit 0 输出 JSON；ask 离线走 structural 模式。
- `graft mcp` 仍暴露 graft_find_code/graft_trace_calls/graft_find_all/graft_file_api/graft_repo_map/graft_check_freshness，与本仓库 MCP 接线一致。

## 范围与边界

分支 `sbtd/strict-graft-trail-code-upgrade`。不切换 trail 包名、不启用 login/workspace/hooks/云同步；保持 `llm:false, cloud:false, wiring 全 false, DNT=1` 边界。ENTRYPOINT 的 Graft 版本行按既有规则留给发布后版本检查同步，本任务不改。完成后按授权开 PR、admin 合入、删分支。未完整调用 grill-with-docs：需求与边界明确，无领域歧义；DDD 门不触发。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-28T17:36:08.469761+08:00 | planned | in-progress | 开始 graft 升级评估（阶段 1） | /tmp/graft-eval 隔离实测完成：tarball integrity 匹配 registry；离线 build 输出 graft/；DNT 下遥测/更新检查 off；7 个受管动词 JSON 契约 exit 0 |
| 2026-10-28T18:52:39.071974+08:00 | in-progress | in-progress | Explicit branch rebinding from "sbtd/strict-graft-trail-code-upgrade" to "main": PR #198 已 squash 合入 main（4093baf），开发分支按授权删除；任务完成记录落在 main | gh pr view 198: MERGED；main 已含 4093baf；本地/远程分支已删 |
| 2026-10-28T18:52:52.303179+08:00 | in-progress | checking | 阶段 2 实施与验证完成，PR #198 CI 全绿待合入 | macOS 全量 701 测试与 main 基线 162 个既有环境失败集合一致、零新增；受管安装→身份钉住→受管 build 真实链路 exit 0；独立 review 两 P3 已闭环 |
| 2026-10-28T18:53:05.542354+08:00 | checking | done | Graft pin 0.28.0 已合入 main | PR #198 tip a4cddbe CI run 40672614333 attempt 1 全绿；squash 合入 4093baf；分支已删 |
