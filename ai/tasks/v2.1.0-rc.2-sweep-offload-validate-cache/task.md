---
schema_version: 1
id: v2.1.0-rc.2-sweep-offload-validate-cache
workflow_mode: strict
mode_source: user
mode_note: 编排方整理：采用 strict；主会话为唯一 writer 与验证 controller，不启动子代理、不使用 advisor；提交、推送与开 PR 由编排方执行。
status: done
branch: perf/sweep-offload-validate-cache
created_at: '2026-10-27T13:56:03+08:00'
updated_at: '2026-10-27T17:09:33+08:00'
completed_at: '2026-10-27T17:09:33+08:00'
---

# PR-2：快照 sweep、线程池与校验缓存

## 决定

- 用户 2026-10-27 群内确认（范围 B＋C＋D；分钟不可考），Lord 记录。
- 编排方整理：未完整调用 grill-with-docs；范围、保留行为与验收明确，无新增领域歧义。

## 范围与边界

- B：仅对内存 expires_instant 已过期候选完整校验后清理；不按 mtime／size 筛选，不改变未知磁盘文件、坏文件及 temp 配额处理。
- C：三个统计／快照 HTTP 路由的同步工作移到现有线程池机制，以信号量限制并发；既有 query／快照错误映射与响应体不变，但 load_dataset 进入 try 后的条件性 500→400／507 变化见「load_dataset 行为变化与契约」。
- D：以设备、inode、size、mtime_ns、ctime_ns 文件身份缓存校验；身份变化重新校验，删除／过期清理；线程安全且返回数据隔离。
- 不改 PRD、契约、schema、ADR、前端，不实现 A、401 重新配对或内存淘汰，不移除快照 deepcopy。
- 只写本工作树与 `/tmp/pr2-perf-*` 临时产物；参考 benchmark 只读；不联网、不安装、不改全局配置、不执行 Git 写命令或 gh，不读 dotenv、环境秘密或会话 jsonl 内容。
- 沿用参考 task 文档格式并用 TaskDocument 解析；不写 active／index／handoff／ignore／身份，不声称 TaskStore 自动恢复。最终仅追加 checking，completed_at 保持 null；独立复核由编排方另行安排。

## 代码事实

- 入口 HEAD 为 `5eec9977f90f3c171bd9c7b4a5587ffc3aa3696f`，分支匹配且工作树干净；下列原始行号对应入口源码，变更后位置见实现记录。

- 读代码推断，未实际运行：`report_snapshot.py:701-747,802-831,941-979` 在 sweep／get／分页重复读取与校验；`export_store.py:493-526` 已按内存 expiry 预筛。`disk_quota.py:118-165` 的计量独立枚举普通文件，B 不改变坏文件、未知文件、temp 的计量或清理授权。
- 读代码推断，未实际运行：`serve.py:526-579` 的三个 async handler 同步执行加载／统计／读取；导出已有 run_in_threadpool 先例。每 app 共用上限 4 的信号量，先取得名额再提交线程，限制数据集加载和排队占用；共享 quota RLock 仍串行化 store 临界区，不声称吞吐线性提升。
- 读代码推断，未实际运行：D 只缓存内存索引已有 ID，键含 st_dev／st_ino／st_size／st_mtime_ns／st_ctime_ns；身份不变复用已校验对象，失效及过期清除。公开 get 深拷贝，分页只复制返回行；create_or_reuse 返回内部对象的限制见遗留项 N4。删除前强制完整校验。启动仍加载全部快照，不加淘汰策略。
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
- 编排方整理：会话 1 运行至 2026-10-27 14:52:36（+08:00）正常退出，看门狗记录 exited，非 kill，无 resume。编排方误判其已停止，于 14:46:46 启动会话 2；两会话在 14:46:46–14:52:36 并发约 6 分钟，均写过 task.md 与同名 2b／2c 产物，旧 2b／2c 可能交叉覆盖，不作为证据。两会话均已退出；会话 3 作为唯一 writer 以新标签 2b3／2c3 串行重跑并协调记录。代码与测试未在并发期间修改。会话 2 检测到 task.md 并发写入后停止写入，未追加 checking。

