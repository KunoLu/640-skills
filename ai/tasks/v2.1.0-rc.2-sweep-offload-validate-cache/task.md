---
schema_version: 1
id: v2.1.0-rc.2-sweep-offload-validate-cache
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：采用 strict；主会话为唯一 writer 与验证 controller，不启动子代理、不使用 advisor；提交、推送与开 PR 由编排方执行。
status: checking
branch: perf/sweep-offload-validate-cache
created_at: '2026-10-27T13:56:03+08:00'
updated_at: '2026-10-27T15:08:46+08:00'
completed_at: null
---

# PR-2：快照 sweep、线程池与校验缓存

## 决定

- 用户 2026-10-27 群内确认（范围 B＋C＋D），Lord 记录。
- 编排方整理：未完整调用 grill-with-docs；范围、保留行为与验收明确，无新增领域歧义。

## 范围与边界

- B：仅对内存 expires_instant 已过期候选完整校验后清理；不按 mtime／size 筛选，不改变未知磁盘文件、坏文件及 temp 配额处理。
- C：三个统计／快照 HTTP 路由的同步工作移到现有线程池机制，以信号量限制并发；错误映射、响应体与状态码不变。
- D：以设备、inode、size、mtime_ns、ctime_ns 文件身份缓存校验；身份变化重新校验，删除／过期清理；线程安全且返回数据隔离。
- 不改 PRD、契约、schema、ADR、前端，不实现 A、401 重新配对或内存淘汰，不移除快照 deepcopy。
- 只写本工作树与 `/tmp/pr2-perf-*` 临时产物；参考 benchmark 只读；不联网、不安装、不改全局配置、不执行 Git 写命令或 gh，不读 dotenv、环境秘密或会话 jsonl 内容。
- 沿用参考 task 文档格式并用 TaskDocument 解析；不写 active／index／handoff／ignore／身份，不声称 TaskStore 自动恢复。最终仅追加 checking，completed_at 保持 null；独立复核由编排方另行安排。

## 代码事实

- 入口 HEAD 为 `5eec9977f90f3c171bd9c7b4a5587ffc3aa3696f`，分支匹配且工作树干净；下列原始行号对应入口源码，变更后位置见实现记录。

- 读代码推断，未实际运行：`report_snapshot.py:701-747,802-831,941-979` 在 sweep／get／分页重复读取与校验；`export_store.py:493-526` 已按内存 expiry 预筛。`disk_quota.py:118-165` 的计量独立枚举普通文件，B 不改变坏文件、未知文件、temp 的计量或清理授权。
- 读代码推断，未实际运行：`serve.py:526-579` 的三个 async handler 同步执行加载／统计／读取；导出已有 run_in_threadpool 先例。每 app 共用上限 4 的信号量，先取得名额再提交线程，限制数据集加载和排队占用；共享 quota RLock 仍串行化 store 临界区，不声称吞吐线性提升。
- 读代码推断，未实际运行：D 只缓存内存索引已有 ID，键含 st_dev／st_ino／st_size／st_mtime_ns／st_ctime_ns；身份不变复用已校验对象，失效及过期清除。内部对象不外泄，get 深拷贝，分页只复制返回行；删除前强制完整校验。启动仍加载全部快照，不加淘汰策略。
- DDIA Data Design Review=confirmed；磁盘为事实源、无 schema／迁移／回填变化，异常沿原路径传播。Legacy Change Safety Review=characterized：B 新回归 red（1 test，0.036s，exit 1），实际发现读取两个 ID 而非仅过期 ID；C／D 各自先 red 后改。Refactoring Review=proceed，normal，无独立重构。
- Python LSP references 实际返回无 language server；改用源码调用点核对。BDD=skipped：内部调度与校验优化，不改变 API 语义；要求的性能与隔离场景永久落在现有 unittest 文件中。install-and-use.md:94-110 仍准确，保持不改。

## Book Gate Plan

