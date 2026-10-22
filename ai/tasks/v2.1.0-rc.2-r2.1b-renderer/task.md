---
schema_version: 1
id: v2.1.0-rc.2-r2.1b-renderer
workflow_mode: strict
mode_source: user
mode_note: 沿用用户 strict；Round 6（operator run7）先完成已开始的 origin/main merge，再接线 #154（d46d4ad）的 503 与失败码；13:38 固定字符串规则已被 #154 取代。当时本地 run 仅授权 worktree，显式 git add，不自行 push／PR／评论／rebase；随后 operator 已 push／开 PR #155，并已 squash-merge。不暂存 .omp-r12b-addendum.txt 或 ai/tasks/codex-verify/；merge 后冻结 contracts、Panel manifest、ADR 0001–0003、PRD、CSV schema。
status: done
blocked_reason: null
branch: feat/v2.1.0-rc.2-r2.1b-renderer
created_at: '2026-10-22T11:12:22+08:00'
updated_at: '2026-10-22T16:22:16+08:00'
completed_at: '2026-10-22T16:22:16+08:00'
---

# R2.1b：JPEG/PDF 独立 renderer

基线 `8931c35ef1aa4a58d3675b6f8d1a8fead309ed90`（R2.1a #151）。当时本地验收不代表评审、合并、部署或发布；随后 operator push／开 PR #155，已于 `2026-10-22T16:22:16+08:00` squash-merge 为 `c5904ef787c29bf9761f44ca4613ce0f2805daa4`。本任务从未本地记 done，completed_at 取合并时间；不把合并等同部署或发布。

## 范围与验收

1. JPEG/PDF 复用 R2.1a 服务端静态 HTML、ExportStore 作业、snapshot pin、原子发布、manifest/digest、24h 保留及启动清扫。
2. Playwright 可选、精确钉版；only-shell Chromium 安装到 `$SBTD_RUNTIME_HOME/browsers/`；依赖清单钉 fonts-noto-cjk，记录实测体积。
3. 每作业子进程与临时 profile；路由拒绝外联和 file；单作业信号量、超时及清理。
4. JPEG 按 §13.5 像素预检、降采样与安全失败；PDF 按 §13.6 可搜索、中日英字体嵌入、长表与页脚。
5. 四格式沿用同一 event-detail exportable/classification 过滤；不改变 derived rows 或 withheld 值。
6. 缺依赖仅 JPEG/PDF 不可用并附原因；Round 4 依 #153 开放 HTTP，Round 6 依 #154 接线受理前 503 与受理后固定失败码；JPEG 依赖可用后预检、固定比例生成，PDF 不做尺寸预检。
7. 单元、真实浏览器、全量指定回归、真实 runtime snapshot smoke、独立复核及冻结契约检查。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-10-22T11:12:22+08:00 | planned | in_progress | 用户指定 strict；授权 worktree、分支与基线匹配；建立共享交付记录 | pwd、git status/branch/rev-parse；用户任务 |
| 2026-10-22T11:13:00+08:00 | in_progress | in_progress | 补记用户后续项 A 决定：保持 #151 事件明细屏蔽行为；不新增 withheld，不为 A 开 contract PR | 用户 round-2 指令；保留四格式 event-detail 屏蔽一致性回归，AC-51 完整验收仍归 R2.2 |
| 2026-10-22T12:17:20.268311+08:00 | in_progress | in_progress | Run 1b 从 ceb202e 续接；库级实现、真实 smoke、指定回归与两位独立复核完成。本地验收通过，保留 in_progress 等待 operator 提审／契约后续，不宣称已发布 | runtime-final-full 341／7 skip；renderer-final-full 39／1 Windows skip；contracts 69、OpenAPI 16；smoke-receipt.json；reviewer closure |
| 2026-10-22T12:35:13.972967+08:00 | in_progress | in_progress | Round 2：A/B/C 与独立 contract PR 登记、模型回填、F 文档越界修正（C 的当时放置已由 10-22 15:00 决定取代，现归第 7 项／F）；补齐事前降级通知／配置跨进程传递和 capabilities 认证回归；本地指定回归与真实 smoke 通过 | round2/runtime-final-full 344／8 skip；renderer-final-full 42／1 Windows skip；contracts 69、OpenAPI 16；runtime-final/smoke-receipt.json |
| 2026-10-22T12:59:34.599901+08:00 | in_progress | in_progress | Round 3 库级 PR #153 对齐、受理前 preflight、AC-42 kana／9pt 页脚完成；本地验收通过，HTTP／合并与跨平台仍不冒充完成 | r3/kana-smoke；kana 720；renderer-final-full 44／1 skip；runtime-native-final-full 346／9 skip；ruff-final；两位独立 reviewer 无发现 |
| 2026-10-22T13:13:53.129882+08:00 | in_progress | in_progress | Round 4 用户明确 strict，入口 340d207、分支与 worktree 匹配；合并 #153 后 HTTP 接线；完成 before-dev 事实与安全网 | http/before-dev-safety：11 passed；合并 OpenAPI 与 #153 task；本轮场景已更新 |
| 2026-10-22T13:55:48.915515+08:00 | in_progress | in_progress | Round 4 独立安全 review 两项发现经红绿修复；指定全部命令与真实 HTTP smoke 重新通过，保留 in_progress 待评审 | http/review-regression-red／green；runtime-reviewed-full 366／10 skip；renderer-reviewed-full 62／1 skip；final/transcript.json；Safety closure Findings=[] |
| 2026-10-22T14:02:40.176880+08:00 | in_progress | in_progress | Round 4 验证收口：独立 safety／contract review 通过，冻结路径最终 diff 为空；仅本地 Linux HTTP 交付 ready，保留 review pending 与两项契约缺口 | http/protected-final；reviewed 全套报告；Safety Findings=[]；ContractReview correct；Release Readiness ready（限定授权范围） |
| 2026-10-22T14:08:00+08:00 | in_progress | in_progress | Round 5 用户明确 strict；入口 09c4c6669f64e4580f0e12b55de7bd1b591a90d6、分支与干净 worktree 已核对；执行固定失败字符串规则 | 用户 13:38 规则与 #154；本轮仅授权四模块审计、最小修复、回归及记录 |
| 2026-10-22T14:24:05.351023+08:00 | in_progress | in_progress | Round 5 固定错误规则、四模块审计、指定全部回归与真实 HTTP timeout smoke 完成；两位独立 reviewer 收口，保留整体 review pending | http/r5/runtime-reviewed-full 366／10 skip；renderer-reviewed-full 62／1 skip；contracts-reviewed 71；golden-reviewed 55；real-http-reviewed；final-server-log.txt |
| 2026-10-22T14:38:21+08:00 | in_progress | in_progress | Round 6（operator run7）沿用 strict；两份指定文档冲突按要求解决，真实 merge 完成；开始 #154 接线 | merge 8ac91c6a1853550a2c94f4e4d406d764514570f2；parent d46d4ad2097742e48441f8d094f29570131a5377；冲突列表为空 |
| 2026-10-22T14:53:27+08:00 | in_progress | in_progress | Round 6 本地交付验证完成；#154 两项缺口均 satisfied，13:38 规则取代；整体保留 operator smoke／提审状态 | runtime 370／10 skip；renderer 64／1 skip；contracts73、golden57；Ruff5；Store smoke5；Safety Findings=[]、Contract correct |
| 2026-10-22T15:37:59+08:00 | in_progress | in_progress | Round 7（operator run8）：Reviewy doc fixes；修正 Round 3 effort、run7d 计数、plan R2.1b 行 → #155、plan:65 已完成，登记后续项 D | docs-only diff；git diff --check；仅本 task 与 plan，无代码变更 |
| 2026-10-22T16:22:16+08:00 | in_progress | done | Closeout：#155 squash-merged；operator 已 push／开 PR，本任务从未本地记 done，completed_at 采用合并时间；不改历史验收证据或契约 | merge SHA c5904ef787c29bf9761f44ca4613ce0f2805daa4；mergedAt 2026-10-22T08:22:16Z；git committer 时间 2026-10-22T16:22:15+08:00；run8 最终 9 assistant messages／24 toolCall blocks |

## 决策

