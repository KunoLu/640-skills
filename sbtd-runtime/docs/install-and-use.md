# R1 本地 API 包：安装与使用

`sbtd-runtime/` 是 v2.1.0-rc.1 的「本地 API 包」：一个进程内 Python 库，不是服务。R1 没有 HTTP 服务、没有 Dashboard；OpenAPI（`contracts/openapi.yaml`）中未标 `x-sbtd-implementation: library` 的操作是 R2 契约，不是当前实现。本文覆盖 §20.1「安装／使用文档」要求的可选启用、项目授权、观察关闭、升级注意、卸载与数据保留。宿主适配器的来源映射与 smoke 判定见 [host-adapters.md](host-adapters.md)。

## 导入（安装）

本包不进 PyPI，也没有打包发布流程。从仓库根通过 `PYTHONPATH` 导入：

```bash
cd /workspace/640-skills
PYTHONPATH=sbtd-runtime python3 - <<'PY'
from facade import RuntimeFacade
from event_store import EventStore
from stats_query import normalize_scope, query, serve_catalog
from report_snapshot import SnapshotStore
from csv_export import serialize_csv
from history_read import list_events, task_history
PY
```

依赖：Python 3.11+（`zoneinfo`）、PyYAML（仅测试与契约读取需要；库模块本身只用标准库）。

## 运行时家目录（SBTD_RUNTIME_HOME）

所有审计与注册数据都在一个显式的运行时家目录下（PRD §10.1）。它独立于任何项目的 `.sbtd/`，不覆盖已有 HOME 资产。当前实现的布局：

```text
$SBTD_RUNTIME_HOME/
  config.json      # 观察开关（schema_version 1）
  registry.json    # facade 显式注册的项目（用户私有）
  audit.db         # SQLite/WAL：原始观察事件（观察开启且确认后才创建）
  spool/           # 待入库批次（随 audit.db 一起创建）
  snapshots/       # R2.0c：临时 ReportSnapshot，24h 默认 TTL，0700/0600
```

`exports/`、`backups/`、`projections.db` 目前**不创建**：导出仍是库调用返回的字节，没有导出作业服务。`snapshots/` 由显式 `serve` 或 `SnapshotStore(home)` 创建，不依赖观察开关。

## 可选启用与项目授权

观察默认关闭。开启与注册都是显式动作：

```bash
# 1. 建立家目录并打开观察开关
export SBTD_RUNTIME_HOME="$HOME/.sbtd-runtime"
python3 - <<'PY'
import json, os
from pathlib import Path
home = Path(os.environ["SBTD_RUNTIME_HOME"])
home.mkdir(mode=0o700, parents=True, exist_ok=True)
(home / "config.json").write_text(json.dumps({
    "schema_version": 1,
    "observation": {"enabled": True, "level": "metadata", "failure_policy": "best-effort"},
}) + "\n")
PY

# 2. 注册项目（显式授权）
PYTHONPATH=sbtd-runtime python3 - <<'PY'
import os
from pathlib import Path
from facade import RuntimeFacade
facade = RuntimeFacade(Path(os.environ["SBTD_RUNTIME_HOME"]))
print(facade.register_project(project_root=Path("/path/to/project")))
PY
```

边界（每条都有测试）：

- 未注册根、注册根的相邻目录、含 symlink 的根或 runtime home：拒绝，不读不写。
- 观察开关关闭或 config 不可读：`EventStore.open` 抛 `StoreError`，不创建 `audit.db`／`spool`；facade 写操作的业务副作用与旧 helper 一致、审计面为零。
- `EventStore.open(confirmed=False)` 拒绝；`read_only=True` 且库不存在时报错而不是建空库。只读调用（list／inspect／preview）不落任何文件。
- `installation_id`／`device_id` 由调用方显式传入（opaque 随机标识）；适配器在缺失时拒绝，不伪造（见 host-adapters.md）。

## 观察关闭

把 config.json 的 `observation.enabled` 置为 `false`（或删除该文件）即完全关闭：事件库拒绝打开，适配器报错退出，原工作流（task.md 状态机、路由、handoff）不受影响，也不产生任何审计文件。旧 helper 的直接导入不需要注册（R1.1 兼容层语义）。

## 升级注意

