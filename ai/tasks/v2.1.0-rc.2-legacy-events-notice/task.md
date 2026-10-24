---
schema_version: 1
id: v2.1.0-rc.2-legacy-events-notice
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：strict；本会话为唯一 writer 与 git 提交者；不启动子代理、不用 advisor；push 与开 PR 由编排方在 omp 之外执行
status: checking
branch: fix/v2.1.0-rc.2-legacy-events-notice
created_at: '2026-10-24T22:53:24+08:00'
updated_at: '2026-10-24T23:05:33+08:00'
completed_at: null
---

# rc.2 fix4：旧格式事件放宽口径 strict 实现修复

## 决定

- 编排方整理：Lord 2026-10-24 22:48 群内指派 fix4：按 PRD `docs/prd/sbtd-workflow-v2-task-status-sync.md:65`（PR #170 合入，`3c49524`）实现旧格式事件放宽口径，使 `TaskStore._catalog()` 不再被 3 个旧 task.md 阻塞，范围不扩大。
- 已读取 PRD 第 55–66 行。无基线且每行五列均完整时，schema／时间戳不合规也归为旧格式，按 frontmatter status 判断当前状态；提示「旧格式事件，不追溯」，不阻塞，不追溯改写。五列不完整、frontmatter、表结构和基线后的错误仍报错。
- 编排方整理：单次 parse 一个旧文件恰好提示一次；单次 catalog 多个旧文件总共提示一次；保持其他调用方行为与返回值，不改 sync notes。
- 本会话恰好一个本地提交；不 push、不 amend、不 reset、不 force、不执行 gh，不改 git／omp 全局配置。正式验证由编排方在该提交上运行，之后另一 omp 会话追加证据并转 checking；done 在 Reviewy CLEAN 后另行提交。
- 新记录时间一律 Asia/Shanghai，以 `TZ=Asia/Shanghai date -Iseconds` 实际获取，事件带 `+08:00`，不倒填。

## 范围与边界

- 生产修改仅限 `sbtd-workflow-onboard/scripts/sbtd_task_document.py` 与 `sbtd-workflow-onboard/scripts/sbtd_task_state.py`（后者仅为 catalog 提示去重）；新增 `tests/test_sbtd_task_legacy_events_notice.py` 和本 task。
- 现有 `tests/test_sbtd_task_status_sync.py` 中拒绝完整五列未知状态／非法日期／非法转换的旧断言与 PRD :65 冲突，按允许的最小测试调整删除；保留空格、frontmatter 与基线严格校验安全网，新增测试覆盖新口径。
- 不改 schema／contract／openapi／templates、版本号、CHANGELOG、plan.md、3 个旧 task 或任何其他已有 task；不改并发测试。
- 本 task.md 手写，未经 TaskStore 写入；仅只读 parse／catalog。不写 active／index／handoff／ignore／身份，不承诺自动恢复。不启动子代理、task／reviewer，不用 advisor；自检不是独立复核。
- 未完整调用 grill-with-docs：PRD、修复边界与验收已明确，无领域歧义，不重复澄清。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮适用性与结果 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求前 | not-needed；未完整 grill，沿用明确 PRD |
| book-ddia-data-design | 持久化事件读取语义，设计前 | confirmed；旧文件是唯一事实，读取不写；无基线仅放宽完整五列的语义，基线后严格；不改变 schema、写入、锁、迁移或恢复机制 |
| book-legacy-change-safety | 既有解析 bug，生产修改前 | characterized；修复前日志、源码与新增回归建立证据；parse／catalog、畸形行、基线后严格校验、bytes 不变构成安全网，无需 seam |
| book-refactoring-pass | 既有生产代码，修改前 | proceed（normal）；no refactor needed，删除旧窄放宽分支，以默认 True 的关键字参数沿现有读取链将提示控制传到 catalog |
| book-release-readiness | 运行时解析变化，本地测试后 | blocked（正式发布门禁）；编排方整理：正式验证已在 ea4c161 上通过，CI、Reviewy 尚未进行，不冒充 ready |
| project-validation | 实现后 | s1 为提交前 dirty worktree 自检；编排方整理：ea4c161 上新增 6 tests、task 8 模块 136 tests、catalog、旧文件 sha256、并发 10/10 与 diff 检查通过，详见「验证与剩余边界」 |

