---
schema_version: 1
id: v2.1.0-rc.5-dashboard-401-auto-repair
workflow_mode: strict
mode_source: user
mode_note: 640 在 11-11 群内确认 rc.5 全程用 strict；contract-only 范围由编排方整理，决策依据为 640 在群里决定 a甲 b同意
status: checking
branch: docs/v2.1.0-rc.5-dashboard-401-re-pair-contract
created_at: '2026-11-11T14:38:57+08:00'
updated_at: '2026-11-11T15:26:30+08:00'
completed_at: null
---

# Dashboard 401 自动重新配对：契约先行

## 目标与边界

编排方整理：本任务只交付 ADR 0001 §9、OpenAPI 新取票契约、双语 CHANGELOG 的 rc.5 未发布条目、本任务与生成的 index；状态为 checking，等待 Reviewy 安全评审、640 批准与 CI，不是实现完成或发布就绪。不改 serve、Dashboard 或既有 pair operation，不执行提交、推送、开 PR、部署、安装或工作流迁移。

未完整调用 grill-with-docs：编排方整理的范围、三个安全问题与验收命令已明确，源码可核对现状，不制造重复访谈。既有 §1–§7 正文逐字保留；§9 编号接并行契约 PR 的 §8，本基线尚无 §8，不代写该节。

`sbtd_task_state.py:450-451` 的显式模式来源为 `user`；该枚举是工具格式，不是将本方案细节归于 640。只保存本共享 task 和生成 index，不建立 active／handoff／developer 等其他记录。

## 决策来源

- 640 在群里决定 a甲 b同意。
- 编排方整理：决策消息日期为 2026-11-11，北京时间约 15:07；a甲对应先单独整理契约 PR，经 Reviewy 安全评审、640 批准后另开实现 PR。640 于同日 15:11 在群内确认 rc.5 全程用 strict；contract-only 范围、三个问题与具体安全方案由编排方整理。
- 编排方整理：沿用创建于 2026-11-11T14:38:57+08:00 的 default／planned 草稿事实，将任务改写为 strict／contract-only；草稿中的多次取票及三轮交换方案被本次一次签发规则替代。草稿是只读输入，不把其外部位置或会话位置写入仓库。

## strict 模式执行记录

- 第 2 轮沿用同一任务和绑定分支；先只读核对分支、基准 SHA、文件类型与 ignore 状态，再读 `sbtd-runtime/serve.py` 的鉴权／配对／路由、ADR 0001 §9、OpenAPI planned operation 和索引生成器源码，之后才写记录与 CHANGELOG。源码确认 serve 未路由新端点，日志不得暗示实现完成。
- 范围冻结：本轮只编辑 `CHANGELOG.md`、`CHANGELOG.zh.md`、本 `task.md`，并运行生成器写 `ai/tasks/index.md`；保留第 1 轮 ADR 0001／OpenAPI 契约，不改运行时、数据字典或 golden 测试，不添加其他 rc.5 PR 条目。
- strict 的 before-dev 按上述源码与 ADR、冻结范围和既有 Book Gate Plan 执行；check 使用原生指定命令，逐步运行索引写入、只读预览、golden 与状态／工作流测试，并检索 CHANGELOG 测试。每项实际结果补入下方第 2 轮验证证据；未执行项不记通过，历史失败原样保留。
- 状态仍为 checking，新增 checking→checking 事件记录本轮补齐，不伪造 done 或批准。独立安全评审仍交 Reviewy，任何必需项缺失均不得声称 CLEAN；作者自检不代替独立审查。
- 不 commit/push；提交、推送及 PR 由编排方处理。未调用 task 执行工具或子代理，未使用其他模型；仅使用主会话工具读取、编辑和验证文件，进度清单不承担任务执行或独立审查。
- 未完整调用 grill-with-docs：补齐项目、边界、文案与验证命令均已明确，源码和契约可回答本轮问题，不新增领域决策或重复访谈；完整 grill 后 DDD 门禁不适用。未编辑生产代码，重构、TDD、运行时／部署与真实浏览器门禁不适用；原契约 DDIA 结论沿用第 1 轮记录，不冒充本轮重新评审。
- finish-work 仅完成文件补齐与本地验证记录；不关闭前轮全量失败、Reviewy／640 批准或 CI 缺口，不把 contract-only 交付等同于实现、部署或发布就绪。

## 当前行为与源码依据

基准提交：`80f14263e7d8bc6ae84f04ba94218e4857fc8b8f`。以下为本轮核对的当前源码，不是新恢复流程的运行证据。

