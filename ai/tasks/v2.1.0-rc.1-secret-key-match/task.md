---
schema_version: 1
id: v2.1.0-rc.1-secret-key-match
workflow_mode: strict
mode_source: user
mode_note: 用户本次明确要求 strict 模式，并要求在 ai/tasks/ 写任务记录。
status: "done"
branch: fix/v2.1.0-rc.1-secret-key-match
created_at: '2026-10-16T21:27:57.232291+08:00'
updated_at: "2026-10-16T21:48:46.971166+08:00"
completed_at: "2026-10-16T21:48:46.971166+08:00"
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

## Reviewy nested-key blocker

未完整调用 grill-with-docs。Reviewy blocker 与 nit 已固定嵌套拒绝、计数放行和复数 cookie。没有新的领域歧义。PRD v0.2 原先允许扩展里的小对象，已于 2026-10-16 按用户决定修订为标量-only；最终结果是扩展值保持标量-only（string ≤256、number、boolean、null），嵌套对象和数组被 schema 拒绝且不入库，递归敏感扫描保留为纵深防御。不改 schema_version，不回填，不把拒绝改成掩码。

开放项已解决（2026-10-16 用户决定）：修订 PRD v0.2 为标量-only 表述，与最终 schema 一致；不另开契约 PR 允许嵌套。文档修订在 `docs/v2.1.0-rc.1-prd-scalar-extensions` 分支。

BDD：沿用 `sbtd-runtime/spec/r1.2a-event-store-scenarios.md`。场景正文中文，关键词英文。源仓不建 .feature。Cross-repo context：not-needed。Mock Strategy：none。

### Book Gate Plan（本轮）

| Reviewer | 客观触发／阶段 | Lifecycle | 谓词与结果 |
|---|---|---|---|
| book-ddd-distilled-modeling | 无完整 grill，无新边界 | before-dev | not-needed |
| book-ddia-data-design | 嵌套扩展值被 schema 拒绝，不入库 | before-dev | confirmed |
| book-legacy-change-safety | 嵌套键漏检 | before-dev | characterized |
| book-refactoring-pass | 既有生产代码 | before-dev | proceed |
| book-release-readiness | 无服务或迁移 | finish | not-needed |
| TDD | 隐私过滤 | implement | 先红后绿 |
| gherkin-bdd | 可观察拒绝／放行 | before-dev | traceable |
| ponytail | 实现选型 | implement | 迭代遍历，不新依赖 |

### DDIA Data Design Review

Status: confirmed

Data owner and source of truth: 已接受事件仍只属于 `audit.db`。不新增表，不改 `schema_version`。

Write / read / async / failure paths: `append` 仍先过 schema，再走 `_secret_extension`。任一层键命中则 `secret-rejected`，不写 spool。嵌套对象和数组在 schema 阶段被拒绝且不入库；递归扫描保留为纵深防御。读取仍是 `replay`。`_recover` 对已落盘行再判一次。

Consistency model: 单进程读己之写。不变。

Idempotency / ordering / retry / deduplication: 去重键不变。被拒绝的事件不进入去重账。

Schema / migration / backfill / rollback / replay: 扩展值只允许标量（string ≤256、number、boolean、null）；嵌套对象和数组被 schema 拒绝。无迁移、无回填。已接受的旧事件不改写。超过深度 32 的未扫描层按敏感拒绝，避免漏检后落盘。

Observability and repair: 拒绝仍记 `secret-rejected`。不新增指标。

Required tests: 嵌套 `github_token`、列表中的 `x-api-key` 与嵌套 `input_tokens` / `max_tokens` 都被 schema 拒绝且不落盘；`cookies` / `set_cookies` 被拒绝；顶层 `max_tokens` 被接受。

### Legacy Change Safety Review

Status: characterized

Behavior to change: `_secret_extension` 只看 extensions 第一层键，漏掉嵌套 `github_token` 和列表里的 `x-api-key`。`cookies` / `set_cookies` 不被拒绝。

Behavior to preserve: 顶层既有敏感名仍拒绝。`token_count`、`input_tokens`、`tokens`、`max_tokens`、`note` 仍接受。校验仍在密钥检查之前。开关关闭不建库。

Current reproduction evidence: 改生产代码前，嵌套 github_token 的 append 结果是 schema-rejected，不是 secret-rejected；`cookies` 被接受。`max_tokens` 顶层已放行。

Safety net: 既有扩展拒绝测试。新增公开 seam 红测先失败再改遍历和扩展值 schema。

Hidden dependencies / seam: 无新生产 seam。`append` 与 `_recover` 都调用 `_secret_extension`。

