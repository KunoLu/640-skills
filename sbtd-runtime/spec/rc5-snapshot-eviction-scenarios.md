# rc.5 快照内存淘汰场景

依据：ADR 0003 §6。沿用 Markdown 场景，中文描述＋英文关键词；不新增 runner。测试入口为 SnapshotStore、ExportStore 和真实 serve HTTP；故障注入只用于文件 I/O 与并发屏障，不替代真实 HTTP 证据。

## Scenario: 最近成功访问决定内存驻留

Given 隔离测试容量为 2，已有快照 A 和 B
When 读取 A 后成功创建 C
Then B 只移出内存，磁盘字节与配额占用不减少
And B 的原 ID、摘要、有效期、全部数据页、旧 cursor 和 CSV 仍可读取
And 相同查询复用 B，不新增文件，修改读取副本不影响后续读取

对应：`test_report_snapshot.SnapshotTests.test_lru_eviction_preserves_pages_reuse_and_csv`。

## Scenario: 启动只留轻量索引

Given 磁盘有 11 个有效快照
When 重启存储并依次读取所有 ID
Then 启动逐个完整校验后完整缓存为空
And 连续访问后完整驻留不超过默认 8 份，索引不持有载荷
And 不在启动索引的合法冷 ID 仍通过受控路径读取

对应：`test_snapshot_persistence` 的 startup 与 unindexed cold ID 用例；本地条数与瞬时对象诊断。8 是缓存条数，不是 RSS 或单快照大小上限。

## Scenario: 失败发布不登记半项

Given 已有可读快照
When 新建在 fsync 或原子发布时失败
Then 错误继续向上传递，原快照仍可读
And 索引、完整缓存与校验项没有新增半项
And 测试容量拒绝 bool、零、负数和非整数，serve 使用默认 8

对应：`test_report_snapshot` 容量用例、`test_snapshot_persistence.test_write_failures_preserve_prior_snapshot`；serve 默认装配诊断。

## Scenario Outline: 冷热读取都拒绝不可信文件

Given 原 ID 曾经成功读取，当前载荷为 <驻留>
When 文件损坏、未知版本、缺失、成为链接或读取时身份变化
Then 返回 SnapshotNotFound，不返回旧载荷
And 完整缓存与校验项同时失效，不删除坏文件或链接目标
And 合法替换重新完整校验后才可读取

Examples:

| 驻留 |
|---|
| 热缓存 |
| 已逐出 |

对应：`test_snapshot_persistence` 的 cold/hot refusal、replacement、fd identity 与既有异源 ctime 用例；Linux 注入不是 Windows 实测，不覆盖身份五字段完全不变的既有限制。

## Scenario: 引用保护磁盘而不是内存

Given 快照有两个后端引用
When 载荷逐出后 TTL 到期
Then 冷读仍返回原数据，pin 不豁免缓存容量
And 命中、重载与重启不延长期限，过期快照不参与查询复用
When 最后一个引用释放
Then 未清扫的原 ID 返回 410，磁盘仍在，正常 sweep 可删除
And 恢复引用先于启动清扫安装

对应：`test_snapshot_persistence` 的 evicted pins、restored references 与既有生命周期用例。

## Scenario: 冷清扫不扰动热缓存

Given 冷快照已到期，热快照未到期，目录还含坏文件
When 清扫或新建准入
Then 仅完整校验过期未 pin 候选，不完整重读未过期项
And 冷清扫不改变热缓存顺序，删除失败保留候选以供重试
And 成功删除移除索引、完整缓存及校验项并保留进程内 Gone
And 坏文件保留并计量，超额新建仍拒绝为 507，超额冷复用不增盘

对应：`test_disk_quota` 的 cold sweep、cold reuse 用例与既有共享配额回归。

## Scenario: 读者与在途导出不被淘汰改写

Given 读者和导出持有原快照对象
When 并发读取、分页、创建、逐出和清扫交错
Then 不发生 KeyError、错页或对象原地改写
And 导出仍返回原 CSV，终态释放引用

对应：`test_export_store` 的 eviction interleaving 用例及既有取消／失败引用回归。

## Scenario: 真实服务继续提供最早快照

Given 隔离 HOME 与 runtime 的真实 loopback serve 已完成鉴权
When 经 statistics/query 创建超过 8 个不同快照
Then 最早 ID 的 public_view、digest、有效期、全部页和旧 cursor 与淘汰前一致
And 新建 CSV 导出的内容一致，重启后仍能读取原快照与下载原导出

对应：本任务真实 HTTP smoke；仅使用既有 query、snapshot GET、dataset、exports 路由，不新增 snapshot POST 或调试端点。
