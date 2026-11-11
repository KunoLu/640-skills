---
schema_version: 1
id: v2.1.0-rc.5-snapshot-eviction-impl
workflow_mode: strict
mode_source: user
mode_note: 用户 2026-11-11 15:10 群内确认（rc.5 全程用 strict），Lord 记录。
status: checking
branch: feat/rc5-snapshot-eviction-impl
created_at: '2026-11-11T22:27:32+08:00'
updated_at: '2026-11-11T23:19:39+08:00'
completed_at: null
---

# 快照内存回收：实现 PR

## 目标与本轮边界

本 PR 按已合入的 ADR 0003 §6，实现完整快照内存上限（默认最多 8 份）与 LRU 淘汰；只断开缓存的内存引用，不删除磁盘文件。

第 1 轮只建立本 task.md，以及正式生成器更新的 `ai/tasks/index.md`。实现代码、测试和双语 CHANGELOG 实现条目留待后续轮次。保持 checking，completed_at 为 null；不提交、不推送、不开 PR，不运行 Git 写命令，提交由编排方稍后处理。不建立 active、handoff、developer 或其他工作流记录。

第 2 轮开始实现。已核实背景：Lord 于 2026-11-11 22:36（北京时间）确认以本 task.md 范围为准，坏文件拒读后完整缓存未清除直接相关，允许一并修复，不得再扩大范围。这是 Lord 的范围确认，不是新的契约决定，方案细节不归给用户。第 1 轮的“尚未执行／后续计划”保留历史原意；本轮实际结果见「第 2 轮本地验证」。状态继续 checking，独立安全评审、CI、合入未完成。

未完整调用 grill-with-docs：边界、已合入 ADR 和验收条件明确，源码可回答本轮问题，不新增领域决定或重复访谈。旧文档任务只作依据，不改其正文、状态或历史证据。

## 决策来源

- 用户 2026-11-11 15:10 群内确认（rc.5 全程用 strict），Lord 记录。
- 用户 2026-11-11 群内确认（a甲 b同意），Lord 记录。注：分钟不可考。编排方整理：b 同意对应完整快照最多 8 份、LRU 移出内存、磁盘文件不删、其他规则不变。具体方案细节不归给用户。文档 PR #211 已将该决策写入 ADR 0003 §6，合并提交 `947fb55ae112cfa66563f322a1c39c2ebcfd944b`；当时仅文档，尚未实现。
- 用户 2026-11-11 群内确认（合入 #212），Lord 记录。注：分钟不可考。Lord 将 #212 squash 合入 main，合并提交 `e4c76707b368fb5e9873852ca3ce25abd67a6573`，提交时间为 `2026-11-11T22:21:57+08:00`，并删除远端开发分支。提交时间不是群内确认的精确时间。
- 在上述合入提交时间之后，Lord 群内调度：清掉本地 #212 分支与工作区，然后开始 rc.5 下一项快照内存回收实现 PR，照 ADR 0003 §6，先写 task.md。这是 Lord 的调度；本会话未执行或核验该清理。
- 上述群内确认与合并经过采用本轮提供的已核实背景，不冒充本会话访问群聊或远端所得。本轮计划由主模型对照 ADR 和当前源码整理。

## 范围与非目标

范围严格限制在 ADR 0003 §6：完整缓存与轻量索引分离；启动逐个完整校验后只保留轻量字段，完整缓存启动为空；默认 8 条 LRU；逐出不删磁盘、不释放配额；冷读沿用安全检查；`_validated` 随完整缓存逐出；索引找复用候选后再读盘核验；sweep 遍历轻量索引，冷清扫不污染 LRU；TTL／pin／404／410／507／分页／cursor／导出语义不变。仅隔离测试可用内部正整数容量参数，serve 固定默认 8，不新增环境变量、CLI 或配置文件。后续包含本 PR 双语 CHANGELOG 实现条目、定向测试与真实 serve smoke。

非目标：改契约／schema／PRD／ADR／数据字典／旧文档任务；改磁盘格式或 checksum、迁移既有文件；把容量变成产品配置；流式 CSV、按需生成数据页、磁盘索引数据库、多进程缓存、全进程内存限制或全仓性能优化；顺带修复文件身份五字段完全不变时的缓存局限；改变 `create_or_reuse` 返回对象的既有所有权接口；以内存压力删除未过期、坏或未知文件；改变 24h TTL、磁盘配额、导出保留策略；重写已发布 CHANGELOG 的 Deferred 历史条目。前端、安装、部署、发布和工作流同步均不在范围内。

OpenAPI `DiskQuotaExceeded` 的 “does not evict unexpired data” 位于共享磁盘配额、清扫与新建准入说明中；PRD §10.4 的“不淘汰未过期快照”也在磁盘上限段。这些句子限制磁盘删除，不禁止只释放内存引用，均不纳入本 PR 修改。ADR §6 的“实现另开代码 PR”等合入前说明，沿既有收尾惯例留给最后的文档 PR，本实现 PR 不改 ADR。

## 当前源码依据

本轮只读基准：`e4c76707b368fb5e9873852ca3ce25abd67a6573`；分支与 front matter 一致，起始工作区干净。下列行号来自本轮读取，不沿用旧文档任务的旧基准／旧行号；源码观察不是新行为的运行证明。