| 事实 | 当前依据 |
|---|---|
| 401 自动重新配对明确为延后项；导出退出而主轮询不因而停止 | `CHANGELOG.md:102`；该行引用 PR #186／#190，本轮未重新查询远端 PR |
| 导出只容忍轮询 409，其他错误退出；最多 40 次，间隔从 1 秒乘 1.5 到 5 秒；401 提示重启并配对 | `sbtd-runtime/dashboard/src/exportJob.ts:101-152`、`sbtd-runtime/dashboard/src/i18n.ts:148` |
| 主快照每 30 秒刷新，依次查询统计、快照与数据页，完整后整体替换 | `sbtd-runtime/dashboard/src/App.tsx:69,145-192` |
| 通用请求只抛 ApiError，不自动恢复；Bearer 与非 GET 的 CSRF 从 sessionStorage 读取 | `sbtd-runtime/dashboard/src/api.ts:116-169` |
| 启动 fragment 交换前清地址栏，短时会话存 sessionStorage | `sbtd-runtime/dashboard/src/api.ts:29-99`、`sbtd-runtime/dashboard/src/App.tsx:194-218` |
| 启动票默认 300 秒，会话默认 8 小时；pair 处理尝试即销毁票，鉴权时删除过期会话 | `sbtd-runtime/serve.py:64-65,160-208` |
| 当前 Host 检查 loopback 白名单和服务端口；Origin 缺失通过，现有解析只检查 scheme／hostname／port，不等于新契约的完整字符串同源检查 | `sbtd-runtime/serve.py:120-145` |
| health／pair 免 Bearer；其余 API 缺有效会话 401；Host／Origin／CSRF 拒绝 403，CSRF 头为 X-CSRF-Token；现有秘密比较尚非本方案要求的常量时间比较 | `sbtd-runtime/serve.py:180-208,371-415` |
| pair 使用 X-Pairing-Code，失败 detail=unauthorized，成功响应头 X-CSRF-Token | `sbtd-runtime/serve.py:518-526` |
| 当前路由无 re-pair-ticket，新增 OpenAPI 不代表已路由 | `sbtd-runtime/serve.py:710-734` |
| 启动票只经 fragment 或 SBTD_RUNTIME_HOME 内 0600 文件交付，访问日志关闭，不是页面随时可领取的票 | `sbtd-runtime/serve.py:740-763,828-846` |
| 既有安全决定与启动 fragment 例外 | `docs/adr/0001-v2.1.0-rc.1-r1.0-runtime-decisions.md:116-137`；`docs/adr/0002-v2.1.0-rc.2-r2.0a-dashboard-frontend-decisions.md:46-66` |
| pair 契约保留原字节；401／403 使用 DetailError，仅 detail 字段，不是 error.code | `sbtd-runtime/contracts/openapi.yaml:52-71`；`components.responses.Unauthorized/Forbidden`、`components.schemas.DetailError` |
| 数据字典不列 API 错误码，无需同步 | `sbtd-runtime/contracts/data-dictionary.md` 全文 |

## 契约要点（编排方整理，与 ADR §9 一致）

### 问题一：60 秒窗口与泄露风险

以同一 serve 进程内的恢复记录绑定原配对会话为授权依据：原 Bearer 与原 CSRF 同时常量时间匹配；Host 必须为 loopback 白名单加实际端口，Origin 必须完整等于对应 `http://<Host>`，无 userinfo／路径／query／fragment，缺失或 null 拒绝。来源是附加约束，不是匿名发票授权。

仅 `原 expires_at <= now < 原 expires_at + 60 秒` 有资格；未过期、撤销、未知、重启前及超窗凭证不可恢复。重试不延长窗口，重启清空。普通 API 对过期 Bearer 仍立即 401，不延长数据访问。每条人工配对链最多自动恢复成功一次，替代会话沿用默认 8 小时寿命但无再次恢复权。

同源 XSS 或同时取得 Bearer＋CSRF 且能构造合规来源请求的攻击者仍能在窗口内抢先利用；Host／Origin 不是秘密，短窗口及一次性只能限制损害，不能消除此风险。

### 问题二：与提前续期比较及结论

提前续期不接受过期凭证，安全面更小，活跃页面可平滑继续；但依赖计时器，后台节流、休眠和合盖会错过时刻，无限续期还会把 8 小时会话变相无期限，仍需链上限。

