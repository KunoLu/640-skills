# rc.5：401 自动重新配对

依据：ADR 0001 §9。沿用既有契约，不改变初次配对、快照和导出语义。后端由 `test_serve.py` 的 RecoveryTests 与 PairingTests、`test_exports_http.py` 追踪；前端由 `api.test.ts`、`exportJob.test.ts`、`pageModel.test.ts` 追踪。后端使用真实 ASGI／loopback；前端故障注入为 contract-backed，不等同真实页面 smoke。

```gherkin
Feature: 过期会话的一次自动重新配对
  Scenario: 半开恢复窗口不授予数据访问权
    Given 人工配对会话在时刻 E 到期
    When 在 E 前、E、E 加 59.75 秒和 E 加 60 秒请求取票
    Then 只有 E 至 E 加 60 秒之前允许取票
    And 普通 API 从 E 起立即返回 401
    And 到达右端删除恢复记录
    And 票寿命不超过 30 秒且不越过窗口右端

  Scenario: 来源检查先于预算和秘密检查
    Given 当前进程有已到期的人工配对会话
    When Host 不在 loopback 白名单或端口不符
    Then 返回 403 forbidden
    When Origin 缺失、null、异主机或含路径、userinfo、query、fragment
    Then 取票与恢复票交换返回 403 forbidden
    And 不消耗票或取票预算
    But 初次配对保留原有 Origin 规则

  Scenario: 两个秘密绑定同一恢复记录
    Given 会话处于恢复窗口内
    When Bearer 或 CSRF 缺失、不符、来自其他会话
    Then 返回 401 unauthorized
    And 未过期、未知、撤销、重启前和无资格会话也返回同一错误

  Scenario: 并发只能签发和交换一次
    Given 合格的过期凭证
    When 并发请求恢复票
    Then 最多一个请求得到 200
    And 签发立即耗尽资格，不因丢失响应补发
    When 首次通过来源检查后用错误、缺失、过期或正确票交换
    Then 待交换票被消费且不可重放
    And 成功交换只建立一个无再恢复权的替代会话

  Scenario: 每进程滚动预算不滑动
    Given 60 秒内已有 10 次通过来源检查的取票请求
    When 再次请求取票
    Then 返回 429 RE_PAIR_RATE_LIMITED 和向上取整的 Retry-After
    And 拒绝不增加接纳数，错误凭证仍计数
    And 最早接纳请求离开窗口后释放名额，重启清零

  Scenario: 所有配对响应禁止缓存且秘密不外泄
    Given 初次票、恢复票或取票请求
    When 返回 pair 的 200、401、403 或取票的 200、401、403、429
    Then 每个响应均带 Cache-Control no-store，包括中间件拒绝
    And 恢复秘密不进入 URL、日志、文件或浏览器存储
    And 仅新会话成功后写入 sessionStorage

  Scenario: 同标签页并发与迟到的 401 合流
    Given 多个携带同代次会话的受保护请求
    When 它们收到 401
    Then 只取票和交换一次，并移除存储中的旧凭证
    And 每个原请求最多重放一次，迟到旧 401 不删除新会话
    But health、初次 pair、取票不递归恢复
    And 403、404、410 和普通网络错误不触发恢复

  Scenario: 不确定的恢复结果转人工
    Given 正在取票或交换恢复票
    When 响应丢失、5 秒超时、服务器错误、429 或期限耗尽
    Then 不盲重试、不补票，清空临时秘密并停止自动请求
    And 中英文提示先停止 serve、重新启动，再使用新配对链接

  Scenario: 保留视图并完成一轮刷新
    Given 已完成的视图、筛选、展开项和正在分页的快照
    When 401 恢复进行中
    Then 暂停主轮询和导出轮询，并提示画面未刷新
    When 恢复成功
    Then 只启动或继续一轮完整主视图刷新
    And 分页继续原 snapshot_id 与 cursor，全部完成后才替换画面

  Scenario: 导出恢复不更换原操作
    Given 导出创建、查询、下载或取消遇到 401
    When 恢复成功
    Then 重放保留原载荷、snapshot_id、export_id 和 Idempotency-Key
    And 不创建新作业，不重置 40 次查询上限
    And 创建网络重试不叠加突破一次恢复重放上限
    And 404 与 410 保持原业务错误

  Scenario: 取消和卸载不复活操作
    Given 恢复中有多个等待者和在途导出
    When 一个等待者取消或页面卸载
    Then 该操作不再重放，不接纳迟到成功或重复下载
    And 不删除其他等待者仍有效的新会话
```
