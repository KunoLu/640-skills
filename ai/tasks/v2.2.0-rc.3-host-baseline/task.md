---
schema_version: 1
id: v2.2.0-rc.3-host-baseline
workflow_mode: strict
mode_source: user
mode_note: rc.3 PRD D11、D13：T2 实测只提交任务记录，原生证据只保留在本地。
status: "blocked"
branch: test/v2.2.0-rc.3-host-baseline
created_at: '2026-11-27T11:03:03.289188+08:00'
updated_at: "2026-11-27T12:03:04.707518+08:00"
completed_at: null
"blocked_reason": "OMP：Codex 隔离预检为 0.171.0，仍缺已验证的 0.172.0 测试入口。"
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
