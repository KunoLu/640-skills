---
schema_version: 1
id: v2.1.0-rc.2-contract-5-5-wording
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：本轮采用 strict，仅同步三处合约措辞并建立本 task；主会话为三个授权文件唯一 writer 与验证 controller，不启动子代理、不使用 advisor；提交由编排方执行。
status: done
branch: docs/v2.1.0-rc.2-contract-5-5-wording
created_at: '2026-10-25T20:10:08+08:00'
updated_at: '2026-10-25T20:57:45+08:00'
completed_at: '2026-10-25T20:57:45+08:00'
---

# rc.2：5.5 合约措辞同步

## 决定

- 用户 2026-10-25 14:19 群内确认（5.5 按推荐：1a、2a+3a），Lord 记录。括号内为编排方整理的概括，不作为原话引用。
- Lord 2026-10-25 20:06 群内裁定（确认三处范围）。
- 同步 5.5 合约措辞：info.summary 说明 info 级 contract-only 的含义；DiskQuotaExceeded 描述与场景文档说明 serve.py 已映射 HTTP 507（PR #167）。
- 未完整调用 grill-with-docs：范围、替换文本与验收明确，源码和测试可直接核对，无新增领域歧义。

## 范围与边界

恰好三个文件：

1. `sbtd-runtime/contracts/openapi.yaml`：A 仅追加第 5 行 summary，B 仅替换第 899–900 行；第 6、895、898 行不变。
2. `sbtd-runtime/spec/r1.0-contract-scenarios.md`：C 仅替换第 187 行；第 142、185–186 行不变。
3. `ai/tasks/v2.1.0-rc.2-contract-5-5-wording/task.md`：本 strict 记录，最终 checking、completed_at=null。

Python 读取仓库外 A-append.txt、B-old.txt、B-new.txt、C-old.txt、C-new.txt，按字节计算替换；经编辑工具落盘，不手抄素材。两文件行数、LF、末尾换行及其余字节保持。

A

```diff
-  summary: "Contract draft for v2.1.0-rc.1. serve.py serves the operations it routes over local HTTP; operations marked x-sbtd-implementation: library have only in-process Python library surfaces under sbtd-runtime/. R1.4 acceptance pins event schema 1.0, QueryScope schema_version 1.0, and CSV export_schema_version 1.1; exports* stay v2.1.0-rc.2."
+  summary: "Contract draft for v2.1.0-rc.1. serve.py serves the operations it routes over local HTTP; operations marked x-sbtd-implementation: library have only in-process Python library surfaces under sbtd-runtime/. R1.4 acceptance pins event schema 1.0, QueryScope schema_version 1.0, and CSV export_schema_version 1.1; exports* stay v2.1.0-rc.2. The info-level x-sbtd-implementation: contract-only marks this document as the contract source; it does not state that no operation is implemented."
```

B

```diff
-        snapshot write is refused by the shared quota; HTTP mapping is deferred
-        to the follow-up implementation PR.
+        snapshot write is refused by the shared quota; serve.py maps it to HTTP
+        507 with this body (PR #167).
```

C

```diff
-  queryStatistics 的 HTTP 507 映射留后续小实现 PR，不证明当前服务已返回 507。
+  queryStatistics 的 HTTP 507 映射已由 serve.py 实现（PR #167），由 test_exports_http.ExportHttpTests.test_statistics_snapshot_quota_refusal_and_reuse 追踪。
```

当前工作树逐项核对，行号均与初查一致：

