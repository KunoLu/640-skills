---
schema_version: 1
id: v2.1.0-rc.2-dashboard-keyword-launch
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：采用 strict；主会话为唯一 writer 与验证 controller，不启动子代理、不使用 advisor；提交与开 PR 由编排方执行。
status: checking
branch: docs/dashboard-keyword-launch
created_at: '2026-10-27T11:41:35+08:00'
updated_at: '2026-10-27T12:16:14+08:00'
completed_at: null
---

# PR-1：Dashboard 关键词启动流程

## 决定

- 编排方整理：只新增 `sbtd dashboard`／`sbtd ui` 的确认后启动指引，核查双语 README 与文档同步要求。
- 沿用近期 `v2.1.0-rc.2-contract-error-bodies`、`v2.1.0-rc.2-prd-wording-4a-4b` 命名与记录格式，选择 `v2.1.0-rc.2-dashboard-keyword-launch`；入口未发现同名任务。
- 未完整调用 grill-with-docs：需求、边界与验收明确，可由既有文档和源码核对，无新增领域歧义。

## 范围与边界

- 只在当前工作树修改 Skill／文档与本记录；不改 PRD、契约、ADR、schema、运行代码或 Dashboard 源码。
- 不联网、不安装依赖、不启动服务、不改全局配置、不执行 Git 写命令或 gh；不读取会话 jsonl 内容、环境变量或 dotenv 文件。
- 沿用参考 task 手写记录并以 TaskDocument 解析，不调用 TaskStore，不写 active／index／handoff／ignore／身份；不承诺自动恢复。临时验证产物只写 `/tmp/pr1-dashboard-keyword-*`。
- 验证通过后仅追加 checking，completed_at 保持 null；不声明独立复核、提交、CI 或发布完成。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮判定与证据 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求前 | not-needed；未完整 grill，既有术语与范围明确 |
| book-ddia-data-design | 数据、schema、迁移机制设计前 | not-needed；仅沿用 task 文档结构，不改数据机制 |
| book-legacy-change-safety | 既有运行行为修改前 | not-needed；不改运行代码，先核实文档与启动分支 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；无生产代码编辑 |
| book-release-readiness | 运行时／部署变化，验证后 | not-needed；只补充启动指引，不实施部署或改变生命周期 |
| writing-for-agents | Skill 编辑前 | 已读取；单一流程节、明确确认边界与事实源指针 |
| gherkin-bdd／TDD | 行为场景，编辑前 | 已读取 gherkin-bdd；仅 Skill 流程说明，不新增运行机制或 .feature；按下列人工场景核对，不冒充宿主执行证据 |
| project-validation | 文档修改后 | 适用；既有 unittest、TaskDocument 实测解析、命令逐字核对与格式扫描 |
| Code Readability Review／独立 review | check | 无手写生产代码／测试变更；主会话文档自核不冒充独立复核，交付保持 checking |

### 流程核对场景

| 前提／触发 | 应有结果 | 验证方式与边界 |
|---|---|---|
| 使用 workflow 时说任一关键词，尚无明确确认 | 先询问是否本机打开统计页，不安装、不启动 | 人工审阅 Skill 确认顺序；无真实宿主自动执行验证 |
| 明确拒绝 | 不启动，告知原关键词可再次触发 | 人工审阅拒绝分支 |
| 明确确认且有完整源码仓根与依赖前提 | 仅按既有安装文档的命令启动，默认打开浏览器 | 文档命令逐字比较；不执行安装／serve |
| 已有实例报错且 exit 2 | 告知先停止原 serve 再重新启动，不承诺重开浏览器或重发 ticket | 读代码推断，未实际运行；人工核对指引 |
| 无浏览器／打开失败 | 按既有 pairing 文件回退，不在对话打印 ticket | 文档与源码对照；无实际配对 |


## 代码事实与 README 结论

以下运行与安装行为判断均为读代码推断，未实际运行；后文 unittest 与解析实测不等于实际安装／启动验收。

