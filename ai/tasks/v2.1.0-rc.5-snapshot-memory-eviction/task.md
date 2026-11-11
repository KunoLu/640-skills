---
schema_version: 1
id: v2.1.0-rc.5-snapshot-memory-eviction
workflow_mode: strict
mode_source: user
mode_note: 用户 2026-11-11 15:10 群内确认（rc.5 全程用 strict），Lord 记录；用户 2026-11-11 群内确认（a甲 b同意），Lord 记录。注：分钟不可考。docs-only 范围由编排方整理
status: checking
branch: docs/v2.1.0-rc.5-adr0003-snapshot-memory-eviction
created_at: '2026-11-11T14:38:57+08:00'
updated_at: '2026-11-11T16:29:09+08:00'
completed_at: null
---

# 快照内存淘汰：ADR 0003 文档修订

## 目标与边界

- 编排方整理：docs-only，本 PR 只改 ADR 0003 的设计决策；配套更新本 task、生成式索引及中英文 CHANGELOG，不改任何代码或测试。
- 完整快照采用最多 8 条的 LRU；磁盘仍是事实源，被逐出的有效 ID 仍可读，分页、导出及生命周期不变。
- 范围冻结为五个文件：`docs/adr/0003-v2.1.0-rc.2-r2.0c-snapshot-persistence.md`、本 `task.md`、`ai/tasks/index.md`、`CHANGELOG.md`、`CHANGELOG.zh.md`。
- 本轮状态保持 `checking`，等待独立 review 与 CI；文档完成不代表实现、部署或发布完成。先合入文档 PR，再另开代码 PR。

## 决策来源

- 用户 2026-11-11 群内确认（a甲 b同意），Lord 记录。注：分钟不可考。
- 用户 2026-11-11 群内确认（a甲 b同意），Lord 记录。注：分钟不可考。编排方整理：b 同意对应完整快照最多 8 份、LRU 移出内存、磁盘文件不删、其他规则不变。具体方案、docs-only 范围、PR 顺序及本轮验证安排均由编排方整理。
- 仓库外只读 planned 草稿用于方案参考，不复制其本机路径。保留草稿创建时间和 planned→planned 事件；本记录采用本轮明确的 strict 模式与文档分支，不把草稿的 default 模式或旧分支当成当前绑定。

## 当前行为与源码依据

基准为 `80f14263e7d8bc6ae84f04ba94218e4857fc8b8f`；以下行号已按当前源码核对。CHANGELOG 行号为本轮新增版本节后的行号。草稿引用过 PR #147／#190，本轮未重新访问这两个 PR，不把历史阅读当作本轮验证。

| 行为 | 当前文件依据 |
|---|---|
| 已发布记录仍把 snapshot memory eviction 列为 Deferred；其他缓存局限独立保留 | `CHANGELOG.md:109-110`（本轮插入前为 103-104） |
| serve 创建共享 SnapshotStore，随后交给 ExportStore；构造器逐个校验合法快照文件并全部加入 `_snapshots`，再按启动流程清扫 | `sbtd-runtime/serve.py:482-488`；`sbtd-runtime/report_snapshot.py:640-685` |
| `_snapshots` 保存完整对象；`_validated` 保存文件身份；`_gone` 为进程内集合 | `sbtd-runtime/report_snapshot.py:663-667` |
| 新建先落盘再加入字典；没有条数或内存压力淘汰 | `sbtd-runtime/report_snapshot.py:906-917,960-962` |
| sweep 已删除已验证、过期且未 pin 的文件，并移除完整内存对象；不是完全不回收 | `sbtd-runtime/report_snapshot.py:825-854` |
| 默认 TTL 为 86400 秒；已知清扫 ID 或过期未 pin 的 ID 抛 SnapshotGone | `sbtd-runtime/report_snapshot.py:47,967-977` |
| 受控 ID／目录检查、普通文件／所有权／链接检查、fd 身份复核、版本／结构／checksum／ID 校验；身份命中返回缓存对象 | `sbtd-runtime/report_snapshot.py:691-770` |
| pin／release 共享锁计数；get 深拷贝完整快照，dataset_page 检查 cursor 所属 ID 并只深拷贝返回页 | `sbtd-runtime/report_snapshot.py:811-823,964-1007` |
| 复用只查完整内存字典的 query_hash／dataset_fingerprint，排除过期候选，再调用 get 核验 | `sbtd-runtime/report_snapshot.py:883-917` |
| 磁盘计量独立枚举普通文件，新建准入前先 sweep，再判断共享配额；共享 RLock 不等于内存容量管理 | `sbtd-runtime/disk_quota.py:66-87,118-165` |
| ADR 历史正文固定落盘格式、24h TTL、引用、删除边界及当时未新增内存淘汰的事实 | `docs/adr/0003-v2.1.0-rc.2-r2.0c-snapshot-persistence.md:7-64`；仅在原启动／无淘汰描述处加注指向 §6 |

