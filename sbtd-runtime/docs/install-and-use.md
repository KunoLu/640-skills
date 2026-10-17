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
```

`snapshots/`、`exports/`、`backups/`、`projections.db` 目前**不创建**：ReportSnapshot 是进程内对象（见下文「快照与保留」），导出是库调用返回的字节，没有导出作业服务。

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
- 进程内 ReportSnapshot 随进程退出消失，无残留。

## 快照与保留（诚实差异）

PRD §10.4 期望临时 ReportSnapshot 默认保留 24 小时。当前实现是**进程内对象**：不创建 `snapshots/` 目录，进程退出即消失，比 24h 更短；过期快照报 gone 而不回收旧 id。跨进程保留（落盘 snapshots/）是明确的未来工作，R1 不建。查询审计事件（`query.executed`）当前也不落盘。

## R1 没有的东西（如实声明）

- 没有 HTTP 服务与 Dashboard（R2）。
- 没有 `/api/v1/exports*` 导出作业（OpenAPI 标记 `v2.1.0-rc.2`，非 rc.1 阻塞）；CSV 通过 `csv_export.serialize_csv(snapshot)` 在进程内直接获得字节。
- 没有 JPEG／PDF／HTML 导出，没有落盘快照保留，没有远程业务控制端点。
- codex@0.163.0 的真实 smoke 状态以 `contracts/capability-matrix.json` 为准；unsupported 如实标记，不返回 0。