## 模型记录

| # | 轮次／用途 | 模型（thinking） | assistant 消息／toolCall | 产出 | 会话文件 |
|---|---|---|---|---|---|
| 1 | ping | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-27T05-55-37-693Z_01a17bed-b25d-70a6-9e11-0820b747f20c.jsonl` |
| 2 | 会话 1 | openai-codex/gpt-6-astra（high） | 95／150 | B／C／D、测试与本 task | `2026-10-27T05-55-47-239Z_01a17bed-d7a7-71aa-8e5f-366dbf78b098.jsonl` |
| 3 | ping 2（会话 2 前） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-27T06-46-36-193Z_01a17c1c-5da1-76ee-a458-3b92b6ba6b9d.jsonl` |
| 4 | 会话 2（续完验证与收尾） | openai-codex/gpt-6-astra（high） | 22／59 | 补跑与本 task | `2026-10-27T06-46-46-887Z_01a17c1c-8767-7178-a2e3-0fd880f01aa4.jsonl` |
| 5 | ping 3（会话 3 前） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-27T07-00-29-348Z_01a17c29-1424-76b4-9c7a-c762fb814a42.jsonl` |
| 6 | 会话 3（唯一 writer 协调与收尾） | openai-codex/gpt-6-astra（high） | 30／53 | 重跑 2b／2c 与本 task | `2026-10-27T07-00-34-856Z_01a17c29-29a8-7179-8fad-f4309a2565e2.jsonl` |
| 7 | Windows 修复 ping（15:47） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查记录 | `2026-10-27T07-47-30-842Z_01a17c54-219a-74fc-aeed-efa1b8875cff.jsonl` |
| 8 | Windows 修复会话 1（唯一 writer） | openai-codex/gpt-6-astra（high） | 44／93 | ctime 复现、修复、回归与本 task | `2026-10-27T07-47-35-402Z_01a17c54-336a-75ec-b3aa-17b83e6eefeb.jsonl` |
| 9 | Windows 修复 ping 2（16:09） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查记录 | `2026-10-27T08-09-30-877Z_01a17c68-45fd-73e7-afef-426eadc88448.jsonl` |
| 10 | Windows 修复会话 2（唯一 writer） | openai-codex/gpt-6-astra（high） | 24／58 | 范围补充、本 task 与 PR 描述文件 | `2026-10-27T08-09-41-054Z_01a17c68-6dbe-7654-82a7-0d3b673ea1de.jsonl` |
| 11 | Windows 修复 ping 3（16:31） | openai-codex/gpt-6-astra（high） | 1／0 | 连通性检查 | `2026-10-27T08-31-40-278Z_01a17c7c-8ef6-7497-ad5b-104cabaf4b11.jsonl` |
| 12 | Windows 修复会话 3（PR 描述文件订正，未改工作树） | openai-codex/gpt-6-astra（high） | 9／15 | 订正 PR 描述文件 | `2026-10-27T08-31-45-485Z_01a17c7c-a34d-70ee-8700-38157cec3e44.jsonl` |

编排方整理；ping 文件名仅经目录列表取得，未读取 jsonl 内容。

编排方整理，数据由编排方从会话 jsonl 统计：会话 1 assistant 消息 95、toolCall 150（read 49、edit 27、bash 26、eval 15、todo 9、write 7、grep 7、wait 7、glob 3）；会话 2 assistant 消息 22、toolCall 59（read 27、todo 10、bash 7、eval 7、edit 4、wait 2、glob 1、write 1）；会话 3 assistant 消息 30、toolCall 53（read 18、edit 8、bash 8、todo 8、eval 7、wait 2、glob 1、grep 1）。旧目录 ping／会话 1／ping 2／会话 2／ping 3／会话 3 的 jsonl 中 model_usage 记录数均为 0（实测）；是否存在未落盘的内部辅助调用不可核。ping／ping 2 的 assistant 消息／toolCall 各为 1／0；上述已统计会话模型均为 gpt-6-astra，未用 kimi／子代理／advisor。会话 1 正常退出，非 kill，无 resume；会话 3 计数按编排方统计回填，本轮未读取 jsonl 内容。ping 3、会话 3 及 Windows 修复轮的文件名仅经目录列表取得。

编排方实测（本修复目录）：三次 ping 的 assistant 消息／toolCall 均为 1／0；修复会话 1 为 44／93（read 36、edit 20、grep 10、eval 8、todo 8、bash 6、find 2、write 2、glob 1），正常退出、看门狗未 kill、无 resume；修复会话 2 为 24／58，修复会话 3 为 9／15。修复轮模型均为 openai-codex/gpt-6-astra（high）。修复会话 1、会话 2 的 jsonl 中存在 provider／model 为 typesafe/jev-latest、purpose find 的 model_usage 记录（会话 1 共 24 条、会话 2 共 8 条），属 omp 内部辅助调用，存在、具体内容不可核；修复轮三次 ping 与会话 3 的 jsonl 中无此类记录（编排方实测）。是否存在未落盘的内部辅助调用不可核。文件名仅经目录列表取得，本轮未读取 jsonl 内容。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-27T13:56:03+08:00 | planned | in-progress | 编排方整理；主会话开始 strict 性能修复 | 分支匹配，入口干净；HEAD 为 5eec9977f90f3c171bd9c7b4a5587ffc3aa3696f；父路径无 symlink，task 尚不存在，ignore 无命中。 |
| 2026-10-27T15:08:46+08:00 | in-progress | checking | 编排方整理；主会话完成 B／C／D 与验证，进入检查 | 会话 3 唯一 writer；2b3／2c3 独立串行补跑，七组 2424 项无重叠且覆盖全部 scope，skip 63、fail 2 均属基线；ruff exit 0，定向 96 tests、skip 2、exit 0；独立复核尚未执行，不声明发布完成。 |
| 2026-10-27T15:48:13+08:00 | checking | in-progress | CI run 40468076141 runtime-e2e-windows 导出 404，开始修复 | 分支匹配，入口干净；HEAD aee0418c4accfa7efb65d450c032f3a13e807f76；先 Linux 注入复现，再修改身份比较；仅本会话写入。 |
| 2026-10-27T16:00:35+08:00 | in-progress | checking | Windows e2e 404 本地复现、身份同源修复与验证完成，进入检查 | 修前 get／ExportStore.create 均 SnapshotNotFound，修后回归及真实 CSV smoke 通过；定向 97 tests、skip 2、exit 0，ruff exit 0；根包装 80 tests、skip 1、fail 1 为已知 tzdata 基线。Windows 原生与独立复核未执行，不声明发布完成；临时复现脚本已删除，raw／中文汇总保留。 |
| 2026-10-27T17:09:33+08:00 | checking | done | 编排方整理；写入者：主会话，Reviewy CLEAN 且 Lord 2026-10-27 16:41 群内下令写 done；PR #190 | Reviewy 对 34bea44dff7ad66ed89ac2c966015d55501b61d7 内容 CLEAN（2026-10-27，16:41 Lord 下令前，分钟不可考）；CI run 40474074238 13/13 全绿；Lord 合并前 --match-head-commit |

## Windows e2e 404 修复

### 证据与根因

- CI run 40468076141 attempt 1，基准 SHA `aee0418c4accfa7efb65d450c032f3a13e807f76`；只读证据 `/tmp/pr2-win/evidence.md`。Windows Server 2025／Python 3.12.10，POST `/api/v1/exports` 期望 202、实际 404 `{"detail":"not found"}`。serve stderr 与 runtime_home_logs 为空；日志中无异常类型，真实异常不可核。main 同一 e2e 为绿来自问题记录，本轮未联网复核。
- 读代码推断，未实际运行：修前 `report_snapshot.py:707,712,724,727,754,761` 从 lstat 建五字段身份，再与 fstat 比较；`disk_quota.py:39-40` 身份含 dev／ino／size／mtime_ns／ctime_ns。`serve.py:627-641` → `ExportStore.create:340` → `SnapshotStore.pin:805` → `get:956` → `_get:964` → `_read`，内部 ValueError 等被包装为 SnapshotNotFound，导出路由转换为 404。此处行号对应修前版本；本轮真实执行到 ExportStore，不冒充注入后的 HTTP 实测。
- Linux 修前注入实证：只令 fstat 身份的 ctime_ns 比真实值大 1,000,000,000；真实创建快照后的首次 get 与 ExportStore.create 都抛 SnapshotNotFound。异常跟踪捕获两次 `ValueError("snapshot file was replaced")`，dev／ino／size／mtime 均相同。支持 Reviewy 的混源身份比较机制；没有把这条 Linux 证据等同于 CI 的真实内部异常。
- 读代码推断，未实际运行：CPython 3.12 Windows 的 stat／lstat ctime 可能表示创建时间、fstat ctime 可能表示 ChangeTime，是本次模拟的语义前提；本机 Linux Python 3.13.5，无法实测 Windows。所查本机源码／文档路径没有可引用的 CPython 3.12 Windows 实现，不冒称源码已独立证实。
- 本轮沿用 strict；未完整调用 grill-with-docs，原因是范围、验收与保留行为明确。仅修改 report_snapshot.py、既有 persistence 测试与本 task；disk_quota.py 不需修改。临时产物限定 `/tmp/pr2-winfix-*`，不沿用早期会话的临时前缀；不改 CI、serve、契约或 schema。

### 修复与保证边界

- `_read` 先 lstat 保留普通文件、非 symlink、单链接和所有权检查；以现有 NOFOLLOW／NONBLOCK 标志打开，在 fd 上再次检查普通文件、单链接及所有权，以 dev／ino 核实打开对象与路径对象一致。fd 保持打开直至解析、校验及缓存发布结束；发布前再 lstat 核对路径 dev／ino，并 fstat 复核身份，防止读取或校验期间替换／改写。
- 缓存命中键、读前身份、读后复核及发布前复核全部采用同一已打开 fd 的 `os.fstat` 五字段身份。缓存命中也先打开并核实路径对象，不再用 lstat ctime 去比较 fstat ctime；代价是命中多一次打开／关闭，仍跳过 JSON 解析与校验。保留既有异常映射、共享锁、deepcopy 隔离和强制清扫校验，不引入备用缓存或平台特判。
- 读代码推断，未实际运行：在 Windows fstat ctime 为 ChangeTime 且改写使其变化的前提下，同 size、mtime 被恢复的原地改写仍会失效缓存并重新验 checksum；新增注入回归实际验证了此条件分支。若某平台 fstat ctime 实为创建时间且其余身份字段不变，该类改写检测不可保证；不宣称已验证 Windows 时间语义，也不宣称五字段身份能检测所有外部并发写入。
- Legacy Change Safety Review=characterized：生产编辑前已有 red 与真实导出失败；DDIA Data Design Review=confirmed：磁盘事实源、缓存同源、共享锁、失败失效、无迁移／回填；Refactoring Review=proceed（normal）：仅调整检查顺序及 fd 生命周期。Python LSP references 返回无 language server，改用源码核对启动恢复、sweep、get 三处 `_read` 调用。
- Code Readability Review／ponytail-review：主会话自核；没有新增依赖、平台分支或抽象，显式 dev／ino 比较与 fd 生命周期可直接核对；无独立重构。自核不代替独立复核。lessons-record 已评估：同源身份原则记录于本节，独立 lesson 文件超出写入范围，未写入且不宣称已保存。

### 修前／修后回归与验证

命令统一设置 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. TMPDIR=/tmp/pr2-winfix-tmp`；每个子进程限时 510 秒，原生命令执行，rtk=skipped-for-report。下表 stem 均位于 `/tmp/`，各有保留 stdout／stderr／exit／完整命令的 `.json` 与同 stem 中文 `.md`。环境为 Linux Python 3.13.5，Evidence Source=developer-local、Source Revision=dirty、Evidence Publication=local-only；基准 SHA 为入口 HEAD，不代表新提交或 CI 通过。

