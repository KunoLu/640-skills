---
schema_version: 1
id: v2.1.0-rc.2-contract-bucket-ceiling
workflow_mode: strict
mode_source: user
mode_note: 用户明确选择 strict；分支由编排方创建，本轮在绑定工作树实施 C 节范围与 D 节两个新测试，严格 TDD；仅写授权白名单，不启动子代理或 advisor，omp 本身不提交、不推送、不联网、不安装依赖；依赖由编排方经 Lord 批准执行 `npm ci --ignore-scripts` 安装；提交、推送与 PR 由编排方执行者完成。
status: "done"
branch: feat/v2.1.0-rc.2-contract-bucket-ceiling
created_at: '2026-10-27T17:50:13+08:00'
updated_at: '2026-10-27T20:59:40+08:00'
completed_at: '2026-10-27T20:59:40+08:00'
---

# 契约 PR：方案 2——统计／快照查询结束时间按时间桶向上取整

## 来源与归属

- Lord 2026-10-27 16:35 群内裁定：范围仅含下列五项。五项原始范围见 C 节；其后关于生成文件、注释与验收的处理也在 C 节列明，不将后续补充倒写成该分钟的原话。
- 编排方整理：Lord 要求开分支前先把 task.md 草案发群给 Reviewy；本次实施指令确认 Reviewy 已批「草案可开分支」。分支已由编排方创建，当前进入实施阶段；不将草案许可写成实现复核通过。
- 用户 2026-10-27 群内确认（固定查询桶 300 秒、UTC epoch 对齐、All 终点也取整），Lord 记录
  注：分钟不可考。
- Lord 2026-10-27 群内裁定：测试②的 Node→Python 串接先在临时拷贝实测，且既有前端 CI 须具备所需环境与依赖，否则删除串接、仅留前端证据，不新增 CI 依赖或第三个测试；无 Reviewy CLEAN 证据，删除两个领域／数据设计审阅小节及其结论；时区偏移的 15 分钟整数倍说法仅列未完整验证的整理；第二轮模型统计按已核实资料记载，第三轮用量仅指向编排方报告。
  注：分钟不可考。
- 编排方整理：Lord 裁定生成的 static 纳入本 PR，长期查询桶 spec 本 PR 不做，OpenAPI 不改；验收写目标而非快照数量硬上限；归属必须使用单一来源格式。
- Reviewy 2026-10-27 群内审阅意见
  注：分钟不可考。
  本轮处理范围与产物、展示／导出影响、字面断言保留、哈希测试证据及已知限制。逐条阻塞／非阻塞等级不可考，不自行补造等级，也不将本轮自核写成 Reviewy 复核通过。
- 草案整理者：编排方整理。当前绑定分支为 `feat/v2.1.0-rc.2-contract-bucket-ceiling`；reflog 实测创建于 `2026-10-27 19:33:43 +0800`，基于 `c126609d0c0cff3303cf293707284698cebecdc1`。不调用 TaskStore，不写索引、active 或 handoff，不声称自动恢复。
- 未完整调用 grill-with-docs：需求及修改边界明确，固定桶宽、UTC 对齐和 All 规则均已确认，本轮直接实施，不重复澄清。
- 草案阶段入口记录：`git -C /workspace/640-contract-bucket status --short` 输出为空；`rev-parse --show-toplevel HEAD origin/main` 返回项目根与两个相同的 `c126609d0c0cff3303cf293707284698cebecdc1`；`symbolic-ref -q --short HEAD` 无输出、退出码 1，与当时分离头一致。当时工作树只读，不代表实施工作树状态。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-27T19:36:20+08:00 | planned | in-progress | 编排方已创建绑定分支，按用户授权进入 strict 实施 | date -Iseconds 实际输出；git reflog show --date=iso feat/v2.1.0-rc.2-contract-bucket-ceiling 记录 2026-10-27 19:33:43 +0800 从 c126609d0c0cff3303cf293707284698cebecdc1 创建 |
| 2026-10-27T20:59:30+08:00 | in-progress | checking | 编排方整理：PR #191 开启后进入审阅与 CI 检查阶段 | 在 done 提交中补记：PR #191 以 head 0722083f2a94a1f5cc6d3dd06ec1b21505052dec 开启；Reviewy 审阅与 CI 随之开始；其后 head 更新为 9914050e2350b79b880a1ccd45c1bb4d498e0606（Lord、Reviewy 归属：日期 2026-10-27，注：分钟不可考。） |
| 2026-10-27T20:59:40+08:00 | checking | done | 编排方整理：Lord 指示提交 done commit；Reviewy CLEAN；CI 全绿（Lord、Reviewy 归属：日期 2026-10-27，注：分钟不可考。） | 在 done 提交中补记：Reviewy CLEAN 绑定完整 SHA 9914050e2350b79b880a1ccd45c1bb4d498e0606；CI run 40503407766 attempt 1 在该 head 上 13/13 作业按名称全绿：dashboard-artifacts、linux-full、linux-shards (1)、linux-shards (2)、linux-shards (3)、macos-bash-installer、runtime-e2e-macos、runtime-e2e-windows、windows-powershell-installer、windows-shards (1)、windows-shards (2)、windows-shards (3)、windows-shards (4)；整体完成 success 于 20:41（UTC+8）；CLEAN 与 CI 仅适用于 9914050e2350b79b880a1ccd45c1bb4d498e0606，不适用于本 done 提交 |

草案阶段无事件；以上保留实施开始事件，并在 done 提交中补记 checking／done 转换，完成依据见 checking／done 事件；未合并、未发布。

## A. 固定查询桶与 PRD 定稿措辞

### 规则与具体时刻

来源：用户 2026-10-27 群内确认（固定查询桶 300 秒、UTC epoch 对齐、All 终点也取整），Lord 记录
注：分钟不可考。

- 固定查询桶为 **300 秒（300,000 ms）**，以 UTC epoch 为原点，与图表趋势桶独立，不随预置时长改变。
- 以 `now` 表示当前 epoch 毫秒数：`endMs = Math.ceil(now / 300_000) * 300_000`。前端的 Date 参数先取 `now.getTime()`。必须向上取整（ceil），不是 floor，保证 `to ≥ now`。
- 非 All 预置：`to = endMs`，`from = endMs − 预置时长`；1h／24h／7d／30d／90d 仍为 1／24／168／720／2160 个实际小时，不改为本地自然日运算。
- All：起点仍为 `1970-01-01T00:00:00.000Z`，终点使用同一向上取整规则。自定义范围不取整，保持精确，仅沿用既有 ISO 归一及有效性校验。
- 恰在边界的 now 不前进；过边界 1 ms 才前进下一桶。查询区间保持 `[from,to)`，发生时间恰等于 to 的事件仍排除。

以下为规则演算，不是产品运行结果；日期统一为 2026-10-15，24h 起点为前一天。

| now（UTC） | to（UTC） | 24h 的 from（UTC） | 意义 |
|---|---|---|---|
| `2026-10-15T16:00:10.000Z` | `2026-10-15T16:05:00.000Z` | `2026-10-14T16:05:00.000Z` | 非边界向上取整 |
| `2026-10-15T16:03:00.000Z` | `2026-10-15T16:05:00.000Z` | `2026-10-14T16:05:00.000Z` | 同桶得到完全相同范围 |
| `2026-10-15T16:05:00.000Z` | `2026-10-15T16:05:00.000Z` | `2026-10-14T16:05:00.000Z` | 边界幂等，不前进 |
| `2026-10-15T16:05:00.001Z` | `2026-10-15T16:10:00.000Z` | `2026-10-14T16:10:00.000Z` | 边界后 1 ms 推进 |

### 仓库依据与代价

以下源码结论均为读代码推断，未实际运行；行号本轮在工作树重新核对。