## ADR §6 要点摘要

编排方整理：

1. 完整缓存最多 8 份，按最近成功访问排序并 LRU 逐出；只断开内存引用，绝不删磁盘，不释放磁盘配额。
2. 启动逐个打开、完整校验，只保留 ID、expires_at、query_hash、dataset_fingerprint 等轻量字段；不持有 dataset／rows／public_view，完整缓存启动为空。
3. 缓存未命中按受控 ID 路径读盘，沿用全部安全检查，成功才缓存；淘汰不是 404／410。
4. 24h 从原 created_at 起算，命中／逐出／重载不续期；分页、cursor、导出、404／410、pin、507 不变。pin 保护磁盘生命周期，不要求常驻内存。
5. sweep 已回收已验证、过期、未 pin 的快照；新增的是未过期快照条数上限。清扫改遍历轻量索引，不仅是 LRU。
6. 条数不是 RSS／字节上限；索引、_gone、临时对象和返回副本不计入 8 条，不承诺进程总内存恒定。
7. 仅隔离测试可通过内部参数覆盖容量；不提供环境变量／CLI／配置文件，serve 固定默认 8，公开配置另作决策。
8. _validated 随完整缓存逐出；索引查复用候选后读盘核验，不因淘汰新建 ID 或多占磁盘。
9. 沿用共享锁；读者已持有对象不清空，get／分页 deepcopy 隔离不变。8 条可能反复冷读；回退恢复全量驻留但不删快照。

## 后续实现方案（未实现）

以下沿用草稿并按当前源码核对，由编排方整理；本轮没有实现或运行淘汰场景。

### 有上限的缓存与独立索引

- 使用标准库 LRU，默认 8 条；最近成功创建／发布或读取的项移到最近使用端，超额移出最久未用的项。
- SnapshotStore 增加内部正整数容量参数供隔离测试；serve 固定默认值，不新增产品配置面。
- 独立轻量索引只保留复用／清扫必要字段，不建立第二份完整载荷缓存；_validated 与完整缓存项共同失效／逐出。
- 每次操作结束后完整缓存不超过容量；索引与 _gone 不受该条数上限约束。

### 启动、读取与写入

- 启动仍逐个完整校验，建立轻量索引后释放完整载荷；完整缓存为空，不新增磁盘 manifest，不迁移旧文件，也不承诺减少启动总读盘量。
- get／dataset_page／pin／复用冷读都走受控 ID 路径；目录／普通文件／所有权／链接、同一 fd 身份、版本／结构／checksum／ID 检查不减弱。
- 热读保留现有文件身份检查；文件变化重新校验，缺失或损坏时失效载荷与校验项，拒绝返回旧数据，不删除坏文件。
- 成功读取／发布才更新 LRU；新建仍先 temp、fsync、原子发布，成功后登记索引与缓存。失败不发布半个条目，不假报可复用。
- query_hash／dataset_fingerprint 从索引找未过期候选，再读盘核验；被逐出不迫使相同查询产生新 ID 或重复磁盘占用。

### TTL、引用与读取一致性

- 重启、缓存命中、逐出、重载不延长原 expires_at；过期 ID 不复用。原 ID 的 public_view、页、cursor、导出继续来自原持久快照，不用最新统计重建原 ID。
- 有效未过期冷快照可读；已知过期未 pin 返回 410，缺失／坏文件返回 404；不新增跨重启永久 tombstone。
- pin 只保护磁盘生命周期，完整载荷仍可逐出；多个引用、恢复引用先于清扫、最后 release 后正常 TTL 判断不变，前端固定 ID 不冒充后端 pin。
- 沿用共享 RLock，不拆锁；并发读者不能看到半发布项。已持有的对象不原地清空或改写，get／分页 deepcopy 不变，外部副本不计入缓存上限。

