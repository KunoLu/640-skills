---
schema_version: 1
id: v2.1.0-rc.5-probe-links-flaky-test
workflow_mode: strict
mode_source: user
mode_note: 用户 2026-11-11 15:10 群内确认（rc.5 全程用 strict），Lord 记录；本记录于 2026-11-11T15:14:49+08:00 从 default 切换为 strict，原轮开始时记录为 default，不追溯冒称当时已是 strict；编排方整理共享 task 记录，唯一 writer，不使用子代理；已创建开发分支、commit 并 push，已开 PR #208。
status: checking
branch: chore/v2.1.0-rc.5-probe-links-flaky-143
created_at: '2026-11-11T14:38:02+08:00'
updated_at: '2026-11-11T16:12:34+08:00'
completed_at: null
---

# #143：确定化 probe link materialize 授权测试

## 目标与范围

仅修复 `tests/test_sbtd_probe_links.py::MaterializeAuthorizationTests` 的文件系统时序依赖，保留全部用例、ContractError 类型及既有拒绝错误码；不改正式代码，不增加 skip、重试或宽松断言。验收为独立进程连续至少 30 轮目标类全过、完整模块一次通过，并运行适用轻量检查。

#143 原轮授权范围为授权工作树根，基线与 origin/main 均为 `80f14263e7d8bc6ae84f04ba94218e4857fc8b8f`。原轮写前工作树无改动；目标路径与父目录无 symlink、无 ignore 命中，新任务目录不存在。原轮允许测试文件、任务记录、必要索引／CHANGELOG 记账；临时诊断辅助只放 tests/，完成后移除。不访问主 checkout，不修改 active、handoff、ignore 或身份，不安装依赖、不发布。本次基线为 `0e7a1a807415110d080d1c1e0a5e96f663581d74`，分支与 frontmatter 一致；保留已有未提交 task 修订，仅授权本 task 与两份 CHANGELOG，路径为普通 tracked 文件、无 symlink 或 ignore 命中。

未完整调用 grill-with-docs：范围、验收与错误码保持要求明确，无领域歧义。#143 原轮开始时记录为 default；决定依据为「用户 2026-11-11 15:10 群内确认（rc.5 全程用 strict），Lord 记录」，本次据此修改记录，不追溯宣称原轮已按 strict 执行。strict 落实为本 task.md 落盘，包含状态事件与验证证据；本次审阅修订的 omp 运行按该记录执行，主会话唯一 writer／验证 controller，无子代理或独立审阅声明。

本次 Book Gate Plan：仅修订任务元数据与双语日志，不改 schema、测试或正式代码；DDD（无完整 grill／领域歧义）、DDIA（无数据模型／迁移／恢复机制变更）、Legacy Safety（无行为变更）、Refactoring（无生产代码编辑）、Release Readiness（无运行时／部署／发布动作）均为 not-needed，适用性在编辑前核对。本次 check 使用现有 parser／history 和索引生成器；无用户可见行为变化，BDD、代码可读性与独立审阅不适用，不把自检称为独立审阅。

## 调查依据

已读取 `gh issue view 143 --json body,comments`（无评论）、`gh pr diff 206`、`gh pr diff 207 --name-only`，以及索引、rc.4 发布任务、rc.2 index-regen 任务、task state 契约与索引生成实现。

`sbtd_probe_links.py` 的 `_object_identity` 比较 device、inode、ctime_ns，不比较 mtime。prepare 记录链接和目标身份并执行 live 复核；materialize 在 `backup_reference` 前后均执行 `_validate_live`，先检查链接身份，再检查文本、目标身份与内容。三个问题用例原本全部断言 `identity-mismatch`；文本变化用例的原注释明确要求身份拒绝优先，不应改成接受两种错误码。

## 记账惯例

`TaskStore._catalog()` 与 `_index_candidate()` 生成排序导航自动块，不能手工补索引行；沿用 #206 和 rc.2 index-regen 的手写 task＋真实 parser/history 校验惯例，不调用会写 active 的 TaskStore 生命周期方法，不声称自动恢复。

#206 是任务记账 PR，未修改双 CHANGELOG；#207 是发布／功能 PR，修改两份 CHANGELOG。本次按仓库双语同步惯例，已在 `CHANGELOG.md` 与 `CHANGELOG.zh.md` 导言后、已发布 rc.4 前新增未发布 rc.5 节，精简记录 #143 的测试夹具修复，并同时引用 #143／#208；不改用户可见行为，不改 rc.4 及更早历史，不填写发布日期或声称 tag／CI 结果。README、ENTRYPOINT 与 automation 使用方式不变，亦不修改。