- 版本针：事件 `schema_version` 1.0、QueryScope `schema_version` "1.0"、CSV `export_schema_version` 1.1。三者独立演进；未知未来版本被如实拒绝（事件入库 `schema-rejected`、QueryScope 抛 `QueryScopeError`），不静默降级解释。
- CSV 从 1.0 到 1.1 的变化仅是末尾追加 `reasoning_tokens` 列；既有列顺序不变。消费方按列名读取则不受升级影响。
- 损坏的 `audit.db` 被拒绝且不替换为空库；不要手工删库后声称统计完整（§10.4）。升级前的数据库备份与版本化 migration 属于未来工作，本期没有自动升级流程。

## 卸载与数据保留

卸载即删除 `$SBTD_RUNTIME_HOME` 整个目录；包本身只是仓库内的源码目录，没有全局安装、没有 HOME／hooks／MCP 改动。删除前注意：

- `audit.db` 是原始审计事件的唯一副本；删除后历史统计不可重建。`registry.json` 是注册映射的唯一副本。
- 源 `task.md`／测试报告／handoff 永远不在该目录内，统计清理永不触及它们（§10.4）。
- ReportSnapshot 保存在 `snapshots/`，退出服务不删除；默认创建后 24 小时过期，下次启动清扫无引用过期快照。整个家目录的卸载删除是用户操作，不等于快照自动清扫授权。

## 快照与保留（R2.0c）

`SnapshotStore(home)` 要求显式 runtime home，默认 TTL 为 **86400 秒（24 小时）**。创建／复用返回 `expires_at`，`statistics/query`、`timeseries` 与快照 public view 均可获得该有效期；重启不续期，TTL 内凭原 `snapshot_id` 读取相同快照及 dataset。serve 使用 `--home` / `SBTD_RUNTIME_HOME` / `~/.sbtd-runtime` 的既有选址规则。

文件格式 **v1 + SHA-256**，见 [ADR 0003](../../docs/adr/0003-v2.1.0-rc.2-r2.0c-snapshot-persistence.md)。同目录临时文件完整写入、fsync 后原子 rename，POSIX 同步目录；半写、缺 checksum、错误版本、checksum 不符均拒读。损坏或未来格式文件保留，不替换 audit.db、不冒充空数据；重新查询生成新 ID。遗留 `.snapshot-*.tmp` 不会被当作快照。SHA-256 是损坏检测，不是防同机管理员篡改证明。

**清理授权独立依据 PRD §10.4 临时 ReportSnapshot 行与 D13，不由 AC-61 覆盖。** 启动清扫与显式 `store.sweep()` 只删除 `snapshots/` 内有效、已过期且无引用的本扩展快照；不递归、不跟随 symlink/junction、不碰 `exports/`、审计库、配置、spool、备份、源 task.md／报告／handoff。未知文件、坏文件和遗留 temp 保留。服务持续运行时没有新增定时清理器；到期即拒绝无引用读取，但物理删除在 sweep 执行时发生。当前实例已知的过期 ID 返回 gone；删除并再次重启后返回 not found，不永久保存 tombstone。

**R2.1a pin 对接：** 前端 `PinRegistry` 只固定 snapshot_id；它本身不是后端保活。HTML／CSV 作业接受前调用共享 `store.pin(snapshot_id)`，完成／取消／失败的 `finally` 调用 `store.release(snapshot_id)`；引用计数未归零时，即使到期，get/dataset_page 仍可读且 snapshot sweep 不删除。R2.1a 不恢复进程中断的在途作业；重启只装载已完整发布并通过校验的 ready 产物，因此无需恢复在途 pin。

目录／文件沿用 POSIX 0700／0600，Windows ACL 尚未本机验证。单 runtime writer 由 serve 实例锁保证，不支持多个独立服务并发管理相同 snapshots/。当前仍启动装载全部快照，无新增容量策略。查询审计事件（`query.executed`）当前也不落盘。回滚到 R1 内存实现不会自动删除新文件，但不能解析它们；可重新查询，原始事件不受影响。

## R1 没有的东西（如实声明）