- `docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md:695` 已有「1h 使用 5 分钟桶」；`sbtd-runtime/stats_query.py:218-228` 的 `_default_bucket_seconds` 在跨度 ≤1h 时返回 300 秒（具体分支为 `:220-221`）。两处原本描述趋势桶，不是已经实现的查询上界规则，不能混同。
- `stats_query.py:235-279` 从实际 from 开始连续切趋势桶，尾桶裁至 to，不负责全局查询终点取整。`task_granularity`（`:99-101`）仍是任务统计粒度，不是查询桶。
- 时区偏移为 15 分钟整数倍的说法：**编排方整理，未对完整时区数据库验证**。不涵盖历史偏移（历史 IANA 秒级偏移不在这一概括内）。不据此断言 UTC 5 分钟边界必然也是当地 5 分钟边界，也不以此作为任何事实性结论的前提。算法直接按 UTC epoch 毫秒取整，独立于这一说法；不进行本地 DST 算术。
- 已知代价：所有预置（含 All）的终点最多晚于当前 5 分钟；窗口最旧的最多 5 分钟数据被丢掉；水位显示最多滞后 5 分钟。严格数学差值为 `[0,300_000)` ms，整边界差值为零。水位这一量级指正常持续轮询、桶内复用原快照的显示影响，不是页面暂停、网络失败或自定义固定范围下的全局时效保证。
- 例如 1h 在 `16:00:10Z` 查询得到 `[15:05:00Z,16:05:00Z)`；相对精确滚动窗口 `[15:00:10Z,16:00:10Z)`，左侧少了 4 分 50 秒，右侧多了同样长度。不能只固定 to 而让 from 随 now 滑动，否则完整 scope 与哈希仍会变化。

### PRD :686

文件：`docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md`。本轮核对旧文仍在第 686 行。

- 旧文：
  > 4. `1h/24h/7d/30d/90d` 为以快照 anchor 为终点的滚动窗口；自定义日期支持精确时间，并清楚显示起止时刻。
- 新文定稿：
  > 4. `1h/24h/7d/30d/90d` 的预置终点为查询时当前时间按固定 300 秒查询桶（UTC epoch 对齐）向上取整后的边界，起点为终点减去预置时长；各预置分别为 1/24/168/720/2160 个实际小时。恰在边界时终点不前进，过边界 1 ms 才前进下一桶。`All` 起点仍为 epoch，终点同样取整；自定义范围不取整，保持精确时间，并清楚显示实际起止时刻。查询区间仍为 `[from,to)`。

### PRD :1077

本轮核对旧文仍在第 1077 行。

- 旧文：
  > - 默认 `24h`；记忆上次 preset，但每次新查询重新解析相对窗口 anchor。
- 新文定稿：
  > - 默认 `24h`；记忆上次 preset，每次新查询重新解析当前时间，并按 §8.4 固定 300 秒查询桶（UTC epoch 对齐）向上取整得到预置终点，All 同规则，自定义不取整。同桶内预置范围保持不变，过边界后范围推进；查询范围相同不等于数据视图相同。新增入库事件改变数据指纹时生成新快照，旧快照保持不变；复用仍要求查询哈希和数据指纹一致、快照未过期且有效。

PRD 其他位置只作为关联依据；若需修改，必须列为「需先在群里问」，不擅自纳入本 PR。

## B. 目标验收与已知限制

编排方整理：Lord 裁定验收只写目标，不写快照数量硬上限，不承诺性能收益。

### 验收目标

1. 没有新数据时，同一个桶内的 query_hash 稳定。前提是预置、时区、metrics、filters 等其余条件不变；哈希稳定不等于无条件复用，仍受数据指纹、有效期与文件有效性约束。query_hash 仅由规范化后的 scope 决定（from/to 按原字符串参与），见 report_snapshot.py:885-886；复用另需 :895-916 的数据指纹与有效期。
2. 终点向上取整，保证 `to ≥ now`，对应 PRD:1311 的「已采集事件到可见 ≤30 秒」。本轮核对实际原文为「正常采集与服务开启下 ≤ 30 秒；必须同时显示实际延迟」。这避免 floor 将当前桶已采集事件挡在上界外，不是端到端延迟已经得到验证；`[from,to)` 的边界排除仍保留。
3. 没有新数据时每天快照 **288 次**可作为目标，出处「不可考」；不是硬上限，不保证实际数量或降幅，不能以此替代两个行为测试。
4. 桶内真实新增事件仍得到新快照，旧快照与已固定的导出视图不变；All 同样取整、自定义精确、describeRange 格式不变，整页仍使用同一 snapshot_id。

### 已知限制（PR 描述原样保留）

(1) 指纹覆盖全库事件（`report_snapshot.py:895-905`），事件持续到达时，单页固定 scope 下快照上界仍是 2880/天，任何桶宽都一样；只有没有新数据时才会降低，具体降幅「不可考」；

(2) 30 秒轮询仍照常发请求，不保证每轮得到不同 snapshot_id，也不承诺快照数量或性能收益；

(3) 后端不拒绝取整后晚于 `as_of` 的终点（`stats_query.py:57-80` normalize_scope 只查可解析、from<to、时区；`report_snapshot.py:940-942` 对 as_of 与 effective_to 无约束），取整后的终点可以晚于快照 `as_of`；

(4) 复用快照时，响应 `meta.as_of`（`stats_query.py:171` 取当前时间）可能与 `snapshot.as_of` 不一致，取整后复用更频繁，这个不一致更常见；

(5) 只有前端预置范围取整，所有 API 调用自动取整不在本 PR 范围，OpenAPI 不改。

上述行号均已核对，文件位于 `sbtd-runtime/`；行为结论为读代码推断，未实际运行。第 (1) 项按单页仅有固定 30 秒轮询计算，不涵盖额外手动请求或多页；第 (3) 项的「只查」限定为时间范围，函数还校验 schema、filters、metrics 等字段，不是完全没有其他校验。

补充证据：`report_snapshot.py:885-886` 对规范化 scope 求 query_hash，`:906-916` 仅在未过期、哈希与指纹相同且能读取有效快照时复用；`:934-958` 新建时记录创建时刻与原范围。`stats_query.py:183-193` 只将 snapshot_id、expires_at、watermark_seq、query_hash 附到响应，不将响应 `meta.as_of` 改成旧快照时间。取整不减少后端每轮查询，也不改变缓存、配额或过期机制。

PR 描述一次写成，已知限制按 B 节原样写入。链式校验已在 scratch 副本两步验证通过，未纳入测试。本任务不新增 PR 描述全文。

## C. 实施范围、关联影响与历史说明

### 五项原始范围及后续补充

Lord 2026-10-27 16:35 群内裁定：范围仅含下列五项。

1. PRD `docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md:686` 的预置窗口措辞。
2. 同一 PRD `:1077` 的相对 anchor 措辞。
3. `sbtd-runtime/dashboard/src/timeRange.ts` 及 `timeRange.test.ts`；核对 `snapshotPin.test.ts` 是否需要改。
4. `ai/tasks/v2.1.0-rc.2-r2.0b-filters-detail/task.md:80` 的轮询说明，保留原句并追加更正说明。
5. 两个新测试：「桶内出现新事件仍会生成新快照」「取整后查询哈希稳定」。

编排方整理：Lord 裁定 `sbtd-runtime/dashboard/static/` 重建纳入本 PR，按生成文件交付；`artifact-budget.json` 视构建结果一并更新；长期查询桶 spec 本 PR 不做；OpenAPI 不改。

- static 只能在 `sbtd-runtime/dashboard` 用仓库现有 `npm run build` 生成，不得手改。PR 列明构建命令与实际 Node 版本；CI 固定 Node 22.20.0（`.github/workflows/validation.yml:116-119`）。
- Reviewy 重新构建复核字节一致；该项是后续计划，不是本轮独立复核结果。CI 的 dashboard-artifacts 在 `validation.yml:148-156` 依次构建、检查预算、要求 `git status --porcelain` 为空。
- 构建配置核对及第 2 轮实测：`package.json:9` 为 `tsc --noEmit && vite build`；`vite.config.ts:11-12` 输出并清空 static。`artifact-budget.json:4-13` 保存预算与基线；`check_artifacts.py:17-50` 只读体积并检查预算，构建命令没有自动重写该 JSON 的步骤。第 2 轮两次构建通过且 static 字节一致，详见 H 节；本轮禁止修改 artifact-budget.json，未运行预算检查，不把预算基线误称为自动生成物，不擅自放宽预算或修改 ADR／CI。
- `App.tsx:167-169` 的轮询注释同步改为「每轮重解析，预置按固定查询桶取整，可能复用相同 snapshot_id，完整加载后整份替换」，只同步注释，不改轮询或导出逻辑。
- `snapshotPin.test.ts:19-52` 核对后无需改；`:27-41` 是页面发生两次不同快照替换时仍固定旧 ID 的场景，不要求每次实际轮询都换 ID。保留原断言，不为重复 ID 新增第三个测试。
- 未新增长期 spec，如需要另提。

