---
schema_version: 1
id: v2.1.0-rc.1-secret-key-match
workflow_mode: strict
mode_source: user
mode_note: 用户本次明确要求 strict 模式，并要求在 ai/tasks/ 写任务记录。
status: "checking"
branch: fix/v2.1.0-rc.1-secret-key-match
created_at: '2026-10-16T21:27:57.232291+08:00'
updated_at: "2026-10-16T21:33:38.710651+08:00"
completed_at: null
---
收紧事件库扩展字段的敏感名判断：`_secret_key` 不能只做去分隔符后的精确名匹配。`github_token`、`x-api-key`、`X-Api-Key`、`authToken` 当前会入库。

未完整调用 grill-with-docs。用户已固定匹配词、反例和单测名单，PRD v0.2 的扩展字段禁令与既有拒绝入库行为没有未决产品问题。不把拒绝改成掩码，不回填已入库事件，不改 schema。

## 范围

- 只改 `sbtd-runtime/event_store.py` 的敏感名判断，以及对应场景、单测、未发布变更日志。
- 大小写不敏感。先把 `-`、`_` 和驼峰切成段，再按段后缀或段子串匹配 `token`、`secret`、`password`、`passwd`、`api_key`、`apikey`、`authorization`、`cookie`、`credential`、`private_key`。既有 `bearer` / `oauth` 仍作为后缀命中，不放宽成任意子串。
- 计数字段不脱敏：`token_count`、`tokens`、`input_tokens` 仍可入库。
- 命中后仍是整条事件 `secret-rejected`，不写 spool，不改值。已入库记录不回扫。

## 验收

- `github_token`、`x-api-key`、`X-Api-Key`、`authToken`、`client_secret` 被拒绝且值不落盘。
- `token_count`、`input_tokens` 被接受且值仍在重放中。`tokens` 同样保留，作为计数边界。
- 既有 `api_key` / `clientSecret` 拒绝、非敏感 `note`、开关关闭路径不变。
- 相关测试与 ruff 全绿。提交、推送、开 PR 到 main，不合并。

## 测试 seam

公开 seam 仍是 `EventStore.append` / `replay`。断言结果状态、`secret-rejected` 和重放是否含该值。不单测私有表。用户已点名这些键，不另开 seam 确认。

## Book Gate Plan

| Reviewer | 客观触发／阶段 | Lifecycle | 谓词与结果 |
|---|---|---|---|
| book-ddd-distilled-modeling | 领域术语或上下文歧义，需求确认前 | before-dev | not-needed。未完整 grill。脱敏在本库就是拒绝入库，不是新边界。 |
| book-ddia-data-design | 持久化写入过滤，设计确认前 | before-dev | confirmed。见正文。不改 schema、所有权或恢复算法。 |
| book-legacy-change-safety | 既有敏感名判断过窄，改行为前 | before-dev | characterized。改前复现见正文。安全网是既有拒绝测试加本轮红测。 |
| book-refactoring-pass | 既有生产代码编辑前 | before-dev | proceed。只替换匹配谓词，不先重构。 |
| book-release-readiness | 生产运行时／部署，验证后 | finish | not-needed。无服务、作业、队列、集成、发布或迁移。 |
| TDD | 高风险隐私过滤 | implement | 先红后绿。 |
| gherkin-bdd | 可观察拒绝行为 | before-dev | traceable。源仓不建 .feature。场景补在 `sbtd-runtime/spec/r1.2a-event-store-scenarios.md`。 |
| ponytail | 实现选型 | implement | stdlib 分段，不新依赖，不回扫旧库。 |

## DDIA Data Design Review

Status: confirmed

Data owner and source of truth: 已接受事件仍只属于 `audit.db` 的 events 表。本改动不新增表，不改 `schema_version`。

Write / read / async / failure paths: `append` 在写 spool 之前拒绝敏感扩展名。`_recover` 对已落盘行再判一次，命中则记 `secret-rejected` 并不提交该事件。读取仍是 `replay`。无跨进程队列。

Consistency model: 单进程读己之写。不变。

Idempotency / ordering / retry / deduplication: 去重键不变。被拒绝的事件不进入去重账。

Schema / migration / backfill / rollback / replay: 无迁移、无回填。已经接受的旧事件不改写。回滚是还原本提交，不删历史行。

