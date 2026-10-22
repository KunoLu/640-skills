---
schema_version: 1
id: v2.1.0-rc.2-disk-cap-error-contract
workflow_mode: strict
mode_source: user
mode_note: 用户明确 strict、CONTRACT-ONLY；主会话唯一 writer／验证 controller；恰好三个本地 commit，仅显式 git add；不 push／PR／评论／merge／rebase／amend，不改其他 worktree 或全局配置，不暂存禁止路径或 reports。
status: done
branch: contract/v2.1.0-rc.2-item4-disk-cap-error-contract
created_at: '2026-10-22T18:56:12+08:00'
updated_at: '2026-10-22T19:10:57+08:00'
completed_at: '2026-10-22T19:10:57+08:00'
---

# rc.2 计划第 4 项：磁盘上限拒绝错误契约

## 范围与验收

入口 HEAD／origin/main 为 `6c344d13ddf6b49882b87d52300b8d697e8aeec4`（#157）；工作根 `/workspace/640-skills-item4-errc`。用户授权五条路径、三个本地提交：先回填 plan／ADR task，再仅提交 OpenAPI／golden tests，最后提交本记录。task index 按 rc.2 惯例不改。未完整调用 grill-with-docs：PRD §10.4、ADR 0003 §4／§5 与用户验收边界明确，不重开需求。

只定义同步拒绝契约，不实现清扫、计量、HTTP handler、库异常或 CLI。沿用 #152／#153／#154 的 response 引用与 OpenApiDraftTests／Draft202012Validator seam，不增加依赖或其他测试文件。

```gherkin
Scenario: 清扫后共享占用超限时拒绝新建
  Given snapshots/ 与 exports/ 清扫后共占用 2000000001 字节且有效配额为 2000000000 字节
  When 客户端处理新建快照或任一格式导出的配额拒绝
  Then 契约声明 507 且 body 仅含 detail DISK_QUOTA_EXCEEDED、used_bytes 与 quota_bytes
  And 导出在 202 前拒绝，没有 job、export_id 或本次文件
  And 快照在 201 前拒绝，库等价操作也不得创建本次文件
  And 不淘汰未过期数据，不把拒绝记入 ExportJob.error

Scenario: 返回解析后的有效配额而不是固定默认值或原始配置
  Given 有效配额已调整为 4000000000 字节且清扫后占用为 4000000001 字节
  When 客户端校验配额拒绝错误体
  Then 两个字节字段为整数且 quota_bytes 不固定为默认值
  And 缺字段、错误码、非法类型、负数、零配额或额外原始环境字段均不合法

Scenario: 恰等配额不是拒绝条件
  Given 清扫后共享占用恰等有效配额
  When 判断是否因共享配额拒绝新建
  Then 不因配额拒绝且不预留尚未生成的产物大小
  And 已有 ID 复用与幂等回放不是新建，其优先级不由本契约重定义
```

前两场景的响应映射／schema 由 golden tests 验证；第三场景、清扫顺序与无副作用为 ADR／契约描述边界，R2.2 才实现并验证，不冒充本次运行证据。JSON Schema 不能跨字段比较 `used_bytes > quota_bytes`。

## 待定项／Review flags

### Proposed values for user decision