## 根因与修复

白话根因：删掉链接马上原地重建，文件系统可能把旧 inode 又分给新链接，而且 ctime 也没变，程序看到的身份就完全一样。同文本时拒绝可能消失，改文本时则越过身份检查后报 link-mismatch，而测试要求 identity-mismatch。

真实临时目录探针连续 20/20 次观察到重建前后三元组完全相同，例如 `(65040, 115484, 1794379138461170286)`。`ctime_ns` 返回纳秒单位不代表每次文件操作都有不同时间值；设置 mtime 不能直接控制被测 ctime，因此不使用 sleep 或 utime 掩盖时序。

仅在三个既有用例把 `link.unlink()` 改为 `link.rename(self.base / "retired-link")`，再按原逻辑创建新链接。旧对象留在同一个 TemporaryDirectory 内，inode 不会被复用；与本类既有目标目录替换用例的 rename 保留模式一致。三条注释解释 inode 存活约束，不新增框架／永久辅助。复制中替换仍发生在真实 `backup_reference` 返回之后，验证真实的复制后身份复核。

原有 10 条用例、全部异常类型／错误码／内容断言逐字保留，无新增 skip、重试、mock 或宽松断言。原有 ctime 单字段变化用例保持不动；正式代码完全未编辑。

## 本地验证证据

环境：Linux x64，Python 3.13.5；Evidence Source：developer-local；Source Revision：dirty；Environment Alignment：unverified（不是 CI 的 Python 3.12.10／三平台环境）；Evidence Publication：local-only。测试均在授权 worktree 根执行，不提交、不推送。

| 命令／检查 | 实际结果 |
|---|---|
| 修改前 `python3 -B -m unittest tests.test_sbtd_probe_links.MaterializeAuthorizationTests` | 首轮 10 tests OK |
| 修改前 `python3 -B tests/_probe_links_repeat.py 3` | 0/3 轮通过：同文本替换 3 轮均 `ContractError not raised`；第 2 轮文本变化另报 `'link-mismatch' != 'identity-mismatch'`。连同首轮共 1/4 轮通过 |
| `python3 -B tests/_probe_links_repeat.py probe` | 快速 unlink／symlink 身份碰撞 20/20；本地现象，不声称所有文件系统相同 |
| 修改后 `python3 -B tests/_probe_links_repeat.py 30` | 30/30 轮通过，每轮 10 tests OK，共 300 次用例执行；无失败、无 skip |
| `python3 -B -m unittest tests.test_sbtd_probe_links` | 63 tests OK，63/63，0 skip，4.610s |
| `rtk ruff check tests/test_sbtd_probe_links.py` | exit 1：38 项，RUF059×23、SIM117×8、UP037×3、F841×3、F401×1；非通过 |
| 基线 `git show HEAD:tests/test_sbtd_probe_links.py` 经 stdin 输入 `ruff check --no-cache --stdin-filename tests/test_sbtd_probe_links.py - --output-format concise` | 同样 38 项、同规则与对应语句位置（新增注释造成后续行号平移）；未引入新 lint 问题，未修改这些既有问题 |
| 下方内存 Python 语法检查 | 116/116 文件编译成功，不写 bytecode |
| `bash -n install.sh` | exit 0 |
| 新 task 的 `TaskDocument.parse` 和 `TaskStore._history` | 状态转换前输出 `TASK in-progress legacy False events 1 HISTORY (None, True)` |
| 下方索引生成命令 | 生成 78 行候选，仅多本任务导航；13 条「旧格式事件，不追溯」来自既有记录，本任务非 legacy |

三十轮辅助以固定 `range(1, count + 1)` 顺序执行独立进程 `subprocess.run(["python3", "-B", "-m", "unittest", "tests.test_sbtd_probe_links.MaterializeAuthorizationTests"], check=False)`，保留每轮原生输出，累计所有返回码；任一失败最终 exit 1，不重试失败用例。它是验收循环，不在测试代码中；`tests/_probe_links_repeat.py` 已移除。未生成独立正式报告，本节保留本地失败与成功事实，不冒称 PR-head 或 CI 证据。