Validation plan: 红测证明漏报，再改遍历、复数 cookie 和扩展值 schema，然后跑 `sbtd-runtime/tests` 与 ruff。

Review mode: normal

### Refactoring Review

Status: proceed

Review mode: normal

Existing-code scope: `_secret_extension` 与扩展值 schema。

Behavior that must remain unchanged: 非敏感顶层扩展可入库；已命中的精确名仍拒绝；schema 校验仍在密钥检查之前。

Structural friction: 无。一层 `any` 换成迭代遍历即可。

Decision and smallest safe step: no refactor needed。

Safety net and validation: 既有拒绝测试加本轮红测。

Deferred refactors: 不把深度上限做成配置，不回扫旧库。

## 验证（本轮）

- 红：`test_nested_extension_secrets_are_rejected_and_counters_stay` 失败，结果是 schema-rejected。`test_cookie_plurals_are_rejected` 失败，`cookies` 被接受。`max_tokens` 在改代码前已由既有计数测试放行。
- 绿：`python3 -B -m unittest discover -s sbtd-runtime/tests` 74 ok。`python3 -B -m unittest tests.test_sbtd_runtime_r1_event_store tests.test_sbtd_runtime_r1_facade` 33 ok。
- ruff 0.17.1：`check` 与 `format --check` 对 `event_store.py` 和 `test_event_store.py` 通过。`rtk` 存在但不能启动 ruff（PATH 无 ruff），回退本机 uv cache 的 0.17.1。测试用原生 unittest，skipped-for-report。
- 未跑三平台 CI。PR head 的 CI 才是远端证明。不合并。

## Ponytail Review（本轮）

迭代栈加深度 32，不新依赖。`cookies` 只加一个段，不把所有复数都剥掉，否则 `tokens` 会被误伤。扩展值用一份 `$ref`，不复制两套 anyOf。Lean already. Ship.

## Code Readability Review（本轮）

`_secret_nodes` 只遍历 dict 和 list。注释写明深度失败关闭，以及为什么不把 `tokens` 当 `token`。测试按场景名断言拒绝码、落盘和重放值。未改 vendor。

## Release Readiness Review（本轮）

Status: not-needed

无服务、作业、队列、外部集成、发布或迁移。扩展值形状变宽，不改变打开、恢复或 `schema_version`。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-16T21:28:04.307641+08:00 | planned | in-progress | secret-key misses are reproduced; add the failing public-seam test before changing the matcher | pre-change _secret_key: github_token/x-api-key/X-Api-Key/authToken/private_key False; API_KEY/client_secret True; token_count/input_tokens/tokens False |
| 2026-10-16T21:33:38.710651+08:00 | in-progress | checking | prefixed secret names are rejected and counter fields still replay | python3 -B -m unittest discover -s sbtd-runtime/tests (72 ok); tests.test_sbtd_runtime_r1_event_store and tests.test_sbtd_runtime_r1_facade (31 ok); ruff 0.17.1 check/format passed |
| 2026-10-16T21:34:11.291544+08:00 | checking | done | secret key matching is broadened and the pull request is open, not merged | https://github.com/KunoLu/640-skills/pull/132 head 13b557bbdf5573997bec04b9234b1f7a09044db5; sbtd-runtime tests 72 ok; ruff 0.17.1 passed |
| 2026-10-16T21:45:16.789772+08:00 | done | planned | Reviewy blocker: nested extension keys bypass secret rejection; cookie plurals are not blocked | pre-change _secret_extension False for nested github_token and list x-api-key; schema ValidationError on those objects and on nested input_tokens/max_tokens; _secret_key False for cookies/set_cookies/max_tokens and True for cookie/set_cookie |
| 2026-10-16T21:45:22.101626+08:00 | planned | in-progress | nested secret miss is reproduced; add the failing public-seam test before changing the walker | append path validates schema before _secret_extension, so nested objects are schema-rejected today and are not secret-rejected; flat cookies and set_cookies are accepted |
| 2026-10-16T21:48:41.630056+08:00 | in-progress | checking | nested secret keys are rejected, cookie plurals are rejected, and nested counters still replay | python3 -B -m unittest discover -s sbtd-runtime/tests (74 ok); tests.test_sbtd_runtime_r1_event_store and tests.test_sbtd_runtime_r1_facade (33 ok); ruff 0.17.1 check/format passed |
| 2026-10-16T21:48:46.971166+08:00 | checking | done | nested extension secret scan is on the same pull request branch and is not merged | https://github.com/KunoLu/640-skills/pull/132 not merged; sbtd-runtime tests 74 ok; wrapper tests 33 ok; ruff 0.17.1 passed |
