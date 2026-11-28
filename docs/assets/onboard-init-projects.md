# --init-projects 只初始化项目

project-only 模式。与普通 `--projects-root` + `--action init|reset` 互斥。不安装或更新全局工具、Skills、AGENTS、MCP 或 hooks。不构建项目图，也不删除历史项目目录。

`python scripts/onboard.py init-projects` 接受可选 `--platform`，但不需要 Trellis CLI、用户名或其平台标志。Trellis 参数已移除；普通项目无 task、developer 或 bootstrap 仍可检查和安装必要资产。

`install.sh --platform ... --init-projects` 仍跳过 Agent CLI gate，但会把 `--platform` 传给 `onboard.py`。

两安装器在可选 Playwright / React Bits 安装之前调用完整 `check-projects`，包含状态、目标和保护冲突；`--skip-project-agents` 仅排除用户未选择的 AGENTS 目标。Python 核心写入前再次检查所有所选根。下面展示核心写入流程，optional 安装仍各自确认。

使用已审阅 v2 包执行；追加项目的可复制提示词见[中文 README](../../README.zh.md#onboard-prompts)和[英文 README](../../README.md#onboard-prompts)。已有 v1 数据先走显式 migration；project-only既不是全局包 upgrade，也不授权旧数据清理。

```mermaid
flowchart TD
  start[确定项目根及是否写项目 AGENTS.md] --> entry{入口？}
  entry -->|根安装器| summary["Final plan 仅列平台、动作、项目根及 AGENTS 等摘要；不调用 plan"]
  summary --> confirm{"确认执行，或已传 --yes？"}
  confirm -->|否| abort[不调用 init-projects]
  confirm -->|是| dry{dry-run？}
  dry -->|是| stopDry[到此停止，不执行核心写入]
  dry -->|否| wrapperCall["携带所选范围和 --yes 调用 init-projects"]
  entry -->|直接调用 Python| core
  wrapperCall --> core["Python 构建文件操作；非 JSON 模式打印计划摘要"]
  core --> yes{"已传 --yes？"}
  yes -->|否| refuse[拒绝执行，不等待交互确认]
  yes -->|是| stateCheck[检查所选项目状态与目标]
  stateCheck --> stateOk{允许安装写入?}
  stateOk -->|否| stateBlock[逐项目报告 reason / nextStep, 零写入]
  stateOk -->|是| writes[按计划写必要项目文件]

  writes --> gi{项目 gitignore 已含模板全部非空行?}
  gi -->|从未安装或有缺行| appendGi[只追加缺行]
  gi -->|已安装且行齐全| skipGi[skipped-already-present]
  appendGi --> pAgents
  skipGi --> pAgents{本轮是否写项目 AGENTS.md?}
  pAgents -->|否| post
  pAgents -->|是且文件不存在| copyProj[复制项目模板]
  pAgents -->|是且文件已存在| bakProj[备份后覆盖]
  copyProj --> post
  bakProj --> post
  post[只读复查；不追加宿主接线，不构建项目图]
  post --> pw{项目已有 Playwright 适用标记?}
  pw -->|否| skipPw[Playwright: not-needed]
  pw -->|是且未装| notePw[仅汇报; 安装要另走 install-playwright-cli]
  pw -->|是且已装| keepPw[already-installed]
  skipPw --> rb
  notePw --> rb
  keepPw --> rb[React Bits 判定]
  rb --> rbApp{React 项目且存在 components.json?}
  rbApp -->|否| skipRb[React Bits: 不问]
  rbApp -->|是| noteRb[仅汇报适用性; 不在 onboard.py 里改 tier]
  skipRb --> done[汇总项目 AGENTS / gitignore / SBTD]
  noteRb --> done
```

## 从未初始化 vs 项目已有配置后再跑

| 对象 | 项目从未初始化 | 项目已有文件后再跑 |
|---|---|---|
| 用户级配置与全局工具 | 不安装、不写入；适用时只读检查已有 runtime | 不写用户级 MCP 或 hooks |
| Agent `--platform` | 仅平台上下文，不调用或安装 Agent CLI | 同样无全局操作 |
| 项目 `AGENTS.md` | Q4 同意才复制 | Q4 同意则备份后覆盖 |
| `.gitignore` | 追加缺行 | 行齐全则 skip |
| 历史项目目录 | 不构建、不删除 | 目录存在不证明宿主已接线；退役见 README 的退役说明 |
| task / developer / bootstrap | 不预建，缺失正常 | 只读检查选中记录；未完成 bootstrap 返回 6 |
| 旧 `.trellis` 或异常状态 | 无旧工具前置依赖 | 保留并报告需用户处理，不自动迁移或重建 |
| Playwright / React Bits | `onboard.py` 只在写入后汇报 | `install.sh` 才可能在写入前询问并另装 |

入口示例：

```bash
# 直接子命令：只维护必要项目安装资产
python scripts/onboard.py init-projects \
  --platform codex \
  --projects-root /abs/project-one \
  --yes

# 根安装器包装: 跳过 Agent CLI gate, 仍转发 --platform
bash install.sh --platform codex --init-projects /abs/project-one --yes
```
