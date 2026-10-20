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

**R2.1a pin 对接：** 前端 `PinRegistry` 只固定 snapshot_id；它本身不是后端保活。作业开始取数前调用共享 `store.pin(snapshot_id)`，完成／取消／失败的 `finally` 调用 `store.release(snapshot_id)`；引用计数未归零时，即使到期，get/dataset_page 仍可读且 sweep 不删除。若作业支持跨重启恢复，须先恢复引用，再用 `SnapshotStore(home, pinned_snapshot_ids=恢复的 ID 列表)` 创建 store，确保引用先于启动清扫安装。本任务没有导出作业或新的 pin HTTP API；进程内引用不自动成为持久作业。

目录／文件沿用 POSIX 0700／0600，Windows ACL 尚未本机验证。单 runtime writer 由 serve 实例锁保证，不支持多个独立服务并发管理相同 snapshots/。当前仍启动装载全部快照，无新增容量策略。查询审计事件（`query.executed`）当前也不落盘。回滚到 R1 内存实现不会自动删除新文件，但不能解析它们；可重新查询，原始事件不受影响。

## R1 没有的东西（如实声明）

- 没有 HTTP 服务与 Dashboard（R2。R2.0a PR-2 起见下文「R2.0a：serve」）。
- 没有 `/api/v1/exports*` 导出作业（OpenAPI 标记 `v2.1.0-rc.2`，非 rc.1 阻塞）；CSV 通过 `csv_export.serialize_csv(snapshot)` 在进程内直接获得字节。
- R1 没有 JPEG／PDF／HTML 导出和落盘快照保留；R2.0c 起快照保留已实现（见上文）。仍没有远程业务控制端点。
- codex@0.163.0 的真实 smoke 状态以 `contracts/capability-matrix.json` 为准；unsupported 如实标记，不返回 0。

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
