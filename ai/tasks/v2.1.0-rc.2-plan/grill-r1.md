# v2.1.0-rc.2 任务 0 — Grill 第 1 轮（R2：Local Dashboard + 四格式导出）

> **R1 已锁定（2026-10-19 11:47，Asia/Shanghai）**：用户逐题确认全部 17 个子问题，所选与推荐一致（Q1a A、Q1b A、Q2a A、Q2b A、Q3a A、Q3b A、Q3c A、Q3d A、Q4 D、Q5 C、Q6a A、Q6b A、Q6c A、Q7 B、Q8 C、Q9 C、Q10 A）；锁定决定清单见文末「D1–D17」。DDD 初稿已按锁定结果更新，待 Reviewy 按 book-ddd-distilled-modeling 出独立 Boundary Review。
>
> 修订记录（R1e，2026-10-19）：吸收 Reviewy DDD Boundary Review 意见——Query & Snapshot 由「R1 已有，不改」改为「R1 已有，R2.0c 扩展」并列出新增职责（落盘快照格式与版本、24h 保留、`snapshots/` 过期清理含启动清扫、崩溃一致性）；新增导出与快照清理不变量（在途导出作业固定 `snapshot_id` 并持引用，被引用快照不得被清理；`snapshots/` 仅由 Query & Snapshot 清理、`exports/` 仅由 Export 清理），上下文表拆分两目录的所有权；新增 Local Server & Access Control 上下文（D5–D8：端口冲突、serve 生命周期与实例锁含陈旧锁、一次性 ticket 配对与 session／Bearer、Host／Origin 白名单），明确不拥有查询与导出；Renderer Isolation 补 fonts-noto-cjk 依赖清单（D16）与 Playwright 安装目录 `SBTD_RUNTIME_HOME/browsers/`（D3/D4）；plan.md 将 D5–D8 实现归入 R2.0a，R2.2 只出证据。其余未动。
>
> 修订记录（R1d，2026-10-19）：吸收 Researchy 2026-10-19 事实核验——Q10 OMP 许可证已查明为 MIT（https://github.com/can1357/oh-my-pi/blob/main/LICENSE，GitHub API 识别为 MIT，最新 release v18.12.2），全文删除 OMP 许可证「待核验」表述，B/C 标为许可证可行（须保留版权声明并记入第三方声明），维持推荐 A（仅参考视觉语言，无许可证义务，B 可作 R2.0a ADR 升级路径）；Q2a-A 默认改为 `playwright install --only-shell chromium`（仅 headless shell，截图与 PDF 足够），体积按 Playwright 1.64.0 压缩下载量核验（--only-shell 每平台约 100–126MB；完整 chromium 约 300–330MB；Python playwright 包本体约 140MB），删除「约 300MB 估算／待核验」，安装授权提示须按实际所选模式显示体积；Q3c-A 补 ADR 须注明 #ticket URL 出现在浏览器启动命令行参数中、同机其他进程可见及缓解措施。其余未动。
>
> 修订记录（R1c，2026-10-19）：原 Q6 拆为 Q6a（仅导出临时副本，exports/ 下 24h 为 PRD §10.4 第 900 行默认）与 Q6c（临时 ReportSnapshot 是否本期落盘并默认保留 24h，PRD §10.4 第 899 行）；事实依据已核对——PRD v0.2 第 899–900 行、`sbtd-runtime/report_snapshot.py` `DEFAULT_TTL_SECONDS = 3600`（进程内 `SnapshotStore`）、`r1.4-acceptance-report.md`「落盘 snapshots/ 保留（§10.4 24h 期望）」deferred 条目；全文删除把快照推迟称为「基准／基线」的表述。非阻塞审题意见折入：Q2a-A「约 300MB」标为估算（待核验，随钉定的 Playwright 版本而异）并注明 Playwright 为可选 extra 依赖；Q1a-A 补「源码重建产物与入仓静态产物一致」的 CI 检查（仿 omp-sbtd kit `check-generated`）；Q3c-A 注明终端不打印含 ticket 的 URL、ticket 一次性；Q3b-A 注明陈旧锁（端口未监听）按无效处理；Q10 维持 OMP 许可证待核验。Q6b 未动。
>
> 修订记录（R1b）：吸收 Researchy/Reviewy 审题——Q1/Q2 按 §14.3、§19.3 与 ADR 0001 既定前提收窄；Q3 重出并拆为 Q3a–Q3d（框架与鉴权已由 ADR 0001 §2/§5 锁定，不再投票）；Q6 以 §10.4 导出副本 24h 默认为基准改写，30 秒刷新交互拆为 Q6b；新增 Q10（OMP 视觉复用程度，R2.0 固定）；Q4 补 CI runner／真机证据标注要求；DDD 初稿同步。Q5、Q7、Q8、Q9 未动。

出题范围：PRD v0.2（`docs/prd/SBTD_Runtime_API_and_Local_Dashboard_PRD_v0.2.md`）§12、§13、§14、§15.3、§16.3／§16.4、§18、§19.3、§20.2；底座核对：`sbtd-runtime/` 库面（`stats_query`／`csv_export`／`event_store`／`report_snapshot`／`facade`）、`contracts/openapi.yaml`（`/api/v1/exports*` 已钉 `x-sbtd-release: v2.1.0-rc.2`、下载无路径参数、带 CsrfToken）、`sbtd-runtime/docs/r1.4-acceptance-report.md`「有意推迟」一节。

已核对的 R1 现状事实（出题依据，不是待问项）：

- 快照：`report_snapshot.SnapshotStore` 为**进程内**对象，`DEFAULT_TTL_SECONDS = 3600`；迟到事件 mint 新 `snapshot_id`，过期返回 gone；rc.1 报告已把 §10.4 的 24h 落盘保留如实标为有意推迟。
- 库面零第三方依赖：纯 Python + unittest + ruff；无 HTTP 服务、无 Node 工具链。
- CSV：schema 1.1 已钉（末列 `reasoning_tokens`、BOM、注入防护、全量 cursor 遍历），R2 只需接服务与下载。