| 事实 | 当前依据 |
|---|---|
| ADR 全文保留文件格式、24h、引用和磁盘删除边界；历史启动／无内存淘汰说明已加注指向 §6 | `docs/adr/0003-v2.1.0-rc.2-r2.0c-snapshot-persistence.md:1-102`，特别是 23、62、66-102 |
| 快照 POST 仍为 library；GET／dataset 提供 404／410；磁盘 507 不定义新内存策略 | `sbtd-runtime/contracts/openapi.yaml:517-582,1060-1105` |
| 原 ID 固定数据与有效期；snapshot HTTP 幂等仍待单独决定；磁盘上限与复用条件独立 | `docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md:810-845,898-914,1076-1082` |
| 双语 rc.5 有 #211 文档条目和 #212 实现条目；rc.3／rc.2 历史仍记内存淘汰未实现及其他缓存限制 | `CHANGELOG.md:10-26,67-70,122-123`、`CHANGELOG.zh.md:10-26,67-70,122-123`；历史不重写 |
| 旧文档任务已列后续实现方案、测试计划、后续实现验收及风险；其历史测试失败不是本轮结果 | `ai/tasks/v2.1.0-rc.5-snapshot-memory-eviction/task.md` 对应小节；本轮重新核对源码 |
| 构造器安装恢复 pin，所有有效文件完整加载进 `_snapshots`；无容量参数，`_validated` 独立保存身份 | `sbtd-runtime/report_snapshot.py:640-685` |
| `_read` 先弹出旧校验项；热命中直接索引完整字典；重校验只在原字典有该 ID 时更新缓存；首次冷读不登记新对象 | `sbtd-runtime/report_snapshot.py:702-770` |
| 受控 ID／目录身份、普通文件／所有权／链接、同一 fd 五字段、版本／结构／checksum／ID 检查均已有 | `sbtd-runtime/report_snapshot.py:608-630,691-770`；fd 与路径 ctime 可不同 |
| 原子写仍为 temp→flush／fsync→replace→目录 fsync，之后才加入完整字典；失败沿原路径返回 | `sbtd-runtime/report_snapshot.py:772-809,960-962` |
| 复用遍历完整对象，匹配 query_hash／dataset_fingerprint 且未过期后 get；复用先于 quota.admit | `sbtd-runtime/report_snapshot.py:883-917` |
| sweep 已回收有效、过期、未 pin 文件；目前仅遍历完整字典；删除前强制完整校验与身份复核，失败保留 | `sbtd-runtime/report_snapshot.py:825-854` |
| pin 经 get 再计数；get 深拷贝，分页只拷贝返回页；过期拒读移除校验项但可保留完整对象 | `sbtd-runtime/report_snapshot.py:811-823,964-1007` |
| serve 构造默认 store 并 defer_sweep，再交 ExportStore；HTTP 保留统计 507、快照 404／410、cursor 400 与四槽线程池 | `sbtd-runtime/serve.py:662-670,739-803` |
| ExportStore 共享 quota／锁；恢复的是 ready 导出，不是新增在途作业恢复；pin 后取对象，终态 release | `sbtd-runtime/export_store.py:254-282,325-394,749-770,965-972` |
| quota 按磁盘普通文件 st_size 计量，export→snapshot→temp 顺序清扫，80% 预警，U > L 拒绝 | `sbtd-runtime/disk_quota.py:66-87,118-165`；并不按完整缓存数计量 |
| 现有 snapshot／persistence／quota 测试覆盖复用、页与 cursor、重启、文件拒读、pin、发布失败、计量与删除失败，但没有 LRU 场景 | `sbtd-runtime/tests/test_report_snapshot.py:75-330`、`test_snapshot_persistence.py:29-494`、`test_disk_quota.py:107-361` |
| serve／export 必须回归：线程池、HTTP 查询与旧 ID、超额复用、冷 ID 错误、导出 pin 与重启下载 | `sbtd-runtime/tests/test_serve.py:192-294,607-660`、`test_exports_http.py:71-125,300-320,359-413`、`test_export_store.py:219-293`；另核对 `test_csv_export.py` 与 `test_export_reconciliation.py` 的覆盖入口 |

### 实现时必须小心的差异与开放问题

1. 不能只把 `_snapshots` 换成有界字典：当前启动、复用、sweep 都依赖它包含所有对象。三条路径必须一并切到轻量索引，不得另藏完整载荷。
2. `_read` 兼做文件校验和热缓存更新。需区分正常读取与启动／强制清扫：后两者只用临时对象；正常读取通过安全与 TTL／pin 判断后才登记、更新 LRU。身份命中必须同时存在完整对象，防止逐出后 KeyError。失败访问不发布半项，不把失效旧载荷留在缓存。
3. 当前坏文件拒读会弹出 `_validated`，但不移除 `_snapshots` 旧对象；§6 明确要求完整缓存也失效。该差异属于本实现范围，不扩展成文件身份五字段未变的漏洞修复。轻量候选不能成为跳过磁盘核验的理由。
4. sweep 要先按轻量过期时间与 pin 过滤；删除前完整复核。成功同时清理索引／载荷／校验项并记 Gone；删除失败保留候选，下次仍可清扫。冷清扫不可逐出热读对象或改变 LRU 次序。
5. 复用从索引筛选后沿 get 核验，避免淘汰触发新 ID／重复占盘；不能在遍历可变索引期间直接删改导致迭代失效。冷 ID 不在启动索引也仍应沿受控路径读盘，不能把索引当存在性白名单。
6. `get` 的 deepcopy 和分页复制发生在取得私有对象之后；并发淘汰只能断缓存引用，不能清空或原地改写读者对象。`create_or_reuse` 新建时直接返回对象的既有限制不顺带改变。
7. `test_expired_cache_is_dropped_without_evicting_snapshot` 当前还断言过期对象留在 `_snapshots`。后续保留 410、磁盘保留、校验失效等行为证据，删除受影响的偶然内部驻留断言，不重新钉死旧实现形状。其余无关测试不清理。
8. serve 默认构造、defer_sweep 和 quota 回调已经可承载内部改动；优先不改这些生产文件，以回归证明衔接。恢复 pin 先于清扫的库接口保留，不声称现有 ExportStore 自动恢复在途作业。

对照后未发现必须改契约／schema／PRD 的开放问题。OpenAPI 中 createReportSnapshot 相对 507 的复用优先级尚未定义，这是既有 HTTP 契约边界；本 PR 保留库与 statistics 的现状，不新增 POST 路由或替契约作决定。后续若发现必须改变契约／schema／PRD 才能实现的分歧，记录开放问题并停止该部分扩展，另开 PR 等用户决定。