- 没有 HTTP 服务与 Dashboard（R2。R2.0a PR-2 起见下文「R2.0a：serve」）。
- R1 没有 `/api/v1/exports*` 导出作业；R2.1a 起支持 HTML／CSV，见下文。库面仍可通过 `csv_export.serialize_csv(snapshot)` 直接获得 CSV 字节。
- R1 没有 JPEG／PDF／HTML 导出和落盘快照保留；R2.0c 起快照保留已实现，R2.1a 增加 HTML／CSV 作业，R2.1b 增加 JPEG／PDF（#153 合并后 HTTP 已开放）；仍没有远程业务控制端点。
- codex@0.163.0 的真实 smoke 状态以 `contracts/capability-matrix.json` 为准；unsupported 如实标记，不返回 0。

### R2.1a：离线 HTML／全量 CSV 导出

`POST /api/v1/exports` 必须提交
`application/json`，例如 `{"snapshot_id":"snap_0123456789abcdef0123456789abcdef","format":"html"}`。
`snapshot_id` 固定点击导出时已完成的快照；`format` 接受 `html`、`csv`、`jpeg` 或 `pdf`。
JPEG／PDF 需要下述可选 renderer；现有 Bearer、CSRF、Idempotency-Key 要求不变。
快照 ID 必须完整匹配 `^snap_[0-9a-f]{32}$`。

可省略 `presentation_state`（使用现有 ReportDocument 默认呈现状态）；若提供，
须包含与 Dashboard `PresentationState` 相同的七个字段：`theme`、
`report_width_px`、`expanded_detail_ids`、`table_sort`、`preview_row_sets`、
`panel_order`、`legend_state`，具体类型见 OpenAPI `ExportPresentationState`。
`report_width_px` 与 `preview_row_sets` 的值为非负 number，允许零与小数；不限制为 integer。
`panel_order` 必须是 `sbtd-runtime/contracts/panel-manifest.json` 中所有 Panel ID
的完整、唯一排列，可调整顺序；空列表、重复、未知或遗漏 ID 均要求 400 BadRequest。
schema 检查非空与唯一性；成员资格和完整性由服务按 manifest 校验，不在 schema 复制枚举。
请求和呈现对象拒绝未知字段；排序、预览行数和隐藏图例不改变 CSV 全量数据范围。
createExport 对非法／缺失请求（包括 snapshot_id 不满足 pattern）返回 400 BadRequest；
格式正确但不存在／不可见的快照为 404，已过期快照为 410；不能静默替换成新快照。
这与既有快照 PATH 参数不同：PATH ID 格式错误在 runtime 中按不存在处理，返回 404。

接受成功返回 **202**，标准 Envelope 的 `data` 恰为 `{"export_id":"exp_…"}`；不表示文件已生成。使用同一请求与 Idempotency-Key 重试获得同一 ID，换请求而复用该键返回 400。`GET /api/v1/exports/{export_id}` 查询 queued／generating／ready／failed／cancelled；ready 后 `GET /api/v1/exports/{export_id}/file` 下载一个文件。`DELETE /api/v1/exports/{export_id}`（Bearer、CSRF、Idempotency-Key）取消／清理本作业。下载不接受 query 参数或文件路径；无 session、非法路径、其他 runtime home 的 ID 被拒绝。

授权沿用现有本地服务：配对 session 可读取当前 runtime home 的快照与导出，不新增多用户／租户隔离。serve 重启使旧 session 失效；重新配对后可按原 export_id 下载该 home 内仍有效的 ready 文件。任何下载都不重新查询实时数据，字节与 SHA-256 保持不变，下载或重启不续期。