---

❓ **Q1 — 前端构建产物归属与打包工具钉住**

前提（不投票）：React + TypeScript 静态构建、由同一服务提供静态资源，已是 §14.3 的建议（「与 OMP 视觉参考接近；不要求生产 Node Web 服务」）；§12.3 要求 OMP 风格深浅主题、响应式、可访问性；§13.4 要求 HTML 导出单文件自包含、不加载外部脚本／CDN／字体。现状 `sbtd-runtime/` 是纯 Python 零依赖库，仓内没有任何 npm 构建链。本题只问两个未定点：**构建产物是否入仓**与**打包工具及版本钉住方式**。

**Q1a — 构建产物归属**

- **A. 产物入仓 `sbtd-runtime/dashboard/static/`**：Python 侧 `serve` 零 npm 依赖即可提供页面，与 R1 纯库面形态一致；§13.4 自包含离线 HTML 导出可复用同一份预构建产物内联；代价是仓内出现预构建 bundle 体积，需 diff 可审性约定（如产物独立目录、独立提交）；并配 CI 检查：从源码重新构建的静态产物须与入仓产物逐字节一致（仿 omp-sbtd kit `check-generated` 先例），防止产物与源码脱节。
- **B. 产物不入仓，仅 CI 构建并作为发布附件**：仓库干净；代价是源码检出后 `serve` 无页面可发，本地开发／验收必须先装 Node 构建，违反「本地服务不成为日常开发前置条件」的轻量定位（§3.3）。
- **C. 发布包内含产物但仓库不入（gitignore + 构建步骤进打包）**：仓库干净且发布可用；代价是仓库内任何一次验收（含 CI 的 serve 冒烟）都依赖构建步骤，R2.0b 起的本地验收链路变重。

**Q1b — 打包工具与版本钉住**

- **A. Vite，钉精确版本 + lockfile 入仓 + CI `npm ci` + 依赖审计**：主流 React+TS 静态构建链，产物为静态文件契合 §14.3；代价是引入 npm 依赖审计与许可证管理面。
- **B. esbuild 直接调用**：链最短；代价是 TS/资源处理与开发体验需自行拼装，§12.3 主题与组件复杂度下自维护成本高。
- **C. 不打包，原生 ES modules + importmap**：无构建步骤；代价是仍需 vendor 第三方 JS 并管许可证与版本，且与「React+TS 静态构建」前提不符。

✅ **已锁定 Q1a-A、Q1b-A**（用户 2026-10-19 11:47 确认，与推荐一致）。产物入仓让 Python 库保持零运行时新依赖即可 serve，npm 链只存在于开发／CI，不进用户运行时；Vite 精确版本 + lockfile + `npm ci` 保证构建可重复。产物体积预算、审计基线与钉住的具体版本号由 R2.0a 的 ADR 固定。

---

❓ **Q2 — Chromium 分发方式与版本钉住**

前提（不投票）：JPEG／PDF 渲染器用受控 Chromium（Python Playwright），已是 §13.5／§13.6 推荐（来源 S12/S13）、§14.3「独立 Playwright／Chromium 适配器」与 §19.3「renderer 包分发：独立管理的 Chromium，安装时授权，业务项目零依赖变更（R2.1 前固定）」的共同结论。**隔离要求是前提而非选项**：独立临时 profile、不复用用户浏览器登录态、只渲染服务器生成的安全报告、禁止外部网络与任意 `file://`、每次最多一个图像／PDF 作业、不得在用户项目装包或改 lockfile（§13.7）；AC-58 要隔离与断网测试证据。本题只问两个未定点：**Chromium 二进制怎么分发**与**版本钉住策略**。

**Q2a — Chromium 分发**

- **A. 安装时 `playwright install --only-shell chromium` 到扩展自有目录（`SBTD_RUNTIME_HOME/browsers/`），安装文档明示磁盘占用并取得授权（§13.7）**：默认仅安装 headless shell（截图与 PDF 渲染足够，无需完整 Chrome for Testing）；版本随 Playwright 精确钉住，路径归属扩展、不碰用户浏览器；体积已核验（Playwright 1.64.0，压缩下载体积，未测解压后体积）：`--only-shell` 每平台约 100–126MB；完整 `playwright install chromium`（Chrome for Testing + headless shell + 约 2MB ffmpeg）每平台约 300–330MB（Linux 约 200+126，Windows 约 207+124，macOS arm64 约 195+104）；Python playwright 包本体安装后约 140MB（含捆绑 node driver）。三平台差异仍存在；Playwright 作为可选 extra 依赖声明，未安装 renderer 时其余功能不受影响、仅 JPEG/PDF 导出标不可用；安装授权提示必须显示**实际所选模式**的体积（--only-shell 或完整 chromium），不显示通用估算。
- **B. 首次导出 JPEG／PDF 时按需下载并当场请求授权**：未用导出功能的用户零磁盘成本；代价是首次导出延迟长、离线环境直接失败，且授权时机从安装时推迟到使用中，与 §19.3「安装时授权」表述有张力。
- **C. 复用系统 Chrome（Playwright channel）作为降级**：零下载；代价是版本不受控、与用户 Chrome 的 profile／登录态边界模糊，难以满足 §13.7 与 AC-58 的隔离证据，只能作为 A 不可用时的显式降级并如实标注。

**Q2b — 版本钉住**

- **A. 钉 `playwright` 精确 PyPI 版本（其 Chromium revision 随包固定），CI 缓存按版本键**：一次钉住同时固定驱动与浏览器；代价是升级需走依赖更新流程。
- **B. Playwright 钉版本，Chromium 另钉 `PLAYWRIGHT_BROWSERS_PATH` 下的具体 revision**：颗粒更细；代价是两针要维护一致性，收益不明显。
- **C. 只钉主版本范围，随上游漂移**：验收证据不可重复，否决。

