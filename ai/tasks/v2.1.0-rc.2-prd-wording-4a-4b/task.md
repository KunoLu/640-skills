---
schema_version: 1
id: v2.1.0-rc.2-prd-wording-4a-4b
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：本轮采用 strict，主会话为两个授权文件唯一 writer 与验证 controller；不启动子代理、不使用 advisor；提交、推送与开 PR 由编排方执行。
status: checking
branch: docs/v2.1.0-rc.2-prd-wording-4a-4b
created_at: '2026-10-26T00:27:49+08:00'
updated_at: '2026-10-26T07:41:24+08:00'
completed_at: null
---

# rc.2：PRD 措辞 4a＋4b 定稿

## 决定

- 用户 2026-10-25 23:15 群内确认（4a、4b 按 Lord 推荐：只改措辞，不改代码，文档写明现状），Lord 记录。
- 用户 2026-10-26 07:35 群内确认（同意 4b 按代码事实改写），Lord 记录。确认的是改写后的 4b 版本；PRD 中 4b 行的归因开头原样为「   - 用户 2026-10-26 07:35 群内确认（同意 4b 按代码事实改写），Lord 记录：」。用户已确认改写版，提交、推送与开 PR 由编排方执行。
- Lord 2026-10-26 群内裁定（分钟不可考）：4a 追加句缩短；4b 去掉未实际运行检查却断言检查结果的措辞，按代码事实改写；skill 三处「合法时间戳」差异不进本 PR；task.md 对已删除临时脚本的引用改为说明脚本已删除、结果文件保留。
- 更正记录（编排方整理）：Lord 推荐 4b 时说「JSON 形式对应工具自己写入的 done 事件」，该说法未经核实。`sbtd-workflow-onboard/scripts/sbtd_task_sync.py:350-409` 的 `check_finish_commit` 只校验、不写入；按 `clean_sha` 的仓库文本检索，源码仅见该函数与 `tests/test_sbtd_task_sync_git.py:304`、`:354` 的测试手工构造，另有 `sbtd-workflow-onboard/templates/skills/sbtd-task/references/state.md:52` 文档说明，未找到写入此类 JSON done 事件的工具。已按代码事实更正；草稿阶段使用文本检索工具，未把它记作执行过 `git grep -n clean_sha`。
- 未完整调用 grill-with-docs：两处文本、范围与验收明确，可直接核对代码，无新增领域歧义。

## 范围与边界

只改两个文件：`docs/prd/sbtd-workflow-v2-task-status-sync.md` 原 :65 行末追加一句、原 :79 之后新插一行；新建 `ai/tasks/v2.1.0-rc.2-prd-wording-4a-4b/task.md`。PRD 原 :65 内容与 :79 整行逐字节保留；4a 仍在同一行，不加空格或换行，沿用 #179 ebc0719 的行末追加方式。

```diff
# :65 原行逐字节保留，以下内容追加在原行末尾
+用户 2026-10-25 23:15 群内确认（4a 按 Lord 推荐：只改措辞，不改代码），Lord 记录：上述「合法时间戳」按现行代码指——`at` 末尾的 `Z` 换成 `+00:00` 后须能被 `datetime.fromisoformat` 解析，且不以 `Z` 结尾时末两位数字不大于 59；无基线的旧格式判定不要求时区，当前格式事件行仍须符合内置 schema。
# :79 原行逐字节保留，以下整行插在其后
+   - 用户 2026-10-26 07:35 群内确认（同意 4b 按代码事实改写），Lord 记录：`check_finish_commit` 校验收尾提交时要求证据为 JSON 形式 `{"clean_sha": "<收尾父提交完整 SHA>", "ci_run": "<CI run 标识>"}`；现行手写收尾提交用文字证据，只含 CLEAN 对应的 SHA 和 CI run，内容仍符合上一条。
```

草稿阶段：Python 按字节读取 `/workspace/640-prd-wording-verify/append-4a.txt` 与 `insert-4b.txt`，计算补丁后交编辑工具落盘。本轮定稿：Python 按字节读取 `/workspace/640-prd-wording-verify/insert-4b-final.txt`，计算原 :80 整行替换后交编辑工具落盘；冒号之后正文、当前 :65、:79 及其余 PRD 字节不变，不手抄、不自行改句。

不改代码、契约、测试、plan.md、skill 文档（含 REFERENCE.md、AGENTS.project.md、state.md）；不动 `ai/tasks/v2.1.0-rc.2-contract-scope-wording/task.md` 中「Lord 2026-10-25 21:34 群内裁定」那一行，不动 #179、#183、#184 等历史 task.md。不安装依赖、不改全局配置、不提交或操作暂存区、不推送。沿用参考 task 的手写记录，不调用 TaskStore 写入，不写 active／handoff／ignore／身份，不承诺 TaskStore 自动恢复。临时文件仅放 `/tmp`；只列会话目录文件名，不读取 jsonl 内容、不输出环境变量值。