- **HTML**：单文件静态正文、内联 CSS／SVG，无外部脚本、CDN、字体或 API；所有 Panel 的身份／指标绑定来自 manifest。系统字体栈含 PingFang SC、Hiragino Sans GB、Microsoft YaHei、Noto Sans CJK SC／JP；不写入机器字体路径。深浅主题、顺序、宽度、排序、预览行数、展开详情和隐藏系列说明随请求固定；HTML 预览不等于完整审计明细。
- **CSV**：沿 snapshot-bound dataset cursor 取完所有授权数据族，复用 schema **1.1** serializer；BOM、固定列、空值与公式转义不变，不受 HTML 预览／排序／图例限制。
- **输出安全**：四格式均在后端输出层应用统一脱敏；manifest 记录 `redaction_policy_version`。不输出原始对话 JSON、秘密或绝对路径；HTML 文本转义，CSV 保留文本公式防护。非 exportable 事件明细不输出，保留省略告警与实际导出数据族计数；不在脱敏前改写指标输入。JPEG／PDF 消费同一已过滤 HTML。
- **产物与保留**：`$SBTD_RUNTIME_HOME/exports/`，目录 0700、文件 0600（POSIX）。artifact 与 v1 JSON manifest 依次用同目录 temp、fsync、atomic rename 发布；manifest 为 ready 标记。记录 MIME、字节数、SHA-256、固定范围、Panel、数据族行数、renderer／脱敏版本和告警。半成品、坏摘要与未知版本不提供下载；失败只报告安全错误，不泄露本地路径。
- **清扫**：ready 起默认 **86400 秒（24h）**；启动必扫，可显式调用 `ExportStore.sweep()`，没有后台定时删除器。到期拒绝下载；物理回收在 sweep 时发生。仅删除 `exports/` 内已验证的过期文件，不递归、不跟随链接、不触及 snapshots／audit.db／配置／源 task／报告／handoff／浏览器下载文件；未知、损坏和崩溃遗留 temp 保留且不升级为成品。删除后本进程记 gone，重启后无永久 tombstone，可返回 not found。

一个本地 worker 串行生成；取消由作业在取数／发布边界响应，不影响其他业务测试或 Agent。manifest 摘要用于损坏检测，不抵御同机管理员篡改。Snapshot 磁盘容量上限不在本轮实现；Windows ACL、macOS／Windows 视觉及四格式对账仍属 R2.2。撤回本轮代码不迁移或删除原始事件／快照；已下载文件不由服务回收。

### R2.1b：可选 JPEG／PDF renderer（HTTP 与库级）

不改变业务项目依赖或 lockfile。先取得安装授权，再在扩展专用虚拟环境中安装；不自动下载、不回退到用户 Chrome/profile：

```bash
python3 -m venv /path/to/sbtd-renderer-venv
/path/to/sbtd-renderer-venv/bin/python -m pip install \
  -r sbtd-runtime/requirements-serve.txt \
  -r sbtd-runtime/requirements-renderer.txt
export SBTD_RUNTIME_HOME=/path/to/sbtd-runtime-home
PLAYWRIGHT_BROWSERS_PATH="$SBTD_RUNTIME_HOME/browsers" \
  /path/to/sbtd-renderer-venv/bin/python -m playwright install --only-shell chromium
```

Playwright 精确固定 **1.64.0**，Chromium headless shell **156.0.8078.4 / revision 1248** 随包固定。Linux 字体依赖见 [`renderer-system-dependencies.txt`](../renderer-system-dependencies.txt)：`fonts-noto-cjk=1:20240730+repack1-1`（本次 Debian 环境实际已安装）。如发行版提供该版本，可在独立授权后使用 `sudo apt-get install 'fonts-noto-cjk=1:20240730+repack1-1'`；不要把别的版本静默当成已验收环境。字体不入仓。可用 `fc-match 'Noto Sans CJK SC'` 和 `fc-match 'Noto Sans CJK JP'` 核验字体选择；macOS／Windows 字体与视觉证据仍属 R2.2。

本次 Linux x64 `--only-shell` 实测：下载 shell 约 **120 MiB**、FFmpeg 约 **2.2 MiB**；解压后整个 `browsers/` apparent size **290,381,668 bytes（约 277 MiB）**，实际分配 **291,356,672 bytes（约 278 MiB）**。不含 Python venv、字体及导出产物；不是所有平台的通用占用值。安装和版本升级都应重新确认磁盘与依赖。

库级调用（`snapshot` 来自当前 `SnapshotStore`，不接受 URL／HTML）：

```python
import time

from export_render import ExportRenderer, default_presentation
from export_store import ExportStore

exports = ExportStore(home, snapshots, ExportRenderer(snapshots, home=home))
try:
    export_id = exports.create(snapshot.snapshot_id, "pdf", default_presentation())
    while (info := exports.get(export_id))["status"] not in {
        "ready", "failed", "cancelled"
    }:
        time.sleep(0.1)
    if info["status"] != "ready":
        raise RuntimeError(info["error"] or info["status"])
    payload, metadata = exports.download(export_id)
finally:
    exports.close()  # 关闭会取消尚未完成的作业；不要在轮询完成前退出。
```