不做：不改 OpenAPI、ADR、存储 schema、serve.py、stats_query.py、report_snapshot.py、快照缓存／过期／配额／导出／采集机制，不将所有 API 请求自动取整。PRD 除 :686/:1077 外若发现必需改动，仅记录「需先在群里问」。

草案阶段仅修订任务文件，另在当时工作树 HEAD 的 git archive 临时拷贝中修改实验文件并运行 D 节诊断；这些历史实验不作为本轮实施证据。实施阶段仅写用户授权白名单，临时数据仅放在当前工作树 `.tmp-omp/` 并在结束前删除；不写任务索引、active、handoff、身份或配置，不创建分支、不提交、不发布、不联网、不安装依赖。编排方已执行 `npm ci --ignore-scripts`（退出码 0、锁文件未变）；第 2 轮两次构建与 static 字节一致证据见 H 节，预算文件不改。

### 现状与最小修改对照

以下均为读代码推断，未实际运行。

| 已核对位置 | 当前行为 | 计划修改／保留 |
|---|---|---|
| `timeRange.ts:6-8,59-74,106-115` | 注释把不同 now 与不同窗口关联；预置 to=now，非 All 的 from=now−duration | 局部固定 300,000 ms 查询桶；一次计算 endMs，from/to 一起对齐；同步注释 |
| `timeRange.ts:20-36` | 实际小时长度；All 从 epoch 起 | 时长与 All 起点保留 |
| `timeRange.ts:80-104,118-134` | 自定义有效性及 ISO 归一；buildScope 组合真实范围、metrics 与非空 filters | 不新增请求字段，不改自定义或维度语义 |
| `timeRange.test.ts:19-50,81-93` | 固定 NOW 在整点，预置宽度／to=NOW／相隔一小时窗口不同 | 修改已有用例，使用非边界 now 与明确的取整预期；测试②补足完整证据 |
| `timeRange.test.ts:52-79,95-125` | 自定义拒绝无效输入、记忆选择 | 保留行为；在既有自定义用例和测试②检查非边界上界不取整 |
| `timeRange.test.ts:127-143` | 完整范围摘要与标签的字面断言 | **timeRange.test.ts:127-143 保留**，不删、不重写成新文案；describeRange 格式不变 |

`timeRange.ts:175-184` 已核对：describeRange 只是格式化实际 from/to/timezone，selectionLabel 的既有格式也不变。固定 NOW 为整边界，原字面断言在新规则下仍成立；第一轮建议删除这些断言有误，本版撤回该建议。

### 展示、导出与水位影响

来源：Reviewy 2026-10-27 群内审阅意见
注：分钟不可考。
以下已逐条核对，均为读代码推断，未实际运行；路径简写的前端文件位于 `sbtd-runtime/dashboard/src/`，Python 文件位于 `sbtd-runtime/`。

| 位置 | 影响 |
|---|---|
| `filters.ts:89-96`（值在 :96） | 范围摘要读取快照 effective_from／effective_to，会显示取整后的 to |
| `App.tsx:227` | 导出标签读取快照实际范围，会显示取整后的 to |
| `export_render.py:835-838,892-894`（关键 :837/:893） | 报告范围与导出元数据 range_to 读取 effective_to |
| `csv_export.py:160-161,212-213,240-241` | CSV 元数据、指标、数据行的 range_to 使用取整后的快照终点 |
| `App.tsx:504-507`（值在 :506） | 水位显示 snapshot.as_of；同桶复用时保留旧创建时刻，正常轮询下最多滞后 5 分钟这一量级，不应改成取整后的 to 或伪装成当前创建时间 |
| `App.tsx:167-172` | 注释需同步；定时器仍按 30 秒重查，频率不变 |
| `App.tsx:220-228`；`snapshotPin.test.ts:27-41` | 导出入口仍使用已显示的 snapshot_id，pin 继续固定原快照；只改变预置生成的范围值，不改变入口和 pin 语义 |
| `timeRange.ts:80-115` | 自定义路径保持精确，不受预置取整影响 |

### R2.0b task.md:80 更正说明

文件：`ai/tasks/v2.1.0-rc.2-r2.0b-filters-detail/task.md`。第 80 行本轮核对未漂移，保留原句：

>   - **D12 轮询**：无用户操作时网络面板出现第二轮完整 roundtrip（30s poll 自动整份替换为新 snapshot_id）；替换期间视图不清空（pageModel 语义单测覆盖「正在更新」保留旧视图）。

追加更正说明文本：

> 编排方整理：第 80 行记录的是 R2.0b 当时一次浏览器实测，原文保留。预置范围现按固定 300 秒查询桶（UTC epoch 对齐）向上取整，All 同规则，自定义不取整。30 秒轮询仍执行整份查询与视图替换，但不保证每轮得到不同 snapshot_id。同一查询哈希与数据指纹、未过期且有效的快照可复用；同桶新增事件改变数据指纹时生成新快照，已固定的旧快照不变。本更正的运行验证以本契约任务实施后的实际记录为准，不沿用 R2.0b 的旧结果证明新行为。

实施时追加真实记录时间和证据，不预填运行或合并结论；R2.0b 的 done（`:7`）、原 completed_at（`:12`）及历史完成／合并事件（`:109-110`）不改。本轮按上述文本追加更正，运行证据见实施阶段记录。

### 关联契约保持

- 读代码推断，未实际运行：PRD `:683,685,691` 的 IANA 展示、半开区间与 DST 规则不变；`:699` 与 AC-08 `:1437` 的迟到事件进入新快照、旧快照不变仍须成立。
- 读代码推断，未实际运行：PRD `:817-818` 的精确查询条件、as_of 与 effective_to 不能混同；`:1078` 的全页单快照与加载时保留旧视图不变；`:1086` 的 30 秒检查并不要求每轮 ID 改变。
- 读代码推断，未实际运行：`sbtd-runtime/contracts/openapi.yaml:1136-1164` 的 QueryScope 只有具体 from/to/timezone 等，没有 preset 或查询桶字段；本 PR 不改 OpenAPI。
- 读代码推断，未实际运行：`sbtd-runtime/spec/r1.3-stats-api-scenarios.md:83-108` 的共享、事件到达换 ID、过期与 cursor 场景保留。`:85` 仅提相同接收水位，实际还比较全量指纹；不借本 PR 改写这一长期 spec。

## D. 两个新测试与验证计划

本节保留获准的两个新测试规格与草案实验历史；当前已正式新增且仅新增这两个测试，前端既有用例的断言更新不另算新测试。场景正文用中文，沿用已有 Markdown 场景的 Given／When／Then 结构词；不新建 .feature，不新增或修改长期 spec。测试②所列临时拷贝实测仍为历史，当前分支的 RED／GREEN 与真实实现运行结果见 H 节，不以局部诊断冒充完整链路或 CI，不以 mock 回声代替。

### 测试①：桶内出现新事件仍会生成新快照

- 落点：`sbtd-runtime/tests/test_report_snapshot.py` 的 `SnapshotTests`，拟名 `test_new_event_inside_query_bucket_mints_new_snapshot`。
- Given：沿用该文件 `:95-150` 的真实 EventStore＋base_event 夹具，独立临时 runtime；scope 固定 24h，from=`2026-10-14T16:05:00.000Z`、to=`2026-10-15T16:05:00.000Z`、UTC，其余条件固定。先入库 occurred_at／recorded_at=`2026-10-15T16:00:05Z` 的事件，第一次查询 now=`16:00:10Z`，TTL 覆盖整个测试。
- When：同一数据在 `16:00:30Z` 再查询，确认有效复用；随后 append 唯一 source_event_id 的新事件，occurred_at=`16:02:00Z`、recorded_at=`16:02:30Z`，在 `16:03:00Z` 用同一 scope 查询。新增事件位于首次 now 与取整后 to 之间，不能只测很早的历史数据。
- Then：前两次 snapshot_id 相同；新增事件后 query_hash 相同、dataset_fingerprint 不同、snapshot_id 不同；新快照包含新增 event_id，旧快照再次读取仍不含该事件，旧 rows／digest／as_of／expires_at 与保存值完全相同。历史受控时刻的读取显式传 now，避免测试运行当天使固定历史快照过期。
- 在同一测试内以独立夹具子场景覆盖迟到：occurred_at=`15:59:00Z`，recorded_at=`16:02:30Z`，仍在查询范围内；查询后新快照包含该事件、旧快照不变。沿用真实 producer 的 payload ingest_seq=0 路径，不靠人为抬高最大序号绕过全量指纹。
- `test_report_snapshot.py:75-79` 已核对：只比较同一数据与 scope 两次创建得到相同 ID；`:95-150` 已有零 payload 序号新增事件换 ID。新测试增加固定查询桶、桶内新事件可见与旧快照不变证据，不重复仅同对象复用。