选择真实 401 后的 60 秒有界恢复，避免必须在到期前运行计时器，并复用 pair；代价是扩大过期秘密的有限授权窗口，长休眠与响应丢失仍须人工配对。提前续期只可未来独立评估，不在本 PR 范围。

### 问题三：防重放、错误码与网络失败

同一个过期凭证／恢复记录只能成功签发一张票：第一次签发即原子标已用，不等 pair 成功，不补发、不轮换。票绑定记录／链／进程，`expires_at = min(签发时刻 + 30 秒, 原会话 expires_at + 60 秒)`，有效期右端不含。票只通过现有 pair 的 X-Pairing-Code 交换；严格来源检查先执行，到达配对处理的首次恢复票交换尝试即消费待交换票据，成功或失败均不可重放。成功交换与新会话创建、链成功标记原子完成。

取票请求网络失败：服务端尚未签发才可重试；一旦签发，无论客户端是否收到或交换是否成功，都不能再换。超时无法证明未签发，结果不确定直接转人工，不盲重试、不查回秘密；pair 响应丢失也转人工。

| 情形 | HTTP | detail |
|---|---|---|
| 重复换票、超窗、未知／重启前／撤销／未过期凭证、无恢复资格或缺 Bearer | 401 | `unauthorized`（复用） |
| pair 票重复交换、过期、未知、缺失或错误 | 401 | `unauthorized`（复用） |
| 取票／恢复票交换的 Host 或完整 Origin 不符、缺 Origin | 403 | `forbidden`（复用） |
| 取票记录合格但缺 CSRF 或 CSRF 不符 | 403 | `forbidden`（复用） |
| 新取票端点进程预算耗尽 | 429 | `RE_PAIR_RATE_LIMITED`（唯一新增） |

错误体遵循 `DetailError`，401 共码避免细分未知／已用／过期记录，403 不暴露具体策略；不承诺隐藏全部时序／校验阶段差异。顺序为 Host／Origin → 进程限流 → Bearer／资格 → CSRF → 原子签发复核；表中结果服从此前置优先级，不引入 409／410。

限流：每进程任意滚动 60 秒最多接纳 10 次通过来源检查的取票请求进入凭证校验，错误凭证也计数；之后返回 429，不增加接纳数。单调计时，重启清零；Retry-After 为最早接纳请求退出窗口所需秒数向上取整，至少 1。每记录成功签发上限仍为 1，预算未耗尽时重复取票是 401。前端不自动重试 429，不延长窗口；恶意本机请求耗尽预算的可用性风险保留。

200 返回 `pairing_code`、UTC RFC 3339 `expires_at`、正数 `ttl_seconds`（可含小数，≤30）。取票所有响应及恢复票交换响应均 no-store。恢复票只在内存、响应体、请求头传递，不进 URL／日志／文件／浏览器存储；新短时会话可沿用 sessionStorage。ADR 0002 的启动 fragment 例外不扩展。

## 修订后的实现方案（后续实现 PR，尚未实现）

### 服务端

- 先经 Reviewy 安全评审和 640 批准本契约，再改 AccessControl／SecurityMiddleware／路由；新路径专用恢复校验，不扩大匿名豁免，不把过期 session 继续留作数据访问凭证。
- 保存独立的短时恢复记录及链资格；普通 authenticate 到期删除活跃 session 时保留必要恢复信息至原窗口结束。使用同一进程内的原子状态转移，确保首次签发即耗尽记录、首次交换即消费票、成功链只恢复一次。
- 新增一次性票的签发、精确期限、进程预算、no-store 与错误映射；常量时间比较秘密，严格完整来源检查只应用于新恢复路径，不把当前弱一些的解析描述成已经满足要求。
- 维持初次启动票据和已有 pair 请求／响应格式；恢复票也经 pair 交换，恢复票交换的严格来源要求和 no-store 须在后续实现测试中覆盖。

### 前端识别、合流与恢复

