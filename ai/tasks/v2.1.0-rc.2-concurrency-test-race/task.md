---
schema_version: 1
id: v2.1.0-rc.2-concurrency-test-race
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：strict；本会话为唯一 writer 与 git 提交者；不启动子代理、不用 advisor；push 与开 PR 由编排方在 omp 之外执行
status: in-progress
branch: test/v2.1.0-rc.2-concurrency-test-race
created_at: '2026-10-24T21:49:56+08:00'
updated_at: '2026-10-24T21:51:23+08:00'
completed_at: null
---

# rc.2：并发测试时序竞争 strict 测试修复

## 决定

- 「Lord 2026-10-24 21:47 群内裁定（测试修复单开 PR，排在 fix4 前）」：只修 `tests/test_sbtd_task_sync_git.py` 中的 `SyncGitTests.test_concurrent_processes_do_not_lose_successful_events`；先对两个子进程都 `communicate()` 并收齐两个退出码，之后再为退出码为 3 的子进程补记事件。不加 TaskStateError 重试；不改 `sbtd_task_*.py` 或任何其他代码。
- 编排方整理：本会话只创建一个本地提交，不 push、不 amend、不 reset、不 force、不执行 gh、不修改 git 或 omp 全局配置。push 与开 PR 由编排方在 omp 之外执行。
- 所有新记录时间使用 Asia/Shanghai，由 `TZ=Asia/Shanghai date -Iseconds` 实际获取，不倒填群内决定时间。

## 范围与边界

- 只修改目标测试中 `successful = []` 起的收集循环，并新建本 `task.md`。第一个循环依次 `communicate(timeout=30)`，断言退出码属于 `(0, 3)`，收集 `(writer, returncode)`；两个进程都结束后，再计算 successful，并为退出码为 3 的 writer 调用 `TaskSync(self.store).record("sync", step="并发", writer=writer, confirmed=True)`。
- 保留 `self.assertTrue(successful)` 及后续断言，不改子进程脚本、其他测试或生产代码，不加重试、不加 sleep。
- 本 task.md 手写，未经 TaskStore 写入。编排方整理：`TaskStore._catalog()` 被 3 个旧 task.md 阻塞：`ai/tasks/v2.1.0-rc.1-csv-reasoning-tokens/task.md`、`ai/tasks/v2.1.0-rc.1-r1.3-stats-api/task.md`、`ai/tasks/v2.1.0-rc.2-r2.1b-renderer/task.md`。沿用已报告事实，不重跑失败调用，不改写这些旧文件。
- 仅用仓库 `sbtd_task_state.TaskDocument.parse` 只读解析本 task，不调用 TaskStore 写入，不写 active／index／handoff／ignore／身份，不承诺自动恢复。
- 未完整调用 grill-with-docs：根因、修复方案、范围与验收已明确，无领域歧义；不重复澄清。不启动子代理、task／reviewer，不用 advisor；本会话自检不等于独立审查。
- 本提交状态保持 `in-progress`，`completed_at: null`；仅记录 `planned → in-progress` 及可选的 `in-progress → in-progress`，不记录 checking／done 迁移。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮适用性与结果 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求确认前 | not-needed；未完整 grill，修复边界明确 |
| book-ddia-data-design | 持久化、schema、迁移或跨进程机制设计前 | not-needed；不设计或修改 TaskStore 持久化及锁机制，仅调整测试等待顺序 |
| book-legacy-change-safety | 既有行为 bug，测试修改前 | characterized；已报告 CI 失败与原循环建立行为证据，保留子进程脚本、退出码检查及最终事件断言，以目标单测和整文件作为安全网，无需新增 seam |
| book-refactoring-pass | 既有生产代码编辑前 | not-needed；不改生产代码，无额外重构 |
| book-release-readiness | 运行时或部署变化，正式验证后 | not-needed；仅测试与任务记录，不宣称部署或发布就绪 |
| project-validation | 修改后本地自检 | 按约定原生命令运行目标单测、整文件各一次，并核对 diff、禁词与 TaskDocument.parse；正式验证由编排方在本提交上运行 |

## 根因与复现

