---
schema_version: 1
id: v2.1.0-rc.2-contract-error-bodies
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：本轮采用 strict，主会话为四个授权文件唯一 writer 与验证 controller；不启动子代理、不使用 advisor；提交、推送与开 PR 由编排方执行。
status: done
branch: docs/v2.1.0-rc.2-contract-error-bodies
created_at: '2026-10-26T15:21:16+08:00'
updated_at: '2026-10-26T16:00:51+08:00'
completed_at: '2026-10-26T16:00:51+08:00'
---

# rc.2：下载 409 ExportNotReady 与通用 DetailError

## 决定

用户 2026-10-26 群内确认（方向 1，下载 409 新建 ExportNotReady，其他保留 Conflict），Lord 记录。
- 备注：上一条归因的确认分钟不可考（群内无法读取消息记录，不写近似值）。

- 未完整调用 grill-with-docs：方向、范围与验收明确，直接核对既有实现，无新增领域歧义。
- 本 PR 只改文档／契约／测试，后端行为未变；serve.py、dashboard、static 均保持 0 行改动。

## 范围与边界

- 仅修改 `sbtd-runtime/contracts/openapi.yaml`、`sbtd-runtime/tests/test_golden_contracts.py`、`sbtd-runtime/docs/install-and-use.md`，新建本 task；serve.py／dashboard／static 不动。
- OpenAPI 基线 :378 的 collection tag 与 :379 的 ingest scope summary、:808-809 的 Unauthorized scope 措辞、:816-817 的 Gone snapshot 措辞仅标注，不改原文。共享 Conflict 及 refresh／ingest 引用保留；get／delete 导出不增加 409；422／503／507 原 schema 不改。
- 同键异 payload 创建导出实际映射 400，而 Conflict 描述为 409：读代码推断，未实际运行；属于代码行为问题，不在本 PR，留待以后用户决定。
- 不实现 refresh、ingest、getOpenApi；新说明不将契约声明冒充已路由能力。不改 PRD、plan.md、其他测试、监听、认证、重放、配额、存储或清扫机制。
- 沿用参考 task 手写结构并用 TaskDocument 解析；不调用 TaskStore，不写 active／index／handoff／ignore／身份，不承诺 TaskStore 自动恢复。不联网、不安装、不改全局配置、不提交或发布；临时证据仅写 `/tmp/contract-error-bodies-*`。

## 代码事实

入口 HEAD 与 origin/main 均为 `3b5497b360b1325a4ca95c262665d59832cd7c31`。以下为已核对源码行号；运行行为判断均为读代码推断，未实际运行，后文实测另列。

- `sbtd-runtime/serve.py:364-367` 直接构造 JSONResponse；:395、:405、:411、:513、:530-538、:560-576、:625-629、:664-689 的 400／401／403／404／410／409 detail 体恰为单键。采用 `DetailError.additionalProperties: false`，detail 为必需 string，不枚举 QueryScopeError／CursorError 的动态值。
- 同文件 :539-547、:630-658：422／507 另有数值字段，503 有固定 detail；三类继续使用原独立 schema，不套 DetailError。
- `sbtd-runtime/export_store.py:425-434` 对已找到的非 ready 作业抛 ExportNotReady；`sbtd-runtime/serve.py:671-689` 映射下载 409 `{"detail":"export is not ready"}`。queued／generating／failed／cancelled 均在非 ready 集合内，不能推出稍后必成功。
- `sbtd-runtime/export_store.py:405-423,436-465` 与 `sbtd-runtime/serve.py:666-683`：get 返回状态视图，delete 成功 204，两条路径不抛 ExportNotReady。
- `sbtd-runtime/export_store.py:528-538` 的同键异 payload 抛 ValueError；`sbtd-runtime/serve.py:594-600,624-625` 将它映射为 400 invalid export request。
- `sbtd-runtime/serve.py:691-715` 路由表没有 refresh、ingest、getOpenApi；OpenAPI 基线 :373-400 的 refresh／ingest 409 仍是声明，不能声称业务 HTTP 已可调用。
- `sbtd-runtime/serve.py:648-650` 显式通用 500 为 text/plain；:712-715 使用 StaticFiles／Starlette。框架 404／405 的已有观察来源为 `/tmp/640-contract-proposal.md:300-353` 的最小探针，非完整服务实测；本轮烟测证据另列。
- `.github/workflows/validation.yml:38,85,114,173,218,255,283,310` 配置 Python 3.12.10；本地版本检查为 Python 3.13.5，未在 3.12 实测。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮判定与证据 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求前 | not-needed；未完整 grill，方向与术语边界明确 |
| book-ddia-data-design | API schema，设计稳定前 | confirmed；已读取 Skill 并输出独立 DDIA Data Design Review；handler／ExportStore 为事实源，wire body、异步路径、一致性、幂等及重试不改，无迁移／回填／重放；风险是生成器组件类型名变化；要求样本、引用与回归验证 |
| book-legacy-change-safety | 既有运行行为修改前 | not-needed；不改运行代码，以契约样本与既有回归保护保留行为 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；只改契约、测试与说明，无生产代码编辑 |
| book-release-readiness | 运行时／部署变化，验证后 | not-needed；后端与部署不改，不作发布就绪声明 |
| gherkin-bdd／TDD | 新行为或高风险机制变更前 | not-needed；无新增 HTTP 行为或状态机制，沿用 golden JSON Schema 正反例，不新建 .feature |
| ponytail | 实现前 | 已读取；复用现有 YAML 加载与 Draft202012Validator.evolve，不增加 helper、依赖或抽象 |
| project-validation | 修改后 | 适用；执行三组限定回归、YAML 与引用检查、内存烟测、task 解析及范围／格式检查 |
| Code Readability Review／独立 review | check | 主会话自核手写测试；公共契约独立复核不由 writer 冒充，本轮不启动子代理或 advisor，交付停在 checking，不声明独立复核通过 |