代码事实基于 origin/main `9fb137beef46b8411975c31cdae969925075687b`，逐项复核行号无偏差：

- `sbtd-workflow-onboard/scripts/sbtd_project.py:515-538`：`validate_task_timestamps` 将末尾 `Z` 换成 `+00:00` 后调用 `datetime.fromisoformat`；不以 `Z` 结尾时，末两位数字大于 59 抛出 `TaskDataError`。
- `sbtd-workflow-onboard/scripts/sbtd_task_document.py:231-245`：无基线时五列须非空；不符合 stateEvent schema 记为旧格式；`at` 不为 `unknown` 时调用 `validate_task_timestamps`；旧格式向 stderr 输出「旧格式事件，不追溯」。
- `sbtd-workflow-onboard/templates/skills/sbtd-task/references/task-data.schema.json:13-17`：timestamp pattern 要求 `T` 分隔与 `Z` 或 `±HH:MM` 时区；当前格式事件仍须符合 schema。
- `sbtd-workflow-onboard/scripts/sbtd_task_sync.py:383-391`：evidence 须能 `json.loads` 为恰含 `clean_sha`、`ci_run` 两键的对象；`clean_sha` 等于父提交，`ci_run` 为非空字符串。
- 读代码推断，未实际运行：#183、#184 的收尾提交使用文字 evidence（对应历史 task 的 :126、:102），按 `sbtd_task_sync.py:383-385` 会在 `json.loads` 处失败，因而过不了 `check_finish_commit`；未对这两个历史收尾提交运行该检查。
- 已知差异只记录、不在本 PR 处理：`sbtd-workflow-onboard/REFERENCE.md:29`、`sbtd-workflow-onboard/templates/agents/AGENTS.project.md:35`、`sbtd-workflow-onboard/templates/skills/sbtd-task/references/state.md:38` 仍写「合法时间戳」，是否另开 PR 由用户之后再定；`state.md:52` 已写明 JSON 格式。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮判定与证据 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求前 | not-needed；未完整 grill，仅核实既有实现措辞 |
| book-ddia-data-design | schema／迁移／持久化机制设计前 | not-needed；不改 schema 或机制，沿用 task 格式 |
| book-legacy-change-safety | 既有行为修改前 | not-needed；不改行为，以基线字节比较保护原文 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；已读取适用边界，无生产代码修改 |
| book-release-readiness | 运行时／部署变化，验证后 | not-needed；无运行时、部署或发布变化 |
| gherkin-bdd／TDD | 行为、场景或状态机制变更前 | not-needed；仅澄清现状，不改行为、持久场景或机制 |
| project-validation | 文档落盘后 | 适用；精确字节、实测解析、八模块回归、task 解析与文字扫描 |
| Code Readability Review／独立 review | check | not-needed；无手写代码或测试修改，单一文档与任务记录范围，不触发独立 review；主会话自核不冒充独立审查，不声明 strict 全流程或发布完成 |

## 验证与剩余边界

### 草稿阶段（保留历史结果）

- 入口 `pwd && git rev-parse --show-toplevel --abbrev-ref HEAD && git rev-parse origin/main && git status --short --untracked-files=all`：exit 0，根与分支匹配，工作树干净；另查 HEAD，与 origin/main 同为 `9fb137beef46b8411975c31cdae969925075687b`。
- 草稿阶段准备验证：临时脚本，已删除，结果文件保留；原记录 exit 0，两路径及父路径无 symlink／逃逸，新 task 原先不存在，PRD 原文等于 origin/main；内部 `git check-ignore --no-index <两个授权路径>` exit 1、stdout／stderr 空，无命中。本轮另行复核路径与 ignore 安全，不以已删除脚本作为可复现证据。
- 草稿阶段事件时间由真实 `TZ=Asia/Shanghai date +%Y-%m-%dT%H:%M:%S+08:00` 取得，exit 0；当时 created_at、updated_at 与唯一事件时间相同，completed_at=null；当时验证后未追加事件，保持 in-progress。
- 草稿阶段 smoke：临时脚本，已删除，结果文件保留于 `/tmp/prd-wording-smoke-results.json`；exit 0，Python 3.13.5；逐个真实调用 `validate_task_timestamps({'updated_at': v}, 'x')`，结果如下。脚本捕获 `TaskDataError` 后继续，表中异常不代表脚本失败。