Observability and repair: 拒绝仍记 quality `secret-rejected`。不新增指标。

Required tests: 点名的前缀／驼峰／连字符键被拒绝且不落盘；`token_count` 与 `input_tokens` 被接受并出现在重放中。

## Legacy Change Safety Review

Status: characterized

Behavior to change: 去分隔符后的精确名匹配漏掉 `github_token`、`x-api-key`、`X-Api-Key`、`authToken`、`private_key`。

Behavior to preserve: `api_key`、`API_KEY`、`client_secret`、`clientSecret`、`token`、`password`、`authorization`、`cookie` 仍拒绝。`token_count`、`input_tokens`、`tokens`、`note` 仍接受。顶层未知字段仍是 schema 拒绝。开关关闭不建库。

Current reproduction evidence: 改生产代码前，对当前 `_secret_key` 的直接复现：`github_token`/`x-api-key`/`X-Api-Key`/`authToken`/`private_key`/`secret_key` 为 False；`API_KEY`/`client_secret`/`api_key`/`clientSecret` 为 True；`token_count`/`input_tokens`/`tokens`/`note` 为 False。用户名单里的 `API_KEY` 与 `client_secret` 已被现有精确集命中，本轮仍须保持拒绝。

Safety net: 既有 `test_extension_secret_is_not_persisted`。新增公开 seam 红测覆盖点名键和计数边界，先失败再改匹配。

Hidden dependencies / seam: 无新生产 seam。`append` 与 `_recover` 都调用 `_secret_extension`。

Validation plan: 红测证明漏报，再改谓词，然后跑 `sbtd-runtime/tests` 与 ruff。

Review mode: normal

## Refactoring Review

Status: proceed

Review mode: normal

Existing-code scope: `sbtd-runtime/event_store.py` 的 `_secret_key`。

Behavior that must remain unchanged: 非敏感扩展可入库；已命中的精确名仍拒绝；不写 spool 的拒绝路径不变。

Structural friction: 无。精确集合放不下前缀名，换成同一函数内的分段谓词即可。

Decision and smallest safe step: no refactor needed。

Safety net and validation: 既有扩展拒绝测试加本轮红测。

Deferred refactors: 不把敏感名表抽成配置文件，不把拒绝改成掩码。


## 验证

- 红：`test_prefixed_secret_names_are_rejected_and_counters_stay` 在改匹配前失败，`github_token` 被接受。
- 绿：`python3 -B -m unittest discover -s sbtd-runtime/tests` 72 ok。`python3 -B -m unittest tests.test_sbtd_runtime_r1_event_store tests.test_sbtd_runtime_r1_facade` 31 ok。
- ruff 0.17.1：`check` 与 `format --check` 对 `event_store.py` 和 `test_event_store.py` 通过。PATH 无 ruff，使用本机 uv cache 的 0.17.1。`rtk`：not-available for ruff；测试用原生 unittest，skipped-for-report。
- 未跑三平台 CI。PR head 的 CI 才是远端证明。

## Ponytail Review

`event_store.py` 词表曾有两份。已收成一段表，后缀由 `"".join(term)` 派生。剩余两段判断分别覆盖粘连词（`accesstoken`）和段中子串（`secret_key`），不能再并成一个 `endswith`。Lean already. Ship.

## Code Readability Review

`_secret_parts` 只做切段。`_secret_key` 先排除 `count` / `counts` 尾段，再做后缀和段子串。注释写明 `tokens` 不是 `token`。测试按场景名断言拒绝码、落盘和重放值。未改 vendor。

## Release Readiness Review

Status: not-needed

无服务、作业、队列、外部集成、发布或迁移。本地库过滤变严，不改变打开、恢复或 schema。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-16T21:28:04.307641+08:00 | planned | in-progress | secret-key misses are reproduced; add the failing public-seam test before changing the matcher | pre-change _secret_key: github_token/x-api-key/X-Api-Key/authToken/private_key False; API_KEY/client_secret True; token_count/input_tokens/tokens False |
| 2026-10-16T21:33:38.710651+08:00 | in-progress | checking | prefixed secret names are rejected and counter fields still replay | python3 -B -m unittest discover -s sbtd-runtime/tests (72 ok); tests.test_sbtd_runtime_r1_event_store and tests.test_sbtd_runtime_r1_facade (31 ok); ruff 0.17.1 check/format passed |
