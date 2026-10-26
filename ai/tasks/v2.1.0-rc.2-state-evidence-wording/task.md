---
schema_version: 1
id: v2.1.0-rc.2-state-evidence-wording
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：本轮采用 strict，主会话为两个授权文件唯一 writer 与验证 controller；不启动子代理、不使用 advisor；提交与推送由编排方执行。
status: checking
branch: docs/v2.1.0-rc.2-state-evidence-wording
created_at: '2026-10-26T12:38:48+08:00'
updated_at: '2026-10-26T12:42:30+08:00'
completed_at: null
---

# rc.2：state.md 收尾证据措辞

## 决定

Lord 2026-10-26 群内裁定（分钟不可考）：state.md:52 证据句按选项 1 改写为现状描述，只改该句，其余字节不变。

- 目标：让 state.md:52 的收尾证据描述与现状一致；代码 `check_finish_commit` 要求 JSON，现行手写收尾提交用文字证据，只含 CLEAN 对应 SHA 与 CI run。
- `docs/prd/sbtd-workflow-v2-task-status-sync.md:80` 归因：用户 2026-10-26 07:35 群内确认（同意 4b 按代码事实改写），Lord 记录。
- 备注：沿用 main PRD 写法，分钟未独立核实。
- 未完整调用 grill-with-docs：替换文本、范围与验收明确，直接核对既有文档与代码，无新增领域歧义。

## 范围与边界

只改 `sbtd-workflow-onboard/templates/skills/sbtd-task/references/state.md:52` 的证据句，新建本 task。Python 按字节读取 `/workspace/640-state-evidence-verify/old.txt` 与 `new.txt`，确认旧句恰出现一次且位于第 52 行，计算替换后交编辑工具落盘；同一行内替换，不额外增删空格或换行。后半 `check_finish_commit(task_path, commit="HEAD")` 本地验证段及其余字节保持不变，state.md 不加归因或说明。

不改代码、契约、测试、其他文档或历史 task。不安装依赖、不改全局配置，不提交、不操作暂存区、不推送或发布。沿用参考 task 的手写记录，不调用 TaskStore，不写 active／handoff／index／ignore／身份，不承诺 TaskStore 自动恢复。临时文件只放 `/tmp`；仅列会话目录取文件名，不读取 jsonl 内容，不读取或打印环境变量与秘密文件。

## 代码事实

基线与入口 HEAD、origin/main 均为 `5aa5a1aa74951a8c57e2bbd7b0a2bf6f132914ae`，工作树入口干净。以下行号经 `git grep` 与源码读取核对：

- `sbtd-workflow-onboard/scripts/sbtd_task_sync.py:350-409` 定义 `check_finish_commit`；:351 明记只验证本地收尾 diff，不证明 CLEAN 或 CI run 真实性。
- 同文件 :383-391：`json.loads(event["evidence"])` 解析证据，要求对象恰含 `clean_sha`、`ci_run`；前者等于父提交，后者为非空字符串。:375-380、:392-409 检查状态、事件、时间、候选正文与文件模式。
- `git grep -n check_finish_commit`：非文档代码仅有上述 :350 定义，以及 `tests/test_sbtd_task_sync_git.py:309,359,371,379` 调用。读代码推断，未实际运行：仓库当前调用点只在测试内；该结论是静态检索结论，不代表对所有外部宿主调用的证明。
- `docs/prd/sbtd-workflow-v2-task-status-sync.md:80` 记录 JSON 校验与现行文字证据的区别；`ai/tasks/v2.1.0-rc.2-r2.1c-export-menu/task.md:166` 的收尾事件用文字记录 CLEAN 对应 SHA 与 CI run。
- 读代码推断，未实际运行：文字 evidence 不符合 :383 的 JSON 解析要求；未对上述历史收尾提交执行 `check_finish_commit`，不把静态推断写成历史提交实测。
- `.github/workflows/validation.yml:38,85,114,173,218,255,283,310` 配置 Python 3.12.10；本地 `python3 --version` 为 Python 3.13.5，未在 3.12 实测。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮判定与证据 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求前 | not-needed；未完整 grill，仅核对现状措辞 |
| book-ddia-data-design | schema／迁移／持久化机制设计前 | not-needed；不改 schema 或机制，沿用 task 格式 |
| book-legacy-change-safety | 既有行为修改前 | not-needed；无行为修改，以精确字节比较保护范围 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；无生产代码修改 |
| book-release-readiness | 运行时／部署变化，验证后 | not-needed；无运行时、部署或发布变化 |
| gherkin-bdd／TDD | 行为、场景或状态机制变更前 | not-needed；只改文档措辞，不改行为或机制 |
| project-validation | 文档落盘后 | 适用；已读取 Skill，执行精确字节检查、三组指定回归、task 解析及范围／文字检查 |
| Code Readability Review／独立 review | check | not-needed；无代码或测试修改，仅单一文档与任务记录，不触发独立 review；主会话自核不冒充独立审查 |

## 验证与剩余边界