### 测试②：取整后查询哈希稳定

证据仅依赖 `sbtd-runtime/dashboard/src/timeRange.test.ts` 的一个新测试「取整后查询哈希稳定」。删除计划中的 Node→Python 串接检查，不启动 Python 子进程，不新增 CI 依赖或步骤，不在 Python 增加另一条哈希测试；连同测试①，总共仍恰好两个新测试。该名称沿用裁定，前端直接验证的是构成查询条件的完整 scope 稳定，不冒称它直接计算了后端 query_hash。

- Given：固定 24h 预置、同一 metrics／filters 和运行时区；时刻使用 A 节四行。既有 `timeRange.test.ts:19-43,81-93` 同步更新为明确的绝对结果与宽度断言。
- When：直接调用真实 `resolvePresetRange`／`buildScope`，不在测试里重写生产取整公式。
- Then（前端主要证据）：`16:00:10Z` 与 `16:03:00Z` 输出完整 scope 深相等；to 为 `16:05:00Z`、from 为前一天 `16:05:00Z`；`16:05:00Z` 边界幂等；`16:05:00.001Z` 推进到 `16:10:00Z`，from 同步推进，窗口宽度不变。All 两时刻都从 epoch 到 `16:05:00Z`；自定义 from=`2026-10-14T16:00:07.123Z`、to=`2026-10-15T16:03:12.345Z` 在不同 now 下仍原样精确，不取整。
- Lord 2026-10-27 群内裁定维持删除（链式校验已在临时拷贝两步验证通过，未纳入测试；Node 在测试里直接调用 Python 这一步未试，保留会多一个 CI 依赖或一轮验证）
  注：分钟不可考。
- 前端实际命令（临时拷贝的 `sbtd-runtime/dashboard`）：`TMPDIR=/workspace/scratch-contract-chain/.tmp node --test --test-name-pattern='取整后查询哈希稳定' src/timeRange.test.ts`，退出码 0，1 项通过。仅在拷贝内按 A 节修改 `timeRange.ts`，追加同名实验用例调用真实 `resolvePresetRange`／`buildScope`；四个时刻的完整 scope 写入 `.tmp/scopes.json`。前三次为 from=`2026-10-14T16:05:00.000Z`、to=`2026-10-15T16:05:00.000Z`，第四次为 from=`2026-10-14T16:10:00.000Z`、to=`2026-10-15T16:10:00.000Z`；运行时区为 Asia/Shanghai，All 与自定义断言也通过。
- Python 实际命令（临时拷贝根）：`TMPDIR=/workspace/scratch-contract-chain/.tmp PYTHONDONTWRITEBYTECODE=1 python3 -B .tmp/check_snapshot.py`，退出码 0。脚本直接读取上述 JSON 与现有 golden 数据，以同一 `SnapshotStore`、3600 秒 TTL 调用真实 `stats_query.query(..., store=store)`；前三次 query_hash 和 snapshot_id 均相同，第四次两者均不同，输出 `same_bucket_equal: true`、`cross_bucket_different: true`。没有手抄范围或复制哈希实现。TemporaryDirectory 限于 `.tmp` 并自动清理；文件传值的两步诊断不是 Node 测试内启动 Python 的兼容性验证，脚本也不是第三个拟新增测试。
- 前端范围回归实际命令（同一 dashboard 目录）：`TMPDIR=/workspace/scratch-contract-chain/.tmp node --test src/timeRange.test.ts`，退出码 0，9 项通过，包含原摘要字面断言及一个实验用例。实际版本探测 `node --version && python3 -B --version` 退出码 0，分别为 v22.20.0、Python 3.13.5；不是 CI Python 版本下的运行证据。
- CI 逐行核对：读代码推断，未实际运行。`validation.yml:99-109` 确定同一 dashboard-artifacts 作业；`:111-114` 设置 Python 3.12.10，`:116-119` 设置 Node 22.20.0；`:121-125` 安装 Onboard 依赖，`:127-134` 在前端测试前再安装 Onboard 与 serve 依赖；`:136-138` 安装锁定 npm 依赖，`:140-142` 执行 `npm test`，其展开为 `node --test src/*.test.ts`（`package.json:10`），覆盖 timeRange 测试。`sbtd-workflow-onboard/requirements.txt:1-5` 声明 jsonschema、PyYAML 等，`sbtd-runtime/requirements-serve.txt:4-8` 包含 jsonschema 与 tzdata；既有作业具备所需环境，无需新增步骤。CI 配置条件成立，但 Node 在测试里直接调用 Python 这一步未试，按上述裁定维持删除串接；不把配置核对写成 CI 已通过。

### 保留回归

- **timeRange.test.ts:127-143 保留**。describeRange 格式不变，保留原字面断言；自定义错误、时区、选择记忆回归保留。
- `snapshotPin.test.ts` 核对后无需改，按原样回归。
- `test_stats_query.py:146-154,161-191,251-275` 的 golden 数值、UTC／Tokyo 等价范围、半开边界与完整趋势桶保留，不改 golden 来掩盖窗口误改。
- `test_report_snapshot.py:75-95,163-177,184-228` 的复用、新水位、共享 ID、过期、cursor、manifest、不可变回归保留；`test_snapshot_persistence.py:29-57` 的重启复用与原 expires_at 不续期保留。
- `test_golden_contracts.py:126-127,177-205` 的事件 schema 与既有指标断言不直接依赖前端 now，保持不变。

### 验证计划表

以下保留草案验证计划；本分支实际执行、退出码及未执行原因以 H 节为准。正式报告须保留失败原始输出及同 stem 中文汇总，记录真实 SHA／分支／工作树状态／工具版本；本轮仅提供本地未提交工作树的定向回归与烟测记录，不声称完成正式 CI／发布报告 Gate，解析任务文件不能替代产品验证。