| v | 结果 |
|---|---|
| `2026-10-25T23:15:00+08:00` | 通过 |
| `2026-10-25T23:15:00Z` | 通过 |
| `2026-10-25T23:15:00` | 通过 |
| `2026-10-25T23:15:00+08:60` | TaskDataError |
| `2026-10-25 23:15:00+08:00` | 通过 |
| `2026-10-25T23:15:00+0800` | 通过 |
| `2026-02-30T00:00:00+08:00` | TaskDataError |
| `2026-10-25T23:15:00.123+08:00` | 通过 |

- 草稿阶段同一 smoke 使用临时 task 文本构造无基线、`at=2026-10-25T23:15:00`、五列非空场景，以 `TaskDocument.parse` 实测；临时脚本与临时 task 文本已删除，结果文件保留于 `/tmp/prd-wording-smoke-results.json`。输出 `legacy_parse in-progress True 0 False`（status／legacy_events／events 数／has_baseline），解析 stderr 精确为 `旧格式事件，不追溯\n`。该 stderr 在脚本中捕获并打印，脚本自身 stderr 空。
- `.github/workflows/validation.yml:38,85,114,173,218,255,283,310` 的 CI Python 为 3.12.10；3.12 上未实测，不以本地结果代替 CI。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B /workspace/640-prd-wording-verify/expected.py`：exit 0，`prd_byte_exact True 12555 13258 13258`。
- 草稿阶段 initial 验证：临时脚本，已删除，结果文件保留于 `/tmp/prd-wording-checks-initial.json`；exit 0；内部 `git diff --numstat` 为 PRD `2 1`，`git diff --check` exit 0、输出空，`git status --short --untracked-files=all` 恰两个授权文件；新 task 为 LF、末尾 LF、无尾随空白，全文文字限制扫描 0 命中，包含「读代码推断，未实际运行」。
- 草稿阶段以下 task 解析命令 exit 0、stderr 空，路径后输出 `in-progress False 1 None`；解析前后字节不变，唯一事件为 planned → in-progress，updated_at 保持事件时间：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" ai/tasks/v2.1.0-rc.2-prd-wording-4a-4b/task.md
```