## 后续实现计划与预期将改的文件

以下均为预期，不是本轮已改。

| 文件 | 计划 |
|---|---|
| `sbtd-runtime/report_snapshot.py` | 默认 8 条标准库 LRU、内部正整数容量参数、轻量索引；统一发布／冷读／失效／逐出；迁移启动、复用与 sweep，保留共享锁及复制接口 |
| `sbtd-runtime/serve.py`、`sbtd-runtime/disk_quota.py` | 必要衔接检查项，当前预计无需生产改动；保持 serve 默认 8 与延后清扫装配、quota 原回调顺序／磁盘计量。仅后续证明现接口确有缺口且仍属 §6 时作最小修改，不加配置或新策略 |
| `sbtd-runtime/tests/test_report_snapshot.py`、`sbtd-runtime/tests/test_snapshot_persistence.py` | 小容量 LRU、冷读／复用、启动无完整驻留、安全拒读、TTL／pin／隔离与发布失败回归 |
| `sbtd-runtime/tests/test_disk_quota.py` | 冷快照清扫、失败保留、内存逐出不释放磁盘字节、超额复用与 507 |
| `sbtd-runtime/tests/test_serve.py`、`sbtd-runtime/tests/test_exports_http.py`、`sbtd-runtime/tests/test_export_store.py` | 默认容量与真实 HTTP 冷读／翻页／导出、在途 pin 与淘汰交错、终态释放；只补既有覆盖缺口 |
| `sbtd-runtime/spec/rc5-snapshot-eviction-scenarios.md`（计划新增） | 沿既有 Markdown 场景形式，中文说明＋英文 Given／When／Then，记录 §6 行为并映射定向测试；不改旧文档任务或 ADR |
| `CHANGELOG.md`、`CHANGELOG.zh.md` | 后续验证后各补 rc.5 本实现条目，与既有文档条目区分，不重写历史 Deferred，不提前报发布完成 |
| `ai/tasks/v2.1.0-rc.5-snapshot-eviction-impl/task.md`、`ai/tasks/index.md` | 本任务持续记录真实轮次与证据；index 只由正式生成器维护 |

顺序：先完成生产编辑前 Gate、保留行为基线与高风险失败测试；实现有界缓存和索引，再接冷读／复用／sweep；随后运行定向 unittest、真实 serve 与内存观察，补双语实现条目并送独立安全评审。`test_csv_export`／`test_export_reconciliation` 作为现有回归入口，不预设要改渲染、序列化或前端文件。

## 验收标准（后续实现轮，尚未执行）

1. §6.1：每次操作结束后完整缓存不超过 8 条；成功创建／发布或读取更新 LRU，容量 2 时 A、B、读 A、建 C 应逐出 B。失败不发布半项；隔离测试容量只接受正整数（排除 bool、零、负数和非整数），serve 固定默认 8，无新配置面。
2. §6.1：启动处理超过 8 份合法文件，仍逐个完整校验，只留轻量索引，完整缓存为空，不累积 dataset／rows／public_view。索引不是另一份载荷缓存；不新增磁盘 manifest，不宣称少读了磁盘。
3. §6.1：逐出仅断内存引用，磁盘文件字节不变、共享占用不减少；不能以内存压力删未过期文件或释放配额。
4. §6.2：有效被逐出 ID 通过 get／dataset_page／pin／复用仍可冷读，不误报 404／410。原安全检查不减弱；热文件变化重新验证，缺失／坏文件拒读并失效载荷与校验项，不删除坏文件；`_validated` 不留已逐出 ID。
5. §6.2：索引查候选后读盘核验，淘汰后相同查询仍复用原 ID，不多建文件、不多占盘；过期不复用。新建仍在完整写入、fsync、原子发布成功后登记，I/O 失败保留原错误与已有文件。
6. §6.3：原 snapshot_id、digest、public_view、全量页、cursor、导出和 expires_at 一致，不能以最新统计重建旧 ID。命中／逐出／重载／重启均不续期，仍从原 created_at 起算 24h。
7. §6.3：pin 只保护磁盘生命周期，被 pin 对象也可逐出且不能绕过容量上限；冷重载可跨过期读取。多引用、恢复引用先于启动 sweep、最后 release 恢复正常 TTL 判断均不变，前端固定 ID 不等于后端 pin。
8. §6.3：sweep 遍历轻量索引，不漏冷快照；仅对过期未 pin 候选强制完整校验与身份复核。冷清扫不污染 LRU，未过期项不做完整重读；删除成功同步清理所有内存条目并保留 Gone，删除失败保留候选与剩余字节。
9. §6.3：已知过期未 pin 仍为 410，缺失／坏文件仍为 404；不新增跨重启 tombstone。启动／新建前清扫时机、共享配额、80% 预警、507、坏／未知版本／未知文件／链接保留规则不退化，不加后台定时器。
10. §6.3：沿共享锁协调索引、缓存、校验、pin／release、发布与 sweep；并发读取／淘汰／导出不出错页或 KeyError。读者已持有对象不被清空或原地改写；get 与分页的 deepcopy 隔离不变。
11. §6.4：定向 unittest、隔离临时 HOME 的真实 serve smoke，以及容量外瞬时对象／单个大快照峰值证据齐备，且适用 strict Gate 与独立评审闭环后，才可声称实现完成。缓存条数不是 RSS 上限，不以引用释放推断 RSS 立即下降；CI、合入、部署、发布分别记录。

## 计划中的测试证据

已对照旧文档任务的实现方案、测试计划和“后续实现”验收重写下表；全部尚未执行，不沿用历史通过结论。