### 清扫与配额

- sweep 遍历轻量索引，先按 expires_at／pin 筛选，删除前强制完整校验并复核身份；冷清扫用临时对象，不污染 LRU。
- 删除成功同步清理索引、载荷、校验项并保留原 Gone 语义；失败保留候选供下次尝试。
- 未知／坏文件／链接不因内存压力被删；原磁盘计量与保留规则不变。未过期文件不能因淘汰而回删。
- 保留启动＋新建准入前清扫，不加定时器；共享配额、80% 预警、507 不变，内存逐出不能释放磁盘配额。

## 不做的范围

- 不改代码、测试、JSON 格式、checksum、HTTP schema、TTL、磁盘配额或导出保留策略；不迁移既有文件，不改发布版本 Deferred 历史条目。
- 不做流式 CSV、按需生成数据页、磁盘索引数据库、多进程缓存、全进程内存限制或全仓性能优化。
- 不顺带修复文件身份五字段完全不变时的缓存局限，不改 create_or_reuse 返回对象的既有所有权接口。
- 不运行安装、workflow sync、部署或发布；不修改 active／handoff／身份文件，不调用 task 工具或子代理，不 commit／push，不开 PR。

## 测试计划（实施时执行）

- 在现有 test_report_snapshot／test_snapshot_persistence 中，以容量 2 执行 A、B、访问 A、创建 C；B 被逐出，磁盘文件仍在且可再次读取。
- 冷读比较原 ID、digest、所有数据页、cursor；相同查询复用旧 ID 且不增文件；修改 get 返回副本不影响后续读取。
- 重启加载远超 8 份快照，所有有效 ID 可用、启动缓存为空，连续访问后完整缓存不超过 8 条。
- 冷／热读覆盖损坏、未知版本、删除、symlink、替换、fd 身份变化；沿用 Windows 异源 ctime 回归，Linux 注入不冒充 Windows 实测。
- 覆盖逐出后过期、pin 跨过期、多个引用、最后 release、恢复引用先于 sweep；pin 不能绕过容量限制。
- 在 test_disk_quota 覆盖冷快照到期清扫、删除失败、坏文件保留计量；未过期文件不被 sweep 完整重读，超额新建仍为 507。
- 并发读／淘汰／sweep／导出交错，无 KeyError、错页或读者对象被改写。
- 隔离临时 HOME 启动真实 serve，创建超过上限的快照，读取最早 ID、翻页、导出 CSV，与淘汰前结果对照。
- 固定大小合成快照对比驻留对象数、Python 分配量和 RSS，另测单个大快照；不把释放引用当作 RSS 立即下降。
- 定向 snapshot／quota／serve／export unittest 加真实 smoke；本轮仅跑既有基线，没有内存收益或新策略通过的实测结论。

## 验收标准

### 本轮文档

- ADR 历史正文保留，原启动／无淘汰描述只加注；§6 完整记录边界、安全检查、索引、复用、并发、风险与回退。
- 本 task 为 strict／checking，completed_at 为 null，模型次数不猜测；来源归属限于决策原话，其余方案由编排方整理。
- 索引仅由指定 TaskStore 生成器生成，只新增本任务一行，预览逐字节相同。
- 双语 rc.5 未发布节结构一致且各一条，位于 rc.4 之前，无未开 PR 的链接，已发布历史不变。
- 仅五个授权文件变化，无本机路径或不当归属措辞；所有指定基线实际运行，失败如实保留，不以本地验证代替 review／CI。

### 后续实现

- 操作结束后完整缓存不超过 8 条，启动不累积完整载荷，校验项不持有已逐出项。
- 有效快照可冷读，复用、原 ID／数据／expires_at、分页、cursor、导出不变。
- 过期冷快照仍可清扫，pin、404／410、拒读、507、未知文件保留不退化。
- 定向回归、真实 serve 与容量外瞬时对象／大快照峰值证据齐备，才可声称实现完成。

## 风险与恢复边界

- 多标签页／多查询可能在 8 条间反复冷读；共享锁内 I/O 增加等待，单个大快照／在途副本／索引仍可占较多内存。
- 不以跳过校验或拆锁换取未经证明的性能收益。容量仅限制完整缓存，不承诺 RSS 恒定。
- 不改磁盘格式；回退代码可读既有文件并恢复全量驻留，不删快照或 audit.db。
- 本轮不证明实现性能、Windows／macOS、跨平台耐久性、部署或发布就绪；独立 review、CI 和代码 PR 均未完成。