- 未完整调用 grill-with-docs：用户范围、锁定决定与冻结契约边界明确，不重开需求。
- 后续项 A 已决定（用户 2026-10-22 11:13 +08:00）：保持 #151 行为，仅屏蔽 `exportable=false` 或 `classification != local-metadata` 的 event-detail 行；派生 task/run/aggregate 不过滤。四格式共用同一过滤管线，不新增 `withheld` 值，不为 A 开 contract PR。保留 AC-51 四格式事件明细屏蔽一致性测试作为该决定的回归保护；AC-51 完整验收仍在 R2.2，不宣称本轮通过 AC-51。
- 后续项 B 在计划第 7 项／F 阶段回填 `install-and-use.md`；后续项 C 同归第 7 项／F 阶段，另开单独 PRD docs PR，独立于第 4 项的 PRD §10.4 磁盘上限补充。依据「用户 11:15 授权，10-22 15:00 确认放第 7 项」。C 明确本地导出在 `exportable=false` 或 `classification != local-metadata` 时屏蔽 event-detail 行，task/run/aggregate 派生行不受影响，与 B 措辞一致；先前放置决定由本次确认取代。本轮不改 PRD，也不提前交付 B／C。
- 后续项 D（待用户决定，Reviewy 2026-10-22）：只读核对 `serve.py:create_export` 与 `export_store.py:ExportStore.create`，当前先校验请求体／Idempotency-Key，再对 JPEG／PDF 检查 renderer 可用性；不可用则直接返回 503 `EXPORT_RENDERER_UNAVAILABLE`，早于 Store 内的 snapshot 404／410 检查及幂等重放。因此，同一 jpeg/pdf 请求曾受理后，若 renderer 被移除，再以相同 Idempotency-Key 重试会返回 503，而非原 export_id。#154 未规定 availability、snapshot 404／410 与幂等重放之间的优先级；该 503 不进入 Store，不创建作业／文件、不 pin 快照，也不持久化此次请求的幂等结果。本轮仅登记，无代码变更，是否调整顺序待用户决定。
- 独立 JPEG/PDF contract PR #153（https://github.com/KunoLu/640-skills/pull/153；tip `2084d71`；status open；另一 agent 提交，非本任务会话所开）。**当时快照**：上述 tip／open 及本段执行边界保留为历史；#153 后于 **2026-10-22 13:06:35 +08:00** squash-merged 为 `ce80ca2`。用户 2026-10-22 11:23 +08:00 授权，11:24 指定他人完成。范围：`CreateExportRequest.format` 加 `jpeg`／`pdf`；仅 createExport 预接受 422 `{detail: 'EXPORT_IMAGE_SIZE_LIMIT', max_edge_px, max_total_pixels}`；202 `meta.warnings` 精确 `EXPORT_SCALE_DOWNGRADED:1x`；golden tests。不含第 4 项磁盘上限错误码；后续项 C 的当时放置已由 10-22 15:00 决定取代，现归计划第 7 项／F 阶段的单独 PRD docs PR。合并后 main 以 merge（非 rebase）并入 R2.1b 才开放 HTTP；本轮不接线、不评论、不 merge。
- 配额决定仅登记在 plan，R2.2 才实现。
- 沿用 R2.1a 已记录的 TaskStore catalog/frontmatter 限制，不重跑已知失败、不改 active/ignore；本文件是用户明确要求的共享交付，不声称 helper lifecycle 或自动恢复成功。
- Round 4：#153 已合并为 `ce80ca2` 并经 `376ea0c` merge 纳入；前述 Round 1–3 的 open／HTTP 冻结描述是历史证据。本轮按用户缩小范围接线正常路径，两个尚未定义的失败协议仅登记于文末，不自行改映射。
- Round 5：遵循 Reviewy/Lord **2026-10-22 13:38 +08:00** 决定，contract [PR #154](https://github.com/KunoLu/640-skills/pull/154) 合并前所有失败作业对外 `error` 精确为 `"export failed"`，与 main R2.1a 一致。renderer code 仅写安全服务端 warning，不记录异常原文、stderr、traceback、路径或凭据；不改 createExport 422 或 202 warning。JPEG 不可用仍 500／无作业，PDF 仍 202 后失败，不提前决定不可用的错误协议。
- Round 6：contract [PR #154](https://github.com/KunoLu/640-skills/pull/154) 已合并为 `d46d4ad2097742e48441f8d094f29570131a5377`，经本轮真实 merge `8ac91c6a1853550a2c94f4e4d406d764514570f2` 纳入。**2026-10-22 13:38 +08:00 的固定 `"export failed"` 规则已被 #154 取代**，Round 5 描述仅为历史证据。请求校验后、pin／JPEG 预检／建作业前复用 capabilities 的可用性检查；不可用返回封闭 503，JPEG 不能预检时 503 优先于尺寸 422。受理后 renderer timeout → `EXPORT_RENDER_TIMEOUT`，其他失败 → `EXPORT_RENDER_FAILED`，所有格式适用；非失败状态 error=null。

## Book Gate Plan

| Gate | 触发事实与阶段 | 本轮结论／证据 |
|---|---|---|
| book-ddd-distilled-modeling | 未重开 grill，无领域规则变更 | not-needed；沿用已锁定 Query & Snapshot / Export / Renderer Isolation 所有权 |
| book-ddia-data-design | 跨进程渲染与持久导出，before-dev | confirmed；固定 HTML 输入，现有 ExportStore 原子发布／pin／恢复；无迁移或重放 |
| book-legacy-change-safety | 既有导出与服务高回归面，before-dev | characterized；before-dev-safety 35 tests，34 passed／1 Windows skip |
| book-refactoring-pass | 既有生产代码修改前 | proceed / normal；无需前置重构，保留过滤和 HTTP 校验；Python LSP 不可用，源码补充调用分析 |
| book-release-readiness | runtime 子进程与可选安装变化，check 后 | ready（仅本次 Linux 库级验收）；指定套件与真实 smoke 通过，两位 reviewer 有效发现关闭；HTTP 开放／跨平台实测／完整 AC-51 仍按授权归后续 |

测试 seam 为用户明确要求的 ExportStore、renderer 隔离／预检、capabilities 与真实 PDF/JPEG。主会话为唯一验证 controller。BDD 沿用 spec 中文正文＋英文关键词，不引入 Gherkin runner。Round 1 未提交场景已复用并修正 A 的状态。

Round 2 before-dev：Legacy Change Safety=`characterized`，`round2/preflight-red` 两项真实失败分别证明低于 1440px 的降级未拒绝、父进程配置／事前告警未生效；保留完整输出、错误码、隔离清理与四格式过滤回归。Refactoring=`proceed / normal`，无需前置重构。DDIA=`confirmed`：配置随现有 request 进入独立 worker；降级通知／确认只在临时 job 目录，通知返回前不截图，取消／超时／处理器异常均沿用清理和不发布语义；不改数据格式、恢复或 HTTP。Python LSP status／references 均实际不可用，使用源码调用点补充。Round 2 release gate 见本轮验证收口，不以 Run 1b 的 ready 替代。

上表与 Round 2 段落是既有轮次证据，不是 Round 3 门禁结果。

Round 3 before-dev：strict、分支与干净入口 `4476b3136e280077816518faa996a59e1ca4f329` 已核对。未完整调用 grill-with-docs：本轮接口、验收与冻结边界明确，无新领域歧义。Legacy Change Safety=`characterized`：`r3/contract-preflight-red` 实测旧 warning、无 public preflight、异常无 caps；`r3/footer-before` 原 PDF 页脚实测 6pt；operator 的零 kana 结果直接采纳，不重跑确认。安全网沿用尺寸／通知／隔离／HTTP 冻结测试，并扩展本轮 public preflight 回归。Refactoring=`proceed / normal`：无需前置重构；复用既有 worker／预算／信号量／清理。DDIA=`confirmed`：无新持久状态、无迁移；SnapshotStore／ExportStore 所有权不变，preflight 不创建导出作业。预检不预留资源；调用者负责 snapshot 生命周期，至受理保持 snapshot／presentation／配置固定，生成仍复检。Python LSP references 实际不可用，源码补充调用分析。沿用已知 TaskStore catalog/frontmatter 限制，不重试 helper、不声称自动恢复；本共享记录保存用户明确 strict 选择。

Round 4 before-dev：未完整调用 grill-with-docs，范围和合并 wire contract 明确。DDD=`not-needed`，无新领域歧义；Legacy Change Safety=`characterized`，`http/before-dev-safety` 11 passed，保留认证／CSRF／Host-Origin／幂等／快照到期／下载安全网；Refactoring=`proceed / normal`，无需前置重构；DDIA=`confirmed`：SnapshotStore 仍拥有快照，ExportStore 在现有 pin 生命周期内先执行 JPEG preparation，再建立作业。固定同一 HTML／metadata／presentation／caps／scale；拒绝释放 pin，不写作业／文件；幂等先查重，准备后在锁内再查重，避免并发重复作业。无迁移、第二队列或恢复语义变化。Python LSP references 实际不可用，采用源码调用分析。Release gate=`pending`，须完成本轮指定测试、真实 HTTP smoke 与独立 review。TaskStore 已知 catalog/frontmatter 限制不重试，不写 active/ignore，不声称 helper lifecycle 或自动恢复；本文件保存用户明确模式。主会话唯一验证 controller；子代理仅在各自文件责任范围写入，均不得执行测试／lint／formatter。

Round 5 Book Gate Plan／执行结论：未完整调用 grill-with-docs，用户 13:38 规则与边界明确，DDD=`not-needed`。Legacy Change Safety=`characterized`：用户报告与 worker 源码直接建立错误码泄漏事实；新 HTTP 红例 `failure-red` 记录无安全 warning 的 11 个失败子项，避免重复运行已知问题只为确认。Refactoring=`proceed / normal`：无需重构，移除 `_fail` 可变 error 参数，在现有边界固定错误并记录允许码；保留 422／202 warning、pin、取消与原子发布。DDIA=`confirmed`：ExportStore 仍是唯一作业／产物 owner，无新持久状态、重试或迁移；失败不写 manifest，幂等／恢复／保留期不变。Python LSP references 实际无 server，源码核对两个 `_fail` 调用及全部 error 写入。Release=`ready`（仅授权 Linux 本地修复），最终测试与真实 HTTP 证据见 Round 5 段；无部署／发布。TaskStore 既有 helper 限制不重试、不声称自动恢复。

Round 6 Book Gate Plan／before-dev：未完整调用 grill-with-docs，#154 与用户验收明确，DDD=`not-needed`。Legacy Change Safety=`characterized`：新增 `reports/r6/unavailable-red` 在现有 HTTP seam 证明新 503／零 pin 约束未满足；保留 422、202 warning、幂等、访问控制、取消、原子发布与安全日志回归。Refactoring=`proceed / normal`：无需重构，仅 admission 和既有失败边界。DDIA=`confirmed`：503 在 Store 外拒绝，预检竞态释放 pin，202 后仍由 ExportStore 唯一管理失败／清理；仅 ready manifest 持久化且 error=null；无迁移／重试／恢复策略变更。Python LSP references 实际无 server，源码／合并契约补充分析。Release=`ready`（仅本轮本地交付，详见 Round 6 验证与复核收口）；TaskStore 既有 catalog/frontmatter 限制不重试，不写 active/ignore、不声称 helper lifecycle 或自动恢复成功。主会话唯一 writer／验证 controller。

## 验证证据

Run 1 初始检查与 ignore 事实沿用当轮记录。Run 1b 首次只读核对：仅既有未提交 `sbtd-runtime/spec/r2.1b-renderer-scenarios.md`；分支正确，HEAD 为 `ceb202e`。步骤 (a) 未重做；只在指定 worktree 写入。

主会话唯一验证 controller；子代理均未执行测试、lint、formatter 或 build。原始输出 `.txt`、命令／时间／源 SHA `.json` 与同 stem 中文汇总 `.md` 全部保存在 **`/workspace/smoke-r2.1b/`**，不入仓。证据为 `developer-local / dirty / local-only`，不是 CI 或 PR-head 验证；提交后通过 `validated-source-hashes.json` 与 `final-tip.json` 记录代码内容等价绑定，不用旧 HEAD 冒充新代码已运行。

### 最终计划范围

| 命令 | 实际结果 | raw／中文汇总 stem |
|---|---|---|
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py' -v` | 341 tests；334 passed、7 skipped；57.318s | `runtime-final-full` |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. SBTD_RENDERER_TEST_HOME=/workspace/smoke-r2.1b/home /workspace/venv-r2.1b/bin/python -B -m unittest test_browser_renderer test_renderer_integration test_renderer_windows -v` | 39 tests；38 passed、1 Windows skip；22.330s | `renderer-final-full` |
| `python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_runtime_r1_acceptance -v` | 69 passed；0.566s | `contracts-final-full` |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_golden_contracts.OpenApiDraftTests -v` | 16 passed；0.062s | `openapi-final-full` |
| `ruff check --fix` 九个修改 Python 文件，随后 `ruff format --check` 同一范围 | 仅删除最后一个未使用测试 import；0 remaining；9 files already formatted。随后完整套件使用最终文件运行 | `ruff-final-clean`、`ruff-final-clean-format` |
| 独立 venv 安装 `requirements-renderer.txt`、`requirements-serve.txt`，`PLAYWRIGHT_BROWSERS_PATH=…/home/browsers python -m playwright install --only-shell chromium` | 成功；Playwright 1.64.0／shell 156.0.8078.4 revision 1248 | `renderer-pip-install`、`renderer-browser-install` |
| 真实 EventStore→load_dataset→SnapshotStore→ExportStore smoke，非 golden fixture | HTML／CSV／JPEG／PDF ready，下载 SHA-256 匹配 manifest；重新构造 Store 后摘要与到期时间不变 | `runtime-smoke-final`、`smoke-receipt.json` |
| `pdffonts report.pdf`、`pdftotext -layout report.pdf -`、`pdfinfo report.pdf`、`pdftoppm -f 1 -singlefile -png -r 60 report.pdf page-1` | 嵌入 NotoSansCJK 字体、中文／日本語／English 可搜索；A3 横向 12 页；已查看第 1 页 PNG | `pdffonts-final`、`pdftotext-final`、`pdfinfo-final`、`pdf-preview-final` |
| 同一报告注入受控 img／fetch／file 探针的私有 renderer seam smoke | HTTP img／fetch 均 route abort，监听服务 hits=[]；两作业 profile 新鲜、不同且删除；本地文件 canary 不在 PDF 文本 | `route-smoke-final`、`route-abort-log.json` |
| Chromium 原生 file 拒绝诊断 | console 明确 `Not allowed to load local resource`；file iframe 在路由前被拒绝，未伪称它进入 route-abort 列表 | `file-denial` |

系统 Python 的 7 skips：4 个显式未启用的真实浏览器场景＋3 个 Windows 场景；独立 venv 已实际运行前 4 项，剩余 Windows Job Object 原生测试跳过。套件间有重叠，不能把这些数量相加成独立用例数。未运行 Dashboard tests／build-consistency：`dashboard/` 未修改。未运行全仓 workflow 或已知无关 probe_links；指定范围没有未解决的无关失败。

### Smoke 产物与体积

- 最终快照：`snap_dd558322924d46e98f627efdf29f565a`。本轮真实追加 72 条带中日英可见 worktree 字段的新事件；throwaway home 保留上一轮 72 个任务，所以 dataset 含 144 个 task context 行、当前范围 72 个 event 行，未改既有查询语义。
- `/workspace/smoke-r2.1b/report.jpg`：5,971,450 bytes；完整 2880×25494 JPEG；SHA-256 `7a2eba9dc6da16a48ce69acc150d3f5a984493a6e39905fca7efb934b05d7ace`。
- `/workspace/smoke-r2.1b/report.pdf`：737,479 bytes；12 页、1191.12×842.88 pt；SHA-256 `d55afc95df6a5c83779088510de57ed2900ecff71a50466bf2e7ca7dd4034b9e`。
- 同目录 `report.html`、`report.csv`、`page-1.png`、字体／文本原生输出、`route-abort-log.json`、`file-denial.txt` 和 `smoke-receipt.json`。此前成功产物保留为 `before-review-*`。
- `du -sb …/home/browsers`：**290,381,668 bytes，约 277 MiB**；`du -sB1`：291,356,672 bytes。仅 only-shell＋FFmpeg 解压安装，不含 venv／字体。原生安装下载日志为 120 MiB＋2.2 MiB。
- 本机 `fonts-noto-cjk=1:20240730+repack1-1`，SC／JP 均由 fc-match 解析到 NotoSansCJK-Regular.ttc；没有本轮全局字体安装或字体入仓。

### 复核、红绿证据与 BDD

- RendererSecurityReview：最终 `Findings: []`，代码级关闭相对 home、父进程异常泄露、准备预算、信号量取消竞争及 Windows 后代清理发现；明确 Windows 原生证据仍待 R2.2。
- RendererOutputReview：最终 `correct`，confidence 0.85；两个 P3 证据建议已执行：真实 31,999 CSS px→1x 的 SOF 精确 1440×31999；32,001 px 安全失败；PDF 标题／范围／时区／短快照至少出现两次，区别正文与页脚。
- 保留失败原始报告：`renderer-store-tracer-red`（原库拒绝 jpeg）、`browser-unit-red`（新模块尚未实现）、`renderer-focused-first`（错误测试期望 55,555px 可通过，已修正）、`renderer-real-first`（file 路由日志假设错误）、`worker-crash-red`、`security-review-red`、`semaphore-cancellation-red`、`jpeg-width-preflight-red`。后四者对应生产修复及绿例均保留，不删除／覆盖失败证据。
- 实测宽内容探针曾输出 32002×1800，证明不能只把 viewport 1440 代入预检。已测量实际 scrollWidth／scrollHeight，1x 回退后重新测量，并在截图前复检；16001px 宽内容现在完整 1x。
- POSIX 以 `waitid(..., WNOWAIT)` 保留 worker PID 至进程组清理，避免 worker 先退出留下 Chromium，也避免回收 PID 后误杀复用的进程组。Windows 用 Job Object 显式 terminate→等待 ActiveProcesses=0→close，再删除 profile；不以创建进程组标志冒充树所有权。
- Ponytail Review：删除自写递归清理，使用 `shutil.rmtree`；删除冗余 viewport 重设、重复 source-reuse 测试、mock 回声断言、未授权的 32 MB HTML 限制和不可靠 sandbox 探测。保留实际资源所有权／安全校验 seam，不做无关重构。
- Code Readability Review：消费者仍只用 ExportRenderer／ExportStore；Windows 系统结构隔离在小型平台模块；行为断言集中在输出、边界与生命周期。lessons-record 已评估，因果与预防已落于 ADR／代码注释／持久回归，本轮不另建身份或 lesson 库。
- BDD：`traceable`；`sbtd-runtime/spec/r2.1b-renderer-scenarios.md`，中文正文＋英文 Gherkin 关键词；Cross-repo context=`complete`；API Contract=`verified`（冻结格式）；Mock Strategy=`user-approved`（缺依赖／故障／生命周期），真实浏览器与真实 runtime smoke 独立记录。

| 场景 | 持久测试／原生证据 |
|---|---|
| 缺依赖与 HTTP 冻结 | `CapabilityTests`、`FrozenHttpExportTests` |
| 四格式同一 withheld 集合／计数、派生行不变 | `RendererLibraryTests.test_four_formats_withhold_the_same_event_detail`；真实 PDF 文本 omission case |
| 无外联与新 profile | `IsolationTests`、`RealBrowserTests.test_route_abort_fresh_profiles_and_jpeg_2x`；route／file smoke |
| JPEG 长图／降级／超限 | `PreflightTests`、真实 31999／32001／16001-wide case、JPEG SOF／实际产物 |
| PDF 中日英／长表／重复表头／页脚 | `RealBrowserTests.test_pdf_is_searchable_a3_with_embedded_cjk`；pdffonts／pdftotext／page-1 |
| 取消／超时／崩溃清理 | `IsolationTests`；`WindowsJobTests`（本机 skip） |
| 既有存储生命周期复用 | `RendererLibraryTests` 的 pin／digest／restart／sweep cases；真实 Store 重启 smoke |

### Round 2：决定回填与剩余项收口

本轮入口 HEAD=`6caf067`，工作区干净、分支匹配，strict 沿用用户选择；round-1 六个提交均已存在，不重做已完成的安装、字体下载、隔离实现或四格式屏蔽测试。

修改范围（Round 2 历史）：`plan.md`／本 task 登记 A 决定、B 在 F、C 当时的 PRD docs PR 放置、独立 JPEG/PDF contract PR 和 merge-main 前置条件；C 的当时放置已由 10-22 15:00 决定取代，现归第 7 项／F 阶段，与 B 同阶段、另开单独 PRD docs PR。安装文档输出安全 bullet 恢复基线，仅「两格式→四格式」并追加消费同一过滤 HTML 的中性说明。spec／ADR 0004 去掉 A 决策归因，决定只在 plan/task；既有行为场景与同源过滤仍保留。

预检补齐：`MAX_SIDE_PX`／`MAX_PIXELS` 标为建议值、实测后冻结，并随作业传入 worker；2x→1x 要求完整内容、至少 1440 CSS px，重测后复检。截图前 worker 通知、父进程同步发出 `RuntimeWarning` 并重检取消／超时，再确认继续；manifest 保留同一 warning。处理器异常不确认，沿用进程清理／安全错误／不发布。没有改 `serve.py` 或任何 HTTP 错误映射。

本轮报告统一在 **`/workspace/smoke-r2.1b/round2/`**，每个 stem 保留 native `.txt`、中文九节 `.md` 与命令／时间／源码身份 `.json`。均为 `developer-local / dirty / local-only`，不是 CI 或 PR-head；最终提交用 `validated-source-hashes.json` 对照实际文件字节作等价绑定。

| 执行命令 | 结果 | 报告 stem |
|---|---|---|
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py' -v` | 344 tests：336 passed、8 skipped；60.480s | `runtime-final-full` |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. SBTD_RENDERER_TEST_HOME=/workspace/smoke-r2.1b/home /workspace/venv-r2.1b/bin/python -B -m unittest test_browser_renderer test_renderer_integration test_renderer_windows -v` | 42 tests：41 passed、1 Windows skip；28.564s | `renderer-final-full` |
| `python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_runtime_r1_acceptance -v` | 69 passed；0.548s | `contracts-final-full` |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest test_golden_contracts.OpenApiDraftTests -v` | 16 passed；0.060s | `openapi-final-full` |
| `ruff format`、`ruff check`、`ruff format --check`：browser_renderer.py、test_browser_renderer.py、test_renderer_integration.py | 三文件全部通过；最终完整回归在格式化后运行 | `round2-ruff-format` |
| `PYTHONPATH=sbtd-runtime:. /workspace/venv-r2.1b/bin/python -B /workspace/smoke-r2.1b/round2/smoke.py` | 真实追加 72 条中／日／英事件，经 EventStore→load_dataset→SnapshotStore→ExportStore；四格式 ready，摘要匹配；配置降级及超限失败均验证 | `round2-runtime-smoke-final` |
| `pdffonts`、`pdftotext -layout`、`pdftoppm -f 1 -singlefile -png -r 60`，输入 `round2/runtime-final/report.pdf` | CJK 嵌入、三语可搜索；12 页；已查看新生成 page-1.png | `round2-pdffonts`、`round2-pdftotext`、`round2-pdf-preview` |

系统套件 8 skips = 5 个需显式 browser home 的场景＋3 个 Windows 场景；venv 已执行前 5 项，Windows 原生证据仍归 R2.2。Dashboard 未修改，跳过其测试／构建；没有重装已验证依赖或运行无关全仓检查。rtk=`skipped-for-report`，native 保留真实输出。

Smoke 产物在 `round2/runtime-final/`：`report.html`、`report.csv`、`report.jpg`、`report.pdf`、`downgraded.jpg`、`page-1.png`、`smoke-receipt.json`。默认 JPEG **2880×25494**，降级 **1440×12744**；2x／1x 字体布局舍入会改变高度，不把两者高度恰好二分当作契约。固定高度真实回归另证完整 **1440×31999**、32001 安全失败及宽内容不截断。通知记录时 job=`generating`、artifact 不存在；最终 manifest 有 warning。1x 超限 job=`failed`、error=`EXPORT_IMAGE_SIZE_LIMIT`、无产物／manifest 且 download 拒绝。原 round-1 route-abort 日志与浏览器体积证据保留，不冒充本轮重新测量；本轮真实隔离回归已再执行。

失败记录保留：`preflight-red` 两个产品缺口；`preflight-green` 的 Host 测试误用 helper 会覆盖的 header（改用 `host` 参数后 `http-auth-green` 通过）；`round2-runtime-smoke` 的 throwaway 脚本误用异常名、`round2-runtime-smoke-green` 的不成立高度二分断言；`round2-ruff` 的 SIM117。脚本／断言修正后 smoke 与最终套件通过，无遗留产品失败。没有以降低预检标准修复 smoke。

持久回归保留四格式同一 snapshot 屏蔽集合／计数、HTML／CSV／JPEG/PDF 源与真实 PDF 文本 omission；新增 capabilities 无认证 401、非法 Host／Origin 403，既有 JPEG/PDF POST 400 与 `http_available=false` 测试通过。预检新增低于标准宽度拒绝、配置跨 worker 生效、实际 screenshot 入口前告警、拒绝通知无截图与清理、成功 1x 完整输出。AC-51 完整验收未在本轮执行或宣称通过。

独立安全复核 `RoundTwoSafetyReview`：`Findings: []`，覆盖通知顺序、配置传播、取消／超时／异常清理及 Store 发布边界；只读，未运行测试。其额外建议为给「通知处理器返回后取消／超时」补专门分支回归，非阻断发现；现有检查与生命周期回归保留。Ponytail Review：无新增公共 API、队列、依赖或第二存储路径，保留最小临时通知／确认以保证调用方在截图前收到告警，无可安全删除的控制步骤。Code Readability Review：生产逻辑限于单模块，预检与存储所有权未混合，测试在用户指定预检／HTTP／Store seam 验证行为。

独立范围复核 `RoundTwoScopeReview`：`correct`，当时的 A/B/C 放置、HTTP 冻结、AC-51 边界、模型回填、安装 safety bullet 基线逐字比对均通过（C 放置结论已由 10-22 15:00 决定取代，现归第 7 项／F）；唯一 P3 建议已采纳：CONTRACT-CHANGE-NEEDED 第 3 项改成待另行决策的信息项，不扩大 11:23 授权 PR 的范围。两位 reviewer 均只读，不充当验证 controller。

Round 2 Release Readiness=`ready`（仅用户授权的 Linux 库级交付，不代表 HTTP／跨平台／发布就绪）：指定完整套件与真实 Store smoke 通过；单作业信号量、总预算、取消、处理器异常清理与不发布语义保留；降级可提前观察且 manifest 留据。配置／代码回滚无需迁移，不删除原始事件或产物；未安装／卸载全局依赖。BDD=`traceable`（既有中文场景＋英文关键词，renderer／integration unittest），Cross-repo context=`complete`，API Contract=`verified`（冻结 html/csv），Mock Strategy=`user-approved`；实际浏览器／库 smoke 不混称 HTTP 四格式 E2E。Final Full Rerun=`passed`；原生/raw 与同 stem 中文汇总已校验章节／配对；跨平台与完整 AC-51 按用户计划仍归 R2.2。

### Round 3：AC-42 假名证据、页脚与契约库级对齐

证据根目录 **`/workspace/smoke-r2.1b/r3/`**；既有 venv `/workspace/venv-r2.1b`、browser home `/workspace/smoke-r2.1b/home`，未重装依赖／字体。本轮单独 `r3/home` 写入 72 条真实事件，经 EventStore → load_dataset → SnapshotStore → ExportStore，非 golden fixture。快照 `snap_562bef29d39a4d7cb44ee9f28b787d25`。原生 `.txt`、命令／时间／入口 SHA `.json` 与同 stem 中文 `.md` 保留；developer-local／dirty／local-only，不冒充 CI 或发布。

- 混合字段完整字符串：`中文验收：任务完成 日本語のテキスト・カタカナ検証 English mixed`。`pdftotext -layout report.pdf -` 中逐字找到；U+3040–U+30FF 计数 **720**，出现于 PDF 第 9／10／11 页。`pdftotext.txt`、`kana-evidence.json` 记录文本与计数；不再用 kanji-only 的 `日本語` 作为日文假名覆盖证据。
- `pdffonts.txt`：`NotoSansCJKsc-Regular`／Bold 和 `NotoSansCJKjp-Regular` 均嵌入（emb/sub/uni=yes）。SC CJK 字体也覆盖本次假名；不把 JP 字体存在单独解释为所有日文字形均选用 JP face。
- `report.jpg`：完整 **2880×25494**；`report.pdf`：A3 横向 **12 页**。`smoke-receipt.json` 保存 ready／SHA-256／manifest；下载摘要实际匹配。`downgraded.jpg` 的通知与 manifest 精确包含 `EXPORT_SCALE_DOWNGRADED:1x`。
- `pdftoppm -f 9 -singlefile -png -r 80 report.pdf page-kana` → `page-kana.png`；已查看，第 9 页完整显示假名字符串。第 1 页同命令 → `page-1.png`。Pillow 从 JPEG 原图 `(1260,19130,2630,19520)` 裁出 `jpeg-kana-crop.png`，2 倍放大为 `jpeg-kana-zoom.png`；已查看，中文／平假名／片假名／English 均可读。
- 页脚根因：`8px` 等效 **6pt**，`pdftohtml -xml -zoom 1` 对原 `report.pdf` 的 fontspec 12／13／14 均为 6（`footer-before.txt`）。仅将 footer template 改为 **9pt**；同命令对新 PDF 实测页脚字体均为 **9pt**（`footer-after.txt`），`footer-zoom.png` 已查看，标题／范围／短 snapshot／页码均保留，没有改正文 CSS。
- `kana-smoke` 原生执行证明 public preflight 在无 exports 目录时返回 JPEG 2x／PDF None；调整配置后返回 1x＋固定 warning；1x 超限直接抛异常，caps 实测 `(1439,30000000)`。没有受理／生成失败作业来冒充 pre-acceptance 结果。HTTP 仍未接线。

独立复核：`RoundThreeSafetyReview` Findings=`[]`，确认公共 preflight 与生成共用生命周期、无 capture／publication、有效 caps 跨进程回传、固定 warning 顺序及冻结 HTTP；`RoundThreeScopeReview`=`correct`（confidence 0.96），PR #153 映射／后续项 C（当时放置结论已由 10-22 15:00 决定取代，现归第 7 项／F）／模型回填／剩余缺口／kana／9pt 证据一致。两者只读，未运行验证；其静态生产／范围结论不冒充尚未完成的新增测试执行结果。Ponytail Review：复用 worker 与结果文件，无新增存储、缓存、队列或依赖，无需额外抽象。Code Readability Review：public preflight 的生命周期与生成集中在 `_run`，捕获前直接返回测量结果，IPC 只新增允许的数值 caps。

#### Round 3 最终验证与收口

| 命令／检查 | 实际结果 | `r3/` 报告 stem |
|---|---|---|
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. SBTD_RENDERER_TEST_HOME=/workspace/smoke-r2.1b/home /workspace/venv-r2.1b/bin/python -B -m unittest test_browser_renderer test_renderer_integration test_renderer_windows -v` | **44 tests：43 passed、1 Windows skip；35.327s** | `renderer-final-full` |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py' -v` | **346 tests：337 passed、9 skipped；59.944s** | `runtime-native-final-full` |
| 同系统 Python，`-m unittest test_facade_registration test_history_import -v` | 24 passed；2.469s | `native-environment-targeted` |
| renderer venv，`-m unittest test_browser_renderer.PreflightTests test_renderer_integration.RendererLibraryTests.test_preflight_measures_real_snapshot_without_capture -v` | 6 passed；6.099s | `preflight-targeted` |
| `ruff check`、`ruff format --check`：browser_renderer.py、test_browser_renderer.py、test_renderer_integration.py | 全部通过；3 files already formatted | `ruff-final`、`ruff-format-check` |
| venv `python -B /workspace/smoke-r2.1b/r3/smoke.py`＋pdftotext／pdffonts／pdftohtml／pdftoppm | 真实 Store ready、摘要匹配、exact string 72 次、kana 720、页脚 9pt；已查看 PNG | `kana-smoke`、`pdftotext`、`pdffonts`、`footer-after`、`pdf-preview-kana`、`pdf-preview-footer` |

失败证据保留而不覆盖：`contract-preflight-red` 是修改前的旧 warning／缺 preflight／缺 caps；`ruff-check` 为新增测试两处 SIM117，合并 with 后最终 lint 通过；`runtime-final-full` 是 **renderer venv 的失败尝试**（346 tests，3 failures、8 errors、3 skips，79.438s），该 venv 缺 workflow 所需 `markdown-it-py`，不是产品修复项。未安装新依赖，改用前两轮全量验证的系统 Python，先复跑 facade/history 24 项再跑完整 runtime 全量；最终通过以 `runtime-native-final-full` 为准。`renderer-focused-first` 是新增测试落地前的 42 tests 先行回归，不冒充最终 44 tests。

系统全量的 9 skips＝6 个需显式 browser home 的真实场景＋3 个 Windows 场景；6 个 browser 场景已由 venv 最终 renderer suite 执行通过。套件有重叠，不相加成独立测试数。未运行 Dashboard tests／build：无 Dashboard 修改。`ty` 当前不可用；未安装额外工具、不声称 typecheck 通过。本轮无需独立重跑全仓 workflow；全 runtime 已含 frozen OpenAPI golden tests，HTTP JPEG/PDF 拒绝与 capabilities 访问控制仍通过。

新增持久回归：精确 warning 字面量而非与同源常量自比；配置 caps 的直接异常及真实 worker 回传；public preflight 真实 SnapshotStore → HTML → Chromium 测量，normal／downgrade／oversize／PDF、报告原有 warning 保留，worker 禁止 screenshot／pdf，成功／失败都检查 profile/job 清理及 exports 不存在。删除测试写入的 snapshot/theme 源文本回声检查，不用 wiring 断言替代行为。真实混合文本 fixture 与 PDF 抽取断言均含 `中文日本語のテキスト・カタカナ English`。

Round 3 Release Readiness=`ready`（仅 Linux 库级交付）：最终计划范围通过、真实输出已查看；隔离／单作业背压／总预算／取消／错误清理沿用，preflight 无持久写路径，配置与代码回滚无数据迁移。BDD=`traceable`，`sbtd-runtime/spec/r2.1b-renderer-scenarios.md` 中文正文＋英文关键词；Cross-repo context=`complete`（本仓库面），API Contract=`verified`（已读取 origin/pr153 diff，但不改本分支冻结契约），Mock Strategy=`user-approved`（既有故障替身）；真实 Chromium／Store smoke 不混称 HTTP JPEG/PDF E2E。Final Full Rerun=`passed`；Final Test Report／Run Summary MD=`generated`，rtk=`skipped-for-report`。lessons-record 已评估：kana fixture 与 pt／px 根因的预防已落在持久场景、回归和本段原生证据，不重复创建长期 lesson／身份。HTTP 接线、Windows/macOS 实测与完整 AC-51 仍按原计划归后续。

`validated-source-hashes.json` 绑定最终实际跑过的生产／测试／场景／安装文档字节；`artifact-hashes.json` 绑定 PDF／JPEG／PNG；提交后由 `final-tip.json` 记录实际 tip 和相同字节核对，不把旧入口 SHA 当作新提交执行证明。Smoke 后生产文件仅 ruff 格式化，无行为改变；最终测试使用格式化后代码。报告仍为本地证据，不声明发布或自动恢复。

### Round 4：合并 #153 后 HTTP JPEG／PDF 接线

入口 `340d207a4d28024ab33773d1bca60ce83d99f2c8`；合并契约 `ce80ca2` 经 `376ea0c` merge 已在本分支。所有执行仅在授权 worktree，主会话唯一验证 controller；没有安装浏览器／字体／全局工具，复用已有 renderer venv 与 pinned only-shell Chromium，smoke 的独立 home 使用浏览器目录副本。

实现：`serve.py` 放行四格式，JPEG 由 threadpool 内的 `ExportStore.create(..., prepare=renderer.prepare)` 在 job 分配前预检；先 pin，失败 finally release。`ExportRenderer.prepare` 只生成一次过滤／脱敏静态 HTML，固化 HTML／metadata／presentation／caps／scale；`BrowserRenderer.preflight` 与生成共享隔离路径，生成使用 locked_scale 并复测，不能静默降级或截断。既有幂等先查重、准备后再查重；202 告警读取不引入 getExport 的到期／文件核验副作用。PDF 不做图像预检。get／download／delete 路由不改，JPEG／PDF MIME 沿用既有 Store。capabilities 的 http_available 随 renderer available。

#### 首次完整验证（独立 review 修正前，保留历史）

证据根目录 **`/workspace/smoke-r2.1b/http/`**。每个命令 stem 保留 raw `.txt`、命令／时间／完整入口 SHA `.json` 与同 stem 九节中文 `.md`。Evidence Source=`developer-local`、Source Revision=`dirty`、Evidence Publication=`local-only`；不是 CI／PR-head／部署证明。`validated-source-hashes.json` 与提交后 `final-tip.json` 作代码字节等价绑定，不以旧 HEAD 冒充新提交已运行。

| 命令／检查 | 实测结果 | 执行时间（+08:00） | 报告 stem |
|---|---|---|---|
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py' -v` | **365 tests：355 passed、10 skipped；99.487s** | 2026-10-22 13:42:16–13:43:56 | `runtime-final-full` |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. SBTD_RENDERER_TEST_HOME=/workspace/smoke-r2.1b/home /workspace/venv-r2.1b/bin/python -B -m unittest test_browser_renderer test_renderer_integration test_renderer_windows -v` | **61 tests：60 passed、1 Windows skip；86.881s** | 2026-10-22 13:43:56–13:45:23 | `renderer-final-full` |
| `python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_runtime_r1_acceptance -v` | **71 passed；0.653s** | 2026-10-22 13:45:23 | `contracts-final-full` |
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest sbtd-runtime/tests/test_golden_contracts.py -v` | **55 passed；0.296s** | 2026-10-22 13:45:23–13:45:24 | `golden-final-full` |
| `ruff check`／`ruff format --check`：serve.py、export_store.py、export_render.py、browser_renderer.py、test_exports_http.py、test_renderer_integration.py、test_browser_renderer.py | **全部通过；7 files already formatted** | 2026-10-22 13:45:24 | `ruff-final`、`ruff-format-final` |
| renderer venv 真实 `serve.main` HTTP smoke；72 条新事件经 EventStore 写入后 HTTP 查询快照／受理／轮询／下载 | **JPEG／PDF ready；422／降级均符合 schema；摘要与 MIME 正确** | 2026-10-22 13:41:40–13:42:00 | `real-http-smoke`、`transcript.json`、`smoke-receipt.json` |
| `pdffonts report.pdf`、`pdftotext -layout report.pdf -`、`pdfinfo report.pdf`、`pdftoppm -f 9 -singlefile -png -r 80 report.pdf page-kana` | CJK 字体嵌入；中／日／英可搜索，kana **720**；A3 横向 **12 页**；已查看 `page-kana.png` | 2026-10-22 13:42（完整精确时间在各 JSON） | `pdffonts`、`pdftotext`、`pdfinfo`、`pdf-preview` |
| `git diff 376ea0c -- sbtd-runtime/contracts/ docs/prd/ 'docs/adr/0001*' 'docs/adr/0002*' 'docs/adr/0003*'`；`git diff --check` | **输出为空，退出 0** | 2026-10-22 13:45 后记录 | 本轮终端结果 |

系统全量 10 skips＝7 个未启用 browser home 的真实场景＋3 个 Windows 场景；7 个真实浏览器场景均由 renderer venv 执行通过，含新增真实 HTTP JPEG／PDF。套件有重叠，不累加成独立用例数。Dashboard／移动端未改，未跑其构建或 UI E2E；真实 Chromium 通过项目 CLI 场景验证，不用 MCP 探索冒充回归。`ty` 未安装，未安装新工具、不声称 typecheck。rtk=`skipped-for-report`，原生 runner 写报告。

#### 真实 HTTP smoke 产物

- 新快照：`snap_4ae12df1fd774e2eafe12628ccd10a49`，非 fixture；同一快照与 presentation 用于四次 POST（正常 JPEG、PDF、降级 JPEG、超限 JPEG）。
- 正常 JPEG：`report.jpg`，**6,658,482 bytes，2880×25494**；SHA-256 `9bd5bdd0867aa7b5e3e4c56c7ba9cdc4f800f6511b35b9fef716c824beed657e`。
- PDF：`report.pdf`，**749,310 bytes，12 页**；SHA-256 `9cb1ddd38c19f69352cf0dff40ae4388d97fb7358e2105bd90e7b040be712c3f`；混合字符串含 `日本語のテキスト・カタカナ検証`，PNG 实际可读。
- 降级：仅 smoke 启动进程设置 `MAX_PIXELS=30000000`；202 `meta.warnings` 恰为 `["EXPORT_SCALE_DOWNGRADED:1x"]`，data 仅 export_id。`downgraded.jpg` **2,568,123 bytes，1440×12744**，manifest 保留相同告警；不是提交默认值更改。
- 超限：仅 smoke 进程设置 `MAX_SIDE_PX=1439`，422 body 恰为 `{"detail":"EXPORT_IMAGE_SIZE_LIMIT","max_edge_px":1439,"max_total_pixels":30000000}`；实际响应经合并 schema Draft202012Validator 校验，exports 目录前后文件集合相同。持久 HTTP 回归另证无 job 与无 pin。
- `transcript.json` 保存 **64 个请求**的 status、去凭据 headers、JSON body；下载二进制单独保存并记录摘要。配对响应凭据省略，Authorization／CSRF／pairing headers 不进入证据；客户端读 ticket 后移除临时文件。已程序核对无上述凭据头或配对 token body。服务已停止。

#### 红绿与本轮覆盖

保留 `before-dev-safety`（11 passed）、`http-tracer-red`（PDF 旧 400 对新 202 预期失败）、`http-pdf-tracer-green`。`http-renderer-focused` 首轮 23 tests 中 1 个测试断言失败：golden snapshot 自带 `UNKNOWN_OCCURRED_AT`，应与固定降级告警共存；未删除既有警告，修正测试为精确两项列表，`downgrade-targeted-green` 通过，最终全量通过。`ruff-first` 保留 3 个问题：SIM401、未使用测试 import、局部 import 排序；最小修正后最终 lint／format 通过。失败报告不覆盖或删除。

持久测试：实际 HTTP 202／400／404／410／422 对照合并 response set，202 与 422 用 Draft202012Validator 校验；精确有效 caps／key set／无 job/file/pin；降级固定比例、caps 改变不影响已预检作业、job-time 超限无输出；幂等重放不重复预检／告警保持；预检期间 health 可响应、pin 至完成才释放；可用／不可用 capabilities；正常 JPEG／PDF 真实浏览器下载；原有认证／CSRF／Host-Origin／非法请求覆盖保留。

Ponytail／Code Readability Review：复用既有 semaphore、worker、pin、原子发布和 manifest，无第二队列／存储／依赖；删除新增测试中的 closure 反射取 Store，改成显式注入真实 Store；合并重复 PDF failed／download 场景，移除 prepared HTML mock 回声／实例字符串检查。保留固定输入、比例、预算和消费者响应的行为回归；没有无关重构。独立 review 与 release gate 收口另见下文。

#### 独立 review 修正与最终计划范围

`RoundFourSafety` 首轮两项 P2 均确认并修复：① restored job 的告警在 `job.public` 中，受理响应原只读空 `job.metadata`，导致重启后幂等重放丢失降级告警；改从已恢复的 authoritative public manifest 读取。② preflight 位于 job 建立前，原 close 无法取消／等待；现在于锁内、pin 前登记正在准备的请求，Store 关闭触发取消，经 HTML／preflight／semaphore／worker 传播，finally 先 release pin 再唤醒 close。只是资源生命周期登记，不提前创建 Export job 或第二队列。`review-regression-red` 两项实测失败、`review-regression-green` 两项通过；`review-affected-subset` **39 tests，36 passed／3 skipped**。Safety 独立只读 closure=`Findings: []`，两项关闭，未运行任何验证命令。

以下才是 **Final Full Rerun**；使用上表相同的全部指定命令与七个 touched Python 文件，报告不覆盖首次结果：

| 命令范围 | 最终实测结果 | 开始 → 结束（2026-10-22，+08:00） | `http/` stem |
|---|---|---|---|
| runtime discover 全量 | **366 tests：356 passed、10 skipped；104.788s** | 13:52:36.563052 → 13:54:21.708113 | `runtime-reviewed-full` |
| renderer venv 三模块（含真实浏览器 HTTP） | **62 tests：61 passed、1 Windows skip；85.550s** | 13:54:21.711406 → 13:55:47.453495 | `renderer-reviewed-full` |
| R1 contracts＋acceptance | **71 passed；0.573s** | 13:55:47.455945 → 13:55:48.137140 | `contracts-reviewed-full` |
| golden 全量 | **55 passed；0.303s** | 13:55:48.138948 → 13:55:48.561186 | `golden-reviewed-full` |
| ruff check／format --check | **全部通过；7 files already formatted** | 13:55:48.563276 → 13:55:48.590812 | `ruff-reviewed`、`ruff-format-reviewed` |
| 真实 serve HTTP smoke（新 home／新事件／新快照，含重启后幂等重放） | **五场景通过**：正常 JPEG／PDF、降级、重启同 key 重放、422；schema／MIME／摘要正确 | 13:52:18.223207 → 13:52:36.560940 | `real-http-smoke-reviewed` |

最终 smoke 证据位于 **`/workspace/smoke-r2.1b/http/final/`**，快照 `snap_6fca7d9df7154c7f8deee69301d21683`；`transcript.json` **58 个去凭据请求记录**，`smoke-receipt.json` 与 `artifact-hashes.json` 留据。`report.jpg` **6,635,865 bytes，2880×25494**；`downgraded.jpg` **2,537,180 bytes，1440×12744**；`report.pdf` **749,473 bytes，A3 横向 12 页**。JPEG／PDF SHA-256 分别为 `cd47f42e53095dc900ceb5d0bcb8f5158f17f13c71d821a81bfc003caf7c149f`／`db53091aaf58b6ee29eb9f07c3eafb674ed68f95cd279004b15622ad3e133f7c`。同 key 跨重启、重新配对且 caps 降至会拒绝新作业的值后，仍返回原 export_id 与精确降级告警，无新预检；新 key 返回精确 422 caps `(1439,30000000)`，文件集合不变。

对最终 PDF 再执行 `pdffonts`／`pdftotext -layout`／`pdfinfo`／`pdftoppm -f 9 -singlefile -png -r 80`；raw 与中文汇总为 `http/pdffonts-reviewed`、`pdftotext-reviewed`、`pdfinfo-reviewed`、`pdf-preview-reviewed`。CJK 嵌入、混合字符串可搜索、kana **720**；已查看 `final/page-kana.png`。所有 smoke 服务已停止、临时 ticket 已消费移除；没有 session token／ticket 进入 transcript 或报告。首次产物和失败记录完整保留，最终代码以 reviewed 报告及文件哈希为准。

`RoundFourContractReview` 最终=`correct`（confidence 0.9），无 blocking／actionable correctness finding，确认四格式／202／422／caps／MIME／capabilities／两项 open gap 与实现一致，覆盖无必需遗漏。其唯一 P3 为过期清扫后的 warning 重放：沿用 R2.1a digest-only gone 记录，本进程同 key 返回旧 ID、GET／download 410，不重预检／生成，不额外保留 warning metadata。按用户明确正常路径范围，不扩展保留策略；spec 和 operator docs 将告警重放承诺限定保留期内。reviewer 已确认这是 documented-intentional 的现有 retention 边界并关闭，不是第三个 CONTRACT-CHANGE-NEEDED。两位 reviewer 均只读、未跑验证。

Round 4 Release Readiness=`ready`（**仅授权的 Linux HTTP 本地交付，不代表部署／发布**）：所需测试／真实 HTTP／字体文本与 PNG／保护路径检查通过；`protected-final` 实际 `git diff 376ea0c -- sbtd-runtime/contracts/ docs/prd/ 'docs/adr/0001*' 'docs/adr/0002*' 'docs/adr/0003*'` 为空。单作业背压、总预算、关闭取消、无部分产物和原子发布保留；两项用户排除的错误协议仍 open，跨平台／完整 AC-51 属 R2.2。无迁移、依赖安装或发布；回滚仅撤回代码，不删除用户数据。长久预防已落于生命周期／重放回归及本记录，不新增 developer 身份或独立 lesson 文件。临时 smoke 脚本验收后移除，raw／中文汇总／transcript／下载产物保留。

BDD=`traceable`（既有中文场景／英文关键词，无新 runner）；Cross-repo context=`complete`，API Contract=`verified`，Mock Strategy=`user-approved`（故障与边界 seam）；真实 HTTP smoke 为 `backend-only / none`，不混称 Dashboard UI E2E。Final Test Report／Run Summary MD=`generated`，Targeted Rerun／Affected Subset Rerun／Final Full Rerun=`passed`，rtk=`skipped-for-report`。原生/raw、JSON 与九节中文摘要已逐 stem 核对；提交前代码／测试哈希留据，提交后只作内容等价绑定，证据仍 developer-local／dirty／local-only。TaskStore 既有 helper 限制未绕过，无自动恢复承诺。

### Round 5：#154 合并前固定失败 error

入口 `09c4c6669f64e4580f0e12b55de7bd1b591a90d6`，strict；仅授权 worktree。证据根目录 **`/workspace/smoke-r2.1b/http/r5/`**；20 组原生 `.txt`、命令／真实 +08:00 时间／入口 SHA `.json` 与同 stem 九节中文 `.md` 已校验配对。全部为 `developer-local / dirty / local-only`，非 CI／PR-head。`validated-source-hashes.json` 绑定实际测试的代码／场景／operator 文档字节；提交后 `final-tip.json` 作内容等价核对，不拿入口 SHA 冒充新提交执行证明。

修改仅两个生产模块：`export_store.py` 的 `_fail` 无可变错误参数，所有失败固定 `"export failed"`；worker 的 warning 重新 allowlist code，普通异常统一 `RENDERER_FAILED`，不记录异常原文／stderr／traceback。取消或 Store 关闭时不把正常取消记作失败。`serve.py` 非尺寸 RendererError 保留原通用 500／无作业／释放 pin，但显式返回同一 `Internal Server Error` body，避免框架 traceback 泄漏源码路径。不改 422 分支或 202 warning。同步更新 integration 回归、已有中文 BDD 场景与 operator 文档两项过时错误描述；未改冻结文件。

| 最终命令／检查 | 实测结果 | `http/r5/` stem |
|---|---|---|
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py'` | **366 tests；356 passed、10 skipped；100.363s** | `runtime-reviewed-full` |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. SBTD_RENDERER_TEST_HOME=/workspace/smoke-r2.1b/home /workspace/venv-r2.1b/bin/python -B -m unittest test_browser_renderer test_renderer_integration test_renderer_windows` | **62 tests；61 passed、1 Windows skip；84.271s** | `renderer-reviewed-full` |
| `python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_runtime_r1_acceptance` | **71 passed；0.583s** | `contracts-reviewed` |
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest sbtd-runtime/tests/test_golden_contracts.py` | **55 passed；0.305s** | `golden-reviewed` |
| `ruff check`／`ruff format --check`：export_store.py、serve.py、test_renderer_integration.py | **全部通过；3 files already formatted** | `ruff-reviewed`、`ruff-format-reviewed` |
| 真实 `create_app`／uvicorn 子进程，JPEG 真实预检，process-only job timeout=0.000001s；JPEG／PDF POST 后轮询 GET | **两格式 202 → 200／failed／error 精确 export failed；两条安全 RENDERER_TIMEOUT warning；无 artifact／manifest** | `real-http-reviewed`、`final-http-transcript.json`、`final-jpeg-failed.json`、`final-pdf-failed.json`、`final-server-log.txt` |
| 实际 renderer 取消／delete throwaway 场景 | **cancelled、error=null、无失败 warning、无发布文件** | `cancellation-smoke` |
| review 后三项定点 HTTP 回归；此前 HTTP／Store 影响子集 | **3 passed／10.248s**；**34 tests，33 passed／1 skip，51.875s** | `review-targeted`、`affected-subset` |

新增 HTTP 矩阵覆盖 JPEG／PDF × unavailable、timeout、crash、job-time size limit、普通异常共十个作业子用例。每项检查 202／getExport 完整 body／409 不含任何 renderer code 或消息／私有路径，`error` 精确固定字符串、`assertLogs` 含安全码且无 exc_info／stack_info、不发布产物或 manifest。既有 HTML／CSV、缺依赖 PDF 与 JPEG job 的 code-in-error 断言全部转换。422 和 202 warning 原回归保留。真实 smoke 仅修改独立服务进程的预算，不提交 override；配对 ticket 经专用 pipe 只在内存传递，auth／CSRF 不入 transcript，不写 ticket 文件；服务器输出经凭据／路径／traceback 检查后保存，两轮服务均已停止。没有落盘临时脚本或新安装。

#### 四模块审计与独立复核

| 文件 | 已检查的全部相关出口 | 结论 |
|---|---|---|
| `export_store.py` | create／prepare、acceptance_warnings、`_run` invoke／publish catch／finally、`_fail`、cancel/delete/close、get/download、`_public_view`、`_accepted_metadata`、原子 publish／restore／`_read_ready` | 固定失败字段；日志只有安全码；失败不发布 manifest；成功 manifest error=null；没有将异常拼入 metadata/warnings |
| `serve.py` | create_export validation／400／404／410／422／generic 500、202 warnings、getExport envelope、download 409、capabilities、关闭路径 | 仅非尺寸预检去掉 traceback；JPEG 不可用仍 500、PDF 仍 202 后固定失败；未新增状态码／字段 |
| `export_render.py` | HTML／CSV metadata／warnings、ExportRenderer 调用分派、prepare 错误边界／固定 HTML 与 frozen metadata closure | 无异常文本进入 metadata；普通 preparation 异常转安全库码；无需修改 |
| `browser_renderer.py` | RendererError allowlist／capabilities、parent `_run`／timeout／cleanup、child `_capture`／worker error IPC、`_read_result`、stderr/stdout DEVNULL、`_published` 与 warning 来源 | 诊断码仅内部 IPC 后抛给边界；临时目录清理；aborted URLs 不发布；既有固定降级通知不变，无需修改 |

`FailurePrivacyReview`：Findings=`[]`；`FailureContractReview`：`correct`（0.85），唯一 P3 为取消时误记失败 warning，增加取消状态 guard 后独立复核关闭；测试命名与 operator 文档陈旧描述亦已关闭。两者仅只读，未执行测试／lint。主会话唯一验证 controller。Ponytail Review：无需新增 abstraction、logger framework、异常字段或第二存储路径；Code Readability Review：两个既有边界集中处理，保留最小状态判断，十场景共用现有 HTTP fixture，无死的 fail_job 模式。

失败证据 `failure-red` 保留（2 个测试／11 个失败子项均因没有安全 warning）；`failure-green` 两项通过。首次完整报告保留，review 后所有指定命令完整重跑，以 `*-reviewed*` 为最终结果。系统 10 skips＝7 个需 browser home 的真实场景＋3 个 Windows 场景；venv 已覆盖真实 browser 场景，1 个 Windows 原生 skip 保留。跨平台仍属 R2.2；UI 未改，不运行 Dashboard／移动端；无新依赖／全仓 workflow 检查，Python LSP 不可用，不声称 typecheck 或 CI。BDD=`traceable`（中文＋英文关键词），Cross-repo context=`complete`，API Contract=`verified`（#153 保持，#154 前规则 user-provided），Mock Strategy=`user-approved`；真实 HTTP 为 backend-only，不冒充 UI E2E。Final Test Report／Run Summary MD=`generated`，Final Full Rerun=`passed`，rtk=`skipped-for-report`。

Round 5 本地交付完成，当时整体任务仍 `in_progress`／`completed_at=null`，等待 operator 评审及契约后续；当时本地 run 没有 push、PR、评论、merge/rebase 或发布。回滚仅撤回代码，无迁移，不删除用户数据。长期预防已落实在固定错误／日志隐私回归，不另建 developer 身份或 lesson 文件；不改变既有 TaskStore 恢复限制。

### Round 6（operator run7）：#154 合并与失败状态接线

入口已有 `origin/main` merge，冲突恰为 #153 task 与 plan 两份文档。先按用户指定保留 HEAD 详细 reviewer／title／widget rows 与三条 plan bullets，追加 main closeout 和 export-failure-states bullet；仅暂存两份冲突文件，unmerged 列表为空后 `git commit --no-edit`。真实 merge=`8ac91c6a1853550a2c94f4e4d406d764514570f2`，parents=`0705e3888f1acccd4f730ce63a43aba31e9b5e32`／`d46d4ad2097742e48441f8d094f29570131a5377`。merge 后不修改 contracts 或 golden tests。

实现仅两个生产文件：`serve.py` 复用 `renderer_capability`，在 pin／预检／job 前拒绝不可用 JPEG／PDF，503 body 精确封闭；JPEG 预检期间依赖消失也拒绝并释放 pin。`export_store.py` 两处原 `"export failed"` 写入改为契约码；仅 allowlisted renderer timeout 映射超时，其余生成／发布／兜底失败均通用失败，取消仍 null。HTML／CSV 同样适用失败码，但不执行 renderer admission。依赖不可用的 createExport 503 优先于 JPEG 尺寸预检与 Store 幂等重放；已有 GET／download 不受该检查影响。

证据目录：**`ai/tasks/v2.1.0-rc.2-r2.1b-renderer/reports/r6/`**（已确认 ignored，不暂存）。每条命令保留 raw `.txt`、命令／真实 +08:00 时间／入口 SHA `.json` 与同 stem 九节中文 `.md`。Evidence Source=`developer-local`、Source Revision=`dirty`、Evidence Publication=`local-only`；`validated-source-hashes.json` 绑定最终被测字节，提交后再作内容等价核对，不能把 merge SHA 冒充新提交已运行。

| 最终命令／检查 | 实际结果 | 报告 stem |
|---|---|---|
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest discover -s sbtd-runtime/tests -p 'test_*.py'` | **370 tests：360 passed、10 skipped；106.689s** | `runtime-final-full` |
| `PYTHONPATH=sbtd-runtime:sbtd-runtime/tests:. SBTD_RENDERER_TEST_HOME=/workspace/smoke-r2.1b/home /workspace/venv-r2.1b/bin/python -B -m unittest test_browser_renderer test_renderer_integration test_renderer_windows` | **64 tests：63 passed、1 Windows skip；91.248s** | `renderer-final-full` |
| `python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_sbtd_runtime_r1_acceptance` | **73 passed；0.569s** | `contracts-final-full` |
| `PYTHONPATH=sbtd-runtime:. python3 -B -m unittest sbtd-runtime/tests/test_golden_contracts.py` | **57 passed；0.289s；golden 原样通过** | `golden-final-full` |
| `ruff check`／`ruff format --check`：serve.py、export_store.py、test_export_store.py、test_exports_http.py、test_renderer_integration.py | **全部通过；5 files already formatted** | `ruff-final`、`ruff-format-final` |
| 系统 Python throwaway Store smoke（`python3 -B -c …`，完整命令在 JSON） | **5 场景，无 mocks**：无浏览器时 HTML／CSV ready/null；库级接受 JPEG／PDF 后通用失败；真实 renderer budget 到期为超时；失败无 manifest | `store-smoke-corrected` |
| 503 定点、失败码定点、旧 HTTP 校验定点 | **3 passed／11.062s；2 passed／3.380s；1 passed／3.678s** | `unavailable-green`、`failure-codes-green`、`http-validation-targeted` |

新增／更新回归：JPEG／PDF 精确 503、与 capabilities 原因一致、无新文件／job／pin／manifest、503 优先于尺寸预检；HTML／CSV 缺依赖仍可生成；预检依赖消失释放 pin；四格式 × 五种失败（unavailable、timeout、crash、job-time size、generic）共 20 个 HTTP 子项验证固定码／安全日志／409／无产物。HTTP 实际 getExport 数据用合并 ExportJob schema 验证；阻塞真实 Store worker 固定观察 queued／generating／cancelled／ready，全部 error=null；ready manifest 及重启恢复保持 null。Store 普通失败保留 path-not-leaked 断言，并覆盖发布失败通用码。全测试目录剩余 `"export failed"` 仅为未修改 golden 的反例。

失败证据保留：`unavailable-red`（1 test，3 failure 子项）与 `failure-codes-red`（2 tests，11 failure 子项）是契约红例；`affected-subset`（54 tests，1 failure、3 skips）发现旧 `test_exports_http` 仍断言无依赖 PDF202，删除该重复旧断言后定点及完整 runtime 通过；`ruff-format-check` 的两处格式问题经 formatter 修正；`store-smoke` 首轮因 throwaway fixture 调用缺 metrics 参数失败，修正后无替身 5 场景通过，不改生产代码来迎合 smoke。

BDD=`traceable`：沿用 `sbtd-runtime/spec/r2.1b-renderer-scenarios.md` 中文正文＋英文关键词，Cross-repo context=`complete`，API Contract=`verified`（#154），Mock Strategy=`user-approved / contract-backed`（可控故障）；无替身 Store smoke 与 suite 内真实 Chromium／HTTP 分开记录。系统 10 skips 沿用未启用 browser home／Windows 条件，venv 仅剩 1 Windows 原生 skip；套件重叠，不相加成独立用例数。用户明确 operator 另跑真实 HTTP smoke，本轮未另建该 smoke；无 UI 修改，不跑 Dashboard／移动端，未安装任何依赖。rtk=`skipped-for-report`，Final Full Rerun=`passed`。

Ponytail／Code Readability Review：复用现有 admission、failure、schema helper 与生命周期 fixture；无新增运行时 abstraction／持久格式／队列／依赖。用布尔 timeout 选择两个允许的公开码，不引入任意 error 透传。删除重复旧 PDF202 测试，不复制第二份 503 用例。无新长期 lesson／身份文件，错误调用的修正与预防保留在本轮 evidence。

独立 `RoundSixSafetyReview`：Findings=`[]`；静态检查 pin／取消／关闭、生成失败／finally、原子发布／恢复、503／422／安全 500 与日志边界，无本轮引入的泄漏或生命周期问题。只读、未运行测试／lint，runtime 自报实际模型 `openai-codex/gpt-6-astra`。主会话最终 scope 检查仅 8 个允许文件变化，`git diff --check` 通过；相对 merge 的 contracts／golden／PRD／ADR 0001–0003 diff 为空，Panel／CSV schema 不在修改列表。

独立 `RoundSixContractReview`：`correct`（confidence 0.9），无 P0–P2 缺陷；确认闭合 503、四格式失败码、状态 schema／null、503 优先级、422／warning 与测试替换符合 #154。runtime 自报 `kimi-code/k3`，只读、未运行验证。两条非阻断观察：serve 可改用已有不可用常量替代字面量；依赖不可用时重放的 503 优先级与已有产物仍可 GET／download 可增加专门测试。实现与文档已明确该边界，不扩展本轮范围。

Round 6 Release Readiness=`ready`（仅授权 Linux 本地交付）：指定完整套件、5 场景无替身 Store smoke、两位独立复核通过；单 worker／背压、总预算、取消／pin／原子发布保持，安全日志与 operator 指引已更新。无数据迁移／安装／部署；回滚撤回实现提交，不删除 audit.db、snapshots、exports 或浏览器资源。Windows／macOS、用户安排的 operator 真实 HTTP smoke 与发布不冒充完成。17 组 raw／JSON／九节中文汇总已检查章节顺序与配对，失败记录保留；Final Test Report／Run Summary MD=`generated`，Final Full Rerun=`passed`。不存在本轮未关闭的阻断发现。




## 模型使用

| 轮次／用途 | 请求模型 | 实际模型 | assistant messages | 工具调用次数 |
|---|---|---|---|---|
| Run 1 主会话：计划首提交、只读设计；session 01a16197-919f-7482-b4ca-4d8cef45a0e5 | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra | 15 | 52 |
| Run 1 BrowserRenderer：只读研究，无写入 | agent `task` → `@task` 角色 xai-oauth/grok-4.7 | xai-oauth/grok-4.7（session_init resolvedModel `xai-oauth/grok-4.7:xhigh`） | 7 | 18 |
| Run 1 RendererIntegrationTests：只读研究，无写入 | agent `task` → `@task` 角色 xai-oauth/grok-4.7 | xai-oauth/grok-4.7（session_init resolvedModel `xai-oauth/grok-4.7:xhigh`） | 5 | 16 |
| Run 1b 主会话：实现、验证、交付；session 01a161a4-776d-75bb-aef2-39a6e00bc50f | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra | 130 | 218 |
| Run 1b BrowserImplementation：renderer 实现 | agent `task` → `@task` 角色 xai-oauth/grok-4.7 | xai-oauth/grok-4.7（session_init resolvedModel `xai-oauth/grok-4.7:xhigh`） | 64 | 124 |
| Run 1b RendererIntegration：库／HTTP／过滤一致性实现 | agent `task` → `@task` 角色 xai-oauth/grok-4.7 | xai-oauth/grok-4.7（session_init resolvedModel `xai-oauth/grok-4.7:xhigh`） | 63 | 139 |
| Run 1b RendererSecurityReview：安全复核 | agent `security-reviewer`（未钉 model；main spawn effort:"hi" → thinking max） | openai-codex/gpt-6-astra（session_init resolvedModel `openai-codex/gpt-6-astra:max`） | 28 | 82 |
| Run 1b RendererOutputReview：输出／集成复核 | agent `reviewer`（内置 `model: "@slow"`）→ slow 角色 kimi-code/k3:max | kimi-code/k3（session_init resolvedModel `kimi-code/k3:max`） | 62 | 78 |
| Round 2 主会话：决定回填、范围修正、预检通知与验证；session 01a161d9-7264-725e-9d47-caeaf21ccfd9 | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra | 51 | 112 |
| Round 2 RoundTwoSafetyReview：独立只读安全复核 | agent `security-reviewer`（未钉 model；main spawn effort:"hi" → thinking max） | openai-codex/gpt-6-astra（session_init resolvedModel `openai-codex/gpt-6-astra:max`） | 12 | 40 |
| Round 2 RoundTwoScopeReview：独立只读范围／输出复核 | agent `reviewer`（内置 `model: "@slow"`）→ slow 角色 kimi-code/k3:max | kimi-code/k3（session_init resolvedModel `kimi-code/k3:high`） | 42 | 47 |
| Round 3 主会话；session 01a161ea-1974-77c4-9051-f6209e7b6283 | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra | 55 | 104 |
| Round 3 RoundThreeDocs：plan／task 文档更新 | agent `task` → `@task` 角色 xai-oauth/grok-4.7 | xai-oauth/grok-4.7（session_init resolvedModel `xai-oauth/grok-4.7:medium`） | 12 | 25 |
| Round 3 RoundThreeTests：预检／caps／kana 回归实现 | agent `task` → `@task` 角色 xai-oauth/grok-4.7 | xai-oauth/grok-4.7（session_init resolvedModel `xai-oauth/grok-4.7:xhigh`） | 41 | 79 |
| Round 3 RoundThreeSafetyReview：独立只读安全复核 | agent `security-reviewer`（未钉 model；main spawn effort:"hi" → thinking max） | openai-codex/gpt-6-astra（session_init resolvedModel `openai-codex/gpt-6-astra:max`） | 15 | 55 |
| Round 3 RoundThreeScopeReview：独立只读范围／输出复核 | agent `reviewer`（内置 `model: "@slow"`，configured primary kimi-code/k3:max；spawn effort:"med"） | kimi-code/k3（thinking_level_change `high`；session_init resolvedModel `kimi-code/k3:high`；resolvedModelIsFallback=false） | 17 | 35 |
| Session title generation（Run 1，omp log pid 23357） | omp `tiny`／title-generator | cursor/composer-2.5 | 4 requests | 0 |
| Session title generation（Run 1b，pid 36250） | omp title-generator | cursor/composer-2.5 | 6 requests | 0 |
| Session title generation（Round 2，pid 120521） | omp title-generator | cursor/composer-2.5 ×4；kimi-code/k3-256k ×1 | 5 requests | 0 |
| Session title generation（Round 3，pid 149475） | omp title-generator | cursor/composer-2.5 ×6；kimi-code/k3-256k ×1 | 7 requests | 0 |
| Round 4 主会话：HTTP 接线与本地验证；session 01a16205-0866-7749-8956-0c353f38b14b | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra（thinking_level_change `high`） | 105 | 172 |
| Round 4 PreparedRenderer：renderer／store 预检冻结实现 | agent `task` → `@task` 角色 xai-oauth/grok-4.7 | xai-oauth/grok-4.7（session_init `xai-oauth/grok-4.7:xhigh`） | 57 | 99 |
| Round 4 HttpRendererTests：HTTP 测试实现 | agent `task` → `@task` 角色 xai-oauth/grok-4.7 | xai-oauth/grok-4.7（session_init `xai-oauth/grok-4.7:xhigh`） | 52 | 99 |
| Round 4 RoundFourSafety：安全复核 | agent `security-reviewer`（未钉 model；main spawn effort:"hi" → thinking max） | openai-codex/gpt-6-astra（session_init `openai-codex/gpt-6-astra:max`） | 20 | 51 |
| Round 4 RoundFourContractReview：契约复核 | agent `reviewer`（内置 `model: "@slow"`）→ slow 角色 kimi-code/k3:max | kimi-code/k3（session_init `kimi-code/k3:max`） | 68 | 76 |
| Session title generation（Round 4，pid 190550） | omp title-generator | cursor/composer-2.5 ×6；kimi-code/k3-256k ×2 | 8 requests | 0 |
| Round 5 主会话：固定失败 error、审计、验证与记录；session 01a16238-6c99-74da-873a-30f8569cfa47 | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra（thinking_level_change `high`） | 29 | 85 |
| Round 5 FailurePrivacyReview：只读隐私审计 | agent `security-reviewer`（未钉 model；main spawn effort:"hi" → thinking max） | openai-codex/gpt-6-astra（session_init `openai-codex/gpt-6-astra:max`） | 11 | 33 |
| Round 5 FailureContractReview：只读契约／覆盖复核 | agent `reviewer`（内置 `model: "@slow"`）→ slow 角色 kimi-code/k3:max | kimi-code/k3（session_init `kimi-code/k3:high`） | 33 | 40 |
| Session title generation（Round 5，pid 269214） | omp title-generator | cursor/composer-2.5 ×4；kimi-code/k3-256k ×1 | 5 requests | 0 |
| Round 6（operator run7）主会话：merge、#154 接线、验证与记录；session 01a16253-37ca-7535-b26a-cc86989790e0 | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra（thinking `high`；resolvedModelIsFallback=false） | 51 | 93 |
| Round 6 follow-up resume run7b：Reviewy notes | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra（thinking `high`） | 12 | 33 |
| Round 6 follow-up resume run7c：follow-up C placement | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra（thinking `high`） | 8 | 17 |
| Round 6 RoundSixContractReview：只读契约／覆盖复核 | agent `reviewer`（@slow，configured primary kimi-code/k3:max；spawn effort:"med"） | kimi-code/k3（session_init `kimi-code/k3:high`；resolvedModelIsFallback=false） | 28 | 33 |
| Round 6 RoundSixSafetyReview：只读生命周期／隐私复核 | agent `security-reviewer`（未覆盖 model；main spawn effort:"hi" → thinking max） | openai-codex/gpt-6-astra（session_init `openai-codex/gpt-6-astra:max`；resolvedModelIsFallback=false） | 11 | 41 |
| Session title generation（Round 6：run7 ×4，含 2 subagents；run7b ×1；run7c ×1） | omp title-generator | cursor/composer-2.5 ×6（全部成功） | 6 requests | 0 |
| Round 6 follow-up resume run7d：plan.md:63 + count backfill；无子代理 | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra（thinking `high`） | 6 | 12 |
| Session title generation（Round 6 resume run7d） | omp title-generator | cursor/composer-2.5 ×1 | 1 request | 0 |
| Round 7 doc-fix resume run8（最终；无子代理） | openai-codex/gpt-6-astra:high | openai-codex/gpt-6-astra（thinking `high`） | 9 | 24 |
| Session title generation（Round 7 resume run8） | omp title-generator | cursor/composer-2.5 ×1（成功） | 1 request | 0 |

子代理 agent 名称取自 `~/.omp/logs/omp.2026-10-22.*.log` 的 `subagent launch timing` 记录（`agent` 字段）及各子代理 jsonl 的 `session_init.agent`；`session_init.resolvedModel` 记录了派出时的实际模型与 thinking level（reviewer 在 Run 1b 为 `kimi-code/k3:max`，Round 2／3 为 `kimi-code/k3:high`；原因见下述 effort 解释）；`model_change` 记录不含 thinking level（仅 `kimi-code/k3`、`xai-oauth/grok-4.7`、`openai-codex/gpt-6-astra`）。主会话 jsonl 无 session_init，thinking 以命令行 `:high` 为准。operator 2026-10-22 13:15 +08:00 回填，Round 6 按用户提供的 spawn 事实补充原因。

同为 reviewer agent（@slow = kimi-code/k3）；thinking 随 main 每次 spawn 传的 effort 变化：Run 1b RendererOutputReview 与 Round 4 RoundFourContractReview 传 effort:"hi" → kimi-code/k3 thinking max；Round 2 RoundTwoScopeReview、Round 3 RoundThreeScopeReview、Round 5 FailureContractReview 与 Round 6 RoundSixContractReview 均传 effort:"med" → kimi-code/k3 thinking high。Round 3 的 effort 由 operator 核对父 session `2026-10-22T04-41-34-324Z_01a161ea-1974-77c4-9051-f6209e7b6283.jsonl` 的 task spawn，子 `RoundThreeScopeReview.jsonl` 的 thinking_level_change=`high`、session_init resolvedModel=`kimi-code/k3:high`、resolvedModelIsFallback=false。由 omp main 自行选择 effort，非配置或角色差异。

Security-reviewer thinking 亦随 main 每次 spawn 的 effort，而非沿用主会话 thinking：以下六次父会话 `task` 调用均明确传 `effort:"hi"`、未传 `model` override；子会话 `thinking_level_change` 均为 `max`，`session_init.resolvedModel` 均为 `openai-codex/gpt-6-astra:max`。父会话各自第 4 行的 `thinking_level_change` 均为 `high`，不能把子会话 max 写成「继承主会话」。本次只读核对的证据根为 `~/.omp/agent/sessions/--workspace-640-skills-r2.1b--/`：

| 轮次／security reviewer | 父 session 文件 stem（`.jsonl` 的 spawn 行） | spawn effort | 子 session 文件（在同 stem 目录内） | resolved thinking 证据 |
|---|---|---|---|---|
| Run 1b RendererSecurityReview | `2026-10-22T03-25-30-861Z_01a161a4-776d-75bb-aef2-39a6e00bc50f`：272 | `hi` | `RendererSecurityReview.jsonl` | 第 4 行 thinking=`max`；第 6 行 resolvedModel=`openai-codex/gpt-6-astra:max` |
| Round 2 RoundTwoSafetyReview | `2026-10-22T04-23-22-980Z_01a161d9-7264-725e-9d47-caeaf21ccfd9`：157 | `hi` | `RoundTwoSafetyReview.jsonl` | 第 4 行 thinking=`max`；第 6 行 resolvedModel=`openai-codex/gpt-6-astra:max` |
| Round 3 RoundThreeSafetyReview | `2026-10-22T04-41-34-324Z_01a161ea-1974-77c4-9051-f6209e7b6283`：155 | `hi` | `RoundThreeSafetyReview.jsonl` | 第 4 行 thinking=`max`；第 6 行 resolvedModel=`openai-codex/gpt-6-astra:max` |
| Round 4 RoundFourSafety | `2026-10-22T05-10-59-430Z_01a16205-0866-7749-8956-0c353f38b14b`：281 | `hi` | `RoundFourSafety.jsonl` | 第 4 行 thinking=`max`；第 6 行 resolvedModel=`openai-codex/gpt-6-astra:max` |
| Round 5 FailurePrivacyReview | `2026-10-22T06-07-07-417Z_01a16238-6c99-74da-873a-30f8569cfa47`：109 | `hi` | `FailurePrivacyReview.jsonl` | 第 4 行 thinking=`max`；第 6 行 resolvedModel=`openai-codex/gpt-6-astra:max` |
| Round 6 RoundSixSafetyReview | `2026-10-22T06-36-23-370Z_01a16253-37ca-7535-b26a-cc86989790e0`：171 | `hi` | `RoundSixSafetyReview.jsonl` | 第 4 行 thinking=`max`；第 6 行 resolvedModel=`openai-codex/gpt-6-astra:max` |

Round 6 模型与计数按用户提供的 operator 核验结果回填，来源为 session `01a16253-37ca-7535-b26a-cc86989790e0` 的 jsonl；计数为 assistant messages／toolCall blocks。run7、run7b、run7c、run7d 分别为 51／93、12／33、8／17、6／12；run7d 主模型 openai-codex/gpt-6-astra:high、thinking high，无子代理，标题生成 `cursor/composer-2.5` ×1。两位子代理分别为 ContractReview 28／33、SafetyReview 11／41。run7 至 run7c 的 title generation 共 6 次，均为 `cursor/composer-2.5` 且全部成功；加上 run7d 的 1 次，Round 6 合计 7 次。Round 6 logs 无 job widget。

Round 7 run8 最终计数：只读解析 `/home/box/.omp/agent/sessions/--workspace-640-skills-r2.1b--/2026-10-22T06-36-23-370Z_01a16253-37ca-7535-b26a-cc86989790e0.jsonl` 第 411–471 行（run8 用户消息起至 session_exit），统计 role=assistant 的 message 记录与其中 type=toolCall 的 blocks，分别为 9／24；含计数回填、提交与最终报告，全部为 `openai-codex/gpt-6-astra`。无子代理；标题生成 `cursor/composer-2.5` ×1，来源 `~/.omp/logs/omp.2026-10-22.355356.log` 的 `title-generator: request` ×1 及对应 success。

Run 1／1b 模型与计数由 operator 于 2026-10-22 从 session jsonl 核实；计数为 assistant messages／toolCall blocks，全部 `resolvedModelIsFallback: false`，无 advisor。Run 1 两子代理只读，operator 于 11:17 +08:00 停止该轮。Round 2 主会话、SafetyReview、ScopeReview 的计数亦由 operator 从 jsonl 核实，全部 `resolvedModelIsFallback: false`，无 advisor。Round 3 主会话与四个子代理计数亦由 operator 于 2026-10-22 从 session jsonl 核实，全部 `resolvedModelIsFallback: false`，无 advisor。Session title generation 计数来自 `~/.omp/logs/omp.2026-10-22.<pid>.log` 的 `title-generator: request` 记录（含子代理会话标题）；R2.1b 各轮无 job-widget 记录。Round 4／5 计数由 operator 于 2026-10-22 14:35 +08:00 从 session jsonl 核实（assistant messages／toolCall blocks），全部 `resolvedModelIsFallback: false`，无 advisor；主会话 thinking 取自 `thinking_level_change`。

Round 2 两位 reviewer 均从各自运行环境确认实际模型；ScopeReview 已只读复核第 3 项修正并确认 P3 关闭，无进一步发现。其回执晚于首次 docs commit 返回，因此仅将该回执与实际模型并入同一未发布的本轮 docs commit；不改 round-1 历史。

## 提交与交付边界

1. `ceb202e` — `docs(plan): backfill R2.1a and record 10-21 plan`（Run 1 已完成；本轮不重做）。
2. `4c46b85` — `docs(adr): define isolated library renderer decisions`。
3. `ca9478a` — `feat(runtime): add isolated JPEG and PDF library renderer`（含复用的场景文件）。
4. `1987db4` — `test(runtime): cover renderer isolation and four-format consistency`。
5. `30b7518` — `docs(runtime): document pinned optional renderer installation`。
6. `6caf067` — `docs(task): record R2.1b acceptance evidence and contract gaps`（Run 1b）。
7. `12afbb4` — `fix(runtime): notify JPEG downgrade before capture`（Round 2 预检、测试与 renderer 文档）。
8. Round 2 决定回填采用用户指定 `docs(r2.1b): record follow-up A decision (keep #151 exportable behavior)`。最终 tip 与源码内容绑定记录在 `/workspace/smoke-r2.1b/round2/final-tip.json` 及 stdout，避免本文件自引用自身哈希。
9. `aea5cd6` — `feat(runtime): align renderer preflight with export contract`（Round 3：库级 preflight／固定 warning／有效 caps、kana 回归、9pt 页脚、场景与使用文档）。
10. Round 3 文档收口：`docs(task): record R2.1b AC-42 kana smoke`（本 task、plan 的 #153 登记与模型回填）；实际最终 tip 记录在 `/workspace/smoke-r2.1b/r3/final-tip.json` 及交付输出，避免自身哈希循环。
11. `79b5654` — `feat(serve): open HTTP jpeg/pdf exports per #153 contract`（Round 4：serve／Store／固定输入 renderer，含 review 两项生命周期修复）。
12. `bff1484` — `test(serve): cover jpeg/pdf 202, 422 and downgrade warning`（三份测试与既有 renderer 场景）。
13. `a0e97e4` — `docs(runtime): document HTTP jpeg/pdf exports`（仅 renderer 相关 operator 文档）。
14. Round 4 记录收口：`docs(task): record R2.1b HTTP wiring evidence`（本 task 与 plan；最终 tip 在 `http/final-tip.json` 与 stdout，避免自身哈希循环）。
15. Round 5 修复提交：`fix(runtime): keep fixed export failure error until #154`；两个生产文件、integration 回归、既有 BDD 场景与 operator 文档。
16. Round 5 记录提交：`docs(task): record R2.1b fixed failure error rule`；实际提交与最终 tip 在 `http/r5/final-tip.json` 及最终交付，避免自身哈希循环。
17. `8ac91c6a1853550a2c94f4e4d406d764514570f2` — Round 6 真实 merge：纳入 main 的 #154；仅手工解决两份指定 docs 冲突，不 rebase。
18. `18de842a5f4ece38808054ae791c5bd491f323d6` — `feat(runtime): wire #154 renderer-unavailable 503 and failure codes`；两个生产模块、三份测试、renderer spec 与安装使用文档，共 7 文件。
19. Round 6 记录提交：`docs(task): record R2.1b #154 wiring and reviewer effort`；仅本 task。最终 SHA／tip 与被测文件内容等价绑定见 ignored `reports/r6/final-tip.json` 及最终交付，不自引用本提交哈希。

主要修改：新增 `browser_renderer.py`、`renderer_windows.py`；扩展 `export_render.py`、`export_store.py`、`serve.py`；新增三个 renderer 测试文件并删除旧 pdf 拒绝断言；复用场景、ADR 0004、安装文档、两份依赖清单；更新本 task 与 plan 的后续项 A 决定。

当时已执行 `git diff 8931c35 -- sbtd-runtime/contracts/ docs/prd/ 'docs/adr/0001*' 'docs/adr/0002*' 'docs/adr/0003*'`，输出为空。CSV schema／Panel manifest 未改。仅显式路径 git add；不暂存／提交禁止路径；当时本地 run 未 push、未开 PR、未评论 GitHub、未 merge，未触及主 checkout。

Round 3 提交前已核对仅上述 7 个允许文件变化、index 初始为空；相对入口 `4476b3136e280077816518faa996a59e1ca4f329` 的 contracts／serve.py／PRD／ADR 0001–0003 diff 为空，`git diff --check` 通过。本轮仅显式 `git add <path>`，无禁止路径入 index。

Round 4 仅上述 **11 个允许文件**变化，提交前 index 为空；四个提交均使用显式路径 `git add`，不包含 `.omp-r12b-addendum.txt`／`ai/tasks/codex-verify/`，不含 OpenAPI／Panel manifest／CSV schema／PRD／ADR 0001–0003／#153 task。未 push、未开 PR、未评论、未 merge/rebase、未操作其他 worktree。

Round 6 当时 `status` 保持 **in_progress**，`completed_at=null`：已完成 #154 本地接线与指定测试，整体仍待 operator 真实 HTTP smoke／提审／合并。现 operator 已 push／开 PR #155 并 squash-merge，本任务记 done（见 closeout 状态事件）；R2.2 跨平台／完整 AC-51 和发布不冒充完成。原生/raw 与同 stem 中文汇总已生成，Final Full Rerun=`passed`（条件 skip 如上），rtk=`skipped-for-report`；工具诊断不是 CI。

恢复／回滚：无数据迁移；撤回代码不删除 audit.db、snapshots、exports 或浏览器下载文件。在途作业不跨重启恢复；浏览器依赖不自动安装／下载；配额仍待 R2.2。应用级隔离显式 `chromium_sandbox=False`，不承诺 OS sandbox 或抵御浏览器漏洞。TaskStore 历史限制未绕过，不声称自动恢复成功。

## CONTRACT-CHANGE-NEEDED

格式、受理前尺寸限制与 202 降级通知已由 [PR #153](https://github.com/KunoLu/640-skills/pull/153) 合并解决：squash `ce80ca2`，经 merge `376ea0c` 纳入本分支。Round 4 仅消费该契约，不修改 OpenAPI／#153 task。`CreateExportRequest.format` 为 html/csv/jpeg/pdf；尺寸 422 为无 Envelope 的封闭三字段对象，返回生效 caps；202 的 `data` 仍只有 export_id，降级告警在 `meta.warnings`。capabilities 自由 Json 响应不需 schema 修改。

以下两项 **CONTRACT-CHANGE-NEEDED 均已 satisfied**：由 [PR #154](https://github.com/KunoLu/640-skills/pull/154)（`d46d4ad`）定义，经 merge `8ac91c6a1853550a2c94f4e4d406d764514570f2` 纳入，并在 Round 6 实现：

1. **createExport 时 renderer 不可用 — satisfied / implemented in Round 6**。JPEG／PDF 共用 capabilities 检查／原因，在 pin／预检／作业前返回 HTTP **503**，封闭 body 精确 `{"detail":"EXPORT_RENDERER_UNAVAILABLE"}`，无 job、export_id、文件、pin 或 manifest。JPEG 无法预检时 503 优先；预检期间依赖消失同样 503 并释放 pin。HTML／CSV 不返回该 503；422 尺寸 caps 与 202 warning 不变。
2. **202 后失败状态协议 — satisfied / implemented in Round 6**。四格式均适用：renderer timeout → **EXPORT_RENDER_TIMEOUT**；崩溃、受理后不可用、作业时尺寸超限、发布失败及普通异常 → **EXPORT_RENDER_FAILED**。getExport 保持 HTTP200 Envelope，queued／generating／ready／cancelled 的 error=null，ready 持久 manifest 同样 null。内部诊断仅入安全 server warning，异常原文／stderr／路径／凭据不公开。downloadExport 仍 **409**，失败不发布 artifact／manifest。**13:38 的 `"export failed"` 固定字符串规则已被 #154 取代**，此前轮次记录仅为历史。

本轮不实施磁盘上限协议、跨平台或完整 AC-51；这些仍按计划单独交付。后续项 B 与后续项 C 均归第 7 项／F 阶段，C 另开单独 PRD docs PR，本轮仅更新放置记录。