| 场景 | 预期证据 | 计划映射 |
|---|---|---|
| 小容量与成功访问排序 | Given 容量 2 的 A／B；When 读 A 再建 C；Then B 只移出内存，冷读返回原数据，磁盘字节不变；失败发布不留下半项 | `test_report_snapshot`、`test_snapshot_persistence`；容量边界与 `_validated` 同步失效 |
| 超过 8 份的启动 | Given 多份未过期文件；When 重启；Then 完整缓存为空、全部 ID 可冷读，连续访问不超 8；启动每个临时载荷可释放 | `test_snapshot_persistence`；对象引用观察与单独内存诊断 |
| 复用／分页／cursor／副本 | Given 已被逐出的原 ID；When 重复查询、沿旧 cursor 翻全页、修改返回副本；Then 原 ID／digest／expires_at／页数据不变、不增文件，后续读取不受副本修改影响 | `test_report_snapshot`、`test_snapshot_persistence`、现有 `test_csv_export` |
| 冷／热安全拒读 | Given 原文件；When 损坏、未知版本、删除、链接、替换或 fd 身份变化；Then 拒读、不返旧载荷、不删文件；恢复合法文件后按完整校验读取 | `test_snapshot_persistence`；沿用异源 ctime 回归，Linux 注入不冒充 Windows 实测 |
| TTL／pin／恢复引用 | Given 多引用或恢复引用；When 淘汰、到期、逐个 release；Then pin 不豁免容量，跨期可冷读，最后 release 后恢复 410／可清扫，命中不续期 | `test_snapshot_persistence`、`test_export_store` |
| 冷清扫与配额 | Given 冷过期、热未过期、坏／未知文件；When sweep、删除失败或准入；Then 只删除有效候选，LRU 不变，失败保留重试，坏文件计量，超限新建仍 507；超额冷复用不增盘 | `test_disk_quota`、`test_snapshot_persistence`、`test_exports_http` |
| 并发与在途导出 | Given 读者／导出持有对象；When 读、逐出、sweep 交错；Then 对象数据不改写、页不串、pin／release 正常；任务取消／失败后引用释放 | `test_export_store`、`test_report_snapshot`、`test_serve`；事件屏障而非耗时竞赛 |
| 真实 serve 链路 | Given 隔离临时 HOME／runtime 与真实采集测试数据；When 配对后建超过 8 个不同快照，再读最早 ID、沿旧 cursor 翻页并导出 CSV；Then 与淘汰前 public_view／digest／页／导出内容一致，重启仍可读 | `test_exports_http` 的真实进程辅助设施＋一次性 smoke；通过 statistics/query 建快照，不新增 snapshot POST |
| 导出保留回归 | Given 原 ID 与已完成导出；When 淘汰、重启、下载或同 key 重放；Then 原 export_id／字节摘要／保留期不变，404／410 与准入顺序不变 | `test_exports_http`、`test_export_store`；现有 `test_csv_export`、`test_export_reconciliation` 定向回归，renderer 能力缺失据实区分 |
| 内存边界 | Given 固定大小合成快照及单个大快照；When 启动、超过容量、冷读并有在途副本；Then 记录完整驻留对象数、Python 分配量、RSS 与峰值，分清索引／_gone／临时对象／读者副本不在 8 条内 | 一次性隔离诊断；不设不稳定 RSS 下降永久断言，不扩大为百万规模或全仓性能验收 |

计划命令（仓库根，后续执行）：

```sh
PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_report_snapshot test_snapshot_persistence test_disk_quota
PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_serve test_exports_http test_export_store test_csv_export
PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_export_reconciliation
```

真实 smoke 走 `POST /api/v1/statistics/query`、`GET /api/v1/report-snapshots/{snapshot_id}`、`GET /api/v1/report-snapshots/{snapshot_id}/dataset`、`POST /api/v1/exports`、导出查询与下载；保留真实鉴权，不输出票或凭证。内存诊断保留输入规模、平台、对象数、分配／RSS 指标及证据限制，不能用 HTTP 200 单独证明驻留上限。后续正式报告按既有规则保存 raw 与同 stem 中文汇总，并绑定当轮真实 SHA／worktree；本轮不生成这些报告。

## Strict Book Gate Plan

本轮只做记录与计划，尚未开始生产代码编辑。下表不把计划当执行，不把作者自审当独立安全评审。

| Gate | 客观触发条件与阶段 | 本轮状态／后续证据 |
|---|---|---|
| DDD | 完整 grill 或领域边界不清，需求稳定前 | not-needed：未完整 grill；沿用既有快照／缓存／磁盘生命周期，后续发现歧义先停对应扩展 |
| DDIA | 跨请求缓存、持久数据所有权与恢复，设计稳定前 | confirmed：本轮调用 Skill 并作计划级自审，详见下节；不是实现或独立安全批准，后续结构变化须复核 |
| Legacy safety | 既有读取／清扫／配额高风险行为，首次行为修改前 | pending：已读现状；实现轮先建立保留行为与故障安全网，记录真实失败原因 |
| Refactoring／ponytail | strict 首次生产编辑前 | pending：实现轮审查最小内部接口、单一锁与可读性，不引入缓存框架；本轮无生产编辑 |
| BDD／TDD | 用户可见旧 ID／导出／错误语义，实施前 | planned：沿既有 Markdown 中文场景＋英文关键词，落实上表并先补高风险失败测试；不新增 runner |
| Project validation | 本轮记录及后续实现各自的指定验证 | 本轮仅指定工作流／记录校验；后续 snapshot／quota／serve／export 与内存证据 pending |
| 独立安全评审 | 文件删除、安全校验、共享锁及导出引用交界，合入前 | pending：后续独立人工或 Reviewy 审查；本轮不调用子代理 |
| Release readiness | 运行时变更，测试门禁后、完成／发布前 | pending：本轮未实现，不是发布就绪；明确内存／冷读／平台证据边界 |
| CI／合入 | 实现 PR 最终提交 | pending：本轮不提交、不推送、不开 PR；旧 HEAD 的验证不证明未来代码 |