## 验证证据

证据类型：`developer-local`；Source Revision：`dirty`；Evidence Publication：`local-only`。源分支见 front matter，基准 SHA 为 `80f14263e7d8bc6ae84f04ba94218e4857fc8b8f`，环境为 Linux x64 的独立克隆。以下仅为本轮本地命令／工具输出，不是最终 PR head 的 CI 证据；不另建正式报告或扩大五文件范围。

| 命令／检查 | 实际结果 | 退出码 |
|---|---|---|
| `git status --short`、`git branch --show-current`、`git rev-parse HEAD` | 写入前工作区干净，分支匹配，HEAD 为上述基准 | 0 |
| `git ls-files --stage --`（四个既有目标与新 task） | 四个既有目标均为 100644；新 task 尚未跟踪 | 0 |
| `git check-ignore -v --no-index`（新 task 与 index） | 无匹配，不被忽略 | 1（无匹配） |
| `namei -l`（五个目标父路径） | 既有目标及父目录均非链接；新任务目录当时不存在 | 1（新目录尚不存在） |
| 专用 grep：在 tests 与 runtime tests 搜索 ADR 文件名，在 tests 搜索 CHANGELOG | 均无匹配；替代同模式 rg 文件定位，不虚构专项测试 | 不适用（工具未提供进程退出码） |
| 专用 grep：扩展搜索文档链接／格式检查 | 仅发现迁移 fixture 的链接测试及快照测试注释，未发现读取本次 ADR 或 CHANGELOG 的专项测试 | 不适用（工具未提供进程退出码） |
| `python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts` | 99 tests，OK；99 通过，0 跳过，41.001s | 0 |
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py'` | 457 tests，445 通过、2 失败、10 跳过；`FAILED (failures=2, skipped=10)`，191.054s；失败详情见下文 | 1 |
| `python3 --version`、`uname -srmo` | Python 3.13.5；Linux 6.12.113+ x86_64 GNU/Linux | 0 |
| 下方索引生成命令（仓库根执行） | `INDEX_REGEN changed=True rows=78`；出现既有“旧格式事件，不追溯”提示，生成成功 | 0 |
| 下方只读索引预览命令 | `INDEX_PREVIEW_SAME True rows=78`；逐字节一致 | 0 |
| `git diff --stat`、`git diff --check`、`git diff -- ai/tasks/index.md`、`git ls-files --others --exclude-standard` | 既有差异只有 ADR、双语 CHANGELOG、index；index 仅新增本任务一行；唯一未跟踪文件为本 task，空白检查通过 | 0 |
| `git diff --no-index --stat -- /dev/null ai/tasks/v2.1.0-rc.5-snapshot-memory-eviction/task.md` | 补充新 task 的新增统计；普通 diff 不显示未跟踪文件，未为统计改动 Git index | 1（预期：新增文件存在差异） |
| 专用 grep：新增／修改内容的本机路径扫描 | ADR、rc.5 双语条目、本 task、index 均无匹配；使用附件指定模式，不将敏感路径字面量复制进仓库 | 不适用（工具未提供进程退出码） |
| 专用 grep：本 task 与 ADR §6 的归属措辞扫描 | 附件指定的三类措辞均无匹配 | 不适用（工具未提供进程退出码） |
| 第 2 轮 omp 会话：下方只读索引预览命令 | `INDEX_PREVIEW_SAME True rows=78`；逐字节一致；出现既有“旧格式事件，不追溯”提示；未写入 index | 0 |
| 第 2 轮 omp 会话：`python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts` | 99 tests，OK；99 通过，0 跳过，43.840s | 0 |

索引仅运行编排方整理的指定生成器；没有手工编辑 index。实际命令如下：

```sh
python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); Path('ai/tasks/index.md').write_bytes(a); print('INDEX_REGEN', 'changed=%s' % (b!=a), 'rows=%d' % len(s._index_rows(r)))"
python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); print('INDEX_PREVIEW_SAME', Path('ai/tasks/index.md').read_bytes()==a, 'rows=%d' % len(s._index_rows(r)))"
```

