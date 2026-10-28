# Graft 0.22.0 → 0.28.0（Trail-code 时代）升级评估报告

- 日期：2026-10-28
- 评估人：omp（strict task `graft-trail-code-upgrade-eval` 阶段 1）
- 隔离环境：`/tmp/graft-eval`（npm pack 提取 + `npm install --omit=dev`），fixture 仓库 `/tmp/graft-fixture`，全程 `DO_NOT_TRACK=1`

## 结论

**建议升级**：保持 `@nanonets/graft` 包名不变，pin 从 0.22.0 升至 0.28.0。不换 `@trailhq/trail-code`、不启用 login/workspace/hooks/skills/云同步。SBTD 所需离线 code map 能力在 0.28.0 上经实测完整可用，遥测边界经实测保持。

## 官方状态（registry/CHANGELOG 实证）

- graft 更名 Trail-code（trailhq/Trail-Code），同一构建双发包：`@trailhq/trail-code`（`trail` 命令）与 `@nanonets/graft`（`graft` 命令不变，CHANGELOG 明示两者持续同步发布）。
- npm `@nanonets/graft` latest = 0.28.0；tarball `https://registry.npmjs.org/@nanonets/graft/-/graft-0.28.0.tgz`；integrity `sha512-zto3AJeK5qMdjhZrsrIr0Bq7agySU/aPIgBgokpPXleabiY9l83iHUETec9oeMiiBZM7YRxh4OSDMHlP4sSwBA==`（本地下载实测 sha512 逐字节一致）。
- 0.24.0 起 update check 遵守 `DO_NOT_TRACK`（上游 #651）；0.24/0.25 含多个 Windows 修复（language server 启动 #579、console 窗口 #631 等），与本次 Windows 迁移修复方向一致。

## 隔离实测结果（0.28.0，fixture 2 文件 Python 仓库）

| 检查项 | 结果 |
|---|---|
| `graft build . --no-gitignore --no-ignore`（受管精确参数） | exit 0，全离线，4 nodes/4 edges/2 cards |
| 输出目录 | 仍落 `graft/`（`--dir` 默认 `<repo>/graft` 保留；`.trail/cache` 迁移只发生在 `trail init` 管理路径） |
| 副作用 | fixture 内未创建 `.trail/`、hooks、`.claude/`；git 状态干净 |
| `graft telemetry`（DNT 下） | `telemetry: off`；`update check: off` |
| `ask`（无 API key） | exit 0，`"mode": "structural"`，返回 callers JSON |
| `map/skeleton/callers/check/grep/blast`（受管精确参数含 `--json`/`--no-refresh`/`--fixed`） | 全部 exit 0，JSON 输出 |
| `graft mcp` 工具面 | 仍暴露 graft_find_code / graft_trace_calls / graft_find_all / graft_file_api / graft_repo_map / graft_check_freshness，与本仓库 MCP 接线一致 |
| `dist/claude/hooks.js`（graft-hook-entry.mjs 钉住的模块） | 存在；`main(event)` 形状由 launcher 每事件重证，实施阶段回归测试兜底 |

## 风险与应对

| 风险 | 评估 | 应对 |
|---|---|---|
| R1 0.23.0 起 `trail init` 把图迁到 `.trail/cache/` | 对受管裸 build 无影响（实测默认仍 `graft/`） | `graft-build-policy.json` 保持 `graph_directory: "graft"`；实施冒烟确认 |
| R2 新增 login/workspace/hooks/云同步面 | 不启用即不触发；受管子进程已 scrub `TRAIL_*`、固定 Graft 品牌、禁 fetch/切换（0.22.0 既有机制） | 边界不变；`graft check`/动词实测不触发网络要求 |
| R3 hooks 模块形状漂移 | 文件仍在；形状由 launcher 每事件重证 + fail-closed | 实施阶段跑 graft entry/isolation 全量测试 |
| R4 `--deep`/LLM 依赖 | 政策已禁 `--deep`，`llm:false`；`openai`/`@anthropic-ai/sdk` 仍为非默认依赖 | 不变 |

## 阶段 2 实施清单（确认后执行）

1. `graft_runtime.py`：`GRAFT_PINNED_VERSION="0.28.0"`、`GRAFT_TARBALL_URL`、`GRAFT_TARBALL_INTEGRITY` 三常量。
2. `assets/graft-build-policy.json`：`version` → `0.28.0`。
3. 文案版本引用：`install.sh`、`install.ps1` fallback 显示串；`graft-instructions.txt`、`graft-hook-entry.mjs` 注释；`REFERENCE.md`、`SKILL.md` 的 pin 引用。
4. 测试：`tests/test_sbtd_graft_entry.py` 3 处 `0.22.0` 字面量；`test_graft_runtime.py` 动态读常量（无需改）。
5. 验证：受影响测试 + macOS 全量 + 受管安装器 dry 路径；真实 build 冒烟（隔离前缀安装 0.28.0 并建图）。
6. CHANGELOG 双语条目（PR 号回填）。
7. **不改** `ENTRYPOINT.md` 的 Graft 版本行：按既有规则，ENTRYPOINT 基线只在已发布 workflow 的受管 pin 变化后由版本检查同步；`update` 不写 Graft。PRD v0.2 的 0.22.0 为历史核对基线，不改写。

## 确认门

阶段 2 待用户确认后执行。