## 验证与剩余边界

- 三组命令均在 `/workspace/640-skills-contract-errors` 原生执行一次，exit 0、OK；基线计数为 79，新增两项契约测试后 runtime 与根包装各为 81，二者覆盖重叠，不累计为独立用例总数。
- 实际解释器 Python 3.13.5（GCC 14.2.0）；CI 用 3.12.10，本地未在 3.12 实测。临时测试夹具通过启动器 `TMPDIR=/tmp/contract-error-bodies-tmp` 隔离；不在本工作树执行 Git 写操作。

| 命令 | exit | 测试数／原生耗时 | 命令墙钟耗时 | 本地证据 stem |
|---|---|---|---|---|
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_golden_contracts test_r1_acceptance -v` | 0 | 81 tests，0.627s，OK | 0.775s | `/tmp/contract-error-bodies-runtime` |
| `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_runtime_r1_acceptance -v` | 0 | 81 tests，0.669s，OK | 0.811s | `/tmp/contract-error-bodies-wrappers` |
| `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_onboard_multi_projects tests.test_sbtd_task_sync_git` | 0 | 73 tests，61.758s，OK | 61.969s | `/tmp/contract-error-bodies-workflow` |

- 每个 stem 对应 raw `.json` 与同 stem 中文汇总 `.md`，保留实际命令、stdout／stderr、exit、时间、SHA、分支、工作树与 Python 版本。Final Test Report／Run Summary MD=generated；Targeted Rerun=not-needed；Final Full Rerun=passed，仅上列限定测试范围。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/contract-error-bodies-smoke.py`：临时脚本，已删除，结果文件保留（`/tmp/contract-error-bodies-smoke.txt`／`.md`）；exit 0。YAML 解析成功，全部 152 个 `$ref` 可解析；从 serve.py AST 读取 18 个目标状态的字面量样本，实际调用 `_json` 序列化后均通过 DetailError，动态 detail 构造不在此样本计数内。
- 同一最小内存烟测：真实 SecurityMiddleware＋最小 Starlette／StaticFiles 路由，未认证未知 API 为 JSON 401，非法 Host 为 JSON 403，认证后未知 GET 为 text/plain 404，POST health 与认证后未知 POST 为 text/plain 405，示例 endpoint 未捕获异常为 text/plain 500 `Internal Server Error`。没有调用 create_app、监听 socket、创建 runtime home 或启动 renderer；这是框架／构造函数烟测，不是完整业务服务或真实导出作业实测。来源与方案中的最小探针分开记录。
- `ruff check --no-cache sbtd-runtime/tests/test_golden_contracts.py`：exit 1，既有 :19-30 导入块 I001；本轮不改该块，不夹带格式整理。该失败独立保留，不宣称全部检查绿；三组 unittest 均无失败，不因 lint 重跑或削弱测试。
- `git diff --stat`：三个已跟踪文件合计 102 insertions、2 deletions（OpenAPI 46 行、测试 52 行、文档新增 6 行）；新 task 未跟踪，不计入 stat。`git diff --check` exit 0、输出空；`git status --short --untracked-files=all` 恰四个授权文件。