### 行为场景与安全网

- Given 无基线且事件五列完整，含 verifying、in_progress（可带微秒时间戳）或无效日期等不符合当前校验的行；When parse；Then legacy_events=True、events=()，状态取 frontmatter，stderr 一次提示，原 bytes 不变。单纯微秒时间戳已被当前校验接受，不新增格式限制。
- Given 多个旧任务和一个当前任务；When 一次只读 catalog；Then 返回全部记录，仅一次提示，所有文件 bytes 不变；重复 catalog 每次独立计数。
- Given 任意一行少列、多列或空白列，即使邻接完整旧行；When parse／catalog；Then 普通解析错误，不掩盖畸形行。
- Given 当前格式、错误 frontmatter／表结构或基线文件；When parse；Then 当前格式无提示，结构错误仍失败，基线内不追溯、基线后严格校验。
- BDD traceability 以 PRD「旧格式事件规则」与新增 unittest 承载；按本轮文件边界不增加 .feature 或测试框架。场景中文、Given／When／Then 英文。

## 背景与并发复现

- 编排方整理：main `2e5ddb5` 的 `_catalog()` 抛 `TaskStateError: task state event fails the bundled stateEvent schema`，阻塞文件为 `ai/tasks/v2.1.0-rc.1-csv-reasoning-tokens/task.md`（verifying）、`ai/tasks/v2.1.0-rc.1-r1.3-stats-api/task.md`（verifying）、`ai/tasks/v2.1.0-rc.2-r2.1b-renderer/task.md`（in_progress、微秒时间戳）。既有 `_validate_event(..., legacy=True)` 仅放宽历史 in-progress → done。
- 已读取 `/workspace/640-fix4-verify/catalog-before.log`：失败前有 5 次「旧格式事件，不追溯」，随后 `CATALOG_FAIL TaskStateError task state event fails the bundled stateEvent schema`。沿用已报告事实，不重跑失败探针。
- 编排方整理，Lord 2026-10-24 21:25 裁定：main `3c49524`，unittest，Python 3.13.5（venv `~/.local/venvs/project-validation`），nproc 8；并发单测独立运行 50/50 通过（`/workspace/640-concurrency-repro/single.csv`），整文件 20/20 通过（每次 Ran 14 tests OK，`/workspace/640-concurrency-repro/file.csv`），CPU 负载下单测 100/100 通过（`/workspace/640-concurrency-repro/stress-single.csv`），未复现。
- 编排方整理：命令见 `/workspace/640-concurrency-repro/run.sh`，先 compileall -q，再 `$PY -B -m unittest -v tests.test_sbtd_task_sync_git.SyncGitTests.test_concurrent_processes_do_not_lose_successful_events` ×50、`$PY -B -m unittest -v tests.test_sbtd_task_sync_git` ×20；CPU 具体加压命令未保存，不可考，只有结果 csv。上述为既有证据，不计本会话执行。
- 编排方整理：CI run `40094994851`、linux-shards (2)、`:228` 失败是测试自身等待顺序竞争，已由 #171（合入 `2e5ddb5`）修复。fix4 不改该测试，不增加重试或并发机制。

## 验证与剩余边界