CI `.github/workflows/validation.yml` 的便宜检查为 compileall 和 bash syntax，没有 Ruff／独立 task-index lint 步骤。为避免 compileall 在正式代码目录落 bytecode，使用相同 scripts／tests 范围的内存编译：

```sh
python3 -B -c 'from pathlib import Path; paths=sorted(Path("sbtd-workflow-onboard/scripts").rglob("*.py"))+sorted(Path("tests").rglob("*.py")); [compile(p.read_bytes(),str(p),"exec") for p in paths]; print("SYNTAX_OK",len(paths),"Python files; no bytecode written")'
bash -n install.sh
```

索引真实生成命令（生成候选，通过编辑工具仅应用生成器给出的新增行；随后按完整候选字节校验，不另写排序规则）：

```sh
python3 -B -c 'import sys; from pathlib import Path; sys.path.insert(0,"sbtd-workflow-onboard/scripts"); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(),read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); print(a.decode(),end=""); print("INDEX_ROWS",len(s._index_rows(r)))'
```

任务文档与索引最终使用真实 parser／history 和完整候选一致性断言复核；最终结果在交付回复报告，避免为记录检查而无限重写记录。

本次 strict＋CHANGELOG 文档修订验证（developer-local、Source Revision: dirty、Evidence Publication: local-only）：`TaskDocument.parse`（含 frontmatter schema／时间戳）与 `TaskStore._history` 已通过，输出 `strict / user / checking`、`EVENTS 3 LEGACY False HISTORY (None, True)`；两条原状态事件保留，仅追加 checking→checking 的模式切换事件。仓库根执行以下只读索引校验，输出 `INDEX_ROWS 78`、`byte_identical True cur 6082 gen 6082`；13 条「旧格式事件，不追溯」来自既有其他记录，本任务非 legacy。未修改 index。

```sh
python3 -B -c 'import sys; from pathlib import Path; sys.path.insert(0,"sbtd-workflow-onboard/scripts"); from sbtd_task_document import TaskDocument; from sbtd_task_state import TaskStore; d=TaskDocument.parse(Path("ai/tasks/v2.1.0-rc.5-probe-links-flaky-test/task.md").read_text()); print("FRONTMATTER",{k:d.frontmatter[k] for k in ("workflow_mode","mode_source","status","updated_at","completed_at")}); print("EVENTS",len(d.events),"LEGACY",d.legacy_events,"HISTORY",TaskStore._history(d)); assert not d.legacy_events and len(d.events)==3 and TaskStore._history(d)==(None,True); assert (d.frontmatter["workflow_mode"],d.frontmatter["mode_source"],d.frontmatter["status"])==("strict","user","checking")'
python3 -B -c 'import sys; from pathlib import Path; sys.path.insert(0,"sbtd-workflow-onboard/scripts"); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(),read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); cur=Path("ai/tasks/index.md").read_bytes(); print("INDEX_ROWS",len(s._index_rows(r))); print("byte_identical", cur==a, "cur",len(cur),"gen",len(a))'
```

## 交付与剩余边界

#143 原轮修改目标测试、本 task 与生成索引；本次仅修改本 task、`CHANGELOG.md`、`CHANGELOG.zh.md` 三个授权文件，索引只读生成校验，不修改测试或正式代码。任务保持 `checking`（待审），`completed_at: null`；编排方已创建开发分支、commit 并 push，已开 PR #208，本次不 commit、push 或切分支，不写 done。

模型核账：主模型 openai-codex/gpt-6-astra（thinking high）。#143 原轮 astra 16 次（1 次主会话运行，无子代理），同轮 typesafe/jev-latest 40 次，仅用于 omp 内置 find 工具、未写内容，不计入 astra；按 Reviewy 意见修订第一次会话 astra 10 次、jev-latest 0 次；核次补记会话 astra 9 次（会话结束后核对）、jev-latest 0 次。本轮（strict＋CHANGELOG）会话 astra 14 次，按本会话 jsonl 中 role=assistant、provider=openai-codex、model=gpt-6-astra 的条数核计，并计入 1 次收尾回复；typesafe/jev-latest 次数不可核：本会话 find 日志记录 23 requests，但未提供 provider／model，不能把这些请求确认为 jev-latest，也不并入 astra。15:45 轮（本次措辞修订会话）openai-codex/gpt-6-astra（thinking high）据事后日志更正为 9 次；find 工具用 typesafe/jev-latest 24 次，不并入 astra。主会话唯一 writer／验证 controller，无子代理或独立审阅声明。