✅ **已锁定 Q2a-A、Q2b-A**（用户 2026-10-19 11:47 确认，与推荐一致）。与 §19.3「独立管理的 Chromium，安装时授权」逐字对齐；缺 renderer 时导出菜单标注不可用及原因，不谎称四格式已验收。Q2a-C 仅在安装文档中作为明示降级路径保留，不作为验收基线。隔离落地（独立子进程、每作业临时 profile、路由层 abort 一切外联、单作业信号量）按 §13.7 执行，AC-58 出断网与隔离证据。

---

❓ **Q3 — `serve` 运行形态、配对交付与 Host/Origin 细则**

前提（不投票，若要改须另开 ADR）：

- **服务框架已由 ADR 0001 §2 锁定**：Starlette + uvicorn（`starlette>=1.8,<2`、`uvicorn>=0.54,<0.56`），纯标准库 `http.server` 与 FastAPI+pydantic 已在该 ADR 中明示否决，本题不再投票。
- **鉴权已由 ADR 0001 §5 锁定**：短时一次性配对凭证换取本地 session／Bearer；长期 token 只放 `~/.sbtd-runtime/`（Unix 权限 0600），不进入 URL、日志或导出；服务保持 loopback，并做 Host／Origin 校验与 CSRF（满足 AC-56）。固定 Bearer token 文件不配对、仅 loopback+Origin 不鉴权均已否决。
- §3.3：入口 `sbtd-runtime serve --port 6400`，显式启动、无 daemon、无开机自启；§12.1 默认 `http://localhost:6400`；OpenAPI 契约已含 `localSession` 安全方案与 `CsrfToken` 参数。

本题只问四个未定部分：

**Q3a — 端口冲突处理（AC-34：不杀其他进程、不静默换地址）**

- **A. 启动失败，明确报「6400 被占用」并提示用 `--port` 显式指定后重试**：与 AC-34「显示冲突及显式替代端口选项」逐字对齐；代价是自动化场景需人多敲一次。
- **B. 检测到占用后交互询问，用户确认才换端口**：不静默；代价是引入交互依赖，无 TTY 环境退化路径要另定。
- **C. 自动自增或随机端口并在终端显著提示**：即使有提示也属未经显式选择换地址，偏离 AC-34，须用户明确批准才可考虑。
- **D. 杀掉占用进程**：AC-34 明禁，仅列出以示否决。

✅ **已锁定 Q3a-A**（用户 2026-10-19 11:47 确认，与推荐一致）。失败信息给出冲突事实与 `--port` 显式替代，退出码非零可脚本化。

**Q3b — `serve` 启停形态**

- **A. 前台进程、Ctrl-C 退出；默认自动打开浏览器（等价 `--open`），重复启动检测到已有实例时提示其地址并非零退出**：日常路径一键可达；重复启动不产生第二个服务实例，不会触发 Q3a 的伪冲突。
- **B. 前台进程、Ctrl-C 退出；不自动开浏览器，只打印本地 URL（不含凭证），`--open` 为显式 flag**：保守；代价是多一步手动打开。
- **C. 前台进程；重复启动直接按 Q3a 端口冲突失败**：实现最简；代价是用户忘了已有实例时体验差（错误信息与真实语义不符）。
- **D. 后台化／daemon／系统服务**：违反 §3.3（显式启动、无 daemon、无开机自启），仅列出以示否决。

✅ **已锁定 Q3b-A**（用户 2026-10-19 11:47 确认，与推荐一致）。§3.3 已定显式启动前台形态；默认 `--open` 配合 Q3c 的一次性票据交付，把配对摩擦降到零；重复启动检测用 runtime home 下的实例锁文件＋端口双判，命中则提示已有实例地址并以非零退出；锁文件存在但端口未监听视为陈旧锁、按无效处理（清理后正常启动），不误报冲突。

**Q3c — 一次性配对凭证如何交给浏览器且不进日志**

- **A. 启动时自动打开带一次性 ticket 的 URL fragment（`#ticket=…`）；前端读取后立即调用配对端点换 session／Bearer，并立即从地址栏与浏览器历史移除销毁**：§10.2 明文允许此路径（「若使用 URL fragment 传一次性票据，读取后立即移除并销毁」）；fragment 不进 HTTP 请求与服务器访问日志；ticket 短时、一次性、与本次进程绑定，使用即销毁；终端不打印含 ticket 的 URL（ticket 只经自动打开的浏览器 fragment 传递，避免落进终端回滚缓冲区与 shell 历史）。**风险注明（ADR 必载）**：带 `#ticket` 的 URL 会出现在浏览器启动的命令行参数中，同机其他进程可读进程列表看到；缓解措施为终端永不打印该 URL、ticket 短时且一次性（被旁观窃取后窗口极短且用后即废）。
- **B. 启动器把一次性 ticket 写入 `~/.sbtd-runtime/` 下 0600 临时文件，页面配对框提示用户从该文件复制粘贴**：无浏览器历史风险；代价是手动步骤，ticket 文件需用后立即删除。
- **C. 终端显示短配对码（如 6 位），用户在页面输入完成配对（设备码式）**：不落 URL 与文件；代价是 brute-force 面要限速，实现比 A 重。
- **D. 把长期 token 或 session 直接放进 URL／剪贴板／环境变量交给浏览器**：ADR 0001 §5 明禁（长期 token 不进 URL／日志），仅列出以示否决。

✅ **已锁定 Q3c-A**（用户 2026-10-19 11:47 确认，与推荐一致）。与 §10.2 的 fragment 明文和 ADR §5 的「短时一次性配对换 session」逐字对齐；ticket 不落任何日志文件与导出，服务器日志只记配对成功事件不记 ticket 值。B 作为无 `--open` 环境（SSH／无浏览器机器）的备用路径保留。

**Q3d — Host／Origin 白名单具体规则**