### DDIA Data Design Review

Status：confirmed（计划级作者自审）。数据所有者是 SnapshotStore，磁盘文件是事实源；轻量索引和 LRU 可在重启重建。写路径仍先原子发布，再登记索引与完整缓存；读路径完整校验后按 TTL／pin 决定可读，失败不发布缓存，坏文件不自动删除。共享 RLock 串行化缓存／索引／引用／清扫，导出读者继续持自己的对象，不能被淘汰改写。

复用以 query_hash／dataset_fingerprint 找候选后读盘核验，保留原 ID 和期限，不新增重试或去重服务。无 schema、迁移、回填或新 manifest；回退恢复旧全量驻留，仍读现有格式且不删磁盘。观察只需本地缓存数、校验／错误、磁盘计量与峰值证据，不加遥测或自动修复策略。必需测试为上表冷／热读取、失败发布、引用、删除失败、并发与真实 serve；尚未执行。

风险与恢复边界：多查询可能在 8 条间反复冷读，共享锁内 I/O 可能增加等待；索引、_gone、大快照、在途对象与返回副本仍占内存。释放 Python 引用不等于 RSS 立即下降；不拆锁或跳过校验换取未经证明的收益。本轮不证明性能收益、跨平台耐久性、部署或发布就绪，回退不授权清空数据。

## 验证证据

Evidence Source：developer-local；Source Revision：dirty（新增任务记录）；Evidence Publication：local-only；Environment Alignment：not-needed（本轮不部署）。基准 SHA 与分支见上文。rtk：skipped-for-report，使用指定原生命令保留真实输出；本节是本地证据表，不是 CI 或正式 PR-head 报告。

已执行只读核对 ADR 全文、相关契约／PRD、双语 CHANGELOG、旧文档任务和当前源码／测试；目标 task 不存在，父目录和 index 非链接，index 已跟踪、两个目标路径均无 ignore 匹配。已用 write 亲手建立本任务。未改生产代码、测试、ADR、OpenAPI、CHANGELOG、PRD、数据字典或旧任务。使用了会话内 todo 清单工具，未调用任务状态写 API；未调用子代理或 find，未执行 Git 写命令。

| 命令／检查 | 实际结果 | 退出码 |
|---|---|---|
| `git status --short`、`git branch --show-current`、`git rev-parse HEAD` | 起始干净，分支匹配，HEAD 为上述基准 | 0 |
| `namei -l`（index 与新任务父路径）；`git ls-files --stage --`（两个目标）；`git check-ignore -v --no-index --`（两个目标） | index 为普通文件 100644；父目录无链接，新任务目录尚不存在；无 ignore 匹配 | 1（新目录不存在）／0／1（无匹配） |
| `TZ=Asia/Shanghai date --iso-8601=seconds` | `2026-11-11T22:27:32+08:00`，用于开始写文件的 created_at／updated_at 与 started 事件 | 0 |
| `python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); Path('ai/tasks/index.md').write_bytes(a); print('INDEX_REGEN', 'changed=%s' % (b!=a), 'rows=%d' % len(s._index_rows(r)))"` | `INDEX_REGEN changed=True rows=83`；82→83，只新增本任务导航一行；保留既有“旧格式事件，不追溯”提示 | 0 |
| `python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); print('INDEX_PREVIEW_SAME', Path('ai/tasks/index.md').read_bytes()==a, 'rows=%d' % len(s._index_rows(r)))"` | `INDEX_PREVIEW_SAME True rows=83`；逐字节一致，保留相同旧格式事件提示 | 0 |
| `python3 -B -c "from pathlib import Path; text=Path('docs/adr/0003-v2.1.0-rc.2-r2.0c-snapshot-persistence.md').read_text(encoding='utf-8'); present='## 6.' in text; print('ADR_READ_OK', present); assert present"` | `ADR_READ_OK True`；只读文本检查 §6 存在，Markdown 不当作 YAML 解析 | 0 |
| `python3 -B -c "import yaml; d=yaml.safe_load(open('sbtd-runtime/contracts/openapi.yaml', encoding='utf-8')); print('OPENAPI_PARSE_OK', 'paths' in d)"` | `OPENAPI_PARSE_OK True`；仅证明 YAML 可解析且含 paths，不是完整 API 或实现验证 | 0 |
| `python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts` | 99 项通过，失败 0、跳过 0；`OK`，41.792 秒 | 0 |
| `git diff --check`；`git status --short --untracked-files=all`；`git diff --stat`；`git diff -- ai/tasks/index.md` | 空白检查无输出；只有 index 修改与本 task 未跟踪；tracked stat 为 index 一行新增，diff 证实只加本任务。未跟踪 task 不在普通 diff --stat 中，未为此改 Git index | 0 |
| 专用 grep：新 task 的本机路径、禁用归因措辞、非“契约”目标用字 | 无匹配；按本轮列出的禁用项检查，未把禁用字面量写入仓库 | 工具成功，无 shell 退出码 |

以上为本轮实际执行结果，不是 CI。证据回填后再检查新写文字与空白；末尾计数 edit 只补模型表和推算说明，之后不再调用工具，不将计数编辑冒充重新测试。

本轮跳过实现测试、真实 serve、内存实测、前端／运行时 lint／build 与全仓测试：只写记录，不改程序。旧文档任务的 runtime 历史失败与平台缺口未重跑、不关闭。BDD：skipped（只列计划，未改长期场景）；Cross-repo context：not-needed（本仓内部，未跨仓）；API Contract：verified（仅只读表述核对、§6 存在与 YAML 解析）；Mock Strategy：none。Final Test Report／Run Summary MD：not-needed（仅 developer-local 证据表）；Final Full Rerun：passed（仅本轮指定的 99 项工作流测试，不是运行时全量）；Targeted Rerun：not-needed。独立安全评审、CI、合入仍待后续。

## 第 2 轮本地验证

