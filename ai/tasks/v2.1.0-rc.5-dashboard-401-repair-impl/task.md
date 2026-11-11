---
schema_version: 1
id: v2.1.0-rc.5-dashboard-401-repair-impl
workflow_mode: strict
mode_source: user
mode_note: 用户 2026-11-11 15:10 群内确认（rc.5 全程用 strict），Lord 记录。
status: checking
branch: feat/rc5-401-repair-impl
created_at: '2026-11-11T19:53:53+08:00'
updated_at: '2026-11-11T20:02:57+08:00'
completed_at: null
---

# Dashboard 401 重新配对：实现 PR

## 目标与本轮边界

本 PR 按已合入的 ADR 0001 §9、OpenAPI `POST /api/v1/session/re-pair-ticket` 与 pair 恢复票交换契约，实现 serve 取票、一次性交换，以及 Dashboard 受保护请求 401 后自动重新配对。

第 1 轮只建立本 task.md 和正式生成器更新的 `ai/tasks/index.md`。实现代码、测试、构建产物和双语 CHANGELOG 实现条目留待后续轮次；保持 checking，completed_at 为 null。不提交、不推送、不开 PR，不执行 Git 写命令；提交由编排方稍后处理。不建立 active、handoff、developer 等其他记录。

第 2 轮仅按 Reviewy 2026-11-11 19:57（北京时间）的意见修订本 task 的范围、验收和测试计划，明确 ADR 0001 §9 已要求实现 PR 补齐所有配对端点响应的 no-store 及测试；不改实现代码、ADR、OpenAPI、CHANGELOG、PRD 或旧契约任务。index 仅由正式生成器处理，预期与第 1 轮结果逐字节一致；状态仍为 checking，completed_at 保持 null。

未完整调用 grill-with-docs：交付边界、已合入契约和验收步骤明确，源码可回答本轮问题，不新增领域决定或重复访谈。旧契约任务是只读依据，不改写其正文或历史状态。

## 决策来源

- 用户 2026-11-11 15:10 群内确认（rc.5 全程用 strict），Lord 记录。
- 用户 2026-11-11 17:38 群内确认（合入 #208，批准 #210 契约，按新顺序 #208、#211、#210、#209），Lord 记录。#210 已合入 main，合并提交 `f2887297b2e098b8339758bba918afaa842fbe79`；当时只交付契约，未实现。
- 用户 2026-11-11 19:48 群内确认（合入 #209），Lord 记录。Lord 于同日 19:48（北京时间）将 #209 squash 合入 main，合并提交 `6c5eef24e6cd4f1dba3872683d26b99a703c059b`，并删除远端分支 `contract/rc5-host-gate-codex-0167-omp-18188`。
- 合入后 Lord 下令：清掉本地 `pr209-rebase` 分支和工作区，再按 rc.5 顺序开始 401 重新配对实现 PR，先写 task.md。这是 Lord 的调度；本会话未执行或核验该清理，不把它记成本轮完成动作。
- 本轮的记录边界与后续方案细节由编排方整理，并与契约、当前源码核对；不把这些细节归给用户。上述群内决定和合并经过采用本轮提供的已核实背景，不冒充本会话查询群聊或远端所得。
- Reviewy 2026-11-11 19:57（北京时间）在 640-skills 群指出：401 重新配对实现 PR 必须让所有配对端点响应都带 `Cache-Control: no-store`，并有测试覆盖；这是 ADR 0001 §9.3／§9.4 已有的实现要求，不是新增契约决定。该意见采用已核实背景，本会话未查询群聊。

## 范围与非目标

范围内：服务端进程内恢复记录、一次性取票、pair 恢复票单次交换、限流、错误映射、严格来源和常量时间比较；前端同标签页 401 合流、一次恢复、原操作最多一次重放、双语提示与失败转人工；本 PR 的双语 CHANGELOG 实现条目及对应测试、场景和静态构建。

范围内单列：依据 ADR 0001 §9.3／§9.4 及 Reviewy 2026-11-11 19:57（北京时间）的意见，本 PR 必须让所有配对端点响应（`POST /api/v1/session/pair` 的全部响应，含初次配对与恢复票交换的成功、失败和中间件拒绝）都带 `Cache-Control: no-store`，并增加测试断言该头；取票端点 `POST /api/v1/session/re-pair-ticket` 的全部成功与错误响应同样必须 no-store。此项是补齐当前 serve 尚未发送的响应头及其测试，不是契约／OpenAPI 改动。