- **A. 严格匹配：Host 头必须属于 `{localhost, 127.0.0.1, [::1]}` 且端口必须等于实际监听端口；Origin 必须 scheme+host+port 全匹配本服务来源，否则拒绝；无 Origin 的非浏览器请求（CLI）允许但须持有效 Bearer**：直接封堵 DNS rebinding（外部域名解析到 127.0.0.1 时 Host 不在白名单即拒）与跨端口兄弟服务偷渡。
- **B. Host 白名单同上但端口不校验；Origin 只校验 host 部分**：实现略简；代价是同机任意端口上的恶意页面可过 Host 检查，削弱 DNS rebinding 防线。
- **C. 白名单可配置，允许用户追加自定义主机名**：灵活；代价是每加一个名字就开一个 rebinding 入口，本期无需求。
- **D. 只检查连接来自 loopback，不查 Host／Origin**：ADR 0001 §5 与 §10.2 已否决（「不能因为请求来自本机就无条件信任网页请求」），仅列出以示否决。

✅ **已锁定 Q3d-A**（用户 2026-10-19 11:47 确认，与推荐一致）。与 AC-56 的 Host／DNS rebinding 测试面一一对应；规则全部硬编码、无配置面，CI 用外部域名 Host 头、错误端口、跨 Origin 三组负例锁定。

---

❓ **Q4 — macOS／Windows 真机证据从哪里来**

背景：§14.2 平台矩阵：macOS Apple Silicon「首发必验」、Windows 11 x64「首发必验，含 ACL／路径」「Windows 原生测试不能被 Linux 模拟路径测试替代」；AC-33 要 macOS／Windows 原生启动退出测试、AC-62 要「实际报告而非 README 自报」。现状：只有云端 Linux（本环境）和用户的一台 Mac。rc.1 报告对宿主 smoke 的先例是「真实执行 + capability matrix 如实记录」，禁止 fixture 冒充。

- **A. GitHub Actions `macos-*`／`windows-latest` runner 跑启动、API、四格式导出与字体断言，报告工件入仓**：可重复、是原生 OS 而非模拟；代价是 CI 时长与 Chromium 缓存管理，runner 环境（字体、GPU）与用户真机仍有差异。
- **B. 用户 Mac 手跑验收脚本，原生报告＋同 stem 中文摘要入仓**：真机最真；代价是占用用户时间、不可自动重复，且仍不覆盖 Windows。
- **C. Windows 标 unsupported／延期**：违反 §14.2「首发必验」，等于缩减已确认范围，须用户显式批准才可考虑。
- **D. A+B 组合**：CI runner 出可重复的自动化原生证据，用户 Mac 补一轮真机视觉／字体确认；Windows 完全靠 CI runner。

✅ **已锁定 Q4-D**（用户 2026-10-19 11:47 确认，与推荐一致）。AC-62 要的是真实平台实测报告，GitHub Actions 的 macOS／Windows runner 是原生系统，满足 §14.2「不能用 Linux 模拟替代」；CI 覆盖可重复部分（启动、API 冒烟、JPEG/PDF 生成、CJK 渲染像素断言），用户 Mac 只做一轮人工视觉确认（主题、字体、长图完整性），负担最小。**所有报告必须逐条分开标注证据来自 CI runner 还是真机，不混称；若 Windows 只有 CI runner 证据，报告中如实写明「Windows 证据全部来自 CI runner，无真机确认」。** Windows 不降级；若用户坚持砍 Windows，那是范围变更，须回到 PRD 层面确认。

---

❓ **Q5 — 任务表与 R2 计划放哪个文件**

背景：§15.3 已有 R2 五行工作包表（R2.0a–R2.2）与完成门；Lord 拟定的 rc.2 任务表（0 计划／R2.0a／R2.0b／R2.1a／R2.1b／R2.2／E prerelease／F docs 回填）是实施编排，比 PRD 表细。本轮范围明确「不改 PRD 正文」。rc.1 先例：任务工件在 `ai/tasks/<id>/`，验收报告在 `sbtd-runtime/docs/`。

- **A. PRD v0.2 §15.3 原地补表**：单一文档；代价是本轮禁止改 PRD，且执行级编排（E／F、依赖顺序）污染产品需求文档，PRD 版本需升 v0.3。
- **B. 新建 `docs/prd/` 下 rc.2 计划文件**：与 PRD 同区；代价是 docs/prd 混入一份有时效的执行计划，发布后要再处理。
- **C. 放 `ai/tasks/v2.1.0-rc.2-plan/`（如 `plan.md`），与本 task.md 同目录**：任务工件随任务生命周期归档；代价是不在 docs 正式文档区，F 阶段回填时才进 docs／CHANGELOG。
- **D. 拆散：任务表进 `ai/tasks/index.md`，计划进 PRD**：两处都要改，索引只该存导航（rc.1 先例），否决。

✅ **已锁定 Q5-C**（用户 2026-10-19 11:47 确认，与推荐一致）。本轮明确不改 PRD 正文；Lord 任务表是实施编排而非需求变更，放任务目录与 rc.1 先例一致（任务工件在 `ai/tasks/`）。E／F 阶段（prerelease、docs 回填）再把锁定的计划摘要回填 CHANGELOG／docs，PRD 若需升 v0.3 由用户届时另行授权。

---

❓ **Q6a — 导出临时副本的存放与保留（PRD §10.4 第 900 行）**

背景：本题只问**导出临时副本**（export artifacts）。已核对事实：§10.4 第 900 行「导出临时副本：ready 后默认保留 24 小时；用户浏览器下载文件不由服务清理」；§13.10「下载中断后在有效期内下载同一产物，摘要不变」。未定点：导出产物文件存哪、ready 后保留期与清理按什么执行。（快照本身的保活与落盘问题见 Q6c；作业保活语义：创建导出即固定 `snapshot_id` 并持引用直到完成／取消，TTL 只约束空闲快照——这是 R1 已有语义的延续，不在本题投票。）