- API 层按 HTTP status 接管已携带会话的受保护请求 401；统计 POST、快照／数据页 GET、capabilities、导出创建／状态／下载／取消纳入。health、初次 pair、取票自身不递归触发；403／404／410／普通网络错误不冒充会话过期。
- 同标签页 single-flight 合并并发 401；记录会话代次，迟到的旧 401 不清除新会话。恢复期间暂停主轮询和导出轮询，保留画面、筛选和展开状态，明确提示未刷新。
- 旧凭证只在当前恢复流程内存中使用，移除旧 sessionStorage；成功一次替换新会话，失败清空临时秘密。不广播到其他标签页。
- 单个网络请求超时 5 秒，总恢复流程最多 30 秒且不得越过服务端窗口；最多一次签发、一次交换。仅能确认尚未发送／服务端尚未签发时，才在上述期限内重试取票；不再使用“三轮取票／交换”的草稿方案，未知 5xx 或网络结果不确定均转人工。
- 成功后主视图只启动一轮完整刷新；数据页重放使用原 snapshot_id，完整后才整体替换。原请求最多重放一次。
- 导出 POST 保留原 Idempotency-Key、完整载荷和 snapshot_id；查询／下载／取消保留 export_id 和 key。404／410 提示对象不存在／过期，不偷换快照，不创建新作业；原 40 次导出查询上限不因恢复清零。取消／卸载中断恢复，不复活操作，不重复触发下载。
- 中英文提示恢复中、已恢复或需要人工配对，不再提示第 N/3 次；失败停止自动请求，不反复弹窗，给出重启 serve 后重新配对步骤。

## 不做的范围

编排方整理：不做运行时或 Dashboard 实现、匿名取票、无限续期、提前续期、跨重启恢复、跨标签页广播、长期 token 下发、refresh token、后台 daemon。不能绕过 Host／Origin／CSRF 来提高恢复成功率。不改快照 TTL、导出渲染、业务错误语义或数据持久化，不承诺旧作业跨重启恢复。

不改数据字典（无错误码目录）或现有 golden 断言。第 1 轮未改 CHANGELOG；第 2 轮补充双语 rc.5 未发布节，各仅一条本契约记录。可选的契约形状测试不新增：第 1 轮一次性本地检查验证新 operation、精确响应集合、planned 标记、schema 边界与 pair 原字节，避免将源码拷贝／文字锁定做成永久测试。

## Strict Book Gate Plan 与审查边界

| Gate | 触发条件／阶段 | 本轮结论与证据 |
|---|---|---|
| DDD | 完整 grill 后或领域歧义稳定前 | not-needed：未完整 grill；会话、恢复记录、票据、链的边界在 ADR §9 明确；domain-modeling 用于 ADR 术语整理 |
| DDIA | 跨请求恢复状态、一次性签发／交换；契约稳定前 | confirmed（本轮设计自审，非独立安全批准）：所有者为同进程内存，无持久化；原子签发／消费，窗口不可滑动，网络不确定转人工；并发／时间／重启场景见测试计划 |
| Legacy safety | 既有高风险行为修改前 | not-needed：本轮不改生产行为；后续实现必须先建立过期鉴权与 pair 保留行为证据 |
| Refactoring | 生产代码编辑前 | not-needed：没有生产代码编辑，不顺带重构 |
| Release readiness | 运行时／部署变化及发布前 | not-needed：仅 proposed 契约，未实现、未部署、未发布 |
| 独立安全评审 | 授权／身份契约；合并及实现前 | pending：Reviewy 未执行；不使用本轮作者自审代替 |
| 批准与 CI | 契约获准、后续实现准入 | pending：640 批准与 CI 尚无本轮证据，保持 checking |

BDD：本轮为契约设计，未变更可执行行为，不新增 .feature 或测试框架；下列场景是后续实现计划，须按项目既有 Markdown 场景规范落实并映射定向测试。新行为 BDD／真实浏览器验证本轮 skipped，原因是 serve 尚未路由且本轮禁止实现。Cross-repo context：contract-only；Mock Strategy：none。代码可读性审查不适用（无手写代码变更），ADR／OpenAPI／任务已按状态边界分层。

## 测试计划（实施时执行，以下不是本轮通过证据）