OpenAPI 实现标记采用保守边界：`x-sbtd-implementation` 虽是状态元数据，但当前 operation、pair 和 schema 描述同时保留 proposed／planned 说明，单改标记会留下互相冲突的实现状态，扩改说明又会进入冻结的契约文件范围。因此本 PR 计划不改该标记，留待用户决定；不能因此声称标记已更新。本轮绝不改 OpenAPI。

非目标：改契约、schema、PRD、数据字典；提前续期、跨重启恢复、跨标签页广播、匿名取票、无限续期、refresh token、长期 token 下发；改快照 TTL、导出业务语义、渲染或数据持久化；绕过 Host／Origin／CSRF；改旧契约任务。ADR §9 中“§8 由另一契约 PR 追加”的过时说明按 Reviewy 建议留给最后的文档 PR，本 PR 不改 ADR。

## 当前源码依据

本轮只读核对基准：`6c5eef24e6cd4f1dba3872683d26b99a703c059b`；起始分支与 front matter 一致，工作区干净。以下是现状，不是新行为已经运行的证据。

| 事实 | 当前依据 |
|---|---|
| §8 已包含新宿主门禁；§9 给出恢复契约，仍有合入前说明 | `docs/adr/0001-v2.1.0-rc.1-r1.0-runtime-decisions.md:182-271`；门禁为 codex@0.167.1 + omp@18.18.8，历史 smoke 不是本轮执行 |
| pair 接受恢复票的契约与取票 planned operation 已存在 | `sbtd-runtime/contracts/openapi.yaml:52-187,928-985,1119-1141` |
| rc.5 两份 CHANGELOG 均只把 401 恢复记为契约先行、尚未实现；同时保留快照内存、宿主门禁、probe-link 条目 | `CHANGELOG.md:10-24`、`CHANGELOG.zh.md:10-24` |
| 旧契约任务有实现方案、九行测试计划、后续实现验收及源码依据表；其旧行号和旧状态不能直接当本轮现状 | `ai/tasks/v2.1.0-rc.5-dashboard-401-auto-repair/task.md` 的对应小节，本轮按新基准重新核对 |
| 启动票默认 300 秒，会话默认 8 小时；pair 每次尝试销毁启动票，普通鉴权删除过期会话；尚无独立恢复记录 | `sbtd-runtime/serve.py:64-65,151-208` |
| 当前 Origin 缺失可通过，只解析 scheme／hostname／port，不要求完整等于 Host；秘密仍用普通比较 | `sbtd-runtime/serve.py:120-145,180-208,393-412`；不能称为满足新恢复规则 |
| health／pair 豁免普通 Bearer；新取票路径尚未路由；pair 响应还没有 no-store | `sbtd-runtime/serve.py:371-415,518-526,710-734` |
| 初次票通过 fragment 或 0600 文件交付，uvicorn access log 关闭 | `sbtd-runtime/serve.py:740-763,828-846`；恢复票不得复用文件／fragment 交付 |
| API 从 sessionStorage 读取 Bearer／CSRF，通用 request 遇错直接抛 ApiError；初次 pair 独立 fetch 并保存短时会话 | `sbtd-runtime/dashboard/src/api.ts`：`readSession`、`pairWithTicket`、`request` |
| 主页面每 30 秒刷新；统计→快照→数据页全部完成才替换视图；已有展开项保留与卸载时导出 stop | `sbtd-runtime/dashboard/src/App.tsx:114-129,145-218,236-279`；`pageModel.ts` 的 `applySuccess`／`applyFailure` |
| 数据页核对 snapshot_id；导出创建、查询、下载、取消均走 request；取消目前未传 AbortSignal | `sbtd-runtime/dashboard/src/api.ts:347-429` |
| 导出创建网络错误已有一次同 key／载荷重试；轮询最多 40 次，延迟 1 秒乘 1.5 至 5 秒；只对 409 继续等待；stop／cancel 防迟到结果 | `sbtd-runtime/dashboard/src/exportJob.ts`：`ExportJob.run`／`stop`／`cancel`；恢复不能叠加成额外重放 |
| 当前中英文 401 提示直接重启 serve 并配对，尚无恢复中状态 | `sbtd-runtime/dashboard/src/i18n.ts`：`export_err_401`、`error_unpaired` |
| 现有测试覆盖启动票单次消费、来源与鉴权、导出同 key、404／410、下载／取消、轮询上限、迟到响应、快照整体替换 | `sbtd-runtime/tests/test_serve.py`、`sbtd-runtime/tests/test_exports_http.py`、`sbtd-runtime/dashboard/src/exportJob.test.ts`、`pageModel.test.ts`、`snapshotPin.test.ts`、`i18n.test.ts` |
| 前端使用 Node 原生测试；构建包含类型检查，产物提交到 static 并由 serve 提供 | `sbtd-runtime/dashboard/package.json:7-11`、`vite.config.ts:4-15`、`sbtd-runtime/serve.py:731` |

