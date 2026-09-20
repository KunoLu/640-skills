# P1-15：Codex / OMP 三模式 smoke 与 token 计量

## 范围与边界

- 基线 `main` merge `bf996395d3fa034b64ce624417c352288ee4ba8f`（PR #63）。分支 `p1-15-codex-omp-mode-smoke`。
- 依据主 PRD P1-15 / AC-04、AC-14、AC-19、AC-20、AC-22、AC-23、AC-24。六个 host×mode 组合必须是真实 CLI 会话；mock、源码字符串匹配或 TaskRouter 返回值不能冒充 Agent 已按模式执行。
- 不写真实 HOME、不 sync live automation、不创建 rc tag、不跑 P2 迁移。CI 默认跳过 host 会话；本机用 `SBTD_P115_HOST=1` 才跑。
- 未完整调用 `grill-with-docs`：模式路由、token 目标和 host 分层已由主 PRD / P0-10 / P1-18 固定。

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

- 隔离项目根、`CODEX_HOME` / OMP `--profile`+`--session-dir` 均在临时目录。
- Codex：`exec --ephemeral --ignore-user-config --sandbox read-only --skip-git-repo-check --json`。
- OMP：`--print --no-session --no-extensions --approval-mode always-ask`。
- 提示只要求读 `AGENTS.md` 并报告当前模式，禁止写文件。
- 模式拒绝：default 任务上建议升 strict，检查回复是否暂停并保留 default 选项。
- HOME / 用户 Codex / OMP 配置目录前后 snapshot；预期外路径必须失败。

## Token 计量

- 公共核心目标约 2k、轻入口 ≤3k 是测量目标，不是保证。
- 优先使用 host JSON 中的实际 usage。没有 usage 时不得把字数换算成 token 并宣称达标。
- 可选 tokenizer 仅作并列观察，须写明编码名。

## 报告

- 正式 raw + 同 stem 中文 Markdown 写入 `tests/api/reports/`。
- `evidenceSource=developer-local`，dirty 只能 `local-only`。
- host 不可用、未登录或拒绝网络时标记 `blocked`，不伪造通过。
