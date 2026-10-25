---
schema_version: 1
id: v2.1.0-rc.2-contract-scope-wording
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：本轮采用 strict，仅新增 scope_checks 现状说明与本 task；主会话为两个授权文件唯一 writer 与验证 controller，不启动子代理、不使用 advisor；提交由编排方执行。
status: done
branch: docs/v2.1.0-rc.2-contract-scope-wording
created_at: '2026-10-25T21:37:23+08:00'
updated_at: '2026-10-25T22:18:53+08:00'
completed_at: '2026-10-25T22:18:53+08:00'
---

# rc.2：x-sbtd-auth scope 现状说明

## 决定

- 用户 2026-10-25 14:28 群内确认（scope 按推荐：方案 2，只写现状，PRD :1634/:837 不动，触发条件记入本 PR 的 task.md），Lord 记录。括号内为编排方整理的概括，不作为原话引用。
- Lord 2026-10-25 21:34 群内裁定（确认候选 A、键名 scope_checks、新增同级扩展键、保留 declarative、保留 at most one session）。候选 B（更短的写法）未采用。
- 在 `x-sbtd-auth` 新增同级扩展键 `scope_checks`，只写现状；本句不作未来承诺。
- 未完整调用 grill-with-docs：插入文本、范围与验收明确，源码和测试可直接核对，无新增领域歧义。
- 编排方整理：E（v2.1.0-rc.2 预发布）保持暂停，本项计为新增需求。

## 范围与边界

仅两个文件：`sbtd-runtime/contracts/openapi.yaml` 原第 22 行之后插入一行；新建 `ai/tasks/v2.1.0-rc.2-contract-scope-wording/task.md`。不改 PRD、spec、测试、代码、plan.md、index 或其他 task。

```diff
+    scope_checks: serve.py issues, stores, and checks no scopes; x-sbtd-scopes is declarative, each process pairs at most one session, and that session bearer alone authenticates /api/v1 requests other than health and pairing.
```

Python 读取 `/workspace/640-contract-scope-verify/insert-line.txt`，去掉末尾 LF 后按字节计算插入候选及编辑补丁；编辑工具直接消费生成的补丁，不手抄。保留 4 空格缩进、LF、末尾换行与其余全部字节，无尾随空白。

当前工作树逐项复核，以下证据行号与基线 `745564a` 初查一致：

- `sbtd-runtime/serve.py:192-195`：`pair()` 建立的 session 只有 csrf 与 expires_at；`:516` 响应体只有 token_type／access_token／expires_in，不签发或存储 scopes。
- `SecurityMiddleware` 在 `serve.py:392-396` 只检查 Host／Origin；`:403-406` 检查 bearer；`:407-412` 检查不安全方法的 CSRF；`:413` 将 session 传给下游，无 scope 校验。bearer alone 指身份认证，不免除 Host／Origin 与 CSRF 检查。
- `git grep -n 'x-sbtd-scopes'`（exit 0）表明，除 openapi.yaml 外，非测试代码不读取该键；唯一读取为 `sbtd-runtime/tests/test_r1_acceptance.py:192-205`（实际读取在 `:201`）。Python safe_load 解析 YAML，26 个 operation 声明该键。
- 一次性票据由 `AccessControl.__init__` 在 `serve.py:165` 生成一次；任何配对尝试在 `:185-186` 读后销毁；启动路径每个进程在 `:809` 只创建一个 `AccessControl()`。测试 `sbtd-runtime/tests/test_serve.py:317` 验证成功后不能再次配对，`:359` 验证失败也销毁票据。
- `_AUTH_EXEMPT_PATHS` 在 `serve.py:371` 仅列 health 与 pairing；`:398` 实际检查 `/api/` 前缀，覆盖说明中的 `/api/v1`。测试 `test_serve.py:400` 验证 health 无需 session，`:458` 验证 API 的 bearer 与 CSRF。
- openapi.yaml 原 `:378` 的 “The browser session does not hold this scope”（ingestEvents）与现状一致，不改；`serve.py:691-711` 未路由 ingestEvents。
- openapi.yaml 原 `:808` 的 “Missing credential or scope” 不矛盾，不改；serve.py 的 401 只来自 bearer 缺失／无效／过期（`:403-406`，有效期检查在 `:198-207`）和配对失败（`:511-513`），scope 分支当前不可达，合约描述的是超集。本 PR 行号顺延：`:378→:379`、`:808→:809`。
- 仅记录、不处理：`docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md:837` 写「无凭证／scope 不足 → 401／403」，openapi 合并为 401，属于既有差异。PRD `:1634` 的最小 scope 与 `:837` 均不动。
- 未来触发条件（编排方整理）：出现第二种凭证类型时，需先决定 scope 的签发与校验。
- 沿用参考 task 的手写记录，不调用 TaskStore 写入，不写 active／handoff／ignore／身份；仅以 TaskDocument 解析验证，不承诺 TaskStore 自动恢复。不提交、不推送、不安装依赖；临时文件仅放 `/tmp`。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮判定与证据 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求前 | not-needed；未完整 grill，仅澄清既有实现 |
| book-ddia-data-design | 数据 schema／迁移／跨进程机制设计前 | not-needed；仅新增说明扩展键，不改数据 schema 或签发机制 |
| book-legacy-change-safety | 既有行为修改前 | not-needed；不改行为，基线字节比较保护其余内容 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；已读取适用边界，无生产代码编辑或结构摩擦 |
| book-release-readiness | 运行时／部署变化，验证后 | not-needed；无运行时、部署或发布变化，E 仍暂停 |
| gherkin-bdd／TDD | 用户可见行为或状态机制变更前 | not-needed；不改行为、场景或任务状态机制，仅使用既有记录格式 |
| project-validation | 文档落盘后 | 适用；执行限定字节、YAML、回归、task 解析与文字扫描 |
| Code Readability Review | 手写代码／测试编辑后 | not-needed；未编辑代码或测试 |
| 独立 review | 授权说明／公共合约检查 | 未执行；主会话自核不冒充独立审查，不启动子代理或 advisor，记录停在 checking，不声明 strict 全流程或发布完成 |