## 后续实现计划与预期文件

以下均为预期将改，不是本轮已经修改。

| 文件 | 计划 |
|---|---|
| `sbtd-runtime/serve.py` | 在 AccessControl 内管理恢复记录／票／链资格和进程预算；SecurityMiddleware 分离专用恢复校验，接入取票路由及 pair 单次交换；为所有 pair／取票响应补齐 `Cache-Control: no-store`，覆盖初次配对、恢复票交换及取票的成功、失败与中间件拒绝，不限于拒绝路径 |
| `sbtd-runtime/dashboard/src/api.ts` | 同标签页共享恢复流程、会话代次、超时与取消；受保护请求最多重放一次；补主查询／分页的中断传递，不递归拦截 health／pair／取票 |
| `sbtd-runtime/dashboard/src/App.tsx` | 暂停轮询、恢复状态提示、一次完整刷新、失败停止自动请求；卸载和取消不接纳迟到结果 |
| `sbtd-runtime/dashboard/src/exportJob.ts` | 保留原 input／key／id、查询次数与取消语义；区分普通创建网络重试和恢复失败，避免重复作业／下载 |
| `sbtd-runtime/dashboard/src/i18n.ts` | 增加中英文恢复中、已恢复、未刷新、人工配对步骤，不使用多轮重试提示 |
| `sbtd-runtime/dashboard/src/sessionRecovery.ts`（如需要，新模块） | 仅隔离共享恢复状态与订阅，便于 API／App 共用；若 api.ts 内可清楚承载则不新增，不做通用重试框架 |
| `sbtd-runtime/tests/test_serve.py`、`sbtd-runtime/tests/test_exports_http.py` | 时间边界、来源／秘密、并发、限流、no-store、重启、导出原对象继续与失败路径 |
| `sbtd-runtime/dashboard/src/api.test.ts`（新增）、`exportJob.test.ts`、`pageModel.test.ts`、`i18n.test.ts` | API 合流与单次重放、导出取消／网络边界、画面保留与双语状态；如新增恢复模块则补对应定向测试 |
| `sbtd-runtime/spec/rc5-401-repair-scenarios.md`（新增） | 沿用现有 Markdown 内 Gherkin：中文场景、英文关键字；从下表落实长期场景，映射真实行为测试，不改契约或 PRD |
| `sbtd-runtime/dashboard/static/` | 实现验证后由 `npm run build` 生成，不手写产物，确保真实 serve 使用新页面 |
| `CHANGELOG.md`、`CHANGELOG.zh.md` | rc.5 各补本实现条目，区分先前契约记录；不提前宣称实现或发布完成，不碰其他 PR 条目 |
| `ai/tasks/v2.1.0-rc.5-dashboard-401-repair-impl/task.md`、`ai/tasks/index.md` | 更新实际计划／证据；index 只由正式生成器维护 |

顺序：先补场景和高风险失败测试，建立既有行为安全网；再实现服务端原子转移与来源／错误优先级；随后接前端恢复与导出；最后运行定向回归、构建和真实浏览器 smoke，补双语实现条目并送独立安全评审。所有新接口／schema／PRD 决策另开 PR 并等用户决定，不在实现里偷偷改变契约。

## 验收标准（后续实现轮，尚未执行）