- **A.（符合 PRD §10.4 第 900 行默认）导出产物写 runtime home 下 `exports/`（以 `export_id` 寻址，契约下载无路径参数，天然防穿越 AC-57；目录权限 0700、文件 0600），ready 后默认保留 24 小时并带过期清理，清理仅触及本扩展生成目录**：与 PRD 默认逐字对齐；代价是进程重启后 24h 内的产物仍在盘上，清理逻辑须处理「服务不在运行时过期」的情形（如下次启动时清扫）。
- **B.（偏离 PRD §10.4 默认）ready 后保留期短于 24 小时（如下载完即删或仅进程内存活）**：无法保证「有效期内重复下载同一产物、摘要不变」（§13.10），须用户明确批准此偏离并记入 ADR／PRD 偏离清单。
- **C.（偏离 PRD §10.4 默认）保留期长于 24 小时或用户可配置**：保留面与磁盘占用扩大，偏离默认须用户明确批准；配置面本期无需求。

✅ **已锁定 Q6a-A**（用户 2026-10-19 11:47 确认，与推荐一致）。24h 保留就是 §10.4 第 900 行的明文默认，A 不构成任何偏离；`export_id` 寻址＋0700／0600 权限与 ADR 0001 §3 家目录约定一致；过期清理限定在本扩展自有的 `exports/` 目录内，不触碰用户数据。

---

❓ **Q6b — 30 秒轮询发现新数据时的页面交互**

背景（从原 Q6 拆出）：§12.6「服务运行时可每 30 秒检查是否有新的已入库数据；更新采用整份快照替换」；§12.5「应用筛选后全页 Panel 与详情使用同一 snapshot；加载中保留上一份已完成视图并标明正在更新，不混合新旧数据」。未定：轮询发现新水位时，页面是自动替换还是先提示。

- **A. 自动整份替换，替换期间保留上一份已完成视图并标注「正在更新」，完成后无感切换**：直接执行 §12.6「整份快照替换」＋§12.5 加载语义；代价是正在阅读详情的用户视图被换掉。
- **B. 只提示「有新数据」，用户点击后才整份替换**：阅读不被打断；代价是与 §12.6「更新采用整份快照替换」的自动语义有张力，页面可能长时间停留在旧水位，须明确标注当前水位时间。
- **C. 自动替换，但用户展开了详情或有在途导出作业时暂停替换、只提示**：折中；代价是「暂停条件」规则引入第三种交互状态，测试面变大。
- **D. 提供用户可选的自动／手动刷新开关**：把决策推给用户；代价是新增持久化偏好与双路径测试。

✅ **已锁定 Q6b-A**（用户 2026-10-19 11:47 确认，与推荐一致）。§12.6 已写「整份快照替换」、§12.5 已写「加载中保留上一份视图并标明正在更新」，A 只是把两条既定语义接起来，不自造第三种交互；导出作业固定 snapshot_id（Q6a 背景所述保活语义），自动刷新不影响在途导出（AC-52）。页面须始终显示当前快照水位时间，使「看到的是哪一刻的数据」可见。

---

❓ **Q6c — 临时 ReportSnapshot 是否本期改为落盘并默认保留 24 小时（PRD §10.4 第 899 行）**

背景（均已核对，不是待问项）：PRD §10.4 第 899 行「临时 ReportSnapshot：默认 24 小时；创建时告知有效期；过期清理仅触及本扩展生成目录」。R1 现状：`report_snapshot.py` 的 `SnapshotStore` 是**进程内**对象，`DEFAULT_TTL_SECONDS = 3600`，进程退出快照即消失；`r1.4-acceptance-report.md`「有意推迟」一节已把「落盘 `snapshots/` 保留（§10.4 24h 期望）」如实标为 deferred，差异写进 install-and-use.md。注意：rc.1 的推迟是针对 R1 验收范围的已接受决定，**不是长期基线**——R2 引入长驻 `serve` 进程后，「进程内 3600s」与 PRD 第 899 行「默认 24 小时＋创建时告知有效期」的差距会变成用户可感知的行为差异（重启即全灭、有效期只有 1 小时）。未定点：rc.2 是否补上落盘快照。

- **A. 落盘 + 24h TTL + 启动时清理过期（符合 PRD）**：runtime home 下 `snapshots/`（权限 0700／0600 同 exports），创建时返回有效期，过期清理与启动清扫仅触及本目录；与 §10.4 第 899 行逐字对齐，无新配置面。
- **B. 落盘但 TTL 可配置、默认 24h（符合 PRD，多一个配置面）**：同样满足默认；代价是新增配置面及其测试、文档与「配置错配导致快照提前消失」的支持成本，本期无此需求。
- **C. 维持 R1 进程内 3600s**：**偏离 PRD §10.4 第 899 行**，须用户书面批准，并记入 ADR／PRD 偏离清单；安装文档与验收报告须继续如实写明差异。
- **D. 推迟到 rc.3**：**同样偏离 PRD §10.4 第 899 行**（rc.2 交付时不满足），须用户书面批准并记入偏离清单；适合仅当本期范围必须收敛时。

✅ **已锁定 Q6c-A**（用户 2026-10-19 11:47 确认，与推荐一致）。事实依据：§10.4 第 899 行是 PRD 明文默认而非建议；rc.1 的 deferred 只覆盖 R1 验收，不能自动继承为 R2 基线；R2 恰恰是把快照暴露给长驻服务与导出作业的一期，「重启即消失＋1 小时过期」与 §12.6 的 30 秒轮询长会话语义直接冲突。代价如实列出：新增落盘格式与版本、崩溃一致性（半成品快照文件不得被当作有效快照）、清理授权边界（AC-61 只覆盖原始事件清理，快照清理授权须按 §10.4「仅触及本扩展生成目录」单独立据），R2 范围相应变大，已在任务表中单列工作包（见 `plan.md`）。

---

❓ **Q7 — Panel 注册表契约放哪、是否机器可读**

背景：§15.3 R2.0a 产物写「Panel registry、ReportDocument、设计规格」；§12.4 已定 13 个 Panel ID 与字段依赖；§13.3 要求页面主体与导出共用同一 Panel 定义与数据绑定；AC-45 要「Panel manifest 对账」、AC-51 要四格式关键数值一致。未定：registry 是前端 TS 私有结构，还是 `contracts/` 下的机器可读契约（R1 有 `metrics-catalog.json` 先例）。