- 入口核对 HEAD `2e5ddb5f588cf250938bc2802fffceb202e984f0`、分支 `fix/v2.1.0-rc.2-legacy-events-notice`，初始工作区干净；授权路径及父级无 symlink、新文件不存在、授权文件无 ignore 匹配。
- LSP references 实际返回 No language server found for this action；已用源码调用点检索补充影响分析。parse 的默认提示行为保留；catalog 经 _records／_read 控制提示；迁移、sync、updated 及独立 _records 调用仍使用默认值。
- 新增回归 red：`python3 -B -m unittest tests.test_sbtd_task_legacy_events_notice` 首次 Ran 6 tests，FAILED（failures=2, errors=6，2.661s）；schema／日期错误证明旧窄放宽不满足规则。另有 2 个失败来自测试错误地把单纯微秒时间戳当作非法；核对实际校验后改用带 in_progress 的微秒旧行，不改生产时间戳规则。
- 实现后同一新增回归命令 Ran 6 tests in 2.321s，OK；覆盖未知状态、微秒旧行、无效日期、历史 in-progress → done、混合行、提示次数、重复 catalog、bytes 不变、4／6 列及每列空白、frontmatter／表结构和基线严格边界。
- `python3 -B -m unittest tests.test_sbtd_task_document tests.test_sbtd_task_recovery tests.test_sbtd_task_routing tests.test_sbtd_task_schema tests.test_sbtd_task_state tests.test_sbtd_task_status_sync tests.test_sbtd_task_sync_git`：Ran 130 tests in 51.168s，OK。仅删除 status-sync 中与放宽口径冲突的两个输入和一个旧拒绝测试；未改并发测试。
- `python3 -B /workspace/640-fix4-verify/catalog_probe.py`：exit 0，CATALOG_OK 47；捕获 stderr 为一行「旧格式事件，不追溯」，计数 1。`sha256sum -c /workspace/640-fix4-verify/legacy-sha256-before.txt`：3 项 OK；三个旧 task 的 git status 无变化。
- 本机 `python3 --version` 为 Python 3.13.5。新 task 首次只读解析输出 `in-progress False 1 None`；本次追加自检事件后，提交前再次执行解析与范围／禁词／diff 检查。
- Ponytail Review：Lean already，无新增依赖、全局去重状态或抽象；Code Readability Review 自检通过，完整行检查与语义放宽分离，默认提示保留，catalog 独立汇总。没有独立 reviewer，不把本会话自检称为独立复核。
- BDD：traceable；PRD :59–65 与本 task 中文行为场景对应新增 unittest，无新 .feature／runner。s1 自检的 Evidence Source：developer-local；Source Revision：dirty；Environment Alignment：unverified（未对齐正式 CI）；Evidence Publication：local-only；Final Test Report／Run Summary MD：not-needed（s1 仅本地自检）。s1 结束时本 task 为 in-progress、completed_at null。
- rtk：not-needed，按编排方要求原生命令；Cross-repo context／API Contract：not-needed；Mock Strategy：none。不运行 Web／Mobile E2E、全量 CI 或额外 lint／formatter，不创建正式报告；无 UI／服务变化且本轮正式验证由编排方负责。
- 不宣称独立审查、CI、合入、部署或发布通过；回退仅涉及本提交的解析逻辑与测试，历史 task bytes 不应改变。

### 编排方正式验证补记（checking s2）