`GET /api/v1/capabilities` 的 `data.exports` 分格式提供 `available`、`reason` 与 `http_available`。Playwright、专用 browser 或必需 CJK 字体缺失时，仅 JPEG／PDF 不可用且附原因；HTML／CSV 不受影响。JPEG／PDF 的 `http_available` 与 renderer 的 `available` 一致：依赖可用时为 true，否则 false。依赖可用不保证每次作业成功。

JPEG 使用当前主题、1440 CSS px、默认 2x、质量 90、完整长图与不透明背景；等待字体和布局，禁动画。`browser_renderer.MAX_SIDE_PX=32000` 与 `MAX_PIXELS=80000000` 是模块级可配置建议值（实测后冻结），须在提交作业前设置，独立 worker 沿用该次配置。2x 超限仅在完整内容和不低于 1440 CSS px 宽度下回退 1x；截图前在调用进程发出 `RuntimeWarning`（精确字符串 `EXPORT_SCALE_DOWNGRADED:1x`），告警处理返回后才截图，manifest 保留同一字符串。调用方可用 Python `warnings` 机制提前显示／捕获通知；ExportStore 调用发生在其工作线程，应在提交作业前配置告警处理，不应在处理器中阻塞。1x 仍超限抛库级 `RendererError.code=EXPORT_IMAGE_SIZE_LIMIT`，异常的 `max_edge_px`／`max_total_pixels` 是 worker 当次生效的配置值，不截断、不分包、不发布半成品。PDF 为 A3 横向、10mm 边距、保留背景的可搜索文字／矢量文档；长表分页重复表头，9pt 页脚含标题、范围、短 snapshot ID 与页码。
上述 `RuntimeWarning` 是直接库级生成路径的通知机制；HTTP 预检已决定的降级通过下述 202 `meta.warnings` 通知，作业不再另作比例决定。