- **A. 前端 TS 内私有注册表**：实现快；代价是 HTML/JPEG/PDF 导出侧（服务端）与 E2E 对账没有共享事实源，AC-45 只能靠 DOM 断言拼。
- **B. 新增 `contracts/panel-manifest.json`（schema 版本化）：Panel ID、标题、数据依赖 metric 族、导出必需性；前端注册表、ReportDocument、导出对账、AC-45 测试都从它派生**：单一事实源；代价是多一个要版本化与锁定的契约文件。
- **C. 后端 Python 持有 manifest，前端构建期生成 TS**：单一事实源在 Python；代价是构建期代码生成步骤，前端独立开发时脱节。

✅ **已锁定 Q7-B**（用户 2026-10-19 11:47 确认，与推荐一致）。R1 已有 `metrics-catalog.json` 机器可读契约＋golden 钉测的成熟先例（`test_golden_contracts`），Panel manifest 照搬该模式成本最低；AC-45「Panel manifest 对账」字面要求一个可对账的 manifest；四格式一致性（AC-51）和「折叠 Panel 导出时展开、但不能少内容」（§12.3）都需要服务端与前端共用同一份 Panel 全集定义。版本号纳入导出 manifest 记录（§13.9）。

---

❓ **Q8 — 脱敏与安全净化的落点**

背景：§13.2 导出主路径含「预检数据完整性、renderer／容量、授权与脱敏」；§13.9 文件名不得含邮箱、HOME 绝对路径、凭证，且要记录「脱敏版本」；AC-54 导出无秘密／绝对路径／隐藏原始对话 JSON，AC-55 恶意任务名 XSS。R1 已有存储层防线：秘密键入库即拒（`test_event_store…test_extension_secret_is_not_persisted`）。未定：R2 展示与导出侧的脱敏／净化（用户别名、HTML 转义、SVG 净化、路径→opaque ID）落在哪一层，脱敏规则版本在哪定义。

- **A. 后端查询／导出序列化层统一脱敏，前端拿到的 DTO 即安全文本**：一处规则、一个版本号；代价是所有展示字段都必须过同一管线，前端富交互（内联 SVG 图表）的自由度受限。
- **B. 前端渲染层净化（DOMPurify 类库）**：贴近 DOM 上下文；代价是 CSV／服务端 HTML／JPEG/PDF 渲染不经过前端 DOM，四格式脱敏不一致，AC-54 无法统一证明。
- **C. 分层：存储层拒绝秘密（已有）＋后端输出层统一脱敏与转义（规则与版本号在 `contracts/` 侧定义，写进导出 manifest）＋前端只做 DOM 上下文转义兜底**：纵深防御；代价是两层都要测。
- **D. 不新增脱敏层，只靠 R1 存储层拒绝**：§13.9/AC-54 明确要求导出侧无绝对路径与隐藏 JSON，存储层不覆盖「合法入库但不该导出」的字段（如 actor_alias 的呈现策略），不足。

✅ **已锁定 Q8-C**（用户 2026-10-19 11:47 确认，与推荐一致）。四格式里只有交互页面经过前端 DOM，CSV 与离线 HTML 由服务端直接产出，脱敏必须以后端输出层为唯一权威管线才能给 AC-54/AC-55 统一证据；前端转义只是 XSS 兜底。脱敏规则版本号随导出 manifest 记录（§13.9 已要求「脱敏版本」），与事件 schema 1.0／QueryScope 1.0／CSV 1.1 的三针模式一致，可锁定可回归。

---

❓ **Q9 — 中日文字体策略与渲染环境基线**

背景：§13.4 要求离线 HTML「使用系统字体及明确 CJK fallback，不把当前机器字体路径写入文件」；§13.6 要求 PDF「中／日／英混合文字可显示」；§13.5 导出前等待字体完成；AC-42 中日英可用、AC-62 平台实测；§18.1「导出视觉测试」含中日文字体。未定：是否打包字体；CI Linux 容器与 GitHub runner 默认常无 CJK 字体，JPEG/PDF 验收会出豆腐块。

- **A. 纯系统字体栈，文档列出各平台期望字体**：零体积零许可证负担；代价是 Linux CI／最小容器无 CJK 字体时 JPEG/PDF 验收不稳定，AC-42/62 证据不可重复。
- **B. 打包开源 CJK 字体（Noto Sans CJK 或其子集）内嵌离线 HTML 并装入 renderer 环境**：最稳；代价是体积（全量数十 MB，子集化需构建步骤）、许可证声明，且与 §13.4「使用系统字体」表述有张力（§13.4 禁的是外部网络加载，不禁内嵌，但产品语义要用户确认）。
- **C. 系统字体为主；把 `fonts-noto-cjk` 纳入受控 renderer 环境的依赖清单（安装时随 renderer 一起授权，§13.7），CI／runner 钉字体版本；离线 HTML 只用系统字体栈 + fallback**：HTML 侧零变化；代价是 Linux 上 JPEG/PDF 可用性依赖该字体包，缺时按 §13.7 标不可用。
- **D. 导出时动态从 CDN 拉字体**：直接违反 §13.4 离线要求与 §13.7 renderer 禁网，否决。

✅ **已锁定 Q9-C**（用户 2026-10-19 11:47 确认，与推荐一致）。§13.4 对 HTML 的表述就是系统字体 + CJK fallback，不该为本期改它；字体可读性问题实际出在**受控 renderer 环境**（JPEG/PDF 由我们生成），而 §13.7 已确立「安装时明确说明可选导出运行时的磁盘与依赖并取得授权」的机制，把字体包并入该依赖清单顺理成章；CI 与 GitHub runner 钉住字体版本后 AC-42/62 证据可重复。不打包字体入仓，避免体积与许可证成本。

---

❓ **Q10 — OMP 视觉复用程度（§19.3 要求 R2.0 固定）**