- 编排方整理：正式验证由编排方在 fix4 提交 `ea4c161903a37ef9a1f20fb33511b185ba126be3`（`ea4c161`）上运行，日志目录 `/workspace/640-fix4-verify/`；`head.txt` 记录该 SHA，`python.txt` 记录 Python 3.13.5、nproc 8。本会话读取核对日志，不将这些运行计为本会话执行。
- 编排方整理：`python3 -B -m unittest -v tests.test_sbtd_task_legacy_events_notice`：Ran 6 tests，OK（`new-tests.log`）；`python3 -B -m unittest` 覆盖全部 `tests/test_sbtd_task*.py`，共 8 个模块（含新文件）：Ran 136 tests，OK（`task-tests.log`）。
- 编排方整理：`python3 -B /workspace/640-fix4-verify/catalog_probe.py`：`CATALOG_OK 47`，其中 13 个记录 legacy_events=True（`catalog-after.stdout`），stderr 中「旧格式事件，不追溯」恰好 1 次（`catalog-after.stderr`）。修复前为 `CATALOG_FAIL TaskStateError task state event fails the bundled stateEvent schema`，失败前提示 5 次（`catalog-before.log`）；保留失败证据，未重跑。
- 编排方整理：`legacy-sha256-before.txt`／`legacy-sha256-after.txt` 中 3 个旧 task.md 的 sha256 前后一致：csv-reasoning-tokens `20c911c7d63dbf2178f7abc05971aea15e6792d27b13e2d1ad4b9b6139bb6fec`；r1.3-stats-api `fe74daed7d722493c76a342c1321e0b977b02e79569f084fff72a641afebdfec`；r2.1b-renderer `908f0b7594cf9300a3ef8582ad1522785832083b76d193ed2b4b8246b462c017`。编排方整理：`git diff 2e5ddb5 HEAD` 对这 3 个目录为空。
- 编排方整理：并发测试 `tests.test_sbtd_task_sync_git.SyncGitTests.test_concurrent_processes_do_not_lose_successful_events` 独立进程 10/10 通过，每次 `Ran 1 test`、OK（`concurrency-10x.csv`、`concurrency-run1.log` 至 `concurrency-run10.log`）。
- 编排方整理：`git diff --check 2e5ddb5 HEAD` 干净（`diff-check.log`）；新增行禁词 0 命中；task.md 无本机 HOME 绝对路径。
- 编排方整理：本轮仅手写补记本 task.md 并转 checking，未经 TaskStore 写入；updated_at 与追加事件使用同一实际 Asia/Shanghai 时间，completed_at 保持 null。模型记录 main s1 的 `23／62` 来自编排方按 jsonl 统计（assistant 消息 23、toolCall 62）。
- 编排方整理：Reviewy 与 CI 尚未进行；done 在 Reviewy CLEAN 后另行提交。本轮不写 done、不 push，不宣称正式发布门禁通过；上述正式验证绑定 ea4c161，不冒充本轮文档提交的 CI 或独立审查结果。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | 产出 | 会话文件 |
|---|---|---|---|---|---|
| 1 | ping（2026-10-24 22:51:03 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `~/.omp/agent/sessions/--workspace-640-skills-fix4--/2026-10-24T14-51-04-596Z_01a16e64-d614-770e-8cf6-56a462eae4d8.jsonl` |
| 2 | main s1 | openai-codex/gpt-6-astra（high） | 23／62 | fix4 实现、测试与本 task，一个本地提交 | `~/.omp/logs/640-fix4/s1/2026-10-24T14-52-27-361Z_01a16e66-1961-775f-88b8-46c936ee8b26.jsonl` |
| 3 | checking s2（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告 | 补记正式验证与 in-progress → checking，一个本地提交 | `~/.omp/logs/640-fix4/s2/2026-10-24T15-05-03-619Z_01a16e71-a383-7234-8ae4-1578b2ac9ef2.jsonl` |

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-24T22:53:24+08:00 | planned | in-progress | 编排方整理：建立手写 strict 任务，开始 fix4 实现与本地自检。 | HEAD、分支、工作区及路径安全已核对；PRD :55–66 与修复前 catalog 失败日志已读；未经 TaskStore 写入；at 为实际记录时间。 |
| 2026-10-24T22:57:38+08:00 | in-progress | in-progress | 编排方整理：完成 fix4 实现、测试与本地自检，非正式验证。 | 新增 6 tests OK；指定 7 模块 130 tests OK；catalog CATALOG_OK 47，stderr 提示 1 次；旧文件 sha256 3 项 OK 且 git 无变化；首次 task 解析 in-progress False 1 None，本事件后提交前再次解析。正式验证由编排方在本提交上运行；未经 TaskStore 写入。 |
| 2026-10-24T23:05:33+08:00 | in-progress | checking | 编排方整理：正式验证在 fix4 提交 ea4c161 上通过，送审（Reviewy）与 CI。 | SHA ea4c161903a37ef9a1f20fb33511b185ba126be3；新测试 6 OK；task 8 模块 136 OK；catalog 47 OK 提示 1 次；3 旧文件 sha256 不变；并发 10/10；diff --check 干净；日志 /workspace/640-fix4-verify/；手写，未经 TaskStore 写入。 |
