---
schema_version: 1
id: v2.2.0-rc.3-host-baseline
workflow_mode: strict
mode_source: user
mode_note: rc.3 PRD D11、D13：T2 实测只提交任务记录，原生证据只保留在本地。
status: "blocked"
branch: test/v2.2.0-rc.3-host-baseline
created_at: '2026-11-27T11:03:03.289188+08:00'
updated_at: "2026-11-27T12:36:40.471005+08:00"
completed_at: null
"blocked_reason": "OMP：Codex 和 OMP 已完成本轮真实行为矩阵；剩余阻断是 agy D10 的已有登录复用与钥匙串不写入的可验证边界。"
---
# T2：三宿主行为基线和退役演练

## T1 合入回执

[PR #232](https://github.com/KunoLu/640-skills/pull/232) 的受审 head `2fce542894c279a0268a1fba2d3e985f1b19a0b6`：OMP 内置审查与 agy 独立复审均为 CLEAN，[PR validation](https://github.com/KunoLu/640-skills/actions/runs/45922706149) 13/13。agy 核销了 F1 和两个 P1，无新发现；这是静态审查，不是宿主 smoke。合入后 main 为 `dc228de75b4587df8abf05315e30bc7b9ebbb4ef`，内容树与受审 head 相同，[main validation](https://github.com/KunoLu/640-skills/actions/runs/45930622708) 13/13。已验证 T1 的本地和远程开发分支均不存在；未删除私有报告。T3 需保护 OMP 全局 AGENTS 导入链并评估探测进程 DNT；T4 评估宿主中性表述。

## 实测范围和停止条件

按 PRD Phase 0：分开验证 agy 的全局规则、同名 Skills、受保护配置与输出格式；三宿主的配置读取、真实审批及拒绝、工具装载和调用、事件、失败和中断；另测 Codex 延迟 MCP 启动、OMP lease／JSON／配置来源。用合成配置演练旧接线退役和悬空检测，不触碰真实宿主或启动原生结构图工具。只记录实际观察，不拿单纯版本匹配、主会话、历史报告或夹具作为真实行为通过凭证。

rc.3 精确验收 pin：`codex@0.172.0`、`omp@19.2.1`、`agy@1.5.18`。按用户在 D5 提前复核后的决定，只有 agy 的验收目标从 `1.5.16` 改为 `1.5.18`。本次复核时 agy 官方 CLI Latest 仍为 `1.5.16`；验收目标不改写该观察，也不改变官方版本监控的取值规则。后续适配和 T6 能力矩阵按这些目标执行；冻结前仍需复核，验收通过仍需相应版本的真实行为矩阵和 smoke。

每个宿主独用隔离 HOME、缓存、配置和合成项目。Codex／OMP 只允许隔离域内官方登录；agy 仅按 D10 复用已有钥匙串登录，不能读出或复制令牌，若要求重新登录或出现钥匙串写入迹象就停。不更新真实宿主。原生证据及中文摘要保存在本任务 ignored reports，不提交认证或会话正文。

## Book Gate Plan

本任务不改生产代码。无新领域、数据设计、迁移实现或重构：DDD、DDIA、migration 和 Refactoring 不触发。Legacy Safety 以本轮真实观察为后续 T3 的特征证据，不预记通过。验证以本机真实隔离进程为准；未执行不写通过，无部署／发布门。未完整调用 grill-with-docs：范围、四类退役夹具和停止条件已由 PRD 定稿。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-27T11:03:13.975367+08:00 | planned | in-progress | OMP：开始 核对三宿主测试入口及精确版本 | {"changed_files": [], "evidence_files": [], "sync_files": {}, "validation": ""} |
| 2026-11-27T11:03:56.108763+08:00 | in-progress | blocked | OMP：完成隔离版本预检；agy 已从 PRD 所述本机 1.5.16 变为 1.5.18，与 T2 精确验收 pin 不符，按定稿差异规则停止。 | 本地三组 --version 均 exit 0：codex-cli 0.171.0（目标 0.172.0），omp/19.2.1（匹配），agy 1.5.18（目标 1.5.16）。见 ignored reports/{codex,omp,agy}-version.txt 及同 stem 中文摘要。没有启动真实会话、登录或退役操作；未改变 pin、真实宿主或钥匙串。需可用的受信 agy 1.5.16 或经用户决定提前执行 D5 复核；Codex 仍需独立的匹配版本。 |
| 2026-11-27T12:02:53.960956+08:00 | blocked | in-progress | OMP：用户指定 agy 验收 pin 为 1.5.18，解除旧 agy 版本不匹配的阻断。 | D5 查询的 CLI Latest 为 1.5.16；此次为用户明确指定的验收例外，不作为官方 Latest 证据。 |
| 2026-11-27T12:03:04.707518+08:00 | in-progress | blocked | OMP：Codex 隔离预检为 0.171.0，仍缺已验证的 0.172.0 测试入口。 | 确认验收目标为 Codex 0.172.0、OMP 19.2.1、agy 1.5.18；后两者在已有预检中匹配。没有安装或升级，也没有新的 smoke。 |
| 2026-11-27T12:05:13.199147+08:00 | blocked | in-progress | OMP：用户授权在 T2 私有环境安装 Codex 0.172.0 并继续实测；保留 agy 1.5.18。 | 仅限任务私有测试域；不更新全局 CLI，不读取或复制真实认证。开始获取并验证固定发行物。 |
| 2026-11-27T12:13:31.273703+08:00 | in-progress | in-progress | OMP：完成 安装固定 Codex 并核对隔离宿主预检与离线协议 | {"changed_files": [], "evidence_files": [], "sync_files": {}, "validation": "Codex 官方 rust-v0.172.0 macOS arm64 资产 SHA-256 bd121f8abd6b28b3fc476da04a348e25a83e89eda19d39107f68f8e966053092。三宿主版本全匹配。Codex config/read 和同进程跨线程 optional stdio 实调用通过，缓存线程首次调用前无新启动、调用后增加一个并返回合成标记；不是模型审批。OMP 空 lease、隔离配置路径、禁用共享 MCP 后的 RPC get_state 成功；首次 RPC -11 已保留，未归因为产品缺陷。agy 1.5.18 的离线 ACP initialize 成功，未访问钥匙串。rc.2 归属夹具首轮缺 tomlkit，复用已有解释器后 7 passed、4 subtests passed，不是 rc.3 完整退役演练。原生或脱敏协议证据与中文汇总在本任务 ignored reports。"} |
| 2026-11-27T12:13:41.820165+08:00 | in-progress | blocked | OMP：三宿主版本阻断已解除；下一阶段 Codex／OMP 真实模型回合需要在各自私有 HOME 内完成人工官方登录。 | Codex login status 返回 Not logged in（exit 1），account/read 无账号且 requiresOpenaiAuth=true；OMP 使用独立新 HOME，未导入登录。未执行真实模型回合、审批矩阵或 D10 agy 钥匙串 smoke。不要在真实 HOME 登录或导出凭据；恢复后逐项补证。 |
| 2026-11-27T12:16:30.581259+08:00 | blocked | in-progress | OMP：收到用户已登录的回报，继续 T2 的隔离取证；逐宿主核对该身份是否对任务测试进程可用。 | 既有隔离 Codex login status 仍返回 Not logged in；不推断用户未登录、不搜索其他域。继续不依赖该账号的原生测试和退役演练，独立核验 OMP 与 agy。 |
| 2026-11-27T12:30:34.086827+08:00 | in-progress | in-progress | OMP：完成 取证隔离 Codex 0.172.0 行为矩阵 | {"changed_files": [], "evidence_files": [], "sync_files": {}, "validation": "用户澄清 OMP 登录先成功，Codex 设备码请求失败且 Teams 成员不可使用。隔离 Codex 指定系统公有 CA 后，原生 doctor 的 provider HTTP 从 fail 到 ok；未改代理或系统信任。改用官方浏览器登录，隔离 login status exit 0、account/read=chatgpt。完整包 SHA-256 0970016d48209a09c4039139629ed79b4a31c5e3d864e792c043419d98fa6466，与此前独立发行物的主二进制逐字一致。真实 readOnly/untrusted 线程按精确命令接收一次性审批，批准成功 exit 0、拒绝无退出码、批准缺失文件 exit 1、主动中断 interrupted。真实 MCP 回合同样获得三次匹配审批：允许实际读取，拒绝无服务端调用，允许缺失文件产生 ENOENT。保留初次仅列出目录却无模型调用的两份结果。#62366 同进程延迟启动见前轮原生证据；#62194 保留 exec resume 权限的上游变化只作记录，未作验收结论。"} |
| 2026-11-27T12:36:29.957993+08:00 | in-progress | in-progress | OMP：完成 验证 OMP 真实行为及 T2 退役演练 | {"changed_files": [], "evidence_files": [], "sync_files": {}, "validation": "OMP 19.2.1：真实 JSON 模型回合成功，无模型回退；RPC 明确拒绝、一次批准成功、ENOENT、abort；无交互审批 fail-closed 不算人工拒绝。活动 lease 为 held，退出后释放；不安全合成 lease 进入 unknown，生产适配器默认守卫退出 2 且未创建数据目录，恢复 0700 后为阴性。默认与 named profile 来源已验证。退役夹具验收 50/50：两个 MCP、Codex hooks、项目围栏；启动器缺失后三类悬空，围栏仍可证；第二次零写，恢复四项字节和原权限；五类负例均无目标写入。无真实 Graft/npx/清理；不冒充 T3 的生产退役实现。详见 ignored reports/omp-followup-01/snapshot、omp-unknown-guard-01、retirement-t2-01/result 的 JSON 及同 stem 中文汇总。"} |
| 2026-11-27T12:36:40.471005+08:00 | in-progress | blocked | OMP：Codex 和 OMP 已完成本轮真实行为矩阵；剩余阻断是 agy D10 的已有登录复用与钥匙串不写入的可验证边界。 | agy 1.5.18，隔离 ACP initialize 成功，缺省／合成 mcp_config.json 的原生 list 差分通过。已放置两份规则、同名与链接 Skill；ACP session/new 返回 -32603。仅放行回环、保持钥匙串和外网禁用的无终端负例提示 authentication required 后停止；没有执行登录、登出或复制凭据。这不是实际 D10 复用失败，也不能证明真实登录无效。官方文档描述静默复用，当前无已验证的只读钥匙串运行／写入审计边界；未开放无限制安全服务。规则预算、同名 Skills 优先级、受保护配置审批、成功 stream-json / transcript 字段和 agy 真实矩阵均未通过。T2 不开 PR、不进 T3。 |