1. 恢复记录只在原 serve 进程内，绑定原 Bearer、CSRF、expires_at 和人工配对链。仅 `expires_at <= now < expires_at + 60 秒` 可取票；右端到达即从内存删除记录，重试不滑动窗口。未过期、未知、撤销、重启前、超窗或无资格均 401；普通 API 到期即 401，不因恢复记录继续给旧 Bearer 数据权限。
2. 取票严格按 Host／Origin→进程预算→Bearer＋CSRF 整体校验→原子签发复核执行。Host 是 loopback 白名单加实际端口；Origin 必须完整等于 `http://<Host>`，拒绝缺失、null、异主机／端口、userinfo、路径、query、fragment。恢复票 pair 也先查严格来源；初次配对的既有交付方式不扩大。
3. 两个秘密必须常量时间匹配同一记录，任一缺失或错误均 `401 {"detail":"unauthorized"}`，不能用 CSRF 的 403 泄露 Bearer 恢复资格。恢复路径的 403 仅来源拒绝，detail 为 forbidden；pair 不额外要求 CSRF。沿用 DetailError，不新增信封或用 409／410 区分票状态；普通 API 原有 CSRF 规则不变。
4. 首次成功签发与标已用原子完成，并发最多一张票；签发后即耗尽资格，不等 pair 成功。首次通过来源并到达 pair 处理的恢复票尝试即原子消费待交换票，成功或失败都不可重放；来源拒绝在消费前。成功交换、新会话创建和链成功标记原子完成；每条人工配对链最多自动成功一次，替代会话默认仍为 8 小时且无再次恢复权。
5. 随机票绑定记录／链／进程，只通过 X-Pairing-Code 交换，不是 Bearer。票到期为 `min(签发时间 + 30 秒, 原 expires_at + 60 秒)`，右端不含。200 直接返回 pairing_code、UTC RFC 3339 expires_at、`0 < ttl_seconds <= 30`（允许小数），不是 Session 或 Envelope；不轮换、不补发、不延长。
6. 每进程滚动 60 秒最多接纳 10 次通过来源的取票请求进入凭证校验，错误凭证也计数；第 11 次及以后 429／RE_PAIR_RATE_LIMITED，429 不增加接纳数。单调计时，重启清零；Retry-After 为最早请求退出窗口剩余秒数向上取整、至少 1。预算未耗尽的重复取票是 401，不是 429；前端不自动重试 429。
7. 所有取票响应（成功与错误）和所有 pair 响应都必须带 `Cache-Control: no-store`；pair 覆盖 `POST /api/v1/session/pair` 的全部响应，包括初次配对和恢复票交换的成功、失败及中间件拒绝。当前 serve 尚未发送 pair 的该头，实现时必须补齐，并增加测试，逐类断言初次配对与恢复票交换的 200／401／403 及中间件拒绝响应均带该头；取票全部响应也须断言。这是 ADR 0001 §9（§9.3／§9.4）要求实现 PR 补上的内容，Reviewy 2026-11-11 19:57（北京时间）的意见再次明确了此项。恢复票只留内存及响应体／请求头，不进入 URL／fragment、日志、异常详情、导出、文件或浏览器存储。短时新会话仍可用 sessionStorage；不下发长期 token。
8. 取票超时、未知 5xx、响应丢失等不能证明未签发时直接转人工；pair 响应丢失不重放票或查回秘密。只有确知未发送／未签发才可在原期限内重试取票。本实现计划默认不主动重试结果不确定的恢复请求；单请求 5 秒、总恢复最多 30 秒且不越过服务端期限，不另设三轮交换。
9. 只对携带会话的受保护请求 401 恢复：统计、快照／数据页、capabilities、导出创建／查询／下载／取消均纳入；health、初次 pair、取票不递归恢复。403／404／410 和普通网络错误不当作会话到期。并发 401 同标签页合流一次，迟到旧代次 401 不删新会话；旧凭证从 sessionStorage 移除后仅供当前流程内存使用，成功一次替换，失败清空临时秘密。
10. 恢复期间暂停主轮询和导出轮询，保留画面、筛选、展开状态并提示未刷新。成功后只启动／继续一轮完整主视图刷新，不因多个等待者产生多轮刷新；数据页沿用原 snapshot_id／cursor，全部完成才替换视图。每个原请求最多重放一次，重放仍 401 不再次恢复。
11. 导出 POST 沿用原 Idempotency-Key、完整载荷和 snapshot_id；查询／下载沿用 export_id，取消沿用 export_id 和原 key。不自动换快照或创建新作业，404／410 保留原业务语义；40 次查询上限不重置。既有创建网络重试不得叠加突破恢复重放上限，恢复失败不得被当作普通网络错误重新发起创建。
12. 取消／卸载中断对应等待和重放，取消不复活旧操作，不接纳迟到成功或重复下载；单个取消不能误清其他仍有效等待者的新会话。恢复失败停止自动请求，不反复弹窗，中英文明确给出重启 serve 后重新配对步骤。
13. 后端定向测试、前端测试、类型检查／构建、真实 serve＋浏览器 smoke 齐备，且独立安全评审与适用 strict Gate 闭环后才可声称实现完成；CI、合入、部署和发布状态分别记录，不用本轮记录校验代替。