| 场景 | Given / When / Then | 拟用验证 |
|---|---|---|
| 到期边界与访问隔离 | Given 原会话及配对链，When now 在原到期前、恰到期、+60 秒前／恰+60 秒，Then 仅半开恢复窗口可取票，普通 API 到期即 401 | `test_serve` 定向测试，可控时钟 |
| 来源与秘密绑定 | Given 同进程记录，When Bearer／CSRF 错误、Origin 缺失／null／异端口／异主机／含路径、Host 不符，Then 按优先级 401／403，不签发 | `test_serve` 安全测试 |
| 一次签发及重放 | Given 一个合格过期记录，When 并发取票／重复取票，Then 仅一个 200，其余 401；When 票重复交换／到期，Then 401，无第二会话 | `test_serve` 并发、单次消费测试 |
| 一次链上成功与重启 | Given 自动恢复后的替代会话或旧进程凭证，When 再到期／新进程取票，Then 401、人工配对；人工建立新链才能恢复资格 | `test_serve` 生命周期测试 |
| 网络结果不确定 | Given 取票已签发或 pair 已消费，When 响应丢失／超时／取消，Then 不重发票、不重放票、不查回秘密，转人工；仅确定未签发可重试 | 前后端故障注入与 API 层测试 |
| 限流及秘密保护 | Given 滚动窗口，When 第 11 个合规来源请求到达，Then 429 与 Retry-After；不滑动恢复窗口，不落 URL／存储／日志，所有取票结果 no-store | `test_serve` 隔离 runtime home 与捕获日志，不打印秘密 |
| 401 合流与迟到响应 | Given 多个受保护请求与旧代次响应，When 同时 401，Then 一次恢复，旧 401 不删新会话；其他状态和递归路径不触发 | Dashboard `npm test` 定向测试 |
| 原操作恢复及取消 | Given 主快照／导出原 ID 和 key，When 恢复成功或取消／卸载，Then 最多重放一次，不重复作业／下载，不换 snapshot，不复活取消，保留查询次数上限 | Dashboard 测试、`test_exports_http` |
| 真实页面路径 | Given 缩短测试会话寿命的真实 serve，When 主轮询及导出遇到期，Then 观察恢复／人工退出、旧数据提示和秘密不泄漏 | 真实 serve＋浏览器 smoke；不是仅 mock 或契约检查 |

## 验收标准

### 本契约轮

- ADR §9 明确回答三个问题，原 §1–§7 不改，§8 留给并行 PR。
- OpenAPI 仅新增 planned 取票 operation 及必要组件；声明 Bearer／X-CSRF-Token／严格来源、200 字段与 no-store、精确 401／403／429；所有原 operations 尤其 pair 不变。
- 一次签发、一次链上成功、时间边界、错误码复用、网络不确定、限流与人工回退在 ADR／OpenAPI／本任务一致。
- strict 记录保留草稿创建时间与事件，index 仅生成新增一行；指定本地验证结果如实记录，失败不隐藏。
- 双语 CHANGELOG 在 rc.4 之前各有一个 rc.5 未发布节、一个新增小节与一条对应契约记录；明确未实现、serve 未路由及批准后另开实现 PR，无 PR 号链接。
- Reviewy 安全评审、640 批准和 CI 仍待外部执行；本地检查通过也不能标 done。

### 后续实现轮（未执行）

- 合格页面在同进程窗口内并发 401 只自动恢复一次，主视图和原导出继续且无重复作业。
- 未知、超窗、重启、已消费、资格耗尽时停止自动恢复，明确人工配对，不绕过认证。
- 故障有时间上限，不吞其他错误，不破坏快照一致性和取消结果；后端定向、前端及真实浏览器证据齐备才可声称实现完成。

## 风险与恢复边界

- 过期秘密新增短暂恢复权；同源 XSS／Bearer＋CSRF 同时泄露仍可利用。严格来源不能替代凭证保密，进程预算可能被本机攻击者耗尽。
- 只签发一次意味着响应丢失也可能丧失恢复机会，这是安全优先的取舍；休眠超过窗口必须人工配对，不把 8 小时变为无限有效。
- 当前 Origin／秘密比较／过期清理实现尚不满足拟议规则；OpenAPI planned 不是运行时实现证据。现有 pair 字节不变不代表其未来内部无需适配恢复票。
- 本轮仅追加契约文档；未批准时保持既有人工配对。后续实现回退须停自动流程、清掉恢复记录及票据、重新人工配对，不动统计／快照／导出数据。
- 本地测试基于上述 SHA 的未提交工作树，不代表 PR head、CI、macOS／Windows 或部署证据；本轮不创建提交，不承诺跨会话自动恢复。

## 验证证据

### 第 1 轮本地验证（历史保留，非本轮重跑）

证据来源：云主机实测；Evidence Source：developer-local；Source Revision：dirty；Evidence Publication：local-only。基准 SHA 与分支见上文，Python 3.13.5，Linux x64；环境对齐 CI 尚未验证。使用原生指定命令，rtk：skipped-for-report，避免压缩或缓存影响输出。以下为本轮本地命令证据，不是已提交 PR head 的正式报告或 CI 结果。