本轮（次数勘误）模型核账：主模型 openai-codex/gpt-6-astra（thinking high）按指定口径计 8 次：完成其他修改与校验后，本会话 jsonl 中 role=assistant、provider=openai-codex、model=gpt-6-astra 已出现 7 条，加 1 次收尾 stop 回复；未记录其他模型的 assistant 消息。未调用 find，typesafe/jev-latest 0 次，不并入 astra。本段为本轮对 task.md 的最后一次编辑，写入后不再调用工具。主会话唯一 writer／验证 controller，无子代理或独立审阅声明。

#143 原轮工具记录：rtk used（Ruff）；unittest 按编排方整理的原生命令执行，避免包装缓存。BDD：skipped，无用户可见行为或 .feature 变化；Cross-repo context／API Contract：not-needed；Mock Strategy：contract-backed（保留既有被测文件操作 seam 与 host doubles，修复未新增 mock）。Final Test Report／Run Summary MD：not-needed，原轮为本地 unittest 验证；Targeted Rerun：passed；Final Full Rerun：passed（仅完整目标模块，不是仓库全套）。本次文档修订 rtk：not-needed（按指定原生只读命令校验）；BDD／代码 lint／单元与集成测试：skipped（未改行为或代码）；Cross-repo context／API Contract：not-needed；Mock Strategy：none；Final Test Report／Run Summary MD：not-needed，未生成正式测试报告。

#143 原轮未运行全仓库测试、三平台 CI 或 UI/E2E：只改三个文件系统夹具动作，本地验收范围已覆盖；macOS／Windows 仍待外部 CI。38 项既有 lint 问题保留，不作为此次通过项。正式代码的身份三元组碰撞能力边界不由本次测试修复扩大；本任务只确保构造真实身份变化。本次仅文档／元数据修订，不重跑原轮测试或冒称新 CI 结果；恢复仅撤回本次三个授权文件中的本次改动，保留已有未提交修订，无生产迁移或部署回滚。

建议 commit message：`chore(tests): stabilize probe-link materialization authorization tests (#143)`。
建议 PR 标题：`chore(tests): 修复 probe links 授权测试偶发失败（#143）`，沿用近期 PR 的 conventional prefix＋中文主题格式。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-11T14:38:02+08:00 | planned | in-progress | 建立 default 共享记录，开始 #143 测试确定化诊断。 | 分支、完整基线、干净工作树、路径安全已核对；首轮原生目标测试 10 tests OK；时间来自 date --iso-8601=seconds。 |
| 2026-11-11T14:40:39+08:00 | in-progress | checking | 测试夹具确定化及本地验收完成，进入待审；不标 done，不声明已提 PR。 | 目标类 30/30 轮、完整模块 63/63；Python 语法 116/116、bash syntax exit 0；Ruff 与基线相同的 38 项未修复；task parser/history 有效，索引生成 78 行；时间来自 date --iso-8601=seconds。 |
| 2026-11-11T15:14:49+08:00 | checking | checking | 用户 2026-11-11 15:10 群内确认（rc.5 全程用 strict），Lord 记录；本任务记录据此从 default 改为 strict，状态保持 checking。 | 依据用户本次明确指定的决定原文；workflow_mode=strict、mode_source=user；原轮记录当时为 default，不追溯改写；本行时间为记录切换时间，来自 TZ=Asia/Shanghai date --iso-8601=seconds。 |
| 2026-11-11T15:45:15+08:00 | checking | checking | 按 Reviewy 意见统一 strict 决定原文，仅修订 task.md 措辞与本轮模型核账，保持待审。 | 依据用户本次明确指定的原文，统一 mode_note、正文与模式切换事件；保留 15:10 用户决定时间及 15:14:49 记录切换时间，不改历史模型次数；时间来自 TZ=Asia/Shanghai date --iso-8601=seconds。 |
| 2026-11-11T16:12:34+08:00 | checking | checking | 按事后日志事实更正 15:45 轮次数：astra 8→9，jev-latest 原“不可核”更正为 find 工具用 jev-latest 24 次；保持待审。 | 本轮（次数勘误）核账见模型核账段，astra 按本会话 jsonl 指定条件计数并加 1 次收尾回复；未调用 find，jev-latest 0 次，不并入 astra；仅修改本 task.md；时间来自 TZ=Asia/Shanghai date --iso-8601=seconds。 |