1. **错误码字符串 `DISK_QUOTA_EXCEEDED`**：沿用既有 UPPER_SNAKE 与 `detail` const；因 snapshots/ 与 exports/ 共用，不用只表示导出的 `EXPORT_` 前缀；与 ADR 配置名 `SBTD_RUNTIME_DISK_QUOTA_BYTES` 的 quota 术语一致。
2. **HTTP 507 Insufficient Storage**：按 [RFC 4918 §11.5](https://www.rfc-editor.org/rfc/rfc4918.html#section-11.5)，服务端无法存储完成请求所需表示；区别于既有 503 `EXPORT_RENDERER_UNAVAILABLE` 依赖不可用，避免混淆为 Retry-After 等待；413 针对请求载荷而非小型创建请求；422 `EXPORT_IMAGE_SIZE_LIMIT` 是请求特定输出缺陷；409 既用于幂等 payload／资源状态冲突，不如 507 明确表示共享存储配额。这是 proposed value，待用户决定，不宣称最终批准。
3. **body 字段名 `detail`、`used_bytes`、`quota_bytes`**：沿用 #153／#154 封闭错误体与 `detail`；`_bytes` 与 `max_edge_px`／`max_total_pixels` 及既有 `byte_count` 的单位显式命名一致。used_bytes 为 ADR 清扫后 st_size 总量 U，quota_bytes 为生效上限 L；只回数字，不回显原始环境变量字符串。

预警决定项：`5 × U >= 4 × L` 的 80% 预警不定义 `meta.warnings` 新码；本契约按 log-only／R2.2 边界登记，最终呈现渠道仍由 R2.2 决定，不宣称已有日志实现。非法 `SBTD_RUNTIME_DISK_QUOTA_BYTES` 的启动拒绝属于进程／CLI，OpenAPI 不覆盖；本次不定义启动错误码。默认 2000000000 字节是 ADR 当前值，不以 const／enum／maximum 冻结。

## Book Gate Plan

| Gate | 客观触发／阶段 | 状态 |
|---|---|---|
| book-ddia-data-design | wire schema／共享容量拒绝边界，稳定设计前 | confirmed；已加载并输出 DDIA Data Design Review；数据所有权不变，同步拒绝与异步作业失败分离，无迁移，不改幂等优先级。 |
| book-ddd-distilled-modeling | 完整 grill／领域歧义 | not-needed；未完整 grill，沿用已批准领域边界。 |
| book-legacy-change-safety | 既有运行行为修改 | not-needed；不改 runtime，已有 validator seam。 |
| book-refactoring-pass | 已读路由，生产代码修改 | not-needed；声明式 schema 与测试，无需重构。 |
| book-release-readiness | runtime／部署／发布变化 | not-needed；契约领先实现，不能宣称发布就绪。 |
| TDD／gherkin-bdd／ponytail | 消费者契约变化／before-dev 与 check | confirmed；中文场景／英文关键词；基线红灯、当前 golden 绿灯、真实 schema 消费者 smoke；复用既有结构。Ponytail Review：无新抽象、依赖或可删业务逻辑，保留每类非法值边界；无需重构。 |
| 独立 review／可读性 | 公共契约与测试边界／check | correct；QuotaContractReview、QuotaEvidenceReview 均无 findings；只读、不运行验证，主会话唯一 writer／controller。 |
| project-validation | 用户指定命令／check | 完成指定 golden／runtime suite、消费者 smoke 与格式检查；既有 import I001 如实保留；不运行根 native CI。 |

## 验证证据

- 已读 PRD §10.4、ADR 0003 §4／§5、plan 第 4 项、rc.2 两条 task 先例及 `git show 650c336`、`9fc31f8`、`c7a87e4`、`ce80ca2`、`d46d4ad`。#157 mergedAt 与主会话最终 34／62 采用用户已核实事实；`git show -s --format=%cI 6c344d1` 实际为 `2026-10-22T18:36:02+08:00`。
- 首 commit 前 Python／MarkdownIt／PyYAML 消费者 smoke 通过：Markdown 可渲染、frontmatter 可解析、时间是合法 +08:00 日历时间；旧 ADR task 的历史事件逐字不变，仅追加一条 closeout；两个 reviewer 行逐字不变。
- 验证在授权 worktree 根、Linux／Python 3.13.5 运行，原生命令附加 `PYTHONDONTWRITEBYTECODE=1 RUFF_NO_CACHE=true`。报告位于本任务 ignored `reports/`：每个 stem 都有 raw `.json` 与九节中文 `.md`，保存命令／stdout／stderr／退出码／时间／HEAD／环境／契约与测试 SHA-256。全部 `Evidence Source: developer-local`、`Source Revision: dirty`、`Evidence Publication: local-only`、`Environment Alignment: unverified`；不把当时 HEAD `92d6a35` 当新 PR-head CI 证明。

| 命令 | 实际结果 | 报告 stem |
|---|---|---|
| `python -B -c <baseline YAML red script>` | exit 1（预期）；3 tests，0.046s，2 failures／1 error；两个 507 映射缺失与 DiskQuotaExceeded 不存在 | baseline-red |
| `python -B -m unittest sbtd-runtime/tests/test_golden_contracts.py -v` | 首轮 exit 0；59 passed，0.341s | golden-green |
| `python -B -c <contract consumer smoke script>` | exit 0；两个创建入口分别消费默认／非默认配额 JSON round-trip，拒绝多余 export_id；撤去本次新增项后 YAML 结构等于基线 | contract-smoke |
| `python -B -m unittest discover -s sbtd-runtime/tests` | 首轮 exit 0；372 tests，362 passed／10 skipped，107.665s | runtime-full |
| `ruff format --check sbtd-runtime/tests/test_golden_contracts.py` | 首轮 exit 1：新增 required 断言需换行；修正后 exit 0，1 file already formatted | format-check／format-final |
| `ruff check sbtd-runtime/tests/test_golden_contracts.py` | exit 1；仅既有 19–30 行 import I001，未触及该 import block，不重跑确认已知问题 | lint |
| `python -B -m unittest sbtd-runtime/tests/test_golden_contracts.py -v` | 格式修正后最终 exit 0；59 passed，0.336s | golden-final |
| `python -B -m unittest discover -s sbtd-runtime/tests` | 格式修正后最终 exit 0；372 tests，362 passed／10 skipped，109.171s | runtime-final |

基线红灯从 `git show origin/main:sbtd-runtime/contracts/openapi.yaml` 读入 TemporaryDirectory，在进程内替换测试模块 OPENAPI；不改工作树契约、不 stash／reset。原始完整脚本在报告 command 中，临时目录自动清理。新增两个永久测试及既有 createExport 精确集合更新只测试消费者契约，不测试源码措辞或 runtime mock 回声。

smoke 从两个 response 引用实际解析 schema，经 JSON 编码／解码验证 `{detail, used_bytes, quota_bytes}`，拒绝额外 export_id；`U > L` 在有效示例由独立消费者断言，而相等值能通过字段 schema，明确这不是应发拒绝的证明。撤去两个 507 引用、新 response，并恢复唯一 ExportJob.error 描述后，与基线 YAML 解析结构相等：其 enum、Meta.warnings 和其他契约未变。

手写测试可读性复核：使用原有 unittest／subTest，非法类型含 string、非整数、bool、null；分别保护 used_bytes 的 0 下界和 quota_bytes 的 1 下界，非默认配额高于默认值，防止意外冻结。格式修正只改变断言换行，未改变行为；最终两个 suite 覆盖修正后的内容。runtime 默认输出不提供逐例 skip 名称，本记录只报告原生 10 skips，不猜原因。套件与轮次重叠，不累计通过数。

`BDD: traceable`（本 task 中文场景／英文关键词；无新增 .feature／runner）；`Cross-repo context: contract-only`；`API Contract: verified`（schema，不是 live quota）；`E2E Mode: contract-backed`；`Mock Strategy: none`（新增用例）；`rtk: skipped-for-report`。`Final Test Report`／`Run Summary MD: generated`；`Targeted Rerun: passed`；`Final Full Rerun: passed` 仅指用户指定 runtime suite，不是根 CI。根 native CI 明确不运行；无新增配额 HTTP／库副作用、浏览器、跨平台、真实容量校准或启动错误实测，均归 R2.2。无独立 OAS linter 配置证明，只采用既有 PyYAML／Draft202012Validator，不声称完整 OAS lint 或所有检查全绿。

| 最终被测文件 | SHA-256 |
|---|---|
| sbtd-runtime/contracts/openapi.yaml | 93d6f31a71e672dd0994e848ca70bf1ff7a5de0d49f62e0fe524bef56488084e |
| sbtd-runtime/tests/test_golden_contracts.py | 5ece73d9ab6c8f3d3503ccd771c049d7cc2d3e233fa241049df52d0b279b1b8f |

### 记录与报告诊断

本 task 与 ADR closeout 的 frontmatter／事件已用安装 Skill 的 `task-data.schema.json`、Draft202012Validator／FormatChecker 验证，Markdown 表可消费；Proposed values 列表恰好三项。九对报告均经 `git check-ignore` 确认 ignored；失败轮次保留。此为文档诊断，不是 TaskStore helper 生命周期证明。

### 独立审查

- QuotaContractReview：correct，confidence 0.95，无 findings；逐项对照 PRD／ADR、共享 507、接受前拒绝、library 等价语义、计量／阈值／不淘汰、幂等边界、warnings／startup 排除与 proposed values。区分创建前配额拒绝和 PRD §13.10 的生成中磁盘不足，不改作业失败 enum。
- QuotaEvidenceReview：correct，无 findings；核对 golden 边界、基线红灯方法、最终被测哈希、closeout 时间／事件／最终 34／62；确认只有新增断言换行的格式修正、最终两 suite 已覆盖修正内容，I001 在未改 import 区域。两位只读，没有执行测试、lint、build 或 formatter；不冒充外部 Reviewy CLEAN。

## 提交与恢复边界

入口工作区干净；五条授权路径逐级核对 containment／无 symlink；新 task 不受 ignore，reports 命中 `.gitignore:4:/ai/tasks/**/reports`。沿用前置 rc.2 task 已记录的 TaskStore catalog/frontmatter 限制，不重跑已知失败；helper active／index 写入超授权。以 edit/write 保存用户指定记录，不声称 TaskStore lifecycle 或自动恢复成功；不写 active、ignore、身份或模型配置。旧 ADR task 的分支仅为历史绑定，closeout 不重绑定。

撤回只涉及本地契约／文档提交，无数据迁移，不删除用户数据；后续消费者采用前须协调错误契约。local done 不等同 operator 提审／合并、R2.2 实现、部署或发布。

1. `92d6a35267da0c2946597d4bd03d4d4231405b33` — `docs(plan): backfill rc.2 item 4 ADR (#157 / 6c344d1) and close task record`，仅 plan 与 ADR task。
2. `0253f9f09038fb26bf55a51cd488cc3395c2eb26` — `contract(openapi): declare DISK_QUOTA_EXCEEDED 507 for snapshot/export creation (rc.2 item 4)`，仅 OpenAPI 与 golden tests。已提交 blob 的 SHA-256 与最终验证内容完全相等；这是内容身份核对，不冒称提交后的新 CI。
3. `docs(task): record rc.2 item 4 disk-cap error contract task`，仅本记录，自身 SHA 由最终 stdout 给出，避免自引用。

前两次提交均显式 `git add <paths>`，`git diff --check`／`git diff --cached --check` 退出 0；第三次同样仅暂存本 task。最终 log／stat／status 与五路径集合由提交后回执核对；报告、`.omp-r12b-addendum.txt`、`ai/tasks/codex-verify/` 均不暂存。没有新增需要单独身份记录的长期 lesson，不写 developer／lesson。

## 模型使用

| agent/session | provider/model | thinkingLevel (thinking_level_change) | assistant messages / toolCall blocks | purpose | resolvedModelIsFallback | title-generation count | job-widget entries |
|---|---|---|---|---|---|---|---|
| 主会话／01a16340-612d-7726-aebd-044ea7db772e | openai-codex/gpt-6-astra | high | 32 / 65（提交前 snapshot） | 唯一 writer、验证 controller | false | 未记录 / unknown | 未记录 / unknown |
| QuotaContractReview／QuotaContractReview.jsonl | kimi-code/k3 | max | 18 / 22（提交前 snapshot） | 只读配额契约语义复核 | false | 未记录 / unknown | 未记录 / unknown |
| QuotaEvidenceReview／QuotaEvidenceReview.jsonl | kimi-code/k3 | max | 21 / 34（提交前 snapshot） | 只读 golden／历史 closeout 证据复核 | false | 未记录 / unknown | 未记录 / unknown |

统计时间 `2026-10-22T19:10:57+08:00`，只读 Python `json.loads` 解析 `~/.omp/agent/sessions/--workspace-640-skills-item4-errc--/2026-10-22T10-55-25-997Z_01a16340-612d-7726-aebd-044ea7db772e.jsonl` 第 1–169 行及同 stem 目录的 QuotaContractReview 第 1–71 行、QuotaEvidenceReview 第 1–98 行。口径为 `type=message`／`role=assistant` 与其 `type=toolCall` blocks；均为截至提交前快照，不含后续记录、提交与最终输出，不是最终总数。

模型来自 message／model_change，thinking 明确来自 `thinking_level_change`；两 reviewer 的 session_init 另记录 `kimi-code/k3:max`。model_change 的 resolvedModelIsFallback 均为 false，未覆盖模型配置。各 JSONL 各有一个 title 条目，但条目不等于 title-generation request 次数，因此计数 unknown；未见 `type=model_usage`／customType 同名条目，不把缺记录填作 job-widget 0。此前 `01a1633f-0207-7690-b3d5-71c253e14c7c` 是 operator ASTRA_OK ping，不计入本任务主会话。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-22T18:56:12+08:00 | planned | in-progress | 用户 strict 与三提交授权；保存模式、场景、决定及 gate | HEAD／origin/main 6c344d13ddf6b49882b87d52300b8d697e8aeec4；路径安全；PRD／ADR／rc.2 先例；DDIA confirmed |
| 2026-10-22T19:06:10+08:00 | in-progress | checking | 回填已提交；基线红灯、schema smoke、最终指定 suites 通过，进入独立 review 与记录收口 | 92d6a35；golden 59／0.336s；runtime 372／10 skipped／109.171s；格式通过；既有 I001 保留 |
| 2026-10-22T19:10:57+08:00 | checking | done | 本地契约交付收口；前两个 commit 已完成，第三个仅保存本记录；两位独立 review 均无 findings，不等同提审／合并／实现／发布 | 0253f9f09038fb26bf55a51cd488cc3395c2eb26；golden 59 passed，runtime 372／10 skipped；schema smoke／格式通过，既有 I001 保留；被测哈希与提交 blob 一致；主会话提交前 snapshot 32／65 |