## 计划中的测试证据

沿用旧契约任务九行测试计划，并已对照当前 test_serve、test_exports_http、Node 测试入口核对；第 2 轮另列全部配对／取票响应头断言覆盖。以下全是后续计划，不是本轮通过证据。

| 场景 | Given / When / Then | 计划映射 |
|---|---|---|
| 到期边界与访问隔离 | Given 原会话；When 到期前、恰到期、+60 秒前与恰 +60 秒；Then 只在半开窗口取票，普通 API 到期即 401，右端记录清除 | `test_serve` 可控时钟，含票 30 秒及剩余窗口不足 30 秒、小数 TTL |
| 来源与秘密绑定 | Given 同进程记录；When 来源畸形、Host 不符、Bearer／CSRF 任一缺失或错误；Then 按前置优先级 403／401，不签发，不泄露资格 | `test_serve` 安全矩阵；来源拒绝不消耗票／预算；常量时间比较由代码审查核对，不用不稳定耗时断言 |
| 一次签发与重放 | Given 合格记录／待交换票；When 并发取票、重复交换、错误／过期票尝试；Then 最多一张票与一个替代会话，已消费不可复用 | `test_serve` 并发与单次消费；来源先拒绝后正确交换；签发前失败和签发后丢响应分开 |
| 一次链成功与重启 | Given 已恢复链或旧进程凭证；When 再到期、撤销或重启；Then 401 转人工，新人工链才有新资格 | `test_serve` 生命周期；启动票原格式、错误尝试销毁和 health 豁免回归 |
| 网络结果不确定 | Given 已签发／已消费；When 取票或 pair 响应丢失、5 秒超时、总期限、取消；Then 不补票、不查回秘密、不盲重试，转人工 | 后端故障注入＋新增 Dashboard API 定向测试；单独覆盖可确认尚未发送的边界 |
| 限流与秘密保护 | Given 通过来源的有效／无效凭证；When 第 11 次与窗口边界；Then 429、正确 Retry-After、不延长窗口；所有取票／pair 响应 no-store，秘密不落外部介质 | `test_serve` 隔离 runtime home、捕获日志；浏览器检查 URL／存储，断言不得打印真实秘密 |
| 全部配对／取票响应 no-store | Given 初次启动票或恢复票，以及有效／无效取票凭证；When 分别触发 pair 的 200、401（缺失／错误／过期／重复票）、403（来源拒绝）及中间件提前拒绝，并触发取票的 200／401／403／429；Then 每个响应均断言 `response.headers["cache-control"] == "no-store"`，不能仅检查成功或拒绝路径 | `test_serve` 增加响应头断言矩阵：初次配对与恢复票交换分别覆盖 200／401／403 及 Host／Origin 中间件拒绝；取票覆盖成功、凭证失败、来源拒绝和限流，任何新增错误响应也须覆盖。按 ADR 0001 §9 补齐当前 pair 缺失的头，不把计划当作已通过测试 |
| 401 合流与迟到响应 | Given 多个受保护请求和旧代次；When 并发／迟到 401；Then 只恢复一次，新会话保留，其余状态和递归路径不触发 | Dashboard `api.test.ts`（及必要的新恢复模块测试），由 `npm test` 执行；隔离 fetch／存储／时钟并恢复全局 |
| 原操作恢复及取消 | Given 原快照／导出 id、key、载荷；When 恢复、404／410、取消／卸载；Then 最多一次重放，不重复作业／下载，不换快照、不重置查询上限、不复活取消 | `test_exports_http`＋`exportJob.test.ts`＋`pageModel.test.ts`；真实 HTTP 同 key 返回原 export_id，前端覆盖创建／查询／下载／DELETE 每阶段 |
| 真实页面路径 | Given 隔离数据与短测试会话的真实 serve；When 主轮询与在途导出遇到期、再到期或超窗；Then 可见恢复／旧数据提示／人工步骤，恢复后原导出继续，取消保持终态 | 构建后的真实 serve＋浏览器 smoke，中英文；测试启动装配缩短寿命，不加生产调试端点，不以 mock 代替端到端 |