- 草稿阶段仓库根执行八模块回归：临时脚本，已删除，结果文件保留于 `/tmp/prd-wording-unittest.json`、`/tmp/prd-wording-unittest.md`；runner 与下列原生命令均 exit 0：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_sbtd_task_document tests.test_sbtd_task_legacy_events_notice tests.test_sbtd_task_recovery tests.test_sbtd_task_routing tests.test_sbtd_task_schema tests.test_sbtd_task_state tests.test_sbtd_task_status_sync tests.test_sbtd_task_sync_git
```

- 实际结果 `Ran 135 tests in 50.753s`、`OK`；一轮无失败或重试，未报告 skipped，stdout 空。stderr 的「旧格式事件，不追溯」来自既有测试夹具，不是本 task 解析 stderr。
- 原生/raw `/tmp/prd-wording-unittest.json` 与同 stem 中文汇总 `/tmp/prd-wording-unittest.md` 已生成；绑定实际 HEAD `9fb137beef46b8411975c31cdae969925075687b`、当前分支和未提交工作树。Final Test Report／Run Summary MD=generated；Targeted Rerun=not-needed；Final Full Rerun=passed，仅八模块。
- 草稿阶段 final 验证：临时脚本，已删除，结果文件保留于 `/tmp/prd-wording-checks-final.json`；exit 0；写入回归结果后，PRD 精确字节、`2 1`、diff 空白、恰两文件、task 解析与全文文字扫描再次通过，扫描 0 命中；当时 task 为 `in-progress False 1 None`，stderr 空，updated_at 与唯一事件时间均为 `2026-10-26T00:27:49+08:00`。中文汇总九节、同 stem、命令、SHA、版本、数量与耗时均与原生报告一致，未填字段 0；这些草稿阶段检查未追加状态事件。

- 草稿与本轮定稿的本地证据不证明 CI、PR head、独立审查、合入或发布。未运行 lint／format／build、全仓测试、浏览器或移动端验证，因仅两份文档变更。BDD=skipped，无行为或持久场景变更，语言检查不适用；Cross-repo context／API Contract=not-needed，Mock Strategy=none；rtk=skipped-for-report，使用原生命令保留输出；Evidence Source=developer-local，Source Revision=dirty，Environment Alignment=unverified（本地与 CI Python 版本不同），Evidence Publication=local-only。临时证据不保证长期保留。

### 本轮定稿验证

- 入口核对根、分支、HEAD 与 origin/main 均符合预期，基线为 `9fb137beef46b8411975c31cdae969925075687b`；工作树已有 PRD 草稿与未跟踪的本 task，恰两个授权文件。两路径及父路径无 symlink／逃逸；`git check-ignore --no-index <两个授权路径>` exit 1、stdout／stderr 空，无命中。先 `ls` 确认上述五份草稿结果文件仍存在。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B /workspace/640-prd-wording-verify/expected-final.py`：exit 0，`prd_byte_exact True 12555 13296 13296`；Python 另按本轮入口字节确认仅 :80 整行替换，冒号后正文、:65、:79 与其余 PRD 字节均不变。
- 本轮 initial 检查：`git diff --numstat` 为 `2 1`（PRD）；`git diff --check` exit 0、输出空；`git status --short --untracked-files=all` 恰两个授权文件；task 无 CRLF、末尾 LF、无尾随空白，全文文字限制扫描 0 命中。原 planned → in-progress 事件、代码事实、推断标注、三处 skill 差异与 Python 3.13.5 实测表保留；原事件逐字节不变。结果保留于 `/tmp/prd-wording-final-initial.json`。
- 本轮使用上述 `TaskDocument.parse` 解析命令，转态前输出 `in-progress False 1 None`（status／legacy_events／events 数／completed_at），exit 0、stderr 空，解析前后字节不变。
- 本轮在仓库根真实执行上列八模块原生命令，`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest` 后接完整八模块列表；Python 3.13.5，`Ran 135 tests in 51.616s`、`OK`、exit 0，stdout 空，一轮无失败或重试，未报告 skipped。stderr 的旧格式通知来自既有测试夹具，不是本 task 的解析 stderr。
- 本轮原生/raw `/tmp/prd-wording-final-unittest.json` 与同 stem 中文汇总 `/tmp/prd-wording-final-unittest.md` 保留；九节顺序、命令、SHA、工作树、版本、数量与耗时已核对一致，无未填字段。Final Test Report／Run Summary MD=generated；Targeted Rerun=not-needed；Final Full Rerun=passed，仅八模块。使用原生命令保留输出，rtk=skipped-for-report。
- 上述验证完成后，真实 `TZ=Asia/Shanghai date +%Y-%m-%dT%H:%M:%S+08:00` exit 0，取得 `2026-10-26T07:41:24+08:00`；追加 in-progress → checking，updated_at 与末事件时间相同，completed_at=null。不写 done，不声明提交、CI 或发布完成。
- 转 checking 后再次运行 `expected-final.py`、`git diff --numstat`、`git diff --check`、全文文字扫描与同一 task 解析：字节核对 True、numstat 2／1、diff 空白检查 exit 0、扫描 0 命中，无 CRLF／尾随空白；解析为 `checking False 2 None`、exit 0、stderr 空，解析前后字节不变，updated_at 与末事件相同。`git status --short --untracked-files=all` 仍恰两个授权文件。结果保留于 `/tmp/prd-wording-final-checking.json`；准备与校验使用临时脚本，结果文件保留，临时脚本不作为证据路径。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | 产出 | 会话文件 |
|---|---|---|---|---|---|
| 1 | ping（2026-10-26 00:23:55 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-25T16-23-55-832Z_01a173e0-34b7-763f-8f0e-91b0bb7e8746.jsonl` |
| 2 | 会话 1（草稿） | openai-codex/gpt-6-astra（high） | 25／61 | PRD 两处措辞草稿与本 task 草稿 | `2026-10-25T16-24-48-855Z_01a173e1-03d7-70ed-b3c0-4ab5930fa148.jsonl` |
| 3 | ping2（2026-10-26 07:37:30 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-25T23-37-30-014Z_01a1756d-269e-72e9-860c-f5310ee45203.jsonl` |
| 4 | 会话 2（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告 | 4b 归因定稿与本 task 转 checking | `2026-10-25T23-38-25-162Z_01a1756d-fe0a-764b-89e3-b0d6ca5588b7.jsonl` |

每个 omp 会话一行；未使用子代理、advisor；会话 1 计数为编排方按 jsonl 统计（编排方整理），无 model_usage 记录；内部辅助 model_usage 记录（如有）由群内交付报告另列。本会话文件名仅经目录列表核对，未读取 jsonl 内容。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-26T00:27:49+08:00 | planned | in-progress | 编排方整理；写入者：主会话，建立 PRD 4a＋4b 本地草稿记录 | 基线 `9fb137b`；入口干净，分支、两路径及 ignore 安全；源码行号复核一致，时间戳与无基线旧格式解析已实测；草稿阶段不提交。 |
| 2026-10-26T07:41:24+08:00 | in-progress | checking | 编排方整理；写入者：主会话，4b 归因定稿与全部限定验证完成，进入检查 | 基线 `9fb137b`；expected-final.py 字节核对 True、exit 0，4a、:79 与其余字节保留；numstat 2／1，diff --check exit 0；全文文字扫描 0 命中、无 CRLF／尾随空白；八模块 135 tests OK、exit 0；task 解析 `checking False 2 None`、exit 0、stderr 空；工作树恰两个授权文件，原 planned → in-progress 事件逐字节不变。 |