| Gate | 客观触发／阶段 | 本轮状态 |
|---|---|---|
| book-ddd-distilled-modeling | 完整 grill 或领域歧义 | not-needed；未完整 grill，既有语义明确 |
| book-ddia-data-design | 跨请求校验缓存，设计前 | confirmed；已输出独立可见 review，磁盘事实源、文件身份失效、共享锁、隔离返回，无迁移 |
| book-legacy-change-safety | 既有性能行为，修改前 | characterized；B／C／D 均有实际 red 与 green，原错误映射和安全测试保留 |
| book-refactoring-pass | 生产代码编辑前 | proceed；normal，无独立重构，沿用库与 handler 边界 |
| book-release-readiness | 运行行为变化，验证后 | 验证后执行，不声明部署或发布完成 |
| ponytail／TDD／BDD | 实现前 | 最小修改，复用既有测试文件与线程池惯例 |
| project-validation | 修改后 | 定向、根包装、三片 CI、smoke 与 TaskDocument |
| Code Readability Review／独立 review | check | 主会话自核不冒充独立复核；交付保持 checking |

## 验证

- 按要求执行定向与三片 CI，逐项记录命令、exit、计数、耗时；环境基线与新增失败分开，不削弱断言。

### 实现与回归

- B：sweep 按内存 expires_instant 与 pin 预筛，过期候选以 force_validate 完整读取／校验，身份复核后删除；未过期文件不调用 `_read`。D 元数据在强制读取前移除，失败也不恢复旧缓存。
- C：三个同步 response 函数把 load_dataset、query、store 读取、public view、envelope 与 JSON 序列化全部放在线程内；handler 先取得同一个 4 槽信号量，异常返回原 400／404／410／507 映射。未改变导出路由。
- D：复用 `disk_quota.file_identity` 五字段元组；命中仍检查路径、普通文件与所有权，miss 在读前、读后及发布缓存前复核身份。缓存只有每个已索引 ID 的身份元数据，不另存整份快照；解析对象更新原内存索引。get 返回 deepcopy；dataset_page 只 deepcopy 当前页。读取过期无 pin、强制 sweep、篡改或缺失均移除校验元数据，不新增快照淘汰。
- 新测试：`test_sweep_reads_only_expired_candidates`、`test_statistics_workers_are_offloaded_and_bounded`、`test_unchanged_file_is_validated_once_and_returns_isolated_data`、`test_cached_file_rewrite_with_preserved_size_and_mtime_is_rejected`、`test_cached_file_replacement_is_revalidated`、`test_expired_cache_is_dropped_without_evicting_snapshot`。
- red／green：B 1 test 0.036s exit 1 → 0.032s exit 0；C 1 test／4 subtest 11.346s exit 1 → 3.821s exit 0；D 3 tests 0.074s exit 1（重复解析计数 5／2，篡改拒读原本通过）→ 快照两模块 30 tests 1.297s exit 0、skip 1。耗时来自原生 unittest，不是 HTTP 性能基准。
- C 为真实 handler 请求与数据库／快照工作，mock 只用于包裹原函数记录线程和阻塞屏障，不替换返回结果；每组 8 个请求、4 组均完成，最大并发 4，事件循环能在 worker 阻塞期间执行。不是 socket 并发上限的独立测量。
- lint 首轮发现新增测试闭包 B023 共 5 处；明确绑定本轮观察器依赖后再验。未修改已有断言。

### 限定验证结果

原生命令通过临时 launcher 逐条执行，设置 `PYTHONDONTWRITEBYTECODE=1`、`PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:.`、`TMPDIR=/tmp/pr2-perf-tmp`，子进程最长 510 秒。rtk=skipped-for-report。早期 red／green 使用 unittest 默认临时夹具，夹具已自行清理；后续正式验证统一限制临时根。