- `sbtd-runtime/serve.py:526-547`：statistics_query 对非法 JSON／scope 返回 400；捕获 DiskQuotaExceeded 返回 507，正文为 detail、used_bytes、quota_bytes。
- `sbtd-runtime/report_snapshot.py:891` 复用已有快照，先于 `:894` 的 self.quota.admit。
- `sbtd-runtime/disk_quota.py:154-165`：admit 在 80% 阈值仅 logging 警告，超额抛 DiskQuotaExceeded。
- `sbtd-runtime/tests/test_exports_http.py:68-105`：ExportHttpTests.test_statistics_snapshot_quota_refusal_and_reuse 断言非法 scope 400、超额 507 及三字段正文，不创建快照、不删除未知文件。
- `ai/tasks/v2.1.0-rc.2-r2.2-statistics-507-impl/task.md:139` 记录了 openapi.yaml:898–900 与场景文档 :185–187 仍写 deferred。
- 说明一：`openapi.yaml:895` 的「log-only / presentation handling belongs to R2.2」略显过时（`disk_quota.py:158-163` 已仅记录日志），本 PR 有意不改。
- 说明二：Python safe_load 解析 OpenAPI、ast 解析 serve.py Route 显式 methods；共 28 个 operation，`serve.py:691-711` 路由 11 个（按方法计，不计框架自动 HEAD），4 个标 library，其余 13 个既未路由也未标 library，本 PR 不处理。
- 不改 plan、index、其他 task、代码或测试。沿用参考 task 的手写记录，不调用 TaskStore 写入，不写 active／handoff／ignore／身份，不承诺 TaskStore 自动恢复。不提交、不推送；临时文件仅放 /tmp。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮适用性与证据 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义，需求前 | not-needed；未完整 grill，既有含义明确 |
| book-ddia-data-design | schema／迁移／持久化机制设计前 | not-needed；仅描述措辞，不改 schema 或数据机制 |
| book-legacy-change-safety | 既有行为修改前 | not-needed；不改行为，以基线字节比较保护原文 |
| book-refactoring-pass | 生产代码编辑前 | not-needed；无生产代码修改 |
| book-release-readiness | 运行时／部署变化，验证后 | not-needed；无运行时、部署或发布变化 |
| gherkin-bdd | 持久场景说明同步／check | 适用；沿用中文正文、英文关键词，只改说明行；既有契约测试与真实 HTTP 测试追踪，不扩大为全仓同步 |
| project-validation | 文档落盘后 | 适用；运行限定字节、YAML、回归与 task 解析检查 |
| Code Readability Review／独立 review | check | not-needed；无代码或测试编辑，无接口结构变化；主会话核对，不冒充独立审查 |

## 验证与剩余边界

- 入口命令 `pwd && git rev-parse --show-toplevel && git branch --show-current && git rev-parse origin/main && git status --short --untracked-files=all`：exit 0，分支、根目录匹配，工作树干净。HEAD 与 origin/main 均为 `7feada29d7a4fdd096199b987dfeee91f9d49f6b`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/contract-5-5-prepare.py`：exit 0，三个路径及全部父路径无 symlink／逃逸，目标原文等于基线、新 task 不存在；内部 `git check-ignore --no-index <三个授权路径>` exit 1、stdout／stderr 空。操作计数 28／11／4／13；两文件 1128／194 行。
- 开始时间由 `TZ=Asia/Shanghai date +%Y-%m-%dT%H:%M:%S+08:00` 实际取得，exit 0；不倒填群内决定时间。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/contract-5-5-validate.py checks initial`：exit 0；两文件分别等于 origin/main 原文仅做 A／B／C 替换，行数 1128／194、LF、末尾换行与受保护行不变；新增行与 task 全文的禁词、路径、无日期时间归因、模糊分钟及密钥格式扫描 0 命中。内部 `git diff --check` exit 0、输出为空；`git status --short --untracked-files=all` exit 0，恰三个授权文件。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B -c "import yaml; yaml.safe_load(open('sbtd-runtime/contracts/openapi.yaml'))"`：exit 0、stdout／stderr 空。openapi-spec-validator=skipped，模块未安装，不安装。
- 以下命令由仓库外 runner 顺序执行，各一轮、exit 0，无失败或重试：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest sbtd-runtime/tests/test_golden_contracts.py sbtd-runtime/tests/test_r1_acceptance.py sbtd-runtime/tests/test_renderer_integration.py sbtd-runtime/tests/test_exports_http.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests python3 -B -m unittest test_exports_http.ExportHttpTests.test_statistics_snapshot_quota_refusal_and_reuse
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_sbtd_task_document tests.test_sbtd_task_legacy_events_notice tests.test_sbtd_task_recovery tests.test_sbtd_task_routing tests.test_sbtd_task_schema tests.test_sbtd_task_state tests.test_sbtd_task_status_sync tests.test_sbtd_task_sync_git
```