- `install.sh:249-278`、`install.ps1:223-249`：source root 是 `sbtd-workflow-onboard` 目录，不是整个仓根。
- `sbtd-workflow-onboard/catalog.json:24-107`：Onboard 自身 source 为 `.`，其余 bundled Skill 位于 `templates/skills/`，无 sibling `sbtd-runtime` 安装项。
- `sbtd-workflow-onboard/scripts/onboard.py:98-113,265-271,6036-6074,2505-2528`：catalog 本地源必须位于 Skill 根内，普通模式从 SKILL_SOURCES 建复制操作，copytree 只复制各源目录；project-only 跳过全局 Skill。因此“不随 Onboard 安装／复制”仍准确。
- `sbtd-runtime/docs/install-and-use.md:233-247` 已记录仓根依赖安装、serve 启动、前台 Ctrl-C 与 pairing 文件回退；`sbtd-runtime/serve.py:780-843` 已有真实服务入口。因此 README 仅称 R1.0 契约已过时；“不是已运行的服务”不是对当前机器进程的可证实描述，也容易混同“无可运行服务”。两版仅改目录职责一行，保留不随 Onboard 安装边界，明确可手动启动而非自动运行。
- `sbtd-runtime/serve.py:242-245,279-286,795-800`：活实例锁报已有实例并 return 2；`AccessControl()` 位于 :809，ticket 交付在 :827，浏览器打开／文件回退在 :721-744。因此该失败分支不会重开浏览器或重发 ticket，与需求描述无差异；指引要求先停原 serve 再重启，不承诺重新配对。
- `sbtd-runtime/serve.py:827-843` 与安装文档 :246 一致：前台运行，Ctrl-C 后释放锁；本 PR 不改变生命周期。
- 修改后的 Skill :255-270 为唯一流程节，:3 添加关键词发现入口；:262-263 两条命令逐字沿用安装文档 :238-239，另说明方括号仅表示可选参数。无浏览器分支不读取或展示 ticket 内容。

## 镜像／同步候选逐项结论

| 候选 | 改／不改与原因 |
|---|---|
| `sbtd-workflow-onboard/SKILL.md` | 改；新增 Dashboard Launch Routing 与 description 关键词入口，既有 cleanup 流程不变 |
| `README.md:494`、`README.zh.md:485` | 改；同一目录职责条目双语对齐，依据见代码事实 |
| `sbtd-workflow-onboard/REFERENCE.md` | 不改；:613-639 镜像的是 cleanup 检测／确认协议，不是通用关键词清单；全文无 Dashboard／sbtd-runtime 启动指引或镜像要求 |
| `sbtd-workflow-onboard/templates/agents/AGENTS.global.md:31` | 不改；仅同步 cleanup 授权边界，无 Dashboard 路由；本次不扩大常驻全局规则 |
| `sbtd-workflow-onboard/templates/agents/AGENTS.project.md:41` | 不改；仅同步 cleanup 与本地状态边界，无 Dashboard 路由 |
| `sbtd-workflow-onboard/SKILL*` 语言版、`templates/skills/sbtd-workflow-onboard/` 生成副本 | 不改；文件枚举仅有 canonical SKILL.md，后者目录不存在；catalog :25-28 直接指向 `.`，不创建第二份源 |
| `sbtd-workflow-onboard/catalog.json`、`install.sh`、`install.ps1`、onboard 脚本 | 不改；安装机制无需变化，新流程不把 runtime 纳入安装载荷 |
| `sbtd-runtime/docs/install-and-use.md:233-249`、`sbtd-runtime/serve.py` | 不改；作为命令与生命周期事实源，无本次需修正差异 |
| `tests/` | 不改；文本检索 SKILL.md／REFERENCE.md／模板／README／sync，主要相关为 `test_workflow_contracts.py:597-605,1025-1075` 的公开文档断言；未发现 Dashboard 关键词或对应模板同步断言，既有安装与 task Git 回归照常运行，不新增措辞快照 |
| `CHANGELOG.md`、`CHANGELOG.zh.md` | 不改；:3,7 按 tag 双语记录，当前首节 :10 是 rc.1，无 rc.2 未发布节。只读 git show 核对近期 #185（fbaff7b）、#188（9967828）以及修改 Skill 的 #169（6f79e9d）完整文件集，均未改 CHANGELOG；不把新指引写入历史 tag |

## 验证与剩余边界

- CI 入口：`.github/workflows/validation.yml:35-54` 使用 Python 3.12.10，`python -B tests/run_ci.py --platform linux --shard ... --shards 3 --output ...`；`tests/run_ci.py:51-54,319-327` 发现全部 `tests/test_*.py` 后分片。本轮按改动选三个既有模块，不运行安装步骤或全仓 CI。
- 原生执行一次，工作目录为 `/workspace/640-pr1-dashboard-keyword`；`TMPDIR=/tmp/pr1-dashboard-keyword-tmp` 将测试临时夹具放入授权前缀。`test_onboard_multi_projects.py:19-34` 使用隔离 HOME，`test_sbtd_task_status_sync.py:114-138` 的 Git helper 固定临时仓库；未对当前工作树执行 Git 写命令。

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_workflow_contracts tests.test_onboard_multi_projects tests.test_sbtd_task_sync_git
```

- exit 0，`Ran 112 tests in 59.433s`、`OK`，墙钟 59.679s，Python 3.13.5；stdout 空，无失败／跳过／重试；stderr 的旧格式事件通知来自既有测试夹具。raw `/tmp/pr1-dashboard-keyword-unittest.json` 与同 stem 中文 `.md` 保留真实命令、时间、SHA、分支、环境、输出与退出码；九节顺序、数量、耗时、stem 与无未填字段已核对。
- 实际执行下列 TaskDocument 解析命令，exit 0、stderr 空，转态前输出 `in-progress False 1 None`；这是真实解析 smoke，不是手工判断 schema。

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" ai/tasks/v2.1.0-rc.2-dashboard-keyword-launch/task.md
```