| 轮次 | 命令 | exit | 原生结果／墙钟 | 证据 stem |
|---|---|---|---|---|
| 回归 red | `python3 -B -m unittest test_snapshot_persistence.SnapshotPersistenceTests.test_different_path_and_fd_ctime_preserves_cache_and_rejects_rewrite` | 1 | 1 test，0.021s，errors 1；首次 get 抛 SnapshotNotFound；墙钟 0.214s | `pr2-winfix-regression-red` |
| 库路径 red | `python3 -B /tmp/pr2-winfix-repro.py` | 1 | get 首次读取及 ExportStore.create 均 SnapshotNotFound；墙钟 0.152s | `pr2-winfix-repro-red` |
| 异常定位 | `python3 -B -c` 加只读 trace 探针，完整参数见 raw | 1 | 两次 ValueError，只有 ctime 不一致；墙钟 0.242s | `pr2-winfix-identity-probe` |
| 回归 green | 同回归 red 命令 | 0 | 1 test，0.029s；墙钟 0.161s | `pr2-winfix-regression-green` |
| 库路径 green | `python3 -B /tmp/pr2-winfix-repro.py` | 0 | get 行数据一致，真实 CSV ready 并下载 42,199 bytes；墙钟 0.213s | `pr2-winfix-repro-green3` |
| 七模块定向 | `python3 -B -m unittest test_report_snapshot test_snapshot_persistence test_disk_quota test_serve test_exports_http test_export_store test_export_render` | 0 | 97 tests，110.695s，skip 2；墙钟 110.897s | `pr2-winfix-targeted` |
| 根包装 | `python3 -B -m unittest tests.test_sbtd_runtime_r1_stats_api` | 1 | 80 tests，4.481s，fail 1、skip 1；墙钟 4.631s | `pr2-winfix-wrappers` |
| 最终 lint | `ruff check --no-cache sbtd-runtime/report_snapshot.py sbtd-runtime/tests/test_snapshot_persistence.py` | 0 | All checks passed；墙钟 0.012s | `pr2-winfix-lint-final` |