背景：§19.3「OMP 视觉复用程度：先参考视觉语言；复制代码时核验并保留适用许可证／声明，R2.0 固定」；§15.3 R2.0a「OMP 视觉参考与单页布局」；§12.3 要求 OMP 风格深浅主题、分段按钮沿用 OMP 预置范围（§12.5）。**许可证核查结论（Researchy 2026-10-19 核验）：OMP 许可证为 MIT**——https://github.com/can1357/oh-my-pi/blob/main/LICENSE，GitHub API 识别为 MIT，最新 release v18.12.2。MIT 允许复制代码与资源，条件是保留版权与许可证声明并记入第三方声明（third-party notices）。

- **A. 只参考 OMP 视觉规范（配色、密度、圆角、间距、深浅主题结构、预置时间段）自行实现，零代码／零资源文件复制**：视觉风格的参考不构成版权复制，无需 OMP 许可证即可满足「仿 OMP 风格」；代价是组件全部手写，R2.0a 设计规格须把参考点写成自有 token 定义。
- **B. 复用 OMP 设计 token 与图标资源，逐文件核验许可证并保留声明**：一致性最高；许可证可行（OMP 为 MIT，条件是保留版权／许可证声明并记入第三方声明）；代价是须维护逐文件来源清单与第三方声明，复用面越大维护越重。
- **C. 直接复制 OMP 组件代码并附许可证声明**：实现最快；许可证可行（MIT，保留版权／许可证声明并记入第三方声明即可，无 copyleft 义务）；代价是复制代码的声明面与后续同步上游修复的成本比 token／图标重。
- **D. 不复用 OMP 任何视觉元素，另起设计语言**：偏离 §12.3／R2.0a「仿 OMP 风格」的既定方向，须用户明确批准。

✅ **已锁定 Q10-A**（用户 2026-10-19 11:47 确认，与推荐一致）。A 不依赖任何许可证结论即可执行，天然满足 §19.3「先参考视觉语言」的默认建议，且无任何许可证义务（自行实现、零复制即无声明负担）；OMP 许可证已核验为 MIT，B／C 在许可证上均可行，若用户希望提升一致性，可在 R2.0a ADR 中把 token／图标升级为 B，逐文件保留版权／许可证声明并记入第三方声明。

---

## 锁定决定清单（D1–D17，用户 2026-10-19 11:47 确认）

| # | 题目 | 选择 | 内容（一行） |
|---|---|---|---|
| D1 | Q1a | A | 前端构建产物入仓 `sbtd-runtime/dashboard/static/`，配源码重建逐字节一致 CI 检查 — 「用户 11:47 确认」 |
| D2 | Q1b | A | Vite 钉精确版本 + lockfile 入仓 + CI `npm ci` + 依赖审计 — 「用户 11:47 确认」 |
| D3 | Q2a | A | 安装时 `playwright install --only-shell chromium` 到扩展自有目录，授权提示按实际所选模式显示体积 — 「用户 11:47 确认」 |
| D4 | Q2b | A | 钉 `playwright` 精确 PyPI 版本（Chromium revision 随包固定），CI 缓存按版本键 — 「用户 11:47 确认」 |
| D5 | Q3a | A | 端口占用即启动失败，明确报冲突并提示 `--port` 显式替代，退出码非零 — 「用户 11:47 确认」 |
| D6 | Q3b | A | 前台 Ctrl-C 退出，默认 `--open`；重复启动经实例锁＋端口双判提示已有实例并非零退出，陈旧锁按无效处理 — 「用户 11:47 确认」 |
| D7 | Q3c | A | 一次性 ticket 经 URL fragment 自动打开交付，读后即毁、不进日志、终端不打印；命令行参数可见风险与缓解写入 ADR — 「用户 11:47 确认」 |
| D8 | Q3d | A | Host 严格白名单（localhost/127.0.0.1/[::1]＋端口相等）＋Origin 全匹配，规则硬编码无配置面 — 「用户 11:47 确认」 |
| D9 | Q4 | D | CI macOS/Windows runner 出自动化原生证据＋用户 Mac 补一轮真机视觉／字体确认；证据逐条标注来源，不混称 — 「用户 11:47 确认」 |
| D10 | Q5 | C | 任务表与 R2 计划放 `ai/tasks/v2.1.0-rc.2-plan/plan.md`，E/F 阶段再回填 docs／CHANGELOG — 「用户 11:47 确认」 |
| D11 | Q6a | A | 导出产物落 `exports/`（export_id 寻址、0700/0600），ready 后默认保留 24h 并带过期清理，符合 PRD §10.4 第 900 行 — 「用户 11:47 确认」 |
| D12 | Q6b | A | 轮询发现新数据自动整份快照替换，替换期间保留上一份视图并标注「正在更新」，页面常显水位时间 — 「用户 11:47 确认」 |
| D13 | Q6c | A | 临时 ReportSnapshot 本期改落盘 `snapshots/`＋24h TTL＋启动清扫过期；崩溃一致性：半成品文件永不当有效快照（写临时文件＋原子 rename＋校验和／版本头）；任务表单列工作包 — 「用户 11:47 确认」 |
| D14 | Q7 | B | 新增 `contracts/panel-manifest.json`（schema 版本化）为 Panel 单一事实源，前端注册表／ReportDocument／导出对账／AC-45 测试均由此派生 — 「用户 11:47 确认」 |
| D15 | Q8 | C | 分层脱敏：存储层拒秘密（已有）＋后端输出层统一脱敏（规则与版本号在 `contracts/` 侧、写入导出 manifest）＋前端 DOM 转义兜底 — 「用户 11:47 确认」 |
| D16 | Q9 | C | 离线 HTML 纯系统字体栈＋CJK fallback；`fonts-noto-cjk` 纳入受控 renderer 环境依赖清单并钉版本，不打包字体入仓 — 「用户 11:47 确认」 |
| D17 | Q10 | A | 仅参考 OMP 视觉语言自行实现、零代码／零资源复制、无许可证义务；如需升级 B 由 R2.0a ADR 固定（OMP 为 MIT） — 「用户 11:47 确认」 |

---