Evidence Source：developer-local；Source Revision：dirty；Evidence Publication：local-only。基准 SHA 为 `5e5e0109922c96dc45852eb3dec18c7efcdf9ede`，分支 `feat/rc5-snapshot-eviction-impl`；Linux x64、Python 3.13.5。不是 CI、未来提交或发布证明。rtk：skipped-for-report，指定命令由一次性记录器原生执行并保留 stdout、stderr、退出码、时间与 worktree 绑定；未执行 Git 写命令，未调用 task 状态写工具、子代理或 find。会话内使用 todo 清单，不生成 active／handoff／developer。路径与 ignore 检查确认本任务 `reports/` 受既有规则保护，不改 ignore。

### 实际变更与 Gate

- `sbtd-runtime/report_snapshot.py`：默认 8 条 OrderedDict LRU，内部 `_cache_capacity` 只收正整数且排除 bool；轻量索引每项只有 expires_instant、query_hash、dataset_fingerprint，ID 为字典键。成功发布后登记；安全读取与 TTL／pin 判断全部通过后登记完整缓存与 fd 身份。逐出同步去掉 `_validated`，不触及磁盘或配额。
- 启动逐个强制完整校验、登记索引并释放临时对象；完整缓存为空。复用和 sweep 遍历轻量索引的稳定列表；候选沿 get 复核后再检查复用键及期限。未索引 ID 仍走受控路径读盘。冷清扫不登记完整载荷、不重排热缓存；删除失败保留候选，成功清理索引／缓存／校验并记 Gone。
- 缺失、坏文件和不安全路径拒读时同时失效完整载荷与校验项，坏文件不删；五字段完全不变的既有限制不扩展修复。get／分页 deepcopy 与新建直接返回对象的既有接口保持。pin 保护磁盘，不能豁免内存容量。
- 测试改动为 `test_report_snapshot.py`、`test_snapshot_persistence.py`、`test_disk_quota.py`、`test_export_store.py`；新增 `sbtd-runtime/spec/rc5-snapshot-eviction-scenarios.md`。双语 CHANGELOG 各新增唯一 rc.5 Changed／变更条目，紧跟原 ADR §6 文档条目；其余字节保持不变。
- `serve.py`、`disk_quota.py` 无需生产衔接修改：现有默认构造、defer_sweep、共享 quota 回调与恢复引用顺序可承载改动；真实 HTTP、默认装配观察及回归已执行。前端／static、OpenAPI、ADR、PRD、schema、数据字典、旧文档任务均未修改。
- DDIA Data Design Review：confirmed（作者自审）。磁盘为事实源，单 writer／共享 RLock 不变；先原子发布再登记，无迁移或新 manifest。Legacy Change Safety Review：characterized；明确问题报告与源码建立坏文件残留根因，既有安全／生命周期测试作为保留行为安全网；容量参数缺失与启动仍保留对象的红灯先于生产编辑。
- Refactoring Review：proceed / normal；仅拆轻量索引和完整缓存，无额外框架或生产测试 seam。Ponytail Review：无可删除的多余抽象；Code Readability Review 已按本轮改动检查职责、命名和故障注入闭包，未重排无关代码。
- BDD：traceable，中文场景＋英文关键词；测试映射见新增场景文档，无新 runner。Cross-repo context：not-needed；API Contract：verified（沿用既有路由与错误语义，不修改契约）。HTTP smoke Mock Strategy：none；文件故障注入与导出对账的既有 stub 单独标明，不冒充真实浏览器链路。
- Lessons 评估：本轮缓存失效／索引分离规则已经是 ADR §6 与持久场景的明确规则，不新增重复长期 lesson，不读取或建立作者身份。独立安全评审仍 pending，作者自审不替代独立评审。

### 命令、结果与失败记录

下表的 unittest 均实际使用 `python3 -B -m unittest`；运行时模块命令前置 `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:.`。初始红灯与 lint 失败保留真实原因，不把后续通过改写成首次即通过。