- 编排方整理：该测试由 #169（`6f79e9d`）加入。GitHub Actions run `40094994851` attempt 1，job `linux-shards (2)`（job id `120875259692`，Python 3.12.10），于 2026-10-24 20:55:12 +08:00 在 `tests/test_sbtd_task_sync_git.py:228` 报 `sbtd_task_state.TaskStateError: task data changed before writing`；异常由 `TaskStore._write`（`sbtd_task_state.py:366`）抛出。该 job 输出 `Ran 810 tests`、`FAILED (errors=1, skipped=35)`。
- 根因（Reviewy 同意）：测试启动甲、乙两个子进程；原 for 循环先 `communicate()` 甲，甲退出 3 时立即在测试进程补记甲的事件，尚未等待乙。若乙仍在写入，测试进程的写入会被 `_write` 的过期内容检查正确拒绝。TaskStore 的锁按设计工作，问题在测试等待顺序。
- 本会话源代码核对：原循环在 `process.returncode != 0` 分支直接调用 record，而下一个进程的 communicate 尚未执行。修复把所有子进程结束作为补记的前置条件，不吞异常、不重试写入。
- 编排方提供的修复前本地证据：main `3c49524`，Python 3.13.5 venv `/home/box/.local/venvs/project-validation`，nproc 8；CI 为 3.12.10。本地未复现：单测 unittest 50/50 通过（每次 `Ran 1 test` OK，`/workspace/640-concurrency-repro/single.csv`）；整文件 20/20 通过（每次 `Ran 14 tests` OK，`/workspace/640-concurrency-repro/file.csv`）；CPU 负载下单测 100/100 通过（`/workspace/640-concurrency-repro/stress-single.csv`）。这些为既有证据，不计为本会话执行。
- 既有复现脚本：`/workspace/640-concurrency-repro/run.sh`；CI 日志：`/workspace/640-concurrency-repro/ci-job-120875259692.log`；逐次日志：`/workspace/640-concurrency-repro/verify2/`。本会话不重复修复前压力复现，不添加其他测试或临时脚本。

## 验证与剩余边界

- 入口已核对：HEAD `3c49524fec9561e6feacce40638be11ecea60dc7`，分支 `test/v2.1.0-rc.2-concurrency-test-race`，初始工作区干净；授权父目录与测试文件非 symlink，新 task 目录不存在，授权文件未被 ignore。
- 本地自检命令：`/home/box/.local/venvs/project-validation/bin/python3 -B -m unittest tests.test_sbtd_task_sync_git.SyncGitTests.test_concurrent_processes_do_not_lose_successful_events`；`/home/box/.local/venvs/project-validation/bin/python3 -B -m unittest tests.test_sbtd_task_sync_git`。各运行一次，分别输出 `Ran 1 test in 0.558s` / `OK`、`Ran 14 tests in 7.016s` / `OK`；目标测试实际启动两个子进程并核对落盘事件。这是提交前 dirty worktree 自检，非正式验证。
- 提交前另核对两个授权文件的 diff、`git diff --check`、新增行禁词零命中；只读解析应输出 `in-progress False <N> None`。手写代码可读性检查关注两个循环的阶段边界及原有断言保留，不夹带重构。
- 正式验证（50 次独立进程单测、整文件、89 项任务测试）由编排方在本提交上运行，之后由另一 omp 会话追加证据并转 checking。本会话不执行这些正式验证，不宣称 CI、独立审查、合入或发布通过。
- BDD：skipped（仅测试时序调整，无用户可见行为变化，无 .feature 变动）；API Contract／Cross-repo context：not-needed；Mock Strategy：none。rtk：not-needed（按约定直接运行原生命令）。不运行额外 lint／formatter／全量 CI，不生成额外报告文件；本轮仅本地自检，正式报告不在本会话范围。
- 旧 task 的 catalog 阻塞未修复；本地单次通过不能证明所有调度下无竞争，且 Python 环境与失败 CI 不同。测试补记的等待顺序修复不改变 TaskStore 并发语义。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | 产出 | 会话文件 |
|---|---|---|---|---|---|
| 1 | ping（2026-10-24 21:48:25 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `~/.omp/agent/sessions/--workspace-640-skills-concurrency-test-fix--/2026-10-24T13-48-25-975Z_01a16e2b-7bf7-7005-b0db-1af5d0fdf610.jsonl` |
| 2 | main s1（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告 | 测试修复与本 task，一个本地提交 | `~/.omp/logs/640-concurrency-test-fix/s1/2026-10-24T13-49-20-644Z_01a16e2c-5184-706a-ad6c-aa91e4b913dc.jsonl` |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-24T21:49:56+08:00 | planned | in-progress | 编排方整理，主会话记录：建立手写 strict 任务，开始测试时序修复与本地自检。 | 已核对 HEAD、分支、干净工作区及授权路径安全；按 Lord 21:47 裁定仅改目标测试与本 task；未经 TaskStore 写入；at 为实际记录时间。 |
| 2026-10-24T21:51:23+08:00 | in-progress | in-progress | 主会话记录：完成最小测试修改与两项本地自检，非正式验证。 | 目标单测 1 项 OK（0.558s），整文件 14 项 OK（7.016s）；首次只读解析输出 in-progress False 1 None。本事件追加后提交前再次解析；两个循环分别收齐退出码和补记事件，原子进程脚本及最终断言未改，不引入重试或 sleep。正式验证由编排方在本提交上运行。 |
