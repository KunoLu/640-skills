# PR #110 第二轮审查修复

审查基线：40b0dbf62745861123be3e94e25ad02aa660b155。沿用 strict；用户要求先修 P1，再按风险依次修复全部其余问题。本轮编号 N01–N14 对应最新审查 1–14，与 review-fixes.md 的旧 R01–R19 分开。

未完整调用 grill-with-docs：修复目标、既有契约与授权明确，无新增领域模型。保留缺失 host 仍安装、受支持嵌套安装及 installed-copy 续作、restore intent + absent 恢复窗口、OMP user-wide 隔离探测四项契约。允许提交／推送当前草稿 PR 及 CI；不授权同步、真实 HOME 应用、合并、发布、真实旧资产清理或备份销毁。

## 优先级与顺序

| 顺序 | 编号 | 级别 | 风险与验收 |
|---|---|---|---|
| 1 | N01 | P1 | 冲突物理目标别名在写入前拒绝，preserve 原件不变 |
| 2 | N02 | P2高 | Windows 大小写敏感的不同路径不去重、不共享错误摘要、不误判包含 |
| 3 | N03 | P2高 | 已选非 Skill／Onboard 子目录真实别名绑定封存拼写 |
| 4 | N04 | P2高 | 继承输入别名冲突在任意目标写入前拒绝 |
| 5 | N05 | P2高 | 封存 blocked host 决定不被 drift／aligned 掩盖 |
| 6 | N09 | P2高 | method 回复仅 result／error 有效，不接受 data 冒充 |
| 7 | N10 | P2高 | MCP 初始化协商版本必须属于支持集合 |
| 8 | N11 | P2高 | MCP 异常关闭不能证明 protocol verified |
| 9 | N06 | P2中 | 首行 UTF-8 BOM 的标记识别及替换保留 BOM |
| 10 | N07 | P2中 | 新 PowerShell profile 的 Unicode PATH 可由 5.1 正确解释 |
| 11 | N08 | P2中 | 登录 profile 以隔离登录语义探测 |
| 12 | N12 | P2中 | probe 未确认的拒绝满足 failureDocument，不读取 plan |
| 13 | N13 | P2中 | home 展开失败在输入边界转受控 JSON 拒绝 |
| 14 | N14 | P3 | method-not-found 脱敏分类为 unsupported |

## 测试与所有权

沿用已确认 seam：公开 CLI、build_inventory、plan/apply/verify/recovery、host render/verify；协议故障由可控子进程模拟，仅证明协议边界。主会话唯一验证 controller。优先真实临时文件系统；平台 skip 不算通过。保留 red 与同 stem 中文汇总；原始报告位于 reports/review-round2/。LSP 实测无已配置服务器，采用源码调用点／contract 分析，不假称 LSP 影响证明。

BDD 继续用 REFERENCE.md Markdown 场景，中文正文、Given/When/Then 英文，不创建 .feature。数据契约不改 schema 版本或 vault 历史格式；输入路径保留字面拼写并拒绝链接，身份由实际文件系统证明。

## Book Gate Plan

| Gate | 触发／时点 | 状态 |
|---|---|---|
| DDD | 无 full grill 或领域歧义 | not-required |
| DDIA | 物理身份、写入预检和协议证据；开发前 | confirmed：字面封存与物理身份分离，原有 vault／恢复格式和单 writer 不变 |
| Legacy | 既有行为修复；每切面生产编辑前 | characterized：N01–N14 逐切面 red／green；N07 是旧编码模型，原生 Windows 待 CI |
| Refactoring | 既有生产代码；Legacy 后 | proceed / normal：无广泛重构，既有 public seams 足够 |
| Release | 完整验证与独立复核后 | pending |

## 已执行的局部验证