| 命令／检查 | 实际结果 | 退出码 |
|---|---|---|
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_report_snapshot.SnapshotTests.test_lru_eviction_preserves_pages_reuse_and_csv test_snapshot_persistence.SnapshotPersistenceTests.test_startup_indexes_all_files_without_retaining_payloads` | 生产编辑前红灯：2 项；1 error 为构造器不接受 `_cache_capacity`，1 failure 为启动 weakref 仍存活；是本轮新增功能的预期失败 | 1 |
| 上述两项加 `test_report_snapshot.SnapshotTests.test_cache_capacity_rejects_non_positive_integers` | 实现后 3 项通过，0.194 秒 | 0 |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_report_snapshot test_snapshot_persistence test_disk_quota` | 首轮 55 项，54 通过、1 Windows junction 跳过，3.005 秒；增强拒读／冷 pin 断言及 lint 修正后最终同范围 55 项，54 通过、1 跳过，3.103 秒 | 0／0 |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_serve test_exports_http test_export_store test_csv_export` | 71 项，70 通过、1 Windows junction 跳过，65.932 秒；并发读／淘汰／sweep／在途 CSV 交错通过。故障注入日志不代表测试失败 | 0 |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_export_reconciliation` | 2 项通过，0.258 秒；原输出明确 `existing worker stub (Playwright is not installed)`，不算真实 JPEG/PDF 浏览器渲染 | 0 |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B local://rc5-smoke.py` | 真实 serve HTTP、默认装配与内存诊断通过，16.344 秒；详情见下节与同 stem raw／中文汇总 | 0 |
| `python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts` | 99 项通过，43.113 秒；按指定原生入口执行，记录器额外提供 runtime PYTHONPATH，不替代测试实现 | 0 |
| `python3 -B -m unittest sbtd-runtime.tests.test_golden_contracts` | 66 项通过，0.439 秒；未修改 golden | 0 |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_snapshot_persistence` | 增强拒读／冷 pin 后定向 24 项，23 通过、1 Windows 跳过，1.505 秒；之后同范围纳入上面的最终 55 项 | 0 |
| `ruff check sbtd-runtime/report_snapshot.py sbtd-runtime/tests/test_report_snapshot.py sbtd-runtime/tests/test_snapshot_persistence.py sbtd-runtime/tests/test_disk_quota.py sbtd-runtime/tests/test_export_store.py` | 首次 3 个 lint 问题：新测试循环闭包 B023 两项、嵌套 with SIM117 一项；绑定默认参数并合并 with 后同命令 `All checks passed!`，未全仓格式化 | 1→0 |
| 正式 index 生成器写入（第 1 轮同命令） | `INDEX_REGEN changed=False rows=83`，保留原“旧格式事件，不追溯”提示；未手改 index | 0 |
| 正式 index 只读预览（第 1 轮同命令） | `INDEX_PREVIEW_SAME True rows=83` | 0 |
| `git diff --check`、`git status --short --untracked-files=all`、`git diff --stat` | 空白检查通过；只涉及上述生产文件、4 个测试、场景、双语 CHANGELOG 与本任务，index 无差异 | 0 |
| `git diff origin/main -- sbtd-runtime/tests` | 4 个测试文件共新增 346 行、删除 1 行；无测试函数删除，无无关断言削弱；唯一删除行见下表 | 0 |
| 双语 CHANGELOG 字节核对 | 各移除本轮新增的条目与空行后，与 `git show HEAD:<文件>` 字节完全相同：两项 True | 0 |
| `git diff --exit-code HEAD -- docs/adr docs/prd sbtd-runtime/contracts ai/tasks/v2.1.0-rc.5-snapshot-memory-eviction` | 无输出，保护文件无改动；完整 status 未出现数据字典或其他任务 | 0 |
| 专用 grep：本轮新写文字的本机路径、禁用归因措辞及非“契约”目标用字 | 新增条目／场景／源码测试范围无匹配；一次多路径 selector 检索包含历史 CHANGELOG，发现的历史文字未改动，随后单文件精确行范围复查无匹配 | 工具成功 |

原生报告与同 stem 中文汇总保存在本任务忽略的 `reports/`，共同后缀为 `-feat_rc5-snapshot-eviction-impl-<UTC时间>.json`／`.md`：`snapshots`（20261111T144259）、`serve-exports`（20261111T144305）、`reconciliation`（20261111T144512）、`smoke-memory`（20261111T144522）、`workflow`（20261111T144555）、`golden`（20261111T144703）、`persistence-final`（20261111T144731）、`snapshots-final`（20261111T144852）。初始红灯及 lint 原始输出保留于本会话，不伪造为 CI 报告；该两次为诊断，后续正式范围输出原样保留。Final Test Report／Run Summary MD：generated；Targeted Rerun：passed；Final Full Rerun：passed（本轮指定范围，包含两项平台跳过，不是全仓或跨平台全通过）。

### 真实 HTTP 与内存证据

真实独立 `serve --no-open` 进程、隔离临时 HOME／runtime、loopback、真实配对与 bearer／CSRF 鉴权。使用真实 EventStore 追加 golden 与 150 个合成事件；不是 parser fixture 或生产数据。经 `POST /api/v1/statistics/query` 创建 11 个不同快照；最早 ID 淘汰前后 public_view／digest／expires_at、3 页共 241 行与旧 cursor 完全一致，CSV 108284 字节逐字节一致，SHA-256 为 `4a36d80e063489333e974e50d27c32efb005bdb1ea0e579e25d27344ab263391`。原查询复用不增文件；真实重启后原快照、旧 cursor、原导出下载及导出期限一致。两个服务进程正常停止，退出码 0；未输出票或凭证。

覆盖路由为 health GET、session/pair POST、statistics/query POST、report-snapshots/{snapshot_id} GET、其 dataset GET、exports POST、exports/{export_id} GET 与其 file GET；逐 URI、状态码及字段证据在 smoke 同 stem 中文汇总。没有新增 snapshot POST 或生产调试端点。默认装配另用一次性观察真实 create_app 构造：容量 8，创建 10 个后完整驻留 8、索引 10；不以 HTTP 200 代替内部条数证据。

固定大小合成快照每份 500 个 task，共创建 12 份，操作结束驻留依次为 1、2、3、4、5、6、7、8、8、8、8、8。重启索引 12、完整缓存 0，weakref 观察启动同时存活载荷最多 1，处理完成全部释放。逐出原私有载荷后 weakref 已释放，读者副本仍有 500 行。单个大快照 5000 个 task、磁盘 6048576 字节，最终完整驻留 8、索引 13、Gone 0。tracemalloc 当前 19854409、峰值 36281265 字节，Linux ru_maxrss 96844 KiB；均为本次合成数据观察，不作性能保证，不断言 RSS 立即下降。

索引／_gone、校验临时对象、在途对象和返回副本不计入 8 条；单快照大小无新增上限。启动仍完整读盘及 checksum 校验，不宣称减少读盘量。无后台定时器、环境变量、CLI 或产品配置。

### 既有内部驻留断言调整

| 文件／用例 | 原断言含义 | 必须调整原因 | 保留行为证据 |
|---|---|---|---|
| `sbtd-runtime/tests/test_snapshot_persistence.py`：`test_expired_cache_is_dropped_without_evicting_snapshot` | `assertIn(snapshot.snapshot_id, store._snapshots)` 固定过期拒读后完整对象仍驻留 | TTL 拒读不能发布或保留失效完整缓存；驻留不再是磁盘存在性依据 | 原 410（SnapshotGone）、读取前校验命中、拒读后 `_validated` 失效全部保留；替换为磁盘文件仍存在。新 TTL／pin 用例另证完整缓存失效与最后 release 后 410 |

仅这一处调整既有驻留断言；其他既有测试函数和断言未删减。坏文件矩阵及原 corruption／异源 ctime／同大小同 mtime 改写用例新增完整缓存与校验项同步失效、坏字节仍保留断言；发布故障新增索引／缓存／校验无半项断言。

### 剩余门禁、风险与恢复边界

Release Readiness Review：blocked（发布门禁）。本轮指定本地验证通过，独立安全评审、CI、合入仍 pending；继续 checking、completed_at 为 null，不声称发布就绪。Windows junction 两项跳过；异源 ctime 是 Linux 故障注入，不冒充 Windows 实测。Playwright 未安装，沿用对账原 worker stub，不安装全局工具、不改 renderer 或 golden。未改 Dashboard，按范围跳过 npm test／build 与 static 检查；未做全仓性能／百万规模测试。

8 条可能增加冷读和共享锁等待；单个大载荷、轻量索引、Gone、在途副本仍占内存。磁盘格式不变，回退可恢复旧全量驻留且继续读原文件；不以回退为由删除快照。无契约／schema／PRD 分歧需要扩展，故未进入受禁文件修改。计数回填之前的验证不覆盖最后的纯记录计数 edit。

## 模型记录

| 轮次 | 模型 | 用途 | 模型调用 | 工具调用 |
|---|---|---|---|---|
| 第 1 轮 | `openai-codex/gpt-6-astra`（thinking high，主模型） | 只读核对、编写本任务、生成 index 与本地校验 | 17 | 71 |
| 第 2 轮 | `openai-codex/gpt-6-astra`（thinking high，主模型） | ADR §6 实现、定向测试、真实 HTTP／内存诊断、记录与本地验证 | 35（推算） | 99（推算） |
| 第 3 轮 | `openai-codex/gpt-6-astra`（thinking high，主模型） | 按 Reviewy NOT CLEAN 意见修正 task.md 措辞并回填本轮计数 | 6（推算） | 12（推算） |

计数方法：在 omp 会话日志中筛选 `role=assistant`、`provider=openai-codex`、`model=gpt-6-astra` 的消息计模型调用，同一记录内 `toolCall` 条目计工具调用。本轮只读 count.py 输出 `astra_assistant=15 astra_toolcalls=70 other_assistant={} model_usage={}`，退出码 0，没有写入仓库。统计后只有本次 edit 和一次纯文本收尾，因此模型调用按 A+2=15+2=17、工具调用按 T+1=70+1=71 推算。日志未记录其他模型，不另列模型行；find 未列入本轮工具，调用为 0。本次 edit 为最后一次工具调用，仅回填次数与推算说明；之后不再运行检查，前述验证截止于计数回填前，不将回填称为重新测试。

第 2 轮计数：只读 count.py 对本轮 sessions-r2 输出 `astra_assistant=33 astra_toolcalls=98 other_assistant={} model_usage={}`，退出码 0，未写仓库。统计后仅本次 edit 与一次纯文本收尾，故模型调用按 A+2=33+2=35、工具调用按 T+1=98+1=99 推算；第 1 轮 17／71 原样保留。本次 edit 是最后一次工具调用，只回填本轮次数与推算说明，之后不再运行工具或将计数回填冒充重新验证。

第 3 轮计数：只读 count.py 对本轮 sessions-r3 输出 `astra_assistant=4 astra_toolcalls=11 other_assistant={} model_usage={}`，退出码 0，未写仓库。统计后只有本次 edit 和一次纯文本收尾，故模型调用按 A+2=4+2=6、工具调用按 T+1=11+1=12 推算，与第 2 轮相同；第 1 轮 17／71、第 2 轮 35（推算）／99（推算）原样保留。日志只出现 gpt-6-astra，不另列其他模型行；find 未列入本轮工具，调用为 0。本次 edit 为最后一次工具调用，仅追加本轮模型表行与计数说明；计数回填前整份 task.md 的禁用词及非“契约”目标用字 grep 无匹配，之后不再运行工具，不将计数回填冒充重新验证。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-11T22:27:32+08:00 | planned | checking | started：Lord 在合入 #212（合并提交 e4c7670，提交时间 2026-11-11T22:21:57+08:00）之后在群内调度开始快照内存回收实现 PR，本轮只写 task.md 及生成式 index，不开始实现 | 已核对分支、HEAD、路径安全、ADR／契约与源码；INDEX_REGEN changed=True rows=83，INDEX_PREVIEW_SAME True rows=83，ADR_READ_OK／OPENAPI_PARSE_OK True，指定 unittest 99 项通过，diff 空白与范围检查通过、新写文字 grep 无匹配；developer-local，非 CI，详见验证证据。 |
| 2026-11-11T22:38:59+08:00 | checking | checking | 按 Lord 2026-11-11 22:36（北京时间）的范围确认开始实现：以 task.md 范围为准，允许一并修复坏文件完整缓存未清除，不得再扩大范围 | 分支／路径匹配；本轮快照配额 55 项（1 平台跳过）、serve／导出 71 项（1 平台跳过）、对账 2 项、工作流 99 项、golden 66 项均退出 0；真实 HTTP 11 个快照／3 页／CSV／重启及条数烟测通过；ruff 修正后通过；INDEX_REGEN changed=False rows=83，预览 True；独立安全评审、CI、合入未完成，详见第 2 轮本地验证。 |
| 2026-11-11T23:19:39+08:00 | checking | checking | 按 Reviewy 意见修正：对照头 `187ed70f58aa5771ee239126033e9b7138ddb4e8` 的 NOT CLEAN，改正 task.md 三处措辞（两处群内「安排」改为「群内调度」／「在群内调度」；删去无日期的「用户已在群内要求开始本实现」半句，改为从 Lord 于 2026-11-11 22:36（北京时间）确认写起）。 | 三处已改；禁用词复查除指定三处外无其余匹配，时间无模糊表述；未改代码／测试／CHANGELOG／契约文件或其他仓库文件；索引生成、提交与 CI 由编排方处理，本轮未执行。 |