runtime 失败记录（未修复、未重跑）：

- `test_runtime_perf_smoke.RuntimePerfSmokeTests.test_cli_preserves_dataset_and_reports_unmeasured_boundaries`：CLI 子进程返回 1，输出 `execution: failed`、`events: 101`，并提示未达 1M 档；顶层输出没有给出具体失败指标，不能把“未达 1M 档”直接认定为根因。内部报告位于测试临时目录，本轮不复制本机路径，不声称该临时报告为持久正式证据。
- `test_stats_query.NormalizeScopeTests.test_iana_queries_and_dst_work_without_system_timezone_data`：子进程缺少 `tzdata`，继而无法加载 `Asia/Tokyo`，触发 `QueryScopeError`。这是本轮可直接确认的环境缺依赖失败；没有安装或修改依赖。
- runner 记录 10 项跳过；输出另有 Playwright 未安装提示，但未逐项打印 skip 原因，不把全部跳过归为同一原因。没有把 renderer stub 或故障注入输出当作真实浏览器验证。
- 本轮只执行一次各指定 suite；失败如实保留，不扩展 docs-only 范围修复，也不声称全绿。`Final Full Rerun: failed`（指定 runtime 基线）；`Targeted Rerun: not-needed`（没有代码修复）；独立 review／CI 仍待执行。正式测试报告／同 stem 汇总未生成，本 task 为本地结果记录，不冒充发布证据。

### 第 3 轮本地验证

本轮仅修订本 `task.md`；`index.md` 仅由生成器写入且字节不变。基准 HEAD 为 `9aa5f4140cdcd6ed71f102ec755255838d330b87`，分支与 front matter 一致；Linux x64 独立克隆，写入前工作区干净。证据为 `developer-local`／`dirty`／`local-only`，不是 CI 或发布证据。

| 命令／检查（按执行顺序） | 实际结果 | 退出码 |
|---|---|---|
| 上方索引生成命令（含 `Path('ai/tasks/index.md').write_bytes(a)`） | `INDEX_REGEN changed=False rows=78`；出现既有“旧格式事件，不追溯”提示 | 0 |
| 上方只读索引预览命令 | `INDEX_PREVIEW_SAME True rows=78`；逐字节一致；出现相同既有提示 | 0 |
| `python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts` | 99 tests，OK；99 通过，0 跳过，35.455s | 0 |
| `git diff --stat`、`git diff`、`git diff --check` | 差异仅本 `task.md`，新增行无附件列出的本机路径，空白检查通过 | 0 |
| 专用 grep：全文件禁用归属措辞、旧模型说法及本机路径扫描 | 均无匹配；三个第 3 轮计数占位符留给会话末尾统计脚本填入 | 不适用（工具未提供进程退出码） |

`rtk: skipped-for-report`（直接执行指定原生命令，避免包装层缓存）；`BDD: skipped`（仅记录修正，无行为变化）；Cross-repo context／API Contract：not-needed；Mock Strategy：none。Book Gates、代码可读性复核、lint／build、Web／Mobile／serve smoke：not-needed（本轮不改设计、代码或测试）。未重跑 runtime 基线，历史失败保留；未生成正式报告，未 commit／push，状态继续为 checking，后续独立 review／CI 不由本地结果替代。

### 第 4 轮本地验证

本轮按 Reviewy NOT CLEAN 仅修正 ADR §6 的决策来源／状态措辞及本 `task.md` 的记录，不改已确认方案。基准 HEAD 为 `07f1cefe99980a8bffafb5539d0dcba7ee04b5ee`，分支与 front matter 一致，写入前工作区干净；Linux x64 独立克隆。证据为 `developer-local`／`dirty`／`local-only`，不是 CI 或发布证据。