- `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/contract-error-bodies-check.py`：临时脚本，已删除，结果仅记录于此；exit 0。与 HEAD 比较确认 OpenAPI 仅有授权语义变化；五个原 description、Conflict、422／503／507 块逐字节保留，:378-379 不变；安装文档无原行删除／改写；既有测试除 download 映射外逐字保留，额外 I001 所在导入块也与基线相同。四文件 LF、末尾 LF、无尾随空白，限制文字扫描无命中；三组 raw／汇总的计数、命令与九节顺序检查通过。
- 修改后位置：`sbtd-runtime/contracts/openapi.yaml:699-700` 下载引用；:806-837 五个通用 response 与保留的 Conflict；Unauthorized 原 description 现为 :813，Gone 原 description 现为 :833；:838-849 ExportNotReady；:953-964 DetailError。测试新增 :688-736；安装文档仅新增 :208-213。
- Code Readability Review：主会话完成；新增测试按 response 名称分组，复用 setUpClass 文档与 evolve 引用解析；正例使用当前 handler body，负例覆盖缺 detail、null／整数类型、非对象及额外字段，不增加 description 快照或新 helper。现有精确响应集合仍保护 get／delete 无 409。
- 本轮最小烟测 raw／中文汇总为 `/tmp/contract-error-bodies-smoke.txt`／`.md`；lint 失败保留于 `/tmp/contract-error-bodies-lint.txt`。一次性 runner／烟测／检查脚本交付前移除，保留报告，不清理已有资产。
- 解析命令如下；转态前实测输出 `in-progress False 1 None`，exit 0、stderr 空。时间取自真实 `TZ=Asia/Shanghai date +%Y-%m-%dT%H:%M:%S+08:00`；限定验收通过后追加 checking，completed_at 保持 null，额外 lint I001 不隐瞒、不宣称全面通过。

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" ai/tasks/v2.1.0-rc.2-contract-error-bodies/task.md
```

- Evidence Source=developer-local；Source Revision=dirty；Environment Alignment=unverified；Evidence Publication=local-only。rtk=skipped-for-report，使用原生命令保留输出；不是新提交／PR head 的 CI 证据。
- BDD=skipped，无新增运行行为，不新建场景或 .feature，语言检查不适用；Cross-repo context=not-needed；API Contract=verified（本地 schema、引用与样本）；Mock Strategy=none（新增永久测试无 mock），内存框架探针的示例 endpoint 单独限定为 smoke-only。
- 未运行 CI、全仓套件、完整 HTTP 服务、renderer、前端构建／浏览器或移动端；未在 Python 3.12 实测，无运行代码／前端变化。公共契约独立复核未执行，本轮保持 checking，不标 done；提交、推送与开 PR 由编排方执行。生成器新类型名对仓外消费者的影响未知；恢复仅涉及四份契约／测试／文档记录，无数据迁移，临时证据不保证长期保留。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | 产出 | 会话文件 |
|---|---|---|---|---|---|
| 1 | ping（2026-10-26 15:20:02 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-26T07-20-02-004Z_01a17714-9cd4-7468-863b-2fac0e66ff8a.jsonl` |
| 2 | 会话 1（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），待后续回填 | 契约、测试、文档与本 task | `2026-10-26T07-20-16-247Z_01a17714-d477-76b5-84f3-10025911e7ab.jsonl` |

每个 omp 会话一行；未使用子代理与 advisor；内部辅助 model_usage（如有）由群内交付报告另列。会话文件名仅经 ls 目录列表取得，未读取 jsonl 内容。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-26T15:21:16+08:00 | planned | in-progress | 编排方整理；写入者：主会话，开始 strict 契约错误体修订 | HEAD 与 origin/main 均为 `3b5497b360b1325a4ca95c262665d59832cd7c31`；入口干净，分支匹配，四路径及父路径无 symlink／逃逸，ignore 检查 exit 1、输出空；已核对方案 a／c／f、当前源码与参考 task。 |
| 2026-10-26T15:29:53+08:00 | in-progress | checking | 编排方整理；写入者：主会话，契约／测试／文档修订与限定验收验证完成，进入检查 | 三组回归 81／81／73 tests 均 OK、exit 0；152 个引用解析与 18 个真实构造样本通过，最小内存烟测通过；原 description、Conflict、422／503／507 与既有断言保留，安装文档只新增；diff --check exit 0，恰四个授权文件，LF／文字检查通过；转态前解析 in-progress False 1 None，转态后核对 checking False 2 None；额外 lint 仍有基线 I001，CI 与独立复核未执行，completed_at=null。 |
| 2026-10-26T16:00:51+08:00 | checking | done | 编排方整理；写入者：主会话，Reviewy CLEAN 后写入 done；PR #188 | Reviewy CLEAN 对应 SHA dd89434a5e7831aa533aa03c63c4c4e9226444c2（640 群），CI run 40287229883 13/13 success |