计划命令：仓库根运行 `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_serve test_exports_http`；Dashboard 目录运行 `npm test`（既有入口为 `node --test src/*.test.ts`），可先用 `node --test src/api.test.ts src/exportJob.test.ts src/pageModel.test.ts` 做定向，再跑前端套件；`npm run build` 完成 tsc 与 Vite。新文件名仅是计划，尚未创建或执行。真实浏览器 smoke 的环境、实际命令、结果和版本绑定在执行轮记录。

永久测试只覆盖可见行为、边界、状态转移与安全不变量；修改受影响测试时删除纯文案锁定或实现形状断言，不把新提示逐字重新钉死，不扩大为无关测试清理。现有 `exportJob.test.ts` 的 401 终止场景要区分“恢复已失败后终止”与“可恢复 401”，保留其他致命错误不重试的行为。

## Strict Book Gate Plan

| Gate | 客观触发条件与阶段 | 本轮状态／后续证据 |
|---|---|---|
| DDD | 完整 grill 后或领域边界不清时，需求稳定前 | not-needed：未完整 grill，现有契约已定义会话／恢复记录／票／链；后续出现歧义先停相应实现 |
| DDIA | 跨请求状态、恢复、重放；设计稳定和生产编辑前 | confirmed：本轮仅做契约到计划的映射自审；进程内所有权、原子签发／消费、单链上限、网络不确定转人工已明确。具体状态结构和并发实现须在后续轮再次核对，不是独立安全批准 |
| Legacy safety | 既有鉴权、pair、导出高风险行为修改前 | pending：本轮只读建立现状；后续先跑保留行为和失败场景，记录真实 red 原因 |
| Refactoring／ponytail | strict 首次生产编辑前 | pending：后续核对最小接口与可读性，不顺带重构；本轮无生产代码编辑 |
| BDD／TDD | 用户可见认证／取消行为，实施前 | planned：上述原九行映射及第 2 轮新增的响应头断言矩阵在既有 Markdown 场景体系落地，先补高风险失败测试再实现；不引入新测试框架 |
| Project validation／Web | 实现后检查 | pending：后端、前端、构建和真实浏览器均未执行；真实页面证据不可由 mock 代替 |
| 独立安全评审 | 授权／身份边界，合入前 | pending：后续交 Reviewy 或独立人工审查；本轮未调用子代理，作者自检不代替独立评审 |
| Release readiness | 运行时变更；测试门禁后、完成／发布前 | pending：实现未开始，不是发布就绪；记录 XSS、限流耗尽、响应丢失和回退风险 |
| CI／合入 | 实现 PR 最终提交 | pending：本轮不提交、不推送、不开 PR，不能用旧合并提交的结果证明后续实现 |

DDIA 设计边界：状态事实源只有原 serve 进程内存；活跃数据鉴权与短时恢复资格分开。写入顺序是资格检查→原子签发并标已用→来源检查后的原子消费→成功创建会话并标链成功；普通读取仍拒绝过期会话。没有 schema 迁移、回填或恢复票持久化。回退停止自动流程，清空进程内恢复记录／票并人工配对，不动统计、快照或导出数据。可观察信号只用脱敏状态与错误码，不输出秘密；并发、时钟和响应丢失测试待实现轮执行。

## 本轮验证证据

Evidence Source：developer-local；Source Revision：dirty（新增记录工作树）；Evidence Publication：local-only；Environment Alignment：unverified。基准 SHA 与分支见上文。rtk：skipped-for-report，使用指定原生命令保留实际输出；此处是本地证据表，不生成正式 PR-head 报告，不是 CI。

已执行：只读核对契约、双语 rc.5 条目、旧契约任务、当前源码与相关测试；确认目标 task 不存在、父目录和 index 无符号链接、index 已跟踪且两个目标路径未被 ignore；亲手用 write 建立本任务，正式生成器写入 index，再执行以下指定校验。未改生产代码、测试、契约或 CHANGELOG。