HTTP 已按合并的 [contract PR #153](https://github.com/KunoLu/640-skills/pull/153) 开放：JPEG 在返回 202 之前，于线程池内调用 `BrowserRenderer.preflight()`，沿用单作业信号量与隔离浏览器；期间固定 snapshot 引用、呈现状态、同一已过滤／脱敏静态 HTML 和当次 caps。2x 安全则正常受理；仅 1x 安全时，202 Envelope 的 `meta.warnings` 包含精确字符串 `EXPORT_SCALE_DOWNGRADED:1x`（保留其他报告告警），`data` 仍恰为 `{"export_id":"exp_…"}`。作业沿用预检选定比例，不另行静默降级；生成时复测若该比例不安全则失败且不发布。PDF 为多页输出，无图像尺寸预检，正常返回 202 后生成。下载 MIME 分别为 `image/jpeg`、`application/pdf`，get／download／delete 路由不变。
保留期内的同请求／同 Idempotency-Key 重放（包括重启后重新配对）保留原导出 ID 与告警，不重复预检。过期并清扫后仍沿用既有幂等行为：本进程返回旧 ID，GET／download 为 410；已清理的告警 metadata 不额外保留，不重新生成导出。

JPEG 在 1x 仍超限时，createExport 返回 **422**，JSON body 不包 Envelope、不含额外字段：

```json
{"detail":"EXPORT_IMAGE_SIZE_LIMIT","max_edge_px":32000,"max_total_pixels":80000000}
```

上述数字仅示例；响应携带当次生效 caps，不是冻结常量。422 不创建作业或导出文件，不遗留 snapshot pin；可改用 PDF／HTML 或减少展示明细。库调用仍可独立调用 `BrowserRenderer(home, snapshots).preflight(snapshot, format, presentation_state, cancelled=None)`，返回 `{"scale": 2或1, "warnings": [...]}`（PDF 的 `scale=None`），不截图或创建作业；直接库调用方自行管理 snapshot 生命周期。

两个 **CONTRACT-CHANGE-NEEDED（open）** 未在本轮扩张：

1. **createExport 时 renderer 不可用**：JPEG 同步预检抛出 `RENDERER_UNAVAILABLE`，目前没有专用 HTTP 映射，由框架返回 500，无作业；PDF 不做图像预检，仍 202，随后作业 failed、error=`RENDERER_UNAVAILABLE`。Reviewy 初步认为可映射现有 400 BadRequest（“export format”）；最终由用户决定，本轮不采用新映射。
2. **202 后超时／崩溃**：现有 getExport 返回 200 Envelope，`data.status=failed`、`data.error=RENDERER_TIMEOUT` 或 `RENDERER_FAILED`；download 返回 409 `{"detail":"export is not ready"}`。不发布部分文件或伪造 ready。Reviewy 初步认为需要独立 contract PR；最终由用户决定，#153 的受理前 422 不覆盖此异步失败协议。

每作业独立子进程与临时 profile，不复用浏览器登录态；只允许内存报告主文档，其他路由一律 abort，禁止外联和任意 file 读取。进程内单作业信号量限制 JPEG／PDF 并发，配合服务现有单 runtime writer 锁；取消／超时终止本作业并清理 profile。作业复用现有 pin、`exports/` 原子发布、manifest／SHA-256、ready 后 24h 保留和启动清扫，没有第二条存储路径或新增配额策略。

隔离是应用级边界，Chromium 显式使用 `chromium_sandbox=False`，不声称 OS sandbox 或浏览器漏洞防护。POSIX 在回收 worker PID 前终止其独占进程组；Windows 使用 kill-on-close Job Object 保有后代进程所有权，即使 worker 先退出也能终止后代。Windows 原生 crash 回归已入仓，但本次 Linux 环境跳过；平台实测属 R2.2。整个库级作业默认 60 秒预算，包含依赖预检、HTML 生成、信号量等待和渲染；取消、超时及失败不会发布半成品。

## R2.0a：serve（本地 Dashboard 服务，D5–D8）

R2.0a PR-2 起仓内有 HTTP 服务层 `sbtd-runtime/serve.py`（Starlette＋uvicorn，ADR 0001 §2），服务入仓的 `dashboard/static/` 产物并接 R1 真实库面（`stats_query`／`report_snapshot` over `EventStore`）。安装精确钉版依赖后从仓库根启动：

```bash
python3 -m pip install -r sbtd-runtime/requirements-serve.txt
PYTHONPATH=sbtd-runtime python3 -m serve [--port 6400] [--no-open] [--home PATH]
```

行为（访问控制见 `tests/test_serve.py` 的真实进程／socket 测试，落盘见 `tests/test_snapshot_persistence.py` 与 R2.0c task 的真实重启 smoke）：

- 只绑定 127.0.0.1；Host 白名单 localhost／127.0.0.1／[::1] 且端口相等，Origin 全匹配，规则硬编码无配置面（D8）。
- 端口占用即启动失败、退出码非零并提示 `--port`（D5）；重复启动经 `serve.lock` 实例锁＋端口双判报「已有实例」，陈旧锁（死 pid／不可读／损坏）按无效处理（D6）。
- 前台运行，Ctrl-C 干净退出并移除锁（D6）。
- 一次性 ticket 只经自动打开浏览器的 URL fragment 交付（默认 `--open`）；`--no-open` 或打开失败时写入 `$SBTD_RUNTIME_HOME/pairing-ticket`（0600）由用户手动配对。ticket 短时（300s）一次性、读后即毁、终端与日志不打印（D7；命令行参数可见风险与残余风险见 ADR 0002 §3）。配对换取 session Bearer＋CSRF（`X-CSRF-Token` 响应头），unsafe 方法要求两者。
- 审计库不可用（观察关闭／无 audit.db）时服务仍启动，查询响应 Envelope meta 带 `AUDIT_STORE_UNAVAILABLE:*` warning 且 complete=false，不编造数字。
- R2.0c 起快照落盘 `snapshots/`，默认 TTL 24h，创建告知 expires_at；TTL 内重启仍可读取，启动只清扫本目录无引用过期快照。

跨平台（macOS／Windows）证据与 Host/Origin 负例对账属 R2.2；Windows 上实例锁的活 pid 判定（`os.kill(pid, 0)` 语义）未在本期验证。