## 验证与剩余边界

- 入口 `pwd && git rev-parse --show-toplevel && git branch --show-current && git rev-parse origin/main && git status --short --untracked-files=all`：exit 0，根目录及分支匹配，工作树干净；HEAD 与 origin/main 均为 `745564a3924f5b650aeaa2c3ae607da2f96143cf`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B -c <路径、基线、插入候选及 operation 计数检查>`：exit 0；两路径及全部父路径无 symlink／逃逸，新 task 不存在，openapi 原文等于 origin/main。内部 `git check-ignore --no-index <两个授权路径>` exit 1、stdout／stderr 空；26 个 operation 声明 scopes；原文 38822 字节，候选 39049 字节。
- 开始时间由 `TZ=Asia/Shanghai date +%Y-%m-%dT%H:%M:%S+08:00` 实际取得，exit 0，不倒填群内决定时间。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/contract-scope-validate.py checks`：exit 0；openapi 等于 origin/main 原文仅在原第 22 行后插入外部文件的一行，1128→1129 行，LF、末尾换行和原 `:378`／`:808` 文本不变。内部 `git diff -U0 -- sbtd-runtime/contracts/openapi.yaml` 为 +1／0 删除；`git diff --check` exit 0、输出为空；`git status --short --untracked-files=all` exit 0、恰两个授权文件。task 禁词／主目录路径／无日期时间归因／带 x 分钟／错误裁定归因／常见密钥格式扫描 0 命中，正文人工核对无密钥。
- YAML 真实解析命令（exit 0、stderr 空）：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -c "import yaml; d=yaml.safe_load(open('sbtd-runtime/contracts/openapi.yaml')); a=d['info']['x-sbtd-auth']; print(len(a), list(a))"
```

输出：`6 ['loopback', 'pairing', 'long_term_token', 'csrf', 'host_origin', 'scope_checks']`。openapi-spec-validator 由编排方另行检查，结果见群内交付报告。

以下命令由仓库外 runner 顺序、分别运行，各一轮；无失败或重试：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest sbtd-runtime/tests/test_golden_contracts.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest sbtd-runtime/tests/test_r1_acceptance.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest sbtd-runtime/tests/test_renderer_integration.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest sbtd-runtime/tests/test_exports_http.py
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_sbtd_task_document tests.test_sbtd_task_legacy_events_notice tests.test_sbtd_task_recovery tests.test_sbtd_task_routing tests.test_sbtd_task_schema tests.test_sbtd_task_state tests.test_sbtd_task_status_sync tests.test_sbtd_task_sync_git
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest test_serve.PairingTests.test_pair_once_only_and_ticket_never_in_output test_serve.PairingTests.test_wrong_ticket_unauthorized_and_destroys test_serve.HostOriginAndApiTests.test_health_needs_no_session test_serve.HostOriginAndApiTests.test_api_requires_bearer_and_csrf
```

| 选集 | exit | 原生结果 |
|---|---|---|
| test_golden_contracts | 0 | Ran 63 tests in 0.326s；OK |
| test_r1_acceptance | 0 | Ran 16 tests in 0.323s；OK |
| test_renderer_integration | 0 | Ran 35 tests in 81.910s；OK (skipped=3) |
| test_exports_http | 0 | Ran 9 tests in 33.561s；OK |
| 八模块任务回归 | 0 | Ran 135 tests in 50.430s；OK |
| 真实 HTTP 鉴权冒烟 | 0 | Ran 4 tests in 4.672s；OK |