| 命令／检查 | 实际结果 | 退出码 |
|---|---|---|
| `python3 -B -c "import importlib.util, platform; print('PYTHON',platform.python_version()); print('VALIDATORS', {n: importlib.util.find_spec(n) is not None for n in ['yaml','openapi_spec_validator','openapi_schema_validator','jsonschema','markdown_it']})"` | Python 3.13.5；yaml／jsonschema／markdown_it 可用；openapi-spec-validator 与 openapi-schema-validator 未安装，未运行，未安装依赖 | 0 |
| `python3 -B -c "from pathlib import Path; import yaml; d=yaml.safe_load(Path('sbtd-runtime/contracts/openapi.yaml').read_text()); o=d['paths']['/api/v1/session/re-pair-ticket']['post']; assert d['openapi']=='3.1.0'; assert o['operationId']=='issueRePairTicket'; assert o['x-sbtd-implementation']=='planned'; assert set(o['responses'])=={'200','401','403','429'}; assert o['security']==[{'localSession':[]}]; assert {'\u0024ref':'#/components/parameters/CsrfToken'} in o['parameters']; print('OPENAPI_YAML_AND_SHAPE_OK')"` | `OPENAPI_YAML_AND_SHAPE_OK`；YAML 可解析，新 operation／planned／精确响应集合／Bearer／CSRF 引用通过 | 0 |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_golden_contracts -v` | 总数 65，通过 65，跳过 0；OK | 0 |
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py'` | 总数 457，通过 445，失败 2，跳过 10；`FAILED (failures=2, skipped=10)`，198.509 秒；失败详情见下文，未重跑或筛掉失败 | 1 |
| `python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_runtime_r1_acceptance` | 总数 81，通过 81，跳过 0；OK | 0 |
| `python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts` | 总数 99，通过 99，跳过 0；OK | 0 |
| `python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); Path('ai/tasks/index.md').write_bytes(a); print('INDEX_REGEN', 'changed=%s' % (b!=a), 'rows=%d' % len(s._index_rows(r)))"` | `INDEX_REGEN changed=True rows=78`；生成器保留现有导航，仅新增本任务；原样报告“旧格式事件，不追溯”，不修改历史任务 | 0 |
| `python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); print('INDEX_PREVIEW_SAME', Path('ai/tasks/index.md').read_bytes()==a, 'rows=%d' % len(s._index_rows(r)))"` | `INDEX_PREVIEW_SAME True rows=78`；有相同旧格式事件提示，无错误退出 | 0 |
| `python3 -B -c` 一次性字节比较（从 `git show HEAD:<相对文件>` 读取基线，对比当前原 API 路径块、ADR 前缀及 index 行） | `EXISTING_OPERATIONS_BYTE_IDENTICAL 27 PAIR_BYTE_IDENTICAL True ADR_PREFIX_IDENTICAL True INDEX_ONLY_ONE_NEW_ROW True` | 0 |
| `python3 -B -c` 首轮 RePairTicket／429 schema 边界诊断（含 FormatChecker 的非法日期断言） | **失败保留**：AssertionError；非法日期被接受，未执行到后续 429 断言，不能算 12 项通过 | 1 |
| `python3 -B -c` schema 失败定位（输出 FormatChecker.checkers、各样本有效性与错误规则） | `DATE_TIME_CHECKER_AVAILABLE False`；仅非法日期样本与预期不同，环境未安装 date-time 格式校验支持；不是票据 schema 的数值／字段约束失效 | 0 |
| `python3 -B -c` 修订后的可执行 schema 检查（正数／≤30 秒、分数秒、必需字段、空票、额外字段、429 固定 detail） | `RE_PAIR_SCHEMA_BOUNDARIES_OK cases=11`；`DATE_TIME_RUNTIME_VALIDATION_SKIPPED True`。检查 date-time 声明存在，但未运行日期格式语义校验；不把删去不受支持的诊断算完整格式验证 | 0 |
| `git diff --stat`；`git ls-files --others --exclude-standard` | tracked 仅 ADR 0001（+62）、OpenAPI（+144）、index（+1）；未跟踪仅本 task.md。新文件未暂存，因此不会出现在普通 diff --stat；未为显示它而修改 Git index | 0／0 |
| grep 工具：新增 ADR §9、OpenAPI 新 operation／组件、本 task 和 index 的本机路径扫描 | 无匹配；仅扫描新增／修改内容，既有 ADR 正文不因此修改 | 工具成功，无 shell 退出码 |
| grep 工具：本 task 与 ADR §9 的禁止归因措辞扫描 | 无匹配 | 工具成功，无 shell 退出码 |
| `python3 -B -c "import importlib.util; from datetime import datetime; from zoneinfo import ZoneInfo; print('DEPENDENCIES', {n: importlib.util.find_spec(n) is not None for n in ['tzdata','playwright']}); print('BEIJING',datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds'))"` | tzdata=False，playwright=False；当前北京时间 2026-11-11T15:23:24+08:00 | 0 |
| 只读检查性能 smoke 的原生详细报告 | 报告已不存在；测试使用 TemporaryDirectory，退出后清理，原生汇总未打印 error 字段；无法从本轮保留输出进一步确定根因 | read 工具：not found |