| 命令 | exit | 原生计数／耗时 | 墙钟 | 证据 stem |
|---|---|---|---|---|
| `python3 -B -m unittest test_report_snapshot test_snapshot_persistence test_disk_quota test_serve test_exports_http test_export_store test_export_render -v` | 0 | 96 tests，47.591s，skip 2 | 47.807s | `/tmp/pr2-perf-targeted` |
| `python3 -B -m unittest tests.test_sbtd_runtime_r1_stats_api -v` | 1 | 79 tests，4.406s，fail 1，skip 1 | 4.567s | `/tmp/pr2-perf-wrappers` |
| `python3 -B /tmp/pr2-perf-smoke.py` | 0 | 真实 serve：24 个混合请求全部 200；篡改后两读取路径 404，恢复后 200；CSV 202→ready→下载 200 | 3.804s | `/tmp/pr2-perf-smoke` |

`/tmp/pr2-perf-smoke.py` 与 `/tmp/pr2-perf-library-smoke.py` 均为临时脚本，已由会话 1 删除；结果文件保留。

- 根包装仅 stats_api 包含本轮 snapshot 测试；serve／disk_quota／export_store／export_render／exports_http 未找到对应根包装，已由定向模块直接运行。
- 根包装失败恰为 `test_iana_queries_and_dst_work_without_system_timezone_data`，与编排方整理的缺 tzdata 基线一致；不重跑干净 main 来重复确认。定向 507／400 测试通过，未出现子进程找不到 serve 的失败。
- smoke 使用真实 loopback serve 与合成审计数据；不输出配对凭据、不使用 renderer 替身，不代表浏览器或生产环境验证。
- 库级真实路径 smoke：`python3 -B /tmp/pr2-perf-library-smoke.py`，exit 0，墙钟 3.253s；800 合成事件、25 个已有快照，新 query 的 `_read` 调用 0；新文件 1,585,123 bytes，9 页／839 行仅 json.load 1 次。带 profiler 耗时 query 0.227s、全分页 0.101s，且与 CI 同机运行，不作为独立吞吐基准或提升比例。参考 benchmark 只读，未执行或修改其文件；Reviewy 环境的既有测量不冒充本轮实测。
- 真实 HTTP smoke 的 24 个混合请求墙钟 0.124s，CSV 下载 44,343 bytes；这是小合成夹具，不外推生产规模。raw／同 stem 中文汇总均保留 `/tmp/pr2-perf-smoke.json`／`.md` 与 `/tmp/pr2-perf-library-smoke.json`／`.md`。
- `ruff check --no-cache sbtd-runtime/report_snapshot.py sbtd-runtime/serve.py sbtd-runtime/tests/test_snapshot_persistence.py sbtd-runtime/tests/test_serve.py`：修正新增闭包绑定后 exit 0，0.014s，All checks passed；证据 `/tmp/pr2-perf-lint.json`／`.md`。
- 会话 2 再跑同一 `ruff check --no-cache` 四文件命令：exit 0，墙钟 0.016s，All checks passed；raw `/tmp/pr2-perf-session2-lint.json`，不覆盖会话 1 结果。
- 会话 3 再跑同一 `ruff check --no-cache` 四文件命令：exit 0，墙钟 0.019s，All checks passed；raw／同 stem 中文汇总 `/tmp/pr2-perf-session3-lint.json`／`.md`。
- 会话 3 定向命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_report_snapshot test_snapshot_persistence test_disk_quota test_serve test_exports_http test_export_store test_export_render`，经同一 launcher 串行执行；exit 0，96 tests，50.188s，skip 2，墙钟 50.413s；raw／同 stem 中文汇总 `/tmp/pr2-perf-session3-targeted.json`／`.md`。本会话未修改运行代码或测试，不启动子代理、不使用 advisor。
- Code Readability Review：主会话自核完成；response helper 明确线程边界，`_get` 是只读内部对象入口，公开 get／分页复制返回值。ponytail-review：无可删除的抽象或依赖；复用 file_identity、共享 RLock、run_in_threadpool 与 Semaphore，未引入配置项或第二个缓存载荷。此自核不是独立复核。

### 更广验证与时限

- 原生 CI 入口各片独立命令，统一 `PYTHONDONTWRITEBYTECODE=1 python3 -B tests/run_ci.py --platform linux --shard N --shards 3 --output /tmp/pr2-perf-ci-N`；launcher 仅设置上述测试环境与 510 秒时限，不改 runner 或已有断言。
- 第 1 片 exit 124、墙钟 510.011s；原 inventory 842 项，stdout／stderr 中 590 项已记录结束（572 ok、1 FAIL、17 skipped），之后在 facade 测试中触及时限，未生成最终 native result。观察到的 FAIL 为 `MaterializeAuthorizationTests.test_link_text_change_is_refused`，属于既知基线类别；超时本身不归因产品代码。
- 第 2 片 exit 124、墙钟 510.012s；原 inventory 663 项，521 项已记录结束（511 ok、2 FAIL、8 skipped）；失败为 `MaterializeAuthorizationTests.test_replaced_link_with_identical_text_is_refused` 及缺 tzdata 测试，在 task-state 测试中触及时限，未生成最终 native result。
- 原片 raw 与中文汇总保留 `/tmp/pr2-perf-ci-1-run.json`／`.md`、`/tmp/pr2-perf-ci-2-run.json`／`.md`，inventory 保留原输出目录；不能把未结束用例或未生成报告写成通过。
- 补齐方式：临时 `/tmp/pr2-perf-ci-subpart.py` 读取原 inventory，复用 CI 的 discover、partition、fixture_unit、RecordedResult、required_native_cases 与 unpassed_required；按每原片三组从新夹具完整重跑，不从中断点续跑。每组都验证原集合不变、分组并集完整且无重叠；不修改仓库 CI 入口或权重，逐组独立命令且仍最长 510 秒。
- 第 3 片原生命令完整结束：exit 0，919 tests，482.762s，skip 10，墙钟 483.938s；required_native_failures 为空，selected 与逐例结果 ID 集合完全一致。raw `/tmp/pr2-perf-ci-3-run.json`／同 stem 中文汇总，以及 `/tmp/pr2-perf-ci-3/linux-3.json`／原生 `.md` 保留。
- 本轮所有报告均为 developer-local／dirty／local-only，基准 SHA 为入口 HEAD，不是新提交或 PR head；未设置 VALIDATION_SHA 的原生 CI 报告字段保持 null，外层 raw 与中文汇总明确记录真实基准 SHA、分支与 dirty 状态，不伪装干净 CI。

补跑命令：每行独立执行 `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/pr2-perf-run.py /tmp/pr2-perf-ci-L-run python3 -B /tmp/pr2-perf-ci-subpart.py N P /tmp/pr2-perf-ci-L`，L／N／P 对应下表；原 runner 不变，raw／中文汇总与每组 `result.json`／同 stem `.md` 均保留。

| L | N／P | exit | tests／skip／fail | 原生耗时 | 墙钟 |
|---|---|---|---|---|---|
| 1a | 1／1 | 0 | 42／0／0 | 375.484s | 376.507s |
| 1b | 1／2 | 1 | 349／11／1 | 139.044s | 140.110s |
| 1c | 1／3 | 0 | 451／28／0 | 142.931s | 144.023s |
| 2a | 2／1 | 0 | 220／5／0 | 137.441s | 138.466s |
| 2b3 | 2／2 | 1 | 208／4／1 | 166.651s | 167.834s |
| 2c3 | 2／3 | 0 | 235／5／0 | 154.976s | 156.180s |

- 全量汇总：七组 1a／1b／1c／2a／2b3／2c3／原第 3 片合计 tests／skip／fail 为 2424／63／2；2424 个 ID 恰等于全部 scope，无重叠、无遗漏，各组 selected 与逐例结果 ID 完全一致，required_native_failures 均为空。2a＋2b3＋2c3 的 663 个不重复 ID 恰等于原第 2 片 inventory。两项失败分别为 1b 的 MaterializeAuthorizationTests 链接竞态与 2b3 的 `test_iana_queries_and_dst_work_without_system_timezone_data`（原始错误 `No module named 'tzdata'`），均属已知环境基线，无其他失败；不宣称全绿。skip 按原生计数相加，原第 3 片 native skip 10、逐例 skipped 8，保留原报告差异。集合核对证据：`/tmp/pr2-perf-session3-inventory.json`；旧超时轮与旧 2b／2c 不重复计入。
- 1b 唯一失败 `test_link_text_change_is_refused` 的实际断言为 `link-mismatch != identity-mismatch`；属于编排方整理的 MaterializeAuthorizationTests 基线，未修改断言或链接代码。1a／1b 的 selected 与逐例结果集合相等，required_native_failures 均为空。
- 第一原片补跑集合实测核对：842 个不重复 ID，恰等于原 selected；合计 skip 39、fail 1，无遗漏。未将原超时轮与补跑轮重复计数。
- 编排方整理：会话 1 运行至 2026-10-27 14:52:36（+08:00）正常退出，看门狗记录 exited，非 kill，无 resume。编排方误判其已停止，于 14:46:46 启动会话 2；两会话在 14:46:46–14:52:36 并发约 6 分钟，均写过 task.md 与同名 2b／2c 产物，旧 2b／2c 可能交叉覆盖，不作为证据。两会话均已退出；会话 3 作为唯一 writer 以新标签 2b3／2c3 串行重跑并协调记录。代码与测试未在并发期间修改。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | 产出 | 会话文件 |
|---|---|---|---|---|---|
| 1 | ping | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-27T05-55-37-693Z_01a17bed-b25d-70a6-9e11-0820b747f20c.jsonl` |
| 2 | 会话 1 | openai-codex/gpt-6-astra（high） | 95／150 | B／C／D、测试与本 task | `2026-10-27T05-55-47-239Z_01a17bed-d7a7-71aa-8e5f-366dbf78b098.jsonl` |
| 3 | ping 2（会话 2 前） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-27T06-46-36-193Z_01a17c1c-5da1-76ee-a458-3b92b6ba6b9d.jsonl` |
| 4 | 会话 2（续完验证与收尾） | openai-codex/gpt-6-astra（high） | 22／59 | 补跑与本 task | `2026-10-27T06-46-46-887Z_01a17c1c-8767-7178-a2e3-0fd880f01aa4.jsonl` |
| 5 | ping 3（会话 3 前） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-27T07-00-29-348Z_01a17c29-1424-76b4-9c7a-c762fb814a42.jsonl` |
| 6 | 会话 3（唯一 writer 协调与收尾） | openai-codex/gpt-6-astra（high） | 未知（落盘时本轮尚未结束），待后续回填 | 重跑 2b／2c 与本 task | `2026-10-27T07-00-34-856Z_01a17c29-29a8-7179-8fad-f4309a2565e2.jsonl` |