| 目的 | 命令／工作目录 | 预期证据与写入边界 |
|---|---|---|
| 新测试①定向 | 根目录：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_report_snapshot.SnapshotTests.test_new_event_inside_query_bucket_mints_new_snapshot -v` | 固定 to=16:05:00Z，桶内新增事件换 ID，旧快照不变；写临时事件库和快照 |
| 新测试②定向 | `sbtd-runtime/dashboard`：`node --test --test-name-pattern='取整后查询哈希稳定' src/timeRange.test.ts` | 仅前端完整 scope／300 秒边界、All 与自定义；无 Python 串接，不新增 CI 依赖或步骤；当前新用例已随两文件回归经历 RED／GREEN，未单独执行此筛选命令；临时拷贝两步诊断保留为历史 |
| 前端范围与 pin 回归 | 同目录：`node --test src/timeRange.test.ts src/snapshotPin.test.ts` | All、自定义、原字面断言、导出 pin 语义保持；不是新增第三个测试 |
| 前端全套 | 同目录：`npm test`，实际为 `node --test src/*.test.ts`（package.json:10） | 保留现有全部前端回归；npm 可能写日志／缓存 |
| 快照／统计／契约回归 | 根目录：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_report_snapshot test_snapshot_persistence test_stats_query test_golden_contracts -v` | 不修改原黄金值、边界与持久化预期；写测试夹具 |
| 根 CI 发现入口 | 根目录：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_sbtd_runtime_r1_stats_api tests.test_sbtd_runtime_r1_contracts -v` | stats 包装 :17-23、contracts 包装 :15-18 已核对；与直接模块覆盖重叠，不累加独立测试数 |
| static 构建 | `sbtd-runtime/dashboard`：`npm run build` | 只用现有命令生成 static，禁止手改；PR 记录命令与 Node 22.20.0／实际版本 |
| 预算与基线 | 根目录：`PYTHONDONTWRITEBYTECODE=1 python3 -B sbtd-runtime/dashboard/check_artifacts.py` | 检查实际产物体积；artifact-budget.json 视构建结果同步，不放宽预算；单独预算通过不证明字节一致 |
| Reviewy 字节一致复核 | 从包含源码、生成 static 与必要预算基线更新的干净提交出发，在 dashboard 重跑 `npm run build`；根目录执行 `test -z "$(git status --porcelain)"` | 与 dashboard-artifacts 的检查相同；非空即不能声称字节一致，不用清理命令抹掉差异 |
| Python 新测试静态检查 | 根目录：`ruff check --no-cache sbtd-runtime/tests/test_report_snapshot.py` | 仅后续实施执行；不在本轮安装工具或修复环境 |
| Linux 全套三片 | 根目录逐片：`PYTHONDONTWRITEBYTECODE=1 python3 -B tests/run_ci.py --platform linux --shard N --shards 3 --output <获准报告目录>`，N=1、2、3 | `tests/run_ci.py:330-339,356-357` 会创建目录并写 inventory／JSON／Markdown；本轮不执行，不以局部回归代替全套计划 |
| 实际浏览器烟测 | 后续运行真实服务与浏览器，观察请求、数据页、范围摘要、水位、导出标签和导出文件 | 默认 24h、1h、All、自定义、桶内两次轮询、跨桶推进、新事件换 ID、全页同快照；检查 B 节 as_of 差异，不伪造 MCP／端到端结果 |

### 已知环境基线

- 编排方整理：既有 `test_sbtd_probe_links.MaterializeAuthorizationTests` 链接竞争每轮 1–3 项不定；`test_iana_queries_and_dst_work_without_system_timezone_data` 曾因缺 tzdata 失败（时间不可考）。本轮未重跑，不作当前环境实测结论。
- 读代码推断，未实际运行：历史任务 `ai/tasks/v2.1.0-rc.2-sweep-offload-validate-cache/task.md:93-95,111-112` 记录链接竞态与 `No module named 'tzdata'`。本轮只核对记录，不将其他新失败自动归入旧基线。
- CI Python 3.12.10、Node 22.20.0 来自 `validation.yml:114,119` 的配置；本轮临时拷贝实测 Node v22.20.0、Python 3.13.5，详见测试②；不将局部诊断冒充 CI 或完整产品验证。

## E. 风险、归属规范与 Gate 计划

### 剩余风险与证据边界

1. **未来上界与左端损失——读代码推断，未实际运行。** 固定窗口整体前移，可能包含已入库但 occurred_at 在 now 与 to 之间的记录；PRD:1079 禁止未来全空范围，不等于禁止部分未来窗口。本 PR 不加 as_of 截断，已明确 A 节代价。
2. **哈希不等于快照身份——读代码推断，未实际运行。** 相同 scope 还需全量指纹一致、未过期且文件有效；过滤范围外事件、任务或来源水位变化也能换 ID。不同 ISO 字符串、timezone、metrics 次序或 filters 变化不属于同键保证。
3. **显示与实际延迟——读代码推断，未实际运行。** UI 读取 snapshot.as_of，查询响应 meta.as_of 取当前时间；取整使这一既有差异更常见，不伪造水位，不承诺请求减少或性能改善。
4. **时区与 DST——读代码推断，未实际运行。** 固定实际小时不等于自然日；算法按 UTC 毫秒取整，与本地展示分离，不依赖时区偏移是否整除桶宽。时区偏移为 15 分钟整数倍的说法仅为「编排方整理，未对完整时区数据库验证」，不能据此推广当前或历史时区的当地边界。
5. **生成文件与长期文档。** 编排方整理：Lord 裁定 static 已纳入本 PR，长期查询桶 spec 不做，OpenAPI 不改。这不再是开放范围冲突；第 2 轮已取得本地两次构建字节一致证据，产物预算已通过（check_artifacts OK），仅真实界面证据仍待取得。
6. **串接环境。** 串接检查已从测试②与验证计划中删除，不新增 CI 依赖或第三个测试；测试②证据仅依赖前端 timeRange 测试。草案阶段文件传值的前端与真实 Python 快照诊断均退出 0，链式校验已在临时拷贝两步验证通过，未纳入测试；Node 在测试里直接调用 Python 这一步未试，保留会多一个 CI 依赖或一轮验证，按裁定维持删除。既有 CI 环境配置核对不代表 CI 已运行；源码本地测试及第 2 轮构建字节一致证据见 H 节，性能与数量降幅仍无本轮运行证据。

### 归属规范

有确切分钟的 Lord 发言采用「Lord 2026-10-27 16:35 群内裁定」格式；没有确切分钟的采用「编排方整理：Lord 裁定……」或普通编排方整理，不拼接模糊日期冒充精确来源。桶规则来源始终使用「用户 2026-10-27 群内确认（固定查询桶 300 秒、UTC epoch 对齐、All 终点也取整），Lord 记录」。
注：分钟不可考。
Reviewy 意见始终使用「Reviewy 2026-10-27 群内审阅意见」。
注：分钟不可考。
不借审阅者姓名推断已执行复核或已同意发布。

### strict Gate 计划

| Gate | 实施阶段触发 | 本轮状态 |
|---|---|---|
| DDD／DDIA | 查询桶语义、跨请求视图身份 | DDD 不触发：无完整 grill 或领域歧义；DDIA 实施自核，未经 Reviewy 审阅，见 H 节，不是 Reviewy CLEAN 或独立审阅 |
| legacy-change-safety／TDD | 既有预置行为修改前 | characterized；先前端 5 fail／7 pass，再最小改动后 12 pass；后端保留行为首次即通过 |
| refactoring-pass／ponytail | strict 生产编辑前 | proceed／normal，无需重构；局部时间计算，无新抽象、依赖或服务端取整 |
| gherkin-bdd | 用户可见范围与快照行为 | traceable：D 节两条获准场景对应两个新测试，不扩写长期 spec |
| project-validation／真实界面烟测 | 实施修改后 | 第 1 轮前端 12 项、后端 13 项及 ruff 通过；真实范围函数 smoke-only；编排方 npm ci --ignore-scripts 退出码 0、锁文件未变；第 2 轮两次 npm run build（--configLoader native，含 tsc）退出码均为 0，static 字节一致；CI 与浏览器未运行 |
| 可读性／独立审阅 | 实现后及提交审阅前 | 手写改动自核完成；Reviewy 2026-10-27 群内审阅意见在 `9914050e2350b79b880a1ccd45c1bb4d498e0606` 上 CLEAN，并独立构建两次结果一致（注：分钟不可考。） |
| release-readiness | 测试后、运行前端交付前 | blocked（第 2 轮自核时记录）：static 已重建，构建内类型检查及本地两次字节一致通过；产物预算已通过；当时 CI／真实界面证据未取得，不声明发布就绪。此后 CI run 40503407766 已全绿；真实界面（浏览器）证据仍未取得 |

## F. 模型记录

第一轮与第二轮数据出处：编排方整理，据会话 jsonl 核对。本轮按这一来源记载，未自行读取或统计任何会话 jsonl；第二轮两个会话文件均位于第二轮日志目录 `contract-bucket-draft-v2` 下。

| 轮次／用途 | 时间 | 模型 | thinking 档位 | assistant 消息／toolCall | 来源及补充 | 会话文件 |
|---|---|---|---|---|---|---|
| 第一轮 ping | 17:49:28 | openai-codex/gpt-6-astra | 未知／不可核 | 1 条 assistant 消息／0 toolCall | 编排方整理，据会话 jsonl 核对 | `2026-10-27T09-49-29-815Z_01a17cc3-cf57-7315-a4cf-9b5a7fb486be.jsonl` |
| 第一轮草案主会话 | 17:49:34 起约 12 分钟 | openai-codex/gpt-6-astra | 未知／不可核 | 19 条 assistant 消息／65 次 toolCall | 编排方整理，据会话 jsonl 核对；read 33、grep 10、bash 7、edit 7、todo 5、glob 2、write 1；model_usage 记录 0 | `2026-10-27T09-49-34-726Z_01a17cc3-e286-70f4-91a8-cc415fe4c41a.jsonl` |
| 第二轮 ping | 未知／不可核 | openai-codex/gpt-6-astra | 未知／不可核 | 1 条 assistant 消息／0 toolCall | 编排方整理，据会话 jsonl 核对；模型出处沿用命令行参数 | `ping/2026-10-27T10-34-42-670Z_01a17ced-346e-709f-9728-c4e2bd8e7922.jsonl` |
| 第二轮草案主会话 | 未知／不可核 | openai-codex/gpt-6-astra | 未知／不可核 | 18 条 assistant 消息／68 次 toolCall | 编排方整理，据会话 jsonl 核对；read 42、bash 9、todo 9、grep 4、glob 2、edit 2；model_usage 记录 0 | `session/2026-10-27T10-34-51-927Z_01a17ced-5897-7348-9a0b-e26bf6509a8c.jsonl` |
| 第三轮（v3）草案主会话 | 未知／不可核 | openai-codex/gpt-6-astra | 未知／不可核 | 本轮（v3）用量见编排方报告，草案正文不含 | 模型出处：命令行参数；本轮不读取自己的会话 jsonl | 未知／不可核 |
| 实施第 1 轮（ping＋主会话） | ping 19:34:58、主会话 19:35:07 起（会话 jsonl 记录的 UTC 时间换算为 +08:00） | openai-codex/gpt-6-astra | high | ping 1 条 assistant 消息／0 toolCall；主会话 22 条 assistant 消息／67 次 toolCall | 编排方整理，据会话 jsonl 核对；read 31、bash 16、todo 8、edit 5、grep 4、find 1、write 1、eval 1；model_usage 存在（24 条，均为 purpose=find，辅助模型 typesafe/jev-latest） | `contract-bucket-impl/ping/2026-10-27T11-34-58-057Z_01a17d24-5f09-76df-832f-5c4303e30748.jsonl`；`contract-bucket-impl/session/2026-10-27T11-35-07-027Z_01a17d24-8213-721e-8b95-2c339473181f.jsonl` |
| 实施第 2 轮（ping＋主会话） | ping 19:51:46、主会话 19:51:53 起（会话 jsonl 记录的 UTC 时间换算为 +08:00） | openai-codex/gpt-6-astra | high | ping 1 条 assistant 消息／0 toolCall；主会话 17 条 assistant 消息／41 次 toolCall | 编排方整理，据会话 jsonl 核对；read 13、eval 8、todo 6、grep 5、bash 4、edit 3、find 1、glob 1；model_usage 存在（4 条，均为 purpose=find，辅助模型 typesafe/jev-latest） | `contract-bucket-impl-r2/ping/2026-10-27T11-51-46-904Z_01a17d33-c3d8-76a3-99a4-e84330b10ce3.jsonl`；`contract-bucket-impl-r2/session/2026-10-27T11-51-53-296Z_01a17d33-dcd0-7316-b5f3-8924f01a20dd.jsonl` |
| 实施第 3 轮（ping＋主会话） | ping 20:20:00、主会话 20:20:12 起（会话 jsonl 记录的 UTC 时间换算为 +08:00） | openai-codex/gpt-6-astra | high | ping 1 条 assistant 消息／0 toolCall；主会话 9 条 assistant 消息／26 次 toolCall | 编排方整理，据会话 jsonl 核对；todo 10、bash 7、read 5、grep 3、edit 1；model_usage 无记录（0） | `contract-bucket-impl-r3/ping/2026-10-27T12-20-00-698Z_01a17d4d-9c3a-7754-ae38-4dd3edef5cb0.jsonl`；`contract-bucket-impl-r3/session/2026-10-27T12-20-12-193Z_01a17d4d-c921-7249-8264-85daf3704610.jsonl` |
| 实施第 4 轮（ping＋主会话，已弃用未提交） | ping 20:47:09、主会话 20:47:18 起（会话 jsonl 记录的 UTC 12:47:09／12:47:18 换算为 +08:00） | openai-codex/gpt-6-astra | high | ping 1 条 assistant 消息／0 toolCall；主会话 8 条 assistant 消息／24 次 toolCall | 编排方整理，据会话 jsonl 核对；read 10、bash 5、todo 4、grep 3、find 1、edit 1；model_usage 存在（22 条，均为 purpose=find，辅助模型 typesafe/jev-latest）；该次尝试因违反状态机（直接 in-progress → done）被弃用，其编辑在第 5 轮修正后沿用，未原样提交 | `contract-bucket-impl-r4/ping/2026-10-27T12-47-09-083Z_01a17d66-751b-70d2-8a4f-13136c8a0dc2.jsonl`；`contract-bucket-impl-r4/session/2026-10-27T12-47-18-564Z_01a17d66-9a24-738a-9368-8766dc54d7cb.jsonl` |

model_usage 记录 0 不等于没有模型调用或 token 消耗。第二轮统计与文件名已按编排方核对资料记载；未给出的时间及 thinking 档位均为未知／不可核，不从文件名或文件大小推算。草案第三轮（v3）用量只见编排方报告，不在草案正文自算。实施第 1、2、4 轮存在 model_usage 记录，均为 find 工具的辅助模型调用，不是子代理；实施第 3 轮无记录。第 3 轮无记录，待 Reviewy 对会话日志复核。实施第 4 轮已记入上表；本轮（实施第 5 轮）omp 运行的用量不在本文件自计，由编排方在群内／PR 另行报告。

## G. 草案阶段（v4）证据、格式自检与交付边界

本节保留草案阶段历史；其中「本轮」指 v4 文字修订，不指当前分支实施。实施结果另见 H 节。

- 本轮为 v4 草案的定点文字修订，仅写本文件；未写临时拷贝、工作树或其他文件，未运行产品测试或构建。未完整调用 grill-with-docs，原因是修改项与边界明确。没有启动子代理／task 工具／advisor，没有联网、安装、提交或发布。
- 本轮入口 `git -C /workspace/640-contract-bucket status --short` 输出为空；`rev-parse --show-toplevel HEAD` 返回项目根与指定 SHA，`symbolic-ref -q HEAD` 无输出，与分离头一致。除 `report_snapshot.py:885-886` 本轮重新核对外，以下源码核对、临时拷贝命令及结果均保留自上一轮记录，本轮未重跑，不能作为本轮新取得的运行证据。
- 上一轮记录：只读核对工作树源码、契约、测试与构建配置；工作树未运行任何产品命令。源码基准为 `c126609d0c0cff3303cf293707284698cebecdc1`，分离头与 origin/main 一致。D 节所列临时拷贝诊断为上一轮实测，其余读代码所得行为结论均标作读代码推断，未实际运行。
- 上一轮临时拷贝实际命令：根目录执行 `mkdir -p /workspace/scratch-contract-chain/.tmp`（退出码 0）、`node --version && python3 -B --version`（退出码 0）；dashboard 目录执行 D 节带 TMPDIR 的定向与整份 `timeRange.test.ts` 命令（分别 1 项、9 项通过，退出码均为 0）；根目录执行 D 节带 TMPDIR／禁字节码前缀的 `.tmp/check_snapshot.py`（退出码 0，同桶相同、跨桶不同）。未运行 npm、构建、完整套件、CI 或浏览器，不以局部诊断替代正式验证。
  草案阶段 `test -d …` 一类目录存在性检查已随 B2' 删除，因为 Node→Python 串接已删除、临时拷贝诊断不再作为保留该串接的环境前置，故本历史命令列表省略这类检查。
- 上一轮临时拷贝写入清单：`sbtd-runtime/dashboard/src/timeRange.ts`、`sbtd-runtime/dashboard/src/timeRange.test.ts`、`.tmp/check_snapshot.py`、`.tmp/scopes.json`，以及 Python 检查在 `.tmp/contract-chain-*` 下创建后自动清理的快照数据。实验文件仅留于临时拷贝，不纳入草案的实施文件或新测试数量；本轮未写这些文件。
- 上一轮行号核对记录：第一轮已说明早先 `report_snapshot.py:863-889` 线索不完整，上一轮复核实际创建／复用函数仍为 `:874-962`，指纹仍在 `:895-905`；PRD :686/:695/:1077/:1311、stats_query :57-80/:171/:218-228、展示与导出各行均未漂移；CI 字节一致的具体检查在 `validation.yml:155-156`。预算文件不是构建自动生成物，已在 C 节明确；snapshotPin 测试不需修改。snapshotPin 引用结束行 52 沿用既有修订，本轮不声称重新核对了所有源码行号。
- `updated_at` 使用本轮 `date -Iseconds` 的实际输出；保持 planned、空状态事件表与 null 完成时间，不制造草案完成即实现完成的状态转换。
- 自检使用仓库真实 TaskDocument 解析器。`sbtd-workflow-onboard/scripts/sbtd_task_document.py:195-198` 调用 frontmatter／schema／时间校验；只调用 parse，不调用 TaskStore。命令如下，参数用草案路径占位避免在正文写入本机日志目录：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -c "import sys; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); import sbtd_task_document as s; p=sys.argv[1]; d=s.TaskDocument.parse(open(p,encoding='utf-8').read()); print(p, d.frontmatter['status'], d.legacy_events, len(d.events), d.frontmatter.get('completed_at'))" <草案路径>
```

- 自检实测：上述 TaskDocument 命令退出码 0，输出状态字段为 `planned False 0 None`；禁用措辞扫描存在一项要求冲突：指定哈希原句中的谓词也列入零命中清单，保留指定原句，其他禁用措辞零命中。两个领域／数据设计审阅小节在本轮修订前已不存在，strict Gate 的未执行状态保持不变。用户与 Reviewy 的来源各三处，均在紧接下一行注明分钟不可考；Lord 本轮改为日期式的裁定同样紧接该注。重复括注仅保留已知环境基线一处，拟新增测试仍恰好两项。
- 本轮哈希依据核对：`report_snapshot.py:885` 为 `scope = normalize_scope(raw_scope, catalog=catalog)`，`:886` 为 `query_hash = _digest(scope)`；已在验收目标第 1 条加入指定的 scope 哈希说明。
- 本轮修改限于 B1' 分钟归属、B2' 串接删除依据及冲突措辞、两处重复括注、哈希说明、E 节标题、F 节中性措辞、版本号、本节自检与实际更新时间；保留临时拷贝命令及通过证据。五项已知限制、300 秒规则、PRD 两处定稿、测试①、既有回归计划及空状态事件表保持不变。
- 退出前再次执行 `git -C /workspace/640-contract-bucket status --short`，末次实际输出在交付汇报中说明。Python 使用环境前缀与 `-B` 禁止字节码写入，不输出环境变量，不写额外报告。本轮验证仅为文档解析与文字自检，不声称产品测试、正式测试 Gate、CI 或完整链路通过。
- 两个领域／数据设计审阅小节已整节删除，strict Gate 如实标记未执行，不保留自核审阅结论。第二轮会话统计已取得并按 F 节记载；完整时区库验证、未提供的模型时间／thinking 档位与 Reviewy CLEAN 证据仍未取得。
- 本轮交付仅为这一份 v4 草案的文字修订；不是开分支、实现、独立审阅、CI、部署或发布完成。工作树没有修改或数据迁移；本轮恢复边界仅为本草案，不涉及上一轮临时拷贝文件或真实产品代码与数据。

## H. 实施阶段记录

- 第 1 轮根与分支只读核对通过；基准 SHA 为 `c126609d0c0cff3303cf293707284698cebecdc1`，当轮入口仅新任务目录未跟踪，其他文件无修改。Node `v22.20.0`、Python `3.13.5`。第 2 轮入口已有第 1 轮未提交修改，本轮保留；构建证据另列于本节末。
- schema 源为 `sbtd-workflow-onboard/templates/skills/sbtd-task/references/task-data.schema.json:12`，合法状态为 `in-progress`；首次 TaskDocument 解析退出码 0，原草案为 `planned False 0 None`。仅用解析器验证，不调用会写索引等文件的 TaskStore。
- Reviewy 四项文字修正：(a) 裁定条目补列表标记及两格缩进；(b) 待替换词在输入文件中仅 1 处，恰为要求原样保留的 PR 描述句，因此实际替换 0 处；其他位置已是「临时拷贝」；(c) 写入前核对 `report_snapshot.py:885-886,895-916` 与 `stats_query.py:112-115`，行号、规范化后哈希、from/to 原字符串和复用条件均吻合，无差异；(d) G 节历史命令列表仅追加一句省略目录检查的原因。
- 依赖与构建状态已更新：编排方执行 `npm ci --ignore-scripts`，报告退出码 0、「added 72 packages, and audited 73 packages」「found 0 vulnerabilities」，package.json／package-lock.json 未变。本轮未安装依赖；执行两次 `npm run build -- --configLoader native`，退出码均为 0，static 字节一致；artifact-budget.json 未改。安装结果归属编排方，不冒称本轮执行。
- 实施 Book Gate Plan：既有 D 节中文 Given／When／Then 为本任务获准场景，不新建长期 spec／.feature；前端 seam 为真实 resolvePresetRange／buildScope，后端为 EventStore＋SnapshotStore。先记录前端 RED，再最小改动及 GREEN；后端保留行为不伪造 RED。legacy 与 refactoring 在生产编辑前完成自核，project-validation 在修改后执行；发布就绪与独立审阅分别记录，不借用草案许可。无完整 grill 或未决领域术语，DDD 不触发；不恢复草案中已删除的审阅小节。
- 生产编辑前评审（第 1 轮实施自核，非独立审阅）：Legacy Change Safety Review=`characterized`，前端 RED 证明旧范围仍以精确 now 结束；自定义、选择记忆、摘要与 pin 在同轮通过，无需安全 seam。Refactoring Review=`proceed`／`normal`，无需重构，仅固定桶常量与一次 endMs 计算。DDIA 实施自核，未经 Reviewy 审阅：前端改变 scope 值、后端仍以 scope＋全量指纹＋TTL／有效性判复用；真实事件入库与不可变快照由测试①确认，不改数据所有权、schema 或迁移。LSP 实测未配置服务，调用点以源码检索核对：App.tsx:131 → buildScope → resolveRange → resolvePresetRange。
- TDD RED：dashboard 执行 `TMPDIR=../../.tmp-omp node --test src/timeRange.test.ts src/snapshotPin.test.ts`，退出码 1；12 项，7 pass／5 fail。失败为预置、All、跨桶、buildScope 和新增测试②，实际终点分别仍是 `16:00:10.000Z`／`16:03:00.000Z`，而非预期 `16:05:00.000Z`；不是导入或环境失败。原摘要字面断言通过。此处将第 1 轮命令的临时路径等价改写为相对路径，未重跑测试。
- 后端保留行为定向：根目录执行 `TMPDIR=.tmp-omp PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_report_snapshot.SnapshotTests.test_new_event_inside_query_bucket_mints_new_snapshot -v`，退出码 0，1 项通过，含独立迟到子场景；生产后端未修改，不声称该测试曾 RED。临时路径为第 1 轮实际路径的相对表示。
- TDD GREEN：同一 dashboard 回归命令退出码 0，12 pass／0 fail；原摘要测试块逐字保留，snapshotPin.test.ts 不改。根目录 `TMPDIR=.tmp-omp PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_report_snapshot -v` 退出码 0，13 项 OK。`ruff check --no-cache sbtd-runtime/tests/test_report_snapshot.py` 退出码 0，`All checks passed!`。临时路径为第 1 轮实际路径的相对表示。
- 本地运行烟测：dashboard 用 `node --input-type=module -e` 直接导入真实 buildScope／describeRange，打印 A 节四个时刻、All 与自定义；退出码 0。前三个时刻均输出 `[2026-10-14T16:05:00.000Z,2026-10-15T16:05:00.000Z)`，边界后 1 ms 为 `[2026-10-14T16:10:00.000Z,2026-10-15T16:10:00.000Z)`；All 起点 epoch；自定义毫秒原样保留。此为 smoke-only，不是浏览器、HTTP 或 Node→Python 串接验证，不新增第三个测试。
- 可读性与 ponytail-review 自核：生产改动仅固定常量、一次上界计算及原路径复用，无新抽象／依赖／后台改动；测试保留真实夹具和独立迟到子场景，无 mock、第三个测试或全局时区修改。R2.0b 第 80 行原句保留并追加更正及上述本轮结果，原状态与历史事件不变。
- 验证分类：BDD=`traceable`，本任务 D 节中文场景＋英文 Given／When／Then，两个新测试与之对应；Mock Strategy=`none`；Cross-repo context=`not-needed`，API Contract=`verified`（本地 normalize_scope／SnapshotStore 源码与测试，不声称 HTTP 契约全量验收）；rtk=`not-needed`，按编排方整理的原生命令运行。证据为 developer-local／dirty／local-only，不是 CI 或当前 PR 提交证明；原始运行输出保留在本次工具记录，未生成或宣称正式测试报告。
- TaskDocument 自检：G 节命令的路径参数分别为 `ai/tasks/v2.1.0-rc.2-contract-bucket-ceiling/task.md` 与 `ai/tasks/v2.1.0-rc.2-r2.0b-filters-detail/task.md`，各自退出码 0。新任务输出 `in-progress False 1 None`；R2.0b 输出 `done True 0 2026-10-20T03:14:10+08:00`，并提示「旧格式事件，不追溯」。该提示是保留的旧事件格式，不将其写成新格式事件校验通过。
- 跳过边界（更新至第 2 轮）：依赖由编排方安装，本轮未安装；已执行两次 npm run build（附 --configLoader native），构建内 tsc 及 static 字节一致均通过。编排方执行者在根目录运行 `python3 -B sbtd-runtime/dashboard/check_artifacts.py`，输出 `OK: 3 files, 267300 bytes (budget 524288)`，退出码 0；artifact-budget.json 未改；未跑前端全套、扩展 Python 套件、根 CI 发现入口、Linux 三片、浏览器／HTTP 全链路。第 1 轮定向回归与真实函数烟测保留为当轮证据，本轮未重跑，不以生成物替代真实界面验证。未联网，未启子代理／advisor，未做 git 写操作、提交、发布或全局配置修改。
- Release Readiness Review=`blocked`（发布层面，第 2 轮自核时记录）：第 1 轮源码行为验证通过，第 2 轮 static 重建、构建内类型检查与本地两次字节一致通过；预算已通过；当时 CI 及真实界面证据仍缺失，独立审阅待编排方安排。当时仅交付分支阶段授权修改，保留 in-progress 与 null 完成时间。此后 CI run 40503407766 已全绿，独立审阅结果见 done 事件；真实界面（浏览器）证据仍未取得，未合并、未发布。无 schema／数据迁移，回退边界是本次源码、文档和配套生成物，不需回滚既有事件库；未实际执行回退。固定窗口前移代价、30 秒轮询请求量与 meta.as_of／snapshot.as_of 的既有差异仍按 B 节说明，不声称数量或性能收益；未改监控／告警或运行手册，不新增服务、队列或背压机制。
- 临时数据均限定 `.tmp-omp/`；测试夹具已自动清理，实测为空后执行 `rmdir .tmp-omp` 退出码 0。末次记录时间取同次 `date -Iseconds` 输出 `2026-10-27T19:41:22+08:00`。仅任务文件承载本地结果摘要，不写索引、active、handoff、正式报告目录或长期 spec。

### 第 2 轮：构建证据与 task 文字修正

- 模式保持 strict；分支及基准与本节一致。未完整调用 grill-with-docs：本轮仅补构建证据及明确授权的文字修正，不改变需求或生产源码。`updated_at` 取实际 `date -Iseconds` 输出 `2026-10-27T19:53:48+08:00`；状态保持 `in-progress`、`completed_at: null`。
- dashboard 中执行 `node --version`，退出码 0，输出 `v22.20.0`。
- 默认 Vite 配置加载器会写 `node_modules/.vite-temp/`，超出本轮临时文件白名单。因此两次均执行 `TMPDIR=../../.tmp-omp npm_config_cache=../../.tmp-omp/npm-cache npm_config_offline=true npm_config_update_notifier=false npm run build -- --configLoader native`；原脚本展开为 `tsc --noEmit && vite build --configLoader native`。仅通过参数使用 Node 原生配置加载，未改 package.json、锁文件或 vite.config.ts；npm 缓存限定 `.tmp-omp/`，离线运行。这不是无参数构建或 CI 默认加载器的复核证据。
- 构建前及两次构建后，均在 dashboard 执行 `find static -type f -print0 | sort -z | xargs -0 sha256sum`，退出码均为 0；由调用器将原始 stdout 分别写入 `../../.tmp-omp/static.before.sha256`、`../../.tmp-omp/static.run1.sha256`、`../../.tmp-omp/static.run2.sha256`（等价于命令后加对应 `>` 重定向）。
- 第 1 次构建退出码 **0**；输出尾部：`static/index.html 0.46 kB │ gzip: 0.30 kB`、`static/assets/index-cSr3LuxA.css 7.70 kB │ gzip: 1.84 kB`、`static/assets/index-KzymcUqY.js 259.14 kB │ gzip: 82.15 kB`、`✓ built in 915ms`。Vite `v6.4.4`，41 modules transformed。
- 第 2 次构建退出码 **0**；相同三个文件及体积，输出结束为 `✓ built in 841ms`。根目录 `diff .tmp-omp/static.run1.sha256 .tmp-omp/static.run2.sha256` 退出码 **0**、输出为空，两个文件集合与逐文件 SHA-256 完全相同，static 字节一致。
- 根目录 `diff .tmp-omp/static.before.sha256 .tmp-omp/static.run1.sha256` 退出码 **1**（预期存在变化）：删除 `sbtd-runtime/dashboard/static/assets/index-I9-hua3C.js`，新增 `sbtd-runtime/dashboard/static/assets/index-KzymcUqY.js`，修改 `sbtd-runtime/dashboard/static/index.html`；`sbtd-runtime/dashboard/static/assets/index-cSr3LuxA.css` 字节不变。dashboard 的 `git status --short -- static` 对应输出 ` D static/assets/index-I9-hua3C.js`、` M static/index.html`、`?? static/assets/index-KzymcUqY.js`。
- 第三次及独立构建记录：
  - 编排方执行者第三次构建：在 `sbtd-runtime/dashboard` 执行 CI 同款无参数 `npm run build`，Node v22.20.0，退出码 0；构建前后 static 三个文件的 SHA-256 与前两次构建一致：`static/assets/index-KzymcUqY.js` 为 `d8b9897f984040f7cc95634dcb36c6ea5f74e2e8702c10cb502d788764ec7c10`，`static/assets/index-cSr3LuxA.css` 为 `a678f1d887c2a9838a6be0a1f0fd90869e9c0dc32a252a8a4e6165f29619087f`，`static/index.html` 为 `51611e457cade33850f502df56532e039ae3b2827e965ce11fc44ec6722917b6`；构建前后 `git status --porcelain` 输出完全相同（当时工作树含尚未提交的本任务修改，构建未产生任何新变化）。
  - Lord 2026-10-27 群内说明：
    注：分钟不可考。
    Lord 也独立执行 `npm run build` 两次，哈希一致，`git status` 为空。
  - Reviewy 2026-10-27 群内审阅意见：
    注：分钟不可考。
    Reviewy 也独立构建两次，结果相同（index-KzymcUqY.js 的 sha256 以 d8b9897f 开头，css 以 a678f1d8 开头，html 以 51611e45 开头）。
- 文字修正：更新 H 节、Gate 表与相关过时边界；新 task 两处过强 DDIA 审阅结论均改为「DDIA 实施自核，未经 Reviewy 审阅」。R2.0b 只修正第 1 轮追加记录；H 节及追加记录的当前工作树临时路径改为相对路径，保留真实 `+08:00` 时间戳与草案历史路径。
- 第 2 轮自检：按 G 节解析逻辑，以 `python3 -B -c` 分别解析两个 task，退出码均为 0；新任务输出 `in-progress False 1 None`，R2.0b 输出 `done True 0 2026-10-20T03:14:10+08:00`，仍提示「旧格式事件，不追溯」。不调用 TaskStore，不改旧任务 frontmatter／历史事件。全文不区分大小写复扫禁用审阅词零命中，过时缺依赖／未重建陈述及指定当前工作树绝对路径亦零命中。
- 写入范围自检：以本轮入口文件 SHA-256 为基线，变化仅上述 static 三个路径与两个 task；其余已跟踪／未忽略的未跟踪文件字节保持不变。R2.0b 仅第 82 行有变化，第 80 行逐字不动；两个任务中原有 `+08:00` 时间戳均保留。构建清单与 npm／Node 临时缓存已从本轮创建的 `.tmp-omp/` 删除，目录不存在；原始构建输出及比较结果保留在本轮工具记录，本节承载摘要，不留临时文件或另建正式报告。