- 原生结果依次为 `Ran 123 tests in 124.388s`、`OK (skipped=3)`；`Ran 1 test in 4.319s`、`OK`；`Ran 135 tests in 55.339s`、`OK`。组合选集未逐例输出 skip 原因，不据源码推定本轮原因；既有 renderer mock／可选真实浏览器用例不等同于全真实浏览器验证。
- 独立用例启动真实 serve.py，覆盖 `POST /api/v1/statistics/query` 的 400／507／200、detail／used_bytes／quota_bytes、拒绝不创建快照、等于上限允许及超额后的已有快照复用；另验证 `GET /api/v1/report-snapshots/{snapshot_id}` 返回 200。BDD=run，API Contract=verified；E2E Mode=backend-only；独立用例 Mock Strategy=none（仅通过既有夹具配置配额）；组合套件保留既有 mock，不称 full-stack。
- 真实 task 解析命令如下；转 checking 前 exit 0、stderr 空，输出路径后字段为 `in-progress False 1 None`，解析前后字节不变：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" ai/tasks/v2.1.0-rc.2-contract-5-5-wording/task.md
```

- 原始报告与同 stem 中文汇总保留于 `/tmp/contract-5-5-s1-reports/`，测试 stem 分别为 `runtime-docs_v2.1.0-rc.2-contract-5-5-wording`、`quota-http-docs_v2.1.0-rc.2-contract-5-5-wording`、`task-regression-docs_v2.1.0-rc.2-contract-5-5-wording`（`.json`／`.md`）。环境为本地 Linux x86_64、Python 3.13.5；runner 命令为 `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/contract-5-5-validate.py tests`，exit 0。Final Test Report=generated；Run Summary MD=generated；Targeted Rerun=not-needed；Final Full Rerun=passed，仅指上述选集，保留 3 skips 边界；Environment Alignment=not-needed。
- 全部限定验证完成后，再由真实 date 命令取得 `2026-10-25T20:16:36+08:00`（exit 0），进入 checking；updated_at 等于末事件时间，completed_at=null。临时报告不保证长期保留。
- Evidence Source=developer-local，Source Revision=dirty，Evidence Publication=local-only；不作为 CI／PR head／合入／发布证明。rtk=skipped-for-report，使用原生命令保留输出。Cross-repo context=not-needed；不运行 lint／format／构建、全仓测试或浏览器／移动端验证，因仅限定文档改动。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | 产出 | 会话文件 |
|---|---|---|---|---|---|
| 1 | ping（2026-10-25 20:08:14 +08:00 开始） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-25T12-08-14-824Z_01a172f6-1ee8-7285-8233-37feec564da2.jsonl` |
| 2 | 会话 1（本会话） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），实际计数见群内交付报告 | 三处措辞同步与本 task | `2026-10-25T12-08-54-424Z_01a172f6-b998-701e-9c46-4300f85617d6.jsonl` |

每个 omp 会话一行；未使用子代理、advisor；内部辅助 model_usage 记录（如有）由群内交付报告另列。本会话文件名仅通过会话目录文件名列表核对，未读取 jsonl 内容。

编排方整理，按 jsonl 统计：会话 1 实际为 22／44；其后 ping2 为 1／0，会话 2 为 12／19，二者均为 openai-codex/gpt-6-astra（high），上表未单列。上方第 2 行的「未知」写法原样保留。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-25T20:10:08+08:00 | planned | in-progress | 编排方整理；写入者：主会话，开始三处措辞同步与本 task 建立 | 基线 `7feada2`；入口干净、分支匹配、路径与 ignore 安全；实现证据行号一致，operation 计数 28／11／4／13。 |
| 2026-10-25T20:16:36+08:00 | in-progress | checking | 编排方整理；写入者：主会话，三处措辞同步与限定验证完成，进入检查 | 基线 `7feada2`；字节、行数、换行、保护行及三文件范围检查通过；文字限制 0 命中；YAML 解析 exit 0；123 tests OK（3 skips）、独立 HTTP 1 test OK、任务回归 135 tests OK；task 解析 exit 0、stderr 空；openapi-spec-validator 未安装，skipped。 |
| 2026-10-25T20:57:45+08:00 | checking | done | 编排方整理：Reviewy CLEAN 后写入 done；PR #182 | Reviewy CLEAN @ 38e287248dead1d16ffb0d098ae764d60ca3e966（编排方整理）；CI validation run 40192819927 attempt 1 success 13/13（编排方整理） |