- 新回归仅注入 fd ctime，其他 stat 字段来自真实 fstat；两次 get 内容一致且 json.load 恰一次，证明缓存命中。随后真实改写 checksum、保持 size 并恢复 mtime，推进模拟 ChangeTime；第三次 get 重新解析并拒读。修前同一测试在首次 get 失败，修后通过。
- 既有六个 B／C／D 新增测试均在定向范围内继续通过；`test_statistics_snapshot_quota_refusal_and_reuse` 覆盖 400／507，导出请求校验 400 也继续通过。根包装唯一失败为 `test_iana_queries_and_dst_work_without_system_timezone_data`，原始原因 `No module named 'tzdata'`，与已知基线一致；未安装依赖或重跑 main，不宣称全绿。
- 修后 smoke 首轮与第二轮 exit 1 分别是临时脚本误将 `generating` 写为 `running`、误断言 CSV 含 `dataset`；证据 `pr2-winfix-repro-green`（0.200s）／`pr2-winfix-repro-green2`（0.209s）保留。按真实状态与 CSV 表头／snapshot_id 修正脚本后第三轮通过，产品代码未因这两项失败变更。初次 lint 同样 exit 0，证据 `pr2-winfix-lint`。

### 覆盖缺口与 Windows 覆盖方案（仅方案）