| 命令／检查 | 实际结果 | 退出码 |
|---|---|---|
| `python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); Path('ai/tasks/index.md').write_bytes(a); print('INDEX_REGEN', 'changed=%s' % (b!=a), 'rows=%d' % len(s._index_rows(r)))"` | `INDEX_REGEN changed=True rows=82`；从 81 条任务导航增加为 82 条，仅新增本任务一行；保留“旧格式事件，不追溯”提示，不修改历史记录 | 0 |
| `python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); print('INDEX_PREVIEW_SAME', Path('ai/tasks/index.md').read_bytes()==a, 'rows=%d' % len(s._index_rows(r)))"` | `INDEX_PREVIEW_SAME True rows=82`；只读预览逐字节一致，保留相同旧格式事件提示 | 0 |
| `python3 -B -c "import yaml; d=yaml.safe_load(open('sbtd-runtime/contracts/openapi.yaml', encoding='utf-8')); print('OPENAPI_PARSE_OK', '/api/v1/session/re-pair-ticket' in d['paths'])"` | `OPENAPI_PARSE_OK True`；仅证明 YAML 解析及路径存在，不是完整规范或运行时验证 | 0 |
| `python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts` | 99 项通过，失败 0，跳过 0；`OK`，50.701 秒 | 0 |
| `git diff --check`；`git status --short --untracked-files=all`；`git diff --stat`；`git diff -- ai/tasks/index.md` | 空白检查无输出；仅 index 修改和新 task 未跟踪；tracked stat 为 index 一行新增，diff 证实只加本任务导航。新 task 未暂存，不出现在普通 diff --stat，未为此修改 Git index | 0 |
| grep 新 task 的本机路径、禁止归因措辞和非“契约”用字 | 无匹配；检查表达式包含非“契”前缀的目标用字，时间均为精确记录 | 工具成功，无 shell 退出码 |

本轮跳过实现测试、BDD 执行、真实 serve＋浏览器、前端 lint／构建和运行时全量：未改生产代码，且本轮范围仅记录。BDD：skipped（只写场景计划）；Cross-repo context：contract-only（前后端源码均在本仓库，新链路尚未运行）；Mock Strategy：none（本轮无实现测试）。Final Test Report／Run Summary MD：not-needed（只保留本地命令证据）。旧契约任务的历史失败、跳过和环境缺口未重跑、不关闭。

Final Full Rerun：passed（仅本轮指定的 99 项工作流／任务测试，不是运行时全量）；Targeted Rerun：not-needed。API Contract：verified（仅本轮 YAML 解析和路径存在检查）。测试通过不代表新恢复流程已实现。末尾只读计数后，最后一次 edit 仅补模型表和推算数字，之后不再调用工具；计数编辑不改验收计划或程序行为。

## 第 2 轮本地验证

Evidence Source：developer-local；Source Revision：dirty；Evidence Publication：local-only；Environment Alignment：unverified。以上“本轮验证证据”保留第 1 轮原始记录，本节只记第 2 轮实际执行。rtk：skipped-for-report，直接使用指定原生命令保留实际输出；不生成正式 PR-head 报告，不是 CI。

| 命令／检查 | 实际结果 | 退出码 |
|---|---|---|
| `python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); Path('ai/tasks/index.md').write_bytes(a); print('INDEX_REGEN', 'changed=%s' % (b!=a), 'rows=%d' % len(s._index_rows(r)))"` | `INDEX_REGEN changed=False rows=82`；正式生成器写入前后字节不变，保留“旧格式事件，不追溯”提示 | 0 |
| `python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); print('INDEX_PREVIEW_SAME', Path('ai/tasks/index.md').read_bytes()==a, 'rows=%d' % len(s._index_rows(r)))"` | `INDEX_PREVIEW_SAME True rows=82`；只读预览逐字节一致，保留相同旧格式事件提示 | 0 |
| `python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts` | 99 项通过，失败 0，跳过 0；`OK`，50.666 秒 | 0 |
| `git diff --check`；`git diff --stat`；`git status --short --untracked-files=all`；`git diff -- ai/tasks/index.md` | 空白检查无输出；tracked stat 仅 index 一行新增，与第 1 轮已有差异相同；新 task 仍未跟踪，不出现在普通 diff --stat。未执行 Git 写命令 | 0 |
| grep 本 task 的本机路径、禁止归因措辞和非“契约”用字；grep 范围、验收第 7 条、serve 计划及响应头测试矩阵 | 禁用项无匹配；四处均明确全部 pair／取票响应的 no-store，范围与验收均要求增加测试，独立矩阵含响应头相等断言 | 工具成功，无 shell 退出码 |
| `TZ=Asia/Shanghai date --iso-8601=seconds` | `2026-11-11T20:02:57+08:00`；用于本轮状态事件及 updated_at | 0 |