## DDD 初稿（已按 R1 锁定结果更新，2026-10-19；待 Reviewy 按 book-ddd-distilled-modeling 出独立 Boundary Review）

> 已由 ADR 0001 锁定、不在本草案开放项内：服务框架 Starlette + uvicorn（ADR 0001 §2，`starlette>=1.8,<2`、`uvicorn>=0.54,<0.56`）；鉴权（ADR 0001 §5：短时一次性配对凭证换 session／Bearer，长期 token 仅 `~/.sbtd-runtime/` 0600 不进 URL／日志／导出，loopback + Host／Origin + CSRF）；runtime 家目录与 registry（ADR 0001 §3）；验收宿主版本（ADR 0001 §6）。导出产物保留按 PRD §10.4 默认并已锁定（D11）：ready 后 24 小时；临时 ReportSnapshot 本期落盘 24h 已锁定（D13，落盘格式与崩溃一致性细节由 R2.0c 工作包实现）。

**Ubiquitous language（通用语言草案）**：

- **ReportDocument**：`ReportDocument(snapshot, presentation_state)`（§13.3），页面与四格式导出共用的单一报告文档模型；不是 DOM 快照、不是 outerHTML。
- **Panel**：注册表（panel-manifest）中的一个逻辑报告区块，有稳定 Panel ID、数据依赖与导出必需性（§12.4、AC-45）；页面呈现与导出共用同一定义。
- **快照（Snapshot）**：一个规范化 QueryScope 在一个 ingest 水位上的固定视图（R1 已定义）；一份筛选、一份快照、四种导出共用同一 `snapshot_id`（§0.2-4）；迟到事件 mint 新 id，旧快照不被改写。
- **呈现状态（presentation_state）**：主题、报告宽度、展开明细、排序、预览行集、Panel 顺序、图例状态（§13.3）；只影响呈现，不改变 CSV 数据范围。
- **数据质量（data quality）**：覆盖状态、缺口、未关联、来源水位的如实声明；Panel 与导出必须始终携带，不用 0 或绿灯冒充（§12.4 data-quality Panel、AC-39）。
- **导出作业（Export Job）**：`export_id` 寻址的一次性产物生成任务；固定 snapshot_id＋呈现状态，可取消，产物落 `exports/`，ready 后默认保留 24 小时（PRD §10.4 默认）并带过期清理；`export.generated` ≠ 用户已保存（§13.9）。
- **数据族（record_type）**：CSV 内的粒度声明（metric/task/run/…/data_quality，§13.8），汇总族与明细族分离防双算。
- **受控渲染器（Isolated Renderer）**：扩展自有的 Chromium 子进程环境，独立临时 profile、禁网、单作业（§13.7）；是导出依赖，不是业务项目的测试依赖。

**Bounded contexts（边界草案）**：

| Context | 拥有 | 不拥有 |
|---|---|---|
| Query & Snapshot（R1 已有，R2.0c 扩展） | QueryScope、指标口径、snapshot_id／水位、dataset cursor；R2.0c 新增：落盘快照格式与版本、24h 保留、`snapshots/` 过期清理（含启动时清扫过期快照）、崩溃一致性（半成品文件永不当有效快照） | 页面布局、导出文件格式 |
| Dashboard Presentation（R2 新） | Panel 注册表消费、筛选交互、主题、整页同一快照替换 | 不直接查事件库、不各自计算总数 |
| Export（R2 新） | ReportDocument 序列化、四格式产物、导出作业生命周期、脱敏版本、manifest 对账、`exports/` 过期清理（仅 Export 清理 exports/） | 不改快照语义、不新造统计口径、不清理 `snapshots/` |
| Renderer Isolation（R2 新） | Chromium 子进程、profile／网络隔离、像素与分页上限；renderer 环境依赖清单（含 fonts-noto-cjk 并钉版本，D16）与 Playwright 安装目录 `SBTD_RUNTIME_HOME/browsers/`（D3/D4） | 不接受任意 URL／HTML，不复用用户浏览器 |
| Local Server & Access Control（R2 新） | `serve` 启动与端口冲突处理（D5）、serve 生命周期与实例锁（含陈旧锁按无效处理，D6）、一次性 ticket 配对与 session／Bearer 签发（D7）、Host／Origin 白名单校验（D8） | 不拥有查询与快照语义、不拥有导出产物与导出作业 |
| Observation & Audit（R1 已有，不改） | 原始事件、去重、checkpoint | 导出行为只产生操作事件，不回流污染当前快照（§13.9） |

**Invariants（草案）**：同一快照四格式关键数值一致（AC-51）；导出期间新数据不影响在生成文件（AC-52）；导出作业创建即固定 `snapshot_id` 并持引用直到完成／取消，**被在途导出作业引用的快照不得被清理**（plan.md 依赖顺序说明已载）；页面与导出无任何业务写操作（§0.2-5）；核心 Panel 查询失败不产出冒充完整的导出（§13.10）；脱敏以后端输出层为唯一权威管线；落盘快照半成品文件永不被当作有效快照（写临时文件＋原子 rename＋校验和／版本头，D13）；清理所有权单一：`snapshots/` 仅由 Query & Snapshot 清理（含启动时清扫过期快照，D13），`exports/` 仅由 Export 清理（ready 后 24h 过期清理，D11），两者互不越界且均仅触及本扩展自有目录。

**Open questions（R1 锁定后剩余，待后续轮次或 ADR 固定）**：Panel manifest 版本号与 metrics 版本的对齐节奏（R2.0a ADR 固定）；落盘 ReportSnapshot 文件格式版本号与校验和算法选型（R2.0c ADR 固定）；Q10 若升级 B 则逐文件复用清单与第三方声明的格式由 R2.0a ADR 固定（OMP 许可证已核验为 MIT，2026-10-19）。服务框架、鉴权、家目录、宿主版本已由 ADR 0001 锁定；Q1–Q10（含 Q6a/Q6b/Q6c）全部子问题已由用户 2026-10-19 11:47 锁定（D1–D17）。