- 读代码推断，未实际运行：原 96 项 Linux 定向测试没有注入不同来源 ctime；POSIX 上相同文件的 lstat／fstat ctime 通常一致，因而没有暴露混源比较。修前探针在本机也观察到除注入偏移外身份相同；这不是 Windows 证据。
- 读代码推断，未实际运行：`tests/run_ci.py:15-40,51-79` 的 Windows 选择集为升级模块、显式 WINDOWS_CASES、SessionRootResolution、安装器及 workflow/probe 模块，未包含 `test_snapshot_persistence`、`test_serve` 或 stats_api 根包装。`.github/workflows/validation.yml:199-238,296-321` 中 Windows shards 调用该选择集；该工作流 Windows 作业只有 runtime-e2e-windows 通过 `sbtd-runtime/tests/runtime_e2e.py` 进入真实运行时导出路径，使用 Python 3.12.10。
- 方案：后续把快照持久化及 serve／导出边界测试或对应根包装加入 Windows 选择集，并安装既有声明的运行时依赖；加入本轮异源 ctime 回归，同时保留 Windows 原生创建→首次 get→CSV 导出 smoke。先检查既有“恢复 mtime 后 ctime 必变”测试中的 path.stat 断言是否适合 Windows，按真实 fd ChangeTime 保证明确平台限制；不以 Linux 注入测试代替 Windows 原生验证。本轮未修改 CI 或执行该方案。
- Release Readiness Review=blocked（发布层面）：本地修复与定向验证已完成，但 Windows 原生运行和独立复核未执行，根包装仍有已知 tzdata 基线失败。共享配额／并发／取消机制未改；没有迁移，恢复边界是代码回退，未执行 Git 写操作。保持 checking、completed_at=null，不声明部署、发布或 Windows CI 已绿。
- project-validation：BDD=skipped（恢复既有读取语义，持久回归在现有 unittest，无契约或 .feature 修改）；Cross-repo context=not-needed；API Contract=verified（既有错误映射与定向 HTTP 测试）；Mock Strategy=Lord 2026-10-27 15:44 群内下令补 identity 取值注入回归测试，编排方整理（stat 身份注入，业务路径真实）；E2E Mode=backend-only，浏览器／移动工具不适用。Final Test Report／Run Summary MD=generated，Targeted Rerun=passed，Final Full Rerun=failed（根包装基线）；所有新报告为本地 dirty 证据，独立复核与发布由 Lord 后续安排。