API Contract：verified（YAML、形状及已执行 schema 约束；不含完整 OpenAPI 规范校验或日期格式校验）。openapi-spec-validator／openapi-schema-validator 未安装，未运行，未擅自安装依赖。补充诊断首轮失败保留，后续仅确认环境支持的 11 个样本；环境缺口仍在，不用后续通过覆盖它。

### 全量回归失败与跳过（如实保留）

- `test_runtime_perf_smoke.RuntimePerfSmokeTests.test_cli_preserves_dataset_and_reports_unmeasured_boundaries`：子进程返回 1，输出 `execution=failed`、`events=101`、`seconds=6.471294864000811`。`test_runtime_perf_smoke.py:18-42` 在读取详细报告前断言失败，临时目录随后被测试清理；本轮尝试只读详细报告得到不存在。`runtime_perf.py:712-742` 把根因写在报告的 error 字段，终端只有汇总，所以**根因未确定**，不能声称是本契约引起或已经证明与本契约无关。输出中的“未达 1M 档”是该 101 事件测试预期的规模说明，不是已证实失败原因；Playwright 缺失在 `runtime_perf.py:271-280` 是可选浏览器测量跳过，不能据此归因本次失败。
- `test_stats_query.NormalizeScopeTests.test_iana_queries_and_dst_work_without_system_timezone_data`：明确 `ModuleNotFoundError: No module named 'tzdata'`，继而 `ZoneInfoNotFoundError` 和 `QueryScopeError: range.timezone: unknown timezone 'Asia/Tokyo'`；独立模块可用性检查同样显示 tzdata=False，归类为环境依赖缺失。
- 原生汇总有 10 项 skipped；本次非 verbose 全量命令不列逐项名称／原因，不编造逐项映射。源码具有真实 renderer 前置条件和 Windows-only 条件，当前是 Linux 且未安装 Playwright；这不是这些平台／浏览器检查已经通过的证据。
- 不扩大本轮范围修改生产代码、测试或环境；未安装 tzdata／Playwright，也未重跑全量或失败案例筛选成功。Final Full Rerun：failed（本轮唯一全量执行）；Targeted Rerun：not-needed（未修复范围外失败）。这些失败、完整 OpenAPI 校验器缺失、独立安全评审与 CI 都仍未闭环，task 保持 checking，不能宣称全绿或发布就绪。

新恢复流程未实现，BDD：skipped（新行为尚无运行时）；真实浏览器、UI 构建、跨平台、新鉴权运行场景与生产代码 lint 均未运行（本轮无这些代码变更）。现有回归不证明新恢复行为安全。Final Test Report／Run Summary MD：not-needed（本轮仅保存本地命令证据表，不生成正式报告）；不冒充 CI 或正式 PR-head 验收。未创建临时脚本、永久源码文字测试或额外报告文件。此次可选格式检查缺口只记任务证据，不扩展为仓库 lesson／身份变更。

### 第 2 轮本地验证（补 CHANGELOG 与 strict 记录）

本轮基准仍为 `80f14263e7d8bc6ae84f04ba94218e4857fc8b8f`，分支仍为 `docs/v2.1.0-rc.5-dashboard-401-re-pair-contract`；Evidence Source：developer-local；Source Revision：dirty；Evidence Publication：local-only；Environment Alignment：unverified（未对齐 CI）。使用原生命令保留完整输出，rtk：skipped-for-report；这里只保存本地验证证据，不生成正式 PR-head 报告。