Final Full Rerun：passed（仅本轮指定的 99 项工作流／任务测试）；Targeted Rerun：not-needed。API Contract：not-needed（本轮不改契约，未重跑第 1 轮 OpenAPI 解析）。BDD：skipped；Cross-repo context：not-needed；Mock Strategy：none；Final Test Report／Run Summary MD：not-needed。实现测试、真实 serve／浏览器、前端 lint／构建、运行时全量和生产代码相关 Gate 均未执行：本轮仅修订计划，实际响应头及其测试仍待实现，不能据此声称恢复流程完成、独立评审通过或发布就绪。

## 风险与恢复边界

- 同源 XSS 或同时泄露 Bearer＋CSRF 仍可抢先恢复；Host／Origin 不是秘密。一次性和短窗口只限制损害，不消除风险。
- 本机请求可耗尽进程预算；响应丢失会丧失恢复机会；超过窗口或替代会话再到期必须人工配对，不降低认证来提高成功率。
- App 轮询、API 合流和 ExportJob 已有网络重试会交叉；必须证明只有一轮刷新、一次原操作重放，取消不复活。构建后还须验证 serve 实际提供的页面。
- 本轮只能证明记录及指定本地校验，不能证明实现、独立安全批准、CI、部署或发布；不承诺跨会话自动恢复。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-11T19:53:53+08:00 | planned | checking | started：Lord 在 2026-11-11 19:48 合入 #209（合并提交 6c5eef2）后下令开始 401 重新配对实现 PR；本轮只写 task.md 及生成的 index | 已读契约／源码／测试并建立本 task；INDEX_REGEN changed=True rows=82，INDEX_PREVIEW_SAME True rows=82，OPENAPI_PARSE_OK True；99 项 unittest 通过；diff 空白检查通过，仅 task 和 index 变化，文案 grep 无匹配；证据仅 developer-local，不是 CI |
| 2026-11-11T20:02:57+08:00 | checking | checking | 按 Reviewy 意见修正：实现 PR 必须让所有配对端点响应带 Cache-Control: no-store，并有测试覆盖（ADR 0001 §9） | 第 2 轮仅修订 task 的范围／验收／测试计划；INDEX_REGEN changed=False rows=82，INDEX_PREVIEW_SAME True rows=82；99 项 unittest 通过；diff 空白检查通过，index 保留第 1 轮同一行差异；文案禁用项 grep 无匹配，范围和验收均明确所有 pair 响应 no-store 及测试；仅 developer-local，尚未实现 |

## 模型记录

| 轮次 | 模型 | 用途 | 模型调用 | 工具调用 |
|---|---|---|---|---|
| 第 1 轮 | openai-codex/gpt-6-astra（thinking high） | 读契约与源码、写实现任务计划、生成索引、执行指定本地校验 | 15 | 57 |
| 第 2 轮 | openai-codex/gpt-6-astra（thinking high） | 按 Reviewy 意见补范围／验收／测试计划，记录本轮状态事件和本地验证 | 11 | 30 |

计数方法：在 omp 会话日志中筛选 `role=assistant`、`provider=openai-codex`、`model=gpt-6-astra` 的消息计模型调用，同一记录内 `toolCall` 条目计工具调用。末尾只读统计实际输出 astra_assistant=13、astra_toolcalls=56、other_assistant={}，退出码 0；此后只有本次 edit 和一次纯文本收尾，因此模型调用按 A+2=13+2=15、工具调用按 T+1=56+1=57 推算。该 edit 为最后一次工具调用，数字回填后不再运行校验。find 工具未列入本轮工具，调用为 0；未调用任务执行工具或子代理。不把所读历史文件中的模型名字算成本会话模型调用。

第 2 轮计数方法：沿用第 1 轮的 assistant 消息与 toolCall 条目筛选口径，仅统计本轮 sessions-r2 日志，不计所读历史文件里的模型名称。只读 count.py 实际输出 `astra_assistant=9 astra_toolcalls=29 other_assistant={} model_usage={}`，退出码 0，不写仓库。统计后只执行本次 edit 和一次纯文本收尾，因此模型调用按 A+2=9+2=11、工具调用按 T+1=29+1=30 推算；第 1 轮 15／57 保持不变。本次 edit 为最后一次工具调用，仅追加本轮模型记录和计数说明，之后不再运行校验。