### 范围外订正（Lord 可否决）

- 决定原文「用户 2026-10-27 群内确认（范围 B＋C＋D），Lord 记录」→「用户 2026-10-27 群内确认（范围 B＋C＋D；分钟不可考），Lord 记录」。
- 模型表第 6 行原文「未知（落盘时本轮尚未结束），待后续回填」→「30／53」；依据编排方统计 assistant 30、toolCall 53（read 18、edit 8、bash 8、todo 8、eval 7、wait 2、glob 1、grep 1）。对应回填说明原文「会话 3 尚未结束，计数不预估」→「会话 3 计数按编排方统计回填，本轮未读取 jsonl 内容」。
- 回填说明原文「model_usage 均为 0」→「旧目录六轮 jsonl 中 model_usage 记录数均为 0（实测）；是否存在未落盘的内部辅助调用不可核」。编排方实测本修复会话 1 有 24 条 model_usage（jev-latest，purpose find，内部辅助检索），证明该格式会落盘；不能因此推断所有内部辅助调用都已落盘。
- 并发说明原文末句「代码与测试未在并发期间修改」→「代码与测试未在并发期间修改。会话 2 检测到 task.md 并发写入后停止写入，未追加 checking」。
- 编排方实测：修复提交 `git diff --stat aee0418..34bea44` 为 3 files，+174／−43；整个 PR `git diff --stat 5eec997..34bea44` 为 5 files，+552／−52。修复会话 1 结束时汇报的 +145／−41 是会话 2 修改 task.md 之前的工作树中间态统计，不是最终值；若 PR 描述或群内报告引用 +145／−41 即为笔误，以上述实测为准。PR 描述暂未更正，等用户同意。

## Lord 15:46 范围补充

### load_dataset 行为变化与契约

