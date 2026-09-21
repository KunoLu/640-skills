# P1-15：Codex / OMP 三模式 smoke 与 token 计量

## 范围与边界

- 基线 `main` merge `bf996395d3fa034b64ce624417c352288ee4ba8f`（PR #63）。分支 `p1-15-codex-omp-mode-smoke`。
- 依据主 PRD P1-15 / AC-04、AC-14、AC-19、AC-20、AC-22、AC-23、AC-24。六个 host×mode 组合必须是真实 CLI 会话；mock、源码字符串匹配或 TaskRouter 返回值不能冒充 Agent 已按模式执行。
- 不写真实 HOME、不 sync live automation、不创建 rc tag、不跑 P2 迁移。CI 默认跳过 host 会话；本机用 `SBTD_P115_HOST=1` 才跑。
- **grill-with-docs：未完整调用。** 只读了 Skill 与既有 PRD/P0-10/P1-18 事实。P1-15 是已冻结 AC 的验收，不新增领域术语或边界；完整访谈不会改变六格 host×mode、token 分层或拒绝/恢复口径。不进入 grilling 轮次，也不触发后置 DDD 门禁。

## Book Gate Plan

| Skill | 触发 | Gate |
|---|---|---|
| grill-with-docs | 未完整访谈 | not-required（现有契约已消除歧义） |
| book-ddd-distilled-modeling | 无新领域选择 | not-required |
| book-ddia-data-design | 仅隔离临时项目写 task 记录 | not-required |
| book-legacy-change-safety | 不改既有生产执行路径 | not-required |
| book-refactoring-pass | 无生产重构 | not-required |
| book-release-readiness | 不改生产运行时 | not-required |
| ponytail | 编码前 | running |

## 分层证明

| 层 | 证明什么 | 不能证明什么 |
|---|---|---|
| TaskRouter / 既有 unittest | AC-22/24 机器可检查的选择来源、拒绝保存、只读零写入 | Agent 是否先暂停推荐 |
| 入口文件规模观察 | UTF-8 字节与空白分词，只作规模观察 | AC-20 token 目标 |
| 真实 `codex exec` / `omp -p` | AC-04 六个组合的可观察回复、隔离目录副作用 | CI 可复现模型成功、Windows host、P3 观察统计 |

## Host 会话约定

- 隔离 `HOME` / `USERPROFILE`；Graft 走 `HOME/.codex`，与 `CODEX_HOME` 同指临时目录。只复制 `auth.json`。
- OMP 的 `PI_CODING_AGENT_DIR` 也在该临时 HOME 下，不设持久 `--profile`。
- Codex：`exec --ephemeral --sandbox read-only --skip-git-repo-check --json`。
- OMP：`--print --no-session --no-extensions --tools read`，避免 `always-ask` 挂起。
- 提示只要求读 `AGENTS.md` 与 `MODE` 并返回 JSON；提示正文不含 default/lite/strict。
- 从输出解析 JSON `mode`，不得用提示回声或裸子串匹配冒充读到了模式。
- 只断言临时项目树（`.git` / `AGENTS.md` / `MODE`）；不 rglob 真实 `~/.codex`。
- 缺登录或 CLI 记 `blocked`；live 矩阵未满 6 个 passed 则 skip，不当 AC-04 绿。

## Token 计量

- 公共核心目标约 2k、轻入口 ≤3k 是测量目标，不是保证。
- 优先使用 host JSON 中的实际 usage。没有 usage 时不得把字数换算成 token 并宣称达标。
- 可选 tokenizer 仅作并列观察，须写明编码名。

## 本轮实测

- 无 host：`python -B -m unittest tests.test_p1_15_host_mode_smoke` → 5 tests / 1 skip / OK。
- `SBTD_P115_HOST=1` 六格全 passed（约 67s）。报告：`tests/api/reports/api-report-p1-15-host-mode-smoke-p1-15-codex-omp-mode-smoke-2026_09_21-07_49_31`。
- Codex JSON usage 约 3.9 万 input tokens／格，含大量 cache；OMP 无 usage 字段。
- 这只证明隔离会话能读 MODE 并返回 JSON。不是 AC-20 达标，也不是完整 grill／strict Gate／跨会话恢复。
- `evidenceSource=developer-local`，`publication=local-only`。

## AC 缺口与本轮口径

| AC | 口径 | 证据 |
|---|---|---|
| AC-04 | **partial**：六格隔离会话能读 MODE 并返回 JSON。不是完整澄清／实现验证／strict Gate | live matrix；`SBTD_P115_HOST=1` |
| AC-14 | **machine-only**：模式分层仍由 bundled 规则与 P1-09 测试覆盖。host 未跑 Book/BDD | 不把 JSON smoke 当成 Gate 执行 |
| AC-19 | **inherited**：仓库 CI 可复现归 P1-14。本项 opt-in host 不进 CI | 无 host unittest |
| AC-20 | **measured-not-met**：Codex 约 3.9 万 input tokens／格；OMP 无 usage。不是 2k 达标 | 主机 JSON usage |
| AC-22 | **split**：TaskRouter 已覆盖推荐暂停与拒绝保存；host 增加 refuse/pause JSON（current≠recommended、paused、keep_option） | `test_sbtd_task_routing` + live refuse |
| AC-23 | **not-met for host**：未证明 default/lite 少加载 Gate | 如实记录 |
| AC-24 | **machine-only**：保存失败不冒充恢复由 TaskRouter 测试覆盖 | 无 host 跨会话 |

## 报告

- 正式 raw + 同 stem 中文 Markdown 写入 `tests/api/reports/`。
- `evidenceSource=developer-local`，dirty 只能 `local-only`。
- host 不可用、未登录或拒绝网络时标记 `blocked`，不伪造通过。