编排方整理；ping 文件名仅经目录列表取得，未读取 jsonl 内容。

编排方整理，数据由编排方从会话 jsonl 统计：会话 1 assistant 消息 95、toolCall 150（read 49、edit 27、bash 26、eval 15、todo 9、write 7、grep 7、wait 7、glob 3）；会话 2 assistant 消息 22、toolCall 59（read 27、todo 10、bash 7、eval 7、edit 4、wait 2、glob 1、write 1）。会话 1／2 与 ping／ping 2 的 model_usage 均为 0，ping／ping 2 的 assistant 消息／toolCall 各为 1／0；模型均为 gpt-6-astra，未用 kimi／子代理／advisor。会话 1 正常退出，非 kill，无 resume；会话 3 尚未结束，计数不预估。ping 3 与会话 3 文件名仅经目录列表取得，未读取 jsonl 内容。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-27T13:56:03+08:00 | planned | in-progress | 编排方整理；主会话开始 strict 性能修复 | 分支匹配，入口干净；HEAD 为 5eec9977f90f3c171bd9c7b4a5587ffc3aa3696f；父路径无 symlink，task 尚不存在，ignore 无命中。 |
| 2026-10-27T15:08:46+08:00 | in-progress | checking | 编排方整理；主会话完成 B／C／D 与验证，进入检查 | 会话 3 唯一 writer；2b3／2c3 独立串行补跑，七组 2424 项无重叠且覆盖全部 scope，skip 63、fail 2 均属基线；ruff exit 0，定向 96 tests、skip 2、exit 0；独立复核尚未执行，不声明发布完成。 |