| 命令／检查 | 实际结果 | 退出码 |
|---|---|---|
| `git status --short --branch`、`git rev-parse HEAD` | 分支与基准匹配，写入前工作区干净 | 0 |
| `TZ=Asia/Shanghai date --iso-8601=seconds` | `2026-11-11T16:29:09+08:00`；用于本轮 updated_at 与 checking→checking 事件 | 0 |
| `namei -l`、`git ls-files --stage --`、`git check-ignore -v --no-index --`（ADR、本 task、index） | 目标及父路径无链接，目标均为 100644；无 ignore 匹配 | 0／0／1（无匹配） |
| 上方只读索引预览命令，增加 `assert same` | `INDEX_PREVIEW_SAME True rows=78`；与 TaskStore `_index_candidate` 输出逐字节一致，未写入 index；出现既有“旧格式事件，不追溯”提示 | 0 |
| `python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts` | 99 tests，OK；99 通过，0 跳过，43.035s | 0 |
| 专用 grep：ADR 与本 task 的禁用措辞、模糊分钟及本机路径扫描 | 无匹配；固定决策原文含“注：分钟不可考。” | 不适用（工具未提供进程退出码） |
| `git diff --check`、`git diff --unified=0 --`（本轮授权文件） | 空白检查通过；差异仅 ADR §6 三行措辞及本 task 记录；ADR §1–§5、§6.1–§6.4 全部不变，8 份完整快照／LRU 不删磁盘等方案不变；index 与双语 CHANGELOG 无差异，rc.5 未发布标题不变 | 0 |

`rtk: skipped-for-report`（直接执行指定原生命令）；`BDD: skipped`（仅措辞与记录修正，无行为变化，无 feature 变更）；Cross-repo context／API Contract：not-needed；Mock Strategy：none。Book Gates、代码可读性复核、lint／build、Web／Mobile／serve smoke：not-needed（不改方案、代码或测试）。未重跑 runtime 基线，历史失败保留；未生成正式报告，未 commit／push，保持 strict／user／checking，completed_at 为 null。独立 review／CI 仍待执行；最后一次文件编辑仅补本轮日志计数，不以本地结果代替发布证据。

## strict 模式执行记录

- 用户 2026-11-11 15:10 群内确认（rc.5 全程用 strict），Lord 记录。编排方整理：先只读确认任务、根目录、分支、授权、基准及路径安全，再读完整 ADR、草稿、指定源码和 CHANGELOG；未把草稿 default 当成当前模式。
- 先冻结五文件范围再写；仅追加 ADR §6 与历史加注，配套 task／生成式 index／双语 CHANGELOG。状态记录为 checking，等待 review／CI，不写 done。
- 未完整调用 grill-with-docs：附件给出了明确决策、设计边界和验收条件，源码能回答当前行为，无需重复需求访谈；没有声称完成 grill 后的 DDD Gate。
- 已读取 sbtd-task strict／state 规则与 project-validation；遵从本轮限定，直接编辑文档，索引仅用指定只读 TaskStore 生成命令，不调用任务状态写 API、task 工具或子代理。
- 每个阶段只记录实际读取／写入／命令结果；验证失败不删除、不编造通过。原生 Python unittest 用于本地基线，`rtk: skipped-for-report`，避免包装层缓存；本轮不生成正式发布报告。
- 不 commit／push，不开 PR，由编排方在本轮结束后处理；独立 review 与 CI 待编排方安排，不冒充已执行。

### Book Gate Plan 与实际状态

| Gate | 客观触发／阶段 | 本轮状态与依据 |
|---|---|---|
| DDIA Data Design Review | 跨请求持久快照缓存设计，定稿前 | confirmed：已调用对应 Skill 并独立输出审查；磁盘为事实源，发布后登记、冷读完整校验、共享锁协调、索引复用不增 ID；无迁移，回退可读旧文件。仅设计确认，不是实现测试通过 |
| DDD Boundary Review | 完整 grill 或领域歧义后 | not-needed：未完整 grill，既有术语与生命周期不变 |
| Legacy Change Safety | 既有行为修改前 | not-needed：没有生产行为修改，源码基线与实施时场景已记录 |
| Refactoring Pass／Code Readability／ponytail-review | 生产代码或手写测试修改前后 | not-needed：只改文档，不做重构 |
| Release Readiness | 运行时／部署变化且测试后 | not-needed：文档 PR，不部署、不发布，不宣称淘汰已实现 |
| 独立 review／CI | 文档交付后的外部检查 | pending：本轮不调用子代理，保持 checking |

BDD：skipped（仅决策文档，不新增运行时行为或 feature）；Cross-repo context：not-needed；API Contract：not-needed（不改 API）；Mock Strategy：none。Web／Mobile／真实 serve smoke 不适用于本轮文档，留待实现；不新增测试框架或正式报告文件。

## 模型记录