- Python 内存检查正常返回：MarkdownIt 解析新增流程与安装文档，两个 bash 命令块逐字相等；PyYAML 解析 Skill metadata 正常且含两个触发词，相对文档链接存在；四文件 LF、末尾换行、无尾随空白，task 全文限制文字扫描 0 命中。人工核对询问／确认／拒绝、源码前提、已有实例与无浏览器分支；没有执行 LLM 宿主路由。
- Final Test Report／Run Summary MD=generated；Targeted Rerun=not-needed；Final Full Rerun=passed，仅三个模块。rtk=skipped-for-report，原生捕获输出；Evidence Source=developer-local，Source Revision=dirty，Environment Alignment=unverified，Evidence Publication=local-only。
- BDD=skipped：仅文档流程，未新增运行实现或 .feature；人工场景见上表。Cross-repo context／API Contract=not-needed；未引入 mock，既有测试隔离夹具不代表真实安装。未运行 lint／format／build、全仓 CI、Python 3.12、serve／浏览器或移动端；不以本地回归证明实际宿主服从指引、部署或发布。恢复边界为四份文本文件；未改运行数据，临时证据不保证长期保留。
- 转态后再次执行同一 TaskDocument 解析命令：exit 0、stderr 空，输出 `checking False 2 None`；原 planned → in-progress 事件保留，仅追加 in-progress → checking，completed_at=null。`git diff --check` exit 0、无输出，`git status --short --untracked-files=all` exit 0、仅列 README 两版、Skill 与新 task。
- 编排方本地全量：`PYTHONDONTWRITEBYTECODE=1 python3 -B tests/run_ci.py --platform linux --shard 1 --shards 1 --output /tmp/pr1-ci/out`，Python 3.13.5，2419 tests，1290.6s，exit 1，4 项失败：`test_sbtd_probe_links.MaterializeAuthorizationTests` 的 3 项链接竞态测试与 `sbtd_runtime_test_stats_query` 的 `test_iana_queries_and_dst_work_without_system_timezone_data`（本机缺 tzdata）。同样的测试在 origin/main 99678289 的干净分离工作树上单独运行亦失败（链接测试每次 1–3 项不定），与本 PR 文档改动无关；不宣称全量绿，CI 结果以 PR CI 为准。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | 产出 | 会话文件 |
|---|---|---|---|---|---|
| 1 | ping | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-27T03-41-08-638Z_01a17b72-929e-77e8-a56b-79d03b3e4d51.jsonl` |
| 2 | 本会话 | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），待后续回填 | Skill、README 与本 task | `2026-10-27T03-41-20-543Z_01a17b72-c11f-7565-bdc5-4ab23474e45d.jsonl` |
| 3 | 会话 2（追加式回填） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），待后续回填 | 本 task 回填 | `2026-10-27T04-15-57-687Z_01a17b92-72f7-712d-a5a2-bf75fe7244f3.jsonl` |

- 回填（编排方整理，数据由编排方从会话 jsonl 统计）：ping 为 assistant 消息 1、toolCall 0、model_usage 0；会话 1 为 assistant 消息 32、toolCall 84（read 38、edit 12、grep 9、bash 8、todo 8、eval 4、write 2、glob 2、find 1）、model_usage 21（jev-latest，purpose find，内部辅助检索），assistant 消息模型均为 gpt-6-astra；看门狗未杀会话，无 resume；未使用 kimi、子代理或 advisor。第 2 行原文保留不改。

编排方整理；文件名经 ls 取得，仅列 ping／session 目录，不读 jsonl 内容；未启动子代理或 advisor。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-27T11:41:35+08:00 | planned | in-progress | 编排方整理；主会话开始 strict 文档任务 | 分支匹配，入口工作树干净；HEAD 与 origin/main 均为 99678289f8e1d756fad3a27a1797bca8c087c25f；四目标路径无 symlink／逃逸，新 task 不存在，ignore 检查 exit 1、无命中。 |
| 2026-10-27T11:48:15+08:00 | in-progress | checking | 编排方整理；主会话完成文档修改与限定验证，进入检查 | 三模块 112 tests OK、exit 0；TaskDocument 转态前 in-progress False 1 None；命令块逐字一致，四文件格式与限制文字扫描通过；git diff --check exit 0，git status --short --untracked-files=all 仅三份 Skill／README 与本 task；时间取真实 TZ=Asia/Shanghai date；未执行实际 serve／宿主路由或独立复核，completed_at=null。 |