- P1 首先执行：真实库存的冲突 AGENTS 别名计划 red，修后公开 CLI 写前拒绝，原字节与空 vault 保持；`n01-*`。
- N02 在自建 Case-sensitive APFS 卷，模拟 Windows normcase 的不同根／配置越界 red/green；最终两个场景通过、三个相反平台用例跳过。Windows 测试仅在自身空临时目录启用 fsutil case sensitivity，原生结果待 CI。
- N03 两个合法别名 red/green。初次 green 报告暴露测试误读 inventory 的不存在 scope 字段，改为实际 normalize_scope/domain 消费接口后通过；失败保留，不作为产品缺陷。
- N04 公开 CLI 原实现 partial，修后 inherited-dependency-conflict 且 provider 原件和 consumer 缺席保持。N05 真实 profile 封存 blocked 优先于 drift／后来磁盘对齐。
- N09／N10／N11／N14 的协议模拟回归已过；额外真实子进程拒绝 data-only、未知版本和退出7，区别于真实外部 MCP 服务。MCP 仅支持初始化式版本 2024-11-05、2025-03-26、2025-06-18、2025-11-25；[2026-07-28 官方协议](https://modelcontextprotocol.io/docs/2026-07-28/learn/versioning)已改逐请求协商，不伪称兼容。
- N06 BOM 与 UTF-16 6项回归通过；N07 旧编码模型＋原生 pwsh red/green、Shell/PowerShell 13项（1原生Windows skip）；N08 原生 Bash／zsh 登录及 rc 对照通过；N12／N13 真实 CLI schema 和路径展开拒绝通过。
- `round2-upgrade-regression`：302 tests，OK，13平台／条件skip。`round2-ruff-green`、`round2-ty`、compileall 与 Bash syntax 通过；首轮 Ruff 的测试 callback／subprocess 约定问题修正且原始失败保留。
- `native-round2-*`：最终实现包 37资源 plan/apply，真实 Codex app-server 与 OMP RPC 各加载33 Skills、6工具，分层全部 verified；安装副本 retry 与 recovery 成功，恢复原 profile 和旧自包字节。仅隔离临时域，不等于真实 HOME／GUI 重载。
- README.html 用 Chrome DevTools 隔离页面实测两个新增区块可见；Ego沿用前轮不可用证据，不安装或修配置。无业务Web/Mobile变更，Playwright/Maestro专项not-needed。
- 宿主独立 reviewer 未发现高可信剩余缺陷；路径／事务／CLI独立复核和完整项目 suite 尚在进行。原始报告及同stem中文汇总保留在 reports/review-round2/；developer-local／dirty／local-only，不能冒充新提交 CI。

## 文档与方法判断

README.md、README.html、版本化 automation prompt 均需同步并已追加本轮长期边界；CHANGELOG 顶部未发布章节追加修复；REFERENCE U20—U24 为持久场景，配合既有 U18／U19。未改 live automation、ENTRYPOINT 版本或任何全局生效目录。BDD: traceable，中文＋英文 Given/When/Then；Cross-repo context: not-needed；API Contract: verified（本地 schema 与官方协议）；Mock Strategy: contract-backed。rtk: skipped-for-report。

Ponytail／Code Readability：保留必要的物理祖先检查、输入异常 seam 和收尾状态，不引入依赖、通用框架或新配置。Lesson 使用已验证本地身份 kuno，记录到 validation-scripts topic 与 index；短入口已有通用回归规则，不再堆叠本次详情。

## 独立复核修正

路径 reviewer 发现两处相关遗漏：缺失目标没有 inode 时的大小写别名仍能穿过 preserve；WindowsPath 等值可能选错大小写敏感双根的 Onboard provider。两项均修正，未改变四项保留契约。缺失尾部歧义仅在共同物理祖先下检查，Darwin／Windows／Linux 分别只读查询目录大小写语义，无法证明则拒绝歧义；已存在目标仍用物理身份。provider 按已封存目标精确拼写选择，不用 WindowsPath 折叠。

新增公开真实库存／计划回归和完整包双根＋host apply。普通卷与 Case-sensitive APFS 各8项（各4 skip）互补通过；后者包括实际双根安装成功。修正后305项升级回归通过、15 skip；Ruff／ty通过。`final-native-*` 再次完成37资源 plan/apply、真实 Codex／OMP、installed retry/recovery及原件恢复。此前启动的全量因复核修正主动取消，不计通过；新的完整运行已启动。

两位独立 reviewer 最终均无本轮剩余 finding：宿主切面一次通过，路径切面两项修正后复核通过；reviewer 未运行验证。路径复核额外指出 APFS 缺失文件 NFC／NFD 规范化等价属于基线已有、未纳入本轮14项的边界；本轮只证明大小写别名与所列场景，不宣称涵盖所有 Unicode 等价路径。