| 轮次 | 模型 | 用途 | 模型调用 | 工具调用 |
|---|---|---|---|---|
| 第 1 轮 | `openai-codex/gpt-6-astra`（thinking high，主模型） | 编写 ADR §6、双语 CHANGELOG、task.md、index 与本地验证 | 18 | 45 |
| 第 1 轮 | `typesafe/jev-latest` | omp find 工具内部调用 | 10 | — |
| 第 2 轮 | `openai-codex/gpt-6-astra`（thinking high，主模型） | 补记模型调用次数 | 7 | 13 |
| 第 3 轮（历史：Reviewy 修正） | `openai-codex/gpt-6-astra`（thinking high，主模型） | 改 strict 记录口径与模型表 | 10 | 22 |
| 第 3 轮 | 其他后台模型 | omp 工具内部调用 | 无 | — |
| 第 4 轮（本轮：Reviewy NOT CLEAN 修正） | `openai-codex/gpt-6-astra`（主模型） | 修正决策措辞、披露历史填数、验证并直接写入记录 | 10 | 27 |
| 第 4 轮 | `typesafe/jev-latest` | find 未调用 | 0 | 0 |

第 1／2 轮次数沿用编排方依据 omp 会话日志的统计。第 1 轮 find 的会话日志每条记录为 `"purpose":"find","provider":"typesafe","model":"jev-latest"`，共 10 次；次数来自这些日志字段，归属 `typesafe/jev-latest`。

第 3 轮次数披露（Lord 16:21）：第 3 轮写入的调用次数，是当时由仓库外脚本在 omp 最后一次 bash 调用里填入文件的，不是 omp 在文件里亲手写的；从本轮起全部正文由 omp 直接写入。第 3 轮的 10 次模型调用、22 次工具调用保留为历史统计，不改称 omp 手写。

第 4 轮由 omp 收尾前按会话日志计数并亲自用 edit 写入：筛选 `type=message`、`role=assistant`、`provider=openai-codex`、`model=gpt-6-astra`，已有 8 条（含最后一次日志统计调用），加本次最终 edit 的 1 次模型调用及随后纯文本收尾 stop 的 1 次，共 10 次。相同 assistant 记录内 `content.type=toolCall` 已有 26 条，加本次最终 edit 1 条，共 27 次；按日志中的实际工具条目计数，不另计并行包装。日志中 `purpose=find`、`provider=typesafe`、`model=jev-latest` 的记录为 0，本轮未调用 find。统计命令只读日志并输出数字，没有写入仓库；本次为最后一次文件编辑，之后不再调用工具。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-11T14:38:57+08:00 | planned | planned | 编排方整理：保留主会话建立延后项草稿的事件，未开始实现 | 草稿记录已读取 PR #147／#190、ADR 0003 与源码；当时仅 task 草稿范围，基准 80f14263e7d8bc6ae84f04ba94218e4857fc8b8f；本轮不重复声称已访问这些 PR。 |
| 2026-11-11T15:14:16+08:00 | planned | checking | 用户 2026-11-11 15:10 群内确认（rc.5 全程用 strict），Lord 记录；编排方整理：按本轮 docs-only 范围编写 ADR 与配套记录，进入验证并等待 review／CI；未实现 | 已核对分支、基准、ADR 与指定源码；本轮命令结果见验证证据，文档提交／PR 由编排方处理。 |
| 2026-11-11T15:26:10+08:00 | checking | checking | 编排方整理：补记模型调用次数 | 会话日志统计 |
| 2026-11-11T15:58:57+08:00 | checking | checking | 按 Reviewy 意见修正：strict 记录口径改为用户 2026-11-11 15:10 群内确认（rc.5 全程用 strict），Lord 记录；补全模型调用次数 | INDEX_REGEN changed=False rows=78；INDEX_PREVIEW_SAME True rows=78；指定 unittest 99 tests，OK；diff 仅本 task.md，新增行无本机路径，禁用措辞无匹配，空白检查通过；详见第 3 轮本地验证。 |
| 2026-11-11T16:29:09+08:00 | checking | checking | 按 Reviewy NOT CLEAN 一次性修正决策来源／状态措辞，以及第 3 轮次数披露 | 固定决策原文已写入 ADR §6 的状态／来源／编排说明及本 task 的 mode_note／正文；第 3 轮脚本填数已按 Lord 16:21 说明披露；本轮验证结果见第 4 轮本地验证。 |