- 入口 `git grep -n "证据使用 JSON"`：exit 0，唯一命中 state.md:52，原文一致。Python 字节预检：旧句出现 1 次、行号 52、state.md 与 origin/main 完全一致；两个授权路径及父路径无 symlink／逃逸，新 task 原先不存在。
- `git check-ignore --no-index sbtd-workflow-onboard/templates/skills/sbtd-task/references/state.md ai/tasks/v2.1.0-rc.2-state-evidence-wording/task.md`：exit 1，输出空，两路径均未命中 ignore。
- 事件时间取自真实 `TZ=Asia/Shanghai date +%Y-%m-%dT%H:%M:%S+08:00`，exit 0；开始时 planned → in-progress，completed_at=null。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B /workspace/640-state-evidence-verify/expected.py`：exit 0，`state_byte_exact True 21574 21756 21756`。Python 另按入口字节核对替换结果，只有授权旧句替换为新句，其余字节与换行不变。
- `git diff --stat`：state.md 为 1 insertion、1 deletion；`git diff --numstat` 为 `1 1`。新 task 尚未跟踪，不计入上述 diff；`git status --short --untracked-files=all` 恰两个授权文件（state.md 修改、本 task 新建）。`git diff --check` exit 0、输出空。
- Python 文字与格式检查：task 全文及 state.md 改动的限制词扫描 0 命中；task 为 LF、末尾 LF、无尾随空白。原 planned → in-progress 事件保留。
- 以下三组命令均在仓库根执行，各执行一次，exit 0、stdout 空、结果 OK，无失败或重试，未报告 skipped。`python3 --version` exit 0，Python 3.13.5；CI 用 Python 3.12.10，本地未在 3.12 实测。旧格式通知来自既有测试夹具，不是本 task 解析 stderr。

| 命令 | exit | 测试数／原生耗时 | 命令墙钟耗时 | 本地证据 stem |
|---|---|---|---|---|
| `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_onboard_multi_projects` | 0 | 59 tests，52.150s，OK | 52.210s | `/tmp/state-evidence-onboard` |
| `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_sbtd_task_sync_git` | 0 | 14 tests，6.522s，OK | 6.692s | `/tmp/state-evidence-sync-git` |
| `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_sbtd_task_document tests.test_sbtd_task_legacy_events_notice tests.test_sbtd_task_recovery tests.test_sbtd_task_routing tests.test_sbtd_task_schema tests.test_sbtd_task_state tests.test_sbtd_task_status_sync tests.test_sbtd_task_sync_git` | 0 | 135 tests，50.873s，OK | 51.108s | `/tmp/state-evidence-eight-modules` |

每个 stem 对应原生/raw `.json` 与同 stem 中文汇总 `.md`，保留命令、stdout、stderr、exit、真实 SHA、工作树与版本；汇总九节顺序、计数、耗时、exit 与 raw 一致，无未填字段。Final Test Report／Run Summary MD=generated；Targeted Rerun=not-needed；Final Full Rerun=passed，仅上列计划范围，八模块包含 sync-git，不累加为独立用例总数。

实测 task 解析命令：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" ai/tasks/v2.1.0-rc.2-state-evidence-wording/task.md
```

- 转态前解析为 `in-progress False 1 None`，exit 0、stderr 空。全部限定验证通过后，真实 date 命令取得 `2026-10-26T12:42:30+08:00`，追加 in-progress → checking；updated_at 等于末事件时间，completed_at=null，不写 done。
- 最终验收核对同一解析命令输出 `checking False 2 None`、exit 0、stderr 空，并复核字节精确、numstat 1／1、恰两个授权文件、diff 空白与文字／LF 检查；不以本地验证代表 CI 或发布。

- 证据绑定上述基线、当前分支与未提交工作树；Evidence Source=developer-local，Source Revision=dirty，Environment Alignment=unverified，Evidence Publication=local-only。rtk=skipped-for-report，使用原生命令保留输出。CI 与独立复核未执行，不证明 PR head、合入或发布；临时证据不保证长期保留。
- BDD=skipped，无行为或持久场景变更，语言检查不适用；Cross-repo context／API Contract=not-needed，Mock Strategy=none。未运行全仓测试、lint／formatter／build、浏览器或移动端验证：范围仅两份文档。恢复边界为两个授权文件的文档改动，不涉及数据迁移。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | 产出 | 会话文件 |
|---|---|---|---|---|---|
| 1 | ping（2026-10-26 12:37:51 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-26T04-37-51-630Z_01a17680-238e-7137-94c2-eb97038a5082.jsonl` |
| 2 | 会话 1（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告 | state.md 措辞与本 task | `2026-10-26T04-38-33-343Z_01a17680-c67f-734a-b014-648cf9100fe2.jsonl` |

每个 omp 会话一行；未使用子代理与 advisor；内部辅助 model_usage（如有）由群内交付报告另列。会话文件名仅经 ls 目录列表取得，未读取 jsonl 内容。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-26T12:38:48+08:00 | planned | in-progress | 编排方整理；写入者：主会话，开始 strict 收尾证据措辞修订 | 基线 `5aa5a1aa74951a8c57e2bbd7b0a2bf6f132914ae`；入口干净，分支、两路径与 ignore 安全；旧句唯一且位于 state.md:52，代码与 PRD 行号已核对。 |
| 2026-10-26T12:42:30+08:00 | in-progress | checking | 编排方整理；写入者：主会话，证据句修订与全部限定验证完成，进入检查 | expected.py 字节核对 True、exit 0；state.md numstat 1／1，diff --check exit 0，工作树恰两个授权文件；文字扫描 0 命中、LF 与尾随空白检查通过；三组回归 59／14／135 tests 均 OK、exit 0；task 最终解析核对 checking False 2 None，completed_at=null；CI 与独立复核未执行。 |