- 读代码推断，未实际运行：PR #190 的 C 线程池改造将 `load_dataset` 移入 `statistics_response`，其调用现在受 `statistics_query` 的 try 保护（`serve.py:529-560`）；不是本修复会话新增的代码变化。若加载阶段抛出 `QueryScopeError`／`DiskQuotaExceeded`，此前未被该 handler 捕获、会返回 500，现在分别映射为 400／507。`contracts/openapi.yaml:305-331` 的 POST `/api/v1/statistics/query` 已声明 400／507，契约一致，无需修改。
- 可达性判断（读代码推断，未实际运行）：`load_dataset` 只读打开 EventStore、replay、close 并组装任务；打开失败的 StoreError 转为 warning。当前调用链不做 QueryScope 校验或 DiskQuota.admit，未发现自然抛出上述两类异常的路径，正常实现中判断不可达；这是条件性异常边界变化，不是已复现的线上响应变化，也不把既有 query 的 400／507 测试当作加载阶段证明。

### 遗留项（不修）

Lord 2026-10-27 15:46 群内决定不修，编排方整理。

- N1：Linux ctime 粒度较粗，同一 tick 内同 size、mtime 恢复的改写可能保持五字段身份不变，被缓存接受；Reviewy 的窄窗口观察，本轮未复测。
- N2：仅记录上述 load_dataset 条件性 500→400／507 行为变化；契约已声明，正常加载路径判断不可达，不改代码。
- N3：取消等待时信号量可能释放而工作线程继续运行，4 槽限制的是等待中的协程，不是仍在运行的线程；anyio 默认 limiter 40 仍生效，不把 4 槽解释为取消后的线程硬上限。本轮未实际运行取消场景。
- N4：缓存命中时 get 基于内存对象；公开 get 虽有 deepcopy，但 create_or_reuse 返回的内存对象若被库调用方修改，可能影响之后缓存命中的读取；当前 stats_query 只读该对象（`stats_query.py:188-192`）。读代码推断，未实际运行库调用方修改场景。

### PR 描述补充（文件已生成，未提交）

- 用户 2026-10-27 群内确认允许修改 PR 描述一次（16:07 前，具体分钟不可考），Lord 记录。本会话只更新本 task，并从只读备份 `/tmp/pr2-mine/body-before.md` 生成完整新描述 `/tmp/pr2-winfix-body-after.md`；未联网、未运行 gh、未实际修改 PR #190。原描述未涉及的段落逐字保留。沿用 strict；未完整调用 grill-with-docs，范围与验收明确。已有状态为 checking，不追加事件，completed_at 保持 null。
- 可直接粘贴的补充文本如下；完整新描述另含新增回归名、修复轮验证与用量表。

Windows 404 的混源身份比较问题已在修复会话 1 改为同一已打开 fd 的 fstat 身份：缓存键与读前／读后及发布前复核同源，路径 lstat 身份对照只比 st_dev／st_ino，安全检查保留。Windows 上同 size、mtime 恢复的原地改写仅在 fd ctime 为 ChangeTime 且改写使其变化时会失效缓存；五字段不变时不可保证检测，不能写成已解决。Windows 原生行为为读代码推断，未实际运行，真实验证看 runtime-e2e-windows。PR #190 的 C 改造还使 load_dataset 的条件性 QueryScopeError／DiskQuotaExceeded 从 500 映射为 400／507，契约已声明；当前只读加载链判断不可达，未实际运行该异常场景。遗留 N1 同 tick 改写可能命中缓存、N2 仅记录该行为变化、N3 取消后线程可能继续运行（4 槽限等待协程，anyio 默认 limiter 40 仍生效）、N4 create_or_reuse 对象被库调用方修改可能影响缓存命中读取（get 有 deepcopy，当前 stats_query 只读），Lord 2026-10-27 15:46 群内决定不修，编排方整理。范围外订正：群内确认补分钟不可考、旧会话 3 回填 30／53、旧目录六轮 jsonl 中 model_usage 记录数为 0（实测）并保留未落盘内部辅助调用不可核、补会话 2 冲突后停写且未追加 checking。Windows 覆盖仅为方案：补快照持久化及 serve／导出测试选择集、异源 ctime 回归与原生创建→get→CSV smoke，核实 path.stat 断言及 fd ChangeTime 限制；未改 CI，未执行方案。