| 命令／检查 | 实际结果 | 退出码 |
|---|---|---|
| `python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); Path('ai/tasks/index.md').write_bytes(a); print('INDEX_REGEN', 'changed=%s' % (b!=a), 'rows=%d' % len(s._index_rows(r)))"` | `INDEX_REGEN changed=False rows=78`；实际执行写入，内容与第 1 轮一致；保留“旧格式事件，不追溯”提示，不修改历史任务 | 0 |
| `python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); same=Path('ai/tasks/index.md').read_bytes()==a; print('INDEX_PREVIEW_SAME', same, 'rows=%d' % len(s._index_rows(r))); assert same"` | `INDEX_PREVIEW_SAME True rows=78`；只读预览与写入结果相同；相同旧格式事件提示，无错误退出 | 0 |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_golden_contracts -v` | 总数 65，通过 65，失败 0，跳过 0；`OK`，0.360 秒 | 0 |
| grep 工具检索 `tests` 中的 `CHANGELOG`（等价于 `rg -l CHANGELOG tests` 的候选查找），并以大小写不敏感的 `changelog` 补查 `tests`、`sbtd-runtime/tests` | 两次均无匹配；无 CHANGELOG 相关测试可运行，记 skipped，不宣称该项测试通过 | 工具成功，无 shell 退出码 |
| `python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts` | 总数 99，通过 99，失败 0，跳过 0；`OK`，38.999 秒 | 0 |
| `git diff --stat`；`git ls-files --others --exclude-standard` | tracked 仅 CHANGELOG.md（+7）、CHANGELOG.zh.md（+7）、index（+1）、ADR 0001（+62）、OpenAPI（+144），共 5 文件、221 行新增；未跟踪仅本 task.md。未暂存新文件，故普通 diff --stat 不显示它，未修改 Git index | 0／0 |
| `git diff --check` | 无输出，空白检查通过 | 0 |
| grep 工具：本 task、ADR §9、OpenAPI 新 operation／限流响应、双语 rc.5 新增节的本机路径与禁止归因措辞检查 | 无匹配；不将历史正文重写或扫描结论扩展到无关文件 | 工具成功，无 shell 退出码 |

本轮指定可运行测试共 164 项通过；Final Full Rerun：passed（仅本轮指定的两个 unittest 命令，不是 runtime 全量）。第 1 轮全量的 2 项失败、10 项跳过及校验器缺口仍保留，未重复运行或改写其结论。BDD／真实浏览器／新端点运行验证：skipped（契约未实现、serve 未路由）；生产代码 lint／构建：not-needed（无生产代码变更）。Cross-repo context：contract-only；API Contract：verified（既有 golden 检查范围，不含新恢复行为安全证明）；Mock Strategy：none。Final Test Report／Run Summary MD：not-needed（本地证据表，非正式报告）。Reviewy 独立安全评审、640 批准与 CI 仍 pending，不声称 CLEAN、实现完成或发布就绪。

## 模型记录

| 模型 | 用途 | 调用次数 |
|---|---|---|
| `openai-codex/gpt-6-astra`（thinking high，主模型） | 第 1 轮 omp 会话：编写 ADR §9、OpenAPI、task.md、index 与本地验证；第 2 轮 omp 会话：补 CHANGELOG 与 strict 执行记录、重跑验证 | 第 1 轮：22 次模型调用、81 次工具调用（编排方从会话日志统计）；第 2 轮：见 PR 描述 |

只使用上述一个模型，未使用其他模型、task 执行工具或子代理。第 2 轮调用次数在本轮结束后由编排方统计，写入 PR 描述与群内汇报，本文件不估算。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-11T14:38:57+08:00 | planned | planned | 编排方整理：保留 default 延后项草稿建立事件，未开始实现；归因措辞按本轮边界整理 | 草稿记录已读取 PR #186／#190、ADR 0001／0002 和相关源码；历史基准 80f14263e7d8bc6ae84f04ba94218e4857fc8b8f；本轮不将历史读取冒充新查询。 |
| 2026-11-11T15:15:09+08:00 | planned | checking | 编排方整理：将只读草稿改写为 strict、contract-only 契约任务，等待独立安全评审、批准和 CI | ADR 0001 §9 与 OpenAPI planned operation 已写入；本轮工作树未提交，实际本地验证见上表。此行记录草稿交付阶段变化，不声称调用 TaskStore.transition 跨阶段转换。 |
| 2026-11-11T15:26:30+08:00 | checking | checking | 按 strict 补 CHANGELOG 与执行记录 | 640 于 2026-11-11 15:11 在群内确认 rc.5 全程用 strict；第 2 轮补齐双语未发布条目、strict 执行与单模型记录，验证结果见第 2 轮证据表；未 commit/push，独立评审、批准与 CI 仍待完成。 |