- 实际数量共 Ran 262，包含 3 skips；golden 与 R1 合计 79，分别为 63／16。renderer 原生输出未逐例列出 skip 原因，不据源码推定本轮原因；配额警告及 renderer 失败场景输出保留在 raw 报告，不等于 unittest 失败。任务回归中的「旧格式事件，不追溯」来自既有回归用例，不是新 task 解析结果。
- HTTP 冒烟启动真实 serve.py，验证首次配对 200、重用和错误票据 401、错误尝试销毁票据、health 无凭证 200、metrics/catalog 缺凭证 401／有效 bearer 200、statistics/query 缺失或错误 CSRF 403，且凭证不泄露到输出。E2E Mode=backend-only；Mock Strategy=none。renderer 选集保留既有渲染 mock，不称 full-stack。
- task 真实解析命令：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" ai/tasks/v2.1.0-rc.2-contract-scope-wording/task.md
```

- 转 checking 前解析 exit 0、stderr 空，输出路径后为 `in-progress False 1 None`；转 checking 后同一解析命令 exit 0、stderr 空，输出 `checking False 2 None`，解析前后文件字节不变。全部限定验证完成后，真实 date 命令取得 `2026-10-25T21:43:52+08:00`，exit 0；updated_at 等于最后事件时间，completed_at=null。
- runner 命令 `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/contract-scope-validate.py tests` exit 0。六份 native/raw JSON 与同 stem 中文汇总保留于 `/tmp/contract-scope-s1-reports/`；stem 为 `test_golden_contracts`、`test_r1_acceptance`、`test_renderer_integration`、`test_exports_http`、`task-regression`、`auth-http-smoke` 各加 `-docs_v2.1.0-rc.2-contract-scope-wording`，后缀 `.json`／`.md`。本地 Python 报告一致性检查 exit 0，核对六对文件、九节顺序、命令、SHA、计数与占位符；该辅助命令的字符串转义产生一条 SyntaxWarning，不影响上述测试结果。
- 环境：本地 Linux x86_64、Python 3.13.5。rtk=skipped-for-report，使用原生命令保留输出；Final Test Report=generated；Run Summary MD=generated；Targeted Rerun=not-needed；Final Full Rerun=passed，仅指上述选集并保留 3 skips。
- BDD=traceable，沿用既有测试；未改 .feature 或持久场景文本，语言检查不适用。API Contract=verified（字节、解析与现有契约回归，不包含 openapi-spec-validator）；Cross-repo context=not-needed。
- Evidence Source=developer-local；Source Revision=dirty；Evidence Publication=local-only；Environment Alignment=not-needed。不证明 CI、PR head、合入或发布。未运行 lint／format／build、全仓测试或浏览器／移动端验证，因仅限定说明与记录变更；独立审查未执行。临时报告不保证长期保留；只保存本 task，不承诺自动恢复。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | 产出 | 会话文件 |
|---|---|---|---|---|---|
| 1 | ping（2026-10-25 21:35:33 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-25T13-35-33-726Z_01a17346-0f5e-7363-8bcc-2dff75f8977c.jsonl` |
| 2 | 会话 1（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告 | x-sbtd-auth 插入一行与本 task | `2026-10-25T13-36-11-648Z_01a17346-a380-7416-8caf-5144b0168ed6.jsonl` |

每个 omp 会话一行；未使用子代理、advisor；内部辅助 model_usage 记录（如有）由群内交付报告另列。本会话文件名仅通过会话目录文件名列表核对，未读取 jsonl 内容。

编排方整理，按 jsonl 统计：会话 1 实际为 26／59。上方第 2 行的「未知」写法原样保留。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-25T21:37:23+08:00 | planned | in-progress | 编排方整理；写入者：主会话，开始 scope_checks 单行插入与本 task 建立 | 基线 `745564a`；入口干净，分支匹配，两路径及 ignore 安全；证据行号一致，26 个 operation 声明 scopes。 |
| 2026-10-25T21:43:52+08:00 | in-progress | checking | 编排方整理；写入者：主会话，单行说明与限定验证完成，进入检查 | 基线 `745564a`；字节 +1／0 删除、LF、保护行、两文件范围与文字扫描通过；YAML 6 键；63／16／35（3 skips）／9／135／4 tests 均 OK、exit 0；task 解析 exit 0、stderr 空；openapi-spec-validator 由编排方另行检查。 |
| 2026-10-25T22:18:53+08:00 | checking | done | 编排方整理；写入者：主会话，Reviewy CLEAN 后写入 done；PR #183 | Reviewy CLEAN @ 615138acca222026d376d47165ed515a99dc78d9（编排方整理）；CI validation run 40199543723 attempt 1 success 13/13（编排方整理） |
